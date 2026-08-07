---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: ux-skill
name: ux-skill
displayName: 交互设计 体验审查 界面诊断
description: 面向AI编程工具的体验设计审查引擎，将输入转化为结构化诊断结果。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/ux-skill
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: Linaro Design Studio
agent_created: true
trigger_words: ["ux-skill", "体验审查", "界面诊断", "UX评审", "交互检查", "设计走查"]
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

# ux-skill — 交互设计体验审查引擎

## 一、能力边界：一页纸速查卡

### 1.1 能做什么

| 序号 | 能力项 | 说明 | 输入示例 |
|------|--------|------|----------|
| 1 | 数据/文件/URL 结构化转换 | 将设计稿链接、用户反馈文本、竞品页面 URL 转为结构化诊断数据 | `https://example.com/login` |
| 2 | 关键信息识别与保留 | 自动提取界面中的操作路径、反馈机制、视觉层级等关键要素 | 设计说明文档、PRD 片段 |
| 3 | 按约定格式生成输出 | 输出固定为 Markdown 表格 + 问题清单 + 优先级排序 | 见 3.3 输出规范 |
| 4 | 置信度标注 | 对每项诊断结论标注高/中/低三档置信度 | `[置信度:高]` |
| 5 | 批量处理与自定义格式 | 支持一次提交多个 URL 或文件，输出可指定字段子集 | `--fields=问题,建议,优先级` |

### 1.2 不能做什么

- 不能代替真实用户进行可用性测试（无真实交互数据）
- 不能对视觉美观度做主观评分（仅做客观规范检查）
- 不能访问需登录认证的私有页面
- 不能自动修复代码问题（仅输出诊断建议）
- 不能保证覆盖所有边界场景（输出中会标注未检查项）

### 1.3 适用对象

| 角色 | 适用场景 | 不适用场景 |
|------|----------|------------|
| 前端开发者 | 实现前快速走查设计稿 | 已上线产品的深度用研 |
| 产品经理 | 评审阶段检查交互完整性 | 商业决策分析 |
| 设计师 | 交付前自查设计规范 | 品牌视觉风格定义 |
| AI 编程助手 | 生成 UI 代码前的约束检查 | 后端逻辑审查 |


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
