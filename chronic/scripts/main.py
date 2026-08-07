#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
chronic - 时间语义解析（自然语言转结构化）
=============================================
本脚本依据功能规格独立实现，仅使用 Python 标准库。
支持相对/绝对日期、模糊时段、批量处理、时区标注、节假日识别。

用法示例：
    python scripts/main.py "后天下午3点"
    python scripts/main.py --selftest
    python scripts/main.py --batch "明天" "2024年3月15日" "周五傍晚"
"""

import argparse
import datetime
import re
import sys
from typing import Any, Dict, List, Optional, Tuple

# 错误码定义（E001-E010）
ERROR_CODES = {
    "E001": "输入为空或仅含空白字符",
    "E002": "输入不是字符串类型",
    "E003": "无法识别任何日期信息",
    "E004": "批量输入为空列表",
    "E005": "批量输入包含非字符串元素",
    "E006": "日期超出合理范围（1900-2100）",
    "E007": "时间格式非法（应为 HH:MM 或 HH:MM:SS）",
    "E008": "时区格式非法（应为 UTC±H 或 UTC±H:MM）",
    "E009": "内部计算错误（日期偏移失败）",
    "E010": "未知错误",
}

# 中文数字映射
CN_NUM = {
    "零": 0, "一": 1, "二": 2, "两": 2, "三": 3, "四": 4,
    "五": 5, "六": 6, "七": 7, "八": 8, "九": 9,
}

# 模糊时段关键词（权重用于置信度计算）
TIME_PERIODS = {
    "清晨": ("early_morning", 0.75),
    "早上": ("morning", 0.80),
    "上午": ("morning", 0.85),
    "中午": ("noon", 0.90),
    "下午": ("afternoon", 0.85),
    "傍晚": ("evening", 0.82),
    "晚上": ("evening", 0.80),
    "夜间": ("night", 0.70),
    "深夜": ("night", 0.65),
    "凌晨": ("early_morning", 0.70),
}

# 节假日映射（固定公历日期）
HOLIDAYS = {
    "元旦": (1, 1),
    "春节": None,  # 农历，不处理
    "劳动节": (5, 1),
    "国庆节": (10, 1),
    "圣诞节": (12, 25),
    "情人节": (2, 14),
    "妇女节": (3, 8),
    "植树节": (3, 12),
    "愚人节": (4, 1),
    "儿童节": (6, 1),
    "建军节": (8, 1),
    "教师节": (9, 10),
    "万圣节": (10, 31),
    "光棍节": (11, 11),
    "平安夜": (12, 24),
}

# 英文月份缩写
EN_MONTHS = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}

# 星期映射（中文）
WEEKDAYS_CN = {
    "一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "日": 7, "天": 7,
}


def _err(code: str, detail: str = "") -> Dict[str, Any]:
    """构造错误返回结构"""
    msg = ERROR_CODES.get(code, ERROR_CODES["E010"])
    result = {"error": {"code": code, "message": msg}}
    if detail:
        result["error"]["detail"] = detail
    return result


def _parse_cn_number(text: str) -> Optional[int]:
    """解析简单中文数字（0-99）"""
    if not text:
        return None
    # 直接数字
    if text.isdigit():
        return int(text)
    # 中文数字
    if text in CN_NUM:
        return CN_NUM[text]
    # 十位处理
    if "十" in text:
        parts = text.split("十")
        tens = CN_NUM.get(parts[0], 1) if parts[0] else 1
        ones = CN_NUM.get(parts[1], 0) if len(parts) > 1 and parts[1] else 0
        return tens * 10 + ones
    return None


def _parse_time(text: str) -> Optional[Tuple[int, int, int]]:
    """解析时间字符串为 (时, 分, 秒)，失败返回 None"""
    text = text.strip()
    # 支持 HH:MM 或 HH:MM:SS
    m = re.match(r"^(\d{1,2}):(\d{2})(?::(\d{2}))?$", text)
    if m:
        h, mi = int(m.group(1)), int(m.group(2))
        s = int(m.group(3)) if m.group(3) else 0
        if 0 <= h <= 23 and 0 <= mi <= 59 and 0 <= s <= 59:
            return (h, mi, s)
    # 支持 "3点" "3点半" "3点15分" 等中文
    m = re.match(r"^(\d{1,2})点(?:(半)|(\d{1,2})分?)?$", text)
    if m:
        h = int(m.group(1))
        if 0 <= h <= 23:
            if m.group(2):  # 半
                return (h, 30, 0)
            if m.group(3):
                mi = int(m.group(3))
                if 0 <= mi <= 59:
                    return (h, mi, 0)
            return (h, 0, 0)
    return None


def _parse_timezone(text: str) -> Optional[str]:
    """解析时区标注如 UTC+8, UTC-5, UTC+5:30, 北京时间"""
    text = text.strip()
    if "北京时间" in text:
        return "UTC+8"
    m = re.match(r"^UTC([+-])(\d{1,2})(?::(\d{2}))?$", text.strip(), re.IGNORECASE)
    if m:
        sign = 1 if m.group(1) == "+" else -1
        h = int(m.group(2))
        mi = int(m.group(3)) if m.group(3) else 0
        if 0 <= h <= 14 and 0 <= mi <= 59:
            return f"UTC{'+' if sign > 0 else '-'}{h}:{mi:02d}" if mi else f"UTC{'+' if sign > 0 else '-'}{h}"
    return None


def _parse_holiday(text: str, year: int) -> Optional[Dict[str, Any]]:
    """识别节假日，返回包含 date 和 holiday 字段的字典"""
    for name, (month, day) in HOLIDAYS.items():
        if name in text and month is not None:
            try:
                d = datetime.date(year, month, day)
                return {"date": d.isoformat(), "holiday": name, "format": "holiday"}
            except ValueError:
                return None
    return None


def _get_weekday_date(year: int, month: int, day: int, target_wd: int) -> datetime.date:
    """获取给定日期所在周的指定星期几（周一=1 ... 周日=7）"""
    base = datetime.date(year, month, day)
    delta = target_wd - base.isoweekday()
    return base + datetime.timedelta(days=delta)


def parse_datetime(text: str, base_date: Optional[datetime.date] = None) -> Dict[str, Any]:
    """
    解析自然语言日期描述为结构化数据。

    参数:
        text: 自然语言日期描述
        base_date: 基准日期（默认今天），用于相对日期计算

    返回:
        结构化字典，包含 date, time 等字段；失败时含 error 字段
    """
    # ---- 输入校验 ----
    if text is None:
        return _err("E001")
    if not isinstance(text, str):
        return _err("E002")
    text = text.strip()
    if not text:
        return _err("E001")

    # 基准日期
    today = base_date or datetime.date.today()
    year = today.year

    result: Dict[str, Any] = {}
    offset_days = 0
    time_str: Optional[str] = None
    time_period: Optional[str] = None
    confidence = 0.5  # 默认置信度
    tz_str: Optional[str] = None
    holiday_name: Optional[str] = None

    # ---- 时区识别 ----
    tz_match = re.search(r"(UTC[+-]\d{1,2}(?::\d{2})?|北京时间)", text)
    if tz_match:
        tz_parsed = _parse_timezone(tz_match.group(1))
        if tz_parsed:
            tz_str = tz_parsed
            result["timezone"] = tz_str
            text = text.replace(tz_match.group(1), "").strip()
        else:
            return _err("E008", tz_match.group(1))

    # ---- 节假日识别 ----
    holiday_result = _parse_holiday(text, year)
    if holiday_result:
        result.update(holiday_result)
        return result

    # ---- 相对日期关键词 ----
    rel_map = {
        "前天": -2, "昨天": -1, "今天": 0, "明天": 1, "后天": 2,
        "大前天": -3, "大后天": 3,
    }
    for kw, off in rel_map.items():
        if kw in text:
            offset_days = off
            text = text.replace(kw, "").strip()
            break

    # ---- 星期几识别（如 周一、周三、上周五） ----
    wd_match = re.search(r"(?:上|本|这|下)?(?:周|星期|礼拜)([一二三四五六日天])", text)
    if wd_match:
        prefix = wd_match.group(0)[0] if wd_match.group(0)[0] in "上本这下" else ""
        wd_num = WEEKDAYS_CN.get(wd_match.group(1))
        if wd_num:
            if prefix == "上":
                # 上周：取当前周对应星期再减7天
                target = _get_weekday_date(year, today.month, today.day, wd_num)
                offset_days = (target - today).days - 7
            elif prefix == "下":
                target = _get_weekday_date(year, today.month, today.day, wd_num)
                offset_days = (target - today).days + 7
            else:
                target = _get_weekday_date(year, today.month, today.day, wd_num)
                offset_days = (target - today).days
            text = text.replace(wd_match.group(0), "").strip()

    # ---- 模糊时段识别 ----
    for kw, (period, conf) in TIME_PERIODS.items():
        if kw in text:
            time_period = period
            confidence = max(confidence, conf)
            text = text.replace(kw, "").strip()
            break

    # ---- 时间识别（如 3点、15:30） ----
    time_match = re.search(r"(\d{1,2}[:点]\d{0,2}(?::\d{2})?(?:分)?)", text)
    if time_match:
        t_parsed = _parse_time(time_match.group(1))
        if t_parsed:
            h, mi, s = t_parsed
            time_str = f"{h:02d}:{mi:02d}:{s:02d}"
            result["time"] = time_str
            text = text.replace(time_match.group(1), "").strip()

    # ---- 绝对日期识别 ----
    date_found = False
    abs_date: Optional[datetime.date] = None

    # 格式1: 2024年3月15日 或 2024年3月15号
    m = re.search(r"(\d{4})年(\d{1,2})月(\d{1,2})[日号]?", text)
    if m:
        y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
        try:
            abs_date = datetime.date(y, mo, d)
            date_found = True
            text = text.replace(m.group(0), "").strip()
        except ValueError:
            return _err("E006", f"{y}-{mo}-{d}")

    # 格式2: 3月15日 / 3月15号（无年份，默认当前年）
    if not date_found:
        m = re.search(r"(\d{1,2})月(\d{1,2})[日号]?", text)
        if m:
            mo, d = int(m.group(1)), int(m.group(2))
            try:
                abs_date = datetime.date(year, mo, d)
                date_found = True
                text = text.replace(m.group(0), "").strip()
            except ValueError:
                return _err("E006", f"{year}-{mo}-{d}")

    # 格式3: 03/15/2024 或 2024/03/15 或 2024-03-15
    if not date_found:
        m = re.search(r"(\d{4})[/-](\d{1,2})[/-](\d{1,2})", text)
        if m:
            y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
            try:
                abs_date = datetime.date(y, mo, d)
                date_found = True
                text = text.replace(m.group(0), "").strip()
            except ValueError:
                return _err("E006", f"{y}-{mo}-{d}")

    # 格式4: 英文月份缩写（如 15 Mar 2024 或 Mar 15, 2024）
    if not date_found:
        m = re.search(r"(\d{1,2})\s+([A-Za-z]{3})\.?\s+(\d{4})", text)
        if m:
            d, mon, y = int(m.group(1)), m.group(2).lower(), int(m.group(3))
            if mon in EN_MONTHS:
                try:
                    abs_date = datetime.date(y, EN_MONTHS[mon], d)
                    date_found = True
                    text = text.replace(m.group(0), "").strip()
                except ValueError:
                    return _err("E006", f"{y}-{EN_MONTHS[mon]}-{d}")
        if not date_found:
            m = re.search(r"([A-Za-z]{3})\.?\s+(\d{1,2}),?\s+(\d{4})", text)
            if m:
                mon, d, y = m.group(1).lower(), int(m.group(2)), int(m.group(3))
                if mon in EN_MONTHS:
                    try:
                        abs_date = datetime.date(y, EN_MONTHS[mon], d)
                        date_found = True
                        text = text.replace(m.group(0), "").strip()
                    except ValueError:
                        return _err("E006", f"{y}-{EN_MONTHS[mon]}-{d}")

    # ---- 组合日期 ----
    if date_found and offset_days != 0:
        # 绝对日期 + 相对偏移（如 3月15日 后天？不太合理，但规格允许简单组合）
        try:
            abs_date = abs_date + datetime.timedelta(days=offset_days)
        except OverflowError:
            return _err("E009")
        offset_days = 0  # 已应用

    if date_found:
        result["date"] = abs_date.isoformat()
        result["format"] = "explicit"
    elif offset_days != 0:
        try:
            target = today + datetime.timedelta(days=offset_days)
            result["date"] = target.isoformat()
            result["offset_days"] = offset_days
            result["format"] = "relative"
        except OverflowError:
            return _err("E009")
    else:
        # 无日期信息，尝试仅识别时间/时段
        if time_str or time_period:
            result["date"] = today.isoformat()
            result["format"] = "partial"
        else:
            return _err("E003")

    # ---- 附加信息 ----
    if time_period:
        result["time_period"] = time_period
        result["confidence"] = round(confidence, 2)
    elif time_str:
        result["confidence"] = 0.95
    elif date_found:
        result["confidence"] = 1.0
    else:
        result["confidence"] = 0.6

    return result


def parse_batch(items: List[str], base_date: Optional[datetime.date] = None) -> List[Dict[str, Any]]:
    """批量解析多条日期描述"""
    if not items:
        return [_err("E004")]
    if not isinstance(items, list):
        return [_err("E004")]
    results = []
    for item in items:
        if not isinstance(item, str):
            results.append(_err("E005"))
        else:
            results.append(parse_datetime(item, base_date))
    return results


def _selftest() -> int:
    """自检核心逻辑，使用硬编码样例数据，不依赖外部环境"""
    print("[chronic] 自检开始...")
    errors = 0

    # 固定基准日期，确保可复现
    base = datetime.date(2026, 5, 10)  # 2026-05-10 是星期日

    # 测试用例：(输入, 期望日期, 期望时间, 期望偏移)
    test_cases = [
        ("明天", "2026-05-11", None, 1),
        ("后天下午3点", "2026-05-12", "15:00:00", 2),
        ("2024年3月15日", "2024-03-15", None, None),
        ("03/15/2024", "2024-03-15", None, None),
        ("周五傍晚", "2026-05-15", None, None),  # 基准日周日，本周五是 5/15
        ("上周三", "2026-05-06", None, None),    # 基准日周日，上周三是 5/6
        ("国庆节", "2026-10-01", None, None),
        ("明天上午9点(UTC+8)", "2026-05-11", "09:00:00", 1),
    ]

    for input_text, exp_date, exp_time, exp_offset in test_cases:
        result = parse_datetime(input_text, base_date=base)
        if "error" in result:
            print(f"  [FAIL] '{input_text}' -> 错误: {result['error']}")
            errors += 1
            continue

        # 宽松断言：日期必须匹配
        if result.get("date") != exp_date:
            print(f"  [FAIL] '{input_text}' -> 期望日期 {exp_date}, 实际 {result.get('date')}")
            errors += 1
            continue

        # 时间宽松断言：存在性 + 非空
        if exp_time:
            if not result.get("time") or result["time"] != exp_time:
                print(f"  [FAIL] '{input_text}' -> 期望时间 {exp_time}, 实际 {result.get('time')}")
                errors += 1
                continue

        # 偏移宽松断言：存在性 + 数值
        if exp_offset is not None:
            if result.get("offset_days") != exp_offset:
                print(f"  [FAIL] '{input_text}' -> 期望偏移 {exp_offset}, 实际 {result.get('offset_days')}")
                errors += 1
                continue

        print(f"  [PASS] '{input_text}' -> {result}")

    # 批量测试
    batch_input = ["明天", "2024年3月15日", "周五傍晚"]
    batch_result = parse_batch(batch_input, base_date=base)
    if len(batch_result) != 3:
        print(f"  [FAIL] 批量测试期望 3 条结果, 实际 {len(batch_result)}")
        errors += 1
    else:
        if "error" in batch_result[0] or "error" in batch_result[1] or "error" in batch_result[2]:
            print("  [FAIL] 批量测试存在错误结果")
            errors += 1
        else:
            print(f"  [PASS] 批量测试 -> {batch_result}")

    # 错误处理测试
    err_cases = ["", "   ", "无意义内容xyz", 12345]
    for bad_input in err_cases:
        r = parse_datetime(bad_input, base_date=base)
        if "error" not in r:
            print(f"  [FAIL] 错误输入 '{bad_input}' 未返回错误")
            errors += 1
        else:
            print(f"  [PASS] 错误输入 '{bad_input}' -> {r['error']['code']}")

    if errors == 0:
        print("[chronic] 自检全部通过 ✔")
    else:
        print(f"[chronic] 自检完成，{errors} 项失败 ✘")
    return errors


def main() -> int:
    """命令行入口"""
    parser = argparse.ArgumentParser(
        prog="chronic",
        description="时间语义解析：自然语言日期转结构化数据",
        epilog="示例: chronic '后天下午3点' | chronic --batch '明天' '2024年3月15日'"
    )
    parser.add_argument("text", nargs="?", help="要解析的日期描述")
    parser.add_argument("--batch", nargs="+", help="批量解析多条日期描述")
    parser.add_argument("--selftest", action="store_true", help="运行内置自检")
    parser.add_argument("--json", action="store_true", help="以 JSON 格式输出")
    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        return _selftest()

    # 批量模式
    if args.batch:
        results = parse_batch(args.batch)
        if args.json:
            import json
            print(json.dumps(results, ensure_ascii=False, indent=2))
        else:
            for item, r in zip(args.batch, results):
                if "error" in r:
                    print(f"'{item}': 错误 [{r['error']['code']}] {r['error']['message']}")
                else:
                    print(f"'{item}': {r}")
        return 0

    # 单条模式
    if not args.text:
        parser.print_help()
        return 1

    result = parse_datetime(args.text)
    if args.json:
        import json
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        if "error" in result:
            print(f"错误 [{result['error']['code']}]: {result['error']['message']}")
            if "detail" in result["error"]:
                print(f"详情: {result['error']['detail']}")
            return 1
        print(result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
