---
slug: competitor-analysis
name: competitor-analysis
displayName: 竞品透视 多维对标 差异洞察
description: 输入竞品资料，输出功能、定价、评价多维对比与差异化建议报告
version: 2.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: LinguaForge Studio
agent_created: true
trigger_words: ["competitor-analysis", "竞品分析", "竞品对比", "市场对标", "差异化分析", "竞品调研", "对标分析", "竞争格局"]
---

# 竞品透视 · 多维对标与差异洞察

**将零散的竞品资料（文档、表格、网页摘录）转化为结构化的多维对比报告，并给出可执行的差异化建议。** 面向产品经理、市场分析师、创业者与投研人员，解决"资料一堆、结论没有"的痛点。

## 快速开始 Quick Start

| 场景 | 操作 | 预期结果 |
|------|------|----------|
| 快速分析 | `python run.py --input data.csv --format csv` | 生成 `report.md` 与 `comparison_matrix.csv` |
| 预览不落盘 | `python run.py --input data.json --format json --dry-run` | 控制台打印报告摘要，不写任何文件 |
| 自检 | `python run.py --selftest` | 退出码 0，输出 `[SELFTEST] PASS` |

## 适用场景 When to Use

**推荐使用：**
- 手头有 2 家以上竞品的功能清单、定价表或用户评价文本
- 需要快速梳理竞争格局，输出结构化对比文档
- 需要从用户评价中提取情感倾向（正面/负面/中性）
- 需要识别竞品间的差异化机会点

**不建议使用：**
- 需要一手调研数据（用户访谈、实地考察）的深度分析
- 需要法律意见或财务审计的正式报告
- 输入资料不足（少于 2 家竞品）或信息严重缺失

## 能力总览 Capabilities

| 能力 | 命令/参数 | 示例 |
|------|-----------|------|
| 多格式输入解析 | `--input` + `--format` | `--input data.csv --format csv` |
| 功能清单对比 | 自动提取功能列 | 输入含"功能"列，输出功能对比矩阵 |
| 定价档位归类 | 自动识别价格列 | 输入含"价格"列，输出价格对比 |
| 用户评价情感分析 | 自动识别评价列 | 输入含"评价"列，输出情感倾向统计 |
| 差异化建议生成 | 自动基于对比结果 | 输出报告中含"差异化建议"章节 |
| 多格式输出 | `--output-format` | `--output-format md` 或 `--output-format json` |
| 预览模式 | `--dry-run` | 只打印不写盘 |
| 详细日志 | `--verbose` | 输出处理过程明细 |
| 自检 | `--selftest` | 验证核心功能 |

## 模块决策表 Decision Table

| 用户意图 | 模块/命令 | 读取指引 |
|----------|-----------|----------|
| 我有 CSV 文件要分析 | `--format csv` | 见"示例 Examples"第 1 条 |
| 我有 JSON 数据 | `--format json` | 见"示例 Examples"第 2 条 |
| 我有 Markdown 表格 | `--format md` | 见"示例 Examples"第 3 条 |
| 我想先预览结果 | `--dry-run` | 见"示例 Examples"第 1 条 |
| 我想看处理细节 | `--verbose` | 见"示例 Examples"第 2 条 |
| 我想验证工具是否正常 | `--selftest` | 见"快速开始"第 3 条 |

## 示例 Examples

### 示例 1：CSV 文件分析（含预览）

```bash
python run.py --input competitors.csv --format csv --dry-run
```

**输入 `competitors.csv`：**
```csv
名称,功能,价格,评价
竞品A,实时协作;文件分享;版本历史,免费;专业版99元/月,用户反馈积极;界面友好
竞品B,实时协作;文件分享,免费;团队版199元/月,功能强大但学习曲线陡峭
竞品C,实时协作;文件分享;版本历史;API接口,免费;企业版399元/月,功能全面;支持好
```

**预期输出（控制台摘要）：**
```text
[DRY-RUN] 将写入: report.md
[DRY-RUN] 将写入: comparison_matrix.csv
分析完成: 3 家竞品, 4 个功能点, 3 个价格档位
```

### 示例 2：JSON 数据详细分析

```bash
python run.py --input data.json --format json --verbose
```

**输入 `data.json`：**
```json
[
  {"name": "竞品A", "features": ["实时协作", "文件分享"], "price": "免费", "reviews": ["很好用", "界面漂亮"]},
  {"name": "竞品B", "features": ["实时协作"], "price": "99元/月", "reviews": ["功能少", "价格贵"]}
]
```

