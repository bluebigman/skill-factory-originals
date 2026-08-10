---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: exam-question-gen
name: exam-question-gen
displayName: 试题生成 知识点出题 批量练习
description: 按知识点与难度批量生成选择题、填空题、简答题，附答案解析。
version: 1.0.2
rules_version: cpr-20260810-n301
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/exam-question-gen
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: SkillForge Studio
agent_created: true
trigger_words: ["exam-question-gen", "生成练习题", "出题", "试题生成", "批量出题", "知识点出题"]
---

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->


> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# 试题生成 Skill（exam-question-gen）

## 一、能力边界：一页纸速查卡

### 1.1 能做与不能做

| 维度 | 能做 ✅ | 不能做 ❌ |
|------|--------|----------|
| 输入处理 | 知识点列表、题型与数量要求、难度等级、自定义格式模板 | 处理图片/PDF 中的题目，无法读取外部题库文件 |
| 题型生成 | 选择题（单选/多选）、填空题、简答题 | 判断题、连线题、排序题、综合应用题 |
| 输出格式 | JSON、Markdown 两种结构化格式 | 其他格式（如 XML、CSV）需用户自定义模板 |
| 答案解析 | 每题附答案、解析、知识点标签 | 自动评估用户作答、生成分数报告 |
| 批量处理 | 单次最多 50 道题，支持多知识点混合 | 超过 50 道需分批调用 |
| 置信度处理 | 对不确定内容标注 `[需核实:字段]` 占位 | 编造不存在的知识点或答案 |

### 1.2 适用对象

- **教师/培训师**：快速生成课堂练习、课后作业
- **学生/自学者**：按知识点自测，检验掌握程度
- **内容创作者**：为文章、课程配套生成练习题
- **企业培训部门**：批量生成岗位知识考核题

### 1.3 输入输出速查

| 项目 | 说明 |
|------|------|
| 最小输入 | 至少 1 个知识点 + 1 个题型 + 1 个数量 |
| 推荐输入 | 知识点列表 + 各题型数量 + 难度分布 + 输出格式 |
| 输出文件 | `questions.json` 或 `questions.md`（自动命名） |
| 处理耗时 | 约 1-3 秒/10 道题 |

---

## 二、触发方式：场景映射表

| 触发词/短语 | 典型用户表述 | 本 Skill 响应 |
|-------------|-------------|---------------|
| `exam-question-gen` | 直接调用 Skill 名称 | 进入标准出题流程 |
| `生成练习题` | "帮我生成 10 道关于二次函数的练习题" | 解析知识点、题型、数量 |
| `出题` | "出 5 道选择题，考一下 Python 列表操作" | 按指定题型生成 |
| `批量出题` | "批量生成 30 道题，覆盖第三章全部知识点" | 多知识点批量处理 |
| `试题生成` | "生成一套期中考试模拟题" | 综合生成多题型试卷 |
| `知识点出题` | "围绕光合作用出几道填空题" | 按知识点定向出题 |

---

## 三、标准流程

### 3.1 前置条件

在调用本 Skill 前，请确认以下信息（至少满足 2 项）：

| 参数 | 是否必填 | 默认值 | 示例 |
|------|---------|--------|------|
| 知识点列表 | ✅ 必填 | 无 | `["二次函数", "一元二次方程"]` |
| 题型与数量 | ✅ 必填 | 无 | `{"选择题": 5, "填空题": 3}` |
| 难度等级 | ❌ 可选 | 中等 | `简单 / 中等 / 困难` |
| 输出格式 | ❌ 可选 | markdown | `json` 或 `markdown` |
| 自定义要求 | ❌ 可选 | 无 | "题目需结合生活场景" |

### 3.2 执行步骤

**步骤 1：解析输入内容**

- 从用户输入中提取：知识点、题型、数量、难度、格式
- 识别缺失字段，记录为待确认项

**步骤 2：确认关键信息**

- 若知识点或题型缺失，返回错误提示并附正确输入格式示例
- 若数量超过 50，提示分批处理
- 若用户指定了自定义格式，确认字段结构

