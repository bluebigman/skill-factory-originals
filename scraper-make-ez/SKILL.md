---
slug: scraper-make-ez
name: scraper-make-ez
displayName: 网页采集 数据清洗 结构化输出
description: 将网页、文件或原始数据转化为规范结构化结果，附置信度标注。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 数据工坊·林默
agent_created: true
trigger_words: ["网页抓取", "数据采集", "scraper make ez", "爬虫", "结构化输出", "数据清洗"]
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# scraper-make-ez 技能手册

## 一、能力边界速查卡

本技能用于将**非结构化或半结构化输入**（网页、文本、CSV、JSON 等）转换为**符合约定字段结构的结果**，并给出每条结果的置信度评估。

| 维度 | 说明 |
|------|------|
| **输入来源** | 用户直接粘贴的文本 / 本地文件路径 / URL 地址 |
| **输出格式** | JSON（默认）、CSV（可选）、Markdown 表格（可选） |
| **核心能力** | 字段提取、类型识别、批量处理、置信度标注、格式转换 |
| **不处理** | 验证码破解、登录态绕过、反爬对抗、数据真实性核验 |
| **适用对象** | 个人学习研究、原型验证、小规模数据整理（≤5000 条/批） |

**不能做的事：**

- 不执行任何违反目标网站 robots.txt 或服务条款的抓取行为
- 不处理包含个人隐私（身份证、手机号、住址）的批量数据
- 不保证提取字段 100% 准确——所有输出均带置信度标记

---

## 二、触发方式与场景映射

当你的请求中出现以下任一情况时，本技能自动激活：

| 触发词（含变体） | 典型用户表述 | 本技能响应 |
|------------------|--------------|------------|
| 网页抓取 / 爬虫 | "帮我把这个页面里的商品信息抓下来" | 解析 HTML → 提取商品字段 |
| 数据采集 / 收集 | "采集这 50 个 URL 里的标题和日期" | 批量请求 → 结构化输出 |
| scraper make ez | "用 scraper make ez 处理一下" | 按标准流程执行 |
| 数据清洗 / 整理 | "把这个 CSV 里的脏数据整理成规整格式" | 字段映射 → 类型校正 |
| 结构化输出 | "把这段文本转成 JSON" | 语义解析 → 键值对输出 |

**场景示例：**

- 输入：`https://example.com/news/2024/01/15/article-123` → 输出：`{"title": "...", "date": "2024-01-15", "author": "...", "confidence": 0.92}`
- 输入：`data.csv`（含 200 行混合格式数据）→ 输出：清洗后的 `data_clean.json`

---

## 三、标准执行流程

### 前置条件

1. 待处理文件与工作目录在同一路径下，文件名不含空格或特殊字符
2. URL 可直接访问（无证书错误、无重定向循环）
3. 用户已明确输出格式偏好（默认 JSON）

### 执行步骤

| 步骤 | 操作 | 说明 |
|------|------|------|
| 1 | **输入确认** | 识别输入类型（文本/文件/URL），确认字段需求 |
| 2 | **单样本试运行** | 取 1 条数据执行完整流程，核对输出字段与格式 |
| 3 | **批量执行** | 确认无误后处理全量数据，保留原始文件备份 |
| 4 | **置信度标注** | 每条结果附加 `confidence` 字段（0.0~1.0） |
| 5 | **输出生成** | 按约定格式输出，附字段完整性自查表 |
| 6 | **结果校验** | 抽查 ≥5% 输出条目，与源数据比对关键字段 |

### 输出规范

```json
{
  "schema_version": "1.0",
  "generated_at": "2024-01-15T10:30:00Z",
  "total_items": 2,
  "items": [
    {
      "title": "示例标题",
      "date": "2024-01-15",
      "author": "张三",
      "confidence": 0.95,
      "warnings": []
    },
    {
      "title": "缺失标题",
      "date": null,
      "author": "李四",
      "confidence": 0.60,
      "warnings": ["title 字段缺失，已置空"]
    }
  ]
}
```

**字段完整性自查表：**

