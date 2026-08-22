---
slug: schemr
name: schemr
displayName: 数据建模 结构转换 字段映射
description: 将任意数据源转换为结构化Schema文档的领域专用语言工具
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: SchemaForge
agent_created: true
trigger_words: ["schemr", "schema生成", "结构转换", "数据建模", "字段映射", "数据源转Schema", "结构定义"]
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# schemr — 数据源转 Schema 结构定义工具

## 一、能力边界（一页纸速查卡）

### 能做什么

| 能力项 | 说明 | 适用场景 |
|--------|------|----------|
| 数据源读取 | 从 JSON、CSV、YAML、XML 等常见格式读取数据 | 接口返回、配置文件、日志导出 |
| Schema 生成 | 自动推断字段类型、嵌套层级、数组结构 | 新项目数据建模、接口文档编写 |
| 结构转换 | 将非规范化数据整理为规范 Schema | 多系统数据对齐、数据仓库建模 |
| 字段映射 | 支持字段重命名、类型强转、默认值设定 | 新旧系统迁移、多源数据合并 |
| 批量处理 | 对同目录下多个文件统一执行转换 | 批量日志分析、多环境配置管理 |

### 不能做什么

- 不能自动理解业务语义（如"这个字段代表用户ID"需要人工确认）
- 不能处理加密或二进制格式的数据源
- 不能保证推断出的类型 100% 准确（复杂嵌套需人工复核）
- 不能自动修复源数据中的缺失值或格式错误
- 不支持流式数据或实时数据管道接入

### 适用对象

- 后端开发工程师：快速生成接口文档的数据结构
- 数据工程师：多源数据入仓前的结构统一
- 产品经理：梳理业务对象字段清单
- 测试工程师：构造测试数据的结构模板

---

## 二、触发方式

### 触发词

- 主触发词：`schemr`、`schema生成`、`结构转换`、`数据建模`、`字段映射`
- 补充触发词：`数据源转Schema`、`结构定义`、`字段结构提取`

### 场景映射表

| 你说的话（大白话） | 实际触发动作 |
|-------------------|-------------|
| "帮我把这个 JSON 转成结构文档" | 读取 JSON → 生成 Schema 文档 |
| "这几个 CSV 文件字段对不上，统一一下" | 多文件读取 → 字段映射 → 输出统一 Schema |
| "新项目要建数据模型，先看看接口返回什么" | 读取接口样本 → 推断类型 → 生成建模文档 |
| "把测试数据的结构整理出来" | 批量读取 → 去重合并 → 输出标准 Schema |

---

## 三、标准流程

### 前置条件

1. 待处理文件已放入当前工作目录
2. 文件命名符合规范（见下表）
3. 已确认源数据格式（JSON/CSV/YAML/XML）
4. 已明确输出 Schema 的目标格式（JSON Schema / TypeScript 接口 / Markdown 表格）

**命名规范参考：**

| 数据类型 | 推荐命名 | 示例 |
|----------|----------|------|
| 单一样本 | `sample.<ext>` | `sample.json` |
| 批量数据 | `data_<序号>.<ext>` | `data_001.csv` |
| 映射配置 | `mapping.<ext>` | `mapping.yaml` |

### 执行步骤

**第一步：准备输入**

- 将待处理文件放入同一目录
- 确认命名规范一致（建议使用 `sample` 或 `data_` 前缀）
- 检查文件编码（推荐 UTF-8）

**第二步：试运行**

- 先用单个样本文件执行转换
- 核对输出字段名、类型、嵌套层级是否符合预期
- 如有偏差，调整映射配置后重新执行

**第三步：批量执行**

- 确认试运行结果无误后，对全量数据执行
- 保留原始文件备份（建议复制到 `backup/` 子目录）
- 执行过程中如遇错误，记录错误码并定位问题文件

**第四步：校验结果**

- 抽查输出条目（建议抽取 10%-20%）
- 核对关键字段与源数据一致性
- 确认数组长度、嵌套深度、枚举值范围正确

### 输出规范

输出 Schema 文档需包含：

1. **元信息**：数据源名称、生成时间、版本号
2. **字段定义**：字段名、类型、是否必填、默认值、描述
3. **嵌套结构**：对象嵌套层级、数组元素类型
4. **约束条件**：枚举值、范围限制、格式要求（如日期格式）

**输出示例（JSON Schema 格式）：**

```json
{
  "title": "UserProfile",
  "type": "object",
  "properties": {
    "userId": { "type": "integer", "required": true },
    "userName": { "type": "string", "maxLength": 50 },
    "email": { "type": "string", "format": "email" },
    "tags": { "type": "array", "items": { "type": "string" } }
  }
}
```

---

## 四、置信度门控

当遇到以下情况时，**不得编造字段值或类型**，必须输出占位符 `[需核实:字段名]`：

