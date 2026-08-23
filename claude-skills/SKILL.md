---
slug: claude-skills
name: claude-skills
displayName: 技能研习 规范处理 流程参考
description: 面向学习与参考场景，提供规范、可复用的技能处理流程与输出。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 林栖
agent_created: true
trigger_words: ["claude skills", "技能学习", "技能参考", "技能处理", "技能规范", "技能研习", "技能查阅", "技能执行"]
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

> 本 Skill 由 AI 辅助生成，仅供参考

# 技能研习与规范处理参考

## 一、能力边界速查卡

本 Skill 面向「学习如何规范地处理技能类任务」这一场景，提供一套可复用的流程框架与输出约定。它不替代具体业务逻辑，而是为处理过程提供结构指引。

| 维度 | 能做 | 不能做 |
|------|------|--------|
| 输入准备 | 指导文件放置、命名核对 | 自动移动或重命名文件 |
| 试运行 | 提供单样本验证步骤与核对要点 | 代替用户执行试运行 |
| 批量执行 | 给出批量处理的操作顺序与备份要求 | 自动执行批量任务 |
| 结果校验 | 提供抽查方法与字段比对清单 | 保证数据绝对正确 |
| 输出规范 | 定义输出字段与格式约定 | 生成具体业务内容 |

**适用对象**：需要处理批量文件、希望建立规范流程的学习者或初级执行者；需要快速查阅处理步骤的参考型用户。

---

## 二、触发方式与场景映射

当出现以下表述或意图时，可触发本 Skill：

| 用户说（大白话） | 实际意图 | 触发动作 |
|------------------|----------|----------|
| "帮我看看这批文件怎么处理" | 需要处理流程指导 | 进入标准流程 |
| "技能学习" / "技能参考" | 查阅处理规范 | 展示速查卡与流程 |
| "这个技能怎么用" | 了解触发与边界 | 展示触发方式与能力边界 |
| "处理完怎么检查" | 需要校验方法 | 展示校验步骤 |
| "claude skills" | 调用本 Skill | 进入标准流程 |

---

## 三、标准处理流程

### 前置条件

| 条件项 | 要求 | 检查方式 |
|--------|------|----------|
| 文件放置 | 待处理文件位于同一目录 | 目视确认或 `ls` 命令 |
| 命名规范 | 文件名遵循统一规则（如 `前缀_序号.扩展名`） | 抽查 3-5 个文件名 |
| 原始备份 | 已复制一份原始文件至备份目录 | 确认备份目录存在且非空 |

### 执行步骤

**第一步：准备输入**

1. 将所有待处理文件放入同一工作目录。
2. 检查文件名是否遵循统一命名规范；若不统一，先整理命名。
3. 建立备份目录，复制一份原始文件作为存档。

**第二步：单样本试运行**

1. 从全量数据中选取 1 个代表性样本。
2. 按目标输出格式执行一次处理。
3. 核对输出字段是否完整、格式是否符合预期。

| 核对项 | 预期结果 |
|--------|----------|
| 字段完整性 | 所有必填字段均有值 |
| 格式一致性 | 日期、编号等格式统一 |
| 内容准确性 | 关键信息与源数据一致 |

**第三步：批量执行**

1. 确认试运行无误后，对全量数据执行处理。
2. 处理过程中不修改原始文件，输出至独立结果目录。
3. 保留原始备份，直至全部校验通过。

**第四步：结果校验**

1. 从批量结果中随机抽取不少于 10% 的条目（至少 3 条）。
2. 逐项核对关键字段与源数据的一致性。
3. 若发现异常，定位原因并修正后重新执行受影响部分。

### 输出规范

| 输出项 | 规范要求 |
|--------|----------|
| 文件格式 | 与试运行确认的格式一致 |
| 字段命名 | 使用统一字段名，不混用中英文 |
| 编码 | UTF-8 无 BOM |
| 目录结构 | 结果输出至独立目录，不覆盖原始文件 |

---

## 四、置信度门控

当处理过程中遇到信息不足或字段缺失时，遵循以下规则：

1. **不编造**：不得自行推测或填充缺失信息。
2. **占位标记**：在对应字段输出 `[需核实:字段名]` 占位符。
3. **记录说明**：在输出文件的备注字段中说明缺失原因。
4. **上报处理**：批量执行前，将缺失情况汇总并确认处理方式。

示例：若源数据缺少「创建时间」字段，输出为 `[需核实:创建时间]`，并在备注中注明"源数据未提供该字段"。

---

## 五、错误码体系

| 错误码 | 错误描述 | 提示话术 | 修正步骤 |
|--------|----------|----------|----------|
| E001 | 文件未放置在同一目录 | "请将所有待处理文件移至同一目录后重试" | 移动文件至统一目录 |
| E002 | 命名规范不一致 | "检测到文件名不符合统一规范，请先整理命名" | 按规则重命名文件 |
| E003 | 试运行输出字段缺失 | "试运行输出缺少必填字段，请检查处理逻辑" | 核对字段映射，补齐缺失项 |
| E004 | 批量执行中断 | "批量执行在第 N 条中断，请检查该条数据" | 定位异常条目，修正后续跑 |
| E005 | 校验不一致 | "抽查发现字段 X 与源数据不一致" | 对比源数据，修正处理逻辑 |

---

## 六、FAQ 反模式对照

| 常见坑（反模式） | 问题描述 | 正确做法 |
|------------------|----------|----------|
| 跳过试运行直接全量执行 | 批量执行后才发现格式错误，返工成本高 | 务必先单样本试运行，确认无误再批量 |
| 覆盖原始文件 | 处理出错后无备份可恢复 | 始终保留原始备份，输出至独立目录 |
| 编造缺失字段 | 信息不足时自行推测填充 | 使用 `[需核实:字段]` 占位，不编造 |
| 校验只看数量不看内容 | 只数条数不核对字段值 | 抽查关键字段与源数据逐项比对 |
| 命名随意不统一 | 文件名混乱导致处理遗漏或重复 | 处理前先统一命名规范 |

---

## 七、渐进式阅读路径

### 速查卡（30 秒版）

```
准备输入 → 单样本试运行 → 批量执行 → 结果校验
   │            │             │            │
 同目录      核对字段      保留备份      抽查10%
 统一命名    确认格式      独立输出      字段比对
```

### 新手路径（首次使用）

1. 阅读「能力边界速查卡」了解适用范围。
2. 按「标准处理流程」逐步执行，每步完成后检查前置条件。
3. 遇到异常时查阅「错误码体系」定位问题。
4. 完成后阅读「FAQ 反模式对照」避免常见错误。

### 进阶路径（有经验用户）

1. 直接查阅「标准处理流程」的步骤细节与参数表。
2. 关注「置信度门控」规则，确保输出严谨性。
3. 参考「输出规范」调整自定义格式。
4. 定期回顾「FAQ 反模式对照」优化个人流程。

---

## 用户协议

使用本 Skill 即表示您同意以下条款：

1. **责任承担**：使用者自行承担因使用本 Skill 产生的全部责任。本 Skill 提供的流程与建议仅供参考，不构成任何形式的保证。
2. **禁止反向工程**：不得对本 Skill 进行反向工程、反编译、破解或试图提取底层逻辑。
3. **合规使用**：使用者应确保使用场景符合当地法律法规及平台政策。
4. **免责声明**：本 Skill 由 AI 辅助生成，可能存在不准确或不完整之处，使用者应结合实际情况判断。

<!-- user-agreement-injected -->

---

## 许可证（License）

本 Skill 采用 MIT 许可证发布：

```
MIT License

Copyright (c) 2024 林栖

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
