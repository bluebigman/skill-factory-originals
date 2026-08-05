---
> 本内容由 AI 生成，仅供学习参考（《人工智能生成合成内容标识办法》显式标识）。
<!-- ai-generated-notice -->
slug: batch_image_resize
name: placeholder-removed
displayName: 批量图片缩放 尺寸调整 格式转换
description: 批量处理图片尺寸、格式与质量，支持预览与回滚。
version: 0.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/batch_image_resize
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 像素工坊
agent_created: true
trigger_words: 批量图片缩放, 图片尺寸调整, 图片格式转换, 图片压缩, resize images
---

> 本内容由 AI 生成，仅供学习参考 <!-- ai-generated-notice -->

# 批量图片处理 Skill 文档

## 一、能力边界（一页纸速查卡）

本 Skill 提供批量图片的尺寸缩放、格式转换、质量调整能力。请先确认你的需求是否在此范围内。

| 能力项 | 支持情况 | 说明 |
| --- | --- | --- |
| 批量尺寸缩放 | ✅ 支持 | 指定宽度、高度、或百分比缩放 |
| 单一图片处理 | ✅ 支持 | 与批量逻辑一致，只是数量为1 |
| 格式转换 | ✅ 支持 | JPEG、PNG、WebP、BMP 互转 |
| 质量调整 | ✅ 支持 | JPEG/WebP 质量参数（1-100） |
| 保持宽高比 | ✅ 支持 | 指定单边时自动等比缩放 |
| 裁剪 | ❌ 不支持 | 如需裁剪，请先手动处理或说明需求 |
| 旋转/翻转 | ❌ 不支持 | 如需旋转，请先手动处理 |
| 滤镜/特效 | ❌ 不支持 | 如需滤镜，请先手动处理 |
| 元数据保留 | ⚠️ 部分支持 | 保留基础信息，EXIF 可能丢失 |
| 输出目录自定义 | ✅ 支持 | 默认输出到 `output/` 子目录 |
| 覆盖原文件 | ❌ 不允许 | 防止误操作，必须输出到新文件 |

**适用对象**：需要批量处理图片尺寸或格式的个人开发者、设计师、运营人员。

**不适用对象**：需要复杂图像编辑（如抠图、合成）、需要保留全部 EXIF 信息的场景。

---

## 二、触发方式

以下触发词或场景描述可激活本 Skill：

| 触发词/场景 | 示例说法 |
| --- | --- |
| 批量图片缩放 | "把这50张图缩到800宽" |
| 图片尺寸调整 | "把所有商品图改成 600x600" |
| 图片格式转换 | "把 PNG 全转成 WebP" |
| 图片压缩 | "压一下图片质量，文件变小点" |
| resize images | "Resize all images to 1024px width" |

**场景映射表**：

| 大白话需求 | 实际含义 | Skill 动作 |
| --- | --- | --- |
| "图太大了，发不出去" | 需要缩小尺寸或降低质量 | 缩放 + 质量调整 |
| "网站加载慢" | 需要压缩图片 | 转 WebP + 质量调至 70-80 |
| "统一尺寸" | 所有图调整为相同宽高 | 指定宽高（注意比例问题） |
| "换个格式" | 转换文件类型 | 格式转换 |

---

## 三、标准流程

### 前置条件

1. **输入路径**：需要提供图片所在文件夹路径，或单个图片文件路径。
2. **图片格式**：支持 jpg/jpeg、png、webp、bmp（大小不超过 50MB/张）。
3. **环境依赖**：确认运行环境中已安装 Python 3.8+ 和 Pillow 库（`pip install Pillow`）。
4. **输出目录**：默认在输入目录下创建 `output/` 文件夹，无需手动创建。

### 执行步骤

**第 1 步：确认输入**

收集以下信息，缺一不可：

| 参数 | 必填 | 示例 | 说明 |
| --- | --- | --- | --- |
| `input_path` | ✅ | `/path/to/images` 或 `/path/to/image.jpg` | 文件夹或单文件路径 |
| `mode` | ✅ | `width` / `height` / `percent` / `exact` | 缩放模式 |
| `value` | ✅ | `800` / `600` / `50` / `[600,600]` | 缩放值 |
| `output_format` | ❌ | `jpeg` / `png` / `webp` / `bmp` | 默认保持原格式 |
| `quality` | ❌ | `80` | 仅对 jpeg/webp 生效，默认 85 |

**第 2 步：格式校验**

检查输入是否符合规范：

- `input_path` 必须存在且可读。
- `mode` 必须是 `width`、`height`、`percent`、`exact` 之一。
- `value` 必须是正整数（percent 模式下为 1-500）。
- `exact` 模式必须提供 `[宽,高]` 数组。
- 若 `output_format` 提供，必须是 `jpeg`、`png`、`webp`、`bmp` 之一。

**第 3 步：执行处理**

程序按以下逻辑处理每张图片：

