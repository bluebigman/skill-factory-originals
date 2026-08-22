---
slug: pdf-inspector
name: pdf-inspector
displayName: PDF文档体检与路由决策
description: 快速识别PDF类型（扫描/文本），抽取文本内容，为后续处理提供智能路由决策。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: SkillForge Studio
agent_created: true
trigger_words: ["pdf-inspector", "PDF类型检测", "PDF文本提取", "扫描版识别", "PDF体检", "PDF文档分析", "PDF内容识别"]
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# PDF Inspector — PDF文档体检与路由决策

## 一、能力边界（一页纸速查卡）

### ✅ 能做什么

| 能力项 | 说明 | 输出形式 |
|--------|------|----------|
| 类型判定 | 区分文本型PDF、扫描版PDF、混合型PDF | `document_type` 字段 |
| 文本抽取 | 提取PDF内嵌文本层内容 | 纯文本字符串 |
| 置信度评估 | 基于文本覆盖率计算判定可信度 | `confidence` 字段（0~1） |
| 路由建议 | 给出后续处理路径建议 | `routing_suggestion` 字段 |
| 批量体检 | 支持多文件顺序处理 | JSON数组 |

### ❌ 不能做什么

| 限制项 | 说明 |
|--------|------|
| OCR识别 | 本工具不执行光学字符识别，仅检测"是否有文本层" |
| 加密破解 | 无法绕过密码保护，需用户提供密码 |
| 图像分析 | 不识别图片内容、图表、手写文字 |
| 格式转换 | 不输出Word/HTML等其他格式 |
| 修复损坏文件 | 文件结构损坏时仅报错，不尝试修复 |

### 🎯 适用对象

- 需要批量判断PDF类型的文档管理员
- 搭建文档处理流水线的开发者
- 需要快速区分"可搜索PDF"与"图片PDF"的办公人员

---

## 二、触发方式与场景映射

| 触发词/短语 | 典型场景 |
|-------------|----------|
| "pdf-inspector" | 直接调用工具 |
| "PDF类型检测" | 想知道一个PDF是文字版还是扫描版 |
| "PDF文本提取" | 需要从PDF中取出文字内容 |
| "扫描版识别" | 判断PDF是否为纯图片扫描件 |
| "PDF体检" | 批量检查一批PDF的质量和类型 |
| "这个PDF能搜索吗" | 判断PDF是否有文本层（可搜索性） |
| "帮我看看这个PDF" | 快速了解PDF基本属性 |

---

## 三、标准执行流程

### 前置条件

- 输入文件为 `.pdf` 格式，或可访问的PDF文件URL
- 文件大小建议不超过 200MB（超出可能超时）
- 若文件加密，需准备密码

### 执行步骤

#### Step 1：加载文件

```
输入：文件路径 或 URL
操作：读取文件字节流 → 使用 pypdf.PdfReader 加载
```

#### Step 2：基础校验

| 检查项 | 通过条件 | 失败处理 |
|--------|----------|----------|
| 文件格式 | 文件头为 `%PDF` | 返回 `error_code: 1001` |
| 文件完整性 | 可正常解析交叉引用表 | 返回 `error_code: 1002` |
| 加密状态 | 无密码或密码正确 | 返回 `error_code: 1003` |

#### Step 3：逐页文本提取

```
遍历每一页：
  - 尝试提取文本内容
  - 记录该页是否有非空文本
  - 统计：有文本页数 / 总页数
```

#### Step 4：类型判定与置信度计算

| 文本覆盖率 | 判定类型 | 置信度 |
|-----------|----------|--------|
| ≥ 0.95 | `text_layer` | 覆盖率本身 |
| ≤ 0.05 | `scanned` | 1 - 覆盖率 |
| 0.05 ~ 0.95 | `mixed` | 覆盖率与0.5的距离归一化 |

置信度公式：
- `text_layer`: `confidence = coverage`
- `scanned`: `confidence = 1 - coverage`
- `mixed`: `confidence = 1 - (|coverage - 0.5| * 2)`

#### Step 5：输出检测报告

```json
{
  "file_path": "/path/to/document.pdf",
  "total_pages": 12,
  "pages_with_text": 11,
  "text_coverage": 0.9167,
  "document_type": "text_layer",
  "confidence": 0.9167,
  "routing_suggestion": "direct_parse",
  "extracted_text_preview": "前500字符预览...",
  "error_code": null,
  "error_message": null
}
```

### 输出规范

