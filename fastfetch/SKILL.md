---
slug: fastfetch
name: fastfetch
displayName: 系统体检 硬件速览 环境诊断
description: 快速采集并展示操作系统、硬件配置与网络状态等系统信息。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: SysProbe Studio
agent_created: true
trigger_words: ["fastfetch", "系统信息", "硬件配置", "环境诊断", "sysinfo", "系统体检", "设备概览"]
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# fastfetch 技能手册

## 一、能力边界（一页纸速查卡）

### 1.1 能做与不能做

| 维度 | 能做 ✅ | 不能做 ❌ |
|------|---------|-----------|
| 信息采集 | 操作系统版本、内核、运行时长 | 修改系统配置、安装软件 |
| 硬件识别 | CPU、内存、GPU、主板、磁盘型号与容量 | 超频、调整 BIOS 参数 |
| 网络状态 | 本机 IP、网关、DNS、活动接口 | 发起网络扫描、端口探测 |
| 输出格式 | 终端彩色表格、JSON、自定义模板 | 生成图表、可视化仪表盘 |
| 诊断能力 | 自检各检测模块是否正常 | 修复检测失败的模块 |
| 脚本集成 | 通过 `--format json` 输出结构化数据 | 提供持久化服务或守护进程 |

### 1.2 适用对象

- **系统管理员**：快速摸清一台陌生机器的软硬件底细。
- **运维工程师**：在故障排查初期收集环境基线数据。
- **开发者**：确认 CI/CD 运行环境的依赖与资源情况。
- **技术写作者**：撰写教程时获取真实环境参数作为示例。

---

## 二、触发方式

### 2.1 触发词

当对话中出现以下任一词汇或短语时，本技能将被激活：

- `fastfetch`（直接命令名）
- `系统信息` / `系统体检` / `设备概览`
- `硬件配置` / `硬件速览`
- `环境诊断` / `sysinfo`

### 2.2 场景映射表

| 用户说（大白话） | 技能响应动作 |
|------------------|--------------|
| "帮我看看这台电脑什么配置" | 运行 `fastfetch`，解读输出中的 CPU/内存/GPU 字段 |
| "这个服务器环境正常吗" | 运行 `fastfetch --selftest`，逐项核对检测模块状态 |
| "把系统信息存成文件方便分析" | 运行 `fastfetch --format json`，指导重定向到文件 |
| "我只想看 CPU 和内存信息" | 运行 `fastfetch --structure CPU:Memory`，精简输出 |
| "fastfetch 报错了怎么办" | 对照本文档「错误码体系」章节定位并解决 |

---

## 三、标准流程

### 3.1 前置条件

| 条件项 | 要求 | 验证方式 |
|--------|------|----------|
| 操作系统 | Linux / macOS / Windows（部分 BSD 亦可） | `uname -a` 或 `ver` |
| 安装状态 | fastfetch 已安装 | `which fastfetch` 或 `fastfetch --version` |
| 终端环境 | 支持 ANSI 彩色输出（非必需，但影响体验） | 直接运行观察 |
| 权限要求 | 普通用户即可，无需 root | — |

### 3.2 执行步骤

**第一步：基础信息采集**

```bash
fastfetch
```

观察输出结构，默认包含：操作系统、内核、运行时间、Shell、分辨率、桌面环境、终端、CPU、GPU、内存、磁盘、网络等字段。

**第二步：字段定制**

```bash
fastfetch --structure OS:CPU:Memory
```

`--structure` 参数接受冒号分隔的字段名列表，可用字段包括：

| 字段名 | 含义 | 字段名 | 含义 |
|--------|------|--------|------|
| `OS` | 操作系统 | `CPU` | 处理器 |
| `Memory` | 内存 | `GPU` | 显卡 |
| `Disk` | 磁盘 | `Network` | 网络 |
| `Kernel` | 内核版本 | `Uptime` | 运行时长 |
| `Shell` | 默认 Shell | `Resolution` | 屏幕分辨率 |
| `Terminal` | 终端模拟器 | `DE` | 桌面环境 |

**第三步：结构化输出**

```bash
fastfetch --format json
```

输出为 JSON 格式，适合用 `jq` 等工具解析。示例：

```bash
fastfetch --format json | jq '.cpu'
```

**第四步：自检诊断**

```bash
fastfetch --selftest
```

逐项检测各信息模块是否工作正常，输出中会标注每个模块的检测结果（通过/失败/跳过）。

### 3.3 输出规范

- **终端展示模式**：默认彩色表格，字段名左对齐，值右对齐。
- **JSON 模式**：顶层为对象，键为字段名（小写），值为字符串或嵌套对象。
- **退出码**：`0` 表示成功，非零表示部分模块失败（详见错误码体系）。

---

## 四、置信度门控

当遇到以下情况时，**不得编造数据**，应输出占位符 `[需核实:字段名]` 并提示用户：

