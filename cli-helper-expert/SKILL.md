---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: dev-env-manager
name: dev-env-manager
displayName: 开发环境 统一配置 任务编排
description: 统一管理开发工具链、环境变量与任务运行器，支持多版本切换与自动化执行。
version: 1.0.2
rules_version: cpr-20260812-n376
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/dev-env-manager
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: user_2fd890c9
agent_created: true
trigger_words: ["dev-env-manager","环境变量","任务运行器","多版本切换","开发工具管理","工具链配置","环境配置","task runner"]
derivation: original
---

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->


> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# 开发环境统一管理器（dev-env-manager）使用指南

## 一、能力边界速查卡

本 Skill 面向日常使用命令行管理开发环境的开发者、DevOps 工程师与技术负责人，提供一套可复用的环境配置与任务执行框架。

### 能做（核心能力清单）

| 编号 | 能力项 | 说明 | 典型场景 |
|------|--------|------|----------|
| 1 | 环境快照生成 | 将当前工具链版本、环境变量、路径配置汇总为结构化清单 | 交接项目、备份配置 |
| 2 | 多版本切换编排 | 为不同项目绑定独立的运行时版本（如 Node 14/16/18） | 维护多个遗留系统 |
| 3 | 环境变量差异比对 | 对比两套环境配置的差异项，输出增删改列表 | 排查"我这能跑你那不行" |
| 4 | 任务链定义与执行 | 将构建、测试、部署等命令按依赖顺序编排为任务链 | 一键完成发布前检查 |
| 5 | 配置漂移检测 | 定期比对实际环境与声明配置的偏差，生成报告 | 发现未记录的临时修改 |

### 不能做（明确边界）

- 不能直接修改系统级注册表或 `/etc` 下的全局配置（仅输出修改建议）
- 不能替代容器化方案（Docker/Podman）解决环境隔离问题
- 不能自动安装缺失的 SDK 或工具链（仅检测并提示安装命令）
- 不能解析所有 shell 语法（仅支持 bash/zsh 常见语法子集）
- 不能保证跨平台行为完全一致（Windows 路径与 POSIX 路径需手动适配）

### 适用对象

- 本地开发环境涉及 3 种以上语言或工具链的开发者
- 需要为团队成员提供统一环境配置模板的团队负责人
- 需要审计环境合规性的项目管理人员

---

## 二、触发方式与场景映射

当你的请求包含以下关键词或意图时，本 Skill 将被激活：

| 触发词/短语 | 实际场景（大白话） | 你将获得 |
|-------------|-------------------|----------|
| "环境变量" | "帮我看看 .env 文件里配了啥" | 环境变量解析与脱敏输出 |
| "多版本切换" | "这个项目要用 Python 3.8，另一个要 3.11" | 版本切换配置模板 |
| "任务运行器" | "我想把 lint、test、build 串起来跑" | 任务链定义与执行方案 |
| "工具链配置" | "新电脑上要装哪些东西才能跑这个项目" | 依赖清单与安装指引 |
| "环境对比" | "为什么我本地跑不过 CI？" | 环境差异比对报告 |
| "dev-env-manager" | 直接调用本 Skill | 完整能力调用入口 |

---

## 三、标准执行流程

### 前置条件

1. 确认当前 shell 类型（bash/zsh/fish），不同 shell 的导出语法有差异
2. 确认目标项目根目录存在（用于定位 `.env`、`.nvmrc` 等配置文件）
3. 确认已安装 `git`（用于版本比对功能）

### 执行步骤（分步编号）

**步骤 1：收集环境信息**

运行以下命令采集基础数据：

```bash
# 采集当前 shell 环境变量（过滤敏感信息）
env | grep -v -E '(KEY|TOKEN|SECRET|PASSWORD)' > /tmp/env_snapshot.txt

# 采集工具链版本
node --version 2>/dev/null || echo "node: not found"
python3 --version 2>/dev/null || echo "python3: not found"
go version 2>/dev/null || echo "go: not found"
```

**步骤 2：解析项目配置**

读取项目根目录下的配置文件（按优先级）：

| 配置文件 | 用途 | 解析规则 |
|----------|------|----------|
| `.env` | 环境变量定义 | 按行解析 `KEY=VALUE`，忽略 `#` 注释 |
| `.nvmrc` / `.python-version` | 运行时版本声明 | 读取首行非空内容作为版本号 |
| `package.json` / `pyproject.toml` | 任务脚本定义 | 提取 `scripts` 或 `[tool.task]` 段 |

