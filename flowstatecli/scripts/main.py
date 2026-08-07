#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
flowstatecli - 开发专注流会话追踪与目标管理工具

本脚本为 clean-room 独立实现，仅依据功能规格编写。
核心功能：解析工作日志文本、提取关键信息、汇总目标进度、标注置信度。
支持命令行批量处理与离线自检（--selftest）。
"""

import argparse
import csv
import json
import os
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# 错误码定义
ERROR_CODES = {
    "E001": "输入文件不存在或无法读取",
    "E002": "输入格式不支持（仅支持 txt/json/csv/md）",
    "E003": "JSON 解析失败",
    "E004": "CSV 解析失败",
    "E005": "时间格式无法解析",
    "E006": "会话数据无效（缺少必要字段）",
    "E007": "目标数据无效",
    "E008": "输出目录无法写入",
    "E009": "命令行参数错误",
    "E010": "内部逻辑错误（未知异常）",
}

# 置信度常量
CONFIDENCE_HIGH = 0.90
CONFIDENCE_MEDIUM = 0.70
CONFIDENCE_LOW = 0.40


def err_exit(code: str, detail: str = "") -> None:
    """打印错误信息并以非零状态退出"""
    msg = ERROR_CODES.get(code, "未知错误")
    if detail:
        msg = f"{msg}: {detail}"
    print(f"[错误 {code}] {msg}", file=sys.stderr)
    sys.exit(1)


class SessionParser:
    """会话数据解析器：将原始文本转换为结构化会话记录"""

    # 时间范围模式：如 "09:30-11:45" 或 "9:30-11:45"
    TIME_RANGE_PATTERN = re.compile(
        r"(\d{1,2}):(\d{2})\s*[-~至]\s*(\d{1,2}):(\d{2})"
    )
    # 日期模式：如 "2024-01-15" 或 "2024/01/15" 或 "01-15"
    DATE_PATTERN = re.compile(r"(\d{4})[-/](\d{1,2})[-/](\d{1,2})")
    # 会话前缀：如 "S001" 或 "会话1"
    SESSION_ID_PATTERN = re.compile(r"(?:S|会话)[-_]?(\d+)", re.IGNORECASE)

    def parse_line(self, line: str, line_num: int = 1) -> Dict[str, Any]:
        """
        解析单行工作日志文本，提取会话信息。
        支持格式示例：
          "2024-01-15 09:30-11:45 重构登录模块"
          "2024-01-15 09:30-11:45 重构登录模块 #42 涉及auth.py"
        """
        line = line.strip()
        if not line:
            raise ValueError("空行无法解析")

        # 提取日期
        date_match = self.DATE_PATTERN.search(line)
        if not date_match:
            raise ValueError("未找到日期")
        year, month, day = date_match.groups()
        date_str = f"{int(year):04d}-{int(month):02d}-{int(day):02d}"

        # 提取时间范围
        time_match = self.TIME_RANGE_PATTERN.search(line)
        if not time_match:
            raise ValueError("未找到时间范围")
        start_h, start_m, end_h, end_m = time_match.groups()
        start_str = f"{int(start_h):02d}:{int(start_m):02d}"
        end_str = f"{int(end_h):02d}:{int(end_m):02d}"

        # 计算时长（分钟）
        try:
            start_dt = datetime.strptime(f"{date_str} {start_str}", "%Y-%m-%d %H:%M")
            end_dt = datetime.strptime(f"{date_str} {end_str}", "%Y-%m-%d %H:%M")
            if end_dt < start_dt:
                # 跨天情况，加一天
                end_dt += timedelta(days=1)
            duration_min = int((end_dt - start_dt).total_seconds() / 60)
            if duration_min <= 0:
                raise ValueError("时长必须为正数")
        except ValueError as e:
            raise ValueError(f"时间计算失败: {e}")

        # 提取会话ID（如果有）
        session_id_match = self.SESSION_ID_PATTERN.search(line)
        session_id = f"S{session_id_match.group(1)}" if session_id_match else f"S{line_num:03d}"

        # 提取任务描述（去除日期、时间、ID后的剩余文本）
        task_text = line
        task_text = self.DATE_PATTERN.sub("", task_text)
        task_text = self.TIME_RANGE_PATTERN.sub("", task_text)
        task_text = self.SESSION_ID_PATTERN.sub("", task_text)
        # 清理多余空格和分隔符
        task_text = re.sub(r"\s+", " ", task_text).strip()
        task_text = task_text.strip("-~至")

        # 提取关联文件（如 .py, .js, .ts, .md 等）
        files = re.findall(r"[\w\-./]+\.(?:py|js|ts|jsx|tsx|md|json|css|html|go|rs|java|c|cpp|h)", task_text, re.IGNORECASE)

        # 提取任务ID（如 #42, #BUG-123）
        task_id_match = re.search(r"#([\w\-]+)", task_text)
        task_id = f"#{task_id_match.group(1)}" if task_id_match else None

        # 提取类型关键词
        type_map = {
            "bug": "bugfix", "修复": "bugfix", "fix": "bugfix",
            "重构": "refactor", "refactor": "refactor",
            "测试": "test", "test": "test",
            "文档": "docs", "doc": "docs",
            "功能": "feature", "feature": "feature", "开发": "feature",
        }
        session_type = "unset"
        for keyword, type_val in type_map.items():
            if keyword.lower() in task_text.lower():
                session_type = type_val
                break

        # 提取优先级关键词
        priority_keywords = {
            "high": ["紧急", "高优", "urgent", "high", "critical"],
            "medium": ["中优", "medium", "normal"],
            "low": ["低优", "low", "minor"],
        }
        priority = "unset"
        for prio, keywords in priority_keywords.items():
            for kw in keywords:
                if kw.lower() in task_text.lower():
                    priority = prio
                    break
            if priority != "unset":
                break

        return {
            "session_id": session_id,
            "date": date_str,
            "start": start_str,
            "end": end_str,
            "duration_min": duration_min,
            "task": task_text if task_text else "[未命名任务]",
            "task_id": task_id,
            "type": session_type,
            "priority": priority,
            "files": files,
            "confidence": self._calc_confidence(task_text, files, task_id),
        }

    def _calc_confidence(self, task: str, files: List[str], task_id: Optional[str]) -> float:
        """计算解析置信度"""
        confidence = CONFIDENCE_HIGH
        if not task or task == "[未命名任务]":
            confidence -= 0.3
        if not files:
            confidence -= 0.1
        if not task_id:
            confidence -= 0.1
        return max(confidence, CONFIDENCE_LOW)

    def parse_batch(self, lines: List[str]) -> List[Dict[str, Any]]:
        """批量解析多行文本"""
        sessions = []
        for i, line in enumerate(lines, 1):
            line = line.strip()
            if not line or line.startswith("#") or line.startswith("//"):
                continue
            try:
                sessions.append(self.parse_line(line, i))
            except ValueError as e:
                # 单行解析失败不中断整体，记录错误信息
                sessions.append({
                    "session_id": f"S{i:03d}",
                    "error": str(e),
                    "raw": line,
                    "confidence": CONFIDENCE_LOW,
                })
        return sessions


class InfoExtractor:
    """关键信息提取器：从非结构化文本中提取任务要素"""

    # 时间模式：如 "2小时", "1.5h", "30分钟"
    DURATION_PATTERN = re.compile(
        r"(\d+(?:\.\d+)?)\s*(?:小时|h|hr|hrs|分钟|min|mins|m)", re.IGNORECASE
    )
    # 文件模式
    FILE_PATTERN = re.compile(r"[\w\-./]+\.(?:py|js|ts|jsx|tsx|md|json|css|html|go|rs|java|c|cpp|h)", re.IGNORECASE)
    # 任务ID模式
    TASK_ID_PATTERN = re.compile(r"#([\w\-]+)")
    # 优先级关键词
    PRIORITY_HIGH = ["紧急", "高优", "urgent", "high", "critical"]
    PRIORITY_MEDIUM = ["中优", "medium", "normal"]
    PRIORITY_LOW = ["低优", "low", "minor"]

    def extract(self, text: str) -> Dict[str, Any]:
        """从非结构化文本中提取关键信息"""
        text_lower = text.lower()
        result: Dict[str, Any] = {}

        # 提取任务ID
        task_id_match = self.TASK_ID_PATTERN.search(text)
        if task_id_match:
            result["task_id"] = f"#{task_id_match.group(1)}"
        else:
            result["task_id"] = None

        # 提取时长（小时）
        duration_match = self.DURATION_PATTERN.search(text)
        if duration_match:
            value = float(duration_match.group(1))
            unit = duration_match.group(2).lower()
            if unit in ("分钟", "min", "mins", "m"):
                result["duration_h"] = value / 60.0
            else:
                result["duration_h"] = value
        else:
            result["duration_h"] = None

        # 提取关联文件
        result["files"] = list(set(self.FILE_PATTERN.findall(text)))

        # 判断类型
        type_map = {
            "bug": "bugfix", "修复": "bugfix",
            "重构": "refactor",
            "测试": "test",
            "文档": "docs",
            "功能": "feature", "开发": "feature",
        }
        result["type"] = "unset"
        for keyword, type_val in type_map.items():
            if keyword in text_lower:
                result["type"] = type_val
                break

        # 判断优先级
        result["priority"] = "unset"
        for kw in self.PRIORITY_HIGH:
            if kw in text_lower:
                result["priority"] = "high"
                break
        if result["priority"] == "unset":
            for kw in self.PRIORITY_MEDIUM:
                if kw in text_lower:
                    result["priority"] = "medium"
                    break
        if result["priority"] == "unset":
            for kw in self.PRIORITY_LOW:
                if kw in text_lower:
                    result["priority"] = "low"
                    break

        # 计算置信度
        confidence = CONFIDENCE_HIGH
        if not result["task_id"]:
            confidence -= 0.2
        if not result["duration_h"]:
            confidence -= 0.2
        if not result["files"]:
            confidence -= 0.1
        if result["priority"] == "unset":
            confidence -= 0.1
        result["confidence"] = max(confidence, CONFIDENCE_LOW)

        return result


class GoalAggregator:
    """目标进度汇总器：按目标维度聚合会话数据"""

    def aggregate(self, sessions: List[Dict[str, Any]], goals: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """将会话记录按目标聚合，输出进度百分比"""
        results = []
        for goal in goals:
            goal_name = goal.get("name", "")
            target_hours = float(goal.get("target_hours", 0))
            if target_hours <= 0:
                raise ValueError(f"目标 '{goal_name}' 的 target_hours 必须为正数")

            # 匹配会话（按任务名称包含目标关键词）
            matched_sessions = []
            for sess in sessions:
                task = sess.get("task", "")
                if goal_name.lower() in task.lower():
                    matched_sessions.append(sess)

            # 计算总时长
            total_min = sum(sess.get("duration_min", 0) for sess in matched_sessions)
            total_hours = total_min / 60.0

            # 计算进度百分比
            progress_pct = min(100.0, (total_hours / target_hours) * 100.0)

            results.append({
                "goal": goal_name,
                "total_hours": round(total_hours, 2),
                "target_hours": target_hours,
                "progress_pct": round(progress_pct, 1),
                "session_count": len(matched_sessions),
                "status": "completed" if progress_pct >= 100 else "in_progress",
            })

        return results


class ConfidenceAnnotator:
    """置信度标注器：对推断字段标注置信度等级"""

    def annotate(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """为数据中的推断字段添加置信度标注"""
        result = dict(data)

        # 为优先级字段标注置信度
        if "priority" in result:
            if result["priority"] == "unset":
                result["priority_confidence"] = CONFIDENCE_LOW
            else:
                result["priority_confidence"] = CONFIDENCE_MEDIUM

        # 为类型字段标注置信度
        if "type" in result:
            if result["type"] == "unset":
                result["type_confidence"] = CONFIDENCE_LOW
            else:
                result["type_confidence"] = CONFIDENCE_MEDIUM

        # 为 task_id 标注置信度
        if "task_id" in result:
            result["task_id_confidence"] = CONFIDENCE_HIGH if result["task_id"] else CONFIDENCE_LOW

        return result


class FileHandler:
    """文件处理器：支持多种格式的读写"""

    SUPPORTED_EXTENSIONS = {".txt", ".json", ".csv", ".md"}

    def read_input(self, filepath: str) -> str:
        """读取输入文件内容"""
        path = Path(filepath)
        if not path.exists():
            err_exit("E001", f"文件不存在: {filepath}")
        if path.suffix.lower() not in self.SUPPORTED_EXTENSIONS:
            err_exit("E002", f"不支持的文件格式: {path.suffix}")

        try:
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            err_exit("E001", str(e))

    def parse_content(self, content: str, filepath: str = "") -> List[Dict[str, Any]]:
        """根据文件类型解析内容为会话记录列表"""
        ext = Path(filepath).suffix.lower() if filepath else ".txt"
        parser = SessionParser()

        if ext in (".txt", ".md"):
            lines = content.splitlines()
            return parser.parse_batch(lines)
        elif ext == ".json":
            try:
                data = json.loads(content)
                if isinstance(data, list):
                    return data
                elif isinstance(data, dict) and "sessions" in data:
                    return data["sessions"]
                else:
                    raise ValueError("JSON 格式无效")
            except Exception as e:
                err_exit("E003", str(e))
        elif ext == ".csv":
            try:
                reader = csv.DictReader(content.splitlines())
                sessions = []
                for row in reader:
                    sessions.append({
                        "session_id": row.get("session_id", ""),
                        "date": row.get("date", ""),
                        "start": row.get("start", ""),
                        "end": row.get("end", ""),
                        "duration_min": int(row.get("duration_min", 0)),
                        "task": row.get("task", ""),
                    })
                return sessions
            except Exception as e:
                err_exit("E004", str(e))
        else:
            err_exit("E002", f"不支持的文件格式: {ext}")

    def write_output(self, data: List[Dict[str, Any]], output_path: Optional[str] = None) -> str:
        """输出结果到文件或标准输出"""
        json_str = json.dumps(data, ensure_ascii=False, indent=2)

        if output_path:
            try:
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(json_str)
                return f"已写入: {output_path}"
            except Exception as e:
                err_exit("E008", str(e))
        else:
            return json_str


def run_selftest() -> None:
    """离线自检核心逻辑，使用内置硬编码样例数据"""
    print("=== flowstatecli 自检开始 ===")

    # 测试1: 会话数据解析
    parser = SessionParser()
    sample_line = "2024-01-15 09:30-11:45 重构登录模块 #42 涉及auth.py"
    try:
        sess = parser.parse_line(sample_line, 1)
        assert sess["date"] == "2024-01-15", "日期解析错误"
        assert sess["duration_min"] > 100, "时长计算错误"
        assert sess["duration_min"] < 200, "时长计算错误"
        assert "重构" in sess["task"] or "登录" in sess["task"], "任务描述错误"
        assert sess["confidence"] > 0.5, "置信度计算错误"
        print("[PASS] 会话数据解析")
    except AssertionError as e:
        err_exit("E010", f"自检失败 - 会话解析: {e}")

    # 测试2: 批量解析
    sample_lines = [
        "2024-01-15 09:30-11:45 重构登录模块",
        "2024-01-16 14:00-16:00 修复#42 bug 涉及auth.py",
        "2024-01-17 10:00-12:30 编写API文档",
    ]
    sessions = parser.parse_batch(sample_lines)
    assert len(sessions) == 3, "批量解析数量错误"
    assert all("duration_min" in s for s in sessions), "会话缺少时长字段"
    print("[PASS] 批量会话解析")

    # 测试3: 关键信息提取
    extractor = InfoExtractor()
    info = extractor.extract("下午修了#42 bug，花了2小时，涉及auth.py")
    assert info["task_id"] == "#42", "任务ID提取错误"
    assert info["duration_h"] > 1.5, "时长提取错误"
    assert info["duration_h"] < 2.5, "时长提取错误"
    assert "auth.py" in info["files"], "文件提取错误"
    assert info["type"] == "bugfix", "类型判断错误"
    print("[PASS] 关键信息提取")

    # 测试4: 目标进度汇总
    aggregator = GoalAggregator()
    goals = [
        {"name": "登录模块", "target_hours": 10},
        {"name": "API文档", "target_hours": 5},
    ]
    try:
        results = aggregator.aggregate(sessions, goals)
        assert len(results) == 2, "目标聚合数量错误"
        login_goal = [r for r in results if r["goal"] == "登录模块"][0]
        assert login_goal["total_hours"] > 0, "登录模块时长应大于0"
        assert login_goal["progress_pct"] > 0, "进度百分比应大于0"
        assert login_goal["progress_pct"] <= 100, "进度百分比不应超过100"
        print("[PASS] 目标进度汇总")
    except Exception as e:
        err_exit("E010", f"自检失败 - 目标汇总: {e}")

    # 测试5: 置信度标注
    annotator = ConfidenceAnnotator()
    annotated = annotator.annotate({"priority": "high", "type": "bugfix", "task_id": "#42"})
    assert "priority_confidence" in annotated, "缺少优先级置信度"
    assert annotated["priority_confidence"] > 0.5, "优先级置信度错误"
    assert annotated["type_confidence"] > 0.5, "类型置信度错误"
    print("[PASS] 置信度标注")

    # 测试6: 文件处理器（内存模式）
    handler = FileHandler()
    content = "\n".join(sample_lines)
    parsed = handler.parse_content(content)
    assert len(parsed) >= 2, "文件解析数量错误"
    print("[PASS] 文件处理器")

    print("=== 全部自检通过 ===")


def main() -> None:
    """主入口函数"""
    parser = argparse.ArgumentParser(
        description="flowstatecli - 开发专注流会话追踪与目标管理",
        epilog="示例: python main.py --input sessions.txt --output result.json",
    )
    parser.add_argument("--input", "-i", help="输入文件路径（txt/json/csv/md）")
    parser.add_argument("--output", "-o", help="输出文件路径（JSON格式）")
    parser.add_argument("--goals", "-g", help="目标配置文件路径（JSON格式）")
    parser.add_argument("--selftest", action="store_true", help="运行离线自检")
    parser.add_argument("--version", action="version", version="flowstatecli 1.0.1")

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        run_selftest()
        return

    # 参数校验
    if not args.input:
        err_exit("E009", "缺少 --input 参数")

    # 读取输入
    handler = FileHandler()
    content = handler.read_input(args.input)
    sessions = handler.parse_content(content, args.input)

    # 处理目标聚合
    if args.goals:
        try:
            with open(args.goals, "r", encoding="utf-8") as f:
                goals_data = json.load(f)
            if isinstance(goals_data, dict) and "goals" in goals_data:
                goals = goals_data["goals"]
            else:
                goals = goals_data
            aggregator = GoalAggregator()
            results = aggregator.aggregate(sessions, goals)
            output_data = {"sessions": sessions, "goal_progress": results}
        except Exception as e:
            err_exit("E007", str(e))
    else:
        output_data = sessions

    # 输出结果
    result_str = handler.write_output(output_data, args.output)
    if not args.output:
        print(result_str)
    else:
        print(result_str)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:
        err_exit("E010", str(e))
