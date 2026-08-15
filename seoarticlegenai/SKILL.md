---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: seoarticlegenai
name: seoarticlegenai
displayName: SEO文章生成 关键词内容创作 搜索优化写作
description: 将数据与URL转化为结构化搜索优化内容，辅助SEO文章批量生成。
version: 1.0.2
rules_version: cpr-20260815-n476
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/seoarticlegenai
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: LinguaForge Studio
agent_created: true
trigger_words: ["SEO文案", "SEO文章生成", "搜索优化写作", "关键词内容创作", "seoarticlegenai", "搜索引擎优化", "内容营销"]
---

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->


> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# SEO文章生成器（seoarticlegenai）操作手册

## 一、能力边界与适用场景（速查卡）

本 Skill 的核心任务：将你提供的结构化数据（如 CSV、JSON、TXT）与目标 URL 结合，批量生成符合搜索引擎优化（SEO）规范的草稿文章。

### 1.1 能做与不能做

| 能力维度 | 支持情况 | 说明 |
| :--- | :--- | :--- |
| 批量生成 | ✅ 支持 | 可对同一目录下的多个数据文件依次处理 |
| 字段映射 | ✅ 支持 | 自动识别常见字段（标题、关键词、描述、URL） |
| 格式输出 | ✅ 支持 | 输出 Markdown 或纯文本，含标题层级与元描述 |
| 关键词密度控制 | ✅ 支持 | 基于输入关键词，在正文中自然分布 |
| 原创性保证 | ⚠️ 有限支持 | 基于模板与数据重组，非深度语义创作 |
| 实时搜索排名 | ❌ 不支持 | 不连接搜索引擎，不提供排名数据 |
| 多语言内容 | ⚠️ 基础支持 | 依赖输入数据语言，不自动翻译 |
| 图片/视频生成 | ❌ 不支持 | 仅处理文本内容 |

### 1.2 适用对象

- **内容运营人员**：需要快速产出大量 SEO 草稿，后续人工润色。
- **独立站长**：维护多个垂直站点，需要批量生成栏目文章。
- **数据驱动写作者**：手头有结构化数据（如产品列表、FAQ 集合），希望转化为文章初稿。

### 1.3 不适用场景

- 需要深度行业洞察或专家意见的权威文章。
- 需要实时数据（如股价、天气）的时效性内容。
- 完全脱离人工审核的自动化发布流程。

---

## 二、触发方式与场景映射

### 2.1 触发词

当你的指令中包含以下任一词汇或短语时，本 Skill 将被激活：

`SEO文案`、`SEO文章生成`、`搜索优化写作`、`关键词内容创作`、`seoarticlegenai`、`搜索引擎优化`、`内容营销`

### 2.2 场景映射表（大白话对照）

| 你说的话（场景） | Skill 实际执行的动作 |
| :--- | :--- |
| “帮我把这个产品列表做成 SEO 文章” | 读取产品数据文件，为每个产品生成一篇包含标题、描述、关键词的草稿。 |
| “给这批博客标题写点搜索优化内容” | 将标题列表作为输入，为每个标题生成正文框架与元描述。 |
| “这个 URL 对应的文章能优化下吗” | 提取 URL 中的路径与参数作为关键词线索，生成优化后的内容草稿。 |
| “批量跑一下这个文件夹里的数据” | 遍历指定目录，对每个符合命名规范的文件执行生成流程。 |

---

## 三、标准执行流程

### 3.1 前置条件

1. **文件准备**：将所有待处理的数据文件（`.csv`、`.json`、`.txt`）放入同一工作目录。
2. **命名规范**：确保文件名具有辨识度，例如 `products_20260815.csv`、`blog_titles.txt`。避免使用 `新建文档(2).txt` 这类无意义名称。
3. **字段确认**：检查数据文件是否包含以下至少一个关键字段：`title`（标题）、`keywords`（关键词）、`description`（描述）、`url`（链接）。若无，请先进行数据清洗。

### 3.2 执行步骤（分步编号）

**第一步：试运行（单样本验证）**

1. 指定一个样本文件，例如 `sample.csv`。
2. 运行命令：`seoarticlegenai --input sample.csv --output sample_output.md`
3. 检查输出文件中的以下字段：
   - `# 标题`（H1）
   - `## 元描述`（Meta Description）
   - `## 关键词`（Primary Keyword）
   - `### 正文段落`（H3 及以下）
4. 核对输出内容是否与源数据一致，无乱码或字段错位。

**第二步：批量执行**

1. 确认试运行无误后，对全量文件执行。
2. 运行命令：`seoarticlegenai --input ./data_folder/ --output ./output_folder/`
3. **重要**：在执行前，将原始数据目录复制一份备份，命名为 `data_backup_YYYYMMDD`。

**第三步：结果校验**

1. 随机抽取 3-5 个输出文件。
2. 核对以下关键点：
   - 标题是否包含核心关键词。
   - 元描述是否在 150-160 字符内。
   - 正文是否自然分布了 2-3 次关键词变体。
   - 数据中的 URL 是否被正确嵌入为链接或引用。

