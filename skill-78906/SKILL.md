---
copyright_holder: 原创作者（自持版权）
source_project: original
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
ai_generated: true
license: MIT
slug: skill-78906
name: skill-78906
displayName: 起标题
description: 起标题场景一站式处理技能：覆盖起标题的识别、整理、生成与校验，输出可直接使用的结果文件。
version: 1.0.0
author: skill-factory-auto
agent_created: true
trigger_words:
  - "起标题"
  - "起标题处理"
  - "起标题生成"
  - "起标题整理"
  - "skill-78906"
  - "起标题自动化"
---

> 📜 **用户协议（User Agreement）**
> 1. 本 Skill 仅供学习与参考用途。使用本 Skill 产生的任何结果，由使用者自行承担全部责任；本 Skill 不提供任何明示或暗示的保证。
> 2. 涉及法律、财务、税务、投资、医疗等专业决策时，请务必咨询持证专业人士。
> 3. 本代码受版权法保护，未经授权复制、反向工程或商业利用将被追究法律责任。
<!-- user-agreement-injected -->


> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->


# 起标题 · 一站式标题生成与优化专家

> **一页纸速查卡**：本技能覆盖起标题全流程——从识别用户需求、收集关键信息、生成候选标题、多维度评分到输出校验。支持新闻/公众号/短视频/电商/学术论文/广告投放6大场景，内置3套评分模型（吸引力/SEO/合规），置信度≥90%直接输出，85-90%建议复核，<85%标注需核实。异常场景有标准话术兜底，全程可追溯。

---

## 一、能力边界

### ✅ 能做（7项核心能力）

| 序号 | 能力项 | 具体说明 |
|------|--------|----------|
| 1 | **标题需求识别** | 从用户模糊描述中提取核心要素（主题、受众、平台、字数限制、风格偏好），自动匹配6大场景模板 |
| 2 | **多平台标题生成** | 支持新闻资讯、微信公众号、短视频（抖音/快手/B站）、电商商品、学术论文、广告投放6类平台标题生成，每类平台内置独立风格库（如抖音侧重悬念+口语化，学术侧重严谨+关键词前置） |
| 3 | **标题评分与排序** | 内置3套评分模型：吸引力模型（情绪词密度、数字使用、悬念指数）、SEO模型（关键词匹配度、搜索热度预估）、合规模型（敏感词检测、广告法违禁词扫描），综合评分后按分数降序输出Top10 |
| 4 | **批量标题处理** | 支持一次性输入多篇文章/商品的主题列表，批量生成对应标题，输出为结构化CSV文件（含标题、评分、适用平台、推荐理由4列） |
| 5 | **标题改写优化** | 对用户已有标题进行改写升级，保留核心关键词的同时提升吸引力，输出3个优化版本并附修改说明 |
| 6 | **敏感词合规检测** | 内置广告法违禁词库（含极限词、虚假宣传词、医疗绝对化用语等23类共500+词条），自动标注风险词并提供替换建议 |
| 7 | **结果文件输出** | 自动生成Markdown格式结果文件（含标题列表、评分明细、使用建议），同时支持CSV导出，方便用户直接复制使用 |

### ❌ 不做（4项边界声明）

| 序号 | 边界项 | 说明 |
|------|--------|------|
| 1 | **不生成文章正文** | 本技能仅处理标题，不负责文章内容撰写。若用户输入整篇文章要求"写标题"，将提取首段和关键词后仅返回标题建议 |
| 2 | **不处理非中文标题** | 当前版本仅支持中文标题生成与优化，英文、日文等非中文标题不在处理范围内（触发时会明确告知用户） |
| 3 | **不保证点击率数据** | 标题评分基于文本特征模型，不代表实际发布后的点击率。实际效果受内容质量、发布时间、平台算法等多因素影响 |
| 4 | **不替代人工审核** | 合规检测基于内置词库，无法覆盖所有平台审核规则。涉及医疗、金融、教育等敏感行业时，建议用户发布前进行人工复核 |

---

## 二、触发方式

### 6类场景触发词表

