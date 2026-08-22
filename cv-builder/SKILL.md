---
slug: cv-builder
name: cv-builder
displayName: 简历智造 求职文书 结构化输出
description: 将零散经历转化为规范简历，支持多格式输出与置信度标注。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: LingForge
agent_created: true
trigger_words: ["简历制作", "求职", "cv builder", "简历优化", "履历整理", "求职文书"]
---

> 本内容由 AI 生成，仅供学习参考 <!-- ai-generated-notice -->

# SKILL.md — cv-builder 技能文档

## 一、能力边界（一页纸速查卡）

### ✅ 能做（5 项核心能力）

| 编号 | 能力项 | 说明 | 示例 |
|------|--------|------|------|
| C1 | 数据转结构化 | 将用户提供的文本、文件或 URL 内容解析为简历字段 | 从一段工作描述中提取"公司-职位-时间-职责" |
| C2 | 关键信息识别 | 自动识别姓名、联系方式、教育背景、工作经历、技能标签 | 从散乱笔记中挑出学历信息 |
| C3 | 约定格式输出 | 按用户指定模板（或默认模板）生成 Markdown / JSON / TXT 简历 | 输出标准 JSON 结构或 Markdown 简历 |
| C4 | 置信度提示 | 对自动提取的每个字段标注可信程度（高/中/低） | `"company": {"value": "某科技公司", "confidence": "high"}` |
| C5 | 批量与自定义 | 支持一次处理多份简历数据，支持自定义字段映射 | 批量处理 10 份文本简历并统一输出 |

### ❌ 不能做（明确边界）

| 编号 | 限制项 | 说明 |
|------|--------|------|
| L1 | 不生成虚假经历 | 不会编造用户未提供的工作经历或技能 |
| L2 | 不保证求职结果 | 不承诺简历投递后必然获得面试或录用 |
| L3 | 不替代人工审阅 | 输出结果需用户自行核对，尤其是日期、公司名称等细节 |
| L4 | 不处理敏感信息 | 不接收或存储身份证号、银行账号等敏感个人数据 |
| L5 | 不提供法律建议 | 涉及劳动纠纷、合同条款等问题时，建议咨询专业人士 |

### 👥 适用对象

- 正在求职的应届毕业生
- 准备跳槽的职场人士
- 需要批量整理团队简历的 HR 或猎头
- 学习简历写作技巧的学生或求职者

---

## 二、触发方式

### 触发词

当用户输入包含以下任一关键词时，本技能自动激活：

- 简历制作 / 简历优化 / 简历修改
- 求职 / 找工作 / 应聘
- cv builder / resume builder / CV 制作
- 履历整理 / 个人简介生成

### 场景映射表

| 用户说（大白话） | 技能响应 |
|------------------|----------|
| "帮我写份简历" | 启动 C1，询问用户提供基本信息或原始材料 |
| "把这段经历整理成简历格式" | 启动 C1+C2，解析文本并结构化 |
| "我有 5 份简历要统一格式" | 启动 C5，批量处理 |
| "这个简历模板能用吗？" | 提供默认模板说明，并询问是否自定义 |
| "帮我检查简历里有没有错" | 执行字段完整性自查，输出缺失项提示 |

---

## 三、标准流程

### 前置条件

1. 用户提供至少一份原始材料（文本、文件路径或 URL）
2. 若为文件，需确认文件格式（.txt / .md / .pdf / .docx）
3. 若为 URL，需确认内容可公开访问且非登录页

### 执行步骤（分步编号）

**Step 1 — 输入接收与解析**

- 接收用户输入，识别输入类型（文本 / 文件 / URL）
- 若为文件，读取内容并转为纯文本
- 若为 URL，抓取页面正文并去除导航、广告等噪声

**Step 2 — 字段提取与结构化**

按以下字段结构进行提取：

| 字段名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `name` | string | 是 | 姓名 |
| `contact` | object | 是 | 邮箱、电话、地址（至少一项） |
| `education` | array | 否 | 学历记录（学校、专业、时间） |
| `experience` | array | 否 | 工作/实习经历（公司、职位、时间、职责） |
| `skills` | array | 否 | 技能标签列表 |
| `projects` | array | 否 | 项目经历（名称、角色、成果） |
| `certificates` | array | 否 | 证书/资质 |

**Step 3 — 置信度标注**

- 对每个提取字段标注 `confidence` 值：
  - `high`：信息完整且无歧义
  - `medium`：信息部分缺失或存在多种可能
  - `low`：信息模糊或无法确认
- 对 `low` 置信度的字段，输出 `[需核实:字段名]` 占位符

**Step 4 — 输出生成**

- 默认输出格式为 Markdown 简历
- 用户可指定输出为 JSON 或纯文本
- 输出文件命名规则：`{姓名}_resume_{日期}.md`

**Step 5 — 自查与确认**

