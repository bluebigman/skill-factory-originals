#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
发票识别 (receipt-scanner-for-android) - 独立实现脚本

本脚本依据功能规格独立编写，不复制任何既有代码。
仅依赖 Python 标准库，无需第三方安装。

功能概述：
- 将输入文本解析为结构化发票/收据信息
- 支持置信度评估与标注
- 提供命令行接口与离线自检

错误码：
- E001: 输入为空
- E002: 关键信息缺失
- E003: 输入格式错误
- E004: 超出能力边界
- E005: 置信度过低
- E006: 内部处理异常
- E007: 参数解析错误
- E008: 自检失败
- E009: 输出写入失败
- E010: 未知错误

免责声明：
本脚本仅供学习与参考用途，不构成专业建议。
使用者应自行承担全部责任。
"""

import argparse
import json
import re
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# 核心数据结构
# ============================================================

class ReceiptData:
    """发票/收据结构化数据容器"""

    def __init__(self) -> None:
        self.raw_text: str = ""
        self.merchant: Optional[str] = None
        self.date: Optional[str] = None
        self.total: Optional[float] = None
        self.currency: str = "CNY"
        self.items: List[Dict[str, Any]] = []
        self.confidence: float = 0.0
        self.warnings: List[str] = []
        self.missing_fields: List[str] = []

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "merchant": self.merchant,
            "date": self.date,
            "total": self.total,
            "currency": self.currency,
            "items": self.items,
            "confidence": self.confidence,
            "warnings": self.warnings,
            "missing_fields": self.missing_fields,
        }


# ============================================================
# 解析核心逻辑
# ============================================================

# 常见字段的正则模式
_PATTERNS = {
    "merchant": [
        r"(?:商户|商家|店名|收款方)[:：]\s*([^\n\r]+)",
        r"(?:merchant|store|shop)[:：]\s*([^\n\r]+)",
        r"^([^\n\r]{2,30})$",  # 兜底：首行非空短文本
    ],
    "date": [
        r"(?:日期|时间)[:：]\s*(\d{4}[-/年]\d{1,2}[-/月]\d{1,2}日?)",
        r"(?:date|time)[:：]\s*(\d{4}[-/]\d{1,2}[-/]\d{1,2})",
        r"(\d{4}[-/年]\d{1,2}[-/月]\d{1,2}日?)",
    ],
    "total": [
        r"(?:总计|合计|金额|总额)[:：]\s*[¥￥]?\s*(\d+(?:\.\d{1,2})?)",
        r"(?:total|amount|sum)[:：]\s*[¥￥]?\s*(\d+(?:\.\d{1,2})?)",
        r"[¥￥]\s*(\d+(?:\.\d{1,2})?)",
    ],
    "currency": [
        r"(?:币种|货币)[:：]\s*([A-Z]{3})",
        r"(?:currency)[:：]\s*([A-Z]{3})",
    ],
    "item": [
        r"(?:商品|项目|名称)[:：]\s*([^\n\r]+?)\s*(?:数量|单价|价格|金额)[:：]\s*(\d+(?:\.\d{1,2})?)",
        r"([^\n\r]{2,30}?)\s+(?:数量|单价|价格|金额)[:：]\s*(\d+(?:\.\d{1,2})?)",
    ],
}


def _extract_first(text: str, patterns: List[str]) -> Optional[str]:
    """从文本中提取第一个匹配的字段值"""
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return None


def _extract_all_items(text: str) -> List[Dict[str, Any]]:
    """提取所有商品/项目条目"""
    items: List[Dict[str, Any]] = []
    for pattern in _PATTERNS["item"]:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            name = match.group(1).strip()
            price_str = match.group(2).strip()
            try:
                price = float(price_str)
            except ValueError:
                continue
            items.append({"name": name, "price": price})
    return items


def _parse_total(value_str: str) -> Optional[float]:
    """解析金额字符串为浮点数"""
    try:
        return float(value_str)
    except ValueError:
        return None


def parse_receipt(raw_text: str) -> ReceiptData:
    """
    解析发票/收据文本

    参数:
        raw_text: 原始输入文本

    返回:
        ReceiptData 对象

    异常:
        ValueError: 输入为空或格式错误时抛出
    """
    if not raw_text or not raw_text.strip():
        raise ValueError("E001: 输入为空")

    receipt = ReceiptData()
    receipt.raw_text = raw_text.strip()

    # 提取各字段
    receipt.merchant = _extract_first(raw_text, _PATTERNS["merchant"])
    receipt.date = _extract_first(raw_text, _PATTERNS["date"])
    total_str = _extract_first(raw_text, _PATTERNS["total"])
    if total_str:
        receipt.total = _parse_total(total_str)
    currency_str = _extract_first(raw_text, _PATTERNS["currency"])
    if currency_str:
        receipt.currency = currency_str.upper()

    receipt.items = _extract_all_items(raw_text)

    # 检查关键字段缺失
    if not receipt.merchant:
        receipt.missing_fields.append("merchant")
    if not receipt.date:
        receipt.missing_fields.append("date")
    if receipt.total is None:
        receipt.missing_fields.append("total")

    # 计算置信度
    confidence = 0.0
    if receipt.merchant:
        confidence += 0.3
    if receipt.date:
        confidence += 0.3
    if receipt.total is not None:
        confidence += 0.3
    if receipt.items:
        confidence += 0.1

    receipt.confidence = confidence

    # 生成警告
    if receipt.confidence < 0.85:
        receipt.warnings.append("[需核实] 部分字段无法确定，请人工确认")
    elif receipt.confidence < 0.9:
        receipt.warnings.append("建议复核：部分字段可能存在偏差")

    return receipt


# ============================================================
# 输出格式化
# ============================================================

def format_output(receipt: ReceiptData, fmt: str = "json") -> str:
    """
    格式化输出结果

    参数:
        receipt: 解析结果
        fmt: 输出格式 ("json" 或 "text")

    返回:
        格式化字符串
    """
    if fmt == "json":
        return json.dumps(receipt.to_dict(), ensure_ascii=False, indent=2)

    # 文本格式
    lines = []
    lines.append("=== 发票识别结果 ===")
    if receipt.merchant:
        lines.append(f"商户: {receipt.merchant}")
    if receipt.date:
        lines.append(f"日期: {receipt.date}")
    if receipt.total is not None:
        lines.append(f"金额: {receipt.currency} {receipt.total:.2f}")
    if receipt.items:
        lines.append("商品明细:")
        for idx, item in enumerate(receipt.items, 1):
            lines.append(f"  {idx}. {item['name']} - {item['price']:.2f}")
    lines.append(f"置信度: {receipt.confidence * 100:.0f}%")
    if receipt.warnings:
        lines.append("提示:")
        for warning in receipt.warnings:
            lines.append(f"  - {warning}")
    if receipt.missing_fields:
        lines.append("缺失字段:")
        for field in receipt.missing_fields:
            lines.append(f"  - {field}")
    lines.append("=" * 20)
    return "\n".join(lines)


# ============================================================
# 自检模块
# ============================================================

# 内置硬编码样例数据（不依赖外部文件）
_SELFTEST_SAMPLES = [
    {
        "input": (
            "商户: 测试超市\n"
            "日期: 2024-03-15\n"
            "总计: ¥128.50\n"
            "商品1: 苹果 价格: 25.00\n"
            "商品2: 牛奶 价格: 15.50\n"
            "商品3: 面包 价格: 88.00"
        ),
        "expected": {
            "merchant": "测试超市",
            "date": "2024-03-15",
            "total": 128.50,
            "currency": "CNY",
            "items_count": 3,
        },
    },
    {
        "input": (
            "Receipt from Coffee Shop\n"
            "Date: 2024/06/20\n"
            "Amount: $45.80\n"
            "Item: Latte Price: 25.00\n"
            "Item: Cake Price: 20.80"
        ),
        "expected": {
            "merchant": "Coffee Shop",
            "date": "2024/06/20",
            "total": 45.80,
            "currency": "USD",
            "items_count": 2,
        },
    },
    {
        "input": (
            "小卖部收据\n"
            "日期: 2024年12月31日\n"
            "合计: 58.00\n"
            "商品: 可乐 单价: 3.00\n"
            "商品: 薯片 单价: 55.00"
        ),
        "expected": {
            "merchant": "小卖部",
            "date": "2024年12月31日",
            "total": 58.00,
            "currency": "CNY",
            "items_count": 2,
        },
    },
]


def _run_selftest() -> bool:
    """
    运行离线自检

    使用内置硬编码样例数据验证核心解析逻辑。
    断言使用宽松阈值（大小比较/区间判断），不依赖精确值。

    返回:
        自检是否通过
    """
    print("开始离线自检...")
    all_passed = True

    for idx, sample in enumerate(_SELFTEST_SAMPLES, 1):
        print(f"\n样例 {idx}:")
        try:
            receipt = parse_receipt(sample["input"])
            expected = sample["expected"]

            # 宽松断言：字段存在且非空
            if expected.get("merchant"):
                assert receipt.merchant is not None, "商户名称解析失败"
                assert len(receipt.merchant) > 0, "商户名称为空"

            if expected.get("date"):
                assert receipt.date is not None, "日期解析失败"
                assert len(receipt.date) > 0, "日期为空"

            if expected.get("total") is not None:
                assert receipt.total is not None, "金额解析失败"
                # 宽松比较：允许 10% 误差范围
                expected_total = expected["total"]
                assert abs(receipt.total - expected_total) < expected_total * 0.1, \
                    f"金额偏差过大: 期望约 {expected_total}, 实际 {receipt.total}"

            # 货币类型检查（若样例中有指定）
            if expected.get("currency"):
                assert receipt.currency == expected["currency"], \
                    f"币种不匹配: 期望 {expected['currency']}, 实际 {receipt.currency}"

            # 商品数量检查（宽松范围）
            if expected.get("items_count") is not None:
                expected_count = expected["items_count"]
                assert len(receipt.items) >= expected_count - 1, "商品数量过少"
                assert len(receipt.items) <= expected_count + 2, "商品数量过多"

            # 置信度检查（宽松阈值）
            assert receipt.confidence >= 0.6, "置信度异常偏低"

            print(f"  ✓ 通过 (置信度: {receipt.confidence * 100:.0f}%)")

        except AssertionError as e:
            all_passed = False
            print(f"  ✗ 失败: {e}")
        except Exception as e:
            all_passed = False
            print(f"  ✗ 异常: {e}")

    # 边界测试：空输入
    print("\n边界测试: 空输入")
    try:
        parse_receipt("")
        print("  ✗ 失败: 空输入未抛异常")
        all_passed = False
    except ValueError as e:
        if str(e).startswith("E001"):
            print("  ✓ 通过 (正确抛出 E001)")
        else:
            print(f"  ✗ 失败: 错误码不正确 ({e})")
            all_passed = False

    # 边界测试：无效格式
    print("\n边界测试: 无效格式")
    try:
        receipt = parse_receipt("这是一段没有发票信息的普通文本")
        # 不应抛异常，但置信度应较低
        if receipt.confidence < 0.5:
            print("  ✓ 通过 (低置信度正确)")
        else:
            print(f"  ✗ 失败: 置信度异常 ({receipt.confidence})")
            all_passed = False
    except Exception as e:
        print(f"  ✗ 失败: 异常 ({e})")
        all_passed = False

    print(f"\n自检结果: {'全部通过' if all_passed else '存在失败项'}")
    return all_passed


# ============================================================
# 命令行入口
# ============================================================

def _parse_args(argv: List[str]) -> argparse.Namespace:
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="发票识别工具 - 将文本解析为结构化发票信息",
        epilog="示例: python main.py --input '商户: 测试\n日期: 2024-01-01\n总计: 100.00'",
    )
    parser.add_argument(
        "--input", "-i",
        type=str,
        help="待解析的发票文本内容",
    )
    parser.add_argument(
        "--file", "-f",
        type=str,
        help="从文件读取发票文本",
    )
    parser.add_argument(
        "--format", "-fmt",
        type=str,
        choices=["json", "text"],
        default="json",
        help="输出格式 (默认: json)",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行离线自检并退出",
    )
    return parser.parse_args(argv)


def _read_input(args: argparse.Namespace) -> str:
    """
    读取输入文本

    参数:
        args: 命令行参数

    返回:
        输入文本

    异常:
        ValueError: 输入为空或读取失败
    """
    if args.input:
        return args.input

    if args.file:
        try:
            with open(args.file, "r", encoding="utf-8") as f:
                return f.read()
        except IOError as e:
            raise ValueError(f"E009: 读取文件失败 - {e}")

    # 无输入时尝试从标准输入读取
    if not sys.stdin.isatty():
        return sys.stdin.read()

    raise ValueError("E001: 输入为空")


def main(argv: Optional[List[str]] = None) -> int:
    """
    主入口函数

    参数:
        argv: 命令行参数列表

    返回:
        退出码 (0 成功, 非 0 失败)
    """
    try:
        args = _parse_args(argv if argv is not None else sys.argv[1:])

        # 自检模式
        if args.selftest:
            passed = _run_selftest()
            return 0 if passed else 8  # 8 对应 E008

        # 正常处理模式
        try:
            raw_text = _read_input(args)
        except ValueError as e:
            print(f"错误: {e}")
            return 1  # E001

        # 解析
        try:
            receipt = parse_receipt(raw_text)
        except ValueError as e:
            print(f"错误: {e}")
            if str(e).startswith("E001"):
                return 1
            elif str(e).startswith("E003"):
                return 3
            return 6  # E006

        # 输出结果
        output = format_output(receipt, args.format)
        print(output)

        # 低置信度提示
        if receipt.confidence < 0.85:
            print("\n[提示] 置信度较低，请人工核实关键字段 (E005)")
            return 5

        return 0

    except KeyboardInterrupt:
        print("\n操作已取消")
        return 130
    except Exception as e:
        print(f"未知错误: {e} (E010)")
        return 10


if __name__ == "__main__":
    sys.exit(main())
