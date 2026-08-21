---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: notewise
name: notewise
displayName: 笔记整理 知识卡片 信息萃取
description: 将零散笔记转化为结构化知识卡片，辅助学习与复盘。
version: 1.0.4
rules_version: cpr-20260821-n626
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/notewise
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: linqiu
agent_created: true
trigger_words: ["notewise", "知识库", "笔记整理", "结构化笔记", "信息萃取", "卡片笔记", "知识管理"]
---

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->


> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# notewise 技能手册

## 一、能力边界：一页纸速查卡

### 1.1 能做什么

| 能力项 | 说明 | 输出物 |
|--------|------|--------|
| 单文件处理 | 将一篇 Markdown/纯文本笔记拆解为多张知识卡片 | `output/` 目录下的 JSON 文件 |
| 批量处理 | 遍历指定目录下所有 `.md`/`.txt` 文件，逐一生成卡片 | 每文件对应一个 JSON 文件 |
| 卡片分类 | 自动识别笔记内容，分配 `card_type`（概念/流程/案例/清单/疑问） | 卡片元数据 |
| 置信度评估 | 对每张卡片的字段完整性进行打分，标记低置信度字段 | `confidence` 字段 + `[需核实]` 占位 |
| 输出校验 | 对已生成的卡片集进行完整性检查，生成校验报告 | `verification.json` |

### 1.2 不能做什么

| 限制项 | 说明 |
|--------|------|
| 不处理图片/PDF | 仅支持 UTF-8 编码的纯文本与 Markdown 文件 |
| 不联网检索 | 不补充外部知识，只基于输入内容做结构化 |
| 不自动修正 | 低置信度字段仅标记，不猜测填充 |
| 不生成新知识 | 不进行推理扩展，只做信息重组 |

### 1.3 适用对象

- 需要整理课堂笔记、会议纪要、阅读摘录的学生与职场人
- 使用卡片盒笔记法（Zettelkasten）进行知识管理的实践者
- 需要定期复盘学习成果的终身学习者

---

## 二、触发方式：场景映射表

| 用户说（大白话） | 触发词命中 | 实际执行动作 |
|------------------|------------|--------------|
| "帮我把这篇笔记整理成卡片" | 笔记整理 | 单文件处理流程 |
| "我有一堆笔记文件，帮我批量处理" | 批量处理 | 批量处理流程 |
| "看看这些卡片有没有缺东西" | 校验 | 输出校验流程 |
| "这个笔记里有哪些关键概念？" | 信息萃取 | 单文件处理 + 查看概念类卡片 |
| "帮我建个知识库" | 知识库 | 批量处理 + 校验 |

---

## 三、标准流程

### 3.1 前置条件

| 条件 | 要求 |
|------|------|
| 输入文件 | UTF-8 编码，`.md` 或 `.txt` 格式 |
| 文件大小 | 单文件 ≤ 500KB |
| 目录结构 | 输入目录内不包含子目录（批量模式） |
| 运行环境 | Python 3.8+，已安装 notewise CLI |

### 3.2 执行步骤

#### 步骤 1：放置文件

将待处理笔记放入同一目录，确保编码为 UTF-8。

```bash
# 示例：准备输入目录
mkdir -p ./notes/
cp ~/Desktop/我的笔记.md ./notes/
```

#### 步骤 2：试运行（单文件）

```bash
notewise --input ./notes/我的笔记.md --output ./output/
```

**预期输出**：
```
[INFO] 已读取文件: 我的笔记.md (12.4KB)
[INFO] 识别到 5 个知识单元
[INFO] 生成卡片: 概念_认知负荷.md.json
[INFO] 生成卡片: 流程_双链笔记法.md.json
[INFO] 生成卡片: 案例_卢曼卡片盒.md.json
[INFO] 生成卡片: 清单_每日复盘步骤.md.json
[INFO] 生成卡片: 疑问_间隔重复算法.md.json
[INFO] 完成，共 5 张卡片，平均置信度 0.82
```

#### 步骤 3：核对输出

打开生成的 JSON 文件，检查 `card_type` 与 `confidence` 是否符合预期。

