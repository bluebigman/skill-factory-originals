---
slug: django-dashing
name: django-dashing
displayName: 数据看板 Django 快速搭建
description: 将用户数据快速转化为可交互的Django仪表盘应用。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 数据工坊
agent_created: true
trigger_words: ["django-dashing", "数据可视化", "仪表盘", "dashboard", "看板开发", "数据面板", "可视化报表"]
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# django-dashing — 数据看板 Django 快速搭建

## 一、能力边界（一页纸速查卡）

### 1.1 能做什么

| 能力项 | 说明 | 适用场景 |
|--------|------|----------|
| 数据接入 | 读取 CSV、JSON、Excel（需 pandas）等结构化数据 | 业务报表、运营数据、日志统计 |
| 看板生成 | 自动生成 Django 项目 + 仪表盘页面 | 内部管理后台、数据展示站点 |
| 图表渲染 | 集成 Chart.js，支持折线图、柱状图、饼图 | 趋势分析、占比展示、对比视图 |
| 交互筛选 | 按日期范围、分类字段进行前端筛选 | 运营看板、销售分析 |
| 多页布局 | 支持多图表网格布局，自动适配屏幕 | 大屏展示、监控中心 |

### 1.2 不能做什么

| 限制项 | 说明 |
|--------|------|
| 不支持实时流数据 | 仅处理静态文件或数据库快照，不接入 WebSocket/消息队列 |
| 不做复杂权限系统 | 仅提供 Django 默认 admin 登录，不实现细粒度权限 |
| 不生成业务逻辑 | 只做展示层，不生成增删改查的业务代码 |
| 不处理非结构化数据 | 图片、音频、自由文本等需自行预处理 |
| 不保证图表美观度 | 使用默认主题，不进行视觉定制 |

### 1.3 适用对象

- 需要快速搭建内部数据看板的开发人员
- 已有数据文件（CSV/JSON）但缺乏可视化界面的团队
- 希望用 Django 统一管理数据展示的初学者

---

## 二、触发方式

### 2.1 触发词

当用户输入以下任一关键词时，本 Skill 被激活：

- `django-dashing`
- `数据可视化`
- `仪表盘`
- `dashboard`
- `看板开发`
- `数据面板`
- `可视化报表`

### 2.2 场景映射表

| 用户说（大白话） | 实际需求 | 本 Skill 响应 |
|------------------|----------|---------------|
| "帮我把这个 CSV 变成网页看板" | 将数据文件转为可交互网页 | 生成 Django 项目 + 图表页面 |
| "我想做个销售数据仪表盘" | 销售数据可视化 | 读取数据 → 生成折线图/柱状图 |
| "给我搞个监控大屏" | 多指标同时展示 | 多图表网格布局，自动适配 |
| "这个 JSON 数据怎么展示" | JSON 数据可视化 | 解析 JSON → 生成表格 + 图表 |

---

## 三、标准流程

### 3.1 前置条件

| 条件 | 要求 | 检查方式 |
|------|------|----------|
| Python 环境 | Python 3.8+ | `python --version` |
| Django 安装 | Django 3.2+ | `pip show django` |
| 数据文件 | CSV/JSON，编码 UTF-8 | 文件可正常打开 |
| 数据格式 | 至少包含 1 个数值字段 + 1 个分类/时间字段 | 人工确认 |

### 3.2 执行步骤

#### 步骤 1：准备输入

将待处理的数据文件放入同一工作目录，确认命名规范一致（如 `data.csv`、`sales.json`）。

```bash
mkdir my_dashboard
cd my_dashboard
cp /path/to/your/data.csv .
```

#### 步骤 2：试运行（单样本验证）

先用单个数据文件执行，核对输出字段与格式：

```bash
django-dashing --input data.csv --output preview.html --dry-run
```

检查 `preview.html` 中的字段名、数据类型、图表类型是否符合预期。

#### 步骤 3：批量执行

确认无误后，对全量数据执行：

```bash
django-dashing --input data.csv --output dashboard/
```

生成 Django 项目结构：

```
dashboard/
├── manage.py
├── dashboard_app/
│   ├── views.py
│   ├── urls.py
│   └── templates/
│       └── index.html
└── static/
    └── js/
        └── chart.min.js
```

#### 步骤 4：校验结果

抽查输出条目，核对关键字段与源数据一致：

```bash
python manage.py runserver
# 打开 http://localhost:8000 检查图表数据
```

### 3.3 输出规范

| 输出项 | 格式 | 说明 |
|--------|------|------|
| Django 项目 | 标准项目结构 | 可直接 `runserver` 运行 |
| 图表数据 | JSON 嵌入 HTML | 前端 Chart.js 读取 |
| 日志 | 控制台输出 | 记录处理进度和错误 |

