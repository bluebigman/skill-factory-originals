---
slug: skill
name: skill
displayName: 数据转换 结构化解析 置信度标注
description: 将用户数据、文件或URL转换为结构化结果，并标注置信度。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 结构化工坊
agent_created: true
trigger_words: ["skill", "转换", "结构化", "解析", "格式化输出", "数据清洗", "字段映射"]
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# Skill：数据转换与结构化解析

## 一、能力边界（一页纸速查卡）

### 1.1 能做什么

| 能力项 | 说明 | 示例 |
|--------|------|------|
| 文件转换 | 将 CSV、JSON、TXT 等文本文件转为结构化结果 | 将 `orders.csv` 转为 JSON 数组 |
| URL 抓取 | 从公开网页 URL 提取关键字段 | 从商品页提取价格、标题 |
| 字段映射 | 按预定义 schema 重命名字段 | `user_name` → `username` |
| 置信度标注 | 对每个输出字段标注可信程度 | `confidence: 0.95` |
| 批量处理 | 对同目录下多个文件统一执行 | 处理 `data/*.csv` |

### 1.2 不能做什么

| 限制项 | 说明 |
|--------|------|
| 不处理二进制文件 | 仅支持 UTF-8 编码的文本类文件 |
| 不访问需登录的页面 | 仅处理公开可访问的 URL |
| 不进行语义理解 | 仅做模式匹配与字段提取，不判断业务含义 |
| 不保证字段完整性 | 源数据缺失时输出 `[需核实:字段名]` 占位 |
| 不修改原始文件 | 所有输出写入新文件或标准输出 |

### 1.3 适用对象

- 需要批量整理日志、导出数据的运维人员
- 需要从网页快速提取结构化信息的研究人员
- 需要统一多来源数据格式的数据工程师

---

## 二、触发方式

### 2.1 触发词

| 触发词 | 场景示例 |
|--------|----------|
| `skill` | "用 skill 处理这个文件" |
| `转换` | "帮我把这个 CSV 转换一下" |
| `结构化` | "把这段文本结构化输出" |
| `解析` | "解析这个 URL 里的数据" |
| `格式化输出` | "按固定格式输出结果" |
| `数据清洗` | "把脏数据整理成干净格式" |
| `字段映射` | "把字段名统一一下" |

### 2.2 场景映射表

| 用户说 | 实际需求 | 本 Skill 动作 |
|--------|----------|---------------|
| "把这个文件整理一下" | 将非结构化文本转为表格 | 执行文件转换 + 字段映射 |
| "这个网页里的价格帮我抓下来" | 提取 URL 中的特定字段 | 执行 URL 抓取 + 置信度标注 |
| "这些 CSV 格式不一样，统一一下" | 多文件 schema 对齐 | 执行批量转换 + 字段重命名 |
| "这个数据靠谱吗" | 判断提取结果可信度 | 输出置信度分数 + 低置信度提示 |

---

## 三、标准流程

### 3.1 前置条件

| 条件 | 要求 | 检查方式 |
|------|------|----------|
| 输入文件 | UTF-8 编码，单文件 ≤ 10MB | `file -i input.csv` |
| 输入 URL | 公开可访问，返回 HTML 或 JSON | `curl -I <url>` |
| 命名规范 | 同批文件前缀一致，如 `data_01.csv` | `ls data_*` |
| 输出目录 | 存在且可写 | `mkdir -p output && test -w output` |

### 3.2 执行步骤

1. **准备输入**
   - 将待处理文件放入当前工作目录
   - 确认所有文件命名前缀一致（如 `raw_`、`input_`）
   - 若输入为 URL，确认链接可公开访问

2. **定义输出 schema**
   - 列出期望输出的字段名（如 `id`, `name`, `price`）
   - 指定每个字段的类型（string / number / date）

3. **试运行**
   - 选取单个样本文件执行
   - 核对输出字段名、类型、顺序是否符合预期
   - 检查置信度标注是否合理（≥ 0.8 为高置信）

4. **批量执行**
   - 对全量文件执行转换
   - 输出文件命名规则：`<原文件名>_structured.json`
   - 原始文件不做任何修改

5. **校验结果**
   - 随机抽取 5% 输出条目
   - 对照源数据核对关键字段（如 ID、金额、日期）
   - 确认 `[需核实:字段]` 占位符出现的频率 < 10%

### 3.3 输出规范

```json
{
  "schema_version": "1.0",
  "source": "input.csv",
  "processed_at": "2025-01-15T10:30:00Z",
  "total_records": 128,
  "records": [
    {
      "id": "A001",
      "name": "示例商品",
      "price": 19.99,
      "_confidence": {
        "id": 1.0,
        "name": 0.95,
        "price": 0.98
      }
    }
  ],
  "warnings": [
    "3 条记录缺少 price 字段，已标记 [需核实:price]"
  ]
}
```

---

## 四、置信度门控

