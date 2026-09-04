# -*- coding: utf-8 -*-
"""template_lib.py — 公众号文章 图文生成器 模板库（数据层）"""

SCENE_OPTIONS = {
  "insight": "观点洞察",
  "tutorial": "干货教程",
  "story": "故事讲述",
  "news": "热点评论"
}

STRUCTURE = [["title", 0.02], ["intro", 0.1], ["body1", 0.28], ["body2", 0.28], ["quote", 0.12], ["cta", 0.2]]

TEMPLATES = {
  "title": [
    "标题建议：{t1} / {t2} / {t3}"
  ],
  "intro": [
    "导语：{topic}，这事值得说道说道。"
  ],
  "body1": [
    "## 先讲清背景\n{topic} 的火爆不是偶然，背后有三层原因。"
  ],
  "body2": [
    "## 再说透关键\n把最核心的一层拆开看：{point}"
  ],
  "quote": [
    "金句：{q}"
  ],
  "cta": [
    "结尾：如果这篇文章对你有启发，点个「在看」，让更多人看到。"
  ]
}

BLOCK_WORDS = ["绝对", "第一", "最牛", "稳赚"]
RISK_WORDS = []

MIN_COUNT = 1
MAX_COUNT = 3
