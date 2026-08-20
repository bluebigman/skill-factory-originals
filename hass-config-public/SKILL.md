---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: hass-config-public
name: hass-config-public
displayName: 智能家居面板配置解析与可视化建议
description: 解析Home Assistant仪表盘配置，提取结构化信息并生成可视化方案建议。
version: 1.0.2
rules_version: cpr-20260820-n601
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/hass-config-public
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 智居工坊
agent_created: true
trigger_words: ["数据可视化", "仪表盘配置", "Home Assistant", "智能家居面板", "配置解析", "面板布局", "可视化方案"]
---

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->


> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# 智能家居面板配置解析与可视化建议（hass-config-public）

## 一、能力边界：一页纸速查卡

### 1.1 本 Skill 能做什么

| 能力项 | 说明 | 输出物 |
|--------|------|--------|
| 配置解析 | 读取 YAML 格式的 Home Assistant Lovelace 仪表盘配置 | 结构化 JSON 摘要 |
| 实体提取 | 识别卡片类型、实体列表、统计ID、条件逻辑 | 实体清单及用途分类 |
| 布局分析 | 分析视图结构、卡片堆叠方式、可见性条件 | 布局拓扑描述 |
| 可视化建议 | 基于卡片类型与实体特征，给出布局优化建议 | 建议列表（含优先级） |
| 配置校验 | 检查常见配置错误（如缺失 type、无效实体引用） | 错误报告（含错误码） |

### 1.2 本 Skill 不能做什么

| 限制项 | 说明 |
|--------|------|
| 不执行配置 | 不向 Home Assistant 实例推送配置，不调用其 API |
| 不修改原文件 | 只读解析，输出结果到独立文件 |
| 不处理非 YAML 格式 | 仅支持 `.yaml` / `.yml` 扩展名，不支持 JSON 格式的仪表盘配置 |
| 不验证实体真实性 | 无法确认实体 ID 是否在目标系统中真实存在，仅做格式与引用一致性检查 |
| 不生成完整 UI | 建议为文字描述，不产出可直接导入的 UI 主题包 |

### 1.3 适用对象

- 正在搭建或重构 Home Assistant 仪表盘的智能家居爱好者
- 需要批量审查多个仪表盘配置的集成商或运维人员
- 希望从现有配置中快速提取信息做二次开发的开发者

---

## 二、触发方式：场景映射表

| 触发词/短语 | 实际场景 | 本 Skill 的响应动作 |
|-------------|----------|---------------------|
| "帮我看看这个仪表盘配置" | 用户提供 YAML 文件路径 | 解析文件并输出结构化摘要 |
| "这个面板布局合理吗" | 用户希望获得优化建议 | 解析后输出布局分析 + 建议列表 |
| "提取所有实体" | 用户需要实体清单 | 输出按卡片类型分组的实体列表 |
| "批量检查配置" | 用户有多个文件 | 逐个解析并汇总报告 |
| "数据可视化" | 用户想了解可视化方案 | 输出卡片类型统计 + 可视化建议 |
| "配置解析" | 用户需要结构化数据 | 输出 JSON 格式的解析结果 |

---

## 三、标准流程

### 3.1 前置条件

| 条件项 | 要求 | 检查方式 |
|--------|------|----------|
| 文件格式 | YAML（.yaml / .yml） | 扩展名检查 |
| 文件编码 | UTF-8 无 BOM | 文件头检查 |
| 文件大小 | ≤ 5 MB | 文件属性检查 |
| 目录权限 | 当前目录可写（用于输出结果） | 写入测试 |
| 命名规范 | 文件名建议含 `dashboard` 或 `lovelace` 关键字 | 正则匹配 |

### 3.2 执行步骤

**Step 1：环境确认**
```bash
# 检查当前目录下所有候选文件
ls -la *.yaml *.yml 2>/dev/null
```

**Step 2：单样本试运行**
```bash
# 对单个文件执行解析（示例）
python3 -c "
from hass_config_public import parse_dashboard
result = parse_dashboard('dashboard_01.yaml')
print(result.summary())
"
```
核对输出字段：`views_count`、`cards_count`、`entity_count`、`card_types`。

