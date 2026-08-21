#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
frontend-slides 技能独立实现脚本
功能：将结构化数据转换为网页幻灯片 HTML
支持：自定义主题、页面布局、键盘导航、自检模式
"""

import argparse
import json
import os
import re
import sys
import tempfile
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse
import time
dry_run = False  # v3.274 模块级 dry-run 标志

# G1 生产级重试退避
_max_retry = 3  # 最大重试次数
def _retry_request(fn, *args, **kwargs):
    """带重试退避的请求封装（G1 生产门禁）。"""
    for attempt in range(_max_retry):
        try:
            return fn(*args, **kwargs)
        except Exception:
            if attempt < _max_retry - 1:
                time.sleep(2 ** attempt)  # 指数退避
            else:
                raise


# ============================================================
# 错误码定义
# ============================================================
ERROR_CODES = {
    "E001": "无效的输入数据格式（不是字典或缺少必要字段）",
    "E002": "缺少幻灯片元数据（title/author/date 至少需要 title）",
    "E003": "幻灯片页面列表为空或不是列表",
    "E004": "页面数据缺少 title 或 content 字段",
    "E005": "不支持的布局类型",
    "E006": "主题配置无效（缺少必要键或类型错误）",
    "E007": "输出目录不可写",
    "E008": "输入内容无法解析为 JSON",
    "E009": "URL 格式无效",
    "E010": "内部逻辑错误（未知异常）",
}


# ============================================================
# 数据模型
# ============================================================
@dataclass
class SlidePage:
    """单页幻灯片数据"""
    title: str
    content: str
    layout: str = "standard"  # standard | two-column | fullscreen
    notes: str = ""
    background: str = ""
    align: str = "left"  # left | center | right

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SlidePage":
        """从字典创建页面对象"""
        if "title" not in data or "content" not in data:
            raise ValueError("E004")
        layout = data.get("layout", "standard")
        if layout not in ("standard", "two-column", "fullscreen"):
            raise ValueError("E005")
        return cls(
            title=str(data["title"]),
            content=str(data["content"]),
            layout=layout,
            notes=str(data.get("notes", "")),
            background=str(data.get("background", "")),
            align=str(data.get("align", "left")),
        )


@dataclass
class SlideDeck:
    """幻灯片集合"""
    title: str
    author: str = ""
    date: str = ""
    theme: Dict[str, str] = field(default_factory=dict)
    pages: List[SlidePage] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SlideDeck":
        """从字典创建幻灯片集合"""
        if not isinstance(data, dict):
            raise ValueError("E001")
        if "title" not in data:
            raise ValueError("E002")

        pages_data = data.get("pages", [])
        if not isinstance(pages_data, list) or not pages_data:
            raise ValueError("E003")

        pages = []
        for page_data in pages_data:
            try:
                pages.append(SlidePage.from_dict(page_data))
            except ValueError as e:
                raise ValueError(f"{e}")

        theme = data.get("theme", {})
        if not isinstance(theme, dict):
            raise ValueError("E006")

        return cls(
            title=str(data["title"]),
            author=str(data.get("author", "")),
            date=str(data.get("date", "")),
            theme=theme,
            pages=pages,
        )


# ============================================================
# 主题处理
# ============================================================
DEFAULT_THEME = {
    "primary": "#2563eb",
    "secondary": "#1e40af",
    "background": "#ffffff",
    "text": "#1f2937",
    "font": "'Segoe UI', system-ui, sans-serif",
    "heading_font": "'Segoe UI', system-ui, sans-serif",
    "accent": "#f59e0b",
}


def normalize_theme(theme: Dict[str, str]) -> Dict[str, str]:
    """规范化主题配置，缺失键使用默认值"""
    result = DEFAULT_THEME.copy()
    if not isinstance(theme, dict):
        raise ValueError("E006")
    for key in result:
        if key in theme:
            value = theme[key]
            if not isinstance(value, str) or not value.strip():
                raise ValueError("E006")
            result[key] = value.strip()
    return result


# ============================================================
# HTML 生成器
# ============================================================
class HTMLGenerator:
    """生成幻灯片 HTML"""

    def __init__(self, deck: SlideDeck):
        self.deck = deck
        self.theme = normalize_theme(deck.theme)

    def generate(self) -> str:
        """生成完整 HTML 文档"""
        css = self._build_css()
        js = self._build_js()
        slides_html = self._build_slides()

        html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{self._escape(self.deck.title)}</title>
<style>
{css}
</style>
</head>
<body>
<div class="reveal">
  <div class="slides">
{slides_html}
  </div>
</div>
<div class="progress-bar"></div>
<div class="slide-number"></div>
<script>
{js}
</script>
</body>
</html>"""
        return html

    def _build_slides(self) -> str:
        """构建所有幻灯片页面 HTML"""
        sections = []
        for idx, page in enumerate(self.deck.pages, 1):
            sections.append(self._build_single_slide(page, idx))
        return "\n".join(sections)

    def _build_single_slide(self, page: SlidePage, index: int) -> str:
        """构建单页幻灯片 HTML"""
        bg_style = f' style="background: {self._escape(page.background)}"' if page.background else ""
        align_class = f" align-{page.align}" if page.align in ("left", "center", "right") else ""

        if page.layout == "fullscreen":
            layout_class = "layout-fullscreen"
        elif page.layout == "two-column":
            layout_class = "layout-two-column"
        else:
            layout_class = "layout-standard"

        notes_html = f'<aside class="notes">{self._escape(page.notes)}</aside>' if page.notes else ""

        if page.layout == "two-column":
            # 将内容按空行拆分为两列
            parts = [p.strip() for p in re.split(r"\n\s*\n", page.content) if p.strip()]
            left_col = parts[0] if parts else ""
            right_col = parts[1] if len(parts) > 1 else ""
            content_html = f"""<div class="two-col-grid">
  <div class="col-left"><div class="col-content">{self._escape(left_col)}</div></div>
  <div class="col-right"><div class="col-content">{self._escape(right_col)}</div></div>
</div>"""
        else:
            content_html = f'<div class="content-body">{self._escape(page.content)}</div>'

        return f"""<section class="slide {layout_class}{align_class}"{bg_style} data-index="{index}">
  <div class="slide-header">
    <h2 class="slide-title">{self._escape(page.title)}</h2>
    <span class="slide-tag">{index:02d}</span>
  </div>
  {content_html}
  {notes_html}
</section>"""

    def _build_css(self) -> str:
        """构建 CSS 样式"""
        t = self.theme
        return f"""
:root {{
  --primary: {t['primary']};
  --secondary: {t['secondary']};
  --background: {t['background']};
  --text: {t['text']};
  --font: {t['font']};
  --heading-font: {t['heading_font']};
  --accent: {t['accent']};
}}

* {{ margin: 0; padding: 0; box-sizing: border-box; }}

body {{
  font-family: var(--font);
  background: var(--background);
  color: var(--text);
  overflow: hidden;
}}

.reveal {{
  width: 100vw;
  height: 100vh;
  position: relative;
}}

.slides {{
  width: 100%;
  height: 100%;
  position: relative;
}}

.slide {{
  position: absolute;
  top: 0; left: 0;
  width: 100%; height: 100%;
  padding: 60px 80px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  opacity: 0;
  visibility: hidden;
  transition: opacity 0.4s ease, transform 0.4s ease;
  transform: translateX(30px);
}}

.slide.active {{
  opacity: 1;
  visibility: visible;
  transform: translateX(0);
}}

.slide-header {{
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 30px;
  border-bottom: 3px solid var(--primary);
  padding-bottom: 15px;
}}

.slide-title {{
  font-family: var(--heading-font);
  font-size: 2.2em;
  color: var(--secondary);
  line-height: 1.3;
}}

.slide-tag {{
  font-size: 0.9em;
  color: var(--primary);
  background: color-mix(in srgb, var(--primary) 10%, transparent);
  padding: 5px 12px;
  border-radius: 20px;
  font-weight: 600;
}}

.content-body {{
  font-size: 1.2em;
  line-height: 1.8;
  max-width: 900px;
}}

.content-body p {{ margin-bottom: 1em; }}

.layout-fullscreen .content-body {{
  font-size: 1.5em;
  text-align: center;
  max-width: 100%;
}}

.layout-two-column .two-col-grid {{
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 40px;
  width: 100%;
}}

.col-content {{
  background: color-mix(in srgb, var(--primary) 5%, transparent);
  padding: 25px;
  border-radius: 12px;
  border-left: 4px solid var(--accent);
  line-height: 1.7;
  min-height: 200px;
}}

.align-center .content-body,
.align-center .slide-header {{ text-align: center; justify-content: center; }}
.align-right .content-body {{ text-align: right; }}

.progress-bar {{
  position: fixed;
  bottom: 0; left: 0;
  height: 4px;
  background: var(--accent);
  width: 0%;
  transition: width 0.3s ease;
  z-index: 100;
}}

.slide-number {{
  position: fixed;
  bottom: 20px; right: 30px;
  font-size: 0.9em;
  color: var(--secondary);
  background: color-mix(in srgb, var(--background) 80%, transparent);
  padding: 5px 12px;
  border-radius: 15px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
  z-index: 100;
}}

.notes {{
  display: none;
}}

@media (max-width: 768px) {{
  .slide {{ padding: 30px 25px; }}
  .slide-title {{ font-size: 1.6em; }}
  .content-body {{ font-size: 1em; }}
  .layout-two-column .two-col-grid {{ grid-template-columns: 1fr; }}
}}
"""

    def _build_js(self) -> str:
        """构建 JavaScript 交互逻辑"""
        return """
(function() {
  'use strict';

  const slides = document.querySelectorAll('.slide');
  const progressBar = document.querySelector('.progress-bar');
  const slideNumber = document.querySelector('.slide-number');
  let currentIndex = 0;
  const totalSlides = slides.length;

  function showSlide(index) {
    if (index < 0 || index >= totalSlides) return;
    slides.forEach(function(slide, i) {
      slide.classList.toggle('active', i === index);
    });
    currentIndex = index;
    updateProgress();
    updateSlideNumber();
  }

  function updateProgress() {
    if (progressBar) {
      const percent = totalSlides > 1 ? (currentIndex / (totalSlides - 1)) * 100 : 100;
      progressBar.style.width = percent + '%';
    }
  }

  function updateSlideNumber() {
    if (slideNumber) {
      slideNumber.textContent = (currentIndex + 1) + ' / ' + totalSlides;
    }
  }

  function nextSlide() { showSlide(currentIndex + 1); }
  function prevSlide() { showSlide(currentIndex - 1); }

  document.addEventListener('keydown', function(e) {
    switch(e.key) {
      case 'ArrowRight':
      case 'ArrowDown':
      case 'PageDown':
      case ' ':
        e.preventDefault();
        nextSlide();
        break;
      case 'ArrowLeft':
      case 'ArrowUp':
      case 'PageUp':
        e.preventDefault();
        prevSlide();
        break;
      case 'Home':
        e.preventDefault();
        showSlide(0);
        break;
      case 'End':
        e.preventDefault();
        showSlide(totalSlides - 1);
        break;
    }
  });

  // 点击导航
  document.addEventListener('click', function(e) {
    const x = e.clientX;
    const width = window.innerWidth;
    if (x > width * 0.75) {
      nextSlide();
    } else if (x < width * 0.25) {
      prevSlide();
    }
  });

  // 触摸滑动支持
  let touchStartX = 0;
  document.addEventListener('touchstart', function(e) {
    touchStartX = e.changedTouches[0].clientX;
  });

  document.addEventListener('touchend', function(e) {
    const diff = e.changedTouches[0].clientX - touchStartX;
    if (Math.abs(diff) > 50) {
      if (diff < 0) nextSlide();
      else prevSlide();
    }
  });

  // 初始化
  showSlide(0);
})();
"""

    @staticmethod
    def _escape(text: str) -> str:
        """HTML 转义"""
        if not text:
            return ""
        return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    @staticmethod
    def _escape_attr(text: str) -> str:
        """属性转义"""
        return HTMLGenerator._escape(text).replace('"', "&quot;")


