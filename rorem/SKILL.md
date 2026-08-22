---
slug: rorem
name: rorem
displayName: 测试数据生成 随机造数 批量填充
description: 按需生成随机测试数据，支持结构化输出与批量定制，辅助开发调试。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 数据工坊
agent_created: true
trigger_words: ["rorem", "随机数据", "测试数据生成", "造数", "mock数据", "模拟数据", "假数据填充"]
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# rorem — 随机测试数据生成 Skill

本 Skill 由 AI 辅助生成，仅供参考。使用前请确认输出数据符合你的业务场景与合规要求。

---

## 一、能力边界（一页纸速查卡）

### ✅ 能做什么

| 能力项 | 说明 | 示例 |
|--------|------|------|
| 随机文本生成 | 生成人名、地址、邮箱、手机号、公司名等常见字段 | `rorem --field name --count 5` |
| 结构化输出 | 按 JSON / CSV / SQL 等格式输出 | `rorem --schema user.json --format json` |
| 批量定制 | 指定数量、前缀、长度范围、字符集 | `rorem --count 100 --prefix "TST_"` |
| 规则约束 | 支持正则约束、枚举值、唯一性要求 | `--pattern "^[A-Z]{3}\d{4}$"` |
| 本地文件处理 | 读取模板文件，替换占位符生成数据 | `rorem --template input.txt --out output.txt` |

### ❌ 不能做什么

- 不能生成真实个人数据（身份证、银行卡、真实手机号等）
- 不能保证生成数据的业务语义正确性（如"合法订单号"需自行校验）
- 不能替代数据库备份或生产环境数据
- 不支持跨网络调用外部 API 获取实时数据

### 🎯 适用对象

- 前端开发：联调接口时填充假数据
- 后端开发：单元测试、压力测试数据准备
- 测试工程师：构造边界值、异常值、批量用例
- 产品/设计：原型演示时的占位内容

---

## 二、触发方式与场景映射

| 触发词 | 大白话场景 | 推荐用法 |
|--------|------------|----------|
| `rorem` | "帮我造点假数据" | 直接命令行调用 |
| `随机数据` | "给我随机生成几个用户" | `rorem --field user --count 10` |
| `测试数据生成` | "写测试用例需要数据" | 配合 `--schema` 使用 |
| `造数` | "批量造 1000 条订单" | `rorem --schema order.json --count 1000` |
| `mock数据` | "接口 mock 用" | 输出 JSON 格式 |
| `模拟数据` | "演示环境填充" | 配合 `--prefix` 定制 |
| `假数据填充` | "表单自动填一下" | 使用 `--template` 模式 |

---

## 三、标准流程

### 前置条件

1. 已安装 rorem 命令行工具（`rorem --version` 可验证）
2. 如需模板替换，确认模板文件与 rorem 在同一目录
3. 明确输出格式（JSON / CSV / SQL / 纯文本）

### 执行步骤

1. **确认字段需求**  
   列出需要的字段名与类型，例如：`name, email, phone, created_at`

2. **单条试运行**  
   ```bash
   rorem --field name --count 1
   ```
   检查输出格式是否符合预期。

3. **批量执行**  
   ```bash
   rorem --schema user.json --count 100 --format json --out users.json
   ```

4. **校验结果**  
   抽查 5-10 条数据，确认字段完整、格式正确、无重复（如需要唯一性）。

### 输出规范

| 格式 | 说明 | 示例 |
|------|------|------|
| `json` | 数组或对象，适合接口 mock | `[{"name":"张三","age":28}]` |
| `csv` | 逗号分隔，适合导入表格 | `name,age\n张三,28` |
| `sql` | INSERT 语句，适合数据库测试 | `INSERT INTO users (name) VALUES ('张三');` |
| `text` | 纯文本，适合模板替换 | `TST_001` |

---

## 四、置信度门控

当以下信息不明确时，rorem 会输出 `[需核实:字段名]` 占位符，**不会编造**：

