---
slug: tasks
name: tasks
displayName: 数据转换 批量处理 结构化输出
description: 将各类数据源转换为结构化结果，支持批量处理与自定义格式输出。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 林墨
agent_created: true
trigger_words: ["tasks", "任务处理", "数据转换", "批量处理", "结构化输出", "数据清洗", "格式转换"]
---

> 本内容由 AI 生成，仅供学习参考 <!-- ai-generated-notice -->

# tasks — 数据转换与批量处理 Skill 文档

## 一、能力边界（一页纸速查卡）

### 1.1 能做什么

| 能力项 | 说明 | 示例 |
|--------|------|------|
| 数据源读取 | 支持 CSV、JSON、TXT、Markdown 表格等常见文本格式 | 读取 `orders.csv` 或 `log.json` |
| 字段映射 | 将源数据字段重命名、筛选、排序 | 将 `user_name` 映射为 `username` |
| 格式转换 | 在不同结构化格式之间互转 | CSV → JSON，JSON → Markdown 表格 |
| 批量处理 | 对同一目录下多个文件执行相同转换逻辑 | 将 `./data/*.csv` 全部转为 JSON |
| 自定义输出 | 指定输出字段顺序、分隔符、缩进等 | 输出仅含 `id` 和 `status` 两列 |
| 数据校验 | 检查必填字段、类型一致性、重复项 | 检测 `email` 字段是否为空 |

### 1.2 不能做什么

| 限制项 | 说明 |
|--------|------|
| 非文本数据 | 无法直接处理图片、音视频、二进制文件 |
| 语义理解 | 不进行自然语言理解或情感分析 |
| 数据修复 | 不自动补全缺失值或修正错误数据（仅标记） |
| 外部服务调用 | 不联网获取数据，不调用第三方 API |
| 超大文件 | 单文件超过 50MB 时建议拆分后再处理 |

### 1.3 适用对象

- 需要将日志、导出表格等原始数据转为统一格式的开发者
- 需要批量整理多个同类文件的运维或数据分析人员
- 需要将数据接入下游系统（如数据库、可视化工具）的工程师

---

## 二、触发方式

### 2.1 触发词

| 触发词 | 场景 |
|--------|------|
| `tasks` | 直接调用本 Skill 的通用指令 |
| `任务处理` | 中文场景下的通用调用 |
| `数据转换` | 明确需要格式转换时 |
| `批量处理` | 需要处理多个文件时 |
| `结构化输出` | 需要将非结构化数据转为表格/JSON 时 |
| `数据清洗` | 需要筛选、去重、重命名字段时 |
| `格式转换` | 明确指定源格式和目标格式时 |

### 2.2 场景映射表

| 你说的话 | 实际需求 | 本 Skill 的动作 |
|----------|----------|-----------------|
| "帮我把这几个 CSV 合成一个 JSON" | 多文件合并 + 格式转换 | 读取目录下所有 CSV，合并后输出 JSON |
| "这个日志文件太乱了，整理成表格" | 非结构化文本 → 结构化 | 按行解析，提取关键字段，输出 Markdown 表格 |
| "把 user_id 改成 uid，只要前 100 条" | 字段重命名 + 行数限制 | 映射字段并截取前 100 行 |
| "检查一下这些数据里有没有重复的" | 数据校验 | 输出重复项列表及位置 |

---

## 三、标准流程

### 3.1 前置条件

| 条件 | 要求 |
|------|------|
| 输入文件 | 文本格式（CSV/JSON/TXT/MD），编码为 UTF-8 |
| 文件位置 | 所有待处理文件放在同一目录下 |
| 命名规范 | 文件名建议包含类型标识，如 `raw_2024.csv`、`raw_2024.json` |
| 环境 | 无需安装额外依赖，纯命令行执行 |

### 3.2 执行步骤

#### 步骤 1：准备输入

将待处理文件放入同一目录，确认命名规范一致。例如：

```
./data/
  ├── raw_2024-01.csv
  ├── raw_2024-02.csv
  └── raw_2024-03.csv
```

#### 步骤 2：试运行（单样本验证）

先用单个文件执行，核对输出字段与格式是否符合预期。

```bash
tasks --input ./data/raw_2024-01.csv --output ./output/test.json --format json
```

检查输出文件 `test.json` 中的字段名、字段顺序、数据类型。

#### 步骤 3：批量执行

确认无误后，对全量数据执行：

```bash
tasks --input ./data/ --output ./output/ --format json --batch
```

**重要**：执行前备份原始文件：

```bash
cp -r ./data ./data_backup_$(date +%Y%m%d)
```

#### 步骤 4：校验结果

抽查输出条目，核对关键字段与源数据一致：

```bash
tasks --verify --input ./data/raw_2024-01.csv --output ./output/raw_2024-01.json
```

校验规则：
- 输出行数 = 输入行数（除非指定了 `--limit`）
- 关键字段值完全一致（无截断、无乱码）
- 类型正确（数字字段为数字，字符串字段为字符串）

### 3.3 输出规范

| 参数 | 默认值 | 可选值 | 说明 |
|------|--------|--------|------|
| `--format` | `json` | `json`, `csv`, `md`, `txt` | 输出格式 |
| `--output` | `./output/` | 任意路径 | 输出目录或文件路径 |
| `--limit` | 无限制 | 正整数 | 最大输出行数 |
| `--fields` | 全部字段 | 逗号分隔字段名 | 指定输出字段 |
| `--rename` | 无 | `旧名:新名,旧名:新名` | 字段重命名映射 |
| `--delimiter` | `,` | 任意单字符 | CSV 分隔符 |
| `--indent` | `2` | `0-8` | JSON 缩进空格数 |
| `--dedupe` | 关闭 | `--dedupe` | 按指定字段去重 |
| `--verify` | 关闭 | `--verify` | 校验模式 |

