---
slug: exception-logger
name: exception-logger
displayName: 异常日志 根因定位 修复指引
description: 解析Python异常日志，定位根因并输出修复指引。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: LogPulse Studio
agent_created: true
trigger_words: ["exception-logger", "异常日志", "exception log", "log analyzer", "错误日志分析", "traceback解析", "堆栈追踪", "崩溃日志分析"]
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

> 本 Skill 由 AI 辅助生成，仅供参考。使用前请结合自身场景验证输出结果。

# exception-logger — Python 异常日志根因定位与修复指引

## 一、能力边界（一页纸速查卡）

### 1.1 工具能做什么

| 能力项 | 说明 |
|--------|------|
| 异常解析 | 从日志文件中提取 Python traceback，识别异常类型、错误消息、触发位置（文件、行号、函数名） |
| 根因定位 | 分析调用链，标记出首个引发异常的栈帧，区分「直接原因」与「深层原因」 |
| 修复建议 | 基于内置规则表（`suggestions.py`）输出针对性的代码修改建议 |
| 批量分析 | 支持一次传入多个日志文件，输出异常分布统计 |
| 格式输出 | 支持纯文本（默认）、JSON（`--format json`）、Markdown（`--format md`）三种输出格式 |
| 流式观察 | `--verbose` 模式下逐步打印解析过程，便于调试规则表 |

### 1.2 工具不能做什么

| 限制项 | 说明 |
|--------|------|
| 不执行代码 | 仅做静态文本分析，不会运行或调试你的 Python 程序 |
| 不修改源码 | 只输出建议文本，不自动改写任何 `.py` 文件 |
| 不识别自定义异常 | 除非你在 `suggestions.py` 中自行扩展映射表，否则仅覆盖 Python 内置异常类型 |
| 不处理非 traceback 文本 | 日志中若没有完整的 `Traceback (most recent call last):` 段落，则无法解析 |
| 不保证修复正确 | 建议基于规则匹配，最终修复效果需人工验证 |

### 1.3 适用对象

- 使用 Python 3.6+ 的开发者
- 维护遗留 Python 项目的运维/DevOps 人员
- 在 CI 流水线中集成日志分析的自动化工程师
- 需要快速定位线上异常的技术支持人员

---

## 二、触发方式

### 2.1 触发词

当对话中出现以下任一词汇时，本 Skill 自动激活：

- `exception-logger`
- `异常日志`
- `exception log`
- `log analyzer`
- `错误日志分析`
- `traceback解析`
- `堆栈追踪`
- `崩溃日志分析`

### 2.2 场景映射表

| 用户说（大白话） | 实际需求 | 工具动作 |
|------------------|----------|----------|
| "帮我看看这个报错是啥" | 解析一段异常日志 | 运行 `exception-logger -i 日志文件路径` |
| "这个 bug 到底哪行代码出的问题" | 定位根因位置 | 解析后高亮首个异常栈帧 |
| "怎么改才能不报错" | 获取修复建议 | 匹配 `suggestions.py` 规则表输出建议 |
| "帮我统计一下这周所有日志里的错误" | 批量分析 | 传入多个日志文件，输出分布统计 |
| "这个异常在 CI 里怎么自动检查" | 集成到流水线 | 使用 `--format json` 输出供脚本消费 |

---

## 三、标准流程

### 3.1 前置条件

| 条件 | 要求 |
|------|------|
| 日志文件 | 包含至少一个完整的 `Traceback (most recent call last):` 段落 |
| 文件编码 | UTF-8 或 ASCII（其他编码需先转换） |
| 文件大小 | 单文件不超过 10MB（超过请先拆分） |
| 运行环境 | Python 3.6+，无需安装第三方依赖 |

### 3.2 执行步骤

1. **准备日志文件**：确保日志中包含完整的 traceback 段落。最小可解析示例：

   ```
   Traceback (most recent call last):
     File "/app/main.py", line 42, in <module>
       result = divide(10, 0)
     File "/app/utils.py", line 18, in divide
       return a / b
   ZeroDivisionError: division by zero
   ```

