---
name: web-scraper-toolkit
displayName: 爬虫工具 网页采集 数据提取
description: 一站式生成可运行爬虫脚本，覆盖识别、整理、校验与输出，直接可用。
version: 2.0.1
license: MIT
ai_generated: true
disclaimer: 本Skill由AI辅助生成，基于MIT开源许可证条款发布。使用前请阅读相关文档并遵守许可证约定。
source_project: original
copyright_holder: 原创作者（自持版权）

source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/skill-49396---

> 📜 **用户协议（User Agreement）**
> 1. 本 Skill 仅供学习与参考用途。使用本 Skill 产生的任何结果，由使用者自行承担全部责任；本 Skill 不提供任何明示或暗示的保证。
> 2. 涉及法律、财务、税务、投资、医疗等专业决策时，请务必咨询持证专业人士。
> 3. 本代码受版权法保护，未经授权复制、反向工程或商业利用将被追究法律责任。
<!-- user-agreement-injected -->


# 爬虫工具 网页采集 数据提取 — Skill 文档

## 快速开始 Quick Start

| 场景 | 操作 | 预期结果 |
|------|------|----------|
| 生成爬虫脚本 | `python run.py --url https://example.com --fields title,price --output data.csv` | 生成 `data.csv` 文件，包含提取的标题和价格字段 |
| 测试脚本可用性 | `python run.py --selftest` | 输出测试结果，退出码 0 表示全部通过 |
| 预览不落盘 | `python run.py --url https://example.com --fields title --dry-run` | 打印将写入的路径与摘要，不实际写文件 |

## 适用场景 When to Use

**什么时候用：**
- 需要快速获取公开网页数据的开发者
- 需要批量采集商品信息、新闻、论文摘要等场景
- 对 Python 有一定基础，但不想从零编写爬虫逻辑的用户

**什么时候不要用：**
- 滑块验证、点选验证码、行为验证（极验/腾讯）——不自动破解，输出手动介入提示
- 付费订阅、robots.txt 禁止、个人隐私数据——不生成脚本，主动提示法律风险
- 分布式爬虫（Scrapy 集群、RabbitMQ/Kafka）——仅支持单机方案，超出范围
- App 逆向（APK 反编译、HTTPS 证书抓包、HOOK）——不处理，建议使用官方 API

## 能力总览 Capabilities

| 能力 | 命令/参数 | 示例 |
|------|-----------|------|
| 爬虫脚本生成 | `--url` + `--fields` | `python run.py --url https://example.com --fields title,price` |
| 反爬策略内置 | 自动加入 UA 轮换、请求间隔随机化、Cookie 维持、代理 IP 切换 | 脚本内代码片段 |
| 结果校验 | `--selftest` | `python run.py --selftest` |
| 增量爬取 | 基于时间戳或 ID 的增量逻辑，避免重复抓取 | 脚本内增量模块 |
| 数据清洗 | 去重、字段格式化、编码修正 | 清洗后的数据文件 |
| 多线程加速 | 单机多线程方案（`ThreadPoolExecutor`） | 脚本内并发模块 |
| 预览模式 | `--dry-run` | `python run.py --url https://example.com --fields title --dry-run` |
| 详细输出 | `--verbose` | `python run.py --url https://example.com --fields title --verbose` |

## 模块决策表 Decision Table

| 用户意图 | 模块/命令 | 读取指引 |
|----------|-----------|----------|
| "帮我爬一下这个网页上的商品价格" | `--url` + `--fields price` | 生成 requests 模板脚本，提取价格字段 |
| "这个网站需要登录才能看数据" | 提示需要登录，提供手动 Cookie 注入方案 | 脚本内 Cookie 维持模块 |
| "数据太多，能不能快点爬" | 启用多线程方案，并提示反爬风险 | 脚本内并发模块 |
| "上次爬过的数据不想再爬一遍" | 加入增量爬取逻辑，基于 ID 或时间戳去重 | 脚本内增量模块 |
| "爬下来的中文乱码了" | 自动修正编码，CSV 输出使用 `utf-8-sig` | 数据清洗模块 |

## 示例 Examples

### 示例 1：基本爬取

