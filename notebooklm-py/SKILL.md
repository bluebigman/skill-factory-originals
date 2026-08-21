---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: notebooklm-py
name: notebooklm-py
displayName: 知识库笔记 结构化转换 批量处理
description: 将笔记、文件或URL转为结构化JSON，支持批量处理与置信度标注。
version: 1.0.3
rules_version: cpr-20260821-n626
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/notebooklm-py
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 林墨轩
agent_created: true
trigger_words: ["notebooklm py", "知识库笔记", "笔记处理", "结构化转换", "批量处理", "笔记整理", "文档结构化"]
---

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->


> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# notebooklm-py — 知识库笔记结构化转换工具

## 一、能力边界（速查卡）

### 1.1 能做什么

| 功能项 | 说明 | 示例 |
|--------|------|------|
| 单文件转换 | 将单个笔记文件解析为结构化 JSON | `notebooklm py notes/会议纪要.md` |
| 批量处理 | 一次处理目录下多个文件，输出合并结果 | `notebooklm py notes/ --batch` |
| URL 抓取 | 从网页链接提取正文内容并结构化 | `notebooklm py https://example.com/article` |
| 置信度标注 | 对每个字段标注可信程度（高/中/低） | `"confidence": 0.92` |
| 自定义匹配 | 通过正则表达式筛选待处理文件 | `--pattern "*.md"` |
| 自检模式 | 验证安装与依赖是否正常 | `notebooklm py --selftest` |

### 1.2 不能做什么

- ❌ 不执行语义理解之外的深度推理（如情感分析、意图判断）
- ❌ 不处理加密文件或需要登录认证的私有 URL
- ❌ 不保证 OCR 识别（图片型 PDF 需先自行转换）
- ❌ 不提供数据持久化存储，输出仅限终端或指定文件
- ❌ 不进行跨语言翻译，仅保留原文结构

### 1.3 适用对象

- 知识库管理员：需要将散乱笔记统一为结构化格式
- 数据分析师：需要从文档中提取字段用于下游分析
- 自动化流程开发者：需要将文档处理接入 CI/CD 流水线

---

## 二、触发方式

### 2.1 触发词

| 触发词 | 使用场景 |
|--------|----------|
| `notebooklm py` | 直接调用命令行工具 |
| `知识库笔记` | 在对话中描述需求时触发 |
| `笔记处理` | 需要批量整理笔记时 |
| `结构化转换` | 需要将非结构化文本转为 JSON 时 |
| `批量处理` | 需要一次处理多个文件时 |

### 2.2 场景映射表

| 你说的话 | 工具实际执行的动作 |
|----------|-------------------|
| "帮我把这些笔记整理成表格" | 解析笔记 → 提取标题/时间/标签 → 输出 JSON |
| "这个网页内容帮我存下来" | 抓取 URL → 提取正文 → 结构化输出 |
| "我有一堆 md 文件要统一格式" | 批量扫描目录 → 逐个解析 → 合并输出 |
| "这个字段不太确定，标注一下" | 对低置信度字段添加 `[需核实:字段名]` 标记 |

---

## 三、标准流程

### 3.1 前置条件

- Python 3.8+ 环境
- 已安装 `notebooklm-py` 包（`pip install notebooklm-py`）
- 输入文件编码为 UTF-8（其他编码需先转换）

### 3.2 执行步骤

**第一步：环境自检**

```bash
notebooklm py --selftest
```

预期输出：
```
[OK] Python version: 3.10.12
[OK] Dependencies: all installed
[OK] Network: reachable
```

**第二步：试运行（单文件）**

```bash
notebooklm py sample.md
```

检查输出 JSON 结构是否符合预期。示例输出：

```json
{
  "source": "sample.md",
  "title": "项目周会纪要",
  "date": "2026-08-20",
  "tags": ["会议", "项目"],
  "content": "本周完成...",
  "confidence": 0.95
}
```

**第三步：批量处理**

```bash
notebooklm py notes/ --batch --pattern "*.md" --output result.json
```

参数说明：

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `--batch` | 标志 | 无 | 启用批量模式 |
| `--pattern` | 字符串 | `*.md` | 文件匹配正则 |
| `--output` | 路径 | 终端输出 | 结果写入文件 |
| `--confidence` | 浮点数 | `0.8` | 置信度阈值，低于此值标注 `[需核实]` |

**第四步：结果校验**

```bash
notebooklm py --validate result.json
```

校验规则：
- 所有字段均有值（或 `[需核实]` 占位）
- JSON 格式合法
- 置信度值在 0~1 之间

### 3.3 输出规范

输出 JSON 统一包含以下字段：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `source` | string | 是 | 原始文件路径或 URL |
| `title` | string | 是 | 文档标题 |
| `date` | string | 否 | 文档日期（ISO 格式） |
| `tags` | array | 否 | 标签列表 |
| `content` | string | 是 | 结构化正文内容 |
| `confidence` | float | 是 | 整体置信度（0~1） |
| `fields` | object | 否 | 自定义字段映射 |

---

## 四、置信度门控

### 4.1 置信度判定规则

