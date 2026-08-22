---
slug: harnesskit
name: harnesskit
displayName: 技能包管理 工具链配置 环境同步
description: 管理技能包、工具链与MCP配置，支持dry-run预览和原子化写入的CLI工具。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: Kai Zhang
agent_created: true
trigger_words: ["harnesskit", "技能管理", "工具链", "MCP配置", "环境同步", "技能包", "配置同步", "dry-run预览"]
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# harnesskit 技能文档

## 一、能力边界（一页纸速查卡）

### 1.1 工具能做什么

| 能力项 | 说明 | 示例 |
|--------|------|------|
| 技能包管理 | 创建、列出、更新、删除技能包配置 | `harnesskit skill add my-skill --path ./skills` |
| 工具链配置 | 声明工具链依赖与版本约束 | `harnesskit toolchain pin node@20` |
| MCP 配置 | 管理 Model Context Protocol 服务器配置 | `harnesskit mcp add server-name --command npx --args ...` |
| 环境同步 | 将本地配置推送到目标环境或拉取远端配置 | `harnesskit sync push --env production` |
| 预览模式 | 所有写操作支持 `--dry-run` 先行预览 | `harnesskit init --dry-run` |
| 原子化写入 | 配置写入采用临时文件+重命名，避免半写入状态 | 内置机制，无需手动操作 |

### 1.2 工具不能做什么

- 不能自动安装或升级外部软件包（仅生成配置声明）
- 不能验证远端 MCP 服务器是否真实可用（仅校验格式）
- 不能回滚已执行的非 dry-run 操作（请自行备份配置）
- 不能解析技能包内部代码逻辑（仅管理元数据）

### 1.3 适用对象

- 使用 Claude 或其他支持 MCP 的 AI 工具的开发人员
- 需要统一管理多项目工具链配置的团队
- 希望将技能包配置纳入版本控制的个人开发者

---

## 二、触发方式

### 2.1 触发词

| 触发词 | 场景说明 |
|--------|----------|
| `harnesskit` | 直接调用 CLI 工具时 |
| `技能管理` | 需要整理或查看技能包列表时 |
| `工具链` | 需要声明或调整工具版本时 |
| `MCP配置` | 需要添加或修改 MCP 服务器时 |
| `环境同步` | 需要将配置同步到其他环境时 |
| `配置同步` | 同上，偏重团队协作场景 |
| `dry-run预览` | 希望在正式写入前查看变更内容时 |

### 2.2 大白话场景映射

| 你说的话 | harnesskit 实际做的事 |
|----------|----------------------|
| "帮我看看现在有哪些技能包" | 执行 `harnesskit skill list` |
| "加一个 MCP 服务器，用 npx 启动" | 执行 `harnesskit mcp add` 并填写参数 |
| "把配置同步到测试环境" | 执行 `harnesskit sync push --env staging` |
| "先别写入，让我看看会改什么" | 执行 `harnesskit <命令> --dry-run` |

---

## 三、标准流程

### 3.1 前置条件

| 条件 | 要求 | 验证方法 |
|------|------|----------|
| 操作系统 | Linux / macOS / Windows (WSL2) | `uname -a` 或 `ver` |
| Node.js | ≥ 18.0.0 | `node --version` |
| 配置文件目录 | 当前用户目录下 `.harnesskit/` 可写 | `ls -la ~/.harnesskit` |
| 网络（可选） | 如需拉取远端模板 | `curl -I https://registry.npmjs.org` |

### 3.2 执行步骤

#### 第一步：初始化配置

```bash
harnesskit init
```

