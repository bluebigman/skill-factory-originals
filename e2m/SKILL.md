---
slug: e2m
name: e2m
displayName: 文档转制 结构化提取 内容复用
description: 将文件或链接转为结构化Markdown，保留关键信息，便于复用与检索。
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
trigger_words: ["e2m", "转markdown", "结构化提取", "文件转md", "链接转md", "内容转写", "文档结构化"]
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# e2m — 文档转制与结构化提取 Skill

## 一、能力边界（一页纸速查卡）

### 能做什么

| 能力项 | 说明 |
|--------|------|
| 文件转换 | 将 `./data` 目录下的常见文本类文件（`.txt`、`.md`、`.csv`、`.json`、`.html`、`.xml`、`.log` 等）转换为结构化 Markdown |
| 链接转换 | 将 HTTP/HTTPS 链接指向的网页内容抓取并转为结构化 Markdown |
| 信息保留 | 提取标题、段落、列表、表格、代码块、链接、元数据等关键信息 |
| 批量处理 | 遍历目录下所有支持的文件，逐个独立转换，单个失败不影响整体 |
| 备份机制 | 转换前自动创建 `./backup_YYYYMMDD` 目录，复制原始文件，便于追溯 |
| 占位符标记 | 无法确定的内容以统一格式占位，不猜测、不遗漏、可追踪 |

### 不能做什么

| 限制项 | 说明 |
|--------|------|
| 不支持二进制文件 | 图片、音视频、压缩包等二进制格式不在处理范围内 |
| 不执行 OCR | 扫描件、图片中的文字无法自动提取 |
| 不处理加密内容 | 需要密码或密钥的文件无法转换 |
| 不进行语义改写 | 仅做结构化整理，不改变原文语义和表述 |
| 不保证排版完美 | 复杂嵌套表格、极端样式可能丢失部分格式 |

### 适用对象

- 需要将零散文档整理为统一格式的团队或个人
- 需要将网页内容存档为本地 Markdown 的研究人员
- 需要批量处理日志、导出数据、配置文件的技术人员
- 需要将非结构化文本转为可检索结构的知识管理者

---

## 二、触发方式

### 触发词

直接使用以下任一方式唤起本 Skill：

- `e2m`
- `转markdown`
- `结构化提取`
- `文件转md`
- `链接转md`
- `内容转写`
- `文档结构化`

### 场景映射表

| 你说的话 | 实际意图 | 本 Skill 的行为 |
|----------|----------|-----------------|
| "帮我把这个文件夹里的文档都转成 md" | 批量转换本地文件 | 遍历 `./data`，逐个转换，输出到指定目录 |
| "把这个网页存成 markdown" | 链接转 md | 抓取链接内容，结构化输出 |
| "把这份日志整理一下" | 日志结构化 | 提取时间戳、级别、消息字段，转为表格 |
| "把这个 CSV 变成好看的文档" | 表格转 md | 保留表头和数据，转为 Markdown 表格 |
| "这个 HTML 文件帮我提取正文" | HTML 转 md | 剥离标签，保留文本结构和链接 |

---

## 三、标准流程

### 前置条件

| 条件 | 要求 |
|------|------|
| 输入目录 | 存在 `./data` 目录，内含待转换文件，或提供有效链接 |
| 输出目录 | 默认 `./output`，可通过 `--output-dir` 自定义 |
| 运行环境 | Python 3.8+，已安装必要的依赖库（如 `requests`、`beautifulsoup4`） |
| 编码设置 | 默认 UTF-8，可通过 `--encoding` 参数调整 |

### 执行步骤

#### 步骤 1：环境准备

```bash
# 检查依赖
pip install requests beautifulsoup4

# 创建输入目录（如不存在）
mkdir -p ./data
```

#### 步骤 2：执行转换

```bash
# 单文件转换
e2m ./data/example.txt

# 批量转换（默认行为）
e2m

# 自定义输出目录
e2m --output-dir ./converted

# 指定编码
e2m --encoding gbk

# 链接转 md
e2m "https://example.com/article"
```

#### 步骤 3：检查输出

转换完成后，检查输出目录：

```
./output/
├── example.md
├── article.md
└── conversion_report.json   # 转换报告，含成功/失败状态
```

#### 步骤 4：验证占位符

```bash
# 全局搜索占位符，确认是否有需要人工补充的内容
grep -r "需核实" ./output/
```

### 输出规范

| 输出项 | 规范 |
|--------|------|
| 文件名 | 与原文件同名，扩展名改为 `.md`；链接转换使用域名+标题命名 |
| 元数据 | 文件头包含来源、转换时间、原始格式 |
| 标题层级 | 按原文层级映射为 `#`、`##`、`###` |
| 表格 | 统一转为 Markdown 表格，空单元格用 `-` 填充 |
| 代码块 | 保留语言标记，无标记则用 `text` |
| 链接 | 保留原始 URL 和锚文本 |
| 占位符 | 格式为 `[需核实:字段名]`，置于原文位置 |

---

## 四、置信度门控

### 原则

1. **不猜测**：无法确定的内容一律使用占位符
2. **不遗漏**：占位符保留在原文位置，便于后续补充
3. **可追踪**：占位符统一格式，方便全局搜索定位

### 占位符使用场景

