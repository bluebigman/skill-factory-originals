---
slug: audio-transcript-format
name: audio-transcript-format
displayName: 语音转写 文本精修 纪要提取
description: 将语音转写文本整理为结构化纪要，清理冗余并提取关键事项。
version: 1.0.0
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/audio-transcript-format 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: SkillForge Studio
agent_created: true
trigger_words: ["语音转写整理", "音频转文字", "会议纪要提取", "transcript cleanup", "语音稿润色"]
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# 语音转写文本智能整理 Skill 文档

## 一、能力边界（一页纸速查卡）

### 1.1 能做什么

| 能力项 | 说明 | 输出形式 |
|--------|------|----------|
| 分句与标点修复 | 将无标点或标点错乱的转写文本，按语义断句并补全标点 | 整理后的完整文本 |
| 填充词清理 | 删除"嗯、啊、那个、就是"等无意义口语词 | 清理后的文本 |
| 段落分割 | 按话题切换或发言人变化，将长文本切分为逻辑段落 | 分段文本 |
| 术语统一 | 根据领域词表，将同义异形词统一为规范术语 | 统一后的文本 + 替换记录表 |
| 关键信息提取 | 提取待办事项、截止日期、异议点、决策结论 | 结构化清单（含原文句索引） |
| 多编码识别 | 自动检测并读取 utf-8 / gbk / gb18030 编码的文本文件 | 正确解码的文本内容 |

### 1.2 不能做什么

| 限制项 | 说明 |
|--------|------|
| 不处理音频/视频文件 | 输入必须是已转写完成的纯文本文件（.txt / .md 等） |
| 不进行语义改写 | 只做清理和结构化，不改变原意，不润色文风 |
| 不自动执行写操作 | 默认 dry-run 模式，需显式加 `--force` 才写入文件 |
| 不保证提取项绝对准确 | 所有提取结果均带原文句索引，需人工复核 |
| 不识别说话人身份 | 无法区分"谁说的"，只能按段落标记 [发言人未知] |

### 1.3 适用对象

- 会议纪要整理者：需要快速从冗长转写稿中提取行动项
- 访谈研究员：需要清理口语杂质，保留关键回答
- 法务/医疗记录员：需要术语统一和精确提取（需指定 `--domain`）
- 播客/课程内容编辑：需要将口语转写变为可发布的文字稿

---

## 二、触发方式

### 2.1 触发词

当用户输入包含以下任一关键词时，本 Skill 被激活：

- 语音转写整理
- 音频转文字
- 会议纪要提取
- transcript cleanup
- 语音稿润色

### 2.2 场景映射表

| 用户说（大白话） | 实际需求 | 推荐命令 |
|------------------|----------|----------|
| "帮我把这个会议录音的文字稿弄干净点" | 清理填充词、修复标点、分段 | `audio-transcript-format --input meeting.txt` |
| "这段访谈里有哪些待办事项？" | 提取行动项和截止日期 | `audio-transcript-format --input interview.txt --extract todos` |
| "法律讲座的稿子，术语要统一" | 术语统一 + 领域词表 | `audio-transcript-format --input lecture.txt --domain legal` |
| "这文件打开是乱码" | 编码识别与转换 | `audio-transcript-format --input unknown.txt --detect-encoding` |
| "帮我整理完直接保存" | 跳过预览，直接写文件 | `audio-transcript-format --input raw.txt --force` |

---

## 三、标准流程

### 3.1 前置条件

| 条件 | 要求 | 检查方式 |
|------|------|----------|
| 输入文件 | 纯文本格式（.txt / .md / .csv） | 文件扩展名检查 |
| 文件大小 | ≤ 10 MB | 超过则提示分段处理 |
| 领域词表（可选） | 法律/医疗场景需指定 `--domain` | 参数校验 |
| 输出目录 | 默认与输入同目录，可 `--output` 指定 | 目录存在性检查 |

### 3.2 执行步骤（分步编号）

1. **读取与编码识别**
   - 自动检测文件编码（utf-8 → gbk → gb18030 依次尝试）
   - 若全部失败，输出错误码 `E001` 并终止

2. **预清理（dry-run 预览）**
   - 生成整理后的完整文本，但不写入文件
   - 显示 diff 摘要：修改了多少处标点、删除了多少个填充词

3. **分句与标点修复**
   - 按语义边界断句（句号、问号、感叹号）
   - 修复常见错误：逗号误用、引号不配对、省略号不规范

