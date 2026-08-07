---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: layoutlmv3-fine-tuning
name: layoutlmv3-fine-tuning
displayName: 票据解析 版面识别 字段抽取
description: 从发票与PDF中抽取结构化字段，输出JSON并标注置信度。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/layoutlmv3-fine-tuning
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 墨斗研习社
agent_created: true
trigger_words: ["发票识别", "票据解析", "版面分析", "字段抽取", "OCR结构化", "invoice parsing"]
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

# LayoutLMv3 票据字段抽取 Skill 文档

## 一、能力边界速查卡

本 Skill 面向**票据/文档结构化抽取**场景，核心任务是将非结构化的版面信息（扫描件、PDF、图片）转化为带置信度标注的 JSON 结构。

### 1.1 能做与不能做

| 维度 | 能做 ✅ | 不能做 ❌ |
|------|--------|----------|
| 输入 | 图片文件（PNG/JPG/JPEG）、PDF 文件、可访问的 URL 直链 | 加密 PDF、超过 20MB 的文件、无文字层的纯手写扫描件（需先做 OCR 预处理） |
| 处理 | 版面检测、文本定位、字段语义映射、键值对抽取 | 跨页表格合并、签名笔迹鉴定、发票真伪核验 |
| 输出 | 结构化 JSON、字段置信度、批量结果打包 | 生成可视化标注图、导出 Excel 报表（需另行配置） |
| 交互 | 单文件处理、批量目录处理、自定义字段映射规则 | 实时流式识别、多轮对话式修正（仅支持单次提交） |

### 1.2 适用对象

- **直接适用**：财务报销单据、采购订单、物流运单、增值税发票（专票/普票）、银行回单
- **间接适用**：名片、身份证、营业执照（需调整字段映射表）
- **不适用**：手写笔记、艺术字体海报、低分辨率截图（< 300 DPI）


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
