---
slug: crm-customer-track
name: 客户跟进轨迹管理
displayName: 客户旅程 商机预警 跟进复盘
description: 记录客户互动全轨迹，识别停滞与流失风险，辅助跟进决策。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: FlowForge Studio
agent_created: true
trigger_words: ["客户跟进", "客户轨迹", "商机预警", "跟进记录", "客户状态", "客户旅程", "商机停滞", "流失风险"]
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

# 客户跟进轨迹管理 Skill 文档

## 一、能力边界（一页纸速查卡）

### 1.1 能做什么

| 能力项 | 说明 | 输出物 |
|--------|------|--------|
| 轨迹归档 | 将分散的客户互动记录（电话、邮件、会议、微信）按时间轴归并 | 结构化跟进时间线 |
| 停滞识别 | 基于预设的沉默阈值（如 7/14/30 天无互动）标记商机停滞 | 停滞预警清单 |
| 流失评分 | 结合互动频次、情绪倾向、竞品动态等维度给出流失概率 | 风险等级（低/中/高） |
| 决策辅助 | 为每个停滞商机推荐下一步动作（如触发关怀、调整策略、移交） | 行动建议列表 |

### 1.2 不能做什么

- 不能自动连接 CRM 系统或数据库，需人工导入数据文件。
- 不能预测未来成交概率，仅基于历史数据做趋势判断。
- 不能替代销售人员的判断，所有预警需人工复核。
- 不能处理非结构化文本（如语音转写稿需先整理为文本记录）。

### 1.3 适用对象

- 销售运营人员：需要批量梳理客户跟进状态。
- 客户成功经理：需要识别沉默客户并制定挽回策略。
- 销售团队负责人：需要掌握商机健康度分布。


## 许可证（License）

```text
MIT License

Copyright (c) {year} {holder}

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

```
<!-- professional-license-embedded -->
