---
slug: schemaz
name: schemaz
displayName: 结构解析 数据清洗 字段映射
description: 将任意数据源解析为结构化结果，标注置信度并输出规范格式。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 知微架构师
agent_created: true
trigger_words: ["schemaz", "结构解析", "数据清洗", "字段映射", "结构化输出"]
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# schemaz 技能文档

## 一、能力边界（一页纸速查卡）

### 1.1 能做与不能做

| 维度 | 能做 | 不能做 |
|------|------|--------|
| 输入处理 | 用户提供的数据、文件（CSV/JSON/XML/TXT）、URL 指向的公开数据 | 无法访问需登录/付费/内网的资源 |
| 解析能力 | 识别键值对、表格、列表、嵌套结构中的关键信息 | 不执行语义理解、情感分析或主观判断 |
| 输出格式 | 按约定生成 JSON/CSV/Markdown 表格，支持自定义字段结构 | 不生成二进制文件或加密格式 |
| 置信度标注 | 对每个字段标注 high/medium/low 置信度 | 不提供概率数值或统计显著性 |
| 批量处理 | 支持多文件顺序处理，保持命名规范一致 | 不并行处理，不自动发现新文件 |

### 1.2 适用对象

- **数据工程师**：快速清洗非结构化日志为结构化表格
- **业务分析师**：从网页或文档提取关键指标
- **运维人员**：将配置文件转换为统一格式
- **学生/研究者**：整理实验数据或文献元数据

### 1.3 输入输出速查

| 项目 | 规格 |
|------|------|
| 输入来源 | 本地文件路径 / 粘贴文本 / 公开 URL |
| 输出文件类型 | `.json`（默认）、`.csv`、`.md` |
| 字段结构 | 由用户指定或自动推断（见 3.3 节） |
| 最大处理量 | 单文件 ≤ 5MB，批量 ≤ 50 个文件 |

---

## 二、触发方式

### 2.1 触发词

- 主触发词：`schemaz`
- 同义场景词：`结构解析`、`数据清洗`、`字段映射`、`结构化输出`

### 2.2 场景映射表

| 用户说（大白话） | 实际触发动作 |
|------------------|--------------|
| "帮我把这个 CSV 整理成 JSON" | 调用 schemaz 解析 CSV → 输出 JSON |
| "这个网页里的表格能提取吗？" | 调用 schemaz 抓取 URL → 提取表格 → 结构化 |
| "日志文件太乱了，帮我理一理" | 调用 schemaz 识别日志模式 → 输出字段化结果 |
| "批量处理这些文件，格式要统一" | 调用 schemaz 批量模式 → 按统一 schema 输出 |

---

## 三、标准流程

### 3.1 前置条件

1. 待处理文件已放入当前工作目录（或提供可访问的 URL）
2. 文件命名遵循 `[前缀]_[日期].[扩展名]` 规范（如 `sales_20250101.csv`）
3. 用户已明确输出格式偏好（JSON/CSV/MD）或接受默认 JSON
4. 若需自定义字段映射，用户已提供字段对照表

### 3.2 执行步骤

| 步骤 | 操作 | 说明 |
|------|------|------|
| 1 | 输入确认 | 核对文件路径、格式、编码（UTF-8 优先） |
| 2 | 单样本试运行 | 取第一个文件执行解析，输出样例供用户确认 |
| 3 | 字段映射确认 | 若自动推断字段，列出映射表请用户确认 |
| 4 | 批量执行 | 按确认后的配置处理全部文件 |
| 5 | 结果校验 | 抽查 10% 输出条目，核对关键字段与源数据一致性 |
| 6 | 输出交付 | 生成结果文件 + 处理报告（含置信度统计） |

### 3.3 输出规范

**默认 JSON 结构：**

```json
{
  "schema_version": "1.0",
  "source_file": "sales_20250101.csv",
  "processed_at": "2025-01-01T12:00:00Z",
  "record_count": 128,
  "records": [
    {
      "id": 1,
      "fields": {
        "customer_name": {"value": "张三", "confidence": "high"},
        "amount": {"value": 299.00, "confidence": "high"},
        "note": {"value": null, "confidence": "low"}
      }
    }
  ],
  "warnings": ["字段 'note' 在 23 条记录中缺失"]
}
```

**置信度定义：**

| 级别 | 含义 | 判定标准 |
|------|------|----------|
| high | 明确匹配 | 字段值完整且格式符合预期 |
| medium | 推断值 | 存在格式偏差但可合理推断 |
| low | 缺失/模糊 | 字段为空或存在多种可能解释 |