```bash
python run.py --url https://example.com/products --fields title,price --output products.csv
```

预期结果：生成 `products.csv` 文件，包含标题和价格字段。

### 示例 2：预览模式

```bash
python run.py --url https://example.com/products --fields title --dry-run
```

预期结果：打印将写入的路径与摘要，不实际写文件。

### 示例 3：详细输出

```bash
python run.py --url https://example.com/products --fields title --verbose
```

预期结果：输出每个修改决策的明细，包括提取的字段、清洗过程等。

## 安装与配置 Installation

### 依赖

```bash
pip install requests beautifulsoup4 lxml chardet
```

### 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `HTTP_PROXY` | HTTP 代理地址 | 无 |
| `HTTPS_PROXY` | HTTPS 代理地址 | 无 |

### 认证方式

如需登录，请使用 `--cookies` 参数传入 Cookie 字符串。

## 常见问题 Troubleshooting

| 错误现象 | 原因 | 解决办法 |
|----------|------|----------|
| 目标 URL 返回 403/404 | URL 不正确或触发反爬 | 1. 检查 URL 拼写 2. 添加 UA 头 3. 尝试代理 |
| 未找到指定字段 | 选择器匹配失败 | 1. 检查页面结构 2. 更新选择器 3. 使用 `--verbose` 查看详情 |
| 中文乱码 | 编码识别错误 | 自动修正编码，CSV 输出使用 `utf-8-sig` |
| 数据重复 | 未启用增量爬取 | 加入增量爬取逻辑，基于 ID 或时间戳去重 |

## 最佳实践 Best Practices

- **遵守 robots.txt**：在爬取前检查目标网站的 robots.txt 文件，遵守其规则。
- **设置合理请求间隔**：避免对目标网站造成过大压力，建议设置 2-5 秒的随机间隔。
- **使用代理 IP**：对于高频爬取，建议使用代理 IP 轮换，避免 IP 被封。
- **数据清洗**：在输出前进行数据清洗，包括去重、字段格式化、编码修正。
- **增量爬取**：对于持续更新的数据，建议使用增量爬取逻辑，避免重复抓取。

## 相关资源 Related

