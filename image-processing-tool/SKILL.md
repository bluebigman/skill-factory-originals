---
slug: image-processing-tool
name: image-processing-tool
displayName: 图像批处理 尺寸压缩 格式转换
description: 批量调整图片尺寸、压缩体积、转换格式，支持自检与版本查询。
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
trigger_words: ["图片批量处理", "图像批处理", "批量压缩图片", "图片格式转换", "图片尺寸调整", "图片缩放", "图片优化", "图像转换"]
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# 图像批处理工具 Skill 文档

## 一、能力边界（一页纸速查卡）

### 1.1 能做什么

| 能力项 | 说明 | 支持参数 |
|--------|------|----------|
| 尺寸调整 | 按指定宽高缩放图片 | `--width`, `--height`, `--mode`（fit/fill/stretch） |
| 体积压缩 | 降低图片文件大小 | `--quality`（1-100），`--level`（low/medium/high） |
| 格式转换 | 转换图片编码格式 | `--format`（jpeg/png/webp/avif） |
| 批量处理 | 对目录内全部图片执行统一操作 | `--input-dir`, `--output-dir` |
| 自检功能 | 验证工具链完整性 | `--selftest` |
| 版本查询 | 显示当前版本号 | `--version` |

### 1.2 不能做什么

- 不支持图片内容识别、物体检测、人脸识别等 AI 视觉任务
- 不支持 GIF 动图帧级编辑
- 不支持 RAW 格式（CR2/NEF/ARW 等）直接处理
- 不支持批量重命名（需配合其他工具）
- 不支持云端存储对接（仅本地文件系统）

### 1.3 适用对象

- 电商运营：商品图统一尺寸与压缩
- 前端开发者：Web 图片资源优化
- 内容创作者：多平台配图格式适配
- 文档管理员：扫描件格式统一

---

## 二、触发方式

### 2.1 触发词

用户说出以下任一短语即可激活本 Skill：

| 触发词 | 场景示例 |
|--------|----------|
| 图片批量处理 | "帮我把这个文件夹里的图都处理一下" |
| 图像批处理 | "这批图需要统一改尺寸" |
| 批量压缩图片 | "图片太大了，网页加载慢，压一下" |
| 图片格式转换 | "把 PNG 都转成 WebP" |
| 图片尺寸调整 | "所有图改成 800 宽" |
| 图片缩放 | "缩小到原来的一半" |
| 图片优化 | "优化一下这些图，让它们更小" |
| 图像转换 | "转成 JPG 格式" |

### 2.2 场景映射表

| 用户真实需求 | 触发短语 | 实际执行动作 |
|-------------|----------|--------------|
| 商品图统一为 1000×1000 | "统一尺寸" | 尺寸调整 + 居中裁剪 |
| 网站图片加载慢 | "压缩一下" | 质量压缩 + 格式转换 WebP |
| 微信图片发不出去 | "转成 JPG" | 格式转换 + 尺寸限制 |
| 批量处理前先验证 | "先试试" | 单样本试运行 |

---

## 三、标准流程

### 3.1 前置条件

| 条件项 | 要求 | 检查方式 |
|--------|------|----------|
| 输入目录 | 存在且包含图片文件 | `ls` 或文件管理器确认 |
| 文件命名 | 建议统一前缀（如 `IMG_`、`photo_`） | 目视检查 |
| 磁盘空间 | 剩余空间 ≥ 输出文件预估总量 × 1.5 | `df -h` |
| 工具链 | 已安装依赖（见 3.2） | `--selftest` |

### 3.2 执行步骤

**Step 1：环境自检**

```bash
image-processing-tool --selftest
```

预期输出：

```
[OK] 核心模块加载正常
[OK] 编解码库可用（libjpeg / libpng / libwebp）
[OK] 磁盘写入权限正常
[OK] 版本: 1.0.0
```

**Step 2：单样本试运行**

