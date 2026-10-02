---
name: after-sale-coach-1
description: "针对 及时响应、标准统一 等情境给出可执行处置"
version: 1.0.0
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/after-sale-coach
license: MIT
copyright_holder: SkillForge Lab
ai_generated: true
---

# 售后处理 退换流程 顾问

针对 及时响应、标准统一 等情境给出可执行处置 —— 给需要快速定位与处置「该领域」类问题的使用者：把模糊描述转成**归因清单 + 可执行动作**。

<!-- ai-generated-notice -->
**AI 生成披露**：本能力边界、领域规则与示例由生成器按通用领域知识撰写，经人工规则化整理与
自动化合规检查后产出；**未复制任何受版权保护的原文**，与上游开源项目无派生关系。

<!-- professional-disclaimer-injected -->
**边界声明**：本能力提供通用方法性建议，**不构成专业诊断、治疗、法律或投资意见**；
涉及医疗/法律/金融等专业事项请咨询具备资质的专业人士。

## 快速开始 Quick Start

| 你的处境 | 立即执行 |
|---|---|
| 手上有一段描述，想马上得到处置建议 | `python run.py --text "你的描述"` |
| 内容在文件里 | `python run.py --input note.txt --verbose` |
| 想先确认环境可用 | `python run.py --selftest` |
| 只想预览不写盘 | `python run.py --text "..." --dry-run` |

## 适用场景 When to Use

**适合使用**


**不适合使用**
- 输入为空或与「该领域」完全无关
- 需要**专业资质判断**的场景（医疗诊断、法律意见、投资决策）——请转介专业人士
- 需要读取真实业务系统数据的场景——本能力只处理你提供的文本

## 能力总览 Capabilities

| 能力 | 覆盖关键词 | 触发方式 | 输出 |
|---|---|---|---|
| 识别与处置「及时响应」 | 及时响应 | `--text` 输入含该词 | 归因 + 可执行动作 |
| 识别与处置「标准统一」 | 标准统一 | `--text` 输入含该词 | 归因 + 可执行动作 |

## 模块决策表 Decision Table

| 你的意图 | 对应处理 | 读取位置 |
|---|---|---|
| 想解决「及时响应」 | 拖延会升级为平台介入 | `scripts/main.py` 规则表 |
| 想解决「标准统一」 | 建判定标准 | `scripts/main.py` 规则表 |

## 示例 Examples

### 示例 1：及时响应

**输入**
```bash
python run.py --text "及时响应"
```

**输出（人读部分）**
```text
【归因】及时响应
【建议动作】
  1. 拖延会升级为平台介入
【边界】本能力提供通用方法建议，不构成专业诊断；重度情形请转介专业机构。
```

**输出（机读 JSON 摘要）**
```json
{{"ok": true, "summary": "及时响应 的处置建议已生成", "next_actions": ["拖延会升级为平台介入"], "error_code": null}}
```

**为什么这样建议**：拖延会升级为平台介入

### 示例 2：标准统一

**输入**
```bash
python run.py --text "标准统一"
```

**输出（人读部分）**
```text
【归因】标准统一
【建议动作】
  1. 建判定标准
【边界】本能力提供通用方法建议，不构成专业诊断；重度情形请转介专业机构。
```

**输出（机读 JSON 摘要）**
```json
{{"ok": true, "summary": "标准统一 的处置建议已生成", "next_actions": ["建判定标准"], "error_code": null}}
```

**为什么这样建议**：建判定标准


## 安装与配置 Installation

- **运行环境**：Python 3.8+（仅标准库，无第三方依赖）
- **目录结构**：
  ```text
  after-sale-coach-1/
  ├── SKILL.md          本文件
  ├── run.py            入口（转发到 scripts/main.py）
  ├── selftest.py       自检脚本
  └── scripts/main.py   规则引擎实现
  ```
- **无 API Key 要求**：本能力为**本地规则引擎**，不调用任何外部服务
- **编码**：输入自动尝试 `utf-8 → gbk → gb18030 → latin-1` 多级回退

## 常见问题 Troubleshooting