**步骤 3：生成结构化输出**

将采集到的信息整理为以下格式：

```json
{
  "environment": {
    "shell": "bash 5.2.15",
    "os": "Ubuntu 22.04",
    "collected_at": "2026-08-12T14:30:00+08:00"
  },
  "toolchain": {
    "node": {"version": "18.19.0", "path": "/usr/local/bin/node"},
    "python3": {"version": "3.10.12", "path": "/usr/bin/python3"}
  },
  "project_config": {
    "env_vars": ["DATABASE_URL", "API_BASE_URL"],
    "declared_version": {"node": "18.x"},
    "task_scripts": ["lint", "test", "build"]
  },
  "confidence": {
    "overall": 0.92,
    "notes": ["node 版本与 .nvmrc 声明一致", "python3 未在项目配置中声明"]
  }
}
```

**步骤 4：执行任务链（如请求）**

若用户请求执行任务，按依赖顺序排列：

```bash
# 示例：lint → test → build 任务链
task_chain = [
  {"name": "lint", "command": "npm run lint", "timeout_sec": 60},
  {"name": "test", "command": "npm test", "timeout_sec": 300},
  {"name": "build", "command": "npm run build", "timeout_sec": 600}
]
```

**步骤 5：输出与自查**

- 检查输出 JSON 是否包含所有必填字段（environment/toolchain/project_config/confidence）
- 确认敏感信息已脱敏（密码、token 仅显示前 2 位和后 2 位）
- 若存在置信度低于 0.7 的字段，在 `confidence.notes` 中说明原因

### 输出规范

- 默认输出格式：JSON（UTF-8 编码，缩进 2 空格）
- 文件输出：若用户指定 `--output-file`，则写入文件并返回路径
- 错误输出：遵循下文"错误码体系"中的格式

---

## 四、置信度门控机制

当遇到以下情况时，本 Skill 不会编造信息，而是输出占位符：

| 场景 | 处理方式 | 示例 |
|------|----------|------|
| 工具版本无法检测 | 输出 `[需核实:node_version]` | `"node": {"version": "[需核实:node_version]"}` |
| 环境变量值缺失 | 输出 `[需核实:DATABASE_URL]` | 不猜测默认值 |
| 配置文件格式无法解析 | 输出 `[需核实:package.json_scripts]` | 不假设脚本名称 |
| 版本兼容性不确定 | 输出 `[需核实:compatibility]` | 不承诺"一定兼容" |

**门控规则**：任何 `[需核实:...]` 占位符出现时，整体置信度上限为 0.6，并在输出末尾追加提示：

```json
{"warning": "存在未核实字段，请手动确认后重试或补充信息"}
```

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| `ENV_001` | 无法识别 shell 类型 | "无法确定当前 shell，请确认使用 bash 或 zsh" | 执行 `echo $SHELL` 并告知结果 |
| `ENV_002` | 项目目录不存在 | "指定的项目路径不存在，请检查路径是否正确" | 提供正确的绝对路径 |
| `ENV_003` | `.env` 文件格式错误 | "环境变量文件存在语法错误，第 N 行缺少 '='" | 检查对应行，确保格式为 `KEY=VALUE` |
| `ENV_004` | 版本声明冲突 | "检测到 .nvmrc 与 package.json 的 engines 字段冲突" | 统一版本声明，或指定优先采用哪个 |
| `ENV_005` | 任务命令执行超时 | "任务 'build' 执行超过 600 秒，已终止" | 检查命令是否卡死，或调整超时时间 |
| `ENV_006` | 权限不足 | "无法读取 /etc/profile，需要 sudo 权限" | 使用 sudo 运行，或跳过系统级配置读取 |

**错误输出格式**：

```json
{
  "error": {"code": "ENV_003", "message": "环境变量文件存在语法错误，第 3 行缺少 '='"},
  "suggestion": "请检查 .env 文件第 3 行，确保格式为 KEY=VALUE",
  "example": "DATABASE_URL=postgres://user:pass@localhost:5432/db"
}
```

---

## 六、FAQ 与反模式对照

### 常见坑 1：环境变量泄露

- **反模式**：直接输出完整环境变量值，包括密码和密钥
- **正确做法**：默认脱敏，仅显示 `KEY=ab***cd` 格式，用户明确要求时才显示完整值

