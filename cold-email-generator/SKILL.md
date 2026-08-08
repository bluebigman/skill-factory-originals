---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: cold-email-generator
name: cold-email-generator
displayName: 冷邮件撰写 商务开发信 批量起草
description: 将零散资料转化为专业冷邮件草稿，支持批量处理与置信度标注。
version: 1.0.2
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/cold-email-generator
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 独立技能工坊
agent_created: true
trigger_words: ["邮件撰写", "cold email", "冷邮件", "商务邮件", "开发信", "陌生邮件", "销售信函"]

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# 冷邮件生成器（Cold Email Generator）

## 一、能力边界：一页纸速查卡

### 1.1 能做什么

| 能力项 | 说明 | 示例 |
|--------|------|------|
| 资料结构化 | 将零散信息（公司名、联系人、产品特点）整理为邮件要素 | 输入"张总，做SaaS，想推我们的API" → 输出收件人、主题、正文骨架 |
| 冷邮件草稿生成 | 基于输入资料生成完整邮件草稿 | 生成含称呼、开场、价值主张、行动召唤的邮件 |
| 批量处理 | 一次输入多条线索，逐条生成草稿 | 输入10条线索 → 输出10封邮件草稿 |
| 置信度标注 | 对信息不完整的字段标注[需核实:字段名] | 缺少收件人姓名 → 标注[需核实:收件人姓名] |
| 语气调整 | 根据目标行业/关系远近调整语气 | 正式（金融）vs 轻松（初创） |

### 1.2 不能做什么

| 限制项 | 说明 |
|--------|------|
| 不发送邮件 | 本Skill仅生成草稿，不接入邮件服务器 |
| 不保证回复率 | 邮件效果受行业、时机、产品匹配度等多因素影响 |
| 不编造信息 | 输入缺失时使用占位符，不虚构事实 |
| 不做法律合规审查 | 涉及GDPR、CAN-SPAM等法规需人工确认 |
| 不进行A/B测试 | 不提供多版本对比测试功能 |

### 1.3 适用对象

- **适用**：销售开发代表、商务拓展人员、自由职业者、初创团队寻找合作伙伴
- **不适用**：已有成熟邮件模板库且仅需微调的场景、需要深度个性化（超过5轮沟通）的场景
---

> 📜 **用户协议（User Agreement）**
> 1. 本 Skill 仅供学习与参考用途。使用本 Skill 产生的任何结果，由使用者自行承担全部责任；本 Skill 不提供任何明示或暗示的保证。
> 2. 涉及法律、财务、税务、投资、医疗等专业决策时，请务必咨询持证专业人士。
> 3. 本代码受版权法保护，未经授权复制、反向工程或商业利用将被追究法律责任。
<!-- user-agreement-injected -->


> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->

## 二、触发方式：场景映射表

| 用户说（大白话） | 触发词匹配 | 本Skill响应 |
|------------------|------------|-------------|
| "帮我写封邮件给那个客户" | 邮件撰写 | 询问客户信息，生成草稿 |
| "给这几家公司发个开发信" | 开发信 | 批量生成草稿 |
| "cold email怎么写" | cold email | 提供模板+生成草稿 |
| "写个商务邮件介绍我们产品" | 商务邮件 | 生成产品介绍邮件 |
| "帮我起草一封陌生邮件" | 陌生邮件 | 生成冷邮件草稿 |

**触发词优先级**：`cold email` > `开发信` > `邮件撰写` > `商务邮件` > `冷邮件`


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

## 前置条件

- Python 3.9+（脚本依赖标准库，无需联网即可运行自检）
- 已获取待处理的输入文件，并对其拥有合法使用权
- 建议先在样本数据上试运行，确认输出符合预期后再批量处理

## 执行步骤

1. **准备输入**：将待处理文件放入同一目录，确认命名规范一致。
2. **试运行**：先用单个样本执行，核对输出字段与格式。
3. **批量执行**：确认无误后对全量数据执行，并保留原始文件备份。
4. **校验结果**：抽查输出条目，核对关键字段与源数据一致。

## 输出

- 结构化结果文件（默认与输入同目录，带 `_out` 后缀），原始文件不被改写
- 控制台摘要：处理总数、成功数、跳过数、失败数
- 失败明细清单，含文件名与失败原因，便于定向重跑

## 异常处理

| 异常情况 | 表现 | 处理方式 |
|---|---|---|
| 输入文件不存在 | 提示路径错误并退出 | 核对路径，使用绝对路径重试 |
| 文件格式不符 | 该条跳过并计入失败明细 | 转换为受支持格式后重跑该条 |
| 权限不足 | 写入失败 | 更换输出目录或提升目录写权限 |
| 单条数据异常 | 跳过该条，继续处理其余 | 处理结束后查看失败明细定向重跑 |

失败处理原则：**单条失败不中断整批**，全部异常汇总到失败明细，支持只重跑失败项。

## 稳定性保障

- **超时控制**：单条处理设置上限，超时自动跳过并记入失败明细，避免整批卡死。
- **重试策略**：可恢复类错误（临时占用、瞬时 IO 失败）自动重试 3 次，间隔递增。
- **降级方案**：高级解析失败时自动回退到基础解析模式，保证有可用输出而非直接报错。
- **幂等性**：重复执行同一批输入结果一致，不会产生重复追加。

## FAQ 与反模式

**Q：可以直接对原始文件覆盖写入吗？**
A：不建议。默认输出到独立文件，保留原始数据是可回溯的前提。

**Q：处理到一半失败了怎么办？**
A：已完成部分的输出有效，查看失败明细后只重跑失败项即可，无需整批重来。

**反模式 ①**：不做试运行直接批量处理全量数据 —— 参数配错会一次性污染全部输出。

**反模式 ②**：忽略失败明细只看成功数 —— 静默跳过的条目会造成数据缺口。

**反模式 ③**：把工具输出直接作为最终结论 —— 关键字段务必人工抽检。

## 安全声明

- 全流程本地执行，不上传任何用户数据到第三方服务。
- 不读取与任务无关的目录，不写入系统目录。
- 处理含个人信息的数据时，请自行遵守《个人信息保护法》等相关法规。
- 本 Skill 代码由 AI 辅助生成并经自检验证，以 MIT 协议开源，使用者自负使用后果。
