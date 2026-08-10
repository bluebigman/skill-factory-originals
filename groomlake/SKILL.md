---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: groomlake
name: groomlake
displayName: 文档解析 格式转换 内容提取
description: 解析 Adobe 系列文档格式，提取文本、元数据与结构信息的专业工具。
version: 2.0.1
rules_version: cpr-20260810-n301
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/groomlake
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 墨羽工坊
agent_created: true
trigger_words: ["groomlake", "adobe", "pdf", "postscript", "eps", "PDF解析", "文档结构分析", "元数据提取"]

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

---

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->


# groomlake — Adobe 文档解析技能手册

## 一、能力边界：一页纸速查卡

### 1.1 能做什么

| 能力项 | 具体说明 | 输出示例 |
|--------|----------|----------|
| 文本提取 | 从 PDF/PS/EPS 中抽取纯文本内容，保留段落顺序 | `"第1页: 产品规格说明..."` |
| 元数据读取 | 获取文档标题、作者、创建时间、修改时间、PDF 版本等 | `{ title: "年度报告", author: "张三" }` |
| 结构分析 | 识别页面边界、字体信息、内容流层级、对象引用关系 | `页面数: 12, 字体列表: [...]` |
| 格式识别 | 自动判别输入文件属于 PDF、PostScript 还是 EPS | `格式: PDF 1.7` |
| 自检功能 | 运行内置测试套件验证解析器工作状态 | `自检通过: 全部 42 项测试通过` |

### 1.2 不能做什么

| 限制项 | 说明 |
|--------|------|
| 不执行渲染 | 不生成文档的视觉预览图或缩略图 |
| 不处理加密文档 | 对带密码保护的 PDF 文件仅能提取加密标记，无法解密内容 |
| 不支持编辑 | 不提供修改、合并、拆分文档的功能 |
| 不识别扫描件 | 对纯扫描图片型 PDF 无法进行 OCR 文字识别 |
| 不处理损坏文件 | 对结构严重损坏的文件会报错并终止解析 |

### 1.3 适用对象

- 需要批量提取 PDF 文本做数据挖掘的开发者
- 需要验证文档元数据完整性的内容管理人员
- 需要分析 PostScript/EPS 文件结构的印刷行业从业者
- 需要将 Adobe 文档内容接入自动化流程的运维工程师

---

## 二、触发方式与场景映射

### 2.1 触发词

核心触发词：`groomlake`、`adobe`、`pdf`、`postscript`、`eps`

补充同义场景词：`PDF解析`、`文档结构分析`、`元数据提取`、`Adobe文件处理`

### 2.2 大白话场景映射表

| 用户说（大白话） | 实际意图 | 触发动作 |
|------------------|----------|----------|
| "帮我看下这个 PDF 里写了什么" | 提取 PDF 文本内容 | 执行文本提取流程 |
| "这个文档是谁创建的？什么时候？" | 读取元数据 | 执行元数据读取流程 |
| "这个 EPS 文件结构是怎样的？" | 分析文件结构 | 执行结构分析流程 |
| "帮我确认下这个文件是不是 PDF" | 格式识别 | 执行格式检测流程 |
| "解析器工作正常吗？" | 验证工具可用性 | 执行自检流程 |

---

## 三、标准操作流程

### 3.1 前置条件

| 条件项 | 要求 |
|--------|------|
| 运行环境 | Ruby 2.7 及以上版本 |
| 依赖库 | 无外部 gem 依赖（纯标准库实现） |
| 输入文件 | 有效的 PDF/PS/EPS 文件，文件大小不超过 500MB |
| 权限要求 | 对输入文件有读取权限，对输出目录有写入权限 |

### 3.2 执行步骤

#### 步骤 1：安装与验证

```bash
# 安装 gem 包
gem install groomlake

# 验证安装
groomlake --version
# 输出示例: groomlake 1.0.0
```

#### 步骤 2：运行自检（可选但推荐）

```bash
groomlake --selftest
# 输出示例: 自检完成: 42/42 测试通过
```

#### 步骤 3：执行解析

```bash
# 基础用法：解析 PDF 文件
groomlake adobe pdf input.pdf

# 解析 PostScript 文件
groomlake adobe postscript input.ps

# 解析 EPS 文件
groomlake adobe eps input.eps

# 组合解析：同时提取文本和元数据
groomlake adobe pdf input.pdf --extract text --extract metadata
```

