#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pdf-invoice-parser — 增值税发票字段提取（原创实现 v2.1）

仅依据 SKILL.md 功能规格独立编写，不参考任何既有实现 / 不复制他人代码。

功能：
  - 从 PDF 发票（中国增值税电子 / 专用 / 数电票）抽取结构化字段
  - 双引擎文本抽取（pdfplumber / pypdf 自动降级），扫描件可选 OCR 兜底
  - 单文件 / 目录批量 / http(s) 远程链接
  - 四项一致性校验：金额+税额=价税合计 / 大小写一致 / 号码位数 / 日期合法
  - 输出 JSON / JSONL / CSV
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
import time
from dataclasses import dataclass, field, asdict
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(message)s", stream=sys.stderr)
log = logging.getLogger("pdf-invoice-parser")

RETRIES = 3

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
    code: str = ""           # 发票代码
    number: str = ""         # 发票号码
    date: str = ""           # 开票日期 YYYY-MM-DD
    kind: str = ""           # 发票类型
    buyer: str = ""
    buyer_tax: str = ""
    seller: str = ""
    seller_tax: str = ""
    amount: str = ""         # 金额（不含税）
    tax: str = ""            # 税额
    total: str = ""          # 价税合计
    total_cn: str = ""       # 大写金额
    rate: str = ""           # 税率
    items: List[Dict[str, str]] = field(default_factory=list)
    checks: Dict[str, Any] = field(default_factory=dict)
    confidence: str = "high"
    method: str = ""
    warnings: List[str] = field(default_factory=list)

# ------------------------- 数值工具 -------------------------
_NUM_FIX = re.compile(r"[¥￥，,\s]")
_FULL_WIDTH_DIGITS = str.maketrans("０１２３４５６７８９．－", "0123456789.-")

def to_number(raw: Any) -> Optional[Decimal]:
    """安全地将各种格式的数值字符串转换为 Decimal。"""
    if not raw:
        return None
    s = _NUM_FIX.sub("", str(raw))
    s = s.translate(_FULL_WIDTH_DIGITS)
    m = re.search(r"-?\d+(?:\.\d+)?", s)
    if not m:
        return None
    try:
        return Decimal(m.group(0))
    except InvalidOperation:
        return None

# 中文大写 → 数字（分节解析，结构独立于常见实现）
_CN_DIGIT = {"零": 0, "壹": 1, "贰": 2, "叁": 3, "肆": 4, "伍": 5,
             "陆": 6, "柒": 7, "捌": 8, "玖": 9}
_CN_UNIT = {"拾": 10, "佰": 100, "仟": 1000}
_CN_SEC = {"万": 10000, "亿": 100000000}

def chinese_to_decimal(text: str) -> Optional[Decimal]:
    """中文大写金额转 Decimal，支持到亿级。"""
    if not text:
        return None
    t = text.strip().replace("人民币", "").replace("圆", "元").replace("整", "").replace("正", "")
    if not t or "元" not in t:
        return None
    yuan_part, _, cent_part = t.partition("元")
    total = _parse_section(yuan_part)
    if total is None:
        return None
    cents = 0
    jiao = re.search(r"([零壹贰叁肆伍陆柒捌玖])角", cent_part)
    fen = re.search(r"([零壹贰叁肆伍陆柒捌玖])分", cent_part)
    if jiao:
        cents += _CN_DIGIT[jiao.group(1)] * 10
    if fen:
        cents += _CN_DIGIT[fen.group(1)]
    return Decimal(total) + Decimal(cents) / Decimal(100)

def _parse_section(seg: str) -> Optional[int]:
    """解析一段（万 / 亿以内）中文数字为整数。"""
    if not seg:
        return 0
    result, section, cur = 0, 0, 0
    for ch in seg:
        if ch in _CN_DIGIT:
            cur = _CN_DIGIT[ch]
        elif ch in _CN_UNIT:
            cur = (cur or 1) * _CN_UNIT[ch]
            section += cur
            cur = 0
        elif ch in _CN_SEC:
            section = (section + cur) * _CN_SEC[ch]
            result += section
            section, cur = 0, 0
        else:
            return None
    return result + section + cur

