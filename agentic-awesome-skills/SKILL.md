---
slug: agentic-awesome-skills
name: AI智能体技能运行器
displayName: 技能仓库调度 依赖镜像 结构化执行
description: 拉取GitHub技能仓库，自动处理依赖镜像，返回结构化执行结果。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 流云架构师
agent_created: true
trigger_words: ["技能运行", "技能拉取", "技能执行", "仓库运行", "技能调用", "技能调度", "仓库执行"]
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# AI智能体技能运行器 — 使用指南

本 Skill 用于从 GitHub 拉取技能仓库、自动处理依赖镜像、执行技能并返回结构化 JSON 结果。以下内容按「速查卡 → 详细流程 → 进阶配置」分层组织，请根据自身经验水平选择阅读路径。

---

## 一、能力边界（一页纸速查卡）

### 能做

| 能力项 | 说明 |
|--------|------|
| 仓库探测 | 检查目标仓库是否存在、是否公开、网络是否可达 |
| 技能拉取 | 克隆公开技能仓库到本地工作区 |
| 依赖镜像 | 自动读取 `config/mirrors.json`，替换依赖源为镜像地址 |
| 技能执行 | 按 `skill.json` 定义运行技能，捕获 stdout/stderr |
| 结构化输出 | 返回 JSON，包含状态码、执行日志、产物路径、耗时等字段 |
| 自检模式 | `--selftest` 验证本机环境（Git、网络、运行时）是否就绪 |

### 不能做

| 限制项 | 说明 |
|--------|------|
| 私有仓库 | 无法克隆需要鉴权的私有仓库（无凭据注入机制） |
| 交互式技能 | 不支持需要 TTY 交互的终端程序（如 vim、htop） |
| 跨平台运行时 | 仅支持 `runtimes/` 目录下已注册的运行时适配器 |
| 依赖自动修复 | 镜像替换仅覆盖 `mirrors.json` 中列出的依赖源，其余报错需人工介入 |
| 无限重试 | 网络超时默认 30 秒，超时即失败，不自动重试 |

### 适用对象

- 需要批量运行多个技能仓库的自动化流水线
- 希望将技能执行结果接入自有监控/报表系统的开发者
- 在受限网络环境中需要依赖镜像加速的团队

---

## 二、触发方式

### 触发词

直接使用以下任一短语即可唤起本 Skill：

- 技能运行 / 技能拉取 / 技能执行 / 仓库运行 / 技能调用
- 技能调度 / 仓库执行（补充触发词）

### 场景映射表

| 你说的话 | 实际动作 |
|----------|----------|
| "帮我跑一下 octocat/Hello-World 这个仓库" | 执行 `技能拉取 --repo octocat/Hello-World`，然后尝试运行 |
| "检查一下网络通不通" | 执行 `curl -I https://github.com` 并报告结果 |
| "这个技能跑完结果存哪了" | 解析 JSON 输出的 `artifacts` 字段，给出绝对路径 |
| "批量跑 5 个仓库" | 循环调用 `技能执行 --repo <name>`，汇总 JSON 数组 |

---

## 三、标准流程

### 前置条件

| 条件 | 检查方式 |
|------|----------|
| 本机已安装 Git | `git --version` 返回非空 |
| 网络可访问 GitHub | `curl -I https://github.com` 返回 200 或 301 |
| 目标仓库为公开仓库 | 浏览器访问仓库页面，确认无锁图标 |
| 运行时依赖已安装 | 根据 `skill.json` 的 `runtime` 字段，确认对应解释器存在 |

### 执行步骤

#### 第一步：环境自检

```bash
agentic-awesome-skills --selftest
```

预期输出（JSON）：

```json
{
  "status": "ok",
  "checks": {
    "git": "2.39.2",
    "network": "reachable",
    "runtime": "python3.11"
  }
}
```

若任一检查失败，输出 `"status": "degraded"` 并列出失败项。

#### 第二步：拉取仓库

```bash
agentic-awesome-skills 技能拉取 --repo octocat/Hello-World
```

参数说明：

| 参数 | 必填 | 默认值 | 说明 |
|------|------|--------|------|
| `--repo` | 是 | 无 | 格式为 `owner/repo` |
| `--branch` | 否 | `main` | 指定分支 |
| `--depth` | 否 | `1` | 浅克隆深度，设为 `0` 表示完整克隆 |

