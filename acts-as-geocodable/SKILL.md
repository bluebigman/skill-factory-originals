---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: acts-as-geocodable
name: acts-as-geocodable
displayName: 地址解析 地理编码 坐标转换
description: 将中文地址文本解析为结构化地理数据，输出坐标与匹配置信度。
version: 1.0.6
rules_version: cpr-20260820-n601
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/acts-as-geocodable
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: GeoParser Studio
agent_created: true
trigger_words: ["acts as geocodable", "地理编码", "地址转坐标", "geocode", "地址解析", "定位", "经纬度查询"]
---

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->


> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# 地址解析与地理编码 Skill 文档

## 一、能力边界（一页纸速查卡）

本 Skill 专注于将非结构化的中文地址文本转换为结构化的地理信息数据。它不是一个通用的地图服务，也不提供路径规划或实时交通信息。

| 能力维度 | 支持情况 | 详细说明 |
|---------|---------|---------|
| 地址解析 | ✅ 支持 | 将"XX省XX市XX区XX路XX号"解析为省、市、区、街道、门牌号等字段 |
| 坐标输出 | ✅ 支持 | 输出 WGS84 坐标系下的经纬度（经度在前，纬度在后） |
| 置信度评估 | ✅ 支持 | 返回 `confidence` 字段，范围 0.0 ~ 1.0，表示匹配可靠程度 |
| 匹配级别标注 | ✅ 支持 | 返回 `match_level` 字段，标识匹配精度（`precise` / `street` / `locality`） |
| 省级以下地址解析 | ❌ 不支持 | 仅输入"北京市"或"广东省"这类省级地址将返回错误 |
| 非中文地址解析 | ❌ 不支持 | 仅支持 UTF-8 编码的中文地址文本 |
| 地址模糊搜索 | ❌ 不支持 | 不提供"猜你想找"式的模糊匹配，仅做确定性解析 |
| 批量解析 | ❌ 不支持 | 单次调用仅处理一条地址文本 |

**适用对象**：需要将用户输入的中文地址转换为坐标以便进行地图展示、距离计算、区域统计的开发者或数据分析师。

**不适用场景**：需要实时路况、驾车导航、POI 兴趣点搜索的场景，请使用专业地图 SDK。

---

## 二、触发方式

当对话中出现以下意图时，本 Skill 被激活：

| 触发词/短语 | 典型用户表述 | 示例 |
|------------|-------------|------|
| `acts as geocodable` | 直接调用 Skill 名称 | "acts as geocodable 解析这个地址" |
| `地理编码` | 使用专业术语 | "帮我做一下地理编码：杭州市西湖区文三路138号" |
| `地址转坐标` | 描述功能需求 | "把'上海市浦东新区世纪大道100号'转成经纬度" |
| `geocode` | 英文触发 | "geocode 北京市朝阳区建国路88号" |
| `地址解析` | 通用表述 | "地址解析一下：广州市天河区体育西路191号" |
| `定位` | 口语化表达 | "定位一下这个地址：成都市武侯区天府大道北段1700号" |
| `经纬度查询` | 明确需求 | "查询这个地址的经纬度：南京市鼓楼区中山北路100号" |

**场景映射表**：

| 用户场景 | 触发语句示例 | Skill 响应行为 |
|---------|-------------|---------------|
| 电商收货地址处理 | "把这个收货地址转成坐标：深圳市南山区科技园南区" | 解析地址，输出坐标和置信度 |
| 数据分析前处理 | "地理编码这批门店地址" | 逐条解析（单次调用处理一条） |
| 地图打点 | "把'北京市海淀区中关村大街27号'变成经纬度" | 输出坐标及匹配级别 |
| 地址规范化 | "帮我解析这个地址的省市区" | 输出结构化字段 |

---

## 三、标准执行流程

### 前置条件

1. 输入地址文本长度 ≥ 4 个字符（少于 4 个字符无法进行有效解析）
2. 输入文本编码为 UTF-8
3. 输入必须包含至少一个省级行政区划名称（如"省""市""自治区"）

### 执行步骤

**步骤 1：输入校验**

- 检查输入是否为空或长度 < 4 字符 → 返回 `INVALID_INPUT` 错误
- 检查输入是否为 UTF-8 编码 → 非 UTF-8 返回 `ENCODING_ERROR` 错误
- 检查输入是否包含省级关键词（省/市/自治区/特别行政区）→ 不包含则返回 `INCOMPLETE_ADDRESS` 错误

**步骤 2：逐级匹配**

按以下顺序进行行政区划匹配：

1. **省级匹配**：在省级词典中查找输入文本中的省级名称
   - 匹配失败 → 返回 `INCOMPLETE_ADDRESS` 错误，提示用户补充省/市信息
