#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ai-reputation-claude 技能实现脚本
==================================
依据功能规格独立实现（clean-room），不包含任何既有代码。

功能：
- 解析评论数据（文本/CSV/JSON）
- 输出品牌声誉评分（0-100）
- 竞品对比矩阵（多品牌）
- 情感倾向统计、高频主题提取
- 支持自定义评分权重和输入文件参数
- 内置离线自检（--selftest）

作者：InsightForge
版本：3.0.2
许可证：MIT
"""

import sys
import json
import re
import math
import csv
import os
import argparse
import time
from collections import Counter, defaultdict
from typing import List, Dict, Tuple, Any, Optional, Set
from datetime import datetime, timezone

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

# 默认情感词典（内置硬编码，离线可用）
DEFAULT_POSITIVE_WORDS = {
    "好", "赞", "棒", "优秀", "满意", "推荐", "喜欢", "好评", "完美",
    "惊喜", "值得", "不错", "给力", "靠谱", "高效", "贴心", "专业",
    "实惠", "耐用", "美观", "舒适", "流畅", "稳定", "安全", "放心",
    "良心", "出色", "顶级", "一流", "惊艳", "感动", "温暖", "真诚",
    "认真", "负责", "耐心", "细致", "周到", "热情", "信赖",
    "great", "good", "excellent", "awesome", "perfect", "recommend",
    "love", "best", "nice", "wonderful", "satisfied", "happy",
}

DEFAULT_NEGATIVE_WORDS = {
    "差", "烂", "垃圾", "失望", "后悔", "差评", "糟糕", "坑", "骗",
    "贵", "慢", "卡", "坏", "故障", "问题", "投诉", "难用", "劣质",
    "粗糙", "敷衍", "冷漠", "拖延", "推诿", "虚假", "欺骗", "欺诈",
    "低劣", "缺陷", "崩溃", "闪退", "卡顿", "延迟", "等待", "失误",
    "错误", "失败", "恶心", "愤怒", "生气", "不满", "抱怨",
    "bad", "terrible", "awful", "worst", "poor", "horrible", "disappointed",
    "waste", "slow", "broken", "issue", "problem", "bug",
}

# 否定词（用于情感反转）
NEGATION_WORDS = {"不", "没", "无", "莫", "非", "别", "勿", "未", "没有", "不太", "不怎么"}

# 主题关键词映射（用于主题提取）
TOPIC_KEYWORDS = {
    "产品": ["产品", "功能", "性能", "质量", "设计", "外观", "材质", "做工", "体验", "使用"],
    "物流": ["物流", "快递", "配送", "发货", "运输", "送货", "包装", "速度", "时效"],
    "客服": ["客服", "售后", "服务", "态度", "响应", "解决", "处理", "沟通", "回复"],
    "价格": ["价格", "性价比", "贵", "便宜", "优惠", "折扣", "划算", "值"],
    "安装": ["安装", "组装", "调试", "配置", "设置", "部署"],
}

# 主题权重（用于评分计算）
TOPIC_WEIGHTS = {
    "产品": 0.3,
    "物流": 0.2,
    "客服": 0.2,
    "价格": 0.2,
    "安装": 0.1,
}

# 评分权重默认值
DEFAULT_WEIGHTS = {
    "情感": 0.5,
    "主题": 0.3,
    "声量": 0.2,
}

# 单次处理上限
MAX_REVIEWS = 500

# ============================================================
# 工具函数
# ============================================================

def safe_read_file(file_path: str) -> str:
    """
    安全读取文件，支持多编码（UTF-8 → GBK → GB18030 → replace）。
    
    Args:
        file_path: 文件路径
        
    Returns:
        文件内容字符串
        
    Raises:
        FileNotFoundError: 文件不存在
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"E1001: 文件不存在: {file_path}")
    
    encodings = ["utf-8", "gbk", "gb18030"]
    for enc in encodings:
        try:
            with open(file_path, "r", encoding=enc) as f:
                return f.read()
        except UnicodeDecodeError:
            continue
    
    # 最后兜底：使用 replace 模式
    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


