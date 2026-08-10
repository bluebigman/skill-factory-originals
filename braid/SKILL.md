---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: braid
name: braid
displayName: 供应商分支 同步追踪 变更审计
description: 追踪 Git 仓库中供应商分支的变更与同步状态，提供状态查看、同步、注册与变更日志功能。
version: 1.2.1
rules_version: cpr-20260810-n301
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/braid
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 林栖
agent_created: true
trigger_words: ["braid", "供应商分支", "vendor branch", "分支同步", "变更追踪", "同步状态", "分支注册"]
---

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->


> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# braid — 供应商分支同步追踪 Skill 文档

## 一、能力边界（一页纸速查卡）

### 1.1 能做什么

| 能力项 | 说明 | 对应 CLI 参数 |
|--------|------|----------------|
| 状态查看 | 查看当前仓库中所有已注册供应商分支的同步状态（领先/落后/分叉/干净） | `braid status` |
| 同步执行 | 将上游供应商的变更拉取并合并到本地供应商分支 | `braid sync <branch-name>` |
| 分支注册 | 将一个新的供应商分支纳入 braid 的追踪管理范围 | `braid register <branch-name> <upstream-url>` |
| 变更日志 | 查看某个供应商分支的历史同步记录与变更摘要 | `braid log <branch-name>` |
| 自检 | 验证 braid 自身安装与配置是否正常 | `braid --selftest` |
| 版本查询 | 输出当前 braid 版本号 | `braid --version` |

### 1.2 不能做什么

| 限制项 | 说明 |
|--------|------|
| 不做代码审查 | braid 只追踪分支的同步状态，不分析代码质量或冲突内容 |
| 不自动解决冲突 | 同步过程中若出现合并冲突，braid 会停止并提示人工介入 |
| 不管理非 Git 依赖 | 仅适用于 Git 仓库内的分支，不处理 npm/pip 等包管理器的依赖同步 |
| 不做远程推送 | braid 只拉取和合并，不会自动 push 到远程仓库 |
| 不处理未注册分支 | 只有通过 `register` 注册的分支才会被追踪 |

### 1.3 适用对象

- 维护多个上游供应商代码库的团队
- 需要定期将第三方代码合并进自己项目的开发者
- 希望自动化追踪供应商分支变更状态的 DevOps 工程师

---

## 二、触发方式

### 2.1 触发词

- 核心触发词：`braid`、`供应商分支`、`vendor branch`
- 补充触发词：`分支同步`、`变更追踪`、`同步状态`、`分支注册`

### 2.2 场景映射表

| 用户场景（大白话） | 触发动作 | 实际执行 |
|-------------------|----------|----------|
| "帮我看看现在哪些供应商分支需要更新" | 状态查看 | `braid status` |
| "把 xxx 分支和上游同步一下" | 同步执行 | `braid sync xxx` |
| "这个新分支以后也要跟踪，帮我登记一下" | 分支注册 | `braid register xxx <url>` |
| "这个分支最近都同步了些什么？" | 变更日志 | `braid log xxx` |
| "braid 是不是装坏了？" | 自检 | `braid --selftest` |
| "你用的是哪个版本？" | 版本查询 | `braid --version` |

---

## 三、标准流程

### 3.1 前置条件

| 条件 | 要求 | 验证方式 |
|------|------|----------|
| Git 仓库 | 当前目录必须是 Git 仓库 | `git rev-parse --is-inside-work-tree` 返回 `true` |
| braid 已安装 | braid 命令可用 | `braid --version` 能正常输出 |
| 分支已注册 | 目标分支必须已通过 `register` 注册 | `braid status` 中能看到该分支 |
| 网络可达 | 上游 URL 可访问（若执行同步） | `git ls-remote <upstream-url>` 能返回引用列表 |

### 3.2 执行步骤

#### 流程 A：状态查看

1. 打开终端，进入目标 Git 仓库根目录。
2. 执行 `braid status`。
3. 查看输出表格，每一行代表一个已注册的供应商分支。
4. 输出列说明：

