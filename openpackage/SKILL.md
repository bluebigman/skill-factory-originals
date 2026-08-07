---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: openpackage
name: openpackage
displayName: 技能包管家 组织分发 命令编排
description: 统一收纳、组织、分发各类技能包与命令，支持批量转换与格式校验。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/openpackage
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: SkillForge Studio
agent_created: true
trigger_words: ["openpackage", "技能包管理", "技能组织", "命令编排", "技能分发", "package organizer"]
---

> 📜 **用户协议（User Agreement）**
> 1. 本 Skill 仅供学习与参考用途。使用本 Skill 产生的任何结果，由使用者自行承担全部责任；本 Skill 不提供任何明示或暗示的保证。
> 2. 涉及法律、财务、税务、投资、医疗等专业决策时，请务必咨询持证专业人士。
> 3. 本代码受版权法保护，未经授权复制、反向工程或商业利用将被追究法律责任。
<!-- user-agreement-injected -->


> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->

> 本内容由 AI 生成，仅供学习参考 <!-- ai-generated-notice -->

# openpackage — 技能包管家

## 一、能力边界速查卡

### 能做什么（5 项核心能力）

| 编号 | 能力项 | 说明 | 典型场景 |
|------|--------|------|----------|
| 1 | 数据/文件/URL 结构化转换 | 将用户提供的原始输入（文本、文件路径、网页链接）解析为统一的结构化结果 | 把一份散乱的技能说明文档转为标准 JSON 清单 |
| 2 | 关键信息识别与保留 | 从输入中提取名称、版本、依赖、触发词等核心字段，不丢失语义 | 从一段对话中抽取技能包的元数据 |
| 3 | 按约定格式生成输出 | 遵循预定义的输出模板（JSON / Markdown / YAML）产出结果 | 生成符合规范的技能包索引文件 |
| 4 | 置信度标注 | 对每个输出字段标注可信程度（高/中/低），不确定时明确提示 | 当输入来源模糊时，标注"低置信度" |
| 5 | 批量处理与自定义格式 | 支持一次处理多个输入项，并允许用户指定输出格式 | 将 20 个 URL 批量转为技能包清单 |

### 不能做什么（明确边界）

- 不能执行技能包内部的业务逻辑（如运行某个技能的实际功能）
- 不能自动安装或部署技能包到第三方平台
- 不能在没有足够信息时凭空补全字段（会以 `[需核实:字段名]` 占位）
- 不能处理加密或权限受限的文件内容
- 不能保证输入源的时效性与准确性（依赖用户提供的信息）

### 适用对象

- 需要整理本地技能包/命令集合的开发者
- 需要将散落文档转为统一格式的团队协作者
- 需要批量导入技能清单的自动化流程使用者


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
