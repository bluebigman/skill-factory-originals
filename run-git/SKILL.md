---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: run-git
name: run-git
displayName: Git日常操作 版本管理 代码协作
description: 提供Git日常操作的结构化处理流程与规范输出，辅助代码版本管理。
version: 1.0.4
rules_version: cpr-20260820-n601
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/run-git
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: FlowForge
agent_created: true
trigger_words: ["run git", "git操作", "代码管理", "版本控制", "git命令", "git提交", "分支管理", "代码回滚"]
---

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->


> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# Git 操作导航 Skill

## 一、能力边界（一页纸速查卡）

### 本 Skill 能做什么

| 编号 | 能力项 | 说明 | 典型耗时 |
|------|--------|------|----------|
| 1 | 状态检视 | 查看工作区、暂存区、本地仓库的当前状态 | 秒级 |
| 2 | 文件暂存 | 将指定文件或全部改动加入暂存区 | 秒级 |
| 3 | 提交记录 | 按规范格式创建提交，附带清晰描述 | 分钟级 |
| 4 | 远程同步 | 推送本地提交至远程仓库，或拉取远程更新 | 分钟级 |
| 5 | 分支管理 | 创建、切换、合并、删除分支 | 分钟级 |
| 6 | 历史追溯 | 查看提交历史、定位关键节点 | 秒级 |
| 7 | 撤销与回滚 | 撤销工作区修改、重置提交、回退版本 | 分钟级 |
| 8 | 冲突处理 | 识别并解决合并过程中的文件冲突 | 视复杂度而定 |

### 本 Skill 不能做什么

| 编号 | 限制项 | 说明 |
|------|--------|------|
| 1 | 不替代代码审查 | 不判断代码质量，只处理版本管理动作 |
| 2 | 不自动解决冲突 | 冲突需要人工判断保留哪部分内容 |
| 3 | 不处理认证问题 | SSH 密钥、访问令牌等需自行配置 |
| 4 | 不管理远程仓库 | 创建远程仓库需在托管平台操作 |
| 5 | 不处理大文件 | 超过 100MB 的文件需使用 Git LFS |

### 适用对象

- 刚接触 Git 的开发者，需要一套可照做的操作指引
- 日常使用 Git 但偶尔忘记命令细节的工程师
- 需要统一团队提交规范的协作场景

---

## 二、触发方式与场景映射

当对话中出现以下意图时，本 Skill 将被激活：

| 触发词/短语 | 用户实际意图 | 本 Skill 响应动作 |
|-------------|--------------|-------------------|
| "run git" | 需要执行 Git 操作 | 询问具体操作类型，提供对应命令 |
| "git操作" | 想了解或执行 Git 命令 | 展示速查卡，定位具体需求 |
| "代码管理" | 需要管理代码版本 | 引导至状态检视或提交流程 |
| "版本控制" | 需要处理版本相关事务 | 提供分支、回滚等方案 |
| "git命令" | 查询某个命令的用法 | 给出命令参数表与示例 |
| "提交代码" | 想将改动保存到仓库 | 走标准提交流程 |
| "分支管理" | 需要创建或切换分支 | 提供分支操作指引 |
| "代码回滚" | 需要撤销或回退版本 | 区分 reset/revert/checkout 场景 |

---

## 三、标准操作流程

### 前置条件

| 检查项 | 验证方法 | 通过标准 |
|--------|----------|----------|
| Git 已安装 | `git --version` | 输出版本号 |
| 已配置用户信息 | `git config user.name` 和 `git config user.email` | 均有返回值 |
| 已初始化仓库 | `git rev-parse --is-inside-work-tree` | 输出 `true` |
| 远程仓库可达 | `git remote -v` | 显示远程地址 |

### 执行步骤（分步编号）

#### 流程 A：首次提交

```
步骤 1  初始化仓库（如尚未初始化）
        git init

步骤 2  查看当前状态
        git status
        # 确认哪些文件处于未跟踪状态

步骤 3  暂存所有改动
        git add .
        # 或指定文件：git add src/main.py

步骤 4  创建提交
        git commit -m "feat: 初始化项目结构"
        # 提交信息格式见「Commit Message 规范」

步骤 5  关联远程仓库（如需要推送）
        git remote add origin <远程仓库地址>

步骤 6  推送至远程
        git push -u origin main
        # -u 参数建立本地分支与远程分支的关联
```

#### 流程 B：日常迭代

