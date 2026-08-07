#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
hallmark — 文本净化与原创性校准工具

功能：
  - AI 痕迹检测（模式匹配 + 统计特征）
  - 文本风格净化（规则改写）
  - 原创性辅助审查（片段相似度风险提示）
  - 内容校准（文体风格建议）

仅依赖 Python 标准库，无第三方依赖。
"""

import argparse
import math
import re
import sys
from collections import Counter
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# 错误码定义
# ---------------------------------------------------------------------------
ERR_OK = 0
ERR_INPUT_EMPTY = "E001"
ERR_INPUT_TOO_SHORT = "E002"
ERR_INPUT_TOO_LONG = "E003"
ERR_INVALID_ENCODING = "E004"
ERR_UNSUPPORTED_STYLE = "E005"
ERR_INTERNAL = "E006"
ERR_FILE_READ = "E007"
ERR_FILE_WRITE = "E008"
ERR_ARGUMENT = "E009"
ERR_UNKNOWN = "E010"


# ---------------------------------------------------------------------------
# 数据模型
# ---------------------------------------------------------------------------
@dataclass
class TraceMark:
    """单条 AI 痕迹标注"""
    start: int
    end: int
    pattern_type: str
    description: str
    confidence: float  # 0.0 ~ 1.0


@dataclass
class DetectionResult:
    """检测结果"""
    score: float  # 0~100，越高越像 AI
    marks: List[TraceMark] = field(default_factory=list)
    stats: Dict[str, float] = field(default_factory=dict)


@dataclass
class PurificationResult:
    """净化结果"""
    text: str
    changes: List[str] = field(default_factory=list)


@dataclass
class RiskItem:
    """原创性风险条目"""
    start: int
    end: int
    snippet: str
    reason: str
    risk_level: str  # low / medium / high


@dataclass
class StyleAdvice:
    """风格校准建议"""
    style: str
    advice: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# 内置模式库（规则引擎）
# ---------------------------------------------------------------------------
class PatternLibrary:
    """AI 生成文本常见模式库"""

    # 高频连接词 / 过渡词
    TRANSITION_WORDS = [
        "总而言之", "综上所述", "首先", "其次", "最后", "此外", "另外",
        "值得注意的是", "值得一提的是", "总的来说", "由此可见",
        "毫无疑问", "毋庸置疑", "不可否认", "众所周知", "事实上",
        "实际上", "换句话说", "也就是说", "这意味着", "因此", "所以",
    ]

    # 模板化开头/结尾
    TEMPLATE_OPENINGS = [
        "在当今社会", "随着社会的发展", "随着科技的进步", "在当今时代",
        "随着时代的发展", "在当今世界", "随着经济的飞速发展",
    ]

    TEMPLATE_CLOSINGS = [
        "让我们共同努力", "相信在不久的将来", "我们相信", "综上所述，我们可以得出",
        "总之，我们应该", "因此，我们需要", "毫无疑问，这将",
    ]

    # 过度工整排比（检测重复句式）
    PARALLEL_PATTERN = re.compile(r"([^。！？；\n]{4,20}?)[，,](?:\1[，,]){1,}")

    # 机械列举
    ENUM_PATTERN = re.compile(r"((?:第一|第二|第三|第四|第五|首先|其次|再次|最后)[，,、\s]){2,}")

    # 空洞修饰词
    HOLLOW_ADJECTIVES = [
        "重要的", "关键的", "必要的", "显著的", "巨大的", "深刻的",
        "全面的", "系统的", "有效的", "重要的", "积极的", "重大的",
    ]

    # 冗余短语
    REDUNDANT_PHRASES = [
        "进行了一个", "进行了", "能够有效地", "可以很好地", "在一定程度上",
        "从某种程度上说", "在某种程度上", "有着非常重要的", "具有非常重要的",
        "发挥着重要作用", "起到了积极作用", "是一个重要的",
    ]

    # 过于绝对的表述
    ABSOLUTE_WORDS = [
        "绝对", "必然", "一定", "肯定", "毫无疑问", "百分之百",
        "永远", "绝不", "完全", "彻底",
    ]

    # 高频 AI 用词（基于语言模型输出统计）
    AI_FREQUENT_WORDS = [
        "赋能", "抓手", "闭环", "颗粒度", "组合拳", "方法论",
        "底层逻辑", "认知升级", "第二曲线", "护城河", "生态位",
        "心智模型", "破圈", "链路", "场景化", "结构化", "体系化",
    ]


# ---------------------------------------------------------------------------
# 核心算法
# ---------------------------------------------------------------------------
class TextAnalyzer:
    """文本统计分析"""

    @staticmethod
    def sentence_length_variation(text: str) -> float:
        """计算句长变异系数（CV）。CV 越小越工整，越像 AI。"""
        sentences = re.split(r"[。！？!?；;\n]+", text)
        lengths = [len(s.strip()) for s in sentences if len(s.strip()) > 0]
        if len(lengths) < 2:
            return 0.0
        mean = sum(lengths) / len(lengths)
        if mean == 0:
            return 0.0
        variance = sum((x - mean) ** 2 for x in lengths) / len(lengths)
        std = math.sqrt(variance)
        return std / mean

    @staticmethod
    def word_repetition_rate(text: str) -> float:
        """计算词汇重复率（去掉停用词后的高频词占比）"""
        # 简单分词（按中文字符 + 英文单词）
        tokens = re.findall(r"[\u4e00-\u9fff]|[a-zA-Z]+", text)
        if not tokens:
            return 0.0
        # 去掉常见停用词
        stopwords = set("的了是在和有就不都一个很也吗吧啊呢这那".strip())
        filtered = [t for t in tokens if t not in stopwords and len(t) > 0]
        if not filtered:
            return 0.0
        counter = Counter(filtered)
        top_count = sum(count for _, count in counter.most_common(5))
        return top_count / len(filtered)

    @staticmethod
    def punctuation_density(text: str) -> float:
        """标点密度"""
        if not text:
            return 0.0
        puncts = re.findall(r"[，。！？；：、,.;:!?]", text)
        return len(puncts) / len(text)

    @staticmethod
    def sentence_avg_length(text: str) -> float:
        """平均句长"""
        sentences = re.split(r"[。！？!?；;\n]+", text)
        lengths = [len(s.strip()) for s in sentences if len(s.strip()) > 0]
        if not lengths:
            return 0.0
        return sum(lengths) / len(lengths)


class TraceDetector:
    """AI 痕迹检测器"""

    def __init__(self):
        self.patterns = PatternLibrary()
        self.analyzer = TextAnalyzer()

    def detect(self, text: str) -> DetectionResult:
        """检测文本中的 AI 痕迹"""
        marks: List[TraceMark] = []
        stats: Dict[str, float] = {}

        if not text or len(text.strip()) == 0:
            return DetectionResult(score=0.0, marks=[], stats={})

        # 1. 检测高频连接词
        for word in self.patterns.TRANSITION_WORDS:
            for match in re.finditer(re.escape(word), text):
                marks.append(TraceMark(
                    start=match.start(),
                    end=match.end(),
                    pattern_type="transition",
                    description=f"高频连接词: {word}",
                    confidence=0.6,
                ))

        # 2. 检测模板化开头
        for phrase in self.patterns.TEMPLATE_OPENINGS:
            if text.startswith(phrase):
                marks.append(TraceMark(
                    start=0,
                    end=len(phrase),
                    pattern_type="template_opening",
                    description=f"模板化开头: {phrase}",
                    confidence=0.7,
                ))

        # 3. 检测模板化结尾
        for phrase in self.patterns.TEMPLATE_CLOSINGS:
            if text.rstrip().endswith(phrase):
                marks.append(TraceMark(
                    start=max(0, len(text) - len(phrase)),
                    end=len(text),
                    pattern_type="template_closing",
                    description=f"模板化结尾: {phrase}",
                    confidence=0.7,
                ))

        # 4. 检测排比句式
        for match in self.patterns.PARALLEL_PATTERN.finditer(text):
            marks.append(TraceMark(
                start=match.start(),
                end=match.end(),
                pattern_type="parallel",
                description="过度工整的排比结构",
                confidence=0.75,
            ))

        # 5. 检测机械列举
        for match in self.patterns.ENUM_PATTERN.finditer(text):
            marks.append(TraceMark(
                start=match.start(),
                end=match.end(),
                pattern_type="enumeration",
                description="机械列举结构",
                confidence=0.65,
            ))

        # 6. 检测空洞修饰词
        for word in self.patterns.HOLLOW_ADJECTIVES:
            for match in re.finditer(re.escape(word), text):
                marks.append(TraceMark(
                    start=match.start(),
                    end=match.end(),
                    pattern_type="hollow_adjective",
                    description=f"空洞修饰词: {word}",
                    confidence=0.5,
                ))

        # 7. 检测冗余短语
        for phrase in self.patterns.REDUNDANT_PHRASES:
            for match in re.finditer(re.escape(phrase), text):
                marks.append(TraceMark(
                    start=match.start(),
                    end=match.end(),
                    pattern_type="redundant",
                    description=f"冗余短语: {phrase}",
                    confidence=0.55,
                ))

        # 8. 检测绝对化表述
        for word in self.patterns.ABSOLUTE_WORDS:
            for match in re.finditer(re.escape(word), text):
                marks.append(TraceMark(
                    start=match.start(),
                    end=match.end(),
                    pattern_type="absolute",
                    description=f"绝对化表述: {word}",
                    confidence=0.45,
                ))

        # 9. 检测 AI 高频词
        for word in self.patterns.AI_FREQUENT_WORDS:
            for match in re.finditer(re.escape(word), text):
                marks.append(TraceMark(
                    start=match.start(),
                    end=match.end(),
                    pattern_type="ai_word",
                    description=f"AI 高频词: {word}",
                    confidence=0.5,
                ))

        # 10. 统计特征
        cv = self.analyzer.sentence_length_variation(text)
        rep = self.analyzer.word_repetition_rate(text)
        punct = self.analyzer.punctuation_density(text)
        avg_len = self.analyzer.sentence_avg_length(text)

        stats = {
            "sentence_length_cv": cv,
            "word_repetition_rate": rep,
            "punctuation_density": punct,
            "avg_sentence_length": avg_len,
        }

        # 11. 综合评分
        score = self._compute_score(marks, stats)
        return DetectionResult(score=score, marks=marks, stats=stats)

    def _compute_score(self, marks: List[TraceMark], stats: Dict[str, float]) -> float:
        """综合评分（0~100）"""
        if not marks and not stats:
            return 0.0

        score = 0.0

        # 痕迹数量贡献（最多 50 分）
        mark_score = min(50.0, len(marks) * 5.0)
        score += mark_score

        # 统计特征贡献
        cv = stats.get("sentence_length_cv", 1.0)
        # CV 越小越像 AI（< 0.5 加分，> 1.0 减分）
        if cv < 0.5:
            score += 15.0
        elif cv < 0.8:
            score += 8.0
        elif cv > 1.5:
            score -= 5.0

        rep = stats.get("word_repetition_rate", 0.0)
        if rep > 0.3:
            score += 10.0
        elif rep > 0.2:
            score += 5.0

        punct = stats.get("punctuation_density", 0.0)
        if punct > 0.15:
            score += 5.0

        avg_len = stats.get("avg_sentence_length", 0.0)
        if 20 <= avg_len <= 40:
            score += 10.0  # 过于均匀的句长区间

        # 归一化到 0~100
        return max(0.0, min(100.0, score))


class TextPurifier:
    """文本净化器"""

    def __init__(self):
        self.patterns = PatternLibrary()

    def purify(self, text: str) -> PurificationResult:
        """净化文本，去除 AI 痕迹"""
        changes: List[str] = []
        result = text

        # 1. 去除冗余短语
        for phrase in self.patterns.REDUNDANT_PHRASES:
            pattern = re.compile(re.escape(phrase))
            matches = list(pattern.finditer(result))
            for match in reversed(matches):
                result = result[:match.start()] + result[match.end():]
                changes.append(f"移除冗余短语: {phrase}")

        # 2. 弱化绝对化表述
        for word in self.patterns.ABSOLUTE_WORDS:
            replacement = self._softer_word(word)
            if replacement:
                pattern = re.compile(re.escape(word))
                matches = list(pattern.finditer(result))
                for match in reversed(matches):
                    result = result[:match.start()] + replacement + result[match.end():]
                    changes.append(f"弱化绝对表述: {word} -> {replacement}")

        # 3. 替换 AI 高频词
        for word in self.patterns.AI_FREQUENT_WORDS:
            replacement = self._humanize_word(word)
            if replacement:
                pattern = re.compile(re.escape(word))
                matches = list(pattern.finditer(result))
                for match in reversed(matches):
                    result = result[:match.start()] + replacement + result[match.end():]
                    changes.append(f"替换 AI 高频词: {word} -> {replacement}")

        # 4. 打破模板化开头
        for phrase in self.patterns.TEMPLATE_OPENINGS:
            if result.startswith(phrase):
                rest = result[len(phrase):]
                result = rest
                changes.append(f"移除模板化开头: {phrase}")

        # 5. 打破模板化结尾
        for phrase in self.patterns.TEMPLATE_CLOSINGS:
            if result.rstrip().endswith(phrase):
                result = result[: -len(phrase)].rstrip()
                changes.append(f"移除模板化结尾: {phrase}")

        # 6. 打破机械列举（将序号词替换为普通连接）
        result = re.sub(r"(第一|第二|第三|第四|第五)[，,、\s]", "", result)
        changes.append("移除机械列举序号")

        # 清理多余空格和空行
        result = re.sub(r"[ \t]+", " ", result)
        result = re.sub(r"\n{3,}", "\n\n", result)

        return PurificationResult(text=result.strip(), changes=changes)

    def _softer_word(self, word: str) -> str:
        """将绝对化词汇弱化为更柔和的表达"""
        mapping = {
            "绝对": "通常",
            "必然": "往往",
            "一定": "一般",
            "肯定": "可能",
            "毫无疑问": "从某种角度看",
            "百分之百": "很大程度上",
            "永远": "长期来看",
            "绝不": "很少",
            "完全": "很大程度上",
            "彻底": "较大程度地",
        }
        return mapping.get(word, "")

    def _humanize_word(self, word: str) -> str:
        """将 AI 高频词替换为更自然的表达"""
        mapping = {
            "赋能": "提供支持",
            "抓手": "切入点",
            "闭环": "完整流程",
            "颗粒度": "细致程度",
            "组合拳": "多种手段并用",
            "方法论": "方法体系",
            "底层逻辑": "根本原因",
            "认知升级": "认识提升",
            "第二曲线": "新的增长点",
            "护城河": "竞争优势",
            "生态位": "定位",
            "心智模型": "思维方式",
            "破圈": "拓展受众",
            "链路": "环节",
            "场景化": "结合实际",
            "结构化": "有条理地",
            "体系化": "系统地",
        }
        return mapping.get(word, "")


class OriginalityChecker:
    """原创性辅助审查"""

    def __init__(self):
        # 内置一些常见公共知识片段（用于演示，实际场景会连接外部库）
        self.common_phrases = [
            "地球是太阳系中唯一已知存在生命的行星",
            "水是由氢和氧两种元素组成的",
            "人工智能是研究如何让计算机模拟人类智能的学科",
            "光合作用是植物利用光能将二氧化碳和水转化为有机物",
        ]

    def check(self, text: str) -> List[RiskItem]:
        """检查文本与常见片段的相似度风险"""
        risks: List[RiskItem] = []

        for phrase in self.common_phrases:
            # 简单相似度检查（包含或部分包含）
            if phrase in text:
                idx = text.index(phrase)
                risks.append(RiskItem(
                    start=idx,
                    end=idx + len(phrase),
                    snippet=phrase,
                    reason="与常见公共表述高度重合",
                    risk_level="high",
                ))
            else:
                # 检测部分匹配（连续 8 字以上相同）
                for i in range(len(phrase) - 8):
                    fragment = phrase[i:i + 8]
                    if fragment in text:
                        idx = text.index(fragment)
                        risks.append(RiskItem(
                            start=idx,
                            end=idx + len(fragment),
                            snippet=fragment,
                            reason="与常见表述存在片段重合",
                            risk_level="medium",
                        ))
                        break

        return risks


class StyleCalibrator:
    """内容校准器"""

    STYLE_RULES = {
        "论文": [
            "使用正式学术语气，避免口语化表达",
            "增加文献引用和理论支撑",
            "使用专业术语并确保定义清晰",
            "结论部分应明确研究局限与展望",
        ],
        "博客": [
            "采用第一人称视角，增加个人观点",
            "使用短段落和小标题增强可读性",
            "适当加入提问和互动性语句",
            "结尾可加入行动号召（CTA）",
        ],
        "公文": [
            "使用规范公文体例和固定格式",
            "避免情绪化表达，保持客观中立",
            "使用正式称谓和敬语",
            "内容应条理清晰，层次分明",
        ],
        "小说": [
            "增加感官细节描写（视觉、听觉、触觉）",
            "使用多样化的对话标签，避免单一'说'字",
            "适当使用短句营造节奏感",
            "减少抽象概念，多用具体意象",
        ],
    }

    def calibrate(self, text: str, style: str) -> StyleAdvice:
        """返回针对特定文体的校准建议"""
        if style not in self.STYLE_RULES:
            return StyleAdvice(style=style, advice=["暂不支持该文体，请选择：论文、博客、公文、小说"])

        base_advice = self.STYLE_RULES[style].copy()

        # 根据文本特征补充建议
        analyzer = TextAnalyzer()
        avg_len = analyzer.sentence_avg_length(text)

        if avg_len > 40:
            base_advice.append("检测到句子偏长，建议适当拆分以提高可读性")
        elif avg_len < 15:
            base_advice.append("检测到句子偏短，可适当合并以增强连贯性")

        return StyleAdvice(style=style, advice=base_advice)


# ---------------------------------------------------------------------------
# 主处理器（门面类）
# ---------------------------------------------------------------------------
class HallmarkProcessor:
    """hallmark 主处理入口"""

    def __init__(self):
        self.detector = TraceDetector()
        self.purifier = TextPurifier()
        self.checker = OriginalityChecker()
        self.calibrator = StyleCalibrator()

    def analyze(self, text: str) -> Dict:
        """完整分析流程"""
        # 输入校验
        if not text or not text.strip():
            return {"error": ERR_INPUT_EMPTY, "message": "输入文本为空"}

        if len(text.strip()) < 10:
            return {"error": ERR_INPUT_TOO_SHORT, "message": "输入文本过短（至少 10 字符）"}

        if len(text) > 100000:
            return {"error": ERR_INPUT_TOO_LONG, "message": "输入文本过长（最多 100000 字符）"}

        # 检测
        detection = self.detector.detect(text)

        # 净化
        purification = self.purifier.purify(text)

        # 原创性检查
        risks = self.checker.check(text)

        # 风格建议（默认给常见文体）
        style_advice = self.calibrator.calibrate(text, "博客")

        return {
            "detection": detection,
            "purification": purification,
            "risks": risks,
            "style_advice": style_advice,
        }

    def detect_only(self, text: str) -> DetectionResult:
        """仅检测"""
        return self.detector.detect(text)

    def purify_only(self, text: str) -> PurificationResult:
        """仅净化"""
        return self.purifier.purify(text)

    def check_only(self, text: str) -> List[RiskItem]:
        """仅原创性检查"""
        return self.checker.check(text)

    def calibrate_only(self, text: str, style: str) -> StyleAdvice:
        """仅风格校准"""
        return self.calibrator.calibrate(text, style)


# ---------------------------------------------------------------------------
# 命令行接口
# ---------------------------------------------------------------------------
def format_report(result: Dict) -> str:
    """格式化输出报告"""
    lines = []
    lines.append("=" * 60)
    lines.append("hallmark 分析报告")
    lines.append("=" * 60)

    if "error" in result:
        lines.append(f"错误码: {result['error']}")
        lines.append(f"错误信息: {result['message']}")
        return "\n".join(lines)

    detection = result["detection"]
    lines.append(f"\n【AI 痕迹检测】")
    lines.append(f"综合评分: {detection.score:.1f}/100")
    if detection.score >= 60:
        lines.append("判定: 高度疑似 AI 生成")
    elif detection.score >= 30:
        lines.append("判定: 存在部分 AI 痕迹")
    else:
        lines.append("判定: 基本符合人类写作特征")

    if detection.marks:
        lines.append(f"\n检测到 {len(detection.marks)} 处痕迹:")
        for mark in detection.marks[:10]:  # 最多显示 10 条
            lines.append(f"  - [{mark.pattern_type}] {mark.description} (置信度: {mark.confidence:.0%})")
        if len(detection.marks) > 10:
            lines.append(f"  ... 等共 {len(detection.marks)} 处")
    else:
        lines.append("未检测到明显 AI 痕迹")

    lines.append(f"\n统计特征:")
    stats = detection.stats
    lines.append(f"  句长变异系数: {stats.get('sentence_length_cv', 0):.3f}")
    lines.append(f"  词汇重复率: {stats.get('word_repetition_rate', 0):.2%}")
    lines.append(f"  标点密度: {stats.get('punctuation_density', 0):.2%}")
    lines.append(f"  平均句长: {stats.get('avg_sentence_length', 0):.1f} 字符")

    purification = result["purification"]
    lines.append(f"\n【文本净化】")
    if purification.changes:
        lines.append(f"执行了 {len(purification.changes)} 项净化操作:")
        for change in purification.changes:
            lines.append(f"  - {change}")
        lines.append(f"\n净化后文本 (前 200 字符):")
        lines.append(f"  {purification.text[:200]}...")
    else:
        lines.append("未需要净化操作")

    risks = result["risks"]
    lines.append(f"\n【原创性风险】")
    if risks:
        lines.append(f"发现 {len(risks)} 处风险提示:")
        for risk in risks:
            lines.append(f"  - [{risk.risk_level}] {risk.reason}: '{risk.snippet[:30]}...'")
    else:
        lines.append("未发现明显重叠风险")

    advice = result["style_advice"]
    lines.append(f"\n【风格校准建议】({advice.style})")
    for item in advice.advice:
        lines.append(f"  - {item}")

    lines.append("\n" + "=" * 60)
    lines.append("免责声明: 本报告仅供参考，不构成法律或学术结论。")
    lines.append("=" * 60)

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 自检模块（内置硬编码样例，离线运行）
# ---------------------------------------------------------------------------
def run_selftest() -> int:
    """内置样例数据的离线自检"""
    print("=" * 60)
    print("hallmark 自检程序")
    print("=" * 60)

    processor = HallmarkProcessor()

    # 样例 1: 典型的 AI 生成文本
    ai_text = """
    总而言之，随着科技的进步，人工智能在当今社会中发挥着重要作用。首先，人工智能能够有效地提高生产效率。其次，人工智能可以很好地改善医疗服务质量。最后，人工智能能够极大地促进教育发展。

    值得注意的是，人工智能的底层逻辑是数据驱动，通过机器学习算法实现认知升级。此外，人工智能的生态位正在不断扩展，赋能各行各业。毫无疑问，人工智能将成为未来发展的重要驱动力。

    综上所述，我们应该积极拥抱人工智能技术，充分发挥其优势，为社会发展做出更大的贡献。
    """

    # 样例 2: 自然的人类写作文本
    human_text = """
    昨晚下了一场雨，今早推开窗，空气里全是泥土的味道。院子里的月季开了，花瓣上还挂着水珠。

    我泡了杯茶，坐在门槛上发呆。隔壁张大爷又在修他的自行车，链条咔嗒咔嗒响。他说这车骑了二十年，比儿子还亲。

    中午去菜市场，卖菜的大姐多塞了我一把葱。她说今天的菠菜新鲜，让我回去下面条吃。我拎着菜往回走，路过书店买了本旧小说。

    晚上给老家的妈打了个电话。她说我爸最近迷上了钓鱼，天天往河边跑，晒得跟黑炭似的。我听着就笑了，想起小时候他带我去河边捉鱼的样子。
    """

    print("\n[测试 1] AI 痕迹检测...")
    result1 = processor.detect_only(ai_text)
    assert result1.score > 30, f"AI 文本评分应较高，实际: {result1.score}"
    assert len(result1.marks) > 0, "AI 文本应检测到痕迹"
    print(f"  通过。评分: {result1.score:.1f}, 痕迹数: {len(result1.marks)}")

    print("\n[测试 2] 人类文本检测...")
    result2 = processor.detect_only(human_text)
    assert result2.score < 30, f"人类文本评分应较低，实际: {result2.score}"
    print(f"  通过。评分: {result2.score:.1f}, 痕迹数: {len(result2.marks)}")

    print("\n[测试 3] 文本净化...")
    purify = processor.purify_only(ai_text)
    assert purify.text != ai_text, "净化后文本应发生变化"
    assert len(purify.changes) > 0, "应有净化操作"
    print(f"  通过。执行了 {len(purify.changes)} 项操作")

    print("\n[测试 4] 原创性检查...")
    risks = processor.check_only("地球是太阳系中唯一已知存在生命的行星，这是一个科学常识。")
    assert len(risks) > 0, "应检测到常见表述"
    print(f"  通过。发现 {len(risks)} 处风险")

    print("\n[测试 5] 风格校准...")
    advice = processor.calibrator.calibrate(ai_text, "论文")
    assert len(advice.advice) > 0, "应有建议"
    assert advice.style == "论文"
    print(f"  通过。获得 {len(advice.advice)} 条建议")

    print("\n[测试 6] 完整分析流程...")
    full = processor.analyze(ai_text)
    assert "detection" in full
    assert "purification" in full
    assert "risks" in full
    assert "style_advice" in full
    print(f"  通过。")

    print("\n[测试 7] 边界情况...")
    # 空输入
    err = processor.analyze("")
    assert "error" in err
    print(f"  空输入错误码正确: {err['error']}")

    # 过短输入
    err2 = processor.analyze("短")
    assert "error" in err2
    print(f"  短输入错误码正确: {err2['error']}")

    print("\n[测试 8] 统计分析稳健性...")
    analyzer = TextAnalyzer()
    cv = analyzer.sentence_length_variation(ai_text)
    rep = analyzer.word_repetition_rate(ai_text)
    punct = analyzer.punctuation_density(ai_text)
    assert 0.0 <= cv <= 5.0, f"变异系数应在合理范围: {cv}"
    assert 0.0 <= rep <= 1.0, f"重复率应在合理范围: {rep}"
    assert 0.0 <= punct <= 1.0, f"标点密度应在合理范围: {punct}"
    print(f"  通过。CV={cv:.3f}, 重复率={rep:.2%}, 标点密度={punct:.2%}")

    print("\n" + "=" * 60)
    print("所有自检测试通过！")
    print("=" * 60)
    return 0


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------
def main() -> int:
    """命令行主入口"""
    parser = argparse.ArgumentParser(
        description="hallmark - 文本净化与原创性校准工具",
        epilog="示例: python main.py --detect 文件.txt | --purify 文件.txt | --selftest"
    )
    parser.add_argument("--detect", metavar="FILE", help="检测文件中的 AI 痕迹")
    parser.add_argument("--purify", metavar="FILE", help="净化文件中的文本")
    parser.add_argument("--check", metavar="FILE", help="检查文件的原创性风险")
    parser.add_argument("--calibrate", metavar="FILE", help="对文件进行风格校准")
    parser.add_argument("--style", default="博客", choices=["论文", "博客", "公文", "小说"],
                        help="指定文体（用于 --calibrate）")
    parser.add_argument("--selftest", action="store_true", help="运行内置自检")
    parser.add_argument("--version", action="version", version="hallmark 1.0.2")

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        return run_selftest()

    # 处理模式
    processor = HallmarkProcessor()

    try:
        if args.detect:
            with open(args.detect, "r", encoding="utf-8") as f:
                text = f.read()
            result = processor.detect_only(text)
            print(f"AI 痕迹评分: {result.score:.1f}/100")
            if result.marks:
                print(f"发现 {len(result.marks)} 处痕迹:")
                for mark in result.marks:
                    print(f"  - [{mark.pattern_type}] {mark.description}")
            else:
                print("未发现明显 AI 痕迹")
            return ERR_OK

        elif args.purify:
            with open(args.purify, "r", encoding="utf-8") as f:
                text = f.read()
            result = processor.purify_only(text)
            print("净化完成。执行操作:")
            for change in result.changes:
                print(f"  - {change}")
            print(f"\n净化后文本:\n{result.text}")
            return ERR_OK

        elif args.check:
            with open(args.check, "r", encoding="utf-8") as f:
                text = f.read()
            risks = processor.check_only(text)
            if risks:
                print(f"发现 {len(risks)} 处风险:")
                for risk in risks:
                    print(f"  - [{risk.risk_level}] {risk.reason}")
            else:
                print("未发现明显风险")
            return ERR_OK

        elif args.calibrate:
            with open(args.calibrate, "r", encoding="utf-8") as f:
                text = f.read()
            advice = processor.calibrate_only(text, args.style)
            print(f"【{args.style}风格校准建议】")
            for item in advice.advice:
                print(f"  - {item}")
            return ERR_OK

        else:
            parser.print_help()
            return ERR_ARGUMENT

    except FileNotFoundError:
        print(f"错误: 文件不存在", file=sys.stderr)
        return ERR_FILE_READ
    except UnicodeDecodeError:
        print(f"错误: 文件编码无效（需 UTF-8）", file=sys.stderr)
        return ERR_INVALID_ENCODING
    except Exception as e:
        print(f"错误: 内部错误 - {e}", file=sys.stderr)
        return ERR_INTERNAL


if __name__ == "__main__":
    sys.exit(main())
