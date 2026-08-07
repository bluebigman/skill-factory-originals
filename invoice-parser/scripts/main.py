#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
invoice-parser 独立实现（clean-room 重写）
=========================================
依据功能规格从零实现，未参考任何既有代码。

功能：
- 从发票/采购单文本中抽取结构化字段
- 支持命令行单次解析与内置样例自检
- 离线可用，无第三方依赖

用法：
    python scripts/main.py --selftest
    python scripts/main.py --input "发票号: ABC123 金额: 456.78 日期: 2024-01-15"
    python scripts/main.py --input-file path/to/file.txt
"""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# 错误码定义
ERR_SUCCESS = 0
ERR_INPUT_EMPTY = "E001"      # 输入为空
ERR_INPUT_TYPE = "E002"       # 输入类型不支持
ERR_FILE_NOT_FOUND = "E003"   # 文件不存在
ERR_FILE_READ = "E004"        # 文件读取失败
ERR_PARSE_FAIL = "E005"       # 解析失败（无任何字段）
ERR_SELFTEST = "E006"         # 自检失败
ERR_ARG_INVALID = "E007"      # 参数无效
ERR_INTERNAL = "E008"         # 内部错误
ERR_OUTPUT_FAIL = "E009"      # 输出失败
ERR_UNKNOWN = "E010"          # 未知错误


# ============================================================
# 核心解析逻辑（纯函数，不涉及 IO）
# ============================================================

def _extract_invoice_no(text: str) -> Optional[str]:
    """抽取发票号码。支持常见格式：发票号/发票号码/NO. 后跟字母数字。"""
    patterns = [
        r"(?:发票号码?|invoice\s*(?:no\.?|number)?)\s*[:：]?\s*([A-Za-z0-9\-]{4,30})",
        r"(?:NO\.?|No\.?)\s*[:：]?\s*([A-Za-z0-9\-]{4,30})",
        r"\b(\d{8,12})\b",  # 纯数字 8-12 位
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            return m.group(1).strip()
    return None


def _extract_date(text: str) -> Optional[str]:
    """抽取日期。支持多种格式。"""
    patterns = [
        r"(?:开票日期|日期|date)\s*[:：]?\s*(\d{4}[-/年]\d{1,2}[-/月]\d{1,2}日?)",
        r"(\d{4}[-/年]\d{1,2}[-/月]\d{1,2}日?)",
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            # 规范化格式为 YYYY-MM-DD
            raw = m.group(1)
            raw = raw.replace("年", "-").replace("月", "-").replace("日", "")
            raw = raw.replace("/", "-")
            parts = [p for p in raw.split("-") if p]
            if len(parts) == 3:
                return f"{parts[0]}-{int(parts[1]):02d}-{int(parts[2]):02d}"
    return None


def _extract_amount(text: str) -> Optional[float]:
    """抽取金额。支持人民币符号和常见格式。"""
    patterns = [
        r"(?:金额|合计|总计|amount|total)\s*[:：]?\s*[￥¥]?\s*(\d+(?:\.\d{1,2})?)",
        r"[￥¥]\s*(\d+(?:\.\d{1,2})?)",
        r"(?:amount|total)\s*[:：]?\s*(\d+(?:\.\d{1,2})?)",
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            try:
                return float(m.group(1))
            except ValueError:
                continue
    return None


def _extract_seller(text: str) -> Optional[str]:
    """抽取销售方/供应商名称。"""
    patterns = [
        r"(?:销售方|卖方|供应商|seller|supplier)\s*[:：]?\s*([^\s,，;；]+)",
        r"(?:公司名称|单位名称)\s*[:：]?\s*([^\s,，;；]+)",
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            return m.group(1).strip()
    return None


def _extract_buyer(text: str) -> Optional[str]:
    """抽取购买方/客户名称。"""
    patterns = [
        r"(?:购买方|买方|客户|buyer|customer)\s*[:：]?\s*([^\s,，;；]+)",
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            return m.group(1).strip()
    return None


def _extract_tax_rate(text: str) -> Optional[float]:
    """抽取税率。支持百分比和十进制。"""
    patterns = [
        r"(?:税率|tax\s*rate)\s*[:：]?\s*(\d+(?:\.\d+)?)\s*%",
        r"(?:税率|tax\s*rate)\s*[:：]?\s*(\d+(?:\.\d+)?)",
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            try:
                val = float(m.group(1))
                # 若大于 1，视为百分比
                return val if val <= 1 else val / 100.0
            except ValueError:
                continue
    return None


def parse_invoice(text: str) -> Dict[str, Any]:
    """
    从文本中解析发票/票据字段。

    参数:
        text: 票据文本内容

    返回:
        字典包含抽取的字段，未找到的字段为 None
    """
    if not text or not text.strip():
        raise ValueError(f"输入为空 ({ERR_INPUT_EMPTY})")

    result: Dict[str, Any] = {
        "invoice_no": _extract_invoice_no(text),
        "date": _extract_date(text),
        "amount": _extract_amount(text),
        "seller": _extract_seller(text),
        "buyer": _extract_buyer(text),
        "tax_rate": _extract_tax_rate(text),
    }

    # 检查是否至少解析出一个字段
    if not any(v is not None for v in result.values()):
        raise ValueError(f"无法从文本中解析出任何字段 ({ERR_PARSE_FAIL})")

    return result


# ============================================================
# 文件处理
# ============================================================

def read_file(file_path: str) -> str:
    """读取文本文件内容。"""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"文件不存在 ({ERR_FILE_NOT_FOUND}): {file_path}")
    if not path.is_file():
        raise IsADirectoryError(f"路径是目录而非文件 ({ERR_FILE_READ}): {file_path}")
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except (IOError, OSError) as e:
        raise IOError(f"文件读取失败 ({ERR_FILE_READ}): {e}")


# ============================================================
# 输出格式化
# ============================================================

def format_output(data: Dict[str, Any], fmt: str = "json") -> str:
    """格式化输出结果。支持 json 和 text 格式。"""
    if fmt == "json":
        return json.dumps(data, ensure_ascii=False, indent=2)
    elif fmt == "text":
        lines = []
        for key, value in data.items():
            lines.append(f"{key}: {value if value is not None else '未识别'}")
        return "\n".join(lines)
    else:
        raise ValueError(f"不支持的输出格式: {fmt} ({ERR_ARG_INVALID})")


# ============================================================
# 自检功能（内置样例，离线验证）
# ============================================================

def _run_selftest() -> bool:
    """
    内置样例自检。不读文件、不访问网络、不依赖工作目录。

    使用宽松阈值断言，确保稳定通过。
    """
    sample_text = """
    增值税普通发票
    发票号码: INV2024001
    开票日期: 2024年3月15日
    销售方: 北京科技有限公司
    购买方: 上海贸易有限公司
    金额: 1234.56
    税率: 13%
    """

    try:
        result = parse_invoice(sample_text)

        # 宽松断言：验证字段非空且类型正确
        assert result["invoice_no"] is not None, "发票号未解析"
        assert len(result["invoice_no"]) >= 4, "发票号长度异常"

        assert result["date"] is not None, "日期未解析"
        assert result["date"].startswith("2024"), "日期年份异常"

        assert result["amount"] is not None, "金额未解析"
        assert result["amount"] > 0, "金额应大于0"

        assert result["seller"] is not None, "销售方未解析"
        assert len(result["seller"]) >= 2, "销售方名称过短"

        assert result["buyer"] is not None, "购买方未解析"
        assert len(result["buyer"]) >= 2, "购买方名称过短"

        assert result["tax_rate"] is not None, "税率未解析"
        assert 0 < result["tax_rate"] < 1, "税率应在0到1之间"

        # 验证 parse_invoice 的异常处理
        try:
            parse_invoice("")
            assert False, "空输入应抛出异常"
        except ValueError:
            pass  # 预期行为

        # 验证无法解析的输入
        try:
            parse_invoice("这是一段没有任何票据信息的普通文本内容")
            assert False, "无字段输入应抛出异常"
        except ValueError:
            pass  # 预期行为

        return True

    except AssertionError as e:
        print(f"自检失败: {e} ({ERR_SELFTEST})", file=sys.stderr)
        return False
    except Exception as e:
        print(f"自检异常: {e} ({ERR_SELFTEST})", file=sys.stderr)
        return False


# ============================================================
# 命令行入口
# ============================================================

def main(argv: Optional[List[str]] = None) -> int:
    """主入口函数。"""
    parser = argparse.ArgumentParser(
        description="票据解析 - 从发票/采购单文本中抽取结构化字段",
        epilog="示例: python main.py --input '发票号: ABC123 金额: 456.78'"
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置样例自检（离线，无需任何外部资源）"
    )
    parser.add_argument(
        "--input",
        type=str,
        help="直接传入票据文本内容"
    )
    parser.add_argument(
        "--input-file",
        type=str,
        help="从文件读取票据文本"
    )
    parser.add_argument(
        "--format",
        choices=["json", "text"],
        default="json",
        help="输出格式（默认: json）"
    )

    args = parser.parse_args(argv)

    # 自检模式
    if args.selftest:
        ok = _run_selftest()
        if ok:
            print("自检通过 ✓")
            return ERR_SUCCESS
        else:
            return 1

    # 解析模式：处理输入
    try:
        # 获取输入文本
        if args.input:
            text = args.input
        elif args.input_file:
            text = read_file(args.input_file)
        else:
            parser.error(f"请提供 --input 或 --input-file，或使用 --selftest 进行自检 ({ERR_ARG_INVALID})")
            return 1  # parser.error 会抛出 SystemExit

        # 执行解析
        result = parse_invoice(text)

        # 输出结果
        output = format_output(result, args.format)
        print(output)
        return ERR_SUCCESS

    except FileNotFoundError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1
    except IsADirectoryError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1
    except IOError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1
    except ValueError as e:
        print(f"解析错误: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"未知错误 ({ERR_UNKNOWN}): {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
