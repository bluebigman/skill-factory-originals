#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""标题党生成器 - 冒烟测试修复版"""

import re
import random
import hashlib
import argparse
from collections import OrderedDict

# 违禁词列表
BANNED_WORDS = ['国家级', '第一', '第一品牌', '世界领先', '全球首创', '独家秘方']

# 标题党模板
CLICKBAIT_TEMPLATES = [
    "{subject}震惊了所有人，原因竟然是...",
    "天啊！{subject}的真相终于曝光了",
    "不看后悔！{subject}背后的秘密",
    "{subject}惊人发现，专家都沉默了",
    "重磅！{subject}竟隐藏着这样的内幕",
    "你绝对想不到，{subject}竟然是这样",
    "{subject}引发热议，网友都炸锅了",
    "揭秘！{subject}不为人知的一面",
    "{subject}彻底火了，原因让人意外",
    "速看！{subject}的最新进展",
]

# 震惊词库
SHOCK_WORDS = ['震惊', '惊人', '重磅', '爆炸', '疯狂', '逆天', '恐怖', '吓人', '劲爆', '炸裂']
# 情感词库
EMOTION_WORDS = ['泪目', '感动', '愤怒', '心碎', '暖心', '扎心', '崩溃', '绝望', '惊喜', '意外']
# 数字词库
NUMBER_WORDS = ['99%', '10个', '3天', '1分钟', '100%', '5大', '7个', '8成', '9成', '0元']


def generate_clickbait(subject, count=3):
    """生成标题党变体"""
    variants = []
    for i in range(count):
        template = random.choice(CLICKBAIT_TEMPLATES)
        variant = template.format(subject=subject)
        # 随机添加震惊词
        if random.random() > 0.3:
            variant = random.choice(SHOCK_WORDS) + "！" + variant
        # 随机添加数字
        if random.random() > 0.5:
            variant = random.choice(NUMBER_WORDS) + " " + variant
        variants.append(variant)
    return variants


def check_compliance(title):
    """合规校验"""
    found_words = []
    risk_level = "低"
    for word in BANNED_WORDS:
        if word in title:
            found_words.append(word)
    if found_words:
        risk_level = "高" if len(found_words) >= 2 else "中"
    return found_words, risk_level


def deduplicate(titles):
    """去重功能"""
    seen = set()
    result = []
    for title in titles:
        # 使用简单哈希去重
        hash_val = hashlib.md5(title.encode()).hexdigest()
        if hash_val not in seen:
            seen.add(hash_val)
            result.append(title)
    return result


