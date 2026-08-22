---
slug: agent-workflow-kit
name: agent-workflow-kit
displayName: 工作流体检 风险评分 质量门禁
description: 面向AI辅助软件项目的结构化评估工具，支持多维度风险评分与置信度门控，输出JSON/Markdown报告。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: FlowForge Studio
agent_created: true
trigger_words: ["agent-workflow-kit", "工作流质量评估", "风险评分", "置信度门控", "AI辅助项目评估", "工作流体检", "质量门禁", "风险量化"]
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# agent-workflow-kit — 工作流体检与风险评分工具

本 Skill 提供一套面向 AI 辅助软件项目的结构化评估方案。它接收描述项目工作流的 JSON 数据，从多个维度计算质量得分，识别风险点，并生成可供人读或机器解析的报告。核心设计原则是：**数据不足时不猜测，信息存疑时显式标注**。

---

## 一、能力边界（速查卡）

### 1.1 这个工具能做什么

| 能力项 | 说明 |
|--------|------|
| 多维度评分 | 对输入的工作流数据，从至少 2 个维度（如步骤完整性、资源分配、风险暴露等）进行量化打分 |
| 风险等级判定 | 根据综合得分，输出 `low` / `medium` / `high` / `critical` 四个风险等级 |
| 置信度门控 | 当输入数据缺少关键字段时，输出 `[需核实:字段名]` 占位符，而非编造数值 |
| 双格式报告 | 同时生成 JSON（机器可读）和 Markdown（人读友好）两种报告 |
| 自检模式 | 通过 `--selftest` 参数验证工具自身安装是否正常 |

### 1.2 这个工具不能做什么

| 限制项 | 说明 |
|--------|------|
| 不能评估少于 2 个维度的数据 | 输入数据维度不足时，直接拒绝评估并返回错误码 `E_DIMENSION_INSUFFICIENT` |
| 不能处理关键字段缺失的数据 | `steps`、`project` 等关键字段缺失时，返回错误码 `E_MISSING_FIELD` |
| 不能评估空对象 | 数据格式合法但内容为空对象 `{}` 时，返回错误码 `E_EMPTY_PAYLOAD` |
| 不能修改项目代码 | 本工具只做评估分析，不提供修复建议的具体代码实现 |
| 不能预测未来 | 评分基于当前输入数据，不构成对项目成功率的预测 |

### 1.3 适用对象

- **AI 辅助软件项目的负责人**：需要量化评估工作流健康度
- **技术管理者**：需要在 CI/CD 流水线中设置质量门禁
- **质量保障工程师**：需要结构化的工作流风险报告
- **AI 工具链集成开发者**：需要将评估结果接入自动化流程

---

## 二、触发方式

### 2.1 触发词

当用户输入包含以下任一关键词时，本 Skill 应被激活：

| 触发词 | 场景示例 |
|--------|----------|
| agent-workflow-kit | "用 agent-workflow-kit 评估一下这个项目" |
| 工作流质量评估 | "帮我做一次工作流质量评估" |
| 风险评分 | "给这个工作流打个风险分" |
| 置信度门控 | "这个数据不全，走置信度门控流程" |
| AI辅助项目评估 | "评估一下我们 AI 辅助开发的项目" |
| 工作流体检 | "给项目做个体检" |
| 质量门禁 | "设置质量门禁阈值" |

### 2.2 场景映射表

| 用户实际需求 | 大白话翻译 | 本 Skill 的响应 |
|-------------|-----------|----------------|
| "看看这个项目流程健不健康" | 想要一个整体质量分数 | 运行评估，输出 overall_score 和 risk_level |
| "数据不太全，但你先看看" | 输入数据有缺失 | 启用置信度门控，标注 `[需核实:xxx]` |
| "这个结果准不准？" | 怀疑评估可靠性 | 展示置信度等级和缺失字段列表 |
| "能不能自动挡在 CI 里？" | 需要机器可读的判定结果 | 输出 JSON 格式，含 pass/fail 判定 |

---

## 三、标准流程

### 3.1 前置条件

| 条件 | 要求 |
|------|------|
| Python 环境 | Python 3.8 及以上 |
| 输入数据格式 | 合法 JSON，包含至少 2 个评估维度 |
| 关键字段 | 必须包含 `project`（项目名）和 `steps`（步骤数组） |
| 数据内容 | 非空对象，即不能是 `{}` |

### 3.2 执行步骤

**步骤 1：准备 JSON 数据**

构造包含项目信息和步骤列表的 JSON 对象。示例：

