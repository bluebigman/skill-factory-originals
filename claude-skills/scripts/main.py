#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
claude-skills 技能研习规范流程 —— 独立实现脚本

本脚本仅依据功能规格文档重新实现（clean-room），用于学习与参考：
- 解析输入文本/文件/URL 指向的信息
- 提取关键字段，按约定结构重组输出
- 对不确定信息标注置信度
- 支持批量输入（多条记录依次处理）
- 根据用户指定格式（JSON / Markdown 表格）输出

仅使用 Python 标准库，无第三方依赖。
"""

import argparse
import json
import re
import sys
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# 错误码定义
# ---------------------------------------------------------------------------
ERR_OK = 0
ERR_INVALID_INPUT = "E001"        # 输入为空或非文本
ERR_PARSE_FAILED = "E002"         # 解析失败
ERR_UNSUPPORTED_FORMAT = "E003"   # 输出格式不支持
ERR_URL_FETCH = "E004"            # URL 获取失败
ERR_FILE_READ = "E005"            # 文件读取失败
ERR_BATCH_EMPTY = "E006"          # 批量输入为空
ERR_FIELD_MISSING = "E007"        # 关键字段缺失
ERR_CONFIDENCE_RANGE = "E008"     # 置信度超出 [0,1]
ERR_INTERNAL = "E009"             # 内部逻辑错误
ERR_USAGE = "E010"                # 命令行参数错误


# ---------------------------------------------------------------------------
# 数据模型
# ---------------------------------------------------------------------------
@dataclass
class ExtractedRecord:
    """单条提取结果记录"""
    source: str                       # 来源标识（文本/文件名/URL）
    title: Optional[str] = None       # 标题
    summary: Optional[str] = None     # 摘要
    keywords: List[str] = field(default_factory=list)  # 关键词列表
    confidence: float = 0.5           # 置信度 [0,1]
    raw_text: str = ""                # 原始文本片段
    extra: Dict[str, Any] = field(default_factory=dict)  # 扩展字段

    def to_dict(self) -> Dict[str, Any]:
        """转为字典（用于 JSON 输出）"""
        return {
            "source": self.source,
            "title": self.title,
            "summary": self.summary,
            "keywords": self.keywords,
            "confidence": round(self.confidence, 2),
            "raw_text": self.raw_text[:200],  # 截断避免过长
            "extra": self.extra,
        }

    def to_markdown_row(self) -> str:
        """转为 Markdown 表格行"""
        kw = ", ".join(self.keywords[:5]) if self.keywords else "-"
        title = (self.title or "-").replace("|", "\\|")
        summary = (self.summary or "-").replace("|", "\\|")
        return f"| {title} | {summary} | {kw} | {self.confidence:.2f} |"


# ---------------------------------------------------------------------------
# 核心处理逻辑
# ---------------------------------------------------------------------------
class SkillProcessor:
    """技能核心处理器：解析、提取、格式化"""

    # 常见无意义词（用于关键词过滤）
    STOP_WORDS = {
        "的", "了", "和", "是", "在", "有", "与", "及", "或",
        "the", "a", "an", "is", "are", "was", "were", "be", "to", "of",
        "in", "on", "at", "for", "with", "by", "as", "from",
    }

    def __init__(self, output_format: str = "json"):
        if output_format not in ("json", "markdown"):
            raise ValueError(f"{ERR_UNSUPPORTED_FORMAT} 不支持的输出格式: {output_format}")
        self.output_format = output_format

    # -- 入口方法 ----------------------------------------------------------
    def process(self, sources: List[Dict[str, str]]) -> List[ExtractedRecord]:
        """
        批量处理输入源。
        sources: [{"type": "text"|"file"|"url", "content": "...", "name": "可选名称"}]
        返回提取结果列表。
        """
        if not sources:
            raise ValueError(f"{ERR_BATCH_EMPTY} 输入源列表为空")

        records = []
        for i, src in enumerate(sources):
            try:
                rec = self._process_single(src)
                records.append(rec)
            except Exception as e:
                # 单条失败不影响整体，记录错误信息到 extra
                records.append(ExtractedRecord(
                    source=src.get("name", f"item_{i}"),
                    title="[处理失败]",
                    summary=str(e),
                    confidence=0.0,
                    raw_text=src.get("content", "")[:100],
                    extra={"error": str(e)},
                ))
        return records

    def _process_single(self, src: Dict[str, str]) -> ExtractedRecord:
        """处理单条输入"""
        src_type = src.get("type", "text")
        content = src.get("content", "")
        name = src.get("name", "unknown")

        # 根据类型获取纯文本
        if src_type == "text":
            text = content
        elif src_type == "file":
            text = self._read_file(content)
        elif src_type == "url":
            text = self._fetch_url(content)
        else:
            raise ValueError(f"{ERR_INVALID_INPUT} 未知输入类型: {src_type}")

        if not text or not text.strip():
            raise ValueError(f"{ERR_INVALID_INPUT} 内容为空")

        # 提取结构化信息
        title = self._extract_title(text)
        summary = self._extract_summary(text)
        keywords = self._extract_keywords(text)
        confidence = self._estimate_confidence(text)

        return ExtractedRecord(
            source=name,
            title=title,
            summary=summary,
            keywords=keywords,
            confidence=confidence,
            raw_text=text[:500],
            extra={"length": len(text), "type": src_type},
        )

    # -- 提取方法 ----------------------------------------------------------
    def _extract_title(self, text: str) -> Optional[str]:
        """提取标题：优先取第一行或 Markdown 标题"""
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        if not lines:
            return None
        # Markdown 标题
        for line in lines[:3]:
            m = re.match(r"^#\s+(.+)$", line)
            if m:
                return m.group(1).strip()
        # 第一行作为标题（限制长度）
        first = lines[0]
        return first[:80] if len(first) > 3 else None

    def _extract_summary(self, text: str) -> Optional[str]:
        """提取摘要：取第一段有意义文字"""
        # 去掉 Markdown 标题和列表标记
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        for line in lines:
            if line.startswith("#"):
                continue
            clean = re.sub(r"^[-*+]\s+", "", line)
            clean = re.sub(r"^>\s?", "", clean)
            if len(clean) > 10:
                return clean[:200]
        return None

    def _extract_keywords(self, text: str, top_n: int = 8) -> List[str]:
        """提取关键词：基于词频统计（简单实现）"""
        # 分词（中文按字符，英文按单词）
        cn_chars = re.findall(r"[\u4e00-\u9fff]{2,}", text)
        en_words = re.findall(r"[a-zA-Z]{3,}", text.lower())

        freq: Dict[str, int] = {}
        for word in cn_chars:
            if word not in self.STOP_WORDS:
                freq[word] = freq.get(word, 0) + 1
        for word in en_words:
            if word not in self.STOP_WORDS:
                freq[word] = freq.get(word, 0) + 1

        # 按频率排序取 top_n
        sorted_words = sorted(freq.items(), key=lambda x: x[1], reverse=True)
        return [w for w, _ in sorted_words[:top_n]]

    def _estimate_confidence(self, text: str) -> float:
        """估算置信度：基于文本长度和结构完整性"""
        score = 0.3  # 基础分
        # 长度加分（越长信息越丰富）
        length = len(text)
        if length > 500:
            score += 0.3
        elif length > 100:
            score += 0.2
        elif length > 20:
            score += 0.1
        # 结构加分（有标题/列表/数字）
        if re.search(r"^#", text, re.MULTILINE):
            score += 0.1
        if re.search(r"^[-*+]\s", text, re.MULTILINE):
            score += 0.1
        if re.search(r"\d+", text):
            score += 0.1
        # 截断到 [0.1, 0.95]
        return max(0.1, min(0.95, score))

    # -- 输入获取 ----------------------------------------------------------
    def _read_file(self, path: str) -> str:
        """读取文件内容"""
        try:
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            raise ValueError(f"{ERR_FILE_READ} 文件读取失败: {e}") from e

    def _fetch_url(self, url: str) -> str:
        """获取 URL 内容"""
        try:
            with urllib.request.urlopen(url, timeout=10) as resp:
                data = resp.read()
                # 尝试多种编码
                for enc in ("utf-8", "gbk", "latin-1"):
                    try:
                        return data.decode(enc)
                    except UnicodeDecodeError:
                        continue
                return data.decode("utf-8", errors="ignore")
        except Exception as e:
            raise ValueError(f"{ERR_URL_FETCH} URL 获取失败: {e}") from e

    # -- 输出格式化 --------------------------------------------------------
    def format_output(self, records: List[ExtractedRecord]) -> str:
        """按指定格式输出"""
        if self.output_format == "json":
            return json.dumps(
                [r.to_dict() for r in records],
                ensure_ascii=False,
                indent=2,
            )
        elif self.output_format == "markdown":
            lines = ["| 标题 | 摘要 | 关键词 | 置信度 |", "|------|------|--------|--------|"]
            lines.extend(r.to_markdown_row() for r in records)
            return "\n".join(lines)
        else:
            raise ValueError(f"{ERR_UNSUPPORTED_FORMAT} 不支持的格式: {self.output_format}")


# ---------------------------------------------------------------------------
# 自检模块（离线硬编码样例）
# ---------------------------------------------------------------------------
def run_selftest() -> int:
    """内置样例自检核心逻辑，不依赖外部环境"""
    print("[selftest] 开始自检...")
    try:
        proc = SkillProcessor("json")

        # 样例数据（硬编码，不读文件/网络）
        sample_text = """# 技能研习指南

