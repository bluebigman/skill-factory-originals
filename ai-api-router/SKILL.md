---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: ai-api-router
name: ai_api_router
displayName: AI网关 模型路由 成本优化
description: 根据模型、预算、延迟需求，推荐并配置AI API中转服务，生成接入代码。
version: 1.0.1
rules_version: cpr-20260809-n251
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/ai-api-router
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: LinguaForge
agent_created: true
trigger_words: ["ai-api-router", "API中转", "模型路由", "AI网关", "模型代理", "API聚合"]
---

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->


> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# AI API 路由与中转配置助手

## 一、能力边界：一页纸速查卡

本 Skill 用于解决一个核心问题：**当你有多个 AI 模型供应商（如 OpenAI、Anthropic、国产模型等）或需要通过中转服务统一访问时，如何根据你的具体约束条件（预算、延迟、能力）选择最合适的路由方案，并生成可运行的接入代码。**

### 1.1 能做什么

| 序号 | 能力项 | 说明 |
|------|--------|------|
| 1 | 需求解析 | 将用户的自然语言描述（如"我要便宜点的"、"响应要快"）转化为结构化参数（模型、预算、延迟阈值） |
| 2 | 路由推荐 | 基于内置的模型能力矩阵与价格参考表，给出候选模型列表及推荐理由 |
| 3 | 配置生成 | 生成 OpenAI 兼容格式的 `base_url`、`api_key` 配置片段，以及 Python/curl 调用示例 |
| 4 | 成本估算 | 根据输入 token 量与输出 token 量，估算单次调用成本与月度开销 |
| 5 | 故障排查 | 针对常见的 401、429、超时等错误，给出诊断步骤与修正建议 |

### 1.2 不能做什么

| 序号 | 限制项 | 说明 |
|------|--------|------|
| 1 | 不提供真实密钥 | 无法获取或验证任何中转服务的实际 API Key，所有密钥需用户自行购买与管理 |
| 2 | 不保证服务可用性 | 中转服务的稳定性、速率限制、数据隐私政策由各服务商自行决定，本 Skill 不承担任何责任 |
| 3 | 不进行基准测试 | 延迟数据为经验参考值，实际表现受网络环境、服务商负载、模型版本影响，需用户实测 |
| 4 | 不处理非 API 类需求 | 如需要图形化界面工具、本地模型部署（Ollama 等），不在本 Skill 范围内 |

### 1.3 适用对象

- **个人开发者**：需要快速在多个模型间切换，不想维护多套 SDK 接入代码。
- **小型团队**：希望统一管理 API 调用，控制成本，但暂无能力自建网关。
- **技术评估人员**：在项目初期需要对比不同模型的性价比，做出技术选型。

## 二、触发方式与场景映射

当你的输入中包含以下关键词或意图时，本 Skill 将被激活：

| 触发词/场景 | 用户可能说的话（大白话） | 本 Skill 的响应动作 |
|-------------|--------------------------|----------------------|
| `ai-api-router` | "用 ai-api-router 帮我看看怎么接中转" | 进入标准流程，开始收集需求参数 |
| API中转 | "我想找个 API 中转，能同时用 GPT 和 Claude" | 解析模型偏好，推荐支持多模型的中转方案 |
| 模型路由 | "帮我做个模型路由，贵的模型只在必要时用" | 生成带条件判断的路由逻辑代码 |
| 成本优化 | "现在太贵了，想换便宜点的模型" | 根据预算约束，推荐低价模型并估算节省幅度 |
| 延迟敏感 | "我要做实时对话，响应必须快" | 优先推荐低延迟模型，并给出超时配置建议 |

## 三、标准流程：从需求到代码

### 3.1 前置条件

在开始之前，请确认你已具备以下信息（如缺失，本 Skill 会使用 `[需核实:字段]` 占位）：

| 参数 | 是否必填 | 示例值 | 缺失时的处理 |
|------|----------|--------|--------------|
| 模型偏好 | 否 | GPT-4o, Claude 3.5 Sonnet | 默认推荐通用均衡型模型 |
| 月预算上限 | 否 | 50 美元 | 默认不设上限，但会给出成本预警 |
| 延迟要求 | 否 | < 2 秒 | 默认标准延迟（< 5 秒） |
| 调用量预估 | 否 | 10 万 token/天 | 默认 1 万 token/天 |
| 中转服务商 | 否 | 无（需推荐） | 根据其他条件推荐 |

### 3.2 执行步骤

**步骤 1：需求结构化**

将你的输入转化为以下 JSON 结构：

```json
{
  "model_preference": ["gpt-4o", "claude-3-5-sonnet"],
  "budget_monthly_usd": 50,
  "latency_sla_seconds": 2,
  "daily_token_volume": 100000,
  "provider_constraint": null
}
```

**步骤 2：模型匹配与路由推荐**

根据内置参考矩阵（见附录 A），筛选出满足条件的模型。推荐逻辑如下：

