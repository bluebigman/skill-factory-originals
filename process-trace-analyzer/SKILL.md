---
slug: process-trace-analyzer
name: process-trace-analyzer
displayName: 进程端口容器文件 启动溯源排查
description: 追踪进程、端口、容器或文件的启动来源，生成溯源报告，辅助定位异常与排查系统问题。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: TraceForge Lab
agent_created: true
trigger_words: ["进程溯源", "进程追踪", "端口溯源", "容器溯源", "文件溯源", "启动来源", "异常进程排查"]
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# 进程溯源分析器（Process Trace Analyzer）

## 一、能力边界（一页纸速查卡）

### 能做什么

| 输入类型 | 输入示例 | 输出内容 |
|---------|---------|---------|
| 进程名 | `nginx`、`sshd` | 启动命令、父进程链、可执行文件路径、启动时间、运行用户 |
| PID | `12345` | 进程详情、父进程链、环境变量（脱敏）、打开的文件句柄 |
| 端口号 | `8080`、`3306` | 监听该端口的进程、进程启动来源、连接状态 |
| 容器ID | `abc123def456` | 容器镜像来源、启动命令、所属 Pod/Compose 项目、创建者 |
| 文件路径 | `/tmp/malware.sh` | 文件创建进程、最近访问进程、文件类型、权限变更记录 |

### 不能做什么

- **不能** 提供实时监控或持续追踪（仅做一次性快照分析）
- **不能** 跨主机追踪（单机范围）
- **不能** 恢复已删除的进程信息（依赖系统日志留存）
- **不能** 自动判定恶意行为（只提供事实链，由用户判断）
- **不能** 绕过权限限制读取受保护进程信息（需 root/管理员权限）

### 适用对象

- 系统运维工程师：排查异常进程、端口冲突
- 安全分析人员：定位可疑启动项、追踪入侵痕迹
- 开发人员：确认服务启动配置、容器部署来源
- 合规审计人员：生成进程启动来源报告

---

## 二、触发方式（场景映射表）

| 你的需求（大白话） | 触发词 | 输入准备 |
|------------------|--------|---------|
| "有个进程叫 xmr，不知道哪来的" | 进程溯源 / 进程追踪 | 进程名或 PID |
| "8080 端口被占了，谁干的？" | 端口溯源 | 端口号 |
| "这个容器是谁启动的？" | 容器溯源 | 容器 ID 或名称 |
| "这个脚本什么时候被谁执行的？" | 文件溯源 | 文件绝对路径 |
| "检查一下系统有没有可疑的启动项" | 异常进程排查 | 无需特定输入，将执行全量扫描 |
| "帮我看看这个服务是怎么起来的" | 启动来源 | 服务名或进程名 |

---

## 三、标准流程

### 前置条件

| 条件 | 说明 | 检查方式 |
|------|------|---------|
| 操作系统 | Linux（优先）/ macOS / Windows（部分功能受限） | `uname -a` |
| 权限 | 建议 root 或管理员权限 | `id -u`（Linux 返回 0 即 root） |
| 工具依赖 | `ps`、`lsof`、`ss`、`systemctl`、`docker`（如查容器） | `which ps lsof ss` |
| 日志可读 | `/var/log/syslog` 或 `journalctl` 可访问 | `journalctl --no-pager -n 5` |

### 执行步骤

**Step 1：确认输入格式**

| 输入类型 | 格式要求 | 示例 |
|---------|---------|------|
| 进程名 | 1-64 字符，不含路径分隔符 | `nginx` |
| PID | 正整数，1-4194304 | `2345` |
| 端口号 | 1-65535 | `8080` |
| 容器ID | 12-64 位十六进制字符 | `abc123def456` |
| 文件路径 | 绝对路径，以 `/` 开头 | `/usr/local/bin/start.sh` |

**Step 2：选择分析模式**

```
模式 A：单目标溯源（默认）
  输入：进程名 / PID / 端口号 / 容器ID / 文件路径（任选其一）
  输出：该目标的完整溯源报告

模式 B：关联分析（进阶）
  输入：多个目标（如进程名 + 端口号）
  输出：目标间的关联关系图（文本形式）

模式 C：全量扫描
  输入：无（或指定目录）
  输出：所有可疑启动项清单
```

**Step 3：执行数据采集**

