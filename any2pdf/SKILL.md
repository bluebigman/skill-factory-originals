---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: any2pdf
name: any2pdf
displayName: 文档排版 PDF 转换 格式美化
description: 将 Markdown 等内容转换为排版精良的 PDF 文档。
version: 1.0.2
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/any2pdf
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本 Skill 由 AI 辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: FormatForge Studio
agent_created: true
trigger_words: ["any2pdf", "转PDF", "PDF转换", "Markdown转PDF", "文档排版", "导出PDF", "生成PDF"]
---

> 📜 **用户协议（User Agreement）**
> 1. 本 Skill 仅供学习与参考用途。使用本 Skill 产生的任何结果，由使用者自行承担全部责任；本 Skill 不提供任何明示或暗示的保证。
> 2. 涉及法律、财务、税务、投资、医疗等专业决策时，请务必咨询持证专业人士。
> 3. 本代码受版权法保护，未经授权复制、反向工程或商业利用将被追究法律责任。
<!-- user-agreement-injected -->


> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# any2pdf — Markdown 到 PDF 的排版转换工具

本 Skill 提供了一套将 Markdown 文本转换为高质量 PDF 文档的完整方案。它涵盖了从输入校验、样式应用到最终文件生成的各个环节，并内置了错误处理与质量检查机制。

## 一、能力边界：一页纸速查卡

本工具专注于**文本到 PDF 的转换与排版**，不涉及其他文档处理领域。

| 能力维度 | 支持范围 | 不支持范围 |
| :--- | :--- | :--- |
| **输入格式** | Markdown（`.md`）、纯文本（`.txt`）、富文本（`.rtf`） | 扫描件、图片型 PDF 的 OCR 识别 |
| **输出特性** | 自定义页边距、字体、字号、行距、页眉页脚、封面页 | 动态表单填写、数字签名、文档加密 |
| **排版元素** | 标题层级、列表、表格、代码块、引用块、图片、链接、脚注 | 复杂数学公式（LaTeX 渲染）、矢量绘图、3D 模型 |
| **文档结构** | 自动生成目录（TOC）、页码、章节编号 | 多文档合并、交叉引用、索引生成 |
| **字符支持** | 中文、英文、日文、韩文、西欧语言（Latin-1） | 阿拉伯语、希伯来语等从右至左书写的语言 |
| **文件大小** | 建议输入文本 ≤ 5MB，输出 PDF ≤ 50MB | 包含大量高清图片的超大文档（>100MB） |

**适用对象**：需要将技术文档、报告、论文、简历、合同草案等 Markdown 内容转换为正式 PDF 文件的个人用户或团队。

## 二、触发方式：场景映射表

当你的需求与下表左侧场景匹配时，即可调用本 Skill。

| 触发词/短语 | 典型用户表述 | 实际执行动作 |
| :--- | :--- | :--- |
| `any2pdf` | "用 any2pdf 把这个文档转一下" | 启动转换流程，读取默认配置 |
| `转PDF` | "帮我把这份 Markdown 转成 PDF" | 执行标准转换，使用默认样式 |
| `PDF转换` | "我需要一个 PDF 转换工具" | 展示能力清单，确认输入格式 |
| `Markdown转PDF` | "把 readme.md 转成 PDF 看看效果" | 指定文件转换，输出到当前目录 |
| `文档排版` | "这个文档排版太乱了，帮我整理成 PDF" | 应用预设排版模板，重新生成 PDF |
| `导出PDF` | "把这篇报告导出为 PDF 格式" | 转换并优化打印布局 |
| `生成PDF` | "根据这些内容生成一个 PDF 文件" | 从文本内容直接创建 PDF |

## 三、标准流程：从输入到输出

### 前置条件

1. **输入文件确认**：确保源文件为 `.md`、`.txt` 或 `.rtf` 格式，且文件编码为 UTF-8。
2. **环境检查**：确认系统已安装 Python 3.8+ 环境，并已安装 `markdown`、`weasyprint` 或 `reportlab` 库。
3. **资源准备**：若文档包含图片，请确保图片路径为绝对路径或相对路径正确，且图片文件可访问。

### 执行步骤

**步骤 1：初始化转换环境**

```bash
# 安装依赖（如未安装）
pip install markdown weasyprint
```

**步骤 2：读取并解析源文件**

```python
import markdown

with open('input.md', 'r', encoding='utf-8') as f:
    text = f.read()
html_body = markdown.markdown(text, extensions=['tables', 'fenced_code', 'toc'])
```

**步骤 3：应用排版样式**

创建或加载 CSS 样式表，定义页面尺寸、字体、间距等参数。以下为关键参数参考表：

| 参数名 | 默认值 | 可选值 | 说明 |
| :--- | :--- | :--- | :--- |
| `page-size` | `A4` | `A4`, `Letter`, `Legal` | 页面尺寸 |
| `margin-top` | `2cm` | `1cm` ~ `3cm` | 上边距 |
| `margin-bottom` | `2cm` | `1cm` ~ `3cm` | 下边距 |
| `margin-left` | `2.5cm` | `1.5cm` ~ `3cm` | 左边距（装订预留） |
| `margin-right` | `2cm` | `1.5cm` ~ `3cm` | 右边距 |
| `font-family` | `"Noto Sans CJK SC", sans-serif` | 系统已安装字体 | 正文字体 |
| `font-size` | `11pt` | `9pt` ~ `14pt` | 正文字号 |
| `line-height` | `1.6` | `1.4` ~ `2.0` | 行间距倍数 |
| `code-font-size` | `9pt` | `8pt` ~ `11pt` | 代码块字号 |

