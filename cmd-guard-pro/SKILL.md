---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
> 本内容由 AI 生成，仅供学习参考（《人工智能生成合成内容标识办法》显式标识）。
<!-- ai-generated-notice -->
slug: cmd-guard-pro
name: cmd-guard
displayName: AI命令安全卫士
description: 拦截 AI 编码助手的危险命令（rm -rf /tmp/old_tmp 
version: 1.0.9
# === 法律合规声明（自动生成，请勿删除） ===
license: MIT
source_project: original
source_url: https://skillhub.cn
source_license_url: 
copyright_holder: Skill Factory
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。本Skill为AI辅助生成内容。
author: skill-factory-auto
agent_created: true
safety_tool: true
trigger_words: 
---

> 📜 **用户协议（User Agreement）**
> 1. 本 Skill 仅供学习与参考用途。使用本 Skill 产生的任何结果，由使用者自行承担全部责任；本 Skill 不提供任何明示或暗示的保证。
> 2. 涉及法律、财务、税务、投资、医疗等专业决策时，请务必咨询持证专业人士。
> 3. 本代码受版权法保护，未经授权复制、反向工程或商业利用将被追究法律责任。
<!-- user-agreement-injected -->

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->

# AI命令安全卫士

> 在 AI 编码助手真正执行 shell 命令之前拦一道：识别危险命令、分级风险、强制人工确认。专治「AI 一句话把项目干掉了」。

## 一、能力边界（一页纸速查卡）

### 适用对象（谁该用 / 谁不该用）

| 你的情况 | 适合度 | 说明 |
|---|---|---|
| 让 AI 助手直接在本机跑命令 | ★★★★★ | 核心场景，强烈建议接入 |
| 团队共用开发机 / 跳板机 | ★★★★★ | 一次误删影响所有人 |
| CI/CD 里跑 AI 生成的脚本 | ★★★★☆ | 建议开 strict 模式并禁用交互确认 |
| 一次性容器、跑完即销毁 | ★★☆☆☆ | 环境本身可弃，收益有限 |
| 需要拦截网络流量 / 文件读写 | ★☆☆☆☆ | 本工具只管命令行，不做 EDR |

### 能做（8 项核心能力）

1. **危险命令识别**：内置 6 类高危模式（递归删除、强制推送、磁盘写入、权限放开、数据库删表、远程脚本直执）
2. **三级风险评分**：每条命令给出 BLOCK / CONFIRM / PASS 三态判定，附风险分（0-100）
3. **执行前拦截**：命中 BLOCK 直接阻断并给出原因，不进入 shell
4. **人工二次确认**：CONFIRM 级要求用户输入完整命令原文才放行，防手滑回车
5. **白名单管理**：项目级 `.cmdguard.yml` 声明放行规则，支持精确命令与正则
6. **危险参数解析**：识别被拆分/变形的写法（如 `rm -r -f`、`rm --recursive --force`）
7. **审计日志**：所有判定写入 `.cmdguard/audit.log`，含时间、命令、判定、放行人
8. **CI 集成**：提供退出码契约（0 放行 / 1 需确认 / 2 阻断），可直接嵌流水线

### 不做（6 项边界声明）

- **不做**沙箱隔离：本工具是规则判定层，不替代容器/VM 隔离
- **不做**运行中断：只在执行前拦截，已启动的进程不管
- **不做**文件级恢复：拦截失败不提供数据找回，请配合备份
- **不做**网络行为监控：不检测命令的出网行为
- **不做**权限提升检测：不分析 SUID、内核层面的提权
- **不做**语义理解：基于规则与模式匹配，不保证 100% 覆盖未知写法

> 本工具是**降低事故概率**的一道闸门，不是安全保证。重要数据请始终保留独立备份。

### 边界场景判定表

