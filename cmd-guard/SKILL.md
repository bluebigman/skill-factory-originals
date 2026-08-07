---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: cmd-guard
name: cmd-guard
displayName: 命令安全 风险拦截 操作审计
description: 拦截危险命令，评估风险并提供安全替代方案与执行确认。
version: 1.0.2
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/cmd-guard
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 林栖
agent_created: true
trigger_words: ["cmd-guard", "危险命令拦截", "rm -rf 防护", "命令风险评估", "shell 安全", "删除保护", "高危操作确认"]
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# cmd-guard — 危险命令拦截与操作审计 Skill

## 一、能力边界（一页纸速查卡）

### 1.1 能做与不能做

| 维度 | 能做 ✅ | 不能做 ❌ |
|------|---------|-----------|
| **命令检测** | 识别 `rm -rf`、`mkfs`、`dd`、`chmod -R 777`、`shutdown`、`reboot`、`:(){ :\|:& };:`（fork 炸弹）等高风险命令 | 无法检测经过编码/混淆后的变体（如 hex 编码后执行） |
| **风险评估** | 基于命令类型、目标路径、通配符展开范围给出 0-100 风险分 | 无法评估业务语义层面的风险（如"这个目录是否该删"） |
| **路径校验** | 支持白名单（允许删除的路径）与黑名单（禁止触碰的路径，如 `/etc`、`/boot`） | 无法识别符号链接指向的真实路径（需 `-P` 选项配合） |
| **替代建议** | 对常见危险命令给出安全替代方案（如用 `find -delete` 替代 `rm -rf` 的部分场景） | 无法保证替代命令在目标系统上可用（需提前验证） |
| **执行拦截** | 在命令执行前弹出确认提示，要求输入 `YES` 或二次确认码 | 无法拦截已经通过 `sudo` 提权且绕过确认的进程 |
| **审计日志** | 记录操作时间、用户、命令全文、风险评分、确认状态到本地日志文件 | 无法将日志远程同步（需配合外部工具） |

### 1.2 适用对象

- **适用**：使用 AI 编码助手（如 Copilot、Codex、Cursor 等）生成 shell 命令的开发者；管理多台服务器的运维人员；CI/CD 流水线中需要命令安全闸门的团队。
- **不适用**：已通过容器隔离/沙箱环境完全隔离的场景（此时拦截意义不大）；需要处理加密或混淆命令的安全分析场景。

### 1.3 风险评分模型

| 风险等级 | 分值区间 | 判定条件 | 处置动作 |
|----------|----------|----------|----------|
| 低危 | 0-30 | 普通文件操作，路径明确，无递归/强制标志 | 记录日志，放行 |
| 中危 | 31-60 | 包含递归删除、通配符、或路径在系统目录附近 | 输出警告，要求确认 |
| 高危 | 61-85 | 涉及 `mkfs`、`dd`、`chmod -R 777`、黑名单路径 | 强制拦截，需输入确认码 |
| 致命 | 86-100 | 同时命中多条高危规则（如 `rm -rf /` 或 `dd if=/dev/zero of=/dev/sda`） | 直接拒绝，不可覆盖 |

---

## 二、触发方式

### 2.1 触发词与场景映射

| 触发词/短语 | 典型场景 | 触发动作 |
|-------------|----------|----------|
| `cmd-guard` | 用户直接调用本 Skill | 进入交互式检查模式 |
| "帮我删掉这个目录" | 用户要求 AI 生成删除命令 | 自动套用危险命令检测 |
| "清理磁盘空间" | 用户意图不明确，可能涉及 `dd` 或 `rm` | 先询问目标路径，再检测 |
| "给这个文件加权限" | 可能生成 `chmod 777` | 检测权限值，给出最小权限建议 |
| "格式化这个 U 盘" | 涉及 `mkfs` | 强制拦截，要求二次确认 |
| "危险命令拦截" | 用户主动要求启用防护 | 加载规则库，进入监控模式 |

### 2.2 命令行接口