| 检查项 | 通过标准 |
|--------|----------|
| 必填字段 | 所有约定字段均存在（值可为 null） |
| 类型正确 | 日期为 ISO 格式，数值为 Number 类型 |
| 置信度标注 | 每条结果均有 0.0~1.0 的 confidence 值 |
| 警告信息 | 缺失/异常字段有明确 warnings 说明 |

---

## 四、置信度门控机制

当信息不足以确定某个字段值时，**不猜测、不编造**，按以下规则处理：

| 场景 | 处理方式 | 示例 |
|------|----------|------|
| 字段缺失 | 置为 `null`，confidence 降 0.2 | `"author": null` |
| 格式冲突 | 保留原始值，标注 `[需核实:字段名]` | `"date": "[需核实:date]"` |
| 多值歧义 | 取第一个，warnings 中列出全部候选 | `"warnings": ["存在多个日期，已取首个"]` |
| 编码异常 | 替换为 U+FFFD，confidence 降 0.3 | `"title": "商品���名"` |

**置信度评分规则：**

- 基础分 1.0，每出现一次缺失/异常扣 0.1~0.3
- 低于 0.5 的结果在输出中单独标记 `"needs_review": true`

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| E001 | 输入为空 | "未检测到有效输入，请提供文本、文件路径或 URL" | 检查输入参数 |
| E002 | URL 无法访问 | "目标 URL 返回 404/超时，请确认地址有效性" | 手动浏览器验证 URL |
| E003 | 文件格式不支持 | "仅支持 .txt/.csv/.json/.html 格式" | 转换格式后重试 |
| E004 | 字段映射失败 | "无法将源数据映射到目标字段结构" | 检查源数据表头/键名 |
| E005 | 批量处理中断 | "第 N 条数据异常，已停止处理" | 移除异常数据后重试 |
| E006 | 输出写入失败 | "目标路径无写入权限或磁盘已满" | 更换输出路径 |

---

## 六、FAQ 与反模式对照

| 常见坑 | 反模式（错误做法） | 正模式（推荐做法） |
|--------|---------------------|---------------------|
| 忽略试运行 | 直接批量处理 5000 条，发现字段全错 | 先跑 1 条样本，确认 schema 正确再全量 |
| 覆盖原始文件 | 清洗后直接覆盖源 CSV | 输出到新文件 `_clean.json`，保留原件 |
| 无置信度标注 | 输出结果不带任何质量指示 | 每条附 confidence 和 warnings |
| 编造缺失值 | 日期缺失时填"2024-01-01" | 置 null 并标注 `[需核实:date]` |
| 忽略编码问题 | 直接丢弃乱码字符 | 替换为 U+FFFD 并记录 warning |

---

## 七、渐进式阅读路径

### 新手路径（5 分钟上手）

1. 阅读「能力边界速查卡」确认本技能是否适用
2. 准备一个单条数据样本
3. 按「标准执行流程」步骤 1-2 执行
4. 查看输出 JSON 的 confidence 字段

### 进阶路径（深度使用）

1. 熟悉「置信度门控机制」，理解各扣分场景
2. 掌握「错误码体系」，能自主排查 E001~E006
3. 自定义字段映射规则（需在输入时声明 schema）
4. 批量处理前编写校验脚本，自动比对源数据与输出

### 自定义格式示例

```json
{
  "custom_schema": {
    "title": "string",
    "price": "number",
    "in_stock": "boolean"
  }
}
```

---

## 八、用户协议

使用本技能即表示您同意以下条款：

1. **责任承担**：使用者自行承担因使用本技能产生的全部责任，包括但不限于数据合法性、目标网站合规性、输出结果准确性。
2. **合法用途**：本技能仅供学习、研究、个人参考使用，禁止用于商业爬取、隐私侵犯、数据倒卖等非法场景。
3. **禁止反向工程**：不得对本技能的逻辑、提示词结构进行反向工程、反编译或提取核心算法。
4. **无担保声明**：本技能按"现状"提供，不附带任何明示或暗示的担保。

<!-- user-agreement-injected -->

---

## 九、许可证（License）

本技能采用 MIT 许可证授权：

```
MIT License

Copyright (c) 2024 数据工坊·林默

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

*本 Skill 由 AI 辅助生成，仅供参考。使用前请阅读相关文档。*
