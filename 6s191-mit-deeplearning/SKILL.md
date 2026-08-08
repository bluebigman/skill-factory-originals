---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: 6s191-mit-deeplearning
name: 6s191-mit-deeplearning
displayName: 深度学习课程 知识萃取 结构化笔记
description: 将MIT 6.S191课程资料转化为结构化学习笔记与知识卡片。
version: 1.0.2
rules_version: cpr-20260808-n152
rules_version: cpr-20260808-n152
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/6s191-mit-deeplearning
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: LinguaForge
agent_created: true
trigger_words:
  - "6s191-mit-deeplearning"
  - "MIT深度学习"
  - "6.S191"
  - "深度学习课程笔记"
  - "课程知识萃取"
  - "深度学习讲义整理"

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

---

> 📜 **用户协议（User Agreement）**
> 1. 本 Skill 仅供学习与参考用途。使用本 Skill 产生的任何结果，由使用者自行承担全部责任；本 Skill 不提供任何明示或暗示的保证。
> 2. 涉及法律、财务、税务、投资、医疗等专业决策时，请务必咨询持证专业人士。
> 3. 本代码受版权法保护，未经授权复制、反向工程或商业利用将被追究法律责任。
<!-- user-agreement-injected -->


> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->

# Skill：深度学习课程 知识萃取 结构化笔记

## 一、能力边界（一页纸速查卡）

### 1.1 核心能力清单

| 序号 | 能力项 | 说明 | 输入示例 | 输出示例 |
|------|--------|------|----------|----------|
| 1 | 课程资料解析 | 从讲义、视频字幕、论文链接中提取关键概念 | PDF讲义、YouTube字幕文本、课程Slides链接 | 概念清单、定义表 |
| 2 | 知识结构化 | 将零散内容组织为层级化知识树 | 一段关于反向传播的杂乱笔记 | 算法流程图 + 数学公式标注 |
| 3 | 术语表生成 | 自动提取专业术语并给出简明释义 | 课程中出现的"梯度消失" | 术语卡片（术语/定义/出处章节） |
| 4 | 学习路径规划 | 根据课程大纲生成递进式学习路线 | 课程周次安排表 | 按周拆解的学习任务清单 |
| 5 | 复习题生成 | 基于内容自动生成自测题目 | 某一讲的核心知识点 | 选择题/简答题 + 参考答案 |
| 6 | 智能洞察（高级） | 识别知识盲区、评估掌握度、推荐复习重点 | 用户自测错题记录 | 薄弱点分析报告 + 针对性复习建议 |
| 7 | 多格式导出（高级） | 将笔记转换为 Anki 卡片、Markdown 或 JSON 格式 | 结构化笔记 | Anki 导入包 / .md 文件 / .json 文件 |
| 8 | 概念对比分析（高级） | 对易混淆概念进行多维度对比 | "CNN与Transformer的区别" | 对比表格 + 适用场景建议 |
| 9 | 代码公式解读（高级） | 对课程中的关键代码片段和数学公式进行逐行解读 | 一段PyTorch训练循环代码 | 逐行注释 + 数学推导过程 |

### 1.2 明确不做的范围

| 禁止事项 | 说明 | 替代方案 |
|----------|------|----------|
| 不提供课程视频/资料下载 | 仅处理用户已提供的内容 | 引导用户自行获取官方资料 |
| 不替代原课程作业评分 | 可辅助解释题目，不判定对错 | 提供解题思路与参考方向 |
| 不生成完整课程翻译 | 仅对关键术语做中英对照 | 输出术语对照表 |
| 不提供学术不端帮助 | 不代写课程项目代码 | 提供架构建议与伪代码 |
| 不处理超出课程范围的内容 | 不回答与6.S191无关的深度学习问题 | 提示用户切换至通用AI助手 |
| 不处理未授权版权材料 | 不解析受DRM保护的付费讲义 | 提示用户提供合法获取的文本 |
| 不提供实时课程更新 | 不追踪2025年之后的新增课程内容 | 提示用户访问MIT官方课程页面 |
| 不生成可直接提交的作业答案 | 不提供完整可提交的作业代码或答案 | 提供解题思路、伪代码与参考方向 |

