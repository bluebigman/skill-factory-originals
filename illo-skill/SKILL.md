---
slug: illo-skill
name: illo-skill
displayName: 编辑插画 创意视觉化 方案设计
description: 将文章创意转化为原创编辑插画方案，输出可交付的视觉文档。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 视觉工坊·林默
agent_created: true
trigger_words: ["illo-skill", "编辑插画", "文章配图", "创意视觉化", "插画方案", "配图设计", "视觉提案"]

---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# 编辑插画方案设计 Skill（illo-skill）

## 一、能力边界：一页纸速查卡

本 Skill 用于将文章的核心创意转化为可交付的编辑插画方案文档。它输出的是**视觉方案**，不是最终成图。

| 能做 ✅ | 不能做 ❌ |
|---------|-----------|
| 解析文章主题、情绪、关键意象 | 直接生成位图/矢量图文件 |
| 输出插画构图、配色、风格建议 | 替代设计师的审美判断 |
| 提供分镜/分层描述（用于对接画师） | 保证任何平台的审核通过率 |
| 生成交付文档（Markdown 格式） | 自动完成版权登记或授权 |
| 批量处理同目录下的多篇文本 | 理解图片内容（仅限文本输入） |

**适用对象**：编辑、内容运营、独立撰稿人、需要为文章配图但缺乏视觉方案经验的创作者。

**不适用对象**：需要成品图片的紧急任务、对视觉风格有极强主观偏好且不愿调整的团队。

---

## 二、触发方式：场景映射表

当你的需求匹配以下任一场景时，可使用本 Skill：

| 大白话场景 | 触发词示例 | 说明 |
|------------|-----------|------|
| "这篇文章配什么图好？" | 文章配图、编辑插画 | 输出完整方案 |
| "帮我把这个创意画出来" | 创意视觉化、插画方案 | 输出构图与风格建议 |
| "给这段文字配个封面" | 配图设计、视觉提案 | 输出封面构图方案 |
| "批量给专栏文章做配图规划" | 批量配图、系列插画 | 输出多篇方案文档 |

**命令行调用方式**（如适用）：
```bash
illo-skill "输入文件路径" [--output 输出路径] [--selftest] [--version]
```

---

## 三、标准流程：从输入到交付

### 3.1 前置条件

| 条件 | 要求 | 检查方法 |
|------|------|---------|
| 输入文件 | 纯文本或 Markdown 格式 | 文件扩展名为 .txt / .md |
| 文件位置 | 与 Skill 运行目录一致 | 使用 `ls` 确认 |
| 命名规范 | 文件名不含空格与特殊字符 | 建议使用 `article_001.md` 格式 |
| 内容长度 | 单篇不少于 200 字 | 少于 200 字时输出 [需核实:内容完整性] |

### 3.2 执行步骤

**第一步：主题提取（输入解析）**

读取全文，提取以下要素：
- 核心主题（1-2 个关键词）
- 情绪基调（如：严肃、幽默、温暖、悬疑）
- 关键意象（文中反复出现的物品、场景、隐喻）

**第二步：方案生成（核心逻辑）**

基于提取要素，生成以下内容：

| 输出字段 | 说明 | 示例 |
|---------|------|------|
| 构图描述 | 画面主体、位置关系、视角 | "俯视视角，主体为一张摊开的地图，边缘有折痕" |
| 配色建议 | 主色、辅色、点缀色（HEX 值） | 主色 #2C3E50，辅色 #E67E22 |
| 风格定位 | 写实/扁平/手绘/拼贴等 | 扁平插画，带轻微噪点质感 |
| 分层说明 | 前景/中景/背景的元素拆分 | 前景：人物剪影；中景：城市轮廓；背景：渐变天空 |
| 文字标注 | 画面中可出现的文字元素 | 标题短句、数据标签 |

**第三步：输出规范**

输出文档结构固定为：

```markdown
# 插画方案：[文章标题]

## 方案概览
- 主题关键词：
- 情绪基调：
- 推荐风格：

## 构图描述
（200字以内的画面描述）

## 配色方案
| 角色 | 色值 | 使用场景 |
|------|------|---------|
| 主色 | #XXXXXX | 背景/大面积 |
| 辅色 | #XXXXXX | 次要元素 |
| 点缀 | #XXXXXX | 强调细节 |

## 分层说明
- 前景：
- 中景：
- 背景：

## 交付备注
- 建议尺寸：
- 输出格式：
- 对接画师时的注意事项：
```

