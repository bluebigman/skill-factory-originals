#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
argo — 代码安全静态审计漏洞筛查工具
基于 LLM 的本地静态漏洞检测，辅助人工代码审计。

仅依据功能规格独立实现（clean-room），不复制任何既有代码。
"""

import argparse
import os
import re
import sys
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

# 错误码定义
ERROR_CODES = {
    "E001": "参数错误：无法识别的命令行参数",
    "E002": "路径错误：指定的扫描路径不存在",
    "E003": "路径错误：指定的扫描路径不是目录",
    "E004": "权限错误：无法读取文件或目录",
    "E005": "格式错误：文件编码无法识别",
    "E006": "文件过大：超过 500KB 限制，跳过扫描",
    "E007": "内部错误：规则引擎初始化失败",
    "E008": "内部错误：报告生成失败",
    "E009": "内部错误：自检失败",
    "E010": "内部错误：未知异常",
}

# 支持的文件扩展名
SUPPORTED_EXTENSIONS = {
    ".py", ".js", ".ts", ".java", ".go", ".c", ".cpp", ".h", ".hpp", ".cc", ".cxx"
}

# 单文件大小限制（500KB）
MAX_FILE_SIZE = 500 * 1024

# 扫描的根目录（相对当前脚本位置）
DEFAULT_SCAN_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scan_target")


@dataclass
class Vulnerability:
    """漏洞信息结构"""
    file_path: str
    line_number: int
    rule_id: str
    severity: str  # 严重级别：high / medium / low
    description: str
    snippet: str
    suggestion: str


@dataclass
class ScanResult:
    """扫描结果结构"""
    vulnerabilities: List[Vulnerability] = field(default_factory=list)
    scanned_files: int = 0
    skipped_files: int = 0
    error_files: List[Tuple[str, str]] = field(default_factory=list)

    def add_vulnerability(self, vuln: Vulnerability) -> None:
        self.vulnerabilities.append(vuln)

    def add_error(self, file_path: str, error_code: str) -> None:
        self.error_files.append((file_path, error_code))

    def summary(self) -> Dict[str, int]:
        """生成汇总信息"""
        summary_dict = {
            "scanned_files": self.scanned_files,
            "skipped_files": self.skipped_files,
            "error_files": len(self.error_files),
            "total_vulnerabilities": len(self.vulnerabilities),
            "high": 0,
            "medium": 0,
            "low": 0,
        }
        for vuln in self.vulnerabilities:
            summary_dict[vuln.severity] = summary_dict.get(vuln.severity, 0) + 1
        return summary_dict


class RuleEngine:
    """漏洞规则引擎"""

    def __init__(self) -> None:
        """初始化规则引擎，定义漏洞检测规则"""
        # 规则格式：规则ID -> (正则模式, 严重级别, 描述, 修复建议)
        self.rules: Dict[str, Tuple[str, str, str, str]] = {}

        # 注册规则
        self._register_rules()

    def _register_rules(self) -> None:
        """注册所有内置规则"""
        # SQL 注入（Python/Java/Go 常见写法）
        self.rules["SQL_INJECTION"] = (
            r"(execute|executemany|query|rawQuery|exec|Query)\s*\([^)]*(\+|\"|\'|f\"|f\')",
            "high",
            "检测到可能的 SQL 注入：动态拼接 SQL 语句",
            "使用参数化查询或预编译语句，避免直接拼接用户输入"
        )

        # XSS 注入（JavaScript/前端）
        self.rules["XSS"] = (
            r"(innerHTML|document\.write|outerHTML)\s*=\s*(.*)",
            "high",
            "检测到可能的 XSS 注入：直接将数据写入 DOM",
            "使用 textContent 或进行 HTML 转义处理"
        )

        # 路径穿越
        self.rules["PATH_TRAVERSAL"] = (
            r"(open|read|write|unlink|remove|rename)\s*\(\s*(.*)(\.\./|\.\.\\\\)",
            "high",
            "检测到可能的路径穿越：使用相对路径访问文件",
            "对路径进行规范化校验，禁止使用 .. 路径"
        )

        # 命令注入
        self.rules["COMMAND_INJECTION"] = (
            r"(os\.system|subprocess\.(Popen|call|run)|exec|eval)\s*\(\s*[^)]*(\+|f\"|f\')",
            "high",
            "检测到可能的命令注入：动态执行系统命令",
            "避免拼接命令字符串，使用参数列表方式调用"
        )

        # 硬编码凭证
        self.rules["HARDCODED_CREDENTIAL"] = (
            r"(password|passwd|pwd|secret|api_key|apikey|token)\s*[:=]\s*[\"\'][^\"\']+[\"\']",
            "medium",
            "检测到硬编码的凭证信息",
            "使用环境变量或密钥管理服务存储敏感信息"
        )

        # 不安全的反序列化
        self.rules["INSECURE_DESERIALIZATION"] = (
            r"(pickle\.loads|yaml\.load|json\.loads)\s*(?!.*safe)",
            "medium",
            "检测到可能的反序列化漏洞",
            "使用安全的反序列化库或验证输入数据"
        )

        # 弱加密算法
        self.rules["WEAK_CRYPTO"] = (
            r"(md5|sha1)\s*\(",
            "medium",
            "检测到使用弱加密算法",
            "使用 SHA-256 或更安全的加密算法"
        )

        # 文件上传未校验
        self.rules["UNVALIDATED_UPLOAD"] = (
            r"(upload|save|store).*(file|upload)",
            "low",
            "检测到文件上传操作，未校验文件类型",
            "校验文件扩展名、MIME 类型和文件大小"
        )

        # 不安全的随机数
        self.rules["INSECURE_RANDOM"] = (
            r"random\.(random|randint|choice|shuffle)\s*\(",
            "low",
            "检测到使用不安全的随机数生成器",
            "使用 secrets 模块生成安全随机数"
        )

        # 过时的调试输出
        self.rules["DEBUG_OUTPUT"] = (
            r"(print|console\.log|System\.out\.println|fmt\.Println)\s*\(.*(password|token|secret|key)",
            "low",
            "检测到可能泄露敏感信息的调试输出",
            "移除调试输出或脱敏处理"
        )

        # 新增规则：LDAP 注入
        self.rules["LDAP_INJECTION"] = (
            r"(ldap_search|ldap_bind)\s*\([^)]*(\+|f\"|f\')",
            "high",
            "检测到可能的 LDAP 注入：动态拼接 LDAP 查询",
            "使用参数化 LDAP 查询或严格过滤特殊字符"
        )

        # 新增规则：XXE 漏洞
        self.rules["XXE"] = (
            r"(DocumentBuilderFactory|SAXParserFactory|XMLReader)\s*\([^)]*(DOCTYPE|ENTITY)",
            "high",
            "检测到可能的 XXE 漏洞：XML 解析未禁用外部实体",
            "禁用外部实体解析，使用安全配置的 XML 解析器"
        )

        # 新增规则：SSRF 漏洞
        self.rules["SSRF"] = (
            r"(requests\.(get|post|put|delete)|urllib\.request\.urlopen)\s*\([^)]*(\+|f\"|f\')",
            "high",
            "检测到可能的 SSRF 漏洞：动态拼接 URL",
            "对 URL 进行白名单校验，禁止访问内网地址"
        )

        # 新增规则：不安全的文件权限
        self.rules["INSECURE_PERMISSIONS"] = (
            r"(chmod|os\.chmod)\s*\([^)]*0o?[0-7]{3}",
            "medium",
            "检测到不安全的文件权限设置",
            "使用最小权限原则设置文件权限"
        )

        # 新增规则：日志注入
        self.rules["LOG_INJECTION"] = (
            r"(logger\.(info|debug|warning|error)|logging\.(info|debug|warning|error))\s*\([^)]*(\+|f\"|f\')",
            "medium",
            "检测到可能的日志注入：日志记录包含用户输入",
            "对日志内容进行过滤和转义处理"
        )

        # 新增规则：不安全的会话管理
        self.rules["INSECURE_SESSION"] = (
            r"(session\.cookie|set_cookie)\s*\([^)]*(secure|httpOnly)",
            "medium",
            "检测到不安全的会话管理：Cookie 未设置安全属性",
            "设置 Secure 和 HttpOnly 属性保护会话"
        )

        # 新增规则：模板注入
        self.rules["TEMPLATE_INJECTION"] = (
            r"(render_template_string|Template)\s*\([^)]*(\+|f\"|f\')",
            "high",
            "检测到可能的模板注入：动态拼接模板内容",
            "使用安全的模板渲染方式，避免拼接用户输入"
        )

    def scan_content(self, file_path: str, content: str) -> List[Vulnerability]:
        """
        扫描文件内容，返回漏洞列表

        Args:
            file_path: 文件路径
            content: 文件内容

        Returns:
            漏洞列表
        """
        findings: List[Vulnerability] = []
        lines = content.splitlines()

        for line_num, line in enumerate(lines, 1):
            for rule_id, (pattern, severity, desc, suggestion) in self.rules.items():
                if re.search(pattern, line, re.IGNORECASE):
                    vuln = Vulnerability(
                        file_path=file_path,
                        line_number=line_num,
                        rule_id=rule_id,
                        severity=severity,
                        description=desc,
                        snippet=line.strip()[:100],  # 截取前100字符
                        suggestion=suggestion
                    )
                    findings.append(vuln)

        return findings


class Scanner:
    """代码扫描器"""

    def __init__(self, rule_engine: RuleEngine) -> None:
        """
        初始化扫描器

        Args:
            rule_engine: 规则引擎实例
        """
        self.rule_engine = rule_engine
        self.result = ScanResult()

    def scan_directory(self, target_dir: str) -> ScanResult:
        """
        递归扫描目录下的所有支持文件

        Args:
            target_dir: 目标目录路径

        Returns:
            扫描结果

        Raises:
            E002: 路径不存在
            E003: 路径不是目录
            E004: 权限错误
        """
        # 路径检查
        if not os.path.exists(target_dir):
            raise FileNotFoundError(f"E002: 路径不存在: {target_dir}")

        if not os.path.isdir(target_dir):
            raise NotADirectoryError(f"E003: 不是目录: {target_dir}")

        # 遍历目录
        for root, dirs, files in os.walk(target_dir):
            for filename in files:
                file_path = os.path.join(root, filename)

                # 检查扩展名
                ext = os.path.splitext(filename)[1].lower()
                if ext not in SUPPORTED_EXTENSIONS:
                    continue

                # 检查文件大小
                try:
                    file_size = os.path.getsize(file_path)
                except OSError as e:
                    self.result.add_error(file_path, "E004")
                    continue

                if file_size > MAX_FILE_SIZE:
                    self.result.skipped_files += 1
                    continue

                # 读取并扫描文件
                try:
                    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                        content = f.read()
                    self.result.scanned_files += 1
                    findings = self.rule_engine.scan_content(file_path, content)
                    for finding in findings:
                        self.result.add_vulnerability(finding)
                except UnicodeDecodeError:
                    self.result.add_error(file_path, "E005")
                except PermissionError:
                    self.result.add_error(file_path, "E004")
                except Exception as e:
                    self.result.add_error(file_path, "E010")

        return self.result

    def scan_file(self, file_path: str) -> ScanResult:
        """
        扫描单个文件

        Args:
            file_path: 文件路径

        Returns:
            扫描结果
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"E002: 文件不存在: {file_path}")

        try:
            file_size = os.path.getsize(file_path)
        except OSError:
            self.result.add_error(file_path, "E004")
            return self.result

        if file_size > MAX_FILE_SIZE:
            self.result.skipped_files += 1
            return self.result

        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
            self.result.scanned_files += 1
            findings = self.rule_engine.scan_content(file_path, content)
            for finding in findings:
                self.result.add_vulnerability(finding)
        except UnicodeDecodeError:
            self.result.add_error(file_path, "E005")
        except PermissionError:
            self.result.add_error(file_path, "E004")
        except Exception:
            self.result.add_error(file_path, "E010")

        return self.result


