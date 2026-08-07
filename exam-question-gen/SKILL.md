---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: exam-question-gen
name: exam-question-gen
displayName: 组卷出题 知识点覆盖 题型配置
description: 按知识点与难度批量生成带解析的练习题，支持三种题型。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/exam-question-gen
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: SkillForge Lab
agent_created: true
trigger_words: ["出题", "生成练习题", "组卷", "出卷", "练习题生成"]
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

# 组卷出题 Skill 文档

## 一、能力边界（一页纸速查卡）

### 能做（5 项核心能力）

| 编号 | 能力项 | 说明 |
|------|--------|------|
| 1 | 知识点列表解析 | 从用户输入中提取知识点名称、数量要求、难度系数 |
| 2 | 题型与数量映射 | 将"3 道选择 + 2 道填空"这类指令转换为结构化生成参数 |
| 3 | 结构化结果输出 | 按固定 JSON 格式输出题目、选项、答案、解析 |
| 4 | 置信度标注 | 对推断出的信息（如默认难度、默认题量）标注置信度等级 |
| 5 | 批量与自定义格式 | 支持一次生成多组题目，支持用户指定输出字段顺序 |

### 不能做（明确边界）

| 编号 | 限制项 | 说明 |
|------|--------|------|
| 1 | 不生成主观题（论述/作文） | 仅支持选择、填空、简答三种客观/半客观题型 |
| 2 | 不保证知识点覆盖完整性 | 若用户未指定知识点范围，仅按输入内容生成，不自动补全 |
| 3 | 不校验题目学术准确性 | 生成内容基于模型知识，不替代专业教研审核 |
| 4 | 不生成图片/表格题 | 仅支持纯文本题目与答案 |
| 5 | 不执行外部题库检索 | 所有题目由模型即时生成，不连接外部数据库 |

### 适用对象

- 中小学教师备课组卷
- 培训机构助教出练习题
- 自学者自测练习
- 教育产品开发者批量生成测试数据


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
