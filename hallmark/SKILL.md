---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: hallmark
name: hallmark
displayName: 文本净化 原创性审查 痕迹检测
description: 识别AI生成痕迹，净化文本风格，辅助原创性审查与内容校准。
version: 1.0.3
rules_version: cpr-20260813-n401
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/hallmark
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 墨规工作室
agent_created: true
trigger_words: ["hallmark", "anti-ai-slop", "去AI味", "AI痕迹检测", "文本净化", "原创性审查", "内容校准", "风格清洗"]
---

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->


> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# hallmark — 文本净化与原创性审查 Skill

## 一、能力边界：一页纸速查卡

### 1.1 能做什么（✅ 支持范围）

| 能力项 | 说明 | 适用对象 |
|--------|------|----------|
| AI 痕迹识别 | 检测文本中高频出现的 AI 生成特征（如过度工整的排比、机械化的连接词、缺乏个人语感的转折） | 文章、报告、论文、营销文案 |
| 风格净化 | 对检测出的 AI 痕迹进行改写，保留原意，注入更自然的人类表达节奏 | 博客、公众号推文、产品说明 |
| 原创性辅助审查 | 输出疑似 AI 生成片段的位置与特征标签，供人工复核 | 学术论文、投稿稿件、竞标文件 |
| 批量处理 | 支持多文件批量执行，输出结构化结果 | 内容团队批量审稿、平台内容巡检 |

### 1.2 不能做什么（❌ 不支持范围）

| 限制项 | 说明 |
|--------|------|
| 不替代查重系统 | 本工具不比对数据库，不提供相似度百分比 |
| 不保证绝对原创 | 净化后的文本仍需人工确认，不承诺"零 AI 痕迹" |
| 不处理图片/PDF | 仅支持纯文本文件（.txt / .md / .docx 需先转文本） |
| 不提供法律效力 | 检测结果仅供参考，不构成学术不端或法律纠纷的判定依据 |

### 1.3 适用对象速查

- **内容创作者**：需要降低 AI 辅助写作痕迹的博主、作者
- **编辑/审稿人**：需要快速定位可疑 AI 生成段落的编辑团队
- **学术人员**：需要自查论文语言风格是否过于"机器味"的研究者
- **运营人员**：需要批量清洗历史 AI 生成内容的平台运营

---

## 二、触发方式：场景映射表

| 触发词/短语 | 典型使用场景 | 预期响应 |
|-------------|--------------|----------|
| `hallmark` | 命令行直接调用 | 执行检测或净化流程 |
| `anti-ai-slop` | 需要去除 AI 味的长文处理 | 启动风格净化模式 |
| `去AI味` | 中文内容口语化改写 | 输出净化后的文本 |
| `AI痕迹检测` | 审查稿件是否像 AI 写的 | 输出检测报告 |
| `文本净化` | 批量清洗历史内容 | 批量处理并生成汇总 |
| `原创性审查` | 投稿前自查 | 输出风险片段清单 |
| `内容校准` | 调整文风一致性 | 按目标风格校准 |
| `风格清洗` | 去除模板化表达 | 重写模板化段落 |

---

## 三、标准流程：从输入到输出

### 3.1 前置条件

| 条件项 | 要求 |
|--------|------|
| 文件格式 | `.txt` 或 `.md`，UTF-8 编码 |
| 文件命名 | 建议 `input_文件名.txt`，避免特殊字符 |
| 目录结构 | 所有待处理文件置于同一目录，建议创建 `input/` 和 `output/` 子目录 |
| 备份要求 | 处理前自动备份原始文件至 `backup/` 目录 |

### 3.2 执行步骤（分步编号）

1. **准备输入**：将待处理文件放入 `input/` 目录，确认命名规范一致（如 `article_001.txt`）。
2. **试运行**：先用单个样本执行，核对输出字段与格式是否符合预期。
   ```bash
   hallmark --file input/article_001.txt --mode detect
   ```
3. **核对输出**：检查检测报告中的字段（见 3.3 输出规范），确认无误。
4. **批量执行**：确认无误后对全量数据执行，并保留原始文件备份。
   ```bash
   hallmark --dir input/ --mode purify --output output/
   ```
5. **校验结果**：抽查输出条目，核对关键字段与源数据一致（如段落数、关键术语是否保留）。

### 3.3 输出规范

**检测模式输出（JSON 格式）**：

```json
{
  "file": "article_001.txt",
  "ai_score": 0.72,
  "suspicious_segments": [
    {
      "position": [12, 18],
      "feature": "excessive_parallelism",
      "snippet": "不仅...而且...同时..."
    }
  ],
  "recommendation": "review"
}
```

**净化模式输出（文本 + 报告）**：

