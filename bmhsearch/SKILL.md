---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: bmhsearch
name: bmhsearch
displayName: 多段文本解析 快速检索定位 字段抽取
description: 基于BMH算法的多段文本快速检索与结构化解析工具。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/bmhsearch
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 检索工坊
agent_created: true
trigger_words: ["bmhsearch", "快速检索", "多段解析", "字符串查找", "文本定位", "字段抽取"]
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

# bmhsearch — 多段文本快速检索与结构化解析

## 一、能力边界：一页纸速查卡

### 1.1 能做什么（核心能力清单）

| 序号 | 能力项 | 说明 | 典型场景 |
|------|--------|------|----------|
| 1 | 多段文本检索 | 在长文本中快速定位多个目标字符串（BMH 算法，平均亚线性复杂度） | 日志文件中的错误码扫描 |
| 2 | 结构化结果输出 | 将检索命中的位置、上下文、频次整理为 JSON/CSV 等结构化格式 | 批量提取合同中的关键条款 |
| 3 | 关键信息保留 | 自动保留输入中的原始上下文（前后 N 字符），不丢失源信息 | 从 HTML 源码中抽取指定标签内容 |
| 4 | 置信度标注 | 对每个命中结果标注匹配置信度（高/中/低），辅助人工复核 | 模糊匹配场景下的结果筛选 |
| 5 | 批量与自定义格式 | 支持多文件/多 URL 输入，支持自定义输出模板 | 爬虫抓取后的批量字段清洗 |

### 1.2 不能做什么（明确边界）

| 序号 | 限制项 | 说明 |
|------|--------|------|
| 1 | 不支持正则表达式 | 仅支持字面量字符串匹配，如需正则请配合其他工具 |
| 2 | 不支持模糊匹配 | 匹配基于精确字节比对，不做拼写纠错或近似度计算 |
| 3 | 不处理编码转换 | 输入输出编码需保持一致（默认 UTF-8） |
| 4 | 不执行远程请求 | 仅接受用户提供的 URL 文本内容，不主动发起网络请求 |
| 5 | 不修改源文件 | 所有操作均为只读，输出结果独立生成 |

### 1.3 适用对象

- 需要快速定位日志中特定错误码的运维人员
- 需要从多份文档中抽取统一字段的数据处理工程师
- 需要批量解析 URL 参数或 HTML 标签的爬虫开发者
- 任何需要在长文本中做多关键字定位的脚本使用者


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
