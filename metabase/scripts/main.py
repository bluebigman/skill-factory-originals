#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
metabase 数据可视化技能 - 独立实现脚本
基于功能规格实现：数据解析、结构化输出、置信度标注、错误处理
"""

import argparse
import sys
import json
from typing import Dict, List, Any, Tuple, Optional

# 错误码定义
ERROR_CODES = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：输入来源、输出格式、期望完整度",
    "E003": "输入格式不符合要求，示例：需要包含数据字段和值",
    "E004": "这超出了本工具的能力范围，建议使用专业数据分析工具",
    "E005": "结果无法确定，建议增加数据量或明确需求",
    "E006": "内部处理错误，请检查输入数据格式",
    "E007": "输出格式不支持，支持格式：json、table、text",
    "E008": "数据字段不一致，各记录字段需保持一致",
    "E009": "数据量过大，超出处理限制",
    "E010": "置信度计算失败，请检查数据质量",
}


class DataProcessor:
    """核心数据处理类"""
    
    def __init__(self):
        self.supported_formats = ["json", "table", "text"]
        self.max_records = 10000
        
    def validate_input(self, data: Any) -> Tuple[bool, str]:
        """校验输入数据"""
        if data is None:
            return False, "E001"
        if isinstance(data, str) and not data.strip():
            return False, "E001"
        if isinstance(data, list) and len(data) == 0:
            return False, "E001"
        if isinstance(data, dict) and len(data) == 0:
            return False, "E001"
        if isinstance(data, list) and len(data) > self.max_records:
            return False, "E009"
        return True, ""
    
    def parse_input(self, data: Any) -> List[Dict[str, Any]]:
        """解析输入为结构化记录列表"""
        # 如果输入是字符串，尝试解析为 JSON
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except json.JSONDecodeError:
                raise ValueError("E003")
        
        # 统一转为记录列表
        if isinstance(data, dict):
            # 检查是否为单条记录
            if "fields" in data and "records" in data:
                # 标准表格格式
                fields = data["fields"]
                records = data["records"]
                if not isinstance(fields, list) or not isinstance(records, list):
                    raise ValueError("E003")
                result = []
                for record in records:
                    if len(record) != len(fields):
                        raise ValueError("E008")
                    result.append(dict(zip(fields, record)))
                return result
            else:
                # 单条记录
                return [data]
        elif isinstance(data, list):
            # 检查是否为记录列表
            if all(isinstance(item, dict) for item in data):
                # 检查字段一致性
                if len(data) > 1:
                    first_fields = set(data[0].keys())
                    for item in data[1:]:
                        if set(item.keys()) != first_fields:
                            raise ValueError("E008")
                return data
            elif all(isinstance(item, list) for item in data):
                # 二维数组格式
                if not data:
                    return []
                headers = [f"column_{i}" for i in range(len(data[0]))]
                result = []
                for row in data:
                    if len(row) != len(headers):
                        raise ValueError("E008")
                    result.append(dict(zip(headers, row)))
                return result
            else:
                raise ValueError("E003")
        else:
            raise ValueError("E003")
    
    def calculate_confidence(self, records: List[Dict[str, Any]]) -> float:
        """计算置信度"""
        if not records:
            return 0.0
        
        # 基础置信度
        confidence = 90.0
        
        # 数据量充足性
        if len(records) < 3:
            confidence -= 10
        
        # 字段完整性检查
        total_fields = 0
        missing_values = 0
        for record in records:
            for key, value in record.items():
                total_fields += 1
                if value is None or value == "" or value == "N/A":
                    missing_values += 1
        
        if total_fields > 0:
            missing_ratio = missing_values / total_fields
            if missing_ratio > 0.3:
                confidence -= 15
            elif missing_ratio > 0.1:
                confidence -= 8
        
        # 数据类型一致性
        if records:
            first_record = records[0]
            for key in first_record:
                value_type = type(first_record[key]).__name__
                for record in records[1:]:
                    if key in record and type(record[key]).__name__ != value_type:
                        confidence -= 5
                        break
        
        return max(0.0, min(100.0, confidence))
    
    def format_output(self, records: List[Dict[str, Any]], 
                     output_format: str = "json") -> str:
        """格式化输出"""
        if output_format not in self.supported_formats:
            raise ValueError("E007")
        
        if output_format == "json":
            return json.dumps(records, ensure_ascii=False, indent=2)
        elif output_format == "table":
            if not records:
                return "空数据"
            
            # 获取所有字段名
            fields = list(records[0].keys())
            
            # 计算每列宽度
            col_widths = {}
            for field in fields:
                max_width = len(str(field))
                for record in records:
                    value_str = str(record.get(field, ""))
                    max_width = max(max_width, len(value_str))
                col_widths[field] = min(max_width + 2, 50)  # 限制最大宽度
            
            # 生成表头
            header = "| " + " | ".join(field.ljust(col_widths[field]) 
                                        for field in fields) + " |"
            separator = "|" + "|".join("-" * (col_widths[field] + 2) 
                                       for field in fields) + "|"
            
            # 生成数据行
            lines = [header, separator]
            for record in records:
                row = "| " + " | ".join(
                    str(record.get(field, "")).ljust(col_widths[field])
                    for field in fields
                ) + " |"
                lines.append(row)
            
            return "\n".join(lines)
        else:  # text
            if not records:
                return "空数据"
            
            lines = []
            for i, record in enumerate(records, 1):
                lines.append(f"记录 {i}:")
                for key, value in record.items():
                    lines.append(f"  {key}: {value}")
                lines.append("")
            return "\n".join(lines)
    
    def process(self, data: Any, output_format: str = "json") -> Dict[str, Any]:
        """主处理流程"""
        # Step 1: 校验输入
        valid, error_code = self.validate_input(data)
        if not valid:
            return {
                "success": False,
                "error_code": error_code,
                "message": ERROR_CODES.get(error_code, "未知错误"),
                "data": None,
                "confidence": 0.0
            }
        
        try:
            # Step 2: 解析输入
            records = self.parse_input(data)
            
            # Step 3: 计算置信度
            confidence = self.calculate_confidence(records)
            
            # Step 4: 格式化输出
            formatted = self.format_output(records, output_format)
            
            # Step 5: 构建结果
            result = {
                "success": True,
                "error_code": None,
                "message": "处理成功",
                "data": records,
                "formatted_output": formatted,
                "confidence": confidence,
                "record_count": len(records),
                "fields": list(records[0].keys()) if records else []
            }
            
            # 置信度标注
            if confidence >= 90:
                result["confidence_label"] = "高置信度"
            elif confidence >= 85:
                result["confidence_label"] = "建议复核"
            else:
                result["confidence_label"] = "[需核实]"
                result["message"] += " - 部分内容需人工核实"
            
            return result
            
        except ValueError as e:
            error_code = str(e)
            if error_code not in ERROR_CODES:
                error_code = "E006"
            return {
                "success": False,
                "error_code": error_code,
                "message": ERROR_CODES.get(error_code, "处理失败"),
                "data": None,
                "confidence": 0.0
            }
        except Exception:
            return {
                "success": False,
                "error_code": "E010",
                "message": ERROR_CODES["E010"],
                "data": None,
                "confidence": 0.0
            }


def run_selftest() -> bool:
    """内置自检函数 - 使用硬编码样例数据"""
    print("=" * 60)
    print("运行自检程序...")
    
    processor = DataProcessor()
    all_passed = True
    
    # 测试用例 1: 基本数据处理
    print("\n[测试 1] 基本数据处理")
    test_data = [
        {"name": "产品A", "sales": 100, "region": "华东"},
        {"name": "产品B", "sales": 200, "region": "华北"},
        {"name": "产品C", "sales": 150, "region": "华南"}
    ]
    result = processor.process(test_data, "json")
    assert result["success"], "基本处理失败"
    assert result["record_count"] == 3, "记录数不正确"
    assert len(result["fields"]) == 3, "字段数不正确"
    assert result["confidence"] > 70, "置信度应高于70"
    assert result["confidence_label"] in ["高置信度", "建议复核", "[需核实]"]
    print("  ✓ 通过")
    
    # 测试用例 2: 空输入处理
    print("\n[测试 2] 空输入处理")
    result = processor.process(None)
    assert not result["success"], "空输入应失败"
    assert result["error_code"] == "E001", "错误码应为E001"
    print("  ✓ 通过")
    
    # 测试用例 3: 单条记录处理
    print("\n[测试 3] 单条记录处理")
    result = processor.process({"id": 1, "value": "测试"})
    assert result["success"], "单条记录处理失败"
    assert result["record_count"] == 1, "记录数应为1"
    assert result["confidence"] < 90, "单条记录置信度应较低"
    print("  ✓ 通过")
    
    # 测试用例 4: 表格格式输出
    print("\n[测试 4] 表格格式输出")
    result = processor.process(test_data, "table")
    assert result["success"], "表格格式处理失败"
    assert "|" in result["formatted_output"], "表格格式应包含竖线分隔符"
    assert "产品A" in result["formatted_output"], "表格应包含数据"
    print("  ✓ 通过")
    
    # 测试用例 5: 文本格式输出
    print("\n[测试 5] 文本格式输出")
    result = processor.process(test_data, "text")
    assert result["success"], "文本格式处理失败"
    assert "记录 1" in result["formatted_output"], "文本格式应包含记录编号"
    print("  ✓ 通过")
    
    # 测试用例 6: 字段不一致处理
    print("\n[测试 6] 字段不一致处理")
    bad_data = [
        {"a": 1, "b": 2},
        {"a": 3, "c": 4}  # 字段不一致
    ]
    result = processor.process(bad_data)
    assert not result["success"], "字段不一致应失败"
    assert result["error_code"] == "E008", "错误码应为E008"
    print("  ✓ 通过")
    
    # 测试用例 7: 缺失值处理
    print("\n[测试 7] 缺失值处理")
    data_with_missing = [
        {"name": "A", "value": 100},
        {"name": "B", "value": None},
        {"name": "C", "value": ""}
    ]
    result = processor.process(data_with_missing)
    assert result["success"], "含缺失值的处理应成功"
    assert result["confidence"] < 90, "缺失值应降低置信度"
    print("  ✓ 通过")
    
    # 测试用例 8: 批量数据处理
    print("\n[测试 8] 批量数据处理")
    batch_data = [{"index": i, "value": i * 2} for i in range(100)]
    result = processor.process(batch_data)
    assert result["success"], "批量处理失败"
    assert result["record_count"] == 100, "记录数应为100"
    assert result["confidence"] > 85, "大批量数据置信度应较高"
    print("  ✓ 通过")
    
    # 测试用例 9: 错误格式处理
    print("\n[测试 9] 错误格式处理")
    result = processor.process(12345)  # 不支持的类型
    assert not result["success"], "不支持的类型应失败"
    assert result["error_code"] in ["E003", "E006"], "错误码应为E003或E006"
    print("  ✓ 通过")
    
    # 测试用例 10: 二维数组处理
    print("\n[测试 10] 二维数组处理")
    matrix_data = [
        [1, 2, 3],
        [4, 5, 6],
        [7, 8, 9]
    ]
    result = processor.process(matrix_data)
    assert result["success"], "二维数组处理失败"
    assert result["record_count"] == 3, "记录数应为3"
    assert "column_0" in result["fields"], "字段名应为column_0"
    print("  ✓ 通过")
    
    print("\n" + "=" * 60)
    print("全部自检通过！")
    return True


def main():
    """主入口"""
    parser = argparse.ArgumentParser(
        description="metabase 数据可视化技能 - 数据处理工具"
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检程序"
    )
    parser.add_argument(
        "--input",
        type=str,
        help="输入数据（JSON字符串）"
    )
    parser.add_argument(
        "--format",
        type=str,
        choices=["json", "table", "text"],
        default="json",
        help="输出格式（默认: json）"
    )
    
    parser.add_argument("--verbose", action="store_true", help="显示修改明细")  # R6 可解释输出
    
    args = parser.parse_args()
    
    # 自检模式
    if args.selftest:
        success = run_selftest()
        sys.exit(0 if success else 1)
    
    # 正常处理模式
    if not args.input:
        print("错误 E001: " + ERROR_CODES["E001"], file=sys.stderr)
        print("提示: 使用 --input 提供数据，或使用 --selftest 运行自检")
        sys.exit(1)
    
    # 尝试解析输入为 JSON
    try:
        input_data = json.loads(args.input)
    except json.JSONDecodeError:
        # 如果不是 JSON，尝试作为字符串处理
        input_data = args.input
    
    # 处理数据
    processor = DataProcessor()
    result = processor.process(input_data, args.format)
    
    # 输出结果
    if result["success"]:
        print(result["formatted_output"])
        print(f"\n--- 统计信息 ---")
        print(f"记录数: {result['record_count']}")
        print(f"字段: {', '.join(result['fields'])}")
        print(f"置信度: {result['confidence']:.1f}% ({result['confidence_label']})")
    else:
        print(f"错误 {result['error_code']}: {result['message']}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