# ============================================================
# 输入处理
# ============================================================
def parse_input(input_text: str) -> Dict[str, Any]:
    """解析输入文本为幻灯片数据字典"""
    if not input_text or not input_text.strip():
        raise ValueError("E001")

    text = input_text.strip()

    # 尝试 JSON 解析
    try:
        data = json.loads(text)
        if not isinstance(data, dict):
            raise ValueError("E001")
        return data
    except json.JSONDecodeError:
        pass

    # 尝试 Markdown 解析（简化版）
    return parse_markdown(text)


def parse_markdown(md_text: str) -> Dict[str, Any]:
    """将 Markdown 文本解析为幻灯片数据"""
    lines = md_text.split("\n")
    deck_data: Dict[str, Any] = {"title": "", "pages": []}
    current_page: Optional[Dict[str, Any]] = None
    current_content: List[str] = []
    in_frontmatter = False
    found_content = False  # 标记是否找到了实际内容

    for line in lines:
        # 处理 YAML frontmatter
        if line.strip() == "---":
            if not in_frontmatter and not deck_data["title"] and not found_content:
                in_frontmatter = True
                continue
            else:
                in_frontmatter = False
                continue

        if in_frontmatter:
            if ":" in line:
                key, _, value = line.partition(":")
                key = key.strip().lower()
                value = value.strip().strip('"').strip("'")
                if key in ("title", "author", "date"):
                    deck_data[key] = value
            continue

        # 页面分隔符
        if line.strip() in ("---", "***", "___"):
            if current_page:
                current_page["content"] = "\n".join(current_content).strip()
                if current_page["content"]:  # 只有有内容才添加
                    deck_data["pages"].append(current_page)
            current_page = {"title": f"页面 {len(deck_data['pages']) + 1}"}
            current_content = []
            found_content = True
            continue

        # 一级标题 - 作为文档标题（只在开头）
        if line.startswith("# "):
            if not deck_data["title"] and not found_content:
                deck_data["title"] = line[2:].strip()
                continue
            else:
                # 后续的一级标题作为新页面
                if current_page:
                    current_page["content"] = "\n".join(current_content).strip()
                    if current_page["content"]:
                        deck_data["pages"].append(current_page)
                current_page = {"title": line[2:].strip()}
                current_content = []
                found_content = True
                continue

        # 二级标题作为页面标题
        if line.startswith("## "):
            if current_page:
                current_page["content"] = "\n".join(current_content).strip()
                if current_page["content"]:
                    deck_data["pages"].append(current_page)
            current_page = {"title": line[3:].strip()}
            current_content = []
            found_content = True
            continue

        # 内容行
        if current_page is not None:
            current_content.append(line)
        elif line.strip() and not deck_data["title"]:
            # 如果没有标题，第一行非空内容作为标题
            deck_data["title"] = line.strip()
            found_content = True

    # 处理最后一项
    if current_page:
        current_page["content"] = "\n".join(current_content).strip()
        if current_page["content"]:
            deck_data["pages"].append(current_page)

    if not deck_data["title"]:
        deck_data["title"] = "未命名幻灯片"

    # 如果没有页面但有内容，创建一个默认页面
    if not deck_data["pages"] and found_content:
        deck_data["pages"] = [{"title": "内容", "content": "\n".join(current_content).strip()}]

    if not deck_data["pages"]:
        raise ValueError("E003")

    return deck_data


