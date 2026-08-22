---
slug: braid
name: braid
displayName: 供应商分支 同步追踪 变更审计
description: 追踪并同步 Git 仓库中的供应商分支，提供状态查看、注册与变更日志功能。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: FlowForge
agent_created: true
trigger_words: ["braid", "供应商分支", "vendor branch", "分支同步", "变更追踪", "上游同步", "vendor sync"]
---

> 本内容由 AI 生成，仅供学习参考 <!-- ai-generated-notice -->

# braid — 供应商分支同步与变更追踪

## 一、能力边界（速查卡）

### 1.1 能做什么

| 能力项 | 说明 | 对应命令 |
|--------|------|----------|
| 状态查看 | 列出所有已注册的供应商分支及其同步状态 | `braid status` |
| 分支同步 | 将上游仓库的变更合并到本地供应商分支 | `braid sync <branch-name>` |
| 分支注册 | 将新的上游仓库注册为受管供应商分支 | `braid register <branch-name> <upstream-url>` |
| 变更日志 | 查看指定分支的历史同步记录 | `braid log <branch-name>` |
| 环境自检 | 验证 braid 工具链是否正常工作 | `braid --selftest` |
| 版本查询 | 查看当前 braid 版本号 | `braid --version` |

### 1.2 不能做什么

- **不能**自动创建上游仓库——上游必须已存在且可访问。
- **不能**处理未注册的分支——所有操作均基于 `.braid/config.json` 中的注册记录。
- **不能**解决合并冲突——同步过程中若出现冲突，需要人工介入处理。
- **不能**回滚已推送的同步结果——同步操作会直接修改本地分支历史。
- **不能**跨仓库自动传播变更——每个仓库需独立执行同步。

### 1.3 适用对象

- 维护多个第三方依赖分支的 Git 仓库管理者。
- 需要定期将上游开源项目变更合并到自有分支的团队。
- 希望审计供应商分支变更历史的合规性检查人员。

---

## 二、触发方式

### 2.1 触发词

| 触发词 | 使用场景 |
|--------|----------|
| `braid` | 直接调用工具命令 |
| `供应商分支` | 中文场景下描述该工具的功能领域 |
| `vendor branch` | 英文场景下的同义表达 |
| `分支同步` | 描述需要执行同步操作时 |
| `变更追踪` | 描述需要查看变更历史时 |
| `上游同步` | 描述从上游拉取变更的场景 |

### 2.2 场景映射表

| 用户说（大白话） | 实际执行 |
|------------------|----------|
| "帮我看看现在有哪些供应商分支，状态怎么样" | `braid status` |
| "把 xxx 分支和上游同步一下" | `braid sync xxx` |
| "我要把一个新的上游仓库加进来管理" | `braid register xxx <url>` |
| "这个分支最近同步过几次？" | `braid log xxx` |
| "检查一下 braid 能不能正常用" | `braid --selftest` |

---

## 三、标准流程

### 3.1 前置条件

| 条件 | 检查方式 |
|------|----------|
| 已安装 braid 工具 | 终端执行 `braid --version` 能输出版本号 |
| 已进入 Git 仓库根目录 | 终端执行 `pwd` 确认路径，且该目录包含 `.git` 文件夹 |
| 上游仓库可访问 | 执行 `git ls-remote <upstream-url>` 能正常返回引用列表 |
| 网络连接正常 | 能访问上游仓库的远程地址 |

### 3.2 流程 A：查看状态

**步骤：**

1. 打开终端，进入目标 Git 仓库根目录。
2. 执行 `braid status`。
3. 查看输出表格，每一行代表一个已注册的供应商分支。

**输出列说明：**

| 列名 | 含义 | 可能值 |
|------|------|--------|
| Branch | 分支名称 | 任意合法 Git 分支名 |
| Upstream | 上游仓库地址 | URL 或本地路径 |
| Status | 同步状态 | `clean` / `behind` / `diverged` / `unregistered` |
| Last Sync | 最近同步时间 | ISO 8601 格式时间戳 |

