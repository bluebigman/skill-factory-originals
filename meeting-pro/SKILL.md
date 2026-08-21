---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: meeting-pro
name: meeting-pro
displayName: 会议全流程 录音转写 纪要行动项
description: 一站式会议处理：录音转文字、纪要生成、行动项提取与校验。
version: 2.0.1
rules_version: cpr-20260820-n601
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/meeting-pro
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: LinguaForge Studio
agent_created: true
trigger_words: ["会议纪要", "录音转文字", "行动项提取", "会议记录", "纪要生成", "meeting-minutes", "transcription"]
---

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->


> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# meeting-pro 技能文档

## 一、能力边界：一页纸速查卡

### 1.1 能做什么

| 能力项 | 说明 | 输入要求 | 输出格式 |
|--------|------|----------|----------|
| 录音转文字 | 将音频/视频文件转为带时间戳的文本 | 音频文件路径或URL，时长≤3小时 | SRT + 纯文本双格式 |
| 会议纪要生成 | 从转写文本提取主题、结论、分歧点 | 转写文本或SRT文件 | 结构化Markdown纪要 |
| 行动项提取 | 识别责任人、截止时间、任务描述 | 会议纪要或转写文本 | JSON数组 + 表格 |
| 行动项校验 | 核对行动项是否完整、可执行 | 行动项JSON | 校验报告（通过/警告/失败） |
| 批量处理 | 多文件队列处理，支持断点续跑 | 文件列表 + 配置参数 | 批量处理汇总表 |

### 1.2 不能做什么

- **不进行实时转写**：仅支持离线文件处理，不支持流式音频输入。
- **不识别说话人身份**：仅区分不同声道或时间片段，不进行声纹识别。
- **不翻译非中文内容**：仅处理中文普通话，其他语言需先自行转译。
- **不生成会议评分**：不评估会议效率或参与者表现。
- **不自动发送邮件**：提取的行动项需人工确认后自行分发。

### 1.3 适用对象

- 需要频繁记录会议内容的行政/秘书人员
- 项目管理中需要跟踪行动项的团队负责人
- 需要归档会议资料的业务分析师
- 对会议记录有合规要求的法务/审计人员

---

## 二、触发方式与场景映射

### 2.1 触发词表

| 触发词 | 使用场景 | 示例指令 |
|--------|----------|----------|
| 会议纪要 | 会议结束后需要整理记录 | "帮我生成今天产品评审会的纪要" |
| 录音转文字 | 有录音文件需要转写 | "把 meeting_20260820.m4a 转成文字" |
| 行动项提取 | 需要从纪要中找出待办事项 | "提取这个纪要里的所有行动项" |
| 会议记录 | 泛指会议相关处理 | "整理一下上周的会议记录" |
| 纪要生成 | 同会议纪要，偏正式场景 | "基于这份转写生成正式纪要" |
| transcription | 英文触发，处理英文文件 | "Transcribe this audio file" |

### 2.2 场景映射表

| 用户说（大白话） | 实际执行动作 | 所需参数 |
|------------------|--------------|----------|
| "把这个录音整理一下" | 转写 + 生成纪要 | 文件路径 |
| "上次开会说的任务帮我列出来" | 提取行动项 | 纪要文件或转写文本 |
| "帮我检查这些行动项有没有遗漏" | 行动项校验 | 行动项JSON |
| "这周的三个会一起处理" | 批量处理 | 文件列表 |
| "转写结果准不准？" | 置信度报告 | 转写文本 |

---

## 三、标准处理流程

### 3.1 前置条件

| 条件项 | 要求 | 检查方式 |
|--------|------|----------|
| 音频文件 | 格式：MP3/WAV/M4A/FLAC，采样率≥16kHz | 文件头检查 |
| 转写文本 | 纯文本或SRT，编码UTF-8 | 编码检测 |
| 环境依赖 | Python 3.9+，安装 `meeting-pro` 包 | `pip show meeting-pro` |
| 存储空间 | 音频文件10倍大小的临时空间 | `df -h` |

### 3.2 执行步骤

#### 步骤一：输入验证

```bash
meeting-pro --selftest   # 检查环境完整性
meeting-pro --version    # 确认版本
```

