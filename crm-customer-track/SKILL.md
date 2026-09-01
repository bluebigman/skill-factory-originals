---
slug: crm-customer-track
name: crm-customer-track
displayName: 客户轨迹 商机预警 跟进决策
description: 记录客户互动全轨迹，识别停滞与流失风险，辅助跟进决策。
version: 1.0.0
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/crm-customer-track
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: FlowForge Studio
agent_created: true
trigger_words: ["客户跟进", "客户轨迹", "商机预警", "跟进记录", "客户状态", "互动历史", "流失分析", "跟进提醒"]
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# 客户轨迹与商机预警 Skill 文档

## 一、能力边界（一页纸速查卡）

### 1.1 能做什么

| 编号 | 能力项 | 说明 | 输入要求 |
|------|--------|------|----------|
| C1 | 客户互动轨迹记录 | 按时间线汇总客户所有触点（电话、邮件、会议、微信等） | 至少提供客户ID或名称 + 1条互动记录 |
| C2 | 停滞风险识别 | 检测超过设定阈值（默认14天）无有效互动的客户 | 客户列表 + 最近互动日期 |
| C3 | 流失风险预警 | 结合互动频率下降趋势、负面反馈标记、竞品接触信号综合判断 | 连续3个周期的互动数据 |
| C4 | 跟进决策建议 | 基于风险等级输出下一步动作建议（触达方式、优先级、话术要点） | 风险识别结果 + 客户阶段信息 |
| C5 | 跟进记录查询 | 按客户、时间范围、互动类型筛选历史记录 | 至少一个筛选条件 |

### 1.2 不能做什么

| 编号 | 限制项 | 说明 |
|------|--------|------|
| L1 | 不替代CRM系统 | 本Skill是分析辅助工具，不负责数据存储与权限管理 |
| L2 | 不预测绝对结果 | 风险判断基于规则模型，不承诺客户必然流失或必然挽回 |
| L3 | 不处理非结构化附件 | 仅处理文本形式的互动记录，不解析PDF/图片内容 |
| L4 | 不自动发送消息 | 只输出建议文案，不直接调用邮件/IM发送接口 |
| L5 | 不跨客户关联分析 | 单次调用仅处理指定客户或客户群，不做全局关系图谱 |

### 1.3 适用对象

- 销售代表：日常跟进提醒与记录整理
- 客户成功经理：健康度监控与干预策略
- 销售主管：团队客户风险总览与资源调配
- 运营人员：客户分层与生命周期分析

---

## 二、触发方式

### 2.1 触发词映射表

| 用户说（大白话） | 触发词匹配 | 实际执行动作 |
|------------------|------------|--------------|
| "帮我看看老王那边最近啥情况" | 客户跟进 / 客户轨迹 | 输出该客户的互动时间线 + 当前状态 |
| "这个月哪些客户没动静了？" | 商机预警 / 客户状态 | 扫描停滞客户列表，输出风险分级 |
| "把上周跟李总聊的内容记下来" | 跟进记录 | 新增一条互动记录并更新轨迹 |
| "张总是不是要跑了？" | 流失分析 / 商机预警 | 输出流失风险评估报告 |
| "明天该联系谁？" | 跟进提醒 / 客户跟进 | 按优先级输出今日待跟进清单 |

### 2.2 命令行接口

```bash
# 记录客户互动
客户跟进 --customer "客户A" --type "电话" --content "讨论了Q3续约方案" --date "2025-01-15"

# 查询客户轨迹
客户轨迹 --customer "客户A" --from "2025-01-01" --to "2025-01-31"

# 商机预警（全量扫描）
商机预警 --threshold-days 14 --risk-level high

# 查看特定客户状态
客户状态 --customer "客户A"

# 自检
--selftest

# 版本
--version
```

---

## 三、标准流程

### 3.1 前置条件

| 条件 | 要求 | 缺失处理 |
|------|------|----------|
| 客户标识 | 至少提供客户ID或唯一名称 | 报错 E1001，提示补充 |
| 互动数据 | 文本格式，含日期与类型 | 报错 E1002，提示格式要求 |
| 时间参数 | 日期格式 YYYY-MM-DD | 自动纠正为当日，提示警告 W2001 |

### 3.2 执行步骤

**流程A：记录客户互动**

