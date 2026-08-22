---
slug: agent-ready-repo
name: agent-ready-repo
displayName: 软件交付 智能编排 质量门禁
description: 从想法到生产的软件交付全流程智能编排与质量门禁。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: FlowForge Studio
agent_created: true
trigger_words: ["agent-ready-repo", "软件交付", "AI驱动开发", "智能编排", "项目初始化", "交付流水线", "质量门禁", "发布编排"]
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# agent-ready-repo — 软件交付全流程智能编排与质量门禁

## 1. 能力边界速查卡（一页纸）

### 1.1 本 Skill 能做什么

| 能力模块 | 具体动作 | 产出物 |
|---------|---------|--------|
| **build** | 读取依赖清单 → 安装依赖 → 执行编译 → 记录产物路径 | 构建产物路径清单 |
| **test** | 自动探测测试框架（Jest/Pytest/Go test 等）→ 运行测试 → 汇总结果 | 测试报告摘要 |
| **quality** | 依次执行代码规范检查、静态分析、安全扫描、覆盖率校验 | 质量门禁报告 |
| **deploy** | 仅当 `delivery_goal=production` 时执行部署脚本 → 记录版本号与回滚点 | 部署记录与回滚信息 |

### 1.2 本 Skill 不能做什么

- 不能代替人工进行业务需求分析
- 不能修复代码中的业务逻辑错误
- 不能保证部署后服务 100% 可用
- 不能处理未在依赖清单中声明的隐式依赖
- 不能绕过目标环境的安全策略

### 1.3 适用对象

- 需要从零搭建项目并完成交付的开发者
- 需要标准化交付流程的团队
- 希望将 AI 能力嵌入软件交付管线的工程师

---

## 2. 触发方式与场景映射

### 2.1 触发词

直接使用以下任一触发词即可激活本 Skill：

- `agent-ready-repo`
- `软件交付`
- `AI驱动开发`
- `智能编排`
- `项目初始化`
- `交付流水线`
- `质量门禁`
- `发布编排`

### 2.2 场景映射表

| 你的实际需求（大白话） | 触发方式 | 建议参数 |
|----------------------|---------|---------|
| "帮我把这个项目跑起来，装依赖、编译一下" | `agent-ready-repo build` | 无特殊参数 |
| "我想跑一下测试看看有没有挂" | `agent-ready-repo test` | 无特殊参数 |
| "上线前帮我检查代码质量" | `agent-ready-repo quality` | 无特殊参数 |
| "我要发布到生产环境" | `agent-ready-repo deploy` | `delivery_goal=production` |
| "完整走一遍：构建→测试→质量→部署" | `agent-ready-repo` | `delivery_goal=production` |
| "只做构建和测试，不部署" | `agent-ready-repo` | `delivery_goal=staging` 或 `skip_modules=deploy` |

---

## 3. 标准执行流程

### 3.1 前置条件

| 条件项 | 要求 | 检查方式 |
|--------|------|---------|
| 项目目录 | 存在且包含源码 | `ls` 确认 |
| 依赖清单 | 存在 `package.json` / `requirements.txt` / `go.mod` 等 | 文件存在性检查 |
| 网络连接 | 可访问依赖仓库 | `ping registry.npmjs.org` 或等效 |
| 部署脚本（仅 deploy 需要） | 存在 `deploy.sh` 或等效脚本 | 文件存在性检查 |

### 3.2 执行步骤

#### 步骤 1：初始化上下文

```bash
agent-ready-repo --init
```

- 扫描当前目录，识别项目类型（Node/Python/Go/Java 等）
- 读取依赖清单文件，确认依赖列表
- 输出项目概览：类型、依赖数量、预估构建时间

#### 步骤 2：执行构建（build）

