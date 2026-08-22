---
slug: obsidian-skills
name: obsidian-skills
displayName: 笔记转换 知识库构建 双向链接整理
description: 将任意数据、文件或URL转换为结构化Obsidian笔记，支持CLI操作与开放格式处理。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 林墨
agent_created: true
trigger_words: ["obsidian", "笔记整理", "知识库", "markdown转换", "obsidian skills", "笔记转换", "双链生成", "知识管理"]
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# obsidian-skills 技能文档

本 Skill 由 AI 辅助生成，仅供参考。使用前请确认输出结果符合您的预期。

---

## 一、能力边界（速查卡）

### 1.1 能做什么

| 能力项 | 说明 | 示例 |
|--------|------|------|
| 文件转 Markdown | 将常见格式（如 .txt、.docx、.html、.csv）转换为 .md 文件 | `input/项目报告.docx` → `output/项目报告.md` |
| URL 转笔记 | 将网页内容抓取并转换为结构化笔记 | 输入 URL 列表，输出对应 .md 文件 |
| 批量处理 | 一次处理整个目录下的所有文件 | `--batch` 模式 |
| 元数据注入 | 自动生成 frontmatter（标题、日期、标签等） | 见 4.3 节 |
| 双向链接生成 | 根据内容关键词自动生成 `[[链接]]` | 见 4.4 节 |

### 1.2 不能做什么

| 限制项 | 说明 |
|--------|------|
| 不处理二进制文件 | 图片、音频、视频等文件不会转换，仅跳过并记录 |
| 不猜测占位符 | 遇到无法确定的信息，输出 `[需核实:字段]` 占位符，不自行编造 |
| 不执行代码 | 输入文件中的代码块仅作为文本保留，不运行 |
| 不处理加密文件 | 需要密码的文件无法读取 |
| 不保证格式完美 | 复杂排版（如多级表格、嵌套列表）可能丢失部分样式 |

### 1.3 适用对象

- 需要将散落文件整理为 Obsidian 知识库的个人用户
- 需要批量将网页内容存档的研究人员
- 需要将旧笔记迁移到 Obsidian 的团队

---

## 二、触发方式

### 2.1 触发词

当您输入以下关键词时，本技能将被激活：

- `obsidian`、`笔记整理`、`知识库`、`markdown转换`、`obsidian skills`
- 补充触发词：`笔记转换`、`双链生成`、`知识管理`

### 2.2 场景映射表

| 您的需求（大白话） | 对应操作 |
|-------------------|----------|
| "帮我把这些文档变成 Obsidian 能用的格式" | 文件转 Markdown |
| "这个网页内容不错，存到我的笔记里" | URL 转笔记 |
| "我有一堆文件要处理，能不能一次搞定" | 批量处理 |
| "转换后帮我加上标签和链接" | 元数据注入 + 双向链接生成 |

---

## 三、标准流程

### 3.1 前置条件

| 条件 | 要求 |
|------|------|
| 输入目录 | 所有待处理文件放入同一目录（如 `./input/`） |
| 文件名规范 | 仅含字母、数字、下划线、连字符、中文；不含空格和特殊符号 |
| URL 列表 | 如需 URL 转换，准备一个文本文件，每行一个 URL |
| 输出目录 | 确保输出目录存在（如 `./output/`），不存在会自动创建 |

### 3.2 执行步骤

#### 步骤 1：准备文件

将待转换文件放入 `./input/` 目录。确认文件名符合规范。

#### 步骤 2：单文件试运行

```bash
obsidian --input ./input/示例文件.txt --output ./output/
```

检查输出文件格式是否符合预期。

#### 步骤 3：确认预览输出

打开生成的 `.md` 文件，检查：
- frontmatter 是否正确
- 正文内容是否完整
- 占位符是否标记清楚

#### 步骤 4：批量处理

确认无误后，执行批量转换：

```bash
obsidian --input ./input/ --output ./output/ --batch
```

#### 步骤 5：校验输出

随机抽查 2-3 个输出文件，确认：
- 文件名与输入一致（扩展名为 `.md`）
- 内容无乱码
- 占位符已正确标记

### 3.3 输出规范

| 项目 | 规范 |
|------|------|
| 输出文件名 | 与输入文件名一致，扩展名改为 `.md` |
| 编码 | UTF-8 |
| 换行 | LF（Unix 风格） |
| frontmatter | 包含 `title`、`date`、`tags` 字段（见 4.3 节） |
| 占位符 | 格式为 `[需核实:字段名]`，不得删除或替换 |

---

## 四、置信度门控

### 4.1 占位符规则

当遇到以下情况时，输出 `[需核实:字段]` 占位符，**不猜测、不编造**：

| 场景 | 占位符示例 |
|------|-----------|
| 无法确定作者 | `[需核实:作者]` |
| 无法确定日期 | `[需核实:日期]` |
| 无法确定标签 | `[需核实:标签]` |
| 内容缺失 | `[需核实:缺失内容]` |

### 4.2 占位符处理流程

1. 转换完成后，输出报告列出所有占位符位置
2. 用户确认后，可手动替换占位符为实际值
3. 未确认前，占位符保留在输出文件中