**状态含义：**

| 状态 | 含义 | 建议操作 |
|------|------|----------|
| `clean` | 本地分支与上游完全一致 | 无需操作 |
| `behind` | 上游有新提交，本地落后 | 执行 `braid sync` |
| `diverged` | 本地与上游各自有独立提交 | 执行 `braid sync` 并处理可能的冲突 |
| `unregistered` | 分支存在但未在配置中注册 | 执行 `braid register` |

### 3.3 流程 B：同步分支

**步骤：**

1. 执行 `braid status` 确认目标分支当前状态。
2. 若状态为 `behind` 或 `diverged`，执行 `braid sync <branch-name>`。
3. braid 会依次执行以下操作：
   - 从上游仓库拉取最新提交。
   - 将上游提交合并到本地供应商分支。
   - 更新 `.braid/config.json` 中的同步时间戳。
4. 同步完成后，再次执行 `braid status` 确认状态变为 `clean`。

**参数说明：**

| 参数 | 必填 | 说明 |
|------|------|------|
| `<branch-name>` | 是 | 已注册的供应商分支名称 |

**输出规范：**

```
Syncing branch: <branch-name>
  Fetching from upstream: <upstream-url>
  Merging commits: <commit-hash-1>..<commit-hash-n>
  Sync completed successfully.
```

**冲突处理：**

若合并过程中出现冲突，braid 会输出冲突文件列表，并停止操作。此时需要：

1. 手动解决冲突文件。
2. 执行 `git add <resolved-files>`。
3. 执行 `git commit` 完成合并。
4. 重新执行 `braid status` 确认状态。

### 3.4 流程 C：注册新分支

**步骤：**

1. 执行 `braid register <branch-name> <upstream-url>`。
2. braid 会验证：
   - `<branch-name>` 是否已存在于本地仓库。
   - `<upstream-url>` 是否可访问且包含有效的 Git 仓库。
   - 该分支是否已被其他上游注册。
3. 注册成功后，该分支会出现在 `braid status` 列表中。
4. 注册信息存储在 `.braid/config.json` 文件中（位于仓库根目录）。

**参数说明：**

| 参数 | 必填 | 说明 |
|------|------|------|
| `<branch-name>` | 是 | 本地分支名称，必须已存在 |
| `<upstream-url>` | 是 | 上游仓库的 URL 或本地路径 |

**注册失败场景：**

| 失败原因 | 提示信息 | 修正方法 |
|----------|----------|----------|
| 分支不存在 | `Error: branch <name> not found` | 先创建本地分支 |
| 上游不可访问 | `Error: cannot access upstream <url>` | 检查 URL 和网络 |
| 分支已被注册 | `Error: branch <name> already registered` | 先注销或选择其他分支 |

### 3.5 流程 D：查看变更日志

**步骤：**

1. 执行 `braid log <branch-name>`。
2. 输出按时间倒序排列的同步记录，每条记录包含：

| 字段 | 说明 |
|------|------|
| Timestamp | 同步发生的具体时间 |
| Action | 操作类型（`sync` / `register` / `update`） |
| From | 同步前的上游提交哈希 |
| To | 同步后的上游提交哈希 |
| Status | 本次同步的结果（`success` / `conflict` / `failed`） |

**输出示例：**

```
2024-05-20T14:32:10Z  sync   a1b2c3d..e4f5g6h  success
2024-05-18T09:15:44Z  sync   f6e5d4c..a1b2c3d  success
2024-05-15T11:00:00Z  register  -  -  success
```

---

## 四、置信度门控

当遇到以下信息不足的情况时，braid 会输出 `[需核实:字段]` 占位符，**不会**编造数据：

| 场景 | 输出占位符 | 后续处理 |
|------|------------|----------|
| 上游仓库无法访问时 | `[需核实:upstream-url]` | 检查网络或 URL 后重试 |
| 分支状态无法确定时 | `[需核实:branch-status]` | 手动执行 `git log` 对比 |
| 同步时间戳缺失时 | `[需核实:last-sync-time]` | 检查 `.braid/config.json` |
| 提交哈希无法解析时 | `[需核实:commit-hash]` | 检查上游仓库引用 |

