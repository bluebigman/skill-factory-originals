---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: ai-reputation-claude
name: ai-reputation-claude
displayName: 舆情声誉 竞品对标 洞察报告
description: 解析在线评论，量化品牌声誉，对标竞品，输出可执行洞察报告。
version: 3.0.1
rules_version: cpr-20260819-n551
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/ai-reputation-claude
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: LinguaForge
agent_created: true
trigger_words: ["声誉分析", "评论分析", "品牌舆情", "竞品对标", "口碑洞察", "声誉量化"]
---

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->


> 本内容由 AI 生成，仅供学习参考 <!-- ai-generated-notice -->

# AI 声誉分析器（ai-reputation-claude）技能文档

## 一、能力边界：一页纸速查卡

本技能用于从在线评论数据中提取品牌声誉信号，进行量化评估，并与竞品进行横向对比，最终生成结构化的洞察报告。

### 1.1 能做什么（Do）

| 编号 | 能力项 | 说明 | 输入要求 |
|------|--------|------|----------|
| D1 | 评论数据清洗 | 去除重复、广告、无意义字符 | 原始评论文本（UTF-8） |
| D2 | 情感极性判定 | 将评论分为正面/中性/负面 | 单条评论 ≥ 5 个汉字 |
| D3 | 主题聚类 | 自动归纳高频话题（如物流、质量、客服） | 评论集 ≥ 50 条 |
| D4 | 声誉评分 | 输出 0-100 综合声誉指数 | 评论集 ≥ 30 条 |
| D5 | 竞品对比 | 多品牌同维度雷达图数据输出 | 每个品牌评论 ≥ 30 条 |
| D6 | 洞察建议生成 | 基于短板自动生成改进建议 | 评分结果 + 主题分布 |

### 1.2 不能做什么（Don't）

| 编号 | 限制项 | 说明 |
|------|--------|------|
| X1 | 不预测销量 | 声誉指数与销量无因果模型 |
| X2 | 不处理非文本数据 | 图片、视频评论需先转文本 |
| X3 | 不判定评论真实性 | 不区分水军与真实用户（需外部标记） |
| X4 | 不提供实时流式分析 | 仅支持批量文件处理 |
| X5 | 不输出法律意见 | 涉及法律风险请咨询专业人士 |

### 1.3 适用对象

- 品牌经理：季度声誉复盘
- 市场调研员：竞品动态监测
- 产品运营：用户反馈归因
- 初创团队：种子用户口碑摸底

---

## 二、触发方式：场景映射表

| 用户说（大白话） | 触发词命中 | 技能动作 |
|------------------|------------|----------|
| "帮我看看我们店铺最近评价怎么样" | 评论分析 | 执行 D1→D2→D4 |
| "对比一下我和竞品的口碑差距" | 竞品对标 | 执行 D1→D5 |
| "用户都在吐槽什么？" | 口碑洞察 | 执行 D1→D3→D6 |
| "这个品牌声誉打几分？" | 声誉量化 | 执行 D4 |
| "分析下差评集中在哪方面" | 品牌舆情 | 执行 D2→D3 |

---

## 三、标准流程：从输入到输出

### 3.1 前置条件（必须满足）

| 条件 | 要求 | 校验方式 |
|------|------|----------|
| 数据格式 | CSV 或 JSON，含 `text` 字段 | 文件头检查 |
| 数据量 | 单品牌 ≥ 30 条有效评论 | 行数统计 |
| 编码 | UTF-8 无 BOM | 字节检查 |
| 字段 | 可选：`brand`, `date`, `rating` | 缺失自动置空 |

### 3.2 执行步骤（分步编号）

**Step 1：数据加载与校验**
```python
# 伪代码示意
data = load_reviews("input.csv")
assert len(data) >= 30, "评论数量不足"
```

**Step 2：文本清洗**
- 去除 URL、@提及、emoji（保留中文标点）
- 统一全半角
- 去除重复评论（MD5 去重）

**Step 3：情感判定**
- 基于词典 + 规则（否定词翻转、程度副词加权）
- 输出：`positive` / `neutral` / `negative`

**Step 4：主题聚类**
- 使用 LDA 或 TF-IDF + KMeans
- 输出：主题词 Top 5 + 占比

**Step 5：声誉评分**
```
声誉指数 = 60 * 正面占比 + 30 * 中性占比 + 10 * 负面占比
          + 5 * (平均星级 / 5) * 10   # 若有星级字段
```
- 映射：≥80 优秀，60-79 良好，40-59 一般，<40 预警

**Step 6：竞品对比（可选）**
- 输入多个品牌数据，输出对比表 + 雷达图数据

**Step 7：报告生成**
- 输出 Markdown 报告，包含：概览、评分、主题分布、竞品对比、改进建议

### 3.3 输出规范

