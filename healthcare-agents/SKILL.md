---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: healthcare-agents
name: healthcare-agents
displayName: 医疗行政 专科智能体 流程自动化
description: 51个专科AI智能体，处理美国医疗行政数据清洗与字段映射。
version: 1.0.3
rules_version: cpr-20260820-n601
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/healthcare-agents
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: DataFlow Architect
agent_created: true
trigger_words: ["healthcare agents", "医疗行政智能体", "医疗流程自动化", "healthcare admin agents", "医疗行政工作流", "专科数据处理", "医疗记录清洗"]
---

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->


> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# healthcare-agents — 医疗行政专科智能体工具包

## 一、能力边界（一页纸速查卡）

### 1.1 工具包能做什么

| 能力项 | 说明 | 适用场景示例 |
|--------|------|-------------|
| 专科字段映射 | 根据 51 个专科代码表，将原始 CSV 字段映射为标准化输出 | 心脏病科、骨科、神经内科等专科的医疗记录整理 |
| 数据优先级消解 | 多源数据冲突时，按"最近日期优先"规则自动选择 | 同一患者在不同日期有多次就诊记录 |
| 冲突标记 | 无法判断优先级时，输出 `[需核实:字段名]` 占位符 | 两个不同来源的出生日期不一致且无时间戳 |
| 处理日志 | 每次运行生成 `processing_log.json`，记录冲突详情 | 需要人工复核的数据质量问题追踪 |
| 批量处理 | 支持整个 `./medical_input/` 目录的批量文件处理 | 月度医疗记录归档 |

### 1.2 工具包不能做什么

| 限制项 | 说明 |
|--------|------|
| 不提供临床诊断 | 仅处理行政数据，不涉及医学判断 |
| 不保证数据准确性 | 输入数据本身有误时，工具无法识别 |
| 不处理非结构化文本 | 仅支持 CSV 格式的结构化数据 |
| 不自动修复冲突 | 冲突仅标记，需人工决策 |
| 不覆盖所有医疗场景 | 仅限 51 个预设专科类型 |

### 1.3 适用对象

- **医疗行政人员**：需要批量整理患者记录、生成标准化报表
- **医疗数据工程师**：需要将异构数据源统一为规范格式
- **医疗系统集成商**：需要将数据映射逻辑嵌入现有管理系统

---

## 二、触发方式

### 2.1 触发词

| 触发词 | 使用场景 |
|--------|---------|
| `healthcare agents` | 英文环境下的标准触发 |
| `医疗行政智能体` | 中文环境下的标准触发 |
| `医疗流程自动化` | 需要描述工具包功能时 |
| `healthcare admin agents` | 英文环境下的管理场景 |
| `医疗行政工作流` | 中文环境下的流程描述 |
| `专科数据处理` | 强调专科维度时 |
| `医疗记录清洗` | 强调数据清洗功能时 |

### 2.2 场景映射表

| 大白话描述 | 实际对应操作 |
|-----------|-------------|
| "帮我把这些病历整理一下" | 运行 `run_agents.py` 批量处理 CSV 文件 |
| "这个字段怎么有两个值" | 查看 `processing_log.json` 中的冲突记录 |
| "我想知道处理结果靠不靠谱" | 检查输出中是否有 `[需核实:]` 占位符 |
| "能不能只处理心脏科的" | 修改专科映射规则，仅保留指定专科代码 |
| "处理完的文件叫什么名字" | 输出文件按 `[专科代码]_processed_[时间戳].csv` 命名 |

---

## 三、标准流程

### 3.1 前置条件

| 条件 | 要求 | 检查方法 |
|------|------|---------|
| Python 环境 | Python 3.8+ | `python --version` |
| 依赖包 | pandas, numpy | `pip list \| grep pandas` |
| 输入目录 | `./medical_input/` 存在 | `ls ./medical_input/` |
| 输出目录 | `./medical_output/` 存在 | `ls ./medical_output/` |
| 测试文件 | `test.csv` 存在 | `ls ./medical_input/test.csv` |

### 3.2 执行步骤

#### 步骤 1：放置输入文件

将待处理的 CSV 文件放入 `./medical_input/` 目录。

```bash
cp /path/to/your/data.csv ./medical_input/
```

#### 步骤 2：验证测试文件

检查 `test.csv` 的字段结构是否符合预期：

```bash
head -5 ./medical_input/test.csv
```

预期字段示例：

```csv
patient_id,visit_date,specialty_code,diagnosis,provider_name
P001,2025-03-15,CARD,Hypertension,Dr. Smith
P002,2025-03-16,ORTH,Fracture,Dr. Jones
```

#### 步骤 3：执行全量处理

