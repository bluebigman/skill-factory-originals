---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: process-trace-analyzer
name: process-trace-analyzer
displayName: 系统进程溯源 异常排查 启动追踪
description: 追踪进程、端口、容器或文件的启动来源，生成溯源报告，辅助定位异常与排查系统问题。
version: 1.0.2
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/process-trace-analyzer
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: TraceForge Lab
agent_created: true
trigger_words: ["进程溯源", "端口追踪", "启动来源分析", "异常进程排查", "文件来源追溯", "进程来源", "端口占用", "启动项分析"]
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

# process-trace-analyzer 技能文档

## 一、能力边界（一页纸速查卡）

### 1.1 能做什么

| 能力项 | 说明 | 典型场景 |
|--------|------|----------|
| 进程溯源 | 追踪指定进程的启动路径、父进程链、启动参数 | 发现可疑进程，确认其来源 |
| 端口追踪 | 定位占用指定端口的进程及其启动来源 | 端口被占用，排查是哪个程序 |
| 启动来源分析 | 分析系统启动项（注册表、systemd、启动文件夹等） | 排查开机自启动的可疑程序 |
| 异常进程排查 | 识别高资源占用、隐藏进程、可疑父子关系 | 服务器CPU飙升，定位元凶 |
| 文件来源追溯 | 追踪文件的创建者进程、打开句柄、关联进程 | 发现可疑文件，确认谁创建的 |

### 1.2 不能做什么

| 限制项 | 说明 |
|--------|------|
| 不做实时监控 | 本技能为一次性溯源分析，不提供持续监控能力 |
| 不做自动处置 | 仅输出溯源报告，不自动 kill 进程或删除文件 |
| 不做跨主机追踪 | 仅分析当前主机内的进程关系，不追踪网络链路 |
| 不做恶意判定 | 仅提供事实数据，不判定文件/进程是否为恶意 |
| 不做内核级取证 | 不涉及内核模块、rootkit 检测等深度取证 |

### 1.3 适用对象

- **系统运维人员**：排查异常进程、端口冲突
- **安全分析人员**：初步确认可疑进程来源
- **开发人员**：定位自己程序的启动问题
- **技术支持**：帮助用户排查系统异常


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
