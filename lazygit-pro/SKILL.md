---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: lazygit-pro
name: lazygit
displayName: 终端Git可视化 分支合并 冲突处理
description: 终端里的Git图形界面，分支合并、冲突解决、交互式暂存一站式搞定。
version: 1.1.9
rules_version: cpr-20260821-n626
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/lazygit-pro
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: terminal-craft-studio
agent_created: true
trigger_words: ["lazygit", "终端git", "git图形界面", "git可视化", "交互式暂存", "git面板", "终端git工具"]
---

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->


> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# lazygit 终端 Git 可视化操作指南

## 一、能力边界速查卡

### 1.1 能做什么

| 功能域 | 具体操作 | 对应按键/命令 |
|--------|----------|---------------|
| 仓库概览 | 查看当前分支、工作区状态、最近提交 | 启动后默认面板 |
| 分支管理 | 切换分支、创建新分支、删除已合并分支 | `b` 打开分支面板 |
| 提交管理 | 查看提交历史、查看提交详情、cherry-pick | `c` 打开提交面板 |
| 交互式暂存 | 逐行/逐块暂存、取消暂存、丢弃更改 | `v` 打开暂存面板 |
| 合并与变基 | 执行 merge、rebase、abort/continue | `m` 打开合并菜单 |
| 冲突解决 | 可视化查看冲突文件、选择保留版本 | 冲突时自动进入合并面板 |
| 远程同步 | push、pull、fetch、查看远程分支 | `p` 打开远程面板 |
| 标签管理 | 查看、创建、删除标签 | `t` 打开标签面板 |

### 1.2 不能做什么

- 不能替代代码编辑器：lazygit 不提供文件内容编辑功能，冲突解决需借助外部编辑器
- 不支持复杂的交互式 rebase 编辑（如 squash 多个提交并改写信息），需回到命令行
- 不支持子模块的深度管理操作
- 不支持 Git LFS 的专属操作界面
- 不能自动解决语义冲突（如两个分支对同一函数的不同实现）

### 1.3 适用对象

| 用户类型 | 适用程度 | 说明 |
|----------|----------|------|
| Git 初学者 | ★★★★☆ | 可视化降低理解门槛，但需先掌握基本概念 |
| 日常开发者 | ★★★★★ | 提升日常提交、分支操作效率 |
| 资深工程师 | ★★★☆☆ | 复杂操作仍需命令行，但日常操作够用 |
| CI/CD 维护者 | ★★☆☆☆ | 主要用于查看状态，自动化操作仍需脚本 |

---

## 二、触发方式与场景映射

### 2.1 触发词

当用户输入以下任一关键词时，本 Skill 被激活：

- `lazygit` / `终端git` / `git图形界面` / `git可视化`
- `交互式暂存` / `git面板` / `终端git工具`
- 场景化触发：`我要看下仓库状态` / `帮我解决合并冲突` / `怎么暂存部分文件`

### 2.2 场景映射表

| 用户说（大白话） | 实际需求 | 本 Skill 提供的操作路径 |
|------------------|----------|------------------------|
| "我想看看改了什么" | 查看工作区变更 | 启动 lazygit → 默认面板 → 查看 Changes 区域 |
| "只提交一部分改动" | 交互式暂存 | `v` 进入暂存面板 → 逐行选择 → 提交 |
| "两个分支合并不了" | 解决合并冲突 | `m` 合并 → 冲突文件高亮 → 选择保留版本 |
| "刚才的提交有问题" | 修改最近提交 | `c` 提交面板 → 选中提交 → `r` 改写信息 |
| "把某个提交挪过来" | cherry-pick | `c` 提交面板 → 选中提交 → `C` cherry-pick |
| "推送被拒绝了" | 处理远程分歧 | `p` 远程面板 → 查看状态 → 选择 pull --rebase |

---

## 三、标准操作流程

### 3.1 前置条件检查

