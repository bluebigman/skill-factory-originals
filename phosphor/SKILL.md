---
slug: phosphor
name: phosphor
displayName: 运行时追踪 事件采集 性能探针
description: 基于DTrace的Ruby运行时事件采集与结构化输出工具
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: RuntimeForge
agent_created: true
trigger_words: ["phosphor", "dtrace", "ruby事件", "运行时追踪", "性能探针", "--selftest", "--version", "ruby诊断", "事件采集"]
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# phosphor — Ruby 运行时事件采集与结构化输出

## 一、能力边界（一页纸速查卡）

### 能做

| 能力项 | 说明 | 示例 |
|--------|------|------|
| 事件采集 | 通过 DTrace 探针捕获 Ruby 运行时事件（方法调用、GC、线程切换等） | `phosphor dtrace -e 'ruby$target:::*'` |
| 结构化输出 | 将原始 DTrace 输出转换为 JSON/NDJSON 格式，便于下游处理 | 输出 `{"event":"method-call","timestamp":...,"data":{...}}` |
| 自检模式 | 验证工具自身安装与依赖是否正常 | `phosphor --selftest` |
| 版本查询 | 输出当前工具版本信息 | `phosphor --version` |
| 批量处理 | 对多个输入文件执行统一的事件解析与转换 | `phosphor dtrace -f trace1.txt -f trace2.txt` |

### 不能做（明确边界）

- **不能修改 Ruby 程序行为**：仅做观测，不做字节码注入或运行时修改。
- **不能捕获非 DTrace 支持的事件**：如纯用户态锁等待（无内核探针）不在范围内。
- **不能跨平台运行**：DTrace 依赖 macOS/BSD/Solaris 内核支持，Linux 需使用 `bpftrace` 替代方案（不在本工具范围内）。
- **不能自动修复性能问题**：只负责采集与呈现，不提供优化建议引擎。

### 适用对象

- Ruby 应用开发者（排查性能瓶颈）
- SRE/运维工程师（生产环境黑盒观测）
- 性能测试工程师（压测数据采集）

---

## 二、触发方式

### trigger_words 映射表

| 触发词/短语 | 实际场景 | 使用方式 |
|-------------|----------|----------|
| `phosphor` | 需要采集 Ruby 运行时事件 | 直接执行 CLI 命令 |
| `dtrace` | 需要底层内核级追踪 | 配合 `phosphor dtrace` 子命令 |
| `ruby事件` | 关注方法调用、GC、线程事件 | 使用默认事件集 |
| `性能探针` | 定位 CPU/内存热点 | 结合 `-e` 自定义探针表达式 |
| `--selftest` | 环境异常，需验证工具可用性 | 单独执行 |
| `--version` | 确认工具版本 | 单独执行 |
| `ruby诊断` | 线上问题排查 | 采集后分析输出 |

### 大白话场景映射

| 用户说 | 工具做 |
|--------|--------|
| "我的 Rails 应用响应变慢了" | 采集方法调用事件，输出各方法耗时分布 |
| "GC 频率异常高" | 捕获 GC 相关探针，输出 GC 触发次数与耗时 |
| "生产环境不能加代码，怎么观测？" | 使用 DTrace 无侵入采集，不改动应用代码 |
| "采集结果看不懂" | 使用结构化输出 + 字段说明文档 |

---

## 三、标准流程

### 前置条件

| 条件 | 检查方法 | 不满足时的处理 |
|------|----------|----------------|
| 操作系统支持 DTrace | `dtrace --version` | 使用替代工具，或换用支持平台 |
| Ruby 编译时启用 DTrace 支持 | `ruby -r rbconfig -e 'print RbConfig::CONFIG["enable_dtrace"]'` | 重新编译 Ruby，或使用预编译 DTrace 版本 |
| 当前用户有 DTrace 权限 | `sudo dtrace -l` | 使用 sudo 或配置特权 |
| 磁盘空间 ≥ 100MB | `df -h` | 清理空间，或使用流式输出 |

### 执行步骤（分步编号）

#### 步骤 1：准备输入

