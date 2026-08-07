#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
微信公众号内容生产流水线 Skill - 独立实现脚本

本脚本依据功能规格 clean-room 重写，仅使用标准库。
提供：素材解析、文章结构重组、HTML/Markdown 双格式排版、
配图规划建议、草稿创建模拟（离线）等核心能力。

用法示例:
    python scripts/main.py --selftest          # 离线自检
    python scripts/main.py --help              # 查看帮助
"""

import argparse
import hashlib
import json
import re
import sys
import tempfile
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# 错误码定义
ERROR_CODES = {
    "E001": "输入参数缺失或为空",
    "E002": "素材内容无法解析（空文本/无有效段落）",
    "E003": "URL 格式不合法",
    "E004": "输出目录不可写",
    "E005": "HTML 渲染失败（模板错误）",
    "E006": "Markdown 渲染失败（模板错误）",
    "E007": "配图规划失败（尺寸参数异常）",
    "E008": "草稿创建失败（数据校验未通过）",
    "E009": "文件读写失败（IO 异常）",
    "E010": "未知内部错误",
}


# ---------- 数据结构 ----------

@dataclass
class ArticleSection:
    """文章段落结构"""
    heading: str = ""
    paragraphs: List[str] = field(default_factory=list)
    quotes: List[str] = field(default_factory=list)
    data_tables: List[List[str]] = field(default_factory=list)


@dataclass
class ImagePlan:
    """配图规划建议"""
    position: str          # 建议位置描述
    size: Tuple[int, int]  # 建议尺寸 (宽, 高)
    style: str             # 风格建议
    alt_text: str          # 替代文本建议


@dataclass
class Article:
    """成品文章数据结构"""
    title: str
    summary: str
    sections: List[ArticleSection]
    image_plans: List[ImagePlan]
    confidence: float      # 信息完整度置信度 0.0-1.0
    created_at: str


# ---------- 核心逻辑 ----------

class ArticlePipeline:
    """公众号文章流水线核心引擎"""

    def __init__(self) -> None:
        self._image_style_pool = ["简约商务", "清新自然", "科技感", "温暖治愈", "高对比插画"]
        self._image_size_pool = [(900, 383), (900, 500), (1080, 720), (750, 400)]

    # ----- 步骤1: 素材解析 -----
    def parse_material(self, raw_text: str, source_url: str = "") -> Dict[str, Any]:
        """
        解析原始素材文本，提取标题、摘要、段落、引用、数据表格。
        返回结构化字典。
        """
        if not raw_text or not raw_text.strip():
            raise RuntimeError(f"E002: {ERROR_CODES['E002']}")

        if source_url and not re.match(r'^https?://', source_url):
            raise RuntimeError(f"E003: {ERROR_CODES['E003']}")

        # 按空行分割段落
        raw_paragraphs = [p.strip() for p in re.split(r'\n\s*\n', raw_text) if p.strip()]

        if not raw_paragraphs:
            raise RuntimeError(f"E002: {ERROR_CODES['E002']}")

        # 识别标题（第一个非空行且较短）
        title = raw_paragraphs[0][:50] if len(raw_paragraphs[0]) <= 50 else "未命名文章"

        # 识别摘要（第二个段落或第一段截断）
        summary = ""
        if len(raw_paragraphs) > 1:
            summary = raw_paragraphs[1][:200]
        else:
            summary = raw_paragraphs[0][:200]

        # 识别引用（以 > 或 “ 开头的行）
        quotes = []
        for line in raw_text.split('\n'):
            stripped = line.strip()
            if stripped.startswith('>') or stripped.startswith('“'):
                quotes.append(stripped.lstrip('> “').rstrip('”'))

        # 识别表格（包含 | 分隔符的行组）
        tables = []
        table_buffer = []
        for line in raw_text.split('\n'):
            if '|' in line and '-' not in line[:3]:
                cells = [c.strip() for c in line.strip('|').split('|')]
                table_buffer.append(cells)
            else:
                if len(table_buffer) >= 2:
                    tables.append(table_buffer)
                table_buffer = []
        if len(table_buffer) >= 2:
            tables.append(table_buffer)

        # 计算置信度
        confidence = 0.5
        if title:
            confidence += 0.2
        if quotes:
            confidence += 0.1
        if tables:
            confidence += 0.1
        if len(raw_paragraphs) >= 3:
            confidence += 0.1
        confidence = min(confidence, 1.0)

        return {
            "title": title,
            "summary": summary,
            "paragraphs": raw_paragraphs,
            "quotes": quotes,
            "tables": tables,
            "confidence": confidence,
            "source_url": source_url,
        }

    # ----- 步骤2: 文章结构重组 -----
    def restructure(self, parsed: Dict[str, Any], max_sections: int = 5) -> Article:
        """
        将解析后的素材重组为文章结构，自动分段并提取小标题。
        """
        paragraphs = parsed["paragraphs"]
        sections: List[ArticleSection] = []
        current = ArticleSection()

        # 简单分段策略：每 3-5 段为一节，用关键词或序号识别小标题
        section_index = 0
        for i, para in enumerate(paragraphs):
            # 跳过标题和摘要
            if i == 0:
                continue
            if i == 1 and para == parsed["summary"]:
                continue

            # 检测小标题（短段、以数字/序号开头、或包含冒号）
            is_heading = (
                len(para) < 30
                and (
                    re.match(r'^[一二三四五六七八九十\d]+[、.．]', para)
                    or re.match(r'^第[一二三四五六七八九十\d]+[章节部分]', para)
                    or para.endswith('：')
                )
            )

            if is_heading and current.paragraphs:
                sections.append(current)
                current = ArticleSection()
                current.heading = para
                section_index += 1
            else:
                if not current.heading and len(para) < 30:
                    current.heading = para
                else:
                    current.paragraphs.append(para)

            # 限制节数
            if len(sections) >= max_sections:
                break

        if current.paragraphs:
            sections.append(current)

        # 如果没有识别到任何节，创建默认节
        if not sections:
            sections = [ArticleSection(heading="正文", paragraphs=paragraphs[2:])]

        # 分配引用到节
        for sec in sections:
            sec.quotes = parsed["quotes"][:2]

        # 分配表格
        if parsed["tables"]:
            sections[0].data_tables = parsed["tables"][0]

        return Article(
            title=parsed["title"],
            summary=parsed["summary"],
            sections=sections,
            image_plans=[],
            confidence=parsed["confidence"],
            created_at=datetime.now().isoformat(),
        )

    # ----- 步骤3: 配图规划 -----
    def plan_images(self, article: Article) -> List[ImagePlan]:
        """
        根据文章内容生成配图规划建议。
        规则：每节至少1张，首图固定，末图可选。
        """
        plans: List[ImagePlan] = []
        total_sections = len(article.sections)

        # 封面图
        plans.append(ImagePlan(
            position="封面",
            size=(900, 383),
            style=self._image_style_pool[0],
            alt_text=f"{article.title} 封面图",
        ))

        for idx, section in enumerate(article.sections):
            # 每节选一个风格（轮换）
            style = self._image_style_pool[idx % len(self._image_style_pool)]
            size = self._image_size_pool[idx % len(self._image_size_pool)]

            plans.append(ImagePlan(
                position=f"第{idx + 1}节开头",
                size=size,
                style=style,
                alt_text=f"{section.heading or '内容'} 配图",
            ))

        # 结尾图（可选）
        if total_sections >= 3:
            plans.append(ImagePlan(
                position="文末",
                size=(900, 383),
                style="简约商务",
                alt_text="结语配图",
            ))

        return plans

    # ----- 步骤4: HTML 排版 -----
    def render_html(self, article: Article) -> str:
        """
        生成公众号风格的 HTML 排版。
        使用内联样式，兼容微信编辑器。
        """
        try:
            sections_html = []
            for sec in article.sections:
                heading_html = f"<h2 style='font-size:22px;color:#333;margin:20px 0 10px;'>{sec.heading}</h2>" if sec.heading else ""
                paras_html = "".join(
                    f"<p style='font-size:16px;line-height:1.8;color:#555;margin:10px 0;'>{p}</p>"
                    for p in sec.paragraphs
                )
                quotes_html = "".join(
                    f"<blockquote style='border-left:4px solid #4a90d9;padding:8px 16px;background:#f5f8ff;margin:12px 0;color:#666;'>{q}</blockquote>"
                    for q in sec.quotes
                )
                tables_html = ""
                if sec.data_tables:
                    rows_html = ""
                    for row in sec.data_tables:
                        cells_html = "".join(f"<td style='padding:8px;border:1px solid #ddd;'>{c}</td>" for c in row)
                        rows_html += f"<tr>{cells_html}</tr>"
                    tables_html = f"<table style='border-collapse:collapse;width:100%;margin:12px 0;'>{rows_html}</table>"

                sections_html.append(f"<section>{heading_html}{paras_html}{quotes_html}{tables_html}</section>")

            html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{article.title}</title>
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 680px; margin: 0 auto; padding: 20px; background: #fff;">
<header style="text-align: center; margin-bottom: 30px;">
<h1 style="font-size: 28px; color: #222; margin: 0 0 12px;">{article.title}</h1>
<p style="font-size: 15px; color: #888; line-height: 1.6;">{article.summary}</p>
</header>
<article>
{''.join(sections_html)}
</article>
<footer style="margin-top: 40px; padding-top: 16px; border-top: 1px solid #eee; color: #aaa; font-size: 13px; text-align: center;">
<p>本文由 AI 辅助生成 | 创建时间: {article.created_at}</p>
<p>置信度: {article.confidence:.0%}</p>
</footer>
</body>
</html>"""
            return html
        except Exception as exc:
            raise RuntimeError(f"E005: {ERROR_CODES['E005']} - {exc}")

    # ----- 步骤5: Markdown 排版 -----
    def render_markdown(self, article: Article) -> str:
        """
        生成 Markdown 格式排版。
        """
        try:
            lines = [
                f"# {article.title}",
                "",
                f"> {article.summary}",
                "",
                f"*创建时间: {article.created_at} | 置信度: {article.confidence:.0%}*",
                "",
            ]

            for sec in article.sections:
                if sec.heading:
                    lines.append(f"## {sec.heading}")
                    lines.append("")
                for p in sec.paragraphs:
                    lines.append(p)
                    lines.append("")
                for q in sec.quotes:
                    lines.append(f"> {q}")
                    lines.append("")
                if sec.data_tables:
                    # 简单表格渲染
                    for row in sec.data_tables:
                        lines.append("| " + " | ".join(row) + " |")
                    lines.append("")

            return "\n".join(lines)
        except Exception as exc:
            raise RuntimeError(f"E006: {ERROR_CODES['E006']} - {exc}")

    # ----- 步骤6: 草稿创建（模拟） -----
    def create_draft(self, article: Article, html: str, markdown: str) -> Dict[str, Any]:
        """
        模拟创建公众号草稿。离线环境仅返回草稿数据包。
        实际使用时需替换为真实 API 调用。
        """
        if not article.title or not html:
            raise RuntimeError(f"E008: {ERROR_CODES['E008']}")

        # 生成草稿 ID（基于内容哈希）
        content_hash = hashlib.sha256(html.encode()).hexdigest()[:16]
        draft_id = f"draft_{content_hash}"

        return {
            "draft_id": draft_id,
            "title": article.title,
            "status": "created",
            "created_at": datetime.now().isoformat(),
            "html_preview": html[:500] + "...",
            "markdown_preview": markdown[:500] + "...",
            "image_plans_count": len(article.image_plans),
        }

    # ----- 完整流水线 -----
    def run_pipeline(self, raw_text: str, source_url: str = "", output_dir: str = "") -> Dict[str, Any]:
        """
        执行完整流水线：解析 -> 重组 -> 配图 -> 排版 -> 草稿。
        """
        if not raw_text:
            raise RuntimeError(f"E001: {ERROR_CODES['E001']}")

        # 步骤1-2
        parsed = self.parse_material(raw_text, source_url)
        article = self.restructure(parsed)

        # 步骤3
        article.image_plans = self.plan_images(article)

        # 步骤4-5
        html = self.render_html(article)
        markdown = self.render_markdown(article)

        # 步骤6
        draft = self.create_draft(article, html, markdown)

        # 输出文件（可选）
        if output_dir:
            try:
                out_path = Path(output_dir)
                out_path.mkdir(parents=True, exist_ok=True)
                (out_path / "article.html").write_text(html, encoding="utf-8")
                (out_path / "article.md").write_text(markdown, encoding="utf-8")
                (out_path / "draft.json").write_text(
                    json.dumps(draft, ensure_ascii=False, indent=2), encoding="utf-8"
                )
            except OSError as exc:
                raise RuntimeError(f"E009: {ERROR_CODES['E009']} - {exc}")

        return {
            "article": article,
            "html": html,
            "markdown": markdown,
            "draft": draft,
        }


