---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: opencrow
name: opencrow
displayName: 数据采集 结构化整理 批量处理
description: 将用户提供的各类数据源转换为规范结构化结果，支持批量与自定义格式。
version: 1.0.1
rules_version: cpr-20260821-n626
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/opencrow
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 林默
agent_created: true
trigger_words: ["爬虫采集", "数据整理", "结构化输出", "批量处理", "信息提取"]
---

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->


> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# opencrow 技能文档

## 一、能力边界速查卡

本技能面向需要将零散数据源（文本、表格、网页链接）转化为统一结构化格式的用户，适用于数据整理、信息归档、批量转换等场景。

| 维度 | 说明 |
|------|------|
| 输入类型 | 用户直接粘贴的文本、上传的文件（CSV/TXT/JSON）、可访问的 URL |
| 输出类型 | 结构化字段集合（JSON/表格）、带置信度标注的结果列表 |
| 单次处理量 | 建议不超过 500 条独立记录，超出请分批执行 |
| 处理耗时 | 单条记录平均 0.5~2 秒，批量任务视数据量而定 |

**能做：**

1. 从非结构化文本中提取关键字段（如名称、日期、编号、金额）
2. 将表格类数据按指定字段映射重新组织
3. 对 URL 指向的公开页面内容做基础解析与字段抽取
4. 批量处理同格式文件，保持输出结构一致
5. 对提取结果标注置信度，辅助人工复核

**不能做：**

- 无法访问需要登录验证或付费墙后的内容
- 不执行 JavaScript 渲染后的页面数据抓取
- 不处理图像、音频、视频中的信息提取
- 不保证提取字段的绝对准确，需人工抽检
- 不提供数据可视化或图表生成功能

**适用对象：** 需要快速整理批量数据的运营人员、进行资料归档的行政人员、需要从网页提取结构化信息的研究者。

---

## 二、触发方式与场景映射

当你的需求与下表左侧描述相符时，可直接使用本技能。

| 场景描述（大白话） | 触发词示例 | 预期结果 |
|-------------------|-----------|---------|
| "帮我把这堆联系人信息整理成表格" | 数据整理、结构化输出 | 统一字段的联系人列表 |
| "这个网页里的产品价格帮我抓下来" | 爬虫采集、信息提取 | 含品名/价格/链接的条目 |
| "我有 50 个文件需要统一格式" | 批量处理、格式转换 | 格式一致的多文件输出 |
| "这段文字里的日期和金额帮我挑出来" | 信息提取、关键字段 | 标注置信度的字段清单 |

---

## 三、标准处理流程

### 前置条件

- 输入数据已准备好，文件与工作目录在同一路径下
- 文件命名遵循统一规则（如 `data_01.csv`、`data_02.csv`）
- 明确告知输出格式偏好（默认输出 JSON 结构）

### 执行步骤

**步骤 1：输入确认**

| 参数 | 必填 | 说明 |
|------|------|------|
| 数据来源 | 是 | 粘贴文本 / 文件路径 / URL 列表 |
| 目标字段 | 否 | 期望输出的字段名清单，缺省则自动识别 |
| 输出格式 | 否 | json / csv / 表格，默认 json |

**步骤 2：试运行**

取单条样本执行完整流程，核对：

- 字段名称是否符合预期
- 数据类型是否正确（字符串/数字/日期）
- 置信度标注是否合理

**步骤 3：批量执行**

试运行通过后，对全量数据执行。处理过程中保留原始文件备份，输出文件命名规则为 `原文件名_output.格式`。

**步骤 4：结果校验**

随机抽取 10%~20% 输出条目，逐项核对：

- 关键字段是否与源数据一致
- 是否有遗漏或多余条目
- 置信度低于 0.7 的字段是否已标注

### 输出规范

```json
{
  "record_id": "唯一标识",
  "fields": {
    "字段名1": "值1",
    "字段名2": "值2"
  },
  "confidence": 0.95,
  "source": "数据来源标识"
}
```

---

## 四、置信度门控机制

当遇到以下情况时，本技能不会强行猜测，而是输出占位符供人工确认：