```
步骤 1  拉取最新代码
        git pull --rebase
        # --rebase 保持提交历史线性，减少合并节点

步骤 2  创建功能分支
        git checkout -b feature/用户登录

步骤 3  开发完成后暂存改动
        git add src/ 测试用例/

步骤 4  提交改动
        git commit -m "feat: 实现用户登录功能"

步骤 5  推送分支至远程
        git push -u origin feature/用户登录

步骤 6  合并至主分支
        git checkout main
        git pull --rebase
        git merge --no-ff feature/用户登录
        # --no-ff 保留分支合并记录，便于追溯

步骤 7  推送主分支
        git push
```

#### 流程 C：撤销与回滚

| 场景 | 命令 | 说明 | 风险等级 |
|------|------|------|----------|
| 撤销工作区未暂存修改 | `git checkout -- <文件名>` | 丢弃工作区改动 | 低（不可恢复） |
| 撤销暂存区修改 | `git reset HEAD <文件名>` | 将文件移出暂存区，保留工作区改动 | 低 |
| 撤销最近一次提交（保留改动） | `git reset --soft HEAD~1` | 提交撤销，改动回到暂存区 | 中 |
| 撤销最近一次提交（丢弃改动） | `git reset --hard HEAD~1` | 提交和改动全部丢弃 | 高（不可恢复） |
| 回退已推送的提交 | `git revert <commit-hash>` | 生成反向提交，保留历史 | 低（推荐） |

### 输出规范

每次操作完成后，按以下格式输出结果摘要：

```
操作类型：<提交/推送/拉取/合并/回滚>
执行结果：<成功/失败>
影响范围：<涉及的文件或分支>
当前状态：<HEAD 位置、工作区是否干净>
后续建议：<如有需要>
```

---

## 四、Commit Message 规范

### 格式模板

```
<type>(<scope>): <subject>

<body>

<footer>
```

### type 取值表

| type | 含义 | 示例 |
|------|------|------|
| feat | 新功能 | `feat: 添加用户注册接口` |
| fix | 修复缺陷 | `fix: 修复登录超时问题` |
| docs | 文档变更 | `docs: 更新 README` |
| style | 格式调整 | `style: 统一缩进为两个空格` |
| refactor | 重构代码 | `refactor: 抽取公共方法` |
| test | 测试相关 | `test: 补充边界值测试用例` |
| chore | 构建/工具 | `chore: 升级依赖版本` |

### 规范要求

| 规则 | 说明 |
|------|------|
| subject 不超过 50 字符 | 简洁描述本次改动 |
| 使用祈使句 | 如 "添加" 而非 "添加了" |
| 不省略关键信息 | 让读者不看代码也能理解改动意图 |
| 关联 issue（如有） | 在 footer 中标注 `Closes #123` |

---

## 五、置信度门控

当遇到以下情况时，本 Skill 不会猜测或编造信息，而是输出占位符提示：

| 场景 | 输出格式 |
|------|----------|
| 不确定远程仓库地址 | `[需核实:远程仓库URL]` |
| 不确定当前分支名称 | `[需核实:当前分支名]` |
| 不确定提交哈希值 | `[需核实:commit-hash]` |
| 不确定文件具体路径 | `[需核实:文件路径]` |
| 不确定用户邮箱配置 | `[需核实:user.email]` |

**原则**：信息不足时，先询问用户获取准确信息，再执行操作。

---

## 六、错误码体系

| 错误码 | 错误现象 | 提示话术 | 修正步骤 |
|--------|----------|----------|----------|
| GIT-001 | `fatal: not a git repository` | 当前目录不是 Git 仓库 | ① 确认目录路径 ② 执行 `git init` 或切换到正确目录 |
| GIT-002 | `fatal: unable to access` | 无法连接远程仓库 | ① 检查网络 ② 确认远程地址 ③ 验证认证信息 |
| GIT-003 | `error: failed to push some refs` | 推送被拒绝，远程有本地没有的提交 | ① 执行 `git pull --rebase` ② 解决冲突 ③ 重新推送 |
| GIT-004 | `CONFLICT (content)` | 合并时发生内容冲突 | ① 打开冲突文件 ② 查找 `<<<<<<<` 标记 ③ 手动编辑保留内容 ④ 删除标记 ⑤ 执行 `git add` ⑥ 完成合并 |
| GIT-005 | `fatal: refusing to merge unrelated histories` | 两个仓库没有共同历史 | ① 确认是否确实需要合并 ② 如需要，加 `--allow-unrelated-histories` 参数 |
| GIT-006 | `error: Your local changes would be overwritten` | 本地修改与拉取内容冲突 | ① 暂存本地修改 `git stash` ② 拉取更新 ③ 恢复修改 `git stash pop` |
| GIT-007 | `warning: LF will be replaced by CRLF` | 换行符格式警告 | ① 确认团队换行符规范 ② 配置 `git config core.autocrlf` |

