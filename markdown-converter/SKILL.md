---
slug: markdown-converter
name: markdown-converter
displayName: 文档转写 Markdown 格式整理
description: 将文本、文件或网页链接转为结构化 Markdown，保留要点并标注可信度。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 林墨
agent_created: true
trigger_words: ["markdown转换", "md转换", "转markdown", "文本转md", "网页转md", "格式整理", "文档转写"]
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# Markdown 转换器（markdown-converter）使用指南

## 一、能力边界速查卡

本 Skill 用于将非结构化内容（纯文本、本地文件、网页链接）转换为结构清晰的 Markdown 文档。以下是能力边界一览：

| 能力维度 | 支持情况 | 说明 |
|---------|---------|------|
| 纯文本输入 | ✅ 支持 | 直接粘贴或通过标准输入传入 |
| 本地文件输入 | ✅ 支持 | 需指定文件路径，支持 `.txt`、`.md`、`.html` 等格式 |
| 网页链接输入 | ✅ 支持 | 自动抓取网页正文，去除导航、广告等干扰元素 |
| 标题层级识别 | ✅ 支持 | 自动识别 1-4 级标题，超出部分降级处理 |
| 列表结构识别 | ✅ 支持 | 无序/有序列表自动转换，嵌套缩进保留 |
| 表格结构识别 | ✅ 支持 | 识别规则表格并转为 GitHub 风格表格 |
| 代码块识别 | ✅ 支持 | 识别代码片段并标注语言类型 |
| 引用块识别 | ✅ 支持 | 识别引用内容并添加 `>` 前缀 |
| 图片转换 | ❌ 不支持 | 图片链接保留原 URL，不做下载或转存 |
| 复杂排版还原 | ❌ 不支持 | 如多栏布局、浮动元素等无法还原 |
| 数学公式转换 | ❌ 不支持 | LaTeX 公式保留原样，不做格式转换 |
| 语音/视频内容 | ❌ 不支持 | 仅处理文本内容，不处理音视频文件 |

**适用对象**：需要快速整理文档结构的内容创作者、需要批量转换格式的开发者、需要从网页提取要点的研究人员。

---

## 二、触发方式与场景映射

当你的请求中包含以下关键词时，本 Skill 将被激活：

| 触发词 | 使用场景示例 |
|-------|-------------|
| markdown转换 | "帮我把这段文字做 markdown 转换" |
| md转换 | "这个文件帮我 md 转换一下" |
| 转markdown | "把这篇网页文章转 markdown" |
| 文本转md | "这段会议纪要文本转 md 格式" |
| 网页转md | "这个链接内容网页转 md" |
| 格式整理 | "帮我把这份文档做格式整理" |
| 文档转写 | "把这份报告文档转写成结构化格式" |

---

## 三、标准操作流程

### 前置条件

1. 确认输入内容可访问（本地文件存在、网页链接有效）
2. 确认输出目录有写入权限
3. 确认输入内容不包含违法或侵权信息

### 执行步骤

**步骤 1：准备输入**

根据内容来源选择输入方式：

| 参数 | 说明 | 示例 |
|------|------|------|
| `--input` | 指定本地文件路径 | `--input report.txt` |
| `--url` | 指定网页链接 | `--url https://example.com/article` |
| 标准输入 | 直接粘贴文本内容 | `echo "内容" \| python run.py` |
| `--output` | 指定输出文件路径（可选） | `--output result.md` |

**步骤 2：运行转换**

```bash
# 转换本地文件
python run.py --input test.txt --output test.md

# 转换网页链接
python run.py --url https://example.com/article --output article.md

# 从标准输入读取
cat content.txt | python run.py --output content.md
```

**步骤 3：检查输出**

打开生成的 `.md` 文件，确认：
- 标题层级是否正确（不超过 4 级）
- 列表缩进是否保留
- 表格是否完整显示
- 置信度标记是否合理

**步骤 4：处理置信度标记**

输出文档末尾可能包含 `[需核实:字段名]` 格式的标记，表示该字段信息不确定，需要人工确认。

### 输出规范

生成的 Markdown 文档遵循以下规范：

