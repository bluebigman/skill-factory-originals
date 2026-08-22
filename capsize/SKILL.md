---
slug: capsize
name: capsize
displayName: EC2部署 远程运维 Cstrano扩展
description: 管理Amazon EC2应用部署流程，支持Cstrano扩展与远程运维。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: deploy-craft
agent_created: true
trigger_words: ["capsize", "EC2部署", "Cstrano扩展", "AWS运维", "远程部署", "云主机发布", "弹性计算部署"]

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# capsize — EC2 应用部署与 Cstrano 扩展管理 Skill

## 一、能力边界（一页纸速查卡）

### 1.1 能做与不能做

| 维度 | 能做 ✅ | 不能做 ❌ |
|------|---------|-----------|
| **部署管理** | 管理 EC2 实例上的应用发布流程，包括构建产物上传、远程执行部署命令、版本回滚 | 直接修改 AWS 控制台策略、创建或销毁 EC2 实例（需通过 AWS CLI 或控制台预先完成） |
| **Cstrano 扩展** | 调用 Cstrano 扩展接口执行自定义部署任务，管理扩展配置 | 编写 Cstrano 扩展插件源码，调试扩展内部逻辑 |
| **远程操作** | 通过 SSH 执行部署脚本、检查服务状态、查看部署日志 | 绕过 SSH 密钥认证直接访问实例，修改安全组规则 |
| **文件处理** | 将本地构建产物打包并传输至目标实例，校验文件完整性 | 在实例上执行任意非部署相关命令（如数据库操作） |
| **流程编排** | 按预定义步骤串联部署流程，支持试运行与批量执行 | 动态生成新的部署策略（需提前在配置中定义） |

### 1.2 适用对象

- **适用**：使用 Amazon EC2 作为应用服务器、需要标准化部署流程的团队；已配置好 Cstrano 扩展环境、需要统一管理入口的运维人员。
- **不适用**：未开通 AWS 账号或未配置 EC2 密钥对的用户；需要图形化界面操作 AWS 控制台的场景；对部署安全性有合规审计要求的金融级场景（本工具不提供审计日志导出）。

### 1.3 输入输出速查

| 项目 | 说明 |
|------|------|
| **输入** | 部署清单文件（JSON/YAML）、构建产物目录、目标实例 IP 列表、SSH 密钥路径 |
| **输出** | 部署状态报告（含每台实例的执行结果）、错误日志、回滚确认单 |
| **退出码** | 0=成功；1=参数错误；2=连接失败；3=脚本执行异常；4=校验不通过 |

---

## 二、触发方式与场景映射

### 2.1 触发词

直接使用以下任一词汇即可激活本 Skill：

- `capsize`
- `EC2部署`
- `Cstrano扩展`
- `AWS运维`
- `远程部署`
- `云主机发布`（补充）
- `弹性计算部署`（补充）

### 2.2 大白话场景映射表

| 你说的话（口语化表达） | Skill 理解后的动作 |
|------------------------|---------------------|
| "帮我把新版本推到那几台服务器上" | 读取部署清单，将构建产物传输至目标 EC2 实例并执行部署脚本 |
| "上次的发布好像有问题，帮我看看" | 检查部署日志，定位失败步骤，输出错误码与修正建议 |
| "先拿一台机器试试，别全上" | 进入试运行模式，仅对清单中标记为 `canary: true` 的实例执行部署 |
| "Cstrano 那边有个新任务要跑" | 调用 Cstrano 扩展接口，执行配置中定义的自定义任务 |
| "部署完帮我确认一下服务是不是起来了" | 部署完成后自动执行健康检查脚本（需在配置中声明 `health_check` 命令） |

---

## 三、标准流程

### 3.1 前置条件

| 条件项 | 要求 | 校验方式 |
|--------|------|----------|
| 部署清单 | 文件存在且格式合法（JSON/YAML），包含 `instances` 数组与 `deploy` 对象 | 启动时自动解析，格式错误报错码 `E1001` |
| SSH 密钥 | 密钥文件存在且权限为 600，能通过目标实例认证 | 连接前校验，失败报错码 `E2001` |
| 构建产物 | 目录存在且包含 `artifact.tar.gz`（或配置中指定的文件名） | 打包前检查，缺失报错码 `E1002` |
| Cstrano 配置 | 若使用扩展，需存在 `cstrano_config.yml` 且包含 `tasks` 定义 | 调用扩展前加载，缺失报错码 `E3001` |
| 网络连通 | 本机可访问目标实例的 22 端口（SSH） | 连接时检测，超时报错码 `E2002` |