1. 打开图片 → 读取尺寸和格式。
2. 根据 mode 计算新尺寸：
   - `width`：新宽 = value，新高 = 原高 × (value / 原宽)
   - `height`：新高 = value，新宽 = 原宽 × (value / 原高)
   - `percent`：新宽 = 原宽 × value / 100，新尺寸按比例
   - `exact`：直接使用提供的宽高（可能拉伸变形）
3. 使用 `LANCZOS` 重采样算法缩放（质量优先）。
4. 若指定了 `output_format`，则转换格式。
5. 若格式为 jpeg/webp，应用 quality 参数。
6. 保存到 `output/` 目录，文件名格式：`原文件名_处理参数.新格式`。

**第 4 步：输出规范**

- 所有输出文件保存在 `output/` 子目录。
- 处理完成后输出摘要：

```text
处理完成！
- 总文件数：50
- 成功：48
- 失败：2（详见错误报告）
- 输出位置：/path/to/images/output/
```

- 每个文件单独报告（成功/失败 + 原因）。

---

## 四、置信度门控

当出现以下情况时，输出 `[需核实:字段]` 占位符，**不编造**数据：

| 场景 | 占位符示例 |
| --- | --- |
| 图片原始尺寸未知 | `[需核实:原图宽高]` |
| 图片原始格式未知 | `[需核实:原图格式]` |
| 目标路径无写入权限 | `[需核实:输出路径权限]` |
| 图片损坏无法读取 | `[需核实:文件完整性]` |

**示例**：

> 图片 `photo_01.jpg` 无法读取元数据，可能已损坏。当前跳过处理，建议手动检查文件。如需继续处理，请提供该图片的原始尺寸 `[需核实:原图宽高]`。

---

## 五、错误码体系

| 错误码 | 触发场景 | 用户提示话术 | 修正步骤 |
| --- | --- | --- | --- |
| `E001` | 输入路径不存在 | "未找到指定的路径，请检查路径是否正确。" | 1. 确认路径拼写正确<br>2. 确认文件夹/文件存在<br>3. 重新输入 |
| `E002` | 输入路径无读取权限 | "无法读取该路径，请确认有读取权限。" | 1. 检查权限设置<br>2. 更换路径<br>3. 重新执行 |
| `E003` | 不支持的图片格式 | "不支持的图片格式。仅支持：JPEG、PNG、WebP、BMP。" | 1. 转换格式后再处理<br>2. 或使用支持的格式 |
| `E004` | mode 参数无效 | "缩放模式无效。可选：width、height、percent、exact。" | 1. 检查 mode 拼写<br>2. 按提示重新输入 |
| `E005` | value 参数无效 | "缩放值无效，必须为正整数。" | 1. 检查 value 值<br>2. 确认无小数或负数 |
| `E006` | exact 模式缺少宽高数组 | "exact 模式需要提供 [宽,高] 数组。" | 1. 按格式输入，如 `[600,600]` |
| `E007` | 图片文件损坏 | "图片文件可能已损坏，无法读取。" | 1. 检查原图<br>2. 重新导出图片<br>3. 跳过该文件 |
| `E008` | 磁盘空间不足 | "磁盘空间不足，无法保存输出文件。" | 1. 清理磁盘空间<br>2. 更换输出路径 |
| `E009` | 输出目录无写入权限 | "无法写入输出目录，请检查权限。" | 1. 修改目录权限<br>2. 更换输出路径 |

---

## 六、FAQ 反模式对照

| 常见坑 | 反模式（❌） | 正确做法（✅） |
| --- | --- | --- |
| **图片拉伸变形** | 使用 exact 模式将非正方形图强制改为正方形 | 使用 width 或 height 模式保持比例；或先裁剪再缩放 |
| **质量过差** | 将 quality 设为 10 以追求最小体积 | 建议 70-85 之间，视觉无损且体积合理 |
| **格式转换后颜色变化** | PNG 转 JPEG 后透明区域变黑 | 先填充白色背景再转换，或告知用户透明信息会丢失 |
| **忽略元数据丢失** | 处理重要照片后发现 EXIF 丢失 | 处理前明确提示：本工具不保留 EXIF 信息，重要照片请备份原图 |
| **批量处理中途中断** | 50 张图处理到第 30 张崩溃，全部重来 | 程序按文件逐个处理并即时保存，已完成的文件不受影响，重新运行时自动跳过已存在的输出文件 |
| **大小写格式混乱** | 输入 `.JPG` 文件，未识别 | 程序自动忽略大小写，统一按扩展名小写处理 |

---

## 七、渐进式披露

### 速查卡（30 秒上手）

```bash
# 基本用法（Python 代码示例）
from PIL import Image
import os

def resize_image(input_path, output_path, width=None, height=None, percent=None):
    img = Image.open(input_path)
    orig_w, orig_h = img.size
    if width:
        new_h = int(orig_h * width / orig_w)
        img = img.resize((width, new_h), Image.LANCZOS)
    elif height:
        new_w = int(orig_w * height / orig_h)
        img = img.resize((new_w, height), Image.LANCZOS)
    elif percent:
        new_w = int(orig_w * percent / 100)
        new_h = int(orig_h * percent / 100)
        img = img.resize((new_w, new_h), Image.LANCZOS)
    img.save(output_path)
```

