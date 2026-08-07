---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: batch-image-resize
name: batch-image-resize
displayName: 图片批处理 批量缩放 格式转换
description: 批量缩放、压缩、转换图片格式，自动处理EXIF与目录归档。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/batch-image-resize
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 像素工坊
agent_created: true
trigger_words: ["batch-image-resize", "批量缩放图片", "图片压缩", "图片格式转换", "图片批处理", "图像尺寸调整", "图片批量处理"]

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

# 批量图片尺寸调整与格式转换技能（batch-image-resize）

## 一、能力边界速查卡

### 1.1 能做什么

| 功能项 | 说明 | 典型参数示例 |
|--------|------|--------------|
| 批量缩放 | 按指定宽度/高度/百分比调整图片尺寸 | `--width 1920` 或 `--scale 50%` |
| 批量压缩 | 调整 JPEG/WebP 质量参数，减小文件体积 | `--quality 80` |
| 格式转换 | 在 JPEG、PNG、WebP、AVIF 之间互转 | `--format webp` |
| EXIF 处理 | 自动剥离或保留元数据（默认剥离） | `--keep-exif` |
| 目录归档 | 输出到独立目录，保留原始文件结构 | `--output-dir ./processed` |

### 1.2 不能做什么

- 不支持图片内容识别、裁剪、滤镜、水印等编辑操作
- 不支持动图（GIF/APNG）帧级处理
- 不支持超过 10000×10000 像素的超大图（内存限制）
- 不支持批量重命名（仅保留原文件名或加后缀）
- 不支持云端存储直传（需本地路径）

### 1.3 适用对象

- 需要为 Web 页面准备多尺寸素材的前端开发者
- 需要压缩图片以节省存储空间的运营人员
- 需要统一图片格式的文档管理者
- 需要批量处理相机照片的摄影爱好者


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
