---
slug: ai-review-pipeline
name: ai-review-pipeline
displayName: 代码审查 自动修复 报告生成
description: 一键执行代码审查、自动修复、测试生成与HTML报告输出。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: CodePilot Studio
agent_created: true
trigger_words: ["ai-review-pipeline", "代码审查流水线", "自动修复代码", "审查报告生成", "code review pipeline", "代码体检", "质量门禁"]
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# SKILL.md — ai-review-pipeline

## 一、能力边界（一页纸速查卡）

### 1.1 能做什么

| 能力项 | 说明 | 典型耗时 |
|--------|------|----------|
| 静态审查 | 扫描代码中的潜在缺陷、风格问题、安全隐患 | 中型项目（1万行）约 30~60 秒 |
| 自动修复 | 对可机械修复的问题生成补丁（`--mode fix`） | 与审查耗时相当 |
| 测试骨架生成 | 为核心函数生成单元测试模板（`--mode function`） | 每个函数约 5~10 秒 |
| HTML 报告输出 | 生成带严重级别分级的可视化报告 | 审查完成后即时生成 |
| CI 集成 | 以退出码形式提供质量门禁判定 | 无额外耗时 |

### 1.2 不能做什么

- **不执行运行时验证**：不运行你的测试套件，不检测运行时崩溃。
- **不保证修复正确性**：自动生成的补丁需要人工确认，不保证逻辑等价。
- **不覆盖所有语言**：当前优先支持 Python、JavaScript、TypeScript、Go、Java；其他语言可能部分支持。
- **不替代人工评审**：工具只能发现模式化问题，架构级、业务语义级问题仍需人工介入。

### 1.3 适用对象

| 适用场景 | 不适用场景 |
|----------|------------|
| 个人项目快速体检 | 大型遗留系统全量迁移 |
| CI 流水线质量门禁 | 需要深度架构重构的项目 |
| 教学场景代码规范演示 | 对误报率极其敏感的生产核心 |
| 开源项目贡献前自检 | 需要自定义复杂规则引擎的场景 |

---

## 二、触发方式

### 2.1 触发词

直接使用以下任一短语即可触发本 Skill：

- `ai-review-pipeline`
- `代码审查流水线`
- `自动修复代码`
- `审查报告生成`
- `code review pipeline`
- `代码体检`（补充）
- `质量门禁`（补充）

### 2.2 场景映射表

| 你说的话（大白话） | 实际执行的动作 |
|-------------------|----------------|
| "帮我看看这段代码有没有问题" | 对当前目录执行默认审查，输出 HTML 报告 |
| "这个模块的函数能自动补测试吗" | 以 `--mode function` 生成测试骨架 |
| "把能自动修的问题直接改掉" | 以 `--mode fix` 生成补丁并应用 |
| "提交之前帮我检查一下" | 执行审查，以退出码判断是否通过质量门禁 |
| "这个项目代码质量怎么样" | 执行审查并输出汇总统计 |

---

## 三、标准流程

### 3.1 前置条件

| 条件 | 要求 | 验证方式 |
|------|------|----------|
| 运行环境 | Python 3.9+ 或 Node.js 16+ | `python --version` 或 `node --version` |
| 工具安装 | 已安装 `ai-review-pipeline` | `ai-review-pipeline --version` |
| 项目结构 | 目标目录包含可识别的源码文件 | 目录内存在 `.py` / `.js` / `.ts` / `.go` / `.java` 文件 |
| 配置文件（可选） | `config.yaml` 位于项目根目录 | `ls config.yaml` |

### 3.2 执行步骤

#### 第一步：环境自检

```bash
ai-review-pipeline --selftest
```

预期输出：

```
[OK] 环境检查通过
[OK] 依赖库版本兼容
[OK] 报告模板可用
```

#### 第二步：执行默认审查

```bash
ai-review-pipeline
```

参数说明：

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--path` | 当前目录 | 指定审查目标路径 |
| `--mode` | `review` | 可选 `review` / `fix` / `function` |
| `--severity` | `all` | 过滤级别：`error` / `warning` / `info` / `all` |
| `--format` | `html` | 输出格式：`html` / `json` / `text` |
| `--output` | `./review-report.html` | 报告输出路径 |
| `--config` | `./config.yaml` | 自定义规则配置文件路径 |

#### 第三步：查看报告

打开生成的 HTML 报告，重点关注：

- **error 级别**：必须修复的问题（如空指针引用、未捕获异常）
- **warning 级别**：建议修复的问题（如资源未关闭、复杂度超标）
- **info 级别**：可选优化项（如命名规范、注释缺失）

#### 第四步：修复与复检

```bash
# 生成修复补丁（不自动应用）
ai-review-pipeline --mode fix --dry-run

# 检查补丁内容
git diff

