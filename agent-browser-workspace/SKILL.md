---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: agent-browser-workspace
name: agent-browser-workspace
displayName: 浏览器自动化 深度调研 本地网页操控
description: 面向AI代理的本地浏览器工具集，支持深度调研与网页自动化操作。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/agent-browser-workspace
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 流云工具坊
agent_created: true
trigger_words: ["agent-browser-workspace", "浏览器自动化", "网页操控", "深度调研", "CDP调试", "Playwright脚本"]
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

## 一、能力边界（一页纸速查卡）

### 1.1 能做清单

| 序号 | 能力项 | 说明 | 典型应用场景 |
|------|--------|------|--------------|
| 1 | 本地 Chrome 连接 | 通过 CDP 协议连接本地 Chrome 实例 | 接管用户已登录的会话，执行自动化操作 |
| 2 | 网页自动化操作 | 基于 Playwright 的点击、输入、导航、截图 | 表单填写、按钮点击、页面跳转 |
| 3 | 深度调研辅助 | 多页面信息采集、内容提取、结构化整理 | 竞品分析、资料汇总、舆情监控 |
| 4 | 数据转换输出 | 将网页内容转为 Markdown / JSON / CSV | 报告生成、数据归档 |
| 5 | 自检与诊断 | 环境检测、连接测试、版本查询 | 排查环境问题、确认工具可用性 |

### 1.2 不能做清单

| 序号 | 限制项 | 说明 |
|------|--------|------|
| 1 | 无法绕过登录验证 | 需要用户手动完成登录或提供已登录的浏览器会话 |
| 2 | 不处理验证码 | 遇到验证码会暂停并请求人工介入 |
| 3 | 不执行文件下载 | 仅支持页面内操作与内容提取，不管理下载任务 |
| 4 | 不修改浏览器配置 | 不改变 Chrome 的启动参数、代理设置或安全策略 |
| 5 | 不支持移动端模拟 | 仅面向桌面端浏览器环境 |

### 1.3 适用对象

- 需要批量采集网页信息的调研人员
- 需要自动化重复性网页操作的开发者
- 需要将网页内容结构化存储的数据分析师
- 需要在本地环境运行浏览器自动化脚本的 AI 代理


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