```json
{
  "project": "demo",
  "steps": [
    {"name": "需求分析", "duration_days": 3, "risk_flags": ["需求不明确"]},
    {"name": "编码实现", "duration_days": 10, "risk_flags": []},
    {"name": "测试验证", "duration_days": 5, "risk_flags": ["测试环境不稳定"]}
  ]
}
```

**步骤 2：运行评估命令**

```bash
python skill.py --data '{"project":"demo","steps":[]}'
```

**步骤 3：查看输出报告**

执行完成后，在输出目录下生成两个文件：

| 文件 | 格式 | 用途 |
|------|------|------|
| `report_<timestamp>.json` | JSON | 机器解析、CI/CD 集成 |
| `report_<timestamp>.md` | Markdown | 人工阅读、团队分享 |

**步骤 4：解读关键指标**

| 指标 | 含义 | 参考范围 |
|------|------|----------|
| `overall_score` | 综合质量得分 | 0-100，越高越好 |
| `risk_level` | 风险等级 | low / medium / high / critical |
| `confidence` | 置信度 | 0-1，低于 0.6 时建议补充数据 |
| `missing_fields` | 缺失字段列表 | 空数组表示数据完整 |

**步骤 5：处理存疑数据**

如果报告中出现 `[需核实:xxx]` 占位符，表示该字段数据缺失或不可靠。补充对应数据后重新运行评估。

### 3.3 输出规范

**JSON 报告结构：**

```json
{
  "meta": {
    "tool": "agent-workflow-kit",
    "version": "1.0.0",
    "timestamp": "2025-01-15T10:30:00Z"
  },
  "input_summary": {
    "project": "demo",
    "step_count": 3,
    "dimensions_evaluated": 4
  },
  "scores": {
    "overall_score": 72.5,
    "dimension_scores": {
      "step_completeness": 80.0,
      "resource_allocation": 65.0,
      "risk_exposure": 70.0,
      "process_consistency": 75.0
    }
  },
  "risk_assessment": {
    "risk_level": "medium",
    "top_risks": ["测试环境不稳定", "需求不明确"]
  },
  "confidence": {
    "score": 0.85,
    "missing_fields": [],
    "needs_verification": []
  }
}
```

**Markdown 报告结构：**

```markdown
# 工作流质量评估报告

## 项目信息
- 项目名称：demo
- 评估时间：2025-01-15T10:30:00Z
- 评估维度数：4

## 综合评分
- 总分：72.5 / 100
- 风险等级：medium

## 分维度得分
| 维度 | 得分 |
|------|------|
| 步骤完整性 | 80.0 |
| 资源分配 | 65.0 |
| 风险暴露 | 70.0 |
| 流程一致性 | 75.0 |

## 主要风险
1. 测试环境不稳定
2. 需求不明确

## 置信度
- 置信度得分：0.85
- 缺失字段：无
```

---

## 四、置信度门控

### 4.1 触发条件

以下任一情况触发置信度门控：

| 条件 | 说明 |
|------|------|
| 关键字段缺失 | `steps` 或 `project` 字段不存在 |
| 数据维度不足 | 可评估维度少于 2 个 |
| 字段值可疑 | 字段值超出合理范围（如负数的时长） |
| 数据格式异常 | JSON 解析成功但结构不符合预期 |

### 4.2 降级逻辑

当置信度门控触发时，工具执行以下降级策略：

1. **不编造数据**：对于缺失或可疑的字段，输出 `[需核实:字段名]` 占位符
2. **降低置信度分数**：整体置信度得分按缺失字段比例下调
3. **调整风险等级**：当置信度低于 0.5 时，风险等级强制标记为 `unknown`
4. **标注报告**：在报告头部添加警告横幅，提示数据不完整

### 4.3 处理建议

| 置信度区间 | 建议操作 |
|-----------|----------|
| 0.9 - 1.0 | 结果可直接用于决策 |
| 0.7 - 0.9 | 结果可参考，建议补充缺失字段 |
| 0.5 - 0.7 | 结果仅作初步参考，需补充数据后重跑 |
| < 0.5 | 结果不可用，必须补充数据后重跑 |

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| `E_DIMENSION_INSUFFICIENT` | 可评估维度少于 2 个 | "输入数据维度不足，至少需要 2 个可评估维度" | 补充更多维度的数据后重试 |
| `E_MISSING_FIELD` | 关键字段缺失 | "缺少关键字段：steps 或 project" | 检查 JSON 数据，补齐 `steps` 和 `project` 字段 |
| `E_EMPTY_PAYLOAD` | 数据为空对象 | "输入数据为空对象，无法执行评估" | 提供包含实际数据的 JSON 对象 |
| `E_INVALID_JSON` | JSON 解析失败 | "JSON 格式错误，请检查语法" | 使用 JSON 验证工具检查格式 |
| `E_UNKNOWN_DIMENSION` | 包含未知评估维度 | "包含无法识别的评估维度：xxx" | 移除未知维度或升级工具版本 |

