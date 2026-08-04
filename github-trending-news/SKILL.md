---
slug: github-trending-news
name: github_trending_reporter
displayName: GitHub热榜 周报生成器
description: 抓取GitHub Trending，按语言与日期过滤，生成结构化周报。
version: 1.2.5
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/github-trending-news
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: DevRelLab
agent_created: true
trigger_words:
  - "github-trending-reporter"
  - "GitHub热榜周报"
  - "trending项目整理"
  - "本周热门仓库"
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# GitHub Trending 周报生成器（v1.0.0）

## 一、能力边界（速查卡）

| 维度 | 能做 | 不能做 |
|------|------|--------|
| 数据源 | GitHub Trending 公开页面 | GitHub API 私有仓库、企业内网 |
| 时间范围 | 最近 7 天（自然周） | 自定义任意历史日期段 |
| 语言筛选 | 单语言（如 Python、JavaScript） | 多语言叠加（如 "Python+Go" 同时筛选） |
| 输出格式 | Markdown 表格 + 摘要段落 | PDF/HTML 文件导出 |
| 星标数据 | 相对变化（较上周增量） | 绝对总数（需调用 API 补充） |
| 并发处理 | 单任务顺序抓取 | 多任务并行批量生成 |

**适用对象**：技术团队负责人、技术选型调研者、开源社区运营人员、个人开发者。

---

## 二、触发方式与场景映射

| 触发词（或同义表达） | 对应场景 |
|----------------------|----------|
| "github-trending-reporter" | 直接调用本 Skill 的完整命令 |
| "看下这周 GitHub 上有什么火的" | 生成默认周报（全语言、本周） |
| "整理 Python 最近一周的热门项目" | 按语言筛选，输出 Python 周报 |
| "上周的 trending 报告给我一份" | 指定日期范围（上周一至上周日） |

**输入参数表**（全部可选，缺省时使用默认值）：

| 参数名 | 类型 | 默认值 | 示例 |
|--------|------|--------|------|
| language | string | 空（全部） | "Python" |
| since | string（YYYY-MM-DD） | 本周一 | "2025-03-10" |
| until | string（YYYY-MM-DD） | 本周日 | "2025-03-16" |
| limit | int | 10 | 5（只取前5个） |

---

## 三、标准流程

### 前置条件
- 网络可访问 `github.com/trending`
- 用户提供至少一个有效触发词或参数

### 执行步骤

1. **解析输入**：提取 language、since、until、limit 参数。若缺失，使用默认值。
   - 日期校验：since 必须早于 until，且跨度不超过 7 天。若超限，取最近 7 天。

2. **抓取数据**：访问 `https://github.com/trending/{language}?since=weekly`。
   - 若指定日期范围，则依次抓取每日页面（since=daily）并合并去重。
   - 抓取字段：仓库名、描述、编程语言、本周星标增量、贡献者数（若可获取）。

3. **结构化整理**：按星标增量降序排列，截取 limit 条记录。

4. **生成报告**：输出 Markdown 格式，包含：
   - 报告标题（含时间范围与语言筛选）
   - 汇总表（仓库名 / 描述 / 语言 / 本周星标增量）
   - 简短趋势摘要（最多 3 条，基于增量最大的项目特征）

5. **返回结果**：将完整 Markdown 文本返回给调用方。

### 输出规范示例

```markdown
# GitHub Trending 周报（2025-03-10 至 2025-03-16，语言：Python）

| 排名 | 仓库 | 描述 | 语言 | 本周星标增量 |
|------|------|------|------|--------------|
| 1 | owner/repo | 一个快速的异步框架 | Python | +2,345 |
| 2 | user/tool | CLI 工具，简化部署流程 | Python | +1,890 |

**趋势摘要**：
- 异步框架类项目本周增量明显，可能与近期技术博客推广相关。
- 部署工具持续走热，建议关注 CI/CD 集成方向。
```

---

## 四、置信度门控

遇到以下情况，**不得编造数据**，使用占位符 `[需核实:字段名]`：

| 场景 | 处理方式 |
|------|----------|
| 描述信息缺失 | 输出 `[需核实:描述]` |
| 星标增量无法获取 | 输出 `[需核实:星标增量]` |
| 日期范围无数据（如节假日） | 输出 `[需核实:该日期范围无Trending数据]` |
| 语言参数拼写错误 | 不猜测，返回提示语（见错误码） |

---

## 五、错误码体系

| 错误码 | 触发条件 | 提示话术 | 修正步骤 |
|--------|----------|----------|----------|
| ERR-001 | 参数格式错误（如日期为 "abc"） | "日期参数需为 YYYY-MM-DD 格式" | 重新输入日期，或省略该参数使用默认值 |
| ERR-002 | 语言参数无效（非 GitHub 支持语言） | "未找到该语言，请检查拼写（如 Python 而非 python）" | 参考 [GitHub 语言列表](https://github.com/trending) 重新输入 |
| ERR-003 | 网络访问失败 | "无法连接 GitHub，请检查网络或稍后重试" | 确认网络通畅后重试；若持续失败，报告系统状态 |
| ERR-004 | 日期跨度超过 7 天 | "仅支持单周数据，请缩小日期范围" | 调整 since/until 使跨度 ≤ 7 天 |
| ERR-005 | 抓取结果为空 | "该筛选条件下无数据，请调整语言或日期" | 尝试更换语言或扩大日期范围 |

---

## 六、FAQ 与反模式

| 常见坑 | 反模式（错误做法） | 正确模式 |
|--------|-------------------|----------|
| 误以为能获取历史任意日期 | 直接请求 2024 年数据 | 明确告知仅支持最近 7 天，或使用 GitHub Archive 等其他工具 |
| 多语言叠加筛选 | 输入 "Python+Go" 试图混合筛选 | 分两次调用，分别生成单语言报告 |
| 忽略描述缺失 | 自行补写描述 | 使用 `[需核实:描述]` 占位，避免虚构 |
| 星标增量解读错误 | 将增量当作绝对星标数 | 报告明确标注"增量"，如需总数需另行调用 API |
| 输出过长 | 一次性返回 50 个项目 | 默认 limit=10，用户可显式指定更大值 |

---

## 七、渐进式披露（阅读路径）

### 速查卡（10 秒上手）
- 输入：`github-trending-reporter` + 可选语言/日期
- 输出：Markdown 周报表格
- 缺省行为：本周全语言 Top10

### 新手路径（5 分钟）
1. 阅读 [能力边界](#一能力边界速查卡) 了解限制。
2. 使用默认参数生成第一份周报。
3. 按 [FAQ](#六faq-与反模式) 排查常见问题。

### 进阶路径（深入使用）
1. 掌握 [参数表](#二触发方式与场景映射) 的完整用法，尝试用 since/until 指定精确日期。
2. 阅读 [置信度门控](#四置信度门控)，理解数据真实性的边界。
3. 结合 [错误码体系](#五错误码体系)，在自动化流程中处理异常情况。
4. 如需绝对星标数、贡献者画像等深度数据，建议结合 GitHub REST API 扩展本 Skill。

---

*本 Skill 提供的是数据整理与呈现能力，不包含数据源本身的准确性保证。使用前请确认目标仓库的公开信息。*

## 许可证（License）

```text
MIT License

Copyright (c) 2026 SkillForge Lab

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.
```
<!-- professional-license-embedded -->
