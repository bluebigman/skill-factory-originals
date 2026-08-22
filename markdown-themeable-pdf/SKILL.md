---
slug: markdown-themeable-pdf
name: markdown-themeable-pdf
displayName: PDF识别 文字提取 主题化转换
description: 将PDF内容识别提取为结构化Markdown，支持主题化定制输出。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: SkillForge Studio
agent_created: true
trigger_words: ["PDF识别", "文字提取", "markdown themeable pdf", "PDF转Markdown", "主题化PDF处理"]
---

> 本内容由 AI 生成，仅供学习参考 <!-- ai-generated-notice -->

# Markdown Themeable PDF 技能文档

## 一、能力边界速查卡

### 1.1 能做与不能做

| 维度 | 能做 | 不能做 |
|------|------|--------|
| 输入 | 用户提供的PDF文件、文本数据、可访问URL | 加密PDF、扫描图片型PDF（无OCR能力） |
| 处理 | 提取文字内容、识别标题层级、保留表格结构 | 还原复杂排版（如多栏混排）、识别手写内容 |
| 输出 | 结构化Markdown、自定义主题样式、批量生成 | 生成PDF文件、执行格式转换以外的操作 |
| 扩展 | 支持自定义字段映射、输出模板定制 | 跨语言翻译、语义理解与摘要生成 |

### 1.2 适用对象

- 需要将PDF文档内容快速转为Markdown格式的开发者
- 需要统一文档风格、批量处理PDF资料的内容运营人员
- 需要从PDF中提取结构化数据用于后续处理的自动化流程设计者

---

## 二、触发方式与场景映射

| 触发词/场景 | 用户意图 | 技能响应 |
|-------------|----------|----------|
| "PDF识别" | 用户想从PDF中提取文字 | 启动文字提取流程，输出Markdown |
| "文字提取" | 用户需要纯文本内容 | 提取并清理格式，输出纯Markdown |
| "markdown themeable pdf" | 用户需要主题化PDF转Markdown | 应用默认主题模板，生成带样式的Markdown |
| "PDF转Markdown" | 用户需要格式转换 | 执行完整转换流程，输出结构化结果 |
| "批量处理PDF" | 用户有多份PDF需处理 | 进入批量模式，按目录规则处理 |

---

## 三、标准处理流程

### 3.1 前置条件

| 条件项 | 要求 | 检查方式 |
|--------|------|----------|
| 输入文件 | PDF格式，未加密，文字型（非纯扫描） | 文件头检查 `%PDF`，尝试读取文本层 |
| 文件命名 | 建议 `源文件名_日期.pdf` 格式 | 目视检查 |
| 输出目录 | 与输入同目录，或指定输出路径 | 确认可写权限 |
| 依赖环境 | Python 3.8+，安装 `pypdf`、`markdown` 库 | `pip list` 检查 |

### 3.2 执行步骤

**第一步：输入验证**

```bash
# 检查文件是否为有效PDF
file document.pdf
# 输出应包含 "PDF document" 字样
```

**第二步：文字提取**

```python
from pypdf import PdfReader

reader = PdfReader("document.pdf")
text_content = []
for page in reader.pages:
    text_content.append(page.extract_text())
full_text = "\n\n".join(text_content)
```

**第三步：结构识别**

- 根据字体大小、缩进、编号模式识别标题层级
- 表格数据按行列关系保留为Markdown表格
- 列表项识别 `-`、`*`、数字编号

**第四步：主题应用**

| 主题名称 | 样式特征 | 适用场景 |
|----------|----------|----------|
| `default` | 标准标题层级，代码块灰底 | 通用文档 |
| `compact` | 减少间距，紧凑排版 | 代码文档、API说明 |
| `readable` | 加大行距，强调标题 | 长文阅读、教程 |

**第五步：输出生成**

```bash
# 输出文件命名规则
# 输入: document.pdf → 输出: document.md
```

### 3.3 输出规范

```markdown
---
source: document.pdf
processed_at: 2024-01-15T10:30:00Z
confidence: 0.95
---

# 文档标题

正文内容...
```

---

## 四、置信度门控机制

### 4.1 置信度标注规则

| 置信度范围 | 标注方式 | 说明 |
|------------|----------|------|
| 0.90 - 1.00 | 无特殊标注 | 提取结果可靠 |
| 0.70 - 0.89 | `> 部分内容可能不完整` | 有少量字符识别异常 |
| 0.50 - 0.69 | `> 内容缺失较多，建议人工核对` | 存在段落遗漏 |
| < 0.50 | `[需核实:全部内容]` | 提取失败或严重异常 |

### 4.2 信息不足处理

当遇到以下情况时，使用占位符而非编造内容：