---

## 六、FAQ 反模式

### 6.1 常见坑与反模式对照

| 常见坑 | 反模式示例 | 正确做法 |
|--------|-----------|----------|
| 数据不足硬跑 | 只提供项目名和 1 个步骤就运行评估 | 确保至少 2 个维度、关键字段齐全 |
| 忽略置信度提示 | 看到 `[需核实:xxx]` 但直接使用结果 | 补充数据后重新运行，确保置信度 ≥ 0.7 |
| 空对象提交 | 提交 `{}` 作为输入数据 | 提供结构完整的 JSON 对象 |
| 误读风险等级 | 将 `medium` 风险视为安全 | 结合 `top_risks` 列表具体分析风险点 |
| 重复评估不对比 | 多次评估但从不对比历史报告 | 保存历史报告，分析质量变化趋势 |

### 6.2 反模式自查清单

- [ ] 输入数据是否包含至少 2 个可评估维度？
- [ ] `steps` 和 `project` 字段是否存在且非空？
- [ ] 报告中是否有 `[需核实:xxx]` 占位符？
- [ ] 置信度得分是否 ≥ 0.7？
- [ ] 是否对比了历史评估报告？

---

## 七、渐进式披露

### 7.1 速查卡（30 秒上手）

```
1. 准备 JSON：{"project":"名字","steps":[...]}
2. 运行命令：python skill.py --data '<你的JSON>'
3. 查看报告：输出目录下 .json 和 .md 文件
4. 关注指标：overall_score、risk_level、confidence
5. 有 [需核实:xxx] → 补数据 → 重跑
```

### 7.2 新手阅读路径

**第一步**：阅读「一、能力边界」了解工具能做什么、不能做什么
**第二步**：按「三、标准流程」步骤 1-2 操作，完成第一次评估
**第三步**：对照「五、错误码体系」排查可能遇到的问题
**第四步**：阅读「六、FAQ 反模式」避免常见坑

### 7.3 进阶阅读路径

**第一步**：深入研究「四、置信度门控」的触发条件与降级逻辑
**第二步**：自定义维度权重（需修改源码中的 `dimension_weights` 字典）
**第三步**：将 JSON 输出接入 CI/CD 流水线，设置评分阈值门禁
**第四步**：结合历史报告分析项目质量变化趋势

---

## 八、参数参考

### 8.1 命令行参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `--data` | string | 是* | JSON 格式的输入数据 |
| `--selftest` | flag | 否 | 运行自检，验证工具安装 |
| `--version` | flag | 否 | 显示版本号 |
| `--output-dir` | string | 否 | 指定输出目录，默认 `./output` |
| `--threshold` | number | 否 | 设置风险门禁阈值，默认 60 |

*注：`--data` 与 `--selftest` 二选一。

### 8.2 维度权重默认值

| 维度 | 默认权重 | 说明 |
|------|----------|------|
| 步骤完整性 | 0.3 | 步骤定义是否清晰完整 |
| 资源分配 | 0.25 | 人力、时间等资源分配是否合理 |
| 风险暴露 | 0.25 | 潜在风险点的数量与严重程度 |
| 流程一致性 | 0.2 | 流程是否符合规范、前后一致 |

---

## 用户协议

<!-- user-agreement-injected -->

**1. 责任承担**

使用者自行承担因使用本 Skill 产生的全部责任。包括但不限于因评估结果不准确、遗漏、延迟或错误导致的任何直接、间接、附带或后果性损失。

**2. 禁止反向工程**

不得对本 Skill 的源码进行反向工程、反编译、破解或试图提取其核心算法（个人学习研究用途除外，但不得用于商业目的）。

**3. 无担保声明**

本 Skill 按"原样"提供，不附带任何明示或暗示的担保，包括但不限于适销性、特定用途适用性和非侵权性担保。

**4. 数据合规**

使用者确保输入数据不包含违反法律法规的内容，不包含他人隐私信息或商业机密。

**5. 协议更新**

本协议可能随时更新，更新后继续使用本 Skill 视为接受新协议。

---

## 许可证（License）

<!-- professional-license-embedded -->

**MIT License**

Copyright (c) 2025 FlowForge Studio

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
