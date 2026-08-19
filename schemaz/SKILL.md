---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: schemaz
name: schemaz
displayName: 数据整形 结构转换 字段映射
description: 将任意来源数据按约定规则转换为结构化结果，支持批量与自定义格式。
version: 1.0.1
rules_version: cpr-20260819-n551
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/schemaz
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: schema-craft
agent_created: true
trigger_words: ["schemaz", "数据整形", "结构转换", "字段映射", "schema转换", "数据标准化"]
---

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->


> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# schemaz 技能文档

## 一、能力边界速查卡

### 能做（核心能力清单）

| 序号 | 能力项 | 说明 | 典型场景 |
|------|--------|------|----------|
| 1 | 数据→结构化结果 | 将用户提供的原始数据（文本、表格、URL内容）解析为规范结构 | 日志转JSON、CSV转对象数组 |
| 2 | 关键信息识别与保留 | 自动提取输入中的核心字段，丢弃噪声信息 | 从非结构化文本中抽取ID、时间、状态 |
| 3 | 约定格式输出 | 按用户指定或系统默认的模板生成输出 | 生成统一接口报文、数据导入模板 |
| 4 | 置信度标注 | 对自动推断的字段值标注可信程度 | 模糊匹配的字段标注"需人工复核" |
| 5 | 批量处理与自定义格式 | 支持多文件/多记录批量转换，允许用户自定义输出模板 | 批量清洗历史数据、多格式导出 |

### 不能做（明确边界）

| 序号 | 限制项 | 说明 |
|------|--------|------|
| 1 | 不执行数据语义理解 | 无法判断字段的业务含义是否正确，仅做结构转换 |
| 2 | 不处理加密/压缩格式 | 输入需为明文可读格式（UTF-8文本、JSON、CSV、XML） |
| 3 | 不保证数据质量 | 输入中的错误值、缺失值会原样保留或标记，不做自动修复 |
| 4 | 不提供实时流处理 | 仅支持批处理模式，不支持持续监听数据源 |
| 5 | 不生成业务决策 | 输出仅为结构化数据，不包含任何建议或结论 |

### 适用对象

- 需要将异构数据统一为固定格式的开发人员
- 需要批量整理数据文件的数据分析师
- 需要将外部数据导入内部系统的运维工程师
- 需要快速预览数据结构的产品经理

---

## 二、触发方式

### 触发词

- 主触发词：`schemaz`
- 同义场景词：`数据整形`、`结构转换`、`字段映射`、`schema转换`、`数据标准化`

### 场景映射表

| 用户说（大白话） | 实际触发动作 | 预期输出 |
|------------------|--------------|----------|
| "帮我把这个CSV转成JSON格式" | 解析CSV → 按默认映射转JSON | JSON文件 + 转换报告 |
| "这批日志文件需要统一字段名" | 识别日志模式 → 字段重命名 → 输出统一结构 | 标准化后的日志文件 |
| "把接口返回的数据整理成表格" | 解析嵌套JSON → 扁平化 → 输出CSV | CSV文件 + 字段说明 |
| "这个URL里的数据帮我抓下来整理" | 获取URL内容 → 解析 → 结构化输出 | 结构化数据文件 |
| "按我给的模板格式输出" | 读取用户模板 → 按模板映射字段 → 输出 | 符合模板的文件 |

---

## 三、标准处理流程

### 前置条件

| 条件项 | 要求 | 检查方式 |
|--------|------|----------|
| 输入文件 | 位于当前工作目录，命名不含空格和特殊字符 | `ls -la` 确认文件存在 |
| 输入格式 | UTF-8编码，单文件不超过10MB | `file` 命令检查编码 |
| 输出目录 | 当前目录有写权限 | `touch .write_test` 验证 |
| 模板文件（可选） | 如使用自定义模板，需为JSON格式且字段名合法 | `python -m json.tool template.json` 验证 |

### 执行步骤

**步骤1：准备输入**

1. 将待处理文件放入当前工作目录
2. 确认文件命名符合 `[前缀]_[日期].[扩展名]` 规范（如 `user_data_20260819.csv`）
3. 如有多文件批量处理，确保命名前缀一致

**步骤2：单样本试运行**

```bash
# 使用单个文件测试转换效果
schemaz --input sample.csv --output sample_output.json --verbose
```

1. 检查输出字段是否完整
2. 核对字段类型是否正确（字符串/数字/布尔）
3. 确认置信度标注是否合理

**步骤3：批量执行**

```bash
# 对目录下所有匹配文件执行转换
schemaz --input-dir ./data/ --pattern "*.csv" --output-dir ./output/ --batch
```

