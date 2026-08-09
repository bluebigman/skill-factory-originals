---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: awesome-llm-skills
name: awesome-llm-skills
displayName: 技能导航 场景匹配 能力速查
description: 快速匹配LLM技能场景，提供结构化处理与置信度标注的通用工作流。
version: 1.0.1
rules_version: cpr-20260809-n251
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/awesome-llm-skills
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: LingFlow Studio
agent_created: true
trigger_words: ["awesome-llm-skills", "技能导航", "能力匹配", "场景速查", "技能清单", "LLM技能"]
---

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->


> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# awesome-llm-skills 技能导航与场景匹配工作流

## 一、能力边界速查卡

本 Skill 定位为「通用输入处理与结构化输出」的导航型工作流。它不绑定特定业务领域，而是提供一套可复用的处理框架。

### 能做（核心能力）

| 编号 | 能力项 | 说明 | 适用场景举例 |
|------|--------|------|--------------|
| C1 | 输入解析 | 接收用户提供的文本、文件路径或 URL，提取关键实体与关系 | 从一段会议纪要中提取待办事项 |
| C2 | 结构化输出 | 将非结构化内容转换为 JSON / Markdown 表格等约定格式 | 将产品评论整理为评分表 |
| C3 | 置信度标注 | 对每个输出字段附加可信度等级（高/中/低） | 从模糊语音转写中提取地址 |
| C4 | 批量处理 | 支持多条目输入，逐条处理并汇总结果 | 一次分析 20 条用户反馈 |
| C5 | 格式自定义 | 允许用户指定输出字段结构或模板 | 按客户要求的字段顺序导出报告 |

### 不能做（明确边界）

| 编号 | 限制项 | 说明 |
|------|--------|------|
| L1 | 不执行外部操作 | 不发送邮件、不修改数据库、不调用第三方 API |
| L2 | 不保证事实准确性 | 输出基于输入内容推断，不联网核验事实 |
| L3 | 不处理加密或二进制内容 | 仅支持纯文本、常见文档格式（.txt/.md/.csv）及公开 URL |
| L4 | 不提供法律/医疗建议 | 输出仅供参考，不构成专业意见 |

### 适用对象

- **终端用户**：需要快速将零散信息整理为结构化清单的办公人群
- **开发者**：需要为 LLM 应用搭建输入预处理管道的工程师
- **内容运营**：需要批量归类用户反馈或评论的运营人员

---

## 二、触发方式与场景映射

当你的输入包含以下特征时，本 Skill 会自动激活：

| 触发词/短语 | 典型用户表述 | 实际执行动作 |
|-------------|--------------|--------------|
| 整理 / 提取 / 结构化 | “帮我把这段文字里的日期和地点提取出来” | 执行 C1 解析 + C2 结构化 |
| 批量处理 / 逐条分析 | “这里有 10 条评论，帮我按情感分类” | 执行 C4 批量处理 |
| 转成表格 / JSON | “把这份名单转成 JSON 格式” | 执行 C2 结构化输出 |
| 置信度 / 不确定 | “哪些信息是推测的？” | 执行 C3 置信度标注 |
| 技能导航 / 能力匹配 | “我该用哪个技能处理这个任务？” | 输出本 Skill 的能力清单与推荐路径 |

**场景映射表（大白话版）**

| 你手头有什么 | 你想得到什么 | 本 Skill 做什么 |
|--------------|--------------|-----------------|
| 一段杂乱笔记 | 清晰的待办列表 | 提取动作 + 时间 + 负责人，生成 Markdown 清单 |
| 一堆客户反馈 | 分类统计表 | 按主题聚类，标注每条的情感倾向与置信度 |
| 一个网页链接 | 页面核心要点摘要 | 抓取文本，提取标题、关键段落、链接列表 |
| 一份 CSV 文件 | 清洗后的数据字典 | 识别列名、数据类型、缺失值占比 |

---

## 三、标准工作流

### 前置条件

- 输入内容已就绪（文本粘贴 / 文件路径 / URL）
- 明确输出格式（若未指定，默认输出 JSON）
- 确认处理范围（单条 or 批量）

### 执行步骤

**Step 1：输入确认**

接收用户输入，记录以下元信息：

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `input_type` | string | 是 | - | `text` / `file` / `url` |
| `content` | string | 是 | - | 文本内容或文件路径或 URL |
| `output_format` | string | 否 | `json` | `json` / `markdown` / `csv` |
| `fields` | array | 否 | 自动识别 | 自定义输出字段列表 |
| `batch_mode` | boolean | 否 | `false` | 是否批量处理 |

