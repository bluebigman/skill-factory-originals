---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: microsis
name: microsis
displayName: 旧档解析 字段还原 置信标注
description: 将老旧数据、文件或URL解析为结构化结果，保留关键信息并标注置信度。
version: 1.0.3
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/microsis
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 数据考古师
agent_created: true
trigger_words: ["microsis", "旧数据解析", "结构化提取", "字段还原", "老旧文件转换", "数据清洗", "历史档案数字化"]
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

# microsis — 旧档解析与结构化还原

## 一、能力边界（一页纸速查卡）

### 1.1 能做什么

| 能力项 | 说明 | 示例 |
|--------|------|------|
| 老旧文件解析 | 读取 `.txt`、`.csv`、`.log`、`.dat`、`.xml`、`.json` 等常见旧格式 | 解析 1998 年的销售记录 `.dat` 文件 |
| URL 内容抓取 | 从指定 URL 提取文本内容并结构化 | 抓取一个已停运网站的存档页面 |
| 字段自动识别 | 根据内容特征识别日期、金额、编号、人名等关键字段 | 从杂乱文本中提取出订单号、日期、金额 |
| 置信度标注 | 对每个提取字段标注可信程度（高/中/低） | 日期字段置信度 0.95，金额字段置信度 0.72 |
| 缺失标记 | 信息不足时输出 `[需核实:字段名]` 占位符 | 无法确认客户姓名时输出 `[需核实:客户姓名]` |

### 1.2 不能做什么

| 限制项 | 说明 |
|--------|------|
| 不执行二进制逆向 | 不解析加密、压缩或专有二进制格式（如 `.doc`、`.xls` 旧版 Office 文件） |
| 不进行语义推断 | 不猜测缺失字段的真实值，只标注需要核实 |
| 不修改原始文件 | 只输出结构化结果，不写回原文件 |
| 不处理超大文件 | 单文件建议不超过 50MB，超过则分段处理 |
| 不保证字段完整性 | 旧数据本身缺失的字段，无法凭空补全 |

### 1.3 适用对象

- 需要迁移历史数据到新系统的开发人员
- 需要从旧档案中提取信息的档案管理员
- 需要整理历史日志的运维工程师
- 需要从存档网页中恢复信息的研究人员


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