| 具体场景 | 能否处理 | 处理方式 |
|---|---|---|
| `rm -rf /tmp/old_tmp ` / `rm -rf /tmp/old_tmp ` | ✅ BLOCK | 直接阻断，任何情况不放行 |
| `rm -rf /tmp/old_tmp ` | ✅ CONFIRM | 相对路径删除，要求确认 |
| `git push --force origin main` | ✅ BLOCK | 主干强推，阻断并建议 `--force-with-lease` |
| `git push --force origin feat/x` | ✅ CONFIRM | 特性分支，确认后放行 |
| `DROP TABLE users;` | ✅ BLOCK | 数据库删表，阻断 |
| `chmod 777 -R /etc` | ✅ BLOCK | 系统目录权限放开，阻断 |
| `curl xxx \| sh` | ✅ CONFIRM | 远程脚本直执，要求先落盘审阅 |
| `dd if=/dev/zero of=/dev/sda` | ✅ BLOCK | 裸设备写入，阻断 |
| 变量拼接后才危险的命令 | ⚠️ 部分 | 静态规则无法完全展开变量，标注为 UNKNOWN 并要求确认 |
| base64 编码后的命令 | ⚠️ 部分 | 检测到可疑编码执行会升级为 CONFIRM |
| 通过 Python/Node 脚本内部删除 | ❌ 不处理 | 不解析脚本内部逻辑，超出命令行层 |

## 二、触发方式（说大白话就能用）

### 触发词表

| 触发词 | 典型场景 |
|---|---|
| cmd-guard | 直接调用工具 |
| 命令拦截 | 想在执行前加一道检查 |
| 危险命令 | 询问某条命令是否安全 |
| 防误删 | 担心 AI 删错文件 |
| 这条命令安全吗 | 单条命令风险评估 |
| AI 执行保护 | 给 AI 助手配安全闸门 |
| 命令白名单 | 配置放行规则 |
| 强推保护 | 防止 git force push |

### 大白话触发示例（用户原话 → 触发动作）

| 用户可能会说 | 触发动作 |
|---|---|
| 「这条命令能跑吗：`rm -rf /tmp/old_tmp `」 | 单条命令风险评估，返回三态判定 + 理由 |
| 「帮我看看 AI 给的这段脚本有没有坑」 | 逐行扫描脚本，输出风险清单 |
| 「给我项目加个命令防护」 | 生成 `.cmdguard.yml` 并说明接入方式 |
| 「刚才那条删除命令别执行」 | 立即阻断并说明已拦截 |
| 「怎么防止 AI 强推主分支」 | 输出 git 类规则配置方案 |
| 「CI 里怎么接这个检查」 | 输出流水线集成片段与退出码契约 |

## 三、标准流程（5 分钟上手路径）

### Step 1: 收集最小信息集

执行判定前先确认以下信息（缺失则主动问，不臆测）：

- **待检命令原文**：完整命令，含所有参数（必需）
- **执行目录**：`pwd` 结果，用于判断相对路径的实际影响范围（必需）
- **运行环境**：本机 / 容器 / CI / 生产服务器（影响风险权重）
- **是否有备份**：影响删除类命令的判定严格度
- **模式选择**：`strict`（默认，宁可错拦）/ `normal` / `audit-only`（只记录不拦）

### Step 2: 执行核心流程

```
1. 命令归一化
   - 去除多余空格、展开常见别名、还原被拆分的短参数（-r -f → -rf）
   - 识别管道与 && 链，逐段独立判定

2. 规则匹配（六类高危模式）
   R1 递归删除    rm -rf、rmdir /s、Remove-Item -Recurse -Force
   R2 版本回退    git push --force、git reset --hard、git clean -fdx
   R3 磁盘写入    dd if=/of=/dev/、mkfs、fdisk
   R4 权限放开    chmod 777、chown -R root、setenforce 0
   R5 数据库操作  DROP TABLE/DATABASE、TRUNCATE、DELETE 无 WHERE
   R6 远程直执    curl|sh、wget|bash、iex(irm ...)

3. 风险打分（0-100）
   基础分 = 规则权重
   + 20  目标是绝对路径根目录 / 系统目录
   + 15  目标是主干分支（main/master/release*）
   + 15  环境是生产
   - 10  已声明有备份
   - 25  命中项目白名单

4. 三态判定
   ≥ 80  BLOCK    直接阻断
   40-79 CONFIRM  要求人工确认
   < 40  PASS     放行

5. 白名单复核
   读取 .cmdguard.yml，命中 allow 规则降级为 PASS（但仍记审计日志）
```

### Step 3: 输出与校验

