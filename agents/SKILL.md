# 多智能体协作框架 · 技能文档

```yaml
---
slug: agents
name: 多智能体协作框架
displayName: 任务拆解 多角色协同 结果归并
description: 编排多个AI Agent分工协作，完成复杂任务并输出结构化结果
version: 1.0.17
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/agents
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 协同流工作室
agent_created: true
trigger_words:
  - "多智能体"
  - "多代理协作"
  - "agent编排"
  - "任务分工"
---
```

> 本内容由 AI 生成，仅供学习参考 <!-- ai-generated-notice -->

---

## 一、适用场景与前置条件

本技能适用于需要将一项复杂任务拆解为多个子任务，并由不同角色的 AI Agent 并行或串行处理的场景。典型用途包括：研究报告撰写、代码模块开发、内容多维度审核、数据分析流水线等。

**使用前请确认以下条件已满足：**

| 条件项 | 要求 |
|--------|------|
| 运行环境 | 已安装 Node.js 18+ 或 Python 3.9+（取决于 CLI 实现） |
| 项目仓库 | 目标仓库已可访问（本地路径或远程 Git URL） |
| 依赖管理 | 项目包含 `package.json` 或 `requirements.txt` 等依赖声明文件 |
| 网络权限 | 若使用远程仓库，需具备克隆与拉取权限 |
| 基础命令 | `git`、`npm`/`pip`、`./main` 可执行文件已就绪 |

---

## 二、执行流程总览

整个运行过程分为四个阶段，按序推进：

```mermaid
graph TD
    A[收集输入参数] --> B[环境准备与部署]
    B --> C[执行agent任务编排]
    C --> D[结果收集与校验]
    D --> E[输出结构化报告]
```

---

## 三、详细执行步骤

### 步骤 1：收集用户输入并确认格式

用户需提供以下信息（至少包含任务描述）：

- **任务描述**：自然语言描述需要完成的目标
- **Agent 角色配置**（可选）：指定参与协作的 Agent 类型与数量
- **参数覆盖**（可选）：覆盖默认 CLI 参数的键值对

**输入格式校验规则：**

| 输入类型 | 合法格式 | 非法示例 |
|----------|----------|----------|
| 任务描述 | 非空字符串，长度 ≥ 10 字符 | 空、纯标点 |
| 角色配置 | JSON 数组，元素为合法角色名 | 非 JSON、未知角色 |
| 参数覆盖 | `key=value` 对，用空格分隔 | 缺少 `=`、值为空 |

> 若输入不满足上述规则，直接进入“失败处理”章节，返回错误说明与正确格式示例。

### 步骤 2：环境准备与项目部署

```bash
# 2.1 获取项目源码
if [ -d "./workspace" ]; then
    cd ./workspace
    git pull origin main
else
    git clone <repository_url> ./workspace
    cd ./workspace
fi

# 2.2 安装依赖
if [ -f "package.json" ]; then
    npm install
elif [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
else
    echo "WARNING: 未找到依赖声明文件，跳过安装"
fi

# 2.3 确认 CLI 可执行
chmod +x ./main
./main --version  # 验证安装成功
```

**环境就绪标准：**
- 退出码为 0
- `./main --version` 能输出版本号

### 步骤 3：执行 Agent 任务编排

#### 3.1 基础命令格式

```bash
./main --task "<任务描述>" [--agents '<角色JSON>'] [--params "key=value key2=value2"]
```

#### 3.2 常用参数说明

| 参数 | 必填 | 默认值 | 说明 |
|------|------|--------|------|
| `--task` | 是 | 无 | 任务描述文本 |
| `--agents` | 否 | 默认角色组 | 角色配置 JSON 数组 |
| `--params` | 否 | 空 | 自定义参数对 |
| `--output` | 否 | `./output` | 结果输出目录 |
| `--timeout` | 否 | 300 | 单 Agent 超时秒数 |
| `--retry` | 否 | 2 | 失败重试次数 |

#### 3.3 典型调用示例

