---
slug: librechat
name: librechat
displayName: 数据规整 结构化输出 格式转换
description: 将任意数据、文件或链接整理为结构化、可校验的规范输出。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 林墨
agent_created: true
trigger_words: ["librechat", "数据整理", "结构化输出", "格式转换", "信息提取", "数据规整", "字段映射"]
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# librechat — 数据规整与结构化输出 Skill

## 一、能力边界（一页纸速查卡）

### 1.1 能做什么

| 能力项 | 说明 | 示例 |
|--------|------|------|
| 数据整理 | 将散乱数据（文本、表格、日志）规整为统一结构 | 将 CSV 中的日期格式统一为 ISO 8601 |
| 结构化输出 | 将非结构化内容（如自然语言描述）映射到预定义字段 | 从一段产品描述中提取"名称/型号/价格/库存" |
| 格式转换 | 在 JSON、YAML、CSV、Markdown 表格之间互转 | 将 JSON 数组转为 Markdown 表格 |
| 信息提取 | 从长文本中抽取关键实体与属性 | 从合同中提取"甲方/乙方/金额/期限" |
| 链接解析 | 从 URL 中提取页面标题、元描述、关键字段 | 从商品链接中提取价格与规格 |

### 1.2 不能做什么

| 限制项 | 说明 |
|--------|------|
| 不做语义理解 | 不判断文本情感、意图、立场，仅做结构映射 |
| 不做数据清洗决策 | 不自动删除"疑似脏数据"，需人工确认 |
| 不做跨源合并 | 不自动关联多个文件中的同名实体（需显式指定映射规则） |
| 不做格式美化 | 不生成带样式的报告，仅输出纯结构化数据 |

### 1.3 适用对象

- 需要批量整理日志、导出报表的运维/开发人员
- 需要将调研资料转为统一模板的研究助理
- 需要从网页/文档中提取字段做入库的爬虫使用者
- 任何需要"把乱的东西摆整齐"的场景

---

## 二、触发方式

### 2.1 触发词

直接使用以下任一词汇即可激活本 Skill：

- `librechat`
- `数据整理`
- `结构化输出`
- `格式转换`
- `信息提取`
- `数据规整`
- `字段映射`

### 2.2 场景映射表

| 你说的话（大白话） | 本 Skill 实际做的事 |
|-------------------|---------------------|
| "帮我把这个 Excel 里的日期改成统一格式" | 识别日期列 → 统一为 YYYY-MM-DD → 输出新表 |
| "这段文字里有哪些关键信息？帮我列出来" | 按预设字段提取实体 → 输出 JSON |
| "把这个 JSON 转成表格给我看" | 解析 JSON → 映射为 Markdown 表格 |
| "这个网页链接里有什么数据？" | 抓取页面 → 提取标题/描述/关键字段 → 结构化输出 |
| "把这些日志里的错误码都挑出来" | 按正则规则匹配 → 输出错误码清单 |

---

## 三、标准流程

### 3.1 前置条件

| 条件 | 要求 |
|------|------|
| 输入文件 | 与 Skill 运行目录一致，命名不含空格与特殊字符 |
| 输入格式 | 支持 txt / csv / json / yaml / md / html（链接需可访问） |
| 字段定义 | 若需自定义输出结构，请提前提供字段名清单 |
| 运行环境 | 无需额外依赖，纯文本处理 |

### 3.2 执行步骤

**第一步：准备输入**

1. 将待处理文件放入当前工作目录。
2. 确认文件命名规范（如 `input_001.csv`、`raw_data.json`）。
3. 若输入为链接，确保链接可公开访问。

**第二步：试运行（单样本验证）**

1. 选取 1 条样本数据（如文件第一行、JSON 第一个对象）。
2. 执行结构化输出，检查字段名、类型、格式是否符合预期。
3. 若字段缺失或格式不符，调整映射规则后重试。

**第三步：批量执行**

1. 确认单样本输出无误后，对全量数据执行。
2. 保留原始文件备份（自动生成 `backup_<时间戳>/` 目录）。
3. 输出文件命名规则：`output_<原文件名>_<时间戳>.json`。

**第四步：校验结果**

1. 随机抽取 5% 条目（至少 3 条）核对关键字段。
2. 比对源数据与输出数据，确认无字段丢失或错位。
3. 若发现异常，定位是映射规则问题还是源数据问题，修正后重跑。

### 3.3 输出规范