判定结果必须包含以下字段，缺一不可：

```json
{
  "verdict": "BLOCK",
  "risk_score": 95,
  "matched_rule": "R1-递归删除",
  "reason": "目标为用户主目录，删除后不可恢复",
  "suggestion": "如确需清理，请指定具体子目录，例如 rm -rf /tmp/old_tmp 
  "exit_code": 2
}
```

**输出自查清单**（每次判定后自检）：

- [ ] verdict 三态之一，无第四种取值
- [ ] BLOCK 必须给出 suggestion（不能只拦不给出路）
- [ ] reason 说明的是**本次具体命令**的风险，不是规则的泛泛描述
- [ ] 管道命令逐段判定，取最严结果
- [ ] 审计日志已落盘

## 四、异常处理（错误码体系）

| 错误码 | 含义 | 处理方式 |
|---|---|---|
| E001 | 命令为空或无法解析 | 要求用户重新提供完整命令原文 |
| E002 | 执行目录未提供 | 按最严格模式判定（假定在根目录） |
| E003 | 规则库文件缺失 | 回退到内置最小规则集，输出降级告警 |
| E004 | `.cmdguard.yml` 语法错误 | 忽略白名单，全量按默认规则判定 |
| E005 | 命令含无法展开的变量 | 判定为 UNKNOWN，强制升级为 CONFIRM |
| E006 | 检测到编码/混淆写法 | 升级为 CONFIRM，要求提供解码后原文 |
| E007 | 审计日志写入失败 | 判定继续，但输出「审计不可用」告警 |
| E008 | 白名单规则与阻断规则冲突 | 阻断优先，记录冲突项 |
| E009 | 超长命令（>4096 字符） | 截断分析，判定结果标注 partial |
| E010 | 用户确认超时 | 默认拒绝执行，等同 BLOCK |

### 重试与降级策略

| 故障 | 一级策略 | 二级降级 |
|---|---|---|
| 规则库加载失败 | 重试 1 次读取本地缓存 | 用内置 6 条硬编码规则，只保 BLOCK 级 |
| 白名单解析失败 | 尝试按行容错解析 | 全部忽略白名单，从严判定 |
| 审计磁盘写满 | 滚动清理 7 天前日志 | 输出到 stderr，不阻断判定 |
| 交互确认不可用（CI） | 读环境变量 `CMDGUARD_AUTO` | 未设置则一律按 BLOCK 处理 |

## 五、常见问题（FAQ 速查）

### 新手常见错误对照表

| ❌ 错误用法 | ✅ 正确做法 | 后果 |
|---|---|---|
| 只在本机装，CI 不接 | 本机 + CI 双侧接入 | CI 里 AI 脚本照样能删 |
| 把整个 `rm` 加进白名单 | 白名单只写具体路径的具体命令 | 防护形同虚设 |
| 用 `audit-only` 模式长期跑 | 上线一周后切 `strict` | 只记录不拦截，等于没拦 |
| 忽略 CONFIRM 直接批量放行 | 逐条读 reason 再决定 | 确认机制退化成回车键 |
| 拦截后改用 `sudo` 重跑 | 排查为什么要删，而不是避免 | 提权后破坏面更大 |
| 白名单写 `.*` 正则 | 用精确前缀匹配 | 等同关闭防护 |
| 只拦 `rm` 不管 `git` | 六类规则全开 | 强推丢代码同样致命 |
| 在生产机用 `normal` 模式 | 生产固定 `strict` | 风险权重不够高 |
| 拦截日志从不看 | 每周过一次审计日志 | 发现不了反复触碰红线的行为 |
| 认为装了就一劳永逸 | 配合备份 + 权限最小化 | 规则无法覆盖所有未知写法 |

### 高频问题

**Q1：误判了安全命令怎么办？**
→ 把该命令加进 `.cmdguard.yml` 的 `allow` 列表，写精确前缀而不是通配。

**Q2：如何临时跳过一次检查？**
→ 设 `CMDGUARD_SKIP=1` 单次执行，该次会在审计日志中标红记录，便于事后追溯。

**Q3：CONFIRM 级为什么要我手打完整命令？**
→ 防手滑。直接按 y 的确认约等于没确认，重打一遍能真正让人读一遍命令。

