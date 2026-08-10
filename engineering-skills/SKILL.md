---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: engineering-skills
name: engineering-skills
displayName: 工程实战 代码审查 部署运维
description: 为AI编码代理提供生产级工程技能，涵盖代码审查、测试、部署等最佳实践，直接提升代理的工程能力。
version: 1.0.1
rules_version: cpr-20260810-n301
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/engineering-skills
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 陈墨工
agent_created: true
trigger_words: ["engineering-skills", "代码审查", "测试", "部署", "工程实践", "代码质量", "CI/CD"]
---

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->


> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# engineering-skills 技能手册

## 一、能力边界速查卡

本技能面向**AI编码代理**（如 Codex、Copilot 等）及**使用代理的开发者**，提供一套可落地的工程实践指引。以下是能力边界一览：

| 维度 | 能做 | 不能做 |
|------|------|--------|
| 代码审查 | 识别逻辑缺陷、安全隐患、性能瓶颈、风格问题；给出修改建议 | 替代人工评审决策；自动修改代码（除非显式授权） |
| 测试 | 设计测试用例、生成测试代码、分析覆盖率报告 | 保证测试通过率；修复被测代码的 bug |
| 部署 | 生成部署脚本、检查配置项、梳理发布流程 | 直接操作生产环境；保证部署成功 |
| 文档 | 生成 README、API 文档、变更日志 | 保证文档与代码完全同步 |
| 输入处理 | 支持 http(s) URL、Markdown 文本、JSON/YAML 文件 | 处理二进制文件、图像内容 |

**适用对象**：使用 AI 编程助手的开发者、需要标准化工程流程的团队、希望提升代码质量的个人开发者。

**不适用场景**：需要人类判断的架构决策、涉及商业机密的代码审查、无明确输入格式的自由对话。

---

## 二、触发方式与场景映射

当出现以下情况时，本技能会自动激活：

| 触发词/短语 | 典型场景 | 代理行为 |
|-------------|----------|----------|
| "帮我审查这段代码" | 提交 PR 前自查 | 执行代码审查流程，输出问题清单 |
| "写个测试" | 为函数/模块补充测试 | 生成测试用例和测试代码 |
| "怎么部署？" | 准备上线 | 输出部署步骤和配置建议 |
| "检查一下这个 URL" | 分析远程文件 | 抓取内容并结构化处理 |
| "工程实践" | 询问最佳实践 | 给出对应场景的实践建议 |

**大白话映射**：
- "看看这代码有啥问题" → 代码审查流程
- "帮我测测这个函数" → 测试用例生成
- "这玩意儿怎么上线" → 部署流程梳理
- "这个链接里是啥" → URL 内容解析

---

## 三、标准工作流程

### 前置条件

1. 输入内容明确（代码片段、文件路径、URL 或 Markdown 文本）
2. 输出格式要求清晰（默认 Markdown，可指定 JSON）
3. 代理已获得必要的上下文（如项目结构、技术栈信息）

### 执行步骤

**步骤 1：输入解析**
- 识别输入类型：代码 / 文件 / URL / 文本
- 提取关键信息：语言、框架、业务逻辑、约束条件
- 若输入不明确，返回错误提示（见错误码表）

**步骤 2：按需处理**

| 任务类型 | 处理规则 | 输出结构 |
|----------|----------|----------|
| 代码审查 | 逐行检查 → 分类问题（严重/一般/建议）→ 给出修改建议 | 问题清单 + 优先级 + 示例修复 |
| 测试生成 | 分析函数签名 → 设计边界用例 → 生成测试代码 | 测试文件 + 用例说明 |
| 部署规划 | 梳理依赖 → 检查配置 → 列出步骤 | 部署清单 + 回滚方案 |
| URL 解析 | 抓取内容 → 提取正文 → 结构化输出 | 摘要 + 关键信息 + 来源标注 |

**步骤 3：置信度标注**
- 信息完整时：正常输出，不标注
- 信息缺失时：在对应字段标注 `[需核实:字段名]`
- 推测内容：标注 `[推测:内容]` 并说明依据

