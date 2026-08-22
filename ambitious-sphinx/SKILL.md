---
slug: ambitious-sphinx
name: ambitious-sphinx
displayName: 数据整形 批量转换 结构化输出
description: 将任意文本数据转换为结构化结果，支持批量处理与自定义格式映射。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: LinguaForge
agent_created: true
trigger_words: ["数据转换", "结构化处理", "批量解析", "格式转换", "数据整形", "数据映射", "字段提取", "记录清洗"]
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# ambitious-sphinx — 数据整形与结构化输出 Skill

## 一、能力边界（一页纸速查卡）

### 1.1 能做什么

| 能力项 | 说明 | 示例 |
|--------|------|------|
| 文本转结构化 | 将 UTF-8 编码的纯文本/CSV/日志等转换为 JSON、YAML 或自定义格式 | 将 `"name:张三,age:30"` 转为 `{"name":"张三","age":30}` |
| 批量记录解析 | 一次性处理多条记录，支持按行或按分隔符切分 | 处理 10 万行日志，提取时间戳与级别 |
| 字段映射与重命名 | 通过 `--map` 参数将源字段映射为目标字段 | `--map "姓名->name,年龄->age"` |
| 字段筛选 | 通过 `--select` 仅保留指定字段 | `--select name,age` |
| 字段计算 | 通过 `--compute` 对字段做简单运算（拼接、数值运算） | `--compute "fullname=姓+名"` |
| 自定义模板输出 | 通过 JSON 模板文件实现嵌套结构展开 | 将扁平字段展开为 `{"user":{"name":"..."}}` |
| 批量大小控制 | 通过 `--batch-size` 控制每批处理记录数，适配大文件 | `--batch-size 1000` |
| 演示模式 | 通过 `--demo` 运行内置示例，快速了解输出格式 | `--demo` |
| 自检与版本 | `--selftest` 检查环境依赖，`--version` 显示版本号 | `--selftest` |

### 1.2 不能做什么

| 限制项 | 说明 |
|--------|------|
| 非 UTF-8 编码 | 不支持 GBK、UTF-16 等编码，需先转码 |
| 二进制数据 | 不支持图片、音频、压缩包等非文本输入 |
| 语义理解 | 不进行情感分析、意图识别、实体消歧等 NLP 操作 |
| 自动纠错 | 不自动修正拼写错误或格式错误，需通过 `--map` 显式指定 |
| 占位符静默处理 | 占位符（如 `{{unknown}}`）不会被自动替换，需用户明确确认 |
| 流式处理 | 不支持实时流式输入，需一次性提供完整数据 |

### 1.3 适用对象

- 需要将日志、CSV、配置文件等文本批量转为结构化数据的开发者
- 需要统一多源数据格式的数据工程师
- 需要快速验证数据转换逻辑的原型设计者

---

## 二、触发方式

### 2.1 触发词

当对话中出现以下关键词时，本 Skill 将被激活：

- **核心触发词**：数据转换、结构化处理、批量解析、格式转换、数据整形
- **补充触发词**：数据映射、字段提取、记录清洗、文本转JSON

### 2.2 场景映射表

| 用户说（大白话） | 实际需求 | 推荐命令 |
|------------------|----------|----------|
| "帮我把这个 CSV 转成 JSON" | CSV 转 JSON 结构 | `--input data.csv --output-format json` |
| "这堆日志里我只想要时间和错误级别" | 字段筛选 | `--select timestamp,level` |
| "把'姓名'这个字段改名叫'name'" | 字段重命名 | `--map "姓名->name"` |
| "我有 5 万条数据，会不会卡死？" | 大文件批量处理 | `--batch-size 1000` |
| "有些行缺字段，能跳过吗？" | 缺失字段处理 | 默认跳过 + 标记，或 `--strict` 中断 |
| "先跑个例子看看输出长啥样" | 快速体验 | `--demo` |

---

## 三、标准流程

### 3.1 前置条件

