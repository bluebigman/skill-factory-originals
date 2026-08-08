---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: attachment-fu
name: attachment-fu
displayName: 附件管理 文件处理 数据转换
description: 将文件或数据转为结构化附件记录，提取关键信息并输出。
version: 1.0.1
rules_version: cpr-20260808-n152
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/attachment-fu
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 林墨工坊
agent_created: true
trigger_words: ["attachment-fu", "附件处理", "文件转记录", "附件管理", "数据提取", "文件解析"]
---

> 📜 **用户协议（User Agreement）**
> 1. 本 Skill 仅供学习与参考用途。使用本 Skill 产生的任何结果，由使用者自行承担全部责任；本 Skill 不提供任何明示或暗示的保证。
> 2. 涉及法律、财务、税务、投资、医疗等专业决策时，请务必咨询持证专业人士。
> 3. 本代码受版权法保护，未经授权复制、反向工程或商业利用将被追究法律责任。
<!-- user-agreement-injected -->


> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# attachment-fu Skill 文档

## 一、能力边界速查卡

本 Skill 的核心定位：**将用户提供的文件、数据或 URL 转换为符合约定格式的结构化附件记录**。它不是一个通用的文件存储工具，也不是一个数据清洗工具，而是一个“输入 → 解析 → 结构化输出”的转换器。

### 1.1 能做（核心能力）

| 编号 | 能力项 | 说明 | 典型输入示例 |
|------|--------|------|--------------|
| C1 | 文件/数据/URL 转结构化结果 | 将原始输入解析为字段化的附件记录 | 一个 PDF 路径、一段 JSON 字符串、一个下载链接 |
| C2 | 关键信息识别与保留 | 自动提取文件名、大小、类型、时间戳等元数据 | 文件名含日期、URL 带参数、数据含嵌套字段 |
| C3 | 按约定格式输出 | 输出遵循固定 schema，便于下游程序消费 | 输出 JSON 对象，字段名固定 |
| C4 | 置信度标注 | 对自动推断的字段给出可信度标记 | 类型推断置信度 0.92，来源不明置信度 0.4 |
| C5 | 批量处理与自定义格式 | 支持多文件/多记录输入，允许用户指定输出模板 | 传入 10 个文件路径数组，指定输出 CSV 格式 |

### 1.2 不能做（明确边界）

| 编号 | 限制项 | 说明 |
|------|--------|------|
| L1 | 不执行文件内容深度分析 | 不进行 OCR、语义理解、情感分析等 |
| L2 | 不修改原始文件 | 只读取元数据，不写入、不转换原文件 |
| L3 | 不处理加密或损坏文件 | 无法读取加密容器或损坏的文件头 |
| L4 | 不保证字段值绝对准确 | 所有推断字段均带置信度，低置信度需人工确认 |
| L5 | 不替代数据库或存储系统 | 只生成结构化记录，不负责持久化存储 |

### 1.3 适用对象

- 需要将散落文件整理为清单的运营人员
- 需要将外部数据源接入内部系统的开发人员
- 需要批量归档文件元数据的档案管理员
- 需要从 URL 快速获取文件信息的爬虫脚本使用者

---

## 二、触发方式与场景映射

### 2.1 触发词

- 主触发词：`attachment-fu`
- 同义触发词：`附件处理`、`文件转记录`、`附件管理`、`数据提取`、`文件解析`

### 2.2 场景映射表

| 用户实际说法 | 触发动作 | 处理模式 |
|--------------|----------|----------|
| “帮我把这个文件转成记录” | 解析单个文件 | 单文件模式 |
| “处理一下这个 URL 里的附件” | 下载并解析 URL 指向的文件 | URL 模式 |
| “这有一批文件，都转一下” | 批量解析多个文件 | 批量模式 |
| “输出成 CSV 格式” | 按自定义模板输出 | 自定义格式模式 |
| “这个文件是什么类型？” | 仅提取类型与元数据 | 快速识别模式 |

---

