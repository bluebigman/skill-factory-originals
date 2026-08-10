---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: attachment-fu
name: attachment-fu
displayName: 文件归档 元数据提取 结构化记录
description: 将文件、数据或URL转为结构化附件记录，提取元数据并输出JSON/CSV。
version: 2.0.1
rules_version: cpr-20260810-n301
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/attachment-fu
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 独立技能工坊
agent_created: true
trigger_words: ["attachment-fu", "附件整理", "文件转记录", "元数据提取", "附件归档", "文件结构化"]
---

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->


> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# attachment-fu 技能文档

## 一、能力边界（一页纸速查卡）

### 1.1 能做什么

| 能力项 | 说明 | 输入示例 | 输出示例 |
|--------|------|----------|----------|
| 文件转记录 | 将本地文件路径解析为结构化附件记录 | `/data/reports/Q3.pdf` | `{"name":"Q3.pdf","size":204800,"type":"pdf"}` |
| URL 转记录 | 抓取 URL 指向的资源并提取基础元数据 | `https://example.com/doc.pdf` | `{"url":"...","domain":"example.com","status":200}` |
| 数据转记录 | 将内存中的字节流或 Base64 数据转为附件记录 | `b"%PDF..."` | `{"name":"untitled.pdf","size":1024,"encoding":"binary"}` |
| 元数据提取 | 从附件中提取文件名、大小、类型、修改时间等 | 任意文件 | 结构化字段集合 |
| 批量输出 | 将多条附件记录汇总为 JSON 数组或 CSV 表格 | 多个文件路径 | `attachments.json` 或 `attachments.csv` |

### 1.2 不能做什么（明确边界）

- **不执行内容解析**：不读取 PDF 正文、图片 OCR、音视频转写。
- **不修改原文件**：只读取元数据，不移动、重命名、删除源文件。
- **不处理加密文件**：密码保护的压缩包或加密文档无法提取内部信息。
- **不进行语义理解**：不判断文件内容好坏、不分类主题、不生成摘要。
- **不保证网络可达性**：URL 抓取依赖网络环境，超时或拒绝连接时返回错误码。

### 1.3 适用对象

- 需要批量整理本地文件清单的办公人员
- 需要将附件信息导入数据库或表格的开发者
- 需要快速生成文件索引的档案管理员
- 需要将网络资源登记为附件的调研人员

---

## 二、触发方式

### 2.1 触发词

| 触发词 | 场景 |
|--------|------|
| `attachment-fu` | 直接调用技能主命令 |
| `附件整理` | 中文场景，批量处理文件 |
| `文件转记录` | 需要将文件转为结构化数据 |
| `元数据提取` | 需要获取文件属性信息 |
| `附件归档` | 将附件登记入库 |
| `文件结构化` | 将散乱文件转为统一格式 |

### 2.2 场景映射表

| 用户说（大白话） | 实际执行 |
|------------------|----------|
| "帮我把这个文件夹里的文件都列出来" | 扫描目录，生成 JSON 记录 |
| "这个链接里的文件帮我登记一下" | 抓取 URL，提取元数据 |
| "把这些附件信息导成表格" | 输出 CSV 格式 |
| "看看这个文件多大、什么格式" | 提取单个文件元数据 |
| "我有几个文件要整理，格式统一一下" | 批量转换并输出标准结构 |

---

## 三、标准流程

### 3.1 前置条件

| 条件 | 要求 | 检查方式 |
|------|------|----------|
| 输入路径存在 | 文件或目录必须真实存在 | `os.path.exists()` |
| 网络可用（仅 URL 模式） | 能访问目标域名 | `requests.get()` 状态码 |
| 输出目录可写 | 有权限创建输出文件 | `os.access()` 写权限 |
| 输入格式合法 | 文件路径为字符串，数据为 bytes 或 Base64 | 类型检查 |

### 3.2 执行步骤

#### 步骤 1：确定输入模式

根据输入类型选择处理路径：

| 输入类型 | 检测方式 | 处理模式 |
|----------|----------|----------|
| 本地文件路径 | 以 `/` 或 `./` 开头，且 `os.path.isfile()` 为真 | `local` |
| 目录路径 | `os.path.isdir()` 为真 | `directory` |
| URL | 以 `http://` 或 `https://` 开头 | `remote` |
| 字节流 | `isinstance(data, bytes)` 为真 | `binary` |
| Base64 字符串 | 可被 `base64.b64decode()` 解析 | `encoded` |