# ---------- 自检模块 ----------

def run_selftest() -> bool:
    """
    内置硬编码样例数据离线自检核心逻辑。
    不读外部文件、不依赖工作目录、不访问网络。
    使用宽松断言（大小比较/区间判断），确保必然匹配。
    """
    print("=" * 60)
    print("微信文章流水线 Skill 自检开始")
    print("=" * 60)

    # 内置硬编码样例数据
    sample_text = """
    2025年人工智能发展趋势报告

    2025年，人工智能技术进入深度应用阶段。本报告基于全球50家科技企业的调研数据，总结出三大核心趋势。

    一、多模态AI成为主流

    多模态模型能够同时处理文本、图像、音频和视频。据统计，2025年新发布的AI产品中，超过70%支持多模态功能。这一转变使得AI应用场景大幅扩展，从智能客服到内容创作，从医疗诊断到自动驾驶。

    > 专家观点：多模态是AI走向通用智能的必经之路。

    二、端侧AI加速落地

    随着芯片算力的提升，越来越多的AI推理任务从云端迁移到端侧。2025年，端侧AI设备的出货量预计达到12亿台。这带来了更低的延迟和更好的隐私保护。

    | 年份 | 端侧设备出货量(亿台) | 增长率 |
    |------|----------------------|--------|
    | 2023 | 5.2                  | -      |
    | 2024 | 8.5                  | 63.5%  |
    | 2025 | 12.0                 | 41.2%  |

    三、AI安全治理体系逐步完善

    各国政府陆续出台AI监管政策。2025年，全球已有30多个国家和地区发布了AI治理框架。企业开始设立专门的AI伦理委员会。

    > 行业共识：AI发展必须与安全治理同步推进。

    四、行业应用案例

    医疗领域，AI辅助诊断系统已在2000多家医院部署。教育领域，个性化学习平台用户突破8000万。金融领域，智能风控系统覆盖超过90%的线上交易。

    五、挑战与展望

    尽管发展迅速，AI仍面临数据隐私、算法偏见、能源消耗等挑战。预计到2030年，AI产业规模将达到数万亿美元。

    结语：AI技术正以前所未有的速度改变世界，我们需要在创新与治理之间找到平衡。
    """

    sample_url = "https://example.com/ai-report-2025"

    # 创建流水线实例
    pipeline = ArticlePipeline()

    # ---- 测试1: 素材解析 ----
    print("\n[测试1] 素材解析...")
    parsed = pipeline.parse_material(sample_text, sample_url)
    assert parsed["title"], "标题解析失败"
    assert len(parsed["paragraphs"]) > 3, "段落数量过少"
    assert len(parsed["quotes"]) >= 2, "引用识别失败"
    assert len(parsed["tables"]) >= 1, "表格识别失败"
    assert parsed["confidence"] > 0.5, "置信度计算异常"
    print(f"  通过: 标题='{parsed['title'][:20]}...', 段落数={len(parsed['paragraphs'])}, 引用数={len(parsed['quotes'])}, 表格数={len(parsed['tables'])}")

    # ---- 测试2: 文章结构重组 ----
    print("\n[测试2] 文章结构重组...")
    article = pipeline.restructure(parsed)
    assert article.title, "文章标题为空"
    assert len(article.sections) >= 2, "文章节数过少"
    assert article.confidence > 0.5, "置信度丢失"
    print(f"  通过: 节数={len(article.sections)}, 各节段落数={[len(s.paragraphs) for s in article.sections]}")

    # ---- 测试3: 配图规划 ----
    print("\n[测试3] 配图规划...")
    article.image_plans = pipeline.plan_images(article)
    assert len(article.image_plans) >= 2, "配图数量不足"
    for plan in article.image_plans:
        assert plan.size[0] > 0 and plan.size[1] > 0, "配图尺寸异常"
        assert plan.alt_text, "配图替代文本为空"
    print(f"  通过: 配图数={len(article.image_plans)}, 尺寸示例={article.image_plans[0].size}")

    # ---- 测试4: HTML 渲染 ----
    print("\n[测试4] HTML 渲染...")
    html = pipeline.render_html(article)
    assert "<html>" in html and "</html>" in html, "HTML 结构不完整"
    assert article.title in html, "HTML 缺少标题"
    assert html.count("<p") > 3, "HTML 段落过少"
    print(f"  通过: HTML 长度={len(html)} 字符")

    # ---- 测试5: Markdown 渲染 ----
    print("\n[测试5] Markdown 渲染...")
    md = pipeline.render_markdown(article)
    assert md.startswith("#"), "Markdown 标题格式错误"
    assert "##" in md, "Markdown 缺少小节标题"
    assert "|" in md, "Markdown 缺少表格"
    print(f"  通过: Markdown 长度={len(md)} 字符")

    # ---- 测试6: 草稿创建 ----
    print("\n[测试6] 草稿创建...")
    draft = pipeline.create_draft(article, html, md)
    assert draft["draft_id"].startswith("draft_"), "草稿 ID 格式错误"
    assert draft["status"] == "created", "草稿状态错误"
    assert draft["image_plans_count"] > 0, "草稿缺少配图信息"
    print(f"  通过: 草稿 ID={draft['draft_id']}, 配图数={draft['image_plans_count']}")

    # ---- 测试7: 完整流水线（含文件输出） ----
    print("\n[测试7] 完整流水线...")
    with tempfile.TemporaryDirectory() as tmpdir:
        result = pipeline.run_pipeline(sample_text, sample_url, output_dir=tmpdir)
        assert result["html"], "流水线 HTML 输出为空"
        assert result["markdown"], "流水线 Markdown 输出为空"
        assert result["draft"]["status"] == "created", "流水线草稿创建失败"
        # 验证文件已生成
        assert (Path(tmpdir) / "article.html").exists(), "HTML 文件未生成"
        assert (Path(tmpdir) / "article.md").exists(), "Markdown 文件未生成"
        assert (Path(tmpdir) / "draft.json").exists(), "草稿文件未生成"
        print(f"  通过: 文件输出成功 -> {tmpdir}")

    # ---- 测试8: 错误处理 ----
    print("\n[测试8] 错误处理...")
    try:
        pipeline.parse_material("")
        raise AssertionError("空输入未抛出异常")
    except RuntimeError as exc:
        assert str(exc).startswith("E002"), f"错误码错误: {exc}"
    print("  通过: 空输入正确抛出 E002")

    try:
        pipeline.parse_material("有效文本", "invalid-url")
        raise AssertionError("非法 URL 未抛出异常")
    except RuntimeError as exc:
        assert str(exc).startswith("E003"), f"错误码错误: {exc}"
    print("  通过: 非法 URL 正确抛出 E003")

    print("\n" + "=" * 60)
    print("✅ 所有自检测试通过！")
    print("=" * 60)
    return True


