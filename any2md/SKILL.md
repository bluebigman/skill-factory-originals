---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: any2md
name: any2md
displayName: 文档转Markdown 结构化整理 内容转换
description: 将任意输入内容转换为结构化Markdown，保留关键信息并标注置信度。
version: 2.0.1
rules_version: cpr-20260810-n301
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/any2md
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: LinguaForge
agent_created: true
trigger_words: ["any2md", "转markdown", "转md", "结构化转换", "文档转换", "内容整理"]
---

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->


> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# any2md — 任意内容转 Markdown 技能手册

## 一、能力边界（一页纸速查卡）

### 1.1 能做什么

| 序号 | 能力项 | 说明 | 输入示例 |
|------|--------|------|----------|
| 1 | 文本转 Markdown | 将纯文本、富文本内容转换为带标题层级、列表、表格的 Markdown | 一段会议纪要文本 |
| 2 | PDF 转 Markdown | 提取 PDF 中的文字内容，保留段落结构和基础排版 | 产品说明书 PDF |
| 3 | 网页转 Markdown | 抓取网页正文，去除导航、广告等噪音信息 | 新闻文章 URL |
| 4 | 对话记录转 Markdown | 将聊天记录、访谈内容整理为对话式 Markdown | 客服聊天记录导出 |
| 5 | 文档批量转换 | 支持多文件输入，统一输出到指定目录 | 一个文件夹下的多个 .txt 文件 |
| 6 | 置信度标注 | 对识别不确定的内容标注 `[需核实:字段]` 占位符 | OCR 识别模糊的日期 |

### 1.2 不能做什么

| 序号 | 限制项 | 说明 |
|------|--------|------|
| 1 | 不处理加密文件 | 需要密码的 PDF、加密压缩包无法解析 |
| 2 | 不保留复杂排版 | 页眉页脚、多栏布局、艺术字效果会丢失 |
| 3 | 不识别手写内容 | 手写笔记、签名等非印刷体无法准确转换 |
| 4 | 不执行语义总结 | 只做结构转换，不生成摘要或提炼观点 |
| 5 | 不修改原始文件 | 转换过程只读，输出为新文件 |

### 1.3 适用对象

- **内容运营人员**：需要将多来源素材统一为 Markdown 格式以便发布
- **技术文档写作者**：需要将 PDF 规格书、网页文档转为可编辑的 Markdown
- **数据分析师**：需要将非结构化文本转为结构化数据以便后续处理
- **知识管理者**：需要将散落的笔记、对话记录归档为统一格式

---

## 二、触发方式

### 2.1 触发词

当输入内容包含以下关键词时，本技能自动激活：

- 核心触发词：`any2md`、`转markdown`、`转md`
- 补充触发词：`结构化转换`、`文档转换`、`内容整理`、`格式转换`

### 2.2 场景映射表

| 用户说（大白话） | 实际需求 | 本技能动作 |
|------------------|----------|------------|
| "帮我把这个 PDF 变成 Markdown" | PDF 内容提取与结构化 | 解析 PDF → 输出 .md 文件 |
| "这段聊天记录整理一下" | 对话内容结构化 | 识别说话人 → 转为对话格式 |
| "这个网页内容太乱了，帮我整理" | 网页正文提取 | 去除噪音 → 输出干净 Markdown |
| "我有一堆 txt 文件要统一格式" | 批量格式转换 | 遍历目录 → 批量输出 .md |
| "这个文档转出来要能直接编辑" | 可编辑格式输出 | 保留结构 → 输出标准 Markdown |

---

## 三、标准流程

### 3.1 前置条件

| 条件项 | 要求 | 检查方式 |
|--------|------|----------|
| 输入文件存在 | 文件路径有效且可读 | `ls -l <file>` |
| 输入格式受支持 | 文本/PDF/网页/对话/文档 | 查看文件扩展名 |
| 输出目录可写 | 目标目录存在且有写权限 | `touch <dir>/.write_test` |
| 磁盘空间充足 | 至少 2 倍于输入文件大小 | `df -h` |

### 3.2 执行步骤

**步骤 1：识别输入类型**

```bash
# 检查文件类型
file input.pdf
# 输出示例: input.pdf: PDF document, version 1.4
```

**步骤 2：选择转换模式**

