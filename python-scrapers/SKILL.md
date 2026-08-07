---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: python-scrapers
name: python-scrapers
displayName: 网页采集 表格化提取 字段映射
description: 将网页、文件或原始数据转化为结构化表格，支持批量处理与自定义字段映射。
version: 1.0.2
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/python-scrapers
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: DataForge Studio
agent_created: true
trigger_words: ["爬虫采集", "数据抓取", "网页解析", "结构化提取", "批量采集", "表格化", "字段映射"]
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

# python-scrapers 技能文档

## 一、能力边界（一页纸速查卡）

### 1.1 能做什么

| 能力项 | 说明 | 典型场景 |
|--------|------|----------|
| 网页内容采集 | 从静态或动态网页中提取文本、链接、表格数据 | 新闻列表、商品信息、公告通知 |
| 文件内容解析 | 解析 CSV、JSON、XML、HTML 文件中的结构化数据 | 导出报表、日志分析、配置读取 |
| 原始数据清洗 | 对抓取到的脏数据进行去重、去空白、类型转换 | 去除 HTML 标签、统一日期格式 |
| 自定义字段映射 | 将源数据字段重命名、拆分、合并，映射到目标表结构 | 将"发布时间"拆分为"日期"和"时刻" |
| 批量处理 | 对多个 URL 或文件批量执行同一套采集与转换逻辑 | 采集 100 个商品页、处理 50 个日志文件 |
| 输出表格化 | 将处理结果统一输出为 CSV 或 Markdown 表格 | 生成数据报告、导入数据库 |

### 1.2 不能做什么

| 限制项 | 说明 |
|--------|------|
| 不处理登录墙 | 需要登录才能访问的页面不在本技能处理范围内 |
| 不绕过反爬机制 | 不提供验证码破解、IP 轮换、指纹伪装等功能 |
| 不执行 JavaScript 渲染 | 仅处理服务端返回的原始 HTML，不模拟浏览器渲染 |
| 不处理二进制文件 | PDF、图片、音视频等非文本格式不在解析范围内 |
| 不保证数据完整性 | 若源数据本身缺失或格式异常，输出结果可能不完整 |

### 1.3 适用对象

- 需要将网页数据整理为表格的运营人员
- 需要批量提取文件信息的分析人员
- 需要快速搭建数据管道的开发人员
- 需要将非结构化数据转为结构化数据的任何角色


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
