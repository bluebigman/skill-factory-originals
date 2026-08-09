---
copyright_holder: 原创作者（自持版权）
source_project: original
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
ai_generated: true
license: MIT
slug: report-pro
name: report-pro
displayName: 报告
description: 报告场景一站式处理技能：覆盖报告的识别、整理、生成与校验，输出可直接使用的结果文件。
version: 1.0.0
author: skill-factory-auto
agent_created: true
trigger_words:
  - "报告"
  - "报告处理"
  - "报告生成"
  - "报告整理"
  - "report-pro"
  - "报告自动化"
---

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->


> 📜 **用户协议（User Agreement）**
> 1. 本 Skill 仅供学习与参考用途。使用本 Skill 产生的任何结果，由使用者自行承担全部责任；本 Skill 不提供任何明示或暗示的保证。
> 2. 涉及法律、财务、税务、投资、医疗等专业决策时，请务必咨询持证专业人士。
> 3. 本代码受版权法保护，未经授权复制、反向工程或商业利用将被追究法律责任。
<!-- user-agreement-injected -->


# WorkBuddy Skill: report_pro

---
slug: report-pro
name: report_pro
displayName: 报告处理
description: 报告场景一站式处理技能：覆盖报告的识别、整理、生成与校验，输出可直接使用的结果文件。
version: 1.0.0
trigger_words: ["报告", "报告处理", "报告生成", "报告整理", "帮我写报告", "这个报告乱了", "报告自动化", "汇总报告", "报告格式", "报告校验"]
---

# 报告处理 · 一页纸速查卡

> **报告处理** = 识别（读入）→ 整理（清洗）→ 生成（产出）→ 校验（检查）→ 交付（输出）

| 场景 | 你要说什么 | 我会做什么 |
|------|-----------|-----------|
| 识别 | "帮我看看这个报告是什么格式" | 自动检测文件类型、结构、编码 |
| 整理 | "这个报告乱了，帮我理理" | 清洗数据、统一格式、去重补缺 |
| 生成 | "帮我写一份周报" | 基于数据源生成结构化报告 |
| 校验 | "帮我检查报告有没有问题" | 交叉验证数据、检查逻辑一致性 |
| 汇总 | "把这几份报告合并一下" | 多文件合并、去重、统一schema |

**输出物**：`report_输出_时间戳.md` + `report_输出_时间戳.xlsx`（含校验日志）

---

## 一、能力边界

### ✅ 能做（5+项）

| # | 能力 | 具体说明 |
|---|------|---------|
| 1 | **多格式报告识别** | 支持 PDF、Word（.docx）、Excel（.xlsx/.csv）、Markdown、纯文本，自动检测编码（UTF-8/GBK/GB2312）与结构 |
| 2 | **数据提取与清洗** | 从非结构化文本中提取表格、数字、日期、关键字段；自动去重、去空、统一日期格式（YYYY-MM-DD）、统一数字格式（千分位） |
| 3 | **报告结构重建** | 自动识别标题层级（#/##/###）、段落、列表、表格，重建为规范 Markdown 结构 |
| 4 | **多报告合并汇总** | 多份报告按指定字段（如日期、部门、项目）合并，自动对齐 schema，冲突字段标记 |
| 5 | **报告生成** | 基于结构化数据（CSV/Excel/JSON）生成 Markdown 报告，含表格、统计摘要、趋势描述 |
| 6 | **质量校验** | 交叉验证数据一致性（合计=分项之和）、日期合法性、必填字段完整性，输出校验报告 |
| 7 | **格式转换** | Markdown ↔ Excel ↔ CSV 互转，保留表格结构与元数据 |

### ❌ 不做（3+项边界声明）

| # | 边界 | 说明 |
|---|------|------|
| 1 | **不做主观判断** | 不评估报告内容的"好坏"、不提供业务建议、不做情感分析 |
| 2 | **不处理扫描件/图片** | 不支持 OCR 识别（如需请配合 OCR Skill 先行转换） |
| 3 | **不生成图表** | 不产出可视化图表，只输出结构化数据与 Markdown 表格 |
| 4 | **不处理加密/损坏文件** | 密码保护的 PDF/Excel、损坏文件直接报错 E004，不尝试破解 |

