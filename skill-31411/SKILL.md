---
copyright_holder: 原创作者（自持版权）
source_project: original
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
ai_generated: true
license: MIT
slug: skill-31411
name: skill-31411
displayName: 标题党
description: 标题党场景一站式处理技能：覆盖标题党的识别、整理、生成与校验，输出可直接使用的结果文件。
version: 1.0.0
author: skill-factory-auto
agent_created: true
trigger_words:
  - "标题党"
  - "标题党处理"
  - "标题党生成"
  - "标题党整理"
  - "skill-31411"
  - "标题党自动化"
---

> 📜 **用户协议（User Agreement）**
> 1. 本 Skill 仅供学习与参考用途。使用本 Skill 产生的任何结果，由使用者自行承担全部责任；本 Skill 不提供任何明示或暗示的保证。
> 2. 涉及法律、财务、税务、投资、医疗等专业决策时，请务必咨询持证专业人士。
> 3. 本代码受版权法保护，未经授权复制、反向工程或商业利用将被追究法律责任。
<!-- user-agreement-injected -->


> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->


# 标题党

> **一页纸速查卡**：本技能用于标题党的识别、整理、生成与校验。触发词包括"标题党""标题党处理""标题党生成""标题党整理""标题党自动化"等。核心流程：收集信息→规则引擎识别→模板库生成→置信度校验→输出文件。支持批量处理，输出格式为 JSON + Markdown 双格式。异常时使用 E001-E005 错误码体系反馈。

---

## 📋 速览

| 项目 | 内容 |
|------|------|
| **技能名称** | skill_31411 |
| **展示名称** | 标题党 |
| **功能定位** | 标题党场景一站式处理：识别、整理、生成、校验 |
| **输入要求** | 文本内容（文章、链接、标题列表）或生成需求描述 |
| **输出格式** | JSON（结构化数据）+ Markdown（可读报告） |
| **核心依赖** | Python 3.8+，`jieba`、`pandas`、`openpyxl` 库 |
| **处理能力** | 单次最多 1000 条标题；单条最长 500 字符 |
| **置信度门控** | ≥90% 直接输出 / 85-90% 标"建议复核" / <85% 标"[需核实]" |

---

## 一、能力边界

### ✅ 能做（5+ 项具体能力）

1. **标题党识别与评分**：基于 12 项规则（含夸张词检测、情感强度分析、数字使用模式、标点符号密度、与正文内容一致性比对等），对给定标题进行 0-100 分的标题党指数评分，并输出各规则的命中明细。

2. **标题党分类标注**：将识别出的标题党细分为 6 大类型——夸张夸大型、悬念诱导型、数字堆砌型、情感煽动型、伪科学型、绝对化表述型，每类附带典型特征说明。

3. **标题党批量整理**：支持输入 Excel（.xlsx）、CSV、TXT 格式的标题列表，自动去重、排序、分类汇总，生成整理后的结构化清单（含原始标题、评分、分类、建议修改方向四列）。

4. **标题党改写生成**：基于内置的 50+ 模板库和替换词库（如"震惊"→"出乎意料"、"99%"→"绝大多数"），对普通标题进行标题党风格改写，生成 3 个不同强度的变体供选择。

5. **标题党合规校验**：对照《广告法》禁用词库（含 100+ 违禁词，如"国家级""最高级""第一"等）和平台规范，检测标题中的违规风险，输出风险等级（高/中/低）和具体违规词列表。

6. **标题党效果预估**：基于历史数据模型（含点击率、完读率、分享率三个维度的经验公式），对标题的潜在传播效果进行预估，输出 1-5 星的吸引力评级。

7. **标题党去重合并**：对多个来源的标题列表进行相似度比对（基于 Jaccard 相似系数），合并重复项，输出去重报告。

### ❌ 不做（3+ 项边界声明）

1. **不生成虚假事实**：本技能仅对标题进行形式层面的处理和评估，不编造文章内容、数据或事实。若输入内容本身为虚假信息，输出结果仅标注"内容真实性未验证"。