```bash
image-processing-tool \
  --input-dir ./test_samples \
  --output-dir ./test_output \
  --width 800 \
  --quality 80 \
  --format webp \
  --limit 1
```

检查输出文件：

- 文件名后缀是否正确（`.webp`）
- 文件尺寸是否为 800px 宽
- 文件体积是否在预期范围

**Step 3：批量执行**

```bash
image-processing-tool \
  --input-dir ./originals \
  --output-dir ./processed \
  --width 800 \
  --quality 80 \
  --format webp \
  --backup
```

`--backup` 参数会在 `./processed/backup/` 下保留原始文件副本。

**Step 4：结果校验**

```bash
# 抽查 5 个文件
image-processing-tool --verify --input-dir ./processed --sample 5
```

校验项：

- 文件可解码（无损坏）
- 尺寸符合设定值（±2px 容差）
- 格式正确

### 3.3 输出规范

| 输出项 | 规范 |
|--------|------|
| 文件命名 | 保留原名 + 新扩展名（如 `photo.jpg` → `photo.webp`） |
| 目录结构 | 输出目录自动创建，与输入目录结构一致 |
| 日志文件 | `processing_log.json` 记录每个文件的处理参数与结果 |
| 错误报告 | `error_report.txt` 列出失败文件及原因 |

---

## 四、置信度门控

### 4.1 信息不足时的处理

当用户请求缺少必要参数时，不猜测、不编造，按以下规则输出占位符：

| 缺失参数 | 输出占位 | 示例 |
|----------|----------|------|
| 目标尺寸 | `[需核实:目标宽度]` | "请指定目标宽度，如 800" |
| 压缩质量 | `[需核实:质量等级]` | "请指定质量等级（low/medium/high）" |
| 输出格式 | `[需核实:目标格式]` | "请指定输出格式（jpeg/png/webp/avif）" |
| 输入目录 | `[需核实:输入路径]` | "请提供图片所在目录路径" |

### 4.2 边界值处理

| 参数 | 合法范围 | 超出范围的处理 |
|------|----------|----------------|
| `--width` | 1-10000 | 超出则提示并取最接近的边界值 |
| `--quality` | 1-100 | 超出则提示并取 80 默认值 |
| `--format` | jpeg/png/webp/avif | 其他值报错并列出合法选项 |
| `--limit` | 1-9999 | 超出则提示并取 1000 |

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| `E001` | 输入目录不存在 | "未找到指定目录，请检查路径" | 确认路径正确或创建目录 |
| `E002` | 目录内无图片文件 | "该目录下未发现支持的图片格式" | 确认文件扩展名为 .jpg/.png/.webp/.avif |
| `E003` | 输出目录不可写 | "无法写入输出目录，请检查权限" | 修改目录权限或更换输出路径 |
| `E004` | 图片解码失败 | "文件可能已损坏或格式不支持" | 尝试用图片查看器打开确认文件完整性 |
| `E005` | 编码器不可用 | "当前环境缺少所需编码库" | 运行 `--selftest` 查看缺失项并安装 |
| `E006` | 磁盘空间不足 | "剩余空间不足以完成处理" | 清理磁盘或更换输出位置 |
| `E007` | 参数冲突 | "指定的参数组合不合法" | 查看参数说明，调整冲突项 |

---

## 六、FAQ 反模式

### 6.1 常见坑与反模式对照

| 常见坑 | 反模式（错误做法） | 正确做法 |
|--------|-------------------|----------|
| 原图被覆盖 | 直接对原目录执行处理 | 指定独立输出目录，或使用 `--backup` |
| 质量参数无效 | 认为 quality=100 一定无损 | JPEG 即使 100 也有损，无损请用 PNG |
| 尺寸失真 | 只指定宽度不指定高度导致变形 | 使用 `--mode fit` 保持宽高比 |
| 批量处理失败 | 不试运行直接全量执行 | 先 `--limit 1` 验证，再全量 |
| 格式误解 | 认为 WebP 所有场景都更优 | 兼容性要求高时用 JPEG，透明需求用 PNG |

