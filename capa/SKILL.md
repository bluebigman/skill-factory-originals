---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: capa
name: capa
displayName: 配置编排 能力装配 技能接线
description: 将技能、工具、规则、子代理等能力组件装配为统一配置并校验。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/capa
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: Ling
agent_created: true
trigger_words: ["capa", "capabilities.yaml", "能力配置", "装配", "接线", "编排"]
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

# capa — 能力装配与配置编排 Skill

## 一、能力边界（一页纸速查卡）

### 能做

| 序号 | 能力项 | 说明 |
|------|--------|------|
| 1 | 输入解析 | 接受用户提供的数据、文件路径或 URL，提取其中的结构化内容 |
| 2 | 关键信息识别 | 从输入中定位技能、工具、规则、子代理、MCP 服务器、插件等组件声明 |
| 3 | 配置生成 | 按约定 schema 生成 capabilities.yaml 格式的装配结果 |
| 4 | 置信度标注 | 对每个字段的识别结果给出可信程度标记 |
| 5 | 批量与自定义 | 支持多组件同时装配，允许用户指定输出格式偏好 |

### 不能做

- 不能执行或运行被装配的技能/工具本身
- 不能验证外部 MCP 服务器或插件的真实可用性
- 不能自动修改用户本地文件（仅输出装配结果）
- 不能推断用户未提供的信息（如版本号、权限设置）

### 适用对象

- 需要为 Cursor、Claude Code、Codex 等环境编写 capabilities.yaml 的开发者
- 需要将散落组件统一编排的工程配置人员
- 需要快速将数据/URL 转为结构化配置清单的自动化流程使用者


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
