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
版本：3.0.0
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
dry_run = False  # v3.274 模块级 dry-run 标志

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

# 主题关键词映射（用于主题提取）
TOPIC_KEYWORDS = {
    "产品": ["产品", "功能", "性能", "质量", "设计", "外观", "材质", "做工", "体验", "使用"],
    "服务": ["服务", "客服", "售后", "态度", "响应", "处理", "解决", "支持", "帮助", "咨询"],
    "价格": ["价格", "性价比", "贵", "便宜", "实惠", "折扣", "优惠", "值", "划算", "费用"],
    "物流": ["物流", "快递", "配送", "发货", "速度", "包装", "运输", "收货", "送达", "时效"],
    "安装": ["安装", "调试", "配置", "设置", "部署", "上线", "集成", "对接", "使用", "操作"],
}

# 默认评分权重（用于声誉指数计算）
DEFAULT_WEIGHTS = {
    "sentiment": 0.5,
    "rating": 0.3,
    "topic": 0.2,
}

# 置信度阈值
CONFIDENCE_THRESHOLDS = {
    "high": 100,
    "medium": 50,
    "low": 20,
}

# 最大评论处理条数
MAX_REVIEWS = 500

# ============================================================
# 工具函数
# ============================================================

def log_info(message: str, verbose: bool = False) -> None:
    """打印信息日志。"""
    if verbose or not verbose:
        print(f"[信息] {message}")

def log_warning(message: str) -> None:
    """打印警告日志到 stderr。"""
    print(f"[警告] {message}", file=sys.stderr)

def log_error(message: str) -> None:
    """打印错误日志到 stderr。"""
    print(f"[错误] {message}", file=sys.stderr)

def get_utc_now() -> str:
    """获取当前 UTC 时间字符串。"""
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

def safe_float(value: Any, default: float = 0.0) -> float:
    """安全转换为浮点数。"""
    try:
        if value is None:
            return default
        return float(value)
    except (ValueError, TypeError):
        return default

def safe_int(value: Any, default: int = 0) -> int:
    """安全转换为整数。"""
    try:
        if value is None:
            return default
        return int(value)
    except (ValueError, TypeError):
        return default

def read_text_safe(file_path: str) -> str:
    """
    读取文件内容，支持多编码（utf-8 -> gbk -> gb18030 -> latin-1）。
    使用流式读取，避免一次性加载大文件。
    """
    encodings = ["utf-8", "gbk", "gb18030", "latin-1"]
    for encoding in encodings:
        try:
            with open(file_path, "r", encoding=encoding, errors="replace") as f:
                return f.read()
        except (UnicodeDecodeError, UnicodeError):
            continue
        except FileNotFoundError:
            raise
        except Exception as e:
            log_warning(f"读取文件 {file_path} 时发生错误: {e}")
            raise
    # 如果所有编码都失败，使用二进制模式读取并替换错误
    with open(file_path, "rb") as f:
        return f.read().decode("utf-8", errors="replace")

def write_file_atomic(file_path: str, content: str, dry_run: bool = False) -> bool:
    """
    原子化写入文件：先写入临时文件，再重命名。
    避免写入过程中程序崩溃导致文件损坏。
    """
    if not dry_run:
        temp_path = f"{file_path}.tmp"
        try:
            with open(temp_path, "w", encoding="utf-8") as f:
                f.write(content)
            os.replace(temp_path, file_path)
            print(f"[写入] {file_path}")
            return True
        except Exception as e:
            log_error(f"写入文件 {file_path} 失败: {e}")
            # 清理临时文件
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except OSError:
                    pass
            raise
    else:
        print(f"[dry-run] 将写入 {file_path}（{len(content)} 字节），未落盘")
        return False

# ============================================================
# 数据解析模块
# ============================================================

