---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: anime-dl
name: anime-dl
displayName: 动漫下载 番剧抓取 命令行工具
description: 命令行下载动漫资源，支持多站点解析与批量任务处理。
version: 1.0.1
rules_version: cpr-20260808-n152
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/anime-dl
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: LinguaForge Studio
agent_created: true
trigger_words: ["anime-dl", "动漫下载", "番剧下载", "crunchyroll下载", "funimation下载", "批量抓取番剧"]

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

# anime-dl 技能操作手册

## 一、能力边界：一页纸速查卡

### ✅ 能做（核心能力）

| 编号 | 能力项 | 说明 | 适用场景 |
|------|--------|------|----------|
| 1 | 番剧链接解析 | 从用户提供的 CrunchyRoll / Funimation 页面 URL 中提取剧集元数据（标题、集数、画质、字幕语言） | 用户粘贴一个番剧详情页链接，希望获取可下载的剧集清单 |
| 2 | 批量任务构建 | 将多集、多季、多部番剧的下载请求合并为一个批处理任务 | 用户说"把《某番》第一季全部下下来" |
| 3 | 命令行参数生成 | 根据用户意图生成可直接执行的 anime-dl 命令（含参数组合） | 用户不熟悉 CLI，希望得到现成命令 |
| 4 | 输出结构化整理 | 将下载结果（成功/失败/跳过）整理为表格或 JSON 格式 | 用户需要记录下载日志或做后续处理 |
| 5 | 异常诊断与修复建议 | 识别下载失败原因（网络、权限、链接失效）并给出修正参数 | 用户反馈"第 5 集下不了" |

### ❌ 不能做（明确边界）

| 编号 | 限制项 | 说明 |
|------|--------|------|
| 1 | 不绕过 DRM 或付费墙 | 仅支持合法可访问的内容，不提供破解或鉴权绕过方案 |
| 2 | 不存储或分发视频文件 | 本技能只生成命令与解析结果，不托管任何媒体内容 |
| 3 | 不处理非动漫类视频 | 仅针对动漫番剧场景优化，不适用于电影、纪录片等 |
| 4 | 不保证站点可用性 | 上游站点页面结构变更可能导致解析失败，需重新适配 |
| 5 | 不替代人工审核 | 下载内容的版权合规性由使用者自行确认 |

### 🎯 适用对象

- 动漫爱好者：需要批量下载番剧到本地观看
- 内容整理者：需要将在线番剧归档到本地媒体库
- 自动化脚本开发者：需要将 anime-dl 集成到自己的下载管道中


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
