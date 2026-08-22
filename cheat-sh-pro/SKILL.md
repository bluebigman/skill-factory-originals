---
slug: cheat-sh-pro
name: 命令行速查手册
displayName: 终端速查 代码示例 即时检索
description: 一条命令获取编程语言与工具示例，开发调试即时查阅。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 终端工匠
agent_created: true
trigger_words: ["cheat.sh", "命令行速查", "代码示例查询", "终端查手册", "命令速查", "开发调试速查"]
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# 命令行速查手册（cheat-sh-pro）

## 一、能力边界：一页纸速查卡

### 能做什么

| 能力项 | 说明 | 示例 |
|--------|------|------|
| 查询编程语言语法 | 获取指定语言的核心语法示例 | `curl cheat.sh/python/lambda` |
| 查询工具用法 | 获取命令行工具的参数与用法 | `curl cheat.sh/tar` |
| 查询库/框架用法 | 获取特定库的常用操作示例 | `curl cheat.sh/numpy/array` |
| 查询算法实现 | 获取常见算法的代码示例 | `curl cheat.sh/sort` |
| 学习/速查双模式 | 支持学习模式（详细）与速查模式（精简） | `curl cheat.sh/python/lambda?T` |
| 本地终端集成 | 无需浏览器，终端内直接查阅 | 配合 curl 使用 |

### 不能做什么

| 限制项 | 说明 |
|--------|------|
| 不提供代码执行环境 | 仅返回示例文本，不执行任何代码 |
| 不保证示例的绝对正确性 | 示例来自社区贡献，可能存在过时或错误 |
| 不提供交互式问答 | 仅返回静态文本，不支持多轮对话 |
| 不覆盖所有工具/语言 | 仅覆盖社区已贡献的内容 |
| 不提供中文翻译 | 返回内容以英文为主 |

### 适用对象

- 日常使用命令行的开发者
- 需要快速查阅语法/用法的程序员
- 学习新语言/工具时希望快速上手的学习者
- 在无图形界面环境下工作的运维人员

---

## 二、触发方式：场景映射表

| 触发词/场景 | 用户意图 | 推荐操作 |
|-------------|----------|----------|
| "查一下 python 的 lambda 用法" | 想快速获取 Python lambda 语法示例 | `curl cheat.sh/python/lambda` |
| "tar 命令怎么解压" | 想获取 tar 命令的常用参数 | `curl cheat.sh/tar` |
| "有没有 numpy 数组操作的例子" | 想获取 numpy 库的常用操作 | `curl cheat.sh/numpy/array` |
| "快速排序怎么写" | 想获取排序算法的代码示例 | `curl cheat.sh/sort` |
| "查一下 go 语言的 goroutine" | 想获取 Go 语言并发示例 | `curl cheat.sh/go/goroutine` |
| "终端里直接查手册" | 想在终端内完成查询 | 直接使用 curl 调用 |

---

## 三、标准流程

### 前置条件

1. 终端环境已安装 `curl`（或 `wget`/`httpie`）
2. 网络可访问 `cheat.sh` 服务
3. 了解基本的命令行操作

### 执行步骤

**步骤 1：构造查询 URL**

基本格式：
```
{语言或工具}/{查询主题}
```

**步骤 2：发起请求**

```bash
# 基础查询
curl cheat.sh/python/lambda

# 指定语言版本
curl cheat.sh/python/3/lambda

# 查询工具用法
curl cheat.sh/tar

# 查询库用法
curl cheat.sh/numpy/array

# 查询算法
curl cheat.sh/sort
```

**步骤 3：使用查询参数（可选）**

| 参数 | 作用 | 示例 |
|------|------|------|
| `?T` | 终端模式（去除 ANSI 颜色） | `curl cheat.sh/python/lambda?T` |
| `?Q` | 静默模式（仅返回代码） | `curl cheat.sh/python/lambda?Q` |
| `?s` | 简化输出 | `curl cheat.sh/python/lambda?s` |
| `?b` | 浏览器模式（返回 HTML） | `curl cheat.sh/python/lambda?b` |

**步骤 4：阅读与使用输出**

- 输出为 Markdown 格式的文本
- 包含代码示例、参数说明、注意事项
- 可直接复制代码到编辑器中使用

### 输出规范

- 默认输出包含 ANSI 颜色代码（终端可读）
- 使用 `?T` 参数去除颜色，便于重定向到文件
- 输出内容按主题分组，包含标题、说明、代码块

---

## 四、置信度门控

当遇到以下情况时，输出 `[需核实:字段]` 占位符，不编造内容：

