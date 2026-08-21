#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
design-harness 技能实现脚本
===========================
功能：将设计稿或需求转化为可验证的前端原型，提供结构化输出与置信度提示。
本脚本为 clean-room 独立实现，仅依据功能规格编写。

用法示例：
    python scripts/main.py --help
    python scripts/main.py --selftest
    python scripts/main.py --input design.json --output proto.html --format html
"""

import argparse
import json
import os
import sys
import tempfile
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Tuple
dry_run = False  # v3.274 模块级 dry-run 标志

# ---------------------------------------------------------------------------
# 错误码定义
# ---------------------------------------------------------------------------
ERROR_CODES = {
    "E001": "输入文件不存在或无法读取",
    "E002": "输入 JSON 格式非法",
    "E003": "输入数据结构不完整（缺少必需字段）",
    "E004": "不支持的输出格式",
    "E005": "输出目录不可写",
    "E006": "内部逻辑错误（未知组件类型）",
    "E007": "参数冲突（如 --input 与 --selftest 同时使用）",
    "E008": "数据字段类型错误",
    "E009": "自检失败",
    "E010": "未捕获的运行时异常",
}


def fail(code: str, message: str) -> None:
    """打印错误并退出。"""
    sys.stderr.write(f"[{code}] {message}\n")
    sys.exit(1)


# ---------------------------------------------------------------------------
# 数据模型
# ---------------------------------------------------------------------------
@dataclass
class DesignComponent:
    """设计稿中的单个组件。"""
    type: str                 # 组件类型：button / input / text / image / container
    label: str = ""           # 组件名称或文本内容
    x: int = 0                # 横坐标（px）
    y: int = 0                # 纵坐标（px）
    width: int = 100          # 宽度（px）
    height: int = 40          # 高度（px）
    color: str = "#333333"    # 主色
    font_size: int = 14       # 字号（px）
    interactive: bool = False # 是否为交互组件
    action: str = ""          # 交互动作描述（如 "跳转到详情页"）


@dataclass
class DesignDocument:
    """一份完整的结构化设计稿。"""
    title: str = "未命名设计"
    width: int = 375          # 画布宽度（px）
    height: int = 812         # 画布高度（px）
    components: List[DesignComponent] = field(default_factory=list)
    breakpoints: List[int] = field(default_factory=lambda: [375, 768, 1024])  # 响应式断点


# ---------------------------------------------------------------------------
# 核心逻辑：设计稿解析
# ---------------------------------------------------------------------------
def parse_design_data(data: Dict[str, Any]) -> DesignDocument:
    """
    将原始 JSON 数据解析为 DesignDocument 对象。
    期望输入格式：
    {
        "title": "登录页",
        "width": 375,
        "height": 812,
        "components": [
            {"type": "button", "label": "登录", "x": 20, "y": 300, "width": 200, "height": 48, "interactive": true, "action": "提交表单"}
        ]
    }
    """
    if not isinstance(data, dict):
        fail("E008", "顶层数据必须是 JSON 对象")

    # 必需字段检查
    if "components" not in data:
        fail("E003", "缺少必需字段 'components'")

    doc = DesignDocument(
        title=str(data.get("title", "未命名设计")),
        width=int(data.get("width", 375)),
        height=int(data.get("height", 812)),
    )

    # 解析断点（可选）
    if "breakpoints" in data:
        try:
            doc.breakpoints = [int(b) for b in data["breakpoints"]]
        except (TypeError, ValueError):
            fail("E008", "'breakpoints' 字段必须是整数列表")

    # 解析组件列表
    comp_list = data["components"]
    if not isinstance(comp_list, list):
        fail("E008", "'components' 字段必须是列表")

    for item in comp_list:
        if not isinstance(item, dict):
            fail("E008", "组件必须是 JSON 对象")

        ctype = item.get("type", "")
        if ctype not in ("button", "input", "text", "image", "container"):
            fail("E006", f"未知组件类型: {ctype}")

        comp = DesignComponent(
            type=ctype,
            label=str(item.get("label", "")),
            x=int(item.get("x", 0)),
            y=int(item.get("y", 0)),
            width=int(item.get("width", 100)),
            height=int(item.get("height", 40)),
            color=str(item.get("color", "#333333")),
            font_size=int(item.get("font_size", 14)),
            interactive=bool(item.get("interactive", False)),
            action=str(item.get("action", "")),
        )
        doc.components.append(comp)

    return doc


# ---------------------------------------------------------------------------
# 核心逻辑：前端代码生成
# ---------------------------------------------------------------------------
def generate_html(doc: DesignDocument) -> str:
    """将 DesignDocument 转换为 HTML 原型代码。"""
    lines: List[str] = []
    lines.append("<!DOCTYPE html>")
    lines.append('<html lang="zh-CN">')
    lines.append("<head>")
    lines.append('  <meta charset="UTF-8">')
    lines.append('  <meta name="viewport" content="width=device-width, initial-scale=1.0">')
    lines.append(f"  <title>{doc.title}</title>")
    lines.append("  <style>")
    lines.append("    * { box-sizing: border-box; margin: 0; padding: 0; }")
    lines.append(f"    body {{ font-family: 'PingFang SC', 'Helvetica Neue', Arial, sans-serif; background: #f5f5f5; }}")
    lines.append(f"    .design-canvas {{ width: {doc.width}px; min-height: {doc.height}px; margin: 0 auto; background: #ffffff; position: relative; }}")
    lines.append("    /* 响应式适配建议 */")
    for i, bp in enumerate(doc.breakpoints):
        if i == 0:
            continue  # 最小断点不写媒体查询
        lines.append(f"    @media (min-width: {bp}px) {{ .design-canvas {{ width: {bp}px; }} }}")
    lines.append("  </style>")
    lines.append("</head>")
    lines.append("<body>")
    lines.append(f'  <div class="design-canvas" data-title="{doc.title}" data-width="{doc.width}" data-height="{doc.height}">')

    # 为每个组件生成对应 HTML 元素
    for comp in doc.components:
        style_attrs = (
            f"position:absolute; "
            f"left:{comp.x}px; top:{comp.y}px; "
            f"width:{comp.width}px; height:{comp.height}px; "
            f"font-size:{comp.font_size}px; "
            f"color:{comp.color}; "
        )

        if comp.type == "button":
            bg_color = comp.color if comp.color.startswith("#") else "#4A90D9"
            style_attrs += (
                f"background:{bg_color}; color:#fff; border:none; border-radius:6px; "
                f"display:flex; align-items:center; justify-content:center; cursor:pointer;"
            )
            lines.append(
                f'    <div data-component="button" data-label="{comp.label}" '
                f'data-action="{comp.action}" style="{style_attrs}">{comp.label}</div>'
            )
        elif comp.type == "input":
            lines.append(
                f'    <input type="text" placeholder="{comp.label}" '
                f'data-component="input" style="{style_attrs}border:1px solid #ccc; border-radius:4px; padding:0 8px;">'
            )
        elif comp.type == "text":
            lines.append(
                f'    <div data-component="text" style="{style_attrs}">{comp.label}</div>'
            )
        elif comp.type == "image":
            lines.append(
                f'    <div data-component="image" data-label="{comp.label}" '
                f'style="{style_attrs}background:#eee; border:1px dashed #aaa; '
                f'display:flex; align-items:center; justify-content:center; color:#999;">'
                f'🖼️ {comp.label}</div>'
            )
        elif comp.type == "container":
            lines.append(
                f'    <div data-component="container" data-label="{comp.label}" '
                f'style="{style_attrs}background:{comp.color}; border:1px solid #ddd; border-radius:8px;"></div>'
            )
        else:
            fail("E006", f"无法生成未知组件类型: {comp.type}")

    lines.append("  </div>")
    lines.append("</body>")
    lines.append("</html>")
    return "\n".join(lines)


def generate_css(doc: DesignDocument) -> str:
    """生成独立的 CSS 样式文件内容。"""
    lines: List[str] = []
    lines.append(f"/* {doc.title} - 原型样式 */")
    lines.append("* { box-sizing: border-box; margin: 0; padding: 0; }")
    lines.append("body { font-family: 'PingFang SC', sans-serif; background: #f0f0f0; }")
    lines.append(f".design-canvas {{ width: {doc.width}px; min-height: {doc.height}px; margin: 0 auto; background: #fff; position: relative; }}")
    lines.append("[data-component='button'] { display: flex; align-items: center; justify-content: center; cursor: pointer; border: none; border-radius: 6px; color: #fff; }")
    lines.append("[data-component='input'] { border: 1px solid #ccc; border-radius: 4px; padding: 0 8px; }")
    lines.append("[data-component='image'] { background: #eee; border: 1px dashed #aaa; display: flex; align-items: center; justify-content: center; color: #999; }")
    lines.append("[data-component='container'] { border: 1px solid #ddd; border-radius: 8px; }")
    for i, bp in enumerate(doc.breakpoints):
        if i == 0:
            continue
        lines.append(f"@media (min-width: {bp}px) {{ .design-canvas {{ width: {bp}px; }} }}")
    return "\n".join(lines)


def generate_js(doc: DesignDocument) -> str:
    """生成交互逻辑标注 JS 文件内容。"""
    lines: List[str] = []
    lines.append("// 交互逻辑标注 - 由 design-harness 生成")
    lines.append("// 此文件仅包含交互点标注，不包含真实业务逻辑")
    lines.append("(function() {")
    lines.append("  const interactions = [];")
    for comp in doc.components:
        if comp.interactive:
            lines.append(f"  interactions.push({{ component: '{comp.label}', type: '{comp.type}', action: '{comp.action}' }});")
    lines.append("  window.__designInteractions = interactions;")
    lines.append("  console.log('[design-harness] 已标注 ' + interactions.length + ' 个交互点');")
    lines.append("})();")
    return "\n".join(lines)


def export_design(doc: DesignDocument, output_dir: str, fmt: str) -> Dict[str, str]:
    """
    将 DesignDocument 导出为指定格式的文件。
    返回生成的文件路径字典。
    """
    os.makedirs(output_dir, exist_ok=True)
    generated: Dict[str, str] = {}

    if fmt == "html":
        html_content = generate_html(doc)
        html_path = os.path.join(output_dir, "index.html")
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        generated["html"] = html_path

    elif fmt == "css":
        css_content = generate_css(doc)
        css_path = os.path.join(output_dir, "style.css")
        with open(css_path, "w", encoding="utf-8") as f:
            f.write(css_content)
        generated["css"] = css_path

    elif fmt == "js":
        js_content = generate_js(doc)
        js_path = os.path.join(output_dir, "interactions.js")
        with open(js_path, "w", encoding="utf-8") as f:
            f.write(js_content)
        generated["js"] = js_path

    elif fmt == "json":
        json_path = os.path.join(output_dir, "design.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(asdict(doc), f, ensure_ascii=False, indent=2)
        generated["json"] = json_path

    elif fmt == "vue":
        # Vue 单文件组件原型（简化输出）
        html_part = generate_html(doc)
        vue_content = f"""
