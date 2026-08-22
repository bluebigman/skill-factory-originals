---
slug: redash
name: redash
displayName: 数据看板 可视化 图表编排
description: 将数据源连接、查询与可视化配置转化为结构化交付物，辅助快速搭建数据看板。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 数据工坊·阿澈
agent_created: true
trigger_words: ["数据可视化", "redash", "仪表板", "数据看板", "图表生成", "BI报表", "数据大屏"]

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

---

# Redash 数据看板搭建辅助 Skill

## 一、能力边界速查卡

### 1.1 能做什么

| 能力项 | 说明 | 输出物 |
|--------|------|--------|
| 数据源连接配置 | 解析并整理各类数据库（PostgreSQL、MySQL、ClickHouse 等）的连接参数 | 连接配置清单（JSON/YAML） |
| 查询语句编排 | 将业务取数逻辑转化为可执行的 SQL 查询模板，含参数占位 | 查询脚本集（.sql 文件） |
| 可视化配置映射 | 将图表类型（折线、柱状、饼图、透视表等）与查询结果字段做映射 | 图表配置表（Markdown/CSV） |
| 仪表板布局规划 | 根据业务指标优先级，输出看板布局建议（栅格位置、尺寸） | 布局规划文档 |
| 数据刷新策略 | 设定缓存刷新周期、告警阈值等运维参数 | 运维配置建议表 |

### 1.2 不能做什么

| 限制项 | 说明 |
|--------|------|
| 不直接连接数据库 | 本 Skill 仅生成配置与脚本，不执行实际数据查询 |
| 不替代 Redash 服务端部署 | 服务器安装、Docker 编排等基础设施操作不在范围内 |
| 不生成复杂 ETL 逻辑 | 涉及多表 join 之外的清洗、聚合、机器学习特征工程需人工介入 |
| 不保证图表美观度 | 视觉风格调优（配色、字体、动画）需结合前端知识自行调整 |

### 1.3 适用对象

- 数据分析师：需要快速将取数逻辑转化为可视化看板
- 业务运营人员：有明确指标诉求，但缺乏 SQL 编写经验
- 数据平台研发：需要批量生成多数据源的查询模板

---

## 二、触发方式与场景映射

### 2.1 触发词

| 触发词 | 场景示例 |
|--------|----------|
| 数据可视化 | "帮我把销售数据做成可视化看板" |
| redash | "用 redash 搭建一个运营监控面板" |
| 仪表板 | "生成一个日活用户趋势仪表板" |
| 数据看板 | "我要一个库存预警看板" |
| 图表生成 | "根据这个 CSV 生成柱状图配置" |
| BI报表 | "把月度报表转成 BI 可视化" |
| 数据大屏 | "做一个实时订单大屏的配置" |

### 2.2 场景映射表

| 用户诉求（大白话） | 本 Skill 动作 | 输出物 |
|-------------------|---------------|--------|
| "我有一堆数据，想画个图看看趋势" | 解析数据字段，生成折线图配置 | 图表配置 JSON + SQL 模板 |
| "公司要用 redash，帮我写查询" | 根据业务描述生成 SQL 查询模板 | .sql 文件 + 参数说明 |
| "看板要每天自动刷新" | 设定 refresh 策略与缓存参数 | 运维配置表 |
| "多个团队共用看板，权限怎么分" | 生成用户组与权限建议清单 | 权限矩阵文档 |

---

## 三、标准执行流程

### 3.1 前置条件

| 条件项 | 要求 |
|--------|------|
| 输入文件 | 待处理的数据文件（CSV/Excel/JSON）或业务需求描述文档 |
| 命名规范 | 文件命名需包含业务域前缀，如 `sales_2024Q1.csv` |
| 环境确认 | 明确目标 Redash 版本（v8+ / v10+），不同版本 API 有差异 |
| 数据字典 | 如有字段说明文档，一并放入同目录，命名 `data_dictionary.md` |

### 3.2 执行步骤

**步骤 1：输入解析**

- 读取同目录下所有 `.csv` / `.json` / `.xlsx` 文件
- 提取字段名、数据类型、样例值（前 5 行）
- 输出：`input_summary.md`（字段清单 + 类型推断 + 空值率）

**步骤 2：单样本试运行**

- 选取一个最小数据集（如 100 行）执行查询模板生成
- 核对输出字段与源数据字段是否一一对应
- 校验 SQL 语法（使用 SQLite 本地引擎做语法检查）

**步骤 3：批量执行**

- 对全量数据文件执行模板生成
- 每个文件输出独立目录：`output/{filename}/`
- 保留原始文件备份至 `backup/` 目录

**步骤 4：结果校验**

- 抽查 3 个输出文件，核对：
  - 查询字段名与源数据一致
  - 图表类型与字段类型匹配（数值型→折线/柱状，类别型→饼图/条形）
  - 参数占位符格式正确（`{{param}}` 格式）

### 3.3 输出规范

| 输出物 | 格式 | 命名规则 |
|--------|------|----------|
| 查询脚本 | .sql | `query_{业务域}_{指标}.sql` |
| 图表配置 | .json | `viz_{图表类型}_{指标}.json` |
| 看板布局 | .md | `dashboard_layout.md` |
| 运维配置 | .yaml | `ops_config.yaml` |
| 汇总报告 | .md | `summary_report.md` |

---

## 四、置信度门控机制

### 4.1 信息不足时的处理

当遇到以下情况，输出 `[需核实:字段]` 占位符，不进行猜测：