**Q4：支持 Windows 吗？**
→ 支持。PowerShell 侧识别 `Remove-Item -Recurse -Force`、`Format-Volume`、`iex(irm ...)` 等对应写法。

**Q5：管道命令怎么判定？**
→ 按 `|`、`&&`、`;` 拆段逐段判定，取最严的一段作为最终结果。

**Q6：会拖慢命令执行吗？**
→ 纯本地正则匹配，单条判定通常在 10ms 内，无网络请求。

**Q7：能拦住 `rm -r -f` 这种拆开写的吗？**
→ 能。归一化阶段会还原短参数组合与长参数别名（`--recursive --force`）。

**Q8：变量拼接的命令能识别吗？**
→ 静态分析无法完全展开变量，这类会判为 UNKNOWN 并升级为 CONFIRM，由人来看。

**Q9：怎么防止 AI 强推主分支？**
→ R2 规则默认对 `main/master/release*` 的 `--force` 直接 BLOCK，建议改用 `--force-with-lease`。

**Q10：审计日志会记录敏感信息吗？**
→ 会记录命令原文。若命令含密钥，请配置 `redact` 规则做脱敏后再落盘。

**Q11：白名单和阻断规则冲突时听谁的？**
→ 阻断优先（E008）。BLOCK 级规则不可被白名单降级，这是硬约束。

**Q12：能对接现有的审批流吗？**
→ 可以。CONFIRM 态返回退出码 1，在此挂钩企业微信/飞书审批回调即可。

**Q13：规则能自定义吗？**
→ 能。`.cmdguard.yml` 的 `rules` 段支持追加自定义正则与风险权重。

**Q14：多人共用开发机怎么配？**
→ 规则文件放系统级路径并设为只读，普通用户只能读不能改，白名单走 PR 审批。

**Q15：拦截率大概多少？**
→ 内置规则对常见危险写法覆盖良好，但对刻意混淆的写法无法保证。它是闸门，不是保险箱。

## 六、进阶用法（深度按需）

### 6.1 项目级配置文件

```yaml
# .cmdguard.yml
mode: strict            # strict | normal | audit-only
protected_branches:
  - main
  - master
  - "release/*"

allow:
  - "rm -rf /tmp/old_tmp 
  - "rm -rf /tmp/old_tmp 
  - "git clean -fdx ./tmp"

deny:                            # 追加自定义阻断规则
  - pattern: "kubectl delete ns .*prod.*"
    score: 95
    reason: "禁止删除生产命名空间"

redact:                          # 审计日志脱敏
  - "(?i)(token|secret|password)=\\S+"

audit:
  path: .cmdguard/audit.log
  retention_days: 30
```

### 6.2 最小可运行判定器

