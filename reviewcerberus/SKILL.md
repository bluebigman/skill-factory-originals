---
slug: reviewcerberus
name: reviewcerberus
displayName: 数据审查 三头犬 结构化校验
description: 将用户提供的任意数据源解析为结构化结果，标注置信度并输出规范格式。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 林砚秋
agent_created: true
trigger_words: ["reviewcerberus", "数据审查", "结构化校验", "数据解析", "格式转换"]
---

> 本内容由 AI 生成，仅供学习参考 <!-- ai-generated-notice -->

# reviewcerberus 技能文档

本 Skill 由 AI 辅助生成，仅供参考。使用前请确认你的数据合规性与安全性。

---

## 一、能力边界：一页纸速查卡

### 1.1 能做（5 项核心能力）

| 编号 | 能力项 | 说明 |
|------|--------|------|
| C1 | 多源输入解析 | 支持用户粘贴文本、上传文件（.txt/.csv/.json/.md）、提供 URL 链接三种输入方式 |
| C2 | 关键信息提取 | 从原始数据中抽取实体、数值、日期、状态等关键字段，保留上下文关联 |
| C3 | 结构化输出 | 按约定 schema 输出 JSON 或 Markdown 表格，字段名与类型固定 |
| C4 | 置信度标注 | 每个输出字段附带 confidence 等级（high/medium/low），低置信度时明确提示 |
| C5 | 批量处理与格式定制 | 支持多文件顺序处理；允许用户自定义输出字段子集或排序规则 |

### 1.2 不能做（明确拒绝的场景）

| 编号 | 拒绝项 | 原因 |
|------|--------|------|
| R1 | 不执行代码或脚本 | 本技能仅做文本解析与格式转换，不运行任何程序 |
| R2 | 不访问需登录的私有系统 | 仅处理用户直接提供的数据，不主动抓取受保护资源 |
| R3 | 不进行语义判断或情感分析 | 只做结构化提取，不推断意图、情绪或隐含含义 |
| R4 | 不保证数据准确性 | 输出基于输入内容，若源数据本身有误，结果同样有误 |
| R5 | 不处理二进制文件 | 仅支持纯文本类格式，不支持图片、音频、视频等 |

### 1.3 适用对象

- 需要将零散数据整理为统一格式的运营人员
- 需要批量校验数据字段完整性的测试工程师
- 需要快速预览 URL 内容结构的调研者
- 学习数据解析与格式规范的学生

---

## 二、触发方式：场景映射表

当你的需求匹配以下任一场景时，可直接使用本技能：

| 触发词/短语 | 典型场景 | 示例说法 |
|-------------|----------|----------|
| reviewcerberus | 直接调用技能 | "用 reviewcerberus 处理这个文件" |
| 数据审查 | 检查数据格式是否统一 | "帮我审查一下这批数据的格式" |
| 结构化校验 | 验证字段是否齐全 | "校验一下这些记录里有没有缺字段" |
| 数据解析 | 从文本中提取关键信息 | "把这段文字里的日期和金额都提取出来" |
| 格式转换 | 将非标准格式转为标准格式 | "把这个 CSV 转成 JSON 格式" |
| 批量处理 | 多个文件统一处理 | "把这 10 个文件都跑一遍，输出统一格式" |

**大白话示例**：

- "我有一堆乱七八糟的笔记，帮我整理成表格" → 触发 C1+C3
- "这个网页链接里的内容，帮我提取标题和发布时间" → 触发 C1+C2+C3
- "检查一下这些数据里有没有空值或格式不对的" → 触发 C2+C4

---

## 三、标准流程：前置条件 → 执行步骤 → 输出规范

### 3.1 前置条件

| 条件项 | 要求 |
|--------|------|
| 输入格式 | 文本（≤1MB）、.txt/.csv/.json/.md 文件、可公开访问的 URL |
| 命名规范 | 多文件批量处理时，文件名需包含序号或批次标识（如 `batch_01.csv`） |
| 环境要求 | 无需安装任何依赖，纯文本处理 |
| 数据合规 | 用户须确保拥有数据的使用权，不得包含敏感个人信息 |

