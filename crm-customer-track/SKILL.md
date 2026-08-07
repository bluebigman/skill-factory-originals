---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: crm-customer-track
name: 客户跟进轨迹管理
displayName: 客户轨迹 商机预警 跟进决策
description: 记录客户互动全轨迹，识别停滞与流失风险，辅助跟进决策。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/crm-customer-track
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: FlowForge Studio
agent_created: true
trigger_words: ["客户跟进", "客户轨迹", "商机预警", "跟进记录", "客户状态", "互动历史", "停滞分析", "流失风险"]
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

# 客户跟进轨迹管理 Skill 文档

## 一、能力边界（一页纸速查卡）

### 1.1 能做什么

| 能力项 | 说明 | 输入要求 |
|--------|------|----------|
| 轨迹记录 | 按时间线汇总客户所有互动事件（电话、邮件、会议、消息） | 事件列表或原始日志 |
| 停滞识别 | 计算距上次互动的时间间隔，标记超过阈值的客户 | 客户ID + 最近互动日期 |
| 流失风险评分 | 基于互动频率衰减、负面反馈、竞对接触等信号给出风险等级 | 至少3条历史互动记录 |
| 跟进建议生成 | 根据风险等级和客户阶段输出下一步动作建议 | 客户阶段 + 风险等级 |
| 轨迹可视化 | 输出结构化时间线（文本格式） | 事件序列 |

### 1.2 不能做什么

- 不自动发送任何消息或邮件（仅生成建议文本）
- 不预测具体成交金额或成交概率（只做风险分级）
- 不替代人工判断客户意图（输出仅供参考）
- 不接入外部 CRM 系统（需手动导入数据）
- 不处理非文本类数据（如语音录音、视频会议原始文件）

### 1.3 适用对象

- 销售运营人员：需要快速掌握客户互动全貌
- 客户成功经理：需要识别沉默客户并及时干预
- 销售团队负责人：需要了解团队跟进密度与盲区
- 初创企业创始人：需要轻量级客户关系管理辅助


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
