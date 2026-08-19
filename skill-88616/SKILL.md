---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: skill-88616
name: skill-88616
displayName: 反欺诈识别 风险分析 批量处理
description: 反欺诈场景一站式处理：识别、整理、生成与校验，输出可直接使用的结果文件。
version: 1.0.2
rules_version: cpr-20260819-n551
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/skill-88616
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: RiskForge Studio
agent_created: true
trigger_words: ["反欺诈", "欺诈识别", "风险分析", "反欺诈批量处理", "自定义规则", "异常检测", "风控扫描"]
---

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->


> 本内容由 AI 生成，仅供学习参考 <!-- ai-generated-notice -->

# 反欺诈识别与风险分析 Skill 文档

## 一、能力边界速查卡（一页纸）

本 Skill 面向**反欺诈场景**，提供从原始数据到最终风险报告的一站式处理能力。以下是能力边界速览：

| 维度 | 支持 | 不支持 |
|------|------|--------|
| 数据格式 | CSV、Excel（.xlsx）、JSON（UTF-8 编码） | 数据库直连、API 实时拉取 |
| 数据规模 | 单文件 ≤ 50 万行（建议 ≤ 10 万行） | 流式无限数据 |
| 识别能力 | 基于规则集的欺诈模式匹配、异常金额检测、频次异常分析 | 机器学习模型训练、深度学习预测 |
| 自定义规则 | 支持 JSON 格式规则文件（结构见下文） | 图形化规则编辑器 |
| 输出产物 | `fraud_analysis_summary.json` + 分片结果目录 | 可视化仪表盘、邮件推送 |
| 校验能力 | 数据完整性校验、字段类型校验、规则冲突检测 | 业务逻辑正确性保证 |

**适用对象**：电商平台运营人员、支付风控专员、数据分析师、业务安全团队。需要具备基础的 JSON 和 CSV 操作能力。

**不适用场景**：实时交易拦截（需毫秒级响应）、复杂团伙欺诈识别（需图计算）、未知新型欺诈模式发现（需无监督学习）。

---

## 二、触发方式与场景映射

当你的需求与下表左侧描述匹配时，可直接使用本 Skill：

| 你说的话（大白话） | 触发动作 | 对应能力 |
|-------------------|----------|----------|
| "帮我看看这批订单有没有异常" | 触发 `反欺诈` / `欺诈识别` | 默认规则集扫描 |
| "这批数据里有没有刷单的" | 触发 `风险分析` | 频次 + 金额异常检测 |
| "按我们公司的规则跑一遍" | 触发 `自定义规则` | 加载自定义规则 JSON |
| "5 万条数据，帮我分片处理" | 触发 `反欺诈批量处理` | 并行分片 + 汇总 |
| "检查一下规则文件对不对" | 触发 `--selftest` | 规则自检与冲突检测 |
| "看下版本信息" | 触发 `--version` | 版本号输出 |

**触发词优先级**：`自定义规则` > `反欺诈批量处理` > `欺诈识别` > `风险分析` > `反欺诈`。当同时出现多个触发词时，按此顺序匹配最具体的能力。

---

## 三、标准处理流程

### 3.1 前置条件

| 条件项 | 要求 | 校验方式 |
|--------|------|----------|
| 数据文件 | CSV / XLSX / JSON，UTF-8 编码 | 文件头检查 |
| 唯一标识字段 | 至少包含 `id` 或 `order_no` 之一 | 字段存在性检查 |
| 金额字段 | 建议包含 `amount` 字段（数值型） | 类型推断 |
| 自定义规则（可选） | JSON 格式，结构符合 3.4 节规范 | `--selftest` 预检 |

### 3.2 执行步骤

**Step 1：环境准备**

```bash
# 确认 Python 环境（3.8+）
python --version

# 安装依赖（如需）
pip install pandas openpyxl
```

**Step 2：数据准备**

将数据文件放置于工作目录，命名建议：`input_data.csv`。确认首行包含字段名，数据行无空值（如有，需先清洗）。

**Step 3：调用技能**

```bash
# 基础调用（默认规则集）
python main.py --input input_data.csv

# 指定自定义规则
python main.py --input input_data.csv --rules my_rules.json

# 大数据量分片处理（>5 万条）
python main.py --input input_data.csv --parallel --chunk-size 10000

# 规则自检
python main.py --selftest --rules my_rules.json

# 版本查询
python main.py --version
```

**Step 4：查看输出**

执行完成后，工作目录下生成：

```
output/
├── fraud_analysis_summary.json    # 整体风险汇总
├── chunks/                        # 分片结果目录
│   ├── chunk_0_result.json
│   ├── chunk_1_result.json
│   └── ...
└── validation_report.json         # 数据质量校验报告
```

### 3.3 输出规范

`fraud_analysis_summary.json` 结构示例：

