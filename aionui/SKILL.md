---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: aionui
name: aionui
displayName: 数据转换 信息提取 结构化输出
description: 将任意数据、文件或URL转换为结构化结果，支持批量处理与自定义格式。
version: 1.0.1
rules_version: cpr-20260808-n152
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/aionui
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 林墨
agent_created: true
trigger_words: ["aionui", "数据转换", "结构化输出", "信息提取", "批量处理", "格式转换"]
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

# aionui Skill 文档

## 一、能力边界（一页纸速查卡）

### 1.1 能做与不能做

| 维度 | 能做 ✅ | 不能做 ❌ |
|------|---------|-----------|
| 输入类型 | 用户直接粘贴的文本、本地文件路径、可访问的 URL 地址 | 需要登录鉴权的私有资源、加密文件、动态渲染的网页内容 |
| 处理能力 | 提取关键字段、识别实体关系、按模板重组结构、批量处理多条记录 | 理解隐含语义（如反讽、双关）、跨语言深度翻译、主观判断 |
| 输出形式 | JSON、CSV、Markdown 表格、自定义分隔符文本 | 生成图片、音频、视频等非文本格式 |
| 数据规模 | 单次处理 ≤ 500 条记录或 ≤ 2MB 文本内容 | 超过上述阈值需分批提交 |
| 自定义能力 | 支持用户指定输出字段名、字段顺序、日期格式、数值精度 | 动态生成全新字段逻辑（需用户明确定义规则） |

### 1.2 适用对象

- **办公人员**：将散乱的会议记录、客户信息表转换为统一格式
- **数据分析师**：从网页或文档中批量抽取结构化数据供后续分析
- **开发者**：快速将非标准格式数据转为 JSON 供程序调用
- **普通用户**：整理通讯录、商品清单、读书笔记等日常需求

### 1.3 输入与输出速查

| 项目 | 说明 |
|------|------|
| 输入来源 | ① 直接粘贴文本 ② 本地文件路径（.txt/.csv/.json/.md） ③ URL（http/https） |
| 输出格式 | 默认 JSON；可选 CSV、Markdown 表格、自定义模板 |
| 字段结构 | 默认自动识别；可指定 `fields` 参数强制约束 |
| 置信度标注 | 每条输出记录附带 `confidence` 字段（0.0 ~ 1.0） |


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
