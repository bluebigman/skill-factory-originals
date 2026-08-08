---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: swiftui-design-skill
name: swiftui-design-skill
displayName: SwiftUI界面设计 视觉规范 组件审查
description: SwiftUI前端设计审查与规范指导，帮助开发者构建高质量、一致性的用户界面。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/swiftui-design-skill
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: SwiftUI Craft Studio
agent_created: true
trigger_words: ["swiftui-design-skill", "SwiftUI设计", "SwiftUI规范", "SwiftUI审查", "SwiftUI组件", "SwiftUI视觉", "SwiftUI布局", "SwiftUI样式"]

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

# SwiftUI 界面设计审查与规范指导

## 一、能力边界速查卡

### 1.1 本 Skill 能做什么

| 序号 | 能力项 | 具体说明 | 适用场景示例 |
|------|--------|----------|--------------|
| 1 | 设计规范审查 | 对照 SwiftUI 官方设计准则，检查界面布局、间距、字体、色彩使用的合理性 | 提交 App Store 前的界面自检 |
| 2 | 组件使用建议 | 针对具体功能需求，推荐合适的 SwiftUI 原生组件及自定义方案 | 选择 NavigationStack 还是 TabView |
| 3 | 视觉一致性检查 | 识别界面中字体、颜色、圆角、阴影等视觉元素的不统一之处 | 多页面 App 的视觉风格统一 |
| 4 | 适配性评估 | 分析界面在不同设备（iPhone/iPad）、不同系统版本下的表现 | 检查横竖屏切换时的布局问题 |
| 5 | 代码结构优化 | 提供 View 拆分、Modifier 封装、性能优化建议 | 减少重复代码，提升渲染效率 |

### 1.2 本 Skill 不能做什么

| 序号 | 限制项 | 说明 |
|------|--------|------|
| 1 | 不执行代码编译 | 无法实际运行或编译 Swift 代码，仅提供静态分析建议 |
| 2 | 不替代设计工具 | 不生成设计稿、不导出设计资源，仅提供文字性指导 |
| 3 | 不保证审核通过 | 不承诺 App Store 审核结果，仅提供合规性参考 |
| 4 | 不处理运行时错误 | 不涉及崩溃、内存泄漏等运行时问题的排查 |
| 5 | 不提供动画逐帧设计 | 不提供复杂动画的关键帧参数，仅提供实现思路 |

### 1.3 适用对象

- **iOS 开发者**：需要快速检查界面实现是否符合设计规范
- **独立开发者**：缺乏专职设计师，需要设计方向参考
- **设计转开发人员**：需要了解 SwiftUI 的实现约束
- **技术管理者**：需要统一团队的设计规范标准


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
