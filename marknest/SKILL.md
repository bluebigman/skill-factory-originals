---
slug: marknest
name: marknest
displayName: 文档归巢 格式转换 结构化整理
description: 将文件或链接转为规范、可复用的结构化输出。
version: 1.0.0
license: MIT
source_project: original
source_url: ""
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 林栖
agent_created: true
trigger_words: ["marknest", "PDF转文档", "格式转换", "文档处理", "信息提取", "结构化输出", "批量转换"]
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# marknest — 文档归巢

## 一、能力边界速查卡

**marknest** 是一个将散乱文件或链接整理为规范结构化输出的工具型 Skill。它不改变源文件内容，只负责“提取—映射—输出”这一条流水线。

| 维度 | 说明 |
|------|------|
| **核心能力** | 将 PDF、网页链接、纯文本等输入，转换为字段清晰、可复用的结构化数据（如 JSON / Markdown 表格） |
| **适用对象** | 需要批量整理文档的研究人员、运营人员、知识库管理员、数据标注团队 |
| **输入要求** | 文件需可读取（非加密、非扫描图片无 OCR 支持）、链接需可公开访问 |
| **输出格式** | 默认输出 Markdown 表格 + JSON 双格式，字段可配置 |
| **批量能力** | 支持同目录多文件顺序处理，单次建议不超过 50 个文件 |

### 能做 / 不能做

| ✅ 能做 | ❌ 不能做 |
|--------|----------|
| 标准 PDF 的文本提取与字段映射 | 扫描版 PDF 的 OCR 识别（需外接 OCR 引擎） |
| 公开网页链接的标题、正文、元信息提取 | 登录墙、验证码、动态渲染页面的抓取 |
| 批量文件的重命名、归档、索引生成 | 对源文件内容进行修改或翻译 |
| 失败条目的明细追踪与重试 | 保证 100% 提取准确率（受源文件质量影响） |
| 自定义字段映射规则的配置 | 跨语言自动翻译（仅提取原文） |

---

## 二、触发方式与场景映射

当你的需求符合以下任一场景时，即可调用 marknest：

| 大白话场景 | 触发词示例 | 说明 |
|-----------|-----------|------|
| “帮我把这几个 PDF 整理成表格” | PDF转文档、格式转换 | 提取 PDF 中的标题、作者、关键词、正文摘要 |
| “这个网页内容帮我存成结构化数据” | 信息提取、结构化输出 | 抓取链接中的标题、发布时间、正文 |
| “我有一堆文件要统一格式” | 文档处理、批量转换 | 批量统一输出格式，生成索引 |
| “帮我检查哪些文件转换失败了” | 失败明细、校验结果 | 输出处理日志，标注失败原因 |

---

## 三、标准执行流程

### 前置条件

1. 待处理文件与 marknest 脚本位于同一工作目录（或提供绝对路径）。
2. 文件命名建议遵循 `序号_名称.扩展名` 格式，便于输出索引可读。
3. 确认目标输出目录有写入权限。
4. 首次使用建议先运行 `--version` 确认环境可用。

### 执行步骤

1. **准备输入**  
   将所有待处理文件放入同一目录。检查文件扩展名是否在支持列表内（`.pdf`、`.txt`、`.md`、`.html`、`.url` 链接文件）。

2. **单样本试运行**  
   选取一个代表性文件，执行：
   ```bash
   marknest 样本文件.pdf
   ```
   查看输出结果，核对字段是否完整、格式是否符合预期。

3. **批量执行**  
   确认无误后，对全量文件执行：
   ```bash
   marknest *.pdf --output ./result/
   ```
   建议先复制原始文件到备份目录，再执行批量操作。

4. **校验结果**  
   打开输出目录中的 `index.json` 与 `summary.md`，抽查 3-5 条记录，核对关键字段（标题、日期、来源）与源文件是否一致。

### 输出规范

