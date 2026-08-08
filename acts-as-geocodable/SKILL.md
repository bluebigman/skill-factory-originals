---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: acts-as-geocodable
name: acts-as-geocodable
displayName: 地理编码 地址解析 坐标转换
description: 将地址文本解析为结构化地理数据并输出坐标与置信度。
version: 1.0.1
rules_version: cpr-20260808-n152
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/acts-as-geocodable
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: LingMap Studio
agent_created: true
trigger_words: ["geocoding", "地址转坐标", "地理编码", "经纬度解析", "位置标准化"]
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

# acts-as-geocodable — 地理编码 Skill 文档

## 一、能力边界速查卡

本 Skill 面向需要将「非结构化地址文本」转换为「结构化地理信息」的场景，适用于数据分析师、后端开发者、运营人员及任何需要批量处理位置数据的用户。

### 能做（核心能力清单）

| 编号 | 能力项 | 说明 | 输入示例 | 输出示例 |
|------|--------|------|----------|----------|
| 1 | 地址文本解析 | 从自由文本中提取省/市/区/街道/门牌号 | "北京市朝阳区建国路88号" | `{province:"北京市", city:"北京市", district:"朝阳区", street:"建国路", number:"88号"}` |
| 2 | 坐标估算与输出 | 基于行政区划中心点或已知地标返回经纬度 | "上海市浦东新区" | `{lat:31.2304, lng:121.4737, source:"district_center"}` |
| 3 | 关键信息保留 | 原输入中的非地址信息（如联系人、备注）不丢失，原样透传 | "张三 13800138000 北京市海淀区中关村大街1号" | `{address:{...}, extra:{contact:"张三", phone:"13800138000"}}` |
| 4 | 置信度标注 | 每条结果附带置信度等级，区分精确匹配/模糊匹配/推测 | 见下文置信度门控 | `confidence: 0.85` |
| 5 | 批量处理与格式定制 | 支持多行输入、JSON 数组输入，输出格式可选 JSON/CSV/表格 | 见下文参数表 | 见下文输出规范 |

### 不能做（明确边界）

- 不能访问实时地图服务或卫星影像，所有坐标均为静态参考值。
- 不能解析非中文地址（英文、日文等需先自行翻译为中文）。
- 不能处理加密、图片或语音中的地址信息，仅接受纯文本。
- 不能保证坐标精确到建筑物级别，街道号缺失时只返回区级中心点。
- 不执行任何形式的地址验证（如确认该地址是否真实存在）。

### 适用对象

- 需要将用户通讯录、订单收货地址、门店列表等批量转换为坐标的开发者。
- 需要从日志、备注、自由文本中抽取位置信息的数据分析人员。
- 需要为地图可视化准备数据集的运营人员。


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
