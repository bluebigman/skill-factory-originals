---
slug: batch_image_resize
name: placeholder-removed
displayName: 图片批处理 尺寸格式 压缩转换
description: 批量调整图片尺寸、转换格式与压缩质量，支持预览回滚。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 图匠工坊
agent_created: true
trigger_words: ["批量图片缩放","图片尺寸调整","图片格式转换","图片压缩","resize images","--selftest","--version","图片批处理","图像尺寸修改","图片格式批量转换"]

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

# 图片批处理 Skill 使用指南

## 一、能力边界（一页纸速查卡）

### 能做什么

| 功能项 | 说明 | 示例 |
|--------|------|------|
| 批量缩放 | 按宽度、高度、百分比或指定宽高调整图片尺寸 | 将所有 PNG 缩放到宽度 800px |
| 格式转换 | 在 jpg/jpeg、png、webp、bmp 之间互转 | 将 BMP 批量转为 JPG |
| 质量压缩 | 对 JPEG/WebP 设置压缩质量参数（1-95） | 将 JPG 质量设为 75 |
| 输出预览 | 执行前显示处理参数摘要，确认后运行 | 显示"将处理 12 张图片，输出至 output/" |
| 回滚机制 | 处理前自动备份原图元数据，出错时可恢复 | 某张图处理失败，原图不受影响 |

### 不能做什么

| 限制项 | 具体边界 |
|--------|----------|
| 输入格式 | 仅支持 jpg/jpeg、png、webp、bmp 四种格式 |
| 文件大小 | 单张图片不超过 50MB，超出将跳过并提示 |
| 输入路径 | 必须是本地存在的文件夹路径或单文件路径 |
| 输出覆盖 | 不会覆盖原图，所有结果写入 `output/` 子目录 |
| 批量上限 | 单次处理不超过 500 张图片（防止内存溢出） |
| 动图支持 | 不支持 GIF/APNG 等动态图片格式 |

### 适用对象

- 需要批量整理图片素材的设计师、运营人员
- 需要压缩图片以适配网页/邮件/社交媒体的开发者
- 需要统一图片格式与尺寸的文档管理者


## 许可证（License）

```text
MIT License

Copyright (c) {year} {holder}

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

```
<!-- professional-license-embedded -->