| 场景 | 占位符示例 | 说明 |
|------|------------|------|
| 图片无法识别 | `[需核实:图片内容]` | 保留图片位置，标注待人工补充 |
| 表格单元格为空 | `[需核实:单元格值]` | 不确定是空值还是缺失 |
| 编码无法识别 | `[需核实:乱码内容]` | 原文编码异常，无法还原 |
| 链接失效 | `[需核实:链接地址]` | 原链接无法访问，保留锚文本 |
| 日期格式不明 | `[需核实:日期]` | 无法判断是日月年还是年月日 |

### 置信度分级

| 级别 | 判定标准 | 处理方式 |
|------|----------|----------|
| 高置信度 | 内容完整、格式清晰、无歧义 | 直接转换，不做标记 |
| 中置信度 | 内容可读但存在少量不确定项 | 转换 + 占位符标记 |
| 低置信度 | 内容残缺、格式混乱、编码异常 | 转换 + 占位符标记 + 在转换报告中标注 warning |

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| `E001` | 文件不存在 | "未找到指定文件，请检查路径" | 确认文件路径，检查 `./data` 目录 |
| `E002` | 文件格式不支持 | "该文件类型不在支持范围内" | 查看能力边界，确认文件是否为文本类 |
| `E003` | 编码无法识别 | "无法识别文件编码，请指定 --encoding" | 尝试常见编码（UTF-8、GBK、GB2312） |
| `E004` | 链接无法访问 | "链接请求失败，请检查网络或 URL" | 确认链接有效性，检查网络连接 |
| `E005` | 内容为空 | "文件内容为空，无法转换" | 检查源文件是否为空或仅有空白字符 |
| `E006` | 输出目录不可写 | "无法写入输出目录，请检查权限" | 确认目录存在且有写权限 |
| `E007` | 转换超时 | "转换耗时过长，已终止" | 检查文件大小，考虑拆分处理 |
| `E008` | 内存不足 | "内存占用过高，转换失败" | 关闭其他程序，或分批次处理 |

---

## 六、FAQ 反模式

### 常见坑与反模式对照

| 常见错误 | 反模式（错误做法） | 正模式（正确做法） |
|----------|-------------------|-------------------|
| 忽略备份 | 直接转换，不保留原始文件 | 先备份到 `./backup_YYYYMMDD`，再转换 |
| 猜测内容 | 不确定的内容自行编造 | 使用 `[需核实:字段]` 占位，留待人工确认 |
| 中断批量 | 一个文件失败就停止全部 | 单个失败记录错误，继续处理后续文件 |
| 忽略编码 | 默认 UTF-8 硬转 | 先检测编码，必要时指定 `--encoding` |
| 不检查输出 | 转换完不验证直接使用 | 检查占位符、对比原文、查看转换报告 |
| 覆盖原文件 | 转换后直接覆盖源文件 | 输出到独立目录，保留源文件 |

### 补充说明

- **批量处理时**：建议先跑一个文件验证效果，再全量执行
- **链接转换时**：注意目标网站的反爬策略，必要时设置请求头
- **大文件处理时**：超过 10MB 的文件建议拆分或使用流式处理

---

## 七、渐进式披露

### 速查卡（30 秒上手）

```
1. 确保 ./data 目录存在，放入待转换文件
2. 运行 e2m
3. 检查 ./output 目录下的 .md 文件
4. 搜索 [需核实: 占位符，补充缺失信息
```

### 分层次阅读路径

#### 新手路径（首次使用）

1. 阅读「一、能力边界」了解能做什么
2. 阅读「三、标准流程」中的步骤 1-2
3. 执行一次单文件转换，观察输出

#### 进阶路径（日常使用）

1. 阅读「三、标准流程」完整流程
2. 阅读「四、置信度门控」理解占位符机制
3. 阅读「五、错误码体系」掌握异常处理
4. 阅读「六、FAQ 反模式」避免常见错误

#### 专家路径（深度定制）

1. 自定义 `--encoding`、`--output-dir` 等参数
2. 结合脚本实现自动化转换流程
3. 根据业务需求扩展输出模板

---

## 八、参数参考

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--input-dir` | `./data` | 输入目录 |
| `--output-dir` | `./output` | 输出目录 |
| `--encoding` | `utf-8` | 文件编码 |
| `--backup` | `true` | 是否创建备份 |
| `--timeout` | `30` | 链接请求超时时间（秒） |
| `--max-size` | `10MB` | 单文件大小上限 |
| `--selftest` | - | 运行自检 |
| `--version` | - | 显示版本号 |

---

## 用户协议

**使用本 Skill 即表示您同意以下条款：**

1. **责任承担**：使用者应自行承担使用本 Skill 的全部责任。因使用本 Skill 导致的任何直接或间接损失，Skill 作者不承担任何责任。

2. **禁止反向工程**：不得对本 Skill 进行反向工程、反编译、反汇编或试图提取源代码（适用法律允许的除外）。

3. **合规使用**：使用者应确保使用本 Skill 的行为符合当地法律法规及所在组织的政策要求。

4. **无担保声明**：本 Skill 按"现状"提供，不附带任何明示或暗示的担保，包括但不限于适销性、特定用途适用性和非侵权保证。

5. **修改与分发**：使用者可以修改本 Skill 用于个人或内部用途，但不得将修改后的版本作为原创作品对外分发。

<!-- user-agreement-injected -->

---

## 许可证（License）

本 Skill 采用 MIT 许可证发布：

```
MIT License

Copyright (c) 2024 林墨

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