2. **市级匹配**：在市级词典中查找输入文本中的市级名称
   - 匹配失败 → 降级处理，返回省级政府所在地坐标，`match_level` 设为 `locality`
3. **区县级匹配**：在区县级词典中查找输入文本中的区县名称
   - 匹配失败 → 降级处理，返回市政府所在地坐标，`match_level` 设为 `locality`
4. **街道/乡镇级匹配**：在街道级词典中查找输入文本中的街道名称
   - 匹配失败 → 降级处理，返回区政府所在地坐标，`match_level` 设为 `street`
5. **详细地址匹配**：尝试匹配门牌号、道路名等详细地址信息
   - 匹配成功 → `match_level` 设为 `precise`

**步骤 3：坐标与置信度计算**

- 根据匹配到的行政区域，从内置词典中提取该区域的中心点坐标
- 置信度计算规则：
  - `precise` 级别：置信度 0.85 ~ 1.0（根据门牌号完整度微调）
  - `street` 级别：置信度 0.70 ~ 0.84
  - `locality` 级别：置信度 0.50 ~ 0.69

**步骤 4：输出结构化结果**

输出格式为 JSON，包含以下字段：

```json
{
  "input": "原始输入地址",
  "status": "success",
  "match_level": "precise | street | locality",
  "confidence": 0.0,
  "coordinates": {
    "longitude": 0.0,
    "latitude": 0.0
  },
  "structured_address": {
    "province": "省/自治区/直辖市名称",
    "city": "市/地区/自治州名称",
    "district": "区/县/县级市名称",
    "street": "街道/镇/乡名称",
    "detail": "门牌号/道路名等详细地址"
  }
}
```

### 输出规范

- 坐标使用 WGS84 坐标系，经度范围 -180 ~ 180，纬度范围 -90 ~ 90
- 所有字段均为字符串类型（坐标除外），缺失字段返回空字符串 `""`
- 输出必须包含 `status` 字段，成功为 `success`，失败为对应错误码

---

## 四、置信度门控机制

本 Skill 遵循"宁缺毋滥"原则，在信息不足时不会编造数据。

| 场景 | 处理方式 | 输出示例 |
|------|---------|---------|
| 地址缺少门牌号 | 返回街道级坐标，置信度降低，`match_level` 为 `street` | `"confidence": 0.75` |
| 地址缺少区县信息 | 返回市级坐标，置信度降低，`match_level` 为 `locality` | `"confidence": 0.60` |
| 地址缺少市级信息 | 返回省级坐标，置信度降低，`match_level` 为 `locality` | `"confidence": 0.50` |
| 地址包含无法识别的部分 | 在 `structured_address` 对应字段中输出 `[需核实:原始文本片段]` 占位符 | `"detail": "[需核实:XX路XX号]"` |
| 地址包含矛盾信息（如省与市不匹配） | 返回 `ADDRESS_CONFLICT` 错误，不进行猜测性解析 | 见错误码表 |

**重要原则**：当解析过程中遇到无法确认的信息时，使用 `[需核实:字段]` 占位符明确标注，绝不虚构坐标或行政区划名称。

---

## 五、错误码体系

| 错误码 | 含义 | 用户提示话术 | 修正步骤 |
|--------|------|-------------|---------|
| `INVALID_INPUT` | 输入为空或长度不足 4 字符 | "地址文本过短，请提供至少 4 个字符的完整地址" | 请用户补充更详细的地址信息 |
| `ENCODING_ERROR` | 输入不是 UTF-8 编码 | "输入编码格式不支持，请转换为 UTF-8 编码后重试" | 转换编码后重新提交 |
| `INCOMPLETE_ADDRESS` | 省级匹配失败，缺少省/市信息 | "无法识别省级行政区划，请补充省/市信息（如'浙江省'或'杭州市'）" | 在地址前添加省或市级名称 |
| `ADDRESS_CONFLICT` | 地址中包含相互矛盾的行政区划信息 | "地址中的省/市/区信息存在矛盾，请核对后重新输入" | 检查并修正地址中的行政区划名称 |
| `MATCH_NOT_FOUND` | 地址中的行政区划名称不在内置词典中 | "未能匹配到已知的行政区划，请确认地址名称是否正确" | 核对地址名称，或使用更常见的行政区划名称 |
| `INTERNAL_ERROR` | 解析过程中发生内部错误 | "解析过程中出现异常，请稍后重试" | 重新提交请求，若持续失败请检查输入格式 |

---

## 六、FAQ 与反模式对照

### 常见坑 1：输入过短的地址

