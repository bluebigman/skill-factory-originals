---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: schemr
name: schemr
displayName: 数据建模 结构转换 字段映射
description: 将任意数据源转换为结构化Schema文档的领域专用语言工具
version: 1.0.2
rules_version: cpr-20260819-n551
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/schemr
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: schema-craft-lab
agent_created: true
trigger_words: ["schemr", "schema生成", "结构转换", "数据建模", "字段映射", "schema转换", "结构定义", "字段提取"]
---

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->


> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# schemr — 数据建模与结构转换工具

## 一、能力边界（一页纸速查卡）

### 1.1 能做什么

| 能力项 | 说明 | 适用场景 |
|--------|------|----------|
| **Schema 生成** | 从 CSV、JSON、XML、数据库导出等数据源自动推导字段结构 | 新项目初始化、数据迁移前调研 |
| **结构转换** | 将非标准数据格式（嵌套 JSON、扁平 CSV）转换为目标 Schema 结构 | 多系统数据对接、API 响应规范化 |
| **字段映射** | 支持源字段到目标字段的别名映射、类型转换、默认值填充 | 数据仓库建模、ETL 管道设计 |
| **数据建模** | 输出标准化的 Schema 文档（JSON Schema / DDL / Markdown 表格） | 团队协作、文档沉淀、代码生成 |

### 1.2 不能做什么

| 限制项 | 说明 |
|--------|------|
| **不执行数据清洗** | 不处理缺失值填充、异常值剔除、去重等数据质量操作 |
| **不进行数据存储** | 不连接数据库，不写入任何持久化存储 |
| **不保证语义正确性** | 仅基于结构推导，无法理解业务语义（如"金额"字段是否含税） |
| **不支持流式处理** | 输入必须为完整文件或完整数据集，不支持增量追加 |

### 1.3 适用对象

- 数据工程师：快速评估异构数据源的结构兼容性
- 后端开发者：为 API 请求/响应定义标准 Schema
- 数据分析师：将散乱数据整理为可建模的结构化文档
- 项目经理：在数据迁移前输出结构对比报告

---

## 二、触发方式

### 2.1 触发词

当对话中出现以下关键词时，自动激活本 Skill：

| 触发词 | 同义场景词 |
|--------|------------|
| schemr | schema 生成、结构转换、数据建模、字段映射 |
| schema 生成 | 结构推导、字段提取、格式定义 |
| 结构转换 | 格式重排、结构映射、Schema 对齐 |
| 数据建模 | 数据字典、元数据定义、模型设计 |

### 2.2 场景映射表

| 用户说（大白话） | 实际需求 | 本 Skill 响应 |
|------------------|----------|----------------|
| "帮我把这个 CSV 转成 JSON Schema" | 从 CSV 推导字段类型并输出 JSON Schema | 执行 `schemr --input data.csv --format json-schema` |
| "这两个系统的字段对不上，帮我看看" | 对比两个数据源的结构差异 | 执行 `schemr --compare source_a.json source_b.json` |
| "我要建个数据模型，但不知道从哪开始" | 从现有数据推导建模基础 | 执行 `schemr --input raw_data.json --format ddl` |
| "这个嵌套 JSON 太乱了，帮我理一下" | 扁平化或重组嵌套结构 | 执行 `schemr --input nested.json --flatten` |

---

## 三、标准流程

### 3.1 前置条件

| 条件 | 要求 | 检查方式 |
|------|------|----------|
| 输入文件 | 必须为 UTF-8 编码的文本文件（CSV/JSON/XML） | `file -i input.csv` |
| 文件命名 | 文件名不得包含空格和特殊字符（建议 `snake_case`） | 目视检查 |
| 数据规模 | 单文件 ≤ 100MB，行数 ≤ 500,000 | `wc -l input.csv` |
| 环境依赖 | Python 3.8+，已安装 `schemr` 包 | `schemr --version` |

### 3.2 执行步骤

#### 步骤 1：准备输入

```bash
# 将待处理文件放入同一目录
mkdir -p /tmp/schemr-work
cp /path/to/your/data.csv /tmp/schemr-work/
cd /tmp/schemr-work

# 确认命名规范一致（建议统一为 snake_case）
mv "Sales Data 2024.csv" sales_data_2024.csv
```

#### 步骤 2：试运行（单样本验证）

```bash
# 使用 --sample 参数提取前 100 行进行试运行
schemr --input sales_data_2024.csv --sample 100 --format json-schema

# 输出示例（节选）
{
  "type": "object",
  "properties": {
    "order_id": {"type": "string", "description": "订单编号"},
    "amount": {"type": "number", "description": "订单金额"},
    "created_at": {"type": "string", "format": "date-time"}
  },
  "required": ["order_id", "amount"]
}
```

**核对要点**：
- 字段名是否符合预期（是否被错误拆分或合并）
- 类型推断是否准确（如 `"001"` 被推断为 string 而非 number）
- 必填字段是否合理（`required` 列表）

#### 步骤 3：批量执行