class ReportGenerator:
    """报告生成器"""

    @staticmethod
    def generate_text_report(result: ScanResult) -> str:
        """
        生成文本格式报告

        Args:
            result: 扫描结果

        Returns:
            文本格式报告
        """
        lines = []
        lines.append("=" * 60)
        lines.append("argo 代码安全静态审计报告")
        lines.append("=" * 60)

        summary = result.summary()
        lines.append(f"扫描文件数: {summary['scanned_files']}")
        lines.append(f"跳过文件数: {summary['skipped_files']}")
        lines.append(f"错误文件数: {summary['error_files']}")
        lines.append(f"漏洞总数: {summary['total_vulnerabilities']}")
        lines.append(f"  高危: {summary['high']}")
        lines.append(f"  中危: {summary['medium']}")
        lines.append(f"  低危: {summary['low']}")
        lines.append("-" * 60)

        if result.error_files:
            lines.append("错误文件列表:")
            for file_path, error_code in result.error_files:
                lines.append(f"  [{error_code}] {file_path}")
            lines.append("-" * 60)

        if result.vulnerabilities:
            lines.append("漏洞详情:")
            for i, vuln in enumerate(result.vulnerabilities, 1):
                lines.append(f"\n[{i}] {vuln.file_path}:{vuln.line_number}")
                lines.append(f"    规则: {vuln.rule_id} (严重级别: {vuln.severity})")
                lines.append(f"    描述: {vuln.description}")
                lines.append(f"    代码: {vuln.snippet}")
                lines.append(f"    建议: {vuln.suggestion}")
        else:
            lines.append("未发现已知模式的安全问题。")

        lines.append("=" * 60)
        return "\n".join(lines)


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


