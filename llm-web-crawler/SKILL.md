---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: llm-web-crawler
name: llm-web-crawler
displayName: 网页采集 结构化提取 数据清洗
description: 将网页、文件或原始文本转化为结构化数据，供LLM应用与自动化流程直接调用。
version: 1.0.2
rules_version: cpr-20260815-n476
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/llm-web-crawler
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: DataForge Studio
agent_created: true
trigger_words: ["爬虫采集", "网页抓取", "数据提取", "结构化输出", "web scraper", "信息抽取", "页面解析", "--selftest", "--version"]
---

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->


> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# llm-web-crawler 技能文档

## 一、能力边界（速查卡）

### 1.1 能做什么

| 能力项 | 说明 | 输入示例 | 输出示例 |
|--------|------|----------|----------|
| 网页抓取 | 从 URL 获取 HTML 内容并解析 | `https://example.com/products` | 商品列表 JSON |
| 文件解析 | 读取本地 HTML/JSON/CSV/TXT 文件 | `./data/input.html` | 结构化记录数组 |
| 文本清洗 | 去除标签、空白、噪声字符 | 含 `<div>` 的原始文本 | 纯文本内容 |
| 字段抽取 | 按规则提取标题、链接、表格、列表 | 新闻页面 | `{title, url, date}` |
| 批量处理 | 多文件/多 URL 顺序执行 | 10 个 URL 列表 | 合并后的 JSON 数组 |

### 1.2 不能做什么（明确限制）

- **不执行 JavaScript 渲染**：SPA 页面（如 React/Vue 应用）动态加载的内容无法直接抓取，需配合无头浏览器。
- **不处理登录态**：需要 Session/Cookie 的页面无法访问。
- **不进行语义理解**：仅做结构抽取，不判断内容情感或主题。
- **不自动重试**：网络错误直接返回错误码，不自动重连。
- **不修改源文件**：所有输出写入新文件，原始数据保持只读。

### 1.3 适用对象

- 需要批量采集公开网页数据的分析师
- 需要将非结构化文本转为 JSON 供 LLM 调用的开发者
- 需要定期同步网页表格/列表数据的运维人员

---

## 二、触发方式

### 2.1 触发词映射

| 用户说（大白话） | 触发动作 |
|------------------|----------|
| "帮我抓一下这个网页" | 执行 `crawl_url` 流程 |
| "把这份 HTML 转成 JSON" | 执行 `parse_file` 流程 |
| "提取所有链接" | 执行 `extract_links` 流程 |
| "清洗这段文本" | 执行 `clean_text` 流程 |
| "批量处理这些文件" | 执行 `batch_process` 流程 |
| "--selftest" | 运行内置自检 |
| "--version" | 输出版本号 |

### 2.2 场景示例

```
用户：抓取 https://news.example.com 的所有文章标题和链接
→ 触发：crawl_url + extract_links
→ 输出：[{"title": "...", "url": "..."}]

用户：把 data/ 目录下所有 .html 文件转成 JSON
→ 触发：batch_process + parse_file
→ 输出：data/output/ 下生成同名 .json 文件
```

---

## 三、标准流程

### 3.1 前置条件

| 条件 | 要求 | 检查方式 |
|------|------|----------|
| 输入文件 | 与 Skill 同目录，命名不含空格 | `ls -la` 确认 |
| 网络环境 | 目标 URL 可公开访问 | `curl -I <url>` 返回 200 |
| 输出目录 | `./output/` 存在 | 不存在则自动创建 |
| 依赖库 | Python 3.8+，requests, beautifulsoup4 | `pip list` 检查 |

### 3.2 执行步骤

1. **准备输入**
   - 将待处理文件放入当前目录，确认命名规范（如 `page_01.html`）。
   - 若为 URL 列表，创建 `urls.txt`，每行一个 URL。

2. **试运行（单样本）**
   - 执行：`python main.py --input sample.html --output test.json`
   - 检查 `test.json` 字段是否完整，格式是否符合预期。

3. **批量执行**
   - 确认无误后，执行：`python main.py --input ./data/ --output ./output/ --batch`
   - 保留原始文件备份（Skill 不修改源文件）。

4. **校验结果**
   - 抽查 3-5 条输出，对比源数据核对关键字段（如标题、日期、链接）。
   - 检查 JSON 合法性：`python -m json.tool output.json > /dev/null`

### 3.3 输出规范

| 字段 | 类型 | 说明 |
|------|------|------|
| `source` | string | 原始 URL 或文件路径 |
| `extracted_at` | string (ISO 8601) | 抓取时间 |
| `data` | array/object | 结构化内容 |
| `status` | string | `success` / `partial` / `failed` |
| `error` | object \| null | 错误详情（如有） |

示例输出：

```json
{
  "source": "https://example.com/news",
  "extracted_at": "2026-08-15T10:30:00Z",
  "data": [
    {"title": "标题A", "url": "/news/a", "date": "2026-08-14"},
    {"title": "标题B", "url": "/news/b", "date": "2026-08-13"}
  ],
  "status": "success",
  "error": null
}
```

