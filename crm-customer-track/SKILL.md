---
slug: crm-customer-track
name: crm-customer-track
description: 客户跟进轨迹分析与商机停滞预警工具
version: 1.1.0
license: MIT
ai_generated: true
disclaimer: true
source_project: skill-factory-originals
copyright_holder: bluebigman

---

> 📜 **用户协议（User Agreement）**
> 1. 本 Skill 仅供学习与参考用途。使用本 Skill 产生的任何结果，由使用者自行承担全部责任；本 Skill 不提供任何明示或暗示的保证。
> 2. 涉及法律、财务、税务、投资、医疗等专业决策时，请务必咨询持证专业人士。
> 3. 本代码受版权法保护，未经授权复制、反向工程或商业利用将被追究法律责任。
<!-- user-agreement-injected -->


> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->

# 客户跟进轨迹管理（crm-customer-track）

## 能力边界

### 能做什么

| 能力项 | 说明 | 输出物 |
|--------|------|--------|
| 轨迹归档 | 读取 CSV/XLSX 格式的客户跟进记录，按客户 ID 归并时间线，计算跟进频次、最近跟进时间、平均跟进间隔 | 结构化 JSON/CSV 报告 |
| 停滞识别 | 基于可配置的沉默阈值（默认 14 天），标记超过阈值未跟进的商机 | 停滞预警清单（含停滞天数） |
| 流失评分 | 基于互动频次、情绪倾向（正向/负向关键词）、竞品提及三个维度计算流失风险评分（0-100） | 风险等级（低/中/高） |
| 决策辅助 | 根据风险等级和停滞天数，为每个商机生成行动建议（关怀/调整策略/移交） | 行动建议列表 |

### 不能做什么

- 不能自动连接 CRM 系统或数据库，需人工导出数据文件。
- 不能预测未来成交概率，仅基于历史数据做趋势判断。
- 不能替代销售人员的判断，所有预警需人工复核。
- 不能处理非结构化文本（如语音转写稿需先整理为文本记录）。
- 不包含情绪分析模型，仅基于关键词词典做简单匹配。

### 适用对象

- 销售运营人员：批量梳理客户跟进状态。
- 客户成功经理：识别沉默客户并制定挽回策略。
- 销售团队负责人：掌握商机健康度分布。

## 触发条件

- 用户提供客户跟进记录文件（CSV/XLSX），包含字段：客户ID、客户名称、跟进日期、跟进方式、跟进内容摘要。
- 用户要求分析客户跟进轨迹、识别停滞商机、评估流失风险。
- 用户指定沉默阈值（可选，默认 14 天）。

## 标准流程

1. **输入校验**：检查文件存在性、格式、必填字段完整性。
2. **数据加载**：读取 CSV（UTF-8 编码）或 XLSX 文件。
3. **数据清洗**：解析日期为 ISO 格式，跳过无效记录并计数。
4. **轨迹归并**：按客户 ID 分组，按日期排序，计算跟进频次、最近跟进日期、平均间隔。
5. **停滞识别**：计算距今天数，超过阈值标记为停滞。
6. **流失评分**：对每条记录进行关键词匹配，计算客户级情绪得分；结合频次、情绪、竞品提及计算风险评分。
7. **报告生成**：输出 JSON 或 CSV 格式报告，包含客户列表、停滞预警、风险等级、行动建议。
8. **结果展示**：打印摘要统计（客户总数、停滞数、风险分布）。

## 置信度门控

- 若输入文件缺少必填字段，抛出 `ValueError` 并提示缺失字段。
- 若日期格式无法解析，该记录被跳过并计入 `invalid_records`，报告中显示警告。
- 若文件编码错误，抛出 `ValueError` 提示使用 UTF-8。
- 若 XLSX 依赖未安装，抛出 `ImportError` 提示安装 openpyxl。
- 所有预警结果基于规则引擎，置信度标注为"规则匹配"，需人工复核。

## 错误码

| 错误码 | 含义 | 处理方式 |
|--------|------|----------|
| `E001` | 文件不存在 | 检查路径，提示用户 |
| `E002` | 缺少必填字段 | 列出缺失字段，提示补充 |
| `E003` | 日期解析失败 | 跳过记录，计入警告 |
| `E004` | 编码错误 | 提示使用 UTF-8 编码 |
| `E005` | 依赖缺失 | 提示安装 openpyxl |

## FAQ / 反模式

**Q: 为什么我的 XLSX 文件无法读取？**
A: 需要安装 openpyxl：`pip install openpyxl`。

**Q: 日期格式支持哪些？**
A: 支持 ISO 格式（YYYY-MM-DD）和常见格式（YYYY/MM/DD、YYYY.MM.DD）。其他格式可能解析失败。

**Q: 风险评分是真实的吗？**
A: 评分基于规则引擎（关键词匹配 + 频次计算），非机器学习模型。结果仅供参考。

**反模式：**
- ❌ 不要用本工具做最终成交预测。
- ❌ 不要忽略 `invalid_records` 警告，可能影响分析完整性。
- ❌ 不要修改阈值后不重新验证结果。


## 许可证（License）

```text
MIT License

Copyright (c) {year} {holder}

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

## 前置条件

- 本技能开箱即用，无需额外安装依赖。
- 需要 Python 3.9+ 运行环境。
- 涉及网络请求时需保持网络连通。