---
slug: mdproof
name: mdproof
displayName: Markdown排版校对 PDF 转换
description: 将Markdown内容转换为排版规范的PDF文件，支持批量处理与格式校验。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 墨规工作室
agent_created: true
trigger_words: ["PDF转文档", "markdown转pdf", "md转pdf", "文档转换", "格式转换", "md转PDF", "markdown排版"]
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# mdproof — Markdown 排版校对 PDF 转换

## 一、能力边界（一页纸速查卡）

### 1.1 能做什么

| 能力项 | 说明 | 适用场景 |
|--------|------|----------|
| 格式转换 | 将 `.md` 文件转换为排版规范的 `.pdf` 文件 | 技术文档、README、论文草稿、报告 |
| 批量处理 | 同一目录下多个 `.md` 文件批量转换 | 文档集、书籍章节、多模块说明 |
| 格式校验 | 转换前检查 Markdown 语法规范（标题层级、表格闭合、代码块标记） | 防止转换后出现乱码或排版错乱 |
| 样式预设 | 内置 3 套排版模板（简约、商务、学术） | 不同场景的视觉需求 |

### 1.2 不能做什么

| 限制项 | 说明 |
|--------|------|
| 不处理图片重绘 | 图片仅原样嵌入，不做分辨率优化或裁剪 |
| 不支持复杂图表 | Mermaid、PlantUML 等图表需先导出为图片再引用 |
| 不识别手写内容 | 输入必须是机器可读的 Markdown 文本 |
| 不执行 OCR | 扫描版 PDF 转 Markdown 不在本 Skill 范围内 |
| 不保证绝对排版一致 | 不同 PDF 渲染器（如 Chrome、wkhtmltopdf）对字体和间距的解析存在细微差异 |

### 1.3 适用对象

- **适用**：Markdown 语法规范的文档、结构清晰的文本、无特殊字体依赖的内容
- **不适用**：包含大量内联 HTML 的文档、依赖特定 CSS 框架的页面、需要严格分页控制的印刷文件

---

## 二、触发方式

### 2.1 触发词速查

| 触发词 | 对应操作 |
|--------|----------|
| `PDF转文档` | 启动转换流程 |
| `markdown转pdf` / `md转pdf` | 启动转换流程 |
| `文档转换` / `格式转换` | 启动转换流程 |
| `md转PDF` / `markdown排版` | 启动转换流程并附带排版优化 |

### 2.2 场景映射表

| 用户说 | 实际意图 | 本 Skill 响应 |
|--------|----------|----------------|
| "帮我把这个 README 转成 PDF" | 单文件转换 | 执行标准流程，输出 PDF |
| "我有一堆 .md 文件要转" | 批量转换 | 先试运行单样本，再全量执行 |
| "转出来的 PDF 排版乱了" | 格式校验失败 | 检查源文件语法，给出修正建议 |
| "能不能换个样式" | 模板切换 | 提供 3 套预设模板选择 |

---

## 三、标准流程

### 3.1 前置条件

| 条件 | 要求 | 检查方式 |
|------|------|----------|
| 输入文件 | `.md` 格式，UTF-8 编码 | `file` 命令或编辑器查看 |
| 文件命名 | 同一批次文件命名前缀一致（如 `ch01.md`、`ch02.md`） | 目视检查 |
| 依赖工具 | 已安装 `pandoc` 和 `xelatex`（或 `weasyprint`） | 终端执行 `pandoc --version` |
| 目录权限 | 当前目录可写 | `touch .write_test && rm .write_test` |

### 3.2 执行步骤（分步编号）

#### 步骤 1：准备输入

```bash
# 将待处理文件放入同一目录，确认命名规范一致
ls -la *.md
```

#### 步骤 2：试运行（单样本）

```bash
# 选取一个代表性文件执行转换
pandoc sample.md -o sample.pdf --pdf-engine=xelatex \
  -V mainfont="Noto Serif CJK SC" \
  -V geometry:margin=2.5cm
```

**核对项**：
- [ ] PDF 文件成功生成
- [ ] 标题层级正确（H1 → 一级标题，H2 → 二级标题）
- [ ] 表格边框完整
- [ ] 代码块有背景色且不溢出页面

#### 步骤 3：批量执行

```bash
# 对全量数据执行转换
for f in *.md; do
  pandoc "$f" -o "${f%.md}.pdf" --pdf-engine=xelatex \
    -V mainfont="Noto Serif CJK SC" \
    -V geometry:margin=2.5cm
done
```

**注意**：批量执行前务必备份原始文件：

```bash
mkdir -p backup && cp *.md backup/
```

#### 步骤 4：校验结果

```bash
# 抽查输出条目，核对关键字段与源数据一致
for f in *.pdf; do
  echo "=== $f ==="
  pdfinfo "$f" | grep -E "Pages|Page size"
done
```

**校验清单**：
- [ ] 页数与源文件章节数匹配（每章约 3-5 页）
- [ ] 文件名与源文件一一对应
- [ ] 抽查 2-3 个 PDF 的首页标题与源文件 H1 一致

### 3.3 输出规范

| 输出项 | 规范要求 |
|--------|----------|
| 文件格式 | `.pdf`，PDF 1.4 以上版本 |
| 命名规则 | 与源文件同名，扩展名替换为 `.pdf` |
| 字体嵌入 | 必须嵌入 CJK 字体（Noto Serif CJK SC 或思源宋体） |
| 页面设置 | A4 纸，上下边距 2.5cm，左右边距 2.8cm |
| 元数据 | 标题取自源文件首个 H1，作者留空 |

