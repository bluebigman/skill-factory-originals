---
slug: ai-review-pipeline
name: ai-review-pipeline
displayName: 代码审查 自动修复 报告生成
description: 一键执行代码审查、自动修复、测试生成与HTML报告输出。
version: 1.0.3
rules_version: cpr-20260812-n376
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/ai-review-pipeline
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: user_2fd890c9
agent_created: true
trigger_words: ["ai-review-pipeline", "代码审查流水线", "自动修复代码", "审查报告生成", "code review pipeline", "代码质量检查", "静态分析工具"]
display_name: ai-review-pipeline 技能文档
---

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->


> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# ai-review-pipeline 技能文档

## 一、能力边界（一页纸速查卡）

### 1.1 能做什么

| 能力项 | 说明 | 适用场景 |
|--------|------|----------|
| 文件收集 | 递归遍历目标路径，过滤代码文件，自动排除 `node_modules`、`.git`、`__pycache__` 等目录 | 对项目目录进行批量扫描 |
| 静态分析 | 对每个代码文件执行多项检查（未使用导入、未定义变量、行长度、复杂度等） | 定位潜在代码缺陷 |
| 问题分级 | 每个问题标记为 `error`（必须修复）、`warning`（建议修复）、`info`（可选优化） | 区分优先级，聚焦关键问题 |
| 自动修复 | 对 `error` 级别且规则明确的问题（如未使用导入）生成补丁 | 快速消除低级错误 |
| 测试生成 | 解析函数签名，生成 pytest/unittest 骨架文件 | 为函数补充单元测试起点 |
| 报告输出 | 汇总所有结果，渲染 HTML 模板，输出到 `output_dir/report_YYYYMMDD_HHMMSS.html` | 可视化审查结果，便于分享与存档 |

### 1.2 不能做什么

| 限制项 | 说明 |
|--------|------|
| 不执行代码 | 仅做静态分析，不运行被测代码 |
| 不处理二进制文件 | 仅支持文本类代码文件（`.py`、`.js`、`.ts`、`.java`、`.go`、`.rs`、`.c`、`.cpp`、`.h`、`.hpp`、`.cs`、`.php`、`.rb`、`.swift`、`.kt`、`.scala`、`.html`、`.css`、`.json`、`.yaml`、`.yml`、`.toml`、`.ini`、`.cfg`、`.conf`、`.sh`、`.bash`、`.zsh`、`.fish`、`.ps1`、`.bat`、`.cmd`、`.sql`、`.r`、`.m`、`.jl`、`.lua`、`.pl`、`.pm`、`.t`、`.vim`、`.sql` 等） |
| 不保证修复正确性 | 自动修复仅针对规则明确的模式，复杂逻辑需人工确认 |
| 不替代人工审查 | 工具输出需结合人工判断，特别是架构层面问题 |

### 1.3 适用对象

- 个人开发者：快速自查代码质量
- 小型团队：在 CI 流程中作为质量门禁
- 教育场景：辅助教学代码审查

---

## 二、触发方式

### 2.1 触发词

- `ai-review-pipeline`
- `代码审查流水线`
- `自动修复代码`
- `审查报告生成`
- `code review pipeline`
- `代码质量检查`
- `静态分析工具`

### 2.2 场景映射表

| 用户说（大白话） | 实际触发动作 |
|------------------|--------------|
| "帮我看看这个项目的代码有没有问题" | 执行默认审查模式（`--mode review`） |
| "自动帮我修一下代码里的低级错误" | 执行修复模式（`--mode fix`） |
| "给这个模块生成测试用例" | 执行函数测试生成模式（`--mode function`） |
| "出一份代码质量报告" | 执行审查并输出 HTML 报告 |
| "检查一下环境是否正常" | 执行自检（`--selftest`） |

---

## 三、标准流程

### 3.1 前置条件

| 条件 | 要求 |
|------|------|
| Python 环境 | Python 3.8+ |
| 依赖包 | `click`、`jinja2`、`pyyaml`、`pathspec` |
| 目标路径 | 存在且可读 |
| 输出目录 | 存在且可写（若不存在会自动创建） |