**Step 3：批量执行**
```bash
# 对目录下所有 YAML 文件执行
python3 -m hass_config_public --input-dir ./configs --output-dir ./results
```

**Step 4：结果校验**
- 抽查 3 个输出条目，与源文件对照
- 检查实体 ID 是否与卡片内容一致
- 确认错误码标记是否准确

### 3.3 输出规范

输出文件为 Markdown 格式，包含以下章节：

```markdown
# 仪表盘配置解析报告

## 概览
- 视图数量：N
- 卡片总数：M
- 实体总数：K
- 卡片类型分布：...

## 视图详情
### 视图 1: [名称]
- 路径: /lovelace/xxx
- 卡片列表: ...

## 实体清单
| 实体 ID | 卡片类型 | 用途推测 |
|---------|----------|----------|

## 可视化建议
1. [建议内容]（优先级：高/中/低）

## 错误报告
- [错误码] 描述
```

---

## 四、置信度门控

当解析过程中遇到以下情况时，输出 `[需核实:字段名]` 占位符，不进行推测：

| 场景 | 占位符示例 | 说明 |
|------|------------|------|
| 实体 ID 格式合法但无法确认存在 | `[需核实:entity_exists]` | 需用户确认实体是否在系统中 |
| 卡片 type 字段缺失 | `[需核实:card_type]` | 无法判断卡片用途 |
| 条件逻辑引用未知变量 | `[需核实:condition_var]` | 无法解析条件表达式 |
| 视图 path 重复 | `[需核实:duplicate_path]` | 需用户确认是否为有意配置 |
| 统计 ID 与实体不匹配 | `[需核实:statistics_id]` | 需用户核对统计配置 |

**规则**：宁可输出占位符，不编造数据。占位符出现时，报告顶部会显示黄色警告条。

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| `E001` | 文件不存在 | "未找到指定文件，请检查路径" | 1. 确认路径正确 2. 检查文件名大小写 |
| `E002` | YAML 语法错误 | "YAML 解析失败，存在语法问题" | 1. 定位错误行号 2. 检查缩进 3. 验证引号闭合 |
| `E003` | 缺少 `views` 根键 | "配置缺少 views 根节点" | 1. 确认文件为 Lovelace 配置 2. 补充 views 键 |
| `E004` | 卡片缺少 `type` 字段 | "第 N 个卡片缺少 type 字段" | 1. 定位卡片位置 2. 补充 type 值 |
| `E005` | 实体 ID 格式非法 | "实体 ID 不符合命名规范" | 1. 检查 domain 前缀 2. 确认无非法字符 |
| `E006` | 文件编码不支持 | "文件编码非 UTF-8" | 1. 转换编码 2. 去除 BOM 头 |
| `E007` | 文件超过大小限制 | "文件超过 5MB 限制" | 1. 拆分文件 2. 精简配置 |
| `E008` | 输出目录不可写 | "无法写入输出目录" | 1. 检查权限 2. 更换目录 |

---

## 六、FAQ 反模式

### 常见坑 1：混淆 YAML 与 JSON 格式
- **错误做法**：直接传入 JSON 格式的仪表盘配置
- **正确做法**：先转换为 YAML 格式，或使用专门的 JSON 解析器
- **反模式对照**：本 Skill 仅支持 YAML，JSON 文件会返回 `E002` 错误

### 常见坑 2：忽略视图可见性条件
- **错误做法**：只统计卡片数量，忽略 `visibility` 条件
- **正确做法**：解析 `visibility` 字段，标注条件视图
- **反模式对照**：本 Skill 会提取条件逻辑并标记为 `conditional_view`

### 常见坑 3：实体 ID 大小写敏感
- **错误做法**：假设实体 ID 不区分大小写
- **正确做法**：保持原始大小写，在报告中原样输出
- **反模式对照**：本 Skill 不自动转换大小写，保留原始值

### 常见坑 4：嵌套卡片未递归解析
- **错误做法**：只解析顶层卡片，忽略 `stack` 或 `grid` 内的子卡片
- **正确做法**：递归遍历所有嵌套层级
- **反模式对照**：本 Skill 使用深度优先遍历，完整提取所有卡片

