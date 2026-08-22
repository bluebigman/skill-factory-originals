---
slug: microsis
name: microsis
displayName: 旧档解析 字段还原 置信标注
description: 将老旧数据、文件或URL解析为结构化结果，保留关键信息并标注置信度。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 数据复原工坊
agent_created: true
trigger_words: ["microsis", "旧数据解析", "结构化提取", "字段还原", "老旧文件转换", "数据复原", "历史档案清洗"]
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# microsis — 旧数据解析与结构化复原 Skill

本 Skill 由 AI 辅助生成，仅供参考。使用前请结合具体数据场景进行验证。

---

## 一、能力边界（一页纸速查卡）

### 1.1 能做什么

| 能力项 | 说明 | 示例 |
|--------|------|------|
| 老旧文本解析 | 从非结构化文本中抽取关键字段 | 手写扫描件 OCR 文本、老式报表打印件 |
| 文件格式转换 | 将 .txt/.log/.csv 等旧格式转为统一 JSON 结构 | 1990 年代 DOS 导出的数据文件 |
| URL 内容提取 | 从指定 URL 抓取文本并结构化 | 已下线网站的缓存页面 |
| 字段还原 | 根据上下文补全缺失字段名 | 只有值的列表，推断字段含义 |
| 置信度标注 | 每个输出字段附带可信程度标记 | `confidence: 0.87` |

### 1.2 不能做什么

- 不能解析加密或损坏的文件（输出 `ERROR_CORRUPT`）
- 不能保证 100% 字段还原准确率（受源数据质量限制）
- 不能处理需要人工专业判断的语义歧义（如法律条款解释）
- 不能自动修改原始文件（只读操作）

### 1.3 适用对象

| 适用场景 | 不适用场景 |
|----------|------------|
| 历史数据迁移前的摸底 | 实时流式数据处理 |
| 老旧报表数字化 | 需要复杂业务规则映射的场景 |
| 归档文件内容检索 | 图像/音频等非文本数据 |

---

## 二、触发方式与场景映射

### 2.1 触发词

直接使用以下任一触发词即可激活：

- `microsis`
- `旧数据解析`
- `结构化提取`
- `字段还原`
- `老旧文件转换`
- `数据复原`
- `历史档案清洗`

### 2.2 大白话场景映射表

| 你说的话（口语化） | Skill 实际执行动作 |
|-------------------|-------------------|
| "帮我把这个老 txt 整理成表格" | 解析文本 → 识别字段 → 输出 JSON |
| "这个网址里的内容帮我抓下来" | 请求 URL → 提取正文 → 结构化 |
| "这些乱糟糟的数据能理清楚吗" | 尝试推断字段 → 标注置信度 → 输出 |
| "这批旧文件能转成新格式吗" | 批量转换 → 输出统一 schema |

---

## 三、标准执行流程

### 3.1 前置条件

| 条件 | 要求 | 检查方式 |
|------|------|----------|
| 文件可读 | 非加密、非损坏 | 尝试读取，失败则报 `ERROR_READ` |
| 编码识别 | 支持 UTF-8/GBK/Shift-JIS | 自动检测，无法识别报 `ERROR_ENCODING` |
| 命名规范 | 建议 `源文件名_日期.扩展名` | 不强制，但影响批量处理效率 |
| 目录权限 | 当前目录可写（用于输出） | 检查写权限 |

### 3.2 执行步骤（分步编号）

1. **输入确认**
   - 单个文件：`microsis 文件名`
   - URL：`microsis https://example.com/page`
   - 批量：`microsis 目录路径/`

2. **试运行（单样本）**
   - 执行命令：`microsis 样本文件 --dry-run`
   - 核对输出字段名、类型、置信度是否合理
   - 若字段缺失严重，调整解析规则（见 3.4）

3. **批量执行**
   - 确认试运行无误后：`microsis 目录路径/ --batch`
   - 输出目录自动创建 `microsis_output/`
   - 原始文件不做任何修改

4. **结果校验**
   - 抽查 5% 输出条目，比对源数据关键字段
   - 使用 `microsis --validate 输出文件.json` 自动校验 schema

### 3.3 输出规范

输出统一为 JSON 格式，结构如下：

```json
{
  "source": "原始文件路径或URL",
  "parsed_at": "2025-01-15T10:30:00Z",
  "schema_version": "1.0",
  "fields": [
    {
      "name": "字段名",
      "value": "字段值",
      "confidence": 0.92,
      "source_position": "第3行第2列"
    }
  ],
  "warnings": ["字段 'date' 存在两种格式，已统一为 ISO8601"]
}
```

### 3.4 解析规则调整参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--delimiter` | 自动检测 | 指定分隔符（逗号/制表符/竖线） |
| `--encoding` | 自动检测 | 强制指定编码 |
| `--field-hint` | 无 | 提供字段名提示列表 |
| `--date-format` | 自动 | 指定日期解析格式 |
| `--confidence-threshold` | 0.6 | 低于此值的字段标记为 `[需核实]` |

---

## 四、置信度门控机制

### 4.1 置信度评分规则

