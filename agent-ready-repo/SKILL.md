---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: agent-ready-repo
name: agent-ready-repo
displayName: 交付编排 质量门禁 项目初始化
description: 从想法到生产的软件交付全流程智能编排与质量门禁。
version: 1.0.3
rules_version: cpr-20260812-n376
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/agent-ready-repo
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: FlowForge Studio
agent_created: true
trigger_words: ["agent-ready-repo", "软件交付", "AI驱动开发", "智能编排", "项目初始化", "交付流水线", "质量门禁", "工程化启动"]
---

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->


> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# agent-ready-repo — 交付编排与质量门禁 Skill

## 一、能力边界速查卡（一页纸）

### 1.1 本 Skill 能做什么

| 能力项 | 具体说明 | 输出物 |
|--------|----------|--------|
| 项目骨架生成 | 根据输入参数（项目名、技术栈、目标）生成标准目录结构与基础配置文件 | 目录树 + 配置文件清单 |
| 流水线编排 | 生成 CI/CD 流水线定义（构建、测试、部署阶段） | 流水线 YAML/JSON 定义 |
| 质量门禁检查 | 对代码库执行规范、安全、测试覆盖三个维度的静态检查 | 门禁报告（JSON/Markdown） |
| 结果报告输出 | 结构化输出检查结果、问题清单、修复建议 | 报告文件 + 控制台输出 |

### 1.2 本 Skill 不能做什么

| 限制项 | 说明 |
|--------|------|
| 业务需求分析 | 不替代人工进行需求调研、业务建模、用户故事拆分 |
| 代码缺陷自动修复 | 仅标记问题点，不自动改写代码逻辑 |
| 生产环境保障 | 不承诺交付后零故障，不负责运行时监控 |
| 个性化场景处理 | 仅覆盖预设流程模板，未定义场景需人工介入 |
| 外部系统访问 | 不访问私有仓库、内部 CI 系统或企业内网资源 |

### 1.3 适用对象

- **适用**：需要快速搭建项目骨架的开发者、需要标准化交付流程的团队、希望引入质量门禁的工程负责人。
- **不适用**：已有成熟定制化流水线的团队、需要深度业务分析的场景、对安全合规有特殊行业要求的项目。

---

## 二、触发方式与场景映射

### 2.1 触发词

使用以下任一关键词即可激活本 Skill：

- `agent-ready-repo`
- `软件交付`
- `AI驱动开发`
- `智能编排`
- `项目初始化`
- `交付流水线`
- `质量门禁`

### 2.2 场景映射表（大白话版）

| 你说的话（场景） | 本 Skill 会做什么 | 你需要准备什么 |
|------------------|-------------------|----------------|
| "帮我初始化一个 Python 项目" | 生成标准目录结构、pyproject.toml、基础测试框架 | 项目名称、Python 版本偏好 |
| "我要搭一条 CI 流水线" | 生成 GitHub Actions / GitLab CI 的 YAML 定义 | 目标平台、构建命令 |
| "检查一下我的代码质量" | 执行规范检查（lint）、依赖安全检查、测试覆盖率统计 | 代码仓库路径、测试命令 |
| "准备上线，帮我过一遍门禁" | 运行完整质量门禁流程，输出通过/不通过结论 | 已配置的测试套件 |

---

## 三、标准执行流程

### 3.1 前置条件

| 条件 | 说明 | 检查方式 |
|------|------|----------|
| 输入参数完整 | 至少提供项目名称与目标技术栈 | 参数校验 |
| 代码仓库可访问 | 本地路径存在且包含有效代码（质量检查场景） | 路径存在性检查 |
| 测试命令可执行 | 项目已配置测试脚本（门禁场景） | 命令 dry-run |

### 3.2 执行步骤

#### 步骤 1：解析输入参数

接收以下参数（均可选，但至少提供 `project_name`）：