```bash
# 确认无误后对全量数据执行
schemr --input sales_data_2024.csv --format json-schema --output schema.json

# 保留原始文件备份
cp sales_data_2024.csv sales_data_2024.csv.bak
```

#### 步骤 4：校验结果

```bash
# 抽查输出条目（随机抽取 5 条）
schemr --validate schema.json --against sales_data_2024.csv --sample 5

# 校验输出示例
[OK] order_id: string (匹配 5/5)
[OK] amount: number (匹配 5/5)
[WARN] created_at: string (匹配 4/5, 1 条为空值)
```

**校验标准**：
- 字段名匹配率 ≥ 95%
- 类型匹配率 ≥ 90%
- 必填字段覆盖率 = 100%

### 3.3 输出规范

| 输出格式 | 适用场景 | 文件后缀 |
|----------|----------|----------|
| JSON Schema | API 定义、数据验证 | `.schema.json` |
| DDL（SQL 建表语句） | 数据库建模 | `.sql` |
| Markdown 表格 | 文档沉淀、团队评审 | `.md` |
| YAML | 配置管理、CI/CD 集成 | `.yaml` |

---

## 四、置信度门控

### 4.1 信息不足时的处理

当输入数据存在以下情况时，输出中必须使用 `[需核实:字段名]` 占位符，**禁止**编造或猜测：

| 场景 | 处理方式 | 示例 |
|------|----------|------|
| 字段值全部为空 | 标记为 `[需核实:字段名]`，不推断类型 | `"customer_phone": "[需核实:customer_phone]"` |
| 字段值类型混杂 | 标记为 `[需核实:字段名]`，输出最宽松类型 | `"status": "[需核实:status]"`（string 和 number 混杂） |
| 字段名含义不明 | 保留原字段名，添加 `[需核实]` 注释 | `"col_12": "[需核实:col_12 含义]"` |
| 数据量不足以推断 | 输出 `[需核实:字段名]` 并提示增加样本量 | `[需核实:字段名] 样本量不足 10 条，无法推断` |

### 4.2 置信度分级

| 置信度 | 判定标准 | 输出行为 |
|--------|----------|----------|
| 高（≥90%） | 字段类型一致率 ≥ 90%，样本量 ≥ 100 | 正常输出，标注置信度 |
| 中（70%-90%） | 字段类型一致率 70%-90% | 输出类型，附加 `[需核实]` 警告 |
| 低（<70%） | 字段类型一致率 < 70% | 不输出类型，仅输出 `[需核实:字段名]` |

---

## 五、错误码体系

### 5.1 常见错误及处理

| 错误码 | 错误描述 | 提示话术 | 修正步骤 |
|--------|----------|----------|----------|
| `E001` | 输入文件不存在 | `错误: 文件 sales_data.csv 不存在，请检查路径` | 1. 使用 `ls` 确认文件存在<br>2. 检查路径拼写<br>3. 确认文件权限（`chmod +r`） |
| `E002` | 文件编码错误 | `错误: 文件编码不是 UTF-8，请转换后重试` | 1. 使用 `iconv -f GBK -t UTF-8 input.csv > output.csv` 转换<br>2. 或使用 `--encoding` 参数指定编码 |
| `E003` | 数据格式无法解析 | `错误: 无法解析 JSON，第 3 行存在语法错误` | 1. 使用 `jq . input.json` 检查语法<br>2. 修复引号、逗号等语法问题 |
| `E004` | 字段类型冲突 | `警告: 字段 amount 同时存在 string 和 number 类型` | 1. 检查源数据是否混入异常值<br>2. 使用 `--type-force number` 强制类型 |
| `E005` | 输出目录无权限 | `错误: 无法写入 /output/ 目录，权限不足` | 1. 使用 `chmod +w /output/` 添加写权限<br>2. 或更换输出目录 |
| `E006` | 样本量不足 | `警告: 样本量仅 5 条，推断结果可能不准确` | 1. 增加 `--sample` 参数值<br>2. 或移除 `--sample` 参数使用全量数据 |

### 5.2 错误处理原则

- 所有错误信息输出到 `stderr`，正常输出到 `stdout`
- 错误发生时退出码非零（`exit code 1`），便于脚本集成
- 错误信息包含具体行号/字段名，便于定位问题

---

## 六、FAQ 反模式

### 6.1 常见坑

| 坑位 | 错误做法 | 正确做法 |
|------|----------|----------|
| **忽略样本试运行** | 直接对全量数据执行，发现字段映射错误后返工 | 先 `--sample 100` 试运行，确认无误后再全量执行 |
| **覆盖原始文件** | 直接使用 `--output` 覆盖输入文件 | 保留 `.bak` 备份，输出到独立目录 |
| **盲目信任类型推断** | 不校验推断结果，直接用于生产 | 使用 `--validate` 抽查 5-10 条记录 |
| **忽略空值处理** | 空值字段被推断为 `null` 类型 | 空值字段标记为 `[需核实]`，人工确认业务含义 |
| **混用不同编码** | 多个文件使用不同编码（GBK/UTF-8） | 统一转换为 UTF-8 后再处理 |

