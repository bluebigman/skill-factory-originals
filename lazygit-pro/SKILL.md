---
slug: lazygit-pro
name: lazygit
displayName: 终端Git可视化 分支合并 冲突处理
description: 终端里的Git图形界面，分支合并、冲突解决、交互式暂存一站式搞定。
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
trigger_words: ["lazygit", "终端git", "git图形界面", "git可视化", "交互式暂存", "git tui", "终端git工具"]
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# lazygit 终端Git可视化操作指南

## 一、能力边界速查卡

### 能做什么

| 能力项 | 说明 | 操作入口 |
|--------|------|----------|
| 分支管理 | 创建、切换、合并、删除分支 | `b` 分支菜单 |
| 交互式暂存 | 逐行/逐块选择暂存内容 | `空格` 暂存，`v` 多选 |
| 冲突解决 | 可视化查看冲突文件差异 | `Enter` 查看详情，`e` 编辑 |
| 提交管理 | 提交、修改、撤销、cherry-pick | `c` 提交，`C` 修改 |
| 远程同步 | 拉取、推送、fetch | `f` 拉取，`p` 推送 |
| 历史查看 | 提交历史、文件变更追溯 | `l` 查看日志 |
| Rebase 操作 | 交互式变基、提交压缩 | `r` 进入 rebase 模式 |
| 自定义命令 | 配置个性化快捷键和命令 | 编辑 `~/.config/lazygit/config.yml` |

### 不能做什么

- 不能替代完整的 Git 命令行操作（如复杂的分支重写、filter-branch 等）
- 不支持图形化的 diff 对比窗口（仅文本差异展示）
- 不提供远程仓库管理功能（如创建远程仓库、管理权限）
- 不包含 Git LFS 的专门管理界面
- 不支持 Windows 原生 GUI 渲染（需依赖终端模拟器）

### 适用对象

- 习惯终端操作但需要可视化反馈的开发者
- 需要频繁进行分支合并和冲突处理的团队协作场景
- 希望提高 Git 操作效率的中级开发者
- 教学场景中展示 Git 工作流的讲师

---

## 二、触发方式与场景映射

| 触发词/场景 | 使用建议 | 预期效果 |
|-------------|----------|----------|
| "查看当前分支状态" | 启动 lazygit 后直接查看主面板 | 分支、暂存区、工作区一目了然 |
| "帮我暂存这几个文件" | 进入文件面板，按 `空格` 逐个暂存 | 文件进入暂存区，状态实时更新 |
| "解决合并冲突" | 查看冲突文件，按 `Enter` 查看差异 | 冲突位置高亮显示，可手动编辑 |
| "提交代码" | 按 `c` 输入提交信息 | 提交完成，历史面板更新 |
| "推送代码到远程" | 按 `p` 执行推送 | 推送成功或显示错误信息 |
| "查看提交历史" | 按 `l` 进入日志面板 | 提交记录按时间倒序排列 |
| "合并 dev 分支到 main" | 切换到 main，按 `b` 选择 merge | 合并完成或提示冲突 |

---

## 三、标准操作流程

### 前置条件

1. 已安装 lazygit，版本 ≥ 0.40（通过 `lazygit --version` 确认）
2. 当前目录为 Git 仓库或子目录
3. 终端支持彩色显示（推荐，非强制）

### 基础操作流程

```bash
# 步骤 1：启动 lazygit
lazygit

# 步骤 2：查看当前状态
# 主面板显示：分支、暂存区、工作区、提交历史

# 步骤 3：暂存更改
# 按 空格 暂存当前文件，按 v 进入多选模式批量操作

# 步骤 4：提交更改
# 按 c 打开提交输入框，输入信息后按 Enter

# 步骤 5：推送远程
# 按 p 执行推送，确认远程分支无误

# 步骤 6：退出
# 按 q 退出 lazygit
```

### 分支合并流程

| 步骤 | 操作 | 说明 |
|------|------|------|
| 1 | `b` 打开分支菜单 | 查看所有本地和远程分支 |
| 2 | 选择目标分支 | 如 `main`，按 `Enter` 切换 |
| 3 | `b` 再次打开菜单 | 选择要合并的分支 |
| 4 | 选择 `merge --no-ff` | 保留合并历史，便于追溯 |
| 5 | 处理冲突（如有） | 按 `Enter` 查看冲突详情 |

### 冲突解决标准流程

1. **识别冲突**：状态面板显示 `UU` 或 `AA` 标记
2. **查看详情**：按 `Enter` 查看冲突文件的差异对比
3. **理解意图**：分析 `HEAD` 和 `MERGE_HEAD` 两侧的修改逻辑
4. **手动编辑**：按 `e` 打开编辑器，手动解决冲突标记
5. **标记已解决**：编辑完成后，按 `空格` 暂存该文件
6. **继续合并**：所有冲突解决后，执行 `git merge --continue`

### 输出规范

- 所有操作完成后，主面板应显示干净的工作区状态
- 提交信息遵循团队规范（如 Conventional Commits）
- 合并操作建议保留 `--no-ff` 标记以维护历史完整性

