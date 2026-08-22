---
slug: batch-image-resize
name: batch-image-resize
displayName: 图片批处理 缩放压缩 格式转换
description: 批量缩放、压缩、转换图片格式，自动处理EXIF与目录归档。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: PixelForge Studio
agent_created: true
trigger_words: ["batch-image-resize", "批量缩放图片", "图片压缩", "图片格式转换", "图片批处理", "图像尺寸调整", "批量转格式"]
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# batch-image-resize 技能文档

## 一、能力边界（一页纸速查卡）

### 1.1 能做什么

| 能力项 | 说明 | 支持参数 |
|--------|------|----------|
| 批量缩放 | 按指定宽高或百分比调整图片尺寸 | `--width`, `--height`, `--percent` |
| 批量压缩 | 调整图片质量参数，减小文件体积 | `--quality` (1-100) |
| 格式转换 | 在 JPEG/PNG/WebP/AVIF 之间互转 | `--format` |
| EXIF 处理 | 自动保留或剥离 EXIF 元数据 | `--keep-exif` / `--strip-exif` |
| 目录归档 | 输出文件按规则自动归档到子目录 | `--output-dir`, `--pattern` |

### 1.2 不能做什么（明确边界）

- 不支持动图（GIF/APNG）的逐帧处理
- 不支持批量重命名（需配合其他工具）
- 不支持云端存储直接读写（需先下载到本地）
- 不支持 RAW 格式（CR2/NEF/ARW 等）直接处理
- 不提供 OCR 文字识别能力

### 1.3 适用对象

- 需要批量处理图片的运营人员
- 需要统一图片规格的前端开发者
- 需要压缩图片以节省存储空间的个人用户
- 需要转换格式以适配不同平台的创作者

---

## 二、触发方式

### 2.1 触发词

| 触发词 | 场景示例 |
|--------|----------|
| `batch-image-resize` | 直接调用技能主命令 |
| `批量缩放图片` | "帮我把这些图批量缩小到 800px 宽" |
| `图片压缩` | "这批照片太大了，帮我压缩一下" |
| `图片格式转换` | "把文件夹里所有 png 转成 webp" |
| `图片批处理` | "统一处理一下这个目录下的所有图片" |

### 2.2 场景映射表

| 用户说（大白话） | 技能执行动作 |
|------------------|--------------|
| "把 product_photos 里的图都改成 1200x800" | 读取目录 → 批量缩放 → 输出到指定目录 |
| "这些截图太大了，压到 500KB 以内" | 读取目录 → 循环压缩 → 输出压缩报告 |
| "把 logo 从 png 转成 svg" | 读取文件 → 格式转换 → 输出新格式文件 |
| "处理完记得把原图备份一下" | 处理前自动复制原图到 `_backup` 子目录 |

---

## 三、标准流程

### 3.1 前置条件

| 条件 | 要求 | 检查方式 |
|------|------|----------|
| 输入目录存在 | 目录路径有效且包含图片文件 | `ls <input_dir>` 确认 |
| 图片格式受支持 | 扩展名为 .jpg/.jpeg/.png/.webp/.avif | 自动扫描并跳过不支持格式 |
| 输出目录可写 | 有创建子目录和写入文件的权限 | `touch <output_dir>/.write_test` |
| 磁盘空间充足 | 剩余空间 ≥ 输入总大小的 1.5 倍 | `df -h <output_dir>` |

### 3.2 执行步骤

1. **参数解析**：读取命令行参数或交互式输入，确认输入目录、输出目录、处理规则。
2. **文件扫描**：递归扫描输入目录，收集所有受支持的图片文件，生成待处理清单。
3. **规则校验**：检查参数合法性（如 quality 在 1-100 之间，width/height 为正整数）。
4. **预处理**：若指定 `--backup`，先将原图复制到输出目录下的 `_backup` 子目录。
5. **逐文件处理**：
   - 读取图片 → 按规则缩放 → 按规则压缩 → 按规则转换格式
   - 处理 EXIF（保留或剥离）
   - 写入输出目录（按 `--pattern` 规则归档）
6. **生成报告**：输出处理结果汇总，包括成功/失败文件数、总节省空间、耗时。
7. **清理临时文件**：删除处理过程中产生的临时缓存。

### 3.3 输出规范

处理完成后输出结构化结果：

```
处理完成：
- 成功处理：42 个文件
- 跳过：3 个文件（格式不支持）
- 失败：1 个文件（文件损坏）
- 总节省空间：156.3 MB（压缩率 62%）
- 耗时：3.2 秒
- 输出目录：/path/to/output/
```

---

## 四、置信度门控

当遇到以下情况时，技能不会编造结果，而是输出 `[需核实:字段]` 占位符：

| 场景 | 输出占位符 | 后续动作 |
|------|------------|----------|
| 无法读取图片尺寸 | `[需核实:图片尺寸]` | 提示用户检查文件是否损坏 |
| 无法确定原始格式 | `[需核实:原始格式]` | 提示用户指定格式 |
| 压缩后文件反而变大 | `[需核实:压缩参数]` | 建议降低 quality 或改用更高效格式 |
| 输出路径权限不足 | `[需核实:输出权限]` | 提示用户检查目录权限 |
| EXIF 信息读取失败 | `[需核实:EXIF数据]` | 提示用户确认是否保留原 EXIF |

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| `E001` | 输入目录不存在 | "指定的输入目录不存在，请检查路径" | 确认路径是否正确，或创建目录 |
| `E002` | 无支持的图片文件 | "目录下未找到支持的图片文件（jpg/png/webp/avif）" | 确认文件格式，或更换目录 |
| `E003` | 参数不合法 | "参数值超出允许范围，请检查" | 确认 quality 在 1-100，尺寸为正整数 |
| `E004` | 输出目录不可写 | "无法写入输出目录，请检查权限" | 修改目录权限或更换输出路径 |
| `E005` | 文件处理失败 | "文件处理过程中发生错误，已跳过" | 检查文件是否损坏，或单独处理该文件 |
| `E006` | 磁盘空间不足 | "磁盘空间不足，无法完成处理" | 清理磁盘空间，或减少处理文件数量 |
| `E007` | 格式转换不支持 | "目标格式不支持，请选择 jpg/png/webp/avif" | 更换目标格式 |

