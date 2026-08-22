---
slug: ape
name: ape
displayName: 文本解析 实体抽取 字段映射
description: 将任意文本解析为结构化JSON，标注置信度并输出缺失字段清单。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 数据工坊
agent_created: true
trigger_words: ["ape", "解析", "结构化", "数据提取", "信息整理", "文本转JSON", "字段抽取"]
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# APE 技能手册

## 一、能力边界速查卡

### 1.1 能做什么

| 能力项 | 说明 | 示例 |
|--------|------|------|
| 实体识别 | 从文本中提取人名、地名、组织名、日期、金额等 | "张三于2024年3月1日在北京参加了会议" → 提取出人名、日期、地点 |
| 字段匹配 | 根据默认或自定义 Schema 将文本内容映射到字段 | 默认 Schema 包含 `person`、`location`、`date`、`amount` 等 |
| 置信度计算 | 为每个字段标注提取结果的可靠程度（0~1） | 明确出现的日期置信度 0.95，推断出的日期置信度 0.6 |
| 缺失字段标记 | 识别文本中未提供的信息字段 | 文本未提及金额时，`amount` 字段标记为缺失 |

### 1.2 不能做什么

| 限制项 | 说明 |
|--------|------|
| 不支持非 UTF-8 编码 | 输入文本必须是 UTF-8 编码格式 |
| 不进行语义推理 | 仅做模式匹配和规则提取，不推断隐含信息 |
| 不保证 100% 准确 | 提取结果受文本质量、歧义程度影响 |
| 不处理图片/音频 | 仅支持纯文本输入，不支持多模态数据 |
| 不自动补全缺失数据 | 缺失字段仅标记，不猜测填充 |

### 1.3 适用对象

- 需要从非结构化文本中提取结构化信息的开发者
- 需要批量处理文本数据的数据分析人员
- 需要将文本数据接入自动化流程的运维工程师
- 需要快速了解文本内容要点的业务人员

---

## 二、触发方式与场景映射

### 2.1 触发词

直接使用以下任一方式触发：

```
ape "你的文本内容"
ape --selftest
ape --version
```

### 2.2 场景映射表

| 你的需求（大白话） | 对应操作 | 推荐参数 |
|-------------------|----------|----------|
| "我想从这段文字里提取人名和日期" | 使用默认 Schema 解析 | `ape "文本"` |
| "我需要按自己的字段结构提取信息" | 自定义 Schema | `ape "文本" --schema '{"fields":["name","email"]}'` |
| "我只想要高置信度的结果" | 设置置信度阈值 | `ape "文本" --min-confidence 0.8` |
| "我要批量处理很多文本" | 脚本调用 + 结果过滤 | 结合 `suggestions` 字段处理 |
| "解析出错了怎么办" | 查看错误码 | 参考第五节错误码体系 |

---

## 三、标准执行流程

### 3.1 前置条件

- 输入文本为 UTF-8 编码
- 文本长度不超过 10,000 字符（超出部分将被截断）
- 如需自定义 Schema，请确保 JSON 格式合法

### 3.2 执行步骤

1. **初始化**：确认输入文本编码格式，检查文本长度
2. **基础解析**：运行 `ape "你的文本"`，系统自动识别实体并匹配默认 Schema
3. **查看输出**：检查 `data` 字段获取结构化结果，检查 `confidence` 字段获取置信度
4. **自定义配置**（可选）：
   - 使用 `--schema` 参数传入自定义字段结构
   - 使用 `--min-confidence` 设置置信度阈值，低于阈值的字段将被标记
5. **异常处理**：如遇错误，参考错误码体系进行修正
6. **结果应用**：将输出 JSON 接入下游流程

### 3.3 输出规范

输出为 JSON 格式，包含以下字段：

