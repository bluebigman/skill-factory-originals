---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: airecon-skills
name: airecon-skills
displayName: 数据识别 字段映射 批量解析
description: 将文本、CSV、JSON或URL内容解析为结构化数据，支持字段映射与多格式输出。
version: 1.0.4
rules_version: cpr-20260819-n551
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/airecon-skills
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: DataForge Studio
agent_created: true
trigger_words: ["airecon-skills", "数据解析", "字段提取", "结构化输出", "信息识别"]
---

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->


> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# airecon-skills 技能文档

## 一、能力边界：一页纸速查卡

### 1.1 能做什么

| 能力项 | 说明 | 示例 |
|--------|------|------|
| 文本解析 | 从非结构化文本中提取实体字段 | 从邮件正文提取联系人姓名、电话 |
| CSV 解析 | 将 CSV 表格数据映射为标准字段 | 将客户导出表映射为 name/phone/email |
| JSON 解析 | 从嵌套 JSON 中提取指定路径字段 | 从 API 响应中提取订单号、金额 |
| URL 抓取 | 抓取公开网页并解析其中结构化信息 | 从公开黄页页面提取商家联系方式 |
| 字段映射 | 将源数据字段重命名为标准字段名 | `客户名称` → `name` |
| 批量处理 | 支持大文件分批处理 | 10 万行 CSV 分 100 批执行 |
| 多格式输出 | 输出 JSON / CSV / Markdown 三种格式 | 生成 `.json` 或 `.csv` 结果文件 |
| 置信度标注 | 每条记录附带 confidence 分数 | `confidence: 0.92` |

### 1.2 不能做什么

| 限制项 | 说明 |
|--------|------|
| 不处理非公开数据 | 仅抓取可公开访问的 URL，不绕过登录或付费墙 |
| 不执行语义理解 | 无法判断文本的隐含意图或情感倾向 |
| 不保证字段完整 | 源数据缺失时输出 `[需核实:字段]` 占位符 |
| 不进行数据清洗 | 不自动去重、纠错或格式化电话号码 |
| 不支持 OCR | 无法从图片或扫描件中识别文字 |

### 1.3 适用对象

- 需要从大量文本中提取结构化信息的运营人员
- 需要批量整理客户/供应商数据的业务分析师
- 需要将网页公开信息转为表格的调研人员
- 需要快速将异构数据统一格式的开发人员

---

## 二、触发方式

### 2.1 触发词

使用以下任一方式触发本技能：

- 直接输入 `airecon-skills`
- 描述需求时包含：`数据解析`、`字段提取`、`结构化输出`、`信息识别`

### 2.2 场景映射表

| 大白话描述 | 触发动作 |
|------------|----------|
| "帮我从这段文字里把联系方式都拎出来" | 执行文本解析，提取 name/phone/email |
| "这个 Excel 导出的 CSV 字段名太乱了，帮我规整一下" | 执行字段映射，重命名为标准字段 |
| "把这个网页上的公司信息抓下来做成表格" | 执行 URL 抓取 + 结构化输出 |
| "这个 JSON 嵌套太深，帮我拍平了" | 执行 JSON 路径提取 + 字段映射 |
| "我有 5 万条数据要处理，会不会卡死？" | 执行批量处理 + dry-run 预览 |

---

## 三、标准流程

### 3.1 前置条件

| 条件 | 要求 |
|------|------|
| 输入格式 | 文本（≤10MB）、CSV（≤50MB）、JSON（≤20MB）、URL（可公开访问） |
| 编码 | 默认 UTF-8，中文乱码时指定 `--encoding gbk` |
| 字段命名 | 使用标准字段名：`name, phone, email, date, address` |
| 运行环境 | Python 3.8+，安装依赖 `pip install requests pandas` |

### 3.2 执行步骤

**第一步：输入确认**

确认输入类型与数据规模：

```bash
# 文本输入
airecon parse --input "张三 13800138000 zhangsan@example.com"

# CSV 文件输入
airecon parse --input ./customers.csv --format csv

# URL 输入
airecon parse --url "https://example.com/directory"

# 指定编码
airecon parse --input ./data.csv --encoding gbk
```

**第二步：Dry-run 预览（推荐）**

大文件处理前先预览效果：

```bash
airecon parse --input ./big_data.csv --dry-run --limit 20
```

输出前 20 条记录的解析结果与字段映射预览，确认无误后再正式执行。

**第三步：正式执行**

```bash
airecon parse --input ./big_data.csv --output ./result.json --format json
```