- 表格单元格为空 → `[需核实:单元格内容]`
- 图片无法识别 → `[需核实:图片描述]`
- 页眉页脚混入 → 自动过滤，若无法过滤则标注 `[需核实:页眉内容]`

---

## 五、错误码体系

| 错误码 | 错误描述 | 提示话术 | 修正步骤 |
|--------|----------|----------|----------|
| `E001` | 文件不存在 | "未找到指定文件，请检查路径" | 确认路径正确，重新输入 |
| `E002` | 文件加密 | "该PDF已加密，无法提取内容" | 提供密码或使用解密工具 |
| `E003` | 无文本层 | "该PDF为扫描件，无文字信息" | 使用OCR工具预处理 |
| `E004` | 提取内容为空 | "提取结果为空，请检查源文件" | 验证PDF内容，尝试其他工具 |
| `E005` | 输出目录不可写 | "无法写入输出文件，请检查权限" | 更换目录或修改权限 |
| `E006` | 批量处理中断 | "批量处理在第N个文件中断" | 查看错误日志，修复后重试 |

---

## 六、FAQ 反模式对照

### 6.1 常见坑与正确做法

| 常见错误（反模式） | 问题说明 | 正确做法 |
|---------------------|----------|----------|
| 直接处理扫描PDF | 提取结果为空或乱码 | 先确认PDF类型，扫描件走OCR流程 |
| 忽略表格结构 | 表格数据混为纯文本 | 使用表格识别模式，保留行列关系 |
| 不检查置信度 | 低质量提取结果直接使用 | 查看置信度标注，低置信度内容人工复核 |
| 批量处理不备份 | 源文件损坏无法恢复 | 处理前复制原始文件到备份目录 |
| 自定义主题不测试 | 样式异常影响阅读 | 先用单文件试运行，确认效果再批量 |

### 6.2 反模式示例

**反模式：** 直接对扫描版PDF执行提取，得到大量乱码字符。

**正确流程：**
1. 使用 `file` 命令确认PDF类型
2. 检测到无文本层时，提示用户使用OCR工具
3. 或自动切换到OCR模式（需安装 `tesseract`）

---

## 七、渐进式披露路径

### 7.1 新手快速上手（5分钟）

1. 将PDF文件放入工作目录
2. 运行 `python skill_runner.py --input document.pdf`
3. 查看生成的 `document.md` 文件
4. 检查置信度标注，确认提取质量

### 7.2 进阶用户定制（15分钟）

1. 创建自定义主题文件 `my_theme.json`
2. 配置标题样式、代码块格式、表格边框
3. 使用 `--theme my_theme` 参数应用
4. 批量处理：`python skill_runner.py --batch ./pdfs/ --theme my_theme`

### 7.3 高级开发者扩展（30分钟）

1. 修改 `extractor.py` 中的结构识别逻辑
2. 添加自定义输出模板（Jinja2格式）
3. 集成到CI/CD流水线，实现自动化文档处理
4. 编写单元测试，确保提取稳定性

---

## 八、参数配置参考

| 参数名 | 类型 | 默认值 | 取值范围 | 说明 |
|--------|------|--------|----------|------|
| `--input` | string | 无 | 文件路径 | 输入PDF文件 |
| `--output` | string | 同目录 | 目录路径 | 输出目录 |
| `--theme` | string | `default` | `default`/`compact`/`readable` | 主题样式 |
| `--batch` | string | 无 | 目录路径 | 批量处理目录 |
| `--confidence-threshold` | float | `0.7` | `0.0` - `1.0` | 置信度阈值 |
| `--preserve-tables` | bool | `true` | `true`/`false` | 保留表格结构 |
| `--verbose` | bool | `false` | `true`/`false` | 输出详细日志 |

---

## 九、用户协议

使用本技能即表示您同意以下条款：

1. **责任承担**：使用者自行承担使用本技能产生的全部责任。本技能提供的处理结果仅供参考，不构成任何形式的保证或承诺。
2. **禁止反向工程**：不得对本技能进行反向工程、反编译、破解或试图提取源代码（除非适用法律允许）。
3. **合规使用**：使用者应确保使用本技能处理的内容符合相关法律法规，不侵犯第三方权益。
4. **免责声明**：本技能按"原样"提供，不附带任何明示或暗示的保证，包括但不限于适销性、特定用途适用性和非侵权保证。

<!-- user-agreement-injected -->

---

## 十、许可证（License）

### MIT License

```
MIT License

Copyright (c) 2024 SkillForge Studio

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

---

*本 Skill 由 AI 辅助生成，仅供参考。使用前请阅读相关文档并自行验证适用性。*
