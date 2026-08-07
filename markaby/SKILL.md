---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: markaby
name: markaby
displayName: 数据解析 结构化输出 置信度标注
description: 将用户输入数据解析为结构化结果，标注置信度并支持批量处理。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/markaby
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 灵犀设计组
agent_created: true
trigger_words: ["markaby", "数据解析", "结构化输出", "信息提取", "批量转换"]
---

> 📜 **用户协议（User Agreement）**
> 1. 本 Skill 仅供学习与参考用途。使用本 Skill 产生的任何结果，由使用者自行承担全部责任；本 Skill 不提供任何明示或暗示的保证。
> 2. 涉及法律、财务、税务、投资、医疗等专业决策时，请务必咨询持证专业人士。
> 3. 本代码受版权法保护，未经授权复制、反向工程或商业利用将被追究法律责任。
<!-- user-agreement-injected -->


> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# Markaby 数据解析与结构化输出 Skill 文档

## 一、能力边界（一页纸速查卡）

### 1.1 能做（核心能力清单）

| 序号 | 能力项 | 说明 | 适用场景示例 |
|------|--------|------|--------------|
| 1 | 多源输入解析 | 接受用户直接粘贴的文本、上传的文件（.txt/.csv/.json）、或指定 URL 指向的公开数据 | 从网页抓取商品信息、读取日志文件 |
| 2 | 关键信息识别与保留 | 自动提取输入中的实体、字段、数值、日期等关键要素，并保持原始上下文 | 从合同文本中提取甲方乙方、金额、期限 |
| 3 | 约定格式输出 | 按用户指定的字段结构（JSON/表格/键值对）生成结果 | 将非结构化笔记转为标准字段记录 |
| 4 | 置信度标注 | 对每个提取字段给出 0~1 的置信度评分，低置信度字段显式标注 | 手写扫描件识别结果标注可信程度 |
| 5 | 批量处理与自定义格式 | 支持多条记录批量转换，允许用户自定义输出模板 | 将 100 条客户反馈统一转为 CSV 报表 |

### 1.2 不能做（明确边界）

| 序号 | 限制项 | 说明 |
|------|--------|------|
| 1 | 不执行代码 | 不运行用户提供的脚本或程序，仅做静态解析 |
| 2 | 不访问私有数据 | 无法访问需要登录认证的 URL 或本地文件系统 |
| 3 | 不进行语义推理 | 不推断隐含含义，仅基于显式文本提取 |
| 4 | 不保证绝对准确 | 所有输出均带置信度，不承诺 100% 正确 |
| 5 | 不处理非文本输入 | 不支持图片、音频、视频等非文本格式（除非先经 OCR 转为文本） |

### 1.3 适用对象

- 需要快速将零散数据整理为规范格式的运营人员
- 需要从外部页面提取结构化信息的开发者
- 需要批量清洗和转换数据的分析师


## 许可证（License）

```text
MIT License

Copyright (c) 2026 SkillForge Lab

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.
```
<!-- professional-license-embedded -->