| 场景 | 处理方式 |
|------|----------|
| 查询主题不存在 | 返回 404 或空内容，提示 `[需核实:主题是否存在]` |
| 查询的语言/工具未收录 | 提示 `[需核实:该语言/工具是否已收录]` |
| 示例内容可能过时 | 提示 `[需核实:示例时效性]` |
| 网络请求失败 | 提示 `[需核实:网络连接]`，建议重试 |
| 返回内容不完整 | 提示 `[需核实:内容完整性]` |

---

## 五、错误码体系

| 错误码 | 错误描述 | 提示话术 | 修正步骤 |
|--------|----------|----------|----------|
| E001 | 网络连接失败 | "无法连接到 cheat.sh 服务，请检查网络" | 1. 检查网络连接 2. 重试请求 3. 使用 `curl -v` 查看详细错误 |
| E002 | 查询主题不存在 | "未找到相关主题，请检查拼写" | 1. 确认主题拼写 2. 尝试更通用的关键词 3. 访问 cheat.sh 首页查看支持列表 |
| E003 | 请求超时 | "请求超时，请稍后重试" | 1. 等待几秒后重试 2. 使用 `--max-time` 参数设置超时 |
| E004 | 返回内容为空 | "返回内容为空，可能主题未收录" | 1. 尝试其他关键词 2. 检查 URL 格式 3. 使用 `?s` 简化参数重试 |
| E005 | 参数错误 | "请求参数格式不正确" | 1. 检查 URL 格式 2. 确认参数拼写 3. 参考文档中的参数表 |

---

## 六、FAQ 反模式

### 常见坑 1：URL 编码问题

**错误做法**：直接在 URL 中使用空格和特殊字符
```bash
curl cheat.sh/python/lambda expression
```

**正确做法**：使用 URL 编码或连字符
```bash
curl cheat.sh/python/lambda-expression
# 或
curl cheat.sh/python/lambda%20expression
```

### 常见坑 2：忽略终端模式

**错误做法**：直接重定向带颜色的输出到文件
```bash
curl cheat.sh/python/lambda > output.md
```

**正确做法**：使用 `?T` 参数去除颜色
```bash
curl cheat.sh/python/lambda?T > output.md
```

### 常见坑 3：查询过于具体

**错误做法**：查询非常具体的函数名，导致无结果
```bash
curl cheat.sh/python/requests.post
```

**正确做法**：先查询库的通用用法，再自行查找
```bash
curl cheat.sh/python/requests
```

### 常见坑 4：忽略版本差异

**错误做法**：不指定语言版本，获取到过时示例
```bash
curl cheat.sh/python/f-string
```

**正确做法**：指定版本号
```bash
curl cheat.sh/python/3/f-string
```

### 常见坑 5：依赖单一来源

**错误做法**：完全依赖 cheat.sh 的示例，不验证正确性

**正确做法**：将 cheat.sh 作为参考，结合官方文档验证

---

## 七、渐进式披露

### 速查卡（30 秒上手）

```bash
# 最常用三个命令
curl cheat.sh/python/lambda
curl cheat.sh/tar
curl cheat.sh/git/commit

# 终端模式（推荐）
curl cheat.sh/python/lambda?T
```

### 新手路径（5 分钟入门）

1. 从常用工具开始：`curl cheat.sh/tar`、`curl cheat.sh/grep`
2. 学习 URL 结构：`{语言}/{主题}` 或 `{工具}`
3. 掌握 `?T` 参数，避免颜色干扰
4. 尝试查询自己常用的语言：`curl cheat.sh/python`、`curl cheat.sh/go`

### 进阶路径（深入使用）

1. 使用 `?Q` 参数获取纯代码，便于脚本处理
2. 结合 `jq` 等工具处理返回内容
3. 使用 `?s` 参数获取简化输出，提高阅读效率
4. 探索 cheat.sh 的社区贡献机制，了解内容来源
5. 结合其他速查工具（如 tldr、man pages）形成完整速查体系

---

## 八、用户协议

<!-- user-agreement-injected -->

**使用须知：**

1. 本 Skill 提供的所有信息仅供学习参考，使用者应自行判断信息的准确性和适用性。
2. 使用者因使用本 Skill 产生的任何直接或间接损失，本 Skill 作者不承担任何责任。
3. 本 Skill 仅提供信息查询功能，不包含任何代码执行能力。
4. 使用者不得对本 Skill 进行反向工程、反编译或破解。
5. 使用者应遵守相关法律法规，不得将本 Skill 用于非法用途。
6. 本 Skill 依赖第三方服务（cheat.sh），该服务的可用性和内容质量不在本 Skill 控制范围内。
7. 使用者应定期验证获取的信息，特别是用于生产环境的代码示例。

---

## 九、许可证（License）

<!-- professional-license-embedded -->

**MIT License**

Copyright (c) 2024 终端工匠

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
