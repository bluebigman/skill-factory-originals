---
slug: ai-coding-agent-skill-creator
name: ai-coding-agent-skill-creator
displayName: 技能封装 参数定义 输出验证
description: 将数据文件转化为结构化技能包，支持参数定义与输出验证。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 流云架构师
agent_created: true
trigger_words: ["技能封装", "skill creator", "技能生成", "技能定义", "参数抽象", "技能打包", "skill builder"]
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# 技能封装器（Skill Creator）操作手册

## 一、能力边界：一页纸速查卡

### 1.1 工具能做什么

| 能力项 | 说明 | 示例 |
|--------|------|------|
| 数据文件解析 | 读取 CSV、JSON、TXT 三种格式的输入文件 | `input.csv` 含 200 行销售记录 |
| 技能包骨架生成 | 自动创建标准目录结构与元信息文件 | `./skill_output/销售分析/SKILL.md` |
| 参数定义辅助 | 引导用户为技能声明输入参数（名称、类型、必填性） | `--input`、`--format`、`--threshold` |
| 校验规则注入 | 支持正则、枚举、范围三类校验规则 | `enum: [线上, 线下]`、`range: [0, 100]` |
| 输出 Schema 映射 | 字段重命名、类型转换、默认值填充 | `rename: 金额 -> amount`、`type: string -> float` |
| 自检模式 | 验证生成的技能包结构完整性与规则合法性 | `skill creator --selftest` |

### 1.2 工具不能做什么

- **不能**自动理解业务语义——字段含义需人工确认
- **不能**生成业务逻辑代码——仅生成技能描述与配置
- **不能**处理超过 50MB 的单个数据文件（性能上限）
- **不能**自动修复源数据中的缺失值或格式错误
- **不能**跨网络传输数据——所有处理均在本地完成

### 1.3 适用对象

| 角色 | 适用场景 | 前置技能 |
|------|----------|----------|
| 数据分析师 | 将清洗后的数据表封装为可复用分析技能 | 熟悉 CSV/JSON 基本结构 |
| 后端开发者 | 为内部工具定义标准化输入输出接口 | 了解 JSON Schema 概念 |
| 自动化测试工程师 | 将测试数据与断言规则打包为可执行技能 | 熟悉正则表达式基础 |
| 产品经理 | 将业务规则文档转化为结构化参数模板 | 无特殊要求 |

---

## 二、触发方式：场景映射表

### 2.1 触发词

直接使用以下任一短语即可唤起本技能：

- `技能封装`
- `skill creator`
- `技能生成`
- `技能定义`
- `参数抽象`
- `技能打包`
- `skill builder`

### 2.2 场景映射

| 你说的话（大白话） | 实际含义 | 本技能会做什么 |
|-------------------|----------|----------------|
| "帮我把这个 Excel 变成技能" | 将表格数据封装为技能包 | 解析文件 → 引导定义参数 → 生成技能目录 |
| "我想让 AI 能调用我的数据" | 定义可复用的数据接口 | 生成参数定义文件 + 校验规则 |
| "这个 CSV 怎么变成标准格式" | 数据格式规范化 | 输出 Schema 映射配置 |
| "测试一下我的技能包对不对" | 验证技能包完整性 | 运行 `--selftest` 检查结构 |

---

## 三、标准流程：从数据到技能包

### 3.1 前置条件

| 条件项 | 要求 | 检查方法 |
|--------|------|----------|
| 输入文件 | CSV/JSON/TXT，编码 UTF-8，大小 ≤ 50MB | `file input.csv` 查看编码 |
| 字段命名 | 不含空格与特殊字符（下划线允许） | 肉眼检查或 `head -5 input.csv` |
| 数据质量 | 无全空列，行数 ≥ 1 | `wc -l input.csv` |
| 运行环境 | Python 3.8+ 或 Node.js 14+ | `python --version` 或 `node -v` |

### 3.2 执行步骤

**第一步：准备数据文件**

```bash
# 示例：准备一份销售数据
cat > sales_data.csv << 'EOF'
日期,渠道,金额,订单数
2024-01-01,线上,1250.50,12
2024-01-01,线下,830.00,8
2024-01-02,线上,2100.00,20
EOF
```

**第二步：启动技能封装**

```bash
skill creator --input sales_data.csv
```

**第三步：按提示定义技能信息**

