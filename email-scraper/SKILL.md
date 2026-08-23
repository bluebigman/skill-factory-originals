---
slug: email-scraper
name: email-scraper
displayName: 网站邮箱采集 线索挖掘 联系人提取
description: 递归爬取网站页面，自动提取并整理公开邮箱地址。
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
trigger_words: ["email-scraper", "爬虫采集", "邮箱抓取", "邮件地址收集", "网站邮箱提取", "邮件线索挖掘", "联系人批量获取"]
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# email-scraper 技能手册

## 一、能力边界（一页纸速查卡）

### 1.1 能做与不能做

| 维度 | 能做 ✅ | 不能做 ❌ |
|------|---------|-----------|
| 采集范围 | 公开可访问的网页、静态HTML、部分动态渲染页面 | 需登录/付费/验证码的页面、robots.txt 明确禁止的站点 |
| 提取对象 | 标准格式邮箱（`name@domain.tld`）、`mailto:` 链接中的地址 | 图片/PDF/JS文件内嵌的邮箱、混淆编码的地址 |
| 递归深度 | 默认 2 层，可配置 1~5 层 | 无限深度（会触发反爬机制） |
| 去重策略 | 同域名内自动去重，跨页面合并 | 跨域名去重（不同子域视为不同来源） |
| 输出格式 | JSON / CSV / 纯文本列表 | 直接写入外部数据库或 CRM 系统 |
| 合规处理 | 仅采集公开信息，遵守 robots.txt | 绕过访问限制、批量发送邮件（本工具不包含发送功能） |

### 1.2 适用对象

- **市场人员**：寻找潜在客户的公开联系邮箱
- **研究人员**：收集学术机构、政府网站的公开联系方式
- **开发者**：构建联系人数据库或进行竞品分析
- **运营人员**：整理行业媒体、合作方的公开邮箱

### 1.3 不适用场景

- 需要登录后才能查看的联系方式
- 已被 Cloudflare 等防护机制拦截的站点
- 需要遵守 GDPR 等隐私法规的敏感数据采集（请自行评估合规性）

---

## 二、触发方式

### 2.1 触发词

直接使用以下任一方式唤起本技能：

```
email-scraper
爬虫采集
邮箱抓取
邮件地址收集
网站邮箱提取
邮件线索挖掘
联系人批量获取
```

### 2.2 场景映射表

| 你的需求（大白话） | 实际执行动作 |
|-------------------|-------------|
| "帮我找一下这个公司官网上的邮箱" | 单域名采集，默认深度 2 层 |
| "把这个行业几个网站的邮箱都抓下来" | 多域名批量采集，输出合并文件 |
| "只要联系页和关于页的邮箱" | 指定路径过滤，只爬 `/contact` 和 `/about` |
| "别爬太深，首页看看就行" | 设置深度为 1，仅采集首页 |
| "把结果整理成表格给我" | 输出 CSV 格式，含来源页面 URL |

---

## 三、标准流程

### 3.1 前置条件

| 条件项 | 要求 | 说明 |
|--------|------|------|
| Python 环境 | ≥ 3.8 | 需安装 `requests`、`beautifulsoup4`、`lxml` |
| 网络环境 | 可访问目标站点 | 建议配置合理的请求间隔（≥1秒） |
| 目标 URL | 合法且公开 | 需确认 robots.txt 允许爬取 |
| 输出目录 | 存在且有写权限 | 默认输出到当前目录 `/output` 子文件夹 |

### 3.2 执行步骤

#### 第一步：初始化与参数确认

```bash
# 安装依赖（首次使用）
pip install requests beautifulsoup4 lxml

# 查看帮助
email-scraper --help
```