```bash
# 自检模式：验证规则库完整性与配置有效性
cmd-guard --selftest

# 版本信息
cmd-guard --version

# 交互式检查（默认模式）
cmd-guard "rm -rf /var/log/old"

# 批量检查（从文件读取命令列表）
cmd-guard --batch commands.txt

# 生成审计报告
cmd-guard --audit --output report.json
```

---

## 三、标准流程

### 3.1 前置条件

| 条件项 | 要求 | 验证方式 |
|--------|------|----------|
| 操作系统 | Linux/macOS（Windows 需 WSL） | `uname -a` |
| Shell 环境 | bash/zsh 均可 | `echo $SHELL` |
| 配置文件 | `~/.cmd-guard/config.yaml` 存在 | `ls -la ~/.cmd-guard/` |
| 日志目录 | `~/.cmd-guard/logs/` 可写 | `touch ~/.cmd-guard/logs/.write_test` |

首次使用请运行 `cmd-guard --selftest` 验证环境。

### 3.2 执行步骤（标准检查流程）

**步骤 1：命令解析**

将待检查命令拆分为命令名、参数、目标路径三部分。

```bash
输入: rm -rf /var/log/nginx/access.log*
解析: {command: "rm", flags: ["-r", "-f"], target: "/var/log/nginx/access.log*"}
```

**步骤 2：规则匹配**

将解析结果与内置规则库逐条比对。规则库包含以下维度：

| 规则维度 | 示例 | 权重 |
|----------|------|------|
| 命令名 | `rm`、`mkfs`、`dd`、`chmod`、`shutdown` | 30 |
| 危险标志 | `-rf`、`-R 777`、`if=`、`of=` | 25 |
| 目标路径 | `/`、`/etc`、`/boot`、`/dev/sd*` | 25 |
| 通配符 | `*`、`?`、`[a-z]` | 10 |
| 递归深度 | `-r` 且目标为目录 | 10 |

**步骤 3：路径校验**

- 将目标路径与白名单比对：若在白名单内，直接放行。
- 将目标路径与黑名单比对：若在黑名单内，风险分直接 +50。
- 通配符预检：展开通配符，统计匹配文件数。若匹配数 > 100，风险分 +20。

```bash
# 通配符预检示例
输入: rm -rf /tmp/backup_*
预检: 匹配 156 个文件 → 风险分 +20
```

**步骤 4：风险评分与决策**

根据规则匹配结果计算总分，按 1.3 节的风险等级表执行对应动作。

**步骤 5：执行确认（高危及以上）**

```bash
⚠️  高危命令拦截确认
命令: rm -rf /var/log/nginx/access.log*
风险分: 72/100
风险因素: 递归删除 + 通配符 + 日志目录
建议替代: find /var/log/nginx/ -name "access.log*" -mtime +7 -delete

请输入确认码 [7842] 以继续，或输入 N 取消: 
```

**步骤 6：审计日志记录**

```json
{
  "timestamp": "2025-01-15T14:32:07+08:00",
  "user": "deploy",
  "command": "rm -rf /var/log/nginx/access.log*",
  "risk_score": 72,
  "risk_level": "高危",
  "decision": "confirmed",
  "confirmation_code": "7842",
  "replacement_suggested": "find /var/log/nginx/ -name \"access.log*\" -mtime +7 -delete"
}
```

### 3.3 输出规范

| 输出类型 | 格式 | 适用场景 |
|----------|------|----------|
| 终端交互 | 彩色文本 + 表格 | 人工确认场景 |
| JSON | 结构化数据 | 程序化调用/CI 集成 |
| 审计报告 | Markdown 表格 | 定期回顾/合规检查 |

---

## 四、置信度门控

当以下信息缺失时，**不得**自行推断，必须输出 `[需核实:字段]` 占位符：

