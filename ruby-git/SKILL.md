---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: ruby-git
name: ruby-git
displayName: Git仓库操作 命令行封装
description: 基于Ruby的Git仓库操作封装，提供命令行接口，简化日常版本控制任务。
version: 1.0.3
rules_version: cpr-20260819-n551
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/ruby-git
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 林默
agent_created: true
trigger_words: ["ruby-git", "Ruby Git 操作", "Git 仓库管理", "Git 封装库", "Ruby 版本控制", "git 命令行工具", "ruby git 封装"]
---

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->


> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# ruby-git Skill 文档

本 Skill 由 AI 辅助生成，仅供参考。使用前请自行验证命令行为与你的环境兼容。

---

## 一、能力边界（一页纸速查卡）

### 1.1 能做什么

| 编号 | 能力项 | 说明 | 典型耗时 |
|------|--------|------|----------|
| C1 | 仓库状态速览 | 一次性输出当前分支、暂存区、工作区变更摘要 | < 1 秒 |
| C2 | 批量提交 | 将指定目录下所有变更文件按预设规则分组提交 | 2-5 秒 |
| C3 | 分支清理 | 列出已合并分支并支持批量删除（需二次确认） | 3-8 秒 |
| C4 | 历史检索 | 按作者/日期/关键字过滤提交记录 | 1-3 秒 |
| C5 | 标签管理 | 创建、列出、删除轻量标签与附注标签 | 1-2 秒 |
| C6 | 配置检查 | 输出当前仓库的用户名、邮箱、远程地址等关键配置 | < 1 秒 |

### 1.2 不能做什么（明确边界）

| 编号 | 禁止事项 | 原因 |
|------|----------|------|
| X1 | 不执行 `git push --force` 或任何强制推送 | 可能造成远端历史不可逆损坏 |
| X2 | 不自动解决合并冲突 | 冲突解决需要人工判断业务语义 |
| X3 | 不修改 `.git` 内部文件 | 绕过 Git 协议层操作会导致仓库损坏 |
| X4 | 不处理子模块递归操作 | 子模块状态复杂，超出本工具设计范围 |
| X5 | 不执行 `git reset --hard` | 会丢弃工作区未提交的修改 |

### 1.3 适用对象

- **适用**：个人开发者、小型团队（≤ 10 人）、CI 脚本中需要快速获取仓库状态的场景。
- **不适用**：大型 monorepo 的精细权限管理、跨仓库原子操作、需要图形化交互的复杂合并场景。

---

## 二、触发方式

### 2.1 触发词速查

| 触发词 | 场景映射（大白话） |
|--------|-------------------|
| `ruby-git` | 直接调用工具主命令 |
| `Ruby Git 操作` | 当用户提到"用 Ruby 操作 Git"时触发 |
| `Git 仓库管理` | 当用户要求"管理一下这个仓库"时触发 |
| `Git 封装库` | 当用户询问"有没有现成的 Git 封装"时触发 |
| `Ruby 版本控制` | 当用户说"用 Ruby 做版本控制"时触发 |
| `git 命令行工具` | 当用户说"给我一个 Git 命令行工具"时触发 |
| `ruby git 封装` | 当用户说"写个 Ruby 的 Git 封装"时触发 |

### 2.2 触发优先级

当多个触发词同时出现时，按以下优先级处理：

1. 精确命令名（`ruby-git`）> 功能描述（`Git 仓库管理`）> 模糊意图（`版本控制`）
2. 若用户同时提到"批量"和"提交"，优先执行批量提交流程（见第四节）。

---

## 三、标准流程

### 3.1 前置条件

| 条件编号 | 条件内容 | 校验方式 |
|----------|----------|----------|
| P1 | 目标目录必须是一个合法的 Git 仓库 | 执行 `git rev-parse --is-inside-work-tree`，输出必须为 `true` |
| P2 | Ruby 版本 ≥ 2.6.0 | 执行 `ruby -v`，版本号第一位 ≥ 2 |
| P3 | 当前用户对仓库目录有读写权限 | 执行 `test -w .git && echo writable` |
| P4 | 环境变量 `GIT_TERMINAL_PROMPT=0`（非交互模式） | 避免远程操作时卡在凭据输入 |

