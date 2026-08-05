---
slug: code-review-report
name: code-review-report
displayName: 代码审查 差异分析 质量报告
description: 解析代码差异，定位逻辑、安全、性能与规范问题，输出分级报告。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 独立技能工坊
agent_created: true
trigger_words: ["code-review-report","代码审查","代码评审","diff审查","变更检查","代码走查","差异检视","--selftest","--version"]
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# 代码审查 · 差异分析 · 质量报告

## 一、能力边界（一页纸速查卡）

### 1.1 能做什么

| 能力项 | 说明 | 输入要求 |
|--------|------|----------|
| 差异解析 | 解析统一 diff 格式（unified diff）的文本内容 | 纯文本 diff，或可访问的文件路径 |
| 问题定位 | 识别逻辑错误、安全漏洞、性能隐患、规范偏离 | 至少包含代码变更上下文（前后各 3-5 行） |
| 分级报告 | 按严重程度输出 P0/P1/P2/P3 四级问题清单 | 无特殊要求，自动分级 |
| 变更摘要 | 概括变更涉及的文件、函数、模块范围 | 无特殊要求，自动生成 |

### 1.2 不能做什么

| 限制项 | 说明 |
|--------|------|
| 不执行代码 | 仅做静态文本分析，不运行、不编译、不测试 |
| 不访问仓库 | 无法主动拉取 git 历史、分支信息或远程代码 |
| 不保证完整覆盖 | 无法发现所有问题，尤其是依赖运行时状态的缺陷 |
| 不替代人工评审 | 输出为辅助参考，最终判断由开发者负责 |

### 1.3 适用对象

- 日常提交前的自检
- CI 流程中的人工复核辅助
- 代码评审会议的前置准备
- 学习他人代码时的质量观察

---

## 二、触发方式

### 2.1 触发词

直接输入以下任一关键词即可激活：

- `code-review-report`
- `代码审查`
- `代码评审`
- `diff审查`
- `变更检查`
- `代码走查`
- `差异检视`

### 2.2 场景映射表

| 你的实际需求 | 你应该怎么说 | 预期结果 |
|-------------|-------------|----------|
| 刚写完代码，想自查一遍 | "帮我审查一下这段 diff" | 输出问题清单和修改建议 |
| 准备提交 PR，想提前排雷 | "代码评审，这是变更内容" | 输出分级报告，标注高风险项 |
| 收到同事的 diff，想快速了解 | "diff审查，看看有什么问题" | 输出变更摘要 + 问题清单 |
| 想确认某个改动是否安全 | "帮我看看这个改动有没有安全风险" | 重点标注安全类问题 |

---

## 三、标准流程

### 3.1 前置条件

| 条件 | 要求 | 不满足时的处理 |
|------|------|---------------|
| 输入格式 | 统一 diff 格式（`---`/`+++` 开头，`@@` 分段） | 提示"无法识别 diff 格式"，请重新提供 |
| 内容完整性 | 包含足够的上下文行（建议前后各 3 行以上） | 输出时标注 `[需核实:上下文不足]` |
| 语言类型 | 主流编程语言（Python/JS/Java/Go/C++/TS 等） | 未知语言时标注 `[需核实:语言类型]` |

### 3.2 执行步骤

1. **接收输入**：读取你粘贴的 diff 文本，或确认文件路径可访问
2. **格式校验**：检查是否为合法 unified diff 格式，若不符合则提示修正
3. **变更解析**：提取变更文件列表、变更行号、增删内容
4. **逐项分析**：对每个变更块执行四维检查（逻辑/安全/性能/规范）
5. **问题分级**：按严重程度分配 P0-P3 等级
6. **生成报告**：输出结构化 Markdown 报告

### 3.3 输出规范

报告格式如下：

```markdown
## 代码审查报告

### 变更摘要
- 涉及文件：N 个
- 变更行数：+X / -Y
- 主要变更模块：...

### 问题清单

| 编号 | 严重级别 | 文件位置 | 问题类型 | 描述 | 建议 |
|------|---------|---------|---------|------|------|
| 1 | P1 | file.py:42 | 逻辑 | 空指针风险 | 增加判空处理 |

### 修改建议
（按优先级排列的具体修改方案）
```

---

## 四、置信度门控

### 4.1 信息不足时的处理

当分析所需信息不完整时，使用 `[需核实:字段名]` 占位，不进行猜测或编造。

| 场景 | 输出示例 |
|------|---------|
| 缺少函数定义上下文 | `[需核实:is_valid() 函数定义]` |
| 不确定变量类型 | `[需核实:user_input 类型]` |
| 外部依赖未知 | `[需核实:第三方库版本]` |
| 业务规则不明确 | `[需核实:金额上限规则]` |

### 4.2 置信度分级

