#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tui_scaffold.py — 从规格生成可直接运行的 Textual 终端界面（TUI）应用骨架。

重要声明（与 SKILL.md 一致）：
  - 生成过程零第三方依赖：仅使用 Python 标准库（argparse/ast/json/dataclasses/pathlib/typing）。
  - 生成的应用运行需 textual：目标机需 `pip install textual` 才能运行生成的 .py 文件。
  - 生成后校验分两层：
      1) 静态校验（ast.parse + 组件类名/构造参数检查 + import 路径验证）——不依赖 textual 安装。
      2) 运行时校验（若本地已安装 textual，则检查组件类存在性）——若未安装则跳过。

真实能力（与 SKILL.md 声明一致）：
  1. 按规格（名称 + 组件清单 + 主题）生成一个完整的、可 import textual 运行的 TUI 应用 .py 文件
  2. 生成后做静态校验（ast.parse + 必含 import textual + 组件类引用 + 构造参数签名 + import 路径验证），保证产出的 .py 是合法 Python
  3. 支持常见组件：button / input / datatable / label / static / textarea / tree / log / progress / checkbox / select
  4. 结构化错误码 E001-E010 + 降级提示
  5. 支持主题 dark/light/auto，通过 --theme 参数传入并在生成代码中设置（App.theme 属性 + CSS 变量）
  6. DataTable 组件自动添加默认列，避免运行时空白/报错
  7. 生成后尝试 import textual 并检查组件类存在性，版本不匹配时给出友好报错