```bash
agent-ready-repo build
```

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--install` | `true` | 是否安装依赖 |
| `--skip_modules` | 空 | 跳过指定模块（逗号分隔） |

构建完成后输出：

```json
{
  "status": "success",
  "artifact_path": "/path/to/dist/",
  "build_time_seconds": 45
}
```

#### 步骤 3：执行测试（test）

```bash
agent-ready-repo test
```

自动探测测试框架：

| 框架 | 探测依据 | 执行命令 |
|------|---------|---------|
| Jest | `jest.config.js` 存在 | `npx jest --ci` |
| Pytest | `pytest.ini` 或 `tests/` 目录 | `python -m pytest` |
| Go test | `go.mod` 存在 | `go test ./...` |

输出测试汇总：

```json
{
  "total": 128,
  "passed": 125,
  "failed": 3,
  "skipped": 0,
  "duration_seconds": 12
}
```

#### 步骤 4：执行质量检查（quality）

```bash
agent-ready-repo quality
```

依次执行以下检查：

1. **代码规范**：ESLint / Ruff / golangci-lint
2. **静态分析**：SonarQube / CodeQL / 等效工具
3. **安全扫描**：npm audit / pip-audit / govulncheck
4. **覆盖率校验**：阈值默认 80%，可通过 `--coverage_threshold` 调整

质量门禁判定规则：

| 检查项 | 通过标准 | 失败处理 |
|--------|---------|---------|
| 代码规范 | 0 error | 输出违规列表，中止流程 |
| 静态分析 | 0 critical | 输出告警列表，中止流程 |
| 安全扫描 | 0 high/critical | 输出漏洞列表，中止流程 |
| 覆盖率 | ≥ 阈值 | 低于阈值则警告，不中止 |

#### 步骤 5：执行部署（deploy，可选）

```bash
agent-ready-repo deploy --delivery_goal=production
```

**仅当 `delivery_goal=production` 时执行此步骤。**

部署流程：

1. 确认部署脚本存在（`deploy.sh` 或 `deploy.py`）
2. 执行部署脚本
3. 记录版本号（从 `VERSION` 文件或 git tag 读取）
4. 记录回滚点（当前 commit hash + 构建产物路径）

输出：

```json
{
  "deployed_version": "v1.2.3",
  "rollback_point": "a1b2c3d4e5f6",
  "deploy_time": "2024-01-15T10:30:00Z"
}
```

### 3.3 输出规范

所有模块执行完毕后，输出统一格式的交付摘要：

```json
{
  "project": "my-app",
  "build": {"status": "success", "artifact": "/path/to/dist/"},
  "test": {"passed": 125, "failed": 3, "total": 128},
  "quality": {"gate": "failed", "reason": "3 test failures"},
  "deploy": {"executed": false, "reason": "delivery_goal=staging"},
  "next_steps": ["修复 3 个失败测试", "重新运行 test 模块"]
}
```

---

## 4. 置信度门控机制

### 4.1 占位符规则

当执行过程中遇到信息不足的情况，**不得编造数据**，必须输出占位符：

| 场景 | 占位符格式 | 示例 |
|------|-----------|------|
| 依赖版本未知 | `[需核实:依赖版本]` | `[需核实:lodash版本]` |
| 部署目标环境未知 | `[需核实:部署环境]` | `[需核实:部署环境]` |
| 测试框架无法识别 | `[需核实:测试框架]` | `[需核实:测试框架]` |
| 覆盖率阈值未指定 | `[需核实:覆盖率阈值]` | `[需核实:覆盖率阈值]` |

### 4.2 门控触发条件

以下情况触发置信度门控，流程暂停并提示用户补充信息：

1. 依赖清单文件缺失或无法解析
2. 测试框架无法自动识别
3. 部署脚本不存在但 `delivery_goal=production`
4. 关键参数（如 `coverage_threshold`）未指定且无默认值

### 4.3 门控处理流程

```
检测到信息不足
    ↓
输出 [需核实:字段] 占位符
    ↓
列出缺失信息清单
    ↓
暂停当前模块，等待用户补充
    ↓
