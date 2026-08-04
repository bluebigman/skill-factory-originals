---
slug: batch_image_resize
name: placeholder-removed
displayName: 图片批量缩放 尺寸处理 格式转换
description: 批量调整图片尺寸、格式与质量，支持多格式输入输出。
version: 0.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/batch_image_resize
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 图匠工坊
agent_created: true
trigger_words: 批量调整图片尺寸, 图片批量缩放, 图片尺寸修改, 图像分辨率调整, 图片压缩, 图片格式转换, 批量处理图片
---

> 本内容由 AI 生成，仅供学习参考 <!-- ai-generated-notice -->

# 图片批量缩放与格式处理 Skill

## 一、能力边界与适用场景（速查卡）

### 1.1 能做什么

| 功能项 | 说明 | 支持参数 |
|--------|------|----------|
| 尺寸调整 | 按指定宽高缩放，或按比例缩放 | `width`, `height`, `scale` |
| 格式转换 | 转换输出格式 | `output_format`（支持 jpg/png/webp/bmp/tiff） |
| 质量调整 | 控制压缩比 | `quality`（1-100，仅对有损格式生效） |
| 批量处理 | 一次处理文件夹内全部图片 | `source_dir`, `target_dir` |
| 覆盖策略 | 跳过已存在文件或强制覆盖 | `overwrite`（true/false） |

### 1.2 不能做什么

- 不支持图片内容识别、裁剪、滤镜、文字叠加等编辑操作
- 不支持动图（GIF/APNG）的逐帧处理
- 不支持 RAW 格式（CR2/NEF/ARW 等）
- 不处理加密或损坏的图片文件
- 不保证超分辨率放大后的细节保真度

### 1.3 适用对象

- 电商运营：批量统一商品图尺寸
- 前端开发：压缩素材图以加快页面加载
- 个人用户：整理手机/相机照片的尺寸与格式
- 文档处理：将截图统一转成 PDF 可嵌入的 JPG 格式

---

## 二、触发方式与场景映射

| 触发词/用户说法 | 对应行为 |
|----------------|----------|
| "把图片缩小一半" | 按比例缩放，scale=0.5 |
| "统一改成 800 像素宽" | 设置 width=800，高度按原比例 |
| "转成 webp 格式" | output_format=webp |
| "压缩到 80% 质量" | quality=80，保持原尺寸 |
| "处理这个文件夹里所有图" | 解析 source_dir，批量执行 |

---

## 三、标准处理流程

### 3.1 前置条件

1. 用户提供以下任一信息：
   - 单个图片文件路径
   - 文件夹路径（含多张图片）
2. 明确目标参数（尺寸/格式/质量）
3. 确认输出路径（若未指定，默认在源目录下新建 `output` 子文件夹）

### 3.2 执行步骤

1. **收集输入**：获取源路径、目标参数、输出路径。
2. **格式校验**：检查源文件扩展名是否在支持列表内。
3. **参数归一化**：
   - 若同时给出 `width` 和 `scale`，以 `width` 为准
   - 若只给 `width` 不给 `height`，保持原纵横比
   - `quality` 仅对 jpg/webp 生效
4. **执行处理**：逐文件读取 → 缩放 → 格式转换 → 保存。
5. **生成报告**：输出每张图处理前后的尺寸、大小变化。

### 3.3 输出规范

处理完成后返回以下结构：

```
处理完成：
- 成功：12 张
- 跳过：2 张（已存在且未允许覆盖）
- 失败：1 张（文件损坏）
输出目录：/path/to/output
详细日志：见下方列表
```

---

## 四、置信度门控规则

- 当用户未明确指定输出格式时，默认保持原格式，并在结果中注明"未改变格式"。
- 当用户要求的尺寸超过原图 200% 时，提示"放大可能导致画质模糊"，但正常执行。
- 若无法读取图片元信息（如文件头损坏），输出 `[需核实:文件完整性]` 并跳过该文件，不猜测处理结果。

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| `E001` | 文件不存在 | "未找到指定路径，请检查路径是否正确" | 重新提供路径，或使用绝对路径 |
| `E002` | 不支持的格式 | "该格式不在支持列表内，请转换为 jpg/png/webp/bmp/tiff" | 先手动转换格式再重试 |
| `E003` | 参数无效 | "width/height 必须为正整数，quality 必须在 1-100 之间" | 检查参数值是否符合规范 |
| `E004` | 输出目录无写入权限 | "无法写入目标目录，请检查权限" | 更换输出路径或修改目录权限 |
| `E005` | 文件损坏 | "图片文件可能已损坏，无法读取内容" | 确认原文件能否正常打开 |

---

## 六、FAQ 与反模式对照

### 6.1 常见坑

| 坑 | 反模式（错误做法） | 正确做法 |
|----|-------------------|----------|
| 宽高同时指定导致变形 | 直接设置 width=800, height=600 不管原图比例 | 只给一个维度，或先确认原图比例与目标比例一致 |
| 高质量压缩无效果 | 对 PNG 设置 quality=50 | 先转成 JPG/WebP 再压缩，PNG 无损格式不吃 quality 参数 |
| 批量处理中断 | 不记录进度，失败后全部重来 | 边处理边写日志，已完成的文件跳过 |
| 覆盖原图 | 输出路径=源路径，直接覆盖原始文件 | 默认输出到独立子目录，保留源文件 |
| 忽略透明通道 | 将带透明底的 PNG 转成 JPG 导致黑底 | 告知用户 JPG 不支持透明，建议保留 PNG 或转 WebP |

### 6.2 反模式对照表

- **反模式**：不验证输入直接执行 → 先校验路径和参数，再启动处理
- **反模式**：静默跳过失败文件 → 每次失败都记录原因并反馈
- **反模式**：只给结果不给过程 → 输出每张图的处理明细

---

## 七、渐进式披露阅读路径

### 7.1 新手速查（30 秒上手）

```
输入：图片路径 + 目标宽度 → 输出：缩放后的图片
示例：/images/photo.jpg → width=800 → /images/output/photo.jpg
```

### 7.2 进阶使用（完整参数）

```
参数表：
- source_dir: 必填，源文件夹路径
- target_dir: 选填，输出目录（默认源目录下 output/）
- width: 选填，目标宽度（像素）
- height: 选填，目标高度（像素）
- scale: 选填，缩放比例（0.1-4.0）
- output_format: 选填，jpg/png/webp/bmp/tiff
- quality: 选填，1-100 整数
- overwrite: 选填，true/false

约束：
- width、height、scale 三者至少给一个
- width 和 height 同时给时，若比例与原图不一致，以 width 为准，高度自动调整
- quality 默认 90，仅对 jpg/webp 有意义
```

### 7.3 批量处理示例

```
输入：
source_dir=/photos/raw
target_dir=/photos/resized
width=1200
output_format=webp
quality=85
overwrite=false

输出：
/photos/resized/001.webp（1200x800，85%质量）
/photos/resized/002.webp（1200x675，85%质量）
...
```

---

## 八、附注

- 所有操作均在本地完成，不涉及图片上传。
- 单次处理上限为 500 张，超出部分提示分批执行。
- 若目标目录存在同名文件且 `overwrite=false`，自动跳过并计入"跳过"计数。

---

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
