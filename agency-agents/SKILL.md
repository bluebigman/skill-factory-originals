---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: agency-agents
name: agency-agency-agents
displayName: 多角色任务编排 结构化交付 批量处理
description: 将任意输入转化为结构化成果，支持多角色任务编排与批量处理。
version: 1.0.2
rules_version: cpr-20260811-n351
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/agency-agents
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: Lin Chen
agent_created: true
trigger_words: ["agency-agents", "全能代理", "任务编排", "多角色协作", "结构化输出", "批量处理", "工作流调度"]

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

---

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->


# 多角色任务编排与结构化交付 Skill 文档

## 一、能力边界：一页纸速查卡

### 1.1 本 Skill 能做什么

| 能力项 | 说明 | 典型场景 |
|--------|------|----------|
| 输入解析 | 接受自然语言指令、JSON 参数、文件路径或标准输入 | 用户说"帮我整理这堆会议纪要" |
| 多角色编排 | 将复杂任务拆解为多个子任务，分配给不同角色（如分析员、撰写员、审核员） | 市场调研报告：先收集→再分析→后撰写 |
| 批量处理 | 对一组同类输入执行相同流程，输出结构化结果集 | 批量生成 50 条商品描述 |
| 结构化输出 | 统一输出为 JSON / Markdown 表格 / 分节文档 | 输出含字段名、类型、说明的规范结果 |
| 流程可配置 | 通过参数指定角色数量、任务顺序、输出格式 | 指定"先总结后翻译，输出双语对照" |

### 1.2 本 Skill 不能做什么

| 限制项 | 说明 |
|--------|------|
| 不执行外部 API 调用 | 不主动请求网络接口、数据库或第三方服务 |
| 不保证结果正确性 | 输出基于输入信息与模型推理，不承担事实核查责任 |
| 不处理二进制文件 | 仅接受文本类输入（.txt/.md/.json/.csv 等） |
| 不进行实时交互 | 单次执行，不支持多轮对话式修正（除非重新调用） |

### 1.3 适用对象

- 需要将零散信息整理为规范文档的运营人员
- 需要批量生成结构化内容的创作者
- 需要多步骤分析任务的初级数据分析师
- 希望减少重复性文案工作的团队负责人

---

## 二、触发方式与场景映射

### 2.1 触发词

- 主触发词：`agency-agents`、`全能代理`、`任务编排`
- 辅助触发词：`多角色协作`、`结构化输出`、`批量处理`、`工作流调度`

### 2.2 大白话场景映射表

| 用户说（大白话） | 触发词命中 | 实际执行内容 |
|------------------|------------|--------------|
| "帮我把这 20 条客户反馈整理成表格" | 批量处理 | 解析每条反馈 → 提取要点 → 输出 Markdown 表格 |
| "写一份竞品分析，先收集再对比" | 多角色协作 | 角色A收集 → 角色B对比 → 角色C撰写报告 |
| "把这段录音转成会议纪要" | 结构化输出 | 提取发言人、议题、结论 → 输出分节纪要 |
| "每天给我生成一份数据日报" | 任务编排 | 定义流程模板 → 每次输入数据自动执行 |

---

## 三、标准执行流程

### 3.1 前置条件

| 条件 | 要求 | 缺失时的处理 |
|------|------|--------------|
| 输入内容 | 文本格式，建议 ≤ 10000 字/批次 | 提示用户分段提交 |
| 角色配置 | 默认 3 角色（分析/执行/审核），可自定义 | 使用默认配置 |
| 输出格式 | 默认 JSON，可指定 Markdown | 使用默认格式 |

### 3.2 执行步骤（分步编号）

**Step 1：输入接收与解析**

- 读取命令行参数或交互输入
- 识别任务类型（单次/批量）、角色数量、输出格式
- 参数表：

