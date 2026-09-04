# -*- coding: utf-8 -*-
"""template_lib.py — 月度工作报告生成器 模板库（数据层）"""

SCENE_OPTIONS = {
  "pro": "专业",
  "concise": "简洁",
  "detail": "详尽"
}

STRUCTURE = [["hook", 0.05], ["done", 0.3], ["progress", 0.2], ["problem", 0.2], ["plan", 0.25]]

TEMPLATES = {
  "hook": [
    "【{month} 月度工作报告】"
  ],
  "done": [
    "完成事项 {i}：{d}（结果：{r}）"
  ],
  "progress": [
    "进行中：{p}，当前进度 {pct}%，预计 {e} 完成。"
  ],
  "problem": [
    "风险/问题：{p}。缓解：{m}。"
  ],
  "plan": [
    "下月计划 {i}：{p}（优先级：{pr}）"
  ]
}

BLOCK_WORDS = []
RISK_WORDS = []

MIN_COUNT = 1
MAX_COUNT = 3
