---
slug: laravel-dynamic-report-generator
name: laravel-dynamic-report-generator
displayName: 动态报表 数据透视 可视化输出
description: 将用户数据转化为结构化报表，支持动态查询与可视化输出。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: DataForge Studio
agent_created: true
trigger_words: ["报表", "数据可视化", "laravel dynamic report generator", "动态报表", "数据透视", "报表生成", "数据图表", "统计视图"]
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# Laravel 动态报表生成器 Skill 文档

## 一、能力边界（一页纸速查卡）

### 1.1 本 Skill 能做什么

| 能力项 | 说明 | 典型场景 |
|--------|------|----------|
| 动态查询 | 基于用户传入的筛选条件，实时构建数据库查询语句 | 按日期范围、状态、分类筛选订单数据 |
| 结构化报表 | 将查询结果整理为表格、分组汇总、透视表等结构 | 月度销售汇总、用户活跃度统计 |
| 可视化输出 | 生成图表数据（柱状图、折线图、饼图）所需的数据结构 | 趋势分析、占比分布 |
| 多格式导出 | 支持 JSON、CSV、HTML 表格三种输出格式 | 接口返回、文件下载、页面渲染 |
| Laravel 集成 | 提供 Artisan 命令、Service Provider 注册、中间件支持 | 在 Laravel 项目中快速接入 |

### 1.2 本 Skill 不能做什么

| 限制项 | 说明 |
|--------|------|
| 不执行实际查询 | 仅生成查询构建器（Query Builder）配置，不直接连接数据库执行 |
| 不处理认证授权 | 不包含用户登录、权限校验逻辑，需自行集成 |
| 不支持复杂 ETL | 不做跨库数据同步、清洗转换，仅针对单库单表查询 |
| 不生成前端代码 | 可视化输出为数据结构，不包含 Vue/React 组件代码 |
| 不替代迁移工具 | 不负责数据库表结构创建与修改 |

### 1.3 适用对象

- Laravel 开发者（≥ 8.0 版本）
- 需要快速搭建管理后台报表模块的团队
- 希望将查询逻辑与视图层解耦的架构设计者

---

## 二、触发方式

### 2.1 触发词速查

| 触发词 | 场景描述 | 示例指令 |
|--------|----------|----------|
| 报表 | 需要生成数据汇总表 | "帮我生成上个月的订单报表" |
| 数据可视化 | 需要图表展示数据 | "把销售数据做成可视化图表" |
| 动态报表 | 需要按条件筛选的报表 | "做一个可按日期筛选的动态报表" |
| 数据透视 | 需要多维汇总分析 | "按地区和产品做数据透视" |
| 报表生成 | 批量生成定期报表 | "每周一自动生成库存报表" |
| 数据图表 | 需要图表数据结构 | "给我饼图数据，展示各品类占比" |

### 2.2 触发词映射表

| 用户说（大白话） | Skill 实际动作 |
|------------------|----------------|
| "我要看这个月的收入情况" | 生成月度收入报表，按天分组，输出折线图数据 |
| "帮我统计一下各渠道的用户来源" | 生成渠道分布报表，输出饼图数据 |
| "想按部门看看加班时长" | 生成部门维度透视表，支持多级汇总 |
| "导出 CSV 给我" | 生成 CSV 格式的报表文件 |

---

## 三、标准流程

### 3.1 前置条件

| 条件 | 要求 | 验证方式 |
|------|------|----------|
| Laravel 版本 | ≥ 8.0 | `php artisan --version` |
| PHP 版本 | ≥ 7.4 | `php -v` |
| 数据库连接 | 已配置且可访问 | `php artisan migrate:status` |
| 目标数据表 | 已存在且包含所需字段 | `php artisan db:show`（Laravel 11+）或直接查询 |

### 3.2 执行步骤

#### 步骤 1：下载 Skill 文件

```bash
# 将 run.py 下载到项目根目录
curl -O https://your-source/run.py
# 或手动放置到项目目录
```

#### 步骤 2：赋予执行权限（可选）

