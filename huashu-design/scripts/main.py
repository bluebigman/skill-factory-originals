#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py — 画术设计（huashu-design）核心逻辑实现

功能概述：
    根据功能规格实现高保真原型/幻灯片/交互动画的 HTML 生成核心逻辑。
    本脚本仅依赖 Python 标准库，提供命令行接口与离线自检功能。

用法示例：
    python scripts/main.py --selftest
    python scripts/main.py --input data.json --output prototype.html
"""

import argparse
import json
import os
import re
import sys
import time
from html import escape
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timezone


# ---------------------------------------------------------------------------
# 常量定义
# ---------------------------------------------------------------------------
ERROR_CODES = {
    "E001": "参数错误：缺少必要的命令行参数或参数值非法",
    "E002": "文件错误：输入文件不存在或无法读取",
    "E003": "文件错误：输出目录不存在或无法写入",
    "E004": "数据错误：输入 JSON 格式不正确",
    "E005": "数据错误：缺少必需的字段（如 title 或 slides）",
    "E006": "数据错误：字段类型不符合预期",
    "E007": "数据错误：数值超出允许范围",
    "E008": "逻辑错误：内部状态不一致",
    "E009": "逻辑错误：HTML 生成失败",
    "E010": "未知错误：未预期的异常",
}

DEFAULT_VIEWPORT_WIDTH = 1440
DEFAULT_VIEWPORT_HEIGHT = 900
RESPONSIVE_BREAKPOINT_768 = 768
RESPONSIVE_BREAKPOINT_480 = 480

# 设计哲学常量（用于自动应用视觉风格）
DESIGN_PHILOSOPHY_CSS = """
/* 设计哲学自动应用 */
.hs-card {
    border-radius: 12px;
    box-shadow: 0 4px 20px rgba(0,0,0,0.08);
    transition: transform 0.3s ease, box-shadow 0.3s ease;
}
.hs-card:hover {
    transform: translateY(-4px);
    box-shadow: 0 8px 30px rgba(0,0,0,0.12);
}
.hs-gradient-text {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}
.hs-slide {
    min-height: 100vh;
    display: flex;
    flex-direction: column;
    justify-content: center;
    padding: 4rem 2rem;
    scroll-snap-align: start;
}
.hs-fade-in {
    opacity: 0;
    transform: translateY(20px);
    transition: opacity 0.6s ease, transform 0.6s ease;
}
.hs-fade-in.hs-visible {
    opacity: 1;
    transform: translateY(0);
}
@media (max-width: 768px) {
    .hs-slide { padding: 2rem 1rem; }
}
@media (max-width: 480px) {
    .hs-slide { padding: 1rem 0.5rem; }
}
"""


# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------
def _fail(error_code: str, message: Optional[str] = None) -> None:
    """抛出带错误码的异常。"""
    default_msg = ERROR_CODES.get(error_code, ERROR_CODES["E010"])
    if message:
        raise RuntimeError(f"[{error_code}] {default_msg} — {message}")
    raise RuntimeError(f"[{error_code}] {default_msg}")


def _safe_text(value: Any) -> str:
    """安全转换为文本并转义 HTML 特殊字符。"""
    if value is None:
        return ""
    return escape(str(value))


def _validate_slide_structure(slide: Any, index: int) -> None:
    """验证单个幻灯片的数据结构。"""
    if not isinstance(slide, dict):
        _fail("E006", f"slides[{index}] 应为对象")
    if "title" not in slide:
        _fail("E005", f"slides[{index}] 缺少 title 字段")
    if not isinstance(slide["title"], str):
        _fail("E006", f"slides[{index}].title 应为字符串")


def _validate_input_data(data: Any) -> Dict[str, Any]:
    """验证并规范化输入数据。"""
    if not isinstance(data, dict):
        _fail("E006", "输入数据应为 JSON 对象")
    if "title" not in data:
        _fail("E005", "缺少 title 字段")
    if not isinstance(data["title"], str):
        _fail("E006", "title 应为字符串")
    if "slides" not in data:
        _fail("E005", "缺少 slides 字段")
    if not isinstance(data["slides"], list) or len(data["slides"]) == 0:
        _fail("E006", "slides 应为非空数组")
    for i, slide in enumerate(data["slides"]):
        _validate_slide_structure(slide, i)
    return data


def _build_css(extra_css: str = "") -> str:
    """构建完整 CSS 样式。"""
    base_css = """
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, "PingFang SC", "Microsoft YaHei", sans-serif;
        line-height: 1.6;
        color: #1a1a2e;
        background: #ffffff;
    }
    .hs-container {
        max-width: 1200px;
        margin: 0 auto;
        padding: 0 24px;
    }
    .hs-slide-title {
        font-size: 2.5rem;
        font-weight: 700;
        margin-bottom: 1.5rem;
        letter-spacing: -0.02em;
    }
    .hs-slide-content {
        font-size: 1.125rem;
        color: #4a4a6a;
    }
    .hs-slide-content p { margin-bottom: 1rem; }
    .hs-slide-content ul, .hs-slide-content ol { margin-left: 1.5rem; margin-bottom: 1rem; }
    .hs-slide-content li { margin-bottom: 0.5rem; }
    .hs-navigation {
        position: fixed;
        bottom: 24px;
        right: 24px;
        display: flex;
        gap: 12px;
        z-index: 1000;
    }
    .hs-nav-btn {
        padding: 10px 20px;
        border: none;
        border-radius: 8px;
        background: #667eea;
        color: white;
        cursor: pointer;
        font-size: 14px;
        transition: background 0.2s ease;
    }
    .hs-nav-btn:hover { background: #5a67d8; }
    .hs-nav-btn:disabled { background: #cbd5e0; cursor: not-allowed; }
    .hs-progress {
        position: fixed;
        top: 0;
        left: 0;
        height: 4px;
        background: linear-gradient(90deg, #667eea, #764ba2);
        transition: width 0.3s ease;
        z-index: 1001;
    }
    .hs-slide-container {
        scroll-snap-type: y mandatory;
        overflow-y: auto;
        height: 100vh;
    }
    """
    return base_css + DESIGN_PHILOSOPHY_CSS + extra_css


def _build_js(transition: str = "slide", autoplay: bool = False) -> str:
    """构建交互 JavaScript 脚本。"""
    # 转义配置值用于 JS 字符串
    transition_js = json.dumps(transition)
    autoplay_js = "true" if autoplay else "false"
    
    return f"""
    (function() {{
        // 配置
        const config = {{
            transition: {transition_js},
            autoplay: {autoplay_js},
            autoplayInterval: 5000
        }};

        // 幻灯片导航逻辑
        const slides = document.querySelectorAll('.hs-slide');
        const prevBtn = document.getElementById('hs-prev');
        const nextBtn = document.getElementById('hs-next');
        const progress = document.getElementById('hs-progress');
        let currentSlide = 0;
        let autoplayTimer = null;

        function showSlide(index) {{
            if (index < 0 || index >= slides.length) return;
            
            // 根据过渡类型应用不同效果
            if (config.transition === 'fade') {{
                slides.forEach((slide, i) => {{
                    slide.style.display = i === index ? 'flex' : 'none';
                    slide.style.opacity = i === index ? '1' : '0';
                    slide.style.transition = 'opacity 0.5s ease';
                }});
            }} else if (config.transition === 'slide') {{
                slides.forEach((slide, i) => {{
                    slide.style.display = i === index ? 'flex' : 'none';
                    slide.style.transform = i === index ? 'translateX(0)' : 'translateX(100%)';
                    slide.style.transition = 'transform 0.5s ease';
                }});
            }} else {{
                // 默认直接切换
                slides.forEach((slide, i) => {{
                    slide.style.display = i === index ? 'flex' : 'none';
                }});
            }}
            
            currentSlide = index;
            if (prevBtn) prevBtn.disabled = currentSlide === 0;
            if (nextBtn) nextBtn.disabled = currentSlide === slides.length - 1;
            if (progress) {{
                progress.style.width = ((currentSlide + 1) / slides.length * 100) + '%';
            }}
            // 触发渐入动画
            const activeSlide = slides[currentSlide];
            if (activeSlide) {{
                const fadeEls = activeSlide.querySelectorAll('.hs-fade-in');
                fadeEls.forEach((el, i) => {{
                    setTimeout(() => el.classList.add('hs-visible'), i * 100);
                }});
            }}
        }}

        function nextSlide() {{
            if (currentSlide < slides.length - 1) {{
                showSlide(currentSlide + 1);
            }}
        }}

        function prevSlide() {{
            if (currentSlide > 0) {{
                showSlide(currentSlide - 1);
            }}
        }}

        // 自动播放
        function startAutoplay() {{
            if (config.autoplay && slides.length > 1) {{
                autoplayTimer = setInterval(nextSlide, config.autoplayInterval);
            }}
        }}

        function stopAutoplay() {{
            if (autoplayTimer) {{
                clearInterval(autoplayTimer);
                autoplayTimer = null;
            }}
        }}

        if (prevBtn) prevBtn.addEventListener('click', () => {{
            prevSlide();
            stopAutoplay();
        }});
        if (nextBtn) nextBtn.addEventListener('click', () => {{
            nextSlide();
            stopAutoplay();
        }});

        // 键盘导航
        document.addEventListener('keydown', (e) => {{
            if (e.key === 'ArrowRight' || e.key === 'PageDown') {{
                nextSlide();
                stopAutoplay();
            }} else if (e.key === 'ArrowLeft' || e.key === 'PageUp') {{
                prevSlide();
                stopAutoplay();
            }}
        }});

        // 滚动渐入检测
        const observer = new IntersectionObserver((entries) => {{
            entries.forEach(entry => {{
                if (entry.isIntersecting) {{
                    entry.target.classList.add('hs-visible');
                }}
            }});
        }}, {{ threshold: 0.1 }});

        document.querySelectorAll('.hs-fade-in').forEach(el => observer.observe(el));

        // 初始化
        showSlide(0);
        startAutoplay();
    }})();
    """


def _render_slide(slide: Dict[str, Any], index: int) -> str:
    """渲染单个幻灯片 HTML。"""
    title = _safe_text(slide.get("title", ""))
    content = slide.get("content", "")
    
    # 处理内容：支持字符串或列表
    content_html = ""
    if isinstance(content, str):
        # 简单 Markdown 风格转换
        paragraphs = content.split("\n\n")
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            if para.startswith("- ") or para.startswith("* "):
                items = [p.strip()[2:] for p in para.split("\n") if p.strip().startswith(("- ", "* "))]
                list_html = "".join(f"<li>{_safe_text(item)}</li>" for item in items)
                content_html += f"<ul>{list_html}</ul>"
            elif para.startswith("# "):
                content_html += f"<h2>{_safe_text(para[2:])}</h2>"
            else:
                content_html += f"<p>{_safe_text(para)}</p>"
    elif isinstance(content, list):
        for item in content:
            if isinstance(item, str):
                content_html += f"<p>{_safe_text(item)}</p>"
            elif isinstance(item, dict) and "type" in item:
                item_type = item["type"]
                if item_type == "text":
                    content_html += f"<p>{_safe_text(item.get('text', ''))}</p>"
                elif item_type == "list":
                    items = item.get("items", [])
                    list_html = "".join(f"<li>{_safe_text(i)}</li>" for i in items)
                    content_html += f"<ul>{list_html}</ul>"
                elif item_type == "quote":
                    content_html += f"<blockquote>{_safe_text(item.get('text', ''))}</blockquote>"
                elif item_type == "code":
                    lang = _safe_text(item.get("language", ""))
                    code = _safe_text(item.get("code", ""))
                    content_html += f"<pre><code class='language-{lang}'>{code}</code></pre>"
    
    # 添加额外卡片内容
    cards = slide.get("cards", [])
    if isinstance(cards, list) and cards:
        cards_html = '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:24px;margin-top:24px;">'
        for card in cards:
            if isinstance(card, dict):
                card_title = _safe_text(card.get("title", ""))
                card_desc = _safe_text(card.get("description", ""))
                cards_html += f"""
                <div class="hs-card" style="padding:24px;background:#f8f9fa;border:1px solid #e9ecef;">
                    <h3 style="margin-bottom:12px;font-size:1.25rem;">{card_title}</h3>
                    <p style="color:#6c757d;font-size:0.95rem;">{card_desc}</p>
                </div>"""
        cards_html += "</div>"
        content_html += cards_html

    return f"""
    <section class="hs-slide hs-fade-in" id="slide-{index + 1}" style="display:{'flex' if index == 0 else 'none'};">
        <div class="hs-container">
            <h1 class="hs-slide-title">{title}</h1>
            <div class="hs-slide-content">{content_html}</div>
        </div>
    </section>"""


def generate_html(data: Dict[str, Any], transition: str = "slide", autoplay: bool = False) -> str:
    """根据输入数据生成完整 HTML 文档。"""
    try:
        validated = _validate_input_data(data)
        title = _safe_text(validated["title"])
        slides = validated["slides"]

        # 构建幻灯片 HTML
        slides_html = "\n".join(_render_slide(slide, i) for i, slide in enumerate(slides))

        # 构建完整页面
        html_doc = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
    {_build_css()}
    </style>
</head>
<body>
    <div class="hs-progress" id="hs-progress"></div>
    <main class="hs-slide-container">
        {slides_html}
    </main>
    <nav class="hs-navigation">
        <button class="hs-nav-btn" id="hs-prev" disabled>← 上一页</button>
        <button class="hs-nav-btn" id="hs-next">下一页 →</button>
    </nav>
    <script>
    {_build_js(transition, autoplay)}
    </script>
</body>
</html>"""
        return html_doc
    except RuntimeError:
        raise
    except Exception as e:
        _fail("E009", str(e))


def _load_json_file(filepath: str) -> Dict[str, Any]:
    """从文件加载并验证 JSON 数据，带重试逻辑。"""
    if not os.path.isfile(filepath):
        _fail("E002", f"文件不存在: {filepath}")
    
    max_retries = 3
    base_delay = 0.5
    last_error = None
    
    for attempt in range(max_retries):
        try:
            with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                data = json.load(f)
            return _validate_input_data(data)
        except json.JSONDecodeError as e:
            _fail("E004", f"JSON 解析失败: {e}")
        except (IOError, OSError) as e:
            last_error = e
            if attempt < max_retries - 1:
                time
