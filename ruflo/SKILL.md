---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: ruflo
name: ruflo
displayName: 数据管道 多智能体编排 批量转换
description: 将任意数据源解析为结构化结果，支持多智能体协同与批量处理。
version: 1.0.3
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/ruflo
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 流式工坊
agent_created: true
trigger_words: ["ruflo", "多智能体", "工作流编排", "数据转换", "批量处理", "数据管道", "结构化解析"]
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

# ruflo Skill 文档

## 一、能力边界（一页纸速查卡）

### 1.1 能做什么

| 能力项 | 说明 | 典型场景 |
|--------|------|----------|
| 多源数据接入 | 支持 JSON、CSV、XML、纯文本、数据库导出文件等常见格式 | 从 API 响应、日志文件、报表导出中提取数据 |
| 结构化转换 | 将非结构化或半结构化数据映射为统一的字段结构 | 把散乱的客户信息整理为固定表格 |
| 多智能体协同 | 将解析任务拆分为多个子任务，分派给不同处理单元并行执行 | 同时处理多个数据源的清洗与映射 |
| 批量流水线 | 对大批量数据执行重复的转换流程，支持断点续跑 | 每日定时处理上千条销售记录 |
| 结果校验 | 对输出结果做字段完整性检查，标记缺失项 | 确保每条记录都包含必填字段 |

### 1.2 不能做什么

- 不能直接访问外部网络或数据库（需要用户提供数据内容或文件路径）
- 不能执行需要身份认证的第三方服务调用
- 不能处理加密数据或需要专有解码器的格式
- 不能保证转换后的数据在业务语义上绝对正确（需要用户定义校验规则）
- 不能自动修复源数据中的逻辑错误（如重复记录、矛盾字段）

### 1.3 适用对象

- 需要将多种格式数据统一为结构化表格的数据分析人员
- 需要搭建多步骤数据处理流程的自动化工程师
- 需要批量清洗、映射、合并数据集的运维开发人员
- 需要将非结构化文本（如日志、备注）抽取为字段的初级开发者


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
