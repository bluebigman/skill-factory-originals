---
slug: skill-59071
name: phone-tutorial-builder
displayName: 手机教程 截图编排 操作指引
description: 将手机截图与文字素材整理为结构化 Markdown 教程，支持识别与校验。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: LingCraft
agent_created: true
trigger_words: ["手机教程", "截图编排", "操作指引", "教程生成", "步骤整理"]
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# 手机教程构建器（Phone Tutorial Builder）

## 一、能力边界：一页纸速查卡

本 Skill 面向需要将手机操作截图与文字说明整理为 Markdown 教程文档的个人或团队。以下清单帮助你在 30 秒内判断是否适用。

| 维度 | 能做 | 不能做 |
|------|------|--------|
| 输入素材 | 手机截图（PNG/JPG）、文字描述、操作目标说明 | 视频文件、音频文件、非手机类截图 |
| 处理能力 | 按文件名排序、OCR 提取界面文字、生成步骤标题与说明 | 自动理解截图中的复杂业务逻辑、跨应用流程推断 |
| 输出格式 | 结构化 Markdown 教程（含标题、步骤、图片引用、注意事项） | 生成 PDF、HTML 或可直接发布的公众号排版 |
| 质量保障 | 置信度标注、`[需核实]` 占位符、dry-run 预览 | 保证 OCR 100% 准确、保证教程无需人工复核 |
| 适用对象 | 新手用户、技术写作人员、客服知识库维护者 | 需要深度交互式教程或视频教程的用户 |

**适用场景示例**：给父母写手机设置指南、为新员工制作内部 App 操作手册、为产品功能更新撰写图文说明。

---

## 二、触发方式：场景映射表

当你的需求符合以下任一描述时，即可使用本 Skill：

| 大白话描述 | 触发词匹配 | 说明 |
|------------|------------|------|
| "帮我把这几张手机截图做成一个教程" | 手机教程 | 最直接的触发方式 |
| "整理一下我拍的操作步骤，配上文字" | 截图编排 | 适用于已有截图但未排序的情况 |
| "写个说明书，教人怎么设置双卡" | 操作指引 | 有明确操作目标，需要生成步骤 |
| "把这些图片按顺序变成文档" | 教程生成 | 通用场景，不限定手机 |
| "做个图文步骤给我同事看" | 步骤整理 | 内部协作场景 |

> 提示：触发时请附带素材文件路径或直接粘贴文字素材，可显著提升处理效率。

---

## 三、标准流程：从素材到成品

### 3.1 前置条件

| 条件项 | 要求 | 缺失后果 |
|--------|------|----------|
| 截图文件 | 按操作顺序命名（如 `01.png`、`02.png`），格式为 PNG/JPG | 顺序混乱，教程逻辑不清（错误码 E003） |
| 文字素材 | 提供操作目标描述（如"设置双卡双待"） | 教程缺乏上下文，步骤说明模糊 |
| 截图质量 | 界面文字清晰，无严重反光/模糊 | OCR 准确率下降，产生大量 `[需核实]` 占位 |
| 输出目录 | 确认目标路径可写，无同名文件冲突 | 覆盖已有文件（需用 `--dry-run` 规避） |

### 3.2 执行步骤

1. **素材收集与命名**  
   将所有截图按操作先后顺序重命名：`01.png`、`02.png`、`03.png`…  
   若截图数量超过 20 张，建议拆分为多个子教程，避免单文档过长。

2. **文字素材整理**  
   准备一段操作目标描述（1-2 句话即可），例如：  
   > 目标：在小米手机上设置双卡双待，确保 SIM1 用于上网，SIM2 用于通话。

3. **运行生成命令**  
   在终端执行（示例）：
   ```bash
   phone-tutorial-builder --input ./screenshots/ --output ./tutorial.md --text "设置双卡双待"
   ```

4. **预览检查（推荐）**  
   生成前先执行 dry-run 模式：
   ```bash
   phone-tutorial-builder --dry-run --input ./screenshots/ --output ./tutorial.md
   ```
   该模式会列出将生成的步骤大纲与文件清单，不实际写入文件。

5. **生成并复核**  
   正式生成后，打开 Markdown 文件检查：
   - 步骤顺序是否与截图命名一致
   - 每步的 OCR 文字是否与截图内容匹配
   - `[需核实]` 占位符数量是否在可接受范围（建议不超过总步骤数的 20%）

6. **修正与迭代**  
   若发现步骤缺失或文字识别错误，补充截图或调整文字素材后重新生成。

### 3.3 输出规范

生成的 Markdown 文档结构如下：

