---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: comfyui-mcp
name: comfyui-mcp
displayName: 本地创意工坊 ComfyUI 节点控制台
description: 通过 MCP 协议在本地驱动 ComfyUI 完成图像、视频与音频生成任务。
version: 1.0.2
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/comfyui-mcp
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 林墨白
agent_created: true
trigger_words: ["comfyui-mcp", "图像生成", "视频生成", "音频生成", "ComfyUI 控制", "本地生成任务"]

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

# comfyui-mcp Skill 文档

## 一、能力边界（一页纸速查卡）

### 1.1 能做什么

| 能力项 | 说明 | 输入示例 | 输出示例 |
|--------|------|----------|----------|
| 图像生成 | 调用本地 ComfyUI 工作流，生成静态图像 | `comfyui mcp 图像生成 --prompt "赛博朋克城市夜景" --steps 30` | 返回图像文件路径与预览图 |
| 视频生成 | 驱动视频工作流，生成短视频片段 | `comfyui mcp 视频生成 --prompt "蝴蝶在花丛中飞舞" --frames 48` | 返回视频文件路径与元数据 |
| 音频生成 | 调用音频节点，生成音效或配乐 | `comfyui mcp 音频生成 --prompt "雨声与雷声混合" --duration 10` | 返回音频文件路径与波形摘要 |
| 工作流自检 | 检查当前 ComfyUI 服务是否可用 | `comfyui mcp --selftest` | 返回服务状态、节点数量、版本号 |
| 版本查询 | 查看 Skill 自身版本 | `comfyui mcp --version` | 返回 `1.0.0` |

### 1.2 不能做什么

- 不能直接修改 ComfyUI 的底层节点代码或自定义节点源码。
- 不能在没有本地 ComfyUI 服务运行的情况下完成生成任务。
- 不能保证生成结果的艺术质量或风格一致性（受模型权重与工作流配置影响）。
- 不能处理超出本地硬件资源（显存/内存）的生成请求。
- 不能替代 ComfyUI 官方 API 的全部功能（如节点热插拔、实时预览流）。

### 1.3 适用对象

- 已安装并运行 ComfyUI 的本地用户。
- 需要通过命令行或 MCP 协议批量触发生成任务的开发者。
- 希望在自动化脚本中集成图像/视频/音频生成能力的工程师。


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
