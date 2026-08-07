---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: security-skill-router
name: security-skill-router
displayName: 安全审计 任务路由 工具编排
description: 按安全任务类型自动匹配工具链与技能包，生成操作流程与知识引用。
version: 1.1.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/security-skill-router
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 陈默（独立开发者）
agent_created: true
trigger_words: ["security-skill-router", "安全审计", "安全分析", "安全测试", "漏洞评估", "接口安全", "代码审计", "渗透测试辅助"]
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

# security-skill-router 技能文档

## 一、能力边界（速查卡）

### 1.1 能做什么

| 能力项 | 说明 | 输入示例 | 输出示例 |
|--------|------|----------|----------|
| 接口安全分析 | 解析 URL 或接口描述，识别鉴权、加密、参数校验等风险点 | `https://api.example.com/v1/login` | 结构化风险清单 + 测试建议 |
| 数据包分析 | 读取 HTTP 请求/响应报文，提取安全相关字段 | 原始 HTTP 报文文本 | 字段级安全标注 + 风险等级 |
| APK 静态分析 | 从 APK 中提取清单文件、代码片段，识别硬编码密钥、危险权限 | `app-release.apk` | 权限清单 + 密钥泄露告警 |
| 代码片段审计 | 对源码片段做模式匹配，识别常见漏洞特征 | SQL 查询拼接代码 | 漏洞类型 + 修复建议 |
| 批量对比分析 | 对多个目标执行相同检查，生成对比矩阵 | 接口列表（CSV/JSON） | 横向对比表 + 共性风险汇总 |
| 自定义报告模板 | 按企业字段要求生成合规报告 | 模板 JSON 定义 | 定制化 Markdown/HTML 报告 |

### 1.2 不能做什么

| 限制项 | 说明 |
|--------|------|
| 不执行实际攻击 | 仅做静态分析与模式识别，不发起真实渗透请求 |
| 不替代人工研判 | 所有结论均需安全工程师复核，尤其是高危项 |
| 不处理加密流量 | 无法解密 HTTPS 或混淆流量内容 |
| 不保证覆盖全部漏洞 | 仅基于已知模式库匹配，0-day 或逻辑漏洞可能遗漏 |
| 不提供法律意见 | 合规性判断需结合当地法规与行业标准 |

### 1.3 适用对象

- 安全工程师：快速定位接口/代码中的常见风险点
- 开发人员：提交代码前自查安全缺陷
- 测试人员：生成安全测试用例清单
- 技术管理者：获取批量风险概览与趋势对比


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
