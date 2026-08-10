---
slug: crm-customer-track
name: crm-customer-track
displayName: 客户旅程 商机预警 跟进复盘
description: 记录客户互动全轨迹，识别停滞与流失风险，辅助跟进决策。
version: 2.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: FlowForge Studio
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: FlowForge Studio
agent_created: true
trigger_words: ["客户跟进", "客户轨迹", "商机预警", "跟进记录", "客户状态", "客户旅程", "商机停滞", "流失风险"]
---

> 📜 **用户协议（User Agreement）**
> 1. 本 Skill 仅供学习与参考用途。使用本 Skill 产生的任何结果，由使用者自行承担全部责任；本 Skill 不提供任何明示或暗示的保证。
> 2. 涉及法律、财务、税务、投资、医疗等专业决策时，请务必咨询持证专业人士。
> 3. 本代码受版权法保护，未经授权复制、反向工程或商业利用将被追究法律责任。
<!-- user-agreement-injected -->


# 客户跟进轨迹管理（CRM Customer Track）

**一句话定位**：面向销售运营、客户成功经理和销售团队负责人的客户跟进轨迹分析工具，通过结构化时间线归并、沉默阈值识别和流失风险评分，解决“客户何时该跟进、哪个商机在流失、下一步该做什么”三大痛点。

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

---

## 快速开始 Quick Start

以下 3 条路径覆盖 90% 的日常使用场景，每条均可在 1 分钟内完成。

| 场景 | 命令 | 预期结果 |
|------|------|----------|
| **最小可用**：分析 CSV 跟进记录并输出 JSON 报告 | `python run.py --file ./customer_data.csv --output ./report.json` | 生成 `report.json`，包含客户时间线、停滞预警、流失评分 |
| **自定义阈值**：将沉默阈值调整为 7 天 | `python run.py --file ./data.xlsx --threshold 7 --output ./report.csv` | 生成 CSV 报告，7 天无互动的商机被标记为停滞 |
| **安全预览**：不写盘，仅查看将生成的分析结果摘要 | `python run.py --file ./data.csv --dry-run` | 控制台打印各客户跟进摘要与预警清单，不生成任何文件 |

---

## 适用场景 When to Use

### ✅ 推荐使用

- **批量梳理客户跟进状态**：销售运营需要每周/每月对数百个客户的跟进记录做结构化归并。
- **识别沉默客户并制定挽回策略**：客户成功经理需要快速定位 7/14/30 天无互动的客户。
- **掌握商机健康度分布**：销售团队负责人需要了解停滞商机数量、流失风险等级分布。
- **跟进复盘与交接**：销售离职交接时，将历史跟进记录整理为结构化时间线。

### ❌ 不要使用

- **实时 CRM 系统集成**：本工具不连接任何 CRM 数据库，需人工导出 CSV/XLSX 文件。
- **成交概率预测**：仅基于历史数据做趋势判断，不预测未来成交概率。
- **非结构化文本处理**：语音转写稿需先整理为文本记录，本工具不处理原始音频。
- **替代销售判断**：所有预警需人工复核，工具不替代人的决策。

---

## 能力总览 Capabilities

| 能力项 | 命令/参数 | 示例 | 说明 |
|--------|-----------|------|------|
| **轨迹归档** | `--file` | `python run.py --file ./data.csv` | 将分散的客户互动记录按时间轴归并，输出结构化时间线 |
| **停滞识别** | `--threshold` | `python run.py --file ./data.csv --threshold 14` | 基于沉默阈值（默认 14 天）标记停滞商机 |
| **流失评分** | 自动计算 | `python run.py --file ./data.csv` | 结合互动频次、情绪倾向、竞品动态计算流失概率（低/中/高） |
| **决策辅助** | 自动生成 | `python run.py --file ./data.csv` | 为每个停滞商机推荐下一步动作（关怀/调整策略/移交） |
| **安全预览** | `--dry-run` | `python run.py --file ./data.csv --dry-run` | 只打印分析摘要，不写任何文件 |
| **详细诊断** | `--verbose` | `python run.py --file ./data.csv --verbose` | 输出每个客户的详细分析过程与评分依据 |
| **自检测试** | `--selftest` | `python run.py --selftest` | 运行内置测试用例，验证核心功能正确性 |

---

## 模块决策表 Decision Table

| 用户意图 | 推荐模块 | 读取指引 |
|----------|----------|----------|
| 快速了解客户跟进概况 | `--dry-run` + `--verbose` | 先预览再决定是否生成完整报告 |
| 生成周报/月报 | `--file` + `--output` | 指定输入文件与输出路径，生成 JSON 或 CSV |
| 调整停滞判定标准 | `--threshold` | 根据业务节奏设置沉默阈值（如 7/14/30 天） |
| 排查数据问题 | `--verbose` + 错误码 | 查看详细诊断信息，定位数据格式问题 |
| 验证工具正确性 | `--selftest` | 运行内置测试，确认核心逻辑无误 |

---

## 示例 Examples

### 示例 1：基础分析（CSV 输入 → JSON 输出）

**输入文件 `customer_data.csv`**：

```csv
客户ID,客户名称,跟进日期,跟进方式,跟进内容摘要
C001,张三,2026-01-01,电话,讨论产品需求
C001,张三,2026-01-10,邮件,发送报价单
C002,李四,2026-01-05,会议,演示产品功能
C002,李四,2026-01-20,微信,客户表示满意
```