### 3.2 执行步骤（分步编号）

#### 阶段一：准备输入

1. 将待部署的构建产物（如 `artifact.tar.gz`）与部署清单（`deploy.json`）放入同一工作目录。
2. 确认命名规范：清单文件必须为 `deploy.json` 或 `deploy.yaml`，产物文件名需与清单中 `artifact_name` 字段一致。
3. 检查清单内容完整性：`instances` 数组至少包含 1 个实例对象，每个对象需有 `ip` 与 `role` 字段。

#### 阶段二：试运行

4. 执行 `capsize --dry-run` 进入试运行模式。
5. 系统仅对清单中 `canary: true` 的实例执行部署流程，其余实例跳过。
6. 核对输出字段：每台实例应输出 `instance_ip`、`deploy_status`、`duration_ms`、`log_tail` 四个字段。
7. 确认输出格式与预期一致，无异常报错。

#### 阶段三：批量执行

8. 执行 `capsize --run` 进入全量部署模式。
9. 系统按清单顺序逐台执行部署，每台实例独立记录日志。
10. 部署前自动备份目标实例上的旧版本产物至 `/opt/backups/{timestamp}/` 目录。
11. 若某台实例部署失败，默认跳过继续执行后续实例（可通过 `--fail-fast` 参数改为立即终止）。

#### 阶段四：校验结果

12. 部署完成后，系统输出汇总报告，包含每台实例的部署状态。
13. 抽查 20% 的实例（至少 1 台），核对 `deploy_status` 为 `success` 的实例其 `log_tail` 中是否包含 `DEPLOY_OK` 标记。
14. 若存在 `failed` 状态的实例，查看对应错误码并参考第五节修正后重试。

### 3.3 输出规范

| 输出项 | 格式 | 示例 |
|--------|------|------|
| 汇总报告 | JSON 数组，每元素对应一台实例 | `[{"instance_ip":"10.0.0.1","deploy_status":"success","duration_ms":4520,"log_tail":"...DEPLOY_OK..."}]` |
| 错误日志 | 写入 `./logs/capsize_error_{timestamp}.log` | `[E2002] 连接 10.0.0.2:22 超时（15s）` |
| 回滚确认单 | 当部署失败且执行回滚时输出 | `rollback_required: true, instance: 10.0.0.3, reason: script_exit_1` |

---

## 四、置信度门控

当遇到以下信息不足的情况时，**不得编造数据**，必须输出占位符 `[需核实:字段名]`：

| 场景 | 占位符示例 | 后续动作 |
|------|------------|----------|
| 清单中缺少实例的 `region` 字段 | `[需核实:region]` | 提示用户补充，或从 AWS 默认配置读取 |
| 部署脚本返回非零退出码但无错误信息 | `[需核实:exit_reason]` | 建议用户登录实例查看 `/var/log/deploy.log` |
| Cstrano 任务名称在配置中不存在 | `[需核实:task_name]` | 列出可用任务列表，请用户确认 |
| 健康检查命令未在清单中声明 | `[需核实:health_check_cmd]` | 跳过健康检查，在报告中标注 `health_check: skipped` |

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| `E1001` | 部署清单解析失败 | "部署清单格式错误，请检查 JSON/YAML 语法" | 1. 用 `json.tool` 或 `yaml.lint` 校验文件；2. 确认字段名与文档一致 |
| `E1002` | 构建产物缺失 | "未找到构建产物文件，请确认文件名与清单一致" | 1. 检查 `artifact_name` 字段；2. 将产物放入工作目录 |
| `E2001` | SSH 密钥认证失败 | "SSH 密钥无法通过认证，请检查密钥权限与指纹" | 1. 执行 `chmod 600 key.pem`；2. 确认密钥对与实例匹配 |
| `E2002` | 连接超时 | "无法连接目标实例，请检查网络与安全组" | 1. 确认实例公网 IP 正确；2. 检查安全组是否放行 22 端口 |
| `E3001` | Cstrano 配置缺失 | "未找到 cstrano_config.yml，无法执行扩展任务" | 1. 确认配置文件存在；2. 检查 `tasks` 字段定义 |
| `E4001` | 部署脚本执行异常 | "部署脚本返回非零退出码，请查看日志" | 1. 查看 `log_tail` 输出；2. 登录实例检查 `/var/log/deploy.log` |
| `E4002` | 健康检查失败 | "部署完成但健康检查未通过" | 1. 确认服务端口监听正常；2. 检查健康检查命令路径 |