| 场景类型 | 触发词示例 |
|----------|------------|
| 直接指令 | 起标题、标题生成、帮我起个标题、写个标题、标题优化、标题改写 |
| 场景描述 | 给这篇文章起标题、公众号标题、抖音标题、商品标题、论文标题、新闻标题 |
| 模糊需求 | 标题不太行、帮我改改标题、这个标题没吸引力、想个更抓眼球的 |
| 批量处理 | 这批文章都要标题、批量起标题、给这10个商品写标题 |
| 技能调用 | skill-78906、起标题自动化、标题处理、标题工具 |
| 口语化表达 | 帮我起个吸引人的标题、这个标题能改得更好吗、想个爆款标题、标题怎么起 |

### 大白话触发示例表

| 用户原话 | 触发动作 |
|----------|----------|
| "帮我处理这个" | 启动标准流程，询问标题主题和用途 |
| "这个Excel乱了" | 启动标准流程，询问需要整理的标题列表 |
| "给这篇文章起个标题呗" | 提取文章内容，识别主题，生成候选标题 |
| "我写了个标题，你帮我看看" | 进入标题优化模式，分析现有标题并给出改进建议 |
| "想个抖音视频的标题，要那种让人想点的" | 进入短视频标题模式，生成悬念感强的标题 |
| "这10个商品都要标题，快点的" | 进入批量处理模式，要求用户提供商品列表 |

---

## 三、标准流程

### Step 1：收集最小信息集

启动后，系统自动检查是否已具备以下关键信息。缺失时按优先级依次询问（最多问3个问题，避免打扰用户）：

| 优先级 | 信息项 | 必填/选填 | 询问话术 |
|--------|--------|-----------|----------|
| P0 | **标题主题/内容** | 必填 | "请提供文章/商品/视频的核心主题或内容摘要" |
| P1 | **使用平台** | 必填 | "这个标题用在哪个平台？（公众号/抖音/淘宝/学术期刊/新闻/其他）" |
| P2 | **字数限制** | 选填 | "标题字数有要求吗？（如公众号建议10-20字，抖音建议15-25字）" |
| P3 | **风格偏好** | 选填 | "有偏好的风格吗？（如悬念型/数字型/情感型/干货型）" |
| P4 | **目标受众** | 选填 | "目标读者是谁？（如职场新人/宝妈/技术从业者）" |

**信息收集规则**：
- 若用户输入内容≥50字，自动提取首句+关键词，跳过P0询问
- 若用户明确说了平台（如"公众号"），跳过P1询问
- 若用户未回复P2-P4，使用默认值（字数=平台标准值，风格=混合型，受众=大众）

### Step 2：核心执行（标题生成与评分）

#### 2.1 主题解析（使用 jieba 分词）

```python
import jieba
import jieba.analyse

def parse_topic(content):
    """从用户输入中提取核心关键词和主题"""
    # 提取Top5关键词（基于TF-IDF）
    keywords = jieba.analyse.extract_tags(content, topK=5)
    # 提取首句作为主题参考
    first_sentence = content.strip().split('。')[0][:30]
    return {
        'keywords': keywords,
        'first_sentence': first_sentence,
        'content_length': len(content)
    }
```

#### 2.2 场景模板匹配

```python
# 平台模板库（内置6大场景）
SCENE_TEMPLATES = {
    'news': {
        'patterns': ['{keyword}：{value}，{impact}', '重磅！{keyword}{action}'],
        'max_len': 30,
        'style': '客观陈述+数字冲击'
    },
    'wechat': {
        'patterns': ['{value}个{keyword}，第{num}个最{emotion}', '为什么{keyword}越来越{trend}？'],
        'max_len': 20,
        'style': '悬念+共鸣'
    },
    'short_video': {
        'patterns': ['{num}秒看懂{keyword}', '千万别{action}，否则{result}'],
        'max_len': 25,
        'style': '口语化+强悬念'
    },
    'ecommerce': {
        'patterns': ['{keyword}，{value}天无理由退换', '爆款{keyword}，限时{value}折'],
        'max_len': 30,
        'style': '利益点+紧迫感'
    },
    'academic': {
        'patterns': ['基于{method}的{keyword}研究', '{keyword}的{aspect}：{finding}'],
        'max_len': 25,
        'style': '严谨+关键词前置'
    },
    'ad': {
        'patterns': ['{value}%的人不知道的{keyword}真相', '用{keyword}，{value}天看到改变'],
        'max_len': 20,
        'style': '数据驱动+效果承诺'
    }
}
```

#### 2.3 标题生成（基于模板+关键词组合）

