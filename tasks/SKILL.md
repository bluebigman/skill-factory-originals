---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: tasks
name: tasks
displayName: 任务管理 进度追踪 待办清单
description: 面向个人与团队的任务拆解、进度跟踪与交付物管理工具。
version: 1.0.1
rules_version: cpr-20260821-n626
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/tasks
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 林栖
agent_created: true
trigger_words: ["任务", "待办", "todo", "task", "进度", "计划", "清单", "工作项"]
---

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->


> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# 任务管理 Skill 文档

## 一、能力边界（一页纸速查卡）

本 Skill 专注于**任务的全生命周期管理**，从创建、拆解、排期、执行到验收归档。

| 维度 | 能做 | 不能做 |
|------|------|--------|
| 任务创建 | 支持单条/批量录入，自动提取截止时间、优先级关键词 | 无法自动从聊天记录中识别任务（需手动指定） |
| 任务拆解 | 将复杂目标拆为可执行的子任务，建议粒度控制在 2-4 小时 | 无法判断业务逻辑是否合理，仅做结构拆分 |
| 进度追踪 | 提供状态标记（未开始/进行中/阻塞/已完成）及完成率计算 | 不自动同步外部日历或项目管理工具 |
| 优先级排序 | 基于紧急程度和重要程度给出排序建议 | 不替代人工决策，最终排序需用户确认 |
| 输出格式 | 支持 Markdown 表格、清单列表、看板视图三种格式 | 不支持导出为 PDF 或图片 |

**适用对象**：个人开发者、3-10 人小团队、项目负责人。不适合需要复杂依赖关系（如甘特图）的大型项目。

## 二、触发方式

当你的输入包含以下场景时，本 Skill 会自动激活：

| 用户说（大白话） | 触发词命中 | Skill 响应 |
|-----------------|-----------|-----------|
| "帮我列一下这周要做的事" | 任务/待办 | 生成周任务清单 |
| "这个项目怎么拆解？" | 计划/拆解 | 输出任务分解结构 |
| "我现在做到哪了？" | 进度 | 展示当前进度状态 |
| "把这几件事排个优先级" | 优先级/排序 | 给出排序建议 |
| "记录一下：周五前给客户发方案" | 任务/截止 | 创建带截止日期的任务 |

**补充触发词**：工作项、行动项、任务列表、任务拆解、进度汇报

## 三、标准流程

### 前置条件

- 明确任务的目标或最终交付物
- 提供至少一个时间约束（截止日期或期望时长）
- 若为团队任务，需说明负责人

### 执行步骤

**Step 1：任务收集**
将所有待办事项以列表形式输入，每条包含：
- 任务名称（必填）
- 截止时间（可选，格式：YYYY-MM-DD 或 "下周三"）
- 优先级（可选：高/中/低 或 P0/P1/P2）
- 负责人（可选，默认"我"）

**Step 2：任务清洗与标准化**
- 去除重复项
- 合并相似任务
- 将模糊描述转化为动词开头的明确行动（如"处理邮件" → "清空收件箱，回复未读邮件"）

**Step 3：任务拆解（仅当任务复杂度高时）**
- 将超过 8 小时的工作拆为子任务
- 每个子任务有独立交付物
- 子任务数量控制在 3-7 个

**Step 4：排序与排期**
- 按紧急-重要矩阵排序
- 为每个任务分配建议时间段
- 输出排序结果供用户确认

**Step 5：输出规范**

输出包含三部分：
1. **任务总览表**（Markdown 表格）：任务名、负责人、截止时间、优先级、状态
2. **今日/本周焦点**：列出最近 3 个优先处理项
3. **风险提示**：标记可能延期或阻塞的任务

### 输出示例

```markdown
## 任务总览

| 任务名 | 负责人 | 截止时间 | 优先级 | 状态 |
|--------|--------|----------|--------|------|
| 完成API接口文档 | 张三 | 2026-09-01 | P0 | 进行中 |
| 修复登录bug | 李四 | 2026-08-28 | P1 | 未开始 |
| 客户演示准备 | 王五 | 2026-08-30 | P1 | 阻塞 |

## 本周焦点
1. 完成API接口文档（今日优先）
2. 修复登录bug（明日截止）
3. 客户演示准备（需协调资源解除阻塞）

## 风险提示
- 客户演示准备：依赖设计稿，当前设计稿未交付
```

