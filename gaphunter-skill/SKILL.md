---
slug: gaphunter-skill
name: gaphunter-skill
displayName: 竞品差距 结构化分析 报告生成
description: 将竞品数据转化为结构化差距分析报告，支持过滤与PDF导出。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: SkillForge Studio
agent_created: true
trigger_words: ["代码审查", "竞品分析", "差距分析", "gap analysis", "competitor review", "功能对比", "产品对标", "--selftest", "--version"]
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# gaphunter-skill 技能文档

## 一、能力边界（一页纸速查卡）

### 1.1 能做什么

| 能力项 | 说明 | 输出物 |
|--------|------|--------|
| 数据解析 | 读取同一目录下的竞品数据文件（支持 CSV / JSON / Markdown 表格） | 标准化内部数据结构 |
| 差距识别 | 按预设维度（功能、性能、体验、价格）自动比对目标产品与竞品 | 差距清单（含差距等级） |
| 报告生成 | 生成结构化 Markdown 报告，含差距摘要、明细表、优先级建议 | `gap-report-{timestamp}.md` |
| 过滤筛选 | 支持按差距等级（高/中/低）、维度、竞品名称过滤报告内容 | 过滤后的报告子集 |
| PDF 导出 | 将 Markdown 报告转换为 PDF 文件（需本地安装 `pandoc` 与 `xelatex`） | `gap-report-{timestamp}.pdf` |
| 自检模式 | 运行 `--selftest` 验证环境依赖与基础功能 | 自检报告 |

### 1.2 不能做什么

| 限制项 | 说明 |
|--------|------|
| 不采集数据 | 不主动抓取网页或调用外部 API 获取竞品信息，仅处理用户提供的本地文件 |
| 不自动更新 | 不监听文件变化，每次执行需手动触发 |
| 不跨目录 | 仅处理当前工作目录下的文件，不递归扫描子目录 |
| 不生成虚假数据 | 若源数据缺失关键字段，输出 `[需核实:字段名]` 占位符，不编造数值 |
| 不做决策建议 | 报告提供差距事实与优先级排序，不给出"应该收购/放弃"等战略结论 |

### 1.3 适用对象

- 产品经理：快速梳理竞品功能覆盖情况
- 技术负责人：评估技术方案与竞品的性能差距
- 市场分析师：整理竞品定价与卖点差异
- 创业者：验证产品定位与市场空白

---

## 二、触发方式

### 2.1 触发词

直接使用以下任一触发词即可激活本 Skill：

```
代码审查、竞品分析、差距分析、gap analysis、competitor review、功能对比、产品对标
```

### 2.2 场景映射表

| 大白话场景 | 触发指令示例 | 预期行为 |
|------------|--------------|----------|
| "帮我看看我们和XX的差距" | `差距分析 对比文件在 ./data/` | 解析目录下所有竞品文件，生成差距报告 |
| "只关注高优先级问题" | `竞品分析 --filter-level high` | 仅输出差距等级为"高"的条目 |
| "把报告导成 PDF" | `gap analysis --export pdf` | 生成 Markdown 报告后自动转换 PDF |
| "检查环境是否可用" | `--selftest` | 输出依赖检查清单与通过/失败状态 |
| "看版本号" | `--version` | 输出当前 Skill 版本号 |

---

## 三、标准流程

### 3.1 前置条件

| 条件 | 要求 | 检查方式 |
|------|------|----------|
| 输入文件 | 与 Skill 同目录，命名含 `competitor` 或 `target` 关键字 | 执行时自动扫描 |
| 文件格式 | CSV（UTF-8 编码）、JSON 数组、Markdown 表格 | 解析器自动识别 |
| 必填字段 | `feature_name`（功能名）、`competitor_name`（竞品名）、`target_value`（目标值）、`competitor_value`（竞品值） | 缺失时输出 `[需核实:字段名]` |
| 可选字段 | `dimension`（维度）、`weight`（权重 0-1）、`notes`（备注） | 缺失时使用默认值 |
| 环境依赖 | Python 3.8+；PDF 导出需 `pandoc` 与 `xelatex` | `--selftest` 自动检测 |