- 检查字段完整性（必填项是否齐全）
- 检查格式正确性（日期格式、列表缩进等）
- 若存在 `low` 置信度字段，主动向用户二次确认

### 输出规范

```markdown
# {姓名}

## 联系方式
- 邮箱：{email}
- 电话：{phone}
- 地址：{address}

## 教育背景
- {学校} | {专业} | {时间}（置信度：{high/medium/low}）

## 工作经历
### {公司} — {职位}（{时间}）
- {职责描述}

## 技能
- {技能1}、{技能2}、{技能3}

---
> 生成时间：{timestamp} | 置信度标注：{字段名}:{confidence}
```

---

## 四、置信度门控

### 规则

1. **不编造**：任何未在原始材料中出现的信息，一律不生成
2. **占位符**：信息不足时，输出 `[需核实:字段名]` 占位符
3. **主动确认**：当必填字段缺失或置信度为 `low` 时，主动询问用户

### 示例

**输入**："我在某公司做过开发，2023 年。"

**输出**：

```json
{
  "experience": [
    {
      "company": "某公司",
      "position": "[需核实:职位]",
      "start_date": "2023",
      "end_date": "[需核实:结束时间]",
      "responsibilities": ["开发相关工作"],
      "confidence": "low"
    }
  ]
}
```

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| `E001` | 输入为空 | "未检测到有效输入，请提供简历相关文本或文件。" | 请用户重新输入或上传文件 |
| `E002` | 文件格式不支持 | "当前文件格式暂不支持，请转换为 .txt / .md / .pdf / .docx。" | 指导用户转换格式后重试 |
| `E003` | URL 无法访问 | "无法访问该链接，请确认链接是否公开有效。" | 检查链接或改用文本输入 |
| `E004` | 必填字段缺失 | "缺少必填字段：姓名、联系方式。" | 提示用户补充缺失信息 |
| `E005` | 批量处理中断 | "批量处理在第 N 条数据时中断，请检查该条数据格式。" | 定位问题数据并修正后重试 |
| `E006` | 输出格式冲突 | "指定的输出格式与模板不兼容，请选择支持的格式。" | 重新选择输出格式 |

---

## 六、FAQ 反模式

### 常见坑 1：过度美化

- **反模式**：将"参与项目"自动改写为"主导项目"
- **正确做法**：忠实于原始描述，仅做格式整理，不做事实性夸大

### 常见坑 2：忽略时间线

- **反模式**：不检查经历时间是否连续合理
- **正确做法**：输出时按时间倒序排列，并标注时间缺失项

### 常见坑 3：技能堆砌

- **反模式**：将用户提到的所有关键词全部列为技能
- **正确做法**：区分"熟练"与"了解"，按用户自述程度分层标注

### 常见坑 4：格式混乱

- **反模式**：不同经历的格式不一致（有的有日期，有的没有）
- **正确做法**：统一字段结构，缺失项用占位符标注

### 常见坑 5：忽略隐私

- **反模式**：将用户完整身份证号或家庭住址写入简历
- **正确做法**：仅保留必要联系方式，敏感信息一律过滤

---

## 七、渐进式披露

### 速查卡（30 秒上手）

```
输入 → 解析 → 提取 → 标注置信度 → 输出 → 自查
```

### 新手路径（首次使用）

1. 阅读"能力边界"了解能做什么
2. 直接提供一段文本或文件，触发 C1
3. 查看输出结果，重点关注 `[需核实:]` 占位符
4. 根据提示补充缺失信息

### 进阶路径（熟练用户）

1. 使用批量处理模式（C5），准备多份文件
2. 自定义字段映射，适配特定行业模板
3. 使用 JSON 输出对接其他工具
4. 结合错误码体系排查批量处理中的问题

---

## 八、用户协议

使用本 Skill 即表示您同意以下条款：

1. **责任承担**：使用者自行承担因使用本 Skill 产生的全部责任。本 Skill 提供的输出仅供参考，不构成任何形式的求职保证或法律建议。
2. **禁止反向工程**：禁止对本 Skill 的底层逻辑、提示词结构进行反向工程、破解或二次分发。
3. **数据安全**：使用者应自行确保输入数据的合法性，不得输入侵犯他人隐私或违反法律法规的内容。
4. **无担保声明**：本 Skill 按"现状"提供，不附带任何明示或暗示的担保。

<!-- user-agreement-injected -->

---

## 九、许可证（License）

本 Skill 采用 MIT 许可证授权：

```
MIT License

Copyright (c) 2024 LingForge

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

## 十、版本记录

| 版本 | 日期 | 变更说明 |
|------|------|----------|
| 1.0.0 | 2024-01 | 初始版本，包含核心能力与标准流程 |

---

*本 Skill 由 AI 辅助生成，仅供参考。使用前请阅读相关文档。*
