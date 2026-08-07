---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: anthropic-cybersecurity-skills
name: anthropic-cybersecurity-skills
displayName: 安全分析 威胁建模 框架映射
description: 将安全数据映射至六大权威框架，输出结构化分析结果。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/anthropic-cybersecurity-skills
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: SkillForge Studio
agent_created: true
trigger_words: ["cybersecurity","威胁建模","安全框架映射","MITRE ATT&CK","NIST CSF","安全分析","威胁情报"]
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

# 安全分析 威胁建模 框架映射 Skill

## 一、能力边界：一页纸速查卡

本 Skill 面向安全分析师、威胁情报人员、蓝队/红队成员及安全自动化工程师，用于将原始安全数据（日志、报告、URL、文件）转换为结构化、可追溯的框架映射结果。

### 能做（核心能力）

| 编号 | 能力项 | 说明 | 输入示例 |
|------|--------|------|----------|
| C1 | 数据解析与结构化 | 从文本/日志/URL/文件中提取实体、行为、指标 | 原始告警日志、威胁报告段落 |
| C2 | 多框架映射 | 将提取结果映射至 MITRE ATT&CK、NIST CSF 2.0、MITRE ATLAS、D3F 等六大框架 | 攻击技术描述 → ATT&CK 技术编号 |
| C3 | 置信度标注 | 对每条映射结果给出高/中/低置信度判断 | 明确技术名称 → 高置信度 |
| C4 | 批量处理 | 支持多条目输入，批量输出结构化结果 | 包含 50 条 IOC 的 CSV 文件 |
| C5 | 自定义格式输出 | 按用户指定的字段结构生成 JSON/CSV/Markdown 表格 | 指定输出字段：技术ID、映射框架、置信度 |

### 不能做（明确边界）

| 编号 | 限制项 | 说明 |
|------|--------|------|
| L1 | 不执行实时扫描 | 本 Skill 不连接外部扫描器或 SIEM，仅处理用户提供的数据 |
| L2 | 不提供修复建议 | 仅做映射与分析，不生成漏洞修复步骤或补丁方案 |
| L3 | 不保证覆盖全部框架条目 | 映射结果受限于输入信息的完整度，缺失字段会以占位符标注 |
| L4 | 不替代专业判断 | 输出为辅助参考，最终决策需由安全专业人员复核 |

### 适用对象

- 需要快速将威胁情报对齐到行业标准框架的分析师
- 需要批量处理安全事件报告并生成标准化输出的自动化流程
- 需要为安全报告补充框架引用依据的文档编写人员


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