#### 第三步：执行技能

```bash
agentic-awesome-skills 技能执行 --repo owner/simple-skill
```

执行前自动完成：

1. 读取仓库根目录 `skill.json`
2. 校验 `skill.json` 必填字段（`name`、`version`、`entry`）
3. 根据 `runtime` 字段选择适配器（`runtimes/` 目录下）
4. 读取 `config/mirrors.json`，替换依赖源
5. 运行入口文件，捕获输出

#### 第四步：查看输出

返回 JSON 结构示例：

```json
{
  "status": "success",
  "repo": "owner/simple-skill",
  "exit_code": 0,
  "stdout": "Hello from skill",
  "stderr": "",
  "duration_ms": 1234,
  "artifacts": ["/tmp/agentic-skills/owner/simple-skill/output.json"],
  "mirror_used": true
}
```

字段说明：

| 字段 | 类型 | 说明 |
|------|------|------|
| `status` | string | `success` / `failed` / `skipped` |
| `exit_code` | int | 进程退出码，0 为成功 |
| `stdout` | string | 标准输出全文 |
| `stderr` | string | 错误输出全文 |
| `duration_ms` | int | 执行耗时（毫秒） |
| `artifacts` | array | 产物文件绝对路径列表 |
| `mirror_used` | bool | 是否启用了镜像替换 |

### 输出规范

- 所有输出均为 UTF-8 编码 JSON
- 日志写入 `logs/exec_<timestamp>.log`
- 产物默认保存在 `/tmp/agentic-skills/<owner>/<repo>/` 下
- 若需持久化，请参考「进阶配置」第 3 条

---

## 四、置信度门控

当出现以下情况时，本 Skill **不会**编造结果，而是输出占位符 `[需核实:字段]`：

| 场景 | 输出示例 |
|------|----------|
| 仓库存在但 `skill.json` 缺失 | `{"status": "failed", "error": "[需核实:skill.json] 未找到入口定义"}` |
| 网络超时但无法确认仓库状态 | `{"status": "unknown", "error": "[需核实:网络连通性] 请手动访问仓库页面确认"}` |
| 运行时版本未知 | `{"status": "failed", "error": "[需核实:runtime版本] 请检查 skill.json 的 runtime 字段"}` |

**原则**：信息不足时，宁可返回占位符，也不猜测或伪造数据。

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| `E001` | 仓库不存在 | "仓库 owner/repo 未找到，请检查拼写" | 1. 浏览器访问确认 2. 检查 owner 大小写 |
| `E002` | 仓库为私有 | "该仓库为私有，无法克隆" | 1. 确认仓库可见性 2. 使用公开仓库 |
| `E003` | 网络不可达 | "无法连接 GitHub，请检查网络" | 1. `curl -I https://github.com` 2. 配置代理 |
| `E004` | `skill.json` 缺失 | "仓库缺少技能定义文件" | 1. 检查仓库根目录 2. 确认文件命名 |
| `E005` | 运行时不适配 | "未找到对应运行时适配器" | 1. 查看 `runtimes/` 目录 2. 添加自定义适配器 |
| `E006` | 依赖安装失败 | "依赖安装失败，请查看 stderr" | 1. 检查 `mirrors.json` 2. 手动安装依赖 |
| `E007` | 执行超时 | "执行超过 30 秒，已终止" | 1. 修改超时配置 2. 优化技能逻辑 |

---

## 六、FAQ 反模式

### 反模式 1：忽略自检直接拉取

**错误做法**：跳过 `--selftest`，直接执行拉取，遇到网络错误才排查。

**正确做法**：先运行自检，确认 Git 和网络就绪后再操作。

### 反模式 2：依赖镜像配置错误

**错误做法**：修改 `mirrors.json` 时，将 `"source"` 和 `"target"` 写反，导致依赖源指向无效地址。

**正确做法**：`source` 为原始地址，`target` 为镜像地址。修改后先跑一次测试仓库验证。

### 反模式 3：忽略 `exit_code` 只看 `status`

**错误做法**：`status` 为 `success` 就认为技能完全正确，忽略 `exit_code` 非零的情况。

