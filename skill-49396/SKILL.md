---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: skill-49396
name: skill-49396
displayName: 爬虫工具 网页采集 数据提取
description: 一站式生成可运行爬虫脚本，覆盖识别、整理、校验与输出，直接可用。
version: 1.0.1
rules_version: cpr-20260813-n401
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/skill-49396
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 林栖
agent_created: true
trigger_words:
  - 爬虫工具
  - 网页采集
  - 数据抓取
  - 爬虫脚本
  - 数据提取
---

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->


> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# 爬虫工具 网页采集 数据提取 — Skill 文档

## 一、能力边界（一页纸速查卡）

### 1.1 能做什么

| 能力项 | 说明 | 交付物 |
|--------|------|--------|
| 爬虫脚本生成 | 根据目标 URL 与字段需求，生成可直接运行的 Python 脚本 | `.py` 文件 |
| 反爬策略内置 | 自动加入 UA 轮换、请求间隔随机化、Cookie 维持、代理 IP 切换 | 脚本内代码片段 |
| 结果校验 | 对生成的脚本做语法检查、依赖检查、运行测试 | 校验报告（Markdown） |
| 增量爬取 | 基于时间戳或 ID 的增量逻辑，避免重复抓取 | 脚本内增量模块 |
| 数据清洗 | 去重、字段格式化、编码修正 | 清洗后的数据文件 |
| 多线程加速 | 单机多线程/异步方案（`ThreadPoolExecutor` / `asyncio`） | 脚本内并发模块 |

### 1.2 不能做什么（明确拒绝）

| 场景 | 处理方式 |
|------|----------|
| 滑块验证、点选验证码、行为验证（极验/腾讯） | 不自动破解，输出手动介入提示 |
| 付费订阅、robots.txt 禁止、个人隐私数据 | 不生成脚本，主动提示法律风险 |
| 分布式爬虫（Scrapy 集群、RabbitMQ/Kafka） | 仅支持单机方案，超出范围 |
| App 逆向（APK 反编译、HTTPS 证书抓包、HOOK） | 不处理，建议使用官方 API |

### 1.3 适用对象

- 需要快速获取公开网页数据的开发者
- 需要批量采集商品信息、新闻、论文摘要等场景
- 对 Python 有一定基础，但不想从零编写爬虫逻辑的用户

---

## 二、触发方式

### 2.1 触发词

当对话中出现以下关键词时，本 Skill 自动激活：

- **核心触发**：爬虫工具、网页采集、数据抓取、爬虫脚本、数据提取
- **补充触发**：爬虫、采集、抓取、spider、crawler、scraper

### 2.2 场景映射表

| 用户说（大白话） | 本 Skill 响应 |
|------------------|---------------|
| "帮我爬一下这个网页上的商品价格" | 生成 requests 模板脚本，提取价格字段 |
| "这个网站需要登录才能看数据" | 提示需要登录，提供手动 Cookie 注入方案 |
| "数据太多，能不能快点爬" | 启用多线程/异步方案，并提示反爬风险 |
| "上次爬过的数据不想再爬一遍" | 加入增量爬取逻辑，基于 ID 或时间戳去重 |
| "爬下来的中文乱码了" | 自动修正编码，CSV 输出使用 `utf-8-sig` |

---

## 三、标准流程

### 3.1 前置条件

用户必须提供以下信息（至少前 3 项）：

| 参数 | 必填 | 示例 |
|------|------|------|
| 目标网页 URL | ✅ | `https://example.com/products` |
| 需要提取的字段 | ✅ | 标题、价格、日期 |
| 输出格式 | ❌（默认 CSV） | CSV / JSON / Excel |
| 翻页规律 | ❌ | `?page=1,2,3...` 或无限滚动 |
| 是否需要登录 | ❌ | 是 / 否 |
| 预估数据量级 | ❌ | 100 条 / 10000 条 |

### 3.2 执行步骤

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

### 3.3 输出规范

| 输出物 | 格式 | 说明 |
|--------|------|------|
| 爬虫脚本 | `.py` | 可直接运行，含注释 |
| 校验报告 | `.md` | 包含检查项、通过/失败状态、修正建议 |
| 数据文件 | `.csv` / `.json` / `.xlsx` | 按用户偏好输出 |

---

## 四、置信度门控

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

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| `E001` | 目标 URL 无法访问 | "目标 URL 返回 403/404，请检查 URL 是否正确或是否触发反爬" | 1. 检查 URL 拼写 2. 添加 UA 头 3. 尝试代理 |
| `E002` | 选择器匹配失败 | "未找到指定元素，页面结构可能已变化" | 1. 重新检查页面结构 2. 使用更宽松的选择器 3. 尝试 XPath |
| `E003` | 字段提取不完整 | "部分字段提取为空，请确认字段名是否正确" | 1. 打印 HTML 片段 2. 调整选择器 3. 检查动态加载 |
| `E004` | 反爬机制触发 | "检测到 IP 限制或验证码，请降低频率或使用代理" | 1. 增加请求间隔 2. 切换代理 IP 3. 手动处理验证码 |
| `E005` | 编码乱码 | "输出文件出现乱码，请检查编码设置" | 1. 设置 `resp.encoding = resp.apparent_encoding` 2. CSV 使用 `utf-8-sig` |
| `E006` | 依赖缺失 | "缺少必要依赖库，请安装 requirements.txt" | 1. 运行 `pip install -r requirements.txt` 2. 检查 Python 版本 |

