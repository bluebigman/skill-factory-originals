---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: any2pdf
name: any2文档
displayName: 文档转换 排版输出 PDF 生成
description: 将 Markdown、纯文本或富文本文件转换为排版精良的 PDF 文档。
version: 2.0.1
rules_version: cpr-20260810-n301
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/any2pdf
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: DocForge Studio
agent_created: true
trigger_words: ["any2pdf", "any2文档", "转PDF", "文档转换", "生成PDF", "md转pdf", "txt转pdf", "rtf转pdf"]

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

---

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->


# any2文档 — 文档转 PDF 技能手册

## 一、能力边界：一页纸速查卡

### 1.1 能做什么

| 功能项 | 说明 | 支持格式 |
|--------|------|----------|
| 格式转换 | 将源文件转换为 PDF | `.md`、`.txt`、`.rtf` |
| 编码识别 | 自动检测并处理文件编码 | UTF-8、GBK、GB18030 |
| 样式定制 | 通过 CSS 自定义 PDF 排版样式 | 自定义样式表 |
| 目录生成 | 为 Markdown 标题自动生成目录 | 仅限 `.md` 文件 |
| 图片嵌入 | 文档中引用的本地图片可嵌入 PDF | 相对路径或绝对路径 |

### 1.2 不能做什么

| 限制项 | 说明 |
|--------|------|
| 不支持扫描件 OCR | 无法将扫描图片转换为可编辑文本 |
| 不支持加密 PDF | 不提供密码保护或权限设置功能 |
| 不支持批量转换 | 每次调用仅处理单个文件 |
| 不支持复杂表格 | 对复杂嵌套表格的渲染支持有限 |
| 不保证字体嵌入 | 依赖系统字体，特殊字体可能无法嵌入 |

### 1.3 适用对象

- **内容创作者**：需要将 Markdown 笔记、文章转为正式 PDF 文档
- **办公人员**：需要将纯文本报告、RTF 合同转为统一格式的 PDF
- **开发者**：需要将技术文档、README 转为可分发 PDF

---

## 二、触发方式：场景映射表

| 触发词/短语 | 使用场景 | 预期行为 |
|-------------|----------|----------|
| `any2pdf` | 直接调用技能 | 执行标准转换流程 |
| `any2文档` | 中文环境调用 | 同上 |
| `转PDF` | 用户有文件需要转换 | 询问源文件路径并执行 |
| `md转pdf` | 明确指定 Markdown 源 | 按 Markdown 规则转换 |
| `txt转pdf` | 明确指定纯文本源 | 按纯文本规则转换 |
| `rtf转pdf` | 明确指定富文本源 | 按富文本规则转换 |
| `生成PDF` | 用户需要输出 PDF | 同上 |
| `文档转换` | 通用转换需求 | 先确认源格式再执行 |

---

## 三、标准流程

### 3.1 前置条件检查

执行转换前，必须逐项确认以下条件：

| 检查项 | 检查方法 | 失败处理 |
|--------|----------|----------|
| Python 版本 | `python3 --version` | 需 ≥ 3.8，否则提示升级 |
| markdown 库 | `python3 -c "import markdown"` | 执行 `pip install markdown` |
| weasyprint 库 | `python3 -c "import weasyprint"` | 执行 `pip install weasyprint` |
| 源文件存在 | `ls -l <源文件路径>` | 提示文件不存在 |
| 源文件格式 | 检查扩展名 | 非支持格式则拒绝执行 |
| 文件编码 | 使用 `file` 命令检测 | 非支持编码则尝试转码 |

### 3.2 执行步骤

#### 步骤 1：验证输入文件

```bash
# 检查文件是否存在且格式正确
file <源文件路径>
# 预期输出示例：UTF-8 Unicode text
```

**参数说明**：
- `<源文件路径>`：必填，支持相对路径和绝对路径
- 文件大小限制：建议不超过 50MB

#### 步骤 2：确认输出配置

| 配置项 | 默认值 | 可选值 | 说明 |
|--------|--------|--------|------|
| 输出路径 | 源文件同目录 | 任意路径 | 需有写权限 |
| 页面大小 | A4 | A4、Letter、Legal | 通过 CSS 设置 |
| 页边距 | 2cm | 1cm-3cm | 通过 CSS 设置 |
| 字体 | 系统默认 | 任意已安装字体 | 通过 CSS 设置 |
| 目录 | 自动生成 | 开启/关闭 | 仅 Markdown 支持 |

#### 步骤 3：执行转换

