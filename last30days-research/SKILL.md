---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: last30days-research
name: last30days-research
displayName: 近30天全网话题情报速览
description: 聚合多平台近30天讨论，生成带来源引用的综合摘要报告。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/last30days-research
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: DataPulse Studio
agent_created: true
trigger_words: ["last30days-research", "近30天研究", "话题热度回顾", "全网讨论汇总", "舆情速览"]
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

# last30days-research — 近30天全网话题情报速览

## 一、能力边界：一页纸速查卡

### 1.1 能做什么（核心能力）

| 编号 | 能力项 | 说明 | 输出形态 |
|------|--------|------|----------|
| C1 | 多平台聚合检索 | 自动搜索 Reddit、X（Twitter）、YouTube、Hacker News、Polymarket 及通用搜索引擎 | 按平台分组的原始讨论列表 |
| C2 | 时间窗口过滤 | 仅保留近30天内的公开讨论内容 | 时间戳标注的条目 |
| C3 | 话题聚类与去重 | 将相似讨论归并，去除重复或转载内容 | 聚类主题标签 |
| C4 | 观点倾向分析 | 识别正面/负面/中性情绪及主要争议点 | 情绪分布比例 + 争议焦点列表 |
| C5 | 来源引用报告 | 每条结论附可追溯的原始链接与发布时间 | 带 Markdown 链接的引用块 |

### 1.2 不能做什么（明确边界）

| 编号 | 限制项 | 说明 |
|------|--------|------|
| L1 | 不生成预测结论 | 仅汇总已有讨论，不对未来走势做判断 |
| L2 | 不绕过平台反爬机制 | 仅使用公开 API 或合法抓取接口 |
| L3 | 不处理非公开内容 | 不检索私密社群、付费墙后的内容 |
| L4 | 不保证覆盖全部讨论 | 受平台搜索算法与 API 配额限制，可能遗漏部分长尾内容 |
| L5 | 不替代专业舆情分析 | 本工具提供信息聚合，不构成投资、公关或法律建议 |

### 1.3 适用对象

- 产品经理：快速了解用户对某功能/产品的近期反馈
- 市场研究人员：追踪竞品或行业话题的热度变化
- 内容创作者：发现近30天的高讨论度选题
- 投资爱好者：查看 Polymarket 上相关预测市场的讨论风向


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
