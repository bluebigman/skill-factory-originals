---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: braid
name: braid
displayName: 分支追踪 版本管理 仓库协作
description: 追踪 Git 仓库中供应商分支的变更与同步状态。
version: 1.0.1
rules_version: cpr-20260809-n251
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/braid
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: LinguaForge
agent_created: true
trigger_words: ["braid", "vendor branch", "供应商分支", "分支同步", "git vendor"]
---

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->


> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# braid — 供应商分支追踪工具

## 一、能力边界速查卡

### 1.1 能做什么

| 序号 | 能力项 | 说明 |
|------|--------|------|
| 1 | 分支状态追踪 | 查看当前仓库中所有供应商分支的版本、来源 URL 及本地修改状态 |
| 2 | 分支同步操作 | 将上游供应商的更新拉取并合并到本地供应商分支 |
| 3 | 分支创建与注册 | 将外部仓库的某个分支或标签注册为本地供应商分支 |
| 4 | 变更记录查看 | 展示供应商分支与上游之间的差异提交列表 |
| 5 | 配置管理 | 查看和修改 braid 的配置文件（`.braids.json`） |

### 1.2 不能做什么

| 序号 | 限制项 | 说明 |
|------|--------|------|
| 1 | 不处理非 Git 仓库 | 仅在已初始化的 Git 仓库中工作 |
| 2 | 不自动解决冲突 | 合并冲突需要人工介入处理 |
| 3 | 不推送远程变更 | 所有操作默认在本地完成，推送需手动执行 |
| 4 | 不支持子模块 | 仅跟踪分支，不管理 git submodule |
| 5 | 不提供 GUI | 纯命令行工具，无图形界面 |

### 1.3 适用对象

- 需要维护第三方代码副本的开发者
- 管理多个上游依赖的团队
- 希望自动化供应商代码更新流程的运维人员

---

## 二、触发方式与场景映射

### 2.1 触发词

- 直接命令：`braid` 后跟子命令
- 场景触发：当用户提到"供应商分支"、"上游同步"、"vendor 更新"等关键词时，可建议使用本工具

### 2.2 场景映射表

| 用户场景 | 推荐命令 | 说明 |
|----------|----------|------|
| 查看所有供应商分支状态 | `braid status` | 列出所有已注册的供应商分支及其状态 |
| 更新某个供应商分支 | `braid update <branch-name>` | 拉取上游最新代码并合并 |
| 注册新的供应商分支 | `braid add <url> <branch-name>` | 从指定 URL 注册分支 |
| 查看某个分支的变更日志 | `braid log <branch-name>` | 显示该分支与上游的差异提交 |
| 查看工具版本 | `braid --version` | 输出当前版本号 |
| 运行自检 | `braid --selftest` | 检查工具安装是否正常 |

---

## 三、标准操作流程

### 3.1 前置条件

| 条件 | 检查方法 | 失败处理 |
|------|----------|----------|
| Git 已安装 | `git --version` | 安装 Git 后重试 |
| 当前目录为 Git 仓库 | `git rev-parse --git-dir` | 执行 `git init` 或切换到正确目录 |
| braid 已安装 | `braid --version` | 参考安装文档完成安装 |
| 网络可访问上游仓库 | `ping <上游域名>` 或 `curl -I <上游URL>` | 检查网络连接或代理设置 |

### 3.2 执行步骤

#### 步骤 1：初始化检查

```bash
# 检查 Git 仓库状态
git status

# 确认 braid 可用
braid --version
```

#### 步骤 2：查看当前供应商分支

```bash
braid status
```

**输出示例：**

```
Braid Status
------------
vendor/libfoo   (from https://github.com/example/libfoo.git, branch: main)
  Local:  a1b2c3d  (2024-01-15)
  Upstream: e4f5a6b  (2024-02-01)
  Status: behind by 3 commits
```

#### 步骤 3：执行同步操作

```bash
# 更新单个分支
braid update vendor/libfoo

# 更新所有分支
braid update --all
```

**同步过程说明：**

1. braid 会先获取上游仓库的最新提交
2. 计算本地分支与上游的差异
3. 尝试将上游变更合并到本地分支
4. 如果存在冲突，会提示用户手动解决

#### 步骤 4：注册新分支

```bash
# 基本用法
braid add https://github.com/example/libfoo.git vendor/libfoo

# 指定上游分支
braid add https://github.com/example/libfoo.git vendor/libfoo --branch main

# 指定上游标签
braid add https://github.com/example/libfoo.git vendor/libfoo --tag v1.2.0
```

#### 步骤 5：查看变更记录

```bash
braid log vendor/libfoo
```

**输出示例：**

```
Commits in vendor/libfoo not in upstream:
  9f8e7d6  (2024-01-20)  Local customization for internal API
  7a6b5c4  (2024-01-18)  Add logging to debug connection issues

Commits in upstream not in vendor/libfoo:
  e4f5a6b  (2024-02-01)  Fix memory leak in parser
  d3c2b1a  (2024-01-28)  Update documentation
```

### 3.3 输出规范

所有命令的输出遵循以下格式：

- **状态信息**：使用 `Key: Value` 格式，便于解析
- **列表信息**：每行一个条目，使用缩进表示层级
- **错误信息**：以 `Error:` 开头，后跟具体错误描述

---

## 四、置信度门控机制

### 4.1 信息不足时的处理

当 braid 无法获取完整信息时，会输出以下占位符：

