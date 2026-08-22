---
slug: gitsum
name: gitsum
displayName: Git代码管理 提交规范 仓库操作
description: 将Git操作需求转化为结构化执行方案，提供规范流程与输出。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: CodeCraft Studio
agent_created: true
trigger_words: ["gitsum", "git代码管理", "git操作", "代码提交", "仓库管理", "版本控制"]
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# GitSum 技能文档

## 一、能力边界速查卡

### 1.1 能做与不能做

| 维度 | 能做 ✅ | 不能做 ❌ |
|------|---------|-----------|
| 输入处理 | 解析用户提供的Git命令、仓库路径、文件路径、URL | 无法直接访问本地文件系统或远程仓库 |
| 信息提取 | 从用户描述中识别操作类型、目标分支、文件范围 | 无法自动推断未提及的仓库信息 |
| 流程生成 | 生成规范化的Git操作步骤与命令序列 | 不替代用户执行任何实际命令 |
| 结果输出 | 输出结构化操作方案、检查清单、回滚预案 | 不保证操作结果（依赖用户环境） |
| 批量处理 | 支持多文件/多分支场景的方案编排 | 不处理超出Git范畴的需求（如CI/CD配置） |

### 1.2 适用对象

- **适用**：需要规范化Git操作流程的开发者、需要批量处理提交任务的团队、学习Git标准流程的新手。
- **不适用**：需要直接操作远程服务器的场景、需要图形化界面交互的场景、非Git版本控制需求。

---

## 二、触发方式与场景映射

### 2.1 触发词

- 核心触发词：`gitsum`、`git代码管理`、`git操作`
- 补充触发词：`代码提交`、`仓库管理`、`版本控制`、`分支合并`

### 2.2 场景映射表

| 用户说（大白话） | 实际需求 | 技能响应 |
|------------------|----------|----------|
| "帮我把这几个文件提交一下" | 提交指定文件到当前分支 | 生成add/commit命令序列及提交信息模板 |
| "我要把dev合并到main" | 分支合并操作 | 生成merge/rebase方案及冲突处理预案 |
| "看看这个仓库的提交历史" | 查看日志 | 生成log查询命令及输出格式建议 |
| "我改乱了，想回退" | 版本回退 | 生成reset/revert方案及数据安全提示 |
| "批量处理多个仓库" | 多仓库操作 | 生成循环处理脚本框架及校验步骤 |

---

## 三、标准处理流程

### 3.1 前置条件

| 条件项 | 要求 | 缺失处理 |
|--------|------|----------|
| 仓库路径 | 用户需提供本地仓库路径或确认当前目录 | 输出 [需核实:仓库路径] 占位符 |
| 操作类型 | 明确提交/合并/回退/查询等意图 | 列出可选操作类型请用户选择 |
| 目标分支 | 涉及分支操作时需指定 | 默认使用当前分支并标注假设 |
| 文件范围 | 提交操作需明确文件列表 | 提示用户补充或默认全部改动 |

### 3.2 执行步骤

**第一步：需求解析**
1. 提取用户描述中的操作动词（提交/合并/回退/查询）
2. 识别涉及的仓库路径、分支名、文件名
3. 确认操作约束（如是否强制推送、是否需要保留历史）

**第二步：方案生成**
1. 根据操作类型选择对应命令模板
2. 填入用户提供的具体参数
3. 补充安全检查项（如`git status`预检）

**第三步：输出与确认**
1. 输出完整操作步骤清单
2. 标注每步的预期结果
3. 对不确定参数使用 `[需核实:参数名]` 标注

### 3.3 输出规范

```markdown
## 操作方案

### 操作类型
[提交/合并/回退/查询]

### 前置检查
- [ ] 仓库路径确认：[路径或占位符]
- [ ] 当前分支确认：[分支名]
- [ ] 工作区状态检查：`git status`

### 执行步骤
1. [命令1] — 预期结果：[描述]
2. [命令2] — 预期结果：[描述]

### 回滚预案
- 如步骤2失败，执行：[回滚命令]

### 置信度标注
- 参数完整性：[高/中/低]
- 需用户确认项：[列出所有占位符]
```

---

## 四、置信度门控机制

### 4.1 信息不足处理规则

| 缺失信息类型 | 处理方式 | 示例 |
|--------------|----------|------|
| 仓库路径 | 输出 `[需核实:仓库路径]` | `cd [需核实:仓库路径]` |
| 分支名称 | 默认当前分支并标注 | `git merge [需核实:目标分支]` |
| 文件列表 | 提示用户补充或使用`git add -A` | `git add [需核实:文件列表]` |
| 提交信息 | 生成模板供用户填写 | `git commit -m "[需核实:提交说明]"` |