仅标准库依赖；--selftest 完全离线，不需安装 textual，也不需终端。
生成的应用如需真正运行，则目标机需 `pip install textual`（见 requirements.txt）。
"""
from __future__ import annotations

import argparse
import ast
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# 错误码体系 E001-E010
# ---------------------------------------------------------------------------
ERRORS: Dict[str, Dict[str, str]] = {
    "E001": {"reason": "应用名称非法", "fix": "名称需为合法 Python 标识符（字母/数字/下划线，不以数字开头）"},
    "E002": {"reason": "未指定任何组件", "fix": "用 --components 至少给一个组件，如 button,input,datatable"},
    "E003": {"reason": "输出文件写入失败", "fix": "检查 --output 路径所在目录是否有写权限"},
    "E004": {"reason": "未知组件类型", "fix": "仅支持: " + ", ".join(["button", "input", "datatable", "label", "static", "textarea", "tree", "log", "progress", "checkbox", "select"])},
    "E005": {"reason": "生成代码静态校验失败", "fix": "内部错误，请附日志反馈维护者"},
    "E006": {"reason": "组件清单解析失败", "fix": "--components 用逗号分隔，如 button,input"},
    "E007": {"reason": "主题非法", "fix": "主题可选: dark / light / auto"},
    "E008": {"reason": "输入参数缺失", "fix": "--name 与 --components 为必填"},
    "E009": {"reason": "输出路径不是 .py 文件", "fix": "--output 需以 .py 结尾"},
    "E010": {"reason": "未知内部错误", "fix": "请附上完整日志向维护者反馈"},
}

# 组件 -> (Textual 类名, 生成表达式, 所需 import 路径, 构造参数签名检查函数)
WIDGETS: Dict[str, Dict[str, Any]] = {
    "button":    {"cls": "Button",    "expr": 'Button("点击我", id="btn")',            "mod": "textual.widgets", "args": ["label", "id"]},
    "input":     {"cls": "Input",     "expr": 'Input(placeholder="请输入...")',        "mod": "textual.widgets", "args": ["placeholder"]},
    "datatable": {"cls": "DataTable", "expr": 'DataTable()',                           "mod": "textual.widgets", "args": []},
    "label":     {"cls": "Label",     "expr": 'Label("标签文本")',                     "mod": "textual.widgets", "args": ["content"]},
    "static":    {"cls": "Static",    "expr": 'Static("静态内容")',                    "mod": "textual.widgets", "args": ["content"]},
    "textarea":  {"cls": "TextArea",  "expr": 'TextArea("多行文本...", id="ta")',      "mod": "textual.widgets", "args": ["content", "id"]},
    "tree":      {"cls": "Tree",      "expr": 'Tree("文件树")',                        "mod": "textual.widgets", "args": ["label"]},
    "log":       {"cls": "Log",       "expr": "Log()",                                 "mod": "textual.widgets", "args": []},
    "progress":  {"cls": "ProgressBar","expr": "ProgressBar()",                        "mod": "textual.widgets", "args": []},
    "checkbox":  {"cls": "Checkbox",  "expr": 'Checkbox("启用选项", id="cb")',         "mod": "textual.widgets", "args": ["label", "id"]},
    "select":    {"cls": "Select",    "expr": 'Select([(k, k) for k in ["A","B","C"]], id="sel")', "mod": "textual.widgets", "args": ["options", "id"]},
}
THEMES = {"dark", "light", "auto"}


class ScaffoldError(Exception):
    def __init__(self, code: str, detail: str = ""):
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {ERRORS.get(code, {}).get('reason','未知')} | {detail}")


# ---------------------------------------------------------------------------
# 校验
# ---------------------------------------------------------------------------
def is_valid_identifier(name: str) -> bool:
    return name.isidentifier() and not name[0].isdigit()


def parse_components(raw: str) -> List[str]:
    if not raw:
        raise ScaffoldError("E002", "组件清单为空")
    parts = [p.strip().lower() for p in raw.split(",") if p.strip()]
    if not parts:
        raise ScaffoldError("E002", "组件清单为空")
    for c in parts:
        if c not in WIDGETS:
            raise ScaffoldError("E004", f"未知组件: {c}")
    return parts


# ---------------------------------------------------------------------------
# 生成
# ---------------------------------------------------------------------------
def build_app(name: str, components: List[str], theme: str = "dark") -> str:
    if not is_valid_identifier(name):
        raise ScaffoldError("E001", f"名称 {name!r} 非合法标识符")
    if not components:
        raise ScaffoldError("E002", "组件清单为空")
    if theme not in THEMES:
        raise ScaffoldError("E007", f"主题 {theme!r} 不在 {sorted(THEMES)}")
    # 直接以 Python 接口调用时不会经过 parse_components，此处兜底校验组件名，
    # 保证任何入口下未知组件都返回 E004 结构化错误，而非裸 KeyError。
    for c in components:
        if c not in WIDGETS:
            raise ScaffoldError("E004", f"未知组件: {c}")

    used_mods = set()
    widget_lines: List[str] = []
    for c in components:
        spec = WIDGETS[c]
        used_mods.add(spec["mod"])
        widget_lines.append(f"        yield {spec['expr']}")

    widget_imports = ", ".join(sorted({WIDGETS[c]["cls"] for c in components}))
    
    # 主题映射到 CSS 变量
    theme_css = {
        "dark": """
    Screen { background: #1e1e1e; color: #ffffff; }
    """,
        "light": """
    Screen { background: #ffffff; color: #000000; }
    """,
        "auto": """
    Screen { background: auto; color: auto; }
    """
    }.get(theme, "")
    
    # 为 DataTable 添加默认列
    datatable_init = ""
    if "datatable" in components:
        datatable_init = """
        # DataTable 初始化：添加默认列
        dt = self.query_one(DataTable)
        dt.add_columns("列1", "列2")
        dt.add_row("示例数据1", "示例数据2")
"""
    
    body = f'''# 由 tui_scaffold.py 生成 — Textual TUI 应用
# 运行: pip install textual && python {name}_app.py
from textual.app import App, ComposeResult
from textual.widgets import {widget_imports}


class {name}App(App):
    """自动生成的 {name} 终端应用。"""

    CSS = """
    Screen {{ align: center middle; }}
    #btn {{ margin: 1; }}
    {theme_css}
    """

    def compose(self) -> ComposeResult:
        # 以下组件由规格生成，可自由增删
{chr(10).join(widget_lines)}
{datatable_init}

    def on_mount(self) -> None:
        """应用挂载时设置主题。"""
        self.theme = "{theme}"


if __name__ == "__main__":
    {name}App().run()
'''
    return body


def validate_source(src: str) -> None:
    """静态校验：能 ast.parse + 必须 import textual + 组件构造参数合法性 + import 路径验证。失败抛 E005。"""
    try:
        tree = ast.parse(src)
    except SyntaxError as e:
        raise ScaffoldError("E005", f"生成代码语法错误: {e}")
    imports_textual = False
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("textual"):
            imports_textual = True
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith("textual"):
                    imports_textual = True
    if not imports_textual:
        raise ScaffoldError("E005", "生成代码未包含 textual 导入")
    
    # 深度检查：验证组件构造参数合法性 + import 路径
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                # 检查 DataTable 是否使用 add_columns 方法
                if node.func.id == "DataTable":
                    # 检查是否有 add_columns 调用
                    has_add_columns = False
                    for child in ast.walk(tree):
                        if isinstance(child, ast.Call):
                            if isinstance(child.func, ast.Attribute):
                                if child.func.attr == "add_columns":
                                    has_add_columns = True
                                    break
                    if not has_add_columns:
                        raise ScaffoldError("E005", "DataTable 必须使用 add_columns 方法添加列")
                # 检查 Select 是否有选项参数
                if node.func.id == "Select":
                    if not node.args and not node.keywords:
                        raise ScaffoldError("E005", "Select 必须包含选项参数")
                # 检查其他组件的构造参数
                for comp, spec in WIDGETS.items():
                    if node.func.id == spec["cls"]:
                        # 检查是否使用了正确的参数
                        arg_names = []
                        for arg in node.args:
                            arg_names.append("positional")
                        for kw in node.keywords:
                            arg_names.append(kw.arg)
                        # 检查是否有未知参数
                        known_args = set(spec["args"])
                        for arg_name in arg_names:
                            if arg_name != "positional" and arg_name not in known_args:
                                raise ScaffoldError("E005", f"{spec['cls']} 使用了未知参数 {arg_name!r}")
    
    # 验证 import 路径正确性（textual.widgets 等模块是否存在）
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            # 检查 textual 相关模块路径
            if node.module.startswith("textual"):
                # 验证模块路径格式正确（如 textual.widgets 存在）
                parts = node.module.split(".")
                if len(parts) > 1:
                    # 检查是否包含已知的 textual 子模块
                    valid_submodules = {"app", "widgets", "containers", "screens", "events"}
                    if parts[1] not in valid_submodules:
                        raise ScaffoldError("E005", f"无效的 textual 子模块路径: {node.module}")


def check_textual_runtime(components: List[str]) -> None:
    """尝试 import textual 并检查组件类存在性，版本不匹配时给出友好报错。"""
    try:
        import textual
    except ImportError:
        # 本地未安装 textual 时跳过运行时检查（生成阶段不强制要求）
        return
    
    for comp in components:
        spec = WIDGETS[comp]
        mod_name = spec["mod"]
        cls_name = spec["cls"]
        try:
            mod = __import__(mod_name, fromlist=[cls_name])
            if not hasattr(mod, cls_name):
                raise ScaffoldError("E010", f"textual 版本不匹配：组件 {comp} 的类 {cls_name} 不存在于 {mod_name} 中，请升级 textual 或调整组件")
        except ImportError as e:
            raise ScaffoldError("E010", f"无法导入 {mod_name}：{e}，请检查 textual 安装")


def write_app(name: str, components: List[str], output: str, theme: str = "dark") -> Dict[str, Any]:
    if not output.endswith(".py"):
        raise ScaffoldError("E009", f"输出路径 {output!r} 需以 .py 结尾")
    src = build_app(name, components, theme)
    validate_source(src)
    # 运行时检查（如果 textual 已安装）
    check_textual_runtime(components)
    try:
        Path(output).write_text(src, encoding="utf-8", errors="replace")
    except OSError as e:
        raise ScaffoldError("E003", f"写入失败: {e}")
    return {
        "name": name,
        "components": components,
        "output": output,
        "lines": src.count(chr(10)) + 1,
        "theme": theme,
    }


# ---------------------------------------------------------------------------
# 离线自检
# ---------------------------------------------------------------------------
def selftest() -> int:
    print("== tui_scaffold.py 离线自检 ==")
    failures: List[str] = []

    def check(name: str, cond: bool):
        print(f"  [{'OK' if cond else 'FAIL'}] {name}")
        if not cond:
            failures.append(name)

    check("错误码 E001-E010 齐全", set(ERRORS) == {f"E{i:03d}" for i in range(1, 11)})

    # 1) 生成样例 + 静态校验通过（含 DataTable 列检查 + import 路径验证）
    try:
        src = build_app("Demo", ["button", "input", "datatable"], "dark")
        validate_source(src)
        check("生成 Demo 应用且含 textual 导入", "textual" in src and "DemoApp" in src)
        check("DataTable 使用 add_columns 方法", "add_columns" in src)
        check("生成代码包含主题设置", "self.theme = \"dark\"" in src)
        check("import 路径验证通过", "textual.widgets" in src)
    except Exception as e:  # noqa: BLE001
        check(f"生成异常: {e}", False)

    # 2) 写出到临时文件
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        out = str(Path(td) / "demo_app.py")
        info = write_app("Demo", ["label", "static", "log"], out, "light")
        check("写出文件且行数>0", Path(out).exists() and info["lines"] > 0)
        # 再次 ast 校验落盘文件
        try:
            ast.parse(Path(out).read_text(encoding="utf-8", errors="replace"))
            check("落盘文件可被 ast.parse", True)
        except Exception as e:  # noqa: BLE001
            check(f"落盘文件语法错误: {e}", False)

    # 3) 错误路径
    bad_cases = [("1bad", "E001", ["button"]), ("", "E001", ["button"]), ("Ok", "E002", [])]
    for bad_name, code, comps in bad_cases:
        raised = False
        try:
            build_app(bad_name, comps, "dark")
        except ScaffoldError as e:
            raised = e.code == code
        check(f"名称 {bad_name!r} 组件{comps} 抛 {code}", raised)

    # 4) 未知组件 E004
    raised = False
    try:
        parse_components("button,unknownx")
    except ScaffoldError as e:
        raised = e.code == "E004"
    check("未知组件抛 E004", raised)

    # 4b) Python 接口直调（绕过 parse_components）同样应抛 E004 而非 KeyError
    raised = False
    try:
        build_app("Demo", ["button", "unknownx"], "dark")
    except ScaffoldError as e:
        raised = e.code == "E004"
    check("接口直调未知组件抛 E004", raised)

    # 5) 非 .py 输出 E009
    raised = False
    try:
        write_app("Demo", ["button"], "out.txt", "dark")
    except ScaffoldError as e:
        raised = e.code == "E009"
    check("非 .py 输出抛 E009", raised)

    if failures:
        print(f"\n❌ 自检失败 {len(failures)} 项: {failures}")
        return 1
    print("\n✅ 全部自检通过")
    return 0


# ---------------------------------------------------------------------------
# CLI 入口（R1 契约 + R4 预览 + R6 可解释输出）
# ---------------------------------------------------------------------------
def main() -> int:
    parser = argparse.ArgumentParser(
        description="textual 终端界面（TUI）应用骨架生成器",
        epilog="示例: python tui_scaffold.py --name Demo --components button,label --output demo.py")
    parser.add_argument("--name", default="DemoApp", help="应用类名")
    parser.add_argument("--components", default="button,label",
                        help="组件清单（逗号分隔）：button/input/datatable/label/static/textarea/tree/log/progress/checkbox/select")
    parser.add_argument("--theme", default="dark", help="主题: dark / light / auto")
    parser.add_argument("--output", "-o", help="输出 .py 文件路径")
    parser.add_argument("--selftest", action="store_true", help="运行离线自检")
    parser.add_argument("--dry-run", action="store_true", help="预览模式：只打印生成内容不写盘")
    parser.add_argument("--verbose", "-v", action="store_true", help="输出生成决策明细（组件数、校验步骤、行数）")
    args = parser.parse_args()

    if args.selftest:
        return selftest()

    try:
        comps = parse_components(args.components)
        src = build_app(args.name, comps, args.theme)
        validate_source(src)
    except ScaffoldError as e:
        print(f"{e.code}: {e.message}", file=sys.stderr)
        return 1

    if args.verbose:
        print(f"[verbose] 组件 {len(comps)} 个: {comps}")
        print(f"[verbose] 静态校验通过（ast + import + 构造参数）")

    if not args.output:
        print(src)
        return 0

    if not args.dry_run:
        try:
            Path(args.output).write_text(src, encoding="utf-8", errors="replace")
            print(f"✅ 已写入 {args.output}（{src.count(chr(10)) + 1} 行）")
        except OSError as e:
            print(f"E003: 写入失败: {e}", file=sys.stderr)
            return 1
    else:
        print(f"🔍 [dry-run] 预览模式，不写盘。输出路径: {args.output}")
        print(src)
    return 0


if __name__ == "__main__":
    sys.exit(main())
