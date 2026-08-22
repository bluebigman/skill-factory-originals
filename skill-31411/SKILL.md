---
slug: skill-31411
name: clickbait-detector
displayName: 标题猎手 内容辨识 合规校验
description: 识别标题党内容，提供评分、分类、改写与合规检查的一站式处理方案。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 林墨研
agent_created: true
trigger_words: ["标题党", "clickbait", "标题检测", "标题评分", "标题改写", "标题合规", "标题去重", "标题整理"]

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

---

# 标题猎手：标题党识别与内容治理工具

## 一、能力边界速查卡

本工具聚焦于标题文本的**质量评估**与**合规治理**，不涉及正文内容分析、搜索引擎排名优化或流量预测。

| 能力维度 | 支持范围 | 明确不支持 |
|---------|---------|-----------|
| 识别评分 | 基于夸张词、悬念断裂、事实夸大等维度打分（0-100） | 不评估标题的文学美感或艺术价值 |
| 分类标注 | 区分"夸张型""悬念型""事实误导型""正常型"四类 | 不判断作者主观意图，仅依据文本特征 |
| 批量整理 | 支持 CSV/JSON 格式输入，单批上限 10,000 条 | 不处理图片、PDF 或扫描件中的标题 |
| 改写生成 | 提供 3-5 个替代标题变体，保留原意 | 不保证改写后的点击率或传播效果 |
| 合规校验 | 检测广告法禁用词、绝对化用语、虚假承诺 | 不提供法律意见，仅作技术性提示 |
| 效果预估 | 基于历史语料给出"吸引力指数"参考区间 | 不承诺具体流量、转化率或收益数值 |
| 去重合并 | 识别近似重复标题（相似度 >85%） | 不处理跨语言语义重复 |

**适用对象**：内容编辑、新媒体运营、SEO 专员、合规审核人员、批量内容管理团队。

---

## 二、触发方式与场景映射

当你的工作流中出现以下任一场景，即可调用本工具：

| 触发词/场景 | 大白话解释 | 推荐操作 |
|------------|-----------|---------|
| "帮我看看这个标题是不是标题党" | 单条标题快速体检 | 直接输入标题文本，获取评分与分类 |
| "这批文章标题需要过一遍" | 批量检测与整理 | 准备 CSV/JSON 文件，执行批量处理 |
| "这个标题能发吗？会不会违规" | 发布前合规检查 | 运行 `compliance` 校验命令 |
| "标题太平淡了，帮我改几个" | 标题优化与变体生成 | 使用 `rewrite` 命令生成候选 |
| "这些标题好多重复的" | 内容去重与合并 | 使用 `dedupe` 命令清理冗余 |

---

## 三、标准操作流程

### 前置条件

- 输入文件格式：CSV（首列为标题文本）或 JSON（数组或 `{ "titles": [...] }` 结构）
- 单条标题长度：2-60 个字符（超出部分截断处理）
- 运行环境：Python 3.8+，安装 `clickbait-detector` 包

### 执行步骤

#### 步骤 1：环境自检

```bash
clickbait-detector --selftest
```

预期输出：`All systems operational` 或列出缺失依赖项。

#### 步骤 2：单条检测（快速模式）

```bash
clickbait-detector "震惊！你绝对不知道的五个秘密"
```

输出 JSON 格式结果：

```json
{
  "title": "震惊！你绝对不知道的五个秘密",
  "score": 87,
  "category": "夸张型",
  "signals": ["震惊体", "绝对化用语", "悬念断裂"],
  "compliance": {
    "status": "warning",
    "issues": ["使用'绝对'属广告法敏感词"]
  }
}
```

#### 步骤 3：批量处理（含 dry-run 预览）

```bash
# 先预览将执行的操作
clickbait-detector batch input.csv --dry-run

# 确认无误后正式执行
clickbait-detector batch input.csv --output results.json --format json
```

`--dry-run` 会输出每行将被如何处理，不写入任何文件。

#### 步骤 4：合规校验（发布前必做）

```bash
clickbait-detector compliance input.csv --report compliance_report.md
```

校验项包括：
- 绝对化用语（最、第一、顶级、100% 等）
- 虚假承诺（"保证""必看""速成"等）
- 医疗/金融敏感词（未经证实的功效宣称）

#### 步骤 5：改写生成

```bash
clickbait-detector rewrite "震惊！你绝对不知道的五个秘密" --style balanced
```

输出 3-5 个变体，风格参数可选：`conservative` / `balanced` / `engaging`。

#### 步骤 6：去重合并

```bash
clickbait-detector dedupe input.csv --threshold 0.85 --output deduped.csv
```

相似度超过阈值的条目会被标记，保留首次出现的版本。

### 输出规范