| 输入很简短会不会没结果？ | 关键词命中率低 | 描述越具体越可用；补充场景与已尝试过的做法 |
| 同一输入多次调用结果不一致？ | 不应发生 | 本能力是纯本地规则引擎，**幂等**；若不一致请上报 |
| 能不能直接给专业结论？ | 超出能力边界 | 本能力只给**通用方法建议**；医疗/法律/投资请咨询专业人士 |
| 支持批量处理吗？ | 当前为单次调用 | 循环调用即可，单次 <1 秒 |

## 最佳实践 Best Practices

- **遇到「及时响应」**：拖延会升级为平台介入
- **遇到「标准统一」**：建判定标准
- **先描述再提问**：把现象、已尝试的做法、期望结果一次说清，建议会更贴合
- **结合自身情况判断**：本能力给的是通用做法，具体决策请结合你的实际情境
- **越界即止**：涉及专业资质的事项，本能力会明确提示转介，请遵从
- **保留输入样本**：若输出异常，保留原始输入便于定位（错误码 E04）

## 相关资源 Related

- 本能力属于专家包 `after-sale-coach`（含 3 个协同技能）
- 知识来源：`self_authored_rules`（按通用领域知识自撰，**无上游派生**）
- 可复现性：见 `reproduce.py` 与 `.phoenix/selftest_evidence.json`

## 许可证与版权

<!-- professional-license-embedded -->
本项目以 **MIT License** 授权（全文见包内 `LICENSE` 文件）。
Copyright (c) 2026 **SkillForge Lab**. 保留所有权利声明。

## AtoA 调用示例（Agent 视角）

面向 Agent 自主调用时，建议按以下顺序判断与使用：

1. **适配判断**：读 `when_to_use` 与 `boundary`，确认用户意图落在「该领域」领域内
2. **构造入参**：按 `input_schema` 组装 `{"text": "<用户原始描述>"}`，不要自行改写用户原话
3. **调用**：`python run.py --text "<text>"`（或 `--input <文件>`）
4. **解析出参**：读 JSON 摘要的 `ok` / `summary` / `next_actions`；`next_actions` 可直接转述给用户
5. **异常处理**：`error_code` 非空时按错误码表自愈重试；**同一错误重试不超过 1 次**
6. **边界兜底**：若 `ok=false` 且 `error_code=E03`，说明超出本能力范围，应改用其他能力或补充上下文

## 能力声明（机器可读 · AtoA）

```yaml
capability:
  id: after-sale-coach-1
  name_zh: "售后处理 退换流程 顾问"
  when_to_use: "针对 及时响应、标准统一 等情境给出可执行处置"
  input_schema:
    type: object
    properties:
      text: {type: string, description: "待分析的文本描述"}
      input: {type: string, description: "文件路径（与 text 二选一）"}
  output_schema:
    type: object
    properties:
      ok: {type: boolean}
      summary: {type: string}
      next_actions: {type: array, items: {type: string}}
      error_code: {type: string, enum: [E01, E02, E03, E04]}
  boundary: "只处理 '该领域' 等领域情境；不做专业诊断/法律/投资意见"
  idempotent: true
```

## 调用契约

1. **输入**：`--text`（直接文本）或 `--input`（文件路径）二者之一；均缺则读标准输入
2. **输出**：Markdown（人读）+ JSON 摘要（机读，字段见 `output_schema`）
3. **幂等**：相同输入重复调用结果一致；`--dry-run` 不产生副作用
4. **超时**：单次调用 <1 秒（纯本地计算）；调用方建议设 10 秒超时

## 错误码表

| 码 | 含义 | 触发条件 | 自愈建议 |
|---|---|---|---|
| E01 | 输入缺失 | 未提供 text/input 且标准输入为空 | 补齐文本后重试 |
| E02 | 格式不符 | 输入非可解码文本 | 转为纯文本（UTF-8）后重试 |
| E03 | 超出边界 | 内容与「该领域」等关键词均不匹配 | 改用其他能力或补充上下文 |
| E04 | 内部错误 | 未预期的运行异常 | 退避 1 次后重试；仍失败请记录输入样本 |
