---
slug: duplikate
name: duplikate
displayName: 数据复制 结构转换 批处理工具
description: 将用户提供的数据、文件或URL转换为结构化结果，支持批量处理与自定义格式输出。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 技能工坊·林默
agent_created: true
trigger_words: ["duplikate", "数据复制", "结构转换", "批量处理", "格式转换"]
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# duplikate 技能文档

本 Skill 由 AI 辅助生成，仅供参考。使用前请确认输入数据来源合法合规，并自行承担使用后果。

---

## 一、能力边界速查卡

### 1.1 能做（核心能力）

| 编号 | 能力项 | 说明 | 适用场景示例 |
|------|--------|------|--------------|
| C1 | 数据/文件/URL 结构化转换 | 将非结构化输入转为约定格式的结构化结果 | 网页链接提取标题与正文摘要 |
| C2 | 关键信息识别与保留 | 自动抽取输入中的核心字段，不丢失重要内容 | 从文本中提取日期、编号、名称 |
| C3 | 按约定格式输出 | 支持 JSON / CSV / Markdown 表格等格式 | 生成指定字段结构的报告 |
| C4 | 置信度标注 | 对不确定的字段标注置信度等级 | 识别模糊信息时给出提示 |
| C5 | 批量处理与自定义格式 | 支持多文件/多条目批量执行，可自定义输出模板 | 批量转换同目录下多个文件 |

### 1.2 不能做（明确边界）

| 编号 | 限制项 | 说明 |
|------|--------|------|
| L1 | 不执行代码 | 本技能仅处理文本与结构转换，不运行或执行任何代码 |
| L2 | 不访问付费/受限资源 | 对需要登录或付费的 URL 不进行抓取 |
| L3 | 不保证数据准确性 | 输出结果依赖输入质量，不承担数据真实性核验责任 |
| L4 | 不处理二进制大文件 | 单文件建议不超过 10MB，超过需分片处理 |
| L5 | 不进行语义理解 | 仅做模式识别与结构映射，不做深层语义分析 |

### 1.3 适用对象

- **输入类型**：纯文本、CSV、JSON、Markdown 文件、公开 URL
- **输出类型**：JSON、CSV、Markdown 表格、自定义模板
- **目标用户**：需要批量整理数据、转换格式、提取关键信息的个人或团队

---

## 二、触发方式与场景映射

### 2.1 触发词

- 主触发词：`duplikate`
- 同义触发词：`数据复制`、`结构转换`、`批量处理`、`格式转换`、`数据整理`

### 2.2 场景映射表

| 用户说（大白话） | 实际意图 | 触发动作 |
|------------------|----------|----------|
| "帮我把这个网页内容整理成表格" | URL 转结构化输出 | 执行 C1 + C3 |
| "这个文件夹里的文件都转成 JSON" | 批量格式转换 | 执行 C5 |
| "提取这段文字里的日期和人名" | 关键信息抽取 | 执行 C2 |
| "这个 CSV 帮我转成 Markdown 表格" | 格式转换 | 执行 C3 |
| "不确定的地方标出来" | 置信度标注 | 执行 C4 |

---

## 三、标准执行流程

### 3.1 前置条件

| 条件项 | 要求 |
|--------|------|
| 输入文件命名 | 统一命名规范，如 `input_01.csv`、`input_02.csv` |
| 文件位置 | 所有待处理文件放入同一目录 |
| 输出格式确认 | 用户需明确指定输出格式（JSON/CSV/Markdown） |
| 字段映射确认 | 如有自定义字段需求，需提前说明字段名与类型 |

### 3.2 执行步骤

**Step 1 — 输入准备**
1. 确认待处理文件已放入指定目录
2. 检查文件命名是否符合规范（`前缀_序号.扩展名`）
3. 列出文件清单，与用户确认处理范围

**Step 2 — 单样本试运行**
1. 取第一个文件作为样本
2. 执行解析与转换，生成输出
3. 与用户核对字段完整性、格式正确性
4. 如有偏差，调整映射规则后重新试运行

