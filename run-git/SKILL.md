---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: run-git
name: run-git
displayName: Git日常操作 版本控制 代码管理
description: 提供Git日常操作的结构化处理流程与规范输出，辅助代码版本管理。
version: 1.0.2
rules_version: cpr-20260819-n551
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/run-git
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 林墨
agent_created: true
trigger_words: ["run git", "git操作", "代码管理", "版本控制", "git命令", "提交代码", "分支管理", "代码回滚"]
---

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->


> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# run-git Skill 文档

## 一、能力边界（一页纸速查卡）

### 1.1 能做什么

| 序号 | 能力项 | 说明 | 典型场景 |
|------|--------|------|----------|
| 1 | 日常提交 | 规范 commit message，按类型分类 | 功能开发、Bug 修复 |
| 2 | 分支管理 | 创建、切换、合并、删除分支 | 功能分支开发、热修复 |
| 3 | 状态检查 | 查看工作区/暂存区状态 | 提交前确认、冲突排查 |
| 4 | 历史追溯 | 查看提交记录、文件变更 | 代码审查、问题定位 |
| 5 | 回滚操作 | 撤销提交、恢复文件 | 误提交、版本回退 |
| 6 | 远程同步 | push/pull/fetch 操作 | 团队协作、代码同步 |
| 7 | 冲突处理 | 合并冲突识别与解决 | 多人协作合并 |

### 1.2 不能做什么

| 序号 | 限制项 | 说明 |
|------|--------|------|
| 1 | 不自动修复冲突 | 冲突需要人工判断，Skill 仅提供定位与建议 |
| 2 | 不操作远程仓库权限 | 无权限的仓库无法推送，需先配置 SSH/HTTPS 凭据 |
| 3 | 不处理大文件 | 超过 100MB 的文件建议使用 Git LFS，本 Skill 不涉及 |
| 4 | 不执行危险操作 | 如 `git push --force` 需人工确认，Skill 不自动执行 |
| 5 | 不管理子模块 | 子模块操作需单独处理，本 Skill 不覆盖 |

### 1.3 适用对象

- **适用**：个人开发者、小型团队（≤10人）、日常 Git 操作频繁的技术人员
- **不适用**：大型企业级 Git 管理、Git 服务器运维、复杂 CI/CD 流水线配置

---

## 二、触发方式

### 2.1 触发词速查

| 触发词 | 场景说明 |
|--------|----------|
| `run git` | 通用触发，进入 Git 操作流程 |
| `git操作` | 中文场景触发 |
| `代码管理` | 需要管理代码版本时 |
| `版本控制` | 需要回滚或查看历史时 |
| `git命令` | 需要具体命令指导时 |
| `提交代码` | 需要提交代码时 |
| `分支管理` | 需要处理分支时 |
| `代码回滚` | 需要撤销操作时 |

### 2.2 场景映射表

| 用户说（大白话） | Skill 执行动作 |
|------------------|----------------|
| "我把代码改乱了，想恢复" | 执行状态检查 → 定位变更 → 提供回滚方案 |
| "怎么把代码提交上去" | 执行 add → commit → push 流程 |
| "想开个新分支做功能" | 执行 branch 创建 → checkout 切换 |
| "合并代码时冲突了怎么办" | 执行冲突定位 → 提供解决步骤 |
| "想看下昨天改了什么" | 执行 log 查询 → 展示变更摘要 |

---

## 三、标准流程

### 3.1 前置条件

| 条件项 | 要求 | 检查方法 |
|--------|------|----------|
| Git 已安装 | 版本 ≥ 2.0 | `git --version` |
| 仓库已初始化 | 存在 `.git` 目录 | `ls -a` 查看 |
| 远程仓库已配置 | 有 origin 或对应 remote | `git remote -v` |
| 用户信息已配置 | user.name 和 user.email | `git config --list` |

### 3.2 执行步骤

#### 步骤 1：状态检查

```bash
git status
```

