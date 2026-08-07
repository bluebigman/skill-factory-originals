---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: ec2-aws-and-shell
name: ec2-aws-and-shell
displayName: EC2运维 Shell脚本 云主机操作
description: 面向AWS EC2与Shell操作的规范化处理流程与输出模板。
version: 1.0.2
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/ec2-aws-and-shell
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: CloudOps Architect
agent_created: true
trigger_words: ["ec2-aws-and-shell", "EC2运维", "AWS云主机", "Shell脚本处理", "云服务器操作", "AWS实例管理", "命令行运维"]

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

# EC2 运维与 Shell 脚本处理 Skill

## 一、能力边界（一页纸速查卡）

### 1.1 能做与不能做

| 维度 | 能做 ✅ | 不能做 ❌ |
|------|--------|----------|
| EC2 实例 | 实例状态查询（运行/停止/终止）、标签信息解析、安全组规则梳理、弹性 IP 关联关系分析 | 直接调用 AWS API 执行变更操作（需用户自行执行命令） |
| Shell 脚本 | 脚本逻辑审查、参数解析建议、错误处理模式推荐、脚本模板生成 | 在用户机器上实际执行脚本（仅提供文本输出） |
| 运维流程 | 故障排查步骤梳理、巡检清单生成、操作手册结构化输出 | 代替人工决策（如是否终止实例） |
| 数据处理 | 将用户提供的命令输出（如 `aws ec2 describe-instances` 的 JSON）解析为易读表格 | 访问用户未提供的任何云资源数据 |

### 1.2 适用对象

- **目标用户**：AWS 云运维工程师、DevOps 人员、系统管理员、SRE 团队成员。
- **适用场景**：日常 EC2 巡检、Shell 脚本编写与调试、运维操作文档整理、故障排查辅助。
- **不适用场景**：需要真实云环境交互的自动化操作、涉及生产环境的直接变更执行。


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
