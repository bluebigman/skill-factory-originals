---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: attendance
name: attendance
displayName: 考勤处理 排班校准 异常筛查
description: 考勤文件一站式处理，自动清洗、核验异常并生成统计报表。
version: 1.0.1
rules_version: cpr-20260809-n251
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/attendance
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 林默
agent_created: true
trigger_words: ["考勤", "打卡记录", "排班表", "出勤统计"]
---

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->


> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# 考勤处理 Skill 文档

## 一、能力边界速查卡

本 Skill 面向需要批量处理员工打卡记录、排班对照及出勤统计的行政、HR 或团队管理者。它接收原始考勤文件，输出结构化 Excel 工作簿，内含四个工作表：原始数据、清洗后数据、异常记录、统计汇总。

**能做：**

- 解析常见格式的考勤导出文件（.xlsx, .xls, .csv）
- 按预设或自定义班次时间比对打卡记录，标记迟到、早退、缺卡
- 自动剔除重复打卡、跨日打卡等噪声数据
- 生成按日、按人、按周维度的出勤统计
- 输出带格式的 Excel 文件，包含四个固定 Sheet

**不能做：**

- 无法识别图片格式的考勤截图（需先转为文本或表格）
- 不处理请假、加班审批流，仅标记异常，不判定合理性
- 不连接任何考勤机或 OA 系统，仅处理离线文件
- 不提供排班优化建议，仅做事实核对

**适用对象：** 单次处理 500 人以内、单文件不超过 10MB 的考勤记录。超出此规模建议分拆文件处理。

## 二、触发方式与场景映射

| 触发词 | 用户实际说出口的话 | 本 Skill 的行为 |
|--------|-------------------|----------------|
| 考勤 | "帮我处理一下这个月考勤" | 启动考勤处理流程，询问文件路径 |
| 打卡记录 | "这是打卡记录，帮我看看谁迟到多" | 解析文件，输出异常清单与统计 |
| 排班表 | "排班表在这里，和打卡对一下" | 读取排班配置，执行比对 |
| 出勤统计 | "月底了，要出勤统计表" | 生成统计 Sheet，含出勤率、迟到次数 |

若用户未提供文件路径，主动询问；若用户未说明班次，默认采用 9:00-18:00（午休 12:00-13:00 不计入工时）。

## 三、标准处理流程

### 前置条件

1. 用户提供可访问的文件路径（本地或相对路径）
2. 文件格式为 .xlsx / .xls / .csv
3. 文件内至少包含两列：人员标识（工号或姓名）、打卡时间（格式如 2026-08-01 08:57:23）
4. 若涉及排班比对，需额外提供排班表或确认默认班次

### 执行步骤

**步骤 1：确认输入**

- 询问或确认文件路径
- 确认排班时间（默认 9:00-18:00，可修改）
- 确认输出路径（默认与输入文件同目录，文件名追加 "_processed"）

**步骤 2：数据读取与解析**

- 读取文件，识别表头
- 标准化时间列格式（统一为 `YYYY-MM-DD HH:mm:ss`）
- 若存在多列时间（上班卡/下班卡），分别提取

**步骤 3：数据清洗**

- 删除完全重复的行（同一人同一分钟多次打卡，保留最早一条）
- 过滤明显噪声（如日期超出当月范围、时间字段为空）
- 对跨日打卡（如晚班 23:00 打卡，次日 02:00 下班）做日期归属修正

**步骤 4：排班比对与异常标记**

- 将每条打卡记录与当日班次比对
- 判定规则：
  - 迟到：上班打卡时间晚于班次开始时间 + 宽限分钟数（默认 5 分钟）
  - 早退：下班打卡时间早于班次结束时间 - 宽限分钟数
  - 缺卡：当日有排班但无任何打卡记录
  - 异常：单日打卡次数超过 4 次（可能重复或误操作）

**步骤 5：统计汇总**

- 按人员维度：出勤天数、迟到次数、早退次数、缺卡次数、出勤率（出勤天数 / 应出勤天数）
- 按日期维度：当日出勤人数、迟到人数、缺卡人数

**步骤 6：输出 Excel**

生成工作簿，包含四个 Sheet：

| Sheet 名 | 内容 |
|-----------|------|
| 原始数据 | 清洗前的完整记录，原样保留 |
| 清洗数据 | 去重、修正后的有效记录 |
| 异常记录 | 所有标记为迟到/早退/缺卡/异常的明细 |
| 统计汇总 | 人员维度与日期维度的统计表 |

输出文件命名规则：`{原文件名}_考勤处理_{日期}.xlsx`

### 输出规范

