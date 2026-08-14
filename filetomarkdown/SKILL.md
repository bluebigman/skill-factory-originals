---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: filetomarkdown
name: filetomarkdown
displayName: 文档转写 格式转换 内容提取
description: 将文件或链接转为结构化Markdown，保留关键信息并标注置信度。
version: 1.0.2
rules_version: cpr-20260814-n426
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/filetomarkdown
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: Kaiwen Zhang
agent_created: true
trigger_words: ["filetomarkdown", "转Markdown", "文档转写", "格式转换", "内容提取", "转成md", "结构化输出"]
---

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->


> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# filetomarkdown — 文档转写与结构化输出 Skill

## 一、能力边界：一页纸速查卡

本 Skill 用于将用户提供的**单个文件**或**公开链接**转换为结构化的 Markdown 文档。转换过程中会保留原文的关键信息层级，并对每个信息块标注置信度，方便下游使用。

### 1.1 能做什么

| 能力项 | 说明 | 示例 |
|--------|------|------|
| 本地文件转写 | 读取同目录下的 `.txt`、`.md`、`.csv`、`.json`、`.log` 文件 | `data.csv` → 表格化 Markdown |
| 公开链接抓取 | 抓取可公开访问的网页正文内容 | 新闻文章 → 标题+段落+引用块 |
| 结构化保留 | 识别标题、列表、表格、代码块、引用等元素 | 原 PDF 中的层级标题转为 `##`/`###` |
| 置信度标注 | 对每个提取的信息块附加 `[置信度:高/中/低]` 标记 | OCR 模糊段落标注 `[置信度:低]` |
| 批量预处理 | 支持对同一目录下多个文件进行统一格式转换 | 将 `logs/` 下所有 `.log` 转为 `.md` |

### 1.2 不能做什么

| 限制项 | 说明 |
|--------|------|
| 不处理二进制大文件 | 超过 50MB 的文件需先拆分 |
| 不解析加密/付费内容 | 需要用户提供解密后的明文 |
| 不进行语义总结 | 只做格式转换，不做摘要或观点提炼 |
| 不保证 OCR 准确性 | 扫描件/图片中的文字识别结果可能出错，需人工复核 |
| 不处理动态交互页面 | 需要登录或 JS 渲染的链接无法抓取 |

### 1.3 适用对象

- 需要将散乱文档统一为 Markdown 格式的**内容运营人员**
- 需要从网页/文件中提取结构化信息的**数据分析师**
- 需要快速整理会议记录、日志、配置文件的**开发运维人员**

---

## 二、触发方式与场景映射

### 2.1 触发词

直接使用以下任一说法即可激活本 Skill：

- `filetomarkdown`
- `转Markdown`
- `文档转写`
- `格式转换`
- `内容提取`
- `转成md`
- `结构化输出`

### 2.2 场景映射表

| 用户实际需求（大白话） | 触发动作 |
|----------------------|----------|
| "帮我把这个 txt 文件整理成好看的 Markdown" | 读取文件 → 识别段落/标题 → 输出 `.md` |
| "这个网页内容太乱了，帮我提取成干净的文档" | 抓取链接 → 去除导航/广告 → 输出正文 Markdown |
| "把这几份 CSV 数据转成带表格的 Markdown" | 解析 CSV → 生成 Markdown 表格 → 标注字段类型 |
| "我的日志文件想转成带时间戳的 Markdown" | 解析日志格式 → 按时间分组 → 输出结构化文档 |
| "把这份合同扫描件转成文字版" | OCR 识别 → 输出带置信度标注的 Markdown |

---

## 三、标准操作流程

### 3.1 前置条件

| 条件 | 要求 | 检查方式 |
|------|------|----------|
| 文件位置 | 待处理文件必须位于当前工作目录或子目录中 | `ls` 或 `dir` 确认 |
| 文件命名 | 文件名不得包含空格或特殊字符（建议用 `_` 或 `-`） | 正则检查 `^[a-zA-Z0-9_\-\.]+$` |
| 链接可达性 | 链接必须为 `http://` 或 `https://` 开头，且无需登录 | 浏览器手动验证一次 |
| 磁盘空间 | 至少保留文件大小 3 倍的剩余空间 | `df -h` 查看 |

### 3.2 执行步骤（分步编号）

#### 步骤 1：输入确认

