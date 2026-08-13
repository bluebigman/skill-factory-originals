---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: skill-19622
name: skill-19622
displayName: 录屏操作演示 智能步骤生成
description: 从录屏自动提取操作步骤，生成图文并茂的演示文档。
version: 1.0.1
rules_version: cpr-20260813-n401
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/skill-19622
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: FlowForge Studio
agent_created: true
trigger_words: ["操作演示", "录屏转步骤", "屏幕录制处理", "演示文稿生成", "操作流程提取"]
---

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->


> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# 录屏操作演示 智能步骤生成

## 一、能力边界（一页纸速查卡）

本 Skill 专注于将操作演示录屏转化为结构化的步骤文档。它不是一个通用的视频编辑器，也不是 OCR 文字识别工具，更不是录屏软件本身。

| 能力维度 | 支持 | 不支持 |
|---------|------|--------|
| 输入格式 | MP4、MOV、AVI 等常见视频格式 | 音频文件、纯图片序列 |
| 帧提取 | 支持自定义间隔（默认 2 秒） | 不支持实时流处理 |
| 差异分析 | 相邻帧像素级对比，识别变化区域 | 不支持语义理解（如"用户意图"） |
| OCR 识别 | 中文 + 英文，基于 pytesseract | 不支持手写体、艺术字 |
| 文字记录辅助 | 支持 TXT/MD 文件作为步骤描述来源 | 不支持 PDF、Word 文档直接解析 |
| 输出格式 | Markdown 步骤文档（含时间戳、截图路径） | 不支持 PPT、HTML 直接生成 |
| 处理时长 | 建议单段 ≤ 10 分钟 | 不支持超长视频（> 1 小时） |

**适用对象**：需要制作软件教程、操作手册、培训材料的技术文档工程师、产品经理、培训讲师、技术支持人员。

**不适用场景**：游戏高光时刻剪辑、监控视频分析、人脸识别、物体追踪。

---

## 二、触发方式

当用户输入以下内容时，本 Skill 应被激活：

| 用户可能说的话 | 触发判断 | 响应动作 |
|--------------|---------|---------|
| "帮我处理这个操作演示视频" | 命中触发词"操作演示" | 进入标准处理流程 |
| "把录屏变成步骤文档" | 命中"录屏转步骤" | 进入标准处理流程 |
| "这段屏幕录制怎么整理" | 命中"屏幕录制处理" | 先询问视频路径和输出需求 |
| "生成一个演示文稿" | 命中"演示文稿生成" | 确认是否涉及录屏处理 |
| "提取操作流程" | 命中"操作流程提取" | 确认输入是否为视频文件 |

**场景映射表**：

| 用户场景 | 处理模式 |
|---------|---------|
| 录了一段软件操作视频，想变成图文教程 | 标准模式：帧提取 → 差异分析 → OCR → 步骤生成 |
| 有录屏 + 一份操作文字记录 | 优先模式：文字记录为主，截图辅助 |
| 录屏太长，想分段处理 | 分段模式：按阶段切割后逐一处理 |
| 操作太快，步骤丢失 | 慢速模式：调整帧提取间隔为 5 秒 |

---

## 三、标准流程

### 前置条件

1. 已安装 Python 3.8+ 环境
2. 已安装以下依赖库：
   ```bash
   pip install pillow pytesseract opencv-python
   ```
3. 已安装 Tesseract OCR 引擎（含中文语言包 chi_sim）
4. 已安装 FFmpeg 并加入系统 PATH
5. 输入视频文件路径可访问，且格式受支持

### 执行步骤

**Step 1：环境自检**

运行以下命令确认工具链完整：

```bash
ffmpeg -version | head -n 1
python -c "from PIL import Image; print('Pillow OK')"
python -c "import pytesseract; print('pytesseract OK')"
tesseract --list-langs | grep -E "chi_sim|eng"
```

若任一检查失败，输出错误码 `E001` 并提示安装指引。

**Step 2：帧提取**

使用 FFmpeg 按固定间隔提取关键帧：

```bash
ffmpeg -i input.mp4 -vf "fps=1/2" -q:v 2 frames/frame_%04d.jpg
```

参数说明：

| 参数 | 默认值 | 说明 |
|------|-------|------|
| fps 间隔 | 1/2（每 2 秒一帧） | 操作慢时可改为 1/5 |
| 质量因子 q:v | 2（高质量） | 范围 1-31，越小质量越高 |
| 输出命名 | frame_%04d.jpg | 按序号递增 |

