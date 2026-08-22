---
slug: pdf2md-web
name: pdf2md-web
displayName: 文档转写 结构化提取 置信标注
description: 将PDF或网页转为结构化Markdown，保留关键信息并标注置信度。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: DocForge Studio
agent_created: true
trigger_words: ["pdf转markdown", "网页转markdown", "pdf2md", "结构化提取", "文档转换", "网页转md", "pdf提取", "文档结构化"]
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# pdf2md-web — 文档转写与结构化提取 Skill

## 一、能力边界（一页纸速查卡）

### 1.1 能做什么

| 能力项 | 说明 | 适用场景 |
|--------|------|----------|
| PDF 转 Markdown | 解析 PDF 文本层，输出结构化 Markdown | 论文、报告、合同、说明书 |
| 网页转 Markdown | 抓取网页正文，去除导航/广告/页脚 | 博客、新闻、文档站 |
| 表格结构保留 | 识别表格行列关系，输出 Markdown 表格 | 数据报表、价目表、对比表 |
| 标题层级映射 | 根据字体大小/样式推断标题层级 | 长文档、技术手册 |
| 置信度标注 | 对不确定内容自动插入 `[需核实:字段]` 占位 | 扫描件、低清晰度文档、乱码文本 |
| 批量文件头汇总 | 同一文档多处不确定时，在文件头部集中列出 | 批量转换、质检流程 |

### 1.2 不能做什么

| 限制项 | 说明 |
|--------|------|
| 不编造内容 | 无法确认的内容一律用占位符，绝不猜测填充 |
| 不处理扫描件（无 OCR） | 纯图片型 PDF 需要先接 OCR 工具（见进阶路径） |
| 不保留复杂排版 | 多栏、浮动框、页眉页脚会被简化或丢弃 |
| 不识别手写内容 | 手写批注、签名无法提取 |
| 不保证 100% 准确 | 转换结果需人工复核，尤其是数字和专有名词 |

### 1.3 适用对象

- **适合**：文本型 PDF、网页文章、结构化报告、技术文档
- **不适合**：扫描版书籍、手写笔记、复杂排版的杂志/画册

---

## 二、触发方式与场景映射

### 2.1 触发词

直接说以下任一短语即可触发本 Skill：

- `pdf转markdown`
- `网页转markdown`
- `pdf2md`
- `结构化提取`
- `文档转换`
- `网页转md`
- `pdf提取`
- `文档结构化`

### 2.2 场景映射表

| 你说的话（大白话） | 实际执行的动作 |
|-------------------|----------------|
| "帮我把这个 PDF 变成 Markdown" | 解析 PDF → 输出 .md 文件 + 置信度标注 |
| "这个网页内容帮我存成 md" | 抓取网页 → 提取正文 → 输出 .md 文件 |
| "这个表格能转成 Markdown 表格吗" | 识别表格区域 → 输出 Markdown 表格语法 |
| "这份合同的关键条款帮我标出来" | 提取文本 → 标注不确定字段 → 输出结构化 md |
| "批量转一下这个文件夹里的 PDF" | 遍历目录 → 逐个转换 → 汇总置信度报告 |

---

## 三、标准流程

### 3.1 前置条件

| 条件 | 要求 | 检查方式 |
|------|------|----------|
| Python 环境 | Python 3.8+ | `python --version` |
| 依赖库 | pdfplumber, beautifulsoup4, requests | `pip list \| grep pdfplumber` |
| 输入文件 | PDF 文件路径或网页 URL | 文件存在 / URL 可访问 |
| 输出目录 | 有写权限的目录 | `touch test.md` 测试 |

安装依赖：

```bash
pip install pdfplumber beautifulsoup4 requests
```

### 3.2 执行步骤

#### 步骤 1：确认输入类型

```bash
# 检查文件类型
file document.pdf
# 或确认 URL 可访问
curl -I https://example.com/article
```

#### 步骤 2：运行转换命令

```bash
# PDF 转 Markdown
python pdf2md.py input.pdf -o output.md

# 网页转 Markdown
python web2md.py https://example.com/article -o output.md

# 批量转换（目录遍历）
python batch_convert.py ./pdf_folder/ -o ./output_folder/
```

#### 步骤 3：查看输出文件

```bash
cat output.md
```

重点检查：

- 文件头部是否有 `[需核实]` 汇总块
- 正文中的 `[需核实:字段]` 占位符
- 表格是否完整、标题层级是否正确

#### 步骤 4：处理不确定内容

对每个 `[需核实:...]` 标记：

1. 打开原始 PDF/网页对应位置
2. 手动确认正确内容
3. 替换占位符为真实值
4. 删除文件头部的汇总条目

### 3.3 输出规范

输出 Markdown 文件结构如下：

```markdown
---
title: 文档标题
source: 原始文件路径或URL
converted_at: 2024-01-15T10:30:00Z
confidence: 0.87
---

> ⚠️ 本文件由自动转换生成，以下字段需人工核实：
> - 第 3 段：`[需核实:合同编号]`
> - 第 7 段：`[需核实:金额数字]`

# 一级标题

正文内容...

## 二级标题

| 列1 | 列2 |
|-----|-----|
| 值1 | 值2 |

[需核实:表格第3行第2列的数据]
```

---

## 四、置信度门控机制

### 4.1 置信度分级

