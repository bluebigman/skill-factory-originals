---
slug: dev-env-manager
name: dev-env-manager
displayName: 开发环境 工具链 版本切换
description: 统一管理开发工具链、环境变量与任务运行器，支持多版本切换与自动化执行。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: env-architect
agent_created: true
trigger_words: ["dev-env-manager", "环境变量", "任务运行器", "多版本切换", "开发工具管理", "环境配置", "工具链管理", "版本切换"]

---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# 开发环境管理器（dev-env-manager）技能文档

## 一、能力边界速查卡

### 1.1 能做什么

| 能力项 | 说明 | 适用场景 |
|--------|------|----------|
| 环境采集 | 自动读取项目根目录下的 `.env`、`.nvmrc`、`.tool-versions` 等配置文件，汇总工具链版本与环境变量 | 新接手项目时快速了解环境依赖 |
| 多版本切换 | 针对 Node.js、Python、Go 等常见运行时，生成切换指令或直接执行切换（需用户确认） | 多个项目使用不同运行时版本时 |
| 任务链执行 | 支持自定义多步骤流水线（如 lint → test → build），按顺序执行并汇总结果 | 提交代码前批量执行质量检查 |
| 配置漂移检测 | 对比当前环境与项目声明的配置，输出差异报告 | 定期审计环境一致性，排查"在我机器上能跑"的问题 |
| 环境变量管理 | 读取、合并、导出环境变量，支持不同 shell（bash/zsh/fish）的语法差异 | 跨 shell 环境迁移或 CI 配置复用 |

### 1.2 不能做什么

| 限制项 | 说明 |
|--------|------|
| 不安装系统级依赖 | 不负责安装操作系统包（如 apt、brew），仅管理项目级工具链 |
| 不修改全局配置 | 默认不写入 `~/.bashrc` 等全局配置文件，除非用户明确要求 |
| 不处理 Docker 容器 | 仅管理宿主机环境，不涉及容器内环境配置 |
| 不保证版本兼容性 | 版本切换后是否兼容项目代码，需由用户自行验证 |

### 1.3 适用对象

- **前端/后端开发者**：需要管理多个项目的 Node.js、Python 等运行时版本
- **DevOps 工程师**：需要统一 CI 与本地环境的一致性
- **技术团队负责人**：需要审计团队开发环境配置

---

## 二、触发方式

### 2.1 触发词

直接使用以下任一方式发起请求：

- `dev-env-manager`
- `环境变量`
- `任务运行器`
- `多版本切换`
- `开发工具管理`
- `环境配置`
- `工具链管理`
- `版本切换`

### 2.2 场景映射表

| 你说的话（大白话） | 实际触发的能力 |
|-------------------|----------------|
| "帮我看看这个项目需要什么环境" | 环境采集 → 输出 JSON 报告 |
| "这个项目要用 Node 18，但我本机是 20" | 多版本切换 → 生成切换指令 |
| "跑一下 lint 和 test" | 任务链执行 → 按顺序执行并汇总 |
| "为什么我本地跑不过 CI？" | 配置漂移检测 → 输出差异报告 |
| "把 .env 里的变量导出到当前 shell" | 环境变量管理 → 按 shell 类型生成导出命令 |

---

## 三、标准执行流程

### 3.1 前置条件

| 条件 | 检查方式 | 不满足时的处理 |
|------|----------|----------------|
| 确认 shell 类型 | 执行 `echo $SHELL` | 默认按 bash 处理，并在报告中标注 |
| 确认项目根目录存在 | 检查用户提供的路径是否有效 | 提示用户重新输入路径 |
| 确认已安装 git | 执行 `git --version` | 跳过版本比对功能，仅输出环境采集结果 |

### 3.2 执行步骤

**步骤 1：确认目标项目**

用户需提供项目根目录路径。示例：

```
用户：管理 /home/user/my-project 的环境
助手：确认路径存在，开始采集配置
```

**步骤 2：采集工具链版本**

自动执行以下检查（按需）：

| 工具 | 检查命令 | 配置文件 |
|------|----------|----------|
| Node.js | `node --version` | `.nvmrc`、`package.json` |
| Python | `python --version` | `.python-version`、`pyproject.toml` |
| Go | `go version` | `go.mod` |
| Java | `java -version` | `pom.xml`、`build.gradle` |
| 包管理器 | `npm --version` / `pnpm --version` | `package.json` |

**步骤 3：读取环境变量**

- 读取项目根目录下的 `.env` 文件（若存在）
- 检查 `.env.example` 是否存在，用于比对缺失变量
- 输出变量名列表（**不输出值**，避免敏感信息泄露）

**步骤 4：生成 JSON 报告**

输出格式如下：

```json
{
  "project": "/home/user/my-project",
  "shell": "bash",
  "tools": {
    "node": {"current": "v20.11.0", "required": "v18.0.0", "match": false},
    "python": {"current": "3.11.5", "required": "3.10.0", "match": false}
  },
  "env_vars": {
    "declared": ["API_KEY", "DB_HOST", "LOG_LEVEL"],
    "missing_from_example": ["DB_PORT"],
    "confidence": 0.85
  },
  "drift_detected": true
}
```

**步骤 5：执行任务链（可选）**

用户明确说"执行 lint 和 test"时，按以下顺序执行：

1. 读取项目 `package.json` 中的 `scripts` 字段
2. 依次执行 `npm run lint` → `npm run test`
3. 汇总每个步骤的退出码与输出摘要

### 3.3 输出规范

