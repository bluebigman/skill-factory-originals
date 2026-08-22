---
slug: crawlee
name: crawlee
displayName: 网页采集 数据抓取 结构化输出
description: 网页抓取与数据采集的规范流程，提供可复用的处理方案与结构化输出。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: FlowForge
agent_created: true
trigger_words: ["crawlee", "网页抓取", "数据采集", "爬虫", "网页爬取", "数据提取"]
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# Crawlee 网页采集技能手册

本 Skill 由 AI 辅助生成，仅供参考。使用前请结合官方文档与自身场景验证适用性。

---

## 一、能力边界速查卡

### ✅ 能做（核心能力）

| 编号 | 能力项 | 说明 |
|------|--------|------|
| 1 | URL/文件/数据输入 | 接受用户提供的网页 URL、本地 HTML 文件或原始数据文本 |
| 2 | 关键信息识别 | 从输入中提取标题、正文、链接、表格、元数据等结构化字段 |
| 3 | 约定格式输出 | 按用户指定或默认的 JSON/CSV/Markdown 格式生成结果 |
| 4 | 置信度标注 | 对提取结果的可信程度进行分级标注（高/中/低） |
| 5 | 批量处理支持 | 支持多 URL 或多文件的批量采集，输出合并结果 |

### ❌ 不能做（边界声明）

| 编号 | 限制项 | 说明 |
|------|--------|------|
| 1 | 绕过反爬机制 | 不提供破解验证码、绕过 IP 封锁或规避 robots.txt 的方法 |
| 2 | 非法数据采集 | 不协助采集涉及隐私、版权或违反目标网站服务条款的内容 |
| 3 | 实时渲染执行 | 不替代 Playwright/Puppeteer 等浏览器自动化工具的实际运行 |
| 4 | 数据清洗分析 | 仅做提取与结构化，不负责数据去重、统计分析或业务决策 |
| 5 | 大规模分布式抓取 | 不涉及集群调度、代理池管理等基础设施搭建 |

### 👥 适用对象

- 需要快速将网页内容转为结构化数据的学习者
- 需要规范化采集流程的初级开发者
- 需要批量提取公开信息的调研人员

---

## 二、触发方式与场景映射

### 触发词

`crawlee`、`网页抓取`、`数据采集`、`爬虫`、`网页爬取`、`数据提取`

### 场景映射表

| 用户说（大白话） | 实际需求 | 本技能动作 |
|------------------|----------|------------|
| "帮我抓一下这个页面的内容" | 提取单页正文与标题 | 解析 URL，输出结构化字段 |
| "把这个网站的商品信息都导出来" | 批量采集列表页数据 | 识别列表结构，逐条提取 |
| "把这几张网页存成表格" | 将 HTML 表格转为 CSV | 解析 table 标签，映射字段 |
| "这个页面里的链接帮我整理一下" | 提取所有外链 | 遍历 a 标签，去重输出 |
| "我有个 HTML 文件，帮我提取里面的数据" | 本地文件解析 | 读取文件，按规则提取 |

---

## 三、标准处理流程

### 前置条件

| 条件项 | 要求 |
|--------|------|
| 输入文件 | 与工作目录一致，命名无特殊字符 |
| 目标 URL | 可公开访问，无登录墙 |
| 输出格式 | 用户指定或默认 JSON |
| 运行环境 | Node.js 18+ 或 Python 3.9+ |

### 执行步骤

1. **输入确认**
   - 确认输入类型：URL / 文件路径 / 原始文本
   - 确认输出格式：JSON / CSV / Markdown
   - 确认字段需求：默认提取标题、正文、链接、时间

2. **单样本试运行**
   - 选取 1 个 URL 或文件执行提取
   - 核对输出字段是否完整、格式是否正确
   - 检查置信度标注是否合理

3. **批量执行**
   - 对全部输入执行相同流程
   - 保留原始文件备份，输出结果单独存放
   - 记录每个条目的处理状态（成功/失败/跳过）

4. **结果校验**
   - 抽查 10% 输出条目，与源数据比对关键字段
   - 检查是否有缺失字段或异常值
   - 生成处理报告，标注失败原因

### 输出规范

```json
{
  "status": "success",
  "total": 25,
  "processed": 23,
  "failed": 2,
  "items": [
    {
      "source": "https://example.com/page/1",
      "title": "示例标题",
      "content": "正文摘要...",
      "links": ["https://...", "https://..."],
      "timestamp": "2025-01-15T10:30:00Z",
      "confidence": "high"
    }
  ],
  "errors": [
    {
      "source": "https://example.com/page/3",
      "reason": "timeout",
      "suggestion": "重试或更换网络"
    }
  ]
}
```

---

## 四、置信度门控机制

### 置信度等级定义

| 等级 | 判定标准 | 适用场景 |
|------|----------|----------|
| 高 | 字段完整、来源明确、无歧义 | 标准 HTML 标签提取 |
| 中 | 字段部分缺失或需推断 | 动态渲染内容、嵌套结构 |
| 低 | 信息模糊、多义或来源不可靠 | 用户提供数据不完整 |