**原则：** 宁可输出占位符，绝不猜测或伪造数据。

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| `E001` | 未在 Git 仓库中执行 | `Error E001: not a git repository` | 进入仓库根目录后重试 |
| `E002` | 分支未注册 | `Error E002: branch <name> not registered` | 执行 `braid register` 注册 |
| `E003` | 上游仓库不可访问 | `Error E003: upstream <url> unreachable` | 检查 URL、网络、权限 |
| `E004` | 合并冲突 | `Error E004: merge conflict in <file>` | 手动解决冲突后提交 |
| `E005` | 配置损坏 | `Error E005: invalid config in .braid/config.json` | 检查 JSON 格式，必要时恢复备份 |
| `E006` | 分支名非法 | `Error E006: invalid branch name <name>` | 使用合法 Git 分支名 |
| `E007` | 权限不足 | `Error E007: permission denied` | 检查文件系统写权限 |

---

## 六、FAQ 反模式

| 常见坑 | 反模式（错误做法） | 正确做法 |
|--------|-------------------|----------|
| 直接编辑配置文件 | 手动修改 `.braid/config.json` 导致格式错误 | 使用 `braid register` 命令注册 |
| 忽略冲突信号 | 同步失败后强制推送覆盖 | 先解决冲突，再重新同步 |
| 在非仓库目录执行 | 在任意目录执行 `braid status` 报错 | 先 `cd` 到仓库根目录 |
| 同步后不验证 | 同步完成直接推送，未确认状态 | 执行 `braid status` 确认 `clean` |
| 注册不存在的分支 | 注册时分支名拼写错误 | 先用 `git branch` 确认分支存在 |
| 混淆本地分支与上游分支 | 在本地分支上直接修改后同步 | 明确区分本地开发分支与供应商分支 |

---

## 七、渐进式披露

### 7.1 速查卡（30 秒上手）

```
# 查看状态
braid status

# 同步分支
braid sync <branch-name>

# 注册新分支
braid register <branch-name> <upstream-url>

# 查看日志
braid log <branch-name>

# 环境自检
braid --selftest
```

### 7.2 新手路径（首次使用）

1. 阅读「能力边界」了解 braid 能做什么。
2. 执行 `braid --selftest` 确认环境正常。
3. 对已有分支执行 `braid status` 查看当前状态。
4. 若分支未注册，按「流程 C」注册。
5. 对 `behind` 状态的分支执行 `braid sync`。

### 7.3 进阶路径（日常运维）

1. 阅读「标准流程」了解每个命令的详细执行逻辑。
2. 熟悉「错误码体系」，遇到问题能快速定位。
3. 阅读「FAQ 反模式」避免常见陷阱。
4. 定期执行 `braid log` 审计供应商分支的变更历史。
5. 结合 CI/CD 流水线，在每次构建前自动执行 `braid status` 检查。

### 7.4 专家路径（自动化集成）

1. 直接编辑 `.braid/config.json` 实现批量注册。
2. 编写脚本调用 `braid status --json`（若支持）获取结构化输出。
3. 将 braid 集成到 pre-commit 钩子中，同步前自动检查。

---

## 八、用户协议

1. 本 Skill 提供的所有功能与指导，使用者应自行承担全部使用责任。因使用本 Skill 导致的任何直接或间接损失，作者不承担任何责任。
2. 使用者不得对本 Skill 进行反向工程、反编译、处理或试图提取底层源代码（除非适用法律允许）。
3. 使用者不得将本 Skill 用于任何违反法律法规或侵犯第三方权益的用途。
4. 本 Skill 的配置信息（包括 `.braid/config.json`）属于用户数据，作者不收集、不存储、不分析任何用户数据。

<!-- user-agreement-injected -->

---

## 九、许可证（License）

MIT License

Copyright (c) 2024 原创作者（自持版权）

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
