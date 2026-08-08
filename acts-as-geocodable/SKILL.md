---
> 本内容由 AI 生成，仅供学习参考（《人工智能生成合成内容标识办法》显式标识）。
<!-- ai-generated-notice -->
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: acts-as-geocodable
name: acts-as-geocodable
displayName: 地理编码 地址解析 坐标映射
description: 将地址文本解析为结构化地理数据并输出坐标与置信度。
version: 1.0.3
rules_version: cpr-20260808-n152
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/acts-as-geocodable
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: GeoForge Studio
agent_created: true
trigger_words:
  - "acts-as-geocodable"
  - "地理编码"
  - "地址转坐标"
  - "geocode"
  - "地址解析"
  - "经纬度提取"
---

> 📜 **用户协议（User Agreement）**
> 1. 本 Skill 仅供学习与参考用途。使用本 Skill 产生的任何结果，由使用者自行承担全部责任；本 Skill 不提供任何明示或暗示的保证。
> 2. 涉及法律、财务、税务、投资、医疗等专业决策时，请务必咨询持证专业人士。
> 3. 本代码受版权法保护，未经授权复制、反向工程或商业利用将被追究法律责任。
<!-- user-agreement-injected -->


> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# 地理编码 Skill — 地址解析与坐标映射

本 Skill 提供一套轻量级的地理编码处理规范，帮助你将用户提供的地址描述（文本、文件或 URL 中的地址信息）转换为结构化的地理坐标结果，并附带置信度评估。适用于需要从非结构化文本中提取位置信息的场景。


## 一页纸速查卡（Quick Reference）

> **给新手的 30 秒上手路径**：先看「触发方式」→ 再跑一个「标准流程」示例 → 最后对照「输出格式」检查结果。

| 项目 | 速查内容 |
|---|---|
| **我能做什么** | 把"北京市海淀区中关村大街27号"变成 `{lat: 39.9847, lng: 116.3184, confidence: 0.95}` |
| **我不能做什么** | 不处理模糊地址（如"北京"）、不保证实时路况、不解析手写图片 |
| **怎么触发** | 直接说"把这段地址转成坐标"或"geocode 这个文件" |
| **最快示例** | 输入：`北京市朝阳区建国路88号` → 输出：结构化 JSON + 置信度 |
| **常见坑** | 地址缺省市级时置信度会降到 0.6 以下；海外地址需指定国家代码 |
| **出错怎么办** | 看错误码表（E001-E005），按"如何修正"步骤操作 |
| **进阶玩法** | 批量处理 1000 条地址、坐标反查、置信度阈值调优、自定义输出格式 |
| **智能洞察** | 自动识别地址模式、质量评分、异常检测、优化建议 |

---

## 触发方式（Trigger）

### 触发词（8 个）

| 触发词 | 大白话解释 | 示例 |
|---|---|---|
| `acts as geocodable` | 激活本技能 | "acts as geocodable，帮我解析这个地址" |
| `地理编码` | 把地址变成坐标 | "做一下地理编码" |
| `地址转坐标` | 同上，更直白 | "把地址转成坐标" |
| `geocode` | 英文触发词 | "geocode this address" |
| `地址解析` | 从文本里提取位置 | "解析这段文字里的地址" |
| `经纬度提取` | 只要经纬度 | "提取经纬度" |
| `把地址变成坐标` | 口语化触发 | "帮我把这个地址变成坐标" |
| `查经纬度` | 口语化触发 | "查一下这个地址的经纬度" |

### 触发场景

- 用户直接要求转换地址
- 用户提供包含地址的文本/文件/URL，要求提取位置
- 用户要求批量处理多个地址
- 用户要求验证已有坐标的准确性
- 用户要求从混合文本中提取所有地址并批量转换
- 用户要求对地址数据进行质量评估和清洗

---

## 能力边界（Boundary）

### 能做（Capabilities）

