---
slug: graphify
name: graphify
displayName: 代码知识图谱 结构解析 智能问答
description: 将代码库、文档、SQL结构、配置和PDF转化为可查询的知识图谱，实现代码问答与可视化分析。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: LingGraph Studio
agent_created: true
trigger_words: ["graphify", "知识图谱", "代码图谱", "代码问答", "图谱构建", "代码关系分析", "结构可视化"]
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# graphify — 代码知识图谱构建与查询 Skill 文档

## 一、能力边界速查卡

### 1.1 能做什么

| 能力项 | 说明 | 典型输入 | 典型输出 |
|--------|------|----------|----------|
| 代码图谱构建 | 解析源码文件，提取函数、类、调用关系 | `graphify index ./src` | 图谱 JSON 文件 |
| 文档图谱化 | 将 Markdown/PDF 文档转为实体关系图 | `graphify index ./docs --type doc` | 文档实体节点与链接 |
| SQL 结构解析 | 提取表、字段、外键关系 | `graphify index schema.sql --type sql` | 数据库结构图谱 |
| 配置依赖分析 | 解析配置文件中的依赖项 | `graphify index config.yaml --type config` | 配置依赖图 |
| 增量索引 | 只处理变更文件，节省时间 | `graphify index --incremental` | 增量更新后的图谱 |
| 图谱合并 | 合并多个图谱文件 | `graphify merge --graphs a.json,b.json` | 合并后的图谱 |
| 可视化导出 | 导出 D3.js 可渲染格式 | `graphify export --format d3` | HTML/JSON 可视化文件 |
| 代码问答 | 基于图谱回答代码结构问题 | `graphify query "哪些函数调用了 db.connect?"` | 调用链列表 |

### 1.2 不能做什么

| 限制项 | 说明 |
|--------|------|
| 不执行代码 | 只做静态分析，不运行程序 |
| 不保证语义理解 | 图谱基于结构关系，不包含业务语义 |
| 不处理加密文件 | 无法解析加密或二进制混淆的源码 |
| 不支持实时监控 | 需手动触发索引更新 |
| 不替代调试工具 | 不提供运行时堆栈或内存分析 |

### 1.3 适用对象

- **开发者**：快速理解陌生代码库结构
- **技术文档作者**：将文档转化为可导航的知识网络
- **数据库管理员**：可视化表关系与依赖
- **架构师**：分析模块间耦合度与调用链

---

## 二、触发方式与场景映射

### 2.1 触发词

| 触发词 | 使用场景 |
|--------|----------|
| `graphify` | 直接调用工具主命令 |
| `知识图谱` | 需要构建或查询图谱时 |
| `代码图谱` | 针对代码库的结构分析 |
| `代码问答` | 询问代码关系、调用链时 |
| `图谱构建` | 从零开始创建图谱 |
| `代码关系分析` | 分析模块依赖、函数调用 |
| `结构可视化` | 需要图形化展示结构 |

### 2.2 场景映射表

| 用户说（大白话） | 实际执行动作 |
|------------------|--------------|
| "帮我看看这个项目里哪些文件互相依赖" | `graphify index ./project && graphify query "依赖关系"` |
| "这个函数被谁调用了？" | `graphify query "callers of <function_name>"` |
| "数据库表之间怎么关联的？" | `graphify index schema.sql --type sql && graphify export --format d3` |
| "文档里提到的概念之间有什么关系？" | `graphify index ./docs --type doc` |
| "我只想更新改过的文件" | `graphify index --incremental` |

---

## 三、标准执行流程

### 3.1 前置条件

| 条件 | 要求 | 验证方法 |
|------|------|----------|
| 环境变量 | 已设置 `GRAPHIFY_API_KEY`（如使用 LLM 增强） | `echo $GRAPHIFY_API_KEY` |
| 输入文件 | 源码/文档/SQL 文件路径存在 | `ls <path>` |
| 输出目录 | 有写权限 | `touch .graphify_test && rm .graphify_test` |
| 配置文件 | `graphify.yaml` 存在（可选） | `cat graphify.yaml` |

### 3.2 执行步骤

#### 步骤 1：初始化配置（可选）

```bash
graphify init
```

生成默认 `graphify.yaml`，可自定义 `custom_extractors`：

```yaml
custom_extractors:
  - name: "api_endpoint"
    pattern: "\\@(get|post|put|delete)\\(['\"]([^'\"]+)['\"]\\)"
    type: "endpoint"
```

#### 步骤 2：构建图谱

```bash
graphify index <path> [--type <code|doc|sql|config>] [--incremental]
```

参数说明：

| 参数 | 可选值 | 默认值 | 说明 |
|------|--------|--------|------|
| `--type` | `code`, `doc`, `sql`, `config` | `code` | 输入类型 |
| `--incremental` | 无 | 关闭 | 增量模式 |
| `--output` | 文件路径 | `graph.json` | 输出文件 |
| `--depth` | 整数 | 3 | 递归深度 |

#### 步骤 3：查询图谱

```bash
graphify query "<问题>"
```

示例查询：

```bash
graphify query "列出所有调用 db.connect 的函数"
graphify query "模块 A 和模块 B 之间的依赖"
graphify query "哪些表有外键指向 users 表"
```

#### 步骤 4：合并图谱（可选）

```bash
graphify merge --graphs a.json,b.json --output merged.json
```

#### 步骤 5：导出可视化

```bash
graphify export --format d3 --input graph.json --output graph.html
```

支持格式：`d3`（默认）、`json`、`csv`、`graphml`。

### 3.3 输出规范