**核心参数表：**

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--url` | 必填 | 起始页面 URL |
| `--depth` | 2 | 递归爬取深度（1~5） |
| `--delay` | 1.0 | 请求间隔秒数（0.5~5.0） |
| `--format` | json | 输出格式：json / csv / txt |
| `--include` | 无 | 仅爬取包含指定关键词的路径（可多次指定） |
| `--exclude` | 无 | 排除包含指定关键词的路径 |
| `--same-domain` | true | 仅在同域名内爬取 |
| `--output-dir` | ./output | 输出目录 |

#### 第二步：单样本试运行

```bash
# 使用单个 URL 测试，确认输出格式
email-scraper --url https://example.com --depth 1 --format json
```

**预期输出示例（JSON）：**

```json
{
  "task_id": "20250115_143022",
  "target_url": "https://example.com",
  "crawl_depth": 1,
  "pages_scanned": 12,
  "emails_found": 5,
  "results": [
    {
      "email": "contact@example.com",
      "source_url": "https://example.com/contact",
      "context": "mailto:contact@example.com",
      "first_seen": "2025-01-15T14:30:22Z"
    }
  ]
}
```

#### 第三步：批量执行

```bash
# 多 URL 批量采集（URL 列表文件，每行一个）
email-scraper --url-list urls.txt --depth 2 --format csv --output-dir ./output
```

#### 第四步：结果校验

- 抽查 10% 的邮箱，访问其来源页面确认邮箱确实存在
- 检查是否有重复项（同邮箱多来源时保留首次出现的记录）
- 确认 CSV 中 `source_url` 字段可正常点击访问

### 3.3 输出规范

**JSON 格式字段说明：**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `task_id` | string | 是 | 任务唯一标识（时间戳） |
| `target_url` | string | 是 | 起始 URL |
| `crawl_depth` | int | 是 | 实际爬取深度 |
| `pages_scanned` | int | 是 | 扫描页面总数 |
| `emails_found` | int | 是 | 发现的唯一邮箱数 |
| `results[].email` | string | 是 | 邮箱地址 |
| `results[].source_url` | string | 是 | 发现该邮箱的页面 URL |
| `results[].context` | string | 否 | 邮箱出现的上下文（如 mailto 链接） |
| `results[].first_seen` | string | 是 | 首次发现时间（ISO 8601） |

**CSV 格式列：**

```
email,source_url,context,first_seen
contact@example.com,https://example.com/contact,mailto:contact@example.com,2025-01-15T14:30:22Z
```

---

## 四、置信度门控

### 4.1 信息不足时的处理

当遇到以下情况时，**不编造、不猜测**，使用占位符标记：

| 情况 | 处理方式 |
|------|----------|
| 页面加载失败 | 跳过该页面，在日志中记录 `[需核实:页面加载失败]` |
| 邮箱格式异常（如缺少@） | 不提取，记录 `[需核实:格式异常]` |
| 无法确认邮箱是否公开 | 标注 `[需核实:公开性]`，默认不采集 |
| 递归深度达到上限但仍有未访问链接 | 输出中标注 `[需核实:存在未遍历链接]` |

### 4.2 置信度分级

| 级别 | 说明 | 输出标记 |
|------|------|----------|
| 高 | 邮箱在 `mailto:` 链接中，且页面可公开访问 | 无特殊标记 |
| 中 | 邮箱以纯文本形式出现在页面正文中 | `[需核实:文本提取]` |
| 低 | 邮箱出现在 JS 渲染内容中，可能不准确 | `[需核实:动态渲染]` |

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| `E001` | URL 格式无效 | "请输入合法的 URL，以 http:// 或 https:// 开头" | 检查 URL 拼写，补全协议头 |
| `E002` | 连接超时 | "目标站点响应超时，请检查网络或稍后重试" | 增加 `--delay` 值，或检查目标站点可用性 |
| `E003` | robots.txt 禁止访问 | "目标站点 robots.txt 禁止爬取，已终止任务" | 更换目标站点，或确认是否有权限 |
| `E004` | 无有效邮箱 | "已扫描 N 个页面，未发现有效邮箱地址" | 调整 `--depth` 或 `--include` 参数，扩大范围 |
| `E005` | 输出目录不可写 | "无法写入输出目录，请检查权限" | 更换 `--output-dir` 或修改目录权限 |
| `E006` | 参数冲突 | "`--include` 和 `--exclude` 不能同时指定相同关键词" | 检查参数，移除冲突项 |
| `E007` | 依赖缺失 | "缺少必要依赖库，请运行 pip install -r requirements.txt" | 安装依赖后重试 |

---

## 六、FAQ 反模式对照

| 常见坑 | 反模式（错误做法） | 正确做法 |
|--------|-------------------|----------|
| 爬取过深导致被封 IP | 设置 `--depth 5` 且 `--delay 0.5` | 默认深度 2，延迟 ≥1 秒，遵守目标站点速率限制 |
| 采集到大量无效邮箱 | 直接使用默认参数全站爬取 | 先用 `--include contact` 限定路径，再逐步扩大范围 |
| 结果中邮箱格式混乱 | 手动复制粘贴整理 | 使用 `--format csv` 输出结构化数据，用 Excel 筛选 |
| 忽略 robots.txt 导致法律风险 | 直接爬取所有页面 | 先访问 `target.com/robots.txt` 确认允许范围 |
| 重复采集同一站点 | 多次运行相同命令 | 使用 `--output-dir` 区分任务，或检查已有输出文件 |

---

## 七、渐进式披露

### 7.1 速查卡（30 秒上手）

```
1. 安装依赖：pip install requests beautifulsoup4 lxml
2. 单次采集：email-scraper --url https://example.com --depth 1
3. 查看结果：打开 ./output/ 下的 JSON 或 CSV 文件
4. 批量采集：准备 urls.txt（每行一个 URL），运行 --url-list urls.txt
```

### 7.2 新手路径（首次使用）

1. 阅读「能力边界」确认工具是否适合你的场景
2. 按「标准流程」的第二步执行单样本试运行
3. 检查输出格式是否符合预期
4. 确认无误后，按第三步执行批量采集
5. 用「结果校验」清单抽查数据质量

### 7.3 进阶路径（熟练用户）

1. 结合 `--include` 和 `--exclude` 精细控制爬取范围
2. 使用 `--delay` 调节请求频率，平衡速度与稳定性
3. 对输出结果做二次清洗（去重、域名分类、有效性验证）
4. 将采集结果导入 CRM 或营销工具前，先做格式转换
5. 定期更新目标站点列表，避免采集过期数据

---

## 八、合规与伦理提醒

- 本工具仅用于采集**公开可访问**的邮箱地址
- 使用前请检查目标站点的 `robots.txt` 和服务条款
- 采集到的数据不得用于发送垃圾邮件（违反 CAN-SPAM 法案及中国《反垃圾邮件法》）
- 涉及个人信息（如个人邮箱）时，请遵守 GDPR、PIPL 等隐私法规
- 建议设置合理的请求频率，避免对目标站点造成压力

---

## 用户协议

<!-- user-agreement-injected -->

**生效日期：** 使用本 Skill 即视为同意以下条款

1. **责任承担**：使用者自行承担因使用本 Skill 产生的全部责任，包括但不限于数据采集的合法性、数据使用的合规性、以及对第三方造成的任何影响。
2. **禁止反向工程**：不得对本 Skill 的代码、逻辑、算法进行反向工程、反编译或试图提取源代码（除非适用法律允许）。
3. **数据合规**：使用者须确保采集和使用数据的行为符合当地法律法规及目标网站的服务条款。
4. **免责声明**：本 Skill 按"现状"提供，不附带任何明示或暗示的保证。作者不对采集结果的准确性、完整性或适用性承担责任。
5. **终止条款**：若使用者违反本协议，作者有权终止其使用权限。

---

## 许可证（License）

<!-- professional-license-embedded -->

### MIT License

Copyright (c) 2025 数据工坊

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

*本 Skill 由 AI 辅助生成，仅供学习参考。使用前请阅读相关文档并自行评估适用性。*
