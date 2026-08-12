---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: agent-toolkit
name: agent-toolkit
displayName: 智能体技能编排 指令扩展 工作流管理
description: 为AI编码智能体提供结构化技能指令与脚本扩展能力。
version: 2.0.5
rules_version: cpr-20260812-n376
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/agent-toolkit
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: LingFlow Studio
agent_created: true
trigger_words: ["agent-toolkit", "技能包", "技能编排", "skill collection", "技能管理", "技能调度", "指令扩展", "工作流编排"]

---

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->


> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# agent-toolkit 技能编排与指令扩展手册

## 一、能力边界速查卡

### 1.1 能做什么

| 能力项 | 说明 | 输出物 |
|--------|------|--------|
| 技能清单扫描 | 扫描本地技能注册表，列出全部可用技能及其元数据 | 结构化清单（名称/版本/状态/依赖） |
| 技能编排执行 | 按用户指定顺序加载多个技能，生成可执行的编排计划 | 执行计划文件（YAML/JSON） |
| 技能状态管理 | 启用或停用指定技能，修改注册表中的状态字段 | 更新后的注册表状态 |
| 环境自检诊断 | 检查运行环境配置、依赖完整性、路径有效性 | 诊断报告（通过/警告/失败） |
| 版本信息查询 | 读取当前工具包版本元数据 | 版本号及构建信息 |

### 1.2 不能做什么

- 不能自动编写或修改技能内部的业务逻辑代码
- 不能跨进程调用其他 AI 智能体的私有技能库
- 不能保证编排后的技能组合一定产生正确结果（依赖用户输入质量）
- 不能替代 CI/CD 流水线中的测试与发布环节
- 不提供图形化界面，仅支持命令行交互

### 1.3 适用对象

- 使用 AI 编码智能体（如 Cursor、Copilot 类工具）的开发者
- 需要将多个技能串联成自动化流程的运维工程师
- 希望将技能包集成到现有工程流水线的技术负责人

---

## 二、触发方式与场景映射

### 2.1 触发词表

| 触发词 | 同义场景词 | 典型用户表述 |
|--------|------------|--------------|
| agent-toolkit | 技能工具包 | “用 agent-toolkit 看看有什么技能” |
| 技能包 | 技能集合 / 指令包 | “帮我加载技能包里的代码审查技能” |
| 技能编排 | 技能串联 / 流程组合 | “把格式化、lint、测试三个技能按顺序跑一遍” |
| skill collection | 技能库 / 技能仓库 | “list all skills in the collection” |
| 技能管理 | 技能启停 / 技能配置 | “停用那个过时的部署技能” |

### 2.2 场景映射表

| 用户场景 | 推荐命令 | 预期结果 |
|----------|----------|----------|
| 刚接触工具，想了解有哪些可用技能 | `agent-toolkit 技能包` | 输出技能清单及简要说明 |
| 需要依次执行多个技能完成一个任务 | `agent-toolkit 技能编排 --order lint,test,deploy` | 生成编排计划并逐项执行 |
| 某个技能报错，想临时停用 | `agent-toolkit 技能管理 --disable skill-name` | 技能状态变为 disabled |
| 环境刚迁移，想确认工具是否可用 | `agent-toolkit --selftest` | 输出诊断报告 |
| 想知道当前版本是否支持某功能 | `agent-toolkit --version` | 输出版本号及功能特性列表 |

---

## 三、标准执行流程

### 3.1 前置条件

| 条件项 | 要求 | 验证方式 |
|--------|------|----------|
| 操作系统 | Linux/macOS/Windows（WSL 推荐） | `uname -a` 或 `ver` |
| Python 版本 | ≥ 3.8 | `python --version` |
| 技能注册表 | 位于 `~/.agent-toolkit/registry.json` | `ls ~/.agent-toolkit/` |
| 网络连接 | 无需联网（本地运行） | — |

### 3.2 执行步骤

#### 步骤 1：环境自检

```bash
agent-toolkit --selftest
```

**输出示例：**

```
[通过] Python 版本 3.10.12
[通过] 注册表文件存在
[通过] 依赖包完整
[警告] 技能目录 /opt/skills 不存在（将使用默认目录）
[失败] 无（全部检查项通过）
```

#### 步骤 2：查看技能清单

```bash
agent-toolkit 技能包
```

**输出示例：**

```
技能 ID           版本    状态      依赖
------------------------------------------
code-format      1.2.0   enabled   none
lint-check       2.0.1   enabled   code-format
unit-test        1.0.3   enabled   none
deploy-staging   0.9.0   disabled  unit-test
```

#### 步骤 3：选择技能查看详情

```bash
agent-toolkit 技能包 --detail lint-check
```

