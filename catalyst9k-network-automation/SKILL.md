---
slug: catalyst9k-network-automation
name: catalyst9k-network-automation
displayName: 交换机配置 脚本生成 网络编排
description: 将网络配置需求转化为可执行脚本，辅助Catalyst交换机的自动化工作流设计。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: NetForge Studio
agent_created: true
trigger_words: ["catalyst9k network automation", "网络自动化", "交换机脚本", "Catalyst配置生成", "网络脚本编排", "交换机批量配置", "网络设备自动化"]
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# Catalyst9K 网络自动化脚本生成 Skill

## 一、能力边界（速查卡）

### 1.1 能做什么

| 能力项 | 说明 | 输出形式 |
|--------|------|----------|
| 配置需求解析 | 将自然语言或结构化描述的网络需求解析为配置要素 | 结构化中间表示（JSON/YAML） |
| 脚本生成 | 基于解析结果生成 Catalyst 9K 系列交换机可执行脚本 | Python + Netmiko / Ansible Playbook / CLI 命令序列 |
| 工作流设计辅助 | 提供自动化任务的编排建议（如备份、推送、校验） | 流程图描述 + 步骤清单 |
| 批量执行支持 | 支持多设备、多配置段的批量脚本生成 | 按设备分组的脚本文件 |
| 配置校验 | 生成脚本内嵌校验逻辑（如 `show` 命令回读比对） | 校验代码片段 |

### 1.2 不能做什么

| 限制项 | 说明 |
|--------|------|
| 不执行真实设备操作 | 本 Skill 仅生成脚本，不直接连接设备下发配置 |
| 不保证配置正确性 | 生成的脚本需在测试环境验证后方可投入生产 |
| 不处理非 Catalyst 平台 | 仅面向 Catalyst 9K 系列（如 9200/9300/9500） |
| 不替代人工设计 | 复杂网络架构（如 VXLAN/EVPN 多租户）仍需网络工程师决策 |

### 1.3 适用对象

- 网络运维工程师（需具备基础 CLI 操作经验）
- 自动化平台集成开发人员
- 网络方案验证测试人员

---

## 二、触发方式

### 2.1 触发词

| 触发词 | 场景示例 |
|--------|----------|
| catalyst9k network automation | "帮我生成 Catalyst 9300 的端口配置脚本" |
| 网络自动化 | "这个网络自动化任务怎么设计？" |
| 交换机脚本 | "写个批量改 VLAN 的脚本" |
| Catalyst配置生成 | "生成 Catalyst 9500 的 NTP 配置" |
| 网络脚本编排 | "帮我编排一个配置备份+推送的流程" |
| 交换机批量配置 | "20 台交换机要统一加一个 ACL" |

### 2.2 大白话场景映射

| 用户说 | 实际需求 | 本 Skill 动作 |
|--------|----------|---------------|
| "帮我写个脚本，把这几台交换机接口都划到 VLAN 100" | 批量端口 VLAN 配置 | 生成 Netmiko 脚本 + 配置模板 |
| "我想自动化配置，但不知道从哪开始" | 自动化工作流设计 | 输出流程步骤 + 推荐工具链 |
| "这个配置任务能不能做成 Ansible 的？" | Ansible Playbook 生成 | 生成 Playbook YAML + 变量文件 |
| "配置完怎么确认生效了？" | 配置校验逻辑 | 生成回读比对代码 |

---

## 三、标准流程

### 3.1 前置条件

| 条件 | 要求 | 检查方式 |
|------|------|----------|
| 输入文件 | 待处理文件与 Skill 工作目录一致，命名含设备标识 | `ls` 确认 |
| 设备清单 | 明确 IP/主机名、账号权限、设备型号 | 核对 inventory 文件 |
| 配置模板 | 有基线配置或需求描述文档 | 人工确认 |
| 环境依赖 | Python 3.8+ / Ansible 2.9+ / Netmiko 已安装 | `pip list` 或 `ansible --version` |

### 3.2 执行步骤

1. **需求解析**：将用户提供的配置需求（文本/表格/现有配置片段）解析为结构化字段。
   - 输入示例：`"接口 Gi1/0/1-24 划入 VLAN 200，端口模式 access"`
   - 解析结果：
     ```json
     {
       "interfaces": ["Gi1/0/1", "Gi1/0/2", "..."],
       "vlan": 200,
       "mode": "access"
     }
     ```

2. **脚本生成**：根据解析结果选择脚本类型（CLI 序列 / Python / Ansible），生成对应文件。
   - 生成文件命名规范：`{设备名}_{任务名}_{日期}.{ext}`

3. **试运行**：使用单个样本设备执行生成的脚本，核对输出字段与格式。
   - 检查点：命令是否被设备接受、回显是否正常、有无报错

4. **批量执行**：确认无误后对全量设备执行，执行前备份原始配置。
   - 备份命令示例：`show running-config > {设备名}_backup_{日期}.txt`

5. **结果校验**：抽查输出条目，核对关键字段（VLAN、接口状态、ACL 序号）与源数据一致。
   - 校验脚本自动比对预期值与实际回显

