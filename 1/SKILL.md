---
> 本内容由 AI 生成，仅供学习参考（《人工智能生成合成内容标识办法》显式标识）。
<!-- ai-generated-notice -->
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: data-parsing-structure-conversion
name: 数据解析与结构化转换
displayName: 数据解析 结构化转换 置信度标注
description: 将用户提供的原始数据、文件或URL解析为结构化结果，并标注置信度。
version: 1.0.2
rules_version: cpr-20260808-n152
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/1
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 林墨
agent_created: true
trigger_words:
  - "1"
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

# 数据解析与结构化转换 Skill

## 📖 阅读指南（分层次路径）

> **新手快速上手**：阅读「一、能力边界」→「三、标准执行流程」→「五、参数配置表」→「七、FAQ 与反模式」即可完成 80% 的日常任务。
> **进阶用户**：在此基础上补充阅读「四、高级用法」→「六、智能洞察与质量评估」→「八、错误码体系」，可解锁全部能力。
> **深度定制用户**：完整阅读全文，重点关注「九、稳定性与降级策略」和「十、安全与合规声明」。

---

## 一、能力边界（一页纸速查卡）

### 能做（核心能力）

| 编号 | 能力项 | 说明 | 适用场景示例 |
|------|--------|------|--------------|
| 1 | 原始数据解析 | 从文本、表格、日志中提取关键字段 | 用户粘贴一段合同条款，提取甲方、乙方、金额 |
| 2 | 文件内容识别 | 读取常见文本格式（.txt, .md, .csv, .json, .xml, .yaml） | 用户上传 CSV 文件，要求转为 JSON 结构 |
| 3 | URL 内容抓取 | 访问公开网页并提取正文关键信息 | 用户提供新闻链接，要求提取标题、时间、核心事件 |
| 4 | 结构化输出生成 | 按用户指定的字段结构输出结果 | 用户要求"输出为表格，含名称、数量、单位" |
| 5 | 批量处理与格式自定义 | 一次处理多条记录，支持自定义分隔符和字段映射 | 用户提供 50 条日志，要求按错误级别分组输出 |
| 6 | 数据清洗与标准化 | 去除重复项、统一日期格式、修正编码问题 | 用户提供混合格式的日期列，要求统一为 ISO 8601 |
| 7 | 字段映射与重命名 | 将源字段名映射为目标字段名，支持别名 | 用户要求将 "cust_id" 映射为 "customerId" |
| 8 | 智能洞察与质量评分 | 自动识别数据模式、异常值，并给出质量评分 | 用户要求评估数据完整性和一致性 |

### 不能做（明确边界）

- **不能**访问需要登录认证的页面或接口
- **不能**解析图片、音频、视频中的非文字内容（OCR 不在本 Skill 范围内）
- **不能**对输入内容进行语义扩展或主观判断（仅做提取与整理）
- **不能**保证输入源本身的真实性、准确性
- **不能**处理超过 10,000 字或 5MB 的单个输入（超出时需分段处理）
- **不能**执行跨数据源的关联分析（如数据库 JOIN 操作）
- **不能**自动生成业务结论或决策建议（仅提供数据洞察，不替代人工判断）

### 适用对象

| 用户类型 | 典型需求 | 推荐用法 |
|----------|----------|----------|
| 运营人员 | 快速整理非结构化文本（如用户反馈、评论） | 使用「原始数据解析」+「数据清洗」 |
| 研发人员 | 将日志/报表转为统一格式 | 使用「批量处理」+「字段映射」 |
| 研究人员 | 从网页提取关键信息 | 使用「URL 内容抓取」+「智能洞察」 |
| 数据分析师 | 多源数据标准化 | 使用「格式转换」+「质量评分」 |

---

## 二、触发方式（大白话映射表）

当用户说出以下任何一句话时，本 Skill 应被激活：

| 用户可能说的话（大白话） | 触发词（正式） | 触发动作 |
|--------------------------|----------------|----------|
| "帮我把这段文字整理成表格" | 数据解析、结构化输出 | 启动解析流程 |
| "这个 CSV 文件能转成 JSON 吗？" | 格式转换 | 启动格式转换 |
| "从这篇新闻里提取关键信息" | 信息提取 | 启动 URL 抓取 |
| "把日志按错误级别分一下组" | 日志分析 | 启动批量处理 |
| "这堆数据里有重复的，帮我清一下" | 数据清洗 | 启动清洗流程 |
| "把 'name' 字段改成 'fullName'" | 字段映射 | 启动映射流程 |
| "这个数据质量怎么样？" | 质量评估 | 启动智能洞察 |
| "帮我看看这段代码有什么问题" | 代码审查 | 启动代码审查流程 |
| "把这几列合并成一列" | 格式转换 | 启动转换流程 |
| "这个网页上的价格信息能抓下来吗？" | 网页抓取 | 启动 URL 抓取 |

> **触发优先级**：当用户输入同时命中多个触发词时，按以下优先级处理：
> 1. 代码审查（最高，涉及代码安全）
> 2. 数据清洗（涉及数据完整性）
> 3. 格式转换（涉及输出结构）
> 4. 信息提取（涉及内容解析）
> 5. 其他（按出现顺序）

---

## 三、标准执行流程

### 步骤 0：输入确认与参数初始化

在开始处理前，先确认以下信息：


## 失败处理
- 输入不符合预期 → 返回错误说明与正确的输入格式示例
- 执行中异常 → 保留中间结果，报告失败原因与已处理进度
- 依赖缺失 → 给出安装命令并重试一次

## 前置条件
- 无特殊环境要求

## 执行步骤
1. 收集用户输入并确认格式
2. 按功能逻辑处理输入内容
3. 生成结果并校验完整性

## 输出
- 结构化文本结果，附处理说明


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
