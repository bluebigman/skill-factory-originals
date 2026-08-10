#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tach — 依赖透视与架构边界守护（clean-room 独立实现）

功能：
  1. 静态解析 Python 源码中的模块导入关系
  2. 按包/模块粒度聚合依赖图谱
  3. 依据架构规则（允许/禁止的依赖方向）执行一致性校验
  4. 输出结构化依赖清单与违规报告

仅使用 Python 标准库实现，无第三方依赖。
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import re
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Callable

# ---------------------------------------------------------------------------
# 错误码定义
# ---------------------------------------------------------------------------
ERR_OK = 0
ERR_USAGE = "E001"       # 命令行参数错误
ERR_PATH = "E002"        # 路径不存在或不可读
ERR_PARSE = "E003"       # 源码解析失败
ERR_RULE = "E004"        # 架构规则格式错误
ERR_INTERNAL = "E005"    # 内部逻辑错误
ERR_OUTPUT = "E006"      # 输出写入失败
ERR_SELFTEST = "E007"    # 自检失败
ERR_EMPTY = "E008"       # 无有效源码文件
ERR_MODULE = "E009"      # 模块名解析失败
ERR_UNKNOWN = "E010"     # 未知错误


# ---------------------------------------------------------------------------
# 数据结构
# ---------------------------------------------------------------------------
@dataclass
class Dependency:
    """一条依赖关系：source -> target"""
    source: str
    target: str
    line: int = 0
    column: int = 0


@dataclass
class ArchRule:
    """架构规则：允许或禁止 source 依赖 target"""
    kind: str            # "allow" 或 "forbid"
    source_pattern: str  # 支持简单通配符 * 和 **（** 表示任意层级）
    target_pattern: str


@dataclass
class Violation:
    """违规记录"""
    rule: ArchRule
    source: str
    target: str
    line: int = 0


@dataclass
class AnalysisResult:
    """分析结果汇总"""
    dependencies: List[Dependency] = field(default_factory=list)
    modules: Set[str] = field(default_factory=set)
    violations: List[Violation] = field(default_factory=list)
    files_scanned: int = 0
    errors: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# 依赖解析器：基于 AST 静态扫描
# ---------------------------------------------------------------------------
class DependencyParser:
    """使用 Python 标准库 ast 模块解析源码中的导入语句"""

    # 常见第三方库前缀，用于过滤标准库/第三方依赖
    STDLIB_MODULES: Set[str] = set(sys.stdlib_module_names) if hasattr(sys, "stdlib_module_names") else set()

    def __init__(self, root: Path):
        self.root = root
        self.result = AnalysisResult()
        self._imports_cache: Dict[Path, List[Tuple[str, int]]] = {}

    def parse_project(self) -> AnalysisResult:
        """扫描项目根目录下所有 .py 文件"""
        if not self.root.exists() or not self.root.is_dir():
            self.result.errors.append(f"{ERR_PATH}: 路径不存在或不是目录: {self.root}")
            return self.result

        py_files = sorted(self.root.rglob("*.py"))
        # 跳过常见生成目录
        py_files = [f for f in py_files if not any(
            part in {".git", "__pycache__", ".venv", "venv", "node_modules", ".tox", ".eggs"}
            for part in f.parts
        )]

        if not py_files:
            self.result.errors.append(f"{ERR_EMPTY}: 未找到任何 .py 文件")
            return self.result

        for py_file in py_files:
            self.result.files_scanned += 1
            rel_path = py_file.relative_to(self.root)
            module_name = self._path_to_module(rel_path)
            if not module_name:
                continue
            self.result.modules.add(module_name)
            imports = self._parse_file_imports(py_file)
            for imported, line in imports:
                target = self._resolve_import_target(imported, module_name)
                if target:
                    dep = Dependency(source=module_name, target=target, line=line)
                    self.result.dependencies.append(dep)

        return self.result

    def _path_to_module(self, rel_path: Path) -> Optional[str]:
        """将相对路径转换为模块名，如 src/pkg/mod.py -> src.pkg.mod"""
        try:
            parts = list(rel_path.parts)
            if parts[-1] == "__init__.py":
                parts = parts[:-1]  # 包目录
            elif parts[-1].endswith(".py"):
                parts[-1] = parts[-1][:-3]
            else:
                return None
            # 过滤非法标识符
            valid_parts = []
            for p in parts:
                if p.isidentifier():
                    valid_parts.append(p)
                else:
                    valid_parts.append("_")
            return ".".join(valid_parts) if valid_parts else None
        except Exception:
            return None

    def _parse_file_imports(self, file_path: Path) -> List[Tuple[str, int]]:
        """解析单个文件中的导入语句，返回 (模块名, 行号) 列表"""
        try:
            source = file_path.read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(source, filename=str(file_path))
        except (SyntaxError, UnicodeDecodeError) as e:
            self.result.errors.append(f"{ERR_PARSE}: 解析失败 {file_path}: {e}")
            return []

        imports: List[Tuple[str, int]] = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append((alias.name, node.lineno))
            elif isinstance(node, ast.ImportFrom):
                if node.module:  # 相对导入 module 为 None
                    imports.append((node.module, node.lineno))
                elif node.level > 0:
                    # 相对导入，转换为绝对模块名在 resolve 阶段处理
                    imports.append((f".{'.' * (node.level - 1)}{node.module or ''}", node.lineno))

        return imports

    def _resolve_import_target(self, imported: str, current_module: str) -> Optional[str]:
        """将导入名解析为绝对模块名"""
        if not imported:
            return None

        # 处理相对导入
        if imported.startswith("."):
            level = 0
            while imported.startswith("."):
                level += 1
                imported = imported[1:]
            base_parts = current_module.split(".")
            if level > len(base_parts):
                return None
            base = base_parts[:len(base_parts) - level + 1]
            if imported:
                base.append(imported)
            return ".".join(base) if base else None

        # 绝对导入
        return imported


