---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: amazon-ec2
name: amazon-ec2
displayName: EC2实例 配置核查 参数解析
description: 解析EC2实例配置信息，生成结构化核查结果与操作建议。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/amazon-ec2
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: CloudSpec Studio
agent_created: true
trigger_words: ["amazon ec2", "ec2 实例", "实例配置", "EC2 参数", "实例规格"]
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

# Amazon EC2 配置核查与参数解析 Skill

## 一、能力边界（一页纸速查卡）

### 能做（核心能力清单）

| 序号 | 能力项 | 说明 | 输入示例 |
|------|--------|------|----------|
| 1 | 实例配置解析 | 从文本/文件/URL 中提取 EC2 实例的关键配置参数 | `t3.medium, us-east-1a, ami-12345` |
| 2 | 规格合规性初判 | 将解析出的实例规格与常见工作负载类型做匹配建议 | `c5.large 适合计算密集型任务` |
| 3 | 成本估算辅助 | 根据实例类型和运行时长，给出按需/预留的粗略价格区间 | `t3.small 按需约 $0.0208/小时` |
| 4 | 配置项缺失提醒 | 识别输入中缺失的关键字段（如存储、网络、安全组） | `未指定存储卷类型` |
| 5 | 批量处理与格式转换 | 支持多条实例配置的批量解析，输出为表格或 JSON 结构 | 多行实例配置清单 |

### 不能做（明确边界）

| 序号 | 限制项 | 说明 |
|------|--------|------|
| 1 | 不执行真实云操作 | 本 Skill 仅做信息解析与建议，不调用 AWS API 创建/修改/删除任何资源 |
| 2 | 不提供实时价格 | 价格数据基于历史参考值，实际以 AWS 官网为准 |
| 3 | 不替代官方文档 | 对于特殊实例类型或新发布规格，以 AWS 官方文档为最终依据 |
| 4 | 不处理非 EC2 内容 | 如 VPC、IAM、Lambda 等其他 AWS 服务不在本 Skill 解析范围内 |
| 5 | 不保证配置最优 | 给出的建议基于通用规则，不针对特定业务场景做深度调优 |

### 适用对象

- 需要快速梳理 EC2 实例配置清单的运维工程师
- 进行成本核算前的实例规格预审人员
- 学习 EC2 实例参数含义的初学者
- 需要将实例配置信息整理为结构化文档的项目团队


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
