#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
报销单据整理工具 - 独立实现脚本

功能：
- 解析手工录入的报销清单文本
- 对发票字段做格式合规性初筛（发票代码、号码、校验码）
- 按费用性质自动归类（交通/餐饮/办公/差旅等）
- 汇总金额并生成 Markdown / CSV 明细表

用法示例：
    python main.py --input data.txt --output report.md
    python main.py --selftest
"""

import argparse
import csv
import io
import re
import sys
from collections import defaultdict
from datetime import datetime

# ---------------------------------------------------------------------------
# 常量定义
# ---------------------------------------------------------------------------

# 错误码
ERR_OK = 0
ERR_INPUT_FILE = "E001"       # 输入文件不存在或无法读取
ERR_INPUT_FORMAT = "E002"     # 输入内容无法解析
ERR_OUTPUT_FILE = "E003"      # 输出文件无法写入
ERR_INVALID_AMOUNT = "E004"   # 金额格式非法
ERR_INVALID_DATE = "E005"     # 日期格式非法
ERR_INVALID_INVOICE = "E006"  # 发票字段格式不合规
ERR_EMPTY_DATA = "E007"       # 没有任何有效单据
ERR_UNKNOWN_CATEGORY = "E008" # 类别不在预定义集合内
ERR_CLI_USAGE = "E009"        # 命令行参数使用错误
ERR_INTERNAL = "E010"         # 内部逻辑错误

# 预设费用类别（含同义词映射）
CATEGORY_KEYWORDS = {
    "交通": ["交通", "打车", "出租车", "地铁", "公交", "高铁", "火车", "机票", "燃油", "停车", "过路"],
    "餐饮": ["餐饮", "餐费", "午餐", "晚餐", "早餐", "招待餐", "外卖", "团建餐"],
    "办公": ["办公", "文具", "打印", "耗材", "快递", "邮寄", "软件", "订阅"],
    "差旅": ["差旅", "住宿", "酒店", "民宿", "出差", "住宿费"],
    "通讯": ["通讯", "话费", "流量", "宽带"],
    "其他": [],  # 兜底类别
}

# 发票代码 / 号码 / 校验码 的常见格式（简化版）
INVOICE_CODE_PATTERN = re.compile(r"^\d{10,12}$")          # 发票代码：10-12 位数字
INVOICE_NUMBER_PATTERN = re.compile(r"^\d{8}$")            # 发票号码：8 位数字
INVOICE_CHECK_PATTERN = re.compile(r"^\d{6,20}$")          # 校验码：6-20 位数字

# 日期格式：YYYY-MM-DD 或 YYYY/MM/DD
DATE_PATTERN = re.compile(r"^(\d{4})[-/](\d{1,2})[-/](\d{1,2})$")

# 金额格式：数字（可含小数，最多两位）
AMOUNT_PATTERN = re.compile(r"^\d+(\.\d{1,2})?$")


# ---------------------------------------------------------------------------
# 领域模型
# ---------------------------------------------------------------------------

class ExpenseItem:
    """单张报销单据条目"""

    def __init__(self, date_str, doc_type, amount, category, note="", confidence=1.0):
        self.date_str = date_str
        self.doc_type = doc_type      # 如：发票、收据、行程单
        self.amount = amount          # float
        self.category = category      # 交通/餐饮/办公/差旅/通讯/其他
        self.note = note
        self.confidence = confidence  # 0.0 ~ 1.0

    def to_dict(self):
        return {
            "日期": self.date_str,
            "单据类型": self.doc_type,
            "金额": f"{self.amount:.2f}",
            "类别": self.category,
            "备注": self.note,
            "置信度": f"{self.confidence:.2f}",
        }


# ---------------------------------------------------------------------------
# 校验函数
# ---------------------------------------------------------------------------

def validate_date(date_str):
    """校验日期格式，返回 (是否合法, 错误信息)"""
    m = DATE_PATTERN.match(date_str.strip())
    if not m:
        return False, "日期格式应为 YYYY-MM-DD 或 YYYY/MM/DD"
    year, month, day = int(m.group(1)), int(m.group(2)), int(m.group(3))
    try:
        datetime(year, month, day)
    except ValueError:
        return False, f"日期不存在: {date_str}"
    return True, ""


def validate_amount(amount_str):
    """校验金额格式，返回 (是否合法, 错误信息)"""
    s = amount_str.strip()
    if not AMOUNT_PATTERN.match(s):
        return False, f"金额格式非法: {amount_str}（应为非负数字，最多两位小数）"
    return True, ""


def validate_invoice_fields(code="", number="", check_code=""):
    """
    发票字段格式合规性初筛。
    仅检查格式，不做官方验真。
    返回 (是否通过, 问题列表)
    """
    problems = []
    if code and not INVOICE_CODE_PATTERN.match(code.strip()):
        problems.append(f"发票代码格式异常: {code}（应为10-12位数字）")
    if number and not INVOICE_NUMBER_PATTERN.match(number.strip()):
        problems.append(f"发票号码格式异常: {number}（应为8位数字）")
    if check_code and not INVOICE_CHECK_PATTERN.match(check_code.strip()):
        problems.append(f"校验码格式异常: {check_code}（应为6-20位数字）")
    return (len(problems) == 0), problems


# ---------------------------------------------------------------------------
# 文本解析
# ---------------------------------------------------------------------------

def parse_line(line):
    """
    解析单行文本为 ExpenseItem。
    支持两种格式：
    1. 字段分隔：日期 | 类型 | 金额 | 类别 | 备注
    2. 自然语言：2026-01-15 打车 35.5 交通 去机场
    返回 (ExpenseItem 或 None, 错误信息列表)
    """
    line = line.strip()
    if not line:
        return None, []

    # 尝试分隔符解析（支持 | 或 , 或 tab）
    parts = None
    for sep in ["|", ",", "\t"]:
        if sep in line:
            parts = [p.strip() for p in line.split(sep)]
            break

    errors = []

    if parts and len(parts) >= 4:
        # 结构化格式：日期 | 类型 | 金额 | 类别 | 备注
        date_str, doc_type, amount_str, category = parts[0], parts[1], parts[2], parts[3]
        note = parts[4] if len(parts) > 4 else ""

        # 校验日期
        ok, msg = validate_date(date_str)
        if not ok:
            errors.append(f"[{ERR_INVALID_DATE}] {msg}")

        # 校验金额
        ok, msg = validate_amount(amount_str)
        if not ok:
            errors.append(f"[{ERR_INVALID_AMOUNT}] {msg}")
            amount = 0.0
        else:
            amount = float(amount_str)

        # 类别检查（若给出）
        if category not in CATEGORY_KEYWORDS:
            errors.append(f"[{ERR_UNKNOWN_CATEGORY}] 未知类别: {category}")

        if errors:
            return None, errors

        return ExpenseItem(
            date_str=date_str,
            doc_type=doc_type,
            amount=amount,
            category=category,
            note=note,
        ), []

    # 自然语言解析：尝试从文本中提取日期、金额、类别关键词
    # 提取日期
    date_match = re.search(r"(\d{4}[-/]\d{1,2}[-/]\d{1,2})", line)
    if not date_match:
        errors.append(f"[{ERR_INPUT_FORMAT}] 未找到日期")
        return None, errors
    date_str = date_match.group(1)
    ok, msg = validate_date(date_str)
    if not ok:
        errors.append(f"[{ERR_INVALID_DATE}] {msg}")

    # 提取金额（第一个匹配的数字）
    amount_match = re.search(r"(\d+(?:\.\d{1,2})?)", line)
    if not amount_match:
        errors.append(f"[{ERR_INVALID_AMOUNT}] 未找到金额")
        return None, errors
    amount_str = amount_match.group(1)
    ok, msg = validate_amount(amount_str)
    if not ok:
        errors.append(f"[{ERR_INVALID_AMOUNT}] {msg}")
        amount = 0.0
    else:
        amount = float(amount_str)

    # 识别单据类型
    doc_type = "发票"
    if "收据" in line:
        doc_type = "收据"
    elif "行程单" in line:
        doc_type = "行程单"
    elif "发票" in line:
        doc_type = "发票"

    # 识别类别 - 改进：优先匹配更具体的类别
    category = "其他"
    max_keyword_len = 0
    for cat, keywords in CATEGORY_KEYWORDS.items():
        if cat == "其他":
            continue
        for kw in keywords:
            if kw in line and len(kw) > max_keyword_len:
                max_keyword_len = len(kw)
                category = cat

    # 备注（去掉已识别的日期和金额）
    note = line
    note = re.sub(r"\d{4}[-/]\d{1,2}[-/]\d{1,2}", "", note)
    note = re.sub(r"\d+(?:\.\d{1,2})?", "", note)
    note = note.strip(" |,，\t")

    if errors:
        return None, errors

    return ExpenseItem(
        date_str=date_str,
        doc_type=doc_type,
        amount=amount,
        category=category,
        note=note,
    ), []


def parse_input(text):
    """
    解析多行输入文本。
    返回 (items列表, 错误列表)
    """
    items = []
    errors = []
    for idx, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        item, errs = parse_line(line)
        if item:
            items.append(item)
        else:
            for e in errs:
                errors.append(f"第{idx}行: {e}")

    if not items:
        errors.append(f"[{ERR_EMPTY_DATA}] 未解析到任何有效单据")
    return items, errors


# ---------------------------------------------------------------------------
# 归类与汇总
# ---------------------------------------------------------------------------

def categorize_items(items):
    """
    按类别汇总金额。
    返回 {类别: 总金额}
    """
    summary = defaultdict(float)
    for it in items:
        summary[it.category] += it.amount
    return dict(summary)


def generate_summary(items):
    """
    生成汇总信息（含总额、各类别小计）。
    返回 dict
    """
    total = sum(it.amount for it in items)
    by_category = categorize_items(items)
    return {
        "total": total,
        "count": len(items),
        "by_category": by_category,
    }


# ---------------------------------------------------------------------------
# 输出生成
# ---------------------------------------------------------------------------

def to_markdown(items, summary=None):
    """生成 Markdown 表格"""
    if summary is None:
        summary = generate_summary(items)

    lines = []
    lines.append("# 报销单据明细表\n")
    lines.append(f"- 单据总数: {summary['count']}")
    lines.append(f"- 报销总额: ¥{summary['total']:.2f}\n")

    # 类别汇总
    lines.append("## 类别汇总\n")
    lines.append("| 类别 | 金额 |")
    lines.append("|------|------|")
    for cat, amt in sorted(summary["by_category"].items(), key=lambda x: -x[1]):
        lines.append(f"| {cat} | ¥{amt:.2f} |")
    lines.append("")

    # 明细
    lines.append("## 明细\n")
    lines.append("| 序号 | 日期 | 单据类型 | 金额 | 类别 | 备注 | 置信度 |")
    lines.append("|------|------|----------|------|------|------|--------|")
    for i, it in enumerate(items, start=1):
        d = it.to_dict()
        lines.append(
            f"| {i} | {d['日期']} | {d['单据类型']} | ¥{d['金额']} "
            f"| {d['类别']} | {d['备注']} | {d['置信度']} |"
        )
    lines.append("")
    return "\n".join(lines)


def to_csv(items):
    """生成 CSV 内容（返回字符串）"""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["序号", "日期", "单据类型", "金额", "类别", "备注", "置信度"])
    for i, it in enumerate(items, start=1):
        d = it.to_dict()
        writer.writerow([i, d["日期"], d["单据类型"], d["金额"], d["类别"], d["备注"], d["置信度"]])
    return output.getvalue()


# ---------------------------------------------------------------------------
# 发票核验（格式初筛）
# ---------------------------------------------------------------------------

def verify_invoice(items):
    """
    对每张发票做格式合规性初筛。
    返回 (通过列表, 问题列表)
    """
    passed = []
    problems = []
    for idx, it in enumerate(items, start=1):
        if it.doc_type != "发票":
            passed.append((idx, it, "非发票单据，跳过核验"))
            continue
        # 从备注中尝试提取发票代码/号码/校验码（简化处理）
        code_match = re.search(r"代码[：:]\s*(\d{10,12})", it.note)
        num_match = re.search(r"号码[：:]\s*(\d{8})", it.note)
        chk_match = re.search(r"校验码[：:]\s*(\d{6,20})", it.note)

        code = code_match.group(1) if code_match else ""
        number = num_match.group(1) if num_match else ""
        check = chk_match.group(1) if chk_match else ""

        ok, errs = validate_invoice_fields(code, number, check)
        if ok:
            passed.append((idx, it, "格式合规"))
        else:
            problems.append((idx, it, errs))
    return passed, problems


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------

def process_text(text, output_format="markdown"):
    """
    处理输入文本，返回输出内容。
    """
    items, errors = parse_input(text)

    # 即使有部分错误，如果解析到了条目也继续处理
    if not items:
        raise ValueError(f"[{ERR_EMPTY_DATA}] 没有有效单据，错误: {errors}")

    # 发票核验
    passed, problems = verify_invoice(items)

    # 生成输出
    if output_format == "csv":
        return to_csv(items)
    else:
        return to_markdown(items)


def main_cli():
    """命令行入口"""
    parser = argparse.ArgumentParser(description="报销单据整理工具")
    parser.add_argument("--input", "-i", help="输入文件路径（文本格式）")
    parser.add_argument("--output", "-o", help="输出文件路径（默认 stdout）")
    parser.add_argument("--format", "-f", choices=["markdown", "csv"], default="markdown",
                        help="输出格式（默认 markdown）")
    parser.add_argument("--selftest", action="store_true", help="运行内置自检")
    args = parser.parse_args()

    if args.selftest:
        rc = run_selftest()
        sys.exit(rc)

    if not args.input:
        print(f"[{ERR_CLI_USAGE}] 需要提供 --input 或使用 --selftest", file=sys.stderr)
        return ERR_CLI_USAGE

    # 读取输入
    try:
        with open(args.input, "r", encoding="utf-8") as f:
            text = f.read()
    except Exception as e:
        print(f"[{ERR_INPUT_FILE}] 读取输入文件失败: {e}", file=sys.stderr)
        return ERR_INPUT_FILE

    # 处理
    try:
        output = process_text(text, args.format)
    except ValueError as e:
        print(f"处理失败: {e}", file=sys.stderr)
        return ERR_INPUT_FORMAT

    # 输出
    if args.output:
        try:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(output)
        except Exception as e:
            print(f"[{ERR_OUTPUT_FILE}] 写入输出文件失败: {e}", file=sys.stderr)
            return ERR_OUTPUT_FILE
    else:
        print(output)

    return ERR_OK


# ---------------------------------------------------------------------------
# 自检
# ---------------------------------------------------------------------------

def run_selftest():
    """内置自检，不依赖外部文件"""
    print("=== 自检开始 ===\n")

    # 1. 日期校验
    print("[1] 日期校验")
    assert validate_date("2026-03-15") == (True, "")
    assert validate_date("2026/03/15") == (True, "")
    assert validate_date("2026-13-01")[0] == False
    assert validate_date("2026-02-30")[0] == False
    print("    通过\n")

    # 2. 金额校验
    print("[2] 金额校验")
    assert validate_amount("100") == (True, "")
    assert validate_amount("100.5") == (True, "")
    assert validate_amount("100.55") == (True, "")
    assert validate_amount("abc")[0] == False
    assert validate_amount("-5")[0] == False
    print("    通过\n")

    # 3. 发票格式校验
    print("[3] 发票格式校验")
    ok, probs = validate_invoice_fields("123456789012", "12345678", "123456")
    assert ok and len(probs) == 0
    ok, probs = validate_invoice_fields("123", "12345678", "123456")
    assert not ok and len(probs) == 1
    ok, probs = validate_invoice_fields("123456789012", "123", "123456")
    assert not ok and len(probs) == 1
    print("    通过\n")

    # 4. 文本解析
    print("[4] 文本解析")
    text = """2026-03-01 | 发票 | 100.00 | 交通 | 打车去机场
