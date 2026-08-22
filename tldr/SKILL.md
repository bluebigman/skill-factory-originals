---
slug: tldr
name: tldr
displayName: 命令速查 参数解析 示例生成
description: 协作式命令行速查，比 man 更简洁实用，含常见示例，支持多语言。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: LinguaForge
agent_created: true
trigger_words: ["tldr", "速查", "命令示例", "怎么用", "命令行帮助", "command cheat sheet", "用法示例"]
---

> 本内容由 AI 生成，仅供学习参考 <!-- ai-generated-notice -->

# TLDR 命令速查 Skill 文档

## 一、能力边界（一页纸速查卡）

### 1.1 能做什么

| 能力项 | 说明 | 示例 |
|--------|------|------|
| 命令速查 | 返回命令的简介、语法、参数、示例 | `tldr grep` |
| 参数解释 | 解释特定参数的含义与用法 | `tldr grep -A` |
| 示例生成 | 按需生成典型使用场景的示例 | `tldr tar 压缩文件夹` |
| 命令对比 | 对比两个相似命令的差异与适用场景 | `tldr 对比 curl wget` |
| 组合建议 | 推荐管道/串联用法 | `tldr ps 配合 grep` |
| 高级用法 | 展示不常见但实用的技巧 | `tldr find -exec` |
| 参数默认值 | 说明未指定参数时的默认行为 | `tldr grep 默认` |
| 别名解析 | 将常见别名映射到真实命令 | `tldr ll` → `ls -l` |

### 1.2 不能做什么

- 不提供 man 级别的完整文档（超出 TLDR 定位）
- 不解释操作系统内部实现原理
- 不提供 GUI 工具的操作指南
- 不提供非命令行工具的速查（如 Excel 操作）
- 不保证覆盖所有命令的所有参数（仅覆盖常用部分）

### 1.3 适用对象

- 初级开发者：快速上手常用命令
- 中级开发者：查找不常用参数
- 高级开发者：获取组合用法与高级技巧
- 运维人员：快速定位命令用法

---

## 二、触发方式

### 2.1 触发词

直接使用 `tldr` 前缀，或包含以下场景词：

| 场景 | 触发词示例 |
|------|-----------|
| 直接查询 | `tldr docker`、`tldr git log` |
| 中文表达 | `怎么用 grep`、`tar 命令速查` |
| 参数询问 | `curl -L 什么意思`、`ls -la 参数解释` |
| 示例需求 | `给我几个 awk 示例`、`find 用法举例` |
| 对比需求 | `cp 和 rsync 区别`、`diff 和 cmp 对比` |

### 2.2 场景映射表

| 用户真实意图 | 触发语句示例 | 本 Skill 响应 |
|-------------|-------------|--------------|
| 想快速知道命令怎么用 | "tldr ffmpeg" | 输出 ffmpeg 速查卡 |
| 想知道某个参数的作用 | "tldr grep -v" | 解释 -v 参数含义 |
| 想看看实际例子 | "tldr tar 解压到指定目录" | 生成 tar 解压示例 |
| 不知道选哪个命令 | "tldr 对比 scp 和 rsync" | 输出对比表格 |
| 想组合多个命令 | "tldr 用 jq 处理 curl 结果" | 给出管道组合示例 |

---

## 三、标准流程

### 3.1 前置条件

- 用户输入包含命令名（英文）或明确的命令描述
- 若输入不明确，先询问澄清，不猜测

### 3.2 执行步骤

1. **提取命令名**：从用户输入中识别核心命令（支持别名映射，见附录 C）
2. **识别参数**：检测输入中的参数标记（`-x`、`--xxx` 格式）
3. **判断查询类型**：根据输入特征归类（速查/参数/示例/对比/组合/高级/默认值/别名）
4. **检索速查库**：在附录 A 中查找命令；未命中则使用附录 B 通用模板
5. **生成输出**：按 TLDR 格式组织内容（见 3.3）
6. **置信度标注**：若信息不完整，标注 `[需核实:字段]`

### 3.3 输出规范

输出格式固定为以下结构：

```
## 命令名

### 简介
（一句话说明命令用途）

### 常用语法
（1-3 行核心语法）

### 常用参数
| 参数 | 说明 |
|------|------|
| -x | 说明 |

### 典型示例
（3-5 个示例，每个含说明+命令）

### 高级用法
（1-2 个进阶技巧）
```

---

## 四、置信度门控

### 4.1 信息不足处理

当出现以下情况时，使用 `[需核实:字段]` 占位，不编造信息：

| 场景 | 处理方式 |
|------|---------|
| 命令存在但参数不确定 | 标注 `[需核实:该参数在 v2.0+ 中是否可用]` |
| 命令不在速查库中 | 使用通用模板，并标注 `[需核实:命令具体行为]` |
| 跨平台差异 | 标注 `[需核实:Linux/macOS 行为差异]` |
| 版本差异 | 标注 `[需核实:不同版本参数变化]` |

### 4.2 禁止行为

- 不编造不存在的参数
- 不臆测命令行为
- 不提供未经确认的默认值

---

## 五、错误码体系