**Step 3 — 批量执行**
1. 确认试运行结果无误
2. 对全量文件执行转换
3. 输出文件命名规则：`原文件名_output.新扩展名`
4. 保留原始文件备份，不覆盖源文件

**Step 4 — 结果校验**
1. 抽查输出条目（建议不少于 10%）
2. 核对关键字段与源数据一致性
3. 检查置信度标注是否完整
4. 汇总校验报告，告知用户

### 3.3 输出规范

**默认输出格式（JSON）示例：**

```json
{
  "source": "input_01.csv",
  "processed_at": "2025-01-15T10:30:00Z",
  "items": [
    {
      "id": 1,
      "name": "示例条目",
      "date": "2025-01-10",
      "confidence": {
        "date": "high",
        "name": "high"
      }
    }
  ],
  "summary": {
    "total": 1,
    "high_confidence": 1,
    "medium_confidence": 0,
    "low_confidence": 0
  }
}
```

**字段结构说明：**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| source | string | 是 | 源文件名或 URL |
| processed_at | string | 是 | 处理时间（ISO 8601） |
| items | array | 是 | 结构化数据条目列表 |
| items[].id | number | 是 | 条目序号 |
| items[].confidence | object | 是 | 各字段置信度标注 |
| summary | object | 是 | 处理汇总统计 |

---

## 四、置信度门控机制

### 4.1 置信度等级定义

| 等级 | 标识 | 判定标准 |
|------|------|----------|
| 高 | `high` | 字段值明确，无歧义，来源可靠 |
| 中 | `medium` | 字段值可推断，但存在多种可能 |
| 低 | `low` | 字段值模糊，无法确定 |
| 缺失 | `[需核实:字段名]` | 信息不足，无法提取 |

### 4.2 处理规则

1. **信息不足时**：输出 `[需核实:字段名]` 占位符，不编造数据
2. **多义时**：取最可能值并标注 `medium` 置信度，同时列出备选值
3. **冲突时**：保留所有候选值，标注 `low` 置信度，提示用户确认

### 4.3 示例

**输入文本：** "张三在3月参加了会议，李四可能也去了。"

**输出：**
```json
{
  "items": [
    {
      "name": "张三",
      "event": "参加会议",
      "date": "2025-03",
      "confidence": {
        "name": "high",
        "event": "high",
        "date": "medium"
      }
    },
    {
      "name": "李四",
      "event": "参加会议",
      "date": "[需核实:日期]",
      "confidence": {
        "name": "high",
        "event": "medium",
        "date": "low"
      }
    }
  ]
}
```

---

## 五、错误码体系

| 错误码 | 错误描述 | 提示话术 | 修正步骤 |
|--------|----------|----------|----------|
| E001 | 文件不存在 | "未找到指定文件，请确认路径是否正确" | 1. 检查文件路径 2. 确认文件已放入指定目录 |
| E002 | 文件格式不支持 | "当前文件格式不在支持范围内（支持：txt/csv/json/md）" | 1. 转换文件格式 2. 或联系管理员扩展支持类型 |
| E003 | 字段映射失败 | "源数据字段与目标字段无法匹配" | 1. 检查源数据字段名 2. 重新定义映射规则 |
| E004 | 批量处理中断 | "批量处理在第 N 个文件处中断" | 1. 查看错误日志 2. 修复问题文件 3. 从断点继续 |
| E005 | 输出格式错误 | "生成的输出文件格式校验未通过" | 1. 检查模板配置 2. 重新生成输出 |
| E006 | 置信度过低 | "大量字段置信度为 low，建议人工复核" | 1. 检查源数据质量 2. 考虑补充数据源 |

---

## 六、FAQ 与反模式对照

### 6.1 常见坑位