---

## 四、置信度门控

### 4.1 基本原则

- **不编造**：当信息不足时，输出 `[需核实:字段名]` 占位符，不猜测值
- **显式标注**：每个字段必须附带 confidence 属性
- **批量一致性**：同一字段在批量处理中置信度标准保持一致

### 4.2 处理规则

| 场景 | 处理方式 |
|------|----------|
| 字段完全缺失 | 输出 `null` + confidence: low |
| 字段格式异常（如日期乱码） | 保留原始值 + confidence: medium + warning |
| 字段存在多义性 | 取最可能值 + confidence: medium + 备注说明 |
| 字段值超出合理范围 | 输出 `[需核实:字段名]` + 停止该条处理 |

### 4.3 二次确认触发条件

- 超过 30% 字段为 low 置信度
- 自动推断的字段映射与用户预期不符
- 输入文件编码无法识别

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| E001 | 文件不存在 | "未找到指定文件，请确认路径是否正确" | 检查路径 → 重新输入 |
| E002 | 编码不支持 | "文件编码非 UTF-8，请转换后重试" | 用 `iconv` 转换 → 重试 |
| E003 | 字段映射冲突 | "检测到字段映射冲突，请确认优先级" | 查看冲突详情 → 指定优先级 |
| E004 | 批量中断 | "第 N 个文件处理失败，已停止批量任务" | 修复该文件 → 从断点继续 |
| E005 | 输出格式错误 | "输出格式参数无效，可选 json/csv/md" | 修正参数 → 重试 |
| E006 | URL 不可访问 | "无法访问该 URL，请检查网络或权限" | 下载到本地 → 重新处理 |

---

## 六、FAQ 反模式

| 常见坑 | 反模式（错误做法） | 正确做法 |
|--------|---------------------|----------|
| 忽略置信度 | 直接使用 low 置信度数据做决策 | 先人工复核 low 置信度字段 |
| 过度清洗 | 删除"看起来没用"的原始字段 | 保留原始值，仅在输出层过滤 |
| 批量盲目执行 | 不试运行直接全量处理 | 先单样本验证，再批量 |
| 字段命名随意 | 输出字段名与源数据无对应关系 | 维护字段映射表，保持可追溯 |
| 忽略警告 | 无视 warnings 数组直接交付 | 检查 warnings，必要时补充处理 |

---

## 七、渐进式披露

### 7.1 速查卡（30 秒上手）

```
schemaz 使用三步：
1. 放文件 → 2. 说"解析" → 3. 拿结果
默认输出 JSON，含置信度标注。
```

### 7.2 新手路径（5 分钟）

1. 阅读第 1 节了解能力边界
2. 按第 3 节流程执行一次单文件解析
3. 查看输出 JSON 中的 confidence 字段
4. 遇到问题查第 5 节错误码表

### 7.3 进阶路径（深度使用）

1. 自定义字段映射：提供字段对照表（源字段→目标字段）
2. 批量处理：按 `[前缀]_[日期].[扩展名]` 命名后执行批量
3. 输出定制：使用 `--format csv` 或 `--format md` 切换输出
4. 二次开发：基于输出 JSON 编写后续处理管道

---

## 八、CLI 接口参考

| 参数 | 说明 | 示例 |
|------|------|------|
| `--selftest` | 运行自检，验证环境配置 | `schemaz --selftest` |
| `--version` | 显示版本号 | `schemaz --version` |
| `--format` | 指定输出格式（json/csv/md） | `schemaz input.csv --format csv` |
| `--batch` | 批量处理当前目录所有匹配文件 | `schemaz --batch` |

---

## 用户协议

<!-- user-agreement-injected -->

**使用须知：**

1. 本技能仅供学习与参考用途，使用者应自行承担全部使用风险与责任。
2. 使用者不得对本技能进行反向工程、反编译或试图提取底层算法。
3. 本技能输出的结果不构成任何专业建议，重要决策请咨询相关领域专家。
4. 使用者应确保输入数据的合法性与合规性，不得处理违法违规内容。
5. 本技能不提供任何形式的明示或暗示担保，包括但不限于适销性与特定用途适用性。

---

## 许可证（License）

<!-- professional-license-embedded -->

**MIT License**

Copyright (c) 2025 知微架构师

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

*本文档由 AI 辅助生成，仅供参考。使用前请阅读相关文档。*