```bash
# 示例1：默认配置执行
./main --task "分析用户流失原因并提出3条改进建议"

# 示例2：指定角色分工
./main --task "编写一个登录模块的单元测试" \
    --agents '[{"role":"架构师","count":1},{"role":"测试工程师","count":2}]'

# 示例3：覆盖超时与输出路径
./main --task "生成季度销售报告" \
    --params "year=2025 quarter=Q1" \
    --output "./reports" --timeout 600
```

#### 3.4 帮助信息查询

任何时候可运行以下命令获取完整用法：

```bash
./main --help
```

该命令会输出所有可用参数、示例与退出码说明。

### 步骤 4：结果收集与完整性校验

#### 4.1 捕获输出

执行完成后，程序会自动捕获并保存：

- **标准输出（stdout）** → 保存至 `{output_dir}/stdout.log`
- **错误输出（stderr）** → 保存至 `{output_dir}/stderr.log`
- **文件型产出** → 保存至 `{output_dir}/artifacts/` 目录

#### 4.2 完整性校验规则

| 检查项 | 通过标准 |
|--------|----------|
| 退出码 | 等于 0 |
| stdout 非空 | 日志文件大小 > 0 字节 |
| 关键产出存在 | `artifacts/` 下存在预期文件（若任务声明了产出） |
| 无致命错误 | stderr 中不包含 `FATAL` 或 `ERROR` 级别日志 |

#### 4.3 输出结构化整理

最终结果按以下 JSON 结构返回给调用方：

```json
{
  "status": "success",
  "exit_code": 0,
  "summary": "任务执行摘要，由主 Agent 生成",
  "artifacts": [
    {"name": "report.md", "path": "./output/artifacts/report.md", "size": 2048}
  ],
  "stdout_log": "./output/stdout.log",
  "stderr_log": "./output/stderr.log",
  "agents_involved": ["架构师", "测试工程师"]
}
```

---

## 四、失败处理机制

### 4.1 常见失败类型与应对

| 失败场景 | 检测方式 | 处理策略 |
|----------|----------|----------|
| 输入格式错误 | 前置校验不通过 | 返回错误码 1，附带正确格式示例 |
| 环境部署失败 | 依赖安装或克隆报错 | 返回错误码 2，提示检查网络与权限 |
| Agent 执行超时 | 单个 Agent 运行超过 `--timeout` | 自动重试（次数由 `--retry` 控制），仍失败则终止 |
| 输出校验不通过 | 退出码非 0 或产出缺失 | 返回错误码 3，附上 stderr 日志路径 |

### 4.2 错误信息模板

```
[错误码 {code}] {错误类型}
原因：{具体原因描述}
解决方法：{可操作建议}
正确示例：{符合格式的输入示例}
日志位置：{stdout/stderr 文件路径}
```

### 4.3 强制终止与清理

- 若任务连续失败超过 `--retry` 上限，框架将终止后续 Agent 调度
- 所有已生成的中间文件保留在输出目录，便于排查
- 可手动删除工作目录：`rm -rf ./workspace ./output`

---

## 五、最佳实践建议

1. **任务描述越具体，结果质量越高**：建议包含背景、约束、交付物格式
2. **合理规划角色分工**：避免角色过多导致协调开销过大，常规任务 2-4 个 Agent 即可
3. **善用参数覆盖**：不同场景下的差异化配置可通过 `--params` 灵活传入
4. **定期清理输出目录**：避免历史产物干扰后续任务
5. **先小规模验证**：在完整任务前，先用小规模测试确认环境与角色配置无误

---

## 六、版本与更新说明

当前版本：1.0.0

本技能文档随框架迭代更新。若框架 CLI 参数或行为发生变化，请以 `./main --help` 输出为准，并同步更新本技能的使用方式。

---

*本文档由 AI 辅助生成，用于指导多智能体协作框架的使用。实际执行时请以命令输出为准。*

## 许可证（License）

```text
MIT License

Copyright (c) 2026 SkillForge Lab

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.
```
<!-- professional-license-embedded -->
