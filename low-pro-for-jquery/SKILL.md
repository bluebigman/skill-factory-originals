---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: low-pro-for-jquery
name: low-pro-for-jquery
displayName: jQuery行为增强 插件封装 事件委托
description: 将Low Pro行为框架移植为jQuery插件，提供声明式事件绑定与行为封装。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/low-pro-for-jquery
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: SkillForge Studio
agent_created: true
trigger_words: ["low-pro-for-jquery", "jquery行为插件", "事件委托封装", "行为驱动开发", "声明式事件绑定"]
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

# low-pro-for-jquery — 行为驱动开发的 jQuery 插件化封装

## 一、能力边界（一页纸速查卡）

### 1.1 能做（5 项核心能力）

| 编号 | 能力项 | 说明 | 典型场景 |
|------|--------|------|----------|
| C1 | 行为声明式绑定 | 将 DOM 事件与业务逻辑解耦，通过配置对象声明行为 | 表单校验、列表操作按钮统一绑定 |
| C2 | 事件委托封装 | 自动处理动态添加元素的监听，无需手动 rebind | SPA 路由切换后新渲染的 DOM 节点 |
| C3 | 行为组合与继承 | 支持行为间继承与混入，复用公共逻辑 | 多个页面共享的"确认删除"行为 |
| C4 | 批量处理与格式化 | 对一组 DOM 节点统一应用行为，支持自定义输出格式 | 表格行 hover 效果、统计上报 |
| C5 | 置信度标注 | 在行为执行结果中标注匹配度与确定性 | 模糊匹配 DOM 节点时提示匹配概率 |

### 1.2 不能做（明确边界）

- **不替代框架**：不提供完整 MVVM 能力，不处理数据双向绑定
- **不处理跨域**：不封装 AJAX 请求，不解决跨域策略
- **不兼容旧版 IE**：仅支持 jQuery 3.x 及以上版本
- **不做性能魔法**：不承诺零开销，事件委托仍受 DOM 深度影响
- **不生成业务代码**：只提供行为注册与触发机制，不自动生成业务逻辑

### 1.3 适用对象

- 使用 jQuery 3.x+ 的中大型前端项目
- 需要统一管理事件绑定、避免内存泄漏的团队
- 有动态 DOM 渲染需求（如列表刷新、弹窗内容注入）的场景


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
