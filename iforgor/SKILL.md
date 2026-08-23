---
slug: iforgor
name: iforgor
displayName: 代码语法 速查速答 命令行助手
description: 命令行即问即答，快速查询代码语法片段，提升编码效率。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: SyntaxSage
agent_created: true
trigger_words: ["iforgor", "语法速查", "代码片段", "语法查询", "命令行工具", "语法忘记", "代码回忆", "语法助手"]

---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# iforgor — 命令行语法速查助手

## 一、能力边界（一页纸速查卡）

### 能做什么

| 能力项 | 说明 | 示例 |
|--------|------|------|
| 语法片段查询 | 输入关键词，返回对应语言的语法片段 | `iforgor python list comprehension` |
| 代码片段速查 | 返回可直接使用的代码模板 | `iforgor js fetch` |
| 多语言支持 | 覆盖主流编程语言（Python、JavaScript、Java、Go、Rust、C++ 等） | `iforgor rust match` |
| 命令行交互 | 纯终端操作，无需打开浏览器 | `iforgor sql join` |
| 自检功能 | 验证工具安装是否正确 | `iforgor --selftest` |
| 版本查看 | 显示当前工具版本 | `iforgor --version` |

### 不能做什么（明确边界）

| 限制项 | 说明 |
|--------|------|
| 不执行代码 | 仅返回语法片段，不运行、不编译、不解释执行结果 |
| 不提供完整项目方案 | 只回答语法层面的问题，不涉及架构设计、业务逻辑 |
| 不替代官方文档 | 返回的是常用片段，复杂场景请查阅官方文档 |
| 不保证代码正确性 | 返回的片段基于常见用法，需结合具体环境验证 |
| 不支持自然语言对话 | 仅支持关键词查询，不支持多轮对话 |

### 适用对象

- 初级开发者：快速回忆语法，减少搜索时间
- 中级开发者：查漏补缺，确认边界写法
- 高级开发者：快速获取模板，减少重复输入

---

## 二、触发方式

### 触发词

- 主触发词：`iforgor`
- 同义场景词：`语法忘记`、`代码回忆`、`语法助手`

### 场景映射表

| 用户场景 | 触发方式 | 示例命令 |
|----------|----------|----------|
| 忘记 Python 列表推导式写法 | `iforgor python list comprehension` | 返回推导式语法及示例 |
| 需要 JS 的 async/await 模板 | `iforgor js async await` | 返回异步函数写法 |
| 查询 SQL 的 JOIN 语法 | `iforgor sql join` | 返回 JOIN 类型及示例 |
| 确认 Go 的错误处理写法 | `iforgor go error handling` | 返回 error 处理模式 |
| 查看工具是否正常 | `iforgor --selftest` | 运行自检 |
| 查看版本号 | `iforgor --version` | 显示版本信息 |

---

## 三、标准流程

### 前置条件

1. 已安装 iforgor 命令行工具
2. 终端环境可正常执行命令
3. 网络连接正常（如需在线查询）

### 执行步骤

1. **确认工具状态**：执行 `iforgor --selftest`，确认返回 `OK` 状态
2. **输入查询命令**：按 `iforgor [语言] [关键词]` 格式输入
3. **查看返回结果**：系统返回语法片段及简要说明
4. **复制使用**：将片段复制到代码中，按需修改
5. **验证结果**：在开发环境中运行，确认语法正确

### 输出规范

| 输出项 | 格式 | 示例 |
|--------|------|------|
| 语法片段 | 代码块，含语言标识 | ```python\n[x for x in range(10)]\n``` |
| 简要说明 | 1-2 行文字描述 | 列表推导式，生成 0-9 的列表 |
| 参数说明 | 表格或列表 | 参数名、类型、说明 |
| 注意事项 | 提示性文字 | 注意：Python 3.8+ 支持海象运算符 |

---

## 四、置信度门控

### 信息不足时的处理

当查询信息不足以返回准确结果时，系统将输出：

```
[需核实:语言类型]
[需核实:具体语法关键词]
```

### 不编造原则

- 不猜测用户意图，仅返回明确匹配的结果
- 不确定的语法不返回，提示用户补充信息
- 版本差异导致的语法变化，标注版本要求

