---
slug: filetomarkdown
name: filetomarkdown
displayName: 文档转写 格式转换 内容提取
description: 将文件或链接转为结构化Markdown，保留关键信息并标注置信度。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 林墨
agent_created: true
trigger_words: ["filetomarkdown","转Markdown","文档转写","格式转换","内容提取","文件转MD","链接转MD"]
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# filetomarkdown — 文档转写与结构化提取

本 Skill 由 AI 辅助生成，仅供参考。使用前请确认输入文件来源合法，且不涉及敏感或受版权保护的内容。

---

## 一、能力边界（一页纸速查卡）

### 1.1 能做什么

| 能力项 | 说明 | 示例 |
|--------|------|------|
| 单文件转换 | 将单个文件转为 Markdown | `filetomarkdown report.pdf` |
| 批量转换 | 将目录下所有支持的文件批量转换 | `filetomarkdown ./docs/ --batch` |
| 链接抓取 | 将网页链接内容转为 Markdown | `filetomarkdown https://example.com/article` |
| 置信度标注 | 对提取的每个信息块标注可信程度 | `[置信度: 0.92]` |
| 自定义输出目录 | 指定输出文件的存放位置 | `--output ./converted/` |
| 自检模式 | 验证工具链是否正常 | `--selftest` |

### 1.2 不能做什么

| 限制项 | 说明 |
|--------|------|
| 不处理加密文件 | 需要先解密才能转换 |
| 不识别手写内容 | 仅支持印刷体文本提取 |
| 不保留复杂排版 | 表格、多栏布局可能简化处理 |
| 不执行语义理解 | 仅做结构化提取，不做摘要或翻译 |
| 不保证 100% 准确 | 低置信度内容需人工复核 |

### 1.3 适用对象

- 需要将 PDF、Word、HTML 等格式转为 Markdown 的文档工作者
- 需要从网页中提取结构化内容的调研人员
- 需要批量整理文档库的运维或数据工程师

---

## 二、触发方式

### 2.1 触发词

| 触发词 | 使用场景 |
|--------|----------|
| `filetomarkdown` | 直接调用工具 |
| `转Markdown` | 口语化指令，如"帮我把这个文件转Markdown" |
| `文档转写` | 需要将文档内容重新整理为 Markdown 格式 |
| `格式转换` | 泛指格式转换需求 |
| `内容提取` | 需要从文件中提取关键信息 |
| `文件转MD` | 简短指令 |
| `链接转MD` | 将网页链接转为 Markdown |

### 2.2 场景映射表

| 用户说 | 工具执行 |
|--------|----------|
| "把这个 PDF 转成 Markdown" | `filetomarkdown 文件.pdf` |
| "把整个文件夹里的文档都转一下" | `filetomarkdown ./文件夹/ --batch` |
| "这个网页内容帮我存下来" | `filetomarkdown https://...` |
| "转换结果放哪了？" | 默认输出到当前目录，文件名为 `<原文件名>_converted.md` |

---

## 三、标准操作流程

### 3.1 前置条件

| 条件 | 要求 |
|------|------|
| 输入文件 | 存在且可读，编码建议为 UTF-8（非 UTF-8 需先转换） |
| 网络（链接模式） | 目标链接可访问，且非登录墙内容 |
| 磁盘空间 | 至少为输入文件大小的 2 倍 |
| 工具链 | 已安装 filetomarkdown，可通过 `--version` 验证 |

### 3.2 执行步骤

**单文件转换流程：**

1. 将待转换文件放入当前工作目录
2. 打开终端，运行：
   ```bash
   filetomarkdown 文件名.扩展名
   ```
3. 等待执行完成，观察终端输出（成功/警告/错误）
4. 检查当前目录下生成的 `<文件名>_converted.md` 文件
5. 打开输出文件，核对置信度标注：
   - 置信度 ≥ 0.7：可直接使用
   - 置信度 < 0.7：需人工复核对应段落

**批量转换流程：**

1. 确认目标目录下所有文件均为支持的格式
2. 运行：
   ```bash
   filetomarkdown ./目标目录/ --batch
   ```
3. 批量模式下每个文件独立生成 `_converted.md` 文件
4. 批量模式不中断执行，单个文件失败会记录错误并继续

**链接转换流程：**

1. 确认链接可公开访问
2. 运行：
   ```bash
   filetomarkdown https://example.com/article
   ```
3. 工具会抓取页面正文内容，去除导航、广告等噪声

### 3.3 输出规范

| 输出项 | 规范 |
|--------|------|
| 文件名 | `<原文件名>_converted.md` |
| 编码 | UTF-8 |
| 标题层级 | 按原文结构映射为 H1-H6 |
| 表格 | 保留为 Markdown 表格 |
| 图片 | 保留引用路径，不嵌入图片数据 |
| 置信度标注 | 每个段落末尾标注 `[置信度: 0.xx]` |
| 低置信度标记 | 置信度 < 0.7 的内容前加 `> ⚠️ 需人工复核` |

**输出文件结构示例：**

```markdown
# 原文档标题

> 来源: 文件名.扩展名
> 转换时间: 2025-01-15 14:30:22

## 第一节

正文内容... [置信度: 0.95]

## 第二节

> ⚠️ 需人工复核

部分模糊内容... [置信度: 0.42]
```

---

## 四、置信度门控

### 4.1 置信度评分规则

| 评分范围 | 含义 | 处理建议 |
|----------|------|----------|
| 0.90 - 1.00 | 高置信度，文本清晰且结构完整 | 直接使用 |
| 0.70 - 0.89 | 中等置信度，可能存在轻微识别误差 | 快速浏览确认 |
| 0.40 - 0.69 | 低置信度，文本模糊或结构混乱 | 需人工复核 |
| 0.00 - 0.39 | 极低置信度，内容基本不可用 | 建议重新获取源文件 |

