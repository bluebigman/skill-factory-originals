---
slug: ambition
name: ambition
displayName: 文本结构化 字段识别 置信标注
description: 将非结构化文本智能转换为带置信度标注的JSON数据，支持批量处理。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 数据炼金术士
agent_created: true
trigger_words: ["ambition", "文本转JSON", "结构化提取", "字段识别", "批量转换", "置信度标注"]

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

---

# ambition：文本结构化转换与置信度标注

## 一、能力边界速查卡

### 1.1 能做什么

| 能力项 | 说明 | 示例 |
|--------|------|------|
| 纯文本转JSON | 将非结构化文本解析为结构化JSON对象 | 一段简历文本 → `{"name":"张三","age":28}` |
| 自动字段识别 | 根据上下文语义自动识别实体与属性 | 从邮件中提取发件人、日期、主题 |
| 置信度标注 | 每个字段附带0~1的置信度分数 | `{"name":{"value":"张三","confidence":0.95}}` |
| 批量处理 | 一次输入多条记录，自动拆分并逐条转换 | 10条客户反馈 → 10个JSON对象数组 |
| 多编码容错 | 自动检测并处理UTF-8/GBK/ASCII等编码 | 乱码文本自动修复或提示 |

### 1.2 不能做什么

| 限制项 | 说明 |
|--------|------|
| 非文本输入 | 不接受PDF、图片、音频等原始格式，需先经OCR或转录 |
| 语义推理 | 不进行跨句推理或隐含信息补全，只提取显式内容 |
| 自定义Schema | 不支持用户预设输出模板，字段结构由模型自主决定 |
| 实时流处理 | 不支持流式输入，需一次性提交完整文本 |

### 1.3 适用对象

- 需要将日志、邮件、表单、报告等文本批量转为结构化数据的开发人员
- 需要快速抽取关键字段用于下游分析的数据工程师
- 需要验证文本中信息完整度的质检人员

---

## 二、触发方式与场景映射

### 2.1 触发词

- 主触发词：`ambition`
- 同义触发词：`文本转JSON`、`结构化提取`、`字段识别`、`批量转换`、`置信度标注`

### 2.2 场景映射表

| 用户说（大白话） | 实际触发行为 |
|------------------|--------------|
| "帮我把这些客户反馈整理成表格" | 调用ambition，将每条反馈转为JSON对象 |
| "这段合同的关键条款提取出来" | 调用ambition，识别条款编号、日期、金额等字段 |
| "这个CSV转成JSON，顺便标一下哪些字段不确定" | 调用ambition，输出带置信度的JSON |
| "我有100条日志，批量转一下" | 调用ambition，自动拆分并批量转换 |

---

## 三、标准执行流程

### 3.1 前置条件

| 条件 | 要求 |
|------|------|
| 输入格式 | 纯文本字符串，或UTF-8编码的文本文件 |
| 输入大小 | 单条记录≤10KB，批量≤100条/次 |
| 编码要求 | 支持UTF-8/GBK/ASCII，其他编码需先转码 |

### 3.2 执行步骤

**步骤1：输入预处理**
- 检测输入编码，若为GBK则自动转UTF-8
- 去除首尾空白字符，统一换行符为`\n`
- 若输入包含多条记录，按空行或分隔符（如`---`）拆分

**步骤2：字段识别与提取**
- 扫描文本，识别实体（人名、日期、金额、编号等）
- 根据上下文推断字段名（如"张三"→`name`，"2024-01-15"→`date`）
- 对每个字段生成候选值列表

**步骤3：置信度计算**
- 基于以下维度打分：
  - 文本匹配度（字段名与值是否语义一致）
  - 上下文一致性（值是否与周围信息矛盾）
  - 格式规范性（日期、金额等是否符合标准格式）
- 置信度范围：0.0（完全不确定）~ 1.0（高度确定）

**步骤4：JSON输出**
- 输出格式：
```json
{
  "records": [
    {
      "field_name": {
        "value": "提取的值",
        "confidence": 0.95
      }
    }
  ],
  "meta": {
    "record_count": 1,
    "encoding": "UTF-8",
    "processing_time_ms": 123
  }
}
```

### 3.3 输出规范

| 项目 | 规范 |
|------|------|
| 字段名 | 小写驼峰式（如`userName`、`orderId`） |
| 置信度 | 保留两位小数，范围0.00~1.00 |
| 空值处理 | 未识别字段不输出，不填充null |
| 批量输出 | 统一包裹在`records`数组中 |

---

## 四、置信度门控机制

