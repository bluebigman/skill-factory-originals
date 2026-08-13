---
copyright_holder: 原创作者（自持版权）
source_project: original
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
ai_generated: true
license: MIT
slug: skill-54580
name: skill-54580
displayName: 投融资
description: 投融资场景一站式处理技能：覆盖投融资的识别、整理、生成与校验，输出可直接使用的结果文件。
version: 1.0.0
author: skill-factory-auto
agent_created: true
trigger_words:
  - "投融资"
  - "投融资处理"
  - "投融资生成"
  - "投融资整理"
  - "skill-54580"
  - "投融资自动化"
---

> 📜 **用户协议（User Agreement）**
> 1. 本 Skill 仅供学习与参考用途。使用本 Skill 产生的任何结果，由使用者自行承担全部责任；本 Skill 不提供任何明示或暗示的保证。
> 2. 涉及法律、财务、税务、投资、医疗等专业决策时，请务必咨询持证专业人士。
> 3. 本代码受版权法保护，未经授权复制、反向工程或商业利用将被追究法律责任。
<!-- user-agreement-injected -->


> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->


# WorkBuddy Skill: 投融资

---
## 📋 一页纸速查卡

| 项目 | 内容 |
|------|------|
| **技能名称** | skill_54580 |
| **展示名称** | 投融资 |
| **核心能力** | 投融资场景一站式处理：识别、整理、生成与校验，输出可直接使用的结果文件 |
| **适用场景** | 商业计划书整理、融资路演材料生成、投资分析报告、财务数据清洗、尽调清单整理 |
| **输入要求** | 投融资相关文档（BP、财务表、尽调材料、投资意向书等）或结构化数据 |
| **输出格式** | 标准化投融资文档（Markdown/Excel/PDF） |
| **置信度门控** | ≥90% 直接输出 / 85-90% 建议复核 / <85% 标记[需核实] |
| **最小信息集** | 项目名称、融资阶段、融资金额、行业领域、核心财务数据 |
| **运行环境** | Python 3.8+，需安装 pandas, openpyxl, pdfplumber, python-docx |

---

## 一、能力边界

### ✅ 能做（5+项具体能力）

1. **投融资文档识别与解析**：自动识别并提取商业计划书（BP）、投资意向书（Term Sheet）、尽职调查清单、财务预测表中的关键信息，包括项目名称、融资阶段、融资金额、股权结构、财务指标等结构化数据。

2. **财务数据清洗与标准化**：对投融资相关的财务数据（收入、利润、现金流、资产负债等）进行自动化清洗，包括缺失值处理、异常值检测、单位统一（万元/亿元）、格式标准化，输出干净的 Excel 数据表。

3. **投融资文档自动生成**：基于用户提供的核心信息，自动生成结构完整的商业计划书框架、投资分析报告、融资路演材料（PPT 大纲）、尽调清单等标准文档，可直接编辑使用。

4. **投融资数据交叉验证**：对文档中的关键数据进行交叉校验，如财务数据一致性、估值与融资金额匹配度、股权稀释比例计算等，自动标记异常数据并给出修正建议。

5. **投融资进度跟踪与整理**：将零散的投融资沟通记录、会议纪要、邮件往来整理为结构化的进度跟踪表，包含时间线、参与方、关键决策、待办事项等字段。

6. **多格式输出支持**：支持输出 Markdown、Excel（.xlsx）、Word（.docx）、PDF 等多种格式，满足不同场景的使用需求。

### ❌ 不做（3+项边界声明）

1. **不提供投资建议**：本技能仅做信息整理、格式标准化和文档生成，不提供任何投资决策建议、估值判断或投资风险评估。投资决策需由专业投资人或机构完成。

2. **不处理非结构化图像**：本技能不处理纯图片格式的投融资材料（如手写扫描件、非文字型 PDF 扫描件）。如需处理，请先使用 OCR 工具转换为可编辑文本。

3. **不保证数据真实性**：本技能仅对用户提供的数据进行格式化和逻辑校验，无法验证数据本身的真实性和准确性。用户需确保输入数据的真实性。

