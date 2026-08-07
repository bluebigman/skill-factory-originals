#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FTC SKYSTONE 机器人项目代码结构审查工具

本脚本依据功能规格独立实现，用于：
1. 解析 FTC 机器人项目目录结构
2. 识别 OpMode、硬件映射、工具类、配置类等模块
3. 分析类之间的依赖关系
4. 检查代码规范问题
5. 标注潜在风险点
6. 生成结构化 Markdown 审查报告

仅使用 Python 标准库实现，无第三方依赖。
"""

import os
import re
import sys
import json
import hashlib
from pathlib import Path
from datetime import datetime
from collections import defaultdict


# ============================================================
# 错误码定义
# ============================================================
ERROR_CODES = {
    "E001": "参数错误：缺少必要参数或参数格式不正确",
    "E002": "路径错误：指定的项目路径不存在",
    "E003": "路径错误：指定的路径不是目录",
    "E004": "读取错误：无法读取文件内容",
    "E005": "解析错误：无法解析 Java 文件",
    "E006": "解析错误：无法解析依赖关系",
    "E007": "生成错误：无法生成审查报告",
    "E008": "自检错误：自检失败",
    "E009": "IO错误：文件操作失败",
    "E010": "未知错误：发生未预期的异常",
}


# ============================================================
# 模块分类定义
# ============================================================
MODULE_CATEGORIES = {
    "opmode": {
        "patterns": [
            r"@Autonomous",
            r"@TeleOp",
            r"@Disabled",
            r"extends\s+OpMode",
            r"extends\s+LinearOpMode",
        ],
        "description": "OpMode 操作模式",
    },
    "hardware": {
        "patterns": [
            r"HardwareMap",
            r"hardwareMap",
            r"Servo",
            r"DcMotor",
            r"Motor",
            r"IMU",
            r"Gyro",
            r"TouchSensor",
            r"ColorSensor",
            r"DistanceSensor",
        ],
        "description": "硬件映射与驱动",
    },
    "utility": {
        "patterns": [
            r"class\s+\w*Util",
            r"class\s+\w*Helper",
            r"class\s+\w*Tool",
            r"class\s+\w*Util\w*",
            r"static\s+\w+\s+\w+\s*\(",
            r"public\s+static",
        ],
        "description": "工具类",
    },
    "config": {
        "patterns": [
            r"Config",
            r"config",
            r"Constants",
            r"constants",
            r"Settings",
            r"settings",
            r"Parameters",
            r"parameters",
        ],
        "description": "配置类",
    },
    "telemetry": {
        "patterns": [
            r"Telemetry",
            r"telemetry",
            r"Dashboard",
            r"dashboard",
        ],
        "description": "遥测与数据展示",
    },
    "control": {
        "patterns": [
            r"PID",
            r"pid",
            r"Controller",
            r"controller",
            r"Feedback",
            r"feedback",
            r"Loop",
            r"loop",
        ],
        "description": "控制算法",
    },
}


# ============================================================
# 代码规范检查规则
# ============================================================
STYLE_RULES = {
    "class_naming": {
        "pattern": r"class\s+([A-Z][a-zA-Z0-9]*)",
        "description": "类名应使用大驼峰命名法（PascalCase）",
        "check": lambda name: name[0].isupper() if name else False,
    },
    "method_naming": {
        "pattern": r"(?:public|private|protected)\s+(?:static\s+)?[\w<>\[\]]+\s+([a-z]\w*)\s*\(",
        "description": "方法名应使用小驼峰命名法（camelCase）",
        "check": lambda name: name[0].islower() if name else False,
    },
    "constant_naming": {
        "pattern": r"(?:public|private|protected)\s+(?:static\s+)?final\s+[\w<>\[\]]+\s+([A-Z_][A-Z0-9_]*)",
        "description": "常量名应使用全大写加下划线",
        "check": lambda name: "_" in name or name.isupper() if name else False,
    },
    "field_naming": {
        "pattern": r"(?:public|private|protected)\s+(?!static\s+final)[\w<>\[\]]+\s+([a-z]\w*)\s*[=;]",
        "description": "成员变量名应使用小驼峰命名法",
        "check": lambda name: name[0].islower() if name else False,
    },
}


# ============================================================
# 风险检测规则
# ============================================================
RISK_PATTERNS = [
    {
        "name": "空指针风险",
        "pattern": r"(?:\.\w+\(\)|\.\w+)\s*\.\s*\w+",
        "description": "链式调用可能导致空指针异常",
        "severity": "high",
    },
    {
        "name": "资源未关闭",
        "pattern": r"(?:FileInputStream|FileOutputStream|BufferedReader|BufferedWriter|PrintWriter|Scanner)\s+\w+\s*=",
        "description": "IO 资源可能未关闭",
        "severity": "medium",
    },
    {
        "name": "硬编码值",
        "pattern": r"=\s*[-+]?\d{2,}",
        "description": "疑似硬编码的魔法数字",
        "severity": "low",
    },
    {
        "name": "线程安全风险",
        "pattern": r"(?:static\s+)?\w+\s+(\w+)\s*;",
        "description": "共享变量可能未同步",
        "severity": "medium",
    },
    {
        "name": "异常吞没",
        "pattern": r"catch\s*\([^)]*\)\s*\{\s*\}",
        "description": "空的 catch 块可能吞没异常",
        "severity": "medium",
    },
    {
        "name": "TODO/FIXME",
        "pattern": r"(?:TODO|FIXME|XXX|HACK)",
        "description": "存在未完成的开发标记",
        "severity": "low",
    },
]


# ============================================================
# 核心数据结构
# ============================================================
class JavaFileInfo:
    """Java 文件信息"""

    def __init__(self, file_path):
        self.file_path = file_path
        self.file_name = Path(file_path).name
        self.package = ""
        self.imports = []
        self.classes = []
        self.methods = []
        self.fields = []
        self.annotations = []
        self.categories = []
        self.risks = []
        self.style_issues = []
        self.dependencies = []
        self.content = ""
        self.class_name = ""
        self.super_class = ""
        self.interfaces = []
        self.total_lines = 0


class ProjectInfo:
    """项目信息"""

    def __init__(self, root_path):
        self.root_path = root_path
        self.project_name = Path(root_path).name
        self.java_files = []
        self.total_files = 0
        self.total_lines = 0
        self.total_classes = 0
        self.total_methods = 0
        self.dependencies = defaultdict(list)
        self.modules = defaultdict(list)
        self.issues = []
        self.risks = []
        self.file_count = 0
        self.dir_count = 0


# ============================================================
# 文件扫描与解析
# ============================================================
def scan_project(root_path):
    """扫描项目目录，收集所有 Java 文件"""
    try:
        root = Path(root_path)
        if not root.exists():
            return None, "E002"
        if not root.is_dir():
            return None, "E003"

        project = ProjectInfo(root)
        java_files = []
        dir_count = 0

        for dirpath, dirnames, filenames in os.walk(root):
            # 跳过构建目录和版本控制目录
            dirnames[:] = [d for d in dirnames if d not in
                          ['.git', '.gradle', 'build', '.idea', '.settings']]
            dir_count += len(dirnames)

            for filename in filenames:
                if filename.endswith('.java'):
                    file_path = os.path.join(dirpath, filename)
                    java_files.append(file_path)

        project.java_files = java_files
        project.file_count = len(java_files)
        project.dir_count = dir_count
        return project, None

    except Exception:
        return None, "E010"


def read_file(file_path):
    """读取文件内容"""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read(), None
    except Exception:
        try:
            with open(file_path, 'r', encoding='latin-1') as f:
                return f.read(), None
        except Exception:
            return None, "E004"


def parse_java_file(file_path, content):
    """解析 Java 文件，提取结构信息"""
    try:
        info = JavaFileInfo(file_path)
        info.content = content
        lines = content.split('\n')
        info.total_lines = len(lines)

        # 提取包名
        package_match = re.search(r'package\s+([\w.]+)\s*;', content)
        if package_match:
            info.package = package_match.group(1)

        # 提取导入语句
        info.imports = re.findall(r'import\s+(?:static\s+)?([\w.]+)\s*;', content)

        # 提取类定义
        class_pattern = r'@?\w*\s*class\s+(\w+)(?:\s+extends\s+(\w+))?(?:\s+implements\s+([\w,\s]+))?'
        for match in re.finditer(class_pattern, content):
            class_name = match.group(1)
            super_class = match.group(2)
            interfaces = match.group(3)
            info.classes.append(class_name)
            if not info.class_name:
                info.class_name = class_name
            if super_class:
                info.super_class = super_class
            if interfaces:
                info.interfaces = [i.strip() for i in interfaces.split(',')]

        # 提取方法定义
        method_pattern = r'(?:public|private|protected)\s+(?:static\s+)?(?:final\s+)?[\w<>\[\]]+\s+(\w+)\s*\('
        info.methods = re.findall(method_pattern, content)

        # 提取成员变量
        field_pattern = r'(?:public|private|protected)\s+(?!static\s+final)(?:static\s+)?[\w<>\[\]]+\s+(\w+)\s*[=;]'
        info.fields = re.findall(field_pattern, content)

        # 提取注解
        info.annotations = re.findall(r'@(\w+)', content)

        # 识别模块类别
        for category, rules in MODULE_CATEGORIES.items():
            for pattern in rules['patterns']:
                if re.search(pattern, content):
                    if category not in info.categories:
                        info.categories.append(category)
                    break

        # 提取依赖关系（通过导入和类引用）
        for imp in info.imports:
            dep_class = imp.split('.')[-1]
            info.dependencies.append(dep_class)
            # 检查是否在代码中实际使用
            if re.search(r'\b' + dep_class + r'\b', content):
                info.dependencies.append(dep_class + "_used")

        return info, None

    except Exception:
        return None, "E005"


def check_style_rules(info):
    """检查代码规范"""
    issues = []
    content = info.content

    for rule_name, rule in STYLE_RULES.items():
        try:
            for match in re.finditer(rule['pattern'], content):
                name = match.group(1)
                if not rule['check'](name):
                    issues.append({
                        "type": "style",
                        "rule": rule_name,
                        "name": name,
                        "description": rule['description'],
                        "line": content[:match.start()].count('\n') + 1,
                        "severity": "warning",
                    })
        except Exception:
            continue

    return issues


def detect_risks(info):
    """检测潜在风险"""
    risks = []
    content = info.content

    for risk in RISK_PATTERNS:
        try:
            matches = list(re.finditer(risk['pattern'], content))
            if matches:
                # 限制每个文件每个风险类型最多报告3处
                for match in matches[:3]:
                    line_no = content[:match.start()].count('\n') + 1
                    risks.append({
                        "type": "risk",
                        "name": risk['name'],
                        "description": risk['description'],
                        "line": line_no,
                        "severity": risk['severity'],
                        "code": content[max(0, match.start()-20):match.end()+20].strip(),
                    })
        except Exception:
            continue

    return risks


# ============================================================
# 依赖分析
# ============================================================
def analyze_dependencies(project):
    """分析项目依赖关系"""
    try:
        # 建立类名到文件的映射
        class_map = {}
        for file_path in project.java_files:
            content, _ = read_file(file_path)
            if content:
                info, _ = parse_java_file(file_path, content)
                if info and info.class_name:
                    class_map[info.class_name] = file_path

        # 分析依赖
        for file_path in project.java_files:
            content, _ = read_file(file_path)
            if not content:
                continue

            file_name = Path(file_path).name
            project.dependencies[file_name] = []

            # 查找所有类引用
            for class_name in class_map:
                if class_name != Path(file_path).stem:
                    if re.search(r'\b' + class_name + r'\b', content):
                        project.dependencies[file_name].append({
                            "target": class_name,
                            "target_file": class_map[class_name],
                            "type": "reference",
                        })

        return None

    except Exception:
        return "E006"


# ============================================================
# 报告生成
# ============================================================
def generate_report(project):
    """生成 Markdown 格式的审查报告"""
    try:
        report_lines = []
        report_lines.append("# FTC 机器人项目代码结构审查报告\n")
        report_lines.append("## 项目信息\n")
        report_lines.append("- 项目名称: " + project.project_name)
        report_lines.append("- 项目路径: " + project.root_path)
        report_lines.append("- 扫描时间: " + datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        report_lines.append("- Java 文件数: " + str(project.file_count))
        report_lines.append("- 目录数: " + str(project.dir_count) + "\n")

        # 目录结构
        report_lines.append("## 目录结构\n")
        report_lines.append("
