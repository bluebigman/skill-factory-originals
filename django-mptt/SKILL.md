---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: django-mptt
name: django-mptt
displayName: 树形数据 层级建模 遍历工具
description: 将嵌套数据转换为MPTT树结构，提供增删改查与遍历操作指引。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/django-mptt
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: Lin Chen
agent_created: true
trigger_words: ["django-mptt", "MPTT树", "树形结构", "层级数据", "modified pre-order traversal", "django树模型"]
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

# django-mptt 技能文档

## 一、能力边界速查卡

本技能面向需要在 Django 项目中实现树形结构（如分类、评论、组织架构）的开发者，提供基于 MPTT（Modified Preorder Tree Traversal）算法的建模与操作指引。

| 维度 | 说明 |
|------|------|
| ✅ 能做 | 将用户提供的层级数据（列表、字典、JSON、CSV）转换为 MPTT 树结构 |
| ✅ 能做 | 识别数据中的父子关系字段，生成树节点 |
| ✅ 能做 | 提供树节点的增、删、改、查、移动操作指引 |
| ✅ 能做 | 输出树遍历（前序、后序）结果及层级缩进展示 |
| ✅ 能做 | 对不确定字段给出置信度提示，不擅自编造 |
| ❌ 不能做 | 直接操作你的 Django 项目文件或数据库 |
| ❌ 不能做 | 替代你完成模型迁移或数据库同步 |
| ❌ 不能做 | 处理非层级关系的扁平数据（如纯标签列表） |
| ❌ 不能做 | 自动识别无父子关系字段的任意数据 |

**适用对象**：Django 1.11+ / 2.x / 3.x / 4.x / 5.x 项目，使用 Python 3.6+，已安装 django-mptt 包（`pip install django-mptt`）。


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