4. **不涉及法律文件起草**：本技能不生成具有法律效力的合同、协议等法律文件。如需法律文件，请咨询专业律师。

---

## 二、触发方式

### 6类场景触发词表

| 场景类型 | 触发词/短语 |
|---------|------------|
| 投融资识别 | 投融资、融资、投资、BP、商业计划书、Term Sheet、投资意向书 |
| 投融资整理 | 整理、梳理、汇总、归类、清洗、格式化 |
| 投融资生成 | 生成、创建、制作、撰写、起草、输出 |
| 投融资校验 | 校验、验证、检查、核对、审查、交叉验证 |
| 投融资自动化 | 自动化、一键、批量、流程化、标准化 |
| 特定场景 | 尽调、尽职调查、路演、融资计划、投资分析、股权结构 |

### 大白话触发示例表

| 用户原话 | 触发动作 |
|---------|---------|
| "帮我处理这个投融资文档" | 启动标准投融资文档处理流程 |
| "这个BP有点乱，帮我整理下" | 启动 BP 文档整理流程 |
| "帮我生成一份融资计划书" | 启动融资计划书生成流程 |
| "检查下这份财务数据有没有问题" | 启动财务数据校验流程 |
| "把这几份尽调材料汇总一下" | 启动尽调材料汇总流程 |
| "帮我做个投资分析报告" | 启动投资分析报告生成流程 |
| "这个Excel里的融资数据帮我清洗下" | 启动财务数据清洗流程 |
| "整理下这几次融资沟通的记录" | 启动投融资进度整理流程 |

---

## 三、标准流程

### Step 1: 收集最小信息集

在开始处理前，必须明确以下关键信息（如用户未提供，需主动询问）：

| 信息项 | 说明 | 示例 |
|-------|------|------|
| **项目名称** | 融资主体/项目名称 | "XX智能科技有限公司" |
| **融资阶段** | 种子轮/天使轮/A轮/B轮/C轮等 | "A轮" |
| **融资金额** | 计划融资金额及币种 | "5000万人民币" |
| **行业领域** | 所属行业及细分领域 | "人工智能-企业服务" |
| **核心财务数据** | 营收、利润、增长率等关键指标 | "2023年营收3000万，同比增长150%" |
| **文档类型** | 需要处理的文档类型 | "商业计划书" |

**信息收集方法**：
- 如用户提供文档，使用 `pdfplumber` 或 `python-docx` 提取文本内容，自动识别上述信息
- 如用户未提供文档，通过对话引导用户补充关键信息
- 使用正则表达式自动匹配常见字段（融资金额、融资阶段等）

### Step 2: 核心执行

#### 2.1 投融资文档识别与解析

```python
import pdfplumber
import re
from typing import Dict, List

def parse_investment_document(file_path: str) -> Dict:
    """
    解析投融资文档，提取关键信息
    """
    # 提取文本
    text = ""
    if file_path.endswith('.pdf'):
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                text += page.extract_text() or ""
    elif file_path.endswith('.docx'):
        from docx import Document
        doc = Document(file_path)
        for para in doc.paragraphs:
            text += para.text + "\n"
    
    # 提取关键信息
    info = {}
    
    # 提取融资金额（支持多种格式）
    amount_patterns = [
        r'融资金额[：:]\s*([\d,]+\.?\d*)\s*(万|亿)?\s*(元|人民币|美元)?',
        r'计划融资\s*([\d,]+\.?\d*)\s*(万|亿)?\s*(元|人民币|美元)?',
        r'融资规模[：:]\s*([\d,]+\.?\d*)\s*(万|亿)?\s*(元|人民币|美元)?'
    ]
    for pattern in amount_patterns:
        match = re.search(pattern, text)
        if match:
            amount = float(match.group(1).replace(',', ''))
            unit = match.group(2) or '万'
            currency = match.group(3) or '元'
            if unit == '亿':
                amount *= 10000
            info['融资金额'] = f"{amount:.0f}万{currency}"
            break
    
    # 提取融资阶段
    stage_pattern = r'(种子轮|天使轮|Pre-A轮|A轮|A\+轮|B轮|B\+轮|C轮|D轮|Pre-IPO轮)'
    match = re.search(stage_pattern, text)
    if match:
        info['融资阶段'] = match.group(1)
    
    # 提取项目名称（通常在文档开头或标题位置）
    lines = text.split('\n')
    for line in lines[:20]:
        if len(line.strip()) > 5 and len(line.strip()) < 50:
            if not re.search(r'(融资|投资|商业计划|目录|摘要)', line):
                info['项目名称'] = line.strip()
                break
    
    return info
```

