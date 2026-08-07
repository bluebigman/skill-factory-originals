---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: capsize
name: capsize
displayName: EC2部署 运维自动化 发布管理
description: 管理并运行Amazon EC2上的应用部署，支持Capistrano扩展。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/capsize
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: DevForge Studio
agent_created: true
trigger_words: ["capsize", "EC2部署", "Capistrano扩展", "AWS运维", "远程部署"]
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

# capsize — EC2 部署与运维自动化 Skill

## 一、能力边界（一页纸速查卡）

### 1.1 能做什么

| # | 能力项 | 说明 | 输入示例 |
|---|--------|------|----------|
| 1 | 部署配置解析 | 将用户提供的部署配置、服务器清单、环境变量等转换为结构化部署方案 | `server: ec2-xx-xx-xx.compute.amazonaws.com, user: ubuntu` |
| 2 | 关键信息提取 | 从部署脚本、SSH 配置、环境描述中识别主机、路径、角色、密钥等关键参数 | `deploy_to: /var/www/app, roles: app, db` |
| 3 | 命令生成 | 根据 Capistrano 约定生成可执行的部署命令序列 | `cap production deploy` |
| 4 | 置信度标注 | 对推断出的配置项标注可信程度，不确定时明确提示 | `[需核实:ssh_port]` |
| 5 | 批量处理 | 支持多服务器、多环境（staging/production）的批量部署方案生成 | 多组服务器清单 + 环境变量 |

### 1.2 不能做什么

- 不能直接连接 AWS 或执行真实部署操作（仅生成方案与命令）
- 不能读取用户的 AWS 密钥或 SSH 私钥内容（仅接受路径引用）
- 不能替代 Capistrano 官方文档，不提供版本兼容性保证
- 不能自动发现服务器拓扑，需用户提供基础信息

### 1.3 适用对象

- 使用 Capistrano 管理 EC2 部署的运维工程师
- 需要将现有部署流程迁移到 EC2 的开发团队
- 希望规范化部署配置的 DevOps 初学者


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