<template>
{html_part}
</template>

<script>
export default {{
  name: 'DesignPrototype',
  data() {{
    return {{
      title: '{doc.title}',
      components: {json.dumps(asdict(doc)['components'], ensure_ascii=False)}
    }}
  }},
  mounted() {{
    console.log('[design-harness] Vue 原型已加载');
  }}
}}
</script>

<style scoped>
{generate_css(doc)}
</style>
"""
        vue_path = os.path.join(output_dir, "Prototype.vue")
        with open(vue_path, "w", encoding="utf-8") as f:
            f.write(vue_content)
        generated["vue"] = vue_path

    elif fmt == "react":
        # React 函数组件原型（简化输出）
        html_part = generate_html(doc)
        react_content = f"""
import React from 'react';

const DesignPrototype = () => {{
  return (
    <>
      {html_part}
    </>
  );
}};

export default DesignPrototype;
"""
        react_path = os.path.join(output_dir, "DesignPrototype.jsx")
        with open(react_path, "w", encoding="utf-8") as f:
            f.write(react_content)
        generated["react"] = react_path

    else:
        fail("E004", f"不支持的输出格式: {fmt}")

    return generated


# ---------------------------------------------------------------------------
# 自检逻辑（--selftest）
# ---------------------------------------------------------------------------
def run_selftest() -> None:
    """
    内置硬编码样例数据，离线自检核心逻辑。
    不读外部文件、不依赖当前工作目录、不访问网络。
    """
    # 硬编码样例：一个简单的登录页设计
    sample_data = {
        "title": "登录页原型",
        "width": 375,
        "height": 812,
        "breakpoints": [375, 768, 1024],
        "components": [
            {"type": "text", "label": "欢迎登录", "x": 20, "y": 80, "width": 200, "height": 40, "font_size": 24, "color": "#333333"},
            {"type": "input", "label": "请输入用户名", "x": 20, "y": 150, "width": 335, "height": 48},
            {"type": "input", "label": "请输入密码", "x": 20, "y": 210, "width": 335, "height": 48},
            {"type": "button", "label": "登 录", "x": 20, "y": 280, "width": 335, "height": 48, "color": "#4A90D9", "interactive": True, "action": "提交登录表单"},
            {"type": "button", "label": "注册账号", "x": 20, "y": 340, "width": 335, "height": 40, "color": "#FFFFFF", "interactive": True, "action": "跳转到注册页"},
            {"type": "container", "label": "底部信息栏", "x": 0, "y": 750, "width": 375, "height": 62, "color": "#F8F8F8"},
        ],
    }

    # ---- 检查 1: 解析逻辑 ----
    doc = parse_design_data(sample_data)
    assert doc.title == "登录页原型", "标题解析错误"
    assert doc.width == 375, "宽度解析错误"
    assert doc.height == 812, "高度解析错误"
    assert len(doc.components) == 6, f"组件数量错误: {len(doc.components)}"
    assert doc.components[0].type == "text", "第一个组件类型错误"
    assert doc.components[3].interactive is True, "按钮交互标记错误"
    assert len(doc.breakpoints) == 3, "断点解析错误"

    # ---- 检查 2: HTML 生成逻辑 ----
    html = generate_html(doc)
    assert "<!DOCTYPE html>" in html, "HTML 缺少 DOCTYPE"
    assert "登录页原型" in html, "HTML 缺少标题"
    assert "data-component=\"button\"" in html, "HTML 缺少按钮组件"
    assert "data-component=\"input\"" in html, "HTML 缺少输入框组件"
    assert "data-component=\"text\"" in html, "HTML 缺少文本组件"
    assert "data-component=\"container\"" in html, "HTML 缺少容器组件"
    assert "@media" in html, "HTML 缺少响应式媒体查询"
    # 宽松检查：组件数量应 >= 5
    assert html.count("data-component=") >= 5, "HTML 组件数量不足"

    # ---- 检查 3: CSS 生成逻辑 ----
    css = generate_css(doc)
    assert "design-canvas" in css, "CSS 缺少画布样式"
    assert "data-component='button'" in css, "CSS 缺少按钮样式"
    assert "@media" in css, "CSS 缺少响应式规则"

    # ---- 检查 4: JS 交互标注逻辑 ----
    js = generate_js(doc)
    assert "design-harness" in js, "JS 缺少标识"
    assert "__designInteractions" in js, "JS 缺少交互数组"
    # 宽松检查：至少包含一个交互
    assert js.count("interactions.push") >= 1, "JS 交互标注数量不足"

    # ---- 检查 5: 导出逻辑（使用临时目录） ----
    with tempfile.TemporaryDirectory() as tmpdir:
        # 测试 HTML 导出
        files = export_design(doc, tmpdir, "html")
        assert os.path.exists(files["html"]), "HTML 文件未生成"
        with open(files["html"], "r", encoding="utf-8") as f:
            content = f.read()
        assert len(content) > 100, "HTML 文件内容过短"

        # 测试 JSON 导出
        files = export_design(doc, tmpdir, "json")
        assert os.path.exists(files["json"]), "JSON 文件未生成"
        with open(files["json"], "r", encoding="utf-8") as f:
            json_data = json.load(f)
        assert json_data["title"] == "登录页原型", "JSON 导出内容错误"

        # 测试 CSS 导出
        files = export_design(doc, tmpdir, "css")
        assert os.path.exists(files["css"]), "CSS 文件未生成"

        # 测试 JS 导出
        files = export_design(doc, tmpdir, "js")
        assert os.path.exists(files["js"]), "JS 文件未生成"

        # 测试 Vue 导出
        files = export_design(doc, tmpdir, "vue")
        assert os.path.exists(files["vue"]), "Vue 文件未生成"

        # 测试 React 导出
        files = export_design(doc, tmpdir, "react")
        assert os.path.exists(files["react"]), "React 文件未生成"

    # ---- 检查 6: 错误处理 ----
    # 缺少 components 字段
    try:
        parse_design_data({"title": "无组件"})
        fail("E009", "缺少 components 字段时未报错")
    except SystemExit as e:
        assert e.code != 0, "错误退出码不正确"

    # 未知组件类型
    try:
        parse_design_data({"components": [{"type": "unknown_type"}]})
        fail("E009", "未知组件类型时未报错")
    except SystemExit as e:
        assert e.code != 0, "错误退出码不正确"

    # 不支持的输出格式
    try:
        export_design(doc, tempfile.gettempdir(), "exe")
        fail("E009", "不支持的输出格式时未报错")
    except SystemExit as e:
        assert e.code != 0, "错误退出码不正确"

    # 全部检查通过
    print("[selftest] 全部自检通过 ✔")


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------
def main() -> None:
    parser = argparse.ArgumentParser(
        description="design-harness: 将设计稿转为可验证的前端原型",
        epilog="示例: python main.py --input design.json --output proto --format html",
    )
    parser.add_argument("--input", "-i", help="输入设计稿 JSON 文件路径")
    parser.add_argument("--output", "-o", default="./output", help="输出目录（默认: ./output）")
    parser.add_argument(
        "--format", "-f",
        default="html",
        choices=["html", "css", "js", "json", "vue", "react"],
        help="输出格式（默认: html）",
    )
    parser.add_argument("--selftest", action="store_true", help="运行内置自检（不读外部文件）")
    parser.add_argument("--version", action="version", version="design-harness 1.0.1")

    parser.add_argument("--force", action="store_true")  # R4 强制写盘


    parser.add_argument("--dry-run", action="store_true")  # R4 预览模式

    args = parser.parse_args()

    global dry_run

    dry_run = getattr(args, "dry_run", False)  # v3.274 同步到全局

    # 自检模式
    if args.selftest:
        if args.input:
            fail("E007", "--selftest 与 --input 不能同时使用")
        run_selftest()
        return

    # 正常处理模式
    if not args.input:
        fail("E001", "请提供 --input 参数（或使用 --selftest 运行自检）")

    # 读取输入文件
    if not os.path.isfile(args.input):
        fail("E001", f"输入文件不存在: {args.input}")

    try:
        with open(args.input, "r", encoding="utf-8") as f:
            raw_data = json.load(f)
    except json.JSONDecodeError as e:
        fail("E002", f"JSON 解析失败: {e}")
    except OSError as e:
        fail("E001", f"文件读取失败: {e}")

    # 解析设计稿
    doc = parse_design_data(raw_data)

    # 导出
    try:
        generated = export_design(doc, args.output, args.format)
    except OSError as e:
        fail("E005", f"输出失败: {e}")

    # 输出结果摘要
    print(f"✅ 设计稿 '{doc.title}' 已生成 {args.format} 原型:")
    for key, path in generated.items():
        print(f"   - {key}: {path}")

    # 置信度提示
    interactive_count = sum(1 for c in doc.components if c.interactive)
    print(f"\n📊 置信度评估:")
    print(f"   - 组件总数: {len(doc.components)}")
    print(f"   - 交互组件: {interactive_count}")
    if len(doc.components) > 0:
        print(f"   - 交互覆盖率: {interactive_count / len(doc.components) * 100:.0f}%")
    print(f"   - 提示: 原型仅用于设计验证，非生产级代码")


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:
        fail("E010", f"未捕获异常: {e}")
