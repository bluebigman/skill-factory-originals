---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: scrapecraft
name: scrapecraft
displayName: 网页采集 流程编排 数据抽取
description: 用自然语言构建、测试并部署网页采集流程的可视化编辑器。
version: 1.0.2
rules_version: cpr-20260819-n551
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/scrapecraft
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: FlowForge Studio
agent_created: true
trigger_words: ["爬虫采集","网页抓取","数据抽取","采集流程","scrapecraft","页面解析","数据管道"]
---

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->


> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# Scrapecraft — 网页采集流程可视化编排 Skill

## 一、能力边界（一页纸速查卡）

### 1.1 能做什么

| 能力项 | 说明 | 示例 |
|--------|------|------|
| 自然语言转流程 | 将中文描述转换为可执行的采集步骤链 | "抓取商品标题和价格" → 选择器 + 输出字段 |
| 单步调试 | 对单个采集步骤进行试运行，查看中间结果 | 仅执行"翻页"步骤，观察 URL 变化 |
| 批量执行 | 对全量目标 URL 执行完整流程 | 1000 个商品页依次采集 |
| 结果校验 | 对比源页面与输出字段，标记不一致项 | 价格字段缺失时输出 `[需核实:price]` |
| 流程导出 | 生成可独立运行的 Python 脚本 | 输出 `main.py` 及依赖清单 |

### 1.2 不能做什么

| 限制项 | 说明 |
|--------|------|
| 不处理验证码 | 若目标站点出现验证码，流程将暂停并提示人工介入 |
| 不绕过反爬机制 | 不提供 IP 轮换、指纹伪装等规避手段 |
| 不保证数据完整性 | 页面结构变化可能导致字段缺失，需人工确认 |
| 不支持流式数据 | 仅处理静态 HTML 或已加载的 DOM 内容 |

### 1.3 适用对象

- 需要定期从公开网页提取结构化数据的运营人员
- 希望用自然语言描述采集需求的产品经理
- 需要快速搭建数据管道的初级开发者

---

## 二、触发方式与场景映射

### 2.1 触发词

当对话中出现以下任一词汇时，本 Skill 自动激活：

- 爬虫采集 / 网页抓取 / 数据抽取 / 采集流程 / scrapecraft / 页面解析 / 数据管道

### 2.2 场景映射表

| 用户说（大白话） | 实际含义 | 本 Skill 响应 |
|------------------|----------|---------------|
| "帮我把这个网页上的新闻标题都抓下来" | 提取列表页中的标题字段 | 创建选择器 → 试运行 → 批量输出 |
| "每天自动跑一遍这个采集" | 定时执行流程 | 生成可调度的 Python 脚本 |
| "这个页面改版了，抓不到数据了" | 选择器失效 | 重新识别页面结构 → 更新流程 |
| "只要价格和库存，其他不要" | 限定输出字段 | 配置字段白名单 → 精简输出 |

---

## 三、标准流程

### 3.1 前置条件

| 条件 | 要求 | 检查方式 |
|------|------|----------|
| 目标 URL 可访问 | 返回 200 且非登录页 | 浏览器直接打开确认 |
| 页面结构稳定 | 关键字段的 CSS 选择器唯一 | 使用 DevTools 验证 |
| 输入文件就绪 | 待处理 URL 列表存放于 `./input/` 目录 | 文件存在且格式为 `.txt` 或 `.csv` |

### 3.2 执行步骤（分步编号）

**Step 1 — 描述需求**

用自然语言说明采集目标，例如：
> "抓取 `https://example.com/products` 页面中所有商品的名称、价格和评价数量，翻页 3 次。"

**Step 2 — 生成流程草稿**

系统将输出以下流程结构：

```
流程ID: flow_20260819_001
步骤:
  1. 打开页面: https://example.com/products
  2. 提取字段: name, price, review_count
  3. 翻页: 3 次 (CSS 选择器: .pagination .next)
  4. 输出格式: JSON
```

**Step 3 — 单样本试运行**

执行以下命令：

```bash
python scrapecraft.py --url "https://example.com/products" --fields name,price,review_count --max-pages 1
```

预期输出：

```json
{
  "status": "success",
  "data": [
    {"name": "商品A", "price": "¥199", "review_count": "234"},
    {"name": "商品B", "price": "¥299", "review_count": "89"}
  ]
}
```

**Step 4 — 校验字段**

对比源页面与输出结果，确认：
- 字段名与页面显示一致
- 价格包含货币符号（如需要，可配置去除）
- 缺失字段显示为 `[需核实:字段名]`

**Step 5 — 批量执行**

```bash
python scrapecraft.py --input ./input/urls.txt --output ./output/result.json
```

**Step 6 — 结果抽查**

随机抽取 5% 输出条目，人工核对源页面。

### 3.3 输出规范

