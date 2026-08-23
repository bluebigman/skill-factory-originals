---
slug: crawlee-python
name: crawlee-python
displayName: 网页采集 结构化抽取 数据清洗
description: 将网页或文件批量转为结构化数据，支持校验与备份。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 数据工坊
agent_created: true
trigger_words: ["爬虫采集","网页抓取","数据抽取","爬虫","crawlee","页面解析","列表提取"]
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# Crawlee Python 网页采集技能

## 一、能力边界速查卡

本技能基于 Crawlee 框架，用于将指定 URL 或本地文件中的非结构化内容转换为结构化数据（如 JSON、CSV）。以下表格明确列出能力范围与限制。

| 维度 | 能做 | 不能做 |
|------|------|--------|
| 输入类型 | 单个 URL、批量 URL 列表、本地 HTML/文本文件 | 图片验证码识别、登录墙后的动态内容（需额外配置） |
| 输出格式 | JSON、CSV、Excel（需自行扩展） | 直接写入数据库（需二次开发） |
| 数据抽取 | 基于 CSS 选择器、XPath、正则表达式的字段提取 | 语义理解（如判断文章情感倾向） |
| 反爬处理 | 基础请求头伪装、请求间隔设置 | 自动解决滑块验证、IP 池轮换 |
| 运行规模 | 单机多线程（建议 ≤ 50 并发） | 分布式集群调度 |

**适用对象**：需要从新闻网站、商品列表、公开文档中批量提取结构化字段的个人开发者或小团队。不适合需要登录态、强反爬或实时流式数据的场景。

---

## 二、触发方式与场景映射

当你的请求中包含以下关键词时，本技能将被激活。下表列出典型用户表述与对应操作。

| 触发词 | 用户可能说 | 技能响应 |
|--------|------------|----------|
| 爬虫采集 | "帮我爬一下这个网站的商品列表" | 解析 URL，提取列表字段 |
| 网页抓取 | "把这几篇文章的标题和正文抓下来" | 按选择器抽取正文内容 |
| 数据抽取 | "从这份 HTML 文件里抽出表格数据" | 读取本地文件，结构化输出 |
| 爬虫 / crawlee | "用 crawlee 写个爬虫脚本" | 生成可执行的 Crawlee 脚本 |
| 页面解析 | "解析这个页面的所有链接" | 提取 href 与锚文本 |

**场景示例**：
- 输入："抓取 https://example.com/news 下所有新闻的标题、日期和正文"
- 输出：包含 `title`、`date`、`content` 字段的 JSON 数组。

---

## 三、标准执行流程

### 前置条件

1. 确认目标 URL 可公开访问，或本地文件路径正确。
2. 将待处理的本地文件放入当前工作目录，文件名需符合 `input_*.html` 或 `data_*.txt` 的命名规范（可自定义）。
3. 检查 Python 环境已安装 `crawlee` 与 `beautifulsoup4`（若未安装，执行 `pip install crawlee beautifulsoup4`）。

### 执行步骤

1. **单样本试运行**  
   选取一条最小数据（如一个 URL 或一个文件），运行以下命令验证抽取逻辑：
   ```bash
   python run_crawler.py --url "https://example.com/single-page" --fields title,date,content
   ```
   检查输出 JSON 中字段是否完整、类型是否正确。

2. **字段配置确认**  
   若默认选择器未命中目标字段，需在配置文件中调整 CSS 选择器或 XPath。示例配置：
   ```json
   {
     "selectors": {
       "title": "h1.article-title",
       "date": "time.publish-date",
       "content": "div.article-body"
     }
   }
   ```

3. **批量执行**  
   确认单样本无误后，对全量数据执行：
   ```bash
   python run_crawler.py --input urls.txt --output result.json --concurrency 10
   ```
   执行前自动备份原始输入文件至 `backup/` 目录。

4. **结果校验**  
   随机抽取输出中的 5-10 条记录，与源页面人工比对关键字段（如标题、价格、日期）。若偏差率超过 2%，需回退至步骤 2 调整选择器。

### 输出规范

- 输出文件为 UTF-8 编码的 JSON 数组，每个对象包含 `url`（来源地址）与抽取字段。
- 字段缺失时以 `null` 填充，不跳过记录。
- 输出文件命名规则：`output_YYYYMMDD_HHMMSS.json`。

---

## 四、置信度门控

当遇到以下情况时，技能不会编造数据，而是输出占位符：

| 场景 | 输出行为 |
|------|----------|
| 页面元素未找到 | 字段值输出 `[需核实:字段名]` |
| 网络请求超时 | 该条记录标记 `"status": "timeout"`，不重试 |
| 文件编码无法识别 | 提示错误码 `E1003`，跳过该文件 |
| 字段类型不匹配（如日期格式错误） | 原样保留字符串，附加 `"_raw": true` 标记 |

**示例**：
```json
{
  "url": "https://example.com/page-1",
  "title": "[需核实:title]",
  "date": "2024-01-15",
  "content": "正文内容..."
}
```

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| E1001 | URL 格式无效 | "地址格式有误，请检查是否包含 http(s)://" | 重新输入完整 URL |
| E1002 | 页面返回 404 | "目标页面不存在，可能已下架" | 确认 URL 拼写或更换来源 |
| E1003 | 文件编码不支持 | "文件编码需为 UTF-8 或 GBK" | 用文本编辑器转换编码后重试 |
| E1004 | 选择器未命中 | "未找到匹配元素，请检查页面结构" | 使用浏览器开发者工具重新定位选择器 |
| E1005 | 并发数超限 | "并发数需在 1-50 之间" | 调整 `--concurrency` 参数 |

---

## 六、FAQ 与反模式对照

| 常见坑（反模式） | 正确做法 |
|------------------|----------|
| 直接对全量数据执行，未先试运行 | 务必先用单样本验证，避免批量失败 |
| 忽略请求间隔，导致 IP 被封 | 设置 `--delay 2`（秒）或随机间隔 1-3 秒 |
| 输出文件覆盖原文件 | 技能自动备份至 `backup/`，但用户不应手动指定输出路径与输入相同 |
| 依赖默认选择器不检查页面更新 | 每次执行前抽查 1-2 条记录，确认选择器仍有效 |
| 将错误记录直接丢弃 | 保留错误记录并标记状态，便于事后补采 |

---

## 七、渐进式阅读路径

### 速查卡（30 秒上手）

1. 准备 URL 或文件 → 2. 运行单样本命令 → 3. 检查输出 → 4. 批量执行 → 5. 抽查校验。

### 新手路径（首次使用）

- 阅读「能力边界速查卡」了解限制。
- 按「标准执行流程」步骤 1-2 完成首次试运行。
- 遇到问题对照「错误码体系」排查。

### 进阶路径（深度定制）

- 修改 `selectors` 配置以适配复杂页面。
- 扩展输出格式（如 CSV）需修改脚本中的序列化逻辑。
- 结合 `crawlee` 官方文档实现登录态或分页抓取。

---

## 用户协议

使用本 Skill 即表示您同意以下条款：

1. **责任承担**：使用者自行承担因使用本技能产生的全部责任，包括但不限于数据合规性、目标网站服务条款遵守情况。
2. **禁止反向工程**：不得对本技能生成的代码或配置进行反向工程、反编译或试图提取底层算法。
3. **合法用途**：本技能仅用于合法数据采集，使用者需确保目标网站允许爬取，并遵守相关法律法规。

<!-- user-agreement-injected -->

---

## 许可证（License）

本技能基于 MIT 许可证发布。MIT 许可证全文如下：

```
MIT License

Copyright (c) 2024 数据工坊

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