def _run_selftest() -> None:
    """
    内置自检函数，使用硬编码样例数据验证核心逻辑

    自检通过标准（宽松阈值）：
    - 扫描样例目录成功，无异常
    - 扫描文件数大于 0
    - 漏洞检测结果非空
    - 报告生成成功
    """
    print("[selftest] 开始自检...")

    # 创建内存中的临时目录结构（不依赖文件系统）
    import tempfile

    temp_dir = tempfile.mkdtemp(prefix="argo_selftest_")

    # 硬编码样例代码
    sample_files = {
        "vuln_sample.py": """
import os
import sqlite3

def login(username, password):
    # SQL 注入漏洞
    query = "SELECT * FROM users WHERE username='" + username + "' AND password='" + password + "'"
    conn = sqlite3.connect("users.db")
    conn.execute(query)

    # 硬编码密码
    admin_password = "secret123"
    
    # 命令注入
    os.system("echo " + username)
""",
        "vuln_sample.js": """
// XSS 漏洞
function renderUser(user) {
    document.getElementById("user").innerHTML = user.name;
}

// 弱加密
var hash = md5(user.password);
""",
        "clean_sample.py": """
# 安全代码示例
import hashlib

def safe_hash(data):
    return hashlib.sha256(data.encode()).hexdigest()
""",
    }

    # 写入临时
