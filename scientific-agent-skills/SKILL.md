---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: scientific-agent-skills
name: scientific-agent-skills
displayName: 科研数据解析 结构化转换 科学分析
description: 将科研数据、文件或URL转化为结构化结果，辅助科学分析。
version: 1.0.2
rules_version: cpr-20260819-n551
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/scientific-agent-skills
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: DataForge Lab
agent_created: true
trigger_words: ["scientific agent skills", "科研数据处理", "科学数据解析", "结构化输出", "数据转换", "实验数据整理", "文献信息抽取"]
---

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->


> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# 科研数据解析与结构化转换 Skill 文档

## 一、能力边界速查卡

### 1.1 能做什么

| 能力项 | 说明 | 示例 |
|--------|------|------|
| 文件解析 | 从 CSV、TXT、Excel、JSON 等常见格式中提取数据 | 读取实验记录 CSV，提取时间、温度、浓度列 |
| URL 内容抓取 | 从公开网页或 API 端点获取数据并结构化 | 抓取公开数据集页面，提取表格内容 |
| 字段映射 | 将非标准字段名映射为统一 schema | 将 "Temp"、"温度" 统一映射为 `temperature` |
| 数据清洗 | 去除空行、重复项，标记异常值 | 删除全空行，对超出 3σ 的值打标 |
| 结构化输出 | 生成统一的 JSON / Markdown 表格 / CSV 结果 | 输出 `results.json` 及摘要报告 |

### 1.2 不能做什么

| 限制项 | 说明 |
|--------|------|
| 不做统计分析 | 不计算 p 值、不拟合模型，仅做格式转换与字段提取 |
| 不处理图像/PDF 扫描件 | 若数据在图片中，需先经 OCR 转成文本 |
| 不访问付费/私有数据库 | 仅处理用户提供的文件或公开可访问的 URL |
| 不推断缺失值 | 缺失字段输出 `[需核实:字段名]`，不做猜测填充 |
| 不保证数据准确性 | 仅按规则转换，源数据错误会原样保留 |

### 1.3 适用对象

- 科研人员：整理实验记录、批量转换数据格式
- 数据分析师：将异构数据源统一为分析前格式
- 文献管理者：从网页或文本中抽取结构化元数据

---

## 二、触发方式与场景映射

### 2.1 触发词

- 主触发词：`scientific agent skills`、`科研数据处理`、`科学数据解析`
- 辅助触发词：`结构化输出`、`数据转换`、`实验数据整理`、`文献信息抽取`

### 2.2 场景映射表

| 用户说（大白话） | 实际触发动作 |
|------------------|--------------|
| "帮我把这批实验数据整理成表格" | 解析文件 → 字段映射 → 输出 CSV/JSON |
| "这个网页上的数据能提取出来吗" | 抓取 URL → 解析 HTML 表格 → 结构化输出 |
| "我的数据列名不统一，能统一吗" | 字段映射 + 重命名 → 输出统一 schema |
| "把这几份数据合并成一个文件" | 多文件解析 → 按主键合并 → 输出合并结果 |

---

## 三、标准执行流程

### 3.1 前置条件

| 条件 | 要求 |
|------|------|
| 文件格式 | 支持 .csv, .txt, .xlsx, .json, .tsv |
| 文件位置 | 所有待处理文件放在同一目录下，路径中不含空格 |
| 命名规范 | 建议使用 `样本名_日期.扩展名` 格式，便于追溯 |
| URL 访问 | 目标 URL 需为公开可访问，无登录墙 |

### 3.2 执行步骤

#### 步骤 1：输入确认

- 列出目录下所有待处理文件，确认格式与数量。
- 若输入为 URL，确认可访问性（返回 200 状态码）。

#### 步骤 2：单样本试运行

- 选取 1 个文件或 1 个 URL 作为样本。
- 执行解析，输出字段映射表与样例数据。
- 核对输出字段是否完整、类型是否正确。

**字段映射表示例：**

| 源字段 | 目标字段 | 类型 | 备注 |
|--------|----------|------|------|
| Temp | temperature | float | 单位：°C |
| Time | timestamp | datetime | 格式：ISO 8601 |
| Conc | concentration | float | 单位：mol/L |

#### 步骤 3：批量执行

- 确认样本无误后，对全量数据执行相同流程。
- 每个文件生成独立输出文件，命名规则：`原文件名_processed.json`。
- 原始文件不做任何修改，仅读取。

#### 步骤 4：结果校验

- 随机抽取 10% 输出条目，与源数据逐字段比对。
- 检查字段数量、类型、边界值（如最大值、最小值）。
- 校验通过后，生成汇总报告 `summary_report.md`。

### 3.3 输出规范

**输出目录结构：**

```
output/
├── processed/
│   ├── sample1_processed.json
│   └── sample2_processed.json
├── summary_report.md
└── field_mapping.json
```

**JSON 输出格式：**

```json
{
  "source_file": "sample1.csv",
  "processed_at": "2026-08-19T10:30:00Z",
  "record_count": 152,
  "fields": ["timestamp", "temperature", "concentration"],
  "data": [
    {
      "timestamp": "2026-08-01T09:00:00",
      "temperature": 25.3,
      "concentration": 0.12
    }
  ],
  "warnings": ["record 47: temperature out of expected range"]
}
```

---

## 四、置信度门控机制

### 4.1 占位符规则

当遇到以下情况时，输出 `[需核实:字段名]` 占位符，**不进行猜测填充**：

