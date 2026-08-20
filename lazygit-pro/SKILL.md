---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: lazygit-pro
name: lazygit
displayName: 终端Git可视化 分支合并 冲突处理
description: 终端里的Git图形界面，分支合并、冲突解决、交互式暂存一站式搞定。
version: 1.1.8
rules_version: cpr-20260820-n601
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/lazygit-pro
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: FlowForge Studio
agent_created: true
trigger_words: ["lazygit", "终端git", "git图形界面", "git可视化", "交互式暂存", "git tui", "终端git工具"]
---

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->


> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# lazygit 终端Git可视化操作指南

## 一、能力边界：一页纸速查卡

### 能做什么

| 能力项 | 具体说明 | 操作入口 |
|--------|----------|----------|
| 仓库状态总览 | 查看工作区、暂存区、提交历史的整体状态 | 启动后默认面板 |
| 交互式暂存 | 逐行/逐块选择要暂存的更改 | `空格` 暂存，`Tab` 切换暂存区/工作区 |
| 分支管理 | 创建、切换、合并、删除分支 | `b` 打开分支菜单 |
| 提交管理 | 创建提交、修改提交信息、压缩提交 | `c` 提交，`r` 进入rebase模式 |
| 冲突解决 | 可视化查看冲突文件，辅助手动解决 | `Enter` 查看差异，`e` 打开编辑器 |
| 远程同步 | 拉取、推送、查看远程分支状态 | `f` 拉取，`p` 推送 |
| 批量操作 | 多选文件/提交进行批量处理 | `v` 进入多选模式 |
| 自定义扩展 | 通过配置文件添加自定义命令和快捷键 | 编辑 `~/.config/lazygit/config.yml` |

### 不能做什么

| 限制项 | 说明 |
|--------|------|
| 不能自动解决冲突 | lazygit 只提供可视化辅助，最终合并决策仍需人工判断 |
| 不能替代代码审查 | 不提供 PR/MR 审查流程，仅覆盖本地 Git 操作 |
| 不支持非 Git 版本控制 | 仅适用于 Git 仓库，不兼容 SVN、Mercurial 等 |
| 不能离线使用远程功能 | 拉取/推送需要网络连接 |
| 不提供图形化 Diff 工具 | 差异对比基于文本，复杂二进制文件无法有效展示 |

### 适用对象

- 已安装 lazygit 0.40+ 版本的用户
- 当前工作目录位于 Git 仓库内（或子目录）
- 终端支持彩色显示（推荐，非强制）
- 熟悉 Git 基本概念（提交、分支、暂存区）

---

## 二、触发方式：场景映射表

| 触发词/场景 | 实际含义 | 推荐操作 |
|-------------|----------|----------|
| "lazygit" | 直接启动工具 | 在仓库目录运行 `lazygit` |
| "终端git" | 想在终端里操作 Git | 启动 lazygit 替代命令行 |
| "git图形界面" | 需要可视化操作 | 启动 lazygit 查看图形面板 |
| "git可视化" | 查看提交历史/分支图 | 启动后按 `1` 查看提交面板 |
| "交互式暂存" | 只想暂存部分更改 | 启动后按 `空格` 逐块暂存 |
| "git tui" | 终端用户界面操作 | 同 lazygit 启动方式 |
| "怎么解决冲突" | 需要处理合并冲突 | 启动后按 `m` 合并，`Enter` 查看冲突 |

---

## 三、标准流程：从启动到推送

### 前置条件

1. 确认 lazygit 已安装：运行 `lazygit --version`，版本号需 ≥ 0.40
2. 确认当前目录是 Git 仓库：运行 `git status` 无报错
3. 终端宽度建议 ≥ 100 字符，否则面板可能错位

### 执行步骤

#### 场景 A：日常提交推送流程

| 步骤 | 操作 | 预期结果 |
|------|------|----------|
| 1 | 在仓库根目录运行 `lazygit` | 进入主界面，左侧为文件面板 |
| 2 | 按 `空格` 暂存需要提交的文件 | 文件从"未暂存"移到"已暂存"区域 |
| 3 | 按 `c` 打开提交输入框 | 底部出现信息输入栏 |
| 4 | 输入提交信息，按 `Enter` 确认 | 提交创建成功，文件面板清空 |
| 5 | 按 `p` 执行推送 | 远程分支更新，状态栏显示成功 |
| 6 | 按 `q` 退出 lazygit | 返回终端命令行 |

