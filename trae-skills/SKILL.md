---
slug: trae-skills
name: trae-skills
displayName: 技能检索 匹配编排 开发辅助
description: 面向开发者的技能检索、匹配与执行编排辅助工具。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 林墨
agent_created: true
trigger_words: ["trae skills", "技能列表", "技能选择", "skill 匹配", "技能编排", "--selftest", "--version", "技能查找", "技能调度"]
---

> 本内容由 AI 生成，仅供学习参考 <!-- ai-generated-notice -->

本 Skill 由 AI 辅助生成，仅供参考。

---

# trae-skills 技能编排辅助工具

## 一、能力边界（一页纸速查卡）

### 能做什么

| 能力项 | 说明 | 适用场景 |
|--------|------|----------|
| 技能检索 | 按关键词、场景、名称查找可用技能 | 需要快速定位某个技能时 |
| 技能匹配 | 根据任务描述推荐最合适的技能组合 | 面对新任务不知用哪个技能时 |
| 执行编排 | 将多个技能按顺序串联，形成工作流 | 复杂任务需要多步骤处理时 |
| 自检 | 通过 `--selftest` 验证工具链完整性 | 环境异常或首次使用前 |
| 版本查询 | 通过 `--version` 查看当前版本信息 | 确认工具版本时 |

### 不能做什么（明确边界）

| 限制项 | 说明 |
|--------|------|
| 不执行技能内部逻辑 | 本工具只负责检索、匹配与编排，不替代技能本身的运行 |
| 不修改技能源码 | 不提供编辑、调试技能代码的能力 |
| 不保证匹配结果绝对正确 | 匹配基于规则与元数据，实际效果需人工确认 |
| 不处理跨平台兼容 | 仅面向当前 CLI 环境，不负责 Windows/macOS/Linux 差异适配 |

### 适用对象

- 日常使用技能库的开发者
- 需要批量处理文件并编排多个技能的工作流设计者
- 初次接触技能系统、需要快速上手的新手

---

## 二、触发方式与场景映射

### 触发词

直接使用以下命令或短语触发：

| 触发词 | 对应操作 |
|--------|----------|
| `trae skills` | 进入技能工具主界面 |
| `技能列表` | 列出当前可用技能 |
| `技能选择` | 进入交互式选择流程 |
| `skill 匹配` | 根据描述推荐技能 |
| `技能编排` | 进入多技能编排模式 |
| `--selftest` | 运行自检 |
| `--version` | 显示版本号 |

### 大白话场景映射表

| 你遇到的情况 | 你该说什么 | 工具会做什么 |
|--------------|------------|--------------|
| "我有 200 个文件要处理，不知道用哪个技能" | `skill 匹配 批量文件处理` | 返回候选技能列表及匹配度 |
| "我想把 A 技能和 B 技能串起来跑" | `技能编排 A B` | 生成编排顺序并检查依赖 |
| "工具好像坏了，跑不动" | `trae skills --selftest` | 逐项检查环境与配置 |
| "我想看看现在有哪些技能可用" | `技能列表` | 输出技能清单及简介 |

---

## 三、标准流程

### 前置条件

1. 已安装 trae-skills 工具，且 `trae skills` 命令可正常响应。
2. 待处理文件已放入当前工作目录，命名遵循统一规范（如 `input_001.csv`、`input_002.csv`）。
3. 确认目标技能所需的输入格式与当前文件格式一致。

### 执行步骤（分步编号）

#### 步骤 1：准备输入

- 将待处理文件放入同一目录。
- 检查命名规范：建议使用 `前缀_序号.扩展名` 格式，避免特殊字符与空格。
- 若文件来自外部，先做格式转换与清洗。

#### 步骤 2：试运行（单样本验证）

- 选取 1 个代表性样本文件。
- 执行技能，观察输出字段与格式是否符合预期。
- 核对关键字段（如 ID、时间戳、内容主体）是否完整。

**试运行检查表：**

| 检查项 | 通过标准 |
|--------|----------|
| 输出字段完整性 | 所有预期字段均有值，无缺失 |
| 格式一致性 | 输出格式与文档描述一致 |
| 异常处理 | 无未捕获的报错或崩溃 |

#### 步骤 3：批量执行

- 确认试运行无误后，对全量数据执行。
- **保留原始文件备份**：执行前复制一份原始数据到 `backup/` 目录。
- 执行过程中监控日志，记录异常条目。

#### 步骤 4：校验结果

- 随机抽取 5%~10% 的输出条目。
- 逐项核对关键字段与源数据的一致性。
- 若发现偏差，定位原因并修正后重新执行。

