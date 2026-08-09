---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: booking-scraper
name: booking-scraper
displayName: 酒店预订 数据采集 信息抽取
description: 将酒店预订页面或数据转为结构化表格，支持批量与自定义字段。
version: 1.0.1
rules_version: cpr-20260809-n251
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/booking-scraper
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: LinDataWorks
agent_created: true
trigger_words: ["booking-scraper", "酒店数据采集", "预订信息抽取", "booking抓取", "房源数据整理"]

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

---

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->


# booking-scraper 技能文档

## 一、能力边界速查卡

本技能用于将用户提供的酒店预订相关数据（链接、文件、粘贴文本）转换为结构化的表格数据。它不直接访问网络，而是处理用户已经获取的内容。

| 维度 | 说明 |
|------|------|
| **核心用途** | 从 Booking.com 风格的酒店信息文本中提取字段，整理为统一格式 |
| **输入类型** | ① 网页链接（用户需自行粘贴页面文本）② CSV/Excel 文件路径 ③ 直接粘贴的文本块 |
| **输出格式** | Markdown 表格 / CSV 字符串 / JSON 数组（由用户指定） |
| **处理规模** | 单次建议 1-50 条记录；超过 50 条需分批处理 |
| **关键字段** | 酒店名称、地址、评分、价格范围、房型、入住日期、退房日期、设施列表 |

### 不能做的事

- 不执行网络请求，不自动抓取网页内容
- 不处理验证码、登录墙、反爬机制
- 不保存数据到本地文件（仅输出文本结果）
- 不进行价格预测或趋势分析
- 不翻译非中文内容（保留原文）

### 适用对象

- 需要整理酒店比价数据的旅行规划者
- 做市场调研的酒店行业分析人员
- 需要批量整理预订确认邮件的行政人员

---

## 二、触发方式与场景映射

当用户输入包含以下意图时，本技能自动激活：

| 触发词/场景 | 用户可能说的话 | 技能响应 |
|-------------|---------------|----------|
| booking-scraper | "用 booking-scraper 处理这个文件" | 启动数据解析流程 |
| 酒店数据采集 | "帮我采集这些酒店的信息" | 识别输入中的酒店条目 |
| 预订信息抽取 | "把预订邮件里的信息提取出来" | 解析邮件文本为字段 |
| 房源数据整理 | "整理一下这些房源数据" | 标准化字段并输出表格 |
| 批量处理 | "这里有 20 家酒店，一起处理" | 启用批量模式 |

---

## 三、标准处理流程

### 前置条件

1. 用户已获取原始数据（页面文本、文件或粘贴内容）
2. 数据中至少包含酒店名称或 URL 之一
3. 明确输出格式（默认 Markdown 表格）

### 执行步骤

**步骤 1：输入确认**

接收用户输入，判断类型：

| 输入类型 | 识别方式 | 处理方式 |
|----------|----------|----------|
| 文本块 | 包含"酒店"、"Room"、"评分"等关键词 | 直接解析 |
| 文件路径 | 以 .csv/.xlsx/.txt 结尾 | 读取文件内容 |
| URL | 以 http 开头 | 提示用户粘贴页面文本 |

**步骤 2：字段提取**

按优先级提取以下字段：

```
必提字段：酒店名称、评分、价格
优先字段：地址、房型、入住/退房日期
可选字段：设施、联系电话、图片链接
```

提取规则：
- 酒店名称：取第一个独立行或加粗文本
- 评分：匹配 `\d\.\d` 模式，保留一位小数
- 价格：匹配货币符号后数字，统一转为人民币（CNY）估算值
- 日期：匹配 `YYYY-MM-DD` 或 `Month DD, YYYY` 格式

**步骤 3：置信度标注**

每个字段附带置信度标记：

| 标记 | 含义 | 使用条件 |
|------|------|----------|
| 高 | 字段值完整且格式正确 | 直接匹配到明确模式 |
| 中 | 字段值存在但可能有误差 | 需要推断或格式不标准 |
| 低 | 字段值缺失或模糊 | 仅能部分识别 |
| [需核实:字段名] | 无法确定，需用户确认 | 信息冲突或缺失 |

**步骤 4：输出生成**

按用户指定格式输出结果。默认格式示例：

```markdown
| 酒店名称 | 地址 | 评分 | 价格(CNY) | 房型 | 入住日期 | 退房日期 | 置信度 |
|----------|------|------|-----------|------|----------|----------|--------|
| 城市花园酒店 | 上海市静安区南京西路 | 8.7 | 680 | 豪华大床房 | 2026-09-01 | 2026-09-03 | 高 |
```

**步骤 5：自查校验**

- 检查必填字段是否完整
- 验证日期格式统一
- 确认价格数值合理（范围 50-50000 CNY）
- 标注所有低置信度字段

---

## 四、置信度门控机制