参数说明：

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--dir` | `~/.harnesskit` | 配置目录位置 |
| `--template` | `basic` | 初始模板（`basic` / `team` / `empty`） |
| `--dry-run` | `false` | 预览将要生成的文件 |

#### 第二步：添加技能包

```bash
harnesskit skill add <name> --path <path> [--version <semver>] [--tags <tag1,tag2>]
```

示例：

```bash
harnesskit skill add code-reviewer --path ./skills/code-reviewer --version 1.2.0 --tags review,code
```

#### 第三步：配置工具链

```bash
harnesskit toolchain pin <tool>@<version>
```

示例：

```bash
harnesskit toolchain pin node@20
harnesskit toolchain pin python@3.11
```

#### 第四步：添加 MCP 服务器

```bash
harnesskit mcp add <server-name> --command <cmd> --args <arg1> <arg2> [--env KEY=VALUE]
```

示例：

```bash
harnesskit mcp add filesystem --command npx --args -y @modelcontextprotocol/server-filesystem --env ROOT=/tmp
```

#### 第五步：预览并写入

```bash
harnesskit sync push --env production --dry-run
# 确认无误后去掉 --dry-run 执行
harnesskit sync push --env production
```

### 3.3 输出规范

所有命令输出遵循以下格式：

```
[时间戳] [级别] [操作] 消息
```

示例：

```
2025-01-15T10:30:00Z [INFO] [skill.add] 技能包 code-reviewer 已添加
2025-01-15T10:30:01Z [WARN] [toolchain.pin] python@3.11 已存在，将覆盖
2025-01-15T10:30:02Z [ERROR] [mcp.add] 参数 --command 不能为空
```

JSON 输出模式（供脚本调用）：

```bash
harnesskit skill list --json
```

```json
{
  "status": "success",
  "data": {
    "skills": [
      {"name": "code-reviewer", "version": "1.2.0", "tags": ["review", "code"]}
    ]
  }
}
```

---

## 四、置信度门控

当遇到以下情况时，harnesskit 不会编造信息，而是输出占位符：

| 场景 | 输出内容 | 处理建议 |
|------|----------|----------|
| 远端模板版本未知 | `[需核实:template_version]` | 手动指定 `--template` 版本 |
| MCP 服务器可用性未知 | `[需核实:mcp_server_status]` | 手动启动验证 |
| 工具链兼容性不确定 | `[需核实:toolchain_compat]` | 查阅官方兼容矩阵 |
| 配置文件路径不确定 | `[需核实:config_path]` | 使用 `harnesskit doctor` 诊断 |

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| `E001` | 配置目录不可写 | `无法写入配置目录，请检查权限` | 1. `chmod 700 ~/.harnesskit` 2. 或更换 `--dir` 参数 |
| `E002` | 技能包名称重复 | `技能包 <name> 已存在` | 1. 使用 `harnesskit skill update` 2. 或先 `harnesskit skill remove` |
| `E003` | MCP 命令参数缺失 | `参数 --command 不能为空` | 1. 检查命令拼写 2. 确认 npx 或可执行文件路径 |
| `E004` | 版本号格式错误 | `版本号 <ver> 不符合 semver 规范` | 1. 使用 `x.y.z` 格式 2. 或省略版本号使用 latest |
| `E005` | dry-run 与写入冲突 | `--dry-run 模式下不会执行写入操作` | 1. 确认预览结果 2. 去掉 `--dry-run` 重新执行 |
| `E006` | 同步目标环境不存在 | `环境 <env> 未在配置中定义` | 1. 检查 `environments` 配置段 2. 使用 `harnesskit env add` 添加 |
| `E007` | JSON 输出解析失败 | `输出不是合法 JSON，请检查管道` | 1. 确认命令支持 `--json` 2. 检查是否有 stderr 混入 |

---

## 六、FAQ 反模式

### 反模式 1：跳过 dry-run 直接写入

**错误做法**：

```bash
harnesskit sync push --env production
```

**正确做法**：

```bash
harnesskit sync push --env production --dry-run
# 确认变更内容后，再执行正式写入
```

### 反模式 2：手动编辑配置文件导致格式错误

**错误做法**：直接修改 `~/.harnesskit/config.yaml` 且不校验语法。

**正确做法**：使用 `harnesskit config validate` 校验，或通过 CLI 命令修改。

### 反模式 3：忽略版本约束

**错误做法**：`harnesskit toolchain pin node`（未指定版本）。

**正确做法**：明确指定版本 `harnesskit toolchain pin node@20`，避免环境漂移。

### 反模式 4：将配置文件放在项目目录而非用户目录

**错误做法**：在项目根目录创建 `.harnesskit/` 并提交到仓库。

**正确做法**：使用 `~/.harnesskit/` 存放个人配置，项目级配置通过 `harnesskit sync` 分发。

### 反模式 5：不清理废弃的 MCP 服务器

**错误做法**：长期保留不再使用的 MCP 配置，导致启动缓慢。

**正确做法**：定期执行 `harnesskit mcp list` 并移除无用项。

---

## 七、渐进式披露

### 7.1 新手路径（5 分钟上手）

1. 阅读「能力边界」了解工具范围
2. 执行 `harnesskit init` 生成配置
3. 使用 `--dry-run` 熟悉操作
4. 参考「速查卡」完成基础操作

### 7.2 进阶路径（日常使用）

1. 掌握「标准流程」中的完整操作步骤
2. 熟悉「错误码体系」快速定位问题
3. 阅读「FAQ 反模式」避免常见错误
4. 将配置文件纳入版本控制，实现团队协作

### 7.3 专家路径（深度定制）

1. 自定义配置文件结构，扩展技能包元数据
2. 编写脚本调用 harnesskit 的 JSON 输出
3. 结合 CI/CD 流程实现自动化配置同步
4. 为团队维护共享的工具链配置模板

---

## 八、用户协议

<!-- user-agreement-injected -->

**使用本 Skill 即表示您同意以下条款：**

1. **责任承担**：使用者自行承担使用本 Skill 的全部责任。因使用本 Skill 导致的任何直接或间接损失，作者不承担任何责任。

2. **禁止反向工程**：不得对本 Skill 进行反向工程、反编译、破解或试图提取源代码（除非适用法律允许）。

3. **合规使用**：使用者应确保使用方式符合当地法律法规及所在平台的服务条款。

4. **无担保**：本 Skill 按"现状"提供，不附带任何明示或暗示的担保。

---

## 九、许可证（License）

<!-- professional-license-embedded -->

**MIT License**

Copyright (c) 2025 原创作者（自持版权）

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