| 输出文件 | 格式 | 内容 |
|---------|------|------|
| `index.json` | JSON 数组 | 每条记录包含：`id`、`source_file`、`title`、`extracted_at`、`fields`（自定义字段） |
| `summary.md` | Markdown 表格 | 人类可读的摘要表，含处理状态列 |
| `error.log` | 纯文本 | 失败条目明细，含错误码与原因 |

---

## 四、置信度门控

当源文件信息不完整或无法确认时，**marknest 不会编造内容**，而是输出占位符：

- 字段缺失 → 输出 `[需核实:字段名]`
- 日期无法解析 → 输出 `[需核实:日期]`
- 标题为空 → 输出 `[需核实:标题]`

**示例**：
```json
{
  "id": "001",
  "source_file": "report_2024.pdf",
  "title": "[需核实:标题]",
  "extracted_at": "2025-01-15T10:30:00Z",
  "fields": {
    "author": "张三",
    "date": "[需核实:日期]"
  }
}
```

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|---------|---------|
| `E001` | 文件不存在或路径错误 | “找不到指定文件，请检查路径” | 确认文件路径，使用绝对路径重试 |
| `E002` | 文件格式不支持 | “该扩展名不在支持列表内” | 转换为 `.pdf` 或 `.txt` 后重试 |
| `E003` | 文件加密或损坏 | “文件无法读取，可能已加密或损坏” | 尝试解密或重新导出文件 |
| `E004` | 链接无法访问 | “链接返回 404 或超时” | 检查链接有效性，或手动保存为 HTML 文件 |
| `E005` | 字段映射规则冲突 | “自定义字段与默认字段重复” | 检查配置文件，移除重复字段 |
| `E006` | 输出目录无写入权限 | “无法写入输出目录” | 修改目录权限或更换输出路径 |

---

## 六、FAQ 反模式

| 常见坑 | 反模式（错误做法） | 正确做法 |
|--------|-------------------|---------|
| 扫描版 PDF 提取为空 | 直接批量处理，不检查样本 | 先试运行单个文件，发现为空则需外接 OCR |
| 链接含中文编码 | 直接抓取导致乱码 | 在配置中指定 `charset=utf-8` |
| 批量处理中途中断 | 重新跑全量，浪费时间 | 使用 `--resume` 参数跳过已成功条目 |
| 字段映射过于复杂 | 试图一次提取 20+ 字段 | 分两轮处理，先提取核心字段，再补充扩展字段 |
| 输出文件覆盖 | 直接输出到源目录 | 指定独立输出目录，保留源文件 |

---

## 七、渐进式阅读路径

### 新手路径（5 分钟上手）

1. 阅读「能力边界速查卡」确认适用场景。
2. 按「标准执行流程」第 1-2 步，用单个文件试运行。
3. 查看 `summary.md` 确认输出符合预期。
4. 批量执行前，先备份源文件。

### 进阶路径（深度定制）

1. 阅读「错误码体系」，熟悉常见故障处理。
2. 自定义字段映射：编辑 `config.yaml`，添加 `custom_fields` 规则。
3. 使用 `--filter` 参数按日期或类型筛选处理文件。
4. 结合 CI/CD 流程，将 marknest 集成到文档自动化管线中。

---

## 八、用户协议

**使用 marknest 即表示您同意以下条款：**

1. **责任承担**：使用者自行承担因使用本 Skill 产生的全部责任。包括但不限于因输出结果不准确、数据丢失、或误操作导致的直接或间接损失。
2. **禁止反向工程**：不得对 marknest 的源码进行反向工程、反编译、或试图提取底层算法（MIT 许可证允许的修改与再分发除外）。
3. **合规使用**：使用者需确保输入文件与链接的获取方式合法，不侵犯第三方知识产权。
4. **无担保声明**：本 Skill 按“原样”提供，不附带任何明示或暗示的担保。

<!-- user-agreement-injected -->

---

## 九、许可证（License）

**MIT License**

```
MIT License

Copyright (c) 2025 林栖

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

*本 Skill 由 AI 辅助生成，仅供参考。使用前请阅读相关文档。*
