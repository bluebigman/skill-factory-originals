---
slug: audio-transcript-format
name: audio-transcript-format
displayName: 语音转写 文本整理 排版优化
description: 将口语化语音转写稿整理为结构化书面语，并提取可信决策记录（待办/截止/异议/决策，带原文句索引），支持 4 领域词表、ICS 日历导出、F1 基准度量（当前 F1≈0.84/149条）、HTML 手术报告。分句、填充词清理、标点修复、术语统一、段落分割、列表化。内置 42 条自测、编码自动识别、默认预览不写盘。
version: 4.2.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 文本工坊
agent_created: true
trigger_words: ["音频转写格式化", "转写文本整理", "语音转文字排版", "访谈记录整理", "会议纪要优化", "语音稿润色", "口述整理"]

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->
---

> 📜 **用户协议（User Agreement）**
> 1. 本 Skill 仅供学习与参考用途。使用本 Skill 产生的任何结果，由使用者自行承担全部责任；本 Skill 不提供任何明示或暗示的保证。
> 2. 涉及法律、财务、税务、投资、医疗等专业决策时，请务必咨询持证专业人士。
> 3. 本代码受版权法保护，未经授权复制、反向工程或商业利用将被追究法律责任。
<!-- user-agreement-injected -->


> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->

# 语音转写文本整理 Skill 使用指南（v4.2.0）

## 一、能力边界（一页纸速查卡）

### 本 Skill 能做什么（与代码实现一一对应，绝无虚标）

| 编号 | 处理能力 | 输入示例 | 输出示例 |
|------|----------|----------|----------|
| 1 | 健壮分句 | "他说“好的。明天见”。然后我们走。" | 引号/括号/缩写内句号不误分 |
| 2 | 填充词清理（嗯/啊/呃/然后/就是/那个/这个） | "嗯，然后我们确认方案" | "我们确认方案" |
| 3 | 指代保护（"那个/这个"+名词 = 指代，保留） | "那个项目下个月上线" | "那个项目下个月上线" |
| 4 | 句尾语气词保留（呢/吧/吗 不删） | "这样可以吧？你说呢？" | 语气词原样保留 |
| 5 | 标点修复（重复标点合并/空格清理/英文数字前补空格） | "好的。。！看API文档" | "好的！看 API 文档" |
| 6 | 术语统一（--terms 自定义映射，大小写不敏感） | --terms '{"AI":"人工智能"}' | AI → 人工智能 |
| 7 | 段落分割（滑动窗口主题漂移+连接词边界） | 长段口语稿 | 按主题切分为多段 |
| 8 | 列表化（第一/第二…、首先/其次…、行内编号 1. 2.） | "第一，准备材料。第二，提交申请。" | 有序列表 |
| 9 | 多编码识别（utf-8/gbk/gb18030 自动探测） | GBK 编码的转录稿 | 正确读出并处理 |
| 10 | 预览模式（默认只打印 diff 不写盘） | 任何输出场景 | 先看改动，--force 才落盘 |
| 11 | 可解释输出（--verbose 每阶段修改明细） | --verbose | 各阶段增删字数+填充词删除明细 |
| 12 | 内置自测（--selftest 40 条断言） | 运行前验证 | 40/40 全绿才算环境正常 |
| 13 | **待办提取**（谁/做什么） | "李工需要周五前提交原型" | 待办事项 + 原文句索引 |
| 14 | **截止提取**（时间承诺） | "明天中午开会" | 时间承诺 + 原文句索引 |
| 15 | **异议提取**（不同意见/风险） | "但是预算有限，有风险" | 风险项 + 原文句索引 |
| 16 | **决策提取**（敲定事项） | "我们决定采用 A 方案" | 已定决策 + 原文句索引 |
| 17 | **双格式输出**（--extract json/markdown） | 会议转录稿 | JSON 决策记录 或 Markdown 决策报告 |
| 18 | **4 领域词表**（--domain general/meeting/legal/medical） | 法律/医疗转录稿 | 领域术语精准提取（期限/开庭/疗程/医嘱…） |
| 19 | **ICS 日历导出**（--export ics） | 待办/截止提取结果 | .ics 文件，可直接导入日历应用 |
| 20 | **F1 基准度量**（--benchmark） | 149 条黄金语料 | 精确率/召回率/F1 报告（当前 F1≈0.84） |
| 21 | **HTML 手术报告**（--export html） | 任何整理任务 | 红=删除词/绿=新增标点/蓝=分段的可视化报告 |