2. **运行解析命令**：

   ```bash
   exception-logger -i /path/to/your.log
   ```

   常用参数表：

   | 参数 | 简写 | 说明 | 默认值 |
   |------|------|------|--------|
   | `--input` | `-i` | 输入日志文件路径（可多次传入） | 必填 |
   | `--format` | `-f` | 输出格式：`text` / `json` / `md` | `text` |
   | `--verbose` | `-v` | 打印流式处理过程 | 关闭 |
   | `--version` | 无 | 显示版本号 | 无 |
   | `--selftest` | 无 | 运行内置自检 | 无 |

3. **查看输出**：默认文本输出包含以下区块：

   ```
   [异常类型] ZeroDivisionError
   [错误消息] division by zero
   [触发位置] /app/utils.py:18 (函数: divide)
   [调用链]
      /app/main.py:42 <module>
      -> /app/utils.py:18 divide
   [根因分析] 除数为零，未做前置校验
   [修复建议] 在除法前检查除数是否为 0，或捕获 ZeroDivisionError 并给出友好提示
   ```

4. **根据建议修改代码**：人工审查建议，应用到实际代码中。

5. **验证修复**：重新运行程序，确认异常消失。

### 3.3 输出规范

- **文本格式**：按上述区块顺序输出，区块间空一行。
- **JSON 格式**：结构化输出，字段包括 `exception_type`、`message`、`location`、`stack_trace`、`root_cause`、`suggestion`、`confidence`。
- **Markdown 格式**：以表格和代码块呈现，便于嵌入文档。

---

## 四、置信度门控

当以下信息缺失时，工具不会猜测，而是输出 `[需核实:字段]` 占位符：

| 缺失信息 | 输出占位符 | 处理方式 |
|----------|------------|----------|
| 异常类型无法识别 | `[需核实:exception_type]` | 检查日志是否被截断 |
| 栈帧行号缺失 | `[需核实:line_number]` | 确认日志格式是否完整 |
| 规则表无匹配建议 | `[需核实:suggestion]` | 提示用户可扩展 `suggestions.py` |
| 根因分析置信度低于 60% | `[需核实:root_cause]` | 仅输出直接原因，不推断深层原因 |

**置信度分级**：

| 级别 | 置信度范围 | 输出策略 |
|------|------------|----------|
| 高 | 90%+ | 直接输出根因和建议 |
| 中 | 60%-89% | 输出根因，标注「可能原因」 |
| 低 | <60% | 仅输出异常类型和位置，根因字段置为 `[需核实:root_cause]` |

---

## 五、错误码体系

| 错误码 | 场景 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| `E001` | 输入文件不存在 | `错误: 文件 /path/xxx.log 不存在` | 检查路径是否正确，或使用绝对路径 |
| `E002` | 日志中无 traceback | `错误: 未找到 Traceback 段落，请确认日志包含完整异常堆栈` | 检查日志是否被截断，或确认程序确实抛出了异常 |
| `E003` | 文件编码不支持 | `错误: 文件编码非 UTF-8/ASCII，请先转换` | 使用 `iconv -f gbk -t utf-8` 转换编码 |
| `E004` | 文件超过 10MB | `错误: 文件过大，请拆分后重试` | 使用 `split -l 10000` 拆分日志 |
| `E005` | 规则表加载失败 | `错误: suggestions.py 语法错误，请检查` | 运行 `python -m py_compile suggestions.py` 验证语法 |
| `E006` | 未知异常类型 | `警告: 未识别的异常类型，已跳过建议生成` | 在 `suggestions.py` 中补充映射规则 |

---

## 六、FAQ 反模式

### 6.1 常见坑

| 坑 | 反模式示例 | 正确做法 |
|----|------------|----------|
| 日志截断 | 只复制了最后一行 `ZeroDivisionError`，没有完整 traceback | 确保复制从 `Traceback` 开始到异常类型结束的完整段落 |
| 多异常混淆 | 一个日志文件包含多个 traceback，只关注最后一个 | 工具默认分析所有 traceback，逐个输出，请逐一查看 |
| 忽略置信度 | 直接采用低置信度的根因建议 | 当输出包含 `[需核实:root_cause]` 时，需人工确认 |
| 规则表不更新 | 遇到新异常类型不扩展 `suggestions.py` | 每次遇到未识别异常，补充映射规则 |
| 依赖绝对路径 | 在 CI 中使用相对路径导致找不到文件 | 始终使用绝对路径或基于 `$CI_PROJECT_DIR` 的路径 |