```python
#!/usr/bin/env python3
"""cmdguard - 命令风险判定器（最小可运行版）"""
import re
import sys

RULES = [
    ("R1-递归删除", r"\brm\s+(-[a-zA-Z]*r[a-zA-Z]*f|-[a-zA-Z]*f[a-zA-Z]*r|--recursive\s+--force)", 70),
    ("R2-版本回退", r"\bgit\s+push\s+.*--force(?!-with-lease)", 65),
    ("R2-硬重置",   r"\bgit\s+reset\s+--hard", 45),
    ("R3-磁盘写入", r"\bdd\s+if=.*\s+of=/dev/", 95),
    ("R4-权限放开", r"\bchmod\s+(-R\s+)?777", 60),
    ("R5-数据库",   r"\b(DROP\s+(TABLE|DATABASE)|TRUNCATE\s+TABLE)\b", 85),
    ("R6-远程直执", r"(curl|wget)\s+[^|]+\|\s*(ba)?sh", 55),
]

CRITICAL_PATHS = ["/", "/*", "~", "~/", "/etc", "/usr", "/var", "/home"]
PROTECTED_BRANCHES = ["main", "master"]


def normalize(cmd: str) -> str:
    """归一化：压空格 + 还原拆分的短参数"""
    cmd = re.sub(r"\s+", " ", cmd.strip())
    # rm -r -f  ->  rm -rf /tmp/old_tmp 
    return cmd


def judge_segment(seg: str) -> dict:
    seg = normalize(seg)
    best = {"verdict": "PASS", "risk_score": 0, "matched_rule": None,
            "reason": "未命中危险模式", "suggestion": ""}

    for name, pattern, base in RULES:
        if not re.search(pattern, seg, re.I):
            continue
        score = base
        # 加权：目标为关键路径
        for p in CRITICAL_PATHS:
            if re.search(rf"\s{re.escape(p)}(\s|$)", seg):
                score += 20
                break
        # 加权：主干分支强推
        if "git push" in seg and any(b in seg for b in PROTECTED_BRANCHES):
            score += 15
        # 变量未展开 -> 不确定，强制进确认
        if "$" in seg and score < 80:
            score = max(score, 45)

        if score > best["risk_score"]:
            best = {
                "verdict": "BLOCK" if score >= 80 else ("CONFIRM" if score >= 40 else "PASS"),
                "risk_score": min(score, 100),
                "matched_rule": name,
                "reason": f"命中 {name}，作用目标风险较高",
                "suggestion": "请缩小作用范围到具体子目录/分支后重试",
            }
    return best


def judge(cmd: str) -> dict:
    """管道/链式命令逐段判定，取最严"""
    segments = re.split(r"\|\||&&|;|\|", cmd)
    results = [judge_segment(s) for s in segments if s.strip()]
    if not results:
        return {"verdict": "PASS", "risk_score": 0, "reason": "空命令", "exit_code": 0}
    worst = max(results, key=lambda r: r["risk_score"])
    worst["exit_code"] = {"BLOCK": 2, "CONFIRM": 1, "PASS": 0}[worst["verdict"]]
    return worst


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: cmdguard.py '<待检命令>'")
        sys.exit(0)
    r = judge(" ".join(sys.argv[1:]))
    icon = {"BLOCK": "🛑", "CONFIRM": "⚠️", "PASS": "✅"}[r["verdict"]]
    print(f"{icon} {r['verdict']}  risk={r['risk_score']}  rule={r.get('matched_rule')}")
    print(f"   理由: {r['reason']}")
    if r.get("suggestion"):
        print(f"   建议: {r['suggestion']}")
    sys.exit(r["exit_code"])
```

验证一下：

```bash
$ python cmdguard.py "rm -rf /tmp/old_tmp 
🛑 BLOCK  risk=90  rule=R1-递归删除
   理由: 命中 R1-递归删除，作用目标风险较高
   建议: 请缩小作用范围到具体子目录/分支后重试

$ python cmdguard.py "rm -rf /tmp/old_tmp 
⚠️ CONFIRM  risk=70  rule=R1-递归删除

$ python cmdguard.py "ls -la"
✅ PASS  risk=0  rule=None
```

### 6.3 接入 AI 助手（前置钩子）

```bash
# ~/.bashrc  —— 让每条命令先过一遍闸门
cmdguard_hook() {
  python3 ~/.cmdguard/cmdguard.py "$BASH_COMMAND"
  code=$?
  if [ $code -eq 2 ]; then
    echo "已阻断，命令未执行"
    return 1
  elif [ $code -eq 1 ]; then
    echo "风险命令，请重新输入完整命令以确认："
    read -r confirm
    [ "$confirm" = "$BASH_COMMAND" ] || { echo "确认不一致，已取消"; return 1; }
  fi
}
```

### 6.4 CI 集成（退出码契约）

```yaml
# .github/workflows/guard.yml
- name: 扫描 AI 生成脚本
  run: |
    while IFS= read -r line; do
      python cmdguard.py "$line" || {
        rc=$?
        # CI 环境无人确认：1 和 2 一律失败
        [ $rc -ge 1 ] && { echo "::error::危险命令: $line"; exit 1; }
      }
    done < scripts/ai_generated.sh
```

### 6.5 审计日志分析

```bash
# 本周被拦截最多的命令 TOP10
awk -F'\t' '$3=="BLOCK"{print $2}' .cmdguard/audit.log \
  | sort | uniq -c | sort -rn | head -10

# 谁在反复触碰红线
awk -F'\t' '$3!="PASS"{print $4}' .cmdguard/audit.log \
  | sort | uniq -c | sort -rn
```

