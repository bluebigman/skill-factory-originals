---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: resource-controller
name: resource-controller
displayName: 资源编排 控制器生成 接口抽象
description: 将输入数据转化为结构化REST控制器结果，支持批量与自定义格式。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/resource-controller
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 架构工坊
agent_created: true
trigger_words: ["resource controller", "资源控制器", "RESTful控制器", "控制器生成", "接口抽象"]

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

# 资源控制器（Resource Controller）技能文档

## 一、能力边界速查卡

### 1.1 能做（核心能力）

| 编号 | 能力项 | 说明 | 输入示例 | 输出示例 |
|------|--------|------|----------|----------|
| C1 | 数据/文件/URL → 结构化结果 | 解析用户提供的任意来源内容，提取关键字段 | `users.csv` 文件 | `[{ "name": "张三", "age": 30 }]` |
| C2 | 关键信息识别与保留 | 自动识别实体、属性、关系，保留原始语义 | 一段产品描述文本 | `{ "product_name": "...", "price": "..." }` |
| C3 | 按约定格式生成输出 | 支持 JSON / YAML / 表格 / 自定义模板 | 指定 `format=yaml` | YAML 格式的控制器定义 |
| C4 | 置信度标注 | 对每个字段标注可信程度（高/中/低） | 模糊的输入数据 | `{ "field": "value", "confidence": 0.85 }` |
| C5 | 批量处理与自定义格式 | 支持多文件/多记录批量转换，可扩展输出模板 | 10 个 JSON 文件 | 合并后的结构化数据集 |

### 1.2 不能做（明确边界）

| 编号 | 限制项 | 说明 |
|------|--------|------|
| L1 | 不执行代码 | 不运行、编译或调试用户提供的程序代码 |
| L2 | 不访问外部服务 | 不主动调用第三方 API 或数据库（除非用户明确提供连接信息） |
| L3 | 不保证数据准确性 | 输入数据本身的错误不在本技能纠错范围内 |
| L4 | 不生成完整应用 | 只生成控制器层抽象，不包含视图、路由、模型等 |

### 1.3 适用对象

- **适用**：需要快速将散乱数据整理为结构化 REST 控制器定义的开发者、架构师、API 设计人员。
- **不适用**：需要完整 MVC 框架代码生成、需要数据库迁移脚本、需要前端页面代码的场景。


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
