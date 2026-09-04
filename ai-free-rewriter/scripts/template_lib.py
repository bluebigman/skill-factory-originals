# -*- coding: utf-8 -*-
"""template_lib.py — 去AI味 文本改写润色 模板库（数据层）"""

SCENE_OPTIONS = {
  "natural": "自然口语",
  "formal": "正式书面",
  "concise": "简洁有力"
}

STRUCTURE = [["intro", 0.1], ["rules", 0.3], ["rewrite", 0.5], ["note", 0.1]]

TEMPLATES = {
  "intro": [
    "改写说明：目标风格 {style}，逐段处理。"
  ],
  "rules": [
    "规则 {i}：{r}"
  ],
  "rewrite": [
    "原文：{orig}\n改写：{new}"
  ],
  "note": [
    "提示：保留原文信息完整性，不增删事实。"
  ]
}

BLOCK_WORDS = []
RISK_WORDS = []

MIN_COUNT = 1
MAX_COUNT = 3
