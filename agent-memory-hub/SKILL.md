---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: agent-memory-hub
name: agent-memory-hub
displayName: 团队记忆 资产归档 知识索引
description: 将对话、文档、代码整理为四类记忆资产，生成团队共享索引。
version: 1.0.1
rules_version: cpr-20260811-n351
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/agent-memory-hub
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 林墨
agent_created: true
trigger_words: ["记忆整理", "知识库构建", "代码图谱", "团队索引", "资产归档", "知识沉淀", "信息归档"]
---

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->


> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# Agent Memory Hub — 团队记忆资产整理与共享索引

## 一、能力边界（一页纸速查卡）

### 1.1 能做什么

| 能力项 | 说明 | 输入示例 | 输出示例 |
|--------|------|----------|----------|
| 对话记忆整理 | 从聊天记录中提取决策、结论、待办 | 会议纪要文本 | 结构化记忆卡片（决策/待办/疑问） |
| 文档知识抽取 | 从文档中抽取概念、术语、流程 | PDF/Word/MD 文本 | 知识条目（定义+出处+关联） |
| 代码结构图谱 | 从代码仓库提取模块、函数、依赖关系 | 代码文件列表或 AST 数据 | 代码图谱 JSON（节点+边） |
| 团队索引生成 | 汇总上述三类资产，生成统一检索索引 | 多份记忆卡片+知识条目+代码图谱 | 索引文件（Markdown/JSON） |
| 资产归档 | 按时间/主题/类型归档，生成目录树 | 一批散乱文件 | 归档目录结构+README 说明 |

### 1.2 不能做什么

- **不执行代码**：只分析代码结构，不运行、不调试、不验证逻辑正确性。
- **不修改原始文件**：所有输出均为新生成的文件，不覆盖源文件。
- **不进行语义理解**：不判断内容"对错"，只做结构化整理和关联。
- **不处理二进制文件**：仅接受文本内容或文本提取结果。
- **不生成最终报告**：只产出结构化资产，报告撰写需由使用者完成。

### 1.3 适用对象

- 需要沉淀团队知识的项目经理、技术负责人
- 需要整理个人笔记/代码库的独立开发者
- 需要建立部门知识库的运营/HR/行政人员
- 需要从历史对话中恢复上下文的 AI Agent 使用者

---

## 二、触发方式

### 2.1 触发词

直接使用以下任一词语即可触发：

- 记忆整理
- 知识库构建
- 代码图谱
- 团队索引
- 资产归档
- 知识沉淀
- 信息归档

### 2.2 场景映射表

| 大白话场景 | 实际需求 | 触发词建议 |
|------------|----------|------------|
| "帮我把这周开会聊的东西理一理" | 从会议记录中提取决策和待办 | 记忆整理 |
| "我们组的知识太散了，想搞个库" | 汇总文档、代码、对话为统一索引 | 知识库构建 |
| "这个项目的代码结构给我画个图" | 提取模块、函数、依赖关系 | 代码图谱 |
| "把散落的文件归归类" | 按规则归档文件并生成目录 | 资产归档 |
| "AI 下次对话别老忘事" | 将历史对话转为可检索记忆 | 记忆整理 |

---

## 三、标准流程

### 3.1 前置条件

| 条件 | 要求 | 检查方式 |
|------|------|----------|
| 输入内容 | 至少提供一种输入（对话文本/文档文本/代码路径） | 参数检查 |
| 文本编码 | UTF-8 或 ASCII | 编码检测 |
| 内容长度 | 单次处理不超过 50,000 字符（超出分批次） | 长度校验 |
| 输出目录 | 可写权限 | 权限检查 |

### 3.2 执行步骤

**步骤 1：输入解析**

读取参数或交互输入，识别输入类型：

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `input_type` | string | 是 | `conversation` / `document` / `code` / `mixed` |
| `content` | string | 条件必填 | 文本内容（input_type 为 conversation/document 时） |
| `code_path` | string | 条件必填 | 代码路径（input_type 为 code 时） |
| `output_dir` | string | 否 | 输出目录，默认 `./memory_hub_output` |
| `tags` | array | 否 | 附加标签，如 `["项目A", "2026Q3"]` |

**步骤 2：内容分类**

按输入类型执行对应处理：

- **对话** → 按发言者/时间戳/主题切分 → 提取决策、待办、疑问、结论
- **文档** → 按章节/段落切分 → 提取定义、流程、术语、引用
- **代码** → 扫描文件 → 提取模块名、函数签名、类定义、依赖引用

**步骤 3：结构化生成**

生成四类资产：

```
memory_hub_output/
├── conversations/          # 对话记忆卡片
│   └── conv_20260811_001.md
├── documents/              # 知识条目
│   └── doc_20260811_001.md
├── code_graph/             # 代码图谱
│   └── code_graph_20260811.json
└── index/                  # 团队索引
    └── INDEX.md
```

**步骤 4：索引合并**

将所有资产条目汇总到 `INDEX.md`，格式：

```markdown
# 团队记忆索引

## 对话记忆
- [2026-08-11 产品评审](conversations/conv_20260811_001.md)
  - 标签: 产品, 评审, 决策

## 知识条目
- [微服务架构定义](documents/doc_20260811_001.md)
  - 标签: 架构, 微服务

## 代码图谱
- [订单服务模块](code_graph/code_graph_20260811.json)
  - 标签: 订单, 服务
```

**步骤 5：输出确认**

输出以下信息：

1. 生成的文件列表（含路径）
2. 各类资产数量统计
3. 索引文件路径
4. 下一步建议（如：补充标签、合并重复条目、导出为其他格式）

### 3.3 输出规范