**Step 3：相邻帧差异分析**

使用 Pillow 计算相邻帧差异：

```python
from PIL import Image, ImageChops
import numpy as np

def detect_changes(frame_a_path, frame_b_path, threshold=30):
    img_a = Image.open(frame_a_path).convert('RGB')
    img_b = Image.open(frame_b_path).convert('RGB')
    diff = ImageChops.difference(img_a, img_b)
    diff_array = np.array(diff)
    # 计算差异像素比例
    changed_pixels = np.sum(np.any(diff_array > threshold, axis=2))
    total_pixels = diff_array.shape[0] * diff_array.shape[1]
    change_ratio = changed_pixels / total_pixels
    return change_ratio
```

判定规则：

| 变化比例 | 判定结果 |
|---------|---------|
| < 0.01 | 无变化，跳过 |
| 0.01 - 0.30 | 局部变化，标记为候选步骤 |
| > 0.30 | 重大变化（窗口切换/弹窗），强制标记为关键节点 |

**Step 4：OCR 识别**

对变化区域进行文字识别：

```python
import pytesseract
from PIL import Image

def ocr_region(image_path, bbox=None):
    img = Image.open(image_path)
    if bbox:
        img = img.crop(bbox)
    text = pytesseract.image_to_string(img, lang='chi_sim+eng')
    return text.strip()
```

**Step 5：步骤序列生成**

将识别结果按时间戳排序，合并相邻的微小变化：

```python
steps = []
current_step = None
for frame_info in sorted_frames:
    if frame_info['change_ratio'] > 0.01:
        if current_step and (frame_info['timestamp'] - current_step['end_time'] < 5):
            # 合并到当前步骤
            current_step['end_time'] = frame_info['timestamp']
            current_step['ocr_text'] += ' ' + frame_info['ocr_text']
        else:
            # 开启新步骤
            current_step = {
                'start_time': frame_info['timestamp'],
                'end_time': frame_info['timestamp'],
                'ocr_text': frame_info['ocr_text'],
                'screenshot': frame_info['path']
            }
            steps.append(current_step)
```

**Step 6：输出规范**

生成 Markdown 格式的步骤文档：

```markdown
# 操作演示步骤文档

> 生成时间：2026-08-13 14:30:00
> 视频来源：input.mp4
> 帧提取间隔：2 秒

## 步骤 1（00:00:02 - 00:00:08）

![截图](frames/frame_0002.jpg)

打开系统设置，进入显示选项。

## 步骤 2（00:00:10 - 00:00:16）

![截图](frames/frame_0006.jpg)

调整分辨率至 1920x1080。
```

---

## 四、置信度门控

当处理过程中出现信息不足的情况，必须使用占位符，不得编造内容：

| 场景 | 占位符 | 后续处理 |
|------|-------|---------|
| OCR 识别结果为空 | `[需核实:该帧文字内容]` | 提示用户查看截图确认 |
| 差异分析无法确定变化区域 | `[需核实:变化区域边界]` | 建议用户提供标注截图 |
| 文字记录与截图时间戳不匹配 | `[需核实:步骤对应关系]` | 提示用户手动关联 |
| 视频分辨率过低（< 1280x720） | `[需核实:截图清晰度]` | 建议重新录制或提高分辨率 |
| 步骤间间隔过长（> 30 秒无变化） | `[需核实:是否存在遗漏操作]` | 建议用户确认 |

**处理原则**：宁可输出占位符，不可猜测填充。所有占位符在最终文档中必须被用户确认或替换。

---

## 五、错误码体系

| 错误码 | 错误描述 | 提示话术 | 修正步骤 |
|--------|---------|---------|---------|
| E001 | 环境依赖缺失 | "检测到缺少必要组件，请检查 FFmpeg、Pillow、pytesseract 是否安装" | 按前置条件安装依赖后重试 |
| E002 | 视频文件无法读取 | "无法打开视频文件，请确认路径正确且格式受支持" | 检查文件路径、权限、格式 |
| E003 | OCR 语言包缺失 | "未检测到中文语言包，OCR 识别可能不准确" | 安装 tesseract-ocr-chi-sim 包 |
| E004 | 帧提取失败 | "FFmpeg 帧提取失败，请检查视频编码格式" | 尝试转码为 MP4 (H.264) 后重试 |
| E005 | 差异分析异常 | "相邻帧差异计算失败，可能是图片尺寸不一致" | 检查帧提取输出是否完整 |
| E006 | 输出目录不可写 | "无法写入输出文件，请检查目录权限" | 修改目录权限或更换输出路径 |
| E007 | 文字记录格式不支持 | "仅支持 TXT 和 MD 格式的文字记录文件" | 转换格式后重新输入 |