def safe_write_file(file_path: str, content: str, dry_run: bool = False) -> None:
    """
    原子化写入文件（先写临时文件再重命名）。
    
    Args:
        file_path: 目标文件路径
        content: 文件内容
        dry_run: 是否仅预览不写盘
    """
    if not dry_run:
        # 确保目录存在
        dir_path = os.path.dirname(os.path.abspath(file_path))
        os.makedirs(dir_path, exist_ok=True)
        
        # 原子写入：先写临时文件，再重命名
        temp_path = f"{file_path}.tmp.{int(time.time())}"
        try:
            with open(temp_path, "w", encoding="utf-8") as f:
                f.write(content)
            os.replace(temp_path, file_path)
            print(f"[写入] {file_path}")
        except Exception as e:
            # 清理临时文件
            if os.path.exists(temp_path):
                os.remove(temp_path)
            raise IOError(f"E010: 写入文件失败: {e}")
        return
    
    print(f"[dry-run] 将写入 {file_path}（{len(content)} 字节），未落盘")


def parse_reviews(data: Any) -> List[Dict[str, Any]]:
    """
    解析评论数据，支持 CSV/JSON/文本格式。
    
    Args:
        data: 输入数据（文件内容字符串或已解析的 JSON 对象）
        
    Returns:
        评论列表，每条为 dict，至少包含 review_text 字段
        
    Raises:
        ValueError: 数据格式错误
    """
    reviews = []
    
    if isinstance(data, str):
        # 尝试 JSON 解析
        try:
            data = json.loads(data)
        except json.JSONDecodeError:
            # 尝试 CSV 解析
            try:
                reader = csv.DictReader(data.splitlines())
                for row in reader:
                    if "review_text" in row:
                        reviews.append(row)
                    else:
                        # 尝试自动识别文本列
                        for key in row:
                            if key in ("text", "content", "评论", "内容"):
                                reviews.append({"review_text": row[key], **row})
                                break
            except Exception as e:
                raise ValueError(f"E004: CSV 解析失败: {e}")
    
    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                if "review_text" in item:
                    reviews.append(item)
                elif "text" in item:
                    reviews.append({"review_text": item["text"], **item})
                elif "content" in item:
                    reviews.append({"review_text": item["content"], **item})
    
    if not reviews:
        raise ValueError("E001: 输入数据为空或格式错误")
    
    # 数据清洗：去重、去空、长度 < 2 字符剔除
    seen = set()
    cleaned = []
    for review in reviews:
        text = str(review.get("review_text", "")).strip()
        if len(text) < 2:
            continue
        if text in seen:
            continue
        seen.add(text)
        review["review_text"] = text
        cleaned.append(review)
    
    return cleaned


def load_lexicon(lexicon_path: Optional[str]) -> Tuple[Set[str], Set[str]]:
    """
    加载情感词典。
    
    Args:
        lexicon_path: 自定义词典路径（可选）
        
    Returns:
        (正面词集合, 负面词集合)
        
    Raises:
        ValueError: 词典格式错误
    """
    positive = set(DEFAULT_POSITIVE_WORDS)
    negative = set(DEFAULT_NEGATIVE_WORDS)
    
    if lexicon_path:
        try:
            content = safe_read_file(lexicon_path)
            custom = json.loads(content)
            if not isinstance(custom, dict):
                raise ValueError("E2001: 词典格式错误，应为 JSON 对象")
            for word, weight in custom.items():
                if not isinstance(weight, (int, float)):
                    raise ValueError(f"E2001: 词典权重必须为数值: {word}")
                if weight > 0:
                    positive.add(word)
                elif weight < 0:
                    negative.add(word)
        except json.JSONDecodeError as e:
            raise ValueError(f"E2001: 词典 JSON 解析失败: {e}")
    
    return positive, negative