- **JSON 格式**：包含 `title`、`score`、`category`、`signals`、`compliance` 字段
- **Markdown 格式**：生成表格化报告，含评分分布、问题汇总、修改建议
- **大文件处理**：超过 10,000 条时自动启用流式分块，每 1,000 条输出中间进度

---

## 四、置信度门控

当遇到以下情况时，工具会输出 `[需核实:字段]` 占位符，而非编造结果：

| 场景 | 输出示例 | 处理建议 |
|------|---------|---------|
| 标题含生僻行业术语 | `[需核实:术语定义]` | 人工确认术语含义后重新检测 |
| 合规词库未覆盖的新词 | `[需核实:合规状态]` | 咨询法务或使用 `--update-lexicon` 更新词库 |
| 非中文标题 | `[需核实:语言支持]` | 当前版本仅支持中文标题检测 |
| 输入格式无法解析 | `[需核实:输入格式]` | 检查 CSV/JSON 结构是否符合规范 |

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|---------|---------|
| `E001` | 输入为空 | "未检测到标题文本，请检查输入" | 确认输入文件非空，或直接传入标题字符串 |
| `E002` | 格式不支持 | "仅支持 CSV 或 JSON 格式" | 转换文件格式后重试 |
| `E003` | 单条标题超长 | "标题长度超过 60 字符，已截断处理" | 手动截断或调整输入 |
| `E004` | 合规词库加载失败 | "合规词库缺失，请运行 --update-lexicon" | 执行词库更新命令 |
| `E005` | 批量处理中断 | "处理中断于第 N 条，已保存断点" | 使用 `--resume` 从断点继续 |
| `E006` | 输出目录无权限 | "无法写入目标目录，请检查权限" | 修改目录权限或指定其他输出路径 |

---

## 六、常见误区与反模式对照

| 误区（反模式） | 正确做法 | 说明 |
|---------------|---------|------|
| 把评分当绝对真理 | 将评分作为参考，结合人工判断 | 评分基于统计特征，不替代编辑判断 |
| 合规检查只跑一次 | 每次修改后重新校验 | 改写后的标题可能引入新的合规风险 |
| 直接采用 AI 改写结果 | 人工选择并微调 | AI 变体需匹配品牌调性，建议二次编辑 |
| 忽略 dry-run 步骤 | 批量操作前必跑预览 | 避免误操作导致文件被覆盖 |
| 用同一阈值处理所有场景 | 按渠道调整评分阈值 | 不同平台对标题夸张程度的容忍度不同 |
| 认为去重只处理完全重复 | 设置合理相似度阈值 | 近似重复同样影响内容质量评估 |

---

## 七、分层次阅读路径

### 新手快速上手（5 分钟）

1. 运行 `--selftest` 确认环境
2. 用单条检测模式测试一条标题
3. 查看 JSON 输出中的 `score` 和 `category` 字段
4. 对需要发布的标题运行 `compliance` 检查
5. 阅读输出报告中的修改建议

### 进阶使用（深度治理）

1. 掌握批量处理流程，善用 `--dry-run` 预览
2. 理解评分信号的具体含义（`signals` 字段）
3. 自定义合规词库，适配行业特定要求
4. 结合 `--verbose` 查看评分决策的详细依据
5. 建立定期批量检测的自动化流程

### 参数速查表

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `--dry-run` | 布尔 | false | 预览操作不写入文件 |
| `--verbose` | 布尔 | false | 输出详细评分依据 |
| `--threshold` | 浮点 | 0.85 | 去重相似度阈值 |
| `--style` | 字符串 | balanced | 改写风格（conservative/balanced/engaging） |
| `--format` | 字符串 | json | 输出格式（json/markdown） |
| `--output` | 字符串 | stdout | 输出文件路径 |
| `--resume` | 布尔 | false | 从断点继续处理 |
| `--update-lexicon` | 布尔 | false | 更新合规词库 |

---

## 八、用户协议

使用本 Skill 即表示您同意以下条款：

1. **责任承担**：使用者自行承担使用本工具产生的全部责任。本工具提供的评分、分类、合规提示等信息仅供参考，不构成任何专业建议或法律意见。
2. **禁止反向工程**：不得对本 Skill 的底层算法、评分模型、词库结构进行反向工程、破解、反编译或提取核心逻辑。
3. **合理使用**：不得将本工具用于批量生成违规内容、规避平台规则、或任何违反法律法规的活动。
4. **无担保声明**：本工具按"现状"提供，不附带任何明示或暗示的担保，包括但不限于适销性、特定用途适用性和非侵权保证。

<!-- user-agreement-injected -->

---

## 九、许可证（License）

本 Skill 采用 MIT 许可证发布：

```
MIT License

Copyright (c) 2024 林墨研

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

*本 Skill 由 AI 辅助生成，仅供参考。使用前请阅读相关文档，并结合实际场景验证输出结果。*
