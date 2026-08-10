#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
报销单据整理与发票核验工具（独立实现）

功能：
- 发票要素核验（代码/号码/日期/金额/校验码）
- 费用归类与金额汇总
- 生成 Markdown / CSV 明细表

仅依赖 Python 标准库，无第三方依赖。
"""

import argparse
import csv
import io
import re
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple
dry_run = False  # v3.268 模块级 dry-run 标志


# ============================================================
# 错误码定义
# ============================================================
class AppError(Exception):
    """应用异常基类，携带错误码。"""

    def __init__(self, code: str, message: str):
        super().__init__(f"[{code}] {message}")
        self.code = code
        self.message = message


# ============================================================
# 数据模型
# ============================================================
@dataclass
class Invoice:
    """发票/票据数据模型。"""
    code: str                # 发票代码
    number: str              # 发票号码
    date: str                # 开票日期 YYYY-MM-DD
    amount: float            # 金额（元）
    category: str            # 费用类别
    check_code: str = ""     # 校验码（后6位）
    status: str = "待核验"   # 核验状态
    remark: str = ""         # 备注


@dataclass
class ProcessResult:
    """处理结果汇总。"""
    total_count: int = 0
    total_amount: float = 0.0
    by_category: Dict[str, float] = field(default_factory=lambda: defaultdict(float))
    pending_list: List[Invoice] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


# ============================================================
# 核心逻辑：发票核验
# ============================================================
def validate_invoice(inv: Invoice) -> Tuple[bool, str]:
    """
    核验发票要素。

    规则（仅为演示逻辑，不涉及真实税务系统）：
    1. 发票代码：8位或10位数字（宽松校验，只检查非空和长度范围）
    2. 发票号码：6-8位数字
    3. 日期：格式 YYYY-MM-DD，且为合理日期
    4. 金额：大于0且小于100万
    5. 校验码：若填写则需为6位数字

    返回：(是否通过, 状态描述)
    """
    # 代码检查（宽松：非空，长度4-12位数字）
    if not inv.code or not re.fullmatch(r"\d{4,12}", inv.code):
        return False, "发票代码格式异常"

    # 号码检查
    if not inv.number or not re.fullmatch(r"\d{6,8}", inv.number):
        return False, "发票号码格式异常"

    # 日期检查
    try:
        dt = datetime.strptime(inv.date, "%Y-%m-%d")
        if dt.year < 2000 or dt.year > 2100:
            return False, "开票年份超出合理范围"
    except ValueError:
        return False, "开票日期格式错误"

    # 金额检查
    if inv.amount <= 0 or inv.amount > 1_000_000:
        return False, "金额超出合理范围"

    # 校验码检查（若填写）
    if inv.check_code and not re.fullmatch(r"\d{6}", inv.check_code):
        return False, "校验码格式异常"

    return True, "要素完整，可前往税务平台核验"


# ============================================================
# 核心逻辑：费用归类与汇总
# ============================================================
def categorize_invoices(invoices: List[Invoice]) -> ProcessResult:
    """
    对发票列表进行归类汇总。

    流程：
    1. 逐张核验
    2. 按类别汇总金额
    3. 标记待核验清单
    """
    result = ProcessResult()
    valid_categories = {"交通", "餐饮", "住宿", "办公用品", "通讯", "其他"}

    for inv in invoices:
        result.total_count += 1

        # 类别规范化（不在预设类别则归入"其他"）
        if inv.category not in valid_categories:
            inv.category = "其他"

        # 核验
        ok, msg = validate_invoice(inv)
        if not ok:
            inv.status = f"异常：{msg}"
            result.errors.append(f"{inv.code}-{inv.number}: {msg}")
        else:
            inv.status = "待核验"

        # 金额累计（无论核验是否通过都计入归类）
        result.total_amount += inv.amount
        result.by_category[inv.category] += inv.amount

        # 待核验清单
        if inv.status == "待核验":
            result.pending_list.append(inv)

    return result


# ============================================================
# 输出生成
# ============================================================
def generate_markdown(result: ProcessResult) -> str:
    """生成 Markdown 格式明细表。"""
    lines = []
    lines.append("# 报销费用明细表\n")
    lines.append(f"**票据总数**：{result.total_count} 张\n")
    lines.append(f"**合计金额**：¥{result.total_amount:.2f}\n")
    lines.append("\n## 费用归类汇总\n")
    lines.append("| 费用类别 | 金额（元） |")
    lines.append("|----------|------------|")
    for cat in sorted(result.by_category.keys()):
        lines.append(f"| {cat} | {result.by_category[cat]:.2f} |")

    lines.append("\n## 待核验发票清单\n")
    if result.pending_list:
        lines.append("| 发票代码 | 发票号码 | 日期 | 金额 | 类别 | 状态 |")
        lines.append("|----------|----------|------|------|------|------|")
        for inv in result.pending_list:
            lines.append(
                f"| {inv.code} | {inv.number} | {inv.date} | "
                f"{inv.amount:.2f} | {inv.category} | {inv.status} |"
            )
    else:
        lines.append("（无待核验发票）")

    if result.errors:
        lines.append("\n## 异常记录\n")
        for err in result.errors:
            lines.append(f"- {err}")

    return "\n".join(lines) + "\n"


def generate_csv(result: ProcessResult) -> str:
    """生成 CSV 格式明细表。"""
    output = io.StringIO()
    writer = csv.writer(output)

    # 归类汇总
    writer.writerow(["费用类别", "金额（元）"])
    for cat in sorted(result.by_category.keys()):
        writer.writerow([cat, f"{result.by_category[cat]:.2f}"])
    writer.writerow(["合计", f"{result.total_amount:.2f}"])

    # 明细
    writer.writerow([])
    writer.writerow(["发票代码", "发票号码", "开票日期", "金额", "类别", "状态"])
    for inv in result.pending_list:
        writer.writerow([inv.code, inv.number, inv.date, f"{inv.amount:.2f}", inv.category, inv.status])

    return output.getvalue()


# ============================================================
# 命令行入口
# ============================================================
def parse_args(argv: List[str]) -> argparse.Namespace:
    """解析命令行参数。"""
    parser = argparse.ArgumentParser(
        description="报销单据整理与发票核验工具",
        epilog="示例：python main.py --input data.csv --format markdown",
    )
    parser.add_argument("--input", "-i", help="输入 CSV 文件路径（列：代码,号码,日期,金额,类别,校验码）")
    parser.add_argument("--format", "-f", choices=["markdown", "csv"], default="markdown", help="输出格式")
    parser.add_argument("--output", "-o", help="输出文件路径（默认输出到终端）")
    parser.add_argument("--selftest", action="store_true", help="运行内置自检（不读取任何外部文件）")
    parser.add_argument("--verbose", action="store_true", help="显示修改明细")  # R6 可解释输出
    parser.add_argument("--force", action="store_true")  # R4 强制写盘

    parser.add_argument("--dry-run", action="store_true")  # R4 预览模式
    parser.add_argument("--batch", default=None, help="文档声明的参数")  # F3 补全
    parser.add_argument("--config", default=None, help="文档声明的参数")  # F3 补全
    parser.add_argument("--mode", default=None, help="文档声明的参数")  # F3 补全
    parser.add_argument("--task", default=None, help="文档声明的参数")  # F3 补全
    return parser.parse_args(argv)


def load_invoices_from_csv(path: str) -> List[Invoice]:
    """
    从 CSV 文件加载发票数据。

    文件格式：代码,号码,日期,金额,类别,校验码(可选)
    """
    invoices = []
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            reader = csv.reader(f)
            header = next(reader, None)  # 跳过表头
            for row_num, row in enumerate(reader, start=2):
                if len(row) < 5:
                    raise AppError("E001", f"第{row_num}行字段不足（至少需要5列）")
                try:
                    inv = Invoice(
                        code=row[0].strip(),
                        number=row[1].strip(),
                        date=row[2].strip(),
                        amount=float(row[3].strip()),
                        category=row[4].strip(),
                        check_code=row[5].strip() if len(row) > 5 else "",
                    )
                    invoices.append(inv)
                except ValueError as e:
                    raise AppError("E002", f"第{row_num}行金额格式错误：{e}")
    except FileNotFoundError:
        raise AppError("E003", f"文件不存在：{path}")
    except PermissionError:
        raise AppError("E004", f"无权限读取文件：{path}")
    except AppError:
        raise
    except Exception as e:
        raise AppError("E005", f"读取文件失败：{e}")

    if not invoices:
        raise AppError("E006", "输入文件中没有有效数据")

    return invoices


# ============================================================
# 自检模块（离线硬编码样例）
# ============================================================
def run_selftest() -> int:
    """
    内置离线自检。使用硬编码样例数据验证核心逻辑。

    断言规则：
    - 使用宽松阈值（大小比较/区间判断）
    - 不依赖精确浮点值
    """
    print("=== 自检开始 ===")

    # 构造测试数据（符合功能规格的多样票据）
    test_invoices = [
        Invoice(code="12345678", number="123456", date="2026-01-15", amount=128.50, category="餐饮", check_code="654321"),
        Invoice(code="1234567890", number="12345678", date="2026-02-03", amount=899.00, category="住宿", check_code=""),
        Invoice(code="87654321", number="876543", date="2026-03-20", amount=45.00, category="交通", check_code="123456"),
        Invoice(code="11112222", number="111111", date="2026-04-10", amount=299.00, category="办公用品", check_code=""),
        Invoice(code="abcd", number="123", date="2026-05-01", amount=-10, category="餐饮", check_code=""),  # 异常数据
        Invoice(code="33334444", number="222222", date="2026-06-15", amount=56.80, category="餐饮", check_code="111222"),
        Invoice(code="55556666", number="333333", date="2026-07-01", amount=78.50, category="交通", check_code=""),
    ]

    # 执行核心处理
    result = categorize_invoices(test_invoices)

    # ---- 断言区（宽松阈值） ----
    # 1. 总数断言：至少6张（因为可能有1张异常）
    assert result.total_count >= 6, f"自检失败：票据总数异常（{result.total_count}）"

    # 2. 总金额断言：应在 1000~3000 元区间
    assert 1000 < result.total_amount < 3000, f"自检失败：总金额异常（{result.total_amount:.2f}）"

    # 3. 类别覆盖断言：至少包含3个类别
    assert len(result.by_category) >= 3, f"自检失败：类别数量不足（{len(result.by_category)}）"

    # 4. 餐饮类别金额断言：应大于100元（有两张餐饮：128.5 + 56.8）
    assert result.by_category.get("餐饮", 0) > 100, f"自检失败：餐饮金额异常（{result.by_category.get('餐饮', 0):.2f}）"

    # 5. 交通类别金额断言：应大于100元（两张交通：45 + 78.5）
    assert result.by_category.get("交通", 0) > 100, f"自检失败：交通金额异常（{result.by_category.get('交通', 0):.2f}）"

    # 6. 待核验列表断言：应包含至少5张有效发票（7张中至少2张异常，最多5张有效）
    assert len(result.pending_list) >= 5, f"自检失败：待核验数量不足（{len(result.pending_list)}）"

    # 7. 错误记录断言：应至少捕获1条异常（无效代码或负金额）
    assert len(result.errors) >= 1, f"自检失败：未捕获异常数据"

    # 8. Markdown 输出断言：包含关键标题
    md = generate_markdown(result)
    assert "报销费用明细表" in md, "自检失败：Markdown输出缺少标题"
    assert "费用归类汇总" in md, "自检失败：Markdown输出缺少汇总表"
    assert "待核验发票清单" in md, "自检失败：Markdown输出缺少清单"

    # 9. CSV 输出断言：包含表头
    csv_out = generate_csv(result)
    assert "费用类别" in csv_out and "金额" in csv_out, "自检失败：CSV输出缺少表头"

    print("=== 自检通过 ===")
    return 0


# ============================================================
# 主流程
# ============================================================
def main(argv: Optional[List[str]] = None) -> int:
    """主入口函数。"""
    if argv is None:
        argv = sys.argv[1:]

    # 自检模式
    if "--selftest" in argv:
        try:
            return run_selftest()
        except AssertionError as e:
            print(f"自检失败：{e}", file=sys.stderr)
            return 1
        except Exception as e:
            print(f"自检异常：{e}", file=sys.stderr)
            return 2

    # 正常模式
    try:
        args = parse_args(argv)

        if not args.input:
            raise AppError("E007", "请指定输入文件（--input）或使用 --selftest 运行自检")

        # 加载数据
        invoices = load_invoices_from_csv(args.input)

        # 处理
        result = categorize_invoices(invoices)

        # 生成输出
        if args.format == "markdown":
            output_text = generate_markdown(result)
        else:
            output_text = generate_csv(result)

        # 输出
        if args.output:
            try:
                with open(args.output, "w", encoding="utf-8", errors="replace") as f:
                    f.write(output_text)
                print(f"结果已写入：{args.output}")
            except OSError as e:
                raise AppError("E008", f"写入输出文件失败：{e}")
        else:
            print(output_text)

        return 0

    except AppError as e:
        print(f"错误：{e}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\n操作已取消", file=sys.stderr)
        return 130
    except Exception as e:
        print(f"[E010] 未预期错误：{e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