---

## 四、置信度门控

当输入数据存在以下情况时，本 Skill **不会**编造或猜测，而是输出占位符 `[需核实:字段名]`：

| 场景 | 处理方式 |
|------|----------|
| 字段值缺失 | 输出 `[需核实:email]` 而非空字符串或默认值 |
| 字段类型不明确 | 输出 `[需核实:age]` 而非猜测为数字或字符串 |
| 编码无法识别 | 输出 `[需核实:encoding]` 并跳过该行 |
| 字段名拼写不一致 | 输出 `[需核实:user_id]` 并提示检查源数据 |

**示例**：

输入 CSV：
```
id,name,email
1,张三,
2,李四,zhangsan@example.com
```

输出 JSON：
```json
[
  {"id": 1, "name": "张三", "email": "[需核实:email]"},
  {"id": 2, "name": "李四", "email": "zhangsan@example.com"}
]
```

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| `E001` | 输入文件不存在 | `未找到输入文件: {path}` | 检查路径是否正确，确认文件已放入指定目录 |
| `E002` | 文件编码不支持 | `文件编码不是 UTF-8: {path}` | 使用 `iconv` 或文本编辑器将文件转为 UTF-8 |
| `E003` | 字段映射冲突 | `字段映射冲突: {field} 被映射到多个目标` | 检查 `--rename` 参数，确保每个源字段只映射一次 |
| `E004` | 输出目录不可写 | `无法写入输出目录: {path}` | 检查目录权限，或更换输出路径 |
| `E005` | 数据格式解析失败 | `第 {line} 行解析失败: {content}` | 检查该行数据是否符合格式要求，修正后重试 |
| `E006` | 字段类型不一致 | `字段 {field} 存在多种类型: {types}` | 在 `--fields` 中排除该字段，或统一源数据格式 |
| `E007` | 批量处理中断 | `批量处理在第 {n} 个文件时中断: {reason}` | 查看错误详情，修复后从第 n+1 个文件继续 |

---

## 六、FAQ 反模式

### 6.1 常见坑

| 坑 | 反模式示例 | 正确做法 |
|----|------------|----------|
| 跳过试运行 | 直接对全量数据执行，结果字段全错 | 先用单个文件试运行，确认输出后再批量 |
| 不备份原始文件 | 批量处理后发现数据被覆盖 | 执行前先 `cp -r` 备份原目录 |
| 忽略编码问题 | 输出出现乱码，但未检查源文件编码 | 先确认源文件为 UTF-8，否则先转码 |
| 字段名随意 | 不同文件字段名不一致，导致合并后数据错乱 | 统一命名规范，或使用 `--rename` 映射 |
| 不校验结果 | 输出行数少于输入行数，但未发现 | 执行后使用 `--verify` 校验行数和关键字段 |

### 6.2 反模式对照表

| 反模式 | 问题 | 替代方案 |
|--------|------|----------|
| "直接跑吧，应该没问题" | 未验证输入格式，可能全错 | 先跑单样本，确认字段映射正确 |
| "输出文件覆盖了也没事" | 原始数据丢失，无法恢复 | 备份原始文件，输出到独立目录 |
| "这个字段空着就空着吧" | 下游系统可能因空值报错 | 用 `[需核实:字段]` 标记，人工确认后补填 |
| "把所有字段都输出" | 输出文件过大，且包含无关字段 | 用 `--fields` 指定必要字段，减小体积 |

---

## 七、渐进式披露

### 7.1 速查卡（30 秒上手）

```
1. 放文件到 ./data/
2. 试运行: tasks --input ./data/xxx.csv --output ./output/test.json
3. 检查 test.json
4. 备份: cp -r ./data ./data_backup
5. 批量: tasks --input ./data/ --output ./output/ --batch
6. 校验: tasks --verify --input ./data/xxx.csv --output ./output/xxx.json
```

### 7.2 分层次阅读路径

#### 新手路径（首次使用）

1. 阅读「一、能力边界」了解能做什么
2. 阅读「三、标准流程」按步骤执行
3. 遇到问题查「五、错误码体系」

#### 进阶路径（熟练使用）

1. 阅读「二、触发方式」了解全部参数
2. 阅读「四、置信度门控」理解占位符机制
3. 阅读「六、FAQ 反模式」避免常见错误
4. 自定义 `--rename`、`--fields`、`--dedupe` 组合使用

---

## 八、用户协议

使用本 Skill 即表示您同意以下条款：

1. **责任承担**：使用者自行承担使用本 Skill 的全部责任。因使用本 Skill 导致的任何数据丢失、业务中断或其他损失，Skill 作者不承担任何责任。
2. **禁止反向工程**：不得对本 Skill 进行反向工程、反编译、破解或试图提取底层算法。
3. **合规使用**：使用者应确保输入数据不违反任何法律法规，不包含敏感个人信息（除非已获得合法授权）。
4. **修改与分发**：允许在保留版权声明的前提下修改和分发本 Skill，但修改后的版本不得使用原作者名义进行宣传。

<!-- user-agreement-injected -->

---

## 九、许可证（License）

MIT License

Copyright (c) 2024 林墨

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

<!-- professional-license-embedded -->

---

*本 Skill 由 AI 辅助生成，仅供参考。使用前请阅读相关文档。*