- `output/` 目录下生成净化后的 `.md` 文件
- 同时生成 `report_文件名.json`，包含修改点清单（原句 → 改后句 → 修改原因）

---

## 四、置信度门控：不编造原则

当检测信息不足时，遵循以下规则：

| 场景 | 处理方式 |
|------|----------|
| 文本过短（< 50 字） | 输出 `[需核实:文本长度不足，无法可靠检测]` |
| 语言非中英文 | 输出 `[需核实:暂不支持该语言]` |
| 文件读取失败 | 输出 `[需核实:文件无法读取，请检查编码]` |
| 特征不明确 | 输出 `[需核实:特征模糊，建议人工复核]` |

**核心原则**：宁可输出占位符，绝不编造检测结果或评分。

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| `E001` | 文件不存在 | "未找到指定文件，请检查路径" | 确认文件路径，重新输入 |
| `E002` | 编码不支持 | "文件编码非 UTF-8，请转换后重试" | 使用文本编辑器另存为 UTF-8 |
| `E003` | 目录为空 | "输入目录中无待处理文件" | 将文件移入 input/ 目录 |
| `E004` | 输出目录不可写 | "无法写入输出目录，请检查权限" | 修改目录权限或更换路径 |
| `E005` | 批量处理中断 | "批量处理在第 N 个文件中断" | 查看日志，修复问题后从断点继续 |

---

## 六、FAQ 反模式对照

| 常见坑 | 反模式（错误做法） | 正确做法 |
|--------|-------------------|----------|
| 过度依赖评分 | 直接根据 ai_score 判定"这是 AI 写的" | 将评分作为参考，结合人工阅读判断 |
| 忽略上下文 | 单独抽取句子判断，脱离段落语境 | 至少以段落为单位进行检测 |
| 净化后不校对 | 直接使用净化输出，不检查语义是否改变 | 逐条核对修改点，确认原意保留 |
| 批量处理不备份 | 直接覆盖原文件 | 始终保留 backup/ 目录的原始文件 |
| 期望绝对准确 | 认为检测结果 100% 可靠 | 理解检测是概率性的，重要内容必须人工复核 |

---

## 七、渐进式披露：分层次阅读路径

### 7.1 速查卡（30 秒上手）

```
1. 放文件到 input/
2. 跑单文件测试：hallmark --file input/test.txt --mode detect
3. 看 JSON 报告，确认格式
4. 批量净化：hallmark --dir input/ --mode purify --output output/
5. 抽查 output/ 结果，核对修改点
```

### 7.2 新手路径（首次使用）

- 阅读「一、能力边界」了解工具边界
- 按「三、标准流程」执行一次完整流程
- 遇到问题查「五、错误码体系」
- 完成后阅读「六、FAQ 反模式」避免常见错误

### 7.3 进阶路径（深度用户）

- 自定义检测特征：修改配置文件中的 `feature_weights` 参数
- 批量处理优化：使用 `--threads 4` 并行处理，注意 CPU 负载
- 集成到 CI/CD：将检测命令嵌入内容发布流水线，自动拦截高 AI 评分内容
- 二次开发：基于输出 JSON 构建自定义报告或可视化面板

---

## 八、参数参考表

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `--file` | string | 无 | 指定单个文件处理 |
| `--dir` | string | 无 | 指定目录批量处理 |
| `--mode` | enum | `detect` | `detect`（检测）或 `purify`（净化） |
| `--output` | string | `output/` | 输出目录路径 |
| `--threshold` | float | `0.6` | AI 评分阈值，高于此值标记为可疑 |
| `--threads` | int | `1` | 并行线程数（批量模式） |
| `--selftest` | flag | 无 | 运行自检，验证安装正确性 |
| `--version` | flag | 无 | 显示版本号 |

---

## 九、用户协议

<!-- user-agreement-injected -->

**使用本 Skill 即表示您同意以下条款：**

1. **责任承担**：使用者自行承担全部责任。本工具输出的检测结果和净化建议仅供参考，不构成任何形式的专业判断或法律意见。因使用本工具产生的任何直接或间接损失，工具作者不承担任何责任。

2. **禁止反向工程**：禁止对本 Skill 的代码、算法、模型权重进行反向工程、反编译、破解或试图提取底层逻辑。

3. **合规使用**：使用者应确保使用场景符合当地法律法规及平台政策，不得将本工具用于学术不端、欺诈或任何非法用途。

4. **无担保声明**：本工具按"现状"提供，不附带任何明示或暗示的担保，包括但不限于适销性、特定用途适用性和非侵权保证。

---

## 十、许可证（License）

<!-- professional-license-embedded -->

**MIT License**

```
MIT License

Copyright (c) 2026 墨规工作室

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

---

*本 Skill 由 AI 辅助生成，仅供参考。使用前请阅读相关文档。*