**输出示例：**

```
技能: lint-check
版本: 2.0.1
状态: enabled
依赖: code-format (>=1.0.0)
描述: 对 Python 代码执行 pylint 静态检查
参数:
  - path: 目标文件或目录路径（必填）
  - threshold: 评分阈值，默认 7.0
```

#### 步骤 4：执行单个技能

```bash
agent-toolkit 技能编排 --single lint-check --param path=./src --param threshold=8.0
```

#### 步骤 5：编排多个技能

```bash
agent-toolkit 技能编排 --order code-format,lint-check,unit-test --param path=./src
```

**执行计划生成逻辑：**

1. 解析 `--order` 参数，按逗号分隔得到技能序列
2. 检查每个技能的依赖是否满足（依赖技能必须已启用）
3. 若依赖缺失，自动插入依赖技能到序列前部
4. 生成执行计划并逐项执行，每步输出独立日志

### 3.3 输出规范

所有命令输出遵循以下格式：

```
[级别] 消息内容
```

级别包括：`通过`、`警告`、`失败`、`信息`、`错误`

编排执行完成后，输出汇总表：

```
技能 ID          状态    耗时    备注
------------------------------------------
code-format     成功    1.2s    —
lint-check      成功    3.4s    评分 8.3
unit-test       失败    0.8s    2 个用例未通过
```

---

## 四、置信度门控机制

当遇到以下情况时，工具不会编造信息，而是输出占位符：

| 场景 | 输出内容 |
|------|----------|
| 技能依赖版本未知 | `[需核实:依赖版本]` |
| 注册表路径未配置 | `[需核实:注册表路径]` |
| 技能参数默认值不确定 | `[需核实:参数默认值]` |
| 编排顺序存在循环依赖 | `[需核实:依赖关系]` 并终止执行 |

**示例：**

```bash
$ agent-toolkit 技能编排 --order skill-a,skill-b
[失败] skill-a 依赖 skill-c，但 skill-c 的版本信息为 [需核实:依赖版本]
```

此时工具会停止执行，提示用户手动确认依赖版本后再继续。

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| E001 | 注册表文件不存在 | “未找到技能注册表，请先运行 `agent-toolkit --init`” | 运行初始化命令创建注册表 |
| E002 | 技能 ID 不存在 | “技能 `xxx` 不在注册表中，使用 `agent-toolkit 技能包` 查看可用技能” | 检查技能 ID 拼写 |
| E003 | 依赖未满足 | “技能 `xxx` 依赖 `yyy`，但 `yyy` 未启用” | 先启用依赖技能 |
| E004 | 参数缺失 | “技能 `xxx` 需要参数 `path`，请通过 `--param path=...` 提供” | 补充必填参数 |
| E005 | 循环依赖 | “检测到技能依赖循环：a → b → a” | 修改注册表中的依赖声明 |
| E006 | 版本不兼容 | “技能 `xxx` 需要 Python ≥ 3.10，当前为 3.8” | 升级 Python 或更换技能版本 |
| E007 | 权限不足 | “无法写入注册表文件，请检查文件权限” | 使用 `chmod` 调整权限 |

---

## 六、FAQ 与反模式对照

### 6.1 常见坑

| 坑编号 | 常见错误做法 | 反模式示例 | 正确做法 |
|--------|--------------|------------|----------|
| P1 | 跳过自检直接编排 | 直接运行 `agent-toolkit 技能编排` 导致路径错误 | 先执行 `--selftest` 确认环境 |
| P2 | 忽略依赖顺序 | 手动指定顺序时遗漏依赖技能 | 使用 `--order` 时让工具自动补全依赖 |
| P3 | 参数值不带引号 | `--param path=./my dir` 导致解析错误 | 使用引号包裹含空格的路径：`--param "path=./my dir"` |
| P4 | 停用技能后不检查依赖 | 停用了被其他技能依赖的技能，导致后续编排失败 | 停用前使用 `技能包 --detail` 查看反向依赖 |
| P5 | 修改注册表 JSON 时破坏格式 | 手改 JSON 导致语法错误 | 使用 `技能管理` 命令修改，避免直接编辑文件 |

### 6.2 反模式对照表

| 反模式 | 问题 | 替代方案 |
|--------|------|----------|
| 把所有技能塞进一个编排 | 执行时间过长，失败难以定位 | 拆分为多个小编排，逐步验证 |
| 依赖最新版本而不锁定版本 | 技能升级后行为变化 | 在注册表中固定版本号 |
| 忽略警告信息 | 警告可能预示潜在问题 | 每次执行后检查警告项 |
| 在 CI 中直接使用未验证的编排 | 生产环境出现意外行为 | 先在本地跑通，再集成到 CI |

