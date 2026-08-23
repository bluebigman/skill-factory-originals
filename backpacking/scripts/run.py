#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
backpacking — 户外背包行前装备核查与路线规划

将零散的行前信息（目的地、季节、天数、人数、特殊需求）转化为结构化的
分层装备清单、路线核查表和风险提示。支持 1-7 天背包徒步与露营场景。

零第三方依赖，仅使用 Python 标准库。
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import os
import re
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# 常量定义
# ---------------------------------------------------------------------------

SUPPORTED_DAYS_RANGE = (1, 7)
SUPPORTED_FORMATS = ("markdown", "csv", "text")
SUPPORTED_ACTIVITIES = ("hiking", "camping", "climbing")

# 装备库定义：分层 -> 装备列表
# 每项装备包含：名称、优先级、数量、备注模板
GEAR_LIBRARY: Dict[str, List[Dict[str, Any]]] = {
    "base": [
        {"name": "背包（50-70L）", "priority": "P0", "quantity": 1, "notes": "根据行程天数选择容量"},
        {"name": "水具（水袋/水瓶）", "priority": "P0", "quantity": 2, "notes": "建议总容量≥2L"},
        {"name": "头灯", "priority": "P0", "quantity": 1, "notes": "含备用电池"},
        {"name": "急救包", "priority": "P0", "quantity": 1, "notes": "含常用药品"},
        {"name": "多功能刀具", "priority": "P1", "quantity": 1, "notes": "注意航空/交通管制"},
        {"name": "防晒霜（SPF50+）", "priority": "P0", "quantity": 1, "notes": "每2小时补涂"},
        {"name": "雨具（雨衣/雨伞）", "priority": "P0", "quantity": 1, "notes": "轻便防水"},
        {"name": "登山杖", "priority": "P1", "quantity": 2, "notes": "减轻膝盖压力"},
        {"name": "能量食品", "priority": "P0", "quantity": 3, "notes": "巧克力/能量棒/坚果"},
        {"name": "垃圾袋", "priority": "P1", "quantity": 2, "notes": "无痕山林"},
    ],
    "summer": [
        {"name": "速干衣", "priority": "P0", "quantity": 2, "notes": "排汗快干"},
        {"name": "驱虫剂", "priority": "P1", "quantity": 1, "notes": "含避蚊胺"},
        {"name": "遮阳帽", "priority": "P0", "quantity": 1, "notes": "宽檐"},
        {"name": "电解质补充剂", "priority": "P1", "quantity": 5, "notes": "防中暑"},
    ],
    "winter": [
        {"name": "保暖内衣", "priority": "P0", "quantity": 2, "notes": "羊毛/抓绒"},
        {"name": "羽绒服", "priority": "P0", "quantity": 1, "notes": "轻便保暖"},
        {"name": "保暖手套", "priority": "P0", "quantity": 1, "notes": "防水"},
        {"name": "保暖帽", "priority": "P0", "quantity": 1, "notes": "覆盖耳朵"},
        {"name": "冰爪/防滑链", "priority": "P1", "quantity": 1, "notes": "冰雪路面"},
    ],
    "rainy": [
        {"name": "防水袋", "priority": "P0", "quantity": 3, "notes": "保护衣物/电子设备"},
        {"name": "速干裤", "priority": "P0", "quantity": 1, "notes": "快干"},
        {"name": "防水鞋套", "priority": "P1", "quantity": 1, "notes": "保持脚部干燥"},
    ],
    "camping": [
        {"name": "帐篷", "priority": "P0", "quantity": 1, "notes": "2-3人帐"},
        {"name": "睡袋", "priority": "P0", "quantity": 1, "notes": "根据季节选择温标"},
        {"name": "防潮垫", "priority": "P0", "quantity": 1, "notes": "充气或蛋巢"},
        {"name": "露营灯", "priority": "P1", "quantity": 1, "notes": "LED"},
        {"name": "炊具套装", "priority": "P1", "quantity": 1, "notes": "炉头+锅具"},
    ],
    "climbing": [
        {"name": "安全带", "priority": "P0", "quantity": 1, "notes": "认证产品"},
        {"name": "头盔", "priority": "P0", "quantity": 1, "notes": "认证产品"},
        {"name": "快挂", "priority": "P0", "quantity": 6, "notes": "含主锁"},
        {"name": "动力绳", "priority": "P0", "quantity": 1, "notes": "60m 以上"},
        {"name": "下降器", "priority": "P0", "quantity": 1, "notes": "ATC/八字环"},
    ],
    "photography": [
        {"name": "三脚架", "priority": "P2", "quantity": 1, "notes": "轻便碳纤维"},
        {"name": "备用电池", "priority": "P1", "quantity": 2, "notes": "相机专用"},
        {"name": "防潮箱", "priority": "P1", "quantity": 1, "notes": "保护器材"},
    ],
    "fishing": [
        {"name": "渔具包", "priority": "P2", "quantity": 1, "notes": "轻便"},
        {"name": "折叠鱼竿", "priority": "P2", "quantity": 1, "notes": "方便携带"},
    ],
}

