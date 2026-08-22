---
slug: ec2-aws-and-shell
name: ec2-aws-and-shell
displayName: EC2运维 Shell操作 云主机规范
description: 面向AWS EC2实例的Shell操作规范化处理与输出模板。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: SkillForge Studio
agent_created: true
trigger_words: ["EC2运维", "AWS云主机", "Shell脚本处理", "云服务器操作", "实例标签", "EC2管理", "AWS运维"]

---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# EC2 运维与 Shell 操作规范

## 一、能力边界（一页纸速查卡）

### 本 Skill 能做什么

| 能力项 | 说明 | 典型场景 |
|--------|------|----------|
| EC2 实例信息查询 | 获取实例 ID、状态、类型、IP、标签等元数据 | 盘点资源、故障排查前摸底 |
| Shell 命令规范化 | 将零散命令整理为可复用脚本，统一输出格式 | 批量操作、自动化巡检 |
| 标签管理辅助 | 生成标签增删改查的 CLI 命令模板 | 成本分摊、环境标识 |
| 输出模板生成 | 将命令结果整理为结构化表格或 JSON | 汇报、交接、审计 |

### 本 Skill 不能做什么

| 限制项 | 说明 |
|--------|------|
| 不执行真实操作 | 仅生成命令与脚本模板，不代替用户实际运行 |
| 不处理认证授权 | 不涉及 IAM 策略配置、密钥管理、MFA 等 |
| 不覆盖所有 AWS 服务 | 仅聚焦 EC2 与基础 Shell 操作，不涉及 S3、Lambda 等 |
| 不保证命令兼容性 | 不同 AWS CLI 版本、操作系统可能导致命令差异 |

### 适用对象

- 需要频繁操作 EC2 的运维工程师
- 刚接触 AWS CLI 的开发者
- 需要规范化运维脚本的团队

---

## 二、触发方式

当你的请求包含以下关键词或意图时，本 Skill 会被激活：

| 触发词 | 大白话场景 |
|--------|------------|
| EC2运维 | "帮我看下 EC2 实例状态" |
| AWS云主机 | "列出所有云主机信息" |
| Shell脚本处理 | "写个脚本批量重启实例" |
| 云服务器操作 | "怎么用命令行停止服务器" |
| 实例标签 | "给实例加个环境标签" |
| EC2管理 | "管理我的 EC2 资源" |
| AWS运维 | "日常 AWS 运维有哪些常用命令" |

---

## 三、标准操作流程

### 前置条件

| 条件 | 检查项 | 验证方法 |
|------|--------|----------|
| AWS CLI 已安装 | `aws --version` | 输出版本号即通过 |
| 凭证已配置 | `aws sts get-caller-identity` | 返回账号 ID 即通过 |
| 区域已设置 | `aws configure list` | 确认 `region` 字段有值 |
| jq 工具（可选） | `jq --version` | 输出版本号即通过 |

### 执行步骤

#### 步骤 1：确认操作目标

明确你要操作的实例范围：

```bash
# 查看所有实例（含停止状态）
aws ec2 describe-instances --query "Reservations[].Instances[].[InstanceId,State.Name,Tags[?Key=='Name'].Value|[0]]" --output table

# 仅查看运行中的实例
aws ec2 describe-instances --filters "Name=instance-state-name,Values=running" --query "Reservations[].Instances[].InstanceId" --output text
```

#### 步骤 2：生成操作命令

根据需求选择操作类型，参考以下模板：

| 操作类型 | 命令模板 | 注意事项 |
|----------|----------|----------|
| 启动实例 | `aws ec2 start-instances --instance-ids i-xxxxxxxx` | 确认实例处于停止状态 |
| 停止实例 | `aws ec2 stop-instances --instance-ids i-xxxxxxxx` | 谨慎操作，影响业务 |
| 重启实例 | `aws ec2 reboot-instances --instance-ids i-xxxxxxxx` | 比 stop/start 更快 |
| 查询状态 | `aws ec2 describe-instance-status --instance-ids i-xxxxxxxx` | 返回系统与实例状态 |

#### 步骤 3：格式化输出

将结果整理为易读格式：

```bash
# 输出为 JSON 并提取关键字段
aws ec2 describe-instances --instance-ids i-xxxxxxxx \
  --query "Reservations[].Instances[].[InstanceId,InstanceType,PublicIpAddress,State.Name]" \
  --output json | jq '.[] | {ID: .[0], Type: .[1], IP: .[2], State: .[3]}'
```

#### 步骤 4：验证结果

```bash
# 确认操作生效
aws ec2 describe-instances --instance-ids i-xxxxxxxx --query "Reservations[].Instances[].State.Name" --output text
```

### 输出规范

所有输出应包含：

