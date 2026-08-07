---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: image-processing-tool
name: image-processing-tool
displayName: 图像批处理 尺寸压缩 格式转换
description: 批量处理图片尺寸、压缩体积、转换格式，支持自检与版本查询。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/image-processing-tool
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: SkillForge Studio
agent_created: true
trigger_words: ["图片批量处理", "图像批处理", "批量压缩图片", "图片格式转换", "图片尺寸调整"]
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

# 图像批处理工具（image-processing-tool）使用指南

## 一、能力边界速查卡

本工具是一个面向图片批处理场景的 Python 命令行应用，核心能力集中在**尺寸调整、体积压缩、格式转换、批量优化**四个方面。

### 1.1 能做与不能做

| 能力维度 | 支持情况 | 说明 |
|---------|---------|------|
| 批量处理本地图片文件 | ✅ 支持 | 可一次传入多个文件路径或目录 |
| 从 URL 拉取图片处理 | ✅ 支持 | 需网络可达，且 URL 指向可直接下载的图片资源 |
| 调整图片尺寸 | ✅ 支持 | 支持按宽高像素、缩放比例两种模式 |
| 压缩图片体积 | ✅ 支持 | 支持 JPEG/PNG/WebP 的有损与无损压缩 |
| 格式转换 | ✅ 支持 | 支持 JPEG ↔ PNG ↔ WebP ↔ BMP 互转 |
| 保留 EXIF 信息 | ⚠️ 部分支持 | 默认剥离 EXIF，可通过参数保留 |
| 处理动图（GIF/APNG） | ❌ 不支持 | 仅处理静态图片，动图会报错 |
| 批量重命名 | ❌ 不支持 | 输出文件名由规则自动生成，不支持自定义命名模板 |
| 图片内容识别/OCR | ❌ 不支持 | 本工具不做内容理解，仅做像素级处理 |
| 云端存储/上传 | ❌ 不支持 | 处理结果仅保存在本地 |

### 1.2 适用对象

- **适合**：需要批量处理本地图片资源的开发者、内容运营、UI 设计师、数据标注人员。
- **不适合**：需要图片内容理解（OCR、物体识别）、需要在线协作编辑、需要复杂滤镜特效的场景。


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
