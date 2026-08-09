---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: auto-claude-code-research-in-sleep
name: auto-claude-code-research-in-sleep
displayName: 睡眠科研 自动调研 跨模型评审
description: 轻量级Markdown技能，实现跨模型评审的自动化机器学习研究循环。
version: 1.0.1
rules_version: cpr-20260809-n251
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/auto-claude-code-research-in-sleep
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: Lin Chen
agent_created: true
trigger_words: ["auto-claude-code-research-in-sleep", "ARIS", "睡眠研究", "自动调研", "跨模型评审", "ML研究循环", "夜间研究"]

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

---

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->


# ARIS ⚔️ 睡眠自动科研助手 — SKILL.md

## 一、能力边界（一页纸速查卡）

### ✅ 能做（5项核心能力）
| 编号 | 能力 | 说明 | 输入示例 |
|------|------|------|----------|
| 1 | 数据/文件/URL 结构化转换 | 将用户提供的任意数据源解析为结构化结果 | `data.csv`、`https://arxiv.org/abs/2301.xxxx`、`notes.md` |
| 2 | 关键信息识别与保留 | 自动抽取输入中的核心实体、数值、结论 | 论文中的准确率、损失值、方法名 |
| 3 | 约定格式输出 | 按用户指定的字段结构生成结果 | JSON、Markdown 表格、摘要卡片 |
| 4 | 置信度提示 | 对不确定项标注置信度等级 | `[高置信]`、`[中置信]`、`[需核实:字段名]` |
| 5 | 批量处理与自定义格式 | 支持多文件/多URL批量处理，输出格式可定制 | 批量处理 10 篇论文摘要 |

### ❌ 不能做（明确边界）
| 编号 | 限制 | 说明 |
|------|------|------|
| 1 | 不执行代码 | 不运行 Python/Shell 脚本，仅做文本分析与结构化 |
| 2 | 不访问付费数据库 | 仅处理用户提供的公开数据或 URL 内容 |
| 3 | 不保证结果准确性 | 输出结果基于输入内容推断，不承担事实核查责任 |
| 4 | 不替代人类判断 | 最终研究决策需由用户自行确认 |
| 5 | 不支持实时交互 | 批处理模式下不进行多轮对话确认 |

### 👥 适用对象
- **机器学习研究者**：需要快速整理文献、对比实验结果
- **数据科学家**：需要将散乱数据转为结构化报告
- **技术写作者**：需要批量生成研究摘要或技术文档
- **夜间工作者**：希望在睡眠期间自动完成调研整理任务

---

## 二、触发方式

### 触发词
| 触发词 | 场景 |
|--------|------|
| `auto-claude-code-research-in-sleep` | 完整技能名，精确触发 |
| `ARIS` | 缩写触发 |
| `睡眠研究` | 中文场景触发 |
| `自动调研` | 功能触发 |
| `跨模型评审` | 特定功能触发 |
| `夜间研究` | 时间场景触发 |

### 大白话场景映射表
| 用户说（大白话） | 实际触发功能 |
|-----------------|-------------|
| "帮我把这几篇论文整理成表格" | 批量结构化转换 + 关键信息提取 |
| "我睡一觉，你帮我看看这些实验结果" | 自动解析数据文件 + 生成对比报告 |
| "这个 URL 里的内容帮我总结一下" | URL 内容抓取 + 摘要生成 |
| "把上次的结果按我给的格式重新输出" | 自定义格式输出 |
| "这些数据里哪些数字比较重要？" | 关键信息识别 + 置信度标注 |

---

## 三、标准流程

### 前置条件
| 条件 | 要求 | 缺失时的处理 |
|------|------|-------------|
| 输入数据 | 至少一个数据源（文件/URL/文本） | 返回错误码 `E1001` |
| 输出格式 | 明确指定或使用默认格式 | 使用默认 JSON 格式 |
| 权限 | 用户确认可处理输入内容 | 未确认时返回错误码 `E1002` |

### 执行步骤（分步编号）

**步骤 1：收集输入并确认格式**
1. 接收用户输入的数据源列表
2. 确认输出格式（JSON / Markdown / 自定义）
3. 确认置信度标注需求（默认开启）

**步骤 2：解析输入内容**
1. 对每个数据源执行内容提取
2. 识别关键信息（实体、数值、结论、方法）
3. 记录不确定项（信息缺失、语义模糊）