| 参数名 | 类型 | 必填 | 默认值 | 说明 |
|--------|------|------|--------|------|
| `project_name` | string | 是 | 无 | 项目名称，用于命名空间与目录生成 |
| `tech_stack` | string | 否 | `python` | 技术栈：`python` / `node` / `go` / `java` |
| `delivery_goal` | string | 否 | `standard` | 交付目标：`standard` / `production` / `prototype` |
| `ci_platform` | string | 否 | `github` | CI 平台：`github` / `gitlab` / `jenkins` |
| `quality_gates` | array | 否 | `["lint","security","test"]` | 启用的质量门禁维度 |

#### 步骤 2：生成项目骨架

根据 `tech_stack` 生成对应目录结构。以 Python 为例：

```
{project_name}/
├── src/
│   └── {project_name}/
│       ├── __init__.py
│       └── main.py
├── tests/
│   ├── __init__.py
│   └── test_main.py
├── docs/
│   └── README.md
├── pyproject.toml
├── .gitignore
└── .pre-commit-config.yaml
```

#### 步骤 3：生成流水线配置

根据 `ci_platform` 生成流水线定义。核心阶段：

1. **build** — 依赖安装与编译
2. **test** — 单元测试执行
3. **quality** — 质量门禁检查（lint + security + coverage）
4. **deploy** — 部署（仅 `delivery_goal=production` 时启用）

#### 步骤 4：执行质量门禁

按 `quality_gates` 配置依次执行：

| 门禁维度 | 检查工具 | 通过标准 |
|----------|----------|----------|
| lint | ruff / eslint | 0 error，warning ≤ 5 |
| security | pip-audit / npm audit | 0 高危漏洞 |
| test | pytest / jest | 覆盖率 ≥ 80% |

#### 步骤 5：输出报告

默认输出 JSON 到标准输出，使用 `--report` 参数输出 Markdown 报告。

**JSON 输出示例：**

```json
{
  "project_name": "demo",
  "gates": {
    "lint": {"passed": true, "errors": 0, "warnings": 2},
    "security": {"passed": true, "vulnerabilities": 0},
    "test": {"passed": false, "coverage": 72.5, "threshold": 80}
  },
  "overall": "failed",
  "next_steps": ["提升测试覆盖率至 80%", "修复 2 个 lint warning"]
}
```

### 3.3 输出规范

| 输出类型 | 格式 | 适用场景 |
|----------|------|----------|
| 标准输出 | JSON（结构化） | 程序化消费 |
| 报告文件 | Markdown | 人工阅读 |
| 控制台 | 彩色文本摘要 | 快速查看 |

---

## 四、置信度门控机制

当输入信息不足以生成可靠输出时，本 Skill 会使用 `[需核实:字段名]` 占位符，**不会编造数据**。

### 4.1 触发条件

| 场景 | 占位示例 |
|------|----------|
| 未提供技术栈 | `[需核实:tech_stack]` |
| 未提供测试命令 | `[需核实:test_command]` |
| 代码仓库路径不存在 | `[需核实:repo_path]` |

### 4.2 处理规则

1. 占位符出现时，对应功能模块输出标记为 `"confidence": "low"`。
2. 报告顶部显示警告：`部分字段因信息不足使用占位符，请补充后重试。`
3. 占位符字段不参与质量门禁评分。

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| `E1001` | 缺少必填参数 | "请提供项目名称（project_name）" | 补充参数后重试 |
| `E1002` | 不支持的平台 | "当前仅支持 github/gitlab/jenkins" | 更换平台参数 |
| `E2001` | 仓库路径不存在 | "无法访问指定路径，请检查路径是否正确" | 确认路径存在 |
| `E2002` | 测试命令执行失败 | "测试命令返回非零退出码，请先本地验证" | 本地运行测试 |
| `E3001` | 门禁配置冲突 | "quality_gates 包含未知维度" | 检查维度名称 |
| `E4001` | 输出目录不可写 | "无法写入报告文件，请检查权限" | 调整目录权限 |

---