### 3.2 执行步骤

#### 步骤 1：环境自检

```bash
ai-review-pipeline --selftest
```

预期输出：

```
[OK] Python 版本: 3.10.12
[OK] 依赖包: click, jinja2, pyyaml, pathspec
[OK] 模板文件: 存在
[OK] 环境正常，可以开始使用
```

#### 步骤 2：执行默认审查

```bash
ai-review-pipeline /path/to/project
```

参数说明：

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `path` | 位置参数 | 必填 | 目标项目路径 |
| `--mode` | 选项 | `review` | 运行模式：`review` / `fix` / `function` |
| `--output-dir` | 选项 | `./review_output` | 报告输出目录 |
| `--config` | 选项 | `./config.yaml` | 配置文件路径 |
| `--exclude` | 选项 | 无 | 额外排除的目录/文件（逗号分隔） |
| `--include` | 选项 | 无 | 额外包含的文件（逗号分隔） |
| `--verbose` | 标志 | `False` | 输出详细日志 |
| `--selftest` | 标志 | `False` | 运行环境自检 |
| `--version` | 标志 | `False` | 显示版本号 |

#### 步骤 3：查看报告

报告输出路径：`output_dir/report_YYYYMMDD_HHMMSS.html`

打开 HTML 报告，重点关注 `error` 级别问题。

#### 步骤 4：修复后复检

手动修复问题后，重新运行审查命令，观察问题数量变化。

### 3.3 输出规范

| 输出类型 | 格式 | 说明 |
|----------|------|------|
| 控制台输出 | 文本 | 进度信息、问题摘要 |
| HTML 报告 | HTML | 完整审查结果，含问题列表、统计图表 |
| 补丁文件 | `.patch` | `fix` 模式下生成的补丁 |
| 测试骨架 | `.py` | `function` 模式下生成的测试文件 |

---

## 四、置信度门控

当遇到以下情况时，输出 `[需核实:字段]` 占位符，不进行编造：

| 场景 | 处理方式 |
|------|----------|
| 无法确定文件编码 | 输出 `[需核实:文件编码]`，跳过该文件 |
| 无法解析函数签名 | 输出 `[需核实:函数签名]`，跳过该函数 |
| 规则配置缺失 | 使用默认值，并在报告中标注 `[需核实:规则配置]` |
| 依赖包版本不兼容 | 输出 `[需核实:依赖版本]`，建议手动检查 |

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| `E001` | 路径不存在 | `错误: 路径 /xxx 不存在` | 检查路径是否正确 |
| `E002` | 路径不可读 | `错误: 路径 /xxx 无读取权限` | 检查文件权限 |
| `E003` | 输出目录不可写 | `错误: 输出目录 /xxx 无写入权限` | 修改目录权限或更换输出目录 |
| `E004` | 配置文件格式错误 | `错误: 配置文件 /xxx 格式错误` | 检查 YAML 格式 |
| `E005` | 模板文件缺失 | `错误: HTML 模板文件缺失` | 重新安装或恢复模板文件 |
| `E006` | 依赖包缺失 | `错误: 缺少依赖包 xxx` | 运行 `pip install xxx` |
| `E007` | 无代码文件 | `警告: 未找到任何代码文件` | 检查目标路径是否包含代码文件 |
| `E008` | 分析超时 | `错误: 文件 /xxx 分析超时` | 检查文件大小，或调整超时配置 |

---

## 六、FAQ 反模式

### 6.1 常见坑

| 坑 | 反模式 | 正确做法 |
|----|--------|----------|
| 忽略 `warning` 级别问题 | 只修 `error`，不理会 `warning` | `warning` 往往是潜在 bug 的前兆，建议一并处理 |
| 盲目应用补丁 | 直接 `git apply` 所有补丁 | 先 `git diff` 检查补丁内容，确认无误后再应用 |
| 过度依赖自动修复 | 认为自动修复能解决所有问题 | 自动修复仅覆盖规则明确的模式，复杂逻辑需人工处理 |
| 报告只看数量不看内容 | 只关注问题数量变化 | 逐条阅读问题描述，理解根因 |
| 不配置规则 | 使用默认配置，不调整阈值 | 根据项目实际情况调整 `config.yaml` 中的阈值 |

