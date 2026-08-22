---
slug: reviewday
name: reviewday
displayName: 代码审查 报告生成 批量处理
description: 将代码审查数据转为结构化报告，支持批量处理与置信度标注。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 流云工坊
agent_created: true
trigger_words: ["代码审查", "审查报告", "review report", "代码评审", "审查汇总", "代码走查", "审查纪要"]
---

> 本内容由 AI 生成，仅供学习参考 <!-- ai-generated-notice -->

# reviewday — 代码审查报告生成器

## 一、能力边界（一页纸速查卡）

### 能做什么

| 能力项 | 说明 | 输入要求 |
|--------|------|----------|
| 单文件解析 | 读取一份代码审查记录，提取关键字段 | 文本文件，编码 UTF-8 |
| 批量处理 | 同一目录下多份审查记录合并为一份报告 | 文件命名含日期或模块名 |
| 置信度标注 | 对每条审查结论标注可信程度 | 原始记录含审查人/时间/证据 |
| 汇总统计 | 按模块、严重级别、审查人维度聚合 | 至少 3 条有效记录 |
| 格式输出 | 生成 Markdown 或 CSV 格式报告 | 通过参数指定输出格式 |

### 不能做什么

- 不能自动执行代码审查，仅处理已有审查数据
- 不能识别图片、PDF 中的审查内容
- 不能修改原始审查文件，只生成新报告
- 不能对无证据的结论自动补充理由

### 适用对象

- 需要将分散的代码审查意见汇总为团队报告的技术负责人
- 需要向管理层汇报审查覆盖率的质量工程师
- 需要归档审查记录的项目助理

---

## 二、触发方式

当对话中出现以下意图时，本 Skill 被激活：

| 用户说（大白话） | 触发词命中 | 实际动作 |
|------------------|------------|----------|
| "帮我把这周的审查意见整理一下" | 代码审查、审查汇总 | 批量处理目录内文件 |
| "出一份评审报告给老大看" | 审查报告、代码评审 | 生成 Markdown 报告 |
| "review report for sprint 12" | review report | 按日期过滤并生成报告 |
| "这些审查记录怎么合并？" | 审查汇总 | 执行批量合并流程 |

---

## 三、标准流程

### 前置条件

1. 所有审查记录文件存放在**同一目录**下
2. 文件命名建议格式：`YYYYMMDD_模块名_审查人.txt`（日期或模块名至少包含一项）
3. 每个文件内至少包含：问题描述、严重级别（高/中/低）、建议

### 执行步骤

**第一步：环境准备**

```bash
# 确认目录结构
ls -la ./review_data/

# 预期输出示例
-rw-r--r-- 1 user user  2048 Jun 10 09:00 20240610_auth_zhang.txt
-rw-r--r-- 1 user user  1536 Jun 11 14:30 20240611_payment_li.txt
```

**第二步：单样本试运行**

```bash
python main.py --input ./review_data/20240610_auth_zhang.txt --output ./output/test_report.md
```

核对输出字段是否完整：问题ID、模块、严重级别、描述、建议、置信度。

**第三步：批量执行**

```bash
# 先备份原始数据
cp -r ./review_data ./backup_review_data_$(date +%Y%m%d)

# 全量处理
python main.py --input ./review_data/ --output ./output/full_report.md --format markdown
```

**第四步：输出校验**

- 抽查 3 条记录，确认与原始文件内容一致
- 检查置信度字段是否有 `[需核实:xxx]` 占位符
- 确认统计数字与文件数量匹配

**第五步：报告交付**

- 输出报告文件路径
- 附上处理文件清单
- 标注整体置信度水平

### 输出规范

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| issue_id | 字符串 | 是 | 唯一标识，格式 `MOD-001` |
| module | 字符串 | 是 | 所属模块名 |
| severity | 枚举 | 是 | high / medium / low |
| description | 文本 | 是 | 问题描述 |
| suggestion | 文本 | 否 | 改进建议 |
| confidence | 枚举 | 是 | high / medium / low / 需核实 |
| reviewer | 字符串 | 否 | 审查人 |

---

## 四、置信度门控

### 判定逻辑

| 条件 | 置信度 |
|------|--------|
| 有明确审查人 + 具体代码行号 + 可复现步骤 | high |
| 有审查人 + 问题描述，但缺少复现细节 | medium |
| 仅有一句话描述，无上下文 | low |
| 信息矛盾或缺失关键字段 | `[需核实:字段名]` |

