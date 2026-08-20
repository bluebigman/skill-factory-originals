---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: rubinius
name: rubinius
displayName: 数据解析 结构化提取 格式转换
description: 将数据、文件或URL解析为结构化结果，保留关键信息并标注置信度。
version: 1.0.3
rules_version: cpr-20260820-n601
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/rubinius
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: "LuminaWorks"
agent_created: true
trigger_words: ["数据解析", "结构化提取", "格式转换", "信息抽取", "数据清洗", "字段映射", "置信度标注"]
---

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->


> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# rubinius — 数据解析与结构化提取 Skill

## 一、能力边界（一页纸速查卡）

### 能做什么

| 能力项 | 说明 | 示例 |
|--------|------|------|
| 文件解析 | 从 CSV、JSON、TXT、日志等文本类文件中提取字段 | 将非标准 CSV 转为规范 JSON |
| URL 抓取解析 | 从网页 URL 中提取正文关键信息 | 从新闻页提取标题、时间、正文摘要 |
| 字段映射 | 将源数据字段名映射为目标字段名 | `user_name` → `username` |
| 置信度标注 | 对每个输出字段标注可信程度（0~1） | 缺失值标注 `confidence: 0.3` |
| 批量处理 | 多文件顺序或并行处理 | 一次处理 100 个日志文件 |
| 结果校验 | 抽样比对源数据与输出结果 | 随机抽 10% 条目人工核对 |

### 不能做什么

| 限制项 | 说明 |
|--------|------|
| 非文本文件 | 不支持图片、音频、视频等二进制文件解析 |
| 复杂语义理解 | 不进行情感分析、意图识别、实体关系抽取 |
| 数据修复 | 不自动补全缺失值，仅标注低置信度 |
| 实时流处理 | 不支持持续监听数据流，仅处理静态输入 |
| 跨语言翻译 | 不进行任何语言翻译 |

### 适用对象

- 需要将杂乱文本转为结构化数据的开发者
- 需要批量处理日志/导出文件的运维人员
- 需要从网页提取信息的数据分析人员

---

## 二、触发方式

### 触发词

直接使用以下任一词汇即可激活本 Skill：

- 数据解析
- 结构化提取
- 格式转换
- 信息抽取
- 数据清洗
- 字段映射
- 置信度标注

### 场景映射表

| 你说的话（大白话） | Skill 实际做的事 |
|-------------------|-----------------|
| "帮我把这个 CSV 转成 JSON" | 解析 CSV → 映射字段 → 输出 JSON + 置信度 |
| "这个日志文件太乱了，整理一下" | 识别日志模式 → 提取关键字段 → 结构化输出 |
| "把这个网页内容提取出来" | 抓取 URL → 提取正文 → 输出结构化结果 |
| "这几个文件格式不一样，统一一下" | 多文件解析 → 统一字段映射 → 批量输出 |

---

## 三、标准流程

### 前置条件

1. 输入文件为文本格式（CSV/JSON/TXT/LOG/HTML）
2. 文件编码为 UTF-8（其他编码需先转换）
3. 若输入为 URL，需可公开访问（无需登录）

### 执行步骤

#### 步骤 1：确认输入

列出待处理文件清单，核对文件数量与命名。

```bash
# 示例：检查输入目录
$ ls -la ./input/
-rw-r--r-- 1 user user 2.3K Aug 20 10:00 data_001.csv
-rw-r--r-- 1 user user 1.8K Aug 20 10:01 data_002.csv
```

#### 步骤 2：单样本试运行

选取第一个文件，执行解析，检查输出字段是否完整、类型是否正确。

```bash
$ rubinius parse ./input/data_001.csv --output ./output/
```

检查输出 JSON：

```json
{
  "records": [
    {
      "id": "001",
      "name": "张三",
      "amount": 123.45,
      "_confidence": { "id": 1.0, "name": 0.95, "amount": 0.98 }
    }
  ]
}
```

#### 步骤 3：调整映射规则

若字段名不匹配，修改映射表 `mapping.json`：

```json
{
  "字段映射": {
    "用户ID": "id",
    "姓名": "name",
    "金额": "amount"
  },
  "类型转换": {
    "amount": "float"
  }
}
```

#### 步骤 4：批量执行

对剩余文件逐一处理，每处理完一个文件输出一行进度日志：

```bash
$ rubinius batch ./input/ --output ./output/
[1/10] data_001.csv → 完成 (0.8s)
[2/10] data_002.csv → 完成 (0.6s)
...
[10/10] data_010.csv → 完成 (0.9s)
```

#### 步骤 5：结果校验

随机抽取 10% 输出条目，与源数据人工比对关键字段。

```bash
$ rubinius validate ./output/ --sample-rate 0.1
```

#### 步骤 6：生成报告

输出 `summary.json`，包含处理文件数、成功数、失败数、平均置信度：

```json
{
  "summary": {
    "total_files": 10,
    "success": 9,
    "failed": 1,
    "avg_confidence": 0.92,
    "failed_files": ["data_007.csv"]
  }
}
```

### 输出规范

| 输出项 | 格式 | 说明 |
|--------|------|------|
| 解析结果 | JSON | 每条记录含 `_confidence` 字段 |
| 进度日志 | 文本 | 每行一个文件处理状态 |
| 汇总报告 | `summary.json` | 统计信息 |

---

## 四、置信度门控

### 置信度规则

| 置信度范围 | 含义 | 处理方式 |
|-----------|------|---------|
| 0.9 ~ 1.0 | 高置信度，字段完整且类型正确 | 正常输出 |
| 0.6 ~ 0.9 | 中置信度，字段存在但可能有格式问题 | 输出并提示 |
| 0.0 ~ 0.6 | 低置信度，字段缺失或无法解析 | 输出 `[需核实:字段名]` 占位 |