1. 执行前自动创建输出目录备份
2. 每个文件独立处理，互不影响
3. 生成批次处理报告（成功/失败清单）

**步骤4：校验结果**

1. 随机抽取10%的输出文件进行人工核对
2. 比对关键字段（ID、时间戳、状态值）与源数据一致性
3. 检查置信度低于0.8的字段是否需要人工修正

### 输出规范

| 输出项 | 格式 | 说明 |
|--------|------|------|
| 结构化数据 | JSON/CSV/XML（默认JSON） | 字段名遵循snake_case命名 |
| 转换报告 | Markdown表格 | 包含：处理文件数、成功数、失败数、平均置信度 |
| 错误日志 | 文本文件 | 记录每个失败文件的错误码和原因 |

---

## 四、置信度门控机制

### 置信度等级定义

| 等级 | 分值范围 | 含义 | 输出标记 |
|------|----------|------|----------|
| 高 | 0.9-1.0 | 字段值直接从源数据提取，无歧义 | 无标记 |
| 中 | 0.7-0.89 | 字段值经过格式转换或类型推断 | `[置信度:0.85]` |
| 低 | 0.5-0.69 | 字段值来自模糊匹配或默认值填充 | `[需核实:字段名]` |
| 不可用 | <0.5 | 无法确定字段值 | `[需核实:字段名]` + 置空 |

### 信息不足时的处理规则

1. **缺失必填字段**：输出 `[需核实:字段名]` 占位符，不编造数据
2. **类型不匹配**：尝试自动转换，失败则标记为字符串并降置信度
3. **枚举值超出范围**：保留原值，标注 `[需核实:枚举值]`
4. **日期格式异常**：尝试解析常见格式，失败则标记 `[需核实:日期]`

### 置信度调整规则

| 场景 | 调整幅度 | 示例 |
|------|----------|------|
| 字段名完全匹配 | +0.1 | 源字段`user_name` → 目标字段`user_name` |
| 字段名模糊匹配 | -0.2 | 源字段`uname` → 目标字段`user_name` |
| 值经过正则提取 | -0.1 | 从文本中提取邮箱地址 |
| 值经过单位换算 | -0.3 | 从`kg`转换为`lb` |
| 值来自默认值 | -0.4 | 空值填充为`unknown` |

---

## 五、错误码体系

| 错误码 | 含义 | 用户提示话术 | 修正步骤 |
|--------|------|--------------|----------|
| E001 | 输入文件不存在 | "未找到指定的输入文件，请检查路径是否正确" | 1. 确认文件路径；2. 检查文件名大小写；3. 确认文件未移动 |
| E002 | 输入格式不支持 | "当前文件格式不在支持范围内（支持：CSV/JSON/XML/TXT）" | 1. 转换文件格式；2. 或使用`--force`强制解析 |
| E003 | 字段映射冲突 | "检测到多个源字段映射到同一目标字段，请指定优先级" | 1. 查看冲突报告；2. 在配置文件中指定`priority`字段 |
| E004 | 输出目录无权限 | "无法写入输出目录，请检查目录权限" | 1. 使用`chmod`修改权限；2. 或更换输出目录 |
| E005 | 模板格式错误 | "自定义模板JSON格式错误，请检查语法" | 1. 使用JSON验证工具检查；2. 确认字段名符合规范 |
| E006 | 批量处理中断 | "批量处理在第N个文件时中断，请查看错误日志" | 1. 查看`error.log`；2. 修复问题后使用`--resume`继续 |
| E007 | 置信度过低 | "输出结果置信度低于阈值（0.5），请人工复核" | 1. 检查源数据质量；2. 调整映射规则；3. 或手动修正输出 |

---

## 六、FAQ 反模式对照

### 常见坑与正确做法

| 序号 | 反模式（错误做法） | 问题 | 正确做法 |
|------|-------------------|------|----------|
| 1 | 直接对全量数据执行转换，不做样本测试 | 字段映射错误被放大，浪费大量时间 | 先单样本试运行，确认无误后再批量执行 |
| 2 | 忽略置信度标注，直接使用所有输出 | 低置信度字段包含错误值，影响下游使用 | 对置信度<0.8的字段进行人工复核 |
| 3 | 修改原始文件后再转换 | 无法追溯转换前的数据状态 | 保留原始文件备份，转换输出到独立目录 |
| 4 | 使用自定义模板但不验证模板格式 | 模板错误导致全部输出失败 | 先验证模板JSON格式，再执行转换 |
| 5 | 批量处理失败后从头开始 | 重复处理已成功的文件，浪费时间 | 使用`--resume`参数从失败点继续 |