## 四、置信度门控

当遇到以下情况时，本 Skill 不会编造信息，而是输出占位符：

| 场景 | 输出 |
|------|------|
| 用户未提供截止时间 | `[需核实:截止时间]` |
| 负责人不明确 | `[需核实:负责人]` |
| 任务描述过于模糊（无法转化为行动） | `[需核实:任务具体内容]` |
| 优先级信息缺失 | 默认按"中"处理，但会标注 `[需核实:优先级]` |

**规则**：宁可输出占位符，也不猜测。用户补充信息后，占位符自动替换。

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| T-001 | 输入为空 | "未检测到任务内容，请提供至少一条待办事项" | 重新输入任务列表 |
| T-002 | 日期格式无法解析 | "无法识别日期，请使用 YYYY-MM-DD 或自然语言（如'下周一'）" | 重新提供日期 |
| T-003 | 任务数量超限 | "单次最多处理 50 条任务，请分批输入" | 拆分输入 |
| T-004 | 优先级冲突 | "同一任务标记了多个优先级，请确认唯一值" | 指定单一优先级 |
| T-005 | 拆解失败 | "该任务无法进一步拆解，可能已是最小粒度" | 接受当前粒度或提供更多上下文 |

## 六、FAQ 反模式

### 常见坑 1：过度拆解
**反模式**：把"写周报"拆成"打开电脑→新建文档→输入标题→..."共 10 步。
**正确做法**：拆解到"可独立交付"即可，如"整理本周数据→撰写周报→发送给主管"。

### 常见坑 2：忽略依赖关系
**反模式**：所有任务并行排期，不考虑前后置关系。
**正确做法**：在输入时标注依赖（如"任务B依赖任务A完成"），排序时自动后移。

### 常见坑 3：优先级全标"高"
**反模式**：所有任务都是 P0，等于没有优先级。
**正确做法**：P0 不超过总量的 20%，其余按实际分配。

### 常见坑 4：没有缓冲时间
**反模式**：排期精确到小时，不留任何余量。
**正确做法**：每个任务预留 15-20% 缓冲时间。

### 常见坑 5：只列不做
**反模式**：生成清单后不更新状态。
**正确做法**：每次交互时同步最新状态，本 Skill 支持增量更新。

## 七、渐进式披露

### 速查卡（30 秒上手）

```
输入格式：任务名 | 截止时间 | 优先级 | 负责人
示例：完成PPT | 周五 | 高 | 我
```

### 新手路径（首次使用）

1. 阅读"能力边界"了解范围
2. 按"标准流程"Step 1 格式输入任务
3. 查看输出，确认排序是否合理
4. 下次更新时直接说"更新进度：任务X已完成"

### 进阶路径（熟练用户）

1. 使用批量输入（一次 10-20 条）
2. 利用"任务拆解"功能处理复杂项目
3. 结合"风险提示"提前识别阻塞
4. 使用增量更新语法："把任务X的截止时间改为下周二"

## 八、命令行接口

本 Skill 提供两个 CLI 参数：

| 参数 | 功能 | 使用场景 |
|------|------|----------|
| `--selftest` | 运行自检，验证 Skill 配置完整性 | 安装后验证 |
| `--version` | 输出版本号 | 确认版本 |

## 用户协议

使用本 Skill 即表示您同意以下条款：

1. **责任承担**：使用者自行承担使用本 Skill 产生的全部责任。本 Skill 提供的所有输出仅为建议，不构成任何形式的决策依据。
2. **禁止反向工程**：不得对本 Skill 的底层逻辑进行反向工程、反编译或试图提取源代码。
3. **无担保声明**：本 Skill 按"现状"提供，不附带任何明示或暗示的担保。
4. **使用限制**：不得将本 Skill 用于任何违法或侵权活动。

<!-- user-agreement-injected -->

## 许可证（License）

本 Skill 采用 MIT 许可证发布：

```
MIT License

Copyright (c) 2026 林栖

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
