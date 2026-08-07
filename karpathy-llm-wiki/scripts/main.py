#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py — Karpathy LLM Wiki 知识库构建与结构化输出工具

独立实现（clean-room），仅依据功能规格编写。
功能：
  - 多源文本输入解析（文本、文件、URL 由上层调用传入，本脚本仅处理文本）
  - 关键信息识别（实体、概念、关系、时间、数据指标）
  - 结构化输出（Markdown / JSON 知识条目）
  - 置信度标注（高/中/低）
  - 批量合并处理
  - 内置自检（--selftest），离线运行，不读外部文件、不访问网络
"""

import argparse
import json
import re
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple

# ---------------------------------------------------------------------------
# 错误码定义
# ---------------------------------------------------------------------------
# E001: 输入为空
# E002: 输入不是字符串
# E003: JSON 序列化失败
# E004: 输出目录不可写
# E005: 参数冲突
# E006: 内部逻辑错误（自检失败）
# E007: 不支持的文件类型
# E008: 文件读取失败
# E009: 输出格式不支持
# E010: 未知异常

ERROR_CODES = {
    "E001": "输入为空",
    "E002": "输入不是字符串",
    "E003": "JSON 序列化失败",
    "E004": "输出目录不可写",
    "E005": "参数冲突",
    "E006": "内部逻辑错误（自检失败）",
    "E007": "不支持的文件类型",
    "E008": "文件读取失败",
    "E009": "输出格式不支持",
    "E010": "未知异常",
}


class SkillError(Exception):
    """技能运行异常，携带错误码。"""

    def __init__(self, code: str, message: str = ""):
        self.code = code
        self.message = message or ERROR_CODES.get(code, "未知错误")
        super().__init__(f"[{code}] {self.message}")


# ---------------------------------------------------------------------------
# 核心数据结构
# ---------------------------------------------------------------------------

class KnowledgeEntry:
    """知识条目：一个结构化知识单元。"""

    def __init__(
        self,
        title: str,
        content: str,
        entities: Optional[List[str]] = None,
        concepts: Optional[List[str]] = None,
        relations: Optional[List[Dict[str, str]]] = None,
        timestamps: Optional[List[str]] = None,
        metrics: Optional[List[Dict[str, Any]]] = None,
        confidence: str = "中",
    ):
        self.title = title.strip()
        self.content = content.strip()
        self.entities = entities or []
        self.concepts = concepts or []
        self.relations = relations or []
        self.timestamps = timestamps or []
        self.metrics = metrics or []
        self.confidence = confidence  # 高 / 中 / 低

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典。"""
        return {
            "title": self.title,
            "content": self.content,
            "entities": self.entities,
            "concepts": self.concepts,
            "relations": self.relations,
            "timestamps": self.timestamps,
            "metrics": self.metrics,
            "confidence": self.confidence,
        }

    def to_markdown(self) -> str:
        """转换为 Markdown 格式。"""
        lines = [f"## {self.title}", "", self.content, ""]
        if self.entities:
            lines.append("**实体:** " + ", ".join(self.entities))
        if self.concepts:
            lines.append("**概念:** " + ", ".join(self.concepts))
        if self.relations:
            lines.append("**关系:**")
            for rel in self.relations:
                lines.append(
                    f"- {rel.get('from', '?')} --[{rel.get('type', '?')}]--> {rel.get('to', '?')}"
                )
        if self.timestamps:
            lines.append("**时间:** " + ", ".join(self.timestamps))
        if self.metrics:
            lines.append("**数据指标:**")
            for m in self.metrics:
                lines.append(
                    f"- {m.get('name', '?')}: {m.get('value', '?')} {m.get('unit', '')}"
                )
        lines.append(f"\n*置信度: {self.confidence}*\n")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# 文本解析与信息抽取
# ---------------------------------------------------------------------------

# 实体识别：常见专有名词（大写开头词、引号内术语）
_ENTITY_PATTERN = re.compile(
    r"(?<![A-Za-z])([A-Z][a-zA-Z]{2,}(?:\s[A-Z][a-zA-Z]{2,}){0,3})"
)

