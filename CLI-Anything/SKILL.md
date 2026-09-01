---
slug: CLI-Anything
name: 自然语言转命令工具
displayName: 终端指令 中文转译 命令生成
description: 将中文操作意图精准转译为可执行命令行，内置命令库检索与结构化输出。
version: 1.0.0
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/CLI-Anything
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: LinguaTerm
agent_created: true
trigger_words: ["自然语言转命令", "CLI生成", "命令翻译", "终端指令转换", "命令行助手", "命令查询", "终端命令", "shell翻译"]
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# 自然语言转命令工具（CLI-Anything）

## 一、能力边界：一页纸速查卡

### 1.1 能做什么

| 能力项 | 说明 | 示例 |
|--------|------|------|
| 中文意图转命令 | 将自然语言描述转换为对应 shell 命令 | "查看当前目录所有文件" → `ls -la` |
| 命令库检索 | 内置常见命令库，支持模糊匹配 | "压缩这个文件夹" → `tar -czvf archive.tar.gz ./folder` |
| 参数补全建议 | 为命令补充常用参数 | "删除文件" → `rm -i file`（提示 `-i` 交互确认） |
| 多平台适配 | 区分 Linux/macOS/Windows 差异 | "查看IP" → Linux: `ip addr` / macOS: `ifconfig` / Win: `ipconfig` |
| 结构化输出 | 以 JSON 格式返回命令、说明、风险等级 | 见 4.3 输出规范 |

### 1.2 不能做什么

| 限制项 | 说明 |
|--------|------|
| 不执行命令 | 仅生成命令文本，不实际运行 |
| 不处理敏感操作 | 涉及 `rm -rf /`、`mkfs` 等破坏性命令时，仅输出警告并建议人工确认 |
| 不保证跨平台一致 | 部分命令在不同 shell（bash/zsh/powershell）中语法有差异，需用户自行确认环境 |
| 不覆盖所有命令 | 仅覆盖常用命令库（约 200+ 条），超出范围时返回 `[需核实:命令不存在]` |

### 1.3 适用对象

- **终端初学者**：不熟悉命令语法，需要中文引导
- **日常开发者**：偶尔忘记命令参数，需要快速检索
- **运维人员**：需要批量生成命令模板，减少重复输入

---

## 二、触发方式

### 2.1 触发词

直接使用以下任一触发词即可激活：

- 自然语言转命令
- CLI生成
- 命令翻译
- 终端指令转换
- 命令行助手
- 命令查询
- 终端命令
- shell翻译

### 2.2 场景映射表

| 用户说（大白话） | 触发词匹配 | 实际意图 |
|------------------|------------|----------|
| "帮我看看这个文件夹里有什么" | 命令翻译 | 列出目录内容 |
| "怎么把那个文件压缩一下" | 终端指令转换 | 压缩文件/目录 |
| "查一下当前系统的网络配置" | 命令行助手 | 查看网络接口信息 |
| "我想批量改文件名" | 命令查询 | 批量重命名操作 |
| "这个端口被占用了怎么办" | 终端命令 | 查找占用端口的进程 |

---

## 三、标准流程

### 3.1 前置条件

- 输入：用户提供中文操作意图（一句话或一段描述）
- 环境：无需特殊环境，纯文本交互
- 可选参数：`--selftest`（自检）、`--version`（版本信息）

### 3.2 执行步骤

**步骤 1：意图解析**
- 提取核心动词（如：查看、创建、删除、压缩、查找）
- 提取操作对象（如：文件、目录、进程、端口、网络）
- 提取附加条件（如：递归、强制、后台运行）

**步骤 2：命令库匹配**
- 在预置命令库中检索匹配项
- 若匹配失败，尝试组合命令或给出近似建议

**步骤 3：参数补全与安全检查**
- 根据意图补充默认参数（如 `ls` 补 `-l`）
- 检测危险命令（`rm`、`dd`、`mkfs` 等），附加风险提示

**步骤 4：结构化输出**
- 按 4.3 节格式输出 JSON

**步骤 5：下一步建议**
- 提供 1-2 条后续操作建议（如："如需递归删除请添加 `-r` 参数"）

### 3.3 输出规范

```json
{
  "query": "查看当前目录所有文件",
  "command": "ls -la",
  "platform": ["linux", "macos"],
  "risk_level": "low",
  "description": "列出当前目录下所有文件（含隐藏文件）的详细信息",
  "alternatives": [
    {"command": "ls -l", "note": "仅显示非隐藏文件的详细信息"},
    {"command": "tree", "note": "以树状结构显示目录层级（需安装）"}
  ],
  "next_steps": ["如需查看子目录内容，可添加 -R 参数"]
}
```