## 六、FAQ 与反模式对照

### 6.1 常见坑

| # | 坑描述 | 反模式（错误做法） | 正确做法 |
|---|--------|---------------------|----------|
| 1 | 忽略前置条件 | 直接运行质量检查但仓库为空 | 先确认代码已提交且可构建 |
| 2 | 参数拼写错误 | 使用 `tech-stack` 而非 `tech_stack` | 严格使用下划线命名 |
| 3 | 依赖未安装 | 跳过步骤 3 直接跑门禁 | 先执行依赖安装 |
| 4 | 覆盖率阈值不合理 | 对小型项目要求 95% 覆盖率 | 根据项目规模设置 60-80% |
| 5 | 忽略 next_steps | 只看通过/不通过，不处理建议 | 按 next_steps 逐项闭环 |

### 6.2 反模式对照表

| 反模式 | 问题 | 替代方案 |
|--------|------|----------|
| 把本 Skill 当代码生成器 | 期望自动生成完整业务逻辑 | 只生成骨架与配置，业务代码需人工编写 |
| 把门禁结果当最终结论 | 忽略人工 review 环节 | 门禁是辅助，人工审查不可替代 |
| 一次配置永久使用 | 技术栈升级后流水线失效 | 定期更新配置与依赖版本 |

---

## 七、渐进式披露路径

### 7.1 新手快速上手（5 分钟）

1. 阅读「能力边界速查卡」确认适用范围。
2. 查看「触发方式与场景映射」找到你的场景。
3. 按「标准执行流程」步骤 1-2 完成基础操作。
4. 遇到问题查阅「错误码体系」。

### 7.2 进阶用户（完整掌握）

1. 熟悉「标准执行流程」全部步骤，理解参数组合效果。
2. 掌握「置信度门控机制」，正确处理占位符。
3. 参考「FAQ 与反模式对照」优化使用习惯。
4. 结合输出中的 `next_steps` 建立完整交付闭环。

### 7.3 专家级（自定义扩展）

- 修改流程模板：编辑 Skill 内置的模板目录，添加自定义阶段。
- 扩展质量门禁：在 `quality_gates` 中注册自定义检查脚本。
- 集成外部工具：通过 `--hook` 参数在流水线各阶段注入自定义命令。

---

## 八、参数速查表

| 参数 | 可选值 | 默认值 | 说明 |
|------|--------|--------|------|
| `--selftest` | — | — | 运行自检，验证 Skill 环境 |
| `--version` | — | — | 显示版本号 |
| `--report` | — | — | 输出 Markdown 报告 |
| `--project_name` | string | 必填 | 项目名称 |
| `--tech_stack` | python/node/go/java | python | 技术栈 |
| `--delivery_goal` | standard/production/prototype | standard | 交付目标 |
| `--ci_platform` | github/gitlab/jenkins | github | CI 平台 |
| `--quality_gates` | lint/security/test | 全部 | 门禁维度 |

---

## 九、用户协议

<!-- user-agreement-injected -->

**使用本 Skill 即表示您同意以下条款：**

1. **责任承担**：使用者应自行承担因使用本 Skill 产生的全部责任。本 Skill 提供的输出仅为建议性内容，不构成任何形式的保证或承诺。任何基于本 Skill 输出所做的决策，其后果由使用者自行承担。

2. **禁止反向工程**：未经授权，不得对本 Skill 的底层逻辑、流程模板、评分算法进行反向工程、反编译或提取核心代码。本 Skill 的知识产权归原作者所有。

3. **合规使用**：使用者应确保使用场景符合当地法律法规及所在组织的政策要求。本 Skill 不承担因违规使用产生的任何法律责任。

4. **内容变更**：本 Skill 可能随版本更新调整行为，使用者应关注版本变更说明。持续使用视为接受更新后的条款。

---

## 十、许可证（License）

<!-- professional-license-embedded -->

### MIT License

Copyright (c) 2026 原创作者（自持版权）

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