**步骤 3：生成题目**

按以下规则生成：

| 题型 | 生成规则 | 字段结构 |
|------|---------|---------|
| 选择题 | 每题 4 个选项，标注正确答案 | `{type, question, options, answer, explanation, knowledge_point, difficulty, confidence}` |
| 填空题 | 每题 1-2 个空，答案明确 | `{type, question, answer, explanation, knowledge_point, difficulty, confidence}` |
| 简答题 | 每题附参考答案要点 | `{type, question, reference_answer, explanation, knowledge_point, difficulty, confidence}` |

**步骤 4：置信度标注**

- 对每个题目生成 `confidence` 字段，取值 `high / medium / low`
- 若知识点超出常见范围或答案存在歧义，标注 `[需核实:字段]` 占位

**步骤 5：输出与自查**

- 按约定格式输出完整结果
- 自查清单：
  - [ ] 字段完整性：每个题目包含全部必填字段
  - [ ] 格式正确性：JSON 可解析 / Markdown 渲染正常
  - [ ] 置信度标注：所有题目均有 confidence 字段
  - [ ] 数量核对：实际生成数量与要求一致

### 3.3 输出规范

**JSON 格式示例：**

```json
{
  "meta": {
    "generated_at": "2026-08-10T12:00:00Z",
    "total_questions": 3,
    "knowledge_points": ["二次函数"],
    "difficulty": "中等"
  },
  "questions": [
    {
      "type": "选择题",
      "question": "二次函数 y = x² - 4x + 3 的对称轴是？",
      "options": ["x = 1", "x = 2", "x = 3", "x = -2"],
      "answer": "B",
      "explanation": "对称轴公式 x = -b/(2a)，代入 a=1, b=-4 得 x = 2",
      "knowledge_point": "二次函数",
      "difficulty": "简单",
      "confidence": "high"
    }
  ]
}
```

**Markdown 格式示例：**

```markdown
# 练习题：二次函数

> 知识点：二次函数 | 难度：中等 | 共 3 题

## 一、选择题

1. 二次函数 y = x² - 4x + 3 的对称轴是？
   - A. x = 1
   - B. x = 2
   - C. x = 3
   - D. x = -2
   - **答案：B**
   - **解析：** 对称轴公式 x = -b/(2a)，代入 a=1, b=-4 得 x = 2
   - 置信度：高
```

---

## 四、置信度门控

### 4.1 置信度等级定义

| 等级 | 含义 | 使用场景 |
|------|------|---------|
| `high` | 答案确定，无歧义 | 标准知识点、公式推导明确 |
| `medium` | 答案基本确定，但可能有多种表述 | 开放性问题、需结合上下文 |
| `low` | 答案不确定，需人工核实 | 知识点超出常见范围、存在争议 |

### 4.2 占位符规则

当信息不足时，使用 `[需核实:字段名]` 占位，**严禁编造**：

| 场景 | 占位示例 |
|------|---------|
| 答案不确定 | `[需核实:答案]` |
| 知识点归属不明 | `[需核实:知识点]` |
| 难度判断存疑 | `[需核实:难度]` |
| 解析内容不完整 | `[需核实:解析]` |

### 4.3 处理流程

1. 生成题目时，若某字段置信度低于 `high`，自动标注
2. 若 `low` 置信度题目超过总量的 30%，在输出末尾附加提示：
   > 注意：本批题目中 X% 置信度较低，建议人工审核后使用。

---

## 五、错误码体系

| 错误码 | 错误描述 | 用户提示话术 | 修正步骤 |
|--------|---------|-------------|---------|
| `E001` | 缺少知识点 | "未检测到知识点信息，请提供至少一个知识点。" | 输入格式示例：`生成 5 道关于[知识点]的[题型]` |
| `E002` | 缺少题型 | "未指定题型，请选择：选择题 / 填空题 / 简答题。" | 补充题型，如：`生成 3 道选择题` |
| `E003` | 数量超限 | "单次最多生成 50 道题，当前请求 X 道。" | 拆分为多次请求，或减少数量 |
| `E004` | 格式不支持 | "仅支持 JSON 和 Markdown 两种输出格式。" | 重新指定格式为 `json` 或 `markdown` |
| `E005` | 输入无法解析 | "无法从输入中识别有效信息，请检查格式。" | 参考标准输入格式重新描述 |
| `E006` | 知识点过偏 | "该知识点超出常见范围，生成结果置信度可能较低。" | 确认是否继续，或更换知识点表述 |

