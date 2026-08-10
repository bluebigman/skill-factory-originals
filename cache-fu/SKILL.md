---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: cache-fu
name: cache-fu
displayName: 磁盘清理 缓存分析 安全回收
description: 智能扫描并清理系统缓存，提供安全预览与回滚机制，释放磁盘空间。
version: 2.0.1
rules_version: cpr-20260810-n301
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/cache-fu
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: LinusTechWriter
agent_created: true
trigger_words: ["cache", "缓存", "清理", "cleanup", "disk space", "磁盘空间", "释放空间", "垃圾文件"]
---

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->


> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# cache-fu — 系统缓存智能清理与安全回滚指南

## 一、能力边界（一页纸速查卡）

### 1.1 能做什么

| 能力项 | 说明 | 示例 |
|--------|------|------|
| 缓存扫描 | 识别常见系统与应用缓存目录 | `~/Library/Caches`、`/var/cache`、`~/.cache` |
| 大小统计 | 计算各缓存目录占用空间 | 输出目录路径 + 人类可读大小（KB/MB/GB） |
| 安全预览 | 清理前生成待删除文件清单 | 列出文件路径、大小、最后修改时间 |
| 白名单保护 | 跳过正在运行进程占用的缓存文件 | 通过 `lsof` 检测活跃文件句柄 |
| 回滚机制 | 删除前自动备份至临时回收站 | 备份至 `~/.cache-fu/trash/`，可恢复 |
| 报告输出 | 生成 Markdown 格式清理报告 | 包含清理前后空间对比、文件数量 |

### 1.2 不能做什么

| 限制项 | 说明 |
|--------|------|
| 不清理系统关键文件 | 不会触碰 `/System`、`/bin`、`/etc` 等目录 |
| 不清理用户数据 | 不会删除文档、图片、下载等个人文件 |
| 不支持跨平台 | 仅支持 macOS / Linux（Windows 需另行适配） |
| 不自动定期执行 | 需用户手动触发或配置 cron |
| 不清理应用自身数据 | 仅处理缓存，不涉及应用配置或数据库 |

### 1.3 适用对象

- **个人用户**：希望安全释放磁盘空间，不熟悉命令行操作
- **开发人员**：需要快速清理构建缓存、包管理器缓存
- **运维人员**：批量清理多台服务器缓存，需生成审计报告

---

## 二、触发方式

### 2.1 触发词

| 触发词 | 场景描述 |
|--------|----------|
| `cache` / `缓存` | 用户直接提及缓存清理需求 |
| `清理` / `cleanup` | 用户要求释放磁盘空间 |
| `disk space` / `磁盘空间` | 用户报告磁盘空间不足 |
| `垃圾文件` / `临时文件` | 用户描述系统变慢或空间被占 |

### 2.2 场景映射表

| 用户说 | 实际需求 | 执行动作 |
|--------|----------|----------|
| "我的磁盘满了，帮我看看" | 需要空间分析 | 运行 `--scan` 扫描各缓存目录 |
| "清理一下缓存吧" | 安全清理 | 运行 `--preview` 生成清单 → 确认后 `--clean` |
| "刚才清理的东西能恢复吗" | 回滚需求 | 运行 `--restore` 从回收站恢复 |
| "清理后系统变慢了" | 误删排查 | 运行 `--rollback` 回滚最近一次清理 |

---

## 三、标准流程

### 3.1 前置条件

| 条件 | 要求 | 检查方式 |
|------|------|----------|
| Python 版本 | ≥ 3.6 | `python3 --version` |
| 操作系统 | macOS / Linux | `uname -a` |
| 磁盘空间 | 至少 100MB 可用 | `df -h` |
| 权限 | 普通用户即可（无需 sudo） | `id -u` |

### 3.2 执行步骤

#### 步骤 1：环境自检

```bash
python3 run.py --selftest
```

预期输出：
```
[OK] Python 3.9.6 detected
[OK] Platform: Darwin (macOS)
[OK] Cache directories accessible
[OK] Trash directory writable
```

