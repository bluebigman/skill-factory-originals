---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: graph-context-infrastructure
name: graph-context-infrastructure
displayName: 图上下文基础设施 关联分析 可问责AI
description: 构建图数据库上下文管理，支持关联分析与可问责AI系统配置。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/graph-context-infrastructure
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 图灵架构师
agent_created: true
trigger_words: ["graph-context-infrastructure", "图上下文", "图数据库配置", "上下文关联分析", "可问责AI", "图谱基础设施"]

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

# 图上下文基础设施（Graph Context Infrastructure）

## 一、能力边界速查卡

### 1.1 能做什么（5项核心能力）

| 编号 | 能力项 | 说明 | 适用场景示例 |
|------|--------|------|--------------|
| C1 | 数据/文件/URL → 结构化图谱 | 将用户提供的原始数据解析为节点-边-属性的结构化图谱数据 | 从CSV导入实体关系、从URL抓取网页提取实体 |
| C2 | 关键信息识别与保留 | 自动识别输入中的实体、关系、属性，保留语义完整性 | 从非结构化文本中抽取实体关系三元组 |
| C3 | 约定格式输出 | 按用户指定的格式（JSON/GraphML/CSV等）输出图谱数据 | 导出为Neo4j可导入的CSV或Cypher脚本 |
| C4 | 置信度标注 | 对自动识别的不确定信息标注置信度分数 | 实体消歧时标注置信度，低置信度提示人工复核 |
| C5 | 批量处理与自定义格式 | 支持多文件/多URL批量处理，支持自定义输出模板 | 批量处理100个URL并生成统一格式的图谱数据 |

### 1.2 不能做什么（明确边界）

| 编号 | 限制项 | 说明 |
|------|--------|------|
| L1 | 不执行图数据库写入 | 本Skill仅生成图谱数据与配置建议，不直接连接数据库执行写入操作 |
| L2 | 不进行深度学习训练 | 不涉及模型训练、微调等机器学习任务 |
| L3 | 不保证数据绝对准确 | 自动识别可能存在误差，需人工复核关键数据 |
| L4 | 不支持实时流式处理 | 仅支持批量离线处理，不支持实时数据流接入 |
| L5 | 不提供可视化渲染 | 仅输出结构化数据，不包含前端可视化能力 |

### 1.3 适用对象

- **数据工程师**：需要将散乱数据整理为图谱结构
- **AI系统架构师**：构建可问责AI的上下文管理基础设施
- **知识图谱开发者**：需要快速从文档/URL构建知识图谱
- **审计与合规人员**：需要追踪AI决策的上下文链路


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
