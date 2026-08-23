---
slug: claude-code-reviewer
name: claude-code-reviewer
displayName: 代码审查 风险标注 变更评审
description: 将代码或补丁转为结构化审查报告，标注风险等级与置信度，辅助人工决策。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: CodeReviewLab
agent_created: true
trigger_words: ["代码审查", "code review", "代码走查", "补丁检查", "变更评审", "代码检视", "diff检查"]
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# 代码审查 Skill 使用指南

## 一、能力边界（一页纸速查卡）

### 能做
| 能力项 | 说明 | 示例 |
|--------|------|------|
| 格式解析 | 识别统一格式的代码文件或补丁文件 | `.patch`、`.diff`、统一格式文本 |
| 字段提取 | 从变更中提取文件路径、变更行、函数名等关键信息 | 提取 `src/utils.ts` 中第 42 行变更 |
| 风险分级 | 对每个变更点标注风险等级（高/中/低） | 未处理空指针 → 高风险 |
| 置信度标注 | 对每条审查结论给出置信度百分比 | 置信度 85% |
| 批量处理 | 对同一目录下多个文件依次执行审查 | 一次处理 20 个补丁文件 |
| 失败追踪 | 输出处理失败的条目及原因 | 文件格式无法解析 → 记录错误码 |

### 不能做
| 限制项 | 说明 |
|--------|------|
| 不替代人工决策 | 最终是否合入代码由开发者判断 |
| 不执行代码 | 仅做静态分析，不运行被测代码 |
| 不处理非标准格式 | 仅支持规格中约定的输入格式 |
| 不保证发现所有缺陷 | 审查结果受输入质量影响 |

### 适用对象
- 需要快速了解变更影响的开发者
- 进行代码评审的团队负责人
- 需要留档审查记录的合规人员

---

## 二、触发方式

### 触发词
直接使用以下任一短语即可激活本 Skill：
- `代码审查`
- `code review`
- `代码走查`
- `补丁检查`
- `变更评审`
- `代码检视`
- `diff检查`

### 场景映射表
| 使用场景 | 大白话说法 | 触发词示例 |
|----------|-----------|-----------|
| 提交 PR 前自查 | "帮我看看这次改动有没有问题" | 代码审查 + 文件路径 |
| 评审他人补丁 | "这个补丁风险大不大" | 补丁检查 + 补丁文件 |
| 批量检查多个变更 | "把这几个文件都过一遍" | 代码走查 + 目录路径 |
| 记录审查过程 | "出个报告留档" | 变更评审 + 输出格式要求 |

---

## 三、标准流程

### 前置条件
1. 待审查文件已保存为统一格式（`.patch`、`.diff` 或纯文本 diff）
2. 文件命名规范一致（如 `change_001.patch`、`change_002.patch`）
3. 确认输入文件编码为 UTF-8（避免乱码导致解析失败）

### 执行步骤
1. **准备输入**
   - 将待处理文件放入同一目录
   - 检查文件命名是否符合约定（如 `*.patch` 后缀）
   - 如有必要，先复制原始文件到备份目录

2. **试运行**
   - 选取单个样本文件执行审查
   - 核对输出字段是否完整（文件路径、变更行、风险等级、置信度）
   - 确认格式符合预期后再继续

3. **批量执行**
   - 对目录下全部文件依次执行审查
   - 保留原始文件备份（不覆盖源文件）
   - 输出结果按文件逐一生成报告

4. **校验结果**
   - 抽查 3-5 条输出记录
   - 核对关键字段（如文件路径、变更行号）与源数据一致
   - 确认无遗漏或错误条目

### 输出规范
输出为结构化 Markdown 报告，每个变更点包含以下字段：

