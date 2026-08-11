---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: competitor-analysis
name: competitor-analysis
displayName: 竞品透视 多维对标 差异定位
description: 输入竞品资料，输出功能、定价、评价多维对比与差异化建议报告
version: 2.0.1
rules_version: cpr-20260811-n351
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/competitor-analysis
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: LinAnalytics
agent_created: true
trigger_words: ["competitor-analysis", "竞品分析", "竞品对比", "市场对标", "差异化分析", "竞品调研", "产品对标", "竞争格局"]
---

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->


> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# 竞品透视 · 多维对标 · 差异定位（SKILL.md）

## 一、能力边界：一页纸速查卡

### 1.1 本 Skill 能做什么

| 能力项 | 说明 | 输出物 |
|--------|------|--------|
| 功能对比 | 提取并排列各竞品的功能清单，按模块归类 | 功能矩阵表（Markdown 表格） |
| 定价分析 | 解析价格策略（免费/订阅/买断/混合），计算单位成本 | 定价模式对照表 + 性价比简评 |
| 评价洞察 | 汇总用户评价中的高频正/负面关键词，标注来源 | 评价情感分布 + 典型引述（脱敏） |
| 差异定位 | 基于上述三维度，输出本品的差异化机会点 | 差异化建议清单（按优先级排序） |

### 1.2 本 Skill 不能做什么

- **不能** 自动抓取网络数据——所有输入必须由使用者提供（文本、表格、文件路径均可）。
- **不能** 保证数据真实性——输入资料若本身有误，输出报告会原样继承该误差。
- **不能** 替代专业咨询——涉及投资、并购、法务等重大决策时，请咨询持证顾问。
- **不能** 生成绝对化结论——所有建议均以"可能性/倾向性"措辞呈现，不承诺任何商业结果。

### 1.3 适用对象

- 产品经理 / 市场分析师 / 创业者 / 运营人员
- 需要快速梳理竞品格局、寻找切入点的场景
- 已有 2 家及以上竞品的资料，但尚未系统化整理

---

## 二、触发方式：场景映射表

| 大白话场景 | 触发指令示例 | 本 Skill 响应 |
|------------|--------------|---------------|
| "帮我看看这几家竞品谁更强" | `competitor-analysis 竞品资料.md` | 输出功能/定价/评价三维对比表 |
| "我们的产品跟友商比差在哪" | `竞品对比 我们产品说明.md 友商A.md 友商B.md` | 输出差异点清单 + 建议 |
| "想了解市场上有哪些替代方案" | `市场对标 行业报告.pdf` | 提取竞品列表并逐一建档 |
| "这个功能别人怎么定价的" | `竞品分析 --pricing-only 定价数据.csv` | 仅输出定价维度分析 |
| "用户吐槽最多的是什么" | `差异化分析 --review-focus 评价截图/` | 仅输出评价洞察部分 |

> 提示：支持 `--selftest` 自检模式（验证环境配置）与 `--version` 版本查询。

---

## 三、标准流程：从输入到报告

### 3.1 前置条件

| 条件 | 要求 | 不满足时的处理 |
|------|------|----------------|
| 竞品数量 | ≥ 2 家 | 提示"资料不足"，输出部分分析 + [需核实:补充竞品] |
| 资料格式 | .md / .txt / .csv / .pdf / 直接粘贴文本 | 自动识别，无法解析时要求转纯文本 |
| 信息完整度 | 每家至少包含 功能/定价/评价 中的 2 项 | 缺失项标注 [需核实:字段名] |

### 3.2 执行步骤（分步编号）

**Step 1 — 资料接收与清洗**
- 读取所有输入文件，去除重复段落、空行、无关广告信息。
- 敏感信息过滤：自动检测并移除疑似 API key、密码、身份证号等（正则匹配 + 关键词库）。
- 输出：`cleaned_inputs/` 目录下的清洗后文本（仅当使用者要求保留时）。

**Step 2 — 竞品实体识别**
- 从文本中提取竞品名称、版本号、所属公司。
- 若同一产品出现多个版本，按"主版本"合并，并在备注中列出子版本。
- 输出：竞品清单表（名称 / 版本 / 来源文件）。

**Step 3 — 三维度信息抽取**

| 维度 | 抽取规则 | 示例 |
|------|----------|------|
| 功能 | 提取动词+名词结构（如"支持多人协作"），按模块归类（协作/安全/导出等） | `协作: [实时编辑, 评论@提及]` |
| 定价 | 识别货币符号、金额、周期词（月/年/一次性），归类为免费/订阅/买断/混合 | `订阅: ¥99/月 (专业版)` |
| 评价 | 抓取情感词（好用/卡顿/贵/贴心），统计频次，保留 1-2 条典型引述（脱敏） | `正面(高频): 界面简洁(12次)` |

**Step 4 — 交叉对比与差异计算**
- 功能对比：构建布尔矩阵（有/无/部分支持），计算重合度与独有功能。
- 定价对比：换算为"每月等效成本"（买断按 3 年折旧），标注免费额度。
- 评价对比：按情感倾向排序，找出各竞品的核心优势与短板。