# 应用补丁
ai-review-pipeline --mode fix
```

#### 第五步：测试骨架生成

```bash
ai-review-pipeline --mode function --target src/core/parser.py
```

生成文件位于 `tests/` 目录下，命名规则为 `test_<模块名>.py`。

### 3.3 输出规范

| 输出类型 | 格式 | 内容 |
|----------|------|------|
| HTML 报告 | 单文件自包含 | 问题列表、严重级别、文件位置、修复建议 |
| JSON 报告 | 结构化数据 | 便于 CI 解析和二次处理 |
| 文本报告 | 纯文本 | 终端直接查看的摘要 |
| 补丁文件 | unified diff | 标准 `git apply` 可用的格式 |

---

## 四、置信度门控

### 4.1 信息不足时的处理

当工具无法确定某个问题的准确性时，输出中会包含 `[需核实:字段]` 占位符，而不是给出武断结论。

常见占位符：

| 占位符 | 含义 | 处理建议 |
|--------|------|----------|
| `[需核实:变量类型]` | 无法推断变量类型 | 人工确认类型后决定是否修复 |
| `[需核实:调用链]` | 跨文件调用关系不明确 | 检查相关文件后确认 |
| `[需核实:业务逻辑]` | 问题可能涉及业务语义 | 咨询业务负责人 |
| `[需核实:版本兼容]` | 依赖库版本影响判断 | 核对依赖版本 |

### 4.2 置信度分级

| 级别 | 含义 | 报告标记 |
|------|------|----------|
| 高 | 模式明确，修复方案确定 | 无标记 |
| 中 | 模式可识别，但需人工确认 | `[需核实:...]` |
| 低 | 仅提示可能存在问题 | 归入 info 级别 |

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| `E001` | 环境未就绪 | "依赖库缺失，请先运行 --selftest" | 安装缺失依赖后重试 |
| `E002` | 目标路径无效 | "指定路径不存在或不可读" | 检查路径权限和存在性 |
| `E003` | 无支持的源码文件 | "未找到可识别的源码文件" | 确认文件扩展名受支持 |
| `E004` | 配置解析失败 | "config.yaml 格式错误" | 检查 YAML 语法和字段名 |
| `E005` | 报告生成失败 | "HTML 模板渲染异常" | 检查输出路径权限，重试 |
| `E006` | 补丁应用冲突 | "补丁与当前代码冲突" | 手动合并或回退后重试 |
| `E007` | 测试生成失败 | "目标函数无法解析" | 确认函数签名完整且无语法错误 |

---

## 六、FAQ 反模式

### 6.1 常见坑

| 坑 | 反模式 | 正确做法 |
|----|--------|----------|
| 盲目应用补丁 | 直接 `--mode fix` 不检查 diff | 先 `--dry-run` 生成补丁，人工审查后再应用 |
| 忽略配置 | 使用默认规则审查所有项目 | 根据项目语言和规范调整 `config.yaml` |
| 只看数量不看内容 | 以问题数量作为唯一质量指标 | 结合 error 级别数量和修复难度综合评估 |
| 一次性全量审查 | 对大型项目一次性执行 | 按模块分批审查，避免超时和误报 |
| 不设质量门禁阈值 | CI 中不设置退出码判断 | 配置 `--severity error --max-errors 0` 作为门禁 |

### 6.2 反模式对照表

| 反模式 | 问题 | 替代方案 |
|--------|------|----------|
| "工具说没问题就是没问题" | 工具覆盖有限 | 结合人工评审和测试 |
| "把所有 warning 都修掉" | 可能引入新问题 | 优先修复 error，warning 按需处理 |
| "报告太长不看" | 遗漏关键问题 | 用 `--severity error` 过滤后查看 |
| "测试骨架生成后直接提交" | 骨架可能不完整 | 补充断言和边界用例后再提交 |

---

## 七、渐进式披露

### 7.1 速查卡（30 秒上手）

```bash
# 环境自检
ai-review-pipeline --selftest

# 默认审查当前目录
ai-review-pipeline

# 只看 error 级别
ai-review-pipeline --severity error

# 生成修复补丁（先检查）
ai-review-pipeline --mode fix --dry-run
git diff
ai-review-pipeline --mode fix

# 生成测试骨架
ai-review-pipeline --mode function --target src/core/parser.py
```

### 7.2 新手路径（首次使用）

1. 运行 `--selftest` 确认环境正常
2. 对一个小型项目执行默认审查
3. 打开 HTML 报告，只看 `error` 级别问题
4. 手动修复后重新运行，观察问题数量变化

### 7.3 进阶路径（熟练使用）

1. 结合 `--mode function` 对核心模块生成测试骨架
2. 使用 `--mode fix` 生成补丁，通过 `git diff` 检查后应用
3. 将报告输出集成到 CI 流程，作为质量门禁的一部分
4. 自定义规则配置（通过 `config.yaml` 调整行长度阈值、复杂度上限等）

### 7.4 配置示例（config.yaml）

```yaml
rules:
  line_length:
    enabled: true
    max: 100
  complexity:
    enabled: true
    max: 10
  security:
    enabled: true
    check_sql_injection: true
    check_xss: true

report:
  include_suggestions: true
  include_fix_examples: true

ci:
  fail_on: error
  max_errors: 0
```

---

## 八、用户协议

<!-- user-agreement-injected -->

**使用本 Skill 即表示您同意以下条款：**

1. **责任承担**：使用者自行承担使用本 Skill 的全部责任。因使用、误用或依赖本 Skill 产生的任何直接或间接损失，作者及贡献者不承担任何责任。

2. **禁止反向工程**：不得对本 Skill 的底层逻辑、提示词结构、评分机制进行反向工程、破解、篡改或二次分发用于商业竞争。

3. **合规使用**：使用者应确保使用场景符合当地法律法规及所在组织的安全规范。

4. **无担保声明**：本 Skill 按"现状"提供，不附带任何明示或暗示的担保，包括但不限于适销性、特定用途适用性及非侵权性。

---

## 九、许可证（License）

<!-- professional-license-embedded -->

**MIT License**

Copyright (c) 2024 CodePilot Studio

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