| 输出项 | 格式 | 说明 |
|--------|------|------|
| 对话记忆卡片 | Markdown | 含元信息（时间、参与者）+ 决策/待办/疑问分节 |
| 知识条目 | Markdown | 含定义、出处、关联条目 |
| 代码图谱 | JSON | 含节点（模块/函数/类）和边（依赖/调用） |
| 团队索引 | Markdown | 含分类目录和链接 |

---

## 四、置信度门控

### 4.1 信息不足处理

当输入信息不足以生成完整条目时，使用占位符 `[需核实:字段名]`，不编造内容。

| 场景 | 占位示例 |
|------|----------|
| 对话中未明确决策结果 | `[需核实:决策结果]` |
| 文档中未给出定义 | `[需核实:术语定义]` |
| 代码中函数无注释 | `[需核实:函数用途]` |
| 无法确定时间 | `[需核实:时间戳]` |

### 4.2 置信度分级

| 级别 | 说明 | 输出方式 |
|------|------|----------|
| 高（≥90%） | 信息完整，来源明确 | 正常输出 |
| 中（70-89%） | 部分信息缺失但可推断 | 输出+标注推断依据 |
| 低（<70%） | 信息不足或矛盾 | 输出占位符+建议补充信息 |

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| `E001` | 输入为空 | "未检测到输入内容，请提供对话文本、文档内容或代码路径。" | 检查输入参数，至少提供一种输入 |
| `E002` | 输入类型无效 | "input_type 仅支持 conversation/document/code/mixed。" | 修正 input_type 参数 |
| `E003` | 内容超长 | "内容超过 50,000 字符限制，请分批处理。" | 将内容拆分为多个批次 |
| `E004` | 代码路径不存在 | "指定的代码路径不存在或不可读。" | 检查路径是否正确，确认权限 |
| `E005` | 输出目录不可写 | "输出目录无写入权限。" | 更换输出目录或修改权限 |
| `E006` | 编码不支持 | "仅支持 UTF-8 或 ASCII 编码。" | 转换编码后重试 |
| `E007` | 解析失败 | "内容解析失败，请检查格式。" | 确认输入为纯文本或有效 JSON |

---

## 六、FAQ 反模式

### 6.1 常见坑

| 坑 | 反模式示例 | 正确做法 |
|----|------------|----------|
| 过度整理 | 把每句话都做成记忆卡片 | 只提取有长期价值的决策、待办、结论 |
| 重复条目 | 同一知识点多次出现未合并 | 生成前先检查索引，合并相似条目 |
| 忽略出处 | 知识条目没有来源链接 | 每条记录必须包含来源（文件/对话ID/时间） |
| 代码图谱过细 | 把每个变量都画成节点 | 只提取模块、函数、类级别的结构 |
| 索引失效 | 文件移动后索引链接断裂 | 使用相对路径，归档后重新生成索引 |

### 6.2 反模式对照

**反模式 1：无脑全收**
- ❌ "把所有聊天记录都转成记忆卡片"
- ✅ "只提取有决策、待办、结论的片段"

**反模式 2：无源引用**
- ❌ "这个功能是上周讨论的"（无出处）
- ✅ "这个功能是 2026-08-05 产品评审会确定的（来源：conv_20260805_002.md）"

**反模式 3：结构失衡**
- ❌ 只整理对话，忽略文档和代码
- ✅ 三类资产按比例整理，保持索引完整

---

## 七、渐进式披露

### 7.1 速查卡（30 秒上手）

```
输入 → 分类 → 结构化 → 索引 → 输出
```

- 对话 → 决策/待办/疑问
- 文档 → 定义/流程/术语
- 代码 → 模块/函数/依赖
- 全部 → INDEX.md

### 7.2 新手路径（首次使用）

1. 准备一份会议纪要文本（或直接粘贴对话）
2. 输入：`记忆整理` + 粘贴内容
3. 查看输出的 `conversations/` 目录下的记忆卡片
4. 打开 `index/INDEX.md` 查看汇总

### 7.3 进阶路径（团队使用）

1. 准备多种输入（对话+文档+代码）
2. 使用 `mixed` 类型一次性处理
3. 自定义 `tags` 参数添加团队标签
4. 定期归档，更新索引
5. 将索引文件接入团队 Wiki 或知识库系统

### 7.4 参数速查

| 参数 | 默认值 | 推荐值 |
|------|--------|--------|
| `output_dir` | `./memory_hub_output` | 团队共享目录 |
| `tags` | `[]` | 项目名+季度 |
| 单批处理量 | 50,000 字符 | 10,000-20,000 字符（更稳定） |

---

## 八、用户协议

使用本 Skill 即表示您同意以下条款：

1. **责任承担**：使用者自行承担使用本 Skill 产生的一切后果。本 Skill 仅提供信息整理与结构化建议，不构成任何形式的决策依据或专业意见。
2. **禁止反向工程**：不得对本 Skill 的提示词、处理逻辑、内部参数进行反向工程、破解、提取或用于商业竞争。
3. **内容合规**：使用者需确保输入内容不违反法律法规，不包含敏感信息。本 Skill 不承担内容审核义务。
4. **无担保声明**：本 Skill 按"原样"提供，不附带任何明示或暗示的担保，包括但不限于适销性、特定用途适用性。
5. **免责范围**：因使用本 Skill 导致的数据丢失、业务中断、决策失误等损失，Skill 作者及贡献者不承担任何责任。

<!-- user-agreement-injected -->

---

## 九、许可证（License）

本 Skill 采用 MIT 许可证：

```
MIT License

Copyright (c) 2026 林墨

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

---

*本 Skill 由 AI 辅助生成，仅供参考。使用前请阅读相关文档。*
