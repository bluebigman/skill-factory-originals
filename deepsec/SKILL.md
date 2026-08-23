---
slug: deepsec
name: deepsec
displayName: 代码安全审计 依赖风险 配置缺陷检测
description: 检测AI生成代码中的恶意依赖与配置缺陷，输出结构化审计报告。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: Lin Chen
agent_created: true
trigger_words: ["deepsec", "安全审计", "代码风险检测", "依赖安全", "AI代码审查", "供应链攻击", "配置漏洞扫描"]
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# deepsec — 代码安全审计 Skill 文档

## 一、能力边界（一页纸速查卡）

### 1.1 能做

| 编号 | 能力项 | 说明 | 输出物 |
|------|--------|------|--------|
| C-01 | 输入准备 | 将待审计文件放入统一工作目录，校验命名规范 | 文件清单 `manifest.txt` |
| C-02 | 单样本试运行 | 对单个文件执行审计，核对输出字段与格式是否符合预期 | 单样本审计报告 `sample_report.json` |
| C-03 | 批量执行 | 对全量文件执行审计，自动生成备份目录 | 批量审计报告集 `reports/` 目录 |
| C-04 | 结果校验 | 抽查输出条目，核对关键字段与源数据一致性 | 校验记录 `validation_log.csv` |
| C-05 | 恶意依赖识别 | 检测依赖清单中的可疑包名、版本异常、来源不明组件 | 依赖风险清单 `dependency_risks.json` |
| C-06 | 配置缺陷扫描 | 检查配置文件中的弱口令、硬编码密钥、权限过度开放等问题 | 配置缺陷报告 `config_issues.json` |

### 1.2 不能做

| 编号 | 限制项 | 说明 |
|------|--------|------|
| N-01 | 不执行代码 | 本工具仅做静态分析，不运行目标代码 |
| N-02 | 不保证检出率 | 无法覆盖所有攻击向量，新型攻击手法可能漏检 |
| N-03 | 不替代人工审查 | 输出结果需由安全工程师复核确认 |
| N-04 | 不处理加密内容 | 加密或混淆的依赖包无法深度分析 |
| N-05 | 不提供修复代码 | 仅指出问题位置与建议方向，不自动生成补丁 |

### 1.3 适用对象

| 对象类型 | 适用场景 | 不适用场景 |
|----------|----------|------------|
| 使用AI生成代码的开发者 | 提交前自检、CI流水线集成 | 生产环境实时防护 |
| 安全审计人员 | 代码入库前批量筛查 | 渗透测试 |
| 技术管理者 | 外包代码交付验收 | 合规认证（需专业机构） |

---

## 二、触发方式

### 2.1 触发词

当对话中出现以下任一词汇或短语时，本 Skill 将被激活：

| 触发词 | 场景示例 |
|--------|----------|
| deepsec | "用 deepsec 扫一下这个项目" |
| 安全审计 | "帮我做一次安全审计" |
| 代码风险检测 | "检测这段代码的风险" |
| 依赖安全 | "检查一下依赖包安不安全" |
| AI代码审查 | "AI生成的代码需要审查" |
| 供应链攻击 | "看看有没有供应链攻击风险" |
| 配置漏洞扫描 | "扫描配置文件漏洞" |

### 2.2 场景映射表

| 用户实际需求（大白话） | 对应能力 |
|------------------------|----------|
| "帮我看看这个AI写的代码有没有问题" | 执行完整审计流程 |
| "这个依赖包靠谱吗？" | 执行依赖风险专项检查 |
| "配置文件里有没有密码泄露？" | 执行配置缺陷专项扫描 |
| "批量检查一下这堆文件" | 执行批量审计模式 |
| "先试一个看看效果" | 执行单样本试运行 |

---

## 三、标准流程

### 3.1 前置条件