---

## 七、渐进式披露阅读路径

### 7.1 新手速查卡（30 秒上手）

```bash
# 1. 检查环境
agent-toolkit --selftest

# 2. 查看可用技能
agent-toolkit 技能包

# 3. 执行单个技能
agent-toolkit 技能编排 --single <技能ID> --param <key>=<value>

# 4. 编排多个技能
agent-toolkit 技能编排 --order <技能1>,<技能2>
```

### 7.2 进阶路径（1 小时精通）

1. 阅读「标准执行流程」章节，理解编排计划的生成逻辑
2. 使用 `--detail` 查看每个技能的参数要求
3. 尝试自定义技能配置参数（见 7.3）
4. 将编排命令封装为 shell 脚本，集成到 CI/CD

### 7.3 自定义技能配置参数

技能参数通过 `--param key=value` 传递，支持以下类型：

| 类型 | 示例 | 说明 |
|------|------|------|
| 字符串 | `path=./src` | 文件路径或名称 |
| 数字 | `threshold=8.5` | 浮点数或整数 |
| 布尔 | `verbose=true` | true/false |
| 列表 | `exclude=test,docs` | 逗号分隔的多个值 |

### 7.4 编写技能组合模板

创建 `~/.agent-toolkit/templates/` 目录，存放 YAML 模板：

```yaml
# 模板示例：code-quality.yaml
order:
  - code-format
  - lint-check
  - unit-test
params:
  path: ./src
  threshold: 8.0
```

使用模板执行：

```bash
agent-toolkit 技能编排 --template code-quality
```

### 7.5 集成到 CI/CD 流程

在 GitHub Actions 中示例：

```yaml
- name: Run skill orchestration
  run: |
    agent-toolkit --selftest
    agent-toolkit 技能编排 --template code-quality
```

---

## 八、技能注册表结构说明

注册表文件 `~/.agent-toolkit/registry.json` 格式：

```json
{
  "version": "1.0.0",
  "skills": {
    "code-format": {
      "version": "1.2.0",
      "status": "enabled",
      "dependencies": [],
      "entry": "skills/code-format/main.py",
      "params": {
        "path": {"type": "string", "required": true},
        "verbose": {"type": "boolean", "default": false}
      }
    }
  }
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| version | string | 注册表格式版本 |
| skills | object | 技能字典，键为技能 ID |
| skills.<id>.version | string | 技能版本号 |
| skills.<id>.status | string | enabled / disabled |
| skills.<id>.dependencies | array | 依赖的技能 ID 列表 |
| skills.<id>.entry | string | 技能入口脚本路径 |
| skills.<id>.params | object | 参数定义，含类型和必填标记 |

---

## 九、开发自定义技能扩展

### 9.1 技能包目录结构

```
skills/
└── my-skill/
    ├── main.py          # 技能入口脚本
    ├── manifest.json    # 技能元数据
    └── README.md        # 使用说明
```

### 9.2 manifest.json 格式

```json
{
  "id": "my-skill",
  "version": "1.0.0",
  "dependencies": [],
  "entry": "main.py",
  "params": {
    "input": {"type": "string", "required": true}
  }
}
```

### 9.3 技能间数据传递

技能间通过标准输入输出传递数据：

- 前一个技能的 stdout 作为后一个技能的 stdin
- 使用 `--param data=@previous_output` 引用前序结果
- 支持 JSON 格式的结构化数据传递

### 9.4 优化编排执行效率

- 将无依赖的技能并行执行（使用 `--parallel` 参数）
- 缓存技能执行结果（`--cache` 参数，按输入哈希缓存）
- 跳过已成功的步骤（`--skip-success` 参数）

---

## 十、用户协议

<!-- user-agreement-injected -->

**使用前请仔细阅读以下条款，使用本技能包即表示您同意全部内容：**

1. 本技能包按“原样”提供，使用者自行承担全部使用风险和责任。
2. 使用者应对使用本技能包产生的任何结果负全部责任，包括但不限于代码质量、数据准确性、业务影响等。
3. 禁止对本技能包进行反向工程、反编译、反汇编或试图提取源代码。
4. 禁止移除或修改本技能包中的版权声明和归属信息。
5. 使用者不得将本技能包用于任何违法或违规用途。
6. 本技能包的维护者不对任何直接、间接、偶然或后果性损害承担责任。
7. 使用本技能包即表示您已阅读、理解并同意本协议的全部条款。

---

## 十一、许可证（License）

<!-- professional-license-embedded -->

### MIT License

Copyright (c) 2026 LingFlow Studio

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

*本文档由 AI 辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。*
<!-- ai-generated-notice -->