1. 若指定了 `model_preference`，则直接使用该列表，跳过筛选。
2. 若未指定，则按以下优先级排序：
   - 延迟敏感场景：`gpt-4o-mini` > `claude-3-haiku` > `gemini-1.5-flash`
   - 成本敏感场景：`deepseek-chat` > `gpt-4o-mini` > `claude-3-haiku`
   - 能力优先场景：`gpt-4o` > `claude-3-5-sonnet` > `gemini-1.5-pro`

**步骤 3：生成配置与代码**

输出包含三部分内容：

1. **环境变量配置**（`.env` 文件示例）：

```bash
# 中转服务统一入口
AI_GATEWAY_BASE_URL=https://your-proxy.example.com/v1
AI_GATEWAY_API_KEY=sk-your-key-here

# 默认模型
AI_DEFAULT_MODEL=gpt-4o-mini
```

2. **Python 接入代码**（使用 `openai` SDK，兼容中转服务）：

```python
import os
from openai import OpenAI

client = OpenAI(
    base_url=os.getenv("AI_GATEWAY_BASE_URL"),
    api_key=os.getenv("AI_GATEWAY_API_KEY"),
    timeout=30.0,  # 根据延迟要求调整
)

def chat_with_router(messages, model=None):
    """统一入口，支持模型路由"""
    selected_model = model or os.getenv("AI_DEFAULT_MODEL")
    
    try:
        response = client.chat.completions.create(
            model=selected_model,
            messages=messages,
            temperature=0.7,
        )
        return response.choices[0].message.content
    except Exception as e:
        # 错误处理见第五节
        raise RuntimeError(f"API call failed: {e}") from e
```

3. **成本估算表**：

| 模型 | 输入价格 ($/1K tokens) | 输出价格 ($/1K tokens) | 日成本估算 (10万token, 1:3 输入输出比) |
|------|------------------------|------------------------|----------------------------------------|
| gpt-4o-mini | 0.15 | 0.60 | $0.15 * 25 + $0.60 * 75 = $48.75 |
| deepseek-chat | 0.14 | 0.28 | $0.14 * 25 + $0.28 * 75 = $24.50 |
| claude-3-haiku | 0.25 | 1.25 | $0.25 * 25 + $1.25 * 75 = $100.00 |

**步骤 4：输出规范**

最终输出必须包含以下章节（Markdown 格式）：

1. **推荐方案摘要**：一段话说明推荐了哪个模型、为什么。
2. **配置清单**：环境变量、依赖安装命令（`pip install openai`）。
3. **代码示例**：可直接运行的 Python 脚本。
4. **成本明细**：基于用户提供的调用量，给出日/月成本估算。
5. **注意事项**：包括限流、重试策略、数据隐私提醒。

## 四、置信度门控

当以下信息缺失时，本 Skill 不会编造，而是输出 `[需核实:字段]` 占位符，并提示用户补充：

| 缺失信息 | 占位符示例 | 后续建议 |
|----------|------------|----------|
| 中转服务商的实际 base_url | `[需核实:base_url]` | 请查阅你的服务商文档，通常形如 `https://api.xxx.com/v1` |
| 实际 API Key | `[需核实:api_key]` | 请勿在对话中明文传输密钥，建议使用环境变量 |
| 模型价格 | `[需核实:model_price]` | 价格表更新频繁，请以服务商官网为准 |
| 延迟实测数据 | `[需核实:latency_measured]` | 建议运行 `curl -w` 进行实测 |

**禁止行为**：不得使用"大约"、"估计"等模糊词汇替代占位符。必须明确标注信息缺口。

## 五、错误码体系

| 错误码 | 常见触发场景 | 用户看到的提示话术 | 修正步骤 |
|--------|--------------|--------------------|----------|
| `E401` | API Key 无效或未配置 | "认证失败：请检查你的 API Key 是否正确，或是否已设置环境变量。" | 1. 确认 `.env` 文件已加载；2. 检查 Key 是否有前缀 `sk-`；3. 联系服务商确认 Key 状态 |
| `E429` | 请求频率超限 | "请求过于频繁：已触发速率限制。建议降低并发或增加重试间隔。" | 1. 在代码中加入 `time.sleep(1)` 或使用指数退避；2. 检查是否与其他服务共享同一 Key |
| `E404` | 模型名称不存在 | "模型不存在：请确认模型 ID 拼写正确，且你的账户有权限访问该模型。" | 1. 对照服务商文档核对模型 ID；2. 尝试使用 `gpt-4o-mini` 等通用 ID |
| `E500` | 服务商内部错误 | "服务端异常：中转服务暂时不可用，请稍后重试。" | 1. 等待 30 秒后重试；2. 检查服务商状态页；3. 切换备用模型 |
| `ETIMEOUT` | 请求超时 | "请求超时：模型响应时间超过设定阈值。可尝试增大 timeout 参数或更换低延迟模型。" | 1. 将 `timeout` 从 30 提升到 60；2. 更换为 `gpt-4o-mini` 等轻量模型 |

## 六、FAQ 与反模式

### 6.1 常见坑