1. **操作时间戳**：记录执行时间
2. **实例标识**：明确操作对象
3. **操作结果**：成功/失败/进行中
4. **后续建议**：如需人工介入，给出提示

---

## 四、置信度门控

当信息不足时，使用 `[需核实:字段]` 占位，不编造数据：

| 场景 | 占位示例 |
|------|----------|
| 实例 ID 未知 | `[需核实:实例ID]` |
| 区域未指定 | `[需核实:AWS区域]` |
| 凭证未确认 | `[需核实:凭证有效性]` |
| 命令版本不确定 | `[需核实:AWS CLI版本]` |

**示例**：

```bash
# 用户未提供实例 ID 时
aws ec2 describe-instances --instance-ids [需核实:实例ID]
```

---

## 五、错误码体系

| 错误码 | 常见错误 | 提示话术 | 修正步骤 |
|--------|----------|----------|----------|
| E001 | 凭证过期 | "凭证无效，请检查 AWS 凭证配置" | 运行 `aws configure` 重新配置 |
| E002 | 实例不存在 | "找不到指定实例，请确认 ID 是否正确" | 运行 `aws ec2 describe-instances` 列出所有实例 |
| E003 | 权限不足 | "当前凭证无权执行此操作" | 检查 IAM 策略，联系管理员授权 |
| E004 | 区域不匹配 | "实例不在当前区域" | 使用 `--region` 参数指定正确区域 |
| E005 | 命令语法错误 | "命令格式有误，请参考帮助文档" | 运行 `aws ec2 help` 查看用法 |

---

## 六、FAQ 反模式

| 常见坑 | 反模式（错误做法） | 正确做法 |
|--------|-------------------|----------|
| 忘记指定区域 | 直接运行命令，未加 `--region` | 始终显式指定区域，或设置默认区域 |
| 批量操作无确认 | 直接对多个实例执行 stop/terminate | 先查询列表，人工确认后再操作 |
| 忽略输出格式 | 直接使用默认输出，难以解析 | 使用 `--query` 和 `--output` 控制格式 |
| 混用新旧命令 | 同时使用 ec2-cli 和 aws cli 命令 | 统一使用 aws cli v2 语法 |
| 不检查返回码 | 命令失败后继续后续操作 | 使用 `$?` 检查退出码，或使用 `set -e` |

---

## 七、渐进式披露

### 新手路径（首次使用）

1. 阅读「一、能力边界」了解适用范围
2. 阅读「三、标准操作流程」的步骤 1-2
3. 使用「速查卡」完成第一次操作

### 进阶路径（日常使用）

1. 阅读「三、标准操作流程」全部步骤
2. 自定义脚本，参考「六、FAQ 反模式」避免常见错误
3. 结合 AWS CLI 高级特性（如 `--query`、`--filter`）扩展功能
4. 建立自动化流水线，集成 CI/CD

### 专家路径（深度定制）

1. 扩展错误处理机制，自定义错误码
2. 集成 AWS CloudWatch 监控，实现自动化告警
3. 开发 Web 界面，可视化操作流程
4. 编写单元测试，确保脚本可靠性

---

## 八、速查卡

```bash
# 常用命令速查

# 列出所有实例
aws ec2 describe-instances --query "Reservations[].Instances[].[InstanceId,State.Name,Tags[?Key=='Name'].Value|[0]]" --output table

# 启动实例
aws ec2 start-instances --instance-ids i-xxxxxxxx

# 停止实例
aws ec2 stop-instances --instance-ids i-xxxxxxxx

# 重启实例
aws ec2 reboot-instances --instance-ids i-xxxxxxxx

# 查看实例状态
aws ec2 describe-instance-status --instance-ids i-xxxxxxxx

# 添加标签
aws ec2 create-tags --resources i-xxxxxxxx --tags Key=Environment,Value=Production

# 删除标签
aws ec2 delete-tags --resources i-xxxxxxxx --tags Key=Environment
```

---

## 用户协议

<!-- user-agreement-injected -->

**使用本 Skill 即表示您同意以下条款：**

1. **责任承担**：使用者自行承担因使用本 Skill 产生的全部责任。包括但不限于因操作失误、配置错误、权限不当导致的资源损失、数据丢失或服务中断。

2. **禁止反向工程**：不得对本 Skill 进行反向工程、反编译、破解或试图提取源代码（除非适用法律允许）。

3. **无担保声明**：本 Skill 按"原样"提供，不附带任何明示或暗示的担保，包括但不限于适销性、特定用途适用性和非侵权保证。

4. **合规使用**：使用者须确保其使用方式符合 AWS 服务条款及当地法律法规。

---

## 许可证（License）

<!-- professional-license-embedded -->

### MIT License

Copyright (c) 2024 SkillForge Studio

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

*本 Skill 由 AI 辅助生成，仅供参考。使用前请阅读 AWS 官方文档确认命令兼容性。*
