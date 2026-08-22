---
slug: run-git
name: run-git
displayName: Git操作 版本控制 代码管理
description: 提供Git日常操作的结构化处理流程与规范输出，辅助代码版本管理。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: SkillForge
agent_created: true
trigger_words: ["run git", "git操作", "代码管理", "版本控制", "git命令", "提交代码", "分支管理", "仓库同步"]

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# run-git — Git 操作结构化处理 Skill

## 一、能力边界（一页纸速查卡）

### 1.1 能做与不能做

| 维度 | 能做 ✅ | 不能做 ❌ |
|------|---------|-----------|
| **仓库操作** | 初始化仓库、克隆远程仓库、查看状态与日志 | 无法直接访问远程服务器，需本地已配置 SSH/HTTPS 凭据 |
| **日常提交** | 暂存文件、提交变更、查看差异、撤销误操作 | 无法自动解决合并冲突，需人工介入判断 |
| **分支管理** | 创建/切换/删除分支、合并分支、查看分支图 | 无法强制推送（force push）到受保护分支 |
| **同步操作** | 拉取（pull）、推送（push）、获取（fetch） | 无法处理网络认证弹窗，需预先配置凭据存储 |
| **批量处理** | 对多个文件执行统一操作（如同一提交信息） | 无法智能判断哪些文件应归入同一逻辑提交 |
| **数据安全** | 提供备份建议、操作前检查清单 | 无法恢复已执行 `git reset --hard` 后未备份的数据 |

### 1.2 适用对象

- **适用**：个人开发者、小型团队（5人以下）、需要规范化 Git 操作流程的初学者
- **不适用**：大型团队复杂分支策略管理、需要代码审查自动化流水线的场景

### 1.3 输入输出速查

| 项目 | 说明 |
|------|------|
| **输入** | 待处理的 Git 仓库路径、目标操作类型、文件列表 |
| **输出** | 结构化操作步骤、执行结果摘要、风险提示 |
| **耗时** | 单次操作约 1-3 分钟（不含网络等待） |

---

## 二、触发方式

### 2.1 触发词映射表

| 用户说（大白话） | 触发意图 | Skill 响应 |
|------------------|----------|------------|
| "帮我提交代码" | 提交变更 | 进入标准提交流程 |
| "git 操作" | 通用 Git 帮助 | 展示能力清单与使用指南 |
| "代码管理" | 版本控制咨询 | 提供仓库管理建议 |
| "版本控制" | 版本管理需求 | 解释 Git 基础概念与操作 |
| "git 命令" | 具体命令查询 | 给出命令参数与示例 |
| "分支怎么弄" | 分支操作 | 展示分支管理流程 |
| "代码同步一下" | 拉取/推送 | 执行同步操作流程 |

### 2.2 触发条件

- 用户明确提到 Git 相关操作需求
- 用户描述代码版本管理场景（如"代码乱了"、"想回退版本"）
- 用户询问 Git 命令用法或操作流程

---

## 三、标准流程

### 3.1 前置条件检查

执行任何 Git 操作前，必须确认以下条件：

| 检查项 | 验证方法 | 通过标准 |
|--------|----------|----------|
| Git 已安装 | 终端执行 `git --version` | 输出版本号 ≥ 2.20 |
| 仓库已初始化 | 执行 `git rev-parse --git-dir` | 输出 `.git` 路径 |
| 用户身份已配置 | 执行 `git config user.name` 和 `git config user.email` | 均有非空输出 |
| 工作区状态清晰 | 执行 `git status --short` | 无未预期的冲突标记 |
| 远程连接可用 | 执行 `git remote -v` | 输出远程地址（如无远程则跳过） |

### 3.2 执行步骤（分步编号）

#### 步骤 1：确认操作类型

根据用户需求，确定操作类别：

| 操作类型 | 关键词 | 对应流程 |
|----------|--------|----------|
| `commit` | 提交、保存、记录 | 流程 A |
| `branch` | 分支、切换、合并 | 流程 B |
| `sync` | 拉取、推送、同步 | 流程 C |
| `inspect` | 查看、日志、状态 | 流程 D |
| `revert` | 回退、撤销、恢复 | 流程 E |

#### 流程 A：提交变更

```bash
# 第1步：查看当前状态
git status

# 第2步：查看具体差异
git diff

# 第3步：暂存文件（按需选择）
git add <file1> <file2>    # 指定文件
git add .                  # 全部暂存（需确认无敏感文件）

# 第4步：提交（必须写清晰的信息）
git commit -m "feat: 添加用户登录功能"
```

