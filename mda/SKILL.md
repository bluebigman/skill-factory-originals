---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: mda
name: mda
displayName: 文档编译 智能转换 结构化输出
description: 将任意数据源编译为标准化 Markdown 文档，支持批量处理与置信度标注。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/mda
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: Ling
agent_created: true
trigger_words: ["mda", "文档编译", "结构化转换", "markdown 生成", "批量文档处理"]
---

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# MDA 文档编译 Skill

## 一、能力边界速查卡

| 维度 | 说明 |
|------|------|
| **核心用途** | 将用户提供的数据、文件或 URL 内容，编译为符合 MDA 规范的 Markdown 文档 |
| **输入类型** | 文本数据、本地文件路径、远程 URL、批量数据列表 |
| **输出类型** | 单个 `.md` 文件、批量 `.md` 文件集合、带置信度标注的结构化文档 |
| **可处理** | 数据提取、字段映射、格式转换、批量编译、置信度评估 |
| **不可处理** | 二进制文件解码、加密内容解密、需要登录的私有资源访问 |
| **适用对象** | 需要将非结构化数据转为标准文档的开发者、文档工程师、数据分析师 |

## 二、触发方式与场景映射

| 触发词/场景 | 实际含义 | 执行动作 |
|-------------|----------|----------|
| "把这份 CSV 转成文档" | 数据转换需求 | 解析 CSV → 生成 Markdown 表格文档 |
| "编译这个 URL 的内容" | 网页内容提取 | 抓取 URL → 提取正文 → 生成结构化文档 |
| "批量处理这些文件" | 多文件处理 | 遍历文件列表 → 逐一编译 → 输出合集 |
| "mda --selftest" | 自检模式 | 运行内部测试用例，验证编译功能正常 |
| "mda --version" | 版本查询 | 输出当前 Skill 版本号 |

## 三、标准执行流程

### 前置条件

1. 确认输入数据可访问（文件存在 / URL 可访问）
2. 确认输出目录有写入权限
3. 明确输出格式要求（默认输出标准 Markdown）

### 执行步骤

**步骤 1：输入解析**

- 识别输入类型（文本 / 文件 / URL / 批量列表）
- 提取关键元数据（文件名、来源、时间戳）

**步骤 2：内容提取与清洗**

- 从原始数据中提取正文内容
- 去除无关噪声（广告、导航、重复信息）
- 保留关键字段与数据结构

**步骤 3：结构化映射**

- 将提取内容映射到 Markdown 结构（标题、段落、列表、表格、代码块）
- 按 MDA 规范组织文档层级

**步骤 4：置信度评估**

- 对每个字段标注置信度等级：
  - `高`：数据完整且来源可靠
  - `中`：数据部分缺失或来源一般
  - `低`：数据大量缺失或来源不明
- 信息不足时输出 `[需核实:字段名]` 占位符，不编造内容

**步骤 5：输出生成**

- 生成标准 Markdown 文档
- 批量处理时生成带索引的文档集合

**步骤 6：自查校验**

- 检查字段完整性（无遗漏必填项）
- 检查格式正确性（Markdown 语法合法）
- 检查置信度标注（所有不确定项均有标注）

### 输出规范

```markdown
# 文档标题

> 来源: [来源描述] | 编译时间: [时间戳] | 置信度: [整体置信度]

## 内容概览
[摘要段落]

## 详细内容
[结构化正文]

## 数据字段
| 字段名 | 值 | 置信度 |
|--------|-----|--------|
| [字段] | [值] | [高/中/低] |

## 原始来源
[来源链接或文件路径]
```

## 四、置信度门控机制

| 场景 | 处理方式 | 示例 |
|------|----------|------|
| 字段值缺失 | 输出 `[需核实:字段名]` | `[需核实:作者]` |
| 数据来源不可靠 | 降低置信度至"低" | 置信度: 低 |
| 多源数据冲突 | 保留主要来源，标注冲突 | `[需核实:价格(来源A:100, 来源B:120)]` |
| 数据完整可靠 | 标注"高"置信度 | 置信度: 高 |

**原则：宁可标注缺失，绝不虚构数据。**

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| E001 | 输入为空 | "未检测到有效输入，请提供数据、文件或 URL" | 检查输入参数，重新提交 |
| E002 | 文件不存在 | "指定文件路径无法访问，请确认路径正确" | 核对路径，确认文件存在 |
| E003 | URL 不可访问 | "目标 URL 返回错误状态码，无法获取内容" | 检查 URL 有效性，或更换网络环境 |
| E004 | 格式不支持 | "当前输入格式不在支持范围内（支持: txt/csv/json/html/md）" | 转换格式后重试 |
| E005 | 输出目录无权限 | "无法写入输出目录，请检查权限设置" | 修改目录权限或更换输出路径 |
| E006 | 批量处理中断 | "批量处理在第 N 个文件处中断，请检查该文件格式" | 单独处理问题文件，跳过后续继续 |

## 六、FAQ 与反模式对照

| 常见坑 | 反模式（错误做法） | 正模式（正确做法） |
|--------|-------------------|-------------------|
| 数据缺失时编造内容 | 猜测缺失字段值并写入文档 | 使用 `[需核实:字段名]` 占位，提示用户补充 |
| 忽略置信度标注 | 所有数据一律标注"高"置信度 | 根据数据来源和完整性客观评估 |
| 批量处理时中断 | 遇到错误文件即终止全部处理 | 跳过问题文件，记录错误，继续处理其余文件 |
| 输出格式混乱 | 不同文件使用不同模板 | 统一使用 MDA 标准模板，保持一致性 |
| 忽略原始来源记录 | 输出文档不包含来源信息 | 每个文档保留来源路径/URL 和编译时间 |

## 七、渐进式阅读路径

### 新手快速上手（5 分钟）

1. 阅读「能力边界速查卡」了解工具范围
2. 查看「触发方式与场景映射」找到你的场景
3. 按「标准执行流程」操作一次简单转换

### 进阶用户（15 分钟）

1. 深入理解「置信度门控机制」，掌握数据质量评估
2. 熟悉「错误码体系」，快速定位和解决问题
3. 参考「FAQ 反模式」避免常见错误

### 高级用户（30 分钟）

1. 自定义输出模板，扩展 MDA 规范
2. 设计批量处理流水线，集成到自动化工作流
3. 结合其他 Skill 构建完整文档处理链路

## 八、CLI 接口参考

| 命令 | 参数 | 说明 |
|------|------|------|
| `mda` | `<input>` | 编译单个输入（文件/URL/文本） |
| `mda --selftest` | 无 | 运行自检，验证功能完整性 |
| `mda --version` | 无 | 输出版本号 |

## 用户协议

使用本 Skill 即表示您同意以下条款：

1. **责任承担**：使用者自行承担使用本 Skill 产生的全部责任。本 Skill 提供的输出仅供参考，不构成任何形式的保证或承诺。
2. **禁止反向工程**：不得对本 Skill 进行反向工程、反编译、破解或试图提取底层算法。
3. **合规使用**：使用者应确保输入数据的合法性和合规性，不得使用本 Skill 处理违法违规内容。
4. **免责声明**：本 Skill 按"现状"提供，不附带任何明示或暗示的保证，包括但不限于适销性、特定用途适用性和非侵权保证。

<!-- user-agreement-injected -->

## 许可证（License）

本 Skill 采用 MIT 许可证发布：

```
MIT License

Copyright (c) 2024 Ling

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