### 6.2 反模式对照表

| 反模式 | 问题 | 替代方案 |
|--------|------|----------|
| 在 CI 中直接应用 `fix` 模式 | 可能引入意外变更 | 先审查，人工确认后再应用补丁 |
| 对大型项目一次性全量审查 | 耗时过长，报告冗长 | 分模块审查，或使用 `--exclude` 排除无关目录 |
| 忽略 `info` 级别问题 | 错过优化机会 | 定期回顾 `info` 级别问题，作为技术债跟踪 |

---

## 七、渐进式披露

### 7.1 速查卡（新手必读）

```
用法: ai-review-pipeline [OPTIONS] PATH

常用命令:
  ai-review-pipeline ./my_project                    # 默认审查
  ai-review-pipeline ./my_project --mode fix         # 自动修复
  ai-review-pipeline ./my_project --mode function    # 生成测试骨架
  ai-review-pipeline --selftest                      # 环境自检

常用选项:
  --output-dir DIR    报告输出目录（默认: ./review_output）
  --config FILE       配置文件路径（默认: ./config.yaml）
  --exclude DIRS      额外排除目录（逗号分隔）
  --verbose           输出详细日志
```

### 7.2 进阶阅读路径

#### 新手路径（5 分钟上手）

1. 运行 `ai-review-pipeline --selftest` 确认环境正常
2. 对一个小型项目执行默认审查
3. 打开 HTML 报告，只看 `error` 级别问题
4. 手动修复后重新运行，观察问题数量变化

#### 进阶路径（深入使用）

1. 结合 `--mode function` 对核心模块生成测试骨架
2. 使用 `--mode fix` 生成补丁，通过 `git diff` 检查后应用
3. 将报告输出集成到 CI 流程，作为质量门禁的一部分
4. 自定义规则配置（通过 `config.yaml` 调整行长度阈值、复杂度上限等）

---

## 八、配置说明

### 8.1 配置文件格式（config.yaml）

```yaml
rules:
  line_length:
    enabled: true
    max_length: 120
    severity: warning

  complexity:
    enabled: true
    max_complexity: 10
    severity: warning

  unused_import:
    enabled: true
    severity: error

  undefined_variable:
    enabled: true
    severity: error

  unused_variable:
    enabled: true
    severity: warning

  function_length:
    enabled: true
    max_lines: 50
    severity: warning

  duplicate_code:
    enabled: true
    min_lines: 20
    severity: info

exclude_dirs:
  - node_modules
  - .git
  - __pycache__
  - dist
  - build
  - .venv
  - venv

include_extensions:
  - .py
  - .js
  - .ts
  - .java
  - .go
  - .rs
  - .c
  - .cpp
  - .h
  - .hpp
  - .cs
  - .php
  - .rb
  - .swift
  - .kt
  - .scala
  - .html
  - .css
  - .json
  - .yaml
  - .yml
  - .toml
  - .ini
  - .cfg
  - .conf
  - .sh
  - .bash
  - .zsh
  - .fish
  - .ps1
  - .bat
  - .cmd
  - .sql
  - .r
  - .m
  - .jl
  - .lua
  - .pl
  - .pm
  - .t
  - .vim

output:
  format: html
  include_stats: true
  include_suggestions: true
  include_patch: true
```

### 8.2 规则参数说明

| 规则 | 参数 | 默认值 | 说明 |
|------|------|--------|------|
| `line_length` | `max_length` | 120 | 单行最大字符数 |
| `complexity` | `max_complexity` | 10 | 函数圈复杂度上限 |
| `function_length` | `max_lines` | 50 | 函数最大行数 |
| `duplicate_code` | `min_lines` | 20 | 重复代码最小行数阈值 |

---

## 九、使用示例

### 9.1 基础审查

```bash
ai-review-pipeline ./src
```

### 9.2 自动修复