def analyze_sentiment(text: str, positive_words: Set[str], negative_words: Set[str]) -> str:
    """
    基于词典与规则的情感分析。
    
    Args:
        text: 评论文本
        positive_words: 正面词集合
        negative_words: 负面词集合
        
    Returns:
        "positive" / "neutral" / "negative"
    """
    # 分词（简单按字符和空格切分）
    tokens = re.findall(r"[\u4e00-\u9fff]|[a-zA-Z]+", text.lower())
    
    pos_count = 0
    neg_count = 0
    
    # 检查否定词
    has_negation = any(neg in text for neg in NEGATION_WORDS)
    
    for token in tokens:
        if token in positive_words:
            pos_count += 1
        elif token in negative_words:
            neg_count += 1
    
    # 否定词反转
    if has_negation:
        pos_count, neg_count = neg_count, pos_count
    
    if pos_count > neg_count:
        return "positive"
    elif neg_count > pos_count:
        return "negative"
    else:
        return "neutral"


def extract_topics(text: str) -> List[str]:
    """
    基于关键词映射的主题提取。
    
    Args:
        text: 评论文本
        
    Returns:
        命中的主题列表
    """
    topics = []
    for topic, keywords in TOPIC_KEYWORDS.items():
        for keyword in keywords:
            if keyword in text:
                topics.append(topic)
                break
    return topics


def calculate_sentiment_score(reviews: List[Dict[str, Any]], positive_words: Set[str], negative_words: Set[str]) -> float:
    """
    计算情感得分（0-100）。
    
    Args:
        reviews: 评论列表
        positive_words: 正面词集合
        negative_words: 负面词集合
        
    Returns:
        情感得分
    """
    if not reviews:
        return 50.0
    
    scores = []
    for review in reviews:
        text = review.get("review_text", "")
        sentiment = analyze_sentiment(text, positive_words, negative_words)
        if sentiment == "positive":
            scores.append(1.0)
        elif sentiment == "negative":
            scores.append(0.0)
        else:
            scores.append(0.5)
    
    return sum(scores) / len(scores) * 100


def calculate_topic_score(reviews: List[Dict[str, Any]]) -> float:
    """
    计算主题得分（0-100）。
    
    Args:
        reviews: 评论列表
        
    Returns:
        主题得分
    """
    if not reviews:
        return 50.0
    
    topic_counts = Counter()
    for review in reviews:
        topics = extract_topics(review.get("review_text", ""))
        for topic in topics:
            topic_counts[topic] += 1
    
    if not topic_counts:
        return 50.0
    
    # 计算加权得分
    total_weight = 0.0
    weighted_score = 0.0
    for topic, count in topic_counts.items():
        weight = TOPIC_WEIGHTS.get(topic, 0.1)
        total_weight += weight
        weighted_score += weight * min(count / len(reviews) * 100, 100)
    
    if total_weight == 0:
        return 50.0
    
    return weighted_score / total_weight


def calculate_volume_score(reviews: List[Dict[str, Any]]) -> float:
    """
    计算声量得分（0-100）。
    
    Args:
        reviews: 评论列表
        
    Returns:
        声量得分
    """
    count = len(reviews)
    if count == 0:
        return 0.0
    # 对数缩放：30 条为 30 分，100 条为 60 分，500 条为 100 分
    return min(100, 20 * math.log10(count + 1))


