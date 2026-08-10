---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: ambition
name: ambition
displayName: 数据清洗 结构化转换 置信度标注
description: 将任意数据源转化为结构化结果，保留关键信息并标注置信度。
version: 2.0.1
rules_version: cpr-20260810-n301
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/ambition
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: DataForge Studio
agent_created: true
trigger_words: ["ambition", "数据转换", "信息提取", "结构化输出", "数据解析", "字段映射", "置信度评估"]
---

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->


> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# ambition — 数据转换与结构化输出 Skill

## 一、能力边界速查卡

### 1.1 能做什么

| 能力项 | 说明 | 示例 |
|--------|------|------|
| 数据源解析 | 读取 JSON、CSV、纯文本、Markdown 表格等常见格式 | 将一段非结构化招聘文本转为字段化记录 |
| 字段映射 | 将源数据中的同义字段名映射为统一 schema | `"name"` / `"姓名"` / `"full_name"` → `fullName` |
| 置信度标注 | 对每个输出字段给出 0~1 的置信度分数 | `confidence: 0.92` |
| 缺失值占位 | 信息不足时输出 `[需核实:字段名]` 占位符 | `[需核实:phone]` |
| 批量处理 | 支持数组输入，逐条转换并汇总统计 | 100 条客户记录一次转换 |

### 1.2 不能做什么

| 限制项 | 说明 |
|--------|------|
| 不编造数据 | 源数据中不存在的信息，一律输出占位符，绝不猜测 |
| 不执行代码 | 本 Skill 仅做文本级转换，不运行任何脚本或程序 |
| 不处理二进制 | 图片、音频、视频等非文本格式不在处理范围内 |
| 不保证绝对准确 | 转换结果受源数据质量影响，置信度低于 0.6 的字段需人工复核 |

### 1.3 适用对象

- 需要将散乱文本整理为表格数据的运营人员
- 需要批量清洗导入数据的开发人员
- 需要从外部文档中提取关键字段的分析师

---

## 二、触发方式

### 2.1 触发词

当输入内容包含以下任一关键词时，本 Skill 自动激活：

- `ambition`
- `数据转换`
- `信息提取`
- `结构化输出`
- `数据解析`
- `字段映射`
- `置信度评估`

### 2.2 场景映射表

| 用户说（大白话） | 实际需求 | 本 Skill 响应 |
|------------------|----------|---------------|
| "帮我把这段文字变成表格" | 非结构化文本 → 结构化记录 | 解析文本，提取字段，输出 JSON 数组 |
| "这些 CSV 里的列名太乱了，统一一下" | 字段名标准化 | 建立映射表，重命名并输出 |
| "这个数据缺了好多，帮我标出来" | 缺失值识别 | 输出 `[需核实:字段]` 占位符 |
| "这个数据能信多少？" | 数据质量评估 | 输出每个字段的置信度分数 |
| "我有 500 条记录要处理" | 批量转换 | 逐条处理，输出汇总统计 |

---

## 三、标准处理流程

### 3.1 前置条件

- 输入数据必须为纯文本格式（UTF-8 编码）
- 若为文件，需提供文件路径或完整内容
- 明确告知目标 schema（期望输出的字段列表），否则使用默认 schema

### 3.2 执行步骤

**Step 1：识别输入格式**

检查输入数据的结构特征，判断格式类型：

| 格式特征 | 判定结果 |
|----------|----------|
| 以 `{` 或 `[` 开头 | JSON |
| 包含逗号分隔的多列 | CSV |
| 包含 `|` 分隔的表格 | Markdown 表格 |
| 无固定分隔符的连续文本 | 纯文本 |

**Step 2：定义目标 Schema**

若用户未指定，使用默认 schema：

```json
{
  "id": "string",
  "title": "string",
  "description": "string",
  "createdAt": "date",
  "tags": "array<string>",
  "source": "string"
}
```

**Step 3：执行字段映射**

建立源字段到目标字段的映射关系，同义词自动识别：

