---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: github-trending-reporter
name: github_trending_reporter
displayName: 开源趋势 周报生成 项目雷达
description: 抓取GitHub Trending，自动生成结构化开源项目周报，支持语言与周期筛选。
version: 1.0.4
rules_version: cpr-20260815-n476
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/github-trending-reporter
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: Lin Chen
agent_created: true
trigger_words: ["github trending", "trending 周报", "开源项目周报", "trending 日报", "开源趋势", "开源项目榜单", "GitHub 热门仓库"]
---

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->


> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# GitHub Trending 周报生成器（Skill 文档）

## 一、能力边界：能做什么，不能做什么

本 Skill 是一个**命令行工具包**，用于抓取 GitHub Trending 页面数据，并按指定周期（日/周/月）和语言筛选，生成结构化的 Markdown 周报。它适合开发者、技术团队负责人、开源爱好者快速掌握近期热门项目动态。

### ✅ 能做的事

| 功能项 | 说明 | 示例 |
|--------|------|------|
| 抓取 Trending 数据 | 从 GitHub Trending 页面获取当前热门仓库列表 | `github-trending --since weekly` |
| 语言筛选 | 按编程语言过滤仓库 | `--language python` |
| 周期筛选 | 支持 today / weekly / monthly 三种时间窗口 | `--since monthly` |
| 输出 Markdown 报告 | 默认生成结构化 Markdown 文件，含仓库名、描述、星标数、今日新增星标、语言、链接 | 见「输出规范」 |
| 交互模式 | 不带参数运行，进入问答式引导 | `github-trending` |
| 自检功能 | 验证环境依赖与网络连通性 | `--selftest` |
| 版本查询 | 输出当前版本号 | `--version` |

### ❌ 不能做的事

| 限制项 | 说明 |
|--------|------|
| 不提供历史数据回溯 | 仅能抓取 GitHub Trending 当前页面数据，无法获取过去某天的快照 |
| 不保证数据实时性 | 抓取结果取决于 GitHub 页面渲染状态，可能存在延迟或缺失 |
| 不做语义分析 | 不会对仓库内容进行 AI 解读，仅做结构化提取 |
| 不提供多平台聚合 | 仅支持 GitHub Trending，不包含 Hugging Face、Gitee 等平台 |
| 不自动推送通知 | 生成报告后需自行集成通知渠道（如 Slack、邮件） |

### 👥 适用对象

- **个人开发者**：快速发现值得关注的新库、新工具
- **技术团队负责人**：每周向团队同步开源生态动态
- **技术内容创作者**：为公众号、Newsletter 提供素材
- **技术选型调研者**：观察某一语言/领域的热门项目趋势

---

## 二、触发方式：怎么叫醒它

### 触发词一览

| 触发词 | 场景说明 |
|--------|----------|
| `github trending` | 最直接的触发方式，等同于运行主命令 |
| `trending 周报` | 想要生成周报时使用 |
| `开源项目周报` | 中文场景下的自然语言触发 |
| `trending 日报` | 想要生成日报时使用 |
| `开源趋势` | 泛化触发，进入交互模式 |
| `开源项目榜单` | 同义触发词 |
| `GitHub 热门仓库` | 同义触发词 |

### 大白话场景映射表

| 你说的话 | Skill 会做什么 |
|----------|----------------|
| "帮我看看这周 GitHub 上 Python 有什么火的" | 执行 `github-trending --language python --since weekly` |
| "今天有什么新项目值得关注？" | 执行 `github-trending --since today` |
| "我想生成一份月度开源报告" | 执行 `github-trending --since monthly` |
| "先检查一下环境能不能用" | 执行 `github-trending --selftest` |
| "直接给我一份默认周报" | 执行 `github-trending`（交互模式，按回车接受默认值） |

---

## 三、标准流程：从输入到输出

### 前置条件

| 条件 | 要求 | 验证方式 |
|------|------|----------|
| Python 环境 | Python 3.8+ | `python --version` |
| 网络连接 | 可访问 github.com | `curl -I https://github.com` |
| 依赖库 | `requests`、`beautifulsoup4` | `pip list \| grep requests` |
| 首次使用 | 运行 `--selftest` 确认环境 | 见下方自检说明 |

### 执行步骤

#### 步骤 1：环境自检（仅首次）

