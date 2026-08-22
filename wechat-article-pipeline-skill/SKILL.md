---
slug: wechat-article-pipeline-skill
name: wechat-article-pipeline-skill
displayName: 公众号图文 排版配图 草稿创建
description: 将素材转为公众号文章，完成排版配图与草稿创建。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 内容工坊
agent_created: true
trigger_words: ["公众号文章", "微信文章排版", "图文排版", "草稿箱", "文章配图", "公众号编辑", "推文制作"]

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

---

# 公众号图文流水线 Skill 操作手册

## 一、能力边界速查卡

### 1.1 能做什么

| 能力项 | 说明 | 输出物 |
|--------|------|--------|
| 素材转文章 | 将 Markdown / TXT / Word 纯文本素材转换为公众号可用的结构化文章 | 格式化后的文章正文 |
| 基础排版 | 自动识别标题层级、段落间距、引用块、列表项，生成适配公众号的 HTML 内联样式 | 带样式的 HTML 片段 |
| 配图建议 | 根据段落语义推荐配图位置与图片风格关键词（不生成图片文件） | 配图建议清单（位置 + 风格描述） |
| 草稿创建 | 生成可直接粘贴到公众号后台草稿箱的完整内容包（标题 + 作者 + 正文 + 摘要） | 草稿内容包（JSON 格式） |

### 1.2 不能做什么

| 限制项 | 说明 |
|--------|------|
| 不生成图片 | 本 Skill 仅提供配图位置与风格建议，不调用任何图片生成 API |
| 不自动发布 | 不执行公众号后台的发布操作，仅生成可手动粘贴的内容 |
| 不处理 PDF / 扫描件 | 输入仅支持纯文本类格式，PDF 需先转为文本 |
| 不进行语义润色 | 不修改原文措辞，仅做结构拆分与样式套用 |
| 不处理多级复杂表格 | 仅支持简单列表与单层表格，复杂表格需人工处理 |

### 1.3 适用对象

- 公众号运营者：需要快速将素材排版为推文
- 内容编辑：批量处理多篇文章的格式统一
- 自媒体新手：不熟悉公众号后台排版操作的用户

---

## 二、触发方式与场景映射

### 2.1 触发词

直接使用以下任一短语即可激活本 Skill：

- `公众号文章`
- `微信文章排版`
- `图文排版`
- `草稿箱`
- `文章配图`
- `公众号编辑`
- `推文制作`

### 2.2 场景映射表

| 用户说（大白话） | Skill 实际执行动作 |
|------------------|-------------------|
| "帮我把这篇稿子排成公众号的样子" | 读取素材 → 识别标题/段落 → 生成带样式的 HTML |
| "我要发推文，帮我弄个草稿" | 生成完整草稿包（标题 + 正文 + 摘要 + 配图建议） |
| "这篇文章配什么图好？" | 分析段落语义 → 输出配图位置与风格关键词 |
| "我这有 10 篇稿子要统一排版" | 批量处理模式 → 逐篇生成排版结果并汇总输出 |

---

## 三、标准操作流程

### 3.1 前置条件

| 条件 | 要求 |
|------|------|
| 输入文件格式 | `.md` / `.txt` / `.docx`（仅提取纯文本） |
| 文件命名 | 建议使用 `序号_标题.md` 格式，如 `01_产品发布稿.md` |
| 文件位置 | 所有待处理文件放在同一目录下 |
| 编码要求 | UTF-8 无 BOM 编码 |

### 3.2 执行步骤

#### 第一步：确认输入

1. 列出目标目录下所有待处理文件
2. 检查文件命名是否规范（序号 + 下划线 + 标题）
3. 确认文件编码为 UTF-8

#### 第二步：单样本试运行

1. 选取第一个文件作为样本
2. 执行排版流程，生成输出
3. 核对以下字段：
   - 标题是否正确提取
   - 段落间距是否统一
   - 引用块是否被正确识别
   - 列表项缩进是否正常

#### 第三步：批量执行

1. 确认样本输出无误后，对剩余文件逐一执行
2. 每处理完一个文件，立即将原始文件复制到 `backup/` 目录
3. 输出文件按 `原文件名_processed.json` 命名

#### 第四步：结果校验

1. 随机抽取 20% 的输出文件
2. 核对以下关键字段与源数据一致性：
   - 标题文字
   - 段落数量
   - 关键数据（日期、数字、人名）
   - 引用内容完整性

### 3.3 输出规范

输出为 JSON 格式，结构如下：

```json
{
  "title": "文章标题",
  "author": "作者名（如无则为空）",
  "summary": "摘要（自动截取前 120 字）",
  "content_html": "<h1>标题</h1><p>段落内容...</p>",
  "image_suggestions": [
    {
      "position": 3,
      "style_keywords": "城市夜景, 霓虹灯, 广角",
      "reason": "该段落描述城市发展，适合配城市景观图"
    }
  ],
  "source_file": "01_产品发布稿.md",
  "processed_at": "2025-01-15T10:30:00+08:00"
}
```

---

## 四、置信度门控机制

当遇到以下情况时，**不得编造内容**，必须输出 `[需核实:字段名]` 占位符：