### 4.1 置信度评分规则

| 置信度区间 | 含义 | 处理方式 |
|------------|------|----------|
| 0.95 - 1.0 | 字段值完整且格式完全匹配 | 直接输出 |
| 0.80 - 0.94 | 字段值存在但格式略有偏差 | 输出并附带解析说明 |
| 0.50 - 0.79 | 字段值存在但来源不可靠 | 输出并标注 `[需核实:字段名]` |
| < 0.50 | 字段值缺失或无法解析 | 输出 `[需核实:字段名]` 占位 |

### 4.2 信息不足时的处理

当源数据缺少必要字段时，**严禁编造数据**。处理规则：

1. 在输出字段位置填入 `[需核实:字段名]`
2. 在 `warnings` 数组中记录缺失详情
3. 该条记录的 `_confidence` 对应字段设为 `0.0`

**示例**：

```json
{
  "id": "A002",
  "name": "[需核实:name]",
  "price": 25.50,
  "_confidence": {
    "id": 1.0,
    "name": 0.0,
    "price": 0.97
  }
}
```

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| `E001` | 文件不存在 | "未找到指定文件，请检查路径" | 确认文件路径正确，重新执行 |
| `E002` | 编码不支持 | "文件编码非 UTF-8，无法解析" | 使用 `iconv -f GBK -t UTF-8` 转码 |
| `E003` | URL 无法访问 | "目标 URL 返回 404 或超时" | 检查 URL 拼写，确认网络连通 |
| `E004` | Schema 不匹配 | "输入字段与目标 schema 不一致" | 检查字段映射表，调整映射规则 |
| `E005` | 批量中断 | "第 3 个文件处理失败，已停止" | 修复问题文件后，从断点继续 |
| `E006` | 输出目录不可写 | "无法写入输出目录，权限不足" | 修改目录权限或更换输出路径 |

---

## 六、FAQ 反模式

### 6.1 常见坑与反模式对照

| 常见坑 | 反模式（错误做法） | 正模式（正确做法） |
|--------|-------------------|-------------------|
| 字段名混淆 | 直接使用源文件字段名，不做映射 | 先定义目标 schema，再建立映射表 |
| 忽略编码问题 | 直接读取文件，遇到乱码就跳过 | 执行前检查文件编码，统一转 UTF-8 |
| 置信度虚高 | 所有字段默认给 0.99 | 按实际解析情况逐字段评分 |
| 批量无验证 | 一次跑完全部文件再检查 | 先跑单样本，确认无误再批量 |
| 覆盖原始数据 | 转换结果直接写回原文件 | 输出到独立目录，保留原始备份 |

### 6.2 反模式示例

**反模式**：用户直接对 100 个文件批量执行，结果发现字段映射错误，全部返工。

**正模式**：先取 1 个文件试运行，核对输出无误后，再执行剩余 99 个文件。

---

## 七、渐进式披露

### 7.1 速查卡（30 秒上手）

```
1. 放文件 → 2. 定义字段 → 3. 试运行 → 4. 批量跑 → 5. 抽查结果
```

### 7.2 新手路径（首次使用）

1. 阅读「能力边界」了解工具范围
2. 按「标准流程」第 1-3 步完成单文件试运行
3. 查看输出 JSON 的 `_confidence` 字段理解置信度含义
4. 遇到问题对照「错误码体系」排查

### 7.3 进阶路径（熟练使用）

1. 自定义字段映射规则，处理复杂嵌套结构
2. 编写预处理脚本，清洗源数据中的异常值
3. 调整置信度阈值，过滤低质量输出
4. 结合 CI/CD 流程，将转换步骤自动化

---

## 八、参数速查表

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `--input` | string | 无 | 输入文件路径或 URL |
| `--output` | string | `./output/` | 输出目录 |
| `--schema` | string | 无 | 目标字段定义（JSON 格式） |
| `--confidence-threshold` | number | 0.5 | 低于此值的字段标记占位符 |
| `--batch` | boolean | false | 是否批量处理目录下所有匹配文件 |
| `--selftest` | boolean | false | 运行内置自检 |
| `--version` | boolean | false | 显示版本号 |

---

## 九、用户协议

使用本 Skill 即表示您同意以下条款：

1. **责任承担**：使用者自行承担因使用本 Skill 产生的全部责任。本 Skill 仅提供数据处理辅助功能，不构成任何形式的专业建议或决策依据。
2. **数据安全**：使用者应确保输入数据不包含敏感信息。本 Skill 不负责数据加密或隐私保护。
3. **禁止反向工程**：使用者不得对本 Skill 进行反向工程、反编译或试图提取底层算法。
4. **无担保声明**：本 Skill 按"现状"提供，不附带任何明示或暗示的担保。

<!-- user-agreement-injected -->

---

## 十、许可证（License）

本 Skill 采用 MIT 许可证发布：

```
MIT License

Copyright (c) 2025 结构化工坊

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
