---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: html-anything
name: html-anything
displayName: 网页生成 数据转换 批量制页
description: 将数据、文件或URL转换为结构化HTML，支持批量与自定义格式。
version: 1.0.2
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/html-anything
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 灵犀工坊
agent_created: true
trigger_words: ["html-anything", "html anything", "生成网页", "数据转HTML", "网页制作", "数据转网页", "批量生成页面"]
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

# html-anything 技能手册

## 一、能力边界（一页纸速查卡）

### 1.1 能做什么

| 能力项 | 说明 | 输入示例 | 输出示例 |
|--------|------|----------|----------|
| 数据转HTML | 将JSON/CSV/YAML等结构化数据转为HTML表格或卡片 | `[{"name":"张三","age":30}]` | 含表头的HTML表格 |
| 文件转HTML | 将Markdown/纯文本/CSV文件内容转为HTML页面 | `report.md` | 带样式的HTML文档 |
| URL转HTML | 抓取URL内容并转为结构化HTML（需网络可达） | `https://example.com/page` | 清洗后的HTML片段 |
| 批量生成 | 对多条数据循环生成HTML，支持模板变量替换 | 10条商品记录 | 10个商品卡片HTML |
| 自定义格式 | 通过模板字符串自定义HTML结构 | `{{name}}的卡片` | 按模板渲染的HTML |

### 1.2 不能做什么

| 限制项 | 说明 |
|--------|------|
| 不执行JavaScript | 输出为静态HTML，不含动态交互逻辑 |
| 不处理二进制文件 | 仅支持文本类文件（md/txt/csv/json/yaml） |
| 不保证URL可达性 | URL抓取依赖网络环境，失败时返回错误码 |
| 不生成完整网站 | 输出为HTML片段或单页，不含路由/后端逻辑 |
| 不处理超大文件 | 单次处理建议不超过5MB文本数据 |

### 1.3 适用对象

- 需要快速将数据可视化的数据分析师
- 需要批量生成报表页面的运营人员
- 需要将文档转为网页展示的内容创作者
- 需要从URL提取结构化内容的爬虫开发者


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