**Step 2：内容解析**

- 若为 `file`：读取文件，检测编码（UTF-8/GBK），提取纯文本。
- 若为 `url`：发起 HTTP GET 请求，解析 HTML，去除脚本与样式标签，提取正文文本。
- 若为 `text`：直接使用。

**Step 3：关键信息识别**

基于以下规则提取信息：

- **实体识别**：人名、组织名、日期、地点、金额、邮箱、电话。
- **关系抽取**：主谓宾结构、因果连词（因为/所以）、转折连词（但是/然而）。
- **主题聚类**：按关键词频次与语义相似度分组。

**Step 4：置信度评估**

对每个提取字段赋予置信度等级：

| 等级 | 判定标准 | 示例 |
|------|----------|------|
| 高 | 输入中明确出现，无歧义 | “2026年8月9日” → 日期置信度高 |
| 中 | 输入中有暗示，但需推断 | “下周一” → 需结合当前日期推断 |
| 低 | 输入缺失，或存在多种可能 | 未提及负责人 → 置信度低 |

**Step 5：输出生成**

按约定格式组装结果。JSON 示例：

```json
{
  "status": "success",
  "data": {
    "entities": [
      {"type": "person", "value": "张三", "confidence": "high"},
      {"type": "date", "value": "2026-08-09", "confidence": "high"}
    ],
    "summary": "会议确定了下季度目标与负责人分工。"
  },
  "meta": {
    "input_type": "text",
    "processed_at": "2026-08-09T10:30:00Z",
    "total_fields": 3,
    "avg_confidence": 0.87
  }
}
```

**Step 6：自查与校验**

- 字段完整性：检查所有必填字段是否已填充。
- 格式正确性：验证 JSON 合法性 / Markdown 表格对齐。
- 置信度标注：确认每个字段都有 `confidence` 属性。

**Step 7：二次确认**

若存在以下情况，主动向用户提问：

- 置信度为「低」的字段超过 50%
- 输入内容长度小于 10 个字符
- 检测到多种可能的输出格式

---

## 四、置信度门控机制

当信息不足以支撑可靠输出时，本 Skill 不会编造内容，而是采用以下策略：

### 占位符规范

| 场景 | 占位符格式 | 示例 |
|------|------------|------|
| 字段缺失 | `[需核实:字段名]` | `"负责人": "[需核实:负责人]"` |
| 值不确定 | `[需核实:字段名=候选值1/候选值2]` | `"城市": "[需核实:城市=北京/上海]"` |
| 格式不确定 | `[需核实:格式]` | `"日期": "[需核实:格式]"` |

### 门控触发条件

- 输入文本少于 20 个字符且未提供上下文 → 直接返回错误码 `E1001`
- 批量处理中单条失败率超过 30% → 中止处理，返回部分结果 + 错误报告
- URL 请求超时或返回非 HTML 内容 → 返回错误码 `E2002`

### 降级策略

当置信度整体偏低时，输出结果附带以下提示：

```
注意：本次处理结果中，有 3/5 个字段置信度为「低」。
建议补充以下信息以提高准确性：
- 明确的日期格式（如 2026-08-09 而非「下周」）
- 完整的姓名与职务
- 可验证的 URL 或文件路径
```

---

## 五、错误码体系

| 错误码 | 错误描述 | 用户提示话术 | 修正步骤 |
|--------|----------|--------------|----------|
| `E1001` | 输入内容过短或为空 | “输入内容似乎不完整，请提供至少 20 个字符的文本，或检查文件路径是否正确。” | 1. 检查输入文本长度；2. 确认文件路径存在且可读；3. 重新提交 |
| `E1002` | 无法识别的输入类型 | “无法判断输入类型，请明确指定为 text / file / url 中的一种。” | 1. 在参数中显式声明 `input_type`；2. 重新提交 |
| `E2001` | 文件读取失败 | “文件读取失败，请确认文件编码为 UTF-8 或 GBK，且未加密。” | 1. 转换文件编码；2. 移除密码保护；3. 重新提交 |
| `E2002` | URL 访问异常 | “无法访问该 URL，请检查链接是否有效，或稍后重试。” | 1. 手动浏览器打开验证；2. 更换为有效链接；3. 重新提交 |
| `E3001` | 输出格式不支持 | “暂不支持该输出格式，可选格式为 json / markdown / csv。” | 1. 修改 `output_format` 参数；2. 重新提交 |
| `E4001` | 批量处理中断 | “批量处理过程中出现过多失败项，已终止。请检查输入数据质量。” | 1. 查看部分结果中的错误明细；2. 修正问题条目；3. 重新提交 |