**步骤 3：按规则处理**
1. 应用结构化转换规则（见下方参数表）
2. 保留原始上下文（不截断关键信息）
3. 生成中间结果（含置信度标注）

**步骤 4：生成输出**
1. 按约定格式组装结果
2. 执行自查（字段完整性、格式正确性、置信度标注）
3. 输出最终结果

**步骤 5：二次确认（仅当存在疑问时）**
- 触发条件：关键字段缺失、数据源无法解析、格式冲突
- 处理方式：输出部分结果 + 明确疑问列表

### 输出规范

**默认输出格式（JSON）**
```json
{
  "meta": {
    "input_count": 3,
    "processed_at": "2026-08-09T22:00:00Z",
    "confidence_level": "high"
  },
  "results": [
    {
      "source": "paper_1.pdf",
      "key_findings": ["方法A在任务B上达到85%准确率"],
      "entities": {"model": "ResNet50", "dataset": "ImageNet"},
      "confidence": "high"
    }
  ],
  "uncertainties": [
    {"field": "training_time", "status": "missing", "placeholder": "[需核实:training_time]"}
  ]
}
```

**字段完整性检查表**
| 字段 | 必填 | 缺失处理 |
|------|------|----------|
| `source` | 是 | 错误码 `E2001` |
| `key_findings` | 是 | 错误码 `E2002` |
| `confidence` | 是 | 默认 `medium` |
| `entities` | 否 | 跳过，不报错 |
| `uncertainties` | 否 | 空数组 |

---

## 四、置信度门控

### 置信度等级定义
| 等级 | 定义 | 使用场景 |
|------|------|----------|
| `high` | 信息完整且明确 | 输入中直接给出数值/结论 |
| `medium` | 信息存在但需推断 | 输入中隐含信息，需上下文推断 |
| `low` | 信息模糊或冲突 | 多个数据源结果不一致 |
| `[需核实:字段名]` | 信息完全缺失 | 输入中未提及该字段 |

### 门控规则
1. **不编造原则**：任何缺失信息一律输出 `[需核实:字段名]` 占位符
2. **冲突处理**：多个数据源结果不一致时，输出所有结果并标注 `low` 置信度
3. **推断标注**：基于上下文的推断结果必须标注 `medium` 或 `low`
4. **用户确认**：当 `low` 置信度结果超过 30% 时，建议用户二次确认

### 示例
**输入**："这个模型准确率不错，但训练时间没记录"
**输出**：
```json
{
  "accuracy": {"value": "unknown", "confidence": "low", "note": "用户提到'不错'但无具体数值"},
  "training_time": {"value": "[需核实:training_time]", "confidence": "missing"}
}
```

---

## 五、错误码体系

| 错误码 | 错误描述 | 用户提示话术 | 修正步骤 |
|--------|----------|-------------|----------|
| `E1001` | 无输入数据 | "未检测到输入数据源，请提供文件、URL或文本内容" | 1. 提供至少一个数据源 2. 重新触发 |
| `E1002` | 未确认处理权限 | "请确认您有权处理这些输入内容" | 1. 明确回复"确认" 2. 重新触发 |
| `E2001` | 缺少 `source` 字段 | "结果中缺少来源标识，无法追溯" | 1. 检查输入格式 2. 确保每个数据源有唯一标识 |
| `E2002` | 缺少 `key_findings` | "未能从输入中提取关键结论" | 1. 检查输入是否包含实质性内容 2. 尝试简化输入 |
| `E3001` | 输出格式冲突 | "指定的输出格式与默认格式冲突" | 1. 明确指定一种格式 2. 使用 `format=json` 或 `format=md` |
| `E3002` | 批量处理超限 | "单次批量处理上限为 20 个数据源" | 1. 分批处理 2. 合并数据源 |
| `E4001` | URL 无法访问 | "无法访问提供的 URL，请检查链接有效性" | 1. 验证 URL 2. 提供本地文件替代 |

---

## 六、FAQ 反模式对照

### 常见坑 1：过度推断
**反模式**：输入"模型表现良好"，输出"模型准确率 90%"
**正确做法**：输出 `{"performance": "良好（用户描述）", "accuracy": "[需核实:accuracy]"}`