---

## 六、FAQ 反模式

### 6.1 常见坑与正确做法

| 常见错误（反模式） | 问题说明 | 正确做法（正模式） |
|-------------------|---------|-------------------|
| ❌ "帮我出题"（无任何细节） | 缺少知识点和题型，无法生成 | ✅ "帮我出 5 道关于勾股定理的选择题" |
| ❌ "生成 100 道题" | 超出单次处理上限 | ✅ 分批请求，每批 ≤ 50 道 |
| ❌ 要求生成判断题 | 本 Skill 不支持判断题 | ✅ 改用选择题或填空题替代 |
| ❌ 输入包含图片中的题目 | 无法解析图片内容 | ✅ 将题目文字复制粘贴为文本输入 |
| ❌ 要求"保证不重复" | 无法绝对保证题目不重复 | ✅ 可指定知识点范围缩小重复概率 |

### 6.2 反模式对照表

| 反模式 | 后果 | 正确做法 |
|--------|------|---------|
| 编造不确定的答案 | 输出错误内容，误导用户 | 使用 `[需核实:答案]` 占位 |
| 忽略置信度标注 | 用户无法判断题目可靠性 | 始终输出 `confidence` 字段 |
| 超出能力范围硬生成 | 质量低下，用户不满 | 明确告知能力边界，建议替代方案 |
| 不校验输出格式 | 用户无法直接使用 | 输出前执行自查清单 |

---

## 七、渐进式披露：分层次阅读路径

### 7.1 速查卡（30 秒上手）

```
输入格式：知识点 + 题型 + 数量
示例：生成 5 道关于二次函数的选择题，难度中等，输出 markdown
输出：questions.md（含答案与解析）
```

### 7.2 新手路径（首次使用）

1. 阅读「能力边界」了解支持范围
2. 参考「触发方式」中的示例表述发起请求
3. 收到输出后，检查 `confidence` 字段，对低置信度题目人工复核
4. 遇到错误时，对照「错误码体系」修正输入

### 7.3 进阶路径（熟练用户）

1. 自定义输出格式：在输入中附加字段结构要求
2. 批量多知识点混合出题：提供知识点列表，指定各知识点题量
3. 结合自定义要求：如"题目需结合生活场景""选项需包含干扰项"
4. 对生成结果进行二次编辑：修改题目表述、调整难度、补充解析

---

## 八、用户协议

<!-- user-agreement-injected -->

**使用本 Skill 即表示您同意以下条款：**

1. **责任承担**：使用者自行承担全部责任。本 Skill 生成的题目、答案及解析仅供参考，使用者应对其内容进行审核，确保准确性和适用性后方可用于教学、考核或其他用途。因使用本 Skill 产生的任何直接或间接损失，Skill 作者不承担任何责任。

2. **禁止反向工程**：使用者不得对本 Skill 的底层逻辑、提示词结构、生成算法进行反向工程、破解、提取或二次分发。本 Skill 仅供个人或组织在合法范围内使用。

3. **内容合规**：使用者不得利用本 Skill 生成违反法律法规、公序良俗或侵犯第三方权益的内容。如因使用者输入内容或使用方式引发纠纷，由使用者自行解决并承担责任。

4. **无担保声明**：本 Skill 按"现状"提供，不附带任何明示或暗示的担保，包括但不限于适销性、特定用途适用性和非侵权性。

---

## 九、许可证（License）

<!-- professional-license-embedded -->

**MIT License**

Copyright (c) 2026 SkillForge Studio

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

*本 Skill 由 AI 辅助生成，仅供学习参考。使用前请阅读上述协议与许可证全文。*