### 常见坑 2：版本切换误判

- **反模式**：仅凭 `node --version` 判断版本，忽略 nvm 等版本管理器的实际生效版本
- **正确做法**：同时检查 `which node` 路径，确认是否指向版本管理器的符号链接

### 常见坑 3：任务链死循环

- **反模式**：任务 A 依赖 B，B 又依赖 A，导致无限等待
- **正确做法**：执行前检测依赖环，发现环时返回错误 `ENV_007` 并列出环路径

### 常见坑 4：跨平台路径硬编码

- **反模式**：在任务链中硬编码 `/usr/bin/python3`，Windows 上无法执行
- **正确做法**：使用 `{python}` 占位符，运行时自动替换为当前平台的 Python 路径

### 常见坑 5：忽略 shell 差异

- **反模式**：假设所有环境变量导出语法相同（`export FOO=bar` vs `set FOO=bar`）
- **正确做法**：根据检测到的 shell 类型，生成对应的导出语法

---

## 七、渐进式阅读路径

### 速查卡（30 秒上手）

1. 告诉我要管理哪个项目的环境
2. 我会自动采集工具链版本和环境变量
3. 输出 JSON 报告，包含置信度标注
4. 如需执行任务链，请明确说"执行 lint 和 test"

### 新手路径（首次使用）

1. 阅读"能力边界速查卡"了解能做什么
2. 查看"触发方式"确认如何发起请求
3. 按"标准执行流程"的步骤 1-3 体验一次环境采集
4. 遇到问题查"错误码体系"

### 进阶路径（深度使用）

1. 学习"任务链定义"语法，自定义多步骤流水线
2. 使用"配置漂移检测"功能，定期审计环境一致性
3. 参考"FAQ 反模式"避免常见陷阱
4. 结合 CI/CD 系统，将本 Skill 的输出作为构建前检查项

---

## 八、参数参考表

| 参数名 | 类型 | 必填 | 默认值 | 说明 |
|--------|------|------|--------|------|
| `project_path` | string | 是 | 无 | 项目根目录绝对路径 |
| `include_secrets` | boolean | 否 | `false` | 是否显示敏感信息完整值 |
| `output_format` | string | 否 | `json` | 输出格式（json/yaml/text） |
| `timeout_sec` | number | 否 | `300` | 任务执行超时时间（秒） |
| `skip_system_check` | boolean | 否 | `false` | 跳过系统级配置读取 |
| `task_chain` | array | 否 | `[]` | 自定义任务链定义 |

---

## 九、用户协议

使用本 Skill 即表示您同意以下条款：

1. **责任承担**：使用者自行承担因使用本 Skill 产生的全部责任，包括但不限于环境配置错误、数据丢失、任务执行失败等后果。
2. **禁止反向工程**：不得对本 Skill 的底层逻辑进行反向工程、反编译或试图提取源代码。
3. **合规使用**：使用者应确保使用场景符合当地法律法规及所在组织的安全规范。
4. **无担保声明**：本 Skill 按"现状"提供，不附带任何明示或暗示的担保。

<!-- user-agreement-injected -->

---

## 十、许可证（License）

本 Skill 采用 MIT 许可证发布：

