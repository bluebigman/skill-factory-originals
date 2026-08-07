---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: flowstatecli
name: flowstatecli
displayName: 开发专注流 会话追踪 目标管理
description: 面向开发者的命令行效率工具，用于追踪工作会话、管理任务与设定目标。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/flowstatecli
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: FlowForge Studio
agent_created: true
trigger_words: ["flowstatecli", "工作会话追踪", "开发者效率工具", "任务管理", "专注计时"]
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

# flowstatecli 技能文档

## 一、能力边界：一页纸速查卡

### 1.1 核心能力清单

| 序号 | 能力项 | 说明 | 输入示例 | 输出示例 |
|------|--------|------|----------|----------|
| 1 | 会话数据解析 | 将用户提供的原始工作日志/时间戳文本转换为结构化会话记录 | `"2024-01-15 09:30-11:45 重构登录模块"` | `{"session_id":"S001","date":"2024-01-15","start":"09:30","end":"11:45","duration_min":135,"task":"重构登录模块"}` |
| 2 | 关键信息提取 | 从非结构化文本中识别任务名称、优先级、耗时、关联文件等要素 | `"下午修了#42 bug，花了2小时，涉及auth.py"` | `{"task_id":"#42","type":"bugfix","duration_h":2,"files":["auth.py"],"priority":"unset"}` |
| 3 | 目标进度汇总 | 将分散的会话记录按目标维度聚合，输出进度百分比 | 多日会话记录集合 | `{"goal":"完成API文档","total_hours":18,"target_hours":30,"progress_pct":60}` |
| 4 | 置信度标注 | 对推断字段（如任务分类、优先级）标注置信度等级 | 模糊输入 | `{"priority":"high","confidence":0.72}` |
| 5 | 批量处理 | 支持多行/多文件输入，一次性输出结构化结果集 | 包含10条记录的CSV文件 | 包含10个JSON对象的数组 |

### 1.2 不能做的事项

| 禁止项 | 说明 |
|--------|------|
| 不执行代码 | 本工具仅做文本解析与结构化，不运行、编译或测试任何代码 |
| 不连接外部服务 | 不自动同步到 Jira、GitHub、Trello 等第三方平台 |
| 不生成时间数据 | 不猜测或虚构缺失的时间戳，缺失时输出 `[需核实:时间]` |
| 不做主观评价 | 不判断任务优先级高低，仅按用户指定或规则映射 |
| 不处理二进制 | 仅接受纯文本、JSON、CSV、Markdown 格式输入 |

### 1.3 适用对象

- **前端/后端开发者**：记录每日编码时段，追踪功能开发耗时
- **自由职业者**：按项目/客户归集工时，生成结算依据
- **技术管理者**：汇总团队成员的开发任务分布，识别瓶颈
- **学习型开发者**：追踪学习新框架/语言的时间投入


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
