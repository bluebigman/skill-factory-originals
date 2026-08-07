---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: css-naked-day
name: css-naked-day
displayName: 样式裸奔日 页面脱衣 样式剥离
description: 在CSS裸奔日自动禁用全站样式，让网页回归纯HTML本色。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/css-naked-day
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 样式剥离工坊
agent_created: true
trigger_words: ["css naked day", "样式裸奔日", "禁用样式", "裸样式模式", "样式剥离"]

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

# CSS Naked Day — 样式剥离技能手册

## 一、能力边界（一页纸速查卡）

### 能做（5项核心能力）

| 编号 | 能力 | 说明 |
|------|------|------|
| 1 | 样式剥离 | 将用户提供的 HTML/CSS 文件或 URL 中的全部样式规则移除，输出纯 HTML 结构 |
| 2 | 关键信息保留 | 自动识别并保留 `<meta>`、`<title>`、`<link rel="icon">`、`<script>` 等非样式关键标签 |
| 3 | 结构化输出 | 按约定格式输出剥离后的 HTML 文件，附带剥离报告（JSON 格式） |
| 4 | 置信度标注 | 对剥离不完整或存在歧义的部分，输出 `[需核实:字段名]` 占位提示 |
| 5 | 批量处理 | 支持一次提交多个文件或 URL，按批次输出结果并汇总报告 |

### 不能做（明确边界）

- **不执行** JavaScript 动态注入的样式（如 JS 运行时修改 DOM 样式）
- **不处理** 内联 `style` 属性中的动态表达式（如 `style="width: calc(100% - 20px)"` 中的计算逻辑）
- **不还原** 原始 CSS 文件（只做剥离，不做备份或恢复）
- **不保证** 剥离后页面在所有浏览器中完全一致（不同浏览器对无样式 HTML 的默认渲染存在差异）

### 适用对象

- 参与 CSS Naked Day（每年4月9日）活动的网站开发者
- 需要快速检查页面语义结构完整性的前端工程师
- 需要生成无样式版本用于无障碍测试的 QA 人员
- 对网页"素颜"状态感兴趣的内容创作者


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
