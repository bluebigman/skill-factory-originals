---
slug: lazygit
name: lazygit
displayName: 终端Git可视化 分支合并 冲突处理
description: 终端里的Git图形界面，让分支合并、冲突解决、交互式暂存一目了然。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: TerminalFlow Studio
agent_created: true
trigger_words: ["lazygit", "git图形界面", "终端git", "git可视化", "分支管理", "git tui", "交互式暂存", "冲突解决"]
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# lazygit 技能手册

## 一、能力边界（一页纸速查卡）

### 1.1 工具定位

lazygit 是一个运行在终端中的 Git 图形化操作工具。它把 Git 的常用操作（暂存、提交、分支、合并、冲突处理、远程同步）组织成可键盘驱动的面板界面，让开发者在不离开终端的前提下获得可视化操作体验。

### 1.2 能做与不能做

| 维度 | 能做 | 不能做 |
|------|------|--------|
| 暂存操作 | 交互式逐行暂存、按文件暂存、批量暂存 | 自动识别暂存意图（仍需人工选择） |
| 分支管理 | 创建、切换、合并、删除分支，可视化分支拓扑 | 自动解决合并冲突（需人工编辑） |
| 冲突处理 | 定位冲突文件、调用外部编辑器、标记已解决 | 智能合并策略（依赖 Git 原生能力） |
| 提交管理 | 创建提交、修改提交信息、交互式 rebase | 自动生成提交信息（需人工输入） |
| 远程操作 | 推送、拉取、获取远程更新 | 自动处理认证凭据（依赖系统配置） |
| 文件浏览 | 查看工作区变更、文件差异对比 | 编辑文件内容（需调用外部编辑器） |
| 批量操作 | 支持自定义脚本调用部分命令 | 完全无头模式（仍需 TUI 交互） |

### 1.3 适用对象

- **适用**：日常使用 Git 的开发者、需要频繁处理分支合并的团队协作成员、偏好终端工作流的技术人员。
- **不适用**：完全不懂 Git 基础概念的新手（建议先掌握 `git add/commit/push` 等基础命令）、需要图形化 Diff 工具（如 Beyond Compare）深度集成的用户。

---

## 二、触发方式

### 2.1 触发词

| 触发词 | 场景说明 |
|--------|----------|
| `lazygit` | 直接启动工具 |
| `git图形界面` / `git可视化` | 描述需求时提及 |
| `终端git` | 强调终端环境 |
| `分支管理` | 涉及分支操作场景 |
| `git tui` | 技术术语触发 |
| `交互式暂存` | 需要逐行暂存时 |
| `冲突解决` | 处理合并冲突时 |

### 2.2 场景映射表

| 用户说 | 实际需求 | 建议操作 |
|--------|----------|----------|
| "我想看看改了哪些文件" | 查看工作区状态 | 启动 lazygit，按 `1` 进入文件面板 |
| "只提交某几行改动" | 交互式暂存 | 文件面板 → 选中文件 → `Enter` → 逐行 `Space` |
| "把 feature 分支合进来" | 分支合并 | 按 `4` 进入分支面板 → 选中分支 → `m` |
| "合并冲突了怎么办" | 冲突解决 | 按 `2` 进入文件面板 → 红色文件 → `Enter` → `e` 编辑 |
| "刚才提交的信息写错了" | 修改提交信息 | 按 `3` 进入提交面板 → 选中提交 → `r`（reword） |

---

## 三、标准流程

### 3.1 前置条件

| 条件项 | 要求 | 验证方式 |
|--------|------|----------|
| Git 已安装 | 版本 ≥ 2.20 | `git --version` |
| lazygit 已安装 | 版本 ≥ 0.40 | `lazygit --version` |
| 终端支持 | UTF-8 编码、256 色 | 直接运行 `lazygit` 观察界面 |
| 仓库初始化 | 已执行 `git init` 或克隆仓库 | `git status` 可正常输出 |

### 3.2 安装验证

```bash
# 运行自检命令，确认安装完整
lazygit --selftest

# 预期输出：所有测试通过（无错误提示）
```

### 3.3 基础操作流程

#### 流程 A：交互式暂存与提交

1. 在仓库目录下启动 `lazygit`。
2. 按 `2` 进入文件面板，查看工作区变更列表。
3. 选中目标文件，按 `Enter` 进入文件详情视图。
4. 使用 `↑`/`↓` 移动光标到目标行，按 `Space` 暂存/取消暂存该行。
5. 按 `c` 打开提交输入框，输入提交信息后按 `Enter` 确认。
6. 按 `q` 退出工具，用 `git log --oneline` 验证提交结果。