| 检查项 | 命令 | 通过标准 | 失败处理 |
|--------|------|----------|----------|
| lazygit 已安装 | `lazygit --version` | 版本号 ≥ 0.40 | 安装：`brew install lazygit`（macOS）/ 官网下载二进制 |
| 当前目录是 Git 仓库 | `git status` | 无报错输出 | `git init` 初始化或切换到正确目录 |
| 终端宽度 | 终端设置 | ≥ 100 字符 | 调整终端窗口大小或减少字体大小 |
| 终端颜色支持 | 终端设置 | 支持 256 色 | 设置终端为 xterm-256color |

### 3.2 执行步骤

#### 步骤 1：启动 lazygit

```bash
cd /path/to/your/repo
lazygit
```

启动后界面分为四个主要区域：

| 区域 | 位置 | 显示内容 |
|------|------|----------|
| 状态栏 | 顶部 | 当前分支、仓库路径、快捷键提示 |
| 主面板 | 中央 | 根据当前模式显示文件/提交/分支列表 |
| 预览面板 | 右侧 | 选中项的详细信息（diff、提交内容） |
| 底部栏 | 底部 | 当前模式的操作快捷键 |

#### 步骤 2：日常提交流程

1. 启动后默认在 Files 面板，查看工作区变更
2. 按 `v` 进入暂存面板，逐行选择要暂存的内容
   - `space`：暂存/取消暂存当前行
   - `a`：暂存当前文件所有变更
   - `A`：暂存所有文件
3. 按 `c` 打开提交信息输入框
4. 输入提交信息（遵循 Conventional Commits 规范）
5. 回车确认提交

#### 步骤 3：分支合并流程

1. 按 `b` 打开分支面板
2. 选中目标分支（要合并进来的分支）
3. 按 `m` 选择 merge 或 rebase
4. 若出现冲突：
   - 冲突文件在 Files 面板中标记为红色
   - 选中冲突文件，按 `enter` 查看冲突详情
   - 按 `e` 打开外部编辑器手动解决
   - 解决后回到 lazygit，文件变为绿色
   - 按 `space` 暂存已解决的文件
   - 按 `c` 完成合并提交

#### 步骤 4：推送与同步

1. 按 `p` 打开远程面板
2. 查看远程分支状态（领先/落后）
3. 按 `P` 推送当前分支
4. 若推送被拒绝，按 `f` 执行 fetch，再选择 pull --rebase

### 3.3 输出规范

| 操作类型 | 预期输出 | 验证方式 |
|----------|----------|----------|
| 提交成功 | 提交信息出现在提交面板 | `git log --oneline -1` |
| 合并完成 | 合并提交出现在提交面板 | `git status` 显示 clean |
| 冲突解决 | 冲突文件变为已暂存状态 | `git diff --cached --check` |
| 推送成功 | 远程分支更新 | `git log origin/branch..HEAD` 为空 |

---

## 四、置信度门控

### 4.1 信息不足时的处理

当遇到以下情况，输出 `[需核实:字段]` 占位，不进行猜测：

| 场景 | 占位示例 | 核实方式 |
|------|----------|----------|
| 不确定 lazygit 版本 | `[需核实:lazygit版本号]` | 运行 `lazygit --version` |
| 不确定仓库远程地址 | `[需核实:远程仓库URL]` | 运行 `git remote -v` |
| 不确定当前分支状态 | `[需核实:分支领先/落后数量]` | 运行 `git status -sb` |
| 不确定冲突文件数量 | `[需核实:冲突文件列表]` | 运行 `git diff --name-only --diff-filter=U` |

### 4.2 禁止编造的内容

- 不编造快捷键（所有快捷键以 lazygit 官方文档为准）
- 不编造版本特性（如某功能在 0.40 版本不可用，需明确说明）
- 不编造仓库历史（所有提交、分支信息必须来自实际查询）

---

## 五、错误码体系

