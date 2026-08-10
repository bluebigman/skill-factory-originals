---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: exception-logger
name: exception-logger
displayName: 异常日志 根因分析 修复指引
description: 捕获并解析Python异常日志，提供根因建议与修复指引。
version: 2.0.1
rules_version: cpr-20260810-n301
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/exception-logger
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 林栖
agent_created: true
trigger_words: ["exception-logger", "异常日志", "exception log", "log analyzer", "错误日志分析", "堆栈追踪", "traceback解析"]
---

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->


> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# exception-logger 技能文档

## 一、能力边界（速查卡）

### 1.1 能做什么

| 能力项 | 说明 | 示例 |
|--------|------|------|
| 异常捕获 | 从文件或直接文本中提取 Python 异常信息 | 读取 `app.log` 中的 Traceback |
| 结构化解析 | 将原始堆栈转换为字段化数据（异常类型、消息、文件位置、调用链） | `{"type": "ValueError", "message": "invalid literal for int()"}` |
| 根因分析 | 基于异常类型与调用链给出可能原因与修复建议 | 提示 `ValueError` 可能源于类型转换前未校验输入 |
| 流式处理 | 大文件按行读取，内存占用稳定 | 处理 2GB 日志文件不崩溃 |
| 批量分析 | 一次处理多个异常记录，输出汇总报告 | 统计各类异常出现频率 |
| 多格式输出 | 支持纯文本与 JSON 两种输出格式 | `--format json` 供下游程序消费 |
| 原子写入 | 结果文件写入时先写临时文件再重命名，避免半截文件 | 写入中断不会损坏已有结果 |

### 1.2 不能做什么

| 限制项 | 说明 |
|--------|------|
| 不修复代码 | 只提供建议，不自动修改你的源代码 |
| 不处理非 Python 异常 | 仅识别 Python 的 `Traceback (most recent call last)` 格式 |
| 不保证根因唯一 | 同一异常可能有多种诱因，建议仅供参考 |
| 不分析运行性能 | 不涉及 CPU、内存等运行时指标 |
| 不处理加密或压缩日志 | 输入必须是明文文本或可读文件 |

### 1.3 适用对象

- 后端开发工程师：快速定位线上服务报错
- 运维工程师：批量分析日志文件中的异常分布
- 数据分析师：处理脚本运行中的异常输出
- 教学场景：向初学者展示异常结构与常见错误模式

---

## 二、触发方式

### 2.1 触发词

以下任一词汇均可激活本技能：

- `exception-logger`
- `异常日志`
- `exception log`
- `log analyzer`
- `错误日志分析`
- `堆栈追踪`
- `traceback解析`

### 2.2 场景映射表

| 用户说（大白话） | 技能执行动作 |
|------------------|--------------|
| "帮我看看这个日志文件里有什么错误" | 读取文件 → 解析所有异常 → 输出汇总 |
| "这个报错是什么意思？" | 解析单条异常 → 给出类型、消息、位置与建议 |
| "把错误信息整理成 JSON 给我" | 解析 → 以 JSON 格式输出 |
| "这个日志文件太大，能处理吗？" | 启用流式模式，逐块读取并解析 |
| "统计一下最近一周的报错类型分布" | 批量分析 → 输出频率统计 |

---

## 三、标准流程

### 3.1 前置条件

| 条件 | 要求 |
|------|------|
| 输入来源 | 文件路径（`--input`）或直接文本（`--input` 传 `-` 时从 stdin 读取） |
| 文件编码 | UTF-8（其他编码需预先转换） |
| 运行环境 | Python 3.8+（本技能为 CLI 工具，非 Python 库） |
| 依赖 | 无第三方依赖，仅标准库 |

### 3.2 执行步骤

```bash
# 步骤 1：查看版本与自检
exception-logger --version
exception-logger --selftest

# 步骤 2：基本用法（从文件读取，输出文本）
exception-logger --input /path/to/app.log

# 步骤 3：从标准输入读取
cat app.log | exception-logger --input -

# 步骤 4：输出 JSON 格式
exception-logger --input app.log --format json

# 步骤 5：写入结果文件（原子写入）
exception-logger --input app.log --output result.json --format json

# 步骤 6：预览模式（不写文件）
exception-logger --input app.log --output result.txt --dry-run

# 步骤 7：详细模式（打印决策过程）
exception-logger --input app.log --verbose
```

