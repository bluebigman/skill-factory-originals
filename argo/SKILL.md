---
slug: argo
name: argo
displayName: 源码审计 弱点定位 安全扫描
description: 阅读源码定位潜在安全弱点，输出风险分级与修复建议。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: CodeSentry
agent_created: true
trigger_words: ["argo", "漏洞扫描", "代码审计", "安全检测", "静态分析", "源码弱点", "安全审查"]
---

> 本内容由 AI 生成，仅供学习参考 <!-- ai-generated-notice -->

# argo — 源码弱点审计 Skill

## 一、能力边界（一页纸速查卡）

| 维度 | 说明 |
|------|------|
| **核心能力** | 对指定目录下的源码进行静态弱点扫描，识别潜在安全风险（如注入、硬编码密钥、危险函数调用、不安全的反序列化等），并按风险等级输出报告。 |
| **输入** | 一个本地项目目录路径（支持主流语言项目结构，如 Python/JavaScript/Java/Go 等）。 |
| **输出** | 结构化扫描报告：风险等级（高/中/低/信息）、风险描述、涉及文件与行号、修复建议、整体 summary 与 next_steps。 |
| **能做** | 识别常见弱点模式；对风险进行分级排序；给出修复方向；支持自定义规则（进阶）；支持 CI/CD 集成（进阶）。 |
| **不能做** | 不执行动态运行分析；不保证覆盖所有漏洞类型；不替代人工代码审查；不提供漏洞利用验证（PoC）；不保证扫描结果无遗漏。 |
| **适用对象** | 开发人员、安全工程师、DevOps 人员，以及需要在开发流程中快速建立安全基线的小型团队。 |
| **不适用场景** | 需要深度数据流追踪的复杂漏洞分析、需要运行时上下文的安全验证、大型遗留系统的全量合规审计。 |

---

## 二、触发方式

### 触发词

`argo`、`漏洞扫描`、`代码审计`、`安全检测`、`静态分析`、`源码弱点`、`安全审查`

### 场景映射表

| 你说的话（大白话） | 实际触发动作 |
|-------------------|-------------|
| "帮我看看这个项目有没有安全问题" | 执行 `argo 漏洞扫描 /path/to/project` |
| "这个代码库需要做一次安全体检" | 同上，默认参数扫描 |
| "检查一下这段代码有没有常见漏洞" | 同上，聚焦高风险项 |
| "我想把安全扫描加到 CI 里" | 参考「进阶路径」中的 CI/CD 集成指引 |
| "这个项目安全状况怎么样？" | 执行扫描后查看 summary 与风险分布 |

---

## 三、标准流程

### 前置条件

- 目标目录存在且包含可识别的源码文件（非空目录）。
- 当前环境具备读取目标目录的权限。
- 若项目较大（超过 10 万行代码），建议先扫描子模块或指定目录。

### 执行步骤

1. **启动扫描**：输入命令 `argo 漏洞扫描 /path/to/project`。
2. **等待完成**：扫描过程通常需要数秒至数分钟，取决于项目规模与文件数量。
3. **查看 summary**：扫描完成后，先阅读报告顶部的 summary 部分，了解整体风险分布（高风险数量、中风险数量等）。
4. **优先处理高风险项**：从 `high` 等级的风险项开始，逐项确认是否真实存在，并参考修复建议进行处理。
5. **查看 next_steps**：根据报告末尾的 next_steps 获取后续行动建议（如补充规则、调整配置、人工复核等）。

### 输出规范

| 字段 | 说明 | 示例 |
|------|------|------|
| `risk_level` | 风险等级：`high` / `medium` / `low` / `info` | `high` |
| `vuln_type` | 弱点类型 | `hardcoded_secret` |
| `file` | 涉及文件路径 | `src/config.py` |
| `line` | 行号 | `42` |
| `description` | 弱点描述 | 检测到疑似硬编码的 API 密钥 |
| `suggestion` | 修复建议 | 将密钥移至环境变量或密钥管理服务 |
| `confidence` | 置信度：`high` / `medium` / `low` | `medium` |
| `summary` | 整体统计 | `{"high": 3, "medium": 5, "low": 12, "info": 8}` |
| `next_steps` | 后续建议列表 | `["人工复核 high 级项", "补充自定义规则"]` |