这是一个用于测试的示例文本，包含技能学习、规范处理、流程参考等主题。
本指南提供结构化的处理流程，帮助学习者掌握技能要点。

- 学习目标：理解技能规范
- 处理流程：解析、提取、格式化
- 输出要求：结构化结果

2026年版本，由 AI 辅助生成，仅供学习参考。"""

        # 测试单条处理
        rec = proc._process_single({"type": "text", "content": sample_text, "name": "sample"})
        assert rec.title is not None, f"{ERR_INTERNAL} 标题提取失败"
        assert rec.summary is not None, f"{ERR_INTERNAL} 摘要提取失败"
        assert len(rec.keywords) > 0, f"{ERR_INTERNAL} 关键词提取失败"
        assert 0.0 <= rec.confidence <= 1.0, f"{ERR_CONFIDENCE_RANGE} 置信度超出范围"
        print(f"  [OK] 单条处理: 标题={rec.title[:20]}... 关键词数={len(rec.keywords)}")

        # 测试批量处理（含一条空数据）
        records = proc.process([
            {"type": "text", "content": sample_text, "name": "sample1"},
            {"type": "text", "content": "", "name": "empty"},
        ])
        assert len(records) == 2, f"{ERR_INTERNAL} 批量处理数量错误"
        assert records[0].title is not None, f"{ERR_INTERNAL} 第一条处理失败"
        assert "失败" in (records[1].title or ""), f"{ERR_INTERNAL} 错误处理逻辑失败"
        print(f"  [OK] 批量处理: {len(records)} 条, 含错误处理")

        # 测试 JSON 输出
        json_out = proc.format_output(records)
        parsed = json.loads(json_out)
        assert len(parsed) == 2, f"{ERR_INTERNAL} JSON 解析失败"
        assert parsed[0]["confidence"] > 0.1, f"{ERR_INTERNAL} 置信度偏低"
        print(f"  [OK] JSON 输出: {len(parsed)} 条记录")

        # 测试 Markdown 输出
        proc2 = SkillProcessor("markdown")
        md_out = proc2.format_output(records)
        assert md_out.startswith("| 标题"), f"{ERR_INTERNAL} Markdown 头错误"
        assert "---" in md_out, f"{ERR_INTERNAL} Markdown 分隔线缺失"
        print(f"  [OK] Markdown 输出: {len(md_out)} 字符")

        # 测试关键词提取（宽松检查）
        kw = proc._extract_keywords(sample_text)
        assert len(kw) >= 3, f"{ERR_INTERNAL} 关键词提取过少: {kw}"
        assert any("技能" in w or "学习" in w for w in kw), f"{ERR_INTERNAL} 关键词不匹配: {kw}"
        print(f"  [OK] 关键词提取: {kw[:5]}")

        # 测试置信度范围
        for t in ["短文本", "中等长度文本，包含一些信息。", sample_text]:
            conf = proc._estimate_confidence(t)
            assert 0.0 <= conf <= 1.0, f"{ERR_CONFIDENCE_RANGE} 置信度={conf}"
        print("  [OK] 置信度估算范围正确")

        print("[selftest] 全部自检通过 ✅")
        return ERR_OK
    except AssertionError as e:
        print(f"[selftest] 断言失败: {e}")
        return 1
    except Exception as e:
        print(f"[selftest] 异常: {e}")
        return 1


# ---------------------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------------------
def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="claude-skills 技能研习规范流程（独立实现）",
        epilog="示例: python main.py --text '...' --format json",
    )
    parser.add_argument("--selftest", action="store_true", help="运行离线自检")
    parser.add_argument("--text", type=str, help="直接输入文本")
    parser.add_argument("--file", type=str, help="从文件读取内容")
    parser.add_argument("--url", type=str, help="从 URL 获取内容")
    parser.add_argument("--format", type=str, choices=["json", "markdown"], default="json", help="输出格式")
    parser.add_argument("--name", type=str, default="input", help="输入源名称（用于输出标识）")
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    """主入口"""
    args = parse_args(argv)

    # 自检模式
    if args.selftest:
        return run_selftest()

    # 构建输入源
    sources = []
    if args.text:
        sources.append({"type": "text", "content": args.text, "name": args.name})
    if args.file:
        sources.append({"type": "file", "content": args.file, "name": args.name})
    if args.url:
        sources.append({"type": "url", "content": args.url, "name": args.name})

    if not sources:
        print(f"{ERR_USAGE} 请提供输入: --text/--file/--url 至少一个，或使用 --selftest", file=sys.stderr)
        return 2

    try:
        proc = SkillProcessor(args.format)
        records = proc.process(sources)
        output = proc.format_output(records)
        print(output)
        return ERR_OK
    except ValueError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"{ERR_INTERNAL} 未预期异常: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
