#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
okf-skills 技能实现脚本
功能：数据整理、信息抽取、结构化输出，附置信度标注。
本脚本为 clean-room 独立实现，仅依据功能规格编写。
"""

import sys
import json
import re
import argparse
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

# 错误码定义
ERROR_CODES = {
    "E001": "输入数据为空或格式不正确",
    "E002": "输入数据不是字符串或字典",
    "E003": "无法从输入中解析出任何有效字段",
    "E004": "输出格式指定错误（仅支持 json/yaml/table）",
    "E005": "批量处理时输入必须为列表",
    "E006": "自定义字段列表为空或格式错误",
    "E007": "日期解析失败",
    "E008": "数值解析失败",
    "E009": "内部逻辑错误（不应发生）",
    "E010": "参数组合错误",
}


class OKFError(Exception):
    """技能自定义异常，携带错误码。"""

    def __init__(self, code: str, message: str = ""):
        self.code = code
        self.message = message or ERROR_CODES.get(code, "未知错误")
        super().__init__(f"[{code}] {self.message}")


# ---------- 核心功能：数据解析 ----------

def _extract_text(data: Any) -> str:
    """从输入数据中提取纯文本内容。支持字符串、字典（取message/text/content字段）。"""
    if isinstance(data, str):
        return data
    if isinstance(data, dict):
        # 优先取常见文本字段
        for key in ("text", "content", "message", "data", "input"):
            if key in data and isinstance(data[key], str):
                return data[key]
        # 若没有字符串字段，尝试 JSON 序列化
        try:
            return json.dumps(data, ensure_ascii=False)
        except Exception:
            raise OKFError("E002", "输入字典无法序列化为文本")
    raise OKFError("E002", "输入必须为字符串或字典")


def _parse_json_if_possible(text: str) -> Optional[Dict[str, Any]]:
    """尝试将文本解析为 JSON 对象。"""
    text = text.strip()
    if not text:
        return None
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
        return None
    except Exception:
        return None


def _find_dates(text: str) -> List[Dict[str, Any]]:
    """从文本中查找日期信息，返回带置信度的日期列表。"""
    dates = []
    # 匹配常见日期格式：YYYY-MM-DD, YYYY/MM/DD, YYYY年MM月DD日
    patterns = [
        r"(\d{4})[-/年](\d{1,2})[-/月](\d{1,2})日?",
        r"(\d{4})年(\d{1,2})月(\d{1,2})日",
    ]
    for pattern in patterns:
        for match in re.finditer(pattern, text):
            year, month, day = int(match.group(1)), int(match.group(2)), int(match.group(3))
            # 宽松校验月份和日期范围
            if 1 <= month <= 12 and 1 <= day <= 31:
                dates.append({
                    "value": f"{year:04d}-{month:02d}-{day:02d}",
                    "confidence": "high",
                    "original": match.group(0),
                })
    return dates


def _extract_emails(text: str) -> List[str]:
    """从文本中提取邮箱地址。"""
    pattern = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
    return list(set(re.findall(pattern, text)))


def _extract_phones(text: str) -> List[str]:
    """从文本中提取中国手机号（11位，1开头）。"""
    pattern = r"1[3-9]\d{9}"
    return list(set(re.findall(pattern, text)))


def _extract_numbers(text: str) -> List[Dict[str, Any]]:
    """提取文本中的数值（整数或小数），附置信度。"""
    numbers = []
    pattern = r"-?\d+(?:\.\d+)?"
    for match in re.finditer(pattern, text):
        raw = match.group(0)
        try:
            value = float(raw)
            # 排除年份和日期中的数字（避免重复）
            if 1900 <= value <= 2100 and len(raw) == 4:
                continue
            numbers.append({
                "value": value,
                "confidence": "high" if "." in raw else "medium",
                "original": raw,
            })
        except ValueError:
            continue
    return numbers


def _extract_key_value_pairs(text: str) -> Dict[str, Any]:
    """尝试提取 key: value 或 key=value 形式的字段。"""
    result = {}
    patterns = [
        r"([\w\u4e00-\u9fff]+)\s*[:：]\s*([^\n,;，；]+)",
        r"([\w\u4e00-\u9fff]+)\s*=\s*([^\n,;，；]+)",
    ]
    for pattern in patterns:
        for match in re.finditer(pattern, text):
            key = match.group(1).strip()
            value = match.group(2).strip()
            if key and value and len(key) <= 20:
                result[key] = value
    return result


def _analyze_confidence(data: Dict[str, Any]) -> str:
    """根据字段完整度计算整体置信度。"""
    if not data:
        return "low"
    fields = len(data)
    if fields >= 4:
        return "high"
    if fields >= 2:
        return "medium"
    return "low"


# ---------- 核心功能：结构化输出 ----------

def _format_json(data: Dict[str, Any]) -> str:
    """格式化为 JSON 字符串。"""
    return json.dumps(data, ensure_ascii=False, indent=2)


def _format_yaml(data: Dict[str, Any]) -> str:
    """格式化为 YAML 风格字符串（简化实现）。"""
    lines = []

    def _serialize(obj: Any, indent: int = 0) -> None:
        prefix = " " * indent
        if isinstance(obj, dict):
            for key, value in obj.items():
                if isinstance(value, (dict, list)):
                    lines.append(f"{prefix}{key}:")
                    _serialize(value, indent + 2)
                else:
                    lines.append(f"{prefix}{key}: {value}")
        elif isinstance(obj, list):
            for item in obj:
                if isinstance(item, (dict, list)):
                    lines.append(f"{prefix}-")
                    _serialize(item, indent + 2)
                else:
                    lines.append(f"{prefix}- {item}")

    _serialize(data)
    return "\n".join(lines)


def _format_table(data: Dict[str, Any]) -> str:
    """格式化为简单表格（支持嵌套结构）。"""
    if not isinstance(data, dict):
        raise OKFError("E004", "表格格式仅支持字典")

    # 将嵌套结构展平为可读的字符串
    def _flatten_value(value: Any) -> str:
        if isinstance(value, dict):
            # 对于字典，转换为 key: value 格式
            items = []
            for k, v in value.items():
                if isinstance(v, (dict, list)):
                    items.append(f"{k}: {_flatten_value(v)}")
                else:
                    items.append(f"{k}: {v}")
            return "{" + ", ".join(items) + "}"
        elif isinstance(value, list):
            # 对于列表，转换为逗号分隔
            items = []
            for item in value:
                if isinstance(item, (dict, list)):
                    items.append(_flatten_value(item))
                else:
                    items.append(str(item))
            return "[" + ", ".join(items) + "]"
        else:
            return str(value)

    if not data:
        return "(空)"

    # 准备表格行
    rows = []
    for key, value in data.items():
        if key == "_meta":
            continue  # 跳过元信息
        rows.append((str(key), _flatten_value(value)))

    if not rows:
        return "(无数据字段)"

    # 计算列宽
    col1_width = max(len(row[0]) for row in rows) + 2
    col2_width = max(len(row[1]) for row in rows) + 2
    col2_width = min(col2_width, 80)  # 限制最大宽度

    # 构建表格
    lines = []
    lines.append(f"+{'-' * col1_width}+{'-' * col2_width}+")
    for key, value in rows:
        # 处理长值换行
        if len(value) > col2_width - 2:
            # 截断并添加省略号
            value = value[:col2_width - 5] + "..."
        lines.append(f"| {key.ljust(col1_width - 1)}| {value.ljust(col2_width - 1)}|")
    lines.append(f"+{'-' * col1_width}+{'-' * col2_width}+")
    return "\n".join(lines)


def _format_output(data: Dict[str, Any], fmt: str) -> str:
    """根据指定格式输出。"""
    fmt = fmt.lower()
    if fmt == "json":
        return _format_json(data)
    if fmt == "yaml":
        return _format_yaml(data)
    if fmt == "table":
        return _format_table(data)
    raise OKFError("E004", f"不支持的输出格式: {fmt}")


# ---------- 主处理逻辑 ----------

def process_single(data: Any, output_format: str = "json", custom_fields: Optional[List[str]] = None) -> Dict[str, Any]:
    """处理单条数据，返回结构化结果。"""
    # 参数校验
    if not data:
        raise OKFError("E001")
    if output_format not in ("json", "yaml", "table"):
        raise OKFError("E004")

    # 提取文本
    text = _extract_text(data)

    # 尝试 JSON 解析
    parsed_json = _parse_json_if_possible(text)

    # 提取各类字段
    result: Dict[str, Any] = {}

    # 日期
    dates = _find_dates(text)
    if dates:
        result["dates"] = dates

    # 邮箱
    emails = _extract_emails(text)
    if emails:
        result["emails"] = emails

    # 手机号
    phones = _extract_phones(text)
    if phones:
        result["phones"] = phones

    # 数值
    numbers = _extract_numbers(text)
    if numbers:
        result["numbers"] = numbers

    # key-value 对
    kv_pairs = _extract_key_value_pairs(text)
    if kv_pairs:
        result["fields"] = kv_pairs

    # 如果输入是 JSON 对象，合并其字段
    if parsed_json:
        for key, value in parsed_json.items():
            if key not in result:
                result[key] = value

    # 自定义字段过滤
    if custom_fields:
        filtered = {}
        for field in custom_fields:
            if field in result:
                filtered[field] = result[field]
            # 也尝试在 fields 子字典中查找
            elif "fields" in result and field in result["fields"]:
                filtered[field] = result["fields"][field]
        if filtered:
            result = filtered
        # 若没有匹配字段，保留原结果但标记
        if not result:
            result["_warning"] = "自定义字段均未匹配"

    # 若什么都没有提取到
    if not result:
        raise OKFError("E003")

    # 添加元信息
    result["_meta"] = {
        "processed_at": datetime.now().isoformat(),
        "input_type": "text" if isinstance(data, str) else "dict",
        "overall_confidence": _analyze_confidence(result),
        "field_count": len(result),
    }

    return result


def process_batch(data: List[Any], output_format: str = "json", custom_fields: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """批量处理多条数据。"""
    if not isinstance(data, list):
        raise OKFError("E005")
    results = []
    for item in data:
        try:
            results.append(process_single(item, output_format, custom_fields))
        except OKFError as e:
            results.append({
                "_error": {"code": e.code, "message": e.message},
                "_meta": {"overall_confidence": "low", "field_count": 0},
            })
    return results


# ---------- 自测函数 ----------

def _run_selftest() -> int:
    """内置硬编码数据自检核心逻辑，不依赖外部文件。"""
    print("=== okf-skills 自检开始 ===")

    # 测试样例 1：文本数据
    sample_text = """
    会议纪要：2026年3月15日，张三（zhangsan@example.com）负责项目A，
    预算约 5000 元，联系电话 13812345678。下次会议 2026/04/01。
    """
    try:
        result = process_single(sample_text, "json")
        assert "dates" in result, "日期提取失败"
        assert len(result["dates"]) >= 1, "至少提取 1 个日期"
        assert "emails" in result, "邮箱提取失败"
        assert "phones" in result, "手机号提取失败"
        assert "numbers" in result, "数值提取失败"
        assert result["_meta"]["overall_confidence"] in ("high", "medium"), "置信度异常"
        print("[PASS] 文本数据解析")
    except AssertionError as e:
        print(f"[FAIL] 文本数据解析: {e}")
        return 1

    # 测试样例 2：字典数据
    sample_dict = {
        "title": "客户反馈",
        "content": "用户提到价格是 299 元，日期 2026-05-20，邮箱 service@shop.com",
        "priority": "high",
    }
    try:
        result = process_single(sample_dict, "yaml")
        assert "emails" in result, "字典数据邮箱提取失败"
        assert "dates" in result, "字典数据日期提取失败"
        assert result["_meta"]["input_type"] == "dict", "输入类型识别错误"
        print("[PASS] 字典数据解析")
    except AssertionError as e:
        print(f"[FAIL] 字典数据解析: {e}")
        return 1

    # 测试样例 3：批量处理
    batch_data = [
        "订单 2026-01-10，金额 1200 元",
        {"text": "联系人：李四，电话 13900001111", "note": "重要客户"},
    ]
    try:
        results = process_batch(batch_data, "json")
        assert len(results) == 2, "批量处理数量错误"
        assert results[0]["_meta"]["overall_confidence"] != "", "批量处理置信度为空"
        print("[PASS] 批量处理")
    except AssertionError as e:
        print(f"[FAIL] 批量处理: {e}")
        return 1

    # 测试样例 4：自定义字段
    try:
        result = process_single(sample_dict, "json", custom_fields=["emails", "dates"])
        assert "emails" in result, "自定义字段过滤失败"
        assert "priority" not in result, "自定义字段过滤未生效"
        print("[PASS] 自定义字段")
    except AssertionError as e:
        print(f"[FAIL] 自定义字段: {e}")
        return 1

    # 测试样例 5：输出格式
    try:
        # 测试表格格式
        result = process_single(sample_text, "table")
        assert "|" in result, "表格格式输出失败"
        assert "+" in result, "表格边框缺失"
        
        # 测试 YAML 格式
        result = process_single(sample_text, "yaml")
        assert "dates:" in result, "YAML 格式输出失败"
        
        # 测试 JSON 格式
        result = process_single(sample_text, "json")
        assert isinstance(json.loads(result), dict), "JSON 格式输出失败"
        
        print("[PASS] 输出格式")
    except AssertionError as e:
        print(f"[FAIL] 输出格式: {e}")
        return 1

    # 测试样例 6：错误处理
    try:
        process_single("", "json")
        print("[FAIL] 空输入未报错")
        return 1
    except OKFError as e:
        assert e.code == "E001", f"错误码应为 E001，实际 {e.code}"
        print("[PASS] 错误处理")

    # 测试样例 7：JSON 输入
    json_input = '{"name": "测试", "amount": 88, "note": "2026-02-14"}'
    try:
        result = process_single(json_input, "json")
        assert "name" in result, "JSON 字段解析失败"
        assert "dates" in result, "JSON 中日期提取失败"
        print("[PASS] JSON 字符串解析")
    except AssertionError as e:
        print(f"[FAIL] JSON 字符串解析: {e}")
        return 1

    # 测试样例 8：无匹配字段
    try:
        result = process_single("没有特殊内容的普通文本", "json")
        # 可能提取到 numbers 或什么都提取不到
        assert "_meta" in result, "元信息缺失"
        print("[PASS] 普通文本处理")
    except OKFError as e:
        assert e.code == "E003", f"应返回 E003，实际 {e.code}"
        print("[PASS] 无匹配字段处理")

    print("=== 全部自检通过 ===")
    return 0


# ---------- 主入口 ----------

def main() -> int:
    """命令行入口。"""
    parser = argparse.ArgumentParser(
        description="okf-skills: 数据整理、信息抽取、结构化输出工具",
        epilog="示例: python main.py --input '文本内容' --format json",
    )
    parser.add_argument("--input", "-i", type=str, help="输入文本或 JSON 字符串")
    parser.add_argument("--file", "-f", type=str, help="从文件读取输入（每行一条记录，或 JSON 数组）")
    parser.add_argument("--format", "-o", type=str, default="json", choices=["json", "yaml", "table"], help="输出格式")
    parser.add_argument("--fields", "-c", type=str, help="自定义输出字段，逗号分隔")
    parser.add_argument("--batch", "-b", action="store_true", help="批量模式（输入为 JSON 数组）")
    parser.add_argument("--selftest", action="store_true", help="运行内置自检")
    parser.add_argument("--version", action="version", version="okf-skills 1.0.2")

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        return _run_selftest()

    # 参数校验
    if not args.input and not args.file:
        parser.error("必须提供 --input 或 --file 参数")

    # 解析自定义字段
    custom_fields = None
    if args.fields:
        custom_fields = [f.strip() for f in args.fields.split(",") if f.strip()]
        if not custom_fields:
            raise OKFError("E006")

    try:
        # 文件模式
        if args.file:
            with open(args.file, "r", encoding="utf-8") as f:
                content = f.read()
            # 尝试解析为 JSON 数组
            try:
                data = json.loads(content)
            except Exception:
                # 按行读取
                data = [line.strip() for line in content.splitlines() if line.strip()]
            if args.batch:
                if not isinstance(data, list):
                    raise OKFError("E005")
                results = process_batch(data, args.format, custom_fields)
            else:
                if isinstance(data, list) and len(data) > 1:
                    results = process_batch(data, args.format, custom_fields)
                else:
                    item = data[0] if isinstance(data, list) else data
                    results = process_single(item, args.format, custom_fields)
        # 输入模式
        else:
            if args.batch:
                # 尝试解析为 JSON 数组
                try:
                    data = json.loads(args.input)
                    if not isinstance(data, list):
                        raise OKFError("E005")
                except json.JSONDecodeError:
                    # 按行拆分
                    data = [line.strip() for line in args.input.splitlines() if line.strip()]
                results = process_batch(data, args.format, custom_fields)
            else:
                results = process_single(args.input, args.format, custom_fields)

        # 输出结果
        if isinstance(results, list):
            output_data = {"results": results, "count": len(results)}
        else:
            output_data = results

        print(_format_output(output_data, args.format))
        return 0

    except OKFError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"未预期错误: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