| 场景 | 占位符示例 | 后续动作 |
|------|------------|----------|
| 字段含义不明确 | `[需核实:revenue_字段口径]` | 提示用户补充数据字典 |
| 时间粒度不明确 | `[需核实:日期粒度-日/周/月]` | 询问用户业务周期 |
| 图表类型不确定 | `[需核实:对比维度-按区域/按产品]` | 建议用户提供分析维度 |
| 数据源类型未知 | `[需核实:数据库类型-PG/MySQL/ClickHouse]` | 要求用户明确环境 |

### 4.2 禁止行为

- 不编造字段名或表名
- 不假设业务口径（如"活跃用户"定义需用户确认）
- 不生成超出输入数据范围的结论

---

## 五、错误码体系

| 错误码 | 错误描述 | 提示话术 | 修正步骤 |
|--------|----------|----------|----------|
| E001 | 输入文件缺失 | "未找到待处理文件，请将 CSV/JSON 文件放入当前目录" | 检查目录，确认文件存在 |
| E002 | 字段名冲突 | "检测到字段名重复，请检查源文件" | 重命名重复字段，添加后缀 |
| E003 | SQL 语法错误 | "生成的 SQL 存在语法问题，已定位到第 N 行" | 检查表名/字段名引用，确认引号使用 |
| E004 | 图表类型不匹配 | "数值型字段不能映射为饼图，已自动切换为柱状图" | 人工确认图表类型 |
| E005 | 参数占位符缺失 | "查询模板缺少时间参数，请补充 {{start_date}}" | 在 SQL 中添加参数定义 |
| E006 | 输出目录冲突 | "目标输出目录已存在同名文件，已生成副本" | 清理旧文件或修改命名 |

---

## 六、FAQ 与反模式对照

### 6.1 常见坑

| 坑位 | 反模式（错误做法） | 正模式（正确做法） |
|------|-------------------|-------------------|
| 字段类型误判 | 将字符串日期直接用于时间序列图 | 先转换为 datetime 类型，再映射图表 |
| 参数硬编码 | 在 SQL 中写死日期 `WHERE date = '2024-01-01'` | 使用 `{{start_date}}` 参数占位 |
| 忽略空值 | 直接对含 NULL 的字段做聚合 | 先处理空值（填充/剔除），再生成查询 |
| 图表过度堆砌 | 一个看板塞 20 个图表 | 按指标优先级控制在 6-8 个核心图表 |
| 缓存策略不当 | 实时数据设置 1 小时缓存 | 根据数据更新频率设定缓存（分钟级/小时级/天级） |

### 6.2 反模式自查清单

- [ ] 是否所有查询都使用了参数化而非硬编码？
- [ ] 是否对每个字段都明确了数据类型？
- [ ] 是否对空值率 > 30% 的字段做了特殊标注？
- [ ] 是否在输出中保留了原始文件备份？
- [ ] 是否对图表类型与字段类型做了匹配校验？

---

## 七、渐进式披露路径

### 7.1 速查卡（30 秒上手）

```
1. 放入数据文件 → 2. 运行 Skill → 3. 检查 input_summary.md → 4. 确认字段 → 5. 获取 SQL + 图表配置
```

### 7.2 新手路径（首次使用）

1. 阅读本 Skill 的「能力边界速查卡」
2. 准备一个最小数据集（< 100 行）
3. 执行单样本试运行
4. 对照「输出规范」检查生成物
5. 如有疑问，查阅「FAQ 与反模式对照」

### 7.3 进阶路径（熟练用户）

1. 自定义字段映射规则（在 `config/custom_mapping.yaml` 中定义）
2. 批量处理多数据源，使用统一命名规范
3. 结合 Redash API 实现自动化部署（需额外编写脚本）
4. 对生成的 SQL 做性能优化（添加索引建议、分区裁剪）

---

## 八、参数配置参考表

### 8.1 图表类型映射规则

| 字段类型 | 推荐图表 | 适用场景 |
|----------|----------|----------|
| 时间序列 + 数值 | 折线图 | 趋势分析 |
| 类别 + 数值 | 柱状图 | 对比分析 |
| 类别 + 占比 | 饼图 | 构成分析 |
| 多维度 + 数值 | 透视表 | 交叉分析 |
| 数值 + 数值 | 散点图 | 相关性分析 |

### 8.2 缓存刷新建议

| 数据更新频率 | 建议缓存时间 | 备注 |
|-------------|-------------|------|
| 实时（秒级） | 30 秒 | 需确认 Redash 版本支持 |
| 分钟级 | 5 分钟 | 适用于监控场景 |
| 小时级 | 1 小时 | 常规业务报表 |
| 天级 | 6 小时 | 日结数据 |

---

## 九、用户协议

<!-- user-agreement-injected -->

**使用本 Skill 即表示您同意以下条款：**

1. **责任承担**：使用者自行承担因使用本 Skill 产生的全部责任。包括但不限于因生成的 SQL 脚本、图表配置或看板布局导致的任何直接或间接损失。

2. **禁止反向工程**：不得对本 Skill 的提示词结构、生成逻辑进行逆向分析、破解或用于商业模型训练。

3. **数据安全**：使用者需自行确保输入数据的合规性，本 Skill 不承担数据泄露或违规使用的责任。

4. **无担保声明**：本 Skill 按"现状"提供，不附带任何明示或暗示的担保，包括但不限于适销性、特定用途适用性。

5. **修改与分发**：允许在保留本协议的前提下修改和再分发，但需注明原始来源。

---

## 十、许可证（License）

<!-- professional-license-embedded -->

**MIT License**

Copyright (c) 2024 数据工坊·阿澈

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

*本 Skill 由 AI 辅助生成，仅供参考。使用前请结合自身场景验证输出结果。*
