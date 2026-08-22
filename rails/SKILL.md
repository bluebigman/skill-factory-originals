---
slug: rails
name: rails
displayName: 数据转换 结构化处理 批量执行
description: 将输入数据按规则转换为结构化结果，支持批量与自定义格式。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: Lin Chen
agent_created: true
trigger_words: rails, 数据处理, 结构化输出, 批量转换, 数据整理
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# Rails 数据转换与结构化处理技能

## 一、能力边界（一页纸速查卡）

### 能做（核心能力）

| 编号 | 能力项 | 说明 |
|------|--------|------|
| 1 | 数据/文件/URL 输入解析 | 支持从文本、文件路径、URL 中提取原始内容 |
| 2 | 关键信息识别与保留 | 自动识别输入中的核心字段，保留上下文关联 |
| 3 | 结构化格式输出 | 按约定模板生成 JSON/YAML/CSV 等结构化结果 |
| 4 | 置信度标注 | 对不确定字段标注置信度等级，不隐瞒不确定性 |
| 5 | 批量处理与自定义格式 | 支持多文件循环处理，允许用户自定义输出模板 |

### 不能做（明确限制）

- 不处理二进制文件（图片、音视频）内容解析
- 不执行外部系统写入操作（如数据库写入、API 调用）
- 不保证 100% 识别准确率，复杂场景需人工复核
- 不处理加密或权限受限的文件内容

### 适用对象

- 需要将散乱数据整理为规范格式的开发者
- 需要批量转换文件格式的运维人员
- 需要从 URL 提取结构化信息的数据分析师

---

## 二、触发方式

### 触发词

`rails`、`数据处理`、`结构化输出`、`批量转换`、`数据整理`

### 场景映射表

| 用户说（大白话） | 触发动作 |
|------------------|----------|
| "帮我把这几个 CSV 转成 JSON" | 批量格式转换 |
| "这个网页里的表格帮我提取出来" | URL 内容解析 |
| "把这份报告里的关键字段整理一下" | 关键信息提取 |
| "我有 100 个文件要统一处理" | 批量执行模式 |
| "输出格式我要自定义" | 自定义模板配置 |

---

## 三、标准处理流程

### 前置条件

1. 输入文件与工作目录在同一路径下，命名规范一致（如 `input_01.csv`、`input_02.csv`）
2. 确认输入格式（文件类型、编码、分隔符）
3. 明确输出格式要求（文件类型、字段结构、命名规则）

### 执行步骤

**步骤 1：输入解析**

- 读取输入内容，识别数据类型（文本/表格/URL）
- 检测编码格式（UTF-8、GBK 等），乱码时提示用户

**步骤 2：关键信息识别**

- 按字段规则提取核心数据
- 保留原始上下文（如行号、来源标识）

**步骤 3：结构化处理**

- 按约定模板组织数据
- 字段映射规则如下：

| 输入类型 | 默认输出字段 | 说明 |
|----------|--------------|------|
| CSV | `id`, `content`, `source` | 自动添加行号与来源 |
| URL | `title`, `content`, `url`, `timestamp` | 提取页面标题与正文 |
| 纯文本 | `text`, `length`, `hash` | 计算长度与哈希值 |

**步骤 4：置信度标注**

- 字段值完整且明确 → `confidence: high`
- 字段值存在但模糊 → `confidence: medium`
- 字段值缺失或冲突 → `confidence: low`，并输出 `[需核实:字段名]`

**步骤 5：输出与自查**

- 生成结果文件，命名规则：`output_<原文件名>.<新格式>`
- 自查清单：
  - [ ] 所有必需字段已填充
  - [ ] 格式符合约定模板
  - [ ] 置信度标注完整
  - [ ] 无遗漏或重复条目

---

## 四、置信度门控机制

### 处理原则

**不编造、不猜测、不省略**。当信息不足时，使用占位符 `[需核实:字段名]` 明确标注。

### 置信度等级定义

