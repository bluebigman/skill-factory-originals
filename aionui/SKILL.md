---
slug: aionui
name: aionui
displayName: 数据整形 格式转换 批量处理
description: 将任意数据、文件或URL转换为结构化结果，支持批量处理与自定义格式。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 流形工坊
agent_created: true
trigger_words: ["aionui", "数据转换", "结构化输出", "信息提取", "批量处理", "格式转换", "数据清洗"]
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

本 Skill 由 AI 辅助生成，仅供参考。使用前请结合具体场景验证输出结果。

---

# aionui — 数据整形与格式转换工具

## 一、能力边界（一页纸速查卡）

### 1.1 能做什么

| 能力项 | 说明 | 示例 |
|--------|------|------|
| 格式互转 | 在 JSON / CSV / YAML / XML / Markdown 表格之间互相转换 | CSV → JSON，YAML → Markdown 表格 |
| 信息提取 | 从 URL 或文本中抽取指定字段（标题、正文、价格、日期等） | 从商品页提取 `title` 与 `price` |
| 批量处理 | 遍历文件夹内所有匹配文件，逐一转换并生成索引 | 将 `./data/*.csv` 全部转为 JSON |
| 字段重命名 | 转换时修改输出字段名 | `name` → `full_name` |
| 字段筛选 | 只输出指定字段，忽略其余 | 仅保留 `id` 和 `status` |
| 数据清洗 | 去除空值、重复项、指定字符，按字段排序 | 去重后按 `date` 升序排列 |
| 自定义模板 | 按用户提供的模板结构输出 | 嵌套 JSON 结构或指定表头顺序 |

### 1.2 不能做什么

| 限制项 | 说明 |
|--------|------|
| 不执行代码 | 不运行 JavaScript、Python 等脚本，仅做数据解析与转换 |
| 不访问登录态内容 | 无法处理需要认证的 URL 或私有 API |
| 不进行语义理解 | 不判断数据含义是否正确，只做结构转换 |
| 不处理二进制大文件 | 超过 50MB 的文件建议先拆分 |
| 不保证输出绝对正确 | 源数据本身有误时，转换结果同样有误 |

### 1.3 适用对象

- 需要快速将 CSV 转为 JSON 的运营人员
- 需要批量整理日志文件的开发工程师
- 需要从网页提取结构化信息的研究人员
- 需要统一多源数据格式的数据分析初学者

---

## 二、触发方式

### 2.1 触发词

以下任一词汇出现在用户输入中，即触发本 Skill：

- `aionui`
- `数据转换`
- `结构化输出`
- `信息提取`
- `批量处理`
- `格式转换`
- `数据清洗`

### 2.2 场景映射表

| 用户说（大白话） | 实际意图 | 本 Skill 执行动作 |
|------------------|----------|-------------------|
| "帮我把这个 Excel 转成 JSON" | 格式转换 | 读取文件 → 识别格式 → 输出 JSON |
| "这个网页里的价格帮我抓出来" | 信息提取 | 请求 URL → 解析 HTML → 提取价格字段 |
| "这个文件夹里所有 csv 都转一下" | 批量处理 | 遍历目录 → 逐个转换 → 生成索引 |
| "只要 id 和状态，其他不要" | 字段筛选 | 转换后仅保留指定字段 |
| "把 name 改成 full_name" | 字段重命名 | 输出时替换字段名 |
| "去掉重复的行，按日期排个序" | 数据清洗 | 去重 → 按日期排序 → 输出 |

---

## 三、标准流程

### 3.1 前置条件

| 条件 | 要求 |
|------|------|
| 输入数据 | 文本、文件路径（本地）或 URL（http/https） |
| 文件格式 | 扩展名需可识别：`.json` `.csv` `.yaml` `.yml` `.xml` `.md` `.txt` |
| 网络请求 | 若为 URL，需可公开访问，无登录墙 |
| 批量模式 | 文件夹路径需存在，且包含至少一个匹配文件 |

### 3.2 执行步骤

**Step 1 — 确认输入**

读取用户提供的数据。若为 URL，先发起 HTTP GET 请求获取内容；若为本地路径，检查文件是否存在。

**Step 2 — 识别源格式**

根据扩展名或内容特征判断格式：

| 特征 | 判定格式 |
|------|----------|
| 以 `{` 或 `[` 开头 | JSON |
| 以逗号分隔且首行为表头 | CSV |
| 以 `key: value` 缩进结构 | YAML |
| 以 `<tag>` 开头 | XML |
| 以 `|` 分隔的表格行 | Markdown 表格 |
| 以上均不匹配 | 纯文本，按行拆分 |

**Step 3 — 解析内容**

将源数据解析为内部结构化对象（键值对或对象数组）。解析失败时返回错误码 `E1001`。

**Step 4 — 应用转换规则**

按用户指令依次执行：

1. 字段重命名（如 `name` → `full_name`）
2. 字段筛选（仅保留指定字段）
3. 清洗规则（去空值、去重、去指定字符）
4. 排序（按指定字段升/降序）

**Step 5 — 生成输出**

按目标格式输出。若为批量模式，则逐个文件转换，并在最后生成 `index.json` 汇总索引（包含每个文件的输入路径、输出路径、转换状态）。