```json
{
  "summary": {
    "total_records": 10000,
    "flagged_records": 342,
    "risk_levels": {
      "high": 45,
      "medium": 128,
      "low": 169
    },
    "processing_time_seconds": 12.5
  },
  "top_risk_factors": [
    {"factor": "amount_outlier", "count": 87},
    {"factor": "frequency_anomaly", "count": 156}
  ],
  "data_quality": {
    "missing_id_count": 0,
    "invalid_amount_count": 3,
    "duplicate_id_count": 2
  }
}
```

分片结果文件包含每条被标记记录的完整信息：`id`、`risk_score`（0-100）、`risk_level`、`matched_rules`、`evidence`（命中详情）。

### 3.4 自定义规则 JSON 格式

```json
{
  "rules": [
    {
      "rule_id": "R001",
      "name": "单笔金额超阈值",
      "field": "amount",
      "operator": "gt",
      "threshold": 50000,
      "risk_weight": 0.8,
      "description": "单笔金额超过 5 万元标记为高风险"
    },
    {
      "rule_id": "R002",
      "name": "短时高频交易",
      "field": "order_count",
      "operator": "gte",
      "threshold": 10,
      "time_window": "1h",
      "risk_weight": 0.6
    }
  ],
  "global_config": {
    "high_risk_threshold": 70,
    "medium_risk_threshold": 40,
    "enable_frequency_analysis": true
  }
}
```

**操作符支持**：`gt`（大于）、`gte`（大于等于）、`lt`（小于）、`lte`（小于等于）、`eq`（等于）、`neq`（不等于）、`in`（在列表中）、`contains`（包含子串）。

---

## 四、置信度门控机制

本 Skill 遵循**不编造原则**。在以下情况，输出中会显式标注占位符：

| 场景 | 输出行为 |
|------|----------|
| 数据缺少 `amount` 字段 | 金额相关规则跳过，输出 `[需核实:amount字段缺失]` |
| 自定义规则引用了不存在的字段 | 该规则不执行，输出 `[需核实:规则R00X引用的字段不存在]` |
| 分片处理时某分片失败 | 该分片结果标记为 `[需核实:chunk_N处理失败]`，不中断整体流程 |
| 数据量超过建议上限 | 输出警告 `[需核实:数据量超过建议范围，结果可能不准确]` |

**置信度评分**：每条标记记录附带 `confidence` 字段（0-1），基于命中规则的数量和权重计算。`confidence < 0.5` 的记录在 summary 中单独归类为"待人工复核"。

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| E001 | 文件不存在 | "未找到输入文件，请检查路径" | 确认文件路径，重新执行 |
| E002 | 编码错误 | "文件编码非 UTF-8，请转换后重试" | 使用 `iconv -f GBK -t UTF-8` 转换 |
| E003 | 缺少唯一标识字段 | "数据中未找到 id 或 order_no 字段" | 检查 CSV 表头，补充标识字段 |
| E004 | 规则文件格式错误 | "自定义规则 JSON 解析失败" | 使用 `--selftest` 定位错误行 |
| E005 | 规则字段冲突 | "规则 R001 与 R002 存在逻辑冲突" | 调整规则阈值或权重 |
| E006 | 内存不足 | "数据量过大，建议启用分片处理" | 添加 `--parallel --chunk-size 5000` |
| E007 | 输出目录无权限 | "无法写入输出目录，请检查权限" | 修改目录权限或更换路径 |

**自检命令**：执行 `python main.py --selftest --rules your_rules.json` 可提前发现 E004、E005 类错误，无需等待完整运行。

---

## 六、常见坑与反模式对照（FAQ）

### 坑 1：忽略数据清洗直接跑批

**错误做法**：原始数据含空值、重复行，直接执行分析。

**正确姿势**：先运行一次基础校验（`--selftest`），查看 `validation_report.json`，清洗后再正式执行。

### 坑 2：规则阈值设置不合理

**错误做法**：金额阈值设得过低（如 100 元），导致大量正常订单被标记。

**正确姿势**：先跑默认规则集，查看风险分布，再根据业务实际调整阈值。建议阈值设置参考业务均值 + 3 倍标准差。

### 坑 3：无视分片处理的内存限制

**错误做法**：10 万条数据直接单线程处理，导致内存溢出（E006）。

**正确姿势**：数据量 > 5 万条时，主动添加 `--parallel` 参数，分片大小建议 5000-10000 条。

### 坑 4：自定义规则与默认规则冲突

**错误做法**：自定义规则覆盖了默认规则，导致基础风险检测失效。

**正确姿势**：自定义规则默认**追加**到默认规则集之后，如需覆盖需在规则文件中显式声明 `"override": true`。

### 坑 5：忽略置信度门控标记

**错误做法**：直接采信所有标记结果，未处理 `[需核实]` 占位符。

**正确姿势**：先筛选 `confidence >= 0.7` 的记录作为高置信度结果，其余进入人工复核队列。

---

## 七、渐进式阅读路径

### 新手路径（首次使用）