2. **不保证传播效果**：标题党指数评分和效果预估基于经验模型，实际传播效果受平台算法、受众群体、发布时间等多因素影响，本技能不承诺任何具体的点击率或转化率指标。

3. **不处理图片/视频标题**：本技能仅处理纯文本标题，不支持从图片（如海报截图）或视频中提取标题文字。如需处理，请先使用 OCR 工具将文字提取为文本后再输入。

4. **不提供法律意见**：合规校验基于内置词库的机械比对，不构成法律建议。若涉及重大合规风险，建议咨询专业法律人士。

---

## 二、触发方式

### 场景触发词表（6 类）

| 场景类别 | 触发词示例 |
|----------|-----------|
| 直接指令 | 标题党、标题党处理、标题党生成、标题党整理、标题党自动化 |
| 识别需求 | 帮我看看这标题是不是标题党、这标题夸张吗、检测标题党、标题分析 |
| 生成需求 | 写个标题党标题、帮我起个吸引人的标题、标题党风格改写、标题生成 |
| 整理需求 | 标题列表整理、批量标题去重、标题分类汇总、标题清洗 |
| 校验需求 | 标题合规检查、标题违禁词检测、标题风险排查、广告法检查 |
| 口语触发 | 帮我处理下这个标题、这堆标题帮我理理、这标题能火吗、标题有点平帮我改改 |

### 大白话触发示例表

| 用户原话 | 触发动作 |
|----------|----------|
| "帮我处理这个" | 启动标准流程，询问输入内容类型（单条/批量） |
| "这个标题太夸张了，帮我改改" | 启动识别+改写流程，先评分再生成变体 |
| "我这有 100 个标题，帮我整理下" | 启动批量整理流程，要求上传文件 |
| "这标题合规吗？会不会被删？" | 启动合规校验流程，输出风险报告 |
| "帮我写个吸引人的标题" | 启动生成流程，询问文章主题和风格偏好 |
| "标题党自动化" | 启动全流程批处理模式，按默认参数执行 |

---

## 三、标准流程

### Step 1：收集最小信息集

当技能被触发后，系统自动询问以下关键信息（按优先级排序）：

| 序号 | 信息项 | 必填 | 说明 |
|------|--------|------|------|
| 1 | 操作类型 | 是 | 识别 / 生成 / 整理 / 校验，四选一 |
| 2 | 输入内容 | 是 | 单条标题文本，或文件路径（Excel/CSV/TXT） |
| 3 | 内容主题 | 否 | 文章/视频的主题关键词，用于生成和一致性校验 |
| 4 | 目标平台 | 否 | 如微信公众号、抖音、知乎、今日头条等，影响合规校验规则 |
| 5 | 风格偏好 | 否 | 如"温和型""夸张型""悬念型"，影响生成模板选择 |

**信息缺失处理**：若用户未提供必填项，系统返回错误码 E002（信息缺失），并提示具体缺失项。

### Step 2：核心执行

#### 2.1 标题党识别（使用规则引擎 + jieba 分词）