```bash
github-trending --selftest
```

预期输出：

```
[OK] Python 版本: 3.10.12
[OK] 依赖库: requests 2.31.0, beautifulsoup4 4.12.2
[OK] 网络连通: github.com 可达
[OK] 环境就绪，可以开始使用。
```

#### 步骤 2：基础使用（交互模式）

```bash
github-trending
```

交互提示示例：

```
? 请选择时间范围 (today/weekly/monthly) [weekly]: 
? 请选择语言 (留空表示全部) [all]: 
? 输出文件路径 [trending_report.md]: 
```

直接回车接受默认值即可生成周报。

#### 步骤 3：进阶使用（参数组合）

| 参数 | 可选值 | 默认值 | 说明 |
|------|--------|--------|------|
| `--language` | `python`, `javascript`, `go`, `rust`, `typescript`, `all` 等 | `all` | 按语言过滤 |
| `--since` | `today`, `weekly`, `monthly` | `weekly` | 时间窗口 |
| `--output` | 任意文件路径 | `trending_report.md` | 输出文件位置 |
| `--format` | `markdown`, `json` | `markdown` | 输出格式 |

示例：

```bash
# 查看本月 JavaScript 趋势
github-trending --language javascript --since monthly

# 生成 JSON 格式日报
github-trending --since today --format json

# 指定输出路径
github-trending --language go --output go_trending.md
```

#### 步骤 4：自动化（cron 定时任务）

将以下行加入 crontab，每周一早上 9 点生成周报：

```cron
0 9 * * 1 cd /path/to/script && github-trending --since weekly --output weekly_report.md
```

### 输出规范

默认 Markdown 格式报告结构如下：

```markdown
# GitHub Trending 周报（2026-08-10 至 2026-08-16）

> 语言筛选: all | 时间范围: weekly | 生成时间: 2026-08-16 09:00:00

## 本周热门项目 TOP 20

### 1. [仓库名](https://github.com/owner/repo)

- **描述**: 一句话项目简介
- **语言**: Python
- **星标总数**: 12,345
- **本周新增星标**: +1,234
- **Fork 数**: 567
- **链接**: https://github.com/owner/repo

---

### 2. [仓库名](https://github.com/owner/repo)
...
```

---

## 四、置信度门控：不编造，不猜测

当抓取数据不完整或存在异常时，本 Skill 遵循以下规则：

| 场景 | 处理方式 |
|------|----------|
| 仓库描述缺失 | 输出 `[需核实: 描述]` 占位符，不自行补写 |
| 星标数获取失败 | 输出 `[需核实: 星标数]` |
| 语言标签缺失 | 输出 `[需核实: 语言]` |
| 网络超时 | 终止执行，输出错误码 `E1001`，不输出半成品报告 |
| 页面结构变化导致解析失败 | 输出错误码 `E2001`，提示等待更新 |

**原则**：宁可输出带占位符的报告，也不编造数据。所有 `[需核实: xxx]` 字段需人工确认后补充。

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| `E1001` | 网络连接失败 | "无法连接 GitHub，请检查网络后重试。" | 1. 检查网络；2. 确认可访问 github.com；3. 重试 |
| `E1002` | 请求超时 | "请求超时，GitHub 响应过慢。" | 1. 稍后重试；2. 使用 `--timeout 30` 增加超时时间 |
| `E2001` | 页面解析失败 | "GitHub Trending 页面结构可能已变化，解析失败。" | 1. 更新 Skill 至最新版；2. 提交 Issue 反馈 |
| `E2002` | 数据为空 | "未获取到任何仓库数据，可能筛选条件过严。" | 1. 放宽语言筛选；2. 尝试 `--since today` |
| `E3001` | 参数无效 | "参数 `--since` 仅支持 today/weekly/monthly。" | 1. 检查参数拼写；2. 参考帮助文档 `--help` |
| `E3002` | 输出路径不可写 | "无法写入输出文件，请检查路径权限。" | 1. 确认目录存在；2. 检查写权限 |
| `E4001` | 依赖缺失 | "缺少依赖库 requests，请先安装。" | 1. 运行 `pip install requests beautifulsoup4` |

---

## 六、FAQ 反模式：常见坑与正确姿势

### 坑 1：频繁抓取导致 IP 被限流

**反模式**：每分钟执行一次脚本，试图实时监控 Trending。

