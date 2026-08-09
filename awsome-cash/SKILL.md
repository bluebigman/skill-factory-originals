---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: awsome-cash
name: awsome-cash
displayName: 财务数据清洗 结构化转换 批量处理
description: 将杂乱财务数据、文件或链接解析为规范结构化结果，支持批量与置信度标注。
version: 1.0.1
rules_version: cpr-20260809-n251
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/awsome-cash
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: DataForge Studio
agent_created: true
trigger_words: ["awsome-cash", "数据清洗", "结构化转换", "财务数据解析", "批量格式化", "信息抽取"]
---

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->


> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# awsome-cash 技能文档

## 一、能力边界速查卡

本技能用于将非结构化的财务相关数据（文本、表格文件、网页链接）转换为符合指定 schema 的结构化结果。以下用一页纸说明边界。

| 维度 | 说明 |
|------|------|
| **核心能力** | ① 解析文本/CSV/Excel/URL 中的关键字段；② 按用户指定的字段结构重组输出；③ 对不确定字段标注 `[需核实:字段名]`；④ 支持多文件批量处理；⑤ 输出 JSON / CSV / Markdown 表格 |
| **适用对象** | 财务对账记录、交易流水、发票信息、预算报表、网页中的财务表格 |
| **不处理** | ① 非财务类通用文本摘要；② 图像中的文字识别（OCR）；③ 数据真实性核验；④ 跨表关联计算（如自动汇总、透视） |
| **输入限制** | 单次处理 ≤ 50 个文件；单文件 ≤ 5MB；URL 需可公开访问 |
| **输出格式** | 默认 JSON，可选 CSV / Markdown 表格；字段结构由用户指定或使用内置默认 schema |

**内置默认 schema（当用户未指定字段时）：**

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `record_id` | string | 记录唯一标识，缺失时自动生成 |
| `date` | string (YYYY-MM-DD) | 交易或记录日期 |
| `amount` | number | 金额数值（不含货币符号） |
| `currency` | string (ISO 4217) | 货币代码，默认 CNY |
| `counterparty` | string | 交易对手方名称 |
| `category` | string | 自动归类：收入/支出/转账/未知 |
| `description` | string | 原始描述或备注 |
| `confidence` | number (0-1) | 整体置信度，低于 0.7 时逐字段标注 |

---

## 二、触发方式与场景映射

当你的输入包含以下关键词或意图时，本技能自动激活：

| 触发场景（大白话） | 触发词示例 | 技能行为 |
|-------------------|-----------|---------|
| "帮我把这些流水整理成表格" | 流水整理、对账、格式化 | 解析文本/文件 → 输出结构化表格 |
| "这个网页里的财务数据提取出来" | 网页提取、URL解析、爬取表格 | 抓取 URL → 提取表格 → 结构化输出 |
| "批量处理这几个 CSV 文件" | 批量转换、多文件处理、合并 | 遍历文件 → 逐文件解析 → 合并输出 |
| "把发票信息录入系统" | 发票解析、字段提取、录入 | 识别发票关键字段 → 按 schema 输出 |
| "运行自检" | selftest、自检、测试 | 执行内置自检流程，验证环境可用性 |

**命令行接口（CLI）调用方式：**

```bash
# 查看版本
awsome-cash --version

# 运行自检
awsome-cash --selftest
```

---

## 三、标准处理流程

### 前置条件

1. 输入数据格式明确（文本、CSV、Excel、URL 之一）
2. 若需自定义输出字段，请提供字段清单及类型
3. 批量处理时，文件命名需包含可区分的前缀或序号

### 执行步骤

**步骤 1：输入确认**

- 接收用户输入，识别来源类型（文本/文件/URL）
- 若输入为空或格式不明，返回错误码 `E1001` 并附正确示例

**步骤 2：内容解析**

- 文本输入：按行分割，识别分隔符（逗号、制表符、竖线）
- 文件输入：读取文件头，判断编码（UTF-8/GBK），解析表格结构
- URL 输入：请求页面，定位 `<table>` 或列表结构，提取行数据

**步骤 3：字段映射**

- 将解析出的原始列名与目标 schema 字段进行映射
- 映射规则优先级：精确匹配 > 同义词匹配（如"金额"→`amount`）> 用户指定映射
- 无法映射的字段放入 `unmapped_fields` 数组，不丢弃

**步骤 4：数据清洗**

- 金额字段：去除货币符号、千分位逗号，转换为 number
- 日期字段：统一为 `YYYY-MM-DD`，无法解析时标注 `[需核实:date]`
- 空值处理：保留为空字符串，不填充默认值

**步骤 5：置信度评估**

- 逐字段计算置信度：完全匹配=1.0，同义词匹配=0.9，需人工确认=0.5，无法解析=0.0
- 整体置信度 = 所有字段置信度的算术平均值
- 置信度 < 0.7 时，在输出中标注 `[需核实:字段名]` 占位

**步骤 6：输出生成与自查**

- 按用户指定格式（JSON/CSV/Markdown）生成输出
- 自查清单：字段完整性（无遗漏）、格式正确性（类型匹配）、置信度标注齐全
- 若自查发现问题，返回错误码并附修正建议

### 输出规范

**成功输出示例（JSON）：**