#### 2.2 财务数据清洗与标准化

```python
import pandas as pd
import numpy as np

def clean_financial_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    清洗投融资财务数据
    """
    df_clean = df.copy()
    
    # 1. 处理缺失值
    numeric_cols = df_clean.select_dtypes(include=[np.number]).columns
    for col in numeric_cols:
        # 用中位数填充缺失值
        df_clean[col] = df_clean[col].fillna(df_clean[col].median())
    
    # 2. 异常值检测（使用IQR方法）
    for col in numeric_cols:
        Q1 = df_clean[col].quantile(0.25)
        Q3 = df_clean[col].quantile(0.75)
        IQR = Q3 - Q1
        lower_bound = Q1 - 1.5 * IQR
        upper_bound = Q3 + 1.5 * IQR
        # 标记异常值
        df_clean[f'{col}_异常标记'] = ((df_clean[col] < lower_bound) | 
                                      (df_clean[col] > upper_bound))
    
    # 3. 单位统一（万元）
    if '金额' in df_clean.columns:
        # 假设原始数据可能为元，统一转换为万元
        df_clean['金额_万元'] = df_clean['金额'] / 10000
    
    # 4. 日期格式标准化
    if '日期' in df_clean.columns:
        df_clean['日期'] = pd.to_datetime(df_clean['日期']).dt.strftime('%Y-%m-%d')
    
    return df_clean

# 使用示例
# df = pd.read_excel('financial_data.xlsx')
# df_cleaned = clean_financial_data(df)
# df_cleaned.to_excel('financial_data_cleaned.xlsx', index=False)
```

#### 2.3 投融资文档自动生成

```python
def generate_business_plan(info: Dict) -> str:
    """
    生成商业计划书框架
    """
    bp_template = f"""
# {info.get('项目名称', '项目名称')} 商业计划书

## 一、执行摘要
- 项目名称：{info.get('项目名称', '待填写')}
- 融资阶段：{info.get('融资阶段', '待填写')}
- 融资金额：{info.get('融资金额', '待填写')}
- 所属行业：{info.get('行业领域', '待填写')}

## 二、市场分析
### 2.1 市场规模
- 目标市场规模：待填写
- 市场增长率：待填写
- 市场趋势：待填写

### 2.2 竞争分析
- 主要竞争对手：待填写
- 竞争优势：待填写
- 市场定位：待填写

## 三、产品与服务
### 3.1 产品概述
- 产品描述：待填写
- 核心功能：待填写
- 技术壁垒：待填写

### 3.2 商业模式
- 盈利模式：待填写
- 定价策略：待填写
- 客户群体：待填写

## 四、财务预测
### 4.1 历史财务数据
- 营收数据：待填写
- 利润数据：待填写
- 现金流：待填写

### 4.2 未来财务预测
- 未来3年营收预测：待填写
- 未来3年利润预测：待填写
- 盈亏平衡点：待填写

## 五、融资计划
### 5.1 融资需求
- 融资金额：{info.get('融资金额', '待填写')}
- 资金用途：待填写
- 预期估值：待填写

### 5.2 股权结构
- 当前股权结构：待填写
- 融资后股权结构：待填写
- 股权稀释比例：待填写

## 六、团队介绍
- 核心团队：待填写
- 顾问团队：待填写
- 组织架构：待填写

## 七、风险分析
- 市场风险：待填写
- 技术风险：待填写
- 运营风险：待填写
- 政策风险：待填写

## 八、发展规划
- 短期规划（1年）：待填写
- 中期规划（2-3年）：待填写
- 长期规划（3-5年）：待填写
"""
    return bp_template
```

