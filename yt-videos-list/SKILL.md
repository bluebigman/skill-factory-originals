---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: yt-videos-list
name: yt-videos-list
displayName: 频道视频清单 采集归档 列表生成
description: 自动采集YouTube频道全部视频，生成可编辑的清单文件。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/yt-videos-list
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: SkillForge Studio
agent_created: true
trigger_words: ["yt-videos-list", "YouTube视频列表", "频道视频采集", "视频清单生成", "YouTube频道归档"]

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

# SKILL.md — yt-videos-list

## 一、能力边界：一页纸速查卡

### 1.1 能做（核心能力清单）

| 编号 | 能力项 | 说明 |
|------|--------|------|
| C1 | 频道视频清单生成 | 输入 YouTube 频道 URL 或频道 ID，输出该频道全部视频的清单文件 |
| C2 | 多格式输出 | 支持生成 `.txt`、`.csv`、`.md` 三种格式的清单文件 |
| C3 | 字段结构化提取 | 自动提取视频标题、视频ID、发布时间、视频时长、观看次数、视频描述摘要等字段 |
| C4 | 增量更新 | 对已生成的清单文件，可自动检测新增视频并追加更新 |
| C5 | 批量频道处理 | 支持一次提交多个频道 URL，批量生成多个清单文件 |

### 1.2 不能做（明确边界）

| 编号 | 限制项 | 说明 |
|------|--------|------|
| L1 | 不下载视频内容 | 仅采集元数据（标题、描述、统计信息），不下载视频文件本身 |
| L2 | 不处理需登录的私有视频 | 仅采集公开可见的视频信息，不处理会员专享或私享视频 |
| L3 | 不绕过地区限制 | 若频道视频因地区限制不可见，则无法采集 |
| L4 | 不保证实时性 | 采集结果反映采集时刻的状态，后续新增视频需重新运行更新 |
| L5 | 不处理非 YouTube 平台 | 仅支持 YouTube 平台，不支持其他视频网站 |

### 1.3 适用对象

- 内容创作者：需要备份自己频道的视频列表
- 市场研究人员：需要分析竞品频道的内容布局
- 数据分析师：需要获取视频元数据用于统计分析
- 档案管理员：需要定期归档频道内容变化


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