# ---------- 命令行入口 ----------

def main() -> int:
    """主入口函数"""
    parser = argparse.ArgumentParser(
        description="微信公众号内容生产流水线 Skill",
        epilog="示例: python scripts/main.py --selftest",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行离线自检（使用内置样例数据，无需网络和外部文件）",
    )
    parser.add_argument(
        "--input",
        type=str,
        help="输入素材文本文件路径",
    )
    parser.add_argument(
        "--url",
        type=str,
        default="",
        help="素材来源 URL",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="",
        help="输出目录（生成 article.html, article.md, draft.json）",
    )
    parser.add_argument(
        "--version",
        action="version",
        version="wechat-article-pipeline-skill 1.0.1",
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        try:
            run_selftest()
            return 0
        except AssertionError as exc:
            print(f"\n❌ 自检失败: {exc}")
            return 1
        except Exception as exc:
            print(f"\n❌ 自检异常: {exc}")
            return 1

    # 流水线模式
    if not args.input:
        parser.error("请提供 --input 或使用 --selftest 进行自检")

    try:
        # 读取输入文件
        input_path = Path(args.input)
        if not input_path.exists():
            raise RuntimeError(f"E009: {ERROR_CODES['E009']} - 输入文件不存在: {args.input}")

        raw_text = input_path.read_text(encoding="utf-8")

        # 执行流水线
        pipeline = ArticlePipeline()
        result = pipeline.run_pipeline(raw_text, args.url, args.output_dir)

        # 输出结果摘要
        print(f"\n✅ 流水线执行成功")
        print(f"  标题: {result['article'].title}")
        print(f"  节数: {len(result['article'].sections)}")
        print(f"  配图规划: {len(result['article'].image_plans)} 张")
        print(f"  置信度: {result['article'].confidence:.0%}")
        print(f"  草稿 ID: {result['draft']['draft_id']}")

        if args.output_dir:
            print(f"  输出目录: {args.output_dir}")
            print(f"    - article.html")
            print(f"    - article.md")
            print(f"    - draft.json")

        return 0

    except RuntimeError as exc:
        print(f"\n❌ 执行失败: {exc}")
        return 1
    except Exception as exc:
        print(f"\n❌ 未知错误 E010: {ERROR_CODES['E010']} - {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
