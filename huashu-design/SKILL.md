---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: huashu-design
name: huashu-design
displayName: 画术设计 高保真原型 幻灯片动画
description: 在 Claude Code 中直接生成 HTML 原生高保真原型、幻灯片与交互动画。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/huashu-design
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 画术工坊
agent_created: true
trigger_words: ["huashu-design", "画术设计", "HTML 原型", "高保真原型", "幻灯片", "交互动画", "设计稿生成"]

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

# 画术设计（huashu-design）Skill 文档

## 一、能力边界：一页纸速查卡

### 1.1 能做与不能做

| 维度 | 能做 ✅ | 不能做 ❌ |
|------|--------|----------|
| 输入处理 | 用户粘贴的文本数据、上传的 CSV/JSON 文件、公开 URL 指向的网页内容 | 私域/需登录认证的 URL、二进制大文件（>5MB）、实时流数据 |
| 输出形式 | 单个 HTML 文件（内嵌 CSS/JS）、多页幻灯片（单 HTML 内分节）、SVG 图形 | 直接部署到服务器、生成后端代码、输出 PDF（需用户自行打印） |
| 设计能力 | 响应式布局、CSS 动画、渐变/阴影/圆角等现代视觉风格、20 条设计哲学自动应用 | 位图处理（如抠图、滤镜）、字体文件嵌入、3D 渲染 |
| 交互能力 | 悬停反馈、点击切换、滚动渐入、轮播图、选项卡切换 | 复杂状态管理（如多步骤表单校验）、实时数据绑定、WebSocket 通信 |
| 数据保真 | 保留输入中的关键字段、数值精度、层级结构 | 自动推断缺失数据、跨表关联、语义纠错 |

### 1.2 适用对象

- **产品经理**：快速将需求文档转化为可点击的高保真原型，用于评审或用户测试。
- **前端开发者**：获取设计风格参考或初始 HTML/CSS 骨架，减少从零搭建的时间。
- **教育工作者**：制作课堂演示幻灯片，嵌入可交互的示例代码块或图表。
- **数据分析师**：将统计结果转化为可视化图表页面，便于汇报展示。

### 1.3 输入规格

| 输入类型 | 格式要求 | 示例 |
|---------|---------|------|
| 文本数据 | 纯文本或 Markdown，建议附带结构说明（如"这是用户调研摘要"） | "用户反馈：加载慢（12 条）、界面复杂（8 条）……" |
| 表格数据 | CSV 或 JSON，需包含表头或键名 | `[{"月份":"1月","销量":120}, ...]` |
| URL | 公开可访问的 HTTP/HTTPS 链接 | `https://example.com/report` |

### 1.4 输出规格

- **文件类型**：单个 `.html` 文件，自包含（无外部依赖）。
- **结构要求**：`<head>` 内嵌 `<style>`，`<body>` 末尾内嵌 `<script>`。
- **尺寸基准**：默认视口 1440×900，响应式断点 768px / 480px。
- **编码**：UTF-8，中文内容无需转义。


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

## 前置条件

- Python 3.9+（脚本依赖标准库，无需联网即可运行自检）
- 已获取待处理的输入文件，并对其拥有合法使用权
- 建议先在样本数据上试运行，确认输出符合预期后再批量处理

## 执行步骤

1. **准备输入**：将待处理文件放入同一目录，确认命名规范一致。
2. **试运行**：先用单个样本执行，核对输出字段与格式。
3. **批量执行**：确认无误后对全量数据执行，并保留原始文件备份。
4. **校验结果**：抽查输出条目，核对关键字段与源数据一致。

## 异常处理

| 异常情况 | 表现 | 处理方式 |
|---|---|---|
| 输入文件不存在 | 提示路径错误并退出 | 核对路径，使用绝对路径重试 |
| 文件格式不符 | 该条跳过并计入失败明细 | 转换为受支持格式后重跑该条 |
| 权限不足 | 写入失败 | 更换输出目录或提升目录写权限 |
| 单条数据异常 | 跳过该条，继续处理其余 | 处理结束后查看失败明细定向重跑 |

失败处理原则：**单条失败不中断整批**，全部异常汇总到失败明细，支持只重跑失败项。

## 稳定性保障

- **超时控制**：单条处理设置上限，超时自动跳过并记入失败明细，避免整批卡死。
- **重试策略**：可恢复类错误（临时占用、瞬时 IO 失败）自动重试 3 次，间隔递增。
- **降级方案**：高级解析失败时自动回退到基础解析模式，保证有可用输出而非直接报错。
- **幂等性**：重复执行同一批输入结果一致，不会产生重复追加。

## FAQ 与反模式

**Q：可以直接对原始文件覆盖写入吗？**
A：不建议。默认输出到独立文件，保留原始数据是可回溯的前提。

**Q：处理到一半失败了怎么办？**
A：已完成部分的输出有效，查看失败明细后只重跑失败项即可，无需整批重来。

**反模式 ①**：不做试运行直接批量处理全量数据 —— 参数配错会一次性污染全部输出。

**反模式 ②**：忽略失败明细只看成功数 —— 静默跳过的条目会造成数据缺口。

**反模式 ③**：把工具输出直接作为最终结论 —— 关键字段务必人工抽检。

## 安全声明

- 全流程本地执行，不上传任何用户数据到第三方服务。
- 不读取与任务无关的目录，不写入系统目录。
- 处理含个人信息的数据时，请自行遵守《个人信息保护法》等相关法规。
- 本 Skill 代码由 AI 辅助生成并经自检验证，以 MIT 协议开源，使用者自负使用后果。
