---
slug: imagecraft-android
name: imagecraft-android
displayName: 安卓图像压缩 格式转换 批量处理
description: 面向安卓开发者的图片压缩、格式转换与批量处理规范流程。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 林墨工
agent_created: true
trigger_words: ["图片批量处理", "图片压缩", "格式转换", "imagecraft", "android", "图像优化", "安卓资源瘦身"]
---

> 本内容由 AI 生成，仅供学习参考 <!-- ai-generated-notice -->

# ImageCraft for Android — 技能文档

## 一、能力边界（一页纸速查卡）

### 1.1 能做什么

| 能力项 | 说明 | 典型场景 |
|--------|------|----------|
| 单张压缩 | 对单张图片按质量参数（0-100）重新编码 | 快速验证某张图的压缩潜力 |
| 批量压缩 | 对目录内全部受支持图片统一压缩 | 上线前整体瘦身 APK 资源 |
| 格式转换 | PNG/JPG/WebP/HEIC 静态图互转 | 将 HEIC 转为 WebP 以减小体积 |
| 预设策略处理 | 读取 `custom_policy.yaml` 执行组合操作（压缩+缩放+转换） | 按项目规范一键处理整批资源 |
| 增量处理 | 仅处理修改时间晚于上次处理的文件 | 日常开发中只处理新增/修改的图片 |
| 报告输出 | 每次批量操作生成 JSON 报告，含体积变化、耗时、成功率 | 追踪优化效果，建立质量基线 |

### 1.2 不能做什么

| 限制项 | 说明 |
|--------|------|
| 不支持动图 | GIF/APNG/WebP 动图不在处理范围内 |
| 不支持有损→无损逆向 | 已压缩的 JPG 无法通过本工具恢复为无损 PNG |
| 不做视觉质量评分 | 工具只输出体积数据，画质需人工确认 |
| 不处理超大图（>100MB） | 单文件超过 100MB 时跳过并记录警告 |
| 不处理 EXIF 信息 | 转换过程中不保留也不修改 EXIF 元数据 |

### 1.3 适用对象

- Android 应用开发者（Java/Kotlin）
- 移动端 UI 资源维护人员
- 需要将图片资源接入 CI/CD 流水线的工程效能团队

---

## 二、触发方式与场景映射

### 2.1 触发词

直接使用以下任一词汇即可唤起本技能：

> 图片批量处理、图片压缩、格式转换、imagecraft、android、图像优化、安卓资源瘦身

### 2.2 场景映射表

| 你说的话（大白话） | 技能实际做的事 |
|-------------------|----------------|
| "帮我把 res 里的图压一下" | 扫描 `res/` 下所有受支持图片，按默认质量 80 执行压缩，输出报告 |
| "这些 PNG 能转成 WebP 吗" | 对指定目录执行 PNG→WebP 转换，输出体积对比 |
| "只处理今天改过的图" | 启用增量模式，仅处理 mtime 晚于上次记录的图片 |
| "按项目规范处理一遍" | 读取 `custom_policy.yaml`，按其中定义的参数执行组合处理 |
| "看看压缩效果怎么样" | 执行单张压缩测试，输出压缩前后体积对比，供人工确认 |

---

## 三、标准流程

### 3.1 前置条件

| 检查项 | 要求 | 失败处理 |
|--------|------|----------|
| 输入目录 | 存在且可读 | 报错 `E1001`，提示检查路径 |
| 图片格式 | 仅限 PNG/JPG/WebP/HEIC 静态图 | 跳过不支持格式，记录警告 |
| 磁盘空间 | 剩余空间 ≥ 待处理图片总大小的 2 倍 | 报错 `E1002`，提示清理磁盘 |
| 工具链 | `imagecraft` 命令可用 | 报错 `E1003`，提示安装或配置 PATH |

### 3.2 执行步骤

#### 步骤 1：环境自检

```bash
imagecraft --selftest
```

预期输出：`[OK] 环境就绪` 或列出缺失项。

#### 步骤 2：单张压缩测试

```bash
imagecraft compress --input sample.png --quality 80
```

参数说明：

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `--input` | string | 必填 | 输入图片路径 |
| `--quality` | int | 80 | 压缩质量（0-100），越高画质越好、体积越大 |
| `--output` | string | 自动生成 | 输出路径，默认在源文件旁生成 `_compressed` 后缀文件 |

