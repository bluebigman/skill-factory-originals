---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: imagecraft-android
name: imagecraft-android
displayName: 图片处理 压缩转换 批量操作
description: 提供图片压缩、格式转换与批量处理的规范流程与输出。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/imagecraft-android
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 像素工坊
agent_created: true
trigger_words: ["图片批量处理", "图片压缩", "格式转换", "imagecraft", "android", "图片处理", "批量转换", "图像优化"]
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

# ImageCraft Android 技能文档

## 一、能力边界（一页纸速查卡）

### 能做（核心能力）

| 编号 | 能力项 | 说明 | 输入示例 |
|------|--------|------|----------|
| 1 | 图片压缩 | 按指定质量/尺寸压缩图片，支持 JPEG、PNG、WebP | 原图路径 + 目标质量（如 80%） |
| 2 | 格式转换 | 在 JPEG、PNG、WebP、BMP 之间互转 | 原图路径 + 目标格式（如 WebP） |
| 3 | 批量处理 | 对文件夹内全部图片执行统一操作 | 文件夹路径 + 处理规则 |
| 4 | 元数据读取 | 提取图片尺寸、大小、格式、色彩空间等基础信息 | 图片路径 |
| 5 | 输出结构化结果 | 将处理结果整理为 JSON 格式返回 | 处理完成后自动生成 |

### 不能做（明确边界）

| 编号 | 限制项 | 说明 |
|------|--------|------|
| 1 | 不支持 RAW 格式 | CR2、NEF、ARW 等相机原始格式不在处理范围内 |
| 2 | 不做图像内容识别 | 不提供 OCR、人脸识别、物体检测等功能 |
| 3 | 不进行像素级编辑 | 不提供抠图、修图、滤镜等操作 |
| 4 | 不处理动图 | GIF 动画、APNG 等动态图片仅保留第一帧 |
| 5 | 不保证无损压缩 | 压缩必然带来质量损失，具体损失程度与参数相关 |

### 适用对象

- 需要批量压缩图片以减小存储占用的个人用户
- 需要将图片转换为特定格式以适配应用开发的开发者
- 需要统一图片规格以优化加载速度的网站维护者


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
