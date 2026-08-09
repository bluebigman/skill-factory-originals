---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: autozest
name: autozest
displayName: 自动化测试 环境配置 结果校验
description: 自动配置测试环境并生成结构化测试结果报告。
version: 1.0.1
rules_version: cpr-20260809-n251
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/autozest
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 林默
agent_created: true
trigger_words: ["autozest", "自动化测试", "测试环境配置", "测试结果生成", "autotest", "growl"]
---

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->


> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# AutoZest 技能手册

## 一、能力边界速查卡

本技能用于辅助完成自动化测试环境的准备、配置检查以及测试结果的规范化整理。它不是一个测试执行引擎，也不替代任何具体测试框架。

| 维度 | 说明 |
|------|------|
| **核心用途** | 将用户提供的测试环境信息、配置文件内容或相关URL，转化为结构化的环境检查清单与测试结果摘要 |
| **输入来源** | 用户粘贴的文本、上传的配置文件（如 `.autotest`）、指向配置仓库的URL |
| **输出格式** | Markdown 表格 + 键值对清单，包含字段完整性检查与置信度标注 |
| **处理上限** | 单次处理不超过 200 行配置或 50 个键值对；超出部分需分批处理 |
| **关键保留项** | 所有涉及路径、端口、服务名称、版本号的信息必须原样保留，不做推断修改 |

### 能做与不能做

**能做：**
1. 解析 `.autotest` 文件内容，提取其中的配置项（如通知方式、监听目录、测试命令）。
2. 识别配置中缺失的必填项，并给出补全建议。
3. 将散乱的测试输出整理为统一的摘要表格。
4. 对配置项的值进行格式校验（如端口号是否为数字、路径是否存在）。
5. 批量处理多个配置文件，生成对比差异报告。

**不能做：**
1. 不能实际执行测试用例或运行测试套件。
2. 不能安装、卸载或修改系统中的任何软件（如 growl）。
3. 不能访问未授权的外部网络资源。
4. 不能判断测试结果的业务正确性，仅能校验格式与完整性。
5. 不能处理加密或二进制格式的配置文件。

**适用对象：** 需要快速梳理测试环境配置的开发者、负责持续集成配置的运维人员、以及需要将测试结果文档化的技术写作者。

---

## 二、触发方式与场景映射

当你的请求中包含以下关键词或意图时，本技能将被激活：

| 触发词/短语 | 典型用户表述 | 技能响应动作 |
|-------------|-------------|-------------|
| autozest | “用 autozest 帮我看看这个配置” | 启动配置解析流程 |
| 自动化测试配置 | “帮我整理一下自动化测试的环境配置” | 提取配置项并结构化 |
| 测试结果整理 | “把这次测试的输出整理成报告” | 格式化测试输出 |
| 环境检查 | “检查一下我的 autotest 配置缺什么” | 执行完整性校验 |
| growl 配置 | “growl 的通知设置应该怎么写” | 解析通知相关配置段 |

**场景示例：**
- 你有一个 `.autotest` 文件，希望知道其中是否包含了 growl 通知的必需参数。
- 你从 CI 系统拿到一份测试日志，需要提取关键字段生成摘要。
- 你想对比两个版本的配置文件差异。

---

## 三、标准处理流程

### 前置条件

- 输入内容为 UTF-8 编码的纯文本或 Markdown 格式。
- 若提供 URL，需为可公开访问的文本文件地址。
- 配置文件的键值对使用 `key = value` 或 `key: value` 的格式。

### 执行步骤

**步骤 1：输入接收与格式确认**

接收用户输入，判断其类型（文本/文件/URL）。若为 URL，尝试获取内容并转为文本。若输入为空或格式无法识别，返回错误码 `E1001`。

**步骤 2：配置项提取**

按以下规则解析文本：
- 行首为 `#` 或 `//` 的视为注释，跳过。
- 匹配 `key = value` 或 `key: value` 模式，提取键值对。
- 值中的引号（单引号或双引号）将被去除，但保留内部空格。
- 若同一键出现多次，以最后一次为准，并在结果中标注“重复定义”。

**步骤 3：完整性校验**

对照内置的常用配置项清单（见下表），检查必填项是否齐全。

| 配置项 | 必填 | 格式要求 | 示例 |
|--------|------|---------|------|
| `notify` | 是 | 布尔值（true/false） | `notify = true` |
| `growl_path` | 否 | 绝对路径 | `growl_path = /usr/local/bin/growlnotify` |
| `watch_dir` | 是 | 存在的目录路径 | `watch_dir = ./spec` |
| `test_command` | 是 | 非空字符串 | `test_command = bundle exec rspec` |
| `timeout` | 否 | 正整数（秒） | `timeout = 300` |

**步骤 4：结果生成与置信度标注**

- 对每个提取的配置项，标注其来源（原始文本/推断/缺失）。
- 若某必填项缺失，输出 `[需核实:配置项名称]` 占位符，不进行猜测。
- 若值格式不符合要求，在结果中标记“格式存疑”，并附上正确格式示例。

**步骤 5：输出与自查**

将结果整理为 Markdown 表格，包含以下列：配置项、值、来源、状态、置信度。自查字段完整性、格式正确性、置信度标注是否齐全。若存在不确定项，在文档末尾列出“待确认清单”。

### 输出规范

输出文档结构如下：

