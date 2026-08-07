#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
flowstatecli - 开发专注流会话追踪与目标管理工具

本脚本根据功能规格独立实现（clean-room），仅使用 Python 标准库。
支持命令行解析、会话数据解析、关键信息提取、目标进度汇总、置信度标注与批量处理。
包含 --selftest 参数，使用内置硬编码样例离线自检核心逻辑。
"""

import argparse
import json
import re
import sys
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

# 错误码定义
ERROR_CODES = {
    "E001": "参数错误：缺少必要参数或参数格式不正确",
    "E002": "输入格式错误：无法解析输入文本",
    "E003": "日期格式错误：日期应为 YYYY-MM-DD",
    "E004": "时间格式错误：时间应为 HH:MM（24小时制）",
    "E005": "会话时间段无效：结束时间早于开始时间",
    "E006": "任务ID格式错误：应为 # 后跟数字",
    "E007": "目标数据格式错误：目标结构不完整",
    "E008": "批量处理失败：输入数据包含无法解析的记录",
    "E009": "文件读取失败：无法读取指定文件",
    "E010": "内部逻辑错误：发生未预期的异常",
}


def _err(code: str) -> str:
    """根据错误码返回错误信息字符串。"""
    return f"[{code}] {ERROR_CODES.get(code, '未知错误')}"


def _parse_time(time_str: str) -> Optional[datetime]:
    """解析 HH:MM 格式的时间字符串，返回 datetime 对象（日期部分固定为 2000-01-01）。"""
    try:
        return datetime.strptime(time_str.strip(), "%H:%M")
    except (ValueError, TypeError):
        return None


def parse_session_line(line: str, line_num: int = 1) -> Dict[str, Any]:
    """
    解析单行会话记录文本。
    支持格式示例：
      "2024-01-15 09:30-11:45 重构登录模块"
      "2024-01-15 09:30-11:45 重构登录模块 (高优先级)"
    返回结构化会话字典。
    """
    line = line.strip()
    if not line:
        raise ValueError(_err("E002"))

    # 匹配日期
    date_match = re.match(r"^(\d{4}-\d{2}-\d{2})\s+", line)
    if not date_match:
        raise ValueError(_err("E003"))
    date_str = date_match.group(1)

    # 验证日期合法性
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        raise ValueError(_err("E003"))

    # 匹配时间段
    rest = line[date_match.end():]
    time_match = re.match(r"^(\d{2}:\d{2})\s*-\s*(\d{2}:\d{2})\s+(.*)$", rest)
    if not time_match:
        raise ValueError(_err("E004"))

    start_str, end_str, task_part = time_match.groups()

    start_dt = _parse_time(start_str)
    end_dt = _parse_time(end_str)
    if start_dt is None or end_dt is None:
        raise ValueError(_err("E004"))

    # 计算时长（分钟）
    if end_dt < start_dt:
        # 跨天情况：增加一天
        end_dt += timedelta(days=1)
    duration_min = int((end_dt - start_dt).total_seconds() // 60)
    if duration_min <= 0:
        raise ValueError(_err("E005"))

    # 解析任务名称与优先级标记
    task_name = task_part.strip()
    priority = "unset"
    priority_match = re.search(r"\(([^)]*优先级)\)\s*$", task_name)
    if priority_match:
        prio_text = priority_match.group(1)
        if "高" in prio_text:
            priority = "high"
        elif "中" in prio_text:
            priority = "medium"
        elif "低" in prio_text:
            priority = "low"
        task_name = task_name[:priority_match.start()].strip()

    session_id = f"S{line_num:03d}"

    return {
        "session_id": session_id,
        "date": date_str,
        "start": start_str,
        "end": end_str,
        "duration_min": duration_min,
        "task": task_name,
        "priority": priority,
    }


def extract_key_info(text: str) -> Dict[str, Any]:
    """
    从非结构化文本中提取关键信息。
    支持识别：任务ID（#数字）、类型（bugfix/feature/docs等）、耗时（小时）、关联文件。
    """
    result: Dict[str, Any] = {
        "task_id": None,
        "type": "unset",
        "duration_h": None,
        "files": [],
        "priority": "unset",
    }

    # 提取任务ID
    task_id_match = re.search(r"#(\d+)", text)
    if task_id_match:
        result["task_id"] = f"#{task_id_match.group(1)}"

    # 提取类型关键词（使用原文，保持大小写不敏感匹配）
    type_keywords = {
        "bugfix": ["bug", "修复", "fix", "defect"],
        "feature": ["功能", "新特性", "feature", "开发"],
        "docs": ["文档", "doc", "readme"],
        "refactor": ["重构", "refactor", "优化"],
        "test": ["测试", "test", "单元测试"],
    }
    lower_text = text.lower()
    for type_name, keywords in type_keywords.items():
        if any(kw in lower_text for kw in keywords):
            result["type"] = type_name
            break

    # 提取耗时（小时），支持格式：X小时 / Xh / X小时X分钟
    duration_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:小时|h|hour)", lower_text)
    if duration_match:
        result["duration_h"] = float(duration_match.group(1))
    else:
        # 尝试 "X小时Y分钟" 格式
        hours_match = re.search(r"(\d+)\s*小时", lower_text)
        minutes_match = re.search(r"(\d+)\s*分钟", lower_text)
        if hours_match or minutes_match:
            hours = int(hours_match.group(1)) if hours_match else 0
            minutes = int(minutes_match.group(1)) if minutes_match else 0
            if hours > 0 or minutes > 0:
                result["duration_h"] = hours + minutes / 60.0

    # 提取关联文件（使用原文保持大小写，.py, .js, .ts, .css, .html, .md, .json 等）
    file_pattern = re.compile(r'[\w\-]+\.(?:py|js|ts|css|html|md|json|txt|yml|yaml|toml|ini|cfg|sh|bat)')
    files_found = file_pattern.findall(text)
    result["files"] = list(set(files_found))  # 去重

    # 置信度标注：根据提取到的信息量计算
    confidence = 0.3  # 基础置信度
    if result["task_id"]:
        confidence += 0.2
    if result["duration_h"] is not None:
        confidence += 0.2
    if result["files"]:
        confidence += 0.15
    if result["type"] != "unset":
        confidence += 0.15
    result["confidence"] = round(min(confidence, 0.95), 2)

    return result


def aggregate_goal_progress(sessions: List[Dict[str, Any]], target_hours: float) -> Dict[str, Any]:
    """
    根据会话记录汇总目标进度。
    sessions: 会话记录列表
    target_hours: 目标总时长（小时）
    返回包含总时长、目标、进度百分比的结果。
    """
    if target_hours <= 0:
        raise ValueError(_err("E007"))

    total_minutes = sum(s.get("duration_min", 0) for s in sessions)
    total_hours = total_minutes / 60.0
    progress_pct = min(100.0, round(total_hours / target_hours * 100, 1))

    # 提取目标名称（取第一个会话的任务名作为目标名）
    goal_name = "未命名目标"
    if sessions and sessions[0].get("task"):
        goal_name = sessions[0]["task"]

    return {
        "goal": goal_name,
        "total_hours": round(total_hours, 2),
        "target_hours": target_hours,
        "progress_pct": progress_pct,
    }


def batch_process(lines: List[str]) -> List[Dict[str, Any]]:
    """批量处理多行会话记录，返回结构化结果列表。"""
    results = []
    for i, line in enumerate(lines, start=1):
        try:
            parsed = parse_session_line(line, line_num=i)
            results.append(parsed)
        except ValueError as e:
            raise ValueError(f"{_err('E008')} 第{i}行: {e}")
    return results


def run_selftest() -> bool:
    """内置硬编码样例数据离线自检核心逻辑。不读外部文件、不访问网络。"""
    print("=== flowstatecli 自检开始 ===")

    # --- 测试1: 会话数据解析 ---
    test_line = "2024-01-15 09:30-11:45 重构登录模块"
    try:
        parsed = parse_session_line(test_line, line_num=1)
        assert parsed["date"] == "2024-01-15", "日期解析错误"
        assert parsed["start"] == "09:30", "开始时间解析错误"
        assert parsed["end"] == "11:45", "结束时间解析错误"
        assert parsed["duration_min"] > 100 and parsed["duration_min"] < 200, "时长计算异常"
        assert "重构" in parsed["task"], "任务名解析错误"
        assert parsed["priority"] == "unset", "默认优先级应为 unset"
        print("[PASS] 会话数据解析")
    except AssertionError as e:
        print(f"[FAIL] 会话数据解析: {e}")
        return False

    # --- 测试2: 关键信息提取 ---
    test_text = "下午修了#42 bug，花了2小时，涉及auth.py"
    try:
        info = extract_key_info(test_text)
        assert info["task_id"] == "#42", "任务ID提取错误"
        assert info["type"] == "bugfix", "类型识别错误"
        assert info["duration_h"] is not None and 1.0 < info["duration_h"] < 3.0, "耗时提取异常"
        assert "auth.py" in info["files"], "文件提取错误"
        assert info["confidence"] >= 0.5, "置信度计算异常"
        print("[PASS] 关键信息提取")
    except AssertionError as e:
        print(f"[FAIL] 关键信息提取: {e}")
        return False

    # --- 测试3: 目标进度汇总 ---
    sessions = [
        {"task": "完成API文档", "duration_min": 120},
        {"task": "完成API文档", "duration_min": 180},
        {"task": "完成API文档", "duration_min": 90},
    ]
    try:
        progress = aggregate_goal_progress(sessions, target_hours=10)
        assert progress["total_hours"] > 5.0 and progress["total_hours"] < 8.0, "总时长计算异常"
        assert progress["progress_pct"] > 50 and progress["progress_pct"] < 80, "进度百分比异常"
        assert progress["goal"] == "完成API文档", "目标名称错误"
        print("[PASS] 目标进度汇总")
    except AssertionError as e:
        print(f"[FAIL] 目标进度汇总: {e}")
        return False

    # --- 测试4: 批量处理 ---
    batch_lines = [
        "2024-01-15 09:30-11:45 重构登录模块",
        "2024-01-16 10:00-12:00 编写单元测试",
        "2024-01-17 14:00-16:30 修复#42 bug",
    ]
    try:
        batch_results = batch_process(batch_lines)
        assert len(batch_results) == 3, "批量处理数量错误"
        assert all(r["session_id"] for r in batch_results), "会话ID缺失"
        assert all(r["duration_min"] > 0 for r in batch_results), "存在无效时长"
        print("[PASS] 批量处理")
    except (ValueError, AssertionError) as e:
        print(f"[FAIL] 批量处理: {e}")
        return False

    # --- 测试5: 边界情况（错误处理） ---
    try:
        # 无效日期
        parse_session_line("2024-13-45 09:30-11:45 测试", line_num=1)
        print("[FAIL] 错误处理: 应拒绝无效日期")
        return False
    except ValueError:
        pass

    try:
        # 结束时间早于开始时间
        parse_session_line("2024-01-15 11:45-09:30 测试", line_num=1)
        print("[FAIL] 错误处理: 应拒绝时间倒置")
        return False
    except ValueError:
        pass

    try:
        # 缺少时间
        parse_session_line("2024-01-15 测试", line_num=1)
        print("[FAIL] 错误处理: 应拒绝缺少时间")
        return False
    except ValueError:
        pass

    print("[PASS] 错误处理")

    # --- 测试6: 跨天会话 ---
    try:
        cross_day = parse_session_line("2024-01-15 23:30-01:45 夜间部署", line_num=1)
        assert cross_day["duration_min"] > 100 and cross_day["duration_min"] < 200, "跨天时长计算异常"
        print("[PASS] 跨天会话处理")
    except (ValueError, AssertionError) as e:
        print(f"[FAIL] 跨天会话处理: {e}")
        return False

    print("=== flowstatecli 自检全部通过 ===")
    return True


def main() -> int:
    """命令行入口函数。"""
    parser = argparse.ArgumentParser(
        description="flowstatecli - 开发专注流会话追踪与目标管理工具",
        epilog="示例: python main.py --parse '2024-01-15 09:30-11:45 重构登录模块'"
    )
    parser.add_argument(
        "--parse", 
        metavar="TEXT", 
        help="解析单行会话记录文本"
    )
    parser.add_argument(
        "--extract", 
        metavar="TEXT", 
        help="从非结构化文本中提取关键信息"
    )
    parser.add_argument(
        "--aggregate", 
        nargs=2, 
        metavar=("SESSIONS_JSON", "TARGET_HOURS"),
        help="汇总目标进度，参数1为会话JSON数组，参数2为目标小时数"
    )
    parser.add_argument(
        "--batch", 
        metavar="FILE", 
        help="批量处理文件（每行一条会话记录）"
    )
    parser.add_argument(
        "--selftest", 
        action="store_true", 
        help="运行内置自检（不读外部文件、不访问网络）"
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        success = run_selftest()
        return 0 if success else 1

    # 无参数时显示帮助
    if not (args.parse or args.extract or args.aggregate or args.batch):
        parser.print_help()
        return 0

    try:
        # 单行解析
        if args.parse:
            result = parse_session_line(args.parse, line_num=1)
            print(json.dumps(result, ensure_ascii=False, indent=2))

        # 关键信息提取
        if args.extract:
            result = extract_key_info(args.extract)
            print(json.dumps(result, ensure_ascii=False, indent=2))

        # 目标进度汇总
        if args.aggregate:
            try:
                sessions_data = json.loads(args.aggregate[0])
                target = float(args.aggregate[1])
            except (json.JSONDecodeError, ValueError):
                raise ValueError(_err("E007"))
            if not isinstance(sessions_data, list):
                raise ValueError(_err("E007"))
            result = aggregate_goal_progress(sessions_data, target)
            print(json.dumps(result, ensure_ascii=False, indent=2))

        # 批量处理
        if args.batch:
            try:
                with open(args.batch, "r", encoding="utf-8") as f:
                    lines = [line.strip() for line in f if line.strip()]
            except (IOError, OSError):
                raise ValueError(_err("E009"))
            results = batch_process(lines)
            print(json.dumps(results, ensure_ascii=False, indent=2))

    except ValueError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"{_err('E010')}: {e}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