**正确姿势**：GitHub Trending 每小时更新一次，建议抓取频率不超过每小时 1 次。加入 cron 定时任务时，设置合理间隔（如每天 1-2 次）。

### 坑 2：忽略 `--selftest` 直接使用

**反模式**：新环境直接运行主命令，遇到依赖缺失报错。

**正确姿势**：首次使用或更换环境后，先运行 `--selftest` 确认环境就绪，避免中途失败。

### 坑 3：对 `[需核实]` 字段自行脑补

**反模式**：看到描述缺失，凭印象补写一段项目介绍。

**正确姿势**：保留 `[需核实: 描述]` 占位符，通过仓库链接人工确认后补充。编造描述可能误导读者。

### 坑 4：使用 `--since monthly` 但期望精确到天

**反模式**：认为月度报告会包含每天的数据明细。

**正确姿势**：`monthly` 是 GitHub Trending 的聚合窗口，只显示近 30 天的整体趋势，不提供逐日明细。如需逐日数据，应分别生成多份日报。

### 坑 5：将报告数据直接用于商业决策

**反模式**：根据星标数排名直接决定技术选型，不做深入调研。

**正确姿势**：Trending 数据反映短期热度，不代表项目质量或长期维护性。选型前应查看项目文档、Issue 响应速度、License 等综合评估。

---

## 七、渐进式披露：按需阅读

### 🚀 速查卡（30 秒上手）

```bash
# 安装依赖
pip install requests beautifulsoup4

# 自检环境
github-trending --selftest

# 生成默认周报
github-trending

# 生成 Python 月度报告
github-trending --language python --since monthly
```

### 📖 新手路径（5 分钟）

1. 阅读「前置条件」确认环境
2. 运行 `--selftest` 验证
3. 不带参数运行，体验交互模式
4. 查看生成的 `trending_report.md` 文件
5. 尝试 `--language` 和 `--since` 参数组合

### 🔧 进阶路径（15 分钟）

1. 阅读「自定义输出模板」章节，修改 `TEMPLATE` 常量
2. 在 `fetch_trending()` 中添加其他数据源（如 Gitee 趋势）
3. 在 `generate_report()` 后集成 Slack/邮件通知
4. 对多期周报做趋势对比分析，观察项目热度变化

---

## 八、自定义与扩展

### 自定义输出模板

编辑脚本中的 `TEMPLATE` 常量，修改报告格式。例如增加「本周新晋项目」分类：

```python
TEMPLATE = """
## 本周新晋项目（首次进入 TOP 20）

{new_entries}

## 本周热门项目 TOP 20

{entries}
"""
```

### 扩展数据源

在 `fetch_trending()` 函数中，可添加其他平台的趋势数据：

```python
def fetch_trending():
    github_data = fetch_github_trending()
    # 添加其他数据源
    # gitee_data = fetch_gitee_trending()
    # return merge_data(github_data, gitee_data)
    return github_data
```

### 集成通知

在 `generate_report()` 返回报告内容后，添加通知逻辑：

```python
report = generate_report()
send_slack_notification(report)  # 自定义函数
send_email_notification(report)  # 自定义函数
```

---

## 九、用户协议

<!-- user-agreement-injected -->

**使用本 Skill 即表示您同意以下条款：**

1. **责任承担**：使用者自行承担使用本 Skill 产生的全部责任。包括但不限于因数据不准确、输出错误、或使用不当导致的任何直接或间接损失。

2. **禁止反向工程**：不得对本 Skill 的源代码进行反向工程、反编译、破解或试图提取底层算法（法律允许的除外）。

3. **合规使用**：使用者应遵守 GitHub 的服务条款，不得利用本 Skill 进行高频抓取、绕过限流或其他违反平台规则的行为。

4. **数据使用**：本 Skill 输出的数据仅供学习参考，使用者应自行核实数据的准确性，不得将数据用于商业用途而未注明来源。

5. **免责声明**：本 Skill 按"现状"提供，不提供任何明示或暗示的保证，包括但不限于适销性、特定用途适用性和非侵权性。

---

## 十、许可证（License）

<!-- professional-license-embedded -->

### MIT License

Copyright (c) 2026 Lin Chen

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

*本 Skill 由 AI 辅助生成，仅供参考。使用前请阅读相关文档。*
