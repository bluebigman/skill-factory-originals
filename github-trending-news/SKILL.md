---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: github-trending-news
name: github-trending-news
displayName: 开源热点追踪 趋势周报 仓库排行
description: 抓取GitHub Trending，按语言与日期过滤，生成结构化周报。
version: 3.0.1
rules_version: cpr-20260810-n301
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/github-trending-news
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: OpenSourcePulse
agent_created: true
trigger_words: ["github trending", "趋势周报", "开源热点", "仓库排行", "trending 报告", "热门项目", "开源动态"]
---

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->


> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# GitHub Trending 趋势周报 Skill 文档

## 一、能力边界：一页纸速查卡

### 1.1 能做什么

| 能力项 | 说明 | 示例 |
|--------|------|------|
| 抓取 Trending 数据 | 从 GitHub Trending 页面获取当前热门仓库列表 | 获取今日 Python 趋势榜 |
| 按语言过滤 | 支持指定编程语言（如 Python、JavaScript、Rust） | 只看 TypeScript 项目 |
| 按日期范围过滤 | 支持 since=daily / weekly / monthly 三种时间窗口 | 本周趋势 vs 本月趋势 |
| 生成结构化周报 | 将原始数据整理为 Markdown 格式报告，含仓库名、描述、星标数、今日增星等字段 | 输出一份可直接发布的周报 |
| 多仓库对比 | 对多个仓库的星标增速、Fork 数进行横向比较 | 比较两个 AI 框架的热度 |

### 1.2 不能做什么

| 限制项 | 说明 |
|--------|------|
| 不抓取非 Trending 页面 | 不提供 GitHub 全局搜索、用户主页、组织仓库等非 Trending 数据 |
| 不提供历史趋势回溯 | 仅能获取当前 Trending 快照，无法查询 30 天前的历史榜单 |
| 不解析代码内容 | 只处理仓库元数据（名称、描述、星标等），不分析代码质量或实现细节 |
| 不保证数据实时性 | 依赖 GitHub Trending 页面更新频率，通常为小时级延迟 |
| 不提供星标预测 | 不基于历史数据预测未来星标增长趋势 |

### 1.3 适用对象

- **开源爱好者**：快速了解本周值得关注的新项目
- **技术选型人员**：对比同领域热门仓库的社区活跃度
- **内容创作者**：生成技术周报、月度开源盘点素材
- **开发者**：发现与自己技术栈相关的新工具、新框架

---

## 二、触发方式：场景映射表

| 触发词/短语 | 用户意图 | 实际执行动作 |
|-------------|----------|--------------|
| "github trending" | 查看当前热门仓库 | 抓取默认（daily）Trending 数据并输出列表 |
| "趋势周报" | 生成一周汇总报告 | 抓取 weekly 数据，按语言分组输出 Markdown 周报 |
| "开源热点" | 了解近期热门项目 | 抓取 weekly 数据，按星标增速排序输出 Top 20 |
| "仓库排行" | 获取排行榜 | 抓取指定语言 + 指定时间窗口的数据，按星标数排序 |
| "trending 报告" | 生成结构化报告 | 同"趋势周报"，但输出格式更详细（含描述、链接） |
| "热门项目" | 查看热门仓库 | 同"github trending"，默认 daily 窗口 |
| "开源动态" | 了解近期开源社区动态 | 抓取 weekly 数据，输出新增仓库 + 星标激增仓库 |

**参数补充**：用户可在触发词后附加语言和时间窗口，如"Python 本周趋势"、"Rust 月度排行"。

---

## 三、标准流程

### 3.1 前置条件

| 条件 | 要求 | 检查方式 |
|------|------|----------|
| 网络连接 | 可访问 github.com | 执行 `curl -sI https://github.com/trending` 返回 200 |
| 依赖库 | Python 3.8+，requests、beautifulsoup4 | `pip list` 确认已安装 |
| 输出目录 | 当前工作目录可写 | `touch .write_test` 成功 |

### 3.2 执行步骤

1. **解析用户输入**：提取语言（可选）、时间窗口（daily/weekly/monthly，默认 daily）
2. **构造请求 URL**：
   - 基础 URL：`https://github.com/trending`
   - 语言参数：`/{language}`（如 `/python`）
   - 时间参数：`?since={daily|weekly|monthly}`
   - 示例：`https://github.com/trending/python?since=weekly`
3. **发送 HTTP 请求**：设置 User-Agent 头（`Mozilla/5.0 (compatible; TrendingBot/1.0)`），超时 10 秒
4. **解析 HTML**：使用 BeautifulSoup 定位 `article.Box-row` 元素，提取以下字段：
   - `repo_name`：仓库全名（如 `owner/repo`）
   - `description`：项目描述（无则置空）
   - `language`：主要编程语言（无则置空）
   - `stars_total`：总星标数（去除逗号）
   - `stars_today`：今日/本周/本月新增星标（从 `float` 标签提取）
   - `forks`：Fork 数
   - `url`：仓库链接
