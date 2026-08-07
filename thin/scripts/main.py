#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py - Thin 服务器技能手册（独立实现）

本脚本根据功能规格独立编写，用于提供 Thin 服务器配置解读、
启动停止指引、日志分析、性能调优建议和部署集成参考。

仅使用 Python 标准库，无第三方依赖。
支持 --selftest 参数进行离线自检。
"""

import argparse
import json
import os
import sys
import tempfile
from typing import Any, Dict, List, Optional, Tuple

# ============================================================
# 错误码定义
# ============================================================
ERROR_CODES = {
    "E001": "参数错误：缺少必要参数或参数格式不正确",
    "E002": "文件错误：配置文件不存在或无法读取",
    "E003": "解析错误：YAML 配置解析失败",
    "E004": "配置错误：配置内容不符合 Thin 规范",
    "E005": "日志错误：日志文件不存在或格式异常",
    "E006": "调优错误：无法基于当前配置生成调优建议",
    "E007": "部署错误：部署集成参数不完整",
    "E008": "自检错误：核心逻辑自检失败",
    "E009": "运行时错误：未预期的运行时异常",
    "E010": "IO错误：输入输出操作失败",
}

# ============================================================
# 核心数据结构
# ============================================================

class ThinConfig:
    """Thin 服务器配置对象"""
    
    def __init__(self) -> None:
        self.address: str = "0.0.0.0"
        self.port: int = 3000
        self.servers: int = 1
        self.max_conns: int = 1024
        self.max_persistent_conns: int = 100
        self.timeout: int = 30
        self.environment: str = "development"
        self.pid_file: str = "tmp/pids/thin.pid"
        self.log_file: str = "log/thin.log"
        self.rackup: str = "config.ru"
        self.tag: str = ""
        self.daemonize: bool = False
        self.chdir: str = "."
        self.threaded: bool = False
        self.no_epoll: bool = False
        self.backend: str = "ruby"
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "address": self.address,
            "port": self.port,
            "servers": self.servers,
            "max_conns": self.max_conns,
            "max_persistent_conns": self.max_persistent_conns,
            "timeout": self.timeout,
            "environment": self.environment,
            "pid_file": self.pid_file,
            "log_file": self.log_file,
            "rackup": self.rackup,
            "tag": self.tag,
            "daemonize": self.daemonize,
            "chdir": self.chdir,
            "threaded": self.threaded,
            "no_epoll": self.no_epoll,
            "backend": self.backend
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ThinConfig":
        """从字典创建配置对象"""
        config = cls()
        for key, value in data.items():
            if hasattr(config, key):
                setattr(config, key, value)
        return config


# ============================================================
# 核心逻辑函数
# ============================================================

def parse_yaml_simple(yaml_text: str) -> Dict[str, Any]:
    """
    简易 YAML 解析器（仅支持 Thin 配置常用格式）
    支持: 键值对、嵌套字典、列表、布尔值、数字、字符串
    """
    result: Dict[str, Any] = {}
    lines = yaml_text.splitlines()
    
    # 预处理：移除注释行和空行，但保留缩进信息
    valid_lines = []
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        valid_lines.append(line)
    
    if not valid_lines:
        return result
    
    # 确定基础缩进（通常是0）
    base_indent = len(valid_lines[0]) - len(valid_lines[0].lstrip())
    
    # 使用栈来跟踪嵌套层级
    # 栈中元素: (缩进级别, 字典)
    stack: List[Tuple[int, Dict[str, Any]]] = [(0, result)]
    
    for line_num, line in enumerate(valid_lines, 1):
        # 计算缩进（相对于基础缩进）
        indent = len(line) - len(line.lstrip())
        if indent < base_indent:
            indent = 0
        else:
            indent -= base_indent
        
        stripped = line.strip()
        
        # 处理列表项
        if stripped.startswith("- "):
            item = stripped[2:].strip()
            
            # 找到当前层级
            while stack and indent <= stack[-1][0]:
                stack.pop()
            
            if not stack:
                raise ValueError(f"E003: 行 {line_num} 缩进异常")
            
            current_dict = stack[-1][1]
            
            # 如果当前字典有列表值，添加到其中
            if isinstance(current_dict, dict):
                # 查找最后一个键是否为列表
                if current_dict:
                    last_key = list(current_dict.keys())[-1]
                    if isinstance(current_dict[last_key], list):
                        current_dict[last_key].append(_parse_yaml_value(item))
                    else:
                        # 创建新列表
                        current_dict[last_key] = [_parse_yaml_value(item)]
                else:
                    result.setdefault("items", []).append(_parse_yaml_value(item))
            elif isinstance(current_dict, list):
                current_dict.append(_parse_yaml_value(item))
            continue
        
        # 处理键值对
        if ":" in stripped:
            key, _, value = stripped.partition(":")
            key = key.strip()
            value = value.strip()
            
            # 弹出缩进大于当前行的栈
            while stack and indent <= stack[-1][0]:
                stack.pop()
            
            if not stack:
                raise ValueError(f"E003: 行 {line_num} 缩进异常")
            
            current_dict = stack[-1][1]
            
            # 处理嵌套字典
            if value == "":
                new_dict: Dict[str, Any] = {}
                current_dict[key] = new_dict
                stack.append((indent, new_dict))
                continue
            
            # 解析值类型
            current_dict[key] = _parse_yaml_value(value)
        else:
            raise ValueError(f"E003: 行 {line_num} 格式无法识别")
    
    return result


def _parse_yaml_value(value: str) -> Any:
    """解析 YAML 标量值"""
    value = value.strip()
    
    # 布尔值
    if value.lower() == "true":
        return True
    if value.lower() == "false":
        return False
    
    # 空值
    if value.lower() in ("null", "~") or value == "":
        return None
    
    # 数字
    try:
        if "." in value:
            return float(value)
        return int(value)
    except ValueError:
        pass
    
    # 字符串（去掉引号）
    if (value.startswith('"') and value.endswith('"')) or \
       (value.startswith("'") and value.endswith("'")):
        return value[1:-1]
    
    return value


def load_config(config_path: str) -> ThinConfig:
    """
    从配置文件加载 Thin 配置
    支持 YAML 格式和简单键值对格式
    """
    if not os.path.isfile(config_path):
        raise FileNotFoundError(f"E002: 配置文件不存在: {config_path}")
    
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            content = f.read()
    except (IOError, OSError) as e:
        raise IOError(f"E010: 读取配置文件失败: {e}") from e
    
    try:
        data = parse_yaml_simple(content)
    except ValueError as e:
        raise ValueError(f"E003: {e}") from e
    
    # 映射配置项
    config = ThinConfig()
    mapping = {
        "address": "address",
        "port": "port",
        "servers": "servers",
        "max_conns": "max_conns",
        "max_persistent_conns": "max_persistent_conns",
        "timeout": "timeout",
        "environment": "environment",
        "pid_file": "pid_file",
        "log_file": "log_file",
        "rackup": "rackup",
        "tag": "tag",
        "daemonize": "daemonize",
        "chdir": "chdir",
        "threaded": "threaded",
        "no_epoll": "no_epoll",
        "backend": "backend"
    }
    
    for yaml_key, attr in mapping.items():
        if yaml_key in data:
            setattr(config, attr, data[yaml_key])
    
    return config


def validate_config(config: ThinConfig) -> List[str]:
    """验证配置合法性，返回问题列表"""
    issues = []
    
    if not (1 <= config.port <= 65535):
        issues.append(f"端口号 {config.port} 超出有效范围 1-65535")
    
    if config.servers < 1:
        issues.append(f"服务器数量 {config.servers} 必须大于 0")
    
    if config.max_conns < 1:
        issues.append(f"最大连接数 {config.max_conns} 必须大于 0")
    
    if config.timeout < 0:
        issues.append(f"超时时间 {config.timeout} 不能为负数")
    
    if config.environment not in ("development", "production", "test"):
        issues.append(f"环境 '{config.environment}' 无效，应为 development/production/test")
    
    return issues


def generate_start_commands(config: ThinConfig) -> List[str]:
    """生成启动命令"""
    commands = []
    
    # 基本启动命令
    cmd = ["thin", "start"]
    
    if config.address:
        cmd.extend(["-a", config.address])
    if config.port:
        cmd.extend(["-p", str(config.port)])
    if config.servers > 1:
        cmd.extend(["-s", str(config.servers)])
    if config.environment:
        cmd.extend(["-e", config.environment])
    if config.rackup:
        cmd.extend(["-R", config.rackup])
    if config.daemonize:
        cmd.append("-d")
    if config.chdir and config.chdir != ".":
        cmd.extend(["-C", config.chdir])
    if config.tag:
        cmd.extend(["-t", config.tag])
    
    commands.append(" ".join(cmd))
    
    # 停止命令
    stop_cmd = ["thin", "stop"]
    if config.pid_file:
        stop_cmd.extend(["-P", config.pid_file])
    commands.append(" ".join(stop_cmd))
    
    # 重启命令
    restart_cmd = ["thin", "restart"]
    if config.pid_file:
        restart_cmd.extend(["-P", config.pid_file])
    commands.append(" ".join(restart_cmd))
    
    return commands


def analyze_log(log_content: str) -> Dict[str, Any]:
    """
    分析 Thin 日志内容
    返回统计信息和异常检测结果
    """
    stats = {
        "total_requests": 0,
        "success_requests": 0,
        "error_requests": 0,
        "slow_requests": 0,
        "errors": [],
        "top_paths": {},
        "status_codes": {}
    }
    
    for line in log_content.splitlines():
        # 跳过空行
        if not line.strip():
            continue
        
        # 尝试解析日志行
        parts = line.split()
        if len(parts) < 3:
            continue
        
        # 检测请求行（包含HTTP方法）
        is_request = False
        for method in ["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"]:
            if f'"{method} ' in line or f' {method} ' in line:
                is_request = True
                break
        
        if is_request:
            stats["total_requests"] += 1
            
            # 提取路径
            for part in parts:
                if part.startswith("/") and len(part) > 1:
                    path = part.split("?")[0]
                    stats["top_paths"][path] = stats["top_paths"].get(path, 0) + 1
                    break
            
            # 提取状态码
            for part in parts:
                # 尝试解析状态码（3位数字）
                try:
                    if len(part) == 3 and part.isdigit():
                        status = int(part)
                        if 100 <= status <= 599:
                            stats["status_codes"][status] = stats["status_codes"].get(status, 0) + 1
                            
                            if status >= 400:
                                stats["error_requests"] += 1
                                if len(stats["errors"]) < 10:  # 最多记录10条错误
                                    stats["errors"].append(line[:200])
                            else:
                                stats["success_requests"] += 1
                            break
                except (ValueError, IndexError):
                    continue
        
        # 检测慢请求
        if "ms" in line:
            try:
                # 查找包含ms的数值
                for part in parts:
                    if part.endswith("ms"):
                        ms_str = part[:-2]
                        if ms_str.isdigit():
                            ms = int(ms_str)
                            if ms > 1000:
                                stats["slow_requests"] += 1
                            break
            except (ValueError, IndexError):
                pass
    
    return stats


def generate_tuning_suggestions(config: ThinConfig, stats: Optional[Dict[str, Any]] = None) -> List[str]:
    """生成性能调优建议"""
    suggestions = []
    
    # 基于配置的建议
    if config.servers == 1:
        suggestions.append("当前仅运行 1 个服务器实例，建议在负载较高时增加 -s 参数（如 -s 2 或 -s 4）")
    
    if config.max_conns < 1024:
        suggestions.append(f"最大连接数 {config.max_conns} 偏低，高并发场景建议提升至 2048 或更高")
    
    if config.timeout > 30:
        suggestions.append(f"超时时间 {config.timeout}s 较长，建议缩短至 30s 以内以避免连接长时间占用")
    
    if config.environment == "development":
        suggestions.append("当前为开发环境，生产部署时请切换为 production 环境以获得更好性能")
    
    if config.threaded:
        suggestions.append("已启用线程模式，注意 Ruby 线程安全性和 GIL 的影响")
    else:
        suggestions.append("未启用线程模式，如处理 I/O 密集型请求可考虑 --threaded 选项")
    
    # 基于日志统计的建议
    if stats:
        if stats.get("error_requests", 0) > 0:
            error_rate = stats["error_requests"] / max(stats["total_requests"], 1)
            if error_rate > 0.1:
                suggestions.append(f"错误率 {error_rate:.1%} 较高，建议检查应用日志和依赖服务状态")
        
        if stats.get("slow_requests", 0) > 0:
            suggestions.append(f"检测到 {stats['slow_requests']} 个慢请求（>1000ms），建议优化应用性能或启用缓存")
    
    return suggestions


def generate_deployment_guide(config: ThinConfig) -> Dict[str, str]:
    """生成部署集成指南"""
    guide = {
        "nginx": f"""# Nginx 反向代理配置示例
