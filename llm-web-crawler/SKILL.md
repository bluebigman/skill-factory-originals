---
slug: llm-web-crawler
name: llm-web-crawler
displayName: 网页采集 结构化提取 数据管道
description: 将网页、文件或原始文本转化为结构化数据，供LLM应用与自动化流程直接调用。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 林墨
agent_created: true
trigger_words: ["爬虫采集", "网页抓取", "数据提取", "结构化输出", "web scraper", "页面解析", "信息抽取"]
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# llm-web-crawler — 网页采集与结构化提取

本 Skill 由 AI 辅助生成，仅供参考。使用前请确认目标网站的服务条款与当地法律法规。

---

## 一、能力边界（一页纸速查卡）

### 能做

| 能力项 | 说明 |
|--------|------|
| 网页抓取 | 从 URL 获取 HTML 内容，支持 HTTP/HTTPS 协议 |
| 文件解析 | 读取本地 HTML、JSON、CSV、TXT 文件 |
| 原始文本处理 | 直接接收用户粘贴的文本片段 |
| 结构化输出 | 按预定义 schema 输出 JSON 格式数据 |
| 批量采集 | 支持多 URL 顺序抓取，可配置延迟与重试 |
| 自定义字段 | 通过修改选择器配置抽取指定字段 |

### 不能做

| 限制项 | 说明 |
|--------|------|
| 登录态维持 | 不处理需要 session 或 cookie 的页面 |
| JavaScript 渲染 | 不执行页面内 JS，SPA 页面可能抓取不到动态内容 |
| 反爬绕过 | 不提供代理池、验证码识别等反爬对抗能力 |
| 数据清洗 | 仅做字段抽取，不做语义去重或实体消歧 |
| 定时调度 | 不内置 cron 或定时触发机制 |

### 适用对象

- 需要从静态页面提取结构化信息的 LLM 应用
- 需要批量处理 URL 列表的自动化脚本
- 需要将网页内容接入下游数据管道的开发者

---

## 二、触发方式

当用户输入包含以下意图时，本 Skill 被激活：

| 用户说（大白话） | 触发词命中 | Skill 响应 |
|------------------|------------|------------|
| "帮我把这个网页里的商品价格抓下来" | 网页抓取、数据提取 | 执行单样本抓取并输出结构化 JSON |
| "这个页面上所有文章的标题和日期整理一下" | 信息抽取 | 按配置抽取标题、日期字段 |
| "我有 50 个链接，批量跑一下" | 批量采集 | 按顺序批量抓取并汇总结果 |
| "这段文字里提到的公司名和金额提取出来" | 原始文本处理 | 直接解析文本并输出字段 |

---

## 三、标准流程

### 前置条件

1. 确认目标 URL 可公开访问（无登录墙）
2. 确认目标页面为静态 HTML 或服务端渲染
3. 确认输出 schema 已定义（默认含 `title`、`content`、`url`、`timestamp` 四个字段）

### 执行步骤

**第 1 步：准备输入**

将待抓取内容放入 `input/` 目录：

- `urls.txt` — 每行一个 URL
- `files/` — 本地文件（HTML/JSON/CSV/TXT）
- `raw_text.txt` — 原始文本

**第 2 步：试运行（单样本）**

```bash
python main.py --url "https://example.com/page" --output sample_output.json
```

检查 `sample_output.json` 中字段是否完整、值是否符合预期。

**第 3 步：批量执行**

```bash
python main.py --input input/urls.txt --output results/ --delay 1.5 --retry 3
```

