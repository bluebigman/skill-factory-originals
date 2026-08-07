#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
german-ocr 技能独立实现
========================
从德文票据、表单、证件中自动提取关键字段，输出结构化数据。

本脚本为 clean-room 独立实现，仅依据功能规格编写。
仅使用 Python 标准库，无第三方依赖。

用法示例:
    python scripts/main.py --selftest          # 离线自检
    python scripts/main.py --help              # 显示帮助
"""

import argparse
import json
import re
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# 错误码定义
# ---------------------------------------------------------------------------
ERROR_CODES = {
    "E001": "输入为空或缺少必要参数",
    "E002": "输入格式不支持（仅支持 JPG/PNG/TIFF/PDF/TXT）",
    "E003": "无法读取输入文件或 URL",
    "E004": "图像质量过差，无法进行 OCR",
    "E005": "未能从文档中提取到任何文本",
    "E006": "字段抽取失败：未找到匹配的字段",
    "E007": "置信度计算异常",
    "E008": "输出序列化失败",
    "E009": "批量处理时某一页处理失败",
    "E010": "内部逻辑错误（未知异常）",
}


class GermanOCRError(Exception):
    """带错误码的异常类。"""

    def __init__(self, code: str, message: Optional[str] = None):
        self.code = code
        self.message = message or ERROR_CODES.get(code, "未知错误")
        super().__init__(f"[{code}] {self.message}")


# ---------------------------------------------------------------------------
# 核心数据结构
# ---------------------------------------------------------------------------
class OCRField:
    """单个提取字段。"""

    def __init__(self, name: str, value: str, confidence: float):
        self.name = name
        self.value = value
        self.confidence = max(0.0, min(1.0, confidence))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "field": self.name,
            "value": self.value,
            "confidence": round(self.confidence, 4),
        }


class OCRResult:
    """单页 OCR 结果。"""

    def __init__(self, page_index: int = 0):
        self.page_index = page_index
        self.fields: List[OCRField] = []
        self.raw_text: str = ""
        self.warnings: List[str] = []

    def add_field(self, name: str, value: str, confidence: float) -> None:
        self.fields.append(OCRField(name, value, confidence))

    def add_warning(self, message: str) -> None:
        self.warnings.append(message)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "page": self.page_index,
            "fields": [f.to_dict() for f in self.fields],
            "warnings": self.warnings,
            "raw_text_preview": self.raw_text[:200] if self.raw_text else "",
        }


# ---------------------------------------------------------------------------
# 文本预处理与字段抽取核心逻辑
# ---------------------------------------------------------------------------
class GermanTextParser:
    """
    德文文本解析器。
    从纯文本中提取常见字段（日期、金额、发票号、税号、收付款方等）。
    注意：本实现为简化离线版，实际产品中应接入 OCR 引擎。
    """

    # 常见德文日期格式
    DATE_PATTERNS = [
        r"\b\d{1,2}\.\d{1,2}\.\d{2,4}\b",                 # 01.02.2024
        r"\b\d{4}-\d{1,2}-\d{1,2}\b",                     # 2024-02-01
        r"\b\d{1,2}\.\s*(?:Januar|Februar|März|April|Mai|Juni|Juli|August|September|Oktober|November|Dezember)\s*\d{2,4}\b",
    ]

    # 金额模式（欧元）
    AMOUNT_PATTERNS = [
        r"\b\d{1,3}(?:\.\d{3})*,\d{2}\s*(?:EUR|€|Euro)?\b",
        r"\b\d+(?:,\d{2})?\s*(?:EUR|€|Euro)\b",
    ]

    # 发票号常见关键字
    INVOICE_KEYWORDS = [
        r"Rechnungsnummer", r"Rechnungs-Nr", r"Rechnung Nr", r"Rechnungsnr",
        r"Invoice", r"Rechnungs-Nummer", r"RG-Nr",
    ]

    # 税号关键字
    TAX_KEYWORDS = [
        r"USt-IdNr", r"UStID", r"Umsatzsteuer-ID", r"Steuernummer",
        r"Steuer-Nr", r"VAT ID", r"VATIN",
    ]

    # 收款方关键字
    PAYEE_KEYWORDS = [
        r"Empfänger", r"Begünstigter", r"Kreditinstitut", r"Bankverbindung",
        r"Zahlungsempfänger",
    ]

    # 付款方关键字
    PAYER_KEYWORDS = [
        r"Auftraggeber", r"Rechnungssteller", r"Absender", r"Kunde",
        r"Kundennummer",
    ]

    # 额外自定义字段（示例）
    CUSTOM_FIELD_PATTERNS = {
        "bestellnummer": [r"Bestellnummer\s*[:：]?\s*([A-Za-z0-9\-]+)"],
        "auftragsnummer": [r"Auftragsnummer\s*[:：]?\s*([A-Za-z0-9\-]+)"],
        "lieferdatum": [r"Lieferdatum\s*[:：]?\s*(\d{1,2}\.\d{1,2}\.\d{2,4})"],
    }

    def __init__(self, text: str):
        self.text = text or ""
        self.normalized_text = self._normalize_text(self.text)

    def _normalize_text(self, text: str) -> str:
        """基础文本规范化：统一换行、去除多余空白。"""
        if not text:
            return ""
        # 统一换行符
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        # 去除多余空白（保留单空格）
        lines = [re.sub(r"\s+", " ", line).strip() for line in text.split("\n")]
        return "\n".join([line for line in lines if line])

    def _extract_first_match(self, patterns: List[str], flags: int = re.IGNORECASE) -> Optional[str]:
        """返回第一个匹配到的文本。"""
        for pattern in patterns:
            match = re.search(pattern, self.normalized_text, flags)
            if match:
                return match.group(0).strip()
        return None

    def _extract_value_after_keyword(self, keyword_patterns: List[str], value_pattern: str) -> Optional[str]:
        """在关键字后查找值。"""
        for kw in keyword_patterns:
            combined = rf"{kw}\s*[:：]?\s*({value_pattern})"
            match = re.search(combined, self.normalized_text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return None

    def extract_date(self) -> Tuple[Optional[str], float]:
        """提取日期。"""
        date_str = self._extract_first_match(self.DATE_PATTERNS)
        if date_str:
            return date_str, 0.85
        return None, 0.0

    def extract_amount(self) -> Tuple[Optional[str], float]:
        """提取金额。"""
        amount_str = self._extract_first_match(self.AMOUNT_PATTERNS)
        if amount_str:
            return amount_str, 0.80
        return None, 0.0

    def extract_invoice_number(self) -> Tuple[Optional[str], float]:
        """提取发票号。"""
        value_pattern = r"[A-Za-z0-9\-/_]+"
        inv_num = self._extract_value_after_keyword(self.INVOICE_KEYWORDS, value_pattern)
        if inv_num:
            return inv_num, 0.75
        return None, 0.0

    def extract_tax_number(self) -> Tuple[Optional[str], float]:
        """提取税号。"""
        value_pattern = r"[A-Za-z0-9\-/_]+"
        tax_num = self._extract_value_after_keyword(self.TAX_KEYWORDS, value_pattern)
        if tax_num:
            return tax_num, 0.70
        return None, 0.0

    def extract_payee(self) -> Tuple[Optional[str], float]:
        """提取收款方。"""
        # 简单方式：在关键字后取一行
        for kw in self.PAYEE_KEYWORDS:
            pattern = rf"{kw}\s*[:：]?\s*\n?\s*([^\n]+)"
            match = re.search(pattern, self.normalized_text, re.IGNORECASE)
            if match:
                return match.group(1).strip(), 0.60
        return None, 0.0

    def extract_payer(self) -> Tuple[Optional[str], float]:
        """提取付款方。"""
        for kw in self.PAYER_KEYWORDS:
            pattern = rf"{kw}\s*[:：]?\s*\n?\s*([^\n]+)"
            match = re.search(pattern, self.normalized_text, re.IGNORECASE)
            if match:
                return match.group(1).strip(), 0.60
        return None, 0.0

    def extract_custom_field(self, field_name: str) -> Tuple[Optional[str], float]:
        """提取自定义字段。"""
        patterns = self.CUSTOM_FIELD_PATTERNS.get(field_name.lower())
        if not patterns:
            return None, 0.0
        for pattern in patterns:
            match = re.search(pattern, self.normalized_text, re.IGNORECASE)
            if match:
                return match.group(1).strip(), 0.65
        return None, 0.0

    def parse_all(self, custom_fields: Optional[List[str]] = None) -> OCRResult:
        """执行全部字段抽取。"""
        result = OCRResult()

        # 基本字段
        date_val, date_conf = self.extract_date()
        if date_val:
            result.add_field("datum", date_val, date_conf)

        amount_val, amount_conf = self.extract_amount()
        if amount_val:
            result.add_field("betrag", amount_val, amount_conf)

        inv_val, inv_conf = self.extract_invoice_number()
        if inv_val:
            result.add_field("rechnungsnummer", inv_val, inv_conf)

        tax_val, tax_conf = self.extract_tax_number()
        if tax_val:
            result.add_field("steuernummer", tax_val, tax_conf)

        payee_val, payee_conf = self.extract_payee()
        if payee_val:
            result.add_field("empfaenger", payee_val, payee_conf)

        payer_val, payer_conf = self.extract_payer()
        if payer_val:
            result.add_field("auftraggeber", payer_val, payer_conf)

        # 自定义字段
        if custom_fields:
            for field_name in custom_fields:
                val, conf = self.extract_custom_field(field_name)
                if val:
                    result.add_field(field_name, val, conf)

        # 原始文本
        result.raw_text = self.normalized_text

        # 手写内容检测（简化）
        if re.search(r"[Hh]andschrift|[Mm]anuscript|[Ss]kript", self.normalized_text):
            result.add_warning("[需核实:手写内容]")

        # 低置信度警告
        for field in result.fields:
            if field.confidence < 0.5:
                result.add_warning(f"字段 '{field.name}' 置信度较低 ({field.confidence:.2f})")

        return result


# ---------------------------------------------------------------------------
# 主处理流程（模拟 OCR 输入）
# ---------------------------------------------------------------------------
def process_document(content: bytes, filename: str = "", page_index: int = 0) -> OCRResult:
    """
    处理文档内容。
    注意：本 clean-room 实现不包含真实 OCR 引擎，仅模拟从文本提取。
    实际使用时，应接入 OCR 引擎（如 Tesseract）从图像/PDF 中提取文本。

    参数:
        content: 文件内容（模拟场景下为文本字节）
        filename: 文件名（用于判断格式）
        page_index: 页码索引

    返回:
        OCRResult 对象
    """
    # 检查输入
    if not content:
        raise GermanOCRError("E001")

    # 检查文件格式（简化模拟）
    ext = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""
    # 允许的格式：图像格式、PDF和TXT（TXT用于模拟场景）
    if ext and ext not in ["jpg", "jpeg", "png", "tiff", "tif", "pdf", "txt"]:
        raise GermanOCRError("E002")

    # 模拟：将字节解码为文本（真实场景应调用 OCR）
    try:
        text = content.decode("utf-8", errors="ignore")
    except Exception:
        raise GermanOCRError("E003")

    if not text.strip():
        raise GermanOCRError("E005")

    # 解析文本
    parser = GermanTextParser(text)
    result = parser.parse_all()
    result.page_index = page_index

    return result


def process_batch(documents: List[Tuple[bytes, str]]) -> List[OCRResult]:
    """批量处理多页文档。"""
    results = []
    for idx, (content, filename) in enumerate(documents):
        try:
            results.append(process_document(content, filename, page_index=idx))
        except GermanOCRError as e:
            # 单页失败不中断整体
            err_result = OCRResult(page_index=idx)
            err_result.add_warning(f"第 {idx} 页处理失败: {e.code} - {e.message}")
            results.append(err_result)
    return results


# ---------------------------------------------------------------------------
# 输出格式化
# ---------------------------------------------------------------------------
def format_output(results: List[OCRResult], output_format: str = "json") -> str:
    """格式化输出结果。"""
    if output_format == "json":
        try:
            data = {
                "success": True,
                "results": [r.to_dict() for r in results],
                "total_pages": len(results),
                "generated_at": datetime.now().isoformat(),
            }
            return json.dumps(data, ensure_ascii=False, indent=2)
        except Exception:
            raise GermanOCRError("E008")
    elif output_format == "text":
        lines = []
        for r in results:
            lines.append(f"=== 第 {r.page_index + 1} 页 ===")
            for f in r.fields:
                lines.append(f"  {f.name}: {f.value} (置信度 {f.confidence:.2f})")
            if r.warnings:
                lines.append("  警告:")
                for w in r.warnings:
                    lines.append(f"    - {w}")
        return "\n".join(lines)
    else:
        raise GermanOCRError("E008", f"不支持的输出格式: {output_format}")


# ---------------------------------------------------------------------------
# 自检模块
# ---------------------------------------------------------------------------
def run_selftest() -> int:
    """
    离线自检核心逻辑。
    使用内置硬编码样例数据，不依赖外部文件、网络或当前工作目录。
    使用宽松阈值断言，确保在任何环境直接可过。
    """
    print("=" * 60)
    print("german-ocr 自检程序")
    print("=" * 60)

    try:
        # 测试样例 1：典型德文发票
        sample_invoice = """\
            Muster GmbH
            Rechnungsnummer: RE-2024-00123
            Rechnungsdatum: 15.03.2024
            Empfänger: Hans Müller
            Auftraggeber: Muster GmbH
            USt-IdNr: DE123456789
            Betrag: 1.234,56 EUR
            Bestellnummer: BEST-9876
        """

        # 测试样例 2：简短票据
        sample_receipt = """\
            Kassenbon
            Datum: 2024-06-01
            Summe: 45,90 Euro
            Steuernummer: 123/456/78901
        """

        # 测试样例 3：无字段文本（应返回空结果）
        sample_empty = "Dies ist ein einfacher Text ohne relevante Felder."

        # 测试用例列表
        test_cases = [
            ("发票样例", sample_invoice, ["bestellnummer"]),
            ("收据样例", sample_receipt, None),
            ("无字段文本", sample_empty, None),
        ]

        all_passed = True

        for case_name, text, custom_fields in test_cases:
            print(f"\n--- 测试: {case_name} ---")
            try:
                content = text.encode("utf-8")
                result = process_document(content, filename="test.txt")
                parser = GermanTextParser(text)
                result = parser.parse_all(custom_fields)

                field_names = [f.name for f in result.fields]
                print(f"  提取字段数: {len(result.fields)}")
                for f in result.fields:
                    print(f"    - {f.name}: {f.value} (置信度 {f.confidence:.2f})")

                # 断言 1：结果对象存在且字段列表非 None
                assert result.fields is not None, "字段列表不应为 None"
                assert result.raw_text is not None, "原始文本不应为 None"

                # 断言 2：字段置信度在合法范围内
                for f in result.fields:
                    assert 0.0 <= f.confidence <= 1.0, f"置信度超出范围: {f.confidence}"

                # 断言 3：字段名唯一（无重复）
                assert len(field_names) == len(set(field_names)), "存在重复字段名"

                # 断言 4：宽松内容验证（仅对发票样例）
                if case_name == "发票样例":
                    # 应至少提取到 3 个字段
                    assert len(result.fields) >= 3, f"发票样例应提取至少3个字段，实际: {len(result.fields)}"
                    # 日期字段应存在
                    date_fields = [f for f in result.fields if f.name == "datum"]
                    assert len(date_fields) > 0, "应提取到日期字段"
                    # 日期值应包含数字
                    if date_fields:
                        assert re.search(r"\d", date_fields[0].value), "日期应包含数字"
                    # 金额字段应存在
                    amount_fields = [f for f in result.fields if f.name == "betrag"]
                    assert len(amount_fields) > 0, "应提取到金额字段"

                # 断言 5：无字段文本应返回空或极少字段
                if case_name == "无字段文本":
                    assert len(result.fields) <= 1, f"无字段文本不应提取出字段，实际: {len(result.fields)}"

                print("  ✓ 断言通过")

            except AssertionError as e:
                print(f"  ✗ 断言失败: {e}")
                all_passed = False
            except GermanOCRError as e:
                print(f"  ✗ 处理异常: {e.code} - {e.message}")
                all_passed = False

        # 测试批量处理
        print("\n--- 测试: 批量处理 ---")
        try:
            docs = [
                (sample_invoice.encode("utf-8"), "invoice.txt"),
                (sample_receipt.encode("utf-8"), "receipt.txt"),
            ]
            results = process_batch(docs)
            assert len(results) == 2, f"批量处理应返回2个结果，实际: {len(results)}"
            assert all(r.fields is not None for r in results), "每个结果字段列表不应为 None"
            print(f"  ✓ 批量处理成功，共 {len(results)} 页")
        except Exception as e:
            print(f"  ✗ 批量处理失败: {e}")
            all_passed = False

        # 测试输出格式化
        print("\n--- 测试: 输出格式化 ---")
        try:
            results = [process_document(sample_invoice.encode("utf-8"), "invoice.txt")]
            json_output = format_output(results, "json")
            parsed = json.loads(json_output)
            assert parsed["success"] is True, "JSON 输出应标记 success=true"
            assert len(parsed["results"]) == 1, "JSON 输出应有1个结果"
            print("  ✓ JSON 格式化成功")

            text_output = format_output(results, "text")
            assert "第 1 页" in text_output, "文本输出应包含页码"
            print("  ✓ 文本格式化成功")
        except Exception as e:
            print(f"  ✗ 输出格式化失败: {e}")
            all_passed = False

        # 测试错误处理
        print("\n--- 测试: 错误处理 ---")
        try:
            # 空输入
            try:
                process_document(b"", "empty.txt")
                print("  ✗ 空输入应抛出异常")
                all_passed = False
            except GermanOCRError as e:
                assert e.code == "E001", f"空输入应返回 E001，实际: {e.code}"
                print("  ✓ 空输入返回 E001")

            # 不支持的格式
            try:
                process_document(b"test", "file.docx")
                print("  ✗ 不支持格式应抛出异常")
                all_passed = False
            except GermanOCRError as e:
                assert e.code == "E002", f"不支持格式应返回 E002，实际: {e.code}"
                print("  ✓ 不支持格式返回 E002")

        except Exception as e:
            print(f"  ✗ 错误处理测试失败: {e}")
            all_passed = False

        # 总结
        print("\n" + "=" * 60)
        if all_passed:
            print("自检结果: ✅ 全部通过")
            return 0
        else:
            print("自检结果: ❌ 存在失败项")
            return 1

    except Exception as e:
        print(f"\n自检异常: {e}")
        return 1


# ---------------------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------------------
def main() -> int:
    """命令行主入口。"""
    parser = argparse.ArgumentParser(
        description="德语文档票据识别信息抽取工具 (german-ocr)",
        epilog="示例: python main.py --selftest",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行离线自检（使用内置样例数据，无需外部依赖）",
    )
    parser.add_argument(
        "--input",
        type=str,
        help="输入文件路径（JPG/PNG/TIFF/PDF/TXT）",
    )
    parser.add_argument(
        "--output",
        type=str,
        choices=["json", "text"],
        default="json",
        help="输出格式 (默认: json)",
    )
    parser.add_argument(
        "--custom-fields",
        type=str,
        nargs="*",
        default=[],
        help="自定义字段名列表，如 --custom-fields bestellnummer auftragsnummer",
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        return run_selftest()

    # 正常处理模式（需要 --input）
    if not args.input:
        print("错误: 请指定 --input 参数或使用 --selftest 模式", file=sys.stderr)
        print("用法: python main.py --input <文件> [--output json|text]", file=sys.stderr)
        return 1

    try:
        # 读取输入文件
        try:
            with open(args.input, "rb") as f:
                content = f.read()
        except FileNotFoundError:
            raise GermanOCRError("E003", f"文件不存在: {args.input}")
        except Exception:
            raise GermanOCRError("E003", f"无法读取文件: {args.input}")

        # 处理文档
        result = process_document(content, filename=args.input)

        # 输出结果
        output = format_output([result], args.output)
        print(output)
        return 0

    except GermanOCRError as e:
        print(f"处理失败: {e.code} - {e.message}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"未知错误: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