**命令**：

```bash
python run.py --file ./customer_data.csv --output ./report.json
```

**输出 `report.json`（节选）**：

```json
{
  "customers": [
    {
      "customer_id": "C001",
      "customer_name": "张三",
      "total_interactions": 2,
      "last_interaction_date": "2026-01-10",
      "days_since_last": 5,
      "status": "active",
      "risk_level": "low",
      "suggested_action": "保持当前跟进节奏"
    }
  ],
  "summary": {
    "total_customers": 2,
    "stalled_count": 0,
    "risk_distribution": {"low": 2, "medium": 0, "high": 0}
  }
}
```

### 示例 2：自定义阈值 + CSV 输出

**命令**：

```bash
python run.py --file ./customer_data.csv --threshold 7 --output ./report.csv
```

**输出 `report.csv`（节选）**：

```csv
客户ID,客户名称,最近跟进日期,距今天数,状态,风险等级,建议动作
C001,张三,2026-01-10,5,正常,低,保持当前跟进节奏
C002,李四,2026-01-20,0,正常,低,保持当前跟进节奏
```

### 示例 3：安全预览（不写盘）

**命令**：

```bash
python run.py --file ./customer_data.csv --dry-run
```

**控制台输出**：

```text
[DRY-RUN] 将生成分析报告，但不会写入任何文件。
客户 C001 (张三): 2 次互动, 最近跟进 5 天前, 风险等级: 低
客户 C002 (李四): 2 次互动, 最近跟进 0 天前, 风险等级: 低
[DRY-RUN] 共 2 个客户, 0 个停滞, 建议动作已生成。
```

---

## 安装与配置 Installation

### 环境要求

- Python 3.9+
- 可选依赖：`openpyxl`（用于读取 XLSX 文件）

### 安装步骤

```bash
# 1. 克隆或下载本 Skill 文件
# 2. （可选）安装 openpyxl 以支持 XLSX 格式
pip install openpyxl

# 3. 验证安装
python run.py --selftest
```

### 输入文件格式

**CSV 文件**（UTF-8 或 GBK 编码均可）：

| 字段名 | 必填 | 说明 |
|--------|------|------|
| 客户ID | ✅ | 客户唯一标识 |
| 客户名称 | ✅ | 客户显示名称 |
| 跟进日期 | ✅ | 格式 `YYYY-MM-DD` 或 `YYYY/MM/DD` |
| 跟进方式 | ✅ | 电话/邮件/会议/微信等 |
| 跟进内容摘要 | ✅ | 互动内容描述 |

**XLSX 文件**：需包含与 CSV 相同的列名。

---

## 常见问题 Troubleshooting

| 错误现象 | 原因 | 解决办法 |
|----------|------|----------|
| `E001: 文件不存在` | 输入文件路径错误 | 检查文件路径是否正确，文件是否存在 |
| `E002: 缺少必填字段` | CSV 缺少必要列 | 确认包含 `客户ID/客户名称/跟进日期/跟进方式/跟进内容摘要` 五列 |
| `E003: 日期解析失败` | 日期格式不符合要求 | 使用 `YYYY-MM-DD` 或 `YYYY/MM/DD` 格式 |
| `E004: 编码错误` | 文件编码无法识别 | 将文件另存为 UTF-8 或 GBK 编码 |
| `E005: 依赖缺失` | 未安装 openpyxl 且输入为 XLSX | 执行 `pip install openpyxl` |

---

## 最佳实践 Best Practices

### 数据准备

- **统一日期格式**：导入前将所有日期统一为 `YYYY-MM-DD`，避免解析错误。
- **清洗重复记录**：同一客户同一天的多次互动建议合并为一条记录。
- **补充情绪信息**：在跟进内容摘要中包含情绪关键词（如“满意”“推迟”），提升流失评分准确性。

### 阈值设置

- **快速销售周期**（如 SaaS 试用）：建议 `--threshold 7`
- **标准销售周期**（如企业软件）：建议 `--threshold 14`
- **长周期销售**（如大型项目）：建议 `--threshold 30`

### 安全提醒

- **敏感数据**：客户跟进记录可能包含商业敏感信息，请勿在公共环境运行。
- **数据备份**：`--dry-run` 模式不会修改任何文件，但正式运行前建议备份原始数据。
- **人工复核**：所有预警和评分仅作参考，需结合业务实际进行人工判断。

---

## 相关资源 Related

- [Python csv 模块文档](https://docs.python.org/3/library/csv.html)
- [openpyxl 官方文档](https://openpyxl.readthedocs.io/)
- [CRM 客户跟进最佳实践指南](https://www.hubspot.com/crm)

---

## 许可证（License）

```text
MIT License

Copyright (c) 2026 FlowForge Studio

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

## 失败处理

- 命令执行失败或返回非零退出码时，程序会输出明确错误信息并给出排查建议。
- 依赖缺失时提示安装命令；网络异常时建议重试并检查连接。
- 异常情况不中断主流程，错误信息包含具体原因（error context），便于定位修复。

## 前置条件

- 本技能开箱即用，无需额外安装依赖。
- 需要 Python 3.9+ 运行环境。
- 涉及网络请求时需保持网络连通。

## 执行步骤

1. 读取输入参数或交互输入。
2. 按技能定义的处理流程执行核心逻辑。
3. 输出结构化结果，并在完成后给出下一步建议。