**第四步：置信度检查**

```bash
airecon check --input ./result.json --threshold 0.7
```

输出所有 `confidence < 0.7` 的记录列表，供人工复核。

### 3.3 输出规范

| 输出格式 | 文件扩展名 | 结构说明 |
|----------|------------|----------|
| JSON | `.json` | 数组对象，每项含 `data` 与 `confidence` 字段 |
| CSV | `.csv` | 首行为字段名，每行一条记录，末列 `confidence` |
| Markdown | `.md` | 表格形式，含字段名、提取值、置信度三列 |

**JSON 输出示例：**

```json
[
  {
    "data": {
      "name": "张三",
      "phone": "13800138000",
      "email": "zhangsan@example.com"
    },
    "confidence": 0.95
  }
]
```

---

## 四、置信度门控

### 4.1 置信度评分规则

| 场景 | 置信度 | 说明 |
|------|--------|------|
| 字段完全匹配且格式验证通过 | 0.9 - 1.0 | 直接采用 |
| 字段匹配但格式存疑 | 0.7 - 0.89 | 建议复核 |
| 字段部分匹配或存在歧义 | 0.5 - 0.69 | 必须复核 |
| 字段缺失或无法识别 | < 0.5 | 输出占位符 |

### 4.2 占位符规则

当信息不足时，**不编造数据**，输出 `[需核实:字段名]` 占位：

```json
{
  "data": {
    "name": "李四",
    "phone": "[需核实:phone]",
    "email": "lisi@example.com"
  },
  "confidence": 0.62
}
```

### 4.3 人工复核建议

- 对 `confidence < 0.7` 的记录逐条复核
- 复核时对照原始输入，确认提取值是否正确
- 复核后手动修正，并更新置信度为 1.0

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| `E001` | 输入为空 | "未检测到有效输入内容，请检查输入数据。" | 确认输入非空后重试 |
| `E002` | 编码错误 | "检测到乱码，尝试指定编码格式。" | 添加 `--encoding gbk` 或 `--encoding utf-8` |
| `E003` | URL 不可访问 | "目标 URL 无法访问，请确认链接有效且为公开页面。" | 检查 URL 拼写、网络连通性、robots.txt 限制 |
| `E004` | 字段映射失败 | "源字段无法匹配到任何标准字段，请检查字段名。" | 使用 `--field-map` 手动指定映射关系 |
| `E005` | 文件过大 | "文件大小超出限制，请拆分后处理。" | 将大文件拆分为多个小文件分批处理 |
| `E006` | 输出格式错误 | "不支持的输出格式，可选 json/csv/markdown。" | 检查 `--format` 参数拼写 |
| `E007` | 批量处理中断 | "批量处理在第 N 批中断，已保存已处理部分。" | 查看部分结果，从断点继续处理 |

---

## 六、FAQ 反模式

### 6.1 常见坑与反模式对照

| 坑 | 反模式（错误做法） | 正模式（正确做法） |
|----|-------------------|-------------------|
| **乱码** | 直接忽略乱码继续处理 | 先识别编码，指定 `--encoding` 参数 |
| **字段丢失** | 源数据没有该字段就跳过 | 输出 `[需核实:字段]` 占位符，保留记录完整性 |
| **URL 抓取失败** | 反复重试同一 URL | 检查 robots.txt，确认目标允许抓取，或更换数据源 |
| **大文件卡死** | 一次性加载全部数据 | 使用 `--batch-size 1000` 分批处理 |
| **置信度误判** | 所有记录都标记为高置信度 | 按规则计算置信度，对低置信度记录明确标注 |

### 6.2 反模式示例

**反模式 1：忽略编码问题**

```bash
# 错误：直接处理 GBK 编码文件，导致乱码
airecon parse --input ./chinese_data.csv

# 正确：指定编码
airecon parse --input ./chinese_data.csv --encoding gbk
```

**反模式 2：不预览直接全量处理**

```bash
# 错误：10 万行数据直接处理，发现映射错误后浪费大量时间
airecon parse --input ./huge_data.csv --output ./result.json

# 正确：先预览 20 条
airecon parse --input ./huge_data.csv --dry-run --limit 20
```

**反模式 3：编造缺失数据**

```json
// 错误：源数据没有 email，编造一个
{"name": "王五", "email": "wangwu@fake.com"}

// 正确：输出占位符
{"name": "王五", "email": "[需核实:email]", "confidence": 0.45}
```

---

