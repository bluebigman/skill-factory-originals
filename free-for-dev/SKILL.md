---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: free-for-dev
name: free-for-dev
displayName: 云资源选型 免费额度 开发运维
description: 梳理开发运维可用的免费云服务层级，辅助选型决策。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/free-for-dev
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 云径勘测员
agent_created: true
trigger_words: ["free for dev", "免费开发资源", "免费云服务", "SaaS免费层", "PaaS免费额度", "开发工具白嫖"]
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

# free-for-dev 技能手册

## 一、能力边界速查卡

本技能面向 **DevOps 工程师、独立开发者、技术选型负责人**，帮助你在海量云服务中快速筛选出符合"免费"条件的选项，并评估其适用性。

| 维度 | 说明 |
|------|------|
| ✅ 能做 | 解析你提供的服务列表、URL、文档片段，提取免费额度信息 |
| ✅ 能做 | 按服务类别（SaaS/PaaS/IaaS）、免费额度类型（时长/用量/人数）归类 |
| ✅ 能做 | 对比多个服务的免费层限制，输出结构化对比结果 |
| ✅ 能做 | 对信息不全的条目标注 `[需核实:字段名]`，不臆造数据 |
| ✅ 能做 | 输出 Markdown 表格、JSON、CSV 三种格式（默认 Markdown） |
| ❌ 不能做 | 实时抓取网页验证免费政策（需你提供最新内容） |
| ❌ 不能做 | 判断免费层是否"够用"（取决于你的业务场景） |
| ❌ 不能做 | 推荐"最佳"服务（避免绝对化，只做客观对比） |
| ❌ 不能做 | 处理非技术类免费资源（如免费域名、免费课程） |

**输入要求**：文本、URL、文件路径均可。URL 需能直接访问且内容为公开信息。


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
