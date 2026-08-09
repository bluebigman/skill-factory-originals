---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: autoscraper
name: autoscraper
displayName: 网页数据自动采集与结构化提取
description: 智能轻量级网页抓取工具，自动识别页面数据并输出结构化结果。
version: 1.0.1
rules_version: cpr-20260809-n251
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/autoscraper
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: DataFlow Studio
agent_created: true
trigger_words: ["autoscraper", "网页抓取", "数据采集", "爬虫", "web scraping", "页面解析", "结构化提取"]
---

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->


> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# AutoScraper 技能文档

## 一、能力边界速查卡

### ✅ 能做（核心能力清单）

| 序号 | 能力项 | 说明 | 适用场景示例 |
|------|--------|------|--------------|
| 1 | 智能页面抓取 | 给定 URL 后自动分析页面结构，提取关键数据 | 商品价格监控、新闻标题聚合 |
| 2 | 规则自学习 | 用户提供少量示例数据，工具自动学习提取规则 | 从列表页提取重复结构的数据 |
| 3 | 多格式输出 | 支持 JSON、CSV、Python 字典等结构化输出 | 数据清洗、API 数据源准备 |
| 4 | 批量 URL 处理 | 同一规则应用于多个页面，批量产出结果 | 多页面商品信息对比 |
| 5 | 轻量级集成 | 纯 Python 实现，无重型依赖，可嵌入现有脚本 | 爬虫脚本、数据处理管道 |

### ❌ 不能做（明确边界）

| 序号 | 限制项 | 说明 |
|------|--------|------|
| 1 | 不处理动态渲染页面 | 需要 JavaScript 执行才能加载内容的页面（如 SPA 应用）无法直接抓取 |
| 2 | 不绕过访问控制 | 不处理登录墙、验证码、IP 封锁等反爬机制 |
| 3 | 不保证数据完整性 | 页面结构变化可能导致提取失败，需定期维护规则 |
| 4 | 不处理非 HTML 内容 | PDF、图片、音视频等二进制内容不在处理范围内 |
| 5 | 不提供分布式抓取 | 单机运行，不支持集群调度 |

### 🎯 适用对象

- **数据工程师**：快速搭建数据采集管道
- **业务分析师**：从竞品网站提取公开数据做对比分析
- **Python 开发者**：需要轻量级抓取能力的项目集成
- **研究人员**：采集公开学术信息、新闻数据

---

## 二、触发方式与场景映射

### 触发词

直接使用以下任一词汇即可激活本技能：

- `autoscraper`
- `网页抓取`
- `数据采集`
- `爬虫`
- `web scraping`
- `页面解析`
- `结构化提取`

### 场景映射表

| 用户说（大白话） | 实际需求 | 技能响应方式 |
|------------------|----------|--------------|
| "帮我抓一下这个网页上的商品价格" | 从商品列表页提取价格数据 | 分析页面结构，提取价格字段并输出结构化数据 |
| "这个网站上的新闻标题怎么批量获取？" | 批量提取新闻标题列表 | 学习标题规则，批量应用于多个页面 |
| "我想把网页表格转成 Excel 格式" | 提取 HTML 表格数据 | 识别 table 结构，输出 CSV 格式 |
| "每天自动监控这个页面的价格变化" | 定期抓取并对比数据 | 提供可重复执行的抓取脚本模板 |

---

## 三、标准工作流程

### 前置条件

| 条件项 | 要求 | 检查方式 |
|--------|------|----------|
| Python 环境 | Python 3.7+ | `python --version` |
| 安装 AutoScraper | 已安装 autoscraper 库 | `pip show autoscraper` |
| 目标 URL 可访问 | 页面可正常打开，非登录墙 | 浏览器直接访问验证 |
| 页面结构明确 | 目标数据在 HTML 中可见 | 浏览器查看源代码确认 |

### 执行步骤

#### 第一步：环境准备

```bash
# 安装 AutoScraper
pip install autoscraper

# 验证安装
python -c "from autoscraper import AutoScraper; print('OK')"
```

#### 第二步：基础抓取流程

```python
from autoscraper import AutoScraper

# 1. 创建实例
scraper = AutoScraper()

# 2. 提供示例数据（关键步骤）
url = 'https://example.com/products'
wanted_list = ['¥299', '无线耳机']  # 从页面中复制想要提取的示例值

# 3. 学习规则
scraper.build(url, wanted_list)

# 4. 应用规则到新页面
result = scraper.get_result_similar('https://example.com/products?page=2')
print(result)
```

