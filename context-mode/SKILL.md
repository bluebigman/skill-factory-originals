---
slug: context-mode
name: context-mode
displayName: 上下文压缩 会话记忆 Token优化
description: 压缩工具输出并持久化会话记忆，提升AI编程代理的上下文窗口利用率。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: LinguaForge
agent_created: true
trigger_words: ["context-mode", "上下文压缩", "会话记忆", "token优化", "上下文管理", "压缩输出", "记忆持久化"]
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# context-mode 技能文档

## 一、能力边界速查卡

本技能用于压缩 AI 编程代理的冗长工具输出，并将关键信息持久化到记忆文件，从而在有限的上下文窗口内保留更多有效信息。

| 维度 | 能做 | 不能做 |
|------|------|--------|
| 输入处理 | 接受标准输入或文件路径中的文本内容 | 无法直接读取二进制文件或图片内容 |
| 压缩策略 | 保留代码块、错误堆栈、关键路径、决策记录 | 不进行语义重写，不生成新代码逻辑 |
| 记忆持久化 | 将摘要写入 JSON 格式的记忆文件 | 不主动修改代理的配置文件 |
| 预算控制 | 支持 `--budget` 参数限制输出 token 数 | 无法动态调整已超出预算的输入 |
| 预演模式 | `--dry-run` 仅输出预览，不落盘 | 预演模式不校验记忆文件路径合法性 |
| 环境自检 | `--selftest` 检查 Python 版本与依赖 | 无法修复缺失的依赖，仅报告错误码 |

**适用对象**：使用 AI 编程代理（如 Claude Code、Codex 等）进行长时间开发任务的开发者；需要管理多轮对话上下文的运维人员；对 token 消耗敏感的个人开发者。

**不适用场景**：需要逐字保留原文的合同审查；需要完整代码审计的合规场景；输入内容小于 500 token 的短文本。

---

## 二、触发方式与场景映射

当你在对话中提及以下关键词或描述类似需求时，本技能自动激活：

| 触发词 | 典型场景描述 | 响应动作 |
|--------|-------------|----------|
| context-mode | "用 context-mode 压缩一下这段日志" | 执行压缩流程 |
| 上下文压缩 | "上下文快满了，帮我压缩一下" | 执行压缩并归档 |
| 会话记忆 | "下次对话还能记住这个决策吗" | 执行记忆持久化 |
| token优化 | "省点 token，把输出精简下" | 执行预算控制压缩 |
| 压缩输出 | "把构建日志压成摘要" | 执行标准压缩 |
| 记忆持久化 | "把关键路径存下来" | 执行记忆写入 |

---

## 三、标准操作流程

### 前置条件

1. Python 3.9 及以上版本（检查方法：`python3 --version`）
2. 已安装 `context-mode` CLI 工具（安装方法见项目 README）
3. 输入内容以文件路径或标准输入形式提供

### 执行步骤

**第一步：环境自检**

```bash
context-mode --selftest
```

预期输出：`[OK] 环境就绪，Python 3.11.4，依赖完整`。若输出错误码，跳转至「错误码体系」章节排查。

**第二步：预演压缩**

```bash
context-mode --input build_log.txt --dry-run
```

预演输出示例：

```
[DRY-RUN] 输入大小: 12,480 tokens
[DRY-RUN] 压缩后大小: 1,240 tokens（压缩率 90.1%）
[DRY-RUN] 摘要预览:
  - 构建失败: 3 处错误，均为类型不匹配
  - 关键路径: src/utils/validator.ts:45-52
  - 已跳过: 重复警告 28 条
```

**第三步：正式压缩**

确认预览无误后执行：

```bash
context-mode --input build_log.txt --output summary.json --budget 1500
```

参数说明：

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `--input` | string | 必填 | 输入文件路径，或 `-` 表示标准输入 |
| `--output` | string | `memory.json` | 输出记忆文件路径 |
| `--budget` | int | 2000 | 压缩后最大 token 数，范围 100-10000 |
| `--mode` | string | `tool` | `tool`（工具输出）或 `prompt`（提示词模板） |
| `--dry-run` | flag | 关闭 | 预演模式，不写入文件 |
| `--verbose` | flag | 关闭 | 输出详细日志 |

**第四步：验证输出**

打开生成的摘要文件，人工确认：

- [ ] 关键错误信息完整保留（错误码、文件路径、行号）
- [ ] 决策记录包含上下文（为什么做此决定）
- [ ] 无敏感信息泄露（API key、密码等）
- [ ] token 数在预算范围内

**第五步：归档清理**

```bash
mkdir -p docs/context-summaries
mv summary.json docs/context-summaries/2025-01-15-build-fix.json
rm temp_input.txt
```

### 输出规范

记忆文件 JSON 结构：