#### 场景 B：分支合并操作

| 步骤 | 操作 | 预期结果 |
|------|------|----------|
| 1 | 按 `b` 打开分支菜单 | 显示本地和远程分支列表 |
| 2 | 选择目标分支（要合并进来的分支） | 高亮显示选中分支 |
| 3 | 按 `m` 选择合并方式 | 弹出合并选项（merge/rebase） |
| 4 | 选择 `merge --no-ff`（推荐） | 保留合并历史，生成合并提交 |
| 5 | 如有冲突，按 `Enter` 查看冲突文件 | 显示冲突标记和双方版本 |
| 6 | 按 `e` 打开编辑器手动解决 | 编辑完成后保存退出 |
| 7 | 回到 lazygit，按 `空格` 暂存已解决文件 | 冲突标记消除 |
| 8 | 按 `c` 完成合并提交 | 合并完成 |

#### 场景 C：交互式 Rebase 压缩提交

| 步骤 | 操作 | 预期结果 |
|------|------|----------|
| 1 | 按 `r` 进入 rebase 模式 | 显示提交列表，可选中操作 |
| 2 | 选择要压缩的提交 | 高亮显示 |
| 3 | 按 `s` 标记为 squash | 该提交标记为压缩 |
| 4 | 按 `Enter` 确认执行 | 提交被合并到前一个提交 |
| 5 | 编辑合并后的提交信息 | 按 `Enter` 确认 |

### 输出规范

- 所有操作完成后，lazygit 会刷新面板显示最新状态
- 提交信息格式建议：`<type>(<scope>): <description>`，如 `feat(login): add validation`
- 推送成功后状态栏显示 `Pushed to origin/<branch>`

---

## 四、置信度门控

当遇到以下情况时，输出 `[需核实:字段]` 占位符，不编造信息：

| 场景 | 处理方式 |
|------|----------|
| 不确定 lazygit 版本是否支持某功能 | 输出 `[需核实:lazygit版本]`，建议运行 `lazygit --version` 确认 |
| 不确定远程仓库地址 | 输出 `[需核实:远程仓库URL]`，建议运行 `git remote -v` 查看 |
| 不确定某个快捷键在当前版本是否有效 | 输出 `[需核实:快捷键绑定]`，建议按 `?` 查看帮助 |
| 不确定配置文件路径 | 输出 `[需核实:配置文件路径]`，建议运行 `lazygit --config` 查看 |
| 不确定某个 Git 命令的副作用 | 输出 `[需核实:命令影响范围]`，建议先查看 `git help <command>` |

---

## 五、错误码体系

| 错误码 | 常见错误 | 提示话术 | 修正步骤 |
|--------|----------|----------|----------|
| E001 | lazygit 未安装 | `command not found: lazygit` | 1. 运行 `brew install lazygit`（macOS）或 `sudo apt install lazygit`（Ubuntu）<br>2. 重新运行 `lazygit --version` 确认安装成功 |
| E002 | 版本过低 | `lazygit version 0.3x is below minimum 0.40` | 1. 升级 lazygit 到 0.40+<br>2. 重新运行 `lazygit --selftest` 确认通过 |
| E003 | 不在 Git 仓库 | `fatal: not a git repository` | 1. 运行 `git init` 初始化仓库<br>2. 或 `cd` 到已有仓库目录 |
| E004 | 推送被拒绝 | `failed to push some refs` | 1. 按 `f` 拉取最新<br>2. 解决可能的冲突<br>3. 重新推送 |
| E005 | 合并冲突未解决 | `CONFLICT (content): Merge conflict in file.txt` | 1. 按 `Enter` 查看冲突详情<br>2. 按 `e` 手动编辑解决<br>3. 暂存已解决文件后继续 |
| E006 | 权限不足 | `Permission denied (publickey)` | 1. 检查 SSH 密钥配置<br>2. 运行 `ssh -T git@github.com` 测试连接<br>3. 重新推送 |
| E007 | 配置文件语法错误 | `yaml: line N: mapping values are not allowed` | 1. 检查 `~/.config/lazygit/config.yml` 第 N 行<br>2. 修正 YAML 缩进<br>3. 重新启动 lazygit |

