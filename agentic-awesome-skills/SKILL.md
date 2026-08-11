---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: agentic-awesome-skills
name: AI智能体技能运行器
displayName: 技能调度 仓库拉取 镜像加速
description: 拉取并运行 GitHub 技能仓库，自动处理依赖与镜像，返回结构化执行结果。
version: 1.0.44
rules_version: cpr-20260811-n351
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/agentic-awesome-skills
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 技能工坊·林默
agent_created: true
trigger_words: ["agentic-awesome-skills", "技能运行", "技能拉取", "技能执行", "仓库运行", "技能调度"]
---

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->


> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# AI智能体技能运行器（Skill Runner）

## 一、能力边界：一页纸速查卡

本 Skill 负责从 GitHub 拉取技能仓库、解析依赖、执行技能逻辑，并返回结构化的执行结果。它不是一个技能创作工具，也不负责技能内容的正确性。

| 能力维度 | 支持 | 不支持 |
|---------|------|--------|
| 拉取公开 GitHub 仓库 | ✅ 支持 HTTPS 与 SSH 协议 | ❌ 不支持私有仓库（需 Token 注入） |
| 自动安装依赖 | ✅ 支持 requirements.txt / package.json / go.mod | ❌ 不支持 Conda 环境切换 |
| 镜像加速 | ✅ 支持 ghproxy / gh-proxy 等公共镜像 | ❌ 不支持自定义镜像源配置 |
| 执行技能主逻辑 | ✅ 支持 Python / Node.js / Shell 三种运行时 | ❌ 不支持 Docker 容器化执行 |
| 返回结构化结果 | ✅ 输出 JSON 格式（含 stdout / stderr / exit_code） | ❌ 不支持流式输出 |
| 自检与版本查询 | ✅ 支持 `--selftest` 与 `--version` | ❌ 不支持交互式调试模式 |

**适用对象**：需要批量运行多个技能仓库的 AI Agent 开发者、自动化流水线维护者、技能市场运营人员。

**不适用对象**：需要可视化界面操作的非技术用户、需要实时日志追踪的调试场景。

---

## 二、触发方式：场景映射表

当用户输入以下意图时，本 Skill 将被激活：

| 用户原话（大白话） | 触发词命中 | 实际执行动作 |
|-------------------|-----------|-------------|
| "帮我跑一下那个技能仓库" | 技能运行 | 拉取仓库 → 解析依赖 → 执行主逻辑 |
| "把 GitHub 上的技能拉下来用" | 技能拉取 | 仅拉取仓库并输出路径，不执行 |
| "运行 agentic-awesome-skills 自检" | agentic-awesome-skills | 执行 `--selftest` 内置自检流程 |
| "这个技能怎么跑不起来" | 技能执行 | 进入错误诊断模式，输出修正步骤 |
| "查一下版本" | --version | 输出当前 Skill 版本号 |

**触发优先级**：显式命令行参数（`--selftest` / `--version`） > 仓库 URL 输入 > 模糊意图匹配。

---

## 三、标准流程：从输入到输出

### 3.1 前置条件

| 条件项 | 要求 | 校验方式 |
|--------|------|---------|
| 网络连通性 | 可访问 github.com 或镜像站 | `curl -I https://github.com` 返回 200 |
| 运行时环境 | Python ≥ 3.8 / Node ≥ 14 / Bash ≥ 4.0 | `python3 --version` 等命令检查 |
| 磁盘空间 | 至少 500MB 可用空间 | `df -h` 检查 |
| 输入格式 | 合法的 GitHub 仓库 URL 或 `owner/repo` 格式 | 正则匹配 `^[A-Za-z0-9-]+/[A-Za-z0-9-]+$` |

### 3.2 执行步骤

**Step 1：输入收集与格式确认**

接收用户输入，执行格式校验：

```
输入示例：
- https://github.com/owner/repo
- owner/repo
- git@github.com:owner/repo.git
```

