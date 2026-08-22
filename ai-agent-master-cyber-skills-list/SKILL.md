---
slug: ai-agent-master-cyber-skills-list
name: ai-agent-master-cyber-skills-list
displayName: 安全编排 渗透取证 云上响应
description: 编排741项安全技能，覆盖渗透、云安全与数字取证场景。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: SkillForge Lab
agent_created: true
trigger_words: ["cyber skills","网络安全技能","渗透测试","安全编排","攻防演练","云安全事件响应","数字取证","应急响应"]
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# 安全编排 渗透取证 云上响应（SKILL.md）

## 1. 能力边界速查卡（一页纸）

本 Skill 是一个**流程编排与知识调度中枢**，它不直接执行攻击或扫描动作，而是将你给出的安全任务拆解为可操作的步骤序列，并调度底层工具链完成工作。

| 维度 | 能做 | 不能做 |
|------|------|--------|
| 渗透测试 | 编排标准渗透流程（信息收集→漏洞探测→利用验证→报告），支持 DVWA、Metasploitable 等授权靶机 | 不发起真实网络攻击，不扫描未授权目标 |
| 云安全 | 编排 CloudTrail 日志分析、异常登录检测、API 调用审计、快照创建指令 | 不直接修改云资源，不删除或篡改日志 |
| 数字取证 | 编排 Volatility 内存镜像分析流程（进程、网络连接、注入检测） | 不执行数据恢复或磁盘镜像制作（需外部工具） |
| 攻防演练 | 组合上述场景形成演练剧本，输出时间线关联图 | 不模拟真实 APT 攻击载荷 |
| 报告输出 | 生成 JSON 格式漏洞列表、事件响应报告、CI/CD 集成脚本 | 不自动修复漏洞，不发送通知消息 |

**适用对象**：安全运维工程师、蓝队分析人员、DevSecOps 从业者、渗透测试学习者（需具备基础网络与 Linux 知识）。

---

## 2. 触发方式与场景映射

在对话中输入以下任一触发词即可激活本 Skill。若描述模糊，系统会先通过追问澄清需求。

| 触发词/短语 | 大白话场景 | 系统行为 |
|-------------|-----------|----------|
| "渗透测试" | "帮我测一下这个靶机有什么漏洞" | 启动标准渗透流程编排 |
| "云安全事件响应" | "我怀疑 AWS 账号被入侵了" | 启动 CloudTrail 分析流程 |
| "数字取证" | "帮我看看这个内存镜像里有什么" | 启动 Volatility 分析流程 |
| "攻防演练" | "想模拟一次红蓝对抗" | 组合渗透+取证流程 |
| "应急响应" | "服务器好像被种了木马" | 启动事件响应全流程 |
| "安全编排" | "把这几步串起来自动跑" | 进入自定义编排模式 |

**补充触发词**：`安全运营`、`入侵分析`、`日志审计`、`漏洞评估`。

---

## 3. 标准执行流程

### 3.1 前置条件（必须全部满足）

| 条件 | 说明 | 验证方法 |
|------|------|----------|
| 授权确认 | 目标系统归属你或你已获得书面授权 | 口头确认 + 记录授权范围 |
| 靶机可达 | DVWA/Metasploitable 等靶机网络可通 | `ping <靶机IP>` |
| 工具链就绪 | Volatility、nmap、sqlmap 等已安装 | `which volatility nmap sqlmap` |
| 云凭证配置 | AWS 只读凭证已配置（若涉及云场景） | `aws sts get-caller-identity` |
| 参数初始化 | 已阅读附录 A 并设置扫描速率、字典路径 | 检查 `~/.cyber-skills/config.yaml` |

### 3.2 执行步骤（以渗透测试为例）

```bash
# Step 1: 环境自检
cyber-skills --selftest

# Step 2: 信息收集（速率限制 500 pps）
nmap -sV -p- --min-rate 500 <靶机IP> -oN recon.txt

# Step 3: 漏洞探测（使用自定义字典）
sqlmap -u "http://<靶机IP>/dvwa/vulnerabilities/sqli/?id=1" --batch --dictionary=./dict/custom.txt

# Step 4: 利用验证（仅限授权靶机）
# 手动执行或调用 metasploit 模块

# Step 5: 输出 JSON 报告
cyber-skills report --format json --output vulns.json
```

### 3.3 输出规范

所有流程结束后，系统生成结构化输出：

- **渗透测试**：`vulns.json`（含漏洞名称、CVSS 评分、复现步骤、修复建议）
- **云安全**：`cloudtrail_analysis.json`（异常事件列表 + 时间线）
- **取证**：`volatility_results.json`（进程列表、网络连接、可疑注入）
- **综合报告**：`incident_response.md`（含置信度标注）

---

## 4. 置信度门控机制

当分析结果存在不确定性时，**严禁编造数据**。系统按以下规则处理：

| 置信度等级 | 判定标准 | 输出方式 |
|-----------|---------|---------|
| 高（≥90%） | 多源日志交叉验证一致 | 正常输出 |
| 中（70-89%） | 单一来源或存在时间偏差 | 标注 `[需核实:字段]` |
| 低（<70%） | 推断成分较多 | 输出 `[需核实:字段]` 并附推断依据 |

