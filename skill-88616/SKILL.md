---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: skill-88616
name: skill-88616
displayName: 反欺诈识别 风险分析 证据整理
description: 反欺诈场景一站式处理：识别、整理、生成与校验，输出可直接使用的结果文件。
version: 1.0.1
rules_version: cpr-20260813-n401
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/skill-88616
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 独立技能工坊
agent_created: true
trigger_words: ["反欺诈", "欺诈识别", "风险分析", "反欺诈批量处理", "自定义规则"]
---

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->


> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# 反欺诈识别与风险分析技能（Skill）

## 一、能力边界速查卡

本技能专注于**用户已提供数据**的反欺诈处理，不涉及外部数据采集与法律判定。

| 维度 | 能做 | 不能做 |
|------|------|--------|
| 数据输入 | 接受用户上传的 CSV/Excel/JSON 格式数据，最大 10 万条记录 | 不主动从外部系统抓取数据（需爬虫或 API 对接） |
| 处理能力 | 字段对齐、格式统一、规则评估、风险评分、分片处理 | 不进行法律定性，不输出法律意见 |
| 输出形式 | 分片结果文件 + 汇总统计报告 + 校验报告 | 不生成具有法律效力的正式文书 |
| 规则配置 | 支持 JSON 自定义规则（字段、阈值、逻辑运算符） | 不支持自然语言规则描述，需结构化配置 |
| 性能优化 | 支持 dtype 指定列类型、分片并行处理（multiprocessing） | 不保证处理速度，受限于硬件环境 |

**适用对象**：需要批量筛查交易记录、用户行为数据、申请资料中潜在欺诈风险的风控人员、数据分析师、业务运营人员。

---

## 二、触发方式与场景映射

当你的输入包含以下关键词或意图时，本技能将被激活：

| 触发词/场景 | 示例输入 | 技能响应 |
|-------------|----------|----------|
| 反欺诈 | "帮我看看这批交易有没有欺诈" | 启动标准反欺诈处理流程 |
| 欺诈识别 | "识别一下这个用户列表里的异常" | 执行规则评估与风险打分 |
| 风险分析 | "分析这些订单的风险等级" | 输出风险评分与分片结果 |
| 批量处理 | "这里有 8 万条记录，分片处理" | 自动分片 + 并行计算 + 汇总 |
| 自定义规则 | "按我的规则文件跑一遍" | 加载 JSON 规则并执行 |

**命令行接口**：
```bash
# 自检命令
反欺诈 --selftest

# 版本查询
反欺诈 --version
```

---

## 三、标准处理流程

### 前置条件

1. 数据文件格式为 CSV、Excel（.xlsx）或 JSON，编码为 UTF-8。
2. 数据中至少包含一个可识别的唯一标识字段（如 `id`、`order_no`）。
3. 自定义规则文件（如有）为 JSON 格式，结构符合下文规范。

### 执行步骤

**步骤 1：数据加载与字段对齐**

- 读取输入文件，自动识别表头。
- 对字段名进行标准化映射（如 `手机号` → `phone`，`金额` → `amount`）。
- 统一日期格式为 `YYYY-MM-DD HH:mm:ss`，数值字段去除千分位逗号。

**步骤 2：数据清洗与类型指定**

- 使用 `dtype` 参数指定列类型（如 `{'amount': 'float32', 'user_id': 'int32'}`），减少内存占用约 40%。
- 缺失值处理：关键字段（金额、用户ID）缺失时标记为 `[需核实:字段名]`，不自动填充。

**步骤 3：规则评估**

- 加载内置规则集（默认包含：金额异常波动、高频交易、短时多地登录、设备指纹异常）。
- 若提供自定义规则 JSON，则合并执行。
- 每条规则输出命中/未命中标记，并计算综合风险分（0-100）。

**步骤 4：分片与并行处理**

- 当记录数 > 10,000 时，自动按 5,000 条/片切分。
- 使用 `multiprocessing.Pool` 对独立分片并行执行规则评估。
- 每片输出独立结果文件（`result_part_001.csv`），并记录处理日志。

**步骤 5：汇总与校验**

- 汇总各分片统计信息：总记录数、命中规则数、风险分布（高/中/低）。
- 生成校验报告，列出具体不一致项（如字段缺失、类型转换失败、规则配置错误）。
- 输出最终文件：`fraud_analysis_summary.json` + 分片结果目录。

### 输出规范

| 输出文件 | 格式 | 内容 |
|----------|------|------|
| 分片结果 | CSV | 原始数据 + 规则命中列 + 风险评分 + 风险等级 |
| 汇总统计 | JSON | 处理总量、分片数、风险分布、耗时 |
| 校验报告 | Markdown | 数据质量检查项、不一致项清单、修正建议 |

---

## 四、置信度门控

当遇到以下情况时，本技能**不会**编造数据，而是输出占位符：

| 场景 | 输出 |
|------|------|
| 字段值缺失 | `[需核实:字段名]` |
| 规则配置引用了不存在的字段 | `[需核实:规则字段]` |
| 数据量超过 10 万条，超出处理上限 | `[需核实:数据截断]` 并提示分批处理 |
| 日期格式无法解析 | `[需核实:日期格式]` 并保留原始值 |

