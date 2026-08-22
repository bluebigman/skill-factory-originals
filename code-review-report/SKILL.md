---
slug: code-review-report
name: code-review-report
displayName: 代码审查 变更巡检 风险扫描
description: 解析git diff，扫描密码硬编码、不安全日志、性能反模式与平台依赖，输出分级审查报告。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 独立技能工坊
agent_created: true
trigger_words: ["code-review-report","代码审查","代码评审","diff审查","变更检查","代码走查","变更评审","diff扫描"]
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# code-review-report — 代码变更审查与风险扫描

## 一、能力边界（一页纸速查卡）

### 1.1 能做什么

| 能力项 | 说明 |
|--------|------|
| 解析 git diff | 接受 `.diff` / `.patch` / `.txt` 格式的变更文件，自动识别 UTF-8 / GBK / UTF-16 编码 |
| 规则扫描 | 内置 4 类规则：硬编码密码、不安全日志、性能反模式、平台依赖 |
| 分级输出 | 按严重级 P0（阻断）/ P1（警告）/ P2（建议）输出审查结果 |
| 多格式报告 | 支持 Markdown 与 JSON 两种输出格式 |
| 严重级过滤 | 通过 `--filter` 参数只查看指定级别及以上的问题 |
| 密码脱敏 | 报告中自动遮蔽疑似密码的敏感字段内容 |
| 默认预览不写盘 | 未加 `--force` 时仅打印结果，不生成文件 |

### 1.2 不能做什么

| 限制项 | 说明 |
|--------|------|
| 不执行代码 | 仅做静态文本分析，不运行被测代码 |
| 不识别上下文语义 | 对误报（如测试代码中的假密码）无法自动判断，需人工复核 |
| 不支持非 diff 格式 | 不接受完整源码文件或压缩包，仅处理变更内容 |
| 不联网 | 所有规则均为本地内置，无外部依赖 |

### 1.3 适用对象

- 日常提交代码前的自检
- CI 流水线中的变更门禁
- 代码评审前的预扫描
- 多分支合并前的风险排查

---

## 二、触发方式

### 2.1 触发词

直接使用 `code-review-report` 或以下任一中文同义词即可唤起：

`代码审查`、`代码评审`、`diff审查`、`变更检查`、`代码走查`、`变更评审`、`diff扫描`

### 2.2 场景映射表

| 用户说（大白话） | 实际执行动作 |
|------------------|--------------|
| "帮我看看这个 diff 有没有问题" | 解析 diff 文件，执行全量规则扫描，输出预览报告 |
| "只查 P0 级别的问题" | 加 `--filter P0` 参数，仅输出阻断级问题 |
| "把报告存下来" | 加 `--output report.md --force` 落盘 |
| "跑一遍自测" | 执行 `--selftest`，验证 12 条内置用例全部通过 |
| "输出 JSON 格式" | 加 `--format json` 参数 |

---

## 三、标准流程

### 3.1 前置条件

| 条件 | 要求 |
|------|------|
| 输入文件 | 必须是 git diff 格式的文本文件，扩展名 `.diff` / `.patch` / `.txt` |
| 运行环境 | Python 3.8+，无需安装第三方依赖 |
| 文件大小 | 单文件不超过 10MB，行数不超过 50,000 行 |

### 3.2 执行步骤

1. **获取变更文件**：从版本控制导出 diff 文件，或使用 `git diff > change.diff` 生成。
2. **运行扫描**：
   ```bash
   python run.py --diff change.diff
   ```
3. **查看预览**：默认在终端打印分级报告，不写盘。
4. **按需过滤**：若问题过多，加 `--filter P0,P1` 只看高严重级。
5. **落盘输出**：确认无误后，加 `--output report.md --force` 生成文件。
6. **自测验证**（可选）：首次使用或规则更新后，执行 `python run.py --selftest` 确认 12/12 全绿。

### 3.3 参数速查表

| 参数 | 取值 | 默认值 | 说明 |
|------|------|--------|------|
| `--diff` | 文件路径 | 无（必填） | 指定 diff 文件 |
| `--filter` | `P0` / `P0,P1` / `P0,P1,P2` | `P0,P1,P2` | 按严重级过滤 |
| `--output` | 文件路径 | 无 | 输出文件路径 |
| `--format` | `markdown` / `json` | `markdown` | 输出格式 |
| `--force` | 无值 | 不启用 | 允许写盘（需配合 `--output`） |
| `--selftest` | 无值 | 不启用 | 运行内置自测 |
| `--version` | 无值 | 不启用 | 打印版本号 |

### 3.4 输出规范

#### Markdown 报告结构

```markdown
# 代码审查报告

- 扫描文件：change.diff
- 扫描时间：2025-01-15 14:30:22
- 规则版本：1.0.0

## 统计概览
| 严重级 | 数量 |
|--------|------|
| P0     | 2    |
| P1     | 5    |
| P2     | 3    |

## 问题明细

### [P0] 硬编码密码
- 文件：src/config.py
- 行号：42
- 描述：检测到疑似硬编码密码
- 内容：`password = "******"`（已脱敏）
- 建议：使用环境变量或密钥管理服务

### [P1] 不安全日志
- 文件：src/logger.py
- 行号：17
- 描述：日志中可能输出敏感信息
- 内容：`log.info(f"user: {user}")`
- 建议：对敏感字段做脱敏处理
```

#### JSON 报告结构

```json
{
  "meta": {
    "file": "change.diff",
    "scanned_at": "2025-01-15T14:30:22",
    "rule_version": "1.0.0"
  },
  "summary": {
    "P0": 2,
    "P1": 5,
    "P2": 3
  },
  "issues": [
    {
      "severity": "P0",
      "rule": "hardcoded_password",
      "file": "src/config.py",
      "line": 42,
      "message": "检测到疑似硬编码密码",
      "snippet": "password = \"******\"",
      "suggestion": "使用环境变量或密钥管理服务"
    }
  ]
}
```

