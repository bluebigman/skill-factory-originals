# -*- coding: utf-8 -*-
"""template_lib.py — SQL查询 语句生成助手 模板库（数据层）"""

SCENE_OPTIONS = {
  "mysql": "MySQL",
  "postgres": "PostgreSQL",
  "sqlite": "SQLite"
}

STRUCTURE = [["intro", 0.08], ["sql", 0.52], ["explain", 0.24], ["tips", 0.16]]

TEMPLATES = {
  "intro": [
    "【SQL 生成】方言 {dialect}，按表结构描述生成查询语句。"
  ],
  "sql": [
    "```sql\\n{stmt}\\n```"
  ],
  "explain": [
    "执行逻辑：{exp}"
  ],
  "tips": [
    "优化建议：{tip}"
  ]
}

BLOCK_WORDS = []
RISK_WORDS = ["删库", "drop table", "truncate"]

MIN_COUNT = 1
MAX_COUNT = 3
