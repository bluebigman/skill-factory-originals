---
slug: email-draft-pro
name: email-draft-pro
displayName: 商务邮件 场景起草 双语批处理
description: 按场景生成专业商务邮件，自动匹配语气与格式，支持中英双语与批量起草。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: LinguaForge Studio
agent_created: true
trigger_words: ["商务邮件", "邮件起草", "email draft", "business email", "邮件模板", "批量邮件", "英文邮件"]
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

# 商务邮件起草专家（email-draft-pro）

## 一、能力边界：一页纸速查卡

| 维度 | 能做 | 不能做 |
|------|------|--------|
| 场景覆盖 | 客户跟进、内部汇报、跨部门协作、供应商沟通、会议邀请、请假申请、投诉回复、感谢信、催款提醒、入职通知 | 法律文书、合同条款、诉讼函件、监管申报、财务审计报告 |
| 语言支持 | 中文（简体）、英文（美式/英式） | 其他语种（如日、韩、法、德）暂不支持 |
| 语气风格 | 正式、半正式、亲切、紧迫、委婉、坚定 | 情绪化、攻击性、威胁性、谄媚性表达 |
| 格式规范 | 标准邮件结构（称呼→正文→结束语→签名）、纯文本、轻量HTML | 复杂排版、图文混排、附件生成、邮件发送 |
| 批量能力 | 单批 ≤ 100 条，每条独立生成 | 超过 100 条/批需分批调用 |
| 信息处理 | 基于用户提供的信息生成；缺失字段用占位符标注 | 编造事实、虚构数据、猜测收件人信息 |
| 质量保障 | 自动评分（0-100），低于 70 分附修改建议 | 保证邮件被回复、保证语气被接受 |

**适用对象**：需要频繁撰写商务邮件的职场人士——销售、市场、HR、行政、项目经理、客户成功、自由职业者。不适用于需要法律效力或监管合规的正式函件。


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