---

## 七、FAQ 反模式对照

| 编号 | 常见坑 | 反模式（错误做法） | 正模式（推荐做法） |
|------|--------|-------------------|-------------------|
| 1 | 直接在主分支开发 | 所有改动直接提交到 main 分支 | 创建功能分支，开发完成后再合并 |
| 2 | 提交信息随意 | `git commit -m "update"` | 按规范写清楚改动内容和原因 |
| 3 | 频繁无意义提交 | 每改一行就提交一次 | 完成一个逻辑单元后再提交 |
| 4 | 强制推送覆盖远程 | `git push --force` 覆盖他人提交 | 使用 `git revert` 或 `git push --force-with-lease` |
| 5 | 忽略冲突直接强制合并 | 用 `-X theirs` 或 `-X ours` 跳过冲突处理 | 手动检查冲突内容，确认保留正确代码 |
| 6 | 提交大文件 | 将 500MB 的模型文件直接提交 | 使用 Git LFS 或排除在版本控制之外 |

---

## 八、渐进式阅读路径

### 新手路径（首次使用）

1. 阅读「能力边界」了解工具范围
2. 使用「标准操作流程」中的流程 A 完成首次提交
3. 遇到问题查「错误码体系」对照修正
4. 熟悉后学习「Commit Message 规范」提升提交质量

### 进阶路径（日常使用）

1. 掌握「标准操作流程」中的流程 B 和流程 C
2. 深入理解「FAQ 反模式对照」避免常见错误
3. 学习分支策略：Git Flow（适合版本发布）或 GitHub Flow（适合持续部署）
4. 理解 fetch / pull / push 的区别：
   - `fetch`：仅下载远程更新，不合并
   - `pull`：下载并合并（等于 fetch + merge）
   - `push`：上传本地提交至远程

### 专家路径（团队协作）

1. 制定团队统一的 Commit Message 规范
2. 设计分支保护规则（如 main 分支禁止直接推送）
3. 建立 Code Review 流程与合并策略
4. 配置 CI/CD 流水线，自动化测试与部署

---

## 九、常用命令参数速查

| 命令 | 参数 | 作用 |
|------|------|------|
| `git add` | `-p` | 交互式暂存部分改动 |
| `git commit` | `--amend` | 修改最近一次提交信息 |
| `git log` | `--graph` | 以图形化方式显示分支历史 |
| `git log` | `--author="name"` | 按作者过滤提交记录 |
| `git branch` | `-d` | 删除已合并的分支 |
| `git branch` | `-D` | 强制删除未合并的分支 |
| `git stash` | `list` | 查看暂存列表 |
| `git stash` | `apply` | 应用最近一次暂存 |
| `git diff` | `--staged` | 查看暂存区与 HEAD 的差异 |
| `git remote` | `-v` | 查看远程仓库详细信息 |

---

## 十、分支策略建议

### Git Flow（适合正式版本发布）

```
main（生产环境）
  └── develop（开发集成）
        ├── feature/*（功能开发）
        ├── release/*（发布准备）
        └── hotfix/*（紧急修复）
```

### GitHub Flow（适合持续部署）

```
main（始终可部署）
  └── feature/*（功能开发，通过 PR 合并）
```

### 选择建议

| 团队规模 | 发布频率 | 推荐策略 |
|----------|----------|----------|
| 1-3 人 | 不定期 | GitHub Flow 简化版 |
| 5-10 人 | 定期版本 | Git Flow |
| 10+ 人 | 高频发布 | GitHub Flow + 分支保护 |

---

## 用户协议

<!-- user-agreement-injected -->

**使用本 Skill 即表示您同意以下条款：**

1. **责任承担**：使用者自行承担因使用本 Skill 产生的全部责任。本 Skill 提供的操作指引基于通用 Git 实践，不构成对特定场景的保证。在执行任何破坏性操作（如 `reset --hard`、`push --force`）前，请自行确认操作影响。

2. **禁止反向工程**：不得对本 Skill 进行反向工程、反编译、反汇编，或试图提取源代码、算法及内部逻辑。

3. **无担保声明**：本 Skill 按"现状"提供，不附带任何明示或暗示的担保，包括但不限于适销性、特定用途适用性和非侵权保证。

4. **免责范围**：因使用或无法使用本 Skill 导致的任何直接、间接、偶然、特殊或后果性损害，作者不承担任何责任。

---

## 许可证（License）

<!-- professional-license-embedded -->

**MIT License**

Copyright (c) 2024 FlowForge

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
