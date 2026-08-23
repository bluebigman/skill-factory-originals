---
slug: firecrawl
name: firecrawl
displayName: 网页采集 结构化转换 批量抓取
description: 将网页与文件批量转为结构化数据，支持搜索与自定义格式输出。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: DataForge Studio
agent_created: true
trigger_words: ["firecrawl", "网页抓取", "爬虫", "数据采集", "网页转结构化", "网页转文本", "批量抓取"]
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# firecrawl — 网页采集与结构化转换 Skill

## 一、能力边界（一页纸速查卡）

### 1.1 能做什么

| 能力项 | 说明 | 支持格式/范围 |
|--------|------|---------------|
| 网页抓取 | 将单个 URL 的 HTML 内容提取为纯文本或 Markdown | http/https 协议，动态渲染页面（需等待 JS 执行） |
| 文件转换 | 将本地 PDF、Word、Excel 等文件内容提取为结构化文本 | .pdf, .docx, .xlsx, .csv, .txt, .md |
| 批量处理 | 对多个 URL 或文件批量执行抓取与转换 | 支持列表输入，逐条输出结果 |
| 搜索采集 | 通过关键词搜索网页并提取搜索结果 | 返回标题、链接、摘要字段 |
| 自定义格式 | 按用户指定的字段结构输出 JSON 或 Markdown | 字段名、嵌套层级可自定义 |

### 1.2 不能做什么

| 限制项 | 说明 |
|--------|------|
| 登录墙内容 | 需要账号认证的页面无法抓取（如会员专区、付费内容） |
| 反爬严格站点 | 有强反爬机制（如验证码、IP 封禁）的站点可能失败 |
| 二进制文件解析 | 图片、音视频等非文本文件无法提取内容 |
| 无限滚动页面 | 依赖滚动加载的页面可能只抓取首屏内容 |
| 实时数据流 | 不适用于 WebSocket 或持续更新的动态数据源 |

### 1.3 适用对象

- 需要将网页内容转为可编辑文本的写作者、研究者
- 需要批量采集公开数据的分析师、运营人员
- 需要将 PDF/Word 转为结构化数据的开发者和数据工程师

---

## 二、触发方式

### 2.1 触发词

当用户输入以下任一关键词时，本 Skill 被激活：

- `firecrawl`
- `网页抓取`
- `爬虫`
- `数据采集`
- `网页转结构化`
- `网页转文本`
- `批量抓取`

### 2.2 场景映射表

| 用户说（大白话） | 实际需求 | Skill 响应动作 |
|------------------|----------|----------------|
| "帮我把这个网页的内容存下来" | 单页抓取 | 提取正文，输出 Markdown 文件 |
| "我有 50 个链接，想批量拿标题和正文" | 批量抓取 | 遍历 URL 列表，逐条输出结构化 JSON |
| "这个 PDF 能转成文字吗" | 文件转换 | 解析 PDF，输出纯文本或 Markdown |
| "搜一下'人工智能'相关的网页" | 搜索采集 | 执行搜索，返回标题+链接+摘要列表 |
| "把这几页的内容整理成表格" | 自定义格式 | 按用户指定字段输出 CSV/JSON |

---

## 三、标准流程

### 3.1 前置条件

| 条件 | 要求 | 检查方式 |
|------|------|----------|
| 输入文件 | 待处理文件与 Skill 工作目录一致 | `ls` 确认文件存在 |
| 命名规范 | 文件名不含空格和特殊字符，建议 `snake_case` | 目视检查 |
| URL 列表 | 批量抓取时需提供 URL 清单（txt/csv 或直接粘贴） | 确认格式正确 |
| 网络环境 | 可访问目标站点 | `curl -I <url>` 测试连通性 |

### 3.2 执行步骤

#### 步骤 1：准备输入

- 单页抓取：直接提供 URL。
- 批量抓取：创建 `urls.txt`，每行一个 URL，或提供 CSV 文件（含 `url` 列）。
- 文件转换：将文件放入当前目录，确认文件名。

#### 步骤 2：试运行（单样本验证）

```bash
# 单页抓取示例
firecrawl fetch https://example.com/article --format markdown

# 单文件转换示例
firecrawl convert ./sample.pdf --format json
```

**核对要点：**
- 输出字段是否完整（标题、正文、日期等）
- 格式是否符合预期（Markdown 标题层级、JSON 字段名）
- 编码是否正常（中文无乱码）

#### 步骤 3：批量执行

```bash
# 批量 URL 抓取
firecrawl batch --input urls.txt --output ./results/ --format json

# 批量文件转换
firecrawl batch --input ./documents/ --output ./output/ --format markdown
```

**执行前确认：**
- 输出目录已创建且有写权限
- 原始文件已备份（`cp -r ./documents/ ./backup/`）

#### 步骤 4：校验结果

```bash
# 抽查输出文件
head -50 ./results/001.json
# 核对关键字段
jq '.title, .content' ./results/001.json
```

**校验标准：**
- 随机抽取 10% 条目，核对标题、正文与源页面一致
- 检查是否有空值或截断内容
- 确认输出文件命名与输入对应

### 3.3 输出规范

| 输出格式 | 适用场景 | 字段结构 |
|----------|----------|----------|
| Markdown | 阅读、编辑 | `# 标题` + 正文段落 + 图片引用 |
| JSON | 程序处理 | `{"url": "", "title": "", "content": "", "timestamp": ""}` |
| CSV | 表格分析 | `url,title,content,timestamp` |

---

## 四、置信度门控

当抓取结果存在以下情况时，**不得编造或猜测**，必须输出占位符：

