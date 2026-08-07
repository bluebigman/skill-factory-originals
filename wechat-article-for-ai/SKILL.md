---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: wechat-article-for-ai
name: wechat-article-for-ai
displayName: 公众号文章 转Markdown 内容提取
description: 将微信公众号文章链接或内容转为结构化Markdown，支持批量与图片本地化。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/wechat-article-for-ai
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 内容管道工
agent_created: true
trigger_words: ["公众号文章", "wechat article", "微信文章转markdown", "公众号内容提取", "文章抓取", "微信推文下载"]
---

> 📜 **用户协议（User Agreement）**
> 1. 本 Skill 仅供学习与参考用途。使用本 Skill 产生的任何结果，由使用者自行承担全部责任；本 Skill 不提供任何明示或暗示的保证。
> 2. 涉及法律、财务、税务、投资、医疗等专业决策时，请务必咨询持证专业人士。
> 3. 本代码受版权法保护，未经授权复制、反向工程或商业利用将被追究法律责任。
<!-- user-agreement-injected -->


> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->

> 本内容由 AI 生成，仅供学习参考 <!-- ai-generated-notice -->

# 微信公众号文章转 Markdown 工具（Skill）

## 一、能力边界：一页纸速查卡

本 Skill 面向需要将微信公众号文章内容转换为干净、结构化 Markdown 的开发者、内容运营者及 AI Agent。它不是一个通用爬虫，也不是排版美化工具。

| 能力维度 | 说明 |
| --- | --- |
| **能做** | 1. 从单个或多个公众号文章 URL 提取正文、标题、作者、发布时间 |
| | 2. 将提取内容输出为规范 Markdown（含 Frontmatter 元数据区） |
| | 3. 自动下载文章内图片到本地目录，并重写图片引用路径 |
| | 4. 批量处理：一次提交多个 URL，按队列顺序逐个抓取 |
| | 5. 对抓取失败或字段缺失的条目，输出 `[需核实:字段名]` 占位符 |
| **不能做** | 1. 无法绕过公众号的付费阅读、关注可见等权限限制 |
| | 2. 不处理视频、音频等非文本媒体内容的转写 |
| | 3. 不提供文章内容的摘要、翻译或情感分析 |
| | 4. 不保证抓取速度，受限于目标站点响应时间 |
| **适用对象** | 需要将公众号内容迁移至自有博客、知识库、或用于本地检索分析的个人/团队 |

## 二、触发方式与场景映射

当你的指令中出现以下关键词或意图时，本 Skill 将被激活：

| 大白话场景 | 触发词示例 | 本 Skill 行为 |
| --- | --- | --- |
| "帮我把这篇微信文章存下来" | 公众号文章、微信推文 | 提取单篇文章并输出 Markdown |
| "抓取这几个链接的正文" | 批量、多个链接、列表 | 按顺序批量处理，生成多个 .md 文件 |
| "把文章里的图也存到本地" | 图片本地化、下载图片 | 启用图片下载与路径重写 |
| "测试一下工具是否正常" | --selftest | 运行内置自检流程，输出环境诊断信息 |
| "查看版本" | --version | 输出当前 Skill 版本号与兼容性说明 |

## 三、标准流程：从输入到输出

### 前置条件

1. 目标 URL 必须是微信公众号文章的标准链接（`https://mp.weixin.qq.com/s/...` 格式）。
2. 运行环境需具备 Python 3.9+ 及网络访问能力。
3. 若启用图片本地化，需确保输出目录有写入权限。

### 执行步骤

1. **输入解析**：接收用户提供的 URL 或包含 URL 的文本。若为多个 URL，按行拆分，去除空白字符。
2. **参数校验**：检查是否包含 `--selftest` 或 `--version` 标志。若存在，执行对应子流程并退出。
3. **抓取与解析**：对每个 URL，使用反检测浏览器内核（Camoufox）发起请求。若首次请求失败，自动重试，最多 3 次，间隔 2 秒。
4. **内容提取**：从 HTML 中提取标题、作者、发布时间、正文 HTML。正文需去除脚本、样式、隐藏元素。
5. **图片处理**（可选）：若指定图片本地化，下载正文中所有 `<img>` 标签的图片至 `assets/` 目录，并将 `src` 属性重写为相对路径。
6. **格式转换**：将正文 HTML 转换为 Markdown。转换规则：
   - 标题层级映射：`<h1>`~`<h6>` → `#`~`######`
   - 段落 `<p>` → 空行分隔的文本块
   - 列表 `<ul>/<ol>` → `-` 或 `1.` 前缀
   - 引用 `<blockquote>` → `> ` 前缀
   - 代码块 `<pre>` → 围栏代码块
   - 链接 `<a>` → `[文本](URL)`
   - 图片 `<img>` → `![替代文本](路径)`
7. **生成输出**：组装 Markdown 文件，结构如下：

```markdown

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
