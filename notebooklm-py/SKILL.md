---
slug: notebooklm-py
name: notebooklm-py
displayName: 知识库笔记 结构化转换 批量处理
description: 将用户数据、文件或URL转换为结构化结果，支持批量处理与置信度标注。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 技能工坊
agent_created: true
trigger_words: ["notebooklm py", "知识库笔记", "笔记处理", "结构化转换", "批量处理", "笔记整理", "数据标注"]
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# notebooklm-py 技能文档

## 一、能力边界：一页纸速查卡

### 1.1 能做什么

| 能力项 | 说明 | 适用场景 |
|--------|------|----------|
| 文件转结构化 | 将 Markdown、TXT、CSV 等文本文件转换为带字段的 JSON 结构 | 笔记归档、数据清洗 |
| URL 内容提取 | 抓取网页正文并转为结构化条目 | 网页收藏、文章摘录 |
| 批量处理 | 对同一目录下多个文件依次执行转换 | 批量整理历史笔记 |
| 置信度标注 | 对每个输出条目附加置信度评分（0-1） | 需要评估转换可靠性的场景 |
| 试运行模式 | 先处理单个样本，核对输出格式后再全量执行 | 首次使用或调整参数时 |

### 1.2 不能做什么

| 限制项 | 说明 |
|--------|------|
| 不支持二进制文件 | PDF、DOCX、图片等需先转为文本格式 |
| 不执行语义理解 | 仅做结构化转换，不判断内容对错 |
| 不修改原始文件 | 所有操作只读，输出另存为新文件 |
| 不处理加密内容 | 需要解密的文件需提前处理 |

### 1.3 适用对象

- 需要将零散笔记整理为统一格式的个人用户
- 需要批量处理文本数据的研究人员
- 需要将网页内容存档的资讯收集者

---

## 二、触发方式

### 2.1 触发词

使用以下任一短语即可激活本技能：

- `notebooklm py`
- `知识库笔记`
- `笔记处理`
- `结构化转换`
- `批量处理`
- `笔记整理`
- `数据标注`

### 2.2 场景映射表

| 用户说（大白话） | 技能响应 |
|------------------|----------|
| "帮我把这些笔记整理一下" | 扫描当前目录文本文件，执行结构化转换 |
| "这个网页内容能存下来吗" | 提取 URL 正文，转为结构化条目 |
| "我有一堆 txt 文件要处理" | 进入批量处理模式，逐文件转换 |
| "先跑一个看看效果" | 进入试运行模式，处理单个样本 |

---

## 三、标准流程

### 3.1 前置条件

| 条件 | 要求 | 检查方式 |
|------|------|----------|
| 文件格式 | .md / .txt / .csv / .json | 查看文件扩展名 |
| 文件位置 | 与执行目录相同 | `ls` 确认 |
| 命名规范 | 建议使用 `前缀_序号.扩展名` 格式 | 目视检查 |
| 原始备份 | 建议先复制一份到 `backup/` 子目录 | `mkdir backup && cp *.txt backup/` |

### 3.2 执行步骤

1. **环境确认**：运行 `notebooklm py --version` 检查版本可用性。
2. **单样本试运行**：选择一个有代表性的文件，执行 `notebooklm py 样本文件.txt`，观察输出结构。
3. **字段核对**：检查输出 JSON 中的字段是否完整，重点核对 `title`、`content`、`source`、`timestamp` 四个核心字段。
4. **批量执行**：确认无误后，运行 `notebooklm py --batch` 处理当前目录全部文本文件。
5. **结果校验**：随机抽取 3-5 个输出条目，与原始文件比对关键字段。
6. **备份留存**：确认结果正确后，将原始文件移入 `backup/` 目录保存。

### 3.3 输出规范

每个输入文件对应一个输出 JSON 文件，命名规则为 `原文件名_structured.json`。

输出结构示例：

```json
{
  "entries": [
    {
      "id": "001",
      "title": "笔记标题",
      "content": "正文内容",
      "source": "文件名或URL",
      "timestamp": "2024-01-15T10:30:00Z",
      "confidence": 0.95,
      "tags": ["标签1", "标签2"]
    }
  ],
  "meta": {
    "total_entries": 1,
    "processing_time_ms": 1234,
    "tool_version": "1.0.0"
  }
}
```

---

## 四、置信度门控

### 4.1 置信度评分规则

| 评分区间 | 含义 | 处理建议 |
|----------|------|----------|
| 0.90 - 1.00 | 高置信度，字段完整 | 直接使用 |
| 0.70 - 0.89 | 中等置信度，个别字段缺失 | 人工复核缺失字段 |
| 0.50 - 0.69 | 低置信度，多处不确定 | 对照原文逐项检查 |
| < 0.50 | 极低置信度 | 建议重新处理或人工录入 |

