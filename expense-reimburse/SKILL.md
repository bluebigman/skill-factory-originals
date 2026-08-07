---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: expense-reimburse
name: expense-reimburse
displayName: 报销单据 发票核验 归类制表
description: 整理报销单据，核验发票真伪，归类金额，生成明细表。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/expense-reimburse
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 单据整理工坊
agent_created: true
trigger_words: ["报销整理", "发票核验", "报销单归类", "费用明细表", "票据整理"]
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

# 报销单据整理 Skill 文档

## 一、能力边界：一页纸速查卡

### 1.1 能做与不能做

| 维度 | 能做 | 不能做 |
|------|------|--------|
| 输入处理 | 发票/收据照片中的文字信息、手工录入的金额清单 | 直接读取图片像素、识别手写体（需 OCR 预处理） |
| 真伪初查 | 根据发票代码、号码、校验码等字段做格式合规性初筛 | 连接税务系统做官方验真（需人工登录查验平台） |
| 金额核对 | 汇总多张单据金额、比对清单与票据总额差异 | 判断业务合理性（如招待费是否超标） |
| 类别归类 | 按费用性质（交通/餐饮/办公/差旅等）自动归类 | 处理跨类别混合单据（需人工指定） |
| 输出生成 | 生成结构化明细表（Markdown/CSV 格式） | 直接提交至财务系统（需人工导入） |

### 1.2 适用对象

- 需要整理月度/季度报销单据的职场人员
- 财务助理、行政专员等需批量处理票据的岗位
- 自由职业者整理个人开支凭证

### 1.3 输入输出规格

| 项目 | 规格 |
|------|------|
| 输入来源 | 发票/收据照片（需先 OCR 提取文字）、金额清单（文本粘贴） |
| 输出格式 | Markdown 表格（默认）、CSV（可选） |
| 字段结构 | 序号、日期、单据类型、金额、类别、备注、置信度 |


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
