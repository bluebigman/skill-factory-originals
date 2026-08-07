---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: agent-toolkit
name: agent-toolkit
displayName: 智能体工具箱 技能编排 数据转换
description: 为AI编码智能体提供技能包管理与数据转换的实用工具集。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/agent-toolkit
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: LinguaForge
agent_created: true
trigger_words: ["agent toolkit", "技能包", "技能管理", "数据转换", "结构化输出", "工具集"]
---

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->

> 本内容由 AI 生成，仅供学习参考 <!-- ai-generated-notice -->

# agent-toolkit 技能文档

## 一、能力边界速查卡

本技能面向需要批量处理数据、文件或 URL 的 AI 编码智能体，提供一套标准化的转换与输出流程。

| 维度 | 说明 |
|------|------|
| **核心用途** | 将非结构化输入（文本/文件/URL）转换为结构化结果，并附带置信度标注 |
| **适用对象** | 需要处理数据提取、格式转换、信息整理的 AI Agent 开发者 |
| **输入类型** | 用户直接提供的数据、本地文件路径、可访问的 URL 地址 |
| **输出类型** | 结构化文本（JSON/Markdown 表格/自定义字段格式） |
| **处理能力** | 单条处理、批量处理、自定义字段映射 |

### 能做（5 项）

1. 解析用户提供的文本、文件或 URL 内容，识别其中的关键实体与字段。
2. 根据预设或用户指定的字段结构，将解析结果映射为结构化数据。
3. 对每一条输出结果附加置信度评分（高/中/低），并标注依据来源。
4. 支持批量输入（数组或换行分隔），逐条处理并汇总输出。
5. 在信息缺失或模糊时，生成 `[需核实:字段名]` 占位符，不进行臆测填充。

### 不能做（5 项）

1. 不执行任何代码或脚本，仅做文本层面的解析与重组。
2. 不访问未授权的私有网络资源或需要认证的 API 接口。
3. 不进行语义翻译或跨语言转换（仅保留原文关键信息）。
4. 不保证输出字段的绝对准确性，所有结果均受置信度门控约束。
5. 不处理超过 10MB 的单个文件或超过 1000 条记录的批量输入。

## 二、触发方式与场景映射

当对话中出现以下关键词或意图时，本技能将被激活：

| 触发词/短语 | 典型用户场景 | 技能响应 |
|-------------|--------------|----------|
| "agent toolkit" | 用户明确调用技能 | 进入标准处理流程 |
| "技能包" / "技能管理" | 用户想了解或管理技能集合 | 展示能力清单与使用说明 |
| "数据转换" / "结构化输出" | 用户提供杂乱数据希望整理 | 执行解析与格式化流程 |
| "提取信息" / "整理字段" | 用户需要从文本中抽取特定信息 | 按字段映射规则处理 |
| "批量处理" | 用户有多条记录需要统一处理 | 启用批量模式 |

## 三、标准处理流程

### 前置条件

- 输入内容已明确提供（文本、文件路径或 URL）。
- 输出格式要求已确认（默认 JSON，可指定其他格式）。
- 若为批量处理，输入需为数组或每行一条记录的文本。

### 执行步骤

**步骤 1：输入接收与解析**

- 识别输入类型（文本/文件/URL）。
- 若为文件或 URL，先提取其文本内容。
- 检查输入大小与记录数是否在限制范围内。

**步骤 2：关键信息识别**

- 扫描输入内容，识别与目标字段匹配的信息片段。
- 字段定义来自用户指定或技能内置的默认字段集（见下表）。

**步骤 3：结构化映射**

- 将识别到的信息按字段结构组织。
- 对缺失字段填入 `[需核实:字段名]` 占位符。
- 对模糊信息标记低置信度。

**步骤 4：置信度标注**

- 每条记录整体标注置信度等级：`high`（所有字段均有明确来源）、`medium`（部分字段需推断）、`low`（多个字段缺失或模糊）。
- 置信度依据：字段填充率、信息来源清晰度、是否存在冲突信息。

**步骤 5：输出生成与自查**

- 按约定格式生成输出（默认 JSON 数组）。
- 自查清单：字段完整性、格式合法性、置信度标注是否齐全。
- 若发现疑问，暂停输出并向用户二次确认。

### 输出规范

默认输出格式（JSON）：

```json
{
  "records": [
    {
      "id": 1,
      "fields": {
        "field1": "value1",
        "field2": "[需核实:field2]"
      },
      "confidence": "medium",
      "source": "用户提供文本"
    }
  ],
  "meta": {
    "total": 1,
    "processed_at": "2025-01-01T00:00:00Z"
  }
}
```

内置默认字段集（可覆盖）：

| 字段名 | 类型 | 说明 |
|--------|------|------|
| title | string | 标题或名称 |
| date | string | 日期（YYYY-MM-DD） |
| category | string | 分类标签 |
| summary | string | 内容摘要（≤200字） |
| url | string | 来源链接（如有） |