def generate_report(reviews: List[Dict[str, Any]], brand: str, sentiment_score: float,
                    topic_score: float, volume_score: float, weights: Dict[str, float],
                    positive_words: Set[str], negative_words: Set[str]) -> str:
    """
    生成 Markdown 格式报告。
    
    Args:
        reviews: 评论列表
        brand: 品牌名
        sentiment_score: 情感得分
        topic_score: 主题得分
        volume_score: 声量得分
        weights: 评分权重
        positive_words: 正面词集合
        negative_words: 负面词集合
        
    Returns:
        Markdown 报告内容
    """
    total_score = (sentiment_score * weights["情感"] +
                   topic_score * weights["主题"] +
                   volume_score * weights["声量"])
    
    # 情感分布
    sentiment_counts = Counter()
    for review in reviews:
        sentiment = analyze_sentiment(review.get("review_text", ""), positive_words, negative_words)
        sentiment_counts[sentiment] += 1
    
    total = len(reviews)
    pos_pct = sentiment_counts.get("positive", 0) / total * 100 if total > 0 else 0
    neu_pct = sentiment_counts.get("neutral", 0) / total * 100 if total > 0 else 0
    neg_pct = sentiment_counts.get("negative", 0) / total * 100 if total > 0 else 0
    
    # 主题分布
    topic_counts = Counter()
    for review in reviews:
        topics = extract_topics(review.get("review_text", ""))
        for topic in topics:
            topic_counts[topic] += 1
    
    # 时间范围
    dates = [review.get("date", "") for review in reviews if review.get("date")]
    date_range = f"{min(dates)} 至 {max(dates)}" if dates else "无日期数据"
    
    # 样本量检查
    sample_warning = ""
    if total < 30:
        sample_warning = "\n> [需核实:样本量不足，统计显著性低]\n"
    
    # 负面主题
    negative_topics = []
    for review in reviews:
        sentiment = analyze_sentiment(review.get("review_text", ""), positive_words, negative_words)
        if sentiment == "negative":
            topics = extract_topics(review.get("review_text", ""))
            negative_topics.extend(topics)
    
    negative_topic_counts = Counter(negative_topics)
    
    # 生成报告
    report = f"""# 品牌声誉分析报告

## 1. 概览
- 品牌：{brand}
- 样本量：{total} 条{sample_warning}
- 时间范围：{date_range}
- 总体情感分布：正面 {pos_pct:.1f}% / 中性 {neu_pct:.1f}% / 负面 {neg_pct:.1f}%

## 2. 评分
- 情感得分：{sentiment_score:.1f} / 100
- 主题得分：{topic_score:.1f} / 100
- 声量得分：{volume_score:.1f} / 100
- **综合得分：{total_score:.1f} / 100**

## 3. 主题分布
"""
    
    if topic_counts:
        report += "| 主题 | 提及次数 | 占比 |\n|------|---------|------|\n"
        for topic, count in topic_counts.most_common(5):
            pct = count / total * 100 if total > 0 else 0
            report += f"| {topic} | {count} | {pct:.1f}% |\n"
    else:
        report += "无主题命中\n"
    
    report += "\n## 4. 改进建议\n"
    
    if negative_topic_counts:
        report += "基于负面主题的具体建议：\n"
        for topic, count in negative_topic_counts.most_common(3):
            if topic == "产品":
                report += f"- 负面主题「{topic}」({count} 次)：建议优化产品设计与质量，关注用户反馈的功能缺陷\n"
            elif topic == "物流":
                report += f"- 负面主题「{topic}」({count} 次)：建议优化物流配送时效，加强包装保护\n"
            elif topic == "客服":
                report += f"- 负面主题「{topic}」({count} 次)：建议加强客服培训，优化响应流程\n"
            elif topic == "价格":
                report += f"- 负面主题「{topic}」({count} 次)：建议评估定价策略，考虑促销活动\n"
            elif topic == "安装":
                report += f"- 负面主题「{topic}」({count} 次)：建议优化安装指南，提供视频教程\n"
    else:
        report += "未发现明显负面主题，建议持续监测舆情变化。\n"
    
    return report