### 3.2 执行步骤（分步编号）

#### 步骤 1：环境自检

```bash
ruby-git --selftest
```

预期输出：

```
[OK] Ruby version: 2.7.5
[OK] Git version: 2.39.2
[OK] Current directory is a git repo
[OK] Write permission confirmed
```

若任一检查失败，输出 `[FAIL]` 并附带具体原因，此时终止后续操作。

#### 步骤 2：状态预览（试运行）

```bash
ruby-git status --short
```

输出格式（每行一条）：

```
<状态码> <文件路径>
```

状态码取值：

| 状态码 | 含义 |
|--------|------|
| `M` | 已修改（未暂存） |
| `A` | 已新增（未暂存） |
| `D` | 已删除（未暂存） |
| `MM` | 已修改且已暂存 |
| `??` | 未跟踪 |

#### 步骤 3：批量提交（确认后执行）

```bash
ruby-git commit --all --message "feat: 批量更新" --dry-run
```

先执行 `--dry-run` 查看将要提交的文件列表。确认无误后去掉 `--dry-run` 执行真实提交。

#### 步骤 4：结果校验

```bash
ruby-git log --oneline -5
```

确认最新一条提交的 hash 与提交信息符合预期。

### 3.3 输出规范

| 输出类型 | 格式要求 | 示例 |
|----------|----------|------|
| 成功提示 | `[OK] <操作描述>` | `[OK] 已提交 3 个文件，commit hash: a1b2c3d` |
| 失败提示 | `[ERROR] <错误码>: <描述>` | `[ERROR] E1001: 目标目录不是 Git 仓库` |
| 警告提示 | `[WARN] <描述>` | `[WARN] 检测到 2 个未跟踪文件，未纳入本次提交` |

---

## 四、置信度门控

### 4.1 信息不足时的处理

当遇到以下情况时，**不得编造**信息，必须输出 `[需核实:字段]` 占位符：

| 场景 | 占位符示例 |
|------|------------|
| 远程仓库地址未知 | `[需核实:remote_url]` |
| 提交作者身份不确定 | `[需核实:author_name]` |
| 分支合并策略不明确 | `[需核实:merge_strategy]` |
| 标签版本号未指定 | `[需核实:tag_version]` |

### 4.2 门控触发条件

- 当用户请求的操作涉及**删除**或**覆盖**时，必须二次确认。
- 当用户请求的操作涉及**远程仓库**时，必须确认远程地址。
- 当用户请求的操作涉及**历史重写**（如 rebase、amend）时，直接拒绝并说明原因。

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| E1001 | 非 Git 仓库 | `当前目录不是 Git 仓库，请先执行 git init` | 1. 确认目录路径；2. 执行 `git init`；3. 重试 |
| E1002 | Ruby 版本过低 | `Ruby 版本需 ≥ 2.6.0，当前版本: <版本号>` | 1. 升级 Ruby；2. 或使用 rvm/rbenv 切换版本 |
| E1003 | 权限不足 | `无法写入 .git 目录，请检查文件权限` | 1. 执行 `ls -la .git` 查看属主；2. 使用 `sudo chown` 修正 |
| E2001 | 提交信息为空 | `提交信息不能为空，请使用 --message 参数` | 1. 补充提交信息；2. 重试 |
| E2002 | 无变更可提交 | `工作区无任何变更，无需提交` | 1. 检查文件修改时间；2. 确认是否已提交 |
| E3001 | 远程连接失败 | `无法连接远程仓库，请检查网络或凭据` | 1. 执行 `git remote -v` 确认地址；2. 检查 SSH key 或 token |
| E3002 | 分支删除冲突 | `分支 <分支名> 未完全合并，拒绝删除` | 1. 先合并该分支；2. 或使用 `--force` 参数（需二次确认） |

---

## 六、FAQ 反模式

### 6.1 常见坑与反模式对照

