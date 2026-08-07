#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
deeppapernote - 论文深度阅读与 Obsidian 风格研究笔记生成工具

本脚本根据功能规格独立实现（clean-room），仅依赖标准库。
核心能力：将单篇论文信息转换为结构化 Obsidian 风格笔记。
"""

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# 错误码定义（E001-E010）
# ============================================================
ERROR_CODES = {
    "E001": "输入为空，请提供待处理的内容（论文文本/文件路径/URL）",
    "E002": "关键信息缺失，请补充：论文标题、作者、年份等必要字段",
    "E003": "输入格式错误，示例：需要包含论文标题或正文内容",
    "E004": "超出能力边界，本工具仅处理单篇论文的阅读与笔记生成",
    "E005": "置信度过低，结果无法确定，建议人工复核",
    "E006": "输出目录无效或不可写",
    "E007": "内部处理异常，请检查输入数据",
    "E008": "参数解析错误",
    "E009": "文件读取失败",
    "E010": "数据序列化失败",
}


# ============================================================
# 数据结构定义
# ============================================================
@dataclass
class PaperInfo:
    """论文基础信息"""
    title: str = ""
    authors: List[str] = field(default_factory=list)
    year: int = 0
    venue: str = ""
    doi: str = ""
    abstract: str = ""
    keywords: List[str] = field(default_factory=list)


@dataclass
class NoteSection:
    """笔记章节"""
    title: str
    content: str
    confidence: float = 1.0


@dataclass
class ResearchNote:
    """研究笔记完整结构"""
    paper: PaperInfo
    sections: List[NoteSection] = field(default_factory=list)
    created_at: str = ""
    overall_confidence: float = 1.0
    warnings: List[str] = field(default_factory=list)


# ============================================================
# 核心处理类
# ============================================================
class PaperNoteGenerator:
    """论文笔记生成器 - 核心逻辑"""

    # 章节模板定义（Obsidian 风格）
    SECTION_TEMPLATES = [
        ("概览", "论文《{title}》由 {authors} 发表于 {year} 年。\n\n**关键词：** {keywords}\n\n**摘要：** {abstract}"),
        ("研究背景与动机", "本文关注 {topic} 领域的关键问题。\n\n> 背景说明：基于输入内容自动提取，置信度 {confidence}"),
        ("方法/核心贡献", "论文提出 {method_desc}。\n\n> 方法细节：根据论文内容自动总结，置信度 {confidence}"),
        ("主要结论", "实验/分析表明：{conclusion}。\n\n> 结论要点：基于摘要与正文推断，置信度 {confidence}"),
        ("个人思考与批注", "**值得深入的点：**\n- {think_points}\n\n**可复用的方法：**\n- {reusable}"),
    ]

    def __init__(self) -> None:
        """初始化生成器"""
        self._confidence_threshold_high = 0.90
        self._confidence_threshold_mid = 0.85

    # ---------- 主入口 ----------
    def generate(self, raw_input: str) -> ResearchNote:
        """
        从原始输入生成研究笔记

        Args:
            raw_input: 论文文本或元数据字符串

        Returns:
            ResearchNote: 生成的研究笔记

        Raises:
            ValueError: 当输入无效或处理失败时，附带错误码
        """
        # 1. 输入校验
        if not raw_input or not raw_input.strip():
            raise ValueError(f"E001: {ERROR_CODES['E001']}")

        # 2. 解析论文信息
        paper = self._parse_paper_info(raw_input)
        if not paper.title:
            raise ValueError(f"E002: {ERROR_CODES['E002']}")

        # 3. 生成笔记章节
        sections = self._build_sections(paper, raw_input)

        # 4. 计算总体置信度
        overall_conf = self._calculate_overall_confidence(sections)

        # 5. 组装笔记
        note = ResearchNote(
            paper=paper,
            sections=sections,
            created_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            overall_confidence=overall_conf,
        )

        # 6. 添加警告
        if overall_conf < self._confidence_threshold_mid:
            note.warnings.append("整体置信度偏低，建议人工复核关键内容")
        if not paper.doi:
            note.warnings.append("缺少 DOI 信息，引用时请注意核对")

        return note

    # ---------- 解析模块 ----------
    def _parse_paper_info(self, raw: str) -> PaperInfo:
        """
        从文本中提取论文元数据（基于正则与启发式规则）

        支持格式：
        - 标题: xxx
        - 作者: a, b, c
        - 年份: 2024
        - 摘要: xxx
        - 关键词: k1, k2
        - 期刊/会议: xxx
        - DOI: 10.xxxx/xxxx
        或自由文本（尽力提取标题/摘要）
        """
        paper = PaperInfo()
        text = raw.strip()

        # 尝试结构化解析（key: value 形式）
        lines = text.split("\n")
        for line in lines:
            line_stripped = line.strip()
            if not line_stripped:
                continue

            # 匹配 "key: value" 模式
            match = re.match(r"^(标题|作者|年份|摘要|关键词|期刊|会议|DOI|doi|Title|Author|Year|Abstract|Keywords)\s*[:：]\s*(.+)$", line_stripped, re.IGNORECASE)
            if match:
                key, value = match.group(1).lower(), match.group(2).strip()
                if key in ("标题", "title"):
                    paper.title = value
                elif key in ("作者", "author"):
                    paper.authors = [a.strip() for a in value.split(",") if a.strip()]
                elif key in ("年份", "year"):
                    try:
                        paper.year = int(value)
                    except ValueError:
                        pass
                elif key in ("摘要", "abstract"):
                    paper.abstract = value
                elif key in ("关键词", "keywords"):
                    paper.keywords = [k.strip() for k in value.split(",") if k.strip()]
                elif key in ("期刊", "会议", "venue"):
                    paper.venue = value
                elif key in ("doi",):
                    paper.doi = value

        # 若未结构化解析出标题，尝试从第一行提取
        if not paper.title:
            for line in lines[:5]:
                line_stripped = line.strip()
                if line_stripped and len(line_stripped) > 5:
                    paper.title = line_stripped[:100]  # 截断过长标题
                    break

        # 若未解析出摘要，取前200字符作为摘要（若有正文）
        if not paper.abstract:
            # 寻找正文段落（非结构化行）
            body_parts = []
            for line in lines:
                line_stripped = line.strip()
                if line_stripped and not re.match(r"^(标题|作者|年份|摘要|关键词|期刊|会议|DOI|doi)\s*[:：]", line_stripped, re.IGNORECASE):
                    body_parts.append(line_stripped)
            if body_parts:
                paper.abstract = " ".join(body_parts)[:300]

        # 默认关键词
        if not paper.keywords:
            paper.keywords = ["未提供"]

        return paper

    # ---------- 章节生成 ----------
    def _build_sections(self, paper: PaperInfo, raw_input: str) -> List[NoteSection]:
        """
        根据论文信息生成各章节内容
        """
        sections = []

        # 1. 概览章节
        overview_conf = 0.95 if paper.title and paper.authors else 0.80
        overview = self.SECTION_TEMPLATES[0][1].format(
            title=paper.title or "未命名",
            authors=", ".join(paper.authors) if paper.authors else "未知",
            year=paper.year or "未知",
            keywords=", ".join(paper.keywords),
            abstract=paper.abstract[:200] + ("..." if len(paper.abstract) > 200 else ""),
        )
        sections.append(NoteSection("概览", overview, overview_conf))

        # 2. 研究背景与动机
        topic = self._extract_topic(paper)
        bg_conf = 0.85 if topic else 0.70
        background = self.SECTION_TEMPLATES[1][1].format(
            topic=topic or "论文主题",
            confidence=f"{bg_conf:.0%}",
        )
        sections.append(NoteSection("研究背景与动机", background, bg_conf))

        # 3. 方法/核心贡献
        method = self._extract_method(paper, raw_input)
        method_conf = 0.80 if method != "未明确提及" else 0.60
        method_section = self.SECTION_TEMPLATES[2][1].format(
            method_desc=method,
            confidence=f"{method_conf:.0%}",
        )
        sections.append(NoteSection("方法/核心贡献", method_section, method_conf))

        # 4. 主要结论
        conclusion = self._extract_conclusion(paper, raw_input)
        concl_conf = 0.75 if conclusion != "未明确提及" else 0.55
        concl_section = self.SECTION_TEMPLATES[3][1].format(
            conclusion=conclusion,
            confidence=f"{concl_conf:.0%}",
        )
        sections.append(NoteSection("主要结论", concl_section, concl_conf))

        # 5. 个人思考与批注
        think_points = self._extract_think_points(paper)
        reusable = "论文的框架结构、分析方法、实验设计"
        think_conf = 0.70
        think_section = self.SECTION_TEMPLATES[4][1].format(
            think_points=think_points,
            reusable=reusable,
        )
        sections.append(NoteSection("个人思考与批注", think_section, think_conf))

        return sections

    # ---------- 辅助提取函数 ----------
    def _extract_topic(self, paper: PaperInfo) -> str:
        """从标题或关键词中提取研究主题"""
        candidates = []
        if paper.keywords and paper.keywords != ["未提供"]:
            candidates.extend(paper.keywords[:3])
        if paper.title:
            # 从标题中提取名词短语（简单启发式）
            words = re.findall(r"[A-Za-z\u4e00-\u9fff]+", paper.title)
            if len(words) >= 2:
                candidates.append(" ".join(words[:4]))
        return candidates[0] if candidates else ""

    def _extract_method(self, paper: PaperInfo, raw_input: str) -> str:
        """提取方法描述"""
        # 在摘要中查找方法关键词
        method_patterns = [
            r"(?:方法|提出|采用|使用|基于|我们|本文|approach|method|propose|introduce)",
            r"(?:模型|算法|框架|系统|framework|model|algorithm)",
        ]
        text = paper.abstract + " " + raw_input[:500]
        for pattern in method_patterns:
            match = re.search(pattern + r"[^。\n]{5,50}", text)
            if match:
                return match.group(0)[:60] + "..."
        return "未明确提及"

    def _extract_conclusion(self, paper: PaperInfo, raw_input: str) -> str:
        """提取主要结论"""
        text = paper.abstract + " " + raw_input[:500]
        patterns = [
            r"(?:结果表明|实验显示|我们发现|结论是|result|conclusion|find)",
            r"(?:性能|效果|准确率|提升|改善|提高)",
        ]
        for pattern in patterns:
            match = re.search(pattern + r"[^。\n]{5,50}", text)
            if match:
                return match.group(0)[:60] + "..."
        return "未明确提及"

    def _extract_think_points(self, paper: PaperInfo) -> str:
        """生成思考点"""
        points = []
        if paper.title:
            points.append(f"论文《{paper.title}》的创新点是否可迁移到其他场景？")
        if paper.authors:
            points.append(f"关注 {', '.join(paper.authors[:2])} 团队的后续工作")
        if paper.year:
            points.append(f"发表于 {paper.year} 年，技术是否仍有参考价值？")
        return "\n- ".join(points) if points else "无特别思考点"

    # ---------- 置信度计算 ----------
    def _calculate_overall_confidence(self, sections: List[NoteSection]) -> float:
        """计算整体置信度（加权平均）"""
        if not sections:
            return 0.0
        weights = [1.0, 0.8, 0.9, 0.9, 0.7]  # 各章节权重
        total_weight = sum(weights[:len(sections)])
        weighted_sum = sum(s.confidence * weights[i] for i, s in enumerate(sections))
        return weighted_sum / total_weight if total_weight > 0 else 0.0


# ============================================================
# 输出格式化模块
# ============================================================
class NoteFormatter:
    """笔记格式化（Obsidian Markdown）"""

    @staticmethod
    def to_markdown(note: ResearchNote) -> str:
        """转换为 Obsidian 风格 Markdown"""
        lines = []
        lines.append(f"# 📄 {note.paper.title}")
        lines.append("")
        lines.append(f"> [!info] 论文元数据")
        lines.append(f"> - **作者：** {', '.join(note.paper.authors) if note.paper.authors else '未知'}")
        lines.append(f"> - **年份：** {note.paper.year or '未知'}")
        lines.append(f"> - **期刊/会议：** {note.paper.venue or '未知'}")
        lines.append(f"> - **DOI：** {note.paper.doi or '未知'}")
        lines.append(f"> - **关键词：** {', '.join(note.paper.keywords)}")
        lines.append("")
        lines.append(f"> [!abstract] 摘要")
        lines.append(f"> {note.paper.abstract}")
        lines.append("")
        lines.append(f"**生成时间：** {note.created_at}")
        lines.append(f"**整体置信度：** {note.overall_confidence:.0%}")
        lines.append("")
        lines.append("---")
        lines.append("")

        # 各章节
        for section in note.sections:
            lines.append(f"## {section.title}")
            lines.append("")
            lines.append(section.content)
            lines.append("")
            if section.confidence < 0.85:
                lines.append(f"> [!warning] 置信度 {section.confidence:.0%}，建议复核")
                lines.append("")
            lines.append("---")
            lines.append("")

        # 警告
        if note.warnings:
            lines.append("## ⚠️ 注意事项")
            lines.append("")
            for warning in note.warnings:
                lines.append(f"- {warning}")
            lines.append("")

        return "\n".join(lines)

    @staticmethod
    def to_json(note: ResearchNote) -> str:
        """转换为 JSON 格式"""
        data = {
            "paper": {
                "title": note.paper.title,
                "authors": note.paper.authors,
                "year": note.paper.year,
                "venue": note.paper.venue,
                "doi": note.paper.doi,
                "abstract": note.paper.abstract,
                "keywords": note.paper.keywords,
            },
            "sections": [
                {"title": s.title, "content": s.content, "confidence": s.confidence}
                for s in note.sections
            ],
            "created_at": note.created_at,
            "overall_confidence": note.overall_confidence,
            "warnings": note.warnings,
        }
        return json.dumps(data, ensure_ascii=False, indent=2)


# ============================================================
# 自检模块（--selftest）
# ============================================================
class SelfTest:
    """内置自检逻辑（不依赖外部文件/网络）"""

    # 硬编码样例数据
    SAMPLE_INPUT = """标题: 基于深度学习的医学图像分割方法研究