### 4.2 信息不足时的处理

当提取的信息不完整或无法确认时，工具会输出占位符而非编造内容：

- 缺失字段：`[需核实: 作者姓名]`
- 无法识别的段落：`[需核实: 本段内容无法识别，请参考原文件]`
- 链接失效：`[需核实: 链接无法访问，已跳过]`

**禁止行为：** 工具不会猜测缺失信息，也不会用相似内容填充空白。

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| E001 | 文件不存在 | `错误: 找不到文件 xxx` | 检查文件名和路径是否正确 |
| E002 | 文件格式不支持 | `错误: 不支持的文件格式 .xyz` | 先转换为支持的格式（PDF、DOCX、HTML、TXT、MD） |
| E003 | 文件编码错误 | `错误: 无法解析文件编码` | 使用 `iconv` 或文本编辑器将文件转为 UTF-8 |
| E004 | 链接无法访问 | `错误: 链接返回 404` | 检查链接是否有效，或改用文件下载方式 |
| E005 | 输出目录不可写 | `错误: 无法写入输出目录` | 检查目录权限，或使用 `--output` 指定可写目录 |
| E006 | 批量模式中断 | `错误: 批量处理在第 N 个文件中断` | 查看错误日志，单独处理失败的文件 |
| E007 | 磁盘空间不足 | `错误: 磁盘空间不足，需要至少 X MB` | 清理磁盘空间后重试 |
| E008 | 内部错误 | `错误: 发生未知错误，请运行 --selftest` | 运行自检，确认工具链完整性 |

---

## 六、FAQ 反模式

### 6.1 常见坑

| 坑 | 反模式（错误做法） | 正模式（正确做法） |
|----|-------------------|-------------------|
| 编码问题 | 直接转换 GBK 编码文件，导致乱码 | 先转为 UTF-8 再转换 |
| 批量失败 | 批量模式中一个文件失败就终止全部 | 使用 `--batch` 的容错机制，单个失败不影响其他 |
| 置信度误判 | 忽略低置信度标记直接使用 | 对置信度 < 0.7 的内容逐段复核 |
| 链接失效 | 不检查链接可访问性直接转换 | 先确认链接有效，或先下载为本地文件 |
| 输出覆盖 | 重复转换同名文件，覆盖原输出 | 使用 `--output` 指定不同目录，或先备份 |

### 6.2 反模式对照表

| 场景 | 错误做法 | 正确做法 |
|------|----------|----------|
| 需要转换 50 个文件 | 手动逐个执行 50 次 | 使用 `--batch` 批量处理 |
| 输出文件找不到 | 在系统其他目录搜索 | 默认输出在当前目录，文件名含 `_converted` 后缀 |
| 转换结果不完整 | 认为是工具缺陷 | 检查原文件是否清晰，低置信度内容需人工补充 |
| 需要自定义输出格式 | 修改工具源码 | 使用 `--output` 指定目录，或调整输出模板 |

---

## 七、渐进式披露

### 7.1 速查卡（30 秒上手）

```bash
# 单文件转换
filetomarkdown 文件.pdf

# 批量转换
filetomarkdown ./目录/ --batch

# 链接转换
filetomarkdown https://example.com

# 指定输出目录
filetomarkdown 文件.pdf --output ./结果/

# 自检
filetomarkdown --selftest
```

### 7.2 分层次阅读路径

**新手路径（首次使用）：**

1. 阅读「一、能力边界」了解适用范围
2. 按「三、标准操作流程」的步骤 1-2 完成一次单文件转换
3. 查看输出文件，对照「3.3 输出规范」检查格式
4. 遇到问题查「五、错误码体系」

**进阶路径（熟练使用）：**

1. 掌握批量模式：`filetomarkdown ./dir/ --batch`
2. 自定义输出目录：`--output ./custom_dir/`
3. 处理特殊格式：先转换编码为 UTF-8，再执行转换
4. 结合 CI/CD：将转换命令写入自动化流水线，配合 `--selftest` 做回归测试
5. 二次开发：修改输出模板，调整置信度阈值（默认 0.7）

---

## 八、参数参考

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `--batch` | 布尔 | false | 批量处理目录下所有支持的文件 |
| `--output` | 字符串 | 当前目录 | 指定输出目录 |
| `--selftest` | 布尔 | false | 运行自检，验证工具链完整性 |
| `--version` | 布尔 | false | 显示版本信息 |
| `--confidence-threshold` | 浮点数 | 0.7 | 置信度阈值，低于此值标记为需复核 |
| `--template` | 字符串 | 默认模板 | 指定输出模板文件路径 |

---

## 九、用户协议

使用本 Skill 即表示您同意以下条款：

1. **责任承担**：使用者自行承担使用本 Skill 产生的全部责任。因使用本工具导致的任何直接或间接损失，作者不承担任何责任。
2. **合法使用**：使用者须确保输入文件来源合法，不侵犯第三方版权、隐私权或其他合法权益。
3. **禁止反向工程**：使用者不得对本 Skill 进行反向工程、反编译、破解或试图提取底层算法。
4. **服务终止**：本 Skill 作者保留随时更新、修改或终止本 Skill 分发的权利，恕不另行通知。
5. **内容免责**：本 Skill 输出的内容仅供参考，不构成任何专业建议。关键决策请以原始文件为准。

<!-- user-agreement-injected -->

---

## 十、许可证（License）

本 Skill 采用 MIT 许可证发布。

### MIT License

```
MIT License

Copyright (c) 2025 林墨

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
