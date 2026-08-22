---
slug: attachment-fu
name: attachment-fu
displayName: 附件归档 元数据提取 文件清单生成
description: 将文件、数据或URL转为结构化附件记录，提取元数据并输出JSON/CSV。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 林栖
agent_created: true
trigger_words: ["附件整理","文件转记录","元数据提取","附件归档","文件清单生成","文件登记","附件索引"]
---

> 本内容由 AI 生成，仅供学习参考 <!-- ai-generated-notice -->

# attachment-fu 技能文档

## 一、能力边界（一页纸速查卡）

### 1.1 能做什么

| 能力项 | 说明 | 示例 |
|--------|------|------|
| 单文件转记录 | 将单个文件转为结构化 JSON 记录 | `attachment-fu report.pdf` |
| 目录批量处理 | 递归扫描目录下所有文件 | `attachment-fu ./docs --recursive` |
| 元数据提取 | 提取文件名、大小、类型、修改时间等 | 输出字段见 3.3 节 |
| URL 抓取 | 将远程资源转为附件记录 | `attachment-fu https://example.com/a.png` |
| 格式导出 | 支持 JSON 与 CSV 两种输出格式 | `--format csv` |
| 文件指纹 | 计算哈希值用于去重 | `--include-hash` |
| 自检模式 | 验证环境可用性 | `attachment-fu --selftest` |

### 1.2 不能做什么

- 不修改原始文件内容，只做读取与记录
- 不执行文件格式转换（如 PDF→Word）
- 不识别图片中的文字（OCR 不在范围内）
- 不处理加密文件或需要密码的压缩包
- 不保证 URL 资源的永久可访问性

### 1.3 适用对象

- 需要批量整理本地文件的个人用户
- 需要生成文件清单的运维或项目管理人员
- 需要将附件信息导入数据库的开发者
- 需要定期扫描目录生成变更报告的自动化流程

---

## 二、触发方式

### 2.1 触发词

当用户表达以下意图时，可调用本技能：

| 用户说（大白话） | 触发词匹配 | 实际动作 |
|-----------------|-----------|---------|
| "帮我把这个文件夹里的文件都列出来" | 附件整理 / 文件清单生成 | 目录批量扫描 |
| "这个 PDF 的信息提取一下" | 文件转记录 / 元数据提取 | 单文件转 JSON |
| "把附件归档到数据库" | 附件归档 | 生成 JSON 供导入 |
| "看看这两个文件是不是重复的" | 文件清单生成 + --include-hash | 哈希比对 |

### 2.2 命令行入口

```
附件整理
文件转记录
元数据提取
附件归档
文件清单生成
--selftest
--version
```

---

## 三、标准流程

### 3.1 前置条件

| 条件 | 要求 | 验证方式 |
|------|------|---------|
| 输入路径存在 | 文件或目录必须真实存在 | `ls <path>` 或 `test -e <path>` |
| 读取权限 | 当前用户可读目标路径 | `test -r <path>` |
| 网络连通（URL 模式） | 目标 URL 可访问 | `curl -I <url>` |
| 环境就绪 | 工具已正确安装 | `attachment-fu --selftest` |

### 3.2 执行步骤

**第一步：环境自检**

```bash
attachment-fu --selftest
```

预期输出：`OK` 或列出缺失依赖项。

**第二步：单文件测试**

```bash
attachment-fu test.pdf
```

**第三步：查看 JSON 输出**

观察各字段含义，确认元数据提取正确。

**第四步：目录批量处理**

```bash
attachment-fu ./docs --recursive
```

**第五步：导出 CSV**

```bash
attachment-fu ./docs --recursive --format csv
```

### 3.3 输出规范

单文件 JSON 输出示例：

```json
{
  "file": "test.pdf",
  "path": "/home/user/docs/test.pdf",
  "size_bytes": 204800,
  "mime_type": "application/pdf",
  "modified_at": "2025-01-15T10:30:00Z",
  "hash_sha256": "a3f5...（64位十六进制）"
}
```

CSV 输出列头：

```
file,path,size_bytes,mime_type,modified_at,hash_sha256
```

---

## 四、置信度门控

当以下信息缺失时，输出 `[需核实:字段名]` 占位符，**不编造数据**：