### 6.2 反模式对照表

| 反模式 | 问题 | 替代方案 |
|--------|------|----------|
| 把工具当调试器 | 期望工具能复现并调试代码 | 工具只做静态分析，调试请用 pdb |
| 批量分析后不分类 | 大量输出淹没关键信息 | 使用 `--format json` 配合 jq 过滤 |
| 修改规则表后不测试 | 语法错误导致工具崩溃 | 修改后先运行 `--selftest` 验证 |

---

## 七、渐进式披露

### 7.1 速查卡（30 秒上手）

```bash
# 基本用法
exception-logger -i error.log

# 批量分析
exception-logger -i app1.log -i app2.log -i app3.log

# JSON 输出（供脚本消费）
exception-logger -i error.log --format json

# 自检
exception-logger --selftest
```

### 7.2 分层次阅读路径

**新手路径**（首次使用）：

1. 阅读「能力边界」了解工具范围
2. 准备一个包含 traceback 的日志文件
3. 运行 `exception-logger -i your.log`
4. 查看输出的异常类型、位置和建议
5. 根据建议修改代码

**进阶路径**（深度集成）：

1. 阅读「标准流程」了解全部参数
2. 在 CI 中集成 `--format json` 输出
3. 自定义 `suggestions.py` 扩展规则表
4. 使用 `--verbose` 观察流式处理过程
5. 批量分析多个日志文件，统计异常分布

**专家路径**（定制开发）：

1. 阅读「错误码体系」处理边界情况
2. 修改 `suggestions.py` 中的映射表
3. 扩展自定义异常类型支持
4. 集成到监控告警系统，自动触发分析

---

## 八、扩展指南：自定义 suggestions.py

`exception-logger` 的修复建议来自 `suggestions.py` 中的规则映射表。默认结构如下：

```python
# suggestions.py 示例
SUGGESTION_RULES = {
    "ZeroDivisionError": {
        "root_cause": "除数为零，未做前置校验",
        "suggestion": "在除法前检查除数是否为 0，或捕获 ZeroDivisionError 并给出友好提示",
        "confidence": 0.95
    },
    "FileNotFoundError": {
        "root_cause": "文件路径不存在或权限不足",
        "suggestion": "检查文件路径是否正确，确认程序有读取权限",
        "confidence": 0.90
    },
    # 添加自定义异常类型
    "MyCustomError": {
        "root_cause": "自定义业务逻辑错误",
        "suggestion": "根据业务文档检查相关条件",
        "confidence": 0.80
    }
}
```

扩展步骤：

1. 打开 `suggestions.py`
2. 在 `SUGGESTION_RULES` 字典中添加新条目
3. 运行 `exception-logger --selftest` 验证语法
4. 用包含该异常的日志文件测试

---

## 九、用户协议

<!-- user-agreement-injected -->

**使用 exception-logger Skill 即表示您同意以下条款：**

1. **责任承担**：使用者自行承担因使用本 Skill 产生的全部责任。包括但不限于：依据输出建议修改代码后产生的功能异常、数据丢失、业务中断等后果。
2. **禁止反向工程**：不得对本 Skill 的提示词、内部逻辑、规则表结构进行反向工程、反编译、提取或二次分发。
3. **无担保声明**：本 Skill 按「现状」提供，不附带任何明示或暗示的担保，包括但不限于适销性、特定用途适用性和非侵权保证。
4. **输出验证义务**：使用者有义务对工具输出的所有建议进行人工验证，不得直接应用于生产环境。
5. **合规使用**：使用者需确保使用场景符合当地法律法规及所在组织的安全规范。

---

## 十、许可证（License）

<!-- professional-license-embedded -->

**MIT License**

Copyright (c) 2024 LogPulse Studio

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
