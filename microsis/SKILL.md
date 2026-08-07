---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: microsis
name: microsis
displayName: 旧档解析 结构化提取 字段还原
description: 将老旧数据/文件/URL解析为结构化结果，保留关键信息并标注置信度。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/microsis
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 独立技能工坊
agent_created: true
trigger_words: ["microsis", "旧数据解析", "结构化提取", "字段还原", "老旧文件转换"]

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

# microsis — 旧档解析与结构化提取

## 一、能力边界（一页纸速查卡）

### 1.1 能做与不能做

| 维度 | 能做 | 不能做 |
|------|------|--------|
| 输入 | 用户提供的数据片段、文本文件内容、URL 指向的文本资源 | 二进制文件直接解码、加密内容破解、需登录的私有系统抓取 |
| 处理 | 识别关键字段、提取实体、按约定模板重组结构 | 语义理解之外的业务判断、跨语言自动翻译、主观内容评价 |
| 输出 | 结构化文本（JSON/表格/键值对）、带置信度标注的字段集 | 生成可执行代码、自动写入外部数据库、替代人工审核 |
| 批量 | 支持多组输入逐条处理，输出可合并 | 无上限的流式处理、分布式并行计算 |
| 自定义 | 允许用户指定输出字段名、分组方式、排序规则 | 动态生成全新的输出协议（需预先约定） |

### 1.2 适用对象

- 需要将历史文本记录（如旧版日志、手写扫描件的 OCR 文本、老系统导出数据）转为结构化清单的运维或数据迁移人员。
- 需要从 URL 抓取公开文本并提取关键字段（如公告、新闻页中的日期/编号/主体）的分析人员。
- 需要快速核对一批数据中关键信息是否完整、格式是否统一的质检人员。

### 1.3 边界值参考

| 参数 | 建议上限 | 超出后的行为 |
|------|----------|--------------|
| 单次输入文本长度 | 8000 字符 | 截断处理，并在输出中标注 `[truncated]` |
| 批量处理条数 | 50 条/次 | 分批提示，不自动拆分 |
| 自定义字段数量 | 20 个 | 超出后仅保留前 20 个，并给出提示 |
| URL 抓取超时 | 10 秒 | 返回 `[fetch_timeout]` 占位 |


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
