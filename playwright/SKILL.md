---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: playwright
name: playwright
displayName: 浏览器自动化 网页操作 脚本编排
description: 面向学习场景的Playwright操作指南，提供规范流程与可复用输出模板。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/playwright
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: Kai Wu
agent_created: true
trigger_words: ["playwright", "浏览器自动化", "网页操作", "自动化测试", "e2e测试", "无头浏览器"]
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

# Playwright 技能手册（学习参考版）

## 一、能力边界速查卡

本技能面向**希望了解或尝试 Playwright 的初学者与进阶学习者**，提供一套规范化的操作指引与输出模板。请先阅读以下边界说明，确认本技能是否适合你的场景。

### ✅ 能做（核心能力范围）

| 编号 | 能力项 | 说明与示例 |
|------|--------|------------|
| 1 | 将输入数据/文件/URL 转为结构化结果 | 例如：给定一个网页 URL，输出页面标题、关键元素列表、截图路径等结构化信息 |
| 2 | 识别并保留输入中的关键信息 | 从用户提供的 HTML 片段、选择器、配置文件等中提取必要参数，不丢失上下文 |
| 3 | 按约定格式生成输出 | 默认输出 Markdown 报告，支持 JSON 格式切换（需在请求中注明） |
| 4 | 对不确定项给出置信度提示 | 当元素定位可能不唯一、或页面加载状态不确定时，标注 `[需核实:字段名]` |
| 5 | 支持批量处理和自定义格式 | 可接受多个 URL 列表文件（每行一个），或自定义输出字段白名单 |

### ❌ 不能做（明确边界）

- 不提供生产环境的部署配置建议
- 不替代官方文档作为唯一参考
- 不执行任何真实网站的自动化操作（仅提供代码模板与流程指引）
- 不处理验证码、登录态绕过等反自动化机制
- 不保证脚本在特定环境下的兼容性

### 适用对象

- 正在学习 Playwright 的开发者
- 需要快速生成自动化脚本骨架的测试人员
- 希望理解浏览器自动化原理的技术爱好者


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