---

## 六、FAQ 反模式对照

| 常见坑（反模式） | 问题描述 | 正确做法（正模式） |
|------------------|----------|---------------------|
| **跳过试运行直接全量** | 用户未执行 `--dry-run` 直接 `--run`，导致批量部署时才发现脚本错误 | 强制要求：首次部署或脚本变更后必须先试运行，系统在检测到清单 `canary` 字段为空时主动提示 |
| **忽略备份直接覆盖** | 部署脚本直接覆盖旧版本，回滚时无可用版本 | 系统默认在部署前自动备份至 `/opt/backups/`，若用户手动关闭备份（`--no-backup`），需二次确认 |
| **错误码只看不查** | 用户看到 `E2002` 后反复重试，未检查安全组配置 | 错误提示中附带检查清单（如"请确认安全组入站规则包含 22 端口"），引导用户按步骤排查 |
| **Cstrano 任务名拼写错误** | 调用不存在的任务名，系统报 `E3001` 但用户不理解 | 报错时列出配置中所有可用任务名，方便用户对照修正 |
| **多实例并行误判** | 用户以为系统并行部署所有实例，实际是串行执行，导致时间预估偏差 | 输出报告中明确标注 `execution_mode: serial`，并在启动时提示预计总耗时 |

---

## 七、渐进式披露

### 7.1 速查卡（30 秒上手）

```
1. 放文件：deploy.json + artifact.tar.gz 放同一目录
2. 试运行：capsize --dry-run
3. 看结果：确认输出字段正常
4. 全量跑：capsize --run
5. 查报告：看汇总 JSON 中 deploy_status
```

### 7.2 分层次阅读路径

| 读者角色 | 建议阅读内容 | 目标 |
|----------|--------------|------|
| **新手（首次使用）** | 第一节（能力边界）+ 第三节（标准流程）+ 速查卡 | 能独立完成一次标准部署 |
| **进阶（日常运维）** | 第五节（错误码）+ 第六节（FAQ 反模式） | 能排查常见问题，减少工单 |
| **专家（定制化需求）** | 第三节（完整流程）+ 第四节（置信度门控）+ Cstrano 扩展配置文档 | 能自定义部署策略与扩展任务 |

### 7.3 参数速查表

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `--dry-run` | 布尔 | false | 试运行模式，仅执行 canary 实例 |
| `--run` | 布尔 | false | 全量部署模式 |
| `--fail-fast` | 布尔 | false | 遇到失败立即终止，不继续后续实例 |
| `--no-backup` | 布尔 | false | 禁用部署前自动备份（需二次确认） |
| `--timeout` | 整数 | 30 | SSH 连接超时时间（秒） |
| `--retry` | 整数 | 2 | 单台实例部署失败后的重试次数 |

---

## 八、用户协议

<!-- user-agreement-injected -->

**使用本 Skill 即表示您同意以下条款：**

1. **责任承担**：使用者自行承担因使用本 Skill 进行部署操作所产生的一切后果，包括但不限于数据丢失、服务中断、配置错误等。Skill 提供方不对任何直接或间接损失负责。
2. **禁止反向工程**：不得对本 Skill 的底层逻辑、提示词结构、评分机制进行反向工程、破解、篡改或二次分发。
3. **合规使用**：使用者须确保其部署行为符合所在组织及 AWS 服务条款的相关规定，不得用于任何非法用途。
4. **无担保声明**：本 Skill 按"现状"提供，不附带任何明示或暗示的担保，包括但不限于适销性、特定用途适用性。

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

*本 Skill 由 AI 辅助生成，仅供参考。使用前请阅读相关文档并自行验证适用性。*