| 参数名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `--input` | string | 必填 | 输入文本或文件路径 |
| `--roles` | int | 3 | 角色数量（1-5） |
| `--format` | string | json | 输出格式（json/markdown） |
| `--batch` | bool | false | 是否批量模式 |
| `--selftest` | bool | false | 运行自检 |
| `--version` | bool | false | 显示版本号 |

**Step 2：任务分解与角色分配**

- 将输入内容按语义切分为子任务
- 示例：输入为 10 条产品信息 → 子任务1：提取产品名称；子任务2：提取价格；子任务3：生成描述

**Step 3：逐角色执行**

- 角色A（解析员）：提取关键字段
- 角色B（执行员）：按规则处理数据
- 角色C（审核员）：检查输出完整性

**Step 4：结果合并与格式化**

- 合并各角色输出 → 按指定格式生成最终结果
- 示例输出（JSON）：

```json
{
  "task_id": "20260811-001",
  "status": "completed",
  "items": [
    {"name": "产品A", "price": 99.0, "description": "..."}
  ],
  "meta": {"roles_used": 3, "duration_ms": 1200}
}
```

**Step 5：输出与建议**

- 输出结构化结果
- 给出下一步建议（如"可继续执行：将结果导出为 CSV"）

### 3.3 输出规范

| 输出类型 | 格式要求 | 示例 |
|----------|----------|------|
| 单次任务 | JSON 对象，含 `status` 和 `data` 字段 | `{"status":"ok","data":{...}}` |
| 批量任务 | JSON 数组，每个元素含 `index` 和 `result` | `[{"index":1,"result":{...}}]` |
| 错误输出 | JSON 对象，含 `error_code` 和 `message` | `{"error_code":"E001","message":"输入为空"}` |

---

## 四、置信度门控

### 4.1 信息不足时的处理原则

当输入信息不足以生成可靠结果时，**不编造、不猜测**，使用占位符标记。

| 场景 | 处理方式 | 示例 |
|------|----------|------|
| 缺少必要字段 | 输出 `[需核实:字段名]` | 用户未提供价格 → `"price": "[需核实:price]"` |
| 数据冲突 | 输出所有候选值，标记 `[需核实:冲突项]` | 两个来源价格不同 → `"price": "[需核实:price 99 vs 109]"` |
| 超出知识范围 | 输出 `[需核实:领域知识]` | 涉及专业医疗建议 → `"advice": "[需核实:medical]"` |

### 4.2 置信度分级

| 级别 | 标记 | 适用条件 |
|------|------|----------|
| 高置信 | 无标记 | 输入信息完整且明确 |
| 中置信 | `[需核实:字段]` | 部分信息缺失或模糊 |
| 低置信 | `[需核实:整体]` | 输入严重不足，建议重新提供 |

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| E001 | 输入为空 | "未检测到输入内容，请提供文本或文件路径。" | 1. 检查参数 `--input` 是否填写 2. 确认文件存在且非空 |
| E002 | 角色数超限 | "角色数量需在 1-5 之间，当前为 N。" | 1. 修改 `--roles` 参数 2. 重新执行 |
| E003 | 格式不支持 | "仅支持 json 或 markdown 格式。" | 1. 修改 `--format` 参数 2. 重新执行 |
| E004 | 批量模式输入无效 | "批量模式需输入数组或换行分隔的文本。" | 1. 检查输入格式 2. 使用 `--batch` 时确保每行一条 |
| E005 | 内部处理超时 | "处理超时，请减少单次输入量。" | 1. 拆分输入为多个批次 2. 逐批执行 |
| E006 | 未知参数 | "检测到未知参数：X。" | 1. 使用 `--help` 查看支持参数 2. 移除无效参数 |

---

## 六、FAQ 反模式对照