| 等级 | 判定标准 | 示例 |
|------|----------|------|
| high | 字段值直接来自源数据，无歧义 | 日期格式 `2024-01-15` |
| medium | 字段值经过推断或格式转换 | 从文本中提取的姓名 |
| low | 字段值缺失、冲突或来源不可靠 | 多个来源数据不一致 |

### 处理示例

```json
{
  "id": 1,
  "name": "张三",
  "age": [需核实:age],
  "confidence": {
    "name": "high",
    "age": "low"
  }
}
```

---

## 五、错误码体系

| 错误码 | 错误描述 | 提示话术 | 修正步骤 |
|--------|----------|----------|----------|
| E001 | 文件不存在 | "未找到指定文件，请检查路径是否正确" | 1. 确认文件路径 2. 检查文件名拼写 3. 重试 |
| E002 | 格式不支持 | "当前格式不在支持范围内，支持 CSV/JSON/TXT/URL" | 1. 转换源文件格式 2. 或联系管理员扩展支持 |
| E003 | 编码解析失败 | "文件编码无法识别，可能出现乱码" | 1. 指定编码格式 2. 使用 `--encoding` 参数 |
| E004 | 字段映射冲突 | "输入字段与输出模板存在冲突" | 1. 检查字段映射表 2. 调整模板配置 |
| E005 | 批量处理中断 | "批量处理在第 N 个文件处中断" | 1. 查看错误日志 2. 修复问题文件 3. 从断点继续 |

---

## 六、常见坑与反模式对照（FAQ）

### 坑 1：忽略原始文件备份

**反模式**：直接修改原文件，导致数据丢失无法恢复。

**正确做法**：始终保留原始文件副本，输出到独立目录。

### 坑 2：批量处理前不试运行

**反模式**：直接对 100 个文件执行，结果全部格式错误。

**正确做法**：先用单个样本验证输出格式，确认无误后再批量执行。

### 坑 3：置信度标注被忽略

**反模式**：低置信度字段直接填默认值，造成数据失真。

**正确做法**：保留 `[需核实:字段]` 占位，交由人工确认。

### 坑 4：编码问题未提前确认

**反模式**：处理 GBK 编码文件时使用 UTF-8 解析，产生乱码。

**正确做法**：处理前先检测文件编码，必要时显式指定。

### 坑 5：输出格式与下游系统不匹配

**反模式**：下游系统需要 YAML，却输出 JSON。

**正确做法**：处理前确认下游系统的格式要求，配置对应模板。

---

## 七、渐进式阅读路径

### 速查卡（30 秒上手）

```
输入 → 解析 → 识别 → 结构化 → 标注置信度 → 输出
```

### 新手路径（首次使用）

1. 阅读「能力边界」了解适用范围
2. 阅读「标准处理流程」步骤 1-3
3. 使用单个文件试运行
4. 检查输出格式与置信度标注

### 进阶路径（深度使用）

1. 阅读「错误码体系」掌握异常处理
2. 阅读「FAQ 反模式」避免常见问题
3. 自定义输出模板
4. 配置批量处理参数
5. 结合 CI/CD 实现自动化流水线

---

## 八、命令行接口

```bash
# 版本信息
rails --version

# 自检模式
rails --selftest

# 基本用法（示例）
rails process input.csv --format json --output ./output/
```

---

## 用户协议

<!-- user-agreement-injected -->

**使用本 Skill 即表示您同意以下条款：**

1. **责任承担**：使用者自行承担使用本 Skill 产生的全部责任。因使用本 Skill 导致的任何直接或间接损失，作者不承担任何责任。
2. **禁止反向工程**：不得对本 Skill 进行反向工程、反编译、破解或试图提取源代码。
3. **合法用途**：本 Skill 仅供学习与参考用途，不得用于任何违法或侵权活动。
4. **无担保**：本 Skill 按"现状"提供，不附带任何明示或暗示的担保。
5. **修改与分发**：未经许可，不得修改或重新分发本 Skill。

---

## 许可证（License）

<!-- professional-license-embedded -->

### MIT License

Copyright (c) 2024 Lin Chen

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
