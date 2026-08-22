---
slug: docspect
name: docspect
displayName: 合同审阅 风险标注 摘要生成
description: 面向合同文本的规范化审阅与风险标注，输出结构化摘要与提示清单。
version: 1.0.0
license: MIT
source_project: original
source_url: ""
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 合同智审工坊
agent_created: true
trigger_words: ["合同审查", "合同分析", "条款审阅", "风险提示", "合同摘要", "合同体检", "条款核查"]
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# docspect — 合同文本审阅与风险标注 Skill

## 一、能力边界（一页纸速查卡）

### 1.1 能做什么

| 能力项 | 说明 | 输出形态 |
|--------|------|----------|
| 条款拆解 | 将合同按章节/条款拆分为独立单元 | 条款编号 + 条款标题 |
| 风险标注 | 识别付款、违约、保密、管辖等高风险条款 | 风险等级 + 风险描述 |
| 摘要生成 | 提炼合同核心要素（当事人、标的、金额、期限） | 结构化摘要表 |
| 提示清单 | 列出需人工复核的疑点与缺失项 | 待办清单 |

### 1.2 不能做什么

| 限制项 | 说明 |
|--------|------|
| 不提供法律意见 | 本 Skill 仅做文本层面的结构化梳理，不构成法律建议 |
| 不判断合同效力 | 不评估合同是否成立、生效或可撤销 |
| 不替代人工审阅 | 输出结果需由具备资质的专业人员复核确认 |
| 不处理扫描件 | 仅支持可复制文本的电子文档（.txt/.md/.docx 纯文本部分） |

### 1.3 适用对象

- 企业法务、合规岗的合同初审辅助
- 合同管理人员的归档前检查
- 业务人员的合同要点速读

---

## 二、触发方式与场景映射

### 2.1 触发词

直接使用以下任一短语即可激活：

`合同审查`、`合同分析`、`条款审阅`、`风险提示`、`合同摘要`、`合同体检`、`条款核查`

### 2.2 场景映射表

| 你说的话（大白话） | Skill 实际动作 |
|-------------------|----------------|
| "帮我把这份合同过一遍" | 执行条款拆解 + 风险标注 |
| "这合同有啥坑？" | 输出高风险条款清单 |
| "给我讲讲这合同主要说啥" | 生成结构化摘要 |
| "这合同缺啥没？" | 输出缺失项提示清单 |
| "这几份合同都帮我看看" | 批量执行（需先单样本试运行） |

---

## 三、标准流程

### 3.1 前置条件

| 条件项 | 要求 |
|--------|------|
| 文件格式 | .txt / .md / .docx（仅提取纯文本） |
| 文件位置 | 与 Skill 运行目录一致 |
| 命名规范 | 建议 `合同名称_日期` 格式，便于批量识别 |
| 备份要求 | 执行前保留原始文件副本 |

### 3.2 执行步骤

**Step 1 — 输入确认**

确认待处理文件已就位，检查命名是否规范。若为批量任务，先确认文件清单。

**Step 2 — 单样本试运行**

选取 1 份代表性文件执行，核对输出字段是否完整、格式是否符合预期。

**Step 3 — 批量执行**

试运行无误后，对全量文件执行。每份文件独立输出，不交叉污染。

**Step 4 — 结果校验**

抽查 20% 输出条目，核对以下字段与源数据一致性：

- 条款编号是否对应原文
- 风险等级是否与描述匹配
- 摘要金额/日期是否与原文一致

### 3.3 输出规范

每份合同输出包含三个部分：

```
【合同摘要】
- 当事人：甲方/乙方名称
- 标的：合同核心标的物/服务
- 金额：合同总金额（若明确）
- 期限：合同有效期起止

【风险标注清单】
| 条款编号 | 条款标题 | 风险等级 | 风险描述 |
|----------|----------|----------|----------|
| 第X条 | 付款方式 | 高 | 预付款比例过高，无履约担保 |

【待办提示】
- [ ] 第X条缺少违约金计算方式
- [ ] 保密条款未约定期限
```

---

## 四、置信度门控

当遇到以下情况，输出 `[需核实:字段名]` 占位符，**不编造**：

| 场景 | 占位示例 |
|------|----------|
| 金额数字模糊（如"约""左右"） | `[需核实:合同总金额]` |
| 日期缺失或仅写"合同签订后X日" | `[需核实:付款截止日]` |
| 当事人名称不完整 | `[需核实:乙方全称]` |
| 条款引用跳转（如"见第X条"但该条不存在） | `[需核实:条款引用有效性]` |

**规则**：宁可留空标注，不可猜测填充。

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| E001 | 文件未找到 | "未在指定目录找到匹配文件，请确认文件名与路径" | 检查文件是否就位，重新输入文件名 |
| E002 | 文本提取失败 | "无法从该文件提取纯文本，可能为扫描件或加密文档" | 转换为可复制文本格式后重试 |
| E003 | 条款拆分异常 | "条款编号识别中断，请检查原文是否包含连续编号" | 手动标注条款边界后重新执行 |
| E004 | 批量任务中断 | "第N份文件处理失败，已跳过，其余文件正常输出" | 单独处理失败文件，排查格式问题 |
| E005 | 输出字段缺失 | "摘要中金额字段为空，原文未明确标注" | 按置信度门控规则补充占位符 |

---

## 六、FAQ 反模式对照

| 常见坑 | 反模式（错误做法） | 正确做法 |
|--------|-------------------|----------|
| 过度解读 | 对模糊条款强行给出"合理"解释 | 标注 `[需核实]` 并列入待办清单 |
| 遗漏上下文 | 只看单一条款，忽略合同整体定义 | 先读"定义与解释"章节再逐条分析 |
| 风险等级随意 | 所有条款都标"高"风险 | 按明确标准分级：金额/期限/违约后果 |
| 批量不试跑 | 直接全量执行导致错误扩散 | 严格按标准流程先单样本验证 |
| 输出无复核 | 直接采信 AI 输出 | 人工抽查关键字段，确认与原文一致 |

---

## 七、渐进式披露

### 7.1 速查卡（30 秒上手）

```
1. 放文件 → 2. 说"合同审查" → 3. 拿结果（摘要+风险+待办）
```

### 7.2 新手路径（首次使用）

1. 阅读本 Skill 的"能力边界"章节
2. 准备 1 份测试合同，按标准流程执行
3. 对照"输出规范"核对结果格式
4. 查阅"FAQ 反模式"避免常见错误

### 7.3 进阶路径（熟练使用）

1. 掌握"置信度门控"规则，理解占位符含义
2. 熟悉"错误码体系"，能独立排查问题
3. 自定义风险分级标准，适配不同合同类型
4. 建立批量执行规范，提升处理效率

---

## 八、用户协议

使用本 Skill 即表示您同意以下条款：

1. **责任承担**：使用者自行承担全部责任。本 Skill 输出内容仅供参考，不构成任何形式的法律意见或合同效力判断。因使用本 Skill 产生的任何直接或间接损失，Skill 作者与发布者不承担任何责任。
2. **禁止反向工程**：不得对本 Skill 的提示词结构、内部逻辑进行逆向拆解、复制或再分发用于商业用途。
3. **合规使用**：使用者应确保输入合同文本的合法获取与使用，遵守适用的数据保护法律法规。

<!-- user-agreement-injected -->

---

## 九、许可证（License）

本 Skill 采用 MIT 许可证发布：

```
MIT License

Copyright (c) 2024 合同智审工坊

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