| 场景 | 处理方式 |
|------|----------|
| 字段缺失 | 输出 `[需核实:temperature]` |
| 格式无法解析 | 输出 `[需核实:timestamp]`，并在 warnings 中注明 |
| 值超出合理范围 | 保留原值，同时输出 `[需核实:temperature]` 标记 |
| 单位不明确 | 输出 `[需核实:unit]`，不假设默认单位 |

### 4.2 置信度等级

| 等级 | 说明 | 输出方式 |
|------|------|----------|
| 高（≥95% 字段匹配） | 直接输出，无标记 | 正常输出 |
| 中（80-94% 字段匹配） | 输出占位符，并在 summary 中列出 | 带 `[需核实]` 标记 |
| 低（<80% 字段匹配） | 停止处理，要求用户确认映射 | 输出错误码 `E1003` |

---

## 五、错误码体系

| 错误码 | 错误描述 | 提示话术 | 修正步骤 |
|--------|----------|----------|----------|
| E1001 | 文件不存在 | "未找到指定文件，请检查路径与文件名" | 1. 确认文件在指定目录；2. 检查文件名拼写；3. 重新执行 |
| E1002 | 文件格式不支持 | "当前格式不支持，请转换为 CSV/JSON/TXT" | 1. 用 Excel 另存为 CSV；2. 重新执行 |
| E1003 | 字段映射失败 | "字段匹配率低于 80%，请检查源文件列名" | 1. 查看 field_mapping.json；2. 手动补充映射；3. 重新执行 |
| E1004 | URL 无法访问 | "URL 返回非 200 状态码，请确认链接有效" | 1. 检查 URL 拼写；2. 确认无登录墙；3. 更换公开链接 |
| E1005 | 输出写入失败 | "无法写入输出文件，请检查磁盘空间与权限" | 1. 清理磁盘空间；2. 修改目录权限；3. 重新执行 |
| E1006 | 数据量超限 | "单文件超过 10 万行，请拆分后处理" | 1. 按时间或样本拆分；2. 分批执行 |

---

## 六、FAQ 与反模式对照

### 6.1 常见坑

| 坑 | 反模式（错误做法） | 正确做法 |
|----|-------------------|----------|
| 忽略单位 | 直接拼接不同单位的数值 | 先确认单位，统一换算后再输出 |
| 覆盖原始文件 | 直接修改源 CSV | 只读源文件，输出到独立目录 |
| 猜测缺失值 | 用平均值填充空值 | 输出 `[需核实]` 占位符 |
| 忽略异常值 | 直接删除超出范围的数据 | 保留并标记，在 warnings 中说明 |
| 一次性处理全部 | 不试运行直接跑全量 | 先单样本试运行，确认后再批量 |

### 6.2 反模式对照表

| 反模式 | 问题 | 替代方案 |
|--------|------|----------|
| "这个数据明显是温度，直接填 25" | 猜测值可能错误 | 输出 `[需核实:temperature]` |
| "把空值都删掉" | 丢失有效信息 | 保留行，空值打标 |
| "所有文件一起处理" | 错误扩散 | 先试运行 1 个，再批量 |
| "这个 URL 打不开，换一个类似的" | 数据源不一致 | 停止处理，要求用户提供正确 URL |

---

## 七、渐进式披露路径

### 7.1 速查卡（新手必读）

1. 把文件放到一个文件夹里
2. 先跑 1 个文件试试
3. 看输出对不对
4. 对了再跑全部
5. 抽查结果

### 7.2 进阶路径（有经验用户）

- **字段映射自定义**：编辑 `field_mapping.json`，支持正则表达式匹配列名。
- **多文件合并**：指定主键（如 `sample_id`），自动合并多个文件。
- **自定义输出格式**：支持输出为 Markdown 表格、LaTeX 表格或 JSON Lines。
- **批量 URL 抓取**：提供 URL 列表文件，批量抓取并结构化。

### 7.3 专家路径

- **规则引擎**：编写自定义转换规则（如单位换算、日期格式标准化）。
- **异常检测**：配置阈值，自动标记超出范围的值。
- **管道集成**：将本 Skill 嵌入自动化工作流，通过 CLI 调用。

---

## 八、CLI 接口参考

```bash
# 版本信息
scientific agent skills --version

# 自检模式
scientific agent skills --selftest

# 标准用法（交互式）
scientific agent skills
```

**自检模式输出示例：**

```
[PASS] 文件解析模块
[PASS] URL 抓取模块
[PASS] 字段映射模块
[PASS] 输出生成模块
[PASS] 错误处理模块
全部检查通过。
```

---

## 九、用户协议

<!-- user-agreement-injected -->

**使用本 Skill 即表示您同意以下条款：**

1. **责任承担**：使用者自行承担全部责任。本 Skill 仅提供数据处理辅助功能，不构成任何形式的数据准确性保证或专业建议。因使用本 Skill 产生的任何直接或间接损失，Skill 作者及贡献者不承担任何责任。

2. **数据安全**：使用者应确保输入数据不包含个人隐私信息、商业机密或受法律保护的数据。本 Skill 不提供数据加密传输功能，请勿处理敏感数据。

3. **禁止反向工程**：使用者不得对本 Skill 进行反向工程、反编译、破解或试图提取底层算法。不得移除、修改或遮蔽文档中的任何版权声明。

4. **合规使用**：使用者应遵守所在国家/地区的法律法规，不得将本 Skill 用于非法用途，包括但不限于数据窃取、侵犯他人知识产权等行为。

5. **免责声明**：本 Skill 按"原样"提供，不附带任何明示或暗示的保证，包括但不限于适销性、特定用途适用性和非侵权保证。

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

*文档版本：1.0.0 | 最后更新：2026-08-19 | 本 Skill 由 AI 辅助生成，仅供参考。*
