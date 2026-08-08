---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: ai-short-drama-agent-company
name: ai-short-drama-agent-company
displayName: 短剧制片 全流程团队 矩阵协作
description: 面向短剧公司的矩阵化团队模板，覆盖策划、编剧、拍摄、后期、宣发全流程。
version: 1.0.2
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/ai-short-drama-agent-company
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: FlowForge Studio
agent_created: true
trigger_words: ["ai-short-drama-agent-company", "短剧公司", "短剧制片", "短剧团队", "短剧工作流", "短剧制作", "短剧协作"]

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

# 短剧制片 全流程团队 矩阵协作 Skill

## 一、能力边界：一页纸速查卡

本 Skill 将 AI 短剧公司的组织架构与工作流封装为可调用的团队矩阵模板。它不是一个自动生成短剧的“魔法盒”，而是一套**角色分工 + 流程编排 + 交付物规范**的协作框架。

### 1.1 能做什么

| 能力项 | 具体说明 | 输出物示例 |
|--------|----------|------------|
| 团队角色编排 | 按短剧生产链路拆分为 5 个专业角色（策划/编剧/拍摄/后期/宣发），每个角色有独立职责与协作接口 | 角色卡（含职责、输入、输出、协作对象） |
| 流程节点管理 | 从立项到上线拆分为 12 个标准节点，每个节点有前置条件、执行动作、验收标准 | 流程甘特图 + 节点检查表 |
| 交付物模板 | 为每个节点提供可直接填写的文档模板（策划案、分镜脚本、排期表、投放计划等） | 模板文件（Markdown/CSV） |
| 跨角色协作协议 | 定义角色间的交接格式、评审机制、版本管理规则 | 交接单模板 + 评审会议纪要模板 |
| 预算与资源估算 | 提供分环节的成本估算参数表（拍摄天数、人员配置、设备清单） | 预算估算表（含参数范围） |

### 1.2 不能做什么（明确边界）

| 限制项 | 说明 |
|--------|------|
| 不生成完整成片 | 本 Skill 输出的是文档、计划、脚本，不包含视频渲染、剪辑合成等实际制作 |
| 不替代真人决策 | 所有节点需由使用者（制片人/导演）确认后方可进入下一环节 |
| 不提供平台算法 | 宣发环节仅提供投放策略框架，不包含抖音/快手等平台的具体算法参数 |
| 不承诺数据结果 | 所有预估数据（播放量、转化率）均为参考区间，实际表现受市场波动影响 |
| 不处理版权纠纷 | 涉及音乐、字体、肖像等版权问题需使用者自行确认合规性 |

### 1.3 适用对象

| 适用场景 | 不适用场景 |
|----------|------------|
| 短剧初创团队（3-10 人）需要标准化流程 | 单人独立制作（流程过重） |
| 从 0 到 1 搭建短剧生产体系 | 已有成熟 SOP 的大型制作公司 |
| 跨职能协作混乱、交付物不统一的团队 | 仅需单一环节（如只写剧本）的临时需求 |
| 需要向投资人/合作方展示完整制作能力的团队 | 非短剧类视频（如长剧、纪录片）制作 |


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