| 源字段 | 目标字段 | 映射规则 |
|--------|----------|----------|
| name, 姓名, full_name | title | 直接映射 |
| desc, 描述, 详情 | description | 直接映射 |
| date, 日期, time | createdAt | 格式标准化为 ISO 8601 |
| tag, 标签, 分类 | tags | 拆分逗号分隔为数组 |
| url, 链接, 来源 | source | 直接映射 |

**Step 4：计算置信度**

对每个输出字段计算置信度分数，规则如下：

| 条件 | 置信度 |
|------|--------|
| 源数据明确存在且格式正确 | 0.9 ~ 1.0 |
| 源数据存在但格式需转换 | 0.7 ~ 0.89 |
| 源数据存在但含义模糊 | 0.5 ~ 0.69 |
| 源数据不存在 | 0.0（输出占位符） |

**Step 5：生成输出**

输出格式为 JSON 数组，每个元素包含 `data` 和 `confidence` 两个部分：

```json
[
  {
    "data": {
      "id": "001",
      "title": "季度销售报告",
      "description": "2026年Q2销售数据汇总",
      "createdAt": "2026-07-15T00:00:00Z",
      "tags": ["销售", "季度"],
      "source": "internal"
    },
    "confidence": {
      "id": 0.98,
      "title": 0.95,
      "description": 0.88,
      "createdAt": 0.92,
      "tags": 0.85,
      "source": 0.99
    }
  }
]
```

### 3.3 输出规范

- 输出必须为合法 JSON，不得包含注释
- 每个字段必须包含置信度分数，不得遗漏
- 缺失字段输出 `[需核实:字段名]` 作为占位值
- 批量处理时，输出末尾附加统计信息：

```json
{
  "summary": {
    "totalRecords": 100,
    "successCount": 95,
    "needsReviewCount": 5,
    "averageConfidence": 0.87
  }
}
```

---

## 四、置信度门控机制

### 4.1 基本原则

**绝不编造数据。** 当源数据不足以支撑某个字段的准确提取时，必须输出 `[需核实:字段名]` 占位符，而非猜测值。

### 4.2 触发条件

以下情况必须触发置信度门控：

1. 源数据中完全找不到对应字段
2. 源数据存在但格式无法解析
3. 源数据存在多个冲突值
4. 源数据含义模糊，无法确定唯一解释

### 4.3 占位符使用规范

| 场景 | 占位符格式 | 示例 |
|------|------------|------|
| 字段完全缺失 | `[需核实:字段名]` | `[需核实:phone]` |
| 字段格式错误 | `[需核实:字段名-格式]` | `[需核实:date-格式]` |
| 字段值冲突 | `[需核实:字段名-冲突]` | `[需核实:address-冲突]` |

### 4.4 置信度阈值建议

| 置信度范围 | 处理建议 |
|------------|----------|
| 0.9 ~ 1.0 | 可直接使用，无需复核 |
| 0.7 ~ 0.89 | 建议抽样复核 |
| 0.5 ~ 0.69 | 必须人工复核 |
| < 0.5 | 视为缺失，需重新采集数据 |

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| `E001` | 输入格式无法识别 | "无法识别输入数据的格式，请提供 JSON、CSV 或纯文本" | 1. 检查输入是否为文本格式<br>2. 确认编码为 UTF-8<br>3. 重新提交 |
| `E002` | 目标 Schema 冲突 | "目标 Schema 与源数据字段冲突，请检查字段定义" | 1. 列出冲突字段<br>2. 调整映射规则<br>3. 重新执行 |
| `E003` | 批量处理中断 | "批量处理在第 N 条记录处中断" | 1. 检查第 N 条记录格式<br>2. 修复后从断点续跑 |
| `E004` | 置信度全部过低 | "所有字段置信度均低于 0.5，数据质量不足" | 1. 检查源数据完整性<br>2. 补充数据源<br>3. 重新转换 |
| `E005` | 输出大小超限 | "输出结果超过 10MB 限制" | 1. 分批处理<br>2. 精简输出字段<br>3. 使用压缩格式 |