### 常见坑 5：忽略主题变量引用
- **错误做法**：不检查 `theme` 字段的引用
- **正确做法**：提取主题变量，标注未定义引用
- **反模式对照**：本 Skill 会输出 `theme_refs` 字段，未定义主题标记为 `[需核实:theme]`

---

## 七、渐进式披露

### 7.1 速查卡（30 秒上手）

```
用法：python3 -m hass_config_public <input.yaml> [--output <result.md>]
功能：解析仪表盘配置 → 输出结构化报告 + 可视化建议
限制：仅支持 YAML，≤5MB，只读不写
输出：Markdown 报告，含概览/实体清单/建议/错误
```

### 7.2 新手路径（首次使用）

1. 准备一个 YAML 格式的仪表盘配置文件
2. 运行单样本试运行命令（见 3.2 Step 2）
3. 查看输出的概览部分，确认解析成功
4. 阅读"可视化建议"章节，获取优化思路
5. 如有错误码，按第五节表格逐项修正

### 7.3 进阶路径（批量处理与二次开发）

1. 将多个配置文件放入同一目录
2. 使用 `--input-dir` 参数批量执行
3. 编写脚本解析输出的 Markdown 报告
4. 结合 `entity_count` 和 `card_types` 做配置复杂度评估
5. 将建议列表接入自动化流程，生成优化工单

---

## 八、参数速查表

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `input` | string | 是 | - | 输入 YAML 文件路径 |
| `--output` | string | 否 | `report.md` | 输出报告路径 |
| `--input-dir` | string | 否 | - | 批量处理目录 |
| `--output-dir` | string | 否 | `./results` | 批量输出目录 |
| `--verbose` | bool | 否 | `false` | 输出调试信息 |
| `--selftest` | bool | 否 | `false` | 运行自检 |
| `--version` | bool | 否 | `false` | 显示版本号 |

---

## 九、输出示例（节选）

```markdown
# 仪表盘配置解析报告

## 概览
- 视图数量：3
- 卡片总数：17
- 实体总数：23
- 卡片类型分布：`entities`(8), `thermostat`(3), `history-graph`(2), `gauge`(2), `custom:mini-graph-card`(2)

## 视图详情
### 视图 1: 客厅
- 路径: /lovelace/living_room
- 卡片列表: 5 张卡片，含 1 个条件卡片

## 实体清单
| 实体 ID | 卡片类型 | 用途推测 |
|---------|----------|----------|
| climate.living_room | thermostat | 客厅空调控制 |
| sensor.temperature_living | entities | 温度显示 |

## 可视化建议
1. 建议将 `sensor.temperature_living` 与 `climate.living_room` 合并为 `thermostat` 卡片（优先级：高）
2. 建议为 `history-graph` 卡片增加 `hours_to_show: 24` 参数（优先级：中）

## 错误报告
- [E004] 视图 2 第 3 个卡片缺少 type 字段
```

---

## 十、用户协议

**使用本 Skill 即表示您同意以下条款：**

1. **责任承担**：使用者自行承担因使用本 Skill 产生的全部责任。本 Skill 仅提供配置解析与建议，不构成对智能家居系统安全性的保证。因配置错误导致的设备异常、数据丢失或其他损失，本 Skill 作者不承担任何责任。

2. **禁止反向工程**：禁止对本 Skill 的源代码进行反向工程、反编译、破解或试图提取底层算法。禁止移除或篡改本 Skill 中的版权声明、许可证信息及 AI 生成标识。

3. **合规使用**：使用者应遵守当地法律法规及 Home Assistant 相关开源协议。不得将本 Skill 用于任何非法目的。

4. **免责声明**：本 Skill 按"现状"提供，不附带任何明示或暗示的担保，包括但不限于适销性、特定用途适用性和非侵权性保证。

<!-- user-agreement-injected -->

---

## 十一、许可证（License）

**MIT License**

```
MIT License

Copyright (c) 2025 智居工坊

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