| 常见坑 | 反模式（错误做法） | 正确做法 |
|--------|---------------------|----------|
| 输入过载 | 一次性提交 50000 字长文 | 分段提交，每段 ≤ 10000 字 |
| 忽略格式要求 | 要求输出 CSV 但未指定 `--format` | 明确指定 `--format markdown` 或 `--format json` |
| 角色配置混乱 | 5 个角色但任务简单，导致过度处理 | 简单任务用 1-2 个角色，复杂任务用 3-5 个 |
| 依赖幻觉数据 | 对缺失字段自行补全 | 使用 `[需核实:字段]` 标记，由用户确认 |
| 批量模式误用 | 单条输入使用 `--batch`，输出结构复杂 | 单条任务不使用 `--batch`，保持输出简洁 |

---

## 七、渐进式披露阅读路径

### 7.1 速查卡（新手必读）

1. 输入：`agency-agents --input "你的内容" --format json`
2. 输出：JSON 格式的结构化结果
3. 批量：`agency-agents --input "文件路径" --batch true`
4. 自检：`agency-agents --selftest`
5. 版本：`agency-agents --version`

### 7.2 进阶路径（有经验用户）

- 自定义角色数量：`--roles 5`
- 批量 + 自定义格式：`--batch true --format markdown`
- 错误排查：参考第五节错误码表
- 置信度处理：参考第四节门控规则

### 7.3 深度定制（开发者）

- 扩展角色逻辑：修改角色执行函数，增加自定义处理规则
- 接入外部数据源：在 Step 2 后增加数据获取环节
- 输出模板定制：修改格式化函数，支持更多输出类型

---

## 八、使用示例

### 8.1 单次任务示例

```bash
agency-agents --input "产品A 价格99元 主打便携 适合户外" --format json
```

输出：

```json
{
  "status": "ok",
  "data": {
    "name": "产品A",
    "price": 99,
    "features": ["便携", "适合户外"],
    "summary": "便携户外产品"
  }
}
```

### 8.2 批量任务示例

```bash
agency-agents --input "items.txt" --batch true --format markdown
```

`items.txt` 内容：

```
产品A 价格99元
产品B 价格159元
```

输出：

```markdown
| 序号 | 名称 | 价格 |
|------|------|------|
| 1 | 产品A | 99 |
| 2 | 产品B | 159 |
```

### 8.3 信息不足示例

```bash
agency-agents --input "产品C 价格未知 主打耐用"
```

输出：

```json
{
  "status": "ok",
  "data": {
    "name": "产品C",
    "price": "[需核实:price]",
    "features": ["耐用"]
  }
}
```

---

## 九、用户协议

<!-- user-agreement-injected -->

**使用前请仔细阅读以下条款：**

1. **责任承担**：使用者自行承担因使用本 Skill 产生的全部责任。本 Skill 提供的输出仅供参考，不构成任何专业建议（包括但不限于法律、医疗、金融建议）。因使用本 Skill 导致的任何直接或间接损失，作者不承担任何责任。

2. **禁止反向工程**：使用者不得对本 Skill 进行反向工程、反编译、破解或试图提取源代码（除非适用法律允许）。不得移除或修改本 Skill 中的任何版权声明或标记。

3. **合规使用**：使用者应确保使用本 Skill 的行为符合所在地区法律法规及平台规定。不得使用本 Skill 生成违法、侵权、诽谤或不当内容。

4. **无担保声明**：本 Skill 按"现状"提供，不附带任何明示或暗示的担保，包括但不限于适销性、特定用途适用性和非侵权性保证。

5. **协议更新**：作者保留随时修改本协议的权利，修改后的协议将在本 Skill 文档中发布并立即生效。

---

## 十、许可证（License）

<!-- professional-license-embedded -->

**MIT License**

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

---

## 十一、版本记录

| 版本 | 日期 | 变更说明 |
|------|------|----------|
| 1.0.0 | 2026-08-11 | 初始版本，实现多角色任务编排与结构化输出核心功能 |

---

*本 Skill 文档由 AI 辅助生成，旨在提供使用指导和最佳实践。使用前请阅读相关文档。*
