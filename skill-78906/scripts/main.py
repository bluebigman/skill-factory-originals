#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
skill-78906 起标题工具 - 独立实现脚本

功能：标题生成、优化、评分、合规检测、批量处理、结果输出
设计原则：clean-room 实现，仅依据功能规格，不参考任何既有代码
"""

import argparse
import csv
import difflib
import json
import os
import random
import re
import sys
import tempfile
from collections import OrderedDict
from pathlib import Path

# ============================================================
# 错误码定义
# ============================================================
ERROR_CODES = {
    "E001": "输入参数缺失或格式错误",
    "E002": "输入内容为空",
    "E003": "不支持的平台类型",
    "E004": "标题长度超出限制",
    "E005": "文件读取失败",
    "E006": "文件写入失败",
    "E007": "编码解析失败",
    "E008": "内部逻辑错误",
    "E009": "批量处理输入格式错误",
    "E010": "未知异常",
}

# ============================================================
# 内置数据：平台模板、评分模型、敏感词库
# ============================================================

PLATFORM_TEMPLATES = {
    "news": {
        "patterns": [
            "{keyword}：{value}，{impact}",
            "重磅！{keyword}{action}",
            "{keyword}迎来{value}大变局",
        ],
        "max_len": 30,
        "style": "客观陈述+数字冲击",
    },
    "wechat": {
        "patterns": [
            "{value}个{keyword}，第{num}个最{emotion}",
            "为什么{keyword}越来越{trend}？",
            "深度好文：{keyword}的{aspect}",
        ],
        "max_len": 20,
        "style": "悬念+共鸣",
    },
    "short_video": {
        "patterns": [
            "{num}秒看懂{keyword}",
            "千万别{action}，否则{result}",
            "{keyword}的{value}个真相",
        ],
        "max_len": 25,
        "style": "口语化+强悬念",
    },
    "ecommerce": {
        "patterns": [
            "{keyword}，{value}天无理由退换",
            "爆款{keyword}，限时{value}折",
            "{keyword}特惠，{value}件包邮",
        ],
        "max_len": 30,
        "style": "利益点+紧迫感",
    },
    "academic": {
        "patterns": [
            "基于{method}的{keyword}研究",
            "{keyword}的{aspect}：{finding}",
            "{keyword}研究综述与展望",
        ],
        "max_len": 25,
        "style": "严谨+关键词前置",
    },
    "ad": {
        "patterns": [
            "{value}%的人不知道的{keyword}真相",
            "用{keyword}，{value}天看到改变",
            "{keyword}限时特惠，{value}折起",
        ],
        "max_len": 20,
        "style": "数据驱动+效果承诺",
    },
}

FILLERS = {
    "value": ["3", "5", "7", "10", "99%", "100%"],
    "num": ["1", "2", "3", "5"],
    "emotion": ["扎心", "实用", "震撼", "意外"],
    "trend": ["流行", "火爆", "消失"],
    "action": ["错过", "踩坑", "忽略"],
    "result": ["后悔", "损失", "白干"],
    "method": ["深度学习", "大数据分析", "实证研究"],
    "aspect": ["现状与趋势", "关键因素", "实践路径"],
    "finding": ["新发现", "重要结论", "实证证据"],
    "impact": ["影响深远", "引发热议", "改变格局"],
}

# 敏感词库（示例，实际应更全面）
SENSITIVE_WORDS = [
    "最", "第一", "顶级", "极致", "绝对", "唯一", "独家",
    "国家级", "世界级", "全球首发", "全网最低", "销量第一",
    "根治", "治愈", "百分百", "包治", "无副作用",
]

# 情绪词库（用于吸引力评分）
EMOTION_WORDS = [
    "震惊", "震撼", "泪目", "感动", "愤怒", "惊喜",
    "扎心", "实用", "干货", "爆款", "神器", "秘诀",
]

# ============================================================
# 工具函数
# ============================================================

def safe_read_text(file_path, encodings=("utf-8", "gbk", "gb18030")):
    """安全读取文本文件，支持多编码尝试"""
    last_error = None
    for enc in encodings:
        try:
            with open(file_path, "r", encoding=enc, errors="replace") as f:
                return f.read()
        except (UnicodeDecodeError, IOError) as e:
            last_error = e
            continue
    raise IOError(f"E007: 无法解析文件编码 - {last_error}")


def safe_write_text(file_path, content, encoding="utf-8"):
    """安全写入文本文件"""
    try:
        with open(file_path, "w", encoding=encoding, errors="replace") as f:
            f.write(content)
    except IOError as e:
        raise IOError(f"E006: 文件写入失败 - {e}")


def parse_topic(content):
    """从输入内容中提取关键词和主题信息"""
    if not content or not content.strip():
        return {"keywords": [], "first_sentence": "", "content_length": 0}

    # 简单分词：按标点和空格切分，提取有意义的中文词
    text = content.strip()
    # 去除常见停用词
    stopwords = {"的", "了", "和", "是", "在", "有", "我", "你", "他", "她", "它", "这", "那", "也", "都", "就", "而", "及", "与", "或", "一个", "没有", "我们", "你们", "他们"}
    
    # 提取候选词：按标点切分后，取长度>=2的片段
    segments = re.split(r'[，。！？、；：""''（）\s]+', text)
    candidates = []
    for seg in segments:
        seg = seg.strip()
        if len(seg) >= 2 and seg not in stopwords:
            candidates.append(seg)
    
    # 取前5个作为关键词
    keywords = candidates[:5]
    first_sentence = segments[0][:30] if segments else ""
    
    return {
        "keywords": keywords,
        "first_sentence": first_sentence,
        "content_length": len(text),
    }


def validate_platform(platform):
    """校验平台类型是否支持"""
    if platform not in PLATFORM_TEMPLATES:
        raise ValueError(f"E003: 不支持的平台类型: {platform}，可选: {list(PLATFORM_TEMPLATES.keys())}")
    return platform


def validate_title_length(title, max_len):
    """校验标题长度"""
    if len(title) > max_len:
        raise ValueError(f"E004: 标题长度 {len(title)} 超过限制 {max_len}")
    return title


# ============================================================
# 核心逻辑：标题生成、评分、优化
# ============================================================

def generate_titles(topic_info, platform, count=10):
    """基于模板和关键词生成候选标题"""
    keywords = topic_info.get("keywords", [])
    if not keywords:
        # 无关键词时使用默认词
        keywords = ["主题"]
    
    templates = PLATFORM_TEMPLATES[platform]["patterns"]
    max_len = PLATFORM_TEMPLATES[platform]["max_len"]
    
    titles = []
    seen = set()
    
    # 为每个模板生成多个变体
    per_template = max(1, count // len(templates))
    for template in templates:
        for _ in range(per_template):
            # 随机选择关键词和填充词
            keyword = random.choice(keywords)
            filled = template
            for placeholder in re.findall(r'\{(\w+)\}', template):
                if placeholder == "keyword":
                    filled = filled.replace("{keyword}", keyword)
                elif placeholder in FILLERS:
                    filled = filled.replace("{" + placeholder + "}", random.choice(FILLERS[placeholder]))
            
            # 截断超长标题
            if len(filled) > max_len:
                filled = filled[:max_len]
            
            if filled not in seen:
                seen.add(filled)
                titles.append(filled)
    
    # 补充到目标数量
    while len(titles) < count:
        keyword = random.choice(keywords)
        template = random.choice(templates)
        filled = template.replace("{keyword}", keyword)
        for placeholder in re.findall(r'\{(\w+)\}', template):
            if placeholder in FILLERS:
                filled = filled.replace("{" + placeholder + "}", random.choice(FILLERS[placeholder]))
        if len(filled) > max_len:
            filled = filled[:max_len]
        if filled not in seen:
            seen.add(filled)
            titles.append(filled)
    
    return titles[:count]


def score_title(title, keywords, platform):
    """对标题进行多维度评分"""
    score = 0.0
    details = {}
    
    # 1. 吸引力评分（0-40分）
    attraction = 0
    # 情绪词加分
    for word in EMOTION_WORDS:
        if word in title:
            attraction += 5
    # 数字加分
    if re.search(r'\d', title):
        attraction += 5
    # 疑问句加分
    if "？" in title or "?" in title:
        attraction += 5
    # 长度适中加分（10-25字）
    if 10 <= len(title) <= 25:
        attraction += 5
    attraction = min(attraction, 40)
    score += attraction
    details["attraction"] = attraction
    
    # 2. SEO评分（0-30分）
    seo = 0
    for kw in keywords:
        if kw and kw in title:
            seo += 10
    seo = min(seo, 30)
    score += seo
    details["seo"] = seo
    
    # 3. 合规评分（0-30分）
    compliance = 30
    for word in SENSITIVE_WORDS:
        if word in title:
            compliance -= 10
    compliance = max(compliance, 0)
    score += compliance
    details["compliance"] = compliance
    
    return score, details


def optimize_title(title, keywords, platform):
    """优化已有标题，生成改进版本"""
    if not title or not title.strip():
        return []
    
    max_len = PLATFORM_TEMPLATES[platform]["max_len"]
    optimizations = []
    original = title.strip()
    
    # 优化1：添加数字增强
    if not re.search(r'\d', original):
        new_title = f"{random.choice(['3', '5', '7', '10'])}个{original}"
        if len(new_title) <= max_len:
            optimizations.append((new_title, "添加数字增强吸引力"))
    
    # 优化2：添加情绪词
    if not any(w in original for w in EMOTION_WORDS):
        emotion = random.choice(EMOTION_WORDS)
        new_title = f"{emotion}！{original}"
        if len(new_title) <= max_len:
            optimizations.append((new_title, "添加情绪词引发共鸣"))
    
    # 优化3：改为疑问句式
    if "？" not in original and "?" not in original:
        new_title = f"{original}？"
        if len(new_title) <= max_len:
            optimizations.append((new_title, "改为疑问句式增加互动"))
    
    # 优化4：添加关键词
    if keywords:
        kw = keywords[0]
        if kw not in original:
            new_title = f"{original}，{kw}"
            if len(new_title) <= max_len:
                optimizations.append((new_title, "添加核心关键词提升SEO"))
    
    return optimizations[:3]


def check_compliance(title):
    """检测标题中的敏感词"""
    violations = []
    for word in SENSITIVE_WORDS:
        if word in title:
            violations.append({
                "word": word,
                "suggestion": f"建议替换为更客观的表述，避免使用'{word}'"
            })
    return violations


# ============================================================
# 批量处理与输出
# ============================================================

def batch_process(items, platform, count_per_item=3):
    """批量处理多个标题主题"""
    if not items or not isinstance(items, list):
        raise ValueError("E009: 批量处理输入格式错误，需要列表")
    
    results = []
    for item in items:
        if not item or not item.strip():
            continue
        topic_info = parse_topic(item)
        titles = generate_titles(topic_info, platform, count=count_per_item)
        for title in titles:
            score, details = score_title(title, topic_info.get("keywords", []), platform)
            results.append({
                "topic": item,
                "title": title,
                "score": score,
                "platform": platform,
                "reason": f"吸引力{details['attraction']}分/SEO{details['seo']}分/合规{details['compliance']}分"
            })
    return results


def format_markdown(results, verbose=False):
    """格式化输出为 Markdown"""
    lines = ["# 标题生成结果\n"]
    lines.append("| 序号 | 标题 | 评分 | 适用平台 | 推荐理由 |")
    lines.append("|------|------|------|----------|----------|")
    
    for idx, r in enumerate(results, 1):
        lines.append(f"| {idx} | {r['title']} | {r['score']} | {r['platform']} | {r['reason']} |")
    
    if verbose:
        lines.append("\n## 详细评分明细\n")
        for idx, r in enumerate(results, 1):
            lines.append(f"### {idx}. {r['title']}")
            lines.append(f"- 主题: {r['topic']}")
            lines.append(f"- 评分: {r['score']}")
            lines.append(f"- 理由: {r['reason']}")
    
    return "\n".join(lines)


def format_csv(results):
    """格式化输出为 CSV 字符串"""
    output = []
    output.append("标题,评分,适用平台,推荐理由")
    for r in results:
        # 转义逗号
        title = r["title"].replace(",", "，")
        reason = r["reason"].replace(",", "，")
        output.append(f"{title},{r['score']},{r['platform']},{reason}")
    return "\n".join(output)


# ============================================================
# 自检模块
# ============================================================

def run_selftest():
    """内置自检：验证核心逻辑正确性"""
    print("=" * 60)
    print("开始自检 (selftest)")
    print("=" * 60)
    
    # 测试1：主题解析
    print("\n[测试1] 主题解析")
    content = "人工智能技术正在改变我们的生活，深度学习在医疗领域的应用尤为突出。"
    topic_info = parse_topic(content)
    assert len(topic_info["keywords"]) > 0, "关键词提取失败"
    assert topic_info["content_length"] > 0, "内容长度计算失败"
    print(f"  ✓ 关键词: {topic_info['keywords']}")
    print(f"  ✓ 首句: {topic_info['first_sentence'][:20]}...")
    
    # 测试2：标题生成
    print("\n[测试2] 标题生成")
    for platform in ["news", "wechat", "short_video", "ecommerce", "academic", "ad"]:
        titles = generate_titles(topic_info, platform, count=5)
        assert len(titles) == 5, f"{platform} 生成数量不足"
        assert all(len(t) > 0 for t in titles), f"{platform} 有空标题"
        print(f"  ✓ {platform}: {titles[0][:30]}...")
    
    # 测试3：评分功能
    print("\n[测试3] 标题评分")
    test_title = "3个AI改变医疗的真相，第2个最震撼！"
    score, details = score_title(test_title, ["AI", "医疗"], "wechat")
    assert score > 0, "评分应为正数"
    assert "attraction" in details and "seo" in details and "compliance" in details, "评分维度缺失"
    print(f"  ✓ 评分: {score} (吸引力:{details['attraction']}, SEO:{details['seo']}, 合规:{details['compliance']})")
    
    # 测试4：合规检测
    print("\n[测试4] 合规检测")
    bad_title = "全网最低价，绝对第一！"
    violations = check_compliance(bad_title)
    assert len(violations) > 0, "应检测到敏感词"
    print(f"  ✓ 检测到 {len(violations)} 个敏感词: {[v['word'] for v in violations]}")
    
    # 测试5：标题优化
    print("\n[测试5] 标题优化")
    original = "AI改变医疗"
    optimizations = optimize_title(original, ["AI", "医疗"], "wechat")
    assert len(optimizations) > 0, "应生成优化版本"
    print(f"  ✓ 优化版本数: {len(optimizations)}")
    for opt, reason in optimizations:
        print(f"    - {opt} ({reason})")
    
    # 测试6：批量处理
    print("\n[测试6] 批量处理")
    items = ["人工智能发展趋势", "健康饮食指南"]
    results = batch_process(items, "news", count_per_item=2)
    assert len(results) >= 2, "批量处理结果不足"
    print(f"  ✓ 批量生成 {len(results)} 条标题")
    
    # 测试7：空输入处理
    print("\n[测试7] 空输入处理")
    empty_info = parse_topic("")
    assert empty_info["keywords"] == [], "空输入应返回空关键词"
    print("  ✓ 空输入处理正常")
    
    # 测试8：超长标题处理
    print("\n[测试8] 超长标题处理")
    long_content = "这是一个非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常长的标题测试内容" * 3
    long_info = parse_topic(long_content)
    titles = generate_titles(long_info, "wechat", count=3)
    max_len = PLATFORM_TEMPLATES["wechat"]["max_len"]
    assert all(len(t) <= max_len for t in titles), "标题超出长度限制"
    print(f"  ✓ 超长输入处理正常，标题长度均 ≤ {max_len}")
    
    # 测试9：中文标点处理
    print("\n[测试9] 中文标点处理")
    punct_content = "你好，世界！这个问题很重要……"
    punct_info = parse_topic(punct_content)
    assert len(punct_info["keywords"]) > 0, "中文标点解析失败"
    print(f"  ✓ 中文标点处理正常")
    
    # 测试10：CSV格式化
    print("\n[测试10] CSV格式化")
    sample_results = [{"title": "测试标题", "score": 80, "platform": "news", "reason": "测试"}]
    csv_output = format_csv(sample_results)
    assert "测试标题" in csv_output, "CSV输出缺少标题"
    print("  ✓ CSV格式化正常")
    
    print("\n" + "=" * 60)
    print("自检全部通过！")
    print("=" * 60)
    return True


# ============================================================
# 主程序入口
# ============================================================

def main():
    """命令行入口"""
    parser = argparse.ArgumentParser(
        description="起标题工具 - 一站式标题生成与优化",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python main.py --content "人工智能发展趋势" --platform wechat
  python main.py --content "人工智能发展趋势" --platform news --count 15
  python main.py --optimize "AI改变医疗" --platform wechat
  python main.py --batch items.json --platform ecommerce
  python main.py --selftest
        """
    )
    
    # 输入参数
    parser.add_argument("--content", type=str, help="标题主题或内容摘要")
    parser.add_argument("--platform", type=str, default="wechat", 
                        choices=list(PLATFORM_TEMPLATES.keys()),
                        help="目标平台")
    parser.add_argument("--count", type=int, default=10, help="生成标题数量")
    parser.add_argument("--optimize", type=str, help="优化已有标题")
    parser.add_argument("--batch", type=str, help="批量处理JSON文件路径")
    parser.add_argument("--output", type=str, help="输出文件路径(Markdown)")
    parser.add_argument("--csv", type=str, help="输出CSV文件路径")
    parser.add_argument("--dry-run", action="store_true", help="仅预览不写文件")
    parser.add_argument("--force", action="store_true", help="强制写入文件")
    parser.add_argument("--verbose", action="store_true", help="输出详细决策信息")
    parser.add_argument("--selftest", action="store_true", help="运行自检")
    
    args = parser.parse_args()
    
    # 自检模式
    if args.selftest:
        try:
            run_selftest()
            return 0
        except AssertionError as e:
            print(f"E008: 自检失败 - {e}", file=sys.stderr)
            return 1
    
    # 检查输入
    if not args.content and not args.optimize and not args.batch:
        parser.print_help()
        print("\nE001: 请提供 --content 或 --optimize 或 --batch 参数", file=sys.stderr)
        return 1
    
    # 校验平台
    try:
        validate_platform(args.platform)
    except ValueError as e:
        print(f"{e}", file=sys.stderr)
        return 1
    
    # 校验数量
    if args.count < 1 or args.count > 50:
        print("E001: count 参数需在 1-50 之间", file=sys.stderr)
        return 1
    
    try:
        # 处理模式
        if args.optimize:
            # 优化模式
            print(f"优化标题: {args.optimize}")
            topic_info = parse_topic(args.optimize)
            optimizations = optimize_title(args.optimize, topic_info["keywords"], args.platform)
            
            if not optimizations:
                print("未生成优化版本，标题已是最优状态")
                return 0
            
            results = []
            for opt_title, reason in optimizations:
                score, details = score_title(opt_title, topic_info["keywords"], args.platform)
                results.append({
                    "topic": args.optimize,
                    "title": opt_title,
                    "score": score,
                    "platform": args.platform,
                    "reason": reason
                })
            
            if args.verbose:
                print("\n优化决策明细:")
                for r in results:
                    print(f"  - {r['title']}")
                    print(f"    理由: {r['reason']}")
                    print(f"    评分: {r['score']}")
            
            # 输出
            markdown = format_markdown(results, args.verbose)
            print("\n" + markdown)
            
            # 写入文件
            if args.output:
                dry = not args.force
                if dry:
                    print(f"\n[dry-run] 将写入文件: {args.output}")
                else:
                    safe_write_text(args.output, markdown)
                    print(f"\n已写入: {args.output}")
            
            if args.csv:
                csv_content = format_csv(results)
                dry = not args.force
                if dry:
                    print(f"[dry-run] 将写入CSV: {args.csv}")
                else:
                    safe_write_text(args.csv, csv_content)
                    print(f"已写入CSV: {args.csv}")
            
        elif args.batch:
            # 批量模式
            try:
                batch_content = safe_read_text(args.batch)
                items = json.loads(batch_content)
                if not isinstance(items, list):
                    raise ValueError("批量文件需为JSON数组")
            except (IOError, json.JSONDecodeError) as e:
                print(f"E005: 批量文件读取失败 - {e}", file=sys.stderr)
                return 1
            
            print(f"批量处理 {len(items)} 个主题...")
            results = batch_process(items, args.platform, count_per_item=3)
            
            if args.verbose:
                print(f"\n共生成 {len(results)} 条标题")
                for r in results[:5]:
                    print(f"  - [{r['score']}分] {r['title']} ({r['platform']})")
                if len(results) > 5:
                    print(f"  ... 等共 {len(results)} 条")
            
            # 输出
            markdown = format_markdown(results, args.verbose)
            print("\n" + markdown)
            
            if args.output:
                dry = not args.force
                if dry:
                    print(f"\n[dry-run] 将写入文件: {args.output}")
                else:
                    safe_write_text(args.output, markdown)
                    print(f"\n已写入: {args.output}")
            
            if args.csv:
                csv_content = format_csv(results)
                dry = not args.force
                if dry:
                    print(f"[dry-run] 将写入CSV: {args.csv}")
                else:
                    safe_write_text(args.csv, csv_content)
                    print(f"已写入CSV: {args.csv}")
        
        else:
            # 生成模式
            print(f"生成标题 (平台: {args.platform}, 数量: {args.count})")
            topic_info = parse_topic(args.content)
            
            if args.verbose:
                print(f"关键词: {topic_info['keywords']}")
                print(f"内容长度: {topic_info['content_length']}")
            
            titles = generate_titles(topic_info, args.platform, count=args.count)
            
            results = []
            for title in titles:
                score, details = score_title(title, topic_info["keywords"], args.platform)
                results.append({
                    "topic": args.content[:30],
                    "title": title,
                    "score": score,
                    "platform": args.platform,
                    "reason": f"吸引力{details['attraction']}分/SEO{details['seo']}分/合规{details['compliance']}分"
                })
            
            # 按评分排序
            results.sort(key=lambda x: x["score"], reverse=True)
            
            if args.verbose:
                print("\n生成决策明细:")
                for r in results:
                    print(f"  - [{r['score']}分] {r['title']}")
                    print(f"    理由: {r['reason']}")
            
            # 输出
            markdown = format_markdown(results, args.verbose)
            print("\n" + markdown)
            
            # 写入文件
            if args.output:
                dry = not args.force
                if dry:
                    print(f"\n[dry-run] 将写入文件: {args.output}")
                else:
                    safe_write_text(args.output, markdown)
                    print(f"\n已写入: {args.output}")
            
            if args.csv:
                csv_content = format_csv(results)
                dry = not args.force
                if dry:
                    print(f"[dry-run] 将写入CSV: {args.csv}")
                else:
                    safe_write_text(args.csv, csv_content)
                    print(f"已写入CSV: {args.csv}")
        
        return 0
    
    except ValueError as e:
        print(f"{e}", file=sys.stderr)
        return 1
    except IOError as e:
        print(f"{e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"E010: 未知异常 - {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