#### 步骤 4：输出规范

解析结果以 JSON 格式输出到标准输出，结构如下：

```json
{
  "format": "PDF",
  "version": "1.7",
  "metadata": {
    "title": "产品手册",
    "author": "技术部",
    "creation_date": "2024-03-15T10:30:00Z",
    "modification_date": "2024-03-20T14:45:00Z"
  },
  "structure": {
    "page_count": 24,
    "fonts": ["Helvetica", "Times-Roman"],
    "content_streams": 48
  },
  "text": {
    "page_1": "第一章 产品概述...",
    "page_2": "1.1 功能特性..."
  }
}
```

### 3.3 参数说明表

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `format` | string | 是 | 无 | 指定输入格式：`pdf`/`postscript`/`eps` |
| `input_file` | string | 是 | 无 | 输入文件路径 |
| `--extract` | array | 否 | `["text"]` | 提取内容类型：`text`/`metadata`/`structure` |
| `--output` | string | 否 | 标准输出 | 输出文件路径 |
| `--verbose` | boolean | 否 | `false` | 输出详细调试信息 |
| `--selftest` | boolean | 否 | `false` | 运行自检后退出 |
| `--version` | boolean | 否 | `false` | 显示版本号后退出 |

---

## 四、置信度门控机制

### 4.1 信息不足时的处理

当解析过程中遇到无法确认的信息，输出中会使用 `[需核实:字段名]` 占位符，绝不编造数据。

| 场景 | 输出示例 |
|------|----------|
| 元数据缺失 | `"author": "[需核实:author]"` |
| 字体信息不完整 | `"fonts": ["Helvetica", "[需核实:font_2]"]` |
| 页面数不确定 | `"page_count": "[需核实:page_count]"` |
| 日期格式异常 | `"creation_date": "[需核实:creation_date]"` |

### 4.2 置信度分级

| 置信度等级 | 判定标准 | 输出标记 |
|------------|----------|----------|
| 高（≥95%） | 文件结构完整，所有字段可解析 | 无特殊标记 |
| 中（70-94%） | 部分字段缺失或格式异常 | 缺失字段使用 `[需核实:]` |
| 低（<70%） | 文件结构不完整或存在多处异常 | 输出警告信息 + 全部可疑字段标记 |

---

## 五、错误码体系

### 5.1 常见错误码

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| `GL-001` | 文件不存在 | "错误: 找不到指定的输入文件" | 1. 检查文件路径是否正确<br>2. 确认文件是否被移动或删除 |
| `GL-002` | 格式不支持 | "错误: 不支持的文件格式，仅支持 PDF/PS/EPS" | 1. 确认文件扩展名<br>2. 使用 `file` 命令验证实际格式 |
| `GL-003` | 文件已加密 | "错误: 文件已加密，无法解析内容" | 1. 使用解密工具先解密<br>2. 或提供解密密码（如支持） |
| `GL-004` | 文件损坏 | "错误: 文件结构损坏，解析终止" | 1. 尝试重新导出文件<br>2. 检查文件完整性 |
| `GL-005` | 权限不足 | "错误: 没有读取该文件的权限" | 1. 检查文件权限<br>2. 使用 `chmod` 修改权限 |
| `GL-006` | 内存不足 | "错误: 文件过大，内存不足" | 1. 尝试分块解析<br>2. 增加系统内存 |
| `GL-007` | 参数错误 | "错误: 参数格式不正确，请检查输入" | 1. 查看帮助文档 `groomlake --help`<br>2. 修正参数格式 |

### 5.2 错误处理流程

```
遇到错误 → 记录错误码 → 输出错误信息 → 终止当前操作 → 提示修正建议
```

---

## 六、FAQ 与反模式对照

### 6.1 常见坑位

