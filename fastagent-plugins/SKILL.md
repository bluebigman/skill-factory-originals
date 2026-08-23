---
slug: fastagent-plugins
name: fastagent-plugins
displayName: 数据速配 结构化转换 批量处理
description: 将任意数据、文件或URL转换为结构化结果，并标注置信度。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 灵犀工坊
agent_created: true
trigger_words: ["fastagent plugins", "插件速配", "数据转换", "结构化输出", "批量处理", "文件转结构化", "URL解析", "数据清洗"]
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# fastagent-plugins 技能文档

## 一、能力边界（一页纸速查卡）

### 1.1 能做什么

| 能力项 | 说明 | 示例 |
|--------|------|------|
| 文件转结构化 | 将 CSV、JSON、TXT、Markdown 等常见格式文件解析为统一结构 | 将 100 行 CSV 转为带字段校验的 JSON 数组 |
| URL 内容提取 | 抓取网页正文、标题、发布时间等元数据 | 提取新闻页面的标题与正文段落 |
| 批量处理 | 对同一目录下多个文件执行相同转换逻辑 | 将 50 个 TXT 日志文件统一转为 JSON |
| 置信度标注 | 对每个输出字段标注可信程度（高/中/低） | 日期字段格式不规范时标注"中"置信度 |
| 字段校验 | 检查必填字段、类型、取值范围 | 年龄字段必须为 0-120 的整数 |

### 1.2 不能做什么

| 限制项 | 说明 |
|--------|------|
| 不处理二进制大文件 | 超过 50MB 的文件需先拆分 |
| 不执行代码 | 仅做数据转换，不运行脚本或程序 |
| 不访问需登录的页面 | 仅处理公开可访问的 URL |
| 不保证字段完整性 | 源数据缺失时输出 `[需核实:字段名]` 占位 |
| 不进行语义理解 | 仅做格式转换，不判断内容含义 |

### 1.3 适用对象

- 需要将散乱数据整理为统一格式的运营人员
- 需要批量清洗日志文件的开发人员
- 需要从网页提取结构化信息的研究人员

---

## 二、触发方式

### 2.1 触发词

| 触发词 | 场景说明 |
|--------|----------|
| `fastagent plugins` | 直接调用技能主命令 |
| `插件速配` | 需要快速匹配转换插件时 |
| `数据转换` | 需要将数据从一种格式转为另一种 |
| `结构化输出` | 需要将非结构化数据转为表格/JSON |
| `批量处理` | 需要一次处理多个文件 |
| `文件转结构化` | 明确指定文件转换需求 |
| `URL解析` | 需要从网页提取内容 |

### 2.2 场景映射表

| 用户说 | 实际需求 | 技能响应 |
|--------|----------|----------|
| "帮我把这个 CSV 转成 JSON" | 格式转换 | 执行文件解析并输出 JSON |
| "这 20 个日志文件帮我整理一下" | 批量处理 | 遍历目录执行统一转换 |
| "这个网页的内容能提取出来吗" | URL 解析 | 抓取页面并提取正文 |
| "这些数据靠谱吗" | 置信度评估 | 对输出字段标注置信度 |

---

## 三、标准流程

### 3.1 前置条件

| 条件 | 要求 | 检查方式 |
|------|------|----------|
| 文件命名 | 同一批文件命名需有规律（如 `data_01.csv`） | 执行 `ls` 查看 |
| 文件格式 | 支持 CSV/JSON/TXT/MD，编码为 UTF-8 | 执行 `file` 命令 |
| 文件大小 | 单个文件 ≤ 50MB | 执行 `du -h` |
| 目录结构 | 待处理文件需在同一目录下 | 确认路径 |

### 3.2 执行步骤

**步骤 1：准备输入**

```bash
# 将待处理文件放入同一目录
mkdir -p ./input_data
cp /path/to/files/* ./input_data/

# 确认命名规范
ls -la ./input_data/
```

**步骤 2：试运行（单样本）**

```bash
# 选择第一个文件作为样本
fastagent plugins --input ./input_data/data_01.csv --sample

# 核对输出字段与格式
# 检查：字段名是否完整、类型是否正确、置信度是否合理
```

**步骤 3：批量执行**

```bash
# 确认无误后执行全量转换
fastagent plugins --input ./input_data/ --output ./output_data/

# 保留原始文件备份
cp -r ./input_data ./backup_input_data/
```

**步骤 4：校验结果**

```bash
# 抽查输出条目（建议抽取 10%）
fastagent plugins --verify ./output_data/

# 核对关键字段与源数据一致性
# 重点检查：ID 字段、日期字段、金额字段
```

### 3.3 输出规范

| 输出项 | 格式 | 示例 |
|--------|------|------|
| 结构化数据 | JSON 数组 | `[{"id": 1, "name": "张三"}]` |
| 置信度 | 每个字段附带 `confidence` 属性 | `{"id": 1, "confidence": "high"}` |
| 处理报告 | Markdown 表格 | 见下方示例 |

**处理报告示例：**

```markdown
| 文件 | 记录数 | 成功 | 失败 | 平均置信度 |
|------|--------|------|------|------------|
| data_01.csv | 100 | 98 | 2 | 0.92 |
| data_02.csv | 150 | 150 | 0 | 0.95 |
```

---

## 四、置信度门控

### 4.1 置信度等级定义

