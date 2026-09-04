# -*- coding: utf-8 -*-
"""template_lib.py — 营销文案模板库（数据层）"""

TONES = {
    "pro": {"name": "专业理性", "openers": ["高效解决", "针对{audience}场景", "为效率而生"]},
    "friendly": {"name": "亲切自然", "openers": ["最近发现", "用了就回不去", "真心推荐"]},
    "young": {"name": "年轻潮流", "openers": ["打工人福音", "谁懂啊", "通勤救星"]},
    "premium": {"name": "高端质感", "openers": ["匠心之作", "细节见品质", "为少数人打造"]},
}

CHANNELS = {
    "title": "电商标题",
    "detail": "商品详情",
    "moments": "朋友圈种草",
    "ads": "信息流广告",
    "slogan": "短广告语",
    "xhs": "小红书笔记",
}

POINT_BRIDGES = [
    "最打动我的是",
    "关键升级在",
    "和普通款拉开差距的",
]

# 绝对化/虚假宣传词（命中 → 输出合规替换提示）
ABSOLUTE_WORDS = [
    "第一", "最", "绝对", "百分百", "100%", "全网", "销量冠军",
    "唯一", "根治", "包治", "立竿见影", "无任何副作用",
]

RISK_INDUSTRY_WORDS = [
    "医疗", "治疗", "药物", "保健", "理财", "投资", "保险", "减肥神效",
]

TITLE_TEMPLATES = [
    "{audience}专用{product} {points}",
    "{product}｜{top_point} {points_short}",
    "{product} {top_point}，{audience}闭眼入",
]

DETAIL_TEMPLATES = [
    "「{product}」——为{audience}解决{top_point}的问题。\n\n"
    "1. {p0}\n2. {p1}\n3. {p2}\n\n"
    "真实体验：{exp}",
]

MOMENTS_TEMPLATES = [
    "最近入手了{product}，{exp}。\n"
    "{p0}这一点最戳我，{p1}也够用。\n"
    "有需要的可以私信我链接～",
]

ADS_TEMPLATES = [
    "还在为{top_point}发愁？{product}给你答案。\n"
    "{p0}｜{p1}｜{p2}\n"
    "点击了解 →",
]

SLOGAN_TEMPLATES = [
    "{top_point}，就选{product}。",
    "{product}：{top_point_short}。",
    "让{top_point}变简单——{product}。",
]

XHS_TEMPLATES = [
    "标题：{product}测评｜{top_point}是真的香\n\n"
    "姐妹们，{product}我用了两周，来交作业📝\n"
    "✨ {p0}\n✨ {p1}\n✨ {p2}\n\n"
    "总结：{audience}可以冲，理性种草～",
]

EXPERIENCE_LINES = [
    "体验比想象中顺",
    "每天在用，没闲置",
    "同事看到都来问链接",
    "包装质感也在线",
]

MAX_POINTS = 5
MIN_POINTS = 2
MAX_COUNT = 3