```bash
chmod +x run.py
```

#### 步骤 3：验证安装

```bash
python3 run.py --selftest
# 预期输出：All checks passed. Version 1.0.0
```

#### 步骤 4：创建报表配置

在 `config/reports/` 目录下新建配置文件，示例：

```php
<?php
// config/reports/sales.php
return [
    'table' => 'orders',
    'group_by' => ['date', 'status'],
    'aggregates' => [
        'total_amount' => 'sum',
        'order_count' => 'count',
    ],
    'filters' => [
        'date_range' => ['created_at', '>=', '2024-01-01'],
        'status' => ['status', '=', 'completed'],
    ],
    'output' => [
        'format' => 'json', // json | csv | html
        'chart' => 'line',  // line | bar | pie
    ],
];
```

#### 步骤 5：生成报表

```bash
python3 run.py --config config/reports/sales.php --output storage/reports/sales_2024.json
```

### 3.3 输出规范

| 输出格式 | 结构说明 | 示例 |
|----------|----------|------|
| JSON | `{ "meta": {...}, "data": [...], "chart": {...} }` | 见下方示例 |
| CSV | 首行为列名，后续为数据行 | `date,total_amount,order_count` |
| HTML | 标准 `<table>` 结构，含 `<thead>` 和 `<tbody>` | 可直接嵌入 Blade 模板 |

**JSON 输出示例：**

```json
{
  "meta": {
    "generated_at": "2024-03-15T10:30:00Z",
    "query_time_ms": 45,
    "row_count": 31
  },
  "data": [
    { "date": "2024-03-01", "total_amount": 12500.00, "order_count": 42 },
    { "date": "2024-03-02", "total_amount": 9800.00, "order_count": 35 }
  ],
  "chart": {
    "type": "line",
    "x_axis": "date",
    "series": [
      { "name": "total_amount", "data": [12500.00, 9800.00] },
      { "name": "order_count", "data": [42, 35] }
    ]
  }
}
```

---

## 四、置信度门控

### 4.1 信息不足时的处理

当遇到以下情况时，输出 `[需核实:字段]` 占位符，**不编造数据**：

| 场景 | 处理方式 | 示例 |
|------|----------|------|
| 数据表字段不确定 | 在报表中标注 `[需核实:字段名]` | `"total_revenue": "[需核实:total_revenue]"` |
| 聚合函数不确定 | 使用 `[需核实:聚合方式]` 提示 | `"aggregate": "[需核实:聚合方式]"` |
| 日期格式不确定 | 标注 `[需核实:日期格式]` | `"date": "[需核实:日期格式]"` |
| 筛选条件不明确 | 返回全量数据并在 meta 中提示 | `"warning": "筛选条件不完整，已返回全量数据"` |

### 4.2 置信度分级

| 级别 | 说明 | 适用场景 |
|------|------|----------|
| 高（≥90%） | 字段名、表名、聚合方式均明确 | 配置文件中已完整定义 |
| 中（70-89%） | 部分字段名推测，但结构合理 | 表结构已知，个别字段名不确定 |
| 低（<70%） | 多个关键信息缺失 | 仅提供表名，无字段信息 |

---

## 五、错误码体系

### 5.1 常见错误对照表

| 错误码 | 错误描述 | 提示话术 | 修正步骤 |
|--------|----------|----------|----------|
| `E001` | 配置文件不存在 | "未找到配置文件，请检查路径" | 1. 确认文件路径正确<br>2. 检查文件名大小写 |
| `E002` | 数据表不存在 | "目标数据表不存在，请检查表名" | 1. 执行 `php artisan list` 查看可用表<br>2. 确认表名拼写 |
| `E003` | 字段不存在 | "字段 [字段名] 不存在于表中" | 1. 执行 `DESCRIBE 表名` 查看字段<br>2. 修正配置中的字段名 |
| `E004` | 聚合函数无效 | "不支持的聚合函数，可用：sum, count, avg, min, max" | 1. 检查聚合函数拼写<br>2. 使用支持的函数 |
| `E005` | 输出目录不可写 | "输出目录无写入权限" | 1. 执行 `chmod -R 755 storage/reports`<br>2. 确认目录存在 |
| `E006` | 数据库连接失败 | "数据库连接失败，请检查 .env 配置" | 1. 检查 DB_HOST/DB_PORT<br>2. 执行 `php artisan config:clear` |
| `E007` | 日期范围无效 | "开始日期不能晚于结束日期" | 1. 检查日期参数<br>2. 确保格式为 YYYY-MM-DD |

