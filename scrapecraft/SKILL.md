---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: scrapecraft
name: scrapecraft
displayName: 网页采集 数据抽取 流程编排
description: 自然语言描述采集需求，自动生成可视化采集流程并执行。
version: 1.0.4
rules_version: cpr-20260820-n601
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/scrapecraft
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 林默
agent_created: true
trigger_words: ["爬虫采集","网页抓取","数据抽取","采集流程","scrapecraft","数据爬取","页面解析","字段提取"]
---

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->


> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# scrapecraft — 网页采集流程编排工具

## 一、能力边界（一页纸速查卡）

### 1.1 能做什么

| 能力项 | 说明 | 示例 |
|--------|------|------|
| 自然语言转流程 | 将口语化需求解析为结构化采集流程定义 | "抓取某电商前3页商品标题和价格" → 生成流程 JSON |
| 字段提取 | 从页面中抽取指定字段，支持 CSS 选择器与 XPath | 标题、价格、发布时间、作者 |
| 分页处理 | 自动识别并遍历翻页链接 | 翻 5 页、翻到末页、按条件停止 |
| 试跑模式 | 单条记录验证，确认字段映射正确后再批量执行 | 先抓 1 条看结果 |
| 批量执行 | 按流程定义自动采集全部目标数据 | 输出 JSON 文件 |
| 结果抽查 | 按比例抽样复核字段完整度与格式 | 5% 抽样，输出报告 |

### 1.2 不能做什么

| 限制项 | 说明 |
|--------|------|
| 不处理登录墙 | 需要登录的站点需先配置 Cookie 或使用外部会话工具 |
| 不执行 JavaScript 渲染 | SPA 站点需配合预渲染工具（如 Puppeteer）使用 |
| 不绕过反爬机制 | 不提供验证码识别、IP 轮换等功能 |
| 不保证数据准确性 | 页面结构变化可能导致提取失败，需人工复核 |
| 不承担合规责任 | 使用者须自行确认采集行为合法合规 |

### 1.3 适用对象

- 需要从网页批量获取结构化数据的分析师、运营人员
- 需要快速搭建采集流程的开发者
- 对代码不熟悉但需要数据支撑的业务人员

---

## 二、触发方式

当用户输入以下任一表述时，本 Skill 被激活：

| 触发词/短语 | 场景示例 |
|-------------|----------|
| 爬虫采集 | "帮我写个爬虫采集这个网站的数据" |
| 网页抓取 | "抓取这个页面的所有链接" |
| 数据抽取 | "从这篇文章里抽出作者和发布时间" |
| 采集流程 | "设计一个采集流程，每天跑一次" |
| scrapecraft | 直接调用工具名 |
| 数据爬取 | "爬取这个列表页的所有条目" |
| 页面解析 | "解析这个页面的表格数据" |
| 字段提取 | "提取商品名称、价格、评价数" |

---

## 三、标准流程

### 3.1 前置条件

| 条件 | 要求 |
|------|------|
| 目标 URL | 必须提供完整的 http/https 地址 |
| 字段清单 | 至少明确 1 个要提取的字段 |
| 翻页规则 | 明确翻页数量或终止条件（可选，默认只抓当前页） |
| 网络环境 | 目标站点可正常访问 |

### 3.2 执行步骤

**Step 1 — 描述需求**

用户需提供以下信息（缺一不可）：

```
目标URL：https://example.com/list
要提取的字段：标题、价格、发布日期
翻页：翻 3 页
```

**Step 2 — 确认流程定义**

Skill 根据需求生成流程定义 JSON，包含：

```json
{
  "start_url": "https://example.com/list",
  "pagination": {"type": "next_link", "max_pages": 3},
  "fields": [
    {"name": "title", "selector": "h2.title", "type": "text"},
    {"name": "price", "selector": ".price", "type": "number"},
    {"name": "date", "selector": ".date", "type": "date"}
  ]
}
```

用户需确认：
- 字段选择器是否正确
- 翻页规则是否符合预期
- 字段类型是否匹配

**Step 3 — 试跑 1 条**

执行单条记录采集，输出样例：

```json
{
  "title": "示例商品A",
  "price": 199.00,
  "date": "2026-08-15"
}
```

用户检查字段值是否提取正确。如有偏差，调整选择器后重试。

**Step 4 — 批量执行**

确认无误后，按流程定义批量采集。输出文件格式：

```json
[
  {"title": "示例商品A", "price": 199.00, "date": "2026-08-15"},
  {"title": "示例商品B", "price": 259.00, "date": "2026-08-14"}
]
```

**Step 5 — 抽查结果**

按 5% 比例（至少 1 条）抽样复核，输出报告：

```
抽样数量：5
字段完整率：100%
格式正确率：80%（1 条日期格式异常）
异常明细：[{"record_id": 3, "field": "date", "issue": "格式为 2026/08/15，应为 2026-08-15"}]
```

### 3.3 输出规范

| 输出类型 | 格式 | 说明 |
|----------|------|------|
| 流程定义 | JSON | 结构化描述采集步骤 |
| 试跑结果 | JSON 单条 | 单条记录样例 |
| 批量结果 | JSON 数组 | 全部采集记录 |
| 抽查报告 | Markdown | 抽样统计与异常明细 |

---

## 四、置信度门控

### 4.1 信息不足时的处理

当以下情况发生时，Skill 不会编造数据，而是输出占位符：

