---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: ruflo
name: ruflo
displayName: 数据流解析 多智能体编排 批量转换
description: 将任意数据源解析为结构化结果，支持多智能体协同与批量处理。
version: 1.0.4
rules_version: cpr-20260819-n551
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/ruflo
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 流川工作室
agent_created: true
trigger_words: ["ruflo", "多智能体", "工作流编排", "数据转换", "批量处理", "数据解析", "结构化输出"]
---

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->


> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# ruflo Skill 文档

## 一、能力边界：一页纸速查卡

### 1.1 能做什么

| 能力项 | 说明 | 典型场景 |
|--------|------|----------|
| 数据源接入 | 读取同目录下的 CSV、JSON、TXT、Markdown 表格等常见格式文件 | 日志文件转表格、爬虫结果清洗 |
| 结构化解析 | 将非结构化文本按字段规则拆解为键值对或表格行 | 合同条款抽取、邮件内容归档 |
| 多智能体协同 | 将解析任务拆分为多个子任务，分派给不同处理单元并行执行 | 大批量文件分片处理、多维度字段提取 |
| 工作流编排 | 按预设顺序串联「读取 → 解析 → 校验 → 输出」各环节 | 每日定时数据管道、增量数据合并 |
| 批量处理 | 对同一目录下多个文件执行相同解析逻辑，输出合并结果 | 月度报表汇总、多客户信息整理 |
| 试运行与回滚 | 支持单样本先行验证，保留原始文件备份以便回溯 | 新规则上线前的灰度测试 |

### 1.2 不能做什么

| 限制项 | 说明 |
|--------|------|
| 不处理跨目录文件 | 所有待处理文件必须放置于同一目录，不支持递归扫描子目录 |
| 不自动识别编码 | 文件编码需为 UTF-8（无 BOM），其他编码需预先转换 |
| 不进行语义理解 | 仅按字段规则做结构拆分，不判断内容含义对错 |
| 不生成业务结论 | 输出为结构化数据，不附带分析报告或决策建议 |
| 不修改原始文件 | 所有操作均在副本上进行，原文件始终保留 |

### 1.3 适用对象

- 需要将零散文本/表格数据整理为统一格式的运营人员
- 需要批量处理多个同构数据文件的开发人员
- 需要将解析任务分派给多个处理单元的工作流设计者

---

## 二、触发方式

### 2.1 触发词

`ruflo`、`多智能体`、`工作流编排`、`数据转换`、`批量处理`、`数据解析`、`结构化输出`

### 2.2 场景映射表

| 你说的话（大白话） | 触发动作 |
|-------------------|----------|
| "帮我把这堆 CSV 合并成一个标准表" | 执行批量解析 + 合并输出 |
| "这个日志文件太乱了，整理成表格" | 执行单文件结构化解析 |
| "我有 500 个文件要处理，分给几个智能体并行跑" | 执行多智能体协同批量处理 |
| "先拿一个文件试试，看看效果对不对" | 执行单样本试运行 |
| "上次跑的结果不对，帮我回滚重来" | 执行备份恢复 + 重新解析 |

---

## 三、标准流程

### 3.1 前置条件

| 条件 | 要求 | 检查方式 |
|------|------|----------|
| 文件位置 | 所有待处理文件位于同一目录 | `ls -la` 确认无子目录引用 |
| 命名规范 | 文件名前缀一致，如 `input_001.csv`、`input_002.csv` | 使用 `ls | grep "前缀"` 验证 |
| 编码格式 | UTF-8 无 BOM | `file -i 文件名` 查看 charset |
| 字段一致性 | 同批文件表头或字段顺序一致 | 随机抽查 2-3 个文件比对 |
| 原始备份 | 已复制一份到 `backup/` 目录 | `cp -r 源目录 backup/` |

### 3.2 执行步骤

#### 步骤 1：准备输入

将待处理文件放入同一目录，确认命名规范一致。

```bash
mkdir -p ./data/input ./data/backup
cp ./raw/*.csv ./data/input/
cp -r ./data/input ./data/backup/
```

#### 步骤 2：试运行

先用单个样本执行，核对输出字段与格式。

```bash
ruflo parse --file ./data/input/input_001.csv --config ./config.yaml --output ./data/output_sample.json
```

检查输出：

```bash
cat ./data/output_sample.json | jq '.fields'
```

确认字段名、类型、顺序与预期一致。

#### 步骤 3：批量执行

确认无误后对全量数据执行，并保留原始文件备份。

```bash
ruflo batch --input ./data/input/ --config ./config.yaml --output ./data/output_all.json --workers 4
```

参数说明：

| 参数 | 必填 | 默认值 | 说明 |
|------|------|--------|------|
| `--input` | 是 | 无 | 输入目录路径 |
| `--config` | 是 | 无 | 解析规则配置文件（YAML/JSON） |
| `--output` | 是 | 无 | 输出文件路径 |
| `--workers` | 否 | 1 | 并行处理线程数（多智能体模式） |
| `--dry-run` | 否 | false | 仅打印执行计划，不实际运行 |

#### 步骤 4：校验结果

抽查输出条目，核对关键字段与源数据一致。

```bash
ruflo verify --output ./data/output_all.json --sample 10
```

校验规则：

- 随机抽取 10 条记录
- 对比源文件中对应行的原始文本
- 确认字段值无丢失、无错位、无类型错误

### 3.3 输出规范

