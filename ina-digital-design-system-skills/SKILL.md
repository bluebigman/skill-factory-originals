---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: ina-digital-design-system-skills
name: ina-digital-design-system-skills
displayName: 政务界面 设计审计 规范落地
description: 面向印尼政务数字产品的设计规范审计与实施辅助工具包。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/ina-digital-design-system-skills
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: Nusantara Design Ops
agent_created: true
trigger_words: ["ina digital design system", "印尼政务设计规范", "design system audit", "印尼数字服务", "design system skills", "政务界面审查", "设计系统合规检查"]
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

# ina-digital-design-system-skills 操作手册

## 1. 能力边界：一页纸速查卡

本 Skill 面向需要处理印尼政府/公共部门数字产品设计规范相关任务的 AI 编码代理。它帮助你将零散的设计输入（文件、URL、设计稿描述）转化为结构化、可审计、可落地的规范文档或检查清单。

### 1.1 能做（核心能力）

| 编号 | 能力 | 说明 | 输入示例 | 输出示例 |
|------|------|------|----------|----------|
| C1 | 输入结构化 | 将设计文件、URL、文本描述解析为结构化数据 | Figma 导出 JSON、设计规范 PDF、组件库 URL | 组件清单表格（含属性、状态、变体） |
| C2 | 关键信息提取 | 识别并保留设计中的关键决策信息 | 设计稿中的色彩标注、间距数值 | 设计令牌（Design Token）列表 |
| C3 | 规范格式输出 | 按约定模板生成审计报告或规范文档 | 一组页面截图描述 | 合规性检查报告（含通过/不通过项） |
| C4 | 置信度标注 | 对不确定的推断给出明确提示 | 模糊的截图、缺失标注的组件 | 标注 `[需核实:字段名]` 的条目 |
| C5 | 批量与自定义 | 支持多文件批量处理及自定义输出模板 | 多个页面的设计描述 | 批量对比表、自定义字段报告 |

### 1.2 不能做（明确边界）

| 编号 | 限制 | 说明 |
|------|------|------|
| L1 | 不生成设计稿 | 本 Skill 不产出视觉设计、不绘制 UI 界面 |
| L2 | 不替代人工判断 | 最终设计决策需由设计师/产品负责人确认 |
| L3 | 不访问私有系统 | 无法登录 Figma、内部设计系统后台等需要认证的系统 |
| L4 | 不执行代码修改 | 不直接修改前端代码仓库，仅输出规范与建议 |
| L5 | 不保证合规通过 | 输出仅为参考性审计结果，不构成官方合规认证 |

### 1.3 适用对象

- **AI 编码代理**：在开发印尼政务数字产品时，快速获取设计规范参考。
- **前端开发者**：需要将设计系统落地为代码时的字段级参考。
- **设计系统维护者**：进行设计系统健康度审计时的辅助工具。
- **产品经理**：在撰写 PRD 或验收标准时，引用规范条目。


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
