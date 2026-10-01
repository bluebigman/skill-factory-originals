---
name: child-proof
description: "儿童防护 —— 分龄儿童居家防护要点"
version: 1.0.0
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/home-safety-check-pro
---

# 儿童防护

分龄儿童居家防护要点

## 能力边界（契约 · R1）
- **能做**：针对 儿童防护、插座、窗户、误食 等情境，输出归因清单与可执行动作
- **不做**：心理/医学诊断；涉自伤、重度抑郁等情况**转介专业机构**
- **输入**：纯文本（`--text` 或 `--input <文件>` 或标准输入）
- **输出**：人类可读 Markdown + **JSON 摘要**（`ok`/`summary`/`next_actions`/`error_code`）

## 用法
```bash
python run.py --text "孩子沉迷手机，怎么说都不听"
python run.py --input note.txt --verbose
python run.py --selftest
```

## 错误码
| 码 | 含义 | 处理 |
|---|---|---|
| E01 | 输入缺失 | 补齐文本后重试 |
| E02 | 格式不符 | 转为纯文本后重试 |
| E03 | 超出边界 | 改用其他能力 |
| E04 | 内部错误 | 退避后重试 1 次 |

## AI 生成披露

<!-- ai-generated-notice -->
本技能的能力边界、领域规则与示例由生成器按**通用领域知识**撰写，经人工规则化整理与
自动化合规检查后产出。**未复制任何受版权保护的原文**；与上游开源项目无派生关系。

## 边界与免责声明

<!-- professional-disclaimer-injected -->
- 本技能提供通用方法性建议，**不构成专业诊断、治疗、法律或投资意见**。
- 涉及医疗、法律、金融等专业事项，请咨询具备相应资质的专业人士或机构。
- 使用者应结合自身实际情况判断，因使用本技能产生的决策后果由使用者自行承担。

## 许可证

<!-- professional-license-embedded -->
本项目以 **MIT License** 授权（全文见包内 `LICENSE` 文件）。
Copyright (c) 2026 SkillForge Lab. 保留所有权利声明。
