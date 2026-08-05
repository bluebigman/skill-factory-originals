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
author: 像素工坊
agent_created: true
trigger_words: ["batch-image-resize", "批量缩放图片", "图片压缩", "图片格式转换", "图片批处理", "图像尺寸调整"]
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# 批量图片处理 Skill 文档

## 一、能力边界（速查卡）

### 1.1 能做什么

| 功能项 | 说明 | 典型参数 |
|--------|------|----------|
| 批量缩放 | 按指定宽高或百分比调整图片尺寸 | `--width 1920` 或 `--scale 50%` |
| 批量压缩 | 调整图片质量以减小文件体积 | `--quality 80`（JPEG/WebP） |
| 格式转换 | 在 JPEG/PNG/WebP/AVIF 之间互转 | `--format webp` |
| EXIF 处理 | 保留或剥离元数据 | `--strip-exif` / `--keep-exif` |
| 目录归档 | 输出到独立目录，保留原文件名 | `--output ./processed/` |

### 1.2 不能做什么

- 不支持动图（GIF/APNG）的逐帧处理
- 不支持 RAW 格式（CR2/NEF/ARW 等）直接处理
- 不支持批量重命名（需配合其他工具）
- 不支持图片内容识别或智能裁剪

### 1.3 适用对象

- 网站开发者需要压缩前端图片资源
- 电商运营批量处理商品图
- 摄影爱好者需要统一照片尺寸
- 文档管理员需要转换图片格式归档

---

## 二、触发方式

### 2.1 触发词

直接使用以下任一短语即可唤起本 Skill：

- `batch-image-resize`
- `批量缩放图片`
- `图片压缩`
- `图片格式转换`
- `图片批处理`
- `图像尺寸调整`

### 2.2 场景映射表

| 你说的话 | 实际需求 | 推荐命令 |
|----------|----------|----------|
| "把这几张图缩小点" | 按比例缩放 | `--scale 50%` |
| "图片太大传不上去" | 压缩文件体积 | `--quality 70 --format jpeg` |
| "网站要 webp 格式" | 格式转换 | `--format webp` |
| "帮我统一一下尺寸" | 固定宽高 | `--width 1200 --height 800` |
| "照片信息别泄露" | 剥离 EXIF | `--strip-exif` |

---

## 三、标准流程

### 3.1 前置条件

- 已安装 Node.js 14+ 或 Python 3.8+
- 目标图片目录可读，输出目录可写
- 磁盘剩余空间 ≥ 原图总大小的 1.5 倍

### 3.2 执行步骤

1. **确认输入目录**：检查图片是否在指定目录内，支持递归扫描子目录（`--recursive`）。
2. **设定处理参数**：根据需求组合以下参数：

   | 参数 | 类型 | 默认值 | 说明 |
   |------|------|--------|------|
   | `--width` | int | 无 | 目标宽度（px） |
   | `--height` | int | 无 | 目标高度（px） |
   | `--scale` | str | 无 | 缩放百分比，如 `50%` |
   | `--quality` | int | 85 | 压缩质量（1-100） |
   | `--format` | str | 原格式 | 输出格式：jpeg/png/webp/avif |
   | `--strip-exif` | flag | 关 | 剥离 EXIF 元数据 |
   | `--keep-exif` | flag | 开 | 保留 EXIF 元数据 |
   | `--output` | str | `./output/` | 输出目录 |
   | `--recursive` | flag | 关 | 递归处理子目录 |
   | `--selftest` | flag | 关 | 运行自检 |
   | `--version` | flag | 关 | 显示版本号 |

3. **执行命令**：示例：
   ```bash
   batch-image-resize --input ./photos/ --output ./processed/ --width 1920 --quality 80 --format webp --strip-exif --recursive
   ```
4. **检查输出**：处理完成后，查看输出目录中的文件列表和日志报告。
5. **验证结果**：抽查 3-5 张图片，确认尺寸、格式、文件大小符合预期。

### 3.3 输出规范

- 输出文件命名规则：`原文件名_处理标记.新格式`（如 `IMG_001_1920w.webp`）
- 处理完成后输出汇总报告：处理总数、成功数、失败数、总耗时
- 失败文件单独列出，并注明失败原因

---

## 四、置信度门控

当遇到以下情况时，**不得编造结果**，应输出占位符 `[需核实:字段]`：