### 3.2 执行步骤（分步编号）

**Step 1：输入确认**

- 明确输入来源（文本/文件/URL）及数量（单条/批量）
- 确认输出格式偏好（默认 JSON，可选 Markdown 表格）
- 确认是否需要自定义字段子集

**Step 2：数据解析**

- 读取输入内容，识别分隔符（逗号、制表符、换行等）
- 检测数据头（header）是否存在，若缺失则自动生成 `field_1, field_2...`
- 对 URL 输入，提取页面标题、正文文本、主要链接

**Step 3：关键信息提取**

- 按以下规则识别字段类型：

| 字段类型 | 识别规则 | 示例 |
|----------|----------|------|
| 日期 | 匹配 `YYYY-MM-DD` / `YYYY/MM/DD` / `MM月DD日` | 2025-03-15 |
| 金额 | 匹配 `¥`/`$` 后跟数字，或纯数字+单位 | ¥1,200 / 300元 |
| 邮箱 | 标准邮箱正则 | user@example.com |
| 手机号 | 1 开头 11 位数字 | 13800138000 |
| 状态 | 枚举值匹配（成功/失败/待处理/进行中） | 成功 |

- 对无法识别的字段，标记为 `unknown_type` 并降低置信度

**Step 4：置信度标注**

- 每条记录整体置信度 = 各字段置信度的加权平均（权重默认均等）
- 置信度等级划分：

| 等级 | 分值范围 | 含义 |
|------|----------|------|
| high | 0.8 - 1.0 | 字段提取明确，无歧义 |
| medium | 0.5 - 0.79 | 字段存在但格式不标准，或存在多义性 |
| low | 0 - 0.49 | 字段缺失、格式混乱或无法识别 |

**Step 5：输出生成**

- 按约定 schema 生成结构化结果（见 3.3）
- 执行自查：字段完整性、格式正确性、置信度标注是否齐全
- 若存在 `low` 置信度字段，在输出末尾附「需人工复核」清单

**Step 6：二次确认（可选）**

- 若输入信息不足以完成解析（如文件为空、URL 无法访问），主动向用户说明原因并请求补充

### 3.3 输出规范

**默认 JSON 格式**：

```json
{
  "meta": {
    "source": "file://batch_01.csv",
    "processed_at": "2025-03-15T10:30:00Z",
    "record_count": 3,
    "overall_confidence": 0.85
  },
  "records": [
    {
      "id": 1,
      "fields": {
        "date": { "value": "2025-03-14", "confidence": "high" },
        "amount": { "value": 1200, "confidence": "high" },
        "status": { "value": "成功", "confidence": "high" }
      },
      "record_confidence": 0.95
    },
    {
      "id": 2,
      "fields": {
        "date": { "value": "2025-03-13", "confidence": "high" },
        "amount": { "value": null, "confidence": "low", "note": "字段缺失" },
        "status": { "value": "处理中", "confidence": "medium" }
      },
      "record_confidence": 0.6
    }
  ],
  "review_required": [
    { "record_id": 2, "field": "amount", "reason": "字段缺失" }
  ]
}
```

**Markdown 表格格式**（用户指定时）：

| ID | 日期 | 金额 | 状态 | 置信度 |
|----|------|------|------|--------|
| 1 | 2025-03-14 | ¥1,200 | 成功 | 高 |
| 2 | 2025-03-13 | 缺失 | 处理中 | 中 |

---

## 四、置信度门控：不编造原则

当遇到以下情况时，输出 `[需核实:字段名]` 占位符，**绝不猜测或编造**：

| 场景 | 处理方式 |
|------|----------|
| 字段值缺失 | 输出 `[需核实:amount]`，confidence 设为 low |
| 字段格式无法识别 | 输出 `[需核实:date_format]`，confidence 设为 low |
| URL 无法访问 | 输出 `[需核实:source_url]`，并终止该条记录的处理 |
| 数据存在矛盾（如同一 ID 出现两个不同日期） | 输出 `[需核实:duplicate_id]`，保留两条记录并标记冲突 |