### 3.3 输出规范

- **文件格式**：`.md`（Markdown）或 `.txt`（纯文本），默认 `.md`。
- **编码**：UTF-8。
- **内容结构**：
  ```markdown
  # [标题]
  > 元描述：[150-160字符]
  ## 关键词
  [关键词1]、[关键词2]、[关键词3]
  ## 正文
  ### 引言
  [内容]
  ### 主体段落
  [内容]
  ### 结语
  [内容]
  ```

---

## 四、置信度门控与信息占位

当输入数据缺失关键信息时，本 Skill 不会编造内容，而是输出占位符，提示人工介入。

| 缺失字段 | 输出占位符 | 人工处理建议 |
| :--- | :--- | :--- |
| 标题 | `[需核实:标题]` | 根据正文内容手动补充标题 |
| 关键词 | `[需核实:关键词]` | 从正文中提取高频词作为关键词 |
| URL | `[需核实:URL]` | 补充目标链接或移除引用 |
| 描述 | `[需核实:描述]` | 根据正文首段提炼描述 |

**示例**：
若输入数据缺少 `keywords` 字段，输出文件中的关键词部分将显示：
```markdown
## 关键词
[需核实:关键词]
```

---

## 五、错误码体系

| 错误码 | 常见原因 | 提示话术 | 修正步骤 |
| :--- | :--- | :--- | :--- |
| `E001` | 输入文件不存在 | “未找到指定文件，请检查路径。” | 1. 确认文件路径正确；2. 检查文件名大小写。 |
| `E002` | 数据格式不支持 | “仅支持 CSV、JSON、TXT 格式。” | 1. 转换文件格式；2. 重新运行。 |
| `E003` | 缺少关键字段 | “数据中未找到 title 或 keywords 字段。” | 1. 检查数据表头；2. 添加缺失字段。 |
| `E004` | 输出目录无写入权限 | “无法写入输出目录，请检查权限。” | 1. 更换输出目录；2. 修改目录权限。 |
| `E005` | 批量执行中断 | “批量处理在第 N 个文件时中断。” | 1. 查看日志定位问题文件；2. 修复后从断点继续。 |

---

## 六、FAQ 与反模式对照

### 6.1 常见坑

| 坑（反模式） | 正确做法 |
| :--- | :--- |
| **直接批量跑全量数据，不做试运行** | 务必先用单个样本验证输出格式与字段映射。 |
| **忽略原始文件备份** | 批量执行前，必须复制一份原始数据作为备份。 |
| **完全信任输出内容，不进行人工审核** | 将输出视为草稿，需人工检查事实、语气与逻辑。 |
| **在数据文件中混入无关字段** | 清理数据，只保留生成文章所需的字段。 |
| **使用无意义文件名** | 使用包含日期与内容类型的命名，如 `faq_20260815.csv`。 |

### 6.2 反模式对照表

| 反模式 | 问题 | 修正 |
| :--- | :--- | :--- |
| “帮我生成一篇关于XX的完美文章” | 期望过高，AI 生成内容需人工润色。 | 明确需求为“草稿”，后续人工优化。 |
| “把这份数据直接发布到网站” | 跳过审核，存在事实错误风险。 | 先人工审核，再走发布流程。 |
| “所有文章都用同一个模板” | 内容同质化，SEO 效果差。 | 根据数据特征调整模板结构。 |

---

## 七、渐进式披露：分层次阅读路径

### 7.1 速查卡（新手必读）

1. 把数据文件放一个文件夹。
2. 先跑一个文件试试。
3. 检查输出格式对不对。
4. 备份原始数据。
5. 批量跑所有文件。
6. 抽查几个结果，人工修改。

### 7.2 进阶路径（熟练用户）

- **自定义模板**：修改 Skill 配置中的模板文件，调整标题层级、段落长度。
- **关键词密度控制**：在配置中设置关键词密度阈值（如 0.5% - 2.5%）。
- **批量校验脚本**：编写简单的 Python 脚本，自动检查输出文件中的占位符数量。

---

## 八、用户协议

<!-- user-agreement-injected -->

**使用本 Skill 即表示您同意以下条款：**

1. **责任承担**：使用者应自行承担因使用本 Skill 产生的全部责任。包括但不限于因内容错误、遗漏或不合规导致的任何损失。
2. **禁止反向工程**：不得对本 Skill 的底层代码、算法或逻辑进行反向工程、反编译或试图提取源代码。
3. **内容合规**：使用者需确保输入数据与输出内容符合当地法律法规及平台政策。
4. **无担保声明**：本 Skill 按“现状”提供，不附带任何明示或暗示的担保。

---

## 九、许可证（License）

<!-- professional-license-embedded -->

本 Skill 采用 MIT 许可证发布。

```
MIT License

Copyright (c) 2026 LinguaForge Studio

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

---

**版本记录**：v1.0.0（2026-08-15）初始版本。