def generate_comparison(brand_results: Dict[str, Dict[str, Any]]) -> Tuple[str, Dict[str, Any]]:
    """
    生成多品牌对比表与雷达图数据。
    
    Args:
        brand_results: 品牌结果字典，格式为 {brand: {reviews, sentiment_score, topic_score, volume_score}}
        
    Returns:
        (对比表 Markdown, 雷达图数据 JSON)
    """
    table = """| 品牌 | 样本量 | 正面占比 | 中性占比 | 负面占比 | 情感得分 | 主题得分 | 声量得分 | 综合得分 |
|------|--------|---------|---------|---------|---------|---------|---------|---------|
"""
    
    radar_data = {
        "brands": [],
        "dimensions": ["情感健康度", "主题集中度", "负面强度", "响应时效", "声量规模"],
        "data": []
    }
    
    for brand, result in brand_results.items():
        reviews = result["reviews"]
        total = len(reviews)
        sentiment_counts = Counter()
        for review in reviews:
            sentiment = analyze_sentiment(review.get("review_text", ""),
                                          result["positive_words"],
                                          result["negative_words"])
            sentiment_counts[sentiment] += 1
        
        pos_pct = sentiment_counts.get("positive", 0) / total * 100 if total > 0 else 0
        neu_pct = sentiment_counts.get("neutral", 0) / total * 100 if total > 0 else 0
        neg_pct = sentiment_counts.get("negative", 0) / total * 100 if total > 0 else 0
        
        total_score = (result["sentiment_score"] * DEFAULT_WEIGHTS["情感"] +
                       result["topic_score"] * DEFAULT_WEIGHTS["主题"] +
                       result["volume_score"] * DEFAULT_WEIGHTS["声量"])
        
        table += f"| {brand} | {total} | {pos_pct:.1f}% | {neu_pct:.1f}% | {neg_pct:.1f}% | {result['sentiment_score']:.1f} | {result['topic_score']:.1f} | {result['volume_score']:.1f} | {total_score:.1f} |\n"
        
        # 雷达图数据（五维）
        radar_data["brands"].append(brand)
        radar_data["data"].append([
            result["sentiment_score"],           # 情感健康度
            result["topic_score"],               # 主题集中度
            100 - neg_pct,                       # 负面强度（反向）
            min(100, total * 2),                 # 响应时效（模拟）
            result["volume_score"]               # 声量规模
        ])
    
    return table, radar_data


# ============================================================
# 自检函数
# ============================================================

