#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py — 公众号图文流水线技能（独立实现）

仅依据功能规格 clean-room 编写，不复制任何既有代码。
提供素材转文章、排版、配图建议、草稿 HTML 生成。
"""

import argparse
import re
import sys
import html as html_lib

# 错误码定义
ERROR_CODES = {
    "E001": "输入文本为空或长度不足",
    "E002": "输入不是字符串类型",
    "E003": "标题提取失败",
    "E004": "分段处理失败",
    "E005": "HTML 渲染失败",
    "E006": "配图建议生成失败",
    "E007": "草稿生成失败",
    "E008": "非法参数",
    "E009": "内部状态错误",
    "E010": "未知错误",
}


class PipelineError(Exception):
    """业务异常，携带错误码。"""

    def __init__(self, code: str, message: str = ""):
        self.code = code
        self.message = message or ERROR_CODES.get(code, ERROR_CODES["E010"])
        super().__init__(f"[{self.code}] {self.message}")


# ---------- 核心处理函数 ----------

def extract_title(text: str) -> str:
    """从文本中提取标题。

    优先取第一个 Markdown 一级标题（# 开头），否则取第一行非空文本（截断 60 字）。
    """
    if not text or not isinstance(text, str):
        raise PipelineError("E002")

    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if not lines:
        raise PipelineError("E003")

    for ln in lines:
        if ln.startswith("# "):
            return ln[2:].strip()[:60]

    # 无 Markdown 标题时取首行
    first = lines[0]
    # 去掉可能的 Markdown 标记
    first = re.sub(r"^#{1,6}\s+", "", first)
    first = re.sub(r"^[>*\-\s]+", "", first)
    return first[:60] or "未命名文章"


def split_paragraphs(text: str) -> list:
    """将文本按空行分段，并清理每段首尾空白。"""
    if not text or not isinstance(text, str):
        raise PipelineError("E002")

    raw_paras = re.split(r"\n\s*\n", text)
    paras = [p.strip() for p in raw_paras if p.strip()]
    if not paras:
        raise PipelineError("E004")
    return paras


def classify_paragraph(para: str) -> dict:
    """判断段落类型：标题、引用、列表、普通段落。"""
    if not para:
        return {"type": "paragraph", "content": ""}

    # 标题（# 开头）
    m = re.match(r"^(#{1,6})\s+(.*)", para)
    if m:
        level = len(m.group(1))
        return {"type": "heading", "level": level, "content": m.group(2).strip()}

    # 引用（> 开头）
    if para.startswith(">"):
        return {"type": "quote", "content": para.lstrip("> ").strip()}

    # 列表（- 或 * 或 数字. 开头）
    if re.match(r"^[-*]\s+", para) or re.match(r"^\d+[.、]\s+", para):
        items = re.split(r"\n(?=[-*]|\d+[.、])", para)
        items = [re.sub(r"^[-*]\s+", "", it).strip() for it in items]
        return {"type": "list", "items": items}

    return {"type": "paragraph", "content": para}


def build_article_structure(text: str) -> dict:
    """构建文章结构化数据。"""
    title = extract_title(text)
    paras = split_paragraphs(text)
    blocks = [classify_paragraph(p) for p in paras]
    return {"title": title, "blocks": blocks}


def render_html(article: dict) -> str:
    """将结构化文章渲染为公众号可用的 HTML 片段。"""
    try:
        title = html_lib.escape(article.get("title", ""))
        blocks = article.get("blocks", [])

        html_parts = [f"<h1>{title}</h1>"]

        for block in blocks:
            btype = block.get("type")
            if btype == "heading":
                level = min(max(block.get("level", 2), 2), 4)
                content = html_lib.escape(block.get("content", ""))
                html_parts.append(f"<h{level}>{content}</h{level}>")
            elif btype == "quote":
                content = html_lib.escape(block.get("content", ""))
                html_parts.append(f"<blockquote>{content}</blockquote>")
            elif btype == "list":
                items = block.get("items", [])
                lis = "".join(
                    f"<li>{html_lib.escape(it)}</li>" for it in items if it
                )
                html_parts.append(f"<ul>{lis}</ul>")
            else:
                content = html_lib.escape(block.get("content", ""))
                # 简单加粗强调：**文字**
                content = re.sub(
                    r"\*\*(.+?)\*\*",
                    lambda m: f"<strong>{m.group(1)}</strong>",
                    content,
                )
                html_parts.append(f"<p>{content}</p>")

        return "\n".join(html_parts)
    except Exception as exc:
        raise PipelineError("E005", str(exc)) from exc


def suggest_images(article: dict) -> list:
    """根据文章主题生成配图建议（描述 + 尺寸 + 位置）。"""
    try:
        title = article.get("title", "")
        blocks = article.get("blocks", [])

        # 统计段落数和关键词
        para_count = sum(1 for b in blocks if b.get("type") == "paragraph")
        heading_count = sum(1 for b in blocks if b.get("type") == "heading")

        # 简单主题推断
        topic = "通用"
        combined_text = title + " " + " ".join(
            b.get("content", "") for b in blocks if b.get("content")
        )
        if any(k in combined_text for k in ["科技", "AI", "代码", "编程", "互联网"]):
            topic = "科技"
        elif any(k in combined_text for k in ["美食", "菜谱", "餐厅", "烹饪"]):
            topic = "美食"
        elif any(k in combined_text for k in ["旅行", "旅游", "景点", "酒店"]):
            topic = "旅行"
        elif any(k in combined_text for k in ["健康", "运动", "健身", "医疗"]):
            topic = "健康"

        suggestions = [
            {
                "position": "封面图",
                "description": f"与{topic}主题相关的宽幅封面，突出文章核心观点",
                "size": "900x383（公众号封面推荐比例 2.35:1）",
                "style": "简洁大气，色彩明快",
            },
            {
                "position": "标题下方",
                "description": f"呼应标题的{topic}主题插图，增强第一印象",
                "size": "900x500（横幅比例）",
                "style": "与封面风格一致",
            },
        ]

        # 根据段落数量建议中间配图
        if para_count >= 3:
            suggestions.append(
                {
                    "position": "正文中部（约 50% 位置）",
                    "description": f"与{topic}相关的场景图或示意图，缓解阅读疲劳",
                    "size": "900x600（4:3 比例）",
                    "style": "自然真实，避免过度装饰",
                }
            )

        if heading_count >= 3:
            suggestions.append(
                {
                    "position": "结尾处",
                    "description": "总结性配图或引导关注图，强化品牌记忆",
                    "size": "900x400（长条横幅）",
                    "style": "简洁，含品牌元素",
                }
            )

        return suggestions
    except Exception as exc:
        raise PipelineError("E006", str(exc)) from exc


def generate_draft(article: dict) -> dict:
    """生成草稿内容（HTML + 配图建议 + 摘要）。"""
    try:
        html_content = render_html(article)
        images = suggest_images(article)

        # 生成摘要（取正文前 120 字）
        plain_text = " ".join(
            b.get("content", "") for b in article.get("blocks", []) if b.get("content")
        )
        plain_text = re.sub(r"<[^>]+>", "", plain_text)
        summary = plain_text[:120] + ("..." if len(plain_text) > 120 else "")

        return {
            "title": article.get("title", ""),
            "html": html_content,
            "image_suggestions": images,
            "summary": summary,
        }
    except PipelineError:
        raise
    except Exception as exc:
        raise PipelineError("E007", str(exc)) from exc


def process_article(text: str) -> dict:
    """完整流水线：素材 → 文章 → 排版 → 配图 → 草稿。"""
    if not text or not isinstance(text, str):
        raise PipelineError("E002")
    if len(text.strip()) < 200:
        raise PipelineError("E001")

    article = build_article_structure(text)
    draft = generate_draft(article)
    return draft


# ---------- 自测模块 ----------

def run_selftest() -> bool:
    """内置硬编码样例离线自检核心逻辑。"""
    # 构造一个超过 200 字的测试文本
    sample_lines = [
        "# 人工智能与未来生活",
        "",
        "人工智能正在深刻改变我们的日常生活。从智能手机的语音助手到自动驾驶汽车，AI 技术已经渗透到各个领域。",
        "",
        "## 主要应用场景",
        "",
        "> 技术发展速度远超预期，我们需要理性看待。",
        "",
        "- 智能家居：自动化控制灯光、温度和安全系统",
        "- 医疗健康：辅助诊断和药物研发",
        "- 教育领域：个性化学习方案推荐",
        "",
        "**未来展望**：人工智能将继续推动社会进步，但同时也带来伦理和隐私方面的挑战。",
        "",
        "我们需要在技术创新与人文关怀之间找到平衡点，确保技术发展造福全人类。",
        "",
        "各国政府和相关机构应当加强合作，制定合理的规范和标准，引导 AI 技术健康发展。",
        "",
        "同时，公众也需要提高数字素养，更好地理解和应对 AI 带来的变化。",
        "",
        "总之，人工智能是机遇与挑战并存的时代命题。",
    ]
    sample_text = "\n\n".join(sample_lines)

    try:
        # 1. 测试标题提取
        title = extract_title(sample_text)
        assert title and "人工智能" in title, "标题提取失败"

        # 2. 测试分段
        paras = split_paragraphs(sample_text)
        assert len(paras) >= 5, "分段数量过少"

        # 3. 测试结构构建
        article = build_article_structure(sample_text)
        assert article["title"], "文章标题为空"
        assert len(article["blocks"]) >= 5, "文章块数量过少"

        # 4. 测试 HTML 渲染
        html_out = render_html(article)
        assert "<h1>" in html_out, "HTML 缺少一级标题"
        assert "<p>" in html_out, "HTML 缺少段落"
        assert html_out.count("<") > 10, "HTML 标签数量异常"

        # 5. 测试配图建议
        images = suggest_images(article)
        assert len(images) >= 2, "配图建议数量过少"
        for img in images:
            assert img["position"], "配图位置为空"
            assert img["description"], "配图描述为空"
            assert img["size"], "配图尺寸为空"

        # 6. 测试草稿生成
        draft = generate_draft(article)
        assert draft["title"], "草稿标题为空"
        assert draft["html"], "草稿 HTML 为空"
        assert draft["summary"], "草稿摘要为空"
        assert len(draft["image_suggestions"]) >= 2, "草稿配图建议过少"

        # 7. 测试完整流水线
        result = process_article(sample_text)
        assert result["title"], "流水线结果标题为空"
        assert len(result["html"]) > 100, "流水线结果 HTML 过短"
        assert len(result["image_suggestions"]) >= 2, "流水线结果配图过少"

        # 8. 测试错误处理（短文本）
        try:
            process_article("太短了")
            assert False, "短文本应抛出 E001 错误"
        except PipelineError as err:
            assert err.code == "E001", f"错误码应为 E001，实际 {err.code}"

        print("[selftest] 全部核心逻辑自检通过 ✅")
        return True

    except AssertionError as exc:
        print(f"[selftest] 断言失败: {exc} ❌")
        return False
    except PipelineError as exc:
        print(f"[selftest] 业务错误: {exc.code} {exc.message} ❌")
        return False
    except Exception as exc:
        print(f"[selftest] 未知异常: {exc} ❌")
        return False


# ---------- 主入口 ----------

def main() -> int:
    """命令行入口。"""
    parser = argparse.ArgumentParser(
        description="公众号图文流水线：素材转文章、排版、配图建议、草稿生成"
    )
    parser.add_argument(
        "--input",
        "-i",
        type=str,
        help="输入文本文件路径（UTF-8 编码）",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置离线自检",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        help="输出草稿 JSON 文件路径（可选，默认输出到 stdout）",
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        ok = run_selftest()
        return 0 if ok else 1

    # 处理模式
    if not args.input:
        print("错误: 请提供 --input 文件路径或使用 --selftest 自检", file=sys.stderr)
        return 2

    try:
        with open(args.input, "r", encoding="utf-8") as f:
            text = f.read()

        result = process_article(text)

        import json

        output_json = json.dumps(result, ensure_ascii=False, indent=2)

        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(output_json)
            print(f"草稿已写入: {args.output}")
        else:
            print(output_json)

        return 0

    except FileNotFoundError:
        print(f"错误: 文件不存在 - {args.input}", file=sys.stderr)
        return 3
    except PipelineError as exc:
        print(f"处理失败: {exc.code} {exc.message}", file=sys.stderr)
        return 4
    except Exception as exc:
        print(f"未知错误: {exc}", file=sys.stderr)
        return 5


if __name__ == "__main__":
    sys.exit(main())