**提交信息规范**：
- 格式：`<type>: <描述>`
- type 可选值：`feat`（新功能）、`fix`（修复）、`docs`（文档）、`refactor`（重构）、`test`（测试）
- 描述使用中文，控制在 20 字以内

#### 流程 B：分支管理

```bash
# 创建并切换新分支
git checkout -b feature/user-login

# 查看所有分支
git branch -a

# 合并分支（先切到目标分支）
git checkout main
git merge feature/user-login

# 删除已合并分支
git branch -d feature/user-login
```

**分支命名规范**：
- 功能分支：`feature/<功能名>`
- 修复分支：`fix/<问题描述>`
- 发布分支：`release/<版本号>`

#### 流程 C：同步操作

```bash
# 拉取远程更新（推荐使用 rebase 保持线性历史）
git pull --rebase

# 推送本地提交
git push origin <branch-name>

# 首次推送新分支
git push -u origin <branch-name>
```

**推送前检查清单**：
- [ ] 本地提交信息完整规范
- [ ] 已执行 `git pull --rebase` 解决潜在冲突
- [ ] 确认推送目标分支正确

#### 流程 D：状态查看

```bash
# 查看精简状态
git status -s

# 查看最近5条提交
git log --oneline -5

# 查看某文件修改历史
git log --oneline -- <file-path>
```

#### 流程 E：回退操作

```bash
# 撤销工作区修改（未暂存）
git checkout -- <file>

# 撤销暂存（保留修改）
git reset HEAD <file>

# 回退到上一个提交（保留修改）
git reset --soft HEAD~1

# 回退到指定提交（丢弃修改，慎用）
git reset --hard <commit-hash>
```

### 3.3 输出规范

每次操作完成后，输出以下格式的结果摘要：

```
操作类型：提交变更
执行结果：成功 ✅
变更文件：3 个（新增 2，修改 1）
提交哈希：a1b2c3d
提交信息：feat: 添加用户登录功能
风险提示：无
```

---

## 四、置信度门控

### 4.1 信息不足处理

当遇到以下情况时，输出 `[需核实:字段]` 占位符，**不编造**任何信息：

| 场景 | 占位输出 | 后续动作 |
|------|----------|----------|
| 用户未指定目标分支 | `[需核实:目标分支名称]` | 询问用户确认 |
| 远程仓库地址未知 | `[需核实:远程仓库URL]` | 请用户提供或检查 `git remote -v` |
| 提交信息不明确 | `[需核实:提交描述]` | 请用户补充具体变更内容 |
| 冲突文件无法自动解决 | `[需核实:冲突解决方案]` | 展示冲突文件列表，请用户决策 |

### 4.2 禁止行为

- ❌ 不猜测远程仓库地址
- ❌ 不假设用户意图（如不确定提交范围，先询问）
- ❌ 不执行可能造成数据丢失的命令（如 `git reset --hard`）前不确认

---

## 五、错误码体系

| 错误码 | 错误描述 | 提示话术 | 修正步骤 |
|--------|----------|----------|----------|
| `GIT-001` | 不是 Git 仓库 | "当前目录未初始化 Git 仓库" | 执行 `git init` 或切换到正确目录 |
| `GIT-002` | 用户身份未配置 | "请先配置 Git 用户信息" | 执行 `git config --global user.name "你的名字"` 和 `git config --global user.email "你的邮箱"` |
| `GIT-003` | 提交信息为空 | "提交信息不能为空" | 使用 `git commit -m "描述"` 重新提交 |
| `GIT-004` | 推送被拒绝（非快进） | "远程有更新，需要先拉取" | 执行 `git pull --rebase` 后重新推送 |
| `GIT-005` | 合并冲突 | "存在冲突文件，需手动解决" | 打开冲突文件，保留正确内容后执行 `git add` 和 `git commit` |
| `GIT-006` | 分支不存在 | "未找到指定分支" | 执行 `git branch -a` 查看可用分支 |
| `GIT-007` | 文件不存在 | "指定文件不在工作区" | 执行 `git status` 确认文件路径 |
| `GIT-008` | 远程连接失败 | "无法连接远程仓库" | 检查网络、SSH 密钥或 HTTPS 凭据配置 |

---

## 六、FAQ 反模式

### 6.1 常见坑与反模式对照

