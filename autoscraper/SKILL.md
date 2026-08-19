---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: autoscraper
name: autoscraper
displayName: 网页数据采集 结构化提取 批量抓取
description: 基于规则与AI辅助的网页数据采集与结构化提取工具，支持批量抓取、多格式输出与置信度门控。
version: 2.0.1
rules_version: cpr-20260819-n551
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/autoscraper
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: DataCraft Studio
agent_created: true
trigger_words: ["autoscraper", "网页抓取", "数据采集", "爬虫", "信息提取", "页面解析", "结构化数据"]
---

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->


> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# autoscraper — 网页数据采集与结构化提取工具

## 一、能力边界（一页纸速查卡）

### 1.1 能做什么

| 能力项 | 说明 | 示例 |
|--------|------|------|
| 规则匹配 | 基于 CSS 选择器 / XPath 提取页面元素 | `#product-title`, `//div[@class="price"]` |
| AI 辅助识别 | 对模糊区域进行语义推断，辅助定位目标字段 | 识别"发布日期"附近的日期文本 |
| 批量抓取 | 支持多 URL 列表输入，顺序或并发抓取 | 100 个商品页依次提取 |
| 多格式输出 | 输出 JSON / CSV / Markdown 表格 | `--format json` |
| 置信度门控 | 对低置信度字段输出 `[需核实:字段名]` 占位 | 不编造数据 |
| 增量更新 | 基于内容哈希跳过未变化页面 | `--incremental` |

### 1.2 不能做什么（明确边界）

| 限制项 | 说明 |
|--------|------|
| 不处理登录态 | 需要会话认证的页面需预先提供 Cookie 文件 |
| 不执行复杂 JS 渲染 | 对重度 SPA 页面需配合无头浏览器（外部工具） |
| 不自动绕过反爬 | 不提供验证码识别、IP 轮换等对抗功能 |
| 不保证字段完整性 | 页面结构变化时，提取结果可能缺失字段 |
| 不承担数据合规责任 | 使用者需自行确认目标网站的数据采集合法性 |

### 1.3 适用对象

- 需要定期采集公开数据的分析师
- 构建结构化数据集的研究人员
- 需要监控竞品公开信息的运营人员
- 对网页内容进行归档整理的开发者

---

## 二、触发方式

### 2.1 触发词

当对话中出现以下任一词汇时，自动激活本 Skill：

- 核心触发：`autoscraper`、`网页抓取`、`数据采集`、`爬虫`、`信息提取`
- 补充触发：`页面解析`、`结构化数据`、`批量采集`

### 2.2 场景映射表

| 用户说（大白话） | 实际需求 | 本 Skill 响应 |
|------------------|----------|---------------|
| "帮我把这个网页上的商品价格都抓下来" | 提取列表页中的价格字段 | 提供选择器方案 + 执行命令 |
| "我想批量下载这个网站的文章标题和发布时间" | 多页面字段提取 | 生成批量抓取配置 |
| "这个页面的数据怎么导出成 Excel" | 格式转换 | 输出 CSV 格式命令 |
| "抓到的数据不太准，有些是空的" | 提取精度问题 | 诊断选择器 + 调整置信度阈值 |

---

## 三、标准流程

### 3.1 前置条件

| 条件 | 要求 | 验证方式 |
|------|------|----------|
| Python 环境 | ≥ 3.8 | `python --version` |
| 网络连通 | 目标站点可访问 | `curl -I <目标URL>` |
| 输出目录 | 存在且有写权限 | `mkdir -p ./output && touch ./output/.write_test` |
| 目标 URL | 完整且有效 | 浏览器中可正常打开 |

### 3.2 执行步骤（分步编号）

**Step 1：初始化配置**

```bash
autoscraper init --project my_scraper
```

生成项目骨架，包含 `config.yaml` 和 `selectors.json`。

**Step 2：定义选择器**

编辑 `selectors.json`：