---

## 六、FAQ 反模式

### 6.1 常见坑

| 坑 | 反模式（错误做法） | 正模式（正确做法） |
|----|-------------------|-------------------|
| 压缩后质量损失 | 直接 quality=10 追求最小体积 | 先用 quality=70 测试，逐步降低 |
| 透明背景丢失 | PNG 转 JPG 导致背景变黑 | 先填充白色背景，或保留 PNG 格式 |
| 文件名冲突 | 不同目录同名文件互相覆盖 | 使用 `--pattern` 保留相对路径 |
| EXIF 隐私泄露 | 处理后的图片保留 GPS 位置 | 使用 `--strip-exif` 剥离元数据 |
| 处理中断 | 大批量处理中途断电 | 使用 `--resume` 支持断点续传 |

### 6.2 反模式对照表

| 用户需求 | 反模式响应 | 正模式响应 |
|----------|------------|------------|
| "把图变小" | 直接缩到 100px 宽 | 询问用途，推荐合适尺寸 |
| "压缩图片" | 全部 quality=20 | 根据图片类型推荐不同质量 |
| "转格式" | 全部转成 JPG | 根据用途推荐格式（WebP 用于网页） |
| "处理快点" | 跳过错误文件不报告 | 处理完统一报告错误清单 |

---

## 七、渐进式披露

### 7.1 速查卡（新手必读）

```
用法：batch-image-resize --input <目录> --output <目录> [选项]

常用选项：
  --width 800        设置宽度（高度自动等比）
  --height 600       设置高度（宽度自动等比）
  --percent 50       按百分比缩放
  --quality 80       压缩质量（1-100）
  --format webp      转换格式（jpg/png/webp/avif）
  --keep-exif        保留 EXIF 信息
  --strip-exif       剥离 EXIF 信息
  --backup           处理前备份原图
  --pattern "sub/"   归档模式（保留相对路径）

示例：
  batch-image-resize --input ./photos --output ./processed --width 1200 --quality 85
```

### 7.2 进阶阅读路径

**新手路径**（5 分钟上手）：
1. 阅读速查卡，掌握基本用法
2. 用一个小目录测试，确认输出符合预期
3. 查看处理报告，了解压缩效果

**进阶路径**（深入使用）：
1. 阅读标准流程章节，理解处理逻辑
2. 学习 `--pattern` 归档规则，实现复杂目录结构
3. 结合错误码体系，排查处理失败原因
4. 使用 `--resume` 处理大规模批量任务

**专家路径**（定制化）：
1. 修改配置文件，自定义默认参数
2. 编写脚本调用技能 API，集成到自动化流水线
3. 扩展支持更多图片格式（需修改源码）

---

## 八、参数详解

### 8.1 尺寸参数

| 参数 | 类型 | 范围 | 说明 |
|------|------|------|------|
| `--width` | 整数 | 1-10000 | 目标宽度（像素），高度自动等比 |
| `--height` | 整数 | 1-10000 | 目标高度（像素），宽度自动等比 |
| `--percent` | 整数 | 1-100 | 缩放百分比，与宽高参数互斥 |
| `--max-dimension` | 整数 | 1-10000 | 限制最大边，保持比例 |

### 8.2 压缩参数

| 参数 | 类型 | 范围 | 说明 |
|------|------|------|------|
| `--quality` | 整数 | 1-100 | JPEG/WebP 质量，越高越清晰 |
| `--lossless` | 布尔 | - | 使用无损压缩（仅 WebP/AVIF） |
| `--target-size` | 整数 | 1-10000 | 目标文件大小（KB），自动调整质量 |

### 8.3 格式参数

| 参数 | 类型 | 范围 | 说明 |
|------|------|------|------|
| `--format` | 字符串 | jpg/png/webp/avif | 目标格式 |
| `--keep-exif` | 布尔 | - | 保留 EXIF 元数据 |
| `--strip-exif` | 布尔 | - | 剥离 EXIF 元数据 |

---

## 九、用户协议

<!-- user-agreement-injected -->

**使用本技能即表示您同意以下条款：**

1. **责任承担**：使用者自行承担因使用本技能产生的全部责任。包括但不限于图片处理结果不符合预期、数据丢失、隐私泄露等风险。
2. **禁止反向工程**：不得对本技能进行反向工程、反编译、破解或试图获取源代码逻辑。
3. **合规使用**：使用者应确保处理的图片内容合法合规，不得处理侵权、违法或敏感内容。
4. **免责声明**：本技能按"原样"提供，不提供任何明示或暗示的保证。作者不对使用结果做任何承诺。
5. **数据安全**：使用者应自行备份重要图片数据，本技能不承担数据丢失的赔偿责任。

---

## 十、许可证（License）

<!-- professional-license-embedded -->

### MIT License

Copyright (c) 2024 PixelForge Studio

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

---

*本 Skill 由 AI 辅助生成，仅供参考。使用前请阅读相关文档。*
