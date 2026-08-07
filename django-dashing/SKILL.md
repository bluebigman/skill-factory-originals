---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: django-dashing
name: django-dashing
displayName: 数据看板 可视化 仪表盘构建
description: 将用户数据快速转化为可交互的Django仪表盘应用。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/django-dashing
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: SkillForge Studio
agent_created: true
trigger_words: ["django-dashing", "数据可视化", "仪表盘", "dashboard", "看板开发", "Django图表"]
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

# django-dashing 技能文档

## 一、能力边界与适用对象（速查卡）

### 1.1 核心能力清单

| 能力项 | 说明 | 输入示例 | 输出示例 |
|--------|------|----------|----------|
| 数据源接入 | 解析用户提供的 CSV/JSON/Excel 或数据库连接串 | `data.csv`、`{"sales": 120}` | 标准化数据字典 |
| 图表配置生成 | 根据数据特征推荐图表类型（折线/柱状/饼图） | 时间序列数据 | ECharts 配置 JSON |
| Django 项目集成 | 生成可嵌入 Django 项目的 dashboard 视图代码 | Django 项目路径 | `views.py` 代码片段 |
| 模块化布局 | 生成可拖拽的网格布局配置 | 模块数量与尺寸偏好 | `layout.json` |
| 数据刷新策略 | 配置定时刷新或实时推送方案 | 刷新间隔（秒） | 轮询/WebSocket 配置 |

### 1.2 明确不做的范围

- 不执行实际的数据分析或机器学习计算
- 不直接操作 Django 项目的数据库结构
- 不生成完整的 Django 项目脚手架（仅生成 dashboard 相关模块）
- 不处理认证授权体系的设计
- 不提供生产环境的部署脚本

### 1.3 适用对象

- Django 开发者：需要快速为现有项目添加数据看板
- 数据分析师：需要将分析结果可视化展示
- 产品经理：需要制作数据展示原型


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