| 缺失信息 | 占位符示例 | 处理方式 |
|----------|------------|----------|
| 目标路径不明确 | `[需核实:目标路径]` | 暂停检查，向用户询问 |
| 通配符匹配范围未知 | `[需核实:通配符匹配数]` | 不进行风险加分，按保守值处理 |
| 用户权限级别未知 | `[需核实:是否sudo]` | 按普通用户权限评估 |
| 文件系统类型未知 | `[需核实:文件系统]` | 不评估 `dd` 对块设备的影响 |
| 环境变量展开结果未知 | `[需核实:$VAR展开值]` | 不评估变量指向的路径风险 |

**示例**：

```bash
输入: rm -rf $TMP_DIR/*
输出: 
  命令解析: rm -rf $TMP_DIR/*
  路径校验: [需核实:$TMP_DIR展开值] — 无法确认目标路径
  风险评分: 45 (保守估计，待路径确认后重新评估)
  建议: 请先执行 echo $TMP_DIR 确认路径后再继续
```

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| `CG-001` | 命令解析失败 | "无法解析该命令，请检查语法" | 确认命令格式正确，特殊字符是否转义 |
| `CG-002` | 路径不存在 | "目标路径不存在，请确认路径拼写" | 使用 `ls` 或 `realpath` 验证路径 |
| `CG-003` | 通配符展开异常 | "通配符匹配异常，可能匹配到系统关键文件" | 先运行 `ls` 查看匹配结果，缩小范围 |
| `CG-004` | 规则库加载失败 | "规则库文件缺失或格式错误" | 运行 `cmd-guard --selftest` 检查配置 |
| `CG-005` | 日志写入失败 | "无法写入审计日志，请检查目录权限" | 检查 `~/.cmd-guard/logs/` 权限 |
| `CG-006` | 确认超时 | "确认超时，命令已取消" | 重新执行命令，在 30 秒内完成确认 |
| `CG-007` | 黑名单路径命中 | "该路径已被列入黑名单，禁止操作" | 更换操作路径，或联系管理员修改黑名单 |
| `CG-008` | 白名单路径冲突 | "该路径同时命中白名单与黑名单，以黑名单为准" | 检查配置文件中黑白名单的顺序与优先级 |

---

## 六、FAQ 反模式对照

### 6.1 常见坑与正确做法

| 常见坑（反模式） | 问题描述 | 正确做法（正模式） |
|------------------|----------|-------------------|
| **盲目信任通配符** | 直接执行 `rm -rf /var/log/*.log`，未先查看匹配范围 | 先运行 `ls /var/log/*.log` 确认匹配文件列表，再决定是否删除 |
| **忽略符号链接** | `rm -rf /tmp/link_to_etc` 实际删除的是 `/etc` 内容 | 使用 `ls -ld` 检查目标是否为符号链接，必要时加 `-P` 参数 |
| **sudo 滥用** | 所有命令都加 `sudo`，导致危险命令权限过大 | 仅在必要时使用 `sudo`，并确认当前用户权限边界 |
| **跳过确认机制** | 为图省事直接 `echo Y \| cmd-guard` 绕过确认 | 保持确认机制，高危操作必须人工确认 |
| **日志从不查看** | 审计日志堆积但从不回顾，无法发现异常模式 | 每周回顾一次审计日志，检查是否有未授权的高危操作记录 |
| **替代命令未验证** | 建议的替代命令在目标系统上不存在或行为不同 | 在测试环境先行验证替代命令的行为，再用于生产 |

### 6.2 反模式示例对照表

```bash
# 反模式：直接删除，不检查
rm -rf /var/log/nginx/

# 正模式：先检查再删除
ls -la /var/log/nginx/
find /var/log/nginx/ -type f -mtime +30 -delete

# 反模式：chmod 777 一把梭
chmod -R 777 /var/www/html

# 正模式：最小权限原则
chmod -R u+rwX,go+rX /var/www/html
chown -R www-data:www-data /var/www/html

# 反模式：dd 直接写块设备
dd if=/dev/zero of=/dev/sdb bs=1M

# 正模式：先确认设备，再操作
lsblk
sudo dd if=/dev/zero of=/dev/sdb bs=1M count=100 status=progress
```

