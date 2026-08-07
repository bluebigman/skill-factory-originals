---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: hyperfine
name: hyperfine
displayName: 命令行基准测试 性能对比 耗时分析
description: 命令行工具性能基准测试，支持多命令对比、预热控制与多格式导出。
version: 1.0.4
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/hyperfine
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: LinguaForge
agent_created: true
trigger_words: ["hyperfine", "基准测试", "性能对比", "耗时分析", "benchmark", "命令行测速"]
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

# hyperfine 技能手册：命令行性能基准测试

## 一、能力边界（速查卡）

### 1.1 能做什么

| 能力项 | 说明 | 典型参数 |
|--------|------|----------|
| 单命令测速 | 测量单条命令的耗时分布 | `hyperfine 'sleep 0.1'` |
| 多命令对比 | 同时对比 2-5 条命令，输出相对速度比 | `hyperfine 'cmd1' 'cmd2' 'cmd3'` |
| 预热控制 | 排除冷启动、缓存、JIT 编译等干扰 | `--warmup 3` |
| 样本量自适应 | 根据稳定性自动调整运行次数 | `--min-runs 10 --max-runs 100` |
| 异常值剔除 | 自动识别并剔除系统抖动导致的异常耗时 | 默认开启，可用 `--ignore-failure` 调整 |
| 多格式导出 | 支持 JSON、Markdown、CSV、Plot 等格式 | `--export-json result.json` |
| 参数化扫描 | 对多组参数逐一测试 | `-P 'size 10 100 1000'` |
| 超时保护 | 防止命令挂起，自动终止 | `--time-limit 10` |

### 1.2 不能做什么

- 不能测量 GPU 利用率、内存带宽等硬件级指标
- 不能替代专业 profiling 工具（如 perf、valgrind）进行热点分析
- 不能对 GUI 应用或需要交互输入的命令进行测试
- 不能跨机器对比（结果受硬件、负载影响，仅限本机相对比较）

### 1.3 适用对象

- 开发者：评估脚本/命令的性能差异
- DevOps：验证部署脚本的耗时是否在可接受范围
- 技术写作者：为文档提供可复现的性能数据


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