| 列名 | 含义 | 可能值 |
|------|------|--------|
| Branch | 分支名称 | 任意合法 Git 分支名 |
| Upstream | 上游地址 | URL 或本地路径 |
| Status | 同步状态 | `clean` / `ahead` / `behind` / `diverged` / `unregistered` |
| Last Sync | 最近一次同步时间 | ISO 8601 格式时间戳 |
| Pending Commits | 待同步提交数 | 非负整数 |

#### 流程 B：同步执行

1. 执行 `braid status` 确认目标分支当前状态。
2. 若状态为 `behind` 或 `diverged`，执行 `braid sync <branch-name>`。
3. braid 会依次执行以下操作：
   - 拉取上游最新提交（`git fetch <upstream-url> <upstream-branch>`）
   - 尝试将上游变更合并到本地供应商分支（`git merge`）
   - 若合并成功，更新 Last Sync 时间戳
   - 若合并冲突，停止并输出冲突文件列表
4. 同步完成后，再次执行 `braid status` 确认状态变为 `clean`。

#### 流程 C：分支注册

1. 执行 `braid register <branch-name> <upstream-url>`。
2. braid 会验证：
   - 本地分支是否存在（若不存在则报错）
   - 上游 URL 是否可访问（`git ls-remote` 测试）
3. 注册成功后，该分支会出现在 `braid status` 列表中。
4. 注册信息存储在 `.braid/config.json` 文件中（位于仓库根目录）。

#### 流程 D：变更日志

1. 执行 `braid log <branch-name>`。
2. 输出按时间倒序排列的同步记录，每条记录包含：
   - 同步时间
   - 同步前状态 → 同步后状态
   - 合并的提交数
   - 冲突文件列表（若有）

### 3.3 输出规范

- 所有命令输出使用 UTF-8 编码。
- 状态表格使用等宽字体对齐，列宽自适应。
- 错误信息统一以 `[braid-error]` 前缀开头。
- 警告信息统一以 `[braid-warn]` 前缀开头。
- 成功信息统一以 `[braid-ok]` 前缀开头。

---

## 四、置信度门控

当遇到以下情况时，braid 不会猜测或编造信息，而是输出占位符 `[需核实:字段]`：

| 场景 | 输出示例 |
|------|----------|
| 上游 URL 无法访问，无法确认最新提交数 | `Pending Commits: [需核实:上游不可达]` |
| 分支未注册，无法获取历史同步记录 | `Last Sync: [需核实:该分支未注册]` |
| 配置文件损坏，无法读取注册信息 | `Upstream: [需核实:配置损坏]` |
| 本地分支不存在，无法判断状态 | `Status: [需核实:分支不存在]` |

**原则**：宁可输出占位符，绝不虚构数据。用户看到 `[需核实:...]` 时应主动检查对应字段。

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| `E001` | 当前目录不是 Git 仓库 | `[braid-error] E001: 当前目录不是 Git 仓库` | 切换到 Git 仓库根目录后重试 |
| `E002` | 分支未注册 | `[braid-error] E002: 分支 'xxx' 未注册，请先执行 register` | 执行 `braid register xxx <upstream-url>` |
| `E003` | 上游 URL 不可达 | `[braid-error] E003: 无法访问上游地址，请检查网络或 URL 拼写` | 确认 URL 正确且网络通畅 |
| `E004` | 合并冲突 | `[braid-error] E004: 合并冲突，请手动解决以下文件：...` | 手动解决冲突后执行 `git add` 和 `git commit` |
| `E005` | 本地分支不存在 | `[braid-error] E005: 本地分支 'xxx' 不存在` | 先创建分支或检查分支名拼写 |
| `E006` | 配置文件损坏 | `[braid-error] E006: .braid/config.json 解析失败` | 检查配置文件 JSON 格式，必要时删除后重新注册 |
| `E007` | 权限不足 | `[braid-error] E007: 没有写入 .braid 目录的权限` | 检查目录权限，或使用 sudo（谨慎） |