1. 解析输入参数，提取客户标识、互动类型、内容、日期
2. 校验客户是否存在（若不存在，创建新客户档案）
3. 校验互动类型是否在枚举范围内（电话/邮件/会议/微信/其他）
4. 将互动记录追加至该客户的时间线
5. 更新客户状态字段（最近互动日期、互动计数）
6. 输出确认信息，包含记录ID与更新后的摘要

**流程B：识别停滞与流失风险**

1. 获取目标客户列表（全量或指定范围）
2. 计算每个客户最近互动日期与当前日期的间隔天数
3. 按阈值分级：
   - 健康：间隔 ≤ 7天
   - 关注：7天 < 间隔 ≤ 14天
   - 停滞：14天 < 间隔 ≤ 30天
   - 高危：间隔 > 30天
4. 对停滞及以上客户，追加分析互动频率趋势（近3个周期对比）
5. 结合负面信号（投诉记录、退款申请、竞品提及）加权修正风险等级
6. 输出风险矩阵表，按优先级排序

**流程C：生成跟进建议**

1. 读取风险等级与客户阶段（潜在/试用/签约/续约/流失）
2. 匹配建议模板：
   - 高危 + 续约期 → 建议48小时内高层介入，提供专属方案
   - 停滞 + 试用期 → 建议发送使用指南 + 邀请参加培训
   - 关注 + 潜在期 → 建议推送行业洞察内容，保持存在感
3. 生成话术要点（3-5条，基于历史互动内容提炼）
4. 输出完整建议卡片

### 3.3 输出规范

所有输出采用以下结构化格式：

```json
{
  "status": "success",
  "data": {
    "customer_id": "CUST-001",
    "customer_name": "示例客户",
    "risk_level": "high",
    "risk_score": 82,
    "last_interaction": "2025-01-02",
    "days_since_last": 18,
    "interaction_count_30d": 2,
    "trend": "declining",
    "suggestions": [
      {"priority": 1, "action": "电话触达", "timeline": "24小时内", "script": "..."}
    ]
  },
  "meta": {
    "processed_at": "2025-01-20T10:30:00Z",
    "version": "1.0.0"
  }
}
```

---

## 四、置信度门控

### 4.1 信息不足处理

当输入数据不足以支撑判断时，**严禁编造**。使用以下占位符：

| 场景 | 占位符 | 示例输出 |
|------|--------|----------|
| 客户最近互动日期未知 | [需核实:最近互动日期] | "该客户风险等级暂无法判定，[需核实:最近互动日期]" |
| 互动类型不明确 | [需核实:互动类型] | "记录已保存，但[需核实:互动类型]将影响后续分析" |
| 客户阶段信息缺失 | [需核实:客户阶段] | "建议生成中，[需核实:客户阶段]以匹配更精准话术" |
| 负面信号未确认 | [需核实:负面信号] | "检测到互动频率下降，但[需核实:负面信号]以确认原因" |

### 4.2 置信度分级

| 置信度 | 条件 | 输出标注 |
|--------|------|----------|
| 高（≥90%） | 数据完整，趋势明确 | 正常输出，无标注 |
| 中（70-89%） | 部分数据缺失但可推断 | 标注"基于现有数据推断" |
| 低（<70%） | 关键字段缺失 | 标注"仅供参考，建议核实" + 占位符 |

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| E1001 | 缺少客户标识 | "请提供客户ID或客户名称" | 补充 --customer 参数或交互输入 |
| E1002 | 互动数据格式错误 | "互动记录需包含日期和内容" | 按"日期|类型|内容"格式重新输入 |
| E1003 | 日期格式不合法 | "日期需为 YYYY-MM-DD 格式" | 转换日期格式后重试 |
| E1004 | 客户不存在 | "未找到该客户，是否创建新档案？" | 确认创建或检查客户ID拼写 |
| E2001 | 时间范围倒置 | "起始日期晚于结束日期" | 交换 from/to 参数 |
| E2002 | 阈值参数越界 | "停滞阈值需在 1-90 天之间" | 调整阈值后重试 |
| E3001 | 数据源连接失败 | "无法读取客户数据，请检查数据源配置" | 检查数据源连接或稍后重试 |
| E9001 | 内部错误 | "处理过程中发生异常，请重试或联系支持" | 重试，若持续报错则记录日志 |

---

## 六、FAQ 反模式对照

### 6.1 常见坑与正确做法

