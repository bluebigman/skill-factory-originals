# -*- coding: utf-8 -*-
"""template_lib.py — 活动策划方案生成器 模板库（数据层）"""

SCENE_OPTIONS = {
  "promo": "促销活动",
  "brand": "品牌活动",
  "community": "社群活动",
  "launch": "新品发布"
}

STRUCTURE = [["theme", 0.1], ["goal", 0.1], ["rundown", 0.3], ["budget", 0.2], ["spread", 0.15], ["risk", 0.15]]

TEMPLATES = {
  "theme": [
    "活动主题：{topic}（一句话主张：{slogan}）"
  ],
  "goal": [
    "目标拆解：K1 参与人数 {p} ｜ K2 转化 {c} ｜ K3 声量 {v}"
  ],
  "rundown": [
    "环节 {i}：{seg}（时长 {t}min，负责人 {o}）"
  ],
  "budget": [
    "预算项：{b} → {amt}（占总预算 {pct}%）"
  ],
  "spread": [
    "传播：预热 {p1} → 爆发 {p2} → 复盘 {p3}"
  ],
  "risk": [
    "风险 {i}：{r}（预案：{m}）"
  ]
}

BLOCK_WORDS = ["虚假宣传", "价格欺诈", "违禁"]
RISK_WORDS = []

MIN_COUNT = 1
MAX_COUNT = 3
