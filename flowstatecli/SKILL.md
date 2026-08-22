---
slug: flowstatecli
name: flowstatecli
displayName: 开发者工作流 会话追踪 专注计时
description: 面向开发者的命令行效率工具，用于追踪工作会话、管理任务与设定目标。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: LingFlow Studio
agent_created: true
trigger_words: ["flowstatecli", "工作会话追踪", "开发者效率工具", "任务管理", "专注计时", "会话记录", "目标设定"]
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# flowstatecli 技能手册

## 一、能力边界（一页纸速查卡）

### 1.1 工具定位

flowstatecli 是一个运行在终端环境下的开发者效率工具，核心职责是：

- 记录工作会话的开始与结束时间
- 管理任务清单（增、删、改、查）
- 设定短期目标并跟踪截止日期
- 提供专注计时功能辅助番茄工作法实践

### 1.2 能做与不能做

| 能力维度 | 支持 | 不支持 |
|---------|------|--------|
| 会话记录 | 开始/结束时间戳、备注 | 自动识别正在进行的应用 |
| 任务管理 | 任务 ID 关联、状态变更 | 依赖外部项目管理工具同步 |
| 目标设定 | 截止日期、进度标记 | 自动提醒（需配合 cron） |
| 数据导出 | JSON/CSV 格式导出 | 云端同步、多人协作 |
| 计时器 | 专注/休息倒计时 | 白噪音、应用锁 |

### 1.3 适用对象

- 日常使用命令行进行开发的程序员
- 需要量化每日工作投入的自由职业者
- 希望培养专注习惯的学习者

---

## 二、触发方式

### 2.1 触发词

当对话中出现以下关键词时，本技能被激活：

- `flowstatecli`
- 工作会话追踪
- 开发者效率工具
- 任务管理
- 专注计时
- 会话记录
- 目标设定

### 2.2 场景映射表

| 用户说（大白话） | 实际意图 | 对应操作 |
|-----------------|---------|---------|
| "帮我记一下刚才改 bug 花了多久" | 记录工作会话 | `flowstatecli session start/end` |
| "我手头有三个任务要排优先级" | 创建任务列表 | `flowstatecli task add` |
| "这周想完成模块重构" | 设定目标 | `flowstatecli goal set` |
| "今天干了啥，给我看看" | 查看当日记录 | `flowstatecli report --today` |
| "我要专注 25 分钟" | 启动专注计时 | `flowstatecli focus --duration 25` |

---

## 三、标准流程

### 3.1 前置条件

1. 已安装 flowstatecli（验证方式：运行 `flowstatecli --version`）
2. 已通过自检（运行 `flowstatecli --selftest`，输出 `OK` 表示安装正常）
3. 配置文件存在于 `~/.flowstatecli/config.yaml`（首次运行自动生成）

### 3.2 执行步骤

#### 步骤 1：初始化环境

```bash
flowstatecli --selftest
```

预期输出：

```
[PASS] 配置目录可写
[PASS] 数据库连接正常
[PASS] 版本兼容性检查通过
```

#### 步骤 2：创建任务

```bash
flowstatecli task add --title "重构认证模块" --priority high
```

输出示例：

```
任务已创建: #T-1024
标题: 重构认证模块
优先级: high
创建时间: 2025-01-15 09:30:00
```

#### 步骤 3：记录工作会话

```bash
flowstatecli session start --task T-1024 --note "分析现有代码结构"
flowstatecli session end --task T-1024 --note "完成接口设计"
```

#### 步骤 4：设定目标

```bash
flowstatecli goal set --title "完成认证模块重构" --deadline 2025-01-31
```

#### 步骤 5：查看当日报告

```bash
flowstatecli report --today
```

#### 步骤 6：导出数据（可选）

```bash
flowstatecli export --format json --output ~/flowstate_backup.json
```

### 3.3 输出规范

- 所有命令输出遵循 `[状态] 描述` 格式
- 时间戳统一使用 `YYYY-MM-DD HH:MM:SS` 格式
- 任务 ID 统一使用 `T-` 前缀加 4 位数字
- 目标 ID 统一使用 `G-` 前缀加 4 位数字

---

## 四、置信度门控

当输入数据无法通过验证时，flowstatecli 不会猜测或编造，而是输出占位符提示。

### 4.1 时间戳有效性

**规则**：结束时间必须晚于开始时间。

```bash
# 错误示例
flowstatecli session start --time 14:00
flowstatecli session end --time 13:30
```

**输出**：

```
[需核实:时间戳] 结束时间早于开始时间，请检查输入
```

### 4.2 任务关联性

**规则**：任务 ID 必须存在于任务表中。

```bash
# 错误示例
flowstatecli session start --task T-9999
```

**输出**：

