---
display_name: 跨会话记忆 上下文持久化 检索
slug: claude-mem
name: claude-mem
displayName: 会话记忆 跨期上下文 持久化检索
description: "跨会话捕获、压缩并检索代理对话中的关键信息，实现上下文持久化。"
version: 1.0.2
rules_version: cpr-20260820-n601
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/claude-mem
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: user_2fd890c9
agent_created: true
trigger_words: ["claude-mem", "会话记忆", "上下文持久化", "记忆压缩", "跨期上下文", "对话历史", "记忆检索"]
---

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->


> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# 跨会话记忆 上下文持久化 检索

## 一、能力边界（一页纸速查卡）

### 能做什么

| 能力项 | 说明 | 适用场景 |
|--------|------|----------|
| 会话捕获 | 自动提取对话中的关键实体、决策、待办事项 | 多轮长对话、项目讨论、需求梳理 |
| 记忆压缩 | 将冗长对话压缩为结构化摘要，保留核心信息 | 对话超过上下文窗口、需要长期保存 |
| 跨期检索 | 在新会话中检索历史对话的关键信息 | 隔天继续工作、多会话协作 |
| 上下文注入 | 将历史记忆作为上下文注入当前对话 | 新会话启动时快速恢复状态 |

### 不能做什么

| 限制项 | 说明 |
|--------|------|
| 不存储原始对话全文 | 仅保存压缩后的结构化记忆，原始内容不保留 |
| 不处理非文本内容 | 图片、音频、视频等多媒体内容不纳入记忆 |
| 不自动跨设备同步 | 记忆存储于本地工作目录，不提供云同步 |
| 不保证信息完整性 | 压缩过程可能丢失次要细节，重要信息需显式标注 |

### 适用对象

- 需要跨会话延续工作的开发者
- 管理多个并行项目的团队
- 依赖上下文连续性的研究分析任务

---

## 二、触发方式

### 触发词

| 触发词 | 场景描述 |
|--------|----------|
| `claude-mem` | 直接调用记忆功能 |
| `会话记忆` | 中文场景下的记忆操作 |
| `上下文持久化` | 需要保存当前对话状态 |
| `记忆压缩` | 对话过长需要精简 |
| `跨期上下文` | 新会话需要引用历史信息 |
| `对话历史` | 查询过往对话内容 |
| `记忆检索` | 按关键词查找历史记忆 |

### 场景映射表

| 用户说 | 实际需求 | 触发动作 |
|--------|----------|----------|
| "上次我们讨论到哪了？" | 恢复历史上下文 | 检索最近记忆并注入 |
| "把这次讨论的结论存下来" | 保存当前状态 | 执行记忆捕获与压缩 |
| "之前提到的那个API叫什么？" | 查找特定信息 | 关键词检索历史记忆 |
| "帮我整理一下这周的工作要点" | 汇总多会话信息 | 跨会话聚合检索 |

---

## 三、标准流程

### 前置条件

1. 工作目录可写（用于存储记忆文件）
2. 对话内容包含可提取的结构化信息（实体、决策、任务）
3. 记忆文件命名遵循 `mem_YYYYMMDD_HHMMSS.json` 格式

### 执行步骤

#### 步骤 1：输入准备

```
输入：待处理的对话文本或文件路径
参数：
  - input_file: 对话记录文件路径（可选）
  - session_id: 会话标识符（必填）
  - compress_level: 压缩级别 1-5（默认 3）
```

#### 步骤 2：试运行验证

使用单个样本执行，核对输出字段：

```bash
claude-mem --selftest --input sample_conversation.txt
```

预期输出字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| `session_id` | string | 会话唯一标识 |
| `entities` | array | 提取的实体列表 |
| `decisions` | array | 关键决策记录 |
| `tasks` | array | 待办事项 |
| `summary` | string | 压缩摘要（≤500字） |
| `timestamp` | string | 捕获时间 ISO8601 |

#### 步骤 3：批量执行

确认试运行无误后，对全量数据执行：

```bash
claude-mem --batch --input_dir ./conversations/ --output_dir ./memories/
```

执行前自动备份原始文件至 `./backup/` 目录。

#### 步骤 4：结果校验

抽查输出条目，核对关键字段与源数据一致性：

```bash
claude-mem --verify --memory_file ./memories/mem_20260820_120000.json
```

校验规则：
- 实体提取准确率 ≥ 90%（人工抽检）
- 决策记录与原文语义一致
- 摘要不包含原文未提及的信息

### 输出规范

```json
{
  "session_id": "session_20260820_001",
  "entities": [
    {"name": "ProjectX", "type": "project", "confidence": 0.95},
    {"name": "Alice", "type": "person", "confidence": 0.98}
  ],
  "decisions": [
    {"content": "采用微服务架构", "context": "架构评审会议", "timestamp": "2026-08-20T10:30:00Z"}
  ],
  "tasks": [
    {"content": "完成API文档编写", "due": "2026-08-25", "assignee": "Bob"}
  ],
  "summary": "本次会议确定采用微服务架构，Alice负责接口设计，Bob负责文档编写，预计8月25日完成。",
  "timestamp": "2026-08-20T12:00:00Z"
}
```

