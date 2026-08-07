---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: security-skill-router
name: security-skill-router
displayName: 安全任务路由 工具链匹配 流程编排
description: 按安全任务类型自动匹配工具链与技能包，生成操作流程与知识引用。
version: 1.1.3
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/security-skill-router
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: skill-forge-studio
agent_created: true
trigger_words: ["安全审计", "安全分析", "安全测试", "漏洞评估", "渗透测试", "安全巡检", "风险排查"]
---

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# 安全任务路由与工具链编排 Skill

## 一、能力边界（一页纸速查卡）

### 1.1 能做什么

| 能力项 | 说明 | 适用场景示例 |
|--------|------|--------------|
| 任务类型识别 | 从用户输入中识别安全任务的具体类别（审计/分析/测试/评估/渗透） | "帮我看看这个系统有哪些漏洞" → 漏洞评估 |
| 工具链匹配 | 根据任务类型推荐对应的工具组合与技能包 | 渗透测试 → 信息收集+扫描+利用+报告工具链 |
| 流程编排 | 生成分步骤的操作流程，含前置条件、执行顺序、输出规范 | 安全审计 → 资产盘点→基线核查→日志分析→报告 |
| 知识引用 | 关联相关的安全知识库条目、CVE 编号、最佳实践文档 | 漏洞评估时引用 OWASP Top 10 对应条目 |
| 参数配置建议 | 为推荐工具提供合理的参数初始值 | Nmap 扫描时建议 -sV -sC 组合 |

### 1.2 不能做什么

| 限制项 | 说明 |
|--------|------|
| 不执行实际扫描/攻击 | 本 Skill 仅生成流程与建议，不直接调用安全工具 |
| 不提供漏洞利用代码 | 仅提供检测思路与验证方法，不生成 exploit |
| 不替代专业判断 | 最终安全决策需由持证专业人员确认 |
| 不保证发现所有漏洞 | 安全检测存在盲区，结果仅供参考 |
| 不处理授权范围外目标 | 未获得书面授权的测试目标不在服务范围内 |

### 1.3 适用对象

- 安全运维工程师：日常巡检、基线核查、日志审计
- 渗透测试人员：授权范围内的渗透测试流程规划
- 安全开发人员：SDLC 中的安全测试环节
- 安全管理者：了解团队工作流程与工具链构成

## 二、触发方式

### 2.1 触发词映射表

| 用户说（大白话） | 触发词 | 任务类型 | 路由结果 |
|------------------|--------|----------|----------|
| "帮我检查一下服务器安全配置" | 安全审计 | 配置审计 | 基线核查工具链 |
| "分析一下这个流量包有什么异常" | 安全分析 | 流量分析 | Wireshark + tshark 流程 |
| "测测这个 Web 应用有没有 SQL 注入" | 安全测试 | 应用测试 | SQLMap + Burp Suite 流程 |
| "这个系统最近有没有被入侵的痕迹" | 漏洞评估 | 入侵排查 | 日志分析 + 文件完整性检查 |
| "模拟黑客攻击一下我们的测试环境" | 渗透测试 | 授权渗透 | 完整渗透测试工具链 |
| "帮我看下这个 API 接口安不安全" | 安全测试 | 接口测试 | Postman + OWASP ZAP 流程 |
| "新上线的服务需要过一遍安全流程" | 安全审计 | 上线前检查 | 综合审计工具链 |

### 2.2 命令行接口

```
安全审计 [目标] [范围] [深度]
安全分析 [文件/流量包路径] [分析维度]
安全测试 [目标URL/接口] [测试类型]
漏洞评估 [目标IP/域名] [评估标准]
渗透测试 [目标范围] [授权编号]
--selftest     # 自检模式，验证 Skill 配置完整性
--version      # 显示版本信息
```

## 三、标准流程

### 3.1 前置条件

| 条件 | 要求 | 检查方式 |
|------|------|----------|
| 目标授权 | 书面授权文件或测试许可 | 确认授权编号/合同编号 |
| 目标信息 | IP/域名/URL/文件路径 | 输入参数校验 |
| 环境准备 | 工具已安装、网络可达 | 环境自检脚本 |
| 范围确认 | 明确测试边界与禁止项 | 与用户确认范围声明 |

### 3.2 执行步骤

#### 步骤 1：任务解析（输入规范化）

```
输入示例："对 192.168.1.0/24 网段做一次漏洞扫描"
解析结果：
  - 任务类型：漏洞评估
  - 目标范围：192.168.1.0/24
  - 深度要求：标准（未指定则默认标准）
  - 特殊要求：无
```

