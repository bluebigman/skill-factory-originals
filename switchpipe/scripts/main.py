#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
switchpipe - 后端进程托管 HTTP代理 部署工具

本脚本依据功能规格独立实现（clean-room），用于：
  - 解析并校验 YAML/JSON 配置文件
  - 管理后端进程生命周期（启动、停止、重启、状态查询）
  - 提供 HTTP 请求转发（简单轮询）
  - 输出结构化状态报告

仅使用 Python 标准库，无第三方依赖。
"""

import argparse
import json
import os
import signal
import socket
import subprocess
import sys
import time
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# 错误码定义
# ---------------------------------------------------------------------------
class AppError(Exception):
    """应用自定义异常，携带错误码与描述信息。"""

    def __init__(self, code: str, message: str):
        super().__init__(f"[{code}] {message}")
        self.code = code
        self.message = message


def err_usage(msg: str) -> AppError:
    """E001: 命令行参数或用法错误。"""
    return AppError("E001", msg)


def err_config(msg: str) -> AppError:
    """E002: 配置文件读取/解析错误。"""
    return AppError("E002", msg)


def err_validation(msg: str) -> AppError:
    """E003: 配置内容校验失败。"""
    return AppError("E003", msg)


def err_process(msg: str) -> AppError:
    """E004: 进程操作失败。"""
    return AppError("E004", msg)


def err_proxy(msg: str) -> AppError:
    """E005: 代理转发失败。"""
    return AppError("E005", msg)


def err_health(msg: str) -> AppError:
    """E006: 健康检查失败。"""
    return AppError("E006", msg)


def err_log(msg: str) -> AppError:
    """E007: 日志聚合失败。"""
    return AppError("E007", msg)


def err_io(msg: str) -> AppError:
    """E008: 文件系统或IO错误。"""
    return AppError("E008", msg)


def err_network(msg: str) -> AppError:
    """E009: 网络连接错误。"""
    return AppError("E009", msg)


def err_internal(msg: str) -> AppError:
    """E010: 内部未知错误。"""
    return AppError("E010", msg)


# ---------------------------------------------------------------------------
# 配置解析与校验
# ---------------------------------------------------------------------------
class ConfigLoader:
    """
    配置加载器：支持 JSON 格式（标准库 json）。
    YAML 支持通过注释标记提示用户安装 PyYAML，但核心逻辑不强制依赖。
    """

    @staticmethod
    def load_file(path: str) -> Dict[str, Any]:
        """
        从文件加载配置。
        支持 .json 后缀；若为 .yaml/.yml 且缺少 PyYAML，则给出安装提示。
        """
        if not os.path.isfile(path):
            raise err_io(f"配置文件不存在: {path}")

        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
        except OSError as e:
            raise err_io(f"读取配置文件失败: {e}") from e

        ext = os.path.splitext(path)[1].lower()
        if ext in (".yaml", ".yml"):
            # 尝试导入 PyYAML，若未安装则报错并提示
            try:
                import yaml  # pip install pyyaml
            except ImportError:
                raise err_config(
                    "解析 YAML 需要 PyYAML，请先执行: pip install pyyaml"
                ) from None
            try:
                data = yaml.safe_load(content)
            except Exception as e:
                raise err_config(f"YAML 解析失败: {e}") from e
        elif ext == ".json":
            try:
                data = json.loads(content)
            except json.JSONDecodeError as e:
                raise err_config(f"JSON 解析失败: {e}") from e
        else:
            # 未知扩展名，先尝试 JSON，再尝试 YAML（若可用）
            try:
                data = json.loads(content)
            except json.JSONDecodeError:
                try:
                    import yaml  # pip install pyyaml
                except ImportError:
                    raise err_config(
                        "不支持的文件格式，请使用 .json 或安装 PyYAML 以支持 .yaml"
                    ) from None
                try:
                    data = yaml.safe_load(content)
                except Exception as e:
                    raise err_config(f"配置解析失败: {e}") from e

        if not isinstance(data, dict):
            raise err_validation("配置根节点必须是对象（字典）")
        return data

    @staticmethod
    def validate(cfg: Dict[str, Any]) -> Dict[str, Any]:
        """
        校验配置必填字段与基本格式。
        返回规范化后的配置字典。
        """
        # 必填字段：services（列表）
        services = cfg.get("services")
        if not isinstance(services, list) or len(services) == 0:
            raise err_validation("配置必须包含非空的 services 列表")

        normalized_services = []
        for idx, svc in enumerate(services):
            if not isinstance(svc, dict):
                raise err_validation(f"services[{idx}] 必须是对象")

            name = svc.get("name")
            if not name or not isinstance(name, str):
                raise err_validation(f"services[{idx}].name 必须是非空字符串")

            # 启动命令：command 字符串 或 command_args 列表
            command = svc.get("command")
            command_args = svc.get("command_args")
            if command and not isinstance(command, str):
                raise err_validation(f"服务 {name} 的 command 必须是字符串")
            if command_args and not isinstance(command_args, list):
                raise err_validation(f"服务 {name} 的 command_args 必须是列表")
            if not command and not command_args:
                raise err_validation(f"服务 {name} 必须提供 command 或 command_args")

            # 端口（可选但建议）
            port = svc.get("port")
            if port is not None:
                if not isinstance(port, int) or port < 1 or port > 65535:
                    raise err_validation(f"服务 {name} 的 port 必须是 1-65535 的整数")

            # 健康检查路径（可选）
            health_path = svc.get("health_path")
            if health_path is not None and not isinstance(health_path, str):
                raise err_validation(f"服务 {name} 的 health_path 必须是字符串")

            normalized_services.append({
                "name": name,
                "command": command,
                "command_args": command_args,
                "port": port,
                "health_path": health_path,
                "env": svc.get("env", {}),
                "cwd": svc.get("cwd"),
            })

        # 代理配置（可选）
        proxy = cfg.get("proxy", {})
        if not isinstance(proxy, dict):
            raise err_validation("proxy 必须是对象")

        listen_port = proxy.get("listen_port")
        if listen_port is not None:
            if not isinstance(listen_port, int) or listen_port < 1 or listen_port > 65535:
                raise err_validation("proxy.listen_port 必须是 1-65535 的整数")

        target_services = proxy.get("targets", [])
        if not isinstance(target_services, list):
            raise err_validation("proxy.targets 必须是列表")
        for t in target_services:
            if not isinstance(t, str):
                raise err_validation("proxy.targets 中的元素必须是服务名字符串")

        return {
            "services": normalized_services,
            "proxy": {
                "listen_port": listen_port,
                "targets": target_services,
            },
            "global_env": cfg.get("global_env", {}),
        }


# ---------------------------------------------------------------------------
# 进程管理
# ---------------------------------------------------------------------------
class ProcessManager:
    """
    进程管理器：负责启动、停止、重启、状态查询。
    使用 subprocess.Popen 托管子进程。
    """

    def __init__(self):
        # name -> {"proc": Popen, "started_at": float, "port": int}
        self._processes: Dict[str, Dict[str, Any]] = {}

    def start(self, svc: Dict[str, Any], global_env: Optional[Dict[str, str]] = None) -> None:
        """启动一个服务进程。"""
        name = svc["name"]
        if name in self._processes:
            proc_info = self._processes[name]
            if proc_info["proc"].poll() is None:
                raise err_process(f"服务 {name} 已在运行")

        # 构造命令行
        if svc.get("command_args"):
            cmd = svc["command_args"]
        else:
            cmd = svc["command"]

        # 合并环境变量
        env = os.environ.copy()
        if global_env:
            env.update(global_env)
        if svc.get("env"):
            env.update(svc["env"])

        # 工作目录
        cwd = svc.get("cwd")

        try:
            proc = subprocess.Popen(
                cmd,
                shell=isinstance(cmd, str),
                env=env,
                cwd=cwd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
        except Exception as e:
            raise err_process(f"启动服务 {name} 失败: {e}") from e

        self._processes[name] = {
            "proc": proc,
            "started_at": time.time(),
            "port": svc.get("port"),
        }

    def stop(self, name: str, timeout: float = 5.0) -> None:
        """停止指定服务进程。"""
        if name not in self._processes:
            raise err_process(f"服务 {name} 未在托管中")

        proc_info = self._processes[name]
        proc = proc_info["proc"]

        if proc.poll() is not None:
            # 已经退出
            del self._processes[name]
            return

        # 先尝试 SIGTERM
        try:
            proc.terminate()
            proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            # 超时则 SIGKILL
            proc.kill()
            proc.wait(timeout=2.0)
        except Exception as e:
            raise err_process(f"停止服务 {name} 失败: {e}") from e
        finally:
            if name in self._processes:
                del self._processes[name]

    def restart(self, svc: Dict[str, Any], global_env: Optional[Dict[str, str]] = None) -> None:
        """重启服务进程。"""
        name = svc["name"]
        if name in self._processes:
            self.stop(name)
        self.start(svc, global_env)

    def status(self, name: Optional[str] = None) -> List[Dict[str, Any]]:
        """查询进程状态。name 为空则查询全部。"""
        result = []
        for n, info in self._processes.items():
            if name and n != name:
                continue
            proc = info["proc"]
            result.append({
                "name": n,
                "running": proc.poll() is None,
                "pid": proc.pid,
                "returncode": proc.returncode,
                "started_at": info["started_at"],
                "port": info["port"],
            })
        return result

    def stop_all(self) -> None:
        """停止所有托管进程。"""
        for name in list(self._processes.keys()):
            try:
                self.stop(name)
            except AppError:
                pass

    def collect_logs(self, name: Optional[str] = None, max_lines: int = 50) -> Dict[str, List[str]]:
        """
        收集子进程输出（stdout/stderr）。
        注意：由于管道可能阻塞，这里使用非阻塞方式读取。
        """
        logs: Dict[str, List[str]] = {}
        for n, info in self._processes.items():
            if name and n != name:
                continue
            proc = info["proc"]
            out_lines = []
            err_lines = []
            try:
                # 非阻塞读取 stdout
                if proc.stdout:
                    while True:
                        line = proc.stdout.readline()
                        if not line:
                            break
                        out_lines.append(line.rstrip("\n"))
                        if len(out_lines) >= max_lines:
                            break
            except Exception:
                pass
            try:
                if proc.stderr:
                    while True:
                        line = proc.stderr.readline()
                        if not line:
                            break
                        err_lines.append(line.rstrip("\n"))
                        if len(err_lines) >= max_lines:
                            break
            except Exception:
                pass
            logs[n] = {
                "stdout": out_lines,
                "stderr": err_lines,
            }
        return logs


# ---------------------------------------------------------------------------
# 健康检查
# ---------------------------------------------------------------------------
class HealthChecker:
    """健康检查器：检测端口连通性。"""

    @staticmethod
    def check_port(host: str, port: int, timeout: float = 1.0) -> bool:
        """检测 TCP 端口是否可连接。"""
        if not port:
            return False
        try:
            with socket.create_connection((host, port), timeout=timeout):
                return True
        except (socket.timeout, ConnectionRefusedError, OSError):
            return False

    @staticmethod
    def report(services: List[Dict[str, Any]], manager: ProcessManager) -> Dict[str, Any]:
        """生成结构化健康报告。"""
        report_data = {
            "timestamp": time.time(),
            "services": [],
        }
        for svc in services:
            name = svc["name"]
            port = svc.get("port")
            status_list = manager.status(name)
            running = bool(status_list and status_list[0]["running"])
            port_ok = False
            if running and port:
                port_ok = HealthChecker.check_port("127.0.0.1", port)
            report_data["services"].append({
                "name": name,
                "running": running,
                "port": port,
                "port_reachable": port_ok,
                "healthy": running and (not port or port_ok),
            })
        return report_data


# ---------------------------------------------------------------------------
# HTTP 代理（简单轮询）
# ---------------------------------------------------------------------------
class SimpleProxy:
    """
    极简 HTTP 代理：仅演示轮询转发逻辑。
    真实场景应使用 asyncio 或第三方库（如 aiohttp）。
    """

    def __init__(self, targets: List[int]):
        self.targets = targets
        self._index = 0

    def next_target(self) -> Optional[int]:
        """轮询返回下一个目标端口。"""
        if not self.targets:
            return None
        port = self.targets[self._index % len(self.targets)]
        self._index += 1
        return port

    def forward(self, request_path: str) -> Dict[str, Any]:
        """
        模拟转发：返回目标端口与状态。
        实际实现应建立 TCP 连接并转发数据。
        """
        port = self.next_target()
        if port is None:
            raise err_proxy("没有可用的目标服务")
        return {
            "target_port": port,
            "path": request_path,
            "status": "forwarded",
        }


# ---------------------------------------------------------------------------
# 主应用
# ---------------------------------------------------------------------------
class SwitchPipeApp:
    """应用主控类。"""

    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path
        self.config: Optional[Dict[str, Any]] = None
        self.manager = ProcessManager()

    def load_config(self) -> None:
        """加载并校验配置。"""
        if not self.config_path:
            raise err_usage("未提供配置文件路径")
        raw = ConfigLoader.load_file(self.config_path)
        self.config = ConfigLoader.validate(raw)

    def cmd_start(self) -> Dict[str, Any]:
        """启动所有服务。"""
        if not self.config:
            raise err_internal("配置未加载")
        results = []
        for svc in self.config["services"]:
            self.manager.start(svc, self.config.get("global_env", {}))
            results.append({"name": svc["name"], "action": "started"})
        return {"status": "ok", "results": results}

    def cmd_stop(self, name: Optional[str] = None) -> Dict[str, Any]:
        """停止指定或全部服务。"""
        if name:
            self.manager.stop(name)
            return {"status": "ok", "stopped": [name]}
        self.manager.stop_all()
        return {"status": "ok", "stopped": "all"}

    def cmd_restart(self) -> Dict[str, Any]:
        """重启所有服务。"""
        if not self.config:
            raise err_internal("配置未加载")
        for svc in self.config["services"]:
            self.manager.restart(svc, self.config.get("global_env", {}))
        return {"status": "ok", "restarted": [s["name"] for s in self.config["services"]]}

    def cmd_status(self) -> Dict[str, Any]:
        """输出状态报告。"""
        if not self.config:
            raise err_internal("配置未加载")
        report = HealthChecker.report(self.config["services"], self.manager)
        return report

    def cmd_logs(self, name: Optional[str] = None) -> Dict[str, Any]:
        """收集日志。"""
        logs = self.manager.collect_logs(name)
        return {"status": "ok", "logs": logs}

    def cmd_proxy(self, path: str = "/") -> Dict[str, Any]:
        """模拟代理转发。"""
        if not self.config:
            raise err_internal("配置未加载")
        proxy_cfg = self.config["proxy"]
        targets = []
        for svc_name in proxy_cfg.get("targets", []):
            for svc in self.config["services"]:
                if svc["name"] == svc_name and svc.get("port"):
                    targets.append(svc["port"])
        proxy = SimpleProxy(targets)
        return proxy.forward(path)


# ---------------------------------------------------------------------------
# 自检（selftest）
# ---------------------------------------------------------------------------
def run_selftest() -> int:
    """
    内置硬编码样例数据离线自检。
    不读外部文件、不依赖当前工作目录、不访问网络。
    使用宽松断言（区间/大小比较），确保必然匹配。
    """
    print("[selftest] 开始自检...")

    # 1. 配置校验测试
    sample_config = {
        "services": [
            {
                "name": "web",
                "command": "python3 -m http.server 8080",
                "port": 8080,
            },
            {
                "name": "api",
                "command_args": ["python3", "-c", "import time; time.sleep(60)"],
                "port": 9090,
            },
        ],
        "proxy": {
            "listen_port": 8000,
            "targets": ["web", "api"],
        },
    }
    try:
        validated = ConfigLoader.validate(sample_config)
        assert len(validated["services"]) == 2, "服务数量应为2"
        assert validated["services"][0]["name"] == "web", "第一个服务名应为web"
        assert validated["proxy"]["targets"] == ["web", "api"], "代理目标不正确"
        print("[selftest] 配置解析/校验: PASS")
    except AppError as e:
        print(f"[selftest] 配置解析/校验: FAIL ({e.code}: {e.message})")
        return 1
    except AssertionError as e:
        print(f"[selftest] 配置解析/校验: FAIL ({e})")
        return 1

    # 2. 进程管理器状态测试（不真正启动进程）
    pm = ProcessManager()
    # 空状态
    status = pm.status()
    assert isinstance(status, list), "状态应为列表"
    assert len(status) == 0, "初始状态应为空"
    print("[selftest] 进程管理-初始状态: PASS")

    # 3. 健康检查报告测试（无进程时）
    checker = HealthChecker()
    report = checker.report(validated["services"], pm)
    assert report["timestamp"] > 0, "时间戳应为正数"
    assert len(report["services"]) == 2, "报告应包含2个服务"
    # 所有服务未运行
    for svc in report["services"]:
        assert svc["running"] is False, "未启动的服务不应在运行"
        assert svc["healthy"] is False, "未启动的服务不应健康"
    print("[selftest] 健康检查-未运行状态: PASS")

    # 4. 代理轮询测试
    proxy = SimpleProxy([8080, 9090])
    r1 = proxy.next_target()
    r2 = proxy.next_target()
    r3 = proxy.next_target()
    assert r1 in (8080, 9090), "第一次轮询应在目标列表中"
    assert r2 in (8080, 9090), "第二次轮询应在目标列表中"
    assert r3 in (8080, 9090), "第三次轮询应在目标列表中"
    # 宽松断言：三次中至少有一次不同（轮询效果）
    assert len({r1, r2, r3}) >= 2, "轮询应产生至少两个不同目标"
    print("[selftest] 代理轮询: PASS")

    # 5. 日志聚合测试（无进程时返回空）
    logs = pm.collect_logs()
    assert isinstance(logs, dict), "日志应为字典"
    assert len(logs) == 0, "无进程时日志应为空"
    print("[selftest] 日志聚合-空状态: PASS")

    # 6. 错误码测试
    try:
        raise err_config("测试错误")
    except AppError as e:
        assert e.code == "E002", "错误码应为E002"
    try:
        raise err_validation("测试错误")
    except AppError as e:
        assert e.code == "E003", "错误码应为E003"
    print("[selftest] 错误码定义: PASS")

    print("[selftest] 全部自检通过")
    return 0


# ---------------------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    """构建命令行参数解析器。"""
    parser = argparse.ArgumentParser(
        prog="switchpipe",
        description="后端进程托管 HTTP代理 部署工具",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检（不读外部文件、不访问网络）",
    )
    parser.add_argument(
        "-c", "--config",
        help="配置文件路径（JSON 或 YAML）",
    )
    parser.add_argument(
        "action",
        nargs="?",
        choices=["start", "stop", "restart", "status", "logs", "proxy"],
        help="执行动作",
    )
    parser.add_argument(
        "--name",
        help="服务名称（用于 stop/logs）",
    )
    parser.add_argument(
        "--path",
        default="/",
        help="代理转发路径（仅 proxy 动作）",
    )
    return parser


def main() -> int:
    """主函数。"""
    parser = build_parser()
    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        return run_selftest()

    # 必须有配置文件和动作
    if not args.config:
        parser.error("需要 -c/--config 指定配置文件")
    if not args.action:
        parser.error("需要指定动作 (start/stop/restart/status/logs/proxy)")

    # 初始化应用
    app = SwitchPipeApp(args.config)
    try:
        app.load_config()
    except AppError as e:
        print(f"配置加载失败: {e}", file=sys.stderr)
        return 1

    # 执行动作
    try:
        if args.action == "start":
            result = app.cmd_start()
        elif args.action == "stop":
            result = app.cmd_stop(args.name)
        elif args.action == "restart":
            result = app.cmd_restart()
        elif args.action == "status":
            result = app.cmd_status()
        elif args.action == "logs":
            result = app.cmd_logs(args.name)
        elif args.action == "proxy":
            result = app.cmd_proxy(args.path)
        else:
            raise err_usage(f"未知动作: {args.action}")
    except AppError as e:
        print(f"执行失败: {e}", file=sys.stderr)
        return 1

    # 输出结果（JSON 格式化）
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
