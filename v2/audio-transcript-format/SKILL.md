
> 📜 **用户协议（User Agreement）**
> 1. 本 Skill 仅供学习与参考用途。使用本 Skill 产生的任何结果，由使用者自行承担全部责任；本 Skill 不提供任何明示或暗示的保证。
> 2. 涉及法律、财务、税务、投资、医疗等专业决策时，请务必咨询持证专业人士。
> 3. 本代码受版权法保护，未经授权复制、反向工程或商业利用将被追究法律责任。
<!-- user-agreement-injected -->
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
| --export | 导出格式：none / ics / html | none |
| --benchmark | 运行 F1 基准测试 | 关闭 |
| --selftest | 运行内置自测 | 关闭 |

## 三、置信度门控（重要）

**规则提取的置信度分级：**

| 置信度 | 条件 | 处理方式 |
|--------|------|----------|
| 高（≥0.9） | 关键词 + 明确主语 + 无否定/疑问 | 直接提取，标注 ✅ |
| 中（0.7-0.9） | 关键词 + 无主语 或 有模糊时间词 | 提取但标注 ⚠️ 需人工确认 |
| 低（<0.7） | 仅关键词命中，无上下文 | 不提取，仅在 verbose 模式提示 |

**置信度计算规则：**
- 基础分 0.5
- +0.2 有明确主语（人名/角色）
- +0.2 有明确时间词（明天/周五/3月）
- +0.1 有动作动词（提交/完成/联系）
- -0.2 否定句（不需要/不用/别）
- -0.2 疑问句（？/吗/呢）

## 四、错误码速查

| 错误码 | 含义 | 处理方式 |
|--------|------|----------|
| E001 | 输入文件不存在 | 检查路径，确认文件存在 |
| E002 | 输入文件编码无法识别 | 手动指定编码，或转存为 UTF-8 |
| E003 | 输出目录无写入权限 | 检查目录权限，或更换输出路径 |
| E004 | JSON 术语文件格式错误 | 检查 JSON 语法，确认键值对格式 |
| E005 | ICS 导出失败（时间解析错误） | 检查时间词格式，确认可解析 |
| E006 | HTML 导出失败（模板错误） | 检查模板文件完整性 |
| E007 | 参数组合冲突（如 --selftest 与 --input 同时） | 检查参数，确认互斥关系 |
| E008 | 输入文件为空 | 确认文件内容非空 |
| E009 | 输入文件过大（>10MB） | 分块处理或分割文件 |
| E010 | 未知领域词表 | 检查 --domain 参数值 |

## 五、FAQ 与反模式

### 常见问题

**Q1: 为什么我的"那个"被删了？**
A: 只有当"那个/这个"后跟名词（如"那个项目"）时才保留。若后跟动词或单独使用（如"那个，我们…"），视为填充词删除。

**Q2: 提取的待办事项不准确怎么办？**
A: 检查是否使用了正确的 --domain 参数。法律/医疗领域有专属词表，通用词表可能漏提。

**Q3: 如何批量处理多个文件？**
A: 当前版本不支持批量，建议使用 shell 循环：
```bash
for f in *.txt; do python run.py --input "$f" --output "${f%.txt}_整理.txt" --force; done
```

**Q4: 为什么 --extract json 输出为空？**
A: 可能原因：1) 文本中没有匹配的决策关键词；2) 所有匹配均为否定/疑问句被过滤；3) 置信度低于阈值。

**Q5: ICS 文件导入日历乱码？**
A: 确保使用 UTF-8 编码保存 .ics 文件，部分旧版日历应用需手动选择 UTF-8。

### 反模式（不要这样做）

| 反模式 | 为什么不行 | 正确做法 |
|--------|-----------|----------|
| 用 --force 直接覆盖原文件 | 丢失原始口语稿，无法回溯 | 先预览 diff，确认后输出到新文件 |
| 依赖提取结果做法律/医疗决策 | 规则提取非 100% 准确 | 人工复核所有提取项 |
| 在 --selftest 失败时继续使用 | 环境可能有问题，结果不可信 | 先修复环境，确保 40/40 通过 |
| 用 --max-len 截断长文本 | 违反 O(n) 性能要求，丢失上下文 | 直接处理完整文本，算法已优化 |
| 期望识别说话人身份 | 本工具不区分发言人 | 使用专业转写工具获取说话人标签 |

## 六、最佳实践

1. **先预览后落盘**：默认 dry-run 模式，确认 diff 无误后再 --force
2. **领域词表要选对**：法律/医疗场景务必指定 --domain，否则提取质量下降
3. **定期跑基准**：修改代码后执行 --benchmark，确保 F1 不下降
4. **保留原始稿**：整理稿与原始稿分开保存，便于审计
5. **人工复核提取项**：所有提取结果均带原文句索引，建议人工核对
6. **使用 --verbose 调试**：结果异常时，用 --verbose 查看每步修改明细

## 七、安装与配置

### 环境要求

- Python 3.8+
- 无第三方依赖（纯标准库）

### 安装步骤

```bash
# 1. 下载 run.py 到本地
# 2. 赋予执行权限（可选）
chmod +x run.py
# 3. 验证安装
python run.py --selftest
```

### 术语映射文件格式（--terms）

```json
{
  "AI": "人工智能",
  "ML": "机器学习",
  "NLP": "自然语言处理"
}
```

## 八、相关资源

- 源码仓库：https://github.com/your-repo/audio-transcript-format
- 问题反馈：https://github.com/your-repo/audio-transcript-format/issues
- 更新日志：https://github.com/your-repo/audio-transcript-format/CHANGELOG.md

---

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->

**版本历史：**
- v4.2.0：新增 HTML 手术报告、F1 基准度量（149 条黄金语料）
- v4.1.0：领域词表贯通到整理阶段、性能优化（正则预编译）
- v4.0.0：4 领域词表、ICS 导出、基准度量
- v3.0.0：决策记录提取（待办/截止/异议/决策）
- v2.0.0：段落分割、列表化
- v1.0.0：基础格式化（分句/填充词清理/标点修复）

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
