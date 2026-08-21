---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: deepseek-harness-runner
name: deepseek-harness-runner
displayName: 智能体任务执行 批量自动化 会话留痕
description: 驱动 DeepSeek Agent 运行时 dsh 执行真实任务，支持队列、会话、报告与 MCP 扩展。
version: 2.0.1
rules_version: cpr-20260821-n626
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/deepseek-harness-runner
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: AgentForge Lab
agent_created: true
trigger_words: ["跑 dsh", "跑 harness", "harness 任务", "让模型动手干活", "dsh 执行", "执行任务队列", "批量跑任务", "会话导出"]

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

---

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->


# DeepSeek Harness Runner — 技能文档

## 一、能力边界（一页纸速查卡）

### 1.1 能做什么

| 能力项 | 说明 | 对应命令/参数 |
|--------|------|----------------|
| 环境自检 | 检查 API Key、CLI 可用性、版本号、DSH_HOME 路径 | `python dsh_run.py --check` |
| 任务预览 | 不实际执行，仅展示任务描述与预期动作 | `python dsh_run.py "任务" --dry-run` |
| 单任务执行 | 让模型读写文件、运行命令、多步推理 | `python dsh_run.py "任务描述"` |
| 参数化控制 | 指定模型、超时时间、权限模式、详细输出 | `--model` / `--timeout` / `--permission` / `--verbose` |
| 任务队列 | 批量添加、查看、执行、清空任务 | `--queue-add` / `--queue-list` / `--queue-run` / `--queue-clear` |
| 批量文件任务 | 从 JSON 文件批量导入任务 | `--batch tasks.json` |
| 会话管理 | 查看历史会话、导出执行记录 | `--session-list` / `--session-export` |
| MCP 配置辅助 | 一键生成外接工具配置模板 | `--mcp-init` |
| JSON 报告输出 | 结构化输出执行结果，供程序消费 | `--report` |
| 自测契约 | 8 项断言验证核心函数 | `--selftest` |
| 多编码容错 | 自动处理 utf-8 / gbk / gb18030 编码文件 | 内置自动 fallback |
| 权限模式控制 | 三档权限：workspace-write / full / readonly | `--permission` |

### 1.2 不能做什么

| 限制项 | 说明 |
|--------|------|
| 跨调用会话续接 | headless 模式为单任务执行，跨调用续接需 TS SDK 模式 |
| Windows 原生支持 | Python SDK 不支持 Windows，需 Node 环境（脚本自动检测） |
| 版本兼容保证 | dsh 处于 developer preview 阶段，升级可能破坏兼容（内置 cordis.yml 自动重建） |
| 绝对正确性保证 | 模型执行结果需人工核验，读写一致才算通过 |

### 1.3 适用对象

- 需要 AI 真正动手执行任务（读写文件、跑命令）而非仅给建议的用户
- 需要批量处理和自动化能力的开发者/运维人员
- 需要开源可控 Agent 运行时的团队
- 需要可审计执行记录的协作场景

---

## 二、触发方式

### 2.1 触发词

| 触发词 | 场景示例 |
|--------|----------|
| 跑 dsh | "帮我跑 dsh 执行这个任务" |
| 跑 harness | "用 harness 跑一下这个脚本" |
| harness 任务 | "把这个 harness 任务加到队列里" |
| 让模型动手干活 | "让模型直接改这个文件" |
| dsh 执行 | "dsh 执行：读取 config.json 并输出内容" |
| 执行任务队列 | "把这三个任务加入队列并执行" |
| 批量跑任务 | "批量跑 tasks.json 里的所有任务" |
| 会话导出 | "导出今天的执行会话记录" |

### 2.2 大白话场景映射表

| 用户说 | 实际含义 | 技能动作 |
|--------|----------|----------|
| "帮我看看环境行不行" | 检查 dsh 是否可用 | 执行 `--check` |
| "先别真跑，看看任务描述对不对" | 预览任务 | 执行 `--dry-run` |
| "让模型把这个文件改了" | 单任务执行 | 执行 `dsh_run.py "修改文件 xxx"` |
| "这几个任务一起跑" | 批量任务 | 使用 `--batch` 或队列 |
| "跑完给我个报告" | 结构化输出 | 使用 `--report` |
| "上次跑的结果在哪看" | 历史记录 | 使用 `--session-list` / `--session-export` |

---

## 三、标准流程

### 3.1 前置条件

| 条件 | 检查方式 | 说明 |
|------|----------|------|
| Python 3.8+ | `python --version` | 脚本运行环境 |
| dsh CLI 已安装 | `dsh --version` | 核心运行时 |
| API Key 已配置 | `dsh_run.py --check` | 环境自检会验证 |
| DSH_HOME 路径正确 | `dsh_run.py --check` | 环境自检会验证 |

