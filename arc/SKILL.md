---
slug: arc
name: arc
displayName: 数据解析 结构化转换 信息提取
description: 将任意数据、文件或URL转换为结构化结果，识别关键信息并标注置信度。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 流萤工坊
agent_created: true
trigger_words: ["arc", "数据转换", "结构化输出", "信息提取", "数据解析", "字段抽取", "置信度标注"]
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# arc — 数据解析与结构化转换 Skill

## 一、能力边界（一页纸速查卡）

### 1.1 能做什么

| 能力项 | 说明 | 示例 |
|--------|------|------|
| 文本解析 | 从纯文本中抽取实体、关键字段 | 从简历文本中提取姓名、电话、邮箱 |
| 文件解析 | 读取常见格式文件并结构化 | `.txt`、`.csv`、`.json`、`.md`、`.log` |
| URL 抓取 | 从网页链接中提取正文与元信息 | 新闻页、产品页、文档页 |
| 字段映射 | 将非标准字段名映射为统一 schema | `"ph"` → `"phone"` |
| 置信度标注 | 对每个抽取字段给出 0~1 的置信度分数 | `{"name": {"value": "张三", "confidence": 0.95}}` |

### 1.2 不能做什么

- 不能解析加密、二进制、损坏的文件
- 不能访问需要登录认证的 URL
- 不能对图片/音频/视频做 OCR 或语音识别
- 不能保证 100% 字段完整——缺失字段会以 `[需核实:字段名]` 占位
- 不能对抽取结果做业务决策，仅提供结构化数据

### 1.3 适用对象

- 需要批量清洗非结构化数据的开发者
- 需要从网页/文档中快速提取关键信息的分析人员
- 需要将异构数据源统一为固定 schema 的数据工程师

---

## 二、触发方式

### 2.1 触发词

直接使用以下任一词汇即可激活：

- `arc`
- `数据转换`
- `结构化输出`
- `信息提取`
- `数据解析`
- `字段抽取`
- `置信度标注`

### 2.2 场景映射表

| 你说的话（大白话） | arc 实际做的事 |
|-------------------|----------------|
| "帮我把这段文字里的联系方式整理出来" | 抽取 phone/email/address 字段并标注置信度 |
| "把这个 CSV 转成带类型的 JSON" | 解析 CSV，推断列类型，输出 JSON schema |
| "抓一下这个网页的产品价格和名称" | 抓取 URL，抽取 title/price/description |
| "把这几份日志里的错误码汇总一下" | 解析 log 文件，提取 error_code 字段并去重统计 |
| "这个表格里字段名太乱了，帮我统一" | 字段映射 + 重命名 + 类型推断 |

---

## 三、标准流程

### 3.1 前置条件

| 条件 | 要求 |
|------|------|
| 输入数据 | 必须是文本可读格式（txt/csv/json/md/log）或可公开访问的 URL |
| 目标 schema | 可选。不提供时使用默认 schema（见 3.4） |
| 上下文 | 可选。提供领域背景可提升抽取准确率（如"这是医疗报告"） |

### 3.2 执行步骤

1. **输入确认** — 检查输入类型（文本/文件/URL），确认可解析性
2. **格式识别** — 自动检测文件编码与格式（UTF-8/GBK、CSV 分隔符等）
3. **内容清洗** — 去除空白噪声、HTML 标签（若为网页）、BOM 头
4. **字段抽取** — 按 schema 逐字段匹配，使用正则 + 上下文规则
5. **置信度计算** — 每个字段根据匹配强度、上下文一致性给出 0~1 分数
6. **结果组装** — 输出 JSON 结构，缺失字段填 `[需核实:字段名]`
7. **自检** — 检查输出是否符合 schema，若不符合则回退到步骤 4

### 3.3 输出规范

输出始终为 JSON 对象，结构如下：

```json
{
  "schema_version": "1.0",
  "source_type": "text|file|url",
  "source_ref": "原始输入描述",
  "parsed_at": "2025-01-15T10:30:00Z",
  "fields": {
    "field_name": {
      "value": "抽取到的值",
      "confidence": 0.0,
      "method": "regex|context|model"
    }
  },
  "warnings": ["字段缺失说明", "编码猜测说明"]
}
```

### 3.4 默认 schema（未指定时使用）

| 字段 | 类型 | 说明 |
|------|------|------|
| `title` | string | 标题/名称 |
| `date` | string | 日期（ISO 8601） |
| `author` | string | 作者/责任人 |
| `content_summary` | string | 内容摘要（≤200字） |
| `keywords` | array | 关键词列表（≤10个） |
| `url` | string | 来源链接（若为 URL 输入） |

---

## 四、置信度门控

### 4.1 置信度分级

| 分数区间 | 含义 | 处理方式 |
|----------|------|----------|
| 0.9 ~ 1.0 | 高置信，规则明确匹配 | 直接输出 |
| 0.6 ~ 0.89 | 中置信，存在上下文推断 | 输出并附 `method: "context"` |
| 0.3 ~ 0.59 | 低置信，模糊匹配 | 输出但附加警告 `"low_confidence": true` |
| 0 ~ 0.29 | 无法确认 | 不输出值，填 `[需核实:字段名]` |