# 时间识别：年份、日期
_TIME_PATTERN = re.compile(
    r"(?:19|20)\d{2}(?:[-/年]\d{1,2}(?:[-/月]\d{1,2}日?)?)?"
)

# 数据指标：数字 + 单位
_METRIC_PATTERN = re.compile(
    r"(\d+(?:\.\d+)?)\s*(%|万|亿|元|美元|人|次|篇|个|GB|MB|TB|ms|秒|分钟|小时)"
)

# 概念词：常见技术/领域术语（简化版）
_CONCEPT_KEYWORDS = [
    "架构", "模型", "算法", "系统", "框架", "协议", "数据库", "网络",
    "机器学习", "深度学习", "知识库", "接口", "API", "分布式", "缓存",
    "索引", "检索", "生成", "推理", "训练", "推理", "向量", "嵌入",
]


def _extract_entities(text: str) -> List[str]:
    """提取实体（专有名词）。"""
    found = _ENTITY_PATTERN.findall(text)
    # 过滤掉常见非实体词
    stop_words = {"The", "This", "That", "These", "Those", "And", "But", "For", "With"}
    result = []
    for item in found:
        if item in stop_words:
            continue
        if item not in result:
            result.append(item)
    return result[:10]  # 最多返回 10 个


def _extract_timestamps(text: str) -> List[str]:
    """提取时间信息。"""
    return list(dict.fromkeys(_TIME_PATTERN.findall(text)))[:5]


def _extract_metrics(text: str) -> List[Dict[str, Any]]:
    """提取数据指标。"""
    result = []
    for match in _METRIC_PATTERN.findall(text):
        value, unit = match
        item = {"name": "指标", "value": value, "unit": unit}
        if item not in result:
            result.append(item)
    return result[:8]


def _extract_concepts(text: str) -> List[str]:
    """提取概念（基于关键词匹配）。"""
    found = []
    for kw in _CONCEPT_KEYWORDS:
        if kw in text and kw not in found:
            found.append(kw)
    return found[:8]


def _extract_relations(text: str) -> List[Dict[str, str]]:
    """提取简单关系（基于模式匹配：A 的 B / A 是 B / A 包含 B）。"""
    relations = []
    patterns = [
        re.compile(r"([\u4e00-\u9fa5A-Za-z]{2,20})的([\u4e00-\u9fa5A-Za-z]{2,20})"),
        re.compile(r"([\u4e00-\u9fa5A-Za-z]{2,20})(?:是|为)([\u4e00-\u9fa5A-Za-z]{2,20})"),
        re.compile(r"([\u4e00-\u9fa5A-Za-z]{2,20})(?:包含|包括|含有)([\u4e00-\u9fa5A-Za-z]{2,20})"),
    ]
    for pat in patterns:
        for m in pat.finditer(text):
            rel = {"from": m.group(1), "type": "关联", "to": m.group(2)}
            if rel not in relations:
                relations.append(rel)
    return relations[:5]


def _determine_confidence(text: str, entry: KnowledgeEntry) -> str:
    """根据抽取信息丰富度确定置信度。"""
    score = 0
    if len(entry.content) > 50:
        score += 1
    if len(entry.entities) >= 2:
        score += 1
    if len(entry.concepts) >= 2:
        score += 1
    if entry.timestamps or entry.metrics:
        score += 1
    if score >= 3:
        return "高"
    if score >= 1:
        return "中"
    return "低"


# ---------------------------------------------------------------------------
# 核心处理函数
# ---------------------------------------------------------------------------

def parse_text_to_entries(text: str, title: Optional[str] = None) -> List[KnowledgeEntry]:
    """将一段文本解析为知识条目列表。

    按段落切分，每段生成一个条目；若文本较短则整体生成一个条目。
    """
    if not text or not text.strip():
        raise SkillError("E001", "输入文本为空")

    if not isinstance(text, str):
        raise SkillError("E002", "输入必须是字符串")

    # 按空行切分为段落
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]

    if not paragraphs:
        paragraphs = [text.strip()]

    entries = []
    for i, para in enumerate(paragraphs):
        # 段落标题：优先取第一行，否则用默认标题
        lines = para.split("\n")
        para_title = lines[0].strip()[:30] if lines else ""
        if title:
            entry_title = f"{title} - 第{i+1}节"
        elif para_title:
            entry_title = para_title
        else:
            entry_title = f"知识条目 {i+1}"

        entry = KnowledgeEntry(
            title=entry_title,
            content=para,
            entities=_extract_entities(para),
            concepts=_extract_concepts(para),
            relations=_extract_relations(para),
            timestamps=_extract_timestamps(para),
            metrics=_extract_metrics(para),
        )
        entry.confidence = _determine_confidence(para, entry)
        entries.append(entry)

    return entries


