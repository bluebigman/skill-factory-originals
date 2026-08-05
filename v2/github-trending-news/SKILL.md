---
slug: github-trending-news
name: github_trending_reporter
displayName: 开源热点 趋势追踪 周报生成
description: 抓取GitHub Trending，按语言与日期过滤，生成结构化周报。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: trend-craft-studio
agent_created: true
trigger_words: ["github trending", "趋势周报", "开源热点", "仓库排行", "trending 报告"]
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# GitHub Trending 周报生成器

## 一、能力边界：一页纸速查卡

| 维度 | 能做 | 不能做 |
|------|------|--------|
| 数据获取 | 抓取 GitHub Trending 页面公开数据 | 访问需登录的私有仓库、GitHub API 限流外的批量请求 |
| 过滤维度 | 按编程语言（如 Python、JavaScript）、时间范围（今日/本周/本月）过滤 | 按 stars 绝对数值精确排序（Trending 页面本身不提供） |
| 输出格式 | 生成 Markdown 周报、CSV 表格、JSON 结构化数据 | 生成 PDF、PPT 等二进制格式 |
| 语言支持 | 中英文双语输出 | 其他语种翻译 |
| 附加能力 | 仓库描述摘要、语言占比统计、星标增速估算 | 贡献者分析、代码质量评估、许可证合规审查 |

**适用对象**：开发者、技术团队负责人、开源爱好者、技术情报分析人员。

**不适用场景**：需要精确 star 增长曲线的量化分析、需要仓库历史数据的回溯研究。

---

## 二、触发方式：场景映射表

| 用户说（大白话） | 触发动作 | 参数提取 |
|------------------|----------|----------|
| "看看这周 Python 有什么火的项目" | 抓取 Trending，语言=Python，周期=本周 | language=python, since=weekly |
| "帮我整理一份今天的 GitHub 热门" | 抓取 Trending，周期=今日 | since=daily |
| "最近 Go 语言有什么新东西" | 抓取 Trending，语言=Go，周期=本周 | language=go, since=weekly |
| "生成一份上周的 JavaScript 趋势报告" | 抓取 Trending，语言=JavaScript，周期=上周 | language=javascript, since=weekly, date=上周 |
| "GitHub 上现在最火的是什么" | 抓取 Trending，无语言过滤，周期=今日 | since=daily |

**触发词补充**：`trending 抓取`、`仓库热度`、`开源动态`、`项目周报`

---

## 三、标准流程

### 前置条件

