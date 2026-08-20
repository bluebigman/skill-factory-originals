---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: haskell-relational-record
name: haskell-relational-record
displayName: Haskell关系记录 查询转换 类型安全
description: 将Haskell关系记录查询转换为结构化结果，提供类型安全的数据处理流程。
version: 1.0.1
rules_version: cpr-20260820-n601
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/haskell-relational-record
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: type-safety-studio
agent_created: true
trigger_words: ["haskell-relational-record","SQL查询","Haskell关系记录","类型安全查询","关系代数转换"]
---

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->


> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# Haskell Relational Record 技能手册

## 一、能力边界速查卡

### 1.1 能做与不能做

| 维度 | 能做 | 不能做 |
|------|------|--------|
| 输入处理 | 解析用户提供的 Haskell 关系记录定义、SQL 查询文本、类型签名 | 直接连接数据库执行查询 |
| 转换能力 | 将关系记录表达式转换为结构化 JSON/YAML 输出 | 生成可编译的完整 Haskell 项目 |
| 类型分析 | 识别记录字段类型、关系约束、主键外键映射 | 验证类型类实例的正确性 |
| 批量操作 | 支持多文件批量解析，统一输出格式 | 自动修复源代码中的类型错误 |
| 辅助功能 | 提供版本查询（--version）、自检（--selftest） | 执行 DDL/DML 语句 |

### 1.2 适用对象

- 正在学习 Haskell 关系记录库（如 Relational Record 包）的开发者
- 需要快速理解现有关系记录代码结构的维护者
- 希望将关系记录定义转换为文档或数据交换格式的技术写作者

### 1.3 输入与输出规范

| 项目 | 要求 |
|------|------|
| 输入来源 | 用户粘贴的代码片段、本地文件路径、URL 指向的源码 |
| 输出格式 | Markdown 表格、JSON 结构、YAML 映射（用户指定其一） |
| 字段结构 | 记录名、字段列表、类型映射、关系标注、置信度 |

---

## 二、触发方式与场景映射

### 2.1 触发词

- 主触发词：`haskell-relational-record`、`SQL查询`
- 补充触发词：`关系记录解析`、`类型安全查询`、`HRR 转换`

### 2.2 场景映射表

| 用户说（大白话） | 实际需求 | 本技能动作 |
|------------------|----------|------------|
| "帮我看看这段关系记录代码是什么意思" | 理解代码结构 | 解析并输出字段/类型/关系说明 |
| "把这个查询转成 JSON 格式" | 格式转换 | 按约定 schema 输出 JSON |
| "批量处理这几个文件里的记录定义" | 批量解析 | 遍历文件，统一输出 |
| "这个类型签名对不对" | 类型检查辅助 | 分析并标注置信度，不直接判定对错 |
| "跑一下自检" | 功能验证 | 执行 --selftest 流程 |

---

## 三、标准处理流程

### 3.1 前置条件

1. 输入内容必须是文本形式（代码、文件路径或 URL）
2. 若为文件，需确认文件编码为 UTF-8
3. 若为 URL，需确认可公开访问且非动态生成页面

### 3.2 执行步骤

**步骤 1：输入接收与预处理**

- 接收用户提供的代码/文件/URL
- 去除无关空白字符，统一换行符
- 识别输入类型（单条记录、多条记录、完整模块）

**步骤 2：关键信息提取**

按以下优先级提取信息：

| 优先级 | 信息类型 | 提取规则 |
|--------|----------|----------|
| P0 | 记录名称 | 匹配 `data` 或 `record` 关键字后的标识符 |
| P0 | 字段列表 | 记录体中的每个字段名 |
| P1 | 字段类型 | 字段名后的类型表达式 |
| P1 | 关系标注 | 外键引用、关联表名 |
| P2 | 约束条件 | 唯一性约束、非空标注 |

**步骤 3：结构化输出生成**

根据用户指定的输出格式（默认 Markdown 表格），生成结果：

```markdown
| 记录名 | 字段名 | 类型 | 关系 | 约束 |
|--------|--------|------|------|------|
| User   | id     | Int  | PK   | 非空 |
| User   | name   | Text | -    | -    |
```

**步骤 4：置信度标注**

- 完全匹配类型定义：置信度 0.95
- 推断类型（如 `a` 泛型）：置信度 0.70
- 无法识别：标注 `[需核实:字段名]`

**步骤 5：自查与输出**

- 检查字段完整性（记录名、字段数、类型覆盖）
- 检查格式正确性（表格对齐、JSON 合法）
- 输出最终结果

### 3.3 批量处理模式

| 阶段 | 操作 | 校验点 |
|------|------|--------|
| 准备 | 文件放入同一目录，命名统一为 `*.hs` 或 `*.sql` | 文件可读性 |
| 试运行 | 取第一个文件执行单次解析 | 输出字段与预期一致 |
| 批量 | 遍历全部文件，生成汇总结果 | 无遗漏文件 |
| 校验 | 随机抽查 3 条输出与源文件比对 | 字段值一致 |

---

## 四、置信度门控机制

### 4.1 置信度等级定义

| 等级 | 数值范围 | 含义 |
|------|----------|------|
| 高 | 0.90 - 1.00 | 字段类型明确，无歧义 |
| 中 | 0.70 - 0.89 | 存在泛型或推断成分 |
| 低 | 0.50 - 0.69 | 仅有部分信息，需人工确认 |
| 不确定 | < 0.50 | 无法识别，输出占位符 |