```json
{
  "fields": {
    "title": {"selector": "h1.product-title", "type": "text"},
    "price": {"selector": "span.price-value", "type": "float"},
    "availability": {"selector": ".stock-status", "type": "text", "required": false}
  },
  "page": {
    "list_item": "div.product-card",
    "pagination": "a.next-page"
  }
}
```

**Step 3：干跑验证**

```bash
autoscraper run --url https://example.com/products --dry-run --verbose
```

输出将显示每个字段的匹配状态和置信度。

**Step 4：正式抓取**

```bash
autoscraper run --url https://example.com/products --format json --output ./output/data.json
```

**Step 5：检查输出**

```bash
cat ./output/data.json | jq '.'
```

### 3.3 输出规范

| 格式 | 适用场景 | 示例 |
|------|----------|------|
| JSON | 程序化处理 | `{"title": "商品A", "price": 199.0}` |
| CSV | Excel 分析 | `title,price\n商品A,199.0` |
| Markdown | 文档嵌入 | `\| 商品A \| 199.0 \|` |

---

## 四、置信度门控

### 4.1 置信度评分机制

每个提取字段附带 0-1 的置信度分数：

| 分数区间 | 含义 | 处理方式 |
|----------|------|----------|
| 0.9 - 1.0 | 高置信，选择器精确匹配 | 直接输出 |
| 0.7 - 0.9 | 中置信，存在轻微歧义 | 输出并附带警告 |
| 0.5 - 0.7 | 低置信，需要人工确认 | 输出 `[需核实:字段名]` |
| < 0.5 | 极低置信，疑似错误 | 丢弃字段，记录日志 |

### 4.2 门控阈值配置

```yaml
confidence:
  global_threshold: 0.7        # 全局阈值
  field_overrides:
    price: 0.85                # 价格字段要求更高
    description: 0.5           # 描述字段可放宽
```

### 4.3 不编造原则

当信息不足时，遵循以下规则：

1. **缺失字段** → 输出 `[需核实:字段名]`，不猜测值
2. **类型不匹配** → 输出 `[需核实:字段名]`，不强制转换
3. **多值冲突** → 输出 `[需核实:字段名]`，不随机选取

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| E001 | 选择器无匹配 | "未找到与选择器匹配的元素" | 1. 使用 `--dry-run --verbose` 查看详细匹配信息；2. 在浏览器开发者工具中重新验证选择器；3. 检查是否因懒加载导致元素未渲染（滚动页面后重试） |
| E002 | 网络超时 | "请求超时，请检查网络或增加超时时间" | 1. 使用 `--timeout 60` 增加超时时间；2. 使用 `--retries 5` 增加重试次数；3. 检查网络连接和代理设置 |
| E003 | 输出写入失败 | "无法写入输出文件，请检查路径权限" | 1. 检查输出目录是否存在且有写权限；2. 使用 `--dry-run` 先预览输出内容；3. 更换输出路径 |
| E004 | 配置解析错误 | "配置文件格式不正确，请检查 JSON/YAML 语法" | 1. 使用 `autoscraper validate --config <path>` 验证；2. 检查引号和逗号；3. 参考示例配置 |
| E005 | 批量任务中断 | "批量抓取在第 N 个 URL 处中断" | 1. 使用 `--resume` 从断点继续；2. 检查中断 URL 的响应状态；3. 将该 URL 加入黑名单后重试 |
| E006 | 置信度过低 | "提取结果置信度低于阈值，已标记需核实" | 1. 检查选择器是否指向正确元素；2. 调整字段级阈值；3. 使用 AI 辅助模式重新识别 |

---

## 六、FAQ 反模式

### 6.1 常见坑与反模式对照

| 常见坑 | 反模式（错误做法） | 正确做法 |
|--------|---------------------|----------|
| 选择器过于宽泛 | 使用 `div` 作为选择器 | 使用带 class 或 id 的精确选择器，如 `div.product-card > h2` |
| 忽略页面结构变化 | 一次配置永久使用 | 定期（如每周）运行 `--dry-run` 检查选择器有效性 |
| 盲目信任提取结果 | 不检查置信度直接入库 | 设置合理阈值，对低置信字段进行人工复核 |
| 并发请求过猛 | 默认 10 并发直接跑 | 从 1 并发开始，逐步增加，观察目标站点响应 |
| 忽略 robots.txt | 直接抓取被禁止路径 | 先检查 `robots.txt`，遵守站点规则 |