1. 阅读**第一节**能力边界速查卡，确认本 Skill 是否适合你的场景。
2. 准备一份含 `id` 和 `amount` 字段的 CSV 测试文件（100 条以内）。
3. 执行基础调用：`python main.py --input test.csv`。
4. 查看 `fraud_analysis_summary.json` 中的风险分布，理解输出含义。
5. 阅读**第三节**标准流程，了解完整参数。

### 进阶路径（业务定制）

1. 学习 **3.4 节**自定义规则 JSON 格式，编写业务专属规则。
2. 使用 `--selftest` 预检规则文件，确保无冲突。
3. 对超过 5 万条的数据启用 `--parallel` 分片处理。
4. 结合 `validation_report.json` 迭代优化数据质量。
5. 定期检查**第五节**错误码，建立运维监控。

### 专家路径（深度调优）

1. 分析 `chunks/` 目录下分片结果，识别规则误报模式。
2. 调整 `global_config` 中的风险阈值，平衡召回率与精确率。
3. 结合业务历史数据，建立专属规则库并版本化管理。
4. 将本 Skill 集成到 CI/CD 流水线，实现定时批量扫描。

---

## 八、参数速查表

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `--input` | str | 必填 | 输入数据文件路径 |
| `--rules` | str | 默认规则集 | 自定义规则 JSON 路径 |
| `--output` | str | `./output` | 输出目录 |
| `--parallel` | bool | False | 启用并行分片处理 |
| `--chunk-size` | int | 10000 | 分片大小（启用 parallel 时生效） |
| `--selftest` | bool | False | 规则自检模式 |
| `--version` | bool | False | 输出版本号 |
| `--dtype` | str | 自动推断 | 指定字段类型，如 `{"amount": "float32"}` |

---

## 九、用户协议

**使用本 Skill 即表示您同意以下条款：**

1. **责任承担**：使用者应自行承担因使用本技能产生的全部责任。本技能输出的风险分析结果和建议仅供参考，不构成任何形式的保证或承诺。因使用本技能做出的业务决策，后果由使用者自行承担。

2. **禁止反向工程**：使用者不得对本技能进行反向工程、反编译、破解或试图提取底层算法逻辑。不得复制、修改、分发本技能的核心处理逻辑。

3. **数据合规**：使用者应确保输入数据来源合法，不包含侵犯第三方权益的信息。因数据使用引发的纠纷由使用者自行解决。本技能不存储任何输入数据，所有处理均在本地完成。

4. **无法律意见**：本技能输出内容不构成法律意见，涉及法律纠纷请咨询专业律师。

5. **修改与终止**：技能作者保留随时修改、更新或终止本技能的权利，恕不另行通知。

<!-- user-agreement-injected -->

---

## 十、许可证（License）

本 Skill 遵循 MIT 许可证发布：

```
MIT License

Copyright (c) 2026 原创作者（自持版权）

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

## 附录：main.py 参考实现

以下为 Skill 配套的参考实现（简化版），供理解处理逻辑使用：

```python
#!/usr/bin/env python3
"""反欺诈识别与风险分析 - 参考实现"""
import argparse
import json
import os
import sys
from datetime import datetime

VERSION = "1.0.0"

def parse_args():
    parser = argparse.ArgumentParser(description="反欺诈识别与风险分析")
    parser.add_argument("--input", type=str, help="输入数据文件路径")
    parser.add_argument("--rules", type=str, help="自定义规则 JSON 路径")
    parser.add_argument("--output", type=str, default="./output", help="输出目录")
    parser.add_argument("--parallel", action="store_true", help="启用并行分片处理")
    parser.add_argument("--chunk-size", type=int, default=10000, help="分片大小")
    parser.add_argument("--selftest", action="store_true", help="规则自检模式")
    parser.add_argument("--version", action="store_true", help="输出版本号")
    parser.add_argument("--dtype", type=str, default=None, help="字段类型映射 JSON")
    return parser.parse_args()

def load_default_rules():
    """加载默认规则集"""
    return {
        "rules": [
            {
                "rule_id": "D001",
                "name": "单笔金额异常偏高",
                "field": "amount",
                "operator": "gt",
                "threshold": 50000,
                "risk_weight": 0.8
            },
            {
                "rule_id": "D002",
                "name": "金额为负值",
                "field": "amount",
                "operator": "lt",
                "threshold": 0,
                "risk_weight": 1.0
            }
        ],
        "global_config": {
            "high_risk_threshold": 70,
            "medium_risk_threshold": 40
        }
    }

def selftest(rules_path):
    """规则自检"""
    if not rules_path:
        print("[OK] 使用默认规则集")
        return True
    try:
        with open(rules_path, "r", encoding="utf-8") as f:
            rules = json.load(f)
        assert "rules" in rules, "缺少 rules 字段"
        for r in rules["rules"]:
            assert "rule_id" in r, "规则缺少 rule_id"