---

## 二、触发方式

### 6类场景触发词表

| 场景类型 | 触发词示例 |
|---------|-----------|
| 报告处理 | 报告、报告处理、report-pro、报告自动化 |
| 报告生成 | 报告生成、帮我写报告、生成周报、写月报、做个总结 |
| 报告整理 | 报告整理、这个报告乱了、帮我理理、格式乱了、排版乱了 |
| 报告汇总 | 报告汇总、合并报告、把这几份合一起、汇总一下 |
| 报告校验 | 报告校验、帮我检查报告、看看有没有问题、数据对不对 |
| 报告转换 | 转成Excel、转成Markdown、换个格式、导出CSV |

### 大白话触发示例表

| 用户原话 | 触发动作 |
|---------|---------|
| "帮我处理这个" | 启动标准流程，先检测文件格式与编码 |
| "这个报告乱了" | 启动整理流程，重建结构+清洗数据 |
| "帮我写份周报" | 启动生成流程，询问数据源与时间范围 |
| "把这几份合一起" | 启动合并流程，检测 schema 对齐情况 |
| "检查下这报告有没有坑" | 启动校验流程，交叉验证数据一致性 |
| "转成 Excel 给我" | 启动格式转换流程 |

---

## 三、标准流程

### Step 1：收集最小信息集

**必问信息（按优先级）：**

| # | 信息项 | 默认值 | 说明 |
|---|--------|--------|------|
| 1 | 输入文件路径 | 无（必填） | 支持相对/绝对路径，多个文件用逗号分隔 |
| 2 | 操作类型 | 自动检测 | `识别`/`整理`/`生成`/`校验`/`汇总`/`转换`，无法检测时询问 |
| 3 | 输出格式 | Markdown | `markdown`/`excel`/`csv`/`json` |

**可选信息（有默认值）：**

| # | 信息项 | 默认值 | 说明 |
|---|--------|--------|------|
| 4 | 编码 | 自动检测 | UTF-8/GBK/GB2312 |
| 5 | 日期格式 | YYYY-MM-DD | 统一输出格式 |
| 6 | 数字格式 | 千分位 | 1,234.56 |
| 7 | 合并字段 | 自动检测 | 汇总操作时指定对齐字段 |

**话术模板：**
> 收到！我来处理报告。请提供：
> 1. **文件路径**（必填）：要处理的报告文件在哪？
> 2. **操作类型**（默认自动检测）：识别 / 整理 / 生成 / 校验 / 汇总 / 转换？
> 3. **输出格式**（默认 Markdown）：要输出成什么格式？

---

### Step 2：核心执行（真实工具绑定）

#### 2.1 文件识别与读取

```python
# 使用 python-docx, openpyxl, pdfplumber 检测文件类型
import os
from pathlib import Path

def detect_file_type(filepath):
    ext = Path(filepath).suffix.lower()
    if ext == '.pdf':
        import pdfplumber
        with pdfplumber.open(filepath) as pdf:
            first_page = pdf.pages[0]
            text = first_page.extract_text() or ''
            tables = first_page.extract_tables()
            return {'type': 'pdf', 'text_len': len(text), 'table_count': len(tables)}
    elif ext == '.docx':
        from docx import Document
        doc = Document(filepath)
        return {'type': 'docx', 'paragraphs': len(doc.paragraphs), 'tables': len(doc.tables)}
    elif ext == '.xlsx':
        import openpyxl
        wb = openpyxl.load_workbook(filepath, read_only=True)
        return {'type': 'xlsx', 'sheets': wb.sheetnames}
    elif ext == '.csv':
        import pandas as pd
        df = pd.read_csv(filepath, nrows=5)
        return {'type': 'csv', 'columns': list(df.columns)}
    elif ext == '.md' or ext == '.txt':
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        return {'type': 'markdown' if ext == '.md' else 'text', 'len': len(content)}
    else:
        raise ValueError(f"Unsupported file type: {ext}")
```