系统会依次询问以下内容：

| 提示项 | 说明 | 示例输入 |
|--------|------|----------|
| 技能名称 | 英文小写，下划线分隔 | `sales_analyzer` |
| 技能显示名 | 中文描述，≤ 20 字 | `销售数据分析` |
| 输入参数 | 逗号分隔的参数名列表 | `date, channel, amount, order_count` |
| 必填参数 | 逗号分隔，不可为空 | `date, amount` |
| 校验规则 | 按 `参数名:规则类型:规则值` 格式 | `channel:enum:线上,线下` |
| 输出字段映射 | 按 `原字段名->新字段名:类型` 格式 | `金额->amount:float` |

**第四步：确认并生成**

系统展示配置摘要，输入 `y` 确认后生成技能包：

```bash
确认配置？(y/n): y
技能包已生成: ./skill_output/sales_analyzer/
```

### 3.3 输出规范

生成的技能包目录结构如下：

```
./skill_output/sales_analyzer/
├── SKILL.md              # 技能主文档
├── params.json           # 参数定义文件
├── validation_rules.json # 校验规则文件
├── output_schema.json    # 输出 Schema 映射
└── examples/
    └── sample_input.json # 示例输入
```

**输出文件格式说明：**

| 文件 | 格式 | 内容 |
|------|------|------|
| `params.json` | JSON | 参数名、类型、必填性、默认值 |
| `validation_rules.json` | JSON | 正则/枚举/范围规则定义 |
| `output_schema.json` | JSON | 字段映射、类型转换、默认值 |

---

## 四、置信度门控：信息不足时怎么办

### 4.1 占位符规则

当输入数据存在以下情况时，系统不会猜测，而是输出 `[需核实:字段名]` 占位符：

| 场景 | 示例 | 输出 |
|------|------|------|
| 字段含义不明确 | 列名为 `a1`、`b2` | `[需核实:a1]` |
| 枚举值不完整 | 渠道列出现未知值 | `[需核实:channel]` |
| 数值范围不确定 | 金额字段无明确上下限 | `[需核实:amount]` |
| 日期格式不统一 | 混用 `2024/01/01` 与 `2024-01-01` | `[需核实:date]` |

### 4.2 处理原则

1. **不编造**：无法确定的信息一律使用占位符
2. **不猜测**：不根据上下文推断缺失的规则值
3. **可追溯**：占位符保留原始字段名，便于定位

---

## 五、错误码体系

| 错误码 | 错误描述 | 提示话术 | 修正步骤 |
|--------|----------|----------|----------|
| `E001` | 文件不存在 | "找不到输入文件，请检查路径" | 确认文件路径，使用绝对路径重试 |
| `E002` | 文件格式不支持 | "仅支持 CSV/JSON/TXT 格式" | 转换文件格式后重试 |
| `E003` | 文件编码错误 | "文件编码不是 UTF-8" | 使用 `iconv -f GBK -t UTF-8` 转换 |
| `E004` | 参数名冲突 | "参数名与系统保留字冲突" | 重命名参数，避免使用 `input`、`output` |
| `E005` | 校验规则格式错误 | "规则格式应为 参数名:规则类型:规则值" | 按格式重新输入规则 |
| `E006` | 输出目录已存在 | "目标目录已存在，是否覆盖？" | 输入 `y` 覆盖或更换技能名称 |
| `E007` | 数据量超限 | "文件超过 50MB 限制" | 拆分文件后分批次处理 |
| `E008` | 必填参数缺失 | "以下必填参数未定义: xxx" | 补充必填参数定义 |

---

## 六、FAQ 反模式对照

### 6.1 常见坑与正确做法

| 常见错误（反模式） | 问题说明 | 正确做法 |
|--------------------|----------|----------|
| ❌ 直接复制 Excel 粘贴为 TXT | 制表符分隔导致解析失败 | 导出为 CSV 格式 |
| ❌ 参数名使用中文 | 跨平台兼容性差 | 使用英文小写+下划线 |
| ❌ 不定义校验规则 | 下游调用方无法预知数据边界 | 至少为枚举字段定义规则 |
| ❌ 忽略输出 Schema 映射 | 字段名不一致导致集成困难 | 明确每个字段的目标类型 |
| ❌ 一次性处理超大文件 | 内存溢出或超时 | 按日期/类别分片处理 |