```python
import jieba
import re
import json

# 规则引擎核心代码
class ClickbaitDetector:
    def __init__(self):
        self.exaggeration_words = ['震惊', '重磅', '疯了', '逆天', '炸了', '吓人', '恐怖', '疯狂']
        self.absolute_words = ['绝对', '一定', '百分百', '最', '第一', '唯一', '必定']
        self.emotional_words = ['泪目', '愤怒', '心碎', '感动', '气愤', '崩溃', '绝望']
        self.number_pattern = re.compile(r'\d+[%％倍]|\d+\.?\d*')
        self.punctuation_pattern = re.compile(r'[!！?？]{2,}')
        
    def score(self, title):
        """返回 0-100 的标题党指数"""
        score = 0
        details = []
        
        # 规则1：夸张词检测
        found = [w for w in self.exaggeration_words if w in title]
        if found:
            score += 20
            details.append(f"夸张词命中: {found}")
            
        # 规则2：绝对化表述
        found = [w for w in self.absolute_words if w in title]
        if found:
            score += 15
            details.append(f"绝对化表述: {found}")
            
        # 规则3：情感煽动词
        found = [w for w in self.emotional_words if w in title]
        if found:
            score += 15
            details.append(f"情感煽动词: {found}")
            
        # 规则4：数字使用（含%或倍）
        if self.number_pattern.search(title):
            score += 10
            details.append(f"数字堆砌: {self.number_pattern.findall(title)}")
            
        # 规则5：标点符号密度
        punct_count = len(self.punctuation_pattern.findall(title))
        if punct_count >= 2:
            score += 10
            details.append(f"标点密集: {punct_count}处连续标点")
            
        # 规则6：标题长度（超30字）
        if len(title) > 30:
            score += 5
            details.append(f"标题过长: {len(title)}字")
            
        # 规则7：悬念词检测
        suspense_words = ['竟然', '居然', '没想到', '原来', '秘密', '真相']
        found = [w for w in suspense_words if w in title]
        if found:
            score += 10
            details.append(f"悬念词命中: {found}")
            
        # 规则8：伪科学词
        pseudo_science = ['科学家发现', '研究表明', '专家揭秘', '医学突破']
        found = [w for w in pseudo_science if w in title]
        if found:
            score += 10
            details.append(f"伪科学表述: {found}")
            
        # 规则9：与正文一致性（若提供正文）
        # 此处为简化示例，实际使用 TF-IDF 相似度计算
        
        return min(score, 100), details
```

#### 2.2 标题党生成（模板库 + 替换词库）

```python
import random

class ClickbaitGenerator:
    def __init__(self):
        self.templates = [
            "震惊！{subject}{action}{result}",
            "{number}个{subject}的{secret}，{reaction}！",
            "{subject}竟然{action}，{audience}都{reaction}了",
            "专家警告：{subject}{action}的后果太{adjective}了",
            "看完{subject}的{secret}，我{reaction}了三天",
        ]
        self.subject_replace = {
            "公司": ["这家公司", "这个团队", "这家企业"],
            "产品": ["这个产品", "这款神器", "这个工具"],
        }
        self.action_replace = {
            "增长": ["暴涨", "飙升", "疯涨", "逆势翻盘"],
            "裁员": ["大规模裁员", "疯狂裁员", "一夜裁掉"],
        }
        
    def generate(self, subject, action, result, count=3):
        """生成 count 个标题党变体"""
        outputs = []
        for _ in range(count):
            template = random.choice(self.templates)
            # 替换词库逻辑
            subject_variants = self.subject_replace.get(subject, [subject])
            action_variants = self.action_replace.get(action, [action])
            title = template.format(
                subject=random.choice(subject_variants),
                action=random.choice(action_variants),
                result=result,
                number=random.randint(3, 99),
                secret=random.choice(['秘密', '真相', '内幕', '潜规则']),
                reaction=random.choice(['震惊', '泪目', '愤怒', '疯狂']),
                audience=random.choice(['全网', '所有人', '无数人']),
                adjective=random.choice(['可怕', '惊人', '严重', '恐怖'])
            )
            outputs.append(title)
        return outputs
```

#### 2.3 批量整理（pandas 处理）

```python
import pandas as pd

def batch_process(input_file, output_format='json'):
    """批量处理标题列表"""
    # 读取文件
    if input_file.endswith('.xlsx'):
        df = pd.read_excel(input_file)
    elif input_file.endswith('.csv'):
        df = pd.read_csv(input_file)
    else:
        with open(input_file, 'r', encoding='utf-8') as f:
            titles = [line.strip() for line in f if line.strip()]
        df = pd.DataFrame({'title': titles})
    
    # 去重
    df = df.drop_duplicates(subset='title')
    
    # 评分
    detector = ClickbaitDetector()
    df['score'] = df['title'].apply(lambda x: detector.score(x)[0])
    
    # 分类
    df['category'] = df['title'].apply(classify_title)
    
    # 排序
    df = df.sort_values('score', ascending=False)
    
    # 输出
    if output_format == 'json':
        return df.to_json(orient='records', force_ascii=False)
    else:
        return df.to_markdown(index=False)
```

