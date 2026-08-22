---
slug: claude-mem
name: claude-mem
displayName: 会话记忆 跨期上下文 持久化
description: 跨会话捕获、压缩并检索代理对话中的关键信息，实现上下文持久化。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 林默
agent_created: true
trigger_words: ["claude-mem", "会话记忆", "上下文持久化", "记忆压缩", "跨期上下文", "记忆检索", "会话续接"]
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# claude-mem — 会话记忆与跨期上下文持久化

## 一、能力边界（一页纸速查卡）

### 能做什么

| 能力项 | 说明 | 适用场景 |
|--------|------|----------|
| 关键信息捕获 | 从当前会话中提取用户偏好、项目约束、决策记录 | 长对话中需要记住重要约定时 |
| 记忆压缩 | 将冗长对话压缩为结构化摘要，保留核心事实 | 对话超过上下文窗口限制前 |
| 跨期检索 | 在新会话中按关键词或时间范围检索历史记忆 | 新会话需要沿用旧会话上下文时 |
| 上下文续接 | 将压缩后的记忆注入新会话，实现无缝衔接 | 多轮次、多会话的复杂任务 |

### 不能做什么

| 限制项 | 说明 |
|--------|------|
| 不存储原始对话全文 | 仅保存压缩后的结构化记忆，原始内容不保留 |
| 不自动跨设备同步 | 记忆文件仅存在于本地指定目录，需手动迁移 |
| 不处理敏感信息 | 密码、密钥、个人隐私等敏感字段需用户自行过滤 |
| 不保证语义完整性 | 压缩过程可能丢失非关键细节，重要信息需用户确认 |

### 适用对象

- 需要多轮次协作的复杂项目（如代码重构、文档撰写）
- 对话频繁中断、需要恢复上下文的场景
- 团队协作中需要共享会话背景的成员

---

## 二、触发方式

### 触发词

直接使用以下任一词汇即可激活本 Skill：

- `claude-mem`
- `会话记忆`
- `上下文持久化`
- `记忆压缩`
- `跨期上下文`
- `记忆检索`
- `会话续接`

### 场景映射表

| 用户说（大白话） | 实际意图 | 本 Skill 动作 |
|------------------|----------|---------------|
| "帮我记住这个项目的端口号是 8080" | 捕获关键信息 | 提取并存入记忆文件 |
| "上次我们讨论的数据库方案是什么来着？" | 检索历史记忆 | 按关键词搜索记忆文件 |
| "这个对话太长了，我们换个会话继续" | 压缩并续接 | 压缩当前上下文，生成摘要 |
| "新会话里把之前的背景同步一下" | 跨期注入 | 将记忆摘要注入新会话 |

---

## 三、标准流程

### 前置条件

1. 当前工作目录可写（用于创建 `.claude-mem/` 记忆目录）
2. 待处理的会话内容已完整呈现（无截断）
3. 用户已确认无敏感信息需要排除

### 执行步骤

#### 步骤 1：初始化记忆目录

```bash
mkdir -p .claude-mem
touch .claude-mem/index.json
```

`index.json` 为记忆索引文件，结构如下：

```json
{
  "version": "1.0",
  "sessions": [],
  "last_updated": "2025-01-01T00:00:00Z"
}
```

#### 步骤 2：捕获关键信息

从当前会话中提取以下类别的信息：

| 信息类别 | 提取规则 | 示例 |
|----------|----------|------|
| 项目约束 | 明确的限制条件、边界值 | "端口固定为 8080，不可更改" |
| 决策记录 | 已确认的选择及理由 | "选用 PostgreSQL，因团队熟悉" |
| 用户偏好 | 重复出现的表达习惯 | "代码注释用中文" |
| 待办事项 | 明确承诺但未完成的任务 | "下周提交 API 文档" |

#### 步骤 3：压缩与存储

将提取的信息按以下模板压缩：

```yaml
session_id: "20250101-001"
timestamp: "2025-01-01T10:30:00Z"
summary:
  project: "电商平台重构"
  decisions:
    - "数据库选用 PostgreSQL"
    - "前端框架锁定 Vue 3"
  constraints:
    - "端口固定 8080"
    - "兼容 Chrome 90+"
  todos:
    - "补充 API 文档"
  preferences:
    - "注释使用中文"
```

#### 步骤 4：检索与注入

新会话中触发检索时：

1. 读取 `.claude-mem/index.json` 获取会话列表
2. 按关键词或时间范围匹配目标会话
3. 将匹配的 `summary` 内容注入当前上下文
4. 输出格式为：

```yaml
[记忆恢复] 会话 20250101-001（2025-01-01）
项目：电商平台重构
关键决策：数据库选用 PostgreSQL；前端框架锁定 Vue 3
约束条件：端口固定 8080；兼容 Chrome 90+
待办事项：补充 API 文档
偏好设置：注释使用中文
```

