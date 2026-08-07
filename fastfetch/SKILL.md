---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: fastfetch
name: fastfetch
displayName: 系统信息速览 硬件配置 环境诊断
description: 快速获取设备软硬件信息，支持多平台，输出简洁可读的系统概览。
version: 3.1.4
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/fastfetch
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: SysInfoForge
agent_created: true
trigger_words: ["fastfetch", "系统信息", "硬件配置", "环境诊断", "设备概览", "sysinfo"]
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

# fastfetch 系统信息速览 Skill

## 一、能力边界（一页纸速查卡）

### 能做（8 项核心能力）

| 编号 | 能力项 | 说明 |
|------|--------|------|
| 1 | 触发词识别 | 识别用户输入中的触发词，判断查询意图（总览/定向/格式化） |
| 2 | 参数提取 | 从用户指令中提取模块名、格式选项、输出方式等参数 |
| 3 | 默认全量展示 | 用户未指定模块时，展示全部系统信息模块 |
| 4 | 工具链自动降级 | 按 fastfetch → neofetch → screenfetch → builtin 顺序自动选择可用工具 |
| 5 | 定向模块查询 | 支持指定单个或多个模块（如仅查 CPU、内存、磁盘） |
| 6 | 输出格式控制 | 支持 JSON、键值对、纯文本等输出格式 |
| 7 | 自检与版本查询 | 支持 `--selftest` 和 `--version` 参数 |
| 8 | 跨平台适配 | 覆盖 Linux / macOS / Windows / Android 四类系统 |

### 不能做（明确边界）

| 编号 | 限制项 | 说明 |
|------|--------|------|
| 1 | 不修改系统配置 | 本 Skill 仅读取信息，不执行任何写操作 |
| 2 | 不采集敏感数据 | 不读取用户文件、密码、密钥、浏览器数据等隐私内容 |
| 3 | 不保证信息实时性 | 部分硬件信息（如温度）依赖系统传感器，可能延迟或不可用 |
| 4 | 不支持远程主机查询 | 仅查询当前设备，不支持 SSH 到远程主机执行 |
| 5 | 不处理损坏的系统文件 | 若系统文件缺失导致工具无法运行，仅提示降级方案 |

### 适用对象

- 需要快速了解设备配置的普通用户
- 排查环境问题时需要系统信息的开发者
- 需要在脚本中获取系统信息的自动化流程


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