### 3.2 执行步骤

#### 步骤 1：准备输入

1. 将所有待分析文件放入同一目录。
2. 确认文件命名包含 `competitor` 或 `target` 关键字（如 `competitor_A.csv`、`target_features.json`）。
3. 确认每个文件包含必填字段（见 3.1 表格）。

#### 步骤 2：试运行（单样本验证）

```bash
# 仅处理第一个文件，输出到 stdout 预览
python gaphunter.py --input ./data/competitor_A.csv --dry-run
```

- 核对输出字段：`feature_name`、`competitor_name`、`gap_score`（差距得分 0-100）、`gap_level`（高/中/低）。
- 确认差距等级阈值：得分 ≥ 70 为"高"，40-69 为"中"，< 40 为"低"。

#### 步骤 3：批量执行

```bash
# 处理目录下所有匹配文件，生成完整报告
python gaphunter.py --input ./data/ --output ./reports/
```

- 执行前自动备份原始文件至 `./backup/` 目录（时间戳命名）。
- 输出文件命名规则：`gap-report-YYYYMMDD-HHMMSS.md`。

#### 步骤 4：校验结果

1. 抽查报告前 5 条记录，与源文件比对 `target_value` 与 `competitor_value` 是否一致。
2. 检查 `[需核实:字段]` 占位符数量，若超过总条目 20%，建议补充源数据后重新执行。
3. 确认过滤条件生效（若使用了 `--filter-level` 或 `--filter-dimension`）。

### 3.3 输出规范

#### 报告结构（Markdown）

```markdown
# 差距分析报告

## 摘要
- 分析时间：{timestamp}
- 竞品数量：{n}
- 功能条目总数：{m}
- 高优先级差距：{h} 项 / 中优先级：{mid} 项 / 低优先级：{low} 项

## 差距明细表
| 功能名 | 竞品名 | 维度 | 目标值 | 竞品值 | 差距得分 | 差距等级 |
|--------|--------|------|--------|--------|----------|----------|
| ...    | ...    | ...  | ...    | ...    | ...      | ...      |

## 优先级建议
- 高优先级（得分 ≥ 70）：建议 2 周内评估
- 中优先级（40-69）：建议下个迭代规划
- 低优先级（< 40）：持续观察

## 附录：原始数据备份位置
```

#### 差距得分计算规则

```
gap_score = (1 - competitor_value / target_value) * 100
若 target_value 为 0 或缺失，则 gap_score = 100（视为完全缺失）
若 competitor_value 缺失，则 gap_score = 100（视为未实现）
```

---

## 四、置信度门控

### 4.1 占位符规则

当源数据存在以下情况时，输出 `[需核实:字段名]` 占位符，不进行任何推断：

| 情况 | 占位符示例 | 后续处理 |
|------|------------|----------|
| 目标值缺失 | `[需核实:target_value]` | 报告顶部提示"存在 N 条数据待核实" |
| 竞品值缺失 | `[需核实:competitor_value]` | 该条目不参与差距得分计算 |
| 功能名缺失 | `[需核实:feature_name]` | 该条目跳过，计入"无效条目"统计 |
| 维度值非法 | `[需核实:dimension]` | 默认归入"未分类"维度 |

### 4.2 置信度分级

| 置信度 | 条件 | 报告标注 |
|--------|------|----------|
| 高（≥ 90%） | 所有必填字段完整，且数值类型正确 | 无特殊标注 |
| 中（70-89%） | 存在 1-2 个可选字段缺失 | 报告脚注说明 |
| 低（< 70%） | 存在必填字段缺失或类型错误 | 报告顶部显著警告 |

---

## 五、错误码体系

