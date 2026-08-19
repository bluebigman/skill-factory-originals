---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: rtk-token-saver-pro
name: rtk-token-saver
displayName: 上下文瘦身 代码压缩 对话精简
description: 压缩代码与对话上下文，减少 LLM Token 消耗，适配主流 AI 编码工具。
version: 1.0.7
rules_version: cpr-20260819-n551
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/rtk-token-saver-pro
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 林默
agent_created: true
trigger_words: ["rtk-token-saver", "token压缩", "上下文精简", "代码摘要", "对话历史压缩", "省token", "压缩上下文"]
---

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->


> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# rtk-token-saver 技能手册

## 一、能力边界（一页纸速查卡）

### 能做什么

| 能力项 | 说明 | 示例 |
|--------|------|------|
| 代码压缩 | 去除注释、精简变量名、合并冗余逻辑 | 将 200 行工具函数压缩至 60 行摘要 |
| 对话历史压缩 | 将多轮对话提炼为要点列表 | 将 50 轮调试对话压缩为 10 条关键结论 |
| 文档摘要 | 提取文档核心论点与结构 | 将 30 页设计文档压缩为 1 页要点 |
| 多源输入 | 支持文件路径、URL、直接粘贴文本 | 同时处理 `src/` 目录下 5 个文件 |
| 格式适配 | 输出 Markdown / JSON / 纯文本 | 供不同下游工具消费 |
| 置信度标注 | 对推断内容标注可信程度 | `[低置信] 基于函数名推断` |

### 不能做什么

| 限制项 | 说明 |
|--------|------|
| 不编造内容 | 无法从输入推断的信息，输出 `[需核实:字段名]` 占位符 |
| 不执行代码 | 只做静态分析与压缩，不运行程序 |
| 不修改原文件 | 默认只输出压缩结果，不写回源文件 |
| 不处理加密内容 | 加密/二进制文件无法解析 |
| 不保证无损 | 压缩必然丢失细节，保留规则可配置 |

### 适用对象

- 使用 AI 编码工具（Copilot、Cursor、Codex 等）的开发者
- 需要将大量上下文喂给 LLM 的提示词工程师
- 维护长对话历史的技术支持人员
- 需要批量整理代码库文档的团队

---

## 二、触发方式

### 触发词

直接说出以下任一短语即可激活：

- `rtk-token-saver`
- `token压缩`
- `上下文精简`
- `代码摘要`
- `对话历史压缩`
- `省token`
- `压缩上下文`

### 大白话场景映射表

| 你想做什么 | 直接说 | 本技能会做什么 |
|-----------|--------|---------------|
| 把一段很长的代码缩短 | "帮我把这个工具函数压缩一下，太长了" | 识别代码结构，去除注释和空行，精简标识符 |
| 把聊天记录变短 | "把我和 AI 的这段调试对话压缩成要点" | 提取关键结论、错误原因、解决方案 |
| 把文档变短 | "这篇设计文档太长了，给我个摘要" | 提取章节结构、核心论点、关键决策 |
| 同时处理多个文件 | "把 src 目录下所有 .py 文件都压缩一遍" | 批量读取、逐个压缩、汇总输出 |
| 压缩后还要给别的工具用 | "压缩结果用 JSON 格式给我" | 输出结构化 JSON，便于程序消费 |

---

## 三、标准流程

### 前置条件

| 条件 | 检查方式 | 不满足时 |
|------|---------|---------|
| 二进制已安装 | 执行 `rtk-token-saver --selftest` | 先安装，见 FAQ |
| 输入内容可访问 | 文件存在 / URL 可访问 / 文本已复制 | 先解决访问问题 |
| 明确输出格式 | 默认 Markdown，可指定 JSON/纯文本 | 使用默认值即可 |

### 执行步骤

1. **解析输入**：识别输入类型（单文件 / 多文件 / URL / 文本），读取内容。
   - 文件路径：检查存在性与可读性
   - URL：发起请求，检查 HTTP 状态码
   - 文本：直接接收

2. **预处理**：
   - 检测编码（UTF-8 / GBK / ASCII）
   - 识别语言类型（Python / JS / TS / Markdown / 纯文本）
   - 估算 Token 数（按 4 字符 ≈ 1 token 粗估）

3. **压缩处理**（按策略执行）：
   - **标准策略**（默认）：删除注释、合并空行、精简变量名、保留函数签名与核心逻辑
   - **激进策略**：在标准策略基础上，进一步删除类型注解、合并相似分支
   - **保守策略**：仅删除注释和空行，其余不动