### 示例

**输入**：`iforgor python`（缺少关键词）

**输出**：
```
[需核实:具体语法关键词]
请补充查询内容，如：iforgor python list
```

---

## 五、错误码体系

| 错误码 | 错误描述 | 提示话术 | 修正步骤 |
|--------|----------|----------|----------|
| E001 | 命令未找到 | `iforgor: command not found` | 检查安装路径，确认环境变量配置 |
| E002 | 参数缺失 | `iforgor: missing arguments` | 输入 `iforgor --help` 查看用法 |
| E003 | 语言不支持 | `iforgor: language not supported` | 输入 `iforgor --list-languages` 查看支持列表 |
| E004 | 关键词无匹配 | `iforgor: no matching syntax found` | 更换关键词，或使用更通用的术语 |
| E005 | 网络错误 | `iforgor: network error` | 检查网络连接，稍后重试 |
| E006 | 版本过旧 | `iforgor: version outdated` | 执行 `iforgor --update` 更新 |

---

## 六、FAQ 反模式

### 常见坑与反模式对照

| 常见坑 | 反模式（错误做法） | 正确做法 |
|--------|-------------------|----------|
| 查询过于模糊 | 输入 `iforgor python` 期望返回所有语法 | 指定具体语法，如 `iforgor python decorator` |
| 忽略版本差异 | 直接使用返回的片段，未检查版本兼容性 | 确认目标环境版本，选择对应语法 |
| 过度依赖模板 | 不修改直接复制，导致逻辑错误 | 理解片段逻辑，按需修改参数 |
| 混淆语言 | 用 Python 的语法查询 JS 的写法 | 明确指定语言，如 `iforgor js map` |
| 忽略错误提示 | 遇到 E004 不调整，反复输入相同查询 | 根据提示更换关键词，或查看帮助文档 |

### 反模式示例

**错误**：`iforgor sort`（未指定语言）

**正确**：`iforgor python sort` 或 `iforgor js sort`

---

## 七、渐进式披露

### 速查卡（快速上手）

```
iforgor --help           # 查看帮助
iforgor --version        # 查看版本
iforgor --selftest       # 自检
iforgor python list      # 查询 Python 列表语法
iforgor js fetch         # 查询 JS fetch 语法
iforgor sql join         # 查询 SQL JOIN 语法
```

### 新手路径（5 分钟上手）

1. 安装工具后，先执行 `iforgor --selftest` 确认安装成功
2. 使用 `iforgor --help` 查看支持的命令格式
3. 从简单的查询开始：`iforgor python print`
4. 逐步尝试多关键词查询：`iforgor python list comprehension`
5. 遇到问题查看错误码表，对照修正

### 进阶路径（深入使用）

1. 掌握多语言查询：`iforgor --list-languages` 查看支持语言
2. 组合查询：`iforgor python file read write` 获取文件操作片段
3. 自定义片段：将常用片段保存到本地，形成个人代码库
4. 版本管理：定期更新工具，获取最新语法支持
5. 贡献内容：向项目提交新的语法片段，丰富知识库

---

## 八、用户协议

<!-- user-agreement-injected -->

**使用条款**

1. **责任承担**：使用者自行承担使用本 Skill 的全部责任。因使用本 Skill 产生的任何直接或间接损失，包括但不限于代码错误、数据丢失、业务中断等，本 Skill 作者及贡献者不承担任何责任。

2. **内容准确性**：本 Skill 提供的语法片段和代码示例仅供参考，不构成任何形式的保证。使用者应在实际环境中验证代码的正确性和适用性。

3. **禁止反向工程**：使用者不得对本 Skill 进行反向工程、反编译、反汇编，或试图提取源代码、算法、数据结构等内部实现细节。

4. **合规使用**：使用者应遵守所在国家/地区的法律法规，不得将本 Skill 用于任何非法用途。

5. **免责声明**：本 Skill 由 AI 辅助生成，仅供学习参考。作者不对内容的完整性、准确性、时效性作出任何承诺。

---

## 九、许可证（License）

<!-- professional-license-embedded -->

**MIT License**

Copyright (c) 2024 SyntaxSage

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
