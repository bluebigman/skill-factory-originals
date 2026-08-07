---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: design-harness
name: design-harness
displayName: UI设计 前端原型 交互验证
description: 将设计稿或需求转化为可验证的前端原型，提供结构化输出与置信度提示。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/design-harness
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: CraftFlow Studio
agent_created: true
trigger_words: ["design harness", "UI设计", "前端原型", "交互验证", "设计稿转前端"]
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

# design-harness Skill 文档

## 一、能力边界（一页纸速查卡）

### 1.1 能做（核心能力清单）

| 编号 | 能力项 | 说明 | 输入示例 | 输出示例 |
|------|--------|------|----------|----------|
| C1 | 设计稿结构化解析 | 从图片/PDF/Figma链接中提取布局、组件、色彩、字体等关键信息 | `Figma链接`、`设计稿.png` | 结构化JSON描述 |
| C2 | 前端代码生成 | 将解析结果转化为HTML/CSS/JS原型代码 | 结构化JSON | `index.html` + `style.css` |
| C3 | 交互逻辑标注 | 识别按钮、跳转、表单等交互点并标注行为 | 设计稿 | 交互标注表 |
| C4 | 响应式适配建议 | 基于设计稿尺寸给出断点与适配方案 | 设计稿 + 目标设备 | 断点配置表 |
| C5 | 批量处理与格式定制 | 支持多文件批量转换，可指定输出格式（Vue/React/纯HTML） | 多张设计稿 | 多文件输出 |

### 1.2 不能做（明确边界）

| 编号 | 限制项 | 说明 |
|------|--------|------|
| L1 | 不执行真实部署 | 不负责将代码部署到服务器或生产环境 |
| L2 | 不处理动效细节 | 复杂交互动效（如3D变换、粒子效果）仅提供占位与建议 |
| L3 | 不保证像素级还原 | 输出为可用的原型代码，非生产级精度的像素还原 |
| L4 | 不读取受保护内容 | 需要登录权限的Figma/设计资源无法直接访问 |

### 1.3 适用对象

- **前端开发者**：快速将设计稿转为可交互原型
- **UI/UX设计师**：验证设计方案的可行性与交互逻辑
- **产品经理**：将需求文档转化为可视化原型用于评审


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
