#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YAWS 服务器运维辅助工具 - 独立实现脚本
基于功能规格重新实现，不参考任何既有代码。
"""

import argparse
import re
import sys
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


# ============================================================
# 错误码定义
# ============================================================
ERR_CONFIG_PARSE = "E001"        # 配置文件解析失败
ERR_CONFIG_SYNTAX = "E002"       # 配置文件语法错误
ERR_CONFIG_LOGIC = "E003"        # 配置逻辑冲突
ERR_DEPLOY_UNSUPPORTED = "E004"  # 不支持的部署环境
ERR_LOG_PARSE = "E005"           # 日志解析失败
ERR_PERF_INVALID = "E006"        # 性能参数输入无效
ERR_TROUBLESHOOT_UNKNOWN = "E007"  # 未知故障类型
ERR_ARGUMENT = "E008"            # 命令行参数错误
ERR_FILE_ACCESS = "E009"         # 文件访问失败
ERR_INTERNAL = "E010"            # 内部错误


# ============================================================
# 数据结构定义
# ============================================================
@dataclass
class YawsConfig:
    """解析后的 YAWS 配置"""
    port: int = 8000
    docroot: str = "/var/www/yaws"
    max_connections: int = 1000
    gc_objs: int = 100
    enable_auth: bool = False
    ssl_enabled: bool = False
    raw_content: str = ""
    lines: List[str] = None

    def __post_init__(self):
        if self.lines is None:
            self.lines = []


@dataclass
class DeployStep:
    """部署步骤"""
    order: int
    title: str
    commands: List[str]
    description: str = ""


@dataclass
class LogEntry:
    """日志条目"""
    timestamp: str
    level: str
    message: str
    source: str = ""


@dataclass
class PerfSuggestion:
    """性能建议"""
    param_name: str
    suggested_value: int
    reason: str
    unit: str = ""


@dataclass
class TroubleshootGuide:
    """故障排查指南"""
    issue: str
    steps: List[str]
    cause: str = ""


# ============================================================
# 核心功能模块
# ============================================================

class ConfigParser:
    """C1: 配置解析与校验"""

    # 已知配置项模式
    _KNOWN_KEYS = {
        'port': 'int',
        'docroot': 'str',
        'max_connections': 'int',
        'gc_objs': 'int',
        'enable_auth': 'bool',
        'ssl_enabled': 'bool',
    }

    def parse(self, content: str) -> YawsConfig:
        """解析配置文件内容"""
        try:
            config = YawsConfig(raw_content=content)
            config.lines = content.splitlines()

            for line_num, line in enumerate(config.lines, 1):
                stripped = line.strip()

                # 跳过空行和注释
                if not stripped or stripped.startswith('#'):
                    continue

                # 解析 key = value 格式
                if '=' not in stripped:
                    raise ValueError(f"第 {line_num} 行缺少 '=' 符号")

                key, _, value = stripped.partition('=')
                key = key.strip()
                value = value.strip()

                # 检查是否已知配置项
                if key not in self._KNOWN_KEYS:
                    continue  # 忽略未知配置项

                # 类型转换
                expected_type = self._KNOWN_KEYS[key]
                try:
                    if expected_type == 'int':
                        setattr(config, key, int(value))
                    elif expected_type == 'bool':
                        setattr(config, key, value.lower() in ('true', 'yes', '1'))
                    else:
                        setattr(config, key, value)
                except ValueError:
                    raise ValueError(f"第 {line_num} 行配置项 '{key}' 值 '{value}' 格式错误")

            self._validate(config)
            return config

        except ValueError as e:
            raise ValueError(f"{ERR_CONFIG_SYNTAX}: {str(e)}")
        except Exception as e:
            raise RuntimeError(f"{ERR_CONFIG_PARSE}: 解析配置失败: {str(e)}")

    def _validate(self, config: YawsConfig) -> None:
        """逻辑校验"""
        # 端口范围检查
        if not (1 <= config.port <= 65535):
            raise ValueError(f"{ERR_CONFIG_LOGIC}: 端口号 {config.port} 超出有效范围 [1, 65535]")

        # 并发连接数检查
        if config.max_connections <= 0:
            raise ValueError(f"{ERR_CONFIG_LOGIC}: max_connections 必须为正数")

        # gc_objs 检查
        if config.gc_objs <= 0:
            raise ValueError(f"{ERR_CONFIG_LOGIC}: gc_objs 必须为正数")

        # docroot 检查
        if not config.docroot:
            raise ValueError(f"{ERR_CONFIG_LOGIC}: docroot 不能为空")


class DeployGenerator:
    """C2: 部署步骤生成"""

    # 支持的 OS 类型
    SUPPORTED_OS = ['ubuntu', 'debian', 'centos', 'rhel', 'amazon']

    def generate(self, os_type: str, erlang_version: str) -> List[DeployStep]:
        """生成部署命令序列"""
        os_type = os_type.lower().strip()

        if os_type not in self.SUPPORTED_OS:
            raise ValueError(f"{ERR_DEPLOY_UNSUPPORTED}: 不支持的 OS 类型 '{os_type}'，支持: {', '.join(self.SUPPORTED_OS)}")

        if not erlang_version or not re.match(r'^\d+\.\d+', erlang_version):
            raise ValueError(f"{ERR_ARGUMENT}: Erlang 版本格式无效: '{erlang_version}'")

        steps = []

        # 步骤1: 安装依赖
        if os_type in ('ubuntu', 'debian'):
            install_cmds = [
                "apt-get update",
                "apt-get install -y build-essential libssl-dev libncurses5-dev",
                "apt-get install -y erlang"
            ]
        else:  # centos/rhel/amazon
            install_cmds = [
                "yum update -y",
                "yum install -y gcc gcc-c++ openssl-devel ncurses-devel",
                "yum install -y erlang"
            ]

        steps.append(DeployStep(
            order=1,
            title="安装系统依赖与 Erlang",
            commands=install_cmds,
            description=f"安装 Erlang {erlang_version} 所需的系统依赖"
        ))

        # 步骤2: 下载并编译 YAWS
        steps.append(DeployStep(
            order=2,
            title="获取并编译 YAWS",
            commands=[
                "git clone https://github.com/erlyaws/yaws.git",
                "cd yaws",
                "autoreconf -fi",
                "./configure --prefix=/usr/local",
                "make",
                "make install"
            ],
            description="从源码编译安装最新版 YAWS"
        ))

        # 步骤3: 创建配置
        steps.append(DeployStep(
            order=3,
            title="创建基础配置",
            commands=[
                "mkdir -p /etc/yaws",
                "cat > /etc/yaws/yaws.conf << 'EOF'\n"
                "port = 8000\n"
                "docroot = /var/www/yaws\n"
                "max_connections = 1000\n"
                "gc_objs = 100\n"
                "EOF",
                "mkdir -p /var/www/yaws"
            ],
            description="创建 YAWS 基础配置文件"
        ))

        # 步骤4: 启动服务
        steps.append(DeployStep(
            order=4,
            title="启动 YAWS 服务",
            commands=[
                "yaws --conf /etc/yaws/yaws.conf --daemon",
                "sleep 2",
                "curl -I http://localhost:8000"
            ],
            description="启动并验证 YAWS 服务"
        ))

        return steps


class LogAnalyzer:
    """C3: 日志分析"""

    # 常见错误模式 - 使用更灵活的正则表达式
    ERROR_PATTERNS = [
        (r'error', '一般错误'),
        (r'crash', '崩溃'),
        (r'out\s+of\s+memory', '内存不足'),  # 修正：允许空格或换行
        (r'timeout', '连接超时'),
        (r'connection\s+refused', '连接被拒绝'),
        (r'file\s+not\s+found', '文件不存在'),
        (r'permission\s+denied', '权限不足'),
    ]

    def analyze(self, log_content: str) -> Tuple[List[LogEntry], Dict[str, int]]:
        """分析日志内容，返回条目列表和错误统计"""
        try:
            entries = []
            error_stats = {}

            for line in log_content.splitlines():
                stripped = line.strip()
                if not stripped:
                    continue

                # 尝试解析日志条目
                entry = self._parse_line(stripped)
                if entry:
                    entries.append(entry)

                    # 统计错误类型
                    if entry.level.lower() in ('error', 'critical', 'fatal'):
                        for pattern, label in self.ERROR_PATTERNS:
                            if re.search(pattern, entry.message, re.IGNORECASE):
                                error_stats[label] = error_stats.get(label, 0) + 1
                                break
                        else:
                            error_stats['其他错误'] = error_stats.get('其他错误', 0) + 1

            return entries, error_stats

        except Exception as e:
            raise RuntimeError(f"{ERR_LOG_PARSE}: 日志解析失败: {str(e)}")

    def _parse_line(self, line: str) -> Optional[LogEntry]:
        """解析单行日志"""
        # 格式: [timestamp] [level] [source] message
        match = re.match(r'\[([^\]]+)\]\s*\[([^\]]+)\]\s*\[([^\]]+)\]\s*(.+)', line)
        if match:
            return LogEntry(
                timestamp=match.group(1),
                level=match.group(2),
                source=match.group(3),
                message=match.group(4)
            )

        # 简化格式: timestamp level message
        match = re.match(r'(\S+)\s+(\S+)\s+(.+)', line)
        if match:
            return LogEntry(
                timestamp=match.group(1),
                level=match.group(2),
                message=match.group(3)
            )

        # 无法解析的行
        return LogEntry(
            timestamp="unknown",
            level="info",
            message=line
        )


class PerfAdvisor:
    """C4: 性能参数建议"""

    def suggest(self, concurrent_users: int, cpu_cores: int, memory_mb: int) -> List[PerfSuggestion]:
        """基于输入参数给出性能建议"""
        if concurrent_users <= 0 or cpu_cores <= 0 or memory_mb <= 0:
            raise ValueError(f"{ERR_PERF_INVALID}: 所有参数必须为正数")

        suggestions = []

        # max_connections 建议: 并发用户的 2-3 倍
        max_conn = int(concurrent_users * 2.5)
        suggestions.append(PerfSuggestion(
            param_name="max_connections",
            suggested_value=max_conn,
            reason=f"建议为并发用户数({concurrent_users})的 2-3 倍",
            unit="连接"
        ))

        # gc_objs 建议: 基于内存的 1/1000
        gc_objs = max(10, int(memory_mb / 1000))
        suggestions.append(PerfSuggestion(
            param_name="gc_objs",
            suggested_value=gc_objs,
            reason=f"基于可用内存({memory_mb}MB)估算",
            unit="对象"
        ))

        # 每个 CPU 核心建议处理约 1000 连接
        per_core = int(max_conn / cpu_cores)
        suggestions.append(PerfSuggestion(
            param_name="per_core_connections",
            suggested_value=per_core,
            reason=f"每个 CPU 核心({cpu_cores}核)分配连接数",
            unit="连接/核"
        ))

        return suggestions


class Troubleshooter:
    """C5: 常见故障排查"""

    # 故障排查数据库
    TROUBLESHOOT_DB = {
        'start_failure': {
            'issue': '启动失败',
            'cause': '端口被占用或配置文件错误',
            'steps': [
                "检查端口是否被占用: netstat -tlnp | grep <port>",
                "检查配置文件语法: yaws --check-conf /etc/yaws/yaws.conf",
                "查看错误日志: tail -100 /var/log/yaws.error.log",
                "验证 Erlang 版本兼容性: erl -version",
                "尝试以调试模式启动: yaws --debug --conf /etc/yaws/yaws.conf"
            ]
        },
        'timeout': {
            'issue': '连接超时',
            'cause': '系统资源不足或网络配置问题',
            'steps': [
                "检查系统负载: uptime",
                "查看连接数: netstat -ant | wc -l",
                "检查 max_connections 是否过小",
                "检查防火墙规则: iptables -L -n",
                "测试网络延迟: ping <server_ip>"
            ]
        },
        'memory_overflow': {
            'issue': '内存溢出',
            'cause': 'gc_objs 过小或存在内存泄漏',
            'steps': [
                "检查当前内存使用: free -m",
                "查看 GC 统计: erlang:statistics(garbage_collection)",
                "增大 gc_objs 参数",
                "检查是否有大文件上传导致内存紧张",
                "考虑使用内存监控工具: etop 或 observer"
            ]
        }
    }

    def troubleshoot(self, issue_type: str) -> TroubleshootGuide:
        """根据故障类型返回排查指南"""
        issue_type = issue_type.lower().strip()

        # 模糊匹配
        for key, guide_data in self.TROUBLESHOOT_DB.items():
            if issue_type in key or key in issue_type:
                return TroubleshootGuide(
                    issue=guide_data['issue'],
                    cause=guide_data['cause'],
                    steps=guide_data['steps']
                )

        # 尝试关键词匹配
        keyword_map = {
            'start': 'start_failure',
            '启动': 'start_failure',
            'timeout': 'timeout',
            '超时': 'timeout',
            'memory': 'memory_overflow',
            '内存': 'memory_overflow',
            '溢出': 'memory_overflow',
        }

        for keyword, mapped_key in keyword_map.items():
            if keyword in issue_type:
                guide_data = self.TROUBLESHOOT_DB[mapped_key]
                return TroubleshootGuide(
                    issue=guide_data['issue'],
                    cause=guide_data['cause'],
                    steps=guide_data['steps']
                )

        raise ValueError(f"{ERR_TROUBLESHOOT_UNKNOWN}: 未知故障类型 '{issue_type}'，支持: {', '.join(self.TROUBLESHOOT_DB.keys())}")


# ============================================================
# 自检模块
# ============================================================

class SelfTest:
    """内置自检功能，使用硬编码样例数据"""

    @staticmethod
    def run() -> bool:
        """运行自检，返回是否全部通过"""
        print("=" * 60)
        print("YAWS 运维辅助工具 - 自检模式")
        print("=" * 60)

        # 测试配置解析
        print("\n[1/5] 测试配置解析...")
        SelfTest._test_config_parser()

        # 测试部署生成
        print("\n[2/5] 测试部署生成...")
        SelfTest._test_deploy_generator()

        # 测试日志分析
        print("\n[3/5] 测试日志分析...")
        SelfTest._test_log_analyzer()

        # 测试性能建议
        print("\n[4/5] 测试性能建议...")
        SelfTest._test_perf_advisor()

        # 测试故障排查
        print("\n[5/5] 测试故障排查...")
        SelfTest._test_troubleshooter()

        print("\n" + "=" * 60)
        print("所有自检通过！")
        print("=" * 60)
        return True

    @staticmethod
    def _test_config_parser():
        """测试配置解析"""
        parser = ConfigParser()

        # 有效配置
        valid_config = """
        # YAWS 配置
        port = 8080
        docroot = /var/www/html
        max_connections = 500
        gc_objs = 50
        enable_auth = true
        ssl_enabled = false
        """
        config = parser.parse(valid_config)
        assert config.port == 8080, "端口解析失败"
        assert config.docroot == "/var/www/html", "docroot 解析失败"
        assert config.max_connections == 500, "max_connections 解析失败"
        assert config.enable_auth is True, "enable_auth 解析失败"
        assert config.ssl_enabled is False, "ssl_enabled 解析失败"

        # 错误配置: 端口超范围
        try:
            parser.parse("port = 99999")
            assert False, "应检测到端口超范围"
        except ValueError:
            pass  # 预期行为

        # 错误配置: 语法错误
        try:
            parser.parse("invalid_line_without_equals")
            assert False, "应检测到语法错误"
        except ValueError:
            pass  # 预期行为

        print("  ✓ 配置解析测试通过")

    @staticmethod
    def _test_deploy_generator():
        """测试部署生成"""
        generator = DeployGenerator()

        # 支持的系统
        steps = generator.generate("ubuntu", "25.0")
        assert len(steps) >= 3, "部署步骤数量不足"
        assert steps[0].order == 1, "步骤顺序错误"
        assert len(steps[0].commands) > 0, "步骤命令为空"

        # 不支持的系统
        try:
            generator.generate("windows", "25.0")
            assert False, "应检测到不支持的系统"
        except ValueError:
            pass  # 预期行为

        # 无效的 Erlang 版本
        try:
            generator.generate("ubuntu", "abc")
            assert False, "应检测到无效版本"
        except ValueError:
            pass  # 预期行为

        print("  ✓ 部署生成测试通过")

    @staticmethod
    def _test_log_analyzer():
        """测试日志分析"""
        analyzer = LogAnalyzer()

        # 模拟日志
        sample_log = """
        [2026-01-15 10:30:00] [info] [yaws_server] Server started
        [2026-01-15 10:31:00] [error] [yaws_server] Connection timeout from 192.168.1.100
        [2026-01-15 10:32:00] [error] [yaws_server] Out of memory error
        [2026-01-15 10:33:00] [warning] [yaws_server] High load detected
        [2026-01-15 10:34:00] [error] [yaws_server] File not found: /index.html
        """

        entries, stats = analyzer.analyze(sample_log)
        assert len(entries) >= 4, "日志条目解析数量不足"
        assert '连接超时' in stats, "应检测到连接超时"
        assert '内存不足' in stats, "应检测到内存不足"
        assert '文件不存在' in stats, "应检测到文件不存在"

        # 空日志
        entries, stats = analyzer.analyze("")
        assert len(entries) == 0, "空日志应无条目"

        print("  ✓ 日志分析测试通过")

    @staticmethod
    def _test_perf_advisor():
        """测试性能建议"""
        advisor = PerfAdvisor()

        # 正常输入
        suggestions = advisor.suggest(1000, 4, 8192)
        assert len(suggestions) >= 3, "建议数量不足"
        assert suggestions[0].suggested_value > 1000, "max_connections 应大于并发用户数"
        assert suggestions[1].suggested_value > 0, "gc_objs 应大于 0"

        # 无效输入
        try:
            advisor.suggest(-1, 4, 8192)
            assert False, "应检测到无效输入"
        except ValueError:
            pass  # 预期行为

        print("  ✓ 性能建议测试通过")

    @staticmethod
    def _test_troubleshooter():
        """测试故障排查"""
        troubleshooter = Troubleshooter()

        # 精确匹配
        guide = troubleshooter.troubleshoot("start_failure")
        assert guide.issue == "启动失败", "启动失败排查指南错误"
        assert len(guide.steps) > 0, "排查步骤为空"

        # 模糊匹配
        guide = troubleshooter.troubleshoot("启动")
        assert guide.issue == "启动失败", "模糊匹配失败"

        # 未知类型
        try:
            troubleshooter.troubleshoot("unknown_issue")
            assert False, "应检测到未知故障类型"
        except ValueError:
            pass  # 预期行为

        print("  ✓ 故障排查测试通过")


# ============================================================
# 主程序
# ============================================================

def main():
    """主入口"""
    parser = argparse.ArgumentParser(
        description="YAWS 服务器运维辅助工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s --check-conf /etc/yaws/yaws.conf
  %(prog)s --deploy ubuntu 25.0
  %(prog)s --analyze-log /var/log/yaws.error.log
  %(prog)s --perf 1000 4 8192
  %(prog)s --troubleshoot start_failure
  %(prog)s --selftest
        """
    )

    parser.add_argument("--check-conf", metavar="FILE", help="检查 YAWS 配置文件")
    parser.add_argument("--deploy", nargs=2, metavar=("OS", "ERLANG_VERSION"), help="生成部署命令")
    parser.add_argument("--analyze-log", metavar="FILE", help="分析日志文件")
    parser.add_argument("--perf", nargs=3, type=int, metavar=("USERS", "CORES", "MEMORY_MB"), help="性能建议")
    parser.add_argument("--troubleshoot", metavar="ISSUE", help="故障排查")
    parser.add_argument("--selftest", action="store_true", help="运行自检")

    args = parser.parse_args()

    # 检查是否有任何操作
    if not any([args.check_conf, args.deploy, args.analyze_log, args.perf, args.troubleshoot, args.selftest]):
        parser.print_help()
        return 1

    try:
        # 自检模式
        if args.selftest:
            SelfTest.run()
            return 0

        # 配置检查
        if args.check_conf:
            try:
                with open(args.check_conf, 'r', encoding='utf-8') as f:
                    content = f.read()
            except FileNotFoundError:
                print(f"{ERR_FILE_ACCESS}: 配置文件不存在: {args.check_conf}")
                return 1

            parser_cfg = ConfigParser()
            try:
                config = parser_cfg.parse(content)
                print(f"✓ 配置有效")
                print(f"  端口: {config.port}")
                print(f"  docroot: {config.docroot}")
                print(f"  max_connections: {config.max_connections}")
                print(f"  gc_objs: {config.gc_objs}")
                print(f"  认证: {'启用' if config.enable_auth else '禁用'}")
                print(f"  SSL: {'启用' if config.ssl_enabled else '禁用'}")
            except ValueError as e:
                print(f"✗ 配置错误: {str(e)}")
                return 1

        # 部署生成
        if args.deploy:
            os_type, erlang_version = args.deploy
            generator = DeployGenerator()
            try:
                steps = generator.generate(os_type, erlang_version)
                print(f"✓ 已生成 {len(steps)} 个部署步骤:")
                for step in steps:
                    print(f"\n步骤 {step.order}: {step.title}")
                    print(f"  说明: {step.description}")
                    for cmd in step.commands:
                        print(f"  $ {cmd}")
            except ValueError as e:
                print(f"✗ 部署生成失败: {str(e)}")
                return 1

        # 日志分析
        if args.analyze_log:
            try:
                with open(args.analyze_log, 'r', encoding='utf-8') as f:
                    content = f.read()
            except FileNotFoundError:
                print(f"{ERR_FILE_ACCESS}: 日志文件不存在: {args.analyze_log}")
                return 1

            analyzer = LogAnalyzer()
            try:
                entries, stats = analyzer.analyze(content)
                print(f"✓ 日志分析完成，共 {len(entries)} 条记录")
                if stats:
                    print("\n错误统计:")
                    for error_type, count in stats.items():
                        print(f"  - {error_type}: {count} 次")
                else:
                    print("\n未发现已知错误模式")
            except RuntimeError as e:
                print(f"✗ 日志分析失败: {str(e)}")
                return 1

        # 性能建议
        if args.perf:
            users, cores, memory = args.perf
            advisor = PerfAdvisor()
            try:
                suggestions = advisor.suggest(users, cores, memory)
                print(f"✓ 基于 并发用户={users}, CPU核数={cores}, 内存={memory}MB 的建议:")
                for suggestion in suggestions:
                    print(f"\n  {suggestion.param_name}: {suggestion.suggested_value} {suggestion.unit}")
                    print(f"    原因: {suggestion.reason}")
            except ValueError as e:
                print(f"✗ 性能建议失败: {str(e)}")
                return 1

        # 故障排查
        if args.troubleshoot:
            troubleshooter = Troubleshooter()
            try:
                guide = troubleshooter.troubleshoot(args.troubleshoot)
                print(f"故障: {guide.issue}")
                print(f"可能原因: {guide.cause}")
                print("\n排查步骤:")
                for i, step in enumerate(guide.steps, 1):
                    print(f"  {i}. {step}")
            except ValueError as e:
                print(f"✗ 故障排查失败: {str(e)}")
                return 1

        return 0

    except Exception as e:
        print(f"{ERR_INTERNAL}: 程序执行出错: {str(e)}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