## 三、标准处理流程

### 3.1 前置条件

| 条件项 | 要求 | 缺失时的处理 |
|--------|------|--------------|
| 输入来源 | 文件路径 / URL / 数据字符串 | 返回错误码 E1001 |
| 输入可访问性 | 文件存在且可读，URL 可下载 | 返回错误码 E1002 |
| 输出格式指定 | 默认 JSON，可指定 CSV/YAML | 使用默认格式 |
| 批量输入 | 数组或换行分隔的列表 | 自动识别并进入批量模式 |

### 3.2 执行步骤

**步骤 1：收集输入并确认格式**

- 接收用户输入，判断输入类型（文件路径 / URL / 原始数据）
- 确认输出格式（JSON / CSV / YAML），未指定则默认 JSON
- 确认是否批量处理（输入为数组或包含多个路径）

**步骤 2：解析输入内容**

- 文件路径：读取文件元数据（大小、修改时间、扩展名）
- URL：发起 HEAD 请求获取 Content-Type、Content-Length、Last-Modified
- 原始数据：解析数据结构，识别关键字段

**步骤 3：按规则处理**

| 处理项 | 规则 | 示例 |
|--------|------|------|
| 文件名提取 | 从路径或 URL 末尾提取，去除查询参数 | `/data/report_2024.pdf` → `report_2024.pdf` |
| 文件类型识别 | 优先使用扩展名，其次使用 MIME 类型 | `.pdf` → `application/pdf` |
| 大小标准化 | 统一转为字节数，保留原始单位 | `2.5 MB` → `2621440` |
| 时间戳规范化 | 转为 ISO 8601 格式 | `2024-01-15 10:30:00` → `2024-01-15T10:30:00Z` |
| 来源标记 | 记录输入来源类型（local/url/data） | `local` |

**步骤 4：生成结果并标注置信度**

- 每个字段附带 `confidence` 属性，取值范围 0~1
- 规则明确字段（如文件大小）置信度为 1.0
- 推断字段（如类型推断）置信度按规则计算

**步骤 5：输出与自查**

- 按约定格式输出结果
- 自查项：字段完整性（必填字段是否齐全）、格式正确性（JSON 语法、CSV 列数）、置信度标注是否完整
- 如有疑问（低置信度字段），在输出中附带提示，并主动询问用户确认

### 3.3 输出规范

**默认 JSON 输出格式：**

```json
{
  "record_id": "uuid-string",
  "source_type": "local | url | data",
  "original_input": "用户输入的原始值",
  "parsed": {
    "file_name": "report_2024.pdf",
    "file_size_bytes": 2621440,
    "mime_type": "application/pdf",
    "extension": "pdf",
    "modified_at": "2024-01-15T10:30:00Z",
    "source_url": "https://example.com/report_2024.pdf"
  },
  "confidence": {
    "file_name": 1.0,
    "file_size_bytes": 1.0,
    "mime_type": 0.95,
    "extension": 1.0,
    "modified_at": 0.8,
    "source_url": 1.0
  },
  "warnings": ["modified_at 为推断值，原始来源未提供 Last-Modified 头"]
}
```

**CSV 输出格式：**

```
record_id,source_type,file_name,file_size_bytes,mime_type,extension,modified_at,confidence_overall
uuid-xxx,local,report_2024.pdf,2621440,application/pdf,pdf,2024-01-15T10:30:00Z,0.95
```

---

## 四、置信度门控机制

### 4.1 置信度分级

| 置信度区间 | 等级 | 处理策略 |
|------------|------|----------|
| 0.9 ~ 1.0 | 高置信 | 直接输出，无需确认 |
| 0.6 ~ 0.89 | 中置信 | 输出并附带提示，建议用户复核 |
| 0 ~ 0.59 | 低置信 | 输出 `[需核实:字段名]` 占位符，主动询问用户 |

### 4.2 占位符规则

