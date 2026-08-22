---
slug: github-automation-scripts
name: github-automation-scripts
displayName: 仓库日常运维 脚本批处理 版本控制
description: 用标准库脚本简化 Git 与 GitHub 日常操作，提升仓库管理效率。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 脚本工坊
agent_created: true
trigger_words: ["github automation", "git 自动化", "仓库脚本", "自动化工作流", "git 批处理", "git 批量操作", "仓库维护脚本"]
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# GitHub 自动化脚本操作指南

## 一、能力边界速查卡

### 能做什么

| 场景 | 说明 | 示例 |
|------|------|------|
| 批量文件处理 | 对同一目录下多个文件执行统一操作 | 批量重命名、批量添加头部注释 |
| 常规 Git 操作 | 通过脚本执行 add/commit/push 等基础命令 | 自动提交并推送 |
| 仓库状态检查 | 批量查看多个仓库的分支、状态、远程信息 | 遍历目录输出各仓库状态 |
| 简单工作流编排 | 将多个 Git 命令串联成固定流程 | 拉取 → 合并 → 推送 |

### 不能做什么

| 限制项 | 说明 |
|--------|------|
| 不处理冲突 | 合并冲突需要人工介入，脚本不负责解决 |
| 不做代码审查 | 不判断代码质量、不检查逻辑正确性 |
| 不涉及权限管理 | 不处理 SSH 密钥配置、仓库访问授权 |
| 不执行危险操作 | 不包含 force push、历史改写等高风险命令 |
| 不替代 CI/CD | 不涉及持续集成、持续部署流水线配置 |

### 适用对象

- 需要频繁处理多个仓库的开发者
- 有重复性 Git 操作需求的团队
- 希望将日常操作脚本化的运维人员

---

## 二、触发方式与场景映射

| 触发词 | 实际场景 | 对应操作 |
|--------|----------|----------|
| "github automation" | 需要自动化 GitHub 操作 | 进入本 Skill 流程 |
| "git 自动化" | 想用脚本替代手动 Git 命令 | 进入本 Skill 流程 |
| "仓库脚本" | 有批量仓库操作需求 | 进入本 Skill 流程 |
| "自动化工作流" | 需要固定流程的重复操作 | 进入本 Skill 流程 |
| "git 批处理" | 多个文件或多个仓库的批量操作 | 进入本 Skill 流程 |
| "git 批量操作" | 同义词场景 | 进入本 Skill 流程 |
| "仓库维护脚本" | 日常维护类脚本需求 | 进入本 Skill 流程 |

---

## 三、标准操作流程

### 前置条件

| 条件 | 检查项 | 通过标准 |
|------|--------|----------|
| 环境 | Python 3.6+ 或 Bash 4.0+ | 命令行执行 `python3 --version` 或 `bash --version` 确认 |
| 目录 | 待处理文件已集中放置 | 所有文件在同一目录下，命名规律一致 |
| 备份 | 原始文件已备份 | 复制一份到 `backup_时间戳` 目录 |
| 权限 | 对目标仓库有读写权限 | 执行 `git ls-remote` 验证远程访问 |

### 执行步骤

**第一步：准备输入清单**

```bash
# 列出当前目录下所有待处理文件
ls -la *.md *.py *.sh 2>/dev/null

# 或生成文件清单到文本文件
find . -maxdepth 1 -type f -name "*.txt" > file_list.txt
```

**第二步：单样本试运行**

选取一个代表性文件，执行目标操作：

```bash
# 示例：批量添加文件头注释（先试一个）
python3 -c "
import sys
with open(sys.argv[1], 'r') as f:
    content = f.read()
with open(sys.argv[1], 'w') as f:
    f.write('# 自动生成注释\n' + content)
" sample_file.txt
```

核对输出结果是否符合预期格式。

**第三步：全量执行**

确认无误后，对清单内所有文件执行：

```bash
# 遍历文件清单执行操作
while read file; do
    python3 -c "
import sys
with open(sys.argv[1], 'r') as f:
    content = f.read()
with open(sys.argv[1], 'w') as f:
    f.write('# 自动生成注释\n' + content)
" "$file"
done < file_list.txt
```

**第四步：结果校验**

```bash
# 抽查前 3 个文件确认内容正确
head -5 file1.txt file2.txt file3.txt

# 检查文件数量是否匹配
ls -la | wc -l
```

### 输出规范