- 每个 Sheet 首行为表头，加粗并填充浅灰色背景
- 异常记录 Sheet 中，异常类型列使用红色字体标注
- 统计汇总 Sheet 中，出勤率低于 80% 的行整行标黄
- 文件编码 UTF-8，兼容 Excel 直接打开

## 四、置信度门控

当遇到以下情况，不猜测、不编造，输出 `[需核实:字段]` 占位符：

| 场景 | 处理方式 |
|------|----------|
| 打卡时间格式无法解析（如 "8:30am" 与 "08:30" 混用） | 标记 `[需核实:时间格式]`，跳过该行，不参与统计 |
| 人员姓名与工号无法对应 | 标记 `[需核实:人员标识]`，按工号独立统计 |
| 排班表缺失且用户未确认默认班次 | 标记 `[需核实:班次时间]`，仅做清洗不做比对 |
| 单日打卡超过 6 次，无法判断哪条有效 | 标记 `[需核实:重复打卡]`，保留最早与最晚各一条 |

所有占位符在输出 Excel 中会以黄色底纹标注，并在「统计汇总」Sheet 末尾附「待核实清单」。

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| E001 | 文件路径不存在 | "未找到该文件，请确认路径是否正确" | 检查路径拼写，或使用绝对路径 |
| E002 | 文件格式不支持 | "仅支持 .xlsx / .xls / .csv 格式" | 转换文件格式后重试 |
| E003 | 缺少必要列 | "未找到人员标识或打卡时间列" | 确认表头名称，或手动指定列名 |
| E004 | 时间解析失败率超 30% | "大量时间字段无法解析，请检查原始数据" | 导出时使用统一时间格式 |
| E005 | 排班表与打卡人员不匹配 | "排班表中存在打卡记录中不存在的人员" | 核对人员名单，补齐或忽略 |
| E006 | 输出路径无写入权限 | "无法写入目标目录，请更换路径" | 检查目录权限，或换用用户目录 |

## 六、FAQ 与反模式

**反模式 1：直接信任原始数据**
- 常见坑：考勤机导出的数据常含重复打卡、跨日未分割等问题，直接统计会导致出勤率虚高或虚低。
- 正确做法：先执行清洗步骤，再进入比对与统计。

**反模式 2：忽略宽限时间**
- 常见坑：将 9:00:30 的打卡直接判为迟到，引发员工争议。
- 正确做法：设置合理宽限分钟数（默认 5 分钟），并在异常记录中注明实际打卡时间与班次时间。

**反模式 3：把异常当错误**
- 常见坑：看到异常记录就认为数据有问题，试图修改原始数据。
- 正确做法：异常记录仅做标记，原始数据 Sheet 保持原样，便于追溯。

**反模式 4：排班时间一刀切**
- 常见坑：所有员工强制 9:00-18:00，忽略轮班、弹性工作制。
- 正确做法：支持按人员或按日期加载不同班次，未配置时使用默认值并标注。

**反模式 5：输出文件覆盖原文件**
- 常见坑：处理结果直接覆盖原始考勤文件，导致数据不可恢复。
- 正确做法：输出文件始终以新文件名保存，保留原始文件。

## 七、渐进式阅读路径

### 速查卡（30 秒上手）

1. 说"帮我处理考勤"
2. 提供文件路径
3. 确认班次（默认 9:00-18:00）
4. 获取输出 Excel（4 个 Sheet）

### 新手路径（首次使用）

- 阅读「能力边界速查卡」了解适用范围
- 按「标准处理流程」逐步操作，遇到问题查「错误码体系」
- 输出文件后，先看「异常记录」Sheet，再核对「统计汇总」

### 进阶路径（深度使用）

- 自定义班次：提供排班表文件，支持多班次、轮班制
- 调整宽限分钟数：在确认班次时一并说明，如"宽限 10 分钟"
- 批量处理：多个文件可依次处理，输出文件自动命名避免覆盖
- 结合「置信度门控」机制，对存疑数据主动标记，不强行修正

---

## 用户协议

使用本 Skill 即表示您理解并同意以下条款：

1. 本 Skill 仅提供数据处理辅助功能，不构成任何形式的劳动关系建议或法律意见。
2. 使用者应确保所处理的考勤数据来源合法、内容真实，并自行承担因数据错误、遗漏或误用所引发的全部责任。
3. 本 Skill 输出结果仅供内部参考，不保证满足任何特定监管或审计要求。
4. 禁止对本 Skill 进行反向工程、破解、二次分发或用于任何违法违规用途。
5. 本 Skill 不存储、上传或传输任何用户数据，所有处理均在本地完成。

<!-- user-agreement-injected -->

---

## 许可证（License）

本 Skill 采用 MIT 许可证发布。

```
MIT License

Copyright (c) 2026 林默

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
```

<!-- professional-license-embedded -->