- 所有报告以 JSON 格式输出，便于机器解析
- 每个字段附带置信度标注（0-1），低于 0.7 的字段标注 `[需核实:字段名]`
- 不编造不存在的配置信息，未检测到的工具标注为 `"not_detected"`

---

## 四、置信度门控

### 4.1 信息不足时的处理

当出现以下情况时，输出 `[需核实:字段]` 占位符，不进行猜测：

| 场景 | 处理方式 |
|------|----------|
| 项目根目录未指定 | `[需核实:project_path]`，提示用户补充 |
| `.nvmrc` 存在但内容为空 | `[需核实:node_version]`，提示用户检查文件 |
| 检测到多个包管理器锁文件 | 全部列出，标注 `[需核实:primary_package_manager]` |
| 环境变量值包含特殊字符 | 仅输出变量名，不输出值 |

### 4.2 置信度计算规则

| 因素 | 权重 | 说明 |
|------|------|------|
| 配置文件完整性 | 40% | 配置文件存在且可解析 |
| 工具检测成功率 | 30% | 实际检测到的工具数 / 应检测的工具数 |
| 版本匹配度 | 20% | 当前版本与声明版本的一致性 |
| 环境变量覆盖率 | 10% | 已声明变量 / 示例文件变量 |

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| `E001` | 项目路径不存在 | "路径 /xxx 不存在，请确认后重试" | 检查路径拼写，或使用 `pwd` 获取当前路径 |
| `E002` | shell 类型无法识别 | "无法识别 shell 类型，默认按 bash 处理" | 手动指定 shell：`--shell zsh` |
| `E003` | 配置文件解析失败 | "解析 .env 文件时出错，请检查格式" | 检查是否有未转义的特殊字符 |
| `E004` | 工具未安装 | "未检测到 Node.js，请先安装" | 安装对应工具后重试 |
| `E005` | 任务链执行失败 | "lint 执行失败，退出码 1" | 查看具体错误输出，修复后重试 |
| `E006` | 版本切换失败 | "无法切换到 Node v18，nvm 未安装" | 安装 nvm 或使用其他版本管理器 |
| `E007` | 权限不足 | "无法写入 /usr/local/bin，需要 sudo 权限" | 使用 `sudo` 或更换安装目录 |

---

## 六、FAQ 反模式

### 6.1 常见坑与反模式对照

| 反模式 | 问题描述 | 正确做法 |
|--------|----------|----------|
| **盲目切换版本** | 用户直接执行版本切换，未验证项目兼容性 | 切换前先运行 `npm test` 验证兼容性 |
| **忽略 shell 差异** | 在 zsh 中使用 bash 的导出语法 | 先确认 `$SHELL`，再生成对应语法 |
| **依赖全局配置** | 期望 Skill 修改 `~/.bashrc` 来持久化环境变量 | 明确要求持久化时，提供追加命令供用户自行执行 |
| **跳过漂移检测** | 直接执行任务链，未检查环境一致性 | 先运行 `--check-drift`，确认无差异后再执行 |
| **敏感信息泄露** | 在报告中输出 `.env` 文件的实际值 | 默认只输出变量名，需用户显式要求才输出值 |

### 6.2 进阶使用建议

- **自定义任务链**：在项目根目录创建 `.dev-env-tasks.json`，定义多步骤流水线：

```json
{
  "tasks": [
    {"name": "lint", "command": "npm run lint"},
    {"name": "test", "command": "npm run test"},
    {"name": "build", "command": "npm run build"}
  ],
  "stop_on_error": true
}
```

- **定期审计**：将 `dev-env-manager --check-drift` 加入 CI 流水线，作为构建前检查项。

---

## 七、渐进式披露

### 7.1 新手路径（首次使用）

1. 阅读本文档的「能力边界速查卡」了解能做什么
2. 查看「触发方式」确认如何发起请求
3. 按「标准执行流程」的步骤 1-3 体验一次环境采集
4. 遇到问题查「错误码体系」

### 7.2 进阶路径（熟练使用）

1. 学习「任务链定义」语法，自定义多步骤流水线
2. 使用「配置漂移检测」功能，定期审计环境一致性
3. 参考「FAQ 反模式」避免常见陷阱
4. 结合 CI/CD 系统，将本 Skill 的输出作为构建前检查项

---

## 八、安装与验证

### 8.1 安装步骤

1. 将本 Skill 文件放置到 AI 助手的技能目录中
2. 确保项目根目录存在 `bin/` 目录（或创建软链接至 `/usr/local/bin/`）
3. 执行 `dev-env-manager --version` 验证安装是否成功

### 8.2 自检命令

| 命令 | 预期输出 |
|------|----------|
| `dev-env-manager --version` | `dev-env-manager v1.0.0` |
| `dev-env-manager --selftest` | 输出环境检测结果，无错误码 |

---

## 用户协议

<!-- user-agreement-injected -->

**使用前请仔细阅读以下条款，使用本 Skill 即视为同意本协议：**

1. **责任承担**：使用者自行承担因使用本 Skill 产生的全部责任，包括但不限于环境配置错误、数据丢失、任务执行失败等后果。
2. **禁止反向工程**：不得对本 Skill 的底层逻辑进行反向工程、反编译或试图提取源代码。
3. **合规使用**：使用者应确保使用场景符合当地法律法规及所在组织的安全规范。
4. **无担保声明**：本 Skill 按"现状"提供，不附带任何明示或暗示的担保。

---

## 许可证（License）

<!-- professional-license-embedded -->

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