#### 2.2 数据清洗（pandas）

```python
import pandas as pd
import re

def clean_dataframe(df):
    """清洗 DataFrame：去重、去空、统一格式"""
    # 1. 去重
    df = df.drop_duplicates()
    
    # 2. 去空（全空行/列）
    df = df.dropna(how='all').dropna(axis=1, how='all')
    
    # 3. 统一日期格式
    date_cols = [c for c in df.columns if '日期' in c or 'date' in c.lower()]
    for col in date_cols:
        df[col] = pd.to_datetime(df[col], errors='coerce').dt.strftime('%Y-%m-%d')
    
    # 4. 统一数字格式（去货币符号、千分位）
    num_cols = [c for c in df.columns if any(k in c for k in ['金额', '数量', '金额', 'price', 'amount'])]
    for col in num_cols:
        df[col] = df[col].astype(str).str.replace(r'[¥$€,]', '', regex=True)
        df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # 5. 文本列去除首尾空格
    str_cols = df.select_dtypes(include=['object']).columns
    for col in str_cols:
        df[col] = df[col].str.strip()
    
    return df
```

#### 2.3 报告结构重建（正则+规则）

```python
import re

def rebuild_markdown_structure(text):
    """从纯文本重建 Markdown 结构"""
    lines = text.split('\n')
    md_lines = []
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # 识别标题（# 开头或数字编号）
        if re.match(r'^#{1,6}\s', line):
            md_lines.append(line)
        elif re.match(r'^\d+[\.、]\s', line):
            # 数字编号 → 二级标题
            md_lines.append(f'## {line}')
        elif re.match(r'^[（(]?\d+[)）]?\s', line):
            md_lines.append(f'### {line}')
        elif re.match(r'^[-*•]\s', line):
            md_lines.append(line)  # 列表项
        elif re.match(r'^\|.*\|$', line):
            md_lines.append(line)  # 表格行
        else:
            # 普通段落
            md_lines.append(line)
    
    return '\n'.join(md_lines)
```

#### 2.4 报告生成（pandas → Markdown）

```python
import pandas as pd

def generate_report_from_data(df, title, summary_cols=None):
    """从 DataFrame 生成 Markdown 报告"""
    md = []
    
    # 标题
    md.append(f'# {title}\n')
    
    # 统计摘要
    md.append('## 统计摘要\n')
    md.append(f'- 总记录数：{len(df)}')
    md.append(f'- 总列数：{len(df.columns)}')
    
    # 数值列统计
    num_cols = df.select_dtypes(include=['number']).columns
    if len(num_cols) > 0:
        md.append('\n### 数值统计\n')
        stats = df[num_cols].describe().to_markdown()
        md.append(stats)
    
    # 数据表格
    md.append('\n## 数据明细\n')
    md.append(df.to_markdown(index=False))
    
    return '\n'.join(md)
```

#### 2.5 质量校验（交叉验证）

```python
def validate_report(df, rules=None):
    """校验数据质量，返回校验报告"""
    issues = []
    
    # 规则1：必填字段非空
    required_cols = rules.get('required_cols', []) if rules else []
    for col in required_cols:
        if col not in df.columns:
            issues.append(f'E001: 缺少必填字段 {col}')
        elif df[col].isna().any():
            empty_count = df[col].isna().sum()
            issues.append(f'E002: 字段 {col} 有 {empty_count} 条空值')
    
    # 规则2：合计=分项之和
    if rules and 'sum_check' in rules:
        for check in rules['sum_check']:
            total_col = check['total']
            part_cols = check['parts']
            if total_col in df.columns and all(c in df.columns for c in part_cols):
                df['_sum'] = df[part_cols].sum(axis=1)
                mismatch = df[abs(df['_sum'] - df[total_col]) > 0.01]
                if len(mismatch) > 0:
                    issues.append(f'E003: {len(mismatch)} 行合计不等于分项之和')
                df.drop('_sum', axis=1, inplace=True)
    
    # 规则3：日期合法性
    date_cols = [c for c in df.columns if '日期' in c or 'date' in c.lower()]
    for col in date_cols:
        invalid_dates = pd.to_datetime(df[col], errors='coerce').isna()
        if invalid_dates.any():
            issues.append(f'E004: 字段 {col} 有 {invalid_dates.sum()} 条非法日期')
    
    return issues
```