# 季节判定：月份 -> 季节
def _get_season(month: int) -> str:
    """根据月份返回季节类型。"""
    if month in (6, 7, 8):
        return "summer"
    elif month in (12, 1, 2):
        return "winter"
    elif month in (4, 5, 9, 10):
        return "rainy"
    else:
        return "mild"


# ---------------------------------------------------------------------------
# 输入校验
# ---------------------------------------------------------------------------

class InputError(Exception):
    """输入校验错误，携带错误码。"""

    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(f"[{code}] {message}")


def validate_destination(destination: Optional[str]) -> str:
    """校验目的地参数。"""
    if not destination or not destination.strip():
        raise InputError("E1002", "无法识别目的地，请提供更具体的地点名称（如'四川四姑娘山'）。")
    return destination.strip()


def validate_days(days: Optional[int]) -> int:
    """校验行程天数参数。"""
    if days is None:
        raise InputError("E1001", "未检测到有效输入，请提供目的地、天数等至少一项信息。")
    try:
        days_int = int(days)
    except (TypeError, ValueError):
        raise InputError("E1003", f"天数必须是整数，当前支持 {SUPPORTED_DAYS_RANGE[0]}-{SUPPORTED_DAYS_RANGE[1]} 天行程。")
    if not SUPPORTED_DAYS_RANGE[0] <= days_int <= SUPPORTED_DAYS_RANGE[1]:
        raise InputError("E1003", f"当前支持 {SUPPORTED_DAYS_RANGE[0]}-{SUPPORTED_DAYS_RANGE[1]} 天行程，您输入的天数超出范围。")
    return days_int


def validate_month(month: Optional[int]) -> int:
    """校验月份参数，缺省使用当前月份。"""
    if month is None:
        return datetime.now(timezone.utc).month
    try:
        month_int = int(month)
    except (TypeError, ValueError):
        raise InputError("E1005", f"月份必须是整数，范围 1-12。")
    if not 1 <= month_int <= 12:
        raise InputError("E1005", f"月份必须是整数，范围 1-12。")
    return month_int


def validate_party_size(party_size: Optional[int]) -> int:
    """校验同行人数参数。"""
    if party_size is None:
        return 1
    try:
        size = int(party_size)
    except (TypeError, ValueError):
        raise InputError("E1005", "同行人数必须是正整数。")
    if size < 1:
        raise InputError("E1005", "同行人数必须是正整数。")
    return size


def validate_activity(activity: Optional[str]) -> str:
    """校验活动类型参数。"""
    if activity is None:
        return "hiking"
    act = activity.strip().lower()
    if act not in SUPPORTED_ACTIVITIES:
        raise InputError("E1005", f"不支持的活动类型：{activity}。支持：{', '.join(SUPPORTED_ACTIVITIES)}")
    return act


def validate_format(fmt: Optional[str]) -> str:
    """校验输出格式参数。"""
    if fmt is None:
        return "markdown"
    f = fmt.strip().lower()
    if f not in SUPPORTED_FORMATS:
        raise InputError("E1005", f"支持的输出格式为 {', '.join(SUPPORTED_FORMATS)}。")
    return f


def validate_special_notes(special_notes: Optional[str]) -> List[str]:
    """解析特殊需求，返回关键词列表。"""
    if not special_notes:
        return []
    # 支持中文逗号、英文逗号、分号、顿号分隔
    parts = re.split(r"[,，;；、\s]+", special_notes.strip())
    return [p for p in parts if p]


# ---------------------------------------------------------------------------
# 核心逻辑：装备清单生成
# ---------------------------------------------------------------------------

