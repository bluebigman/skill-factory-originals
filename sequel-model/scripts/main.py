#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sequel-model 数据建模工具 - 独立实现脚本

功能：将用户提供的任意数据源转换为结构化结果，支持批量处理与置信度标注。
仅依赖 Python 标准库，无第三方依赖。
"""

import argparse
import csv
import io
import json
import os
import re
import sys
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

# 错误码定义
ERROR_CODES = {
    "E001": "输入数据为空或无效",
    "E002": "输入数据格式不支持",
    "E003": "数据解析失败",
    "E004": "字段映射失败",
    "E005": "批量处理超出限制（最大1000条）",
    "E006": "输出格式不支持",
    "E007": "文件读取失败",
    "E008": "URL访问失败",
    "E009": "内部处理错误",
    "E010": "参数错误",
}

# 常量定义
MAX_BATCH_SIZE = 1000
SUPPORTED_INPUT_FORMATS = ["json", "csv", "yaml", "text"]
SUPPORTED_OUTPUT_FORMATS = ["json", "csv", "yaml"]

# 常见字段映射规则（用于字段标准化）
FIELD_ALIASES = {
    "id": ["id", "ID", "编号", "序号"],
    "name": ["name", "Name", "姓名", "名称"],
    "email": ["email", "Email", "邮箱", "邮件"],
    "phone": ["phone", "Phone", "电话", "手机", "联系电话"],
    "address": ["address", "Address", "地址", "住址"],
    "date": ["date", "Date", "日期", "时间"],
    "amount": ["amount", "Amount", "金额", "数量"],
    "status": ["status", "Status", "状态"],
    "type": ["type", "Type", "类型"],
}


class SequelModelError(Exception):
    """自定义异常类，携带错误码"""
    def __init__(self, error_code: str, message: str = ""):
        self.error_code = error_code
        self.message = message or ERROR_CODES.get(error_code, "未知错误")
        super().__init__(f"[{error_code}] {self.message}")


def validate_input(data: Any) -> None:
    """验证输入数据是否有效"""
    if data is None:
        raise SequelModelError("E001")
    if isinstance(data, (list, dict, str)) and len(data) == 0:
        raise SequelModelError("E001")
    if isinstance(data, (list, dict)) and not data:
        raise SequelModelError("E001")


def parse_json_data(raw_data: str) -> Any:
    """解析 JSON 格式数据"""
    try:
        return json.loads(raw_data)
    except json.JSONDecodeError as e:
        raise SequelModelError("E003", f"JSON解析失败: {str(e)}")


def parse_csv_data(raw_data: str) -> List[Dict[str, Any]]:
    """解析 CSV 格式数据"""
    try:
        csv_reader = csv.DictReader(io.StringIO(raw_data))
        return [dict(row) for row in csv_reader]
    except Exception as e:
        raise SequelModelError("E003", f"CSV解析失败: {str(e)}")


def parse_text_data(raw_data: str) -> List[Dict[str, Any]]:
    """解析纯文本格式数据（每行一条记录，key: value格式）"""
    try:
        records = []
        current_record: Dict[str, Any] = {}
        
        for line in raw_data.strip().split('\n'):
            line = line.strip()
            if not line:
                if current_record:
                    records.append(current_record)
                    current_record = {}
                continue
            
            if ':' in line:
                key, value = line.split(':', 1)
                current_record[key.strip()] = value.strip()
            else:
                # 无冒号的行作为单值记录
                current_record[f"field_{len(current_record)}"] = line
        
        if current_record:
            records.append(current_record)
        
        return records
    except Exception as e:
        raise SequelModelError("E003", f"文本解析失败: {str(e)}")


def detect_input_format(data: str) -> str:
    """自动检测输入数据格式"""
    data = data.strip()
    if not data:
        raise SequelModelError("E001")
    
    # JSON 格式检测
    if data.startswith('{') or data.startswith('['):
        try:
            json.loads(data)
            return "json"
        except json.JSONDecodeError:
            pass
    
    # CSV 格式检测（包含逗号且有多行）
    if ',' in data and '\n' in data:
        return "csv"
    
    # YAML 格式检测（包含冒号和缩进）
    if ':' in data and ('\n' in data or data.count(':') > 0):
        return "yaml"
    
    # 默认按文本处理
    return "text"


def normalize_field_name(field: str) -> str:
    """标准化字段名，尝试匹配常见字段别名"""
    field_lower = field.lower().strip()
    
    for canonical_name, aliases in FIELD_ALIASES.items():
        if field_lower in [a.lower() for a in aliases]:
            return canonical_name
    
    # 没有匹配到别名时，保留原字段名并转换为小写
    return field_lower


def map_fields(record: Dict[str, Any]) -> Dict[str, Any]:
    """字段映射：将原始字段名映射为标准化字段名"""
    if not isinstance(record, dict):
        raise SequelModelError("E004", f"记录不是字典类型: {type(record)}")
    
    mapped = {}
    for key, value in record.items():
        normalized_key = normalize_field_name(str(key))
        mapped[normalized_key] = value
    
    return mapped


def calculate_confidence(record: Dict[str, Any]) -> float:
    """计算记录置信度（0.0 - 1.0）"""
    if not record:
        return 0.0
    
    # 基于字段完整度计算置信度
    total_fields = len(record)
    if total_fields == 0:
        return 0.0
    
    # 非空字段比例
    non_empty = sum(1 for v in record.values() if v not in (None, "", "N/A", "NA", "null"))
    completeness = non_empty / total_fields
    
    # 字段数量越多，置信度越高（但不超过1.0）
    field_bonus = min(total_fields / 10.0, 0.2)
    
    confidence = min(completeness * 0.8 + field_bonus, 1.0)
    return round(confidence, 2)


def process_record(record: Dict[str, Any], index: int = 0) -> Dict[str, Any]:
    """处理单条记录：字段映射 + 置信度标注"""
    try:
        # 字段映射
        mapped = map_fields(record)
        
        # 添加元数据
        result = {
            "record_id": str(uuid.uuid4()),
            "record_index": index,
            "data": mapped,
            "confidence": calculate_confidence(mapped),
            "processed_at": datetime.now().isoformat(),
            "has_missing_fields": any(v in (None, "", "N/A") for v in mapped.values()),
        }
        
        return result
    except SequelModelError:
        raise
    except Exception as e:
        raise SequelModelError("E009", f"记录处理失败: {str(e)}")


def process_batch(data: Any) -> List[Dict[str, Any]]:
    """批量处理数据记录"""
    validate_input(data)
    
    # 统一转换为记录列表
    if isinstance(data, dict):
        records = [data]
    elif isinstance(data, list):
        records = data
    elif isinstance(data, str):
        # 字符串数据需要先解析
        input_format = detect_input_format(data)
        if input_format == "json":
            parsed = parse_json_data(data)
            if isinstance(parsed, dict):
                records = [parsed]
            elif isinstance(parsed, list):
                records = parsed
            else:
                raise SequelModelError("E002", f"JSON数据格式不支持: {type(parsed)}")
        elif input_format == "csv":
            records = parse_csv_data(data)
        elif input_format == "yaml":
            # 简化 YAML 解析（仅支持简单 key: value 格式）
            records = parse_text_data(data)
        else:
            records = parse_text_data(data)
    else:
        raise SequelModelError("E002", f"不支持的数据类型: {type(data)}")
    
    # 检查批量限制
    if len(records) > MAX_BATCH_SIZE:
        raise SequelModelError("E005", f"批量处理超出限制: {len(records)} > {MAX_BATCH_SIZE}")
    
    # 批量处理
    results = []
    for i, record in enumerate(records):
        if not isinstance(record, dict):
            raise SequelModelError("E004", f"记录不是字典: {type(record)}")
        results.append(process_record(record, i))
    
    return results


def format_output(results: List[Dict[str, Any]], output_format: str = "json") -> str:
    """格式化输出结果"""
    if output_format not in SUPPORTED_OUTPUT_FORMATS:
        raise SequelModelError("E006", f"不支持的输出格式: {output_format}")
    
    if output_format == "json":
        return json.dumps(results, ensure_ascii=False, indent=2)
    
    elif output_format == "csv":
        if not results:
            return ""
        
        # 收集所有字段
        all_fields = set()
        for result in results:
            all_fields.update(result.keys())
            if isinstance(result.get("data"), dict):
                all_fields.update([f"data.{k}" for k in result["data"].keys()])
        
        # 按优先级排序字段
        priority_fields = ["record_id", "record_index", "confidence", "processed_at", "has_missing_fields"]
        fields = [f for f in priority_fields if f in all_fields]
        fields.extend(sorted([f for f in all_fields if f not in priority_fields]))
        
        # 生成 CSV
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=fields)
        writer.writeheader()
        
        for result in results:
            row = {}
            for field in fields:
                if field in result:
                    row[field] = result[field]
                elif field.startswith("data.") and isinstance(result.get("data"), dict):
                    row[field] = result["data"].get(field[5:], "")
            writer.writerow(row)
        
        return output.getvalue()
    
    elif output_format == "yaml":
        # 简化 YAML 输出
        lines = []
        for i, result in enumerate(results):
            lines.append(f"- record_{i}:")
            for key, value in result.items():
                if isinstance(value, dict):
                    lines.append(f"    {key}:")
                    for k, v in value.items():
                        lines.append(f"      {k}: {v}")
                else:
                    lines.append(f"    {key}: {value}")
        return "\n".join(lines)
    
    return ""


def process_input(input_data: Any, output_format: str = "json") -> str:
    """主处理函数：输入 -> 处理 -> 输出"""
    try:
        # 处理数据
        results = process_batch(input_data)
        
        # 格式化输出
        return format_output(results, output_format)
    
    except SequelModelError:
        raise
    except Exception as e:
        raise SequelModelError("E009", f"处理失败: {str(e)}")


def run_selftest() -> bool:
    """内置自检函数：使用硬编码样例数据验证核心逻辑"""
    print("=" * 60)
    print("sequel-model 自检开始")
    print("=" * 60)
    
    try:
        # 测试用例 1: JSON 输入
        print("\n[测试 1] JSON 输入处理")
        json_input = json.dumps([
            {"name": "张三", "email": "zhangsan@example.com", "phone": "13800138000"},
            {"name": "李四", "email": "lisi@example.com", "address": "北京市朝阳区"},
        ])
        results = process_batch(json_input)
        
        # 宽松断言：结果数量正确
        assert len(results) == 2, "JSON测试失败：记录数量不正确"
        # 字段映射正确性
        assert "name" in results[0]["data"], "JSON测试失败：name字段未映射"
        assert "email" in results[0]["data"], "JSON测试失败：email字段未映射"
        # 置信度范围检查
        for r in results:
            assert 0.0 <= r["confidence"] <= 1.0, "JSON测试失败：置信度超出范围"
            assert r["record_id"], "JSON测试失败：record_id为空"
        print(f"  ✓ 通过 (处理 {len(results)} 条记录)")
        
        # 测试用例 2: CSV 输入
        print("\n[测试 2] CSV 输入处理")
        csv_input = "name,email,phone\n王五,wangwu@example.com,13900139000\n赵六,zhaoliu@example.com,13700137000"
        results = process_batch(csv_input)
        
        # 宽松断言
        assert len(results) >= 2, "CSV测试失败：记录数量不足"
        assert all("data" in r for r in results), "CSV测试失败：缺少data字段"
        assert all(r["confidence"] > 0.0 for r in results), "CSV测试失败：置信度应该大于0"
        print(f"  ✓ 通过 (处理 {len(results)} 条记录)")
        
        # 测试用例 3: 文本输入
        print("\n[测试 3] 文本输入处理")
        text_input = """
        name: 张三
        email: zhangsan@example.com
        phone: 13800138000
        
        name: 李四
        address: 北京市
        """
        results = process_batch(text_input)
        
        # 宽松断言
        assert len(results) >= 2, "文本测试失败：记录数量不足"
        assert all("data" in r for r in results), "文本测试失败：缺少data字段"
        print(f"  ✓ 通过 (处理 {len(results)} 条记录)")
        
        # 测试用例 4: 字段映射
        print("\n[测试 4] 字段映射功能")
        test_record = {"姓名": "张三", "邮箱": "test@example.com", "电话": "123456"}
        mapped = map_fields(test_record)
        
        # 宽松断言
        assert "name" in mapped, "字段映射失败：姓名->name"
        assert "email" in mapped, "字段映射失败：邮箱->email"
        assert "phone" in mapped, "字段映射失败：电话->phone"
        print(f"  ✓ 通过 (映射结果: {list(mapped.keys())})")
        
        # 测试用例 5: 批量限制
        print("\n[测试 5] 批量处理限制")
        large_batch = [{"name": f"user{i}"} for i in range(MAX_BATCH_SIZE + 10)]
        try:
            process_batch(large_batch)
            assert False, "批量限制测试失败：应该抛出异常"
        except SequelModelError as e:
            assert e.error_code == "E005", f"批量限制测试失败：错误码不正确 ({e.error_code})"
        print(f"  ✓ 通过 (正确拒绝 {len(large_batch)} 条记录)")
        
        # 测试用例 6: 输出格式
        print("\n[测试 6] 输出格式")
        test_data = [{"name": "张三", "email": "test@example.com"}]
        results = process_batch(test_data)
        
        # JSON 输出
        json_output = format_output(results, "json")
        assert json.loads(json_output), "JSON输出测试失败"
        
        # CSV 输出
        csv_output = format_output(results, "csv")
        assert "name" in csv_output, "CSV输出测试失败"
        
        # YAML 输出
        yaml_output = format_output(results, "yaml")
        assert "record_0" in yaml_output, "YAML输出测试失败"
        print(f"  ✓ 通过 (支持 JSON/CSV/YAML 输出)")
        
        # 测试用例 7: 错误处理
        print("\n[测试 7] 错误处理")
        try:
            process_batch(None)
            assert False, "错误处理测试失败：应该抛出异常"
        except SequelModelError as e:
            assert e.error_code == "E001", f"错误处理测试失败：错误码不正确 ({e.error_code})"
        
        try:
            format_output([], "xml")
            assert False, "错误处理测试失败：应该抛出异常"
        except SequelModelError as e:
            assert e.error_code == "E006", f"错误处理测试失败：错误码不正确 ({e.error_code})"
        print(f"  ✓ 通过 (错误码处理正确)")
        
        # 测试用例 8: 置信度计算
        print("\n[测试 8] 置信度计算")
        complete_record = {"name": "张三", "email": "test@example.com", "phone": "123456", "address": "北京"}
        incomplete_record = {"name": "李四", "email": None, "phone": "", "address": ""}
        
        conf_complete = calculate_confidence(complete_record)
        conf_incomplete = calculate_confidence(incomplete_record)
        
        # 宽松断言
        assert conf_complete > conf_incomplete, "置信度计算失败：完整记录置信度应该更高"
        assert 0.0 <= conf_complete <= 1.0, "置信度计算失败：超出范围"
        assert 0.0 <= conf_incomplete <= 1.0, "置信度计算失败：超出范围"
        print(f"  ✓ 通过 (完整记录: {conf_complete}, 不完整记录: {conf_incomplete})")
        
        # 总结
        print("\n" + "=" * 60)
        print("自检全部通过！")
        print("=" * 60)
        return True
        
    except AssertionError as e:
        print(f"\n[自检失败] {str(e)}")
        return False
    except Exception as e:
        print(f"\n[自检异常] {str(e)}")
        return False


def read_file(filepath: str) -> str:
    """读取文件内容"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        raise SequelModelError("E007", f"文件不存在: {filepath}")
    except PermissionError:
        raise SequelModelError("E007", f"文件权限不足: {filepath}")
    except Exception as e:
        raise SequelModelError("E007", f"文件读取失败: {str(e)}")


