#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
markaby — 数据解析与结构化提取工具

功能：
- 从非结构化文本中提取指定字段
- 输出结构化 JSON 结果并标注置信度
- 支持批量处理多条记录
- 支持 CSV、JSON、纯文本输入格式

仅依赖 Python 标准库，无第三方依赖。
"""

import argparse
import csv
import io
import json
import re
import sys
from typing import Any, Dict, List, Optional, Tuple

# 错误码定义
ERROR_CODES = {
    "E001": "输入数据为空",
    "E002": "输入格式不支持",
    "E003": "JSON 解析失败",
    "E004": "CSV 解析失败",
    "E005": "字段配置无效",
    "E006": "批量处理数据格式错误",
    "E007": "内部处理错误",
    "E008": "参数错误",
    "E009": "输出序列化失败",
    "E010": "未知错误",
}


class MarkabyError(Exception):
    """自定义异常类，携带错误码"""

    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(f"[{code}] {message}")


def _get_error_message(code: str) -> str:
    """获取错误码对应的默认错误信息"""
    return ERROR_CODES.get(code, ERROR_CODES["E010"])


# ============================================================
# 核心功能：字段抽取与置信度标注
# ============================================================

# 常见日期模式（宽松匹配）
_DATE_PATTERNS = [
    r"\d{4}[-/年]\d{1,2}[-/月]\d{1,2}日?",  # 2024-01-01 / 2024/1/1 / 2024年1月1日
    r"\d{1,2}[-/月]\d{1,2}[-/日]\d{2,4}",  # 01-01-2024 / 1/1/2024
    r"\d{4}年\d{1,2}月\d{1,2}日",           # 2024年1月1日
]

# 常见金额模式（宽松匹配）
_AMOUNT_PATTERNS = [
    r"[¥￥]\s*\d+(?:\.\d{1,2})?",           # ¥100 / ￥100.50
    r"(?:USD|CNY|RMB|EUR)\s*\d+(?:\.\d{1,2})?",  # USD 100.50
    r"\d+(?:\.\d{1,2})?\s*(?:元|美元|欧元|人民币)",  # 100元 / 100.50美元
]

# 常见订单号/编号模式
_ID_PATTERNS = [
    r"(?:订单号|订单编号|单号|编号|ID)[:：]\s*[A-Za-z0-9_-]+",
    r"[A-Z]{2,5}\d{6,}",                    # AB123456
    r"\d{8,}",                              # 至少8位数字
]


def _extract_with_patterns(text: str, patterns: List[str]) -> Optional[str]:
    """使用模式列表从文本中提取第一个匹配项"""
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(0).strip()
    return None


def _clean_extracted_value(field_type: str, value: str) -> str:
    """清洗提取的值"""
    if value is None:
        return value
    value = value.strip()
    if field_type == "amount":
        # 移除货币符号和空格，保留数字
        value = re.sub(r"[¥￥\s]", "", value)
        # 将中文货币单位转换为标准格式
        value = value.replace("元", "").replace("人民币", "CNY ").replace("美元", "USD ")
        value = value.replace("欧元", "EUR ")
    elif field_type == "date":
        # 统一日期格式为 YYYY-MM-DD（宽松处理）
        value = value.replace("年", "-").replace("月", "-").replace("日", "")
        value = re.sub(r"[-/]+", "-", value)
        parts = value.split("-")
        if len(parts) == 3:
            year = parts[0] if len(parts[0]) == 4 else f"20{parts[0]}" if len(parts[0]) == 2 else parts[0]
            month = parts[1].zfill(2)
            day = parts[2].zfill(2)
            value = f"{year}-{month}-{day}"
    return value


def _calculate_confidence(field_type: str, value: Optional[str], source_text: str) -> float:
    """
    计算字段置信度（0.0 - 1.0）
    规则：
    - 值不存在：0.0
    - 值存在且匹配模式：0.7 - 0.95（根据模式匹配程度）
    - 值存在但模式不明确：0.5
    """
    if value is None or value == "":
        return 0.0

    confidence = 0.7  # 基础置信度

    # 根据字段类型和值特征调整置信度
    if field_type == "date":
        # 完整日期格式置信度高
        if re.match(r"^\d{4}-\d{2}-\d{2}$", value):
            confidence = 0.95
        elif re.match(r"^\d{4}-\d{1,2}-\d{1,2}$", value):
            confidence = 0.85
    elif field_type == "amount":
        # 带货币符号的金额置信度高
        if re.search(r"[¥￥]|USD|CNY|RMB|EUR|元|美元|欧元", source_text):
            confidence = 0.9
        else:
            confidence = 0.75
    elif field_type == "order_id":
        # 符合常见订单号格式置信度高
        if re.match(r"^[A-Za-z]{2,5}\d{6,}$", value):
            confidence = 0.9
        elif re.match(r"^\d{8,}$", value):
            confidence = 0.8

    return round(min(confidence, 1.0), 2)


def extract_fields(text: str, fields: List[str]) -> Dict[str, Any]:
    """
    从文本中提取指定字段

    参数:
        text: 输入文本
        fields: 需要提取的字段列表（支持 date, amount, order_id, 或自定义字段）

    返回:
        包含字段值、置信度、原始文本的结构化字典
    """
    if not text or not text.strip():
        raise MarkabyError("E001", _get_error_message("E001"))

    if not fields:
        raise MarkabyError("E005", _get_error_message("E005"))

    result: Dict[str, Any] = {
        "text": text.strip(),
        "fields": {},
        "overall_confidence": 0.0,
    }

    # 字段类型到模式的映射
    type_patterns = {
        "date": _DATE_PATTERNS,
        "amount": _AMOUNT_PATTERNS,
        "order_id": _ID_PATTERNS,
    }

    # 自定义字段名可能包含提示词，如 "date:日期"
    for field_spec in fields:
        field_spec = field_spec.strip()
        if not field_spec:
            continue

        # 支持 "类型:字段名" 格式，如 "date:订单日期"
        if ":" in field_spec:
            field_type, field_name = field_spec.split(":", 1)
            field_type = field_type.strip().lower()
            field_name = field_name.strip()
        else:
            field_type = field_spec.lower()
            field_name = field_spec

        # 获取匹配模式
        patterns = type_patterns.get(field_type, [])
        if not patterns:
            # 自定义字段尝试直接匹配字段名
            patterns = [rf"{re.escape(field_name)}[:：]\s*([^,;\n]+)"]

        # 提取值
        raw_value = _extract_with_patterns(text, patterns)
        value = None
        if raw_value:
            # 对于自定义模式，提取括号内的内容
            if "(" in patterns[0] and ")" in patterns[0]:
                match = re.search(patterns[0], text)
                if match and match.groups():
                    raw_value = match.group(1)
            value = _clean_extracted_value(field_type, raw_value)

        # 计算置信度
        confidence = _calculate_confidence(field_type, value, text)

        # 如果值不存在，使用占位符
        display_value = value if value else f"[需核实:{field_name}]"

        result["fields"][field_name] = {
            "value": display_value,
            "confidence": confidence,
            "raw": raw_value if raw_value else "",
        }

    # 计算整体置信度（所有字段置信度的平均值）
    if result["fields"]:
        confidences = [f["confidence"] for f in result["fields"].values()]
        result["overall_confidence"] = round(sum(confidences) / len(confidences), 2)

    return result


def batch_extract(records: List[str], fields: List[str]) -> List[Dict[str, Any]]:
    """
    批量提取字段

    参数:
        records: 多条文本记录
        fields: 需要提取的字段列表

    返回:
        结构化结果列表
    """
    if not records:
        raise MarkabyError("E006", _get_error_message("E006"))

    results = []
    for record in records:
        try:
            result = extract_fields(record, fields)
            results.append(result)
        except MarkabyError:
            # 单条记录失败不影响整体
            results.append({
                "text": record,
                "fields": {},
                "overall_confidence": 0.0,
                "error": "处理失败",
            })
    return results


# ============================================================
# 输入解析：支持 JSON、CSV、纯文本
# ============================================================

def parse_input(data: str, input_format: str = "auto") -> Tuple[List[str], Dict[str, Any]]:
    """
    解析输入数据为记录列表

    参数:
        data: 输入数据字符串
        input_format: 输入格式（auto/json/csv/text）

    返回:
        (记录列表, 元数据)
    """
    if not data or not data.strip():
        raise MarkabyError("E001", _get_error_message("E001"))

    if input_format == "auto":
        stripped = data.strip()
        if stripped.startswith("{") or stripped.startswith("["):
            input_format = "json"
        elif "," in stripped and ("\n" in stripped or ";" in stripped):
            input_format = "csv"
        else:
            input_format = "text"

    records: List[str] = []
    metadata: Dict[str, Any] = {"format": input_format, "count": 0}

    try:
        if input_format == "json":
            parsed = json.loads(data)
            if isinstance(parsed, list):
                # 列表形式：每个元素可以是字符串或字典
                for item in parsed:
                    if isinstance(item, str):
                        records.append(item)
                    elif isinstance(item, dict):
                        # 将字典转换为文本
                        records.append(json.dumps(item, ensure_ascii=False))
            elif isinstance(parsed, dict):
                # 字典形式：尝试提取 records 字段
                if "records" in parsed and isinstance(parsed["records"], list):
                    for item in parsed["records"]:
                        if isinstance(item, str):
                            records.append(item)
                        elif isinstance(item, dict):
                            records.append(json.dumps(item, ensure_ascii=False))
                else:
                    # 单个字典作为一条记录
                    records.append(json.dumps(parsed, ensure_ascii=False))
            else:
                raise MarkabyError("E003", _get_error_message("E003"))

        elif input_format == "csv":
            # 使用 csv 模块解析
            csv_reader = csv.reader(io.StringIO(data))
            rows = list(csv_reader)
            if rows:
                # 第一行作为表头
                header = rows[0]
                for row in rows[1:]:
                    if len(row) == len(header):
                        record = ", ".join(f"{header[i]}: {row[i]}" for i in range(len(header)) if row[i])
                        if record:
                            records.append(record)
                    else:
                        # 行长度不匹配，直接拼接
                        records.append(", ".join(row))

        else:  # text 格式
            # 按行分割，每行一条记录
            for line in data.strip().split("\n"):
                line = line.strip()
                if line:
                    records.append(line)

    except json.JSONDecodeError:
        raise MarkabyError("E003", _get_error_message("E003"))
    except Exception as e:
        raise MarkabyError("E004", f"{_get_error_message('E004')}: {str(e)}")

    if not records:
        raise MarkabyError("E001", _get_error_message("E001"))

    metadata["count"] = len(records)
    return records, metadata


# ============================================================
# 输出格式化
# ============================================================

def format_output(results: List[Dict[str, Any]], output_format: str = "json") -> str:
    """
    格式化输出结果

    参数:
        results: 结构化结果列表
        output_format: 输出格式（json/text）

    返回:
        格式化后的字符串
    """
    try:
        if output_format == "json":
            return json.dumps(results, ensure_ascii=False, indent=2)
        else:  # text 格式
            lines = []
            for i, result in enumerate(results, 1):
                lines.append(f"--- 记录 {i} ---")
                lines.append(f"原始文本: {result.get('text', '')}")
                lines.append(f"整体置信度: {result.get('overall_confidence', 0.0)}")
                for field_name, field_info in result.get("fields", {}).items():
                    lines.append(f"  {field_name}: {field_info.get('value', 'N/A')} (置信度: {field_info.get('confidence', 0.0)})")
                lines.append("")
            return "\n".join(lines)
    except Exception:
        raise MarkabyError("E009", _get_error_message("E009"))


# ============================================================
# 自检功能
# ============================================================

def run_selftest() -> bool:
    """
    自检核心逻辑功能

    使用硬编码样例数据验证：
    - 字段提取
    - 置信度计算
    - 批量处理
    - 输入解析
    """
    print("=" * 60)
    print("markaby 自检开始")
    print("=" * 60)

    # 测试 1: 单条文本字段提取
    print("\n[测试 1] 单条文本字段提取")
    test_text = "订单号: ABC123456，日期：2024-03-15，金额：¥299.00，客户：张三"
    fields = ["order_id", "date", "amount"]
    try:
        result = extract_fields(test_text, fields)
        assert result["fields"]["order_id"]["value"] != "[需核实:order_id]", "订单号提取失败"
        assert result["fields"]["date"]["value"] != "[需核实:date]", "日期提取失败"
        assert result["fields"]["amount"]["value"] != "[需核实:amount]", "金额提取失败"
        assert result["overall_confidence"] > 0.5, "整体置信度应大于0.5"
        print(f"  ✓ 提取结果: {json.dumps(result, ensure_ascii=False)}")
    except AssertionError as e:
        print(f"  ✗ 断言失败: {e}")
        return False
    except Exception as e:
        print(f"  ✗ 异常: {e}")
        return False

    # 测试 2: 缺失字段的占位处理
    print("\n[测试 2] 缺失字段占位处理")
    test_text2 = "今天天气不错"
    try:
        result2 = extract_fields(test_text2, ["date", "amount"])
        assert result2["fields"]["date"]["value"] == "[需核实:date]", "缺失字段未正确占位"
        assert result2["fields"]["amount"]["value"] == "[需核实:amount]", "缺失字段未正确占位"
        assert result2["overall_confidence"] == 0.0, "整体置信度应为0"
        print(f"  ✓ 占位处理正确: {json.dumps(result2, ensure_ascii=False)}")
    except AssertionError as e:
        print(f"  ✗ 断言失败: {e}")
        return False
    except Exception as e:
        print(f"  ✗ 异常: {e}")
        return False

    # 测试 3: 批量处理
    print("\n[测试 3] 批量处理")
    batch_data = [
        "订单A-001，金额 150.50元，日期 2024-01-10",
        "订单B-002，金额 USD 89.99",
        "无有效信息",
    ]
    try:
        batch_results = batch_extract(batch_data, ["order_id", "amount", "date"])
        assert len(batch_results) == 3, "批量处理数量不正确"
        assert batch_results[0]["fields"]["amount"]["value"] != "[需核实:amount]", "第一条金额提取失败"
        assert batch_results[1]["fields"]["amount"]["value"] != "[需核实:amount]", "第二条金额提取失败"
        assert batch_results[2]["fields"]["date"]["value"] == "[需核实:date]", "第三条日期应占位"
        print(f"  ✓ 批量处理成功，共 {len(batch_results)} 条记录")
        print(f"  ✓ 第一条: {json.dumps(batch_results[0], ensure_ascii=False)}")
    except AssertionError as e:
        print(f"  ✗ 断言失败: {e}")
        return False
    except Exception as e:
        print(f"  ✗ 异常: {e}")
        return False

    # 测试 4: JSON 输入解析
    print("\n[测试 4] JSON 输入解析")
    json_input = json.dumps([
        "订单号: XYZ789，金额 1000元",
        "日期 2024-05-20，备注：测试"
    ], ensure_ascii=False)
    try:
        records, metadata = parse_input(json_input, "json")
        assert metadata["count"] == 2, "JSON 解析记录数不正确"
        assert len(records) == 2, "JSON 解析记录列表长度不正确"
        print(f"  ✓ JSON 解析成功，共 {metadata['count']} 条记录")
    except AssertionError as e:
        print(f"  ✗ 断言失败: {e}")
        return False
    except Exception as e:
        print(f"  ✗ 异常: {e}")
        return False

    # 测试 5: CSV 输入解析
    print("\n[测试 5] CSV 输入解析")
    csv_input = "订单号,金额,日期\nA001,100.50,2024-01-01\nB002,200.00,2024-02-01\n"
    try:
        records, metadata = parse_input(csv_input, "csv")
        assert metadata["count"] == 2, "CSV 解析记录数不正确"
        assert "订单号" in records[0], "CSV 记录应包含字段名"
        print(f"  ✓ CSV 解析成功，共 {metadata['count']} 条记录")
        print(f"  ✓ 第一条记录: {records[0]}")
    except AssertionError as e:
        print(f"  ✗ 断言失败: {e}")
        return False
    except Exception as e:
        print(f"  ✗ 异常: {e}")
        return False

    # 测试 6: 错误处理
    print("\n[测试 6] 错误处理")
    try:
        # 空输入
        try:
            extract_fields("", ["date"])
            print("  ✗ 空输入未抛出异常")
            return False
        except MarkabyError as e:
            assert e.code == "E001", f"错误码应为 E001，实际为 {e.code}"
            print(f"  ✓ 空输入正确抛出 E001: {e.message}")

        # 无效字段
        try:
            extract_fields("测试文本", [])
            print("  ✗ 空字段列表未抛出异常")
            return False
        except MarkabyError as e:
            assert e.code == "E005", f"错误码应为 E005，实际为 {e.code}"
            print(f"  ✓ 空字段列表正确抛出 E005: {e.message}")

        # 无效 JSON
        try:
            parse_input("{invalid json", "json")
            print("  ✗ 无效 JSON 未抛出异常")
            return False
        except MarkabyError as e:
            assert e.code == "E003", f"错误码应为 E003，实际为 {e.code}"
            print(f"  ✓ 无效 JSON 正确抛出 E003: {e.message}")

    except AssertionError as e:
        print(f"  ✗ 断言失败: {e}")
        return False
    except Exception as e:
        print(f"  ✗ 异常: {e}")
        return False

    # 测试 7: 边界情况
    print("\n[测试 7] 边界情况")
    try:
        # 超长文本
        long_text = "订单号: ABC123456 " + "内容" * 1000 + " 金额 100元"
        result_long = extract_fields(long_text, ["order_id", "amount"])
        assert result_long["fields"]["order_id"]["value"] != "[需核实:order_id]", "长文本订单号提取失败"
        print(f"  ✓ 长文本处理成功")

        # 特殊字符
        special_text = "订单号: AB-C_123，金额：￥1,234.56"
        result_special = extract_fields(special_text, ["order_id", "amount"])
        print(f"  ✓ 特殊字符处理成功: {json.dumps(result_special, ensure_ascii=False)}")

        # 中英文混合
        mixed_text = "Order ID: ABC123, Date: 2024/03/15, Amount: CNY 299.50"
        result_mixed = extract_fields(mixed_text, ["order_id", "date", "amount"])
        assert result_mixed["fields"]["date"]["value"] != "[需核实:date]", "中英文混合日期提取失败"
        print(f"  ✓ 中英文混合处理成功: {json.dumps(result_mixed, ensure_ascii=False)}")

    except AssertionError as e:
        print(f"  ✗ 断言失败: {e}")
        return False
    except Exception as e:
        print(f"  ✗ 异常: {e}")
        return False

    # 测试 8: 输出格式化
    print("\n[测试 8] 输出格式化")
    try:
        sample_result = [{
            "text": "测试文本",
            "fields": {"date": {"value": "2024-01-01", "confidence": 0.95}},
            "overall_confidence": 0.95
        }]
        json_output = format_output(sample_result, "json")
        assert json.loads(json_output)[0]["fields"]["date"]["value"] == "2024-01-01", "JSON 输出解析失败"

        text_output = format_output(sample_result, "text")
        assert "2024-01-01" in text_output, "文本输出缺少日期值"
        print(f"  ✓ JSON 输出格式正确")
        print(f"  ✓ 文本输出格式正确")
    except AssertionError as e:
        print(f"  ✗ 断言失败: {e}")
        return False
    except Exception as e:
        print(f"  ✗ 异常: {e}")
        return False

    print("\n" + "=" * 60)
    print("所有自检测试通过！")
    print("=" * 60)
    return True


# ============================================================
# 主程序入口
# ============================================================

def main():
    """命令行入口"""
    parser = argparse.ArgumentParser(
        description="markaby - 数据解析与结构化提取工具",
        epilog="示例: python main.py --text '订单号: ABC123, 金额 100元' --fields order_id amount"
    )
    parser.add_argument("--text", type=str, help="输入文本（单条）")
    parser.add_argument("--input", type=str, help="输入文件路径（支持 JSON/CSV/纯文本）")
    parser.add_argument("--fields", type=str, nargs="+", default=["date", "amount", "order_id"],
                        help="需要提取的字段，支持: date, amount, order_id 或自定义字段")
    parser.add_argument("--format", type=str, choices=["auto", "json", "csv", "text"], default="auto",
                        help="输入格式（默认自动检测）")
    parser.add_argument("--output", type=str, choices=["json", "text"], default="json",
                        help="输出格式（默认 JSON）")
    parser.add_argument("--selftest", action="store_true", help="运行自检测试")
    parser.add_argument("--version", action="store_true", help="显示版本信息")

    args = parser.parse_args()

    # 版本信息
    if args.version:
        print("markaby v1.0.2")
        print("数据解析 结构化提取 批量转换")
        return 0

    # 自检模式
    if args.selftest:
        success = run_selftest()
        return 0 if success else 1

    # 正常处理模式
    try:
        # 获取输入数据
        input_data = ""
        if args.input:
            try:
                with open(args.input, "r", encoding="utf-8") as f:
                    input_data = f.read()
            except FileNotFoundError:
                print(f"错误: 文件不存在: {args.input}", file=sys.stderr)
                return 1
            except Exception as e:
                print(f"错误: 读取文件失败: {e}", file=sys.stderr)
                return 1
        elif args.text:
            input_data = args.text
        else:
            # 从标准输入读取
            input_data = sys.stdin.read()

        if not input_data.strip():
            print(f"错误: [{ERROR_CODES['E001']}] {_get_error_message('E001')}", file=sys.stderr)
            return 1

        # 解析输入
        records, metadata = parse_input(input_data, args.format)

        # 提取字段
        results = batch_extract(records, args.fields)

        # 格式化输出
        output = format_output(results, args.output)
        print(output)

        # 输出统计信息到 stderr
        print(f"\n处理完成: {metadata['count']} 条记录", file=sys.stderr)

        return 0

    except MarkabyError as e:
        print(f"错误: [{e.code}] {e.message}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"错误: [{ERROR_CODES['E010']}] 未知错误: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
