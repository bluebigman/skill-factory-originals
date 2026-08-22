---
slug: autoscraper
name: autoscraper
displayName: 网页数据采集 结构化提取 批量抓取
description: 基于规则与AI辅助的网页数据采集与结构化提取工具，支持批量抓取、多格式输出与置信度门控。
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
trigger_words: ["autoscraper", "网页抓取", "数据采集", "爬虫", "信息提取", "网页解析", "结构化提取", "批量采集"]

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# autoscraper — 网页数据采集与结构化提取工具

## 一、能力边界（一页纸速查卡）

### 1.1 能做与不能做

| 维度 | 能做 ✅ | 不能做 ❌ |
|------|---------|-----------|
| 抓取范围 | 静态HTML页面、常规动态页面（需等待渲染）、分页列表 | 需登录的强鉴权站点、反爬严格站点（如验证码）、需JS深度交互的SPA |
| 提取方式 | CSS选择器、XPath、基于规则的字段映射、AI辅助语义识别 | 无规则纯黑盒提取、图片OCR内容识别 |
| 输出格式 | JSON、CSV、Markdown表格、纯文本 | 直接写入数据库（需自行对接） |
| 批量能力 | 多URL批量抓取、分页自动翻页、限速控制 | 分布式抓取、断点续传（单次任务内） |
| 数据质量 | 置信度评分、缺失字段占位、类型校验 | 语义去重、跨源数据融合 |

### 1.2 适用对象

- **适用**：需要从公开网页中提取结构化数据的开发者、数据分析师、研究人员
- **不适用**：需要绕过登录/验证码的采集场景、需要实时流式抓取的场景、对抓取合法性有严格合规要求的商业场景（请先确认目标站点robots.txt及服务条款）

---

## 二、触发方式

### 2.1 触发词

直接使用以下任一词汇即可唤起本 Skill：

- `autoscraper`
- `网页抓取` / `网页解析` / `网页采集`
- `数据采集` / `批量采集` / `结构化提取`
- `爬虫` / `信息提取`

### 2.2 场景映射表

| 你说的话（大白话） | 本 Skill 实际执行 |
|-------------------|-------------------|
| "帮我把这个网页上的商品价格都抓下来" | 识别列表页结构，提取商品名称+价格字段，输出结构化数据 |
| "这个页面有10页数据，我想一次性全拿了" | 自动翻页遍历，合并所有页面的提取结果 |
| "我只想要标题和发布时间，别的不要" | 按字段白名单过滤，只输出指定字段 |
| "抓下来的数据准不准？" | 输出置信度评分，低置信度字段标记为 `[需核实:字段名]` |
| "能不能存成Excel能打开的格式？" | 输出CSV格式（UTF-8 with BOM，Excel可直接打开） |

---

## 三、标准流程

### 3.1 前置条件

| 条件 | 说明 |
|------|------|
| Python 3.8+ | 运行环境要求 |
| 网络连通 | 目标站点可访问，无防火墙拦截 |
| 目标URL | 需提供具体页面地址或列表页地址 |
| 提取字段（可选） | 若未指定，默认提取页面标题、正文文本、所有链接 |

### 3.2 执行步骤

**Step 1：初始化任务**

```bash
autoscraper --url "https://example.com/products" --fields "name,price,description"
```

**Step 2：干跑预览（推荐先执行）**

```bash
autoscraper --url "https://example.com/products" --fields "name,price" --dry-run --verbose
```

干跑模式会输出：
- 匹配到的选择器及命中数量
- 每条字段的置信度评分（0-1）
- 前3条提取结果的预览

**Step 3：正式抓取**

```bash
autoscraper --url "https://example.com/products" --fields "name,price" --output result.json --format json
```

**Step 4：检查输出**

```bash
cat result.json | head -20
```

### 3.3 参数速查表

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `--url` | string | 必填 | 目标页面URL |
| `--fields` | string | 标题,正文,链接 | 逗号分隔的字段名列表 |
| `--selector` | string | 自动检测 | 自定义CSS选择器，格式 `字段名=选择器` |
| `--output` | string | stdout | 输出文件路径 |
| `--format` | string | json | 输出格式：json/csv/markdown |
| `--timeout` | int | 30 | 单次请求超时（秒） |
| `--retries` | int | 3 | 失败重试次数 |
| `--delay` | float | 0.5 | 请求间隔（秒），避免被封 |
| `--max-pages` | int | 1 | 最大翻页数，0为不限 |
| `--dry-run` | bool | false | 干跑模式，不写文件 |
| `--verbose` | bool | false | 输出详细匹配信息 |
| `--confidence-threshold` | float | 0.6 | 置信度门控阈值，低于此值的字段标记为需核实 |
| `--selftest` | bool | false | 运行自检 |
| `--version` | bool | false | 显示版本号 |

