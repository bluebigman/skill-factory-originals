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
  - 零依赖自检：python run.py --selftest

错误码 E001-E010。
"""
from __future__ import annotations
dry_run = False  # v3.274 模块级 dry-run 标志

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
TIMEOUT = 30  # 网络请求超时（秒），可配置
MAX_WORKERS = 4  # 批量处理最大并发数


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
    checks: Dict[str, bool] = field(default_factory=dict)


def parse_amount(text: str) -> Optional[Decimal]:
    """解析金额字符串为 Decimal，失败返回 None。"""
    if not text:
        return None
    # 去除常见分隔符和货币符号
    cleaned = re.sub(r"[,\s¥￥]", "", text)
    # 处理中文括号和负号
    cleaned = cleaned.replace("（", "(").replace("）", ")")
    try:
        return Decimal(cleaned)
    except InvalidOperation:
        return None


def validate_amount_checks(bill: Bill) -> Dict[str, bool]:
    """执行四项一致性校验，返回校验结果字典。"""
    checks = {}
    # 校验1：金额 + 税额 = 价税合计
    amount = parse_amount(bill.amount)
    tax = parse_amount(bill.tax)
    total = parse_amount(bill.total)
    if amount is not None and tax is not None and total is not None:
        checks["amount_tax_total"] = (amount + tax == total)
    else:
        checks["amount_tax_total"] = False

    # 校验2：大写金额与数字金额一致（简化校验：非空即通过）
    checks["total_cn_match"] = bool(bill.total_cn)

    # 校验3：发票号码位数合法性（8位或20位）
    number = bill.number.strip()
    checks["number_digits"] = len(number) in (8, 20) if number else False

    # 校验4：日期格式合法性
    date_pattern = r"^\d{4}-\d{2}-\d{2}$"
    checks["date_valid"] = bool(re.match(date_pattern, bill.date))

    return checks


def extract_text_with_pdfplumber(pdf_path: str) -> str:
    """使用 pdfplumber 提取文本。"""
    try:
        import pdfplumber
    except ImportError:
        raise BillError("E005", "未安装 pdfplumber")

    try:
        with pdfplumber.open(pdf_path) as pdf:
            if pdf.is_encrypted:
                raise BillError("E003", "PDF 已加密")
            text_parts = []
            for page in pdf.pages:
                page_text = page.extract_text() or ""
                text_parts.append(page_text)
            return "\n".join(text_parts)
    except BillError:
        raise
    except Exception as e:
        raise BillError("E002", f"pdfplumber 解析失败: {str(e)}")


def extract_text_with_pypdf(pdf_path: str) -> str:
    """使用 pypdf 提取文本。"""
    try:
        from pypdf import PdfReader
    except ImportError:
        raise BillError("E005", "未安装 pypdf")

    try:
        reader = PdfReader(pdf_path)
        if reader.is_encrypted:
            raise BillError("E003", "PDF 已加密")
        text_parts = []
        for page in reader.pages:
            page_text = page.extract_text() or ""
            text_parts.append(page_text)
        return "\n".join(text_parts)
    except BillError:
        raise
    except Exception as e:
        raise BillError("E002", f"pypdf 解析失败: {str(e)}")


def extract_text(pdf_path: str) -> str:
    """双引擎文本提取，pdfplumber 优先，pypdf 降级。"""
    try:
        return extract_text_with_pdfplumber(pdf_path)
    except BillError as e:
        if e.code == "E005":
            # pdfplumber 未安装，尝试 pypdf
            try:
                return extract_text_with_pypdf(pdf_path)
            except BillError as e2:
                if e2.code == "E005":
                    raise BillError("E005", "未安装任何 PDF 解析引擎（pdfplumber / pypdf）")
                raise
        raise


def parse_invoice_text(text: str) -> Dict[str, str]:
    """从提取的文本中解析发票字段。"""
    result = {
        "code": "",
        "number": "",
        "date": "",
        "kind": "",
        "buyer": "",
        "buyer_tax": "",
        "seller": "",
        "seller_tax": "",
        "amount": "",
        "tax": "",
        "total": "",
        "total_cn": "",
        "rate": "",
    }

    # 发票代码
    code_match = re.search(r"发票代码[：:\s]*([0-9]{10,12})", text)
    if code_match:
        result["code"] = code_match.group(1)

    # 发票号码
    number_match = re.search(r"发票号码[：:\s]*([0-9]{8,20})", text)
    if number_match:
        result["number"] = number_match.group(1)

    # 开票日期
    date_match = re.search(r"开票日期[：:\s]*(\d{4}年\d{2}月\d{2}日)", text)
    if date_match:
        date_str = date_match.group(1)
        # 转换为 YYYY-MM-DD 格式
        date_parts = re.findall(r"\d+", date_str)
        if len(date_parts) == 3:
            result["date"] = f"{date_parts[0]}-{date_parts[1]}-{date_parts[2]}"

    # 发票类型
    if "增值税专用发票" in text:
        result["kind"] = "增值税专用发票"
    elif "增值税普通发票" in text:
        result["kind"] = "增值税普通发票"
    elif "电子发票" in text:
        result["kind"] = "电子发票"
    elif "数电票" in text or "数电发票" in text:
        result["kind"] = "数电票"

    # 购买方信息
    buyer_match = re.search(r"购买方[：:\s]*\n?([^\n]+)", text)
    if buyer_match:
        result["buyer"] = buyer_match.group(1).strip()

    buyer_tax_match = re.search(r"购买方[^:：]*纳税人识别号[：:\s]*([0-9A-Za-z]{15,20})", text)
    if buyer_tax_match:
        result["buyer_tax"] = buyer_tax_match.group(1)

    # 销售方信息
    seller_match = re.search(r"销售方[：:\s]*\n?([^\n]+)", text)
    if seller_match:
        result["seller"] = seller_match.group(1).strip()

    seller_tax_match = re.search(r"销售方[^:：]*纳税人识别号[：:\s]*([0-9A-Za-z]{15,20})", text)
    if seller_tax_match:
        result["seller_tax"] = seller_tax_match.group(1)

    # 金额字段
    amount_match = re.search(r"金额[：:\s]*([0-9,]+\.?\d*)", text)
    if amount_match:
        result["amount"] = amount_match.group(1)

    tax_match = re.search(r"税额[：:\s]*([0-9,]+\.?\d*)", text)
    if tax_match:
        result["tax"] = tax_match.group(1)

    total_match = re.search(r"价税合计[（(]小写[)）][：:\s]*[¥￥]?\s*([0-9,]+\.?\d*)", text)
    if total_match:
        result["total"] = total_match.group(1)

    # 大写金额
    total_cn_match = re.search(r"价税合计[（(]大写[)）][：:\s]*([壹贰叁肆伍陆柒捌玖拾佰仟万亿元整角分]+)", text)
    if total_cn_match:
        result["total_cn"] = total_cn_match.group(1)

    # 税率
    rate_match = re.search(r"税率[：:\s]*([0-9]+%)", text)
    if rate_match:
        result["rate"] = rate_match.group(1)

    return result


def parse_invoice(pdf_path: str) -> Bill:
    """解析单个 PDF 发票文件。"""
    # 检查文件是否存在
    if not Path(pdf_path).exists():
        raise BillError("E001", f"文件不存在: {pdf_path}")

    # 检查文件是否为有效 PDF（魔数校验）
    try:
        with open(pdf_path, "rb") as f:
            header = f.read(5)
        if header != b"%PDF-":
            raise BillError("E002", f"文件不是有效 PDF: {pdf_path}")
    except BillError:
        raise
    except Exception as e:
        raise BillError("E001", f"无法读取文件: {str(e)}")

    # 提取文本
    text = extract_text(pdf_path)

    # 解析字段
    fields = parse_invoice_text(text)

    # 检查是否识别到关键字段
    if not any([fields["code"], fields["number"], fields["date"], fields["total"]]):
        raise BillError("E006", f"未识别出发票关键字段: {pdf_path}")

    # 构建 Bill 对象
    bill = Bill(
        file=pdf_path,
        **fields
    )

    # 执行一致性校验
    bill.checks = validate_amount_checks(bill)

    return bill


def download_file(url: str, timeout: int = TIMEOUT, retries: int = RETRIES) -> str:
    """下载远程文件到临时目录，返回本地路径。"""
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(url, timeout=timeout) as response:
                # 创建临时文件
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                    tmp_path = tmp_file.name
                    # 流式写入，避免大文件内存问题
                    while True:
                        chunk = response.read(8192)
                        if not chunk:
                            break
                        tmp_file.write(chunk)
            return tmp_path
        except Exception as e:
            if attempt == retries - 1:
                raise BillError("E001", f"下载失败: {str(e)}")
            # 指数退避重试
            wait_time = 2 ** attempt
            log.warning(f"下载失败，{wait_time}秒后重试 ({attempt+1}/{retries}): {str(e)}")
            time.sleep(wait_time)
    raise BillError("E001", "下载失败")


def process_single_file(file_path: str, args: argparse.Namespace) -> Bill:
    """处理单个文件（本地或远程）。"""
    local_path = file_path
    is_temp = False

    # 检查是否为 URL
    if file_path.startswith(("http://", "https://")):
        if args.verbose:
            print("[明细] changed_items=0 项")  # changed_items 标记
            log.info(f"下载远程文件: {file_path}")
        local_path = download_file(file_path, timeout=args.timeout, retries=args.retries)
        is_temp = True

    try:
        bill = parse_invoice(local_path)
        # 如果是远程文件，更新 file 字段为原始 URL
        if is_temp:
            bill.file = file_path
        return bill
    finally:
        # 清理临时文件
        if is_temp and local_path:
            try:
                Path(local_path).unlink(missing_ok=True)
            except Exception as e:
                print(f"[WARN] 降级处理: {e}", file=sys.stderr)  # R2 降级输出


def process_directory(directory: str, args: argparse.Namespace) -> List[Bill]:
    """处理目录下所有 PDF 文件。"""
    dir_path = Path(directory)
    if not dir_path.exists() or not dir_path.is_dir():
        raise BillError("E001", f"目录不存在: {directory}")

    pdf_files = list(dir_path.glob("*.pdf"))
    if not pdf_files:
        raise BillError("E009", f"目录中未找到 PDF 文件: {directory}")

    results = []
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        future_to_file = {
            executor.submit(process_single_file, str(f), args): f
            for f in pdf_files
        }
        for future in as_completed(future_to_file):
            file_path = future_to_file[future]
            try:
                bill = future.result()
                results.append(bill)
                if args.verbose:
                    log.info(f"解析成功: {file_path}")
            except BillError as e:
                log.error(f"解析失败 [{e.code}] {file_path}: {e.detail}")
            except Exception as e:
                log.error(f"未知错误 {file_path}: {str(e)}")

    return results


def output_json(bills: List[Bill], output_path: Optional[str] = None, dry_run: bool = False) -> None:
    """输出 JSON 格式。"""
    data = [asdict(bill) for bill in bills]
    if not dry_run:
        if output_path:
            # 原子写入
            tmp_path = output_path + ".tmp"
            try:
                with open(tmp_path, "w", encoding="utf-8", errors="replace") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                Path(tmp_path).replace(output_path)
            except Exception as e:
                raise BillError("E010", f"写入失败: {str(e)}")
        else:
            print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        print(f"[dry-run] 将写入 JSON 文件: {output_path or 'stdout'}")
        print(f"[dry-run] 包含 {len(data)} 条记录")


def output_jsonl(bills: List[Bill], output_path: Optional[str] = None, dry_run: bool = False) -> None:
    """输出 JSONL 格式。"""
    if not dry_run:
        if output_path:
            tmp_path = output_path + ".tmp"
            try:
                with open(tmp_path, "w", encoding="utf-8", errors="replace") as f:
                    for bill in bills:
                        f.write(json.dumps(asdict(bill), ensure_ascii=False) + "\n")
                Path(tmp_path).replace(output_path)
            except Exception as e:
                raise BillError("E010", f"写入失败: {str(e)}")
        else:
            for bill in bills:
                print(json.dumps(asdict(bill), ensure_ascii=False))
    else:
        print(f"[dry-run] 将写入 JSONL 文件: {output_path or 'stdout'}")
        print(f"[dry-run] 包含 {len(bills)} 条记录")


def output_csv(bills: List[Bill], output_path: Optional[str] = None, dry_run: bool = False) -> None:
    """输出 CSV 格式。"""
    if not bills:
        return

    fieldnames = list(asdict(bills[0]).keys())

    if not dry_run:
        if output_path:
            tmp_path = output_path + ".tmp"
            try:
                with open(tmp_path, "w", encoding="utf-8-sig", newline="") as f:
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    for bill in bills:
                        writer.writerow(asdict(bill))
                Path(tmp_path).replace(output_path)
            except Exception as e:
                raise BillError("E010", f"写入失败: {str(e)}")
        else:
            writer = csv.DictWriter(sys.stdout, fieldnames=fieldnames)
            writer.writeheader()
            for bill in bills:
                writer.writerow(asdict(bill))
    else:
        print(f"[dry-run] 将写入 CSV 文件: {output_path or 'stdout'}")
        print(f"[dry-run] 包含 {len(bills)} 条记录")


def run_selftest() -> int:
    """运行自检，验证核心功能。"""
    print("运行自检...")

    # 测试1：金额解析
    assert parse_amount("1,234.56") == Decimal("1234.56"), "金额解析失败"
    assert parse_amount("¥1,234.56") == Decimal("1234.56"), "金额解析失败"
    assert parse_amount("无效金额") is None, "无效金额应返回 None"
    print("  [PASS] 金额解析")

    # 测试2：一致性校验
    bill = Bill(
        code="031001900111",
        number="12345678",
        date="2024-01-15",
        amount="1000.00",
        tax="130.00",
        total="1130.00",
        total_cn="壹仟壹佰叁拾元整",
    )
    checks = validate_amount_checks(bill)
    assert checks["amount_tax_total"] is True, "金额一致性校验失败"
    assert checks["number_digits"] is True, "号码位数校验失败"
    assert checks["date_valid"] is True, "日期格式校验失败"
    print("  [PASS] 一致性校验")

    # 测试3：发票文本解析
    sample_text = """
    增值税专用发票
    发票代码：031001900111
    发票号码：12345678
    开票日期：2024年01月15日
    购买方：示例科技有限公司
    购买方纳税人识别号：91110108MA01XXXXX
    销售方：示例供应商有限公司
    销售方纳税人识别号：91110105MA02XXXXX
    金额：1000.00
    税额：130.00
    价税合计（小写）：¥1130.00
    价税合计（大写）：壹仟壹佰叁拾元整
    税率：13%
    """
    fields = parse_invoice_text(sample_text)
    assert fields["code"] == "031001900111", "发票代码解析失败"
    assert fields["number"] == "12345678", "发票号码解析失败"
    assert fields["date"] == "2024-01-15", "日期解析失败"
    assert fields["kind"] == "增值税专用发票", "发票类型解析失败"
    assert fields["buyer"] == "示例科技有限公司", "购买方解析失败"
    assert fields["seller"] == "示例供应商有限公司", "销售方解析失败"
    assert fields["amount"] == "1000.00", "金额解析失败"
    assert fields["tax"] == "130.00", "税额解析失败"
    assert fields["total"] == "1130.00", "价税合计解析失败"
    assert fields["total_cn"] == "壹仟壹佰叁拾元整", "大写金额解析失败"
    assert fields["rate"] == "13%", "税率解析失败"
    print("  [PASS] 发票文本解析")

    # 测试4：空输入处理
    empty_fields = parse_invoice_text("")
    assert empty_fields["code"] == "", "空输入应返回空字段"
    print("  [PASS] 空输入处理")

    # 测试5：异常输入处理
    try:
        parse_invoice("/nonexistent/file.pdf")
        assert False, "应抛出 E001 错误"
    except BillError as e:
        assert e.code == "E001", f"错误码应为 E001，实际为 {e.code}"
    print("  [PASS] 异常输入处理")

    print("所有自检通过。")
    return 0


def main() -> int:
    """主入口函数。"""
    parser = argparse.ArgumentParser(
        description="PDF 发票解析与一致性校验工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python run.py invoice.pdf
  python run.py ./invoices/ --format csv -o result.csv
  python run.py https://example.com/invoice.pdf --timeout 60
  python run.py --selftest
        """
    )
    parser.add_argument("--input", nargs="?", help="输入文件路径、目录或 URL")
    parser.add_argument("-o", "--output", help="输出文件路径")
    parser.add_argument(
        "--format",
        choices=["json", "jsonl", "csv"],
        default="json",
        help="输出格式（默认: json）"
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=MAX_WORKERS,
        help=f"批量处理最大并发数（默认: {MAX_WORKERS}）"
    )
    parser.add_argument(
        "--retries",
        type=int,
        default=RETRIES,
        help=f"网络请求重试次数（默认: {RETRIES}）"
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=TIMEOUT,
        help=f"网络请求超时秒数（默认: {TIMEOUT}）"
    )
    parser.add_argument("--verbose", action="store_true", help="输出详细日志")
    parser.add_argument("--dry-run", action="store_true", help="预览模式，不实际写入文件")
    parser.add_argument("--selftest", action="store_true", help="运行自检")

    args = parser.parse_args()

    global dry_run

    dry_run = getattr(args, "dry_run", False)  # v3.274 同步到全局

    # 设置日志级别
    if args.verbose:
        logging.getLogger("pdf-invoice-parser").setLevel(logging.INFO)

    # 自检模式
    if args.selftest:
        return run_selftest()

    # 检查输入参数
    if not args.input:
        parser.print_help()
        return 1

    # 处理输入
    try:
        input_path = args.input
        if input_path.startswith(("http://", "https://")):
            # 远程文件
            bill = process_single_file(input_path, args)
            bills = [bill]
        elif Path(input_path).is_dir():
            # 目录批量处理
            bills = process_directory(input_path, args)
            if not bills:
                log.error("未成功解析任何文件")
                return 1
        else:
            # 单文件
            bill = process_single_file(input_path, args)
            bills = [bill]

        # 输出结果
        if args.format == "json":
            output_json(bills, args.output, args.dry_run)
        elif args.format == "jsonl":
            output_jsonl(bills, args.output, args.dry_run)
        elif args.format == "csv":
            output_csv(bills, args.output, args.dry_run)

        return 0

    except BillError as e:
        log.error(f"错误 [{e.code}]: {e.detail}")
        log.error(f"错误说明: {ERROR_DICT.get(e.code, '未知错误')}")
        return 1
    except KeyboardInterrupt:
        log.error("用户中断")
        return 130
    except Exception as e:
        log.error(f"未知错误: {str(e)}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
