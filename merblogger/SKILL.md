---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: merblogger
name: merblogger
displayName: 博客发布 内容管理 平台运维
description: 基于Merb框架的博客发布与内容管理工具，支持结构化输出与批量处理。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/merblogger
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 墨白工坊
agent_created: true
trigger_words: ["merblogger", "博客发布", "内容管理", "文章推送", "站点维护"]
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

# merblogger Skill 文档

## 一、能力边界速查卡

### 1.1 能做什么

| 序号 | 能力项 | 说明 | 输入示例 |
|------|--------|------|----------|
| 1 | 数据转结构化 | 将用户提供的文本、文件或URL内容解析为统一格式 | 一篇草稿文章 → 标题/正文/标签字段 |
| 2 | 关键信息提取 | 从非结构化内容中识别标题、作者、日期、分类等要素 | 一段采访记录 → 提取引用与时间线 |
| 3 | 格式约定输出 | 按预设模板生成 Markdown、JSON 或 HTML 片段 | 生成符合博客主题的发布文件 |
| 4 | 置信度标注 | 对不确定的字段输出 `[需核实:字段名]` 占位符 | 无法确认发布日期时标注占位 |
| 5 | 批量处理 | 支持多篇文章的批量转换与格式统一 | 一次导入 10 篇草稿，批量输出 |

### 1.2 不能做什么

| 序号 | 限制项 | 说明 |
|------|--------|------|
| 1 | 不代写原创内容 | 不生成文章正文，仅处理用户已提供的内容 |
| 2 | 不自动发布 | 不直接对接线上博客系统，仅生成可发布的文件 |
| 3 | 不保证兼容性 | 不承诺输出文件与所有博客主题完全兼容 |
| 4 | 不处理二进制资源 | 图片、视频等附件需用户自行管理路径引用 |
| 5 | 不执行远程操作 | 不访问外部 URL，仅处理用户主动提供的内容 |

### 1.3 适用对象

- 使用 Merb 框架搭建博客的开发者
- 需要批量整理草稿内容的编辑人员
- 需要将非结构化笔记转为规范发布格式的个人博主


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