### 3.2 执行步骤

#### 第一步：环境自检

```bash
python dsh_run.py --check
```

预期输出（全部 OK 才可继续）：

```
[OK] API Key 已配置
[OK] dsh CLI 可用 (版本 x.y.z)
[OK] DSH_HOME 路径正确
[OK] Python 版本兼容
```

#### 第二步：任务预览（可选但推荐）

```bash
python dsh_run.py "读取项目根目录的 README.md 并总结要点" --dry-run
```

预期输出：任务描述 + 预期动作列表，不实际执行。

#### 第三步：单任务执行

```bash
python dsh_run.py "读取项目根目录的 README.md 并总结要点"
```

常用参数：

| 参数 | 取值示例 | 说明 |
|------|----------|------|
| `--model` | `deepseek-chat` | 指定模型 |
| `--timeout` | `120` | 超时秒数（默认 60） |
| `--permission` | `workspace-write` | 权限模式：`workspace-write` / `full` / `readonly` |
| `--verbose` | 无值 | 输出详细日志 |
| `--report` | 无值 | 输出 JSON 报告 |

#### 第四步：批量任务（可选）

方式一：JSON 文件批量导入

```bash
python dsh_run.py --batch tasks.json
```

`tasks.json` 格式：

```json
{
  "tasks": [
    {"description": "任务1描述", "model": "deepseek-chat", "timeout": 60},
    {"description": "任务2描述", "model": "deepseek-chat", "timeout": 90}
  ]
}
```

方式二：任务队列

```bash
# 添加任务到队列
python dsh_run.py "任务A" --queue-add
python dsh_run.py "任务B" --queue-add

# 查看队列
python dsh_run.py --queue-list

# 执行队列
python dsh_run.py --queue-run

# 清空队列
python dsh_run.py --queue-clear
```

#### 第五步：结果核验

执行完成后，需双重确认：

1. **dsh 输出**：检查模型返回的执行结果
2. **落盘文件**：检查实际文件是否被正确修改

只有读写一致才算通过。

#### 第六步：异常处理

| 异常现象 | 可能原因 | 处理方式 |
|----------|----------|----------|
| 环境自检失败 | API Key 未配置 | 配置 `DEEPSEEK_API_KEY` 环境变量 |
| CLI 版本不兼容 | dsh 升级破坏兼容 | 运行内置 cordis.yml 自动重建 |
| 编码错误 | 文件非 utf-8 编码 | 脚本自动尝试 gbk / gb18030 |
| 权限不足 | 权限模式限制 | 切换 `--permission full`（谨慎使用） |
| 超时 | 任务耗时过长 | 增加 `--timeout` 参数 |

---

## 四、置信度门控

### 4.1 信息不足时的处理

当执行过程中遇到以下情况，输出 `[需核实:字段]` 占位符，不编造结果：

| 场景 | 输出示例 |
|------|----------|
| 文件不存在 | `[需核实:文件路径] 指定的文件不存在，请确认路径` |
| API Key 缺失 | `[需核实:API Key] 未检测到有效的 API Key` |
| 模型返回不完整 | `[需核实:模型输出] 模型返回内容不完整，请重试` |
| 权限模式不明确 | `[需核实:权限模式] 请明确指定 --permission 参数` |

### 4.2 禁止行为

- 不猜测文件内容
- 不假设命令执行结果
- 不虚构模型输出
- 不跳过环境自检直接执行

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| `E001` | API Key 未配置 | "未检测到有效的 DeepSeek API Key" | 1. 设置 `DEEPSEEK_API_KEY` 环境变量 2. 重新运行 `--check` |
| `E002` | dsh CLI 未安装 | "未找到 dsh 命令，请先安装" | 1. 按官方文档安装 dsh 2. 验证 `dsh --version` |
| `E003` | 版本不兼容 | "dsh 版本与脚本不兼容" | 1. 运行 cordis.yml 自动重建 2. 或手动升级/降级 dsh |
| `E004` | 文件编码错误 | "文件编码无法识别" | 1. 确认文件编码 2. 转换为 utf-8 后重试 |
| `E005` | 权限不足 | "当前权限模式不允许此操作" | 1. 检查 `--permission` 参数 2. 按需切换权限模式 |
| `E006` | 任务超时 | "任务执行超时" | 1. 增加 `--timeout` 值 2. 拆分任务为更小步骤 |
| `E007` | 队列为空 | "任务队列为空，无可执行任务" | 1. 使用 `--queue-add` 添加任务 2. 或使用 `--batch` 导入 |
| `E008` | 会话不存在 | "指定的会话 ID 不存在" | 1. 使用 `--session-list` 查看可用会话 2. 确认会话 ID |