#### 步骤二：单文件处理

```bash
# 基本用法：转写 + 纪要 + 行动项
meeting-pro process ./audio/meeting1.m4a \
  --output-dir ./results \
  --confidence-threshold 0.85

# 仅转写
meeting-pro transcribe ./audio/meeting1.m4a -o ./results/

# 从已有转写生成纪要
meeting-pro summarize ./results/meeting1.txt -o ./results/
```

#### 步骤三：批量处理

```bash
# 批量处理目录下所有音频
meeting-pro batch ./audio/ \
  --output-dir ./results/ \
  --parallel 2 \
  --resume

# 指定文件列表
meeting-pro batch --file-list ./meetings.txt \
  --output-dir ./results/
```

#### 步骤四：行动项校验

```bash
meeting-pro validate ./results/action_items.json \
  --rules ./rules.yaml
```

### 3.3 输出规范

#### 转写输出（SRT格式）

```
1
00:00:01,000 --> 00:00:04,500
大家好，今天会议主要讨论Q3产品规划。

2
00:00:04,600 --> 00:00:08,200
首先由产品经理介绍市场调研结果。
```

#### 纪要输出（Markdown）

```markdown
# 会议纪要：产品规划评审会

- **日期**：2026-08-20
- **参会人数**：8人
- **会议时长**：45分钟

## 主题
Q3产品路线图评审

## 结论
1. 确认优先开发移动端功能
2. 暂缓桌面端重构计划

## 分歧点
- 移动端技术栈选择（React Native vs Flutter）
```

#### 行动项输出（JSON）

```json
[
  {
    "id": "AI-001",
    "task": "完成移动端技术选型对比报告",
    "assignee": "张伟",
    "due_date": "2026-08-27",
    "priority": "high",
    "confidence": 0.92,
    "source_timestamp": "00:12:35"
  }
]
```

---

## 四、置信度门控机制

### 4.1 置信度评分规则

| 置信度区间 | 标记 | 处理方式 |
|------------|------|----------|
| ≥ 0.90 | 高置信 | 直接输出，无需标注 |
| 0.70 - 0.89 | 中置信 | 输出时标注 `[需核实:字段]` |
| < 0.70 | 低置信 | 丢弃该字段，输出 `[无法识别]` |

### 4.2 占位符使用规范

当信息不足时，使用以下占位符，**绝不编造**：

| 场景 | 占位符示例 |
|------|------------|
| 责任人无法确定 | `[需核实:行动项负责人]` |
| 截止时间未提及 | `[需核实:截止日期]` |
| 任务描述模糊 | `[需核实:任务具体范围]` |
| 数字/金额听不清 | `[需核实:具体金额]` |

### 4.3 置信度报告

每次处理完成后，生成置信度报告：

```yaml
processing_summary:
  file: meeting1.m4a
  duration_seconds: 2700
  segments_total: 156
  high_confidence: 142 (91.0%)
  medium_confidence: 11 (7.1%)
  low_confidence: 3 (1.9%)
  action_items_extracted: 7
  action_items_validated: 6
  placeholders_used: 2
```

---

## 五、错误码体系

### 5.1 错误码速查表

| 错误码 | 含义 | 用户提示话术 | 修正步骤 |
|--------|------|--------------|----------|
| MP-001 | 文件不存在或路径错误 | "未找到指定的音频文件，请检查路径" | 1. 确认文件路径 2. 检查文件名拼写 3. 确认文件权限 |
| MP-002 | 音频格式不支持 | "该音频格式暂不支持，请转换为MP3/WAV" | 1. 使用ffmpeg转换 2. 重新执行命令 |
| MP-003 | 转写超时 | "转写耗时超过预期，已中断" | 1. 检查音频时长 2. 拆分长音频 3. 增加超时时间参数 |
| MP-004 | 置信度过低 | "转写质量不达标，建议重新录音" | 1. 检查录音环境 2. 提高音频采样率 3. 使用降噪预处理 |
| MP-005 | 输出目录无权限 | "无法写入输出目录，请检查权限" | 1. 修改目录权限 2. 更换输出路径 |
| MP-006 | 批量处理中断 | "批量处理中断，已保存进度" | 1. 使用 --resume 继续 2. 检查失败文件日志 |
| MP-007 | 行动项校验失败 | "行动项格式不符合规范" | 1. 检查JSON格式 2. 确认必填字段 3. 查看校验报告 |