### 6.2 反模式对照表

| 反模式 | 问题 | 替代方案 |
|--------|------|----------|
| 手动编写 Schema | 耗时且易出错，字段遗漏率高 | 使用 `schemr` 自动推导，人工复核 |
| 一次性处理所有文件 | 错误扩散，难以定位问题 | 单文件试运行 → 批量执行 → 逐文件校验 |
| 忽略字段语义 | 类型正确但业务含义错误 | 输出后人工审核字段描述，补充业务注释 |
| 不保留中间产物 | 后续调整需要重新处理 | 保留原始文件、试运行输出、最终 Schema 三个版本 |

---

## 七、渐进式披露

### 7.1 速查卡（30 秒上手）

```bash
# 最常用命令
schemr --input data.csv --format json-schema          # CSV → JSON Schema
schemr --input data.json --format ddl                 # JSON → SQL 建表语句
schemr --input data.csv --sample 100 --output schema.json  # 试运行

# 常用参数
--input <file>     # 输入文件（必填）
--format <type>    # 输出格式：json-schema / ddl / markdown / yaml
--sample <n>       # 仅处理前 n 行（试运行）
--output <file>    # 输出文件路径
--validate         # 校验输出与源数据一致性
```

### 7.2 新手路径（首次使用）

1. **准备**：将数据文件放入独立目录，确认编码为 UTF-8
2. **试运行**：`schemr --input your_data.csv --sample 100 --format json-schema`
3. **检查**：核对字段名、类型、必填项是否符合预期
4. **全量执行**：`schemr --input your_data.csv --format json-schema --output schema.json`
5. **校验**：`schemr --validate schema.json --against your_data.csv --sample 5`

### 7.3 进阶路径（高级用户）

1. **自定义映射**：使用 `--mapping` 参数指定字段映射规则
   ```bash
   schemr --input source.json --mapping mapping.yaml --format json-schema
   ```
   `mapping.yaml` 示例：
   ```yaml
   mappings:
     - source: "user_name"
       target: "username"
       type: "string"
     - source: "reg_date"
       target: "created_at"
       type: "date-time"
   ```

2. **多文件对比**：使用 `--compare` 参数对比两个数据源结构
   ```bash
   schemr --compare source_a.json source_b.json --output diff_report.md
   ```

3. **批量处理**：使用 `--batch` 参数处理目录下所有文件
   ```bash
   schemr --batch ./data_dir/ --format ddl --output ./schemas/
   ```

4. **自定义类型推断**：使用 `--type-rules` 参数覆盖默认类型推断规则
   ```bash
   schemr --input data.csv --type-rules rules.json --format json-schema
   ```

---

## 八、参数参考表

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `--input` | string | 无（必填） | 输入文件路径 |
| `--format` | string | `json-schema` | 输出格式：`json-schema` / `ddl` / `markdown` / `yaml` |
| `--sample` | int | 全量 | 仅处理前 N 行数据 |
| `--output` | string | 标准输出 | 输出文件路径 |
| `--encoding` | string | `utf-8` | 输入文件编码 |
| `--mapping` | string | 无 | 字段映射规则文件（YAML/JSON） |
| `--compare` | string | 无 | 对比第二个数据源文件 |
| `--batch` | string | 无 | 批量处理目录路径 |
| `--type-rules` | string | 无 | 自定义类型推断规则文件 |
| `--type-force` | string | 无 | 强制字段类型（如 `--type-force amount=number`） |
| `--flatten` | bool | `false` | 扁平化嵌套结构 |
| `--validate` | bool | `false` | 校验输出与源数据一致性 |
| `--against` | string | 无 | 校验时对比的源文件（需配合 `--validate`） |
| `--selftest` | bool | `false` | 运行自检程序 |
| `--version` | bool | `false` | 显示版本信息 |

---

## 九、用户协议

<!-- user-agreement-injected -->

**使用本 Skill 即表示您同意以下条款：**

1. **责任承担**：使用者自行承担因使用本 Skill 产生的全部责任。包括但不限于数据丢失、业务中断、决策失误等直接或间接损失。本 Skill 仅提供结构转换和建模建议，不构成任何形式的数据处理保证。

2. **禁止反向工程**：使用者不得对本 Skill 的底层实现进行反向工程、反编译、破解或试图提取源代码（除非适用法律允许）。不得移除、篡改或遮蔽本 Skill 中的任何版权标识、水印或元数据。

3. **合规使用**：使用者须确保输入数据的合法性，不得使用本 Skill 处理违反法律法规、侵犯第三方权益的数据。因违规使用产生的法律后果由使用者自行承担。

4. **无担保声明**：本 Skill 按"现状"提供，不附带任何明示或暗示的担保，包括但不限于适销性、特定用途适用性和非侵权保证。

---

## 十、许可证（License）

<!-- professional-license-embedded -->

**MIT License**

Copyright (c) 2024 schema-craft-lab

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following
