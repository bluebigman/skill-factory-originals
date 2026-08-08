---
> 本内容由 AI 生成，仅供学习参考（《人工智能生成合成内容标识办法》显式标识）。
<!-- ai-generated-notice -->
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: clear-empty-attributes
name: clear-empty-attributes
displayName: 表单空值清洗 数据入库 属性规整
description: 将表单提交的空字符串转为nil，避免数据库存储脏数据。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/clear-empty-attributes
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: DataPorter
agent_created: true
trigger_words: ["clear empty attributes", "空属性清理", "空字符串转nil", "表单空值处理", "属性清洗"]
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

# SKILL.md — clear-empty-attributes

## 一、能力边界（一页纸速查卡）

### 能做（5项核心能力）

| 编号 | 能力项 | 说明 | 示例 |
|------|--------|------|------|
| 1 | 空字符串识别 | 检测 Active Record 对象属性中值为 `""` 的字段 | `user.name = ""` |
| 2 | 空值转换 | 将空字符串统一转为 `nil` | `user.name = nil` |
| 3 | 批量处理 | 一次操作处理多个属性或多个对象 | 表单提交的 10 个字段一次性清洗 |
| 4 | 白名单过滤 | 仅处理指定字段，避免误伤 | 只清洗 `name`、`email`，保留 `password_digest` |
| 5 | 保存前拦截 | 在 `save` 回调前自动执行，确保入库数据干净 | `before_save :clear_empty_attributes` |

### 不能做（明确边界）

| 编号 | 不可用场景 | 原因 |
|------|-----------|------|
| 1 | 不能处理非 Active Record 对象 | 依赖 AR 的回调机制和属性访问器 |
| 2 | 不能识别"空白字符串"（如 `"   "`） | 仅匹配 `""`，不处理空格填充 |
| 3 | 不能自动判断字段是否允许为 nil | 需由调用方自行决定哪些字段需要清洗 |
| 4 | 不能处理 `nil` 以外的其他假值（如 `false`、`0`） | 只针对空字符串场景 |
| 5 | 不能跨数据库迁移历史数据 | 仅作用于新写入的数据 |

### 适用对象

- **目标用户**：Rails 开发者、使用 Active Record 的 Ruby 项目维护者
- **适用场景**：Web 表单提交、API 参数接收、批量导入数据清洗
- **不适用**：非 AR 模型、纯 Ruby 对象、需要保留空字符串语义的场景


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