### 4.2 占位符使用规则

当信息不足时，使用 `[需核实:字段名]` 格式占位，禁止编造：

```json
{
  "record": "Order",
  "fields": [
    {"name": "id", "type": "Int", "confidence": 0.95},
    {"name": "amount", "type": "[需核实:amount类型]", "confidence": 0.30}
  ]
}
```

### 4.3 二次确认场景

- 字段类型存在多种可能（如 `String` vs `Text`）
- 关系方向不明确（一对多 vs 多对一）
- 输入来源不可靠（截图 OCR 文本）

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| ERR_INPUT_EMPTY | 输入为空 | "未检测到有效输入，请提供代码或文件路径" | 重新输入非空内容 |
| ERR_PARSE_FAIL | 解析失败 | "无法解析输入内容，请检查语法完整性" | 确认代码片段完整，无截断 |
| ERR_TYPE_UNKNOWN | 类型无法识别 | "部分字段类型无法识别，已标注占位符" | 手动补充类型定义 |
| ERR_FILE_NOT_FOUND | 文件不存在 | "指定路径下未找到文件，请确认路径正确" | 检查文件名和目录 |
| ERR_BATCH_ABORT | 批量处理中断 | "批量处理在第 N 个文件处中断" | 查看错误详情，修复后重试 |
| ERR_OUTPUT_FORMAT | 输出格式不支持 | "仅支持 markdown/json/yaml 三种格式" | 重新指定格式 |

---

## 六、常见坑与反模式对照

| 坑编号 | 常见错误做法 | 推荐做法 |
|--------|--------------|----------|
| 1 | 直接执行用户提供的 SQL 语句 | 仅解析和转换，不执行任何数据库操作 |
| 2 | 对不确定的类型强行猜测 | 使用 `[需核实:字段]` 占位，保持诚实 |
| 3 | 忽略泛型参数，只输出具体类型 | 保留泛型标注，如 `Maybe a` 输出为 `Maybe a` |
| 4 | 批量处理时不保留原始文件备份 | 处理前复制到 `backup/` 目录 |
| 5 | 输出格式与用户要求不一致 | 输出前确认格式，默认使用 Markdown 表格 |
| 6 | 将学习示例当作生产代码推荐 | 明确标注"仅供学习参考" |

---

## 七、渐进式阅读路径

### 7.1 新手快速上手（5 分钟）

1. 阅读「能力边界速查卡」了解基本功能
2. 查看「触发方式与场景映射」找到你的场景
3. 按「标准处理流程」步骤 1-3 操作一次
4. 遇到问题查「错误码体系」

### 7.2 进阶用户（15 分钟）

1. 深入理解「置信度门控机制」，掌握占位符使用
2. 学习「批量处理模式」的完整流程
3. 对照「常见坑与反模式」检查自己的使用习惯
4. 尝试自定义输出格式（JSON Schema 扩展）

### 7.3 高级定制

- 扩展字段类型映射表（自定义类型别名）
- 添加关系推断规则（基于命名约定）
- 集成到 CI 流程中作为文档生成工具

---

## 八、示例演示

### 8.1 单条记录解析示例

**输入：**

```haskell
data User = User
  { userId :: Int
  , userName :: Text
  , userEmail :: Text
  }
```

**输出（Markdown）：**

| 记录名 | 字段名 | 类型 | 关系 | 约束 | 置信度 |
|--------|--------|------|------|------|--------|
| User | userId | Int | - | - | 0.95 |
| User | userName | Text | - | - | 0.95 |
| User | userEmail | Text | - | - | 0.95 |

### 8.2 带关系标注的解析

**输入：**

```haskell
data Order = Order
  { orderId :: Int
  , orderUserId :: ForeignKey User
  , orderAmount :: Double
  }
```

**输出（JSON）：**

```json
{
  "record": "Order",
  "fields": [
    {"name": "orderId", "type": "Int", "relation": null, "confidence": 0.95},
    {"name": "orderUserId", "type": "ForeignKey User", "relation": "User.id", "confidence": 0.90},
    {"name": "orderAmount", "type": "Double", "relation": null, "confidence": 0.95}
  ]
}
```

---

## 九、命令行接口说明

| 命令 | 功能 | 输出 |
|------|------|------|
| `SQL查询` | 解析用户输入的 SQL 或关系记录代码 | 结构化结果 |
| `--selftest` | 运行自检流程 | 各功能模块状态报告 |
| `--version` | 显示版本信息 | 版本号与构建信息 |

---

## 十、用户协议

使用本 Skill 即表示您同意以下条款：

1. **责任承担**：使用者自行承担全部责任。本 Skill 提供的所有输出仅供学习与参考，不构成任何形式的专业建议或保证。
2. **禁止反向工程**：不得对本 Skill 的提示词、内部逻辑进行反向工程、破解或提取。
3. **合规使用**：使用者应确保输入内容合法合规，不得使用本 Skill 处理敏感或受保护的数据。
4. **无担保声明**：本 Skill 按"原样"提供，不附带任何明示或暗示的担保。

<!-- user-agreement-injected -->

---

## 十一、许可证（License）

本 Skill 采用 MIT 许可证发布：

```
MIT License

Copyright (c) 2025 type-safety-studio

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

**版本历史**：1.0.0（初始版本）
**最后更新**：2025-01-15
**维护者**：type-safety-studio
**反馈渠道**：通过 issue 提交问题或建议