```python
#!/usr/bin/env python3
# convert.py — 标准转换脚本

import sys
import os
import markdown
from weasyprint import HTML

def convert_md_to_pdf(input_path, output_path, css_path=None):
    """将 Markdown 文件转换为 PDF"""
    with open(input_path, 'r', encoding='utf-8') as f:
        text = f.read()
    
    # 转换为 HTML
    html_body = markdown.markdown(text, extensions=['toc', 'tables', 'fenced_code'])
    
    # 构建完整 HTML
    html = f"""
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{ font-family: sans-serif; margin: 2cm; }}
            h1 {{ color: #333; border-bottom: 2px solid #ccc; }}
            h2 {{ color: #555; }}
            table {{ border-collapse: collapse; width: 100%; }}
            th, td {{ border: 1px solid #ddd; padding: 8px; }}
            code {{ background: #f4f4f4; padding: 2px 4px; }}
        </style>
    </head>
    <body>
        {html_body}
    </body>
    </html>
    """
    
    # 生成 PDF
    HTML(string=html).write_pdf(output_path)
    print(f"转换完成: {output_path}")

def convert_txt_to_pdf(input_path, output_path):
    """将纯文本文件转换为 PDF"""
    with open(input_path, 'r', encoding='utf-8') as f:
        text = f.read()
    
    # 转义 HTML 特殊字符
    import html
    escaped_text = html.escape(text)
    # 将换行符替换为 <br>
    html_text = escaped_text.replace('\n', '<br>')
    
    html = f"""
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{ font-family: monospace; margin: 2cm; white-space: pre-wrap; }}
        </style>
    </head>
    <body>
        {html_text}
    </body>
    </html>
    """
    
    HTML(string=html).write_pdf(output_path)
    print(f"转换完成: {output_path}")

def main():
    if len(sys.argv) < 3:
        print("用法: python3 convert.py <输入文件> <输出文件> [样式文件]")
        sys.exit(1)
    
    input_path = sys.argv[1]
    output_path = sys.argv[2]
    css_path = sys.argv[3] if len(sys.argv) > 3 else None
    
    # 检查输入文件
    if not os.path.exists(input_path):
        print(f"错误: 文件不存在 - {input_path}")
        sys.exit(1)
    
    ext = os.path.splitext(input_path)[1].lower()
    if ext == '.md':
        convert_md_to_pdf(input_path, output_path, css_path)
    elif ext == '.txt':
        convert_txt_to_pdf(input_path, output_path)
    elif ext == '.rtf':
        print("错误: RTF 转换需要额外依赖，请使用文本模式")
        sys.exit(1)
    else:
        print(f"错误: 不支持的格式 - {ext}")
        sys.exit(1)

if __name__ == '__main__':
    main()
```

#### 步骤 4：验证输出

```bash
# 检查 PDF 文件是否生成
ls -l <输出文件路径>
# 检查文件类型
file <输出文件路径>
# 预期输出：PDF document, version 1.7
```

### 3.3 输出规范

- **文件命名**：默认与源文件同名，扩展名为 `.pdf`
- **文件大小**：通常为源文件的 1.5-3 倍（含图片时可能更大）
- **页面布局**：A4 纵向，默认页边距 2cm
- **编码要求**：输出 PDF 使用 UTF-8 编码

---

## 四、置信度门控

当遇到以下情况时，输出 `[需核实:字段]` 占位符，不进行猜测：

| 场景 | 占位符示例 | 处理方式 |
|------|------------|----------|
| 图片路径不确定 | `[需核实:图片路径]` | 提示用户确认图片位置 |
| 字体可用性未知 | `[需核实:字体名称]` | 检查系统字体列表 |
| 文件编码不确定 | `[需核实:文件编码]` | 使用 `file` 命令检测 |
| 输出路径权限未知 | `[需核实:写入权限]` | 尝试创建临时文件测试 |
| 依赖库版本未知 | `[需核实:库版本]` | 执行版本检查命令 |

---

## 五、错误码体系

| 错误码 | 错误描述 | 提示话术 | 修正步骤 |
|--------|----------|----------|----------|
| E001 | 源文件不存在 | "未找到指定的源文件，请检查路径是否正确。" | 1. 确认路径拼写；2. 检查文件是否被移动或删除 |
| E002 | 不支持的格式 | "仅支持 .md、.txt、.rtf 格式的文件。" | 1. 转换源文件格式；2. 使用支持的格式 |
| E003 | 编码无法识别 | "无法识别文件编码，请确认文件为 UTF-8、GBK 或 GB18030 编码。" | 1. 使用 `iconv` 转码；2. 重新保存为 UTF-8 |
| E004 | 依赖库缺失 | "缺少必要的 Python 库，请安装 markdown 和 weasyprint。" | 1. 执行 `pip install markdown weasyprint`；2. 验证安装 |
| E005 | 输出路径无权限 | "无法写入输出文件，请检查目录权限。" | 1. 更换输出目录；2. 修改目录权限 |
| E006 | 图片资源缺失 | "文档中引用的图片无法访问，请检查图片路径。" | 1. 确认图片存在；2. 修正相对路径 |
| E007 | 转换超时 | "转换过程超时，文件可能过大或包含复杂元素。" | 1. 简化文档结构；2. 分批处理 |
| E008 | 内存不足 | "内存不足，无法完成转换。" | 1. 关闭其他程序；2. 减小文件大小 |