校验规则：
- URL 必须包含 `github.com` 域名
- `owner/repo` 格式必须符合正则 `^[A-Za-z0-9-]+/[A-Za-z0-9-]+$`
- 不支持 GitLab / Bitbucket 等其他平台

**Step 2：仓库拉取**

```bash
# 优先使用镜像加速
git clone https://ghproxy.com/https://github.com/owner/repo.git /tmp/skills/repo
# 镜像失败则直连
git clone https://github.com/owner/repo.git /tmp/skills/repo
```

镜像选择顺序：`ghproxy.com` → `gh-proxy.com` → 直连。每个镜像超时 30 秒。

**Step 3：依赖解析与安装**

检测仓库根目录下的依赖清单文件：

| 文件 | 运行时 | 安装命令 |
|------|--------|---------|
| requirements.txt | Python | `pip install -r requirements.txt` |
| package.json | Node.js | `npm install` |
| go.mod | Go | `go mod download` |

若同时存在多个依赖文件，按 Python → Node → Go 顺序依次安装。安装失败不中断流程，记录错误后继续。

**Step 4：主逻辑执行**

查找执行入口，优先级：
1. `main.py`
2. `index.js`
3. `run.sh`
4. `skill.json` 中声明的 `entry` 字段

执行命令：`python3 main.py` / `node index.js` / `bash run.sh`

**Step 5：结果收集与校验**

捕获 stdout、stderr 和退出码，校验输出完整性：

```json
{
  "status": "success",
  "exit_code": 0,
  "stdout": "...",
  "stderr": "",
  "output_files": ["/tmp/skills/repo/output.json"],
  "execution_time_ms": 1234
}
```

完整性校验规则：
- stdout 非空（除非技能设计为静默执行）
- 退出码为 0 或技能文档中声明的预期非零值
- 若声明了输出文件，必须实际存在

### 3.3 输出规范

所有输出统一为 JSON 格式，包含以下字段：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| status | string | ✅ | `success` / `partial_success` / `failed` |
| exit_code | int | ✅ | 进程退出码 |
| stdout | string | ✅ | 标准输出内容 |
| stderr | string | ✅ | 错误输出内容 |
| output_files | array | ❌ | 生成的输出文件路径列表 |
| execution_time_ms | int | ✅ | 总执行耗时（毫秒） |
| error_code | string | ❌ | 失败时的错误码（见第五节） |

---

## 四、置信度门控

当遇到以下信息不足的情况，本 Skill 不会编造数据，而是输出占位符：

| 场景 | 输出占位符 | 后续处理 |
|------|-----------|---------|
| 仓库未声明依赖清单 | `[需核实:依赖声明文件]` | 跳过依赖安装，直接执行主逻辑 |
| 主逻辑入口不明确 | `[需核实:执行入口]` | 尝试常见入口，全部失败则报错 |
| 输出文件路径未声明 | `[需核实:输出路径]` | 仅返回 stdout 内容 |
| 技能版本号未知 | `[需核实:技能版本]` | 在结果中标记 `version: "unknown"` |

**门控原则**：宁可返回不完整结果，绝不虚构执行数据。

---

## 五、错误码体系

| 错误码 | 含义 | 用户提示话术 | 修正步骤 |
|--------|------|-------------|---------|
| `E001` | 输入格式不合法 | "输入格式有误，请使用 `owner/repo` 或完整 GitHub URL" | 重新输入，参考 3.2 节格式示例 |
| `E002` | 仓库拉取失败 | "无法拉取仓库，请检查网络或仓库是否存在" | 1. 确认仓库公开 2. 尝试更换镜像 3. 检查网络代理 |
| `E003` | 依赖安装失败 | "依赖安装失败，请查看 stderr 中的具体错误" | 1. 手动安装缺失依赖 2. 检查 Python/Node 版本兼容性 |
| `E004` | 主逻辑执行失败 | "技能执行报错，退出码非零" | 1. 查看 stderr 定位错误 2. 检查输入参数 3. 联系技能作者 |
| `E005` | 输出校验失败 | "执行完成但输出不完整" | 1. 检查技能文档确认预期输出 2. 查看 output_files 是否生成 |
| `E006` | 运行时环境不满足 | "当前环境缺少必要运行时" | 安装对应运行时（Python/Node/Go）后重试 |
| `E007` | 超时 | "执行超过 300 秒，已强制终止" | 1. 确认技能是否设计为长时运行 2. 调整超时阈值 |