| 反模式 ❌ | 问题描述 | 正确做法 ✅ |
|-----------|----------|-------------|
| **盲目 `git add .`** | 可能暂存敏感文件（如 `.env`、密钥文件） | 先执行 `git status` 检查，使用 `.gitignore` 排除敏感文件 |
| **提交信息写"修改"** | 无法追溯变更意图 | 使用规范格式：`feat: 添加XX功能` / `fix: 修复XX问题` |
| **直接 `git pull` 不处理冲突** | 产生合并提交，历史混乱 | 使用 `git pull --rebase`，冲突时手动解决 |
| **`git reset --hard` 后后悔** | 未提交的修改永久丢失 | 操作前先 `git stash` 或备份，确认无误再执行 |
| **推送前不拉取** | 推送被拒绝，产生冲突 | 推送前先 `git pull --rebase` 同步 |
| **在 main 分支直接开发** | 主分支不稳定，难以回退 | 创建功能分支开发，合并前审查 |

### 6.2 反模式自查清单

- [ ] 我是否清楚本次操作涉及哪些文件？
- [ ] 我的提交信息是否描述了"为什么"而不仅是"做了什么"？
- [ ] 我是否已检查 `.gitignore` 排除敏感文件？
- [ ] 推送前是否已同步远程最新代码？
- [ ] 回退操作前是否已备份重要修改？

---

## 七、渐进式披露

### 7.1 速查卡（新手必读）

```
Git 日常操作三连：
1. git status          → 看状态
2. git add <文件>      → 暂存
3. git commit -m "描述" → 提交

同步两件套：
git pull --rebase      → 拉取
git push               → 推送

回退安全阀：
git checkout -- <文件> → 放弃修改（安全）
git reset --soft HEAD~1 → 撤销提交（保留修改）
```

### 7.2 分层次阅读路径

#### 新手路径（首次使用）

1. 阅读「能力边界」了解适用范围
2. 按「标准流程」中的流程 A 完成第一次提交
3. 遇到问题查「错误码体系」
4. 操作前对照「反模式自查清单」

#### 进阶路径（日常使用）

1. 熟悉所有流程（A-E），掌握分支管理
2. 理解「置信度门控」，学会在信息不足时主动确认
3. 建立个人提交信息规范，保持历史清晰
4. 定期使用 `git log --graph` 检查仓库健康度

#### 专家路径（深度使用）

1. 结合 `git rebase -i` 整理提交历史
2. 使用 `git cherry-pick` 选择性合并提交
3. 配置 Git hooks 自动化检查
4. 理解 reflog 用于紧急恢复

---

## 八、使用示例

### 示例 1：完整提交流程

**用户输入**："帮我提交代码，改了登录页面的样式"

**Skill 响应**：

```
正在执行提交流程...

第1步：检查仓库状态
✅ 仓库已初始化
✅ 用户身份已配置

第2步：查看变更文件
M  src/pages/login.css
M  src/pages/login.html

第3步：确认提交范围
变更文件：2 个
是否确认提交？(y/n)：y

第4步：提交变更
git add src/pages/login.css src/pages/login.html
git commit -m "style: 优化登录页面样式"

✅ 提交成功
提交哈希：f3e2d1c
```

### 示例 2：分支合并流程

**用户输入**："把 feature 分支合并到 main"

**Skill 响应**：

```
正在执行分支合并...

第1步：确认分支状态
当前分支：main
目标分支：feature/user-login

第2步：检查合并冲突
✅ 无冲突

第3步：执行合并
git merge feature/user-login

✅ 合并成功
合并提交：a9b8c7d
```

---

## 九、用户协议

<!-- user-agreement-injected -->

**使用本 Skill 即表示您同意以下条款：**

1. **责任承担**：使用者自行承担因使用本 Skill 进行 Git 操作所产生的一切后果。本 Skill 提供的操作建议仅供参考，不构成对任何特定操作结果的保证。

2. **数据安全**：使用者应对重要数据自行备份。本 Skill 不对因操作失误（如误执行 `git reset --hard`、误删分支等）导致的数据丢失负责。

3. **禁止反向工程**：使用者不得对本 Skill 的底层逻辑、提示词结构、决策机制进行反向工程、反编译或提取核心算法。

4. **合规使用**：使用者应遵守所在组织及所在地法律法规，不得利用本 Skill 进行任何非法活动。

5. **免责声明**：本 Skill 按"现状"提供，不附带任何明示或暗示的担保，包括但不限于适销性、特定用途适用性和非侵权保证。

---

## 十、许可证（License）

<!-- professional-license-embedded -->

**MIT License**

Copyright (c) 2024 SkillForge

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