| 输入类型 | 转换模式 | 命令示例 |
|----------|----------|----------|
| 纯文本 | `text` | `any2md input.txt -o output.md` |
| PDF | `pdf` | `any2md input.pdf -o output.md` |
| 网页 URL | `web` | `any2md https://example.com -o output.md` |
| 对话记录 | `chat` | `any2md chat.log -o output.md --type chat` |
| 批量文件 | `batch` | `any2md *.txt -o ./output_dir/` |

**步骤 3：执行转换**

```bash
# 单文件转换
any2md input.txt -o output.md

# 批量转换（输出到指定目录）
any2md ./docs/*.pdf -o ./markdown_output/

# 预览模式（不实际写入，仅显示结果）
any2md input.txt --dry-run
```

**步骤 4：检查输出**

```bash
# 查看输出文件头部
head -50 output.md

# 检查置信度标注
grep -n "需核实" output.md
```

**步骤 5：验证完整性**

```bash
# 对比输入输出行数（文本文件）
wc -l input.txt output.md

# 检查关键段落是否保留
grep -n "关键标题" output.md
```

### 3.3 输出规范

| 规范项 | 要求 | 示例 |
|--------|------|------|
| 文件扩展名 | 必须为 `.md` | `report.md` |
| 标题层级 | 使用 `#` 至 `######` | `# 一级标题` |
| 列表 | 使用 `-` 或 `1.` | `- 项目一` |
| 表格 | 使用管道符 `|` | `\| 列1 \| 列2 \|` |
| 代码块 | 使用三个反引号 | ```` ```python ```` |
| 引用 | 使用 `>` | `> 引用内容` |
| 置信度标注 | 使用 `[需核实:字段名]` | `[需核实:日期]` |

---

## 四、置信度门控

### 4.1 置信度分级

| 置信度等级 | 标识 | 含义 | 处理方式 |
|------------|------|------|----------|
| 高（≥90%） | 无标注 | 内容识别准确 | 直接输出 |
| 中（70%-89%） | `[需核实:字段]` | 内容可能不准确 | 标注占位符 |
| 低（<70%） | `[需核实:字段]` + 警告 | 内容不可靠 | 标注并提示用户 |

### 4.2 常见需核实场景

| 场景 | 示例 | 输出 |
|------|------|------|
| OCR 识别模糊 | 扫描件中的数字 | `[需核实:合同编号]` |
| 网页编码异常 | 乱码文本 | `[需核实:段落内容]` |
| PDF 字体缺失 | 特殊字符显示异常 | `[需核实:特殊符号]` |
| 对话人识别不清 | 多人聊天记录 | `[需核实:发言人]` |

### 4.3 处理原则

1. **不编造**：无法确定的内容绝不猜测，一律标注 `[需核实:字段]`
2. **可追溯**：标注字段保留原始上下文，便于用户人工核对
3. **批量处理**：批量转换时，若超过 10% 内容需核实，输出汇总警告

---

## 五、错误码体系

### 5.1 错误码速查表

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| `E001` | 文件不存在 | "找不到输入文件，请检查路径" | 1. 确认路径正确 2. 检查文件名拼写 |
| `E002` | 格式不支持 | "该文件格式暂不支持转换" | 1. 转换为支持的格式 2. 联系管理员 |
| `E003` | 输出目录不可写 | "输出目录没有写入权限" | 1. 修改目录权限 2. 更换输出目录 |
| `E004` | PDF 加密 | "PDF 文件已加密，无法解析" | 1. 解密 PDF 2. 使用可访问的副本 |
| `E005` | 网页抓取失败 | "无法访问目标网页" | 1. 检查网络连接 2. 确认 URL 有效 |
| `E006` | 磁盘空间不足 | "磁盘空间不足，无法完成转换" | 1. 清理磁盘 2. 更换存储位置 |
| `E007` | 转换超时 | "转换超时，文件可能过大" | 1. 拆分文件 2. 增加超时时间 |
| `E008` | 内容为空 | "输入内容为空，无法转换" | 1. 检查输入文件 2. 确认内容非空 |

### 5.2 错误处理流程

```bash
# 示例：处理 E001 错误
any2md missing.txt -o output.md
# 输出: [E001] 找不到输入文件，请检查路径

