---
slug: airecon-skills
name: airecon-skills
displayName: 数据识别 字段抽取 结构化解析
description: 将文本、CSV、JSON或URL内容解析为结构化数据，支持字段映射与多格式输出。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: DataForge Studio
agent_created: true
trigger_words: ["airecon-skills", "数据解析", "字段抽取", "结构化识别", "信息提取", "数据清洗"]
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# airecon-skills 技能文档

## 一、能力边界速查卡

本技能用于将非结构化或半结构化数据转换为可用的结构化格式。以下是明确的边界说明：

| 维度 | 能做 | 不能做 |
|------|------|--------|
| 输入类型 | 纯文本、CSV、JSON、公开URL页面 | 加密文件、需登录的私有系统、二进制文件（图片/PDF扫描件） |
| 处理能力 | 字段识别、类型推断、批量映射、置信度评分 | 语义理解、情感分析、跨语言翻译 |
| 输出格式 | JSON、CSV、Markdown 表格 | 直接写入数据库、生成可视化图表 |
| 数据规模 | 单次建议 ≤ 10,000 条记录 | 超过建议规模需分批处理 |
| 网络抓取 | 公开可访问的静态页面 | 动态渲染页面（需JS执行）、受robots.txt限制的站点 |

**适用对象**：需要从客户信息表、订单记录、活动报名名单、公开网页列表中提取结构化数据的运营人员、数据分析师、自动化流程开发者。

---

## 二、触发方式与场景映射

当对话中出现以下意图时，本技能将被激活：

| 用户说（大白话） | 触发场景 | 实际执行动作 |
|------------------|----------|--------------|
| "帮我把这些联系人整理成表格" | 文本→结构化 | 识别姓名、电话、邮箱等字段并输出CSV |
| "这个网页上的公司名单能导出来吗" | URL→结构化 | 抓取页面内容，提取公司名称、地址、行业 |
| "这份CSV里字段太乱了，帮我规整一下" | CSV→规范化 | 重命名列、统一格式、补充缺失字段标记 |
| "从这段JSON里挑出我要的信息" | JSON→子集提取 | 按需映射字段，输出精简后的结构化数据 |
| "批量处理一下，先看看效果" | 批量预览 | 执行 `--dry-run` 模式，输出前5条样本 |

**命令行接口**：
```bash
# 版本查询
airecon-skills --version

# 自检模式（验证环境配置）
airecon-skills --selftest

# 预览模式（不写入文件，仅输出样本）
airecon-skills --dry-run input.csv

# 指定编码处理中文乱码
airecon-skills --encoding gbk input.txt
```

---

## 三、标准处理流程

### 前置条件

1. 确认输入数据格式（文本/CSV/JSON/URL）
2. 确认输出格式需求（JSON/CSV/Markdown）
3. 若为URL，确认目标页面可公开访问且未违反robots.txt
4. 若数据量 > 1,000 条，建议先执行 `--dry-run`

### 执行步骤

**步骤 1：数据接入**
- 文本：直接粘贴或指定文件路径
- CSV：确认分隔符（默认逗号，支持 `--delimiter ';'` 自定义）
- JSON：确认是数组还是单对象，数组需指定元素路径
- URL：提供完整链接，系统自动抓取并提取正文内容

**步骤 2：字段映射**
- 系统自动识别常见字段（name, phone, email, date, address）
- 自定义字段使用 `--map 原始字段:标准字段` 语法，可多次指定
- 示例：`--map 客户名称:name --map 联系方式:phone`

**步骤 3：类型推断与清洗**
- 日期统一为 `YYYY-MM-DD` 格式
- 电话号码去除空格和连字符，保留国际区号
- 邮箱转为小写
- 地址保留原始格式，不做标准化

**步骤 4：置信度评估**
- 每条记录生成 `confidence` 分数（0.0 - 1.0）
- 分数 < 0.7 的记录在输出中标记 `[需核实:字段名]`
- 示例输出片段：
```json
{
  "records": [
    {
      "name": "张三",
      "phone": "13800138000",
      "confidence": 0.95
    },
    {
      "name": "[需核实:name]",
      "phone": "未知",
      "confidence": 0.42
    }
  ]
}
```

**步骤 5：输出生成**
- JSON：完整结构化输出，含 `meta` 字段（处理时间、记录数、平均置信度）
- CSV：表头为映射后的标准字段名，`[需核实]` 标记保留在单元格内
- Markdown：生成表格，置信度 < 0.7 的行用 `⚠️` 前缀标注

### 输出规范

| 输出格式 | 文件扩展名 | 编码 | 特殊处理 |
|----------|------------|------|----------|
| JSON | .json | UTF-8 | 缩进2空格，含meta信息 |
| CSV | .csv | UTF-8 (可指定) | 自动添加BOM（Excel兼容） |
| Markdown | .md | UTF-8 | 含统计摘要表格 |

---

## 四、置信度门控机制

当遇到以下信息不足的情况，系统**不会**编造数据，而是插入占位符：

