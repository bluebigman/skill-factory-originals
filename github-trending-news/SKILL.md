---
slug: github-trending-news
name: github-trending-news
displayName: 开源热点 趋势追踪 周报生成
description: 抓取GitHub Trending，按语言与日期过滤，生成结构化周报。
version: 3.0.0
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

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->


> 📜 **用户协议（User Agreement）**
> 1. 本 Skill 仅供学习与参考用途。使用本 Skill 产生的任何结果，由使用者自行承担全部责任；本 Skill 不提供任何明示或暗示的保证。
> 2. 涉及法律、财务、税务、投资、医疗等专业决策时，请务必咨询持证专业人士。
> 3. 本代码受版权法保护，未经授权复制、反向工程或商业利用将被追究法律责任。
<!-- user-agreement-injected -->


# GitHub Trending 周报生成器

**一句话定位**：为开发者、技术团队负责人和开源爱好者，提供从 GitHub Trending 页面抓取数据、按语言/时间过滤、生成 Markdown/CSV/JSON 结构化周报的命令行工具，解决「每日手动刷 Trending 效率低、信息分散」的痛点。

---

## 快速开始 Quick Start

| 场景 (Situation) | 操作 (Action) | 预期结果 (Result) |
|---|---|---|
| 生成今日 Python 趋势周报 | `python run.py --language python --since daily --format md` | 在当前目录生成 `github_trending_python_daily_YYYY-MM-DD.md`，包含 Top 10 仓库列表 |
| 生成本周全语言 JSON 数据 | `python run.py --since weekly --format json --output ./data` | 在 `./data` 目录生成 JSON 文件，包含仓库名、描述、语言、stars 等结构化字段 |
| 预览本周趋势（不写盘） | `python run.py --since weekly --dry-run` | 终端打印将写入的文件路径与仓库数量摘要，不实际创建文件 |
| 运行自检 | `python run.py --selftest` | 执行真实抓取与解析流程，断言关键输出，退出码 0 表示通过 |

---

## 适用场景 When to Use

**什么时候用：**
- 需要每日/每周快速获取 GitHub 热门仓库列表，用于技术选型调研或竞品分析。
- 需要按编程语言（如 Python、JavaScript、Rust）过滤 Trending 数据。
- 需要将趋势数据导出为 Markdown 周报、CSV 表格或 JSON 供下游程序消费。
- 需要离线缓存数据，避免重复请求 GitHub 导致限流。

**什么时候不要用：**
- 需要精确的 star 增长曲线或历史回溯数据（Trending 页面本身不提供）。
- 需要访问私有仓库或需登录的 GitHub API 数据。
- 需要生成 PDF、PPT 等二进制格式报告（本工具仅输出文本格式）。
- 需要分析贡献者、代码质量或许可证合规性（超出本工具能力边界）。

---

## 能力总览 Capabilities

| 能力 | 命令/参数 | 示例 |
|---|---|---|
| 抓取 Trending 数据 | `--since {daily,weekly,monthly}` | `python run.py --since weekly` |
| 按语言过滤 | `--language {python,javascript,rust,...}` | `python run.py --language python` |
| 输出 Markdown 周报 | `--format md` | `python run.py --format md` |
| 输出 CSV 表格 | `--format csv` | `python run.py --format csv` |
| 输出 JSON 结构化数据 | `--format json` | `python run.py --format json` |
| 指定输出目录 | `--output <dir>` | `python run.py --output ./reports` |
| 预览不写盘 | `--dry-run` | `python run.py --dry-run` |
| 显示详细日志 | `--verbose` | `python run.py --verbose` |
| 运行自检 | `--selftest` | `python run.py --selftest` |
| 使用缓存 | `--no-cache` | `python run.py --no-cache`（默认启用 1 小时缓存） |

---

## 模块决策表 Decision Table