**输出规范**：
- 列出所有变更文件（新增/修改/删除）
- 区分暂存区（Staged）和工作区（Unstaged）
- 标记未跟踪文件（Untracked）

#### 步骤 2：变更审查

```bash
git diff              # 查看未暂存变更
git diff --staged     # 查看已暂存变更
```

**审查要点**：
- 确认变更内容符合预期
- 检查是否有敏感信息（密码、密钥）
- 确认无调试代码残留

#### 步骤 3：暂存与提交

```bash
git add <file1> <file2>    # 按文件添加
git add .                  # 添加全部（谨慎使用）
git commit -m "type(scope): description"
```

**Commit Message 规范**：

| 类型 | 说明 | 示例 |
|------|------|------|
| feat | 新功能 | `feat(auth): 添加登录验证` |
| fix | 修复 Bug | `fix(parser): 修复空值处理` |
| docs | 文档变更 | `docs(readme): 更新安装说明` |
| refactor | 重构 | `refactor(utils): 提取公共方法` |
| test | 测试相关 | `test(api): 添加接口测试` |
| chore | 构建/工具 | `chore(deps): 升级依赖版本` |

#### 步骤 4：推送与同步

```bash
git push origin <branch>    # 推送当前分支
git pull origin <branch>    # 拉取并合并
git fetch origin            # 仅拉取不合并
```

**推送前检查清单**：
- [ ] 本地 commit 是否完整
- [ ] 是否已 pull 最新代码
- [ ] 是否有冲突需要处理

#### 步骤 5：结果确认

```bash
git log --oneline -5       # 查看最近提交
git status                 # 确认工作区干净
```

### 3.3 输出规范

所有操作完成后，输出以下格式的结果摘要：

```
操作类型：<提交/推送/回滚/合并>
涉及分支：<branch-name>
变更文件：<file-count> 个文件
提交哈希：<commit-hash>
操作状态：成功/失败
耗时：<duration> 秒
```

---

## 四、置信度门控

### 4.1 信息不足处理

当遇到以下情况时，输出 `[需核实:字段]` 占位符，不进行猜测：

| 场景 | 占位符示例 | 处理方式 |
|------|------------|----------|
| 远程仓库地址未知 | `[需核实:remote-url]` | 提示用户提供 |
| 分支名不确定 | `[需核实:branch-name]` | 列出当前分支供选择 |
| 提交信息不明确 | `[需核实:commit-message]` | 提供模板供填写 |
| 冲突解决策略未知 | `[需核实:conflict-strategy]` | 说明两种策略供选择 |

### 4.2 禁止编造的场景

- 不猜测远程仓库 URL
- 不虚构 commit hash
- 不假设用户的操作意图
- 不推断未提供的文件路径

---

## 五、错误码体系

### 5.1 常见错误速查

| 错误码 | 错误描述 | 提示话术 | 修正步骤 |
|--------|----------|----------|----------|
| GIT-001 | 不是 Git 仓库 | "当前目录不是 Git 仓库，请确认路径" | `git init` 或切换到正确目录 |
| GIT-002 | 无提交权限 | "没有权限推送到远程仓库" | 检查 SSH key / 凭据配置 |
| GIT-003 | 合并冲突 | "检测到合并冲突，需要手动解决" | 打开冲突文件 → 选择保留内容 → `git add` → `git commit` |
| GIT-004 | 分支不存在 | "指定的分支不存在" | `git branch -a` 查看所有分支 |
| GIT-005 | 工作区不干净 | "有未提交的变更，无法执行此操作" | `git stash` 暂存或先提交 |
| GIT-006 | 远程连接失败 | "无法连接远程仓库，请检查网络" | `git remote -v` 确认地址 → 检查网络 |
| GIT-007 | 提交信息为空 | "提交信息不能为空" | 使用 `git commit -m "描述"` 重新提交 |

### 5.2 错误处理流程

```
检测到错误 → 输出错误码和描述 → 提供修正步骤 → 用户确认后重试
```

---

