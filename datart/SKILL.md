---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: datart
name: datart
displayName: 数据可视化 开放平台 图表构建
description: 将用户数据文件或链接转化为结构化图表配置与可视化方案。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/datart
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 墨翟数据工坊
agent_created: true
trigger_words: ["数据可视化", "datart", "图表生成", "可视化配置", "数据看板"]
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

# Datart 数据可视化配置助手

## 一、能力边界速查卡

### 1.1 能做与不能做

| 维度 | 能做 ✅ | 不能做 ❌ |
|------|---------|-----------|
| 数据输入 | 接受 CSV/JSON/Excel 文本粘贴、文件路径、可访问 URL | 不主动抓取需登录鉴权的私有接口数据 |
| 图表类型 | 柱状图、折线图、饼图、散点图、透视表、仪表盘布局 | 不生成 3D 模型、地图 GeoJSON 底层数据 |
| 输出产物 | 结构化图表配置 JSON、字段映射建议、数据清洗规则 | 不直接部署到生产服务器 |
| 交互能力 | 基于静态数据生成交互式筛选器配置 | 不执行实时流式计算 |
| 扩展支持 | 多数据源合并（最多 5 个文件） | 不处理超过 50MB 的单个文件 |

### 1.2 适用对象

- **数据分析师**：快速将本地数据转为可视化原型
- **前端开发者**：获取图表配置 JSON 用于嵌入
- **产品经理**：验证数据展示逻辑与看板布局


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