```json
{
  "status": "success",
  "record_count": 3,
  "schema_version": "1.0",
  "data": [
    {
      "record_id": "R001",
      "date": "2026-01-15",
      "amount": 1280.50,
      "currency": "CNY",
      "counterparty": "某某科技有限公司",
      "category": "收入",
      "description": "软件服务费",
      "confidence": 0.95
    },
    {
      "record_id": "R002",
      "date": "[需核实:date]",
      "amount": 356.00,
      "currency": "CNY",
      "counterparty": "未知",
      "category": "支出",
      "description": "办公用品采购",
      "confidence": 0.62
    }
  ],
  "unmapped_fields": ["备注2"],
  "warnings": ["R002 日期无法解析，请人工确认"]
}
```

**失败输出示例：**

```json
{
  "status": "error",
  "error_code": "E1001",
  "message": "输入内容为空或无法识别为有效数据格式",
  "hint": "请提供文本、CSV/Excel 文件路径或可访问的 URL"
}
```

---

## 四、置信度门控机制

本技能遵循"不编造"原则，对不确定信息显式标注，而非猜测填充。

| 置信度区间 | 处理策略 | 输出表现 |
|-----------|---------|---------|
| 0.9 - 1.0 | 直接输出 | 正常字段值 |
| 0.7 - 0.9 | 输出并提示 | 字段值后附加 `(需复核)` 标记 |
| 0.0 - 0.7 | 占位符替换 | 字段值替换为 `[需核实:字段名]` |
| 无法解析 | 占位符 + 警告 | `[需核实:字段名]` 并加入 `warnings` 数组 |

**触发置信度门控的典型场景：**

- 日期格式非标准（如"2026年1月15日"、"15/01/26"）
- 金额包含多种货币符号且未明确币种
- 对手方名称包含缩写或简称
- 分类无法自动判定（收入/支出/转账均有可能）

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|---------|---------|
| `E1001` | 输入为空或格式无法识别 | "无法识别输入内容，请提供文本、文件路径或 URL" | ① 检查输入是否为空；② 确认文件格式为 CSV/Excel；③ 确认 URL 可访问 |
| `E1002` | 文件读取失败 | "文件读取失败，请检查路径和权限" | ① 确认文件存在；② 检查文件权限；③ 确认文件大小 ≤ 5MB |
| `E1003` | 编码不支持 | "文件编码无法识别，请转换为 UTF-8 或 GBK" | ① 使用文本编辑器另存为 UTF-8；② 重新提交 |
| `E1004` | 字段映射冲突 | "多个原始列映射到同一目标字段，请指定优先级" | ① 提供字段映射优先级；② 或删除冗余列 |
| `E1005` | 批量处理中断 | "批量处理在第 N 个文件处中断，已处理结果已保存" | ① 查看已处理部分；② 修正问题文件后重新提交 |
| `E2001` | 输出格式不支持 | "不支持的输出格式，可选：JSON、CSV、Markdown" | ① 检查输出格式参数；② 重新指定 |

---

## 六、FAQ 与反模式对照

### 常见坑 1：输入包含混合格式

**反模式**：直接拼接不同格式的文本，期望自动识别。
**正确做法**：按来源分块提交，或使用分隔符明确区分。

### 常见坑 2：日期格式不统一

**反模式**：期望技能自动识别所有日期格式。
**正确做法**：预处理时统一日期格式，或在输入中注明日期格式。

### 常见坑 3：金额单位不明确

**反模式**：金额数值后无货币单位，期望默认处理。
**正确做法**：在输入中标注货币单位，或使用 `currency` 字段显式指定。

### 常见坑 4：依赖技能做数据真实性核验

**反模式**：要求技能判断某笔交易是否真实存在。
**正确做法**：技能仅做格式转换和字段提取，真实性需通过银行对账单等外部渠道核验。

### 常见坑 5：批量处理时文件命名无规律

**反模式**：文件命名随意，期望技能自动识别顺序。
**正确做法**：使用序号或日期前缀命名文件，便于结果追溯。

---

## 七、渐进式阅读路径

### 新手快速上手（3 分钟）

1. 阅读「能力边界速查卡」了解能做什么
2. 准备一份 CSV 或文本格式的财务流水
3. 直接提交，使用默认 schema 获取 JSON 输出
4. 查看 `confidence` 字段，低于 0.7 的字段人工确认

### 进阶用户（10 分钟）

1. 自定义输出字段：提交时附带字段清单及类型
2. 批量处理：将多个文件放入同一目录，一次性提交
3. URL 提取：提供公开网页链接，自动提取表格数据
4. 错误处理：熟悉错误码体系，快速定位问题

### 高级用户（深度定制）

1. 使用 CLI 接口 `--selftest` 验证环境
2. 结合外部工具（如 pandas）对输出结果做二次加工
3. 将本技能嵌入自动化流水线，处理周期性对账任务

---

## 八、用户协议

<!-- user-agreement-injected -->

**使用本 Skill 即表示您同意以下条款：**

1. **责任承担**：使用者自行承担因使用本 Skill 产生的全部责任。本 Skill 提供的数据处理结果仅供参考，不构成任何形式的财务建议或法律意见。
2. **禁止反向工程**：不得对本 Skill 的底层逻辑、提示词结构、评分机制进行反向工程、破解、篡改或二次分发。
3. **数据安全**：使用者应确保输入数据不包含敏感个人信息或受保护数据。本 Skill 不承担数据泄露责任。
4. **服务变更**：本 Skill 可能随时更新或下线，不另行通知。

---

## 九、许可证（License）

<!-- professional-license-embedded -->

**MIT License**

Copyright (c) 2026 DataForge Studio

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

*文档版本：1.0.0 | 最后更新：2026-08-09*
