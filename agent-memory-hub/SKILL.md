---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: agent-memory-hub
name: agent-memory-hub
displayName: 团队记忆 资产沉淀 知识复用
description: 将对话、文档与代码沉淀为可复用的团队级记忆资产，支持治理与共享。
version: 1.0.1
rules_version: cpr-20260808-n152
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/agent-memory-hub
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: LingWei
agent_created: true
trigger_words: ["记忆管理", "知识沉淀", "资产复用", "团队知识库", "对话记忆", "技能封装", "LLM维基", "代码图谱"]
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

# agent-memory-hub 技能文档

## 一、能力边界：一页纸速查卡

本技能面向需要将零散信息转化为结构化、可复用资产的团队或个人。它不替代知识管理系统，而是充当“信息炼油厂”——把输入的对话、文档、代码，提炼为四种标准化的记忆资产。

### 1.1 能做（核心能力）

| 编号 | 能力项 | 说明 | 适用输入 |
|------|--------|------|----------|
| C1 | 对话记忆化 | 将聊天记录提炼为带摘要、标签、决策点的结构化记忆条目 | 聊天导出文件、对话文本 |
| C2 | 技能封装 | 从操作步骤、命令序列中提取可复用的技能模板（含参数、前置条件） | 操作手册、教程、命令日志 |
| C3 | LLM维基构建 | 将概念解释、术语定义整理为可供大模型检索的维基条目（含别名、关联） | 术语表、FAQ、概念文档 |
| C4 | 代码图谱生成 | 从代码仓库或代码片段中提取函数、类、依赖关系，生成调用关系图数据 | 代码文件、Git仓库导出 |
| C5 | 批量与自定义格式 | 支持一次处理多个文件/URL，并可按用户指定的字段结构输出 | 多文件目录、URL列表 |

### 1.2 不能做（明确边界）

| 编号 | 限制项 | 说明 |
|------|--------|------|
| L1 | 不执行代码 | 仅分析代码结构，不运行、不调试、不执行任何代码逻辑 |
| L2 | 不自动写入知识库 | 生成结构化结果，由用户决定如何导入目标系统 |
| L3 | 不处理加密/二进制内容 | 仅处理文本类数据（txt/md/json/py/js/ts等） |
| L4 | 不保证信息真实性 | 对输入中的事实性错误不做校验，仅做结构化提取 |
| L5 | 不跨语言翻译 | 保留原文语言，不做翻译处理 |

### 1.3 适用对象

- 需要建立团队知识库的AI代理开发者
- 维护多项目文档体系的技术负责人
- 希望将个人笔记转化为可共享资产的知识工作者


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