### 1.3 适用对象

| 用户类型 | 典型场景 | 推荐用法 |
|----------|----------|----------|
| 6.S191 在读学生 | 课前预习、课后复习、作业准备 | 使用「课程资料解析」+「复习题生成」 |
| 求职面试者 | 深度学习基础速览、概念梳理 | 使用「术语表生成」+「智能洞察」 |
| 工程师/研究员 | 快速回顾核心概念、查漏补缺 | 使用「知识结构化」+「多格式导出」 |
| 教学助理/讲师 | 准备习题课、整理答疑材料 | 使用「复习题生成」+「学习路径规划」 |
| 跨领域学习者 | 从零开始了解深度学习基础 | 使用「课程资料解析」+「概念对比分析」 |

### 1.4 参数默认值表

| 参数名 | 默认值 | 可选值 | 说明 |
|--------|--------|--------|------|
| `output_format` | `markdown` | `markdown` / `anki` / `json` | 输出笔记的格式 |
| `detail_level` | `standard` | `brief` / `standard` / `detailed` | 笔记详细程度 |
| `language` | `zh-CN` | `zh-CN` / `en-US` / `bilingual` | 输出语言 |
| `include_examples` | `true` | `true` / `false` | 是否包含代码/公式示例 |
| `max_depth` | `3` | `1` ~ `5` | 知识树最大层级深度 |
| `auto_quiz` | `false` | `true` / `false` | 是否自动附带自测题 |
| `comparison_mode` | `false` | `true` / `false` | 是否启用概念对比分析模式 |
| `code_annotation` | `false` | `true` / `false` | 是否对代码片段进行逐行注释 |

> **调整指引**：若输出过于冗长，将 `detail_level` 设为 `brief`；若需要导入 Anki，将 `output_format` 设为 `anki`；若需双语学习，将 `language` 设为 `bilingual`；若需深入理解代码，将 `code_annotation` 设为 `true`。


## 二、触发方式（Trigger Words）

### 2.1 触发词列表

| 触发词 | 用户可能说的话（大白话映射） |
|--------|------------------------------|
| 6s191-mit-deeplearning | "帮我整理6.S191的笔记" |
| MIT深度学习 | "MIT那个深度学习课讲了啥" |
| 6.S191 | "6.S191的讲义帮我总结下" |
| 深度学习课程笔记 | "把深度学习课程内容做成笔记" |
| 课程知识萃取 | "把课程内容提炼成重点" |
| 深度学习讲义整理 | "整理一下深度学习的讲义" |
| 神经网络笔记 | "神经网络这块帮我梳理下" |
| 反向传播讲解 | "反向传播到底怎么算的" |
| 深度学习面试复习 | "面试要考深度学习，帮我复习" |
| MIT课程速览 | "快速过一遍MIT课程重点" |
| 深度学习概念对比 | "CNN和Transformer有啥区别" |
| 课程代码解读 | "帮我看看这段训练代码啥意思" |

### 2.2 触发判定规则

1. 用户消息包含任一触发词 → 直接激活本 Skill
2. 用户消息包含「深度学习」+「笔记/整理/总结/复习」任一组合 → 激活本 Skill
3. 用户消息包含「6.S191」或「MIT 6.S191」 → 激活本 Skill
4. 用户消息包含「神经网络」「反向传播」「CNN」「RNN」等课程核心术语 → 激活本 Skill
5. 用户消息包含「深度学习」+「对比/区别」 → 激活本 Skill 的「概念对比分析」模式
6. 用户消息包含「课程代码」+「解读/注释」 → 激活本 Skill 的「代码公式解读」模式


## 三、标准流程（Standard Workflow）

### 3.1 流程总览


## 失败处理
- 输入不符合预期 → 返回错误说明与正确的输入格式示例
- 执行中异常 → 保留中间结果，报告失败原因与已处理进度
- 依赖缺失 → 给出安装命令并重试一次

## 前置条件
- 无特殊环境要求

## 输出
- 结构化文本结果，附处理说明


## 许可证（License）

```text
MIT License

Copyright (c) 2026 SkillForge Lab

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.
```
<!-- professional-license-embedded -->
