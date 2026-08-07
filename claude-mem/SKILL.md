---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: claude-mem
name: claude-mem
displayName: 会话记忆 跨期上下文 持久化压缩
description: 跨会话持久化上下文，自动捕获、压缩并检索代理会话中的关键信息。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/claude-mem
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: LinguaForge
agent_created: true
trigger_words: ["claude-mem", "会话记忆", "上下文持久化", "记忆压缩", "跨期上下文"]
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

# claude-mem — 跨会话上下文持久化与压缩

## 一、能力边界：一页纸速查卡

### 1.1 能做什么

| 编号 | 能力项 | 说明 | 适用场景示例 |
|------|--------|------|--------------|
| C1 | 输入结构化 | 将用户提供的文本、文件路径或 URL 内容解析为结构化字段 | 从对话记录中提取决策项、待办事项 |
| C2 | 关键信息识别 | 自动标记并保留输入中的高价值信息（实体、决策、约束条件） | 识别项目约束、用户偏好、技术选型 |
| C3 | 格式约定输出 | 按预设模板生成压缩后的记忆条目，支持 JSON / Markdown 两种格式 | 生成会话摘要、生成交接文档 |
| C4 | 置信度标注 | 对不确定的字段输出 `[需核实:字段名]` 占位符，不编造内容 | 信息缺失时保留占位，等待用户确认 |
| C5 | 批量与自定义 | 支持多文件批量处理，允许用户自定义输出字段结构 | 批量压缩多个会话日志，自定义摘要模板 |

### 1.2 不能做什么

| 编号 | 限制项 | 说明 |
|------|--------|------|
| L1 | 不主动采集数据 | 仅在用户显式提供输入时工作，不主动监听或记录会话 |
| L2 | 不执行代码 | 不解析或运行输入中的代码片段，仅做文本级处理 |
| L3 | 不保证完整性 | 压缩过程可能丢失低优先级细节，不承诺 100% 信息保留 |
| L4 | 不跨设备同步 | 记忆数据仅保存在当前工作环境中，不自动同步至其他设备 |
| L5 | 不替代人工判断 | 置信度标注仅提示不确定性，最终决策由用户负责 |

### 1.3 适用对象

- 需要跨会话维护项目上下文的开发者
- 需要批量整理对话记录的研究人员
- 需要为团队交接生成结构化摘要的项目管理者


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