5. **数据清洗**：去除空条目、去重（按 repo_name）、按 stars_today 降序排列
6. **生成报告**：按用户指定格式输出（列表 / 周报 / 排行榜）
7. **返回结果**：输出 Markdown 格式报告

### 3.3 输出规范

**默认列表格式**（触发词为 "github trending" 时）：

```
## GitHub Trending（2026-08-10，每日）

| 排名 | 仓库 | 描述 | 语言 | 总星标 | 今日增星 |
|------|------|------|------|--------|----------|
| 1 | owner/repo | 项目描述 | Python | 12,345 | +567 |
| 2 | owner/repo2 | 项目描述2 | Rust | 8,901 | +432 |
```

**周报格式**（触发词为 "趋势周报" 时）：

```
# 开源趋势周报（2026-08-04 ~ 2026-08-10）

## Python 热门项目
### 1. owner/repo
- **描述**：xxx
- **总星标**：12,345
- **本周增星**：+1,234
- **链接**：https://github.com/owner/repo

## JavaScript 热门项目
...
```

**排行榜格式**（触发词为 "仓库排行" 时）：

```
## Top 20 仓库排行（本周）

| 排名 | 仓库 | 语言 | 总星标 | 周增星 |
|------|------|------|--------|--------|
| 1 | owner/repo | Python | 12,345 | +1,234 |
...
```

---

## 四、置信度门控

### 4.1 数据可信度分级

| 数据字段 | 可信度 | 说明 |
|----------|--------|------|
| repo_name | 高 | 直接从 HTML 提取，结构固定 |
| url | 高 | 由 repo_name 拼接生成 |
| stars_total | 中 | 从 HTML 文本提取，可能因页面渲染差异有偏差 |
| stars_today | 中 | 从 `float` 标签提取，格式可能变化 |
| description | 低 | 可能缺失、截断或包含非 ASCII 字符 |
| language | 低 | 可能缺失（未标注语言的仓库） |

### 4.2 占位符规则

当以下情况出现时，使用 `[需核实:字段名]` 占位，不编造数据：

- 描述缺失：`[需核实:description]`
- 语言缺失：`[需核实:language]`
- 星标数解析失败：`[需核实:stars_total]`
- 增星数解析失败：`[需核实:stars_today]`

### 4.3 数据完整性检查

- 若单次抓取结果少于 5 条，输出警告：`数据量异常（<5条），可能页面结构变更或网络异常`
- 若连续 3 次请求失败，终止流程并提示用户检查网络

---

## 五、错误码体系

| 错误码 | 错误场景 | 用户提示话术 | 修正步骤 |
|--------|----------|--------------|----------|
| E001 | 网络无法连接 github.com | "无法访问 GitHub，请检查网络连接或代理设置" | 1. 检查网络；2. 设置代理环境变量 `HTTPS_PROXY`；3. 重试 |
| E002 | HTTP 返回非 200 状态码 | "GitHub 返回异常状态码 {code}，可能被限流或页面变更" | 1. 等待 5 分钟后重试；2. 更换 User-Agent；3. 检查是否触发反爬 |
| E003 | HTML 解析失败（找不到 `article.Box-row`） | "页面结构解析失败，GitHub 可能更新了页面布局" | 1. 更新 BeautifulSoup 选择器；2. 手动访问页面确认结构 |
| E004 | 语言参数无效 | "不支持的语言：{lang}，请使用 GitHub 官方语言列表中的名称" | 1. 参考 https://github.com/trending 页面左侧语言列表；2. 重新输入 |
| E005 | 时间窗口参数无效 | "时间窗口仅支持 daily、weekly、monthly" | 1. 检查输入；2. 使用默认值 daily |
| E006 | 数据为空 | "未获取到任何仓库数据，请稍后重试" | 1. 确认 Trending 页面是否有数据；2. 检查网络；3. 重试 |

---

## 六、FAQ 反模式对照

### 6.1 常见坑

| 坑 | 反模式描述 | 正确做法 |
|----|------------|----------|
| 坑 1：忽略 User-Agent | 使用默认 requests User-Agent 导致被 GitHub 拒绝 | 设置浏览器风格 User-Agent，如 `Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36` |
| 坑 2：硬编码选择器 | 直接使用 `div.repo-list` 等旧选择器，页面更新后失效 | 使用 `article.Box-row` 并定期验证；解析失败时输出 E003 错误 |
| 坑 3：不处理分页 | Trending 只有一页，但误以为有多页而循环请求 | Trending 页面无分页，单次请求即可获取全部数据 |
| 坑 4：忽略时区 | 使用本地时间而非 UTC 时间标记数据 | 统一使用 UTC 时间（`datetime.utcnow()`）标记抓取时间 |
| 坑 5：星标数格式混乱 | 直接拼接字符串导致 "1,234" 和 "1234" 混用 | 统一去除逗号转 int，输出时再格式化 |