---

## 六、常见坑与反模式

### 6.1 反模式对照表

| 反模式 | 问题描述 | 正确做法 |
|--------|----------|----------|
| 猜测缺失值 | 源数据没有 phone 字段，却输出 "13800138000" | 输出 `[需核实:phone]` 占位符 |
| 忽略格式差异 | 日期格式 `2026/07/15` 直接输出，不转 ISO 标准 | 统一转换为 `2026-07-15T00:00:00Z` |
| 过度自信 | 所有字段置信度一律给 1.0 | 根据源数据质量差异化打分 |
| 静默丢弃 | 无法解析的字段直接删除，不告知用户 | 保留占位符并标注置信度 |
| 混淆同义词 | 将 `"price"` 和 `"cost"` 视为同一字段 | 建立明确映射表，区分语义 |

### 6.2 实战案例

**错误示范：**

输入：`"张三，电话：138xxxx，地址：北京"`

错误输出：
```json
{"name": "张三", "phone": "13800138000", "address": "北京市朝阳区"}
```

问题：电话不完整却补全了，地址不详细却编造了区级信息。

**正确示范：**

```json
{
  "data": {
    "name": "张三",
    "phone": "[需核实:phone-不完整]",
    "address": "北京"
  },
  "confidence": {
    "name": 0.98,
    "phone": 0.0,
    "address": 0.65
  }
}
```

---

## 七、渐进式披露路径

### 7.1 速查卡（30 秒上手）

1. 输入数据 → 2. 自动识别格式 → 3. 字段映射 → 4. 置信度标注 → 5. 输出 JSON

### 7.2 新手路径（5 分钟掌握）

- 阅读「能力边界速查卡」了解适用范围
- 使用「标准处理流程」中的默认 Schema 跑通一次转换
- 遇到缺失字段时，观察置信度门控如何工作

### 7.3 进阶路径（深度定制）

- 自定义目标 Schema，调整字段映射规则
- 设置置信度阈值，接入自动化流水线
- 批量处理大数据集，使用统计信息监控转换质量

### 7.4 专家路径（扩展开发）

- 扩展同义词库，提升映射准确率
- 编写自定义置信度计算逻辑
- 集成到 CI/CD 流程，实现数据质量门禁

---

## 八、参数参考表

| 参数名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `input_format` | string | `auto` | 输入格式，可选 `json`/`csv`/`text`/`auto` |
| `schema` | object | 默认 Schema | 目标字段定义 |
| `confidence_threshold` | number | `0.6` | 低于此值的字段标记为需复核 |
| `batch_size` | number | `100` | 批量处理时每批记录数 |
| `output_format` | string | `json` | 输出格式，目前仅支持 JSON |
| `include_summary` | boolean | `true` | 是否在批量输出末尾附加统计信息 |

---

## 九、用户协议

<!-- user-agreement-injected -->

**使用本 Skill 即表示您同意以下条款：**

1. **责任承担**：使用者自行承担因使用本 Skill 产生的全部责任。本 Skill 提供的转换结果仅供参考，不构成任何形式的保证或承诺。

2. **数据安全**：使用者应对输入数据的合法性和敏感性负责。本 Skill 不存储、不传输任何用户数据，所有处理均在本地完成。

3. **禁止反向工程**：使用者不得对本 Skill 进行反向工程、反编译、破解或试图提取底层算法。

4. **合规使用**：使用者应确保使用本 Skill 的行为符合当地法律法规及所在组织的政策要求。

5. **免责声明**：本 Skill 由 AI 辅助生成，可能存在未知缺陷或局限。使用者应结合自身判断使用输出结果，并在关键场景中进行人工复核。

---

## 十、许可证（License）

<!-- professional-license-embedded -->

**MIT License**

Copyright (c) 2026 原创作者（自持版权）

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

*本 Skill 文档由 AI 辅助生成，旨在提供数据转换与结构化输出的标准化操作指南。使用前请仔细阅读「用户协议」章节，并确认您的使用场景符合相关要求。*
