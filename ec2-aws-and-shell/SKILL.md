---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: ec2-aws-and-shell
name: ec2-aws-and-shell
displayName: EC2运维 Shell脚本 云主机管理
description: 面向AWS EC2与Shell操作的规范化处理流程与输出模板。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/ec2-aws-and-shell
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: SkillForgeLab
agent_created: true
trigger_words: ["ec2-aws-and-shell", "EC2运维", "AWS云主机", "Shell脚本处理", "云服务器操作"]
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

# EC2 运维与 Shell 操作处理 Skill

## 一、能力边界速查卡

本 Skill 面向 **AWS EC2 实例管理与 Shell 命令处理** 场景，提供一套可复用的输入解析、命令生成、结果校验流程。

### 能做（核心能力）

| 编号 | 能力项 | 说明 |
|------|--------|------|
| 1 | 输入结构化 | 将用户提供的 EC2 实例 ID、区域、标签、Shell 脚本片段等原始信息解析为结构化参数表 |
| 2 | 关键信息识别 | 从描述中提取实例类型、安全组、密钥对、IAM 角色、存储卷等关键配置项 |
| 3 | 命令模板生成 | 基于参数表生成对应的 AWS CLI 或 Shell 命令序列，附带参数说明 |
| 4 | 输出规范化 | 按约定格式输出命令、预期结果、风险提示三要素 |
| 5 | 批量与自定义 | 支持多实例批量处理，允许用户指定输出字段和格式（JSON/表格/纯文本） |

### 不能做（明确边界）

- 不执行任何真实命令——仅生成命令文本与执行建议
- 不访问 AWS 真实环境——不读取、不修改任何云资源
- 不处理非 EC2/Shell 主题的请求（如数据库 SQL 优化、前端框架问题）
- 不保证命令在特定环境下的兼容性——需用户自行验证
- 不提供安全审计或合规性判定结论

### 适用对象

- 需要快速生成 EC2 操作命令的运维工程师
- 学习 AWS CLI 与 Shell 交互的初学者
- 需要规范化命令输出格式的团队协作场景


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