将待处理的 DTrace 原始输出文件放入同一目录，确认命名规范一致（如 `trace_*.txt`）。

```bash
mkdir -p ~/traces
cp /var/log/ruby_trace_*.txt ~/traces/
ls ~/traces/
```

#### 步骤 2：试运行（单样本验证）

先用单个样本执行，核对输出字段与格式是否符合预期。

```bash
phosphor dtrace -f ~/traces/trace_sample.txt --output json
```

**预期输出示例（JSON）**：

```json
{
  "events": [
    {
      "timestamp": 1712345678.123456,
      "event_type": "method-call",
      "method": "User#find",
      "duration_us": 125.3,
      "thread_id": 140736182345984,
      "file": "app/models/user.rb",
      "line": 42
    }
  ],
  "summary": {
    "total_events": 1,
    "total_duration_us": 125.3,
    "start_time": 1712345678.123456,
    "end_time": 1712345678.123456
  }
}
```

**核对要点**：
- 时间戳格式是否为 Unix 秒（浮点）
- 事件类型枚举是否完整（method-call, gc-start, gc-end, thread-switch, exception）
- 字段名是否与文档一致

#### 步骤 3：批量执行

确认无误后对全量数据执行，并保留原始文件备份。

```bash
# 备份原始文件
cp -r ~/traces ~/traces_backup_$(date +%Y%m%d_%H%M%S)

# 批量处理
phosphor dtrace -f ~/traces/trace_*.txt --output ndjson --output-dir ~/traces/processed/
```

**参数说明**：

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `-f, --file` | 字符串（可重复） | 无 | 输入文件路径，支持通配符 |
| `--output` | 枚举：json/ndjson/table | json | 输出格式 |
| `--output-dir` | 字符串 | 当前目录 | 输出目录 |
| `-e, --expression` | 字符串 | 默认事件集 | DTrace 探针表达式 |
| `--verbose` | 布尔 | false | 输出详细日志 |

#### 步骤 4：校验结果

抽查输出条目，核对关键字段与源数据一致。

```bash
# 抽查第 10 条事件
head -n 10 ~/traces/processed/trace_1.ndjson | tail -n 1

# 与原始文件对比
grep -c "method-call" ~/traces/trace_1.txt
grep -c "method-call" ~/traces/processed/trace_1.ndjson
```

**校验规则**：
- 事件计数一致（误差 ≤ 0.1%）
- 时间戳单调递增（无回退）
- 关键字段（method, thread_id）无空值

### 输出规范

| 格式 | 适用场景 | 示例 |
|------|----------|------|
| JSON | 单次分析，需完整结构 | 见步骤 2 示例 |
| NDJSON | 流式处理，每行一个事件 | `{"event_type":"gc-start","timestamp":...}` |
| Table | 终端快速查看 | `时间戳 | 事件类型 | 方法 | 耗时(us)` |

---

## 四、置信度门控

当输入信息不足或存在歧义时，**不得编造数据**。使用以下占位符：

| 场景 | 占位符 | 示例 |
|------|--------|------|
| 事件类型无法识别 | `[需核实:event_type]` | `{"event_type":"[需核实:event_type]"}` |
| 方法名缺失 | `[需核实:method]` | `{"method":"[需核实:method]"}` |
| 时间戳格式异常 | `[需核实:timestamp]` | `{"timestamp":"[需核实:timestamp]"}` |
| 文件路径无法解析 | `[需核实:file_path]` | `{"file":"[需核实:file_path]"}` |

