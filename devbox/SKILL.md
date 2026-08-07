---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: devbox
name: devbox
displayName: 开发环境 可复现 团队协作
description: 基于Nix的团队开发环境管理器，一键复现统一工具链。
version: 1.0.6
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/devbox
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: LinguaForge
agent_created: true
trigger_words: ["devbox", "开发环境", "环境管理", "Nix环境", "依赖管理", "可复现环境"]

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

# Devbox Skill 文档

## 一、能力边界速查卡

### 1.1 能做什么（8项核心能力）

| 编号 | 能力项 | 说明 | 典型场景 |
|------|--------|------|----------|
| 1 | 环境初始化 | 在项目根目录生成 `devbox.json`，声明项目所需的语言、工具链与依赖包 | 新项目启动，替代手写 README 中的安装步骤 |
| 2 | 依赖声明与锁定 | 通过 `devbox add <pkg>@<version>` 精确锁定版本，生成 `devbox.lock` 保证可复现 | 团队多人协作，消除"在我机器上能跑"问题 |
| 3 | 环境激活与进入 | 通过 `devbox shell` 进入隔离 shell，或 `devbox run` 在环境中执行单条命令 | CI 流水线中执行测试，本地开发调试 |
| 4 | 全局工具管理 | 通过 `devbox global` 管理全局 CLI 工具（如 `gh`、`jq`），不污染系统 | 个人工作站统一工具版本 |
| 5 | 环境变量与钩子 | 在 `devbox.json` 的 `env` 字段声明环境变量，`hooks` 字段在安装/激活时自动执行脚本 | 自动设置 `PYTHONPATH`、初始化数据库、拉取子模块 |
| 6 | 镜像与缓存加速 | 支持配置 Nix 二进制缓存镜像（如内网源），加速依赖下载 | 企业内网、CI 构建加速 |
| 7 | 离线/受限网络部署 | 支持 `--offline` 模式、Nix store 导入导出、内网镜像源配置 | 隔离网络环境、离线机房部署 |
| 8 | 自检与诊断 | 提供 `devbox --selftest`、`devbox --version` 及详细日志输出 | 排查环境异常、确认安装正确性 |

### 1.2 不能做什么（明确边界）

| 编号 | 限制项 | 说明 |
|------|--------|------|
| 1 | 不替代 Docker | Devbox 管理的是 CLI 工具链和库依赖，不提供进程隔离、网络隔离或容器编排 |
| 2 | 不管理运行时服务 | 不负责启动/停止数据库服务、消息队列等常驻进程（可用 `hooks` 辅助，但不托管） |
| 3 | 不保证跨平台一致 | 依赖 Nix 生态，Windows 需通过 WSL2 使用，原生 Windows 支持有限 |
| 4 | 不处理非 Nix 包 | 只能安装 Nixpkgs 中存在的包，无法直接安装 pip/npm 包（但可声明 Python/Node 工具链后由包管理器安装） |
| 5 | 不自动同步团队配置 | 需要团队约定将 `devbox.json` 和 `devbox.lock` 提交到版本库，Devbox 本身不提供配置分发 |

### 1.3 适用对象

- **适用**：使用 Git 进行协作的软件团队、需要统一 CI 与本地环境的项目、频繁切换项目的自由开发者、需要离线部署的工业/内网环境。
- **不适用**：需要完整容器隔离的场景、Windows 原生开发（无 WSL2）、仅使用纯解释型语言且无系统依赖的小脚本项目。


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