# 修正：确认文件存在
ls -l missing.txt
# 若不存在，使用正确路径
any2md /path/to/existing.txt -o output.md
```

---

## 六、FAQ 反模式

### 6.1 常见坑与反模式对照

| 序号 | 常见坑 | 反模式（错误做法） | 正确做法 |
|------|--------|-------------------|----------|
| 1 | 批量处理前不预览 | 直接对 100 个文件执行转换 | 先用 `--dry-run` 预览 3-5 个文件 |
| 2 | 输出文件命名混乱 | 输出为 `output.md` 覆盖原文件 | 使用 `-o` 指定带语义的文件名 |
| 3 | 忽略置信度标注 | 直接使用含 `[需核实]` 的内容 | 人工核对所有标注字段 |
| 4 | 处理加密 PDF | 反复尝试转换失败 | 先解密，再转换 |
| 5 | 网页转换不检查编码 | 输出乱码 | 指定 `--encoding utf-8` |

### 6.2 反模式示例

**反模式 1：不预览直接批量处理**

```bash
# 错误做法
any2md ./docs/*.pdf -o ./output/

# 正确做法
any2md ./docs/sample.pdf --dry-run
# 确认结果满意后
any2md ./docs/*.pdf -o ./output/
```

**反模式 2：忽略置信度标注**

```bash
# 错误做法：直接使用转换结果
cat output.md | grep "需核实"  # 忽略这些内容

# 正确做法：核对所有标注
grep -n "需核实" output.md
# 逐一确认后，移除或修正标注
```

---

## 七、渐进式披露

### 7.1 速查卡（30 秒上手）

```
any2md 使用三步：
1. 输入：any2md <文件或URL> -o <输出.md>
2. 预览：any2md <文件> --dry-run
3. 批量：any2md *.txt -o ./output/
```

### 7.2 新手路径（5 分钟入门）

1. **安装**：下载 `run.py` 到本地目录
2. **验证**：运行 `python run.py --selftest` 确认安装成功
3. **首次转换**：使用一个简单的文本文件测试
4. **检查输出**：用文本编辑器打开生成的 `.md` 文件
5. **处理标注**：查找 `[需核实]` 字段并人工确认

### 7.3 进阶路径（深度使用）

1. **批量处理**：掌握多文件输入和目录输出
2. **自定义配置**：调整转换参数（如编码、标题层级）
3. **错误处理**：熟悉错误码体系，快速定位问题
4. **置信度管理**：建立标注字段的核对流程
5. **集成使用**：将 any2md 嵌入自动化工作流

---

## 八、参数参考表

### 8.1 命令行参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `-o, --output` | string | 当前目录 | 输出文件或目录路径 |
| `--dry-run` | flag | 关闭 | 预览模式，不写入文件 |
| `--type` | string | 自动检测 | 指定输入类型（text/pdf/web/chat） |
| `--encoding` | string | utf-8 | 输入文件编码 |
| `--title-level` | int | 1 | 一级标题的层级（1-6） |
| `--no-conf` | flag | 关闭 | 不输出置信度标注 |
| `--selftest` | flag | 关闭 | 运行自检程序 |
| `--version` | flag | 关闭 | 显示版本号 |

### 8.2 边界值

| 参数 | 最小值 | 最大值 | 说明 |
|------|--------|--------|------|
| 输入文件大小 | 1 KB | 100 MB | 超过 100MB 建议拆分 |
| 批量文件数量 | 1 | 500 | 超过 500 个建议分批 |
| 标题层级 | 1 | 6 | 对应 `#` 到 `######` |
| 超时时间 | 10 秒 | 300 秒 | 默认 60 秒 |

---

## 九、用户协议

<!-- user-agreement-injected -->

**使用 any2md 技能即表示您同意以下条款：**

1. **责任承担**：使用者自行承担因使用本技能产生的全部责任。包括但不限于数据丢失、内容错误、操作失误等造成的直接或间接损失。

2. **禁止反向工程**：不得对本技能进行反向工程、反编译、破解或试图获取源代码（除非明确许可）。

3. **合法使用**：使用者保证输入内容合法合规，不侵犯第三方权益，不包含违法信息。

4. **无担保声明**：本技能按"现状"提供，不附带任何明示或暗示的担保。

5. **变更权利**：技能作者保留随时修改、更新或终止本技能的权利。

---

## 十、许可证（License）

<!-- professional-license-embedded -->

**MIT License**

Copyright (c) 2026 LinguaForge

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

*本 Skill 由 AI 辅助生成，仅供参考。使用前请阅读相关文档并自行验证功能。*