#### 步骤 2：扫描缓存

```bash
python3 run.py --scan
```

输出示例（Markdown 格式）：

```markdown
# 缓存扫描报告

| 目录 | 大小 | 文件数 | 最后修改 |
|------|------|--------|----------|
| ~/Library/Caches/com.apple.Safari | 1.2GB | 3,456 | 2026-08-09 |
| ~/.cache/pip | 856MB | 1,234 | 2026-08-08 |
| /var/cache/apt/archives | 234MB | 87 | 2026-08-07 |

**总计：2.3GB 可回收**
```

#### 步骤 3：安全预览

```bash
python3 run.py --preview
```

生成待删除文件清单，包含：
- 文件完整路径
- 文件大小（字节）
- 最后访问时间
- 是否被进程占用（`[LOCKED]` 标记）

#### 步骤 4：执行清理

```bash
python3 run.py --clean --dry-run  # 先试运行
python3 run.py --clean            # 实际执行
```

清理过程：
1. 将待删除文件移动至 `~/.cache-fu/trash/`（而非直接删除）
2. 生成清理日志 `~/.cache-fu/logs/cleanup_YYYYMMDD_HHMMSS.log`
3. 输出清理前后空间对比

#### 步骤 5：验证与报告

```bash
python3 run.py --report
```

输出 Markdown 报告，包含：
- 清理前后磁盘空间对比
- 各目录清理明细
- 回收站当前占用
- 建议后续操作

### 3.3 输出规范

所有输出均采用 Markdown 格式，遵循以下规范：

| 输出类型 | 格式要求 | 示例 |
|----------|----------|------|
| 扫描报告 | 表格 + 总计 | 见上文 |
| 清理日志 | 时间戳 + 操作 + 路径 | `2026-08-10 14:30:22 [MOVE] ~/Library/Caches/foo/bar.tmp` |
| 错误信息 | `[错误码] 描述` | `[E1001] 目录不存在` |
| 帮助信息 | 参数说明 + 示例 | `--help` 输出 |

---

## 四、置信度门控

### 4.1 信息不足时的处理

当遇到以下情况时，输出 `[需核实:字段]` 占位符，不进行猜测：

| 场景 | 占位符示例 | 后续动作 |
|------|------------|----------|
| 缓存目录不存在 | `[需核实:目录路径]` | 提示用户确认路径 |
| 文件大小无法读取 | `[需核实:文件大小]` | 跳过该文件并记录 |
| 进程占用状态未知 | `[需核实:进程状态]` | 标记为 `[LOCKED]` 并跳过 |
| 回收站空间不足 | `[需核实:回收站容量]` | 提示用户清理回收站 |

### 4.2 禁止行为

- 不猜测文件用途
- 不假设用户意图
- 不自动删除无法确认的文件
- 不修改系统配置文件

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| `E1001` | 目录不存在 | `[E1001] 指定的缓存目录不存在，请检查路径` | 1. 使用 `--scan` 重新扫描 2. 确认路径拼写 |
| `E1002` | 权限不足 | `[E1002] 无法访问该目录，需要更高权限` | 1. 检查目录权限 2. 使用 `sudo`（谨慎） |
| `E1003` | 磁盘空间不足 | `[E1003] 回收站空间不足，无法备份` | 1. 清理回收站 2. 减少本次清理文件数 |
| `E1004` | 文件被占用 | `[E1004] 文件正在被进程使用，已跳过` | 1. 等待进程结束 2. 使用 `--force`（不推荐） |
| `E2001` | 参数错误 | `[E2001] 无效的参数组合，请查看帮助` | 1. 运行 `--help` 2. 检查参数拼写 |
| `E2002` | 版本不兼容 | `[E2002] Python 版本过低，需要 ≥ 3.6` | 1. 升级 Python 2. 使用 pyenv 管理版本 |
| `E3001` | 回滚失败 | `[E3001] 无法恢复文件，回收站可能已损坏` | 1. 检查回收站目录 2. 手动恢复备份 |