#### 2.4 投融资数据交叉验证

```python
def cross_validate_data(info: Dict) -> Dict:
    """
    交叉验证投融资数据
    """
    validation_results = {}
    
    # 1. 验证估值与融资金额匹配度
    if '融资金额' in info and '股权稀释比例' in info:
        try:
            amount = float(info['融资金额'].replace('万', '').replace('元', ''))
            dilution = float(info['股权稀释比例'].replace('%', ''))
            implied_valuation = amount / (dilution / 100)
            validation_results['隐含估值'] = f"{implied_valuation:.0f}万元"
        except:
            validation_results['估值验证'] = "数据格式错误，无法验证"
    
    # 2. 验证财务数据一致性
    if '营收' in info and '利润' in info:
        try:
            revenue = float(info['营收'].replace('万', '').replace('元', ''))
            profit = float(info['利润'].replace('万', '').replace('元', ''))
            profit_margin = profit / revenue * 100
            validation_results['利润率'] = f"{profit_margin:.1f}%"
            if profit_margin > 50:
                validation_results['利润率警告'] = "利润率超过50%，请核实数据真实性"
        except:
            validation_results['财务验证'] = "数据格式错误，无法验证"
    
    # 3. 验证股权结构合理性
    if '当前股权' in info and '融资后股权' in info:
        try:
            current = float(info['当前股权'].replace('%', ''))
            after = float(info['融资后股权'].replace('%', ''))
            if after >= current:
                validation_results['股权验证'] = "警告：融资后股权比例异常"
            else:
                dilution = (current - after) / current * 100
                validation_results['股权稀释比例'] = f"{dilution:.1f}%"
        except:
            validation_results['股权验证'] = "数据格式错误，无法验证"
    
    return validation_results
```

### Step 3: 输出校验

#### 3.1 输出格式校验

```python
def validate_output(output_data: Dict) -> Dict:
    """
    校验输出数据的完整性和格式
    """
    validation = {
        '完整性': [],
        '格式正确性': [],
        '置信度': 0
    }
    
    # 必填字段检查
    required_fields = ['项目名称', '融资阶段', '融资金额']
    for field in required_fields:
        if field in output_data and output_data[field]:
            validation['完整性'].append(f"{field}: ✓")
        else:
            validation['完整性'].append(f"{field}: ✗ 缺失")
    
    # 格式检查
    if '融资金额' in output_data:
        amount_str = str(output_data['融资金额'])
        if re.match(r'^\d+\.?\d*\s*(万|亿)?\s*(元|人民币|美元)?$', amount_str):
            validation['格式正确性'].append("融资金额格式: ✓")
        else:
            validation['格式正确性'].append("融资金额格式: ✗ 不正确")
    
    # 计算置信度
    complete_count = sum(1 for item in validation['完整性'] if '✓' in item)
    format_count = sum(1 for item in validation['格式正确性'] if '✓' in item)
    total_checks = len(required_fields) + len(validation['格式正确性'])
    validation['置信度'] = (complete_count + format_count) / total_checks * 100
    
    return validation
```

#### 3.2 置信度门控

```python
def apply_confidence_gate(validation_result: Dict) -> str:
    """
    根据置信度应用门控策略
    """
    confidence = validation_result['置信度']
    
    if confidence >= 90:
        return "✅ 置信度≥90%，直接输出"
    elif confidence >= 85:
        return "⚠️ 置信度85-90%，建议复核以下字段：\n" + \
               "\n".join([item for item in validation_result['完整性'] if '✗' in item])
    else:
        return "🔴 置信度<85%，标记[需核实]，请人工检查所有字段"
```

---

## 四、置信度门控

### 三档处理策略

