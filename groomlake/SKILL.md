---
slug: groomlake
name: groomlake
displayName: Adobe文档解析 结构提取 元数据读取
description: 解析Adobe系列文档，提取文本、元数据与结构信息的专业工具。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 湖心工作室
agent_created: true
trigger_words: ["groomlake", "adobe解析", "pdf提取", "文档结构分析", "元数据读取", "PDF解析", "文档信息抽取"]
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# groomlake — Adobe 文档解析与结构提取工具

本 Skill 由 AI 辅助生成，仅供参考。使用前请阅读相关文档，并根据实际场景验证输出结果。

---

## 一、能力边界（一页纸速查卡）

### 1.1 工具能做什么

| 能力项 | 说明 |
|--------|------|
| 文本提取 | 从 Adobe PDF 中抽取正文文本内容，保留段落顺序 |
| 元数据读取 | 获取文档标题、作者、创建时间、修改时间、PDF 版本等属性 |
| 结构分析 | 识别文档的章节层级、标题树、页面布局框架 |
| 批量处理 | 支持对多个文件依次执行解析，输出结构化结果 |
| 调试模式 | 通过 `--verbose` 输出详细处理日志，便于排查复杂文件 |

### 1.2 工具不能做什么

| 限制项 | 说明 |
|--------|------|
| 不识别扫描件 | 纯图片型 PDF（无文本层）无法提取文字，需先 OCR 预处理 |
| 不处理加密文件 | 带打开密码的 PDF 无法解析，需先解除密码保护 |
| 不保留复杂排版 | 多栏、表格、浮动框等复杂版式仅保留阅读顺序，不还原视觉布局 |
| 不解析表单域 | 交互式表单字段值不在提取范围内 |
| 不处理损坏文件 | 文件头损坏或结构异常的 PDF 会直接报错退出 |

### 1.3 适用对象

- 需要批量提取 PDF 文本的自动化脚本
- 需要读取 PDF 元数据做归档管理的场景
- 需要分析文档章节结构用于知识库构建的流程

---

## 二、触发方式

### 2.1 触发词

以下关键词可触发本 Skill 的调用：

- `groomlake`
- `adobe解析`
- `pdf提取`
- `文档结构分析`
- `元数据读取`
- `PDF解析`
- `文档信息抽取`

### 2.2 场景映射表

| 用户说（大白话） | 实际执行动作 |
|------------------|--------------|
| "帮我把这个 PDF 的文字弄出来" | 执行文本提取流程 |
| "这个文档是谁写的、什么时候建的？" | 读取元数据字段 |
| "我想看看这份文档的目录结构" | 分析章节层级树 |
| "这个 PDF 打不开，帮我看看啥问题" | 运行错误诊断流程 |
| "我有 50 个 PDF 要批量处理" | 进入批量处理模式 |

---

## 三、标准操作流程

### 3.1 前置条件

| 条件 | 要求 |
|------|------|
| 输入文件 | 必须是 `.pdf` 格式，文件大小 ≤ 500MB |
| 文件权限 | 当前用户具备读取权限，文件未被其他进程锁定 |
| 环境依赖 | 已安装 groomlake 可执行文件，版本 ≥ 1.0.0 |
| 网络要求 | 无需联网，纯本地解析 |

### 3.2 执行步骤

**步骤 1：确认工具版本**

```bash
groomlake --version
```

输出示例：

```
groomlake version 1.0.0
```

**步骤 2：运行自检（可选但推荐）**

```bash
groomlake --selftest
```

自检通过后输出：

```
[OK] Core modules loaded
[OK] PDF parser initialized
[OK] Metadata extractor ready
[OK] Structure analyzer ready
```

**步骤 3：执行解析**

```bash
groomlake input.pdf --output result.json
```

**步骤 4：查看输出**

```bash
cat result.json
```

### 3.3 输出规范

解析结果统一输出为 JSON 格式，顶层结构如下：

```json
{
  "file": "input.pdf",
  "parse_status": "success",
  "metadata": { ... },
  "content": { ... },
  "structure": { ... },
  "warnings": []
}
```

各字段含义见「参数说明表」。

---

## 四、参数说明表

### 4.1 命令行参数

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `input.pdf` | 位置参数 | 是 | 无 | 待解析的 PDF 文件路径 |
| `--output` | 字符串 | 否 | 标准输出 | 结果写入的文件路径 |
| `--verbose` | 布尔 | 否 | `false` | 输出详细处理日志 |
| `--selftest` | 布尔 | 否 | `false` | 运行自检后退出 |
| `--version` | 布尔 | 否 | `false` | 打印版本号后退出 |
| `--extract` | 枚举 | 否 | `all` | 可选值：`text` / `metadata` / `structure` / `all` |
| `--page-range` | 字符串 | 否 | 全部 | 指定页码范围，如 `1-10,15` |

### 4.2 输出 JSON 字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| `file` | 字符串 | 输入文件路径 |
| `parse_status` | 枚举 | `success` / `partial` / `failed` |
| `metadata.title` | 字符串 | 文档标题（可能为空） |
| `metadata.author` | 字符串 | 作者（可能为空） |
| `metadata.creation_date` | 字符串 | 创建时间，ISO 8601 格式 |
| `metadata.modification_date` | 字符串 | 修改时间，ISO 8601 格式 |
| `metadata.pdf_version` | 字符串 | PDF 规范版本号 |
| `metadata.page_count` | 整数 | 总页数 |
| `content.pages` | 数组 | 每页的文本内容，按页分组 |
| `content.pages[].number` | 整数 | 页码（从 1 开始） |
| `content.pages[].text` | 字符串 | 该页提取的纯文本 |
| `structure.headings` | 数组 | 标题层级树，按出现顺序排列 |
| `structure.headings[].level` | 整数 | 标题级别（1-6） |
| `structure.headings[].text` | 字符串 | 标题文本 |
| `structure.headings[].page` | 整数 | 标题所在页码 |
| `warnings` | 数组 | 非致命警告信息列表 |