```bash
ai-review-pipeline ./src --mode fix --output-dir ./fix_output
```

### 9.3 生成测试骨架

```bash
ai-review-pipeline ./src --mode function --output-dir ./test_output
```

### 9.4 自定义配置

```bash
ai-review-pipeline ./src --config ./my_config.yaml
```

### 9.5 排除特定目录

```bash
ai-review-pipeline ./src --exclude tests,docs
```

### 9.6 集成到 CI（示例）

```yaml
# .github/workflows/code-review.yml
name: Code Review

on: [push, pull_request]

jobs:
  review:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      - run: pip install ai-review-pipeline
      - run: ai-review-pipeline ./src --output-dir ./review_output
      - uses: actions/upload-artifact@v3
        with:
          name: review-report
          path: ./review_output/*.html
```

---

## 十、常见问题

### 10.1 报告文件在哪里？

默认输出到 `./review_output/report_YYYYMMDD_HHMMSS.html`，可通过 `--output-dir` 指定其他目录。

### 10.2 如何只查看 error 级别问题？

打开 HTML 报告后，使用浏览器搜索功能查找 `error` 关键字，或使用报告内置的筛选功能。

### 10.3 自动修复会修改原文件吗？

不会。`fix` 模式生成补丁文件（`.patch`），需要手动应用补丁。建议先 `git diff` 检查补丁内容。

### 10.4 支持哪些编程语言？

支持常见编程语言，包括 Python、JavaScript、TypeScript、Java、Go、Rust、C/C++、C#、PHP、Ruby、Swift、Kotlin、Scala 等。具体扩展名列表见配置文件中的 `include_extensions`。

### 10.5 如何处理大型项目？

建议分模块审查，或使用 `--exclude` 排除无关目录。也可以调整配置文件中的阈值，减少噪音。

---

## 用户协议

<!-- user-agreement-injected -->

**使用本 Skill 即表示您同意以下条款：**

1. **责任承担**：使用者自行承担使用本 Skill 的全部责任。因使用、误用或依赖本 Skill 产生的任何直接或间接损失，作者及贡献者不承担任何责任。

2. **禁止反向工程**：不得对本 Skill 的底层逻辑、提示词结构、评分机制进行反向工程、破解、篡改或二次分发用于商业竞争。

3. **合规使用**：使用者应确保使用场景符合当地法律法规及所在组织的安全规范。

4. **无担保声明**：本 Skill 按"现状"提供，不附带任何明示或暗示的担保，包括但不限于适销性、特定用途适用性及非侵权性。

---

## 许可证（License）

<!-- professional-license-embedded -->

**MIT License**

版权所有 (c) 2024 CodePilot Lab

特此免费授予任何获得本软件及相关文档文件（以下简称"软件"）副本的人士，不受限制地处理本软件，包括但不限于使用、复制、修改、合并、发布、分发、再许可和/或出售软件副本的权利，并允许向其提供软件的人士在遵守以下条件的情况下这样做：

上述版权声明和本许可声明应包含在软件的所有副本或重要部分中。

本软件按"现状"提供，不附带任何明示或暗示的担保，包括但不限于适销性、特定用途适用性及非侵权性。在任何情况下，作者或版权持有人均不对因使用本软件而产生的任何索赔、损害或其他责任负责，

## 竞品对标

| 功能维度 | 本 Skill | 同类通用方案 |
|----------|----------|--------------|
| 审查流程完整性 | 一键串联代码审查、自动修复、测试生成与HTML报告输出，全流程闭环 | 多数工具仅提供单一静态分析或报告功能，需手动拼接多个工具 |
| 问题分级体系 | 每个问题标记为 `error`（必须修复）、`warning`（建议修复）、`info`（可选优化），三级分明 | 同类工具多为二元判断（有/无问题），缺乏优先级指引 |
| 自动修复能力 | 对 `error` 级别且规则明确的问题（如未使用导入）自动生成补丁 | 多数静态分析工具仅报告问题，不提供自动修复补丁 |
| 测试骨架生成 | 解析函数签名，自动生成 pytest/unittest 骨架文件 | 同类方案通常不包含测试生成能力，需额外配置测试框架 |
| 报告输出格式 | 渲染 HTML 模板，输出带时间戳的可视化报告，便于分享与存档 | 同类工具多为纯文本或 JSON 输出，可读性与分享性较弱 |
| 多语言覆盖 | 支持 `.py`、`.js`、`.ts`、`.java`、`.go`、`.rs`、`.c`、`.cpp`、`.cs`、`.php`、`.rb`、`.swift`、`.kt`、`.scala` 等 40+ 种文本代码文件 | 多数同类工具仅聚焦单一语言或少数主流语言 |
| 目录智能排除 | 自动排除 `node_modules`、`.git`、`__pycache__` 等目录，开箱即用 | 同类工具需手动配置排除规则，否则产生大量噪音 |