| 用户意图 | 推荐模块/命令 | 读取指引 |
|---|---|---|
| 快速生成今日趋势周报 | `run.py --since daily --format md` | 直接执行，输出到当前目录 |
| 获取本周 Python 仓库 JSON 数据 | `run.py --since weekly --language python --format json` | 指定语言与格式，输出到 `--output` 指定目录 |
| 排查抓取失败问题 | `run.py --verbose` | 查看详细错误日志与降级输出 |
| 批量生成多语言周报 | 循环调用 `run.py --language <lang>` | 每次指定不同语言，输出文件自动命名 |
| 集成到 CI 流水线 | `run.py --since weekly --format json --output ./artifacts` | 使用 JSON 格式，便于下游解析 |

---

## 示例 Examples

### 示例 1：生成今日 Python 趋势周报（Markdown）

```bash
python run.py --language python --since daily --format md
```

**输出文件**：`github_trending_python_daily_2026-08-09.md`

**内容片段**：
```markdown
# GitHub Trending 周报 (Python, daily)

生成时间: 2026-08-09 12:00:00 UTC

## Top 10 仓库

| # | 仓库 | 描述 | 语言 | Stars |
|---|------|------|------|-------|
| 1 | [owner/repo](https://github.com/owner/repo) | 示例描述 | Python | 1234 |
...
```

### 示例 2：获取本周全语言 JSON 数据

```bash
python run.py --since weekly --format json --output ./data
```

**输出文件**：`./data/github_trending_weekly_2026-08-09.json`

**内容片段**：
```json
[
  {
    "rank": 1,
    "repo": "owner/repo",
    "url": "https://github.com/owner/repo",
    "description": "示例描述",
    "language": "Python",
    "stars_today": 1234,
    "forks_today": 56,
    "stars_total": 10000
  }
]
```

### 示例 3：预览本周趋势（不写盘）

```bash
python run.py --since weekly --dry-run
```

**终端输出**：
```text
[DRY-RUN] 将写入文件: ./github_trending_weekly_2026-08-09.md
[DRY-RUN] 仓库数量: 25
[DRY-RUN] 未执行任何写盘操作。
```

---

## 安装与配置 Installation

### 依赖安装

```bash
pip install requests beautifulsoup4
```

> 如果未安装第三方库，脚本会自动降级使用 `urllib` 和 `html.parser`，功能不受影响。

### 环境变量

| 变量名 | 默认值 | 说明 |
|---|---|---|
| `GITHUB_TRENDING_URL` | `https://github.com/trending` | 自定义 Trending 页面 URL |
| `SKILL_OUTPUT_DIR` | `~/.workbuddy/skills/github-trending-news` | 默认输出目录 |
| `SKILL_CACHE_DIR` | `~/.workbuddy/cache/github-trending-news` | 缓存目录 |

---

## 常见问题 Troubleshooting

| 错误现象 | 原因 | 解决办法 |
|---|---|---|
| `E_NETWORK` 错误 | 网络不通或 GitHub 被墙 | 检查网络，或设置 `GITHUB_TRENDING_URL` 为代理地址 |
| `E_PARSE` 错误 | HTML 结构变化或编码异常 | 更新脚本或手动检查 Trending 页面 |
| 输出文件为空 | 抓取到 0 条数据 | 检查 `--since` 参数，或稍后重试 |
| 缓存导致数据过期 | 默认缓存 1 小时 | 使用 `--no-cache` 强制刷新 |

---

## 最佳实践 Best Practices

- **定期运行**：建议每日或每周定时运行，避免错过热点。
- **结合 CI**：将命令集成到 CI 流水线，自动生成周报并归档。
- **缓存策略**：默认启用 1 小时缓存，减少 GitHub 请求频率，避免限流。
- **数据校验**：生成 JSON 后，建议用 `jq` 或 Python 脚本校验数据完整性。

---

## 相关资源 Related

- [GitHub Trending 官方页面](https://github.com/trending)
- [GitHub REST API 文档](https://docs.github.com/en/rest)
- [BeautifulSoup 文档](https://www.crummy.com/software/BeautifulSoup/bs4/doc/)
- [Requests 文档](https://requests.readthedocs.io/en/latest/)

---

## 许可证 License

本项目基于 MIT 许可证开源。使用前请阅读 [LICENSE](LICENSE) 文件。