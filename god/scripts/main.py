#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
未命名工具 - Ruby process monitor
基于功能规格的独立实现（clean-room）
"""

import argparse
import json
import os
import re
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# 错误码体系
# ============================================================
ERROR_CODES = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：输入来源、输出格式、期望完整度",
    "E003": "输入格式不符合要求，示例：文件路径、URL、或明文数据",
    "E004": "这超出了本工具的能力范围，建议：检查输入类型或拆分任务",
    "E005": "结果无法确定，建议：提供更多上下文或重新描述需求",
    "E006": "内部逻辑错误：数据解析失败",
    "E007": "内部逻辑错误：输出生成失败",
    "E008": "内部逻辑错误：自检断言失败",
    "E009": "内部逻辑错误：文件读写失败",
    "E010": "内部逻辑错误：未知异常",
}


class SkillError(Exception):
    """技能运行期异常，携带错误码"""

    def __init__(self, code: str, message: str = ""):
        self.code = code
        self.message = message or ERROR_CODES.get(code, "未知错误")
        super().__init__(f"[{code}] {self.message}")


# ============================================================
# 核心数据结构
# ============================================================
class ProcessInfo:
    """进程信息结构体"""

    def __init__(self, pid: int, name: str, cpu: float, memory: float, state: str):
        self.pid = pid
        self.name = name
        self.cpu = cpu          # CPU使用率 0-100
        self.memory = memory    # 内存使用率 0-100
        self.state = state      # running/sleeping/zombie 等

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pid": self.pid,
            "name": self.name,
            "cpu": round(self.cpu, 1),
            "memory": round(self.memory, 1),
            "state": self.state,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProcessInfo":
        return cls(
            pid=int(data["pid"]),
            name=str(data["name"]),
            cpu=float(data["cpu"]),
            memory=float(data["memory"]),
            state=str(data["state"]),
        )


class MonitorResult:
    """监控结果容器"""

    def __init__(self, timestamp: str, processes: List[ProcessInfo]):
        self.timestamp = timestamp
        self.processes = processes

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "process_count": len(self.processes),
            "processes": [p.to_dict() for p in self.processes],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MonitorResult":
        return cls(
            timestamp=str(data["timestamp"]),
            processes=[ProcessInfo.from_dict(p) for p in data["processes"]],
        )


# ============================================================
# 核心处理函数
# ============================================================
def parse_input(raw_input: str) -> Tuple[str, List[str]]:
    """
    解析用户输入，识别输入来源类型
    
    返回: (来源类型, 内容列表)
    来源类型: "text" / "file" / "url" / "invalid"
    """
    if not raw_input or not raw_input.strip():
        raise SkillError("E001")
    
    content = raw_input.strip()
    
    # 检查是否为文件路径
    if os.path.isfile(content):
        try:
            with open(content, "r", encoding="utf-8") as f:
                lines = [line.strip() for line in f if line.strip()]
            return "file", lines
        except Exception:
            raise SkillError("E009")
    
    # 检查是否为URL
    url_pattern = re.compile(r'^https?://[^\s]+$', re.IGNORECASE)
    if url_pattern.match(content):
        # 本技能不访问网络，返回提示
        raise SkillError("E004", "URL输入需要网络访问，本工具离线运行，请提供本地数据")
    
    # 按行拆分文本数据
    lines = [line.strip() for line in content.split('\n') if line.strip()]
    if not lines:
        raise SkillError("E001")
    
    return "text", lines


def parse_process_lines(lines: List[str]) -> List[ProcessInfo]:
    """
    从文本行解析进程信息
    
    支持格式：
    - "pid name cpu memory state" 空格分隔
    - "pid|name|cpu|memory|state" 管道分隔
    """
    processes = []
    
    for line in lines:
        # 尝试多种分隔符
        parts = None
        for sep in ['|', ',', '\t', ' ']:
            parts = [p.strip() for p in line.split(sep) if p.strip()]
            if len(parts) >= 5:
                break
        
        if not parts or len(parts) < 5:
            # 尝试更灵活的分隔符处理
            parts = re.split(r'[\s|,]+', line.strip())
            parts = [p for p in parts if p]
            if len(parts) < 5:
                raise SkillError("E003", f"无法解析行: {line}")
        
        try:
            pid = int(parts[0])
            name = parts[1]
            cpu = float(parts[2].replace('%', '').replace(',', '.'))
            memory = float(parts[3].replace('%', '').replace(',', '.'))
            state = parts[4]
            
            # 数据范围检查
            if cpu < 0 or cpu > 1000:  # 允许一定的误差范围
                raise ValueError("CPU使用率超出合理范围")
            if memory < 0 or memory > 100:
                raise ValueError("内存使用率超出合理范围")
                
        except (ValueError, IndexError) as e:
            raise SkillError("E006", f"数据格式错误: {line} - {str(e)}")
        
        processes.append(ProcessInfo(pid, name, cpu, memory, state))
    
    if not processes:
        raise SkillError("E001")
    
    return processes


def analyze_processes(processes: List[ProcessInfo]) -> Dict[str, Any]:
    """
    分析进程数据，生成统计信息
    """
    if not processes:
        raise SkillError("E001")
    
    total_cpu = sum(p.cpu for p in processes)
    total_memory = sum(p.memory for p in processes)
    
    # CPU使用率排名
    cpu_sorted = sorted(processes, key=lambda p: p.cpu, reverse=True)
    
    # 内存使用率排名
    memory_sorted = sorted(processes, key=lambda p: p.memory, reverse=True)
    
    # 状态统计
    state_counts: Dict[str, int] = {}
    for p in processes:
        state_counts[p.state] = state_counts.get(p.state, 0) + 1
    
    # 置信度评估 - 改进版
    confidence = 100.0  # 初始置信度
    uncertain_items = []
    
    # CPU使用率检查
    if total_cpu > 100:
        # 多核系统可能超过100%，但需要提示
        confidence -= 10
        uncertain_items.append("CPU使用率总和超过100%，可能为多核系统")
    
    # 内存使用率检查
    if total_memory > 100:
        confidence -= 20
        uncertain_items.append("内存使用率总和超过100%，数据可能不准确")
    
    # 进程状态检查
    valid_states = {"running", "sleeping", "stopped", "zombie", "idle", "waiting"}
    unknown_states = [p.state for p in processes if p.state not in valid_states]
    if unknown_states:
        confidence -= 5
        uncertain_items.append(f"存在未识别的进程状态: {', '.join(set(unknown_states))}")
    
    # 数据完整性检查
    if any(p.cpu < 0 or p.memory < 0 for p in processes):
        confidence -= 10
        uncertain_items.append("存在负值数据，可能不准确")
    
    # 进程数量检查
    if len(processes) < 2:
        confidence -= 5
        uncertain_items.append("进程数量较少，统计可能不具代表性")
    
    # 确保置信度在合理范围
    confidence = max(0.0, min(100.0, confidence))
    
    return {
        "process_count": len(processes),
        "total_cpu": round(total_cpu, 1),
        "total_memory": round(total_memory, 1),
        "cpu_top3": [p.to_dict() for p in cpu_sorted[:3]],
        "memory_top3": [p.to_dict() for p in memory_sorted[:3]],
        "state_distribution": state_counts,
        "confidence": round(confidence, 1),
        "uncertain_items": uncertain_items,
    }


def generate_output(result: MonitorResult, analysis: Dict[str, Any], output_format: str = "json") -> str:
    """
    按指定格式生成输出
    """
    if output_format not in ("json", "text", "table"):
        raise SkillError("E003", f"不支持的输出格式: {output_format}")
    
    try:
        if output_format == "json":
            return json.dumps({
                "result": result.to_dict(),
                "analysis": analysis,
            }, ensure_ascii=False, indent=2)
        
        elif output_format == "text":
            lines = [
                f"时间戳: {result.timestamp}",
                f"进程数: {analysis['process_count']}",
                f"总CPU: {analysis['total_cpu']}%",
                f"总内存: {analysis['total_memory']}%",
                "",
                "Top CPU进程:",
            ]
            for p in analysis.get("cpu_top3", []):
                lines.append(f"  PID {p['pid']} {p['name']}: {p['cpu']}%")
            
            lines.extend(["", "Top 内存进程:"])
            for p in analysis.get("memory_top3", []):
                lines.append(f"  PID {p['pid']} {p['name']}: {p['memory']}%")
            
            lines.extend(["", f"置信度: {analysis['confidence']}%"])
            
            if analysis.get("uncertain_items"):
                lines.extend(["", "注意:"])
                for item in analysis["uncertain_items"]:
                    lines.append(f"  - {item}")
            
            return "\n".join(lines)
        
        else:  # table
            header = f"{'PID':<8} {'名称':<20} {'CPU%':<8} {'内存%':<8} {'状态':<10}"
            sep = "-" * 60
            lines = [header, sep]
            
            for p in result.processes:
                lines.append(f"{p.pid:<8} {p.name:<20} {p.cpu:<8.1f} {p.memory:<8.1f} {p.state:<10}")
            
            lines.extend([sep, f"统计: {analysis['process_count']}个进程, 置信度{analysis['confidence']}%"])
            return "\n".join(lines)
    
    except Exception as e:
        raise SkillError("E007", f"输出生成失败: {str(e)}")


def process_input(raw_input: str, output_format: str = "json") -> Dict[str, Any]:
    """主处理流程"""
    # Step 1: 收集最小信息集
    if not raw_input:
        raise SkillError("E002")
    
    # Step 2: 执行核心流程
    source_type, lines = parse_input(raw_input)
    processes = parse_process_lines(lines)
    analysis = analyze_processes(processes)
    
    # 生成时间戳和结果
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    result = MonitorResult(timestamp, processes)
    
    # Step 3: 输出与校验
    output = generate_output(result, analysis, output_format)
    
    return {
        "source_type": source_type,
        "output": output,
        "analysis": analysis,
        "result": result,
    }


# ============================================================
# 自检模块
# ============================================================
def run_selftest() -> bool:
    """
    离线自检核心逻辑
    使用内置硬编码样例数据，不依赖外部文件或网络
    """
    print("开始自检...")
    
    # 内置测试数据
    test_data = "\n".join([
        "1234 nginx 12.5 8.3 running",
        "5678 ruby 45.2 30.1 running",
        "9012 postgres 3.1 15.7 sleeping",
        "3456 redis 0.5 2.4 sleeping",
        "7890 sidekiq 78.9 45.6 running",
        "2345 worker 1.2 5.5 zombie",
    ])
    
    # Test 1: 解析输入
    try:
        source_type, lines = parse_input(test_data)
        assert source_type == "text", "输入类型应为text"
        assert len(lines) == 6, f"应解析出6行，实际{len(lines)}行"
        print("  [通过] 输入解析")
    except AssertionError as e:
        print(f"  [失败] 输入解析: {e}")
        return False
    except SkillError as e:
        print(f"  [失败] 输入解析异常: {e}")
        return False
    
    # Test 2: 进程解析
    try:
        processes = parse_process_lines(lines)
        assert len(processes) == 6, "应解析出6个进程"
        assert processes[0].pid == 1234, "第一个进程PID应为1234"
        assert processes[1].name == "ruby", "第二个进程名称应为ruby"
        print("  [通过] 进程解析")
    except (AssertionError, SkillError) as e:
        print(f"  [失败] 进程解析: {e}")
        return False
    
    # Test 3: 统计分析
    try:
        analysis = analyze_processes(processes)
        assert analysis["process_count"] == 6, "进程数应为6"
        assert analysis["total_cpu"] > 0, "总CPU应大于0"
        assert analysis["total_memory"] > 0, "总内存应大于0"
        assert len(analysis["cpu_top3"]) == 3, "应返回Top3 CPU"
        assert len(analysis["memory_top3"]) == 3, "应返回Top3内存"
        assert analysis["confidence"] > 0, "置信度应大于0"
        assert analysis["confidence"] <= 100, "置信度不应超过100"
        print(f"  [通过] 统计分析 (置信度: {analysis['confidence']}%)")
    except (AssertionError, SkillError) as e:
        print(f"  [失败] 统计分析: {e}")
        return False
    
    # Test 4: 输出生成
    try:
        result = MonitorResult("2026-01-01 00:00:00", processes)
        json_output = generate_output(result, analysis, "json")
        text_output = generate_output(result, analysis, "text")
        table_output = generate_output(result, analysis, "table")
        
        assert json_output.startswith("{"), "JSON输出应以{开头"
        assert "进程" in text_output or "进程" in table_output, "文本输出应包含进程信息"
        assert "PID" in table_output, "表格输出应包含PID列"
        print("  [通过] 输出生成 (json/text/table)")
    except (AssertionError, SkillError) as e:
        print(f"  [失败] 输出生成: {e}")
        return False
    
    # Test 5: 完整流程
    try:
        result = process_input(test_data, "json")
        assert result["source_type"] == "text", "完整流程输入类型应为text"
        assert "output" in result, "完整流程应包含输出"
        assert "result" in result, "完整流程应包含结果对象"
        print("  [通过] 完整流程")
    except (AssertionError, SkillError) as e:
        print(f"  [失败] 完整流程: {e}")
        return False
    
    # Test 6: 错误处理
    try:
        process_input("")
        print("  [失败] 空输入应抛出E001")
        return False
    except SkillError as e:
        assert e.code == "E001", f"空输入错误码应为E001，实际{e.code}"
        print("  [通过] 错误处理 (E001)")
    
    try:
        process_input("1234 nginx 12.5 8.3")  # 缺少state字段
        print("  [失败] 格式错误应抛出E003")
        return False
    except SkillError as e:
        assert e.code in ("E003", "E006"), f"格式错误码应为E003或E006，实际{e.code}"
        print(f"  [通过] 错误处理 ({e.code})")
    
    # Test 7: 异常输入
    try:
        process_input("not a valid input at all")
        print("  [失败] 无效输入应抛出异常")
        return False
    except SkillError:
        print("  [通过] 异常输入处理")
    
    # Test 8: 边界情况 - 单进程
    try:
        single_process = "9999 test 50.0 25.0 running"
        lines = parse_input(single_process)[1]
        processes = parse_process_lines(lines)
        assert len(processes) == 1, "应解析出1个进程"
        analysis = analyze_processes(processes)
        assert analysis["process_count"] == 1, "进程数应为1"
        assert analysis["confidence"] < 100, "单进程置信度应低于100"
        print(f"  [通过] 边界情况测试 (单进程, 置信度: {analysis['confidence']}%)")
    except (AssertionError, SkillError) as e:
        print(f"  [失败] 边界情况测试: {e}")
        return False
    
    print("\n所有自检通过！")
    return True


# ============================================================
# 主入口
# ============================================================
def main():
    parser = argparse.ArgumentParser(
        description="未命名工具 - Ruby process monitor",
        epilog="示例: python main.py --input '1234 nginx 12.5 8.3 running' --format json"
    )
    parser.add_argument(
        "--input", "-i",
        help="输入数据：明文文本、文件路径、或URL（URL不支持）"
    )
    parser.add_argument(
        "--file", "-f",
        help="从文件读取输入（替代--input）"
    )
    parser.add_argument(
        "--format", "-fmt",
        choices=["json", "text", "table"],
        default="json",
        help="输出格式 (默认: json)"
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行离线自检"
    )
    
    args = parser.parse_args()
    
    # 自检模式
    if args.selftest:
        success = run_selftest()
        sys.exit(0 if success else 1)
    
    # 收集输入
    raw_input = args.input
    if args.file:
        try:
            with open(args.file, "r", encoding="utf-8") as f:
                raw_input = f.read()
        except Exception:
            print(f"错误 [E009]: 无法读取文件 {args.file}")
            sys.exit(1)
    
    if not raw_input:
        print("错误 [E002]: 请提供输入数据，使用 --input 或 --file 参数")
        print("示例: python main.py --input '1234 nginx 12.5 8.3 running'")
        sys.exit(1)
    
    # 处理输入
    try:
        result = process_input(raw_input, args.format)
        print(result["output"])
    except SkillError as e:
        print(f"错误 [{e.code}]: {e.message}")
        sys.exit(1)
    except Exception as e:
        print(f"错误 [E010]: 未知异常: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
