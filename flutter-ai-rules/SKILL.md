---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: flutter-ai-rules
name: flutter-ai-rules
displayName: Flutter开发 智能规则引擎 代码规范
description: 面向AI编程工具的Flutter开发规则与最佳实践集合。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/flutter-ai-rules
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: FlutterForge
agent_created: true
trigger_words: ["flutter", "dart", "flutter ai rules", "flutter开发", "跨平台开发"]
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

# Flutter AI 规则引擎（flutter-ai-rules）

## 一、能力边界速查卡

本 Skill 面向使用 AI 编程助手（Claude、Codex、Cursor 等）进行 Flutter 项目开发的工程师，提供一套可执行的规则与最佳实践。

| 维度 | 说明 |
|------|------|
| **核心用途** | 为 AI 编程工具提供 Flutter 开发的结构化规则，提升代码质量与一致性 |
| **适用对象** | Flutter 移动端开发者、跨平台团队、AI 辅助编码使用者 |
| **输入来源** | 用户提供的 Flutter 项目代码、pubspec.yaml、Dart 文件、项目结构描述 |
| **输出形式** | 规则匹配结果、代码审查建议、项目结构优化方案 |

### ✅ 能做的事情

1. 解析 Flutter 项目结构，识别关键配置文件（pubspec.yaml、analysis_options.yaml）
2. 根据输入代码片段，匹配对应的 Flutter 编码规范
3. 输出结构化的规则检查结果，包含问题定位与修改建议
4. 对不确定的规则匹配结果给出置信度提示
5. 支持批量检查多个 Dart 文件

### ❌ 不能做的事情

1. 不能直接执行 `flutter build` 或 `flutter test` 命令
2. 不能替代官方 Flutter 文档作为唯一参考
3. 不能保证规则覆盖所有 Flutter 版本差异
4. 不能自动修改项目文件（仅提供建议）
5. 不能处理非 Flutter 技术栈的问题


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