def merge_entries(entries: List[KnowledgeEntry]) -> List[KnowledgeEntry]:
    """合并多个条目，按标题去重。"""
    seen_titles = set()
    merged = []
    for entry in entries:
        if entry.title not in seen_titles:
            seen_titles.add(entry.title)
            merged.append(entry)
    return merged


def generate_output(entries: List[KnowledgeEntry], fmt: str = "json") -> str:
    """生成结构化输出（JSON 或 Markdown）。"""
    if fmt == "json":
        try:
            return json.dumps(
                [e.to_dict() for e in entries],
                ensure_ascii=False,
                indent=2,
            )
        except (TypeError, ValueError) as exc:
            raise SkillError("E003", f"JSON 序列化失败: {exc}") from exc

    if fmt == "markdown":
        parts = ["# 知识库输出", ""]
        for e in entries:
            parts.append(e.to_markdown())
        return "\n".join(parts)

    raise SkillError("E009", f"不支持的输出格式: {fmt}")


def process_documents(
    documents: List[Dict[str, str]],
    output_format: str = "json",
) -> str:
    """批量处理文档列表。

    documents: [{"title": "...", "content": "..."}]
    """
    if not documents:
        raise SkillError("E001", "文档列表为空")

    all_entries: List[KnowledgeEntry] = []
    for doc in documents:
        title = doc.get("title", "")
        content = doc.get("content", "")
        if not content:
            continue
        entries = parse_text_to_entries(content, title=title or None)
        all_entries.extend(entries)

    merged = merge_entries(all_entries)
    return generate_output(merged, output_format)


# ---------------------------------------------------------------------------
# 自检模块（--selftest）
# ---------------------------------------------------------------------------

