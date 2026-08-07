---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: wechat-article-pipeline-skill
name: wechat-article-pipeline-skill
displayName: 公众号图文 排版配图 草稿创建
description: 将素材转为公众号文章，完成排版配图与草稿创建。
version: 1.0.2
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/wechat-article-pipeline-skill
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: PipelineForge
agent_created: true
trigger_words: ["公众号文章", "微信文章排版", "图文排版", "草稿箱", "文章配图", "推文制作", "公众号发布"]

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

# 公众号图文流水线 Skill 文档

## 1. 能力边界（一页纸速查卡）

### 1.1 能做什么

| 能力项 | 说明 | 输入要求 |
|--------|------|----------|
| 素材转文章 | 将纯文本、Markdown、Word 提取文本转为公众号风格文章 | 文本长度 ≥ 200 字 |
| 排版处理 | 自动分段、标题层级、引用块、列表、加粗强调 | 文本含结构化标记或可推断层级 |
| 配图建议 | 为文章生成配图描述（含尺寸、风格、位置建议） | 文章主题明确 |
| 草稿创建 | 生成可直接粘贴到公众号后台的草稿内容（含 HTML 片段） | 排版完成后的文章 |

### 1.2 不能做什么

| 限制项 | 说明 |
|--------|------|
| 不直接调用微信 API | 本 Skill 不连接微信公众平台，不自动上传草稿 |
| 不生成图片文件 | 仅提供配图描述与建议，不产出实际图片 |
| 不处理视频/音频 | 仅处理文本与静态图片建议 |
| 不做营销文案撰写 | 仅做排版与结构优化，不生成推广话术 |
| 不保证阅读量/传播效果 | 内容质量与平台算法不在本 Skill 控制范围内 |

### 1.3 适用对象

- 公众号运营者（个人或小团队）
- 需要快速将素材转为可发布格式的内容编辑
- 希望统一排版风格、减少重复劳动的写作者


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