- **标题**：使用 ATX 风格（`#`），层级不超过 4 级
- **列表**：无序列表用 `-`，有序列表用 `1.`，嵌套缩进 2 空格
- **表格**：使用 GitHub 风格表格，表头与分隔行必须完整
- **代码块**：使用围栏式（```），标注语言类型
- **引用**：使用 `>` 前缀，多段引用用 `>` 空行分隔
- **置信度**：对不确定的信息，在文末添加 `[需核实:字段名]` 占位

---

## 四、置信度门控机制

本 Skill 在处理以下类型信息时，会自动进行可信度判断：

| 信息类型 | 判断规则 | 输出示例 |
|---------|---------|---------|
| 数字数据 | 来源不明确或存在矛盾时标记 | `[需核实:统计数字]` |
| 日期时间 | 无法确认准确性时标记 | `[需核实:发布日期]` |
| 专有名词 | 拼写不确定或翻译存疑时标记 | `[需核实:机构名称]` |
| 引用内容 | 无法验证原文出处时标记 | `[需核实:引用来源]` |

**重要原则**：当信息不足时，宁可使用 `[需核实:字段]` 占位，也绝不编造内容。如果输入内容过于模糊无法转换，会明确告知用户需要补充信息。

---

## 五、错误码体系

使用过程中可能遇到的错误及处理方法：

| 错误码 | 错误描述 | 提示话术 | 修正步骤 |
|--------|---------|---------|---------|
| E001 | 输入文件不存在 | "未找到指定的输入文件，请检查路径是否正确" | 确认文件路径，检查文件名拼写 |
| E002 | 网页无法访问 | "无法访问该网页，请检查链接是否有效" | 确认链接正确，检查网络连接 |
| E003 | 输入内容为空 | "输入内容为空，请提供需要转换的文本" | 检查输入内容是否完整 |
| E004 | 输出目录无权限 | "无法写入输出文件，请检查目录权限" | 更换输出目录或调整权限 |
| E005 | 内容格式无法识别 | "无法识别输入内容的格式，请确认内容类型" | 检查输入是否为支持的格式 |
| E006 | 转换过程异常 | "转换过程中出现异常，请重试或检查输入内容" | 重新运行命令，检查输入内容 |

---

## 六、常见问题与反模式对照

| 反模式（错误做法） | 正确做法 | 说明 |
|-------------------|---------|------|
| 直接复制网页全部内容 | 先去除导航、广告等干扰元素 | 保留正文核心内容 |
| 手动数空格调整列表缩进 | 使用 2 空格统一缩进 | 保证嵌套结构清晰 |
| 忽略置信度标记 | 逐一核实标记字段 | 确保关键信息准确 |
| 转换后不检查直接使用 | 打开文件检查格式 | 及时发现格式问题 |
| 用 Tab 键缩进代码块 | 使用 4 空格或围栏式代码块 | 保证代码显示正确 |
| 将不确定信息直接写入 | 添加 `[需核实:]` 标记 | 避免误导读者 |

---

## 七、渐进式学习路径

### 新手入门（5 分钟上手）

1. 准备一个 `.txt` 测试文件
2. 运行 `python run.py --input test.txt --output test.md`
3. 打开 `test.md` 查看结果
4. 尝试 `--url` 参数转换一个网页

### 进阶应用（深入使用）

1. 学习置信度标记规则，理解 `[需核实:]` 的含义
2. 掌握错误码体系，快速定位问题
3. 结合 shell 脚本批量处理多个文件
4. 自定义输出模板（修改 `run.py` 中的 `format_markdown` 函数）

### 高级定制（按需调整）

1. 调整标题层级识别规则（修改正则表达式）
2. 自定义表格识别阈值（调整启发式参数）
3. 添加自定义置信度判断逻辑
4. 扩展支持更多输入格式

---

## 八、技术实现概述

本 Skill 的转换流程包含以下阶段：

1. **输入解析**：根据参数类型（文件/URL/标准输入）读取原始内容
2. **内容清洗**：去除 HTML 标签、脚本代码、样式定义（针对网页）
3. **结构识别**：通过正则表达式和启发式规则识别标题、列表、表格
4. **Markdown 生成**：按规范输出结构化文档
5. **置信度评估**：对数字、日期、专有名词等关键信息进行可信度判断

---

## 用户协议

使用本 Skill 即表示您同意以下条款：

1. **责任承担**：使用者自行承担因使用本 Skill 产生的全部责任。包括但不限于因转换结果不准确、信息遗漏、格式错误等造成的直接或间接损失。
2. **禁止反向工程**：不得对本 Skill 的源代码进行反向工程、反编译、破解或试图提取底层算法。
3. **合法使用**：不得使用本 Skill 处理违法内容、侵犯他人知识产权的内容或违反适用法律的内容。
4. **无担保**：本 Skill 按"原样"提供，不附带任何明示或暗示的担保，包括但不限于适销性、特定用途适用性和非侵权保证。
5. **服务变更**：作者保留随时修改、更新或终止本 Skill 的权利，恕不另行通知。

<!-- user-agreement-injected -->

---

## 许可证（License）

本 Skill 采用 MIT 许可证发布：

```
MIT License

Copyright (c) 2024 林墨

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
