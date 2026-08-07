#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py

技能工厂：代码库萃取与规则蒸馏 —— 独立实现脚本（clean-room 重写）

本脚本依据功能规格独立实现，仅使用 Python 标准库。
提供命令行接口与内置离线自检（--selftest）。

错误码说明：
    E001: 参数解析错误
    E002: 输入路径不存在
    E003: 输入路径不是目录
    E004: 目录不可读
    E005: 文件读取失败
    E006: 文件编码不支持
    E007: 输出目录创建失败
    E008: 输出文件写入失败
    E009: 内部逻辑错误（未知分支）
    E010: 自检失败
"""

import argparse
import os
import re
import sys
import tempfile
from collections import defaultdict
from pathlib import Path

# ---------------------------------------------------------------------------
# 常量定义
# ---------------------------------------------------------------------------

# 文本文件扩展名白名单（用于静态分析）
TEXT_EXTENSIONS = {
    ".py", ".js", ".ts", ".java", ".c", ".cpp", ".h", ".hpp",
    ".go", ".rs", ".rb", ".php", ".swift", ".kt", ".scala",
    ".json", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".conf",
    ".md", ".txt", ".rst", ".xml", ".html", ".css", ".scss",
    ".sh", ".bat", ".ps1", ".sql", ".graphql", ".proto",
}

# 配置文件名（用于识别项目类型）
CONFIG_FILES = {
    "package.json": "node",
    "pom.xml": "java",
    "Cargo.toml": "rust",
    "go.mod": "go",
    "requirements.txt": "python",
    "setup.py": "python",
    "pyproject.toml": "python",
    "Gemfile": "ruby",
    "build.gradle": "gradle",
    "Makefile": "make",
}

# 注释标记（按语言分组）
COMMENT_MARKERS = {
    "python": ("#",),
    "javascript": ("//", "/*", "*"),
    "typescript": ("//", "/*", "*"),
    "java": ("//", "/*", "*"),
    "c": ("//", "/*", "*"),
    "cpp": ("//", "/*", "*"),
    "go": ("//", "/*", "*"),
    "rust": ("//", "/*", "*"),
    "ruby": ("#",),
    "php": ("//", "#", "/*", "*"),
    "shell": ("#",),
    "sql": ("--", "/*", "*"),
}

# 经验标记（TODO/FIXME/HACK/NOTE/XXX）
EXPERIENCE_MARKERS = ["TODO", "FIXME", "HACK", "NOTE", "XXX"]

# 工作流相关关键字（用于识别 CI/CD 流程）
WORKFLOW_KEYWORDS = ["build", "test", "deploy", "publish", "release", "lint", "install"]

# ---------------------------------------------------------------------------
# 核心数据结构
# ---------------------------------------------------------------------------


class AnalysisResult:
    """分析结果容器"""

    def __init__(self):
        self.project_type = "unknown"
        self.config_files = []
        self.modules = []          # 模块/目录列表
        self.file_count = 0
        self.rules = []            # 规则清单
        self.workflows = []        # 工作流
        self.experiences = []      # 经验卡片
        self.dependencies = defaultdict(list)  # 模块依赖关系

    def to_dict(self):
        """转换为字典（用于输出）"""
        return {
            "project_type": self.project_type,
            "config_files": self.config_files,
            "modules": self.modules,
            "file_count": self.file_count,
            "rules": self.rules,
            "workflows": self.workflows,
            "experiences": self.experiences,
            "dependencies": dict(self.dependencies),
        }


# ---------------------------------------------------------------------------
# 核心分析逻辑
# ---------------------------------------------------------------------------


def analyze_codebase(root_path):
    """
    分析代码库，提取结构、规则、工作流与经验。

    参数:
        root_path: 代码库根目录路径（Path 对象）

    返回:
        AnalysisResult 对象

    异常:
        可能抛出 OSError（E002/E003/E004/E005）
    """
    if not root_path.exists():
        raise FileNotFoundError(f"E002: 路径不存在: {root_path}")
    if not root_path.is_dir():
        raise NotADirectoryError(f"E003: 不是目录: {root_path}")
    if not os.access(root_path, os.R_OK):
        raise PermissionError(f"E004: 目录不可读: {root_path}")

    result = AnalysisResult()

    # 1. 扫描目录树，识别模块与配置文件
    _scan_directory(root_path, result)

    # 2. 识别项目类型（基于配置文件）
    result.project_type = _detect_project_type(result.config_files)

    # 3. 提取规则与约定
    result.rules = _extract_rules(root_path, result)

    # 4. 还原工作流
    result.workflows = _extract_workflows(root_path, result)

    # 5. 沉淀经验教训
    result.experiences = _extract_experiences(root_path, result)

    # 6. 构建模块依赖图
    result.dependencies = _build_dependency_graph(root_path, result.modules)

    return result


def _scan_directory(root_path, result):
    """
    递归扫描目录，收集模块列表、配置文件、文件计数。

    参数:
        root_path: 根目录 Path
        result: AnalysisResult 实例（原地修改）
    """
    for root, dirs, files in os.walk(root_path):
        # 跳过隐藏目录（如 .git, .svn, node_modules）
        dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ("node_modules", "venv", "__pycache__")]

        current_dir = Path(root)
        rel_path = current_dir.relative_to(root_path)

        # 记录模块（相对路径）
        if rel_path != Path("."):
            result.modules.append(str(rel_path))

        # 处理文件
        for file in files:
            if file.startswith("."):
                continue
            file_path = current_dir / file
            rel_file = file_path.relative_to(root_path)

            # 配置文件
            if file in CONFIG_FILES:
                result.config_files.append(str(rel_file))

            # 文本文件计数
            if file_path.suffix.lower() in TEXT_EXTENSIONS or file in ("Makefile", "Dockerfile"):
                result.file_count += 1


def _detect_project_type(config_files):
    """
    根据配置文件识别项目类型。

    参数:
        config_files: 配置文件相对路径列表

    返回:
        项目类型字符串
    """
    for config in config_files:
        filename = Path(config).name
        if filename in CONFIG_FILES:
            return CONFIG_FILES[filename]
    return "unknown"


def _extract_rules(root_path, result):
    """
    从配置文件和文档中提取规则与约定。

    参数:
        root_path: 根目录 Path
        result: AnalysisResult 实例

    返回:
        规则列表（字典格式）
    """
    rules = []
    rule_keywords = ["must", "should", "always", "never", "require", "禁止", "必须", "务必"]

    # 扫描 README 或文档中的规则描述
    for doc_name in ["README.md", "README.txt", "CONTRIBUTING.md", "docs/rules.md"]:
        doc_path = root_path / doc_name
        if not doc_path.exists():
            continue
        try:
            content = doc_path.read_text(encoding="utf-8", errors="ignore")
            for line in content.splitlines():
                line = line.strip()
                if not line:
                    continue
                # 检查是否包含规则关键词
                lower_line = line.lower()
                if any(kw in lower_line for kw in rule_keywords):
                    rules.append({
                        "source": doc_name,
                        "content": line[:200],  # 截断超长行
                        "priority": "high" if any(kw in lower_line for kw in ["must", "禁止", "必须"]) else "medium",
                        "scope": "project",
                    })
        except (OSError, UnicodeError):
            continue  # 跳过无法读取的文件

    return rules


def _extract_workflows(root_path, result):
    """
    从 CI 配置和脚本中还原工作流。

    参数:
        root_path: 根目录 Path
        result: AnalysisResult 实例

    返回:
        工作流列表（字典格式）
    """
    workflows = []

    # 检查 GitHub Actions
    gh_actions_dir = root_path / ".github" / "workflows"
    if gh_actions_dir.exists():
        for yml_file in gh_actions_dir.glob("*.yml"):
            try:
                content = yml_file.read_text(encoding="utf-8", errors="ignore")
                steps = []
                for line in content.splitlines():
                    line = line.strip()
                    # 提取步骤名称
                    if line.startswith("name:"):
                        steps.append(line.split(":", 1)[1].strip())
                    # 提取运行命令
                    elif line.startswith("run:"):
                        cmd = line.split(":", 1)[1].strip()
                        if cmd:
                            steps.append(f"run: {cmd[:100]}")
                if steps:
                    workflows.append({
                        "name": yml_file.stem,
                        "source": str(yml_file.relative_to(root_path)),
                        "steps": steps,
                        "type": "ci",
                    })
            except (OSError, UnicodeError):
                continue

    # 检查 package.json scripts
    pkg_json = root_path / "package.json"
    if pkg_json.exists():
        try:
            import json
            data = json.loads(pkg_json.read_text(encoding="utf-8", errors="ignore"))
            scripts = data.get("scripts", {})
            if scripts:
                workflow_steps = []
                for name, cmd in scripts.items():
                    if any(kw in name.lower() for kw in WORKFLOW_KEYWORDS):
                        workflow_steps.append(f"{name}: {cmd[:100]}")
                if workflow_steps:
                    workflows.append({
                        "name": "package-scripts",
                        "source": "package.json",
                        "steps": workflow_steps,
                        "type": "build",
                    })
        except (Exception, ValueError):
            pass  # JSON 解析失败则跳过

    return workflows


def _extract_experiences(root_path, result):
    """
    从代码注释中提取经验教训。

    参数:
        root_path: 根目录 Path
        result: AnalysisResult 实例

    返回:
        经验卡片列表
    """
    experiences = []

    # 遍历所有文本文件
    for root, dirs, files in os.walk(root_path):
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        for file in files:
            file_path = Path(root) / file
            if file_path.suffix.lower() not in TEXT_EXTENSIONS:
                continue

            try:
                content = file_path.read_text(encoding="utf-8", errors="ignore")
            except (OSError, UnicodeError):
                continue

            # 按行检查经验标记
            for idx, line in enumerate(content.splitlines(), 1):
                for marker in EXPERIENCE_MARKERS:
                    if marker in line.upper():
                        # 提取注释内容
                        comment_start = max(line.find("//"), line.find("#"), line.find("--"))
                        if comment_start >= 0:
                            comment = line[comment_start:].strip()
                        else:
                            comment = line.strip()

                        experiences.append({
                            "marker": marker,
                            "file": str(file_path.relative_to(root_path)),
                            "line": idx,
                            "content": comment[:200],
                        })
                        break  # 每行只记录一个标记

    return experiences


def _build_dependency_graph(root_path, modules):
    """
    构建模块依赖图（基于 import/require 语句的简单分析）。

    参数:
        root_path: 根目录 Path
        modules: 模块列表

    返回:
        依赖字典 {模块: [依赖模块列表]}
    """
    dependencies = defaultdict(list)

    # 简化实现：扫描 import 语句，尝试匹配本地模块
    import_patterns = [
        re.compile(r"^\s*(?:from|import)\s+([\w.]+)", re.MULTILINE),  # Python
        re.compile(r"^\s*(?:require|import)\s*\(?\s*['\"]([^'\"]+)['\"]", re.MULTILINE),  # JS/TS
        re.compile(r"^\s*#include\s*[<\"]([^>\"]+)[>\"]", re.MULTILINE),  # C/C++
    ]

    for root, dirs, files in os.walk(root_path):
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        for file in files:
            file_path = Path(root) / file
            if file_path.suffix.lower() not in TEXT_EXTENSIONS:
                continue

            rel_file = file_path.relative_to(root_path)
            module_name = str(rel_file.parent) if rel_file.parent != Path(".") else "root"

            try:
                content = file_path.read_text(encoding="utf-8", errors="ignore")
            except (OSError, UnicodeError):
                continue

            for pattern in import_patterns:
                for match in pattern.finditer(content):
                    imported = match.group(1).split(".")[0]
                    # 检查是否为本地模块
                    for mod in modules:
                        if mod.endswith(imported) or imported in mod:
                            dependencies[module_name].append(mod)
                            break

    return dependencies


# ---------------------------------------------------------------------------
# 输出与格式化
# ---------------------------------------------------------------------------


def format_report(result, format_type="text"):
    """
    格式化分析报告。

    参数:
        result: AnalysisResult 实例
        format_type: 输出格式（text/json/markdown）

    返回:
        格式化字符串
    """
    if format_type == "json":
        import json
        return json.dumps(result.to_dict(), indent=2, ensure_ascii=False)

    if format_type == "markdown":
        lines = ["# 代码库分析报告", ""]
        lines.append(f"## 项目类型: {result.project_type}")
        lines.append("")
        lines.append(f"## 文件数量: {result.file_count}")
        lines.append("")

        # 配置文件
        lines.append("## 配置文件")
        for cfg in result.config_files:
            lines.append(f"- {cfg}")
        lines.append("")

        # 模块
        lines.append("## 模块列表")
        for mod in result.modules[:20]:  # 限制输出
            lines.append(f"- {mod}")
        if len(result.modules) > 20:
            lines.append(f"- ... 共 {len(result.modules)} 个模块")
        lines.append("")

        # 规则
        lines.append("## 提取规则")
        for rule in result.rules[:20]:
            lines.append(f"- [{rule['priority']}] {rule['content']}")
        lines.append("")

        # 工作流
        lines.append("## 工作流")
        for wf in result.workflows:
            lines.append(f"### {wf['name']} ({wf['type']})")
            for step in wf["steps"][:10]:
                lines.append(f"- {step}")
        lines.append("")

        # 经验
        lines.append("## 经验教训")
        for exp in result.experiences[:20]:
            lines.append(f"- [{exp['marker']}] {exp['file']}:{exp['line']} - {exp['content']}")
        lines.append("")

        return "\n".join(lines)

    # 默认文本格式
    lines = ["=" * 60, "代码库分析报告", "=" * 60]
    lines.append(f"项目类型: {result.project_type}")
    lines.append(f"文件数量: {result.file_count}")
    lines.append("")
    lines.append("配置文件:")
    for cfg in result.config_files:
        lines.append(f"  - {cfg}")
    lines.append("")
    lines.append("模块列表 (前 20 个):")
    for mod in result.modules[:20]:
        lines.append(f"  - {mod}")
    if len(result.modules) > 20:
        lines.append(f"  ... 共 {len(result.modules)} 个模块")
    lines.append("")
    lines.append("提取规则 (前 20 条):")
    for rule in result.rules[:20]:
        lines.append(f"  - [{rule['priority']}] {rule['content']}")
    lines.append("")
    lines.append("工作流:")
    for wf in result.workflows:
        lines.append(f"  - {wf['name']} ({wf['type']}):")
        for step in wf["steps"][:5]:
            lines.append(f"      * {step}")
    lines.append("")
    lines.append("经验教训 (前 20 条):")
    for exp in result.experiences[:20]:
        lines.append(f"  - [{exp['marker']}] {exp['file']}:{exp['line']} - {exp['content']}")
    lines.append("=" * 60)

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 自检逻辑（--selftest）
# ---------------------------------------------------------------------------


def run_selftest():
    """
    内置离线自检。

    使用硬编码样例数据在临时目录中构建一个模拟代码库，
    验证核心分析逻辑的正确性。不依赖外部文件、不访问网络。

    返回:
        True 表示自检通过，False 表示失败

    异常:
        自检失败时抛出 AssertionError
    """
    print("运行内置自检...")

    try:
        # 创建临时目录作为模拟代码库
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)

            # --- 创建模拟项目结构 ---
            # 配置文件
            (tmp_path / "package.json").write_text(
                '{"name": "demo", "scripts": {"build": "tsc", "test": "jest", "deploy": "aws deploy"}}',
                encoding="utf-8"
            )
            (tmp_path / "README.md").write_text(
                "# Demo Project\n必须使用 TypeScript 编写所有代码。\nNever use `any` type.\n",
                encoding="utf-8"
            )

            # 源码目录
            src_dir = tmp_path / "src"
            src_dir.mkdir()
            (src_dir / "index.ts").write_text(
                "// TODO: 重构此模块\nimport { helper } from './helper';\nconst x: number = 1;\n",
                encoding="utf-8"
            )
            (src_dir / "helper.ts").write_text(
                "export function helper() { return 'help'; }\n// FIXME: 这里有个 bug\n",
                encoding="utf-8"
            )

            # 嵌套目录
            utils_dir = src_dir / "utils"
            utils_dir.mkdir()
            (utils_dir / "math.ts").write_text(
                "export const add = (a: number, b: number) => a + b;\n",
                encoding="utf-8"
            )

            # CI 工作流
            gh_dir = tmp_path / ".github" / "workflows"
            gh_dir.mkdir(parents=True)
            (gh_dir / "ci.yml").write_text(
                "name: CI\non: [push]\njobs:\n  build:\n    steps:\n      - name: Checkout\n        run: git checkout\n      - name: Install\n        run: npm install\n      - name: Test\n        run: npm test\n",
                encoding="utf-8"
            )

            # --- 执行分析 ---
            result = analyze_codebase(tmp_path)

            # --- 断言（宽松阈值，确保稳健） ---
            # 1. 项目类型应为 node（package.json 存在）
            assert result.project_type == "node", f"E010: 项目类型识别失败: {result.project_type}"

            # 2. 配置文件应包含 package.json
            assert any("package.json" in cfg for cfg in result.config_files), "E010: 未识别 package.json"

            # 3. 文件数量应大于 0（宽松判断）
            assert result.file_count > 0, "E010: 文件计数异常"

            # 4. 模块数量应不少于 2（src 和 src/utils）
            assert len(result.modules) >= 2, f"E010: 模块数量异常: {len(result.modules)}"

            # 5. 规则提取：README 中应至少提取 1 条规则
            assert len(result.rules) >= 1, "E010: 规则提取失败"

            # 6. 工作流提取：应有至少 1 个工作流（package.json scripts 或 CI）
            assert len(result.workflows) >= 1, "E010: 工作流提取失败"

            # 7. 经验提取：应有至少 2 条经验（TODO 和 FIXME）
            assert len(result.experiences) >= 2, f"E010: 经验提取失败: {len(result.experiences)}"

            # 8. 经验内容应包含 TODO 或 FIXME 标记
            markers = [exp["marker"] for exp in result.experiences]
            assert "TODO" in markers and "FIXME" in markers, "E010: 经验标记内容异常"

            # 9. 依赖图不应为空（index.ts 引用了 helper）
            assert len(result.dependencies) > 0, "E010: 依赖图为空"

            # 10. 模块列表中应包含 src 和 src/utils
            module_strs = " ".join(result.modules)
            assert "src" in module_strs, "E010: 模块列表缺少 src"

            print("自检通过: 所有断言成功")

            # 打印简要结果（便于人工验证）
            print(f"  项目类型: {result.project_type}")
            print(f"  文件数量: {result.file_count}")
            print(f"  模块数量: {len(result.modules)}")
            print(f"  规则数量: {len(result.rules)}")
            print(f"  工作流数量: {len(result.workflows)}")
            print(f"  经验数量: {len(result.experiences)}")

            return True

    except AssertionError as e:
        print(f"自检失败: {e}")
        return False
    except Exception as e:
        print(f"自检异常: {e}")
        return False


# ---------------------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------------------


def main():
    """命令行主入口"""
    parser = argparse.ArgumentParser(
        description="技能工厂：代码库萃取与规则蒸馏",
        epilog="示例: python main.py /path/to/repo --format markdown"
    )
    parser.add_argument(
        "path",
        nargs="?",
        default=".",
        help="代码库根目录路径（默认当前目录）"
    )
    parser.add_argument(
        "--format",
        choices=["text", "json", "markdown"],
        default="text",
        help="输出格式（默认 text）"
    )
    parser.add_argument(
        "--output",
        help="输出文件路径（默认输出到 stdout）"
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检（不分析代码库）"
    )

    try:
        args = parser.parse_args()
    except SystemExit as e:
        # argparse 内部错误
        print(f"E001: 参数解析错误: {e}", file=sys.stderr)
        return 1

    # 自检模式
    if args.selftest:
        success = run_selftest()
        return 0 if success else 10

    # 正常分析模式
    try:
        root_path = Path(args.path).resolve()
        result = analyze_codebase(root_path)

        report = format_report(result, args.format)

        # 输出
        if args.output:
            try:
                out_path = Path(args.output)
                out_path.parent.mkdir(parents=True, exist_ok=True)
                out_path.write_text(report, encoding="utf-8")
                print(f"报告已写入: {out_path}")
            except OSError as e:
                print(f"E008: 输出文件写入失败: {e}", file=sys.stderr)
                return 8
        else:
            print(report)

        return 0

    except FileNotFoundError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 2
    except NotADirectoryError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 3
    except PermissionError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 4
    except OSError as e:
        print(f"E005: 文件读取失败: {e}", file=sys.stderr)
        return 5
    except Exception as e:
        print(f"E009: 内部错误: {e}", file=sys.stderr)
        return 9


if __name__ == "__main__":
    sys.exit(main())
