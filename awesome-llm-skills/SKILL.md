---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: awesome-llm-skills
name: awesome-llm-skills
displayName: 技能导航 信息萃取 结构化输出
description: 将任意输入内容解析为结构化结果，支持批量处理与置信度标注。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/awesome-llm-skills
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: SkillForge Studio
agent_created: true
trigger_words: ["awesome llm skills", "技能导航", "信息萃取", "结构化输出", "数据整理"]
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

# awesome-llm-skills 技能文档

## 一、能力边界速查卡

本技能用于将用户提供的原始材料（文本、文件内容、URL 指向的页面）转化为符合约定结构的输出结果。以下内容帮助你在 30 秒内判断本技能是否适用。

### ✅ 能做（核心能力）

| 编号 | 能力项 | 说明 |
|------|--------|------|
| 1 | 输入解析 | 接受用户粘贴的文本、上传的文件内容或提供的 URL 链接 |
| 2 | 关键信息识别 | 从非结构化内容中提取实体、属性、关系等关键要素 |
| 3 | 结构化输出 | 按用户指定或默认的字段结构生成结果 |
| 4 | 置信度标注 | 对每条提取结果标注可信程度（高/中/低） |
| 5 | 批量处理 | 支持多条记录同时输入，逐条解析并统一输出 |

### ❌ 不能做（明确边界）

| 编号 | 限制项 | 说明 |
|------|--------|------|
| 1 | 不访问实时网络 | 除非用户明确提供 URL 且环境允许，否则不主动联网抓取 |
| 2 | 不执行代码 | 不运行输入内容中的任何程序或脚本 |
| 3 | 不修改原始数据 | 输出为独立结果，不改变用户提供的源文件 |
| 4 | 不处理加密内容 | 加密文件或需解密的内容不在处理范围内 |
| 5 | 不生成主观评价 | 不输出价值判断、情感倾向或推荐意见 |

### 👥 适用对象

- 需要快速整理零散信息的个人用户
- 需要将非结构化数据转为表格/清单的团队协作场景
- 需要批量提取关键字段的文档处理流程


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
