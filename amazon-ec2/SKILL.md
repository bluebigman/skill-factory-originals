---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: amazon-ec2
name: amazon-ec2
displayName: EC2实例 运维管理 配置助手
description: 解析EC2需求，生成实例配置与运维操作指引。
version: 1.0.1
rules_version: cpr-20260808-n152
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/amazon-ec2
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: CloudCraft Studio
agent_created: true
trigger_words: ["amazon-ec2", "EC2", "实例配置", "AWS运维", "云服务器"]
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

# Amazon EC2 实例配置与运维助手

## 一、能力边界速查卡

本 Skill 专注于将用户提供的 EC2 相关需求描述、架构草图、成本限制或故障现象，转化为结构化的实例配置建议、运维操作步骤和成本估算清单。它不执行任何真实 AWS API 调用，仅提供基于最佳实践的决策支持。

| 能做 ✅ | 不能做 ❌ |
|---------|-----------|
| 解析实例类型选择需求（CPU/内存/网络场景） | 直接创建、启动或终止真实 EC2 实例 |
| 根据工作负载推荐实例家族（如 M、C、R、T 系列） | 修改 AWS 账户中的任何资源 |
| 生成安全组规则建议（端口、来源 IP） | 绕过或替代 AWS IAM 权限策略 |
| 估算月度成本（基于公开按需定价） | 提供实时价格或预留实例折扣价 |
| 诊断常见启动失败或连接问题（基于现象描述） | 访问用户 AWS 控制台或 CloudWatch 数据 |
| 输出 AMI 选择与存储卷配置建议 | 处理多账户或组织级资源结构 |

**适用对象**：正在准备 AWS 认证考试的开发者、需要快速搭建测试环境的工程师、负责成本优化的架构师、以及刚接触云服务器的运维新手。


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
