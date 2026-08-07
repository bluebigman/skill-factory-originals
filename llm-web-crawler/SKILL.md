---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: llm-web-crawler
name: llm-web-crawler
displayName: 网页采集 结构化提取 数据清洗
description: 将网页、文件或原始文本转化为结构化数据，供LLM应用与自动化流程直接调用。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/llm-web-crawler
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 数据工坊
agent_created: true
trigger_words: ["爬虫采集", "网页抓取", "数据提取", "结构化输出", "web scraper", "crawler", "信息采集", "页面解析"]

> 本内容由 AI 生成，仅供学习参考 <!-- ai-generated-notice -->

---

> 📜 **用户协议（User Agreement）**
> 1. 本 Skill 仅供学习与参考用途。使用本 Skill 产生的任何结果，由使用者自行承担全部责任；本 Skill 不提供任何明示或暗示的保证。
> 2. 涉及法律、财务、税务、投资、医疗等专业决策时，请务必咨询持证专业人士。
> 3. 本代码受版权法保护，未经授权复制、反向工程或商业利用将被追究法律责任。
<!-- user-agreement-injected -->


> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->

# LLM Web Crawler — 网页采集与结构化提取 Skill

## 一、能力边界（一页纸速查卡）

本 Skill 面向需要从非结构化来源（网页、文本、文件）中提取关键信息的场景，适用于 LLM 应用的数据预处理、自动化工作流的数据入口、以及低代码平台的数据清洗环节。

### 能做（5 项核心能力）

| 编号 | 能力项 | 说明 | 典型输入 | 典型输出 |
|------|--------|------|----------|----------|
| 1 | 内容解析 | 从 URL、HTML、纯文本中提取正文与元信息 | `https://example.com/news/123` | `{title, author, publish_date, content}` |
| 2 | 关键信息识别 | 根据用户指定的字段定义，从文本中抽取对应实体 | 一段招聘启事文本 | `{company, position, salary_range, location}` |
| 3 | 结构化转换 | 将自由文本转换为 JSON / CSV / Markdown 表格 | 一段产品描述 | `[{name, price, spec}]` |
| 4 | 批量处理 | 支持多条记录或列表页的循环抓取与合并 | 10 个商品 URL 列表 | 合并后的结构化数组 |
| 5 | 置信度标注 | 对不确定的字段输出置信度标记，不强行编造 | 模糊的日期或缺失的作者信息 | `{publish_date: "[需核实:publish_date]"}` |

### 不能做（明确边界）

| 编号 | 限制项 | 说明 |
|------|--------|------|
| 1 | 不执行 JS 渲染 | 仅处理静态 HTML 或用户直接提供的文本，不运行浏览器内核 |
| 2 | 不绕过登录/验证码 | 不处理需要认证、付费墙或验证码拦截的页面 |
| 3 | 不进行深度递归爬取 | 默认只抓取单页或用户显式指定的 URL 列表，不做站内全量遍历 |
| 4 | 不保证字段必现 | 若源数据中不存在某字段，输出占位符而非猜测值 |
| 5 | 不处理二进制文件 | 不支持 PDF、图片、音视频的直接解析（需用户先转文本） |

### 适用对象

- 需要将网页内容灌入知识库的 RAG 应用开发者
- 需要定期采集竞品信息的运营人员
- 需要将非结构化文档转为表格数据的分析师
- 低代码平台（如 n8n、Zapier）中需要数据预处理节点的使用者


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
