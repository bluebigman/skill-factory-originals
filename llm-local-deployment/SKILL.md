---
> 本内容由 AI 生成，仅供学习参考（《人工智能生成合成内容标识办法》显式标识）。
<!-- ai-generated-notice -->
slug: llm-local-deployment
name: llm-local-deployment
displayName: 本地大模型部署指南
description: 根据硬件配置（GPU型号、显存、内存）和模型需求（如70B、DeepSeek），生成本地推理部署方案，包括工具选择、参数配置和性能优化建议。
version: 1.1.0
# === 法律合规声明（自动生成，请勿删除） ===
license: MIT
source_project: original
source_url: https://skillhub.cn
source_license_url: 
copyright_holder: Skill Factory
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。本Skill为AI辅助生成内容。
author: skill-factory-auto
agent_created: true
trigger_words:
  - "llm-local-deployment"
  - "本地部署大模型"
  - "大模型本地跑"
  - "显卡显存不够"
  - "离线跑模型"
  - "本地推理"
---

> 📜 **用户协议（User Agreement）**
> 1. 本 Skill 仅供学习与参考用途。使用本 Skill 产生的任何结果，由使用者自行承担全部责任；本 Skill 不提供任何明示或暗示的保证。
> 2. 涉及法律、财务、税务、投资、医疗等专业决策时，请务必咨询持证专业人士。
> 3. 本代码受版权法保护，未经授权复制、反向工程或商业利用将被追究法律责任。
<!-- user-agreement-injected -->


> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->

# 本地大模型部署指南

> 根据硬件配置（GPU型号、显存、内存）和模型需求（如70B、DeepSeek），生成本地推理部署方案，包括工具选择、参数配置和性能优化建议。

## 一、能力边界（一页纸速查卡）

### 适用对象（谁适合用）
| 用户类型 | 典型场景 | 是否适用 |
|---|---|---|
| 个人开发者 | 在本地跑 7B~14B 模型做原型验证 | ✅ 完全适用 |
| 中小企业 | 私有化部署 32B~70B 模型，数据不出内网 | ✅ 适用（需提供 GPU 型号与显存） |
| 高校实验室 | 多卡并行推理、微调后部署 | ✅ 适用（需说明卡间通信方式） |
| 纯 CPU 用户 | 无 NVIDIA GPU，仅用 CPU 推理 | ⚠️ 仅提供 CPU 推理方案（速度慢，建议量化） |
| Mac 用户 | Apple Silicon 芯片 | ⚠️ 仅提供 MPS 后端方案，不支持 CUDA |
| 云端用户 | 使用云 GPU 实例 | ✅ 适用（需提供实例类型） |

### 能做（7项核心能力）
1. **工具选型**：根据显存/内存/模型大小，推荐 Ollama、vLLM、llama.cpp、SGLang 等推理框架
2. **量化方案**：给出 Q4_K_M、Q8_0、AWQ、GPTQ 等量化级别建议，并估算显存占用
3. **参数配置**：生成 `context_length`、`gpu_memory_utilization`、`max_batch_size` 等关键参数推荐值
4. **性能优化**：提供吞吐量、延迟、并发数的调优建议（如 `--num-gpu`、`--tensor-parallel-size`）
5. **启动命令**：输出可直接执行的部署命令（含 Docker 或裸机两种方式）
6. **API 接入**：生成 OpenAI 兼容的 API 调用示例（curl / Python）
7. **故障排查**：针对显存不足（OOM）、模型加载失败、推理速度慢等问题给出排查步骤

### 不做（5项边界声明）
- **不做**：不提供模型训练、微调、LoRA 适配服务（仅部署推理）
- **不做**：不处理非 NVIDIA GPU（AMD、Intel 等）的底层驱动配置
- **不做**：不保证模型输出内容的准确性，涉及事实性内容需人工复核
- **不做**：不提供分布式多机部署方案（单机多卡可支持）
- **不做**：不访问网络下载模型，用户需自行准备模型文件或提供 HuggingFace 模型 ID

> 如果用户的需求超出以上边界，明确告知无法处理并说明原因，不强行执行。

