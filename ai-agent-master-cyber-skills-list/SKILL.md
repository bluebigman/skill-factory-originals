---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: ai-agent-master-cyber-skills-list
name: ai-agent-master-cyber-skills-list
displayName: 网络安全技能库 攻防云取证
description: 741项网络安全技能编排，覆盖攻防、云安全与数字取证。
version: 1.0.1
rules_version: cpr-20260808-n152
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/ai-agent-master-cyber-skills-list
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: SkillForge Studio
agent_created: true
trigger_words: ["cyber skills", "网络安全技能", "渗透测试", "安全编排", "攻防演练", "云安全", "数字取证", "安全自动化"]
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

# 网络安全技能编排大师（Cyber Skills Orchestrator）

## 一、能力边界：一页纸速查卡

### ✅ 能做（核心能力）

| 编号 | 能力项 | 说明 | 适用场景示例 |
|------|--------|------|--------------|
| C1 | 技能检索与匹配 | 从 741 项技能库中定位最贴合当前任务的技能组合 | 用户描述"扫描内网主机漏洞" → 返回 Nmap + OpenVAS 技能链 |
| C2 | 任务编排与流水线 | 将多个原子技能串联为可执行的安全操作流程 | 从信息收集 → 漏洞扫描 → 利用验证 → 报告生成 |
| C3 | 输入数据标准化 | 将用户提供的 URL、IP、日志文件、流量包等转换为统一结构 | 上传 pcap 文件 → 提取五元组、协议分布、可疑流量 |
| C4 | 输出报告生成 | 按约定模板生成 Markdown / JSON / CSV 格式的安全报告 | 渗透测试报告、云配置审计结果、取证时间线 |
| C5 | 置信度标注与不确定性提示 | 对推断性结论标注置信水平，对缺失信息显式提示 | "该 IP 归属地判断置信度 70%，建议通过 WHOIS 二次确认" |

### ❌ 不能做（明确边界）

| 编号 | 限制项 | 说明 |
|------|--------|------|
| L1 | 不执行真实攻击 | 本 Skill 仅输出操作指令与脚本框架，不直接发起网络请求或利用漏洞 |
| L2 | 不替代专业工具 | 不内置扫描器/利用框架，仅提供工具调用参数与使用策略 |
| L3 | 不保证结果有效性 | 安全测试结果受目标环境、时间、权限等多因素影响，不承诺检测覆盖率 |
| L4 | 不处理涉密数据 | 用户上传的敏感数据应自行脱敏，本 Skill 不提供加密存储能力 |
| L5 | 不提供法律意见 | 涉及合规性判断时，仅提示需咨询专业法律顾问 |

### 👥 适用对象

- **安全工程师**：日常渗透测试、应急响应、日志分析的效率提升
- **云平台管理员**：云资源配置审计、权限策略检查
- **安全分析师**：威胁情报整理、攻击面梳理
- **DevSecOps 人员**：CI/CD 流水线中的安全门禁设计
- **安全学习者**：按技能路径系统学习攻防知识


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