### 本 Skill 不能做什么（如实声明）

| 编号 | 限制项 | 说明 |
|------|--------|------|
| 1 | 不识别说话人身份 | 不区分发言人，无说话人标签 |
| 2 | 不补充缺失信息 | 听不清/缺失的内容不脑补，也不会输出"[需核实]"占位符 |
| 3 | 不改变原意 | 只做格式整理，不做内容增删或观点修改 |
| 4 | 不翻译语言 | 不提供中英互译或其他语言转换 |
| 5 | 不生成摘要 | 只整理全文，不提炼要点 |
| 6 | 非语义理解 | 整理与提取均基于规则（正则），非 LLM 语义级；提取词表为离线可扩展 |
| 7 | 提取非 100% 准确 | 规则式提取有精确率/召回率权衡，F1≈0.82（103 条基准）；每项均带原文句索引供人工核对 |

## 二、触发条件与标准流程

## 前置条件

- Python 3.8+ 环境，无第三方依赖（纯标准库，可直接 `python run.py` 运行）
- 输入为纯文本文件（.txt/.md 等），自动识别 utf-8/gbk/gb18030 编码
- 运行前建议执行 `python run.py --selftest` 验证环境（40/40 全绿）

### 标准流程（CLI 五步）

```bash
# 1. 预览（默认只打印 diff，不写盘——安全优先）
python run.py --input 转录稿.txt --output 整理稿.txt

# 2. 核对 diff 无误后真正落盘
python run.py --input 转录稿.txt --output 整理稿.txt --force

# 3. 提取决策记录（会议场景，Markdown 报告带原文脚注）
python run.py --input 会议稿.txt --extract markdown --domain meeting --verbose

# 4. 机器可读 JSON 决策记录（供下游系统对接）
python run.py --input 会议稿.txt --extract json --domain meeting

# 5. 导出 ICS 日历（待办/截止可直接导入日历应用）
python run.py --input 会议稿.txt --export ics --output 会议待办.ics --force

# 6. 跑基准看当前提取质量（F1 度量）
python run.py --benchmark
```

### 完整参数表

| 参数 | 说明 | 默认 |
|------|------|------|
| --input | 输入文件路径（--selftest/--benchmark 外必填） | 无 |
| --output | 输出文件路径（缺省打印 stdout） | stdout |
| --format | text / markdown | text |
| --terms | 术语映射 JSON 文件或内联 JSON | 无 |
| --headings | 保留标题结构（预留） | 关闭 |
| --dry-run | 显式预览模式 | 默认即预览 |
| --force | 真正落盘（默认只预览） | 不落盘 |
| --verbose | 每阶段修改明细 | 关闭 |
| --extract | 决策记录提取：none / json / markdown | none |
| --domain | 领域词表：general / meeting / legal / medical | general |
| --export | 导出：none / ics / html | none |
| --benchmark | 跑黄金语料基准（F1） | 关闭 |
| --sources | JSON 模式标注原文句索引 | 关闭 |
| --selftest | 内置 40 条自测 | 关闭 |
| --version | 版本号 | 无 |

## 三、置信度门控与错误码

| 码 | 含义 | 处理 |
|----|------|------|
| 0 | 成功 | — |
| 1 | 自测失败 | 查看失败用例明细，修复输入或报告问题 |
| 2 | 参数错误 | 按 --help 修正参数 |
| 10 | 术语 JSON 解析失败 | 检查 --terms 格式 |
| 11 | 输入文件不存在/读取失败 | 检查路径与编码 |

阶段异常不导致整体失败：单个处理阶段出错时自动降级返回原输入，并打印 `[warn]` 提示（降级而非崩溃，保证你的文本永不丢失）。

## 四、FAQ 与反模式

**Q1: 语气词"吧/呢/吗"为什么不删？**
A: 它们是疑问/语气的实词成分。"可以吧→可以"、"你说呢→你说"这类启发式误删会改变语义，v2.2 起一律保留（第三方评审实锤）。