### 4.3 frontmatter 生成规则

| 字段 | 来源 | 缺失时 |
|------|------|--------|
| `title` | 文件名 | 使用文件名 |
| `date` | 文件修改时间 | `[需核实:日期]` |
| `tags` | 内容关键词 | 空数组 `[]` |
| `source` | 输入文件路径或 URL | `[需核实:来源]` |

### 4.4 双向链接生成规则

- 默认按文件名生成链接：`[[文件名]]`
- 自定义模式：按内容关键词生成链接（需在配置中指定关键词列表）
- 链接生成失败时，输出纯文本，不强制添加链接

---

## 五、错误码体系

| 错误码 | 错误描述 | 提示话术 | 修正步骤 |
|--------|----------|----------|----------|
| E001 | 输入文件不存在 | "未找到输入文件，请检查路径" | 确认文件路径正确，文件确实存在于指定位置 |
| E002 | 文件名不合规 | "文件名包含非法字符（空格或特殊符号）" | 重命名文件，仅保留字母、数字、下划线、连字符、中文 |
| E003 | 文件格式不支持 | "该文件格式暂不支持转换" | 将文件转换为支持的格式（txt、docx、html、csv） |
| E004 | URL 无法访问 | "无法访问该 URL，请检查网络或地址" | 确认 URL 正确，网络连接正常 |
| E005 | 输出目录不可写 | "无法写入输出目录，请检查权限" | 检查目录权限，或更换输出目录 |
| E006 | 占位符过多 | "输出文件中占位符超过 10 个，请检查源文件完整性" | 检查源文件是否完整，补充缺失信息 |
| E007 | 批量处理中断 | "批量处理在第 N 个文件时中断" | 查看错误日志，修复问题后重新执行 |

---

## 六、FAQ 反模式

### 6.1 常见坑

| 坑 | 反模式（错误做法） | 正模式（正确做法） |
|----|-------------------|-------------------|
| 文件名含空格 | 直接使用 `我的 笔记.txt` | 改为 `我的_笔记.txt` 或 `我的笔记.txt` |
| 占位符被替换 | 将 `[需核实:作者]` 替换为猜测的名字 | 保留占位符，确认后手动填写 |
| 批量前不试运行 | 直接执行 `--batch` 处理所有文件 | 先单文件试运行，确认格式后再批量 |
| 忽略错误码 | 遇到 E003 继续处理其他文件 | 先解决格式问题，再继续 |
| 不检查输出 | 转换完成后直接使用，不抽查 | 随机抽查 2-3 个文件确认质量 |

### 6.2 反模式对照表

| 反模式 | 问题 | 替代方案 |
|--------|------|----------|
| 过度依赖自动标签 | 自动生成的标签可能不准确 | 手动补充或修正标签 |
| 强制所有内容加双链 | 无关内容强行链接，造成噪音 | 仅对关键词内容生成链接 |
| 忽略占位符报告 | 占位符未处理，信息缺失 | 按报告逐一确认占位符 |

---

## 七、渐进式披露

### 7.1 速查卡（新手必读）

1. 文件放 `./input/`
2. 单文件试运行：`obsidian --input ./input/文件.txt --output ./output/`
3. 确认输出格式
4. 批量处理：`obsidian --input ./input/ --output ./output/ --batch`
5. 抽查输出文件

### 7.2 分层次阅读路径

| 读者 | 建议阅读内容 |
|------|-------------|
| 新手 | 第三节（标准流程）+ 第六节（FAQ 反模式） |
| 进阶用户 | 第四节（置信度门控）+ 第五节（错误码体系） |
| 高级用户 | 自定义元数据模板、自定义双链规则、批量处理脚本 |

### 7.3 高级用法

| 功能 | 说明 |
|------|------|
| 自定义元数据模板 | 修改 frontmatter 字段映射规则，如增加 `category` 字段 |
| 自定义双链规则 | 按内容关键词而非文件名生成链接 |
| 批量处理脚本 | 将本工具嵌入自动化工作流，如定时任务 |
| 错误处理定制 | 自定义错误提示话术和修正步骤 |
| 与其他工具集成 | 将转换结果接入其他知识管理流程，如 Notion、Roam |

---

## 八、用户协议

<!-- user-agreement-injected -->

**使用本 Skill 即表示您同意以下条款：**

1. **责任承担**：使用者自行承担使用本 Skill 产生的全部责任。因使用本 Skill 导致的任何直接或间接损失，作者不承担任何责任。
2. **禁止反向工程**：未经明确许可，不得对本 Skill 进行反向工程、反编译、破解、提取核心逻辑或用于任何商业竞争目的。
3. **内容合规**：使用者需确保输入内容符合当地法律法规，不得使用本 Skill 处理违法、侵权、违规内容。
4. **数据安全**：使用者需自行做好数据备份。本 Skill 不提供数据恢复功能。
5. **持续改进**：本 Skill 可能不定期更新，使用者需关注版本变化，自行决定是否升级。

---

## 九、许可证（License）

<!-- professional-license-embedded -->

### MIT License

Copyright (c) 2024 林墨

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

*文档版本：1.0.0 | 最后更新：2024年*
