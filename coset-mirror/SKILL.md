---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: coset-mirror
name: coset-mirror
displayName: 数据镜像 结构转换 字段映射
description: 将输入数据转换为结构化结果，保留关键信息并标注置信度。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/coset-mirror
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 墨规
agent_created: true
trigger_words: ["coset mirror", "镜像转换", "数据映射", "结构化输出", "字段提取"]
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

# coset-mirror Skill 文档

## 一、能力边界（一页纸速查卡）

### 能做（核心能力）

| 编号 | 能力项 | 说明 | 示例 |
|------|--------|------|------|
| 1 | 数据/文件/URL 输入解析 | 接受文本、文件路径、URL 作为输入源 | `coset mirror --input ./data.txt` |
| 2 | 关键信息识别与保留 | 自动提取输入中的核心字段，保留原始语义 | 从日志中提取时间戳、级别、消息体 |
| 3 | 结构化结果生成 | 按约定 schema 输出 JSON/YAML 格式 | 输出 `{"timestamp": "...", "level": "..."}` |
| 4 | 置信度标注 | 对每个字段标注提取置信度（高/中/低） | `"confidence": 0.95` |
| 5 | 批量处理与自定义格式 | 支持多文件/多 URL 批量处理，可自定义输出模板 | `--batch --format jsonl` |

### 不能做（明确边界）

| 编号 | 限制项 | 说明 |
|------|--------|------|
| 1 | 不执行代码 | 不运行输入中的脚本或程序 |
| 2 | 不访问私有网络 | 仅处理用户明确提供的 URL，不主动爬取 |
| 3 | 不修改原始数据 | 输出为独立副本，不覆盖输入文件 |
| 4 | 不处理加密内容 | 对加密/压缩文件需用户先解密 |
| 5 | 不保证字段完整性 | 输入缺失时输出 `[需核实:字段名]` 占位 |

### 适用对象

- 需要将非结构化文本转为结构化数据的开发者
- 需要批量提取日志/文档关键字段的运维人员
- 需要统一多来源数据格式的数据工程师


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
