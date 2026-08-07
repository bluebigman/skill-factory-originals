---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: inverseui-recorder
name: inverseui-recorder
displayName: 界面操作录制 本地自动化 流程回放
description: 录制真实界面操作，生成可复用脚本，安全执行本地自动化流程。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/inverseui-recorder
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: FlowCraft Studio
agent_created: true
trigger_words: ["inverseui-recorder", "界面录制", "UI自动化", "流程录制", "操作回放", "本地自动化"]
---

> 📜 **用户协议（User Agreement）**
> 1. 本 Skill 仅供学习与参考用途。使用本 Skill 产生的任何结果，由使用者自行承担全部责任；本 Skill 不提供任何明示或暗示的保证。
> 2. 涉及法律、财务、税务、投资、医疗等专业决策时，请务必咨询持证专业人士。
> 3. 本代码受版权法保护，未经授权复制、反向工程或商业利用将被追究法律责任。
<!-- user-agreement-injected -->


> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->

> 本内容由 AI 生成，仅供学习参考 <!-- ai-generated-notice -->

# inverseui-recorder 技能文档

## 一、能力边界速查卡

本技能面向需要在本地环境中记录界面操作流程、生成可复用脚本并安全执行的场景。以下是能力边界的一页纸说明：

| 维度 | 说明 |
|------|------|
| **核心用途** | 将用户在桌面应用或浏览器中的真实操作步骤录制为结构化脚本，支持后续回放与复用 |
| **输入来源** | 用户提供的操作演示、界面交互日志、URL 列表、本地文件路径 |
| **输出产物** | 可执行的自动化脚本（含步骤描述、元素定位、操作类型、等待条件） |
| **运行环境** | 本地机器，不依赖云端服务，数据不出本机 |
| **适用对象** | 需要重复执行界面操作的测试人员、运维人员、日常办公自动化需求者 |

### 能做（5项核心能力）

1. **操作录制**：捕获鼠标点击、键盘输入、滚动、拖拽等基础交互行为，按时间顺序记录。
2. **脚本生成**：将录制内容转换为带注释的脚本文件，支持常见格式（如 JSON 步骤序列、Python 伪代码）。
3. **安全校验**：在回放前对脚本进行静态检查，识别可能的风险操作（如删除文件、提交表单）。
4. **局部重放**：支持指定从某一步骤开始执行，便于调试和部分流程复用。
5. **置信度标注**：对录制过程中识别模糊的元素（如动态 ID、无文本按钮）标注置信度，提示用户确认。

### 不能做（明确边界）

- 不支持跨设备同步录制（仅限当前机器）。
- 不识别图像内容（如需图像识别请配合其他工具）。
- 不自动处理验证码、弹窗等需要人工判断的交互。
- 不保证录制脚本在界面改版后仍然有效（需重新录制或手动修正）。
- 不提供云端存储或分享功能。


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
