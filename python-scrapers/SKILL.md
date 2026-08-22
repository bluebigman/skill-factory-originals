---
slug: python-scrapers
name: python-scrapers
displayName: 网页数据采集 表格化整理 批量映射
description: 将网页、文件或原始数据转化为结构化表格，支持批量处理与自定义字段映射。
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
trigger_words: ["爬虫采集", "数据抓取", "网页解析", "结构化提取", "批量采集", "表格化", "字段映射"]
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# SKILL.md — python-scrapers

## 一、能力边界（一页纸速查卡）

### 1.1 能做什么

| 能力项 | 说明 | 典型场景 |
|--------|------|----------|
| 网页内容提取 | 从 HTML 页面中抽取文本、链接、表格、图片地址 | 新闻列表、商品信息、公告通知 |
| 文件内容解析 | 读取 CSV、JSON、TXT、Markdown 等文本类文件 | 日志整理、配置汇总、报告合并 |
| 原始数据清洗 | 对非结构化文本做去噪、去重、字段切分 | 聊天记录、邮件正文、评论数据 |
| 自定义字段映射 | 用户指定源字段与目标字段的对应关系 | 将"日期"映射为"发布时间" |
| 批量处理 | 对同一目录下多个文件或 URL 列表依次执行 | 周报汇总、多页面采集 |
| 输出结构化表格 | 统一输出为 CSV 或 Markdown 表格 | 交付给下游分析工具 |

### 1.2 不能做什么

| 限制项 | 说明 |
|--------|------|
| 不处理登录态 | 需要登录的页面需用户自行提供已认证的 Cookie 或 token |
| 不执行 JavaScript 渲染 | 仅解析静态 HTML，动态渲染页面需用户预取渲染后内容 |
| 不处理二进制文件 | PDF、图片、音频等非文本格式不在处理范围内 |
| 不保证数据完整性 | 源页面结构变化可能导致字段缺失，需人工校验 |
| 不提供反爬策略 | 不包含代理池、验证码识别、请求频率控制等功能 |

### 1.3 适用对象

- 需要将零散网页信息整理为表格的运营人员
- 需要批量提取文件关键字段的数据分析初学者
- 需要快速搭建数据管道原型的开发者

---

## 二、触发方式

### 2.1 触发词

当用户输入包含以下任一词汇时，本 Skill 被激活：

- 爬虫采集
- 数据抓取
- 网页解析
- 结构化提取
- 批量采集
- 表格化
- 字段映射

### 2.2 场景映射表

| 用户说（大白话） | 对应能力 | 触发词 |
|------------------|----------|--------|
| "帮我把这个网页上的商品价格都列出来" | 网页内容提取 + 表格化 | 网页解析、表格化 |
| "我有 100 个 JSON 文件，想合并成一个表" | 批量处理 + 字段映射 | 批量采集、字段映射 |
| "这段文本里有很多日期和金额，帮我整理一下" | 原始数据清洗 | 结构化提取 |
| "这个目录下所有 CSV 的列名不一样，统一一下" | 自定义字段映射 + 批量处理 | 批量采集、字段映射 |

---

## 三、标准流程

### 3.1 前置条件

| 条件 | 要求 | 检查方式 |
|------|------|----------|
| 输入文件 | 所有待处理文件置于同一目录，命名不含空格和特殊字符 | `ls -la` 查看 |
| 命名规范 | 文件名前缀一致（如 `raw_001.csv`、`raw_002.csv`） | 肉眼检查 |
| 字段说明 | 用户需提供目标字段清单（至少 1 个） | 对话确认 |
| 环境依赖 | Python 3.8+，已安装 `pandas`、`beautifulsoup4` | `pip list` 查看 |

### 3.2 执行步骤

1. **确认输入**：列出目录下所有文件，与用户核对范围。
2. **定义字段映射**：与用户确认源字段到目标字段的对应关系，形成映射表。
3. **单样本试运行**：选取第一个文件执行，输出结果供用户核对。
4. **核对输出**：检查字段名、数据类型、缺失值情况。
5. **批量执行**：确认无误后，对剩余文件依次执行。
6. **输出汇总**：将所有结果合并为一个表格文件，保存至 `output/` 目录。
7. **备份原文件**：将原始文件复制至 `backup/` 目录，不做任何修改。

### 3.3 输出规范

| 项目 | 规范 |
|------|------|
| 输出格式 | CSV（UTF-8 编码，含 BOM）或 Markdown 表格 |
| 文件命名 | `output_YYYYMMDD_HHMMSS.csv` |
| 字段顺序 | 按用户提供的目标字段清单顺序排列 |
| 缺失值 | 空单元格，不填充默认值 |
| 编码声明 | 文件首行注明 `# encoding: utf-8`（仅 CSV 注释行） |

---

## 四、置信度门控

### 4.1 占位符规则

当遇到以下情况时，使用 `[需核实:字段名]` 占位，不编造数据：