---

## 四、置信度门控

当遇到以下情况时，**不得编造数据**，必须输出占位符：

| 场景 | 占位符 | 说明 |
|------|--------|------|
| 字段缺失 | `[需核实:字段名]` | 如 `[需核实:date]` |
| 解析不确定 | `[需核实:内容]` | 无法确认提取是否正确 |
| 网络超时 | `[需核实:连接]` | 未获取到响应 |
| 编码异常 | `[需核实:编码]` | 无法识别字符集 |

**规则**：任何 `[需核实:...]` 出现时，`status` 必须设为 `partial`，并在 `error` 中注明原因。

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| `E001` | 文件不存在 | "未找到输入文件，请检查路径" | 确认文件路径，重新执行 |
| `E002` | URL 无法访问 | "目标 URL 返回非 200 状态码" | 检查 URL 拼写，或改用本地文件 |
| `E003` | 解析失败 | "HTML 结构不符合预期" | 检查页面是否改版，调整选择器 |
| `E004` | 编码错误 | "无法识别文件编码" | 指定 `--encoding utf-8` |
| `E005` | 输出目录不可写 | "无法写入输出文件" | 检查目录权限，或更换路径 |
| `E006` | 批量中断 | "批量处理在第 N 个文件失败" | 查看错误日志，跳过失败项重试 |

**错误处理流程**：

```
遇到错误 → 输出错误码 + 提示话术 → 记录到 error.log → 继续处理下一项（批量模式）
```

---

## 六、FAQ 反模式

### 6.1 常见坑

| 坑 | 反模式（错误做法） | 正确做法 |
|----|--------------------|----------|
| 忽略编码 | 直接读取文件不指定编码 | 始终指定 `--encoding utf-8` |
| 盲目信任选择器 | 页面改版后仍用旧选择器 | 试运行阶段先验证 1 条数据 |
| 不备份原始数据 | 直接覆盖源文件 | 输出到独立目录，保留源文件 |
| 忽略错误状态 | 只检查 `data` 字段 | 同时检查 `status` 和 `error` |
| 批量无中断 | 一个失败就全部停止 | 使用 `--continue-on-error` 跳过失败项 |

### 6.2 反模式对照表

| 反模式 | 后果 | 替代方案 |
|--------|------|----------|
| 用正则解析 HTML | 结构复杂时易出错 | 使用 BeautifulSoup 选择器 |
| 一次性抓取 1000 个 URL | 触发反爬机制 | 添加 `--delay 1` 间隔 |
| 输出无 schema 的 JSON | 下游解析困难 | 遵循 3.3 节输出规范 |
| 忽略 `[需核实]` 占位 | 数据质量不可控 | 对 `partial` 结果人工复核 |

---

## 七、渐进式披露

### 7.1 速查卡（30 秒上手）

```
1. 放文件 → 2. 试运行 → 3. 批量 → 4. 校验
命令：python main.py --input <文件或目录> --output <输出路径> [--batch]
```

### 7.2 新手路径（首次使用）

1. 阅读「能力边界」了解限制。
2. 按「标准流程」第 1-2 步执行单样本。
3. 对照「输出规范」检查结果。
4. 遇到问题查「错误码体系」。

### 7.3 进阶路径（熟练用户）

1. 自定义字段抽取规则（修改 `config.json` 中的选择器）。
2. 使用 `--delay` 和 `--retry` 参数优化批量采集。
3. 将输出接入自动化流水线（如 CI/CD）。
4. 扩展 `main.py` 添加自定义解析函数。

---

## 八、参数参考表

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `--input` | string | 必填 | 输入文件或目录 |
| `--output` | string | `./output/` | 输出路径 |
| `--batch` | flag | false | 批量模式 |
| `--encoding` | string | `utf-8` | 文件编码 |
| `--delay` | float | 0 | 请求间隔（秒） |
| `--continue-on-error` | flag | false | 失败后继续 |
| `--selftest` | flag | false | 运行自检 |
| `--version` | flag | false | 输出版本 |

---

## 用户协议

<!-- user-agreement-injected -->

**使用本 Skill 即表示您同意以下条款：**

1. **责任承担**：使用者自行承担因使用本 Skill 产生的全部责任，包括但不限于数据准确性、合规性、法律风险等。
2. **禁止反向工程**：不得对本 Skill 进行反向工程、反编译、破解或试图提取源代码（除非适用法律允许）。
3. **合规使用**：使用者应确保采集行为符合目标网站的服务条款及当地法律法规。
4. **无担保**：本 Skill 按"现状"提供，不提供任何明示或暗示的担保。
5. **免责**：因使用本 Skill 造成的任何直接或间接损失，作者不承担任何责任。

---

## 许可证（License）

<!-- professional-license-embedded -->

**MIT License**

```
MIT License

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
```

---

*本 Skill 由 AI 辅助生成，仅供参考。使用前请阅读相关文档。*