#### 步骤 2：工具链匹配

| 任务类型 | 推荐工具链 | 优先级 | 备选方案 |
|----------|------------|--------|----------|
| 安全审计 | OpenSCAP + Lynis + auditd | P1 | CIS-CAT + osquery |
| 安全分析 | Wireshark + tshark + Zeek | P1 | Suricata + Moloch |
| 安全测试 | Burp Suite + SQLMap + OWASP ZAP | P1 | Nikto + w3af |
| 漏洞评估 | Nmap + OpenVAS + Nessus | P1 | Masscan + Vulners |
| 渗透测试 | Metasploit + Cobalt Strike + Empire | P1 | 手工验证 + 自定义脚本 |

#### 步骤 3：流程生成

以"漏洞评估"为例：

```
阶段 1：资产发现
  命令：nmap -sP 192.168.1.0/24
  输出：存活主机列表

阶段 2：端口与服务识别
  命令：nmap -sV -sC -O -p- 192.168.1.1
  输出：服务版本、操作系统指纹

阶段 3：漏洞扫描
  命令：openvas-scan --target 192.168.1.1 --port-list "1-65535"
  输出：漏洞列表（含 CVE 编号、CVSS 评分）

阶段 4：验证与复现
  方法：根据漏洞类型选择验证方式
  输出：验证结果记录

阶段 5：报告生成
  内容：执行摘要、漏洞详情、修复建议、风险等级
  输出：PDF/HTML 报告
```

#### 步骤 4：知识引用

| 任务类型 | 引用知识库 | 示例条目 |
|----------|------------|----------|
| 安全审计 | CIS Benchmarks | CIS Ubuntu 20.04 Benchmark v2.0 |
| 安全分析 | MITRE ATT&CK | T1046 网络服务扫描 |
| 安全测试 | OWASP Top 10 | A03:2021-Injection |
| 漏洞评估 | NVD/CVE | CVE-2023-1234 详情 |
| 渗透测试 | PTES 标准 | PTES 技术指南 |

### 3.3 输出规范

```
输出结构：
1. 任务摘要（类型、目标、时间、工具链）
2. 执行流程（步骤、命令、参数、预期输出）
3. 发现结果（按严重程度排序，含证据）
4. 修复建议（分优先级，含具体操作）
5. 附录（原始数据、工具版本、参考链接）
```

## 四、置信度门控

### 4.1 信息不足处理

当输入信息不足以生成可靠流程时，使用 `[需核实:字段]` 占位，不编造内容。

| 缺失字段 | 占位示例 | 补充方式 |
|----------|----------|----------|
| 目标范围 | `[需核实:目标IP/域名]` | 询问用户提供具体目标 |
| 授权信息 | `[需核实:授权编号]` | 要求用户提供授权证明 |
| 任务类型 | `[需核实:任务类型]` | 根据用户描述重新识别 |
| 环境信息 | `[需核实:操作系统/网络环境]` | 建议用户先做环境探测 |
| 时间窗口 | `[需核实:测试时间窗口]` | 确认可执行时间范围 |

### 4.2 置信度分级

| 置信度 | 条件 | 输出策略 |
|--------|------|----------|
| 高（≥90%） | 目标明确、授权清晰、环境已知 | 直接生成完整流程 |
| 中（70-89%） | 部分信息缺失但可推断 | 生成流程并标注假设条件 |
| 低（<70%） | 关键信息缺失或矛盾 | 先引导用户补充信息，再生成 |

## 五、错误码体系

| 错误码 | 错误描述 | 提示话术 | 修正步骤 |
|--------|----------|----------|----------|
| ERR-001 | 目标未授权 | "未检测到该目标的授权信息，请提供书面授权文件或授权编号" | 1. 获取授权 2. 重新输入 3. 确认授权范围 |
| ERR-002 | 目标格式错误 | "目标格式无法识别，请使用 IP、域名、URL 或文件路径格式" | 1. 检查输入格式 2. 参考示例 3. 重新输入 |
| ERR-003 | 工具链不完整 | "推荐工具链中缺少必要组件：{工具名}" | 1. 安装缺失工具 2. 验证安装 3. 重新执行 |
| ERR-004 | 网络不可达 | "无法连接到目标网络，请检查网络连通性" | 1. ping 测试 2. 检查防火墙 3. 确认路由 |
| ERR-005 | 任务类型冲突 | "输入信息同时匹配多种任务类型，请明确优先级" | 1. 列出匹配类型 2. 请用户选择 3. 按选择执行 |
| ERR-006 | 参数越界 | "参数值超出允许范围：{参数名}={值}" | 1. 查看参数限制 2. 调整参数 3. 重新执行 |
| ERR-007 | 时间窗口冲突 | "当前时间不在允许的测试窗口内" | 1. 确认时间窗口 2. 调整计划 3. 重新调度 |
| ERR-008 | 输出目录不可写 | "无法写入输出目录：{路径}" | 1. 检查权限 2. 更换目录 3. 重新执行 |