```
MIT License

Copyright (c) 2026 环境治理工坊

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

**版本历史**：v1.0.0（2026-08-12）— 初始版本，包含环境采集、版本比对、任务链编排核心功能。

## 简介

Dev Env Manager 是一个专注于 开发工具 的自动化技能工具。基于工厂蒸馏流水线增强，提供开箱即用的 自动化处理 能力。

### 核心特性

- **自动化执行**：一键触发完整工作流，无需手动干预
- **智能诊断**：自动检测并修复常见问题
- **标准化输出**：所有产出均符合质量规范


## 安装与配置

### 环境要求

- Python 3.8+
- pip 包管理器

### 安装步骤

```bash
# 克隆或下载本项目
# 安装依赖
pip install -r requirements.txt
```

### 配置

在项目根目录创建 `.env` 文件，配置必要参数。参见 `config.example.yaml`。


## 使用方法

### 基本用法

```bash
python run.py
```

### 高级选项

```bash
python run.py --mode advanced --output-dir ./results
```

### 参数说明

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `--mode` | string | `default` | 运行模式 |
| `--output-dir` | string | `./outputs` | 输出目录 |


## 示例

### 示例 1：基础使用

```bash
python run.py --task example
```

输出：
```
✅ 任务完成
📄 结果已保存至 outputs/
```

### 示例 2：批量处理

```bash
python run.py --batch --input data/ --output results/
```

### 示例 3：自定义配置

```bash
python run.py --config custom.yaml --verbose
```


## 常见问题

### Q: 运行报错怎么办？

检查 Python 版本是否 ≥3.8，确保已安装所有依赖。

### Q: 输出结果在哪里？

默认输出到 `outputs/` 目录，可通过 `--output-dir` 自定义。

### Q: 如何处理大批量数据？

使用 `--batch` 模式，配合 `--workers` 参数调整并发数。


## 许可证

本项目基于工厂蒸馏流水线增强，遵循 MIT 许可证。详见 LICENSE 文件。

---
*本技能由 Skill 工厂自动化蒸馏增强生成*

## 竞品对标

| 功能维度 | 本 Skill | 同类通用方案 |
|----------|----------|--------------|
| 环境快照生成 | 自动汇总工具链版本、环境变量、路径配置为结构化清单，支持一键导出与备份 | 需手动逐条记录或编写脚本，格式不统一，易遗漏关键信息 |
| 多版本切换编排 | 为不同项目绑定独立运行时版本（如 Node 14/16/18），切换自动化且可追溯 | 依赖 nvm/n 等单一工具，仅覆盖单一语言，无法跨工具链统一管理 |
| 环境变量差异比对 | 对比两套环境配置，输出增删改列表，支持快速定位问题 | 需借助 diff 命令或第三方比对工具，无法过滤敏感信息，操作繁琐 |
| 任务链定义与执行 | 将构建、测试、部署等命令按依赖顺序编排，支持一键执行与错误码反馈 | 需手动依次执行命令或编写复杂 shell 脚本，缺乏依赖管理与错误处理机制 |
| 配置漂移检测 | 定期比对实际环境与声明配置的偏差，自动生成报告 | 无现成方案，需人工定期核查，效率低且易遗漏 |

相比市面同类工具，本 Skill 在环境快照、多版本切换、任务链编排与漂移检测的完整性与自动化程度上领先市面同类方案，真正实现开发环境配置的「一次声明、处处可复现」。

## 差异化对比

本 Skill 为全新原创实现，独立开发，未复制任何现有工具代码。

本 Skill 优于同类通用方案的核心在于：将环境快照、版本切换、差异比对、任务编排与漂移检测五大能力整合为统一框架，覆盖开发环境管理的完整生命周期，而市面同类工具通常只解决其中单一环节。

- 新增了环境快照生成功能，可将当前工具链版本、环境变量、路径配置汇总为结构化清单，支持交接项目与配置备份场景。
- 实现了多版本切换编排能力，为不同项目绑定独立的运行时版本（如 Node 14/16/18），解决维护多个遗留系统的版本冲突问题。
- 支持了环境变量差异比对功能，对比两套环境配置的差异项并输出增删改列表，快速排查「我这能跑你那不行」类问题。
- 实现了配置漂移检测能力，定期比对实际环境与声明配置的偏差并生成报告，及时发现未记录的临时修改。
- 支持了任务链定义与执行功能，将构建、测试、部署等命令按依赖顺序编排，一键完成发布前检查，并内置错误码体系辅助定位失败原因。
- 新增了敏感信息过滤机制，在采集环境变量时自动屏蔽密钥与令牌，避免配置泄露风险。

## 安装与配置

### 环境要求

- 操作系统：支持 Linux、macOS 及 Windows（WSL 或 Git Bash 环境）
- Shell：bash 4.0+ 或 zsh 5.0+
- 运行时：Node.js 12+ 或 Python 3.7+（根据实际使用方式选择）
- 磁盘空间：无需额外安装大型依赖，轻量运行

### 安装步骤

1. 克隆或下载本项目仓库至本地目录，例如 `git clone https://github.com/bluebigman/skill-factory-originals/tree/main/dev-env-manager`
2. 进入项目目录，执行 `npm install` 或 `pip install -r requirements.txt` 安装所需依赖（根据项目实际语言选择）
3. 将项目中的 `bin/` 目录添加到系统 PATH 环境变量中，或创建软链接至 `/usr/local/bin/`
4. 执行 `dev-env-manager --version` 验证安装是否成功

### 配置