| 坑位编号 | 常见错误 | 反模式（错误做法） | 正确做法 |
|----------|----------|-------------------|----------|
| F01 | 忽略试运行 | 直接对全量数据执行批量处理 | 先用单样本试运行，确认无误后再批量执行 |
| F02 | 覆盖原始文件 | 输出直接写入源文件路径 | 保留原始文件，输出到独立目录或加 `_output` 后缀 |
| F03 | 编造缺失数据 | 信息不足时随意填充默认值 | 使用 `[需核实:字段]` 占位符，提示用户补充 |
| F04 | 忽略置信度 | 所有字段一律标注 high | 根据实际提取质量如实标注置信度 |
| F05 | 格式不统一 | 不同批次输出格式不一致 | 使用统一的输出模板，确保字段结构一致 |

### 6.2 反模式对照表

| 反模式 | 问题描述 | 推荐替代方案 |
|--------|----------|--------------|
| "直接跑吧" | 跳过试运行直接批量处理 | 先跑单样本，确认输出结构正确 |
| "差不多就行" | 对置信度标注敷衍了事 | 严格按置信度判定标准执行 |
| "全转成一种格式" | 忽略用户自定义格式需求 | 先确认输出格式要求，再执行转换 |
| "文件太多不检查了" | 批量处理后不做校验 | 至少抽查 10% 输出条目 |

---

## 七、渐进式披露路径

### 7.1 速查卡（一页纸）

```
duplikate 使用速查：
1. 准备输入 → 文件放入同一目录，命名规范
2. 试运行 → 单样本测试，核对输出
3. 批量执行 → 全量转换，保留备份
4. 校验结果 → 抽查输出，核对关键字段
5. 输出格式 → JSON（默认）/ CSV / Markdown
6. 置信度 → high / medium / low / [需核实:字段]
```

### 7.2 新手路径（首次使用）

1. 阅读「能力边界速查卡」了解基本能力
2. 准备 1-2 个测试文件
3. 按「标准执行流程」Step 1-2 完成试运行
4. 确认输出符合预期后，再执行批量处理
5. 遇到问题参考「错误码体系」定位并解决

### 7.3 进阶路径（熟练用户）

1. 自定义输出模板（字段结构、命名规则）
2. 使用置信度门控机制进行数据质量筛选
3. 结合错误码体系建立自动化处理流水线
4. 对低置信度字段设计人工复核流程

---

## 八、参数配置参考

### 8.1 常用参数表

| 参数名 | 类型 | 默认值 | 可选值 | 说明 |
|--------|------|--------|--------|------|
| `input_dir` | string | `./input` | 任意路径 | 输入文件目录 |
| `output_dir` | string | `./output` | 任意路径 | 输出文件目录 |
| `output_format` | string | `json` | `json`/`csv`/`md` | 输出格式 |
| `confidence_threshold` | number | `0.6` | `0-1` | 置信度阈值，低于此值标注需核实 |
| `batch_size` | number | `100` | `1-1000` | 批量处理条目数 |
| `preserve_source` | boolean | `true` | `true`/`false` | 是否保留源文件备份 |

### 8.2 边界值说明

- **单文件大小**：建议不超过 10MB，超过需分片处理
- **批量处理上限**：单次建议不超过 1000 个文件
- **字段数量限制**：单条目字段数建议不超过 50 个
- **URL 抓取限制**：仅支持公开可访问的 URL，单次最多 10 个

---

## 九、用户协议

<!-- user-agreement-injected -->

**使用条款：**

1. **责任承担**：使用者自行承担使用本 Skill 的全部责任。因使用本 Skill 产生的任何直接或间接损失，技能作者及发布平台不承担任何责任。

2. **合法使用**：使用者承诺仅将本 Skill 用于合法目的，不用于侵犯他人权益、违反法律法规的活动。

3. **禁止反向工程**：使用者不得对本 Skill 进行反向工程、反编译、破解或试图提取源代码。

4. **数据合规**：使用者需确保输入数据的获取与使用符合相关法律法规及平台规定。

5. **免责声明**：本 Skill 提供的输出结果仅供参考，不构成任何专业建议或保证。

---

## 十、许可证（License）

<!-- professional-license-embedded -->

**MIT License**

Copyright (c) 2025 技能工坊·林默

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

*文档版本：1.0.0 | 最后更新：2025-01-15*