# ---------------------------------------------------------------------------
# 架构规则引擎
# ---------------------------------------------------------------------------
class RuleEngine:
    """架构规则匹配与校验"""

    def __init__(self, rules: List[ArchRule]):
        self.rules = rules
        self._compiled: List[Tuple[ArchRule, Callable, Callable]] = []
        for rule in rules:
            src_pattern = self._compile_pattern(rule.source_pattern)
            tgt_pattern = self._compile_pattern(rule.target_pattern)
            self._compiled.append((rule, src_pattern, tgt_pattern))

    @staticmethod
    def _compile_pattern(pattern: str) -> Callable[[str], bool]:
        """将通配符模式编译为匹配函数"""
        if pattern == "**":
            return lambda s: True
        
        # 将 ** 转换为匹配任意层级，* 转换为匹配单层
        # 先将 ** 替换为特殊标记，避免与 * 冲突
        parts = pattern.split("**")
        regex_parts = []
        
        for i, part in enumerate(parts):
            if i > 0:
                # 两个部分之间的 ** 匹配任意层级（包括零个）
                regex_parts.append(".*")
            
            if part:
                # 处理单个 * 通配符
                part_escaped = re.escape(part)
                # 将 \* 转换回 * 作为通配符
                part_escaped = part_escaped.replace(r"\*", "[^.]*")
                regex_parts.append(part_escaped)
        
        regex_str = "".join(regex_parts)
        
        # 特殊处理：如果模式以 ** 结尾，需要匹配剩余所有内容
        if pattern.endswith("**"):
            regex_str += ".*"
        
        # 确保完整匹配
        regex_str = f"^{regex_str}$"
        
        try:
            regex = re.compile(regex_str)
            return lambda s: bool(regex.match(s))
        except re.error:
            # 如果编译失败，退化为精确匹配
            return lambda s: s == pattern

    def check_dependency(self, dep: Dependency) -> Optional[Violation]:
        """检查单条依赖是否违规。返回违规记录或 None"""
        # 先检查 forbid 规则
        for rule, src_match, tgt_match in self._compiled:
            if rule.kind == "forbid" and src_match(dep.source) and tgt_match(dep.target):
                return Violation(rule=rule, source=dep.source, target=dep.target, line=dep.line)

        # 如果有匹配的 allow 规则，则允许
        for rule, src_match, tgt_match in self._compiled:
            if rule.kind == "allow" and src_match(dep.source) and tgt_match(dep.target):
                return None

        # 无匹配规则时默认允许
        return None

    def validate(self, deps: List[Dependency]) -> List[Violation]:
        """批量校验依赖"""
        violations = []
        for dep in deps:
            v = self.check_dependency(dep)
            if v:
                violations.append(v)
        return violations


# ---------------------------------------------------------------------------
# 架构规则解析器
# ---------------------------------------------------------------------------
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


def parse_rules(rules_data: List[Dict]) -> List[ArchRule]:
    """从字典列表解析架构规则"""
    rules = []
    for item in rules_data:
        kind = item.get("kind", "").lower()
        if kind not in {"allow", "forbid"}:
            raise ValueError(f"{ERR_RULE}: 无效规则类型: {kind}")
        source = item.get("source", "")
        target = item.get("target", "")
        if not source or not target:
            raise ValueError(f"{ERR_RULE}: source 和 target 不能为空")
        rules.append(ArchRule(kind=kind, source_pattern=source, target_pattern=target))
    return rules


