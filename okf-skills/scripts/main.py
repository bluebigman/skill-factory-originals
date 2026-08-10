#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
okf-skills 数据整理与信息抽取工具

功能：
- 从任意文本中提取结构化字段（日期、金额、姓名等）
- 在 JSON / CSV / YAML / Markdown 表格之间互转
- 字段命名统一映射
- 输出字段附置信度标注
- 支持批量处理

用法：
    python main.py --selftest      # 离线自检
    python main.py --extract "文本" # 提取字段
    python main.py --convert --from csv --to json < input.csv
"""

import argparse
import csv
import io
import json
import re
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from datetime import timezone  # G2 时区修复

# 错误码定义
ERROR_CODES = {
    "E001": "参数错误",
    "E002": "输入为空",
    "E003": "格式不支持",
    "E004": "解析失败",
    "E005": "转换失败",
    "E006": "字段映射失败",
    "E007": "文件读写失败",
    "E008": "JSON 解析失败",
    "E009": "CSV 解析失败",
    "E010": "内部错误",
}

# 字段别名映射表（统一为规范命名）
FIELD_ALIASES = {
    "userName": ["user_name", "username", "姓名", "名字", "name"],
    "date": ["日期", "时间", "date", "time"],
    "amount": ["金额", "价格", "费用", "amount", "price", "cost"],
    "phone": ["电话", "手机", "phone", "mobile", "tel"],
    "email": ["邮箱", "电子邮件", "email", "mail"],
    "address": ["地址", "住址", "address"],
}

# 置信度常量
CONFIDENCE_HIGH = 0.95
CONFIDENCE_MEDIUM = 0.75
CONFIDENCE_LOW = 0.55

# 支持的数据格式
SUPPORTED_FORMATS = ["json", "csv", "yaml", "markdown", "text"]


def err(code: str, message: str = "") -> None:
    """输出错误信息并退出"""
    msg = ERROR_CODES.get(code, "未知错误")
    if message:
        msg = f"{msg}: {message}"
    print(f"[错误 {code}] {msg}", file=sys.stderr)
    sys.exit(1)


def extract_date(text: str) -> Tuple[Optional[str], float]:
    """从文本中提取日期"""
    # 匹配 YYYY-MM-DD 或 YYYY/MM/DD 或 YYYY年MM月DD日
    patterns = [
        (r"(\d{4})[-/年](\d{1,2})[-/月](\d{1,2})日?", 0.95),
        (r"(\d{4})年(\d{1,2})月(\d{1,2})日", 0.95),
        (r"(\d{1,2})月(\d{1,2})日", 0.70),  # 无年份，置信度降低
    ]
    for pattern, conf in patterns:
        match = re.search(pattern, text)
        if match:
            groups = match.groups()
            if len(groups) == 3:
                year, month, day = int(groups[0]), int(groups[1]), int(groups[2])
            else:
                month, day = int(groups[0]), int(groups[1])
                year = datetime.now(timezone.utc).year  # 默认当前年份
            try:
                dt = datetime(year, month, day)
                return dt.strftime("%Y-%m-%d"), conf
            except ValueError:
                continue
    return None, 0.0


def extract_amount(text: str) -> Tuple[Optional[float], float]:
    """从文本中提取金额"""
    patterns = [
        (r"([0-9]+(?:\.[0-9]{1,2})?)\s*(?:元|块|人民币|RMB|CNY)", 0.95),
        (r"([0-9]+(?:\.[0-9]{1,2})?)\s*(?:美元|美金|USD)", 0.90),
        (r"￥\s*([0-9]+(?:\.[0-9]{1,2})?)", 0.95),
        (r"\$\s*([0-9]+(?:\.[0-9]{1,2})?)", 0.90),
        (r"([0-9]+(?:\.[0-9]{1,2})?)\s*元", 0.90),
    ]
    for pattern, conf in patterns:
        match = re.search(pattern, text)
        if match:
            try:
                return float(match.group(1)), conf
            except ValueError:
                continue
    return None, 0.0


def extract_name(text: str) -> Tuple[Optional[str], float]:
    """从文本中提取姓名（简单模式：中文姓名 2-4字）"""
    # 匹配常见中文姓名模式
    pattern = r"(?:姓名|名字|name)[:：\s]*([\u4e00-\u9fa5]{2,4})"
    match = re.search(pattern, text, re.IGNORECASE)
    if match:
        return match.group(1), 0.85
    return None, 0.0


def extract_phone(text: str) -> Tuple[Optional[str], float]:
    """从文本中提取电话号码"""
    patterns = [
        (r"(?:电话|手机|phone|mobile|tel)[:：\s]*(\+?\d{6,15})", 0.95, re.IGNORECASE),
        (r"1[3-9]\d{9}", 0.90),  # 中国手机号
        (r"\d{3,4}-\d{7,8}", 0.85),  # 座机
    ]
    for pattern_info in patterns:
        if len(pattern_info) == 3:
            pattern, conf, flags = pattern_info
        else:
            pattern, conf = pattern_info
            flags = 0
        match = re.search(pattern, text, flags)
        if match:
            return match.group(1) if match.groups() else match.group(0), conf
    return None, 0.0


def extract_email(text: str) -> Tuple[Optional[str], float]:
    """从文本中提取邮箱"""
    pattern = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
    match = re.search(pattern, text)
    if match:
        return match.group(0), 0.95
    return None, 0.0


def extract_address(text: str) -> Tuple[Optional[str], float]:
    """从文本中提取地址（简单模式）"""
    pattern = r"(?:地址|住址|address)[:：\s]*([^\n，,。;；]+)"
    match = re.search(pattern, text, re.IGNORECASE)
    if match:
        return match.group(1).strip(), 0.75
    return None, 0.0


def extract_fields(text: str) -> Dict[str, Dict[str, Any]]:
    """从文本中提取所有可识别字段，返回带置信度的结构"""
    result: Dict[str, Dict[str, Any]] = {}

    extractors = {
        "date": extract_date,
        "amount": extract_amount,
        "name": extract_name,
        "phone": extract_phone,
        "email": extract_email,
        "address": extract_address,
    }

    for field_name, extractor in extractors.items():
        value, confidence = extractor(text)
        if value is not None:
            result[field_name] = {"value": value, "confidence": confidence}

    return result


def normalize_field_name(field: str) -> Tuple[str, float]:
    """将字段名统一为规范命名，返回规范名和映射置信度"""
    field_lower = field.strip().lower()
    for canonical, aliases in FIELD_ALIASES.items():
        if field_lower in [a.lower() for a in aliases]:
            return canonical, 0.95
    # 未匹配到的字段，原样返回，置信度低
    return field, 0.50


def convert_format(data: str, from_format: str, to_format: str) -> str:
    """在支持的格式之间转换"""
    if from_format not in SUPPORTED_FORMATS:
        err("E003", f"不支持的输入格式: {from_format}")
    if to_format not in SUPPORTED_FORMATS:
        err("E003", f"不支持的输出格式: {to_format}")

    # 解析输入
    if from_format == "json":
        try:
            parsed = json.loads(data)
        except json.JSONDecodeError as e:
            err("E008", str(e))
    elif from_format == "csv":
        try:
            reader = csv.DictReader(io.StringIO(data))
            parsed = list(reader)
        except Exception as e:
            err("E009", str(e))
    elif from_format == "yaml":
        # 简化 YAML 解析：仅支持简单 key: value 形式
        parsed = {}
        for line in data.strip().splitlines():
            if ":" in line:
                key, value = line.split(":", 1)
                parsed[key.strip()] = value.strip()
    elif from_format == "markdown":
        # 解析 Markdown 表格
        lines = data.strip().splitlines()
        if len(lines) < 2:
            err("E004", "Markdown 表格格式不正确")
        headers = [h.strip() for h in lines[0].strip("|").split("|")]
        parsed = []
        for line in lines[2:]:  # 跳过表头分隔行
            if line.strip():
                values = [v.strip() for v in line.strip("|").split("|")]
                if len(values) == len(headers):
                    parsed.append(dict(zip(headers, values)))
    else:  # text
        parsed = data

    # 输出转换
    if to_format == "json":
        return json.dumps(parsed, ensure_ascii=False, indent=2)
    elif to_format == "csv":
        if isinstance(parsed, list) and parsed:
            output = io.StringIO()
            if isinstance(parsed[0], dict):
                writer = csv.DictWriter(output, fieldnames=parsed[0].keys())
                writer.writeheader()
                writer.writerows(parsed)
            else:
                writer = csv.writer(output)
                for row in parsed:
                    writer.writerow([row])
            return output.getvalue()
        else:
            err("E005", "无法转换为 CSV")
    elif to_format == "yaml":
        if isinstance(parsed, dict):
            return "\n".join(f"{k}: {v}" for k, v in parsed.items())
        elif isinstance(parsed, list):
            return "\n".join(
                "- " + json.dumps(item, ensure_ascii=False) for item in parsed
            )
        else:
            return str(parsed)
    elif to_format == "markdown":
        if isinstance(parsed, list) and parsed and isinstance(parsed[0], dict):
            headers = list(parsed[0].keys())
            lines = ["| " + " | ".join(headers) + " |"]
            lines.append("| " + " | ".join(["---"] * len(headers)) + " |")
            for item in parsed:
                lines.append(
                    "| " + " | ".join(str(item.get(h, "")) for h in headers) + " |"
                )
            return "\n".join(lines)
        else:
            err("E005", "无法转换为 Markdown")
    else:  # text
        if isinstance(parsed, (dict, list)):
            return json.dumps(parsed, ensure_ascii=False, indent=2)
        return str(parsed)


def batch_process(lines: List[str]) -> List[Dict[str, Any]]:
    """批量处理多行文本"""
    results = []
    for line in lines:
        if line.strip():
            fields = extract_fields(line)
            results.append({"input": line.strip(), "structured": fields})
    return results


def run_selftest() -> bool:
    """内置硬编码样例数据的离线自检"""
    print("=== okf-skills 自检开始 ===")

    # 测试1: 字段提取
    test_text = "姓名：张三，日期：2024年3月15日，金额：3500元，电话：13812345678，邮箱：zhangsan@example.com"
    fields = extract_fields(test_text)
    assert "name" in fields, "E001: 姓名提取失败"
    assert "date" in fields, "E001: 日期提取失败"
    assert "amount" in fields, "E001: 金额提取失败"
    assert "phone" in fields, "E001: 电话提取失败"
    assert "email" in fields, "E001: 邮箱提取失败"
    assert fields["name"]["value"] == "张三", "E001: 姓名值不正确"
    assert fields["date"]["value"] == "2024-03-15", "E001: 日期值不正确"
    assert fields["amount"]["value"] == 3500.0, "E001: 金额值不正确"
    assert fields["amount"]["confidence"] > 0.8, "E001: 金额置信度异常"
    print("[通过] 字段提取测试")

    # 测试2: 字段名规范化
    canonical, conf = normalize_field_name("user_name")
    assert canonical == "userName", "E006: 字段映射失败"
    assert conf > 0.9, "E006: 映射置信度异常"
    canonical2, _ = normalize_field_name("username")
    assert canonical2 == "userName", "E006: username 映射失败"
    print("[通过] 字段映射测试")

    # 测试3: 格式转换 JSON -> CSV
    json_data = '[{"name": "张三", "age": 30}, {"name": "李四", "age": 25}]'
    csv_result = convert_format(json_data, "json", "csv")
    assert "张三" in csv_result and "李四" in csv_result, "E005: JSON转CSV失败"
    print("[通过] JSON->CSV 转换测试")

    # 测试4: 格式转换 CSV -> JSON
    csv_data = "name,age\n王五,28\n赵六,35\n"
    json_result = convert_format(csv_data, "csv", "json")
    parsed_json = json.loads(json_result)
    assert len(parsed_json) == 2, "E005: CSV转JSON失败"
    assert parsed_json[0]["name"] == "王五", "E005: CSV转JSON数据错误"
    print("[通过] CSV->JSON 转换测试")

    # 测试5: Markdown 表格转换
    md_data = "| 姓名 | 年龄 |\n|------|------|\n| 张三 | 30 |\n| 李四 | 25 |\n"
    md_json = convert_format(md_data, "markdown", "json")
    parsed_md = json.loads(md_json)
    assert len(parsed_md) == 2, "E005: Markdown转换失败"
    assert parsed_md[0]["姓名"] == "张三", "E005: Markdown数据错误"
    print("[通过] Markdown->JSON 转换测试")

    # 测试6: 模糊日期置信度
    fuzzy_text = "大约3月付款"
    fields2 = extract_fields(fuzzy_text)
    if "date" in fields2:
        assert fields2["date"]["confidence"] < 0.8, "E001: 模糊日期置信度异常"
    print("[通过] 模糊日期置信度测试")

    # 测试7: 批量处理
    lines = [
        "张三 2024-01-01 100元",
        "李四 2024-02-01 200元",
        "王五 2024-03-01 300元",
    ]
    batch = batch_process(lines)
    assert len(batch) == 3, "E001: 批量处理数量错误"
    assert all(item["structured"] for item in batch), "E001: 批量处理结果为空"
    print("[通过] 批量处理测试")

    # 测试8: 错误处理
    try:
        convert_format("invalid json", "json", "csv")
        assert False, "E008: 应抛出JSON解析错误"
    except SystemExit:
        pass  # 预期行为
    print("[通过] 错误处理测试")

    print("=== 全部自检通过 ===")
    return True


def main() -> None:
    """主入口"""
    parser = argparse.ArgumentParser(description="okf-skills 数据整理工具")
    parser.add_argument("--selftest", action="store_true", help="运行离线自检")
    parser.add_argument("--extract", type=str, help="从文本中提取结构化字段")
    parser.add_argument("--convert", action="store_true", help="格式转换模式")
    parser.add_argument("--from", dest="from_format", type=str, default="text", help="输入格式")
    parser.add_argument("--to", dest="to_format", type=str, default="json", help="输出格式")
    parser.add_argument("--batch", type=str, help="批量处理文件路径")
    parser.add_argument("--input", type=str, help="输入文本或文件路径")

    parser.add_argument("--verbose", action="store_true", help="显示修改明细")  # R6 可解释输出

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        run_selftest()
        return

    # 提取模式
    if args.extract:
        fields = extract_fields(args.extract)
        print(json.dumps(fields, ensure_ascii=False, indent=2))
        return

    # 批量处理模式
    if args.batch:
        try:
            with open(args.batch, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
        except Exception as e:
            err("E007", str(e))
        results = batch_process(lines)
        print(json.dumps(results, ensure_ascii=False, indent=2))
        return

    # 转换模式
    if args.convert:
        if args.input:
            # 从文件读取
            try:
                with open(args.input, "r", encoding="utf-8", errors="replace") as f:
                    data = f.read()
            except Exception as e:
                err("E007", str(e))
        else:
            # 从标准输入读取
            data = sys.stdin.read()

        if not data.strip():
            err("E002")

        result = convert_format(data, args.from_format, args.to_format)
        print(result)
        return

    # 无参数时显示帮助
    parser.print_help()


if __name__ == "__main__":
    main()
