---
slug: invoice-parser
name: -parser
displayName: 采购票据 字段抽取 对账归档
description: 从采购单据中抽取结构化字段，辅助对账与归档。
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
trigger_words: ["识别", "票据解析", "采购单提取", "-parser", "单据结构化", "发票字段抽取"]
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# 采购票据解析 Skill 文档

## 一、能力边界速查卡

### 1.1 能做与不能做

| 维度 | 能做 | 不能做 |
|------|------|--------|
| 输入格式 | 标准 PDF、PNG、JPG 格式的采购订单、入库单、发票 | 手写体模糊票据、非标准版式、加密文件 |
| 处理规模 | 单文件或批量（建议单批 ≤ 500 份） | 超过 500 份需分批执行 |
| 字段抽取 | 供应商名称、采购日期、物料编码、数量、单价、含税总价 | 非结构化备注、合同条款语义理解 |
| 输出能力 | CSV / JSON 结构化输出、失败清单 | 直接写入财务系统（需二次对接） |
| 校验能力 | 关键字段与源文件一致性抽查 | 自动纠错（仅标记不一致） |

### 1.2 适用对象

- **适用**：标准版式采购单据、打印清晰的票据、统一命名规范的批量文件
- **不适用**：扫描件严重倾斜、光照不均、表格线断裂的图片

---

## 二、触发方式与场景映射

| 触发词 | 实际场景 | 预期动作 |
|--------|----------|----------|
| 识别 | "帮我识别这批采购单" | 启动解析流程 |
| 票据解析 | "把发票信息提取出来" | 执行字段抽取 |
| 采购单提取 | "从采购单里抓取关键字段" | 结构化输出 |
| -parser | 命令行直接调用 | 执行完整流程 |
| 单据结构化 | "把这些单据整理成表格" | 批量转换输出 |

---

## 三、标准执行流程

### 3.1 前置条件

| 检查项 | 要求 | 验证方式 |
|--------|------|----------|
| 文件格式 | PDF / PNG / JPG | 文件扩展名检查 |
| 命名规范 | 统一前缀 + 序号（如 `PO_202501_001.pdf`） | 正则匹配 `^[A-Z]+_\d{6}_\d{3}` |
| 目录结构 | 输入文件与输出目录分离 | 确认 `input/` 与 `output/` 存在 |
| 原始备份 | 处理前复制到 `backup/` 目录 | 文件数量比对 |

### 3.2 执行步骤

1. **环境准备**
   - 创建 `input/`、`output/`、`backup/` 三个目录
   - 将待处理文件放入 `input/`，确认命名符合规范

2. **单样本试运行**
   ```bash
   -parser --file input/PO_202501_001.pdf --output output/sample_result.json
   ```
   - 检查输出 JSON 中字段是否完整
   - 核对供应商名称、金额等关键字段与源文件一致

3. **批量执行**
   ```bash
   -parser --dir input/ --output output/ --format csv
   ```
   - 执行前确认 `backup/` 已有原始文件副本
   - 记录开始时间与文件总数

4. **结果校验**
   - 随机抽取 5% 输出条目，人工比对源文件
   - 核对字段：供应商名称、采购日期、含税总价
   - 检查失败清单 `output/failed_list.csv`，确认失败原因分类

### 3.3 输出规范

| 输出项 | 格式 | 说明 |
|--------|------|------|
| 成功结果 | CSV / JSON | 每条记录含 `file_name`、`extract_time`、各字段值 |
| 失败清单 | CSV | 含 `file_name`、`error_code`、`error_message` |
| 汇总报告 | Markdown | 处理总数、成功率、失败分布 |

---

## 四、置信度门控

当以下情况出现时，输出字段值替换为 `[需核实:字段名]` 占位符，**禁止编造**：

| 场景 | 处理方式 |
|------|----------|
| 字段区域模糊不清 | 输出 `[需核实:供应商名称]` |
| 数字位数异常（如单价 10000 元但数量 0.5） | 输出 `[需核实:单价]`，并在报告中标记 |
| 日期格式无法识别 | 输出 `[需核实:采购日期]` |
| 表格跨页断裂 | 输出 `[需核实:物料编码]`，提示人工补录 |

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| `E001` | 文件格式不支持 | "文件格式不支持，请转换为 PDF/PNG/JPG" | 转换格式后重试 |
| `E002` | 文件命名不规范 | "文件名不符合 `前缀_日期_序号` 规范" | 重命名后重试 |
| `E003` | 字段提取失败 | "关键字段缺失，请检查票据清晰度" | 重新扫描或人工录入 |
| `E004` | 批量执行中断 | "处理中断于第 N 个文件，已保存进度" | 查看 `output/checkpoint.json` 续跑 |
| `E005` | 输出目录不可写 | "输出目录权限不足" | 修改目录权限或更换路径 |

---

## 六、FAQ 与反模式对照

| 常见坑 | 反模式（错误做法） | 正确做法 |
|--------|-------------------|----------|
| 文件命名混乱 | 直接批量执行，依赖自动识别 | 先统一命名规范，再执行 |
| 跳过试运行 | 直接全量处理 | 必须先用单样本验证输出 |
| 忽略备份 | 处理完才发现源文件被覆盖 | 执行前强制备份到 `backup/` |
| 不校验结果 | 直接信任输出数据 | 至少抽查 5% 条目 |
| 字段缺失时编造 | 用默认值填充缺失字段 | 使用 `[需核实:字段]` 占位 |

---

## 七、渐进式披露路径

### 7.1 新手速查（5 分钟上手）

1. 把文件放入 `input/`，命名改为 `PO_日期_序号.pdf`
2. 运行单样本命令，查看输出
3. 确认无误后批量执行
4. 查看 `output/` 下的结果与失败清单

### 7.2 进阶使用（深入调优）

- **自定义字段映射**：编辑 `config/field_map.json`，调整字段抽取规则
- **批量断点续跑**：利用 `checkpoint.json` 实现中断恢复
- **异常策略配置**：在 `config/error_policy.json` 中设置错误处理策略（跳过/终止）

---

## 八、用户协议

<!-- user-agreement-injected -->

使用本 Skill 即表示您同意以下条款：

1. **责任承担**：使用者自行承担因使用本 Skill 产生的全部责任。包括但不限于数据准确性、合规性及业务决策后果。
2. **禁止反向工程**：不得对本 Skill 进行反向工程、反编译、破解或试图提取源代码（除非适用法律允许）。
3. **无担保声明**：本 Skill 按"现状"提供，不附带任何明示或暗示的担保。
4. **数据安全**：使用者需自行确保处理数据的合法性与安全性，本 Skill 不承担数据泄露责任。

---

## 九、许可证（License）

<!-- professional-license-embedded -->

MIT License

Copyright (c) 2025 数据工坊

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
