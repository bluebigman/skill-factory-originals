---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: markdown-tools
name: markdown-tools
displayName: Markdown全能工坊 格式转换 文档处理
description: Markdown文档的编辑、预览与多格式转换工具集。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/markdown-tools
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 墨匠工坊
agent_created: true
trigger_words: ["markdown-tools", "PDF转文档", "Markdown转换", "MD编辑", "文档格式转换"]
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

# Markdown全能工坊（markdown-tools）

## 一、能力边界速查卡

本 Skill 定位为 Markdown 文档的**处理工具集**，覆盖编辑辅助、预览生成、格式转换三大场景。

### ✅ 能做（核心能力）

| 编号 | 能力项 | 说明 | 典型输入示例 |
|------|--------|------|--------------|
| 1 | 数据/文件/URL 转结构化结果 | 将外部内容解析为 Markdown 结构化文档 | 网页 URL、PDF 文件路径、纯文本片段 |
| 2 | 关键信息识别与保留 | 自动提取标题层级、列表结构、代码块、表格、链接等 Markdown 元素 | 混合格式的原始文本 |
| 3 | 按约定格式生成输出 | 支持自定义输出模板（如 GitHub 风格、学术风格、简洁风格） | 模板参数 + 源内容 |
| 4 | 置信度提示 | 对解析不确定的内容标注置信度等级 | 扫描件 OCR 结果、乱码文本 |
| 5 | 批量处理与自定义格式 | 支持多文件批量转换、自定义文件命名规则 | 文件夹路径 + 通配符 |

### ❌ 不能做（明确边界）

| 编号 | 限制项 | 说明 |
|------|--------|------|
| 1 | 不执行代码 | 不运行 Markdown 内嵌的代码块，仅做文本处理 |
| 2 | 不处理加密文件 | 密码保护的 PDF/Office 文件需先解密 |
| 3 | 不进行语义理解 | 不判断文档内容的正确性、逻辑性，仅做格式处理 |
| 4 | 不保留复杂排版 | 多栏布局、浮动图片等复杂排版会降级为线性结构 |
| 5 | 不处理超大文件 | 单文件建议不超过 20MB，超过需分段处理 |

### 适用对象

- **内容创作者**：需要将零散笔记整理为规范 Markdown
- **技术文档工程师**：需要批量转换 API 文档、代码注释
- **数据分析师**：需要将报表数据转为 Markdown 表格
- **普通办公用户**：需要将 PDF/Word 内容转为可编辑 Markdown


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