```json
{
  "data": {
    "person": "张三",
    "location": "北京",
    "date": "2024-03-01",
    "amount": null
  },
  "confidence": {
    "person": 0.95,
    "location": 0.88,
    "date": 0.97,
    "amount": 0.0
  },
  "missing_fields": ["amount"],
  "suggestions": ["文本中未提及金额信息，建议补充"]
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `data` | 对象 | 提取的结构化数据，缺失字段为 `null` |
| `confidence` | 对象 | 每个字段的置信度（0~1） |
| `missing_fields` | 数组 | 缺失字段名称列表 |
| `suggestions` | 数组 | 针对缺失字段的补充建议 |

---

## 四、置信度门控机制

### 4.1 置信度规则

| 置信度范围 | 含义 | 处理方式 |
|-----------|------|----------|
| 0.9 ~ 1.0 | 高置信度，文本中明确出现 | 直接使用 |
| 0.7 ~ 0.89 | 中置信度，模式匹配成功但存在歧义 | 建议人工复核 |
| 0.5 ~ 0.69 | 低置信度，推断得出 | 标记为 `[需核实:字段]` |
| 0 ~ 0.49 | 极低置信度，无法确认 | 标记为缺失字段 |

### 4.2 信息不足时的处理

当文本信息不足以支撑字段提取时：

1. 该字段在 `data` 中输出为 `null`
2. 该字段加入 `missing_fields` 列表
3. 在 `suggestions` 中给出补全建议
4. 输出占位符 `[需核实:字段名]` 供下游流程识别

**示例**：
```
输入："张三参加了会议"
输出：data.date = null, missing_fields = ["date"], suggestions = ["文本未提及日期，建议补充会议时间"]
```

### 4.3 禁止行为

- 严禁编造文本中不存在的信息
- 严禁对缺失字段进行猜测性填充
- 严禁在置信度低于 0.5 时输出确定值

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| `E001` | 输入为空 | "输入文本不能为空" | 检查输入参数，确保文本非空 |
| `E002` | 编码不支持 | "仅支持 UTF-8 编码" | 转换文本编码为 UTF-8 |
| `E003` | 文本超长 | "文本长度超过限制（10000字符）" | 截断文本或分段处理 |
| `E004` | Schema 格式错误 | "自定义 Schema 必须是合法 JSON" | 检查 Schema 格式，参考文档示例 |
| `E005` | 字段名冲突 | "Schema 字段名与系统保留字段冲突" | 避免使用 `data`、`confidence` 等保留字段名 |
| `E006` | 置信度阈值无效 | "min-confidence 必须在 0~1 之间" | 调整参数值到有效范围 |
| `E007` | 内部解析失败 | "解析过程中发生未知错误" | 检查文本格式，尝试简化文本后重试 |

---

## 六、FAQ 反模式对照

### 6.1 常见错误用法

| 反模式 | 问题说明 | 正确做法 |
|--------|----------|----------|
| 输入包含 HTML 标签 | 标签干扰实体识别 | 先清洗文本，去除标签后再解析 |
| 依赖单次解析结果 | 单次结果可能不完整 | 多次解析并交叉验证 |
| 忽略置信度直接使用 | 低置信度数据可能错误 | 设置 `--min-confidence` 过滤 |
| 自定义 Schema 过于复杂 | 字段过多导致匹配率下降 | 精简字段，聚焦核心信息 |
| 不处理 `suggestions` 字段 | 缺失字段无法补全 | 根据建议触发数据补全流程 |

### 6.2 最佳实践

1. **批量处理**：将 APE 输出接入 CI/CD 管道，自动处理低置信度模式
2. **自动化补全**：根据 `suggestions` 字段自动触发数据补全流程
3. **错误重试**：结合错误码实现自动化重试机制
4. **结果审计**：定期抽样检查解析结果，持续优化 Schema

---

## 七、渐进式阅读路径

### 7.1 新手快速上手（5分钟）

1. 阅读第一节「能力边界速查卡」了解 APE 能做什么
2. 查看第二节「场景映射表」找到你的使用场景
3. 运行基础命令：`ape "你的文本"`
4. 查看输出中的 `data` 和 `confidence` 字段

### 7.2 进阶使用（30分钟）

1. 学习第三节「标准执行流程」中的参数配置
2. 使用 `--schema` 自定义字段结构
3. 设置 `--min-confidence` 过滤低质量数据
4. 阅读第五节「错误码体系」处理异常情况
5. 参考第六节「FAQ 反模式对照」避免常见错误

### 7.3 高级集成（2小时+）

1. 将 APE 输出接入 CI/CD 管道
2. 编写脚本处理批量结果中的低置信度模式
3. 根据 `suggestions` 字段自动触发数据补全流程
4. 结合错误码实现自动化重试机制

---

## 八、参数速查表

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `--schema` | JSON 字符串 | 默认 Schema | 自定义字段结构 |
| `--min-confidence` | 浮点数 | 0.0 | 置信度阈值，低于此值的字段标记为需核实 |
| `--selftest` | 布尔 | false | 运行自检程序 |
| `--version` | 布尔 | false | 显示版本信息 |
| `--output-format` | 字符串 | json | 输出格式（json/csv） |

---

## 九、用户协议

<!-- user-agreement-injected -->

**使用本 Skill 即表示您同意以下条款：**

1. **责任承担**：使用者自行承担使用本 Skill 产生的全部责任。包括但不限于因解析结果不准确、数据丢失、业务决策失误等造成的任何直接或间接损失。

2. **禁止反向工程**：不得对本 Skill 进行反向工程、反编译、破解、篡改或试图提取源代码。

3. **合规使用**：使用者应确保使用本 Skill 的行为符合当地法律法规及所在组织的政策要求。

4. **无担保声明**：本 Skill 按"现状"提供，不附带任何明示或暗示的担保。

---

## 十、许可证（License）

<!-- professional-license-embedded -->

### MIT License

Copyright (c) 2024 数据工坊

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
