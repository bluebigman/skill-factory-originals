---
slug: switchpipe
name: switchpipe
displayName: 后端进程代理 部署编排 端口管理
description: 管理后端进程与HTTP代理，简化Web应用部署流程。
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
trigger_words: ["switchpipe", "进程管理", "HTTP代理", "后端部署", "Web应用部署", "端口转发", "反向代理"]
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# switchpipe Skill 文档

## 一、能力边界（一页纸速查卡）

### 1.1 能做什么

| 能力项 | 说明 | 典型场景 |
|--------|------|----------|
| 后端进程管理 | 启动、停止、重启、查看后端服务进程 | 本地开发环境启动 Node/Python/Go 服务 |
| HTTP 代理配置 | 将外部请求转发到内部后端服务 | 前端开发服务器代理 API 请求 |
| 端口映射管理 | 绑定端口、查看占用、释放端口 | 多服务并行开发时避免端口冲突 |
| 部署流程编排 | 按顺序执行启动脚本、健康检查、代理绑定 | 一键启动完整 Web 应用栈 |

### 1.2 不能做什么

| 限制项 | 说明 |
|--------|------|
| 不管理数据库 | 不负责数据库实例的启停与迁移 |
| 不处理静态文件 | 不替代 Nginx 等静态资源服务器 |
| 不提供负载均衡 | 单机工具，不面向集群场景 |
| 不进行代码构建 | 不执行编译、打包等构建步骤 |

### 1.3 适用对象

- 前端开发者：需要快速将 API 请求代理到本地后端服务
- 全栈开发者：需要同时管理多个后端进程与端口映射
- DevOps 初学者：希望用命令行简化本地部署验证流程

---

## 二、触发方式

### 2.1 触发词

| 触发词 | 场景描述 |
|--------|----------|
| switchpipe | 直接调用工具主命令 |
| 进程管理 | 需要查看或操作后端进程时 |
| HTTP代理 | 需要配置请求转发规则时 |
| 后端部署 | 需要启动或重启后端服务时 |
| Web应用部署 | 需要完整启动前端+后端应用时 |
| 端口转发 | 需要将请求从一个端口转到另一个端口时 |
| 反向代理 | 需要将外部请求分发到内部服务时 |

### 2.2 大白话场景映射

| 用户说 | 实际需求 | 对应操作 |
|--------|----------|----------|
| "帮我把我电脑上的 Node 服务跑起来" | 启动后端进程 | `switchpipe process start --name node-app` |
| "前端请求 /api 打不到后端" | 配置代理规则 | `switchpipe proxy add --from /api --to localhost:3000` |
| "端口 8080 被占了，帮我看看是谁" | 查看端口占用 | `switchpipe port inspect --port 8080` |
| "一键启动我的项目" | 执行部署编排 | `switchpipe deploy --config switchpipe.yaml` |

---

## 三、标准流程

### 3.1 前置条件

| 条件 | 检查方法 | 不满足时的处理 |
|------|----------|----------------|
| 已安装 switchpipe | `switchpipe --version` | 运行 `npm install -g switchpipe` 或参考官方安装文档 |
| 目标进程可执行 | `which node` 或 `which python3` | 安装对应运行时环境 |
| 配置文件存在（如需要） | `ls switchpipe.yaml` | 使用 `switchpipe init` 生成模板 |
| 端口未被占用 | `switchpipe port inspect --port <端口号>` | 释放端口或更换端口 |

### 3.2 执行步骤

#### 步骤 1：初始化配置（首次使用）

```bash
switchpipe init
```

生成 `switchpipe.yaml` 模板文件，包含以下结构：

```yaml
processes:
  - name: backend
    command: node server.js
    cwd: ./backend
    port: 3000

proxy:
  - from: /api
    to: http://localhost:3000

deploy_order:
  - backend
```

#### 步骤 2：启动后端进程

```bash
# 启动单个进程
switchpipe process start --name backend

# 启动全部配置的进程
switchpipe process start --all
```

#### 步骤 3：配置 HTTP 代理

```bash
# 添加代理规则
switchpipe proxy add --from /api --to http://localhost:3000

# 查看当前代理规则
switchpipe proxy list
```

#### 步骤 4：执行健康检查

```bash
switchpipe health --endpoint http://localhost:3000/health
```

#### 步骤 5：一键部署（可选）

```bash
switchpipe deploy --config switchpipe.yaml
```

### 3.3 输出规范

所有命令输出采用以下格式：

```
[状态] 时间戳 消息内容
```

示例：

```
[OK] 2025-01-15 10:30:00 进程 backend 已启动，监听端口 3000
[WARN] 2025-01-15 10:30:01 端口 3000 已被占用，尝试使用 3001
[ERR] 2025-01-15 10:30:02 代理规则 /api 已存在，请使用 --force 覆盖
```

---

## 四、置信度门控

当遇到以下情况时，输出 `[需核实:字段]` 占位符，不进行猜测：

| 场景 | 输出示例 |
|------|----------|
| 进程启动失败但原因未知 | `[需核实:进程退出码] 进程 backend 启动失败，退出码未知` |
| 端口占用但无法识别占用者 | `[需核实:占用进程] 端口 8080 被未知进程占用` |
| 代理目标不可达 | `[需核实:目标服务状态] 代理目标 http://localhost:3000 无响应` |
| 配置文件字段缺失 | `[需核实:配置项] switchpipe.yaml 缺少 deploy_order 字段` |