---

## 七、渐进式披露

### 7.1 速查卡（30 秒上手）

```
┌─────────────────────────────────────────────────────┐
│  cmd-guard 速查卡                                    │
├─────────────────────────────────────────────────────┤
│  1. 检查单条命令:  cmd-guard "rm -rf /tmp/test"      │
│  2. 批量检查:      cmd-guard --batch list.txt        │
│  3. 自检环境:      cmd-guard --selftest              │
│  4. 查看版本:      cmd-guard --version               │
│  5. 配置文件:      ~/.cmd-guard/config.yaml          │
│  6. 审计日志:      ~/.cmd-guard/logs/audit_*.json    │
├─────────────────────────────────────────────────────┤
│  高危命令速记:                                      │
│  rm -rf /  → 致命                                   │
│  mkfs.*    → 高危                                   │
│  dd if=    → 高危                                   │
│  chmod 777 → 中危                                   │
│  shutdown  → 中危                                   │
└─────────────────────────────────────────────────────┘
```

### 7.2 分层次阅读路径

**新手路径（首次使用）**：

1. 阅读「一、能力边界」了解工具能做什么。
2. 运行 `cmd-guard --selftest` 验证环境。
3. 用 `cmd-guard "rm -rf /tmp/test"` 测试一条简单命令。
4. 查看 `~/.cmd-guard/logs/` 下的审计日志，理解输出格式。

**进阶路径（日常使用）**：

1. 阅读「三、标准流程」理解检查逻辑。
2. 自定义 `~/.cmd-guard/config.yaml`，添加自己的黑白名单。
3. 将 `cmd-guard` 集成到 CI 流水线，使用 `--batch` 模式批量检查。
4. 定期回顾「六、FAQ 反模式对照」，避免常见错误。

**专家路径（深度定制）**：

1. 阅读「五、错误码体系」，理解异常处理逻辑。
2. 修改规则库权重，适配特定业务场景。
3. 编写脚本解析审计日志，生成可视化报告。
4. 扩展规则库，添加自定义危险命令模式。

---

## 八、配置文件参考

`~/.cmd-guard/config.yaml` 示例：

```yaml
# cmd-guard 配置文件
version: 1.0

# 黑名单路径（命中即高危）
blacklist:
  - "/"
  - "/etc"
  - "/boot"
  - "/dev/sd*"
  - "/var/lib/mysql"

# 白名单路径（命中即放行）
whitelist:
  - "/tmp/cache"
  - "/var/log/nginx/old"

# 风险阈值
thresholds:
  low: 30
  medium: 60
  high: 85

# 确认超时（秒）
confirmation_timeout: 30

# 日志保留天数
log_retention_days: 90

# 自定义规则
custom_rules:
  - pattern: "git push --force"
    risk: 40
    reason: "强制推送可能导致远程历史丢失"
```

---

## 九、用户协议

<!-- user-agreement-injected -->

**使用本 Skill 即表示您同意以下条款：**

1. **责任承担**：使用者自行承担因使用本 Skill 产生的全部责任。本 Skill 提供的风险评估与拦截建议仅供参考，不构成任何形式的安全保证。最终操作决策权与执行责任完全归属于使用者本人。

2. **禁止反向工程**：未经授权，不得对本 Skill 的规则库、评分算法、配置解析逻辑进行反向工程、反编译或提取核心逻辑用于商业用途。

3. **无担保声明**：本 Skill 按"现状"提供，不附带任何明示或暗示的担保，包括但不限于适销性、特定用途适用性及不侵权保证。

4. **使用限制**：不得将本 Skill 用于任何违法活动、未授权系统访问或任何形式的恶意操作。

5. **协议更新**：本协议可能随 Skill 版本更新而调整，持续使用即视为接受更新后的协议。

---

## 十、许可证（License


## 许可证（License）

```text
MIT License

Copyright (c) 2026 SkillForge Lab

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.
```
<!-- professional-license-embedded -->