```bash
# 示例：按进程名采集
ps -eo pid,ppid,user,etime,cmd | grep -i "nginx" | grep -v grep

# 示例：按端口采集
lsof -i :8080 -P -n

# 示例：按容器采集
docker inspect abc123def456 --format '{{.Config.Cmd}} {{.Config.Entrypoint}}'

# 示例：按文件采集
stat /tmp/malware.sh
auditctl -w /tmp/malware.sh -p wa -k trace  # 需提前配置 auditd
```

**Step 4：构建进程链**

```
当前进程 ← 父进程 ← 祖父进程 ← ... ← init/systemd
```

通过递归查询 `/proc/<PID>/stat` 中的 `ppid` 字段，向上追溯至根进程。

**Step 5：生成溯源报告**

输出格式二选一（默认 Markdown）：

```markdown
# 溯源报告：进程 nginx (PID 2345)

## 基本信息
| 字段 | 值 |
|------|-----|
| 进程名 | nginx |
| PID | 2345 |
| 父进程 | systemd (PID 1) |
| 运行用户 | www-data |
| 启动时间 | 2024-01-15 08:30:22 |
| 运行时长 | 3天2小时 |

## 启动来源
- **启动命令**: /usr/sbin/nginx -g daemon on;
- **可执行文件**: /usr/sbin/nginx (SHA256: 3f2a...)
- **配置文件**: /etc/nginx/nginx.conf
- **启动方式**: systemd service (nginx.service)

## 进程链
systemd (PID 1) → nginx (PID 2345)

## 关联资源
- 监听端口: 80, 443
- 打开文件: /var/log/nginx/access.log, /var/log/nginx/error.log
- 网络连接: 无外部连接

## 置信度评估
- 整体置信度: **高**
- 依据: 进程链完整，启动命令明确，配置文件存在

## 备注
[需核实: 该进程是否由管理员手动启动]
```

### 输出规范

| 字段 | 必填 | 缺失处理 |
|------|------|---------|
| 进程名 / PID | 是 | 无法分析，报 E1001 |
| 父进程链 | 是 | 标记 `[需核实:父进程]` |
| 启动命令 | 是 | 标记 `[需核实:启动命令]` |
| 可执行文件路径 | 是 | 标记 `[需核实:可执行文件]` |
| 运行用户 | 是 | 标记 `[需核实:运行用户]` |
| 启动时间 | 否 | 标记 `[需核实:启动时间]` |
| 关联端口/文件 | 否 | 留空即可 |
| 置信度 | 是 | 必须标注 高/中/低 |

---

## 四、置信度门控机制

### 判定规则

| 置信度 | 判定条件 | 输出要求 |
|--------|---------|---------|
| **高** | 进程链完整（≥3 级），启动命令明确，可执行文件存在且校验通过 | 正常输出全部字段 |
| **中** | 进程链部分缺失（1-2 级），或启动命令模糊，或文件已被删除 | 缺失字段用 `[需核实:字段]` 占位 |
| **低** | 仅有单一信息源（如仅 PID），无法确认父进程，或系统日志不可用 | 输出占位符 + 明确提示"信息不足，建议补充数据源" |

### 占位符使用规范

```
格式：[需核实:字段名]
示例：[需核实:启动命令]、[需核实:父进程]、[需核实:容器镜像来源]
```

**禁止**：在信息不足时编造数据、猜测启动来源、推断父进程关系。

### 信息不足时的处理路径

1. 尝试补充数据源：`journalctl`、`auditd` 日志、`/var/log/messages`
2. 若仍无法获取，降低置信度等级
3. 在报告末尾附加"数据缺口说明"章节，列出缺失项及建议的补充手段

---

## 五、错误码体系

| 错误码 | 错误场景 | 提示话术 | 修正步骤 |
|--------|---------|---------|---------|
| E1001 | 输入格式无效（如 PID 为负数、端口超范围） | "输入参数无效，请检查格式" | 按 Step 1 的格式要求重新输入 |
| E1002 | 目标不存在（进程已退出、端口未监听） | "未找到匹配的目标，可能已停止运行" | 确认目标状态，或使用全量扫描模式 |
| E1003 | 权限不足（无法读取进程信息） | "权限不足，无法读取目标信息" | 切换至 root 用户或使用 sudo 重试 |
| E1004 | 依赖工具缺失（如 `lsof` 未安装） | "缺少必要工具：lsof" | 安装对应工具：`apt install lsof` 或 `yum install lsof` |
| E1005 | 系统日志不可用（journald 未运行） | "系统日志服务不可用，部分信息将缺失" | 启动 journald 服务，或指定其他日志路径 |
| E1006 | 输入目标过多（超过 10 个） | "一次最多分析 10 个目标，请分批执行" | 拆分输入，分批运行 |

