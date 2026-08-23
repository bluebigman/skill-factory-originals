---
slug: healthcare-agents
name: healthcare-agents
displayName: 医疗行政 专科智能体 流程自动化
description: 面向美国医疗行政场景的51个专科AI智能体便携工具包。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 医政工坊
agent_created: true
trigger_words: ["healthcare agents","医疗行政智能体","医疗流程自动化","healthcare admin agents","医疗行政工作流","专科智能体","医疗办公自动化"]
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# healthcare-agents — 医疗行政专科智能体工具包

## 一、能力边界速查卡

### 1.1 能做什么

| 能力项 | 说明 | 适用对象 |
|--------|------|----------|
| 专科流程模拟 | 覆盖51个美国医疗行政专科场景（如前台接待、病历归档、保险核验、预约调度等） | 医疗行政人员、流程设计者 |
| 输入文件预处理 | 读取同目录下的待处理文件，识别命名规范并解析字段 | 批量处理前的数据准备 |
| 单样本试运行 | 对单条记录执行完整流程，输出字段级核对结果 | 首次使用、流程验证 |
| 批量执行 | 对全量数据执行统一流程，保留原始备份 | 日常批量作业 |
| 结果校验 | 抽查输出条目，比对关键字段与源数据一致性 | 质量抽检、审计 |

### 1.2 不能做什么

| 限制项 | 说明 |
|--------|------|
| 不处理跨专科混合任务 | 每个智能体仅针对单一专科场景，混合任务需拆分 |
| 不替代人工审核 | 输出结果需人工复核，尤其是涉及保险赔付、法律合规的字段 |
| 不处理非结构化手写文档 | 仅支持规范化的电子文件（CSV、JSON、TXT等） |
| 不提供临床诊断建议 | 本工具仅面向行政流程，不涉及任何临床判断 |
| 不保证数据绝对准确 | 输出质量取决于输入数据的完整性与规范性 |

### 1.3 适用对象

- 美国医疗机构的行政前台、保险核验员、病历管理员
- 医疗流程外包服务商的运营人员
- 医疗信息化系统的测试与验收人员

---

## 二、触发方式与场景映射

### 2.1 触发词

使用以下任一触发词即可激活本 Skill：

- `healthcare agents`
- `医疗行政智能体`
- `医疗流程自动化`
- `healthcare admin agents`
- `医疗行政工作流`
- `专科智能体`
- `医疗办公自动化`

### 2.2 场景映射表

| 大白话场景 | 触发词示例 | 实际行为 |
|------------|------------|----------|
| “帮我把这批预约记录跑一遍流程” | `医疗流程自动化` | 执行批量预约调度流程 |
| “这个保险核验文件帮我看看格式对不对” | `医疗行政智能体` | 单样本试运行 + 字段核对 |
| “我想知道51个专科里有没有适合病历归档的” | `专科智能体` | 列出能力清单并匹配场景 |
| “这批数据跑完了，帮我抽查几个对不对” | `healthcare admin agents` | 执行结果校验流程 |
| “新来的同事不会用，怎么上手？” | `医疗行政工作流` | 输出新手引导路径 |

---

## 三、标准操作流程

### 3.1 前置条件

| 条件项 | 要求 |
|--------|------|
| 文件格式 | CSV / JSON / TXT，UTF-8 编码 |
| 命名规范 | 文件名需包含专科标识（如 `cardiology_20250101.csv`） |
| 目录结构 | 待处理文件与输出文件分目录存放 |
| 备份要求 | 批量执行前必须保留原始文件副本 |

### 3.2 执行步骤

**第一步：准备输入**

1. 将待处理文件放入 `input/` 目录。
2. 确认文件名符合 `{专科名}_{日期}.{ext}` 格式。
3. 检查文件首行是否包含表头（字段名）。

**第二步：单样本试运行**

1. 从输入文件中取第一条记录。
2. 执行 `healthcare agents --selftest` 命令。
3. 核对输出字段是否完整、格式是否符合预期。

**第三步：批量执行**

1. 确认试运行无误后，执行 `healthcare agents` 主命令。
2. 系统自动遍历 `input/` 目录下所有文件。
3. 输出结果写入 `output/` 目录，文件名追加 `_processed` 后缀。