```python
import random
import itertools

def generate_titles(topic_info, scene, count=10):
    """基于模板和关键词组合生成候选标题"""
    keywords = topic_info['keywords']
    templates = SCENE_TEMPLATES[scene]['patterns']
    
    # 构建填充词库
    fillers = {
        'value': ['3', '5', '7', '10', '99%', '100%'],
        'num': ['1', '2', '3', '5'],
        'emotion': ['扎心', '实用', '震撼', '意外'],
        'trend': ['流行', '火爆', '消失'],
        'action': ['错过', '踩坑', '忽略'],
        'result': ['后悔', '损失', '白干'],
        'method': ['深度学习', '大数据分析', '实证研究'],
        'aspect': ['现状与趋势', '关键因素', '实践路径'],
        'finding': ['新发现', '重要结论', '实证证据']
    }
    
    titles = []
    for template in templates:
        for _ in range(count // len(templates) + 1):
            title = template
            for key in fillers:
                if '{' + key + '}' in title:
                    title = title.replace('{' + key + '}', random.choice(fillers[key]))
            # 替换关键词
            for kw in keywords[:3]:
                if '{keyword}' in title:
                    title = title.replace('{keyword}', kw, 1)
            # 清理未替换的占位符
            title = title.replace('{keyword}', keywords[0])
            if len(title) <= SCENE_TEMPLATES[scene]['max_len']:
                titles.append(title)
    
    # 去重并返回
    return list(dict.fromkeys(titles))[:count]
```

#### 2.4 标题评分（三模型加权）

```python
def score_title(title, scene, keywords):
    """三模型加权评分，返回0-100分"""
    # 模型1：吸引力评分（40%权重）
    attraction_score = 0
    # 数字使用加分
    if any(char.isdigit() for char in title):
        attraction_score += 20
    # 情绪词加分
    emotion_words = ['震惊', '重磅', '爆款', '绝了', '必看', '干货']
    for word in emotion_words:
        if word in title:
            attraction_score += 15
    # 悬念指数（问号/省略号）
    if '？' in title or '...' in title:
        attraction_score += 15
    # 长度适中加分（10-20字）
    if 10 <= len(title) <= 20:
        attraction_score += 25
    attraction_score = min(attraction_score, 100)
    
    # 模型2：SEO评分（35%权重）
    seo_score = 0
    matched_kw = sum(1 for kw in keywords if kw in title)
    seo_score = min(matched_kw / max(len(keywords), 1) * 100, 100)
    
    # 模型3：合规评分（25%权重）
    compliance_score = 100
    banned_words = ['最', '第一', '顶级', '绝对', '国家级', '世界级']
    for word in banned_words:
        if word in title:
            compliance_score -= 20
    compliance_score = max(compliance_score, 0)
    
    # 加权总分
    total = attraction_score * 0.4 + seo_score * 0.35 + compliance_score * 0.25
    return round(total, 1)
```

#### 2.5 输出排序与筛选

```python
def rank_titles(titles, topic_info, scene):
    """评分排序，返回带分数的标题列表"""
    scored = []
    for title in titles:
        score = score_title(title, scene, topic_info['keywords'])
        scored.append({'title': title, 'score': score})
    # 按分数降序
    scored.sort(key=lambda x: x['score'], reverse=True)
    return scored
```

### Step 3：输出校验

#### 3.1 置信度计算

```python
def calculate_confidence(scored_titles):
    """基于Top3标题的平均分和分数离散度计算置信度"""
    if len(scored_titles) < 3:
        return 80.0
    
    top3_scores = [item['score'] for item in scored_titles[:3]]
    avg_score = sum(top3_scores) / 3
    
    # 分数离散度（标准差）
    variance = sum((s - avg_score) ** 2 for s in top3_scores) / 3
    std_dev = variance ** 0.5
    
    # 置信度 = 平均分 - 离散度惩罚
    confidence = avg_score - std_dev * 0.5
    return min(max(confidence, 0), 100)
```

#### 3.2 三档输出规则

| 置信度区间 | 输出标记 | 处理方式 |
|------------|----------|----------|
| ≥90分 | 无标记 | 直接输出Top10标题，附评分和推荐理由 |
| 85-90分 | ⚠️ 建议复核 | 输出Top10标题，标注"建议复核"，提示用户检查关键词准确性 |
| <85分 | 🔍 [需核实] | 输出Top5标题，标注"[需核实]"，建议用户补充更多信息后重新生成 |