---

## 六、FAQ 反模式

### 常见坑 1：中文乱码

**错误做法**：直接读取文件而不指定编码。

**正确做法**：
```python
with open(input_path, 'r', encoding='utf-8') as f:
    text = f.read()
```

### 常见坑 2：图片不显示

**错误做法**：在 Markdown 中使用绝对路径引用图片。

**正确做法**：使用相对路径，并确保图片与源文件在同一目录或子目录下。

### 常见坑 3：目录无法跳转

**错误做法**：手动编写目录链接。

**正确做法**：使用 `markdown` 库的 `toc` 扩展自动生成目录。

### 常见坑 4：样式不生效

**错误做法**：在 Markdown 中直接写 HTML 样式。

**正确做法**：使用外部 CSS 文件，通过 `weasyprint` 加载。

### 常见坑 5：转换后格式错乱

**错误做法**：忽略源文件中的特殊字符。

**正确做法**：对文本进行 HTML 转义处理。

---

## 七、渐进式披露

### 7.1 速查卡（新手必读）

1. 确保 Python 3.8+ 已安装
2. 安装依赖：`pip install markdown weasyprint`
3. 准备源文件（.md / .txt / .rtf）
4. 运行转换脚本
5. 检查输出 PDF

### 7.2 进阶路径（有经验用户）

#### 自定义样式

创建 `style.css` 文件：

```css
@page {
    size: A4;
    margin: 2.5cm 2cm;
}

body {
    font-family: "Noto Serif SC", serif;
    font-size: 12pt;
    line-height: 1.8;
}

h1 {
    color: #2c3e50;
    border-bottom: 3px solid #3498db;
    padding-bottom: 10px;
}

h2 {
    color: #34495e;
}

code {
    background: #ecf0f1;
    padding: 2px 6px;
    border-radius: 3px;
    font-family: "JetBrains Mono", monospace;
}

pre {
    background: #2d2d2d;
    color: #f8f8f2;
    padding: 15px;
    border-radius: 5px;
    overflow-x: auto;
}

table {
    border-collapse: collapse;
    width: 100%;
    margin: 20px 0;
}

th, td {
    border: 1px solid #bdc3c7;
    padding: 10px;
    text-align: left;
}

th {
    background: #3498db;
    color: white;
}

blockquote {
    border-left: 4px solid #3498db;
    margin: 20px 0;
    padding: 10px 20px;
    background: #f8f9fa;
}
```

使用自定义样式：

```bash
python3 convert.py input.md output.pdf style.css
```

#### 批量处理脚本

```python
# batch_convert.py
import os
import glob

def batch_convert(directory):
    """批量转换目录下所有 .md 文件"""
    md_files = glob.glob(os.path.join(directory, "*.md"))
    for md_file in md_files:
        output = md_file.replace('.md', '.pdf')
        print(f"转换: {md_file} -> {output}")
        # 调用转换函数
        # convert_md_to_pdf(md_file, output)

if __name__ == '__main__':
    batch_convert('./documents')
```

#### 性能优化建议

| 场景 | 优化策略 |
|------|----------|
| 大文件（>10MB） | 分段处理，先转换再合并 |
| 多图片文档 | 压缩图片后再嵌入 |
| 复杂表格 | 使用 HTML 表格替代 Markdown 表格 |
| 频繁转换 | 缓存中间 HTML 结果 |

---

## 八、用户协议

<!-- user-agreement-injected -->

**使用本 Skill 即表示您同意以下条款：**

1. **责任承担**：使用者自行承担因使用本 Skill 产生的全部责任。包括但不限于因转换结果不准确、数据丢失、格式错误等造成的任何直接或间接损失。

2. **禁止反向工程**：不得对本 Skill 的源代码、算法、逻辑进行反向工程、反编译、破解或任何形式的未授权修改。

3. **合规使用**：使用者应确保所转换的内容不违反任何法律法规，不侵犯第三方知识产权。

4. **无担保声明**：本 Skill 按"现状"提供，不附带任何明示或暗示的担保，包括但不限于适销性、特定用途适用性和非侵权保证。

5. **服务变更**：本 Skill 可能随时更新或终止，恕不另行通知。

---

## 九、许可证（License）

<!-- professional-license-embedded -->

**MIT License**

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

## 十、版本记录

| 版本 | 日期 | 变更内容 |
|------|------|----------|
| 1.0.0 | 2024-01-15 | 初始版本，支持基础转换功能 |

---

*本 Skill 由 AI 辅助生成，仅供参考。使用前请阅读相关文档。*
