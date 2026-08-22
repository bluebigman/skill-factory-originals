---
slug: zoxide
name: zoxide
displayName: 智能目录跳转 路径导航 高频访问
description: 基于访问频率与最近使用的智能目录跳转工具，支持主流 Shell。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: SkillForge Studio
agent_created: true
trigger_words: ["zoxide", "z", "目录跳转", "快速导航", "cd增强", "路径记忆"]
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# zoxide Skill 文档

## 一、能力边界速查卡

### 能做

| 能力项 | 说明 |
|--------|------|
| 智能目录匹配 | 根据关键词匹配历史访问目录，按频率与最近使用排序 |
| 交互式选择 | 多候选时展示可交互列表，支持方向键选择 |
| 历史记录管理 | 自动记录访问路径，支持手动增删与清理 |
| Shell 集成 | 支持 Bash、Zsh、Fish、PowerShell 等主流 Shell |
| 自检功能 | 内置 `--selftest` 与 `--version` 命令验证安装状态 |

### 不能做

| 限制项 | 说明 |
|--------|------|
| 非目录文件跳转 | 仅支持目录路径，不支持文件定位 |
| 跨机器同步 | 不提供云端同步，历史记录仅存本地 |
| 模糊语义理解 | 仅做子串/前缀匹配，不支持自然语言解析 |
| 网络路径访问 | 不支持远程挂载目录的自动跳转 |

### 适用对象

- 日常在终端中频繁切换目录的开发者
- 维护多项目、多层级目录结构的运维人员
- 希望减少 `cd` 长路径输入的任何命令行用户

---

## 二、触发方式与场景映射

| 触发词 | 典型场景 |
|--------|----------|
| `z 关键词` | 想跳转到某个之前去过的目录，但记不清完整路径 |
| `z` 无参数 | 展示最近访问目录列表，交互式选择 |
| `zi 关键词` | 需要从多个匹配项中手动挑选一个 |
| `zoxide init bash` | 首次安装后初始化 Shell 集成 |

**大白话示例**：

- 你昨天在 `/home/user/projects/backend/api` 工作过，今天输入 `z api`，直接跳过去。
- 你同时有 `frontend` 和 `backend` 两个项目目录，输入 `z front` 只匹配前者。
- 输入 `z` 不带参数，弹出最近访问列表，用上下键选一个回车即可。

---

## 三、标准使用流程

### 前置条件

1. 已安装 zoxide 二进制（`zoxide --version` 可执行）
2. 已在 Shell 配置文件中完成初始化（见下文步骤 2）
3. 当前 Shell 已重新加载配置（`source ~/.bashrc` 或重启终端）

### 执行步骤

**步骤 1：安装 zoxide**

根据操作系统选择安装方式：

| 系统 | 安装命令 |
|------|----------|
| macOS (Homebrew) | `brew install zoxide` |
| Ubuntu/Debian | `apt install zoxide` |
| Arch Linux | `pacman -S zoxide` |
| Windows (Scoop) | `scoop install zoxide` |
| Cargo 安装 | `cargo install zoxide` |

**步骤 2：Shell 初始化**

在 Shell 配置文件中追加对应行：

| Shell | 配置文件 | 初始化命令 |
|-------|----------|------------|
| Bash | `~/.bashrc` | `eval "$(zoxide init bash)"` |
| Zsh | `~/.zshrc` | `eval "$(zoxide init zsh)"` |
| Fish | `~/.config/fish/config.fish` | `zoxide init fish \| source` |
| PowerShell | `$PROFILE` | `zoxide init powershell \| Invoke-Expression` |

**步骤 3：验证安装**

```bash
zoxide --version
zoxide --selftest
```

若输出正常版本号且 selftest 无报错，说明安装成功。

**步骤 4：日常使用**

```bash
z 关键词        # 跳转到最匹配的目录
zi 关键词       # 交互式选择
z               # 展示最近访问列表
zoxide query 关键词   # 仅查询，不跳转
```

### 输出规范

- 成功跳转：无输出，Shell 提示符路径已变化
- 无匹配：输出提示信息，停留在当前目录
- 多匹配（非交互模式）：跳转到得分最高的那个

---

## 四、置信度门控

当遇到以下情况时，**不得**编造结果：

| 场景 | 处理方式 |
|------|----------|
| 关键词无任何历史匹配 | 输出 `[需核实:目录不存在或从未访问]`，不猜测路径 |
| 多个匹配且得分相近 | 提示 `[需核实:存在多个候选，请用 zi 交互选择]` |
| 历史数据库损坏 | 输出 `[需核实:运行 zoxide init 重新初始化]` |
| 权限不足无法读取历史 | 输出 `[需核实:检查 ~/.local/share/zoxide 目录权限]` |