| 情况 | 处理方式 |
|------|----------|
| 字段值缺失但类型可推断 | 输出类型，值标记为 `[需核实:字段名]` |
| 字段类型不明确（如混合类型） | 输出 `any` 类型，并标记 `[需核实:字段名]` |
| 嵌套层级不确定 | 输出当前层级，标记 `[需核实:嵌套深度]` |
| 枚举值范围不完整 | 输出已知枚举值，标记 `[需核实:枚举范围]` |

**示例：**

```json
{
  "status": {
    "type": "string",
    "enum": ["active", "inactive"],
    "description": "用户状态",
    "note": "[需核实:枚举范围] 可能存在其他状态值"
  }
}
```

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| `E001` | 文件不存在 | "未找到指定文件，请检查文件名和路径" | 1. 确认文件已放入目录 2. 检查文件名拼写 3. 检查路径层级 |
| `E002` | 文件格式不支持 | "当前格式不在支持范围内（JSON/CSV/YAML/XML）" | 1. 转换源文件格式 2. 使用支持的格式重新导出 |
| `E003` | 字段类型冲突 | "同一字段在不同样本中类型不一致" | 1. 查看冲突样本 2. 手动指定目标类型 3. 或标记为 `any` |
| `E004` | 嵌套层级过深 | "嵌套层级超过最大限制（默认10层）" | 1. 简化源数据结构 2. 或调整最大层级配置 |
| `E005` | 编码错误 | "文件编码不是 UTF-8，可能存在乱码" | 1. 转换文件编码为 UTF-8 2. 重新执行 |
| `E006` | 映射配置无效 | "映射配置中存在未知字段或格式错误" | 1. 检查映射配置语法 2. 确认字段名与源数据一致 |

---

## 六、FAQ 反模式

### 常见坑 1：跳过试运行直接批量执行

**反模式**：拿到数据直接全量执行，结果字段类型推断错误，返工成本高。

**正确做法**：先用单个样本试运行，确认输出符合预期后再批量执行。试运行成本低，能避免大面积返工。

### 常见坑 2：忽略原始文件备份

**反模式**：批量执行后源文件被覆盖，发现结果有误无法回退。

**正确做法**：执行前将原始文件复制到 `backup/` 目录，保留恢复能力。

### 常见坑 3：混合类型字段直接指定为 string

**反模式**：遇到数字和字符串混合的字段，直接指定为 string，导致后续数据处理出错。

**正确做法**：标记为 `[需核实:字段名]`，人工确认后决定类型，或使用 `any` 类型。

### 常见坑 4：嵌套结构未校验深度

**反模式**：源数据嵌套 15 层，输出 Schema 后下游系统解析失败。

**正确做法**：执行前检查嵌套深度，超过 10 层时简化结构或调整配置。

### 常见坑 5：枚举值只取样本中的值

**反模式**：样本中只出现 3 个枚举值，就认为枚举范围只有 3 个，导致线上数据校验失败。

**正确做法**：枚举值标记 `[需核实:枚举范围]`，结合业务文档或全量数据确认。

---

## 七、渐进式披露

### 速查卡（30 秒上手）

```
1. 放文件 → 2. 跑样本 → 3. 看输出 → 4. 批量跑 → 5. 抽查校验
```

### 新手路径（首次使用）

1. 阅读「能力边界」了解工具范围
2. 按「标准流程」执行一次完整流程
3. 遇到问题查「错误码体系」
4. 参考「FAQ 反模式」避免常见坑

### 进阶路径（熟练使用）

1. 自定义映射配置（字段重命名、类型强转）
2. 批量处理多目录文件
3. 结合 CI/CD 流程自动化 Schema 生成
4. 编写自定义校验规则（如正则表达式约束）

---

## 八、用户协议

<!-- user-agreement-injected -->

**使用须知：**

1. 本 Skill 提供的所有功能、代码示例和操作指导仅供参考，使用者应自行评估其适用性。
2. 使用者因使用本 Skill 产生的任何直接或间接损失，包括但不限于数据丢失、业务中断、系统故障，由使用者自行承担全部责任。
3. 本 Skill 不提供任何形式的明示或暗示担保，包括但不限于适销性、特定用途适用性和非侵权保证。
4. 禁止对本 Skill 进行反向工程、反编译、反汇编或试图提取源代码（除非适用法律允许）。
5. 使用者应遵守所在国家/地区的法律法规，不得将本 Skill 用于任何非法目的。
6. 本 Skill 的维护者保留随时修改、更新或停止提供本 Skill 的权利，恕不另行通知。

---

## 九、许可证（License）

<!-- professional-license-embedded -->

**MIT License**

Copyright (c) 2024 SchemaForge

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

---

*本文档由 AI 辅助生成，仅供参考。使用前请结合具体业务场景验证功能适配性。*