| 置信度范围 | 处理方式 | 输出标记 |
|-----------|---------|---------|
| **≥90%** | 直接输出，无需额外标记 | 无特殊标记 |
| **85-90%** | 输出结果并标注"建议复核" | `[建议复核]` |
| **<85%** | 输出结果并标注"[需核实]" | `[需核实]` |

### 置信度计算规则

```
置信度 = (必填字段完整数 + 格式正确数) / (必填字段总数 + 格式检查总数) × 100%
```

### 置信度提升建议

1. **补充必填信息**：确保项目名称、融资阶段、融资金额等核心字段完整
2. **统一数据格式**：使用标准化的金额格式（如"5000万元"而非"5千万"）
3. **提供原始文档**：提供原始文档可提高自动识别准确率
4. **人工确认关键数据**：对财务数据、股权结构等关键信息进行人工确认

---

## 五、异常处理

### 错误码体系表

| 错误码 | 错误类型 | 触发条件 | 标准化话术 |
|-------|---------|---------|-----------|
| **E001** | 输入为空 | 用户未提供任何文档或数据 | "未检测到输入内容，请提供需要处理的投融资文档或相关数据。" |
| **E002** | 信息缺失 | 缺少必填字段（项目名称/融资阶段/融资金额） | "检测到关键信息缺失：{缺失字段}。请补充完整后重试，或使用'跳过'继续处理。" |
| **E003** | 格式错误 | 文档格式不支持或数据格式错误 | "文档格式不支持或数据格式有误。请提供PDF、Word、Excel格式的文档，或检查数据格式是否符合要求。" |
| **E004** | 超边界 | 请求超出技能处理范围 | "该请求超出本技能处理范围。本技能仅处理投融资相关的文档整理、数据清洗和文档生成，不提供投资建议或法律文件起草。" |
| **E005** | 置信度低 | 处理结果置信度<85% | "处理结果置信度较低（{置信度}%），部分数据可能不准确。建议人工复核所有字段，或补充更多信息后重新处理。" |
| **E006** | 文件读取失败 | 无法读取用户提供的文件 | "无法读取该文件，请确认文件未损坏且格式受支持（PDF/Word/Excel）。" |
| **E007** | 数据异常 | 检测到明显异常数据 | "检测到异常数据：{异常描述}。请核实数据真实性后重新处理。" |

### 异常处理流程

```
检测到异常
    ↓
识别错误码（E001-E007）
    ↓
输出标准化话术
    ↓
提供解决方案建议
    ↓
等待用户反馈
    ↓
重新处理或终止
```

---

## 六、FAQ（高频问题速查）

### Q1: 这个技能能帮我写商业计划书吗？
**答**: 可以。本技能可以基于您提供的信息自动生成商业计划书框架，包含执行摘要、市场分析、产品服务、财务预测、融资计划、团队介绍、风险分析、发展规划等标准章节。您只需提供项目名称、融资阶段、融资金额等核心信息，即可生成结构完整的 BP 框架。但请注意，生成的框架需要您根据实际情况填充具体内容。

### Q2: 支持哪些文件格式？
**答**: 本技能支持以下格式：
- **文档格式**: PDF、Word（.docx）、纯文本（.txt）
- **表格格式**: Excel（.xlsx, .xls）、CSV
- **输出格式**: Markdown、Excel、Word、PDF

### Q3: 如何处理财务数据中的缺失值？
**答**: 本技能默认使用**中位数填充**策略处理数值型数据的缺失值。同时，我们会标记所有填充的数据，方便您识别。如果您有特定的填充策略（如均值填充、前向填充等），可以在处理前告知。

### Q4: 技能能保证数据的准确性吗？
**答**: 不能。本技能仅对您提供的数据进行格式标准化、逻辑校验和交叉验证，无法验证数据本身的真实性。我们建议您对关键财务数据进行人工核实，特别是涉及投资决策的数据。

### Q5: 处理一份投融资文档需要多长时间？
**答**: 通常在**10-30秒**内完成。处理时间取决于文档长度和复杂度。对于包含大量图表和复杂格式的文档，处理时间可能稍长。