| 场景 | 占位符示例 |
|------|------------|
| 图片尺寸未知 | `[需核实:原图尺寸]` |
| 输出格式不支持 | `[需核实:支持的格式列表]` |
| 磁盘空间不足 | `[需核实:可用空间]` |
| 参数冲突（如同时指定 width 和 scale） | `[需核实:参数优先级]` |

**处理原则**：宁可让用户补充信息，也不猜测输出。

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| `E001` | 输入目录不存在 | "未找到输入目录，请检查路径" | 确认路径是否正确，或使用绝对路径 |
| `E002` | 无有效图片文件 | "目录中没有可处理的图片" | 检查文件扩展名是否在支持列表内 |
| `E003` | 输出目录不可写 | "无法写入输出目录" | 检查目录权限，或更换输出路径 |
| `E004` | 格式转换失败 | "图片格式转换出错" | 确认源格式是否支持，尝试先转为 PNG |
| `E005` | 内存不足 | "处理大图时内存溢出" | 降低 `--quality` 或分批处理 |
| `E006` | 参数冲突 | "width 和 scale 不能同时指定" | 只保留一个尺寸参数 |
| `E007` | EXIF 写入失败 | "元数据写入失败" | 使用 `--strip-exif` 忽略元数据 |

---

## 六、FAQ 反模式

### 6.1 常见坑

| 坑 | 反模式 | 正确做法 |
|----|--------|----------|
| 压缩后图片模糊 | 直接 `--quality 30` | 先试 `--quality 70`，观察效果再逐步降低 |
| 透明背景变黑 | PNG 转 JPEG 不处理 Alpha | 先合成背景色，或改用 WebP 格式 |
| 文件名冲突 | 覆盖原文件 | 始终使用 `--output` 指定独立目录 |
| 处理速度慢 | 一次性处理 1000+ 张 | 分批处理，每批 200 张左右 |
| 元数据泄露 | 忘记 `--strip-exif` | 涉及隐私图片时默认加 `--strip-exif` |

### 6.2 反模式对照表

| 错误做法 | 后果 | 推荐替代 |
|----------|------|----------|
| 用 `--scale 10%` 压缩大图 | 图片几乎不可用 | 用 `--width 800` 指定合理宽度 |
| 所有图片统一 `--quality 50` | 部分图片质量损失严重 | 按图片类型分别设置质量 |
| 直接覆盖原图 | 无法恢复 | 输出到新目录，确认后再替换 |

---

## 七、渐进式披露

### 7.1 速查卡（30 秒上手）

```bash
# 最常用：批量压缩为 WebP
batch-image-resize --input ./in/ --output ./out/ --format webp --quality 80

# 常用：统一宽度
batch-image-resize --input ./in/ --output ./out/ --width 1200

# 常用：剥离 EXIF
batch-image-resize --input ./in/ --output ./out/ --strip-exif
```

### 7.2 新手阅读路径

1. 先读「能力边界」了解能做什么
2. 用「速查卡」里的三条命令跑通流程
3. 遇到问题查「错误码体系」
4. 进阶需求再看「标准流程」完整参数表

### 7.3 进阶阅读路径

1. 完整阅读「标准流程」掌握全部参数
2. 研究「FAQ 反模式」避免常见错误
3. 组合参数实现复杂需求（如：缩放+压缩+转格式+剥离 EXIF）
4. 使用 `--recursive` 处理嵌套目录结构

---

## 八、自检与版本

### 8.1 自检命令

```bash
batch-image-resize --selftest
```

自检内容：
- 环境依赖是否完整
- 支持的图片格式列表
- 临时文件读写权限
- 基本缩放/压缩功能验证

### 8.2 版本信息

```bash
batch-image-resize --version
```

当前版本：1.0.0

---

## 用户协议

使用本 Skill 即表示您同意以下条款：

1. **责任承担**：使用者自行承担使用本 Skill 产生的全部责任。包括但不限于图片处理结果、数据丢失、隐私泄露等风险。
2. **禁止反向工程**：不得对本 Skill 进行反向工程、反编译、破解或试图获取源代码逻辑。
3. **合规使用**：使用者需确保处理的图片内容合法合规，不得用于侵权、违法或违反公序良俗的场景。
4. **无担保声明**：本 Skill 按"现状"提供，不附带任何明示或暗示的担保。

<!-- user-agreement-injected -->

---

## 许可证（License）

MIT License

Copyright (c) 2024 像素工坊

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

<!-- professional-license-embedded -->