### 4.1 置信度阈值

| 置信度区间 | 处理策略 |
|------------|----------|
| 0.80~1.00 | 正常输出，无需额外标注 |
| 0.50~0.79 | 输出字段，并在`meta`中标记`"needs_review": true` |
| 0.00~0.49 | 输出占位符`[需核实:字段名]`，不输出具体值 |

### 4.2 占位符规则

- 格式：`[需核实:字段名]`
- 示例：`[需核实:date]`表示日期字段无法确认
- 占位符保留在JSON的`value`字段中，`confidence`固定为0.00

### 4.3 禁止行为

- 严禁在信息不足时编造字段值
- 严禁将低置信度值强行提升至0.80以上
- 严禁忽略`[需核实]`占位符直接输出空对象

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| `E001` | 输入为空 | "输入文本不能为空，请提供至少一条记录" | 检查输入，补充文本后重试 |
| `E002` | 编码无法识别 | "无法识别输入编码，请转为UTF-8后重试" | 使用`iconv`或文本编辑器转码 |
| `E003` | 单条记录超限 | "单条记录超过10KB，请拆分后处理" | 将长文本按段落拆分 |
| `E004` | 批量条数超限 | "批量条数超过100，请分批处理" | 将输入分为多批，每批≤100条 |
| `E005` | 字段识别失败 | "未能识别任何有效字段，请检查文本内容" | 确认文本包含实体信息，避免纯数字或符号 |
| `E006` | 置信度全部过低 | "所有字段置信度均低于0.50，请检查输入质量" | 提供更清晰的文本，或人工标注关键字段 |

---

## 六、FAQ 反模式对照

### 6.1 常见坑

| 坑 | 反模式示例 | 正确做法 |
|----|------------|----------|
| 忽略置信度 | 直接使用所有字段值，不看置信度 | 对置信度<0.80的字段进行人工复核 |
| 过度依赖占位符 | 将`[需核实]`当作正常值传入下游 | 将占位符过滤或替换为默认值 |
| 批量处理不拆分 | 将1000条记录一次提交 | 分批处理，每批≤100条 |
| 忽略编码问题 | 直接处理GBK文本导致乱码 | 先转UTF-8再处理 |
| 自定义Schema | 期望输出固定字段结构 | 接受模型自主识别的字段名 |

### 6.2 反模式对照表

| 反模式 | 问题描述 | 替代方案 |
|--------|----------|----------|
| 强制字段名 | 要求输出`customer_id`而非`customerId` | 接受小驼峰命名，下游再做映射 |
| 忽略空值 | 期望所有字段都有值 | 接受缺失字段，不强行填充 |
| 单次处理超大文本 | 一次提交100KB文本 | 按段落或逻辑块拆分 |
| 不检查错误码 | 忽略`E005`继续处理 | 捕获错误码，按修正步骤处理 |

---

## 七、渐进式披露路径

### 7.1 速查卡（新手必读）

1. 输入纯文本 → 2. 调用ambition → 3. 获取带置信度的JSON → 4. 检查置信度<0.80的字段 → 5. 人工复核后使用

### 7.2 进阶路径（有经验用户）

- **批量优化**：使用`meta`中的`processing_time_ms`评估性能，对超时批次调整拆分粒度
- **置信度调优**：对特定领域（如法律文书）可自定义置信度计算规则
- **错误处理**：建立错误码映射表，将`E001`~`E006`映射到业务告警

### 7.3 专家路径（深度定制）

- 扩展字段识别规则，支持领域特定实体（如合同编号、税号）
- 集成下游Schema映射，自动将输出转换为目标结构
- 开发置信度校准模型，基于历史数据优化打分逻辑

---

## 八、用户协议

<!-- user-agreement-injected -->

**使用条款**

1. 本Skill按"原样"提供，使用者自行承担全部使用风险和责任。
2. 使用者应对使用本Skill产生的输出结果进行独立验证，不得直接用于生产环境而未加审核。
3. 禁止对本Skill进行反向工程、反编译、反汇编或试图提取源代码。
4. 本Skill不提供任何形式的明示或暗示担保，包括但不限于适销性、特定用途适用性和非侵权保证。
5. 因使用本Skill造成的任何直接、间接、附带、特殊或后果性损害，作者不承担任何责任。
6. 使用者应遵守所在国家/地区的法律法规，不得将本Skill用于任何非法用途。

---

## 九、许可证（License）

<!-- professional-license-embedded -->

**MIT License**

Copyright (c) 2024 数据炼金术士

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
