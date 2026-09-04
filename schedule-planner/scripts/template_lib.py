# -*- coding: utf-8 -*-
"""template_lib.py — 日程管理 时间规划助手 模板库（数据层）"""

SCENE_OPTIONS = {
  "day": "单日时间块",
  "week": "周计划",
  "focus": "专注清单"
}

STRUCTURE = [["intro", 0.08], ["blocks", 0.6], ["remind", 0.16], ["tip", 0.16]]

TEMPLATES = {
  "intro": [
    "【{mode_label}】按优先级与时长把任务排进时间块。"
  ],
  "blocks": [
    "时间块 {i}：{seg}（{slot}，优先级 {pr}）"
  ],
  "remind": [
    "提醒：{r}"
  ],
  "tip": [
    "技巧：{tip}"
  ]
}

BLOCK_WORDS = []
RISK_WORDS = []

MIN_COUNT = 1
MAX_COUNT = 3