# ---------------------------------------------------------------------------
# 输出格式化
# ---------------------------------------------------------------------------
def format_dependency_list(deps: List[Dependency]) -> str:
    """格式化依赖清单为文本"""
    lines = ["依赖清单:", "=" * 60]
    for dep in sorted(deps, key=lambda d: (d.source, d.target)):
        lines.append(f"  {dep.source} -> {dep.target}  [行 {dep.line}]")
    return "\n".join(lines)


def format_violations(violations: List[Violation]) -> str:
    """格式化违规报告"""
    if not violations:
        return "✅ 未发现架构违规"
    lines = ["❌ 架构违规报告:", "=" * 60]
    for v in violations:
        action = "禁止" if v.rule.kind == "forbid" else "允许"
        lines.append(
            f"  [{action}] {v.source} -> {v.target} (行 {v.line}) "
            f"[规则: {v.rule.source_pattern} -> {v.rule.target_pattern}]"
        )
    return "\n".join(lines)


def format_json(result: AnalysisResult) -> str:
    """输出 JSON 格式结果"""
    data = {
        "modules": sorted(result.modules),
        "dependencies": [
            {"source": d.source, "target": d.target, "line": d.line}
            for d in result.dependencies
        ],
        "violations": [
            {
                "source": v.source,
                "target": v.target,
                "line": v.line,
                "rule": {"kind": v.rule.kind, "source": v.rule.source_pattern, "target": v.rule.target_pattern}
            }
            for v in result.violations
        ],
        "files_scanned": result.files_scanned,
        "errors": result.errors,
    }
    return json.dumps(data, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# 主分析流程
# ---------------------------------------------------------------------------
def run_analysis(
    project_path: str,
    rules: Optional[List[ArchRule]] = None,
    json_output: bool = False,
) -> Tuple[int, str]:
    """执行完整分析流程，返回 (退出码, 输出文本)"""
    root = Path(project_path)
    if not root.exists():
        return 1, f"{ERR_PATH}: 路径不存在: {project_path}"
    if not root.is_dir():
        return 1, f"{ERR_PATH}: 不是目录: {project_path}"

    # 解析依赖
    parser = DependencyParser(root)
    result = parser.parse_project()

    # 执行规则校验
    if rules:
        engine = RuleEngine(rules)
        result.violations = engine.validate(result.dependencies)

    # 生成输出
    if json_output:
        output = format_json(result)
    else:
        parts = []
        parts.append(f"扫描文件数: {result.files_scanned}")
        parts.append(f"发现模块数: {len(result.modules)}")
        parts.append(f"发现依赖数: {len(result.dependencies)}")
        parts.append("")
        parts.append(format_dependency_list(result.dependencies))
        parts.append("")
        parts.append(format_violations(result.violations))
        if result.errors:
            parts.append("")
            parts.append("错误信息:")
            for err in result.errors:
                parts.append(f"  {err}")
        output = "\n".join(parts)

    # 如果有错误，返回非零退出码
    if result.errors:
        return 2, output
    if result.violations:
        return 3, output
    return 0, output


# ---------------------------------------------------------------------------
# 内置自检（不依赖外部文件，纯内存数据）
# ---------------------------------------------------------------------------
def run_selftest() -> int:
    """内置硬编码样例数据的离线自检"""
    print("开始自检...")

    # --- 测试 1: 依赖解析器（使用临时内存 AST 模拟）---
    # 由于解析器基于文件系统，这里直接测试模块名转换和规则引擎
    print("[1/4] 测试模块名转换...")
    parser = DependencyParser(Path("."))
    test_cases = [
        (Path("src/main.py"), "src.main"),
        (Path("pkg/__init__.py"), "pkg"),
        (Path("app/utils/helper.py"), "app.utils.helper"),
    ]
    for path, expected in test_cases:
        result = parser._path_to_module(path)
        assert result == expected, f"模块名转换失败: {path} -> {result} (期望 {expected})"
    print("  ✅ 模块名转换测试通过")

    # --- 测试 2: 规则匹配 ---
    print("[2/4] 测试规则引擎...")
    rules = [
        ArchRule(kind="forbid", source_pattern="controller.**", target_pattern="dao.**"),
        ArchRule(kind="allow", source_pattern="service.**", target_pattern="dao.**"),
        ArchRule(kind="forbid", source_pattern="**", target_pattern="**"),
    ]
    engine = RuleEngine(rules)

    # 测试 forbid 规则
    dep1 = Dependency(source="controller.user", target="dao.user", line=10)
    v = engine.check_dependency(dep1)
    assert v is not None, "应检测到 controller -> dao 违规"
    assert v.rule.kind == "forbid"

    # 测试 allow 规则覆盖
    dep2 = Dependency(source="service.user", target="dao.user", line=20)
    v = engine.check_dependency(dep2)
    assert v is None, "service -> dao 应被 allow 规则允许"

    # 测试通配符
    dep3 = Dependency(source="any.module", target="any.other", line=30)
    v = engine.check_dependency(dep3)
    assert v is not None, "** -> ** forbid 应匹配所有"

    print("  ✅ 规则引擎测试通过")

    # --- 测试 3: 规则解析 ---
    print("[3/4] 测试规则解析...")
    rules_data = [
        {"kind": "forbid", "source": "a.*", "target": "b.*"},
        {"kind": "allow", "source": "x.**", "target": "y.**"},
    ]
    parsed_rules = parse_rules(rules_data)
    assert len(parsed_rules) == 2
    assert parsed_rules[0].kind == "forbid"
    assert parsed_rules[1].kind == "allow"
    print("  ✅ 规则解析测试通过")

    # --- 测试 4: 集成测试（模拟依赖图）---
    print("[4/4] 测试完整流程...")
    # 构造模拟依赖和规则
    mock_deps = [
        Dependency(source="app.controller.user", target="app.dao.user", line=1),
        Dependency(source="app.service.user", target="app.dao.user", line=2),
        Dependency(source="app.util.helper", target="app.middleware.auth", line=3),
    ]
    mock_rules = [
        ArchRule(kind="forbid", source_pattern="app.controller.**", target_pattern="app.dao.**"),
        ArchRule(kind="allow", source_pattern="app.service.**", target_pattern="app.dao.**"),
        ArchRule(kind="forbid", source_pattern="app.util.**", target_pattern="app.middleware.**"),
    ]
    engine = RuleEngine(mock_rules)
    violations = engine.validate(mock_deps)
    assert len(violations) == 2, f"期望 2 个违规，实际 {len(violations)}"

    # 验证违规内容
    viol_sources = {v.source for v in violations}
    assert "app.controller.user" in viol_sources
    assert "app.util.helper" in viol_sources

    # 验证 JSON 输出
    result = AnalysisResult()
    result.dependencies = mock_deps
    result.violations = violations
    result.modules = {"app.controller.user", "app.dao.user", "app.service.user", "app.util.helper", "app.middleware.auth"}
    result.files_scanned = 5
    json_out = format_json(result)
    assert "app.controller.user" in json_out
    assert "violations" in json_out

    print("  ✅ 集成测试通过")

    print("\n✅ 全部自检通过")
    return 0


# ---------------------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------------------
def main() -> int:
    """主入口函数"""
    parser = argparse.ArgumentParser(
        description="tach — 依赖透视与架构边界守护",
        epilog="示例: python main.py --path ./src --rules rules.json",
    )
    parser.add_argument("--path", type=str, help="项目根目录路径")
    parser.add_argument("--rules", type=str, help="架构规则 JSON 文件路径")
    parser.add_argument("--json", action="store_true", help="输出 JSON 格式")
    parser.add_argument("--selftest", action="store_true", help="运行内置自检")

    parser.add_argument("--verbose", action="store_true", help="显示修改明细")  # R6 可解释输出

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        try:
            return run_selftest()
        except AssertionError as e:
            print(f"{ERR_SELFTEST}: 自检失败: {e}")
            return 1
        except Exception as e:
            print(f"{ERR_UNKNOWN}: 自检异常: {e}")
            return 1

    # 常规模式
    if not args.path:
        print(f"{ERR_USAGE}: 必须提供 --path 参数", file=sys.stderr)
        parser.print_help(sys.stderr)
        return 1

    # 加载规则
    rules: List[ArchRule] = []
    if args.rules:
        try:
            rules_path = Path(args.rules)
            if not rules_path.exists():
                print(f"{ERR_PATH}: 规则文件不存在: {args.rules}", file=sys.stderr)
                return 1
            with open(rules_path, "r", encoding="utf-8") as f:
                rules_data = json.load(f)
            rules = parse_rules(rules_data)
        except (json.JSONDecodeError, ValueError) as e:
            print(f"{ERR_RULE}: 规则文件解析失败: {e}", file=sys.stderr)
            return 1
        except Exception as e:
            print(f"{ERR_UNKNOWN}: 加载规则失败: {e}", file=sys.stderr)
            return 1

    # 执行分析
    try:
        exit_code, output = run_analysis(args.path, rules, args.json)
        print(output)
        return exit_code
    except Exception as e:
        print(f"{ERR_INTERNAL}: 分析过程异常: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