| 坑（反模式） | 问题说明 | 正确做法 |
|--------------|----------|----------|
| ❌ 只看最近互动日期 | 单一指标误判，客户可能刚互动但频率骤降 | 结合30天互动次数与趋势斜率综合判断 |
| ❌ 所有停滞客户一刀切 | 不同阶段客户合理沉默期不同（如签约前可能3周不联系） | 按客户阶段设置差异化阈值 |
| ❌ 忽略互动质量 | 10次无效寒暄不如1次实质性方案讨论 | 引入互动质量评分（内容关键词匹配） |
| ❌ 建议过于笼统 | "加强联系"等于没说 | 输出具体动作：什么时间、什么渠道、什么内容 |
| ❌ 只预警不闭环 | 识别风险后无跟进追踪 | 每次预警自动生成待办，下次调用时检查闭环 |

### 6.2 反模式示例

**反模式输入：**
```
客户跟进 --customer "某公司" --type "电话" --content "聊了一下"
```

**问题：** 内容过于模糊，无法判断互动质量与主题。

**正确输入：**
```
客户跟进 --customer "某公司" --type "电话" --content "讨论Q3续约方案，客户对价格有异议，提出竞品报价对比"
```

---

## 七、渐进式披露

### 7.1 速查卡（30秒上手）

```
1. 记一笔：客户跟进 --customer "客户名" --type "电话" --content "聊了什么"
2. 看一眼：客户轨迹 --customer "客户名"
3. 扫全局：商机预警 --threshold-days 14
4. 查状态：客户状态 --customer "客户名"
```

### 7.2 新手路径（首次使用）

1. 阅读「能力边界」了解工具范围
2. 从「记录客户互动」开始，积累数据
3. 使用「客户轨迹」查看单客户时间线
4. 运行「商机预警」了解全局风险分布
5. 参考「FAQ 反模式」避免常见错误

### 7.3 进阶路径（熟练用户）

1. 自定义阈值参数与风险权重
2. 结合互动质量评分优化预警精度
3. 使用批量导入接口处理历史数据
4. 将输出结果接入自动化工作流（需自行开发）
5. 定期运行 `--selftest` 验证环境完整性

---

## 八、参数参考表

| 参数名 | 类型 | 必填 | 默认值 | 取值范围 | 说明 |
|--------|------|------|--------|----------|------|
| customer | string | 是* | - | 任意字符串 | 客户ID或名称（*记录/查询时必填） |
| type | enum | 否 | other | phone/email/meeting/wechat/other | 互动类型 |
| content | string | 是 | - | 1-500字 | 互动内容摘要 |
| date | date | 否 | 当日 | YYYY-MM-DD | 互动日期 |
| from | date | 否 | 30天前 | YYYY-MM-DD | 查询起始日期 |
| to | date | 否 | 当日 | YYYY-MM-DD | 查询结束日期 |
| threshold-days | int | 否 | 14 | 1-90 | 停滞判定阈值 |
| risk-level | enum | 否 | all | low/medium/high/all | 风险等级筛选 |
| format | enum | 否 | json | json/table/text | 输出格式 |

---

## 九、用户协议

**使用本 Skill 即表示您同意以下条款：**

1. **责任承担**：使用者自行承担因使用本 Skill 产生的全部责任。本 Skill 提供的分析结果仅供参考，不构成任何商业决策的唯一依据。因依赖本 Skill 输出而导致的直接或间接损失，Skill 作者与贡献者不承担任何责任。

2. **数据安全**：使用者应确保输入数据的合法性与合规性，不得输入违反法律法规或侵犯第三方权益的内容。本 Skill 不负责数据加密与存储安全，敏感数据请自行脱敏处理。

3. **禁止反向工程**：使用者不得对本 Skill 进行反向工程、反编译、破解或试图提取底层算法与逻辑。不得移除或篡改本 Skill 中的版权声明与标识信息。

4. **合规使用**：使用者应遵守所在地区法律法规及所在组织的内部规定，不得将本 Skill 用于任何非法目的或违反道德伦理的场景。

5. **免责声明**：本 Skill 按"现状"提供，不附带任何明示或暗示的保证，包括但不限于适销性、特定用途适用性和非侵权性保证。

<!-- user-agreement-injected -->

---

## 十、许可证（License）

**MIT License**

Copyright (c) 2025 FlowForge Studio

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

<!-- professional-license-embedded -->

---

*本 Skill 由 AI 辅助生成，仅供参考。使用前请阅读相关文档并自行验证适用性。*