---

## 六、FAQ 反模式

### 6.1 常见坑与反模式对照

| 坑 | 反模式（错误做法） | 正模式（推荐做法） |
|----|-------------------|-------------------|
| 直接删除而非移动 | `rm -rf ~/Library/Caches/*` | 先移动至回收站，确认无误后再清空 |
| 忽略进程占用 | 删除正在使用的缓存文件 | 使用 `lsof` 检测，跳过 `[LOCKED]` 文件 |
| 无备份清理 | 一次性删除所有缓存 | 保留最近 7 天的回收站备份 |
| 清理后不验证 | 清理完就结束 | 运行 `--report` 验证空间释放情况 |
| 误删重要缓存 | 删除所有 `.db` 文件 | 仅清理明确标记为缓存的文件 |

### 6.2 反模式案例

**反模式**：用户直接运行 `python3 run.py --clean --all` 清理所有缓存，导致应用启动变慢。

**正确做法**：
1. 先运行 `--scan` 查看各缓存大小
2. 使用 `--preview` 生成清单
3. 仅清理超过 100MB 且非活跃的缓存目录
4. 清理后重启相关应用验证功能

---

## 七、渐进式披露

### 7.1 速查卡（30 秒上手）

```bash
# 快速清理流程
python3 run.py --selftest    # 1. 环境检查
python3 run.py --scan        # 2. 查看缓存
python3 run.py --preview     # 3. 预览待删
python3 run.py --clean       # 4. 执行清理
python3 run.py --report      # 5. 查看报告
```

### 7.2 新手路径（首次使用）

1. 阅读本指南的「能力边界」和「标准流程」
2. 运行 `--selftest` 确认环境
3. 使用 `--scan` 了解缓存分布
4. 使用 `--preview` 确认无误后执行 `--clean`
5. 保存 `--report` 输出作为记录

### 7.3 进阶路径（日常维护）

1. 配置 cron 定期执行 `--scan` 并邮件通知
2. 自定义白名单，保护特定应用的缓存
3. 使用 `--restore` 恢复误删文件
4. 定期清理回收站（超过 30 天的备份自动删除）
5. 结合 `--json` 输出对接监控系统

---

## 八、参数参考

| 参数 | 说明 | 默认值 | 示例 |
|------|------|--------|------|
| `--scan` | 扫描缓存目录 | - | `--scan --json` |
| `--preview` | 生成待删清单 | - | `--preview --min-size 100M` |
| `--clean` | 执行清理 | - | `--clean --dry-run` |
| `--restore` | 从回收站恢复 | - | `--restore --date 2026-08-09` |
| `--report` | 生成报告 | - | `--report --format md` |
| `--selftest` | 环境自检 | - | `--selftest` |
| `--version` | 显示版本 | - | `--version` |
| `--min-size` | 最小文件大小 | 10M | `--min-size 50M` |
| `--dry-run` | 试运行（不实际删除） | false | `--clean --dry-run` |
| `--json` | JSON 格式输出 | false | `--scan --json` |
| `--force` | 强制清理（跳过安全检查） | false | `--clean --force` |

---

## 九、用户协议

<!-- user-agreement-injected -->

**使用本 Skill 即表示您同意以下条款：**

1. **责任承担**：使用者自行承担因使用本 Skill 产生的全部责任。包括但不限于数据丢失、系统异常、应用故障等。
2. **禁止反向工程**：不得对本 Skill 进行反向工程、反编译、破解或试图提取源代码。
3. **合法使用**：仅用于合法目的，不得用于任何违反法律法规的行为。
4. **无担保**：本 Skill 按"现状"提供，不提供任何明示或暗示的担保。
5. **修改与分发**：允许修改和分发，但必须保留原始版权声明。

---

## 十、许可证（License）

<!-- professional-license-embedded -->

**MIT License**

Copyright (c) 2026 原创作者（自持版权）

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

*本 Skill 由 AI 辅助生成，仅供参考。使用前请阅读相关文档并自行评估风险。*
