---
slug: ai-rules-sync
name: ai-rules-sync
displayName: 配置同步 规则治理 技能编排
description: 解析、同步与管理AI规则、技能、命令及子代理配置，支持批量处理与格式标准化。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 流云架构师
agent_created: true
trigger_words: ["ai-rules-sync", "同步规则", "管理AI配置", "分享技能", "规则同步", "配置治理", "技能编排"]
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# ai-rules-sync 技能文档

## 一、能力边界速查卡

### 1.1 工具定位

ai-rules-sync 是一个面向 AI 配置资产的解析与同步工具。它读取各类 AI 规则文件、技能定义、命令脚本和子代理配置，将其转换为结构化的 JSON 格式，并支持批量处理、字段定制和格式标准化。

### 1.2 能做与不能做

| 维度 | 能做 | 不能做 |
|------|------|--------|
| 文件解析 | 单文件解析、目录批量解析 | 解析加密或二进制格式文件 |
| 输出控制 | 定制输出字段、JSON 格式化 | 输出为 PDF/Word 等非结构化格式 |
| 配置管理 | 字段映射、Schema 扩展 | 自动修复源文件中的逻辑错误 |
| 集成能力 | CI/CD 脚本调用、团队协作平台对接 | 直接修改远端仓库配置 |
| 质量评估 | 输出 confidence 置信度指标 | 保证解析结果 100% 准确 |

### 1.3 适用对象

- **AI 平台运维人员**：需要批量管理多套 AI 规则配置
- **技能开发者**：需要标准化技能定义格式并分享
- **DevOps 工程师**：需要将 AI 配置纳入 CI/CD 流水线
- **技术管理者**：需要掌握团队 AI 配置资产全景

---

## 二、触发方式与场景映射

### 2.1 触发词

| 触发词 | 使用场景 |
|--------|----------|
| `ai-rules-sync` | 直接调用工具主命令 |
| `同步规则` | 需要将本地规则文件同步到统一格式时 |
| `管理AI配置` | 需要查看或整理 AI 配置资产时 |
| `分享技能` | 需要将技能定义导出为标准格式时 |
| `规则同步` | 批量处理多个规则文件时 |
| `配置治理` | 需要规范化团队配置管理流程时 |
| `技能编排` | 需要整合多个子代理配置时 |

### 2.2 场景示例

**场景一**：你有一个包含 50 个 AI 规则文件的目录，需要统一检查格式并生成报告。

**场景二**：你编写了一个新的技能定义，需要验证其结构是否符合标准 Schema。

**场景三**：你的团队使用多个 AI 子代理，需要将它们的配置统一管理并纳入版本控制。

---

## 三、标准操作流程

### 3.1 前置条件

- 已安装 ai-rules-sync 工具（版本 ≥ 1.0.0）
- 待解析的配置文件为文本格式（YAML、JSON、TOML 或 Markdown）
- 具备目标文件或目录的读取权限

### 3.2 执行步骤

#### 步骤一：单文件解析

```bash
ai-rules-sync <file-path>
```

**示例**：

```bash
ai-rules-sync ./rules/agent-rules.yaml
```

**输出示例**：

```json
{
  "file": "./rules/agent-rules.yaml",
  "format": "yaml",
  "parsed": true,
  "confidence": 0.92,
  "fields": {
    "name": "customer-support-agent",
    "version": "2.1.0",
    "permissions": ["read", "write"],
    "model": "gpt-4o"
  }
}
```

#### 步骤二：定制输出字段

使用 `--fields` 参数减少信息噪音：

```bash
ai-rules-sync ./rules/agent-rules.yaml --fields name,version,confidence
```

**输出示例**：

```json
{
  "name": "customer-support-agent",
  "version": "2.1.0",
  "confidence": 0.92
}
```

#### 步骤三：批量处理目录

```bash
ai-rules-sync --batch ./configs/
```

**输出示例**：

```json
{
  "summary": {
    "total_files": 25,
    "parsed_success": 23,
    "parsed_failed": 2,
    "avg_confidence": 0.87
  },
  "results": [
    {
      "file": "./configs/rule-01.yaml",
      "status": "success",
      "confidence": 0.95
    },
    {
      "file": "./configs/rule-02.json",
      "status": "failed",
      "error_code": "E-1003"
    }
  ]
}
```

#### 步骤四：自定义字段映射

使用 `mapping` 参数实现字段名转换：

```bash
ai-rules-sync ./rules/legacy-rule.yaml --mapping old_name:name,old_version:version
```

#### 步骤五：CI/CD 集成

在流水线脚本中调用：

```bash
#!/bin/bash
# 在 CI 中验证所有配置文件的格式
ai-rules-sync --batch ./configs/ --strict
if [ $? -ne 0 ]; then
  echo "配置格式校验失败"
  exit 1
fi
```

### 3.3 输出规范

所有输出均为 UTF-8 编码的 JSON 格式，包含以下核心字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| `file` | string | 源文件路径 |
| `format` | string | 检测到的文件格式 |
| `parsed` | boolean | 是否解析成功 |
| `confidence` | number | 解析置信度（0.0 - 1.0） |
| `fields` | object | 解析出的配置字段 |
| `error_code` | string | 失败时的错误码 |

---

## 四、置信度门控机制

### 4.1 置信度说明

`confidence` 字段反映解析结果的可靠程度。当以下情况出现时，置信度会降低：

