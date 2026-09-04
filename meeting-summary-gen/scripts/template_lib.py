# -*- coding: utf-8 -*-
"""template_lib.py — 会议纪要 会议总结生成器 模板库（数据层）"""

SCENE_OPTIONS = {
  "standard": "标准总结",
  "brief": "简报",
  "action": "行动项优先"
}

STRUCTURE = [["hook", 0.05], ["overview", 0.15], ["topics", 0.4], ["actions", 0.25], ["next", 0.15]]

TEMPLATES = {
  "hook": [
    "本场会议共讨论 {n} 个议题，关键结论如下。"
  ],
  "overview": [
    "【会议概况】时间/参会人/主题由你补全，AI 已按录音原文整理。"
  ],
  "topics": [
    "议题 {i}：{t} → 结论：{c}",
    "讨论点：{t}，最终一致意见：{c}"
  ],
  "actions": [
    "行动项：{a}（负责人：{o}，截止：{d}）"
  ],
  "next": [
    "下次会议跟进：{a} 的完成情况与遗留问题。"
  ]
}

BLOCK_WORDS = ["泄露机密", "非法", "贿赂", "违法"]
RISK_WORDS = []

MIN_COUNT = 1
MAX_COUNT = 3
