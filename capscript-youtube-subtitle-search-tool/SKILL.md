---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: capscript-youtube-subtitle-search-tool
name: capscript-youtube-subtitle-search-tool
displayName: 字幕检索 时间轴定位 关键词过滤
description: 将字幕数据转为结构化检索结果，支持时间轴定位与关键词过滤。
version: 1.0.2
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/capscript-youtube-subtitle-search-tool
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: LinguaForge
agent_created: true
trigger_words: ["视频字幕", "字幕检索", "字幕搜索", "youtube subtitle", "字幕翻译", "字幕定位", "字幕筛选"]
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

# capscript-youtube-subtitle-search-tool 技能文档

## 一、能力边界（一页纸速查卡）

### 1.1 能做什么

| 能力项 | 说明 | 输入示例 | 输出示例 |
|--------|------|----------|----------|
| 字幕解析 | 将原始字幕文本（SRT/VTT/纯文本）解析为结构化条目 | 原始字幕文本块 | 带序号、时间戳、文本内容的 JSON 数组 |
| 时间轴定位 | 根据时间点或时间范围检索对应字幕片段 | `00:01:30` 或 `00:01:00-00:02:00` | 命中的字幕条目及上下文 |
| 关键词过滤 | 按单个或多个关键词筛选字幕内容 | `关键词: "机器学习"` | 所有包含该词的字幕条目列表 |
| 组合查询 | 时间范围 + 关键词联合过滤 | `00:05:00-00:10:00` + `"算法"` | 限定时间段内包含关键词的条目 |
| 字幕翻译辅助 | 提取指定片段供翻译参考 | 片段序号或时间戳 | 提取的原文片段及上下文 |

### 1.2 不能做什么

| 限制项 | 说明 |
|--------|------|
| 不生成字幕 | 本工具只检索和结构化已有字幕，不负责从音视频生成字幕 |
| 不执行翻译 | 可提取片段供翻译使用，但不内置翻译引擎 |
| 不处理音视频文件 | 仅处理文本格式的字幕数据，不解析媒体文件 |
| 不保证字幕完整性 | 若输入字幕本身有缺漏，检索结果同样存在缺漏 |
| 不识别说话人 | 不区分字幕中不同说话者的身份 |

### 1.3 适用对象

- 视频内容研究者：需要快速定位视频中特定话题出现的位置
- 字幕翻译人员：需要提取特定片段进行翻译或校对
- 课程学习者：需要按关键词回顾课程视频中的重点内容
- 内容运营者：需要从长视频中筛选出与特定主题相关的段落


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