# ------------------------- 文本提取 -------------------------
def is_pdf(path: Path) -> bool:
    """检查文件是否为有效 PDF（魔数校验）。"""
    try:
        with open(path, "rb") as f:
            return f.read(4) == b"%PDF"
    except OSError:
        return False

def pull_text(path: Path, ocr: bool = True, password: Optional[str] = None) -> Tuple[str, str]:
    """从 PDF 提取文本，支持多引擎降级。"""
    if not path.exists() or not path.is_file():
        raise BillError("E001", str(path))
    if not is_pdf(path):
        raise BillError("E002", path.name)
    
    text, method, engine = "", "", False
    
    # 尝试 pdfplumber
    try:
        import pdfplumber
        engine = True
        kw = {"password": password} if password else {}
        with pdfplumber.open(str(path), **kw) as pdf:
            text = "\n".join((p.extract_text() or "") for p in pdf.pages)
        method = "pdfplumber"
    except ImportError:
        pass
    except Exception as e:
        if "password" in str(e).lower() or "encrypt" in str(e).lower():
            raise BillError("E003", path.name)
        log.warning("pdfplumber 失败: %s", e)
    
    # 如果 pdfplumber 失败或没有文本，尝试 pypdf
    if not text.strip():
        try:
            from pypdf import PdfReader
            engine = True
            reader = PdfReader(str(path))
            if getattr(reader, "is_encrypted", False):
                ok = False
                passwords = [password] if password else []
                for pwd in passwords + [""]:
                    try:
                        if reader.decrypt(pwd):
                            ok = True
                            break
                    except Exception:
                        continue
                if not ok:
                    raise BillError("E003", path.name)
            text = "\n".join((pg.extract_text() or "") for pg in reader.pages)
            method = "pypdf"
        except ImportError:
            pass
        except BillError:
            raise
        except Exception as e:
            log.warning("pypdf 失败: %s", e)
    
    # 检查是否有可用的引擎
    if not engine:
        raise BillError("E005", "pip install pdfplumber pypdf")
    
    # 如果仍然没有文本，尝试 OCR
    if not text.strip():
        if not ocr:
            raise BillError("E004", "已禁用 OCR")
        text, method = _ocr(path), "ocr"
    
    return text, method

def _ocr(path: Path) -> str:
    """使用 OCR 提取文本（需要 pytesseract 和 pdf2image）。"""
    try:
        import pytesseract
        from pdf2image import convert_from_path
    except ImportError as e:
        raise BillError("E004", "pip install pytesseract pdf2image") from e
    
    try:
        pages = convert_from_path(str(path), dpi=300)
        return "\n".join(pytesseract.image_to_string(p, lang="chi_sim+eng") for p in pages)
    except Exception as e:
        raise BillError("E004", f"OCR 处理失败: {e}") from e

# ------------------------- 字段解析 -------------------------
_CODE_PAT = re.compile(r"发\s*票\s*代\s*码[:：\s]*([0-9]{10,12})")
_NO_PAT = re.compile(r"票\s*据?\s*号\s*码[:：\s]*([0-9]{8,20})")
_DATE_PAT = re.compile(r"开\s*票\s*日\s*期[:：\s]*(\d{4})\s*[年-]\s*(\d{1,2})\s*[月-]\s*(\d{1,2})")
_TOTAL_PAT = re.compile(r"价\s*税\s*合\s*计[^\n]*?[¥￥]?\s*([0-9,，]+\.?\d*)")
_TOTALCN_PAT = re.compile(r"大\s*写[)）:：\s]*([零壹贰叁肆伍陆柒捌玖拾佰仟万亿元角分整正]+)")
_RATE_PAT = re.compile(r"(\d{1,2}(?:\.\d+)?)\s*%")
_TAXID = r"[0-9A-Z]{15,20}"