---

## 六、FAQ 反模式对照

### 常见坑 1：只查进程名，忽略同名进程

**反模式**：输入 `nginx` 后，只取第一个结果，忽略其他同名进程。

**正确做法**：列出所有匹配的 PID，逐一分析，或使用 PID 精确定位。

### 常见坑 2：忽略环境变量中的敏感信息

**反模式**：直接输出完整环境变量，可能泄露密钥。

**正确做法**：对 `KEY=value` 格式做脱敏处理，仅显示键名和值的前 4 位。

### 常见坑 3：把容器内进程当作宿主机进程分析

**反模式**：在宿主机上看到容器内进程的 PID，直接按宿主机进程分析。

**正确做法**：先确认进程是否在容器内（检查 `/proc/<PID>/cgroup`），再切换至容器视角分析。

### 常见坑 4：依赖单一数据源

**反模式**：只依赖 `ps` 输出，不交叉验证。

**正确做法**：至少使用 `ps` + `lsof` + 日志三种数据源交叉验证。

### 常见坑 5：忽略时间线

**反模式**：只分析当前状态，不关注启动时间与系统事件的关联。

**正确做法**：将启动时间与系统日志中的关键事件（如补丁安装、配置变更）对齐分析。

---

## 七、渐进式披露（阅读路径）

### 速查卡（30 秒上手）

```
1. 确认输入格式（进程名/PID/端口/容器ID/文件路径）
2. 运行：进程溯源 <输入>
3. 查看输出报告中的"进程链"和"启动来源"
4. 关注置信度标注，低置信度时补充数据源
5. 遇到错误码，查第五节修正
```

### 新手路径（首次使用）

1. 阅读「一、能力边界」了解工具范围
2. 阅读「三、标准流程」的 Step 1-2，确认输入格式
3. 使用「二、触发方式」中的场景映射，找到自己的需求
4. 运行一次分析，查看输出报告结构
5. 遇到问题查阅「五、错误码体系」

### 进阶路径（深度使用）

1. 阅读「四、置信度门控机制」，理解判定规则
2. 阅读「六、FAQ 反模式对照」，避免常见错误
3. 结合多类数据（进程+端口+容器+文件）进行综合溯源
4. 使用 JSON 输出格式，对接自动化脚本
5. 自定义输出模板，适配内部报告格式

---

## 八、JSON 输出格式（自动化对接）

```json
{
  "schema_version": "1.0",
  "trace_id": "20240115-083022-2345",
  "target": {
    "type": "process",
    "name": "nginx",
    "pid": 2345
  },
  "process_chain": [
    {"pid": 1, "name": "systemd", "relation": "root"},
    {"pid": 2345, "name": "nginx", "relation": "target"}
  ],
  "startup_source": {
    "command": "/usr/sbin/nginx -g daemon on;",
    "executable": "/usr/sbin/nginx",
    "config_file": "/etc/nginx/nginx.conf",
    "start_method": "systemd"
  },
  "confidence": {
    "level": "high",
    "missing_fields": []
  },
  "errors": []
}
```

---

## 九、自定义输出模板

用户可在配置文件中定义自己的输出模板，支持变量替换：

```yaml
template: |
  ## 溯源摘要
  目标: {{target.name}} (PID {{target.pid}})
  启动方式: {{startup_source.start_method}}
  父进程: {{process_chain[-2].name}} (PID {{process_chain[-2].pid}})
  置信度: {{confidence.level}}
```

---

## 用户协议

使用本 Skill 即表示您同意以下条款：

1. **责任承担**：使用者自行承担因使用本 Skill 产生的全部责任。本 Skill 仅提供信息收集与整理功能，不构成任何形式的安全保证或合规承诺。
2. **禁止反向工程**：不得对本 Skill 的提示词、内部逻辑、评分机制进行反向工程、破解、提取或二次分发。
3. **数据合规**：使用者需确保所分析的进程、文件、容器等目标不涉及违反法律法规的数据。因使用本 Skill 产生的数据合规问题，由使用者自行负责。
4. **无担保声明**：本 Skill 按"原样"提供，不附带任何明示或暗示的担保，包括但不限于适销性、特定用途适用性和非侵权保证。

<!-- user-agreement-injected -->

---

## 许可证（License）

本 Skill 采用 MIT 许可证发布：

```
MIT License

Copyright (c) 2024 TraceForge Lab

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

*本 Skill 由 AI 辅助生成，仅供参考。使用前请阅读相关文档，并结合实际环境验证输出结果。*
