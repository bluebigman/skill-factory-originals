# 批量图片缩放压缩工具（Batch Image Resize）

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

---
slug: batch-image-resize
name: batch-image-resize
displayName: 图片批处理 缩放压缩 格式转换
description: 批量缩放、压缩、转换图片格式，自动处理EXIF与目录归档。
version: 1.3.13
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/batch-image-resize
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: SkillForge Studio
agent_created: true
trigger_words: ["batch-image-resize", "批量缩放图片", "图片压缩", "图片格式转换"]
---

## 一、能力边界（一页纸速查卡）

| 维度 | 支持 | 不支持 |
|------|------|--------|
| 输入格式 | JPG / JPEG / PNG / WebP / BMP / TIFF | RAW、SVG、GIF（动画）、PSD 等专业格式 |
| 输出格式 | 上述六种格式的相互转换 | 输出到 PDF、视频帧等非目标格式 |
| 缩放方式 | 指定宽度、指定比例、指定最大边长 | 不规则裁剪（如按人脸/主体裁剪） |
| 压缩方式 | JPEG/WebP 质量参数（1-100）；PNG 无损压缩 | 有损压缩 PNG（需先转格式） |
| EXIF 处理 | 自动旋转修正；可选保留/剥离元数据 | 编辑单个 EXIF 字段（如 GPS、时间戳） |
| 目录处理 | 递归扫描子目录；按日期/类型归档 | 跨设备/网络驱动器自动同步 |
| 缩略图 | 生成指定尺寸的缩略图副本 | 生成多级响应式图片集（1x/2x/3x） |

**适用对象**：
- 需要批量处理大量图片素材的运营人员、前端开发者、电商从业者
- 需要统一图片尺寸和体积的文档归档场景
- 需要将图片从一种格式批量迁移到另一种格式的迁移任务

**不适用场景**：
- 单张图片的精细修图（请使用 Photoshop / GIMP）
- 需要感知图片内容的智能裁剪
- 需要保留动态效果的 GIF 处理

---

## 二、触发方式与场景映射

| 触发词 | 实际场景 |
|--------|----------|
| `batch-image-resize` | 直接调用 Skill，按默认参数执行批量处理 |
| `批量缩放图片` | 用户说"把这个文件夹里的图都缩到 800 宽" |
| `图片压缩` | 用户说"图片太大了发不出去，帮我压一下" |
| `图片格式转换` | 用户说"把这些 PNG 全转成 JPG" |

**触发参数示例**：
```
batch-image-resize --input ./photos --output ./processed --width 1280 --quality 80
```

---

## 三、标准工作流程

### 前置条件

| 检查项 | 要求 | 失败处理 |
|--------|------|----------|
| 输入目录存在 | 路径有效且包含至少一张图片 | 返回错误码 `E_NO_INPUT` |
| 图片格式合法 | 扩展名符合上述六种格式 | 跳过并记录至失败清单，不影响其他文件 |
| 输出目录可写 | 有创建文件的权限 | 提示用户更换输出路径或检查权限 |
| 磁盘空间 | 预估输出体积 > 可用空间 | 提前警告，用户确认后继续 |

### 执行步骤（分步编号）

1. **扫描输入目录**：递归遍历所有子目录，识别扩展名匹配的图片文件，建立待处理清单。
2. **参数解析**：读取用户指定的缩放参数（宽度/比例/最大边长三选一）、压缩质量、格式转换目标、EXIF 策略、归档规则。
3. **逐张处理**：
   - 打开图片并读取尺寸、格式、EXIF 旋转信息
   - 计算目标尺寸（保留宽高比，宽高均不超过指定值）
   - 执行缩放（使用 Lanczos 重采样算法保证质量）
   - 若目标格式为 JPEG 且原图带透明通道，先填充白色背景
   - 按质量参数对 JPEG/WebP 进行压缩编码；PNG 执行无损压缩
   - 根据 EXIF 策略选择保留或剥离元数据
4. **文件命名与归档**：默认保留原文件名，追加 `_resized` 后缀；若启用归档，则按日期（`YYYY/MM/`）或类型（`jpg/`、`png/`）建立子目录。
5. **缩略图生成**（可选）：为每张处理后的图片额外生成一张指定尺寸（默认 200×200）的缩略图副本。
6. **输出报告**：生成 `report.txt`，记录每张图片的状态（成功/失败/跳过）、原始尺寸、目标尺寸、压缩率、耗时。

### 输出规范

| 输出项 | 格式 | 示例 |
|--------|------|------|
| 处理报告 | `report.txt`，每行一条记录 | `success | photo1.jpg | 4000x3000 -> 1280x960 | 72.3% | 0.25s` |
| 汇总信息 | 控制在报告末尾 | `成功: 42 | 失败: 1 | 跳过: 3 | 总耗时: 12.7s | 节省空间: 286MB` |
| 错误明细 | 失败原因单独列出 | `photo3.png | 文件损坏，无法解码` |

---

## 四、置信度门控

处理过程中遇到以下情况，输出 `[需核实:字段]` 占位符，不进行推测：

| 场景 | 输出 |
|------|------|
| 图片自身未标注尺寸 | `[需核实:原始尺寸]` |
| EXIF 旋转信息缺失且方向不明 | `[需核实:旋转方向]` |
| 文件扩展名与实际编码格式不一致 | `[需核实:实际格式]` |
| 压缩率计算依赖的原始文件体积无法读取 | `[需核实:原始体积]` |

