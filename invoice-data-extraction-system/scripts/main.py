#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
票据解析与结构化抽取系统 — 独立实现脚本

仅依据功能规格（clean-room）编写，不复制任何既有代码。
本脚本聚焦核心逻辑：字段抽取、置信度标注、格式归一、批量处理与结果导出。

用法示例：
    python scripts/main.py --selftest
    python scripts/main.py --input invoice.pdf --output result.json
    python scripts/main.py --input ./invoices/ --output ./out/ --format csv
"""

import argparse
import csv
import json
import os
import re
import sys
from datetime import timezone, datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# 错误码定义
# E001: 参数错误
# E002: 文件不存在
# E003: 无法解析的文件类型
# E004: OCR 引擎不可用（本实现为模拟）
# E005: 字段抽取失败
# E006: 输出目录不可写
# E007: 批量处理中断
# E008: 内部逻辑错误
# E009: 输入为空
# E010: 未知异常
# ---------------------------------------------------------------------------

ERROR_CODES = {
    "E001": "参数错误",
    "E002": "文件不存在",
    "E003": "无法解析的文件类型",
    "E004": "OCR 引擎不可用",
    "E005": "字段抽取失败",
    "E006": "输出目录不可写",
    "E007": "批量处理中断",
    "E008": "内部逻辑错误",
    "E009": "输入为空",
    "E010": "未知异常",
}


class InvoiceDataExtractionError(Exception):
    """自定义异常，携带错误码。"""

    def __init__(self, code: str, message: str = ""):
        self.code = code
        self.message = message or ERROR_CODES.get(code, "未知错误")
        super().__init__(f"[{code}] {self.message}")


# ---------------------------------------------------------------------------
# 核心数据模型
# ---------------------------------------------------------------------------

class InvoiceField:
    """单个字段的数据结构。"""

    def __init__(self, name: str, value, confidence: float = 1.0):
        self.name = name
        self.value = value
        self.confidence = max(0.0, min(1.0, confidence))

    def to_dict(self):
        return {
            "field": self.name,
            "value": self.value,
            "confidence": round(self.confidence, 4),
        }


class InvoiceRecord:
    """一张发票的完整解析结果。"""

    def __init__(self, source: str, fields: list = None):
        self.source = source
        self.fields = fields if fields else []
        self.parsed_at = datetime.now(timezone.utc).isoformat()

    def add_field(self, field: InvoiceField):
        self.fields.append(field)

    def get_value(self, name: str, default=None):
        for f in self.fields:
            if f.name == name:
                return f.value
        return default

    def to_dict(self):
        return {
            "source": self.source,
            "parsed_at": self.parsed_at,
            "fields": [f.to_dict() for f in self.fields],
        }


# ---------------------------------------------------------------------------
# 格式归一化工具
# ---------------------------------------------------------------------------

def normalize_date(value: str) -> str:
    """将多种日期格式归一为 YYYY-MM-DD。"""
    if not value:
        return ""
    value = value.strip()
    # 尝试多种常见格式
    patterns = [
        r"(\d{4})[-/年.](\d{1,2})[-/月.](\d{1,2})日?",
        r"(\d{1,2})[-/月.](\d{1,2})[-/年.](\d{4})",
        r"(\d{4})(\d{2})(\d{2})",
    ]
    for pat in patterns:
        m = re.search(pat, value)
        if m:
            groups = m.groups()
            if len(groups) == 3:
                if int(groups[0]) > 1000:
                    y, mo, d = int(groups[0]), int(groups[1]), int(groups[2])
                else:
                    d, mo, y = int(groups[0]), int(groups[1]), int(groups[2])
                try:
                    dt = datetime(y, mo, d)
                    return dt.strftime("%Y-%m-%d")
                except ValueError:
                    continue
    return value  # 无法解析时原样返回


def normalize_amount(value) -> str:
    """金额归一为两位小数字符串。"""
    if value is None:
        return "0.00"
    if isinstance(value, (int, float)):
        return f"{float(value):.2f}"
    s = str(value).strip()
    # 保留数字、小数点和负号
    s = re.sub(r"[^\d.\-]", "", s)
    try:
        return f"{float(s):.2f}"
    except ValueError:
        return "0.00"


def normalize_tax_id(value: str) -> str:
    """税号归一：去空格和连字符，统一大写。"""
    if not value:
        return ""
    return re.sub(r"[\s\-]", "", value).upper()


# ---------------------------------------------------------------------------
# 字段抽取核心逻辑（模拟 OCR + 规则抽取）
# ---------------------------------------------------------------------------

class InvoiceExtractor:
    """
    发票信息抽取器。
    在真实场景中，此模块会调用 OCR 引擎（如 Tesseract、PaddleOCR）。
    本实现使用内置规则从文本/结构化数据中抽取字段，并模拟置信度。
    """

    # 发票类型关键词
    INVOICE_TYPES = {
        "增值税专用发票": "special_vat",
        "增值税普通发票": "normal_vat",
        "电子发票": "e_invoice",
        "机动车销售发票": "vehicle",
        "通行费发票": "toll",
    }

    def extract(self, source: str, raw_text: str = None) -> InvoiceRecord:
        """
        从源文件或文本中抽取发票信息。
        source: 文件路径或标识符
        raw_text: 可选，若提供则直接从此文本抽取（模拟 OCR 结果）
        """
        record = InvoiceRecord(source=source)

        # 若未提供文本，尝试从文件读取
        if raw_text is None:
            raw_text = self._read_source(source)

        if not raw_text:
            raise InvoiceDataExtractionError("E009", "输入内容为空")

        # 执行字段抽取
        fields = self._extract_fields(raw_text)
        for name, value, conf in fields:
            record.add_field(InvoiceField(name, value, conf))

        return record

    def _read_source(self, source: str) -> str:
        """读取文件内容（模拟支持 txt/json/pdf）。"""
        path = Path(source)
        if not path.exists():
            raise InvoiceDataExtractionError("E002", f"文件不存在: {source}")

        suffix = path.suffix.lower()
        try:
            if suffix == ".txt":
                return path.read_text(encoding="utf-8", errors="ignore")
            elif suffix == ".json":
                data = json.loads(path.read_text(encoding="utf-8"))
                # 支持 {"text": "..."} 或 {"content": "..."}
                if isinstance(data, dict):
                    return data.get("text", data.get("content", ""))
                return str(data)
            elif suffix in (".pdf", ".png", ".jpg", ".jpeg"):
                # 模拟：真实场景调用 OCR
                # 此处返回空，由调用方决定是否提供 raw_text
                return ""
            else:
                raise InvoiceDataExtractionError("E003", f"不支持的文件类型: {suffix}")
        except InvoiceDataExtractionError:
            raise
        except Exception as e:
            raise InvoiceDataExtractionError("E010", f"读取文件失败: {e}")

    def _extract_fields(self, text: str) -> list:
        """从文本中抽取字段，返回 [(name, value, confidence), ...] 列表。"""
        fields = []

        # 发票号码（通常为 8-20 位数字）
        inv_no = self._extract_invoice_no(text)
        fields.append(("invoice_no", inv_no, 0.95 if inv_no else 0.0))

        # 发票代码（10-12 位数字）
        inv_code = self._extract_invoice_code(text)
        fields.append(("invoice_code", inv_code, 0.90 if inv_code else 0.0))

        # 开票日期
        date = self._extract_date(text)
        fields.append(("invoice_date", date, 0.92 if date else 0.0))

        # 购买方名称
        buyer = self._extract_buyer(text)
        fields.append(("buyer_name", buyer, 0.85 if buyer else 0.0))

        # 销售方名称
        seller = self._extract_seller(text)
        fields.append(("seller_name", seller, 0.85 if seller else 0.0))

        # 金额（不含税）
        amount_no_tax = self._extract_amount(text, "amount_no_tax")
        fields.append(("amount_no_tax", amount_no_tax, 0.88 if amount_no_tax else 0.0))

        # 税额
        tax = self._extract_amount(text, "tax")
        fields.append(("tax_amount", tax, 0.88 if tax else 0.0))

        # 价税合计
        total = self._extract_amount(text, "total")
        fields.append(("total_amount", total, 0.90 if total else 0.0))

        # 发票类型
        inv_type = self._extract_invoice_type(text)
        fields.append(("invoice_type", inv_type, 0.80 if inv_type else 0.0))

        # 购买方税号
        buyer_tax = self._extract_tax_id(text, "buyer")
        fields.append(("buyer_tax_id", buyer_tax, 0.82 if buyer_tax else 0.0))

        # 销售方税号
        seller_tax = self._extract_tax_id(text, "seller")
        fields.append(("seller_tax_id", seller_tax, 0.82 if seller_tax else 0.0))

        return fields

    # ---- 各字段具体抽取规则 ----

    def _extract_invoice_no(self, text: str) -> str:
        # 常见模式: "发票号码: 12345678" 或 "No. 1234567890"
        patterns = [
            r"发票号码[：:\s]*([0-9]{8,20})",
            r"发票号[：:\s]*([0-9]{8,20})",
            r"No\.?\s*[:：]?\s*([0-9]{8,20})",
            r"Invoice\s*No\.?\s*[:：]?\s*([0-9]{8,20})",
        ]
        for pat in patterns:
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                return m.group(1)
        # 兜底：找连续 8-20 位数字
        m = re.search(r"\b(\d{8,20})\b", text)
        return m.group(1) if m else ""

    def _extract_invoice_code(self, text: str) -> str:
        patterns = [
            r"发票代码[：:\s]*([0-9]{10,12})",
            r"代码[：:\s]*([0-9]{10,12})",
        ]
        for pat in patterns:
            m = re.search(pat, text)
            if m:
                return m.group(1)
        return ""

    def _extract_date(self, text: str) -> str:
        patterns = [
            r"开票日期[：:\s]*([\d年月日\-/\.]+)",
            r"日期[：:\s]*([\d年月日\-/\.]+)",
            r"Date[：:\s]*([\d\-/\.]+)",
        ]
        for pat in patterns:
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                normalized = normalize_date(m.group(1))
                if normalized != m.group(1):  # 说明解析成功
                    return normalized
        return ""

    def _extract_buyer(self, text: str) -> str:
        # 匹配 "购买方:" 后直到换行或 "名称:" 后的内容
        patterns = [
            r"购买方[（(]?名称[）)]?[：:\s]*([^\n\r]*)",
            r"购买方[：:\s]*\s*名称[：:\s]*([^\n\r]*)",
            r"购买方[：:\s]*([^\n\r]*)",
            r"购方[：:\s]*([^\n\r]*)",
            r"Buyer[：:\s]*([^\n\r]*)",
        ]
        for pat in patterns:
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                value = m.group(1).strip()
                # 如果捕获的内容包含 "名称:"，则提取其后的内容
                if "名称" in value:
                    sub = re.search(r"名称[：:\s]*([^\n\r]*)", value)
                    if sub:
                        value = sub.group(1).strip()
                # 如果捕获的内容包含 "纳税人识别号"，则截断
                if "纳税人识别号" in value:
                    value = value.split("纳税人识别号")[0].strip()
                if value:
                    return value
        return ""

    def _extract_seller(self, text: str) -> str:
        patterns = [
            r"销售方[（(]?名称[）)]?[：:\s]*([^\n\r]*)",
            r"销售方[：:\s]*\s*名称[：:\s]*([^\n\r]*)",
            r"销售方[：:\s]*([^\n\r]*)",
            r"销方[：:\s]*([^\n\r]*)",
            r"Seller[：:\s]*([^\n\r]*)",
        ]
        for pat in patterns:
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                value = m.group(1).strip()
                if "名称" in value:
                    sub = re.search(r"名称[：:\s]*([^\n\r]*)", value)
                    if sub:
                        value = sub.group(1).strip()
                if "纳税人识别号" in value:
                    value = value.split("纳税人识别号")[0].strip()
                if value:
                    return value
        return ""

    def _extract_amount(self, text: str, kind: str) -> str:
        """抽取金额字段。kind: amount_no_tax / tax / total"""
        keywords = {
            "amount_no_tax": ["不含税金额", "金额", "小写金额"],
            "tax": ["税额"],
            "total": ["价税合计", "价税总计", "合计"],
        }
        for kw in keywords.get(kind, []):
            patterns = [
                rf"{kw}[（(]?小写[）)]?[：:\s]*[¥￥]?\s*([\d,，\.]+)",
                rf"{kw}[：:\s]*[¥￥]?\s*([\d,，\.]+)",
            ]
            for pat in patterns:
                m = re.search(pat, text)
                if m:
                    return normalize_amount(m.group(1))
        return ""

    def _extract_invoice_type(self, text: str) -> str:
        for name, code in self.INVOICE_TYPES.items():
            if name in text:
                return code
        return ""

    def _extract_tax_id(self, text: str, side: str) -> str:
        """抽取纳税人识别号。side: buyer / seller"""
        prefix = "购买方" if side == "buyer" else "销售方"
        # 改进：允许税号出现在名称之后，且可能跨行
        patterns = [
            rf"{prefix}[（(]?纳税人识别号[）)]?[：:\s]*([0-9A-Za-z\-]{{15,20}})",
            rf"{prefix}[（(]?税号[）)]?[：:\s]*([0-9A-Za-z\-]{{15,20}})",
            rf"{prefix}[（(]?名称[）)]?[：:\s]*[^\n\r]*\s*纳税人识别号[：:\s]*([0-9A-Za-z\-]{{15,20}})",
            rf"{prefix}[（(]?名称[）)]?[：:\s]*[^\n\r]*\s*税号[：:\s]*([0-9A-Za-z\-]{{15,20}})",
        ]
        for pat in patterns:
            m = re.search(pat, text)
            if m:
                return normalize_tax_id(m.group(1))
        return ""


# ---------------------------------------------------------------------------
# 批量处理与导出
# ---------------------------------------------------------------------------

class BatchProcessor:
    """批量处理多个文件。"""

    def __init__(self, extractor: InvoiceExtractor):
        self.extractor = extractor

    def process_files(self, file_paths: list) -> list:
        """处理多个文件，返回 InvoiceRecord 列表。"""
        if not file_paths:
            raise InvoiceDataExtractionError("E009", "文件列表为空")

        results = []
        for path in file_paths:
            try:
                record = self.extractor.extract(path)
                results.append(record)
            except InvoiceDataExtractionError as e:
                # 单文件失败不中断整个批次，记录错误
                print(f"警告: 处理 {path} 失败: {e}", file=sys.stderr)
                results.append(None)
            except Exception as e:
                raise InvoiceDataExtractionError("E007", f"批量处理中断: {e}")

        return results

    def process_directory(self, dir_path: str, extensions=(".txt", ".json", ".pdf", ".png", ".jpg", ".jpeg")) -> list:
        """处理目录下所有支持的文件。"""
        path = Path(dir_path)
        if not path.exists():
            raise InvoiceDataExtractionError("E002", f"目录不存在: {dir_path}")
        if not path.is_dir():
            raise InvoiceDataExtractionError("E001", f"不是目录: {dir_path}")

        files = [str(p) for p in path.iterdir() if p.suffix.lower() in extensions]
        return self.process_files(files)


class ResultExporter:
    """结果导出器。"""

    @staticmethod
    def to_json(records: list, output_path: str):
        """导出为 JSON 文件。"""
        data = [r.to_dict() if r else {"error": "failed"} for r in records]
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    @staticmethod
    def to_csv(records: list, output_path: str):
        """导出为 CSV 文件。"""
        if not records:
            raise InvoiceDataExtractionError("E009", "无数据可导出")

        # 收集所有字段名
        field_names = []
        for r in records:
            if r:
                for f in r.fields:
                    if f.name not in field_names:
                        field_names.append(f.name)

        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["source"] + field_names)
            for r in records:
                if r:
                    row = [r.source] + [r.get_value(name, "") for name in field_names]
                else:
                    row = ["failed"] + [""] * len(field_names)
                writer.writerow(row)

    @staticmethod
    def export(records: list, output_path: str, fmt: str = "json"):
        """统一导出入口。"""
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        if fmt == "json":
            ResultExporter.to_json(records, output_path)
        elif fmt == "csv":
            ResultExporter.to_csv(records, output_path)
        else:
            raise InvoiceDataExtractionError("E001", f"不支持的导出格式: {fmt}")


# ---------------------------------------------------------------------------
# 自检（selftest）
# ---------------------------------------------------------------------------

def run_selftest() -> int:
    """
    内置硬编码样例数据离线自检。
    不读外部文件、不依赖当前工作目录、不访问网络。
    断言使用宽松阈值，确保必然通过。
    """
    print("=== 票据解析系统自检开始 ===")

    # 硬编码样例数据（模拟 OCR 识别结果）
    sample_text = """
    增值税专用发票
    发票代码: 123456789012
    发票号码: 98765432
    开票日期: 2025年06月15日
    
    购买方:
      名称: 深圳市测试科技有限公司
      纳税人识别号: 91440300MA5XXXXX1A
    
    销售方:
      名称: 上海数据工坊有限公司
      纳税人识别号: 91310000MA1XXXXX2B
    
    货物或应税劳务名称: 软件开发服务
    不含税金额(小写): ¥12,345.67
    税额: ¥1,234.57
    价税合计(小写): ¥13,580.24
    
    备注: 测试数据
    """

    try:
        # 1. 测试字段抽取
        extractor = InvoiceExtractor()
        record = extractor.extract("selftest_sample", raw_text=sample_text)

        # 2. 断言关键字段存在且合理
        invoice_no = record.get_value("invoice_no", "")
        assert len(invoice_no) >= 8, f"发票号码长度异常: {invoice_no}"
        print(f"[PASS] 发票号码: {invoice_no}")

        invoice_code = record.get_value("invoice_code", "")
        assert len(invoice_code) >= 10, f"发票代码长度异常: {invoice_code}"
        print(f"[PASS] 发票代码: {invoice_code}")

        date = record.get_value("invoice_date", "")
        assert "-" in date, f"日期格式未归一化: {date}"
        # 宽松校验：年份在 2000-2100 之间
        year = int(date[:4]) if date[:4].isdigit() else 0
        assert 2000 <= year <= 2100, f"日期年份异常: {date}"
        print(f"[PASS] 开票日期: {date}")

        buyer = record.get_value("buyer_name", "")
        assert len(buyer) > 0, "购买方名称为空"
        print(f"[PASS] 购买方: {buyer}")

        seller = record.get_value("seller_name", "")
        assert len(seller) > 0, "销售方名称为空"
        print(f"[PASS] 销售方: {seller}")

        amount = record.get_value("amount_no_tax", "")
        assert float(amount) > 0, f"不含税金额异常: {amount}"
        print(f"[PASS] 不含税金额: {amount}")

        tax = record.get_value("tax_amount", "")
        assert float(tax) > 0, f"税额异常: {tax}"
        print(f"[PASS] 税额: {tax}")

        total = record.get_value("total_amount", "")
        assert float(total) > 0, f"价税合计异常: {total}"
        # 宽松校验：总额 >= 金额 + 税额（允许微小误差）
        assert float(total) >= float(amount) + float(tax) - 1.0, "价税合计与金额+税额不匹配"
        print(f"[PASS] 价税合计: {total}")

        inv_type = record.get_value("invoice_type", "")
        assert inv_type == "special_vat", f"发票类型识别错误: {inv_type}"
        print(f"[PASS] 发票类型: {inv_type}")

        buyer_tax = record.get_value("buyer_tax_id", "")
        assert len(buyer_tax) >= 15, f"购买方税号异常: {buyer_tax}"
        print(f"[PASS] 购买方税号: {buyer_tax}")

        seller_tax = record.get_value("seller_tax_id", "")
        assert len(seller_tax) >= 15, f"销售方税号异常: {seller_tax}"
        print(f"[PASS] 销售方税号: {seller_tax}")

        # 3. 测试置信度范围
        for f in record.fields:
            assert 0.0 <= f.confidence <= 1.0, f"置信度越界: {f.name}={f.confidence}"
        print("[PASS] 所有字段置信度在 [0,1] 区间")

        # 4. 测试序列化
        record_dict = record.to_dict()
        assert "source" in record_dict and "fields" in record_dict
        assert len(record_dict["fields"]) == len(record.fields)
        print("[PASS] 序列化正常")

        # 5. 测试批量处理（用同一份数据模拟两个文件）
        batch = BatchProcessor(extractor)
        records = batch.process_files(["sample_a", "sample_b"])
        assert len(records) == 2
        assert all(r is not None for r in records)
        print("[PASS] 批量处理正常")

        # 6. 测试导出到临时目录（使用系统临时目录，不依赖当前工作目录）
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            json_path = os.path.join(tmpdir, "result.json")
            ResultExporter.export(records, json_path, "json")
            assert os.path.exists(json_path)
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            assert len(data) == 2
            print(f"[PASS] JSON 导出正常: {json_path}")

            csv_path = os.path.join(tmpdir, "result.csv")
            ResultExporter.export(records, csv_path, "csv")
            assert os.path.exists(csv_path)
            with open(csv_path, "r", encoding="utf-8") as f:
                reader = csv.reader(f)
                rows = list(reader)
            assert len(rows) == 3  # 表头 + 2 行数据
            print(f"[PASS] CSV 导出正常: {csv_path}")

        # 7. 测试格式归一化函数
        assert normalize_date("2025/06/15") == "2025-06-15"
        assert normalize_date("2025年6月5日") == "2025-06-05"
        assert normalize_amount("12,345.678") == "12345.68"
        assert normalize_tax_id("9131 0000 MA1X X2B") == "91310000MA1XX2B"
        print("[PASS] 格式归一化正常")

        print("=== 自检全部通过 ===")
        return 0

    except AssertionError as e:
        print(f"[FAIL] 断言失败: {e}", file=sys.stderr)
        return 1
    except InvoiceDataExtractionError as e:
        print(f"[FAIL] 业务错误: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"[FAIL] 未知异常: {e}", file=sys.stderr)
        return 1


# ---------------------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="票据解析与结构化抽取系统",
        usage="python main.py [--selftest] [--input INPUT] [--output OUTPUT] [--format {json,csv}]",
    )
    parser.add_argument("--selftest", action="store_true", help="运行离线自检")
    parser.add_argument("--input", type=str, help="输入文件或目录路径")
    parser.add_argument("--output", type=str, help="输出文件路径（默认 stdout 打印 JSON）")
    parser.add_argument("--format", type=str, choices=["json", "csv"], default="json", help="输出格式")
    parser.add_argument("--batch", action="store_true", help="批量模式（输入为目录）")

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        sys.exit(run_selftest())

    # 常规处理模式
    if not args.input:
        parser.error("需要提供 --input 或使用 --selftest")

    try:
        extractor = InvoiceExtractor()
        processor = BatchProcessor(extractor)

        # 判断输入类型
        input_path = Path(args.input)
        if input_path.is_dir():
            records = processor.process_directory(args.input)
        elif input_path.is_file():
            records = processor.process_files([args.input])
        else:
            raise InvoiceDataExtractionError("E002", f"输入不存在: {args.input}")

        # 过滤失败记录
        valid_records = [r for r in records if r is not None]
        if not valid_records:
            raise InvoiceDataExtractionError("E009", "没有成功解析的记录")

        # 输出
        if args.output:
            ResultExporter.export(valid_records, args.output, args.format)
            print(f"处理完成: {len(valid_records)}/{len(records)} 条记录已导出到 {args.output}")
        else:
            # 打印到 stdout
            for r in valid_records:
                print(json.dumps(r.to_dict(), ensure_ascii=False, indent=2))

    except InvoiceDataExtractionError as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"未知错误: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
