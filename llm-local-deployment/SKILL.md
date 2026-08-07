---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: llm-local-deployment
name: llm-local-deployment
displayName: 本地大模型 硬件适配 推理部署
description: 根据硬件与模型规格，生成可执行的本地推理部署方案与调优建议。
version: 1.1.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/llm-local-deployment
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 林栖
agent_created: true
trigger_words: ["llm-local-deployment", "本地部署", "大模型推理", "显存评估", "Ollama", "vLLM", "llama.cpp", "SGLang", "量化选型", "本地推理"]
---

> 📜 **用户协议（User Agreement）**
> 1. 本 Skill 仅供学习与参考用途。使用本 Skill 产生的任何结果，由使用者自行承担全部责任；本 Skill 不提供任何明示或暗示的保证。
> 2. 涉及法律、财务、税务、投资、医疗等专业决策时，请务必咨询持证专业人士。
> 3. 本代码受版权法保护，未经授权复制、反向工程或商业利用将被追究法律责任。
<!-- user-agreement-injected -->


> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->

> 本内容由 AI 生成，仅供学习参考 <!-- ai-generated-notice -->

# 本地大模型推理部署方案生成器

## 一、能力边界（一页纸速查卡）

| 维度 | 能做 | 不能做 |
|------|------|--------|
| 硬件评估 | 根据 GPU 显存、内存、模型参数量估算部署可行性 | 无法检测真实硬件状态，需用户提供准确型号 |
| 工具推荐 | 在 Ollama、vLLM、llama.cpp、SGLang 之间给出选型建议 | 不比较闭源商业框架（如 TensorRT-LLM 的专有优化） |
| 量化建议 | 给出 Q4_K_M、Q8_0、AWQ、GPTQ 等量化级别及显存估算 | 不保证量化后模型精度损失的具体数值 |
| 参数配置 | 生成 `--num-gpu`、`--tensor-parallel-size` 等推荐参数表 | 不覆盖分布式多节点部署的完整配置 |
| 命令生成 | 输出 Docker 与裸机两种启动命令 | 不处理操作系统差异（默认 Linux x86_64） |
| API 示例 | 生成 OpenAI 兼容的 curl 与 Python 调用代码 | 不包含鉴权、限流等生产级安全配置 |
| 故障排查 | 针对 OOM、加载失败、速度慢给出排查步骤 | 无法远程诊断，需用户提供日志 |

**适用对象**：具备基础 Linux 操作能力、拥有 NVIDIA GPU（或 Apple Silicon）、希望自行部署开源大模型的开发者或运维人员。


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