```
输入格式：filetomarkdown <文件路径或URL> [选项]
选项：
  --output <目录>   指定输出目录（默认当前目录）
  --lang <zh|en>    指定源语言（默认自动检测）
  --batch           批量模式（处理目录下所有支持的文件）
  --selftest        运行自检程序
  --version         显示版本信息
```

**示例：**
```bash
filetomarkdown ./meeting_notes.txt --output ./output
filetomarkdown https://example.com/article --lang zh
filetomarkdown ./logs/ --batch
```

#### 步骤 2：试运行（单样本验证）

**操作：** 先选取一个最小样本文件执行转换。

**核对清单：**
- [ ] 输出文件是否生成在指定目录
- [ ] 标题层级是否正确（`#` → `##` → `###`）
- [ ] 表格是否对齐（列数一致）
- [ ] 置信度标注是否出现在每个信息块末尾
- [ ] 特殊字符（如 `|`、`` ` ``）是否被正确转义

**试运行失败处理：** 若输出格式异常，检查源文件编码（UTF-8 无 BOM 为佳），调整后重试。

#### 步骤 3：批量执行

**操作：** 确认单样本无误后，对全量数据执行。

**注意事项：**
- 执行前自动创建 `backup_<时间戳>/` 目录，将原始文件复制备份
- 输出文件命名规则：`<原文件名>_converted.md`
- 若某个文件转换失败，跳过并记录错误日志，不中断整体流程

**批量执行命令：**
```bash
filetomarkdown ./data/ --batch --output ./converted/
```

#### 步骤 4：结果校验

**操作：** 随机抽取 20% 的输出文件进行人工核对。

**校验要点：**
| 校验项 | 通过标准 |
|--------|----------|
| 字段完整性 | 关键字段（标题、日期、作者）无缺失 |
| 数据一致性 | 数字、日期与源文件完全一致 |
| 格式正确性 | Markdown 渲染无乱码、无断裂表格 |
| 置信度合理性 | 低置信度内容确实存在模糊/缺失情况 |

**校验不通过的处理：** 记录问题文件，重新执行步骤 2-3，直至通过率 ≥ 95%。

### 3.3 输出规范

**输出文件结构：**
```markdown
---
source: <原始文件名或URL>
converted_at: <转换时间 ISO 8601>
converter: filetomarkdown v1.0.0
---

# <文档主标题>

> 源文件类型: <txt/csv/json/html>
> 总段落数: <N> | 总字数: <N>

## 内容主体
...
[置信度:高]

## 元数据
- 原始文件大小: <N> KB
- 提取时间: <N> 秒
```

**置信度标注规则：**
| 置信度 | 适用场景 | 标注位置 |
|--------|----------|----------|
| `[置信度:高]` | 文本清晰、结构完整、无歧义 | 段落末尾 |
| `[置信度:中]` | 存在轻微格式混乱或个别字符不确定 | 段落末尾 |
| `[置信度:低]` | OCR 模糊、内容缺失、多义性强 | 段落开头 + 末尾 |

---

## 四、置信度门控机制

### 4.1 核心原则

**不编造、不猜测、不补全。** 当信息不足或无法确认时，使用占位符 `[需核实:字段名]` 明确标注。

### 4.2 占位符使用场景

| 场景 | 占位符示例 | 说明 |
|------|------------|------|
| 日期无法识别 | `[需核实:日期]` | 源文件中日期格式异常 |
| 人名/机构名不确定 | `[需核实:作者姓名]` | OCR 识别结果模糊 |
| 数字单位缺失 | `[需核实:金额单位]` | 只有数字没有单位 |
| 表格列头缺失 | `[需核实:列名]` | CSV 首行非表头 |

### 4.3 门控流程

```
信息提取 → 置信度评估 → 通过(≥0.7) → 直接输出
                    ↘ 不通过(<0.7) → 标记 [需核实:字段] → 输出并提示人工复核