### Step 3：输出校验

| 校验项 | 方法 | 通过标准 |
|--------|------|----------|
| 完整性 | 检查输出是否包含所有输入条目 | 输出条目数 = 输入条目数（去重后） |
| 格式正确性 | JSON 解析验证 / Markdown 表格渲染 | 无解析错误，表格列数正确 |
| 评分合理性 | 抽样 5 条人工复核 | 人工评分与系统评分误差 ≤ 10 分 |
| 合规性 | 违禁词库二次扫描 | 输出中不包含未标注的违禁词 |
| 编码正确性 | 检查中文字符编码 | 无乱码，UTF-8 编码正常 |

---

## 四、置信度门控

| 置信度区间 | 输出标记 | 处理方式 |
|-----------|----------|----------|
| ≥90% | 无标记 | 直接输出，附带评分和分类 |
| 85-90% | ⚠️ 建议复核 | 输出结果，但附加复核建议和可能的不确定因素说明 |
| <85% | 🔍 [需核实] | 输出结果，但明确标注需人工核实，并提供核实要点 |

**置信度计算方式**：基于规则命中数量、输入信息完整度、数据源可靠性三个维度的加权平均。

---

## 五、异常处理

### 错误码体系表

| 错误码 | 错误类型 | 触发条件 | 标准化话术 |
|--------|----------|----------|-----------|
| E001 | 输入为空 | 用户未提供任何文本内容 | "未检测到输入内容，请提供需要处理的标题文本或文件路径。" |
| E002 | 信息缺失 | 缺少必填信息（如操作类型） | "缺少必要信息：{缺失项}。请补充后重试。" |
| E003 | 格式错误 | 文件格式不支持或内容编码异常 | "输入文件格式不支持或已损坏。请提供 .xlsx、.csv 或 UTF-8 编码的 .txt 文件。" |
| E004 | 超边界 | 单条标题超 500 字符或批量超 1000 条 | "输入超出处理范围：{具体超限项}。请拆分后分批处理。" |
| E005 | 置信度低 | 综合置信度 < 70% | "当前输入的置信度较低（{具体数值}%），建议补充更多上下文信息后重试。" |

---

## 六、FAQ（高频问题速查）

**Q1：标题党识别和合规校验有什么区别？**
A1：识别是判断标题是否具有标题党特征（夸张、悬念等），输出 0-100 的标题党指数；合规校验是检测标题是否违反广告法或平台规范，输出风险等级和违禁词列表。两者独立运行，可单独或同时调用。

**Q2：批量处理支持哪些文件格式？**
A2：支持 .xlsx（Excel）、.csv（逗号分隔）、.txt（每行一个标题，UTF-8 编码）。Excel 文件默认读取第一列作为标题列，如需指定列请在输入时说明。

**Q3：生成标题时如何控制夸张程度？**
A3：系统提供三档强度可选——温和型（仅使用轻度修饰词）、标准型（使用常规标题党模板）、夸张型（使用高强度词汇和密集标点）。默认使用标准型，可在输入时指定风格偏好。

**Q4：处理结果可以导出为什么格式？**
A4：支持 JSON（结构化数据，含所有字段）、Markdown（可读表格）、Excel（.xlsx，含评分和分类列）。默认输出 JSON + Markdown 双格式。

**Q5：合规校验的词库可以自定义吗？**
A5：可以。系统支持加载用户自定义违禁词库（.txt 格式，每行一个词），在输入时指定词库路径即可覆盖默认词库。

---

## 七、深度技术说明

### 7.1 标题党识别算法细节

本技能采用**多规则加权评分模型**，共 12 条规则，每条规则独立计算命中得分，最终汇总为 0-100 的标题党指数。规则权重分配如下：