#### 第三步：批量处理

```python
# 批量处理多个 URL
urls = [
    'https://example.com/products?page=1',
    'https://example.com/products?page=2',
    'https://example.com/products?page=3'
]

for url in urls:
    result = scraper.get_result_similar(url)
    print(f"{url}: {result}")
```

#### 第四步：结果保存

```python
import json
import csv

# 保存为 JSON
with open('output.json', 'w', encoding='utf-8') as f:
    json.dump(result, f, ensure_ascii=False, indent=2)

# 保存为 CSV
with open('output.csv', 'w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    writer.writerow(['字段1', '字段2'])
    for item in result:
        writer.writerow(item)
```

### 输出规范

| 输出类型 | 格式 | 示例 |
|----------|------|------|
| 单页结果 | Python 列表 | `['¥299', '无线耳机']` |
| 多页结果 | 列表的列表 | `[['¥299', '无线耳机'], ['¥399', '降噪耳机']]` |
| 结构化输出 | JSON 格式 | `{"price": "¥299", "name": "无线耳机"}` |

---

## 四、置信度门控机制

### 置信度等级

| 等级 | 标识 | 含义 | 处理方式 |
|------|------|------|----------|
| 高 | ✅ 置信度 ≥ 90% | 提取结果与示例数据高度匹配 | 直接输出 |
| 中 | ⚠️ 置信度 70%-89% | 部分字段匹配，可能存在偏差 | 输出结果并提示人工复核 |
| 低 | ❓ 置信度 < 70% | 页面结构变化或规则失效 | 输出 `[需核实:字段名]` 占位符 |

### 信息不足处理规则

1. **字段缺失**：当目标字段在页面中不存在时，输出 `[需核实:字段名]`，不编造数据
2. **结构变化**：当页面结构改变导致规则失效时，提示用户重新提供示例数据
3. **多值歧义**：当多个元素匹配同一规则时，全部输出并标注"存在多个匹配项"

```python
# 置信度检查示例
result = scraper.get_result_similar(url)
if not result:
    print("[需核实:目标数据] 页面结构可能已变化，请重新提供示例数据")
elif len(result) < len(wanted_list):
    print(f"⚠️ 部分字段缺失，期望 {len(wanted_list)} 个，实际获取 {len(result)} 个")
```

---

## 五、错误码体系

| 错误码 | 错误描述 | 用户提示话术 | 修正步骤 |
|--------|----------|--------------|----------|
| E001 | URL 无法访问 | "目标地址无法访问，请检查网络或 URL 是否正确" | 1. 浏览器打开 URL 验证<br>2. 检查网络连接<br>3. 确认无访问限制 |
| E002 | 示例数据不匹配 | "提供的示例数据在页面中未找到，请确认示例值准确" | 1. 从页面复制精确文本<br>2. 去除多余空格<br>3. 确认数据在 HTML 中可见 |
| E003 | 规则学习失败 | "无法从当前页面学习提取规则，页面结构可能过于复杂" | 1. 简化示例数据<br>2. 尝试更具体的文本片段<br>3. 检查页面是否为动态渲染 |
| E004 | 批量处理中断 | "批量处理过程中出现异常，已停止后续操作" | 1. 检查异常 URL<br>2. 单独处理失败项<br>3. 添加重试机制 |
| E005 | 输出格式错误 | "输出格式不符合预期，请检查字段映射" | 1. 确认字段名称<br>2. 检查数据类型<br>3. 调整输出配置 |

---

## 六、FAQ 与反模式对照

### 常见坑位

| 坑位 | 错误做法（反模式） | 正确做法 |
|------|-------------------|----------|
| 坑 1：示例数据不精确 | 使用模糊描述如"价格"作为示例 | 使用页面上的精确文本如"¥299"作为示例 |
| 坑 2：忽略页面结构变化 | 一次学习永久使用，不维护规则 | 定期重新学习规则，监控提取成功率 |
| 坑 3：过度依赖单一规则 | 只用一个示例数据训练，覆盖不全 | 提供 2-3 个不同位置的示例，增强规则鲁棒性 |
| 坑 4：忽略异常处理 | 不处理空结果和异常情况 | 添加空值检查和错误捕获机制 |
| 坑 5：混淆静态与动态内容 | 试图抓取 AJAX 加载的内容 | 确认数据在 HTML 源码中可见，否则需配合其他工具 |