**第四步：校验结果**

1. 从输出文件中随机抽取 5-10 条记录。
2. 比对关键字段（如患者ID、日期、专科代码）与源文件一致性。
3. 若发现异常，定位错误码并参照第五章处理。

### 3.3 输出规范

| 输出项 | 格式 | 示例 |
|--------|------|------|
| 处理报告 | JSON | `{"total": 120, "success": 118, "failed": 2, "errors": [...]}` |
| 结果文件 | CSV | 与输入同结构，追加 `status` 列 |
| 错误日志 | TXT | 每行一条错误记录，含时间戳与错误码 |

---

## 四、置信度门控

当输入信息不足以支撑准确输出时，本 Skill 遵循以下规则：

1. **不编造数据**：缺失字段一律输出 `[需核实:字段名]` 占位符。
2. **不推测结论**：若专科标识无法识别，输出 `[需核实:专科类型]` 并跳过该记录。
3. **不自动补全**：日期格式不明确时，保留原始格式并标记 `[需核实:日期格式]`。
4. **人工介入提示**：当错误率超过 10% 时，输出建议人工复核的提示。

**示例**：

```json
{
  "patient_id": "P-1024",
  "appointment_date": "[需核实:日期格式]",
  "specialty": "[需核实:专科类型]",
  "status": "pending_review"
}
```

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| `E001` | 文件不存在 | “未找到指定输入文件，请检查路径” | 确认文件路径与文件名 |
| `E002` | 格式不支持 | “仅支持 CSV/JSON/TXT 格式” | 转换文件格式后重试 |
| `E003` | 字段缺失 | “缺少必填字段：患者ID” | 补充字段后重新执行 |
| `E004` | 专科标识无效 | “无法识别专科类型，请检查文件名” | 修正文件名中的专科标识 |
| `E005` | 批量执行中断 | “批量处理在第N条记录处中断” | 查看错误日志，修复后从断点继续 |
| `E006` | 输出目录不可写 | “无法写入输出目录，请检查权限” | 修改目录权限或更换路径 |

---

## 六、FAQ 反模式对照

| 常见坑 | 反模式（错误做法） | 正模式（正确做法） |
|--------|-------------------|-------------------|
| 跳过试运行直接批量 | 直接对全量数据执行，导致错误扩散 | 先跑单样本，确认无误后再批量 |
| 覆盖原始文件 | 输出直接覆盖输入文件 | 保留原始备份，输出到独立目录 |
| 忽略错误日志 | 只看成功条数，不看失败原因 | 逐条查看错误日志，分类处理 |
| 混合专科数据 | 一个文件包含多个专科记录 | 按专科拆分文件，分别执行 |
| 依赖自动结果 | 不人工复核，直接使用输出 | 按比例抽检，关键字段人工确认 |

---

## 七、渐进式披露路径

### 7.1 新手速查卡（30秒上手）

1. 把文件放进 `input/` 目录。
2. 跑 `healthcare agents --selftest` 试一条。
3. 没问题就跑 `healthcare agents` 全量处理。
4. 打开 `output/` 目录看结果。

### 7.2 进阶阅读路径

| 层级 | 阅读内容 | 适合人群 |
|------|----------|----------|
| L1 基础 | 第一章（能力边界）+ 第三章（标准流程） | 首次使用者 |
| L2 进阶 | 第四章（置信度门控）+ 第五章（错误码） | 日常操作者 |
| L3 专家 | 第六章（FAQ 反模式）+ 自定义流程设计 | 流程管理者、二次开发者 |

---

## 八、用户协议

<!-- user-agreement-injected -->

**使用本 Skill 即表示您同意以下条款：**

1. **责任承担**：使用者自行承担因使用本 Skill 产生的全部责任，包括但不限于数据处理结果、业务决策后果及合规风险。
2. **禁止反向工程**：不得对本 Skill 进行反向工程、反编译、破解或试图提取底层算法。
3. **合规使用**：使用者须确保使用场景符合美国 HIPAA 及相关医疗数据保护法规。
4. **无担保声明**：本 Skill 按“现状”提供，不附带任何明示或暗示的担保。

---

## 九、许可证（License）

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