| 输出项 | 格式 | 说明 |
|--------|------|------|
| 结构化结果 | JSON Lines（每行一条记录） | 每条记录包含 `id`、`source_file`、`parsed_fields` |
| 校验报告 | Markdown 表格 | 包含样本数、通过数、失败数、失败原因 |
| 日志 | 纯文本 | 记录每个文件的处理时间、状态、耗时 |

---

## 四、置信度门控

当输入信息不足以确定某个字段值时，**禁止编造**。使用以下占位符标记：

| 占位符 | 含义 | 使用场景 |
|--------|------|----------|
| `[需核实:字段名]` | 该字段值无法从源数据中确定 | 源文件该列为空、格式异常、存在多种可能 |
| `[需核实:来源]` | 无法确认数据来源 | 多个文件字段冲突且无优先级规则 |
| `[需核实:格式]` | 无法确定输出格式 | 日期格式不统一、数字精度不一致 |

示例：

```json
{"id": "001", "name": "张三", "amount": "[需核实:金额]", "date": "2024-01-15"}
```

处理原则：

1. 出现占位符时，校验报告必须列出对应记录 ID 和字段名
2. 用户需手动补充确认后，重新执行该条记录的解析
3. 未确认前，该记录不参与最终合并输出

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| `E001` | 文件不存在 | "未找到指定文件，请检查路径" | 1. 确认路径拼写；2. 检查文件是否被移动 |
| `E002` | 编码不支持 | "文件编码非 UTF-8，请转换后重试" | 1. 使用 `iconv -f GBK -t UTF-8 文件 > 新文件` 转换 |
| `E003` | 字段缺失 | "源数据缺少必要字段：xxx" | 1. 检查表头；2. 补充缺失列或调整配置 |
| `E004` | 字段类型错误 | "字段 xxx 期望为数字，实际为文本" | 1. 检查源数据；2. 修改配置中的类型映射 |
| `E005` | 配置解析失败 | "配置文件格式错误，请检查 YAML/JSON 语法" | 1. 使用 `yq` 或 `jq` 验证格式 |
| `E006` | 输出目录无权限 | "无法写入输出文件，请检查目录权限" | 1. `chmod +w` 目录；2. 更换输出路径 |
| `E007` | 批量任务中断 | "批量处理在第 N 个文件处中断" | 1. 查看日志定位失败文件；2. 修复后从断点续跑 |

---

## 六、FAQ 反模式

| 常见坑 | 反模式描述 | 正确做法 |
|--------|------------|----------|
| 跳过试运行 | 直接对全量数据执行，发现字段映射错误后需全部重跑 | 始终先跑单样本，确认无误再批量 |
| 覆盖原始文件 | 将输出直接写回源目录，导致原始数据丢失 | 输出到独立目录，源目录只读 |
| 忽略编码问题 | 混用多种编码文件，解析结果出现乱码 | 批量处理前统一转换为 UTF-8 |
| 字段名硬编码 | 配置中写死字段名，源文件表头微调即报错 | 使用字段别名映射，支持模糊匹配 |
| 并行度过高 | 小文件也开 16 线程，资源浪费且日志混乱 | 文件数 < 50 时使用 `--workers 2` |

---

## 七、渐进式披露

### 7.1 速查卡（新手必读）

1. 所有文件放同一目录
2. 先跑一个文件试效果
3. 确认无误再批量跑
4. 原始文件永远备份

### 7.2 分层次阅读路径

| 读者类型 | 建议阅读内容 | 目标 |
|----------|--------------|------|
| 新手（首次使用） | 速查卡 + 标准流程步骤 1-2 | 完成一次单文件解析 |
| 进阶（日常使用） | 标准流程全部 + 错误码体系 | 独立完成批量任务并处理常见错误 |
| 高级（定制开发） | 能力边界 + 置信度门控 + 配置详解 | 自定义解析规则，集成到现有工作流 |

### 7.3 配置示例

```yaml
# config.yaml
parser:
  delimiter: ","
  encoding: "utf-8"
  fields:
    - name: "id"
      type: "string"
      required: true
    - name: "amount"
      type: "number"
      required: false
      default: 0
    - name: "date"
      type: "date"
      format: "%Y-%m-%d"
  skip_header: true
output:
  format: "jsonl"
  include_source: true
```

---

## 八、用户协议

<!-- user-agreement-injected -->

**使用 ruflo Skill 即表示您同意以下条款：**

1. **责任承担**：使用者自行承担因使用本 Skill 产生的全部责任，包括但不限于数据解析错误、数据丢失、业务决策失误等后果。Skill 提供方不对任何直接或间接损失负责。

2. **数据安全**：使用者应确保待处理数据不包含违反法律法规的内容。本 Skill 不收集、不上传任何用户数据，所有处理均在本地完成。

3. **禁止反向工程**：使用者不得对本 Skill 的底层实现进行反向工程、反编译、破解或试图提取源代码逻辑（法律法规另有规定的除外）。

4. **无担保声明**：本 Skill 按"现状"提供，不附带任何明示或暗示的担保，包括但不限于适销性、特定用途适用性和非侵权保证。

5. **协议更新**：Skill 提供方保留随时修改本协议的权利，修改后的协议将在更新版本中公布。

---

## 九、许可证（License）

<!-- professional-license-embedded -->

**MIT License**

Copyright (c) 2026 流川工作室

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

**版本记录**

| 版本 | 日期 | 变更内容 |
|------|------|----------|
| 1.0.0 | 2026-08-19 | 初始版本发布 |

---

*本 Skill 由 AI 辅助生成，仅供参考。使用前请阅读相关文档。*