#### 步骤 3：批量格式转换

```bash
imagecraft convert --input-dir res/drawable-hdpi --from png --to webp
```

参数说明：

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `--input-dir` | string | 必填 | 源目录（递归扫描） |
| `--from` | string | 必填 | 源格式（png/jpg/webp/heic） |
| `--to` | string | 必填 | 目标格式（png/jpg/webp） |
| `--recursive` | bool | true | 是否递归子目录 |

#### 步骤 4：预设策略批量处理

创建 `custom_policy.yaml`：

```yaml
# 策略示例
max_width: 512        # 超过此宽度则等比缩放
max_height: 512       # 超过此高度则等比缩放
quality: 80           # 压缩质量
target_format: webp   # 目标格式（可选，不填则保持原格式）
incremental: true     # 仅处理修改时间晚于上次的图片
```

执行：

```bash
imagecraft batch --policy custom_policy.yaml --input-dir res/
```

#### 步骤 5：查看报告

每次批量操作后，在输出目录生成 `report_<timestamp>.json`，结构如下：

```json
{
  "total": 128,
  "success": 125,
  "failed": 3,
  "total_size_before": 52428800,
  "total_size_after": 20971520,
  "reduction_ratio": 0.6,
  "items": [
    {
      "file": "res/drawable-hdpi/ic_launcher.png",
      "size_before": 102400,
      "size_after": 40960,
      "format_before": "png",
      "format_after": "webp",
      "duration_ms": 12
    }
  ],
  "failures": [
    {
      "file": "res/drawable-xxhdpi/broken.png",
      "error": "E2003",
      "message": "文件损坏或格式识别失败"
    }
  ]
}
```

### 3.3 输出规范

- 所有报告统一为 JSON 格式，UTF-8 编码
- 报告文件名格式：`report_YYYYMMDD_HHMMSS.json`
- 处理后的图片文件命名规则：`<原名>_<质量>.<新格式>`（如 `icon_80.webp`）
- 日志输出到 stderr，报告写入 stdout 或指定文件

---

## 四、置信度门控

当遇到以下情况时，**不得编造数据或猜测结果**，应输出占位符 `[需核实:字段]`：

| 场景 | 占位符示例 |
|------|-----------|
| 不确定图片原始尺寸 | `[需核实:原始尺寸]` |
| 不确定目标格式是否支持透明通道 | `[需核实:透明通道支持]` |
| 不确定 HEIC 解码库是否已安装 | `[需核实:HEIC解码库]` |
| 不确定 CI 环境变量 | `[需核实:CI环境变量]` |

同时输出提示：`信息不足，请补充上述字段后再执行操作。`

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| `E1001` | 输入目录不存在 | "指定的输入目录不存在，请检查路径。" | 1. 确认路径拼写；2. 使用 `ls` 验证目录存在；3. 重新执行 |
| `E1002` | 磁盘空间不足 | "磁盘剩余空间不足，需要至少待处理图片总大小的 2 倍空间。" | 1. 清理临时文件；2. 更换输出目录；3. 重新执行 |
| `E1003` | 工具链不可用 | "imagecraft 命令未找到，请检查安装。" | 1. 运行 `which imagecraft`；2. 确认安装路径；3. 配置 PATH 或使用全路径 |
| `E2001` | 不支持的输入格式 | "文件格式不支持，仅支持 PNG/JPG/WebP/HEIC 静态图。" | 1. 检查文件扩展名；2. 使用 `file` 命令确认实际格式；3. 转换格式后重试 |
| `E2002` | 质量参数越界 | "质量参数必须在 0-100 之间。" | 1. 检查传入参数；2. 修正为合法值；3. 重新执行 |
| `E2003` | 文件损坏 | "文件损坏或格式识别失败，无法处理。" | 1. 检查源文件完整性；2. 重新导出图片；3. 跳过该文件 |
| `E3001` | 策略文件解析失败 | "custom_policy.yaml 格式错误，无法解析。" | 1. 检查 YAML 语法；2. 参考文档中的示例；3. 修正后重试 |
| `E3002` | 增量模式无基线 | "增量模式需要上一次处理的记录文件，未找到。" | 1. 先执行一次全量处理；2. 或手动指定基线文件；3. 重新执行 |