### 处理规则

1. 当原始记录缺少审查人时，输出 `[需核实:reviewer]`
2. 当严重级别缺失时，默认标记为 `[需核实:severity]`，不猜测
3. 当描述内容相互矛盾时，保留两条记录并标注 `[需核实:conflict]`

### 示例

```text
原始记录：登录接口有 bug，建议修一下。
输出：
- issue_id: AUTH-014
- severity: [需核实:severity]
- description: 登录接口有 bug（原始描述过于简略）
- confidence: low
```

---

## 五、错误码体系

| 错误码 | 触发场景 | 提示话术 | 修正步骤 |
|--------|----------|----------|----------|
| E001 | 目录不存在 | "未找到指定目录，请检查路径" | 确认路径正确后重试 |
| E002 | 文件格式不支持 | "仅支持 .txt 和 .md 格式" | 转换格式后重试 |
| E003 | 文件内容为空 | "文件内容为空，跳过处理" | 补充内容或移除文件 |
| E004 | 缺少关键字段 | "缺少严重级别字段，已标记需核实" | 补充字段后重新处理 |
| E005 | 输出目录无权限 | "无法写入输出目录，请检查权限" | 修改权限或更换目录 |
| E006 | 批量处理中断 | "处理到第 N 个文件时中断" | 查看日志，从断点继续 |

---

## 六、FAQ 反模式

### 常见坑 1：文件命名混乱

**反模式**：所有文件都叫 `review.txt`，无法区分模块和日期。

**正确做法**：统一命名 `YYYYMMDD_模块_审查人.txt`，或至少包含日期。

### 常见坑 2：忽略置信度标注

**反模式**：把所有记录都标为 high confidence，导致报告失真。

**正确做法**：严格按第四节判定逻辑标注，信息不足就标 `[需核实]`。

### 常见坑 3：批量处理前不备份

**反模式**：直接对原目录执行批量处理，出错后无法恢复。

**正确做法**：先 `cp -r` 备份，再执行批量命令。

### 常见坑 4：输出格式选错

**反模式**：需要 CSV 给数据分析团队，却生成了 Markdown。

**正确做法**：确认下游需求，用 `--format csv` 指定格式。

### 常见坑 5：忽略错误码

**反模式**：看到 E004 错误后直接删除记录，丢失审查数据。

**正确做法**：补充缺失字段后重新处理，保留完整数据。

---

## 七、渐进式披露

### 速查卡（30 秒上手）

```bash
# 单文件处理
python main.py --input 文件路径 --output 输出路径

# 批量处理
python main.py --input 目录路径 --output 输出路径 --format markdown

# 自检
python main.py --selftest

# 版本
python main.py --version
```

### 新手路径（首次使用）

1. 阅读「一、能力边界」确认工具适用场景
2. 按「三、标准流程」第一步到第三步执行
3. 遇到问题查「五、错误码体系」

### 进阶路径（深度使用）

1. 阅读「四、置信度门控」理解判定逻辑
2. 阅读「六、FAQ 反模式」避免常见错误
3. 自定义输出格式：修改 `main.py` 中的输出模板
4. 集成 CI/CD：将批量执行命令加入流水线

---

## 八、用户协议

使用本 Skill 即表示您同意以下条款：

1. **责任承担**：使用者自行承担全部责任。因使用本 Skill 产生的任何直接或间接损失，作者不承担任何责任。
2. **禁止反向工程**：不得对本 Skill 进行反向工程、反编译、破解或试图提取源代码（除非适用法律允许）。
3. **合法使用**：不得将本 Skill 用于任何违反法律法规或侵犯他人权益的场景。
4. **修改与分发**：允许在遵守 MIT 许可证的前提下修改和分发本 Skill，但须保留原始版权声明。
5. **免责声明**：本 Skill 按"原样"提供，不附带任何明示或暗示的担保。

<!-- user-agreement-injected -->

---

## 九、许可证（License）

本 Skill 采用 MIT 许可证授权：

```
MIT License

Copyright (c) 2024 流云工坊

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

---

*本 Skill 由 AI 辅助生成，仅供参考。使用前请阅读相关文档。*