---

## 六、FAQ 反模式

### 6.1 常见坑与反模式对照

| 坑 | 反模式（错误做法） | 正确做法 |
|----|-------------------|----------|
| 爬取速度过快被封 IP | 不设延迟，疯狂请求 | 设置 `time.sleep(random.uniform(2, 5))` |
| 中文乱码 | 直接保存 CSV 不指定编码 | 使用 `encoding='utf-8-sig'` |
| 重复爬取 | 每次全量爬取 | 记录上次最大 ID/时间戳，增量爬取 |
| 选择器失效 | 硬编码选择器不检查 | 定期检查页面结构，使用更稳定的属性 |
| 忽略 robots.txt | 直接爬取禁止页面 | 先检查 `robots.txt`，遵守规则 |

### 6.2 反模式示例

```python
# ❌ 反模式：无延迟、无 UA、无编码处理
import requests
resp = requests.get(url)
with open('data.csv', 'w') as f:
    f.write(resp.text)

# ✅ 正确模式
import requests, time, random
headers = {"User-Agent": random.choice(UA_LIST)}
resp = requests.get(url, headers=headers, timeout=10)
resp.encoding = resp.apparent_encoding
time.sleep(random.uniform(2, 5))
with open('data.csv', 'w', encoding='utf-8-sig') as f:
    f.write(resp.text)
```

---

## 七、渐进式披露

### 7.1 速查卡（30 秒上手）

1. 提供 URL + 字段 → 2. 选择输出格式 → 3. 获取脚本 + 校验报告 → 4. 运行脚本 → 5. 得到数据文件

### 7.2 新手路径（首次使用）

1. 阅读「能力边界」了解能做什么
2. 提供 URL 和字段，生成基础脚本
3. 运行脚本，查看校验报告
4. 如有错误，根据「错误码体系」修正

### 7.3 进阶路径（有经验用户）

1. 使用「反爬策略」应对复杂网站
2. 启用「多线程」提升效率
3. 使用「增量爬取」避免重复
4. 自定义数据清洗逻辑

---

## 八、模板代码示例

### 8.1 基础 requests 模板

```python
import requests
import time
import random
from bs4 import BeautifulSoup
import csv

# 配置
URL = "https://example.com/products"
UA_LIST = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
]
OUTPUT_FILE = "output.csv"

def fetch_page(url):
    headers = {"User-Agent": random.choice(UA_LIST)}
    resp = requests.get(url, headers=headers, timeout=10)
    resp.encoding = resp.apparent_encoding
    time.sleep(random.uniform(2, 5))
    return resp.text

def parse_page(html):
    soup = BeautifulSoup(html, 'html.parser')
    items = []
    for product in soup.select('.product'):
        title = product.select_one('.title').text.strip()
        price = product.select_one('.price').text.strip()
        items.append({"title": title, "price": price})
    return items

def main():
    html = fetch_page(URL)
    items = parse_page(html)
    with open(OUTPUT_FILE, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=["title", "price"])
        writer.writeheader()
        writer.writerows(items)
    print(f"完成，共 {len(items)} 条数据")

if __name__ == "__main__":
    main()
```

### 8.2 多线程模板

```python
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests

def fetch_one(url):
    resp = requests.get(url, timeout=10)
    return resp.text

def main():
    urls = [f"https://example.com/page/{i}" for i in range(1, 11)]
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(fetch_one, url) for url in urls]
        for future in as_completed(futures):
            html = future.result()
            # 处理 html
```

---

## 九、用户协议

<!-- user-agreement-injected -->

**使用本 Skill 生成的所有代码、脚本、数据及衍生内容，使用者自行承担全部责任。**

1. 使用者确认已阅读并理解本协议，使用本 Skill 即表示同意本协议全部条款。
2. 使用者应确保其爬取行为符合目标网站的服务条款、robots.txt 规范及适用法律法规。
3. 使用者不得将本 Skill 生成的代码用于任何非法目的，包括但不限于：绕过访问控制、爬取个人隐私数据、侵犯知识产权、干扰网站正常运营。
4. 本 Skill 生成的内容按"现状"提供，不附带任何明示或暗示的担保。作者不对使用后果承担任何责任。
5. 使用者不得对本 Skill 生成的代码进行反向工程、反编译或试图提取底层算法（法律允许的除外）。
6. 若因使用本 Skill 产生任何纠纷或损失，使用者同意自行解决并承担全部责任，与作者无关。

---

## 十、许可证（License）

<!-- professional-license-embedded -->

**MIT License**

版权所有 (c) 2025 林栖

特此免费授予任何获得本软件及相关文档文件（以下简称"软件"）副本的人士无偿使用本软件的权利，包括但不限于使用、复制、修改、合并、出版、分发、再许可和/或销售软件副本的权利，并允许向其提供软件的人士这样做，但须满足以下条件：

上述版权声明和本许可声明应包含在软件的所有副本或重要部分中。

本软件按"现状"提供，不作任何明示或暗示的保证，包括但不限于适销性、特定用途适用性和非侵权性的保证。在任何情况下，作者或版权持有人均不对任何索赔、损害或其他责任负责，无论是在合同诉讼、侵权行为或其他方面，由软件或软件的使用或其他交易引起或与之相关。

---

*本 Skill 文档由 AI 辅助生成，仅供学习参考。使用前请阅读相关文档并遵守法律法规。*