### 3.4 输出规范

**JSON 输出格式：**

```json
{
  "task_id": "a3f8c2e1-9b4d-4f7a-8c1e-2d5b6a7c8d9e",
  "url": "https://example.com/products",
  "extracted_at": "2025-01-15T10:30:00Z",
  "total_items": 24,
  "items": [
    {
      "name": "商品A",
      "price": "¥199.00",
      "description": "商品描述文本",
      "_confidence": {"name": 0.98, "price": 0.95, "description": 0.87}
    }
  ],
  "warnings": ["字段 'description' 在第7条记录中置信度低于阈值，已标记"]
}
```

**CSV 输出格式：** UTF-8 with BOM，首行为字段名，后续为数据行。低置信度字段值替换为 `[需核实:字段名]`。

---

## 四、置信度门控

### 4.1 门控机制

本工具对每个提取字段计算置信度评分（0-1），评分依据：

- 选择器命中率（命中元素数 / 预期元素数）
- 数据格式一致性（如价格字段是否符合货币格式）
- 字段完整性（是否所有记录均提取到该字段）

### 4.2 门控规则

| 置信度区间 | 处理方式 |
|-----------|---------|
| 0.9 - 1.0 | 正常输出，不做标记 |
| 0.6 - 0.9 | 正常输出，在 `warnings` 中提示 |
| 0.0 - 0.6 | 字段值替换为 `[需核实:字段名]`，在 `warnings` 中说明原因 |

### 4.3 门控调整

```bash
# 提高门控阈值，更严格
autoscraper --url "..." --fields "..." --confidence-threshold 0.8

# 降低门控阈值，容忍更多不确定数据
autoscraper --url "..." --fields "..." --confidence-threshold 0.4
```

**重要原则**：本工具**绝不编造数据**。当无法从页面中提取到某个字段时，输出 `[需核实:字段名]` 占位符，而不是猜测或填充虚假值。

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|---------|---------|
| `E001` | 页面加载超时 | "页面加载超时，请检查网络或增加超时时间" | 1. 使用 `--timeout 60` 增加超时时间<br>2. 使用 `--retries 5` 增加重试次数<br>3. 检查网络连接和代理设置 |
| `E002` | 选择器未匹配 | "未找到匹配元素，请检查选择器是否正确" | 1. 使用 `--dry-run --verbose` 查看详细匹配信息<br>2. 在浏览器开发者工具中重新验证选择器<br>3. 检查是否因懒加载导致元素未渲染（滚动页面后重试） |
| `E003` | 输出目录不可写 | "无法写入输出文件，请检查路径权限" | 1. 检查输出目录是否存在且有写权限<br>2. 使用 `--dry-run` 先预览输出内容<br>3. 更换输出路径 |
| `E004` | 目标站点拒绝访问 | "目标站点返回403/429，可能触发了反爬机制" | 1. 增加 `--delay 2` 降低请求频率<br>2. 检查是否被站点封禁IP<br>3. 确认目标站点是否允许爬虫访问 |
| `E005` | 字段提取失败 | "部分字段提取失败，请检查字段名或选择器" | 1. 使用 `--verbose` 查看具体失败原因<br>2. 检查字段名是否与页面结构匹配<br>3. 使用 `--selector` 手动指定选择器 |
| `E006` | 翻页失败 | "翻页过程中出现异常，已停止" | 1. 检查分页URL规律是否正确<br>2. 使用 `--max-pages 3` 限制翻页数量测试<br>3. 检查是否因动态加载导致翻页失效 |

---

## 六、FAQ 反模式对照