| 等级 | 阈值 | 含义 | 处理方式 |
|------|------|------|----------|
| 高 | ≥ 0.90 | 字段值完整且符合预期格式 | 直接输出 |
| 中 | 0.70 - 0.89 | 字段值存在但格式不规范 | 输出并附注说明 |
| 低 | < 0.70 | 字段值缺失或无法解析 | 输出 `[需核实:字段名]` |

### 4.2 置信度判定规则

| 场景 | 判定 | 示例 |
|------|------|------|
| 必填字段为空 | 低置信度 | `[需核实:email]` |
| 日期格式不统一 | 中置信度 | `"2024/01/01"` 标注中 |
| 数值超出合理范围 | 低置信度 | 年龄为 200 时标注低 |
| 字段类型不匹配 | 低置信度 | 字符串出现在数值字段 |

### 4.3 处理原则

- **不编造**：信息不足时输出占位符，不猜测填充
- **可追溯**：每个占位符需记录原因（缺失/格式错误/超范围）
- **可恢复**：用户补充信息后可重新执行转换

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| E001 | 文件不存在 | "未找到指定文件，请检查路径" | 确认路径是否正确，执行 `ls` 查看 |
| E002 | 文件格式不支持 | "仅支持 CSV/JSON/TXT/MD 格式" | 转换文件格式后重试 |
| E003 | 文件编码错误 | "文件编码需为 UTF-8" | 使用 `iconv` 转换编码 |
| E004 | 文件超过大小限制 | "单个文件需 ≤ 50MB" | 拆分文件后重试 |
| E005 | 字段缺失 | "缺少必填字段：{字段名}" | 检查源数据，补充字段 |
| E006 | 字段类型错误 | "字段 {字段名} 类型应为 {预期类型}" | 修正源数据中的字段类型 |
| E007 | URL 无法访问 | "URL 返回 404 或超时" | 检查 URL 有效性，确认网络连通 |
| E008 | 批量处理中断 | "批量处理在第 {n} 个文件中断" | 查看错误日志，修复后从断点继续 |

---

## 六、FAQ 反模式

### 6.1 常见坑

| 坑 | 反模式 | 正确做法 |
|----|--------|----------|
| 跳过试运行 | 直接批量执行，结果全错 | 先用单样本验证格式 |
| 忽略备份 | 原文件被覆盖，无法恢复 | 执行前复制备份目录 |
| 不校验输出 | 数据错误未被发现 | 抽查 10% 输出与源数据比对 |
| 过度依赖置信度 | 低置信度数据直接丢弃 | 保留占位符，人工补充 |
| 忽略命名规范 | 文件命名混乱导致处理失败 | 统一命名规则后再执行 |

### 6.2 反模式对照表

| 反模式 | 问题 | 替代方案 |
|--------|------|----------|
| "直接跑吧，应该没问题" | 未验证格式，批量失败 | 先跑单样本 |
| "这个字段不重要，跳过" | 关键字段缺失影响下游 | 输出占位符并记录 |
| "置信度低就删掉" | 数据丢失不可恢复 | 保留占位符待补充 |
| "一次处理所有文件" | 大文件超时或内存溢出 | 分批处理，每批 ≤ 20 个 |

---

## 七、渐进式披露

### 7.1 速查卡（30 秒上手）

```
1. 放文件 → 2. 跑样本 → 3. 批量跑 → 4. 查结果
```

### 7.2 新手路径（首次使用）

1. 阅读「能力边界」了解适用范围
2. 按「标准流程」步骤 1-2 完成单样本测试
3. 确认输出格式符合预期后，执行步骤 3-4
4. 遇到问题查阅「错误码体系」

### 7.3 进阶路径（熟练用户）

1. 自定义字段映射规则（修改配置文件）
2. 设置置信度阈值（默认 0.7，可调整）
3. 编写后处理脚本（如自动清洗占位符）
4. 集成到 CI/CD 流水线（定时批量处理）

---

## 八、参数参考表

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `--input` | string | 无 | 输入文件或目录路径 |
| `--output` | string | `./output` | 输出目录路径 |
| `--sample` | boolean | false | 单样本试运行模式 |
| `--verify` | boolean | false | 校验模式，抽查输出 |
| `--confidence-threshold` | float | 0.7 | 置信度阈值 |
| `--batch-size` | int | 20 | 每批处理文件数 |
| `--selftest` | boolean | false | 运行自检 |
| `--version` | boolean | false | 显示版本号 |

---

## 九、用户协议

<!-- user-agreement-injected -->

**使用前请仔细阅读以下条款：**

1. **责任承担**：使用者自行承担使用本 Skill 产生的全部责任。包括但不限于数据准确性、处理结果可靠性、以及因使用本 Skill 导致的任何直接或间接损失。

2. **禁止反向工程**：未经授权，不得对本 Skill 进行反向工程、反编译、破解或试图提取源代码。

3. **数据安全**：使用者需自行确保输入数据的合法性与安全性。本 Skill 不承担数据泄露或数据损坏的责任。

4. **合规使用**：使用者需遵守所在地法律法规，不得将本 Skill 用于任何非法用途。

5. **免责声明**：本 Skill 按"现状"提供，不附带任何明示或暗示的保证。

---

## 十、许可证（License）

<!-- professional-license-embedded -->

**MIT License**

Copyright (c) 2024 灵犀工坊

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

*本文档由 AI 辅助生成，仅供参考。使用前请阅读相关文档并自行验证功能。*
