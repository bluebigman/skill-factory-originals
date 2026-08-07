#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py — german-ocr 技能核心实现（clean-room 重写）

功能概述：
    从德文票据/表单/证件文本中提取关键字段，输出结构化 JSON。
    本实现为纯标准库，不依赖任何第三方 OCR 引擎或外部服务。

用法：
    python main.py --selftest          # 离线自检（硬编码样例，无需外部文件）
    python main.py --text "..."        # 从命令行文本提取字段
    python main.py --json "..."        # 从命令行 JSON 字符串提取字段

错误码：
    E001: 输入为空或类型错误
    E002: 输入文本过短（无法提取任何字段）
    E003: 日期解析失败
    E004: 金额解析失败
    E005: 发票号解析失败
    E006: 税号解析失败
    E007: 收/付款方解析失败
    E008: JSON 输入格式错误
    E009: 未知命令行参数
    E010: 内部逻辑错误（不应发生）
"""

import argparse
import json
import re
import sys
from datetime import datetime

# ---------------------------------------------------------------------------
# 常量与配置
# ---------------------------------------------------------------------------

# 字段置信度阈值：低于此值的字段标记为低置信度
CONFIDENCE_THRESHOLD = 0.5

# 常见德文日期格式（用于解析）
DATE_PATTERNS = [
    r"\d{1,2}\.\s*\d{1,2}\.\s*\d{2,4}",          # 01.01.2024 / 1. 1. 24
    r"\d{4}-\d{1,2}-\d{1,2}",                     # 2024-01-01
    r"\d{1,2}\.\s*[A-Za-zäöüÄÖÜ]+\.?\s*\d{2,4}", # 1. Januar 2024
]

# 常见德文金额格式（欧元）
AMOUNT_PATTERNS = [
    r"\d{1,3}(?:\.\d{3})*,\d{2}\s*(?:EUR|€)?",    # 1.234,56 EUR
    r"\d{1,3}(?:,\d{3})*\.\d{2}\s*(?:EUR|€)?",    # 1,234.56 EUR（兼容英文格式）
    r"\d+,\d{2}\s*(?:EUR|€)?",                     # 123,45
]

# 常见发票号关键词（德文）
INVOICE_KEYWORDS = [
    "rechnungsnummer", "rechnung nr", "rechnungsnr",
    "invoice number", "invoice no", "invoice#",
    "rgnr", "rnr",
]

# 常见税号关键词（德文）
TAX_KEYWORDS = [
    "ust-idnr", "ust idnr", "umsatzsteuer-id",
    "steuernummer", "steuer-nr", "tax number",
    "vat id", "vat number",
]

# 常见收/付款方关键词
VENDOR_KEYWORDS = ["rechnungssteller", "absender", "lieferant", "verkäufer", "vendor", "seller"]
CUSTOMER_KEYWORDS = ["rechnungempfänger", "empfänger", "kunde", "customer", "buyer"]

# ---------------------------------------------------------------------------
# 核心数据结构
# ---------------------------------------------------------------------------


class Field:
    """单个提取字段的容器。"""

    def __init__(self, name, value, confidence):
        self.name = name
        self.value = value
        self.confidence = confidence

    def to_dict(self):
        return {
            "name": self.name,
            "value": self.value,
            "confidence": round(self.confidence, 4),
            "low_confidence": self.confidence < CONFIDENCE_THRESHOLD,
        }


class ExtractionResult:
    """提取结果容器，包含多个字段和整体置信度。"""

    def __init__(self):
        self.fields = []
        self.warnings = []

    def add_field(self, name, value, confidence):
        self.fields.append(Field(name, value, confidence))

    def add_warning(self, message):
        self.warnings.append(message)

    def to_dict(self):
        return {
            "fields": [f.to_dict() for f in self.fields],
            "warnings": self.warnings,
            "overall_confidence": self._overall_confidence(),
        }

    def _overall_confidence(self):
        if not self.fields:
            return 0.0
        return round(sum(f.confidence for f in self.fields) / len(self.fields), 4)


# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------


def normalize_text(text):
    """规范化输入文本：去空白、统一换行。"""
    if not text or not isinstance(text, str):
        return ""
    # 将各种换行统一为 \n，并压缩多余空白
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [re.sub(r"\s+", " ", line).strip() for line in text.split("\n")]
    return "\n".join(line for line in lines if line)


def search_pattern(text, patterns):
    """在文本中搜索第一个匹配的模式，返回 (匹配文本, 位置)。"""
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(0).strip(), match.start()
    return None, -1


def extract_date(text):
    """提取日期字段。返回 (日期字符串, 置信度)。"""
    match, _ = search_pattern(text, DATE_PATTERNS)
    if not match:
        return None, 0.0

    # 尝试解析日期以验证格式
    try:
        # 标准化：去除多余空格
        normalized = re.sub(r"\s+", " ", match)
        # 尝试多种格式解析
        parsed = None
        for fmt in ("%d.%m.%Y", "%d.%m.%y", "%Y-%m-%d", "%d %B %Y", "%d. %B %Y"):
            try:
                parsed = datetime.strptime(normalized, fmt)
                break
            except ValueError:
                continue
        if parsed is None:
            return None, 0.0
        return match, 0.9
    except Exception:
        return None, 0.0


def extract_amount(text):
    """提取金额字段。返回 (金额字符串, 置信度)。"""
    match, _ = search_pattern(text, AMOUNT_PATTERNS)
    if not match:
        return None, 0.0

    # 验证金额格式
    try:
        # 去除货币符号和空格
        cleaned = re.sub(r"[^\d,.]", "", match)
        # 判断是欧洲格式还是英文格式
        if "," in cleaned and "." in cleaned:
            if cleaned.rfind(",") > cleaned.rfind("."):
                # 欧洲格式: 1.234,56 -> 1234.56
                cleaned = cleaned.replace(".", "").replace(",", ".")
            else:
                # 英文格式: 1,234.56 -> 1234.56
                cleaned = cleaned.replace(",", "")
        elif "," in cleaned:
            cleaned = cleaned.replace(",", ".")
        value = float(cleaned)
        if value <= 0:
            return None, 0.0
        return match, 0.85
    except (ValueError, TypeError):
        return None, 0.0


def extract_invoice_number(text):
    """提取发票号。返回 (发票号, 置信度)。"""
    lines = text.split("\n")
    for i, line in enumerate(lines):
        lower = line.lower()
        for keyword in INVOICE_KEYWORDS:
            if keyword in lower:
                # 尝试从该行或下一行提取数字
                for candidate_line in [line, lines[i + 1] if i + 1 < len(lines) else ""]:
                    # 去除关键词部分
                    after_kw = re.sub(keyword, "", candidate_line, flags=re.IGNORECASE)
                    # 查找数字序列（可能包含连字符）
                    match = re.search(r"[A-Za-z0-9][A-Za-z0-9\-/]{3,}", after_kw)
                    if match:
                        return match.group(0).strip(), 0.8
    return None, 0.0


def extract_tax_number(text):
    """提取税号。返回 (税号, 置信度)。"""
    lines = text.split("\n")
    for i, line in enumerate(lines):
        lower = line.lower()
        for keyword in TAX_KEYWORDS:
            if keyword in lower:
                for candidate_line in [line, lines[i + 1] if i + 1 < len(lines) else ""]:
                    after_kw = re.sub(keyword, "", candidate_line, flags=re.IGNORECASE)
                    # 税号通常是字母+数字组合
                    match = re.search(r"[A-Za-z]{0,3}\s?\d{2,15}", after_kw)
                    if match:
                        return match.group(0).strip(), 0.75
    return None, 0.0


def extract_party(text, keywords):
    """提取收/付款方名称。返回 (名称, 置信度)。"""
    lines = text.split("\n")
    for i, line in enumerate(lines):
        lower = line.lower()
        for keyword in keywords:
            if keyword in lower:
                # 取该行冒号后的内容，或下一行
                after_kw = re.sub(keyword, "", line, flags=re.IGNORECASE)
                after_kw = after_kw.lstrip(":： \t")
                if after_kw and len(after_kw) > 1:
                    return after_kw.strip(), 0.7
                if i + 1 < len(lines) and lines[i + 1].strip():
                    return lines[i + 1].strip(), 0.6
    return None, 0.0


def extract_vendor(text):
    """提取收款方（供应商）。"""
    return extract_party(text, VENDOR_KEYWORDS)


def extract_customer(text):
    """提取付款方（客户）。"""
    return extract_party(text, CUSTOMER_KEYWORDS)


# ---------------------------------------------------------------------------
# 主提取逻辑
# ---------------------------------------------------------------------------


def extract_fields(text):
    """从文本中提取所有可识别字段。返回 ExtractionResult。"""
    result = ExtractionResult()
    normalized = normalize_text(text)

    if not normalized:
        result.add_warning("E001: 输入为空")
        return result

    if len(normalized) < 10:
        result.add_warning("E002: 输入文本过短")
        return result

    # 日期
    date_val, date_conf = extract_date(normalized)
    if date_val:
        result.add_field("date", date_val, date_conf)
    else:
        result.add_warning("E003: 未找到日期")

    # 金额
    amount_val, amount_conf = extract_amount(normalized)
    if amount_val:
        result.add_field("amount", amount_val, amount_conf)
    else:
        result.add_warning("E004: 未找到金额")

    # 发票号
    inv_val, inv_conf = extract_invoice_number(normalized)
    if inv_val:
        result.add_field("invoice_number", inv_val, inv_conf)
    else:
        result.add_warning("E005: 未找到发票号")

    # 税号
    tax_val, tax_conf = extract_tax_number(normalized)
    if tax_val:
        result.add_field("tax_number", tax_val, tax_conf)
    else:
        result.add_warning("E006: 未找到税号")

    # 收款方
    vendor_val, vendor_conf = extract_vendor(normalized)
    if vendor_val:
        result.add_field("vendor", vendor_val, vendor_conf)
    else:
        result.add_warning("E007: 未找到收款方")

    # 付款方
    customer_val, customer_conf = extract_customer(normalized)
    if customer_val:
        result.add_field("customer", customer_val, customer_conf)
    else:
        result.add_warning("E007: 未找到付款方")

    return result


# ---------------------------------------------------------------------------
# JSON 输入处理
# ---------------------------------------------------------------------------


def extract_from_json(json_str):
    """从 JSON 字符串中提取字段。支持直接传入文本或字段映射。"""
    try:
        data = json.loads(json_str)
    except json.JSONDecodeError:
        return None, "E008: JSON 格式错误"

    if isinstance(data, str):
        # JSON 中直接包含文本
        return extract_fields(data), None
    elif isinstance(data, dict):
        # 支持 {"text": "..."} 或 {"content": "..."}
        text = data.get("text") or data.get("content") or data.get("ocr_text")
        if text:
            return extract_fields(str(text)), None
        # 支持 {"fields": {...}} 直接传入字段
        if "fields" in data:
            result = ExtractionResult()
            for name, value in data["fields"].items():
                result.add_field(str(name), str(value), 0.9)
            return result, None
        return None, "E008: JSON 中未找到文本字段"
    else:
        return None, "E008: JSON 类型不支持"


# ---------------------------------------------------------------------------
# 自检函数（selftest）
# ---------------------------------------------------------------------------


def run_selftest():
    """离线自检核心逻辑，不依赖外部文件。"""
    print("=" * 60)
    print("german-ocr 自检开始")
    print("=" * 60)

    # 硬编码测试样例（德文发票）
    sample_invoice = """
    Firma Muster GmbH
    Rechnungsnummer: RE-2024-00123
    USt-IdNr: DE123456789
    
    An:
    Hans Beispiel
    Musterstraße 12
    10115 Berlin
    
    Rechnungsdatum: 15.03.2024
    Betrag: 1.234,56 EUR
    """

    # 测试1: 基本字段提取
    print("\n[测试1] 标准发票字段提取")
    result = extract_fields(sample_invoice)
    result_dict = result.to_dict()

    # 宽松断言：检查关键字段是否存在
    field_names = [f["name"] for f in result_dict["fields"]]
    assert "date" in field_names, "E010: 应提取到日期字段"
    assert "amount" in field_names, "E010: 应提取到金额字段"
    assert "invoice_number" in field_names, "E010: 应提取到发票号字段"
    assert "tax_number" in field_names, "E010: 应提取到税号字段"
    assert "customer" in field_names, "E010: 应提取到客户字段"

    # 宽松值断言
    for field in result_dict["fields"]:
        assert field["value"], "E010: 字段值不应为空"
        assert 0 <= field["confidence"] <= 1, "E010: 置信度应在 0~1 之间"

    print("  ✓ 字段提取测试通过")
    print(f"  提取到 {len(result_dict['fields'])} 个字段")

    # 测试2: 空输入处理
    print("\n[测试2] 空输入处理")
    empty_result = extract_fields("")
    assert len(empty_result.warnings) > 0, "E010: 空输入应产生警告"
    print("  ✓ 空输入处理通过")

    # 测试3: JSON 输入
    print("\n[测试3] JSON 输入处理")
    json_input = json.dumps({"text": "Rechnung Nr: INV-001\nBetrag: 99,90 EUR\nDatum: 01.01.2024"})
    json_result, err = extract_from_json(json_input)
    assert err is None, f"E010: JSON 处理失败: {err}"
    assert json_result is not None, "E010: JSON 结果不应为空"
    assert len(json_result.fields) > 0, "E010: JSON 应提取到字段"
    print("  ✓ JSON 输入处理通过")

    # 测试4: 错误 JSON
    print("\n[测试4] 错误 JSON 处理")
    bad_result, err = extract_from_json("{invalid json")
    assert err is not None, "E010: 无效 JSON 应返回错误"
    assert err.startswith("E008"), f"E010: 错误码应为 E008，实际: {err}"
    print(f"  ✓ 错误 JSON 处理通过 (错误码: {err})")

    # 测试5: 金额格式兼容
    print("\n[测试5] 金额格式兼容")
    us_format = extract_fields("Amount: 1,234.56 USD")
    us_amount = [f for f in us_format.fields if f.name == "amount"]
    assert len(us_amount) > 0, "E010: 应提取到金额"
    print(f"  ✓ 英文金额格式通过: {us_amount[0].value}")

    # 测试6: 日期格式兼容
    print("\n[测试6] 日期格式兼容")
    iso_date = extract_fields("Date: 2024-03-15")
    iso_date_fields = [f for f in iso_date.fields if f.name == "date"]
    assert len(iso_date_fields) > 0, "E010: 应提取到日期"
    print(f"  ✓ ISO 日期格式通过: {iso_date_fields[0].value}")

    # 测试7: 手写内容标记（规格要求）
    print("\n[测试7] 手写内容处理")
    handwritten = extract_fields("Unterschrift: [需核实:手写内容]")
    # 手写内容不应被错误提取为其他字段
    assert not any(f.name == "amount" for f in handwritten.fields), "E010: 手写内容不应提取为金额"
    print("  ✓ 手写内容处理通过")

    # 测试8: 整体置信度
    print("\n[测试8] 整体置信度计算")
    assert 0 <= result_dict["overall_confidence"] <= 1, "E010: 整体置信度应在 0~1 之间"
    print(f"  ✓ 整体置信度: {result_dict['overall_confidence']}")

    print("\n" + "=" * 60)
    print("所有自检测试通过 ✓")
    print("=" * 60)
    return 0


# ---------------------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(
        description="german-ocr: 德语文档票据信息抽取",
        epilog="示例: python main.py --text 'Rechnung Nr: INV-001 Betrag: 99,90 EUR'"
    )
    parser.add_argument("--text", type=str, help="直接传入文本进行字段提取")
    parser.add_argument("--json", type=str, help="传入 JSON 字符串（包含 text 字段）")
    parser.add_argument("--selftest", action="store_true", help="运行离线自检")

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        sys.exit(run_selftest())

    # 文本模式
    if args.text:
        result = extract_fields(args.text)
        print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
        return 0

    # JSON 模式
    if args.json:
        result, err = extract_from_json(args.json)
        if err:
            print(f"错误: {err}", file=sys.stderr)
            return 1
        print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
        return 0

    # 无参数
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
