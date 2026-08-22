---
slug: plexus
name: plexus
displayName: 智能体工具链 批量配置与编排
description: 为AI编程工具批量配置MCP服务、技能与规则，支持主流CLI智能体。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: LingToolsmith
agent_created: true
trigger_words: ["plexus", "MCP配置", "技能安装", "规则同步", "AI工具链", "智能体配置", "CLI工具集成"]
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# Plexus Skill 文档

## 1. 能力边界（一页纸速查卡）

### 1.1 能做什么

| 能力项 | 说明 | 输入示例 |
|--------|------|----------|
| MCP 服务批量配置 | 为多个 CLI 智能体统一写入 MCP 服务端点配置 | `plexus mcp --add server=github --url=https://mcp.example.com/sse` |
| 技能包安装 | 将本地或远程技能包注册到目标智能体的技能目录 | `plexus skill --install ./skills/pdf-tools` |
| 规则同步 | 将项目级规则文件分发到各智能体的规则加载路径 | `plexus rules --sync ./.plexus/rules/` |
| 配置审计 | 检查现有配置的完整性与冲突项 | `plexus --selftest` |
| 版本查询 | 输出当前工具链版本信息 | `plexus --version` |

### 1.2 不能做什么

- 不能直接修改智能体二进制文件或核心引擎逻辑。
- 不能自动重启或热加载正在运行的智能体进程（需手动重启）。
- 不能解析或转换非标准格式的 MCP 协议（如私有二进制协议）。
- 不能保证所有第三方 MCP 服务的可用性与稳定性。

### 1.3 适用对象

- 使用 Claude Code、Codex CLI、Gemini CLI 等命令行智能体的开发者。
- 需要统一管理多项目、多智能体配置的团队维护者。
- 希望在 CI/CD 流水线中自动化配置同步的运维工程师。

---

## 2. 触发方式与场景映射

### 2.1 触发词

直接使用 `plexus` 命令，或以下同义场景词：

- `MCP配置`
- `技能安装`
- `规则同步`
- `AI工具链`
- `智能体配置`
- `CLI工具集成`

### 2.2 场景映射表

| 用户说（大白话） | 实际触发动作 | 命令示例 |
|------------------|--------------|----------|
| "帮我把这个 MCP 服务加到所有智能体里" | 批量添加 MCP 端点 | `plexus mcp --add --global` |
| "新来的同事需要装那套 PDF 技能" | 安装技能包到指定智能体 | `plexus skill --install ./skills/pdf-tools --target claude-code` |
| "项目规则改了，同步一下" | 同步规则文件 | `plexus rules --sync` |
| "检查一下我的配置有没有问题" | 运行自检 | `plexus --selftest` |
| "你现在什么版本？" | 查询版本 | `plexus --version` |

---

## 3. 标准流程

### 3.1 前置条件

| 条件 | 要求 | 校验方式 |
|------|------|----------|
| 操作系统 | Linux/macOS/Windows (WSL2) | `uname -a` 或 `ver` |
| 运行时 | Node.js ≥ 18 或 Python ≥ 3.9 | `node -v` / `python3 --version` |
| 配置文件 | 目标智能体已初始化（存在配置目录） | 检查 `~/.claude-code/` 或 `~/.codex/` 等 |
| 网络 | 若安装远程技能包需外网访问 | `curl -I https://registry.npmjs.org` |

### 3.2 执行步骤（分步编号）

#### 步骤 1：读取输入参数

```bash
plexus mcp --add server=github --url=https://mcp.example.com/sse --target all
```

参数表：

| 参数 | 必填 | 默认值 | 说明 |
|------|------|--------|------|
| `--add` | 是 | - | 添加操作 |
| `server` | 是 | - | MCP 服务名称（字母数字下划线） |
| `--url` | 是 | - | 服务端点 URL（http/https/ws） |
| `--target` | 否 | `all` | 目标智能体：`all`/`claude-code`/`codex`/`gemini-cli` |
| `--global` | 否 | `false` | 写入全局配置而非项目配置 |

#### 步骤 2：执行核心逻辑

- 解析参数，校验 URL 格式与协议白名单（http/https/ws）。
- 读取目标智能体的配置文件（JSON/YAML/TOML 自动识别）。
- 合并 MCP 服务条目，检测重名冲突（若冲突则报错码 `E1002`）。
- 写入配置前自动备份原文件为 `.bak` 后缀。

#### 步骤 3：输出结构化结果

```json
{
  "status": "success",
  "operation": "mcp.add",
  "targets": ["claude-code", "codex"],
  "added": ["github"],
  "conflicts": [],
  "backup_paths": ["~/.claude-code/config.json.bak"]
}
```

#### 步骤 4：给出下一步建议

- 若添加成功：提示 `请重启目标智能体以加载新配置`。
- 若存在冲突：提示 `运行 plexus mcp --list 查看当前全部服务`。
- 若自检失败：提示 `运行 plexus --selftest --verbose 获取详细日志`。

### 3.3 输出规范