```markdown
# 配置解析报告

## 摘要
（总体情况说明，包括解析的配置项总数、缺失项数量）

## 配置明细
| 配置项 | 值 | 来源 | 状态 | 置信度 |
|--------|-----|------|------|--------|
| ... | ... | ... | ... | ... |

## 待确认清单
- [ ] 配置项A：缺失，需用户提供
- [ ] 配置项B：格式存疑，需确认

## 处理日志
（简要记录处理过程中的异常或跳过项）
```

---

## 四、置信度门控机制

本技能遵循“不编造”原则。在以下情况中，输出将包含明确的占位符：

| 场景 | 处理方式 | 输出示例 |
|------|---------|---------|
| 必填配置项缺失 | 输出 `[需核实:配置项名称]` | `[需核实:watch_dir]` |
| 值格式无法判断 | 保留原值，标注“格式存疑” | `值: "abc" (格式存疑)` |
| URL 内容获取失败 | 返回错误码 `E2001`，不进行后续解析 | 错误信息 + 正确 URL 示例 |
| 配置项含义不明 | 标注“语义未知”，建议用户确认 | `值: "xyz" (语义未知)` |

置信度分为三级：
- **高**：配置项来自原始输入，格式校验通过。
- **中**：配置项来自原始输入，但格式存在疑点，或为重复定义。
- **低**：配置项为推断得出，或来自不完整的上下文。

---

## 五、错误码体系

| 错误码 | 含义 | 用户提示话术 | 修正步骤 |
|--------|------|-------------|---------|
| `E1001` | 输入为空或格式无法识别 | “未检测到有效的配置内容。请提供文本、文件内容或可访问的URL。” | 1. 检查输入是否为纯文本；2. 确认文件编码为 UTF-8；3. 重新提交。 |
| `E1002` | 配置项格式不符合 `key = value` 规范 | “存在无法解析的行，已跳过。请检查以下行：{行内容}” | 1. 修正格式；2. 移除多余符号；3. 重新解析。 |
| `E2001` | URL 无法访问或内容为空 | “无法从该URL获取内容。请确认链接可公开访问。” | 1. 检查URL拼写；2. 尝试在浏览器中打开；3. 更换为文本粘贴。 |
| `E3001` | 输入超出单次处理上限（200行） | “输入内容过长，请分批提交或精简后重试。” | 1. 截取前200行；2. 或拆分文件；3. 重新提交。 |
| `E4001` | 内部处理异常 | “处理过程中出现意外错误，请重试或简化输入。” | 1. 重新提交；2. 若反复失败，检查输入中是否包含特殊字符。 |

---

## 六、FAQ 与反模式对照

### 常见坑 1：忽略注释行中的配置信息

- **错误做法**：将注释行中的示例配置当作有效配置提取。
- **正确做法**：注释行仅作参考，不参与结构化输出。若用户需要，可在“处理日志”中注明“注释中发现疑似配置示例”。

### 常见坑 2：对缺失值进行猜测

- **错误做法**：当 `watch_dir` 缺失时，默认填入 `./spec`。
- **正确做法**：输出 `[需核实:watch_dir]`，并在待确认清单中提示用户补全。

### 常见坑 3：混淆布尔值与字符串

- **错误做法**：将 `notify = "false"` 视为字符串，而非布尔值。
- **正确做法**：识别 `true`/`false` 为布尔类型，若加了引号则标记“格式存疑”。

### 常见坑 4：重复键值静默覆盖

- **错误做法**：直接取最后一个值，不告知用户。
- **正确做法**：在结果中保留最后一次的值，但在“处理日志”中记录“键 `xxx` 重复定义，已采用最后值”。

### 常见坑 5：URL 内容与预期不符

- **错误做法**：URL 返回的是 HTML 页面，仍按纯文本解析。
- **正确做法**：检测到 HTML 标签时，返回错误码 `E2001`，并提示“URL 内容不是纯文本格式”。

---

## 七、渐进式阅读路径

### 速查卡（30秒上手）

1. 粘贴你的 `.autotest` 文件内容。
2. 技能自动提取配置项并检查完整性。
3. 查看输出表格，关注“状态”列中标记为“缺失”或“存疑”的项。
4. 根据“待确认清单”补全信息。

### 新手路径（首次使用）

- 阅读「能力边界速查卡」了解适用范围。
- 按「标准处理流程」的步骤 1-3 准备输入。
- 查看「错误码体系」应对常见问题。

### 进阶路径（深度使用）

- 研究「置信度门控机制」，理解不同置信度的含义。
- 参考「FAQ 与反模式对照」避免处理陷阱。
- 结合「输出规范」自定义报告格式（需在输入中注明格式偏好）。

---

## 八、用户协议

使用本 Skill 即表示您同意以下条款：

1. **责任承担**：使用者应自行承担使用本 Skill 的全部责任。因使用本 Skill 产生的任何直接或间接损失，技能作者及发布平台不承担任何责任。
2. **禁止反向工程**：不得对本 Skill 的提示词、内部逻辑进行反向工程、破解、提取或用于训练竞争模型。
3. **合规使用**：使用者应确保输入内容不违反法律法规，不包含敏感个人信息或受版权保护的第三方内容。
4. **修改与分发**：在保留本协议及版权声明的前提下，允许修改和再分发本 Skill。
5. **无担保声明**：本 Skill 按“现状”提供，不附带任何明示或暗示的担保。

<!-- user-agreement-injected -->

---

## 九、许可证（License）

本 Skill 采用 MIT 许可证授权。

```
MIT License

Copyright (c) 2026 林默

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
