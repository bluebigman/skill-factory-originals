---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: vizzu-lib
name: vizzu-lib
displayName: 动态图表 数据叙事 可视化库
description: 将原始数据转化为可交互的动画图表，辅助构建数据故事。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/vizzu-lib
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: DataFlow Studio
agent_created: true
trigger_words: ["数据可视化", "动画图表", "数据故事", "动态图表", "图表库", "vizzu"]

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

# Vizzu-Lib 技能文档

## 一、能力边界速查卡

本技能面向需要将静态数据转化为动态叙事图表的开发者、数据分析师与内容创作者。它帮助你规划数据可视化的实现路径，而非替你编写全部代码。

| 维度 | 能做 | 不能做 |
|------|------|--------|
| 数据输入 | 接受 CSV、JSON、URL 指向的数据文件 | 不直接连接数据库或实时数据流 |
| 图表类型 | 柱状图、折线图、面积图、散点图、饼图及组合切换 | 不生成 3D 图表、地图或自定义渲染引擎 |
| 动画控制 | 设计图表状态切换、排序动画、时间轴叙事 | 不处理逐帧像素级动画细节 |
| 代码输出 | 生成 Vizzu 库的初始化代码、图表配置片段 | 不替代完整前端工程搭建 |
| 数据清洗 | 识别缺失值、类型异常并给出标注 | 不执行复杂的统计建模或数据修复 |

**适用对象**：需要快速原型验证的数据分析师、制作演示文稿的运营人员、教学场景中的师生。


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
