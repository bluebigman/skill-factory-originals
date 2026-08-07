---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: automatewithpython
name: automatewithpython
displayName: 办公自动化 Python 脚本生成器
description: 将重复性办公任务转化为可执行的 Python 自动化脚本。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/automatewithpython
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: FlowForge Studio
agent_created: true
trigger_words: ["automatewithpython", "python自动化", "办公自动化", "脚本生成", "批量处理", "excel自动化"]
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

# SKILL.md — automatewithpython

## 一、能力边界速查卡（一页纸）

| 维度 | 说明 |
|------|------|
| **核心用途** | 将用户描述的重复性办公任务（文件重命名、Excel 单元格批量更新、数据整理等）转化为可直接运行的 Python 脚本 |
| **输入来源** | 用户提供的：① 任务描述文本 ② 示例数据文件（CSV/Excel/TXT） ③ 文件所在 URL |
| **输出产物** | ① 完整的 Python 脚本（含依赖声明） ② 运行说明（含预期效果示例） ③ 注意事项清单 |
| **支持场景** | 文件批量重命名、Excel 读写与公式更新、CSV 数据清洗、日志文件分析、文件夹结构整理、简单网页数据抓取 |
| **不支持场景** | 涉及 GUI 自动化（如模拟鼠标点击）、需要特定商业软件 API 的操作、大规模并行计算、需要用户交互的复杂流程编排 |
| **适用对象** | 有基础 Python 环境但不想手写重复代码的办公人员；需要快速原型验证的初级开发者；对脚本安全性有自查需求的用户 |

**关键边界值：**
- 输入文件大小建议 ≤ 50MB（超过需分块处理提示）
- 生成的脚本兼容 Python 3.8+，不依赖第三方库超过 3 个
- 每次调用生成 1 个脚本，如需多个脚本请分次描述


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