| 错误码 | 错误现象 | 可能原因 | 提示话术 | 修正步骤 |
|--------|----------|----------|----------|----------|
| LG-E001 | 启动时提示 "command not found" | lazygit 未安装 | "lazygit 未安装，请先安装" | 1. `brew install lazygit` 2. 重新运行 `lazygit --version` |
| LG-E002 | 启动时提示 "not a git repository" | 当前目录不是 Git 仓库 | "当前目录不是 Git 仓库" | 1. `git init` 2. 或 `cd` 到正确目录 |
| LG-E003 | 面板显示错位/重叠 | 终端宽度不足 | "终端宽度不足，建议 ≥ 100 字符" | 1. 调整终端窗口 2. 或 `tmux resize-window -x 120` |
| LG-E004 | 推送失败 "rejected" | 远程有本地没有的提交 | "远程有更新，需要先 pull" | 1. `p` 打开远程面板 2. 选择 pull --rebase 3. 解决冲突后重新推送 |
| LG-E005 | 合并冲突无法自动解决 | 双方修改同一区域 | "存在冲突，需要手动解决" | 1. 选中冲突文件 2. 按 `e` 打开编辑器 3. 保留正确内容 4. 暂存并提交 |
| LG-E006 | 无法切换分支 "would be overwritten" | 工作区有未提交的修改 | "工作区有未提交修改，先处理" | 1. 暂存或提交当前修改 2. 或使用 `git stash` 3. 再切换分支 |

---

## 六、FAQ 与反模式

### 6.1 常见坑

| 坑编号 | 坑描述 | 反模式（错误做法） | 正确做法 |
|--------|--------|-------------------|----------|
| PIT-01 | 误操作丢弃未提交的更改 | 在 Files 面板按 `d` 直接丢弃 | 丢弃前先确认：1. 是否已备份 2. 是否真的不需要 3. 考虑先暂存到 stash |
| PIT-02 | 合并时选错分支方向 | 在分支面板直接按 `m` 不确认方向 | 合并前确认：1. 当前分支是接收方 2. 目标分支是来源方 3. 查看分支面板顶部的当前分支标识 |
| PIT-03 | 交互式暂存时误提交部分内容 | 按 `a` 全选后直接提交 | 提交前检查：1. 暂存区内容是否符合预期 2. 使用 `git diff --cached` 预览 3. 确认无敏感信息 |
| PIT-04 | rebase 过程中途放弃 | 直接关闭终端 | 正确退出：1. 按 `q` 退出 lazygit 2. 运行 `git rebase --abort` 3. 或 `git rebase --continue` 完成 |
| PIT-05 | 推送时覆盖远程历史 | 使用 `git push --force` | 优先使用 `--force-with-lease`，或先与团队确认 |

### 6.2 反模式对照表

| 反模式 | 表现 | 后果 | 替代方案 |
|--------|------|------|----------|
| 盲目使用 force push | 覆盖队友提交 | 代码丢失、团队协作混乱 | 使用 `--force-with-lease`，或先 pull --rebase |
| 长时间不 fetch | 本地远程状态过期 | 合并时出现意外冲突 | 每次操作前按 `f` fetch |
| 忽略冲突文件标记 | 提交了带冲突标记的文件 | 代码无法编译 | 提交前搜索 `<<<<<<<` 标记 |
| 在 master 上直接开发 | 主分支混乱 | 无法回滚、发布困难 | 创建 feature 分支开发 |
| 频繁使用 `git reset --hard` | 丢失提交历史 | 无法恢复已提交的代码 | 使用 `git revert` 或 `git reset --soft` |

---

## 七、渐进式披露

### 7.1 速查卡（一页纸）