### 3.3 参数说明

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `--input` | string | 必填 | 输入文件路径，或 `-` 表示 stdin |
| `--format` | string | `text` | 输出格式：`text` 或 `json` |
| `--output` | string | 无 | 输出文件路径；不指定则打印到 stdout |
| `--dry-run` | bool | `false` | 仅预览，不实际写入文件 |
| `--verbose` | bool | `false` | 打印详细解析过程 |
| `--selftest` | bool | `false` | 运行内置自检 |
| `--version` | bool | `false` | 打印版本号 |

### 3.4 输出规范

#### 文本格式（`--format text`）

```
[异常 #1]
类型: ValueError
消息: invalid literal for int() with base 10: 'abc'
位置: /app/main.py:42 in parse_number
调用链:
  /app/main.py:10 in main
  /app/main.py:42 in parse_number
建议: 在调用 int() 前检查输入是否为数字字符串，可使用 str.isdigit() 或 try-except 包裹。
```

#### JSON 格式（`--format json`）

```json
{
  "exceptions": [
    {
      "index": 1,
      "type": "ValueError",
      "message": "invalid literal for int() with base 10: 'abc'",
      "file": "/app/main.py",
      "line": 42,
      "function": "parse_number",
      "traceback": [
        {"file": "/app/main.py", "line": 10, "function": "main"},
        {"file": "/app/main.py", "line": 42, "function": "parse_number"}
      ],
      "suggestion": "在调用 int() 前检查输入是否为数字字符串，可使用 str.isdigit() 或 try-except 包裹。"
    }
  ],
  "summary": {
    "total": 1,
    "by_type": {"ValueError": 1}
  }
}
```

---

## 四、置信度门控

当输入信息不足以给出确定结论时，使用以下占位符，不编造内容：

| 场景 | 输出占位符 |
|------|-----------|
| 异常消息为空 | `[需核实:异常消息为空，请检查原始日志]` |
| 无法定位到具体文件行号 | `[需核实:无法从堆栈中提取文件位置]` |
| 异常类型不在已知映射表中 | `[需核实:未知异常类型，建议查阅官方文档]` |
| 根因建议置信度低于 60% | `[需核实:此建议基于常见模式，可能不适用于当前场景]` |

**示例**：

```
类型: UnknownError
消息: (空)
位置: [需核实:无法从堆栈中提取文件位置]
建议: [需核实:未知异常类型，建议查阅官方文档]
```

---

## 五、错误码体系

| 错误码 | 触发条件 | 提示话术 | 修正步骤 |
|--------|----------|----------|----------|
| `EL-001` | 输入文件不存在 | `错误: 文件 /path/to/file 不存在` | 检查路径是否正确，使用 `ls` 确认文件存在 |
| `EL-002` | 输入文件无读取权限 | `错误: 无法读取文件，权限不足` | 使用 `chmod +r` 添加读权限，或更换用户 |
| `EL-003` | 输入为空 | `错误: 输入内容为空，未发现任何异常` | 确认日志文件是否为空，或检查管道命令是否正确 |
| `EL-004` | 未找到异常模式 | `错误: 未在输入中检测到 Python Traceback 格式` | 确认输入是否为 Python 异常日志，检查是否包含 "Traceback (most recent call last)" |
| `EL-005` | 输出目录不存在 | `错误: 输出目录 /path/to/dir 不存在` | 使用 `mkdir -p` 创建目录 |
| `EL-006` | 输出文件已存在且未指定覆盖 | `错误: 输出文件已存在，使用 --force 覆盖` | 添加 `--force` 参数，或更换输出路径 |
| `EL-007` | 编码错误 | `错误: 文件编码不是 UTF-8，请先转换` | 使用 `iconv -f GBK -t UTF-8 input.log > output.log` 转换 |

---

## 六、FAQ 反模式

### 6.1 常见坑

| 坑 | 反模式（错误做法） | 正模式（正确做法） |
|----|-------------------|-------------------|
| 大文件一次性读入 | `content = open(file).read()` 导致内存溢出 | 使用流式逐行读取，本技能已内置 |
| 忽略异常类型 | 只关注消息文本，不区分 `ValueError` 与 `TypeError` | 先看类型，再读消息，最后看调用链 |
| 盲目信任建议 | 直接按建议修改代码，不验证上下文 | 将建议作为参考，结合业务逻辑判断 |
| 混合多种日志格式 | 将非 Python 日志（如 Nginx access log）一并输入 | 先过滤出 Python Traceback 段再分析 |
| 输出覆盖丢失 | 直接重定向覆盖已有结果文件 | 使用 `--output` 配合 `--dry-run` 预览，或备份原文件 |