- 源文件格式不规范（如 YAML 缩进错误）
- 字段类型与 Schema 定义不符
- 存在多个同名但类型不同的字段

### 4.2 信息不足处理

当解析器无法确定某个字段的值时，不会编造数据，而是输出占位符：

```json
{
  "fields": {
    "model": "[需核实:model]",
    "permissions": "[需核实:permissions]"
  }
}
```

### 4.3 置信度阈值建议

| 置信度范围 | 建议操作 |
|------------|----------|
| 0.9 - 1.0 | 可直接使用 |
| 0.7 - 0.9 | 人工复核关键字段 |
| 0.5 - 0.7 | 需手动修正后使用 |
| < 0.5 | 建议重新编写源文件 |

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| E-1001 | 文件不存在 | "无法找到指定文件，请检查路径" | 确认文件路径是否正确 |
| E-1002 | 文件格式不支持 | "不支持的文件格式，仅支持 YAML/JSON/TOML/Markdown" | 转换文件格式后重试 |
| E-1003 | 解析语法错误 | "文件存在语法错误，请检查格式" | 使用格式校验工具检查源文件 |
| E-1004 | Schema 校验失败 | "字段结构与 Schema 定义不匹配" | 对照 Schema 文档修正字段 |
| E-1005 | 批量处理中断 | "批量处理过程中发生异常，已停止" | 查看错误详情，修复后重试 |
| E-1006 | 权限不足 | "没有读取该文件的权限" | 检查文件权限设置 |
| E-1007 | 输出目录不可写 | "无法写入输出文件" | 检查输出目录写入权限 |

---

## 六、FAQ 与反模式对照

### 6.1 常见问题

**Q1：为什么我的 YAML 文件解析失败？**

A：最常见的原因是缩进不一致。YAML 对缩进敏感，请确保使用统一数量的空格（推荐 2 空格）进行缩进，不要混用 Tab 和空格。

**Q2：confidence 值偏低怎么办？**

A：检查源文件是否符合 Schema 规范，特别是字段类型和必填项。也可以使用 `--strict` 模式获取更详细的校验信息。

**Q3：批量处理时部分文件失败，如何定位？**

A：查看输出中的 `results` 数组，每个失败项都会包含 `error_code` 和文件路径，根据错误码表逐一排查。

### 6.2 反模式对照

| 反模式 | 问题描述 | 正确做法 |
|--------|----------|----------|
| 忽略置信度 | 直接使用低置信度的解析结果 | 设置置信度阈值，低于阈值时人工介入 |
| 手动修改输出 | 直接编辑 JSON 输出文件 | 修改源文件后重新解析 |
| 无版本管理 | 配置文件不纳入版本控制 | 将配置文件和解析脚本一并纳入 Git |
| 跳过错误 | 批量处理时忽略失败项 | 使用 `--strict` 模式让失败项中断流程 |
| 重复解析 | 每次使用都重新解析同一批文件 | 缓存解析结果，仅在源文件变更时重新解析 |

---

## 七、渐进式学习路径

### 7.1 新手入门（5 分钟上手）

1. 阅读本速查卡，了解工具能力边界
2. 执行单文件解析：`ai-rules-sync <file>`
3. 查看 JSON 输出，理解基本结构
4. 使用 `--fields` 定制输出，减少信息噪音
5. 检查 `confidence` 字段，了解解析质量
6. 阅读错误码表，掌握常见问题处理

### 7.2 进阶应用（1 小时掌握）

1. 学习 `mapping` 参数，实现自定义字段映射
2. 使用 `--batch` 处理整个目录，并分析 `summary` 报告
3. 编写 CI/CD 集成脚本，将同步流程自动化
4. 扩展 Schema 支持自定义配置类型
5. 集成到团队协作平台，实现配置版本管理

### 7.3 专家模式（深度定制）

1. 自定义 Schema 定义，支持私有配置类型
2. 编写插件，扩展解析器功能
3. 构建配置质量监控面板
4. 实现配置变更自动通知机制

---

## 八、参数速查表

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `<file>` | string | 无 | 待解析的文件路径 |
| `--batch <dir>` | string | 无 | 批量解析目录 |
| `--fields <list>` | string | 全部 | 逗号分隔的输出字段列表 |
| `--mapping <pairs>` | string | 无 | 字段映射，格式 `old:new,old2:new2` |
| `--strict` | boolean | false | 严格模式，遇错即停 |
| `--selftest` | boolean | false | 运行自检 |
| `--version` | boolean | false | 显示版本号 |

---

## 用户协议

<!-- user-agreement-injected -->

**使用前请仔细阅读以下条款，使用本 Skill 即视为同意本协议。**

1. **责任承担**：使用者应自行承担使用本 Skill 的全部责任。因使用本 Skill 而产生的任何直接或间接损失，包括但不限于数据丢失、业务中断、系统故障等，本 Skill 作者不承担任何责任。

2. **禁止反向工程**：未经授权，不得对本 Skill 进行反向工程、反编译、破解或试图提取源代码。

3. **合规使用**：使用者应确保使用本 Skill 的行为符合当地法律法规及所在组织的相关规定。

4. **无担保声明**：本 Skill 按"现状"提供，不附带任何明示或暗示的担保，包括但不限于适销性、特定用途适用性和非侵权性保证。

---

## 许可证（License）

<!-- professional-license-embedded -->

### MIT License

Copyright (c) 2024 流云架构师

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