```bash
python run_agents.py --input ./medical_input/ --output ./medical_output/
```

参数说明：

| 参数 | 必填 | 默认值 | 说明 |
|------|------|--------|------|
| `--input` | 是 | 无 | 输入目录路径 |
| `--output` | 是 | 无 | 输出目录路径 |
| `--specialty` | 否 | 全部 | 指定专科代码，如 `--specialty CARD` |
| `--verbose` | 否 | False | 输出详细日志 |

#### 步骤 4：检查处理日志

```bash
cat ./medical_output/processing_log.json
```

日志内容示例：

```json
{
  "run_id": "20250820_143022",
  "total_files": 3,
  "processed_files": 3,
  "conflicts": [
    {
      "file": "cardiology.csv",
      "record_id": "P001",
      "field": "birth_date",
      "values": ["1950-01-01", "1950-06-15"],
      "resolution": "needs_review"
    }
  ]
}
```

#### 步骤 5：抽查结果质量

随机抽取 10 条输出记录，确认无 `[需核实:]` 占位符：

```bash
grep -c "需核实" ./medical_output/*.csv
```

如果输出为 `0`，说明所有字段均成功解析。

### 3.3 输出规范

| 输出项 | 命名规则 | 格式 |
|--------|---------|------|
| 处理结果 | `[专科代码]_processed_[时间戳].csv` | CSV，UTF-8 编码 |
| 处理日志 | `processing_log.json` | JSON，UTF-8 编码 |
| 错误报告 | `error_report_[时间戳].txt` | 纯文本 |

时间戳格式：`YYYYMMDD_HHMMSS`（本地时区）

---

## 四、置信度门控

### 4.1 占位符机制

当工具无法确定字段值时，**不会编造数据**，而是输出 `[需核实:字段名]` 占位符。

### 4.2 优先级规则

| 场景 | 处理策略 |
|------|---------|
| 同一字段有多个值，且有时间戳 | 取最近日期的值 |
| 同一字段有多个值，无时间戳 | 输出 `[需核实:字段名]`，记录冲突 |
| 字段值为空 | 输出 `[需核实:字段名]`，记录缺失 |
| 字段值格式非法 | 输出 `[需核实:字段名]`，记录格式错误 |

### 4.3 冲突记录格式

`processing_log.json` 中的冲突记录包含：

```json
{
  "file": "原始文件名",
  "record_id": "记录唯一标识",
  "field": "冲突字段名",
  "values": ["值1", "值2"],
  "resolution": "needs_review",
  "timestamp": "2025-08-20T14:30:22Z"
}
```

### 4.4 人工复核流程

1. 打开 `processing_log.json`，筛选 `resolution: "needs_review"` 的记录
2. 根据 `file` 和 `record_id` 定位原始记录
3. 核对 `values` 中的多个值，确定正确值
4. 手动修正输出 CSV 中的占位符

---

## 五、错误码体系

| 错误码 | 错误描述 | 提示话术 | 修正步骤 |
|--------|---------|---------|---------|
| `E001` | 输入目录不存在 | `Error: Input directory ./medical_input/ not found` | 创建目录：`mkdir -p ./medical_input/` |
| `E002` | 输出目录不存在 | `Error: Output directory ./medical_output/ not found` | 创建目录：`mkdir -p ./medical_output/` |
| `E003` | CSV 文件格式错误 | `Error: Invalid CSV format in file: [文件名]` | 检查文件编码是否为 UTF-8，分隔符是否为逗号 |
| `E004` | 缺少必填字段 | `Error: Missing required field: [字段名]` | 检查 CSV 表头，补充缺失字段 |
| `E005` | 专科代码无效 | `Error: Unknown specialty code: [代码]` | 对照附录 A 的专科代码表，修正代码 |
| `E006` | 日期格式错误 | `Error: Invalid date format: [值]` | 统一使用 `YYYY-MM-DD` 格式 |
| `E007` | 内存不足 | `Error: Out of memory while processing [文件名]` | 分批次处理，或增加系统内存 |
| `E008` | 权限不足 | `Error: Permission denied for [路径]` | 检查文件读写权限 |

---

## 六、FAQ 反模式

### 6.1 常见坑与反模式对照

| 反模式 | 问题描述 | 正确做法 |
|--------|---------|---------|
| **忽略测试文件** | 直接跑全量数据，发现字段映射错误 | 先运行 `test.csv` 验证字段结构 |
| **手动修改输出** | 直接编辑输出 CSV 修正占位符 | 通过 `processing_log.json` 定位问题，修正输入数据后重新运行 |
| **覆盖原始文件** | 将输出文件写回 `./medical_input/` | 输出目录与输入目录严格分离 |
| **忽略冲突日志** | 只看输出 CSV，不检查 `processing_log.json` | 每次运行后必须检查冲突记录 |
| **修改专科代码表** | 随意增删专科代码导致映射失败 | 通过 `run_agents.py` 的 `--specialty` 参数控制，不修改底层代码表 |