**错误示例**："北京"（仅 2 字符）

**问题**：无法确定是北京市还是其他含"北京"字样的地名，且长度不足 4 字符。

**正确做法**：输入"北京市"或"北京市朝阳区"等至少包含省级信息的地址。

### 常见坑 2：省略省级名称

**错误示例**："杭州市西湖区文三路138号"

**问题**：虽然"杭州市"可被识别为市级名称，但缺少省级信息，解析器需要额外推断"浙江省"。

**正确做法**：输入"浙江省杭州市西湖区文三路138号"，确保省级信息明确。

### 常见坑 3：使用非标准地名

**错误示例**："魔都静安区南京西路"

**问题**："魔都"是上海的别称，不在标准行政区划词典中。

**正确做法**：使用官方行政区划名称"上海市静安区南京西路"。

### 常见坑 4：期望模糊搜索功能

**错误示例**："帮我找一下'北京三里屯'的坐标"

**问题**：本 Skill 仅做确定性解析，不做 POI 模糊搜索。"三里屯"是片区名称而非标准行政区划。

**正确做法**：输入标准行政区划地址，如"北京市朝阳区三里屯街道"。

### 常见坑 5：忽略置信度直接使用坐标

**错误示例**：将 `match_level: "locality"` 的坐标直接用于精确导航

**问题**：`locality` 级别的坐标是市级中心点，与实际地址可能相差数公里。

**正确做法**：根据 `match_level` 判断坐标精度，`locality` 级别仅适用于区域统计等粗粒度场景。

---

## 七、渐进式披露指南

### 速查卡（30 秒上手）

```
输入：中文地址文本（≥4字符，UTF-8）
输出：JSON（含坐标、置信度、匹配级别）
错误：INCOMPLETE_ADDRESS / INVALID_INPUT 等
原则：信息不足时输出 [需核实:字段]，不编造
```

### 新手路径（首次使用）

1. 阅读"能力边界"了解适用范围
2. 查看"触发方式"了解如何激活 Skill
3. 使用"标准执行流程"中的步骤进行首次调用
4. 遇到问题查阅"错误码体系"

### 进阶路径（深度使用）

1. 理解"置信度门控机制"，学会解读 `confidence` 和 `match_level` 字段
2. 掌握降级匹配规则，预判不同输入可能产生的输出精度
3. 阅读"FAQ 与反模式对照"，避免常见使用错误
4. 根据 `match_level` 设计业务逻辑，如：`precise` 级别用于精确打点，`locality` 级别用于区域统计

---

## 八、技术参数参考

### 坐标精度说明

| 匹配级别 | 坐标含义 | 典型误差范围 | 适用场景 |
|---------|---------|------------|---------|
| `precise` | 门牌号级定位 | ±50 米以内 | 精确导航、配送定位 |
| `street` | 街道级中心点 | ±500 米以内 | 区域展示、统计聚合 |
| `locality` | 区/市级中心点 | ±5 公里以内 | 省级/市级宏观分析 |

### 置信度取值参考

| 匹配情况 | 置信度范围 | 说明 |
|---------|-----------|------|
| 完整匹配（省市区街道门牌号齐全） | 0.90 ~ 1.00 | 信息完整，可信度高 |
| 缺少门牌号 | 0.80 ~ 0.89 | 街道级定位，精度可接受 |
| 缺少区县信息 | 0.65 ~ 0.79 | 市级定位，精度有限 |
| 仅省级信息 | 0.50 ~ 0.64 | 省级定位，仅适合宏观分析 |

---

## 九、用户协议

<!-- user-agreement-injected -->

**使用本 Skill 即表示您同意以下条款：**

1. **责任承担**：使用者自行承担因使用本 Skill 产生的全部责任。本 Skill 提供的解析结果仅供参考，不构成任何形式的专业建议或保证。

2. **禁止反向工程**：不得对本 Skill 的底层算法、数据结构、内置词典进行反向工程、反编译、破解或提取核心逻辑。

3. **数据使用**：本 Skill 输出的坐标数据基于公开行政区划信息，使用者应自行核实数据的准确性与时效性。

4. **合规使用**：使用者应确保使用本 Skill 的行为符合当地法律法规，不得将本 Skill 用于任何非法用途。

5. **免责声明**：本 Skill 按"现状"提供，不附带任何明示或暗示的担保，包括但不限于适销性、特定用途适用性和非侵权保证。

---

## 十、许可证（License）

<!-- professional-license-embedded -->

### MIT License

Copyright (c) 2026 GeoParser Studio

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

*本 Skill 由 AI 辅助生成，仅供参考。使用前请阅读相关文档并核实输出结果的准确性。*
