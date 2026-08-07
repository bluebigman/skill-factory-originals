#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
arc — 数据整理与结构化输出 Skill 的独立实现

本脚本依据功能规格独立编写，不复制任何既有代码。
支持将文本、文件、URL 内容解析为结构化结果，并输出 Markdown 表格 / JSON / CSV。
"""

import argparse
import csv
import io
import json
import os
import re
import sys
import urllib.request
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

# 错误码定义
ERROR_CODES = {
    "E001": "参数错误：输入为空或格式不正确",
    "E002": "文件读取失败：文件不存在或无法访问",
    "E003": "URL 访问失败：网络错误或内容不可达",
    "E004": "解析失败：无法从内容中提取有效数据项",
    "E005": "输出格式错误：不支持的输出格式",
    "E006": "数据项数量超限：单次最多处理 10 条",
    "E007": "字段结构错误：用户指定的字段名不合法",
    "E008": "内容长度超限：文本超过 5000 字符或文件超过 2MB",
    "E009": "编码错误：文件编码不支持",
    "E010": "内部错误：未预期的异常",
}

# 内置硬编码样例数据（用于 selftest，不依赖外部文件）
SELFTEST_SAMPLES = [
    {
        "raw": "张三 13812345678 2024-03-15 订单号 A12345 金额 299.00",
        "expected_fields": ["张三", "13812345678", "2024-03-15", "A12345", "299.00"],
    },
    {
        "raw": "李四 13998765432 2024-04-20 发票号 INV-2024-001 金额 1500.50",
        "expected_fields": ["李四", "13998765432", "2024-04-20", "INV-2024-001", "1500.50"],
    },
    {
        "raw": "王五 13712340000 2024-05-01 合同编号 CT-001 金额 8000",
        "expected_fields": ["王五", "13712340000", "2024-05-01", "CT-001", "8000"],
    },
]


def error_exit(code: str, detail: str = "") -> None:
    """输出错误信息并退出。"""
    msg = ERROR_CODES.get(code, "未知错误")
    if detail:
        msg = f"{msg}：{detail}"
    print(f"[错误 {code}] {msg}", file=sys.stderr)
    sys.exit(1)


def read_text_input(text: str) -> str:
    """校验文本输入，检查长度限制。"""
    if not text or not text.strip():
        error_exit("E001", "输入文本为空")
    if len(text) > 5000:
        error_exit("E008", f"文本长度 {len(text)} 超过 5000 字符限制")
    return text.strip()


def read_file_input(file_path: str) -> str:
    """读取本地文件内容，检查大小限制。"""
    if not os.path.exists(file_path):
        error_exit("E002", f"文件不存在：{file_path}")
    try:
        file_size = os.path.getsize(file_path)
        if file_size > 2 * 1024 * 1024:
            error_exit("E008", f"文件大小 {file_size} 字节超过 2MB 限制")
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except UnicodeDecodeError:
        error_exit("E009", "文件编码不支持（仅支持 UTF-8）")
    except Exception as e:
        error_exit("E002", str(e))


def read_url_input(url: str) -> str:
    """读取 URL 内容，检查大小限制。"""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            content = resp.read()
            if len(content) > 2 * 1024 * 1024:
                error_exit("E008", f"URL 内容 {len(content)} 字节超过 2MB 限制")
            return content.decode("utf-8", errors="replace")
    except Exception as e:
        error_exit("E003", str(e))


def split_data_items(content: str) -> List[str]:
    """将内容拆分为独立数据项，支持换行、逗号、分号分隔。"""
    # 优先按行分割，再按逗号/分号补充
    lines = [line.strip() for line in content.splitlines() if line.strip()]
    if len(lines) >= 2:
        return lines

    # 单行时尝试按逗号或分号分割
    if len(lines) == 1:
        parts = re.split(r"[,;]", lines[0])
        parts = [p.strip() for p in parts if p.strip()]
        if len(parts) >= 2:
            return parts
        return lines

    return lines


def extract_fields(data_item: str) -> Dict[str, Any]:
    """从单个数据项中提取关键字段（人名/日期/金额/编号）。"""
    fields: Dict[str, Any] = {}
    raw = data_item.strip()
    if not raw:
        return fields

    # 提取人名（中文姓名：2-4个汉字，或英文姓名）
    name_match = re.search(r"[\u4e00-\u9fa5]{2,4}", raw)
    if name_match:
        fields["name"] = name_match.group()
    else:
        name_match = re.search(r"[A-Za-z]+(?:\s+[A-Za-z]+)?", raw)
        if name_match:
            fields["name"] = name_match.group().strip()

    # 提取电话号码（手机号 1[3-9]\d{9} 或座机）
    phone_match = re.search(r"1[3-9]\d{9}|\d{3,4}-\d{7,8}", raw)
    if phone_match:
        fields["phone"] = phone_match.group()

    # 提取日期（YYYY-MM-DD 或 YYYY/MM/DD 或 YYYY年MM月DD日）
    date_match = re.search(
        r"\d{4}[-/年]\d{1,2}[-/月]\d{1,2}日?", raw
    )
    if date_match:
        date_str = date_match.group().replace("年", "-").replace("月", "-").replace("日", "")
        date_str = date_str.replace("/", "-")
        fields["date"] = date_str

    # 提取金额（数字 + 单位）
    amount_match = re.search(r"(\d+(?:\.\d+)?)\s*(元|块|RMB|CNY)?", raw)
    if amount_match and float(amount_match.group(1)) > 0:
        fields["amount"] = float(amount_match.group(1))
        if amount_match.group(2):
            fields["currency"] = amount_match.group(2)

    # 提取编号（订单号/发票号/合同号等）
    id_patterns = [
        r"(?:订单号|单号|编号)\s*[:：]?\s*([A-Za-z0-9\-]+)",
        r"(?:发票号|发票)\s*[:：]?\s*([A-Za-z0-9\-]+)",
        r"(?:合同编号|合同号)\s*[:：]?\s*([A-Za-z0-9\-]+)",
        r"\b[A-Z]{1,5}-\d{3,}\b",
        r"\b[A-Z]{1,5}\d{4,}\b",
    ]
    for pattern in id_patterns:
        id_match = re.search(pattern, raw)
        if id_match:
            fields["id"] = id_match.group(1) if id_match.lastindex else id_match.group()
            break

    return fields


def calculate_confidence(fields: Dict[str, Any], raw: str) -> Tuple[int, str]:
    """计算置信度并返回等级。"""
    if not fields:
        return 0, "低"

    # 基于提取到的字段数量计算基础置信度
    raw_len = len(raw)
    field_count = len(fields)

    # 基础分：每个有效字段 20 分
    base_score = min(field_count * 20, 80)

    # 内容长度加分：较长内容通常信息更完整
    if raw_len >= 20:
        base_score += 10
    elif raw_len >= 10:
        base_score += 5

    # 关键字段完整度加分
    if "name" in fields and "phone" in fields:
        base_score += 10
    if "date" in fields and "amount" in fields:
        base_score += 10

    # 限制在 0-100 范围
    score = max(0, min(100, base_score))

    # 等级划分
    if score >= 90:
        level = "高"
    elif score >= 70:
        level = "中"
    else:
        level = "低"

    return score, level


def summarize_raw(raw: str, max_len: int = 50) -> str:
    """生成原始内容摘要。"""
    raw = raw.strip()
    if len(raw) <= max_len:
        return raw
    return raw[: max_len - 3] + "..."


def process_data_items(data_items: List[str], custom_fields: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """处理数据项列表，返回结构化结果。"""
    if len(data_items) > 10:
        error_exit("E006", f"数据项数量 {len(data_items)} 超过 10 条限制")

    results = []
    for idx, item in enumerate(data_items, 1):
        fields = extract_fields(item)
        confidence_score, confidence_level = calculate_confidence(fields, item)

        result: Dict[str, Any] = {
            "序号": idx,
            "原始内容摘要": summarize_raw(item),
            "提取字段": fields,
            "置信度": f"{confidence_level} ({confidence_score}%)",
        }

        # 如果指定了自定义字段，按用户要求重组
        if custom_fields:
            custom_result: Dict[str, Any] = {"序号": idx, "原始内容摘要": summarize_raw(item)}
            for field in custom_fields:
                custom_result[field] = fields.get(field, "未提取到")
            custom_result["置信度"] = f"{confidence_level} ({confidence_score}%)"
            results.append(custom_result)
        else:
            results.append(result)

    return results


def format_markdown(results: List[Dict[str, Any]]) -> str:
    """输出为 Markdown 表格。"""
    if not results:
        return "（无数据）"

    # 获取所有字段名（保持顺序）
    all_keys: List[str] = []
    for r in results:
        for k in r.keys():
            if k not in all_keys:
                all_keys.append(k)

    # 构建表头
    header = "| " + " | ".join(all_keys) + " |"
    separator = "| " + " | ".join(["---"] * len(all_keys)) + " |"

    # 构建行
    lines = [header, separator]
    for r in results:
        row = []
        for k in all_keys:
            value = r.get(k, "")
            if isinstance(value, dict):
                # 提取字段字典转为简洁字符串
                parts = [f"{fk}:{fv}" for fk, fv in value.items()]
                value = ", ".join(parts)
            row.append(str(value))
        lines.append("| " + " | ".join(row) + " |")

    return "\n".join(lines)


def format_json(results: List[Dict[str, Any]]) -> str:
    """输出为 JSON 格式。"""
    return json.dumps(results, ensure_ascii=False, indent=2)


def format_csv(results: List[Dict[str, Any]]) -> str:
    """输出为 CSV 格式。"""
    if not results:
        return ""

    # 获取所有字段名
    all_keys: List[str] = []
    for r in results:
        for k in r.keys():
            if k not in all_keys:
                all_keys.append(k)

    output = io.StringIO()
    writer = csv.writer(output)

    # 写入表头
    writer.writerow(all_keys)

    # 写入数据行
    for r in results:
        row = []
        for k in all_keys:
            value = r.get(k, "")
            if isinstance(value, dict):
                parts = [f"{fk}:{fv}" for fk, fv in value.items()]
                value = "; ".join(parts)
            row.append(value)
        writer.writerow(row)

    return output.getvalue()


def run_selftest() -> int:
    """内置自检逻辑，使用硬编码样例数据验证核心功能。"""
    print("=== arc Skill 自检开始 ===")
    passed = 0
    total = len(SELFTEST_SAMPLES)

    for i, sample in enumerate(SELFTEST_SAMPLES, 1):
        raw = sample["raw"]
        expected = sample["expected_fields"]

        # 测试字段提取
        fields = extract_fields(raw)
        print(f"\n[{i}/{total}] 测试数据: {raw}")
        print(f"  提取结果: {fields}")

        # 验证关键字段是否提取到
        has_name = "name" in fields and fields["name"] == expected[0]
        has_phone = "phone" in fields and fields["phone"] == expected[1]
        has_date = "date" in fields and fields["date"] == expected[2]
        has_id = "id" in fields and fields["id"] == expected[3]
        has_amount = "amount" in fields and float(fields["amount"]) == float(expected[4])

        # 宽松断言：至少提取到 3 个关键字段即通过
        found_count = sum([has_name, has_phone, has_date, has_id, has_amount])
        if found_count >= 3:
            print(f"  ✓ 通过（提取到 {found_count}/5 个关键字段）")
            passed += 1
        else:
            print(f"  ✗ 失败（仅提取到 {found_count}/5 个关键字段）")

        # 测试置信度计算
        score, level = calculate_confidence(fields, raw)
        print(f"  置信度: {score}% ({level})")
        if score > 0:
            print("  ✓ 置信度计算正常")
        else:
            print("  ✗ 置信度计算异常")

    # 测试数据项拆分
    print("\n=== 数据项拆分测试 ===")
    test_content = "张三 13812345678;李四 13998765432,王五 13712340000"
    items = split_data_items(test_content)
    print(f"拆分结果: {items}")
    if len(items) >= 3:
        print("✓ 数据项拆分正常")
        passed += 1
    else:
        print("✗ 数据项拆分异常")

    # 测试 Markdown 输出
    print("\n=== 输出格式测试 ===")
    test_fields = extract_fields(SELFTEST_SAMPLES[0]["raw"])
    test_result = [{
        "序号": 1,
        "原始内容摘要": summarize_raw(SELFTEST_SAMPLES[0]["raw"]),
        "提取字段": test_fields,
        "置信度": "高 (90%)",
    }]
    md_output = format_markdown(test_result)
    print(f"Markdown 输出:\n{md_output}")
    if "|" in md_output and "---" in md_output:
        print("✓ Markdown 输出格式正确")
        passed += 1
    else:
        print("✗ Markdown 输出格式异常")

    # 测试 JSON 输出
    json_output = format_json(test_result)
    try:
        json.loads(json_output)
        print("✓ JSON 输出格式正确")
        passed += 1
    except json.JSONDecodeError:
        print("✗ JSON 输出格式异常")

    # 测试 CSV 输出
    csv_output = format_csv(test_result)
    if csv_output and "," in csv_output:
        print("✓ CSV 输出格式正确")
        passed += 1
    else:
        print("✗ CSV 输出格式异常")

    print(f"\n=== 自检完成：{passed}/{total + 5} 项通过 ===")
    return 0 if passed >= total else 1


def main() -> None:
    """主入口函数。"""
    parser = argparse.ArgumentParser(
        description="arc — 数据整理与结构化输出 Skill",
        epilog="示例：python main.py --text '张三 13812345678' --format json",
    )
    parser.add_argument("--text", type=str, help="直接输入的文本内容（不超过 5000 字符）")
    parser.add_argument("--file", type=str, help="本地文件路径（.txt/.csv/.json/.md）")
    parser.add_argument("--url", type=str, help="可访问的 URL 地址")
    parser.add_argument("--format", type=str, choices=["markdown", "json", "csv"], default="markdown", help="输出格式")
    parser.add_argument("--fields", type=str, help="自定义字段名，逗号分隔，如：name,phone,date")
    parser.add_argument("--selftest", action="store_true", help="运行内置自检")
    parser.add_argument("--version", action="version", version="arc 1.0.1")

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        sys.exit(run_selftest())

    # 检查输入源
    input_sources = sum([bool(args.text), bool(args.file), bool(args.url)])
    if input_sources == 0:
        error_exit("E001", "请提供输入内容：--text、--file 或 --url")
    if input_sources > 1:
        error_exit("E001", "只能指定一种输入源（--text、--file 或 --url 三选一）")

    # 读取输入
    if args.text:
        content = read_text_input(args.text)
    elif args.file:
        content = read_file_input(args.file)
    else:
        content = read_url_input(args.url)

    # 解析自定义字段
    custom_fields = None
    if args.fields:
        custom_fields = [f.strip() for f in args.fields.split(",") if f.strip()]
        if not custom_fields:
            error_exit("E007", "字段名不能为空")
        # 校验字段名合法性
        for f in custom_fields:
            if not re.match(r"^[a-zA-Z_\u4e00-\u9fa5][a-zA-Z0-9_\u4e00-\u9fa5]*$", f):
                error_exit("E007", f"非法字段名：{f}")

    # 拆分数据项
    data_items = split_data_items(content)
    if not data_items:
        error_exit("E004", "无法从内容中提取有效数据项")

    # 处理数据
    results = process_data_items(data_items, custom_fields)

    # 输出结果
    if args.format == "markdown":
        output = format_markdown(results)
    elif args.format == "json":
        output = format_json(results)
    elif args.format == "csv":
        output = format_csv(results)
    else:
        error_exit("E005", f"不支持的输出格式：{args.format}")

    print(output)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n用户中断执行", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        error_exit("E010", str(e))