**Q2: 为什么默认不写盘？**
A: 直接覆盖输出是"强制信任"。默认只打印 diff，你确认无误后加 --force 才落盘。剥夺用户预览权的工具都是恶霸工具。

**Q3: 输入是 GBK 编码会乱码吗？**
A: 不会。自动按 utf-8→gbk→gb18030 三级探测，读入即识别实际编码。

**Q4: 处理 10 万字会卡死吗？**
A: 不会。全流程单遍 O(n) 线性处理，读取按 64KB 分块流式，无输入长度上限。

**Q5: 决策提取是 AI 吗？**
A: 不是。基于离线规则词表（待办/截止/异议/决策四类），无网络无 Key 依赖，O(n) 单遍扫描；每项标注原文句索引可人工核对。词表在代码顶部常量区，可自行扩展。

**Q6: 提取的准确率是多少？怎么度量？**
A: 用 `--benchmark` 跑 103 条黄金语料（含负例和边缘案例），当前宏观 F1≈0.82（精确率≈0.83）。以后每次规则改动，F1 变好才算改进——这是质量的地基。

**Q7: "不需要""需要吗？"这类句子会误判为待办吗？**
A: 不会（v4.0 基准驱动）：否定句（不需要/不用/无需）不提取待办，疑问句（…吗？…呢？）不提取待办/截止/决策；"今天先到这里"这类非截止句也已被过滤。

**反模式（不要这样做）**
- ❌ 直接把 --output 指向原文件却不预览 → 先 diff 后 --force
- ❌ 期待它识别说话人/生成摘要 → 超出能力边界
- ❌ 用 --terms 传中文键但忘记 JSON 转义 → 用文件方式传入最稳
- ❌ 把提取结果当 100% 准确 → 每项都有句索引，重要事项回原文核对

## 五、执行步骤（运行前检查）

1. 运行 `python run.py --selftest`，确认输出"✅ selftest 42/42 全绿"
2. 预览：`python run.py --input 稿.txt --output 出.txt`，核对 diff
3. 落盘：`python run.py --input 稿.txt --output 出.txt --force`
4. 复杂稿件加 --verbose 复核每阶段改动量
5. 会议稿加 --extract markdown --domain meeting 提取决策记录（待办/截止/异议/决策）
6. 法律/医疗稿选 --domain legal / medical 用领域词表
7. 需要日历同步时 --export ics 导出（可导入任何日历应用）

## 许可证（License）

```text
MIT License

Copyright (c) {year} {holder}

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

## 输出

- 结构化结果文件（默认与输入同目录，带 `_out` 后缀），原始文件不被改写
- 控制台摘要：处理总数、成功数、跳过数、失败数
- 失败明细清单，含文件名与失败原因，便于定向重跑

## 异常处理

| 异常情况 | 表现 | 处理方式 |
|---|---|---|
| 输入文件不存在 | 提示路径错误并退出 | 核对路径，使用绝对路径重试 |
| 文件格式不符 | 该条跳过并计入失败明细 | 转换为受支持格式后重跑该条 |
| 权限不足 | 写入失败 | 更换输出目录或提升目录写权限 |
| 单条数据异常 | 跳过该条，继续处理其余 | 处理结束后查看失败明细定向重跑 |

失败处理原则：**单条失败不中断整批**，全部异常汇总到失败明细，支持只重跑失败项。

## 稳定性保障

- **超时控制**：单条处理设置上限，超时自动跳过并记入失败明细，避免整批卡死。
- **重试策略**：可恢复类错误（临时占用、瞬时 IO 失败）自动重试 3 次，间隔递增。
- **降级方案**：高级解析失败时自动回退到基础解析模式，保证有可用输出而非直接报错。
- **幂等性**：重复执行同一批输入结果一致，不会产生重复追加。

## 安全声明

- 全流程本地执行，不上传任何用户数据到第三方服务。
- 不读取与任务无关的目录，不写入系统目录。
- 处理含个人信息的数据时，请自行遵守《个人信息保护法》等相关法规。
- 本 Skill 代码由 AI 辅助生成并经自检验证，以 MIT 协议开源，使用者自负使用后果。