**原则**：宁可标注未知，不编造数据。

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| `E_NO_INPUT` | 输入目录为空或不存在 | "未找到任何图片文件，请检查输入路径" | 确认路径正确且目录内有合法图片 |
| `E_NO_PERMISSION` | 无写入权限 | "输出目录不可写，请检查权限设置" | 更换输出目录或提升权限 |
| `E_DECODE_FAIL` | 图片解码失败（文件损坏） | "图片 xxx 无法解析，已跳过" | 手动检查该文件是否可正常打开 |
| `E_ENCODE_FAIL` | 编码输出失败 | "图片 xxx 处理失败，请调整参数重试" | 降低质量参数或改用其他输出格式 |
| `E_DISK_FULL` | 磁盘空间不足 | "磁盘空间不足，已停止处理" | 清理磁盘或更换输出位置 |
| `E_UNSUPPORTED` | 遇到不支持的格式 | "文件 xxx 格式不支持，已跳过" | 确认扩展名是否为六种支持格式之一 |

---

## 六、常见误区与反模式对照

| 常见误区 | 反模式 | 正确做法 |
|----------|--------|----------|
| 认为压缩质量=图片清晰度 | 把质量设为 100 以为无损 | JPEG 质量 100 仍是有损压缩，只是损失极小；追求无损请用 PNG |
| 缩放时直接指定宽高两个值 | 设置 width=800 且 height=600 导致图片变形 | 只指定一个维度，或指定最大边长，系统自动按比例计算 |
| PNG 转 JPEG 后透明区域变黑 | 直接转换不处理透明通道 | 系统自动填充白色背景，用户无需手动干预 |
| 忽略 EXIF 旋转信息 | 图片处理后被错误旋转 90° | 系统自动读取旋转方向并修正，用户无需关心 |
| 期望处理结果可逆 | 处理完原图被覆盖 | 默认输出到独立目录，原图不受影响 |

---

## 七、渐进式阅读路径

### 速查卡（新手必读）

1. 准备好输入文件夹（含图片）和输出文件夹（可不存在）
2. 执行：`batch-image-resize --input ./input --output ./output`
3. 默认行为：不缩放、JPEG 质量 80、保留 EXIF、原文件名 + `_resized` 后缀
4. 查看 `report.txt` 确认结果

### 进阶路径（有经验用户）

- **精细控制**：同时指定 `--width 1280 --quality 75 --format webp --strip-exif` 获得体积最小的 WebP 输出
- **归档规则**：`--organize date` 按日期分目录；`--organize type` 按格式分目录
- **缩略图**：`--thumbnails 200` 为每张图额外生成 200px 宽的缩略图
- **批量重命名**：`--rename-pattern "IMG_{date}_{seq}"` 自定义命名规则

### 参数速查表

| 参数 | 取值范围 | 默认值 | 说明 |
|------|----------|--------|------|
| `--width` | 1–20000 | 无 | 目标宽度（像素），等比缩放 |
| `--ratio` | 0.01–1.0 | 无 | 缩放比例，0.5 表示缩至一半 |
| `--max-side` | 1–20000 | 无 | 最大边长限制 |
| `--quality` | 1–100 | 80 | JPEG/WebP 压缩质量 |
| `--format` | jpg/png/webp/bmp/tiff | 原格式 | 输出格式 |
| `--strip-exif` | 布尔 | false | 是否剥离元数据 |
| `--organize` | none/date/type | none | 归档方式 |
| `--thumbnails` | 正整数 | 无 | 缩略图宽度 |

---

## 八、执行示例

**用户请求**："把 downloads 文件夹里的图片都压缩一下，转成 WebP，宽度不超过 1600。"

**执行过程**：

```
扫描 downloads/ 发现 23 张图片（12 张 JPG、8 张 PNG、3 张 WebP）
参数：max-side=1600, format=webp, quality=80
处理中...
  - photo1.jpg (4000x3000) → (1600x1200) webp, 82.5% 压缩率
  - photo2.png (800x600) → (800x600) webp, 61.3% 压缩率
  ...
完成：成功 21 | 失败 1（photo15.jpg 文件损坏）| 跳过 1（photo16.webp 已是目标格式）
总耗时：8.4s | 节省空间：312MB
输出报告已保存至 downloads_processed/report.txt
```

**输出文件**：
```
downloads_processed/
  ├── photo1_resized.webp
  ├── photo2_resized.webp
  ├── ...
  └── report.txt
```

---

## 九、边界值说明

| 场景 | 行为 |
|------|------|
| 图片宽高比极端（如全景图 20000×500） | 按指定宽度缩放时高度自动计算，可能超过 20000，需注意输出尺寸 |
| 图片尺寸小于目标尺寸 | 默认不放大（保持原尺寸），除非显式指定 `--upscale` |
| 压缩质量设为 1 | 体积最小但画质极低，仅用于预览 |
| 压缩质量设为 100 | 体积仍大于原图可能，建议 JPEG 用 80-90、WebP 用 75-85 |
| 透明 PNG 转 TIFF | TIFF 支持透明通道，直接转换 |
| 透明 PNG 转 BMP | BMP 不支持透明，自动填充白色背景 |

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