#### 流程 B：分支合并

1. 按 `4` 进入分支面板，确认当前分支（高亮标记）。
2. 使用 `↑`/`↓` 选中要合并的分支（如 `feature/login`）。
3. 按 `m` 触发合并操作，lazygit 会执行 `git merge`。
4. 若合并成功，面板自动刷新；若产生冲突，自动跳转冲突处理视图。

#### 流程 C：冲突解决

1. 冲突发生后，按 `2` 进入文件面板。
2. 冲突文件以红色标记显示，按 `Enter` 打开该文件。
3. 按 `e` 调用外部编辑器（默认 `$EDITOR` 环境变量指定）编辑冲突内容。
4. 编辑完成后保存退出，回到 lazygit 界面。
5. 按 `Space` 将该文件标记为已解决。
6. 所有冲突文件处理完毕后，按 `c` 输入合并提交信息，完成合并。

### 3.4 输出规范

| 操作类型 | 成功标志 | 失败标志 |
|----------|----------|----------|
| 暂存 | 文件行前出现绿色 `+` 标记 | 无变化，状态栏提示错误 |
| 提交 | 提交面板出现新提交记录 | 状态栏提示提交失败原因 |
| 合并 | 分支拓扑更新，无冲突标记 | 红色冲突文件列表出现 |
| 冲突解决 | 红色文件变为绿色 | 文件仍为红色，未标记解决 |

---

## 四、置信度门控

### 4.1 信息不足时的处理

当遇到以下情况时，lazygit 会显示占位提示，而非编造结果：

| 场景 | 显示内容 | 处理方式 |
|------|----------|----------|
| 远程仓库信息缺失 | `[需核实:远程仓库地址]` | 检查 `git remote -v` |
| 分支上游未设置 | `[需核实:上游分支]` | 执行 `git branch --set-upstream-to=origin/xxx` |
| 提交者信息缺失 | `[需核实:user.name/user.email]` | 配置 `git config --global user.name` |
| 冲突原因不明 | `[需核实:冲突文件内容]` | 打开文件查看冲突标记 |

### 4.2 禁止行为

- 不猜测远程仓库地址或认证方式。
- 不自动修改 `.git/config` 中的关键配置。
- 不假设用户意图（如自动选择合并策略）。

---

## 五、错误码体系

| 错误码 | 常见场景 | 提示话术 | 修正步骤 |
|--------|----------|----------|----------|
| `E001` | 非 Git 仓库目录启动 | "当前目录不是 Git 仓库" | 执行 `git init` 或切换到仓库目录 |
| `E002` | 暂存时文件已被外部修改 | "文件已变更，请重新加载" | 按 `R` 刷新面板后重试 |
| `E003` | 合并时存在未提交的变更 | "工作区有未提交的更改" | 先提交或 stash（按 `s`） |
| `E004` | 冲突文件未编辑直接标记 | "文件仍包含冲突标记" | 打开文件，删除 `<<<<<<<` 等标记 |
| `E005` | 提交信息为空 | "提交信息不能为空" | 重新输入非空提交信息 |
| `E006` | 远程连接失败 | "无法连接远程仓库" | 检查网络和认证配置 |
| `E007` | 编辑器启动失败 | "无法启动外部编辑器" | 检查 `$EDITOR` 环境变量设置 |

---

## 六、FAQ 反模式

### 6.1 常见坑位

| 坑位 | 错误做法 | 正确做法 |
|------|----------|----------|
| 盲目合并 | 不看分支拓扑直接 `m` 合并 | 先按 `4` 查看分支关系，确认合并方向 |
| 忽略冲突标记 | 手动删除整个文件内容 | 保留 `<<<<<<<` / `=======` / `>>>>>>>` 之间的有效代码 |
| 暂存后不检查 | 全选暂存后直接提交 | 提交前按 `Enter` 查看 diff，确认无多余文件 |
| 混淆面板快捷键 | 在文件面板按 `m` 想合并 | 记住：`m` 在分支面板才是合并，文件面板是打开外部编辑器 |
| 忘记刷新 | 外部修改文件后不刷新 | 按 `R` 或 `F5` 刷新面板状态 |

### 6.2 反模式对照

