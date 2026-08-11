---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: academic-research-skills
name: academic-research-skills
displayName: 学术研究 文献综述 论文写作 资料整理
description: 将研究资料转化为结构化成果，辅助论文写作全流程。
version: 1.0.3
rules_version: cpr-20260811-n351
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/academic-research-skills
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: LinguaForge
agent_created: true
trigger_words: ["学术研究", "文献综述", "论文写作", "research", "academic", "文献整理", "论文大纲", "资料分析"]
---

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->


> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# 学术研究技能（Academic Research Skills）

## 一、能力边界：一页纸速查卡

### 1.1 能做与不能做

| 维度 | 能做 ✅ | 不能做 ❌ |
|------|---------|-----------|
| **输入处理** | 解析 CSV、JSON、HTTP 接口返回的数据；接受用户直接粘贴的文本段落 | 无法直接访问数据库或私有系统；无法读取本地文件（需用户粘贴内容） |
| **文献整理** | 对文献条目进行去重、分类、标签化；提取关键词与主题聚类 | 无法验证文献的真实性与学术价值；无法替代数据库检索 |
| **综述生成** | 基于已有文献资料生成结构化综述框架；归纳研究脉络与争议点 | 无法凭空生成不存在的文献引用；无法判断研究质量优劣 |
| **论文辅助** | 生成论文大纲、章节结构建议、论证逻辑梳理；提供写作模板 | 无法代写完整论文；无法保证查重率或学术合规性 |
| **数据呈现** | 将结构化数据转化为表格、统计摘要、可视化建议 | 无法直接生成图表文件（仅提供描述性建议） |
| **格式适配** | 支持常见学术格式（APA、MLA、GB/T 7714）的引用格式整理 | 无法处理特殊学科领域的非标准格式 |

### 1.2 适用对象

- **适用**：本科及以上学历的论文写作者；需要快速整理文献的研究助理；需要结构化研究资料的分析人员
- **不适用**：需要真实文献检索的深度研究（本技能不联网检索）；需要专业统计分析的定量研究（建议配合 SPSS/R/Python 使用）

---

## 二、触发方式：场景映射表

| 触发词/短语 | 典型用户表述 | 本技能响应 |
|-------------|-------------|-----------|
| 学术研究 | "帮我整理这些研究资料" | 启动资料解析与结构化流程 |
| 文献综述 | "写个文献综述框架" | 生成综述结构 + 分类建议 |
| 论文写作 | "论文大纲怎么搭" | 输出章节框架与论证路径 |
| research | "Organize my research notes" | 英文输入同样支持 |
| academic | "Help me with academic writing" | 英文场景响应 |
| 文献整理 | "这些文献帮我归类" | 执行分类与标签化 |
| 论文大纲 | "给我一个论文提纲" | 生成大纲 + 写作顺序建议 |
| 资料分析 | "分析这些数据" | 输出统计摘要与可视化建议 |

---

## 三、标准流程：从输入到输出

### 3.1 前置条件

| 条件项 | 要求 | 说明 |
|--------|------|------|
| 输入格式 | CSV / JSON / HTTP URL / 纯文本 | 若为 URL，需可公开访问 |
| 数据规模 | 单次 ≤ 500 条记录 | 超出时建议分批处理 |
| 语言 | 中英文均可 | 混合语言可处理 |
| 上下文 | 需明确研究主题或目标 | 未提供时默认生成通用框架 |

### 3.2 执行步骤（分步编号）

**Step 1：输入解析与校验**
- 识别输入类型（CSV/JSON/URL/文本）
- 检查必填字段：`title`（标题）、`content`（内容）或 `data`（数据数组）
- 若信息缺失，输出 `[需核实:字段名]` 占位符

**Step 2：数据清洗与标准化**
- 去除重复条目（基于标题相似度 > 90%）
- 统一日期格式为 `YYYY-MM-DD`
- 提取关键词（基于 TF-IDF 或用户指定主题词）

**Step 3：结构化分类**
- 按主题聚类（默认 5 类，可自定义）
- 生成分类标签：`[主题A]`、`[主题B]` 等
- 输出分类统计表

**Step 4：综述/大纲生成**
- 基于分类结果生成综述框架：
  - 引言（研究背景与问题）
  - 主体（按主题分节，每节含 2-3 个论点）
  - 结论（研究缺口与展望）
- 若用户指定论文类型（如实证研究、案例分析），自动调整结构

**Step 5：输出规范**
- 输出格式：Markdown 文档
- 包含以下区块：
  - 数据概览（记录数、分类数、时间跨度）
  - 分类明细表
  - 综述框架（含占位符）
  - 下一步建议（3 条）

### 3.3 输出示例（节选）

```markdown
## 数据概览
- 总记录数：42 条
- 有效记录：40 条（2 条因缺少标题被标记）
- 时间跨度：2018-01-01 至 2024-06-30

## 分类明细
| 分类 | 数量 | 占比 | 代表关键词 |
|------|------|------|-----------|
| 机器学习 | 15 | 37.5% | 神经网络、监督学习 |
| 数据挖掘 | 12 | 30.0% | 聚类、关联规则 |
| 可视化 | 8 | 20.0% | 图表、交互设计 |
| 其他 | 5 | 12.5% | [需核实:主题] |

## 综述框架
### 1. 引言
- 研究背景：[需核实:领域现状]
- 核心问题：如何提升[需核实:具体问题]的效率？

### 2. 主体
#### 2.1 机器学习方法
- 论点1：...
- 论点2：...

## 下一步建议
1. 补充[需核实:缺失主题]的文献资料
2. 对"机器学习"分类进行子主题细分
3. 生成参考文献列表（需提供引用格式偏好）
```