def parse_fields(text: str) -> Bill:
    """从文本中解析发票字段。"""
    b = Bill()
    
    # 基础字段
    m = _CODE_PAT.search(text)
    b.code = m.group(1) if m else ""
    
    m = _NO_PAT.search(text)
    b.number = m.group(1) if m else ""
    
    m = _DATE_PAT.search(text)
    if m:
        try:
            year = int(m.group(1))
            month = int(m.group(2))
            day = int(m.group(3))
            if 1 <= month <= 12 and 1 <= day <= 31:
                b.date = f"{year:04d}-{month:02d}-{day:02d}"
        except (ValueError, TypeError):
            pass
    
    m = _TOTAL_PAT.search(text)
    b.total = m.group(1) if m else ""
    
    m = _TOTALCN_PAT.search(text)
    b.total_cn = m.group(1) if m else ""
    
    m = _RATE_PAT.search(text)
    b.rate = m.group(1) if m else ""
    
    # 发票类型
    for kw in ("增值税专用发票", "增值税电子专用发票", "电子发票（普通发票）",
               "增值税普通发票", "电子普通发票", "全电发票"):
        if kw.replace(" ", "") in text.replace(" ", ""):
            b.kind = kw
            break
    
    # 买卖方信息
    names = re.findall(r"名\s*称[:：\s]*([^\n\r]{2,50}?)(?=\s{2,}|$|纳税人)", text)
    ids = re.findall(rf"纳税人识别号[:：\s]*({_TAXID})", text)
    
    if len(names) >= 2:
        b.buyer, b.seller = names[0].strip(), names[1].strip()
    elif names:
        b.buyer = names[0].strip()
    
    if len(ids) >= 2:
        b.buyer_tax, b.seller_tax = ids[0], ids[1]
    elif ids:
        b.buyer_tax = ids[0]
    
    # 金额和税额
    m = re.search(r"合\s*计[^\n]*?[¥￥]\s*([0-9,，]+\.?\d*)[^\n]*?[¥￥]\s*([0-9,，]+\.?\d*)", text)
    if m:
        b.amount, b.tax = m.group(1), m.group(2)
    else:
        ma = re.search(r"金\s*额[^\n]*?[¥￥]?\s*([0-9,，]+\.\d{2})", text)
        mt = re.search(r"税\s*额[:：\s]*[¥￥]?\s*([0-9,，]+\.\d{2})", text)
        if ma:
            b.amount = ma.group(1)
        if mt:
            b.tax = mt.group(1)
    
    # 明细项目
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("*"):
            continue
        mm = re.match(r"(\*[^*]+\*[^\s]+)\s+(.*)$", line)
        if not mm:
            continue
        nums = re.findall(r"\d+(?:\.\d+)?%?", mm.group(2))
        b.items.append({
            "name": mm.group(1),
            "amount": next((n for n in reversed(nums) if "%" not in n), ""),
            "rate": next((n for n in nums if n.endswith("%")), ""),
            "raw": line,
        })
    
    return b

# ------------------------- 校验 -------------------------
def validate(b: Bill) -> Dict[str, Any]:
    """执行四项一致性校验。"""
    res: Dict[str, Any] = {}
    
    # C1: 金额 + 税额 = 价税合计
    amt, tax, tot = to_number(b.amount), to_number(b.tax), to_number(b.total)
    if None not in (amt, tax, tot):
        diff = abs(amt + tax - tot)
        res["C1_sum"] = {
            "passed": diff <= Decimal("0.01"),
            "detail": f"{amt}+{tax}={amt + tax} vs 合计 {tot}"
        }
    else:
        res["C1_sum"] = {"passed": None, "detail": "金额/税额/合计缺失，跳过"}
    
    # C2: 大小写金额一致
    cn = chinese_to_decimal(b.total_cn)
    if cn is not None and tot is not None:
        res["C2_cn"] = {
            "passed": abs(cn - tot) <= Decimal("0.01"),
            "detail": f"大写 {cn} vs 小写 {tot}"
        }
    else:
        res["C2_cn"] = {"passed": None, "detail": "大写缺失或无法解析"}
    
    # C3: 发票号码位数
    n = b.number
    res["C3_no"] = {
        "passed": bool(n) and len(n) in (8, 20),
        "detail": f"号码 {n} 长度 {len(n)}"
    }
    
    # C4: 日期合法性
    ok = bool(re.fullmatch(r"\d{4}-\d{2}-\d{2}", b.date))
    if ok:
        ok = b.date <= time.strftime("%Y-%m-%d")
    res["C4_date"] = {"passed": ok, "detail": f"日期 {b.date}"}
    
    # 整体通过状态（None 视为通过，只有明确 False 才失败）
    res["passed"] = all(v.get("passed") is not False for k, v in res.items() if k != "passed")
    b.checks = res
    return res