```markdown
# 品牌声誉报告：{brand_name}
## 概览
- 评论总数：{n}
- 正面/中性/负面：{p}% / {neu}% / {neg}%
- 声誉指数：{score}/100（{等级}）

## 主题分布
| 主题 | 占比 | 情感倾向 |
|------|------|----------|
| 物流 | 35% | 负面为主 |

## 竞品对比（如有）
| 品牌 | 声誉指数 | 优势主题 | 劣势主题 |

## 改进建议
1. {基于负面主题的具体建议}
```

---

## 四、置信度门控

当信息不足时，**禁止编造**。使用以下占位符：

| 场景 | 占位符 | 示例 |
|------|--------|------|
| 缺少品牌名 | `[需核实:品牌名称]` | 报告标题显示该占位符 |
| 评论数不足 | `[需核实:数据量不足，仅X条]` | 评分处显示 |
| 无日期字段 | `[需核实:时间范围未知]` | 趋势分析处显示 |
| 主题聚类不稳定 | `[需核实:主题置信度<0.6]` | 主题列表处显示 |

**规则**：任何占位符出现时，报告顶部必须显示警告横幅：
> ⚠️ 本报告含未核实字段，请补充数据后重新生成。

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| E001 | 文件不存在 | "未找到输入文件，请检查路径" | 确认文件路径 |
| E002 | 编码错误 | "文件编码非 UTF-8，请转换" | 用记事本另存为 UTF-8 |
| E003 | 数据量不足 | "有效评论少于30条，无法评分" | 补充数据或降低要求 |
| E004 | 字段缺失 | "缺少 text 字段，请检查表头" | 添加 text 列 |
| E005 | 竞品数据不齐 | "竞品评论数不一致，对比可能偏差" | 平衡各品牌数据量 |
| E006 | 主题聚类失败 | "文本多样性不足，无法聚类" | 增加评论量或调整参数 |

---

## 六、FAQ 反模式对照

| 常见坑（反模式） | 正确做法（正模式） |
|------------------|---------------------|
| ❌ 直接拿 5 条评论出报告 | ✅ 至少 30 条，否则输出占位符 |
| ❌ 忽略中性评论，只分正负 | ✅ 三分类，中性占比影响评分 |
| ❌ 把评分当唯一指标 | ✅ 结合主题分布看归因 |
| ❌ 不清理重复评论 | ✅ MD5 去重，避免刷屏影响 |
| ❌ 跨平台数据直接合并 | ✅ 标注来源，分平台对比 |

---

## 七、渐进式披露：分层次阅读

### 7.1 速查卡（30 秒上手）

```
输入：CSV/JSON 含 text 字段，≥30 条
命令：python run.py --input reviews.csv --brand "我的品牌"
输出：Markdown 报告 + 控制台摘要
```

### 7.2 新手路径（首次使用）

1. 准备数据文件（参考 3.1 前置条件）
2. 运行 `python run.py --selftest` 验证环境
3. 执行 `python run.py --input your_file.csv --brand "品牌名"`
4. 查看生成的 `report.md`

### 7.3 进阶路径（深度使用）

1. 多品牌对比：`--compare brand1.csv brand2.csv`
2. 自定义词典：`--lexicon my_words.json`
3. 输出 JSON 原始数据：`--output-format json`
4. 结合 CI/CD：将 `run.py` 集成到定时任务

---

## 八、参数参考表

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `--input` | str | 必填 | 输入文件路径 |
| `--brand` | str | 必填 | 品牌名称 |
| `--compare` | list | 空 | 竞品文件列表 |
| `--lexicon` | str | 内置 | 自定义情感词典 |
| `--min-reviews` | int | 30 | 最小评论数阈值 |
| `--output-format` | str | markdown | markdown/json |
| `--selftest` | flag | - | 环境自检 |
| `--version` | flag | - | 版本信息 |

---

## 九、用户协议

**使用本 Skill 即表示您同意以下条款：**

1. **责任承担**：使用者自行承担因使用本 Skill 产生的全部责任。本 Skill 提供的分析结果仅供参考，不构成任何商业决策的唯一依据。
2. **禁止反向工程**：不得对本 Skill 的代码、算法、模型进行反向工程、反编译或试图提取源代码（适用法律允许的除外）。
3. **数据合规**：使用者须确保输入数据符合当地法律法规，不包含个人隐私信息或敏感数据。
4. **无担保**：本 Skill 按"原样"提供，不附带任何明示或暗示的担保。

<!-- user-agreement-injected -->

---

## 十、许可证（License）

### MIT License

```
MIT License

Copyright (c) 2026 原创作者（自持版权）

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

## 附录：CLI 接口速查

```bash
# 环境自检
python run.py --selftest

# 版本信息
python run.py --version

# 基本分析
python run.py --input reviews.csv --brand "示例品牌"

# 竞品对比
python run.py --input my.csv --brand "我" --compare comp1.csv comp2.csv

# JSON 输出
python run.py --input reviews.csv --brand "示例" --output-format json
```

---

*文档结束。本 Skill 由 AI 辅助生成，仅供参考。*
