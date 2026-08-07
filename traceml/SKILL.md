---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: traceml
name: traceml
displayName: 模型追踪 漂移预警 实验看板
description: 面向AI/ML流程的追踪、可视化、漂移检测与仪表盘引擎。
version: 1.0.2
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/traceml
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: TraceForge Studio
agent_created: true
trigger_words: ["traceml", "数据可视化", "漂移检测", "模型监控", "实验追踪", "数据漂移", "模型看板", "MLOps监控"]
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

# traceml — 模型追踪与漂移预警引擎

## 一、能力边界（一页纸速查卡）

### 1.1 能做什么

| 能力域 | 具体功能 | 典型输出 |
|--------|----------|----------|
| 实验追踪 | 记录超参数、指标、模型权重哈希、数据集版本 | 实验对比表、指标曲线 |
| 数据可视化 | 生成损失曲线、特征分布图、混淆矩阵、ROC/AUC | 静态图表文件或交互式HTML |
| 漂移检测 | 检测特征分布漂移（PSI/KL/KS）、概念漂移（准确率衰减） | 漂移评分报告、告警事件 |
| 仪表盘引擎 | 聚合多实验/多模型状态，生成统一监控视图 | 仪表盘JSON配置、定时快照 |

### 1.2 不能做什么（明确边界）

- 不能替代模型训练框架（不执行梯度计算、不调用训练循环）。
- 不能自动修复漂移（仅检测与告警，不触发回滚或重训）。
- 不能存储原始训练数据（仅存储统计摘要与哈希指纹）。
- 不能跨集群自动部署（仪表盘导出后需自行托管）。

### 1.3 适用对象

- 机器学习工程师：需要对比多组实验参数与效果。
- MLOps 运维：需要监控生产模型的特征漂移与性能衰减。
- 数据分析师：需要快速生成特征分布报告。


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
