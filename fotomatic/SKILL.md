---
slug: fotomatic
name: fotomatic
displayName: 图像快照 参数解析 结构化提取
description: 将图片或链接解析为结构化参数，输出带置信度的标准结果。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: LinguaForge
agent_created: true
trigger_words: ["fotomatic", "闪光快照", "图片参数提取", "快照解析", "photo widget", "图像参数识别", "视觉信息结构化"]
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# fotomatic — 图像快照参数解析 Skill

## 一、能力边界（一页纸速查卡）

### 1.1 能做什么

| 能力项 | 说明 | 示例 |
|--------|------|------|
| 图片解析 | 从本地图片文件提取结构化参数 | `fotomatic ./sample.jpg` |
| 链接解析 | 从远程图片 URL 提取结构化参数 | `fotomatic https://example.com/img.png` |
| 批量处理 | 对目录下多个文件依次解析 | `fotomatic ./batch/` |
| 置信度输出 | 每个字段附带可信程度标记 | `confidence: 0.92` |
| 自检模式 | 验证工具链是否就绪 | `fotomatic --selftest` |
| 版本查询 | 输出当前版本号 | `fotomatic --version` |

### 1.2 不能做什么

| 限制项 | 说明 |
|--------|------|
| 不生成图片 | 仅解析，不合成、不编辑图像内容 |
| 不识别模糊图片 | 分辨率过低或严重失真的图片，置信度会显著下降 |
| 不处理视频帧 | 仅支持静态图片格式（jpg/png/webp/bmp） |
| 不推断缺失信息 | 图片中不存在的参数，输出 `[需核实:字段]` 占位，不猜测 |
| 不保留原图 | 解析过程不修改原始文件，但也不会自动备份 |

### 1.3 适用对象

- 需要从产品截图、设计稿、UI 原型中快速提取尺寸、颜色、布局参数的开发者
- 需要将视觉素材批量转为结构化配置项的运维或测试人员
- 需要将图片链接转为标准参数文档的内容运营人员

---

## 二、触发方式与场景映射

### 2.1 触发词

| 触发词 | 使用场景 |
|--------|----------|
| `fotomatic` | 直接调用工具主命令 |
| `闪光快照` | 口语化表达，适合对话式交互 |
| `图片参数提取` | 明确表达提取意图 |
| `快照解析` | 强调解析动作 |
| `photo widget` | 英文场景下的同义触发 |
| `图像参数识别` | 强调识别过程 |
| `视觉信息结构化` | 强调输出格式的规范性 |

### 2.2 场景映射表

| 用户说（大白话） | 实际执行动作 |
|------------------|--------------|
| "帮我把这张图里的参数弄出来" | 解析单张图片，输出结构化参数 |
| "这个链接里的图，提取一下信息" | 下载远程图片并解析 |
| "这一堆图都处理一下" | 批量解析目录下所有图片 |
| "看看工具能不能用" | 执行 `--selftest` 自检 |
| "你是什么版本" | 执行 `--version` 查看版本 |

---

## 三、标准流程

### 3.1 前置条件

| 条件 | 要求 | 检查方式 |
|------|------|----------|
| 文件格式 | jpg / png / webp / bmp | 文件扩展名或 MIME 类型 |
| 文件可读 | 文件存在且权限可读 | `ls -l` 或 `test -r` |
| 网络可用 | 解析远程链接时需要 | `curl -I` 测试可达性 |
| 工具链就绪 | 依赖库已安装 | `fotomatic --selftest` |

### 3.2 执行步骤

1. **准备输入**：将待处理文件放入同一目录，确认命名规范一致（如 `img_001.jpg`、`img_002.jpg`）。
2. **试运行**：先用单个样本执行，核对输出字段与格式是否符合预期。
   ```bash
   fotomatic ./sample.jpg
   ```
3. **批量执行**：确认无误后对全量数据执行，并保留原始文件备份。
   ```bash
   fotomatic ./batch/
   ```
4. **校验结果**：抽查输出条目，核对关键字段与源数据一致。

### 3.3 输出规范

输出为 JSON 格式，结构如下：

```json
{
  "source": "sample.jpg",
  "width": 1920,
  "height": 1080,
  "format": "jpg",
  "color_space": "RGB",
  "dominant_color": "#2C3E50",
  "confidence": {
    "width": 0.99,
    "height": 0.99,
    "format": 1.0,
    "color_space": 0.95,
    "dominant_color": 0.87
  },
  "warnings": []
}
```

字段说明：

| 字段 | 类型 | 说明 |
|------|------|------|
| `source` | string | 输入文件路径或 URL |
| `width` / `height` | int | 像素尺寸 |
| `format` | string | 文件格式 |
| `color_space` | string | 色彩空间（RGB/CMYK/GRAY） |
| `dominant_color` | string | 主色调 HEX 值 |
| `confidence` | object | 各字段置信度（0~1） |
| `warnings` | array | 警告信息列表 |