**Step 6 — 返回结果**

展示输出内容。若输出较长（超过 200 行），提供摘要 + 完整内容下载链接（本地临时文件）。

### 3.3 输出规范

| 输出格式 | 规范 |
|----------|------|
| JSON | 缩进 2 空格，UTF-8 编码，键名不加引号（标准 JSON） |
| CSV | 首行为表头，逗号分隔，含表头行 |
| YAML | 2 空格缩进，字符串不加引号（除非含特殊字符） |
| XML | 根节点 `<root>`，子节点按字段名生成 |
| Markdown 表格 | 首行为表头，第二行为分隔线，左对齐 |

---

## 四、置信度门控

当遇到以下情况时，**不编造数据**，输出占位符 `[需核实:字段名]`：

| 场景 | 处理方式 |
|------|----------|
| URL 请求超时或返回 404 | 输出 `[需核实:URL内容]`，并提示用户检查链接 |
| 源数据中某字段缺失 | 该字段输出 `[需核实:字段名]`，不猜测默认值 |
| 日期格式无法解析 | 输出 `[需核实:日期格式]`，并列出原始值 |
| 批量处理中某个文件解析失败 | 该文件状态标记为 `failed`，索引中注明原因，不中断整体流程 |

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| `E1001` | 源数据解析失败 | "无法解析输入内容，请确认格式是否正确" | 检查文件扩展名与内容是否匹配；尝试手动打开文件确认无损坏 |
| `E1002` | 文件不存在 | "找不到指定路径，请检查路径是否正确" | 确认路径拼写；使用绝对路径；检查文件是否被移动 |
| `E1003` | URL 请求失败 | "无法访问该链接，请确认链接可公开访问" | 检查 URL 拼写；确认无登录墙；尝试在浏览器中打开 |
| `E1004` | 目标格式不支持 | "暂不支持该输出格式，可选：JSON/CSV/YAML/XML/Markdown" | 从支持列表中选择一种；或自定义模板 |
| `E1005` | 字段不存在 | "指定字段在源数据中不存在" | 列出源数据所有字段供用户选择；或忽略该字段继续 |
| `E1006` | 批量模式无匹配文件 | "该文件夹下没有匹配的文件" | 确认扩展名匹配规则；检查文件夹路径 |

---

## 六、FAQ 反模式

### 6.1 常见坑

| 坑 | 反模式（错误做法） | 正模式（正确做法） |
|----|--------------------|--------------------|
| 格式误判 | 看到 `{` 就认为是 JSON，但实际是 JSON 字符串 | 先尝试 `JSON.parse`，失败则按纯文本处理 |
| 编码问题 | 直接读取文件，遇到中文乱码 | 先检测编码（UTF-8/GBK），统一转为 UTF-8 |
| 批量中断 | 一个文件出错就终止整个批量任务 | 跳过错误文件，记录日志，继续处理其余文件 |
| 字段覆盖 | 重命名后新旧字段同时存在 | 重命名时删除旧字段，只保留新字段 |
| 排序不稳定 | 按字符串排序数字（如 10 排在 2 前面） | 检测字段类型，数值型按数值排序 |

### 6.2 反模式对照

| 用户需求 | 反模式 | 正模式 |
|----------|--------|--------|
| "转成 JSON" | 输出带注释的 JSON（非标准） | 输出标准 JSON，无注释 |
| "提取所有信息" | 提取所有可见文本（含导航、广告） | 提取正文主体内容，过滤噪声 |
| "批量处理" | 一次加载所有文件到内存 | 逐文件流式处理，控制内存占用 |

---

## 七、渐进式披露

### 7.1 速查卡（新手必读）

1. 输入：数据 / 文件路径 / URL
2. 动作：格式转换 / 字段操作 / 清洗 / 批量
3. 输出：JSON / CSV / YAML / XML / Markdown 表格
4. 出错：查看错误码，按提示修正

### 7.2 进阶路径（有经验用户）

- **自定义模板**：提供 JSON 模板结构，输出按模板嵌套
- **组合清洗**：多规则串联，如 `去重 → 排序 → 字段筛选`
- **URL 列表批量提取**：传入多个链接，逐个提取指定字段，汇总输出
- **字段类型推断**：自动识别字符串/数字/日期，按类型处理排序与比较

---

## 八、用户协议

<!-- user-agreement-injected -->

**使用前请仔细阅读以下条款，使用本 Skill 即视为同意全部内容：**

1. **责任承担**：使用者自行承担因使用本 Skill 产生的全部责任。包括但不限于数据准确性、输出结果适用性及任何直接或间接损失。
2. **禁止反向工程**：不得对本 Skill 的提示词、内部逻辑进行逆向分析、提取或复制用于商业用途。
3. **数据合规**：使用者须确保输入数据不违反法律法规，不包含敏感个人信息或受版权保护的内容。
4. **无担保声明**：本 Skill 按"现状"提供，不附带任何明示或暗示的担保。

---

## 九、许可证（License）

<!-- professional-license-embedded -->

### MIT License

Copyright (c) 2024 流形工坊

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

*文档版本：1.0.0 | 最后更新：2024年*
