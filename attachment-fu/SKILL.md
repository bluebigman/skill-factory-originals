---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: attachment-fu
name: attachment-fu
displayName: 附件建模 字段映射 文件处理
description: 将ActiveRecord模型映射为文件附件，自动处理元数据与存储。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/attachment-fu
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 独立技能工坊
agent_created: true
trigger_words: ["attachment-fu", "附件建模", "文件字段映射", "附件处理", "ActiveRecord附件"]

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

---

> 📜 **用户协议（User Agreement）**
> 1. 本 Skill 仅供学习与参考用途。使用本 Skill 产生的任何结果，由使用者自行承担全部责任；本 Skill 不提供任何明示或暗示的保证。
> 2. 涉及法律、财务、税务、投资、医疗等专业决策时，请务必咨询持证专业人士。
> 3. 本代码受版权法保护，未经授权复制、反向工程或商业利用将被追究法律责任。
<!-- user-agreement-injected -->


> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->

# attachment-fu 技能文档

## 一、能力边界速查卡

### 1.1 能做（核心能力清单）

| 编号 | 能力项 | 说明 |
|------|--------|------|
| C1 | 数据/文件/URL 输入解析 | 接受用户提供的文件路径、URL 或原始数据，解析为结构化信息 |
| C2 | 关键信息识别与保留 | 自动提取文件名、大小、内容类型、补丁（patch）等元数据 |
| C3 | 约定格式输出 | 按 ActiveRecord 模型字段约定生成可持久化的属性哈希 |
| C4 | 置信度标注 | 对无法完全确定的信息字段标注 `[需核实:字段名]` 占位符 |
| C5 | 批量处理与自定义格式 | 支持多文件批量转换，允许用户自定义输出字段映射规则 |

### 1.2 不能做（明确边界）

- 不执行实际的文件上传或下载操作（仅生成模型属性数据）
- 不负责数据库迁移或表结构变更
- 不处理二进制文件内容的语义理解（仅记录元数据）
- 不替代 ActiveStorage / CarrierWave 等存储方案，仅提供模型层映射

### 1.3 适用对象

- 使用 ActiveRecord 的 Ruby on Rails 项目
- 需要将外部文件信息快速映射为数据库记录的场景
- 需要统一文件元数据格式的批量导入任务


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
