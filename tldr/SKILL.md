---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: tldr
name: tldr
displayName: 命令速查 参数解析 示例生成
description: 快速获取命令用法、参数解释与典型示例的协作式速查工具。
version: 1.6.6
rules_version: cpr-20260817-n526
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/tldr
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: CommandPilot
agent_created: true
trigger_words: ["tldr", "速查", "命令示例", "参数解释", "命令行速查", "cheatsheet", "命令用法"]
---

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->


> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# TLDR 命令速查 Skill 文档

## 一、能力边界（一页纸速查卡）

### 1.1 能做什么

| 能力项 | 说明 | 示例 |
|--------|------|------|
| 命令速查 | 返回命令的简介、语法、常用参数、典型示例 | `tldr grep` |
| 参数解释 | 解释指定参数的含义与适用场景 | `tldr grep -A` |
| 别名解析 | 将常见别名映射到原始命令 | `tldr ll` → 解析为 `ls -l` |
| 示例生成 | 根据命令名生成符合实际场景的示例 | `tldr tar` |
| 命令对比 | 对比两个相似命令的差异与适用场景 | `tldr cp vs rsync` |
| 组合建议 | 给出管道/重定向等组合用法建议 | `tldr ps + grep` |
| 高级用法 | 展示正则、脚本化、批量处理等进阶技巧 | `tldr find -exec` |
| 参数默认值 | 说明关键参数未指定时的默认行为 | `tldr grep` 默认行为说明 |

### 1.2 不能做什么

- 不能执行命令，仅提供文本说明
- 不能访问互联网获取实时文档，仅依赖内置速查库
- 不能保证覆盖所有命令的所有参数（覆盖范围见附录A）
- 不能替代 `man` 的完整手册，仅提供高频用法
- 不能处理模糊查询（如"那个压缩命令"），需明确命令名

### 1.3 适用对象

- 初级开发者：快速上手不熟悉的命令
- 中级开发者：确认参数用法、查找示例
- 高级开发者：对比命令、组合建议、高级用法参考

---

## 二、触发方式

### 2.1 触发词

- 主触发词：`tldr`
- 同义触发词：`速查`、`命令示例`、`参数解释`、`cheatsheet`、`命令用法`

### 2.2 场景映射表

| 用户场景（大白话） | 触发方式 | 期望输出 |
|-------------------|----------|----------|
| "grep 怎么用？" | `tldr grep` | 基础速查卡片 |
| "grep 的 -A 参数啥意思？" | `tldr grep -A` | 参数解释 |
| "ll 是啥命令？" | `tldr ll` | 别名解析结果 |
| "tar 打包有哪些常用写法？" | `tldr tar` | 典型示例列表 |
| "cp 和 rsync 选哪个？" | `tldr cp vs rsync` | 对比分析 |
| "怎么找出大文件并排序？" | `tldr find + sort` | 组合建议 |
| "find 怎么批量删除旧文件？" | `tldr find -delete` | 高级用法 |

---

## 三、标准流程

### 3.1 前置条件

- 用户输入包含明确的命令名（或可解析的别名）
- 命令名拼写正确（不区分大小写）
- 若查询参数，参数格式需符合 POSIX 风格（如 `-A`、`--context`）

### 3.2 执行步骤

1. **解析输入**：提取命令名、参数、查询类型
   - 正则匹配：`tldr\s+([a-zA-Z0-9_-]+)(?:\s+(-{1,2}[a-zA-Z0-9=]+))?`
   - 别名映射：查表 `ll→ls -l`、`la→ls -a`、`..→cd ..` 等
   - 查询类型判断：
     - 含 `vs` → 命令对比
     - 含 `+` → 组合建议
     - 含 `-` 参数 → 参数解释
     - 含 `--advanced` → 高级用法
     - 其余 → 基础速查

2. **检索速查库**：在附录A的速查库中查找命令
   - 命中 → 提取对应条目
   - 未命中 → 进入附录B通用模板生成流程

3. **生成输出**：按 TLDR 格式组织内容
   - 命令简介（一句话）
   - 常用语法（1-3 行）
   - 常用参数表（参数、说明、示例）
   - 典型示例（3-5 个，含注释）
   - 高级用法（1-2 个，可选）