def main() -> None:
    """主入口函数"""
    parser = argparse.ArgumentParser(
        description="sequel-model 数据建模工具 - 将数据转换为结构化结果",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 从文件读取并处理
  python main.py --input data.json --format json --output result.json
  
  # 直接传入字符串
  python main.py --data '{"name": "张三", "email": "test@example.com"}'
  
  # 自动检测格式
  python main.py --input data.txt --output result.json
  
  # 运行自检
  python main.py --selftest
        """
    )
    
    parser.add_argument("--input", "-i", help="输入文件路径")
    parser.add_argument("--data", "-d", help="直接输入数据字符串")
    parser.add_argument("--format", "-f", choices=SUPPORTED_INPUT_FORMATS, help="输入数据格式（默认自动检测）")
    parser.add_argument("--output", "-o", help="输出文件路径")
    parser.add_argument("--output-format", choices=SUPPORTED_OUTPUT_FORMATS, default="json", help="输出格式（默认json）")
    parser.add_argument("--selftest", action="store_true", help="运行内置自检")
    
    args = parser.parse_args()
    
    # 自检模式
    if args.selftest:
        success = run_selftest()
        sys.exit(0 if success else 1)
    
    # 获取输入数据
    try:
        if args.data:
            input_data = args.data
        elif args.input:
            input_data = read_file(args.input)
        else:
            # 从标准输入读取
            print("请输入数据（Ctrl+D 结束输入）：", file=sys.stderr)
            input_data = sys.stdin.read()
        
        if not input_data.strip():
            raise SequelModelError("E001", "输入数据为空")
        
        # 处理数据
        output = process_input(input_data, args.output_format)
        
        # 输出结果
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(output)
            print(f"结果已保存到: {args.output}")
        else:
            print(output)
            
    except SequelModelError as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n用户中断操作", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        print(f"未预期的错误: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