### 4.2 不编造原则

- 任何字段若无法从输入中直接或间接推导，一律输出 `[需核实:字段名]`
- 禁止根据常识或外部知识补全缺失字段
- 若输入为空或不可解析，返回 `{"error": "EMPTY_INPUT", "message": "输入内容为空或无法读取"}`

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| `EMPTY_INPUT` | 输入为空 | "未检测到可解析的内容" | 检查输入是否为空文件/空文本/无效 URL |
| `UNSUPPORTED_FORMAT` | 格式不支持 | "该文件格式不在支持列表中" | 转换为 txt/csv/json/md/log 后重试 |
| `URL_FETCH_FAILED` | URL 抓取失败 | "无法访问该链接，可能是网络或权限问题" | 确认链接可公开访问，或改用文本输入 |
| `ENCODING_ERROR` | 编码识别失败 | "无法确定文件编码，请指定编码格式" | 手动指定 UTF-8/GBK 等编码 |
| `SCHEMA_MISMATCH` | 输出与 schema 不匹配 | "抽取结果未通过 schema 校验" | 检查 schema 定义，或放宽字段约束 |
| `PARSE_TIMEOUT` | 解析超时 | "解析耗时超过 30 秒，已中断" | 缩小输入规模，或分块处理 |

---

## 六、FAQ 反模式对照

### 6.1 常见坑

| 坑 | 反模式（错误做法） | 正模式（正确做法） |
|----|-------------------|-------------------|
| 字段缺失时编造 | 根据上下文"猜"一个值填上 | 输出 `[需核实:字段名]` 占位 |
| 忽略编码问题 | 直接按 UTF-8 解析所有文件 | 先检测编码，失败时提示用户指定 |
| URL 抓取无超时 | 无限等待响应 | 设置 10 秒超时，超时返回 `URL_FETCH_FAILED` |
| 置信度虚高 | 所有字段都给 0.95 以上 | 按匹配方式严格分级，正则匹配才可给 0.9+ |
| 忽略 schema 校验 | 输出后不检查结构 | 组装后跑一遍 schema 校验，失败回退 |

### 6.2 反模式示例

**错误**：输入文本只有 "张三 13800138000"，输出 `{"email": "zhangsan@unknown.com"}`

**正确**：输出 `{"name": {"value": "张三", "confidence": 0.95}, "phone": {"value": "13800138000", "confidence": 0.95}, "email": "[需核实:email]"}`

---

## 七、渐进式披露

### 7.1 速查卡（30 秒上手）

```
输入 → arc → 输出 JSON
- 文本：直接粘贴
- 文件：给路径
- URL：给链接
- 可选：指定 schema
- 结果：fields 对象 + 置信度
- 缺失： [需核实:字段名]
```

### 7.2 新手路径（首次使用）

1. 准备一份纯文本（如一段简历文字）
2. 调用 `arc`，输入该文本
3. 查看输出的 `fields` 对象，确认 `title`、`date` 等字段是否抽取正确
4. 若某字段显示 `[需核实:xxx]`，手动补充该字段值
5. 熟悉后，尝试传入自定义 schema 以适配自己的业务

### 7.3 进阶路径（深度使用）

1. 学习置信度分级规则（见第四节），理解不同 `method` 的含义
2. 为特定领域（如医疗、法律）设计专属 schema 和正则规则
3. 对批量文件执行解析时，先跑 10 条样本，检查 `warnings` 字段
4. 结合错误码体系，编写自动化重试逻辑（如编码失败时自动切换编码）
5. 将输出接入下游管道，用 `schema_version` 做版本管理

---

## 八、参数参考表

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `input` | string | 必填 | 文本内容、文件路径或 URL |
| `schema` | object | 默认 schema | 自定义字段定义 |
| `encoding` | string | 自动检测 | 指定文件编码 |
| `timeout` | int | 30 | URL 抓取超时（秒） |
| `max_keywords` | int | 10 | 关键词最大数量 |
| `summary_length` | int | 200 | 摘要最大字符数 |
| `confidence_threshold` | float | 0.3 | 低于此值输出占位符 |

---

## 九、用户协议

<!-- user-agreement-injected -->

**使用 arc Skill 即表示您同意以下条款：**

1. **责任承担**：使用者自行承担因使用本 Skill 产生的全部责任。包括但不限于数据解析结果不准确、信息遗漏、URL 抓取内容的法律风险等。
2. **禁止反向工程**：不得对本 Skill 的提示词、内部逻辑、置信度算法进行反向工程、破解、提取或二次分发。
3. **数据合规**：使用者须确保输入数据不包含违反法律法规的内容，且拥有处理该数据的合法权利。
4. **无担保声明**：本 Skill 按"现状"提供，不附带任何明示或暗示的担保，包括但不限于适销性、特定用途适用性。
5. **免责范围**：因使用本 Skill 导致的任何直接、间接、偶然或后果性损害，Skill 作者不承担任何责任。

---

## 十、许可证（License）

<!-- professional-license-embedded -->

**MIT License**

Copyright (c) 2025 流萤工坊

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