| 条件项 | 要求 | 检查方式 |
|--------|------|----------|
| 工作目录 | 所有待审计文件位于同一目录 | `ls -la` 确认 |
| 命名规范 | 文件名遵循 `[项目名]_[模块名].[扩展名]` 格式 | 正则校验 `^[a-z0-9_]+_[a-z0-9_]+\.[a-z0-9]+$` |
| 依赖清单 | 存在 `requirements.txt` 或 `package.json` | 文件存在性检查 |
| 配置文件 | 存在 `.env`、`config.*` 或 `*.yaml` 配置 | 文件存在性检查 |
| 磁盘空间 | 至少 500MB 可用空间（用于备份） | `df -h` 确认 |

### 3.2 执行步骤

**Step 1：初始化工作区**

```bash
mkdir -p ./audit_workspace/{input,backup,reports}
cp /path/to/target/files/* ./audit_workspace/input/
cd ./audit_workspace
```

**Step 2：生成文件清单**

```bash
find ./input -type f | sort > manifest.txt
wc -l manifest.txt  # 确认文件总数
```

**Step 3：单样本试运行**

```bash
deepsec audit --input ./input/sample_project_main.py --output ./reports/sample_report.json
```

校验输出字段：

| 字段名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `file_path` | string | 是 | 源文件路径 |
| `risk_level` | enum | 是 | `critical` / `high` / `medium` / `low` |
| `issue_type` | enum | 是 | `malicious_dependency` / `config_defect` / `suspicious_pattern` |
| `description` | string | 是 | 问题描述 |
| `line_number` | int | 否 | 问题所在行号 |
| `recommendation` | string | 否 | 修复建议 |

**Step 4：批量执行**

```bash
cp -r ./input ./backup/original_$(date +%Y%m%d_%H%M%S)
deepsec audit --input ./input --output ./reports --batch
```

**Step 5：结果校验**

```bash
deepsec validate --manifest manifest.txt --reports ./reports --output validation_log.csv
```

校验规则：
- 每个输入文件必须有对应报告
- 报告中的 `file_path` 必须与清单一致
- 风险等级枚举值必须合法
- 抽查比例不低于 10%

### 3.3 输出规范

| 输出物 | 格式 | 存放位置 | 更新频率 |
|--------|------|----------|----------|
| 文件清单 | `manifest.txt` | 工作区根目录 | 每次执行 |
| 单样本报告 | JSON | `reports/` | 试运行阶段 |
| 批量报告集 | JSON（每文件一份） | `reports/` | 批量执行 |
| 依赖风险清单 | JSON | `reports/dependency_risks.json` | 每次执行 |
| 配置缺陷报告 | JSON | `reports/config_issues.json` | 每次执行 |
| 校验记录 | CSV | `validation_log.csv` | 校验阶段 |

---

## 四、置信度门控

### 4.1 信息不足处理

当遇到以下情况时，输出 `[需核实:字段名]` 占位符，**不编造**：

| 场景 | 占位符示例 | 处理方式 |
|------|------------|----------|
| 依赖包版本未知 | `[需核实:package_version]` | 提示用户提供版本号 |
| 配置项用途不明 | `[需核实:config_purpose]` | 标记为待确认项 |
| 文件来源不明 | `[需核实:file_origin]` | 跳过该文件并记录 |
| 网络请求目标未知 | `[需核实:request_destination]` | 标记为可疑项 |

### 4.2 置信度分级

| 置信度等级 | 标识 | 含义 | 处理建议 |
|------------|------|------|----------|
| 高 | `[确认]` | 有明确证据支持 | 直接采纳 |
| 中 | `[可能]` | 有间接证据支持 | 人工复核 |
| 低 | `[需核实]` | 证据不足或矛盾 | 补充信息后重审 |

---

## 五、错误码体系