### 6.2 反模式对照表

| 反模式 | 问题 | 替代方案 |
|--------|------|----------|
| 抓取所有语言不指定 | 数据量大且混杂，用户难以筛选 | 默认按用户指定语言过滤；未指定时输出全部但按语言分组 |
| 只输出仓库名不输出描述 | 用户无法判断项目用途 | 始终包含 description 字段（缺失时用占位符） |
| 不排序直接输出 | 数据顺序与页面一致，非按热度排序 | 按 stars_today 降序排列 |
| 忽略异常直接返回空列表 | 用户无法区分"无数据"和"抓取失败" | 区分 E006（无数据）和 E001/E002（网络错误） |

---

## 七、渐进式披露：分层次阅读路径

### 7.1 速查卡（30 秒上手）

```
用法：github trending [语言] [时间窗口]
示例：
  github trending                    → 今日全语言热门
  github trending python             → 今日 Python 热门
  github trending rust weekly        → 本周 Rust 热门
  github trending javascript monthly → 本月 JavaScript 热门
```

### 7.2 新手路径（5 分钟掌握）

1. 阅读「能力边界」了解能做什么、不能做什么
2. 使用「触发方式」中的示例命令体验基本功能
3. 遇到问题查「错误码体系」对照解决
4. 查看「输出规范」了解报告格式

### 7.3 进阶路径（深度使用）

1. 阅读「标准流程」了解内部实现机制
2. 修改「执行步骤」中的选择器以适配页面变更
3. 扩展「输出规范」增加自定义字段（如 `topics`、`license`）
4. 结合「置信度门控」设计数据校验逻辑
5. 参考「FAQ 反模式」优化抓取稳定性

---

## 八、实现参考（Python 伪代码）

```python
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

def fetch_trending(language=None, since="daily"):
    """抓取 GitHub Trending 数据"""
    url = "https://github.com/trending"
    if language:
        url += f"/{language}"
    url += f"?since={since}"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
    except requests.RequestException as e:
        return {"error": "E001", "message": str(e)}
    
    if resp.status_code != 200:
        return {"error": "E002", "code": resp.status_code}
    
    soup = BeautifulSoup(resp.text, "html.parser")
    articles = soup.select("article.Box-row")
    if not articles:
        return {"error": "E003"}
    
    repos = []
    for article in articles:
        repo_name = article.select_one("h2 a").text.strip().replace(" ", "")
        description_el = article.select_one("p")
        description = description_el.text.strip() if description_el else "[需核实:description]"
        language_el = article.select_one("[itemprop='programmingLanguage']")
        language = language_el.text.strip() if language_el else "[需核实:language]"
        stars_total_el = article.select_one("a[href$='/stargazers']")
        stars_total = stars_total_el.text.strip().replace(",", "") if stars_total_el else "[需核实:stars_total]"
        stars_today_el = article.select_one("span.float-sm-right")
        stars_today = stars_today_el.text.strip().split()[0] if stars_today_el else "[需核实:stars_today]"
        
        repos.append({
            "repo_name": repo_name,
            "description": description,
            "language": language,
            "stars_total": stars_total,
            "stars_today": stars_today,
            "url": f"https://github.com/{repo_name}"
        })
    
    repos.sort(key=lambda x: x["stars_today"], reverse=True)
    return {"data": repos, "fetched_at": datetime.utcnow().isoformat()}
```

---

## 九、用户协议

<!-- user-agreement-injected -->

**使用本 Skill 即表示您同意以下条款：**

1. **责任承担**：使用者自行承担使用本 Skill 产生的全部责任。包括但不限于因数据抓取导致的 IP 封禁、因报告内容引发的任何争议、因依赖本 Skill 输出做出的任何决策后果。
2. **禁止反向工程**：不得对本 Skill 的提示词、内部逻辑、输出模板进行反向工程、破解、提取或用于训练竞争性模型。
3. **数据使用**：本 Skill 抓取的 GitHub 数据版权归 GitHub 及相应仓库所有者所有，使用者应遵守 GitHub 服务条款及相应仓库的开源许可证。
4. **无担保**：本 Skill 按"现状"提供，不附带任何明示或暗示的担保，包括但不限于适销性、特定用途适用性和非侵权保证。
5. **更新与终止**：作者保留随时修改、更新或终止本 Skill 的权利，恕不另行通知。

---

## 十、许可证（License）

<!-- professional-license-embedded -->

**MIT License**

Copyright (c) 2026 OpenSourcePulse

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