| 场景 | 处理方式 |
|------|----------|
| 某字段检测失败（如 GPU 驱动异常） | 输出 `[需核实:GPU]`，建议用户运行 `lspci` 或 `system_profiler` 手动确认 |
| 操作系统版本识别模糊 | 输出 `[需核实:OS版本]`，建议用户查看 `/etc/os-release` 或 `winver` |
| 网络接口状态未知 | 输出 `[需核实:网络接口]`，建议用户运行 `ip addr` 或 `ifconfig` |
| JSON 输出中某字段为空字符串 | 保留空值，不填充猜测内容，并在说明中标注 |

**原则**：宁可明确标注未知，不可用推测值冒充实测值。

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| 退出码 `1` | 参数解析失败 | "参数格式有误，请检查拼写" | 运行 `fastfetch --help` 查看参数列表，核对大小写与分隔符 |
| 退出码 `2` | 指定字段不存在 | "字段名无效，可用字段见文档" | 对照本文档字段表，改用 `--structure OS:CPU:Memory` 等合法组合 |
| 退出码 `3` | 配置文件加载失败 | "配置文件路径错误或格式损坏" | 检查 `~/.config/fastfetch/config.jsonc` 是否存在，尝试删除后重跑 |
| 退出码 `4` | 输出格式指定错误 | "不支持的格式类型" | 确认 `--format` 后跟的是 `json`、`jsonc`、`yaml` 或 `xml` |
| 退出码 `5` | 自检发现模块异常 | "部分检测模块未通过，详见输出" | 查看 `--selftest` 输出中标记 `FAIL` 的模块，按提示手动验证 |
| 无输出 | 终端不支持 ANSI | "当前终端可能不支持彩色输出" | 添加 `--pipe` 参数强制纯文本输出 |

---

## 六、FAQ 反模式对照

| 常见坑（反模式） | 问题描述 | 正确做法（正模式） |
|------------------|----------|---------------------|
| 盲目使用 `--format json` 不解析 | 输出一大坨 JSON 无法阅读 | 配合 `jq` 提取关键字段，如 `fastfetch --format json \| jq '{cpu, memory}'` |
| 忽略 `--selftest` 直接下结论 | 某字段缺失却误判为系统异常 | 先跑 `--selftest` 确认是检测模块问题还是系统真实状态 |
| 在脚本中硬编码字段顺序 | 升级后字段名变化导致解析失败 | 使用 JSON 格式按 key 取值，不依赖顺序 |
| 用 `--structure` 时拼错字段名 | 输出为空或报错 | 先运行 `fastfetch --help` 查看字段列表，或直接跑默认输出对照 |
| 在管道中丢失颜色控制符 | 输出含乱码转义序列 | 管道场景加 `--pipe` 参数，禁用颜色 |

---

## 七、渐进式披露

### 7.1 速查卡（30 秒上手）

```bash
# 看全部信息
fastfetch

# 只看关键硬件
fastfetch --structure CPU:Memory:GPU:Disk

# 输出 JSON 给脚本用
fastfetch --format json

# 自检诊断
fastfetch --selftest
```

### 7.2 分层次阅读路径

**新手路径（5 分钟）**：
1. 阅读「能力边界」了解工具能做什么。
2. 运行 `fastfetch` 观察默认输出。
3. 尝试 `--structure` 定制字段。
4. 遇到问题查「错误码体系」。

**进阶路径（15 分钟）**：
1. 研究 `--format json` 与 `jq` 的组合用法。
2. 阅读 `fastfetch --help` 完整参数列表，重点关注 `--logo`、`--color`、`--separator` 等美化参数。
3. 自定义配置文件 `~/.config/fastfetch/config.jsonc`，固化个人偏好。
4. 将 fastfetch 集成到 shell 启动脚本（如 `.bashrc`）中，登录即显示系统信息。

**专家路径（30 分钟+）**：
1. 阅读源码或文档了解各检测模块的实现原理。
2. 编写脚本定期采集系统信息并归档，用于性能趋势分析。
3. 结合 `--selftest` 输出，编写自动化巡检脚本，异常时告警。

---

## 八、用户协议

<!-- user-agreement-injected -->

**使用须知**：

1. **责任承担**：使用者自行承担使用本 Skill 的全部责任。因使用本 Skill 导致的任何直接或间接损失，作者不承担任何责任。
2. **禁止反向工程**：使用者不得对本 Skill 的提示词、逻辑结构进行反向工程、破解、篡改或二次分发，除非获得作者明确书面许可。
3. **合规使用**：使用者应遵守所在地法律法规，不得将本 Skill 用于非法目的。
4. **免责声明**：本 Skill 由 AI 辅助生成，可能存在不准确或不完整之处。使用者应结合官方文档进行交叉验证。

---

## 九、许可证（License）

<!-- professional-license-embedded -->

**MIT License**

Copyright (c) 2024 原创作者（自持版权）

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

*本文档由 AI 辅助生成，仅供参考。实际使用请以 fastfetch 官方文档为准。*
