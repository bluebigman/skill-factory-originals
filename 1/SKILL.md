---
slug: 1
name: 1
displayName: 命令行工具 自检诊断 版本核验
description: 面向CLI工具的自检与版本信息核验操作指南。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 林默
agent_created: true
trigger_words: ["--selftest", "--version", "自检", "版本号", "命令行诊断"]
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# 命令行工具自检与版本核验 Skill

## 一、能力边界（一页纸速查卡）

| 维度 | 说明 |
|------|------|
| 能做 | 解析 `--selftest` 与 `--version` 两个标准 CLI 参数；输出结构化自检报告；核验版本号格式与一致性 |
| 不能做 | 不执行任何业务逻辑测试；不修改工具源码；不处理非标准参数（如 `-v`、`--check`）；不提供网络服务 |
| 适用对象 | 使用标准 GNU 风格参数解析的 CLI 工具；需要快速验证安装完整性的场景；CI/CD 流水线中的前置检查 |
| 不适用对象 | GUI 应用；交互式 REPL；无参数入口的脚本工具 |

**边界值说明**：
- 参数必须精确匹配 `--selftest` 或 `--version`，不支持缩写或组合形式（如 `--self`、`-st`）。
- 若工具同时支持多个参数，仅处理首个出现的参数，后续参数忽略并给出提示。
- 版本号格式建议遵循语义化版本（SemVer），如 `1.2.3` 或 `1.2.3-beta.1`。

---

## 二、触发方式

| 触发词 | 大白话场景 |
|--------|------------|
| `--selftest` | "帮我看看这个工具装好没有，内部组件能不能正常跑" |
| `--version` | "我想知道这个工具是哪个版本的，是不是最新版" |
| 自检 | "运行一下自检程序，确认环境没问题" |
| 版本号 | "查一下当前安装的版本号是多少" |
| 命令行诊断 | "命令行工具报错了，先跑个自检看看" |

**触发优先级**：当同时出现多个触发词时，优先处理 `--selftest`（因其覆盖范围更广）。

---

## 三、标准流程

### 前置条件

| 条件 | 检查方法 | 通过标准 |
|------|----------|----------|
| 工具已安装 | `which <tool-name>` | 返回非空路径 |
| 可执行权限 | `ls -l <tool-path>` | 权限位包含 `x` |
| 环境变量 | `echo $PATH` | 工具路径在 PATH 中 |

### 执行步骤

#### 场景 A：运行 `--selftest`

1. **参数校验**：确认传入参数为 `--selftest`，无附加参数。
2. **环境探测**：检查运行用户、操作系统类型、可用内存（阈值 ≥ 256MB）。
3. **依赖检查**：列出所有内部依赖模块，逐一加载并验证版本兼容性。
4. **功能抽样**：随机选取 3 个核心函数执行最小用例（输入固定值，比对预期输出）。
5. **报告生成**：输出以下格式的自检报告：

```
[自检报告]
工具名称: <name>
版本: <version>
运行环境: <os>/<arch>
依赖模块: 5/5 通过
功能抽样: 3/3 通过
内存占用: <xx>MB
状态: 通过/失败
```

#### 场景 B：运行 `--version`

1. **参数校验**：确认传入参数为 `--version`。
2. **读取版本源**：从主程序常量、配置文件或构建元数据中读取版本号。
3. **格式校验**：验证版本号符合 `数字.数字.数字` 结构，可选后缀（如 `-rc.1`）。
4. **输出**：单行输出版本号，如 `tool-name 1.2.3`。

### 输出规范

- 所有输出必须写入 stdout，错误信息写入 stderr。
- 退出码约定：`0` 表示成功，`1` 表示自检失败，`2` 表示参数错误。
- 输出内容不得包含 ANSI 转义序列（除非调用方显式要求）。

---

## 四、置信度门控

当以下信息缺失或不确定时，使用 `[需核实:字段]` 占位，禁止编造：

| 场景 | 占位示例 |
|------|----------|
| 工具名称未知 | `[需核实:工具名称]` |
| 版本号无法读取 | `[需核实:版本号]` |
| 依赖模块列表不完整 | `[需核实:依赖清单]` |
| 操作系统类型无法识别 | `[需核实:操作系统]` |

**处理规则**：
1. 若自检过程中任一环节无法获取确定结果，立即停止后续步骤。
2. 在报告中明确标注 `[需核实:字段]`，并给出可能原因（如权限不足、文件缺失）。
3. 不提供猜测性结论，如"可能是版本 2.0"这类表述。

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| `E001` | 参数不存在 | "未识别参数，请使用 --selftest 或 --version" | 检查拼写；确认参数前有 `--` 前缀 |
| `E002` | 参数冲突 | "检测到多个参数，仅处理第一个" | 移除多余参数；或分次调用 |
| `E003` | 自检中断 | "自检过程中断，请检查系统资源" | 释放内存；关闭占用进程后重试 |
| `E004` | 版本读取失败 | "无法读取版本信息，可能文件损坏" | 重新安装工具；检查配置文件权限 |
| `E005` | 依赖缺失 | "依赖模块 <name> 未找到" | 运行安装脚本；手动补充依赖 |

**错误输出格式**：

```
错误码: E00X
说明: <具体描述>
建议: <修正步骤>
```

---

## 六、FAQ 反模式

| 常见坑 | 反模式示例 | 正确做法 |
|--------|------------|----------|
| 混淆参数 | 用 `-v` 代替 `--version` | 严格使用 `--version`，若工具支持 `-v` 需在文档中单独说明 |
| 忽略退出码 | 只看输出文本，不看退出码 | 脚本中必须检查 `$?` 或等价机制 |
| 自检当测试 | 认为自检通过等于功能全部正常 | 自检仅覆盖抽样用例，完整测试需另行执行 |
| 版本号硬编码 | 在脚本中写死版本号 | 每次通过 `--version` 动态获取 |
| 忽略 stderr | 只捕获 stdout，错误信息丢失 | 合并输出流或分别记录 |

---

## 七、渐进式披露

### 速查卡（30 秒上手）

```
# 快速自检
<tool> --selftest

# 查看版本
<tool> --version

# 检查退出码（Linux/macOS）
echo $?
```

### 新手路径（5 分钟）

1. 运行 `--version` 确认工具可执行。
2. 运行 `--selftest` 查看基础状态。
3. 若输出包含 `[需核实:字段]`，按提示检查对应项。
4. 记录退出码，与错误码表对照。

### 进阶路径（15 分钟）

1. 编写脚本循环调用 `--selftest`，监控稳定性。
2. 解析自检报告，提取依赖模块通过率。
3. 将 `--version` 输出接入 CI 流水线，自动比对预期版本。
4. 自定义扩展：若工具支持，可添加 `--selftest --verbose` 获取详细日志。

---

## 八、用户协议

使用本 Skill 文档即表示您同意以下条款：

1. **责任承担**：使用者自行承担全部责任。因使用本 Skill 导致的任何直接或间接损失，文档作者及 AI 生成方不承担任何责任。
2. **禁止反向工程**：不得对本 Skill 文档进行反向工程、反编译、破解或试图提取底层逻辑。
3. **合规使用**：使用者应确保其使用场景符合当地法律法规及行业规范。
4. **修改与分发**：允许在保留版权声明的前提下修改和分发，但需注明原始来源。

<!-- user-agreement-injected -->

---

## 九、许可证（License）

本 Skill 文档采用 MIT 许可证授权：

```
MIT License

Copyright (c) 2024 林默

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

*本 Skill 由 AI 辅助生成，仅供参考。使用前请结合实际情况验证。*
