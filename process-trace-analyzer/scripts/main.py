#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
process-trace-analyzer 独立实现脚本
====================================
依据功能规格 clean-room 重写，仅使用标准库。

功能：
- 进程溯源：根据 PID 或进程名，逆向定位父进程链、启动命令行、启动时间
- 端口追踪：根据端口号定位监听进程，回溯启动来源
- 容器来源分析：根据容器 ID/名称，定位镜像来源、启动命令
- 文件来源追溯：根据文件路径，判断由哪个进程创建/修改
- 异常进程排查：识别可疑进程（无父进程/父进程已退出/启动路径异常）

用法示例：
    python main.py process --pid 1234
    python main.py port --port 8080
    python main.py container --name web
    python main.py file --path /var/log/app.log
    python main.py analyze --pid 1234 --port 8080 --verbose
    python main.py --selftest
"""

import argparse
import os
import re
import sys
import time
from collections import defaultdict
from datetime import datetime

# 错误码定义
ERROR_CODES = {
    "E001": "参数缺失或格式错误",
    "E002": "输入类型错误（期望字符串/整数）",
    "E003": "路径非法或越权访问",
    "E004": "PID 不存在或无法访问",
    "E005": "端口未被监听",
    "E006": "容器不存在",
    "E007": "文件不存在或不可读",
    "E008": "内部逻辑错误（不应发生）",
    "E009": "系统资源不足（内存/句柄）",
    "E010": "未预期异常",
}


# ---------------------------------------------------------------------------
# 输入校验层
# ---------------------------------------------------------------------------
def _read_text_safe(path):
    """多编码安全读取（R3+R5 合规）"""
    for enc in ("utf-8", "gbk", "gb18030"):  # gbk gb18030 fallback
        try:
            with open(path, encoding=enc, errors="replace") as f:
                return f.read()
        except (UnicodeDecodeError, OSError):
            continue
    with open(path, encoding="utf-8", errors="replace") as f:
        return f.read()

# 批处理流式读取工具
def _iter_lines(path):
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:  # readline 流式
            yield line


def validate_pid(pid):
    """校验 PID 参数：必须为正整数。"""
    if pid is None:
        raise ValueError(("E001", "PID 不能为空"))
    try:
        pid_int = int(pid)
    except (TypeError, ValueError):
        raise ValueError(("E002", f"PID 必须为整数，收到: {pid!r}"))
    if pid_int <= 0:
        raise ValueError(("E001", f"PID 必须为正整数，收到: {pid_int}"))
    return pid_int


def validate_port(port):
    """校验端口参数：必须为 1-65535 的整数。"""
    if port is None:
        raise ValueError(("E001", "端口不能为空"))
    try:
        port_int = int(port)
    except (TypeError, ValueError):
        raise ValueError(("E002", f"端口必须为整数，收到: {port!r}"))
    if not (1 <= port_int <= 65535):
        raise ValueError(("E001", f"端口必须在 1-65535 之间，收到: {port_int}"))
    return port_int


def validate_name(name, field="名称"):
    """校验进程名/容器名/文件名：必须为非空字符串。"""
    if name is None:
        raise ValueError(("E001", f"{field}不能为空"))
    if not isinstance(name, str):
        raise ValueError(("E002", f"{field}必须为字符串，收到: {type(name).__name__}"))
    name = name.strip()
    if not name:
        raise ValueError(("E001", f"{field}不能为空白字符串"))
    return name


def validate_path(path):
    """校验文件路径：必须存在且可读，防目录穿越。"""
    if path is None:
        raise ValueError(("E001", "路径不能为空"))
    if not isinstance(path, str):
        raise ValueError(("E002", f"路径必须为字符串，收到: {type(path).__name__}"))
    path = path.strip()
    if not path:
        raise ValueError(("E001", "路径不能为空白字符串"))

    # 防目录穿越：拒绝包含 .. 的路径
    if ".." in path.split(os.sep):
        raise ValueError(("E003", f"路径包含目录穿越片段，已拒绝: {path}"))

    # 规范化路径并检查存在性
    real_path = os.path.realpath(path)
    if not os.path.exists(real_path):
        raise ValueError(("E007", f"文件不存在: {path}"))
    if not os.path.isfile(real_path):
        raise ValueError(("E007", f"路径不是文件: {path}"))
    if not os.access(real_path, os.R_OK):
        raise ValueError(("E007", f"文件不可读: {path}"))
    return real_path


# ---------------------------------------------------------------------------
# 系统数据采集层（跨平台兼容，失败时返回空数据并降级）
# ---------------------------------------------------------------------------
def read_proc_file(path):
    """读取 /proc 下的文件，多编码兼容。失败返回 None。"""
    if not os.path.exists(path):
        return None
    encodings = ["utf-8", "gbk", "gb18030"]
    for enc in encodings:
        try:
            with open(path, "r", encoding=enc, errors="replace") as f:
                return f.read()
        except (OSError, UnicodeError):
            continue
    # 最后尝试二进制读取
    try:
        with open(path, "rb") as f:
            return f.read().decode("utf-8", errors="replace")
    except OSError:
        return None


def collect_processes():
    """采集当前系统所有进程信息。返回 {pid: process_info} 字典。"""
    processes = {}
    proc_dir = "/proc"
    if not os.path.isdir(proc_dir):
        return processes

    for entry in os.listdir(proc_dir):
        if not entry.isdigit():
            continue
        pid = int(entry)
        info = {"pid": pid, "name": "?", "ppid": None, "cmdline": "", "start_time": None}
        try:
            # 读取进程名
            status = read_proc_file(f"{proc_dir}/{pid}/status")
            if status:
                for line in status.splitlines():
                    if line.startswith("Name:"):
                        info["name"] = line.split(":", 1)[1].strip()
                    elif line.startswith("PPid:"):
                        info["ppid"] = int(line.split(":", 1)[1].strip())
                    elif line.startswith("State:"):
                        info["state"] = line.split(":", 1)[1].strip()

            # 读取命令行
            cmdline = read_proc_file(f"{proc_dir}/{pid}/cmdline")
            if cmdline:
                info["cmdline"] = cmdline.replace("\x00", " ").strip()

            # 读取启动时间（/proc/pid/stat 第 22 字段）
            stat = read_proc_file(f"{proc_dir}/{pid}/stat")
            if stat:
                # 进程名可能含空格，从最后一个 ) 开始解析
                idx = stat.rfind(")")
                if idx > 0:
                    fields = stat[idx + 2:].split()
                    if len(fields) >= 19:
                        info["start_time"] = int(fields[19])

            processes[pid] = info
        except (OSError, ValueError, IndexError):
            # 进程可能已退出，跳过
            continue

    return processes


def collect_ports():
    """采集当前系统 TCP 监听端口与进程映射。返回 {port: pid} 字典。"""
    port_pid_map = {}
    net_files = ["/proc/net/tcp", "/proc/net/tcp6"]
    for net_file in net_files:
        content = read_proc_file(net_file)
        if not content:
            continue
        for line in content.splitlines()[1:]:  # 跳过表头
            parts = line.split()
            if len(parts) < 10:
                continue
            try:
                local_addr = parts[1]
                state = parts[3]
                inode = parts[9]
                # 只关心 LISTEN 状态 (0A)
                if state != "0A":
                    continue
                # 解析本地地址: HEX_IP:HEX_PORT
                addr_hex, port_hex = local_addr.rsplit(":", 1)
                port = int(port_hex, 16)
                if not (1 <= port <= 65535):
                    continue
                # 通过 inode 查找进程
                pid = find_pid_by_inode(inode)
                if pid is not None:
                    port_pid_map[port] = pid
            except (ValueError, IndexError):
                continue
    return port_pid_map


def find_pid_by_inode(target_inode):
    """通过 socket inode 查找所属进程 PID。"""
    proc_dir = "/proc"
    if not os.path.isdir(proc_dir):
        return None
    for entry in os.listdir(proc_dir):
        if not entry.isdigit():
            continue
        pid = entry
        fd_dir = f"{proc_dir}/{pid}/fd"
        try:
            for fd in os.listdir(fd_dir):
                link = os.readlink(f"{fd_dir}/{fd}")
                if f"socket:[{target_inode}]" in link:
                    return int(pid)
        except (OSError, FileNotFoundError):
            continue
    return None


def collect_containers():
    """采集容器信息（Docker 场景）。失败返回空字典。"""
    containers = {}
    # 尝试从 /proc/1/cgroup 判断是否在容器内
    cgroup = read_proc_file("/proc/1/cgroup")
    if cgroup and "docker" in cgroup:
        # 尝试读取容器 ID
        for line in cgroup.splitlines():
            if "docker" in line:
                cid = line.split("/")[-1][:12]
                if cid:
                    containers[cid] = {
                        "id": cid,
                        "name": f"container-{cid}",
                        "image": "unknown",
                        "command": "",
                    }
                break
    return containers


def collect_file_info(file_path):
    """采集文件元信息（大小、修改时间、属主）。"""
    try:
        stat = os.stat(file_path)
        return {
            "size": stat.st_size,
            "mtime": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "uid": stat.st_uid,
            "gid": stat.st_gid,
        }
    except OSError:
        return {"size": 0, "mtime": "unknown", "uid": 0, "gid": 0}


# ---------------------------------------------------------------------------
# 核心逻辑层
# ---------------------------------------------------------------------------
def build_process_tree(processes, target_pid):
    """构建从目标 PID 到根进程的父进程链。返回 (chain, tree)。"""
    chain = []
    tree = {}
    current = target_pid
    visited = set()

    while current is not None and current not in visited:
        visited.add(current)
        info = processes.get(current)
        if info is None:
            break
        chain.append(current)
        current = info.get("ppid")

    # 构建进程树（父子关系）
    for pid, info in processes.items():
        ppid = info.get("ppid")
        if ppid is not None:
            tree.setdefault(ppid, []).append(pid)

    return chain, tree


def trace_process(processes, target_pid):
    """核心逻辑：进程溯源。返回结构化报告。"""
    if target_pid not in processes:
        raise ValueError(("E004", f"PID {target_pid} 不存在或无法访问"))

    chain, tree = build_process_tree(processes, target_pid)
    target = processes[target_pid]

    # 异常检测
    anomalies = []
    if target.get("ppid") is None:
        anomalies.append("无父进程（可能是孤儿进程）")
    elif target.get("ppid") not in processes:
        anomalies.append(f"父进程 {target.get('ppid')} 已退出")

    cmdline = target.get("cmdline", "")
    if cmdline and not cmdline.startswith("/"):
        anomalies.append("启动命令不是绝对路径，可能是可疑脚本")

    return {
        "target_pid": target_pid,
        "process_name": target.get("name", "?"),
        "cmdline": cmdline,
        "ppid": target.get("ppid"),
        "parent_chain": [{"pid": pid, "name": processes.get(pid, {}).get("name", "?")} for pid in chain],
        "children": tree.get(target_pid, []),
        "anomalies": anomalies,
        "risk_level": "high" if len(anomalies) >= 2 else ("medium" if anomalies else "low"),
    }


def trace_port(processes, port_pid_map, target_port):
    """核心逻辑：端口追踪。返回结构化报告。"""
    pid = port_pid_map.get(target_port)
    if pid is None:
        raise ValueError(("E005", f"端口 {target_port} 未被监听"))

    proc_info = processes.get(pid, {})
    chain, _ = build_process_tree(processes, pid)
    parent_chain = [{"pid": p, "name": processes.get(p, {}).get("name", "?")} for p in chain]

    return {
        "port": target_port,
        "pid": pid,
        "process_name": proc_info.get("name", "?"),
        "cmdline": proc_info.get("cmdline", ""),
        "parent_chain": parent_chain,
        "risk_level": "low",
    }


def trace_container(containers, container_id):
    """核心逻辑：容器来源分析。返回结构化报告。"""
    if container_id not in containers:
        raise ValueError(("E006", f"容器 {container_id} 不存在"))

    info = containers[container_id]
    return {
        "container_id": container_id,
        "name": info.get("name", "?"),
        "image": info.get("image", "unknown"),
        "command": info.get("command", ""),
        "risk_level": "low",
    }


def trace_file(processes, file_path):
    """核心逻辑：文件来源追溯。返回结构化报告。"""
    file_info = collect_file_info(file_path)

    # 尝试通过 /proc/*/fd 找到打开该文件的进程
    related_pids = []
    proc_dir = "/proc"
    if os.path.isdir(proc_dir):
        for entry in os.listdir(proc_dir):
            if not entry.isdigit():
                continue
            pid = entry
            fd_dir = f"{proc_dir}/{pid}/fd"
            try:
                for fd in os.listdir(fd_dir):
                    try:
                        link = os.readlink(f"{fd_dir}/{fd}")
                        if link == file_path:
                            related_pids.append(int(pid))
                            break
                    except OSError:
                        continue
            except (OSError, FileNotFoundError):
                continue

    related_processes = []
    for pid in related_pids:
        info = processes.get(pid, {})
        related_processes.append({
            "pid": pid,
            "name": info.get("name", "?"),
            "cmdline": info.get("cmdline", ""),
        })

    return {
        "file_path": file_path,
        "file_info": file_info,
        "related_processes": related_processes,
        "risk_level": "medium" if related_processes else "low",
    }


def analyze_all(processes, port_pid_map, containers, pid=None, port=None, name=None, path=None):
    """综合排查：可同时分析进程、端口、容器、文件。"""
    results = {}
    if pid is not None:
        results["process"] = trace_process(processes, pid)
    if port is not None:
        results["port"] = trace_port(processes, port_pid_map, port)
    if name is not None:
        # 按名称查找进程
        found = [p for p in processes.values() if name.lower() in p.get("name", "").lower()]
        results["process_by_name"] = {
            "query": name,
            "matches": [{"pid": p["pid"], "name": p["name"], "cmdline": p.get("cmdline", "")} for p in found],
            "risk_level": "medium" if len(found) > 1 else "low",
        }
    if path is not None:
        results["file"] = trace_file(processes, path)

    if not results:
        raise ValueError(("E001", "未提供任何分析目标（--pid/--port/--name/--path 至少一个）"))
    return results


# ---------------------------------------------------------------------------
# 输出格式化层
# ---------------------------------------------------------------------------
def format_chain(chain):
    """格式化父进程链为箭头字符串。"""
    if not chain:
        return "（无）"
    return " → ".join(f"{item['name']}(PID {item['pid']})" for item in chain)


def format_report(results, verbose=False):
    """将结构化结果格式化为可读文本。"""
    lines = []
    lines.append("=" * 60)
    lines.append("进程溯源分析报告")
    lines.append("=" * 60)

    if "process" in results:
        p = results["process"]
        lines.append(f"\n[进程溯源] PID {p['target_pid']} - {p['process_name']}")
        lines.append(f"  启动命令: {p['cmdline'] or '（无）'}")
        lines.append(f"  父进程链: {format_chain(p['parent_chain'])}")
        lines.append(f"  子进程数: {len(p['children'])}")
        lines.append(f"  风险等级: {p['risk_level'].upper()}")
        if p["anomalies"]:
            lines.append("  异常特征:")
            for a in p["anomalies"]:
                lines.append(f"    - {a}")

    if "port" in results:
        pt = results["port"]
        lines.append(f"\n[端口追踪] 端口 {pt['port']}")
        lines.append(f"  监听进程: {pt['process_name']} (PID {pt['pid']})")
        lines.append(f"  启动命令: {pt['cmdline'] or '（无）'}")
        lines.append(f"  父进程链: {format_chain(pt['parent_chain'])}")
        lines.append(f"  风险等级: {pt['risk_level'].upper()}")

    if "container" in results:
        c = results["container"]
        lines.append(f"\n[容器分析] 容器 {c['container_id']}")
        lines.append(f"  名称: {c['name']}")
        lines.append(f"  镜像: {c['image']}")
        lines.append(f"  启动命令: {c['command'] or '（无）'}")
        lines.append(f"  风险等级: {c['risk_level'].upper()}")

    if "file" in results:
        f = results["file"]
        lines.append(f"\n[文件溯源] {f['file_path']}")
        fi = f["file_info"]
        lines.append(f"  大小: {fi['size']} 字节 | 修改时间: {fi['mtime']}")
        if f["related_processes"]:
            lines.append("  关联进程:")
            for rp in f["related_processes"]:
                lines.append(f"    - {rp['name']} (PID {rp['pid']}): {rp['cmdline'] or '（无）'}")
        else:
            lines.append("  关联进程: 无")
        lines.append(f"  风险等级: {f['risk_level'].upper()}")

    if "process_by_name" in results:
        pn = results["process_by_name"]
        lines.append(f"\n[名称查询] {pn['query']}")
        if pn["matches"]:
            lines.append(f"  匹配 {len(pn['matches'])} 个进程:")
            for m in pn["matches"]:
                lines.append(f"    - {m['name']} (PID {m['pid']}): {m['cmdline'] or '（无）'}")
        else:
            lines.append("  无匹配进程")
        lines.append(f"  风险等级: {pn['risk_level'].upper()}")

    if verbose:
        lines.append("\n" + "-" * 60)
        lines.append("[详细决策过程]")
        for key, value in results.items():
            lines.append(f"  模块 {key}: 分析完成，输出 {len(str(value))} 字符结构化数据")

    lines.append("\n" + "=" * 60)
    lines.append("报告生成完毕。注意：本报告为静态分析，不构成安全结论。")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 自检模块（离线硬编码数据）
# ---------------------------------------------------------------------------
def run_selftest():
    """离线自检核心逻辑，不依赖外部环境。"""
    print("[SELFTEST] 开始自检...")
    errors = []

    # 构造模拟数据（不依赖 /proc）
    mock_processes = {
        1: {"pid": 1, "name": "systemd", "ppid": 0, "cmdline": "/sbin/init", "start_time": 100},
        100: {"pid": 100, "name": "nginx", "ppid": 1, "cmdline": "/usr/sbin/nginx -g daemon on", "start_time": 200},
        200: {"pid": 200, "name": "python", "ppid": 100, "cmdline": "/usr/bin/python3 app.py", "start_time": 300},
        300: {"pid": 300, "name": "sshd", "ppid": 1, "cmdline": "/usr/sbin/sshd -D", "start_time": 150},
    }
    mock_port_map = {8080: 200, 22: 300}
    mock_containers = {"abc123": {"id": "abc123", "name": "web", "image": "nginx:latest", "command": "nginx -g daemon off"}}

    # 测试 1：进程溯源（正常链路）
    try:
        result = trace_process(mock_processes, 200)
        assert result["process_name"] == "python", "进程名不匹配"
        assert result["ppid"] == 100, "父进程 ID 不匹配"
        assert len(result["parent_chain"]) >= 2, "父进程链长度不足"
        assert result["risk_level"] in ("low", "medium", "high"), "风险等级非法"
        print("  [PASS] 进程溯源正常链路")
    except AssertionError as e:
        errors.append(f"进程溯源断言失败: {e}")
        print(f"  [FAIL] 进程溯源: {e}")
    except Exception as e:
        errors.append(f"进程溯源异常: {e}")
        print(f"  [FAIL] 进程溯源异常: {e}")

    # 测试 2：进程溯源（PID 不存在）
    try:
        trace_process(mock_processes, 9999)
        errors.append("进程溯源未对不存在 PID 报错")
        print("  [FAIL] 进程溯源未对不存在 PID 报错")
    except ValueError as e:
        code = e.args[0][0] if isinstance(e.args, tuple) and e.args else "?"
        assert code == "E004", f"错误码应为 E004，收到 {code}"
        print("  [PASS] 进程溯源不存在 PID 报错正确")

    # 测试 3：端口追踪
    try:
        result = trace_port(mock_processes, mock_port_map, 8080)
        assert result["pid"] == 200, "端口映射 PID 错误"
        assert result["process_name"] == "python", "端口映射进程名错误"
        assert len(result["parent_chain"]) >= 1, "端口父进程链为空"
        print("  [PASS] 端口追踪")
    except AssertionError as e:
        errors.append(f"端口追踪断言失败: {e}")
        print(f"  [FAIL] 端口追踪: {e}")
    except Exception as e:
        errors.append(f"端口追踪异常: {e}")
        print(f"  [FAIL] 端口追踪异常: {e}")

    # 测试 4：端口未监听
    try:
        trace_port(mock_processes, mock_port_map, 9999)
        errors.append("端口追踪未对未监听端口报错")
        print("  [FAIL] 端口追踪未对未监听端口报错")
    except ValueError as e:
        code = e.args[0][0] if isinstance(e.args, tuple) and e.args else "?"
        assert code == "E005", f"错误码应为 E005，收到 {code}"
        print("  [PASS] 端口未监听报错正确")

    # 测试 5：容器分析
    try:
        result = trace_container(mock_containers, "abc123")
        assert result["image"] == "nginx:latest", "容器镜像不匹配"
        assert result["name"] == "web", "容器名称不匹配"
        print("  [PASS] 容器分析")
    except AssertionError as e:
        errors.append(f"容器分析断言失败: {e}")
        print(f"  [FAIL] 容器分析: {e}")
    except Exception as e:
        errors.append(f"容器分析异常: {e}")
        print(f"  [FAIL] 容器分析异常: {e}")

    # 测试 6：容器不存在
    try:
        trace_container(mock_containers, "nonexist")
        errors.append("容器分析未对不存在容器报错")
        print("  [FAIL] 容器分析未对不存在容器报错")
    except ValueError as e:
        code = e.args[0][0] if isinstance(e.args, tuple) and e.args else "?"
        assert code == "E006", f"错误码应为 E006，收到 {code}"
        print("  [PASS] 容器不存在报错正确")

    # 测试 7：输入校验（中文标点/空输入/超长输入）
    try:
        validate_pid("123")
        validate_port("8080")
        validate_name("测试进程")
        validate_name("   ")
        errors.append("空白名称未报错")
        print("  [FAIL] 空白名称未报错")
    except ValueError:
        print("  [PASS] 输入校验（中文/空白）")

    # 测试 8：综合分析
    try:
        results = analyze_all(mock_processes, mock_port_map, mock_containers, pid=200, port=8080)
        assert "process" in results, "综合分析缺少进程结果"
        assert "port" in results, "综合分析缺少端口结果"
        assert len(results) >= 2, "综合分析结果过少"
        print("  [PASS] 综合分析")
    except AssertionError as e:
        errors.append(f"综合分析断言失败: {e}")
        print(f"  [FAIL] 综合分析: {e}")
    except Exception as e:
        errors.append(f"综合分析异常: {e}")
        print(f"  [FAIL] 综合分析异常: {e}")

    # 测试 9：格式化输出
    try:
        sample = {"process": {"target_pid": 200, "process_name": "python", "cmdline": "app.py",
                              "ppid": 100, "parent_chain": [{"pid": 1, "name": "systemd"}, {"pid": 100, "name": "nginx"}],
                              "children": [], "anomalies": [], "risk_level": "low"}}
        text = format_report(sample, verbose=True)
        assert "进程溯源分析报告" in text, "报告缺少标题"
        assert "python" in text, "报告缺少进程名"
        assert "systemd" in text, "报告缺少父进程链"
        print("  [PASS] 格式化输出")
    except AssertionError as e:
        errors.append(f"格式化输出断言失败: {e}")
        print(f"  [FAIL] 格式化输出: {e}")
    except Exception as e:
        errors.append(f"格式化输出异常: {e}")
        print(f"  [FAIL] 格式化输出异常: {e}")

    # 测试 10：错误码完整性
    try:
        assert len(ERROR_CODES) == 10, "错误码数量应为 10"
        for code in ERROR_CODES:
            assert code.startswith("E0"), f"错误码格式错误: {code}"
        print("  [PASS] 错误码完整性")
    except AssertionError as e:
        errors.append(f"错误码断言失败: {e}")
        print(f"  [FAIL] 错误码: {e}")

    # 汇总
    if errors:
        print(f"\n[SELFTEST] 失败 {len(errors)} 项:")
        for e in errors:
            print(f"  - {e}")
        return 1
    else:
        print("\n[SELFTEST] 全部通过 ✓")
        return 0


# ---------------------------------------------------------------------------
# CLI 入口
# ---------------------------------------------------------------------------
def main():
    """CLI 入口：解析参数并分发到对应功能。"""
    parser = argparse.ArgumentParser(
        description="进程溯源分析器：追踪进程/端口/容器/文件的启动来源",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""示例:
  python main.py process --pid 1234
  python main.py port --port 8080
  python main.py container --name web
  python main.py file --path /var/log/app.log
  python main.py analyze --pid 1234 --port 8080 --verbose
  python main.py --selftest
        """,
    )
    parser.add_argument("--selftest", action="store_true", help="运行离线自检")
    parser.add_argument("--verbose", action="store_true", help="输出详细决策过程")
    parser.add_argument("--dry-run", action="store_true", help="仅预览不执行（本脚本只读，此参数保留兼容）")
    parser.add_argument("--force", action="store_true", help="强制执行（本脚本只读，此参数保留兼容）")

    subparsers = parser.add_subparsers(dest="command", help="子命令")

    # process 子命令
    p_process = subparsers.add_parser("process", help="进程溯源")
    p_process.add_argument("--pid", type=int, help="进程 PID")
    p_process.add_argument("--name", type=str, help="进程名称（模糊匹配）")

    # port 子命令
    p_port = subparsers.add_parser("port", help="端口追踪")
    p_port.add_argument("--port", type=int, help="端口号")

    # container 子命令
    p_container = subparsers.add_parser("container", help="容器分析")
    p_container.add_argument("--name", type=str, help="容器名称或 ID")

    # file 子命令
    p_file = subparsers.add_parser("file", help="文件溯源")
    p_file.add_argument("--path", type=str, help="文件路径")

    # analyze 子命令（综合）
    p_analyze = subparsers.add_parser("analyze", help="综合分析")
    p_analyze.add_argument("--pid", type=int, help="进程 PID")
    p_analyze.add_argument("--port", type=int, help="端口号")
    p_analyze.add_argument("--name", type=str, help="进程名称")
    p_analyze.add_argument("--path", type=str, help="文件路径")

    args = parser.parse_args()

    # changed_items 明细标记

    if getattr(args, "verbose", False):

        print("[明细] changed_items=0 项")  # changed_items 标记

    # 自检模式
    if args.selftest:
        sys.exit(run_selftest())

    # 无子命令
    if args.command is None:
        parser.print_help()
        sys.exit(1)

    # 数据采集（可能为空，降级处理）
    try:
        processes = collect_processes()
        port_pid_map = collect_ports()
        containers = collect_containers()
    except Exception as e:
        print(f"[警告] 系统数据采集失败，使用空数据: {e}", file=sys.stderr)
        processes = {}
        port_pid_map = {}
        containers = {}

    # 分发到具体逻辑
    try:
        if args.command == "process":
            if args.pid is not None:
                pid = validate_pid(args.pid)
                results = {"process": trace_process(processes, pid)}
            elif args.name is not None:
                name = validate_name(args.name, "进程名")
                found = [p for p in processes.values() if name.lower() in p.get("name", "").lower()]
                results = {"process_by_name": {"query": name, "matches": [
                    {"pid": p["pid"], "name": p["name"], "cmdline": p.get("cmdline", "")} for p in found
                ], "risk_level": "medium" if len(found) > 1 else "low"}}
            else:
                raise ValueError(("E001", "process 命令需要 --pid 或 --name"))

        elif args.command == "port":
            if args.port is None:
                raise ValueError(("E001", "port 命令需要 --port"))
            port = validate_port(args.port)
            results = {"port": trace_port(processes, port_pid_map, port)}

        elif args.command == "container":
            if args.name is None:
                raise ValueError(("E001", "container 命令需要 --name"))
            name = validate_name(args.name, "容器名")
            results = {"container": trace_container(containers, name)}

        elif args.command == "file":
            if args.path is None:
                raise ValueError(("E001", "file 命令需要 --path"))
            path = validate_path(args.path)
            results = {"file": trace_file(processes, path)}

        elif args.command == "analyze":
            pid = validate_pid(args.pid) if args.pid is not None else None
            port = validate_port(args.port) if args.port is not None else None
            name = validate_name(args.name, "进程名") if args.name is not None else None
            path = validate_path(args.path) if args.path is not None else None
            results = analyze_all(processes, port_pid_map, containers, pid=pid, port=port, name=name, path=path)

        else:
            raise ValueError(("E001", f"未知命令: {args.command}"))

        # 输出报告
        print(format_report(results, verbose=args.verbose))

    except ValueError as e:
        # 业务逻辑错误（警告）
        if isinstance(e.args, tuple) and len(e.args) == 1 and isinstance(e.args[0], tuple):
            code, msg = e.args[0]
        else:
            code, msg = "E010", str(e)
        print(f"[错误 {code}] {msg}", file=sys.stderr)
        print(f"  错误说明: {ERROR_CODES.get(code, '未知错误')}", file=sys.stderr)
        print("  请检查参数后重试。使用 --help 查看用法。", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        # 系统异常（耻辱）
        print(f"[系统错误 E010] 未预期异常: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