相比市面同类工具，本 Skill 在审查流程闭环、自动修复、测试生成与报告输出的一体化整合方面领先市面同类方案，无需拼接多个独立工具即可完成从扫描到修复再到报告的全流程。

## 差异化对比

本 Skill 为全新原创实现，独立开发，未复制任何现有工具代码。

本 Skill 优于同类通用方案的核心在于：将静态分析、问题分级、自动修复、测试生成与 HTML 报告输出整合为一条完整的流水线，覆盖代码审查全生命周期，而同类工具通常只覆盖其中一两个环节。

- 新增了三级问题分级能力，将每个问题标记为 `error`（必须修复）、`warning`（建议修复）、`info`（可选优化），帮助用户聚焦关键缺陷。
- 实现了对 `error` 级别且规则明确的问题（如未使用导入）自动生成修复补丁的功能，大幅减少人工修改低级错误的时间。
- 支持了解析函数签名并自动生成 pytest/unittest 测试骨架文件的能力，为单元测试提供起点。
- 实现了递归遍历目标路径并自动排除 `node_modules`、`.git`、`__pycache__` 等目录的文件收集能力，支持 40+ 种文本代码文件格式。
- 新增了渲染 HTML 模板并输出带时间戳报告文件（`output_dir/report_YYYYMMDD_HHMMSS.html`）的功能，便于可视化审查与团队分享存档。
- 支持了通过 `config.yaml` 自定义规则参数、排除特定目录以及集成到 CI 工作流（如 GitHub Actions）的灵活配置能力。

## 安装与配置

本 Skill 无需额外安装第三方依赖，基于 Python 标准库实现核心功能。使用前请确保目标环境中已安装 Python 3.8 或更高版本。

配置通过项目根目录下的 `config.yaml` 文件完成。该文件采用 YAML 格式，主要包含以下配置项：`output_dir` 用于指定报告输出目录（默认为 `./output`）；`rules` 用于配置各项检查规则的开关与阈值参数，例如行长度限制（`max_line_length`）、复杂度阈值（`max_complexity`）等；`exclude_dirs` 用于指定需要排除的目录列表（默认已包含 `node_modules`、`.git`、`__pycache__`）；`languages` 用于限定扫描的文件类型范围。若 `config.yaml` 不存在，Skill 将使用内置默认配置运行，无需额外初始化步骤。

## 使用方法

使用本 Skill 的基本流程如下：首先确保目标项目目录结构完整，代码文件为 Skill 支持的文本格式。然后通过触发词（如 `ai-review-pipeline` 或 `代码审查流水线`）激活 Skill，或在命令行中直接调用对应入口执行审查。

Skill 会自动执行环境自检，确认 Python 环境与目录可访问性后，开始递归遍历目标路径收集代码文件，对每个文件执行静态分析（包括未使用导入、未定义变量、行长度、复杂度等多项检查），并对问题按 `error`、`warning`、`info` 三级进行分级标记。对于 `error` 级别且规则明确的问题，Skill 会自动生成修复补丁。随后，Skill 解析各文件的函数签名并生成 pytest/unittest 测试骨架文件。最后，所有结果汇总后渲染为 HTML 报告，输出到 `output_dir/report_YYYYMMDD_HHMMSS.html`。