**示例**：

```json
{
  "id": 5,
  "fields": {
    "date": { "value": "[需核实:date]", "confidence": "low" },
    "amount": { "value": 800, "confidence": "high" }
  }
}
```

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| E001 | 输入为空 | "未检测到有效输入，请提供文本、文件或 URL" | 检查输入是否为空，重新提供数据 |
| E002 | 文件格式不支持 | "仅支持 .txt/.csv/.json/.md 格式，请转换后重试" | 将文件转为支持的文本格式 |
| E003 | URL 无法访问 | "目标 URL 返回 404 或超时，请确认链接有效性" | 检查链接拼写，或改用文本输入 |
| E004 | 字段提取失败 | "部分字段无法识别，已标记为 low 置信度" | 检查源数据格式，统一分隔符或字段名 |
| E005 | 批量处理中断 | "第 3 个文件解析失败，已跳过，继续处理剩余文件" | 单独检查失败文件，修复后重新执行 |
| E006 | 输出格式冲突 | "自定义字段与默认 schema 冲突，请调整字段名" | 使用标准字段名或明确映射关系 |

---

## 六、FAQ 反模式：常见坑与对照

| 常见错误做法（反模式） | 正确做法 | 说明 |
|------------------------|----------|------|
| 直接跳过缺失字段，不标注 | 用 `[需核实:字段]` 占位并降低置信度 | 保证输出完整性，让用户知道哪里有问题 |
| 对 URL 内容做深度语义分析 | 仅提取标题、正文文本、链接 | 本技能定位是结构化提取，不做语义理解 |
| 批量处理时覆盖原始文件 | 保留原始文件备份，输出到新目录 | 防止数据丢失，便于回溯 |
| 自定义输出格式时随意改字段名 | 在标准 schema 基础上做子集选择或排序 | 保证输出可被下游程序消费 |
| 对低置信度结果不做提示 | 在输出末尾附「需人工复核」清单 | 让用户明确知道哪些数据需要人工确认 |

---

## 七、渐进式披露：分层次阅读路径

### 7.1 速查卡（30 秒上手）

1. 提供数据（文本/文件/URL）
2. 说"用 reviewcerberus 处理"
3. 收到 JSON 或表格输出
4. 检查 `review_required` 清单，人工复核低置信度项

### 7.2 新手路径（首次使用）

- 阅读「一、能力边界」了解能做什么、不能做什么
- 按「三、标准流程」的 Step 1-3 操作，先跑单个样本
- 对照「六、FAQ 反模式」避免常见错误

### 7.3 进阶路径（深度使用）

- 自定义输出字段子集：在请求中说明"只输出日期和金额字段"
- 批量处理：将多个文件命名为 `batch_01.csv`、`batch_02.csv` 等，一次提交
- 格式定制：指定输出 Markdown 表格而非 JSON
- 结合「五、错误码体系」排查批量处理中的异常

---

## 八、用户协议

使用本 Skill 即表示您同意以下条款：

1. **责任承担**：使用者自行承担因使用本 Skill 产生的全部责任。本 Skill 仅提供数据处理与格式转换功能，不构成任何形式的专业建议或决策依据。
2. **数据合规**：使用者须确保输入数据来源合法、内容合规，不得包含侵犯他人隐私、知识产权或违反法律法规的信息。
3. **禁止反向工程**：使用者不得对本 Skill 的提示词、处理逻辑、输出 schema 进行反向工程、破解、篡改或二次分发用于商业用途。
4. **无担保声明**：本 Skill 按"现状"提供，不附带任何明示或暗示的担保，包括但不限于适销性、特定用途适用性和非侵权保证。
5. **免责范围**：因使用或无法使用本 Skill 造成的任何直接、间接、偶然或后果性损害，作者不承担任何责任。

<!-- user-agreement-injected -->

---

## 九、许可证（License）

本 Skill 采用 MIT 许可证发布。

### MIT License

```
MIT License

Copyright (c) 2025 林砚秋

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

*文档版本：1.0.0 | 最后更新：2025-03-15*