4. **填充词清理**
   - 删除列表：嗯、啊、呃、那个、这个、就是、然后、就是说、对吧、是吧
   - 保留条件：当填充词位于引号内（表示原话引用）时不删除

5. **段落分割**
   - 按话题切换（关键词变化）或空行标记分段
   - 每段不超过 200 字，超过则二次切分

6. **术语统一（如指定 --domain）**
   - 加载领域词表（legal / medical / tech 三套内置）
   - 执行替换并生成替换记录表（原词 → 新词 → 出现次数）

7. **关键信息提取**
   - 待办事项：匹配"需要/应该/必须/记得"等动词 + 后续内容
   - 截止日期：匹配"X月X日/本周/下周/月底"等时间词
   - 异议点：匹配"但是/不过/有问题/不同意"等转折词
   - 决策结论：匹配"决定/确定/就这么定/通过"等确认词

8. **输出规范**
   - 整理稿：`原文件名.clean.txt`
   - 提取清单：`原文件名.extract.md`（含句索引）
   - 替换记录：`原文件名.terms.csv`（仅当执行了术语统一）

### 3.3 输出示例

**提取清单格式（extract.md）：**

```markdown
# 关键信息提取清单

## 待办事项
| 序号 | 内容 | 原文句索引 |
|------|------|------------|
| 1 | 周五前提交项目预算 | 句 #12 |
| 2 | 联系供应商确认交期 | 句 #28 |

## 截止日期
| 序号 | 事项 | 日期 | 原文句索引 |
|------|------|------|------------|
| 1 | 预算提交 | 2025-06-20 | 句 #12 |

## 异议点
| 序号 | 内容 | 原文句索引 |
|------|------|------------|
| 1 | 对预算分配比例有异议 | 句 #15 |

## 决策结论
| 序号 | 内容 | 原文句索引 |
|------|------|------------|
| 1 | 项目延期两周，改为 7 月启动 | 句 #22 |
```

---

## 四、置信度门控

### 4.1 占位符规则

当信息不足或无法确认时，使用以下占位符，**绝不编造**：

| 场景 | 占位符 | 示例 |
|------|--------|------|
| 日期不明确 | `[需核实:日期]` | "下周五前完成" → 截止日期：`[需核实:日期]` |
| 人名/机构名不确定 | `[需核实:主体]` | "张总说..." → 待办负责人：`[需核实:主体]` |
| 数字模糊 | `[需核实:数量]` | "大概几十万" → 金额：`[需核实:数量]` |
| 术语无法匹配 | `[需核实:术语]` | 领域词表中无对应词 |

### 4.2 置信度分级

| 级别 | 判定标准 | 输出标记 |
|------|----------|----------|
| 高（≥90%） | 原文有明确关键词且无歧义 | 无标记 |
| 中（70-89%） | 原文有暗示但需推断 | `[需核实:...]` |
| 低（<70%） | 原文信息模糊或缺失 | 不提取，仅记录 `[未提取:原因]` |

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| `E001` | 编码识别失败 | "无法识别文件编码，请确认文件为 utf-8/gbk/gb18030 格式" | 用文本编辑器另存为 utf-8 后重试 |
| `E002` | 输入文件不存在 | "找不到输入文件，请检查路径" | 确认路径正确后重试 |
| `E003` | 文件超过大小限制 | "文件超过 10MB，请分段处理" | 将文件拆分为多个小文件 |
| `E004` | 领域词表不存在 | "未找到指定领域词表，可选值：legal / medical / tech" | 检查 --domain 参数拼写 |
| `E005` | 输出目录不可写 | "无法写入输出目录，请检查权限" | 更换 --output 路径 |
| `E006` | dry-run 模式下不执行写入 | "当前为预览模式，确认无误后请加 --force 执行" | 添加 --force 参数重试 |

---

## 六、FAQ 反模式

### 6.1 常见坑

| 坑 | 反模式（错误做法） | 正模式（正确做法） |
|----|-------------------|-------------------|
| 跳过预览直接写文件 | 直接 `--force` 覆盖原稿 | 先 dry-run 查看 diff，确认后再 `--force` |
| 领域词表选错 | 法律稿用默认词表，术语未统一 | 指定 `--domain legal` |
| 修改后不跑基准 | 改完代码直接上线 | 执行 `--benchmark` 确认 F1 不下降 |
| 覆盖原始稿 | 整理稿直接覆盖原文件 | 分开保存，保留原始稿备查 |
| 盲目信任提取结果 | 直接采用提取清单不核对 | 对照句索引逐条人工复核 |

