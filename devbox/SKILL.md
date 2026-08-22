---
slug: devbox
name: devbox
displayName: 开发环境 工具链 一键复现
description: 基于Nix的团队开发环境管理器，一键复现统一工具链。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 林墨
agent_created: true
trigger_words: ["devbox", "开发环境", "环境管理", "Nix环境", "依赖管理", "工具链复现", "团队环境统一"]
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# devbox Skill 文档

## 1. 能力边界（一页纸速查卡）

### 1.1 能做什么

| 能力项 | 说明 | 典型场景 |
|--------|------|----------|
| 环境初始化 | 在项目根目录生成 `devbox.json` 和 `devbox.lock` | 新项目接入统一工具链 |
| 工具安装 | 通过 Nix 包仓库安装指定版本的工具 | 安装 Python 3.11、Node.js 18 等 |
| 环境进入 | 启动一个包含全部依赖的子 shell | 开发时使用与团队一致的工具版本 |
| 脚本编排 | 定义 `init_hook` 和自定义命令 | 进入环境时自动加载环境变量、启动服务 |
| 版本锁定 | 通过 lock 文件锁定 Nixpkgs 版本和包哈希 | 确保团队所有成员使用完全相同的依赖 |
| 全局工具 | 在系统层面管理常用工具 | 安装 ripgrep、jq 等通用 CLI 工具 |
| CI 集成 | 在流水线中执行 `devbox run` | 构建、测试、静态检查等阶段使用统一环境 |

### 1.2 不能做什么

| 限制项 | 说明 |
|--------|------|
| 不替代 Docker | devbox 管理的是命令行工具链，不提供进程隔离或操作系统级虚拟化 |
| 不管理运行时服务 | 不负责启动数据库、消息队列等常驻服务（可通过脚本配合，但非核心能力） |
| 不解决网络问题 | 首次构建需要从 Nix 缓存或源码编译，网络受限时可能失败 |
| 不保证跨平台一致 | 在 Linux 和 macOS 上表现良好，Windows 需通过 WSL 使用 |

### 1.3 适用对象

- 使用 Git 进行协作的软件团队
- 需要统一 CLI 工具链版本的项目（如 Python、Node.js、Go 多语言混编）
- 希望减少"在我机器上能跑"问题的技术负责人
- 对 Nix 生态感兴趣但不想直接编写 Nix 表达式的开发者

---

## 2. 触发方式

### 2.1 触发词

当对话中出现以下关键词时，本 Skill 将被激活：

- `devbox`
- `开发环境`
- `环境管理`
- `Nix环境`
- `依赖管理`
- `工具链复现`
- `团队环境统一`

### 2.2 场景映射表

| 用户说（大白话） | 实际需求 | 对应操作 |
|------------------|----------|----------|
| "我想让团队都用同一个版本的 Python" | 统一工具链版本 | 初始化 devbox → 添加 python → 提交 lock 文件 |
| "新电脑上配环境太麻烦了" | 快速复现开发环境 | 克隆仓库 → `devbox shell` 即可进入 |
| "CI 里怎么保证构建环境和本地一致？" | CI 环境一致性 | 在流水线中使用 `devbox run build` |
| "我想装个 jq 但不想污染系统" | 全局工具管理 | `devbox global add jq` |
| "进入项目时自动设置一些环境变量" | 自定义初始化逻辑 | 配置 `init_hook` 字段 |

---

## 3. 标准流程

### 3.1 前置条件

| 条件 | 要求 | 验证方式 |
|------|------|----------|
| 操作系统 | Linux 或 macOS（Windows 需 WSL2） | `uname -a` |
| 安装 devbox | 版本 ≥ 0.8.0 | `devbox version` |
| 网络 | 可访问 Nix 缓存或包源 | `curl -I https://nixos.org` |
| Git | 已安装并初始化仓库 | `git status` |

### 3.2 执行步骤

#### 阶段一：基础使用（步骤 1-7）

**步骤 1：安装 devbox**

```bash
# macOS 或 Linux（使用官方安装脚本）
curl -fsSL https://get.jetify.com/devbox | bash

# 验证安装
devbox version
```

**步骤 2：初始化项目环境**

```bash
cd /path/to/your/project
devbox init
```

执行后生成两个文件：

- `devbox.json`：项目配置清单
- `devbox.lock`：锁定精确版本（应提交到 Git）

**步骤 3：添加常用工具**

```bash
# 添加 Python 3.11
devbox add python@3.11

# 添加 Node.js 18
devbox add nodejs@18

# 添加多个包（空格分隔）
devbox add ripgrep jq
```

**步骤 4：进入开发环境**

```bash
devbox shell
```

进入后，`python --version` 应显示 3.11.x，`node --version` 应显示 18.x。

**步骤 5：配置 init_hook 和自定义脚本**

编辑 `devbox.json`，添加如下内容：

