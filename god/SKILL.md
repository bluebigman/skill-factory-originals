---
slug: god
name: god
displayName: 进程守护 Ruby监控 配置巡检
description: 生成God进程监控配置，巡检服务状态，排查守护异常。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 运维工坊
agent_created: true
trigger_words: ["god", "进程监控", "ruby进程", "进程守护", "服务巡检", "--selftest", "--version", "守护进程", "服务监控"]
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# God 进程监控配置与运维辅助 Skill

## 一、能力边界（速查卡）

### 1.1 本 Skill 能做什么

| 能力项 | 说明 | 示例 |
|--------|------|------|
| 配置生成 | 生成 `<服务名>.god` 监控配置文件 | `redis.god` |
| 状态巡检 | 检查 God 管理的进程健康状态 | `god status` 输出解析 |
| 故障排查 | 定位进程频繁重启、无法启动等问题的原因 | 日志分析、条件检查 |
| 配置验证 | 校验配置文件语法与逻辑正确性 | `god check` 使用指导 |
| 运维建议 | 提供内存、CPU、文件大小等监控条件的调优建议 | 阈值设置参考 |

### 1.2 本 Skill 不能做什么

| 限制项 | 说明 |
|--------|------|
| 不替代 God 本体 | 本 Skill 仅提供配置与运维指导，不包含 God 软件的安装与运行 |
| 不处理非 Ruby 进程 | God 主要面向 Ruby 生态，其他语言进程建议使用 systemd 或 supervisor |
| 不提供 Web 界面开发 | God 自带 Web 界面（`god -p 17165`），本 Skill 不涉及界面定制开发 |
| 不保证监控绝对可靠 | 任何监控工具都存在失效可能，需结合多层级监控策略 |

### 1.3 适用对象

- 使用 God 管理 Ruby 进程的开发者与运维人员
- 需要快速生成规范监控配置的团队
- 正在排查 God 监控异常的排障人员

---

## 二、触发方式与场景映射

### 2.1 触发词

当对话中出现以下关键词时，本 Skill 自动激活：

- `god`、`进程监控`、`ruby进程`、`进程守护`
- `服务巡检`、`守护进程`、`服务监控`
- `--selftest`、`--version`

### 2.2 场景映射表

| 用户说（大白话） | 实际需求 | 本 Skill 响应 |
|------------------|----------|---------------|
| "帮我写个 God 配置" | 生成监控配置文件 | 输出完整 `.god` 配置模板 |
| "我的进程老是被杀" | 排查进程异常退出原因 | 分析条件配置与日志 |
| "God 状态怎么看" | 了解进程运行状态 | 解释 `god status` 输出 |
| "配置完怎么生效" | 加载配置并启动监控 | 提供加载与验证步骤 |
| "内存占用太高了" | 设置内存监控阈值 | 给出内存条件配置建议 |

---

## 三、标准操作流程

### 3.1 前置条件

| 条件项 | 要求 |
|--------|------|
| God 已安装 | 运行 `god --version` 确认版本 |
| Ruby 环境正常 | `ruby -v` 可正常输出 |
| 目标服务可启动 | 服务本身能独立运行 |
| 目录权限就绪 | `~/.god/` 目录存在且可写 |

### 3.2 执行步骤

#### 步骤一：创建配置文件

1. 在 `~/.god/` 目录下创建 `<服务名>.god` 文件
2. 文件名使用小写字母与下划线，如 `my_service.god`
3. 设置文件权限：`chmod 644 ~/.god/my_service.god`
4. 确保 PID 文件目录权限为 `755`

#### 步骤二：编写基础配置

```ruby
# 监控目的：确保 my_service 进程持续运行
God.watch do |w|
  w.name = "my_service"
  w.dir = "/path/to/app"
  w.start = "bundle exec ruby app.rb"
  w.stop = "kill -INT %{pid}"
  w.restart = "kill -TERM %{pid}"
  w.pid_file = "/var/run/my_service.pid"
  w.log = "/var/log/my_service.log"

  # 监控目的：进程退出后自动重启
  w.start_if do |start|
    start.condition(:process_running) do |c|
      c.interval = 10.seconds
      c.running = false
    end
  end

  # 监控目的：内存占用超过阈值时重启
  w.restart_if do |restart|
    restart.condition(:memory_usage) do |c|
      c.above = 300.megabytes
      c.times = [3, 5] # 3 次采样中 5 秒内连续触发
    end
  end
end
```

#### 步骤三：验证配置

```bash
god check ~/.god/my_service.god
```

- 输出 `OK` 表示配置语法正确
- 输出错误信息时，根据错误码体系排查

#### 步骤四：加载配置

```bash
god load ~/.god/my_service.god
```

#### 步骤五：观察状态

```bash
god status
```

期望输出：

```
my_service: up
```

- `up`：进程运行中
- `down`：进程未运行
- `unmonitored`：未监控
- `pending`：等待操作

### 3.3 输出规范

| 输出类型 | 格式要求 |
|----------|----------|
| 配置文件 | 完整 Ruby 代码，含中文注释说明监控目的 |
| 状态报告 | 表格形式，包含服务名、状态、运行时长、资源占用 |
| 故障分析 | 按"现象 → 可能原因 → 排查步骤 → 解决方案"组织 |

---

## 四、置信度门控

当信息不足时，使用 `[需核实:字段]` 占位，不编造内容：