def _run_selftest() -> int:
    """内置硬编码样例，离线自检核心逻辑。"""
    print("开始自检...")

    # 样例 1: 基本解析
    sample_text = """
Transformer 架构是深度学习领域的重要模型，广泛应用于自然语言处理。
该模型由 Google 在 2017 年提出，包含注意力机制和位置编码。
训练数据量超过 100GB，推理速度提升 50%。

知识库系统支持分布式存储和向量检索，可处理百万级文档。
该系统在 2023 年完成升级，支持实时索引更新。
"""
    try:
        entries = parse_text_to_entries(sample_text, title="Transformer")
        assert len(entries) >= 1, "E006: 解析结果为空"
        assert all(isinstance(e, KnowledgeEntry) for e in entries), "E006: 类型错误"
        assert all(e.title for e in entries), "E006: 标题为空"
        print(f"  [OK] 文本解析: {len(entries)} 个条目")

        # 检查信息抽取
        combined_text = " ".join(e.content for e in entries)
        entities = _extract_entities(combined_text)
        concepts = _extract_concepts(combined_text)
        timestamps = _extract_timestamps(combined_text)
        metrics = _extract_metrics(combined_text)

        assert len(entities) >= 1, "E006: 未抽取到实体"
        assert len(concepts) >= 1, "E006: 未抽取到概念"
        assert len(timestamps) >= 1, "E006: 未抽取到时间"
        assert len(metrics) >= 1, "E006: 未抽取到指标"
        print(f"  [OK] 信息抽取: 实体={len(entities)}, 概念={len(concepts)}, "
              f"时间={len(timestamps)}, 指标={len(metrics)}")

        # 检查置信度
        confidences = {e.confidence for e in entries}
        assert confidences.issubset({"高", "中", "低"}), "E006: 置信度非法"
        print(f"  [OK] 置信度标注: {confidences}")

    except SkillError as exc:
        print(f"  [FAIL] {exc.code}: {exc.message}")
        return 1
    except AssertionError as exc:
        print(f"  [FAIL] {exc}")
        return 1

    # 样例 2: 批量处理与输出
    try:
        docs = [
            {
                "title": "深度学习",
                "content": "深度学习是机器学习的分支，使用多层神经网络进行特征学习。"
                           "主要框架包括 PyTorch 和 TensorFlow。",
            },
            {
                "title": "知识库",
                "content": "知识库系统用于存储和管理结构化知识，支持检索和推理。"
                           "2024 年新增图数据库支持。",
            },
        ]
        json_output = process_documents(docs, "json")
        parsed = json.loads(json_output)
        assert isinstance(parsed, list) and len(parsed) >= 1, "E006: JSON 输出异常"
        assert all("title" in item for item in parsed), "E006: JSON 缺少字段"
        print(f"  [OK] 批量处理 JSON: {len(parsed)} 条记录")

        md_output = process_documents(docs, "markdown")
        assert md_output.startswith("#"), "E006: Markdown 格式异常"
        assert "置信度" in md_output, "E006: Markdown 缺少置信度"
        print("  [OK] 批量处理 Markdown")

    except SkillError as exc:
        print(f"  [FAIL] {exc.code}: {exc.message}")
        return 1
    except json.JSONDecodeError:
        print("  [FAIL] JSON 解析失败")
        return 1

    # 样例 3: 边界与错误处理
    try:
        # 空输入
        try:
            parse_text_to_entries("")
            print("  [FAIL] 空输入未报错")
            return 1
        except SkillError as exc:
            assert exc.code == "E001", "E006: 错误码不正确"
        print("  [OK] 空输入错误处理")

        # 非字符串输入
        try:
            parse_text_to_entries(12345)  # type: ignore
            print("  [FAIL] 非字符串未报错")
            return 1
        except SkillError as exc:
            assert exc.code == "E002", "E006: 错误码不正确"
        print("  [OK] 非字符串错误处理")

        # 不支持的输出格式
        try:
            generate_output([KnowledgeEntry("测试", "内容")], "xml")
            print("  [FAIL] 不支持格式未报错")
            return 1
        except SkillError as exc:
            assert exc.code == "E009", "E006: 错误码不正确"
        print("  [OK] 格式错误处理")

    except AssertionError as exc:
        print(f"  [FAIL] {exc}")
        return 1

    print("全部自检通过。")
    return 0


# ---------------------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------------------

def _parse_args() -> argparse.Namespace:
    """解析命令行参数。"""
    parser = argparse.ArgumentParser(
        description="Karpathy LLM Wiki — 知识库构建与结构化输出工具"
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检（离线，不读取外部文件）",
    )
    parser.add_argument(
        "--input",
        type=str,
        help="输入文本（直接传入）",
    )
    parser.add_argument(
        "--title",
        type=str,
        default="",
        help="输入文本的标题（可选）",
    )
    parser.add_argument(
        "--format",
        type=str,
        choices=["json", "markdown"],
        default="json",
        help="输出格式（默认 json）",
    )
    parser.add_argument(
        "--output",
        type=str,
        help="输出文件路径（可选，默认输出到 stdout）",
    )
    return parser.parse_args()


def _main() -> int:
    """主函数。"""
    args = _parse_args()

    if args.selftest:
        return _run_selftest()

    # 正常处理模式
    if not args.input:
        print("错误: 请提供 --input 文本，或使用 --selftest 运行自检。", file=sys.stderr)
        return 1

    try:
        entries = parse_text_to_entries(args.input, title=args.title or None)
        output = generate_output(entries, args.format)

        if args.output:
            try:
                with open(args.output, "w", encoding="utf-8") as f:
                    f.write(output)
                print(f"已写入: {args.output}")
            except OSError as exc:
                raise SkillError("E004", f"输出目录不可写: {exc}") from exc
        else:
            print(output)
        return 0

    except SkillError as exc:
        print(f"错误: {exc.code}: {exc.message}", file=sys.stderr)
        return 1
    except Exception as exc:  # 兜底
        print(f"错误: E010: 未知异常: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(_main())