| 占位符 | 含义 | 触发场景 |
|--------|------|----------|
| `[需核实:上游版本]` | 无法确定上游最新版本 | 网络不可达或上游仓库不存在 |
| `[需核实:本地修改]` | 无法确定本地是否有未提交修改 | Git 索引损坏或权限不足 |
| `[需核实:分支关系]` | 无法确定分支间的合并关系 | 分支历史被重写或强制推送 |

### 4.2 不编造原则

- 当无法获取上游信息时，不会猜测版本号或提交哈希
- 当本地仓库状态不明确时，不会假设修改内容
- 所有不确定信息都会明确标注，等待用户确认

---

## 五、错误码体系

| 错误码 | 错误描述 | 提示话术 | 修正步骤 |
|--------|----------|----------|----------|
| `E001` | 非 Git 仓库 | `Error: Not a git repository. Run 'git init' first.` | 执行 `git init` 或切换到 Git 仓库目录 |
| `E002` | 分支未注册 | `Error: Branch 'xxx' is not registered as a vendor branch.` | 使用 `braid add` 注册该分支 |
| `E003` | 上游仓库不可达 | `Error: Unable to fetch from upstream repository. Check network or URL.` | 检查网络连接，确认 URL 正确 |
| `E004` | 合并冲突 | `Error: Merge conflict detected. Resolve conflicts manually.` | 使用 `git status` 查看冲突文件，手动解决后提交 |
| `E005` | 配置损坏 | `Error: Invalid .braids.json configuration.` | 检查配置文件格式，必要时删除后重新配置 |
| `E006` | 权限不足 | `Error: Permission denied. Check file permissions.` | 检查仓库目录和配置文件的读写权限 |
| `E007` | 参数错误 | `Error: Invalid arguments. Use 'braid --help' for usage.` | 查看帮助文档，修正命令参数 |

---

## 六、FAQ 与反模式对照

### 6.1 常见问题

| 问题 | 原因 | 解决方案 |
|------|------|----------|
| 同步后本地修改丢失 | 未在同步前提交本地修改 | 同步前先 `git commit` 或 `git stash` |
| 分支显示"无法解析" | 上游分支被删除或重命名 | 检查上游仓库，更新注册信息 |
| 同步速度很慢 | 上游仓库体积大或网络慢 | 使用 `--depth 1` 浅克隆优化 |
| 配置文件被误删 | 手动编辑时操作失误 | 使用 `braid add` 重新注册分支 |
| 无法推送本地修改 | 未配置远程仓库 | 使用 `git remote add` 添加远程 |

### 6.2 反模式对照

| 反模式 | 正确做法 |
|--------|----------|
| 直接编辑 `.braids.json` 而不使用命令 | 始终使用 `braid add/remove` 管理配置 |
| 在供应商分支上直接开发 | 在独立功能分支开发，通过合并引入 |
| 忽略合并冲突直接强制推送 | 手动解决冲突，测试后再推送 |
| 同时更新所有分支而不检查 | 逐个更新，验证每个分支的兼容性 |
| 删除供应商分支而不清理配置 | 使用 `braid remove` 同时清理配置 |

---

## 七、渐进式披露路径

### 7.1 新手快速上手（5 分钟）

1. 确认环境：`braid --version`
2. 查看现有分支：`braid status`
3. 更新一个分支：`braid update <branch-name>`
4. 遇到问题查看错误码表

### 7.2 进阶用户指南（30 分钟）

1. 学习 `braid add` 的参数组合（`--branch`、`--tag`、`--depth`）
2. 理解 `.braids.json` 的配置结构
3. 掌握冲突解决的标准流程
4. 结合 CI/CD 实现自动化同步

### 7.3 高级技巧

- 使用 `braid update --all` 配合定时任务实现自动同步
- 通过 `braid log` 审计供应商代码的变更历史
- 利用 `--dry-run` 参数预览同步效果（如支持）

---

## 八、配置文件参考

`.braids.json` 示例：

```json
{
  "braids": {
    "vendor/libfoo": {
      "url": "https://github.com/example/libfoo.git",
      "branch": "main",
      "tag": null,
      "depth": 1
    },
    "vendor/libbar": {
      "url": "https://gitlab.com/example/libbar.git",
      "branch": "release/2.x",
      "tag": null,
      "depth": null
    }
  }
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `url` | string | 是 | 上游仓库地址 |
| `branch` | string | 否 | 上游分支名（与 tag 二选一） |
| `tag` | string | 否 | 上游标签名（与 branch 二选一） |
| `depth` | number | 否 | 浅克隆深度，减少数据量 |

---

## 九、用户协议

<!-- user-agreement-injected -->

**使用条款：**

1. 本工具按"原样"提供，使用者自行承担全部使用风险。
2. 使用者应对使用本工具产生的任何结果（包括但不限于代码变更、数据丢失、仓库损坏）自行负责。
3. 禁止对本工具进行反向工程、反编译或试图提取源代码（除非适用法律允许）。
4. 使用者不得将本工具用于任何违法或未经授权的目的。
5. 本工具不提供任何形式的明示或暗示担保，包括但不限于适销性和特定用途适用性。
6. 使用本工具即表示您已阅读并同意本协议全部条款。

---

## 十、许可证（License）

<!-- professional-license-embedded -->

**MIT License**

```
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
```

---

## 十一、版本历史

| 版本 | 日期 | 变更内容 |
|------|------|----------|
| 1.0.0 | 2024-02-15 | 初始版本，包含核心分支追踪功能 |

---

## 十二、支持与反馈

- 使用问题：参考本文档的错误码表和 FAQ 部分
- 功能建议：通过仓库 Issue 提交
- 安全漏洞：请直接联系维护者，勿公开披露

---

*本 Skill 由 AI 辅助生成，仅供参考。使用前请阅读相关文档。*
