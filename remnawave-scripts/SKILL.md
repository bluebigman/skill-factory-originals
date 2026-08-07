---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: remnawave-scripts
name: remnawave-scripts
displayName: RemnaWave 部署配置与数据转换工具集
description: 面向RemnaWave项目的脚本工具集，提供部署、配置管理与数据转换能力。
version: 1.0.2
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/remnawave-scripts
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: ScriptForge Studio
agent_created: true
trigger_words: ["remnawave-scripts", "remnawave 脚本", "脚本工具集", "部署脚本", "配置管理", "数据转换", "RemnaWave 运维"]
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

# RemnaWave 脚本工具集 Skill 文档

## 1. 能力边界（一页纸速查卡）

### 1.1 能做什么

| 能力域 | 具体操作 | 适用场景 |
|--------|----------|----------|
| 部署辅助 | 生成部署脚本骨架、校验部署前置条件 | 新环境初始化、CI/CD 流水线对接 |
| 配置管理 | 读取/修改 RemnaWave 配置文件、参数校验 | 调整服务端口、日志级别、存储路径 |
| 数据转换 | 将外部数据格式（JSON/CSV/YAML）转换为 RemnaWave 所需结构 | 导入用户数据、迁移旧系统配置 |

### 1.2 不能做什么（明确限制）

- 不执行实际部署操作（不调用 Docker/K8s API）
- 不修改 RemnaWave 核心二进制文件
- 不处理加密数据的解密（仅支持明文配置）
- 不提供 GUI 界面，仅命令行交互

### 1.3 适用对象

- RemnaWave 项目的运维人员
- 需要批量配置管理的开发工程师
- 进行数据迁移的项目实施人员


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