---

## 六、FAQ 反模式对照

| 常见坑 | 反模式（错误做法） | 正模式（正确做法） |
|--------|-------------------|-------------------|
| 依赖冲突 | 直接 `pip install` 覆盖全局环境 | 使用虚拟环境（venv）隔离依赖 |
| 镜像失效 | 只配置一个镜像源 | 配置镜像列表，按顺序自动切换 |
| 入口文件缺失 | 报错后直接放弃 | 检查 `skill.json` 声明，或扫描目录下可执行文件 |
| 输出编码问题 | 忽略编码直接拼接字符串 | 统一使用 UTF-8 编码，捕获时指定 `encoding='utf-8'` |
| 仓库更新 | 每次拉取全量 clone | 使用 `--depth 1` 浅克隆，加速拉取 |

---

## 七、渐进式披露：分层次阅读路径

### 速查卡（30 秒上手）

```
输入: owner/repo
→ 拉取 → 装依赖 → 执行 → 输出 JSON
```

### 新手路径（5 分钟掌握）

1. 阅读「能力边界」了解支持范围
2. 按「标准流程」的 Step 1-3 操作
3. 遇到问题查「错误码体系」

### 进阶路径（深入定制）

1. 修改镜像列表：编辑 `config/mirrors.json`
2. 自定义超时：设置环境变量 `SKILL_RUNNER_TIMEOUT=600`
3. 扩展运行时：在 `runtimes/` 目录添加新的运行时适配器
4. 集成 CI/CD：调用 CLI 接口，解析 JSON 输出

---

## 八、CLI 接口参考

```
agentic-awesome-skills [options] [repo]

Options:
  --selftest    运行内置自检流程，验证环境配置
  --version     输出版本号
  --timeout N   设置执行超时（秒），默认 300
  --mirror URL  指定镜像地址，覆盖默认配置
  --no-deps     跳过依赖安装步骤
  --output PATH 指定输出文件路径

Examples:
  agentic-awesome-skills owner/repo
  agentic-awesome-skills --selftest
  agentic-awesome-skills --version
  agentic-awesome-skills --no-deps --timeout 600 owner/repo
```

---

## 九、用户协议

使用本 Skill 即表示您同意以下条款：

1. **责任承担**：使用者自行承担全部责任。本 Skill 仅提供技能拉取与执行的自动化能力，不对技能内容本身的质量、安全性、合法性负责。因使用本 Skill 或其所拉取的技能仓库导致的任何直接或间接损失，均由使用者自行承担。

2. **禁止反向工程**：使用者不得对本 Skill 的源代码进行反向工程、反编译、破解或试图提取其底层算法逻辑，除非适用法律明确允许。

3. **合规使用**：使用者应确保所拉取和运行的技能仓库符合当地法律法规及 GitHub 服务条款，不得用于任何非法目的。

4. **免责声明**：本 Skill 按"现状"提供，不附带任何明示或暗示的保证，包括但不限于适销性、特定用途适用性和非侵权保证。

<!-- user-agreement-injected -->

---

## 十、许可证（License）

本 Skill 采用 MIT 许可证发布。

```
MIT License

Copyright (c) 2026 技能工坊·林默

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

*本 Skill 由 AI 辅助生成，仅供参考。使用前请阅读相关文档。*