| 场景 | 占位符示例 |
|------|-----------|
| 文件修改时间无法读取 | `[需核实:modified_at]` |
| MIME 类型无法识别 | `[需核实:mime_type]` |
| URL 抓取超时 | `[需核实:content]` |
| 哈希计算失败 | `[需核实:hash_sha256]` |

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|---------|---------|
| E001 | 路径不存在 | "指定的路径不存在，请检查输入" | 确认路径拼写，使用绝对路径 |
| E002 | 权限不足 | "当前用户无读取权限" | 使用 `chmod` 调整权限或以 sudo 运行 |
| E003 | URL 超时 | "远程资源响应超时（默认 10 秒）" | 使用 `--timeout 30` 延长超时 |
| E004 | 输出目录不可写 | "无法写入输出文件" | 检查输出目录权限或更换路径 |
| E005 | 内存溢出 | "文件数量过多，处理失败" | 分批处理，每次不超过 1000 个文件 |
| E006 | 自定义 MIME 映射文件格式错误 | "映射文件解析失败" | 检查 JSON/YAML 格式，参考文档示例 |

---

## 六、FAQ 反模式

### 6.1 常见坑与反模式对照

| 坑 | 反模式（错误做法） | 正模式（推荐做法） |
|----|-------------------|-------------------|
| 大量文件一次性处理 | 直接扫描 5000 个文件导致内存溢出 | 分批处理，每批 ≤1000 个 |
| URL 抓取无超时 | 不设置超时，程序挂起 | 设置 `--timeout 10`（默认） |
| 特殊文件类型识别错误 | 依赖系统 MIME 库，识别不准 | 自定义 MIME 映射文件覆盖 |
| 重复文件未发现 | 仅比较文件名 | 使用 `--include-hash` 比对内容 |
| 输出格式不匹配 | 手动改 JSON 为 CSV | 使用 `--format csv` 直接导出 |

### 6.2 进阶使用建议

- **去重场景**：结合 `--include-hash` 生成文件指纹，用脚本比对哈希值。
- **数据库对接**：编写脚本解析 JSON 输出，批量插入数据库表。
- **CI/CD 集成**：在流水线中调用本工具，自动生成构建产物清单。
- **定时扫描**：配合 cron 定时任务，定期扫描目录并生成变更报告。

---

## 七、渐进式披露

### 7.1 速查卡（30 秒上手）

```bash
# 单文件
attachment-fu test.pdf

# 目录递归
attachment-fu ./docs --recursive

# 导出 CSV
attachment-fu ./docs --recursive --format csv

# 带哈希
attachment-fu ./docs --recursive --include-hash
```

### 7.2 新手路径（5 分钟）

1. 运行 `--selftest` 确认环境
2. 用单个文件测试，理解 JSON 字段
3. 尝试目录批量处理
4. 导出 CSV 用 Excel 打开查看

### 7.3 进阶路径（30 分钟）

1. 编写自定义 MIME 映射文件，覆盖内部文件格式
2. 开发后处理脚本，将 JSON 输出导入数据库
3. 集成到 CI/CD 流程，自动生成文件清单
4. 结合定时任务，定期扫描目录并生成变更报告

---

## 八、参数参考表

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `--recursive` | 布尔 | false | 递归扫描子目录 |
| `--format` | 字符串 | json | 输出格式：json 或 csv |
| `--include-hash` | 布尔 | false | 计算 SHA-256 哈希 |
| `--timeout` | 整数 | 10 | URL 抓取超时（秒） |
| `--mime-map` | 路径 | 无 | 自定义 MIME 映射文件 |
| `--output` | 路径 | 标准输出 | 输出文件路径 |
| `--batch-size` | 整数 | 1000 | 批处理文件数量上限 |

---

## 九、用户协议

**使用本 Skill 即表示您同意以下条款：**

1. **责任承担**：使用者自行承担使用本 Skill 的全部责任。因使用本 Skill 导致的任何直接或间接损失，作者不承担任何责任。
2. **禁止反向工程**：不得对本 Skill 的代码、文档进行反向工程、反编译或试图提取源代码（除非适用法律允许）。
3. **合规使用**：使用者应确保使用场景符合当地法律法规，不得用于非法目的。
4. **无担保**：本 Skill 按"现状"提供，不作任何明示或暗示的担保。

<!-- user-agreement-injected -->

---

## 十、许可证（License）

本 Skill 采用 MIT 许可证发布。

```
MIT License

Copyright (c) 2025 林栖

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
