---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: code-review-single-skill
name: code-review-single-skill
displayName: 代码审查 单文件检视 质量门禁
description: 对单份代码文件执行结构化审查，输出问题清单与改进建议。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/code-review-single-skill
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: Lin Chen
agent_created: true
trigger_words: ["代码审查", "code review", "单文件审查", "代码检视", "review code"]
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

# 单文件代码审查 Skill 文档

## 一、能力边界速查卡

本 Skill 面向**单份代码文件**的结构化审查场景，帮助开发者快速定位潜在问题。

| 维度 | 能做 | 不能做 |
|------|------|--------|
| 输入 | 单份代码文件内容（粘贴文本或提供文件路径） | 多文件跨模块依赖分析、完整项目架构评审 |
| 分析 | 语法风格、命名规范、基础逻辑缺陷、常见反模式 | 运行时性能基准测试、安全漏洞渗透验证 |
| 输出 | 问题分级清单（阻断/建议/可选）、修改建议 | 自动修复代码、生成补丁文件 |
| 适用对象 | 个人开发者、小型团队日常自检 | 大型组织合规审计、CI/CD 流水线强制门禁 |

**适用对象**：需要快速自查代码质量的开发者；在提交 PR 前希望获得第二双眼睛的团队个人成员。

## 二、触发方式与场景映射

当你的需求匹配以下任一场景时，可使用本 Skill：

| 大白话场景 | 触发词示例 | 说明 |
|-----------|-----------|------|
| "帮我看看这段代码有啥问题" | 代码审查 / code review | 最常用入口 |
| "这个函数写得对不对" | 单文件审查 / 代码检视 | 聚焦单文件 |
| "提交前帮我检查一下" | review code / 代码检查 | 提交前自检 |

**注意**：若需求涉及多个文件间的调用关系、数据库 schema 变更、或需要与历史提交对比，请改用其他专用工具。

## 三、标准执行流程

### 前置条件

- 用户提供**完整**的代码文件内容（文本粘贴或文件路径）
- 明确告知编程语言（若无法从扩展名/语法判断）
- 如有特殊审查重点（如安全性、可读性），请提前说明

### 执行步骤

1. **解析输入**：识别语言类型、代码规模（行数）、主要结构（函数/类/模块）。
2. **静态扫描**：按以下维度逐项检查：
   - 命名规范（变量/函数/类命名是否清晰一致）
   - 代码风格（缩进、空格、注释完整性）
   - 逻辑正确性（边界条件、空值处理、循环终止条件）
   - 常见反模式（重复代码、过深嵌套、魔法数字）
3. **问题分级**：
   - **[阻断]**：可能导致运行时错误或明显逻辑错误
   - **[建议]**：可读性/可维护性改进点
   - **[可选]**：风格偏好或微优化
4. **生成报告**：按输出规范整理结果。

### 输出规范

```markdown
## 审查报告

**文件**：<文件名或标识>
**语言**：<语言类型>
**代码规模**：<行数>

### 问题清单

| 级别 | 行号 | 问题描述 | 修改建议 |
|------|------|----------|----------|
| 阻断 | 12 | 未处理空指针 | 增加 null 判断 |
| 建议 | 45 | 魔法数字 86400 | 提取为常量 |

### 总体评价
<2-3 句总结性评价>
```

## 四、置信度门控

当出现以下情况时，本 Skill **不会**编造结论，而是输出占位符：

- 代码片段不完整（缺少函数头/尾）→ 输出 `[需核实:完整代码]`
- 语言识别不确定 → 输出 `[需核实:编程语言]`
- 依赖外部库/API 但未提供上下文 → 输出 `[需核实:依赖定义]`

**原则**：宁缺毋滥。无法确认的问题不强行列出，避免误导。

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| E001 | 输入为空 | "未检测到代码内容，请提供待审查的代码文本或文件路径。" | 重新输入代码 |
| E002 | 语言无法识别 | "无法确定代码语言，请明确指定（如 Python/Java/Go）。" | 补充语言信息 |
| E003 | 代码片段不完整 | "代码疑似被截断，请提供完整文件内容。" | 检查粘贴内容完整性 |
| E004 | 超出单文件范围 | "检测到多文件引用，本 Skill 仅支持单文件审查。" | 拆分文件逐一审查 |

## 六、FAQ 反模式对照

| 常见坑 | 反模式示例 | 正确做法 |
|--------|-----------|----------|
| 过度承诺 | "我能保证找出所有 bug" | 明确说明仅做静态结构审查，不覆盖运行时行为 |
| 忽略上下文 | 不询问语言直接分析 | 先确认语言和审查重点 |
| 编造行号 | 代码未分行号时随意标注 | 先标注行号或使用代码块定位描述 |
| 一刀切建议 | 所有问题都标"必须修改" | 按阻断/建议/可选分级 |
| 忽略用户重点 | 用户强调安全性却只查风格 | 优先响应用户指定的审查维度 |

## 七、渐进式阅读路径

### 新手快速上手（30 秒）

1. 直接粘贴代码 → 2. 说明语言 → 3. 获取分级问题清单 → 4. 按"阻断"级别优先修改。

### 进阶使用（3 分钟）

1. 阅读"能力边界速查卡"明确预期。
2. 在输入时指定审查重点（如"重点看并发安全"）。
3. 结合"错误码体系"排查输入问题。
4. 对输出中的 `[需核实]` 项补充信息后重新审查。

### 深度应用（10 分钟）

1. 将本 Skill 输出作为自检清单，配合实际运行测试。
2. 对"建议"级别问题建立个人代码规范清单。
3. 定期用同一文件多次审查，验证改进效果。


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