| 场景 | 输出示例 |
|------|----------|
| 字段类型未知 | `[需核实:type]` |
| 枚举值未提供 | `[需核实:enum_values]` |
| 正则约束缺失 | `[需核实:pattern]` |
| 唯一性要求未声明 | `[需核实:unique]` |

> 使用建议：若输出中出现 `[需核实:...]`，请补充对应参数后重新执行。

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| `E001` | 参数缺失 | "缺少必要参数 --field 或 --schema" | 添加 `--field name` 或 `--schema file.json` |
| `E002` | 模板文件不存在 | "找不到模板文件：xxx" | 检查文件路径与文件名 |
| `E003` | 格式不支持 | "不支持的输出格式：xxx" | 使用 `json/csv/sql/text` 之一 |
| `E004` | 数量超限 | "请求数量超出上限（最大 10000）" | 减少 `--count` 值 |
| `E005` | 正则不合法 | "正则表达式解析失败" | 检查 `--pattern` 语法 |
| `E006` | 唯一性冲突 | "无法在约束下生成足够唯一值" | 扩大字符集或减少数量 |

---

## 六、FAQ 反模式对照

| 常见坑 | 反模式示例 | 正确做法 |
|--------|------------|----------|
| 忽略字段类型 | `--field age` 生成字母 | 明确类型：`--field age --type int` |
| 不校验唯一性 | 批量生成 100 条，出现重复 ID | 添加 `--unique` 参数 |
| 模板路径错误 | 模板在子目录，直接写文件名 | 使用相对路径 `./templates/input.txt` |
| 输出覆盖原文件 | 直接 `--out input.txt` 覆盖模板 | 先备份原文件，或输出到新文件 |
| 忽略边界值 | 只生成正常数据，不测空值/超长 | 使用 `--include-null --max-length 100` |

---

## 七、渐进式披露

### 🟢 新手路径（5 分钟上手）

1. 运行 `rorem --field name --count 3` 看效果
2. 尝试 `--format json` 切换输出
3. 用 `--template` 替换一个文本文件中的占位符

### 🟡 进阶路径（30 分钟精通）

1. 编写 schema 文件（JSON 格式定义字段与约束）
2. 使用 `--pattern` 自定义正则规则
3. 结合 `--unique` 与 `--count` 生成大规模测试集
4. 用 `--out` 输出到文件，配合脚本自动化

---

## 八、参数速查表

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `--field` | string | 无 | 字段名（如 name, email） |
| `--schema` | file | 无 | 字段定义文件（JSON） |
| `--count` | int | 1 | 生成条数（1-10000） |
| `--format` | string | text | 输出格式：json/csv/sql/text |
| `--prefix` | string | 空 | 生成值前缀 |
| `--pattern` | string | 空 | 正则约束 |
| `--unique` | bool | false | 是否要求唯一值 |
| `--out` | file | 标准输出 | 输出文件路径 |
| `--template` | file | 无 | 模板文件路径 |
| `--type` | string | string | 字段类型：string/int/float/bool/date |
| `--min` / `--max` | int | 0/100 | 数值范围 |
| `--include-null` | bool | false | 是否包含空值 |
| `--selftest` | flag | - | 自检安装 |
| `--version` | flag | - | 查看版本 |

---

## 九、用户协议

<!-- user-agreement-injected -->

使用本 Skill 即表示您同意以下条款：

1. **责任承担**：使用者自行承担因使用本 Skill 产生的全部责任，包括但不限于数据准确性、合规性、安全性等。
2. **禁止反向工程**：不得对本 Skill 进行反向工程、反编译、破解或试图提取源代码。
3. **合法用途**：本 Skill 仅用于合法的开发、测试、学习目的，禁止用于生成欺诈、侵权或违法内容。
4. **无担保**：本 Skill 按"现状"提供，不附带任何明示或暗示的担保。
5. **修改与分发**：允许修改与再分发，但需保留原始版权声明。

---

## 十、许可证（License）

<!-- professional-license-embedded -->

### MIT License

Copyright (c) 2024 数据工坊

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

*文档版本：1.0.0 | 最后更新：2024年*