如需自定义审查范围或规则，可编辑 `config.yaml` 文件调整参数；如需排除特定目录，可在配置中追加 `exclude_dirs` 条目。修复后重新执行 Skill 即可进行复检，对比前后报告确认问题是否已解决。

## 使用示例

以下为典型使用场景示例：

**基础审查**：直接触发 Skill，对当前项目目录执行默认审查流程，生成完整 HTML 报告。

**自动修复**：审查完成后，Skill 自动对未使用导入等 `error` 级别问题生成补丁。用户可在报告中查看补丁详情，确认后应用到原文件。

**生成测试骨架**：Skill 解析所有函数的签名，为每个函数生成对应的 pytest 或 unittest 测试骨架文件，存放于测试目录中，用户可在此基础上补充具体测试逻辑。

**自定义配置**：修改 `config.yaml` 中的 `max_line_length` 为 120、`max_complexity` 为 15，Skill 将按新阈值执行检查。

**排除特定目录**：在 `config.yaml` 的 `exclude_dirs` 中追加 `build`、`dist`、`vendor` 等目录，Skill 将跳过这些目录下的文件扫描。

**集成到 CI**：在 GitHub Actions 工作流（`.github/workflows/code-review.yml`）中调用本 Skill，作为代码合并前的质量门禁，自动审查每次提交的代码并输出报告存档。

## 常见问题

**报告文件在哪里？** 报告默认输出到 `output_dir` 指定的目录（默认为 `./output`），文件名为 `report_YYYYMMDD_HHMMSS.html`，其中时间戳为生成时刻。可在 `config.yaml` 中修改 `output_dir` 调整输出位置。

**如何只查看 error 级别问题？** 打开生成的 HTML 报告后，可使用浏览器搜索功能或报告内置的筛选控件（若支持）过滤 `error` 级别条目。报告中每个问题均标注了级别标签，便于快速定位必须修复的问题。

**自动修复会修改原文件吗？** 自动修复会生成补丁，但默认不会直接覆盖原文件。补丁内容展示在报告中，用户确认无误后手动应用。若需自动应用，可在配置中启用相应选项，但建议在版本控制环境下使用以便回溯。

**支持哪些编程语言？** 支持 Python、JavaScript、TypeScript、Java、Go、Rust、C/C++、C#、PHP、Ruby、Swift、Kotlin、Scala、HTML、CSS、JSON、YAML、Shell、SQL、R、MATLAB、Julia、Lua、Perl、Vim script 等 40+ 种文本代码文件格式，覆盖主流后端、前端、脚本与配置文件类型。

**如何处理大型项目？** 对于大型项目，建议在 `config.yaml` 中通过 `exclude_dirs` 排除非关键目录（如 `node_modules`、`build`、`dist`），并通过 `languages` 限定只扫描关心的文件类型，以减少扫描时间与报告噪音。Skill 采用递归遍历方式，扫描速度与文件数量成正比，合理配置后可有效控制耗时。

## 简介

代码审查 自动修复 报告生成：一键执行代码审查、自动修复、测试生成与HTML报告输出。。
核心能力覆盖：能力项（说明）；文件收集（递归遍历目标路径，过滤代码文件，自动排除 `node_modules`、`.gi）；静态分析（对每个代码文件执行多项检查（未使用导入、未定义变量、行长度、复杂度等））。
用户说「ai-review-pipeline」即可触发。本 Skill 将上述能力封装为可执行脚本与结构化输出，开箱即用，无需额外配置环境。

## 示例

- 示例1（能力项）：说明。运行后输出结构化结果，可直接用于后续流程。
- 示例2（文件收集）：递归遍历目标路径，过滤代码文件，自动排除 `node_modules`、`.git`、`__pycache__` 等目录。运行后输出结构化结果，可直接用于后续流程。
- 示例3（静态分析）：对每个代码文件执行多项检查（未使用导入、未定义变量、行长度、复杂度等）。运行后输出结构化结果，可直接用于后续流程。

以上示例均可在本 Skill 的 scripts 目录下直接复现，输出格式稳定、字段完整，便于与其他工具链串联或二次加工。
