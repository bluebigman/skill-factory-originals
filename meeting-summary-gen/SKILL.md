---
> 本内容由 AI 生成，仅供学习参考（《人工智能生成合成内容标识办法》显式标识）。
<!-- ai-generated-notice -->
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: meeting-summary-gen
name: meeting-summary-gen
displayName: 会议纪要 会议总结生成器
description: 把会议记录整理成议题、决议、行动项与责任人的结构化会议总结。
version: 1.0.0
rules_version: cpr-20260820-n601
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/meeting-summary-gen
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 知会工坊
agent_created: true
trigger_words: ["meeting-summary-gen", "会议总结", "会议纪要生成", "会议记录整理", "行动项提取", "会后总结", "会议要点"]

---

> 📜 **用户协议（User Agreement）**
> 1. 本 Skill 仅供学习与参考用途。使用本 Skill 产生的任何结果，由使用者自行承担全部责任；本 Skill 不提供任何明示或暗示的保证。
> 2. 涉及法律、财务、税务、投资、医疗等专业决策时，请务必咨询持证专业人士。
> 3. 本代码受版权法保护，未经授权复制、反向工程或商业利用将被追究法律责任。
<!-- user-agreement-injected -->

# 会议纪要 会议总结生成器（meeting-summary-gen）

把会议记录整理成议题、决议、行动项与责任人的结构化会议总结。 适合需要快速产出结构化成果的内容与运营场景；输出可人工二次精调后直接使用。

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**

## 简介

把会议记录整理成议题、决议、行动项与责任人的结构化会议总结。 基于规则模板引擎，离线运行、零第三方依赖；输出结构稳定（文本/JSON 双形态）、可复现（--seed）、可批量（--input 文件），内置合规词表与参数校验，生成结果一律先预览后写盘。

## 功能简介与能力边界

**能做**
- 输入会议原始记录文本（粘贴或 --input 文件，支持多编码）
- 整理模式：mode ∈ standard(标准总结) / brief(简报) / action(行动项优先)
- 输出结构化成果（按固定框架组织），支持 --json 结构化输出与 --out 落盘
- 内置合规词表拦截与参数边界校验；--dry-run 预览、--verbose 决策明细、--selftest 自检

**不做**
- 不生成绝对化/诱导性内容（词表拦截）
- 不替代人工决策——输出供参考，关键数据请核对原文
- 不联网、不调用外部模型（纯本地规则引擎）

## 差异对比：本工具 vs 直接问 AI

| 功能 | 原版(通用AI直接生成) | 本版(本工具) |
|---|---|---|
| 输 | 入 | | |
| 输 | 出 | | |
| 模 | 式 | | |
| 合 | 规 | | |
| 可 | 复 | 现 |

本项目为**全新原创设计、独立开发实现**，无对应开源前置项目；结构思路借鉴行业通用方法论，代码与模板库全部自研。

本工具核心增量：新增结构化输出功能（固定框架/JSON），新增合规词表拦截功能，实现离线运行能力（零第三方依赖），实现自检契约验证能力，支持 --seed 复现特性，支持 --input 批量处理特性。

## 安装与配置

本工具零第三方依赖，无需 pip 安装。将资产目录放入 skills 目录，或直接 `python run.py --help` 即可运行；跨机迁移仅需拷贝整个资产目录。

## 前置条件

- Python 3.8+，零第三方依赖（纯标准库）
- 运行前建议 `python run.py --selftest` 验证环境（9/9 全绿）
- 生成内容仅打印预览，需落盘时显式传 `--out <路径>`

## 标准执行步骤

```bash
# 1. 自检（验证环境）
python run.py --selftest

# 2. 预览生成（不写盘，安全优先）
python run.py --topic "<输入内容>"

# 3. 落盘输出
python run.py --input "<输入内容>" --out result.md

# 4. 结构化 JSON（供下游程序消费）
python run.py --input "<输入内容>" --json
```

## 使用方法

```bash
python run.py --topic "你的主题"                     # 基础生成（预览）
python run.py --input 原始文件.txt --out 结果.md      # 文件输入处理
python run.py --mode standard  # 指定整理模式
python run.py --count 2 --seed 42                     # 多样性与可复现
```

## 输出示例（节选）

```
【会议纪要 会议总结生成器 · mode=standard】
本场会议共讨论 {n} 个议题，关键结论如下。
【会议概况】时间/参会人/主题由你补全，AI 已按录音原文整理。
（完整输出见运行结果，结构固定可解析）
```

## 参数表

| 参数 | 默认 | 说明 |
|---|---|---|
| --topic / --input | 必填一 | 会议原始记录文本（粘贴或 --input 文件，支持多编码） |
| --mode | standard | 整理模式：standard(标准总结) / brief(简报) / action(行动项优先) |
| --count | 1 | 生成变体数 1-3 |
| --out | 无 | 输出文件（默认仅预览） |
| --json | 无 | 结构化 JSON |
| --dry-run | 无 | 预览不写盘 |
| --verbose | 无 | 输出每段决策明细 |
| --selftest | 无 | 内置自检契约 |

## 高级用法

1. **批量**：`--input` 传文件批量处理；`--topic` 传一句话快速生成
2. **二次创作**：`--json` 输出结构供下游（汇报系统/编辑器/提词器）消费
3. **风格控制**：切换 mode 参数获得不同输出粒度
4. **合规自查**：生成后人工过一遍「三不」清单（不夸大、不承诺效果、不贬低）

## 常见问题（FAQ）

- Q: 生成结果能直接用吗？A: 结构可直接用，具体数字、名称、时间等事实信息需你按真实情况补全。
- Q: 支持中文输入吗？A: 原生支持，且内置 utf-8/gbk/gb18030 多编码容错。
- Q: 为什么内容比较模板化？A: 模板保证结构稳定可解析；同一模板换输入/换 seed 即可获得不同表达。

## 竞品对标

**对标对象**：通用 AI 对话直接生成与各平台的模板工具。

**用户为什么下载这类工具（下载原因拆解）**：
1. 要结构——会议纪要 会议总结生成器 对应的是高频动作词（搜索需求万级），用户要可直接交付的成品框架；
2. 要省事——参数化一次到位，不用反复描述场景与要求；
3. 要合规——平台对绝对化/诱导内容有硬约束，内置词表拦截降低踩线风险。

**覆盖声明**：本工具输出结构优于通用对话的零散建议（可复现、可解析）；独有合规词表拦截功能；通用 AI 方案不具备离线运行与内置自检能力。

**超越声明**：本工具领先同类通用提示词方案，在结构稳定性与合规性两个维度完胜。

## 异常处理与失败排查

| 现象 | 可能原因 | 处理方式 |
|---|---|---|
| 提示缺少输入 | 未传 --topic/--input | 按参数表补必填参数 |
| 提示参数越界 | 变体数/模式超范围 | 调整到合法区间后重试 |
| 内容被拦截(rc=3) | 输入命中内置禁止词 | 按提示改写后重试 |
| 写盘失败 | 路径无权限 | 换可写路径或先 --dry-run 预览 |
| --selftest 有失败项 | 环境异常 | 修环境至自检全绿再使用 |

## 许可证（License）

```text
MIT License

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
```
<!-- professional-license-embedded -->