| 场景 | 占位符 | 说明 |
|------|--------|------|
| 字段缺失 | `[需核实:字段名]` | 该字段在源数据中不存在 |
| 格式异常 | `[需核实:字段名]` | 字段存在但无法解析（如日期格式混乱） |
| 多值冲突 | `[需核实:字段名]` | 同一字段出现多个不同值，无法确定优先级 |
| 编码问题 | `[需核实:全部]` | 数据解码失败，需指定 `--encoding` |

**人工复核建议**：对置信度 < 0.7 的记录进行人工检查，重点核对姓名、电话、邮箱等关键字段。

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| E001 | 输入文件不存在 | "未找到指定文件，请检查路径" | 确认文件路径正确，或使用绝对路径 |
| E002 | 编码无法识别 | "无法解码输入，请指定编码格式" | 添加 `--encoding utf-8` 或 `--encoding gbk` |
| E003 | URL抓取失败 | "页面无法访问，可能被屏蔽或不存在" | 检查URL拼写，确认页面公开可访问 |
| E004 | 字段映射冲突 | "映射字段与标准字段重复" | 检查 `--map` 参数，避免重复映射 |
| E005 | 数据量超限 | "单次处理超过10,000条，请分批执行" | 使用 `--batch-size 5000` 分批处理 |
| E006 | 输出目录无权限 | "无法写入输出文件，权限不足" | 更换输出目录或调整文件权限 |

---

## 六、常见陷阱与反模式对照

| 陷阱 | 反模式（错误做法） | 正模式（推荐做法） |
|------|-------------------|-------------------|
| 忽略编码问题 | 直接处理乱码文本，期望自动修复 | 先指定 `--encoding`，或使用 `--selftest` 检测 |
| 盲目信任低置信度数据 | 将置信度 0.5 的记录直接入库 | 设置阈值，对 < 0.7 的记录标记人工复核 |
| URL抓取不检查协议 | 抓取 robots.txt 禁止的路径 | 先访问 `robots.txt` 确认允许范围 |
| 批量处理不预览 | 直接对 10,000 条数据执行完整处理 | 先 `--dry-run` 查看前5条样本效果 |
| 字段映射过于随意 | 使用 `a, b, c` 等无意义字段名 | 使用标准字段名，确保下游系统可识别 |
| 忽略多值冲突 | 取第一个值丢弃其余 | 标记 `[需核实]`，保留所有值供人工选择 |

---

## 七、渐进式阅读路径

### 速查卡（30秒上手）

1. 输入数据 → 2. 指定格式 → 3. 执行处理 → 4. 检查置信度 → 5. 输出结果

### 新手路径（首次使用）

1. 阅读「能力边界速查卡」了解适用范围
2. 使用 `--selftest` 验证环境
3. 用 `--dry-run` 预览小样本
4. 检查输出中的 `[需核实]` 标记
5. 正式执行并导出结果

### 进阶路径（批量/复杂场景）

1. 自定义字段映射（`--map` 参数）
2. 处理多值冲突与编码问题
3. 设置批量处理参数（`--batch-size`）
4. 结合置信度阈值设计人工复核流程
5. 将输出接入下游自动化系统

---

## 八、参数参考表

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `--input` | string | 必填 | 输入文件路径或URL |
| `--output` | string | stdout | 输出文件路径 |
| `--format` | string | json | 输出格式：json/csv/markdown |
| `--encoding` | string | utf-8 | 输入文件编码 |
| `--delimiter` | string | , | CSV分隔符 |
| `--map` | string | 无 | 字段映射，可多次指定 |
| `--dry-run` | flag | false | 预览模式，输出前5条 |
| `--batch-size` | int | 10000 | 每批处理记录数 |
| `--confidence-threshold` | float | 0.7 | 置信度阈值，低于此值标记 |
| `--selftest` | flag | false | 环境自检 |
| `--version` | flag | false | 版本信息 |

---

## 九、用户协议

<!-- user-agreement-injected -->

使用本 Skill 即表示您同意以下条款：

1. **责任承担**：使用者自行承担因使用本 Skill 产生的全部责任。包括但不限于数据准确性、合规性、以及因错误解析导致的直接或间接损失。
2. **禁止反向工程**：不得对本 Skill 的底层算法、提示词结构、评分逻辑进行反向工程、破解、提取或二次分发。
3. **数据合规**：使用者需确保输入数据来源合法，不包含侵犯第三方权益的内容。抓取URL时需遵守目标网站的 robots.txt 协议及相关法律法规。
4. **无担保声明**：本 Skill 按"现状"提供，不附带任何明示或暗示的担保，包括但不限于适销性、特定用途适用性。
5. **更新与变更**：作者保留随时修改、更新或终止本 Skill 的权利，恕不另行通知。

---

## 十、许可证（License）

<!-- professional-license-embedded -->

### MIT License

Copyright (c) 2024 原创作者（自持版权）

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

*本 Skill 由 AI 辅助生成，仅供参考。使用前请阅读相关文档并自行验证适用性。*
