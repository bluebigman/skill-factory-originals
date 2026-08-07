---
slug: code-review-report
name: code-review-report
displayName: 代码审查 差异分析 质量报告
description: 解析 git diff，规则扫描硬编码密码/不安全日志/性能反模式/平台依赖，输出分级审查报告（markdown/json），支持严重级过滤、密码脱敏、默认预览不写盘。内置 12 条自测。
version: 2.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 独立技能工坊
agent_created: true
trigger_words: ["code-review-report","代码审查","代码评审","diff审查","变更检查","代码走查","差异检视","--selftest","--version"]

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

# 代码审查报告 Skill 使用指南（v2.0.0）

## 一、能力边界（与代码实现一一对应，绝无虚标）

### 本 Skill 能做什么

| 编号 | 处理能力 | 输入示例 | 输出示例 |
|------|----------|----------|----------|
| 1 | 解析 git diff（严格校验，快速失败） | git diff 输出文件 | 结构化 hunk 列表，非法格式立即报错 |
| 2 | SEC001 硬编码密码/密钥检测 | `password = "secret123"` | P0 问题，**密码脱敏显示 `se***`** |
| 3 | LOG001 格式化字符串进日志 | `logging.debug(f"user={u}")` | P1 问题 |
| 4 | PERF001 循环内 range(len()) | `for i in range(len(x))` | P1 问题 |
| 5 | STD001 平台特定命令执行 | `os.system("...")` | P2 问题 |
| 6 | 注释/字符串剥离（tokenize） | 注释里的 `range(len())` | **不误报** |
| 7 | 严重级过滤（--filter） | `--filter P0` | 只输出 P0（参数真实生效） |
| 8 | 双格式输出（--format md/json） | 任意 diff | Markdown 报告 或 JSON 结构化 |
| 9 | 密码脱敏 | 检测到明文密码 | 报告只含前 2 位+***，明文绝不外泄 |
| 10 | 预览模式（默认只打印 diff 不写盘） | 任何输出场景 | --force 才落盘 |
| 11 | 多编码识别（utf-8/gbk/gb18030） | GBK 编码 diff | 正确读取 |
| 12 | 内置自测（--selftest 12 条断言） | 运行前验证 | 12/12 全绿 |

### 本 Skill 不能做什么（如实声明）

| 编号 | 限制项 | 说明 |
|------|--------|------|
| 1 | 非语义级审查 | 基于规则（正则+tokenize），不做 LLM 语义理解 |
| 2 | 不覆盖全部反模式 | 内置 4 条规则（SEC001/LOG001/PERF001/STD001），规则清单见 FAQ |
| 3 | 不做格式美化 | 只输出报告，不修改代码 |
| 4 | 不识别私有 API | 无网络请求，纯离线 |

## 二、触发条件与标准流程

## 前置条件

- Python 3.8+ 环境，无第三方依赖（纯标准库）
- 输入为 git diff 格式文本文件（.diff/.patch/.txt），自动识别编码
- 运行前建议 `python run.py --selftest` 验证（12/12 全绿）

### 标准流程

```bash
# 1. 预览（默认只打印报告不写盘）
python run.py --diff change.diff

# 2. 只查 P0 严重问题
python run.py --diff change.diff --filter P0

# 3. 输出 JSON 供下游系统对接
python run.py --diff change.diff --format json

# 4. 落盘
python run.py --diff change.diff --output report.md --force
```

### 完整参数表

| 参数 | 说明 | 默认 |
|------|------|------|
| --diff | diff 文件路径（必填） | 无 |
| --output | 输出文件路径（缺省 stdout） | stdout |
| --format | md / json | md |
| --filter | 严重级过滤，逗号分隔（P0,P1） | 全部 |
| --dry-run | 显式预览 | 默认即预览 |
| --force | 真正落盘 | 不落盘 |
| --verbose | 每文件命中明细 | 关闭 |
| --selftest | 内置 12 条自测 | 关闭 |
| --version | 版本号 | 无 |

## 三、错误码

| 码 | 含义 |
|----|------|
| 0 | 成功 |
| 1 | 自测失败 |
| 2 | 参数错误 |
| 10 | diff 解析失败（格式不兼容，快速失败，绝不输出虚假报告） |

## 异常处理与失败恢复

- **diff 格式不兼容**：快速失败（fail-fast），立即返回错误码 10 并提示"格式不兼容"，**绝不生成行号错乱的虚假报告**——错误数据比崩溃更危险。
- **输入文件读取失败/编码无法识别**：返回错误码 10，提示检查路径与编码（utf-8→gbk→gb18030 已自动探测兜底）。
- **参数错误**：返回错误码 2，按 --help 修正。
- **报告写盘失败**：原子写入 + finally 清理临时文件，失败时保留原始异常信息，不留下半截文件。
- **自测失败**：返回错误码 1，查看失败用例明细。

## 四、FAQ 与反模式

**Q1: 规则有哪些？置信度怎么来的？**
A: 内置 4 条：SEC001 硬编码密码（P0, 0.95）、LOG001 f-string 进日志（P1, 0.80）、PERF001 range(len)（P1, 0.75）、STD001 os.system/popen（P2, 0.85）。置信度为静态基础值（v2.0 移除拍脑袋的动态加减）。

**Q2: 检测到的密码会泄露吗？**
A: 不会。SEC001 命中后自动脱敏（只显示前 2 位+***），明文密码绝不写入报告（v2.0 安全修复）。

**Q3: 注释里的代码会误报吗？**
A: 不会。规则在 tokenize 剥离注释/字符串后的真实代码上匹配（v2.0 修复）。

**Q4: 遇到不认识的 diff 格式会怎样？**
A: 快速失败：非法 hunk 头/行号立即抛错并提示"格式不兼容"，绝不制造行号错乱的虚假报告（v2.0 修复——错误数据比崩溃更可怕）。

**反模式（不要这样做）**
- ❌ 把含明文密码的报告上传工单系统 → 已脱敏，但仍建议复查
- ❌ 期待语义级审查 → 规则引擎只做模式匹配
- ❌ 输入非 git diff 格式 → 会快速失败，请用 `git diff > change.diff` 导出

## 五、执行步骤（运行前检查）

1. `python run.py --selftest` → 12/12 全绿
2. `python run.py --diff change.diff` 预览
3. 需要过滤：加 `--filter P0` / `--filter P0,P1`
4. 落盘：`--output report.md --force`

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