### 常见坑 2：忽略上下文
**反模式**：只提取数值，不保留实验条件
**正确做法**：同时输出 `{"accuracy": 85, "context": "在验证集上，batch_size=32"}`

### 常见坑 3：格式僵化
**反模式**：用户要求 Markdown，仍输出 JSON
**正确做法**：识别 `format=md` 参数，输出 Markdown 表格

### 常见坑 4：置信度缺失
**反模式**：所有结果统一标注 `high`，不区分来源质量
**正确做法**：根据数据源类型（官方文档 vs 个人笔记）差异化标注

### 常见坑 5：批量处理无进度反馈
**反模式**：处理 20 个文件时静默等待
**正确做法**：每处理 5 个文件输出一次进度提示

---

## 七、渐进式披露

### 🚀 速查卡（30秒上手）
```
1. 提供数据源（文件/URL/文本）
2. 指定输出格式（可选，默认JSON）
3. 触发技能 → 获取结构化结果
4. 检查置信度标注 → 处理 [需核实] 字段
```

### 📖 新手路径（5分钟）
1. 阅读「能力边界」了解能做什么
2. 使用「触发方式」中的场景映射找到对应功能
3. 按「标准流程」执行一次完整操作
4. 遇到问题查「错误码体系」

### 🔬 进阶路径（15分钟）
1. 深入理解「置信度门控」的推断规则
2. 自定义输出格式（参考「输出规范」的字段结构）
3. 批量处理复杂数据源（多文件+URL混合）
4. 结合「FAQ 反模式」优化输入质量

### 🧠 专家路径（30分钟+）
1. 设计自定义字段结构，适配特定研究流程
2. 建立输入模板，减少重复描述
3. 将输出结果接入下游分析工具
4. 定期复盘置信度标注的准确性，优化输入策略

---

## 八、参数速查表

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `format` | string | `json` | 输出格式：`json` / `md` / `custom` |
| `confidence` | boolean | `true` | 是否启用置信度标注 |
| `batch_size` | integer | `10` | 批量处理时每批数量（上限20） |
| `fields` | array | 默认字段 | 自定义输出字段列表 |
| `source_type` | string | `auto` | 输入类型：`file` / `url` / `text` / `auto` |
| `language` | string | `zh` | 输出语言：`zh` / `en` |

---

## 九、使用示例

### 示例 1：单文件处理
**输入**：`data/experiment_results.csv` + `format=md`
**输出**：
```markdown
| 实验编号 | 模型 | 准确率 | 置信度 |
|---------|------|--------|--------|
| EXP-01 | ResNet50 | 85.2% | high |
| EXP-02 | ViT-Base | 87.1% | high |
| EXP-03 | Swin-T | [需核实:accuracy] | missing |
```

### 示例 2：URL 批量处理
**输入**：`https://arxiv.org/abs/2301.00001` + `https://arxiv.org/abs/2301.00002`
**输出**：
```json
{
  "results": [
    {"source": "2301.00001", "title": "示例论文A", "key_findings": ["提出方法X"], "confidence": "high"},
    {"source": "2301.00002", "title": "示例论文B", "key_findings": ["改进方法Y"], "confidence": "medium"}
  ]
}
```

---

## 十、用户协议

**使用须知**
1. 本 Skill 提供的所有输出结果仅供参考，使用者需自行承担全部责任。
2. 使用者应确保输入数据的合法性和合规性，不得输入侵权、违法或敏感内容。
3. 本 Skill 的自动处理结果不构成专业建议，重要决策请结合人工判断。
4. 禁止对本 Skill 进行反向工程、破解或任何形式的未授权修改。
5. 使用者应遵守所在地法律法规及学术伦理规范。

**免责声明**
- 本 Skill 不对输出结果的准确性、完整性或适用性作任何明示或暗示的保证。
- 因使用本 Skill 产生的任何直接或间接损失，作者不承担任何责任。

<!-- user-agreement-injected -->

---

## 十一、许可证（License）

**MIT License**

```
MIT License

Copyright (c) 2026 原创作者（自持版权）

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

---

## 十二、版本记录

| 版本 | 日期 | 变更说明 |
|------|------|----------|
| 1.0.0 | 2026-08-09 | 初始版本，实现核心功能 |

---

*本 Skill 由 AI 辅助生成，仅供参考。使用前请阅读相关文档。*
