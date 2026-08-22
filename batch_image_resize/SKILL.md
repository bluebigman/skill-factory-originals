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

---

## 二、触发方式与场景映射

| 触发词/短语 | 使用场景 |
|-------------|----------|
| "批量图片缩放" | 有一整个文件夹的图片需要统一尺寸 |
| "图片尺寸调整" | 单张图片需要改宽高 |
| "图片格式转换" | 需要把 BMP 老照片转成 JPG 以便分享 |
| "图片压缩" | 图片太大，需要减小文件体积 |
| "resize images" | 英文环境下的同义指令 |
| "图片批处理" | 综合性的批量处理需求 |
| "图像尺寸修改" | 更口语化的尺寸调整表达 |

---

## 三、标准执行流程

### 前置条件检查

| 检查项 | 要求 | 验证方法 |
|--------|------|----------|
| Python 版本 | 3.8 及以上 | `python --version` |
| Pillow 库 | 已安装 | `pip show Pillow` 或 `python -c "import PIL; print(PIL.__version__)"` |
| 输入路径 | 存在且可读 | `ls -la [路径]` |
| 图片格式 | 符合支持列表 | `file [图片路径]` |
| 单张大小 | ≤ 50MB | `ls -lh [图片路径]` |

若 Pillow 未安装，执行：`pip install Pillow`

### 执行步骤

1. **指定输入路径**：提供文件夹路径（批量）或单文件路径（单张处理）。
2. **选择缩放模式**（四选一，必选）：

   | 模式参数 | 含义 | 示例值 |
   |----------|------|--------|
   | `width` | 按指定宽度等比缩放 | `width=800` |
   | `height` | 按指定高度等比缩放 | `height=600` |
   | `percent` | 按百分比缩放 | `percent=50`（缩小一半） |
   | `exact` | 强制拉伸到指定宽高 | `exact=800x600` |

3. **（可选）指定输出格式**：`output_format=jpg` / `png` / `webp` / `bmp`
4. **（可选）设置质量参数**：`quality=75`（仅对 jpeg/webp 生效，范围 1-95）
5. **确认执行**：系统显示处理摘要（输入路径、图片数量、目标尺寸、输出格式），确认后开始处理。
6. **查看输出**：处理完成后，结果保存在 `<输入目录>/output/` 下，文件名格式为 `原文件名_处理参数.新格式`。

### 输出规范

- 输出目录：`<输入路径>/output/`（自动创建，无需手动建）
- 文件名示例：原图 `photo.jpg`，处理参数 `w800_q75`，输出为 `photo_w800_q75.jpg`
- 处理摘要：每张图处理完成后输出一行摘要，包含原尺寸 → 新尺寸、格式变化、耗时

---

## 四、置信度门控

当遇到以下信息不足的情况，系统会输出 `[需核实:字段]` 占位符，**不会**编造数据：

| 场景 | 输出示例 |
|------|----------|
| 输入路径不存在 | `[需核实:输入路径] 指定的路径不存在，请检查后重试` |
| 图片格式不支持 | `[需核实:图片格式] 文件 xxx.tiff 不在支持列表中（仅支持 jpg/jpeg/png/webp/bmp）` |
| 图片大小超限 | `[需核实:文件大小] 文件 xxx.png 为 62MB，超过 50MB 限制，已跳过` |
| 缩放参数缺失 | `[需核实:缩放模式] 未指定 width/height/percent/exact 任一模式` |
| 质量参数越界 | `[需核实:quality] 质量值 120 超出有效范围（1-95），已自动调整为 95` |

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| `E001` | 输入路径无效 | "路径不存在或不可读" | 检查路径拼写；确认文件夹/文件存在；检查读写权限 |
| `E002` | 不支持的图片格式 | "文件格式不在支持列表内" | 确认扩展名为 jpg/jpeg/png/webp/bmp；或先手动转换格式 |
| `E003` | 图片超过 50MB | "文件大小超出限制" | 先压缩原图；或分批处理；或使用其他工具预处理 |
| `E004` | Pillow 库未安装 | "缺少 Pillow 依赖" | 执行 `pip install Pillow` 后重试 |
| `E005` | 缩放参数冲突 | "同时指定了多个缩放模式" | 只保留一个模式参数；或明确优先级（width > height > percent > exact） |
| `E006` | 输出目录写入失败 | "无法写入 output/ 目录" | 检查磁盘空间；确认目录权限；尝试更换输入路径 |
| `E007` | 处理过程中图片损坏 | "图片文件可能已损坏" | 检查原图完整性；尝试用图片查看器打开；重新导出原图 |
| `E008` | 批量数量超限 | "单次处理超过 500 张上限" | 拆分文件夹分批处理；或使用子文件夹方式分批执行 |

