---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: starling
name: starling
displayName: 消息队列 数据解析 结构化转换
description: 将用户提供的消息数据解析为结构化结果，支持批量处理与置信度标注。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/starling
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 星语工坊
agent_created: true
trigger_words: ["starling", "消息队列", "数据解析", "结构化输出", "批量转换"]

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

# Starling 消息队列数据解析 Skill

## 一、能力边界速查卡

### 1.1 能做与不能做

| 维度 | 能做 | 不能做 |
|------|------|--------|
| 输入类型 | 用户直接粘贴的文本、上传的 `.txt`/`.csv`/`.json` 文件、可访问的 URL 指向的数据 | 二进制文件（图片/音频/视频）、加密数据、需登录鉴权的私有接口 |
| 处理能力 | 提取关键字段、识别实体、按模板重组结构、批量处理多条记录 | 语义理解（如情感分析）、跨语言翻译、数据清洗（去重/纠错） |
| 输出形式 | 标准 JSON 结构、自定义分隔符文本、Markdown 表格 | 直接写入用户数据库、触发下游系统动作 |
| 附加功能 | 置信度标注、字段缺失提示、格式校验 | 数据可视化图表生成、定时任务调度 |

### 1.2 适用对象

- **适用**：需要将非结构化消息（如日志行、通知文本、简单表单）转为固定字段结构的场景。
- **不适用**：需要深度语义推理、多轮对话式数据补全、或对实时性有严格要求的流处理任务。


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