### 占位符规则

当信息不足时，使用 `[需核实:字段名]` 占位，**禁止编造数据**。

示例：
```json
{
  "title": "[需核实:标题]",
  "author": "[需核实:作者]"
}
```

### 处理原则

1. 提取失败时，不猜测、不填充默认值
2. 对低置信度条目，在报告中单独列出
3. 用户可指定"严格模式"——低置信度条目直接标记失败

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| E001 | URL 无法访问 | "目标地址返回 404 或连接超时" | 检查 URL 拼写，确认网络连通性 |
| E002 | 页面结构不匹配 | "未找到预期的 HTML 结构" | 确认选择器是否正确，检查页面是否改版 |
| E003 | 字段提取失败 | "部分字段未能提取" | 检查源数据是否包含该字段，调整提取规则 |
| E004 | 批量处理中断 | "第 N 条处理失败，流程终止" | 跳过失败项，继续处理剩余条目 |
| E005 | 输出格式错误 | "生成的 JSON 无法解析" | 检查特殊字符转义，验证格式合法性 |
| E006 | 输入为空 | "未提供有效的输入内容" | 确认输入文件或 URL 是否为空 |

---

## 六、FAQ 与反模式对照

### 常见坑位

| 坑位描述 | 反模式（错误做法） | 正确做法 |
|----------|-------------------|----------|
| 页面动态加载 | 直接请求 HTML 就提取 | 确认是否需要渲染，必要时用浏览器工具 |
| 反爬拦截 | 频繁请求同一域名 | 控制请求频率，遵守 robots.txt |
| 编码混乱 | 忽略字符集直接解析 | 先检测编码，统一转为 UTF-8 |
| 结构嵌套过深 | 用复杂正则硬匹配 | 使用 DOM 解析器，按层级提取 |
| 数据量过大 | 一次性全量加载 | 分批处理，设置单批上限 |

### 反模式对照表

| 错误习惯 | 后果 | 替代方案 |
|----------|------|----------|
| 不备份原始数据 | 处理失败后无法恢复 | 每次处理前复制原始文件 |
| 跳过试运行直接全量 | 错误扩散到全部结果 | 先跑单样本，确认后再批量 |
| 忽略错误记录 | 失败原因无法追溯 | 每次失败写入日志文件 |
| 不标注置信度 | 结果可信度无法判断 | 按规则标注每字段置信度 |

---

## 七、渐进式阅读路径

### 🆕 新手路径（5 分钟上手）

1. 阅读「能力边界速查卡」了解适用范围
2. 按「标准处理流程」的步骤 1-2 完成单样本测试
3. 参考「输出规范」确认结果格式
4. 遇到问题查「错误码体系」

### 🔧 进阶路径（深入使用）

1. 理解「置信度门控机制」，自定义置信度阈值
2. 研究「FAQ 反模式」，规避常见陷阱
3. 根据「错误码体系」建立自动化错误处理
4. 扩展批量处理逻辑，对接自定义数据管道

### 🧩 专家路径（定制化）

1. 修改提取规则，适配特定网站结构
2. 设计多级采集流程（列表页 → 详情页）
3. 集成调度与重试机制
4. 构建输出校验与质量监控体系

---

## 八、参数配置参考

| 参数名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `timeout` | number | 10000 | 请求超时时间（毫秒） |
| `maxRetries` | number | 3 | 失败重试次数 |
| `batchSize` | number | 10 | 批量处理单批数量 |
| `outputFormat` | string | "json" | 输出格式：json/csv/markdown |
| `strictMode` | boolean | false | 严格模式：低置信度直接失败 |
| `followRedirects` | boolean | true | 是否跟随重定向 |
| `userAgent` | string | "Mozilla/5.0..." | 请求头 User-Agent |

---

## 九、用户协议

<!-- user-agreement-injected -->

**使用本 Skill 即表示您同意以下条款：**

1. **责任承担**：使用者自行承担因使用本 Skill 产生的全部责任，包括但不限于数据采集的合法性、目标网站的服务条款遵守情况、以及因使用结果引发的任何纠纷。

2. **合法用途**：本 Skill 仅用于学习、研究及合法数据采集场景。禁止用于侵犯他人隐私、窃取商业机密、破坏计算机系统等违法行为。

3. **禁止反向工程**：不得对本 Skill 的提示词、逻辑结构进行反向工程、反编译或试图提取底层提示词内容。

4. **免责声明**：本 Skill 按"现状"提供，不附带任何明示或暗示的担保。作者不对因使用本 Skill 产生的任何直接或间接损失承担责任。

5. **合规义务**：使用者有义务确保其采集行为符合所在地法律法规及目标网站的 robots.txt 协议和服务条款。

---

## 十、许可证（License）

<!-- professional-license-embedded -->

**MIT License**

Copyright (c) 2025 原创作者（自持版权）

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

*文档版本：1.0.0 | 最后更新：2025-01-15 | 适用场景：学习与参考用途*