### 6.2 反模式对照表

| 场景 | 错误做法 | 正确做法 |
|------|----------|----------|
| 用户要求"直接整理好" | 立即写文件 | 先预览，说明修改点，征得同意后写入 |
| 用户说"大概就行" | 跳过置信度检查 | 仍按置信度门控，模糊处标记 `[需核实]` |
| 用户提供乱码文件 | 猜测内容强行解码 | 报告 `E001`，建议用户转换编码 |

---

## 七、渐进式披露

### 7.1 速查卡（新手必读）

```
用法：audio-transcript-format --input <文件> [选项]

必选参数：
  --input <路径>     输入文本文件

常用选项：
  --domain <领域>    指定领域词表（legal/medical/tech）
  --force            跳过预览，直接写入文件
  --extract <类型>   提取指定类型（todos/dates/objections/decisions）
  --verbose          显示每步修改明细

其他：
  --selftest         运行内置 40 条自测
  --version          显示版本号
  --benchmark        运行基准测试，检查 F1 分数
```

### 7.2 新手路径（5 分钟上手）

1. 运行 `audio-transcript-format --selftest` 确认工具正常
2. 准备一个 .txt 转写文件
3. 执行 `audio-transcript-format --input 你的文件.txt` 查看预览
4. 确认无误后加 `--force` 写入
5. 打开 `.clean.txt` 查看整理结果，打开 `.extract.md` 查看提取清单

### 7.3 进阶路径（深度使用）

1. 法律/医疗场景：指定 `--domain` 启用术语统一
2. 批量处理：编写脚本循环调用，每次输出独立文件
3. 自定义词表：编辑 `terms/` 目录下的 CSV 文件，添加自定义术语
4. 质量监控：每次修改代码后运行 `--benchmark`，对比 F1 分数变化
5. 调试排错：结果异常时加 `--verbose`，查看每步修改明细

---

## 八、参数详解

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `--input` | string | 无（必填） | 输入文件路径 |
| `--output` | string | 输入同目录 | 输出目录路径 |
| `--domain` | string | 无 | 领域词表：legal / medical / tech |
| `--force` | boolean | false | 跳过预览直接写入 |
| `--extract` | string | all | 提取类型：todos / dates / objections / decisions / all |
| `--verbose` | boolean | false | 显示每步修改明细 |
| `--detect-encoding` | boolean | false | 仅检测编码并输出结果 |
| `--selftest` | boolean | false | 运行内置自测 |
| `--benchmark` | boolean | false | 运行基准测试 |
| `--version` | boolean | false | 显示版本号 |

---

## 九、内置自测说明

运行 `--selftest` 将执行 40 条测试用例，覆盖：

- 编码识别（10 条）：utf-8 / gbk / gb18030 各场景
- 分句与标点（10 条）：长句切分、引号修复、省略号规范
- 填充词清理（8 条）：常规删除、引号内保留、边界情况
- 术语统一（6 条）：同义词替换、大小写统一、复数处理
- 关键信息提取（6 条）：待办/日期/异议/决策各场景

每条测试输出 `PASS` 或 `FAIL`，全部通过则提示 `All 40 tests passed.`

---

## 十、用户协议

<!-- user-agreement-injected -->

**使用本 Skill 即表示您同意以下条款：**

1. **责任承担**：使用者自行承担因使用本 Skill 产生的全部责任。包括但不限于因整理结果不准确、提取信息遗漏、文件处理错误等造成的直接或间接损失。
2. **禁止反向工程**：不得对本 Skill 的代码、算法、词表进行反向工程、反编译、破解或试图获取源代码。
3. **合规使用**：使用者应确保输入内容不违反法律法规，不侵犯第三方权益。因输入内容引发的法律纠纷由使用者自行承担。
4. **无担保声明**：本 Skill 按"现状"提供，不附带任何明示或暗示的担保，包括但不限于适销性、特定用途适用性和非侵权保证。
5. **修改与终止**：作者保留随时修改、更新或终止本 Skill 的权利，恕不另行通知。

---

## 十一、许可证（License）

<!-- professional-license-embedded -->

**MIT License**

Copyright (c) 2025 SkillForge Studio

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