```markdown
# 教程标题（取自文字素材或文件名）

> 操作目标：{用户提供的目标描述}

## 准备工作
- 设备型号：{从截图 EXIF 或用户输入获取}
- 系统版本：{如可识别则填写}

## 步骤 1：{自动生成的步骤标题}
![步骤 1 截图](images/01.png)
{OCR 提取的界面文字或操作说明}

## 步骤 2：{自动生成的步骤标题}
![步骤 2 截图](images/02.png)
{OCR 提取的界面文字或操作说明}

...

## 注意事项
- {根据 OCR 内容自动提取的提示信息}
- {若存在 [需核实] 项，在此汇总}
```

---

## 四、置信度门控：不编造，只标注

当信息不足或识别不确定时，本 Skill 遵循以下原则：

| 情况 | 处理方式 | 示例 |
|------|----------|------|
| OCR 文字置信度 < 70% | 输出 `[需核实:字段名]` 占位符 | `[需核实:按钮名称]` |
| 截图顺序无法确定 | 按文件名排序，并在文档开头注明"顺序基于文件名" | 文件名非数字时提示 E003 |
| 缺少操作目标描述 | 在文档开头输出 `[需核实:操作目标]`，不自行推断 | 用户未提供文字素材时 |
| 截图数量为 0 | 拒绝生成，返回错误码 E001 | 提示"未检测到截图文件" |

**占位符处理建议**：生成后，用户应搜索 `[需核实` 并逐项补充真实信息。若占位符超过总步骤数的 20%，建议补充素材后重新生成。

---

## 五、错误码体系：常见问题与修正

| 错误码 | 错误描述 | 提示话术 | 修正步骤 |
|--------|----------|----------|----------|
| E001 | 未找到截图文件 | "输入目录中未检测到 PNG/JPG 文件，请检查路径。" | 确认截图文件存在且格式正确 |
| E002 | 截图质量过低 | "检测到截图模糊或反光严重，OCR 准确率可能受影响。" | 重新截取清晰截图，避免强光环境 |
| E003 | 文件命名不规范 | "截图文件名未按数字顺序命名，步骤顺序可能混乱。" | 重命名为 `01.png`、`02.png` 等格式 |
| E004 | 输出文件已存在 | "目标文件已存在，使用 --dry-run 预览或指定新文件名。" | 更换输出路径或删除旧文件 |
| E005 | 文字素材缺失 | "未提供操作目标描述，教程将缺少上下文说明。" | 补充 1-2 句操作目标描述 |

---

## 六、FAQ 反模式：常见坑与对照

| 反模式（错误做法） | 问题 | 正确做法 |
|--------------------|------|----------|
| 截图随意命名（如 `IMG_001.jpg`） | 无法确定操作顺序，教程逻辑混乱 | 按 `01.png`、`02.png` 顺序命名 |
| 不提供文字素材直接生成 | 教程缺少目标说明，读者不知为何操作 | 至少提供一句操作目标描述 |
| 在光线不足环境截图 | OCR 识别率下降，产生大量占位符 | 确保界面文字清晰可读 |
| 直接覆盖已有教程文件 | 丢失旧版本内容 | 使用 `--dry-run` 预览后再生成 |
| 忽略 `[需核实]` 占位符直接发布 | 教程包含错误信息，误导读者 | 逐项核实并替换占位符 |

---

## 七、渐进式披露：按需阅读

### 速查卡（新手必读）

1. 截图按 `01.png` 顺序命名
2. 提供一句操作目标描述
3. 先 `--dry-run` 预览
4. 生成后搜索 `[需核实` 并补充
5. 占位符过多则补充素材重来

### 进阶路径（有经验用户）

- 阅读「标准流程」完整章节，掌握参数与边界值
- 熟悉「错误码体系」以快速定位问题
- 结合「置信度门控」理解输出质量评估方法
- 参考「FAQ 反模式」优化输入素材质量

---

## 八、用户协议

<!-- user-agreement-injected -->

**使用本 Skill 即表示您同意以下条款：**

1. **责任承担**：使用者自行承担因使用本 Skill 产生的全部责任，包括但不限于教程内容的准确性、合规性及传播后果。本 Skill 提供的输出仅为辅助参考，不构成专业建议。
2. **禁止反向工程**：不得对本 Skill 的底层逻辑、算法或提示词结构进行反向工程、反编译或试图提取源代码。
3. **内容合规**：使用者应确保输入素材（截图、文字）不侵犯第三方权益，不包含违法或敏感信息。
4. **无担保声明**：本 Skill 按"现状"提供，不附带任何明示或暗示的担保，包括但不限于适销性、特定用途适用性。

---

## 九、许可证（License）

<!-- professional-license-embedded -->

**MIT License**

Copyright (c) 2025 LingCraft

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