---

## 四、置信度门控：不编造原则

### 4.1 占位符规则

| 场景 | 占位符 | 示例 |
|------|--------|------|
| 缺少必填字段 | `[需核实:字段名]` | `[需核实:作者]` |
| 数据冲突 | `[需核实:冲突项]` | 两条记录日期不一致 |
| 超出能力范围 | `[需核实:外部依赖]` | 需要联网检索的文献 |
| 用户意图不明 | `[需核实:目标]` | 未指定论文类型 |

### 4.2 处理原则

- **绝不虚构**：不生成不存在的文献引用、数据或结论
- **明确标注**：所有不确定信息必须使用占位符
- **主动提示**：输出末尾列出所有待核实项，引导用户补充

---

## 五、错误码体系

| 错误码 | 错误描述 | 提示话术 | 修正步骤 |
|--------|----------|----------|----------|
| E001 | 输入格式无法识别 | "无法识别输入格式，请提供 CSV、JSON 或有效 URL" | 1. 检查输入是否为纯文本；2. 若为 URL，确认可公开访问；3. 重新提交 |
| E002 | 数据为空 | "未检测到有效数据，请检查输入内容" | 1. 确认数据非空；2. 检查 CSV 分隔符是否为逗号；3. 重新上传 |
| E003 | 缺少必填字段 | "缺少标题字段，无法完成分类" | 1. 补充 `title` 字段；2. 或使用 `content` 字段替代；3. 重新提交 |
| E004 | 数据量超限 | "单次处理上限为 500 条记录，当前为 X 条" | 1. 将数据分批（每批 ≤ 500 条）；2. 或删除冗余记录；3. 重新提交 |
| E005 | 分类失败 | "无法自动分类，请提供主题关键词" | 1. 输入 2-5 个主题词；2. 或选择"手动分类"模式；3. 重新执行 |
| E006 | 综述生成失败 | "综述框架生成失败，请检查输入数据质量" | 1. 确认数据包含有效内容字段；2. 减少数据量至 200 条以内；3. 重试 |

---

## 六、FAQ 反模式对照

| 常见坑 | 反模式（错误做法） | 正确做法 |
|--------|-------------------|----------|
| **过度依赖** | 直接复制生成的综述框架作为论文正文 | 将框架作为起点，结合自身理解进行深度改写 |
| **忽视占位符** | 提交时未处理 `[需核实]` 标记 | 逐一核实并替换所有占位符后再使用 |
| **数据质量差** | 输入含大量重复或无关数据 | 先人工筛选，再提交给技能处理 |
| **忽略格式要求** | 未指定引用格式，导致输出不匹配 | 提前声明需要的引用格式（APA/MLA/GB/T 7714） |
| **超出能力范围** | 要求技能进行真实文献检索或查重 | 明确本技能仅处理已有资料，检索需使用学术数据库 |

---

## 七、渐进式披露：分层次阅读路径

### 7.1 速查卡（30 秒上手）

```
1. 输入：粘贴文本 / CSV / JSON / URL
2. 执行：自动完成清洗、分类、框架生成
3. 输出：Markdown 文档（含占位符）
4. 后续：替换占位符 → 补充文献 → 撰写正文
```

### 7.2 新手路径（首次使用）

1. 阅读「能力边界」了解适用范围
2. 准备一份 ≤ 50 条的 CSV 数据（含 `title` 和 `content` 字段）
3. 触发技能，观察输出结构
4. 根据「下一步建议」逐步完善

### 7.3 进阶路径（熟练用户）

1. 自定义分类数量与主题词
2. 使用 JSON 格式输入，包含嵌套结构
3. 结合 HTTP URL 获取实时数据
4. 将输出框架导入写作工具，进行深度扩展

---

## 八、参数配置表

| 参数名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `max_records` | int | 500 | 单次处理最大记录数 |
| `num_clusters` | int | 5 | 自动分类数量 |
| `theme_words` | list | [] | 自定义主题关键词 |
| `citation_style` | str | "APA" | 引用格式（APA/MLA/GB-T-7714） |
| `output_format` | str | "markdown" | 输出格式（markdown/json） |
| `language` | str | "zh" | 输出语言（zh/en） |

---

## 九、用户协议

<!-- user-agreement-injected -->

**使用本 Skill 即表示您同意以下条款：**

1. **责任承担**：使用者应自行承担因使用本 Skill 产生的全部责任。本 Skill 提供的所有输出仅供参考，不构成任何形式的专业建议或学术保证。
2. **禁止反向工程**：使用者不得对本 Skill 的底层逻辑、提示词结构或生成机制进行反向工程、破解、提取或二次分发。
3. **合规使用**：使用者应确保输入数据合法合规，不得包含侵犯他人知识产权、隐私权或其他合法权益的内容。
4. **输出验证**：使用者应对本 Skill 生成的所有内容进行独立验证，包括但不限于事实核查、引用准确性、学术规范性等。
5. **免责声明**：本 Skill 不对因使用或无法使用而产生的任何直接、间接、偶然或后果性损害承担责任。

---

## 十、许可证（License）

<!-- professional-license-embedded -->

**MIT License**

Copyright (c) 2024 LinguaForge

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