---

## 四、置信度门控

当扫描过程中遇到以下情况，输出中会明确标注 `[需核实:字段]` 占位符，**不编造**任何信息：

| 场景 | 输出行为 |
|------|----------|
| 文件编码无法识别 | `[需核实:文件编码]`，跳过该文件 |
| 行号超出文件范围 | `[需核实:行号]`，保留描述但标注位置不确定 |
| 疑似密码但上下文不明确 | `[需核实:是否确为密码]`，降级为 P1 处理 |
| 规则匹配到测试代码 | `[需核实:测试代码是否豁免]`，默认按 P2 输出 |

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| `E001` | 未指定 diff 文件 | "请使用 --diff 参数指定变更文件路径" | 补加 `--diff change.diff` |
| `E002` | 文件不存在 | "找不到指定文件，请检查路径" | 确认路径正确或使用绝对路径 |
| `E003` | 文件格式不支持 | "仅支持 .diff / .patch / .txt 格式" | 转换文件格式后重试 |
| `E004` | 文件超过大小限制 | "文件超过 10MB 限制，请拆分后扫描" | 按目录或文件拆分 diff |
| `E005` | 编码识别失败 | "无法识别文件编码，请手动指定" | 转换为 UTF-8 后重试 |
| `E006` | 输出目录无权限 | "无法写入目标目录，请检查权限" | 更换输出路径或调整权限 |
| `E007` | 参数冲突 | "--force 必须与 --output 配合使用" | 同时添加 `--output` 参数 |
| `E008` | 自测失败 | "内置自测未通过，请检查环境完整性" | 重新安装或联系维护者 |

---

## 六、FAQ 反模式

### 6.1 常见坑位

| 坑位 | 反模式表现 | 正确做法 |
|------|------------|----------|
| **忽略误报** | 扫描结果直接全盘接受，不人工复核 | 对每条 P0 问题人工确认后再修复 |
| **过度依赖过滤** | 用 `--filter P0` 跳过所有 P1/P2 问题 | 至少完整查看一次全量报告 |
| **不脱敏就分享** | 将原始报告直接发到群里 | 确认报告已自动脱敏，或手动检查敏感字段 |
| **忘记自测** | 规则更新后不跑 `--selftest` | 每次升级后先跑自测再使用 |
| **只看数量不看内容** | 只关注 P0 数量是否为 0 | 逐条阅读问题描述与修复建议 |

### 6.2 反模式对照表

| 反模式 | 问题 | 替代方案 |
|--------|------|----------|
| 把报告当最终结论 | 工具无法理解业务上下文 | 将报告作为评审辅助材料，结合人工判断 |
| 扫描后不修复 | 发现问题但不处理，失去意义 | 建立问题跟踪清单，逐项闭环 |
| 频繁全量扫描 | 大 diff 扫描耗时且噪音多 | 按模块拆分 diff，分批扫描 |

---

## 七、渐进式披露

### 7.1 速查卡（30 秒上手）

```bash
# 1. 生成 diff
git diff > change.diff

# 2. 扫描预览
python run.py --diff change.diff

# 3. 只看 P0
python run.py --diff change.diff --filter P0

# 4. 落盘保存
python run.py --diff change.diff --output report.md --force

# 5. 自测
python run.py --selftest
```

### 7.2 新手路径（首次使用）

1. 先跑 `--selftest` 确认环境正常
2. 用一个小 diff 文件试跑，熟悉输出格式
3. 对照报告逐条理解 P0/P1/P2 的含义
4. 尝试用 `--filter` 和 `--format json` 体验不同输出

### 7.3 进阶路径（深度使用）

1. 将扫描集成到 CI 流水线，作为合并请求的门禁
2. 结合团队规范，自定义规则阈值（需修改规则配置文件）
3. 对历史报告做趋势分析，跟踪问题密度变化
4. 将 JSON 输出接入内部看板，实现可视化

---

## 八、内置规则说明

| 规则类别 | 规则 ID | 严重级 | 检测内容 |
|----------|---------|--------|----------|
| 硬编码密码 | `hardcoded_password` | P0 | 检测 `password = "..."`、`passwd:`、`pwd=` 等模式 |
| 不安全日志 | `unsafe_logging` | P1 | 检测日志中直接拼接用户输入或敏感字段 |
| 性能反模式 | `performance_anti_pattern` | P1 | 检测循环内 SQL 查询、N+1 查询等模式 |
| 平台依赖 | `platform_dependency` | P2 | 检测硬编码路径（如 `/usr/bin`）、Windows 专属 API |

---

## 九、用户协议

<!-- user-agreement-injected -->

**使用前请仔细阅读以下条款：**

1. **责任承担**：使用者自行承担因使用本 Skill 产生的全部责任。本工具仅提供静态分析辅助，不构成对代码安全性的任何保证。
2. **禁止反向工程**：不得对本 Skill 的规则引擎、检测逻辑进行逆向工程、反编译或试图提取源代码。
3. **数据安全**：使用者应对输入文件中的敏感信息负责，建议在扫描前对包含机密数据的文件进行脱敏处理。
4. **合规使用**：使用者应确保使用本工具的行为符合所在组织及当地法律法规的要求。
5. **免责声明**：本 Skill 按"现状"提供，不附带任何明示或暗示的担保，包括但不限于适销性、特定用途适用性和非侵权保证。

---

## 十、许可证（License）

<!-- professional-license-embedded -->

### MIT License

Copyright (c) 2025 独立技能工坊

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

*本 Skill 由 AI 辅助生成，仅供参考。使用前请阅读相关文档。*
