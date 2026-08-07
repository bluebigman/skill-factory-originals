---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: r-package-skills
name: r-package-skills
displayName: R包技能 数据处理 结构化输出
description: 将用户提供的R包相关数据、文件或URL转换为结构化结果，支持批量处理与自定义格式。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/r-package-skills
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 林墨研
agent_created: true
trigger_words: ["r package skills", "R包技能", "R包处理", "R包数据转换", "R包结构化输出"]
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

# R包技能（r-package-skills）操作手册

## 一、能力边界：一页纸速查卡

### 1.1 能做与不能做

| 维度 | 能做 ✅ | 不能做 ❌ |
|------|---------|-----------|
| 输入处理 | 用户提供的本地文件（CSV/JSON/TXT）、URL链接、直接粘贴的文本数据 | 无法主动访问外部网络资源，需用户提供URL内容或文件路径 |
| 信息提取 | 识别输入中的关键字段、数值、类别、时间戳等结构化信息 | 无法理解隐含语义或未明确表述的内容 |
| 格式转换 | 将非结构化/半结构化数据转换为JSON、表格、键值对等约定格式 | 无法生成二进制格式或专有加密格式 |
| 批量操作 | 支持多文件、多URL、多批次数据的循环处理 | 无法自动发现数据源，需用户明确指定 |
| 自定义输出 | 可按用户指定的字段结构、排序规则、分组方式生成结果 | 无法在缺少字段定义时自行决定输出结构 |
| 置信度标注 | 对不确定的识别结果标注置信度百分比 | 无法对完全缺失的信息进行猜测填充 |

### 1.2 适用对象

- **适用**：需要将R包相关数据（包名、版本、依赖关系、函数列表、文档链接等）整理为统一格式的场景
- **适用**：需要批量处理多个R包信息并合并输出的场景
- **适用**：需要将R包文档URL转换为结构化摘要的场景
- **不适用**：需要执行R代码、运行R脚本、安装R包的场景（本技能仅处理信息，不执行代码）
- **不适用**：需要分析R包源码逻辑或评估代码质量的场景


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