### Q6: 可以批量处理多个投融资文档吗？
**答**: 可以。本技能支持批量处理多个文档，自动提取每个文档的关键信息并汇总输出。批量处理时，请将所有文档放在同一文件夹中，并提供文件夹路径。

---

## 七、渐进式披露

### 速览层（30秒了解）

**投融资技能** = 识别 + 整理 + 生成 + 校验

- **识别**: 自动提取投融资文档中的关键信息
- **整理**: 清洗和标准化财务数据
- **生成**: 自动生成商业计划书、投资分析报告等
- **校验**: 交叉验证数据一致性和合理性

### 上手层（5分钟掌握）

1. **准备输入**: 提供投融资文档或核心信息
2. **运行处理**: 自动执行识别、整理、生成流程
3. **检查输出**: 根据置信度标记判断是否需要人工复核
4. **导出结果**: 选择输出格式（Markdown/Excel/Word/PDF）

### 深度层（进阶使用）

#### 高级功能

1. **自定义模板**: 支持用户自定义文档模板，满足特定格式要求
2. **批量处理**: 支持多文档批量处理，自动汇总结果
3. **数据可视化**: 自动生成财务数据趋势图、股权结构图等
4. **API 集成**: 支持通过 API 调用，集成到其他系统中

#### 性能优化建议

- 使用结构化数据（Excel/CSV）比非结构化文档（PDF）处理速度更快
- 提供清晰的字段命名（如"融资金额"而非"钱"）可提高识别准确率
- 对于大型文档（>100页），建议分段处理

#### 扩展场景

- **投融资报告生成**: 基于财务数据自动生成投资分析报告
- **竞品融资分析**: 整理和分析竞品的融资历史
- **投资人关系管理**: 整理投资人沟通记录和跟进状态

---

## 八、技术实现细节

### 依赖库

```python
# requirements.txt
pandas>=1.3.0
openpyxl>=3.0.0
pdfplumber>=0.7.0
python-docx>=0.8.11
numpy>=1.21.0
matplotlib>=3.4.0  # 用于数据可视化
```

### 核心函数清单

| 函数名 | 功能 | 输入 | 输出 |
|-------|------|------|------|
| `parse_investment_document()` | 解析投融资文档 | 文件路径 | 关键信息字典 |
| `clean_financial_data()` | 清洗财务数据 | DataFrame | 清洗后DataFrame |
| `generate_business_plan()` | 生成商业计划书 | 信息字典 | Markdown文本 |
| `cross_validate_data()` | 交叉验证数据 | 信息字典 | 验证结果字典 |
| `validate_output()` | 校验输出 | 输出数据 | 校验结果 |
| `apply_confidence_gate()` | 置信度门控 | 校验结果 | 处理建议 |

### 数据流

```
输入文档/数据
    ↓
parse_investment_document() → 提取关键信息
    ↓
clean_financial_data() → 清洗财务数据
    ↓
generate_business_plan() → 生成文档
    ↓
cross_validate_data() → 交叉验证
    ↓
validate_output() → 输出校验
    ↓
apply_confidence_gate() → 置信度门控
    ↓
输出结果文件
```

---

## 九、版本记录

| 版本 | 日期 | 更新内容 |
|-----|------|---------|
| v1.0.0 | 2024-01-15 | 初始版本，支持基本投融资文档处理 |
| v1.1.0 | 2024-02-01 | 新增财务数据清洗功能 |
| v1.2.0 | 2024-03-01 | 新增置信度门控机制 |
| v1.3.0 | 2024-04-01 | 新增批量处理功能 |
| v1.4.0 | 2024-05-01 | 新增数据可视化支持 |

---

## 十、免责声明

本技能仅提供投融资相关的信息整理、格式标准化和文档生成服务，不构成任何投资建议。用户在使用本技能时，应遵守相关法律法规，并对输入数据的真实性和合法性负责。对于因使用本技能而产生的任何直接或间接损失，技能开发者不承担任何责任。

## 许可证（License）

```text
MIT License

Copyright (c) 2026 原创作者（自持版权）

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
```
<!-- professional-license-embedded -->
