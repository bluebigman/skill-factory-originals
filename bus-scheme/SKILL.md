---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: bus-scheme
name: bus-scheme
displayName: 公交编码 数据解析 结构化转换
description: 将公交场景中的杂散数据解析为结构化结果，支持文件与URL输入。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/bus-scheme
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: transit-forge
agent_created: true
trigger_words: ["bus-scheme", "公交方案", "线路数据解析", "公交编码", "scheme转换"]

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

# bus-scheme — 公交编码数据解析与结构化转换

## 一、能力边界（一页纸速查卡）

### 1.1 能做

| 序号 | 能力项 | 说明 |
|------|--------|------|
| 1 | 多源输入解析 | 接受用户直接粘贴的文本、本地文件路径、远程 URL 三种输入来源 |
| 2 | 关键信息抽取 | 从原始数据中识别线路编号、站点名称、经纬度、时间戳、票价等核心字段 |
| 3 | 结构化输出 | 按约定 JSON Schema 输出，字段名固定，便于下游程序消费 |
| 4 | 置信度标注 | 对每个输出字段附带 confidence 等级（high / medium / low） |
| 5 | 批量与自定义 | 支持一次处理多条记录；可通过参数指定输出字段子集或自定义分隔符 |

### 1.2 不能做

- 不执行实时公交 API 调用（仅解析用户提供的数据）
- 不进行地图渲染或路线可视化
- 不修改原始输入文件（只读解析）
- 不处理非文本二进制格式（如 PDF 扫描件、图片）
- 不保证解析结果绝对正确（受输入质量影响）

### 1.3 适用对象

- 需要将公交线路表、站点清单、运营日志等文本数据转为 JSON 的开发者
- 需要批量清洗公交数据集的运维人员
- 需要从 URL 抓取公交信息并结构化的数据工程师


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
