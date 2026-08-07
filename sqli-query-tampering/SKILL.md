---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: sqli-query-tampering
name: sqli-query-tampering
displayName: SQL注入 查询篡改 载荷生成
description: 为Burp Suite Intruder生成定制SQL注入载荷，辅助安全测试中的查询篡改分析。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/sqli-query-tampering
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: QueryForge Studio
agent_created: true
trigger_words: ["SQL查询", "SQLi", "注入载荷", "查询篡改", "Intruder载荷", "SQL注入测试"]

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

# SQLi 查询篡改载荷生成器 — 使用指南

## 1. 能力边界（速查卡）

### 1.1 本 Skill 能做什么

| 序号 | 能力项 | 说明 |
|------|--------|------|
| 1 | 载荷生成 | 根据用户提供的 SQL 查询模板，生成多种变体的注入载荷 |
| 2 | 输入解析 | 从用户粘贴的文本、上传的文件或指定的 URL 中提取 SQL 查询片段 |
| 3 | 关键信息识别 | 自动识别查询中的表名、字段名、WHERE 子句、ORDER BY 位置等关键锚点 |
| 4 | 格式转换 | 将载荷输出为 Burp Intruder 可直接粘贴的列表格式（每行一个）或 JSON 数组 |
| 5 | 批量处理 | 支持一次处理多条查询模板，批量生成对应载荷集 |
| 6 | 置信度标注 | 对识别不确定的字段或结构，输出 `[需核实:字段名]` 占位符 |

### 1.2 本 Skill 不能做什么

| 序号 | 限制项 | 说明 |
|------|--------|------|
| 1 | 不执行攻击 | 本 Skill 仅生成文本载荷，不发起网络请求，不连接任何目标系统 |
| 2 | 不检测漏洞 | 不判断目标是否存在 SQL 注入漏洞，仅提供测试用输入变体 |
| 3 | 不绕过 WAF | 不提供针对特定 WAF 产品的绕过方案，仅做通用语法变体 |
| 4 | 不保证有效性 | 载荷是否生效取决于目标数据库类型、代码实现和防护措施，本 Skill 不做任何有效性承诺 |
| 5 | 不处理二进制 | 不支持二进制文件输入，仅处理 UTF-8 文本 |

### 1.3 适用对象

- 已获得合法授权的渗透测试人员
- 在本地或测试环境中进行安全研究的开发人员
- 需要批量生成 Intruder 测试向量的 QA 工程师


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