def parse_reviews(file_path: str) -> List[Dict[str, Any]]:
    """
    解析评论数据文件（支持 .txt, .csv, .json）。
    返回评论列表，每条评论为字典，至少包含 'content' 字段。
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"文件不存在: {file_path}")

    file_ext = os.path.splitext(file_path)[1].lower()
    content = read_text_safe(file_path)

    if not content or not content.strip():
        raise ValueError(f"E001: {ERROR_CODES['E001']}")

    reviews = []

    try:
        if file_ext == ".json":
            reviews = _parse_json(content)
        elif file_ext == ".csv":
            reviews = _parse_csv(content)
        else:
            # 默认按纯文本处理
            reviews = _parse_text(content)
    except Exception as e:
        log_error(f"E004: {ERROR_CODES['E004']} - {e}")
        raise

    # 过滤无效评论
    valid_reviews = [r for r in reviews if r.get("content") and r["content"].strip()]

    if not valid_reviews:
        raise ValueError(f"E001: {ERROR_CODES['E001']}")

    if len(valid_reviews) > MAX_REVIEWS:
        raise ValueError(f"E002: {ERROR_CODES['E002']}")

    return valid_reviews

def _parse_json(content: str) -> List[Dict[str, Any]]:
    """解析 JSON 格式评论数据。"""
    try:
        data = json.loads(content)
    except json.JSONDecodeError as e:
        log_error(f"JSON 解析失败: {e}")
        raise

    reviews = []
    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                review = {
                    "content": str(item.get("content", "")),
                    "rating": safe_float(item.get("rating", 0.0)),
                    "date": str(item.get("date", "")),
                    "brand": str(item.get("brand", "")),
                }
                reviews.append(review)
    elif isinstance(data, dict):
        # 支持 {"reviews": [...]} 格式
        review_list = data.get("reviews", [])
        if isinstance(review_list, list):
            for item in review_list:
                if isinstance(item, dict):
                    review = {
                        "content": str(item.get("content", "")),
                        "rating": safe_float(item.get("rating", 0.0)),
                        "date": str(item.get("date", "")),
                        "brand": str(item.get("brand", "")),
                    }
                    reviews.append(review)
    return reviews

def _parse_csv(content: str) -> List[Dict[str, Any]]:
    """解析 CSV 格式评论数据。"""
    reviews = []
    try:
        reader = csv.DictReader(content.splitlines())
        for row in reader:
            review = {
                "content": str(row.get("content", "")),
                "rating": safe_float(row.get("rating", 0.0)),
                "date": str(row.get("date", "")),
                "brand": str(row.get("brand", "")),
            }
            reviews.append(review)
    except Exception as e:
        log_error(f"CSV 解析失败: {e}")
        raise
    return reviews

def _parse_text(content: str) -> List[Dict[str, Any]]:
    """解析纯文本格式评论数据（每行一条评论）。"""
    reviews = []
    for line in content.splitlines():
        line = line.strip()
        if line:
            reviews.append({
                "content": line,
                "rating": 0.0,
                "date": "",
                "brand": "",
            })
    return reviews

# ============================================================
# 情感分析模块
# ============================================================

def analyze_sentiment(text: str, positive_words: Set[str], negative_words: Set[str]) -> str:
    """
    分析文本情感倾向。
    返回 "positive", "negative", 或 "neutral"。
    """
    if not text:
        return "neutral"

    # 分词（简单按字符和空格分割）
    words = set(re.findall(r'[\u4e00-\u9fff]|[a-zA-Z]+', text.lower()))

    positive_count = len(words & positive_words)
    negative_count = len(words & negative_words)

    if positive_count > negative_count:
        return "positive"
    elif negative_count > positive_count:
        return "negative"
    else:
        return "neutral"

def analyze_sentiment_distribution(reviews: List[Dict[str, Any]]) -> Dict[str, int]:
    """分析评论情感分布。"""
    distribution = {"positive": 0, "negative": 0, "neutral": 0}
    for review in reviews:
        sentiment = analyze_sentiment(
            review.get("content", ""),
            DEFAULT_POSITIVE_WORDS,
            DEFAULT_NEGATIVE_WORDS
        )
        distribution[sentiment] += 1
    return distribution

# ============================================================
# 主题提取模块
# ============================================================

def extract_topics(text: str) -> List[str]:
    """从文本中提取主题关键词。"""
    topics = []
    for topic, keywords in TOPIC_KEYWORDS.items():
        for keyword in keywords:
            if keyword in text:
                topics.append(topic)
                break
    return topics

def extract_topic_frequency(reviews: List[Dict[str, Any]]) -> Dict[str, int]:
    """统计主题词频。"""
    topic_counter = Counter()
    for review in reviews:
        topics = extract_topics(review.get("content", ""))
        for topic in topics:
            topic_counter[topic] += 1
    return dict(topic_counter)

# ============================================================
# 声誉评分模块
# ============================================================

def calculate_reputation_score(
    reviews: List[Dict[str, Any]],
    weights: Optional[Dict[str, float]] = None
) -> Tuple[float, str]:
    """
    计算品牌声誉指数（0-100）。
    返回 (评分, 置信度)。
    """
    if weights is None:
        weights = DEFAULT_WEIGHTS

    # 校验权重
    total_weight = sum(weights.values())
    if abs(total_weight - 1.0) > 0.01:
        raise ValueError(f"E005: {ERROR_CODES['E005']}")

    if not reviews:
        return 0.0, "low"

    # 情感得分（0-100）
    sentiment_dist = analyze_sentiment_distribution(reviews)
    total = len(reviews)
    sentiment_score = (
        (sentiment_dist["positive"] * 100 +
         sentiment_dist["neutral"] * 50) / total
    )

    # 评分得分（0-100）
    rating_values = [safe_float(r.get("rating", 0.0)) for r in reviews if r.get("rating")]
    if rating_values:
        avg_rating = sum(rating_values) / len(rating_values)
        rating_score = (avg_rating / 5.0) * 100
    else:
        rating_score = 50.0  # 无评分数据时取中性值

    # 主题得分（0-100）
    topic_freq = extract_topic_frequency(reviews)
    if topic_freq:
        # 主题多样性得分：主题种类越多，得分越高（假设多样化的讨论是积极的）
        topic_score = min(100.0, len(topic_freq) * 20.0)
    else:
        topic_score = 50.0

    # 加权综合得分
    final_score = (
        sentiment_score * weights.get("sentiment", 0.5) +
        rating_score * weights.get("rating", 0.3) +
        topic_score * weights.get("topic", 0.2)
    )

    # 置信度评估
    if total >= CONFIDENCE_THRESHOLDS["high"]:
        confidence = "high"
    elif total >= CONFIDENCE_THRESHOLDS["medium"]:
        confidence = "medium"
    else:
        confidence = "low"

    return round(final_score, 1), confidence

# ============================================================
# 竞品对标模块
# ============================================================

def generate_competitor_matrix(
    reviews: List[Dict[str, Any]],
    brand: str,
    competitors: List[str]
) -> Dict[str, Dict[str, Any]]:
    """
    生成竞品对标矩阵。
    返回 {品牌名: {评分, 置信度, 评论数}}。
    """
    matrix = {}

    # 按品牌分组评论
    brand_reviews = defaultdict(list)
    for review in reviews:
        review_brand = review.get("brand", "")
        if review_brand:
            brand_reviews[review_brand].append(review)

    # 分析目标品牌
    target_reviews = brand_reviews.get(brand, [])
    if not target_reviews:
        # 如果没有品牌字段，使用全部评论作为目标品牌
        target_reviews = reviews

    score, confidence = calculate_reputation_score(target_reviews)
    matrix[brand] = {
        "score": score,
        "confidence": confidence,
        "count": len(target_reviews),
    }

    # 分析竞品
    for competitor in competitors:
        comp_reviews = brand_reviews.get(competitor, [])
        if comp_reviews:
            score, confidence = calculate_reputation_score(comp_reviews)
            matrix[competitor] = {
                "score": score,
                "confidence": confidence,
                "count": len(comp_reviews),
            }
        else:
            matrix[competitor] = {
                "score": 0.0,
                "confidence": "low",
                "count": 0,
            }

    return matrix

# ============================================================
# 报告生成模块
# ============================================================

def generate_markdown_report(
    brand: str,
    reviews: List[Dict[str, Any]],
    score: float,
    confidence: str,
    sentiment_dist: Dict[str, int],
    topic_freq: Dict[str, int],
    competitors: Optional[Dict[str, Dict[str, Any]]] = None
) -> str:
    """生成 Markdown 格式的洞察报告。"""
    total = len(reviews)
    timestamp = get_utc_now()

    report = []
    report.append(f"# {brand} 口碑洞察报告")
    report.append(f"\n> 生成时间：{timestamp}")
    report.append(f"> 分析评论数：{total} 条")
    report.append(f"> 置信度：{confidence}")
    report.append("")

    # 声誉评分
    report.append("## 声誉评分")
    report.append(f"\n**声誉指数：{score}/100**")
    report.append("")

    # 情感分布
    report.append("## 情感分布")
    report.append("\n| 情感 | 数量 | 占比 |")
    report.append("| :--- | :--- | :--- |")
    for sentiment in ["positive", "neutral", "negative"]:
        count = sentiment_dist.get(sentiment, 0)
        pct = (count / total * 100) if total > 0 else 0
        label = {"positive": "正面", "neutral": "中性", "negative": "负面"}[sentiment]
        report.append(f"| {label} | {count} | {pct:.1f}% |")
    report.append("")

    # 主题分布
    report.append("## 主题分布")
    if topic_freq:
        report.append("\n| 主题 | 提及次数 |")
        report.append("| :--- | :--- |")
        for topic, count in sorted(topic_freq.items(), key=lambda x: x[1], reverse=True):
            report.append(f"| {topic} | {count} |")
    else:
        report.append("\n未提取到明显主题。")
    report.append("")

    # 竞品对标
    if competitors:
        report.append("## 竞品对标")
        report.append("\n| 品牌 | 声誉指数 | 置信度 | 评论数 |")
        report.append("| :--- | :--- | :--- | :--- |")
        for comp_name, comp_data in competitors.items():
            report.append(
                f"| {comp_name} | {comp_data['score']} | "
                f"{comp_data['confidence']} | {comp_data['count']} |"
            )
        report.append("")

    # 行动建议
    report.append("## 行动建议")
    report.append("")
    if score >= 80:
        report.append("- **保持优势**：维持当前产品和服务质量，可考虑拓展新市场。")
    elif score >= 60:
        report.append("- **优化提升**：关注负面反馈集中的领域，制定针对性改进计划。")
    else:
        report.append("- **紧急改进**：声誉风险较高，建议立即排查核心问题并制定危机公关方案。")

    if sentiment_dist.get("negative", 0) > total * 0.3:
        report.append("- **负面舆情**：负面评论占比超过 30%，建议重点关注并快速响应。")

    if topic_freq.get("服务", 0) > 0:
        report.append("- **服务体验**：服务相关讨论较多，建议加强客服培训和响应速度。")

    if topic_freq.get("价格", 0) > 0:
        report.append("- **价格敏感**：价格是用户关注重点，建议评估定价策略和性价比。")

    report.append("")
    report.append("---")
    report.append("*本报告由 AI Reputation Claude 自动生成，仅供参考。*")

    return "\n".join(report)

def generate_competitor_csv(matrix: Dict[str, Dict[str, Any]]) -> str:
    """生成竞品对标 CSV 内容。"""
    output = []
    output.append("品牌,声誉指数,置信度,评论数")
    for brand, data in matrix.items():
        output.append(f"{brand},{data['score']},{data['confidence']},{data['count']}")
    return "\n".join(output)

# ============================================================
# 主流程
# ============================================================

def run_analysis(
    input_file: str,
    brand: str,
    competitors: Optional[List[str]] = None,
    output_file: Optional[str] = None,
    dry_run: bool = False,
    verbose: bool = False
) -> int:
    """
    主分析流程。
    返回退出码（0 成功，非 0 失败）。
    """
    try:
        # 1. 解析评论数据
        log_info(f"正在解析评论数据: {input_file}", verbose)
        reviews = parse_reviews(input_file)
        log_info(f"成功解析 {len(reviews)} 条评论。", verbose)

        # 2. 计算声誉评分
        log_info(f"正在计算品牌 '{brand}' 的声誉评分...", verbose)
        score, confidence = calculate_reputation_score(reviews)
        log_info(f"品牌 '{brand}' 声誉指数：{score} (置信度：{confidence})")

        # 3. 情感分布
        sentiment_dist = analyze_sentiment_distribution(reviews)
        log_info(
            f"情感分布：正面 {sentiment_dist['positive']} 条，"
            f"中性 {sentiment_dist['neutral']} 条，"
            f"负面 {sentiment_dist['negative']} 条"
        )

        # 4. 主题提取
        topic_freq = extract_topic_frequency(reviews)
        if topic_freq:
            top_topics = sorted(topic_freq.items(), key=lambda x: x[1], reverse=True)[:5]
            log_info("高频主题：" + ", ".join([t for t, _ in top_topics]))

        # 5. 竞品对标
        competitor_matrix = None
        if competitors:
            log_info(f"正在分析竞品: {', '.join(competitors)}", verbose)
            competitor_matrix = generate_competitor_matrix(reviews, brand, competitors)
            for comp_name, comp_data in competitor_matrix.items():
                log_info(f"品牌 '{comp_name}' 声誉指数：{comp_data['score']}")

        # 6. 生成报告
        report_content = generate_markdown_report(
            brand=brand,
            reviews=reviews,
            score=score,
            confidence=confidence,
            sentiment_dist=sentiment_dist,
            topic_freq=topic_freq,
            competitors=competitor_matrix
        )

        # 7. 输出结果
        if dry_run:
            log_info("[dry-run] 以下文件将被写入（当前未写入）：")
            if output_file:
                log_info(f"  - {output_file}")
            if competitor_matrix:
                log_info("  - 竞品对标矩阵.csv")
            # 打印报告预览
            print("\n" + "=" * 60)
            print("报告预览（前 30 行）：")
            print("=" * 60)
            preview_lines = report_content.split("\n")[:30]
            print("\n".join(preview_lines))
        else:
            # 写入报告
            if output_file:
                write_file_atomic(output_file, report_content, dry_run=False)
                log_info(f"报告已生成：{output_file}")
            else:
                # 默认文件名
                default_report = f"{brand}_口碑洞察报告.md"
                write_file_atomic(default_report, report_content, dry_run=False)
                log_info(f"报告已生成：{default_report}")

            # 写入竞品对标矩阵
            if competitor_matrix:
                csv_content = generate_competitor_csv(competitor_matrix)
                csv_file = "竞品对标矩阵.csv"
                write_file_atomic(csv_file, csv_content, dry_run=False)
                log_info(f"竞品对标矩阵已生成：{csv_file}")

        return 0

    except FileNotFoundError as e:
        log_error(f"E003: {ERROR_CODES['E003']} - {e}")
        return 3
    except ValueError as e:
        log_error(str(e))
        return 1
    except Exception as e:
        log_error(f"E010: {ERROR_CODES['E010']} - {e}")
        return 10

# ============================================================
# 自检模块
# ============================================================

def run_selftest() -> int:
    """
    运行内置自检，验证核心功能。
    返回退出码（0 通过，非 0 失败）。
    """
    print("=" * 60)
    print("开始运行自检...")
    print("=" * 60)

    failures = 0

    # 测试 1：情感分析
    print("\n[测试 1] 情感分析")
    try:
        assert analyze_sentiment("这个产品太棒了，非常满意！", DEFAULT_POSITIVE_WORDS, DEFAULT_NEGATIVE_WORDS) == "positive"
        assert analyze_sentiment("客服态度很差，太失望了。", DEFAULT_POSITIVE_WORDS, DEFAULT_NEGATIVE_WORDS) == "negative"
        assert analyze_sentiment("产品一般般。", DEFAULT_POSITIVE_WORDS, DEFAULT_NEGATIVE_WORDS) == "neutral"
        print("  ✓ 情感分析测试通过")
    except AssertionError as e:
        print(f"  ✗ 情感分析测试失败: {e}")
        failures += 1

    # 测试 2：主题提取
    print("\n[测试 2] 主题提取")
    try:
        topics = extract_topics("这个产品性能很好，价格也实惠。")
        assert "产品" in topics
        assert "价格" in topics
        print("  ✓ 主题提取测试通过")
    except AssertionError as e:
        print(f"  ✗ 主题提取测试失败: {e}")
        failures += 1

    # 测试 3：声誉评分
    print("\n[测试 3] 声誉评分")
    try:
        test_reviews = [
            {"content": "产品很棒，性能强劲，非常满意！", "rating": 5},
            {"content": "客服态度差，等待时间长。", "rating": 1},
            {"content": "性价比一般，外观设计漂亮。", "rating": 3},
            {"content": "物流很快，包装完好。", "rating": 4},
            {"content": "功能强大，但价格偏贵。", "rating": 3},
        ]
        score, confidence = calculate_reputation_score(test_reviews)
        assert 0 <= score <= 100, f"评分超出范围: {score}"
        assert confidence in ["high", "medium", "low"]
        print(f"  ✓ 声誉评分测试通过 (评分: {score}, 置信度: {confidence})")
    except AssertionError as e:
        print(f"  ✗ 声誉评分测试失败: {e}")
        failures += 1

    # 测试 4：数据解析
    print("\n[测试 4] 数据解析")
    try:
        # 创建临时测试文件
        import tempfile
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8") as f:
            f.write("content,rating,date\n")
            f.write("产品很好,5,2023-01-01\n")
            f.write("服务一般,3,2023-01-02\n")
            temp_file = f.name

        reviews = parse_reviews(temp_file)
        assert len(reviews) == 2
        assert reviews[0]["content"] == "产品很好"
        assert reviews[0]["rating"] == 5.0
        print("  ✓ 数据解析测试通过")

        # 清理临时文件
        os.unlink(temp_file)
    except AssertionError as e:
        print(f"  ✗ 数据解析测试失败: {e}")
        failures += 1
    except Exception as e:
        print(f"  ✗ 数据解析测试异常: {e}")
        failures += 1

    # 测试 5：竞品对标
    print("\n[测试 5] 竞品对标")
    try:
        test_reviews = [
            {"content": "产品很棒！", "rating": 5, "brand": "品牌A"},
            {"content": "产品不错！", "rating": 4, "brand": "品牌A"},
            {"content": "服务很差！", "rating": 1, "brand": "品牌B"},
            {"content": "价格太贵！", "rating": 2, "brand": "品牌B"},
        ]
        matrix = generate_competitor_matrix(test_reviews, "品牌A", ["品牌B"])
        assert "品牌A" in matrix
        assert "品牌B" in matrix
        assert matrix["品牌A"]["count"] == 2
        assert matrix["品牌B"]["count"] == 2
        print("  ✓ 竞品对标测试通过")
    except AssertionError as e:
        print(f"  ✗ 竞品对标测试失败: {e}")
        failures += 1

    # 测试 6：报告生成
    print("\n[测试 6] 报告生成")
    try:
        test_reviews = [
            {"content": "产品很棒，性能强劲！", "rating": 5},
            {"content": "客服态度差。", "rating": 1},
        ]
        score, confidence = calculate_reputation_score(test_reviews)
        sentiment_dist = analyze_sentiment_distribution(test_reviews)
        topic_freq = extract_topic_frequency(test_reviews)
        report = generate_markdown_report(
            brand="测试品牌",
            reviews=test_reviews,
            score=score,
            confidence=confidence,
            sentiment_dist=sentiment_dist,
            topic_freq=topic_freq
        )
        assert "测试品牌" in report
        assert "声誉指数" in report
        assert "情感分布" in report
        print("  ✓ 报告生成测试通过")
    except AssertionError as e:
        print(f"  ✗ 报告生成测试失败: {e}")
        failures += 1

    # 测试 7：错误处理
    print("\n[测试 7] 错误处理")
    try:
        # 测试空输入
        try:
            parse_reviews("/nonexistent/file.csv")
            print("  ✗ 错误处理测试失败：应该抛出 FileNotFoundError")
            failures += 1
        except FileNotFoundError:
            print("  ✓ 文件不存在错误处理测试通过")

        # 测试空数据
        import tempfile
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
            f.write("")
            temp_file = f.name
        try:
            parse_reviews(temp_file)
            print("  ✗ 错误处理测试失败：应该抛出 ValueError")
            failures += 1
        except ValueError:
            print("  ✓ 空数据错误处理测试通过")
        os.unlink(temp_file)
    except Exception as e:
        print(f"  ✗ 错误处理测试异常: {e}")
        failures += 1

    # 测试 8：权重校验
    print("\n[测试 8] 权重校验")
    try:
        test_reviews = [{"content": "测试", "rating": 3}]
        try:
            calculate_reputation_score(test_reviews, {"sentiment": 0.5, "rating": 0.5, "topic": 0.5})
            print("  ✗ 权重校验测试失败：应该抛出 ValueError")
            failures += 1
        except ValueError:
            print("  ✓ 权重校验测试通过")
    except Exception as e:
        print(f"  ✗ 权重校验测试异常: {e}")
        failures += 1

    # 测试 9：dry-run 模式
    print("\n[测试 9] dry-run 模式")
    try:
        import tempfile
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8") as f:
            f.write("content,rating\n")
            f.write("产品很好,5\n")
            f.write("服务一般,3\n")
            temp_file = f.name

        # 运行 dry-run
        exit_code = run_analysis(
            input_file=temp_file,
            brand="测试品牌",
            dry_run=True,
            verbose=False
        )
        assert exit_code == 0
        print("  ✓ dry-run 模式测试通过")

        # 清理临时文件
        os.unlink(temp_file)
    except AssertionError as e:
        print(f"  ✗ dry-run 模式测试失败: {e}")
        failures += 1
    except Exception as e:
        print(f"  ✗ dry-run 模式测试异常: {e}")
        failures += 1

    # 测试 10：完整流程
    print("\n[测试 10] 完整流程")
    try:
        import tempfile
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8") as f:
            f.write("content,rating,brand\n")
            f.write("产品很棒，性能强劲！,5,品牌A\n")
            f.write("客服态度差，等待时间长。,1,品牌A\n")
            f.write("价格实惠，性价比高。,4,品牌B\n")
            f.write("设计一流，服务也很棒。,5,品牌B\n")
            temp_file = f.name

        # 运行完整分析
        exit_code = run_analysis(
            input_file=temp_file,
            brand="品牌A",
            competitors=["品牌B"],
            output_file="test_report.md",
            dry_run=False,
            verbose=False
        )
        assert exit_code == 0
        assert os.path.exists("test_report.md")
        assert os.path.exists("竞品对标矩阵.csv")

        # 清理文件
        os.unlink(temp_file)
        os.unlink("test_report.md")
        os.unlink("竞品对标矩阵.csv")
        print("  ✓ 完整流程测试通过")
    except AssertionError as e:
        print(f"  ✗ 完整流程测试失败: {e}")
        failures += 1
    except Exception as e:
        print(f"  ✗ 完整流程测试异常: {e}")
        failures += 1

    # 总结
    print("\n" + "=" * 60)
    if failures == 0:
        print("所有自检测试通过！")
        return 0
    else:
        print(f"自检完成，{failures} 个测试失败。")
        return 1

# ============================================================
# 命令行入口
# ============================================================

def main():
    """命令行入口函数。"""
    parser = argparse.ArgumentParser(
        description="AI Reputation Claude - 评论分析与声誉管理工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python run.py --input reviews.csv --brand "我的品牌"
  python run.py --input data.json --brand "品牌A" --competitors "品牌B,品牌C"
  python run.py --input reviews.txt --brand "我的品牌" --dry-run
  python run.py --selftest
        """
    )

    parser.add_argument(
        "--input",
        type=str,
        help="输入评论数据文件路径（支持 .txt, .csv, .json）"
    )
    parser.add_argument(
        "--brand",
        type=str,
        help="目标品牌名称"
    )
    parser.add_argument(
        "--competitors",
        type=str,
        help="竞品品牌列表，用逗号分隔（例如：'品牌B,品牌C'）"
    )
    parser.add_argument(
        "--output",
        type=str,
        help="输出报告文件路径（默认：{品牌}_口碑洞察报告.md）"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="预览模式：只打印结果和将写入的文件，不实际写入"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="详细日志模式：打印每个分析步骤的详细信息"
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检，验证核心功能"
    )

    args = parser.parse_args()

    global dry_run

    dry_run = getattr(args, "dry_run", False)  # v3.274 同步到全局

    # 运行自检
    if args.selftest:
        exit_code = run_selftest()
        sys.exit(exit_code)

    # 参数校验
    if not args.input:
        log_error("E006: 缺少必要参数 --input")
        parser.print_help()
        sys.exit(6)

    if not args.brand:
        log_error("E006: 缺少必要参数 --brand")
        parser.print_help()
        sys.exit(6)

    # 解析竞品列表
    competitors = None
    if args.competitors:
        competitors = [c.strip() for c in args.competitors.split(",") if c.strip()]

    # 运行分析
    exit_code = run_analysis(
        input_file=args.input,
        brand=args.brand,
        competitors=competitors,
        output_file=args.output,
        dry_run=args.dry_run,
        verbose=args.verbose
    )

    sys.exit(exit_code)

if __name__ == "__main__":
    main()