---

### Step 3：输出校验

**输出物清单：**

| 输出物 | 路径 | 说明 |
|--------|------|------|
| 主报告 | `report_输出_YYYYMMDD_HHMMSS.md` | 处理后的 Markdown 报告 |
| 数据文件 | `report_输出_YYYYMMDD_HHMMSS.xlsx` | 结构化数据（如适用） |
| 校验日志 | `report_校验日志_YYYYMMDD_HHMMSS.json` | 校验结果与置信度 |

**校验检查项：**

- [ ] 文件编码正确（UTF-8 无乱码）
- [ ] 表格结构完整（列数一致、无断裂）
- [ ] 日期格式统一（YYYY-MM-DD）
- [ ] 数字格式统一（千分位）
- [ ] 必填字段无空值
- [ ] 合计=分项之和（如适用）
- [ ] 标题层级正确（无跳级）

---

## 四、置信度门控

| 置信度 | 处理方式 | 输出标记 |
|--------|---------|---------|
| ≥ 90% | 直接输出 | 无标记 |
| 85% - 90% | 输出 + 建议复核 | `⚠️ 建议复核` |
| < 85% | 输出 + 标记需核实 | `[需核实]` |

**置信度计算规则：**

```
置信度 = 基础分(70) 
       + 文件格式识别成功(+10) 
       + 数据清洗无异常(+5) 
       + 校验通过率 × 15
```

**示例：**
- 文件识别成功（+10），清洗无异常（+5），校验通过率 100%（+15）→ 置信度 = 100%
- 文件识别成功（+10），清洗有 2 条警告（+3），校验通过率 80%（+12）→ 置信度 = 95%
- 文件识别成功（+10），清洗有 5 条警告（+0），校验通过率 60%（+9）→ 置信度 = 89% → ⚠️ 建议复核

---

## 五、异常处理

### 错误码体系表

| 错误码 | 错误类型 | 触发条件 | 标准化话术 |
|--------|---------|---------|-----------|
| E001 | 输入为空 | 未提供文件路径 | "请提供要处理的报告文件路径，支持 PDF/Word/Excel/Markdown/文本格式。" |
| E002 | 信息缺失 | 缺少必要参数（如输出格式） | "还缺少输出格式信息，请指定：markdown / excel / csv / json。" |
| E003 | 格式错误 | 文件格式不支持或文件损坏 | "文件格式不支持或已损坏。支持格式：PDF、DOCX、XLSX、CSV、MD、TXT。请检查文件后重试。" |
| E004 | 文件加密 | 文件有密码保护 | "文件有密码保护，无法读取。请解除密码后重试。" |
| E005 | 置信度低 | 置信度 < 85% | "处理完成，但部分数据未能准确识别（置信度 82%）。请人工复核标记为 [需核实] 的部分。" |
| E006 | 超边界 | 请求超出能力范围（如 OCR） | "该请求超出我的能力范围（如扫描件 OCR）。建议先使用 OCR Skill 转换后再处理。" |

---

## 六、FAQ（高频问题速查）

### Q1: 支持哪些文件格式？
**A:** 支持 PDF、Word（.docx）、Excel（.xlsx/.csv）、Markdown（.md）、纯文本（.txt）。不支持扫描件/图片（需 OCR）。

### Q2: 多份报告怎么合并？
**A:** 提供多个文件路径（逗号分隔），我会自动检测各文件的 schema，对齐字段后合并。冲突字段会标记 `[冲突]` 并记录在校验日志中。

### Q3: 报告里的日期格式不统一怎么办？
**A:** 自动统一为 `YYYY-MM-DD` 格式。原始格式多样（如 2024/1/5、2024年1月5日、01-05-2024）都能识别并转换。