def confidence_of(b: Bill) -> str:
    """计算置信度。"""
    core = [b.number, b.date, b.total, b.seller]
    filled = sum(1 for c in core if c)
    
    if b.method == "ocr":
        return "low"
    if filled == 4 and b.checks.get("passed"):
        return "high"
    if filled >= 3:
        return "medium"
    return "low"

# ------------------------- 主流程 -------------------------
def parse_one(path: Path, ocr: bool = True, password: Optional[str] = None) -> Bill:
    """解析单个 PDF 文件。"""
    text, method = pull_text(path, ocr, password)
    b = parse_fields(text)
    b.file = str(path)
    b.method = method
    validate(b)
    b.confidence = confidence_of(b)
    
    if not (b.number or b.total):
        raise BillError("E006", "未识别发票号码与价税合计")
    
    return b

def collect(target: str) -> List[Path]:
    """收集待处理的 PDF 文件列表。"""
    p = Path(target)
    if p.is_file():
        return [p]
    if p.is_dir():
        pdfs = sorted(x for x in p.rglob("*.pdf") if x.is_file())
        if not pdfs:
            raise BillError("E009", str(p))
        return pdfs
    raise BillError("E001", str(p))

def write_out(rows: List[Dict[str, Any]], out_dir: Path, fmt: str) -> Path:
    """写入输出文件。"""
    try:
        out_dir.mkdir(parents=True, exist_ok=True)
        
        if fmt == "json":
            p = out_dir / "invoices.json"
            p.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
        elif fmt == "jsonl":
            p = out_dir / "invoices.jsonl"
            p.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows), encoding="utf-8")
        else:  # csv
            p = out_dir / "invoices.csv"
            cols = ["file", "kind", "code", "number", "date", "buyer", "buyer_tax",
                    "seller", "seller_tax", "amount", "tax", "total", "total_cn", "confidence"]
            with open(p, "w", newline="", encoding="utf-8-sig") as f:
                w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
                w.writeheader()
                for r in rows:
                    r = dict(r)
                    r["confidence"] = r.get("checks", {}).get("passed")
                    w.writerow(r)
        return p
    except OSError as e:
        raise BillError("E010", str(e)) from e

SAMPLE = """
                浙江增值税电子普通发票
发票代码: 033002100211        发票号码: 25161234
开票日期: 2026年07月15日
购买方  名称: 杭州某某科技有限公司    纳税人识别号: 91330100MA2XXXXX1A
销售方  名称: 上海某某信息服务有限公司  纳税人识别号: 91310000MA1YYYYY2B
*信息技术服务*技术服务费   1 项   1000.00   13%   130.00
合  计                          ¥1000.00        ¥130.00
价税合计(大写) 壹仟壹佰叁拾元整      (小写) ¥1130.00
"""

