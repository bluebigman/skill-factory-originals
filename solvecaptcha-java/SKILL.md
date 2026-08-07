---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: solvecaptcha-java
name: solvecaptcha-java
displayName: 验证码识别 Java 自动化接入
description: Java 验证码识别客户端，辅助爬虫与自动化工具绕过人机验证。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/solvecaptcha-java
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 技能工坊·玄机
agent_created: true
trigger_words: ["验证码识别", "captcha solver", "人机验证绕过", "Java 爬虫辅助", "自动化验证处理"]
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

# solvecaptcha-java 技能文档

## 一、能力边界速查卡

| 维度 | 说明 |
|------|------|
| **核心用途** | 为 Java 编写的爬虫、采集器、自动化脚本提供验证码识别接入能力 |
| **输入类型** | 验证码图片 URL、本地图片文件路径、Base64 编码字符串 |
| **输出类型** | 识别出的验证码文本字符串（结构化 JSON 包装） |
| **支持场景** | 登录拦截、表单提交、批量数据采集时的验证码自动填充 |
| **不支持场景** | 无法处理动态验证码（滑块、拼图、行为验证）；不提供打码平台账号体系 |

**适用对象**：正在维护 Java 爬虫项目、需要处理验证码阻塞的开发者；对验证码服务接入流程不熟悉、需要快速落地的团队。

**不适用对象**：需要处理 reCAPTCHA v3 等无感验证的开发者；期望零配置即用的非技术人员。


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