---

## 四、置信度门控

当输入数据信息不足时，使用 `[需核实:字段]` 占位，不编造数据：

| 场景 | 处理方式 |
|------|----------|
| 数据文件缺少数值字段 | 输出 `[需核实:数值字段]`，提示用户补充 |
| 日期格式无法解析 | 输出 `[需核实:日期格式]`，建议提供 `YYYY-MM-DD` |
| 分类字段为空 | 输出 `[需核实:分类字段]`，提示选择分组维度 |
| 文件编码异常 | 输出 `[需核实:文件编码]`，建议转为 UTF-8 |

---

## 五、错误码体系

| 错误码 | 错误描述 | 提示话术 | 修正步骤 |
|--------|----------|----------|----------|
| E001 | 文件不存在 | "未找到指定文件，请检查路径" | 确认文件路径，重新执行 |
| E002 | 文件格式不支持 | "仅支持 CSV 或 JSON 格式" | 转换文件格式后重试 |
| E003 | 缺少数值字段 | "数据中未找到可聚合的数值列" | 检查数据表头，添加数值列 |
| E004 | Django 未安装 | "未检测到 Django，请先安装" | `pip install django` |
| E005 | 端口被占用 | "默认端口 8000 被占用" | 使用 `--port 8080` 指定其他端口 |
| E006 | 数据量过大 | "数据超过 10 万行，可能影响性能" | 建议抽样或分片处理 |

---

## 六、FAQ 反模式

### 6.1 常见坑

| 坑 | 反模式 | 正确做法 |
|----|--------|----------|
| 数据格式混乱 | 直接读取不检查 | 先 `--dry-run` 预览 |
| 字段名含中文 | 直接作为变量名 | 自动转拼音或英文别名 |
| 时间字段为字符串 | 直接排序 | 先解析为 datetime 类型 |
| 图表类型选择错误 | 全部用折线图 | 根据字段类型自动推荐 |
| 忽略数据备份 | 直接覆盖原文件 | 保留原始文件副本 |

### 6.2 反模式对照表

| 反模式 | 问题 | 建议 |
|--------|------|------|
| "这个工具能处理所有格式" | 过度承诺 | 明确支持 CSV/JSON，其他需转换 |
| "图表一定好看" | 主观标准 | 提供默认主题，用户可自行调整 |
| "数据不会出错" | 忽略数据质量问题 | 增加校验步骤，输出警告 |
| "生成后不用改" | 忽略定制需求 | 提供修改入口，说明可编辑位置 |

---

## 七、渐进式披露

### 7.1 速查卡（30 秒上手）

```
1. 准备数据文件（CSV/JSON）
2. 运行：django-dashing --input data.csv --output dashboard/
3. 启动：cd dashboard && python manage.py runserver
4. 打开 http://localhost:8000 查看
```

### 7.2 新手路径（5 分钟）

1. 阅读「能力边界」了解适用范围
2. 按「标准流程」步骤 1-2 执行试运行
3. 查看生成的 `preview.html` 确认数据正确
4. 按步骤 3-4 生成完整项目并启动

### 7.3 进阶路径（深入定制）

1. 修改 `dashboard_app/views.py` 调整数据过滤逻辑
2. 编辑 `templates/index.html` 自定义布局
3. 在 `static/js/` 中添加自定义图表配置
4. 集成 Django admin 实现数据管理

---

## 八、参数参考表

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `--input` | string | 必填 | 输入数据文件路径 |
| `--output` | string | `./dashboard` | 输出目录 |
| `--dry-run` | flag | false | 仅生成预览 HTML |
| `--port` | int | 8000 | 开发服务器端口 |
| `--chart-type` | string | auto | 图表类型（line/bar/pie/auto） |
| `--title` | string | 数据看板 | 页面标题 |
| `--theme` | string | default | 主题（default/dark/light） |

---

## 九、用户协议

<!-- user-agreement-injected -->

**使用本 Skill 即表示您同意以下条款：**

1. **责任承担**：使用者自行承担因使用本 Skill 产生的全部责任。包括但不限于数据准确性、系统兼容性、业务影响等。
2. **禁止反向工程**：不得对本 Skill 生成的代码进行反向工程、反编译或试图提取底层算法。
3. **数据安全**：使用者需确保输入数据不包含敏感信息，或已获得合法使用授权。
4. **无担保**：本 Skill 按"现状"提供，不提供任何明示或暗示的担保。
5. **修改权限**：使用者可自由修改生成的代码，但修改后的代码责任由使用者自行承担。

---

## 十、许可证（License）

<!-- professional-license-embedded -->

**MIT License**

Copyright (c) 2024 数据工坊

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