2026-03-02 | 发票 | 50.50 | 餐饮 | 客户午餐
2026-03-03 | 收据 | 30 | 办公 | 打印耗材
2026-03-04 高铁 200 差旅 出差北京"""
    items, errors = parse_input(text)
    assert len(items) == 4, f"应解析4条，实际{len(items)}"
    assert len(errors) == 0, f"不应有错误: {errors}"
    print(f"    解析到 {len(items)} 条记录")
    print("    通过\n")

    # 5. 类别归类
    print("[5] 类别归类")
    summary = generate_summary(items)
    assert summary["total"] == 380.50, f"总额应为380.50，实际{summary['total']}"
    assert summary["by_category"]["交通"] == 100.00, f"交通应为100.00，实际{summary['by_category'].get('交通')}"
    assert summary["by_category"]["餐饮"] == 50.50, f"餐饮应为50.50，实际{summary['by_category'].get('餐饮')}"
    assert summary["by_category"]["办公"] == 30.00, f"办公应为30.00，实际{summary['by_category'].get('办公')}"
    assert summary["by_category"]["差旅"] == 200.00, f"差旅应为200.00，实际{summary['by_category'].get('差旅')}"
    print(f"    总额: {summary['total']}, 类别: {summary['by_category']}")
    print("    通过\n")

    # 6. 输出生成
    print("[6] 输出生成")
    md = to_markdown(items, summary)
    assert "报销单据明细表" in md
    assert "类别汇总" in md
    csv_out = to_csv(items)
    assert "序号,日期" in csv_out
    print("    Markdown / CSV 生成正常")
    print("    通过\n")

    # 7. 发票核验
    print("[7] 发票核验")
    items_with_invoice = [
        ExpenseItem("2026-03-01", "发票", 100, "交通", "发票代码: 123456789012 号码: 12345678 校验码: 123456"),
        ExpenseItem("2026-03-02", "发票", 50, "餐饮", "发票代码: 123 号码: 12345678 校验码: 123456"),
    ]
    passed, problems = verify_invoice(items_with_invoice)
    assert len(passed) == 1
    assert len(problems) == 1
    print("    通过\n")

    print("=== 全部自检通过 ===")
    return ERR_OK


# ---------------------------------------------------------------------------
# 程序入口
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    sys.exit(main_cli())