**示例**：
```json
{
  "event": "AnomalousLogin",
  "source_ip": "[需核实:IP归属地]",
  "confidence": 0.65,
  "reason": "IP 未在威胁情报库中匹配到历史记录"
}
```

---

## 5. 错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|---------|---------|
| E001 | 目标未授权 | "目标未在授权清单中，请确认授权范围" | 添加授权记录或更换目标 |
| E002 | 工具缺失 | "未找到 Volatility，请安装后重试" | `pip install volatility3` |
| E003 | 云凭证无效 | "AWS 凭证无效或无只读权限" | 检查 `~/.aws/credentials` |
| E004 | 参数越界 | "扫描速率超出安全阈值（1000pps）" | 调整 `--min-rate` 至 500 以下 |
| E005 | 输出目录不可写 | "无法写入报告，请检查目录权限" | `chmod +w ./reports` |
| E006 | 靶机不可达 | "目标主机无响应，请检查网络" | `ping` 测试 + 检查防火墙规则 |

---

## 6. FAQ 反模式对照

| 常见坑 | 反模式（错误做法） | 正模式（推荐做法） |
|--------|-------------------|-------------------|
| 跳过信息收集直接扫描 | 直接运行 `sqlmap` 而不先做端口扫描 | 严格按流程：先 `nmap` 再 `sqlmap` |
| 忽略置信度标注 | 将低置信度结果直接写入报告 | 保留 `[需核实:字段]` 标记 |
| 未确认授权就行动 | 对公网 IP 直接发起扫描 | 先确认目标归属与授权文件 |
| 参数一刀切 | 所有场景都用默认扫描速率 | 根据目标重要性调整速率（内网可快，外网调慢） |
| 报告无时间线 | 只输出漏洞列表不关联时间 | 生成 `timeline.md` 关联各阶段事件 |

---

## 7. 渐进式阅读路径

### 新手路径（首次使用）
1. 阅读第 1 节「能力边界速查卡」确认适用性
2. 运行 `cyber-skills --selftest` 验证环境
3. 从渗透测试场景开始，使用 DVWA 靶机
4. 严格按第 3 节标准流程执行，不跳步
5. 遇到不确定信息使用 `[需核实:字段]`

### 进阶路径（熟练用户）
1. 组合多个场景（如"云安全 + 数字取证"）
2. 自定义参数：调整扫描速率、自定义字典、定制报告模板
3. 将输出集成到 CI/CD 安全门禁（参考附录 B）
4. 研究置信度门控机制，优化数据准确性

---

## 附录 A：参数配置表

| 参数名 | 默认值 | 说明 | 建议范围 |
|--------|--------|------|---------|
| `scan_rate` | 500 pps | 扫描速率 | 100-1000 pps |
| `dict_path` | `./dict/default.txt` | 字典路径 | 自定义字典需 UTF-8 编码 |
| `output_format` | `json` | 报告格式 | json / md / html |
| `confidence_threshold` | 0.7 | 置信度阈值 | 0.5-0.9 |
| `timeout` | 30s | 单次请求超时 | 10-60s |

---

## 附录 B：CI/CD 集成示例（Jenkins Pipeline）

```groovy
pipeline {
    agent any
    stages {
        stage('Security Scan') {
            steps {
                sh 'cyber-skills run --scenario pentest --target $TARGET'
            }
        }
        stage('Gate Check') {
            steps {
                sh '''
                    python3 -c "
                    import json
                    with open('vulns.json') as f:
                        data = json.load(f)
                    critical = [v for v in data if v['cvss'] >= 9.0]
                    if critical:
                        print('BLOCK: Critical vulnerabilities found')
                        exit(1)
                    "
                '''
            }
        }
    }
}
```

---

## 用户协议

<!-- user-agreement-injected -->

**使用本 Skill 即表示您同意以下条款：**

1. **责任承担**：使用者自行承担因使用本 Skill 产生的全部责任。本 Skill 仅提供流程编排与知识调度功能，不执行任何实际测试行为。任何实际的安全测试行为均需由使用者自行执行，并确保已获得目标系统的合法授权。

2. **禁止反向工程**：使用者不得对本 Skill 的底层逻辑进行反向工程、反编译、破解或试图提取源代码（除非适用法律允许）。本 Skill 的编排逻辑、置信度算法及错误码体系均为受保护的知识产权。

3. **合规使用**：使用者须确保所有操作符合当地法律法规及目标组织的安全政策。本 Skill 不鼓励、不纵容任何非法访问行为。对于未授权测试导致的任何法律后果，本 Skill 作者不承担任何责任。

4. **无担保**：本 Skill 按"原样"提供，不附带任何明示或暗示的担保，包括但不限于适销性、特定用途适用性及不侵权保证。使用者应自行验证输出结果的准确性。

---

## 许可证（License）

<!-- professional-license-embedded -->

**MIT License**

Copyright (c) 2024 SkillForge Lab

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

*本 Skill 由 AI 辅助生成，仅供参考。使用前请阅读相关文档并确认环境配置。*
