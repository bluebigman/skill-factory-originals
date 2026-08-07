#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
发票识别 (invoice-scanner) - 独立实现脚本

本脚本依据功能规格独立编写（clean-room），不包含任何既有代码。
仅使用 Python 标准库，无第三方依赖。

功能：
  - 解析发票文本/结构化输入，提取关键字段
  - 按置信度标注输出（≥90% 直接输出；85%-90% 建议复核；<85% 标记 [需核实]）
  - 支持批量输入
  - 内置离线自检（--selftest），不读取外部文件、不依赖工作目录、不访问网络

用法示例：
  python main.py --input "发票号: INV-2024-001 金额: 123.45 日期: 2024-06-01"
  python main.py --batch "文件1内容" "文件2内容"
  python main.py --selftest
"""

import argparse
import re
import sys
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# 错误码定义（依据规格 E001-E005，扩展至 E010）
# ---------------------------------------------------------------------------
ERROR_MESSAGES: Dict[str, str] = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：...",
    "E003": "输入格式不符合要求，示例：发票号: XXX 金额: XXX 日期: XXXX-XX-XX",
    "E004": "这超出了本工具的能力范围，建议使用专业财务软件或咨询持证人士",
    "E005": "结果无法确定，建议：检查原始发票或重新拍摄/扫描",
    "E006": "内部错误：数据解析异常，请重试",
    "E007": "内部错误：输出格式化失败",
    "E008": "参数错误：请检查命令行参数",
    "E009": "内部错误：自检失败，请报告问题",
    "E010": "内部错误：未知异常",
}


def error(message_code: str, extra: str = "") -> str:
    """返回标准化错误信息，附带可选补充说明。"""
    base = ERROR_MESSAGES.get(message_code, ERROR_MESSAGES["E010"])
    if extra:
        return f"[{message_code}] {base} {extra}"
    return f"[{message_code}] {base}"


# ---------------------------------------------------------------------------
# 核心数据模型
# ---------------------------------------------------------------------------
class InvoiceData:
    """发票结构化数据。"""

    def __init__(
        self,
        invoice_number: str = "",
        amount: float = 0.0,
        date: str = "",
        merchant: str = "",
        items: Optional[List[Dict[str, Any]]] = None,
        confidence: float = 1.0,
    ) -> None:
        self.invoice_number = invoice_number
        self.amount = amount
        self.date = date
        self.merchant = merchant
        self.items = items if items is not None else []
        self.confidence = confidence

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式。"""
        return {
            "invoice_number": self.invoice_number,
            "amount": self.amount,
            "date": self.date,
            "merchant": self.merchant,
            "items": self.items,
            "confidence": self.confidence,
            "needs_review": self.confidence < 0.90,
            "needs_verification": self.confidence < 0.85,
        }

    def __repr__(self) -> str:
        return (
            f"InvoiceData(invoice_number={self.invoice_number!r}, "
            f"amount={self.amount!r}, date={self.date!r}, "
            f"merchant={self.merchant!r}, confidence={self.confidence!r})"
        )


