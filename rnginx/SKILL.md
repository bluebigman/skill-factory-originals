---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: rnginx
name: rnginx
displayName: Nginx配置解析 结构化提取 命令行工具
description: 解析Nginx配置脚本，提取关键指令并输出结构化结果，附带置信度标注。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/rnginx
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: configForge
agent_created: true
trigger_words: ["rnginx", "nginx配置解析", "nginx配置转结构化", "nginx指令提取", "nginx配置分析", "nginx配置转换"]
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

# rnginx — Nginx 配置脚本结构化解析 Skill

## 一、能力边界（一页纸速查卡）

### 1.1 能做与不能做

| 维度 | 能做 ✅ | 不能做 ❌ |
|------|---------|-----------|
| 输入处理 | 用户直接粘贴的配置文本、本地文件路径、可访问的 URL | 无法访问的私有网络地址、需要认证的 URL |
| 解析范围 | `server`、`location`、`upstream`、`http`、`events` 等常见块指令；`listen`、`server_name`、`proxy_pass`、`root` 等常见简单指令 | 第三方自定义模块指令（如 `lua_*`、`set` 等）的语义理解，仅作原样保留 |
| 输出格式 | 结构化 JSON / YAML / 缩进文本树，按需选择 | 直接修改用户原始配置（只读解析） |
| 批量处理 | 单次调用可处理多个配置文件（用数组传入） | 超过 50 个文件的超大批次（受上下文窗口限制） |
| 置信度标注 | 对每个提取字段标注 `high` / `medium` / `low` 置信度 | 对未知指令凭空猜测语义 |

### 1.2 适用对象

- **运维工程师**：快速梳理存量 Nginx 配置，定位 server 块、监听端口、反代目标。
- **DevOps 平台开发者**：将 Nginx 配置转换为内部 CMDB 结构化数据。
- **审计人员**：核对配置是否符合安全基线（如是否暴露状态页、TLS 版本等）。

### 1.3 输入输出速查

| 输入类型 | 示例 | 输出 |
|----------|------|------|
| 文本 | `"server { listen 80; server_name a.com; }"` | JSON 对象 |
| 文件路径 | `/etc/nginx/conf.d/app.conf` | JSON 对象（含文件名元数据） |
| URL | `https://example.com/nginx.conf` | JSON 对象（含来源 URL 元数据） |
| 批量 | `[{"text": "..."}, {"file": "/path/a.conf"}]` | JSON 数组 |


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