4. **置信度标注**：
   - 对推断内容标注 `[低置信]` / `[中置信]`
   - 对缺失信息标注 `[需核实:字段名]`

5. **输出整理**：
   - 按指定格式（Markdown / JSON / 纯文本）输出
   - 附压缩统计（原始 Token 数 → 压缩后 Token 数 → 压缩率）

### 输出规范

**Markdown 格式示例：**

```markdown
## 压缩结果

### 文件: utils/helper.py
- 原始: 1,240 tokens
- 压缩后: 380 tokens
- 压缩率: 69.4%

### 摘要
- 函数 `process(data)`: 数据清洗入口，调用 `validate` 和 `transform`
- 函数 `validate(item)`: 检查必填字段，返回布尔值
- 函数 `transform(item)`: 字段映射与格式转换

### 置信度说明
- `process(data)` 内部逻辑 [需核实:函数体逻辑] [低置信]
```

**JSON 格式示例：**

```json
{
  "files": [
    {
      "path": "utils/helper.py",
      "original_tokens": 1240,
      "compressed_tokens": 380,
      "compression_ratio": 0.694,
      "summary": "...",
      "confidence": "medium",
      "placeholders": ["函数体逻辑"]
    }
  ]
}
```

---

## 四、置信度门控

### 原则

1. **不编造**：无法从输入中明确推断的内容，输出 `[需核实:字段名]` 占位符，而非猜测。
2. **标注来源**：中低置信度的推断内容，标注推断依据（如"基于函数名推断"）。
3. **二次确认**：当输入类型无法明确识别（如文件扩展名缺失）时，暂停处理并向用户确认。
4. **失败透明**：处理失败的文件/URL 列入失败清单，不静默跳过。

### 置信度等级

| 等级 | 含义 | 示例 |
|------|------|------|
| 高置信 | 直接从输入中读取，无推断 | 函数名、参数列表、注释内容 |
| 中置信 | 基于上下文合理推断 | "基于调用关系推断该函数为入口" |
| 低置信 | 仅有间接线索 | "基于命名风格猜测为工具函数" |
| 需核实 | 完全无法确定 | `[需核实:函数体逻辑]` |

### 示例

- 输入：`process(data)` 函数体为空 → 输出：`函数 process(data) [低置信] [需核实:函数体逻辑]`
- 输入：URL 返回 404 → 输出：`[失败] https://example.com/page → HTTP 404，页面不存在`

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|---------|---------|
| E001 | 输入文件不存在 | `[错误] 文件不存在: path/to/file` | 检查路径拼写，确认文件已保存 |
| E002 | 文件格式不支持 | `[错误] 无法解析的文件格式: .xyz` | 转换为支持的格式（.py/.js/.ts/.md/.txt） |
| E003 | URL 不可访问 | `[错误] URL 请求失败: {url} → HTTP {code}` | 检查 URL 拼写、网络连接、是否需要代理 |
| E004 | 输入类型无法识别 | `[需确认] 无法识别输入类型，请指定: 文件/URL/文本` | 明确指定输入类型 |
| E005 | 编码无法识别 | `[错误] 无法识别文件编码` | 手动指定编码（如 `--encoding utf-8`） |
| E006 | 二进制文件 | `[错误] 不支持二进制文件: path/to/file` | 确认文件为文本格式 |
| E007 | 压缩结果为空 | `[警告] 压缩后无有效内容，已返回原始输入` | 检查输入是否全为注释/空内容 |
| E008 | 输出目录不可写 | `[错误] 无法写入输出文件: path/to/output` | 检查目录权限，更换输出路径 |

### 重试与降级策略

1. **重试**：网络类错误（E003）自动重试 3 次，间隔 2 秒。
2. **降级**：激进策略失败时，自动降级为标准策略；标准策略失败时，降级为保守策略。
3. **跳过**：批量处理时，单个文件失败不中断整体流程，失败项列入失败清单。

---

## 六、FAQ 反模式

### 常见坑 1：压缩后代码不可用

**反模式**：直接使用激进策略压缩生产代码，导致变量名全部变成 `a`、`b`、`c`，无法维护。

**正确做法**：生产代码使用保守策略，仅删除注释和空行；激进策略仅用于一次性分析场景。

### 常见坑 2：忽略置信度标注

**反模式**：把低置信度的推断结果当作事实使用，导致下游判断错误。

**正确做法**：看到 `[需核实]` 或 `[低置信]` 标注时，先核实再使用。

### 常见坑 3：批量处理时静默失败