# ---------------------------------------------------------------------------
# 核心解析逻辑
# ---------------------------------------------------------------------------
def _parse_amount(text: str) -> Optional[float]:
    """从文本中提取金额（支持货币符号、千分位）。"""
    # 匹配数字（含小数点和千分位逗号）
    patterns = [
        r"金额[:：\s]*([0-9,]+\.?\d*)",
        r"total[:：\s]*([0-9,]+\.?\d*)",
        r"合计[:：\s]*([0-9,]+\.?\d*)",
        r"amount[:：\s]*([0-9,]+\.?\d*)",
        r"([0-9]+,[0-9]{3}\.[0-9]{2})",
        r"([0-9]+\.[0-9]{2})",
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            try:
                # 移除千分位逗号
                cleaned = m.group(1).replace(",", "")
                return float(cleaned)
            except ValueError:
                continue
    return None


def _parse_date(text: str) -> Optional[str]:
    """从文本中提取日期（支持多种常见格式）。"""
    patterns = [
        r"日期[:：\s]*(\d{4}[-/年]\d{1,2}[-/月]\d{1,2}日?)",
        r"date[:：\s]*(\d{4}[-/]\d{1,2}[-/]\d{1,2})",
        r"(\d{4}[-/年]\d{1,2}[-/月]\d{1,2}日?)",
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            raw = m.group(1)
            # 统一格式化为 YYYY-MM-DD
            raw = raw.replace("年", "-").replace("月", "-").replace("日", "")
            raw = raw.replace("/", "-")
            parts = raw.split("-")
            if len(parts) == 3:
                try:
                    year = int(parts[0])
                    month = int(parts[1])
                    day = int(parts[2])
                    if 1900 <= year <= 2100 and 1 <= month <= 12 and 1 <= day <= 31:
                        return f"{year:04d}-{month:02d}-{day:02d}"
                except ValueError:
                    continue
    return None


def _parse_invoice_number(text: str) -> Optional[str]:
    """从文本中提取发票号。"""
    patterns = [
        r"发票号[:：\s]*([A-Za-z0-9\-_]+)",
        r"invoice\s*(?:no|number|#)[:：\s]*([A-Za-z0-9\-_]+)",
        r"编号[:：\s]*([A-Za-z0-9\-_]+)",
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            return m.group(1)
    return None


def _parse_merchant(text: str) -> Optional[str]:
    """从文本中提取商户名称。"""
    patterns = [
        r"商户[:：\s]*([\u4e00-\u9fa5A-Za-z0-9\s]+?)(?:\s|$)",
        r"merchant[:：\s]*([A-Za-z0-9\s]+?)(?:\s|$)",
        r"商家[:：\s]*([\u4e00-\u9fa5A-Za-z0-9\s]+?)(?:\s|$)",
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            return m.group(1).strip()
    return None


def _parse_items(text: str) -> List[Dict[str, Any]]:
    """尝试解析商品/服务明细（宽松解析，不保证完整）。"""
    items = []
    # 简单匹配 "商品名 单价 数量" 或 "商品名 金额" 模式
    lines = text.split("\n")
    for line in lines:
        line = line.strip()
        if not line:
            continue
        # 匹配 "名称 单价 数量" 或 "名称 金额"
        m = re.match(r"^([\u4e00-\u9fa5A-Za-z0-9\s\-]+?)\s+([0-9]+\.?\d*)\s+([0-9]+\.?\d*)$", line)
        if m:
            items.append({
                "name": m.group(1).strip(),
                "unit_price": float(m.group(2)),
                "quantity": float(m.group(3)),
            })
            continue
        m = re.match(r"^([\u4e00-\u9fa5A-Za-z0-9\s\-]+?)\s+([0-9]+\.?\d*)$", line)
        if m:
            items.append({
                "name": m.group(1).strip(),
                "amount": float(m.group(2)),
            })
    return items


def _compute_confidence(invoice: InvoiceData) -> float:
    """根据字段完整性计算置信度（宽松规则）。"""
    score = 0.0
    if invoice.invoice_number:
        score += 0.4
    if invoice.amount > 0:
        score += 0.3
    if invoice.date:
        score += 0.2
    if invoice.merchant:
        score += 0.1
    # 有明细则额外加分
    if invoice.items:
        score = min(1.0, score + 0.1)
    return max(0.0, min(1.0, score))


def parse_invoice_text(text: str) -> InvoiceData:
    """
    解析发票文本，返回结构化数据。

    参数:
        text: 发票文本内容

    返回:
        InvoiceData 对象
    """
    if not text or not text.strip():
        raise ValueError(error("E001"))

    invoice = InvoiceData()
    invoice.invoice_number = _parse_invoice_number(text) or ""
    invoice.amount = _parse_amount(text) or 0.0
    invoice.date = _parse_date(text) or ""
    invoice.merchant = _parse_merchant(text) or ""
    invoice.items = _parse_items(text)

    # 计算置信度
    invoice.confidence = _compute_confidence(invoice)

    return invoice


def format_output(invoice: InvoiceData) -> Dict[str, Any]:
    """
    格式化输出结果，包含置信度标注。

    返回:
        字典格式的结果
    """
    result = invoice.to_dict()
    # 根据置信度添加标注
    if invoice.confidence >= 0.90:
        result["status"] = "可直接使用"
    elif invoice.confidence >= 0.85:
        result["status"] = "建议复核"
    else:
        result["status"] = "[需核实]"
        # 说明不确定点
        uncertain = []
        if not invoice.invoice_number:
            uncertain.append("发票号")
        if not invoice.amount:
            uncertain.append("金额")
        if not invoice.date:
            uncertain.append("日期")
        if uncertain:
            result["uncertain_fields"] = uncertain
    return result


def process_input(user_input: str) -> Dict[str, Any]:
    """
    处理单个用户输入。

    参数:
        user_input: 用户提供的文本内容

    返回:
        结构化结果字典
    """
    try:
        invoice = parse_invoice_text(user_input)
        return format_output(invoice)
    except ValueError as e:
        return {"error": str(e)}
    except Exception:
        return {"error": error("E010")}


def process_batch(inputs: List[str]) -> List[Dict[str, Any]]:
    """
    批量处理多个输入。

    参数:
        inputs: 输入文本列表

    返回:
        结果字典列表
    """
    return [process_input(text) for text in inputs]


# ---------------------------------------------------------------------------
# 自检逻辑（--selftest）
# ---------------------------------------------------------------------------
def _run_selftest() -> int:
    """
    内置自检函数，使用硬编码样例数据离线验证核心逻辑。

    返回:
        0 表示通过，非 0 表示失败
    """
    print("开始自检...")

    # 测试样例 1：完整发票
    sample_1 = """
    发票号: INV-2024-001
    商户: 测试超市
    日期: 2024-06-01
    金额: 123.45
    商品A 10.00 2
    商品B 20.00 1
    """
    try:
        result_1 = process_input(sample_1)
        assert "error" not in result_1, f"样例1失败: {result_1.get('error')}"
        assert result_1["invoice_number"] == "INV-2024-001", f"发票号解析错误: {result_1['invoice_number']}"
        assert abs(result_1["amount"] - 123.45) < 0.01, f"金额解析错误: {result_1['amount']}"
        assert result_1["date"] == "2024-06-01", f"日期解析错误: {result_1['date']}"
        assert result_1["confidence"] >= 0.85, f"置信度过低: {result_1['confidence']}"
        print("  样例1（完整发票）: PASS")
    except AssertionError as e:
        print(f"  样例1（完整发票）: FAIL - {e}")
        return 1

    # 测试样例 2：部分信息（缺少商户和明细）
    sample_2 = "发票号: INV-2024-002 金额: 88.50 日期: 2024/06/15"
    try:
        result_2 = process_input(sample_2)
        assert "error" not in result_2, f"样例2失败: {result_2.get('error')}"
        assert result_2["invoice_number"] == "INV-2024-002", f"发票号解析错误: {result_2['invoice_number']}"
        assert abs(result_2["amount"] - 88.50) < 0.01, f"金额解析错误: {result_2['amount']}"
        assert result_2["date"] == "2024-06-15", f"日期解析错误: {result_2['date']}"
        # 缺少商户，置信度应低于 1.0
        assert result_2["confidence"] < 1.0, "缺少字段时置信度不应为 1.0"
        print("  样例2（部分信息）: PASS")
    except AssertionError as e:
        print(f"  样例2（部分信息）: FAIL - {e}")
        return 1

    # 测试样例 3：空输入（应返回 E001 错误）
    try:
        result_3 = process_input("")
        assert "error" in result_3, "空输入应返回错误"
        assert "E001" in result_3["error"], f"错误码不正确: {result_3['error']}"
        print("  样例3（空输入错误处理）: PASS")
    except AssertionError as e:
        print(f"  样例3（空输入错误处理）: FAIL - {e}")
        return 1

    # 测试样例 4：批量处理
    try:
        batch_inputs = [
            "发票号: INV-B-001 金额: 50.00 日期: 2024-07-01",
            "发票号: INV-B-002 金额: 75.25 日期: 2024-07-02",
        ]
        batch_results = process_batch(batch_inputs)
        assert len(batch_results) == 2, f"批量结果数量错误: {len(batch_results)}"
        assert all("error" not in r for r in batch_results), "批量处理存在错误"
        assert batch_results[0]["invoice_number"] == "INV-B-001", "批量样例1发票号错误"
        assert batch_results[1]["invoice_number"] == "INV-B-002", "批量样例2发票号错误"
        print("  样例4（批量处理）: PASS")
    except AssertionError as e:
        print(f"  样例4（批量处理）: FAIL - {e}")
        return 1

    # 测试样例 5：置信度标注
    try:
        # 只有金额，置信度应很低
        result_5 = process_input("金额: 123.45")
        assert "error" not in result_5, f"样例5失败: {result_5.get('error')}"
        assert result_5["confidence"] < 0.85, f"置信度应低于0.85: {result_5['confidence']}"
        assert result_5["status"] == "[需核实]", f"状态标注错误: {result_5['status']}"
        print("  样例5（置信度标注）: PASS")
    except AssertionError as e:
        print(f"  样例5（置信度标注）: FAIL - {e}")
        return 1

    # 测试样例 6：格式兼容性
    try:
        # 中文日期格式
        result_6 = process_input("发票号: INV-2024-003 金额: 200 日期: 2024年8月8日")
        assert "error" not in result_6, f"样例6失败: {result_6.get('error')}"
        assert result_6["date"] == "2024-08-08", f"中文日期解析错误: {result_6['date']}"
        print("  样例6（中文日期格式）: PASS")
    except AssertionError as e:
        print(f"  样例6（中文日期格式）: FAIL - {e}")
        return 1

    print("所有自检样例通过！")
    return 0


# ---------------------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------------------
def main() -> int:
    """主入口函数。"""
    parser = argparse.ArgumentParser(
        description="发票识别工具 - 从文本中提取结构化发票信息",
        epilog="示例: python main.py --input '发票号: INV-001 金额: 100.00'",
    )
    parser.add_argument(
        "--input", "-i",
        type=str,
        help="单个输入文本（发票内容）",
    )
    parser.add_argument(
        "--batch",
        type=str,
        nargs="+",
        help="批量输入文本（多个参数）",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检（无需任何外部依赖）",
    )
    parser.add_argument(
        "--format",
        type=str,
        choices=["json", "text"],
        default="json",
        help="输出格式（默认: json）",
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        return _run_selftest()

    # 参数校验
    if not args.input and not args.batch:
        print(error("E008", "请使用 --input 或 --batch 提供输入"))
        return 1

    # 处理输入
    try:
        if args.batch:
            results = process_batch(args.batch)
        else:
            results = [process_input(args.input)]

        # 输出结果
        import json

        for idx, result in enumerate(results, 1):
            if args.format == "json":
                print(json.dumps(result, ensure_ascii=False, indent=2))
            else:
                # 文本格式输出
                if "error" in result:
                    print(f"[{idx}] 错误: {result['error']}")
                else:
                    print(f"[{idx}] 发票号: {result.get('invoice_number', 'N/A')}")
                    print(f"    金额: {result.get('amount', 0.0)}")
                    print(f"    日期: {result.get('date', 'N/A')}")
                    print(f"    商户: {result.get('merchant', 'N/A')}")
                    print(f"    状态: {result.get('status', '未知')}")
                    print(f"    置信度: {result.get('confidence', 0.0):.2%}")
            if len(results) > 1:
                print()  # 批量输出时用空行分隔

        return 0

    except Exception as e:
        print(error("E010", str(e)))
        return 1


if __name__ == "__main__":
    sys.exit(main())