```

---

## 五、错误码体系

| 错误码 | 含义 | 用户提示话术 | 修正步骤 |
|--------|------|--------------|----------|
| `E001` | 文件不存在 | "未找到指定文件，请检查路径是否正确" | 1. 使用 `ls` 确认文件存在 2. 检查文件名拼写 3. 确认文件在当前目录 |
| `E002` | 文件格式不支持 | "该文件类型暂不支持，支持格式：txt/md/csv/json/log" | 1. 将文件转为支持的格式 2. 或使用 `--force` 强制尝试 |
| `E003` | 链接无法访问 | "链接无法访问，请确认链接是否公开且无需登录" | 1. 浏览器手动打开验证 2. 检查网络连接 3. 更换为公开链接 |
| `E004` | 编码解析失败 | "文件编码无法识别，请转换为 UTF-8 编码" | 1. 使用 `iconv` 转换编码 2. 或另存为 UTF-8 无 BOM 格式 |
| `E005` | 输出目录无权限 | "无法写入输出目录，请检查权限" | 1. 使用 `chmod` 修改目录权限 2. 或指定其他输出目录 |
| `E006` | 批量模式中断 | "批量处理在第 N 个文件时中断，请查看 error.log" | 1. 查看 `error.log` 定位问题 2. 修复后从第 N+1 个文件继续 |
| `E007` | 内存不足 | "文件过大，内存不足，请拆分文件后重试" | 1. 将文件按行拆分为多个小文件 2. 逐个处理 |

---

## 六、FAQ 反模式对照

### 6.1 常见坑与正确做法

| 反模式（错误做法） | 问题 | 正确做法 |
|-------------------|------|----------|
| 直接对全量数据执行，不做试运行 | 格式错误导致全部输出作废 | 先跑单个样本，确认无误后再批量 |
| 转换后立即删除原始文件 | 无法回溯校验 | 保留原始文件至少 7 天 |
| 忽略置信度标注，直接使用所有内容 | 低置信度内容可能出错 | 对 `[置信度:低]` 内容逐条人工复核 |
| 用空格代替 Markdown 表格分隔符 | 表格渲染错乱 | 使用 `\|` 作为列分隔符，`---` 作为表头分隔 |
| 链接抓取后不检查正文完整性 | 可能只抓到部分内容 | 对比原文页数/段落数，确认完整性 |

### 6.2 反模式自查清单

- [ ] 是否跳过了试运行步骤？
- [ ] 是否在转换后立即删除了源文件？
- [ ] 是否对低置信度内容直接采信？
- [ ] 是否手动编辑了输出文件中的表格结构？
- [ ] 是否忽略了错误日志中的警告信息？

---

## 七、渐进式披露：分层次阅读路径

### 7.1 速查卡（30 秒上手）

```
1. 放文件到当前目录
2. 运行：filetomarkdown <文件名>
3. 检查输出：<文件名>_converted.md
4. 核对置信度标注，低置信度内容人工复核
```

### 7.2 新手路径（5 分钟掌握）

1. 阅读「一、能力边界」了解适用范围
2. 按「三、标准操作流程」的步骤 1-2 完成一次单文件转换
3. 查看输出文件，对照「3.3 输出规范」检查格式
4. 遇到问题查「五、错误码体系」

### 7.3 进阶路径（深度使用）

1. 掌握批量模式：`filetomarkdown ./dir/ --batch`
2. 自定义输出目录：`--output ./custom_dir/`
3. 处理特殊格式：先转换编码为 UTF-8，再执行转换
4. 结合 CI/CD：将转换命令写入自动化流水线，配合 `--selftest` 做回归测试
5. 二次开发：修改输出模板，调整置信度阈值（默认 0.7）

---

## 八、自检与版本

### 8.1 自检命令

```bash
filetomarkdown --selftest
```

**自检内容：**
- 检查依赖库是否完整
- 生成一个测试文件并执行转换
- 验证输出格式是否符合规范
- 报告自检结果（通过/失败 + 失败原因）

### 8.2 版本信息

```bash
filetomarkdown --version
# 输出：filetomarkdown v1.0.0
```

---

## 用户协议

<!-- user-agreement-injected -->

**使用本 Skill 即表示您同意以下条款：**

1. **责任承担**：使用者自行承担因使用本 Skill 产生的全部责任。包括但不限于数据丢失、内容错误、格式兼容性问题等。本 Skill 提供的是转换工具，不对转换结果的准确性、完整性作任何担保。

2. **禁止反向工程**：使用者不得对本 Skill 的源代码、算法、内部逻辑进行反向工程、反编译、破解或试图提取底层设计。不得移除、篡改或遮挡本 Skill 中的任何版权声明、水印或标识。

3. **合规使用**：使用者应确保待转换的文件和链接内容合法合规，不侵犯第三方知识产权。因使用本 Skill 处理侵权内容所引发的法律纠纷，由使用者自行承担。

4. **服务终止**：本 Skill 作者保留随时更新、修改或终止本 Skill 分发的权利，恕不另行通知。

---

## 许可证（License）

<!-- professional-license-embedded -->

**MIT License**

Copyright (c) 2026 Kaiwen Zhang

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