---

## 六、FAQ 反模式对照

### 常见坑 1：直接转换 HEIC → WebP

**反模式**：直接执行 `imagecraft convert --from heic --to webp`，结果报错或输出黑图。

**正确做法**：HEIC 解码与 WebP 编码之间存在兼容性问题，应分两步走：

```bash
# 第一步：HEIC → PNG（无损中间格式）
imagecraft convert --from heic --to png --input-dir photos/

# 第二步：PNG → WebP
imagecraft convert --from png --to webp --input-dir photos/
```

### 常见坑 2：忽略透明通道

**反模式**：将带透明通道的 PNG 直接转为 JPG，透明区域变成黑色块。

**正确做法**：转换前检查图片是否含 alpha 通道。若含透明通道，目标格式应选 WebP（支持透明）而非 JPG。

```bash
# 检查透明通道
imagecraft inspect --input icon.png
# 输出: alpha_channel: true

# 正确转换
imagecraft convert --from png --to webp --input-dir res/
```

### 常见坑 3：质量参数一刀切

**反模式**：所有图片统一用 quality=50，导致文字截图模糊不可读。

**正确做法**：按图片类型分组设置质量参数：

| 图片类型 | 建议质量范围 | 说明 |
|----------|-------------|------|
| 图标/Logo | 85-95 | 边缘清晰度要求高 |
| 照片/渐变 | 70-80 | 视觉容忍度较高 |
| 截图/文字 | 90-95 | 文字边缘不可失真 |

### 常见坑 4：CI 中重复处理已压缩图片

**反模式**：每次构建都全量压缩，已压缩的图片再次压缩反而增大体积。

**正确做法**：启用增量模式，或维护一个已处理文件清单：

```bash
imagecraft batch --policy custom_policy.yaml --input-dir res/ --incremental
```

### 常见坑 5：忽略报告中的失败项

**反模式**：只看总成功率，忽略失败项，导致部分图片未处理就上线。

**正确做法**：每次处理后检查 `failures` 数组，对失败项单独处理：

```bash
# 提取失败文件列表
jq '.failures[].file' report_20240101_120000.json
```

---

## 七、渐进式披露

### 7.1 新手路径（首次使用）

1. 阅读「能力边界」速查卡，了解工具能做什么
2. 执行 `imagecraft --selftest` 确认环境
3. 用一张测试图执行单张压缩，对比画质
4. 查看生成的 JSON 报告，理解体积变化数据
5. 尝试不同质量参数（70/80/90），找到可接受阈值

### 7.2 进阶路径（日常使用）

1. 编写自定义策略配置文件（JSON/YAML）
2. 处理 HEIC 兼容性转换链：HEIC → PNG → WebP（分两步，避免直接转换失败）
3. 实现增量压缩：仅处理修改时间晚于上次处理的文件
4. 集成到 CI/CD：在 Gradle 构建前执行批量处理任务
5. 建立质量回归基线：保存一组标准测试图，每次调整策略后对比输出

### 7.3 专家路径（深度定制）

1. 扩展策略文件，支持按目录/按文件类型差异化配置
2. 编写后处理脚本，自动将报告中的体积缩减数据推送到监控面板
3. 结合 AAPT2 资源打包流程，在资源编译前完成图片优化
4. 建立多套策略（开发版/发布版），按构建类型自动切换

---

## 八、用户协议

**使用本 Skill 即表示您同意以下条款：**

1. **责任承担**：使用者自行承担因使用本 Skill 产生的全部责任。包括但不限于图片处理结果不符合预期、数据丢失、构建失败等情形。
2. **禁止反向工程**：不得对本 Skill 的提示词、内部逻辑进行反向工程、破解、提取或二次分发。
3. **合规使用**：使用者应确保处理图片的合法授权，不得处理侵权或违规内容。
4. **无担保声明**：本 Skill 按"现状"提供，不附带任何明示或暗示的担保。

<!-- user-agreement-injected -->

---

## 九、许可证（License）

本 Skill 采用 MIT 许可证发布：

```
MIT License

Copyright (c) 2024 林墨工

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