### 6.2 反模式对照表

| 反模式 | 问题 | 替代方案 |
|--------|------|----------|
| 用正则硬匹配所有行 | 堆栈跨行，单行正则无法完整捕获 | 使用状态机：检测到 `Traceback` 开始收集，直到下一个 `Traceback` 或文件结束 |
| 忽略异常链（`During handling...`） | 丢失根本原因（`__context__`） | 解析 `During handling of the above exception` 后的嵌套 Traceback |
| 只输出前 N 行 | 大文件分析不完整 | 流式处理全部内容，汇总统计 |

---

## 七、渐进式披露

### 7.1 速查卡（30 秒上手）

```bash
# 最常用命令
exception-logger --input app.log
exception-logger --input app.log --format json
exception-logger --input app.log --output result.txt
```

### 7.2 新手路径（5 分钟）

1. 准备一个包含 Python 异常的日志文件
2. 运行 `exception-logger --input your.log`
3. 查看输出的异常类型、位置与建议
4. 如需 JSON 格式，加 `--format json`
5. 如需保存结果，加 `--output result.txt`

### 7.3 进阶路径（深入使用）

1. **批量分析**：将多个日志文件合并后输入，或循环调用
2. **自定义建议规则**：修改内置的异常类型→建议映射表（位于 `suggestions.py`）
3. **集成到 CI**：在 CI 脚本中调用，失败时输出 JSON 供后续处理
4. **流式处理验证**：使用 `--verbose` 观察逐块处理过程，确认内存占用稳定

---

## 八、实现参考（核心函数）

```python
# parse_exception.py 核心逻辑（示意）
def parse_exception(text_block: str) -> dict:
    """解析单个异常块，返回结构化字段。"""
    result = {
        "type": None,
        "message": None,
        "file": None,
        "line": None,
        "function": None,
        "traceback": [],
        "suggestion": None
    }
    lines = text_block.strip().splitlines()
    for i, line in enumerate(lines):
        if line.startswith("Traceback (most recent call last)"):
            continue
        if "Error" in line and ":" in line:
            # 最后一行通常是 "ExceptionType: message"
            parts = line.split(":", 1)
            result["type"] = parts[0].strip()
            result["message"] = parts[1].strip() if len(parts) > 1 else ""
        elif 'File "' in line:
            # 堆栈帧行: File "/path/file.py", line 42, in func
            import re
            m = re.search(r'File "(.+?)", line (\d+), in (.+)', line)
            if m:
                frame = {
                    "file": m.group(1),
                    "line": int(m.group(2)),
                    "function": m.group(3)
                }
                result["traceback"].append(frame)
                if result["file"] is None:
                    result["file"] = frame["file"]
                    result["line"] = frame["line"]
                    result["function"] = frame["function"]
    result["suggestion"] = get_suggestion(result["type"])
    return result
```

---

## 九、用户协议

<!-- user-agreement-injected -->

**使用本 Skill 即表示您同意以下条款：**

1. **责任承担**：使用者自行承担因使用本 Skill 产生的全部责任。本 Skill 提供的分析结果与建议仅供参考，不构成任何形式的保证或承诺。因依赖本 Skill 输出而导致的任何直接或间接损失，作者不承担任何责任。

2. **禁止反向工程**：不得对本 Skill 进行反向工程、反编译、破解或试图提取底层算法（法律允许的除外）。

3. **合法使用**：使用者应确保输入数据来源合法，不得使用本 Skill 处理违反法律法规或侵犯他人权益的数据。

4. **无担保**：本 Skill 按"现状"提供，不附带任何明示或暗示的担保，包括但不限于适销性、特定用途适用性和非侵权性。

5. **协议更新**：作者保留随时修改本协议的权利，修改后的协议将在本 Skill 文档中公布并即时生效。

---

## 十、许可证（License）

<!-- professional-license-embedded -->

**MIT License**

Copyright (c) 2026 林栖

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