作者: 张三, 李四, 王五
年份: 2024
期刊: 计算机学报
DOI: 10.1234/example.2024.001
关键词: 深度学习, 医学图像, 图像分割, U-Net
摘要: 本文提出一种改进的U-Net架构用于医学图像分割任务。实验表明，该方法在多个公开数据集上取得了优于基线模型的效果，尤其在边界分割精度方面提升显著。"""

    @classmethod
    def run(cls) -> bool:
        """执行自检，返回是否通过"""
        print("=" * 60)
        print("开始自检（deeppapernote --selftest）")
        print("=" * 60)

        try:
            # 1. 测试生成器
            generator = PaperNoteGenerator()
            note = generator.generate(cls.SAMPLE_INPUT)

            # 2. 基本结构断言（宽松阈值）
            assert note.paper.title, "标题不应为空"
            assert len(note.paper.authors) >= 2, "作者数应至少为2"
            assert note.paper.year >= 2020, "年份应在合理范围内"
            assert note.paper.year <= 2030, "年份不应过于超前"
            assert len(note.sections) >= 3, "章节数应至少为3"
            assert len(note.sections) <= 10, "章节数不应过多"

            # 3. 置信度断言（宽松区间）
            assert 0.0 <= note.overall_confidence <= 1.0, "置信度应在0-1之间"
            assert note.overall_confidence >= 0.5, "置信度不应过低"

            # 4. 内容非空断言
            for section in note.sections:
                assert section.title.strip(), "章节标题不应为空"
                assert section.content.strip(), "章节内容不应为空"
                assert 0.0 <= section.confidence <= 1.0, "章节置信度应在0-1之间"

            # 5. 格式化测试
            md_output = NoteFormatter.to_markdown(note)
            assert "## " in md_output, "Markdown 应包含二级标题"
            assert len(md_output) > 500, "Markdown 输出应有足够长度"

            json_output = NoteFormatter.to_json(note)
            parsed = json.loads(json_output)
            assert parsed["paper"]["title"] == note.paper.title, "JSON 往返应一致"
            assert len(parsed["sections"]) == len(note.sections), "JSON 章节数应一致"

            # 6. 错误处理测试
            try:
                generator.generate("")  # 空输入
                assert False, "空输入应抛出异常"
            except ValueError as e:
                assert str(e).startswith("E001"), "空输入应返回 E001 错误"

            try:
                generator.generate("   ")  # 空白输入
                assert False, "空白输入应抛出异常"
            except ValueError as e:
                assert str(e).startswith("E001"), "空白输入应返回 E001 错误"

            print("\n✅ 所有自检断言通过！")
            print(f"   - 论文标题: {note.paper.title}")
            print(f"   - 作者: {', '.join(note.paper.authors)}")
            print(f"   - 年份: {note.paper.year}")
            print(f"   - 章节数: {len(note.sections)}")
            print(f"   - 整体置信度: {note.overall_confidence:.0%}")
            print("\n自检完成，无外部依赖。")
            return True

        except AssertionError as e:
            print(f"\n❌ 自检失败 - 断言错误: {e}")
            return False
        except Exception as e:
            print(f"\n❌ 自检失败 - 异常: {e}")
            return False


# ============================================================
# 主入口
# ============================================================
def main() -> int:
    """命令行入口"""
    parser = argparse.ArgumentParser(
        description="deeppapernote - 论文深度阅读与 Obsidian 风格研究笔记生成工具",
        epilog="示例: python main.py --input '标题: xxx\\n作者: xxx' --output note.md --format markdown",
    )
    parser.add_argument(
        "--input", "-i",
        type=str,
        help="论文文本内容（支持结构化格式或自由文本）",
    )
    parser.add_argument(
        "--file", "-f",
        type=str,
        help="从文件读取论文内容",
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        default="research_note.md",
        help="输出文件路径（默认: research_note.md）",
    )
    parser.add_argument(
        "--format", "-fmt",
        type=str,
        choices=["markdown", "json"],
        default="markdown",
        help="输出格式（默认: markdown）",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检（无需外部输入）",
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        success = SelfTest.run()
        return 0 if success else 1

    # 收集输入
    raw_input = ""
    try:
        if args.input:
            raw_input = args.input
        elif args.file:
            try:
                with open(args.file, "r", encoding="utf-8") as f:
                    raw_input = f.read()
            except (IOError, OSError) as e:
                print(f"E009: {ERROR_CODES['E009']} - {e}", file=sys.stderr)
                return 9
        else:
            # 交互模式：从标准输入读取
            print("请输入论文内容（Ctrl+D 结束）：")
            raw_input = sys.stdin.read().strip()
    except KeyboardInterrupt:
        print("\n用户中断输入", file=sys.stderr)
        return 130

    # 生成笔记
    try:
        generator = PaperNoteGenerator()
        note = generator.generate(raw_input)
    except ValueError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"E007: {ERROR_CODES['E007']} - {e}", file=sys.stderr)
        return 7

    # 格式化输出
    try:
        if args.format == "json":
            output_text = NoteFormatter.to_json(note)
        else:
            output_text = NoteFormatter.to_markdown(note)
    except Exception as e:
        print(f"E010: {ERROR_CODES['E010']} - {e}", file=sys.stderr)
        return 10

    # 输出结果
    try:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output_text)
        print(f"✅ 笔记已生成: {args.output}")
        print(f"   整体置信度: {note.overall_confidence:.0%}")
        if note.warnings:
            print("   注意事项:")
            for w in note.warnings:
                print(f"   - {w}")
        return 0
    except (IOError, OSError) as e:
        print(f"E006: {ERROR_CODES['E006']} - {e}", file=sys.stderr)
        return 6


if __name__ == "__main__":
    sys.exit(main())
