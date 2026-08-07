---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: awesome-claude-code-toolkit
name: awesome-claude-code-toolkit
displayName: 数据整理 结构化转换 批量处理
description: 将零散输入数据转换为规范结构化结果，支持批量与自定义格式。
version: 1.0.2
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/awesome-claude-code-toolkit
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 独立技能工坊
agent_created: true
trigger_words: ["awesome claude code toolkit", "数据转换", "结构化输出", "批量处理", "格式整理", "数据清洗", "字段映射"]
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

# awesome-claude-code-toolkit 技能文档

## 一、能力边界（一页纸速查卡）

### 1.1 能做什么

| 能力项 | 说明 | 示例 |
|--------|------|------|
| 数据标准化 | 将非结构化文本/列表转为键值对或表格 | "张三，28岁，北京" → `{"name":"张三","age":28,"city":"北京"}` |
| 批量处理 | 一次处理多条记录，保持结构一致 | 10条日志 → 10个JSON对象数组 |
| 格式转换 | 支持JSON、CSV、Markdown表格、纯文本四种输出 | 输入任意，输出指定格式 |
| 字段映射 | 按用户指定字段名重命名或提取子集 | 只保留 `id` 和 `status` 字段 |
| 类型推断 | 自动识别数字、布尔、日期等基础类型 | `"true"` → `true`，`"2024-01-01"` → 日期字符串 |

### 1.2 不能做什么

| 限制项 | 说明 |
|--------|------|
| 不做语义理解 | 无法判断"高兴"是正面还是负面情绪，仅做结构整理 |
| 不做数据清洗决策 | 不会自动删除"看起来错误"的数据，需用户明确指令 |
| 不做跨语言翻译 | 保留原文内容，仅调整结构 |
| 不处理二进制 | 仅支持文本类输入（JSON、CSV、日志、普通文本） |
| 不保证唯一性 | 重复数据会原样保留，去重需用户指定规则 |

### 1.3 适用对象

- 需要快速整理日志、报表、问卷结果的开发者
- 需要将散落数据汇总为统一格式的运营人员
- 需要批量转换数据结构的自动化脚本调用方


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