**正确做法**：`status` 表示流程是否走通，`exit_code` 表示技能自身是否成功。两者需同时检查。

### 反模式 4：产物路径写死

**错误做法**：在脚本中硬编码 `/tmp/agentic-skills/` 路径，导致清理临时文件后脚本失效。

**正确做法**：每次执行后从 JSON 输出的 `artifacts` 字段动态获取路径。

### 反模式 5：批量执行无超时控制

**错误做法**：循环执行 10 个仓库，不设置总超时，导致整体任务挂起。

**正确做法**：为每个仓库设置独立超时，并设置整体任务的最大执行时间。

---

## 七、渐进式披露

### 速查卡（新手必读）

1. 先跑 `--selftest`
2. 拉取用 `技能拉取 --repo owner/repo`
3. 执行用 `技能执行 --repo owner/repo`
4. 结果看 JSON 的 `status` 和 `exit_code`
5. 出错查错误码表

### 进阶路径（有经验用户）

#### 1. 理解 `skill.json` 规范

```json
{
  "name": "my-skill",
  "version": "1.0.0",
  "entry": "run.py",
  "runtime": "python3",
  "dependencies": ["requests>=2.0"],
  "timeout": 30
}
```

必填字段：`name`、`version`、`entry`、`runtime`
可选字段：`dependencies`、`timeout`（默认 30 秒）

#### 2. 实现依赖缓存机制

在 `config/mirrors.json` 中增加 `cache_dir` 字段：

```json
{
  "cache_dir": "/var/cache/agentic-skills",
  "mirrors": [
    {"source": "https://pypi.org/simple", "target": "https://mirror.example.com/pypi"}
  ]
}
```

缓存命中时跳过下载，日志中输出 `"cache": "hit"`。

#### 3. 输出文件持久化

设置环境变量 `AGENTIC_ARTIFACT_DIR`：

```bash
export AGENTIC_ARTIFACT_DIR=/data/skill-outputs
```

执行后，`artifacts` 中的文件会自动复制到该目录，并保留原始相对路径。

#### 4. 集成 CI/CD

示例 GitHub Actions 片段：

```yaml
- name: Run skill
  run: |
    agentic-awesome-skills 技能执行 --repo owner/simple-skill
  env:
    AGENTIC_ARTIFACT_DIR: ${{ github.workspace }}/artifacts
```

---

## 八、配置参考

### `config/mirrors.json` 结构

```json
{
  "mirrors": [
    {
      "source": "https://registry.npmjs.org",
      "target": "https://registry.npmmirror.com",
      "enabled": true
    }
  ],
  "timeout_seconds": 30
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `mirrors[].source` | string | 原始依赖源地址 |
| `mirrors[].target` | string | 镜像地址 |
| `mirrors[].enabled` | bool | 是否启用该镜像 |
| `timeout_seconds` | int | 全局超时时间，默认 30 |

### `runtimes/` 目录适配器

每个适配器为一个可执行脚本，命名格式：`<runtime-name>.sh`

示例 `python3.sh`：

```bash
#!/bin/bash
# 用法: python3.sh <entry_file> <timeout_seconds>
timeout "$2" python3 "$1"
```

---

## 九、用户协议

<!-- user-agreement-injected -->

**使用本 Skill 即表示您同意以下条款：**

1. **责任承担**：使用者应自行承担使用本 Skill 的全部责任。包括但不限于：所拉取技能仓库的合法性、执行结果的安全性、以及对下游系统的影响。本 Skill 提供者不对因使用本 Skill 而产生的任何直接或间接损失负责。

2. **禁止反向工程**：使用者不得对本 Skill 的源代码进行反向工程、反编译、破解或试图提取其底层算法逻辑，除非适用法律明确允许。

3. **合规使用**：使用者应确保所拉取和运行的技能仓库符合当地法律法规及 GitHub 服务条款，不得用于任何非法目的。

4. **免责声明**：本 Skill 按"现状"提供，不附带任何明示或暗示的保证，包括但不限于适销性、特定用途适用性和非侵权保证。

---

## 十、许可证（License）

<!-- professional-license-embedded -->

MIT License

Copyright (c) 2024 流云架构师

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
