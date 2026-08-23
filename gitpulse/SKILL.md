---
slug: gitpulse
name: gitpulse
displayName: Git代码管理 操作指引 流程规范
description: 提供Git代码管理操作的结构化处理流程与规范化输出指引。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: FlowForge
agent_created: true
trigger_words: ["gitpulse", "Git代码管理", "git操作", "代码仓库管理", "版本控制"]
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# GitPulse 技能文档

## 一、能力边界速查卡

### 能处理的事项

| 编号 | 能力项 | 说明 | 输入示例 |
|------|--------|------|----------|
| 1 | 数据转结构化 | 将用户提供的文本、文件路径或URL内容解析为规范字段 | 一段git log输出文本 |
| 2 | 关键信息提取 | 从原始材料中识别提交哈希、分支名、作者、时间戳等要素 | 混合格式的提交记录 |
| 3 | 规范格式输出 | 按预定义模板生成Markdown表格、JSON或纯文本报告 | 生成变更汇总表 |
| 4 | 置信度标注 | 对推断字段或模糊匹配结果附加可信度标记 | 作者名拼写不确定时 |
| 5 | 批量处理 | 支持多文件、多URL的循环处理与结果合并 | 一次分析10个仓库的日志 |

### 不处理的事项

- 不执行任何实际的 git 命令，仅做信息整理与格式转换
- 不修改用户仓库内容，不推送、不合并、不回滚
- 不替代代码审查，不判断代码质量
- 不处理二进制文件内容解析
- 不提供安全审计或漏洞扫描结论

### 适用对象

- 需要快速整理 Git 提交记录的开发者
- 需要将 git 输出转为报告格式的团队助理
- 需要批量汇总多仓库状态的项目管理员

---

## 二、触发方式与场景映射

当对话中出现以下意图时，本技能自动激活：

| 用户可能说的话 | 触发词命中 | 实际响应行为 |
|---------------|-----------|-------------|
| "帮我把这次提交记录整理成表格" | gitpulse, Git代码管理 | 解析提交文本，输出结构化表格 |
| "这个URL里的git日志帮我分析下" | git操作 | 抓取URL内容，提取关键字段 |
| "我有三个仓库的log文件，汇总一下" | 批量处理 | 逐一解析并合并输出 |
| "这个提交记录里谁改了什么不太清楚" | 版本控制 | 提取作者、文件、提交说明并标注置信度 |
| "gitpulse --selftest" | gitpulse | 执行自检流程，返回能力状态 |

---

## 三、标准处理流程

### 前置条件

1. 输入材料可读：文本内容非空，文件路径存在，URL可访问
2. 编码格式明确：UTF-8 优先，其他编码需提前声明
3. 命名规范：批量处理时文件名建议包含日期或仓库名，便于结果对应

### 执行步骤

**步骤 1：输入接收与解析**

- 接收用户提供的文本、文件路径或URL
- 识别内容类型：提交日志、分支列表、标签信息、状态快照
- 若为URL，先抓取内容再解析；若为文件，读取后解析

**步骤 2：关键字段提取**

按以下规则提取信息：

| 字段名 | 提取规则 | 示例 |
|--------|----------|------|
| commit_hash | 匹配 7-40 位十六进制字符 | `a1b2c3d` |
| author | 匹配 `Author:` 行或 `by xxx` 模式 | `zhangsan` |
| timestamp | 匹配 ISO 8601 或 `YYYY-MM-DD HH:MM` 格式 | `2025-03-15 14:30` |
| message | 提交说明首行，截取前 80 字符 | `fix: 修复登录超时问题` |
| branch | 匹配 `branch` 或 `on xxx` 模式 | `feature/login` |

**步骤 3：置信度标注**

- 字段值完全匹配 → 置信度 `high`
- 字段值存在但格式不规范 → 置信度 `medium`
- 字段值缺失或需推断 → 置信度 `low`，并输出 `[需核实:字段名]` 占位

**步骤 4：结果组装与输出**

- 默认输出 Markdown 表格
- 可选输出格式：JSON、CSV、纯文本列表
- 输出前自查：字段完整性、格式正确性、置信度标注是否齐全

**步骤 5：二次确认**

- 若关键字段缺失超过 30%，主动向用户确认输入来源
- 若批量处理中某个文件解析失败，单独标记并继续处理其余文件

