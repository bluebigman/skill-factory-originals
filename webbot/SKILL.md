---
slug: webbot
name: webbot
displayName: 网页数据采集 结构化提取 批量标注
description: 将网页或文件内容转化为结构化数据，支持批量处理与置信度标注。
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
trigger_words: ["爬虫采集", "网页抓取", "数据提取", "结构化输出", "webbot", "页面解析", "字段抽取"]
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# WebBot 网页结构化数据提取 Skill

## 一、能力边界速查卡

### 1.1 能做什么

| 能力项 | 说明 | 示例 |
|--------|------|------|
| 网页内容结构化 | 将 HTML 页面转换为 JSON 字段 | 商品标题、价格、库存 |
| 文件内容提取 | 解析 PDF、TXT、CSV 中的文本 | 合同条款、报表数字 |
| 批量处理 | 对同一目录下多个文件依次执行 | 100 个商品页批量提取 |
| 置信度标注 | 对每个字段给出可信度评分 | 价格字段置信度 0.92 |
| 字段映射校验 | 检查输出字段与源数据一致性 | 标题长度、数字格式 |

### 1.2 不能做什么

| 限制项 | 说明 |
|--------|------|
| 动态渲染页面 | 需要 JavaScript 执行后才能加载内容的页面（如 SPA 应用） |
| 登录墙内容 | 需要身份认证才能访问的页面 |
| 反爬严格站点 | 有强验证码、IP 封锁机制的网站 |
| 非文本数据 | 图片、音频、视频中的信息无法直接提取 |
| 语义理解 | 无法判断文本的隐含含义或情感倾向 |

### 1.3 适用对象

- 需要从固定模板网页中批量提取字段的数据分析师
- 需要将散落文件整理为统一格式的运营人员
- 需要快速搭建数据管道的开发者

---

## 二、触发方式与场景映射

### 2.1 触发词表

| 触发词 | 典型场景 |
|--------|----------|
| 爬虫采集 | "帮我把这个网站的商品数据爬下来" |
| 网页抓取 | "抓取这个页面的标题和正文" |
| 数据提取 | "从这份报告里提取关键指标" |
| 结构化输出 | "把这几页内容整理成表格" |
| webbot | 直接调用本 Skill 名称 |
| 页面解析 | "解析这个 HTML 文件里的链接" |
| 字段抽取 | "抽出所有价格字段" |

### 2.2 场景映射表

| 用户说 | 实际需求 | 执行动作 |
|--------|----------|----------|
| "把这个网页转成表格" | 提取表格数据 | 识别 table 标签，映射为二维数组 |
| "批量处理这些文件" | 多文件统一提取 | 遍历目录，逐文件执行提取流程 |
| "这个字段不太确定" | 需要置信度评估 | 输出时附加 confidence 字段 |
| "结果对不上" | 校验失败 | 执行字段比对，输出差异报告 |

---

## 三、标准执行流程

### 3.1 前置条件

| 条件 | 要求 | 检查方式 |
|------|------|----------|
| 输入文件 | 位于当前工作目录 | `ls` 确认文件存在 |
| 命名规范 | 文件名含统一前缀或序号 | 如 `product_001.html` |
| 依赖库 | Python 3.8+，requests, beautifulsoup4 | `pip list` 检查 |
| 网络权限 | 目标站点可访问 | `curl -I <url>` 测试 |

### 3.2 执行步骤

**Step 1：输入准备**

将待处理文件放入同一目录，确认命名规范一致。例如：

```
./input/
  product_001.html
  product_002.html
  product_003.html
```

**Step 2：单样本试运行**

选取第一个文件执行提取：

```bash
python webbot.py --input input/product_001.html --output output/product_001.json
```

检查输出 JSON 的字段名、类型、格式是否符合预期。

**Step 3：批量执行**

确认无误后，对全量数据执行：

```bash
python webbot.py --input input/ --output output/ --batch
```

执行前自动备份原始文件至 `backup/` 目录。

**Step 4：结果校验**

抽查输出条目，核对关键字段与源数据一致：

```bash
python webbot.py --verify output/product_001.json --source input/product_001.html
```

校验项包括：字段存在性、类型匹配、数值范围、文本长度。

### 3.3 输出规范

输出 JSON 格式：

```json
{
  "source": "input/product_001.html",
  "extracted_at": "2025-01-15T10:30:00Z",
  "fields": {
    "title": {
      "value": "无线蓝牙耳机",
      "confidence": 0.98
    },
    "price": {
      "value": 199.00,
      "confidence": 0.95
    }
  },
  "warnings": []
}
```

字段命名规则：小写蛇形命名（snake_case），数值字段使用浮点数，文本字段使用字符串。

---

## 四、置信度门控机制

### 4.1 置信度评分标准

| 置信度区间 | 含义 | 处理方式 |
|------------|------|----------|
| 0.90 - 1.00 | 高置信，字段与源数据完全匹配 | 正常输出 |
| 0.70 - 0.89 | 中置信，存在部分不确定性 | 输出并附加提示 |
| 0.50 - 0.69 | 低置信，字段可能不准确 | 输出并标记 `[需核实:字段名]` |
| < 0.50 | 无法确定 | 不输出该字段，记录 warning |

