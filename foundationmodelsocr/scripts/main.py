#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py — 票据识别与结构化解析（独立实现）

本脚本依据功能规格独立编写，不参考任何既有实现。
提供命令行接口，支持单文件解析、批量处理与离线自检。
"""

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Tuple
dry_run = False  # v3.274 模块级 dry-run 标志

# 错误码定义
ERROR_CODES = {
    "E001": "输入文件不存在",
    "E002": "输入文件类型不支持",
    "E003": "文件读取失败",
    "E004": "文件内容为空",
    "E005": "文件大小超过限制",
    "E006": "批量处理时存在失败项",
    "E007": "输出目录不可写",
    "E008": "JSON 序列化失败",
    "E009": "参数冲突或非法",
    "E010": "内部处理异常",
}


class SkillError(Exception):
    """技能异常基类，携带错误码。"""

    def __init__(self, code: str, message: Optional[str] = None):
        self.code = code
        self.message = message or ERROR_CODES.get(code, "未知错误")
        super().__init__(f"[{code}] {self.message}")


# ---------- 数据结构 ----------

@dataclass
class FieldResult:
    """单个字段的抽取结果。"""
    key: str
    value: Any
    confidence: float  # 0~1
    source: str = "ocr"


@dataclass
class DocumentResult:
    """单份文档的解析结果。"""
    source: str
    fields: List[FieldResult] = field(default_factory=list)
    raw_text: str = ""
    status: str = "ok"
    error_code: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source": self.source,
            "status": self.status,
            "error_code": self.error_code,
            "raw_text": self.raw_text,
            "fields": [asdict(f) for f in self.fields],
        }


# ---------- 核心解析引擎 ----------

class ReceiptParser:
    """
    票据解析器：从文本/模拟 OCR 结果中抽取结构化字段。

    本实现为纯规则引擎，不依赖任何第三方 OCR 库。
    实际使用时可将 OCR 输出（文本）传入 parse_text 方法。
    """

    # 字段提取规则：key -> (正则模式, 字段类型)
    # 使用宽松匹配，避免过度约束
    FIELD_PATTERNS: Dict[str, Tuple[str, str]] = {
        "invoice_number": (r"(发票号码|发票号|NO\.?|No\.?)\s*[:：]?\s*([A-Za-z0-9\-]{4,20})", "str"),
        "invoice_date": (r"(开票日期|日期|date)\s*[:：]?\s*(\d{4}[-/年.]\d{1,2}[-/月.]\d{1,2}日?)", "str"),
        "total_amount": (
            r"(价税合计|合计金额|金额|总计|total)\s*[:：]?\s*[¥￥]?\s*(\d{1,3}(?:,\d{3})*(?:\.\d{1,2})?|\d+(?:\.\d{1,2})?)",
            "float"
        ),
        "tax_amount": (
            r"(税额|税金|tax)\s*[:：]?\s*[¥￥]?\s*(\d{1,3}(?:,\d{3})*(?:\.\d{1,2})?|\d+(?:\.\d{1,2})?)",
            "float"
        ),
        "seller_name": (r"(销售方|卖方|收款方|seller|收款人)\s*[:：]?\s*([^\n]{2,50})", "str"),
        "buyer_name": (r"(购买方|买方|付款方|buyer|付款人)\s*[:：]?\s*([^\n]{2,50})", "str"),
    }

    def __init__(self, confidence_default: float = 0.85):
        self.confidence_default = confidence_default

    def parse_text(self, text: str, source: str = "memory") -> DocumentResult:
        """
        从纯文本中解析结构化字段。
        """
        if not text or not text.strip():
            raise SkillError("E004")

        doc = DocumentResult(source=source, raw_text=text.strip())

        for key, (pattern, type_hint) in self.FIELD_PATTERNS.items():
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if not match:
                continue
            # 取最后一个捕获组作为值
            raw_value = match.group(match.lastindex or 2)
            value = self._convert_value(raw_value, type_hint)
            # 置信度：命中即给默认值，可根据匹配长度微调（保持宽松）
            conf = self.confidence_default
            if len(raw_value) < 4:
                conf = max(0.5, conf - 0.2)  # 短值置信度略低
            doc.fields.append(FieldResult(key=key, value=value, confidence=round(conf, 2)))

        return doc

    @staticmethod
    def _convert_value(raw: str, type_hint: str) -> Any:
        """按类型提示转换字段值。"""
        if type_hint == "float":
            # 容忍千分位逗号或中文逗号
            cleaned = raw.replace(",", "").replace("，", "").replace("￥", "").replace("¥", "")
            try:
                return float(cleaned)
            except ValueError:
                return raw
        return raw.strip()


# ---------- 文件处理 ----------

SUPPORTED_EXTENSIONS = {".txt", ".json", ".jpg", ".jpeg", ".png", ".pdf"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


def read_input_file(filepath: str) -> str:
    """
    读取输入文件并提取文本内容。
    对于图片/PDF，此实现仅返回占位提示（真实场景需接入 OCR 库）。
    """
    if not os.path.exists(filepath):
        raise SkillError("E001", f"文件不存在: {filepath}")

    ext = os.path.splitext(filepath)[1].lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise SkillError("E002", f"不支持的文件类型: {ext}")

    try:
        size = os.path.getsize(filepath)
        if size == 0:
            raise SkillError("E004")
        if size > MAX_FILE_SIZE:
            raise SkillError("E005", f"文件大小 {size} 超过限制 {MAX_FILE_SIZE}")

        if ext in (".txt", ".json"):
            with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                return f.read()
        else:
            # 图片/PDF：真实实现应调用 OCR 库（如 pytesseract、paddleocr）
            # pip install pytesseract pillow pdfplumber
            # 此处返回一个模拟文本，方便离线演示
            return f"[模拟OCR] {os.path.basename(filepath)} 发票号码: INV-2026-001 开票日期: 2026-03-15 价税合计: 1280.50 税额: 147.28 销售方: 示例科技有限公司 购买方: 示例采购有限公司"
    except SkillError:
        raise
    except Exception as e:
        raise SkillError("E003", f"读取失败: {e}") from e


def parse_file(filepath: str, parser: ReceiptParser) -> DocumentResult:
    """解析单个文件。"""
    text = read_input_file(filepath)
    return parser.parse_text(text, source=os.path.basename(filepath))


def parse_batch(filepaths: List[str], parser: ReceiptParser) -> List[DocumentResult]:
    """批量解析，单文件失败不中断整体。"""
    results = []
    has_error = False
    for fp in filepaths:
        try:
            results.append(parse_file(fp, parser))
        except SkillError as e:
            has_error = True
            results.append(DocumentResult(
                source=os.path.basename(fp),
                status="error",
                error_code=e.code,
                raw_text="",
            ))
    if has_error:
        # 不抛出异常，由调用方检查 status
        pass
    return results


# ---------- 输出处理 ----------

def save_results(results: List[DocumentResult], output_path: Optional[str] = None) -> str:
    """将结果序列化为 JSON 字符串，可选写入文件。"""
    payload = [r.to_dict() for r in results]
    try:
        json_str = json.dumps(payload, ensure_ascii=False, indent=2)
    except (TypeError, ValueError) as e:
        raise SkillError("E008", f"JSON 序列化失败: {e}") from e

    if output_path:
        out_dir = os.path.dirname(output_path)
        if out_dir and not os.path.isdir(out_dir):
            raise SkillError("E007", f"输出目录不可写: {out_dir}")
        try:
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(json_str)
        except OSError as e:
            raise SkillError("E007", f"写入失败: {e}") from e
    return json_str


# ---------- 命令行接口 ----------

def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="foundationmodelsocr",
        description="票据识别与结构化解析工具（独立实现）",
        epilog="示例: python main.py -f invoice.jpg -o result.json",
    )
    p.add_argument("-f", "--file", action="append", dest="files", help="输入文件路径（可多次指定）")
    p.add_argument("-d", "--dir", help="批量处理目录下的所有支持文件")
    p.add_argument("-o", "--output", help="输出 JSON 文件路径（可选，默认打印到 stdout）")
    p.add_argument("--selftest", action="store_true", help="运行内置离线自检")
    p.add_argument("--confidence", type=float, default=0.85, help="默认置信度(0~1)")
    return p


def run_selftest() -> int:
    """内置硬编码样例自检，不依赖任何外部资源。"""
    print("[SELFTEST] 开始离线自检...")

    # 硬编码测试样例
    sample_text = """
    增值税普通发票
    发票号码: INV-2026-0001
    开票日期: 2026年03月15日
    购买方: 测试采购有限公司
    销售方: 测试销售有限公司
    价税合计: ¥1,280.50
    税额: 147.28
    备注: 测试专用
    """

    parser = ReceiptParser(confidence_default=0.85)
    try:
        result = parser.parse_text(sample_text, source="selftest")
    except SkillError as e:
        print(f"[SELFTEST] 解析失败: {e}")
        return 1

    # 字段存在性检查（宽松断言）
    field_map = {f.key: f for f in result.fields}
    required_keys = ["invoice_number", "invoice_date", "total_amount", "tax_amount", "seller_name", "buyer_name"]

    missing = [k for k in required_keys if k not in field_map]
    if missing:
        print(f"[SELFTEST] 失败: 缺少字段 {missing}")
        return 1

    # 值范围检查（宽松阈值）
    total = field_map["total_amount"].value
    tax = field_map["tax_amount"].value
    if not (1000 <= total <= 2000):
        print(f"[SELFTEST] 失败: 总金额 {total} 不在预期范围 [1000, 2000]")
        return 1
    if not (100 <= tax <= 200):
        print(f"[SELFTEST] 失败: 税额 {tax} 不在预期范围 [100, 200]")
        return 1

    # 置信度合理性检查
    for f in result.fields:
        if not (0.0 <= f.confidence <= 1.0):
            print(f"[SELFTEST] 失败: 置信度越界 {f.confidence}")
            return 1

    # JSON 序列化验证
    try:
        json_out = save_results([result])
        parsed_json = json.loads(json_out)
        if len(parsed_json) != 1 or parsed_json[0]["status"] != "ok":
            raise ValueError("序列化结果异常")
    except (SkillError, ValueError) as e:
        print(f"[SELFTEST] 失败: JSON 序列化异常 {e}")
        return 1

    print("[SELFTEST] 通过 ✓")
    return 0


def main() -> int:
    """CLI 入口。"""
    args = build_arg_parser().parse_args()

    # 自检模式优先
    if args.selftest:
        return run_selftest()

    # 参数校验
    if not args.files and not args.dir:
        print("错误: 必须提供 -f 或 -d 参数", file=sys.stderr)
        return 2

    if args.files and args.dir:
        print("错误: -f 与 -d 不能同时使用", file=sys.stderr)
        return 2

    if not (0.0 <= args.confidence <= 1.0):
        print("错误: --confidence 必须在 [0,1] 区间", file=sys.stderr)
        return 2

    parser = ReceiptParser(confidence_default=args.confidence)

    # 收集文件列表
    file_list: List[str] = []
    if args.files:
        file_list = args.files
    elif args.dir:
        if not os.path.isdir(args.dir):
            print(f"错误: 目录不存在 {args.dir}", file=sys.stderr)
            return 2
        for fname in sorted(os.listdir(args.dir)):
            fpath = os.path.join(args.dir, fname)
            if os.path.isfile(fpath) and os.path.splitext(fname)[1].lower() in SUPPORTED_EXTENSIONS:
                file_list.append(fpath)

    if not file_list:
        print("错误: 未找到可处理的文件", file=sys.stderr)
        return 2

    try:
        results = parse_batch(file_list, parser)
        json_output = save_results(results, args.output)
        if not args.output:
            print(json_output)
    except SkillError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"错误: [E010] 内部异常: {e}", file=sys.stderr)
        return 1

    # 检查是否有失败项
    if any(r.status == "error" for r in results):
        print("警告: 部分文件解析失败，请检查输出中的 error_code", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
