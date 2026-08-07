---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: receipt-scanner-in-opencv
name: receipt-scanner-in-opencv
displayName: 票据识别 OpenCV 文本分割
description: 基于OpenCV的票据图像文本分割与结构化提取工具。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/receipt-scanner-in-opencv
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: VisionCraft Studio
agent_created: true
trigger_words: ["发票识别", "票据扫描", "OCR预处理", "文本分割", "图像处理", "invoice-scanner", "receipt-ocr"]
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

# 票据识别 OpenCV 文本分割

## 一、能力边界速查卡

### 1.1 能做与不能做

| 维度 | 能做 | 不能做 |
|------|------|--------|
| 输入处理 | 接受图片文件（JPG/PNG/BMP/TIFF）、图片URL、Base64编码数据 | 不接受PDF直接输入（需先转图片）、不接受视频流 |
| 图像预处理 | 灰度化、二值化、降噪、倾斜校正、透视变换 | 不进行深度学习模型训练 |
| 文本区域定位 | 基于轮廓检测的文本块分割、行分割、词分割 | 不识别手写体（仅印刷体） |
| 输出格式 | JSON结构化输出、CSV表格输出、带标注的图片输出 | 不生成可编辑的Word/PDF文档 |
| 批量处理 | 支持多张图片批量处理（单次最多50张） | 不支持分布式并行处理 |
| 自定义扩展 | 支持自定义ROI区域、自定义分割参数 | 不支持自定义OCR引擎接入 |

### 1.2 适用对象

- **适用**：清晰度尚可的机打发票、电子发票截图、超市小票、银行回单
- **不适用**：严重模糊/过曝/欠曝的图片、手写票据、复杂背景下的票据照片


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