**反模式**：批量处理 20 个文件，有 3 个失败，但只看到 17 个成功结果，以为全部完成。

**正确做法**：检查输出末尾的失败清单，确认无遗漏。

### 常见坑 4：压缩对话历史丢失关键决策

**反模式**：压缩对话时只保留结论，丢失了决策背景和备选方案。

**正确做法**：使用 `--keep decisions` 参数，保留决策记录和备选方案。

### 常见坑 5：超大文件一次性处理

**反模式**：直接压缩 100K+ token 的超大文件，导致内存溢出或超时。

**正确做法**：使用分块压缩，每块不超过 10K token，最后合并结果。

---

## 七、高级用法

### 参数化配置

| 参数 | 说明 | 默认值 | 示例 |
|------|------|--------|------|
| `--strategy` | 压缩策略：standard / aggressive / conservative | standard | `--strategy aggressive` |
| `--format` | 输出格式：markdown / json / text | markdown | `--format json` |
| `--keep` | 保留规则：comments / annotations / decisions / all | 无 | `--keep decisions` |
| `--encoding` | 输入文件编码 | 自动检测 | `--encoding utf-8` |
| `--chunk-size` | 分块大小（token 数） | 10000 | `--chunk-size 5000` |
| `--output` | 输出文件路径 | 标准输出 | `--output result.md` |
| `--selftest` | 自检安装正确性 | 无 | `rtk-token-saver --selftest` |
| `--version` | 显示版本号 | 无 | `rtk-token-saver --version` |

### 自定义保留规则

使用 `--keep` 参数自定义保留内容：

```bash
# 保留所有函数体但删除注释
rtk-token-saver input.py --keep function-body --drop comments

# 保留决策记录和备选方案
rtk-token-saver conversation.log --keep decisions alternatives
```

### 与其他 Skill 串联

1. **压缩代码 → 代码审查**：将压缩结果送入代码审查 Skill，快速定位问题。
2. **压缩对话历史 → 决策记录**：将要点送入决策记录 Skill，沉淀团队知识。
3. **压缩文档 → 知识库整理**：将摘要送入知识库整理 Skill，建立索引。

### 批量处理脚本示例

```bash
# 批量压缩 src/ 目录下所有 .py 文件，输出 JSON 格式
for f in src/*.py; do
  rtk-token-saver "$f" --format json --output "compressed/$(basename $f).json"
done
```

### 分块压缩超大文件

```bash
# 将大文件按 5000 token 分块压缩
rtk-token-saver large_file.py --chunk-size 5000 --format json
```

---

## 八、渐进式披露

### 新手路径（5 分钟上手）

1. 阅读「一、能力边界」了解适用范围。
2. 按「三、标准流程」执行一次基础压缩。
3. 使用默认参数（标准策略 + Markdown 输出）。
4. 参考「二、触发方式」中的大白话示例，直接说出需求。

### 进阶路径（1 小时精通）

1. 学习「七、高级用法」中的参数化配置。
2. 尝试批量处理和自定义输出格式。
3. 掌握「五、错误码体系」中的错误码和重试/降级策略，能自主排查问题。
4. 使用 `--keep` 参数自定义保留规则。

### 专家路径（深度定制）

1. 自定义压缩策略（修改保留规则，如保留所有函数体但删除注释）。
2. 与其他 Skill 串联形成工作流（如压缩后自动生成测试用例）。
3. 编写脚本自动化批量压缩任务（结合 `--format json` 输出）。
4. 使用分块压缩处理超大文件（>100K token）。

---

## 用户协议

使用本 Skill 即表示您同意以下条款：

1. **责任承担**：使用者自行承担因使用本 Skill 产生的全部责任。本 Skill 仅提供文本压缩与摘要功能，不构成任何形式的专业建议。
2. **禁止反向工程**：不得对本 Skill 的底层算法、提示词结构进行反向工程、反编译或提取核心逻辑用于商业用途。
3. **内容合规**：使用者应对输入内容的合法性、合规性负责，不得使用本 Skill 处理违法违规信息。
4. **无担保**：本 Skill 按"现状"提供，不附带任何明示或暗示的担保，包括但不限于适销性、特定用途适用性。
5. **服务变更**：本 Skill 可能随时更新或终止，恕不另行通知。

<!-- user-agreement-injected -->

---

## 许可证（License）

MIT License

Copyright (c) 2026 林默

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

<!-- professional-license-embedded -->

---

*本 Skill 由 AI 辅助生成，仅供参考。使用前请阅读相关文档。*