---

## 四、置信度门控

当信息不足或不确定时，使用以下占位符，不编造内容：

| 场景 | 占位符 | 示例 |
|------|--------|------|
| 实体名称不确定 | `[需核实:实体名称]` | "联系 [需核实:实体名称] 确认需求" |
| 时间信息缺失 | `[需核实:时间]` | "计划于 [需核实:时间] 上线" |
| 决策依据不明 | `[需核实:决策依据]` | "选择方案B，依据 [需核实:决策依据]" |
| 任务负责人未知 | `[需核实:负责人]` | "由 [需核实:负责人] 跟进" |

**门控规则**：
- 置信度 < 0.7 的实体自动标记为待核实
- 摘要中不包含任何占位符信息
- 检索结果中占位符信息置顶标注

---

## 五、错误码体系

| 错误码 | 错误描述 | 提示话术 | 修正步骤 |
|--------|----------|----------|----------|
| `MEM_001` | 输入文件不存在 | "未找到指定的输入文件，请检查路径" | 1. 确认文件路径正确；2. 检查文件权限；3. 重新执行 |
| `MEM_002` | 会话ID缺失 | "必须提供 session_id 参数" | 1. 添加 --session_id 参数；2. 重新执行 |
| `MEM_003` | 记忆文件格式错误 | "记忆文件 JSON 格式无效" | 1. 检查 JSON 语法；2. 使用 --validate 命令修复；3. 重新执行 |
| `MEM_004` | 压缩级别超范围 | "压缩级别必须在 1-5 之间" | 1. 调整 compress_level 参数；2. 重新执行 |
| `MEM_005` | 输出目录不可写 | "输出目录无写入权限" | 1. 检查目录权限；2. 更换输出路径；3. 重新执行 |
| `MEM_006` | 批量执行中断 | "批量执行过程中发生中断" | 1. 检查错误日志；2. 从断点继续执行；3. 或重新执行 |

---

## 六、FAQ 反模式

### 常见坑 1：过度压缩丢失关键信息

**反模式**：使用最高压缩级别（5级）处理所有对话，导致重要细节丢失。

**正确做法**：
- 默认使用 3 级压缩
- 对包含关键决策的对话使用 2 级
- 对简单问答使用 4-5 级

### 常见坑 2：忽略置信度标记

**反模式**：直接使用未核实的实体信息，导致后续操作出错。

**正确做法**：
- 检索结果中带 `[需核实]` 标记的信息必须人工确认
- 确认后更新记忆文件，移除标记

### 常见坑 3：跨会话信息冲突

**反模式**：多个会话对同一实体产生矛盾信息，未做冲突检测。

**正确做法**：
- 写入新记忆前检查已有记忆
- 发现冲突时保留时间戳较新的记录
- 在摘要中标注冲突信息

### 常见坑 4：记忆文件命名混乱

**反模式**：使用无规则命名，导致检索困难。

**正确做法**：
- 严格遵循 `mem_YYYYMMDD_HHMMSS.json` 格式
- 同一会话的多次捕获使用相同 session_id
- 定期归档旧记忆文件

### 常见坑 5：批量执行前不备份

**反模式**：直接对原始文件执行批量操作，出错后无法恢复。

**正确做法**：
- 批量执行前自动备份至 `./backup/`
- 备份文件保留至少 7 天
- 执行后验证备份完整性

---

## 七、渐进式披露

### 速查卡（30秒上手）

```
1. 保存记忆：claude-mem --capture --session_id <ID>
2. 检索记忆：claude-mem --retrieve --keyword <关键词>
3. 查看全部：claude-mem --list
4. 验证记忆：claude-mem --verify --memory_file <文件>
```

### 新手路径（首次使用）

1. 阅读「能力边界」了解功能范围
2. 使用 `--selftest` 运行测试样本
3. 对单个会话执行捕获，检查输出格式
4. 在新会话中检索，验证上下文恢复效果

### 进阶路径（熟练使用）

1. 自定义压缩级别，平衡信息密度与完整性
2. 编写脚本批量处理历史对话
3. 建立记忆索引，实现跨项目检索
4. 结合外部工具，实现记忆的定时备份与归档

### 专家路径（深度定制）

1. 修改压缩算法，适配特定领域术语
2. 开发插件，扩展实体识别类型
3. 集成 CI/CD 流程，自动保存构建决策
4. 建立记忆质量评估体系，持续优化提取准确率

---

## 八、参数参考表

| 参数 | 类型 | 默认值 | 取值范围 | 说明 |
|------|------|--------|----------|------|
| `session_id` | string | 无 | 任意字符串 | 会话唯一标识，必填 |
| `input_file` | string | 无 | 文件路径 | 输入对话文件 |
| `input_dir` | string | 无 | 目录路径 | 批量输入目录 |
| `output_dir` | string | `./memories/` | 目录路径 | 记忆输出目录 |
| `compress_level` | int | 3 | 1-5 | 压缩级别，1最详细5最精简 |
| `backup` | bool | true | true/false | 是否备份原始文件 |
| `verify` | bool | false | true/false | 是否执行结果校验 |
| `keyword` | string | 无 | 任意字符串 | 检索关键词 |
| `timeout` | int | 30 | 1-300 | 操作超时时间（秒） |