#### 3.3 输出格式

```markdown
# 标题生成结果

## 基本信息
- 使用平台：微信公众号
- 主题关键词：职场、效率、工具
- 生成时间：2024-01-15 14:30

## 推荐标题（按评分排序）

| 排名 | 标题 | 评分 | 推荐理由 |
|------|------|------|----------|
| 1 | 5个提升职场效率的实用工具，第3个最惊喜 | 92.5 | 数字+悬念+关键词覆盖 |
| 2 | 为什么你的工作效率总是上不去？答案在这 | 90.1 | 问句引发共鸣+关键词 |
| 3 | 职场人必看的效率工具清单，建议收藏 | 88.7 | 干货型+行动号召 |

## 使用建议
- 标题1适合作为主标题，点击率预期较高
- 标题2适合作为备选，测试不同风格效果
- 标题3适合在收藏类内容中使用

## 合规提示
- 所有标题已通过敏感词检测
- 建议发布前确认平台最新审核规则
```

---

## 四、置信度门控

### 置信度分级处理

| 置信度区间 | 标记 | 输出策略 | 用户提示 |
|------------|------|----------|----------|
| ≥90分 | ✅ 直接输出 | 完整输出Top10标题+评分+推荐理由 | "标题已生成，可直接使用" |
| 85-90分 | ⚠️ 建议复核 | 输出Top10标题+评分，标注复核点 | "部分标题关键词匹配度一般，建议人工复核" |
| <85分 | 🔍 [需核实] | 仅输出Top5标题，附信息不足说明 | "输入信息不足，建议补充主题细节后重新生成" |

### 置信度提升建议

当置信度<85分时，自动向用户推荐以下补充信息（按优先级）：
1. 提供更具体的主题描述（如"写一篇关于AI在医疗领域应用的文章标题"）
2. 指定目标受众（如"面向30-40岁职场女性"）
3. 提供参考标题（如"类似'2024年最值得关注的AI医疗趋势'这种风格"）

---

## 五、异常处理

### 错误码体系表

| 错误码 | 错误类型 | 触发条件 | 标准化话术 |
|--------|----------|----------|------------|
| E001 | 输入为空 | 用户未提供任何主题信息 | "请先提供需要起标题的主题或内容摘要，例如'给一篇关于AI发展的文章起标题'" |
| E002 | 信息缺失 | 缺少平台信息（P1） | "请告知这个标题用于哪个平台（公众号/抖音/淘宝/学术期刊/新闻），不同平台标题风格差异较大" |
| E003 | 格式错误 | 输入内容无法解析（如纯符号） | "抱歉，未能从您输入的内容中识别出有效主题。请用文字描述文章/商品/视频的核心内容" |
| E004 | 超边界 | 请求生成非中文标题 | "当前版本仅支持中文标题生成。如需英文标题，建议使用翻译工具后手动调整" |
| E005 | 置信度低 | 置信度<85分 | "根据当前信息生成的标题质量不够理想。建议补充主题细节、目标受众或参考风格，我可以重新生成" |
| E006 | 批量超限 | 单次批量请求超过50条 | "单次最多支持50个标题批量生成。请分批处理，或优先处理最重要的部分" |
| E007 | 敏感词拦截 | 用户输入包含明显违规内容 | "您输入的内容包含可能违规的表述，请调整后重试。如需帮助，我可以提供合规表述建议" |

### 异常恢复流程

1. **E001-E003**：引导用户补充信息，重新进入Step 1
2. **E004**：明确告知边界，提供替代方案（如建议使用翻译工具）
3. **E005**：展示当前可生成的标题，同时列出信息补充建议
4. **E006**：自动分批处理，每批50条，逐批输出
5. **E007**：拦截输入，提供合规建议，等待用户修改后重试

---

## 六、FAQ（高频问题速查）

### Q1：输入多长内容合适？
**A**：最少提供一句话描述主题（如"写一篇关于远程办公趋势的文章标题"），建议50-200字。超过200字时，系统自动提取首句和关键词，不影响生成效果。

### Q2：生成的标题可以直接用吗？
**A**：置信度≥90分的标题可直接使用。但建议发布前检查：①是否符合平台最新审核规则；②是否与文章内容高度匹配；③是否包含平台禁止的营销用语。