```bash
cat ./output/概念_认知负荷.md.json
```

```json
{
  "card_id": "c001",
  "source_file": "我的笔记.md",
  "card_type": "concept",
  "title": "认知负荷",
  "summary": "工作记忆容量有限，处理信息时产生的心理负担。",
  "key_points": [
    "内在负荷：由材料本身复杂度决定",
    "外在负荷：由呈现方式决定",
    "相关负荷：用于构建图式的认知资源"
  ],
  "relations": ["工作记忆", "图式理论", "教学设计"],
  "confidence": 0.85,
  "flags": []
}
```

#### 步骤 4：批量处理

```bash
notewise --input ./notes/ --output ./output/ --batch
```

**批量模式参数**：

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--batch` | 关闭 | 开启批量处理 |
| `--concurrency` | 4 | 并行线程数 |
| `--skip-existing` | 关闭 | 跳过已存在的输出文件 |
| `--max-cards` | 50 | 单文件最大卡片数 |

#### 步骤 5：输出校验

```bash
notewise --verify ./output/ --report ./output/verification.json
```

**校验报告结构**：

```json
{
  "generated_at": "2026-08-21T10:30:00Z",
  "total_files": 12,
  "total_cards": 87,
  "avg_confidence": 0.78,
  "low_confidence_cards": 14,
  "missing_fields": {
    "relations": 23,
    "examples": 18
  },
  "issues": [
    {
      "card_id": "c042",
      "issue": "confidence_below_threshold",
      "detail": "置信度 0.52，低于阈值 0.60"
    }
  ]
}
```

---

## 四、输出规范

### 4.1 卡片类型（card_type）

| 类型 | 标识 | 适用场景 | 必填字段 |
|------|------|----------|----------|
| 概念 | `concept` | 名词解释、理论定义 | title, summary, key_points |
| 流程 | `process` | 步骤、操作序列 | title, steps, prerequisites |
| 案例 | `example` | 实例、应用场景 | title, context, outcome |
| 清单 | `checklist` | 待办、检查项 | title, items, priority |
| 疑问 | `question` | 未解决问题、待查证 | title, question, related |

### 4.2 置信度门控规则

| 置信度区间 | 标记 | 处理方式 |
|------------|------|----------|
| 0.90 - 1.00 | 无 | 正常输出 |
| 0.70 - 0.89 | 无 | 正常输出，但建议人工复核 |
| 0.50 - 0.69 | `[需核实]` | 在对应字段前添加占位标记 |
| < 0.50 | `[需核实]` + 降级 | 卡片标记为 `draft`，不参与关联图谱 |

**占位示例**：

```json
{
  "summary": "[需核实:作者未明确说明] 该方法适用于团队协作场景",
  "confidence": 0.58
}
```

### 4.3 字段完整性要求

| 字段 | 要求 | 缺失处理 |
|------|------|----------|
| `card_id` | 必填，全局唯一 | 自动生成 |
| `source_file` | 必填，来源文件 | 自动填充 |
| `card_type` | 必填，五选一 | 置信度降至 0.4 |
| `title` | 必填，≤ 50 字符 | 置信度降至 0.3 |
| `summary` | 必填，≤ 200 字符 | 置信度降至 0.5 |
| `key_points` / `steps` / `items` | 至少 1 条 | 置信度降至 0.6 |
| `relations` | 选填 | 不降级，但影响图谱完整性 |
| `confidence` | 必填，0-1 浮点 | 自动计算 |

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| E001 | 文件不存在 | `[E001] 找不到输入文件: {path}` | 检查路径是否正确，文件是否被移动 |
| E002 | 编码错误 | `[E002] 文件编码不是 UTF-8: {path}` | 用 `iconv` 或编辑器转换编码 |
| E003 | 文件过大 | `[E003] 文件超过 500KB 限制: {size}` | 拆分文件，或删除冗余内容 |
| E004 | 输出目录不可写 | `[E004] 无法写入输出目录: {path}` | 检查权限，或更换输出路径 |
| E005 | 无有效知识单元 | `[E005] 未识别到可结构化的内容` | 检查笔记是否过于碎片化，补充上下文 |
| E006 | 批量模式目录无效 | `[E006] 输入目录不存在或为空: {path}` | 确认目录存在且包含 `.md`/`.txt` 文件 |
| E007 | 校验失败 | `[E007] 校验发现 {n} 个问题，详见报告` | 打开 `verification.json`，逐项修复 |

---

## 六、FAQ 反模式对照

### 反模式 1：过度依赖自动分类

**错误做法**：完全信任 `card_type` 自动分类结果，不做人工复核。

**正确做法**：对置信度 < 0.80 的卡片，手动检查分类是否合理。特别是 `question` 类型，容易与 `concept` 混淆。

### 反模式 2：忽略 `[需核实]` 标记

**错误做法**：直接使用带 `[需核实]` 占位的卡片，不补充信息。

**正确做法**：将 `[需核实]` 视为待办事项，通过查阅原文或补充资料，替换占位内容。

### 反模式 3：批量处理不校验

**错误做法**：批量处理后直接使用，跳过 `--verify` 步骤。

**正确做法**：批量处理后必须执行校验，检查 `verification.json` 中的低置信度卡片和缺失字段。

### 反模式 4：输入文件格式混乱

**错误做法**：将 PDF、Word 文档直接放入输入目录。

**正确做法**：先将所有输入转换为 UTF-8 编码的 Markdown 或纯文本格式。

### 反模式 5：卡片数量失控

**错误做法**：不设 `--max-cards` 限制，导致单文件生成上百张卡片。

**正确做法**：根据笔记实际内容量，合理设置 `--max-cards`（建议 20-50），超出部分合并或忽略。

---

## 七、渐进式披露：分层次阅读路径

### 7.1 速查卡（30 秒上手）

```
1. 放文件 → 同一目录，UTF-8 编码
2. 试运行 → notewise --input 单文件 --output ./output/
3. 核对 → 检查 card_type 和 confidence
4. 批量 → notewise --input ./notes/ --output ./output/ --batch
5. 校验 → notewise --verify ./output/ --report ./output/verification.json
```

### 7.2 新手路径（首次使用，约 15 分钟）

1. 阅读本速查卡，了解基本流程
2. 准备 1-2 个测试文件，执行步骤 1-2
3. 观察输出格式，对照「输出规范」理解字段含义
4. 熟悉置信度门控规则，了解 `[需核实]` 的含义
5. 完成一次完整流程（步骤 1-4）

### 7.3 进阶路径（熟练用户，持续优化）

1. 掌握错误码体系，能独立排查 E001-E007
2. 理解置信度判定规则，能区分不同置信度场景
3. 能手动修正低置信度卡片，补充缺失信息
4. 能利用关联图谱发现知识盲区，主动补充学习
5. 能自定义输出模板（修改 `config.yaml` 中的模板字段）

### 7.4 配置参考（config.yaml）

```yaml
# 模板配置
templates:
  concept: "concept_template.md"
  process: "process_template.md"
  example: "example_template.md"
  checklist: "checklist_template.md"
  question: "question_template.md"

# 置信度阈值
confidence:
  verify_threshold: 0.70
  draft_threshold: 0.50
  placeholder_threshold: 0.60

# 输出选项
output:
  include_relations: true
  include_flags: true
  pretty_print: true
```

---

## 八、用户协议

**生效日期**：2026 年 8 月 21 日

1. **责任承担**：使用者应自行确保输入数据的合法性与安全性。本 Skill 不承担因输入数据引发的任何法律纠纷或数据泄露责任。

2. **数据安全**：使用者应妥善保管输入文件，避免包含敏感个人信息。本 Skill 不收集、不上传任何用户数据。

3. **禁止反向工程**：使用者不得对本 Skill 的底层算法、提示词结构进行反向工程、反编译或试图提取源代码。

4. **合规使用**：使用者应遵守所在地法律法规，不得将本 Skill 用于任何非法目的。

5. **协议更新**：本协议可能随 Skill 版本更新而调整，使用者应定期查阅最新版本。

<!-- user-agreement-injected -->

---

## 九、许可证（License）

### MIT License

```
MIT License

Copyright (c) 2026 linqiu

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