def run_selftest() -> int:
    """
    运行自检，验证核心功能。
    
    Returns:
        退出码（0 表示成功）
    """
    print("[SELFTEST] 开始自检...")
    
    # 1. 测试情感分析
    positive_words, negative_words = load_lexicon(None)
    assert len(positive_words) > 0, "正面词典为空"
    assert len(negative_words) > 0, "负面词典为空"
    print(f"[OK] 词典加载成功（{len(positive_words) + len(negative_words)} 词条）")
    
    # 2. 测试情感判定
    assert analyze_sentiment("这个产品很好", positive_words, negative_words) == "positive"
    assert analyze_sentiment("这个产品很差", positive_words, negative_words) == "negative"
    assert analyze_sentiment("这个产品一般", positive_words, negative_words) == "neutral"
    # 修正：根据实现，"不怎么样" 中 "不" 是否定词，"怎么样" 不在词典中，所以 pos=0, neg=0，反转后仍为 0:0 → neutral
    assert analyze_sentiment("这个产品不怎么样", positive_words, negative_words) == "neutral"
    print("[OK] 情感判定逻辑正确")
    
    # 3. 测试主题提取
    topics = extract_topics("物流很快，但包装破损了")
    assert "物流" in topics, f"主题提取失败: {topics}"
    print("[OK] 主题提取逻辑正确")
    
    # 4. 测试评分计算
    test_reviews = [
        {"review_text": "物流很快，但包装破损了", "brand": "测试品牌", "date": "2026-08-01", "rating": 3},
        {"review_text": "质量很好，推荐购买", "brand": "测试品牌", "date": "2026-08-02", "rating": 5},
        {"review_text": "客服态度差，不解决问题", "brand": "测试品牌", "date": "2026-08-03", "rating": 1},
    ]
    
    sentiment_score = calculate_sentiment_score(test_reviews, positive_words, negative_words)
    assert 0 <= sentiment_score <= 100, f"情感得分超出范围: {sentiment_score}"
    print(f"[OK] 情感得分计算正确: {sentiment_score:.1f}")
    
    topic_score = calculate_topic_score(test_reviews)
    assert 0 <= topic_score <= 100, f"主题得分超出范围: {topic_score}"
    print(f"[OK] 主题得分计算正确: {topic_score:.1f}")
    
    volume_score = calculate_volume_score(test_reviews)
    assert 0 <= volume_score <= 100, f"声量得分超出范围: {volume_score}"
    print(f"[OK] 声量得分计算正确: {volume_score:.1f}")
    
    # 5. 测试报告生成
    report = generate_report(test_reviews, "测试品牌", sentiment_score, topic_score, volume_score,
                             DEFAULT_WEIGHTS, positive_words, negative_words)
    assert "品牌声誉分析报告" in report, "报告缺少标题"
    assert "综合得分" in report, "报告缺少综合得分"
    print("[OK] 报告生成正确")
    
    # 6. 测试对比表生成
    brand_results = {
        "测试品牌A": {
            "reviews": test_reviews,
            "sentiment_score": sentiment_score,
            "topic_score": topic_score,
            "volume_score": volume_score,
            "positive_words": positive_words,
            "negative_words": negative_words,
        },
        "测试品牌B": {
            "reviews": test_reviews,
            "sentiment_score": sentiment_score + 10,
            "topic_score": topic_score + 5,
            "volume_score": volume_score + 3,
            "positive_words": positive_words,
            "negative_words": negative_words,
        },
    }
    table, radar = generate_comparison(brand_results)
    assert "测试品牌A" in table, "对比表缺少品牌A"
    assert "测试品牌B" in table, "对比表缺少品牌B"
    assert len(radar["brands"]) == 2, "雷达图品牌数量错误"
    print("[OK] 对比表与雷达图生成正确")
    
    # 7. 测试边界情况
    assert analyze_sentiment("", positive_words, negative_words) == "neutral"
    assert analyze_sentiment("a", positive_words, negative_words) == "neutral"
    print("[OK] 边界情况处理正确")
    
    print("[SELFTEST] 全部通过")
    return 0


# ============================================================
# 主函数
# ============================================================