## 七、渐进式披露

### 7.1 速查卡（30 秒上手）

```
输入 → 解析 → 输出
文本/CSV/JSON/URL → 字段映射 + 置信度标注 → JSON/CSV/Markdown

关键参数：
  --dry-run    预览效果
  --encoding   指定编码（默认 UTF-8）
  --threshold  置信度阈值（默认 0.7）
  --batch-size 批量大小（默认 1000）
```

### 7.2 新手路径（首次使用）

1. 准备一个小样本文件（≤100 行）
2. 执行 `--dry-run` 预览解析效果
3. 确认字段映射正确
4. 正式执行并输出 JSON 格式
5. 检查置信度，对低分记录人工复核

### 7.3 进阶路径（熟练使用）

1. 自定义字段映射：`--field-map "客户名称:name, 联系电话:phone"`
2. 批量处理优化：调整 `--batch-size` 与并发参数
3. 多 URL 批量抓取：准备 URL 列表文件，逐行处理
4. 结果二次处理：对输出结果进行去重、排序、关联分析
5. 自动化流水线：将解析命令嵌入脚本，定时执行

### 7.4 参数速查表

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `--input` | string | 必填 | 输入文件路径或文本内容 |
| `--url` | string | 无 | 目标 URL（与 input 二选一） |
| `--format` | string | json | 输出格式：json/csv/markdown |
| `--output` | string | stdout | 输出文件路径 |
| `--encoding` | string | utf-8 | 输入文件编码 |
| `--field-map` | string | 自动 | 自定义字段映射，格式 `源:目标,源:目标` |
| `--dry-run` | flag | false | 预览模式，仅输出前 N 条 |
| `--limit` | int | 20 | dry-run 模式下的预览条数 |
| `--threshold` | float | 0.7 | 置信度阈值，低于此值的记录单独输出 |
| `--batch-size` | int | 1000 | 批量处理时每批的记录数 |
| `--selftest` | flag | false | 运行自检，验证环境与依赖 |
| `--version` | flag | false | 输出版本号 |

---

## 八、自检与版本

### 8.1 自检命令

```bash
airecon --selftest
```

自检项包括：

- Python 版本兼容性检查
- 依赖库（requests, pandas）是否安装
- 标准字段映射表是否完整
- 输出格式模板是否可用

### 8.2 版本信息

```bash
airecon --version
# 输出：airecon-skills v1.0.0
```

---

## 用户协议

<!-- user-agreement-injected -->

**使用本 Skill 即表示您同意以下条款：**

1. **责任承担**：使用者自行承担因使用本 Skill 产生的全部责任，包括但不限于数据处理结果准确性、URL 抓取合规性、输出内容使用方式等。本 Skill 提供的是数据处理辅助能力，不构成任何形式的保证或承诺。

2. **禁止反向工程**：不得对本 Skill 的底层实现进行反向工程、反编译、破解或试图提取源代码（除开源部分外）。不得移除、篡改或遮蔽本 Skill 中的任何版权标识、免责声明或合规标记。

3. **合规使用**：使用者应确保输入数据的合法性与获取权限，遵守目标网站的服务条款与 robots.txt 协议，遵守适用的数据保护法律法规（如《个人信息保护法》《通用数据保护条例》等）。

4. **免责声明**：本 Skill 按"现状"提供，不附带任何明示或暗示的保证，包括但不限于适销性、特定用途适用性和非侵权保证。任何情况下，作者或贡献者均不对因使用本 Skill 而产生的任何索赔、损害或其他责任负责。

---

## 许可证（License）

<!-- professional-license-embedded -->

**MIT License**

版权所有 (c) 2024 DataForge Studio

特此免费授予任何获得本软件及相关文档文件（"软件"）副本的人，不受限制地处理本软件，包括但不限于使用、复制、修改、合并、发布、分发、再许可和/或出售软件副本的权利，并允许向其提供本软件的人这样做，但须满足以下条件：

上述版权声明和本许可声明应包含在本软件的所有副本或主要部分中。

本软件按"现状"提供，不附带任何明示或暗示的保证，包括但不限于适销性、特定用途适用性和非侵权保证。在任何情况下，作者或版权持有人均不对因使用本软件而产生的任何索赔、损害或其他责任负责，无论是在合同诉讼、侵权或其他方面，也不论是否与本软件有关或与本软件的使用或其他交易有关。

---

*本 Skill 由 AI 辅助生成，仅供参考。使用前请阅读相关文档并自行验证适用性。*