### 4.2 禁止行为

- 不猜测用户未提及的仓库地址
- 不假设分支存在（需用户确认）
- 不编造文件路径或提交历史
- 不推荐可能造成数据丢失的命令（如`git push --force`）而不加警告

---

## 五、错误码体系

| 错误码 | 场景 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| GS-001 | 未提供仓库路径 | "请提供本地仓库路径，或确认当前目录即为目标仓库" | 1. 询问路径 2. 或建议运行`pwd`确认 |
| GS-002 | 操作类型不明确 | "请明确操作类型：提交/合并/回退/查询/其他" | 1. 列出可选类型 2. 请用户选择 |
| GS-003 | 分支信息缺失 | "涉及分支操作，请指定源分支和目标分支" | 1. 提示`git branch -a`查看 2. 请用户补充 |
| GS-004 | 文件路径无效 | "指定的文件路径不存在，请核对" | 1. 提示`ls`查看 2. 请用户修正 |
| GS-005 | 命令冲突 | "该操作可能覆盖现有改动，请确认" | 1. 提示风险 2. 建议先`git stash` |

---

## 六、FAQ 与反模式对照

### 6.1 常见坑

| 坑编号 | 常见错误做法 | 反模式示例 | 正确做法 |
|--------|--------------|------------|----------|
| F-01 | 跳过预检直接执行 | 直接`git push`而不先`git status` | 先检查工作区状态，确认无未提交改动 |
| F-02 | 合并前不备份 | 直接`git merge`无回退方案 | 先记录当前HEAD位置，准备回退命令 |
| F-03 | 提交信息模糊 | `git commit -m "fix"` | 使用规范格式：`type(scope): description` |
| F-04 | 忽略冲突可能 | 假设合并必然成功 | 准备冲突解决预案，了解`git mergetool` |
| F-05 | 批量操作无校验 | 循环执行命令不检查中间结果 | 每步执行后检查退出码和输出 |

### 6.2 反模式对照表

| 反模式 | 问题 | 替代方案 |
|--------|------|----------|
| 盲目复制命令 | 不理解命令含义，出错难排查 | 理解每条命令的作用和参数 |
| 忽略错误信息 | 看到报错就放弃 | 阅读错误信息，定位问题根源 |
| 不保留原始状态 | 操作前不记录当前状态 | 使用`git log --oneline -5`记录位置 |
| 一次性执行过多操作 | 多个操作混在一起难排查 | 分步执行，每步验证 |

---

## 七、渐进式披露路径

### 7.1 速查卡（新手路径）

1. 确认仓库路径 → 2. 明确操作类型 → 3. 获取命令序列 → 4. 执行并验证

### 7.2 进阶路径（有经验开发者）

1. 自定义命令模板
2. 批量处理脚本生成
3. 复杂分支策略（rebase vs merge）
4. 钩子脚本集成建议

### 7.3 专家路径

1. 自定义Git别名与函数
2. 工作流优化（Git Flow / Trunk Based）
3. 自动化测试集成
4. 性能优化（浅克隆、稀疏检出）

---

## 八、参数参考表

| 参数名 | 类型 | 必填 | 默认值 | 说明 |
|--------|------|------|--------|------|
| repo_path | string | 是 | 无 | 本地仓库路径 |
| operation | enum | 是 | 无 | commit/merge/revert/log/status |
| branch | string | 否 | 当前分支 | 目标分支名 |
| files | array | 否 | 全部改动 | 文件列表 |
| message | string | 条件必填 | 无 | 提交信息（commit时必填） |
| force | boolean | 否 | false | 是否允许强制操作 |

---

## 九、用户协议

<!-- user-agreement-injected -->

**使用本 Skill 即表示您同意以下条款：**

1. **责任承担**：使用者自行承担因使用本 Skill 产生的全部责任。本 Skill 提供的所有命令、流程和建议仅供参考，不构成任何形式的保证。
2. **操作风险**：Git 操作可能造成不可逆的数据变更。执行任何命令前，请确保已备份重要数据，并理解命令的完整含义。
3. **禁止反向工程**：禁止对本 Skill 文档进行反向工程、破解、篡改或用于任何商业用途。
4. **环境差异**：不同操作系统、Git 版本可能导致命令行为差异，请根据实际环境调整。
5. **免责声明**：本 Skill 不承担因操作失误、数据丢失、代码冲突等造成的任何直接或间接损失。

---

## 十、许可证（License）

<!-- professional-license-embedded -->

**MIT License**

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

---

*本 Skill 由 AI 辅助生成，仅供学习参考。使用前请阅读相关文档并自行验证命令安全性。*