| 场景 | 输出 | 说明 |
|------|------|------|
| 字段选择器未匹配到元素 | `[需核实:字段名]` | 页面结构可能已变化 |
| 翻页链接未找到 | `[需核实:翻页规则]` | 需人工确认翻页方式 |
| 字段类型转换失败 | `[需核实:字段名]` | 原始值格式与预期不符 |
| 页面加载超时 | `[需核实:网络状态]` | 需确认目标站点可访问性 |

### 4.2 选择器校验逻辑

1. **试跑阶段**：每个字段必须至少匹配 1 个元素，否则标记为低置信度
2. **批量阶段**：若某字段匹配率低于 90%，自动暂停并提示人工介入
3. **结果阶段**：抽查发现格式错误率超过 10%，输出警告并建议修正

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| E001 | URL 格式错误 | "目标地址格式不正确，请提供完整的 http/https 链接" | 检查 URL 是否包含协议头 |
| E002 | 字段未指定 | "请至少指定一个要提取的字段" | 补充字段名称及对应选择器 |
| E003 | 选择器无匹配 | "选择器 [xxx] 未匹配到任何元素" | 检查页面结构，调整选择器 |
| E004 | 翻页失败 | "未找到下一页链接，已停止翻页" | 手动确认翻页方式，或改用页码遍历 |
| E005 | 页面超时 | "页面加载超时（10秒），请检查网络或站点状态" | 重试或更换网络环境 |
| E006 | 数据格式异常 | "字段 [xxx] 的值 [yyy] 无法转换为目标类型" | 调整字段类型定义或清洗规则 |
| E007 | 批量中断 | "采集进度 45% 时出现连续 5 条记录提取失败，已自动停止" | 检查站点是否变更结构，调整后重试 |
| E008 | 合规风险 | "目标站点 robots.txt 禁止采集，已拒绝执行" | 更换数据源或取得授权 |

---

## 六、FAQ 反模式

### 6.1 常见陷阱与正确做法

| 反模式 | 问题描述 | 正确做法 |
|--------|----------|----------|
| 一次性抓取全部 | 未试跑直接批量执行，导致大量错误数据 | 先试跑 1 条，确认字段映射正确后再批量 |
| 忽略页面结构变化 | 选择器写死后长期不更新，采集失败 | 定期检查页面结构，维护选择器 |
| 不设翻页上限 | 无限翻页导致请求量过大 | 明确最大翻页数或终止条件 |
| 字段类型一刀切 | 所有字段都按文本处理，后续清洗困难 | 按实际数据类型定义字段（数字、日期、枚举） |
| 忽视异常处理 | 单条失败即中断整个流程 | 配置容错策略（跳过、重试、终止） |

### 6.2 反模式对照表

```
❌ "直接全量跑吧，有问题再说"
✅ "先跑 1 条看看字段对不对，再决定是否批量"

❌ "这个选择器肯定没问题，不用验证"
✅ "试跑确认一下选择器是否匹配到预期元素"

❌ "翻页就翻到没有为止"
✅ "设置最大翻页数 10 页，防止无限请求"

❌ "所有字段都按字符串存"
✅ "价格用数字类型，日期用日期类型，便于后续分析"
```

---

## 七、渐进式披露

### 7.1 速查卡（新手必读）

```
使用四步：
1. 说需求 → URL + 字段 + 翻页
2. 看流程 → 确认选择器和翻页规则
3. 试跑 → 验证 1 条数据
4. 批量 → 执行并抽查
```

### 7.2 分层次阅读路径

**新手路径**（首次使用）：
1. 阅读「能力边界」了解工具范围
2. 按「标准流程」Step 1-3 完成首次采集
3. 遇到问题查「错误码体系」

**进阶路径**（熟练用户）：
1. 深入「置信度门控」理解选择器校验逻辑
2. 参考「FAQ 反模式」规避常见陷阱
3. 自定义清洗规则，处理复杂字段格式

**专家路径**（深度集成）：
1. 结合外部预渲染工具处理 SPA 站点
2. 配置 Cookie 处理半公开数据
3. 将输出接入下游数据处理管道

---

## 八、合规使用声明

**合规使用**：使用者应确保采集行为符合相关法律法规及目标网站的 robots.txt 规定。对于需要授权方可访问的内容，使用者应事先取得相应授权。

---

## 用户协议

<!-- user-agreement-injected -->

使用本 Skill 即表示您同意以下条款：

1. **责任承担**：使用者自行承担因使用本 Skill 进行网页采集所产生的一切责任与后果。包括但不限于数据使用合规性、目标网站服务条款遵守情况、以及因采集行为引发的任何法律纠纷。

2. **禁止反向工程**：使用者不得对本 Skill 的底层实现进行反向工程、反编译、破解或试图提取源代码。不得移除、篡改或绕过本 Skill 中的任何合规检查机制。

3. **数据使用**：通过本 Skill 采集的数据，其使用方式由使用者自行负责。建议在使用前评估数据的敏感性及适用法律。

4. **免责声明**：本 Skill 按"原样"提供，不附带任何明示或暗示的保证。作者不对因使用本 Skill 而产生的任何直接或间接损失承担责任。

5. **协议更新**：本协议可能随 Skill 版本更新而调整，使用者应定期查阅最新版本。

---

## 许可证（License）

<!-- professional-license-embedded -->

MIT License

Copyright (c) 2026 林默

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