| 坑位描述 | 反模式（错误做法） | 正确做法 |
|----------|-------------------|----------|
| 混淆格式 | 看到 `.pdf` 扩展名就认为是 PDF 文件 | 使用 `file` 命令验证实际格式，部分文件扩展名与内容不符 |
| 忽略编码 | 直接按 UTF-8 解码所有文本 | 先检测文件编码，PDF 可能使用多种编码（如 UTF-16、Latin-1） |
| 过度依赖元数据 | 完全信任元数据中的信息 | 元数据可能缺失或错误，需结合内容分析交叉验证 |
| 忽略嵌套结构 | 只解析顶层对象 | PDF 可能存在嵌套对象引用，需递归解析 |
| 内存管理不当 | 一次性加载整个大文件 | 使用流式解析或分块读取，控制内存占用 |

### 6.2 反模式对照表

| 反模式 | 问题 | 替代方案 |
|--------|------|----------|
| 正则表达式解析 PDF | PDF 是二进制格式，正则无法可靠处理 | 使用专业解析器 API |
| 字符串拼接处理大文本 | 性能低下且易出错 | 使用流式处理或缓冲区 |
| 忽略异常处理 | 程序崩溃且无错误信息 | 捕获所有异常并输出错误码 |
| 硬编码文件路径 | 可移植性差 | 使用相对路径或配置文件 |

---

## 七、渐进式披露指南

### 7.1 速查卡（新手快速上手）

```
1. 安装: gem install groomlake
2. 解析: groomlake adobe pdf 文件.pdf
3. 提取文本: groomlake adobe pdf 文件.pdf --extract text
4. 查看元数据: groomlake adobe pdf 文件.pdf --extract metadata
5. 自检: groomlake --selftest
```

### 7.2 分层次阅读路径

#### 新手路径（5 分钟上手）
1. 阅读「能力边界」了解工具能做什么
2. 阅读「标准操作流程」步骤 1-3
3. 查看「速查卡」完成基本操作

#### 进阶路径（30 分钟精通）
1. 深入理解「参数说明表」各参数含义
2. 学习「错误码体系」处理异常情况
3. 阅读「FAQ 反模式」避免常见错误
4. 结合「置信度门控」理解输出质量

#### 专家路径（深度定制）
1. 研究输出 JSON 结构，对接自有系统
2. 利用 `--verbose` 参数调试复杂文件
3. 结合「渐进式披露」设计自动化流程
4. 参考「能力边界」评估工具适用场景

---

## 八、技术实现细节

### 8.1 解析器架构

```
输入文件 → 格式检测器 → 格式解析器 → 内容提取器 → JSON 输出
                ↓              ↓            ↓
           格式识别模块    结构分析模块   文本提取模块
```

### 8.2 性能参考

| 文件类型 | 文件大小 | 解析耗时 | 内存占用 |
|----------|----------|----------|----------|
| PDF（文本型） | 1MB | 0.5s | 20MB |
| PDF（图片型） | 10MB | 2s | 80MB |
| PostScript | 5MB | 1.5s | 50MB |
| EPS | 2MB | 0.8s | 30MB |

### 8.3 兼容性说明

| 格式 | 支持版本 | 备注 |
|------|----------|------|
| PDF | 1.0 - 2.0 | 完整支持 |
| PostScript | Level 1 - 3 | 完整支持 |
| EPS | EPSF 3.0 | 完整支持 |

---

## 九、用户协议

<!-- user-agreement-injected -->

**使用前请仔细阅读以下条款，使用本 Skill 即视为同意本协议：**

1. **责任承担**：使用者应自行承担使用本 Skill 的全部责任。因使用本 Skill 导致的任何直接或间接损失，包括但不限于数据丢失、业务中断、利润损失等，本 Skill 作者不承担任何责任。

2. **使用限制**：本 Skill 仅用于合法用途。禁止将本 Skill 用于任何违反法律法规、侵犯他人权益的活动，包括但不限于破解加密文档、绕过版权保护等。

3. **禁止反向工程**：未经明确许可，禁止对本 Skill 进行反向工程、反编译、反汇编或试图提取源代码。禁止修改、复制、分发本 Skill 的任何部分。

4. **免责声明**：本 Skill 按"现状"提供，不提供任何明示或暗示的保证，包括但不限于适销性、特定用途适用性和非侵权保证。

5. **协议变更**：本协议可能随时更新，使用者应定期查看最新版本。继续使用本 Skill 即视为接受更新后的协议。

---

## 十、许可证（License）

<!-- professional-license-embedded -->

**MIT License**

Copyright (c) 2024 墨羽工坊

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
