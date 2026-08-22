---
slug: Agent-Reach
name: Agent-Reach
displayName: 智能体集群 批量运维 状态巡检
description: 本地批量管理AI智能体实例，支持启停控制与运行状态监控。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 林栖
agent_created: true
trigger_words: ["AI智能体本地控制", "Agent-Reach", "本地批量运维AI智能体", "智能体启停", "智能体状态监控", "实例管理", "进程守护"]
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# Agent-Reach 技能文档

## 一、能力边界（一页纸速查卡）

### 能做什么

| 能力项 | 说明 | 示例 |
|--------|------|------|
| 批量启停 | 对本地多个 AI 智能体实例执行启动或停止操作 | `agent-reach stop --all` |
| 状态巡检 | 查询单个或全部实例的运行状态、资源占用、心跳时间 | `agent-reach status --name worker-01` |
| 密钥认证 | 默认读取 `~/.ssh/id_rsa` 私钥完成 SSH 免密登录 | 无需额外参数 |
| 密码认证 | 通过 `--password` 参数临时指定密码登录 | `agent-reach start --name node-3 --password ****` |
| 自检与版本 | 验证工具自身完整性及输出版本号 | `agent-reach --selftest` / `agent-reach --version` |

### 不能做什么

- 不支持跨公网远程管理（仅限本地网络或本机回环地址）。
- 不提供实例内部的日志分析或业务数据查询。
- 不承担实例崩溃后的自动恢复（仅负责发出启停指令）。
- 密码认证方式不适用于生产环境，工具不会对密码做加密存储。

### 适用对象

- 本地开发环境中运行了 3 个以上 AI 智能体实例的开发者。
- 需要快速统一重启一组实验性智能体进程的研究人员。
- 负责维护内网 AI 服务节点的运维工程师。

---

## 二、触发方式与场景映射

| 触发词（用户可能说的话） | 实际执行动作 |
|--------------------------|--------------|
| “帮我看看本地智能体都活着没” | 执行 `agent-reach status --all` |
| “把那个 worker 节点重启一下” | 执行 `agent-reach restart --name worker-01` |
| “批量停掉所有测试实例” | 执行 `agent-reach stop --all --force` |
| “Agent-Reach 自检一下” | 执行 `agent-reach --selftest` |
| “用密码登录启动 node-2” | 执行 `agent-reach start --name node-2 --password <密码>` |

---

## 三、标准操作流程

### 前置条件

1. 目标主机已开启 SSH 服务（默认端口 22）。
2. 当前用户对目标实例拥有执行权限。
3. 若使用密钥认证，确认 `~/.ssh/id_rsa` 存在且权限为 600。
4. 若使用密码认证，确认网络链路可信（仅限开发环境）。

### 执行步骤（以“批量启动全部实例”为例）

1. **环境预检**  
   运行 `agent-reach --selftest` 确认工具自身可用。

2. **查看当前状态**  
   运行 `agent-reach status --all` 获取所有实例的实时状态，记录当前已停止的实例名。

3. **执行启动**  
   运行 `agent-reach start --all`。  
   若需指定密钥：`agent-reach start --all --key ~/.ssh/id_rsa`  
   若需指定密码：`agent-reach start --all --password <密码>`

4. **确认结果**  
   再次运行 `agent-reach status --all`，核对目标实例状态变为 `running`。

5. **输出规范**  
   所有命令输出遵循以下格式：
   ```
   [时间戳] [实例名] [操作类型] [结果状态] [附加信息]
   ```
   示例：
   ```
   2025-06-01 10:23:45 worker-01 start success pid=12345
   2025-06-01 10:23:45 worker-02 start failed reason=ssh_timeout
   ```

---

## 四、置信度门控

当遇到以下情况时，工具会输出 `[需核实:字段]` 占位符，**不会**编造数据：