```
[需核实:任务ID] 任务 T-9999 不存在，请先创建任务
```

### 4.3 目标截止日期

**规则**：截止日期必须为未来日期。

```bash
# 错误示例
flowstatecli goal set --deadline 2024-01-01
```

**输出**：

```
[需核实:截止日期] 截止日期已过期，请设定未来日期
```

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|---------|---------|
| E001 | 配置目录不可写 | `配置目录权限不足` | 检查 `~/.flowstatecli` 目录权限，执行 `chmod 700 ~/.flowstatecli` |
| E002 | 数据库损坏 | `数据文件损坏，尝试恢复` | 运行 `flowstatecli repair` 或从备份恢复 |
| E003 | 任务不存在 | `[需核实:任务ID]` | 运行 `flowstatecli task list` 查看有效任务 |
| E004 | 会话未关闭 | `存在未结束的会话` | 运行 `flowstatecli session end` 关闭当前会话 |
| E005 | 参数格式错误 | `参数解析失败` | 运行 `flowstatecli --help` 查看正确语法 |
| E006 | 导出失败 | `导出路径不可写` | 检查输出目录权限或更换路径 |

---

## 六、FAQ 反模式

### 6.1 常见坑与正确做法

| 反模式 | 问题描述 | 正确做法 |
|--------|---------|---------|
| 忘记结束会话 | 会话一直处于进行中状态，统计失真 | 设置自动超时（配置文件 `auto_timeout: 30` 分钟） |
| 任务 ID 硬编码 | 脚本中写死任务 ID，任务删除后脚本失效 | 先查询任务列表，动态获取 ID |
| 忽略时间戳校验 | 手动输入时间导致数据错乱 | 使用 `--time` 参数时先验证格式 `HH:MM` |
| 目标设定过于模糊 | 无法判断是否达成 | 目标标题使用动词开头，如"完成""实现""修复" |
| 频繁切换任务 | 会话碎片化，难以统计 | 一次会话只关联一个任务，使用备注记录上下文 |

### 6.2 反模式对照

**反模式 1：过度依赖自动导出**

```bash
# 错误：只在周五手动导出
flowstatecli export --format csv
```

**正确**：配置 cron 每周自动导出

```bash
0 18 * * 5 flowstatecli export --format json --output ~/backups/flowstate_$(date +\%Y\%m\%d).json
```

**反模式 2：忽略配置文件调优**

```bash
# 错误：使用默认配置从不调整
flowstatecli focus --duration 25
```

**正确**：根据个人习惯调整 `~/.flowstatecli/config.yaml`

```yaml
focus:
  default_duration: 45
  break_duration: 10
session:
  auto_timeout: 45
```

---

## 七、渐进式披露

### 7.1 速查卡（新手必读）

```bash
# 安装验证
flowstatecli --selftest

# 创建任务
flowstatecli task add --title "任务名" --priority high|medium|low

# 开始/结束会话
flowstatecli session start --task T-XXXX
flowstatecli session end --task T-XXXX

# 查看今日报告
flowstatecli report --today

# 设定目标
flowstatecli goal set --title "目标描述" --deadline YYYY-MM-DD
```

### 7.2 分层次阅读路径

**新手路径（第 1-2 周）**

1. 阅读「能力边界」了解工具能做什么
2. 运行 `--selftest` 确认环境
3. 练习「标准流程」步骤 1-3
4. 每天结束时运行 `report --today`

**进阶路径（第 3-4 周）**

1. 掌握「标准流程」全部 6 个步骤
2. 学习使用 `goal` 子命令跟踪目标
3. 配置 cron 自动导出
4. 阅读 `--help` 探索全部子命令

**高级路径（第 5 周起）**

1. 编写 shell 脚本批量处理会话数据
2. 使用 `export` 命令对接自定义分析工具
3. 调整 `config.yaml` 中的自动超时、默认时长
4. 参与项目贡献或提交 issue

---

## 八、用户协议

<!-- user-agreement-injected -->

**使用 flowstatecli 技能即表示您同意以下条款：**

1. **责任承担**：使用者自行承担因使用本技能产生的全部责任。包括但不限于数据丢失、任务延误、时间统计偏差等情形。
2. **禁止反向工程**：不得对本技能文档进行反向工程、反编译、破解或试图提取底层算法。
3. **数据备份**：使用者有义务定期备份 `~/.flowstatecli/` 目录下的数据文件。
4. **合规使用**：不得将本技能用于任何违反法律法规或道德伦理的场景。
5. **免责声明**：本技能按"原样"提供，不附带任何明示或暗示的担保。

---

## 九、许可证（License）

<!-- professional-license-embedded -->

### MIT License

Copyright (c) 2025 LingFlow Studio

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