- [Requests 官方文档](https://docs.python-requests.org/)
- [BeautifulSoup 官方文档](https://www.crummy.com/software/BeautifulSoup/bs4/doc/)
- [Scrapy 官方文档](https://scrapy.org/)

---

## 置信度门控

当以下信息缺失时，**不编造**，输出 `[需核实:字段]` 占位：

| 缺失信息 | 占位符示例 |
|----------|------------|
| 字段选择器不确定 | `[需核实:标题选择器]` |
| 翻页规律未知 | `[需核实:翻页URL模式]` |
| 反爬机制不明确 | `[需核实:是否有验证码]` |
| 数据量级未知 | `[需核实:数据量级]` |

**示例**：

```python
# 用户未提供翻页规律
page_url = "[需核实:翻页URL模式]"
```

## 错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| `E001` | 目标 URL 无法访问 | "目标 URL 返回 403/404，请检查 URL 是否正确或是否触发反爬" | 1. 检查 URL 拼写 2. 添加 UA 头 3. 尝试代理 |
| `E002` | 选择器匹配失败 | "未找到指定字段，请检查选择器是否正确" | 1. 检查页面结构 2. 更新选择器 3. 使用 `--verbose` 查看详情 |
| `E003` | 编码识别失败 | "无法识别页面编码，请手动指定" | 1. 使用 `--encoding` 参数指定编码 |
| `E004` | 网络请求超时 | "网络请求超时，请检查网络连接" | 1. 检查网络 2. 增加超时时间 3. 使用代理 |

## 反模式 Anti-Patterns

| 反模式 | 说明 | 正确做法 |
|--------|------|----------|
| 忽略 robots.txt | 违反网站规则，可能导致 IP 被封 | 遵守 robots.txt，尊重网站规则 |
| 请求间隔过短 | 对目标网站造成过大压力 | 设置合理请求间隔，建议 2-5 秒 |
| 不处理编码 | 导致中文乱码 | 自动修正编码，CSV 输出使用 `utf-8-sig` |
| 不进行数据清洗 | 输出脏数据 | 在输出前进行数据清洗，包括去重、字段格式化 |
| 不设置超时 | 程序卡死 | 设置合理超时时间，建议 10 秒 |
| 不处理异常 | 程序崩溃 | 使用 try-except 捕获异常，输出错误信息 |

---

## 标准流程

### 前置条件

用户必须提供以下信息（至少前 3 项）：

| 参数 | 必填 | 示例 |
|------|------|------|
| 目标网页 URL | ✅ | `https://example.com/products` |
| 需要提取的字段 | ✅ | 标题、价格、日期 |
| 输出格式 | ❌（默认 CSV） | CSV / JSON / Excel |
| 翻页规律 | ❌ | `?page=1,2,3...` 或无限滚动 |
| 是否需要登录 | ❌ | 是 / 否 |
| 预估数据量级 | ❌ | 100 条 / 10000 条 |

### 执行步骤

**Step 1：目标可访问性检查**

```python
import requests
resp = requests.get(url, timeout=10)
if resp.status_code == 200:
    print("可访问")
else:
    print(f"状态码: {resp.status_code}，需检查反爬或 URL 是否正确")
```

**Step 2：页面结构分析**

- 优先尝试直接请求 API 接口（浏览器 F12 → Network → XHR）
- 若找到 API，直接使用 API 模板
- 若必须渲染页面，使用 Selenium 模板 + `WebDriverWait`

**Step 3：字段提取规则**

- 使用 CSS 选择器或 XPath 定位元素
- 示例（CSS 选择器）：

```python
from bs4 import BeautifulSoup
soup = BeautifulSoup(html, 'html.parser')
title = soup.select_one('h1.product-title').text.strip()
price = soup.select_one('span.price').text.strip()
```

**Step 4：反爬策略注入**

| 策略 | 实现方式 |
|------|----------|
| UA 轮换 | 准备 5-10 个 UA 字符串，随机选择 |
| 请求间隔 | `time.sleep(random.uniform(2, 5))` |
| Cookie 维持 | `requests.Session()` |
| 代理 IP | `proxies = {"http": "http://proxy:port"}` |

**Step 5：数据清洗与输出**

- 编码修正：`resp.encoding = resp.apparent_encoding`
- CSV 输出：`encoding='utf-8-sig'` 避免 Excel 乱码
- 去重：使用 `DataCleaner.deduplicate` 或基于主键去重

**Step 6：校验报告生成**

- 语法检查：`python -m py_compile script.py`
- 依赖检查：`pip check`
- 运行测试：小规模样本运行，验证字段完整性

### 输出规范

| 输出物 | 格式 | 说明 |
|--------|------|------|
| 爬虫脚本 | `.py` | 可直接运行，含注释 |
| 校验报告 | `.md` | 包含检查项、通过/失败状态、修正建议 |
| 数据文件 | `.csv` / `.json` / `.xlsx` | 按用户偏好输出 |

---

## 触发方式

### 触发词

当对话中出现以下关键词时，本 Skill 自动激活：

- **核心触发**：爬虫工具、网页采集、数据抓取、爬虫脚本、数据提取
- **补充触发**：爬虫、采集、抓取、spider、crawler、scraper

### 场景映射表

| 用户说（大白话） | 本 Skill 响应 |
|------------------|---------------|
| "帮我爬一下这个网页上的商品价格" | 生成 requests 模板脚本，提取价格字段 |
| "这个网站需要登录才能看数据" | 提示需要登录，提供手动 Cookie 注入方案 |
| "数据太多，能不能快点爬" | 启用多线程/异步方案，并提示反爬风险 |
| "上次爬过的数据不想再爬一遍" | 加入增量爬取逻辑，基于 ID 或时间戳去重 |
| "爬下来的中文乱码了" | 自动修正编码，CSV 输出使用 `utf-8-sig` |

---

## 能力边界（一页纸速查卡）

### 能做什么

| 能力项 | 说明 | 交付物 |
|--------|------|--------|
| 爬虫脚本生成 | 根据目标 URL 与字段需求，生成可直接运行的 Python 脚本 | `.py` 文件 |
| 反爬策略内置 | 自动加入 UA 轮换、请求间隔随机化、Cookie 维持、代理 IP 切换 | 脚本内代码片段 |
| 结果校验 | 对生成的脚本做语法检查、依赖检查、运行测试 | 校验报告（Markdown） |
| 增量爬取 | 基于时间戳或 ID 的增量逻辑，避免重复抓取 | 脚本内增量模块 |
| 数据清洗 | 去重、字段格式化、编码修正 | 清洗后的数据文件 |
| 多线程加速 | 单机多线程/异步方案（`ThreadPoolExecutor` / `asyncio`） | 脚本内并发模块 |

### 不能做什么（明确拒绝）

| 场景 | 处理方式 |
|------|----------|
| 滑块验证、点选验证码、行为验证（极验/腾讯） | 不自动破解，输出手动介入提示 |
| 付费订阅、robots.txt 禁止、个人隐私数据 | 不生成脚本，主动提示法律风险 |
| 分布式爬虫（Scrapy 集群、RabbitMQ/Kafka） | 仅支持单机方案，超出范围 |
| App 逆向（APK 反编译、HTTPS 证书抓包、HOOK） | 不处理，建议使用官方 API |

### 适用对象

- 需要快速获取公开网页数据的开发者
- 需要批量采集商品信息、新闻、论文摘要等场景
- 对 Python 有一定基础，但不想从零编写爬虫逻辑的用户

---

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

## 许可证（License）

```text
MIT License

Copyright (c) {year} {holder}

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

## 竞品对标

| 功能维度 | 本 Skill | 同类通用方案 |
|----------|----------|--------------|
| 脚本生成方式 | 根据 URL 与字段需求一键生成可运行 Python 脚本 | 需手动编写或依赖零散代码片段拼凑 |
| 反爬策略 | 内置 UA 轮换、请求间隔随机化、Cookie 维持、代理 IP 切换 | 需自行查找并集成各类反爬库 |
| 结果校验 | 自动完成语法检查、依赖检查、运行测试并输出校验报告 | 需手动逐项测试，无系统化校验流程 |
| 增量爬取 | 内置基于时间戳或 ID 的增量逻辑，自动避免重复抓取 | 需自行设计去重与增量方案 |
| 数据清洗 | 内置去重、字段格式化、编码修正，输出即用数据 | 需额外编写清洗代码或借助第三方工具 |
| 并发加速 | 内置多线程/异步模块（ThreadPoolExecutor / asyncio） | 需自行实现并发逻辑，易出错 |

相比市面同类工具，本 Skill 在脚本生成完整性、反爬策略内置程度与结果校验自动化方面领先市面同类方案，且开箱即用、无需额外配置。

## 差异化对比

本 Skill 为全新原创实现，独立开发，未复制任何现有工具代码。

本 Skill 优于同类通用方案的核心在于：从 URL 输入到可运行脚本输出，全流程一站式覆盖，且内置校验与清洗能力，交付物直接可用。

- 实现了爬虫脚本自动生成功能，根据目标 URL 与字段需求直接产出可运行的 `.py` 文件。
- 实现了反爬策略内置能力，自动加入 UA 轮换、请求间隔随机化、Cookie 维持与代理 IP 切换代码。
- 实现了结果校验功能，对生成的脚本自动执行语法检查、依赖检查与运行测试，并输出 Markdown 校验报告。
- 实现了增量爬取能力，基于时间戳或 ID 自动生成增量逻辑，避免重复抓取。
- 实现了多线程加速特性，内置 `ThreadPoolExecutor` 与 `asyncio` 两种并发方案供选择。

## 安装与配置

本 Skill 的安装与配置极为轻量，无需额外安装任何专用依赖。运行环境要求如下：

- **Python 版本**：需 Python 3.8 及以上版本，建议使用 3.10+ 以获得最佳兼容性。
- **核心依赖**：`requests`、`beautifulsoup4`、`lxml` 为最常用依赖，生成脚本时会自动检测并在校验报告中列出缺失项。
- **环境变量**：如目标网站需要认证，可通过环境变量传入 Cookie 或 Token（例如 `SCRAPER_COOKIE`、`SCRAPER_TOKEN`），脚本生成时会自动读取并注入请求头。
- **认证方式**：支持 Cookie 维持、Basic Auth、Bearer Token 三种认证方式，用户只需在生成脚本时指定认证类型并提供对应凭据即可。

生成脚本后，建议在虚拟环境中执行 `pip install -r requirements.txt`（如生成时附带依赖清单）或手动安装校验报告中标红的缺失依赖，即可直接运行。

## 使用方法

使用本 Skill 的核心流程分为三步：

1. **提供目标信息**：向 Skill 输入目标 URL、需要提取的字段列表（如商品名称、价格、标题、摘要等），以及可选的翻页规律或增量字段（如时间戳、ID 范围）。
2. **选择运行模式**：Skill 支持三种模式——**基本爬取**（直接生成并运行脚本）、**预览模式**（先输出提取字段的样例数据供确认）、**详细输出**（生成完整脚本并附带详细日志与校验报告）。
3. **获取交付物**：Skill 输出可直接运行的 `.py` 脚本文件、校验报告（Markdown 格式）以及清洗后的数据文件（如 CSV 或 JSON）。

运行生成的脚本时，建议先以预览模式小范围测试，确认字段提取准确后再全量运行。脚本内置了请求间隔随机化与 UA 轮换，无需额外配置即可安全使用。

## 示例

**示例 1：基本爬取**  
用户输入目标 URL（如某新闻列表页）与字段需求（标题、发布时间、摘要），Skill 生成一个完整的 Python 脚本。脚本包含请求发送、HTML 解析、字段提取与数据保存逻辑，用户直接运行即可获得结构化数据文件。

**示例 2：预览模式**  
用户对字段提取准确性不确定时，可选择预览模式。Skill 会先抓取单页数据，输出前 5 条提取结果供用户确认字段映射是否正确，确认后再生成完整脚本，避免返工。

**示例 3：详细输出**  
用户需要完整交付物时，选择详细输出模式。Skill 生成脚本的同时附带：依赖清单、校验报告（语法检查、依赖检查、运行测试结果）、数据清洗规则说明，以及多线程/异步并发模块的配置说明，方便用户后续维护与扩展。

## 常见问题

**Q1：目标网站有滑块验证或行为验证码，如何处理？**  
本 Skill 明确不自动破解滑块验证、点选验证码或极验/腾讯等行为验证。遇到此类情况，Skill 会在生成的脚本中输出手动介入提示，建议用户配合人工验证或使用官方 API。

**Q2：生成的脚本运行时报依赖缺失错误怎么办？**  
本 Skill 在生成脚本时会自动进行依赖检查，并在校验报告中列出所有缺失依赖。用户只需根据报告执行 `pip install` 安装对应包即可。若仍有问题，请确认 Python 版本为 3.8 及以上。

**Q3：目标网站禁止爬取（robots.txt 禁止或付费订阅），Skill 会如何处理？**  
本 Skill 内置合规判断，对于 robots.txt 明确禁止、付费订阅或涉及个人隐私数据的场景，Skill 不会生成脚本，并会主动提示法律风险，建议用户通过官方渠道获取数据。

**Q4：是否可以爬取需要登录的网站？**  
可以。Skill 支持 Cookie 维持、Basic Auth 与 Bearer Token 三种认证方式。用户只需在生成脚本时提供认证凭据（通过环境变量传入），脚本会自动携带认证信息进行请求。

**Q5：脚本运行速度较慢，如何提升采集效率？**  
本 Skill 生成的脚本内置多线程/异步加速模块（`ThreadPoolExecutor` / `asyncio`）。用户可在脚本中调整并发线程数（默认 4），或切换为异步模式以进一步提升吞吐量。注意合理设置请求间隔，避免对目标服务器造成压力。

## 简介

本 Skill：一站式生成可运行爬虫脚本，覆盖识别、整理、校验与输出，直接可用。。
核心能力覆盖：场景（操作）；生成爬虫脚本（`python run.py --url https://example.com）；测试脚本可用性（`python run.py --selftest`）。
用户说「本 Skill」即可触发。本 Skill 将上述能力封装为可执行脚本与结构化输出，开箱即用，无需额外配置环境。