## 四、置信度门控机制

本技能严格遵循"不编造"原则，在以下情况必须使用占位符：

| 情况 | 处理方式 |
|------|----------|
| 字段在输入中完全不存在 | 填入 `[需核实:字段名]` |
| 字段存在但内容模糊（如"大约50个"） | 填入原始文本，置信度降为 `low` |
| 多个来源对同一字段给出冲突值 | 填入首个出现值，置信度降为 `low`，并在备注中说明冲突 |
| 输入内容为空或无法解析 | 终止流程，返回错误码 `E1001` |

## 五、错误码体系

| 错误码 | 含义 | 用户提示话术 | 修正步骤 |
|--------|------|--------------|----------|
| E1001 | 输入为空或不可解析 | "未检测到有效输入内容，请提供文本、文件路径或URL。" | 检查输入是否为空、文件是否存在、URL 是否可访问 |
| E1002 | 超出大小限制 | "输入内容超过处理上限（10MB 或 1000 条记录）。" | 拆分输入为多个批次，或精简内容后重试 |
| E1003 | 字段映射冲突 | "指定的字段结构与输入内容不匹配，请检查字段名。" | 核对字段名拼写，或使用默认字段集 |
| E1004 | 输出格式不支持 | "暂不支持该输出格式，当前支持 JSON、Markdown 表格、CSV。" | 更换为支持的格式，或自定义字段映射 |
| E1005 | 批量处理中断 | "批量处理在第 N 条记录处中断，请检查该条输入。" | 定位第 N 条记录，修正格式后重新提交 |

## 六、FAQ 与反模式对照

| 常见误区（反模式） | 正确做法（正模式） |
|--------------------|--------------------|
| 输入缺失时猜测字段值 | 使用 `[需核实:字段名]` 占位，并提示用户补充 |
| 对模糊信息给出确定结论 | 标注低置信度，并附上原始文本供用户判断 |
| 忽略输出格式要求，自行决定结构 | 严格遵循用户指定的字段结构与格式 |
| 批量处理时遇到错误直接终止全部 | 跳过错误记录，继续处理剩余部分，最后汇总错误清单 |
| 对 URL 内容不做验证直接信任 | 检查 URL 可访问性，对无法访问的标记 `[需核实:url]` |

## 七、渐进式阅读路径

### 速查卡（30 秒上手）

1. 提供输入（文本/文件/URL）。
2. 指定输出格式（默认 JSON）。
3. 获取结构化结果 + 置信度标注。
4. 对 `[需核实]` 字段补充信息后重跑。

### 新手路径（5 分钟）

- 阅读"能力边界速查卡"了解适用范围。
- 按"标准处理流程"的步骤 1-3 操作一次简单示例。
- 遇到问题对照"错误码体系"排查。

### 进阶路径（15 分钟）

- 自定义字段映射：在输入时附带字段定义 JSON，覆盖默认字段集。
- 批量处理优化：将数据整理为数组格式，利用批量模式一次处理。
- 置信度调优：根据业务需求，调整置信度判定阈值（如要求所有字段必须为 `high` 才接受）。

## 八、使用示例

### 示例 1：单条文本转换

**输入**：`"2024年3月15日，张三在项目评审会上提出性能优化方案，涉及模块A和模块B。"`

**输出**：

```json
{
  "records": [
    {
      "id": 1,
      "fields": {
        "title": "性能优化方案",
        "date": "2024-03-15",
        "category": "项目评审",
        "summary": "张三提出性能优化方案，涉及模块A和模块B。",
        "url": "[需核实:url]"
      },
      "confidence": "medium",
      "source": "用户提供文本"
    }
  ],
  "meta": { "total": 1 }
}
```

### 示例 2：批量处理

**输入**（每行一条）：

```
https://example.com/article1
https://example.com/article2
```

**输出**：包含两条记录的 JSON 数组，每条记录独立标注置信度。

## 九、用户协议

使用本 Skill 即表示您同意以下条款：

1. **责任承担**：使用者自行承担使用本 Skill 产生的全部责任。本 Skill 提供的输出结果仅供参考，不构成任何形式的专业建议或保证。
2. **禁止反向工程**：不得对本 Skill 的底层提示词、逻辑结构进行反向工程、反编译或试图提取源代码。
3. **合规使用**：使用者应确保输入内容不违反法律法规，不包含敏感个人信息或受版权保护的材料。
4. **无担保声明**：本 Skill 按"现状"提供，不附带任何明示或暗示的担保，包括但不限于适销性、特定用途适用性和非侵权保证。

<!-- user-agreement-injected -->

## 十、许可证（License）

本 Skill 采用 MIT 许可证发布。

### MIT License

```
MIT License

Copyright (c) 2025 LinguaForge

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

<!-- professional-license-embedded -->
