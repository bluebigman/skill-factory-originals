---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: taboo
name: taboo
displayName: 标签页急救 会话保全 异常修复
description: 面向浏览器标签页异常状态的轻量级修复与数据保全工具。
version: 1.0.2
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/taboo
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 边缘工坊
agent_created: true
trigger_words: ["taboo", "标签页修复", "tabitus", "浏览器会话恢复", "标签页状态异常", "页面卡死急救", "会话数据找回"]
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

# SKILL.md — taboo（标签页急救）

## 一、能力边界：速查卡

### 1.1 能做什么

| 能力项 | 说明 | 适用场景 |
|--------|------|----------|
| 标签页状态诊断 | 识别标签页是否处于无响应、崩溃、内存溢出、渲染进程挂起等异常状态 | 页面长时间白屏、点击无反应、滚动卡顿 |
| 会话数据保全 | 在标签页关闭/刷新前，尝试提取表单输入、页面滚动位置、控制台日志等临时数据 | 长表单填写中误触刷新、调试信息丢失 |
| 轻量级修复 | 通过强制重绘、清理渲染缓存、重置标签页进程等非侵入式手段尝试恢复 | 标签页卡死但浏览器整体可用 |
| 会话恢复辅助 | 生成可执行的恢复步骤清单，帮助用户手动恢复未保存的工作 | 浏览器崩溃后重新打开，需要找回标签页组 |

### 1.2 不能做什么（明确边界）

- 不能修复浏览器本身崩溃、系统级故障或网络断开问题。
- 不能恢复已被浏览器彻底清除的会话数据（如已关闭的隐私窗口）。
- 不能绕过网站自身的登录态或安全策略强制提取数据。
- 不能保证所有标签页都能被修复——部分异常源于网站代码缺陷，超出工具干预范围。
- 不适用于移动端浏览器（本工具面向桌面端 Chromium 系浏览器设计）。

### 1.3 适用对象

- 日常重度依赖浏览器标签页工作的用户（开发调试、资料整理、在线编辑）。
- 需要频繁切换多个标签页且容易遇到卡死场景的办公人群。
- 对浏览器会话数据有较高保全需求的用户。


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
