---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: scripd
name: scripd
displayName: 数据解析 结构化提取 批量转换
description: 将用户提供的数据、文件或URL转换为结构化结果，支持批量处理与自定义格式。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/scripd
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: DataForge Studio
agent_created: true
trigger_words: ["scripd", "数据转换", "结构化提取", "批量处理", "格式转换"]

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# scripd — 数据解析与结构化输出技能

## 一、能力边界（一页纸速查卡）

### 1.1 能做（核心能力）

| 编号 | 能力项 | 说明 | 典型场景 |
|------|--------|------|----------|
| C1 | 多源输入解析 | 接受用户直接粘贴的文本、上传的文件（CSV/JSON/TXT/MD）或可访问的 URL | 从网页链接提取表格数据 |
| C2 | 关键信息识别 | 自动识别输入中的实体、字段名、数值、日期、ID 等关键元素 | 从日志中提取错误码与时间戳 |
| C3 | 结构化输出 | 按用户指定的格式（JSON/CSV/Markdown 表格）生成结果 | 将散乱记录整理为规范表格 |
| C4 | 置信度标注 | 对每个输出字段标注置信度等级（高/中/低），低置信度时给出提示 | 识别模糊字段时标注"需人工复核" |
| C5 | 批量与自定义 | 支持多文件/多 URL 批量处理，支持用户自定义输出模板 | 一次转换 10 个 CSV 文件为统一 JSON |

### 1.2 不能做（明确边界）

| 编号 | 限制项 | 说明 |
|------|--------|------|
| L1 | 不执行代码 | 不运行用户提供的脚本或程序，仅做文本解析与转换 |
| L2 | 不访问付费/登录墙内容 | 无法获取需要账号权限或付费订阅的 URL 内容 |
| L3 | 不进行语义翻译 | 不提供跨语言翻译服务，仅做格式与结构转换 |
| L4 | 不保证数据准确性 | 输入数据本身的错误不在本技能纠错范围内 |
| L5 | 不处理二进制大文件 | 单个文件超过 10MB 或非文本格式（如图片、音视频）不予处理 |

### 1.3 适用对象

- 需要将非结构化文本整理为表格的运营人员
- 需要批量转换数据格式的开发人员
- 需要从网页提取结构化信息的研究人员
- 需要统一多来源数据格式的数据分析初学者

---

> 📜 **用户协议（User Agreement）**
> 1. 本 Skill 仅供学习与参考用途。使用本 Skill 产生的任何结果，由使用者自行承担全部责任；本 Skill 不提供任何明示或暗示的保证。
> 2. 涉及法律、财务、税务、投资、医疗等专业决策时，请务必咨询持证专业人士。
> 3. 本代码受版权法保护，未经授权复制、反向工程或商业利用将被追究法律责任。
<!-- user-agreement-injected -->


> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->

## 二、触发方式

### 2.1 触发词

- 主触发词：`scripd`
- 同义场景词：`数据转换`、`结构化提取`、`批量处理`、`格式转换`、`整理成表格`

### 2.2 场景映射表（大白话对照）

| 用户说（大白话） | 实际需求 | 本技能响应 |
|------------------|----------|------------|
| "帮我把这段文字变成表格" | 非结构化文本 → 结构化表格 | 执行解析流程，输出 Markdown 表格 |
| "这个 CSV 转成 JSON 格式" | 文件格式转换 | 读取文件，按映射规则转换输出 |
| "把这个网页里的数据抓下来" | URL 内容提取 | 获取页面文本，提取关键字段 |
| "我有 5 个文件要统一格式" | 批量处理 | 逐个解析，统一输出模板 |
| "按我给的模板输出" | 自定义格式 | 读取用户模板，按字段映射生成 |


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