### 6.2 反模式示例

**反模式 1：不验证直接生产**

```bash
# 错误：跳过干跑直接抓取
autoscraper run --url https://example.com --format csv --output data.csv

# 正确：先干跑验证
autoscraper run --url https://example.com --dry-run --verbose
```

**反模式 2：忽略错误码**

```bash
# 错误：E001 后继续批量抓取
autoscraper run --urls urls.txt --continue-on-error

# 正确：先修复选择器
autoscraper run --url https://example.com --dry-run --verbose
# 修复 selectors.json 后重新执行
```

---

## 七、渐进式披露

### 7.1 速查卡（30 秒上手）

```bash
# 1. 初始化
autoscraper init --project my_scraper

# 2. 编辑 selectors.json（定义要提取的字段）

# 3. 干跑验证
autoscraper run --url <目标URL> --dry-run

# 4. 正式抓取
autoscraper run --url <目标URL> --format json --output result.json

# 5. 查看结果
cat result.json
```

### 7.2 新手路径（首次使用）

1. 阅读「能力边界」了解工具范围
2. 使用「速查卡」完成第一次抓取
3. 遇到问题时查阅「错误码体系」
4. 熟悉后阅读「标准流程」深入了解配置项

### 7.3 进阶路径（深度使用）

1. 掌握「置信度门控」的阈值调优
2. 学习批量抓取与增量更新
3. 自定义选择器模板复用
4. 结合外部工具处理 JS 渲染页面
5. 建立定期验证机制确保提取稳定性

---

## 八、参数参考表

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `--url` | string | 无 | 目标页面 URL |
| `--urls` | file | 无 | URL 列表文件（每行一个） |
| `--format` | string | `json` | 输出格式：json/csv/markdown |
| `--output` | path | `./output` | 输出文件路径 |
| `--dry-run` | flag | false | 干跑模式，不写入文件 |
| `--verbose` | flag | false | 输出详细日志 |
| `--timeout` | int | 30 | 请求超时（秒） |
| `--retries` | int | 3 | 失败重试次数 |
| `--concurrency` | int | 1 | 并发请求数 |
| `--incremental` | flag | false | 增量模式，跳过未变化页面 |
| `--resume` | flag | false | 从上次中断处继续 |
| `--threshold` | float | 0.7 | 全局置信度阈值 |
| `--config` | path | `./config.yaml` | 配置文件路径 |

---

## 九、用户协议

<!-- user-agreement-injected -->

**使用本 Skill 即表示您同意以下条款：**

1. **责任承担**：使用者自行承担因使用本 Skill 产生的全部责任，包括但不限于数据采集的合法性、数据使用的合规性、以及对第三方网站造成的影响。

2. **合法使用**：使用者承诺仅将本 Skill 用于合法目的，遵守目标网站的 `robots.txt` 规则、服务条款及相关法律法规。

3. **禁止反向工程**：使用者不得对本 Skill 进行反向工程、反编译、破解或试图提取源代码（除非适用法律允许）。

4. **无担保**：本 Skill 按"现状"提供，不附带任何明示或暗示的担保，包括但不限于适销性、特定用途适用性和非侵权性。

5. **免责**：在任何情况下，Skill 作者均不对因使用或无法使用本 Skill 而产生的任何损害承担责任，包括但不限于直接损害、间接损害、附带损害或利润损失。

---

## 十、许可证（License）

<!-- professional-license-embedded -->

**MIT License**

Copyright (c) 2024 DataCraft Studio

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

*本 Skill 由 AI 辅助生成，仅供参考。使用前请阅读相关文档并自行验证适用性。*