- 格式：`[需核实:字段名]`
- 示例：`[需核实:mime_type]`
- 占位符不阻断输出流程，但会在 `warnings` 中列出所有待核实项

### 4.3 禁止行为

- 禁止在信息不足时编造字段值
- 禁止将低置信度值标记为高置信度
- 禁止忽略置信度标注直接输出

---

## 五、错误码体系

| 错误码 | 错误描述 | 用户提示话术 | 修正步骤 |
|--------|----------|--------------|----------|
| E1001 | 输入为空或格式不正确 | “未检测到有效输入。请提供文件路径、URL 或数据字符串。” | 检查输入是否为空；确认输入格式为字符串或路径 |
| E1002 | 文件不存在或不可访问 | “无法访问该文件/URL。请确认路径正确且具有读取权限。” | 检查路径拼写；确认文件存在；检查网络连接 |
| E1003 | URL 下载失败 | “URL 下载失败。请确认链接有效且未过期。” | 手动访问 URL 验证；检查是否需要认证 |
| E1004 | 文件类型无法识别 | “无法识别该文件类型。请提供扩展名或 MIME 类型。” | 手动指定文件类型；提供更多文件信息 |
| E1005 | 批量输入格式错误 | “批量输入格式不正确。请使用数组或换行分隔的列表。” | 将输入改为数组格式或每行一个路径 |
| E1006 | 输出格式不支持 | “不支持的输出格式。支持：JSON、CSV、YAML。” | 重新指定输出格式为支持的类型 |

---

## 六、FAQ 与反模式对照

### 6.1 常见坑

| 坑编号 | 常见错误做法 | 正确做法 |
|--------|--------------|----------|
| P1 | 直接使用 URL 中的文件名作为最终文件名，忽略 URL 参数 | 去除查询参数，仅保留路径末尾的文件名 |
| P2 | 仅凭扩展名判断文件类型，忽略 MIME 类型 | 优先使用 MIME 类型，扩展名作为辅助验证 |
| P3 | 批量处理时遇到一个错误就中断全部 | 跳过错误项，记录错误信息，继续处理其余项 |
| P4 | 对推断字段不标注置信度 | 所有推断字段必须附带 confidence 属性 |
| P5 | 输出格式与用户要求不一致 | 处理前确认输出格式，处理中严格遵守 |

### 6.2 反模式对照表

| 反模式 | 表现 | 后果 | 替代方案 |
|--------|------|------|----------|
| 静默失败 | 遇到错误不提示，直接返回空结果 | 用户无法定位问题 | 返回错误码和详细错误信息 |
| 过度推断 | 对无法确定的信息强行给出值 | 输出不准确数据 | 使用 `[需核实:字段]` 占位符 |
| 忽略批量 | 批量输入只处理第一个 | 数据丢失 | 遍历全部输入，逐项处理 |
| 格式混乱 | 同一字段在不同记录中格式不一致 | 下游解析困难 | 统一字段格式，强制类型转换 |

---

## 七、渐进式披露路径

### 7.1 速查卡（30 秒上手）

```
输入：文件路径 / URL / 数据
输出：JSON（默认） / CSV / YAML
必填：输入来源
可选：输出格式、批量模式
关键规则：推断字段必须标注置信度
```

### 7.2 新手路径（首次使用）

1. 阅读「能力边界速查卡」了解能做什么、不能做什么
2. 查看「触发方式与场景映射表」找到自己的使用场景
3. 按照「标准处理流程」的步骤 1-5 执行一次完整处理
4. 遇到问题查阅「错误码体系」定位并修正

### 7.3 进阶路径（深度使用）

1. 研究「置信度门控机制」，理解置信度计算规则
2. 自定义输出模板，适配内部系统格式
3. 结合批量处理能力，编写自动化脚本
4. 参考「FAQ 与反模式对照」优化处理逻辑

---

## 八、参数参考表

### 8.1 输入参数