### 3.3 输出规范

| 输出项 | 格式 | 说明 |
|--------|------|------|
| 脚本文件 | `.py` / `.yaml` / `.txt` | 可直接执行的脚本或命令序列 |
| 执行报告 | `.md` / `.csv` | 记录每台设备的执行状态、耗时、异常 |
| 校验报告 | `.md` | 比对结果，标注差异项 |
| 备份文件 | `.txt` | 执行前设备配置快照 |

---

## 四、置信度门控

当输入信息不足以生成可靠脚本时，使用 `[需核实:字段]` 占位，不编造默认值。

| 场景 | 占位示例 | 处理方式 |
|------|----------|----------|
| 未指定 VLAN ID | `vlan [需核实:vlan_id]` | 提示用户补充，不假设默认值 |
| 未指定接口范围 | `interface [需核实:interface_range]` | 询问具体接口列表 |
| 未指定认证方式 | `auth [需核实:auth_method]` | 提示选择 SSH 密码或密钥 |
| 未指定设备型号 | `platform [需核实:device_model]` | 确认是否为 Catalyst 9K 系列 |

---

## 五、错误码体系

| 错误码 | 错误描述 | 提示话术 | 修正步骤 |
|--------|----------|----------|----------|
| E001 | 输入文件不存在 | "未找到指定的输入文件，请确认路径与文件名" | 检查文件路径，确认文件已放入工作目录 |
| E002 | 设备清单格式错误 | "设备清单缺少必要字段（IP/用户名）" | 按模板补齐字段，重新提交 |
| E003 | 配置模板解析失败 | "配置模板存在无法识别的语法" | 检查模板中的命令拼写与缩进 |
| E004 | 脚本生成超时 | "脚本生成耗时过长，请简化需求描述" | 拆分任务，分步生成 |
| E005 | 校验比对不一致 | "回读配置与预期配置存在差异，请人工确认" | 查看差异报告，定位差异项并修正 |
| E006 | 设备连接失败 | "无法连接目标设备，请检查网络与凭据" | 确认设备可达性，核对账号权限 |

---

## 六、FAQ 反模式

### 6.1 常见坑

| 坑 | 反模式示例 | 正确做法 |
|----|------------|----------|
| 跳过试运行 | "直接批量跑吧，应该没问题" | 先单台试运行，确认输出无误再批量 |
| 忽略备份 | "配置错了再改回来就行" | 执行前必须备份原始配置，保留回滚路径 |
| 硬编码凭据 | 脚本中明文写入密码 | 使用环境变量或 Ansible Vault 管理凭据 |
| 忽略校验 | "命令执行成功就算完成了" | 必须回读配置，比对关键字段 |
| 覆盖源文件 | 直接修改原始配置文件 | 生成新文件，保留原始文件备份 |

### 6.2 反模式对照表

| 反模式 | 问题 | 替代方案 |
|--------|------|----------|
| 一次生成所有设备的脚本 | 单台失败影响全量 | 按设备分组生成，独立执行 |
| 使用 `enable` 后不退出 | 遗留特权模式会话 | 脚本末尾统一 `exit` |
| 忽略 `show` 命令超时 | 设备响应慢导致脚本中断 | 设置合理超时（如 30s）并重试 |

---

## 七、渐进式披露

### 7.1 速查卡（新手必读）

1. 准备输入文件 → 2. 单样本试运行 → 3. 批量执行 → 4. 校验结果
2. 所有脚本生成前先备份设备配置
3. 不确定的参数用 `[需核实:字段]` 标记，不猜默认值
4. 执行后必须回读配置确认

### 7.2 分层次阅读路径

| 读者 | 建议阅读章节 | 目标 |
|------|--------------|------|
| 新手（首次使用） | 能力边界 → 标准流程 → FAQ | 能独立完成一次简单配置任务 |
| 进阶（有自动化经验） | 置信度门控 → 错误码体系 → 输出规范 | 能处理复杂任务与异常场景 |
| 专家（设计工作流） | 全部章节 + 自定义扩展 | 能设计完整自动化流水线 |

---

## 八、用户协议

<!-- user-agreement-injected -->

**使用本 Skill 即表示您同意以下条款：**

1. **责任承担**：使用者自行承担全部责任。本 Skill 生成的脚本、配置及建议仅供参考，使用者须在测试环境充分验证后，方可应用于生产环境。因使用本 Skill 产生的任何直接或间接损失，Skill 作者及发布者不承担任何责任。
2. **禁止反向工程**：禁止对本 Skill 的提示词、生成逻辑、内部结构进行反向工程、破解、提取或二次分发。
3. **合规使用**：使用者须遵守所在组织及所在地的法律法规，确保自动化操作已获得相应授权。
4. **无担保**：本 Skill 按"现状"提供，不附带任何明示或暗示的担保，包括但不限于适销性、特定用途适用性及非侵权保证。

---

## 九、许可证（License）

<!-- professional-license-embedded -->

**MIT License**

Copyright (c) 2024 NetForge Studio

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

*本 Skill 由 AI 辅助生成，仅供参考。使用前请阅读相关文档并充分测试。*