---

## 五、置信度门控

### 5.1 输出质量分级

| 场景 | 处理方式 |
|------|----------|
| 文本层完整、结构清晰 | 正常输出，`parse_status` 为 `success` |
| 部分页面无文本层 | 输出可提取内容，`parse_status` 为 `partial`，并在 `warnings` 中注明页码 |
| 元数据字段缺失 | 对应字段置为 `null`，不猜测、不填充 |
| 标题层级无法确定 | 该标题的 `level` 字段输出 `[需核实:level]` 占位符 |
| 文件损坏或无法解析 | `parse_status` 为 `failed`，输出错误码（见错误码体系） |

### 5.2 占位符规则

当信息不足时，使用以下格式标记：

```
[需核实:字段名]
```

示例：

```json
{
  "metadata": {
    "title": "[需核实:title]",
    "author": null
  }
}
```

严禁编造不存在的元数据或文本内容。

---

## 六、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| `E001` | 文件不存在 | "指定的文件路径不存在，请检查路径是否正确" | 1. 确认文件路径；2. 检查文件名拼写；3. 确认当前目录 |
| `E002` | 文件格式不支持 | "仅支持 .pdf 格式文件，请转换格式后重试" | 1. 确认文件扩展名；2. 使用 PDF 转换工具转换格式 |
| `E003` | 文件加密 | "文件已加密，请先解除密码保护" | 1. 使用密码解锁工具；2. 重新导出无密码版本 |
| `E004` | 文件损坏 | "文件结构异常，无法解析" | 1. 尝试用 Adobe Acrobat 修复；2. 重新导出 PDF |
| `E005` | 权限不足 | "当前用户无读取权限" | 1. 检查文件权限；2. 使用 `chmod` 调整权限 |
| `E006` | 内存不足 | "文件过大，内存溢出" | 1. 使用 `--page-range` 分段处理；2. 增加系统内存 |
| `E007` | 未知错误 | "发生未预期错误，请查看 --verbose 日志" | 1. 使用 `--verbose` 重新执行；2. 提交日志排查 |

---

## 七、FAQ 反模式

### 7.1 常见坑与正确做法

| 常见错误（反模式） | 正确做法 |
|--------------------|----------|
| 直接对扫描件执行文本提取，期望得到文字 | 先做 OCR 处理，再调用本工具提取文本层 |
| 忽略 `warnings` 字段，直接使用全部输出 | 检查 `warnings`，对 `partial` 结果做人工复核 |
| 对加密文件反复重试 | 先解除密码保护，再执行解析 |
| 用 `--extract text` 后期望得到完整元数据 | 使用 `--extract all` 或单独指定 `metadata` |
| 不检查 `parse_status` 就写入数据库 | 先判断状态，`failed` 结果丢弃，`partial` 结果标记 |

### 7.2 反模式对照表

| 反模式 | 问题 | 替代方案 |
|--------|------|----------|
| 批量处理时不设 `--page-range` | 大文件内存溢出 | 按页分段处理 |
| 依赖默认输出到标准输出 | 日志与结果混在一起 | 使用 `--output` 指定结果文件 |
| 忽略 `--verbose` 调试 | 出错时无法定位 | 出错时用 `--verbose` 重跑 |
| 对 `null` 元数据字段做默认填充 | 产生虚假数据 | 保留 `null`，由下游逻辑处理 |

---

## 八、渐进式披露

### 8.1 速查卡（30 秒上手）

```bash
# 基本用法
groomlake document.pdf --output result.json

# 只看元数据
groomlake document.pdf --extract metadata

# 只看第 1-5 页文本
groomlake document.pdf --extract text --page-range 1-5

# 调试模式
groomlake document.pdf --verbose
```

### 8.2 新手路径（首次使用）

1. 运行 `groomlake --selftest` 确认环境正常
2. 用一个小型 PDF（< 10 页）测试基本解析
3. 查看输出 JSON，理解 `metadata` / `content` / `structure` 三个模块
4. 尝试 `--extract` 参数，分别提取不同模块
5. 阅读「错误码体系」，了解常见异常处理方式

### 8.3 进阶路径（深度集成）

1. 研究输出 JSON 结构，设计数据映射层对接自有系统
2. 利用 `--verbose` 调试复杂文件（如含大量嵌入字体或复杂图层的 PDF）
3. 结合 `--page-range` 设计分片处理流水线，应对超大文件
4. 参考「能力边界」评估工具适用场景，对扫描件提前规划 OCR 预处理
5. 建立 `warnings` 监控机制，对 `partial` 结果做自动化标记

---

## 九、用户协议

<!-- user-agreement-injected -->

**使用本 Skill 即表示您同意以下条款：**

1. **责任承担**：使用者自行承担使用本 Skill 的全部责任。因使用本 Skill 产生的任何直接或间接损失，包括但不限于数据丢失、业务中断、利润损失等，本 Skill 作者不承担任何责任。

2. **禁止反向工程**：未经明确许可，禁止对本 Skill 进行反向工程、反编译、反汇编或试图提取源代码。禁止修改、复制、分发本 Skill 的任何部分。

3. **免责声明**：本 Skill 按"现状"提供，不提供任何明示或暗示的保证，包括但不限于适销性、特定用途适用性和非侵权保证。

4. **协议变更**：本协议可能随时更新，使用者应定期查看最新版本。继续使用本 Skill 即视为接受更新后的协议。

---

## 十、许可证（License）

<!-- professional-license-embedded -->

**MIT License**

Copyright (c) 2024 原创作者（自持版权）

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
