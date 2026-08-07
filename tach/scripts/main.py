#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tach — 依赖可视化与架构边界守护（独立实现）

本脚本依据功能规格独立编写，不复制任何既有实现。
支持：
  - 解析 Python 文件中的 import 语句，构建模块依赖图
  - 依据模块归属规则与允许方向，检查架构边界违规
  - 输出文本树、表格、DOT 格式
  - 定向增量检查
  - 内置离线自检（--selftest）

用法示例：
  python main.py --root ./src --config tach.toml
  python main.py --root ./src --config tach.toml --target ./src/app
  python main.py --root ./src --config tach.toml --format dot
  python main.py --selftest
"""

import argparse
import ast
import json
import os
import re
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

# ---------------------------------------------------------------------------
# 错误码定义
# ---------------------------------------------------------------------------
ERR_OK = 0
ERR_CONFIG_NOT_FOUND = "E001"      # 配置文件不存在
ERR_CONFIG_INVALID = "E002"        # 配置文件格式错误
ERR_ROOT_NOT_FOUND = "E003"        # 根目录不存在
ERR_TARGET_NOT_FOUND = "E004"      # 目标文件/目录不存在
ERR_PARSE_FAILED = "E005"          # Python 文件解析失败
ERR_NO_RULES = "E006"              # 未定义任何架构规则
ERR_INTERNAL = "E007"              # 内部逻辑错误
ERR_ARG_INVALID = "E008"           # 命令行参数无效
ERR_OUTPUT_FAILED = "E009"         # 输出写入失败
ERR_SELFTEST_FAILED = "E010"       # 自检失败


# ---------------------------------------------------------------------------
# 数据结构
# ---------------------------------------------------------------------------
@dataclass
class ImportRecord:
    """一条导入记录"""
    module: str          # 模块名（相对或绝对）
    lineno: int          # 行号
    alias: Optional[str] = None  # 别名


@dataclass
class ModuleNode:
    """模块节点"""
    name: str            # 模块名（相对根目录的点路径）
    path: Path           # 文件路径
    imports: List[ImportRecord] = field(default_factory=list)


@dataclass
class BoundaryRule:
    """架构边界规则"""
    source: str          # 源模块（支持前缀匹配）
    allowed: List[str]   # 允许依赖的目标模块（支持前缀匹配）


@dataclass
class Violation:
    """违规记录"""
    source: str
    target: str
    lineno: int
    reason: str


@dataclass
class CheckResult:
    """检查结果"""
    violations: List[Violation] = field(default_factory=list)
    module_count: int = 0
    import_count: int = 0


# ---------------------------------------------------------------------------
# 配置解析
# ---------------------------------------------------------------------------
def load_config(config_path: Path) -> Dict:
    """
    加载配置文件（支持 JSON 或 TOML 简化格式）。
    返回结构：
    {
      "modules": {"app": ["app*"], "core": ["core*"]},
      "rules": [
        {"source": "app", "allowed": ["core"]},
        {"source": "core", "allowed": []}
      ]
    }
    """
    if not config_path.exists():
        raise FileNotFoundError(f"{ERR_CONFIG_NOT_FOUND}: 配置文件不存在: {config_path}")

    try:
        text = config_path.read_text(encoding="utf-8")
        if config_path.suffix == ".json":
            return json.loads(text)
        # 简化 TOML 解析（仅支持小节与 key = value）
        return _parse_simple_toml(text)
    except Exception as exc:
        raise ValueError(f"{ERR_CONFIG_INVALID}: 配置文件格式错误: {exc}") from exc


def _parse_simple_toml(text: str) -> Dict:
    """极简 TOML 解析器（仅用于本工具配置）"""
    result: Dict = {}
    current_section = None

    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("[") and line.endswith("]"):
            current_section = line[1:-1].strip()
            if current_section not in result:
                result[current_section] = []
            continue
        if "=" in line:
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if current_section is None:
                result[key] = value
            else:
                result[current_section].append((key, value))

    # 转换为期望结构
    modules: Dict[str, List[str]] = {}
    rules: List[Dict] = []

    if "modules" in result:
        for item in result["modules"]:
            if isinstance(item, tuple):
                modules[item[0]] = [item[1]]
            else:
                modules[item] = []

    if "rules" in result:
        for item in result["rules"]:
            if isinstance(item, tuple):
                rules.append({"source": item[0], "allowed": [item[1]]})

    return {"modules": modules, "rules": rules}


# ---------------------------------------------------------------------------
# 依赖解析
# ---------------------------------------------------------------------------
def parse_python_file(file_path: Path, root: Path) -> Optional[ModuleNode]:
    """
    解析单个 Python 文件，提取导入关系。
    返回 ModuleNode，解析失败返回 None。
    """
    try:
        tree = ast.parse(file_path.read_text(encoding="utf-8"), filename=str(file_path))
    except (SyntaxError, UnicodeDecodeError):
        return None

    # 计算模块名（相对根目录的点路径）
    try:
        rel_path = file_path.resolve().relative_to(root.resolve())
    except ValueError:
        rel_path = Path(file_path.name)

    parts = list(rel_path.parts)
    if parts[-1] == "__init__.py":
        parts = parts[:-1]
    elif parts[-1].endswith(".py"):
        parts[-1] = parts[-1][:-3]
    else:
        return None

    module_name = ".".join(parts) if parts else "__root__"

    node = ModuleNode(name=module_name, path=file_path)

    for item in ast.walk(tree):
        if isinstance(item, ast.Import):
            for alias in item.names:
                node.imports.append(
                    ImportRecord(module=alias.name, lineno=item.lineno, alias=alias.asname)
                )
        elif isinstance(item, ast.ImportFrom):
            module = item.module or ""
            if item.level > 0:
                # 相对导入：转换为绝对（这里简化处理）
                module = "." * item.level + module
            for alias in item.names:
                target = f"{module}.{alias.name}" if module else alias.name
                node.imports.append(
                    ImportRecord(module=target, lineno=item.lineno, alias=alias.asname)
                )

    return node


def scan_directory(root: Path) -> List[ModuleNode]:
    """递归扫描目录下所有 .py 文件"""
    nodes: List[ModuleNode] = []
    if not root.exists():
        raise FileNotFoundError(f"{ERR_ROOT_NOT_FOUND}: 根目录不存在: {root}")

    for py_file in sorted(root.rglob("*.py")):
        # 跳过常见虚拟环境目录
        if any(part in {"venv", ".venv", "__pycache__", ".git"} for part in py_file.parts):
            continue
        node = parse_python_file(py_file, root)
        if node:
            nodes.append(node)
    return nodes


# ---------------------------------------------------------------------------
# 架构规则匹配
# ---------------------------------------------------------------------------
def match_prefix(module: str, pattern: str) -> bool:
    """前缀匹配（支持 * 通配符）"""
    if pattern.endswith("*"):
        return module.startswith(pattern[:-1])
    return module == pattern or module.startswith(pattern + ".")


def find_rule_for_module(module: str, rules: List[BoundaryRule]) -> Optional[BoundaryRule]:
    """找到模块所属的规则（取最长匹配）"""
    best: Optional[BoundaryRule] = None
    best_len = -1
    for rule in rules:
        if match_prefix(module, rule.source):
            # 计算匹配长度（用于最长匹配）
            pattern = rule.source[:-1] if rule.source.endswith("*") else rule.source
            if len(pattern) > best_len:
                best = rule
                best_len = len(pattern)
    return best


def check_architecture(nodes: List[ModuleNode], rules: List[BoundaryRule]) -> CheckResult:
    """执行架构边界校验"""
    result = CheckResult()
    result.module_count = len(nodes)

    # 构建模块名 -> 节点映射
    module_map = {node.name: node for node in nodes}

    # 收集所有规则中提到的模块前缀，用于判断目标模块是否属于项目
    project_modules = set()
    for rule in rules:
        source_pattern = rule.source[:-1] if rule.source.endswith("*") else rule.source
        project_modules.add(source_pattern)
        for allowed_pattern in rule.allowed:
            pattern = allowed_pattern[:-1] if allowed_pattern.endswith("*") else allowed_pattern
            project_modules.add(pattern)

    for node in nodes:
        rule = find_rule_for_module(node.name, rules)
        if rule is None:
            continue  # 未定义规则的模块不检查

        for imp in node.imports:
            result.import_count += 1
            target = imp.module.lstrip(".")

            # 判断目标模块是否属于项目内模块
            is_project_module = False
            # 检查目标模块是否在已知模块映射中
            if target in module_map or any(name.startswith(target + ".") for name in module_map):
                is_project_module = True
            # 检查目标模块是否匹配项目模块前缀
            else:
                for proj_prefix in project_modules:
                    if match_prefix(target, proj_prefix):
                        is_project_module = True
                        break
            
            # 如果不是项目内模块（标准库、第三方库等），跳过
            if not is_project_module:
                continue

            # 检查是否允许
            allowed = False
            for pattern in rule.allowed:
                if match_prefix(target, pattern):
                    allowed = True
                    break

            if not allowed:
                result.violations.append(
                    Violation(
                        source=node.name,
                        target=target,
                        lineno=imp.lineno,
                        reason=f"模块 '{node.name}' 不允许依赖 '{target}'（规则: {rule.source}）",
                    )
                )

    return result


# ---------------------------------------------------------------------------
# 输出格式化
# ---------------------------------------------------------------------------
def format_text_tree(nodes: List[ModuleNode], max_depth: int = 3) -> str:
    """输出文本树"""
    lines = ["依赖树:"]
    # 构建层级结构
    tree: Dict[str, Set[str]] = defaultdict(set)
    for node in nodes:
        parts = node.name.split(".")
        for i in range(len(parts) - 1):
            parent = ".".join(parts[: i + 1])
            child = ".".join(parts[: i + 2])
            tree[parent].add(child)

    def render(prefix: str, name: str, depth: int):
        if depth > max_depth:
            return
        lines.append(f"{prefix}{name}")
        children = sorted(tree.get(name, set()))
        for i, child in enumerate(children):
            is_last = i == len(children) - 1
            child_prefix = prefix + ("    " if is_last else "│   ")
            lines.append(f"{child_prefix}├── {child}")

    # 根节点
    roots = sorted({node.name.split(".")[0] for node in nodes})
    for root in roots:
        render("", root, 0)

    return "\n".join(lines)


def format_table(nodes: List[ModuleNode]) -> str:
    """输出表格"""
    lines = ["| 模块 | 依赖数 |"]
    lines.append("|------|--------|")
    for node in sorted(nodes, key=lambda n: n.name):
        lines.append(f"| {node.name} | {len(node.imports)} |")
    return "\n".join(lines)


def format_dot(nodes: List[ModuleNode]) -> str:
    """输出 DOT 格式"""
    lines = ["digraph dependencies {"]
    for node in nodes:
        lines.append(f'  "{node.name}";')
        for imp in node.imports:
            target = imp.module.lstrip(".")
            if target:
                lines.append(f'  "{node.name}" -> "{target}";')
    lines.append("}")
    return "\n".join(lines)


def format_violations(result: CheckResult) -> str:
    """格式化违规报告"""
    if not result.violations:
        return "✅ 未发现架构边界违规。"

    lines = [f"❌ 发现 {len(result.violations)} 处架构边界违规:"]
    lines.append("")
    lines.append("| 源模块 | 目标模块 | 行号 | 原因 |")
    lines.append("|--------|----------|------|------|")
    for v in result.violations:
        lines.append(f"| {v.source} | {v.target} | {v.lineno} | {v.reason} |")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 增量检查
# ---------------------------------------------------------------------------
def check_target(target: Path, root: Path, rules: List[BoundaryRule]) -> CheckResult:
    """对指定文件/目录定向检查"""
    if not target.exists():
        raise FileNotFoundError(f"{ERR_TARGET_NOT_FOUND}: 目标不存在: {target}")

    if target.is_file():
        nodes = [node for node in [parse_python_file(target, root)] if node]
    else:
        # 目录：仅扫描该目录（不含子目录？这里递归）
        nodes = []
        for py_file in target.rglob("*.py"):
            node = parse_python_file(py_file, root)
            if node:
                nodes.append(node)

    return check_architecture(nodes, rules)


# ---------------------------------------------------------------------------
# 自检（离线硬编码样例）
# ---------------------------------------------------------------------------
def run_selftest() -> int:
    """
    内置离线自检：使用硬编码样例数据验证核心逻辑。
    不读外部文件、不依赖当前目录、不访问网络。
    """
    print("=== tach 自检开始 ===")

    # ---- 样例模块 ----
    sample_nodes = [
        ModuleNode(name="app.main", path=Path("app/main.py"),
                   imports=[ImportRecord(module="app.service", lineno=1),
                            ImportRecord(module="core.utils", lineno=2)]),
        ModuleNode(name="app.service", path=Path("app/service.py"),
                   imports=[ImportRecord(module="core.base", lineno=1)]),
        ModuleNode(name="core.base", path=Path("core/base.py"),
                   imports=[ImportRecord(module="core.utils", lineno=1)]),
        ModuleNode(name="core.utils", path=Path("core/utils.py"),
                   imports=[ImportRecord(module="os", lineno=1)]),
    ]

    # ---- 样例规则 ----
    sample_rules = [
        BoundaryRule(source="app", allowed=["app", "core"]),
        BoundaryRule(source="core", allowed=["core"]),
    ]

    # ---- 测试1: 架构检查（应无违规） ----
    result = check_architecture(sample_nodes, sample_rules)
    assert result.violations == [], f"测试1失败: 应无违规，实际 {len(result.violations)}"
    assert result.module_count == 4, f"测试1失败: 模块数应为4，实际 {result.module_count}"
    print("✅ 测试1（正常架构检查）通过")

    # ---- 测试2: 违规检测 ----
    bad_nodes = [
        ModuleNode(name="core.base", path=Path("core/base.py"),
                   imports=[ImportRecord(module="app.service", lineno=5)]),
    ]
    result2 = check_architecture(bad_nodes, sample_rules)
    assert len(result2.violations) == 1, f"测试2失败: 应1个违规，实际 {len(result2.violations)}"
    v = result2.violations[0]
    assert v.source == "core.base", f"测试2失败: 源模块错误 {v.source}"
    assert v.target == "app.service", f"测试2失败: 目标模块错误 {v.target}"
    assert v.lineno == 5, f"测试2失败: 行号错误 {v.lineno}"
    print("✅ 测试2（违规检测）通过")

    # ---- 测试3: 规则匹配 ----
    assert match_prefix("app.main", "app") is True, "测试3失败: app.main 应匹配 app"
    assert match_prefix("app.main", "app.*") is True, "测试3失败: app.main 应匹配 app.*"
    assert match_prefix("core.utils", "app") is False, "测试3失败: core.utils 不应匹配 app"
    assert match_prefix("appx", "app") is True, "测试3失败: appx 应匹配 app（前缀）"
    print("✅ 测试3（规则匹配）通过")

    # ---- 测试4: 输出格式 ----
    text_tree = format_text_tree(sample_nodes, max_depth=2)
    assert "app" in text_tree and "core" in text_tree, "测试4失败: 文本树缺少根节点"
    table = format_table(sample_nodes)
    assert "| 模块 |" in table, "测试4失败: 表格缺少表头"
    dot = format_dot(sample_nodes)
    assert "digraph" in dot, "测试4失败: DOT 缺少 digraph"
    print("✅ 测试4（输出格式）通过")

    # ---- 测试5: 违规报告 ----
    report = format_violations(result)
    assert "未发现" in report, "测试5失败: 无违规报告错误"
    report2 = format_violations(result2)
    assert "违规" in report2 and "core.base" in report2, "测试5失败: 违规报告错误"
    print("✅ 测试5（违规报告）通过")

    # ---- 测试6: 边界情况 ----
    # 空规则
    empty_result = check_architecture(sample_nodes, [])
    assert empty_result.violations == [], "测试6失败: 空规则不应有违规"
    # 空模块
    empty_nodes_result = check_architecture([], sample_rules)
    assert empty_nodes_result.module_count == 0, "测试6失败: 空模块计数应为0"
    print("✅ 测试6（边界情况）通过")

    print("\n=== 全部自检通过 ===")
    return ERR_OK


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------
def main() -> int:
    parser = argparse.ArgumentParser(
        description="tach — 依赖可视化与架构边界守护",
        epilog="示例: python main.py --root ./src --config tach.json"
    )
    parser.add_argument("--root", type=str, help="项目根目录")
    parser.add_argument("--config", type=str, help="配置文件路径（JSON 或 TOML）")
    parser.add_argument("--target", type=str, help="定向检查的文件或目录")
    parser.add_argument("--format", choices=["tree", "table", "dot"], default="tree",
                        help="输出格式（默认: tree）")
    parser.add_argument("--max-depth", type=int, default=3,
                        help="文本树最大深度（默认: 3）")
    parser.add_argument("--selftest", action="store_true",
                        help="运行内置离线自检")

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        try:
            return run_selftest()
        except AssertionError as exc:
            print(f"❌ 自检失败: {exc}")
            return 1
        except Exception as exc:
            print(f"❌ 自检异常: {exc}")
            return 1

    # 校验参数
    if not args.root or not args.config:
        parser.error(f"{ERR_ARG_INVALID}: 必须指定 --root 和 --config")
        return 1

    try:
        root = Path(args.root)
        config_path = Path(args.config)

        # 加载配置
        config = load_config(config_path)

        # 提取规则
        modules_config = config.get("modules", {})
        rules_config = config.get("rules", [])

        if not rules_config:
            print(f"⚠️ {ERR_NO_RULES}: 未定义任何架构规则", file=sys.stderr)
            return 1

        # 构建规则对象
        rules: List[BoundaryRule] = []
        for rule_item in rules_config:
            if isinstance(rule_item, dict):
                source = rule_item.get("source", "")
                allowed = rule_item.get("allowed", [])
                # 支持字符串形式的 allowed
                if isinstance(allowed, str):
                    allowed = [allowed]
                rules.append(BoundaryRule(source=source, allowed=list(allowed)))

        # 扫描或定向检查
        if args.target:
            target = Path(args.target)
            result = check_target(target, root, rules)
        else:
            nodes = scan_directory(root)
            result = check_architecture(nodes, rules)

        # 输出结果
        print(f"\n扫描模块数: {result.module_count}")
        print(f"依赖关系数: {result.import_count}")

        # 输出依赖图
        if args.format == "tree":
            nodes = scan_directory(root) if not args.target else _scan_target_nodes(Path(args.target), root)
            print("\n" + format_text_tree(nodes, args.max_depth))
        elif args.format == "table":
            nodes = scan_directory(root) if not args.target else _scan_target_nodes(Path(args.target), root)
            print("\n" + format_table(nodes))
        elif args.format == "dot":
            nodes = scan_directory(root) if not args.target else _scan_target_nodes(Path(args.target), root)
            print("\n" + format_dot(nodes))

        # 输出违规报告
        print("\n" + "=" * 60)
        print(format_violations(result))

        # 返回状态
        return 0 if not result.violations else 2

    except FileNotFoundError as exc:
        print(f"❌ {exc}", file=sys.stderr)
        return 1
    except ValueError as exc:
        print(f"❌ {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"❌ {ERR_INTERNAL}: 内部错误: {exc}", file=sys.stderr)
        return 1


def _scan_target_nodes(target: Path, root: Path) -> List[ModuleNode]:
    """辅助函数：扫描目标（文件或目录）的模块节点"""
    nodes: List[ModuleNode] = []
    if target.is_file():
        node = parse_python_file(target, root)
        if node:
            nodes.append(node)
    else:
        for py_file in target.rglob("*.py"):
            node = parse_python_file(py_file, root)
            if node:
                nodes.append(node)
    return nodes


if __name__ == "__main__":
    sys.exit(main())