| 置信度区间 | 标记方式 | 处理策略 |
|-----------|----------|----------|
| 0.90 - 1.00 | 无标记 | 正常输出，无需人工复核 |
| 0.70 - 0.89 | `[需核实:字段描述]` | 输出占位符，提示人工确认 |
| 0.50 - 0.69 | `[需核实:字段描述]` + 文件头汇总 | 输出占位符，并在文件头部集中列出 |
| < 0.50 | 丢弃该内容 | 不输出，在文件头标注"内容因置信度过低被丢弃" |

### 4.2 自定义阈值

```bash
# 设置置信度阈值为 0.80
python pdf2md.py input.pdf -o output.md --confidence-threshold 0.80

# 低于阈值的直接丢弃
python pdf2md.py input.pdf -o output.md --drop-below 0.60
```

### 4.3 占位符格式

```
[需核实:具体字段描述]
```

示例：

- `[需核实:合同签署日期]`
- `[需核实:第三段中的公司名称]`
- `[需核实:表格第2行第4列的数值]`

**原则：占位符必须包含具体字段描述，不能只写 `[需核实]` 而不说明是什么。**

---

## 五、错误码体系

| 错误码 | 错误描述 | 提示话术 | 修正步骤 |
|--------|----------|----------|----------|
| E001 | 文件不存在 | "找不到指定的 PDF 文件，请检查路径" | 1. 确认路径正确；2. 检查文件名大小写；3. 确认文件未移动 |
| E002 | 文件不是 PDF | "输入文件不是有效的 PDF 格式" | 1. 用 `file` 命令检查实际格式；2. 如果是网页链接，改用网页转换模式 |
| E003 | 网页无法访问 | "无法访问该 URL，请检查网络或链接有效性" | 1. 确认 URL 拼写；2. 检查网络连接；3. 尝试用浏览器打开验证 |
| E004 | 依赖库缺失 | "缺少 pdfplumber，请先安装依赖" | 1. 执行 `pip install pdfplumber beautifulsoup4 requests` |
| E005 | 输出目录无权限 | "无法写入输出目录，请检查权限" | 1. 确认目录存在；2. 检查写权限；3. 更换输出路径 |
| E006 | 文档无文本层 | "该 PDF 没有可提取的文本层，可能是扫描件" | 1. 确认是否为扫描件；2. 接入 OCR 工具（见进阶路径） |
| E007 | 批量转换中断 | "批量转换在第 N 个文件处中断" | 1. 查看错误日志；2. 跳过问题文件；3. 重新运行剩余文件 |

---

## 六、FAQ 反模式对照

### 反模式 1：直接信任输出

**错误做法**：转换完成后不检查 `[需核实]` 标记，直接使用全部内容。

**正确做法**：转换后必须人工复核所有占位符，尤其是数字、日期、专有名词。

### 反模式 2：忽略置信度阈值

**错误做法**：不设置阈值，默认接受所有输出，包括低置信度内容。

**正确做法**：根据文档重要程度设置阈值。合同类文档建议 0.90+，一般文章 0.80 即可。

### 反模式 3：用转换结果替代原文

**错误做法**：转换后删除原始 PDF，只保留 Markdown。

**正确做法**：保留原始文件作为追溯依据，Markdown 仅作为工作副本。

### 反模式 4：不处理多栏排版

**错误做法**：直接按文本流顺序输出，导致多栏文档阅读顺序错乱。

**正确做法**：使用文本块排序算法（见进阶路径），或手动调整输出顺序。

### 反模式 5：批量转换不检查中间结果

**错误做法**：批量转换后不抽查输出质量，直接交付。

**正确做法**：批量转换后随机抽查 10% 的输出文件，确认质量达标。

---

## 七、渐进式披露：分层次阅读路径

### 7.1 新手路径（5 分钟上手）

1. 阅读「一、能力边界」了解能做什么
2. 阅读「三、标准流程」按步骤操作
3. 遇到不确定内容，查看「四、置信度门控」
4. 出错时查「五、错误码体系」

### 7.2 进阶路径（深入定制）

1. **调整置信度阈值**：修改 `--confidence-threshold` 参数
2. **处理多栏 PDF**：修改文本块排序算法，按坐标排序而非文本流顺序
3. **接入 OCR**：安装 `pytesseract` + Tesseract，对无文本层 PDF 先 OCR 再转换
4. **批量处理**：编写目录遍历脚本，支持子目录递归、断点续传
5. **自定义输出模板**：修改 frontmatter 字段，增加自定义元数据

### 7.3 专家路径（二次开发）

- 扩展解析器：支持更多输入格式（DOCX、EPUB）
- 自定义置信度算法：根据字体清晰度、字符间距等特征调整评分
- 集成到 CI/CD：作为文档处理流水线的一环

---

## 八、用户协议

<!-- user-agreement-injected -->

**使用本 Skill 即表示您同意以下条款：**

1. **责任承担**：使用者自行承担因使用本 Skill 产生的全部责任，包括但不限于内容准确性、合规性、版权问题。本 Skill 的输出结果仅供参考，不构成任何专业建议。

2. **禁止反向工程**：不得对本 Skill 进行反向工程、反编译、破解或试图提取源代码（除非适用法律允许）。

3. **无担保**：本 Skill 按"现状"提供，不附带任何明示或暗示的担保，包括但不限于适销性、特定用途适用性和非侵权保证。

4. **合规使用**：使用者应确保输入内容不违反法律法规，不侵犯第三方权益。因输入内容引发的法律纠纷由使用者自行承担。

---

## 九、许可证（License）

<!-- professional-license-embedded -->

### MIT License

Copyright (c) 2024 DocForge Studio

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

*本 Skill 由 AI 辅助生成，仅供参考。使用前请阅读相关文档并自行验证输出质量。*