当遇到以下情况时，技能输出 `[需核实:字段名]` 占位符，**绝不编造数据**：

| 场景 | 处理方式 |
|------|----------|
| 价格缺失 | 输出 `[需核实:价格]`，不估算 |
| 评分格式异常 | 输出 `[需核实:评分]`，保留原始文本 |
| 日期无法解析 | 输出 `[需核实:日期]` |
| 酒店名称重复 | 保留全部条目，标注"疑似重复" |
| 地址不完整 | 输出已识别部分 + `[需核实:地址]` |

---

## 五、错误码体系

| 错误码 | 错误描述 | 提示话术 | 修正步骤 |
|--------|----------|----------|----------|
| ERR-001 | 输入为空 | "未检测到有效输入，请提供文本、文件路径或URL" | 重新输入数据 |
| ERR-002 | 格式无法识别 | "输入内容不符合酒店信息格式，请检查是否包含酒店名称" | 确认数据来源为预订平台 |
| ERR-003 | 文件读取失败 | "无法读取文件，请确认路径正确且文件未损坏" | 检查文件扩展名和权限 |
| ERR-004 | 字段提取失败 | "关键字段（酒店名称）缺失，无法处理" | 补充至少一个酒店名称 |
| ERR-005 | 批量超限 | "单次处理超过50条，请分批提交" | 将数据拆分为多个批次 |
| ERR-006 | 输出格式不支持 | "仅支持 markdown/csv/json 三种格式" | 重新指定输出格式 |

---

## 六、常见坑与反模式对照

| 常见错误 | 反模式（错误做法） | 正模式（正确做法） |
|----------|--------------------|--------------------|
| 忽略置信度 | 直接填充猜测值 | 使用 `[需核实:字段]` 标记 |
| 过度解析 | 尝试提取所有可能字段 | 只提取用户需要的核心字段 |
| 格式混乱 | 混合多种日期格式输出 | 统一为 YYYY-MM-DD |
| 数据污染 | 将广告或推荐内容当作酒店信息 | 仅提取明确包含"评分"或"价格"的条目 |
| 重复处理 | 对同一输入多次解析 | 每次输入只处理一次，输出结果后确认 |

---

## 七、渐进式披露路径

### 速查卡（30秒上手）

1. 粘贴酒店信息文本
2. 说"整理成表格"
3. 获取结构化 Markdown 表格

### 新手路径（5分钟掌握）

1. 阅读能力边界速查卡
2. 尝试处理 3-5 条酒店数据
3. 观察置信度标注，理解 `[需核实]` 含义
4. 使用 CSV 输出格式保存结果

### 进阶路径（深度使用）

1. 批量处理 50 条数据，分批提交
2. 自定义字段提取规则（如只提取含"泳池"的酒店）
3. 结合其他工具进行价格对比分析
4. 使用 JSON 输出对接自动化流程

---

## 八、参数配置表

| 参数名 | 类型 | 默认值 | 可选值 | 说明 |
|--------|------|--------|--------|------|
| output_format | string | markdown | markdown/csv/json | 输出格式 |
| currency | string | CNY | CNY/USD/EUR | 价格转换货币 |
| max_records | int | 50 | 1-100 | 单次最大处理条数 |
| include_facilities | bool | false | true/false | 是否提取设施列表 |
| date_format | string | YYYY-MM-DD | 自定义 | 日期输出格式 |

---

## 九、示例演示

### 示例输入

```
酒店名称：滨海假日酒店
地址：三亚市海棠区海棠北路
评分：9.2
价格：每晚 1200 元
房型：海景大床房
入住：2026-10-01 退房：2026-10-05
设施：游泳池、健身房、免费WiFi
```

### 示例输出

```json
{
  "hotel_name": "滨海假日酒店",
  "address": "三亚市海棠区海棠北路",
  "rating": 9.2,
  "price_per_night": 1200,
  "room_type": "海景大床房",
  "check_in": "2026-10-01",
  "check_out": "2026-10-05",
  "facilities": ["游泳池", "健身房", "免费WiFi"],
  "confidence": {
    "hotel_name": "高",
    "address": "高",
    "rating": "高",
    "price": "高",
    "room_type": "高",
    "dates": "高",
    "facilities": "高"
  }
}
```

---

## 十、用户协议

使用本技能即表示您同意以下条款：

1. **责任承担**：使用者自行承担因使用本技能产生的全部责任，包括但不限于数据准确性、合规性及法律风险。
2. **禁止反向工程**：不得对本技能的逻辑、代码结构进行逆向分析、破解或二次分发。
3. **数据合规**：使用者需确保输入数据来源合法，不侵犯第三方权益。
4. **无担保声明**：本技能按"现状"提供，不提供任何明示或暗示的担保。

<!-- user-agreement-injected -->

---

## 十一、许可证（License）

本技能基于 MIT 许可证开源发布：

```
MIT License

Copyright (c) 2026 LinDataWorks

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