---

## 六、FAQ 反模式

### 6.1 常见坑

| 坑 | 反模式描述 | 正确做法 |
|----|-----------|----------|
| 坑 1：未注册就同步 | 直接对未注册分支执行 `sync`，报 E002 错误 | 先 `register` 再 `sync` |
| 坑 2：忽略冲突信号 | 同步时看到冲突提示，强行 `git merge --abort` 后重试 | 手动解决冲突，不要反复 abort |
| 坑 3：混淆本地分支与供应商分支 | 在供应商分支上直接开发新功能，导致下次同步时大量冲突 | 供应商分支只做同步，开发在独立功能分支进行 |
| 坑 4：删除 .braid 目录 | 误删配置文件后所有分支状态丢失 | 定期备份 `.braid/config.json` |
| 坑 5：同步后不验证 | 同步完成后不执行 `status` 确认状态 | 同步后必须执行 `status` 确认 `clean` |

### 6.2 反模式对照表

| 反模式 | 问题 | 替代方案 |
|--------|------|----------|
| 手动 `git fetch` + `git merge` 代替 braid | 无法记录同步历史，状态不可追踪 | 使用 `braid sync` 自动记录 |
| 在供应商分支上直接改代码 | 下次同步必然冲突 | 新建功能分支，合并时再处理 |
| 多个仓库手动维护同一供应商分支 | 状态不一致，容易遗漏 | 每个仓库独立注册，用 `braid status` 统一查看 |
| 同步失败后反复重试 | 可能掩盖真实问题（如网络、权限） | 先查看错误码，按修正步骤处理 |

---

## 七、渐进式披露

### 7.1 速查卡（新手必读）

```
braid status          # 查看所有供应商分支状态
braid sync <branch>   # 同步指定分支
braid register <branch> <url>  # 注册新分支
braid log <branch>    # 查看同步历史
braid --selftest      # 自检
braid --version       # 版本号
```

### 7.2 分层次阅读路径

#### 新手路径（5 分钟上手）

1. 阅读「能力边界」了解 braid 能做什么。
2. 执行 `braid --selftest` 确认环境正常。
3. 对已有分支执行 `braid status` 查看当前状态。
4. 若分支未注册，按「流程 C」注册。
5. 对 `behind` 状态的分支执行 `braid sync`。

#### 进阶路径（深入使用）

1. 阅读「标准流程」了解每个命令的详细执行逻辑。
2. 熟悉「错误码体系」，遇到问题能快速定位。
3. 阅读「FAQ 反模式」避免常见陷阱。
4. 定期执行 `braid log` 审计供应商分支的变更历史。
5. 结合 CI/CD 流水线，在每次构建前自动执行 `braid status` 检查。

#### 专家路径（定制化）

1. 直接编辑 `.braid/config.json` 实现批量注册。
2. 编写脚本调用 `braid status --json`（若支持）获取结构化输出。
3. 将 braid 集成到 pre-commit 钩子中，同步前自动检查。

---

## 八、用户协议

**使用须知**：

1. 本 Skill 提供的所有功能与指导，使用者应自行承担全部使用责任。因使用本 Skill 导致的任何直接或间接损失，作者不承担任何责任。
2. 使用者不得对本 Skill 进行反向工程、反编译、破解或试图提取底层源代码（除非适用法律允许）。
3. 使用者不得将本 Skill 用于任何违反法律法规或侵犯第三方权益的用途。
4. 本 Skill 的配置信息（包括 `.braid/config.json`）属于用户数据，作者不收集、不存储、不分析任何用户数据。

<!-- user-agreement-injected -->

---

## 九、许可证（License）

本 Skill 基于 MIT 许可证发布。完整许可证文本如下：

```
MIT License

Copyright (c) 2026 林栖

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
```

<!-- professional-license-embedded -->

---

**免责声明**：本 Skill 由 AI 辅助生成，仅供参考。使用前请阅读相关文档，并根据实际环境验证功能表现。
