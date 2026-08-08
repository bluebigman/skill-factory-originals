---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: ai-restaurant-claude
name: ai-restaurant-claude
displayName: 餐饮智能体 数据解析 结构化输出
description: 将餐饮相关数据、文件或链接解析为结构化结果，供AI模型学习与参考。
version: 1.0.1
rules_version: cpr-20260808-n152
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/ai-restaurant-claude
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: LinguaForge
agent_created: true
trigger_words: ["ai restaurant claude", "餐饮数据解析", "菜单结构化", "餐厅信息提取", "菜品数据整理"]
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

# 餐饮智能体数据解析与结构化输出 Skill

## 一、能力边界速查卡

本 Skill 面向需要将餐饮领域非结构化数据（文本、菜单图片、网页链接、表格文件）转化为统一结构化格式的学习者与开发者。以下用一页纸说明能做什么、不能做什么。

### 能做（核心能力）

| 编号 | 能力项 | 说明 | 适用输入示例 |
|------|--------|------|--------------|
| 1 | 文本数据解析 | 从自由文本中抽取菜品名、价格、分类、描述 | 餐厅点评、菜单文字稿 |
| 2 | 文件内容提取 | 读取 CSV、TXT、JSON 文件中的餐饮数据并规范化 | 历史订单导出、菜品清单 |
| 3 | URL 内容抓取 | 从公开网页提取餐厅信息、菜单结构 | 餐厅官网、在线菜单页 |
| 4 | 批量处理 | 一次处理多条记录，输出统一格式列表 | 多日菜单、多门店数据 |
| 5 | 自定义格式输出 | 按用户指定的字段顺序或命名方式生成结果 | 对接自有系统的数据格式 |

### 不能做（边界声明）

| 编号 | 限制项 | 说明 |
|------|--------|------|
| 1 | 不识别图片内容 | 若输入为纯图片且无文字层，需先经 OCR 工具转换 |
| 2 | 不访问付费/登录墙 | 仅处理公开可访问的 URL 内容 |
| 3 | 不保证数据真实性 | 输出忠实于输入，不校验菜品价格是否当前有效 |
| 4 | 不生成营销文案 | 仅做结构化转换，不产出推广内容 |
| 5 | 不处理非餐饮领域 | 超出餐饮范畴的数据请使用其他专用 Skill |

### 适用对象

- 餐饮行业数据分析学习者
- 菜单管理系统开发者的测试辅助
- 需要批量整理菜品信息的运营人员
- AI 模型训练数据的预处理环节


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