**原则**：宁可输出占位符，不猜测、不填充、不虚构。

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| E001 | 文件格式不支持 | "仅支持 CSV、Excel、JSON 格式" | 转换格式后重试 |
| E002 | 字段映射失败 | "未找到唯一标识字段" | 检查表头，确保包含 id 或 order_no |
| E003 | 规则配置语法错误 | "规则 JSON 解析失败，请检查第 X 行" | 使用 JSON 校验工具修正 |
| E004 | 内存溢出 | "数据量过大，建议分片或增加内存" | 减少单次导入量至 5 万条以内 |
| E005 | 并行进程异常 | "分片处理失败，已回退至单线程" | 检查系统资源，降低并行度 |
| E006 | 输出目录无权限 | "无法写入结果文件" | 更换输出路径或调整权限 |

---

## 六、FAQ 与反模式对照

| 常见坑（反模式） | 正确做法 |
|------------------|----------|
| 直接对全量数据做规则评估，导致内存溢出 | 使用分片 + 并行处理，每片独立评估 |
| 忽略字段类型，用默认 int64 加载大文件 | 使用 `dtype` 指定 `float32`/`int32` 减少内存 |
| 自定义规则中逻辑运算符写错（如 `&&` 而非 `and`） | 严格遵循 JSON 规则格式，使用 `"and"`/`"or"` |
| 对缺失值直接填 0 或平均值 | 标记为 `[需核实:字段名]`，交由用户确认 |
| 一次处理超过 10 万条记录 | 分批导入，每批不超过上限，最后合并汇总 |
| 将风险评分当作法律定性依据 | 明确输出为"风险分析建议"，不构成法律意见 |

---

## 七、自定义规则 JSON 格式

```json
{
  "rules": [
    {
      "name": "高频交易检测",
      "field": "transaction_count",
      "operator": "gt",
      "threshold": 50,
      "logic": "and",
      "weight": 0.3
    },
    {
      "name": "金额异常",
      "field": "amount",
      "operator": "gte",
      "threshold": 100000,
      "logic": "or",
      "weight": 0.5
    }
  ],
  "risk_levels": {
    "high": 80,
    "medium": 50,
    "low": 0
  }
}
```

**支持的操作符**：`eq`（等于）、`neq`（不等于）、`gt`（大于）、`gte`（大于等于）、`lt`（小于）、`lte`（小于等于）、`in`（在列表中）、`contains`（包含）。

---

## 八、渐进式阅读路径

### 新手路径（5 分钟上手）

1. 阅读「能力边界速查卡」了解基本范围。
2. 准备一份 CSV 数据文件（含 id 和 amount 字段）。
3. 直接调用技能，使用默认规则集。
4. 查看输出的 `fraud_analysis_summary.json` 了解整体风险分布。

### 进阶路径（深入定制）

1. 学习「自定义规则 JSON 格式」，编写业务专属规则。
2. 调整 `dtype` 参数优化内存占用。
3. 对超过 5 万条的数据启用并行分片处理。
4. 结合「校验报告」迭代优化数据质量。

---

## 九、性能优化参数参考

| 参数 | 默认值 | 建议范围 | 说明 |
|------|--------|----------|------|
| `chunk_size` | 5000 | 2000-10000 | 分片大小，影响内存与并行效率 |
| `parallel_workers` | CPU 核数 | 2-8 | 并行进程数，过高会增加调度开销 |
| `dtype` | 自动推断 | 显式指定 | 推荐 `float32` 替代 `float64` |
| `low_memory` | False | True/False | 分块读取大文件时启用 |

---

## 十、用户协议

<!-- user-agreement-injected -->

**使用本 Skill 即表示您同意以下条款：**

1. **责任承担**：使用者应自行承担因使用本技能产生的全部责任。本技能输出的风险分析结果和建议仅供参考，不构成任何形式的保证或承诺。
2. **禁止反向工程**：使用者不得对本技能进行反向工程、反编译、破解或试图提取底层算法逻辑。
3. **数据合规**：使用者应确保输入数据来源合法，不包含侵犯第三方权益的信息。因数据使用引发的纠纷由使用者自行解决。
4. **无法律意见**：本技能输出内容不构成法律意见，涉及法律纠纷请咨询专业律师。
5. **修改与终止**：技能作者保留随时修改、更新或终止本技能的权利，恕不另行通知。

---

## 十一、许可证（License）

<!-- professional-license-embedded -->

**MIT License**

Copyright (c) 2026 独立技能工坊

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

## 十二、版本与自检

```bash
# 运行自检，验证环境与依赖
反欺诈 --selftest

# 预期输出
# [OK] 环境检查通过
# [OK] 依赖库版本兼容
# [OK] 内置规则集加载正常
# [OK] 示例数据测试通过
```

**当前版本**：1.0.0  
**更新日志**：
- v1.0.0（2026-08-13）：初始版本，支持批量处理、自定义规则、分片并行、输出校验。

---

*本 Skill 由 AI 辅助生成，仅供参考。使用前请阅读相关文档，确保符合您的业务场景。*