| 输出类型 | 格式 | 示例 |
|----------|------|------|
| 查询结果 | 文本列表 | `auth.py:login (连接数: 87)` |
| 图谱文件 | JSON | `{"nodes": [...], "edges": [...]}` |
| 可视化 | HTML | 自包含 D3.js 页面 |
| 错误信息 | 标准错误码 | `E1001: 文件不存在` |

---

## 四、置信度门控

当信息不足时，**不得编造**。使用以下占位符：

| 场景 | 占位符 | 示例 |
|------|--------|------|
| 函数参数不明确 | `[需核实:参数列表]` | `db.connect([需核实:参数列表])` |
| 调用关系不确定 | `[需核实:调用方]` | `[需核实:调用方] -> db.connect` |
| 文件路径缺失 | `[需核实:路径]` | `import [需核实:路径]` |
| 配置值未确认 | `[需核实:配置值]` | `timeout: [需核实:配置值]` |

**门控规则**：

1. 若图谱中不存在某节点，返回 `[需核实:节点不存在]` 而非猜测。
2. 若查询条件模糊，返回最接近的 3 个结果并标注 `[需核实:可能相关]`。
3. 若增量索引检测到文件变更但未重新索引，提示 `[需核实:索引过期]`。

---

## 五、错误码体系

| 错误码 | 含义 | 用户提示话术 | 修正步骤 |
|--------|------|--------------|----------|
| `E1001` | 输入路径不存在 | "指定的路径未找到，请检查路径是否正确。" | 1. 确认路径存在 2. 使用绝对路径重试 |
| `E1002` | 文件格式不支持 | "该文件类型不在支持列表中（code/doc/sql/config）。" | 1. 转换文件格式 2. 使用 `--type` 指定类型 |
| `E1003` | 图谱文件损坏 | "图谱文件无法解析，可能已损坏或版本不兼容。" | 1. 重新索引 2. 检查 JSON 格式 |
| `E2001` | API 密钥缺失 | "未检测到 GRAPHIFY_API_KEY，LLM 增强功能不可用。" | 1. 设置环境变量 2. 或使用纯规则模式 |
| `E2002` | 增量索引冲突 | "检测到文件变更与现有图谱冲突。" | 1. 删除旧图谱 2. 执行全量索引 |
| `E3001` | 导出格式不支持 | "指定的导出格式不可用。" | 1. 使用 `--help` 查看支持格式 2. 选择正确格式 |
| `E3002` | 合并图谱版本不匹配 | "待合并的图谱版本不一致，无法合并。" | 1. 使用相同版本生成图谱 2. 或手动转换格式 |

---

## 六、FAQ 反模式对照

### 常见坑 1：忽略增量索引

**反模式**：每次全量索引，耗时且浪费资源。

**正确做法**：

```bash
graphify index ./src --incremental
```

### 常见坑 2：查询时未指定类型

**反模式**：`graphify query "users"` 返回大量无关结果。

**正确做法**：

```bash
graphify query "type:table name:users"
```

### 常见坑 3：合并图谱前未检查版本

**反模式**：合并后出现节点丢失或关系错乱。

**正确做法**：

```bash
graphify merge --graphs a.json,b.json --check-version
```

### 常见坑 4：自定义提取器正则错误

**反模式**：正则写错导致提取不到任何节点。

**正确做法**：先用 `graphify test-extractor --pattern "<regex>"` 验证。

### 常见坑 5：忽略置信度占位符

**反模式**：直接输出猜测结果，误导用户。

**正确做法**：保留 `[需核实:...]` 占位符，并提示用户补充信息。

---

## 七、渐进式披露路径

### 7.1 新手速查路径（5 分钟上手）

1. 运行 `graphify --selftest` 验证安装
2. 运行 `graphify index ./demo` 构建第一个图谱
3. 运行 `graphify query "列出所有函数"` 查看结果
4. 运行 `graphify export --format d3` 生成可视化

### 7.2 进阶路径（深度使用）

1. 阅读 `graphify.yaml` 配置文档，自定义提取规则
2. 使用 `--incremental` 建立持续索引流程
3. 编写脚本批量合并多个项目图谱
4. 将 D3 导出嵌入到内部文档系统

### 7.3 专家路径（扩展开发）

1. 研究 `custom_extractors` 的正则语法，支持更多语言
2. 使用 `graphify merge` 构建跨项目依赖图
3. 结合 CI/CD 流水线，每次提交自动更新图谱

---

## 八、用户协议

<!-- user-agreement-injected -->

**使用本 Skill 即表示您同意以下条款：**

1. **责任承担**：使用者应自行承担使用本 Skill 的全部责任。因使用本 Skill 导致的任何直接或间接损失，包括但不限于数据丢失、业务中断、法律纠纷，本 Skill 作者及贡献者不承担任何责任。

2. **禁止反向工程**：不得对本 Skill 的底层实现进行反向工程、反编译、破解或试图提取源代码（除非适用法律允许）。

3. **合规使用**：使用者应确保使用本 Skill 的行为符合当地法律法规及所在组织的政策要求。

4. **数据安全**：使用者应自行负责输入数据的合法性和安全性，不得输入包含敏感信息或违反法律的内容。

5. **无担保声明**：本 Skill 按"现状"提供，不附带任何明示或暗示的担保，包括但不限于适销性、特定用途适用性和非侵权保证。

---

## 九、许可证（License）

<!-- professional-license-embedded -->

### MIT License

Copyright (c) 2024 LingGraph Studio

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

*本文档由 AI 辅助生成，仅供参考。使用前请阅读相关文档并验证功能。*