| 评分范围 | 含义 | 输出标记 |
|----------|------|----------|
| 0.90 - 1.00 | 高置信，字段明确匹配 | 无特殊标记 |
| 0.70 - 0.89 | 中置信，存在轻微歧义 | 无特殊标记 |
| 0.50 - 0.69 | 低置信，需要人工确认 | `[需核实:字段名]` |
| < 0.50 | 无法确定 | `[需核实:字段名]` + 置空 value |

### 4.2 信息不足时的处理

**绝不编造数据**。当出现以下情况时：

- 字段值缺失 → 输出 `null` + `[需核实:字段名]`
- 字段名无法推断 → 输出 `field_unknown_N` + `[需核实:字段名]`
- 日期格式冲突 → 统一为 ISO8601 + warning 提示

### 4.3 置信度阈值调整

```bash
# 将阈值提高到 0.8，减少低置信输出
microsis 文件.txt --confidence-threshold 0.8
```

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| `ERROR_READ` | 文件无法读取 | "无法读取文件，请检查文件权限或是否损坏" | 1. 检查文件权限 2. 尝试用文本编辑器打开验证 |
| `ERROR_ENCODING` | 编码无法识别 | "无法识别文件编码，请指定 --encoding" | 1. 尝试 `--encoding GBK` 2. 或 `--encoding UTF-8` |
| `ERROR_PARSE` | 解析失败 | "解析过程中出现异常，请检查数据格式" | 1. 查看 warning 信息 2. 调整 `--delimiter` 参数 |
| `ERROR_URL` | URL 无法访问 | "无法访问该 URL，请检查网络或地址" | 1. 确认 URL 正确 2. 检查网络连接 |
| `ERROR_SCHEMA` | 输出 schema 校验失败 | "输出结构不符合规范，请检查字段定义" | 1. 运行 `--validate` 查看具体错误 2. 修正字段映射 |
| `ERROR_BATCH` | 批量处理中断 | "批量处理在第 N 个文件处中断" | 1. 查看错误日志 2. 跳过问题文件继续执行 |

---

## 六、FAQ 与反模式对照

### 6.1 常见坑

| 坑 | 反模式（错误做法） | 正确做法 |
|----|-------------------|----------|
| 忽略试运行 | 直接批量处理全部文件 | 先跑单样本，确认输出质量 |
| 覆盖原始文件 | 在原文件上直接修改 | 保留原始文件，输出到独立目录 |
| 置信度造假 | 低置信字段强行赋值 | 输出 `[需核实:字段]` 占位 |
| 编码猜错 | 默认 UTF-8 硬解 | 先检测编码，必要时手动指定 |
| 字段名臆测 | 随意命名无法确定的字段 | 使用 `field_unknown_N` 并标注 |

### 6.2 反模式对照表

| 场景 | ❌ 不要这样做 | ✅ 应该这样做 |
|------|--------------|--------------|
| 遇到乱码 | 直接丢弃该文件 | 尝试不同编码重新解析 |
| 字段值缺失 | 用 "N/A" 填充 | 输出 null + 标注 |
| 日期格式混乱 | 保留原始格式 | 统一 ISO8601 + warning |
| 批量处理报错 | 忽略继续 | 记录错误，单独处理问题文件 |

---

## 七、渐进式披露阅读路径

### 7.1 速查卡（30 秒上手）

```
1. 放文件到当前目录
2. 跑：microsis 文件名 --dry-run
3. 看输出 JSON 是否合理
4. 跑：microsis 文件名
5. 输出在 microsis_output/ 下
```

### 7.2 新手路径（完整流程）

1. 阅读「能力边界」了解适用范围
2. 按「标准执行流程」从试运行开始
3. 遇到问题查「错误码体系」
4. 不确定的字段看「置信度门控」

### 7.3 进阶路径（深度调优）

1. 掌握「解析规则调整参数」自定义解析
2. 理解「置信度评分规则」调整阈值
3. 批量处理时使用 `--validate` 保证质量
4. 参考「FAQ 反模式」规避常见错误

---

## 八、用户协议

<!-- user-agreement-injected -->

**使用 microsis Skill 即表示您同意以下条款：**

1. **责任承担**：使用者自行承担全部责任。本 Skill 提供的解析结果仅供参考，不构成任何形式的数据准确性保证。因使用本 Skill 产生的任何直接或间接损失，Skill 作者及贡献者不承担任何责任。

2. **禁止反向工程**：不得对本 Skill 的底层逻辑、提示词结构、评分算法进行反向工程、破解、篡改或二次分发用于商业竞争。

3. **数据合规**：使用者需确保所解析的数据来源合法，不侵犯第三方知识产权或个人隐私。因数据来源违法导致的后果由使用者自行承担。

4. **无担保声明**：本 Skill 按"现状"提供，不附带任何明示或暗示的担保，包括但不限于适销性、特定用途适用性和非侵权保证。

5. **协议更新**：本协议可能随 Skill 版本更新而调整，持续使用视为接受更新后的协议。

---

## 九、许可证（License）

<!-- professional-license-embedded -->

### MIT License

Copyright (c) 2025 数据复原工坊

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

*文档版本：1.0.0 | 最后更新：2025年1月*