| 情况 | 处理方式 |
|------|----------|
| 源数据中字段不存在 | 输出 `[需核实:字段名]` |
| 字段值格式异常（如日期格式混乱） | 输出 `[需核实:字段名]` |
| 批量处理中某文件解析失败 | 该文件所有字段输出 `[需核实:全字段]` |
| 用户未明确字段映射关系 | 停止执行，先询问用户 |

### 4.2 示例

```csv
id,title,publish_date,price
001,示例商品,[需核实:publish_date],19.99
002,另一商品,2024-01-15,[需核实:price]
```

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| `E001` | 目录不存在或为空 | "未找到可处理的文件，请检查目录路径" | 确认路径，创建目录或移动文件 |
| `E002` | 文件格式不支持 | "文件格式不在支持范围内（CSV/JSON/TXT/MD）" | 转换格式或移除该文件 |
| `E003` | 字段映射冲突 | "目标字段与源字段数量不匹配" | 重新核对映射表 |
| `E004` | 解析超时（单文件 > 30 秒） | "该文件解析超时，已跳过" | 检查文件大小，拆分处理 |
| `E005` | 输出目录无写入权限 | "无法写入输出目录，请检查权限" | 修改目录权限或更换路径 |
| `E006` | 批量处理中断 | "批量处理在第 N 个文件处中断" | 查看日志，修复后从第 N+1 个继续 |

---

## 六、FAQ 反模式

### 6.1 常见坑

| 坑 | 反模式示例 | 正确做法 |
|----|------------|----------|
| 忽略页面结构变化 | 直接按固定 CSS 选择器提取，页面改版后全部失败 | 提取前先检查页面结构，使用多级回退选择器 |
| 不校验编码 | 直接按 UTF-8 读取，遇到 GBK 文件乱码 | 先检测文件编码，再决定解码方式 |
| 字段映射过于宽松 | 源字段名相似就自动映射，导致数据错位 | 严格按用户确认的映射表执行，不猜测 |
| 批量处理无断点 | 中途失败后从头开始，浪费时间 | 记录处理进度，支持断点续跑 |
| 输出无校验 | 直接交付，用户发现数据缺失 | 输出后自动生成校验报告，标注缺失率 |

### 6.2 反模式对照表

| 反模式 | 问题 | 替代方案 |
|--------|------|----------|
| "我猜这个字段应该是日期" | 编造数据 | 输出 `[需核实:字段名]` |
| "这个页面结构不会变" | 假设静态 | 每次执行前做结构探测 |
| "所有文件格式都一样" | 忽略差异 | 逐文件检查格式，分类处理 |
| "先跑完再说" | 无校验 | 先跑单样本，确认后再批量 |

---

## 七、渐进式披露

### 7.1 速查卡（新手路径）

1. 把所有文件放到一个文件夹。
2. 告诉我要提取哪些字段。
3. 我先跑一个文件给你看结果。
4. 确认没问题，我再跑全部。
5. 结果在 `output/` 文件夹里。

### 7.2 进阶路径（有经验用户）

- **自定义选择器**：可提供 CSS 选择器或 XPath 表达式，精确指定提取位置。
- **字段转换规则**：支持对提取值做正则替换、日期格式化、单位换算。
- **多级映射**：支持嵌套 JSON 的路径映射，如 `data.items[0].name`。
- **增量采集**：支持基于时间戳或 ID 的增量更新，避免重复处理。

### 7.3 参数速查表

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `--input-dir` | string | `./input` | 输入目录路径 |
| `--output-dir` | string | `./output` | 输出目录路径 |
| `--format` | string | `csv` | 输出格式：`csv` 或 `markdown` |
| `--mapping` | json | 无 | 字段映射关系，如 `{"源字段":"目标字段"}` |
| `--selftest` | flag | 无 | 运行自检，验证环境依赖 |
| `--version` | flag | 无 | 显示版本号 |

---

## 八、自检命令

```bash
# 检查环境依赖是否齐全
python -m python_scrapers --selftest

# 查看版本
python -m python_scrapers --version
```

自检输出示例：

```
[OK] Python 3.10.12
[OK] pandas 2.1.4
[OK] beautifulsoup4 4.12.3
[OK] 所有依赖已就绪
```

---

## 用户协议

<!-- user-agreement-injected -->

使用本 Skill 即表示您同意以下条款：

1. **责任承担**：使用者自行承担因使用本 Skill 产生的全部责任，包括但不限于数据准确性、合规性、法律风险等。
2. **禁止反向工程**：不得对本 Skill 的代码、逻辑、文档进行反向工程、反编译、破解或试图提取底层算法。
3. **数据合规**：使用者需确保采集和处理的数据符合当地法律法规及目标网站的 robots 协议和服务条款。
4. **无担保**：本 Skill 按"原样"提供，不附带任何明示或暗示的担保。
5. **免责**：因使用本 Skill 导致的任何直接或间接损失，作者不承担任何责任。

---

## 许可证（License）

<!-- professional-license-embedded -->

MIT License

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
