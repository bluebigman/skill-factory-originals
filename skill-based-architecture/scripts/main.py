#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
技能工厂：代码库萃取与规则蒸馏 —— 独立实现脚本
=================================================
本脚本根据功能规格，实现以下核心能力：
1. 代码库结构解析（目录树扫描、文件分类）
2. 规则与约定提取（从注释、配置文件名中提炼）
3. 工作流还原（识别构建、测试、发布等步骤）
4. 经验教训沉淀（识别 HACK/TODO/FIXME/NOTE/XXX 标记）
5. 技能包生成（输出 SKILL.md 文本）

仅依赖 Python 标准库，无第三方依赖。
通过 `--selftest` 参数可进行离线自检。

用法示例：
    python main.py /path/to/repo            # 分析指定代码库
    python main.py --selftest               # 运行内置自检
    python main.py --help                   # 显示帮助信息

错误码说明：
    E001: 参数错误（缺少路径或参数冲突）
    E002: 路径不存在
    E003: 路径不是目录
    E004: 目录不可读（权限问题）
    E005: 未找到任何可分析的文件
    E006: 输出文件写入失败
    E007: 自检数据初始化失败
    E008: 自检断言失败（核心逻辑错误）
    E009: 未捕获的运行时异常
    E010: 未知错误
"""

import argparse
import os
import re
import sys
import json
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple


# ============================================================
# 错误码定义
# ============================================================
ERROR_CODES = {
    "E001": "参数错误：请检查命令行参数",
    "E002": "路径不存在",
    "E003": "路径不是目录",
    "E004": "目录不可读",
    "E005": "未找到任何可分析的文件",
    "E006": "输出文件写入失败",
    "E007": "自检数据初始化失败",
    "E008": "自检断言失败",
    "E009": "未捕获的运行时异常",
    "E010": "未知错误",
}


def fail(code: str, message: Optional[str] = None) -> None:
    """输出错误信息并退出。"""
    msg = ERROR_CODES.get(code, "未知错误")
    if message:
        msg = f"{msg}：{message}"
    print(f"[错误 {code}] {msg}", file=sys.stderr)
    sys.exit(1)


# ============================================================
# 数据结构定义
# ============================================================
@dataclass
class FileInfo:
    """单个文件的元信息。"""
    path: str                          # 相对路径
    name: str                          # 文件名
    ext: str                           # 扩展名（含点，如 .py）
    category: str = "其他"             # 文件分类
    size: int = 0                      # 字节数
    annotations: List[str] = field(default_factory=list)  # 注释标记


@dataclass
class AnalysisResult:
    """一次分析的完整结果。"""
    root_path: str                     # 根路径
    total_files: int = 0               # 文件总数
    total_dirs: int = 0                # 目录总数
    total_lines: int = 0               # 总行数
    files: List[FileInfo] = field(default_factory=list)          # 所有文件
    categories: Dict[str, int] = field(default_factory=dict)     # 分类统计
    extensions: Dict[str, int] = field(default_factory=dict)     # 扩展名统计
    rules: List[Dict] = field(default_factory=list)              # 提取的规则
    workflows: List[Dict] = field(default_factory=list)          # 工作流步骤
    lessons: List[Dict] = field(default_factory=list)            # 经验教训
    module_deps: Dict[str, Set[str]] = field(default_factory=dict)  # 模块依赖
    config_files: List[str] = field(default_factory=list)        # 配置文件


# ============================================================
# 常量定义
# ============================================================
# 配置文件识别模式
CONFIG_PATTERNS = [
    r"^\.eslintrc", r"^\.prettierrc", r"^\.babelrc", r"^\.flake8",
    r"^Makefile$", r"^makefile$", r"^CMakeLists\.txt$",
    r"^package\.json$", r"^pom\.xml$", r"^build\.gradle$",
    r"^Cargo\.toml$", r"^go\.mod$", r"^requirements.*\.txt$",
    r"^pyproject\.toml$", r"^setup\.py$", r"^setup\.cfg$",
    r"^tox\.ini$", r"^\.github/workflows/", r"^\.gitlab-ci\.yml$",
    r"^Dockerfile$", r"^docker-compose.*\.yml$", r"^\.env.*$",
    r"^README.*$", r"^LICENSE.*$", r"^\.gitignore$",
    r"^\.dockerignore$", r"^\.editorconfig$", r"^\.npmrc$",
    r"^\.yarnrc$", r"^tsconfig\.json$", r"^jest\.config\.js$",
    r"^\.travis\.yml$", r"^\.circleci/", r"^Jenkinsfile$",
]

# 源代码文件扩展名
SOURCE_EXTS = {
    ".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".c", ".h",
    ".cpp", ".hpp", ".cc", ".go", ".rs", ".rb", ".php", ".swift",
    ".kt", ".scala", ".sh", ".bash", ".zsh", ".cs", ".vue",
    ".html", ".css", ".scss", ".less", ".sql", ".r", ".m",
}

# 注释标记模式（用于经验教训提取）
ANNOTATION_PATTERNS = {
    "HACK": r"//\s*HACK|#\s*HACK|/\*\s*HACK",
    "TODO": r"//\s*TODO|#\s*TODO|/\*\s*TODO",
    "FIXME": r"//\s*FIXME|#\s*FIXME|/\*\s*FIXME",
    "NOTE": r"//\s*NOTE|#\s*NOTE|/\*\s*NOTE",
    "XXX": r"//\s*XXX|#\s*XXX|/\*\s*XXX",
    "WORKAROUND": r"//\s*WORKAROUND|#\s*WORKAROUND|/\*\s*WORKAROUND",
}

# 工作流关键词
WORKFLOW_KEYWORDS = {
    "build": ["build", "编译", "构建", "compile", "make"],
    "test": ["test", "测试", "check", "verify"],
    "lint": ["lint", "静态检查", "eslint", "pylint"],
    "format": ["format", "格式化", "prettier", "black"],
    "publish": ["publish", "发布", "deploy", "部署", "release"],
    "install": ["install", "安装", "setup"],
    "clean": ["clean", "清理"],
    "docs": ["docs", "文档", "documentation"],
}

# 忽略的目录
IGNORE_DIRS = {".git", ".svn", ".hg", "__pycache__", "node_modules",
               "vendor", ".tox", ".mypy_cache", ".pytest_cache",
               "dist", "build", ".idea", ".vscode", ".next", ".nuxt"}

# 忽略的文件
IGNORE_FILES = {".DS_Store", "Thumbs.db"}


# ============================================================
# 核心逻辑实现
# ============================================================
class CodebaseAnalyzer:
    """代码库分析器：扫描目录、提取信息。"""

    def __init__(self, root_path: str):
        self.root_path = root_path
        self.result = AnalysisResult(root_path=root_path)
        self._all_files: List[str] = []

    def scan(self) -> AnalysisResult:
        """执行完整扫描流程。"""
        # 1. 扫描目录树
        self._scan_directory()
        if not self.result.files:
            fail("E005", f"路径 {self.root_path} 下未找到可分析的文件")

        # 2. 分析文件内容
        self._analyze_contents()

        # 3. 提取规则
        self._extract_rules()

        # 4. 还原工作流
        self._restore_workflows()

        # 5. 沉淀经验
        self._extract_lessons()

        return self.result

    # ---------- 目录扫描 ----------
    def _scan_directory(self) -> None:
        """递归扫描目录，收集文件信息。"""
        if not os.path.exists(self.root_path):
            fail("E002", self.root_path)
        if not os.path.isdir(self.root_path):
            fail("E003", self.root_path)
        if not os.access(self.root_path, os.R_OK):
            fail("E004", self.root_path)

        dir_count = 0
        for dirpath, dirnames, filenames in os.walk(self.root_path):
            # 过滤忽略目录
            dirnames[:] = [d for d in dirnames if d not in IGNORE_DIRS]
            dir_count += 1

            rel_dir = os.path.relpath(dirpath, self.root_path)
            if rel_dir == ".":
                rel_dir = ""

            for fname in filenames:
                if fname in IGNORE_FILES:
                    continue

                full_path = os.path.join(dirpath, fname)
                rel_path = os.path.join(rel_dir, fname) if rel_dir else fname

                try:
                    fsize = os.path.getsize(full_path)
                except OSError:
                    fsize = 0

                # 跳过二进制文件（简单判断：读取前几个字节）
                if self._is_binary(full_path):
                    continue

                ext = os.path.splitext(fname)[1].lower()
                category = self._classify_file(fname, ext, rel_path)

                file_info = FileInfo(
                    path=rel_path,
                    name=fname,
                    ext=ext,
                    category=category,
                    size=fsize,
                )
                self.result.files.append(file_info)
                self._all_files.append(rel_path)

                # 更新统计
                self.result.categories[category] = \
                    self.result.categories.get(category, 0) + 1
                if ext:
                    self.result.extensions[ext] = \
                        self.result.extensions.get(ext, 0) + 1

                # 识别配置文件
                if self._is_config_file(fname, rel_path):
                    self.result.config_files.append(rel_path)

        self.result.total_files = len(self.result.files)
        self.result.total_dirs = dir_count

    def _is_binary(self, filepath: str) -> bool:
        """判断文件是否为二进制（读取前1024字节检查空字节）。"""
        try:
            with open(filepath, "rb") as f:
                chunk = f.read(1024)
                return b"\x00" in chunk
        except OSError:
            return True

    def _classify_file(self, fname: str, ext: str, rel_path: str) -> str:
        """根据扩展名和路径对文件分类。"""
        if ext in SOURCE_EXTS:
            return "源代码"
        if ext in {".md", ".rst", ".txt"} or fname.startswith("README"):
            return "文档"
        if self._is_config_file(fname, rel_path):
            return "配置"
        if ext in {".json", ".yaml", ".yml", ".toml", ".ini", ".cfg"}:
            return "数据"
        if ext in {".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico"}:
            return "图片"
        if ext in {".ttf", ".otf", ".woff", ".woff2"}:
            return "字体"
        if ext in {".mp3", ".wav", ".ogg"}:
            return "音频"
        if ext in {".mp4", ".avi", ".mkv"}:
            return "视频"
        return "其他"

    def _is_config_file(self, fname: str, rel_path: str) -> bool:
        """判断是否为配置文件。"""
        for pattern in CONFIG_PATTERNS:
            if re.match(pattern, rel_path) or re.match(pattern, fname):
                return True
        return False

    # ---------- 内容分析 ----------
    def _analyze_contents(self) -> None:
        """分析各文件内容，提取模块依赖、行数等信息。"""
        for file_info in self.result.files:
            # 只分析文本文件
            if file_info.category not in {"源代码", "配置", "文档"}:
                continue

            full_path = os.path.join(self.root_path, file_info.path)
            try:
                with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                    lines = f.readlines()
            except OSError:
                continue

            file_info.size = sum(len(line.encode("utf-8", errors="ignore"))
                                 for line in lines)
            self.result.total_lines += len(lines)

            # 提取模块依赖（import 语句）
            if file_info.ext == ".py":
                self._extract_python_deps(lines, file_info)
            elif file_info.ext in {".js", ".ts", ".jsx", ".tsx"}:
                self._extract_js_deps(lines, file_info)
            elif file_info.ext in {".java", ".go", ".rs", ".c", ".cpp", ".h", ".hpp"}:
                self._extract_c_like_deps(lines, file_info)

            # 提取注释标记
            self._extract_annotations(lines, file_info)

    def _extract_python_deps(self, lines: List[str], file_info: FileInfo) -> None:
        """提取 Python 模块依赖。"""
        deps = set()
        for line in lines:
            stripped = line.strip()
            # import xxx 或 from xxx import yyy
            m = re.match(r"^(?:import|from)\s+([a-zA-Z_][a-zA-Z0-9_]*)", stripped)
            if m:
                deps.add(m.group(1))
            # import a.b.c 或 from a.b.c import ...
            m = re.match(r"^(?:import|from)\s+([a-zA-Z_][a-zA-Z0-9_]*\.[a-zA-Z0-9_.]+)", stripped)
            if m:
                deps.add(m.group(1).split(".")[0])
        if deps:
            self.result.module_deps[file_info.path] = deps

    def _extract_js_deps(self, lines: List[str], file_info: FileInfo) -> None:
        """提取 JavaScript/TypeScript 模块依赖。"""
        deps = set()
        for line in lines:
            stripped = line.strip()
            # import xxx from 'yyy' 或 require('yyy')
            m = re.match(r"^import\s+.*\s+from\s+['\"]([^'\"]+)['\"]", stripped)
            if m:
                deps.add(m.group(1))
            m = re.match(r"^const\s+.*=\s*require\(['\"]([^'\"]+)['\"]\)", stripped)
            if m:
                deps.add(m.group(1))
        if deps:
            self.result.module_deps[file_info.path] = deps

    def _extract_c_like_deps(self, lines: List[str], file_info: FileInfo) -> None:
        """提取 C/Java/Go 等语言的头文件依赖。"""
        deps = set()
        for line in lines:
            stripped = line.strip()
            # #include <xxx> 或 #include "xxx"
            m = re.match(r"^#include\s*[<\"]([^>\"]+)[>\"]", stripped)
            if m:
                deps.add(m.group(1))
            # import xxx
            m = re.match(r"^import\s+([a-zA-Z0-9_.]+)", stripped)
            if m:
                deps.add(m.group(1))
        if deps:
            self.result.module_deps[file_info.path] = deps

    def _extract_annotations(self, lines: List[str], file_info: FileInfo) -> None:
        """提取注释中的标记（HACK、TODO、FIXME 等）。"""
        for annotation_type, pattern in ANNOTATION_PATTERNS.items():
            for i, line in enumerate(lines, 1):
                if re.search(pattern, line):
                    file_info.annotations.append(
                        f"{annotation_type}:{i}:{line.strip()[:100]}"
                    )

    # ---------- 规则提取 ----------
    def _extract_rules(self) -> None:
        """从配置文件和代码中提取规则与约定。"""
        rules: List[Dict] = []

        # 从配置文件名提取规则
        for cfg in self.result.config_files:
            cfg_lower = cfg.lower()
            if "eslint" in cfg_lower:
                rules.append({
                    "来源": cfg,
                    "规则": "使用 ESLint 进行代码规范检查",
                    "优先级": "高",
                    "适用范围": "JavaScript/TypeScript 代码",
                })
            elif "prettier" in cfg_lower:
                rules.append({
                    "来源": cfg,
                    "规则": "使用 Prettier 统一代码格式",
                    "优先级": "中",
                    "适用范围": "前端代码",
                })
            elif "flake8" in cfg_lower or "pyproject" in cfg_lower:
                rules.append({
                    "来源": cfg,
                    "规则": "使用 Flake8 进行 Python 代码风格检查",
                    "优先级": "高",
                    "适用范围": "Python 代码",
                })
            elif "makefile" in cfg_lower:
                rules.append({
                    "来源": cfg,
                    "规则": "使用 Makefile 管理构建任务",
                    "优先级": "中",
                    "适用范围": "项目构建",
                })
            elif "dockerfile" in cfg_lower:
                rules.append({
                    "来源": cfg,
                    "规则": "使用 Docker 容器化部署",
                    "优先级": "中",
                    "适用范围": "部署环境",
                })
            elif "github" in cfg_lower or "gitlab" in cfg_lower:
                rules.append({
                    "来源": cfg,
                    "规则": "使用 CI/CD 自动化流水线",
                    "优先级": "高",
                    "适用范围": "持续集成/部署",
                })

        # 从命名规范提取规则
        for file_info in self.result.files:
            # 蛇形命名
            if file_info.ext == ".py" and re.match(r"^[a-z_]+\.py$", file_info.name):
                rules.append({
                    "来源": file_info.path,
                    "规则": "Python 文件使用蛇形命名法（snake_case）",
                    "优先级": "低",
                    "适用范围": "文件命名",
                })
            # 驼峰命名
            if file_info.ext in {".java", ".ts", ".js"} and \
                    re.match(r"^[A-Z][a-zA-Z0-9]*\.", file_info.name):
                rules.append({
                    "来源": file_info.path,
                    "规则": "类文件使用驼峰命名法（PascalCase）",
                    "优先级": "低",
                    "适用范围": "文件命名",
                })

        # 去重
        seen = set()
        unique_rules = []
        for rule in rules:
            key = (rule["规则"], rule["适用范围"])
            if key not in seen:
                seen.add(key)
                unique_rules.append(rule)

        self.result.rules = unique_rules

    # ---------- 工作流还原 ----------
    def _restore_workflows(self) -> None:
        """从配置文件和脚本中还原工作流步骤。"""
        workflows: List[Dict] = []
        steps: Dict[str, List[str]] = defaultdict(list)

        # 读取 Makefile
        for cfg in self.result.config_files:
            if os.path.basename(cfg).lower() == "makefile":
                full_path = os.path.join(self.root_path, cfg)
                try:
                    with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                    # 提取目标
                    for m in re.finditer(r"^([a-zA-Z_-]+)\s*:", content, re.MULTILINE):
                        target = m.group(1)
                        for wf_type, keywords in WORKFLOW_KEYWORDS.items():
                            if any(kw in target.lower() for kw in keywords):
                                steps[wf_type].append(target)
                except OSError:
                    pass

            # 读取 package.json
            if os.path.basename(cfg) == "package.json":
                full_path = os.path.join(self.root_path, cfg)
                try:
                    with open(full_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    scripts = data.get("scripts", {})
                    for name, cmd in scripts.items():
                        for wf_type, keywords in WORKFLOW_KEYWORDS.items():
                            if any(kw in name.lower() or kw in str(cmd).lower()
                                   for kw in keywords):
                                steps[wf_type].append(f"{name}: {cmd}")
                except (OSError, json.JSONDecodeError):
                    pass

            # 读取 CI 配置
            if "github" in cfg.lower() or "gitlab" in cfg.lower() or "jenkins" in cfg.lower():
                full_path = os.path.join(self.root_path, cfg)
                try:
                    with open(full_path, "r", encoding="utf-8") as f:
                        content = f.read()
                    # 提取 job 名称
                    for m in re.finditer(r"^([a-zA-Z_-]+):", content, re.MULTILINE):
                        job = m.group(1)
                        if job not in {"on", "env", "jobs", "steps", "name", "runs-on"}:
                            steps["ci"].append(job)
                except OSError:
                    pass

        # 整理输出
        for wf_type, step_list in steps.items():
            if step_list:
                workflows.append({
                    "流程类型": wf_type,
                    "步骤": step_list,
                    "步骤数": len(step_list),
                })

        self.result.workflows = workflows

    # ---------- 经验沉淀 ----------
    def _extract_lessons(self) -> None:
        """从代码注释中提取经验教训。"""
        lessons: List[Dict] = []
        for file_info in self.result.files:
            for annotation in file_info.annotations:
                ann_type, line_no, text = annotation.split(":", 2)
                lessons.append({
                    "文件": file_info.path,
                    "行号": int(line_no),
                    "类型": ann_type,
                    "内容": text,
                })
        self.result.lessons = lessons


# ============================================================
# 输出格式化
# ============================================================
def format_report(result: AnalysisResult) -> str:
    """将分析结果格式化为可读文本报告。"""
    lines = []
    lines.append("=" * 60)
    lines.append(f"代码库分析报告")
    lines.append(f"根路径: {result.root_path}")
    lines.append("=" * 60)

    # 基本统计
    lines.append(f"\n【基本统计】")
    lines.append(f"  文件总数: {result.total_files}")
    lines.append(f"  目录总数: {result.total_dirs}")
    lines.append(f"  代码总行数: {result.total_lines}")

    # 分类统计
    lines.append(f"\n【文件分类】")
    for cat, count in sorted(result.categories.items(), key=lambda x: -x[1]):
        lines.append(f"  {cat}: {count}")

    # 扩展名统计
    if result.extensions:
        lines.append(f"\n【扩展名分布】")
        for ext, count in sorted(result.extensions.items(), key=lambda x: -x[1]):
            lines.append(f"  {ext}: {count}")

    # 配置文件
    if result.config_files:
        lines.append(f"\n【配置文件】")
        for cfg in result.config_files:
            lines.append(f"  - {cfg}")

    # 规则
    if result.rules:
        lines.append(f"\n【提取规则】")
        for i, rule in enumerate(result.rules, 1):
            lines.append(f"  {i}. [{rule['优先级']}] {rule['规则']}")
            lines.append(f"     来源: {rule['来源']} | 适用范围: {rule['适用范围']}")

    # 工作流
    if result.workflows:
        lines.append(f"\n【工作流还原】")
        for wf in result.workflows:
            lines.append(f"  [{wf['流程类型']}] {wf['步骤数']} 个步骤")
            for step in wf["步骤"]:
                lines.append(f"    - {step}")

    # 经验教训
    if result.lessons:
        lines.append(f"\n【经验教训】")
        for i, lesson in enumerate(result.lessons[:20], 1):  # 最多显示20条
            lines.append(f"  {i}. [{lesson['类型']}] {lesson['文件']}:{lesson['行号']}")
            lines.append(f"     {lesson['内容']}")
        if len(result.lessons) > 20:
            lines.append(f"  ... 还有 {len(result.lessons) - 20} 条")

    # 模块依赖
    if result.module_deps:
        lines.append(f"\n【模块依赖】")
        for module, deps in list(result.module_deps.items())[:10]:
            lines.append(f"  {module} -> {', '.join(sorted(deps)[:5])}")
        if len(result.module_deps) > 10:
            lines.append(f"  ... 还有 {len(result.module_deps) - 10} 个模块")

    lines.append("\n" + "=" * 60)
    lines.append("报告生成完毕")
    lines.append("=" * 60)

    return "\n".join(lines)


def generate_skill_md(result: AnalysisResult) -> str:
    """生成 SKILL.md 格式的技能包文档。"""
    lines = []
    lines.append("---")
    lines.append("slug: skill-based-architecture")
    lines.append("name: skill-based-architecture")
    lines.append("displayName: 技能工厂 代码库萃取 规则蒸馏")
    lines.append("description: 将任意代码库转化为可复用技能包，提炼规则、流程与经验。")
    lines.append("version: 1.0.1")
    lines.append("license: MIT")
    lines.append("---")
    lines.append("")
    lines.append("# 技能工厂：代码库萃取与规则蒸馏")
    lines.append("")
    lines.append(f"> 本技能包由代码库分析工具自动生成")
    lines.append(f"> 分析时间: {__import__('datetime').datetime.now().isoformat()}")
    lines.append(f"> 源路径: {result.root_path}")
    lines.append("")
    lines.append("## 项目概览")
    lines.append("")
    lines.append(f"- 文件总数: {result.total_files}")
    lines.append(f"- 目录总数: {result.total_dirs}")
    lines.append(f"- 代码总行数: {result.total_lines}")
    lines.append("")
    lines.append("## 文件分类")
    lines.append("")
    lines.append("| 分类 | 数量 |")
    lines.append("|------|------|")
    for cat, count in sorted(result.categories.items(), key=lambda x: -x[1]):
        lines.append(f"| {cat} | {count} |")
    lines.append("")
    lines.append("## 提取的规则")
    lines.append("")
    for i, rule in enumerate(result.rules, 1):
        lines.append(f"{i}. **[{rule['优先级']}]** {rule['规则']}")
        lines.append(f"   - 来源: `{rule['来源']}`")
        lines.append(f"   - 适用范围: {rule['适用范围']}")
    lines.append("")
    lines.append("## 工作流")
    lines.append("")
    for wf in result.workflows:
        lines.append(f"### {wf['流程类型']}")
        lines.append("")
        for step in wf["步骤"]:
            lines.append(f"- {step}")
        lines.append("")
    lines.append("## 经验教训")
    lines.append("")
    for lesson in result.lessons[:50]:
        lines.append(f"- [{lesson['类型']}] `{lesson['文件']}:{lesson['行号']}`: {lesson['内容']}")
    lines.append("")
    lines.append("---")
    lines.append("## 用户协议")
    lines.append("")
    lines.append("> 本技能包仅供学习与参考用途。使用本技能包产生的任何结果，由使用者自行承担全部责任。")
    lines.append("> 涉及法律、财务、税务、投资、医疗等专业决策时，请务必咨询持证专业人士。")
    lines.append("")
    lines.append("## 许可证")
    lines.append("")
    lines.append("