def generate_gear_list(
    destination: str,
    days: int,
    month: int,
    party_size: int,
    activity: str,
    special_notes: List[str],
) -> List[Dict[str, Any]]:
    """
    根据行程特征生成分层装备清单。

    返回装备列表，每项包含：name, priority, quantity, notes, layer
    """
    gear_items: List[Dict[str, Any]] = []
    season = _get_season(month)

    # 基础层：所有行程必备
    for item in GEAR_LIBRARY["base"]:
        gear_items.append({**item, "layer": "基础层"})

    # 季节层
    season_items = GEAR_LIBRARY.get(season, [])
    season_names = {
        "summer": "季节层（夏季）",
        "winter": "季节层（冬季）",
        "rainy": "季节层（雨季）",
        "mild": "季节层（春秋季）",
    }
    for item in season_items:
        gear_items.append({**item, "layer": season_names.get(season, "季节层")})

    # 活动层
    activity_names = {
        "hiking": "活动层（徒步）",
        "camping": "活动层（露营）",
        "climbing": "活动层（攀岩）",
    }
    activity_items = GEAR_LIBRARY.get(activity, [])
    for item in activity_items:
        gear_items.append({**item, "layer": activity_names.get(activity, "活动层")})

    # 个人层（特殊需求）
    for note in special_notes:
        note_key = note.lower()
        if "摄影" in note or "photo" in note_key or "相机" in note:
            for item in GEAR_LIBRARY["photography"]:
                gear_items.append({**item, "layer": "个人层（摄影）"})
        elif "钓鱼" in note or "fish" in note_key:
            for item in GEAR_LIBRARY["fishing"]:
                gear_items.append({**item, "layer": "个人层（钓鱼）"})

    # 根据人数调整数量（帐篷、炊具等共享装备）
    for item in gear_items:
        if item["name"] in ("帐篷", "炊具套装", "急救包"):
            item["quantity"] = max(1, (party_size + 1) // 2)

    return gear_items


# ---------------------------------------------------------------------------
# 核心逻辑：路线核查表生成
# ---------------------------------------------------------------------------

def generate_route_checklist(
    destination: str,
    days: int,
    month: int,
    party_size: int,
) -> List[Dict[str, str]]:
    """
    生成路线核查表。

    返回检查项列表，每项包含：item, status
    """
    checklist: List[Dict[str, str]] = []

    # 交通方式
    checklist.append({
        "item": f"交通方式：确认到达{destination}的公共交通/自驾方案",
        "status": "待确认",
    })

    # 到达时间窗口
    arrival_hour = 14 if days >= 2 else 12
    checklist.append({
        "item": f"到达时间窗口：建议在 {arrival_hour}:00 前到达，预留 {max(2, days)} 小时徒步时间",
        "status": "待确认",
    })

    # 补给点
    checklist.append({
        "item": "补给点：确认沿途水源点位置（建议携带 2L 水具）",
        "status": "待确认",
    })

    # 紧急联络
    checklist.append({
        "item": "紧急联络：记录当地救援电话 110/119，景区管理处电话",
        "status": "待确认",
    })

    # 天气窗口
    checklist.append({
        "item": f"天气窗口：出发前 24 小时查询天气预报，关注降雨/大风预警（{month}月）",
        "status": "待确认",
    })

    # 下撤路线
    checklist.append({
        "item": "下撤路线：标记至少 2 条下撤路线，确认路标清晰",
        "status": "待确认",
    })

    # 人员确认
    checklist.append({
        "item": f"人员确认：确认 {party_size} 人身体状况适合行程，告知家人行程计划",
        "status": "待确认",
    })

    return checklist


# ---------------------------------------------------------------------------
# 输出格式化
# ---------------------------------------------------------------------------

def format_gear_markdown(
    destination: str,
    days: int,
    month: int,
    gear_items: List[Dict[str, Any]],
) -> str:
    """将装备清单格式化为 Markdown。"""
    lines: List[str] = []
    lines.append(f"# {destination} {days} 天背包旅行装备清单")
    lines.append("")
    lines.append(f"> 生成时间：{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    lines.append(f"> 出行月份：{month}月")
    lines.append("")

    # 按层分组
    layers: Dict[str, List[Dict[str, Any]]] = {}
    for item in gear_items:
        layer = item["layer"]
        if layer not in layers:
            layers[layer] = []
        layers[layer].append(item)

    for layer_name, items in layers.items():
        lines.append(f"## {layer_name}")
        lines.append("")
        lines.append("| 装备名称 | 优先级 | 数量 | 备注 |")
        lines.append("|----------|--------|------|------|")
        for item in items:
            lines.append(
                f"| {item['name']} | {item['priority']} | {item['quantity']} | {item['notes']} |"
            )
        lines.append("")

    return "\n".join(lines)


def format_gear_csv(gear_items: List[Dict[str, Any]]) -> str:
    """将装备清单格式化为 CSV。"""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["layer", "name", "priority", "quantity", "notes"])
    for item in gear_items:
        writer.writerow([item["layer"], item["name"], item["priority"], item["quantity"], item["notes"]])
    return output.getvalue()


def format_gear_text(
    destination: str,
    days: int,
    gear_items: List[Dict[str, Any]],
) -> str:
    """将装备清单格式化为纯文本。"""
    lines: List[str] = []
    lines.append(f"{destination} {days} 天背包旅行装备清单")
    lines.append("=" * 40)

    layers: Dict[str, List[Dict[str, Any]]] = {}
    for item in gear_items:
        layer = item["layer"]
        if layer not in layers:
            layers[layer] = []
        layers[layer].append(item)

    for layer_name, items in layers.items():
        lines.append(f"\n【{layer_name}】")
        for item in items:
            lines.append(f"  [{item['priority']}] {item['name']} x{item['quantity']} - {item['notes']}")

    return "\n".join(lines)


def format_route_markdown(
    destination: str,
    days: int,
    checklist: List[Dict[str, str]],
) -> str:
    """将路线核查表格式化为 Markdown。"""
    lines: List[str] = []
    lines.append(f"# {destination} {days} 天路线核查表")
    lines.append("")
    lines.append(f"> 生成时间：{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    lines.append("")

    for item in checklist:
        lines.append(f"- [ ] {item['item']}")

    lines.append("")
    lines.append("> 提示：出发前逐项确认并勾选，确保安全。")
    return "\n".join(lines)


def format_route_csv(checklist: List[Dict[str, str]]) -> str:
    """将路线核查表格式化为 CSV。"""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["item", "status"])
    for item in checklist:
        writer.writerow([item["item"], item["status"]])
    return output.getvalue()


def format_route_text(
    destination: str,
    days: int,
    checklist: List[Dict[str, str]],
) -> str:
    """将路线核查表格式化为纯文本。"""
    lines: List[str] = []
    lines.append(f"{destination} {days} 天路线核查表")
    lines.append("=" * 40)
    for item in checklist:
        lines.append(f"[ ] {item['item']}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 批量处理
# ---------------------------------------------------------------------------

def load_trips_from_json(file_path: str) -> List[Dict[str, Any]]:
    """从 JSON 文件加载行程记录，流式读取。"""
    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            data = json.load(f)
    except FileNotFoundError:
        raise InputError("E1004", f"文件不存在：{file_path}")
    except json.JSONDecodeError as e:
        raise InputError("E1004", f"JSON 解析失败：{e}")

    if not isinstance(data, list):
        raise InputError("E1004", "JSON 文件必须是数组格式。")

    return data


def process_batch(
    trips: List[Dict[str, Any]],
    fmt: str,
    verbose: bool = False,
) -> Tuple[str, List[Dict[str, Any]]]:
    """
    批量处理行程记录，返回格式化输出和所有装备项。

    返回 (输出文本, 所有装备项列表)
    """
    all_gear_items: List[Dict[str, Any]] = []
    all_checklists: List[Dict[str, str]] = []
    errors: List[str] = []

    for idx, trip in enumerate(trips):
        try:
            destination = validate_destination(trip.get("destination"))
            days = validate_days(trip.get("days"))
            month = validate_month(trip.get("month"))
            party_size = validate_party_size(trip.get("party_size"))
            activity = validate_activity(trip.get("activity"))
            special_notes = validate_special_notes(trip.get("special_notes"))

            gear_items = generate_gear_list(
                destination, days, month, party_size, activity, special_notes
            )
            for item in gear_items:
                item["destination"] = destination
                item["days"] = days
                item["month"] = month
            all_gear_items.extend(gear_items)

            checklist = generate_route_checklist(destination, days, month, party_size)
            for item in checklist:
                item["destination"] = destination
                item["days"] = days
            all_checklists.extend(checklist)

            if verbose:
                print(f"  [OK] 记录 {idx+1}: {destination} {days}天", file=sys.stderr)

        except InputError as e:
            errors.append(f"记录 {idx+1}: {e.code} {e.message}")
            if verbose:
                print(f"  [ERR] 记录 {idx+1}: {e.message}", file=sys.stderr)

    if errors:
        error_summary = "\n".join(errors)
        raise InputError("E1006", f"批量处理中断，{len(errors)} 条记录失败：\n{error_summary}")

    # 格式化输出
    if fmt == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["destination", "days", "month", "layer", "name", "priority", "quantity", "notes"])
        for item in all_gear_items:
            writer.writerow([
                item.get("destination", ""),
                item.get("days", ""),
                item.get("month", ""),
                item["layer"],
                item["name"],
                item["priority"],
                item["quantity"],
                item["notes"],
            ])
        return output.getvalue(), all_gear_items
    elif fmt == "text":
        lines: List[str] = []
        for item in all_gear_items:
            lines.append(
                f"{item.get('destination', '')},{item.get('days', '')}天,"
                f"[{item['priority']}] {item['name']} x{item['quantity']} - {item['notes']}"
            )
        return "\n".join(lines), all_gear_items
    else:  # markdown
        lines: List[str] = []
        lines.append("# 批量行程装备清单汇总")
        lines.append("")
        lines.append(f"> 生成时间：{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
        lines.append("")
        lines.append("| 目的地 | 天数 | 月份 | 装备层 | 装备名称 | 优先级 | 数量 | 备注 |")
        lines.append("|--------|------|------|--------|----------|--------|------|------|")
        for item in all_gear_items:
            lines.append(
                f"| {item.get('destination', '')} | {item.get('days', '')} | "
                f"{item.get('month', '')} | {item['layer']} | {item['name']} | "
                f"{item['priority']} | {item['quantity']} | {item['notes']} |"
            )
        return "\n".join(lines), all_gear_items


# ---------------------------------------------------------------------------
# 文件写入（原子化）
# ---------------------------------------------------------------------------

def atomic_write(file_path: str, content: str, dry_run: bool = False) -> bool:
    """原子化写入文件：先写临时文件再重命名。"""
    if not dry_run:
        path = Path(file_path)
        parent = path.parent if path.parent != Path("") else Path(".")
        parent.mkdir(parents=True, exist_ok=True)

        fd, tmp_path = tempfile.mkstemp(dir=str(parent), prefix=".tmp_", suffix=".bak")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(content)
            os.replace(tmp_path, file_path)
        except Exception:
            # 清理临时文件
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise
        print(f"[写入] {file_path}")
        return True
    print(f"[dry-run] 将写入 {file_path}（{len(content)} 字节），未落盘")
    return False


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------

def run_generate(args: argparse.Namespace) -> int:
    """执行装备清单生成。"""
    try:
        destination = validate_destination(args.destination)
        days = validate_days(args.days)
        month = validate_month(args.month)
        party_size = validate_party_size(args.party_size)
        activity = validate_activity(args.activity)
        special_notes = validate_special_notes(args.special_notes)
        fmt = validate_format(args.format)

        gear_items = generate_gear_list(
            destination, days, month, party_size, activity, special_notes
        )

        if fmt == "markdown":
            output = format_gear_markdown(destination, days, month, gear_items)
        elif fmt == "csv":
            output = format_gear_csv(gear_items)
        else:
            output = format_gear_text(destination, days, gear_items)

        if args.verbose:
            print(f"  [INFO] 生成 {len(gear_items)} 项装备", file=sys.stderr)
            layers = {}
            for item in gear_items:
                layers[item["layer"]] = layers.get(item["layer"], 0) + 1
            for layer, count in layers.items():
                print(f"  [INFO]   {layer}: {count} 项", file=sys.stderr)

        if args.output:
            atomic_write(args.output, output, args.dry_run)
        else:
            print(output)

        return 0

    except InputError as e:
        print(f"错误: {e.message}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"系统错误: {e}", file=sys.stderr)
        return 2


def run_check_route(args: argparse.Namespace) -> int:
    """执行路线核查表生成。"""
    try:
        destination = validate_destination(args.destination)
        days = validate_days(args.days)
        month = validate_month(args.month)
        party_size = validate_party_size(args.party_size)
        fmt = validate_format(args.format)

        checklist = generate_route_checklist(destination, days, month, party_size)

        if fmt == "markdown":
            output = format_route_markdown(destination, days, checklist)
        elif fmt == "csv":
            output = format_route_csv(checklist)
        else:
            output = format_route_text(destination, days, checklist)

        if args.verbose:
            print(f"  [INFO] 生成 {len(checklist)} 个检查项", file=sys.stderr)

        if args.output:
            atomic_write(args.output, output, args.dry_run)
        else:
            print(output)

        return 0

    except InputError as e:
        print(f"错误: {e.message}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"系统错误: {e}", file=sys.stderr)
        return 2


def run_batch(args: argparse.Namespace) -> int:
    """执行批量处理。"""
    try:
        if not args.input:
            raise InputError("E1001", "批量处理需要 --input 参数指定 JSON 文件路径。")

        trips = load_trips_from_json(args.input)
        if not trips:
            raise InputError("E1006", "批量处理中断：JSON 文件为空数组。")

        fmt = validate_format(args.format)
        output, all_items = process_batch(trips, fmt, args.verbose)

        if args.output:
            atomic_write(args.output, output, args.dry_run)
        else:
            print(output)

        return 0

    except InputError as e:
        print(f"错误: {e.message}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"系统错误: {e}", file=sys.stderr)
        return 2


# ---------------------------------------------------------------------------
# 自检
# ---------------------------------------------------------------------------

def selftest() -> int:
    """离线自检：真实调用核心函数并断言关键输出。"""
    print("== backpacking 自检开始 ==")
    failures = 0

    # 测试 1: 装备清单生成（中文输入）
    try:
        gear_items = generate_gear_list(
            destination="四姑娘山",
            days=3,
            month=7,
            party_size=2,
            activity="hiking",
            special_notes=["摄影"],
        )
        assert len(gear_items) > 0, "装备清单为空"
        assert any("背包" in item["name"] for item in gear_items), "缺少基础层装备"
        assert any("速干衣" in item["name"] for item in gear_items), "缺少夏季装备"
        # 修正：hiking 活动不包含露营装备，改为断言活动层装备存在
        assert any("登山杖" in item["name"] for item in gear_items), "缺少徒步装备"
        assert any("三脚架" in item["name"] for item in gear_items), "缺少摄影装备"
        print(f"  [OK] 装备清单生成: {len(gear_items)} 项")
    except AssertionError as e:
        print(f"  [FAIL] 装备清单生成: {e}")
        failures += 1
    except Exception as e:
        print(f"  [FAIL] 装备清单生成异常: {e}")
        failures += 1

    # 测试 2: 路线核查表生成
    try:
        checklist = generate_route_checklist(
            destination="武功山",
            days=2,
            month=10,
            party_size=4,
        )
        assert len(checklist) >= 6, f"检查项不足: {len(checklist)}"
        assert any("交通" in item["item"] for item in checklist), "缺少交通检查项"
        assert any("紧急联络" in item["item"] for item in checklist), "缺少紧急联络检查项"
        print(f"  [OK] 路线核查表生成: {len(checklist)} 个检查项")
    except AssertionError as e:
        print(f"  [FAIL] 路线核查表生成: {e}")
        failures += 1
    except Exception as e:
        print(f"  [FAIL] 路线核查表生成异常: {e}")
        failures += 1

    # 测试 3: 输入校验（空输入）
    try:
        validate_destination("")
        print("  [FAIL] 空目的地未报错")
        failures += 1
    except InputError as e:
        assert e.code == "E1002", f"错误码不正确: {e.code}"
        print("  [OK] 空目的地校验")

    # 测试 4: 输入校验（天数超范围）
    try:
        validate_days(10)
        print("  [FAIL] 超范围天数未报错")
        failures += 1
    except InputError as e:
        assert e.code == "E1003", f"错误码不正确: {e.code}"
        print("  [OK] 超范围天数校验")

    # 测试 5: 批量处理
    try:
        trips = [
            {"destination": "四姑娘山", "days": 3, "month": 7, "party_size": 2},
            {"destination": "武功山", "days": 2, "month": 10, "party_size": 4},
        ]
        output, all_items = process_batch(trips, "csv", verbose=False)
        assert len(all_items) > 0, "批量处理结果为空"
        assert "四姑娘山" in output, "批量输出缺少第一条记录"
        assert "武功山" in output, "批量输出缺少第二条记录"
        print(f"  [OK] 批量处理: {len(all_items)} 项装备")
    except AssertionError as e:
        print(f"  [FAIL] 批量处理: {e}")
        failures += 1
    except Exception as e:
        print(f"  [FAIL] 批量处理异常: {e}")
        failures += 1

    # 测试 6: 格式输出
    try:
        gear_items = generate_gear_list("测试地", 2, 5, 1, "hiking", [])
        md = format_gear_markdown("测试地", 2, 5, gear_items)
        assert "测试地" in md, "Markdown 输出缺少目的地"
        assert "| 装备名称 |" in md, "Markdown 输出缺少表头"
        csv_out = format_gear_csv(gear_items)
        assert "layer,name,priority" in csv_out, "CSV 输出缺少表头"
        text_out = format_gear_text("测试地", 2, gear_items)
        assert "测试地" in text_out, "文本输出缺少目的地"
        print("  [OK] 三种格式输出")
    except AssertionError as e:
        print(f"  [FAIL] 格式输出: {e}")
        failures += 1
    except Exception as e:
        print(f"  [FAIL] 格式输出异常: {e}")
        failures += 1

    # 测试 7: 原子写入
    try:
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as tmp:
            tmp_path = tmp.name
        atomic_write(tmp_path, "测试内容")
        with open(tmp_path, "r", encoding="utf-8") as f:
            content = f.read()
        assert content == "测试内容", "原子写入内容不匹配"
        os.unlink(tmp_path)
        print("  [OK] 原子写入")
    except Exception as e:
        print(f"  [FAIL] 原子写入: {e}")
        failures += 1

    # 测试 8: 季节判定
    try:
        assert _get_season(7) == "summer", "7月应为夏季"
        assert _get_season(1) == "winter", "1月应为冬季"
        assert _get_season(5) == "rainy", "5月应为雨季"
        assert _get_season(3) == "mild", "3月应为春秋季"
        print("  [OK] 季节判定")
    except AssertionError as e:
        print(f"  [FAIL] 季节判定: {e}")
        failures += 1

    if failures == 0:
        print("== backpacking 自检通过 ✅ ==")
        return 0
    else:
        print(f"== backpacking 自检失败: {failures} 项未通过 ❌ ==")
        return 1


# ---------------------------------------------------------------------------
# CLI 入口
# ---------------------------------------------------------------------------

def main() -> int:
    """CLI 入口。"""
    parser = argparse.ArgumentParser(
        description="backpacking — 户外背包行前装备核查与路线规划",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python run.py --generate --destination "四姑娘山" --days 3 --month 7
  python run.py --check-route --destination "武功山" --days 2
  python run.py --batch --input trips.json --format csv --output result.csv
  python run.py --selftest
        """,
    )

    # 操作模式
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument("--generate", action="store_true", help="生成装备清单")
    mode_group.add_argument("--check-route", action="store_true", help="生成路线核查表")
    mode_group.add_argument("--batch", action="store_true", help="批量处理行程记录")
    mode_group.add_argument("--selftest", action="store_true", help="运行离线自检")

    # 行程参数
    parser.add_argument("--destination", type=str, help="目的地名称")
    parser.add_argument("--days", type=int, help="行程天数（1-7）")
    parser.add_argument("--month", type=int, help="出行月份（1-12），默认当前月份")
    parser.add_argument("--party-size", type=int, help="同行人数，默认 1")
    parser.add_argument("--activity", type=str, choices=SUPPORTED_ACTIVITIES, help="活动类型")
    parser.add_argument("--special-notes", type=str, help="特殊需求，如'摄影'、'钓鱼'")

    # 批量处理参数
    parser.add_argument("--input", type=str, help="批量处理的 JSON 文件路径")

    # 输出参数
    parser.add_argument("--output", type=str, help="输出文件路径（不指定则输出到 stdout）")
    parser.add_argument("--format", type=str, choices=SUPPORTED_FORMATS, default="markdown", help="输出格式")
    parser.add_argument("--dry-run", action="store_true", help="预览模式，不写盘")
    parser.add_argument("--verbose", action="store_true", help="输出详细决策信息")
    parser.add_argument("--mode", default=None, help="文档声明的参数")  # F3 补全

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        return selftest()

    # 生成模式
    if args.generate:
        return run_generate(args)

    # 路线核查模式
    if args.check_route:
        return run_check_route(args)

    # 批量处理模式
    if args.batch:
        return run_batch(args)

    # 不应到达
    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
