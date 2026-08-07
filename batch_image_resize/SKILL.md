---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: batch_image_resize
name: placeholder-removed
displayName: 图片批处理 尺寸转换 压缩回滚
description: 批量调整图片尺寸、转换格式与压缩质量，支持预览回滚。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/batch_image_resize
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 像素工坊
agent_created: true
trigger_words: ["批量图片缩放", "图片尺寸调整", "图片格式转换", "图片压缩", "resize images", "图片批量处理", "图像尺寸批量修改", "图片压缩打包"]

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

# 图片批处理 Skill 文档

## 一、能力边界（一页纸速查卡）

### 1.1 能做什么

| 能力项 | 说明 | 支持参数 |
|--------|------|----------|
| 批量缩放 | 将多张图片统一调整为指定尺寸 | `width`, `height`, `mode`（fit/fill/stretch） |
| 格式转换 | 在 JPEG、PNG、WebP、GIF 之间互转 | `target_format` |
| 质量压缩 | 调整 JPEG/WebP 的压缩质量 | `quality`（0-100 整数） |
| 预览回滚 | 处理前生成缩略图预览，处理后保留原始文件备份 | `preview_enabled`, `backup_enabled` |
| 批量操作 | 支持单次处理整个文件夹或指定文件列表 | `input_path`, `output_path` |

### 1.2 不能做什么

- 不支持图片内容编辑（裁剪局部、加文字、滤镜等）
- 不支持 EXIF 信息保留或修改
- 不支持批量重命名（需配合其他工具）
- 不支持处理超过 5000 张图片的单次任务（性能保护）
- 不支持动图（GIF/APNG）的逐帧处理

### 1.3 适用对象

- 需要为网站/App 准备多尺寸素材的前端开发者
- 需要压缩图片以节省存储空间的运营人员
- 需要统一图片格式的设计师
- 需要批量处理图片的自动化脚本使用者


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
