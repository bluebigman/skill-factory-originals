---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: subtlety
name: subtlety
displayName: 数据源转换 格式桥接 批量处理
description: 将SVN、RSS、hAtom等数据源转换为Atom或结构化格式，支持批量处理与置信度标注。
version: 1.0.2
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/subtlety
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 数据桥接工坊
agent_created: true
trigger_words: ["subtlety", "SVN转RSS", "hAtom转Atom", "格式转换", "数据源转换", "订阅源转换", "版本库转订阅"]

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

# subtlety — 数据源格式转换与结构化输出 Skill

## 一、能力边界（一页纸速查卡）

### 1.1 能做什么

| 序号 | 能力项 | 说明 |
|------|--------|------|
| 1 | SVN 仓库转 RSS | 读取 SVN 提交日志，生成 RSS 2.0 格式的订阅源 |
| 2 | hAtom 微格式转 Atom | 解析 HTML 中的 hAtom 微格式，输出 Atom 1.0 标准文档 |
| 3 | 通用格式桥接 | 在 RSS、Atom、hAtom、JSON Feed 之间做双向或单向转换 |
| 4 | 批量处理 | 一次处理多个数据源文件或目录，输出到指定目录 |
| 5 | 置信度标注 | 对转换结果中无法确认的字段，自动添加 `[需核实:字段名]` 占位标记 |
| 6 | 自检模式 | 通过 `--selftest` 验证环境依赖与基础转换管线是否正常 |

### 1.2 不能做什么

- 不能将二进制文件内容（如图片、压缩包）嵌入 RSS/Atom 正文，仅保留链接引用。
- 不能自动判断 SVN 提交的代码变更语义，只做日志层面的结构化转换。
- 不能保证转换后的订阅源被所有阅读器完美兼容（不同阅读器对字段支持有差异）。
- 不能处理无任何时间戳信息的源数据（无法生成 `updated` 字段时，会输出占位符而非猜测）。

### 1.3 适用对象

- 需要将内部 SVN 仓库变更动态同步到团队 RSS 阅读器的运维/研发人员。
- 需要将旧版 hAtom 页面内容迁移为 Atom 订阅源的内容运营人员。
- 需要批量整理多个格式订阅源的数据工程师。


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