### 输出规范

```markdown
| commit_hash | author | timestamp | message | confidence |
|------------|--------|-----------|---------|------------|
| a1b2c3d | zhangsan | 2025-03-15 14:30 | fix: 修复登录超时问题 | high |
| e4f5a6b | lisi | 2025-03-14 09:12 | [需核实:message] | low |
```

---

## 四、置信度门控机制

当遇到以下情况时，**不编造信息**，直接输出占位符：

| 场景 | 处理方式 |
|------|----------|
| 提交说明为空 | 输出 `[需核实:message]` |
| 作者名拼写模糊 | 输出 `[需核实:author]`，置信度 `low` |
| 时间格式无法解析 | 输出 `[需核实:timestamp]`，保留原始字符串 |
| 分支信息缺失 | 输出 `[需核实:branch]`，不猜测分支名 |

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| GP-100 | 输入为空 | "未检测到可解析的内容，请提供文本、文件路径或URL" | 请用户补充输入 |
| GP-200 | 文件不存在 | "指定的文件路径无法访问，请确认路径是否正确" | 检查路径，重新输入 |
| GP-300 | URL不可达 | "目标URL无法访问，请检查网络或链接有效性" | 确认URL后重试 |
| GP-400 | 格式无法识别 | "输入内容不符合已知的git输出格式，请确认来源" | 提供样本格式说明 |
| GP-500 | 批量处理中断 | "批量处理在第 N 个文件处中断，已跳过该文件" | 单独处理失败文件 |

---

## 六、常见坑与反模式对照

| 常见错误做法 | 问题说明 | 推荐做法 |
|-------------|----------|----------|
| 直接复制粘贴整个 git log 不做预处理 | 大量无关信息干扰提取 | 先过滤出 `commit`、`Author`、`Date` 行 |
| 忽略编码问题直接解析 | 中文乱码导致作者名或提交说明解析失败 | 先确认编码，统一转为 UTF-8 |
| 批量处理时不保留原始文件 | 解析出错后无法回溯 | 每次处理前备份原始文件到 `backup/` 目录 |
| 对缺失字段自行猜测 | 产生错误信息并误导后续使用 | 使用 `[需核实:字段]` 占位，交由用户确认 |
| 输出格式随意变化 | 下游脚本或人工阅读难以适配 | 固定使用 Markdown 表格或约定的 JSON schema |

---

## 七、渐进式阅读路径

### 新手路径（首次使用）

1. 阅读「能力边界速查卡」了解能做什么
2. 查看「触发方式与场景映射」确认使用场景
3. 按「标准处理流程」的步骤 1-3 操作一次
4. 遇到问题查「错误码体系」

### 进阶路径（批量或复杂场景）

1. 熟悉「置信度门控机制」，理解占位符含义
2. 使用「标准处理流程」的步骤 4-5 进行批量处理
3. 参考「常见坑与反模式对照」规避典型错误
4. 自定义输出格式时，保持字段名与置信度标注不变

---

## 八、参数配置参考

| 参数名 | 默认值 | 可选值 | 说明 |
|--------|--------|--------|------|
| output_format | markdown | json, csv, text | 输出格式 |
| max_message_length | 80 | 20-200 | 提交说明截断长度 |
| confidence_threshold | low | low, medium, high | 低于此置信度的字段强制占位 |
| batch_size | 10 | 1-50 | 批量处理时每批文件数 |

---

## 用户协议

使用本 Skill 即表示您同意以下条款：

1. **责任承担**：使用者自行承担因使用本 Skill 产生的全部责任。本 Skill 仅提供信息整理与格式转换功能，不构成任何形式的专业建议或保证。
2. **禁止反向工程**：不得对本 Skill 的提示词、内部逻辑进行反向工程、破解、提取或二次分发。
3. **合规使用**：使用者应确保输入数据的合法性与合规性，不得使用本 Skill 处理违法违规内容。
4. **无担保声明**：本 Skill 按"现状"提供，不附带任何明示或暗示的担保。

<!-- user-agreement-injected -->

---

## 许可证（License）

本 Skill 采用 MIT 许可证授权：

```
MIT License

Copyright (c) 2025 原创作者（自持版权）

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