### 5.2 错误处理流程

```
检测到错误 → 输出错误码和提示话术 → 建议修正步骤 → 等待用户确认后重试
```

---

## 六、FAQ 反模式

### 6.1 常见坑与反模式对照

| 坑 | 反模式（错误做法） | 正确做法 |
|----|-------------------|----------|
| 字段名硬编码 | 在代码中直接写 `$report->total` | 使用配置驱动，字段名从配置读取 |
| 忽略索引 | 对无索引字段做 `LIKE '%xxx%'` 查询 | 使用前缀匹配 `LIKE 'xxx%'` 或全文索引 |
| N+1 查询 | 循环中逐条查询关联数据 | 使用 `with()` 预加载或 `join` 一次查询 |
| 内存溢出 | 一次性加载全表数据 | 使用 `chunk()` 分批处理或 `cursor()` 流式读取 |
| 时区混乱 | 直接使用 `now()` 不指定时区 | 统一使用 `Carbon::now('Asia/Shanghai')` |
| 聚合错误 | 对 `NULL` 值直接 `sum()` | 使用 `COALESCE` 或 `ifnull` 预处理 |

### 6.2 反模式示例

```php
// ❌ 反模式：硬编码字段名
$report = Order::select('total')->get();

// ✅ 正确做法：配置驱动
$config = config('reports.sales');
$report = DB::table($config['table'])
    ->select($config['fields'])
    ->get();
```

---

## 七、渐进式披露

### 7.1 速查卡（30 秒上手）

```
1. 下载 run.py 到项目目录
2. 创建 config/reports/xxx.php 配置文件
3. 执行 python3 run.py --config config/reports/xxx.php
4. 查看输出文件
```

### 7.2 新手路径（首次使用）

1. 阅读「能力边界」了解适用范围
2. 使用「标准流程」中的示例配置模板
3. 运行 `--selftest` 验证环境
4. 从最简单的单表查询开始

### 7.3 进阶路径（深度使用）

1. 研究「错误码体系」处理复杂场景
2. 参考「FAQ 反模式」优化查询性能
3. 自定义输出格式（扩展 `output` 配置）
4. 集成到 Laravel 任务调度（`schedule`）

---

## 八、用户协议

<!-- user-agreement-injected -->

**使用本 Skill 即表示您同意以下条款：**

1. **责任承担**：使用者自行承担因使用本 Skill 产生的全部责任。包括但不限于数据准确性、系统性能、业务决策等后果。

2. **禁止反向工程**：不得对本 Skill 进行反向工程、反编译、破解或试图提取源代码（除非适用法律允许）。

3. **无担保声明**：本 Skill 按"现状"提供，不附带任何明示或暗示的担保，包括但不限于适销性、特定用途适用性和非侵权性。

4. **合规使用**：使用者应确保使用场景符合当地法律法规及所在组织的政策要求。

5. **数据安全**：使用者应对通过本 Skill 处理的数据负责，包括数据脱敏、加密存储和访问控制。

---

## 九、许可证（License）

<!-- professional-license-embedded -->

### MIT License

```
MIT License

Copyright (c) 2024 原创作者（自持版权）

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

## 十、版本历史

| 版本 | 日期 | 变更说明 |
|------|------|----------|
| 1.0.0 | 2024-03-15 | 初始版本，包含动态查询、报表生成、可视化输出核心功能 |

---

*本 Skill 由 AI 辅助生成，仅供参考。使用前请阅读相关文档并充分测试。*