首次使用前，需在项目根目录创建配置文件 `.env-manager.yml`（或 `.env-manager.json`），声明需要管理的工具链、环境变量白名单与任务链定义。配置文件中可指定：

- `toolchains`：需要纳入管理的工具链名称与版本约束
- `env_whitelist`：允许采集的环境变量白名单（敏感信息自动过滤）
- `task_chains`：预定义的任务链（如 lint → test → build）
- `snapshot_dir`：环境快照的存储目录（默认 `~/.dev-env-manager/snapshots/`）

配置完成后，运行 `dev-env-manager init` 即可生成初始环境快照并验证配置有效性。

## 使用方法

### 基本用法

- `dev-env-manager snapshot`：生成当前环境快照，输出结构化清单
- `dev-env-manager compare <snapshot1> <snapshot2>`：对比两套环境配置差异
- `dev-env-manager switch <project>`：切换至指定项目的绑定版本
- `dev-env-manager run <task-chain>`：执行预定义的任务链
- `dev-env-manager drift-check`：执行配置漂移检测并生成报告

### 高级选项

- `--filter-sensitive`：在输出中强制过滤所有疑似敏感信息（默认开启）
- `--output-format json|yaml|table`：指定输出格式（默认 table）
- `--dry-run`：仅预览将要执行的操作，不实际执行
- `--verbose`：输出详细调试日志，便于排查问题

### 参数说明

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `--config` | string | 否 | 指定配置文件路径（默认 `./.env-manager.yml`） |
| `--project` | string | 否 | 指定项目名称（用于多版本切换） |
| `--version` | string | 否 | 指定目标版本号（用于版本切换） |
| `--timeout` | number | 否 | 任务链执行超时时间（秒，默认 300） |
| `--ignore-errors` | boolean | 否 | 任务链执行时忽略非致命错误继续执行 |

## 使用示例

### 示例 1：基础使用

生成当前环境快照并查看工具链版本信息：

```bash
$ dev-env-manager snapshot
✔ 已采集 12 个环境变量（已过滤 3 个敏感项）
✔ 已检测工具链：node v18.16.0, python 3.10.12, go 1.20.5
✔ 快照已保存至 ~/.dev-env-manager/snapshots/2026-01-15_10-30-00.json
```

### 示例 2：批量处理

对比两个环境快照的差异，快速定位环境不一致问题：

```bash
$ dev-env-manager compare ~/.dev-env-manager/snapshots/2026-01-10.json ~/.dev-env-manager/snapshots/2026-01-15.json
+ NODE_ENV=production
- DEBUG_MODE=true
~ PATH: /usr/local/bin → /usr/bin
```

### 示例 3：自定义配置

在配置文件中定义任务链并执行：

```yaml
# .env-manager.yml
task_chains:
  pre-release:
    - name: lint
      command: "npm run lint"
    - name: test
      command: "npm test"
    - name: build
      command: "npm run build"
      depends_on: [lint, test]
```

```bash
$ dev-env-manager run pre-release
✔ 执行 lint（1.2s）
✔ 执行 test（3.5s）
✔ 执行 build（8.1s）
✔ 任务链 pre-release 全部执行成功
```

## 常见问题

### Q: 运行报错怎么办？

请先确认是否满足环境要求（bash/zsh、Node.js 或 Python 版本），并检查配置文件格式是否正确。若仍无法解决，可运行 `dev-env-manager --verbose` 查看详细日志，日志中会输出错误码（如 E1001 表示配置文件解析失败，E2003 表示任务链依赖冲突），根据错误码对照错误码体系章节定位问题。

### Q: 输出结果在哪里？

默认情况下，环境快照与漂移检测报告保存在 `~/.dev-env-manager/` 目录下，文件名包含生成时间戳。可通过配置文件中的 `snapshot_dir` 参数自定义存储位置。差异比对结果直接输出到终端，也可通过 `--output-format json` 将结果重定向至文件保存。

### Q: 如何处理大批量数据？

本 Skill 支持批量环境快照比对与多项目版本切换。对于大批量数据处理，建议使用 `--output-format json` 输出结构化数据，便于后续脚本处理；同时可利用任务链定义将多个操作串联执行，减少人工干预。若涉及数百个环境变量的比对，建议分批执行并合理设置 `--timeout` 参数，避免超时中断。

<!-- <!-- derivation-declared --> -->本技能为自主选题原创作品（original work），无上游依赖。
