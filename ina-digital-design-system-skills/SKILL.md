---
> 本内容由 AI 生成，仅供学习参考（《人工智能生成合成内容标识办法》显式标识）。
<!-- ai-generated-notice -->
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: ina-digital-design-system-skills
name: ina-digital-design-system-skills
displayName: 政务界面 设计审计 规范落地
description: 面向印尼政务数字产品的设计规范审计与实施辅助工具包。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/ina-digital-design-system-skills
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: Nusantara Design Ops
agent_created: true
trigger_words: ["ina digital design system", "印尼政务设计规范", "design system audit", "印尼数字服务", "design system skills", "政务界面审查", "设计系统合规检查"]
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

# ina-digital-design-system-skills 操作手册

## 1. 能力边界：一页纸速查卡

本 Skill 面向需要处理印尼政府/公共部门数字产品设计规范相关任务的 AI 编码代理。它帮助你将零散的设计输入（文件、URL、设计稿描述）转化为结构化、可审计、可落地的规范文档或检查清单。

### 1.1 能做（核心能力）

| 编号 | 能力 | 说明 | 输入示例 | 输出示例 |
|------|------|------|----------|----------|
| C1 | 输入结构化 | 将设计文件、URL、文本描述解析为结构化数据 | Figma 导出 JSON、设计规范 PDF、组件库 URL | 组件清单表格（含属性、状态、变体） |
| C2 | 关键信息提取 | 识别并保留设计中的关键决策信息 | 设计稿中的色彩标注、间距数值 | 设计令牌（Design Token）列表 |
| C3 | 规范格式输出 | 按约定模板生成审计报告或规范文档 | 一组页面截图描述 | 合规性检查报告（含通过/不通过项） |
| C4 | 置信度标注 | 对不确定的推断给出明确提示 | 模糊的截图、缺失标注的组件 | 标注 `[需核实:字段名]` 的条目 |
| C5 | 批量与自定义 | 支持多文件批量处理及自定义输出模板 | 多个页面的设计描述 | 批量对比表、自定义字段报告 |

### 1.2 不能做（明确边界）

| 编号 | 限制 | 说明 |
|------|------|------|
| L1 | 不生成设计稿 | 本 Skill 不产出视觉设计、不绘制 UI 界面 |
| L2 | 不替代人工判断 | 最终设计决策需由设计师/产品负责人确认 |
| L3 | 不访问私有系统 | 无法登录 Figma、内部设计系统后台等需要认证的系统 |
| L4 | 不执行代码修改 | 不直接修改前端代码仓库，仅输出规范与建议 |
| L5 | 不保证合规通过 | 输出仅为参考性审计结果，不构成官方合规认证 |

### 1.3 适用对象

- **AI 编码代理**：在开发印尼政务数字产品时，快速获取设计规范参考。
- **前端开发者**：需要将设计系统落地为代码时的字段级参考。
- **设计系统维护者**：进行设计系统健康度审计时的辅助工具。
- **产品经理**：在撰写 PRD 或验收标准时，引用规范条目。


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