### 4.2 信息不足时的处理

当遇到以下情况，输出 `[需核实:字段名]` 占位符，不编造数据：

- 页面元素缺失（如价格标签不存在）
- 元素存在但内容为空
- 内容格式异常（如价格包含非数字字符）
- 多个候选值无法唯一确定

示例：

```json
{
  "fields": {
    "price": {
      "value": "[需核实:price]",
      "confidence": 0.45,
      "reason": "页面存在两个价格标签，无法确定主价格"
    }
  }
}
```

---

## 五、错误码体系

### 5.1 错误码对照表

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| E001 | 文件不存在 | "未找到指定文件，请检查路径" | 确认文件路径，使用 `ls` 查看目录 |
| E002 | 文件格式不支持 | "仅支持 .html, .txt, .csv, .pdf 格式" | 转换文件格式后重试 |
| E003 | 网络请求失败 | "无法访问目标 URL，请检查网络" | 测试网络连接，确认 URL 可访问 |
| E004 | 页面结构异常 | "页面缺少预期的 HTML 结构" | 检查页面是否被反爬拦截 |
| E005 | 字段提取失败 | "无法从页面中提取指定字段" | 调整字段选择器，或检查页面模板 |
| E006 | 批量处理中断 | "批量处理在第 N 个文件处中断" | 查看日志，修复问题后从断点继续 |
| E007 | 输出目录不可写 | "无法写入输出目录，请检查权限" | 修改目录权限或更换输出路径 |

### 5.2 错误处理流程

1. 捕获错误码
2. 输出提示话术
3. 记录错误日志至 `logs/error.log`
4. 根据修正步骤处理
5. 重试执行

---

## 六、FAQ 与反模式对照

### 6.1 常见坑

| 坑点 | 反模式 | 正确做法 |
|------|--------|----------|
| 忽略试运行 | 直接批量执行，结果全部错误 | 先单样本验证，再批量执行 |
| 不备份原始文件 | 处理失败后原始数据丢失 | 执行前自动备份至 `backup/` |
| 忽略置信度 | 低置信字段直接使用 | 对置信度 < 0.7 的字段人工复核 |
| 硬编码选择器 | 页面改版后提取全部失败 | 使用可配置的 CSS 选择器 |
| 不校验结果 | 输出错误数据而不自知 | 执行 `--verify` 校验关键字段 |

### 6.2 反模式对照表

| 反模式 | 问题 | 替代方案 |
|--------|------|----------|
| 用正则解析 HTML | 脆弱且易出错 | 使用 BeautifulSoup 等解析库 |
| 忽略异常处理 | 单个文件错误导致全部中断 | 捕获异常，记录日志，继续处理 |
| 输出无结构文本 | 后续处理困难 | 输出标准 JSON 格式 |
| 不记录处理日志 | 出错后无法排查 | 记录每步操作的日志 |

---

## 七、渐进式披露

### 7.1 速查卡（30 秒上手）

```
1. 放文件到 input/ 目录
2. 运行: python webbot.py --input input/ --output output/ --batch
3. 检查 output/ 下的 JSON 文件
4. 校验: python webbot.py --verify output/xxx.json --source input/xxx.html
```

### 7.2 新手路径（首次使用）

1. 阅读「能力边界速查卡」了解适用范围
2. 准备 1-2 个测试文件
3. 按「标准执行流程」Step 1-2 执行单样本
4. 确认输出格式后，再执行批量
5. 遇到问题查「错误码体系」

### 7.3 进阶路径（深度使用）

1. 自定义字段选择器：编辑 `config/selectors.json`
2. 扩展支持的文件格式：添加解析器至 `parsers/` 目录
3. 调整置信度阈值：修改 `config/thresholds.json`
4. 集成到自动化管道：调用 `webbot.py` 作为子进程

---

## 八、参数配置参考

### 8.1 命令行参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `--input` | string | 必填 | 输入文件或目录路径 |
| `--output` | string | `./output/` | 输出目录路径 |
| `--batch` | flag | false | 批量处理模式 |
| `--verify` | flag | false | 校验模式 |
| `--config` | string | `./config/` | 配置文件目录 |
| `--selftest` | flag | false | 运行自检 |
| `--version` | flag | false | 显示版本号 |

### 8.2 配置文件示例

`config/selectors.json`：

```json
{
  "product_page": {
    "title": "h1.product-title",
    "price": "span.price",
    "description": "div.product-desc"
  }
}
```

---

## 九、用户协议

使用本 Skill 即表示您同意以下条款：

1. **责任承担**：使用者自行承担因使用本 Skill 产生的全部责任，包括但不限于数据准确性、合规性、法律风险。
2. **禁止反向工程**：不得对本 Skill 进行反向工程、反编译、破解或试图获取源代码。
3. **合规使用**：使用者需确保使用场景符合相关法律法规，不得用于非法数据采集。
4. **免责声明**：本 Skill 按"原样"提供，不提供任何明示或暗示的保证。

<!-- user-agreement-injected -->

---

## 十、许可证（License）

MIT License

Copyright (c) 2025 数据工坊

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

*本 Skill 由 AI 辅助生成，仅供参考。使用前请阅读相关文档。*