### 输出规范

| 输出项 | 格式要求 |
|--------|----------|
| 执行报告 | Markdown 表格，包含：文件数、成功数、失败数、耗时 |
| 错误日志 | 每行一条，格式：`[时间戳] [错误码] 文件路径 - 错误描述` |
| 结果文件 | 与输入文件同名，加 `_out` 后缀，存放在 `output/` 目录 |

---

## 四、置信度门控

当信息不足或存在不确定性时，遵循以下规则：

1. **不编造数据**：若某字段无法从源数据中确定，输出 `[需核实:字段名]` 占位符。
2. **不猜测匹配**：若技能匹配度低于 60%，明确标注"低置信度"，并列出备选方案。
3. **不跳过校验**：若校验环节发现异常，立即停止批量执行，返回人工确认。

**示例：**

```
输出条目：{"id": 1024, "name": "[需核实:name]", "status": "pending"}
说明：源文件中该字段为空，无法推断，已标记待人工补充。
```

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| `E001` | 输入文件不存在 | "未找到指定文件，请检查路径与文件名" | 1. 确认文件路径；2. 检查文件名大小写；3. 重新执行 |
| `E002` | 格式不匹配 | "输入格式与技能要求不符" | 1. 查看技能文档中的格式要求；2. 转换文件格式；3. 重试 |
| `E003` | 技能未找到 | "未找到匹配的技能，请调整关键词" | 1. 使用 `技能列表` 查看可用项；2. 更换关键词；3. 重试 |
| `E004` | 依赖缺失 | "缺少必要依赖，请先安装" | 1. 查看依赖清单；2. 安装缺失项；3. 运行 `--selftest` 验证 |
| `E005` | 权限不足 | "当前用户无权限执行此操作" | 1. 检查文件权限；2. 切换用户或提升权限；3. 重试 |
| `E006` | 批量执行中断 | "批量执行中断，请查看错误日志" | 1. 查看 `error.log`；2. 修复问题条目；3. 从断点续跑 |

---

## 六、FAQ 反模式

### 常见坑与正确做法对照

| 常见错误（反模式） | 问题描述 | 正确做法 |
|-------------------|----------|----------|
| **跳过试运行直接全量跑** | 格式不匹配导致 200 个文件全部失败 | 先跑 1 个样本，确认无误再批量 |
| **不备份原始文件** | 执行出错后原始数据被覆盖，无法恢复 | 执行前强制备份到 `backup/` |
| **忽略错误日志** | 只看成功数，不关注失败原因 | 每次执行后检查 `error.log`，逐条处理 |
| **盲目信任匹配结果** | 匹配度 50% 的技能被直接使用，结果偏差大 | 低置信度结果必须人工复核 |
| **命名随意** | 文件名含空格、中文、特殊字符，导致解析失败 | 统一使用 `前缀_序号.扩展名` 规范 |

### 反模式示例

```
❌ 反模式：直接执行 `trae skills 批量处理` 然后跑全量数据
✅ 正确做法：先 `skill 匹配 批量文件处理` 查看推荐，再选 1 个文件试运行，确认后备份并批量执行
```

---

## 七、渐进式披露

### 速查卡（30 秒上手）

```
1. 放文件 → 2. 试运行 1 个 → 3. 备份 → 4. 批量跑 → 5. 抽查校验
```

### 分层次阅读路径

#### 新手路径（首次使用）

1. 阅读「能力边界」了解工具能做什么。
2. 按「标准流程」的步骤 1~2 完成一次试运行。
3. 遇到问题查「错误码体系」对照处理。

#### 进阶路径（熟练用户）

1. 深入理解「置信度门控」规则，建立自己的校验标准。
2. 参考「FAQ 反模式」优化工作流，避免常见坑。
3. 结合 `技能编排` 设计多步骤自动化流程，提升效率。

---

## 用户协议

使用本 Skill 即表示您同意以下条款：

1. **责任承担**：使用者自行承担使用本 Skill 产生的全部责任。因使用、误用或依赖本 Skill 导致的任何直接或间接损失，作者不承担任何责任。
2. **禁止反向工程**：不得对本 Skill 进行反向工程、反编译、破解或试图提取底层算法与逻辑。
3. **合规使用**：使用者应确保使用场景符合当地法律法规及所在组织的政策要求。
4. **无担保声明**：本 Skill 按"现状"提供，不附带任何明示或暗示的担保。

<!-- user-agreement-injected -->

---

## 许可证（License）

MIT License

Copyright (c) 2024 林墨

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

<!-- professional-license-embedded -->
