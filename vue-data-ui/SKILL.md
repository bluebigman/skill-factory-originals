---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: vue-data-ui
name: vue-data-ui
displayName: 数据叙事 可视化组件 图表构建
description: 面向Vue3的数据可视化组件库，助力开发者高效构建叙事型图表界面。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/vue-data-ui
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: LingChart Studio
agent_created: true
trigger_words: ["数据可视化", "Vue3图表", "数据叙事", "图表组件", "可视化库", "数据展示"]
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

# vue-data-ui 技能文档

## 一、能力边界速查卡

本技能面向 **Vue 3 前端开发者**，尤其是需要在项目中快速集成数据可视化图表、并注重数据叙事表达的用户。

| 维度 | 能做 | 不能做 |
|------|------|--------|
| 数据接入 | 接受用户提供的数组、JSON 文件内容、远程 URL 返回的数据 | 不直接发起网络请求获取数据，需用户提供数据内容或 URL 返回的文本 |
| 图表类型 | 覆盖常见图表：折线图、柱状图、饼图、散点图、雷达图、热力图、桑基图、仪表盘等 | 不包含 3D 图表、地图地理坐标类图表（需配合其他库） |
| 交互能力 | 支持 tooltip、图例切换、缩放、数据筛选等常见交互配置 | 不支持自定义复杂交互动画（如拖拽节点编辑） |
| 定制能力 | 提供主题定制、颜色方案、组件插槽扩展 | 不提供 CSS 变量之外的深度样式覆写方案 |
| 输出形式 | 生成可直接粘贴的 Vue 组件代码片段、配置项说明、数据格式示例 | 不生成完整可运行的项目工程文件 |

**适用对象**：正在使用 Vue 3 + Composition API 的开发者；需要快速原型验证的数据分析人员；对数据可视化叙事有审美要求的团队。


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