#### 步骤 2：提取元数据

对每个附件执行以下字段提取：

| 字段名 | 类型 | 提取方式 | 缺失时默认值 |
|--------|------|----------|--------------|
| `name` | string | 文件名（含扩展名） | `untitled` |
| `extension` | string | 扩展名（小写，不含点） | `unknown` |
| `size` | integer | 文件字节数 | `0` |
| `mime_type` | string | 根据扩展名映射 | `application/octet-stream` |
| `modified_at` | string | 文件修改时间（ISO 8601） | `1970-01-01T00:00:00Z` |
| `sha256` | string | 文件内容哈希（可选） | 空字符串 |
| `source` | string | 来源（路径/URL/内存） | `unknown` |

**扩展名到 MIME 映射表（节选）**：

| 扩展名 | MIME 类型 |
|--------|-----------|
| `.pdf` | `application/pdf` |
| `.docx` | `application/vnd.openxmlformats-officedocument.wordprocessingml.document` |
| `.xlsx` | `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet` |
| `.png` | `image/png` |
| `.jpg` / `.jpeg` | `image/jpeg` |
| `.txt` | `text/plain` |
| `.csv` | `text/csv` |
| `.zip` | `application/zip` |
| `.mp4` | `video/mp4` |
| `.mp3` | `audio/mpeg` |

#### 步骤 3：生成结构化记录

每条附件记录格式如下：

```json
{
  "name": "Q3_report.pdf",
  "extension": "pdf",
  "size": 204800,
  "mime_type": "application/pdf",
  "modified_at": "2026-08-01T14:30:00Z",
  "sha256": "a3f5...",
  "source": "/data/reports/Q3_report.pdf"
}
```

#### 步骤 4：输出

**JSON 输出**（默认）：

```json
{
  "generated_at": "2026-08-10T10:00:00Z",
  "count": 2,
  "attachments": [
    { "...": "记录 1" },
    { "...": "记录 2" }
  ]
}
```

**CSV 输出**（`--format csv`）：

```csv
name,extension,size,mime_type,modified_at,sha256,source
Q3_report.pdf,pdf,204800,application/pdf,2026-08-01T14:30:00Z,a3f5...,/data/reports/Q3_report.pdf
```

### 3.3 输出规范

| 项目 | 规范 |
|------|------|
| 编码 | UTF-8 |
| 时间格式 | ISO 8601（UTC） |
| 数字格式 | 整数，无千分位分隔 |
| 空值处理 | 使用空字符串 `""`，不使用 `null` |
| 排序 | 按文件名升序（字典序） |
| 换行符 | `\n`（LF） |

---

## 四、置信度门控

### 4.1 信息不足时的处理

当无法获取某个字段的准确值时，**不猜测、不编造**，使用占位符：

| 场景 | 占位符 | 示例 |
|------|--------|------|
| 文件大小无法获取 | `[需核实:size]` | `"size": "[需核实:size]"` |
| 修改时间未知 | `[需核实:modified_at]` | `"modified_at": "[需核实:modified_at]"` |
| MIME 类型无法确定 | `[需核实:mime_type]` | `"mime_type": "[需核实:mime_type]"` |
| 哈希计算失败 | `[需核实:sha256]` | `"sha256": "[需核实:sha256]"` |

### 4.2 使用规则

- 占位符必须原样输出，不得替换为近似值。
- 输出记录中同时包含 `"confidence": "partial"` 标记。
- 用户可依据占位符定位需要人工核实的字段。

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| `E001` | 文件不存在 | "指定路径未找到文件，请检查路径是否正确" | 1. 确认路径拼写；2. 检查文件是否被移动或删除 |
| `E002` | 目录不可读 | "目录存在但无读取权限" | 1. 检查权限设置；2. 以管理员身份运行 |
| `E003` | URL 无法访问 | "网络请求失败，目标地址不可达" | 1. 检查网络连接；2. 确认 URL 拼写；3. 尝试使用浏览器访问 |
| `E004` | 数据格式不支持 | "输入的数据类型无法识别" | 1. 确认输入为 bytes 或 Base64；2. 检查数据是否损坏 |
| `E005` | 输出目录不可写 | "无法写入输出文件，请检查目录权限" | 1. 更换输出目录；2. 检查磁盘空间 |
| `E006` | 批量处理中断 | "处理过程中发生异常，已停止" | 1. 查看错误日志；2. 排除问题文件后重试 |