| 字段 | 说明 | 示例 |
|------|------|------|
| `file` | 变更文件路径 | `src/auth/login.ts` |
| `line` | 变更行号 | `42` |
| `change_type` | 变更类型（新增/删除/修改） | `modified` |
| `risk_level` | 风险等级（high/medium/low） | `high` |
| `confidence` | 置信度百分比 | `85%` |
| `summary` | 变更摘要 | `新增空指针检查逻辑` |
| `suggestion` | 改进建议 | `建议补充单元测试覆盖该分支` |

---

## 四、置信度门控

当输入信息不足以支撑明确结论时，遵循以下规则：

1. **不编造结论**：无法判断时输出 `[需核实:字段名]` 占位符
2. **标注缺失信息**：在报告中明确列出需要补充的信息项
3. **降低置信度**：信息不完整时，置信度上限为 60%

示例：
```
- file: src/utils/parser.ts
- line: 87
- risk_level: [需核实:risk_level]  # 无法判断变更影响范围
- confidence: 45%
- summary: 修改了正则表达式匹配逻辑
- suggestion: 需确认该变更是否影响其他调用方
```

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| `E001` | 文件格式无法解析 | "输入文件不是有效的 diff 格式" | 检查文件是否为统一格式，转换为 `.patch` 后重试 |
| `E002` | 文件编码不支持 | "文件编码不是 UTF-8" | 使用文本编辑器转换编码为 UTF-8 |
| `E003` | 文件路径不存在 | "指定的文件或目录不存在" | 核对路径是否正确，确认文件已保存 |
| `E004` | 变更行号越界 | "变更行号超出文件范围" | 检查源文件是否被修改过，重新生成 diff |
| `E005` | 批量处理中断 | "第 N 个文件处理失败，已跳过" | 查看错误明细，单独处理失败文件 |

---

## 六、FAQ 反模式

### 常见坑 1：输入格式不统一
- **反模式**：混用不同格式的 diff 文件（如 git diff 与 svn diff）
- **正确做法**：统一转换为标准 unified diff 格式后再提交审查

### 常见坑 2：忽略置信度标注
- **反模式**：直接采信所有审查结论，不关注置信度
- **正确做法**：置信度低于 70% 的条目需人工复核

### 常见坑 3：覆盖原始文件
- **反模式**：审查过程中修改了原始文件
- **正确做法**：始终保留原始文件备份，审查输出单独保存

### 常见坑 4：批量执行前不试运行
- **反模式**：直接对全量文件执行，发现格式错误后返工
- **正确做法**：先用单个样本验证输出格式，再批量执行

### 常见坑 5：忽略错误码
- **反模式**：遇到错误码后不处理，直接跳过
- **正确做法**：记录错误码并逐一排查，确保所有文件处理完成

---

## 七、渐进式披露

### 速查卡（30 秒上手）
1. 文件放同一目录 → 2. 试运行单个 → 3. 批量执行 → 4. 校验结果

### 新手路径（首次使用）
1. 阅读「能力边界」了解适用范围
2. 按「标准流程」从试运行开始
3. 遇到问题查「错误码体系」
4. 阅读「FAQ 反模式」避免常见错误

### 进阶路径（熟练使用）
1. 自定义输出格式（需修改配置）
2. 结合 CI/CD 流程自动化触发审查
3. 根据历史审查结果优化风险判断规则
4. 将审查报告接入团队知识库

---

## 用户协议

使用本 Skill 即表示您同意以下条款：

1. **责任承担**：使用者自行承担因使用本 Skill 产生的全部责任。本 Skill 提供的审查结果仅供参考，不构成任何形式的保证或承诺。
2. **禁止反向工程**：不得对本 Skill 进行反向工程、反编译、破解或试图提取源代码。
3. **合规使用**：使用者应确保使用场景符合当地法律法规及所在组织的政策要求。
4. **无担保声明**：本 Skill 按"原样"提供，不附带任何明示或暗示的担保，包括但不限于适销性、特定用途适用性和非侵权保证。

<!-- user-agreement-injected -->

---

## 许可证（License）

### MIT License

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

<!-- professional-license-embedded -->
