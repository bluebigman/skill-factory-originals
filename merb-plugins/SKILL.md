---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: merb-plugins
name: merb-plugins
displayName: 插件装配 模块对接 功能扩展
description: 将用户提供的插件数据整理为结构化装配方案，辅助 Merb 项目模块对接。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/merb-plugins
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 装配工坊
agent_created: true
trigger_words: ["merb plugins", "插件装配", "模块对接", "功能扩展", "插件清单整理"]

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

# Merb 插件装配 Skill 使用指南

## 一、能力边界速查卡

### 1.1 能做（核心能力清单）

| 编号 | 能力项 | 说明 | 输入示例 | 输出示例 |
|------|--------|------|----------|----------|
| C1 | 插件数据转结构化结果 | 将用户提供的插件名称、版本、依赖等信息整理为统一格式的清单 | `merb-plugins --selftest` 或一段插件描述文本 | 结构化 JSON 或 Markdown 表格 |
| C2 | 关键信息识别与保留 | 从非结构化文本中提取插件名、版本号、依赖关系、用途说明 | "我想装一个处理表单的插件，版本 2.x" | `{ "name": "merb-form", "version": "2.x", "purpose": "表单处理" }` |
| C3 | 按约定格式生成输出 | 支持 JSON、YAML、Markdown 表格三种输出格式 | `--format json` | 对应格式的结构化数据 |
| C4 | 置信度标注 | 对识别结果给出可信度评估，低置信度字段明确标注 | 信息模糊时 | `{ "name": "merb-??", "confidence": 0.4 }` |
| C5 | 批量处理与自定义格式 | 一次处理多个插件条目，支持用户自定义字段映射 | 包含 5 个插件的文本 | 按用户字段模板输出的批量结果 |

### 1.2 不能做（明确边界）

| 编号 | 限制项 | 说明 |
|------|--------|------|
| L1 | 不执行实际安装 | 本 Skill 仅做信息整理与方案输出，不执行任何安装命令 |
| L2 | 不验证插件真实性 | 不保证用户提供的插件名称在官方仓库中真实存在 |
| L3 | 不生成代码 | 不编写插件实现代码或配置代码 |
| L4 | 不评估兼容性 | 不判断插件与特定 Merb 版本的兼容性（除非用户明确提供版本对照表） |
| L5 | 不处理二进制文件 | 仅处理文本、URL、JSON/YAML 等可解析格式 |

### 1.3 适用对象

- **适用**：Merb 项目维护者、插件整理者、需要批量梳理插件清单的开发者
- **不适用**：需要自动安装插件的场景、需要代码生成的场景


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