| 编号 | 常见坑（反模式） | 正确做法 |
|------|------------------|----------|
| F1 | **直接执行 `git add .` 后立即提交**，未检查是否包含敏感文件（如 `.env`） | 先执行 `ruby-git status --short` 人工确认，再提交 |
| F2 | **在 CI 脚本中忽略 `--dry-run`**，导致意外提交 | 所有自动化流程必须带 `--dry-run` 先行验证 |
| F3 | **使用 `git commit -am` 跳过暂存区**，误提交了未完成的工作 | 使用 `ruby-git commit --all` 前先查看 diff |
| F4 | **删除分支时不检查是否已合并** | 使用 `ruby-git branch --merged` 先列出已合并分支 |
| F5 | **在非交互环境中依赖 Git 凭据提示** | 设置 `GIT_TERMINAL_PROMPT=0`，提前配置 SSH key 或 credential helper |

### 6.2 反模式示例

```bash
# 反模式 F1：直接提交所有文件
git add .
git commit -m "update"

# 正确做法
ruby-git status --short
# 确认无敏感文件后
ruby-git commit --all --message "update" --dry-run
ruby-git commit --all --message "update"
```

---

## 七、渐进式披露

### 7.1 速查卡（30 秒上手）

```bash
# 1. 查看状态
ruby-git status --short

# 2. 试运行提交
ruby-git commit --all --message "feat: 更新" --dry-run

# 3. 真实提交
ruby-git commit --all --message "feat: 更新"

# 4. 查看最近提交
ruby-git log --oneline -5
```

### 7.2 分层次阅读路径

#### 新手路径（首次使用）

1. 阅读「一、能力边界」了解工具范围。
2. 执行 `ruby-git --selftest` 确认环境。
3. 按「7.1 速查卡」完成第一次提交。
4. 遇到问题查「五、错误码体系」。

#### 进阶路径（日常高频使用）

1. 阅读「三、标准流程」掌握完整操作规范。
2. 熟悉「六、FAQ 反模式」避免常见错误。
3. 结合 `--dry-run` 与 `status` 建立安全操作习惯。
4. 在 CI 脚本中集成 `ruby-git status --porcelain` 输出做自动化判断。

#### 专家路径（二次开发）

1. 阅读源码中的 `lib/ruby_git/commands/` 目录，了解各子命令实现。
2. 通过 `ruby-git --help` 查看所有可用参数。
3. 自定义输出格式时，参考 `--format json` 选项。

---

## 八、参数速查表

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `--selftest` | 布尔 | `false` | 执行环境自检 |
| `--version` | 布尔 | `false` | 输出版本号 |
| `--status` | 布尔 | `false` | 显示仓库状态 |
| `--short` | 布尔 | `false` | 精简输出格式 |
| `--commit` | 布尔 | `false` | 执行提交操作 |
| `--all` | 布尔 | `false` | 包含所有变更文件 |
| `--message` | 字符串 | 无 | 提交信息 |
| `--dry-run` | 布尔 | `false` | 试运行，不实际执行 |
| `--log` | 布尔 | `false` | 显示提交历史 |
| `--oneline` | 布尔 | `false` | 单行显示提交历史 |
| `--branch` | 字符串 | 无 | 指定分支名 |
| `--merged` | 布尔 | `false` | 仅显示已合并分支 |
| `--delete` | 布尔 | `false` | 删除指定分支 |
| `--tag` | 字符串 | 无 | 标签名称 |
| `--format` | 字符串 | `text` | 输出格式（text/json） |

---

## 九、用户协议

**使用本 Skill 即表示您同意以下条款：**

1. **责任承担**：使用者自行承担使用本 Skill 的全部责任。因操作不当（包括但不限于误删分支、错误推送、数据丢失）造成的任何损失，本 Skill 作者不承担任何责任。
2. **禁止反向工程**：不得对本 Skill 的源码进行反向工程、反编译、破解或试图提取底层算法。
3. **合规使用**：使用者应确保其使用场景符合当地法律法规及 GitHub/GitLab 等平台的服务条款。
4. **无担保**：本 Skill 按"现状"提供，不附带任何明示或暗示的担保，包括但不限于适销性、特定用途适用性及非侵权性。

<!-- user-agreement-injected -->

---

## 十、许可证（License）

本 Skill 采用 MIT 许可证发布。

### MIT License

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

---

*文档版本：1.0.0 | 最后更新：2026-08-19*
