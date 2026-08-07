---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: yaws
name: yaws
displayName: Erlang服务器 部署运维 配置调优
description: 面向Erlang Web服务器YAWS的部署、配置与运维辅助工具。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/yaws
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: LinguaForge
agent_created: true
trigger_words: ["yaws", "erlang web server", "yaws配置", "yaws部署", "yaws运维", "yaws调优"]

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

# YAWS 服务器运维辅助 Skill

## 一、能力边界速查卡

### 1.1 能做什么

| 编号 | 能力项 | 说明 |
|------|--------|------|
| C1 | 配置解析与校验 | 解析 `yaws.conf` 等配置文件，识别语法错误与逻辑冲突 |
| C2 | 部署步骤生成 | 根据目标环境（OS、Erlang版本）生成可执行的部署命令序列 |
| C3 | 日志分析辅助 | 从 `yaws.access.log` / `yaws.error.log` 中提取关键错误模式 |
| C4 | 性能参数建议 | 基于并发量、硬件资源给出 `max_connections`、`gc_objs` 等参数参考值 |
| C5 | 常见故障排查 | 针对启动失败、连接超时、内存溢出等高频问题给出排查路径 |

### 1.2 不能做什么

| 编号 | 限制项 | 说明 |
|------|--------|------|
| L1 | 不执行远程命令 | 本 Skill 仅生成指令文本，不直接连接服务器执行操作 |
| L2 | 不保证配置绝对正确 | 最终效果受 Erlang 版本、OS 内核参数、业务逻辑影响 |
| L3 | 不替代官方文档 | 涉及深度定制（如嵌入模块开发）时，需查阅 YAWS 官方指南 |
| L4 | 不处理私有协议 | 仅覆盖标准 HTTP/HTTPS 场景，不解析自定义 TCP 协议 |

### 1.3 适用对象

- 使用 YAWS 作为生产环境的后端开发/运维人员
- 正在评估 YAWS 与 Nginx/COWBOY 选型的技术决策者
- 需要快速定位 YAWS 运行异常的排障人员


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