| 坑编号 | 错误做法（反模式） | 正确做法 |
|--------|--------------------|----------|
| 1 | **密钥硬编码**：将 API Key 直接写在代码里，并提交到 Git 仓库 | 使用环境变量或 `.env` 文件，并在 `.gitignore` 中排除 |
| 2 | **忽略限流**：在循环中无间隔调用 API，导致 429 错误 | 使用 `tenacity` 库实现重试，或手动加入 `time.sleep(0.5)` |
| 3 | **模型 ID 写死**：在代码中硬编码模型名称，切换时需改代码 | 将模型名放入配置文件中，或使用环境变量 `AI_DEFAULT_MODEL` |
| 4 | **不做成本监控**：上线后从不查看账单，月底收到巨额账单 | 设置月度预算告警，使用服务商的用量统计 API 定期拉取 |
| 5 | **忽略数据隐私**：将敏感数据发送给不支持数据隔离的中转服务 | 阅读服务商隐私政策，确认数据是否用于训练；必要时使用本地模型 |

### 6.2 反模式对照表

| 反模式 | 典型表现 | 后果 | 替代方案 |
|--------|----------|------|----------|
| 万能模型崇拜 | 所有请求都用 `gpt-4o`，不考虑成本 | 月度成本超支 5-10 倍 | 按任务复杂度分级路由：简单任务用 mini 模型，复杂任务用旗舰模型 |
| 延迟焦虑 | 为了降低 100ms 延迟，选择最贵的模型 | 成本上升但用户体验无感 | 先实测，确认瓶颈在 API 延迟还是网络延迟；考虑使用流式输出 |
| 配置散乱 | 每个脚本单独配置 base_url 和 key | 维护困难，密钥泄露风险高 | 统一使用 `.env` 文件 + `python-dotenv` 加载 |

## 七、渐进式披露：分层次阅读路径

### 7.1 速查卡（30 秒上手）

1. 告诉我你的**模型偏好**、**月预算**、**延迟要求**。
2. 我会输出一个 `.env` 配置模板 + 一段 Python 调用代码。
3. 复制代码，安装依赖（`pip install openai python-dotenv`），填入你的 Key，即可运行。

### 7.2 新手路径（首次使用）

- 阅读 **第三节 标准流程**，了解完整步骤。
- 重点关注 **步骤 3** 的代码示例，直接复制运行。
- 遇到错误时，对照 **第五节 错误码体系** 排查。

### 7.3 进阶路径（深度定制）

- 阅读 **附录 A：模型参考矩阵**，了解各模型特性。
- 参考 **6.2 反模式对照表**，设计自己的路由策略。
- 如需多模型自动切换，可基于 `步骤 3` 的代码扩展，增加条件判断逻辑（如：当 `gpt-4o` 超时则降级到 `gpt-4o-mini`）。

---

## 附录 A：模型参考矩阵（经验值，非实时数据）

| 模型 ID | 相对速度 | 相对成本 | 能力等级 | 典型场景 |
|---------|----------|----------|----------|----------|
| `gpt-4o` | 中 | 高 | 旗舰 | 复杂推理、代码生成 |
| `gpt-4o-mini` | 快 | 低 | 均衡 | 通用对话、文本分类 |
| `claude-3-5-sonnet` | 中 | 高 | 旗舰 | 长文档分析、复杂指令 |
| `claude-3-haiku` | 快 | 中 | 均衡 | 实时交互、简单问答 |
| `gemini-1.5-pro` | 中 | 高 | 旗舰 | 多模态理解 |
| `gemini-1.5-flash` | 快 | 低 | 均衡 | 高吞吐、低延迟 |
| `deepseek-chat` | 快 | 极低 | 均衡 | 成本敏感、大规模调用 |

> **注意**：以上数据为 2026 年 8 月经验参考值，实际价格与性能请以各服务商官方文档为准。本 Skill 不保证数据的实时准确性。

---

## 用户协议

<!-- user-agreement-injected -->

**使用本 Skill 即表示您同意以下条款：**

1. **责任自负**：您使用本 Skill 生成的配置、代码、推荐方案所产生的任何后果（包括但不限于成本超支、服务中断、数据泄露、法律纠纷），均由您自行承担全部责任。本 Skill 及其作者不承担任何直接或间接损失。

2. **禁止反向工程**：您不得对本 Skill 的提示词、内部逻辑、评分机制进行反向工程、破解、提取或二次分发。本 Skill 的原创表达受版权保护。

3. **信息真实性**：您保证提供的需求信息（预算、调用量、合规要求）真实有效。因虚假信息导致的推荐偏差，本 Skill 不承担责任。

4. **第三方服务**：本 Skill 推荐的中转服务均为第三方独立运营，与本 Skill 无任何从属或合作关系。您与第三方之间的交易、纠纷，与本 Skill 无关。

5. **变更与终止**：本 Skill 可能随时更新或下线，恕不另行通知。建议您在使用关键业务前，自行备份相关配置。

---

## 许可证（License）

<!-- professional-license-embedded -->

**MIT License**

Copyright (c) 2026 原创作者（自持版权）

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

---

*本 Skill 由 AI 辅助生成，仅供参考。使用前请阅读相关文档。*