### 3.3 批量执行

1. 将多篇文章放入同一目录，确认命名规范一致（如 `article_001.md`、`article_002.md`）。
2. 先对单篇执行试运行，核对输出字段与格式是否符合预期。
3. 确认无误后，对全量文件执行批量处理。
4. 处理前自动备份原始文件至 `./backup/` 目录。

---

## 四、置信度门控：不编造原则

当输入信息不足以支撑方案生成时，使用以下占位符，**不得自行编造**：

| 场景 | 输出占位符 |
|------|-----------|
| 文章主题模糊，无法确定核心意象 | `[需核实:主题意象]` |
| 情绪基调不明确 | `[需核实:情绪基调]` |
| 文章长度不足 200 字 | `[需核实:内容完整性]` |
| 用户未指定输出格式 | `[需核实:输出格式]` |

**示例**：
> 构图描述：画面主体为 `[需核实:主题意象]`，背景采用 `[需核实:情绪基调]` 对应的色调。

---

## 五、错误码体系

| 错误码 | 错误描述 | 提示话术 | 修正步骤 |
|--------|---------|---------|---------|
| E001 | 输入文件不存在 | "未找到指定文件，请检查路径与文件名" | 确认文件路径，重新输入 |
| E002 | 文件格式不支持 | "仅支持 .txt 与 .md 格式" | 转换格式后重试 |
| E003 | 内容过短 | "文章内容不足 200 字，无法提取有效主题" | 补充内容或更换文件 |
| E004 | 输出目录无写入权限 | "无法写入输出文件，请检查目录权限" | 更换输出目录或调整权限 |
| E005 | 批量处理中断 | "批量处理在第 N 个文件处中断" | 查看日志，修复后从断点继续 |

---

## 六、FAQ 反模式对照

| 常见坑 | 反模式（错误做法） | 正模式（正确做法） |
|--------|------------------|------------------|
| 过度依赖 AI 判断 | 直接采用 AI 给出的全部配色，不做调整 | 将 AI 方案作为起点，结合品牌手册或个人审美微调 |
| 忽略上下文 | 只输入标题就要求生成方案 | 提供全文或至少 500 字的核心段落 |
| 混淆方案与成品 | 期望输出 PNG/JPG 图片 | 明确本 Skill 输出的是 Markdown 方案文档 |
| 批量处理不校验 | 直接对 100 篇文件跑批，不抽查结果 | 先跑 1 篇，核对无误后再全量执行 |
| 覆盖原始文件 | 输出文件直接覆盖输入文件 | 输出至独立目录，保留原始文件备份 |

---

## 七、渐进式披露：分层次阅读路径

### 速查卡（30 秒上手）

1. 把文章存为 `.md` 文件，放在当前目录。
2. 运行 `illo-skill 文件名.md`。
3. 打开生成的 `文件名_方案.md`，查看构图、配色、分层。
4. 把方案交给画师或自己动手绘制。

### 新手路径（首次使用）

- 阅读「能力边界」明确预期。
- 按「标准流程」的步骤执行一次单篇处理。
- 遇到占位符时，补充信息后重新运行。

### 进阶路径（熟练用户）

- 使用批量模式处理系列文章，保持风格统一。
- 自定义输出模板（修改配置中的模板字段）。
- 将多篇方案整合为系列视觉规划文档。

---

## 八、用户协议

使用本 Skill 即表示您同意以下条款：

1. **责任承担**：使用者自行承担因使用本 Skill 产生的全部责任，包括但不限于内容合规性、版权归属、商业决策等。
2. **禁止反向工程**：不得对本 Skill 的提示词结构、生成逻辑进行反向工程、破解或二次封装用于商业竞争。
3. **内容合规**：使用者需确保输入内容不违反法律法规及平台规定，本 Skill 不对输入内容的合法性负责。
4. **无担保声明**：本 Skill 按"现状"提供，不附带任何明示或暗示的担保。

<!-- user-agreement-injected -->

---

## 九、许可证（License）

本 Skill 采用 MIT 许可证发布：

```
MIT License

Copyright (c) 2024 视觉工坊·林默

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

---

*本 Skill 由 AI 辅助生成，仅供参考。使用前请阅读相关文档。*