---

## 六、FAQ 与反模式对照

### 常见坑 1：过度推断

**反模式**：输入“张三负责项目”，输出中直接补全“张三（男，35岁）”。

**正确做法**：仅提取明确信息，即“负责人：张三”。年龄、性别等未提及字段标注为 `[需核实:年龄]`。

### 常见坑 2：忽略上下文

**反模式**：用户提供一段对话，仅提取了字面实体，未结合对话语境判断意图。

**正确做法**：先识别对话中的意图（如“安排会议”），再提取相关实体（时间、地点、参与人）。

### 常见坑 3：格式僵化

**反模式**：用户要求“简单整理一下”，仍输出冗长的 JSON 结构。

**正确做法**：根据用户语气与输出格式要求灵活调整。若未指定格式，默认输出简洁的 Markdown 列表。

### 常见坑 4：置信度缺失

**反模式**：所有字段均标注为“高”置信度，未体现不确定性。

**正确做法**：如实标注。对于推断内容，明确使用“中”或“低”等级，并附上推断依据。

### 常见坑 5：批量处理无反馈

**反模式**：批量处理 100 条数据，长时间无进度提示，用户误以为卡死。

**正确做法**：每处理 10 条输出一次进度日志，处理完成后汇总成功/失败统计。

---

## 七、渐进式阅读路径

### 速查卡（30 秒上手）

1. 粘贴文本 / 提供文件路径 / 提供 URL
2. 指定输出格式（默认 JSON）
3. 运行 → 得到结构化结果 + 置信度标注
4. 若出现 `[需核实:xxx]`，补充信息后重跑

### 新手路径（首次使用）

1. 阅读「能力边界速查卡」了解适用范围
2. 查看「触发方式与场景映射」确认你的需求是否匹配
3. 按「标准工作流」Step 1-3 完成一次简单文本提取
4. 遇到问题查阅「错误码体系」

### 进阶路径（深度使用）

1. 研究「置信度门控机制」，理解占位符与降级策略
2. 自定义 `fields` 参数，构建专属输出模板
3. 结合批量模式处理大规模数据，观察 `meta` 中的统计信息
4. 参考「FAQ 反模式」优化输入提示词，提升输出质量

---

## 八、参数速查表

| 参数名 | 类型 | 必填 | 默认值 | 取值范围 | 说明 |
|--------|------|------|--------|----------|------|
| `input_type` | string | 是 | - | `text` / `file` / `url` | 输入来源类型 |
| `content` | string | 是 | - | 任意文本 | 输入内容 |
| `output_format` | string | 否 | `json` | `json` / `markdown` / `csv` | 输出格式 |
| `fields` | array | 否 | 自动识别 | 自定义字段名列表 | 指定输出字段 |
| `batch_mode` | boolean | 否 | `false` | `true` / `false` | 是否批量处理 |
| `confidence_threshold` | number | 否 | `0.5` | `0.0` - `1.0` | 低于此值的字段触发占位符 |
| `max_retries` | integer | 否 | `2` | `0` - `5` | URL 请求重试次数 |

---

## 九、用户协议

使用本 Skill 即表示您同意以下条款：

1. **责任承担**：使用者应自行承担因使用本 Skill 产生的全部责任。本 Skill 提供的输出结果仅供参考，不构成任何形式的保证或承诺。
2. **禁止反向工程**：未经授权，不得对本 Skill 的底层逻辑、提示词结构或元数据进行反向工程、破解、篡改或二次分发。
3. **合规使用**：使用者应确保输入内容不违反法律法规，不包含侵犯第三方权益的信息。
4. **免责声明**：本 Skill 由 AI 辅助生成，可能存在未知缺陷或局限性。使用者应在关键场景中人工复核输出结果。

<!-- user-agreement-injected -->

---

## 十、许可证（License）

本 Skill 遵循 MIT 许可证发布。

### MIT License

```
MIT License

Copyright (c) 2026 LingFlow Studio

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

*文档版本：1.0.0 | 最后更新：2026-08-09 | 适用平台：通用 LLM 环境*