| 输出项 | 规范 |
|--------|------|
| 文件格式 | JSON（默认）/ CSV / YAML（可选） |
| 编码 | UTF-8 无 BOM |
| 字段命名 | 小驼峰（如 `userName`）或下划线（如 `user_name`），保持一致 |
| 空值处理 | 缺失字段输出 `null`，不省略 |
| 时间格式 | ISO 8601（`YYYY-MM-DDTHH:mm:ssZ`） |
| 数值精度 | 保留原始精度，不做四舍五入 |

---

## 四、置信度门控

### 4.1 规则说明

当输入信息不足以确定某个字段值时，**禁止编造**。统一使用占位符：

```
[需核实:字段名]
```

### 4.2 触发场景

| 场景 | 处理方式 |
|------|----------|
| 源数据中字段缺失 | 输出 `[需核实:字段名]`，并在日志中标记 `WARN` |
| 字段值格式异常（如日期为 `2024/13/45`） | 输出 `[需核实:字段名]`，不自动修正 |
| 多个来源冲突（如同一字段两个值） | 输出 `[需核实:字段名]`，并在备注中列出所有候选值 |
| 链接无法访问 | 输出 `[需核实:链接内容]`，不猜测页面内容 |

### 4.3 示例

输入：
```
{"name": "张三", "age": "未知", "city": "北京"}
```

输出：
```json
{
  "name": "张三",
  "age": "[需核实:age]",
  "city": "北京"
}
```

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| `E001` | 输入文件不存在 | "未找到指定文件，请确认路径与文件名" | 检查文件名与路径，重新执行 |
| `E002` | 输入格式不支持 | "当前格式不在支持列表中（txt/csv/json/yaml/md/html）" | 转换格式后重试 |
| `E003` | 字段映射冲突 | "同一字段被映射到多个目标，请指定唯一映射" | 检查映射规则，去重后重试 |
| `E004` | 输出目录无写入权限 | "无法写入输出文件，请检查目录权限" | 修改目录权限或更换输出路径 |
| `E005` | 链接访问超时 | "链接无法访问，请确认网络或链接有效性" | 检查链接状态，稍后重试 |
| `E006` | 批量执行中断 | "批量执行在第 N 条中断，已保存已处理部分" | 查看日志定位中断原因，修复后从断点续跑 |

---

## 六、FAQ 反模式

### 6.1 常见坑与反模式对照

| 常见坑 | 反模式（错误做法） | 正确做法 |
|--------|-------------------|----------|
| 字段名不一致 | 直接沿用源数据字段名，不做统一 | 先定义目标字段名，再映射 |
| 日期格式混乱 | 手动逐个修改 | 用正则统一匹配，批量替换 |
| 空值被忽略 | 输出时跳过空字段 | 保留字段，输出 `null` 或 `[需核实]` |
| 批量执行不校验 | 全量跑完直接使用 | 先单样本试跑，再抽检 5% |
| 源文件被覆盖 | 直接在原文件上修改 | 保留备份，输出到新文件 |

### 6.2 反模式示例

**错误做法：**
```
输入：{"a": 1, "b": 2}
输出：{"a": 1}  // b 字段被丢弃
```

**正确做法：**
```
输入：{"a": 1, "b": 2}
输出：{"a": 1, "b": 2}  // 保留全部字段
```

---

## 七、渐进式披露

### 7.1 速查卡（30 秒上手）

1. 放文件 → 2. 跑单样本 → 3. 确认字段 → 4. 批量跑 → 5. 抽检。

### 7.2 分层次阅读路径

**新手路径（首次使用）：**

1. 阅读「能力边界」了解能做什么。
2. 按「标准流程」前三步操作。
3. 遇到问题查「错误码体系」。

**进阶路径（熟练使用）：**

1. 自定义字段映射规则（需提供字段清单）。
2. 使用 `--selftest` 验证规则正确性。
3. 批量执行后，用脚本自动比对源数据与输出数据。

---

## 八、用户协议

<!-- user-agreement-injected -->

使用本 Skill 即表示您同意以下条款：

1. **责任承担**：使用者自行承担因使用本 Skill 产生的全部责任，包括但不限于数据准确性、合规性及由此引发的任何后果。
2. **禁止反向工程**：不得对本 Skill 进行反向工程、反编译、破解或试图提取底层算法。
3. **数据安全**：使用者需自行确保输入数据的合法性与敏感性，本 Skill 不承担数据泄露风险。
4. **无担保**：本 Skill 按"现状"提供，不附带任何明示或暗示的担保。

---

## 九、许可证（License）

<!-- professional-license-embedded -->

MIT License

Copyright (c) 2024 林墨

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
