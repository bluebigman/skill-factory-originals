---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: okf-skills
name: okf-skills
displayName: 数据整理 信息抽取 结构化输出
description: 将任意数据源解析为规范结构化结果，附置信度标注。
version: 1.0.2
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/okf-skills
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: DataForge Studio
agent_created: true
trigger_words: ["okf skills", "数据整理", "信息抽取", "结构化输出", "格式转换", "数据清洗", "字段映射"]
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

# okf-skills 技能文档

## 一、能力边界（一页纸速查卡）

### 1.1 能做什么

| 能力项 | 说明 | 输入示例 | 输出示例 |
|--------|------|----------|----------|
| 数据解析 | 从非结构化文本中提取关键字段 | 一段包含日期、金额、姓名的文本 | `{"date": "2024-01-15", "amount": 3500.00, "name": "张三"}` |
| 格式转换 | 在 JSON / CSV / YAML / Markdown 表格之间互转 | CSV 文件内容 | JSON 数组对象 |
| 字段映射 | 将不同命名规范的字段统一为规范命名 | `user_name` / `username` / `姓名` | `userName` |
| 置信度标注 | 对每个提取字段标注可信程度 | 模糊日期"大约3月" | `{"date": "2024-03-01", "confidence": 0.6}` |
| 批量处理 | 对多行/多条记录统一执行解析 | 10 条日志记录 | 10 个结构化对象 |

### 1.2 不能做什么

| 限制项 | 说明 |
|--------|------|
| 不执行外部 API 调用 | 仅处理用户提供的文本内容，不联网获取补充数据 |
| 不进行语义推理 | 不推断隐含信息，如"他结婚了"不自动补全配偶字段 |
| 不处理二进制文件 | 仅支持文本格式（JSON/CSV/YAML/Markdown/纯文本） |
| 不保证字段完整性 | 源数据缺失的字段输出 `[需核实:字段名]` 占位符 |
| 不做数据校验 | 不验证邮箱格式、电话号码真实性等业务规则 |

### 1.3 适用对象

- 需要从日志、邮件、聊天记录中提取结构化信息的开发者
- 需要统一多来源数据格式的数据分析人员
- 需要将非标准数据导入数据库或 API 的运维工程师


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