**门控规则**：
1. 若某字段解析失败，输出占位符并附带 `"warning": "解析失败原因"`。
2. 若单文件错误率 > 5%，终止处理并提示用户检查源文件。
3. 若 DTrace 探针表达式语法错误，直接报错，不输出部分结果。

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| `E001` | 输入文件不存在 | `文件 xxx 不存在，请检查路径` | 1. 确认路径正确；2. 使用绝对路径 |
| `E002` | DTrace 权限不足 | `当前用户无 DTrace 权限，请使用 sudo` | 1. 使用 `sudo phosphor ...`；2. 配置 sudoers |
| `E003` | Ruby 未启用 DTrace | `当前 Ruby 未编译 DTrace 支持` | 1. 重新编译 Ruby（`--enable-dtrace`）；2. 使用预编译版本 |
| `E004` | 探针表达式语法错误 | `DTrace 探针表达式解析失败: xxx` | 1. 检查 `-e` 参数语法；2. 参考 `dtrace -h` 文档 |
| `E005` | 输出目录不可写 | `无法写入目录 xxx，请检查权限` | 1. 修改目录权限；2. 指定其他输出目录 |
| `E006` | 批量处理错误率超限 | `错误率超过 5%，已终止处理` | 1. 检查源文件格式；2. 分批处理定位问题文件 |
| `E007` | 版本不兼容 | `输入文件版本与当前工具不兼容` | 1. 升级工具；2. 使用兼容版本处理 |

---

## 六、FAQ 反模式

### 常见坑 1：忽略 DTrace 权限

**错误做法**：直接运行 `phosphor dtrace` 报权限错误后放弃。

**正确做法**：
```bash
sudo phosphor dtrace -f trace.txt
```

### 常见坑 2：批量处理前未试运行

**错误做法**：直接对 100 个文件批量执行，结果格式全错。

**正确做法**：先处理 1 个文件，确认输出格式后再批量。

### 常见坑 3：忽略时间戳精度

**错误做法**：使用整数时间戳，导致事件顺序错乱。

**正确做法**：使用浮点时间戳（秒.微秒），确保精度。

### 常见坑 4：不保留原始文件

**错误做法**：处理完直接删除原始文件，后续无法回溯。

**正确做法**：处理前备份，处理中保留原始文件。

### 反模式对照表

| 反模式 | 问题 | 推荐替代 |
|--------|------|----------|
| 依赖 `grep` 手工解析 DTrace 输出 | 易错、不可重复 | 使用 `--output json` 结构化输出 |
| 在 Linux 上强行使用 DTrace | 不支持 | 使用 `bpftrace` 或 `perf` |
| 采集所有事件不加过滤 | 数据量爆炸 | 使用 `-e` 指定探针表达式 |
| 忽略 `--selftest` 直接使用 | 环境问题导致误判 | 先运行 `--selftest` 验证 |

---

## 七、渐进式披露

### 速查卡（新手路径）

1. 运行 `phosphor --selftest` 确认环境。
2. 采集单个文件：`phosphor dtrace -f trace.txt --output table`。
3. 查看表格输出，理解基本事件类型。
4. 使用 `--output json` 获取结构化数据。

### 进阶路径（有经验用户）

1. 自定义探针表达式：`phosphor dtrace -e 'ruby$target::method-call { printf(...) }'`。
2. 批量处理 + NDJSON 输出，接入下游分析管道。
3. 使用 `--verbose` 调试探针表达式。
4. 结合 `summary` 字段进行性能热点分析。

### 专家路径（深度定制）

1. 编写自定义 DTrace 脚本，通过 `-e` 传入。
2. 使用 `--output-dir` 组织多批次输出。
3. 结合外部工具（jq, pandas）进行复杂分析。

---

## 八、用户协议

<!-- user-agreement-injected -->

**使用 phosphor Skill 即表示您同意以下条款：**

1. **责任承担**：使用者自行承担全部责任。本工具仅提供事件采集与输出功能，不构成对任何软件性能、安全性或稳定性的保证。因使用本工具导致的任何直接或间接损失，作者不承担任何责任。

2. **禁止反向工程**：不得对本 Skill 文档中描述的算法、流程进行反向工程、反编译或试图提取底层实现（除非适用法律允许）。

3. **合规使用**：使用者需确保采集行为符合所在司法辖区的法律法规，包括但不限于数据隐私保护、监控合规等。

4. **无担保**：本工具按"原样"提供，不附带任何明示或暗示的担保，包括但不限于适销性、特定用途适用性。

5. **修改与分发**：允许修改和分发，但需保留原始版权声明，并注明修改内容。

---

## 九、许可证（License）

<!-- professional-license-embedded -->

**MIT License**

Copyright (c) 2024 RuntimeForge

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
