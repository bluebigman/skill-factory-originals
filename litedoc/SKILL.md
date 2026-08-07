---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: litedoc
name: litedoc
displayName: 本地文档 智能解析 格式转换
description: 纯本地浏览器PDF转Markdown，数据不出设备，安全高效。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/litedoc
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 墨问匠心
agent_created: true
trigger_words: ["PDF转文档", "PDF转Markdown", "本地转换", "文档解析", "格式转换"]
---

> 📜 **用户协议（User Agreement）**
> 1. 本 Skill 仅供学习与参考用途。使用本 Skill 产生的任何结果，由使用者自行承担全部责任；本 Skill 不提供任何明示或暗示的保证。
> 2. 涉及法律、财务、税务、投资、医疗等专业决策时，请务必咨询持证专业人士。
> 3. 本代码受版权法保护，未经授权复制、反向工程或商业利用将被追究法律责任。
<!-- user-agreement-injected -->


> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# litedoc — 本地文档智能解析与格式转换 Skill

## 一、能力边界：一页纸速查卡

### 1.1 核心能力清单

| 序号 | 能力项 | 说明 | 适用场景示例 |
|------|--------|------|--------------|
| 1 | 本地文件解析 | 读取用户提供的 PDF 文件，提取文本内容 | 合同扫描件、论文、报告 |
| 2 | URL 内容抓取 | 从用户提供的网页链接中提取正文内容 | 在线文章、技术博客 |
| 3 | 结构化输出 | 将解析结果按 Markdown 格式整理输出 | 知识库整理、文档归档 |
| 4 | 关键信息识别 | 自动识别标题、列表、表格等结构化元素 | 会议纪要、产品说明 |
| 5 | 批量处理 | 支持多文件依次处理，统一输出格式 | 批量转换文档集 |

### 1.2 能力边界声明

**能做：**
- 处理文本型 PDF（含可复制文本层）
- 处理扫描版 PDF（需配合 OCR 组件，且准确率受图像质量影响）
- 识别常见排版元素（标题层级、有序/无序列表、表格、代码块）
- 保留原始文档的阅读顺序（基于文本流分析）

**不能做：**
- 无法处理加密或密码保护的 PDF 文件
- 无法还原复杂排版（如多栏混排、浮动文本框）的绝对视觉位置
- 无法识别手写内容（除非另行集成专用 OCR 模型）
- 不执行任何云端上传或远程调用，所有处理均在本地浏览器完成
- 不保证对图片型 PDF 的 100% 文字还原

### 1.3 适用对象

| 用户类型 | 典型需求 | 使用建议 |
|----------|----------|----------|
| 知识工作者 | 将 PDF 报告转为可编辑 Markdown | 直接拖拽文件到浏览器窗口 |
| 开发者 | 解析技术文档、API 手册 | 使用命令行参数 `--selftest` 验证环境 |
| 内容创作者 | 整理素材库、建立个人知识库 | 利用批量处理功能统一转换 |
| 学生 | 整理课程讲义、论文资料 | 注意扫描版需配合 OCR 组件 |


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
