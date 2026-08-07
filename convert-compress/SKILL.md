---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: convert-compress
name: convert-compress
displayName: 图片转换压缩 批量处理 格式适配
description: macOS 原生图片批量转换压缩工具，支持 20+ 格式处理与尺寸调整。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/convert-compress
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: PixelForge Studio
agent_created: true
trigger_words: ["convert-compress", "图片批量处理", "图片转换", "图片压缩", "格式转换", "批量缩放", "图像处理"]
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

# convert-compress — 图片转换压缩技能文档

## 一、能力边界（一页纸速查卡）

### 1.1 能做与不能做

| 维度 | 能做 ✅ | 不能做 ❌ |
|------|--------|----------|
| **格式转换** | 支持 20+ 常见图片格式互转（PNG、JPEG、WEBP、HEIC、TIFF、BMP、GIF、SVG 等） | 不支持 RAW 格式（CR2/NEF/ARW）的专业级色彩管理转换 |
| **压缩优化** | 按质量参数（0-100）压缩 JPEG/WEBP/HEIC，支持有损/无损模式 | 不支持视频文件压缩，不支持 GIF 动图帧级优化 |
| **尺寸调整** | 按宽/高/百分比/最长边/最短边五种模式缩放，支持保持纵横比 | 不支持画布裁剪（crop）操作，不支持旋转/翻转 |
| **批量处理** | 支持多文件拖拽批量处理，支持文件夹递归扫描 | 不支持跨设备（iCloud/外部磁盘）自动同步处理 |
| **元数据** | 保留 EXIF 基础信息（拍摄时间、设备型号） | 不支持 GPS 信息擦除、不支持版权信息写入 |

### 1.2 适用对象

- **前端开发者**：需要将设计稿导出为 WEBP 或压缩后的 JPEG 用于网页
- **内容运营**：批量压缩活动图片，适配公众号/小红书等平台尺寸要求
- **摄影爱好者**：将 HEIC 格式照片批量转为 JPEG 以便分享
- **普通用户**：需要快速缩小图片体积以便邮件发送或存储

### 1.3 输入输出规格

| 项目 | 规格 |
|------|------|
| **输入来源** | 本地文件路径、拖拽文件、文件夹路径、HTTP/HTTPS 图片 URL |
| **输出格式** | 转换后的图片文件（保持原文件名或自定义前缀），输出目录可指定 |
| **字段结构** | 处理结果报告：`{ "status": "success/failed", "input": "原路径", "output": "输出路径", "original_size": 102400, "new_size": 51200, "ratio": 0.5, "duration_ms": 320 }` |


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