**步骤 4：输出与自查**
- 按约定格式整理结果
- 自查清单：
  - [ ] 字段完整性（无遗漏）
  - [ ] 格式正确性（符合 Markdown/JSON 规范）
  - [ ] 置信度标注（缺失信息已标注）
  - [ ] 无编造内容（所有信息有据可查）

**步骤 5：二次确认**
- 若存在歧义或关键信息缺失，主动向用户提问
- 示例："您提供的代码缺少错误处理部分，是否需要我补充相关建议？"

### 输出规范

默认输出 Markdown 格式，包含：
- 执行摘要（3-5 条要点）
- 详细内容（按任务类型组织）
- 置信度说明（如有）
- 后续建议（可选）

---

## 四、置信度门控机制

本技能遵循**"不编造"原则**，当信息不足时：

| 场景 | 处理方式 | 示例 |
|------|----------|------|
| 缺少函数签名 | 输出 `[需核实:函数签名]` | "该函数需要两个参数，但类型未明确 [需核实:参数类型]" |
| 依赖版本未知 | 标注 `[需核实:依赖版本]` | "建议使用 requests 库 [需核实:版本号]" |
| 部署环境不明 | 标注 `[需核实:目标环境]` | "部署步骤适用于 Linux 环境 [需核实:实际环境]" |
| 推测性建议 | 标注 `[推测:依据]` | "该问题可能是内存泄漏导致 [推测:根据代码模式判断]" |

**门控规则**：
1. 缺失字段必须标注，不得留空或跳过
2. 推测内容必须说明依据
3. 用户可要求补充信息后重新生成

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| E001 | 输入为空 | "未检测到输入内容，请提供代码、文件路径或 URL" | 重新输入有效内容 |
| E002 | 格式不支持 | "暂不支持该文件格式，支持 Markdown、JSON、YAML、文本" | 转换格式后重试 |
| E003 | URL 无法访问 | "无法访问该 URL，请检查链接是否有效" | 确认链接后重试 |
| E004 | 语言不支持 | "该编程语言不在支持列表中（支持 Python/JS/TS/Java/Go/Rust）" | 更换语言或手动处理 |
| E005 | 信息不足 | "缺少必要信息，无法完成处理" | 补充缺失信息后重试 |
| E006 | 处理超时 | "处理超时，请简化输入或分段处理" | 拆分输入后重试 |

---

## 六、FAQ 与反模式

### 常见坑

**坑 1：过度承诺**
- ❌ 反模式："这个测试保证 100% 通过"
- ✅ 正确做法："测试覆盖了主要边界情况，建议在 CI 中验证"

**坑 2：忽略上下文**
- ❌ 反模式：只看代码片段，忽略项目整体架构
- ✅ 正确做法：先了解项目结构、依赖关系，再给出建议

**坑 3：编造信息**
- ❌ 反模式：不确定时随意填写版本号或配置项
- ✅ 正确做法：标注 `[需核实]` 并说明原因

**坑 4：输出冗长**
- ❌ 反模式：输出 5000 字分析，核心问题淹没在细节中
- ✅ 正确做法：先给结论，再展开细节，用表格/列表组织

**坑 5：忽略安全**
- ❌ 反模式：建议使用 `eval()` 或硬编码密钥
- ✅ 正确做法：提示安全风险，推荐安全替代方案

### 反模式对照表

| 反模式 | 问题 | 替代方案 |
|--------|------|----------|
| "直接改代码" | 可能引入新问题 | 先给建议，确认后修改 |
| "保证部署成功" | 无法承诺外部因素 | 提供检查清单和回滚方案 |
| "所有情况都适用" | 忽略场景差异 | 分场景给出建议 |
| "跳过测试" | 增加回归风险 | 建议最小测试集 |

---

## 七、渐进式阅读路径

### 新手路径（5 分钟上手）

1. 阅读**能力边界速查卡**（第一节）
2. 查看**触发方式**（第二节），了解何时使用
3. 按**标准流程**（第三节）执行一次简单任务
4. 遇到问题查**错误码表**（第五节）

### 进阶路径（深入实践）

1. 完整阅读**标准工作流程**（第三节），理解每个步骤的细节
2. 学习**置信度门控**（第四节），掌握信息不足时的处理
3. 对照**FAQ 反模式**（第六节），避免常见错误
4. 根据实际场景调整输出格式，形成个人工作流

