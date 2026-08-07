---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: go-get-jobs
name: go-get-jobs
displayName: 职位聚合 技术岗采集 批量抓取
description: 聚合50+科技公司软件工程职位，支持命令行采集与结构化输出。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/go-get-jobs
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: SkillForge Studio
agent_created: true
trigger_words: ["go-get-jobs", "职位采集", "爬虫抓取", "岗位聚合", "job scraper"]
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

# go-get-jobs — 技术职位聚合采集 Skill

## 一、能力边界（一页纸速查卡）

### ✅ 能做（核心能力）

| 编号 | 能力项 | 说明 |
|------|--------|------|
| 1 | 多源职位采集 | 从 50+ 科技公司（Google、Meta、Apple 等）招聘页面抓取软件工程类职位 |
| 2 | 结构化输出 | 将抓取结果转换为统一 JSON / CSV 格式，包含公司、职位、地点、链接等字段 |
| 3 | 命令行交互 | 支持 `--selftest` 自检模式与 `--version` 版本查询 |
| 4 | 增量更新 | 支持基于上次抓取时间戳的增量采集，避免重复请求 |
| 5 | 自定义过滤 | 可按关键词（如 "Go", "Remote"）、地点、经验级别过滤结果 |

### ❌ 不能做（明确边界）

| 编号 | 限制项 | 说明 |
|------|--------|------|
| 1 | 不提供职位申请服务 | 仅采集与展示，不代投简历 |
| 2 | 不保证数据实时性 | 抓取结果取决于目标网站可访问性与更新频率 |
| 3 | 不处理验证码/登录墙 | 需要登录或验证码的页面无法自动采集 |
| 4 | 不解析非结构化附件 | 仅处理 HTML 页面与标准 API 返回 |
| 5 | 不存储历史数据 | 每次运行输出当前快照，不维护历史数据库 |

### 🎯 适用对象

- 求职者：批量浏览多家公司职位，快速筛选目标岗位
- 招聘研究者：分析技术岗位分布、技能需求趋势
- 自动化工作流：作为 CI/CD 或定时任务的一部分，定期采集职位数据


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
