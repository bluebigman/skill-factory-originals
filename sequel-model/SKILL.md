---
slug: sequel-model
name: sequel-model
displayName: 数据建模 结构转换 字段映射
description: 将任意数据源转换为结构化结果，支持批量处理与置信度标注。
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
trigger_words: ["sequel model", "数据建模", "结构转换", "字段映射", "结构化输出", "数据清洗", "格式统一"]
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# sequel-model 技能手册

## 一、能力边界（一页纸速查卡）

### 1.1 能做与不能做

| 维度 | ✅ 能做 | ❌ 不能做 |
|------|--------|----------|
| 输入格式 | 标准 CSV、JSON、JSONL、纯文本表格 | 扫描件 OCR、手写笔记、加密文件 |
| 处理规模 | 单文件 ≤ 50MB，单批次 ≤ 10,000 条记录 | 流式无限数据、跨库关联查询 |
| 输出能力 | 统一 Schema 的 JSON/CSV 输出，字段类型自动推断 | 自定义复杂嵌套结构（需预定义模板） |
| 质量保障 | 置信度标注、失败明细追踪、批量校验 | 语义理解、情感分析、主观判断 |
| 扩展性 | 字段别名映射、类型强制转换、空值策略配置 | 自定义脚本注入、外部 API 调用 |

### 1.2 适用对象

- **数据工程师**：需要快速将异构数据源统一为规范格式
- **业务分析师**：需要将导出数据整理为可分析的结构化表格
- **运维人员**：需要批量处理日志文件并提取关键字段

### 1.3 不适用场景

- 需要理解上下文语义的文本处理
- 需要实时流式处理的高吞吐场景
- 输入数据存在严重编码损坏或格式混乱

---

## 二、触发方式

### 2.1 触发词

直接使用以下任一触发词即可激活：

- `sequel model`
- `数据建模`
- `结构转换`
- `字段映射`
- `结构化输出`

### 2.2 场景映射表

| 用户说（大白话） | 实际触发动作 |
|-----------------|-------------|
| "帮我把这些乱七八糟的表格整理成统一格式" | 执行数据建模 + 结构转换 |
| "这个 CSV 的列名对不上，能重新映射一下吗" | 执行字段映射 + 别名配置 |
| "我有 5000 条数据要批量转成标准 JSON" | 执行批量处理 + 结构化输出 |
| "转换完怎么知道哪些数据可能有问题" | 执行置信度标注 + 失败明细追踪 |

---

## 三、标准流程

### 3.1 前置条件

1. **环境准备**：Python 3.8+，安装 `pandas` 和 `jsonschema` 库
2. **文件准备**：所有待处理文件放入同一目录，命名遵循 `[前缀]_[日期].[扩展名]` 规范
3. **Schema 定义**：准备目标结构定义文件（JSON Schema 格式），或使用默认推断模式

### 3.2 执行步骤

#### 步骤 1：初始化配置

```bash
sequel model init --schema schema.json --input-dir ./data --output-dir ./output
```

参数说明：

| 参数 | 必填 | 默认值 | 说明 |
|------|------|--------|------|
| `--schema` | 否 | 自动推断 | 目标 Schema 文件路径 |
| `--input-dir` | 是 | 无 | 输入文件目录 |
| `--output-dir` | 否 | ./output | 输出目录 |
| `--batch-size` | 否 | 1000 | 每批处理记录数 |
| `--confidence` | 否 | true | 是否启用置信度标注 |

#### 步骤 2：试运行（单样本验证）

```bash
sequel model run --sample --input ./data/sample_001.csv
```

检查输出：
- 字段名称是否符合预期
- 类型转换是否正确（如字符串转数字）
- 空值处理策略是否生效

#### 步骤 3：批量执行

```bash
sequel model run --all --backup
```

`--backup` 参数会在执行前自动备份原始文件至 `./backup/[时间戳]/` 目录。

#### 步骤 4：结果校验

```bash
sequel model verify --output ./output --sample-rate 0.1
```

校验规则：
- 随机抽取 10% 输出条目
- 对比源数据关键字段（主键、时间戳、金额）
- 生成校验报告 `verification_report.json`

### 3.3 输出规范

输出文件结构：

```
output/
├── converted_data.json     # 主输出文件
├── failed_records.csv      # 失败记录明细
├── confidence_scores.json  # 置信度评分
└── metadata.json           # 处理元数据（时间戳、版本、参数）
```

每条记录的标准格式：

```json
{
  "id": "rec_0001",
  "data": { ... },
  "confidence": 0.95,
  "warnings": ["字段 age 类型转换：string → integer"]
}
```

