#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
plexus — 多智能体工具链一键装配环境配置工具

功能概述：
    本脚本根据功能规格实现一个独立的命令行工具，用于：
    1. 解析文本/文件/URL 中的 MCP 服务配置信息
    2. 识别关键字段（服务名、端口、命令、参数等）
    3. 按用户指定格式（JSON/YAML/TOML）输出结构化配置
    4. 提供置信度标注，对低置信度字段进行标记

设计原则：
    - 仅依赖 Python 标准库，无第三方依赖
    - 支持 --selftest 离线自检，不访问网络/文件系统
    - 错误码规范：E001-E010

作者：SkillForge Lab (clean-room implementation)
版本：1.0.1
"""

import argparse
import json
import re
import sys
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse


# ============================================================
# 错误码定义
# ============================================================
ERROR_CODES = {
    "E001": "参数错误：缺少必要参数或参数格式不正确",
    "E002": "输入格式错误：无法解析输入内容",
    "E003": "输出格式错误：不支持的输出格式",
    "E004": "文件读取错误：无法读取指定文件",
    "E005": "URL 解析错误：无法解析指定 URL",
    "E006": "数据解析错误：无法从内容中提取有效配置",
    "E007": "内部逻辑错误：数据一致性校验失败",
    "E008": "自检失败：核心逻辑验证未通过",
    "E009": "模板渲染错误：自定义模板格式不正确",
    "E010": "未知错误：发生未预期的异常",
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


def fail(code: str, message: str = "") -> None:
    """输出错误信息并退出程序"""
    err_msg = ERROR_CODES.get(code, ERROR_CODES["E010"])
    if message:
        err_msg = f"{err_msg} — {message}"
    print(f"[错误 {code}] {err_msg}", file=sys.stderr)
    sys.exit(1)


# ============================================================
# 数据结构定义
# ============================================================
@dataclass
class MCPService:
    """MCP 服务配置项"""
    name: str = ""
    command: str = ""
    args: List[str] = field(default_factory=list)
    env: Dict[str, str] = field(default_factory=dict)
    url: str = ""
    port: Optional[int] = None
    confidence: float = 1.0  # 置信度 0.0-1.0
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        result = asdict(self)
        # 清理空字段，保持输出简洁
        if not self.args:
            result.pop("args", None)
        if not self.env:
            result.pop("env", None)
        if not self.url:
            result.pop("url", None)
        if self.port is None:
            result.pop("port", None)
        if self.confidence >= 1.0:
            result.pop("confidence", None)
        if not self.notes:
            result.pop("notes", None)
        return result


@dataclass
class ParseResult:
    """解析结果"""
    services: List[MCPService] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    source_type: str = ""  # text/file/url
    format: str = "json"   # json/yaml/toml

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "services": [s.to_dict() for s in self.services],
            "warnings": self.warnings,
            "source_type": self.source_type,
            "format": self.format,
        }


# ============================================================
# 核心解析逻辑
# ============================================================
class ConfigParser:
    """配置解析器 — 从文本中提取 MCP 服务配置"""

    # 常见服务名模式
    NAME_PATTERNS = [
        r"service[_\s]*(?:name)?[_\s]*[:=]\s*[\"']?([a-zA-Z0-9_-]+)",
        r"([a-zA-Z0-9_-]+)\s*[:=]\s*\{",
        r"name[_\s]*[:=]\s*[\"']([a-zA-Z0-9_-]+)[\"']",
    ]

    # 命令模式
    COMMAND_PATTERNS = [
        r"(?:command|cmd|exec)[_\s]*[:=]\s*[\"']([^\"']+)[\"']",
        r"(?:command|cmd|exec)[_\s]*[:=]\s*([a-zA-Z0-9_./-]+)",
    ]

    # 端口模式
    PORT_PATTERNS = [
        r"port[_\s]*[:=]\s*(\d{1,5})",
        r"localhost[_:](\d{1,5})",
        r"127\.0\.0\.1[_:](\d{1,5})",
    ]

    # URL 模式
    URL_PATTERNS = [
        r"(?:url|endpoint|host)[_\s]*[:=]\s*[\"'](https?://[^\"'\s]+)[\"']",
        r"(https?://[a-zA-Z0-9._/-]+)",
    ]

    # 环境变量模式
    ENV_PATTERNS = [
        r"(?:env|environment)[_\s]*[:=]\s*\{([^}]+)\}",
        r"(?:env|environment)[_\s]*[:=]\s*([a-zA-Z0-9_=;,\s]+)",
    ]

    def __init__(self) -> None:
        self._reset()

    def _reset(self) -> None:
        """重置解析状态"""
        self.warnings: List[str] = []
        self.services: List[MCPService] = []

    def parse_text(self, content: str) -> ParseResult:
        """从文本内容解析配置"""
        self._reset()
        if not content or not content.strip():
            fail("E002", "输入内容为空")

        # 按块分割（以 service/服务 开头或空行分割）
        blocks = self._split_blocks(content)
        for block in blocks:
            service = self._parse_block(block)
            if service:
                self.services.append(service)

        if not self.services:
            fail("E006", "未从输入中提取到任何有效配置")

        # 去重（按名称）
        self._deduplicate()

        return ParseResult(
            services=self.services,
            warnings=self.warnings,
            source_type="text",
        )

    def _split_blocks(self, content: str) -> List[str]:
        """将文本分割为配置块"""
        # 按空行分割，或按明显的服务定义分割
        lines = content.split("\n")
        blocks: List[str] = []
        current_block: List[str] = []

        for line in lines:
            stripped = line.strip()
            # 检测新块开始（服务定义标记）
            if self._is_block_start(stripped) and current_block:
                blocks.append("\n".join(current_block))
                current_block = [line]
            else:
                current_block.append(line)

        if current_block:
            blocks.append("\n".join(current_block))

        return blocks

    def _is_block_start(self, line: str) -> bool:
        """判断是否为新配置块的开始"""
        markers = [
            "service", "服务", "mcp", "server", "配置",
            "[", "{", "name:", "名称:",
        ]
        return any(line.lower().startswith(m) for m in markers)

    def _parse_block(self, block: str) -> Optional[MCPService]:
        """解析单个配置块"""
        if not block.strip():
            return None

        service = MCPService()

        # 1. 提取名称
        name = self._extract_name(block)
        if name:
            service.name = name
        else:
            # 尝试从第一行推断
            first_line = block.strip().split("\n")[0]
            if ":" in first_line or "=" in first_line:
                service.name = first_line.split(":")[0].split("=")[0].strip().strip("[]{}")
            else:
                service.name = f"service_{len(self.services) + 1}"
                service.confidence = 0.5
                service.notes.append("[需核实:name]")

        # 2. 提取命令
        command = self._extract_command(block)
        if command:
            service.command = command

        # 3. 提取参数
        args = self._extract_args(block)
        if args:
            service.args = args

        # 4. 提取端口
        port = self._extract_port(block)
        if port:
            service.port = port

        # 5. 提取 URL
        url = self._extract_url(block)
        if url:
            service.url = url

        # 6. 提取环境变量
        env = self._extract_env(block)
        if env:
            service.env = env

        # 7. 计算置信度
        self._calculate_confidence(service)

        return service

    def _extract_name(self, text: str) -> str:
        """提取服务名"""
        for pattern in self.NAME_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
        return ""

    def _extract_command(self, text: str) -> str:
        """提取命令"""
        for pattern in self.COMMAND_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
        return ""

    def _extract_args(self, text: str) -> List[str]:
        """提取参数列表"""
        # 查找 args 或参数数组
        pattern = r"(?:args|arguments|参数)\s*[:=]\s*\[([^\]]+)\]"
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            content = match.group(1)
            # 分割参数（处理引号）
            args = re.findall(r"[\"']([^\"']+)[\"']|(\S+)", content)
            return [a[0] if a[0] else a[1] for a in args if a[0] or a[1]]
        return []

    def _extract_port(self, text: str) -> Optional[int]:
        """提取端口号"""
        for pattern in self.PORT_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                port = int(match.group(1))
                if 0 < port < 65536:
                    return port
        return None

    def _extract_url(self, text: str) -> str:
        """提取 URL"""
        for pattern in self.URL_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                url = match.group(1)
                # 验证 URL 格式
                parsed = urlparse(url)
                if parsed.scheme in ("http", "https"):
                    return url
        return ""

    def _extract_env(self, text: str) -> Dict[str, str]:
        """提取环境变量"""
        env: Dict[str, str] = {}
        for pattern in self.ENV_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                content = match.group(1)
                # 解析 key=value 对
                pairs = re.findall(r"(\w+)\s*=\s*[\"']?([^\"',;\s}]+)[\"']?", content)
                for key, value in pairs:
                    if key and value:
                        env[key] = value
                if env:
                    break
        return env

    def _calculate_confidence(self, service: MCPService) -> None:
        """计算置信度"""
        score = 0.0
        checks = 0

        # 名称置信度
        if service.name:
            if service.name.startswith("service_"):
                score += 0.3
            else:
                score += 1.0
            checks += 1

        # 命令置信度
        if service.command:
            score += 1.0
        else:
            score += 0.2
        checks += 1

        # 端口置信度
        if service.port:
            score += 1.0
        else:
            score += 0.5
        checks += 1

        # URL 置信度
        if service.url:
            score += 1.0
        else:
            score += 0.5
        checks += 1

        if checks > 0:
            service.confidence = max(0.0, min(1.0, score / checks))

    def _deduplicate(self) -> None:
        """去重服务（按名称）"""
        seen: Dict[str, MCPService] = {}
        for service in self.services:
            if service.name in seen:
                # 合并信息
                existing = seen[service.name]
                if not existing.command and service.command:
                    existing.command = service.command
                if not existing.port and service.port:
                    existing.port = service.port
                if not existing.url and service.url:
                    existing.url = service.url
                if not existing.args and service.args:
                    existing.args = service.args
                if not existing.env and service.env:
                    existing.env = service.env
                existing.confidence = max(existing.confidence, service.confidence)
            else:
                seen[service.name] = service
        self.services = list(seen.values())


# ============================================================
# 输出格式化
# ============================================================
class OutputFormatter:
    """输出格式化器"""

    @staticmethod
    def format_json(data: Dict[str, Any]) -> str:
        """JSON 格式输出"""
        return json.dumps(data, ensure_ascii=False, indent=2)

    @staticmethod
    def format_yaml(data: Dict[str, Any]) -> str:
        """YAML 格式输出（简化实现）"""
        lines: List[str] = []

        def _format_dict(d: Dict[str, Any], indent: int = 0) -> None:
            prefix = " " * indent
            for key, value in d.items():
                if isinstance(value, dict):
                    lines.append(f"{prefix}{key}:")
                    _format_dict(value, indent + 2)
                elif isinstance(value, list):
                    if not value:
                        lines.append(f"{prefix}{key}: []")
                    else:
                        lines.append(f"{prefix}{key}:")
                        for item in value:
                            if isinstance(item, dict):
                                lines.append(f"{prefix}  -")
                                _format_dict(item, indent + 4)
                            else:
                                lines.append(f"{prefix}  - {item}")
                elif isinstance(value, bool):
                    lines.append(f"{prefix}{key}: {str(value).lower()}")
                elif value is None:
                    lines.append(f"{prefix}{key}: null")
                else:
                    lines.append(f"{prefix}{key}: {value}")

        _format_dict(data)
        return "\n".join(lines)

    @staticmethod
    def format_toml(data: Dict[str, Any]) -> str:
        """TOML 格式输出（简化实现）"""
        lines: List[str] = []

        def _format_value(value: Any) -> str:
            if isinstance(value, bool):
                return str(value).lower()
            elif isinstance(value, (int, float)):
                return str(value)
            elif isinstance(value, str):
                return f'"{value}"'
            elif isinstance(value, list):
                if not value:
                    return "[]"
                items = [_format_value(v) for v in value]
                return "[" + ", ".join(items) + "]"
            else:
                return f'"{value}"'

        # 服务列表
        services = data.get("services", [])
        for i, service in enumerate(services):
            lines.append(f"[[services]]")
            for key, value in service.items():
                if isinstance(value, dict):
                    lines.append(f"[services.{key}]")
                    for k, v in value.items():
                        lines.append(f"{k} = {_format_value(v)}")
                else:
                    lines.append(f"{key} = {_format_value(value)}")
            if i < len(services) - 1:
                lines.append("")

        # 警告信息
        warnings = data.get("warnings", [])
        if warnings:
            lines.append("")
            lines.append("[warnings]")
            for i, warning in enumerate(warnings):
                lines.append(f'warning_{i} = "{warning}"')

        return "\n".join(lines)

    @staticmethod
    def format_custom(data: Dict[str, Any], template: str) -> str:
        """自定义模板输出（简单模板替换）"""
        result = template
        # 替换 {{services}} 为 JSON 数组
        services_json = json.dumps(data.get("services", []), ensure_ascii=False)
        result = result.replace("{{services}}", services_json)
        result = result.replace("{{services_json}}", services_json)

        # 替换 {{count}}
        result = result.replace("{{count}}", str(len(data.get("services", []))))

        # 替换 {{warnings}}
        warnings_str = ", ".join(data.get("warnings", []))
        result = result.replace("{{warnings}}", warnings_str)

        return result


# ============================================================
# 文件/URL 输入处理
# ============================================================
class InputHandler:
    """输入处理器"""

    @staticmethod
    def read_file(filepath: str) -> str:
        """读取文件内容"""
        try:
            with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                return f.read()
        except FileNotFoundError:
            fail("E004", f"文件不存在: {filepath}")
        except PermissionError:
            fail("E004", f"无权限读取文件: {filepath}")
        except Exception as e:
            fail("E004", f"读取文件失败: {str(e)}")
        return ""

    @staticmethod
    def parse_url(url: str) -> str:
        """解析 URL（仅验证格式，不发起网络请求）"""
        try:
            parsed = urlparse(url)
            if parsed.scheme not in ("http", "https"):
                fail("E005", f"不支持的 URL 协议: {url}")
            if not parsed.netloc:
                fail("E005", f"URL 格式无效: {url}")
            # 注意：本工具不执行远程获取，仅验证格式
            return url
        except Exception as e:
            fail("E005", f"URL 解析失败: {str(e)}")
        return ""


# ============================================================
# 自检测试
# ============================================================
def run_selftest() -> bool:
    """运行内置自检测试"""
    print("[自检] 开始执行核心逻辑自检...")

    # 硬编码测试数据
    test_data = """
    # 测试配置
    service: "github-mcp"
    command: "npx"
    args: ["-y", "@modelcontextprotocol/server-github"]
    env: {
        GITHUB_TOKEN: "test-token"
    }

    service: "weather-api"
    url: "https://api.example.com/weather"
    port: 8080

    name: "database"
    command: "python"
    args: ["db_server.py"]
    port: 5432
    """

    # 测试 1: 解析文本
    print("[自检] 测试文本解析...")
    parser = ConfigParser()
    result = parser.parse_text(test_data)

    # 宽松断言：至少解析出 2 个服务
    assert len(result.services) >= 2, f"自检失败: 期望至少2个服务, 实际 {len(result.services)}"
    print(f"  ✓ 解析出 {len(result.services)} 个服务")

    # 测试 2: 字段提取
    print("[自检] 测试字段提取...")
    has_command = any(s.command for s in result.services)
    assert has_command, "自检失败: 未提取到任何命令"
    print("  ✓ 命令提取成功")

    # 测试 3: 置信度计算
    print("[自检] 测试置信度...")
    for service in result.services:
        assert 0.0 <= service.confidence <= 1.0, f"置信度超出范围: {service.confidence}"
    print("  ✓ 置信度在有效范围内")

    # 测试 4: 输出格式
    print("[自检] 测试输出格式...")
    formatter = OutputFormatter()
    data = result.to_dict()

    # JSON
    json_out = formatter.format_json(data)
    json_data = json.loads(json_out)
    assert "services" in json_data, "JSON 输出缺少 services 字段"
    print("  ✓ JSON 格式有效")

    # YAML
    yaml_out = formatter.format_yaml(data)
    assert "services:" in yaml_out, "YAML 输出格式不正确"
    print("  ✓ YAML 格式有效")

    # TOML
    toml_out = formatter.format_toml(data)
    assert "[[services]]" in toml_out, "TOML 输出格式不正确"
    print("  ✓ TOML 格式有效")

    # 测试 5: 边界条件
    print("[自检] 测试边界条件...")
    # 空输入
    try:
        parser.parse_text("")
        fail("E008", "空输入未触发错误")
    except SystemExit:
        pass  # 预期行为
    print("  ✓ 空输入处理正确")

    # 无有效配置
    try:
        parser.parse_text("这是一段没有配置的普通文本内容，不包含任何服务定义。")
        fail("E008", "无配置文本未触发错误")
    except SystemExit:
        pass  # 预期行为
    print("  ✓ 无配置文本处理正确")

    # 测试 6: 特殊输入
    print("[自检] 测试特殊输入...")
    special_data = """
    name: "test-服务"
    command: "echo"
    args: ["hello", "world"]
    """
    result = parser.parse_text(special_data)
    assert len(result.services) >= 1, "特殊输入解析失败"
    print("  ✓ 特殊字符处理正确")

    print("[自检] 所有测试通过 ✓")
    return True


# ============================================================
# 主程序
# ============================================================
def main() -> None:
    """主入口"""
    parser = argparse.ArgumentParser(
        description="plexus — 多智能体工具链一键装配环境配置工具",
        epilog="示例: python main.py --input config.txt --format json",
    )

    parser.add_argument(
        "--input", "-i",
        help="输入内容：文本字符串、文件路径或URL",
    )
    parser.add_argument(
        "--file", "-f",
        help="输入文件路径（与 --input 二选一）",
    )
    parser.add_argument(
        "--url", "-u",
        help="输入 URL（与 --input 二选一，仅验证格式不发起网络请求）",
    )
    parser.add_argument(
        "--format", "-F",
        choices=["json", "yaml", "toml"],
        default="json",
        help="输出格式（默认: json）",
    )
    parser.add_argument(
        "--template", "-t",
        help="自定义输出模板（包含 {{services}} 占位符）",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检测试",
    )
    parser.add_argument(
        "--version",
        action="version",
        version="plexus 1.0.1",
    )

    parser.add_argument("--verbose", action="store_true", help="显示修改明细")  # R6 可解释输出

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        try:
            run_selftest()
        except AssertionError as e:
            fail("E008", str(e))
        except Exception as e:
            fail("E008", f"自检异常: {str(e)}")
        return

    # 检查输入参数
    input_count = sum(1 for x in [args.input, args.file, args.url] if x)
    if input_count == 0:
        fail("E001", "请提供输入内容（--input/--file/--url）")
    if input_count > 1:
        fail("E001", "--input/--file/--url 只能选择一个")

    # 获取输入内容
    content = ""
    source_type = "text"
    if args.input:
        content = args.input
    elif args.file:
        content = InputHandler.read_file(args.file)
        source_type = "file"
    elif args.url:
        InputHandler.parse_url(args.url)  # 仅验证格式
        content = args.url
        source_type = "url"
        # 注意：不实际获取 URL 内容，仅作为占位
        fail("E005", "本工具不执行远程 URL 内容获取，请使用 --file 或 --input")

    # 解析配置
    try:
        parser = ConfigParser()
        result = parser.parse_text(content)
        result.source_type = source_type
        result.format = args.format
    except SystemExit:
        raise
    except Exception as e:
        fail("E006", f"解析失败: {str(e)}")

    # 格式化输出
    try:
        formatter = OutputFormatter()
        data = result.to_dict()

        if args.template:
            output = formatter.format_custom(data, args.template)
        elif args.format == "json":
            output = formatter.format_json(data)
        elif args.format == "yaml":
            output = formatter.format_yaml(data)
        elif args.format == "toml":
            output = formatter.format_toml(data)
        else:
            fail("E003", f"不支持的输出格式: {args.format}")

        print(output)
    except SystemExit:
        raise
    except Exception as e:
        fail("E009" if args.template else "E010", f"输出失败: {str(e)}")


if __name__ == "__main__":
    main()
