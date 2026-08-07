---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: foundationmodelsocr
name: foundationmodelsocr
displayName: 票据识别 文字提取 结构化解析
description: 将票据图片或PDF转为结构化字段，含置信度标注与批量处理。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/foundationmodelsocr
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 识微匠
agent_created: true
trigger_words: ["发票识别", "PDF识别", "文字提取", "OCR", "票据解析", "结构化输出"]
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

# 票据识别与结构化解析 Skill 文档

## 一、能力边界速查卡

### 1.1 能做什么（5项）

| 序号 | 能力项 | 说明 | 适用场景示例 |
|------|--------|------|--------------|
| 1 | 多源输入解析 | 接受用户上传的图片、PDF文件或公开URL链接 | 手机拍摄的发票照片、扫描版合同PDF、网盘分享的票据链接 |
| 2 | 关键字段抽取 | 从非结构化文本/图像中定位并提取核心信息 | 发票号码、开票日期、金额、税号、商品明细 |
| 3 | 结构化格式输出 | 按约定模板生成JSON或表格格式的结果 | 财务系统导入、报销单自动填写 |
| 4 | 置信度标注 | 对每个提取字段给出可信度评分（0-1） | 模糊印章、手写备注等低置信度字段的识别 |
| 5 | 批量处理与自定义格式 | 支持多文件队列处理，允许用户指定输出字段结构 | 月度报销票据批量归档、特定行业模板定制 |

### 1.2 不能做什么（5项限制）

| 序号 | 限制项 | 说明 |
|------|--------|------|
| 1 | 不处理模糊图像 | 分辨率低于150dpi或严重倾斜的图片，识别准确率无法保证 |
| 2 | 不识别手写体 | 仅支持印刷体文字识别，手写内容不在处理范围内 |
| 3 | 不提供法律效力 | 识别结果仅供业务参考，不构成任何法律证明文件 |
| 4 | 不执行跨语言翻译 | 仅识别输入文件原有语言，不做翻译处理 |
| 5 | 不存储用户数据 | 处理完成后立即丢弃原始文件，不保留任何副本 |

### 1.3 适用对象

- **财务人员**：报销单据、增值税发票的快速录入
- **行政人员**：合同扫描件、公文PDF的文字提取
- **开发者**：需要将OCR能力集成到自有系统的技术团队
- **个人用户**：日常票据整理、信息归档需求


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
