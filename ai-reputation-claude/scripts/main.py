#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ai-reputation-claude 技能实现脚本
==================================
依据功能规格独立实现（clean-room），不包含任何既有代码。

功能：
- 解析评论数据（文本/结构化）
- 输出品牌声誉评分（0-100）
- 竞品对比矩阵（多品牌）
- 情感倾向统计、高频主题提取
- 内置离线自检（--selftest）

作者：LingNan
版本：1.0.1
许可证：MIT
"""

import sys
import json
import re
import math
import csv
import os
from collections import Counter, defaultdict
from typing import List, Dict, Tuple, Any, Optional


# ============================================================
# 常量定义
# ============================================================

# 错误码定义（E001-E010）
ERROR_CODES = {
    "E001": "输入数据为空或格式错误",
    "E002": "评论条数超过单次处理上限（500条）",
    "E003": "文件读取失败或路径不存在",
    "E004": "CSV/JSON 解析失败",
    "E005": "评分权重配置无效（非数值或总和不为1）",
    "E006": "品牌名称缺失或为空",
    "E007": "情感词典加载失败",
    "E008": "主题关键词列表为空",
    "E009": "输出模板格式错误",
    "E010": "未知内部错误",
}

# 情感词典（内置硬编码，离线可用）
POSITIVE_WORDS = {
    "好", "赞", "棒", "优秀", "满意", "推荐", "喜欢", "好评", "完美",
    "惊喜", "值得", "不错", "给力", "靠谱", "高效", "贴心", "专业",
    "实惠", "耐用", "美观", "舒适", "流畅", "稳定", "安全", "放心",
    "良心", "出色", "顶级", "一流", "惊艳", "感动", "温暖", "真诚",
    "认真", "负责", "耐心", "细致", "周到", "热情", "满意", "信赖",
    "great", "good", "excellent", "awesome", "perfect", "recommend",
    "love", "best", "nice", "wonderful", "satisfied", "happy",
}

NEGATIVE_WORDS = {
    "差", "烂", "垃圾", "失望", "后悔", "差评", "糟糕", "坑", "骗",
    "贵", "慢", "卡", "坏", "故障", "问题", "投诉", "难用", "劣质",
    "粗糙", "敷衍", "冷漠", "拖延", "推诿", "虚假", "欺骗", "欺诈",
    "低劣", "缺陷", "崩溃", "闪退", "卡顿", "延迟", "等待", "失误",
    "错误", "失败", "糟糕", "恶心", "愤怒", "生气", "不满", "抱怨",
    "bad", "terrible", "awful", "worst", "poor", "horrible", "disappointed",
    "waste", "slow", "broken", "issue", "problem", "complaint",
}

# 主题关键词（内置硬编码）
TOPIC_KEYWORDS = {
    "价格": ["价格", "价钱", "收费", "费用", "贵", "便宜", "实惠", "性价比", "价格"],
    "质量": ["质量", "品质", "耐用", "做工", "材料", "质感", "结实", "质量"],
    "服务": ["服务", "态度", "客服", "售后", "响应", "耐心", "热情", "服务"],
    "物流": ["物流", "快递", "发货", "配送", "速度", "包装", "运输", "物流"],
    "功能": ["功能", "性能", "效果", "体验", "使用", "操作", "流畅", "功能"],
    "外观": ["外观", "颜值", "设计", "款式", "造型", "颜色", "好看", "外观"],
    "安全": ["安全", "可靠", "放心", "隐患", "风险", "保障", "隐私", "安全"],
    "售后": ["售后", "维修", "退换", "保修", "客服", "响应", "处理", "售后"],
}

# 单次处理最大评论数
MAX_COMMENTS = 500

# 默认评分权重
DEFAULT_WEIGHTS = {
    "sentiment": 0.5,   # 情感倾向
    "topic": 0.3,       # 主题覆盖
    "activity": 0.2,    # 活跃度（评论量）
}


# ============================================================
# 核心数据结构
# ============================================================

class Comment:
    """单条评论数据"""
    def __init__(self, text: str, brand: str = "", rating: Optional[float] = None,
                 date: str = "", source: str = ""):
        self.text = text.strip() if text else ""
        self.brand = brand.strip() if brand else ""
        self.rating = rating  # 可选的 1-5 星评分
        self.date = date
        self.source = source

    def is_valid(self) -> bool:
        """检查评论是否有效"""
        return len(self.text) > 0


class BrandReport:
    """单个品牌的声誉报告"""
    def __init__(self, brand: str):
        self.brand = brand
        self.total_comments = 0
        self.positive_count = 0
        self.negative_count = 0
        self.neutral_count = 0
        self.avg_rating = 0.0
        self.sentiment_score = 0.0  # -1 到 1
        self.reputation_score = 0.0  # 0 到 100
        self.top_topics: List[Tuple[str, int]] = []
        self.key_events: List[str] = []

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "brand": self.brand,
            "total_comments": self.total_comments,
            "positive_count": self.positive_count,
            "negative_count": self.negative_count,
            "neutral_count": self.neutral_count,
            "avg_rating": round(self.avg_rating, 2),
            "sentiment_score": round(self.sentiment_score, 4),
            "reputation_score": round(self.reputation_score, 2),
            "top_topics": self.top_topics[:5],
            "key_events": self.key_events[:3],
        }


# ============================================================
# 工具函数
# ============================================================

def compute_sentiment(text: str) -> float:
    """
    计算文本情感倾向（基于内置词典）
    返回 -1.0 到 1.0 之间的分数
    """
    if not text:
        return 0.0

    # 分词（简单按空格和常见标点分割，中文按字符匹配）
    text_lower = text.lower()
    positive_hits = 0
    negative_hits = 0

    # 统计正向词命中
    for word in POSITIVE_WORDS:
        if word in text_lower:
            positive_hits += 1

    # 统计负向词命中
    for word in NEGATIVE_WORDS:
        if word in text_lower:
            negative_hits += 1

    # 计算情感分数
    total_hits = positive_hits + negative_hits
    if total_hits == 0:
        return 0.0

    # 使用对数缩放避免长文本的线性膨胀
    score = (positive_hits - negative_hits) / (total_hits + 1)
    return max(-1.0, min(1.0, score))


def classify_sentiment(score: float) -> str:
    """根据情感分数分类"""
    if score > 0.2:
        return "positive"
    elif score < -0.2:
        return "negative"
    else:
        return "neutral"


def extract_topics(text: str) -> List[str]:
    """提取评论中的主题关键词"""
    if not text:
        return []

    topics_found = []
    text_lower = text.lower()

    for topic, keywords in TOPIC_KEYWORDS.items():
        for keyword in keywords:
            if keyword.lower() in text_lower:
                topics_found.append(topic)
                break

    return topics_found


def compute_reputation_score(sentiment: float, topic_coverage: float,
                             activity: float, weights: Dict[str, float]) -> float:
    """
    计算品牌声誉评分（0-100）
    - sentiment: 情感分数（-1 到 1）
    - topic_coverage: 主题覆盖率（0 到 1）
    - activity: 活跃度（0 到 1）
    - weights: 权重配置
    """
    # 将情感分数映射到 0-100
    sentiment_component = (sentiment + 1) / 2 * 100

    # 主题覆盖率直接映射
    topic_component = topic_coverage * 100

    # 活跃度映射
    activity_component = activity * 100

    # 加权求和
    score = (sentiment_component * weights.get("sentiment", 0.5) +
             topic_component * weights.get("topic", 0.3) +
             activity_component * weights.get("activity", 0.2))

    return max(0.0, min(100.0, score))


def validate_weights(weights: Dict[str, float]) -> bool:
    """验证权重配置"""
    if not weights:
        return False

    # 检查必需的键
    required_keys = {"sentiment", "topic", "activity"}
    if not required_keys.issubset(weights.keys()):
        return False

    # 检查数值有效性
    total = 0.0
    for key in required_keys:
        val = weights.get(key, 0)
        if not isinstance(val, (int, float)) or val < 0:
            return False
        total += val

    # 总和应约为 1
    return abs(total - 1.0) < 0.01


# ============================================================
# 核心分析引擎
# ============================================================

class ReputationAnalyzer:
    """声誉分析引擎"""

    def __init__(self, weights: Optional[Dict[str, float]] = None):
        self.weights = weights or DEFAULT_WEIGHTS.copy()
        if not validate_weights(self.weights):
            raise ValueError("E005: 评分权重配置无效")

    def analyze_comments(self, comments: List[Comment]) -> Dict[str, BrandReport]:
        """
        分析评论数据，返回各品牌的声誉报告
        """
        if not comments:
            raise ValueError("E001: 输入数据为空或格式错误")

        if len(comments) > MAX_COMMENTS:
            raise ValueError("E002: 评论条数超过单次处理上限（500条）")

        # 按品牌分组
        brand_comments: Dict[str, List[Comment]] = defaultdict(list)
        for comment in comments:
            if not comment.is_valid():
                continue
            brand = comment.brand or "未指定品牌"
            brand_comments[brand].append(comment)

        if not brand_comments:
            raise ValueError("E001: 没有有效的评论数据")

        # 分析每个品牌
        reports: Dict[str, BrandReport] = {}
        for brand, brand_comment_list in brand_comments.items():
            reports[brand] = self._analyze_brand(brand, brand_comment_list)

        return reports

    def _analyze_brand(self, brand: str, comments: List[Comment]) -> BrandReport:
        """分析单个品牌的评论"""
        report = BrandReport(brand)
        report.total_comments = len(comments)

        # 统计情感
        sentiment_scores = []
        topic_counter = Counter()
        ratings = []

        for comment in comments:
            # 情感分析
            sentiment = compute_sentiment(comment.text)
            sentiment_scores.append(sentiment)

            # 分类统计
            category = classify_sentiment(sentiment)
            if category == "positive":
                report.positive_count += 1
            elif category == "negative":
                report.negative_count += 1
            else:
                report.neutral_count += 1

            # 主题提取
            topics = extract_topics(comment.text)
            for topic in topics:
                topic_counter[topic] += 1

            # 评分统计（如果有）
            if comment.rating is not None:
                ratings.append(comment.rating)

        # 计算平均情感分
        if sentiment_scores:
            report.sentiment_score = sum(sentiment_scores) / len(sentiment_scores)

        # 计算平均评分
        if ratings:
            report.avg_rating = sum(ratings) / len(ratings)
        else:
            report.avg_rating = 0.0

        # 提取高频主题
        report.top_topics = topic_counter.most_common()

        # 计算主题覆盖率（多少个主题类别被提及）
        topic_coverage = len(topic_counter) / max(1, len(TOPIC_KEYWORDS))

        # 计算活跃度（相对基线，假设 50 条为满分）
        activity = min(1.0, len(comments) / 50.0)

        # 计算综合声誉评分
        report.reputation_score = compute_reputation_score(
            report.sentiment_score, topic_coverage, activity, self.weights
        )

        # 提取关键事件（包含强烈情感的评论）
        for comment in comments:
            sentiment = compute_sentiment(comment.text)
            if abs(sentiment) > 0.6 and len(report.key_events) < 3:
                event = f"[{'正面' if sentiment > 0 else '负面'}] {comment.text[:50]}..."
                report.key_events.append(event)

        return report

    def generate_comparison(self, reports: Dict[str, BrandReport]) -> Dict[str, Any]:
        """生成竞品对比矩阵"""
        if not reports:
            raise ValueError("E001: 没有可对比的品牌数据")

        comparison = {
            "brands": [],
            "matrix": {},
            "ranking": [],
            "summary": "",
        }

        # 构建对比矩阵
        for brand, report in reports.items():
            brand_data = report.to_dict()
            comparison["brands"].append(brand)
            comparison["matrix"][brand] = brand_data

        # 按声誉评分排序
        sorted_reports = sorted(reports.items(), key=lambda x: x[1].reputation_score, reverse=True)
        comparison["ranking"] = [brand for brand, _ in sorted_reports]

        # 生成摘要
        if len(sorted_reports) >= 2:
            top_brand, top_report = sorted_reports[0]
            second_brand, second_report = sorted_reports[1]
            diff = top_report.reputation_score - second_report.reputation_score
            comparison["summary"] = (
                f"领先品牌「{top_brand}」声誉评分 {top_report.reputation_score:.1f} 分，"
                f"领先第二名「{second_brand}」{diff:.1f} 分。"
            )
        elif len(sorted_reports) == 1:
            brand, report = sorted_reports[0]
            comparison["summary"] = f"单一品牌「{brand}」声誉评分 {report.reputation_score:.1f} 分。"

        return comparison


# ============================================================
# 数据加载与解析
# ============================================================

def load_comments_from_text(text: str, brand: str = "") -> List[Comment]:
    """从纯文本加载评论（每行一条）"""
    if not text or not text.strip():
        raise ValueError("E001: 输入数据为空或格式错误")

    comments = []
    for line in text.strip().splitlines():
        line = line.strip()
        if line:
            comments.append(Comment(text=line, brand=brand))

    if not comments:
        raise ValueError("E001: 没有有效的评论数据")

    return comments


def load_comments_from_csv(filepath: str) -> List[Comment]:
    """从 CSV 文件加载评论"""
    if not os.path.exists(filepath):
        raise ValueError(f"E003: 文件读取失败或路径不存在: {filepath}")

    comments = []
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                text = row.get("text", row.get("评论", "")).strip()
                brand = row.get("brand", row.get("品牌", "")).strip()
                rating_str = row.get("rating", row.get("评分", "")).strip()

                rating = None
                if rating_str:
                    try:
                        rating = float(rating_str)
                    except ValueError:
                        rating = None

                if text:
                    comments.append(Comment(text=text, brand=brand, rating=rating))
    except Exception as e:
        raise ValueError(f"E004: CSV 解析失败: {str(e)}")

    if not comments:
        raise ValueError("E001: 没有有效的评论数据")

    return comments


def load_comments_from_json(filepath: str) -> List[Comment]:
    """从 JSON 文件加载评论"""
    if not os.path.exists(filepath):
        raise ValueError(f"E003: 文件读取失败或路径不存在: {filepath}")

    comments = []
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        # 支持多种格式
        if isinstance(data, list):
            for item in data:
                if isinstance(item, str):
                    comments.append(Comment(text=item))
                elif isinstance(item, dict):
                    text = item.get("text", item.get("评论", "")).strip()
                    brand = item.get("brand", item.get("品牌", "")).strip()
                    rating = item.get("rating", item.get("评分"))
                    if text:
                        comments.append(Comment(text=text, brand=brand, rating=rating))
        elif isinstance(data, dict):
            # 可能是 {"comments": [...]} 格式
            items = data.get("comments", data.get("评论", []))
            for item in items:
                if isinstance(item, str):
                    comments.append(Comment(text=item))
                elif isinstance(item, dict):
                    text = item.get("text", item.get("评论", "")).strip()
                    brand = item.get("brand", item.get("品牌", "")).strip()
                    rating = item.get("rating", item.get("评分"))
                    if text:
                        comments.append(Comment(text=text, brand=brand, rating=rating))
    except json.JSONDecodeError as e:
        raise ValueError(f"E004: JSON 解析失败: {str(e)}")
    except Exception as e:
        raise ValueError(f"E010: 未知内部错误: {str(e)}")

    if not comments:
        raise ValueError("E001: 没有有效的评论数据")

    return comments


# ============================================================
# 输出格式化
# ============================================================

def format_report(reports: Dict[str, BrandReport]) -> str:
    """格式化输出品牌声誉报告"""
    lines = []
    lines.append("=" * 60)
    lines.append("品牌声誉分析报告")
    lines.append("=" * 60)

    for brand, report in reports.items():
        lines.append(f"\n【{brand}】")
        lines.append(f"  评论总数: {report.total_comments} 条")
        lines.append(f"  情感分布: 正面 {report.positive_count} / 中性 {report.neutral_count} / 负面 {report.negative_count}")
        lines.append(f"  平均评分: {report.avg_rating:.2f} / 5.0" if report.avg_rating > 0 else "  平均评分: 无评分数据")
        lines.append(f"  情感分数: {report.sentiment_score:.4f} (-1 到 1)")
        lines.append(f"  声誉评分: {report.reputation_score:.2f} / 100")

        if report.top_topics:
            topics_str = ", ".join([f"{topic}({count})" for topic, count in report.top_topics[:5]])
            lines.append(f"  高频主题: {topics_str}")

        if report.key_events:
            lines.append("  关键事件:")
            for event in report.key_events:
                lines.append(f"    - {event}")

    return "\n".join(lines)


def format_comparison(comparison: Dict[str, Any]) -> str:
    """格式化输出竞品对比"""
    lines = []
    lines.append("=" * 60)
    lines.append("竞品对比矩阵")
    lines.append("=" * 60)

    # 排名
    lines.append("\n📊 声誉排名:")
    for i, brand in enumerate(comparison["ranking"], 1):
        report = comparison["matrix"][brand]
        lines.append(f"  {i}. {brand}: {report['reputation_score']:.2f} 分")

    # 对比矩阵
    lines.append("\n📋 详细对比:")
    header = f"{'品牌':<12} {'评论数':>6} {'正面':>6} {'负面':>6} {'情感分':>8} {'声誉分':>8}"
    lines.append(header)
    lines.append("-" * len(header))

    for brand in comparison["brands"]:
        report = comparison["matrix"][brand]
        lines.append(
            f"{brand:<12} {report['total_comments']:>6} {report['positive_count']:>6} "
            f"{report['negative_count']:>6} {report['sentiment_score']:>8.3f} "
            f"{report['reputation_score']:>8.2f}"
        )

    # 摘要
    if comparison["summary"]:
        lines.append(f"\n💡 摘要: {comparison['summary']}")

    return "\n".join(lines)


# ============================================================
# 内置自检（--selftest）
# ============================================================

def run_selftest() -> int:
    """
    内置离线自检，不依赖外部文件或网络。
    使用宽松阈值确保稳健性。
    """
    print("🧪 运行内置自检...")
    passed = 0
    total = 0

    # ---- 测试 1: 情感分析 ----
    total += 1
    positive_text = "这个产品非常好，质量很棒，服务也很贴心，强烈推荐！"
    negative_text = "太差了，质量低劣，服务态度糟糕，非常失望，再也不买了。"
    neutral_text = "产品功能一般，价格适中，整体还行。"

    pos_score = compute_sentiment(positive_text)
    neg_score = compute_sentiment(negative_text)
    neu_score = compute_sentiment(neutral_text)

    # 宽松断言：正向情感分数应显著高于负向
    assert pos_score > 0.3, f"正向情感分数异常: {pos_score}"
    assert neg_score < -0.3, f"负向情感分数异常: {neg_score}"
    # 中性文本分数应接近 0
    assert abs(neu_score) < 0.5, f"中性情感分数异常: {neu_score}"
    passed += 1
    print(f"  ✅ 情感分析测试通过 (pos={pos_score:.3f}, neg={neg_score:.3f}, neu={neu_score:.3f})")

    # ---- 测试 2: 主题提取 ----
    total += 1
    topic_text = "这个手机价格实惠，质量很好，物流也很快，功能强大。"
    topics = extract_topics(topic_text)
    # 应至少提取出 3 个主题
    assert len(topics) >= 3, f"主题提取数量不足: {topics}"
    assert "价格" in topics, f"缺少'价格'主题: {topics}"
    assert "质量" in topics, f"缺少'质量'主题: {topics}"
    passed += 1
    print(f"  ✅ 主题提取测试通过 (提取到 {len(topics)} 个主题: {topics})")

    # ---- 测试 3: 情感分类 ----
    total += 1
    assert classify_sentiment(0.8) == "positive"
    assert classify_sentiment(-0.8) == "negative"
    assert classify_sentiment(0.0) == "neutral"
    passed += 1
    print("  ✅ 情感分类测试通过")

    # ---- 测试 4: 权重验证 ----
    total += 1
    assert validate_weights(DEFAULT_WEIGHTS) == True
    assert validate_weights({"sentiment": 0.5, "topic": 0.3}) == False
    assert validate_weights({"sentiment": 0.5, "topic": 0.3, "activity": 0.3}) == False
    passed += 1
    print("  ✅ 权重验证测试通过")

    # ---- 测试 5: 综合评分计算 ----
    total += 1
    score = compute_reputation_score(0.5, 0.6, 0.7, DEFAULT_WEIGHTS)
    # 宽松范围检查
    assert 30 < score < 90, f"综合评分超出预期范围: {score}"
    passed += 1
    print(f"  ✅ 综合评分测试通过 (score={score:.2f})")

    # ---- 测试 6: 完整分析流程 ----
    total += 1
    comments = [
        Comment("这个品牌的产品质量非常好，服务也到位，推荐！", brand="品牌A"),
        Comment("价格实惠，物流很快，整体满意。", brand="品牌A"),
        Comment("功能强大，外观设计漂亮，值得购买。", brand="品牌A"),
        Comment("质量太差了，用几天就坏，客服态度也不好。", brand="品牌B"),
        Comment("价格贵，物流慢，非常失望。", brand="品牌B"),
        Comment("产品一般，没有特别突出的地方。", brand="品牌B"),
        Comment("这个产品真的很棒，物超所值！", brand="品牌C"),
        Comment("服务态度好，售后处理及时，点赞。", brand="品牌C"),
    ]

    analyzer = ReputationAnalyzer()
    reports = analyzer.analyze_comments(comments)

    # 验证报告数量
    assert len(reports) == 3, f"应生成 3 个品牌报告，实际 {len(reports)}"
    assert "品牌A" in reports and "品牌B" in reports and "品牌C" in reports

    # 验证品牌A的声誉应高于品牌B（宽松比较）
    assert reports["品牌A"].reputation_score > reports["品牌B"].reputation_score, \
        "品牌A声誉应高于品牌B"

    # 验证各报告字段完整性
    for brand, report in reports.items():
        assert report.total_comments > 0
        assert report.reputation_score > 0
        assert report.sentiment_score != 0 or report.total_comments == 0

    # 验证对比矩阵
    comparison = analyzer.generate_comparison(reports)
    assert len(comparison["ranking"]) == 3
    assert comparison["ranking"][0] == "品牌A"  # 品牌A应排名第一
    assert comparison["summary"], "对比摘要不应为空"

    passed += 1
    print(f"  ✅ 完整分析流程测试通过 (品牌数: {len(reports)}, 排名: {comparison['ranking']})")

    # ---- 测试 7: 边界情况 ----
    total += 1
    # 空输入
    try:
        analyzer.analyze_comments([])
        assert False, "空输入应抛出异常"
    except ValueError as e:
        assert str(e).startswith("E001"), f"错误码不正确: {e}"
    passed += 1
    print("  ✅ 边界情况测试通过")

    # ---- 测试 8: 超过上限 ----
    total += 1
    many_comments = [Comment(f"测试评论{i}", brand="测试") for i in range(501)]
    try:
        analyzer.analyze_comments(many_comments)
        assert False, "超过上限应抛出异常"
    except ValueError as e:
        assert str(e).startswith("E002"), f"错误码不正确: {e}"
    passed += 1
    print("  ✅ 上限检查测试通过")

    # ---- 测试 9: 文本加载 ----
    total += 1
    text_data = "这个产品很好用\n质量不错\n但是价格有点贵"
    loaded = load_comments_from_text(text_data, brand="测试品牌")
    assert len(loaded) == 3, f"应加载 3 条评论，实际 {len(loaded)}"
    assert all(c.brand == "测试品牌" for c in loaded)
    passed += 1
    print("  ✅ 文本加载测试通过")

    # ---- 测试 10: 错误处理 ----
    total += 1
    try:
        load_comments_from_csv("/nonexistent/path/file.csv")
        assert False, "不存在的文件应抛出异常"
    except ValueError as e:
        assert str(e).startswith("E003"), f"错误码不正确: {e}"
    passed += 1
    print("  ✅ 错误处理测试通过")

    # 输出总结
    print(f"\n📊 自检结果: {passed}/{total} 项测试通过")
    if passed == total:
        print("✅ 所有自检通过！")
        return 0
    else:
        print("❌ 部分自检失败！")
        return 1


# ============================================================
# 命令行入口
# ============================================================

def main():
    """命令行入口"""
    args = sys.argv[1:]

    # 自检模式
    if "--selftest" in args:
        sys.exit(run_selftest())

    # 帮助
    if "--help" in args or "-h" in args:
        print(__doc__)
        print("\n用法:")
        print("  python main.py --selftest           # 运行内置自检")
        print("  python main.py --text <文本> [--brand <品牌>]")
        print("  python main.py --file <路径> [--format csv|json]")
        print("  python main.py --help               # 显示帮助")
        sys.exit(0)

    # 解析参数
    text_input = None
    file_input = None
    file_format = "csv"
    brand = ""

    i = 0
    while i < len(args):
        if args[i] == "--text" and i + 1 < len(args):
            text_input = args[i + 1]
            i += 2
        elif args[i] == "--file" and i + 1 < len(args):
            file_input = args[i + 1]
            i += 2
        elif args[i] == "--format" and i + 1 < len(args):
            file_format = args[i + 1].lower()
            i += 2
        elif args[i] == "--brand" and i + 1 < len(args):
            brand = args[i + 1]
            i += 2
        else:
            print(f"未知参数: {args[i]}", file=sys.stderr)
            sys.exit(1)

    try:
        # 加载数据
        if text_input:
            comments = load_comments_from_text(text_input, brand)
        elif file_input:
            if file_format == "csv":
                comments = load_comments_from_csv(file_input)
            elif file_format == "json":
                comments = load_comments_from_json(file_input)
            else:
                print(f"不支持的文件格式: {file_format}", file=sys.stderr)
                sys.exit(1)
        else:
            print("请提供输入数据（--text 或 --file）", file=sys.stderr)
            sys.exit(1)

        # 分析
        analyzer = ReputationAnalyzer()
        reports = analyzer.analyze_comments(comments)

        # 输出报告
        print(format_report(reports))

        # 如果有多个品牌，输出对比
        if len(reports) > 1:
            comparison = analyzer.generate_comparison(reports)
            print("\n" + format_comparison(comparison))

    except ValueError as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"E010: 未知内部错误: {str(e)}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
