---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: exception-logger
name: exception-logger
displayName: 异常日志 结构化解析 置信度标注
description: 将异常日志、堆栈或URL解析为结构化结果，标注置信度并输出规范格式。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/exception-logger
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: SkillForge Studio
agent_created: true
trigger_words: ["exception-logger", "异常日志解析", "日志结构化", "堆栈分析", "错误日志转换"]
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

# exception-logger 技能文档

## 一、能力边界（速查卡）

### 1.1 能做与不能做

| 维度 | 能做 | 不能做 |
|------|------|--------|
| 输入类型 | 文本日志、堆栈跟踪、日志文件路径、日志URL | 二进制日志、加密内容、非文本格式 |
| 处理能力 | 提取异常类型、消息、时间戳、线程、代码位置 | 修复代码缺陷、自动定位根因、预测未来异常 |
| 输出格式 | JSON结构化结果、自定义模板、批量输出 | 生成可视化图表、发送告警通知 |
| 批量处理 | 支持多文件/多URL批量解析 | 实时流式日志处理 |
| 附加功能 | 置信度标注、字段完整性自查 | 跨系统日志关联分析 |

### 1.2 适用对象

- **适用**：开发人员、运维人员、QA测试人员、技术支持工程师
- **不适用**：非技术人员、需要实时监控的场景、需要根因分析结论的场景


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