### 反模式对照表

| 场景 | 反模式话术 | 正确话术 |
|------|-----------|----------|
| 用户要求跳过置信度检查 | "好的，直接输出全部结果" | "建议保留置信度标注，低置信度字段可能影响数据质量。如需跳过，请确认您已了解风险。" |
| 用户要求修改原始文件 | "好的，直接在原文件上修改" | "建议保留原始文件，转换结果输出到新文件，以便追溯和对比。" |
| 用户要求处理加密文件 | "尝试强制解析" | "当前不支持加密格式，请先解密后再处理。" |

---

## 七、渐进式披露阅读路径

### 速查卡（30秒上手）

```
1. 放文件 → 2. 跑样本 → 3. 查输出 → 4. 批量跑 → 5. 验结果
```

### 新手路径（首次使用）

1. 阅读「能力边界速查卡」了解工具能做什么
2. 阅读「标准处理流程」中的步骤1-2，完成首次单样本转换
3. 遇到问题时查阅「错误码体系」定位问题
4. 完成一次完整流程后，阅读「FAQ 反模式对照」避免常见坑

### 进阶路径（熟练用户）

1. 深入理解「置信度门控机制」，学会调整置信度规则
2. 掌握「批量处理」的高级参数（`--resume`、`--pattern`、`--priority`）
3. 自定义输出模板，满足特定业务格式要求
4. 结合「错误码体系」编写自动化处理脚本，实现无人值守批量转换

### 专家路径（深度定制）

1. 研究字段映射规则，编写复杂映射配置（多源字段合并、条件映射）
2. 扩展支持自定义数据源（数据库、API接口）
3. 开发后处理钩子（post-processing hooks）实现数据清洗、去重
4. 集成到CI/CD流水线，实现数据转换自动化

---

## 八、参数参考表

### 命令行参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `--input` | string | 无 | 输入文件路径 |
| `--input-dir` | string | 无 | 批量处理的输入目录 |
| `--pattern` | string | `*` | 批量处理的文件匹配模式 |
| `--output` | string | `output.json` | 输出文件路径 |
| `--output-dir` | string | `./output/` | 批量处理的输出目录 |
| `--template` | string | 无 | 自定义输出模板JSON文件 |
| `--format` | string | `json` | 输出格式（json/csv/xml） |
| `--confidence-threshold` | float | `0.5` | 置信度阈值，低于此值标记为需核实 |
| `--batch` | bool | `false` | 启用批量处理模式 |
| `--resume` | bool | `false` | 从上次失败点继续批量处理 |
| `--verbose` | bool | `false` | 输出详细日志 |
| `--selftest` | bool | `false` | 运行自检程序 |
| `--version` | bool | `false` | 显示版本信息 |

### 配置示例

```json
{
  "input_dir": "./data/",
  "pattern": "*.csv",
  "output_dir": "./output/",
  "format": "json",
  "template": "./templates/default.json",
  "confidence_threshold": 0.6,
  "mapping_rules": {
    "user_name": "username",
    "created_at": "timestamp",
    "status": "state"
  },
  "priority": ["exact_match", "fuzzy_match", "default_value"]
}
```

---

## 九、用户协议

<!-- user-agreement-injected -->

**使用须知：**

1. 本技能（schemaz）仅供学习与参考用途，使用者应自行承担使用本技能产生的一切责任。
2. 使用者应确保输入数据的合法性、合规性，不得使用本技能处理违法违规数据。
3. 本技能的输出结果仅供参考，使用者应对输出结果进行独立验证和判断。
4. 禁止对本技能进行反向工程、反编译、破解或任何形式的未授权修改。
5. 使用者不得将本技能用于任何可能侵犯第三方权益的场景。
6. 本技能不提供任何明示或暗示的保证，包括但不限于适销性、特定用途适用性和非侵权性。
7. 因使用本技能产生的任何直接、间接、偶然、特殊或后果性损害，技能作者不承担任何责任。
8. 使用者应遵守所在地法律法规，并对其使用行为负全部责任。

---

## 十、许可证（License）

<!-- professional-license-embedded -->

### MIT License

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

## 附：自检命令

```bash
# 运行自检程序，验证技能功能完整性
schemaz --selftest

# 查看版本信息
schemaz --version
```

自检程序将验证：
1. 核心转换功能是否正常
2. 置信度标注是否正确
3. 错误码体系是否完整
4. 批量处理是否可用

---

*本文档由 AI 辅助生成，仅供参考。使用前请阅读相关文档并验证功能适配性。*