| 错误码 | 错误描述 | 提示话术 | 修正步骤 |
|--------|----------|----------|----------|
| `E001` | 输入目录不存在 | "指定的输入路径不存在，请检查路径是否正确" | 1. 确认路径拼写 2. 创建目录 3. 重新执行 |
| `E002` | 文件命名不符合规范 | "文件 `xxx` 命名不符合 `项目_模块.扩展名` 格式" | 1. 重命名文件 2. 更新 manifest 3. 重新执行 |
| `E003` | 缺少依赖清单 | "未找到 requirements.txt 或 package.json" | 1. 生成依赖清单 2. 放入输入目录 3. 重新执行 |
| `E004` | 输出目录无写入权限 | "无法写入输出目录，请检查权限" | 1. `chmod +w` 目录 2. 或更换目录 3. 重新执行 |
| `E005` | 批量执行中断 | "批量执行在第 N 个文件处中断" | 1. 查看错误日志 2. 修复问题文件 3. 从断点继续 |
| `E006` | 结果校验不一致 | "报告中的 file_path 与清单不一致" | 1. 删除不一致报告 2. 重新生成 3. 再次校验 |
| `E007` | 磁盘空间不足 | "可用空间不足 500MB，无法创建备份" | 1. 清理磁盘 2. 或跳过备份 3. 重新执行 |

---

## 六、FAQ 反模式

### 6.1 常见坑与反模式对照

| 编号 | 常见坑 | 反模式（错误做法） | 正确做法 |
|------|--------|-------------------|----------|
| F-01 | 跳过试运行直接批量 | 直接对全量文件执行批量审计 | 先用单个样本验证输出格式，确认无误后再批量 |
| F-02 | 不保留原始备份 | 直接覆盖原始文件 | 执行前必须复制到 `backup/` 目录 |
| F-03 | 忽略置信度占位符 | 将 `[需核实]` 当作最终结论 | 对占位符逐项核实，补充信息后重新审计 |
| F-04 | 只关注高危项 | 忽略 `low` 级别风险 | 低风险项也可能组合成攻击链，需记录在案 |
| F-05 | 依赖清单不完整 | 只审计主文件，忽略依赖声明 | 确保 `requirements.txt` / `package.json` 完整 |
| F-06 | 输出格式不校验 | 直接使用未校验的报告 | 执行 `validate` 命令，确保字段一致性 |

### 6.2 反模式示例

**反模式 F-01 示例：**

```bash
# ❌ 错误：跳过试运行
deepsec audit --input ./input --output ./reports --batch

# ✅ 正确：先试运行
deepsec audit --input ./input/sample.py --output ./reports/sample.json
# 核对字段后
deepsec audit --input ./input --output ./reports --batch
```

---

## 七、渐进式披露

### 7.1 速查卡（30秒上手）

```
1. 准备：文件放入 input/ 目录
2. 试运行：deepsec audit --input input/样本文件 --output reports/样本.json
3. 核对：检查 risk_level 和 issue_type 字段
4. 批量：deepsec audit --input input/ --output reports/ --batch
5. 校验：deepsec validate --manifest manifest.txt --reports reports/
```

### 7.2 分层次阅读路径

**新手路径（首次使用）：**

1. 阅读「一、能力边界」了解工具范围
2. 按「三、标准流程」Step 1-3 完成单样本试运行
3. 对照「五、错误码体系」处理可能遇到的问题
4. 阅读「六、FAQ 反模式」避免常见错误

**进阶路径（熟练使用）：**

1. 深入理解「四、置信度门控」的占位符处理机制
2. 自定义校验规则，扩展 `validate` 命令的检查项
3. 将审计流程集成到 CI/CD 流水线
4. 结合「六、FAQ 反模式」优化审计策略

---

## 八、用户协议

<!-- user-agreement-injected -->

**使用本 Skill 即表示您同意以下条款：**

1. **责任承担**：使用者自行承担因使用本 Skill 产生的全部责任。本 Skill 提供的审计结果仅供参考，不构成任何形式的安全保证。

2. **禁止反向工程**：不得对本 Skill 的底层算法、检测逻辑进行反向工程、反编译或试图提取源代码。

3. **数据使用**：使用者应对被审计的数据拥有合法权利，并同意本 Skill 在处理过程中对数据的临时访问。

4. **结果解释**：审计结果的解释权归使用者所有，本 Skill 不对因误读或误用结果导致的损失负责。

5. **更新与变更**：本 Skill 可能随时更新，使用者应定期查看最新版本。

---

## 九、许可证（License）

<!-- professional-license-embedded -->

**MIT License**

Copyright (c) 2024 Lin Chen

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

*文档版本：1.0.0 | 最后更新：2024年*