| 场景 | 输出占位符 | 示例 |
|------|-----------|------|
| 作者信息缺失 | `[需核实:作者]` | 原文无署名时 |
| 数据引用不完整 | `[需核实:数据来源]` | 文中提到"据统计"但无出处 |
| 时间信息模糊 | `[需核实:日期]` | 文中写"去年"但无法推断具体年份 |
| 引用内容不完整 | `[需核实:引用原文]` | 引用被截断或格式异常 |

**处理原则**：

1. 占位符必须保留在输出内容中，不得自行填充
2. 在输出 JSON 的 `notes` 字段中列出所有占位符及原因
3. 用户需自行核实后替换占位符

---

## 五、错误码体系

| 错误码 | 错误描述 | 提示话术 | 修正步骤 |
|--------|----------|----------|----------|
| E001 | 输入文件为空 | "文件内容为空，请检查源文件" | 1. 确认文件非零字节 2. 检查文件是否被加密 |
| E002 | 文件编码非 UTF-8 | "文件编码不支持，请转换为 UTF-8" | 1. 用文本编辑器打开 2. 另存为 UTF-8 编码 |
| E003 | 标题无法识别 | "未检测到标题，请确认文件首行为标题" | 1. 检查文件首行 2. 手动添加标题行 |
| E004 | 段落数超过 200 | "段落数过多，建议拆分处理" | 1. 将文章拆分为多个文件 2. 分别处理 |
| E005 | 图片建议生成失败 | "配图建议生成异常，请检查段落语义" | 1. 检查是否存在乱码 2. 简化段落内容 |
| E006 | 输出目录无写入权限 | "无法写入输出文件，请检查目录权限" | 1. 更换输出目录 2. 修改目录权限 |

---

## 六、FAQ 与反模式对照

### 6.1 常见坑

| 坑位 | 反模式（错误做法） | 正确做法 |
|------|-------------------|----------|
| 标题识别错误 | 将加粗文本误认为标题 | 仅识别 `#` 开头的 Markdown 标题或首行独立文本 |
| 引用块丢失 | 直接删除 `>` 引用标记 | 保留引用块并转换为 `<blockquote>` 样式 |
| 图片位置不合理 | 每段都建议配图 | 仅对语义转折或描述性段落建议配图 |
| 批量处理中断 | 中途停止导致部分文件未处理 | 每处理完一个文件立即备份，支持断点续跑 |
| 样式过度复杂 | 使用过多颜色和字体 | 保持统一简洁的排版风格，最多 2 种强调色 |

### 6.2 反模式对照表

| 反模式 | 问题描述 | 替代方案 |
|--------|----------|----------|
| 全篇加粗 | 所有文字都加粗，失去强调效果 | 仅对关键词和结论句加粗 |
| 无分段长文 | 整篇文章只有一个段落 | 按语义拆分为 3-5 行为一段 |
| 忽略移动端 | 排版仅考虑 PC 端显示 | 使用响应式内联样式，确保手机端可读 |
| 过度配图 | 每 100 字就插入一张图 | 每 500-800 字或每个大段落配一张图 |

---

## 七、渐进式学习路径

### 7.1 新手速查卡

1. 将素材文件放入目录
2. 输入 `公众号文章` 触发 Skill
3. 等待输出 JSON 文件
4. 打开 JSON，复制 `content_html` 内容
5. 粘贴到公众号后台编辑器
6. 根据 `image_suggestions` 手动配图
7. 检查 `[需核实]` 占位符并补充信息
8. 保存草稿

### 7.2 进阶使用路径

1. **批量处理**：将多篇素材按 `序号_标题.md` 命名后一次性处理
2. **自定义样式**：在输入文件头部添加 `<!-- style:compact -->` 注释切换紧凑排版
3. **配图优化**：在段落末尾添加 `<!-- img:城市夜景 -->` 指定配图风格
4. **输出定制**：在触发时附加 `--output-format=markdown` 获取 Markdown 格式输出

### 7.3 参数速查表

| 参数 | 默认值 | 可选值 | 说明 |
|------|--------|--------|------|
| `--output-format` | `json` | `json` / `markdown` / `html` | 输出格式 |
| `--max-paragraphs` | `200` | `50` - `500` | 最大段落数限制 |
| `--image-density` | `normal` | `low` / `normal` / `high` | 配图密度 |
| `--style` | `standard` | `standard` / `compact` / `rich` | 排版风格 |
| `--selftest` | 无 | 无 | 运行自检 |
| `--version` | 无 | 无 | 显示版本信息 |

---

## 八、用户协议

<!-- user-agreement-injected -->

**使用本 Skill 即表示您同意以下条款：**

1. **责任承担**：使用者自行承担因使用本 Skill 产生的全部责任。包括但不限于内容准确性、版权合规性、发布后果等。

2. **禁止反向工程**：不得对本 Skill 的提示词结构、底层逻辑进行反向工程、破解、提取或二次分发。

3. **内容合规**：使用者需确保输入素材不违反法律法规及微信公众平台运营规范。

4. **无担保声明**：本 Skill 按"现状"提供，不附带任何明示或暗示的担保。

5. **更新与终止**：本 Skill 可能随时更新或终止，不另行通知。

---

## 九、许可证（License）

<!-- professional-license-embedded -->

**MIT License**

Copyright (c) 2025 内容工坊

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