```json
{
  "packages": ["python@3.11", "nodejs@18"],
  "env": {
    "MY_PROJECT_ROOT": "{{ .DevboxDir }}"
  },
  "init_hook": [
    "echo 'Welcome to devbox environment'",
    "export PATH=\"$PWD/.bin:$PATH\""
  ],
  "scripts": {
    "test": "pytest tests/",
    "build": "npm run build"
  }
}
```

**步骤 6：提交到版本控制**

```bash
git add devbox.json devbox.lock
git commit -m "Add devbox environment configuration"
```

**步骤 7：验证环境复现**

在另一台机器上：

```bash
git clone <your-repo-url>
cd <your-repo>
devbox shell
```

无需手动安装任何工具，直接进入统一环境。

#### 阶段二：进阶配置（步骤 8-11）

**步骤 8：配置环境变量**

在 `devbox.json` 中通过 `env` 字段设置：

```json
{
  "env": {
    "DATABASE_URL": "postgres://localhost:5432/mydb",
    "LOG_LEVEL": "debug",
    "PATH": "{{ .DevboxDir }}/bin:{{ .Env.PATH }}"
  }
}
```

支持 Go template 语法，可引用 `.DevboxDir`、`.Env` 等变量。

**步骤 9：指定 Nixpkgs 版本**

```json
{
  "nixpkgs": {
    "commit": "eabc38219184cc3e04a974fe31857d8e0e8e8c6c"
  }
}
```

或使用 GitHub 引用：

```json
{
  "nixpkgs": {
    "github": "NixOS/nixpkgs/eabc38219184cc3e04a974fe31857d8e0e8e8c6c"
  }
}
```

**步骤 10：CI 集成**

以 GitHub Actions 为例：

```yaml
name: CI
on: [push]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: jetify-com/devbox-install-action@v0.11.0
      - run: devbox run test
```

**步骤 11：全局工具管理**

```bash
# 添加全局工具
devbox global add ripgrep jq

# 查看已安装的全局工具
devbox global list

# 移除全局工具
devbox global remove ripgrep
```

### 3.3 输出规范

| 操作 | 预期输出 |
|------|----------|
| `devbox init` | 输出 "Creating devbox.json" 并生成文件 |
| `devbox add <pkg>` | 输出 "Adding package <pkg>" 并更新 lock 文件 |
| `devbox shell` | 进入子 shell，提示符前出现 `(devbox)` 前缀 |
| `devbox run <script>` | 执行对应脚本，输出脚本运行结果 |
| `devbox version` | 输出版本号，如 `0.11.0` |

---

## 4. 置信度门控

当遇到以下情况时，**不得编造**信息，应输出 `[需核实:字段]` 占位符：

| 场景 | 处理方式 |
|------|----------|
| 不确定某个包在 Nixpkgs 中的确切名称 | 输出 `[需核实:包名]`，建议用户运行 `devbox search <关键词>` |
| 不确定某个包的可用版本列表 | 输出 `[需核实:版本列表]`，建议用户运行 `devbox search <包名>` |
| 不确定 Nixpkgs commit 对应的具体版本 | 输出 `[需核实:Nixpkgs commit]`，建议用户查阅 Nixpkgs 仓库 |
| 不确定 CI 平台的具体配置语法 | 输出 `[需核实:CI平台语法]`，建议用户查阅对应平台文档 |

**示例对话：**

> 用户：我想装一个 Redis 的客户端，叫什么来着？
>
> 助手：Redis 客户端在 Nixpkgs 中有多个实现，常见的有 `redis`（服务端）、`redis-tools`（CLI 工具）。具体包名请运行 `devbox search redis` 确认。当前不确定您需要的具体包名，标记为 `[需核实:包名]`。

---

## 5. 错误码体系

| 错误码 | 错误现象 | 提示话术 | 修正步骤 |
|--------|----------|----------|----------|
| `E001` | `devbox: command not found` | devbox 未安装或不在 PATH 中 | 1. 重新执行安装脚本 2. 检查 `~/.local/bin` 是否在 PATH 中 |
| `E002` | `Package <name> not found` | 包名不存在或拼写错误 | 1. 运行 `devbox search <关键词>` 查找正确包名 2. 检查版本号格式 |
| `E003` | `Failed to resolve nixpkgs` | Nixpkgs 引用无效或网络不可达 | 1. 检查 `nixpkgs` 字段配置 2. 确认网络可访问 GitHub 或 Nix 缓存 |
| `E004` | `Lock file is out of date` | `devbox.json` 与 `devbox.lock` 不一致 | 运行 `devbox update` 重新生成 lock 文件 |
| `E005` | `Permission denied` | 文件权限不足 | 检查项目目录写权限，或使用 `sudo`（不推荐） |
| `E006` | `Script <name> not found` | 引用了未定义的脚本 | 检查 `devbox.json` 中 `scripts` 字段的拼写 |
| `E007` | `init_hook failed` | 初始化钩子执行出错 | 1. 检查 `init_hook` 中的命令语法 2. 逐条执行排查错误命令 |

---

## 6. FAQ 反模式

### 6.1 常见坑