### 6.2 反模式示例

**反模式 1：无备份批量处理**

```
❌ image-processing-tool --input-dir ./photos --output-dir ./photos --width 800
```

问题：输出目录与输入目录相同，原图被覆盖。

**正确做法：**

```
✅ image-processing-tool --input-dir ./photos --output-dir ./photos_resized --width 800 --backup
```

**反模式 2：忽略宽高比**

```
❌ image-processing-tool --input-dir ./photos --output-dir ./out --width 800 --height 600 --mode stretch
```

问题：stretch 模式强制拉伸，图片变形。

**正确做法：**

```
✅ image-processing-tool --input-dir ./photos --output-dir ./out --width 800 --mode fit
```

---

## 七、渐进式披露

### 7.1 速查卡（30 秒上手）

```
1. 自检：  image-processing-tool --selftest
2. 试跑：  image-processing-tool --input-dir ./test --output-dir ./out --width 800 --limit 1
3. 全量：  image-processing-tool --input-dir ./src --output-dir ./dst --width 800 --quality 80 --format webp
4. 校验：  image-processing-tool --verify --input-dir ./dst --sample 5
```

### 7.2 新手路径（首次使用）

1. 阅读本 Skill 文档的「能力边界」和「标准流程」
2. 准备一个测试目录，放入 2-3 张图片
3. 按速查卡步骤 1-2 执行，观察输出
4. 确认无误后，按步骤 3 执行全量处理
5. 用步骤 4 校验结果

### 7.3 进阶路径（深度使用）

1. 熟悉全部参数组合（见「能力边界」参数表）
2. 理解不同格式的适用场景（JPEG 照片 / PNG 透明 / WebP 网页 / AVIF 高压缩）
3. 掌握 `--mode` 三种模式的差异（fit 等比缩放 / fill 裁剪填充 / stretch 拉伸）
4. 结合 `--quality` 与 `--format` 寻找体积与画质的平衡点
5. 阅读 `processing_log.json` 了解每次处理的详细参数

---

## 八、参数速查表

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `--input-dir` | string | 当前目录 | 输入图片目录 |
| `--output-dir` | string | `./output` | 输出目录 |
| `--width` | int | 原图宽度 | 目标宽度（px） |
| `--height` | int | 原图高度 | 目标高度（px） |
| `--mode` | string | `fit` | 缩放模式：fit/fill/stretch |
| `--quality` | int | 80 | 压缩质量（1-100） |
| `--format` | string | 原格式 | 输出格式：jpeg/png/webp/avif |
| `--limit` | int | 无限制 | 最大处理文件数 |
| `--backup` | flag | 关闭 | 保留原始文件备份 |
| `--verify` | flag | 关闭 | 校验模式 |
| `--sample` | int | 全部 | 校验时抽查数量 |
| `--selftest` | flag | - | 运行环境自检 |
| `--version` | flag | - | 显示版本号 |

---

## 九、用户协议

<!-- user-agreement-injected -->

**使用本 Skill 即表示您同意以下条款：**

1. **责任承担**：使用者自行承担因使用本 Skill 产生的全部责任。包括但不限于数据丢失、文件损坏、处理结果不符合预期等情形。
2. **禁止反向工程**：不得对本 Skill 的代码、逻辑、文档进行反向工程、反编译、破解或试图提取源代码。
3. **合法使用**：使用者应确保处理的内容不违反任何法律法规，不侵犯第三方权益。
4. **无担保**：本 Skill 按"现状"提供，不附带任何明示或暗示的担保。
5. **修改与终止**：作者保留随时修改、更新或终止本 Skill 的权利，恕不另行通知。

---

## 十、许可证（License）

<!-- professional-license-embedded -->

**MIT License**

Copyright (c) 2024 原创作者（自持版权）

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

*文档版本：1.0.0 | 最后更新：2024-01-01*