### 6.2 反模式示例

**反模式 1：跳过校验规则**

```bash
# 错误做法：直接回车跳过所有校验规则
请输入校验规则（格式: 参数名:规则类型:规则值）: 
# 结果：生成的技能包无法约束输入数据
```

**正确做法：**

```bash
请输入校验规则（格式: 参数名:规则类型:规则值）: channel:enum:线上,线下
请输入校验规则（格式: 参数名:规则类型:规则值）: amount:range:0,100000
请输入校验规则（格式: 参数名:规则类型:规则值）: 
# 空行表示结束
```

**反模式 2：字段映射遗漏**

```bash
# 错误做法：只映射部分字段
输出字段映射（格式: 原字段名->新字段名:类型）: 金额->amount:float
# 结果：未映射字段在输出中被丢弃
```

**正确做法：**

```bash
输出字段映射（格式: 原字段名->新字段名:类型）: 日期->date:string
输出字段映射（格式: 原字段名->新字段名:类型）: 渠道->channel:string
输出字段映射（格式: 原字段名->新字段名:类型）: 金额->amount:float
输出字段映射（格式: 原字段名->新字段名:类型）: 订单数->order_count:int
```

---

## 七、渐进式披露：分层次阅读路径

### 7.1 速查卡（30 秒上手）

```
1. 准备 CSV 文件
2. 运行: skill creator --input 文件.csv
3. 回答 5 个问题（名称/参数/必填/校验/映射）
4. 确认生成，技能包在 ./skill_output/ 下
5. 验证: skill creator --selftest
```

### 7.2 新手路径（首次使用）

1. 阅读「能力边界」确认工具适用性
2. 按「标准流程」完成一次完整操作
3. 遇到报错查「错误码体系」
4. 使用 `--selftest` 验证生成结果

### 7.3 进阶路径（熟练用户）

1. 掌握「自定义校验」：组合使用正则、枚举、范围
2. 学习「复杂处理逻辑」：多表关联、条件分支
3. 配置「输出 Schema 映射」：字段重命名、类型转换
4. 集成到 CI/CD 流程：编写自动化脚本
5. 编写单元测试覆盖边界场景

### 7.4 专家路径（深度定制）

1. 设计可复用的参数模板库
2. 实现插件式处理引擎
3. 构建技能版本管理机制
4. 编写性能优化策略（大数据量分片处理）

---

## 八、高级用法

### 8.1 自定义校验规则

| 规则类型 | 格式 | 示例 | 说明 |
|----------|------|------|------|
| 正则 | `参数名:regex:模式` | `code:regex:^[A-Z]{3}\d{4}$` | 匹配特定模式 |
| 枚举 | `参数名:enum:值1,值2` | `status:enum:active,pending,closed` | 限定可选值 |
| 范围 | `参数名:range:最小值,最大值` | `score:range:0,100` | 数值区间限制 |

### 8.2 多表关联处理

当输入包含多个数据文件时，使用 `--join` 参数：

```bash
skill creator --input main.csv --join detail.csv --on 订单ID
```

### 8.3 条件分支逻辑

在 `validation_rules.json` 中定义条件规则：

```json
{
  "rules": [
    {
      "field": "amount",
      "condition": "if channel == '线上' then range:0,50000 else range:0,10000"
    }
  ]
}
```

---

## 九、用户协议

<!-- user-agreement-injected -->

**使用本 Skill 即视为同意以下条款：**

1. **责任承担**：使用者自行承担全部责任。本 Skill 提供的输出仅供参考，不构成任何形式的保证或承诺。

2. **禁止反向工程**：禁止对本 Skill 进行反向工程、反编译、破解或试图提取源代码。

3. **数据合规**：使用者应确保输入数据的合法性与合规性，不得使用本 Skill 处理违法违规内容。

4. **数据隐私**：本 Skill 不收集、存储或传输任何用户数据，所有处理均在本地完成。

5. **免责声明**：因使用本 Skill 产生的任何直接或间接损失，作者不承担任何责任。

6. **协议确认**：使用本 Skill 即视为同意本协议全部条款。

---

## 十、许可证（License）

<!-- professional-license-embedded -->

### MIT License

Copyright (c) 2024 流云架构师

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

*本文档由 AI 辅助生成，仅供参考。使用前请阅读相关文档。*