---

## 四、置信度门控

### 4.1 置信度阈值

| 置信度区间 | 处理策略 |
|------------|----------|
| 0.90 ~ 1.00 | 正常输出，无需额外标记 |
| 0.70 ~ 0.89 | 输出字段，附加 `"note": "低置信度，请人工复核"` |
| 0.00 ~ 0.69 | 输出 `[需核实:字段名]` 占位，不提供猜测值 |

### 4.2 信息不足时的处理

当图片中无法提取某个字段时，遵循以下规则：

- **不编造**：不根据经验或猜测填充值。
- **显式占位**：输出 `[需核实:字段名]`。
- **记录原因**：在 `warnings` 中注明缺失原因（如 `"无法识别主色调：图片为灰度图"`）。

### 4.3 示例

```json
{
  "source": "blurry.png",
  "width": 800,
  "height": 600,
  "format": "png",
  "color_space": "RGB",
  "dominant_color": "[需核实:dominant_color]",
  "confidence": {
    "width": 0.98,
    "height": 0.98,
    "format": 1.0,
    "color_space": 0.90,
    "dominant_color": 0.45
  },
  "warnings": ["图片存在明显噪点，主色调识别置信度不足"]
}
```

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| `E001` | 文件不存在 | "指定路径下未找到文件，请检查路径是否正确" | 确认路径，使用 `ls` 查看目录内容 |
| `E002` | 格式不支持 | "该文件格式不在支持列表中（jpg/png/webp/bmp）" | 转换格式后重试 |
| `E003` | 文件损坏 | "文件无法正常解码，可能已损坏" | 重新导出或下载文件 |
| `E004` | 网络不可达 | "无法访问远程链接，请检查网络或链接有效性" | 使用 `curl -I` 测试链接 |
| `E005` | 权限不足 | "当前用户无读取该文件的权限" | 使用 `chmod` 调整权限 |
| `E006` | 批量任务中断 | "批量处理在第 N 个文件处中断" | 查看日志，跳过已处理文件后重试 |

---

## 六、FAQ 反模式

### 6.1 常见坑与反模式对照

| 常见坑 | 反模式（错误做法） | 正确做法 |
|--------|---------------------|----------|
| 批量处理前不试运行 | 直接对全量数据执行，结果格式不符 | 先单样本试运行，确认输出格式 |
| 忽略置信度标记 | 直接使用低置信度字段 | 对置信度 < 0.90 的字段人工复核 |
| 覆盖原始文件 | 输出结果直接写回原文件 | 保留原始文件，输出到独立目录 |
| 不检查网络状态 | 远程链接解析失败后反复重试 | 先 `curl -I` 验证链接可达性 |
| 忽略警告信息 | 只关注主字段，不看 `warnings` | 逐条阅读警告，判断是否需要处理 |

### 6.2 反模式示例

**错误做法**：
```bash
# 直接批量执行，未试运行
fotomatic ./all_images/
```

**正确做法**：
```bash
# 先试运行单个样本
fotomatic ./all_images/img_001.jpg

# 确认输出格式无误后，再批量执行
fotomatic ./all_images/
```

---

## 七、渐进式披露

### 7.1 速查卡（30 秒上手）

```
1. 放文件 → 2. 试运行 → 3. 批量跑 → 4. 查结果
```

### 7.2 分层次阅读路径

**新手路径**（首次使用）：
1. 阅读「能力边界」了解工具能做什么。
2. 阅读「标准流程」按步骤执行一次单样本解析。
3. 阅读「输出规范」理解返回字段含义。

**进阶路径**（深度使用）：
1. 阅读「置信度门控」掌握低置信度字段的处理策略。
2. 阅读「错误码体系」熟悉常见问题的排查方法。
3. 阅读「FAQ 反模式」避免踩坑。

---

## 八、用户协议

<!-- user-agreement-injected -->

使用本 Skill 即表示您同意以下条款：

1. **责任承担**：使用者自行承担因使用本 Skill 产生的全部责任。包括但不限于因解析结果不准确、数据丢失、操作失误等造成的直接或间接损失。
2. **禁止反向工程**：不得对本 Skill 的源代码、算法逻辑进行反向工程、反编译、破解或试图提取底层实现。
3. **合规使用**：使用者应确保输入数据来源合法，不得使用本 Skill 处理侵权、违法或违反公序良俗的内容。
4. **无担保声明**：本 Skill 按"现状"提供，不附带任何明示或暗示的担保，包括但不限于适销性、特定用途适用性和非侵权性。

---

## 九、许可证（License）

<!-- professional-license-embedded -->

### MIT License

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

*本 Skill 由 AI 辅助生成，仅供参考。使用前请阅读相关文档。*
