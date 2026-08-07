---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: foxtracs
name: foxtracs
displayName: Firefox工单追踪 数据解析 结构化输出
description: 解析Firefox工单数据，提取关键信息并生成结构化结果。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/foxtracs
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 技能工坊
agent_created: true
trigger_words: ["foxtracs", "firefox trac", "工单解析", "ticket extraction", "工单结构化"]
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

# foxtracs — Firefox 工单数据解析与结构化输出

## 一、能力边界（一页纸速查卡）

### 1.1 能做与不能做

| 维度 | 能做 | 不能做 |
|------|------|--------|
| 输入处理 | 用户提供的文本、文件内容、URL 指向的工单数据 | 主动访问网络、登录认证系统、抓取需权限的页面 |
| 信息提取 | 识别工单编号、标题、状态、优先级、指派人、时间戳、描述摘要 | 推断未明确写出的隐含业务逻辑、自动修复数据错误 |
| 输出生成 | 按约定字段结构输出 Markdown 或 JSON 格式结果 | 生成非约定格式的二进制文件、图像、PDF |
| 批量处理 | 支持一次输入多条工单记录，逐条解析 | 并行处理超过 50 条以上的超大批量（受上下文窗口限制） |
| 置信度标注 | 对每个提取字段标注 confidence 等级（high/medium/low） | 对缺失字段编造默认值或猜测值 |

### 1.2 适用对象

- 需要将 Firefox 工单系统（Trac）中的文本记录转换为结构化数据的开发者
- 需要批量整理工单信息用于报表、迁移或分析的运维人员
- 需要从工单描述中快速提取关键字段的测试与 QA 工程师

### 1.3 输入输出速览

| 项目 | 说明 |
|------|------|
| 输入来源 | 用户粘贴的文本、上传的文件内容、用户提供的 URL（需用户自行获取内容后提供） |
| 输出格式 | Markdown 表格 或 JSON 对象（用户指定其一，默认 Markdown） |
| 字段结构 | id, title, status, priority, assignee, created_at, updated_at, description_excerpt |


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