| 场景 | 占位示例 |
|------|----------|
| 服务启动命令未知 | `w.start = "[需核实:启动命令]"` |
| PID 文件路径不确定 | `w.pid_file = "[需核实:PID文件路径]"` |
| 内存阈值无依据 | `c.above = [需核实:内存阈值].megabytes` |
| 日志路径未确认 | `w.log = "[需核实:日志路径]"` |

---

## 五、错误码体系

| 错误现象 | 提示话术 | 修正步骤 |
|----------|----------|----------|
| `config file not found` | 配置文件路径错误 | 确认文件存在于 `~/.god/` 下，检查文件名拼写 |
| `syntax error` | 配置语法错误 | 检查 Ruby 语法，确认括号与引号闭合 |
| `permission denied` | 权限不足 | 检查配置文件权限（644）与 PID 目录权限（755） |
| `service already exists` | 服务名冲突 | 修改 `w.name` 为唯一名称 |
| `pid file not writable` | PID 文件不可写 | 确认运行 God 的用户对 PID 文件目录有写权限 |
| `command not found` | 启动命令不存在 | 检查 `w.start` 中的命令路径是否正确 |
| `port already in use` | 端口被占用 | 检查端口占用情况，调整服务配置或停止冲突进程 |
| `condition not supported` | 条件类型不支持 | 查阅 God 文档确认条件名称拼写 |

---

## 六、FAQ 反模式

### 6.1 常见坑与反模式对照

| 反模式 | 问题描述 | 正确做法 |
|--------|----------|----------|
| 配置文件权限设为 777 | 存在安全风险 | 设置为 644，仅所有者可写 |
| 所有服务共用一个 PID 文件 | 导致状态混乱 | 每个服务独立 PID 文件 |
| 监控条件阈值设置过高 | 资源耗尽才触发，失去保护意义 | 根据服务实际资源占用设置合理阈值 |
| 忽略 `god check` 直接加载 | 错误配置直接生效 | 先验证再加载 |
| 重启条件过于频繁 | 进程反复重启，影响服务稳定性 | 设置 `times` 参数，避免瞬时抖动触发 |
| 不设置日志输出 | 故障时无据可查 | 配置 `w.log` 指向日志文件 |

### 6.2 反模式修正示例

**反模式**：内存阈值设置 500MB，但服务正常占用 450MB

**修正**：将阈值调整为 600MB，并设置 `times = [3, 5]`，避免正常波动触发重启。

---

## 七、渐进式披露

### 7.1 速查卡（新手必读）

```
1. 创建配置 → ~/.god/<服务名>.god
2. 验证配置 → god check <配置文件>
3. 加载配置 → god load <配置文件>
4. 查看状态 → god status
5. 常见状态 → up / down / unmonitored / pending
```

### 7.2 新手路径（首次使用）

1. 阅读 **能力边界** 了解适用范围
2. 使用 **标准操作流程** 的模板创建第一个配置
3. 运行 `god check` 验证
4. 加载并观察 `god status` 输出
5. 遇到问题查阅 **错误码体系**

### 7.3 进阶路径（熟练用户）

1. 研究 **FAQ 反模式** 避免常见陷阱
2. 自定义复杂条件（内存、CPU、文件大小）
3. 结合 systemd 实现 God 自身守护
4. 编写巡检脚本，定期检查 `god status` 输出
5. 使用 God 的 Web 界面（`god -p 17165`）进行可视化监控

---

## 八、高级配置参考

### 8.1 CPU 监控条件

```ruby
# 监控目的：CPU 使用率持续过高时重启
w.restart_if do |restart|
  restart.condition(:cpu_usage) do |c|
    c.above = 80.percent
    c.times = 5
  end
end
```

### 8.2 文件大小监控条件

```ruby
# 监控目的：日志文件过大时触发清理
w.transition(:up, :restart) do |on|
  on.condition(:file_size) do |c|
    c.path = "/var/log/my_service.log"
    c.above = 100.megabytes
  end
end
```

### 8.3 生命周期钩子

```ruby
# 监控目的：进程启动后执行额外操作
w.lifecycle do |on|
  on.start(:before) { puts "准备启动" }
  on.start(:after) { puts "启动完成" }
  on.stop(:before) { puts "准备停止" }
  on.stop(:after) { puts "已停止" }
end
```

---

## 九、巡检脚本示例

```bash
#!/bin/bash
# 巡检 God 管理的所有服务状态
STATUS=$(god status 2>&1)
if echo "$STATUS" | grep -q "down"; then
  echo "[$(date)] 发现异常服务："
  echo "$STATUS" | grep "down"
  # 可在此添加告警通知逻辑
else
  echo "[$(date)] 所有服务运行正常"
fi
```

---

## 十、用户协议

<!-- user-agreement-injected -->

**使用本 Skill 即表示您同意以下条款：**

1. **责任承担**：使用者自行承担因使用本 Skill 产生的全部责任。包括但不限于配置错误导致的进程中断、数据丢失、服务不可用等后果。
2. **禁止反向工程**：不得对本 Skill 文档进行反向工程、反编译、破解或试图提取底层算法。
3. **合规使用**：使用者应确保其使用场景符合当地法律法规及所在组织的安全规范。
4. **无担保声明**：本 Skill 按"现状"提供，不附带任何明示或暗示的担保。

---

## 十一、许可证（License）

<!-- professional-license-embedded -->

### MIT License

Copyright (c) 2024 运维工坊

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