---

## 四、置信度门控

### 4.1 信息不足时的处理

当输入信息不足以确定唯一命令时，使用 `[需核实:字段]` 占位，不编造：

| 场景 | 输出示例 |
|------|----------|
| 未指定操作系统 | `[需核实:操作系统]` 请确认是 Linux/macOS/Windows |
| 未指定文件类型 | `[需核实:文件类型]` 压缩的是文件夹还是单个文件？ |
| 命令不在库中 | `[需核实:命令不存在]` 未找到匹配命令，请补充更多上下文 |

### 4.2 置信度分级

| 置信度 | 判定条件 | 输出策略 |
|--------|----------|----------|
| 高（≥90%） | 意图明确，命令唯一 | 直接输出命令 |
| 中（70-89%） | 存在多个候选命令 | 输出主命令 + 备选列表 |
| 低（<70%） | 意图模糊或命令缺失 | 输出占位符 + 追问提示 |

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| `E001` | 输入为空 | "未检测到操作意图，请输入您想执行的命令描述" | 重新输入包含动词和对象的描述 |
| `E002` | 意图不明确 | "无法确定具体操作，请补充操作对象（如：文件、目录、进程）" | 添加操作对象关键词 |
| `E003` | 命令不存在 | "未找到匹配命令，请检查拼写或尝试换一种描述方式" | 使用更通用的词汇（如"删除"→"移除"） |
| `E004` | 危险操作 | "检测到高危命令，请确认是否继续（建议先备份数据）" | 确认后添加 `--force` 参数，或改用安全替代方案 |
| `E005` | 平台不支持 | "该命令在您指定的平台上不可用" | 切换平台参数或使用跨平台替代命令 |

---

## 六、FAQ 反模式

### 6.1 常见坑

| 坑 | 反模式示例 | 正确做法 |
|----|------------|----------|
| 忽略平台差异 | 直接给 `apt-get`（仅 Debian/Ubuntu） | 先确认系统类型，再给出对应包管理器命令 |
| 过度简化参数 | 只给 `rm file` 不给 `-i` 提示 | 默认添加交互确认参数，降低误删风险 |
| 不检查命令存在性 | 直接输出 `tree` 但系统未安装 | 提示"该命令可能需要额外安装" |
| 忽略权限要求 | 直接给 `chmod 777` 不说明风险 | 建议使用最小权限（如 `chmod 644`）并说明原因 |
| 混合 shell 语法 | 在 PowerShell 中输出 bash 语法 | 根据用户环境输出对应 shell 语法 |

### 6.2 反模式对照表

| 反模式 | 问题 | 替代方案 |
|--------|------|----------|
| 输出超长命令链 | 用户难以理解，易出错 | 拆分为多条命令，逐步执行 |
| 直接给破坏性命令 | 数据丢失风险 | 先给安全版本，再提示危险版本 |
| 忽略管道符使用 | 无法组合命令 | 提供管道组合示例（如 `ps aux \| grep nginx`） |

---

## 七、渐进式披露

### 7.1 速查卡（新手路径）

1. 输入你的操作意图（一句话即可）
2. 获取命令 + 说明
3. 复制命令到终端执行

### 7.2 进阶路径（有经验用户）

1. 使用 `--selftest` 检查技能完整性
2. 使用 `--version` 查看版本
3. 直接输入包含多个条件的描述（如"递归删除所有 .log 文件"）
4. 使用 `alternatives` 字段获取多个候选命令
5. 结合 `next_steps` 建议进行命令组合

### 7.3 深度定制

- 可通过修改命令库 JSON 文件扩展命令范围
- 支持自定义平台别名（如 `mac` → `macos`）
- 可添加企业内网专用命令

---

## 八、用户协议

<!-- user-agreement-injected -->

**使用本 Skill 即表示您同意以下条款：**

1. **责任承担**：使用者自行承担全部责任。本 Skill 生成的命令仅供参考，执行前请务必理解命令含义并确认环境适配性。因使用本 Skill 生成的命令导致的任何直接或间接损失，作者不承担任何责任。

2. **禁止反向工程**：未经授权，不得对本 Skill 的底层逻辑、命令库结构进行反向工程、反编译或试图提取源代码。

3. **合规使用**：不得使用本 Skill 生成违反法律法规、侵犯他人权益的命令。

4. **修改与分发**：允许在保留版权声明的前提下修改和分发，但需注明原始出处。

---

## 九、许可证（License）

<!-- professional-license-embedded -->

**MIT License**

Copyright (c) 2024 LinguaTerm

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
