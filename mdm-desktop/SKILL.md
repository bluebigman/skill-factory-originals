---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: mdm-desktop
name: mdm-desktop
displayName: 文档转换 格式迁移 智能解析
description: 将PDF、DOCX、HWP等文档快速转换为结构化Markdown，保留关键信息。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/mdm-desktop
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 格式工坊
agent_created: true
trigger_words: ["PDF转文档", "文档转换", "Markdown转换", "格式迁移", "HWP转MD"]
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

# MDM Desktop — 文档转 Markdown 技能指南

## 一、能力边界（一页纸速查卡）

### 1.1 能做什么

| 序号 | 能力项 | 说明 |
|------|--------|------|
| 1 | 多格式输入解析 | 支持 PDF、DOCX、HWP 三种主流文档格式的内容提取 |
| 2 | 关键信息识别 | 自动识别标题层级、表格结构、列表项、代码块等文档要素 |
| 3 | 结构化 Markdown 输出 | 按规范生成带元数据头的 .md 文件，保留文档逻辑结构 |
| 4 | 置信度标注 | 对识别不确定的内容（如扫描件乱码、复杂表格）标注置信度 |
| 5 | 批量处理与格式定制 | 支持多文件队列处理，可指定输出目录和命名规则 |

### 1.2 不能做什么

| 序号 | 限制项 | 说明 |
|------|--------|------|
| 1 | 不处理加密文档 | 需要密码的 PDF/DOCX 文件无法解析，需用户先解除密码 |
| 2 | 不识别手写内容 | 手写批注、手绘图形不会被提取，仅处理印刷体文本 |
| 3 | 不保留复杂排版 | 页眉页脚、多栏布局、浮动文本框等复杂排版会丢失 |
| 4 | 不执行语义理解 | 不判断文档内容的正确性、不总结摘要、不翻译 |
| 5 | 不处理图片内文字 | 嵌入图片中的文字需先经过 OCR 预处理（本工具不含 OCR） |

### 1.3 适用对象

- 需要将旧格式文档迁移到 Markdown 生态的开发者
- 需要批量整理技术文档、产品手册的内容运营人员
- 需要将论文、报告转为可版本管理格式的研究人员


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
