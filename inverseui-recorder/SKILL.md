---
> 本内容由 AI 生成，仅供学习参考（《人工智能生成合成内容标识办法》显式标识）。
<!-- ai-generated-notice -->
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: inverseui-recorder
name: inverseui-recorder
displayName: 界面操作录制 本地自动化 流程回放
description: 录制真实界面操作，生成可复用脚本，安全执行本地自动化流程。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/inverseui-recorder
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: FlowCraft Studio
agent_created: true
trigger_words: ["inverseui-recorder", "界面录制", "UI自动化", "流程录制", "操作回放", "本地自动化"]
---

> 📜 **用户协议（User Agreement）**
> 1. 本 Skill 仅供学习与参考用途。使用本 Skill 产生的任何结果，由使用者自行承担全部责任；本 Skill 不提供任何明示或暗示的保证。
> 2. 涉及法律、财务、税务、投资、医疗等专业决策时，请务必咨询持证专业人士。
> 3. 本代码受版权法保护，未经授权复制、反向工程或商业利用将被追究法律责任。
<!-- user-agreement-injected -->


> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->

> 本内容由 AI 生成，仅供学习参考 <!-- ai-generated-notice -->

# inverseui-recorder 技能文档

## 一、能力边界速查卡

本技能面向需要在本地环境中记录界面操作流程、生成可复用脚本并安全执行的场景。以下是能力边界的一页纸说明：

| 维度 | 说明 |
|------|------|
| **核心用途** | 将用户在桌面应用或浏览器中的真实操作步骤录制为结构化脚本，支持后续回放与复用 |
| **输入来源** | 用户提供的操作演示、界面交互日志、URL 列表、本地文件路径 |
| **输出产物** | 可执行的自动化脚本（含步骤描述、元素定位、操作类型、等待条件） |
| **运行环境** | 本地机器，不依赖云端服务，数据不出本机 |
| **适用对象** | 需要重复执行界面操作的测试人员、运维人员、日常办公自动化需求者 |

### 能做（5项核心能力）

1. **操作录制**：捕获鼠标点击、键盘输入、滚动、拖拽等基础交互行为，按时间顺序记录。
2. **脚本生成**：将录制内容转换为带注释的脚本文件，支持常见格式（如 JSON 步骤序列、Python 伪代码）。
3. **安全校验**：在回放前对脚本进行静态检查，识别可能的风险操作（如删除文件、提交表单）。
4. **局部重放**：支持指定从某一步骤开始执行，便于调试和部分流程复用。
5. **置信度标注**：对录制过程中识别模糊的元素（如动态 ID、无文本按钮）标注置信度，提示用户确认。

### 不能做（明确边界）

- 不支持跨设备同步录制（仅限当前机器）。
- 不识别图像内容（如需图像识别请配合其他工具）。
- 不自动处理验证码、弹窗等需要人工判断的交互。
- 不保证录制脚本在界面改版后仍然有效（需重新录制或手动修正）。
- 不提供云端存储或分享功能。


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