| 场景 | 输出示例 |
|------|----------|
| 实例状态未知（SSH 连接超时） | `[需核实:worker-03状态] 连接超时，请手动检查` |
| 密码参数缺失 | `[需核实:认证方式] 未提供密码或密钥，无法继续` |
| 实例名不存在 | `[需核实:实例名] node-99 不在配置列表中` |

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| `E_AUTH_FAILED` | 认证失败 | “SSH 认证失败，请检查密钥或密码” | 1. 确认密钥路径正确；2. 确认密码无误；3. 改用 `--key` 显式指定密钥 |
| `E_CONN_TIMEOUT` | 连接超时 | “目标主机无响应，请检查网络” | 1. ping 目标 IP；2. 确认 SSH 端口开放；3. 增加 `--timeout 30` 参数 |
| `E_INSTANCE_NOT_FOUND` | 实例不存在 | “未找到指定实例，请核对名称” | 1. 运行 `agent-reach list` 查看全部实例名 |
| `E_PERM_DENIED` | 权限不足 | “当前用户无权操作该实例” | 1. 切换用户；2. 使用 sudo 前缀 |
| `E_BATCH_PARTIAL` | 批量操作部分失败 | “部分实例操作失败，详见输出” | 1. 查看输出中 `failed` 行；2. 对失败实例单独重试 |

---

## 六、FAQ 反模式对照

| 常见坑（反模式） | 正确做法 |
|------------------|----------|
| 在生产环境用 `--password` 传明文密码 | 仅限开发环境使用；生产必须改用 SSH 密钥 |
| 批量操作前不查看当前状态，直接 `--all` 启动 | 先执行 `status --all`，确认哪些实例需要操作 |
| 忽略 `--selftest` 直接执行管理命令 | 每次升级后先自检，避免工具本身异常导致误操作 |
| 超时时间使用默认值导致误判失败 | 对网络不稳的主机显式指定 `--timeout 60` |
| 停止实例时未加 `--force` 导致进程残留 | 确认无数据写入后使用 `--force` 强制终止 |

---

## 七、渐进式披露

### 速查卡（30 秒上手）

```bash
# 查看所有实例状态
agent-reach status --all

# 启动单个实例
agent-reach start --name worker-01

# 停止所有实例（强制）
agent-reach stop --all --force

# 工具自检
agent-reach --selftest
```

### 新手路径（首次使用）

1. 运行 `agent-reach --version` 确认安装成功。
2. 运行 `agent-reach --selftest` 验证环境。
3. 运行 `agent-reach list` 查看可管理的实例清单。
4. 对单个实例执行 `status` → `start` → `status` 三步验证。
5. 熟悉后再尝试 `--all` 批量操作。

### 进阶路径（日常运维）

1. 编写脚本定期执行 `status --all` 并记录输出。
2. 对失败实例设置重试逻辑（间隔 5 秒，最多 3 次）。
3. 使用 `--key` 参数指定专用部署密钥，避免使用默认密钥。
4. 结合 cron 实现定时巡检，输出重定向至日志文件。

---

## 八、参数速查表

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `--name` | string | 无 | 指定实例名，与 `--all` 互斥 |
| `--all` | bool | false | 操作全部实例 |
| `--key` | path | `~/.ssh/id_rsa` | SSH 私钥路径 |
| `--password` | string | 无 | SSH 密码（不推荐生产） |
| `--timeout` | int | 15 | 连接超时秒数 |
| `--force` | bool | false | 强制停止（跳过确认） |
| `--selftest` | bool | false | 运行自检后退出 |
| `--version` | bool | false | 输出版本后退出 |

---

## 九、用户协议

**使用 Agent-Reach 技能即表示您同意以下条款：**

1. 使用者自行承担因使用本技能产生的全部责任，包括但不限于因误操作导致的实例宕机、数据丢失或服务中断。
2. 禁止对本技能进行反向工程、反编译、破解或试图提取底层实现逻辑。
3. 本技能仅提供操作指引，不构成任何形式的服务承诺或质量保证。
4. 使用者应确保拥有对目标实例的合法管理权限。

<!-- user-agreement-injected -->

---

## 十、许可证（License）

本技能基于 MIT 许可证开源发布。

```
MIT License

Copyright (c) 2025 林栖

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