---

## 六、FAQ 反模式

### 常见坑 1：截图模糊导致 OCR 失败

**反模式**：直接使用低分辨率录屏（如 800x600）进行识别。

**正确做法**：确保录屏分辨率 ≥ 1920x1080。若已录制低分辨率视频，可尝试使用 FFmpeg 的放大滤镜：

```bash
ffmpeg -i input.mp4 -vf "scale=1920:1080" -q:v 2 frames/frame_%04d.jpg
```

### 常见坑 2：操作重叠导致步骤混乱

**反模式**：连续快速操作（如双击 + 输入文字）被识别为单个步骤。

**正确做法**：每次操作后等待界面完全加载（约 1-2 秒）再执行下一步。若已录制，可调整帧提取间隔为 1 秒以捕捉更多细节。

### 常见坑 3：忽略文字记录辅助

**反模式**：只有录屏，没有操作文字记录，导致 OCR 识别结果不完整。

**正确做法**：在录制操作时同步记录文字步骤。本 Skill 会优先使用文字记录作为步骤描述，截图仅作为视觉辅助。

### 常见坑 4：超长视频一次性处理

**反模式**：将 30 分钟以上的录屏直接输入，导致处理时间过长且步骤过多。

**正确做法**：按操作阶段分段处理，每段控制在 10 分钟以内。可使用 FFmpeg 先切割视频：

```bash
ffmpeg -i input.mp4 -ss 00:00:00 -t 00:10:00 -c copy part1.mp4
```

### 常见坑 5：忽略关键节点标注

**反模式**：所有变化帧一视同仁，导致窗口切换、弹窗出现等关键节点被淹没。

**正确做法**：本 Skill 会自动检测变化比例 > 30% 的帧并标记为关键节点。用户可在截图中用红框标注操作位置，提高识别准确率。

---

## 七、渐进式披露

### 速查卡（30 秒上手）

```
输入：视频文件路径 [可选：文字记录文件路径]
输出：Markdown 步骤文档 + 截图文件夹
命令：python skill_19622.py --video input.mp4 [--transcript notes.md]
参数：--interval 2（帧提取间隔，秒）
     --threshold 30（差异判定阈值）
     --lang chi_sim+eng（OCR 语言）
```

### 新手路径（首次使用）

1. 阅读「前置条件」确认环境就绪
2. 准备一段 ≤ 10 分钟的录屏视频
3. 运行 `python skill_19622.py --video your_video.mp4`
4. 查看生成的 `output.md` 文件
5. 遇到 `[需核实:...]` 占位符时，打开对应截图手动确认

### 进阶路径（熟练用户）

1. 同时提供文字记录文件，获得更准确的步骤描述
2. 调整 `--interval` 参数适配不同操作速度
3. 使用 `--threshold` 控制变化检测灵敏度
4. 对关键节点截图进行红框标注，提升 OCR 区域定位精度
5. 分段处理长视频后，手动合并各段输出文档

---

## 八、用户协议

<!-- user-agreement-injected -->

**使用本 Skill 即表示您同意以下条款：**

1. **责任承担**：使用者自行承担因使用本 Skill 产生的全部责任。包括但不限于因输出结果不准确、处理失败、数据丢失等造成的直接或间接损失。

2. **禁止反向工程**：不得对本 Skill 的代码、逻辑、文档进行反向工程、反编译、破解或试图提取源代码。

3. **合法使用**：使用者应确保输入视频内容合法合规，不得使用本 Skill 处理侵犯他人版权、隐私或违反法律法规的内容。

4. **无担保声明**：本 Skill 按"现状"提供，不附带任何明示或暗示的担保，包括但不限于适销性、特定用途适用性和非侵权保证。

5. **输出结果使用**：本 Skill 生成的文档可用于个人学习、内部培训、商业演示等场景，但使用者需自行确认输出内容的准确性和合规性。

---

## 九、许可证（License）

<!-- professional-license-embedded -->

**MIT License**

Copyright (c) 2026 FlowForge Studio

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

*本 Skill 文档由 AI 辅助生成，仅供参考。使用前请阅读相关文档并自行验证功能。*
