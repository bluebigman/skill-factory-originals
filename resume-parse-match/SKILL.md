---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: resume-parse-match
name: resume-parse-match
displayName: 简历解析 岗位匹配 候选人排序
description: 批量解析简历PDF，提取关键经历与技能，对照岗位要求打分排序。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/resume-parse-match
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: SkillForge Studio
agent_created: true
trigger_words: ["简历解析", "岗位匹配", "候选人排序", "简历筛选", "JD匹配", "人才评估"]
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

# 简历解析与岗位匹配 Skill

## 一、能力边界（一页纸速查卡）

### 能做（5项核心能力）

1. **批量解析简历文件**：支持 PDF、Word（.docx）格式的简历，提取文本内容并结构化。
2. **提取关键信息字段**：从简历中抽取教育背景、工作经历、技能标签、项目经验等核心字段。
3. **对照岗位要求匹配**：将候选人信息与岗位 JD（职位描述）进行语义比对，计算匹配度。
4. **输出候选人排序结果**：按匹配度从高到低输出候选人列表，附详细匹配依据。
5. **标注置信度与缺失项**：对无法确定的信息标注 `[需核实:字段名]`，不编造数据。

### 不能做（明确边界）

- 不能解析图片型简历（扫描件需先经 OCR 处理）。
- 不能对候选人进行背景调查或真伪验证。
- 不能替代人工面试决策，仅提供数据参考。
- 不能处理加密或损坏的文件。
- 不能保证匹配结果的绝对准确性。

### 适用对象

| 使用者 | 使用场景 |
|--------|----------|
| HR 招聘专员 | 批量初筛简历，快速定位高匹配候选人 |
| 猎头顾问 | 多岗位候选人匹配，生成推荐排序 |
| 技术面试官 | 快速了解候选人技能栈与岗位契合度 |
| 招聘系统开发者 | 集成简历解析能力到自有系统 |


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
