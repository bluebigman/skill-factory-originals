#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
chronic — 自然语言日期解析 Skill (独立实现)

本脚本依据功能规格独立实现，不包含任何既有代码。
支持中文/英文日期描述解析、相对日期、模糊日期、批量处理。
"""

import re
import sys
import json
from datetime import datetime, timedelta

# 错误码定义
ERROR_CODES = {
    "INVALID_INPUT": "E001",      # 输入不是字符串
    "EMPTY_INPUT": "E002",        # 输入为空
    "INPUT_TOO_LONG": "E003",     # 输入超过200字符
    "BATCH_TOO_LARGE": "E004",    # 批量超过100条
    "PARSE_FAILED": "E005",       # 解析失败
    "INVALID_BATCH": "E006",      # 批量输入不是列表
    "INVALID_DATE": "E007",       # 日期无效
    "INTERNAL_ERROR": "E008",     # 内部错误
    "INVALID_FORMAT": "E009",     # 输出格式错误
    "UNKNOWN": "E010"             # 未知错误
}


class ChronicError(Exception):
    """自定义异常类"""
    def __init__(self, code, message):
        self.code = code
        self.message = message
        super().__init__(f"[{code}] {message}")


def _safe_str(text):
    """安全转换为字符串"""
    if not isinstance(text, str):
        raise ChronicError(ERROR_CODES["INVALID_INPUT"], "输入必须是字符串")
    return text.strip()


def _check_length(text):
    """检查输入长度"""
    if len(text) > 200:
        raise ChronicError(ERROR_CODES["INPUT_TOO_LONG"], "输入超过200字符限制")
    if not text:
        raise ChronicError(ERROR_CODES["EMPTY_INPUT"], "输入为空")


def _check_batch(items):
    """检查批量输入"""
    if not isinstance(items, list):
        raise ChronicError(ERROR_CODES["INVALID_BATCH"], "批量输入必须是列表")
    if len(items) > 100:
        raise ChronicError(ERROR_CODES["BATCH_TOO_LARGE"], "批量输入超过100条限制")


def _normalize_number_cn(num_str):
    """中文数字转阿拉伯数字"""
    cn_nums = {'零': 0, '一': 1, '二': 2, '两': 2, '三': 3, '四': 4,
               '五': 5, '六': 6, '七': 7, '八': 8, '九': 9}
    if num_str in cn_nums:
        return cn_nums[num_str]
    try:
        return int(num_str)
    except ValueError:
        return None


def _normalize_number_en(num_str):
    """英文数字单词转阿拉伯数字"""
    en_nums = {
        'zero': 0, 'one': 1, 'two': 2, 'three': 3, 'four': 4,
        'five': 5, 'six': 6, 'seven': 7, 'eight': 8, 'nine': 9,
        'ten': 10, 'eleven': 11, 'twelve': 12, 'thirteen': 13,
        'fourteen': 14, 'fifteen': 15, 'sixteen': 16, 'seventeen': 17,
        'eighteen': 18, 'nineteen': 19, 'twenty': 20,
        'thirty': 30, 'forty': 40, 'fifty': 50, 'sixty': 60,
        'seventy': 70, 'eighty': 80, 'ninety': 90, 'hundred': 100
    }
    num_str = num_str.lower().strip()
    if num_str in en_nums:
        return en_nums[num_str]
    try:
        return int(num_str)
    except ValueError:
        return None


def _parse_absolute_cn(text, now):
    """解析中文绝对日期，如：2024年3月15日"""
    patterns = [
        # 2024年3月15日
        r'(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日?',
        # 2024-03-15
        r'(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})',
        # 2024/3/15
        r'(\d{4})/(\d{1,2})/(\d{1,2})',
    ]
    for pat in patterns:
        m = re.search(pat, text)
        if m:
            try:
                year, month, day = int(m.group(1)), int(m.group(2)), int(m.group(3))
                # 验证日期有效性
                dt = datetime(year, month, day)
                return dt, 1.0
            except ValueError:
                raise ChronicError(ERROR_CODES["INVALID_DATE"], f"无效日期: {m.group(0)}")
    return None, 0.0


def _parse_relative_cn(text, now):
    """解析中文相对日期，如：三天后、下周、下个月"""
    # 三天后 / 三日前
    m = re.search(r'([零一二两三四五六七八九十\d]+)\s*天?\s*(后|前)', text)
    if m:
        num = _normalize_number_cn(m.group(1))
        if num is not None:
            delta = timedelta(days=num)
            dt = now + delta if m.group(2) == '后' else now - delta
            return dt, 0.85
    # 三小时后
    m = re.search(r'([零一二两三四五六七八九十\d]+)\s*个?\s*小时\s*(后|前)', text)
    if m:
        num = _normalize_number_cn(m.group(1))
        if num is not None:
            delta = timedelta(hours=num)
            dt = now + delta if m.group(2) == '后' else now - delta
            return dt, 0.85
    # 下周
    if '下周' in text:
        days_ahead = 7 - now.weekday() + 7  # 下周一
        dt = now + timedelta(days=days_ahead)
        return dt, 0.75
    # 本周
    if '本周' in text:
        days_ahead = 7 - now.weekday()  # 本周日
        dt = now + timedelta(days=days_ahead)
        return dt, 0.75
    # 下个月
    if '下个月' in text:
        if now.month == 12:
            dt = datetime(now.year + 1, 1, 1)
        else:
            dt = datetime(now.year, now.month + 1, 1)
        return dt, 0.75
    # 明天 / 后天
    if '后天' in text:
        return now + timedelta(days=2), 1.0
    if '明天' in text:
        return now + timedelta(days=1), 1.0
    # 昨天 / 前天
    if '前天' in text:
        return now - timedelta(days=2), 1.0
    if '昨天' in text:
        return now - timedelta(days=1), 1.0
    return None, 0.0


def _parse_absolute_en(text, now):
    """解析英文绝对日期，如：March 15, 2024"""
    months_en = {
        'january': 1, 'february': 2, 'march': 3, 'april': 4,
        'may': 5, 'june': 6, 'july': 7, 'august': 8,
        'september': 9, 'october': 10, 'november': 11, 'december': 12
    }
    # March 15, 2024
    m = re.search(r'([A-Za-z]+)\s+(\d{1,2})(?:st|nd|rd|th)?,\s*(\d{4})', text)
    if m:
        month_name = m.group(1).lower()
        if month_name in months_en:
            try:
                dt = datetime(int(m.group(3)), months_en[month_name], int(m.group(2)))
                return dt, 1.0
            except ValueError:
                raise ChronicError(ERROR_CODES["INVALID_DATE"], f"无效日期: {m.group(0)}")
    # 15 March 2024
    m = re.search(r'(\d{1,2})(?:st|nd|rd|th)?\s+([A-Za-z]+)\s+(\d{4})', text)
    if m:
        month_name = m.group(2).lower()
        if month_name in months_en:
            try:
                dt = datetime(int(m.group(3)), months_en[month_name], int(m.group(1)))
                return dt, 1.0
            except ValueError:
                raise ChronicError(ERROR_CODES["INVALID_DATE"], f"无效日期: {m.group(0)}")
    return None, 0.0


def _parse_relative_en(text, now):
    """解析英文相对日期，如：three days later"""
    # three days later / ago (支持数字和英文单词)
    m = re.search(r'([a-zA-Z]+|\d+)\s+(day|days|hour|hours)\s+(later|ago)', text)
    if m:
        num = _normalize_number_en(m.group(1))
        if num is not None:
            if m.group(2) in ('day', 'days'):
                delta = timedelta(days=num)
            else:
                delta = timedelta(hours=num)
            dt = now + delta if m.group(3) == 'later' else now - delta
            return dt, 0.85
    # tomorrow / yesterday
    if 'tomorrow' in text:
        return now + timedelta(days=1), 1.0
    if 'yesterday' in text:
        return now - timedelta(days=1), 1.0
    # next week
    if 'next week' in text:
        days_ahead = 7 - now.weekday() + 7
        return now + timedelta(days=days_ahead), 0.75
    # next month
    if 'next month' in text:
        if now.month == 12:
            dt = datetime(now.year + 1, 1, 1)
        else:
            dt = datetime(now.year, now.month + 1, 1)
        return dt, 0.75
    return None, 0.0


def _parse_fuzzy_cn(text, now):
    """解析中文模糊日期，如：下个月初"""
    # 下个月初
    if '下个月初' in text or '下月初' in text:
        if now.month == 12:
            dt = datetime(now.year + 1, 1, 1)
        else:
            dt = datetime(now.year, now.month + 1, 1)
        return dt, 0.6
    # 下个月末
    if '下个月末' in text or '下月末' in text:
        if now.month == 12:
            dt = datetime(now.year + 1, 1, 28)
        else:
            next_month = now.month + 1
            if next_month == 2:
                dt = datetime(now.year, 2, 28)
            elif next_month in [4, 6, 9, 11]:
                dt = datetime(now.year, next_month, 30)
            else:
                dt = datetime(now.year, next_month, 31)
        return dt, 0.6
    # 本月初
    if '本月初' in text or '月初' in text:
        return datetime(now.year, now.month, 1), 0.6
    # 本月底
    if '本月底' in text or '月底' in text:
        if now.month == 2:
            dt = datetime(now.year, 2, 28)
        elif now.month in [4, 6, 9, 11]:
            dt = datetime(now.year, now.month, 30)
        else:
            dt = datetime(now.year, now.month, 31)
        return dt, 0.6
    return None, 0.0


def _parse_single(text, now=None):
    """解析单条日期描述"""
    if now is None:
        now = datetime.now()

    text = _safe_str(text)
    _check_length(text)

    warnings = []

    # 尝试各种解析策略
    dt, conf = _parse_absolute_cn(text, now)
    if dt:
        return dt, conf, warnings

    dt, conf = _parse_absolute_en(text, now)
    if dt:
        return dt, conf, warnings

    dt, conf = _parse_relative_cn(text, now)
    if dt:
        return dt, conf, warnings

    dt, conf = _parse_relative_en(text, now)
    if dt:
        return dt, conf, warnings

    dt, conf = _parse_fuzzy_cn(text, now)
    if dt:
        return dt, conf, warnings

    # 无法解析
    raise ChronicError(ERROR_CODES["PARSE_FAILED"], f"无法解析日期描述: {text}")


def _format_output(dt, confidence, original, warnings):
    """格式化输出结果"""
    return {
        "parsed": True,
        "value": dt.strftime("%Y-%m-%dT%H:%M:%S"),
        "confidence": round(confidence, 2),
        "original": original,
        "warnings": warnings
    }


def parse_date(text, now=None):
    """解析单个日期描述"""
    try:
        dt, conf, warnings = _parse_single(text, now)
        return _format_output(dt, conf, text.strip(), warnings)
    except ChronicError:
        return {
            "parsed": False,
            "value": None,
            "confidence": 0.0,
            "original": text if isinstance(text, str) else str(text),
            "warnings": ["解析失败"]
        }


def parse_batch(items, now=None):
    """批量解析日期描述"""
    _check_batch(items)
    results = []
    truncated = False

    for item in items[:100]:  # 最多处理100条
        results.append(parse_date(item, now))

    if len(items) > 100:
        truncated = True

    return {
        "results": results,
        "truncated": truncated,
        "warning": "输入超过100条，已截断" if truncated else None
    }


def selftest():
    """内置自检函数，使用硬编码样例数据"""
    print("=== chronic selftest ===")

    # 固定参考时间点（避免依赖当前时间）
    ref_time = datetime(2024, 3, 15, 12, 0, 0)

    # 测试用例： (输入, 期望有解析结果, 置信度下限)
    test_cases = [
        ("2024年3月15日", True, 0.9),
        ("2024-03-15", True, 0.9),
        ("March 15, 2024", True, 0.9),
        ("三天后", True, 0.8),
        ("明天", True, 0.9),
        ("下个月初", True, 0.5),
        ("tomorrow", True, 0.9),
        ("three days later", True, 0.8),
        ("无效日期测试", False, 0.0),
        ("", False, 0.0),
    ]

    all_passed = True
    for input_text, expect_parsed, min_conf in test_cases:
        result = parse_date(input_text, ref_time)
        if result["parsed"] != expect_parsed:
            print(f"FAIL: '{input_text}' parsed={result['parsed']}, expected={expect_parsed}")
            all_passed = False
            continue
        if result["parsed"] and result["confidence"] < min_conf:
            print(f"FAIL: '{input_text}' confidence={result['confidence']}, expected >= {min_conf}")
            all_passed = False
            continue
        if result["parsed"]:
            # 验证输出格式
            if not re.match(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}', result["value"]):
                print(f"FAIL: '{input_text}' value格式错误: {result['value']}")
                all_passed = False
                continue
        print(f"PASS: '{input_text}' -> {result['value']} (conf={result['confidence']})")

    # 批量测试
    batch_input = ["明天", "2024年1月1日", "后天"]
    batch_result = parse_batch(batch_input, ref_time)
    if len(batch_result["results"]) != 3:
        print(f"FAIL: 批量结果数量错误: {len(batch_result['results'])}")
        all_passed = False
    else:
        print(f"PASS: 批量解析 {len(batch_result['results'])} 条")

    # 长度限制测试
    long_input = "天" * 201
    result = parse_date(long_input, ref_time)
    if result["parsed"]:
        print("FAIL: 超长输入应解析失败")
        all_passed = False
    else:
        print("PASS: 超长输入正确处理")

    # 批量限制测试
    too_many = [str(i) for i in range(101)]
    try:
        batch_result = parse_batch(too_many, ref_time)
        if not batch_result["truncated"]:
            print("FAIL: 批量应截断")
            all_passed = False
        else:
            print("PASS: 批量截断处理")
    except ChronicError as e:
        print(f"FAIL: 批量应截断而非报错: {e.code}")
        all_passed = False

    print("=== selftest " + ("PASSED" if all_passed else "FAILED") + " ===")
    return all_passed


def main():
    """命令行入口"""
    args = sys.argv[1:]

    if "--selftest" in args:
        success = selftest()
        sys.exit(0 if success else 1)

    if not args:
        print("用法: python main.py [--selftest] [日期描述]")
        print("示例:")
        print("  python main.py --selftest")
        print("  python main.py \"明天\"")
        print("  python main.py \"2024年3月15日\"")
        sys.exit(0)

    # 单个输入
    if len(args) == 1:
        result = parse_date(args[0])
        print(json.dumps(result, ensure_ascii=False, indent=2))
        sys.exit(0)

    # 多个输入作为批量
    batch_result = parse_batch(args)
    print(json.dumps(batch_result, ensure_ascii=False, indent=2))
    sys.exit(0)


if __name__ == "__main__":
    main()