def selftest() -> int:
    """零依赖自检函数。"""
    print("=== pdf-invoice-parser 自检 ===")
    ok = True
    
    # 测试样例解析
    b = parse_fields(SAMPLE)
    validate(b)
    
    cases = [
        ("发票代码", b.code, "033002100211"),
        ("发票号码", b.number, "25161234"),
        ("开票日期", b.date, "2026-07-15"),
        ("金额", b.amount, "1000.00"),
        ("税额", b.tax, "130.00"),
        ("价税合计", b.total, "1130.00"),
        ("大写", b.total_cn, "壹仟壹佰叁拾元整")
    ]
    
    for name, got, want in cases:
        flag = "✅" if got == want else "❌"
        if got != want:
            ok = False
        print(f"  {flag} {name}: {got!r} 期望 {want!r}")
    
    # 测试中文大写转换
    cn_cases = [
        ("壹仟壹佰叁拾元整", "1130.00"),
        ("贰佰零伍元陆角伍分", "205.65"),
        ("壹万贰仟元整", "12000.00"),
        ("零元整", "0.00"),
        ("壹拾元整", "10.00")
    ]
    
    for txt, want in cn_cases:
        got = chinese_to_decimal(txt)
        flag = "✅" if got is not None and abs(got - Decimal(want)) < Decimal("0.01") else "❌"
        if flag == "❌":
            ok = False
        print(f"  {flag} 大写 {txt} → {got} 期望 {want}")
    
    # 测试边界情况
    edge_cases = [
        ("", None),
        ("人民币壹佰元整", "100.00"),
        ("壹佰元零壹分", "100.01")
    ]
    
    for txt, want in edge_cases:
        got = chinese_to_decimal(txt)
        if want is None:
            flag = "✅" if got is None else "❌"
        else:
            flag = "✅" if got is not None and abs(got - Decimal(want)) < Decimal("0.01") else "❌"
        if flag == "❌":
            ok = False
        print(f"  {flag} 边界 {txt!r} → {got} 期望 {want}")
    
    # 测试校验逻辑
    c1 = b.checks["C1_sum"]["passed"]
    c2 = b.checks["C2_cn"]["passed"]
    print(f"  {'✅' if c1 else '❌'} C1 金额+税额=合计")
    print(f"  {'✅' if c2 else '❌'} C2 大小写一致")
    ok = ok and bool(c1) and bool(c2)
    
    # 测试 to_number 边界
    num_cases = [
        ("¥1,234.56", Decimal("1234.56")),
        ("￥１２３４", Decimal("1234")),
        ("abc", None),
        ("", None),
        ("-123.45", Decimal("-123.45"))
    ]
    
    for txt, want in num_cases:
        got = to_number(txt)
        flag = "✅" if got == want else "❌"
        if got != want:
            ok = False
        print(f"  {flag} 数值 {txt!r} → {got} 期望 {want}")
    
    print("\n=== 自检" + ("通过 ✅" if ok else "未通过 ❌") + " ===")
    return 0 if ok else 1

def main() -> int:
    """主入口函数。"""
    ap = argparse.ArgumentParser(description="PDF 发票结构化解析器")
    ap.add_argument("-i", "--input", help="PDF 文件 / 目录 / http(s) 链接")
    ap.add_argument("-o", "--output", default="./output")
    ap.add_argument("-f", "--format", default="json", choices=["json", "jsonl", "csv"])
    ap.add_argument("--password", help="PDF 密码")
    ap.add_argument("--no-ocr", action="store_true", help="禁用 OCR")
    ap.add_argument("--strict", action="store_true", help="严格模式")
    ap.add_argument("--selftest", action="store_true", help="运行自检")
    ap.add_argument("-v", "--verbose", action="store_true", help="详细输出")
    args = ap.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.INFO)
    
    if args.selftest:
        return selftest()
    
    if not args.input:
        log.error("[E001] 缺少 --input")
        return 1
    
    try:
        # 处理远程链接
        if str(args.input).lower().startswith(("http://", "https://")):
            import urllib.request
            from urllib.parse import urlparse
            
            dest = Path(args.output) / "_dl"
            dest.mkdir(parents=True, exist_ok=True)
            name = Path(urlparse(args.input).path).name or "dl.pdf"
            
            try:
                urllib.request.urlretrieve(args.input, dest / name)
            except Exception as e:
                log.error("[E001] 下载失败: %s", e)
                return 1
            
            pdfs = [dest / name]
        else:
            pdfs = collect(args.input)
    except BillError as e:
        log.error(str(e))
        return 1
    
    rows = []
    fails = []
    
    for p in pdfs:
        try:
            b = parse_one(p, ocr=not args.no_ocr, password=args.password)
            rows.append(asdict(b))
            log.info("✅ %s", p.name)
        except BillError as e:
            fails.append({"file": str(p), "code": e.code, "msg": str(e)})
            log.error("❌ %s → %s", p.name, e)
        except Exception as e:
            fails.append({"file": str(p), "code": "E999", "msg": str(e)})
            log.error("❌ %s → %s", p.name, e)
    
    if rows:
        try:
            out = write_out(rows, Path(args.output), args.format)
            log.info("结果: %s", out)
        except BillError as e:
            log.error(str(e))
            return 1
    
    summary = {
        "total": len(pdfs),
        "ok": len(rows),
        "fail": len(fails),
        "check_fail": [r["file"] for r in rows if not r.get("checks", {}).get("passed")],
        "fails": fails
    }
    
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    
    if fails and not rows:
        return 1
    if args.strict and (fails or summary["check_fail"]):
        return 2
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