### 反模式对照表

| 反模式 | 问题 | 推荐替代方案 |
|--------|------|--------------|
| 用 AutoScraper 抓取需要登录的数据 | 无法绕过认证 | 使用 Selenium 或 Playwright 处理认证流程 |
| 抓取频率过高导致 IP 被封 | 违反网站使用条款 | 设置合理请求间隔，遵守 robots.txt |
| 将抓取数据用于商业用途 | 可能涉及版权问题 | 确认数据使用许可，遵守相关法律法规 |

---

## 七、渐进式学习路径

### 🚀 新手快速上手（5 分钟）

1. 安装：`pip install autoscraper`
2. 复制下方最小示例，替换 URL 和示例数据
3. 运行并查看输出

```python
from autoscraper import AutoScraper

url = 'https://example.com'
wanted_list = ['示例文本']  # 替换为页面上的实际文本
scraper = AutoScraper()
scraper.build(url, wanted_list)
print(scraper.get_result_similar(url))
```

### 🔧 进阶用户指南

#### 规则持久化

```python
# 保存学习到的规则
scraper.save('my_scraper_rules.json')

# 加载已有规则
scraper = AutoScraper()
scraper.load('my_scraper_rules.json')
```

#### 自定义分组

```python
# 按组管理不同数据类型的规则
scraper.build(url, wanted_list, group_id='products')
scraper.build(url, ['其他数据'], group_id='metadata')

# 按组提取
result = scraper.get_result_similar(url, group_id='products')
```

#### 性能优化建议

| 场景 | 建议 |
|------|------|
| 大量 URL 抓取 | 使用 `asyncio` 异步处理 |
| 频繁规则更新 | 使用 `group_id` 分组管理 |
| 结果后处理 | 配合 `pandas` 进行数据清洗 |
| 定时任务 | 使用 `cron` 或 `schedule` 库调度 |

---

## 八、命令行工具

AutoScraper 提供命令行接口：

```bash
# 查看版本
python -m autoscraper --version

# 运行自检
python -m autoscraper --selftest
```

---

## 用户协议

<!-- user-agreement-injected -->

**使用本 Skill 即表示您同意以下条款：**

1. **责任承担**：使用者自行承担使用本 Skill 的全部责任。因使用本 Skill 产生的任何直接或间接损失，包括但不限于数据丢失、业务中断、法律纠纷，本 Skill 作者及贡献者不承担任何责任。

2. **合法使用**：使用者承诺将本 Skill 仅用于合法目的，遵守适用的法律法规、网站服务条款和 robots.txt 协议。使用者应自行确认目标网站的数据抓取行为合规。

3. **禁止反向工程**：使用者不得对本 Skill 进行反向工程、反编译、破解或试图提取源代码（除非适用法律允许）。

4. **无担保声明**：本 Skill 按"现状"提供，不附带任何明示或暗示的担保，包括但不限于适销性、特定用途适用性和非侵权保证。

5. **使用限制**：使用者不得将本 Skill 用于任何可能损害第三方权益的活动，包括但不限于侵犯知识产权、侵犯隐私、干扰服务正常运行等行为。

---

## 许可证（License）

<!-- professional-license-embedded -->

**MIT License**

版权所有 (c) 2024 DataFlow Studio

特此免费授予任何获得本软件及相关文档文件（"软件"）副本的人士处理本软件的权利，包括但不限于使用、复制、修改、合并、发布、分发、再许可和/或销售软件副本的权利，并允许向其提供软件的人士这样做，但须满足以下条件：

上述版权声明和本许可声明应包含在软件的所有副本或重要部分中。

本软件按"现状"提供，不附带任何明示或暗示的保证，包括但不限于适销性、特定用途适用性和非侵权保证。在任何情况下，作者或版权持有人均不对任何索赔、损害或其他责任负责，无论是在合同诉讼、侵权行为或其他方面，由软件或软件的使用或其他交易引起或与之相关。

---

*本文档由 AI 辅助生成，仅供参考。使用前请阅读 AutoScraper 官方文档获取最新信息。*
