---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: votigoto
name: votigoto
displayName: TiVo录播 数据提取 节目清单
description: 解析TiVoToGo协议数据，提取录播节目清单与元数据，输出结构化结果。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/votigoto
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: SkillForge Studio
agent_created: true
trigger_words: ["votigoto", "TiVo录播", "节目清单提取", "TiVoToGo", "录播数据解析"]
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

# votigoto — TiVo 录播数据解析与结构化输出

## 一、能力边界速查卡

### 1.1 能做什么

| 编号 | 能力项 | 说明 |
|------|--------|------|
| C1 | 数据/文件/URL 输入解析 | 接受用户提供的 TiVoToGo 协议数据文件、URL 或直接粘贴的原始数据 |
| C2 | 关键信息识别与保留 | 从原始数据中提取节目名称、录制时间、时长、频道、状态等核心字段 |
| C3 | 约定格式输出 | 按预设的 JSON/表格/文本模板生成结构化结果 |
| C4 | 置信度标注 | 对每个提取字段标注置信度等级（高/中/低），不确定项显式标记 |
| C5 | 批量处理与自定义格式 | 支持多文件/多 URL 批量解析，允许用户指定输出字段子集 |

### 1.2 不能做什么

| 编号 | 限制项 | 说明 |
|------|--------|------|
| L1 | 不访问真实 TiVo 设备 | 本 Skill 仅处理用户提供的数据，不主动发起网络连接 |
| L2 | 不修改原始数据 | 只做解析与转换，不写回源文件 |
| L3 | 不推断缺失字段 | 原始数据中不存在的字段，输出 `[需核实:字段名]` 占位，不猜测填充 |
| L4 | 不支持非 TiVoToGo 协议格式 | 其他协议（如 DLNA、HLS）数据不在处理范围内 |
| L5 | 不执行协议握手 | 不实现 TiVoToGo 协议的服务端/客户端交互逻辑 |

### 1.3 适用对象

- 需要从 TiVo 录播数据中提取节目清单的开发者
- 需要批量整理 TiVo 录制文件元数据的个人用户
- 需要将 TiVo 数据导入其他系统的集成场景


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