| 输出项 | 格式 | 说明 |
|--------|------|------|
| 流程定义 | YAML | 包含步骤、选择器、翻页配置 |
| 执行日志 | `.log` | 每步耗时、成功/失败状态 |
| 数据文件 | JSON / CSV | 字段名与源页面一致 |
| 错误报告 | `.err` | 失败 URL 及原因分类 |

---

## 四、置信度门控

当以下情况发生时，系统不猜测、不编造，而是输出占位符：

| 场景 | 输出行为 |
|------|----------|
| 字段在页面中不存在 | 输出 `[需核实:字段名]` |
| 翻页选择器匹配多个元素 | 输出 `[需核实:pagination_selector]` 并暂停 |
| 页面加载超时（>10s） | 输出 `[需核实:page_load_timeout]` 并跳过 |
| 编码异常（非 UTF-8） | 输出 `[需核实:charset]` 并尝试 GBK 解码 |

**示例：**

```json
{
  "name": "商品A",
  "price": "[需核实:price]",
  "review_count": "234"
}
```

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| `E001` | URL 无法访问 | "目标地址返回非 200 状态码，请检查链接是否有效" | 1. 浏览器打开确认 2. 检查是否需登录 3. 更换 URL |
| `E002` | 选择器未匹配 | "未找到与描述匹配的页面元素，请检查页面结构" | 1. 使用 DevTools 重新定位 2. 更新选择器 3. 重试 |
| `E003` | 翻页失败 | "翻页按钮未找到或已禁用，请确认分页方式" | 1. 检查是否滚动加载 2. 调整翻页策略 3. 重试 |
| `E004` | 字段类型异常 | "提取到的数据格式与预期不符（如数字包含文本）" | 1. 配置类型转换 2. 使用正则清洗 3. 重试 |
| `E005` | 批量执行中断 | "第 N 个 URL 执行失败，流程已暂停" | 1. 查看错误日志 2. 修复对应 URL 3. 断点续跑 |

---

## 六、FAQ 反模式对照

| 常见坑 | 反模式（错误做法） | 正确做法 |
|--------|--------------------|----------|
| 页面结构变化 | 直接修改选择器后立即全量执行 | 先单样本试运行，确认无误再批量 |
| 数据量过大 | 一次性抓取所有页面导致超时 | 分批执行，每批 100 个 URL，间隔 2 秒 |
| 字段缺失 | 忽略缺失项继续执行 | 标记 `[需核实]` 并人工补录 |
| 编码问题 | 强制使用 UTF-8 解码 | 自动检测编码，失败时尝试 GBK |
| 反爬触发 | 增加请求频率试图绕过 | 降低频率，添加随机延迟 1-3 秒 |

---

## 七、渐进式披露

### 7.1 速查卡（30 秒上手）

```
1. 描述需求 → 2. 生成流程 → 3. 单样本试运行 → 4. 校验字段 → 5. 批量执行 → 6. 抽查结果
```

### 7.2 新手路径（首次使用）

- 阅读「能力边界」了解限制
- 使用「标准流程」Step 1-3 完成首个采集任务
- 遇到问题查阅「错误码体系」

### 7.3 进阶路径（熟练用户）

- 自定义选择器与翻页策略
- 配置字段清洗规则（去空格、类型转换）
- 集成定时调度（cron / 任务计划）
- 扩展输出格式（Excel / 数据库）

---

## 八、参数参考表

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `--url` | string | 无 | 目标页面 URL |
| `--fields` | string | 无 | 逗号分隔的字段名列表 |
| `--max-pages` | int | 1 | 最大翻页次数 |
| `--delay` | float | 1.0 | 请求间隔（秒） |
| `--timeout` | int | 10 | 页面加载超时（秒） |
| `--output` | string | `./output/result.json` | 输出文件路径 |
| `--input` | string | 无 | 批量 URL 列表文件 |
| `--selftest` | flag | 无 | 运行内置自检 |
| `--version` | flag | 无 | 显示版本号 |

---

## 九、用户协议

<!-- user-agreement-injected -->

**使用本 Skill 即表示您同意以下条款：**

1. **责任承担**：使用者自行承担因使用本 Skill 产生的全部责任，包括但不限于数据采集的合法性、目标网站的使用条款遵守情况。
2. **禁止反向工程**：不得对本 Skill 的代码、流程定义进行反向工程、反编译或试图提取底层算法。
3. **合规使用**：使用者应确保采集行为符合相关法律法规及目标网站的 robots.txt 规定。
4. **免责声明**：本 Skill 按"现状"提供，不附带任何明示或暗示的保证。

---

## 十、许可证（License）

<!-- professional-license-embedded -->

**MIT License**

Copyright (c) 2026 FlowForge Studio

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

*本 Skill 由 AI 辅助生成，仅供参考。使用前请阅读相关文档并自行验证适用性。*