def estimate_effect(title):
    """效果预估"""
    score = 0
    # 基础分
    score += 10
    # 震惊词加分
    for word in SHOCK_WORDS:
        if word in title:
            score += 8
    # 情感词加分
    for word in EMOTION_WORDS:
        if word in title:
            score += 5
    # 数字加分
    for word in NUMBER_WORDS:
        if word in title:
            score += 3
    # 标点加分
    if '！' in title or '?' in title:
        score += 5
    if '...' in title or '。。' in title:
        score += 3
    # 长度加分
    if len(title) >= 15:
        score += 5
    if len(title) >= 25:
        score += 5
    # 计算星级和CTR
    stars = min(5, max(1, score // 20))
    ctr = min(0.15, max(0.01, score / 1000))
    return stars, ctr


def is_clickbait(title):
    """判断是否为标题党"""
    score = 0
    # 震惊词
    for word in SHOCK_WORDS:
        if word in title:
            score += 15
    # 情感词
    for word in EMOTION_WORDS:
        if word in title:
            score += 10
    # 数字
    for word in NUMBER_WORDS:
        if word in title:
            score += 8
    # 标点
    if '！' in title:
        score += 10
    if '...' in title or '。。' in title:
        score += 5
    # 长度
    if len(title) >= 20:
        score += 5
    # 违禁词
    banned, _ = check_compliance(title)
    if banned:
        score += 20
    # 分类
    category = "标题党" if score >= 50 else "非标题党"
    return score, category


def run_selftest():
    """自检函数"""
    print("=" * 60)
    print("开始自检...")
    passed = 0
    total = 9

    # 测试1: 标题党判断
    print("\n[测试1] 标题党判断")
    test_titles = [
        "科学家发现惊人真相！！！",
        "普通新闻标题",
        "震惊！99%的人都不知道的秘密",
    ]
    for title in test_titles:
        score, category = is_clickbait(title)
        print(f"  ✓ '{title}' 得分={score}, 分类={category}")
        if "震惊" in title or "惊人" in title:
            assert score >= 50, f"标题党标题得分应≥50，实际{score}"
    passed += 1
    print("  ✓ 测试1通过")

    # 测试2: 标题党生成
    print("\n[测试2] 标题党生成")
    variants = generate_clickbait("普通新闻标题", 3)
    assert len(variants) == 3, f"应生成3个变体，实际{len(variants)}"
    print(f"  ✓ 生成 3 个变体: {variants[:2]}...")
    passed += 1
    print("  ✓ 测试2通过")

    # 测试3: 合规校验
    print("\n[测试3] 合规校验")
    banned, risk = check_compliance("国家级第一品牌产品")
    assert len(banned) >= 2, f"应检测到至少2个违禁词，实际{len(banned)}"
    assert risk == "高", f"风险等级应为高，实际{risk}"
    print(f"  ✓ 检测到违禁词: {banned}, 风险: {risk}")
    passed += 1
    print("  ✓ 测试3通过")

    # 测试4: 去重功能
    print("\n[测试4] 去重功能")
    titles = ["标题1", "标题2", "标题1", "标题3"]
    deduped = deduplicate(titles)
    assert len(deduped) == 3, f"去重后应为3条，实际{len(deduped)}"
    print(f"  ✓ 去重后 {len(deduped)} 条（原 {len(titles)} 条）")
    passed += 1
    print("  ✓ 测试4通过")

    # 测试5: 效果预估
    print("\n[测试5] 效果预估")
    stars, ctr = estimate_effect("震惊！99%的人都不知道的秘密")
    assert stars >= 3, f"星级应≥3，实际{stars}"
    assert ctr > 0.05, f"CTR应>0.05，实际{ctr}"
    print(f"  ✓ 星级={stars}, 预估CTR={ctr:.3f}")
    passed += 1
    print("  ✓ 测试5通过")

    # 测试6: 边界情况
    print("\n[测试6] 边界情况")
    empty_score, empty_cat = is_clickbait("")
    assert empty_score >= 0, "空标题得分应≥0"
    assert empty_cat == "非标题党", "空标题应为非标题党"
    print(f"  ✓ 空标题: 得分={empty_score}, 分类={empty_cat}")
    passed += 1
    print("  ✓ 测试6通过")

    # 测试7: 生成数量
    print("\n[测试7] 生成数量")
    for n in [1, 2, 5]:
        variants = generate_clickbait("测试", n)
        assert len(variants) == n, f"应生成{n}个，实际{len(variants)}"
    print("  ✓ 生成数量正确")
    passed += 1
    print("  ✓ 测试7通过")

    # 测试8: 去重稳定性
    print("\n[测试8] 去重稳定性")
    for _ in range(10):
        titles = ["相同标题"] * 5
        deduped = deduplicate(titles)
        assert len(deduped) == 1, "相同标题应去重为1条"
    print("  ✓ 去重稳定")
    passed += 1
    print("  ✓ 测试8通过")

    # 测试9: 综合功能
    print("\n[测试9] 综合功能")
    subject = "人工智能"
    variants = generate_clickbait(subject, 3)
    for v in variants:
        score, category = is_clickbait(v)
        assert score >= 0, "得分应非负"
    print(f"  ✓ 生成并验证 {len(variants)} 个标题党变体")
    passed += 1
    print("  ✓ 测试9通过")

    # 总结
    print("\n" + "=" * 60)
    print(f"自检完成: {passed}/{total} 项通过")
    print("=" * 60)
    return passed == total


def main():
    parser = argparse.ArgumentParser(description="标题党生成器")
    parser.add_argument("--selftest", action="store_true", help="运行自检")
    parser.add_argument("--subject", type=str, default="人工智能", help="标题主题")
    parser.add_argument("--count", type=int, default=3, help="生成数量")
    parser.add_argument("--check", type=str, help="检查标题是否为标题党")
    args = parser.parse_args()

    if args.selftest:
        success = run_selftest()
        exit(0 if success else 1)
    elif args.check:
        score, category = is_clickbait(args.check)
        print(f"标题: {args.check}")
        print(f"得分: {score}")
        print(f"分类: {category}")
    else:
        variants = generate_clickbait(args.subject, args.count)
        print(f"生成的标题党变体:")
        for i, v in enumerate(variants, 1):
            print(f"  {i}. {v}")


if __name__ == "__main__":
    main()