| 错误码 | 错误描述 | 提示话术 | 修正步骤 |
|--------|----------|----------|----------|
| `E001` | 目录下无匹配文件 | "未找到包含 competitor 或 target 关键字的文件，请检查文件名" | 重命名文件，确保包含关键字 |
| `E002` | 文件格式无法解析 | "文件 {filename} 格式不支持，仅支持 CSV/JSON/Markdown 表格" | 转换文件格式后重试 |
| `E003` | 必填字段缺失 | "文件 {filename} 缺少必填字段：{field_list}" | 补充字段后重新执行 |
| `E004` | 数值类型错误 | "字段 {field} 的值 '{value}' 无法转换为数值" | 检查源数据，修正为数字 |
| `E005` | PDF 导出失败 | "PDF 导出失败：{error_msg}。请确认已安装 pandoc 与 xelatex" | 安装依赖后重试，或仅使用 Markdown 输出 |
| `E006` | 输出目录不可写 | "无法写入输出目录 {path}，请检查权限" | 修改目录权限或指定其他路径 |
| `E007` | 自检失败 | "自检失败：{failed_items}。请参考自检报告逐项修复" | 按自检报告提示安装/配置依赖 |

---

## 六、FAQ 反模式

| 常见坑 | 反模式（错误做法） | 正确做法 |
|--------|-------------------|----------|
| 数据格式混乱 | 在 CSV 中混用中英文逗号、引号不配对 | 统一使用 UTF-8 编码，逗号分隔，字符串用双引号包裹 |
| 单位不一致 | 目标值用"秒"，竞品值用"毫秒" | 统一单位后再执行，或在 `notes` 字段注明换算关系 |
| 权重滥用 | 所有维度权重设为 1，导致总分失真 | 权重范围 0-1，且同一维度下权重总和应为 1 |
| 忽略备份 | 直接覆盖原始文件 | 每次执行前自动备份至 `./backup/`，保留原始数据 |
| 过度解读报告 | 将"高优先级差距"直接等同于"必须立即修复" | 报告仅提供事实与排序，是否修复需结合业务上下文判断 |

---

## 七、渐进式披露

### 7.1 速查卡（30 秒上手）

```
1. 放文件：将竞品数据文件放入当前目录，命名含 competitor 或 target
2. 跑命令：python gaphunter.py --input ./ --output ./reports/
3. 看报告：打开 reports/ 目录下最新生成的 .md 文件
4. 可选：加 --filter-level high 只看高优先级；加 --export pdf 导出 PDF
```

### 7.2 新手路径（首次使用）

1. 运行 `--selftest` 确认环境可用。
2. 准备一个最小样本文件（3-5 条数据），执行 `--dry-run` 预览输出。
3. 核对输出字段含义（见 3.3 输出规范）。
4. 确认无误后，再处理全量数据。

### 7.3 进阶路径（深度使用）

1. 自定义维度与权重：在输入 JSON 中增加 `dimension` 与 `weight` 字段。
2. 调整差距等级阈值：修改配置文件 `config.yaml` 中的 `thresholds` 参数。
3. 扩展过滤条件：支持 `--filter-competitor`、`--filter-dimension` 组合过滤。
4. 集成 CI/CD：将批量执行命令加入流水线，自动生成每日差距报告。

---

## 八、用户协议

<!-- user-agreement-injected -->

**使用本 Skill 即表示您同意以下条款：**

1. **责任承担**：使用者自行承担因使用本 Skill 产生的全部责任。本 Skill 仅提供数据处理与报告生成功能，不构成任何形式的决策建议或商业指导。
2. **数据安全**：使用者应确保输入数据不包含敏感信息（如个人隐私、商业机密）。本 Skill 不收集、不上传任何数据，所有处理均在本地完成。
3. **禁止反向工程**：使用者不得对本 Skill 的源代码进行反向工程、反编译、破解或试图提取底层算法。
4. **无担保声明**：本 Skill 按"现状"提供，不附带任何明示或暗示的担保，包括但不限于适销性、特定用途适用性。
5. **合规使用**：使用者应遵守所在地法律法规，不得将本 Skill 用于任何非法目的。

---

## 九、许可证（License）

<!-- professional-license-embedded -->

### MIT License

```
MIT License

Copyright (c) 2024 SkillForge Studio

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

---

*本 Skill 由 AI 辅助生成，仅供参考。使用前请阅读相关文档。*
