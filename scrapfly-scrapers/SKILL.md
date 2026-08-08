---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: scrapfly-scrapers
name: scrapfly-scrapers
displayName: 网页采集 数据抽取 结构化输出
description: 面向40+主流网站的Python爬虫脚本，将网页数据转为结构化结果。
version: 1.0.2
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/scrapfly-scrapers
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: DataForge Studio
agent_created: true
trigger_words: ["爬虫采集", "网页抓取", "数据抽取", "scraping", "crawler", "数据采集", "页面解析", "--selftest", "--version"]

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->
---

> 📜 **用户协议（User Agreement）**
> 1. 本 Skill 仅供学习与参考用途。使用本 Skill 产生的任何结果，由使用者自行承担全部责任；本 Skill 不提供任何明示或暗示的保证。
> 2. 涉及法律、财务、税务、投资、医疗等专业决策时，请务必咨询持证专业人士。
> 3. 本代码受版权法保护，未经授权复制、反向工程或商业利用将被追究法律责任。
<!-- user-agreement-injected -->


> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->

# scrapfly-scrapers — 网页数据采集与结构化输出 Skill

## 一、能力边界（一页纸速查卡）

### 1.1 能做什么

| 能力项 | 说明 | 覆盖范围 |
|--------|------|----------|
| 目标站点采集 | 针对 40+ 主流网站（电商、新闻、社交、招聘、房产等）编写专用爬虫脚本 | 每个站点对应一个独立脚本模块 |
| 数据抽取 | 从 HTML 页面中提取标题、价格、评论、日期、作者、链接等字段 | 支持 CSS 选择器与 XPath 两种定位方式 |
| 结构化输出 | 将抽取结果统一转换为 JSON 格式，字段名与类型保持一致 | 输出 schema 固定，便于下游直接消费 |
| 批量采集 | 支持列表页翻页、详情页遍历、关键词搜索采集 | 内置限速与重试机制 |
| 反爬应对 | 内置 User-Agent 轮换、请求间隔控制、Cookie 保持 | 仅限合法合规站点，不绕过登录鉴权 |

### 1.2 不能做什么

| 限制项 | 说明 |
|--------|------|
| 不处理登录墙 | 需要账号密码的站点不在覆盖范围内 |
| 不绕过验证码 | 遇到验证码直接返回错误码 `CAPTCHA_DETECTED`，不做破解 |
| 不采集动态渲染页面 | 仅针对服务端渲染的 HTML；SPA 站点需配合无头浏览器（不在本 Skill 范围内） |
| 不提供分布式调度 | 单机串行/并发模式，不包含任务队列与集群管理 |
| 不保证字段完整率 | 目标站点改版或字段缺失时，输出中对应字段为 `null` 或 `[需核实:字段名]` |

### 1.3 适用对象

- 需要定期从公开网站获取结构化数据的开发者
- 做市场调研、竞品分析、舆情监控的数据工程师
- 需要快速搭建采集原型（PoC）的团队


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

## 前置条件

- Python 3.9+（脚本依赖标准库，无需联网即可运行自检）
- 已获取待处理的输入文件，并对其拥有合法使用权
- 建议先在样本数据上试运行，确认输出符合预期后再批量处理

## 执行步骤

1. **准备输入**：将待处理文件放入同一目录，确认命名规范一致。
2. **试运行**：先用单个样本执行，核对输出字段与格式。
3. **批量执行**：确认无误后对全量数据执行，并保留原始文件备份。
4. **校验结果**：抽查输出条目，核对关键字段与源数据一致。

## 输出

- 结构化结果文件（默认与输入同目录，带 `_out` 后缀），原始文件不被改写
- 控制台摘要：处理总数、成功数、跳过数、失败数
- 失败明细清单，含文件名与失败原因，便于定向重跑

## 异常处理

| 异常情况 | 表现 | 处理方式 |
|---|---|---|
| 输入文件不存在 | 提示路径错误并退出 | 核对路径，使用绝对路径重试 |
| 文件格式不符 | 该条跳过并计入失败明细 | 转换为受支持格式后重跑该条 |
| 权限不足 | 写入失败 | 更换输出目录或提升目录写权限 |
| 单条数据异常 | 跳过该条，继续处理其余 | 处理结束后查看失败明细定向重跑 |

失败处理原则：**单条失败不中断整批**，全部异常汇总到失败明细，支持只重跑失败项。

## 稳定性保障

- **超时控制**：单条处理设置上限，超时自动跳过并记入失败明细，避免整批卡死。
- **重试策略**：可恢复类错误（临时占用、瞬时 IO 失败）自动重试 3 次，间隔递增。
- **降级方案**：高级解析失败时自动回退到基础解析模式，保证有可用输出而非直接报错。
- **幂等性**：重复执行同一批输入结果一致，不会产生重复追加。

## FAQ 与反模式

**Q：可以直接对原始文件覆盖写入吗？**
A：不建议。默认输出到独立文件，保留原始数据是可回溯的前提。

**Q：处理到一半失败了怎么办？**
A：已完成部分的输出有效，查看失败明细后只重跑失败项即可，无需整批重来。

**反模式 ①**：不做试运行直接批量处理全量数据 —— 参数配错会一次性污染全部输出。

**反模式 ②**：忽略失败明细只看成功数 —— 静默跳过的条目会造成数据缺口。

**反模式 ③**：把工具输出直接作为最终结论 —— 关键字段务必人工抽检。

## 安全声明

- 全流程本地执行，不上传任何用户数据到第三方服务。
- 不读取与任务无关的目录，不写入系统目录。
- 处理含个人信息的数据时，请自行遵守《个人信息保护法》等相关法规。
- 本 Skill 代码由 AI 辅助生成并经自检验证，以 MIT 协议开源，使用者自负使用后果。