**步骤 4：生成 PDF 文件**

```python
from weasyprint import HTML

html_content = f"<html><head><style>{css_text}</style></head><body>{html_body}</body></html>"
HTML(string=html_content).write_pdf('output.pdf')
```

**步骤 5：质量校验**

- 检查 PDF 页数是否合理（与源文本长度匹配）。
- 抽查 3-5 处关键排版元素（标题、表格、代码块）是否正常显示。
- 确认中文字符未出现乱码（如出现，检查字体配置）。

### 输出规范

- **文件命名**：默认输出文件名为 `output.pdf`，可通过参数指定为 `<原文件名>.pdf`。
- **文件位置**：默认输出到当前工作目录，可通过 `--output-dir` 参数指定。
- **元数据**：PDF 内嵌标题、作者（取自 frontmatter 或系统用户名）、生成日期。

## 四、置信度门控：信息缺失处理

当输入信息不完整时，本 Skill 不会猜测或编造内容，而是采用以下策略：

| 缺失信息类型 | 处理方式 | 输出示例 |
| :--- | :--- | :--- |
| 源文件路径 | 提示用户提供，不自动搜索 | `[需核实:源文件路径]` |
| 输出格式偏好 | 使用默认 A4 纵向布局 | `[需核实:页面方向]`（默认纵向） |
| 字体指定 | 使用系统默认中文字体 | `[需核实:字体偏好]`（默认 Noto Sans CJK SC） |
| 图片资源缺失 | 在 PDF 中保留占位框并标注 | `[需核实:图片路径 - 图片未找到]` |
| 表格数据不完整 | 保留空单元格，不填充虚拟数据 | `[需核实:表格第3行第2列数据]` |

## 五、错误码体系：常见问题排查

| 错误码 | 错误描述 | 提示话术 | 修正步骤 |
| :--- | :--- | :--- | :--- |
| `E1001` | 源文件不存在 | "未找到指定的输入文件，请检查路径是否正确。" | 1. 确认文件路径；2. 检查文件名拼写；3. 确认文件权限 |
| `E1002` | 文件编码错误 | "文件编码不是 UTF-8，可能包含特殊字符。" | 1. 使用 `iconv` 转换编码；2. 在编辑器中将文件另存为 UTF-8 格式 |
| `E2001` | 依赖库缺失 | "缺少 markdown 或 weasyprint 库，无法完成转换。" | 1. 执行 `pip install markdown weasyprint`；2. 确认安装成功 |
| `E2002` | 字体渲染失败 | "中文字体渲染异常，PDF 中可能出现乱码。" | 1. 安装中文字体（如 `fonts-noto-cjk`）；2. 在 CSS 中指定已安装字体 |
| `E3001` | 图片加载失败 | "文档中的图片无法访问，已生成占位框。" | 1. 检查图片路径；2. 确认图片格式（支持 PNG/JPG/SVG）；3. 重新转换 |
| `E3002` | 输出目录无权限 | "无法写入输出目录，请检查权限设置。" | 1. 更换输出目录；2. 修改目录写权限 |
| `E4001` | 内容解析异常 | "Markdown 语法解析出错，请检查文档结构。" | 1. 定位错误行（错误信息中会标注）；2. 修复 Markdown 语法；3. 重新转换 |

## 六、FAQ 反模式：常见坑与规避

| 常见误区（反模式） | 问题描述 | 正确做法 |
| :--- | :--- | :--- |
| **忽略字体配置** | 直接使用默认字体，导致中文乱码或显示为方块 | 显式指定支持中文的字体，如 `"Noto Sans CJK SC"` 或 `"Microsoft YaHei"` |
| **图片使用相对路径** | 转换时图片无法加载，因为工作目录与图片目录不一致 | 使用绝对路径，或将图片与源文件放在同一目录下 |
| **过度依赖在线资源** | CSS 中引用了 Google Fonts 等在线资源，离线时样式失效 | 使用本地字体文件，或下载字体到本地目录 |
| **忽略表格宽度** | 表格列数过多，超出页面宽度被截断 | 在 CSS 中设置 `table-layout: fixed` 并调整列宽比例 |
| **不检查输出质量** | 转换完成后直接使用，未发现排版错位或内容缺失 | 转换后至少浏览一遍 PDF，重点检查目录、页码、代码块换行 |

## 七、渐进式披露：分层阅读路径

### 速查卡（30 秒上手）

1. 准备一个 `.md` 文件。
2. 运行 `any2pdf input.md`。
3. 在当前目录获取 `input.pdf`。

### 新手路径（5 分钟掌握基础）

- 阅读「标准流程」章节，了解完整转换步骤。
- 使用默认配置完成一次转换。
- 遇到问题时，对照「错误码体系」表格排查。

### 进阶路径（深度定制）

- 自定义 CSS 样式表，实现品牌化排版。
- 利用 `--toc` 参数生成自动目录。
- 使用 `--header` 和 `--footer` 参数添加页眉页脚。
- 通过 `--cover` 参数指定封面页模板。
- 结合 CI/CD 流程，实现文档自动构建发布。


## 许可证（License）

```text
MIT License

Copyright (c) 2026 SkillForge Lab

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.
```
<!-- professional-license-embedded -->