| 坑 | 反模式（错误做法） | 正模式（推荐做法） |
|----|-------------------|-------------------|
| **忽略 lock 文件** | 只提交 `devbox.json`，不提交 `devbox.lock` | 两个文件都提交，确保版本锁定 |
| **手动安装工具** | 在 `devbox shell` 里用 `apt install` 或 `brew install` | 所有工具都通过 `devbox add` 管理 |
| **修改全局环境** | 在 `~/.bashrc` 中硬编码工具路径 | 使用 `devbox global` 管理全局工具 |
| **不指定版本** | `devbox add python`（默认最新版） | `devbox add python@3.11`（锁定大版本） |
| **CI 中不用 devbox** | CI 里手动安装依赖，与本地不一致 | CI 中使用 `devbox run` 执行所有命令 |

### 6.2 反模式对照表

| 反模式 | 问题 | 正确做法 |
|--------|------|----------|
| 在 `init_hook` 中写 `cd /absolute/path` | 路径硬编码，团队其他人无法使用 | 使用相对路径或 `{{ .DevboxDir }}` 变量 |
| 在 `devbox.json` 中写死环境变量值 | 不同环境（开发/生产）需要不同值 | 使用 `.env` 文件或 CI 变量注入 |
| 频繁运行 `devbox update` | 导致 lock 文件频繁变动，团队冲突 | 仅在需要升级依赖时运行，并提交变更说明 |
| 在 Windows 上直接使用 | devbox 原生不支持 Windows | 使用 WSL2 或 Docker 容器 |

---

## 7. 渐进式披露

### 7.1 速查卡（30 秒上手）

```bash
# 安装
curl -fsSL https://get.jetify.com/devbox | bash

# 初始化
cd my-project && devbox init

# 添加工具
devbox add python@3.11 nodejs@18

# 进入环境
devbox shell

# 运行脚本
devbox run test
```

### 7.2 分层次阅读路径

#### 新手路径（首次使用）

1. 阅读 **3.2 节阶段一**（步骤 1-7）
2. 完成基础安装和初始化
3. 添加 2-3 个常用工具体验环境切换
4. 将配置提交到 Git 仓库
5. 在另一台机器上验证复现

#### 进阶路径（团队负责人）

1. 深入理解 **3.2 节阶段二**（步骤 8-11）
2. 配置 `init_hook` 和自定义脚本
3. 学习 `env` 和 `nixpkgs` 高级字段
4. 在 CI 中集成 `devbox run` 并配置缓存
5. 探索 `devbox global` 管理全局工具
6. 阅读 [Nixpkgs 手册](https://nixos.org/manual/nixpkgs/stable/) 了解包属性定制

#### 专家路径（平台维护者）

1. 研究 Nix 表达式语言，理解包定义
2. 自定义包属性，覆盖默认配置
3. 构建私有 Nixpkgs 镜像
4. 为团队设计标准化的 devbox 模板

---

## 8. 合规使用声明

**合规使用**：使用者应遵守所在地法律法规及所在组织的安全政策，不得将本 Skill 用于任何非法或未经授权的用途。

**内容变更**：本 Skill 可能随平台规则或技术演进进行更新，使用者应定期查阅最新版本。

**第三方工具**：本 Skill 引用的第三方工具（如 devbox、Nix）的使用，应遵守其各自的许可协议和使用条款。

---

## 用户协议

<!-- user-agreement-injected -->

**生效日期**：2025 年 1 月 1 日

**1. 接受条款**

使用本 Skill 即表示您同意本协议的全部条款。若不同意，请停止使用本 Skill。

**2. 责任承担**

使用者自行承担因使用本 Skill 产生的全部责任。包括但不限于：因操作不当导致的环境损坏、数据丢失、构建失败等后果。本 Skill 提供的是通用指导，不针对任何特定项目或场景做出保证。

**3. 禁止反向工程**

使用者不得对本 Skill 的底层实现进行反向工程、反编译、反汇编，或试图提取源代码（除非适用法律允许）。

**4. 免责声明**

本 Skill 按"原样"提供，不附带任何明示或暗示的保证，包括但不限于适销性、特定用途适用性和非侵权保证。

**5. 协议变更**

本协议可能随时更新，更新后的版本将在本 Skill 文档中发布。继续使用即视为接受变更后的条款。

---

## 许可证（License）

<!-- professional-license-embedded -->

### MIT License

版权所有 (c) 2025 林墨

特此免费授予任何获得本软件及相关文档文件（以下简称"软件"）副本的人士，在不受限制的情况下处理本软件，包括但不限于使用、复制、修改、合并、发布、分发、再许可和/或销售软件副本的权利，并允许向其提供软件的人士在符合以下条件的情况下这样做：

上述版权声明和本许可声明应包含在软件的所有副本或重要部分中。

本软件按"原样"提供，不附带任何明示或暗示的保证，包括但不限于适销性、特定用途适用性和非侵权保证。在任何情况下，作者或版权持有人均不对因使用本软件而产生的任何索赔、损害或其他责任负责，无论是在合同诉讼、侵权或其他诉讼中。

---

*本 Skill 由 AI 辅助生成，仅供参考。使用前请阅读相关文档。*
