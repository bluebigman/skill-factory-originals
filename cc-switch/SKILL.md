---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: cc-switch
name: cc-switch
displayName: 多智能体配置切换台
description: 统一管理多款AI编码助手配置，一键切换，提升开发效率。
version: 2.0.1
rules_version: cpr-20260821-n626
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/cc-switch
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 林墨白
agent_created: true
trigger_words: ["cc-switch", "cc switch", "多智能体切换", "AI编码助手配置管理", "Claude Code配置", "配置切换", "编码助手管理"]
---

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->


> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# cc-switch：多智能体配置切换台

## 一、能力边界：一页纸速查卡

本 Skill 面向需要同时维护多套 AI 编码助手配置的开发者，提供配置备份、切换、恢复的标准化操作指引。

| 维度 | 说明 |
|------|------|
| 核心能力 | 管理 Claude Code、Codex 等编码助手的配置文件，支持备份、切换、恢复 |
| 适用对象 | 使用 2 款及以上 AI 编码助手的开发者、团队技术负责人、DevOps 工程师 |
| 前置条件 | 已安装目标编码助手 CLI 工具，且配置文件路径符合默认约定 |
| 不做的事 | 不修改编码助手本身的模型参数、不代理网络请求、不处理认证令牌生成 |
| 边界限制 | 仅处理本机文件系统内的配置，不涉及远程同步或云端存储 |

**配置路径速查**

| 工具 | 配置文件路径 | 格式 |
|------|-------------|------|
| Claude Code | `~/.claude-code/config.json` | JSON |
| Codex | `~/.codex/config.toml` | TOML |

## 二、触发方式：场景映射表

当出现以下场景时，可调用本 Skill 的操作流程：

| 触发词 | 实际场景 | 对应操作 |
|--------|---------|---------|
| cc-switch / cc switch | 在多个项目间切换不同 AI 助手配置 | 执行配置切换流程 |
| 多智能体切换 | 团队内多人使用不同编码助手配置 | 执行配置备份与分发 |
| AI编码助手配置管理 | 需要统一管理多套配置版本 | 执行配置备份与恢复 |
| Claude Code配置 | 单独调整 Claude Code 配置 | 执行单工具配置操作 |

## 三、标准流程：从备份到切换

### 前置条件检查

1. 确认目标配置文件存在（`ls ~/.claude-code/config.json` 或 `ls ~/.codex/config.toml`）
2. 确认备份目录可写（`mkdir -p ~/.cc-switch/backups`）
3. 确认当前用户对配置文件有读写权限

### 执行步骤

**步骤 1：备份当前生效配置**

```bash
# 生成带时间戳的备份文件名
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
cp ~/.claude-code/config.json ~/.cc-switch/backups/config.claude-code.${TIMESTAMP}.json
```

**步骤 2：写入新配置**

```bash
# 将目标配置内容写入生效位置
cat /path/to/target-config.json > ~/.claude-code/config.json
```

**步骤 3：验证配置生效**

```bash
# 检查配置语法
claude-code --version
# 或直接启动工具确认无报错
```

### 输出规范

- 每次操作后输出操作日志，格式：`[时间] [操作类型] [目标文件] [结果]`
- 备份文件命名规则：`config.{tool-name}.{YYYYMMDD-HHMMSS}.{ext}`

## 四、置信度门控

当遇到以下情况时，输出 `[需核实:字段]` 占位符，不进行猜测：

| 场景 | 处理方式 |
|------|---------|
| 配置文件路径不确定 | 输出 `[需核实:配置文件路径]`，提示用户通过 `which` 或 `find` 确认 |
| 配置格式不明确 | 输出 `[需核实:配置格式]`，建议用户参考官方文档 |
| 工具版本差异 | 输出 `[需核实:工具版本]`，提示不同版本配置项可能存在差异 |

## 五、错误码体系

| 错误码 | 错误描述 | 提示话术 | 修正步骤 |
|--------|---------|---------|---------|
| E001 | 配置文件不存在 | 未找到目标配置文件，请确认工具已初始化 | 运行工具初始化命令（如 `claude-code init`） |
| E002 | 备份目录不可写 | 备份目录权限不足，无法创建备份 | 执行 `chmod u+w ~/.cc-switch/backups` 或更换目录 |
| E003 | 配置格式错误 | 新配置无法被工具解析 | 使用 `jq` 或 `python -m json.tool` 校验 JSON 格式 |
| E004 | 权限拒绝 | 当前用户无权限写入配置文件 | 使用 `sudo` 或调整文件所有者 |
| E005 | 备份文件损坏 | 备份文件内容不完整或格式错误 | 检查备份文件完整性，必要时从其他备份恢复 |

## 六、FAQ 反模式对照

| 常见坑 | 反模式示例 | 正确做法 |
|--------|-----------|---------|
| 跳过备份直接覆盖 | 直接 `cp new-config.json ~/.claude-code/config.json` | 先执行备份步骤，确保可回滚 |
| 忽略配置格式差异 | 将 TOML 格式直接写入 JSON 配置文件 | 确认目标工具期望的格式，必要时转换 |
| 不验证切换结果 | 切换后不启动工具直接关闭终端 | 切换后立即验证工具可正常启动 |
| 备份文件命名混乱 | 使用 `config1.json`、`config2.json` 等无意义名称 | 使用带时间戳的规范命名 |
| 忘记恢复旧配置 | 切换后不保留原配置副本 | 始终保留最近 3 份备份，便于快速回退 |

## 七、渐进式披露：分层次阅读路径

### 速查卡（30 秒上手）

```bash
# 备份
mkdir -p ~/.cc-switch/backups
cp ~/.claude-code/config.json ~/.cc-switch/backups/config.claude-code.$(date +%Y%m%d-%H%M%S).json

# 切换
cp /path/to/new-config.json ~/.claude-code/config.json

# 验证
claude-code --version
```

### 新手路径（5 分钟掌握）

1. 阅读「能力边界」了解适用范围
2. 按「标准流程」执行一次完整备份-切换-验证
3. 遇到问题查阅「错误码体系」

### 进阶路径（深度使用）

1. 结合「FAQ 反模式」优化操作习惯
2. 为多工具建立统一的备份管理脚本
3. 将配置切换纳入 CI/CD 流程，实现自动化

---

## 用户协议

使用本 Skill 即表示您同意以下条款：

1. **责任承担**：使用者自行承担使用本 Skill 产生的全部责任。包括但不限于因配置错误导致的工具异常、数据丢失或开发效率下降。
2. **禁止反向工程**：不得对本 Skill 文档进行反向工程、反编译或试图提取底层逻辑。
3. **合规使用**：使用者应确保使用场景符合相关法律法规及所在组织的规章制度。
4. **无担保声明**：本 Skill 按"现状"提供，不附带任何形式的明示或暗示担保。

<!-- user-agreement-injected -->

## 许可证（License）

MIT License

Copyright (c) 2026 林墨白

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