### 输出规范

- 所有输出使用 YAML 格式，便于机器解析
- 时间戳统一使用 ISO 8601 格式
- 记忆文件编码统一为 UTF-8
- 单条记忆不超过 500 字，超出则拆分

---

## 四、置信度门控

当以下情况发生时，输出 `[需核实:字段名]` 占位符，**不编造**：

| 场景 | 处理方式 |
|------|----------|
| 用户提及的信息不完整 | 输出 `[需核实:端口号]` 并询问补充 |
| 历史记忆检索无匹配结果 | 输出 `[需核实:会话时间范围]` 并建议扩大搜索 |
| 压缩时存在歧义表述 | 输出 `[需核实:决策理由]` 并请用户确认 |
| 跨会话信息冲突 | 输出 `[需核实:冲突字段]` 并列出两个版本供选择 |

**示例：**

```
用户：上次说的那个端口是多少来着？
代理：检索到相关记忆，但端口号字段不完整。
[需核实:端口号] 请确认是否为 8080？
```

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| `MEM001` | 记忆目录不可写 | "无法创建记忆目录，请检查当前目录权限" | 1. 检查目录写权限 2. 手动创建 `.claude-mem/` 3. 重试 |
| `MEM002` | 索引文件损坏 | "记忆索引文件格式错误，尝试重建" | 1. 备份原文件 2. 删除 `index.json` 3. 重新初始化 |
| `MEM003` | 检索无结果 | "未找到匹配的记忆条目" | 1. 检查关键词拼写 2. 扩大时间范围 3. 确认记忆是否已存储 |
| `MEM004` | 压缩超限 | "单条记忆超过 500 字限制" | 1. 拆分记忆为多条 2. 精简表述 3. 重新压缩 |
| `MEM005` | 敏感信息检测 | "检测到疑似敏感字段，已跳过存储" | 1. 手动过滤敏感内容 2. 重新执行捕获 |

---

## 六、FAQ 反模式

### 常见坑 1：记忆文件无限膨胀

**反模式**：每次会话都追加完整摘要，不清理旧数据。

**正确做法**：定期合并重复记忆，删除超过 30 天且无引用的条目。

### 常见坑 2：过度压缩丢失关键信息

**反模式**：为追求精简，把决策理由、约束条件全部省略。

**正确做法**：保留"决策+理由"成对出现，约束条件完整保留。

### 常见坑 3：跨会话信息冲突不处理

**反模式**：新旧记忆冲突时，直接覆盖旧记录。

**正确做法**：标记冲突字段，输出两个版本供用户选择确认。

### 常见坑 4：敏感信息混入记忆

**反模式**：将密码、API Key 等直接存入记忆文件。

**正确做法**：存储前过滤敏感字段，或使用环境变量引用。

### 常见坑 5：检索关键词过于宽泛

**反模式**：使用"项目""方案"等泛词检索，返回大量无关结果。

**正确做法**：使用具体名词+限定词组合，如"数据库选型 2025年1月"。

---

## 七、渐进式披露

### 速查卡（30 秒上手）

```
1. 说"记住 XXX" → 捕获关键信息
2. 说"检索 XXX" → 搜索历史记忆
3. 说"压缩会话" → 生成摘要并存储
4. 新会话说"恢复上下文" → 注入历史记忆
```

### 新手路径（首次使用）

1. 阅读「能力边界」了解能做什么
2. 按「标准流程」步骤 1-2 完成首次捕获
3. 使用「触发方式」中的场景表找到对应指令
4. 遇到问题查「错误码体系」

### 进阶路径（熟练使用）

1. 自定义记忆模板，增加业务专属字段
2. 设置定期清理策略，控制记忆文件大小
3. 编写脚本批量导入历史会话记录
4. 结合外部知识库，扩展记忆检索范围

---

## 用户协议

使用本 Skill 即表示您同意以下条款：

1. **责任承担**：使用者自行承担使用本 Skill 产生的全部责任。因使用不当导致的记忆丢失、信息错误、数据泄露等后果，本 Skill 作者不承担任何责任。
2. **禁止反向工程**：不得对本 Skill 的提示词、处理逻辑进行反向工程、破解、篡改或二次分发。
3. **合规使用**：使用者需确保存储内容符合当地法律法规，不得存储违法、侵权或敏感信息。
4. **无担保声明**：本 Skill 按"现状"提供，不附带任何明示或暗示的担保。

<!-- user-agreement-injected -->

---

## 许可证（License）

本 Skill 采用 MIT 许可证发布。

### MIT License

```
MIT License

Copyright (c) 2025 林默

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
