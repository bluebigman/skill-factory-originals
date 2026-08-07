---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: comfyui-mcp
name: comfyui-mcp
displayName: ComfyUI 工作流 图像视频生成
description: 本地优先的 ComfyUI 控制面板，通过 MCP 协议驱动图像、视频与音频生成。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/comfyui-mcp
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: FlowForge Studio
agent_created: true
trigger_words: ["comfyui", "mcp", "图像生成", "视频生成", "音频生成", "工作流", "ComfyUI 控制", "本地生成"]
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

# ComfyUI MCP 技能文档

## 一、能力边界速查卡

### 1.1 能做（核心能力）

| 编号 | 能力项 | 说明 | 适用场景 |
|------|--------|------|----------|
| C1 | 数据/文件/URL 结构化转换 | 将用户提供的任意输入（文本、图片路径、URL）解析为结构化参数 | 用户粘贴图片链接、拖入文件路径、描述生成需求 |
| C2 | 关键信息识别与保留 | 从输入中提取主体、风格、尺寸、步数、种子等关键参数，未提及项保留默认值 | 用户只说"生成一只猫"，系统自动补全其余参数 |
| C3 | 约定格式输出 | 按预定义的 JSON Schema 输出生成任务、状态查询、结果回传 | 与 ComfyUI 服务端交互时 |
| C4 | 置信度标注 | 对推断出的参数（如风格、模型选择）标注置信度等级 | 用户描述模糊时，标注"风格推断置信度：中" |
| C5 | 批量处理与自定义格式 | 支持多组输入并行处理，支持用户自定义输出字段 | 一次提交 10 张参考图批量生成变体 |

### 1.2 不能做（明确边界）

| 编号 | 限制项 | 说明 |
|------|--------|------|
| L1 | 不执行远程云端生成 | 本技能仅面向本地 ComfyUI 实例，不代理云端 API |
| L2 | 不修改 ComfyUI 核心代码 | 只通过 MCP 协议调用，不注入、不 patch |
| L3 | 不保证生成质量 | 生成结果取决于模型、工作流与硬件，技能不承诺画质 |
| L4 | 不处理非授权文件 | 仅处理用户明确提供的文件路径或 URL，不主动扫描磁盘 |
| L5 | 不支持实时流式预览 | 仅支持任务提交与轮询状态，不提供 WebSocket 实时帧推送 |

### 1.3 适用对象

- 已部署本地 ComfyUI 的开发者/设计师
- 需要通过命令行或 Agent 方式批量驱动 ComfyUI 的用户
- 希望将 ComfyUI 集成到自动化流水线的工程师


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