---

## 六、FAQ 反模式

### 6.1 常见坑

| 坑 | 错误做法 | 正确做法 |
|----|----------|----------|
| 路径含空格 | 直接拼接路径字符串 | 使用 `os.path.join()` 或引号包裹 |
| 文件名编码 | 假设文件名是 ASCII | 使用 UTF-8 解码，处理 Unicode 文件名 |
| 超大文件 | 一次性读入内存计算哈希 | 分块读取（如 64KB 块） |
| 符号链接 | 跟随链接导致循环 | 使用 `os.path.realpath()` 解析后检查 |
| 空目录 | 输出空数组但无提示 | 输出 `count: 0` 并附带警告信息 |

### 6.2 反模式对照

| 反模式 | 问题 | 替代方案 |
|--------|------|----------|
| 静默跳过无法访问的文件 | 用户不知道有文件被遗漏 | 输出 `skipped` 列表并说明原因 |
| 将所有未知类型标记为 `application/octet-stream` | 信息价值低 | 尝试通过文件头（magic bytes）识别 |
| 覆盖已有输出文件 | 数据丢失风险 | 自动重命名或要求确认 |
| 递归扫描无限层级 | 性能问题 | 设置最大深度（默认 5 层） |

---

## 七、渐进式披露

### 7.1 速查卡（30 秒上手）

```
# 基本用法
attachment-fu /path/to/file           # 单文件转 JSON
attachment-fu /path/to/dir            # 目录批量转 JSON
attachment-fu https://example.com/a.pdf  # URL 转记录
attachment-fu --format csv /path/to/dir  # 输出 CSV

# 常用参数
--output <路径>    # 指定输出文件
--max-depth <N>    # 递归深度（默认 5）
--include-hash     # 计算 SHA256
--selftest         # 运行自检
--version          # 显示版本
```

### 7.2 新手路径（首次使用）

1. 运行 `attachment-fu --selftest` 确认环境正常。
2. 用单个文件测试：`attachment-fu test.pdf`。
3. 查看输出的 JSON 结构，理解各字段含义。
4. 尝试目录批量处理，注意 `--max-depth` 参数。
5. 使用 `--format csv` 导出为表格。

### 7.3 进阶路径（深度使用）

1. 结合 `--include-hash` 生成文件指纹，用于去重。
2. 编写脚本调用输出 JSON，对接数据库或自动化流程。
3. 处理 URL 模式时，注意设置合理的超时时间（默认 10 秒）。
4. 对大量文件（>1000）分批处理，避免内存溢出。
5. 自定义 MIME 映射表，覆盖特殊文件类型。

---

## 八、命令行接口

### 8.1 参数说明

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `input` | string | 是 | 文件路径、目录路径或 URL |
| `--format` | string | 否 | 输出格式：`json`（默认）或 `csv` |
| `--output` | string | 否 | 输出文件路径，默认输出到 stdout |
| `--max-depth` | int | 否 | 目录递归最大深度，默认 5 |
| `--include-hash` | flag | 否 | 计算并输出 SHA256 哈希 |
| `--selftest` | flag | 否 | 运行自检并退出 |
| `--version` | flag | 否 | 显示版本号并退出 |

### 8.2 退出码

| 退出码 | 含义 |
|--------|------|
| `0` | 成功 |
| `1` | 参数错误 |
| `2` | 处理过程中出现错误（详见错误码） |

---

## 九、用户协议

使用本 Skill 即表示您同意以下条款：

1. **责任承担**：使用者自行承担使用本 Skill 的全部责任。因使用本 Skill 导致的任何直接或间接损失，作者不承担任何责任。
2. **禁止反向工程**：不得对本 Skill 的代码、文档进行反向工程、反编译或试图提取源代码（除非适用法律允许）。
3. **合规使用**：使用者应确保使用场景符合当地法律法规，不得用于非法目的。
4. **无担保**：本 Skill 按"现状"提供，不作任何明示或暗示的担保。

<!-- user-agreement-injected -->

---

## 十、许可证（License）

MIT License

Copyright (c) 2026 独立技能工坊

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

<!-- professional-license-embedded -->
