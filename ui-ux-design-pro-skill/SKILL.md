---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: ui-ux-design-pro-skill
name: ui-ux-design-pro-skill
displayName: 界面体验 设计规范 交互评审
description: 面向产品设计全流程的 AI 辅助技能，提供结构化评审、规范生成与交付物检查。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/ui-ux-design-pro-skill
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: LinDesignLab
agent_created: true
trigger_words: ["ui ux design pro skill", "界面设计评审", "交互规范生成", "设计系统检查", "UI UX 设计辅助"]

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

# 界面体验设计专业辅助技能（UI/UX Design Pro Skill）

## 一、能力边界：一页纸速查卡

### 1.1 能做（核心能力清单）

| 编号 | 能力项 | 说明 | 输入示例 | 输出示例 |
|------|--------|------|----------|----------|
| C1 | 设计稿结构化解析 | 将截图、设计文件描述或 URL 中的视觉信息转化为结构化设计要素表 | 一张移动端登录页截图 | 色彩体系、字体层级、间距网格、组件清单 |
| C2 | 交互流程梳理 | 从用户操作路径描述中提取关键节点、分支条件与异常态 | "用户忘记密码后如何找回" | 流程图（文字版）、状态转换表 |
| C3 | 设计规范生成 | 根据产品类型与目标平台，生成可落地的设计规范草案 | "面向 B 端后台的表格页" | 色彩、字体、间距、组件状态规范 |
| C4 | 可用性检查 | 对照 WCAG 2.1 及常见设计原则，检查交付物中的潜在问题 | 一份高保真原型描述 | 问题清单 + 严重级别 + 修改建议 |
| C5 | 设计交付物清单校验 | 检查设计交付物是否包含必要文件与标注 | 交付物列表 | 缺失项清单 + 补充建议 |

### 1.2 不能做（明确边界）

| 编号 | 限制项 | 说明 |
|------|--------|------|
| L1 | 不生成实际图片/图标 | 本技能仅输出文字描述与规范，不产出位图或矢量文件 |
| L2 | 不替代真实用户测试 | 可用性检查基于规则推演，无法替代真实用户的行为数据 |
| L3 | 不提供开发代码 | 可给出交互逻辑描述，但不生成 HTML/CSS/JS 代码 |
| L4 | 不评估商业价值 | 不判断设计方案对业务指标的影响，仅关注体验与规范层面 |
| L5 | 不处理非设计类问题 | 如后端架构、算法逻辑、运营策略等超出设计范畴的问题 |

### 1.3 适用对象

- **产品经理**：快速验证交互方案的完整性
- **UI/UX 设计师**：设计评审前的自查、规范整理
- **前端开发人员**：理解设计意图与状态定义
- **创业团队**：无专职设计师时获得基础设计指导


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