## 六、FAQ 反模式

### 6.1 常见坑与反模式对照

| 坑（反模式） | 问题描述 | 正确做法 |
|--------------|----------|----------|
| 直接 `git add .` | 可能提交不需要的文件 | 先 `git status` 确认，按需添加 |
| 提交信息随意写 | 无法追溯变更原因 | 使用规范格式 `type(scope): description` |
| 频繁 pull 不 fetch | 可能引入意外合并 | 先 `git fetch` 查看差异再决定 |
| 忽略冲突直接 push | 会破坏他人代码 | 先解决冲突，测试通过后再推送 |
| 使用 `--force` 推送 | 覆盖远程历史 | 仅在明确需要时使用，并通知团队 |
| 不检查 diff 就提交 | 可能提交错误内容 | 提交前 `git diff` 审查变更 |

### 6.2 反模式示例

**反模式**：
```bash
git add .
git commit -m "update"
git push --force
```

**正确做法**：
```bash
git status
git add src/utils/parser.js
git diff --staged
git commit -m "fix(parser): 修复空值处理逻辑"
git push origin main
```

---

## 七、渐进式披露

### 7.1 速查卡（30 秒上手）

```bash
# 查看状态
git status

# 添加并提交
git add <file>
git commit -m "type: description"

# 推送
git push origin <branch>

# 拉取
git pull origin <branch>
```

### 7.2 新手阅读路径

1. 先读「能力边界」了解能做什么
2. 按「标准流程」执行一次完整操作
3. 遇到问题查「错误码体系」
4. 参考「FAQ 反模式」避免常见坑

### 7.3 进阶阅读路径

1. 深入理解「Commit Message 规范」
2. 掌握「冲突处理」完整流程
3. 学习「回滚操作」的多种方式
4. 了解「远程同步」的最佳实践

---

## 八、附录

### 8.1 常用命令速查表

| 命令 | 用途 | 示例 |
|------|------|------|
| `git init` | 初始化仓库 | `git init` |
| `git clone` | 克隆仓库 | `git clone <url>` |
| `git branch` | 分支管理 | `git branch -a` |
| `git checkout` | 切换分支 | `git checkout -b feature` |
| `git merge` | 合并分支 | `git merge feature` |
| `git stash` | 暂存变更 | `git stash save "wip"` |
| `git log` | 查看历史 | `git log --oneline` |
| `git reset` | 重置 | `git reset --hard HEAD~1` |

### 8.2 参数边界值

| 参数 | 最小值 | 最大值 | 建议值 |
|------|--------|--------|--------|
| commit message 长度 | 1 字符 | 72 字符 | 20-50 字符 |
| 单次提交文件数 | 1 个 | 不限 | ≤10 个 |
| 分支名长度 | 1 字符 | 255 字符 | 10-30 字符 |
| 单次 push 提交数 | 1 个 | 不限 | ≤5 个 |

---

## 用户协议

**使用本 Skill 即表示您同意以下条款：**

1. **责任承担**：使用者自行承担使用本 Skill 产生的全部责任。本 Skill 提供的所有操作建议仅供参考，不构成任何形式的保证或承诺。

2. **操作风险**：Git 操作涉及代码变更，任何操作都可能对代码库产生影响。执行操作前请务必备份重要数据，并确认操作的必要性和正确性。

3. **禁止反向工程**：未经许可，不得对本 Skill 进行反向工程、反编译、破解或试图提取源代码。

4. **合规使用**：使用者应遵守所在国家/地区的法律法规，不得将本 Skill 用于任何非法用途。

5. **免责声明**：本 Skill 按"原样"提供，不附带任何明示或暗示的保证。因使用本 Skill 造成的任何直接或间接损失，作者不承担任何责任。

<!-- user-agreement-injected -->

---

## 许可证（License）

### MIT License

```
MIT License

Copyright (c) 2024 林墨

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

*本 Skill 由 AI 辅助生成，仅供参考。使用前请阅读相关文档。*