| 错误码 | 场景 | 提示话术 | 修正步骤 |
|--------|------|---------|---------|
| E001 | 未识别命令名 | "未识别到命令名，请提供具体命令，如 `tldr grep`" | 重新输入含命令名的查询 |
| E002 | 命令名与参数混淆 | "无法区分命令与参数，请用空格分隔，如 `tldr ls -la`" | 按格式重新输入 |
| E003 | 查询类型无法判断 | "无法确定查询意图，请明确是查参数、示例还是对比" | 补充意图描述 |
| E004 | 命令不在速查库 | "该命令不在速查库中，已生成通用模板，部分信息需核实" | 接受模板或换用其他命令 |
| E005 | 别名无法解析 | "别名无法映射到已知命令，请使用完整命令名" | 使用完整命令名重试 |

---

## 六、FAQ 反模式

### 6.1 常见坑与反模式对照

| 坑 | 反模式（错误做法） | 正模式（正确做法） |
|----|-------------------|-------------------|
| 过度承诺 | "这个命令一定能解决你的问题" | "该命令适用于以下场景：..." |
| 信息过载 | 输出 50 个参数 | 只输出常用参数（≤10 个） |
| 忽略版本 | 不区分 GNU/BSD 差异 | 标注平台差异 |
| 编造默认值 | "默认就是 xxx" | "默认行为因版本而异，[需核实:具体默认值]" |
| 示例不实用 | 给理论示例不给实际场景 | 给真实场景示例（如"解压到指定目录"） |

### 6.2 反模式示例

**反模式**：用户问 `tldr grep -A`，回复 "grep 的 -A 参数是 after context 的意思，默认值是 2 行"（编造默认值）

**正模式**：回复 "-A 参数用于显示匹配行之后的 N 行内容，如 `grep -A 3 error log.txt` 显示匹配行后 3 行。默认值因版本而异，[需核实:具体默认值]"

---

## 七、渐进式披露

### 7.1 速查卡（30 秒上手）

```
tldr <命令名>          → 获取速查
tldr <命令名> -<参数>   → 获取参数解释
tldr <命令名> <场景>    → 获取场景示例
tldr 对比 <命令A> <命令B> → 获取对比
```

### 7.2 分层次阅读路径

**新手路径**：
1. 先看「简介」了解命令用途
2. 再看「典型示例」直接复制使用
3. 最后看「常用参数」了解可选项

**进阶路径**：
1. 查看「高级用法」获取技巧
2. 使用「命令对比」选择合适工具
3. 使用「组合建议」构建管道命令

---

## 附录 A：内置速查库（节选）

| 命令 | 简介 | 核心参数 |
|------|------|---------|
| grep | 文本搜索 | -i 忽略大小写、-v 反向匹配、-A/-B 上下文 |
| find | 文件查找 | -name 按名、-type 按类型、-exec 执行 |
| tar | 归档压缩 | -c 创建、-x 解压、-z gzip、-f 文件 |
| curl | 网络请求 | -L 跟随重定向、-o 输出文件、-H 请求头 |
| docker | 容器管理 | run 运行、ps 列表、exec 进入、logs 日志 |
| git | 版本控制 | log 日志、diff 差异、stash 暂存、rebase 变基 |
| jq | JSON 处理 | . 取值、\| 管道、-r 原始输出 |
| awk | 文本处理 | -F 分隔符、NR 行号、NF 字段数 |
| sed | 流编辑 | s 替换、d 删除、-i 原地修改 |
| ps | 进程查看 | aux 全部、-ef 全格式、--sort 排序 |

---

## 附录 B：通用速查模板

当命令不在速查库中时，使用以下模板：

```
## <命令名>

### 简介
[需核实:命令用途]

### 常用语法
[需核实:核心语法]

### 常用参数
[需核实:常用参数列表]

### 典型示例
[需核实:典型使用场景]

### 高级用法
[需核实:进阶技巧]
```

---

## 附录 C：别名映射表

| 别名 | 真实命令 | 说明 |
|------|---------|------|
| ll | ls -l | 长格式列表 |
| la | ls -a | 显示隐藏文件 |
| .. | cd .. | 返回上级目录 |
| ... | cd ../.. | 返回上上级目录 |
| g | git | git 简写 |
| k | kubectl | kubectl 简写 |
| d | docker | docker 简写 |

---

## 用户协议

使用本 Skill 即表示您同意以下条款：

1. **责任承担**：使用者自行承担因使用本 Skill 产生的全部责任。本 Skill 提供的信息仅供参考，不构成任何形式的保证或承诺。
2. **禁止反向工程**：不得对本 Skill 进行反向工程、反编译、破解或试图提取源代码。
3. **合规使用**：使用者应遵守所在国家/地区的法律法规，不得将本 Skill 用于任何非法用途。
4. **免责声明**：本 Skill 由 AI 辅助生成，可能存在错误或不准确之处，使用者应结合官方文档进行验证。

<!-- user-agreement-injected -->

---

## 许可证（License）

本 Skill 采用 MIT 许可证发布：

```
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
```

<!-- professional-license-embedded -->