### 4.2 信息不足处理

当遇到无法确定的内容时，输出 `[需核实:字段名]` 占位符，不进行猜测性填充。例如：

```json
{
  "title": "[需核实:标题]",
  "content": "正文内容完整",
  "confidence": 0.65
}
```

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| E001 | 文件不存在 | "未找到指定文件，请检查路径" | 确认文件名及路径后重试 |
| E002 | 文件格式不支持 | "仅支持 .md/.txt/.csv/.json 格式" | 转换文件格式后重试 |
| E003 | 目录为空 | "当前目录无待处理文件" | 将文件移入当前目录 |
| E004 | 输出字段异常 | "输出结构不完整，请检查源文件" | 查看源文件是否有空行或乱码 |
| E005 | 批量处理中断 | "批量处理在第 N 个文件处中断" | 从第 N+1 个文件继续执行 |
| E006 | URL 无法访问 | "无法获取网页内容，请检查链接" | 确认 URL 有效性或改用本地文件 |

---

## 六、FAQ 反模式

### 6.1 常见坑

| 坑 | 反模式示例 | 正确做法 |
|----|------------|----------|
| 跳过试运行 | 直接对全量数据执行 | 先跑单个样本，确认格式 |
| 忽略备份 | 处理前不保留原始文件 | 先复制到 backup/ 目录 |
| 盲目信任输出 | 不校验直接使用结果 | 随机抽查 3-5 条比对 |
| 混用文件格式 | 同一目录放多种格式 | 分目录存放，分批处理 |
| 忽略置信度 | 低置信度条目直接采用 | 按 4.1 规则人工复核 |

### 6.2 反模式对照表

| 错误习惯 | 后果 | 替代方案 |
|----------|------|----------|
| 修改原始文件后再处理 | 数据丢失风险 | 始终使用副本 |
| 处理超大批量（>1000 文件） | 内存溢出 | 分批处理，每批 100 个 |
| 依赖默认参数不调整 | 输出不符合预期 | 先试运行，按需调整 |

---

## 七、渐进式披露

### 7.1 速查卡（新手必读）

1. 把文件放当前目录
2. 先跑一个：`notebooklm py 文件名.txt`
3. 看输出对不对
4. 对就跑全部：`notebooklm py --batch`
5. 抽查结果，完事

### 7.2 进阶路径

**新手路径**（首次使用）：
- 阅读第 3.2 节执行步骤
- 按速查卡操作一遍
- 遇到问题查第 5 节错误码

**进阶路径**（熟练用户）：
- 自定义输出字段（修改配置文件）
- 结合其他工具做数据清洗
- 编写脚本自动化调用

**专家路径**（深度集成）：
- 将输出接入数据库
- 开发定时批量处理任务
- 自定义置信度阈值

---

## 八、参数配置

### 8.1 命令行参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `--selftest` | 标志 | 无 | 运行自检，验证环境 |
| `--version` | 标志 | 无 | 显示版本号 |
| `--batch` | 标志 | 无 | 批量处理模式 |
| `--output-dir` | 字符串 | 当前目录 | 输出目录 |
| `--confidence-threshold` | 浮点数 | 0.5 | 置信度阈值 |
| `--max-file-size` | 整数 | 1048576 | 单文件大小上限（字节） |

### 8.2 边界值说明

- 单文件大小上限：1MB（默认），超过需调整参数
- 批量处理数量：建议单批不超过 100 个文件
- 置信度阈值范围：0.0 - 1.0，低于阈值输出 `[需核实]` 占位

---

## 九、用户协议

<!-- user-agreement-injected -->

使用本 Skill 即表示您同意以下条款：

1. **责任承担**：使用者自行承担使用本 Skill 产生的全部责任。包括但不限于数据处理结果、信息准确性、以及因使用本工具导致的任何直接或间接损失。
2. **禁止反向工程**：不得对本 Skill 进行反向工程、反编译、破解或试图提取源代码。
3. **合规使用**：使用者应确保使用本 Skill 的行为符合当地法律法规及平台规定。
4. **无担保声明**：本 Skill 按"现状"提供，不附带任何明示或暗示的担保。

---

## 十、许可证（License）

<!-- professional-license-embedded -->

MIT License

Copyright (c) 2024 技能工坊

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

---

*本 Skill 由 AI 辅助生成，仅供参考。使用前请阅读相关文档。*
