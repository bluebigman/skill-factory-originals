---
copyright_holder: 原创作者（自持版权）
source_project: original
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
ai_generated: true
license: MIT
slug: awesome-selfhosted
name: awesome-selfhosted
displayName: 未命名工具
description: A list of Free Software network services and web applications which can be hosted on your own servers
version: 1.0.0
author: skill-factory-auto
agent_created: true
trigger_words:
  - "awesome selfhosted"
---

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->

> 📜 **用户协议（User Agreement）**
> 1. 本 Skill 仅供学习与参考用途。使用本 Skill 产生的任何结果，由使用者自行承担全部责任；本 Skill 不提供任何明示或暗示的保证。
> 2. 涉及法律、财务、税务、投资、医疗等专业决策时，请务必咨询持证专业人士。
> 3. 本代码受版权法保护，未经授权复制、反向工程或商业利用将被追究法律责任。
<!-- user-agreement-injected -->


# 未命名工具

> A list of Free Software network services and web applications which can be hosted on your own servers

## 一、能力边界（一页纸速查卡）

**能做（5项核心能力）：**
1. 将 用户提供的数据/文件/URL 转换为结构化结果
2. 识别并保留输入中的关键信息
3. 按约定格式生成输出
4. 对不确定项给出置信度提示
5. 支持批量处理和自定义格式

**不做（3项边界声明）：**
- 不做：不执行超出输入范围的分析
- 不做：不保证绝对准确，低置信度会标注
- 不做：不访问网络或外部服务

> 如果用户的需求超出以上边界，明确告知无法处理并说明原因，不强行执行。

## 二、触发方式（说大白话就能用）

**触发词表（6类场景）：**
| awesome selfhosted | 通用场景 |

**大白话触发示例（用户原话 → 触发动作）：**
| 用户可能会说 | 触发动作 |
|---|---|
| 帮我处理一下这个 | 启动 未命名工具，进入标准流程 |
| 把这个转成另一种格式 | 启动 未命名工具，进入标准流程 |
| 批量弄一下这些 | 启动 未命名工具，进入标准流程 |

## 三、标准流程（5分钟上手路径）

### Step 1: 收集最小信息集
向用户确认以下关键信息（缺失则引导补采，不臆测）：
- 输入来源：用户提供的数据/文件/URL
- 输出格式要求（文件类型 / 字段结构）
- 期望的完整度（快速骨架 / 详细成品）

### Step 2: 执行核心流程
1. 解析输入内容，识别关键信息
2. 按以下规则处理：
   - 识别输入中的关键字段并结构化
   - 按默认模板组织输出
   - 对不确定项标注并请求确认
3. 生成结果，并标注置信度：
   - 置信度 ≥90%：直接输出
   - 85%-90%：标注"建议复核"
   - <85%：标注"[需核实]"，并说明不确定点

### Step 3: 输出与校验
1. 将结果整理为约定格式输出
2. 自查：字段完整性、格式正确性、置信度标注
3. 有疑问时向用户二次确认

## 四、异常处理（错误码体系）

| 错误码 | 场景 | 标准化话术 |
|---|---|---|
| E001 | 输入为空 | "请提供待处理的内容，格式为：用户提供的数据/文件/URL" |
| E002 | 关键信息缺失 | "还缺少以下信息，请补充：..."（逐项追问） |
| E003 | 输入格式错误 | "输入格式不符合要求，示例：..." |
| E004 | 超出能力边界 | "这超出了本工具的能力范围，建议..." |
| E005 | 置信度过低 | "结果无法确定，建议：..." |

## 五、常见问题（FAQ 速查）

- Q1: 处理速度如何？ → 骨架结果 1 分钟内，详细结果视输入量而定
- Q2: 会不会出错？ → 低置信度内容会标注 [需核实]，请人工复核关键结果
- Q3: 支持哪些输入？ → 用户提供的数据/文件/URL

## 六、进阶用法（深度按需）

- 批量处理：连续提供多个输入，按同一规则逐项处理
- 自定义输出：说明期望的格式/字段，按需生成
- 与其它工具组合：可串联其他 Skill 形成工作流

## 许可证（License）

```text
MIT License

Copyright (c) 2026 原创作者（自持版权）

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
```
<!-- professional-license-embedded -->