---

## 四、置信度门控

当遇到以下情况时，使用 `[需核实:字段]` 占位，不编造信息：

| 场景 | 处理方式 |
|------|----------|
| 不确定当前分支名 | 显示 `[需核实:当前分支]` |
| 远程仓库地址未知 | 显示 `[需核实:远程仓库URL]` |
| 冲突文件的具体修改意图 | 显示 `[需核实:冲突双方修改意图]` |
| 自定义快捷键配置 | 显示 `[需核实:用户自定义配置]` |
| 版本兼容性问题 | 显示 `[需核实:lazygit版本]` |

---

## 五、错误码体系

| 错误场景 | 提示话术 | 修正步骤 |
|----------|----------|----------|
| lazygit 未安装 | "未检测到 lazygit，请先安装" | 1. 访问官方仓库安装 2. 运行 `lazygit --version` 验证 |
| 非 Git 仓库 | "当前目录不是 Git 仓库" | 1. 执行 `git init` 或 `git clone` 2. 重新启动 lazygit |
| 版本过低 | "lazygit 版本过低，需要 ≥ 0.40" | 1. 升级 lazygit 2. 重新运行 `--selftest` |
| 推送失败 | "推送失败，请检查远程连接" | 1. 按 `f` 拉取最新 2. 确认无冲突 3. 重试推送 |
| 冲突未解决 | "存在未解决的冲突文件" | 1. 按 `Enter` 查看冲突 2. 手动编辑解决 3. 暂存并继续 |
| 配置错误 | "配置文件解析失败" | 1. 检查 YAML 语法 2. 备份后重置配置 3. 重启 lazygit |

---

## 六、FAQ 反模式对照

### 反模式 1：盲目批量暂存

**错误做法**：不查看文件内容直接按 `空格` 全部暂存

**正确做法**：先按 `Enter` 查看文件差异，确认修改内容后再暂存

### 反模式 2：忽略冲突直接推送

**错误做法**：冲突未解决就执行 `p` 推送

**正确做法**：先解决所有冲突，确认状态面板干净后再推送

### 反模式 3：频繁全局刷新

**错误做法**：每次操作都按 `R` 全局刷新

**正确做法**：使用 `r` 仅刷新当前面板，减少不必要的资源消耗

### 反模式 4：不检查版本兼容性

**错误做法**：使用旧版本 lazygit 执行新功能

**正确做法**：定期检查版本，确认功能兼容性

### 反模式 5：忽略自定义配置

**错误做法**：不配置快捷键，每次手动输入命令

**正确做法**：编辑 `~/.config/lazygit/config.yml` 添加常用命令快捷方式

---

## 七、渐进式学习路径

### 新手速查卡（5 分钟上手）

```bash
# 启动
lazygit

# 核心操作
空格 = 暂存/取消暂存
c = 提交
p = 推送
f = 拉取
q = 退出
? = 查看帮助
```

### 进阶操作（1 周内掌握）

| 操作 | 快捷键 | 说明 |
|------|--------|------|
| 多选批量操作 | `v` + `空格` | 批量暂存/取消 |
| 交互式 rebase | `r` | 进入 rebase 模式 |
| 压缩提交 | `s` | 合并多个提交 |
| 自定义命令 | 配置文件 | 添加个性化快捷方式 |
| 与 IDE 集成 | VS Code 终端 | 配合 `code` 命令快速编辑 |

### 专家技巧（持续进阶）

1. **批量操作优化**：使用 `v` 进入多选模式，配合 `空格` 高效处理大量文件
2. **冲突解决模板**：在 `.gitattributes` 中配置 `merge=union` 自动合并特定文件
3. **分支策略**：使用 `merge --no-ff` 保留合并历史，便于代码审查
4. **自定义命令**：在配置文件中添加常用命令快捷方式，如部署、测试等

---

## 八、配置参考

### 配置文件位置

- Linux/macOS: `~/.config/lazygit/config.yml`
- Windows: `%APPDATA%\lazygit\config.yml`

### 常用配置示例

```yaml
# 自定义快捷键
keybinding:
  commits:
    - key: "C"
      action: "commit"
      description: "快速提交"

# 自定义命令
customCommands:
  - key: "D"
    command: "git diff HEAD~1"
    description: "查看上次提交的差异"
```

---

## 用户协议

<!-- user-agreement-injected -->

**使用须知**

1. **责任承担**：使用者自行承担使用本 Skill 的全部责任。因操作不当导致的代码丢失、仓库损坏或其他损失，本 Skill 作者及贡献者不承担任何责任。
2. **禁止反向工程**：未经许可，不得对本 Skill 文档进行反向工程、反编译、破解或尝试提取底层逻辑。
3. **合规使用**：使用者应遵守所在国家/地区的法律法规，不得将本 Skill 用于任何非法用途。
4. **修改与分发**：允许在保留版权声明的前提下修改和分发本 Skill，但需注明原始来源。

---

## 许可证（License）

<!-- professional-license-embedded -->

**MIT License**

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