**原则**：宁可明确标注未知，也不编造数据。

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| E001 | 进程启动失败 | `进程启动失败，请检查命令和路径` | 1. 检查命令是否存在；2. 确认工作目录正确；3. 查看日志 `switchpipe log --name <进程名>` |
| E002 | 端口已被占用 | `端口 <端口号> 已被占用` | 1. 查看占用者 `switchpipe port inspect --port <端口号>`；2. 释放端口或改用 `--port <新端口>` |
| E003 | 代理规则冲突 | `代理规则 <路径> 已存在` | 1. 使用 `--force` 覆盖；2. 或先删除旧规则 `switchpipe proxy remove --from <路径>` |
| E004 | 配置文件解析失败 | `配置文件格式错误，请检查 YAML 语法` | 1. 使用 `switchpipe validate` 检查；2. 对照模板修正 |
| E005 | 健康检查超时 | `健康检查超时（默认 5 秒）` | 1. 确认服务已启动；2. 调整超时 `--timeout 10` |
| E006 | 依赖进程未启动 | `依赖进程 <进程名> 未启动` | 1. 按 deploy_order 顺序启动；2. 或使用 `--ignore-deps` 跳过检查 |

---

## 六、FAQ 反模式

### 6.1 常见坑

| 坑 | 反模式描述 | 正确做法 |
|----|------------|----------|
| 坑 1：忽略端口占用 | 直接启动新进程，导致旧进程被系统杀掉 | 先检查端口占用，再决定是否复用或更换端口 |
| 坑 2：代理路径写错 | 代理规则 `/api` 写成 `/api/`，导致匹配失败 | 统一使用不带尾部斜杠的路径格式 |
| 坑 3：不检查健康状态 | 启动后立即部署，服务尚未就绪 | 启动后等待 2-3 秒，再执行健康检查 |
| 坑 4：配置文件不校验 | 修改 YAML 后直接部署，语法错误导致全部失败 | 先执行 `switchpipe validate` 再部署 |
| 坑 5：忽略日志 | 进程启动失败后不查看日志，反复重试 | 使用 `switchpipe log --name <进程名>` 查看详细错误 |

### 6.2 反模式对照表

| 反模式 | 问题 | 替代方案 |
|--------|------|----------|
| 手动 kill 进程 | 可能误杀其他服务 | 使用 `switchpipe process stop --name <进程名>` |
| 用 `lsof` 手动查端口 | 输出冗长，不易解析 | 使用 `switchpipe port inspect --port <端口号>` |
| 在代码里硬编码代理地址 | 环境切换时需改代码 | 使用 switchpipe.yaml 统一管理代理配置 |

---

## 七、渐进式披露

### 7.1 速查卡（新手必读）

```bash
# 最常用的 5 个命令
switchpipe init                    # 初始化配置
switchpipe process start --all     # 启动所有进程
switchpipe proxy list              # 查看代理规则
switchpipe deploy                  # 一键部署
switchpipe --version               # 查看版本
```

### 7.2 分层次阅读路径

#### 新手路径（5 分钟上手）

1. 阅读「能力边界」了解工具范围
2. 执行 `switchpipe init` 生成配置
3. 修改配置文件中的进程命令和端口
4. 执行 `switchpipe deploy` 完成首次部署

#### 进阶路径（深入使用）

1. 阅读「标准流程」理解完整部署链路
2. 掌握「错误码体系」快速定位问题
3. 参考「FAQ 反模式」避免常见陷阱
4. 自定义 `switchpipe.yaml` 中的 `deploy_order` 实现多服务编排

#### 专家路径（扩展定制）

1. 结合 CI/CD 流水线，将 `switchpipe deploy` 集成到自动化流程
2. 使用 `switchpipe port inspect` 编写端口冲突检测脚本
3. 通过 `switchpipe log` 输出对接日志收集系统

---

## 八、参数速查表

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `--config` | string | `switchpipe.yaml` | 指定配置文件路径 |
| `--port` | int | 无 | 指定端口号 |
| `--timeout` | int | 5 | 健康检查超时时间（秒） |
| `--force` | bool | false | 强制覆盖已有配置 |
| `--ignore-deps` | bool | false | 跳过依赖检查 |
| `--all` | bool | false | 操作所有进程 |
| `--name` | string | 无 | 指定进程名称 |
| `--from` | string | 无 | 代理源路径 |
| `--to` | string | 无 | 代理目标地址 |

---

## 九、用户协议

<!-- user-agreement-injected -->

**使用前请仔细阅读以下条款：**

1. **责任承担**：使用者自行承担使用本 Skill 的全部责任。因使用、误用或依赖本 Skill 导致的任何直接或间接损失，作者不承担任何责任。
2. **禁止反向工程**：不得对本 Skill 进行反向工程、反编译、破解或试图提取源代码（除非适用法律允许）。
3. **合规使用**：使用者应确保使用本 Skill 的行为符合当地法律法规及所在组织的安全政策。
4. **无担保声明**：本 Skill 按"现状"提供，不附带任何明示或暗示的担保，包括但不限于适销性、特定用途适用性和非侵权性担保。

---

## 十、许可证（License）

<!-- professional-license-embedded -->

**MIT License**

```
MIT License

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
```

---

## 十一、自检清单

发布前请确认：

- [x] frontmatter 包含全部必填字段
- [x] 无绝对化承诺用语
- [x] 包含 AI 辅助生成免责声明
- [x] 包含用户协议章节（带 marker）
- [x] 包含 MIT 许可证全文（带 marker）
- [x] 包含置信度门控机制
- [x] 包含错误码体系
- [x] 包含 FAQ 反模式
- [x] 包含渐进式披露路径

---

*本 Skill 由 AI 辅助生成，仅供参考。使用前请阅读相关文档。*