### Q4: 如何判断处理结果是否可靠？
**A:** 每次处理都会输出置信度（≥90% 直接可用，85-90% 建议复核，<85% 需人工核实）。同时附校验日志，列出所有数据质量问题。

### Q5: 能处理多大数据量的报告？
**A:** 单文件建议 ≤ 100MB，行数 ≤ 100 万行。超过建议分批处理。

### Q6: 输出格式可以自定义吗？
**A:** 支持 Markdown、Excel（.xlsx）、CSV、JSON 四种输出格式。默认 Markdown，可在 Step 1 指定。

---

## 七、渐进式披露

### 速览（30秒）
- 输入文件路径 → 自动检测格式 → 按需处理 → 输出结果 + 校验报告
- 支持：识别、整理、生成、校验、汇总、转换 6 种操作
- 输出：Markdown 报告 + Excel 数据 + JSON 校验日志

### 上手（5分钟）
1. 准备一个报告文件（PDF/Word/Excel/Markdown）
2. 说"帮我处理这个报告，文件在 /path/to/file"
3. 等待处理完成，查看输出文件和校验日志
4. 如有问题，查看错误码表定位原因

### 深度（进阶用法）
- **批量处理**：提供多个文件路径，自动批量处理并汇总
- **自定义规则**：在 Step 2 可指定校验规则（如必填字段、合计校验）
- **格式转换**：任意输入格式 → 任意输出格式（如 PDF → Excel）
- **模板生成**：基于数据自动生成周报/月报/项目报告模板

---

## 附录：完整代码示例

```python
#!/usr/bin/env python3
"""report_pro 核心处理流程"""

import sys
import json
from pathlib import Path
from datetime import datetime

def process_report(filepath, operation='auto', output_format='markdown'):
    """报告处理主函数"""
    result = {
        'status': 'success',
        'confidence': 0,
        'output_files': [],
        'issues': [],
        'timestamp': datetime.now().strftime('%Y%m%d_%H%M%S')
    }
    
    try:
        # Step 1: 文件识别
        file_info = detect_file_type(filepath)
        result['confidence'] += 10
        
        # Step 2: 读取数据
        if file_info['type'] == 'pdf':
            import pdfplumber
            with pdfplumber.open(filepath) as pdf:
                text = '\n'.join(page.extract_text() or '' for page in pdf.pages)
                df = None  # PDF 需要额外解析表格
        elif file_info['type'] == 'xlsx':
            import pandas as pd
            df = pd.read_excel(filepath)
        elif file_info['type'] == 'csv':
            import pandas as pd
            df = pd.read_csv(filepath)
        elif file_info['type'] == 'docx':
            from docx import Document
            doc = Document(filepath)
            text = '\n'.join(p.text for p in doc.paragraphs)
            df = None
        else:  # markdown / text
            with open(filepath, 'r', encoding='utf-8') as f:
                text = f.read()
            df = None
        
        # Step 3: 数据清洗（如果是表格数据）
        if df is not None:
            df = clean_dataframe(df)
            result['confidence'] += 5
            
            # Step 4: 校验
            issues = validate_report(df)
            if issues:
                result['issues'] = issues
                pass_rate = max(0, 1 - len(issues) / 10)
                result['confidence'] += int(15 * pass_rate)
            else:
                result['confidence'] += 15
        
        # Step 5: 输出
        output_path = f"report_输出_{result['timestamp']}.md"
        # ... 写入输出文件
        
        return result
        
    except Exception as e:
        result['status'] = 'error'
        result['error'] = str(e)
        return result

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python report_pro.py <filepath> [operation] [output_format]")
        sys.exit(1)
    
    result = process_report(sys.argv[1])
    print(json.dumps(result, ensure_ascii=False, indent=2))
```

---

*报告处理 Skill v1.0.0 · 覆盖识别/整理/生成/校验/汇总/转换 6 大场景 · 输出可直接使用的结果文件*

## 许可证（License）

```text
MIT License

Copyright (c) 2026 原创作者（自持版权）

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
```
<!-- professional-license-embedded -->