| 输出项 | 格式要求 | 示例 |
|--------|----------|------|
| 操作日志 | 每步操作记录时间戳和文件名 | `[2024-01-15 10:30:00] 已处理: file1.txt` |
| 结果摘要 | 成功/失败数量统计 | `成功: 12, 失败: 1, 跳过: 2` |
| 错误报告 | 失败文件及原因 | `file13.txt: 文件不存在` |

---

## 四、置信度门控

当遇到以下情况时，**不得**编造或猜测，必须输出 `[需核实:字段]` 占位符：

| 场景 | 处理方式 |
|------|----------|
| 远程仓库地址不确定 | 输出 `[需核实:远程仓库URL]` |
| 分支名称不确定 | 输出 `[需核实:目标分支名]` |
| 文件编码格式不确定 | 输出 `[需核实:文件编码]` |
| 操作权限不确定 | 输出 `[需核实:用户权限]` |
| 依赖版本不确定 | 输出 `[需核实:依赖版本号]` |

示例：

```bash
# 不确定远程仓库地址时
git remote add origin [需核实:远程仓库URL]
```

---

## 五、错误码体系

| 错误码 | 错误描述 | 提示话术 | 修正步骤 |
|--------|----------|----------|----------|
| E001 | 文件不存在 | `文件 xxx 不存在，请检查路径` | 1. 确认文件路径 2. 检查文件名拼写 3. 重新执行 |
| E002 | 目录无权限 | `目录 xxx 无写入权限` | 1. 检查目录权限 2. 使用 `chmod` 调整 3. 或更换目录 |
| E003 | Git 未初始化 | `当前目录不是 Git 仓库` | 1. 执行 `git init` 2. 或切换到正确目录 |
| E004 | 远程连接失败 | `无法连接远程仓库，请检查网络` | 1. 检查网络连接 2. 验证远程地址 3. 检查 SSH 配置 |
| E005 | 脚本语法错误 | `脚本第 x 行存在语法错误` | 1. 查看错误行 2. 修正语法 3. 重新执行 |
| E006 | 文件编码异常 | `文件编码不是 UTF-8，无法处理` | 1. 转换文件编码 2. 或跳过该文件 |

---

## 六、常见坑与反模式

| 反模式 | 问题描述 | 正确做法 |
|--------|----------|----------|
| 直接全量执行 | 跳过试运行直接处理所有文件 | 先单样本验证，再批量执行 |
| 忽略备份 | 不保留原始文件副本 | 执行前必须备份到独立目录 |
| 硬编码路径 | 脚本中写死绝对路径 | 使用相对路径或参数化路径 |
| 无日志记录 | 操作过程不留痕迹 | 每次操作输出时间戳和操作内容 |
| 盲目使用 force | 随意使用 `--force` 参数 | 确认影响范围后再决定是否使用 |

---

## 七、渐进式学习路径

### 速查卡（30 秒上手）

```
1. 放文件 → 2. 试一个 → 3. 跑全部 → 4. 查结果
```

### 新手路径（首次使用）

1. 阅读「能力边界速查卡」了解适用范围
2. 按「标准操作流程」逐步执行
3. 遇到问题查「错误码体系」
4. 参考「常见坑与反模式」避免踩坑

### 进阶路径（熟练使用）

1. 自定义脚本参数，适配不同场景
2. 组合多个操作形成完整工作流
3. 添加异常处理和日志记录
4. 将常用流程封装为可复用函数

### 参数参考表

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `--input-dir` | 字符串 | 当前目录 | 待处理文件所在目录 |
| `--backup` | 布尔 | true | 是否创建备份 |
| `--dry-run` | 布尔 | false | 试运行模式，不实际执行 |
| `--log-file` | 字符串 | 无 | 日志输出文件路径 |
| `--pattern` | 字符串 | `*` | 文件匹配模式 |

---

## 用户协议

<!-- user-agreement-injected -->

**使用本 Skill 即表示您同意以下条款：**

1. **责任承担**：使用者自行承担使用本 Skill 产生的全部责任。包括但不限于因脚本执行导致的文件丢失、数据损坏、仓库异常等后果。
2. **禁止反向工程**：不得对本 Skill 进行反向工程、反编译、破解或试图提取底层算法。
3. **合规使用**：使用者应确保使用场景符合当地法律法规及 GitHub 服务条款。
4. **无担保声明**：本 Skill 按"现状"提供，不附带任何明示或暗示的担保。
5. **免责范围**：因使用本 Skill 造成的任何直接或间接损失，作者不承担任何责任。

---

## 许可证（License）

<!-- professional-license-embedded -->

### MIT License

Copyright (c) 2024 脚本工坊

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