upstream thin_cluster {{
    server {config.address}:{config.port} fail_timeout=0;
}}
server {{
    listen 80;
    server_name example.com;
    location / {{
        proxy_pass http://thin_cluster;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }}
}}""",
        "systemd": f"""[Unit]
Description=Thin Web Server
After=network.target

[Service]
Type=simple
WorkingDirectory={config.chdir}
ExecStart=/usr/local/bin/thin start -p {config.port} -e {config.environment}
ExecStop=/usr/local/bin/thin stop -P {config.pid_file}
Restart=on-failure

[Install]
WantedBy=multi-user.target""",
        "docker": f"""FROM ruby:3.2-slim
WORKDIR /app
COPY . .
RUN gem install thin
EXPOSE {config.port}
CMD ["thin", "start", "-p", "{config.port}", "-e", "{config.environment}"]"""
    }
    
    return guide


# ============================================================
# 自检函数
# ============================================================

def run_selftest() -> bool:
    """
    运行核心逻辑自检
    使用内置硬编码样例数据，不依赖外部文件
    """
    print("=" * 60)
    print("Thin 技能核心逻辑自检")
    print("=" * 60)
    
    all_passed = True
    
    # 1. 测试配置解析
    print("\n[1/5] 测试配置解析...")
    sample_yaml = """address: 127.0.0.1
port: 8080
servers: 2
max_conns: 2048
timeout: 15
environment: production
daemonize: true
"""
    try:
        parsed = parse_yaml_simple(sample_yaml)
        assert parsed["address"] == "127.0.0.1", "地址解析错误"
        assert parsed["port"] == 8080, "端口解析错误"
        assert parsed["servers"] == 2, "服务器数量解析错误"
        assert parsed["max_conns"] == 2048, "最大连接数解析错误"
        assert parsed["timeout"] == 15, "超时解析错误"
        assert parsed["environment"] == "production", "环境解析错误"
        assert parsed["daemonize"] is True, "守护进程标志解析错误"
        print("  ✓ 配置解析正常")
    except Exception as e:
        print(f"  ✗ 配置解析失败: {e}")
        all_passed = False
    
    # 2. 测试配置验证
    print("\n[2/5] 测试配置验证...")
    try:
        valid_config = ThinConfig()
        valid_config.port = 3000
        valid_config.environment = "production"
        issues = validate_config(valid_config)
        assert len(issues) == 0, f"有效配置被误报: {issues}"
        
        invalid_config = ThinConfig()
        invalid_config.port = 70000  # 无效端口
        invalid_config.servers = 0  # 无效服务器数
        issues = validate_config(invalid_config)
        assert len(issues) >= 2, "无效配置未被正确识别"
        print("  ✓ 配置验证正常")
    except Exception as e:
        print(f"  ✗ 配置验证失败: {e}")
        all_passed = False
    
    # 3. 测试命令生成
    print("\n[3/5] 测试命令生成...")
    try:
        test_config = ThinConfig()
        test_config.port = 3000
        test_config.environment = "production"
        test_config.servers = 2
        commands = generate_start_commands(test_config)
        assert len(commands) >= 3, "命令数量不足"
        assert "thin start" in commands[0], "启动命令格式错误"
        assert "thin stop" in commands[1], "停止命令格式错误"
        assert "thin restart" in commands[2], "重启命令格式错误"
        print("  ✓ 命令生成正常")
    except Exception as e:
        print(f"  ✗ 命令生成失败: {e}")
        all_passed = False
    
    # 4. 测试日志分析
    print("\n[4/5] 测试日志分析...")
    sample_log = """2026-01-01 10:00:00 GET / 200 45ms
2026-01-01 10:00:01 GET /about 200 30ms
2026-01-01 10:00:02 POST /api 500 1200ms
2026-01-01 10:00:03 GET /contact 404 10ms
2026-01-01 10:00:04 GET / 200 60ms
"""
    try:
        stats = analyze_log(sample_log)
        assert stats["total_requests"] == 5, f"请求总数统计错误: {stats['total_requests']}"
        assert stats["error_requests"] == 2, f"错误请求统计错误: {stats['error_requests']}"
        assert stats["success_requests"] == 3, f"成功请求统计错误: {stats['success_requests']}"
        assert stats["slow_requests"] == 1, f"慢请求统计错误: {stats['slow_requests']}"
        assert len(stats["top_paths"]) == 4, f"路径统计错误: {stats['top_paths']}"
        print("  ✓ 日志分析正常")
    except Exception as e:
        print(f"  ✗ 日志分析失败: {e}")
        all_passed = False
    
    # 5. 测试调优建议和部署指南
    print("\n[5/5] 测试调优建议和部署指南...")
    try:
        tuning_config = ThinConfig()
        tuning_config.servers = 1
        tuning_config.max_conns = 512
        tuning_config.environment = "development"
        tuning_config.timeout = 60
        
        # 使用之前分析的统计数据
        if 'stats' not in locals():
            stats = analyze_log(sample_log)
        
        suggestions = generate_tuning_suggestions(tuning_config, stats)
        assert len(suggestions) >= 3, f"调优建议数量不足: {len(suggestions)}"
        
        guide = generate_deployment_guide(tuning_config)
        assert "nginx" in guide, "缺少 Nginx 配置"
        assert "systemd" in guide, "缺少 systemd 配置"
        assert "docker" in guide, "缺少 Docker 配置"
        print("  ✓ 调优建议和部署指南正常")
    except Exception as e:
        print(f"  ✗ 调优建议和部署指南失败: {e}")
        all_passed = False
    
    # 总结
    print("\n" + "=" * 60)
    if all_passed:
        print("自检通过：所有核心逻辑正常")
    else:
        print("自检失败：存在异常")
    print("=" * 60)
    
    return all_passed


# ============================================================
# 主程序
# ============================================================

def main() -> int:
    """主入口函数"""
    parser = argparse.ArgumentParser(
        description="Thin 服务器技能手册 - 配置解读、部署指引、日志分析、性能调优",
        epilog="示例: python main.py --config thin.yml --analyze"
    )
    
    parser.add_argument("--config", "-c", type=str, help="Thin 配置文件路径（YAML格式）")
    parser.add_argument("--analyze", "-a", type=str, help="分析日志文件路径")
    parser.add_argument("--tune", "-t", action="store_true", help="生成性能调优建议")
    parser.add_argument("--deploy", "-d", action="store_true", help="生成部署集成指南")
    parser.add_argument("--validate", "-v", action="store_true", help="验证配置合法性")
    parser.add_argument("--selftest", action="store_true", help="运行核心逻辑自检")
    parser.add_argument("--output", "-o", type=str, help="输出结果到文件（JSON格式）")
    
    args = parser.parse_args()
    
    # 运行自检
    if args.selftest:
        success = run_selftest()
        return 0 if success else 8
    
    # 如果没有指定任何操作，显示帮助
    if not (args.config or args.analyze or args.tune or args.deploy or args.validate):
        parser.print_help()
        return 0
    
    result: Dict[str, Any] = {}
    
    try:
        # 加载配置
        config = None
        if args.config:
            try:
                config = load_config(args.config)
                result["config"] = config.to_dict()
                print(f"已加载配置: {args.config}")
            except (FileNotFoundError, ValueError, IOError) as e:
                print(f"错误: {e}", file=sys.stderr)
                return 2
        
        # 验证配置
        if args.validate and config:
            issues = validate_config(config)
            if issues:
                result["validation_issues"] = issues
                for issue in issues:
                    print(f"  ⚠ {issue}")
            else:
                result["validation_issues"] = []
                print("配置验证通过")
        
        # 生成启动/停止/重启命令
        if config and not args.validate:
            commands = generate_start_commands(config)
            result["commands"] = commands
            print("\n=== 服务器命令 ===")
            for i, cmd in enumerate(commands, 1):
                print(f"  {cmd}")
        
        # 分析日志
        if args.analyze:
            if not os.path.isfile(args.analyze):
                print(f"错误: E005 日志文件不存在: {args.analyze}", file=sys.stderr)
                return 5
            try:
                with open(args.analyze, "r", encoding="utf-8", errors="replace") as f:
                    log_content = f.read()
                stats = analyze_log(log_content)
                result["log_stats"] = stats
                print("\n=== 日志分析结果 ===")
                print(f"  总请求数: {stats['total_requests']}")
                print(f"  成功请求: {stats['success_requests']}")
                print(f"  错误请求: {stats['error_requests']}")
                print(f"  慢请求: {stats['slow_requests']}")
                if stats["top_paths"]:
                    print("  热门路径:")
                    for path, count in sorted(stats["top_paths"].items(), key=lambda x: x[1], reverse=True)[:5]:
                        print(f"    {path}: {count}次")
            except (IOError, OSError) as e:
                print(f"错误: E010 读取日志失败: {e}", file=sys.stderr)
                return 10
        
        # 生成调优建议
        if args.tune:
            if not config:
                print("错误: E001 调优需要提供配置文件 (--config)", file=sys.stderr)
                return 1
            stats = result.get("log_stats")
            suggestions = generate_tuning_suggestions(config, stats)
            result["tuning_suggestions"] = suggestions
            print("\n=== 性能调优建议 ===")
            for i, suggestion in enumerate(suggestions, 1):
                print(f"  {i}. {suggestion}")
        
        # 生成部署指南
        if args.deploy:
            if not config:
                print("错误: E001 部署指南需要提供配置文件 (--config)", file=sys.stderr)
                return 1
            guide = generate_deployment_guide(config)
            result["deployment_guide"] = guide
            print("\n=== 部署集成指南 ===")
            for name, content in guide.items():
                print(f"\n--- {name} ---")
                print(content)
        
        # 输出到文件
        if args.output:
            try:
                with open(args.output, "w", encoding="utf-8") as f:
                    json.dump(result, f, ensure_ascii=False, indent=2)
                print(f"\n结果已保存到: {args.output}")
            except (IOError, OSError) as e:
                print(f"错误: E010 写入输出文件失败: {e}", file=sys.stderr)
                return 10
        
        return 0
        
    except Exception as e:
        print(f"错误: E009 未预期异常: {e}", file=sys.stderr)
        return 9


if __name__ == "__main__":
    sys.exit(main())