参数说明：

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--delay` | 1.0 | 两次请求间隔（秒），建议 ≥1 避免对目标服务器造成压力 |
| `--retry` | 2 | 失败重试次数，超过则跳过该 URL |
| `--timeout` | 10 | 单次请求超时（秒） |

**第 4 步：校验结果**

检查输出目录中的 `_summary.json`：

- `total_urls` — 总 URL 数
- `success_count` — 成功抓取数
- `failed_urls` — 失败列表及原因
- `avg_response_time` — 平均响应时间

### 输出规范

每个成功抓取的 URL 生成一个 JSON 文件，结构如下：

```json
{
  "url": "https://example.com/page",
  "title": "页面标题",
  "content": "正文文本（去除 HTML 标签）",
  "timestamp": "2025-01-15T10:30:00Z",
  "metadata": {
    "http_status": 200,
    "content_type": "text/html; charset=utf-8",
    "response_time_ms": 342
  }
}
```

---

## 四、置信度门控

当出现以下情况时，**不得编造数据**，必须输出占位符 `[需核实:字段名]`：

| 场景 | 处理方式 |
|------|----------|
| 页面元素未找到（选择器无匹配） | 该字段输出 `[需核实:title]` |
| 页面返回 403/404 | 整条记录标记 `"status": "failed"`，不输出字段 |
| 字段值格式异常（如日期解析失败） | 输出原始值 + `[需核实:date]` 后缀 |
| 批量任务中部分 URL 超时 | 该 URL 跳过，在 summary 中记录原因 |

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| `E001` | URL 格式无效 | "URL 格式不正确，请检查是否包含协议头（http/https）" | 补全协议头后重试 |
| `E002` | 连接超时 | "目标服务器响应超时，请检查网络或稍后重试" | 增加 `--timeout` 值或检查网络 |
| `E003` | HTTP 403 | "目标服务器拒绝访问，可能触发了反爬机制" | 增加 `--delay` 至 3 秒以上，或检查是否被 IP 封禁 |
| `E004` | 选择器无匹配 | "页面结构中未找到指定元素，可能页面结构已变更" | 检查 `config.json` 中的 CSS 选择器是否仍有效 |
| `E005` | 输出目录不可写 | "无法写入输出文件，请检查目录权限" | 确认输出路径存在且有写权限 |
| `E006` | 输入文件为空 | "输入文件为空，请确认 urls.txt 中至少有一行 URL" | 检查输入文件内容 |

---

## 六、FAQ 反模式

| 常见坑 | 反模式（错误做法） | 正模式（推荐做法） |
|--------|-------------------|-------------------|
| 抓取动态页面 | 直接抓取 SPA 页面，期望拿到完整内容 | 先确认页面是否服务端渲染；若是 SPA，改用浏览器渲染工具 |
| 请求频率过高 | 不设 delay 批量跑 1000 个 URL | 设置 `--delay 2` 以上，分批执行 |
| 忽略 robots.txt | 不管目标站点是否允许爬取 | 先查看 `robots.txt`，遵守 Disallow 规则 |
| 字段缺失时硬编码 | 页面缺字段时写死默认值 | 使用 `[需核实:字段]` 占位，保留原始可追溯性 |
| 不校验输出 | 批量跑完直接使用结果 | 先跑单样本，再抽查批量结果，最后看 summary |

---

## 七、渐进式披露

### 速查卡（30 秒上手）

```
1. 放 URL 到 input/urls.txt
2. python main.py --url "第一个URL" --output test.json
3. 看 test.json 字段对不对
4. python main.py --input input/urls.txt --output results/
5. 看 results/_summary.json
```

### 新手路径（首次使用）

1. 阅读「能力边界」确认场景匹配
2. 按「标准流程」第 1-2 步跑通单样本
3. 对照「输出规范」检查字段完整性
4. 遇到问题查「错误码体系」定位原因

### 进阶路径（熟练用户）

1. 修改 `config.json` 中的选择器，自定义抽取字段
2. 使用 `--delay` 和 `--retry` 参数优化批量采集稳定性
3. 将输出接入 CI/CD 管道，实现定时数据刷新
4. 扩展 `main.py` 添加自定义解析函数（如正则提取、嵌套 JSON 展开）

---

## 八、配置参考

`config.json` 默认结构：

```json
{
  "selectors": {
    "title": "h1",
    "content": "article",
    "date": "time"
  },
  "output_format": "json",
  "encoding": "utf-8",
  "user_agent": "Mozilla/5.0 (compatible; llm-web-crawler/1.0)"
}
```

自定义字段时，只需修改 `selectors` 中的键值对，键为输出字段名，值为 CSS 选择器。

---

## 用户协议

使用本 Skill 即表示您同意以下条款：

1. **责任承担**：使用者自行承担因使用本 Skill 产生的全部责任，包括但不限于数据准确性、合规性、法律风险等。
2. **禁止反向工程**：不得对本 Skill 进行反向工程、反编译、破解或试图提取源代码（除非适用法律允许）。
3. **合规使用**：使用者应确保采集行为符合目标网站的服务条款及当地法律法规。
4. **无担保**：本 Skill 按"现状"提供，不提供任何明示或暗示的担保。
5. **免责**：因使用本 Skill 造成的任何直接或间接损失，作者不承担任何责任。

<!-- user-agreement-injected -->

---

## 许可证（License）

MIT License

Copyright (c) 2025 林墨

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

<!-- professional-license-embedded -->
