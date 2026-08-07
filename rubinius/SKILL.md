---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: rubinius
name: rubinius
displayName: 数据解析 结构化提取 格式转换
description: 将用户提供的数据、文件或URL解析为结构化结果，保留关键信息并标注置信度。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/rubinius
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: LingDataWorks
agent_created: true
trigger_words: ["rubinius", "数据解析", "结构化提取", "格式转换", "信息抽取"]
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

# Rubinius 数据解析与结构化提取 Skill

## 一、能力边界（一页纸速查卡）

### 1.1 能做（核心能力）

| 编号 | 能力项 | 说明 |
|------|--------|------|
| C1 | 多源输入解析 | 支持用户直接粘贴文本、上传文件（.txt/.csv/.json/.md）、提供 URL 链接三种输入方式 |
| C2 | 关键信息识别 | 自动识别输入中的实体、数字、日期、名称、状态等关键字段，并保留原始上下文 |
| C3 | 结构化输出生成 | 按用户指定或系统默认的字段结构，输出 JSON / Markdown 表格 / CSV 三种格式 |
| C4 | 置信度标注 | 对每个提取字段标注 confidence 等级（high / medium / low），不确定时使用 `[需核实:字段名]` 占位 |
| C5 | 批量处理与自定义格式 | 支持一次提交多条记录（以空行或分隔符区分），允许用户自定义输出字段名和顺序 |

### 1.2 不能做（明确边界）

| 编号 | 限制项 | 说明 |
|------|--------|------|
| L1 | 不执行代码 | 不运行用户提供的脚本、不调用外部 API、不访问 URL 背后的动态内容（仅抓取静态页面） |
| L2 | 不处理加密内容 | 密码保护的文件、加密压缩包、需要登录的网页不在处理范围内 |
| L3 | 不进行语义推断 | 不猜测缺失字段的含义，不根据上下文补全未提供的信息 |
| L4 | 不保证数据准确性 | 输出结果基于输入内容机械提取，不验证业务逻辑正确性 |
| L5 | 不支持图片/音频 | 仅处理文本类输入，不包含 OCR 或语音转写能力 |

### 1.3 适用对象

- 需要将散乱文本整理为表格数据的运营人员
- 需要从网页批量提取信息的调研人员
- 需要将非结构化数据转为结构化格式的开发者
- 需要快速核对多份文档关键字段的审核人员


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
