---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: plexus
name: plexus
displayName: 多智能体工具链 一键装配 环境配置
description: 为AI编程工具批量配置MCP服务、技能与规则，支持主流CLI智能体。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/plexus
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: skill-forge-studio
agent_created: true
trigger_words: ["plexus", "MCP配置", "技能安装", "规则同步", "AI工具链", "环境初始化", "智能体配置"]
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

# SKILL.md — plexus 技能文档

## 1. 能力边界速查卡

### 1.1 能做什么（核心能力清单）

| 编号 | 能力项 | 说明 | 适用场景示例 |
|------|--------|------|--------------|
| C1 | 数据/文件/URL 结构化转换 | 将用户提供的原始输入（文本、文件路径、网页链接）解析为结构化结果 | 从 README 中提取 MCP 配置项 |
| C2 | 关键信息识别与保留 | 自动过滤无关内容，保留服务名、端口、命令、参数等关键字段 | 识别 docker-compose 中的服务定义 |
| C3 | 按约定格式生成输出 | 根据用户指定的格式（JSON/YAML/TOML）输出配置结果 | 生成 `.mcp.json` 或 `settings.json` 片段 |
| C4 | 置信度标注 | 对识别结果给出可信度评估，低置信度字段明确标注 | 识别到疑似路径但无法确认时标注 `[需核实:path]` |
| C5 | 批量处理与自定义格式 | 支持多文件/多 URL 输入，支持用户自定义输出模板 | 批量转换 10 个仓库的配置为统一格式 |

### 1.2 不能做什么（明确边界）

| 编号 | 限制项 | 说明 |
|------|--------|------|
| L1 | 不执行远程安装 | 本 Skill 仅生成配置内容，不直接调用系统命令安装软件 |
| L2 | 不保证兼容性 | 生成的配置是否适配目标工具版本，需用户自行验证 |
| L3 | 不处理二进制文件 | 仅支持文本类文件（`.md`、`.json`、`.yaml`、`.toml`、`.txt` 等） |
| L4 | 不进行身份认证 | 涉及 API Key、Token 等敏感信息，仅做占位符处理，不代填 |

### 1.3 适用对象

- 使用 Claude Code、Codex、Cursor、Gemini CLI、Qwen Code 等 CLI 工具的开发者
- 需要统一管理多个 AI 工具配置的团队或个人
- 需要将现有项目配置迁移到新 AI 工具链的迁移场景


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