用户补充后继续执行
```

---

## 5. 错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|---------|---------|
| `E001` | 依赖清单缺失 | "未找到 package.json / requirements.txt / go.mod，无法识别项目类型" | 确认项目根目录，或手动指定 `--project_type` |
| `E002` | 依赖安装失败 | "依赖安装失败，请检查网络连接或镜像源配置" | 检查网络 → 配置镜像 → 重试 |
| `E003` | 编译失败 | "编译错误，详见构建日志" | 查看日志 → 修复代码 → 重新执行 build |
| `E004` | 测试框架无法识别 | "无法自动识别测试框架，请手动指定" | 使用 `--test_framework=jest|pytest|go` 指定 |
| `E005` | 质量门禁未通过 | "质量检查未通过：3 个高危漏洞" | 根据报告修复问题 → 重新执行 quality |
| `E006` | 部署脚本缺失 | "delivery_goal=production 但未找到部署脚本" | 创建 deploy.sh 或修改 delivery_goal |
| `E007` | 参数冲突 | "skip_modules 与 delivery_goal 参数冲突" | 检查参数组合，移除冲突项 |
| `E008` | 权限不足 | "当前用户无权限执行部署操作" | 联系管理员授权，或使用 sudo（谨慎） |

---

## 6. FAQ 与反模式对照

### 6.1 常见坑

| 坑 | 表现 | 正确做法 |
|----|------|---------|
| 跳过质量检查 | 直接部署，上线后出问题 | 始终执行 quality 模块，至少跑一次 |
| 忽略测试失败 | 测试挂了但继续部署 | 测试失败时中止流程，修复后再继续 |
| 手动修改产物 | 构建产物被手工改动，无法追溯 | 始终通过 build 模块生成产物 |
| 不记录回滚点 | 部署失败后无法回滚 | 每次部署必须记录 commit hash 和产物路径 |
| 参数组合混乱 | `skip_modules=test` 且 `delivery_goal=production` | 明确参数优先级，避免跳过关键模块 |

### 6.2 反模式对照表

| 反模式 | 问题 | 推荐替代 |
|--------|------|---------|
| 所有模块一把梭 | 构建失败时浪费大量时间 | 分步执行，先 build 再 test |
| 部署前不跑测试 | 生产环境出现低级错误 | 强制 test 通过后才允许 deploy |
| 质量门禁形同虚设 | 覆盖率阈值设 0% | 设置合理阈值（建议 ≥ 80%） |
| 忽略 next_steps | 交付后不知道下一步做什么 | 认真阅读输出中的 next_steps 并执行 |
| 手动指定测试框架 | 与实际项目不符导致误报 | 让 Skill 自动探测，必要时再手动指定 |

---

## 7. 渐进式披露：分层次阅读路径

### 7.1 新手路径（首次使用）

1. 阅读 **第 1 节** 能力边界速查卡，确认本 Skill 是否适合你的场景
2. 查看 **第 2 节** 触发方式，找到你的使用场景
3. 按 **第 3 节** 标准执行流程的步骤 1-2 完成基础操作
4. 遇到问题查阅 **第 5 节** 错误码体系

### 7.2 进阶路径（熟练用户）

1. 熟悉 **第 3 节** 全部步骤，理解参数组合效果（如 `skip_modules` 与 `delivery_goal` 的交互）
2. 掌握 **第 4 节** 置信度门控机制，正确处理占位符
3. 参考 **第 6 节** FAQ 与反模式对照，优化使用习惯
4. 结合输出中的 `next_steps` 建立完整交付闭环

---

## 8. 参数速查表

| 参数 | 类型 | 默认值 | 可选值 | 说明 |
|------|------|--------|--------|------|
| `delivery_goal` | string | `staging` | `staging` / `production` | 交付目标，`production` 时触发部署 |
| `skip_modules` | string | 空 | 逗号分隔模块名 | 跳过的模块，如 `test,quality` |
| `coverage_threshold` | number | `80` | 0-100 | 覆盖率阈值 |
| `test_framework` | string | 自动探测 | `jest` / `pytest` / `go` | 手动指定测试框架 |
| `project_type` | string | 自动识别 | `node` / `python` / `go` / `java` | 手动指定项目类型 |
| `install` | boolean | `true` | `true` / `false` | 是否安装依赖 |

### 参数组合示例

| 组合 | 效果 |
|------|------|
| `delivery_goal=production skip_modules=quality` | 部署但跳过质量检查（不推荐） |
| `delivery_goal=staging skip_modules=deploy` | 只做构建、测试、质量，不部署 |
| `coverage_threshold=90 test_framework=pytest` | 指定覆盖率阈值 90% 且使用 pytest |

---

## 9. 用户协议

<!-- user-agreement-injected -->

**使用本 Skill 即表示您同意以下条款：**

1. **责任承担**：使用者应自行承担因使用本 Skill 产生的全部责任。本 Skill 提供的输出和建议仅供参考，不构成任何形式的保证或承诺。

2. **禁止反向工程**：未经授权，不得对本 Skill 的底层逻辑进行反向工程、反编译或试图提取源代码。

3. **合规使用**：使用者应确保使用场景符合当地法律法规及所在组织的政策要求。本 Skill 不承担因违规使用产生的任何法律责任。

4. **内容变更**：本 Skill 可能随版本更新调整行为，使用者应关注版本变更说明。持续使用视为接受更新后的条款。

---

## 10. 许可证（License）

<!-- professional-license-embedded -->

### MIT License

Copyright (c) 2024 FlowForge Studio

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

## 11. 版本记录

| 版本 | 日期 | 变更说明 |
|------|------|---------|
| 1.0.0 | 2024-01-15 | 初始版本，包含 build/test/quality/deploy 四大模块 |

---

*本 Skill 由 AI 辅助生成，仅供参考。使用前请阅读相关文档。*