## 二、触发方式（说大白话就能用）

### 触发词表（10类场景）
| 触发词 | 场景类型 |
|---|---|
| 本地部署大模型 | 核心场景 |
| 大模型本地跑 | 核心场景 |
| 显卡显存不够 | 问题诊断 |
| 离线跑模型 | 核心场景 |
| 本地推理 | 核心场景 |
| GPU部署 | 核心场景 |
| 量化模型 | 参数配置 |
| Ollama部署 | 工具选型 |
| vLLM部署 | 工具选型 |
| 模型跑不动 | 问题诊断 |

### 大白话触发示例（用户原话 → 触发动作）
| 用户可能会说 | 触发动作 |
|---|---|
| "我想在本地跑个 7B 的模型，有什么推荐？" | 启动部署方案生成，收集 GPU 型号与显存 |
| "我的 4090 跑 70B 模型显存不够怎么办？" | 启动量化方案推荐，计算显存需求 |
| "公司内网要部署一个 DeepSeek，怎么搞？" | 启动私有化部署方案，收集硬件信息 |
| "Ollama 和 vLLM 哪个适合我？" | 启动工具对比分析，根据场景推荐 |
| "模型加载总是 OOM 报错" | 启动故障排查流程，检查显存配置 |
| "怎么让推理速度更快？" | 启动性能优化建议，调整批处理与量化参数 |

## 三、标准流程（5分钟上手路径）

### Step 1: 收集最小信息集
向用户确认以下关键信息（缺失则引导补采，不臆测）：
- **硬件配置**：GPU 型号、显存大小、内存大小、CPU 核数
- **模型需求**：模型名称/参数量（如 7B、13B、70B）、是否需量化
- **部署场景**：单机单卡 / 单机多卡、并发请求量预估、是否需要 API 服务

### Step 2: 执行核心流程
1. **硬件评估**：根据 GPU 显存与模型大小，计算是否满足部署条件
   - 公式：所需显存 ≈ 模型大小(GB) × 1.2（含 KV Cache 与激活）
   - 例：7B 模型 FP16 约 14GB，推荐 24GB 显存；Q4 量化后约 4.5GB，推荐 8GB 显存
2. **工具选型**：
   - 显存 ≤ 8GB：推荐 llama.cpp + GGUF 量化
   - 显存 8~24GB：推荐 Ollama（简单）或 vLLM（高性能）
   - 显存 ≥ 24GB 或多卡：推荐 vLLM + tensor-parallel
3. **参数配置**：生成推荐参数表（见第六节）
4. **生成部署命令**：输出可直接执行的命令（含 Docker 或裸机）
5. **API 接入示例**：提供 curl 与 Python 调用示例

### Step 3: 输出与校验
1. 输出部署方案文档，包含：硬件评估结论、工具推荐、启动命令、参数配置表、API 示例
2. 自查：显存计算是否准确、命令是否完整、参数是否合理
3. 有疑问时向用户二次确认（如显存型号不确定时）

## 四、异常处理（错误码体系）

| 错误码 | 场景 | 标准化话术 | 修正步骤 |
|---|---|---|---|
| E001 | 未提供 GPU 型号 | "请提供 GPU 型号（如 RTX 4090、A100），否则无法估算显存。" | 引导用户运行 `nvidia-smi` 查看显卡信息 |
| E002 | 显存不足 | "当前显存不足以运行该模型，建议量化或更换更小模型。" | 给出量化方案（Q4_K_M）或推荐 7B→3B 替代模型 |
| E003 | 模型文件缺失 | "未找到模型文件，请确认路径或提供 HuggingFace 模型 ID。" | 给出 `huggingface-cli download` 命令示例 |
| E004 | 超出能力边界 | "这超出了本工具的能力范围（如多机分布式），建议咨询专业团队。" | 提供替代方案（如云服务） |
| E005 | 推理速度过慢 | "当前配置推理速度低于预期，建议调整批处理大小或量化级别。" | 给出 `--max-batch-size` 与量化调整建议 |
| E006 | 端口冲突 | "默认端口 8000 被占用，请更换端口。" | 给出 `--port 8001` 修改命令 |

