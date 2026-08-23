---
slug: goreporter
name: goreporter
displayName: 报表解析 数据可视化 结构化输出
description: 将用户提供的报表数据转化为结构化结果，支持批量处理与置信度标注。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: DataForge Studio
agent_created: true
trigger_words: ["报表", "数据可视化", "goreporter", "数据报表", "结构化输出"]
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# goreporter 技能文档

## 一、能力边界速查卡

### 1.1 能做与不能做

| 维度 | 能做 | 不能做 |
|------|------|--------|
| 数据输入 | 用户提供的 CSV、JSON、Excel、URL 链接 | 主动爬取未授权的第三方数据源 |
| 信息提取 | 识别表格字段、数值指标、时间序列、分类维度 | 推断数据背后的业务含义或因果逻辑 |
| 格式转换 | 将非结构化报表转为结构化 JSON/Markdown 表格 | 生成图表图片或交互式可视化页面 |
| 批量处理 | 支持多文件同目录批量解析，输出合并结果 | 跨目录递归扫描或自动发现文件 |
| 自定义输出 | 按用户指定的字段顺序、命名规则输出 | 自动适配所有私有格式（需用户提供模板） |

### 1.2 适用对象

- **适用**：标准格式报表（月度销售表、运营周报、日志统计）、字段命名清晰的 CSV/Excel 文件、公开可访问的数据 URL。
- **不适用**：扫描件/图片中的手写数据、加密文件、字段语义模糊且无说明文档的数据。

---

## 二、触发方式与场景映射

### 2.1 触发词

- 核心触发词：`报表`、`数据可视化`、`goreporter`
- 补充同义场景词：`数据整理`、`报表解析`、`结构化输出`

### 2.2 场景映射表

| 用户说（大白话） | 实际触发动作 |
|------------------|--------------|
| "帮我把这个销售报表整理成表格" | 解析文件 → 识别字段 → 输出 Markdown 表格 |
| "这个 URL 里的数据能提取出来吗" | 读取 URL → 解析 HTML/JSON → 结构化输出 |
| "我有 20 个 CSV 要合并处理" | 批量读取 → 统一 schema → 合并输出 |
| "报表里有些数据不确定，帮我标出来" | 解析时对缺失/异常值标注 `[需核实:字段名]` |

---

## 三、标准处理流程

### 3.1 前置条件

| 条件项 | 要求 |
|--------|------|
| 文件格式 | .csv / .json / .xlsx（≤10MB） |
| 命名规范 | 同批次文件需遵循统一前缀，如 `sales_2024_01.csv` |
| 字段说明 | 若字段名非标准英文/中文，需提供字段映射表 |
| 环境要求 | 文件与 Skill 运行目录一致，或提供可访问的 URL |

### 3.2 执行步骤

1. **输入确认**：向用户复述输入来源（文件路径/URL）、文件数量、期望输出格式。
2. **单样本试运行**：取第一个文件执行解析，输出字段清单与样例数据。
3. **字段映射确认**：与用户核对字段识别结果，修正别名或忽略项。
4. **批量执行**：确认无误后，对全量数据执行解析，生成合并结果。
5. **置信度标注**：对缺失值、格式异常、超出合理范围的数据，追加 `[需核实:字段名]` 标记。
6. **输出交付**：按约定格式输出，附字段完整性自查表。

### 3.3 输出规范

- **默认格式**：Markdown 表格 + JSON 双格式输出。
- **字段结构**：`序号 | 原始字段名 | 标准化字段名 | 数据类型 | 置信度 | 原始值`
- **置信度等级**：
  - `高`：字段完整、类型匹配、值在合理范围
  - `中`：字段存在但格式异常（如日期格式不统一）
  - `低`：字段缺失或值明显异常，需人工复核

---

## 四、置信度门控机制

### 4.1 规则说明

- 当某字段无法从源数据中可靠提取时，**不得**编造或猜测值。
- 统一使用占位符 `[需核实:字段名]` 替代，并在输出末尾附「待核实清单」。

### 4.2 示例

```json
{
  "record_id": 1024,
  "sales_amount": 15800.50,
  "region": "[需核实:region]",
  "confidence": {
    "sales_amount": "高",
    "region": "低"
  }
}
```

---

## 五、错误码体系

| 错误码 | 场景描述 | 提示话术 | 修正步骤 |
|--------|----------|----------|----------|
| E001 | 文件格式不支持 | "当前文件类型为 .pdf，仅支持 .csv/.json/.xlsx" | 请转换格式后重试 |
| E002 | 字段映射冲突 | "字段 'date' 与 '日期' 疑似同一字段，请确认" | 提供字段映射表或指定保留字段 |
| E003 | 数据量超限 | "文件行数超过 10 万行，超出处理上限" | 拆分文件或提供筛选条件 |
| E004 | URL 访问失败 | "目标 URL 返回 404，请检查链接有效性" | 更换链接或下载后上传 |
| E005 | 批量文件命名不一致 | "检测到 3 种命名前缀，请统一后重试" | 重命名文件或分批次执行 |

---

## 六、FAQ 反模式对照

| 常见坑 | 反模式（错误做法） | 正确做法 |
|--------|--------------------|----------|
| 字段名猜测 | 看到 "amt" 就默认是金额，不确认 | 先输出字段清单，与用户确认后再映射 |
| 缺失值静默处理 | 空值直接填 0 或 "N/A" | 标注 `[需核实:字段名]`，由用户决定 |
| 批量处理不校验 | 20 个文件直接合并，不抽查 | 先跑 1 个样本，再全量执行，最后抽查 3 条 |
| 日期格式统一 | 混用 2024/01/01 和 01-01-2024 不提示 | 统一为 ISO 8601，并在输出中标注转换规则 |
| 忽略异常值 | 销售额为负数直接保留 | 标记 `[需核实:sales_amount]`，提示用户确认 |

---

## 七、渐进式阅读路径

### 7.1 新手速查（30 秒上手）

1. 把文件放到指定目录，命名统一。
2. 说："解析这个报表，输出 Markdown 表格"。
3. 收到字段清单后，确认或修正。
4. 获取最终结构化结果。

### 7.2 进阶用法（自定义配置）

- **自定义字段映射**：提供 JSON 映射文件，如 `{"原始名": "标准名"}`。
- **批量处理**：同目录下多个文件，自动合并输出。
- **输出格式定制**：指定 JSON 字段顺序、嵌套层级、是否包含原始值。

---

## 八、用户协议

<!-- user-agreement-injected -->

**使用须知：**

1. 本 Skill 仅供学习与参考用途，使用者应自行承担使用本工具产生的全部责任。
2. 禁止对本 Skill 进行反向工程、破解、二次分发或用于商业盈利目的。
3. 使用者应确保输入数据的合法性与授权，不得上传涉及隐私、机密或违反法律法规的内容。
4. 本 Skill 不对输出结果的准确性、完整性或适用性作任何明示或暗示的保证。
5. 如因使用本 Skill 产生任何直接或间接损失，作者及贡献者不承担任何责任。

---

## 九、许可证（License）

<!-- professional-license-embedded -->

**MIT License**

Copyright (c) 2024 原创作者（自持版权）

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

*文档版本：1.0.0 | 最后更新：2024 年 | 生成方式：AI 辅助*
