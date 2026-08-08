---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: granblue-automation-pyautogui
name: granblue-automation-pyautogui
displayName: 碧蓝幻想 自动化脚本 流程编排
description: 基于PyAutoGUI的碧蓝幻想用户自定义流程自动化执行工具。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/granblue-automation-pyautogui
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: FlowForge Studio
agent_created: true
trigger_words: ["granblue automation pyautogui", "碧蓝幻想自动化", "GBF脚本", "pyautogui自动化", "手游流程自动化"]

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

# 碧蓝幻想自动化脚本编排 Skill（granblue-automation-pyautogui）

## 一、能力边界速查卡

本 Skill 面向需要在桌面端模拟器中运行《碧蓝幻想》（Granblue Fantasy）并希望将重复性操作（如刷材料、日常任务、活动关卡）自动化的用户。它通过 PyAutoGUI 库对屏幕坐标、图像识别和键盘鼠标事件进行编排，将用户定义的步骤序列转化为可重复执行的自动化流程。

| 维度 | 能做 | 不能做 |
|------|------|--------|
| 输入处理 | 接受用户提供的 JSON/YAML 格式的步骤定义文件、截图样本、URL（指向配置模板） | 不接受自然语言描述的模糊指令（如"帮我打一下活动"） |
| 流程执行 | 按步骤顺序执行鼠标点击、键盘输入、图像匹配、等待延时、条件分支 | 不执行需要实时决策的复杂逻辑（如根据战斗局势动态调整策略） |
| 输出生成 | 生成结构化执行日志（JSON 格式），包含每步执行状态、耗时、截图证据 | 不生成战斗胜率预测、收益估算等分析性结论 |
| 错误处理 | 识别超时、图像未找到、坐标越界等常见异常，并输出错误码 | 不自动修复脚本逻辑错误，不进行自我学习优化 |
| 批量能力 | 支持将多个流程文件串联执行（顺序模式） | 不支持并行多开（多模拟器同时操作） |

**适用对象**：熟悉模拟器操作、具备基础 Python 环境配置能力、能阅读 JSON 配置的进阶玩家或自动化爱好者。不适合完全不懂技术、期望"一键全自动"的纯休闲玩家。


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