---

## 四、置信度门控

### 4.1 置信度评分规则

| 场景 | 置信度 | 处理方式 |
|------|--------|----------|
| 所有字段精确匹配 Schema | 1.0 | 正常输出 |
| 存在字段类型转换 | 0.9 | 输出 + 警告 |
| 存在空值填充 | 0.8 | 输出 + 警告 |
| 字段名模糊匹配（相似度 > 80%） | 0.7 | 输出 + 需人工确认 |
| 字段无法映射 | 0.0 | 标记为失败 |

### 4.2 信息不足处理

当遇到无法确定的信息时：

1. 在输出字段中填入 `[需核实:字段名]` 占位符
2. 在 `warnings` 数组中添加说明
3. 将该记录置信度降至 0.5 以下

**禁止行为**：不得猜测、编造或使用默认值替代缺失信息。

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| `E001` | 输入文件不存在 | "未找到指定文件，请检查路径" | 确认文件路径，检查文件名大小写 |
| `E002` | Schema 格式错误 | "Schema 定义不合法，请检查 JSON 格式" | 使用 `sequel model validate-schema` 校验 |
| `E003` | 字段类型不兼容 | "字段 [field] 无法从 [type1] 转换为 [type2]" | 检查源数据，或调整 Schema 类型定义 |
| `E004` | 批量处理中断 | "处理在第 [n] 条记录时中断" | 查看 `failed_records.csv`，修复后断点续跑 |
| `E005` | 输出目录无权限 | "无法写入输出目录，请检查权限" | 修改目录权限或更换输出路径 |
| `E006` | 数据编码异常 | "检测到非 UTF-8 编码，已跳过该文件" | 使用 `iconv` 转换编码后重试 |

---

## 六、FAQ 反模式

### 6.1 常见坑与反模式对照

| ❌ 反模式 | ✅ 正确做法 | 说明 |
|-----------|------------|------|
| 直接对全量数据执行，不先试运行 | 先用 `--sample` 验证单个样本 | 试运行可发现 80% 的字段映射问题 |
| 忽略置信度标注，全盘接受输出 | 对置信度 < 0.8 的记录进行人工复核 | 低置信度记录往往是数据质量问题的信号 |
| 修改原始文件作为备份 | 使用 `--backup` 自动备份 | 手动修改会破坏原始数据完整性 |
| 遇到错误就重新跑全量 | 使用断点续跑功能 | 全量重跑浪费时间且可能引入新问题 |
| 自定义 Schema 时随意命名 | 遵循 `snake_case` 命名规范 | 规范命名便于后续维护和团队协作 |

### 6.2 进阶建议

- **字段别名映射**：在 Schema 中配置 `aliases` 字段，自动识别常见变体名称
- **自定义校验规则**：通过 `--rules` 参数加载自定义校验脚本
- **增量处理**：使用 `--incremental` 模式，仅处理新增文件

---

## 七、渐进式披露

### 7.1 速查卡（30 秒上手）

```
1. 放文件 → 2. 跑样本 → 3. 查输出 → 4. 跑全量 → 5. 看报告
```

### 7.2 分层次阅读路径

**新手路径**（首次使用）：
1. 阅读「能力边界」了解适用范围
2. 按「标准流程」步骤 1-2 完成首次试运行
3. 使用「错误码体系」排查常见问题

**进阶路径**（熟练用户）：
1. 深入「置信度门控」理解评分机制
2. 自定义 Schema 和别名映射
3. 配置增量处理和自定义校验规则

**专家路径**（深度定制）：
1. 扩展 `--rules` 实现业务逻辑校验
2. 对接 CI/CD 流水线实现自动化
3. 二次开发 CLI 接口集成到内部平台

---

## 八、用户协议

<!-- user-agreement-injected -->

**使用须知**：

1. 本 Skill 按"原样"提供，使用者自行承担全部使用风险和责任。
2. 使用者应对使用本 Skill 处理的数据负全部责任，包括但不限于数据合法性、数据安全性和数据准确性。
3. 禁止对本 Skill 进行反向工程、反编译、反汇编或试图提取源代码。
4. 使用者不得将本 Skill 用于任何违法、侵权或损害他人利益的活动。
5. 因使用本 Skill 产生的任何直接、间接、附带或后果性损失，作者不承担任何责任。
6. 使用本 Skill 即表示您已阅读、理解并同意本协议全部条款。

---

## 九、许可证（License）

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

*本 Skill 由 AI 辅助生成，仅供参考。使用前请阅读相关文档。*