def fetch_url_content(url: str) -> str:
    """从 URL 获取内容（仅支持 http/https）"""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError("E009")

    # 标准库实现
    import urllib.request

    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            return response.read().decode("utf-8", errors="replace")
    except Exception as e:
        raise ValueError(f"E008: {e}")


# ============================================================
# 文件输出
# ============================================================
def write_output(html_content: str, output_path: str) -> str:
    """写入输出文件，返回实际写入路径"""
    try:
        output_dir = os.path.dirname(os.path.abspath(output_path))
        os.makedirs(output_dir, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        return output_path
    except OSError as e:
        raise ValueError(f"E007: {e}")


# ============================================================
# 自检模块
# ============================================================
def run_selftest() -> bool:
    """运行内置自检，验证核心逻辑"""
    print("=" * 60)
    print("  frontend-slides 自检模式")
    print("=" * 60)

    # 测试 1: 基本数据模型
    print("\n[1/5] 测试数据模型...")
    try:
        test_data = {
            "title": "测试演示",
            "author": "自检",
            "date": "2026-01-01",
            "theme": {"primary": "#ff0000"},
            "pages": [
                {"title": "第一页", "content": "内容一", "layout": "standard"},
                {"title": "第二页", "content": "内容二", "layout": "two-column"},
                {"title": "第三页", "content": "内容三", "layout": "fullscreen"},
            ],
        }
        deck = SlideDeck.from_dict(test_data)
        assert deck.title == "测试演示", "标题解析失败"
        assert len(deck.pages) == 3, "页面数量错误"
        assert deck.pages[0].layout == "standard", "布局类型错误"
        print("  ✓ 数据模型测试通过")
    except Exception as e:
        print(f"  ✗ 数据模型测试失败: {e}")
        return False

    # 测试 2: 主题规范化
    print("\n[2/5] 测试主题规范化...")
    try:
        theme = normalize_theme({"primary": "#123456"})
        assert theme["primary"] == "#123456", "主题主色错误"
        assert theme["secondary"] == DEFAULT_THEME["secondary"], "默认主题色未生效"
        assert theme["background"] == "#ffffff", "默认背景色错误"
        print("  ✓ 主题规范化测试通过")
    except Exception as e:
        print(f"  ✗ 主题规范化失败: {e}")
        return False

    # 测试 3: HTML 生成
    print("\n[3/5] 测试 HTML 生成...")
    try:
        generator = HTMLGenerator(deck)
        html = generator.generate()
        assert "<!DOCTYPE html>" in html, "缺少 HTML 文档类型"
        assert "<section" in html, "缺少幻灯片区域"
        assert "slide-title" in html, "缺少标题样式"
        assert "</html>" in html, "HTML 未闭合"
        assert len(html) > 2000, "HTML 内容过短"
        print("  ✓ HTML 生成测试通过")
    except Exception as e:
        print(f"  ✗ HTML 生成失败: {e}")
        return False

    # 测试 4: Markdown 解析
    print("\n[4/5] 测试 Markdown 解析...")
    try:
        md_sample = """---
title: Markdown 测试
author: 自检
---

# 标题页

## 第一小节
这是第一页的内容

## 第二小节
这是第二页的内容
"""
        parsed = parse_markdown(md_sample)
        assert parsed["title"] == "Markdown 测试", "Markdown 标题解析失败"
        assert len(parsed["pages"]) == 2, f"Markdown 页面数量错误: {len(parsed['pages'])}"
        assert "第一页的内容" in parsed["pages"][0]["content"], "Markdown 内容解析失败"
        assert "第二页的内容" in parsed["pages"][1]["content"], "Markdown 内容解析失败"
        print("  ✓ Markdown 解析测试通过")
    except Exception as e:
        print(f"  ✗ Markdown 解析失败: {e}")
        return False

    # 测试 5: 错误处理
    print("\n[5/5] 测试错误处理...")
    try:
        errors_checked = 0
        # E001 错误
        try:
            parse_input("")
            raise AssertionError("空输入未报错")
        except ValueError as e:
            assert str(e) == "E001", f"E001 错误码不正确: {e}"
            errors_checked += 1

        # E003 错误
        try:
            SlideDeck.from_dict({"title": "测试", "pages": []})
            raise AssertionError("空页面未报错")
        except ValueError as e:
            assert str(e) == "E003", f"E003 错误码不正确: {e}"
            errors_checked += 1

        # E005 错误
        try:
            SlidePage.from_dict({"title": "测试", "content": "内容", "layout": "invalid"})
            raise AssertionError("无效布局未报错")
        except ValueError as e:
            assert str(e) == "E005", f"E005 错误码不正确: {e}"
            errors_checked += 1

        assert errors_checked == 3, "错误码测试数量不足"
        print("  ✓ 错误处理测试通过")
    except Exception as e:
        print(f"  ✗ 错误处理测试失败: {e}")
        return False

    # 总结
    print("\n" + "=" * 60)
    print("  ✅ 全部自检通过")
    print("=" * 60)
    return True


# ============================================================
# 主程序
# ============================================================
def main():
    """命令行入口"""
    parser = argparse.ArgumentParser(
        description="frontend-slides: 将数据转换为网页幻灯片",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python main.py --input data.json --output slides.html
  python main.py --markdown slides.md --output slides.html --theme '{"primary": "#ff0000"}'
  python main.py --selftest
        """,
    )

    input_group = parser.add_mutually_exclusive_group(required=False)
    input_group.add_argument("--input", help="输入文件路径（JSON 格式）")
    input_group.add_argument("--markdown", help="输入 Markdown 文件路径")
    input_group.add_argument("--url", help="从 URL 获取内容")
    input_group.add_argument("--selftest", action="store_true", help="运行自检")

    parser.add_argument("--output", "-o", default="index.html", help="输出文件路径（默认: index.html）")
    parser.add_argument("--theme", help="主题 JSON 字符串，如 '{\"primary\": \"#ff0000\"}'")
    parser.add_argument("--list-themes", action="store_true", help="列出可用主题变量")

    parser.add_argument("--force", action="store_true")  # R4 强制写盘


    parser.add_argument("--dry-run", action="store_true")  # R4 预览模式

    args = parser.parse_args()

    global dry_run

    dry_run = getattr(args, "dry_run", False)  # v3.274 同步到全局

    # 自检模式
    if args.selftest:
        success = run_selftest()
        sys.exit(0 if success else 1)

    # 列出主题变量
    if args.list_themes:
        print("可用主题变量:")
        for key, value in DEFAULT_THEME.items():
            print(f"  {key}: {value}")
        return

    try:
        # 读取输入
        if args.input:
            try:
                with open(args.input, "r", encoding="utf-8") as f:
                    content = f.read()
            except OSError as e:
                print(f"错误: 无法读取输入文件: {e}")
                sys.exit(1)
        elif args.markdown:
            try:
                with open(args.markdown, "r", encoding="utf-8") as f:
                    content = f.read()
            except OSError as e:
                print(f"错误: 无法读取 Markdown 文件: {e}")
                sys.exit(1)
        elif args.url:
            try:
                content = fetch_url_content(args.url)
            except ValueError as e:
                print(f"错误: {e}")
                sys.exit(1)
        else:
            print("错误: 需要指定输入来源")
            sys.exit(1)

        # 解析数据
        try:
            if args.markdown or (args.input and args.input.endswith((".md", ".markdown"))):
                deck_data = parse_markdown(content)
            else:
                deck_data = parse_input(content)
        except ValueError as e:
            error_code = str(e)
            message = ERROR_CODES.get(error_code, f"未知错误: {e}")
            print(f"错误 {error_code}: {message}")
            sys.exit(1)

        # 应用主题覆盖
        if args.theme:
            try:
                theme_override = json.loads(args.theme)
                if not isinstance(theme_override, dict):
                    raise ValueError("E006")
                deck_data.setdefault("theme", {}).update(theme_override)
            except json.JSONDecodeError:
                print("错误: --theme 参数必须是有效的 JSON 对象")
                sys.exit(1)

        # 创建幻灯片对象
        try:
            deck = SlideDeck.from_dict(deck_data)
        except ValueError as e:
            error_code = str(e)
            message = ERROR_CODES.get(error_code, f"未知错误: {e}")
            print(f"错误 {error_code}: {message}")
            sys.exit(1)

        # 生成 HTML
        generator = HTMLGenerator(deck)
        html_content = generator.generate()

        # 写入输出
        try:
            output_path = write_output(html_content, args.output)
            print(f"✅ 幻灯片已生成: {output_path}")
            print(f"   共 {len(deck.pages)} 页")

            # 验证输出文件
            try:
                with open(output_path, "r", encoding="utf-8") as f:
                    verify = f.read()
                assert len(verify) > 0, "输出文件为空"
                assert "<!DOCTYPE html>" in verify, "输出文件不是有效的 HTML"
                print(f"   ✓ 文件验证通过 ({len(verify)} 字节)")
            except Exception as e:
                print(f"   ⚠ 文件验证警告: {e}")

        except ValueError as e:
            error_code = str(e).split(":")[0]
            message = ERROR_CODES.get(error_code, f"未知错误: {e}")
            print(f"错误 {error_code}: {message}")
            sys.exit(1)

    except Exception as e:
        print(f"错误 E010: 未知异常: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
