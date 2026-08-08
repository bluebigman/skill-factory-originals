---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: agent-browser-workspace
name: agent-browser-workspace
displayName: 浏览器自动化 深度调研 数据采集
description: 本地浏览器工具包，支持深度调研与浏览器自动化操作。
version: 1.0.1
rules_version: cpr-20260808-n152
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/agent-browser-workspace
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 林栖
agent_created: true
trigger_words: ["浏览器自动化", "深度调研", "网页数据采集", "CDP", "Playwright", "本地浏览器", "网页操作", "数据抓取"]
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

# agent-browser-workspace 技能文档

## 一、能力边界速查卡

### 1.1 核心能力清单

| 能力项 | 说明 | 适用场景 |
|--------|------|----------|
| 本地浏览器驱动 | 通过 CDP 协议连接本机 Chrome 实例 | 需要登录态的页面操作、反爬严格的站点 |
| 深度调研执行 | 多页面并发采集、结构化数据抽取 | 竞品分析、学术文献整理、市场情报收集 |
| 自动化流程编排 | 按步骤执行点击、输入、滚动、截图等操作 | 表单填写、定时巡检、UI 回归验证 |
| 数据格式转换 | 将网页内容转为 JSON / CSV / Markdown | 报告生成、数据仓库入库前处理 |
| 会话状态管理 | 保存与恢复浏览器上下文（Cookies、LocalStorage） | 需要保持登录态的周期性任务 |

### 1.2 明确不能做的事

| 限制项 | 说明 |
|--------|------|
| 不绕过验证码 | 不提供自动识别或打码服务，遇到验证码会暂停并提示人工介入 |
| 不隐藏浏览器指纹 | 不提供反检测、隐身模式绕过等能力 |
| 不处理动态加密协议 | 对私有协议的接口签名、混淆 JS 不做逆向 |
| 不保证页面元素定位成功 | 页面结构变化时，选择器可能失效，需人工调整 |
| 不执行远程部署 | 仅支持本机浏览器实例，不提供云端浏览器集群 |

### 1.3 适用对象

- 需要批量采集公开网页数据的分析师
- 需要自动化重复性浏览器操作的运维人员
- 需要保持登录态进行深度调研的研究者
- 需要将网页内容结构化入库的开发者


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