```json
{
  "schema_version": "1.0",
  "created_at": "2025-01-15T14:30:00Z",
  "source": "build_log.txt",
  "summary": {
    "key_points": ["构建失败：3处类型错误", "修复路径：validator.ts"],
    "decisions": ["采用显式类型断言替代 any"],
    "skipped": ["重复警告 28 条"]
  },
  "token_stats": {
    "input": 12480,
    "output": 1240,
    "compression_ratio": 0.901
  }
}
```

---

## 四、置信度门控

当输入内容存在以下情况时，输出对应占位符而非编造内容：

| 情况 | 占位符 | 示例 |
|------|--------|------|
| 输入中未明确提及的版本号 | `[需核实:版本号]` | 依赖版本为 [需核实:版本号] |
| 无法确认的错误原因 | `[需核实:错误根因]` | 构建失败，根因 [需核实:错误根因] |
| 缺失的时间戳 | `[需核实:时间]` | 该操作发生于 [需核实:时间] |
| 未提供的文件路径 | `[需核实:文件路径]` | 相关代码位于 [需核实:文件路径] |

**规则**：宁可输出占位符，不进行推测性补全。占位符出现后，用户需手动补充信息或重新提供完整输入。

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| CM-001 | Python 版本过低 | "需要 Python 3.9+，当前版本 x.y.z" | 升级 Python 或使用虚拟环境 |
| CM-002 | 依赖缺失 | "缺少依赖：xxx" | `pip install xxx` 后重试 |
| CM-003 | 输入文件不存在 | "无法读取文件：path" | 检查路径是否正确 |
| CM-004 | 预算过小 | "预算 100 低于最小限制 100" | 调整 `--budget` 至 100-10000 |
| CM-005 | 输出目录无权限 | "无法写入目录：path" | 检查目录权限或更换路径 |
| CM-006 | 输入为空 | "输入内容为空，无法压缩" | 检查输入来源 |
| CM-007 | 记忆文件损坏 | "记忆文件 JSON 解析失败" | 备份后删除，重新生成 |

**排查流程**：

1. 记录错误码和完整错误信息
2. 运行 `context-mode --verbose` 获取详细日志
3. 对照上表定位问题
4. 修正后重新执行 `--dry-run` 验证

---

## 六、常见陷阱与反模式

| 陷阱 | 错误做法 | 正确做法 |
|------|----------|----------|
| 跳过预演 | 直接执行正式压缩，发现摘要缺失关键信息 | 始终先跑 `--dry-run`，确认后再正式执行 |
| 预算设置过大 | `--budget 10000` 导致压缩效果不明显 | 根据上下文窗口大小设置，128k 窗口建议 2000-4000 |
| 忽略记忆文件冲突 | 多个项目共用同一记忆文件，信息互相覆盖 | 使用 `CONTEXT_MODE_MEMORY_PATH` 为每个项目指定独立文件 |
| 压缩后不验证 | 压缩完直接使用，未发现敏感信息泄露 | 每次压缩后人工检查摘要中的敏感信息 |
| 依赖默认配置 | 不阅读参数说明，使用默认值导致效果不佳 | 根据场景调整 `--mode` 和 `--budget` 参数 |

---

## 七、渐进式阅读路径

### 速查卡（30 秒上手）

```
context-mode --selftest          # 环境检查
context-mode --input file.txt --dry-run   # 预演
context-mode --input file.txt --output mem.json --budget 2000  # 正式
```

### 新手路径（首次使用）

1. 阅读「能力边界速查卡」确认适用场景
2. 按「标准操作流程」前三步完成一次完整压缩
3. 对照「输出规范」检查摘要格式
4. 遇到问题查阅「错误码体系」

### 进阶路径（熟练用户）

1. 使用 `--budget` 精细控制 token 消耗，结合代理上下文窗口（如 128k）设置合理预算
2. 自定义记忆文件路径：`CONTEXT_MODE_MEMORY_PATH=/path/to/memory.json`
3. 编写 shell 脚本，将压缩流程集成到 CI/CD 管道
4. 使用 `--mode prompt` 压缩提示词模板，保持代理行为一致性
5. 定期运行 `--selftest` 验证安装完整性

---

## 八、用户协议

<!-- user-agreement-injected -->

**使用责任**：使用者应自行承担因使用本 Skill 产生的全部责任。本 Skill 的压缩操作可能造成信息丢失，使用者应在处理前确认关键信息已备份。

**禁止反向工程**：使用者不得对本 Skill 进行反向工程、反编译、破解或试图提取源代码（除非适用法律允许）。

**无担保**：本 Skill 按"原样"提供，不附带任何明示或暗示的担保，包括但不限于适销性、特定用途适用性和非侵权性。

**数据安全**：使用者应自行备份重要数据。本 Skill 的压缩操作可能造成信息丢失，使用者应在处理前确认关键信息已备份。

**合规使用**：使用者不得将本 Skill 用于任何违反法律法规或侵犯第三方权益的用途。

---

## 九、许可证（License）

<!-- professional-license-embedded -->

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

---

*文档版本：1.0.0 | 最后更新：2025-01-15 | 反馈渠道：项目 GitHub Issues*