| 常见坑（反模式） | 问题说明 | 正确做法 |
|-----------------|---------|---------|
| **盲目信任提取结果** | 直接使用未经验证的数据做决策 | 始终检查 `_confidence` 字段和 `warnings` 数组，对 `[需核实]` 字段人工复核 |
| **抓取频率过高** | 不设置 `--delay`，导致IP被封 | 设置合理的 `--delay 1-3`，遵守目标站点robots.txt |
| **忽略页面动态加载** | 页面内容由JS渲染，直接抓取得到空数据 | 先使用 `--dry-run --verbose` 检查是否匹配到元素；若为空，考虑使用渲染工具或检查是否有API接口 |
| **一次抓取所有字段** | 请求过多字段导致置信度普遍偏低 | 聚焦核心字段，分批提取；先提取少量字段验证流程，再逐步增加 |
| **不检查输出文件** | 抓取完成后直接使用，未发现数据截断或格式错误 | 使用 `--dry-run` 预览前几条记录；抓取完成后抽查输出文件的前20行 |

---

## 七、渐进式披露

### 7.1 速查卡（30秒上手）

```bash
# 基本用法
autoscraper --url "https://example.com" --fields "title,content"

# 干跑预览
autoscraper --url "https://example.com" --fields "title,content" --dry-run --verbose

# 批量翻页 + CSV输出
autoscraper --url "https://example.com/list?page=1" --fields "name,price" --max-pages 10 --format csv --output data.csv
```

### 7.2 分层次阅读路径

**新手路径（首次使用）：**
1. 阅读「能力边界」了解工具能做什么
2. 使用 `--dry-run --verbose` 在目标页面上测试
3. 确认提取结果后，使用 `--format json` 正式输出
4. 检查 `warnings` 数组中的置信度提示

**进阶路径（复杂场景）：**
1. 阅读「参数速查表」了解全部参数
2. 使用 `--selector` 自定义选择器处理复杂页面
3. 调整 `--confidence-threshold` 控制数据质量
4. 结合 `--delay` 和 `--retries` 应对反爬策略
5. 使用 `--max-pages` 控制批量抓取规模

**专家路径（深度定制）：**
1. 阅读「错误码体系」定位问题
2. 结合 `--verbose` 输出分析选择器匹配详情
3. 对特殊页面结构，先手动分析HTML，再构造精确选择器
4. 使用 `--selftest` 验证工具自身运行状态

---

## 八、使用示例

### 示例1：提取新闻标题和发布时间

```bash
autoscraper --url "https://news.example.com/tech" --fields "title,publish_time" --format json --output news.json
```

### 示例2：批量抓取商品列表（5页）

```bash
autoscraper --url "https://shop.example.com/products?page=1" --fields "name,price,rating" --max-pages 5 --delay 1.5 --format csv --output products.csv
```

### 示例3：自定义选择器提取

```bash
autoscraper --url "https://blog.example.com/post/123" --fields "author,body" --selector "author=.post-author,body=.post-content" --output post.json
```

### 示例4：严格模式（高置信度要求）

```bash
autoscraper --url "https://data.example.com/table" --fields "col1,col2,col3" --confidence-threshold 0.85 --output strict.json
```

---

## 九、用户协议

<!-- user-agreement-injected -->

**使用本 Skill 即表示您同意以下条款：**

1. **责任承担**：使用者自行承担因使用本 Skill 产生的全部责任，包括但不限于数据采集的合法性、目标网站的服务条款合规性、采集数据的后续使用方式等。本 Skill 作者不对任何因使用本工具导致的直接或间接损失承担责任。

2. **合法使用**：使用者承诺仅将本 Skill 用于合法目的，遵守适用的法律法规、目标网站的 robots.txt 协议及服务条款。禁止将本 Skill 用于任何侵犯他人权益、违反法律法规的活动。

3. **禁止反向工程**：使用者不得对本 Skill 进行反向工程、反编译、破解或试图提取底层算法逻辑。不得移除或修改本 Skill 中的任何版权声明、水印或标识。

4. **数据合规**：使用者应确保采集、存储、处理和使用数据的行为符合《个人信息保护法》《数据安全法》等相关法律法规的要求，不得采集受保护的个人信息或敏感数据。

5. **免责声明**：本 Skill 按"现状"提供，不附带任何明示或暗示的保证。作者不保证本 Skill 的准确性、可靠性、完整性或适用性。

---

## 十、许可证（License）

<!-- professional-license-embedded -->

**MIT License**

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

*本 Skill 由 AI 辅助生成，仅供参考。使用前请阅读相关文档并自行验证输出结果。*
