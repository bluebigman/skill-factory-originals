---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: antigravity-god-mode
name: antigravity-god-mode
displayName: 全能工程 数据转换 批量处理
description: 将任意输入数据转化为结构化结果，支持批量处理与自定义格式输出。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/antigravity-god-mode
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: SkillForge Studio
agent_created: true
trigger_words: ["antigravity god mode", "god mode", "全能模式", "数据转换", "批量处理"]

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

---

> 📜 **用户协议（User Agreement）**
> 1. 本 Skill 仅供学习与参考用途。使用本 Skill 产生的任何结果，由使用者自行承担全部责任；本 Skill 不提供任何明示或暗示的保证。
> 2. 涉及法律、财务、税务、投资、医疗等专业决策时，请务必咨询持证专业人士。
> 3. 本代码受版权法保护，未经授权复制、反向工程或商业利用将被追究法律责任。
<!-- user-agreement-injected -->


> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->

# antigravity-god-mode 技能文档

## 一、能力边界速查卡

### 1.1 能做什么（5 项核心能力）

| 编号 | 能力项 | 说明 | 典型场景 |
|------|--------|------|----------|
| C1 | 数据/文件/URL 结构化转换 | 将用户提供的原始数据、文件内容或网页链接解析为结构化结果 | 把 CSV 转 JSON、抓取网页表格、解析日志文件 |
| C2 | 关键信息识别与保留 | 自动提取输入中的核心字段，保留上下文关联信息 | 从合同中提取甲方乙方、金额、日期 |
| C3 | 约定格式输出 | 按用户指定的文件类型（JSON/CSV/Markdown/YAML）和字段结构生成结果 | 生成符合 API 规范的请求体 |
| C4 | 置信度标注 | 对每个输出字段标注可信程度，低置信度时明确提示 | 识别手写扫描件时标注识别置信度 |
| C5 | 批量处理与自定义格式 | 支持多文件/多 URL 循环处理，支持用户自定义输出模板 | 批量转换 100 个 Excel 文件为 JSON |

### 1.2 不能做什么（明确边界）

| 编号 | 限制项 | 说明 |
|------|--------|------|
| L1 | 不执行代码 | 本技能仅做数据转换与格式化，不运行程序、不执行脚本 |
| L2 | 不访问私有网络 | 仅处理用户明确提供的 URL，不主动探测内网或受限资源 |
| L3 | 不猜测缺失数据 | 输入中不存在的信息，输出 `[需核实:字段名]` 占位，不编造 |
| L4 | 不保证转换无损 | 复杂嵌套结构转换时可能丢失格式信息，会提前告知风险 |
| L5 | 不处理加密内容 | 加密文件、密码保护的文档需用户先解密 |

### 1.3 适用对象

| 用户类型 | 适用程度 | 说明 |
|----------|----------|------|
| 数据分析师 | ✅ 高度适用 | 日常数据清洗、格式转换、批量处理 |
| 后端开发者 | ✅ 高度适用 | API 数据对接、日志解析、配置生成 |
| 产品经理 | ⚠️ 部分适用 | 简单表格转换可用，复杂逻辑需开发者协助 |
| 非技术用户 | ⚠️ 部分适用 | 需按模板提供输入，建议先阅读新手路径 |


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