---

## 六、FAQ 反模式对照

| 常见坑 | 反模式（错误做法） | 正确做法 |
|--------|-------------------|----------|
| 误暂存文件 | 直接按 `d` 丢弃所有更改 | 先按 `v` 进入多选模式，用 `空格` 精确选择要保留的更改，确认后再按 `d` |
| 合并冲突反复出现 | 每次冲突都手动重新编辑 | 在 `.gitattributes` 中为特定文件配置 `merge=union`，实现自动合并 |
| 提交历史混乱 | 频繁使用 `--force` 推送 | 使用 `merge --no-ff` 保留合并历史，避免强制推送 |
| 快捷键记不住 | 每次操作都查文档 | 按 `?` 在 lazygit 内查看快捷键帮助，或自定义配置 |
| 面板刷新不及时 | 频繁按 `R` 全局刷新 | 按 `r` 仅刷新当前面板，减少不必要的全局刷新 |
| 远程分支不同步 | 直接推送导致冲突 | 先按 `f` 拉取最新，确认无冲突后再推送 |

---

## 七、渐进式披露：分层次阅读路径

### 速查卡（新手必看）

```
启动：lazygit
暂存：空格
提交：c → 输入信息 → Enter
推送：p
退出：q
查看帮助：?
```

### 进阶路径（有经验用户）

#### 1. 批量操作技巧

| 操作 | 快捷键 | 说明 |
|------|--------|------|
| 进入多选模式 | `v` | 可同时选择多个文件/提交 |
| 批量暂存 | `空格` | 在多选模式下逐个暂存 |
| 批量丢弃 | `d` | 确认后丢弃所有选中更改 |

#### 2. 自定义快捷键

编辑 `~/.config/lazygit/config.yml`：

```yaml
keybinding:
  commits:
    - key: "C"
      description: "复制提交哈希"
      command: "git rev-parse HEAD | pbcopy"
```

#### 3. 分支策略建议

- 使用 `b` 菜单的 `merge --no-ff` 保留合并历史
- 定期清理已合并分支：在分支菜单按 `d` 删除
- 使用 `--track` 跟踪远程分支，便于同步

#### 4. 与 IDE 集成

在 VS Code 终端中使用 lazygit，配合 `code` 命令快速编辑：

```
# 在 lazygit 中按 e 打开编辑器时，会调用 $EDITOR 环境变量
export EDITOR="code --wait"
```

#### 5. 版本兼容性说明

本 Skill 基于 lazygit 0.40+ 版本编写，旧版本可能存在功能差异。使用前请确认版本兼容性：

```bash
lazygit --version
# 输出示例：lazygit version 0.44.1
```

---

## 八、高级配置参考

### 常用配置项

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `git.autoFetch` | `true` | 自动拉取远程更新 |
| `git.paging.colorArg` | `always` | 分页器颜色参数 |
| `gui.theme` | 默认主题 | 可自定义颜色方案 |
| `keybinding` | 默认快捷键 | 可覆盖默认绑定 |

### 配置文件位置

| 平台 | 路径 |
|------|------|
| Linux | `~/.config/lazygit/config.yml` |
| macOS | `~/.config/lazygit/config.yml` |
| Windows | `%APPDATA%\lazygit\config.yml` |

---

## 用户协议

<!-- user-agreement-injected -->

使用本 Skill 即表示您同意以下条款：

1. **责任承担**：使用者自行承担使用本 Skill 的全部责任。因操作不当导致的代码丢失、仓库损坏、数据损失等后果，本 Skill 作者不承担任何责任。
2. **禁止反向工程**：不得对本 Skill 文档进行反向工程、反编译、破解或试图提取底层逻辑。
3. **合规使用**：使用者应遵守所在国家/地区的法律法规，不得将本 Skill 用于非法用途。
4. **无担保声明**：本 Skill 按"现状"提供，不附带任何明示或暗示的担保，包括但不限于适销性、特定用途适用性和非侵权保证。
5. **修改与分发**：允许在保留本协议的前提下修改和分发本 Skill，但需注明原始出处。

---

## 许可证（License）

<!-- professional-license-embedded -->

MIT License

Copyright (c) 2025 FlowForge Studio

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