| 能力项 | 具体说明 | 适用场景 |
|---|---|---|
| 标准地址解析 | 支持"省+市+区+街道+门牌号"完整地址 | 电商收货地址、公司注册地址 |
| 批量处理 | 一次处理最多 1000 条地址，输出结构化文件 | 数据清洗、批量迁移 |
| 多格式输入 | 支持 TXT、CSV、JSON、纯文本粘贴 | 各类数据源 |
| 置信度评估 | 每条结果附带 0-1 置信度分数 | 需要质量把控的场景 |
| 失败明细追踪 | 单条失败不影响整体，输出失败清单 | 大规模数据处理 |
| 坐标反查（高级） | 输入坐标，输出最近地址描述 | 地图应用辅助 |
| 地址模式识别 | 自动识别地址中的省市区街道层级 | 非标准地址清洗 |
| 地址质量评分 | 对地址完整度、规范性进行评分 | 数据质量评估 |
| 异常地址检测 | 检测重复、矛盾、缺失关键字段的地址 | 数据清洗 |
| 地址标准化 | 将非标准地址转换为标准格式 | 数据入库前处理 |

### 不做（Non-Capabilities）

| 不做项 | 原因 | 替代方案 |
|---|---|---|
| 模糊地址解析（如"北京"） | 无法确定具体位置 | 要求用户提供更详细地址 |
| 实时路况/导航 | 非地理编码范畴 | 使用专业地图 API |
| 手写图片 OCR | 需额外 OCR 能力 | 先转文本再处理 |
| 海外地址（无国家代码） | 默认中国地址库 | 指定国家代码（如 `US:` 前缀） |
| 加密/损坏文件 | 无法读取内容 | 修复文件后重试 |
| 实时 POI 搜索 | 非本技能范围 | 使用地图搜索服务 |

### 适用对象表

| 用户类型 | 适用程度 | 说明 |
|---|---|---|
| 数据分析师 | ✅ 高度适用 | 批量清洗地址数据 |
| 后端开发者 | ✅ 高度适用 | 集成到服务中 |
| 普通用户 | ⚠️ 部分适用 | 需提供完整地址 |
| 地图应用开发者 | ⚠️ 部分适用 | 需配合地图 API 使用 |
| 需要实时导航的用户 | ❌ 不适用 | 请使用专业导航软件 |
| 数据质量工程师 | ✅ 高度适用 | 地址质量评估与清洗 |

---

## 标准流程（Standard Workflow）

### 输入参数默认值表

| 参数名 | 默认值 | 说明 | 调整建议 |
|---|---|---|---|
| `input_format` | `auto` | 自动检测输入格式 | 明确指定可提速 |
| `output_format` | `json` | 输出格式 | 可选 `csv`、`json`、`txt` |
| `country_code` | `CN` | 国家代码 | 海外地址需修改 |
| `confidence_threshold` | `0.5` | 置信度阈值 | 要求高精度时调至 0.7 |
| `batch_size` | `100` | 批量处理条数 | 内存不足时调小 |
| `timeout` | `10s` | 单条超时时间 | 网络慢时调大 |
| `retry_count` | `3` | 失败重试次数 | 稳定性要求高时调大 |
| `retry_interval` | `1s` | 重试间隔（递增） | 默认即可 |
| `strict_mode` | `false` | 严格模式（失败即中断） | 调试时开启 |
| `deduplicate` | `true` | 是否去重 | 数据清洗时开启 |
| `normalize` | `true` | 是否标准化地址格式 | 默认开启 |

### 执行步骤

1. **读取输入**：接收文本、文件路径或 URL，自动检测格式。
2. **参数校验**：检查必填参数，缺失时使用默认值。
3. **地址清洗**：去除多余空格、特殊字符，统一格式。
4. **地址解析**：按"省-市-区-街道-门牌号"层级拆分。
5. **坐标匹配**：在地址库中查找对应坐标。
6. **置信度评估**：根据地址完整度、匹配精度计算置信度。
7. **智能洞察**：分析地址模式、识别异常、生成质量报告。
8. **结果输出**：生成结构化结果文件 + 控制台摘要。
9. **失败处理**：单条失败记录到失败明细，不中断整体。

### 输出格式示例

**输入**：
## 前置条件
- 无特殊环境要求


## 许可证（License）

```text
MIT License

Copyright (c) 2026 SkillForge Lab

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.
```
<!-- professional-license-embedded -->