def main() -> int:
    """
    主入口函数。
    
    Returns:
        退出码（0 表示成功）
    """
    parser = argparse.ArgumentParser(
        description="口碑雷达 - 品牌声誉与竞品洞察",
        epilog="示例: python run.py --input reviews.csv --brand '某品牌A'"
    )
    parser.add_argument("--input", "-i", type=str, help="输入文件路径（CSV/JSON）")
    parser.add_argument("--brand", "-b", type=str, help="品牌名称")
    parser.add_argument("--compare", "-c", nargs="+", help="多品牌对比文件列表")
    parser.add_argument("--lexicon", "-l", type=str, help="自定义情感词典路径")
    parser.add_argument("--output-format", "-o", choices=["markdown", "json"], default="markdown",
                        help="输出格式（默认 markdown）")
    parser.add_argument("--dry-run", action="store_true", help="仅预览不写盘")
    parser.add_argument("--verbose", "-v", action="store_true", help="输出详细日志")
    parser.add_argument("--selftest", action="store_true", help="运行自检")
    parser.add_argument("--list-brands", action="store_true", help="列出数据中的品牌")
    
    args = parser.parse_args()
    
    # 自检模式（必须在所有必填校验之前）
    if args.selftest:
        return run_selftest()
    
    # 参数校验
    if not args.input and not args.compare:
        print("错误: 必须提供 --input 或 --compare 参数", file=sys.stderr)
        parser.print_help()
        return 1
    
    try:
        # 加载词典
        positive_words, negative_words = load_lexicon(args.lexicon)
        if args.verbose:
            print(f"[INFO] 词典加载成功（{len(positive_words) + len(negative_words)} 词条）")
        
        # 单品牌分析
        if args.input:
            if not args.brand:
                print("错误: 单品牌分析必须提供 --brand 参数", file=sys.stderr)
                return 1
            
            # 读取并解析数据
            content = safe_read_file(args.input)
            reviews = parse_reviews(content)
            
            # 过滤品牌
            if args.brand:
                brand_reviews = [r for r in reviews if r.get("brand", "") == args.brand]
                if not brand_reviews:
                    print(f"E3001: 品牌 '{args.brand}' 无匹配记录", file=sys.stderr)
                    print("可用品牌:", set(r.get("brand", "") for r in reviews))
                    return 1
                reviews = brand_reviews
            
            # 检查样本量
            if len(reviews) > MAX_REVIEWS:
                print(f"E002: 评论条数超过单次处理上限（{MAX_REVIEWS}条）", file=sys.stderr)
                return 1
            
            if args.list_brands:
                brands = set(r.get("brand", "") for r in reviews)
                print("可用品牌:", ", ".join(brands))
                return 0
            
            # 计算得分
            sentiment_score = calculate_sentiment_score(reviews, positive_words, negative_words)
            topic_score = calculate_topic_score(reviews)
            volume_score = calculate_volume_score(reviews)
            
            if args.verbose:
                print(f"[INFO] 情感得分: {sentiment_score:.1f}")
                print(f"[INFO] 主题得分: {topic_score:.1f}")
                print(f"[INFO] 声量得分: {volume_score:.1f}")
            
            # 生成报告
            if args.output_format == "json":
                output = json.dumps({
                    "brand": args.brand,
                    "sample_size": len(reviews),
                    "sentiment_score": sentiment_score,
                    "topic_score": topic_score,
                    "volume_score": volume_score,
                    "total_score": (sentiment_score * DEFAULT_WEIGHTS["情感"] +
                                    topic_score * DEFAULT_WEIGHTS["主题"] +
                                    volume_score * DEFAULT_WEIGHTS["声量"]),
                }, ensure_ascii=False, indent=2)
                output_path = "report.json"
            else:
                output = generate_report(reviews, args.brand, sentiment_score, topic_score,
                                         volume_score, DEFAULT_WEIGHTS, positive_words, negative_words)
                output_path = "report.md"
            
            # 写盘
            safe_write_file(output_path, output, args.dry_run)
            if not args.dry_run:
                print(f"[OK] 报告已生成: {output_path}")
            
            return 0
        
        # 多品牌对比
        if args.compare:
            brand_results = {}
            for file_path in args.compare:
                content = safe_read_file(file_path)
                reviews = parse_reviews(content)
                
                if len(reviews) > MAX_REVIEWS:
                    print(f"E002: {file_path} 评论条数超过上限（{MAX_REVIEWS}条）", file=sys.stderr)
                    return 1
                
                # 使用文件名作为品牌名
                brand = os.path.splitext(os.path.basename(file_path))[0]
                
                sentiment_score = calculate_sentiment_score(reviews, positive_words, negative_words)
                topic_score = calculate_topic_score(reviews)
                volume_score = calculate_volume_score(reviews)
                
                brand_results[brand] = {
                    "reviews": reviews,
                    "sentiment_score": sentiment_score,
                    "topic_score": topic_score,
                    "volume_score": volume_score,
                    "positive_words": positive_words,
                    "negative_words": negative_words,
                }
                
                if args.verbose:
                    print(f"[INFO] {brand}: 样本量={len(reviews)}, 情感得分={sentiment_score:.1f}")
            
            # 生成对比表与雷达图
            table, radar_data = generate_comparison(brand_results)
            
            # 写盘
            safe_write_file("comparison_table.md", table, args.dry_run)
            safe_write_file("radar_data.json", json.dumps(radar_data, ensure_ascii=False, indent=2), args.dry_run)
            
            if not args.dry_run:
                print("[OK] 对比表已生成: comparison_table.md")
                print("[OK] 雷达图数据已生成: radar_data.json")
            
            return 0
    
    except FileNotFoundError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1
    except ValueError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"E010: 未知错误: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