---

## 四、置信度门控

当扫描结果信息不足或无法确认时，报告会使用 `[需核实:字段]` 占位符，不会编造数据。常见情形：

- 文件无法读取时：`[需核实:file_content]`
- 行号无法精确定位时：`[需核实:line_number]`
- 弱点类型不确定时：`[需核实:vuln_type]`
- 修复建议无法给出时：`[需核实:suggestion]`

遇到上述占位符时，请结合人工审查确认实际情况。

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|---------|---------|
| `E001` | 目标目录不存在 | 未找到指定路径，请确认目录是否存在 | 检查路径拼写，确认目录存在后重试 |
| `E002` | 目录为空或无源码文件 | 目标目录中没有可识别的源码文件 | 确认目录内容，或更换为源码所在子目录 |
| `E003` | 权限不足 | 无法读取目标目录，请检查权限 | 使用 `chmod` 或 `sudo` 调整权限后重试 |
| `E004` | 扫描超时 | 扫描超时，项目规模可能过大 | 拆分为子目录扫描，或使用 `--timeout` 参数调整 |
| `E005` | 规则加载失败 | 自定义规则文件格式错误 | 检查规则文件语法，参考规则模板修正 |
| `E006` | 输出写入失败 | 无法写入报告文件 | 检查输出路径权限，或更换输出目录 |

---

## 六、FAQ 反模式

| 常见坑 | 反模式（错误做法） | 正确做法 |
|--------|-------------------|---------|
| 误报处理 | 直接忽略所有 `low` 级结果 | 对 `low` 级结果进行抽样复核，确认是否为误报 |
| 扫描范围 | 一次性扫描整个大型仓库 | 分模块扫描，先扫核心业务代码 |
| 结果依赖 | 仅凭扫描结果就上线发布 | 结合人工审查与测试，自动化结果仅作参考 |
| 规则定制 | 随意修改规则导致大量误报 | 小步调整，每次改动后对比扫描结果 |
| 修复验证 | 修复后不重新扫描 | 修复后重新扫描，确认风险项已消除 |

---

## 七、渐进式披露

### 速查卡（30 秒上手）

```
argo 漏洞扫描 /path/to/project
→ 查看 summary
→ 处理 high 级项
→ 查看 next_steps
```

### 新手路径

1. 阅读「能力边界」了解工具能做什么、不能做什么。
2. 选一个小型项目（如个人练习项目）执行首次扫描。
3. 对照「输出规范」理解每个字段的含义。
4. 从高风险项开始，逐项确认并修复。
5. 将扫描纳入日常开发流程（如每次提交前扫描）。

### 进阶路径

1. **定制扫描规则**：根据项目技术栈和业务特点，编写自定义规则（如特定框架的已知危险函数）。
2. **集成 CI/CD**：将扫描命令加入 CI 流水线，在每次构建时自动执行，并设置高风险项阻断发布。
3. **深度分析**：结合调用链分析工具，追踪数据流，验证扫描结果是否为真实可利用的漏洞。
4. **建立安全基线**：为项目设定可接受的风险阈值，跟踪每次扫描的风险变化趋势。
5. **团队推广**：基于扫描结果制定团队安全编码规范，将常见问题写入开发文档。

---

## 八、用户协议

使用本 Skill 即表示您同意以下条款：

1. **责任承担**：使用者自行承担因使用本 Skill 产生的全部责任。本 Skill 提供的分析结果仅供参考，不构成任何形式的安全保证。
2. **结果解释**：扫描结果可能存在误报或漏报，使用者应结合实际情况进行人工复核，不应仅依赖自动化结果做出关键决策。
3. **禁止反向工程**：禁止对本 Skill 的规则库、算法逻辑进行反向工程、反编译或提取核心逻辑用于商业用途。
4. **合规使用**：使用者应确保使用本 Skill 的行为符合当地法律法规及所在组织的安全政策。
5. **免责声明**：本 Skill 不提供任何形式的明示或暗示担保，包括但不限于适销性、特定用途适用性。

<!-- user-agreement-injected -->

---

## 九、许可证（License）

本 Skill 采用 MIT 许可证发布。

```
MIT License

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
```

<!-- professional-license-embedded -->