4. **质量校验**：
   - 参数表是否完整覆盖用户查询的参数
   - 示例是否可直接复制执行
   - 输出是否包含 [需核实] 占位（信息不足时）

### 3.3 输出规范

```markdown
# 命令名

> 一句话简介（来源：速查库/通用模板）

## 常用语法
- 语法行1
- 语法行2

## 常用参数
| 参数 | 说明 | 示例 |
|------|------|------|
| -x | 参数说明 | 示例用法 |

## 典型示例
1. 场景描述
   ```bash
   命令示例
   ```

## 高级用法
- 进阶技巧说明
  ```bash
  高级示例
  ```
```

---

## 四、置信度门控

### 4.1 信息不足时的处理

当速查库中无该命令、或参数信息不完整时，遵循以下规则：

| 情况 | 处理方式 | 示例 |
|------|----------|------|
| 命令不在速查库 | 使用通用模板，标注 `[需核实:命令名]` | `[需核实:xxd] 该命令不在内置速查库中，以下为通用模板` |
| 参数含义不确定 | 标注 `[需核实:参数-x]` | `[需核实:-z] 该参数含义需查阅官方文档确认` |
| 默认值不确定 | 标注 `[需核实:默认值]` | `[需核实:默认值] grep 默认不显示行号` |
| 示例未验证 | 标注 `[需核实:示例]` | `[需核实:示例] 以下示例未在目标环境验证` |

### 4.2 禁止行为

- 禁止编造不存在的参数
- 禁止猜测命令行为
- 禁止使用"应该""可能"等模糊表述替代占位符

---

## 五、错误码体系

| 错误码 | 错误场景 | 提示话术 | 修正步骤 |
|--------|----------|----------|----------|
| E001 | 未输入命令名 | "请输入要查询的命令名，例如：tldr grep" | 补充命令名后重试 |
| E002 | 命令名无法识别 | "无法识别命令 [xxx]，请检查拼写或使用 tldr --list 查看支持的命令" | 检查拼写，或查询支持列表 |
| E003 | 参数格式错误 | "参数格式不正确，POSIX 风格应为 -x 或 --xxx" | 按正确格式重新输入 |
| E004 | 对比命令格式错误 | "对比查询需使用格式：tldr 命令A vs 命令B" | 按格式重新输入 |
| E005 | 组合查询格式错误 | "组合查询需使用格式：tldr 命令A + 命令B" | 按格式重新输入 |
| E006 | 速查库未覆盖 | "命令 [xxx] 不在速查库中，已生成通用模板，部分信息需核实" | 参考通用模板，或查阅官方文档 |

---

## 六、FAQ 反模式

### 6.1 常见坑

| 坑 | 反模式（错误做法） | 正模式（正确做法） |
|----|-------------------|-------------------|
| 命令名拼写错误 | 输入 `tldr greap` 期望得到 grep 结果 | 检查拼写，或使用 `tldr --list` 搜索 |
| 参数混用 | 同时使用 `-A` 和 `--context` 期望不同结果 | 明确查询一个参数，或使用 `tldr grep -A --context` 对比 |
| 忽略默认值 | 认为 `grep` 默认显示行号 | 查看参数默认值说明，grep 默认不显示行号 |
| 依赖完整手册 | 期望 tldr 输出与 man 相同 | 理解 tldr 定位为速查，完整信息用 man |
| 跨平台混淆 | 认为 Linux 命令在 macOS 上行为完全一致 | 注意平台差异，如 `sed -i` 在 macOS 需 `-i ''` |

### 6.2 反模式对照表

| 反模式 | 问题 | 替代方案 |
|--------|------|----------|
| 输出过长 | 失去速查意义 | 控制输出在 50 行以内，聚焦高频用法 |
| 示例无注释 | 用户难以理解 | 每个示例前加场景说明 |
| 参数表过全 | 用户被信息淹没 | 只列高频参数，低频参数标注"详见 man" |
| 忽略版本差异 | 示例可能不兼容 | 标注适用版本或平台 |

---

## 七、渐进式披露

### 7.1 速查卡（一页纸）

