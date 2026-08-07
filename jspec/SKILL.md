---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: jspec
name: jspec
displayName: 前端测试 行为驱动 断言校验
description: 面向JavaScript行为驱动测试的断言编写与结果解析辅助工具。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/jspec
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 流云工坊
agent_created: true
trigger_words: ["jspec", "BDD测试", "行为驱动开发", "JavaScript测试", "断言库"]
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

# jspec Skill 文档

## 一、能力边界速查卡

### 1.1 能做（核心能力）

| 编号 | 能力项 | 说明 | 输入示例 | 输出示例 |
|------|--------|------|----------|----------|
| C1 | 测试用例结构解析 | 从用户提供的测试代码或描述中提取 describe/it/expect 层级 | `describe('计算器', () => { it('加法', () => { expect(add(1,2)).toBe(3) }) })` | 结构化测试树 |
| C2 | 断言表达式识别 | 识别常见断言方法（toBe/toEqual/toBeTruthy 等）及其参数 | `expect(x).toBeGreaterThan(5)` | 断言类型+参数值 |
| C3 | 测试结果汇总 | 将用户粘贴的测试运行日志解析为通过/失败/跳过统计 | Mocha/Jest 输出文本 | 统计表+失败详情 |
| C4 | 测试用例生成建议 | 根据被测函数签名或描述，生成 BDD 风格的用例骨架 | `function sum(a,b){...}` | 5-8 条用例建议 |
| C5 | 批量文件扫描 | 对指定目录下的 `.test.js` / `.spec.js` 文件进行批量解析 | 目录路径 | 每文件的用例清单 |

### 1.2 不能做（明确边界）

| 编号 | 限制项 | 说明 |
|------|--------|------|
| L1 | 不执行测试代码 | 本 Skill 不负责运行测试，仅做静态解析与文本分析 |
| L2 | 不修改用户源码 | 只输出建议，不直接改动任何源文件 |
| L3 | 不识别非 JavaScript 测试 | 如 Python pytest、Java JUnit 等不在处理范围内 |
| L4 | 不处理混淆代码 | 压缩/混淆后的测试代码无法保证解析准确率 |
| L5 | 不提供通过率保证 | 测试是否通过取决于用户代码逻辑，本 Skill 仅辅助分析 |

### 1.3 适用对象

- 前端开发者：日常编写/维护 Jest、Mocha、Vitest 测试
- 测试工程师：需要快速梳理测试覆盖情况
- 技术管理者：查看测试报告时辅助理解断言含义


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
