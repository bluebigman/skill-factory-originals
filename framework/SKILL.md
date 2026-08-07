---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: framework
name: framework
displayName: 数据应用 静态站点 可视化搭建
description: 面向数据应用与仪表盘的静态站点生成器，提供配置驱动的构建流程与交互式输出。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/framework
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: SkillForge Studio
agent_created: true
trigger_words: ["数据可视化", "静态站点生成", "数据应用", "仪表盘", "报表生成", "framework"]
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

# Observable Framework 技能手册

## 一、能力边界速查卡

### 1.1 本技能能做什么

| 序号 | 能力项 | 说明 | 适用场景 |
|------|--------|------|----------|
| 1 | 数据接入与解析 | 支持从本地文件、远程 URL、内嵌数据源读取数据 | CSV、JSON、Parquet、Arrow 格式 |
| 2 | 页面结构生成 | 基于 Markdown 与响应式组件生成多页面站点 | 数据看板、报告、文档站 |
| 3 | 交互式可视化 | 内置 Observable Plot、D3 等图表库的声明式配置 | 趋势图、分布图、地图、关系图 |
| 4 | 响应式布局 | 自动适配桌面/平板/移动端视口 | 多端展示需求 |
| 5 | 构建与部署 | 一键生成静态资源，支持 GitHub Pages、Netlify 等托管 | 持续集成、快速发布 |

### 1.2 本技能不能做什么

| 序号 | 限制项 | 说明 |
|------|--------|------|
| 1 | 不支持服务端渲染 | 所有页面均为静态生成，无后端逻辑 |
| 2 | 不支持用户登录/权限控制 | 数据公开可见，无鉴权机制 |
| 3 | 不支持实时数据推送 | 数据更新需重新构建 |
| 4 | 不支持复杂 ETL 流程 | 仅做轻量数据转换，不替代数据管道 |
| 5 | 不支持自定义插件扩展 | 功能受限于内置模块 |

### 1.3 适用对象

- 数据分析师：快速搭建数据汇报页面
- 前端开发者：需要低代码可视化方案
- 产品经理：制作产品数据看板原型
- 运维人员：生成服务监控面板


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