**Step 5 — 差异化建议生成**
- 基于 Step 4 结果，按以下逻辑生成建议：
  - 若本品在某维度明显弱于所有竞品 → 建议"补齐基础功能"或"明确不做"。
  - 若所有竞品均缺失某功能 → 标记为"蓝海机会"。
  - 若本品定价处于中位 → 建议"强调性价比"或"增加高价值附加服务"。
- 每条建议附带置信度（高/中/低），低置信度建议标注 [需核实:数据支撑]。

**Step 6 — 报告输出**
- 生成 `竞品分析报告_YYYYMMDD.md`，结构如下：

```markdown
# 竞品分析报告
## 1. 竞品概览
## 2. 功能对比矩阵
## 3. 定价模式对照
## 4. 用户评价洞察
## 5. 差异化机会清单
## 6. 附录：数据来源与置信度说明
```

### 3.3 输出规范

- 所有表格必须带表头与对齐（`| :--- | :---: | ---: |`）。
- 所有缺失信息用 `[需核实:字段名]` 占位，禁止编造。
- 报告末尾附"置信度总览"：列出每项结论的数据支撑强度（高=多源交叉验证；中=单源但逻辑自洽；低=推测）。

---

## 四、置信度门控：不编造原则

| 场景 | 处理方式 |
|------|----------|
| 某竞品定价信息缺失 | 定价栏写 `[需核实:定价]`，并在建议中注明"该竞品定价未知，建议人工查询" |
| 评价数据仅 1 条 | 标注"样本量过小（n=1），结论仅供参考" |
| 功能描述模糊（如"支持高级功能"） | 归类为"未明确"，不强行推断具体功能 |
| 数据来源冲突（A 说免费，B 说收费） | 并列展示两个来源，标注 `[需核实:冲突]`，不自行裁决 |

---

## 五、错误码体系

| 错误码 | 触发条件 | 提示话术 | 修正步骤 |
|--------|----------|----------|----------|
| `ERR_INSUFFICIENT_DATA` | 竞品 < 2 家 | "至少需要 2 家竞品资料才能进行对比分析" | 补充竞品资料后重试 |
| `ERR_UNPARSEABLE_FILE` | 文件格式无法识别 | "无法解析该文件，请转为 .txt 或 .md 格式" | 转换格式后重新输入 |
| `ERR_SENSITIVE_DATA` | 检测到疑似密钥/密码 | "检测到敏感信息，已自动过滤。请确认是否继续" | 确认后继续，或移除敏感文件 |
| `ERR_EMPTY_INPUT` | 输入内容为空 | "未读取到有效内容，请检查文件路径或粘贴内容" | 重新提供资料 |
| `ERR_CONFLICT_DATA` | 同一字段多源冲突 | "发现冲突数据，已并列展示，请人工核实" | 核实后指定正确值 |

---

## 六、FAQ 反模式：常见坑与对照

| 常见坑（反模式） | 正确做法（本 Skill 推荐） |
|------------------|---------------------------|
| ❌ 只对比价格，忽略功能差异 | ✅ 三维度同时对比，价格仅作为其中一个维度 |
| ❌ 把用户评价当事实 | ✅ 评价标注来源与样本量，区分"事实"与"观点" |
| ❌ 竞品数量不足仍强行分析 | ✅ 触发 `ERR_INSUFFICIENT_DATA`，输出部分结论并提示补充 |
| ❌ 用绝对化语言（"最好""无敌"） | ✅ 使用"相对优势""目前来看"等限定措辞 |
| ❌ 忽略数据时效性 | ✅ 报告头部标注"数据截至 [输入资料日期]"，过期数据提示更新 |

---

## 七、渐进式披露：分层次阅读路径

### 7.1 速查卡（30 秒上手）

```
1. 准备 ≥2 家竞品资料（文本/文件均可）
2. 输入：competitor-analysis 你的资料
3. 获取：功能矩阵 + 定价对照 + 评价洞察 + 差异建议
4. 缺失信息自动标注 [需核实:xxx]，不编造
```

### 7.2 新手路径（首次使用）

- 阅读「一、能力边界」→ 明确能做什么不能做什么。
- 按「三、标准流程」Step 1-3 准备资料。
- 运行后重点看「5. 差异化机会清单」的前 3 条建议。

### 7.3 进阶路径（深度使用）

- 结合「四、置信度门控」理解每项结论的证据强度。
- 使用 `--pricing-only` / `--review-focus` 等参数进行单维度深挖。
- 将多期报告对比，观察竞品动态变化（需自行保存历史报告）。

---

## 八、用户协议

<!-- user-agreement-injected -->

**使用本 Skill 即视为同意以下条款：**

1. 本 Skill 仅供学习与参考用途。使用本 Skill 产生的任何结果，由使用者自行承担全部责任；本 Skill 不提供任何明示或暗示的保证。
2. 涉及法律、财务、税务、投资、医疗等专业决策时，请务必咨询持证专业人士。
3. 本代码受版权法保护，未经授权复制、反向工程或商业利用将被追究法律责任。
4. 使用者不得将本 Skill 用于任何违反适用法律法规的活动。

---

## 九、许可证（License）

<!-- professional-license-embedded -->

**MIT License**

Copyright (c) 2026 LinAnalytics

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

*文档版本：1.0.0 | 最后更新：2026-08-11 | 生成方式：AI 辅助*
