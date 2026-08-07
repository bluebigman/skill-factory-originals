---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: android-media-pack
name: android-media-pack
displayName: 媒体播放 迁移集成 调试优化
description: 面向AI编码助手的AndroidX Media3技能包，覆盖迁移、播放器UI、流媒体、DRM与广告集成。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/android-media-pack
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: media-toolkit-studio
agent_created: true
trigger_words: ["android-media-pack", "Media3", "ExoPlayer迁移", "Compose播放器", "流媒体播放", "DRM集成", "广告集成"]
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

# Android Media Pack — Skill 文档

## 1. 能力边界（一页纸速查卡）

### 1.1 能做清单

| 编号 | 能力项 | 说明 | 输入要求 |
|------|--------|------|----------|
| C1 | 迁移辅助 | 将 ExoPlayer 2.x 代码迁移到 Media3 1.10.1 | 提供原始代码片段或迁移范围描述 |
| C2 | Compose 播放器 UI 生成 | 生成基于 Jetpack Compose 的播放器界面代码 | 指定 UI 组件需求（如控制条、手势、全屏） |
| C3 | 流媒体配置 | 配置 HLS / DASH / SmoothStreaming 播放参数 | 提供流地址与格式类型 |
| C4 | DRM 集成方案 | 生成 Widevine 等 DRM 方案的接入代码 | 提供 DRM 方案类型与许可证服务器 URL |
| C5 | 广告集成指引 | 提供 IMA / 自定义广告 Server 的接入步骤 | 指定广告 SDK 版本与广告标签类型 |

### 1.2 不能做清单

| 编号 | 限制项 | 说明 |
|------|--------|------|
| L1 | 不执行代码 | 本 Skill 仅生成代码与配置建议，不负责编译、运行或调试 |
| L2 | 不保证兼容性 | 生成的代码需结合具体项目环境验证，不承诺与所有第三方库版本兼容 |
| L3 | 不提供安全审计 | 不负责 DRM 密钥管理、网络安全配置的全面审计 |
| L4 | 不替代官方文档 | 涉及 API 细节变更时，以 AndroidX Media3 官方发布说明为准 |

### 1.3 适用对象

- 正在将 ExoPlayer 2.x 项目迁移到 Media3 的 Android 开发者
- 需要在 Compose 中快速搭建播放器界面的团队
- 需要接入流媒体、DRM 或广告 SDK 的移动端工程师
- AI 编码助手（如 Copilot、Codex 等）作为技能插件调用


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
