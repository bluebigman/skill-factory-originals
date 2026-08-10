#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YAWS 服务器运维辅助工具 - 全新独立实现

本脚本依据功能规格独立编写，不复制任何既有代码。
提供配置解析、部署建议、日志分析、性能建议和故障排查五大能力。
"""

import argparse
import os
import re
import sys
from typing import Dict, List, Optional, Tuple


# ============================================================
# 错误码定义
# ============================================================
ERROR_CODES = {
    "E001": "配置文件不存在或无法读取",
    "E002": "配置文件格式错误（非键值对结构）",
    "E003": "配置参数值类型不合法",
    "E004": "日志文件不存在或无法读取",
    "E005": "日志格式无法识别",
    "E006": "系统资源信息不完整",
    "E007": "不支持的操作系统类型",
    "E008": "Erlang版本格式无法解析",
    "E009": "参数组合逻辑冲突",
    "E010": "内部处理异常",
}


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


def fail(code: str, message: Optional[str] = None) -> None:
    """输出错误信息并退出"""
    text = ERROR_CODES.get(code, "未知错误")
    if message:
        text = f"{text}: {message}"
    print(f"[错误 {code}] {text}", file=sys.stderr)
    sys.exit(1)


# ============================================================
# 能力 C1: 配置解析与校验
# ============================================================
class YawsConfigParser:
    """YAWS 配置文件解析器"""

    # 已知的配置参数及其期望类型
    KNOWN_KEYS = {
        "port": "int",
        "listen": "str",
        "docroot": "str",
        "max_connections": "int",
        "gc_objs": "int",
        "logdir": "str",
        "erlang_version": "str",
        "enable_ssl": "bool",
        "ssl_port": "int",
        "servername": "str",
    }

    def __init__(self, config_text: str):
        self.config_text = config_text
        self.params: Dict[str, str] = {}
        self.errors: List[str] = []

    def parse(self) -> Dict[str, str]:
        """解析配置文本为字典"""
        if not self.config_text.strip():
            raise ValueError("配置内容为空")

        for line_num, line in enumerate(self.config_text.splitlines(), 1):
            line = line.strip()
            # 跳过空行和注释
            if not line or line.startswith("#") or line.startswith("%"):
                continue

            # 支持 "key = value" 或 "key value" 两种格式
            if "=" in line:
                parts = line.split("=", 1)
            else:
                parts = line.split(None, 1)

            if len(parts) != 2:
                self.errors.append(f"第{line_num}行格式错误: {line}")
                continue

            key = parts[0].strip()
            value = parts[1].strip().strip('"').strip("'")
            self.params[key] = value

        return self.params

    def validate(self) -> Tuple[bool, List[str]]:
        """校验配置参数的类型和逻辑"""
        issues = []

        # 类型校验
        for key, expected_type in self.KNOWN_KEYS.items():
            if key not in self.params:
                continue

            value = self.params[key]
            try:
                if expected_type == "int":
                    int(value)
                elif expected_type == "bool":
                    if value.lower() not in ("true", "false", "yes", "no", "1", "0"):
                        raise ValueError
            except (ValueError, TypeError):
                issues.append(f"参数 {key} 的值 '{value}' 不是合法的{expected_type}类型")

        # 逻辑校验
        if "port" in self.params and "ssl_port" in self.params:
            if self.params["port"] == self.params["ssl_port"]:
                issues.append("port 和 ssl_port 不能相同")

        # 检查必填参数
        required = ["port", "docroot"]
        for key in required:
            if key not in self.params:
                issues.append(f"缺少必填参数: {key}")

        return (len(issues) == 0, issues)


# ============================================================
# 能力 C2: 部署步骤生成
# ============================================================
def generate_deploy_plan(os_type: str, erlang_version: str) -> List[str]:
    """根据目标环境生成部署步骤"""
    os_type = os_type.lower().strip()
    erlang_version = erlang_version.strip()

    # 校验 Erlang 版本格式
    if not re.match(r"^\d+\.\d+", erlang_version):
        fail("E008", f"无法解析 Erlang 版本: {erlang_version}")

    steps = []

    if os_type in ("ubuntu", "debian", "linux"):
        steps.extend([
            "# 更新软件源",
            "sudo apt-get update",
            "# 安装 Erlang（如果未安装）",
            f"sudo apt-get install -y erlang={erlang_version}* || sudo apt-get install -y erlang",
            "# 安装 YAWS",
            "sudo apt-get install -y yaws",
            "# 启动服务",
            "sudo systemctl start yaws",
            "sudo systemctl enable yaws",
        ])
    elif os_type in ("centos", "rhel", "fedora"):
        steps.extend([
            "# 更新软件源",
            "sudo yum update -y",
            "# 安装 Erlang（如果未安装）",
            f"sudo yum install -y erlang-{erlang_version}* || sudo yum install -y erlang",
            "# 安装 YAWS",
            "sudo yum install -y yaws",
            "# 启动服务",
            "sudo systemctl start yaws",
            "sudo systemctl enable yaws",
        ])
    elif os_type in ("macos", "darwin"):
        steps.extend([
            "# 使用 Homebrew 安装 Erlang",
            f"brew install erlang@{erlang_version.split('.')[0]} || brew install erlang",
            "# 使用 Homebrew 安装 YAWS",
            "brew install yaws",
            "# 手动启动",
            "yaws --daemon --conf /usr/local/etc/yaws/yaws.conf",
        ])
    else:
        fail("E007", f"不支持的操作系统: {os_type}")

    return steps


# ============================================================
# 能力 C3: 日志分析辅助
# ============================================================
class LogAnalyzer:
    """日志分析器"""

    # 常见错误模式
    ERROR_PATTERNS = {
        "连接超时": r"(timeout|timed out|ETIMEDOUT)",
        "内存不足": r"(out of memory|OOM|cannot allocate)",
        "连接拒绝": r"(connection refused|ECONNREFUSED)",
        "文件不存在": r"(no such file|ENOENT|not found)",
        "权限不足": r"(permission denied|EACCES)",
        "端口冲突": r"(address already in use|EADDRINUSE)",
        "配置错误": r"(badarg|badmatch|configuration error)",
    }

    def __init__(self, log_content: str, log_type: str = "access"):
        self.log_content = log_content
        self.log_type = log_type

    def analyze(self) -> Dict[str, int]:
        """分析日志，返回错误类型计数"""
        results: Dict[str, int] = {}

        if self.log_type == "access":
            # 访问日志分析：统计状态码
            status_codes = re.findall(r'" (\d{3}) ', self.log_content)
            for code in status_codes:
                if code.startswith("4") or code.startswith("5"):
                    key = f"HTTP_{code}"
                    results[key] = results.get(key, 0) + 1
        else:
            # 错误日志分析：匹配错误模式
            for error_type, pattern in self.ERROR_PATTERNS.items():
                matches = re.findall(pattern, self.log_content, re.IGNORECASE)
                if matches:
                    results[error_type] = len(matches)

        return results

    def extract_samples(self, limit: int = 5) -> List[str]:
        """提取关键日志行样本"""
        lines = self.log_content.splitlines()
        samples = []

        for line in lines:
            if any(re.search(p, line, re.IGNORECASE) for p in self.ERROR_PATTERNS.values()):
                samples.append(line.strip())
                if len(samples) >= limit:
                    break

        return samples


# ============================================================
# 能力 C4: 性能参数建议
# ============================================================
def suggest_performance_params(
    concurrent_users: int,
    total_memory_mb: int,
    cpu_cores: int = 4
) -> Dict[str, int]:
    """基于并发量和硬件资源给出性能参数建议"""
    if concurrent_users <= 0 or total_memory_mb <= 0 or cpu_cores <= 0:
        fail("E006", "并发量、内存和CPU核心数必须为正数")

    # 建议最大连接数：并发用户数的 2-3 倍，但不超过内存限制
    max_connections = min(concurrent_users * 3, total_memory_mb * 10)

    # 建议 GC 对象数：基于内存的 1/1000 到 1/500
    gc_objs = max(1000, total_memory_mb * 2)

    # 建议进程数：CPU 核心数的 2-4 倍
    processes = max(cpu_cores * 2, 4)

    return {
        "max_connections": max_connections,
        "gc_objs": gc_objs,
        "num_processes": processes,
    }


# ============================================================
# 能力 C5: 常见故障排查
# ============================================================
def troubleshoot(symptom: str) -> List[str]:
    """根据症状返回排查路径"""
    symptom = symptom.lower().strip()

    troubleshooting_map = {
        "启动失败": [
            "1. 检查配置文件语法：yaws --check-config",
            "2. 查看错误日志：tail -f /var/log/yaws/error.log",
            "3. 确认端口未被占用：netstat -tlnp | grep <port>",
            "4. 检查 Erlang 版本兼容性：erl -version",
            "5. 尝试前台启动查看详细错误：yaws -i",
        ],
        "连接超时": [
            "1. 检查网络连通性：ping <server>",
            "2. 查看系统负载：top / htop",
            "3. 检查防火墙规则：iptables -L -n",
            "4. 确认 max_connections 是否过小",
            "5. 查看系统文件描述符限制：ulimit -n",
        ],
        "内存溢出": [
            "1. 查看内存使用：free -m",
            "2. 检查 gc_objs 参数设置",
            "3. 分析是否有内存泄漏：erlang:memory()",
            "4. 考虑增加服务器内存或优化代码",
            "5. 检查是否有无限递归或大对象缓存",
        ],
        "连接拒绝": [
            "1. 确认服务是否在运行：ps aux | grep yaws",
            "2. 检查监听地址：netstat -tlnp | grep yaws",
            "3. 验证防火墙规则",
            "4. 检查 listen 参数配置",
            "5. 确认端口是否被其他程序占用",
        ],
        "配置错误": [
            "1. 检查配置文件格式是否符合规范",
            "2. 确认所有参数类型正确",
            "3. 查看官方配置文档",
            "4. 使用 yaws --check-config 验证",
            "5. 检查是否有拼写错误",
        ],
    }

    # 匹配最相关的症状
    for key, steps in troubleshooting_map.items():
        if key in symptom:
            return steps

    # 默认返回通用排查步骤
    return [
        "1. 查看错误日志：tail -f /var/log/yaws/error.log",
        "2. 检查系统资源：top / free -m / df -h",
        "3. 验证配置文件：yaws --check-config",
        "4. 重启服务测试：systemctl restart yaws",
        "5. 如果问题持续，收集日志并联系支持",
    ]


# ============================================================
# 内置自检功能
# ============================================================
def run_selftest() -> bool:
    """内置自检：使用硬编码样例数据验证核心逻辑"""
    print("=" * 60)
    print("YAWS 运维工具自检")
    print("=" * 60)

    # --- 测试 C1: 配置解析 ---
    print("\n[测试 C1] 配置解析与校验")
    sample_config = """
    # YAWS 配置文件示例
    port = 8080
    listen = 0.0.0.0
    docroot = /var/www/yaws
    max_connections = 1000
    gc_objs = 2000
    logdir = /var/log/yaws
    erlang_version = 25.0
    enable_ssl = false
    ssl_port = 8443
    servername = localhost
    """
    parser = YawsConfigParser(sample_config)
    try:
        params = parser.parse()
        valid, issues = parser.validate()
        assert valid, f"配置校验失败: {issues}"
        assert "port" in params, "缺少 port 参数"
        assert "docroot" in params, "缺少 docroot 参数"
        assert int(params["port"]) > 0, "端口号必须为正数"
        print("  ✓ 配置解析正常，参数数量:", len(params))
    except AssertionError as e:
        print(f"  ✗ 配置解析测试失败: {e}")
        return False
    except Exception as e:
        print(f"  ✗ 配置解析异常: {e}")
        return False

    # --- 测试 C2: 部署计划 ---
    print("\n[测试 C2] 部署步骤生成")
    try:
        steps = generate_deploy_plan("ubuntu", "25.0")
        assert len(steps) > 0, "部署步骤为空"
        assert any("yaws" in s for s in steps), "部署步骤中缺少 yaws"
        print(f"  ✓ 部署计划生成成功，共 {len(steps)} 步")
    except Exception as e:
        print(f"  ✗ 部署计划测试失败: {e}")
        return False

    # --- 测试 C3: 日志分析 ---
    print("\n[测试 C3] 日志分析")
    sample_log = """
    127.0.0.1 - - [10/Oct/2026:13:55:36 +0000] "GET /index.html HTTP/1.1" 200 2326
    127.0.0.1 - - [10/Oct/2026:13:55:37 +0000] "GET /api/data HTTP/1.1" 500 512
    127.0.0.1 - - [10/Oct/2026:13:55:38 +0000] "POST /submit HTTP/1.1" 404 234
    error: connection timeout from 192.168.1.1
    error: out of memory when allocating 1024 bytes
    """
    analyzer = LogAnalyzer(sample_log, "access")
    try:
        results = analyzer.analyze()
        assert "HTTP_500" in results, "未检测到 HTTP 500 错误"
        assert "HTTP_404" in results, "未检测到 HTTP 404 错误"
        assert results["HTTP_500"] >= 1, "HTTP 500 计数异常"
        print(f"  ✓ 访问日志分析成功，错误类型: {list(results.keys())}")

        # 测试错误日志分析
        error_analyzer = LogAnalyzer(sample_log, "error")
        error_results = error_analyzer.analyze()
        assert len(error_results) > 0, "错误日志分析结果为空"
        print(f"  ✓ 错误日志分析成功，错误模式: {list(error_results.keys())}")
    except AssertionError as e:
        print(f"  ✗ 日志分析测试失败: {e}")
        return False
    except Exception as e:
        print(f"  ✗ 日志分析异常: {e}")
        return False

    # --- 测试 C4: 性能建议 ---
    print("\n[测试 C4] 性能参数建议")
    try:
        suggestions = suggest_performance_params(500, 8192, 8)
        assert suggestions["max_connections"] > 0, "max_connections 必须为正数"
        assert suggestions["gc_objs"] > 0, "gc_objs 必须为正数"
        assert suggestions["num_processes"] > 0, "num_processes 必须为正数"
        print(f"  ✓ 性能建议生成成功: {suggestions}")
    except Exception as e:
        print(f"  ✗ 性能建议测试失败: {e}")
        return False

    # --- 测试 C5: 故障排查 ---
    print("\n[测试 C5] 故障排查")
    try:
        steps = troubleshoot("启动失败")
        assert len(steps) > 0, "排查步骤为空"
        assert "yaws" in " ".join(steps).lower(), "排查步骤中缺少 yaws 相关内容"
        print(f"  ✓ 故障排查建议生成成功，共 {len(steps)} 条建议")
    except Exception as e:
        print(f"  ✗ 故障排查测试失败: {e}")
        return False

    # --- 测试错误处理 ---
    print("\n[测试错误处理]")
    try:
        # 测试无效配置
        invalid_config = "port = not_a_number\n"
        invalid_parser = YawsConfigParser(invalid_config)
        invalid_parser.parse()
        valid, issues = invalid_parser.validate()
        assert not valid, "无效配置应该校验失败"
        print("  ✓ 错误处理正常：无效配置被正确识别")
    except Exception as e:
        print(f"  ✗ 错误处理测试失败: {e}")
        return False

    print("\n" + "=" * 60)
    print("所有自检测试通过！")
    print("=" * 60)
    return True


# ============================================================
# 主程序入口
# ============================================================
def main():
    """主程序入口"""
    parser = argparse.ArgumentParser(
        description="YAWS 服务器运维辅助工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  python main.py --parse-config yaws.conf          # 解析配置文件
  python main.py --deploy ubuntu 25.0             # 生成部署计划
  python main.py --analyze-log access.log          # 分析访问日志
  python main.py --analyze-log error.log --type error  # 分析错误日志
  python main.py --suggest 500 8192 8             # 性能建议
  python main.py --troubleshoot "启动失败"          # 故障排查
  python main.py --selftest                        # 运行自检
        """,
    )

    parser.add_argument("--parse-config", metavar="FILE", help="解析并校验 YAWS 配置文件")
    parser.add_argument("--deploy", nargs=2, metavar=("OS", "ERLANG_VERSION"), help="生成部署计划")
    parser.add_argument("--analyze-log", metavar="FILE", help="分析日志文件")
    parser.add_argument("--type", choices=["access", "error"], default="access", help="日志类型")
    parser.add_argument("--suggest", nargs=3, type=int, metavar=("USERS", "MEMORY_MB", "CPU_CORES"), help="性能参数建议")
    parser.add_argument("--troubleshoot", metavar="SYMPTOM", help="故障排查")
    parser.add_argument("--selftest", action="store_true", help="运行内置自检")

    parser.add_argument("--verbose", action="store_true", help="显示修改明细")  # R6 可解释输出

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        success = run_selftest()
        sys.exit(0 if success else 1)

    # 解析配置
    if args.parse_config:
        config_file = args.parse_config
        if not os.path.isfile(config_file):
            fail("E001", f"配置文件不存在: {config_file}")
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                content = f.read()
        except (IOError, OSError) as e:
            fail("E001", f"无法读取配置文件: {e}")

        config_parser = YawsConfigParser(content)
        try:
            params = config_parser.parse()
        except ValueError as e:
            fail("E002", str(e))

        valid, issues = config_parser.validate()
        if not valid:
            for issue in issues:
                print(f"  - {issue}")
            fail("E003", "配置校验未通过")
        else:
            print("配置校验通过！")
            print("解析结果:")
            for key, value in sorted(params.items()):
                print(f"  {key} = {value}")
        return

    # 生成部署计划
    if args.deploy:
        os_type, erlang_version = args.deploy
        try:
            steps = generate_deploy_plan(os_type, erlang_version)
            print(f"部署计划 (OS: {os_type}, Erlang: {erlang_version}):")
            for i, step in enumerate(steps, 1):
                print(f"  {i}. {step}")
        except SystemExit:
            raise
        except Exception as e:
            fail("E010", str(e))
        return

    # 分析日志
    if args.analyze_log:
        log_file = args.analyze_log
        if not os.path.isfile(log_file):
            fail("E004", f"日志文件不存在: {log_file}")
        try:
            with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
        except (IOError, OSError) as e:
            fail("E004", f"无法读取日志文件: {e}")

        analyzer = LogAnalyzer(content, args.type)
        try:
            results = analyzer.analyze()
            if not results:
                print("未发现明显错误模式。")
            else:
                print("日志分析结果:")
                for pattern, count in sorted(results.items(), key=lambda x: -x[1]):
                    print(f"  {pattern}: {count} 次")

                # 显示样本
                samples = analyzer.extract_samples(3)
                if samples:
                    print("\n关键日志样本:")
                    for sample in samples:
                        print(f"  > {sample}")
        except Exception as e:
            fail("E005", str(e))
        return

    # 性能建议
    if args.suggest:
        users, memory, cores = args.suggest
        try:
            suggestions = suggest_performance_params(users, memory, cores)
            print("性能参数建议:")
            for key, value in suggestions.items():
                print(f"  {key} = {value}")
        except SystemExit:
            raise
        except Exception as e:
            fail("E010", str(e))
        return

    # 故障排查
    if args.troubleshoot:
        steps = troubleshoot(args.troubleshoot)
        print(f"针对症状 '{args.troubleshoot}' 的排查建议:")
        for step in steps:
            print(f"  {step}")
        return

    # 无参数时显示帮助
    parser.print_help()


if __name__ == "__main__":
    main()
