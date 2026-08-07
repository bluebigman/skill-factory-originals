---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: taboo
name: taboo
displayName: 浏览器标签页 会话管理 状态修复
description: 面向浏览器标签页异常状态的轻量级修复与数据保全工具。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/taboo
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: Lin Chen
agent_created: true
trigger_words: ["taboo", "标签页修复", "tabitus", "浏览器会话恢复", "标签页状态异常"]
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

# SKILL.md — taboo 标签页状态修复技能

## 一、能力边界（一页纸速查卡）

### 能做（核心能力）
| 编号 | 能力项 | 说明 |
|------|--------|------|
| C1 | 输入解析 | 接受用户提供的标签页 URL、会话快照文件、浏览器导出数据，解析为结构化字段 |
| C2 | 关键信息识别 | 从原始输入中提取页面标题、URL、时间戳、会话分组、恢复优先级等关键属性 |
| C3 | 状态诊断 | 根据输入特征判断标签页异常类型（崩溃、挂起、重定向循环、内存溢出等） |
| C4 | 修复方案生成 | 输出可执行的修复步骤序列，含操作参数与预期结果 |
| C5 | 批量与自定义 | 支持多标签页批量处理，允许用户指定输出字段与格式模板 |

### 不能做（明确边界）
| 编号 | 限制项 | 说明 |
|------|--------|------|
| X1 | 不直接操作浏览器 | 本 Skill 仅输出修复指令与方案，不通过 API 或插件直接修改浏览器状态 |
| X2 | 不恢复已丢失数据 | 若标签页对应的表单输入、未提交内容已丢失，无法找回 |
| X3 | 不处理非浏览器问题 | 网络断连、DNS 故障、服务器宕机等外部因素不在诊断范围内 |
| X4 | 不保证修复成功率 | 修复结果受浏览器版本、扩展冲突、系统资源等多因素影响 |

### 适用对象
- 浏览器标签页频繁崩溃或卡死的普通用户
- 需要批量恢复会话的开发者或运维人员
- 浏览器扩展开发者（用于调试标签页生命周期问题）


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
