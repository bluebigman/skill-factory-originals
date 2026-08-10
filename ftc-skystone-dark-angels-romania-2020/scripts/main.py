#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FTC SKYSTONE 机器人项目代码结构审查工具
=========================================
本脚本依据功能规格独立实现（clean-room），提供以下能力：
  1. 解析 FTC 机器人项目目录结构
  2. 识别 OpMode、硬件映射、工具类、配置类等模块
  3. 梳理类之间的继承、接口实现关系
  4. 检查命名、注释等代码规范问题
  5. 标注潜在风险点（空指针、资源泄漏、并发问题）
  6. 生成结构化 Markdown 审查报告

仅使用 Python 标准库实现，无第三方依赖。

用法示例：
  python scripts/main.py /path/to/ftc_project
  python scripts/main.py --selftest
"""

import argparse
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple


# ============================================================
# 常量定义与错误码
# ============================================================

# 错误码：E001~E010
ERROR_CODES = {
    "E001": "参数错误：路径不存在或不可访问",
    "E002": "参数错误：路径不是目录",
    "E003": "IO错误：读取文件失败",
    "E004": "解析错误：无法识别的文件结构",
    "E005": "解析错误：无效的 Java 语法",
    "E006": "内部错误：模块分类异常",
    "E007": "内部错误：依赖分析异常",
    "E008": "内部错误：规范检查异常",
    "E009": "内部错误：报告生成异常",
    "E010": "内部错误：未知异常",
}

# 模块分类关键字
OPMODE_KEYWORDS = ["OpMode", "LinearOpMode", "IterativeOpMode"]
HARDWARE_KEYWORDS = ["HardwareMap", "Hardware", "Motor", "Servo", "Sensor"]
UTIL_KEYWORDS = ["Util", "Helper", "Tool", "Math"]
CONFIG_KEYWORDS = ["Config", "Constants", "Settings", "Parameters"]

# 规范检查规则（宽松版）
MIN_COMMENT_RATIO = 0.05  # 注释行占比下限（宽松阈值）
MAX_LINE_LENGTH = 200     # 行长度上限（宽松阈值）
MIN_FILE_NAME_LEN = 3     # 文件名最小长度

# 风险模式（正则表达式）
RISK_PATTERNS = {
    "空指针风险": re.compile(r"\.get\w*\(\s*\)\s*\.", re.IGNORECASE),
    "资源泄漏风险": re.compile(r"(new\s+FileInputStream|new\s+FileOutputStream|openConnection)", re.IGNORECASE),
    "并发风险": re.compile(r"(synchronized|Thread\.start|volatile)", re.IGNORECASE),
    "硬编码风险": re.compile(r"(telemetry\.addData\(\s*\"[^\"]+\"\s*,\s*\"[^\"]*\")", re.IGNORECASE),
}


# ============================================================
# 数据结构定义
# ============================================================

@dataclass
class JavaFileInfo:
    """单个 Java 文件的结构信息"""
    path: Path
    package: str = ""
    imports: List[str] = field(default_factory=list)
    classes: List[str] = field(default_factory=list)
    class_types: Dict[str, str] = field(default_factory=dict)  # 类名 -> 类型
    parent_classes: Dict[str, str] = field(default_factory=dict)  # 类名 -> 父类
    interfaces: Dict[str, List[str]] = field(default_factory=dict)  # 类名 -> 接口列表
    methods: List[str] = field(default_factory=list)
    fields: List[str] = field(default_factory=list)
    total_lines: int = 0
    comment_lines: int = 0
    max_line_length: int = 0
    has_todo: bool = False
    module_category: str = "未分类"
    risks: List[Tuple[str, str]] = field(default_factory=list)  # (风险类型, 描述)
    violations: List[str] = field(default_factory=list)  # 规范问题


@dataclass
class ProjectInfo:
    """项目整体结构信息"""
    root: Path
    java_files: List[JavaFileInfo] = field(default_factory=list)
    package_structure: Dict[str, List[str]] = field(default_factory=dict)
    module_stats: Dict[str, int] = field(default_factory=dict)
    dependency_graph: Dict[str, Set[str]] = field(default_factory=dict)


# ============================================================
# 核心解析逻辑
# ============================================================

class ProjectParser:
    """FTC 项目解析器：负责目录扫描与文件解析"""

    def __init__(self, root_path: str):
        self.root = Path(root_path)
        self.project = ProjectInfo(root=self.root)
        self._validate_root()

    def _validate_root(self) -> None:
        """验证根路径有效性"""
        if not self.root.exists():
            raise ValueError(f"E001: {ERROR_CODES['E001']} - {self.root}")
        if not self.root.is_dir():
            raise ValueError(f"E002: {ERROR_CODES['E002']} - {self.root}")

    def parse(self) -> ProjectInfo:
        """执行完整解析流程"""
        try:
            self._scan_files()
            self._parse_all_files()
            self._build_package_structure()
            self._build_dependency_graph()
            self._compute_module_stats()
            return self.project
        except ValueError:
            raise
        except Exception as e:
            raise RuntimeError(f"E010: {ERROR_CODES['E010']} - {e}")

    def _scan_files(self) -> None:
        """扫描所有 Java 文件"""
        for path in self.root.rglob("*.java"):
            if path.is_file():
                self.project.java_files.append(JavaFileInfo(path=path))

    def _parse_all_files(self) -> None:
        """解析所有 Java 文件"""
        for file_info in self.project.java_files:
            try:
                self._parse_file(file_info)
            except UnicodeDecodeError:
                raise RuntimeError(f"E003: {ERROR_CODES['E003']} - 编码错误: {file_info.path}")
            except Exception as e:
                raise RuntimeError(f"E005: {ERROR_CODES['E005']} - {file_info.path}: {e}")

    def _parse_file(self, file_info: JavaFileInfo) -> None:
        """解析单个 Java 文件"""
        try:
            content = file_info.path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            content = file_info.path.read_text(encoding="latin-1", errors="replace")

        lines = content.splitlines()
        file_info.total_lines = len(lines)
        file_info.max_line_length = max((len(line) for line in lines), default=0)

        # 统计注释行（宽松：以 // 或 * 开头）
        file_info.comment_lines = sum(
            1 for line in lines
            if line.strip().startswith("//") or line.strip().startswith("*")
        )
        file_info.has_todo = any("TODO" in line.upper() for line in lines)

        # 解析 package 声明
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("package "):
                file_info.package = stripped.replace("package", "").replace(";", "").strip()
                break

        # 解析 import 语句
        file_info.imports = [
            line.strip().replace("import", "").replace(";", "").strip()
            for line in lines
            if line.strip().startswith("import ")
        ]

        # 解析类声明（宽松正则）
        class_pattern = re.compile(
            r"(public\s+|private\s+|protected\s+)?(abstract\s+|final\s+)?class\s+(\w+)"
            r"(\s+extends\s+(\w+))?(\s+implements\s+([\w,\s]+))?"
        )
        for line in lines:
            match = class_pattern.search(line)
            if match:
                class_name = match.group(3)
                file_info.classes.append(class_name)
                parent = match.group(5) or ""
                file_info.parent_classes[class_name] = parent
                interfaces = [i.strip() for i in (match.group(7) or "").split(",") if i.strip()]
                file_info.interfaces[class_name] = interfaces

                # 分类模块
                file_info.module_category = self._categorize_module(
                    class_name, parent, interfaces, file_info.imports
                )

        # 解析方法名（宽松）
        method_pattern = re.compile(r"(public|private|protected)\s+[\w<>\[\]]+\s+(\w+)\s*\(")
        file_info.methods = [
            match.group(2) for line in lines
            for match in [method_pattern.search(line)]
            if match
        ]

        # 解析字段名（宽松）
        field_pattern = re.compile(r"(public|private|protected)\s+(static\s+)?[\w<>\[\]]+\s+(\w+)\s*[=;]")
        file_info.fields = [
            match.group(3) for line in lines
            for match in [field_pattern.search(line)]
            if match
        ]

        # 风险检测
        self._detect_risks(file_info, lines)

        # 规范检查
        self._check_violations(file_info)

    def _categorize_module(self, class_name: str, parent: str,
                           interfaces: List[str], imports: List[str]) -> str:
        """根据类特征分类模块"""
        text = f"{class_name} {parent} {' '.join(interfaces)} {' '.join(imports)}"

        # 检查 OpMode
        if any(kw.lower() in text.lower() for kw in OPMODE_KEYWORDS):
            return "OpMode"

        # 检查硬件映射
        if any(kw.lower() in text.lower() for kw in HARDWARE_KEYWORDS):
            return "硬件映射"

        # 检查配置类
        if any(kw.lower() in text.lower() for kw in CONFIG_KEYWORDS):
            return "配置类"

        # 检查工具类
        if any(kw.lower() in text.lower() for kw in UTIL_KEYWORDS):
            return "工具类"

        return "其他"

    def _detect_risks(self, file_info: JavaFileInfo, lines: List[str]) -> None:
        """检测代码风险点"""
        for i, line in enumerate(lines, 1):
            for risk_type, pattern in RISK_PATTERNS.items():
                if pattern.search(line):
                    file_info.risks.append((risk_type, f"第{i}行: {line.strip()[:80]}"))

    def _check_violations(self, file_info: JavaFileInfo) -> None:
        """检查代码规范问题"""
        # 注释比例检查（宽松阈值）
        if file_info.total_lines > 0:
            ratio = file_info.comment_lines / file_info.total_lines
            if ratio < MIN_COMMENT_RATIO:
                file_info.violations.append(
                    f"注释比例过低: {ratio:.1%} (建议 >= {MIN_COMMENT_RATIO:.0%})"
                )

        # 行长度检查
        if file_info.max_line_length > MAX_LINE_LENGTH:
            file_info.violations.append(
                f"存在超过 {MAX_LINE_LENGTH} 字符的行 (最长 {file_info.max_line_length})"
            )

        # 文件名检查
        stem = file_info.path.stem
        if len(stem) < MIN_FILE_NAME_LEN:
            file_info.violations.append(f"文件名过短: {stem}")

    def _build_package_structure(self) -> None:
        """构建包结构"""
        for file_info in self.project.java_files:
            if file_info.package:
                if file_info.package not in self.project.package_structure:
                    self.project.package_structure[file_info.package] = []
                self.project.package_structure[file_info.package].append(str(file_info.path))

    def _build_dependency_graph(self) -> None:
        """构建依赖关系图（基于 import 和继承）"""
        for file_info in self.project.java_files:
            deps = set()
            # 从 imports 中提取类名
            for imp in file_info.imports:
                parts = imp.split(".")
                if parts:
                    deps.add(parts[-1])
            # 添加父类和接口
            for parent in file_info.parent_classes.values():
                if parent:
                    deps.add(parent)
            for ifaces in file_info.interfaces.values():
                for iface in ifaces:
                    deps.add(iface)
            self.project.dependency_graph[str(file_info.path)] = deps

    def _compute_module_stats(self) -> None:
        """统计各模块数量"""
        for file_info in self.project.java_files:
            cat = file_info.module_category
            self.project.module_stats[cat] = self.project.module_stats.get(cat, 0) + 1


# ============================================================
# 报告生成
# ============================================================

class ReportGenerator:
    """生成 Markdown 审查报告"""

    def __init__(self, project: ProjectInfo):
        self.project = project

    def generate(self) -> str:
        """生成完整报告"""
        try:
            lines = []
            lines.append("# FTC SKYSTONE 机器人项目代码结构审查报告")
            lines.append("")
            lines.append(f"> 生成时间: 自动生成 | 项目根目录: `{self.project.root}`")
            lines.append("")
            lines.append("---")
            lines.append("")

            lines.extend(self._generate_overview())
            lines.extend(self._generate_structure())
            lines.extend(self._generate_modules())
            lines.extend(self._generate_dependencies())
            lines.extend(self._generate_risks())
            lines.extend(self._generate_violations())
            lines.extend(self._generate_summary())

            return "\n".join(lines)
        except Exception as e:
            raise RuntimeError(f"E009: {ERROR_CODES['E009']} - {e}")

    def _generate_overview(self) -> List[str]:
        """生成项目概览"""
        total_files = len(self.project.java_files)
        total_lines = sum(f.total_lines for f in self.project.java_files)
        total_comments = sum(f.comment_lines for f in self.project.java_files)
        total_risks = sum(len(f.risks) for f in self.project.java_files)
        total_violations = sum(len(f.violations) for f in self.project.java_files)

        lines = ["## 一、项目概览", ""]
        lines.append("| 指标 | 数值 |")
        lines.append("|------|------|")
        lines.append(f"| Java 文件数 | {total_files} |")
        lines.append(f"| 总代码行数 | {total_lines} |")
        lines.append(f"| 总注释行数 | {total_comments} |")
        if total_lines > 0:
            lines.append(f"| 注释占比 | {total_comments/total_lines:.1%} |")
        else:
            lines.append("| 注释占比 | 0% |")
        lines.append(f"| 风险点总数 | {total_risks} |")
        lines.append(f"| 规范问题总数 | {total_violations} |")
        lines.append("")
        return lines

    def _generate_structure(self) -> List[str]:
        """生成目录结构"""
        lines = ["## 二、目录结构", ""]
        lines.append("")