---

## 六、FAQ 反模式对照

### 常见坑 1：缩放后图片模糊

| 反模式 | 正确做法 |
|--------|----------|
| 使用 `NEAREST` 或 `BILINEAR` 重采样 | 使用 `LANCZOS` 重采样（本 Skill 默认），质量优先 |
| 先缩小再放大 | 一次到位，避免二次插值损失 |

### 常见坑 2：透明背景变黑

| 反模式 | 正确做法 |
|----------|----------|
| PNG 转 JPG 时未处理透明通道 | JPG 不支持透明，转换前将透明区域填充为白色或指定背景色 |
| 直接保存 RGBA 模式为 JPG | 先转换为 RGB 模式再保存 |

### 常见坑 3：WebP 压缩后体积反而变大

| 反模式 | 正确做法 |
|----------|----------|
| 对已高度压缩的 JPG 再转 WebP 且 quality 设为 95 | 适当降低 quality（如 75-85），WebP 在同等质量下体积更小 |
| 对小尺寸图片（<100px）做格式转换 | 小图压缩收益有限，建议保持原格式 |

### 常见坑 4：批量处理时部分图片失败导致整体中断

| 反模式 | 正确做法 |
|----------|----------|
| 单张失败即终止全部处理 | 逐张处理，失败图片记录错误码并跳过，继续处理剩余图片 |
| 不查看错误摘要 | 处理结束后查看错误汇总表，针对性修复失败项 |

### 常见坑 5：输出文件名冲突

| 反模式 | 正确做法 |
|----------|----------|
| 不同子文件夹的同名图片输出到同一 output/ 目录 | 输出路径保留相对子目录结构；或文件名中加入子文件夹名前缀 |
| 重复执行相同参数导致覆盖 | 文件名中加入时间戳或递增序号 |

---

## 七、进阶用法示例

### 组合使用格式转换 + 质量调整

```bash
# 将 input/ 下所有 BMP 转为 JPG，质量设为 70
python batch_resize.py --input ./input --output_format jpg --quality 70
```

### 批量处理不同子文件夹

```bash
# 分别处理 assets/ 和 photos/ 两个子目录
python batch_resize.py --input ./assets --width 800
python batch_resize.py --input ./photos --width 800
```

### 自定义输出文件命名规则

修改 `output_path` 生成逻辑，加入时间戳：

```python
import time
timestamp = time.strftime("%Y%m%d_%H%M%S")
output_name = f"{original_stem}_{params}_{timestamp}.{new_format}"
```

### 配合 shell 脚本批量处理

```bash
#!/bin/bash
# 遍历所有子目录，统一缩放到宽度 1200px
for dir in */; do
  python batch_resize.py --input "$dir" --width 1200
done
```

---

## 八、渐进式阅读路径

### 新手路径（5 分钟上手）

1. 阅读「一、能力边界」了解能做什么
2. 阅读「三、标准执行流程」中的前置条件检查
3. 按「执行步骤」操作一次最简单的缩放（指定 width）
4. 查看 output/ 目录确认结果

### 进阶路径（深入使用）

1. 阅读「五、错误码体系」掌握常见问题排查
2. 阅读「六、FAQ 反模式对照」避免踩坑
3. 尝试「七、进阶用法示例」中的组合操作
4. 自定义输出命名规则，适配自己的工作流

---

## 用户协议

使用本 Skill 即表示您同意以下条款：

1. **责任承担**：使用者自行承担使用本 Skill 产生的全部责任。包括但不限于因图片处理导致的文件损坏、数据丢失、版权纠纷等。
2. **禁止反向工程**：不得对本 Skill 的代码、逻辑、文档进行反向工程、反编译、破解或试图提取源代码。
3. **合法使用**：使用者应确保处理的图片具有合法来源和使用权限，不得用于侵权、违法或违反公序良俗的场景。
4. **无担保声明**：本 Skill 按"现状"提供，不附带任何明示或暗示的担保，包括但不限于适销性、特定用途适用性和非侵权保证。
5. **免责范围**：在任何情况下，Skill 作者均不对因使用或无法使用本 Skill 而产生的任何间接、偶然、特殊或后果性损害承担责任。

<!-- user-agreement-injected -->

---

## 许可证（License）

本 Skill 采用 MIT 许可证发布：

```
MIT License

Copyright (c) 2024 图匠工坊

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
