---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: stock-prediction-and-recommendation
name: stock-prediction-and-recommendation
displayName: 股票分析 行情预测 投资参考
description: 将用户提供的股票数据或文件转化为结构化分析结果，仅供学习参考。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/stock-prediction-and-recommendation
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: DataCraft Studio
agent_created: true
trigger_words: ["股票预测","stock prediction","行情分析","投资建议","股票推荐","stock recommendation","股价走势","金融数据分析"]
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

# 股票预测与推荐分析 Skill 文档

## 一、能力边界速查卡

### ✅ 能做（核心能力）

| 编号 | 能力项 | 说明 |
|------|--------|------|
| 1 | 数据解析与结构化 | 将用户提供的 CSV、Excel、JSON、URL 链接中的股票数据转换为统一结构 |
| 2 | 关键信息识别 | 自动提取股票代码、时间区间、价格序列、成交量等核心字段 |
| 3 | 规范格式输出 | 按约定模板生成分析报告，包含数据概览、趋势判断、风险提示 |
| 4 | 置信度标注 | 对每项预测结果标注置信水平（高/中/低），不确定项明确标注 |
| 5 | 批量处理与自定义 | 支持多股票同时分析，允许用户指定输出字段和格式偏好 |

### ❌ 不能做（明确边界）

| 编号 | 禁止事项 | 说明 |
|------|----------|------|
| 1 | 保证收益 | 不承诺任何投资回报率或盈利可能性 |
| 2 | 实时行情获取 | 不主动连接交易所或金融数据服务商获取实时数据 |
| 3 | 个性化投资建议 | 不根据用户风险偏好、资产状况给出买卖指令 |
| 4 | 替代专业投顾 | 不提供法律、税务、财务规划等专业意见 |
| 5 | 预测准确性承诺 | 不保证任何预测结果的准确率或可靠性 |

### 👥 适用对象

- 金融数据分析学习者
- 量化策略研究爱好者
- 需要结构化股票数据的研究人员
- 对股票分析流程感兴趣的开发者


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