## 六、FAQ 反模式

### 6.1 常见坑与反模式对照

| 坑 | 反模式示例 | 正确做法 |
|----|------------|----------|
| 忽略授权 | "直接扫吧，反正都是内网" | 必须先确认授权，无授权不执行 |
| 范围蔓延 | "顺便把隔壁网段也扫一下" | 严格限定在授权范围内，超范围需重新授权 |
| 工具滥用 | "用 Metasploit 把所有 exploit 都跑一遍" | 根据目标特征选择合适工具与参数 |
| 忽略验证 | "扫描结果就是最终结论" | 高危漏洞必须人工验证，避免误报 |
| 报告模糊 | "发现了一些问题，建议修复" | 报告需包含具体证据、影响分析、修复步骤 |
| 依赖单一工具 | "Nmap 扫过没发现就安全了" | 多工具交叉验证，结合人工分析 |

### 6.2 反模式自查清单

- [ ] 是否已确认测试授权？
- [ ] 是否明确测试边界？
- [ ] 是否选择了合适的工具链？
- [ ] 是否对结果进行了人工验证？
- [ ] 报告是否包含可操作的修复建议？

## 七、渐进式披露

### 7.1 速查卡（30 秒上手）

```
1. 告诉我要做什么（审计/分析/测试/评估/渗透）
2. 提供目标信息（IP/域名/URL/文件）
3. 确认授权与范围
4. 获取工具链建议与执行流程
5. 按流程执行并生成报告
```

### 7.2 新手路径（首次使用）

1. 阅读"能力边界"了解适用范围
2. 使用"触发方式"中的示例输入尝试
3. 按照"标准流程"逐步执行
4. 遇到问题参考"错误码体系"
5. 完成后查看"FAQ 反模式"避免常见错误

### 7.3 进阶路径（熟练用户）

1. 自定义工具链配置（修改推荐工具组合）
2. 编写自定义流程模板
3. 集成到 CI/CD 流水线
4. 结合威胁情报平台丰富知识引用
5. 建立团队内部的最佳实践库

### 7.4 参数参考表

| 参数 | 类型 | 默认值 | 取值范围 | 说明 |
|------|------|--------|----------|------|
| depth | string | standard | quick/standard/deep | 扫描深度 |
| timeout | int | 3600 | 60-86400 | 超时时间（秒） |
| concurrency | int | 10 | 1-100 | 并发数 |
| output_format | string | html | html/pdf/json/md | 报告格式 |
| verbose | bool | false | true/false | 详细输出 |

## 八、用户协议

<!-- user-agreement-injected -->

**使用本 Skill 即表示您同意以下条款：**

1. **责任承担**：使用者自行承担因使用本 Skill 产生的全部责任。本 Skill 提供的所有建议、流程、工具链推荐仅供参考，不构成任何形式的安全保证或承诺。

2. **合法使用**：使用者必须确保所有操作均在合法授权范围内进行。未经授权的安全测试、扫描、渗透行为可能违反法律法规，使用者需自行承担相应法律后果。

3. **禁止反向工程**：使用者不得对本 Skill 进行反向工程、反编译、反汇编，不得尝试提取源代码、算法或底层实现。

4. **无担保声明**：本 Skill 按"现状"提供，不附带任何明示或暗示的担保，包括但不限于适销性、特定用途适用性和非侵权保证。

5. **免责范围**：因使用本 Skill 导致的任何直接、间接、偶然、特殊或后果性损害，Skill 作者及贡献者不承担任何责任。

6. **协议更新**：本协议可能随时更新，更新后的版本将在本 Skill 文档中发布。继续使用本 Skill 即视为接受更新后的协议。

## 九、许可证（License）

<!-- professional-license-embedded -->

**MIT License**

Copyright (c) 2024 skill-forge-studio

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