```text
lazygit 核心操作速查
====================
启动:  cd <repo> && lazygit

常用按键:
  ?    查看所有快捷键
  q    退出
  v    交互式暂存面板
  c    提交面板
  b    分支面板
  m    合并菜单
  p    远程面板
  t    标签面板

暂存操作:
  space  暂存/取消暂存当前行
  a      暂存当前文件
  A      暂存所有文件

提交操作:
  c      打开提交信息输入
  r      改写最近提交信息

分支操作:
  n      新建分支
  d      删除分支（需确认）
  m      合并/变基

冲突解决:
  e      打开外部编辑器
  space  暂存已解决文件
```

### 7.2 新手路径

**目标**：完成日常提交和推送

1. 阅读速查卡，熟悉基本按键
2. 在测试仓库中练习：创建文件 → 修改 → 暂存 → 提交 → 推送
3. 重点掌握：`v` 暂存面板、`c` 提交、`p` 推送
4. 遇到问题先按 `?` 查看帮助

**练习任务**：
- 创建一个新文件，提交并推送
- 修改已有文件，只暂存部分行
- 查看提交历史，找到某次提交的改动

### 7.3 进阶路径

**目标**：熟练处理分支合并和冲突解决

1. 掌握分支面板的完整操作（创建、切换、删除、合并）
2. 练习冲突解决流程：制造冲突 → 解决 → 完成合并
3. 学习 rebase 工作流：`m` 选择 rebase → 处理冲突 → continue
4. 掌握 cherry-pick：`c` 提交面板 → 选中 → `C`

**练习任务**：
- 创建两个分支，修改同一文件，制造冲突并解决
- 将一个分支的某个提交 cherry-pick 到当前分支
- 使用 rebase 将多个提交合并为一个

### 7.4 专家路径

**目标**：高效处理复杂仓库操作

1. 自定义 lazygit 配置（`~/.config/lazygit/config.yml`）
2. 配置自定义命令（如快速部署、测试运行）
3. 结合外部工具（如 `git worktree`、`git submodule`）
4. 编写脚本自动化常见操作

**练习任务**：
- 配置自定义快捷键执行 `git stash` 操作
- 设置合并时自动打开特定编辑器
- 创建自定义命令批量处理多个仓库

---

## 八、配置参考

### 8.1 常用配置项

配置文件位置：`~/.config/lazygit/config.yml`

```yaml
# 基础配置
gui:
  theme:
    activeBorderColor:
      - green
      - bold
    inactiveBorderColor:
      - white
  showFileIcons: true
  showIcons: true

# 自定义快捷键
keybinding:
  commits:
    - key: "C"
      action: "cherry-pick"
  files:
    - key: "s"
      action: "stash"

# 外部编辑器
os:
  edit: "code --wait"
  editAtLine: "code --wait --goto {{filename}}:{{line}}"
```

### 8.2 版本兼容性

| lazygit 版本 | 新增功能 | 注意事项 |
|--------------|----------|----------|
| 0.40+ | 支持交互式 rebase 可视化 | 需确认终端支持 |
| 0.42+ | 增强冲突解决界面 | 推荐升级 |
| 0.44+ | 支持自定义命令 | 配置语法有变化 |

---

## 九、用户协议

<!-- user-agreement-injected -->

**使用责任**：使用者自行承担使用本 Skill 的全部责任。因操作不当导致的代码丢失、仓库损坏、数据损失等后果，本 Skill 作者不承担任何责任。

**禁止反向工程**：不得对本 Skill 文档进行反向工程、反编译、破解或试图提取底层逻辑。

**合规使用**：使用者应遵守所在国家/地区的法律法规，不得将本 Skill 用于非法用途。

**无担保声明**：本 Skill 按"现状"提供，不附带任何明示或暗示的担保，包括但不限于适销性、特定用途适用性和非侵权保证。

**修改与分发**：允许在保留本协议的前提下修改和分发本 Skill，但需注明原始出处。

---

## 十、许可证（License）

<!-- professional-license-embedded -->

MIT License

Copyright (c) 2024 terminal-craft-studio

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "
