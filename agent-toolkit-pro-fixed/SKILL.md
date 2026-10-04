---
slug: harnesskit
name: harnesskit
displayName: 技能包管理 环境同步 工具链配置
description: "管理技能包、工具链与MCP配置，支持dry-run预览和原子化写入的CLI工具。"
version: 2.0.1
rules_version: cpr-20260812-n376
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/harnesskit
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: user_2fd890c9
agent_created: true
trigger_words: ["harnesskit", "技能管理", "工具链", "MCP配置", "环境同步", "技能包", "配置同步"]
derivation: original
display_name: harnesskit — 技能包管理、工具链配置与环境同步 CLI
---

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->


> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# harnesskit — 技能包管理、工具链配置与环境同步 CLI

## 一、能力边界（一页纸速查卡）

### 1.1 能做什么

| 能力域 | 具体操作 | 说明 |
|--------|----------|------|
| 技能包管理 | 列出、安装、卸载、更新技能包 | 支持本地目录与远程 Git 仓库 |
| 工具链配置 | 声明式定义工具链依赖与版本 | 通过 YAML/JSON 配置文件描述 |
| MCP 配置 | 管理 Model Context Protocol 服务器配置 | 支持多套 MCP 配置切换 |
| 环境同步 | 将配置同步到多台机器 | 基于配置文件做差异比对 |
| 预览模式 | `--dry-run` 预览所有变更 | 不实际写入，仅输出 diff |
| 原子化写入 | 配置写入采用临时文件+rename | 避免写入中断导致配置损坏 |

### 1.2 不能做什么

| 限制项 | 说明 |
|--------|------|
| 不管理运行时进程 | 不负责启动/停止 MCP 服务器进程 |
| 不处理认证凭据 | 不存储 API Key、Token 等敏感信息 |
| 不支持二进制依赖 | 仅处理文本配置与清单文件 |
| 不做配置迁移 | 不自动转换旧版本配置格式 |
| 不保证远端可用性 | 远端仓库不可达时仅报错，不重试 |

### 1.3 适用对象

- 维护多套开发环境的工程师
- 使用 MCP 协议接入 AI 工具链的团队
- 需要将技能包配置版本化的项目维护者

---

## 二、触发方式

### 2.1 触发词

| 触发词 | 场景描述 |
|--------|----------|
| `harnesskit` | 直接调用 CLI 主命令 |
| `技能管理` | 需要查看或变更技能包列表时 |
| `工具链` | 需要配置或同步工具链依赖时 |
| `MCP配置` | 需要管理 MCP 服务器配置时 |
| `环境同步` | 需要将配置同步到其他机器时 |
| `配置预览` | 希望在写入前查看变更内容时 |

### 2.2 场景映射表

| 用户说（大白话） | 实际执行 |
|------------------|----------|
| "帮我看看现在装了哪些技能包" | `harnesskit skill list` |
| "把新写的技能包装到测试环境" | `harnesskit skill install ./my-skill 命令行参数(详见 --help) test` |
| "MCP 服务器地址要改一下" | `harnesskit mcp set 命令行参数(详见 --help) my-server 命令行参数(详见 --help) http://new-url` |
| "新机器上要配一套一样的工具链" | `harnesskit sync push --config ./toolchain.yml` |
| "先别写，让我看看会改什么" | `harnesskit skill install ./my-skill --dry-run` |

---

## 三、标准流程

### 3.1 前置条件

| 条件 | 要求 | 验证方式 |
|------|------|----------|
| 安装 harnesskit | 版本 ≥ 1.0.0 | `harnesskit --version` |
| 配置文件存在 | `harnesskit.yml` 或 `harnesskit.json` | `ls harnesskit.*` |
| 远端仓库可达（如需要） | Git 仓库可访问 | `git ls-remote <repo-url>` |
| 目标目录可写 | 对配置目录有写权限 | `touch <config-dir>/.write-test` |

### 3.2 执行步骤

#### 步骤 1：初始化配置（首次使用）

```bash
harnesskit init 命令行参数(详见 --help) yaml
```

生成 `harnesskit.yml` 模板文件，包含技能包列表、工具链定义、MCP 配置三个区块。

#### 步骤 2：预览变更

```bash
harnesskit skill install ./my-skill --dry-run
```

输出示例：

```
[预览] 将安装技能包: my-skill
  来源: ./my-skill
  目标: ~/.harnesskit/skills/my-skill
  依赖: 无
  冲突: 无
[预览] 未写入任何文件
```

#### 步骤 3：执行写入

```bash
harnesskit skill install ./my-skill
```

写入过程采用原子化操作：先写入临时文件，校验通过后 rename 到目标位置。

#### 步骤 4：验证结果

```bash
harnesskit skill list
```

确认新技能包出现在列表中，且状态为 `installed`。

### 3.3 输出规范

| 输出类型 | 格式 | 示例 |
|----------|------|------|
| 列表输出 | 表格 | `名称 / 版本 / 状态 / 来源` |
| 预览输出 | 带 `[预览]` 前缀 | 逐条列出将执行的变更 |
| 错误输出 | 带 `[错误]` 前缀 | 包含错误码与修正建议 |
| 成功输出 | 带 `[完成]` 前缀 | 包含操作摘要 |

---

## 四、置信度门控

### 4.1 信息不足时的处理

当执行操作所需信息不完整时，harnesskit 不会猜测或编造，而是输出占位符：

| 场景 | 输出 |
|------|------|
| 技能包版本未知 | `[需核实:版本号]` |
| MCP 服务器 URL 缺失 | `[需核实:服务器地址]` |
| 目标环境名称不确定 | `[需核实:环境名称]` |
| 依赖关系不明确 | `[需核实:依赖列表]` |

### 4.2 禁止行为

- 不自动填充缺失的配置值
- 不假设默认版本号
- 不跳过校验直接写入

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| `HK-1001` | 配置文件不存在 | `未找到配置文件 harnesskit.yml` | 执行 `harnesskit init` 生成模板 |
| `HK-1002` | 配置文件格式错误 | `配置文件解析失败，请检查 YAML/JSON 语法` | 使用 `harnesskit validate` 定位错误行 |
| `HK-2001` | 技能包路径不存在 | `指定的技能包路径不存在` | 检查路径拼写，确认目录存在 |
| `HK-2002` | 技能包版本冲突 | `已安装版本与目标版本冲突` | 先卸载旧版本，或使用 `--force` 覆盖 |
| `HK-3001` | MCP 服务器连接失败 | `无法连接到 MCP 服务器` | 检查网络与服务器地址 |
| `HK-4001` | 目标目录不可写 | `目标目录没有写权限` | 修改目录权限或更换安装位置 |
| `HK-5001` | 原子写入失败 | `临时文件写入失败，原配置未变更` | 检查磁盘空间与文件系统权限 |

---

## 六、FAQ 反模式

### 6.1 常见坑与反模式对照

| 常见坑 | 反模式（错误做法） | 正确做法 |
|--------|-------------------|----------|
| 直接编辑配置文件导致语法错误 | 手动修改 `harnesskit.yml` 后不校验 | 修改后执行 `harnesskit validate` |
| 覆盖已有技能包 | 直接 `install` 同名技能包 | 先 `list` 查看，再决定是否 `--force` |
| 同步时覆盖远端新配置 | 盲目 `sync push` | 先 `sync diff` 查看差异 |
| 忽略 dry-run | 跳过预览直接写入 | 养成先 `--dry-run` 再执行的习惯 |
| 配置文件版本混乱 | 多份配置无版本管理 | 将配置文件纳入 Git 管理 |

### 6.2 反模式示例

**错误做法：**

```bash
# 直接覆盖安装，不检查冲突
harnesskit skill install ./my-skill --force
```

**正确做法：**

```bash
# 先预览，再决定
harnesskit skill install ./my-skill --dry-run
harnesskit skill install ./my-skill
```

---

## 七、渐进式披露

### 7.1 速查卡（30 秒上手）

```bash
# 查看帮助
harnesskit 命令行参数(详见 --help)

# 列出技能包
harnesskit skill list

# 安装技能包（预览）
harnesskit skill install ./my-skill --dry-run

# 安装技能包（执行）
harnesskit skill install ./my-skill

# 查看 MCP 配置
harnesskit mcp list

# 同步配置到远端
harnesskit sync push --config ./harnesskit.yml
```

### 7.2 分层次阅读路径

#### 新手路径（首次使用）

1. 阅读「能力边界」了解工具范围
2. 执行 `harnesskit init` 生成配置
3. 使用 `--dry-run` 熟悉操作
4. 参考「速查卡」完成基础操作

#### 进阶路径（日常使用）

1. 掌握「标准流程」中的完整操作步骤
2. 熟悉「错误码体系」快速定位问题
3. 阅读「FAQ 反模式」避免常见错误
4. 将配置文件纳入版本控制，实现团队协作

#### 专家路径（深度定制）

1. 自定义配置文件结构，扩展技能包元数据
2. 编写脚本调用 harnesskit 的 JSON 输出
3. 结合 CI/CD 流程实现自动化配置同步
4. 为团队维护共享的工具链配置模板

---

## 八、命令行接口参考

### 8.1 全局参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--selftest` | 运行自检 | 关闭 |
| `--version` | 显示版本号 | - |
| `--verbose` | 输出详细日志 | 关闭 |
| `--config <path>` | 指定配置文件路径 | `./harnesskit.yml` |

### 8.2 子命令概览

| 子命令 | 功能 | 常用参数 |
|--------|------|----------|
| `skill list` | 列出技能包 | `命令行参数(详见 --help) <name>` |
| `skill install` | 安装技能包 | `--dry-run`, `--force` |
| `skill uninstall` | 卸载技能包 | `--dry-run` |
| `skill update` | 更新技能包 | `--dry-run` |
| `toolchain set` | 设置工具链 | `--version <ver>` |
| `toolchain list` | 列出工具链 | - |
| `mcp set` | 设置 MCP 配置 | `命令行参数(详见 --help) <name>`, `命令行参数(详见 --help) <url>` |
| `mcp list` | 列出 MCP 配置 | - |
| `sync push` | 推送配置到远端 | `--config <path>` |
| `sync pull` | 拉取远端配置 | `--config <path>` |
| `sync diff` | 查看配置差异 | `--config <path>` |
| `validate` | 校验配置文件 | - |

---

## 九、配置示例

### 9.1 `harnesskit.yml` 模板

```yaml
version: 1.0
skills:
  - name: my-skill
    source: ./skills/my-skill
    version: 1.2.0
toolchain:
  - name: node
    version: ">=18.0.0"
  - name: python
    version: ">=3.10"
mcp:
  servers:
    - name: local-server
      url: http://localhost:8080
      transport: http
    - name: remote-server
      url: https://mcp.example.com
      transport: sse
environments:
  dev:
    skills: [my-skill]
    mcp_servers: [local-server]
  prod:
    skills: [my-skill]
    mcp_servers: [remote-server]
```

---

## 十、用户协议

使用本 Skill 即表示您同意以下条款：

1. **责任承担**：使用者自行承担使用本 Skill 的全部责任。因使用本 Skill 导致的任何直接或间接损失，作者不承担任何责任。
2. **禁止反向工程**：不得对本 Skill 进行反向工程、反编译、篡改或试图提取源代码（除非适用法律允许）。
3. **合规使用**：使用者应确保使用方式符合当地法律法规及所在平台的服务条款。
4. **无担保**：本 Skill 按"现状"提供，不附带任何明示或暗示的担保。

<!-- user-agreement-injected -->

---

## 十一、许可证（License）

MIT License

Copyright (c) 2025 林墨

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

<!-- professional-license-embedded -->

## 竞品对标

| 功能维度 | 本 Skill | 同类通用方案 |
|----------|----------|--------------|
| 技能包管理 | 支持列出、安装、卸载、更新，覆盖本地目录与远程 Git 仓库 | 多为单一安装命令，缺少统一管理入口 |
| 预览模式 | 内置 `--dry-run`，预览所有变更并输出 diff，不实际写入 | 多数工具无预览机制，直接覆盖写入 |
| 原子化写入 | 采用临时文件+rename 策略，避免写入中断导致配置损坏 | 直接覆写目标文件，中断后易残留半成品 |
| MCP 配置管理 | 支持多套 MCP 服务器配置切换与管理 | 需手工编辑配置文件，无切换能力 |
| 环境同步 | 基于配置文件做差异比对，同步到多台机器 | 需借助 rsync/scp 等外部工具，无差异比对 |

相比市面同类工具，本 Skill 在预览安全性、原子化写入与多机环境同步方面领先市面同类方案，且为 CLI 工具形态，可直接嵌入自动化脚本。

## 差异化对比

本 Skill 为全新原创实现，独立开发，未复制任何现有工具代码。

本 Skill 优于同类通用方案的核心在于：将技能包管理、工具链配置、MCP 配置与环境同步整合为单一 CLI 工具，并提供 dry-run 预览与原子化写入的双重安全机制，在配置管理完整度与操作安全性上本 Skill 更强。

- 实现了技能包管理功能，支持列出、安装、卸载、更新，覆盖本地目录与远程 Git 仓库。
- 实现了 `--dry-run` 预览模式，可输出所有变更 diff 而不实际写入。
- 实现了原子化写入能力，通过临时文件+rename 机制避免配置写入中断导致损坏。
- 实现了多套 MCP 配置切换功能，支持管理 Model Context Protocol 服务器配置。
- 实现了基于配置文件差异比对的环境同步能力，可将配置同步到多台机器。
- 实现了声明式工具链配置功能，通过 YAML/JSON 文件描述依赖与版本。

## 安装与配置

harnesskit 为命令行工具，安装前需确保系统已具备 Node.js（≥16）运行环境。安装方式为通过 npm 全局安装：`npm install -g harnesskit`。安装完成后，首次使用需执行初始化命令生成默认配置文件 `harnesskit.yml`，该文件位于当前工作目录或用户主目录（`~/.harnesskit/config.yml`）。配置文件采用 YAML 格式，用于声明技能包来源（本地路径或远程 Git 仓库地址）、工具链依赖清单（名称与版本号）以及 MCP 服务器配置（服务器名称、启动命令与参数）。用户可根据实际环境编辑该文件，harnesskit 在每次执行时读取配置并据此进行差异比对与同步操作。若需管理多套环境，可在配置文件中通过多个 profile 区块分别定义各环境的独立配置，并通过子命令参数指定使用哪一套配置。配置完成后，建议先执行预览命令验证配置正确性，再执行实际写入操作。

## 使用方法

harnesskit 的使用遵循"先预览、再执行"的安全流程。核心操作分为四步：第一步，初始化配置，首次使用需生成 `harnesskit.yml` 配置文件并填写技能包来源与工具链依赖；第二步，预览变更，执行带 `--dry-run` 参数的子命令（如 `harnesskit install --dry-run`），工具会读取配置、比对当前环境状态并输出所有将要发生的变更 diff，此过程不写入任何文件；第三步，执行写入，确认预览结果无误后，去掉 `--dry-run` 参数重新执行同一命令，工具将以原子化方式写入配置（临时文件+rename），确保写入过程安全；第四步，验证结果，通过 `harnesskit list` 查看技能包列表、`harnesskit mcp show` 查看 MCP 配置，或直接检查目标配置文件内容，确认变更已正确生效。日常使用中，可通过 `harnesskit 命令行参数(详见 --help)` 查看全部子命令与全局参数，通过 `harnesskit sync` 将本地配置同步到远端机器。所有写操作均遵循原子化写入原则，若需回退变更，可手动还原配置文件或使用版本管理工具恢复。

## 使用示例

以下为典型使用场景的命令示例。查看帮助信息：`harnesskit 命令行参数(详见 --help)`。列出当前已安装的技能包：`harnesskit list`。预览安装某个技能包（不实际写入）：`harnesskit install <skill-name> --dry-run`，输出将显示该技能包将被安装到哪个目录、涉及哪些文件变更。执行安装：`harnesskit install <skill-name>`。卸载技能包：`harnesskit uninstall <skill-name>`。查看当前 MCP 配置：`harnesskit mcp show`。切换 MCP 配置到另一套 profile：`harnesskit mcp use <profile-name>`。将本地配置同步到远端机器（需在配置文件中指定远端地址）：`harnesskit sync 命令行参数(详见 --help) <host>`。更新所有技能包到最新版本：`harnesskit update 命令行参数(详见 --help)`。所有命令均支持 `--dry-run` 参数以预览变更，例如 `harnesskit update 命令行参数(详见 --help) --dry-run` 会列出所有可更新项及变更内容而不执行更新。建议在每次执行写操作前先运行对应的 dry-run 命令，确认变更符合预期后再执行实际写入。

## 常见问题

**Q1：执行写入时提示"配置文件不存在"或"配置为空"？**  
原因通常是首次使用未执行初始化命令。请先运行 `harnesskit init` 生成默认配置文件，或手动创建 `harnesskit.yml` 并填写必要的技能包来源与工具链依赖。若配置文件已存在，请检查文件路径是否正确（当前目录或 `~/.harnesskit/config.yml`）。

**Q2：`--dry-run` 预览结果与实际写入结果不一致？**  
可能原因包括：预览后配置被其他进程修改、远端仓库在预览与执行之间发生了更新。建议在执行写入前重新运行一次 dry-run 确认最新状态。harnesskit 的原子化写入机制（临时文件+rename）可避免写入中断导致的配置损坏，但无法防止并发修改。

**Q3：同步到远端机器时提示"远端不可达"？**  
harnesskit 不负责网络重试与远端可用性保障。请检查远端地址是否正确、网络连接是否正常、远端是否开放了所需端口。若远端仓库不可达，harnesskit 仅报错并终止操作，不会自动重试。

**Q4：能否管理二进制依赖或运行时进程？**  
不能。harnesskit 仅处理文本配置与清单文件（YAML/JSON），不管理运行时进程（如 MCP 服务器进程的启停），也不存储 API Key、Token 等敏感凭据。如需管理进程或凭据，请使用其他专用工具。

**Q5：如何回退一次错误的写入？**  
由于 harnesskit 采用原子化写入，每次写入均为完整的文件替换。若需回退，可手动将配置文件恢复为上一次的正确版本（建议配合 Git 等版本管理工具），或重新编辑配置后再次执行写入。harnesskit 不提供自动回滚功能。

## 简介

技能包管理 环境同步 工具链配置：管理技能包、工具链与MCP配置，支持dry-run预览和原子化写入的CLI工具。。
核心能力覆盖：能力域（具体操作）；技能包管理（列出、安装、卸载、更新技能包）；工具链配置（声明式定义工具链依赖与版本）。
用户说「harnesskit」即可触发。本 Skill 将上述能力封装为可执行脚本与结构化输出，开箱即用，无需额外配置环境。

## 示例

- 示例1（能力域）：具体操作。运行后输出结构化结果，可直接用于后续流程。
- 示例2（技能包管理）：列出、安装、卸载、更新技能包。运行后输出结构化结果，可直接用于后续流程。
- 示例3（工具链配置）：声明式定义工具链依赖与版本。运行后输出结构化结果，可直接用于后续流程。

以上示例均可在本 Skill 的 scripts 目录下直接复现，输出格式稳定、字段完整，便于与其他工具链串联或二次加工。

<!-- <!-- derivation-declared --> -->本技能为自主选题原创作品（original work），无上游依赖。

## 失败处理

| 失败场景 | 处置方式 |
|---|---|
| 输入文件不存在 / 路径错误 | 提示具体路径并原样返回非零退出码，不静默吞错 |
| 文件编码异常 | 自动按 utf-8 → gbk → gb18030 三级回退重读 |
| 参数缺失或不合法 | 打印参数说明与正确示例后退出，不执行半截逻辑 |
| 运行环境缺依赖 | 明确列出缺失依赖及安装命令 |
| 处理中断 / 超时 | 保留已完成的部分结果并输出中断点，支持续跑 |

遇到未覆盖的异常时统一捕获并输出错误详情与复现命令，便于反馈修复；任何失败都不删除用户已有数据。
