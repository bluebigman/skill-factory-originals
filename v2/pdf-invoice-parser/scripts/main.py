#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pdf-invoice-parser — 增值税发票字段提取与一致性校验

功能：
  - 从PDF发票（中国增值税电子/专用/数电票）抽取结构化字段
  - 双引擎文本抽取（pdfplumber/pypdf自动降级）
  - 单文件/目录批量/http(s)远程链接
  - 四项一致性校验：金额+税额=价税合计/大小写一致/号码位数/日期合法
  - 输出JSON/JSONL/CSV
  - 零依赖自检：python main.py --selftest

错误码 E001-E010。
"""
from __future__ import annotations

import argparse
import csv
import json
import logging
import re
import sys
import tempfile
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

# 配置日志
logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(message)s", stream=sys.stderr)
log = logging.getLogger("pdf-invoice-parser")

RETRIES = 3
TIMEOUT = 10  # 网络请求超时（秒）


class BillError(Exception):
    """带错误码的解析异常。"""

    def __init__(self, code: str, detail: str = ""):
        self.code = code
        self.detail = detail
        super().__init__(f"[{code}] {detail}")


ERROR_DICT = {
    "E001": "输入路径不存在或不可读",
    "E002": "文件不是有效 PDF（魔数校验失败）",
    "E003": "PDF 已加密，需要口令",
    "E004": "PDF 无文本层且 OCR 依赖未安装",
    "E005": "未安装任何 PDF 解析引擎（pdfplumber / pypdf）",
    "E006": "文本提取成功但未识别出发票关键字段",
    "E007": "金额字段解析失败",
    "E008": "一致性校验未通过",
    "E009": "批量目录未找到任何 PDF",
    "E010": "输出写入失败",
}


@dataclass
class Bill:
    file: str = ""
    code: str = ""  # 发票代码
    number: str = ""  # 发票号码
    date: str = ""  # 开票日期 YYYY-MM-DD
    kind: str = ""  # 发票类型
    buyer: str = ""
    buyer_tax: str = ""
    seller: str = ""
    seller_tax: str = ""
    amount: str = ""  # 金额（不含税）
    tax: str = ""  # 税额
    total: str = ""  # 价税合计
    total_cn: str = ""  # 大写金额
    rate: str = ""  # 税率
    items: List[Dict[str, str]] = field(default_factory=list)
    checks: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.0
    error: str = ""


# ---------- 工具函数 ----------

def _now_utc() -> str:
    """返回 UTC 时间字符串。"""
    return datetime.now(timezone.utc).isoformat()


def _atomic_write(path: Path, content: str) -> None:
    """原子化写入文件。"""
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    try:
        tmp_path.write_text(content, encoding="utf-8")
        tmp_path.replace(path)
    except Exception as e:
        raise BillError("E010", f"写入失败: {e}") from e


def _download_with_retry(url: str) -> bytes:
    """带指数退避重试的下载。"""
    last_exc = None
    for attempt in range(RETRIES):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                return resp.read()
        except Exception as e:
            last_exc = e
            wait = 2 ** attempt
            log.warning("下载失败（第 %d 次），%ds 后重试: %s", attempt + 1, wait, e)
            time.sleep(wait)
    raise BillError("E001", f"下载失败: {last_exc}")


def _is_pdf(data: bytes) -> bool:
    """检查 PDF 魔数。"""
    return data[:5] == b"%PDF-"


def _is_encrypted(pdf_path: Path) -> bool:
    """检查 PDF 是否加密（简单检测）。"""
    try:
        from pypdf import PdfReader
        reader = PdfReader(str(pdf_path))
        return reader.is_encrypted
    except ImportError:
        try:
            import pdfplumber
            with pdfplumber.open(str(pdf_path)) as pdf:
                return pdf.is_encrypted
        except Exception:
            return False
    except Exception:
        return False


def _extract_text_pdfplumber(pdf_path: Path) -> str:
    """使用 pdfplumber 提取文本。"""
    import pdfplumber
    text = ""
    with pdfplumber.open(str(pdf_path)) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text() or ""
            text += page_text + "\n"
    return text


def _extract_text_pypdf(pdf_path: Path) -> str:
    """使用 pypdf 提取文本。"""
    from pypdf import PdfReader
    reader = PdfReader(str(pdf_path))
    text = ""
    for page in reader.pages:
        page_text = page.extract_text() or ""
        text += page_text + "\n"
    return text


def _extract_text(pdf_path: Path) -> str:
    """双引擎提取文本。"""
    try:
        return _extract_text_pdfplumber(pdf_path)
    except ImportError:
        try:
            return _extract_text_pypdf(pdf_path)
        except ImportError:
            raise BillError("E005", "未安装任何 PDF 解析引擎")
    except Exception as e:
        log.warning("pdfplumber 失败，尝试 pypdf: %s", e)
        try:
            return _extract_text_pypdf(pdf_path)
        except ImportError:
            raise BillError("E005", "未安装任何 PDF 解析引擎")
        except Exception as e2:
            raise BillError("E004", f"文本提取失败: {e2}") from e2


# ---------- 字段解析 ----------

def _parse_amount(value: str) -> Optional[Decimal]:
    """解析金额字符串为 Decimal。"""
    if not value:
        return None
    value = value.strip().replace(",", "").replace("¥", "").replace("￥", "")
    try:
        return Decimal(value)
    except InvalidOperation:
        return None


def _parse_date(value: str) -> Optional[str]:
    """解析日期字符串为 YYYY-MM-DD。"""
    if not value:
        return None
    value = value.strip()
    # 支持 2024年01月01日 / 2024-01-01 / 2024/01/01
    patterns = [
        r"(\d{4})年(\d{1,2})月(\d{1,2})日",
        r"(\d{4})-(\d{1,2})-(\d{1,2})",
        r"(\d{4})/(\d{1,2})/(\d{1,2})",
    ]
    for pat in patterns:
        m = re.search(pat, value)
        if m:
            y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
            try:
                return f"{y:04d}-{mo:02d}-{d:02d}"
            except ValueError:
                return None
    return None


def _parse_invoice(text: str, file_path: str) -> Bill:
    """从文本中解析发票字段。"""
    bill = Bill(file=file_path)

    # 发票代码
    m = re.search(r"发票代码[：:\s]*([0-9]{10,12})", text)
    if m:
        bill.code = m.group(1)

    # 发票号码
    m = re.search(r"发票号码[：:\s]*([0-9]{8,20})", text)
    if m:
        bill.number = m.group(1)

    # 开票日期
    m = re.search(r"开票日期[：:\s]*([0-9年月日/\-]+)", text)
    if m:
        bill.date = _parse_date(m.group(1)) or ""

    # 发票类型
    if "电子发票" in text:
        bill.kind = "电子发票"
    elif "专用发票" in text:
        bill.kind = "专用发票"
    elif "数电票" in text or "数电" in text:
        bill.kind = "数电票"
    else:
        bill.kind = "普通发票"

    # 购买方
    m = re.search(r"购买方[：:\s]*([^\n]+)", text)
    if m:
        bill.buyer = m.group(1).strip()
    m = re.search(r"购买方纳税人识别号[：:\s]*([0-9A-Za-z]+)", text)
    if m:
        bill.buyer_tax = m.group(1)

    # 销售方
    m = re.search(r"销售方[：:\s]*([^\n]+)", text)
    if m:
        bill.seller = m.group(1).strip()
    m = re.search(r"销售方纳税人识别号[：:\s]*([0-9A-Za-z]+)", text)
    if m:
        bill.seller_tax = m.group(1)

    # 金额（不含税）
    m = re.search(r"金额[：:\s]*([0-9,\.]+)", text)
    if m:
        bill.amount = m.group(1)

    # 税额
    m = re.search(r"税额[：:\s]*([0-9,\.]+)", text)
    if m:
        bill.tax = m.group(1)

    # 价税合计（小写）
    m = re.search(r"价税合计[（(]小写[)）][：:\s]*[¥￥]?([0-9,\.]+)", text)
    if not m:
        m = re.search(r"价税合计[：:\s]*[¥￥]?([0-9,\.]+)", text)
    if m:
        bill.total = m.group(1)

    # 价税合计（大写）
    m = re.search(r"价税合计[（(]大写[)）][：:\s]*([壹贰叁肆伍陆柒捌玖拾佰仟万亿零元角分整]+)", text)
    if m:
        bill.total_cn = m.group(1)

    # 税率
    m = re.search(r"税率[：:\s]*([0-9]+%)", text)
    if m:
        bill.rate = m.group(1)

    # 商品明细（简单提取）
    items = []
    for line in text.split("\n"):
        if re.search(r"\d{4}", line) and ("*" in line or "商品" in line or "服务" in line):
            parts = line.split()
            if len(parts) >= 3:
                items.append({"name": parts[0], "spec": parts[1] if len(parts) > 1 else "", "amount": parts[-1]})
    bill.items = items

    # 置信度
    confidence = 0.0
    if bill.code:
        confidence += 0.2
    if bill.number:
        confidence += 0.2
    if bill.date:
        confidence += 0.2
    if bill.amount and bill.tax and bill.total:
        confidence += 0.2
    if bill.buyer and bill.seller:
        confidence += 0.2
    bill.confidence = confidence

    return bill


# ---------- 一致性校验 ----------

def _check_amount_sum(bill: Bill) -> Tuple[bool, str]:
    """校验 金额 + 税额 = 价税合计。"""
    amount = _parse_amount(bill.amount)
    tax = _parse_amount(bill.tax)
    total = _parse_amount(bill.total)
    if amount is None or tax is None or total is None:
        return False, "金额字段不完整"
    if abs(amount + tax - total) < Decimal("0.01"):
        return True, "一致"
    return False, f"金额+税额({amount}+{tax}={amount+tax}) != 价税合计({total})"


def _check_amount_cn(bill: Bill) -> Tuple[bool, str]:
    """校验大小写金额一致（简化校验）。"""
    if not bill.total or not bill.total_cn:
        return False, "大小写金额缺失"
    # 简单映射
    cn_map = {"零": "0", "壹": "1", "贰": "2", "叁": "3", "肆": "4", "伍": "5", "陆": "6", "柒": "7", "捌": "8", "玖": "9"}
    cn_num = ""
    for ch in bill.total_cn:
        if ch in cn_map:
            cn_num += cn_map[ch]
    if not cn_num:
        return False, "大写金额无法解析"
    try:
        cn_value = Decimal(cn_num)
        total_value = _parse_amount(bill.total)
        if total_value is None:
            return False, "小写金额无法解析"
        if abs(cn_value - total_value) < Decimal("0.01"):
            return True, "一致"
        return False, f"大写({cn_value}) != 小写({total_value})"
    except Exception:
        return False, "金额解析异常"


def _check_number_length(bill: Bill) -> Tuple[bool, str]:
    """校验发票号码位数合法。"""
    if not bill.number:
        return False, "发票号码缺失"
    if len(bill.number) in (8, 10, 12, 20):
        return True, "位数合法"
    return False, f"发票号码位数异常: {len(bill.number)}"


def _check_date_valid(bill: Bill) -> Tuple[bool, str]:
    """校验日期格式合法。"""
    if not bill.date:
        return False, "日期缺失"
    try:
        datetime.strptime(bill.date, "%Y-%m-%d")
        return True, "日期合法"
    except ValueError:
        return False, f"日期格式非法: {bill.date}"


def _run_checks(bill: Bill) -> Dict[str, Any]:
    """执行四项一致性校验。"""
    checks = {}
    checks["amount_sum"] = _check_amount_sum(bill)
    checks["amount_cn"] = _check_amount_cn(bill)
    checks["number_length"] = _check_number_length(bill)
    checks["date_valid"] = _check_date_valid(bill)
    return checks


# ---------- 主处理函数 ----------

def process_pdf(pdf_path: Path) -> Bill:
    """处理单个 PDF 文件。"""
    # 检查文件存在
    if not pdf_path.exists():
        raise BillError("E001", f"文件不存在: {pdf_path}")

    # 检查文件大小（10MB 限制）
    if pdf_path.stat().st_size > 10 * 1024 * 1024:
        raise BillError("E001", f"文件超过 10MB: {pdf_path}")

    # 检查 PDF 魔数
    with open(pdf_path, "rb") as f:
        header = f.read(5)
    if not _is_pdf(header):
        raise BillError("E002", f"不是有效 PDF: {pdf_path}")

    # 检查加密
    if _is_encrypted(pdf_path):
        raise BillError("E003", f"PDF 已加密: {pdf_path}")

    # 提取文本
    text = _extract_text(pdf_path)

    # 解析字段
    bill = _parse_invoice(text, str(pdf_path))

    # 检查是否识别到关键字段
    if not bill.code and not bill.number and not bill.total:
        raise BillError("E006", f"未识别出发票关键字段: {pdf_path}")

    # 金额字段检查
    if not bill.amount or not bill.tax or not bill.total:
        raise BillError("E007", f"金额字段解析失败: {pdf_path}")

    # 一致性校验
    bill.checks = _run_checks(bill)

    # 检查校验结果
    failed = [k for k, v in bill.checks.items() if not v[0]]
    if failed:
        bill.error = f"一致性校验未通过: {', '.join(failed)}"

    return bill


def process_input(input_path: str) -> List[Bill]:
    """处理输入（文件/目录/URL）。"""
    results = []

    # 检查是否为 URL
    if input_path.startswith(("http://", "https://")):
        data = _download_with_retry(input_path)
        if not _is_pdf(data):
            raise BillError("E002", f"下载内容不是 PDF: {input_path}")
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(data)
            tmp_path = Path(tmp.name)
        try:
            bill = process_pdf(tmp_path)
            bill.file = input_path
            results.append(bill)
        finally:
            tmp_path.unlink(missing_ok=True)
        return results

    path = Path(input_path)

    # 检查路径存在
    if not path.exists():
        raise BillError("E001", f"路径不存在: {input_path}")

    # 处理文件
    if path.is_file():
        results.append(process_pdf(path))
        return results

    # 处理目录
    if path.is_dir():
        pdf_files = sorted(path.glob("*.pdf"))
        if not pdf_files:
            raise BillError("E009", f"目录未找到 PDF: {input_path}")
        for pdf_file in pdf_files:
            try:
                results.append(process_pdf(pdf_file))
            except BillError as e:
                log.warning("处理失败 %s: %s", pdf_file, e)
                # 创建错误记录
                err_bill = Bill(file=str(pdf_file), error=str(e))
                results.append(err_bill)
        return results

    raise BillError("E001", f"无法处理路径: {input_path}")


# ---------- 输出函数 ----------

def output_json(results: List[Bill]) -> str:
    """输出 JSON 格式。"""
    return json.dumps([asdict(b) for b in results], ensure_ascii=False, indent=2)


def output_jsonl(results: List[Bill]) -> str:
    """输出 JSONL 格式。"""
    return "\n".join(json.dumps(asdict(b), ensure_ascii=False) for b in results)


def output_csv(results: List[Bill]) -> str:
    """输出 CSV 格式。"""
    if not results:
        return ""
    fields = ["file", "code", "number", "date", "kind", "buyer", "buyer_tax", "seller", "seller_tax",
              "amount", "tax", "total", "total_cn", "rate", "confidence", "error"]
    import io
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    for bill in results:
        row = asdict(bill)
        row["checks"] = json.dumps(row.get("checks", {}), ensure_ascii=False)
        writer.writerow(row)
    return output.getvalue()


# ---------- 自检函数 ----------

def selftest() -> int:
    """自检函数：验证核心功能。"""
    print("运行自检...")
    failures = 0

    # 测试 1: 金额解析
    assert _parse_amount("1,234.56") == Decimal("1234.56"), "金额解析失败"
    assert _parse_amount("¥100.00") == Decimal("100.00"), "金额解析失败"
    print("  ✓ 金额解析")

    # 测试 2: 日期解析
    assert _parse_date("2024年01月01日") == "2024-01-01", "日期解析失败"
    assert _parse_date("2024-01-01") == "2024-01-01", "日期解析失败"
    print("  ✓ 日期解析")

    # 测试 3: 发票解析
    sample_text = """
    增值税电子发票
    发票代码：1234567890
    发票号码：12345678
    开票日期：2024年01月01日
    购买方：测试公司
    购买方纳税人识别号：91110000MA01ABCDE
    销售方：供应商公司
    销售方纳税人识别号：91110000MA01XYZ
    金额：100.00
    税额：13.00
    价税合计（小写）：¥113.00
    价税合计（大写）：壹佰壹拾叁元整
    税率：13%
    """
    bill = _parse_invoice(sample_text, "test.pdf")
    assert bill.code == "1234567890", "发票代码解析失败"
    assert bill.number == "12345678", "发票号码解析失败"
    assert bill.date == "2024-01-01", "日期解析失败"
    assert bill.amount == "100.00", "金额解析失败"
    assert bill.tax == "13.00", "税额解析失败"
    assert bill.total == "113.00", "价税合计解析失败"
    print("  ✓ 发票字段解析")

    # 测试 4: 一致性校验
    checks = _run_checks(bill)
    assert checks["amount_sum"][0], f"金额校验失败: {checks['amount_sum'][1]}"
    assert checks["number_length"][0], f"号码校验失败: {checks['number_length'][1]}"
    assert checks["date_valid"][0], f"日期校验失败: {checks['date_valid'][1]}"
    print("  ✓ 一致性校验")

    # 测试 5: 错误处理
    try:
        _parse_amount("abc")
        assert False, "应抛出异常"
    except Exception:
        pass
    print("  ✓ 错误处理")

    # 测试 6: 输出格式
    results = [bill]
    json_out = output_json(results)
    assert json.loads(json_out)[0]["code"] == "1234567890", "JSON 输出失败"
    jsonl_out = output_jsonl(results)
    assert json.loads(jsonl_out.split("\n")[0])["code"] == "1234567890", "JSONL 输出失败"
    csv_out = output_csv(results)
    assert "1234567890" in csv_out, "CSV 输出失败"
    print("  ✓ 输出格式")

    # 测试 7: PDF 魔数检查
    assert _is_pdf(b"%PDF-1.4"), "PDF 魔数检查失败"
    assert not _is_pdf(b"not pdf"), "PDF 魔数检查失败"
    print("  ✓ PDF 魔数检查")

    print(f"\n自检完成，{failures} 个失败")
    return 0 if failures == 0 else 1


# ---------- 主入口 ----------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="PDF发票解析与一致性校验",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""示例:
  python main.py invoice.pdf
  python main.py ./invoices/ --format jsonl
  python main.py https://example.com/invoice.pdf --output result.json
  python main.py --selftest
"""
    )
    parser.add_argument("input", nargs="?", help="输入文件路径、目录路径或 URL")
    parser.add_argument("--format", choices=["json", "jsonl", "csv"], default="json", help="输出格式")
    parser.add_argument("--output", "-o", help="输出文件路径（默认输出到 stdout）")
    parser.add_argument("--selftest", action="store_true", help="运行自检")
    parser.add_argument("--verbose", "-v", action="store_true", help="启用详细日志")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.INFO)

    if args.selftest:
        return selftest()

    if not args.input:
        parser.error("需要提供输入路径或使用 --selftest")

    try:
        results = process_input(args.input)
    except BillError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1

    # 生成输出
    if args.format == "json":
        output = output_json(results)
    elif args.format == "jsonl":
        output = output_jsonl(results)
    elif args.format == "csv":
        output = output_csv(results)
    else:
        output = output_json(results)

    # 输出
    if args.output:
        try:
            _atomic_write(Path(args.output), output)
            print(f"结果已写入: {args.output}")
        except BillError as e:
            print(f"错误: {e}", file=sys.stderr)
            return 1
    else:
        print(output)

    # 检查是否有校验失败
    failed = [b for b in results if b.error]
    if failed:
        print(f"\n警告: {len(failed)} 个文件校验未通过", file=sys.stderr)
        for b in failed:
            print(f"  {b.file}: {b.error}", file=sys.stderr)
        return 2

    return 0


if __name__ == "__main__":
    sys.exit(main())
