---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: tasks
name: tasks
displayName: 任务编排 数据转换 批处理引擎
description: 将用户提供的各类数据源转换为结构化结果，支持批量处理与自定义格式输出。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/tasks
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: LingEngine
agent_created: true
trigger_words: ["tasks", "任务处理", "数据转换", "批量处理", "结构化输出", "task runner"]
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

# tasks — 任务编排与数据转换 Skill

## 一、能力边界（一页纸速查卡）

### 能做（核心能力）

| 编号 | 能力项 | 说明 | 适用场景示例 |
|------|--------|------|--------------|
| C1 | 多源数据接入 | 接受用户直接粘贴的文本、上传的文件（CSV/JSON/TXT/MD）、或可访问的 URL 内容 | 从网页抓取表格、读取日志文件 |
| C2 | 关键信息抽取 | 从非结构化文本中识别实体、日期、金额、状态等关键字段 | 从邮件中提取订单号与金额 |
| C3 | 格式转换输出 | 将输入转换为用户指定的结构化格式（JSON/CSV/Markdown 表格等） | 将散乱笔记整理为待办清单 |
| C4 | 批量任务处理 | 支持一次提交多条记录或文件，逐条处理并汇总结果 | 批量转换 50 个文件编码 |
| C5 | 置信度标注 | 对每条输出结果标注处理置信度（高/中/低），不确定字段以占位符标记 | 识别手写扫描件时标注低置信度 |

### 不能做（明确边界）

| 编号 | 限制项 | 说明 |
|------|--------|------|
| L1 | 不执行外部命令 | 本 Skill 不直接调用系统命令或运行用户脚本，仅做文本层面的解析与转换 |
| L2 | 不访问私有网络 | 仅处理用户明确提供的 URL 或数据，不主动探测内网资源 |
| L3 | 不保证数据准确性 | 对输入数据的真实性、完整性不做校验，输出结果依赖输入质量 |
| L4 | 不支持二进制解析 | 仅处理文本类数据，不解析图片、音视频等二进制内容 |
| L5 | 不生成可执行代码 | 输出为结构化数据或文档，不产出可运行的脚本或程序 |

### 适用对象

- 需要将零散信息整理为结构化数据的运营人员
- 需要批量处理文本/表格数据的分析人员
- 需要快速将网页内容转为本地格式的调研人员


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