| 字段 | 类型 | 说明 |
|------|------|------|
| `document_type` | string | `text_layer` / `scanned` / `mixed` |
| `confidence` | float | 0~1，越高越可信 |
| `routing_suggestion` | string | `direct_parse` / `ocr_required` / `hybrid_processing` |
| `error_code` | int/null | 无错误时为 `null` |

---

## 四、置信度门控机制

### 何时触发"需核实"占位

| 场景 | 处理方式 |
|------|----------|
| 置信度 < 0.7 且用户要求"直接处理" | 输出 `[需核实:document_type]` 占位，不给出确定判定 |
| 检测到混合版但用户未指定处理偏好 | 输出 `[需核实:routing_suggestion]`，建议用户明确偏好 |
| 文件加密但用户未提供密码 | 输出 `[需核实:password]`，提示提供密码 |
| 批量处理中超过 30% 文件判定为低置信 | 中止批量，输出汇总报告，建议人工复核 |

### 门控规则

```
if confidence < 0.7:
    输出占位符，不自动路由
    提示："检测置信度较低，建议人工复核或提供更多上下文"
```

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| 1001 | 非PDF文件 | "文件格式不正确，请确认输入为PDF文件" | 检查文件扩展名和文件头 |
| 1002 | 文件损坏 | "PDF文件结构损坏，无法解析" | 尝试用其他工具修复，或重新获取文件 |
| 1003 | 文件加密 | "PDF已加密，需要密码才能访问" | 提供密码后重试 |
| 1004 | 页面解析失败 | "第X页解析异常，已跳过" | 检查该页是否包含特殊元素 |
| 1005 | 文件过大 | "文件超过200MB限制" | 分割文件或使用流式处理 |
| 1006 | 网络错误 | "无法从URL下载文件" | 检查URL可访问性，或下载后本地处理 |
| 1007 | 批量中断 | "批量处理中低置信文件超过30%，已中止" | 人工复核低置信文件后重新处理 |

---

## 六、FAQ 反模式对照

| 常见误区 | 反模式示例 | 正确做法 |
|----------|------------|----------|
| 混淆"有文本"与"可编辑" | 认为 `text_layer` 类型PDF一定可编辑 | 文本层可能被锁定或使用嵌入字体，需额外验证 |
| 忽略置信度直接处理 | 置信度0.55仍直接走OCR流程 | 置信度<0.7时先人工确认类型 |
| 批量处理无容错 | 一个文件报错导致整个批次失败 | 使用错误码体系，跳过错误文件并记录 |
| 对加密文件反复尝试 | 不提供密码反复重试 | 先确认密码，再发起处理 |
| 将扫描版直接当文本处理 | 对 `scanned` 类型直接提取文本得到空结果 | 先走OCR流程，再提取 |

---

## 七、渐进式披露阅读路径

### 🚀 新手速查（5分钟上手）

1. 阅读「一、能力边界」了解工具能做什么、不能做什么
2. 阅读「三、标准执行流程」的 Step 1-2，掌握基本调用方式
3. 使用默认参数运行一次，观察输出 JSON 结构
4. 遇到问题时查阅「五、错误码体系」对照处理

### 🎯 进阶应用（构建自动化流水线）

1. 阅读「三、标准执行流程」的 Step 3-5，理解类型判定逻辑与置信度计算
2. 掌握「四、置信度门控机制」，学会处理不确定场景
3. 阅读「六、FAQ 反模式对照」，避免常见使用陷阱
4. 根据「路由决策规则」构建自动化处理流水线
5. 批量处理时结合错误码体系设计容错机制

---

## 路由决策规则

| 判定类型 | 路由建议 | 适用场景 |
|----------|----------|----------|
| `text_layer` | `direct_parse` | 直接提取文本，用于搜索、编辑、分析 |
| `scanned` | `ocr_required` | 需先OCR识别，再进行文本处理 |
| `mixed` | `hybrid_processing` | 部分页面直接提取，部分页面OCR |

---

## 用户协议

<!-- user-agreement-injected -->

**使用本 Skill 即表示您同意以下条款：**

1. **责任承担**：使用者自行承担因使用本 Skill 产生的全部责任。本 Skill 提供的检测结果仅供参考，不构成任何形式的专业建议或保证。
2. **禁止反向工程**：禁止对本 Skill 进行反向工程、反编译、反汇编，或试图提取源代码、算法逻辑。
3. **合法使用**：使用者应确保使用本 Skill 处理的内容符合相关法律法规，不得用于处理非法或侵权内容。

---

## 许可证（License）

<!-- professional-license-embedded -->

### MIT License

Copyright (c) 2024 SkillForge Studio

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

*本 Skill 由 AI 辅助生成，仅供参考。使用前请阅读相关文档并自行验证输出结果。*