### 6.2 反模式示例

**反模式 1：跳过测试直接跑全量**

```bash
# 错误做法
python run_agents.py --input ./medical_input/ --output ./medical_output/

# 正确做法
python run_agents.py --input ./medical_input/ --output ./medical_output/ --specialty CARD
# 先跑单个专科验证，再跑全量
```

**反模式 2：用 Excel 直接编辑输出文件**

```bash
# 错误做法
open ./medical_output/CARD_processed_20250820_143022.csv
# 在 Excel 中手动修改 [需核实:] 占位符

# 正确做法
cat ./medical_output/processing_log.json
# 定位冲突记录，修正输入数据，重新运行
```

---

## 七、渐进式披露

### 7.1 速查卡（新手必读）

1. 把文件放到 `./medical_input/`
2. 检查 `test.csv` 字段格式
3. 运行 `python run_agents.py --input ./medical_input/ --output ./medical_output/`
4. 查看 `processing_log.json` 确认处理结果
5. 抽查输出文件，确认无 `[需核实:]` 占位符

### 7.2 新手路径（首次使用）

1. 阅读「一、能力边界」了解工具包能做什么、不能做什么
2. 阅读「三、标准流程」的步骤 1-2，完成首次试运行
3. 阅读「六、FAQ 反模式」避免常见错误
4. 遇到问题时查阅「五、错误码体系」

### 7.3 进阶路径（日常使用）

1. 阅读「三、标准流程」的步骤 3-4，掌握批量执行和校验技巧
2. 阅读「四、置信度门控」理解占位符机制，建立数据质量意识
3. 根据附录 A 的专科代码表，自定义专科映射规则
4. 修改 `run_agents.py` 中的字段映射逻辑，适配特殊业务需求

### 7.4 专家路径（深度定制）

1. 阅读「三、标准流程」的输出规范，设计自定义输出模板
2. 扩展 51 个专科的模板规则，增加新的专科类型
3. 集成到现有医疗管理系统，通过 API 调用本工具包
4. 开发自动化校验脚本，将 `validate_results.py` 集成到 CI/CD 流程

---

## 附录 A：专科代码表（节选）

| 专科代码 | 专科名称 | 说明 |
|---------|---------|------|
| CARD | Cardiology | 心脏病学 |
| ORTH | Orthopedics | 骨科学 |
| NEUR | Neurology | 神经病学 |
| ONCL | Oncology | 肿瘤学 |
| PEDS | Pediatrics | 儿科学 |
| OBGY | Obstetrics/Gynecology | 妇产科学 |
| DERM | Dermatology | 皮肤病学 |
| PSYC | Psychiatry | 精神病学 |
| ... | ... | ... |

完整 51 个专科代码表见 `specialty_codes.json`。

---

## 附录 B：字段映射规则

| 标准字段 | 常见别名 | 数据类型 | 必填 |
|---------|---------|---------|------|
| `patient_id` | `pid`, `patient_no` | string | 是 |
| `visit_date` | `date`, `encounter_date` | date (YYYY-MM-DD) | 是 |
| `specialty_code` | `dept_code`, `specialty` | string | 是 |
| `diagnosis` | `dx`, `condition` | string | 否 |
| `provider_name` | `doctor`, `physician` | string | 否 |

---

## 用户协议

<!-- user-agreement-injected -->

**使用本 Skill 即表示您同意以下条款：**

1. **责任承担**：使用者自行承担使用本工具包的全部责任。因使用本工具包产生的任何直接或间接损失，包括但不限于数据错误、业务中断、合规风险，均由使用者自行承担。

2. **禁止反向工程**：使用者不得对本工具包进行反向工程、反编译、反汇编，不得尝试提取源代码、算法或底层逻辑。

3. **数据合规**：使用者须确保输入数据符合 HIPAA 及其他适用法规要求，不得上传包含受保护健康信息（PHI）的未脱敏数据。

4. **无担保**：本工具包按"现状"提供，不附带任何明示或暗示的担保，包括但不限于适销性、特定用途适用性和非侵权保证。

5. **争议解决**：因本协议产生的争议，适用中华人民共和国法律，由北京市朝阳区人民法院管辖。

---

## 许可证（License）

<!-- professional-license-embedded -->

**MIT License**

Copyright (c) 2025 原创作者（自持版权）

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