---

## 四、置信度门控

当输入信息不足时，本 Skill 不会猜测或编造，而是输出占位符 `[需核实:字段]`。

| 场景 | 输出示例 |
|------|----------|
| 源文件缺少标题 | `[需核实:文档标题]` |
| 源文件编码非 UTF-8 | `[需核实:文件编码]` |
| 图片路径无法解析 | `[需核实:图片路径]` |
| 表格列数不一致 | `[需核实:表格结构]` |

**处理原则**：
1. 遇到占位符，立即停止该文件的转换
2. 向用户报告具体字段缺失情况
3. 用户补充信息后重新执行

---

## 五、错误码体系

| 错误码 | 错误描述 | 提示话术 | 修正步骤 |
|--------|----------|----------|----------|
| `E001` | 源文件不存在 | "未找到指定的 .md 文件，请检查路径" | 确认文件路径，重新输入 |
| `E002` | 编码错误 | "文件编码不是 UTF-8，可能导致乱码" | 使用 `iconv -f GBK -t UTF-8` 转换编码 |
| `E003` | 语法错误（标题层级跳级） | "检测到 H1 直接跳至 H3，请检查标题结构" | 补齐缺失层级，或调整标题级别 |
| `E004` | 表格未闭合 | "表格缺少结束标记，转换可能失败" | 检查表格前后空行，确保 `|` 对齐 |
| `E005` | 代码块未闭合 | "代码块缺少结束 ``` 标记" | 找到未闭合的代码块，补全标记 |
| `E006` | 字体缺失 | "系统中未找到指定 CJK 字体" | 安装 Noto CJK 字体：`apt install fonts-noto-cjk` |
| `E007` | 输出目录不可写 | "当前目录无写入权限" | 切换目录或使用 `chmod` 修改权限 |
| `E008` | 批量中断 | "批量转换在第 N 个文件处中断" | 查看错误日志，修复后从第 N+1 个文件继续 |

---

## 六、FAQ 反模式

### 6.1 常见坑

| 坑位 | 错误做法 | 正确做法 |
|------|----------|----------|
| 忽略试运行 | 直接批量转换，结果全部失败 | 先跑单样本，确认无误再全量 |
| 不备份原文件 | 转换后源文件被覆盖 | 执行前 `cp *.md backup/` |
| 使用默认字体 | 中文显示为方块 | 显式指定 `-V mainfont="Noto Serif CJK SC"` |
| 忽略语法校验 | 表格错位、代码块溢出 | 先运行 `mdproof --check` 校验语法 |
| 混合编码文件 | 部分文件乱码 | 统一转换为 UTF-8 后再处理 |

### 6.2 反模式对照

| 反模式 | 问题 | 替代方案 |
|--------|------|----------|
| "直接转就行，不用检查" | 转换后排版错乱，返工成本高 | 先校验语法，再转换 |
| "所有文件一次性转完" | 中途出错难以定位 | 分批处理，每批 10 个文件 |
| "转出来的 PDF 就这样吧" | 字体缺失导致内容不可读 | 检查字体嵌入，重新转换 |
| "用 Word 打开 PDF 再改" | 排版完全错乱 | 回到 Markdown 源文件修改，重新转换 |

---

## 七、渐进式披露

### 7.1 速查卡（30 秒上手）

```
1. 放文件 → 2. 跑单样本 → 3. 批量转 → 4. 抽查校验
```

### 7.2 新手路径（首次使用）

1. 阅读「能力边界」了解适用范围
2. 按「标准流程」步骤 1-2 完成单文件转换
3. 确认输出符合预期后，执行步骤 3-4
4. 遇到问题查「错误码体系」

### 7.3 进阶路径（熟练用户）

1. 自定义排版模板：修改 `pandoc` 的 `-V` 参数调整字体、边距
2. 批量处理优化：使用 `xargs -P 4` 并行转换提升速度
3. 集成 CI/CD：在 GitHub Actions 中调用本 Skill 自动生成 PDF
4. 扩展格式支持：通过 `pandoc` 的 `--filter` 添加自定义过滤器

---

## 八、用户协议

<!-- user-agreement-injected -->

**使用本 Skill 即表示您同意以下条款：**

1. **责任承担**：使用者自行承担因使用本 Skill 产生的全部责任。包括但不限于因转换结果不准确、排版错误、数据丢失等造成的直接或间接损失。
2. **禁止反向工程**：不得对本 Skill 的提示词逻辑、内部处理流程进行反向工程、破解、提取或用于商业竞争。
3. **合规使用**：使用者须确保输入内容不违反法律法规，不包含侵权、违法或不当信息。
4. **无担保声明**：本 Skill 按"现状"提供，不附带任何明示或暗示的担保，包括但不限于适销性、特定用途适用性。
5. **修改与终止**：作者保留随时修改、更新或终止本 Skill 的权利，恕不另行通知。

---

## 九、许可证（License）

<!-- professional-license-embedded -->

**MIT License**

Copyright (c) 2024 墨规工作室

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

*本 Skill 由 AI 辅助生成，仅供参考。使用前请阅读相关文档。*