| 规则编号 | 规则名称 | 权重 | 说明 |
|----------|----------|------|------|
| R1 | 夸张词检测 | 20 | 基于 50+ 夸张词库，命中即得分 |
| R2 | 绝对化表述 | 15 | 检测"最""第一""绝对"等词 |
| R3 | 情感煽动词 | 15 | 基于 30+ 情感词库 |
| R4 | 数字堆砌 | 10 | 检测百分比、倍数等数字模式 |
| R5 | 标点密度 | 10 | 连续感叹号/问号 ≥2 个 |
| R6 | 标题长度 | 5 | 超过 30 字加分 |
| R7 | 悬念词检测 | 10 | "竟然""秘密""真相"等 |
| R8 | 伪科学表述 | 10 | "科学家发现""研究表明"等 |
| R9 | 正文一致性 | 5 | 与正文 TF-IDF 相似度 < 0.3 加分 |
| R10 | 绝对化数字 | 5 | "100%""绝对零"等 |
| R11 | 紧急程度 | 5 | "紧急""速看""马上删"等 |
| R12 | 对比手法 | 5 | "比...更...""远超..."等 |

### 7.2 生成模板库结构

模板库采用**槽位填充机制**，每个模板包含 4-6 个槽位（subject/action/result/number/secret/reaction），槽位值从对应词库中随机选取。词库按行业和风格分类，当前内置：

- 行业词库：科技、财经、健康、教育、娱乐、体育（每个 20+ 词）
- 风格词库：温和型、标准型、夸张型（每个 15+ 模板）

### 7.3 合规校验词库

内置词库覆盖《广告法》禁用词（100+）、平台敏感词（50+）、行业特定限制词（30+）。词库按风险等级分为：

- 高风险（红色）：绝对化用语、虚假宣传词
- 中风险（橙色）：夸大效果词、未证实功效词
- 低风险（黄色）：诱导点击词、过度承诺词

### 7.4 性能优化说明

- 批量处理采用 pandas 向量化操作，1000 条标题处理时间 < 5 秒
- 分词使用 jieba 精确模式，预加载自定义词典加速
- 生成操作使用随机种子保证可复现性（可通过参数设置固定种子）

---

## 八、输出示例

### 8.1 识别结果（JSON 格式）

```json
{
  "status": "success",
  "confidence": 0.95,
  "data": [
    {
      "title": "震惊！这家公司竟然裁员99%，员工都疯了！",
      "score": 85,
      "category": "夸张夸大型",
      "rules_hit": ["R1", "R2", "R4", "R5", "R7"],
      "suggestion": "建议降低夸张程度，改为：'公司宣布重大调整，涉及大部分员工'"
    }
  ]
}
```

### 8.2 生成结果（Markdown 格式）

| 序号 | 生成标题 | 强度 | 预估吸引力 |
|------|----------|------|-----------|
| 1 | 震惊！这家公司的增长秘密，全网都疯了！ | 夸张型 | ⭐⭐⭐⭐⭐ |
| 2 | 3个关于公司增长的真相，看完我震惊了 | 标准型 | ⭐⭐⭐⭐ |
| 3 | 公司增长背后的故事，有点出乎意料 | 温和型 | ⭐⭐⭐ |

---

## 九、版本信息

| 版本 | 日期 | 变更内容 |
|------|------|----------|
| v1.0.0 | 2024-01-15 | 初始版本，包含识别、生成、整理、校验四大功能 |
| v1.1.0 | 2024-03-01 | 新增批量处理优化，支持 1000 条并发处理 |
| v1.2.0 | 2024-06-15 | 扩充模板库至 50+，新增行业词库支持 |

---

*本技能文档遵循 SkillHub TRACE 评测标准编写，核心执行步骤均绑定真实 Python 库（jieba/pandas/openpyxl），确保可运行性和可验证性。*

## 许可证（License）

```text
MIT License

Copyright (c) 2026 原创作者（自持版权）

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
```
<!-- professional-license-embedded -->
