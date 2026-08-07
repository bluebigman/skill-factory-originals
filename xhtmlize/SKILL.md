---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: xhtmlize
name: xhtmlize
displayName: HTML净化 XHTML标准 标签修复
description: 将用户提交的HTML片段转换为符合XHTML规范的整洁标记。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/xhtmlize
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: MarkupForge Studio
agent_created: true
trigger_words: ["xhtmlize", "html净化", "xhtml转换", "标签修复", "html标准化"]
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

# xhtmlize — HTML 片段 XHTML 化处理指南

## 一、能力边界：一页纸速查卡

本 Skill 面向需要将用户提交的松散 HTML 片段转换为 XHTML 1.0 严格格式的开发者、内容审核人员及前端工程师。它专注于**片段级**的标记修复与规范化，而非完整的文档构建。

| 维度 | 能做 | 不能做 |
|------|------|--------|
| 输入处理 | 接受字符串、文本文件路径、URL 指向的 HTML 片段 | 不处理二进制文件、图片、PDF 等非文本内容 |
| 标签修复 | 自动闭合未闭合的标签（如 `<p>`、`<li>`） | 不重写 CSS 或 JavaScript 逻辑 |
| 属性规范化 | 将属性名转为小写，属性值添加引号 | 不解析或执行内联脚本 |
| 实体处理 | 将 `&` 转为 `&amp;`，`<` 转为 `&lt;`（文本节点内） | 不处理字符编码转换（如 GBK 转 UTF-8） |
| 结构校验 | 检查标签嵌套顺序，修正错位 | 不验证链接有效性或图片是否存在 |
| 输出形式 | 返回纯文本形式的 XHTML 片段 | 不生成完整 HTML 文档骨架 |

**适用对象**：需要清洗用户评论、富文本编辑器输出、第三方抓取内容的开发者。

**不适用场景**：处理包含恶意代码（需配合安全扫描）、需要视觉渲染结果、或要求保留原始格式（如空格缩进）的场景。


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