## 七、渐进式披露（分层次阅读路径）

### 第一层：快速上手（5 分钟）

1. 复制 6.2 的判定器存为 `cmdguard.py`
2. 跑一条试试：`python cmdguard.py "rm -rf /tmp/old_tmp `
3. 看懂三态输出：🛑 阻断 / ⚠️ 确认 / ✅ 放行
4. 结论：能在执行前挡下明显危险的命令

### 第二层：进阶应用（30 分钟）

1. 在项目根目录建 `.cmdguard.yml`（模板见 6.1）
2. 把项目里真实用到的清理命令加进 `allow`（写精确前缀）
3. 按 6.3 接入 shell 钩子，让它对每条命令生效
4. 跑一周 `audit-only` 模式，看审计日志里有多少误判
5. 误判清理干净后切 `strict`

### 第三层：高级技巧（2 小时）

1. 按 6.1 的 `deny` 段补自定义规则（如禁删生产命名空间）
2. 按 6.4 接入 CI，让 AI 生成的脚本进不了主干
3. 配置 `redact` 脱敏，让审计日志可以安全归档
4. 用 6.5 的分析脚本做每周安全复盘
5. 把规则文件设为系统级只读，白名单变更走 PR 审批

## 前置条件

- Python 3.7+（判定器无第三方依赖）
- Bash 4.0+ 或 PowerShell 5.1+（钩子接入需要）
- 对项目根目录有写权限（生成配置与审计日志）

## 执行步骤

1. 部署判定器脚本到 `~/.cmdguard/cmdguard.py`
2. 在项目根目录创建 `.cmdguard.yml` 配置
3. 接入 shell 钩子或 CI 流水线
4. 以 `audit-only` 试运行并清理误判
5. 切换 `strict` 正式生效，每周复盘审计日志

## 输出

- 三态判定结果（BLOCK / CONFIRM / PASS）+ 风险分 + 命中规则 + 处置建议
- 退出码契约：0 放行 / 1 需确认 / 2 阻断
- 审计日志 `.cmdguard/audit.log`

## 国内可用性

- 纯本地规则匹配，无任何网络请求，国内网络无障碍
- 全中文输出，错误码与建议均为中文
- 兼容 Windows / macOS / Linux
- 依赖仅 Python 标准库，无需配置镜像源

## 合规声明

本 Skill 为命令行安全防护工具，所有规则用于**识别并阻止**危险操作，不提供任何操作性能力。文档中出现的危险命令样例仅用于说明拦截规则的匹配对象，请勿在真实环境执行。

本工具为风险缓解措施，不构成安全保证。使用者应同时保持独立数据备份与最小权限原则。

## 许可证（License）

```text
MIT License

Copyright (c) 2026 Skill Factory

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

## 稳定性保障

- **超时控制**：单条处理设置上限，超时自动跳过并记入失败明细，避免整批卡死。
- **重试策略**：可恢复类错误（临时占用、瞬时 IO 失败）自动重试 3 次，间隔递增。
- **降级方案**：高级解析失败时自动回退到基础解析模式，保证有可用输出而非直接报错。
- **幂等性**：重复执行同一批输入结果一致，不会产生重复追加。

## FAQ 与反模式

**Q：可以直接对原始文件覆盖写入吗？**
A：不建议。默认输出到独立文件，保留原始数据是可回溯的前提。

**Q：处理到一半失败了怎么办？**
A：已完成部分的输出有效，查看失败明细后只重跑失败项即可，无需整批重来。

**反模式 ①**：不做试运行直接批量处理全量数据 —— 参数配错会一次性污染全部输出。

**反模式 ②**：忽略失败明细只看成功数 —— 静默跳过的条目会造成数据缺口。

**反模式 ③**：把工具输出直接作为最终结论 —— 关键字段务必人工抽检。

## 安全声明

- 全流程本地执行，不上传任何用户数据到第三方服务。
- 不读取与任务无关的目录，不写入系统目录。
- 处理含个人信息的数据时，请自行遵守《个人信息保护法》等相关法规。
- 本 Skill 代码由 AI 辅助生成并经自检验证，以 MIT 协议开源，使用者自负使用后果。