### 专家路径（定制优化）

1. 结合项目实际，定制代码审查规则
2. 建立团队级测试模板和部署清单
3. 将本技能与其他工具（CI/CD、代码托管平台）集成
4. 反馈使用体验，优化技能细节

---

## 八、输入输出示例

### 示例 1：代码审查

**输入**：
```python
def calculate_total(items):
    total = 0
    for item in items:
        total += item['price'] * item['quantity']
    return total
```

**输出**：
```markdown
## 代码审查结果

### 问题清单
| 优先级 | 问题 | 建议 |
|--------|------|------|
| 严重 | 未处理 items 为空的情况 | 添加空列表检查 |
| 一般 | 未处理 item 缺少 'price' 键的情况 | 使用 .get() 方法 |
| 建议 | 可使用 sum() 简化 | total = sum(item['price'] * item['quantity'] for item in items) |

### 修改建议
```python
def calculate_total(items):
    if not items:
        return 0
    return sum(item.get('price', 0) * item.get('quantity', 0) for item in items)
```

### 置信度说明
- 所有问题基于代码逻辑分析，置信度高
- [需核实:items 的数据结构] 假设为字典列表
```

### 示例 2：URL 解析

**输入**：`https://example.com/api/docs`

**输出**：
```markdown
## URL 内容解析

**来源**：https://example.com/api/docs
**抓取时间**：2026-08-10 14:30

### 内容摘要
- 文档主题：REST API 接口说明
- 包含 3 个主要端点：/users、/orders、/products
- 认证方式：Bearer Token

### 关键信息
| 端点 | 方法 | 说明 |
|------|------|------|
| /users | GET | 获取用户列表 |
| /orders | POST | 创建订单 |
| /products | GET | 获取商品信息 |

### 置信度说明
- 内容完整，置信度高
- [需核实:认证方式] 文档中未明确说明
```

---

## 九、批量处理与自定义格式

### 批量处理

支持一次处理多个输入：
- 多个文件路径（用逗号分隔）
- 多个 URL（每行一个）
- 混合输入（代码 + 文件 + URL）

**批量输出格式**：
```markdown
## 批量处理结果

### 任务 1：[输入描述]
[结果内容]

### 任务 2：[输入描述]
[结果内容]
```

### 自定义格式

可通过参数指定输出格式：
- `--format json`：输出 JSON 格式
- `--format table`：输出表格格式
- `--format concise`：输出精简版（仅结论）

**JSON 输出示例**：
```json
{
  "task": "code_review",
  "input": "calculate_total function",
  "issues": [
    {
      "severity": "critical",
      "description": "Empty list not handled",
      "suggestion": "Add empty check"
    }
  ],
  "confidence": 0.95
}
```

---

## 十、版本与更新

| 版本 | 日期 | 变更内容 |
|------|------|----------|
| 1.0.0 | 2026-08-10 | 初始版本，包含核心功能 |

**更新计划**：
- 支持更多编程语言
- 增加安全审查专项
- 集成更多 CI/CD 工具

---

## 用户协议

使用本 Skill 即表示您同意以下条款：

1. **责任承担**：使用者自行承担全部责任。本 Skill 提供的所有建议、代码示例和流程指引仅供参考，不构成任何形式的保证。因使用本 Skill 产生的任何直接或间接损失，作者不承担任何责任。

2. **禁止反向工程**：未经授权，不得对本 Skill 进行反向工程、反编译、破解或试图提取底层算法。

3. **合规使用**：使用者应确保使用本 Skill 的行为符合当地法律法规及所在组织的政策。

4. **内容免责**：本 Skill 生成的内容基于 AI 模型，可能存在错误或过时信息，使用者应自行验证关键信息。

5. **协议更新**：作者保留随时修改本协议的权利，修改后的协议将在本页面公布。

<!-- user-agreement-injected -->

---

## 许可证（License）

本 Skill 采用 MIT 许可证发布。

### MIT License

```
MIT License

Copyright (c) 2026 陈墨工

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

---

*本 Skill 由 AI 辅助生成，仅供参考。使用前请阅读相关文档。*