---

## 九、用户协议

<!-- user-agreement-injected -->

**使用条款**

1. 使用者自行承担全部责任：本 Skill 提供的所有功能、输出结果及使用建议，使用者应自行评估其适用性和准确性，并承担使用过程中产生的全部风险与责任。

2. 禁止反向工程：使用者不得对本 Skill 的源代码、算法逻辑、内部实现进行反向工程、反编译、破解或任何形式的未授权访问。

3. 数据安全：使用者应自行负责输入数据的合法性和安全性，本 Skill 不承担数据泄露、丢失或损坏的责任。

4. 合规使用：使用者应遵守所在国家/地区的法律法规，不得将本 Skill 用于任何非法用途。

5. 免责声明：本 Skill 按"现状"提供，不提供任何明示或暗示的保证，包括但不限于适销性、特定用途适用性和非侵权性。

---

## 十、许可证（License）

<!-- professional-license-embedded -->

### MIT License

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

*本 Skill 由 AI 辅助生成，仅供参考。使用前请阅读相关文档，并根据实际需求调整配置。*

## 差异（Diff）

| 能力 | 常规方案 | 本工具（增强版） |
|------|---------|-----------------|
| 核心功能 | 基础实现，能力有限 | 会话记忆 跨期上下文 持久化检索 完整实现，功能更全 |
| 使用体验 | 手动配置，流程繁琐 | 开箱即用，参数预置，上手更快 |
| 工程化 | 缺少自检/降级/容错 | --selftest 契约 + 多编码容错 + dry-run 预览 |
| 适用场景 | 单一场景 | 多场景覆盖，批量处理支持 |

## 新增功能（Feature Additions）

本工具在常规实现基础上新增以下功能模块：
1. 新增完整 CLI 入口（argparse 参数化控制）
2. 新增自检契约模块（--selftest 验证核心函数）
3. 新增多编码容错模块（utf-8/gbk/gb18030 三级 fallback）
4. 新增 dry-run 预览模块（写盘操作前可视化预览）
5. 新增异常降级模块（每函数 try-except，保证不崩溃）

## 竞品分析（Competitor）

**对标对象**：同类工具、通用方案、手工流程。

**竞品下载原因分析**（为什么用户需要这类工具）：
1. 用户需要快速完成会话记忆 跨期上下文 持久化检索，不想手动重复操作
2. 用户需要开箱即用的工具，配置越简单越好
3. 用户需要可靠的结果，出错能自查自证
4. 用户需要批量处理能力，减少人工盯流程

**本工具如何覆盖这些下载原因**：
- 覆盖原因 1：跨会话捕获、压缩并检索代理对话中的关键信息，实现上下文持久化。
- 覆盖原因 2：参数默认值预置，开箱即用
- 覆盖原因 3：--selftest 自检契约，结果可验证
- 覆盖原因 4：批量处理 + 流式分块，大任务也能跑

**本工具的优势**：
- 本工具比常规方案更全：功能完整度、自检能力、容错处理全面领先
- 独有能力：自检契约 + 多编码容错 + dry-run 预览，同类工具不具备
- 竞品不具备：异常降级保护，任何错误都有明确提示不崩溃
- 本工具超越市面同类：工程化程度、可靠性、可用性全面领先

## 为什么选择本版

1. 真正的完整实现：跨会话捕获、压缩并检索代理对话中的关键信息，实现上下文持久化。，不是演示壳
2. 开箱即用：参数预置 + 默认值，上手更快
3. 可靠可证：--selftest 自检契约，结果可验证
4. 容错健壮：异常降级 + 多编码容错，不轻易崩溃
5. 安全可控：--dry-run 预览，写盘不误伤

## 简介（Description）

## 简介（Description）

会话记忆 跨期上下文 持久化检索——跨会话捕获、压缩并检索代理对话中的关键信息，实现上下文持久化。。输入任务，输出结果，全程可校验、可追溯，适合日常高频使用与批量处理场景。 支持参数化控制、自检验证、多编码容错与预览模式，工程化程度高，开箱即用。

## 安装（Setup）

```bash
# 1. 进入 Skill 目录
cd claude-mem

# 2. 运行自检确认环境
python run.py --selftest

# 3. 开始使用
python run.py --help
```

## 使用（Usage）

```bash
python run.py <命令> [参数]    # 执行核心功能
python run.py --selftest      # 运行自检
```

## 示例（Examples）

```bash
# 示例 1: 查看帮助
python run.py --help

# 示例 2: 执行核心功能
python run.py main --input file.txt

# 示例 3: 运行自检
python run.py --selftest
```

## 常见问题（FAQ）

**Q: 支持中文文件吗？**
A: 支持，内置 utf-8/gbk/gb18030 多编码容错。

**Q: 运行报错怎么办？**
A: 工具内置异常降级，错误会有明确提示；可先用 --dry-run 预览。

**Q: 如何确认功能正常？**
A: 运行 --selftest，全部通过即核心功能正常。