1. 输入数据为 UTF-8 编码的文本文件或标准输入
2. 已安装 Python 3.8+ 环境（`--selftest` 可自动检测）
3. 明确目标输出格式（JSON/YAML/自定义模板）

### 3.2 执行步骤

**第一步：确认需求匹配**

阅读「能力边界」速查卡，确认你的需求在能力范围内。若涉及占位符处理，请提前确认策略（默认标记跳过，`--strict` 则中断）。

**第二步：运行演示（可选但推荐）**

```bash
ambitious-sphinx --demo
```

观察默认输出格式，确认符合预期后再处理真实数据。

**第三步：传入数据并逐步添加参数**

```bash
# 基础转换
ambitious-sphinx --input data.txt --output-format json

# 添加字段映射
ambitious-sphinx --input data.txt --output-format json --map "姓名->name,年龄->age"

# 添加字段筛选
ambitious-sphinx --input data.txt --output-format json --map "姓名->name" --select name,age

# 添加字段计算
ambitious-sphinx --input data.txt --output-format json --compute "fullname=姓+名"

# 批量处理大文件
ambitious-sphinx --input big_data.txt --output-format json --batch-size 1000
```

**第四步：检查输出**

输出包含两部分：

1. **结构化结果**：按指定格式输出的数据
2. **处理摘要**：包含处理总记录数、成功数、跳过数、耗时等信息

### 3.3 输出规范

| 输出项 | 格式 | 说明 |
|--------|------|------|
| 结构化结果 | JSON/YAML/自定义模板 | 每条记录独立一行（JSON Lines 格式） |
| 处理摘要 | 文本块 | 含 `processed`, `succeeded`, `skipped`, `failed`, `duration_ms` 字段 |

**处理摘要示例：**

```
处理摘要：
- 总记录数: 1000
- 成功: 998
- 跳过(含占位符): 2
- 失败: 0
- 耗时: 123ms
```

---

## 四、置信度门控

当输入数据存在以下情况时，本 Skill 不会编造缺失信息，而是输出 `[需核实:字段名]` 占位符：

| 场景 | 输出行为 |
|------|----------|
| 源数据缺少某字段 | 该字段输出 `[需核实:字段名]`，记录计入"跳过"统计 |
| 字段值格式异常（如日期格式不一致） | 原样保留原始值，并在摘要中标记 `warning` |
| 映射目标字段在源数据中不存在 | 输出 `[需核实:目标字段]`，不自动推断 |
| 批量模式下含占位符的记录 | 单独标记为 `placeholder` 类别，不混入正常结果 |

**示例：**

输入：
```
name:张三,age:30
name:李四
```

输出（默认模式）：
```json
{"name": "张三", "age": 30}
{"name": "李四", "age": "[需核实:age]"}
```

处理摘要：
```
- 总记录数: 2
- 成功: 1
- 跳过(含占位符): 1
- 失败: 0
```

若使用 `--strict` 参数，第二条记录将触发错误并中断处理。

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| `E001` | 输入文件不存在 | `输入文件未找到，请检查路径` | 确认文件路径是否正确，或使用标准输入 |
| `E002` | 编码不支持 | `仅支持 UTF-8 编码，请先转码` | 使用 `iconv` 或文本编辑器转码为 UTF-8 |
| `E003` | 映射字段冲突 | `映射目标字段与已有字段重复` | 检查 `--map` 参数，避免目标字段名冲突 |
| `E004` | 模板文件格式错误 | `模板文件不是合法 JSON` | 使用 `json.tool` 校验模板文件 |
| `E005` | 批量大小非法 | `--batch-size 必须为正整数` | 检查参数值，确保大于 0 |
| `E006` | 严格模式遇占位符 | `严格模式下检测到占位符，处理中断` | 移除 `--strict` 或补充缺失字段 |
| `E007` | 计算表达式错误 | `--compute 表达式无法解析` | 检查表达式语法，确保字段名正确 |
| `E008` | 输出格式不支持 | `不支持的输出格式，可选: json, yaml, template` | 检查 `--output-format` 参数值 |