**预期输出：**
- `report.md`：包含功能对比矩阵、价格对比、情感分析、差异化建议
- `comparison_matrix.csv`：结构化对比数据
- 控制台输出处理明细（`--verbose`）

### 示例 3：Markdown 表格分析

```bash
python run.py --input table.md --format md
```

**输入 `table.md`：**
```markdown
| 名称 | 功能 | 价格 | 评价 |
|------|------|------|------|
| 竞品A | 实时协作;文件分享 | 免费 | 用户反馈积极 |
| 竞品B | 实时协作 | 99元/月 | 功能强大 |
```

**预期输出：** 与示例 1 类似的报告，但输入为 Markdown 格式。

## 安装与配置 Installation

### 环境要求
- Python 3.9+
- 可选依赖：`openpyxl`（Excel 支持）、`chardet`（编码检测）

### 安装依赖

```bash
pip install openpyxl chardet
```

### 文件格式支持

| 格式 | 扩展名 | 说明 |
|------|--------|------|
| CSV | `.csv` | 逗号分隔，支持 UTF-8/GBK 编码 |
| JSON | `.json` | 数组或对象格式 |
| Markdown | `.md` / `.markdown` | 表格格式 |
| Excel | `.xlsx` | 需安装 `openpyxl` |
| 纯文本 | `.txt` | 每行一条记录，用 `|` 分隔字段 |

## 常见问题 Troubleshooting

### 1. 文件编码错误（乱码或解析失败）

**现象：** 读取 CSV 时出现乱码或 `UnicodeDecodeError`。

**原因：** 文件编码不是 UTF-8（常见于 GBK 编码的中文文件）。

**解决：** 工具自动尝试 UTF-8 → GBK → GB18030 三级回退。若仍失败，请手动转换为 UTF-8 编码。

### 2. 输入文件超过大小限制

**现象：** 提示 `文件大小超过限制 (10MB)`。

**原因：** 文件超过 10MB 上限。

**解决：** 拆分文件或使用流式处理（工具已内置流式读取，但单文件仍有限制）。

### 3. 缺少可选依赖

**现象：** 读取 `.xlsx` 文件时提示 `openpyxl 未安装`。

**原因：** 未安装 `openpyxl`。

**解决：** 执行 `pip install openpyxl` 后重试。

### 4. 输出文件无法写入

**现象：** 提示 `写入失败`。

**原因：** 目标目录无写权限或磁盘已满。

**解决：** 检查目录权限，或使用 `--output-dir` 指定其他目录。

## 最佳实践 Best Practices

### 输入数据准备
- **功能列**：使用分号 `;` 或 `|` 分隔多个功能
- **价格列**：建议格式 `免费;专业版99元/月`，工具会自动识别档位
- **评价列**：每条评价用分号 `;` 分隔，工具会逐条分析情感

### 输出解读
- **功能对比矩阵**：行 = 功能点，列 = 竞品，值 = 支持/不支持
- **情感分析**：基于关键词匹配（正面/负面/中性），非深度学习模型
- **差异化建议**：基于功能覆盖差异自动生成，需人工复核

### 安全提醒
- 输入文件中的敏感信息（如 API key）不会写入报告
- 工具不会访问外部网络，所有分析均在本地完成
- 请勿将机密数据用于公开分享

## 相关资源 Related

- [GitHub 仓库](https://github.com/your-repo/competitor-analysis)（示例）
- [Markdown 表格语法](https://www.markdownguide.org/extended-syntax/#tables)
- [CSV 格式规范](https://tools.ietf.org/html/rfc4180)

---

## 许可证（License）

```text
MIT License

Copyright (c) 2026 LinguaForge Studio

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

---

## 失败处理与错误码

| 错误码 | 含义 | 处理方式 |
|--------|------|----------|
| 0 | 成功 | - |
| 1 | 参数错误 | 检查命令行参数 |
| 2 | 文件不存在 | 检查输入路径 |
| 3 | 文件格式不支持 | 检查 `--format` 参数 |
| 4 | 文件大小超限 | 拆分文件 |
| 5 | 解析失败 | 检查文件内容格式 |
| 6 | 写入失败 | 检查目录权限 |
| 7 | 自检失败 | 查看错误详情 |

---

## 用户协议（User Agreement）

1. 本 Skill 仅供学习与参考用途。使用本 Skill 产生的任何结果，由使用者自行承担全部责任；本 Skill 不提供任何明示或暗示的保证。
2. 涉及法律、财务、税务、投资、医疗等专业决策时，请务必咨询持证专业人士。
3. 本代码受版权法保护，未经授权复制、反向工程或商业利用将被追究法律责任。

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。

> 本内容由 AI 生成，仅供学习参考