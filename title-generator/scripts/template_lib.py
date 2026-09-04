# -*- coding: utf-8 -*-
"""template_lib.py — 爆款标题生成器 模板库（数据层）"""

SCENE_OPTIONS = {
  "generic": "通用",
  "wechat": "公众号",
  "douyin": "抖音",
  "zhihu": "知乎",
  "xiaohongshu": "小红书"
}

STRUCTURE = [["intro", 0.05], ["titles", 0.8], ["hint", 0.15]]

TEMPLATES = {
  "intro": [
    "【标题列表】按内容主题生成多条可选标题。"
  ],
  "titles": [
    "{t}"
  ],
  "hint": [
    "选题提示：优先用「{kw}」相关词提高搜索命中。"
  ]
}

BLOCK_WORDS = ["震惊部", "不转不是", "必须转", "看了会死"]
RISK_WORDS = []

MIN_COUNT = 1
MAX_COUNT = 3