| 置信度区间 | 标记 | 处理方式 |
|-----------|------|----------|
| 0.9 ~ 1.0 | 无 | 正常输出 |
| 0.7 ~ 0.9 | 无 | 正常输出，但建议人工复核 |
| 0.5 ~ 0.7 | `[需核实:字段名]` | 在对应字段添加占位标记 |
| < 0.5 | 整条丢弃 | 输出警告日志，不生成结果 |

### 4.2 占位符使用规范

当信息不足时，使用以下格式：

```
[需核实:标题]
[需核实:日期]
[需核实:作者]
```

**禁止行为**：
- ❌ 编造不存在的字段值
- ❌ 用"未知"或"待定"替代占位符
- ❌ 跳过置信度标注直接输出

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| `E001` | 文件不存在 | "找不到指定文件，请检查路径" | 1. 确认路径正确 2. 检查文件名大小写 |
| `E002` | 文件编码错误 | "文件编码不支持，请转换为 UTF-8" | 1. 使用 `iconv` 转换 2. 重新运行 |
| `E003` | URL 无法访问 | "URL 返回 404 或超时" | 1. 检查链接有效性 2. 确认网络连通 |
| `E004` | 解析失败 | "无法从内容中提取结构化信息" | 1. 检查文件格式 2. 尝试调整 `--pattern` |
| `E005` | 批量处理中断 | "批量处理在第 N 个文件处中断" | 1. 查看错误日志 2. 排除问题文件后重试 |
| `E006` | 输出写入失败 | "无法写入输出文件，检查权限" | 1. 确认目录可写 2. 更换输出路径 |

---

## 六、FAQ 反模式

### 6.1 常见坑

| 坑 | 反模式 | 正确做法 |
|----|--------|----------|
| 忽略置信度 | 直接使用所有输出，不检查 `[需核实]` 标记 | 批量处理前先过滤低置信度条目 |
| 过度依赖默认参数 | 不指定 `--pattern`，导致误处理非目标文件 | 明确指定文件匹配规则 |
| 一次性处理过多文件 | 一次处理 1000+ 文件导致内存溢出 | 分批处理，每批不超过 200 个 |
| 忽略错误码 | 遇到 `E004` 直接跳过，不排查原因 | 记录错误码，统一处理后重试 |
| 不校验输出 | 处理完直接使用，不运行 `--validate` | 每次批量处理后执行校验步骤 |

### 6.2 反模式对照表

| 反模式 | 问题 | 替代方案 |
|--------|------|----------|
| 手动修改输出 JSON | 破坏结构一致性 | 使用 `--output` 指定格式，再写脚本转换 |
| 用正则硬解析 | 无法处理复杂嵌套结构 | 使用内置解析器，自定义字段用 `--fields` |
| 忽略 `[需核实]` 标记 | 下游系统收到不完整数据 | 在流水线中设置检查点，拦截低置信度数据 |

---

## 七、渐进式披露

### 7.1 速查卡（新手必读）

```
1. 运行 notebooklm py --selftest 检查环境
2. 单文件试运行，确认输出格式
3. 批量处理，指定 --pattern 和 --output
4. 运行 --validate 校验结果
5. 检查 [需核实] 标记，人工补全
```

### 7.2 进阶路径（有经验用户）

**自定义字段映射**

```bash
notebooklm py notes/ --fields "author:作者,project:项目名"
```

**置信度阈值调整**

```bash
notebooklm py notes/ --confidence 0.9
```

低于 0.9 的字段自动添加 `[需核实]` 标记。

**脚本接入下游系统**

```python
import subprocess
import json

result = subprocess.run(
    ["notebooklm", "py", "notes/", "--batch", "--output", "-"],
    capture_output=True, text=True
)
data = json.loads(result.stdout)
# 接入你的数据处理逻辑
```

**错误处理自动化**

```bash
notebooklm py notes/ --batch 2> error.log
# 检查 error.log 中的错误码，编写重试逻辑
```

---

## 八、高级用法

### 8.1 复杂文件命名匹配

```bash
notebooklm py docs/ --pattern "^(?!draft_).*\.(md|txt)$"
```

排除所有 `draft_` 开头的文件。

### 8.2 多目录批量处理

```bash
notebooklm py dir1/ dir2/ dir3/ --batch --output combined.json
```

### 8.3 自定义置信度标注粒度

```bash
notebooklm py notes/ --confidence-field-level
```

对每个字段单独计算置信度，而非整体置信度。

---

## 九、用户协议

<!-- user-agreement-injected -->

**使用须知**

1. **责任承担**：使用者自行承担因使用本技能产生的全部责任。包括但不限于数据处理结果准确性、合规性及安全性。
2. **禁止反向工程**：使用者不得对本技能进行反向工程、反编译、反汇编，或试图提取源代码（除非适用法律允许）。
3. **合规使用**：使用者应确保输入数据的合法性，不得使用本技能处理违反法律法规或侵犯第三方权益的内容。
4. **数据安全**：使用者应自行做好数据备份，本技能不保证数据处理的绝对完整性。
5. **修改与分发**：在遵守 MIT 许可证的前提下，使用者可以修改和分发本技能，但需保留原始版权声明。

---

## 十、许可证（License）

<!-- professional-license-embedded -->

**MIT License**

Copyright (c) 2026 林墨轩

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
