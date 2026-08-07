---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: batch_image_resize
name: placeholder-removed
displayName: 图片批处理 尺寸格式 压缩回滚
description: 批量调整图片尺寸、转换格式与压缩质量，支持预览回滚。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/batch_image_resize
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 图匠工坊
agent_created: true
trigger_words: ["批量图片缩放", "图片尺寸调整", "图片格式转换", "图片压缩", "resize images", "图片批处理", "图像尺寸修改", "图片体积优化"]
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

# 图片批处理 Skill 文档

## 一、能力边界（一页纸速查卡）

### 1.1 能做什么

| 能力项 | 说明 | 典型参数示例 |
|--------|------|--------------|
| 批量缩放 | 按指定宽高或比例调整图片尺寸 | `--width 1920 --height 1080` 或 `--scale 0.5` |
| 格式转换 | 在 JPEG/PNG/WebP/GIF 之间互转 | `--format webp` |
| 质量压缩 | 调整压缩质量参数，控制输出体积 | `--quality 80` |
| 预览回滚 | 处理前生成预览，支持撤销操作 | `--preview --rollback` |
| 目录递归 | 处理子目录中的图片文件 | `--recursive` |
| 元数据保留 | 可选保留 EXIF 等元数据 | `--keep-metadata` |

### 1.2 不能做什么

- 不支持矢量图（SVG、EPS）的像素级缩放
- 不支持动图（GIF/APNG）的逐帧编辑
- 不支持批量重命名（需配合其他工具）
- 不支持云端存储直接读写（需先下载到本地）
- 不支持超过 5000 张图片的单次处理（性能保护）

### 1.3 适用对象

- 需要批量处理产品图、封面图的电商运营
- 需要压缩图片以优化页面加载速度的前端开发者
- 需要统一图片规格的文档整理人员
- 需要将图片转为特定格式的设计师


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