## 五、常见问题（FAQ 速查）

### Q1: 7B 模型需要多大显存？
- FP16 约 14GB，Q4 量化后约 4.5GB。推荐 8GB 以上显存运行量化版。

### Q2: Ollama 和 vLLM 有什么区别？
- Ollama：简单易用，适合个人开发，支持 CPU/GPU 混合推理。
- vLLM：高吞吐、低延迟，适合生产环境，支持 PagedAttention 优化。

### Q3: 模型加载时 OOM 怎么办？
- 降低 `gpu_memory_utilization`（如 0.9→0.7），或使用量化模型，或减少 `max-batch-size`。

### Q4: 支持 Mac 吗？
- 支持 Apple Silicon（MPS 后端），但速度较慢，建议使用 7B 以下量化模型。

### Q5: 如何让推理速度更快？
- 使用 vLLM + 增大 `max-batch-size` + 开启 `--enable-prefix-caching`。

### Q6: 模型输出质量差怎么办？
- 调整 `temperature`（0.1~0.3 更稳定）、`top_p`（0.9），或更换更大模型。

## 六、进阶用法（深度按需）

### 6.1 参数默认值表与调整指引
| 参数名 | 默认值 | 适用场景 | 调整建议 |
|---|---|---|---|
| `temperature` | 0.7 | 通用对话 | 代码生成建议 0.1~0.2，创意写作可 0.8~1.0 |
| `top_p` | 0.9 | 通用对话 | 需要更确定性输出时降至 0.7 |
| `max_tokens` | 2048 | 通用 | 长文档生成可调至 4096，需注意显存占用 |
| `gpu_memory_utilization` | 0.9 | vLLM | 显存不足时降至 0.7~0.8 |
| `max_batch_size` | 256 | vLLM | 高并发场景可调至 512，但会增加显存压力 |
| `context_length` | 4096 | 通用 | 长上下文场景可调至 8192，需确认模型支持 |
| `quantization` | Q4_K_M | 显存受限 | 显存充足时用 Q8_0 或 FP16 提升精度 |

### 6.2 高级场景：多卡并行部署

## 失败处理
- 输入不符合预期 → 返回错误说明与正确的输入格式示例
- 执行中异常 → 保留中间结果，报告失败原因与已处理进度
- 依赖缺失 → 给出安装命令并重试一次

## 前置条件
- 无特殊环境要求

## 执行步骤
1. 收集用户输入并确认格式
2. 按功能逻辑处理输入内容
3. 生成结果并校验完整性

## 输出
- 结构化文本结果，附处理说明

## 许可证（License）

```text
MIT License

Copyright (c) 2026 Skill Factory

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

```
<!-- professional-license-embedded -->

## 稳定性保障

- **超时控制**：单条处理设置上限，超时自动跳过并记入失败明细，避免整批卡死。
- **重试策略**：可恢复类错误（临时占用、瞬时 IO 失败）自动重试 3 次，间隔递增。
- **降级方案**：高级解析失败时自动回退到基础解析模式，保证有可用输出而非直接报错。
- **幂等性**：重复执行同一批输入结果一致，不会产生重复追加。

## FAQ 与反模式

**Q：可以直接对原始文件覆盖写入吗？**
A：不建议。默认输出到独立文件，保留原始数据是可回溯的前提。

**Q：处理到一半失败了怎么办？**
A：已完成部分的输出有效，查看失败明细后只重跑失败项即可，无需整批重来。

**反模式 ①**：不做试运行直接批量处理全量数据 —— 参数配错会一次性污染全部输出。

**反模式 ②**：忽略失败明细只看成功数 —— 静默跳过的条目会造成数据缺口。

**反模式 ③**：把工具输出直接作为最终结论 —— 关键字段务必人工抽检。

## 安全声明

- 全流程本地执行，不上传任何用户数据到第三方服务。
- 不读取与任务无关的目录，不写入系统目录。
- 处理含个人信息的数据时，请自行遵守《个人信息保护法》等相关法规。
- 本 Skill 代码由 AI 辅助生成并经自检验证，以 MIT 协议开源，使用者自负使用后果。