| 情况 | 输出占位 | 说明 |
|------|---------|------|
| 字段值缺失 | `[需核实:字段名]` | 源数据中未找到对应信息 |
| 格式冲突 | `[需核实:格式]` | 同一字段出现多种格式，无法判定标准 |
| 数据超范围 | `[需核实:范围]` | 数值超出合理区间，疑似异常 |
| 多义性 | `[需核实:歧义]` | 同一内容可作多种解读 |

**处理原则：** 宁可标注待核实，绝不编造数据。所有占位符在输出中统一使用 `[需核实:...]` 格式，便于程序化检索。

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|---------|---------|
| E001 | 输入为空 | "未检测到有效输入，请提供数据源" | 检查输入内容是否为空或格式错误 |
| E002 | 文件不存在 | "指定路径下未找到文件，请确认路径" | 核对文件路径与文件名 |
| E003 | 格式不支持 | "当前格式不在支持范围内（支持：txt/csv/json/url）" | 转换格式后重试 |
| E004 | 批量中断 | "批量处理在第 N 条中断，请检查该条数据" | 定位第 N 条记录，修复后重跑 |
| E005 | 字段映射失败 | "目标字段与源数据无法对应，请检查字段名" | 核对字段映射关系，调整后重试 |
| E006 | 输出写入失败 | "无法写入输出文件，请检查目录权限" | 确认目录可写，或更换输出路径 |

---

## 六、常见坑与反模式对照

| 常见错误做法 | 问题说明 | 推荐做法 |
|-------------|---------|---------|
| 跳过试运行直接全量处理 | 字段映射错误被放大到全量数据 | 务必先跑单条样本，确认无误再批量 |
| 忽略置信度标注 | 低置信度字段混入正式结果 | 保留置信度字段，人工复核低分项 |
| 覆盖原始文件 | 处理出错后无法回退 | 始终保留原始文件，输出另存新文件 |
| 一次性处理超大数据量 | 内存溢出或超时中断 | 分批处理，每批不超过 500 条 |
| 不检查 URL 可访问性 | 失效链接导致提取失败 | 先批量检查 URL 状态码，过滤无效链接 |

---

## 七、分层次阅读路径

### 新手路径（首次使用）

1. 阅读「能力边界速查卡」确认本技能是否满足需求
2. 查看「触发方式与场景映射」找到对应场景
3. 按「标准处理流程」从步骤 1 开始执行
4. 遇到问题查「错误码体系」定位并修正

### 进阶路径（熟练使用）

1. 熟悉「置信度门控机制」，理解占位符含义
2. 掌握「常见坑与反模式对照」，规避典型错误
3. 自定义字段映射规则，适配特定业务场景
4. 结合批量处理与结果校验，建立完整数据流水线

---

## 八、参数参考表

| 参数名 | 类型 | 默认值 | 可选值 | 说明 |
|--------|------|--------|--------|------|
| `input_type` | string | auto | text/file/url | 输入数据类型 |
| `output_format` | string | json | json/csv/table | 输出格式 |
| `batch_size` | int | 100 | 10~500 | 每批处理条数 |
| `confidence_threshold` | float | 0.7 | 0~1 | 低于此值的字段强制标注 |
| `field_mapping` | dict | null | 自定义映射 | 源字段到目标字段的映射关系 |
| `deduplicate` | bool | true | true/false | 是否去除重复记录 |

---

## 九、用户协议

使用本技能即表示您同意以下条款：

1. 本技能仅供学习与参考用途，使用者应自行承担因使用本技能产生的全部责任。
2. 使用者需确保所处理的数据来源合法合规，不得利用本技能采集、处理任何违法违规内容。
3. 禁止对本技能进行反向工程、破解、篡改或试图获取其底层实现逻辑。
4. 本技能不提供任何明示或暗示的担保，包括但不限于适销性、特定用途适用性。
5. 因使用本技能导致的任何直接或间接损失，技能作者不承担任何责任。

<!-- user-agreement-injected -->

---

## 十、许可证（License）

MIT License

Copyright (c) 2025 林默

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