| 参数名 | 类型 | 必填 | 默认值 | 说明 |
|--------|------|------|--------|------|
| `input` | string / string[] | 是 | 无 | 文件路径、URL 或数据字符串 |
| `output_format` | string | 否 | `json` | 输出格式：`json` / `csv` / `yaml` |
| `batch_mode` | boolean | 否 | `false` | 是否启用批量处理 |
| `include_confidence` | boolean | 否 | `true` | 是否在输出中包含置信度信息 |
| `custom_template` | object | 否 | 无 | 自定义输出字段映射模板 |

### 8.2 输出字段说明

| 字段名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `record_id` | string | 是 | 唯一记录标识，UUID 格式 |
| `source_type` | string | 是 | 输入来源类型：`local` / `url` / `data` |
| `original_input` | string | 是 | 用户输入的原始值 |
| `parsed.file_name` | string | 是 | 提取的文件名 |
| `parsed.file_size_bytes` | integer | 是 | 文件大小（字节） |
| `parsed.mime_type` | string | 是 | MIME 类型 |
| `parsed.extension` | string | 是 | 文件扩展名 |
| `parsed.modified_at` | string | 否 | 最后修改时间（ISO 8601） |
| `parsed.source_url` | string | 否 | 来源 URL（当 source_type 为 url 时） |
| `confidence` | object | 是 | 各字段置信度映射 |
| `warnings` | string[] | 否 | 警告信息列表 |

---

## 九、使用示例

### 9.1 单文件处理

**输入：**
```
attachment-fu 处理 /data/report_2024.pdf
```

**输出：**
```json
{
  "record_id": "a3f8c2e1-9b4d-4f6a-8e2c-1d5b7a9c3e2f",
  "source_type": "local",
  "original_input": "/data/report_2024.pdf",
  "parsed": {
    "file_name": "report_2024.pdf",
    "file_size_bytes": 2621440,
    "mime_type": "application/pdf",
    "extension": "pdf",
    "modified_at": "2024-01-15T10:30:00Z"
  },
  "confidence": {
    "file_name": 1.0,
    "file_size_bytes": 1.0,
    "mime_type": 0.95,
    "extension": 1.0,
    "modified_at": 1.0
  },
  "warnings": []
}
```

### 9.2 URL 处理

**输入：**
```
attachment-fu 处理 https://example.com/files/data.csv?token=abc123
```

**输出：**
```json
{
  "record_id": "b7d2e4f8-1a3c-4e5b-9f6d-2c8a0b4d6e7f",
  "source_type": "url",
  "original_input": "https://example.com/files/data.csv?token=abc123",
  "parsed": {
    "file_name": "data.csv",
    "file_size_bytes": 1048576,
    "mime_type": "text/csv",
    "extension": "csv",
    "modified_at": "2024-02-01T08:00:00Z",
    "source_url": "https://example.com/files/data.csv"
  },
  "confidence": {
    "file_name": 1.0,
    "file_size_bytes": 0.9,
    "mime_type": 0.85,
    "extension": 1.0,
    "modified_at": 0.7,
    "source_url": 1.0
  },
  "warnings": ["modified_at 为推断值，原始来源未提供 Last-Modified 头"]
}
```

### 9.3 批量处理

**输入：**
```
attachment-fu 批量处理 ["/data/a.pdf", "/data/b.docx", "/data/c.png"] 输出 CSV
```

**输出：**
```
record_id,source_type,file_name,file_size_bytes,mime_type,extension,modified_at,confidence_overall
c1d3e5f7-2b4d-4e6f-8a7c-3d9b1e5f7a8b,local,a.pdf,524288,application/pdf,pdf,2024-01-10T09:00:00Z,0.98
d2e4f6a8-3c5e-4f7a-9b8d-4eac2f6a8b9c,local,b.docx,1048576,application/vnd.openxmlformats-officedocument.wordprocessingml.document,docx,2024-01-12T14:30:00Z,0.96
e3f5a7b9-4d6f-4a8b-8c9e-5fbd3a7b9cad,local,c.png,2097152,image/png,png,2024-01-14T11:


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
