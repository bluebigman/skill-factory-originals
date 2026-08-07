#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py — 技能工厂：代码库萃取与规则蒸馏（独立实现）

本脚本根据 clean-room 原则独立编写，仅依据功能规格设计，
不复制任何既有代码。提供命令行工具与离线自检功能。
"""

import argparse
import os
import re
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

# 错误码定义
ERROR_CODES = {
    "E001": "参数错误：无法识别的命令行参数",
    "E002": "路径错误：目标代码库路径不存在",
    "E003": "路径错误：目标路径不是目录",
    "E004": "配置错误：未找到任何受支持的配置文件",
    "E005": "解析错误：无法读取文件内容",
    "E006": "解析错误：文件编码不受支持",
    "E007": "分析错误：文件类型无法识别",
    "E008": "生成错误：无法写入输出文件",
    "E009": "自检错误：内置自检数据缺失",
    "E010": "运行时错误：未捕获的异常",
}


@dataclass
class SkillPackage:
    """技能包数据模型，用于聚合萃取结果"""
    project_name: str = ""
    modules: List[str] = field(default_factory=list)
    rules: List[Dict] = field(default_factory=list)
    workflows: List[Dict] = field(default_factory=list)
    experiences: List[Dict] = field(default_factory=list)
    config_files: List[str] = field(default_factory=list)
    file_count: int = 0
    dir_count: int = 0
    total_lines: int = 0


class CodebaseAnalyzer:
    """代码库静态分析器：解析目录结构、提取规则与经验"""

    # 常见配置文件识别模式（配置文件名 -> 配置类型）
    CONFIG_PATTERNS = {
        "package.json": "node",
        "pom.xml": "java",
        "Cargo.toml": "rust",
        "go.mod": "go",
        "requirements.txt": "python",
        "Makefile": "make",
        "README.md": "documentation",
        ".eslintrc": "linting",
        ".eslintrc.json": "linting",
        ".github/workflows": "ci",
        "Dockerfile": "container",
        "docker-compose.yml": "container",
        "docker-compose.yaml": "container",
    }

    # 经验标记注释模式
    EXPERIENCE_MARKERS = {
        "HACK": "workaround",
        "TODO": "pending",
        "FIXME": "bug",
        "NOTE": "decision",
        "XXX": "warning",
    }

    # 规则提取模式（支持中英文）
    RULE_PATTERNS = [
        (r"(?:rule|规则)[:：]\s*(.+)", "rule"),
        (r"(?:约定|convention)[:：]\s*(.+)", "convention"),
        (r"(?:规范|standard)[:：]\s*(.+)", "standard"),
    ]

    # 支持的文本文件扩展名
    TEXT_EXTENSIONS = {
        ".py", ".js", ".ts", ".java", ".c", ".cpp", ".h", ".hpp",
        ".go", ".rs", ".rb", ".php", ".css", ".scss", ".html",
        ".md", ".txt", ".json", ".yaml", ".yml", ".toml", ".ini",
        ".cfg", ".conf", ".xml", ".sh", ".bash", ".zsh",
    }

    def __init__(self, root_path: Path):
        """初始化分析器"""
        self.root_path = root_path
        self.text_files: List[Path] = []
        self.config_files: List[Path] = []
        self.dir_count = 0
        self.file_count = 0
        self.total_lines = 0

    def scan(self) -> SkillPackage:
        """扫描整个代码库，返回萃取结果"""
        if not self.root_path.exists():
            raise FileNotFoundError(f"E002: 目标代码库路径不存在: {self.root_path}")
        if not self.root_path.is_dir():
            raise NotADirectoryError(f"E003: 目标路径不是目录: {self.root_path}")

        package = SkillPackage(project_name=self.root_path.name)
        self._walk_directory(self.root_path, package)
        self._identify_config_files(package)
        self._extract_rules_and_experiences(package)
        self._extract_workflows(package)
        return package

    def _walk_directory(self, current_dir: Path, package: SkillPackage) -> None:
        """递归遍历目录，收集文本文件信息"""
        try:
            for entry in sorted(current_dir.iterdir()):
                if entry.is_dir():
                    # 跳过隐藏目录和版本控制目录
                    if entry.name.startswith(".") or entry.name in {"node_modules", "vendor", "dist", "build"}:
                        continue
                    self.dir_count += 1
                    package.dir_count += 1
                    self._walk_directory(entry, package)
                elif entry.is_file():
                    self.file_count += 1
                    package.file_count += 1
                    if self._is_text_file(entry):
                        self.text_files.append(entry)
                        try:
                            with open(entry, "r", encoding="utf-8", errors="ignore") as f:
                                lines = f.readlines()
                                self.total_lines += len(lines)
                                package.total_lines += len(lines)
                        except (IOError, OSError):
                            # 文件读取失败，跳过
                            pass
        except PermissionError:
            # 无权限访问目录，跳过
            pass

    def _is_text_file(self, file_path: Path) -> bool:
        """判断是否为可分析的文本文件"""
        return file_path.suffix.lower() in self.TEXT_EXTENSIONS or file_path.name in {
            "Makefile", "Dockerfile", "README", "LICENSE"
        }

    def _identify_config_files(self, package: SkillPackage) -> None:
        """识别配置文件并记录到包信息中"""
        for file_path in self.text_files:
            rel_path = file_path.relative_to(self.root_path)
            name = file_path.name
            parent = str(rel_path.parent)

            # 检查文件名匹配
            if name in self.CONFIG_PATTERNS:
                package.config_files.append(str(rel_path))
                self.config_files.append(file_path)
            # 检查目录匹配
            elif any(part in self.CONFIG_PATTERNS for part in rel_path.parts if part in self.CONFIG_PATTERNS):
                package.config_files.append(str(rel_path))
                self.config_files.append(file_path)

    def _extract_rules_and_experiences(self, package: SkillPackage) -> None:
        """从代码注释中提取规则和经验"""
        for file_path in self.text_files:
            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
            except (IOError, OSError):
                continue

            rel_path = str(file_path.relative_to(self.root_path))
            lines = content.split("\n")

            # 提取规则（支持中英文关键词）
            for i, line in enumerate(lines):
                for pattern, rule_type in self.RULE_PATTERNS:
                    match = re.search(pattern, line)
                    if match:
                        package.rules.append({
                            "type": rule_type,
                            "content": match.group(1).strip(),
                            "source": rel_path,
                            "line": i + 1,
                        })

            # 提取经验注释
            for marker, category in self.EXPERIENCE_MARKERS.items():
                # 支持多种注释格式
                patterns = [
                    rf"//\s*{marker}[:\s]\s*(.+)",  # C/C++/Java/JS/TS 风格
                    rf"#\s*{marker}[:\s]\s*(.+)",   # Python/Ruby/Shell 风格
                    rf"/\*\s*{marker}[:\s]\s*(.+)", # 块注释风格
                    rf"--\s*{marker}[:\s]\s*(.+)",  # SQL/Lua 风格
                ]
                for pattern in patterns:
                    for i, line in enumerate(lines):
                        match = re.search(pattern, line)
                        if match:
                            package.experiences.append({
                                "category": category,
                                "marker": marker,
                                "content": match.group(1).strip(),
                                "source": rel_path,
                                "line": i + 1,
                            })

    def _extract_workflows(self, package: SkillPackage) -> None:
        """提取构建、测试等流程信息"""
        workflow_keywords = ["build", "test", "deploy", "publish", "lint", "compile"]

        for config_path in self.config_files:
            try:
                with open(config_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
            except (IOError, OSError):
                continue

            rel_path = str(config_path.relative_to(self.root_path))
            name = config_path.name

            # 提取 package.json 中的 scripts
            if name == "package.json" and "scripts" in content:
                scripts_match = re.search(r'"scripts"\s*:\s*\{([^}]+)\}', content)
                if scripts_match:
                    scripts_block = scripts_match.group(1)
                    script_pairs = re.findall(r'"([^"]+)"\s*:\s*"([^"]+)"', scripts_block)
                    for script_name, script_cmd in script_pairs:
                        package.workflows.append({
                            "name": script_name,
                            "command": script_cmd,
                            "source": rel_path,
                            "type": "script"
                        })

            # 提取 Makefile 中的目标
            if name == "Makefile":
                targets = re.findall(r"^([a-zA-Z_-]+)\s*:", content, re.MULTILINE)
                for target in targets:
                    if any(kw in target.lower() for kw in workflow_keywords):
                        package.workflows.append({
                            "name": target,
                            "command": f"make {target}",
                            "source": rel_path,
                            "type": "make-target"
                        })

            # 提取 GitHub Actions 工作流
            if "workflows" in rel_path and name.endswith((".yml", ".yaml")):
                workflow_names = re.findall(r"name:\s*(.+)", content)
                for wf_name in workflow_names:
                    package.workflows.append({
                        "name": wf_name.strip(),
                        "command": "CI workflow",
                        "source": rel_path,
                        "type": "ci"
                    })


class SkillGenerator:
    """技能包生成器：将分析结果格式化为文档"""

    @staticmethod
    def generate_markdown(package: SkillPackage) -> str:
        """生成 SKILL.md 格式的技能文档"""
        lines = [
            "# 技能包：代码库萃取报告",
            "",
            f"## 项目概览",
            f"- 项目名称: {package.project_name}",
            f"- 文件总数: {package.file_count}",
            f"- 目录总数: {package.dir_count}",
            f"- 代码总行数: {package.total_lines}",
            "",
            "## 配置文件",
        ]

        if package.config_files:
            for cfg in package.config_files:
                lines.append(f"- {cfg}")
        else:
            lines.append("- 未发现配置文件")

        lines.extend(["", "## 提取的规则", ""])
        if package.rules:
            for rule in package.rules[:20]:  # 限制显示数量
                lines.append(f"- [{rule['type']}] {rule['content']} (来源: {rule['source']}:{rule['line']})")
        else:
            lines.append("- 未提取到显式规则")

        lines.extend(["", "## 工作流", ""])
        if package.workflows:
            for wf in package.workflows[:20]:
                lines.append(f"- {wf['name']}: `{wf['command']}` (来源: {wf['source']})")
        else:
            lines.append("- 未发现可识别的工作流")

        lines.extend(["", "## 经验沉淀", ""])
        if package.experiences:
            for exp in package.experiences[:20]:
                lines.append(f"- [{exp['category']}] {exp['content']} (来源: {exp['source']}:{exp['line']})")
        else:
            lines.append("- 未发现经验注释")

        return "\n".join(lines)


class SelfTest:
    """内置自检模块：使用硬编码样例数据离线验证核心逻辑"""

    @staticmethod
    def run() -> bool:
        """执行自检，返回是否通过"""
        print("开始自检...")

        # 构建内存中的模拟文件系统（使用临时目录）
        import tempfile
        import shutil

        temp_dir = Path(tempfile.mkdtemp(prefix="skill_selftest_"))
        try:
            # 创建模拟项目结构
            project_dir = temp_dir / "demo_project"
            src_dir = project_dir / "src"
            config_dir = project_dir / "config"
            src_dir.mkdir(parents=True)
            config_dir.mkdir()

            # 写入模拟文件
            (project_dir / "package.json").write_text(
                '{"name": "demo", "scripts": {"build": "tsc", "test": "jest"}}',
                encoding="utf-8"
            )
            (project_dir / "README.md").write_text(
                "# Demo Project\n规则: 使用 TypeScript 编写",
                encoding="utf-8"
            )
            (src_dir / "main.ts").write_text(
                "// TODO: 实现主逻辑\n// HACK: 临时绕过 bug\nconst x = 1;",
                encoding="utf-8"
            )
            (config_dir / "config.json").write_text(
                '{"debug": true}',
                encoding="utf-8"
            )

            # 执行分析
            analyzer = CodebaseAnalyzer(project_dir)
            package = analyzer.scan()

            # 宽松断言验证
            assert package.file_count > 0, "E009: 自检失败 - 文件计数为零"
            assert package.dir_count > 0, "E009: 自检失败 - 目录计数为零"
            assert package.total_lines > 0, "E009: 自检失败 - 行数为零"
            assert len(package.config_files) >= 1, "E009: 自检失败 - 未识别配置文件"
            assert package.project_name == "demo_project", "E009: 自检失败 - 项目名错误"

            # 验证规则提取
            assert len(package.rules) >= 1, "E009: 自检失败 - 未提取到规则"
            rule_texts = [r["content"] for r in package.rules]
            assert any("TypeScript" in t for t in rule_texts), "E009: 自检失败 - 规则内容错误"

            # 验证经验提取
            assert len(package.experiences) >= 2, "E009: 自检失败 - 未提取到经验注释"
            exp_markers = [e["marker"] for e in package.experiences]
            assert "TODO" in exp_markers and "HACK" in exp_markers, "E009: 自检失败 - 经验标记缺失"

            # 验证工作流提取
            assert len(package.workflows) >= 2, "E009: 自检失败 - 未提取到工作流"
            wf_names = [w["name"] for w in package.workflows]
            assert "build" in wf_names and "test" in wf_names, "E009: 自检失败 - 工作流名称错误"

            # 验证文档生成
            doc = SkillGenerator.generate_markdown(package)
            assert len(doc) > 100, "E009: 自检失败 - 文档过短"
            assert "项目概览" in doc and "配置文件" in doc, "E009: 自检失败 - 文档结构错误"

            print("自检通过 ✓")
            return True

        except AssertionError as e:
            print(f"自检失败 ✗: {e}")
            return False
        except Exception as e:
            print(f"自检异常 ✗: {e}")
            return False
        finally:
            # 清理临时目录
            shutil.rmtree(temp_dir, ignore_errors=True)


def main() -> int:
    """主入口函数"""
    parser = argparse.ArgumentParser(
        description="技能工厂：代码库萃取与规则蒸馏工具",
        epilog="示例: python main.py /path/to/project -o output.md"
    )
    parser.add_argument(
        "path",
        nargs="?",
        help="目标代码库路径",
        default=None
    )
    parser.add_argument(
        "-o", "--output",
        help="输出文件路径（默认输出到 stdout）",
        default=None
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检并退出"
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        success = SelfTest.run()
        return 0 if success else 1

    # 参数校验
    if args.path is None:
        print(f"E001: {ERROR_CODES['E001']}", file=sys.stderr)
        parser.print_help()
        return 1

    try:
        # 执行分析
        root_path = Path(args.path).resolve()
        analyzer = CodebaseAnalyzer(root_path)
        package = analyzer.scan()

        # 生成文档
        doc = SkillGenerator.generate_markdown(package)

        # 输出结果
        if args.output:
            output_path = Path(args.output)
            try:
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_text(doc, encoding="utf-8")
                print(f"技能包已生成: {output_path}")
            except (IOError, OSError) as e:
                print(f"E008: {ERROR_CODES['E008']}: {e}", file=sys.stderr)
                return 8
        else:
            print(doc)

        # 输出统计信息
        print(f"\n分析完成: {package.file_count} 个文件, {package.dir_count} 个目录, "
              f"{package.total_lines} 行代码, 提取 {len(package.rules)} 条规则, "
              f"{len(package.workflows)} 个工作流, {len(package.experiences)} 条经验")
        return 0

    except FileNotFoundError as e:
        print(f"{e}", file=sys.stderr)
        return 2
    except NotADirectoryError as e:
        print(f"{e}", file=sys.stderr)
        return 3
    except Exception as e:
        print(f"E010: {ERROR_CODES['E010']}: {e}", file=sys.stderr)
        return 10


if __name__ == "__main__":
    sys.exit(main())