### 5.2 错误处理流程

```
遇到错误
  ↓
读取错误码和提示信息
  ↓
根据修正步骤操作
  ↓
重新执行命令
  ↓
若仍失败 → 查看详细日志（--debug）
```

---

## 六、FAQ 反模式对照

### 6.1 常见坑与反模式

| 常见坑 | 反模式（错误做法） | 正确做法 |
|--------|-------------------|----------|
| 录音质量差 | 直接转写，不检查音频质量 | 先运行 `meeting-pro check-audio` 检查信噪比 |
| 会议超长 | 一次处理3小时以上音频 | 按议程拆分为30-45分钟片段 |
| 多人发言重叠 | 期望完美区分每个说话人 | 接受时间戳分段，不追求说话人分离 |
| 专业术语多 | 直接使用默认模型 | 提供术语表文件 `--glossary terms.txt` |
| 行动项不完整 | 直接采信提取结果 | 运行 `validate` 命令并人工复核 |

### 6.2 反模式对照表

| 场景 | 反模式 | 推荐模式 |
|------|--------|----------|
| 处理失败时 | 反复重试同一命令 | 先查看日志定位原因 |
| 批量处理时 | 并行数设置过大（>4） | 根据CPU核数设置 `--parallel` |
| 输出结果 | 直接覆盖原文件 | 使用独立输出目录，保留原始文件 |
| 置信度标注 | 忽略 `[需核实]` 标记 | 逐条确认并替换占位符 |

---

## 七、渐进式披露：分层次阅读路径

### 7.1 速查卡（30秒上手）

```
1. 安装：pip install meeting-pro
2. 自检：meeting-pro --selftest
3. 处理：meeting-pro process 音频文件.m4a
4. 查看：./results/ 目录下的纪要.md 和 行动项.json
5. 校验：meeting-pro validate 行动项.json
```

### 7.2 新手路径（首次使用）

1. 阅读「一、能力边界」了解适用范围
2. 按「三、标准处理流程」步骤二执行单文件处理
3. 查看输出文件，理解纪要结构和行动项格式
4. 遇到问题查阅「五、错误码体系」

### 7.3 进阶路径（熟练用户）

1. 掌握「四、置信度门控」的占位符处理
2. 配置自定义术语表提升转写准确率
3. 使用批量处理 + 断点续跑处理多会议
4. 编写规则文件定制行动项校验逻辑
5. 集成到CI/CD流程实现会议纪要自动化归档

### 7.4 参数速查表

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `--confidence-threshold` | float | 0.85 | 置信度阈值，低于此值标记占位符 |
| `--output-dir` | str | ./results | 输出目录 |
| `--parallel` | int | 1 | 批量处理并行数 |
| `--resume` | bool | False | 断点续跑 |
| `--glossary` | str | None | 术语表文件路径 |
| `--debug` | bool | False | 输出调试日志 |
| `--timeout` | int | 3600 | 单文件处理超时（秒） |

---

## 八、用户协议

<!-- user-agreement-injected -->

**使用须知：**

1. **责任承担**：使用者自行承担使用本 Skill 的全部责任。因使用本工具产生的任何直接或间接损失，包括但不限于数据丢失、业务中断、决策失误等，开发者不承担任何责任。

2. **禁止反向工程**：不得对本 Skill 的源代码、算法、模型权重进行反向工程、反编译、反汇编或任何形式的破解尝试。

3. **合规使用**：使用者应确保使用本工具处理的内容符合当地法律法规，不侵犯第三方知识产权，不涉及违法违规信息。

4. **数据安全**：使用者应对输入数据的安全性负责，敏感信息请自行评估处理风险。

5. **无担保声明**：本工具按"现状"提供，不附带任何明示或暗示的担保。

---

## 九、许可证（License）

<!-- professional-license-embedded -->

**MIT License**

Copyright (c) 2026 LinguaForge Studio

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

*本 Skill 由 AI 辅助生成，仅供参考。使用前请阅读相关文档并自行验证适用性。*