```markdown
# TLDR 速查卡

## 基本用法
tldr <命令名>          # 基础速查
tldr <命令名> -<参数>   # 参数解释
tldr <命令A> vs <命令B> # 命令对比
tldr <命令A> + <命令B>  # 组合建议

## 常用命令速查
| 命令 | 一句话用法 |
|------|-----------|
| grep | 文本搜索，支持正则 |
| find | 文件查找，支持条件过滤 |
| tar | 归档压缩，支持多种格式 |
| ps | 进程查看，支持条件过滤 |
| awk | 文本处理，支持列操作 |
```

### 7.2 分层次阅读路径

**新手路径**（首次使用）：
1. 阅读速查卡了解基本用法
2. 尝试 `tldr grep` 查看输出格式
3. 使用 `tldr --list` 查看支持的命令列表
4. 遇到不认识的命令，先查速查再查 man

**进阶路径**（熟练用户）：
1. 使用参数解释功能深入理解 `tldr grep -A`
2. 使用命令对比功能选择合适工具 `tldr cp vs rsync`
3. 使用组合建议优化工作流 `tldr find + xargs`
4. 使用高级用法探索边界能力 `tldr find -exec`

---

## 附录A：内置速查库（节选）

| 命令 | 简介 | 高频参数 |
|------|------|----------|
| grep | 文本搜索 | -i, -v, -r, -n, -A, -B, -C, -E |
| find | 文件查找 | -name, -type, -size, -mtime, -exec, -delete |
| tar | 归档压缩 | -c, -x, -z, -j, -v, -f, -C |
| ps | 进程查看 | -e, -f, -u, -aux, --sort |
| awk | 文本处理 | -F, -v, '{print}', NR, NF |
| sed | 流编辑 | -i, -e, -n, s///, d, p |
| ls | 列表查看 | -l, -a, -h, -t, -r, -S |
| cp | 复制 | -r, -i, -u, -p, -a |
| mv | 移动/重命名 | -i, -u, -v, -n |
| rm | 删除 | -r, -f, -i, -v |
| chmod | 权限修改 | -R, u+x, g-w, o=r |
| curl | 网络请求 | -X, -H, -d, -o, -I, -L |
| wget | 下载 | -O, -c, -r, -q, --limit-rate |
| ssh | 远程连接 | -p, -i, -L, -R, -N, -f |
| scp | 远程复制 | -P, -r, -i, -C |
| docker | 容器管理 | run, ps, exec, logs, stop, rm |
| git | 版本控制 | clone, add, commit, push, pull, status |
| npm | 包管理 | install, run, start, test, publish |
| pip | Python包管理 | install, uninstall, list, freeze, show |
| systemctl | 服务管理 | start, stop, restart, status, enable |

---

## 附录B：通用速查模板

当命令不在速查库中时，使用以下模板生成：

```markdown
# [命令名]

> [需核实:命令名] 该命令不在内置速查库中，以下为通用模板

## 常用语法
- [需核实:语法] 请查阅官方文档确认语法格式

## 常用参数
| 参数 | 说明 | 示例 |
|------|------|------|
| [需核实:参数] | [需核实:说明] | [需核实:示例] |

## 典型示例
1. [需核实:示例] 请参考官方文档或 man 手册
   ```bash
   [需核实:示例命令]
   ```

## 高级用法
- [需核实:高级用法] 建议查阅官方文档获取完整信息
```

---

## 八、用户协议

<!-- user-agreement-injected -->

**使用本 Skill 即表示您同意以下条款：**

1. **责任承担**：使用者自行承担使用本 Skill 产生的全部责任。本 Skill 提供的所有信息仅供参考，不构成任何形式的保证或承诺。

2. **信息准确性**：本 Skill 内置速查库基于公开文档整理，可能存在过时或不准确之处。使用者应通过官方文档（如 `man` 手册）验证关键命令用法。

3. **禁止反向工程**：使用者不得对本 Skill 的底层实现进行反向工程、反编译、破解或试图提取源代码。

4. **合规使用**：使用者应遵守所在国家/地区的法律法规，不得将本 Skill 用于任何非法用途。

5. **免责声明**：因使用本 Skill 导致的任何直接或间接损失，Skill 作者及贡献者不承担任何责任。

---

## 九、许可证（License）

<!-- professional-license-embedded -->

**MIT License**

Copyright (c) 2026 CommandPilot

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