| 级别 | 含义 | 输出标记 |
|------|------|---------|
| 高 | 基于明确代码逻辑可判定 | 无标记 |
| 中 | 基于常见模式推断 | `[需核实:...]` |
| 低 | 仅提示可能性 | `[建议关注:...]` |

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|---------|---------|
| ERR-FMT-001 | 非 diff 格式输入 | "无法识别 diff 格式，请提供 unified diff 文本" | 重新粘贴 `git diff` 输出 |
| ERR-FMT-002 | diff 内容为空 | "未检测到变更内容" | 确认 diff 是否已生成 |
| ERR-FMT-003 | 文件路径不可访问 | "无法访问指定路径，请确认路径正确" | 检查路径或改为粘贴文本 |
| ERR-CTX-001 | 上下文不足 | "变更上下文过少，可能影响判断准确性" | 补充前后各 5 行上下文 |
| ERR-LANG-001 | 无法识别语言 | "未能识别代码语言，部分检查可能受限" | 在 diff 中注明语言类型 |
| ERR-PARSE-001 | 解析异常 | "diff 解析失败，可能存在格式损坏" | 检查 diff 是否完整复制 |

---

## 六、FAQ 反模式

### 6.1 常见坑与对照

| 常见错误做法 | 正确做法 | 说明 |
|-------------|---------|------|
| 只粘贴变更行，不带上下文 | 粘贴完整 diff（含上下文） | 缺少上下文会导致误判 |
| 一次粘贴多个不相关 diff | 分次提交，每次聚焦一个变更 | 混合分析会降低准确度 |
| 期望 AI 运行代码验证 | 明确这是静态分析 | 运行验证需自行执行测试 |
| 忽略 `[需核实]` 标记 | 补充信息后重新分析 | 这些标记是待确认项，不是结论 |
| 将报告直接作为评审结论 | 结合人工判断使用 | 报告是辅助工具，不是最终裁决 |

### 6.2 反模式对照表

| 反模式 | 问题 | 替代方案 |
|--------|------|---------|
| "帮我看看这段代码好不好" | 过于模糊，无法聚焦 | 提供具体 diff 和关注点 |
| "这个改动有没有 bug" | 期望过高，静态分析有局限 | 关注可静态识别的问题类型 |
| "直接告诉我改哪里" | 跳过分析过程，可能遗漏 | 先看报告，再讨论修改方案 |

---

## 七、渐进式披露

### 7.1 速查卡（30 秒上手）

```
1. 复制 git diff 输出
2. 粘贴到对话，输入"代码审查"
3. 查看问题清单表格
4. 对 [需核实] 项补充信息
```

### 7.2 分层次阅读路径

**新手路径（首次使用）**：
- 阅读「能力边界」→ 了解工具限制
- 阅读「触发方式」→ 学会激活
- 阅读「标准流程」→ 按步骤操作
- 遇到问题查「错误码体系」

**进阶路径（熟练用户）**：
- 关注「置信度门控」→ 理解判断依据
- 参考「FAQ 反模式」→ 避免常见错误
- 结合「输出规范」→ 定制报告格式
- 对 `[需核实]` 项主动补充 → 提高分析质量

---

## 八、使用示例

### 8.1 完整示例

**输入**：

```diff
--- a/user_service.py
+++ b/user_service.py
@@ -15,7 +15,9 @@ def get_user(user_id):
     if not user_id:
         return None
     user = db.query(User).filter(User.id == user_id).first()
-    return user
+    if user is None:
+        return None
+    return user.to_dict()
```

**输出**：

```markdown
## 代码审查报告

### 变更摘要
- 涉及文件：1 个
- 变更行数：+4 / -1
- 主要变更模块：user_service.get_user

### 问题清单

| 编号 | 严重级别 | 文件位置 | 问题类型 | 描述 | 建议 |
|------|---------|---------|---------|------|------|
| 1 | P2 | user_service.py:18 | 逻辑 | `to_dict()` 方法是否存在未确认 | [需核实:User.to_dict() 定义] |
| 2 | P3 | user_service.py:18 | 性能 | 每次调用序列化整个对象，若字段过多可能影响性能 | 考虑按需字段序列化 |

### 修改建议
1. 确认 `to_dict()` 方法已定义且覆盖所有需要返回的字段
2. 若返回字段较多，建议增加参数控制序列化字段范围
```

---

## 用户协议

使用本 Skill 即表示您同意以下条款：

1. **责任承担**：使用者自行承担全部责任。本 Skill 提供的分析结果仅供参考，不构成任何形式的保证或承诺。因使用本 Skill 产生的任何直接或间接损失，作者不承担任何责任。

2. **禁止反向工程**：不得对本 Skill 的提示词、内部逻辑、生成机制进行反向工程、破解、提取或用于训练其他模型。

3. **合规使用**：使用者应确保输入内容不违反任何法律法规、不侵犯第三方权益，并遵守所在组织的安全规范。

4. **内容自主**：本 Skill 生成的分析报告仅基于输入内容，使用者应对最终决策负责。

<!-- user-agreement-injected -->

---

## 许可证（License）

### MIT License

```
MIT License

Copyright (c) 2024 独立技能工坊

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