### 新手路径

1. 确认输入路径和输出路径。
2. 选择一种缩放模式（建议从 width 开始）。
3. 执行并查看输出摘要。
4. 如有错误，参考错误码表修正。

### 进阶路径

1. 组合使用格式转换 + 质量调整：
   ```bash
   # 示例：批量转 WebP 并压缩
   input_path: /path/to/images
   mode: width
   value: 1200
   output_format: webp
   quality: 75
   ```
2. 批量处理不同子文件夹：
   ```python
   # 递归处理子目录
   for root, dirs, files in os.walk(input_path):
       for file in files:
           if file.lower().endswith(('.jpg', '.jpeg', '.png')):
               process(os.path.join(root, file))
   ```
3. 自定义输出文件命名规则：修改 `output_path` 生成逻辑，加入时间戳或自定义前缀。
4. 配合 shell 脚本批量处理：
   ```bash
   for img in *.jpg; do
       python resize_script.py --input "$img" --mode width --value 800
   done
   ```

### 性能优化建议

| 场景 | 建议 |
| --- | --- |
| 大量小图（<100KB） | 使用多线程处理，提升速度 |
| 少量大图（>5MB） | 单线程处理，避免内存溢出 |
| 内存受限环境 | 分批处理，每次最多 20 张 |
| 需要极致速度 | 降低 LANCZOS 为 BILINEAR 算法（质量略降） |

---

## 附录：完整参数表

| 参数 | 类型 | 必填 | 默认值 | 有效范围 | 说明 |
| --- | --- | --- | --- | --- | --- |
| `input_path` | string | ✅ | 无 | 有效路径 | 输入文件夹或文件 |
| `mode` | string | ✅ | 无 | width/height/percent/exact | 缩放模式 |
| `value` | int/array | ✅ | 无 | 正整数 或 [宽,高] | 缩放值 |
| `output_format` | string | ❌ | 原格式 | jpeg/png/webp/bmp | 输出格式 |
| `quality` | int | ❌ | 85 | 1-100 | 压缩质量（jpeg/webp） |
| `output_dir` | string | ❌ | `./output` | 有效路径 | 输出目录 |
| `overwrite` | bool | ❌ | false | true/false | 是否覆盖同名文件（默认跳过） |

---

*本文档由 AI 辅助生成，提供批量图片处理的操作指导。实际效果因环境与图片内容而异，建议先在小批量样本上验证效果后再正式使用。*

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

## 输出

- 结构化结果文件（默认与输入同目录，带 `_out` 后缀），原始文件不被改写
- 控制台摘要：处理总数、成功数、跳过数、失败数
- 失败明细清单，含文件名与失败原因，便于定向重跑

## 异常处理

| 异常情况 | 表现 | 处理方式 |
|---|---|---|
| 输入文件不存在 | 提示路径错误并退出 | 核对路径，使用绝对路径重试 |
| 文件格式不符 | 该条跳过并计入失败明细 | 转换为受支持格式后重跑该条 |
| 权限不足 | 写入失败 | 更换输出目录或提升目录写权限 |
| 单条数据异常 | 跳过该条，继续处理其余 | 处理结束后查看失败明细定向重跑 |

失败处理原则：**单条失败不中断整批**，全部异常汇总到失败明细，支持只重跑失败项。

## 稳定性保障

- **超时控制**：单条处理设置上限，超时自动跳过并记入失败明细，避免整批卡死。
- **重试策略**：可恢复类错误（临时占用、瞬时 IO 失败）自动重试 3 次，间隔递增。
- **降级方案**：高级解析失败时自动回退到基础解析模式，保证有可用输出而非直接报错。
- **幂等性**：重复执行同一批输入结果一致，不会产生重复追加。

## FAQ 与反模式

**Q：可以直接对原始文件覆盖写入吗？**
A：不建议。默认输出到独立文件，保留原始数据是可回溯的前提。

**Q：处理到一半失败了怎么办？**
A：已完成部分的输出有效，查看失败明细后只重跑失败项即可，无需整批重来。

**反模式 ①**：不做试运行直接批量处理全量数据 —— 参数配错会一次性污染全部输出。

**反模式 ②**：忽略失败明细只看成功数 —— 静默跳过的条目会造成数据缺口。

**反模式 ③**：把工具输出直接作为最终结论 —— 关键字段务必人工抽检。

## 安全声明

- 全流程本地执行，不上传任何用户数据到第三方服务。
- 不读取与任务无关的目录，不写入系统目录。
- 处理含个人信息的数据时，请自行遵守《个人信息保护法》等相关法规。
- 本 Skill 代码由 AI 辅助生成并经自检验证，以 MIT 协议开源，使用者自负使用后果。