| 情况 | 输出占位符 | 说明 |
|------|------------|------|
| 页面标题缺失 | `[需核实:title]` | 未提取到 `<title>` 标签 |
| 正文内容为空 | `[需核实:content]` | 页面可能为 JS 渲染或反爬拦截 |
| 日期无法确认 | `[需核实:date]` | 页面无时间戳或格式不标准 |
| 作者信息缺失 | `[需核实:author]` | 页面无作者标注 |
| 链接解析失败 | `[需核实:url]` | 相对路径无法解析为绝对地址 |

**示例输出：**

```json
{
  "url": "https://example.com/page",
  "title": "[需核实:title]",
  "content": "[需核实:content]",
  "author": "[需核实:author]",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| `E001` | URL 格式无效 | "提供的 URL 无法解析，请检查协议头（http/https）" | 确认 URL 以 `http://` 或 `https://` 开头 |
| `E002` | 连接超时 | "目标站点响应超时，请稍后重试或检查网络" | 等待 30 秒后重试；或更换网络环境 |
| `E003` | HTTP 403/404 | "目标页面返回 403/404，可能已被删除或禁止访问" | 检查 URL 拼写；确认站点可公开访问 |
| `E004` | 文件格式不支持 | "该文件类型不在支持范围内，支持 PDF/Word/Excel/文本" | 转换文件格式后重试 |
| `E005` | 输出目录不可写 | "无法写入输出目录，请检查权限" | `chmod +w ./output/` 或更换目录 |
| `E006` | 批量列表为空 | "URL 列表为空，请检查输入文件" | 确认 `urls.txt` 非空且每行一个 URL |
| `E007` | 内容提取失败 | "页面内容提取失败，可能为动态渲染或反爬" | 尝试添加 `--wait 3000` 参数等待 JS 执行 |

---

## 六、FAQ 反模式

### 常见坑 1：动态页面抓取不全

**错误做法：** 直接抓取，忽略 JS 渲染。

**正确做法：** 使用 `--wait` 参数等待页面加载完成：

```bash
firecrawl fetch https://spa-site.com/page --wait 5000
```

### 常见坑 2：批量抓取未备份原始文件

**错误做法：** 直接对原文件执行转换，覆盖源数据。

**正确做法：** 先备份再执行：

```bash
cp -r ./documents/ ./backup_documents/
firecrawl batch --input ./documents/ --output ./output/
```

### 常见坑 3：忽略反爬机制导致 IP 被封

**错误做法：** 高频请求同一站点，无间隔。

**正确做法：** 设置请求间隔：

```bash
firecrawl batch --input urls.txt --delay 2000
```

### 常见坑 4：输出格式与下游不匹配

**错误做法：** 直接使用默认格式，未与下游确认字段。

**正确做法：** 先试运行单条，确认字段结构后再批量执行。

### 常见坑 5：忽略编码问题

**错误做法：** 抓取中文页面后出现乱码。

**正确做法：** 指定编码参数：

```bash
firecrawl fetch https://chinese-site.com --encoding utf-8
```

---

## 七、渐进式披露

### 7.1 速查卡（30 秒上手）

```
1. 单页抓取：  firecrawl fetch <url> --format markdown
2. 批量抓取：  firecrawl batch --input urls.txt --output ./out/
3. 文件转换：  firecrawl convert ./file.pdf --format json
4. 搜索采集：  firecrawl search "关键词" --limit 10
5. 自定义格式：firecrawl fetch <url> --schema '{"title":"h1","content":"article"}'
```

### 7.2 新手路径（首次使用）

1. 阅读「能力边界」确认需求在支持范围内
2. 准备单个 URL 或文件，执行试运行
3. 核对输出字段与格式
4. 确认无误后执行批量操作
5. 抽查校验结果

### 7.3 进阶路径（熟练用户）

1. 使用 `--schema` 自定义输出字段结构
2. 结合 `--delay` 和 `--wait` 处理复杂页面
3. 编写脚本批量处理多批次数据
4. 将输出接入下游数据处理管道（如 ETL）

---

## 八、参数速查表

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `--format` | string | `markdown` | 输出格式：`markdown` / `json` / `csv` |
| `--output` | string | `./output/` | 输出目录 |
| `--wait` | int | `0` | 等待 JS 渲染时间（毫秒） |
| `--delay` | int | `0` | 批量请求间隔（毫秒） |
| `--encoding` | string | `utf-8` | 字符编码 |
| `--limit` | int | `10` | 搜索返回条数上限 |
| `--schema` | string | 无 | 自定义字段映射（JSON 格式） |
| `--timeout` | int | `30000` | 请求超时时间（毫秒） |

---

## 九、用户协议

<!-- user-agreement-injected -->

**使用本 Skill 即表示您同意以下条款：**

1. **责任承担**：使用者自行承担因使用本 Skill 产生的全部责任，包括但不限于数据采集的合法性、内容使用的合规性、以及因操作不当导致的任何损失。
2. **禁止反向工程**：不得对本 Skill 的底层逻辑、代码结构进行反向工程、反编译或试图提取源代码。
3. **合规使用**：使用者应遵守目标网站的服务条款、robots.txt 协议及相关法律法规，不得将本 Skill 用于非法用途。
4. **无担保声明**：本 Skill 按"原样"提供，不附带任何明示或暗示的担保，包括但不限于适销性、特定用途适用性和非侵权保证。

---

## 十、许可证（License）

<!-- professional-license-embedded -->

**MIT License**

Copyright (c) 2024 DataForge Studio

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