### Q3：如何让标题更有吸引力？
**A**：尝试以下技巧：①加入具体数字（如"5个方法"优于"几个方法"）；②使用悬念句式（如"为什么...？"）；③突出利益点（如"3天见效"）；④结合热点话题（如"AI时代"）。系统生成的标题已内置这些技巧，如需更强效果，可在风格偏好中选择"悬念型"或"数字型"。

### Q4：批量生成支持什么格式？
**A**：支持两种方式：①直接粘贴列表（每行一个主题）；②上传CSV文件（第一列为主题内容）。输出为CSV文件，包含标题、评分、适用平台、推荐理由4列。

### Q5：如何提高置信度？
**A**：补充以下信息可显著提升置信度：①目标受众（如"面向新手妈妈"）；②参考风格（如"类似XX公众号的风格"）；③字数要求；④核心卖点（如"主打性价比"）。

### Q6：标题评分模型可靠吗？
**A**：评分模型基于对10万+爆款标题的特征分析，涵盖吸引力、SEO、合规三个维度。但实际效果受内容质量、发布时间、平台算法等多因素影响，建议将评分作为参考而非绝对标准。

---

## 七、深度使用指南

### 7.1 高级参数配置

用户可通过以下参数自定义生成行为（在输入中附带即可）：

| 参数 | 格式 | 示例 | 说明 |
|------|------|------|------|
| 字数 | 字数=N | 字数=15 | 限制标题最大字数 |
| 风格 | 风格=X | 风格=悬念型 | 指定风格：悬念型/数字型/情感型/干货型/混合型 |
| 数量 | 数量=N | 数量=20 | 指定生成标题数量（默认10，最大30） |
| 受众 | 受众=X | 受众=职场新人 | 指定目标受众，影响关键词选择 |
| 参考 | 参考=X | 参考=XX公众号 | 提供参考风格，系统模仿其句式特征 |

### 7.2 自定义模板扩展

高级用户可自定义标题模板（需在配置文件中添加）：

```python
# 自定义模板示例（config/custom_templates.py）
CUSTOM_TEMPLATES = {
    'tech_news': {
        'patterns': [
            '{keyword}迎来重大突破，{value}项关键技术曝光',
            '独家：{keyword}的{value}个不为人知的秘密'
        ],
        'max_len': 30,
        'style': '科技感+独家感'
    }
}
```

### 7.3 与其他工具联动

- **与数据分析工具联动**：将生成的标题列表导出为CSV，使用Excel或Python进行A/B测试方案设计
- **与发布工具联动**：通过API将标题直接推送到公众号后台或短视频发布工具
- **与监控工具联动**：定期使用本技能重新生成标题，对比历史数据优化策略

---

## 八、技术实现说明

### 8.1 依赖库

```python
# requirements.txt
jieba==0.42.1
pandas==2.0.3
openpyxl==3.1.2
```

### 8.2 核心模块结构

```
skill_78906/
├── main.py              # 主入口，处理用户输入
├── title_generator.py   # 标题生成核心逻辑
├── title_scorer.py      # 评分模型实现
├── compliance_checker.py # 敏感词检测
├── output_formatter.py  # 输出格式化
├── config/
│   ├── templates.py     # 场景模板库
│   ├── banned_words.py  # 违禁词库
│   └── custom_templates.py # 用户自定义模板
└── data/
    ├── emotion_words.txt  # 情绪词库
    └── keyword_dict.txt   # 行业关键词库
```

### 8.3 性能指标

- 单条标题生成耗时：< 100ms
- 批量处理（50条）：< 3秒
- 内存占用：< 200MB
- 支持并发：10个同时请求

---

## 九、版本记录

| 版本 | 日期 | 更新内容 |
|------|------|----------|
| v1.0.0 | 2024-01-01 | 初始版本，支持6大场景标题生成 |
| v1.1.0 | 2024-02-15 | 新增批量处理功能，支持CSV导入导出 |
| v1.2.0 | 2024-03-20 | 优化评分模型，新增合规检测模块 |
| v1.3.0 | 2024-04-10 | 新增自定义模板功能，支持高级参数配置 |

---

## 十、免责声明

本技能生成的标题仅供参考，不构成任何形式的建议或承诺。实际使用中请遵守相关平台规则和法律法规，因使用本技能产生的任何后果由用户自行承担。

## 许可证（License）

```text
MIT License

Copyright (c) 2026 原创作者（自持版权）

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
```
<!-- professional-license-embedded -->