- 所有命令输出均为 JSON 格式（除非指定 `--human` 参数）。
- 退出码：`0` 成功，`1` 参数错误，`2` 运行时错误，`3` 配置冲突。
- 日志输出到 stderr，结构化结果输出到 stdout。

---

## 4. 置信度门控

当出现以下情况时，**不得**编造或猜测信息，必须输出 `[需核实:字段]` 占位符：

| 场景 | 占位符示例 | 处理方式 |
|------|------------|----------|
| 目标智能体类型未知 | `[需核实:target_type]` | 提示用户指定 `--target` |
| MCP 服务协议无法识别 | `[需核实:protocol]` | 拒绝写入并提示检查 URL |
| 技能包依赖版本不明确 | `[需核实:dependency_version]` | 跳过安装并列出缺失依赖 |
| 规则文件格式非标准 | `[需核实:rule_format]` | 提示用户提供 schema 或示例 |

示例输出：

```json
{
  "status": "blocked",
  "reason": "无法识别 MCP 协议",
  "placeholder": "[需核实:protocol]",
  "suggestion": "请确认 URL 以 http://、https:// 或 ws:// 开头"
}
```

---

## 5. 错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| `E1001` | 参数缺失 | `缺少必要参数：--url` | 补充参数后重试 |
| `E1002` | 配置冲突 | `服务名 github 已存在，请使用 --force 覆盖` | 加 `--force` 或换名 |
| `E1003` | 目标智能体不存在 | `未找到 claude-code 的配置目录` | 先初始化该智能体 |
| `E2001` | 网络超时 | `无法连接远程技能仓库，请检查网络` | 重试或改用本地路径 |
| `E2002` | 权限不足 | `配置文件只读，请检查文件权限` | `chmod +w` 后重试 |
| `E3001` | 格式解析失败 | `配置文件不是合法的 JSON/TOML` | 手动修复或恢复 `.bak` 备份 |

---

## 6. FAQ 反模式对照

| 常见坑（反模式） | 正确做法 |
|------------------|----------|
| 直接手动编辑多个智能体的配置文件，导致格式不一致 | 统一使用 `plexus` 命令管理，保证格式一致 |
| 在配置中添加未验证的 MCP 服务 URL，导致智能体启动失败 | 先 `curl -I` 验证端点可访问性，再写入配置 |
| 忽略备份文件，配置出错后无法回滚 | 每次写入前自动备份，出错时用 `.bak` 恢复 |
| 将项目级规则同步到全局目录，污染其他项目 | 明确区分 `--project` 与 `--global` 作用域 |
| 安装技能包时跳过依赖检查，运行时才发现缺失 | 安装前执行 `plexus skill --check-deps` 预检 |

---

## 7. 渐进式披露

### 7.1 速查卡（30 秒上手）

```bash
# 查看版本
plexus --version

# 添加一个 MCP 服务到所有智能体
plexus mcp --add server=github --url=https://mcp.example.com/sse --target all

# 安装本地技能包
plexus skill --install ./skills/pdf-tools

# 同步规则文件
plexus rules --sync

# 自检配置
plexus --selftest
```

### 7.2 新手路径（首次使用）

1. 运行 `plexus --selftest` 确认环境就绪。
2. 使用 `plexus mcp --add` 添加第一个 MCP 服务。
3. 使用 `plexus skill --install` 安装一个技能包。
4. 重启智能体，验证配置生效。

### 7.3 进阶路径（批量管理）

1. 编写配置文件 `plexus.config.json` 声明全部服务与技能。
2. 使用 `plexus apply --config plexus.config.json` 一键应用。
3. 在 CI 中集成 `plexus --selftest --strict` 作为质量门禁。
4. 使用 `plexus export` 导出当前配置用于团队共享。

---

## 8. 用户协议

<!-- user-agreement-injected -->

**使用须知：**

1. 本 Skill 仅提供配置管理与编排指导，不构成对任何第三方服务的认可或担保。
2. 使用者应自行评估并承担因配置变更、技能安装、规则同步等操作可能引发的全部风险与责任。
3. 禁止对本 Skill 进行反向工程、反编译、破解或试图提取底层源代码（除非适用法律明确允许）。
4. 使用者应确保其操作符合所在组织的信息安全政策与相关法律法规。
5. 本 Skill 不提供任何形式的明示或默示保证，包括但不限于适销性、特定用途适用性及非侵权性。

---

## 9. 许可证（License）

<!-- professional-license-embedded -->

**MIT License**

版权所有 (c) 2025 原创作者（自持版权）

特此免费授予任何获得本软件及相关文档文件（以下简称"软件"）副本的人士使用、复制、修改、合并、发布、分发、再许可及/或出售软件副本的权利，但须满足以下条件：

上述版权声明和本许可声明应包含在软件的所有副本或实质性部分中。

本软件按"原样"提供，不附带任何明示或默示的保证，包括但不限于适销性、特定用途适用性及非侵权性保证。在任何情况下，作者或版权持有人均不对因使用本软件而产生的任何索赔、损害或其他责任负责，无论是在合同诉讼、侵权或其他诉讼中。

---

*本 Skill 由 AI 辅助生成，仅供参考。使用前请阅读相关文档并自行验证。*