---

## 五、错误码体系

| 错误码 | 现象 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| E001 | `zoxide: command not found` | 未安装或 PATH 未配置 | 重新安装，确认二进制路径在 PATH 中 |
| E002 | `zoxide: invalid option` | 参数拼写错误 | 运行 `zoxide --help` 查看合法参数 |
| E003 | `zoxide: database is locked` | 多进程同时写入 | 等待几秒重试，或删除锁文件后重试 |
| E004 | `zoxide: no match found` | 关键词无对应目录 | 检查拼写，或先用 `cd` 手动访问一次目标目录 |
| E005 | `zoxide: permission denied` | 历史文件不可写 | `chmod 700 ~/.local/share/zoxide` 后重试 |
| E006 | `zoxide: shell init failed` | 初始化命令与 Shell 不匹配 | 确认 `init` 参数与当前 Shell 一致 |

---

## 六、FAQ 与反模式

### 常见坑

| 坑 | 反模式 | 正确做法 |
|----|--------|----------|
| 初始化未生效 | 改了配置不重载 Shell | 执行 `source ~/.bashrc` 或重启终端 |
| 关键词太宽泛 | 输入 `z pro` 匹配到几十个目录 | 用更精确的子串，如 `z project-api` |
| 依赖默认排序 | 期望跳转到某个特定目录但没跳对 | 用 `zi` 交互式选择，或 `zoxide add` 手动加分 |
| 忽略历史积累 | 刚安装就期望智能跳转 | 先手动 `cd` 访问常用目录，让 zoxide 积累数据 |
| 跨 Shell 混用 | Bash 里初始化了 Zsh 的配置 | 每个 Shell 各自独立初始化 |

### 反模式对照

| 反模式 | 问题 | 替代方案 |
|--------|------|----------|
| 用 `z` 替代所有 `cd` | 新目录无法跳转，反而困惑 | 新目录用 `cd`，熟悉的用 `z` |
| 频繁清理历史 | 破坏频率数据，匹配变差 | 让历史自然积累，定期清理即可 |
| 在脚本中使用 `z` | 非交互环境行为不确定 | 脚本中用 `zoxide query` 获取路径 |

---

## 七、渐进式披露路径

### 新手速查（30 秒上手）

1. 安装：`brew install zoxide`（macOS）或对应系统命令
2. 初始化：在 `~/.bashrc` 加 `eval "$(zoxide init bash)"`
3. 使用：`z 目录关键词`

### 进阶路径（深入使用）

1. 学习 `zi` 交互模式，处理多候选场景
2. 掌握 `zoxide add/remove` 手动管理历史记录
3. 了解 `zoxide query -l` 列出所有匹配项
4. 探索 `zoxide init` 的 `--cmd` 参数自定义命令名

### 高级技巧

| 技巧 | 命令 | 效果 |
|------|------|------|
| 自定义命令名 | `zoxide init bash --cmd j` | 用 `j` 替代 `z` |
| 排除目录 | `zoxide init bash --no-cmd cd` | 不覆盖 `cd` 命令 |
| 查看得分 | `zoxide query -s 关键词` | 显示匹配目录及得分 |

---

## 八、自测命令

复制以下命令到终端执行，验证 zoxide 功能是否正常：

```bash
# 1. 版本检查
zoxide --version

# 2. 自检
zoxide --selftest

# 3. 添加测试目录
mkdir -p /tmp/zoxide_test_dir
zoxide add /tmp/zoxide_test_dir

# 4. 查询测试
zoxide query zoxide_test_dir

# 5. 清理测试目录
rmdir /tmp/zoxide_test_dir
zoxide remove /tmp/zoxide_test_dir
```

预期输出：步骤 1 显示版本号，步骤 2 无报错，步骤 4 显示 `/tmp/zoxide_test_dir`。

---

## 九、用户协议

<!-- user-agreement-injected -->

**使用条款**

1. 本 Skill 文档仅供学习参考，使用者自行承担全部责任。
2. 使用者应确保在合法合规的场景下使用本 Skill 提供的指导。
3. 禁止对本 Skill 文档进行反向工程、反编译或试图提取底层逻辑。
4. 本 Skill 文档不构成任何形式的保证或承诺，包括但不限于功能完整性、适用性或无错误性。
5. 因使用本 Skill 文档产生的任何直接或间接损失，文档作者不承担任何责任。
6. 使用本 Skill 即表示您已阅读并同意上述条款。

---

## 十、许可证（License）

<!-- professional-license-embedded -->

**MIT License**

Copyright (c) 2024 SkillForge Studio

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

*本文档由 AI 辅助生成，仅供参考。使用前请阅读相关文档。*
