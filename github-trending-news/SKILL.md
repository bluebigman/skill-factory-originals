---
slug: github-trending-news
name: github_trending_reporter
displayName: 开源热点 趋势追踪 周报生成
description: 抓取GitHub Trending，按语言与日期过滤，生成结构化周报。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: trend-craft-studio
agent_created: true
trigger_words: ["github trending", "趋势周报", "开源热点", "仓库排行", "trending 报告"]
---

> 📜 **用户协议（User Agreement）**
> 1. 本 Skill 仅供学习与参考用途。使用本 Skill 产生的任何结果，由使用者自行承担全部责任；本 Skill 不提供任何明示或暗示的保证。
> 2. 涉及法律、财务、税务、投资、医疗等专业决策时，请务必咨询持证专业人士。
> 3. 本代码受版权法保护，未经授权复制、反向工程或商业利用将被追究法律责任。
<!-- user-agreement-injected -->


> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# GitHub Trending 周报生成器

## 一、能力边界：一页纸速查卡

| 维度 | 能做 | 不能做 |
|------|------|--------|
| 数据获取 | 抓取 GitHub Trending 页面公开数据 | 访问需登录的私有仓库、GitHub API 限流外的批量请求 |
| 过滤维度 | 按编程语言（如 Python、JavaScript）、时间范围（今日/本周/本月）过滤 | 按 stars 绝对数值精确排序（Trending 页面本身不提供） |
| 输出格式 | 生成 Markdown 周报、CSV 表格、JSON 结构化数据 | 生成 PDF、PPT 等二进制格式 |
| 语言支持 | 中英文双语输出 | 其他语种翻译 |
| 附加能力 | 仓库描述摘要、语言占比统计、星标增速估算 | 贡献者分析、代码质量评估、许可证合规审查 |

**适用对象**：开发者、技术团队负责人、开源爱好者、技术情报分析人员。

**不适用场景**：需要精确 star 增长曲线的量化分析、需要仓库历史数据的回溯研究。


## 许可证（License）

```text
MIT License

Copyright (c) {year} {holder}

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