---

## 六、FAQ 反模式

### 6.1 常见坑与正确做法

| 反模式（错误做法） | 问题 | 正确做法 |
|---------------------|------|----------|
| 直接处理含占位符的数据，期望自动填充 | 占位符不会被静默替换，结果含 `[需核实]` | 先确认占位符策略，或使用 `--strict` 中断 |
| 一次性加载 10GB 文件不设批量大小 | 内存溢出 | 使用 `--batch-size 1000` 分批处理 |
| 映射字段时目标名与源字段名相同 | 映射无效，可能产生冲突 | 检查映射关系，避免自映射 |
| 忽略处理摘要，直接使用输出 | 可能遗漏跳过记录 | 检查摘要中的 `skipped` 计数，确认无意外跳过 |
| 使用 `--select` 但未先 `--map` | 筛选基于源字段名，可能选错 | 先映射再筛选，或直接使用源字段名 |

### 6.2 反模式对照表

| 场景 | 反模式 | 推荐模式 |
|------|--------|----------|
| 字段重命名 | 手动修改输出文件 | 使用 `--map` 参数 |
| 字段筛选 | 输出全部字段再手动删 | 使用 `--select` 参数 |
| 嵌套结构 | 输出扁平 JSON 再二次处理 | 编写模板文件实现嵌套展开 |
| 大文件处理 | 一次性读取全部内容 | 使用 `--batch-size` 分批处理 |
| 格式验证 | 肉眼检查输出 | 使用 `--selftest` 和 `--demo` 先行验证 |

---

## 七、渐进式披露

### 7.1 速查卡（30 秒上手）

```bash
# 最简用法
ambitious-sphinx --input data.txt --output-format json

# 常用组合
ambitious-sphinx --input data.txt --output-format json --map "姓名->name" --select name,age

# 大文件处理
ambitious-sphinx --input big.txt --output-format json --batch-size 1000

# 演示模式
ambitious-sphinx --demo
```

### 7.2 分层次阅读路径

**新手路径（首次使用）：**

1. 阅读「能力边界」确认需求匹配
2. 运行 `--demo` 观察输出格式
3. 用 `--input` 传入自己的数据，逐步添加 `--output-format`、`--map` 参数
4. 检查处理摘要，确认无意外跳过

**进阶路径（熟练用户）：**

1. 掌握「自定义格式」：组合 `--map`、`--select`、`--compute` 实现复杂转换
2. 理解「置信度门控」：处理含缺失字段的数据集，合理设置占位符策略
3. 批量处理：使用 `--batch-size 1000` 分批处理大文件，监控内存占用
4. 自定义模板：编写 JSON 模板文件，实现嵌套字段展开

**专家路径（深度定制）：**

1. 编写复杂模板文件，实现多级嵌套与条件输出
2. 组合 `--compute` 实现字段间运算与拼接
3. 结合外部工具（如 `jq`）对输出结果做二次加工

---

## 八、用户协议

<!-- user-agreement-injected -->

**使用本 Skill 即表示您同意以下条款：**

1. **责任承担**：使用者自行承担因使用本 Skill 产生的全部责任。包括但不限于数据准确性、合规性、以及因输出结果引发的任何直接或间接损失。

2. **禁止反向工程**：使用者不得对本 Skill 进行反向工程、反编译、破解或试图提取底层算法。

3. **合规使用**：使用者应确保输入数据合法合规，不得使用本 Skill 处理违法、侵权或敏感数据。

4. **无担保**：本 Skill 按"原样"提供，不附带任何明示或暗示的担保，包括但不限于适销性、特定用途适用性和非侵权性。

5. **修改与分发**：使用者可基于 MIT 许可证条款修改和分发本 Skill，但需保留原始版权声明。

---

## 九、许可证（License）

<!-- professional-license-embedded -->

**MIT License**

Copyright (c) 2024 原创作者（自持版权）

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

*本 Skill 由 AI 辅助生成，仅供参考。使用前请阅读相关文档。*
