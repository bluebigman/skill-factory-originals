#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
chronic — 自然语言日期解析工具（clean-room 独立实现）
=====================================================
依据功能规格独立开发，不参考任何既有实现。

能力：
  - 相对日期解析（如"三天后"）
  - 绝对日期解析（如"2024年3月15日"）
  - 模糊日期解析（上/中/下旬）
  - 星期/节日识别
  - 批量处理
  - 时间范围提取

用法示例：
  python scripts/main.py "三天后"
  python scripts/main.py "2024年3月15日"
  python scripts/main.py "下月中旬"
  python scripts/main.py --batch "明天" "下周一" "国庆节"
  python scripts/main.py --selftest

错误码：
  E001 参数缺失
  E002 无法解析的日期文本
  E003 非法日期值（如2月30日）
  E004 批量输入为空
  E005 未知命令
  E006 内部逻辑错误
  E007 不支持的格式
  E008 无效的星期名
  E009 无效的节日名
  E010 无效的偏移量
"""

import argparse
import calendar
import datetime
import json
import re
import sys
from typing import Any, Dict, List, Optional, Tuple, Union


# ============================================================
# 常量定义
# ============================================================

# 月份中文映射
MONTH_CN = {
    "一月": 1, "1月": 1, "01月": 1,
    "二月": 2, "2月": 2, "02月": 2,
    "三月": 3, "3月": 3, "03月": 3,
    "四月": 4, "4月": 4, "04月": 4,
    "五月": 5, "5月": 5, "05月": 5,
    "六月": 6, "6月": 6, "06月": 6,
    "七月": 7, "7月": 7, "07月": 7,
    "八月": 8, "8月": 8, "08月": 8,
    "九月": 9, "9月": 9, "09月": 9,
    "十月": 10, "10月": 10,
    "十一月": 11, "11月": 11,
    "十二月": 12, "12月": 12,
}

# 星期中文映射（周一=0 ... 周日=6）
WEEKDAY_CN = {
    "周一": 0, "星期一": 0, "礼拜一": 0, "周1": 0,
    "周二": 1, "星期二": 1, "礼拜二": 1, "周2": 1,
    "周三": 2, "星期三": 2, "礼拜三": 2, "周3": 2,
    "周四": 3, "星期四": 3, "礼拜四": 3, "周4": 3,
    "周五": 4, "星期五": 4, "礼拜五": 4, "周5": 4,
    "周六": 5, "星期六": 5, "礼拜六": 5, "周6": 5,
    "周日": 6, "星期日": 6, "星期天": 6, "礼拜日": 6, "礼拜天": 6, "周天": 6, "周7": 6,
}

# 节日映射（月, 日 -> 名称）
HOLIDAYS = {
    (1, 1): "元旦",
    (2, 14): "情人节",
    (3, 8): "妇女节",
    (3, 12): "植树节",
    (4, 1): "愚人节",
    (5, 1): "劳动节",
    (5, 4): "青年节",
    (6, 1): "儿童节",
    (7, 1): "建党节",
    (8, 1): "建军节",
    (9, 10): "教师节",
    (10, 1): "国庆节",
    (12, 25): "圣诞节",
}

# 节日名称反向映射
HOLIDAY_NAMES = {name: (m, d) for (m, d), name in HOLIDAYS.items()}

# 数字中文映射
CN_NUM = {
    "零": 0, "〇": 0, "一": 1, "二": 2, "两": 2, "三": 3,
    "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9,
    "十": 10, "十一": 11, "十二": 12, "十三": 13, "十四": 14,
    "十五": 15, "十六": 16, "十七": 17, "十八": 18, "十九": 19,
    "二十": 20, "二十一": 21, "二十二": 22, "二十三": 23,
    "二十四": 24, "二十五": 25, "二十六": 26, "二十七": 27,
    "二十八": 28, "二十九": 29, "三十": 30, "三十一": 31,
}

# 数字中文简写映射
CN_NUM_SHORT = {
    "零": 0, "一": 1, "二": 2, "两": 2, "三": 3,
    "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9,
    "十": 10,
}

# 时段中文映射
PERIOD_CN = {
    "上旬": (1, 10),
    "中旬": (11, 20),
    "下旬": (21, 31),
}

# 相对日期关键词
RELATIVE_PATTERNS = [
    (re.compile(r"^今天$|^今日$"), 0),
    (re.compile(r"^明天$|^明日$"), 1),
    (re.compile(r"^后天$"), 2),
    (re.compile(r"^昨天$|^昨日$"), -1),
    (re.compile(r"^前天$"), -2),
    (re.compile(r"^大前天$"), -3),
]

# 偏移量模式：如 "三天后"、"五日前"
OFFSET_PATTERN = re.compile(
    r"^(?P<num>[\d一二两三四五六七八九十]+)\s*(?P<unit>天|日|周|星期|个月|月|年)\s*(?P<dir>后|前|之后|以前)$"
)

# 绝对日期模式：如 "2024年3月15日"
ABSOLUTE_PATTERN = re.compile(
    r"^(?P<year>\d{4})\s*年\s*(?P<month>\d{1,2})\s*月\s*(?P<day>\d{1,2})\s*日?$"
)

# 月日模式：如 "3月15日"
MONTH_DAY_PATTERN = re.compile(
    r"^(?P<month>\d{1,2})\s*月\s*(?P<day>\d{1,2})\s*日?$"
)

# 范围模式：如 "从周一到周五"
RANGE_PATTERN = re.compile(
    r"^从?\s*(?P<start>.+?)\s*到\s*(?P<end>.+?)\s*$"
)

# 批量分隔符
BATCH_SPLIT_PATTERN = re.compile(r"[,，;；、]+")


# ============================================================
# 工具函数
# ============================================================

def _cn_to_int(text: str) -> Optional[int]:
    """中文数字转整数，支持 0-99。"""
    text = text.strip()
    if not text:
        return None
    # 纯阿拉伯数字
    if text.isdigit():
        return int(text)
    # 中文数字
    if text in CN_NUM:
        return CN_NUM[text]
    # 组合形式如 "二十三"
    if "十" in text:
        parts = text.split("十")
        tens = CN_NUM_SHORT.get(parts[0], 0) if parts[0] else 0
        ones = CN_NUM_SHORT.get(parts[1], 0) if len(parts) > 1 and parts[1] else 0
        if tens == 0 and parts[0] == "":
            tens = 1  # "十" = 10
        return tens * 10 + ones
    # 单个数字
    if text in CN_NUM_SHORT:
        return CN_NUM_SHORT[text]
    return None


def _is_valid_date(year: int, month: int, day: int) -> bool:
    """检查日期是否合法。"""
    try:
        datetime.date(year, month, day)
        return True
    except ValueError:
        return False


def _date_to_str(d: datetime.date) -> str:
    """日期转字符串 YYYY-MM-DD。"""
    return d.strftime("%Y-%m-%d")


def _today() -> datetime.date:
    """获取今天日期（便于测试替换）。"""
    return datetime.date.today()


def _build_result(
    date: Optional[datetime.date] = None,
    date_range: Optional[Tuple[datetime.date, datetime.date]] = None,
    confidence: float = 0.0,
    holiday: Optional[str] = None,
) -> Dict[str, Any]:
    """构建标准输出结构。"""
    result: Dict[str, Any] = {}
    if date is not None:
        result["date"] = _date_to_str(date)
    if date_range is not None:
        result["date_range"] = {
            "start": _date_to_str(date_range[0]),
            "end": _date_to_str(date_range[1]),
        }
    result["confidence"] = confidence
    if holiday:
        result["holiday"] = holiday
    return result


# ============================================================
# 核心解析逻辑
# ============================================================

def parse_absolute(text: str, ref_date: datetime.date) -> Optional[Dict[str, Any]]:
    """解析绝对日期，如 '2024年3月15日'。"""
    m = ABSOLUTE_PATTERN.match(text)
    if m:
        year = int(m.group("year"))
        month = int(m.group("month"))
        day = int(m.group("day"))
        if not _is_valid_date(year, month, day):
            raise ValueError("E003")
        d = datetime.date(year, month, day)
        holiday = HOLIDAYS.get((month, day))
        return _build_result(date=d, confidence=1.0, holiday=holiday)

    m = MONTH_DAY_PATTERN.match(text)
    if m:
        month = int(m.group("month"))
        day = int(m.group("day"))
        year = ref_date.year
        # 如果月份已过，视为明年
        if (month, day) < (ref_date.month, ref_date.day):
            year += 1
        if not _is_valid_date(year, month, day):
            raise ValueError("E003")
        d = datetime.date(year, month, day)
        holiday = HOLIDAYS.get((month, day))
        return _build_result(date=d, confidence=0.9, holiday=holiday)

    return None


def parse_relative(text: str, ref_date: datetime.date) -> Optional[Dict[str, Any]]:
    """解析相对日期，如 '三天后'。"""
    # 固定关键词
    for pattern, delta in RELATIVE_PATTERNS:
        if pattern.match(text):
            d = ref_date + datetime.timedelta(days=delta)
            return _build_result(date=d, confidence=0.95)

    # 偏移量模式
    m = OFFSET_PATTERN.match(text)
    if m:
        num_text = m.group("num")
        unit = m.group("unit")
        direction = m.group("dir")

        num = _cn_to_int(num_text)
        if num is None or num <= 0:
            raise ValueError("E010")

        # 计算偏移天数
        if unit in ("天", "日"):
            delta_days = num
        elif unit in ("周", "星期"):
            delta_days = num * 7
        elif unit == "个月":
            # 月份偏移（按日历月）
            sign = -1 if "前" in direction else 1
            total_months = ref_date.year * 12 + (ref_date.month - 1) + sign * num
            new_year = total_months // 12
            new_month = total_months % 12 + 1
            # 处理月末（如1月31日 + 1个月）
            last_day = calendar.monthrange(new_year, new_month)[1]
            new_day = min(ref_date.day, last_day)
            d = datetime.date(new_year, new_month, new_day)
            return _build_result(date=d, confidence=0.9)
        elif unit == "月":
            delta_days = num * 30  # 近似
        elif unit == "年":
            sign = -1 if "前" in direction else 1
            new_year = ref_date.year + sign * num
            # 处理闰日
            try:
                d = datetime.date(new_year, ref_date.month, ref_date.day)
            except ValueError:
                d = datetime.date(new_year, ref_date.month, 28)
            return _build_result(date=d, confidence=0.9)
        else:
            raise ValueError("E007")

        sign = -1 if "前" in direction else 1
        d = ref_date + datetime.timedelta(days=sign * delta_days)
        return _build_result(date=d, confidence=0.95)

    return None


def parse_weekday(text: str, ref_date: datetime.date) -> Optional[Dict[str, Any]]:
    """解析星期，如 '下周一'、'周五'。"""
    # 模式：可选前缀 + 星期名
    m = re.match(r"^(?P<prefix>这|本|下|上|下个|上个)?\s*(?P<weekday>周[一二三四五六日天]|星期[一二三四五六日天]|礼拜[一二三四五六日天]|周[1-7])$", text)
    if not m:
        return None

    prefix = m.group("prefix") or ""
    weekday_text = m.group("weekday")

    if weekday_text not in WEEKDAY_CN:
        raise ValueError("E008")

    target_weekday = WEEKDAY_CN[weekday_text]
    current_weekday = ref_date.weekday()  # 周一=0

    # 计算偏移
    if prefix in ("这", "本", ""):
        delta = (target_weekday - current_weekday) % 7
    elif prefix == "下":
        delta = (target_weekday - current_weekday) % 7 + 7
    elif prefix == "下个":
        delta = (target_weekday - current_weekday) % 7 + 7
    elif prefix == "上":
        delta = (target_weekday - current_weekday) % 7 - 7
    elif prefix == "上个":
        delta = (target_weekday - current_weekday) % 7 - 7
    else:
        raise ValueError("E008")

    d = ref_date + datetime.timedelta(days=delta)
    return _build_result(date=d, confidence=0.85)


def parse_holiday(text: str, ref_date: datetime.date) -> Optional[Dict[str, Any]]:
    """解析节日，如 '国庆节'。"""
    if text not in HOLIDAY_NAMES:
        return None

    month, day = HOLIDAY_NAMES[text]
    year = ref_date.year
    # 如果节日已过，视为明年
    if (month, day) < (ref_date.month, ref_date.day):
        year += 1
    if not _is_valid_date(year, month, day):
        raise ValueError("E003")
    d = datetime.date(year, month, day)
    return _build_result(date=d, confidence=0.85, holiday=text)


def parse_period(text: str, ref_date: datetime.date) -> Optional[Dict[str, Any]]:
    """解析模糊时段，如 '下月中旬'。"""
    # 模式：可选前缀 + 时段
    m = re.match(r"^(?P<prefix>这|本|下|上|下个|上个)?\s*(?P<period>上旬|中旬|下旬)$", text)
    if not m:
        return None

    prefix = m.group("prefix") or ""
    period = m.group("period")

    if period not in PERIOD_CN:
        raise ValueError("E007")

    start_day, end_day = PERIOD_CN[period]

    # 计算月份偏移
    if prefix in ("这", "本", ""):
        month_offset = 0
    elif prefix == "下":
        month_offset = 1
    elif prefix == "下个":
        month_offset = 1
    elif prefix == "上":
        month_offset = -1
    elif prefix == "上个":
        month_offset = -1
    else:
        raise ValueError("E007")

    total_months = ref_date.year * 12 + (ref_date.month - 1) + month_offset
    year = total_months // 12
    month = total_months % 12 + 1

    # 处理月末（下旬可能只有28/29/30/31天）
    last_day = calendar.monthrange(year, month)[1]
    actual_end_day = min(end_day, last_day)

    start = datetime.date(year, month, start_day)
    end = datetime.date(year, month, actual_end_day)
    return _build_result(date_range=(start, end), confidence=0.7)


def parse_range(text: str, ref_date: datetime.date) -> Optional[Dict[str, Any]]:
    """解析时间范围，如 '从周一到周五'。"""
    m = RANGE_PATTERN.match(text)
    if not m:
        return None

    start_text = m.group("start").strip()
    end_text = m.group("end").strip()

    # 解析起点和终点
    start_result = parse_single(start_text, ref_date)
    if start_result is None or "date" not in start_result:
        return None

    end_result = parse_single(end_text, ref_date)
    if end_result is None or "date" not in end_result:
        return None

    start_date = datetime.date.fromisoformat(start_result["date"])
    end_date = datetime.date.fromisoformat(end_result["date"])

    # 如果终点在起点之前，可能表示跨周（如"从周五到下周一"）
    if end_date < start_date:
        # 尝试将终点延后一周
        end_date += datetime.timedelta(days=7)

    return _build_result(
        date_range=(start_date, end_date),
        confidence=min(start_result["confidence"], end_result["confidence"]) * 0.9,
    )


def parse_single(text: str, ref_date: Optional[datetime.date] = None) -> Optional[Dict[str, Any]]:
    """解析单个日期文本。"""
    if ref_date is None:
        ref_date = _today()

    text = text.strip()
    if not text:
        raise ValueError("E002")

    # 按优先级依次尝试
    parsers = [
        parse_absolute,
        parse_relative,
        parse_weekday,
        parse_holiday,
        parse_period,
        parse_range,
    ]

    for parser in parsers:
        try:
            result = parser(text, ref_date)
            if result is not None:
                return result
        except ValueError as e:
            # 如果解析器识别了但日期非法，抛出具体错误码
            if str(e).startswith("E"):
                raise

    return None


def parse_batch(texts: List[str], ref_date: Optional[datetime.date] = None) -> List[Dict[str, Any]]:
    """批量解析日期文本。"""
    if not texts:
        raise ValueError("E004")

    results = []
    for text in texts:
        try:
            result = parse_single(text, ref_date)
            if result is None:
                results.append({"error": "E002", "input": text, "message": "无法解析的日期文本"})
            else:
                results.append({"input": text, **result})
        except ValueError as e:
            error_code = str(e) if str(e).startswith("E") else "E006"
            results.append({"error": error_code, "input": text, "message": "解析失败"})

    return results


# ============================================================
# 自检模块
# ============================================================

def run_selftest() -> int:
    """内置硬编码样例离线自检。"""
    print("=" * 60)
    print("chronic 自检开始")
    print("=" * 60)

    # 固定参考日期（2026-05-01，周五）
    ref = datetime.date(2026, 5, 1)

    # 1. 绝对日期解析
    print("\n[1] 绝对日期解析")
    r = parse_single("2024年3月15日", ref)
    assert r is not None, "绝对日期解析失败"
    assert r["date"] == "2024-03-15", f"绝对日期错误: {r['date']}"
    assert r["confidence"] > 0.9, "置信度异常"
    print(f"  ✓ '2024年3月15日' -> {r['date']}")

    # 2. 相对日期解析
    print("\n[2] 相对日期解析")
    r = parse_single("三天后", ref)
    assert r is not None, "相对日期解析失败"
    assert r["date"] == "2026-05-04", f"相对日期错误: {r['date']}"
    assert r["confidence"] > 0.9, "置信度异常"
    print(f"  ✓ '三天后' -> {r['date']}")

    # 3. 模糊日期解析
    print("\n[3] 模糊日期解析")
    r = parse_single("下月中旬", ref)
    assert r is not None, "模糊日期解析失败"
    assert "date_range" in r, "缺少日期范围"
    assert r["date_range"]["start"] == "2026-05-11", f"范围起点错误: {r['date_range']['start']}"
    assert r["date_range"]["end"] == "2026-05-20", f"范围终点错误: {r['date_range']['end']}"
    assert r["confidence"] > 0.5, "置信度异常"
    print(f"  ✓ '下月中旬' -> {r['date_range']['start']} ~ {r['date_range']['end']}")

    # 4. 星期解析
    print("\n[4] 星期解析")
    r = parse_single("下周一", ref)
    assert r is not None, "星期解析失败"
    assert r["date"] == "2026-05-04", f"星期解析错误: {r['date']}"
    assert r["confidence"] > 0.8, "置信度异常"
    print(f"  ✓ '下周一' -> {r['date']}")

    # 5. 节日识别
    print("\n[5] 节日识别")
    r = parse_single("国庆节", ref)
    assert r is not None, "节日识别失败"
    assert r["holiday"] == "国庆节", f"节日名错误: {r.get('holiday')}"
    assert r["date"] == "2026-10-01", f"节日日期错误: {r['date']}"
    print(f"  ✓ '国庆节' -> {r['date']} ({r['holiday']})")

    # 6. 时间范围提取
    print("\n[6] 时间范围提取")
    r = parse_single("从周一到周五", ref)
    assert r is not None, "范围解析失败"
    assert "date_range" in r, "缺少范围"
    assert r["date_range"]["start"] == "2026-05-04", f"范围起点错误: {r['date_range']['start']}"
    assert r["date_range"]["end"] == "2026-05-08", f"范围终点错误: {r['date_range']['end']}"
    print(f"  ✓ '从周一到周五' -> {r['date_range']['start']} ~ {r['date_range']['end']}")

    # 7. 批量处理
    print("\n[7] 批量处理")
    batch = ["明天", "下周二", "2025年12月31日"]
    results = parse_batch(batch, ref)
    assert len(results) == 3, "批量结果数量不正确"
    assert results[0]["date"] == "2026-05-02", f"批量结果0错误: {results[0]}"
    assert results[1]["date"] == "2026-05-05", f"批量结果1错误: {results[1]}"
    assert results[2]["date"] == "2025-12-31", f"批量结果2错误: {results[2]}"
    print(f"  ✓ 批量解析 {len(results)} 条全部通过")

    # 8. 非法输入处理
    print("\n[8] 非法输入处理")
    try:
        parse_single("三斤苹果", ref)
        assert False, "非法输入未抛出异常"
    except ValueError as e:
        assert str(e) == "E002", f"错误码不正确: {e}"
    print("  ✓ '三斤苹果' -> 正确抛出 E002")

    # 9. 非法日期
    print("\n[9] 非法日期处理")
    try:
        parse_single("2024年2月30日", ref)
        assert False, "非法日期未抛出异常"
    except ValueError as e:
        assert str(e) == "E003", f"错误码不正确: {e}"
    print("  ✓ '2024年2月30日' -> 正确抛出 E003")

    # 10. 宽松阈值验证
    print("\n[10] 宽松阈值验证")
    # 验证各种输入都能得到合理结果（不依赖精确值）
    test_inputs = [
        "今天", "明天", "昨天", "上周五", "下个月", "明年",
        "1月1日", "12月31日", "周日", "劳动节", "上旬",
    ]
    for t in test_inputs:
        r = parse_single(t, ref)
        assert r is not None, f"输入 '{t}' 解析失败"
        assert "date" in r or "date_range" in r, f"输入 '{t}' 缺少结果"
        assert r["confidence"] > 0.0, f"输入 '{t}' 置信度为0"
    print(f"  ✓ {len(test_inputs)} 个测试输入全部通过")

    print("\n" + "=" * 60)
    print("所有自检通过 ✓")
    print("=" * 60)
    return 0


# ============================================================
# 命令行入口
# ============================================================

def main() -> int:
    """命令行主入口。"""
    parser = argparse.ArgumentParser(
        description="chronic - 自然语言日期解析工具",
        epilog="示例: chronic '三天后' | chronic --batch '明天' '下周一'",
    )
    parser.add_argument(
        "text",
        nargs="?",
        help="要解析的日期文本",
    )
    parser.add_argument(
        "--batch",
        nargs="+",
        help="批量解析多个日期文本",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检",
    )
    parser.add_argument(
        "--date",
        help="参考日期（默认今天），格式 YYYY-MM-DD",
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        try:
            return run_selftest()
        except AssertionError as e:
            print(f"自检失败: {e}", file=sys.stderr)
            return 1
        except Exception as e:
            print(f"自检异常: {e}", file=sys.stderr)
            return 1

    # 参考日期
    ref_date = None
    if args.date:
        try:
            ref_date = datetime.date.fromisoformat(args.date)
        except ValueError:
            print("E003: 参考日期格式错误，应为 YYYY-MM-DD", file=sys.stderr)
            return 3

    # 批量模式
    if args.batch:
        try:
            results = parse_batch(args.batch, ref_date)
            print(json.dumps(results, ensure_ascii=False, indent=2))
            return 0
        except ValueError as e:
            print(f"{e}: {e}", file=sys.stderr)
            return 4

    # 单条模式
    if args.text:
        try:
            result = parse_single(args.text, ref_date)
            if result is None:
                print("E002: 无法解析的日期文本", file=sys.stderr)
                return 2
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0
        except ValueError as e:
            code = str(e) if str(e).startswith("E") else "E006"
            print(f"{code}: 解析失败", file=sys.stderr)
            return 2

    # 无参数
    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