| 反模式 | 问题描述 | 替代方案 |
|--------|----------|----------|
| "全选暂存" | 容易把调试代码或临时文件提交进去 | 使用交互式暂存逐行确认 |
| "冲突后直接 `git checkout --ours`" | 丢失对方分支的修改 | 手动编辑冲突文件，保留双方有效代码 |
| "提交信息随便写" | 后期难以追溯变更原因 | 使用约定式提交（如 `feat: 添加登录功能`） |
| "频繁 rebase 公共分支" | 导致协作成员历史混乱 | 只对未推送的本地提交使用 rebase |

---

## 七、渐进式披露

### 7.1 速查卡（新手必看）

| 按键 | 功能 | 所在面板 |
|------|------|----------|
| `1` | 状态面板 | 全局 |
| `2` | 文件面板 | 全局 |
| `3` | 提交面板 | 全局 |
| `4` | 分支面板 | 全局 |
| `5` | 远程面板 | 全局 |
| `Space` | 暂存/取消暂存 | 文件面板 |
| `c` | 提交 | 文件面板 |
| `m` | 合并 | 分支面板 |
| `e` | 外部编辑器 | 文件详情 |
| `q` | 退出 | 全局 |
| `?` | 帮助菜单 | 全局 |

### 7.2 新手路径（首次使用）

1. 运行 `lazygit --selftest` 验证安装。
2. 在测试仓库中练习「交互式暂存」操作（流程 A）。
3. 熟悉面板切换快捷键（`1`~`5`）。
4. 尝试一次简单的分支合并（流程 B）。
5. 阅读帮助菜单（按 `?`）了解全部快捷键。

### 7.3 进阶路径（熟练用户）

1. 掌握「冲突解决」完整流程（流程 C），练习处理复杂冲突。
2. 学习使用 `-f` 参数定位特定文件：`lazygit -f path/to/file`。
3. 配置自定义编辑命令：在 `~/.config/lazygit/config.yml` 中设置 `editor` 字段。
4. 理解「远程操作集成」：在远程面板中管理推送/拉取策略。
5. 探索自定义配置：修改主题、快捷键映射、自定义命令。

### 7.4 专家路径（高级用户）

1. 编写自定义脚本调用 lazygit 的批量操作（如通过 `--config` 加载预设配置）。
2. 配置 pre-commit 钩子与 lazygit 联动，在提交前自动执行检查。
3. 使用 `lazygit --config /path/to/config.yml` 加载自定义配置文件。
4. 结合 CI/CD 流程，在自动化流水线中调用 lazygit 进行 Git 操作验证。

---

## 八、自定义配置参考

### 8.1 配置文件位置

| 系统 | 路径 |
|------|------|
| Linux/macOS | `~/.config/lazygit/config.yml` |
| Windows | `%APPDATA%\lazygit\config.yml` |

### 8.2 常用配置项

```yaml
# 设置外部编辑器
editor: "vim"

# 自定义快捷键
keybinding:
  universal:
    quit: "q"
    refresh: "R"

# 主题定制
theme:
  activeBorderColor:
    - green
    - bold
```

### 8.3 环境变量

| 变量 | 作用 | 示例 |
|------|------|------|
| `EDITOR` | 指定外部编辑器 | `export EDITOR=vim` |
| `GIT_EDITOR` | Git 专用编辑器 | `export GIT_EDITOR="code --wait"` |
| `LAZYGIT_CONFIG` | 指定配置文件路径 | `export LAZYGIT_CONFIG=/path/to/config.yml` |

---

## 九、用户协议

<!-- user-agreement-injected -->

**使用本 Skill 即表示您同意以下条款：**

1. **责任承担**：使用者应自行承担使用本 Skill 及 lazygit 工具的全部责任。因操作不当导致的代码丢失、仓库损坏或其他损失，本 Skill 作者及贡献者不承担任何责任。

2. **禁止反向工程**：不得对本 Skill 文档进行反向工程、反编译、破解或试图提取底层算法（如适用）。

3. **合规使用**：使用者应遵守所在组织及开源社区的 Git 使用规范，不得利用本 Skill 从事任何违法违规活动。

4. **无担保声明**：本 Skill 按"现状"提供，不附带任何明示或暗示的担保，包括但不限于适销性、特定用途适用性和非侵权性。

5. **变更与终止**：作者保留随时修改、更新或终止本 Skill 的权利，恕不另行通知。

---

## 十、许可证（License）

<!-- professional-license-embedded -->

### MIT License

Copyright (c) 2024 TerminalFlow Studio

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

*本 Skill 由 AI 辅助生成，仅供参考。使用前请阅读 lazygit 官方文档及本手册全部内容。*