### 信息不足时的处理

当遇到无法解析的字段时，**不编造数据**，使用占位符：

```json
{
  "record": {
    "id": "001",
    "name": "[需核实:name]",
    "amount": "[需核实:amount]",
    "_confidence": { "id": 1.0, "name": 0.0, "amount": 0.0 }
  }
}
```

### 边界值处理

| 场景 | 处理方式 |
|------|---------|
| 空文件 | 输出空记录数组，置信度 0 |
| 字段值超长（>1000字符） | 截断并标注 `truncated: true` |
| 日期格式不标准 | 尝试常见格式解析，失败则标注低置信度 |
| 数字含千分位逗号 | 自动去除逗号后解析 |

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|---------|---------|
| `E001` | 文件不存在 | "找不到指定的输入文件" | 检查路径是否正确 |
| `E002` | 文件编码不支持 | "文件编码不是 UTF-8" | 使用 `iconv` 转换编码 |
| `E003` | 字段映射失败 | "源字段 'xxx' 未在映射表中找到" | 检查 `mapping.json` 添加映射 |
| `E004` | 类型转换失败 | "无法将 'xxx' 转换为数字类型" | 检查源数据格式 |
| `E005` | URL 无法访问 | "URL 返回 404 或超时" | 确认 URL 可公开访问 |
| `E006` | 输出目录不可写 | "无法写入输出目录" | 检查目录权限 |
| `E007` | 批量处理中断 | "第 N 个文件处理失败，已停止" | 查看错误日志，修复后重试 |

---

## 六、FAQ 反模式

### 常见坑 1：忽略置信度直接使用数据

**反模式**：拿到输出 JSON 后不检查 `_confidence` 字段，直接入库。

**正确做法**：先过滤低置信度记录，或对低置信度字段进行人工复核。

### 常见坑 2：映射表一次性写死

**反模式**：第一次解析就试图写全所有映射规则，结果字段名猜错。

**正确做法**：先跑单样本，看输出字段名，再迭代修改映射表。

### 常见坑 3：批量处理不设断点

**反模式**：100 个文件一次跑完，第 50 个失败导致全部重来。

**正确做法**：分批处理（每批 10 个），失败后从断点继续。

### 常见坑 4：URL 解析不设超时

**反模式**：URL 响应慢导致整个流程卡死。

**正确做法**：设置 10 秒超时，超时则标记失败并继续下一个。

### 常见坑 5：忽略类型转换

**反模式**：所有字段都当字符串处理，后续计算报错。

**正确做法**：在映射表中明确字段类型，解析时自动转换。

---

## 七、渐进式披露

### 速查卡（30 秒上手）

```
1. 放文件到 ./input/
2. 跑单样本：rubinius parse ./input/file1.csv
3. 看输出 JSON 字段
4. 修改 mapping.json（如需）
5. 跑批量：rubinius batch ./input/
6. 看 summary.json
```

### 新手路径（首次使用）

1. 阅读「能力边界」了解限制
2. 准备一个测试文件，按「标准流程」步骤 1-2 执行
3. 查看输出 JSON，确认字段与置信度
4. 如有问题，参考「错误码体系」排查

### 进阶路径（熟练使用）

1. 自定义映射规则：修改 `mapping.json` 添加新字段别名
2. 批量处理优化：使用 `--parallel` 参数并行处理多文件
3. 结果深度校验：使用 `--validate` 参数自动比对源数据与输出
4. 集成到流水线：将输出 JSON 作为下游任务的输入

---

## 八、高级用法

### 自定义映射规则

在 `mapping.json` 中添加字段别名：

```json
{
  "字段映射": {
    "用户ID": "id",
    "用户名称": "name",
    "user_id": "id",
    "user_name": "name"
  }
}
```

### 批量处理优化

使用 `--parallel` 参数并行处理多文件：

```bash
$ rubinius batch ./input/ --output ./output/ --parallel 4
```

### 结果深度校验

使用 `--validate` 参数自动比对源数据与输出：

```bash
$ rubinius validate ./output/ --sample-rate 0.1 --strict
```

### 集成到流水线

将输出 JSON 作为下游任务的输入：

```python
import json

with open("./output/summary.json") as f:
    summary = json.load(f)

if summary["summary"]["avg_confidence"] > 0.8:
    # 继续下游处理
    pass
else:
    # 触发人工复核
    pass
```

---

## 九、用户协议

<!-- user-agreement-injected -->

**使用本 Skill 即表示您同意以下条款：**

1. **责任承担**：使用者自行承担因使用本 Skill 产生的全部责任。包括但不限于数据解析结果准确性、数据泄露风险、以及因错误解析导致的决策失误。

2. **禁止反向工程**：不得对本 Skill 的底层逻辑进行反向工程、反编译、或试图提取源代码（除非获得明确书面授权）。

3. **数据合规**：使用者须确保输入数据不违反任何法律法规，不包含敏感个人信息（除非已获得合法处理授权）。

4. **无担保声明**：本 Skill 按"现状"提供，不附带任何明示或暗示的担保，包括但不限于适销性、特定用途适用性。

5. **免责范围**：在任何情况下，Skill 作者均不对因使用或无法使用本 Skill 而产生的任何间接、偶然、特殊或后果性损害承担责任。

---

## 十、许可证（License）

<!-- professional-license-embedded -->

### MIT License

Copyright (c) 2026 LuminaWorks

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