---

## 六、FAQ 反模式

### 6.1 常见坑

| 坑 | 反模式 | 正确做法 |
|----|--------|----------|
| 跳过环境自检 | 直接执行任务，报错后才发现 Key 没配 | 先跑 `--check`，确认全 OK 再执行 |
| 忽略 dry-run | 任务描述写错，模型执行了错误操作 | 先 `--dry-run` 预览，确认描述无误 |
| 权限一刀切 | 全部用 `--permission full` | 按需选择：默认 `workspace-write`，只读任务用 `readonly` |
| 不核验结果 | 只看模型输出，不检查落盘文件 | 双重确认：输出 + 文件读写一致 |
| 队列不清理 | 队列堆积旧任务，执行了不想要的任务 | 执行前 `--queue-list` 确认，执行后 `--queue-clear` |

### 6.2 反模式对照表

| 反模式 | 问题 | 替代方案 |
|--------|------|----------|
| 用 `--batch` 导入超大文件 | 内存占用高，易超时 | 拆分为多个小批次 |
| 依赖默认超时 | 复杂任务容易超时 | 预估耗时，显式设置 `--timeout` |
| 忽略编码问题 | 中文文件读取乱码 | 依赖内置多编码 fallback，或手动转码 |
| 不导出会话 | 无法回溯历史执行 | 定期 `--session-export` 留痕 |

---

## 七、渐进式披露

### 7.1 速查卡（30 秒上手）

```bash
# 1. 环境自检
python dsh_run.py --check

# 2. 单任务执行
python dsh_run.py "你的任务描述"

# 3. 批量执行
python dsh_run.py --batch tasks.json

# 4. 队列执行
python dsh_run.py "任务A" --queue-add
python dsh_run.py --queue-run
```

### 7.2 新手路径（5 分钟）

1. 运行 `--check` 确认环境
2. 用 `--dry-run` 预览一个简单任务
3. 执行一个真实任务（如"读取 README.md 并输出内容"）
4. 用 `--report` 查看 JSON 报告
5. 用 `--session-export` 导出执行记录

### 7.3 进阶路径（深入使用）

1. 掌握权限模式：`workspace-write` / `full` / `readonly` 的适用场景
2. 使用任务队列编排多步骤流程
3. 通过 `--mcp-init` 接入外部工具
4. 编写自定义 `tasks.json` 批量任务
5. 结合 `--report` 输出做自动化集成

---

## 八、参数速查表

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `--check` | 标志 | - | 环境自检 |
| `--dry-run` | 标志 | - | 任务预览，不实际执行 |
| `--model` | 字符串 | `deepseek-chat` | 指定模型 |
| `--timeout` | 整数 | `60` | 超时秒数 |
| `--permission` | 枚举 | `workspace-write` | 权限模式 |
| `--verbose` | 标志 | - | 详细日志输出 |
| `--report` | 标志 | - | JSON 报告输出 |
| `--batch` | 文件路径 | - | 批量任务 JSON 文件 |
| `--queue-add` | 标志 | - | 添加任务到队列 |
| `--queue-list` | 标志 | - | 查看队列 |
| `--queue-run` | 标志 | - | 执行队列 |
| `--queue-clear` | 标志 | - | 清空队列 |
| `--session-list` | 标志 | - | 查看会话列表 |
| `--session-export` | 标志 | - | 导出会话记录 |
| `--mcp-init` | 标志 | - | 生成 MCP 配置模板 |
| `--selftest` | 标志 | - | 运行自测契约 |

---

## 九、用户协议

<!-- user-agreement-injected -->

**使用须知：**

1. 本技能仅提供使用指导和最佳实践，使用者需自行承担因使用本技能产生的全部责任。
2. 使用者应确保其使用行为符合相关法律法规及 DeepSeek 服务条款。
3. 禁止对本技能进行反向工程、反编译、破解或任何形式的未授权修改。
4. 本技能不提供任何形式的明示或暗示担保，包括但不限于适销性、特定用途适用性担保。
5. 使用者应自行评估任务风险，对涉及敏感数据、生产环境操作的任务需额外谨慎。
6. 本技能产生的执行记录、日志、报告等数据由使用者自行保管，技能提供方不承担数据丢失责任。

---

## 十、许可证（License）

<!-- professional-license-embedded -->

**MIT License**

```
MIT License

Copyright (c) 2025 AgentForge Lab

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

---

*本 Skill 由 AI 辅助生成，仅供参考。使用前请阅读相关文档。*