| 条件 | 说明 | 检查方式 |
|------|------|----------|
| 网络连通 | 可访问 github.com | `curl -sI https://github.com/trending` 返回 200 |
| 无 IP 封禁 | 未被 GitHub 限流 | 连续请求间隔 ≥ 2 秒 |
| 参数合法 | 语言为 GitHub 支持的语言别名 | 参考 [GitHub 语言列表](https://github.com/trending) 页面下拉框 |

### 执行步骤

1. **解析用户意图**：从输入中提取 `language`（可选）和 `since`（必选，默认 daily）参数。
   - 支持的语言别名映射：`py`→`python`，`js`→`javascript`，`ts`→`typescript`，`go`→`go`，`rust`→`rust`，`cpp`→`c++`。
   - 时间参数映射：`今天/今日`→`daily`，`本周/这周`→`weekly`，`本月/这月`→`monthly`。

2. **构造请求 URL**：
   ```
   https://github.com/trending/{language}?since={since}
   ```
   无语言过滤时：`https://github.com/trending?since={since}`

3. **抓取页面**：使用 HTTP GET 请求，设置 `User-Agent` 为常见浏览器标识，超时 10 秒。

4. **解析 HTML**：定位 `.Box-row` 元素，提取以下字段：
   - `repo_name`：仓库全名（owner/repo）
   - `description`：描述文本（去除多余空白）
   - `language`：主要语言
   - `stars_today`：今日新增 star 数（`<span class="d-inline-block float-sm-right">` 内的文本）
   - `forks`：fork 数
   - `url`：仓库链接

5. **数据清洗**：
   - 去除 HTML 标签和多余空白字符
   - 将 `stars_today` 中的 `,` 去除后转为整数
   - 描述为空时标记为 `[无描述]`

6. **生成报告**：按用户指定格式输出（默认 Markdown）。

7. **输出规范**：
   - Markdown 格式：表格 + 分节，按 star 增量降序排列
   - CSV 格式：`仓库名,描述,语言,今日Star,总Star,Fork数,链接`
   - JSON 格式：数组对象，字段名与 CSV 表头一致

### 输出示例（Markdown）

```markdown
# GitHub Trending 周报（2025-01-06 ~ 2025-01-12）

## Python 语言趋势

| 排名 | 仓库 | 描述 | 本周 Star | 总 Star | 链接 |
|------|------|------|-----------|---------|------|
| 1 | owner/repo-a | AI 推理加速框架 | +1,234 | 12,345 | [链接](https://github.com/owner/repo-a) |
| 2 | owner/repo-b | 异步任务队列 | +890 | 8,901 | [链接](https://github.com/owner/repo-b) |
```

---

## 四、置信度门控

| 场景 | 处理方式 |
|------|----------|
| 页面请求失败（网络错误） | 输出 `[需核实:网络连接]`，提示用户检查网络后重试 |
| 页面返回 403/429 | 输出 `[需核实:IP限流]`，建议等待 5 分钟后重试 |
| 语言参数无效 | 输出 `[需核实:语言参数]`，列出支持的语言列表 |
| 解析结果为空 | 输出 `[需核实:无数据]`，可能是 Trending 页面结构变更 |
| 描述字段缺失 | 保留 `[无描述]` 占位，不编造内容 |
| star 增量无法解析 | 输出 `[需核实:star数据]`，保留原始文本供人工确认 |

**铁律**：任何字段无法确认时，使用 `[需核实:字段名]` 占位，禁止猜测或编造数据。

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| E001 | 网络不可达 | "无法连接 GitHub，请检查网络设置" | 1. 检查网络连通性 2. 确认无防火墙拦截 3. 重试 |
| E002 | HTTP 403 | "GitHub 拒绝了请求，可能触发了限流" | 1. 等待 5 分钟 2. 降低请求频率 3. 更换 User-Agent |
| E003 | HTTP 429 | "请求过于频繁，已被限流" | 1. 增加请求间隔至 5 秒以上 2. 使用代理 IP 3. 稍后重试 |
| E004 | 解析失败 | "页面结构解析失败，可能页面已改版" | 1. 检查页面结构 2. 更新解析规则 3. 报告问题 |
| E005 | 参数错误 | "语言参数不支持，请参考支持列表" | 1. 查看支持的语言列表 2. 修正参数 3. 重新执行 |
| E006 | 无数据 | "当前条件下没有找到任何仓库" | 1. 放宽时间范围 2. 尝试其他语言 3. 确认日期有效性 |

---

## 六、FAQ 反模式

| 常见坑 | 反模式（错误做法） | 正模式（正确做法） |
|--------|-------------------|-------------------|
| 请求频率过高 | 连续快速请求多个页面 | 每次请求间隔 ≥ 2 秒，批量请求时使用队列 |
| 忽略 User-Agent | 使用默认 Python/curl UA | 设置浏览器 UA，降低被识别为爬虫的概率 |
| 硬编码解析规则 | 假设页面结构永远不变 | 解析失败时输出错误码 E004，不静默失败 |
| 编造缺失数据 | 描述为空时自行补写 | 使用 `[无描述]` 占位，保持数据真实性 |
| 忽略时间参数 | 总是使用 daily 而忽略用户指定 | 严格按用户输入映射 since 参数 |
| 输出格式混乱 | 混合多种格式输出 | 按用户指定格式输出，默认 Markdown |

---

## 七、渐进式披露

### 速查卡（30 秒上手）

```
输入示例："本周 Python 趋势"
→ 参数: language=python, since=weekly
→ 输出: Markdown 表格周报
```

### 新手路径（首次使用）

1. 阅读「能力边界」了解工具范围
2. 使用「触发方式」中的示例语句发起请求
3. 查看「标准流程」了解内部处理逻辑
4. 遇到问题参考「错误码体系」定位原因

### 进阶路径（深度使用）

1. 自定义输出格式（CSV/JSON）用于程序化处理
2. 结合 CI/CD 定时触发周报生成
3. 二次开发扩展数据源（如加入 Hacker News 热度对比）
4. 将输出接入 Slack/飞书机器人实现自动推送

---

## 八、用户协议

<!-- user-agreement-injected -->

**使用本 Skill 即表示您同意以下条款：**

1. **责任承担**：使用者自行承担因使用本 Skill 产生的全部责任，包括但不限于数据准确性、合规性、以及因依赖本工具输出所做的任何决策。
2. **禁止反向工程**：不得对本 Skill 的提示词、逻辑流程、内部参数进行反向工程、破解、提取或用于商业竞品分析。
3. **数据使用**：本 Skill 输出的数据来源于 GitHub 公开页面，使用者应遵守 GitHub 的服务条款和 robots.txt 规范。
4. **无担保声明**：本 Skill 按"现状"提供，不附带任何明示或暗示的担保，包括但不限于适销性、特定用途适用性。
5. **免责范围**：因网络波动、GitHub 页面改版、第三方服务故障导致的数据缺失或错误，本 Skill 作者不承担责任。

---

## 九、许可证（License）

<!-- professional-license-embedded -->

**MIT License**

```
MIT License

Copyright (c) 2025 trend-craft-studio

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
