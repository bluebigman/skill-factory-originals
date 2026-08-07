---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: ruview
name: ruview
displayName: 空间感知 无线信号 存在检测
description: 将WiFi信号转化为空间感知与存在检测的结构化分析结果。
version: 1.0.2
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/ruview
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: SignalForge Studio
agent_created: true
trigger_words: ["ruview","WiFi感知","无线信号分析","空间监测","存在检测","信号测绘","室内定位"]
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

# ruview — 无线信号空间感知与存在检测分析

## 一、能力边界（一页纸速查卡）

### 1.1 能做什么

| 能力项 | 说明 | 输入要求 | 输出形式 |
|--------|------|----------|----------|
| 信号强度解析 | 解析 RSSI 数值序列，识别信号波动模式 | 至少 30 秒连续采样，采样率 ≥ 1Hz | 波动特征表（均值、方差、峰值频次） |
| 空间状态推断 | 根据信号多径效应变化，推断空间内是否存在移动物体 | 同一接收端至少 2 个发射源信号 | 存在/不存在/不确定 三态判定 |
| 区域划分建议 | 基于信号衰减模型，给出监测区域划分建议 | 房间尺寸、路由器位置、墙体材质 | 区域划分示意图（文字描述版） |
| 异常信号报告 | 识别信号突变（如设备移动、遮挡物变化） | 连续监测数据，时间跨度 ≥ 5 分钟 | 异常事件列表（时间戳+类型+置信度） |

### 1.2 不能做什么

| 限制项 | 说明 |
|--------|------|
| 不提供精确定位 | 无法给出厘米级坐标，仅能判断"某个区域内有/无活动" |
| 不识别具体人员 | 无法区分"张三"还是"李四"，仅能感知"有人/无人" |
| 不穿透厚重墙体 | 钢筋混凝土墙体对 2.4GHz 信号衰减严重，穿透后数据不可靠 |
| 不做实时告警推送 | 本 Skill 仅做分析，不包含消息推送、邮件通知等集成功能 |
| 不处理视频/图像 | 仅处理 WiFi 信号数据（RSSI/CSI），不涉及摄像头数据 |

### 1.3 适用对象

- 智能家居开发者：需要判断房间是否有人，用于灯光/空调自动控制
- 办公空间管理者：统计会议室使用频率，优化空间利用率
- 养老监护方案设计者：非接触式监测老人活动状态（需配合隐私合规审查）
- 物联网教学场景：演示无线信号与物理世界的映射关系


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
