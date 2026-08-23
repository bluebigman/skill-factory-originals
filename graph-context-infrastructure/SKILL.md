---
slug: graph-context-infrastructure
name: graph-context-infrastructure
displayName: 文本转图 上下文管理 知识基建
description: 将文本自动转为图数据，支撑上下文管理与AI问责基础设施。
version: 1.0.0
license: MIT
source_project: original
source_url: ""
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 图基建工坊
agent_created: true
trigger_words: ["图数据库", "上下文管理", "图基础设施", "semantica", "ai问责", "--selftest", "--version", "知识图谱", "实体关系抽取"]
---

> 本内容由 AI 生成，仅供学习参考 <!-- ai-generated-notice -->

> 本 Skill 由 AI 辅助生成，仅供参考。使用前请阅读「用户协议」章节。

# 文本转图 · 上下文管理基建（graph-context-infrastructure）

## 一、能力边界（一页纸速查卡）

| 维度 | 说明 |
|------|------|
| **核心能力** | 将纯文本内容解析为结构化图数据（节点 + 边），输出标准 JSON，供下游图数据库（如 Neo4j）或上下文管理中间件消费 |
| **输入要求** | UTF-8 编码的纯文本文件（`.txt`、`.md`、`.log` 等），单文件建议不超过 500KB；超出请先切片 |
| **输出格式** | 严格遵循 JSON Schema（见「五、输出规范」），包含 `nodes` 与 `edges` 两个顶层数组 |
| **可调参数** | `--min-confidence`（置信度阈值，默认 0.6，范围 0.0~1.0）、`--config`（自定义实体类型配置） |
| **不能做的事** | ① 不处理图片/PDF/扫描件中的文字；② 不执行跨文档实体消歧（同一实体在不同文件中的指代合并需自行处理）；③ 不提供图数据库部署服务；④ 不保证实体识别覆盖率（受限于输入文本质量与领域词典） |
| **适用对象** | 需要快速搭建文本→图数据管线的开发者、需要为 AI 对话系统构建上下文记忆层的工程师、需要审计 AI 决策依据（问责）的合规人员 |

---

## 二、触发方式与场景映射

当你的任务涉及以下任一场景时，可调用本 Skill：

| 大白话场景 | 触发词示例 | 使用方式 |
|------------|------------|----------|
| "把这段聊天记录变成关系图" | 图数据库、上下文管理 | 将文本保存为 `.txt`，运行主脚本 |
| "我想看 AI 决策时参考了哪些知识" | ai问责、semantica | 对 AI 的提示词/上下文日志执行转换，分析 `edges` 中的引用关系 |
| "给知识库建索引结构" | 知识图谱、实体关系抽取 | 批量处理文档，合并输出 JSON 后导入 Neo4j |
| "检查工具是否正常" | --selftest | 直接运行自检命令 |
| "确认版本号" | --version | 直接运行版本命令 |

---

## 三、标准流程

### 前置条件

1. Python ≥ 3.8（`python --version` 验证）
2. 已下载 Skill 源码至本地目录，目录结构完整（含 `main.py`、`config.example.json`、`examples/`）
3. （可选）如需导入 Neo4j，请自行安装社区版并准备 Cypher Shell

### 执行步骤

1. **准备输入文件**：将待处理文本保存为 `.txt` 文件，编码为 UTF-8。
2. **（可选）自定义配置**：复制 `config.example.json` 为 `config.json`，按需修改 `entity_types` 列表（见「八、配置与扩展」）。
3. **运行转换命令**：

   ```bash
   python main.py --input your_text.txt --output result.json
   ```

   常用参数组合：

   ```bash
   # 调整置信度阈值（降低阈值→更多实体但噪声增加）
   python main.py --input your_text.txt --output result.json --min-confidence 0.4

   # 使用自定义配置
   python main.py --input your_text.txt --output result.json --config config.json
   ```

4. **检查输出**：打开 `result.json`，确认 `nodes` 与 `edges` 结构完整（见「五、输出规范」）。
5. **（可选）导入 Neo4j**：使用 Cypher 语句批量导入，示例：

   ```cypher
   // 导入节点（示例，需按实际字段调整）
   LOAD CSV FROM 'file:///nodes.csv' AS row
   CREATE (:Entity {id: row[0], type: row[1], name: row[2]});
   ```

### 输出规范

输出 JSON 顶层结构：

```json
{
  "schema_version": "1.0",
  "meta": {
    "source_file": "your_text.txt",
    "processed_at": "2025-01-01T12:00:00Z",
    "min_confidence": 0.6,
    "total_nodes": 12,
    "total_edges": 18
  },
  "nodes": [
    {
      "id": "n1",
      "type": "PERSON",
      "name": "张三",
      "confidence": 0.92,
      "properties": {
        "mention_count": 3,
        "first_seen": "第2段"
      }
    }
  ],
  "edges": [
    {
      "id": "e1",
      "source": "n1",
      "target": "n2",
      "relation": "WORKS_AT",
      "confidence": 0.85,
      "evidence": "张三任职于某某公司"
    }
  ]
}
```

---

## 四、置信度门控

本 Skill 采用**置信度门控**机制，防止低质量信息污染下游系统：

- 每个节点和边均附带 `confidence` 字段（0.0~1.0）。
- 低于 `--min-confidence` 阈值的实体/关系**不会出现在输出中**。
- 当输入文本信息不足（如实体名称缺失、关系证据不明确）时，输出中对应字段使用占位符 `[需核实:字段名]`，**绝不编造**。

示例：

```json
{
  "id": "n7",
  "type": "ORGANIZATION",
  "name": "[需核实:组织名称]",
  "confidence": 0.55
}
```

**设计过滤策略建议**：

| 场景 | 建议阈值 | 说明 |
|------|----------|------|
| 快速预览 | 0.4 | 召回优先，容忍噪声 |
| 标准使用 | 0.6（默认） | 平衡召回与精确 |
| 审计/问责 | 0.8 | 精确优先，仅保留高置信证据 |

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| `E001` | 输入文件不存在 | `[错误] 找不到输入文件: xxx` | 检查文件路径是否正确，确认文件已保存 |
| `E002` | 输入文件编码非 UTF-8 | `[错误] 文件编码不支持，请转换为 UTF-8` | 使用 `iconv` 或文本编辑器另存为 UTF-8 |
| `E003` | 配置文件 JSON 解析失败 | `[错误] 配置文件格式错误，请检查 JSON 语法` | 使用 JSON 校验工具检查 `config.json` |
| `E004` | 置信度阈值超出范围 | `[错误] --min-confidence 必须在 0.0~1.0 之间` | 重新传入合法阈值 |
| `E005` | 输出目录不可写 | `[错误] 无法写入输出文件，请检查目录权限` | 更换输出路径或调整目录权限 |
| `E006` | 输入文本为空 | `[警告] 输入文本为空，输出空图` | 检查源文件内容 |

---

## 六、FAQ 与反模式

| 常见坑 | 反模式（错误做法） | 正确做法 |
|--------|-------------------|----------|
| **忽略置信度** | 直接使用默认阈值，不根据场景调整 | 先跑一次默认参数，观察输出质量，再按需调整 |
| **跨文件实体不合并** | 多个文件分别生成 JSON 后直接拼接，导致同一实体出现多个节点 | 编写脚本按实体名称+类型做合并，或使用图数据库的 MERGE 语句 |
| **输入文本质量差** | 将 OCR 乱码或口语化文本直接输入，期望高精度输出 | 先做文本清洗（去重、纠错、分段），再执行转换 |
| **过度依赖默认配置** | 不自定义实体类型，导致领域专有名词无法识别 | 编辑 `config.json`，添加领域实体类型（见「八」） |
| **把输出当绝对事实** | 将图数据直接用于决策，不验证 `confidence` 与 `evidence` | 对低置信度节点进行人工复核，或提高阈值 |

---

## 七、渐进式披露（分层次阅读路径）

### 速查卡（30 秒上手）

```bash
# 1. 运行自检
python main.py --selftest

# 2. 转换文本
python main.py --input doc.txt --output graph.json

# 3. 查看结果
cat graph.json
```

### 新手路径（首次使用）

1. 阅读「一、能力边界」确认工具是否匹配需求。
2. 运行 `--selftest` 验证环境。
3. 使用 `examples/` 下的示例文件跑通一次完整流程。
4. 查看输出 JSON，理解 `nodes` 与 `edges` 结构。

### 进阶路径（深度使用）

1. 阅读「四、置信度门控」，设计过滤策略。
2. 编写脚本批量处理多个文件，合并输出（注意实体消歧）。
3. 将 JSON 导入 Neo4j，编写 Cypher 查询分析关系。
4. 自定义实体类型（通过配置文件指定关注的类型）。
5. 调整置信度阈值，平衡召回率与精确率。

---

## 八、配置与扩展

配置文件 `config.json` 示例：

```json
{
  "entity_types": [
    "PERSON",
    "ORGANIZATION",
    "LOCATION",
    "DATE",
    "PRODUCT",
    "CUSTOM_TYPE"
  ],
  "relation_types": [
    "WORKS_AT",
    "LOCATED_IN",
    "MENTIONS",
    "CUSTOM_RELATION"
  ],
  "language": "zh",
  "max_entities_per_doc": 500
}
```

**自定义实体类型**：在 `entity_types` 数组中添加新类型名称，系统将尝试识别该类型。注意：新增类型需要提供至少 3 个示例样本（在 `examples/` 下新建 `.txt` 文件并标注），否则识别效果可能不理想。

---

## 九、自检与版本

```bash
# 运行自检（验证环境与依赖）
python main.py --selftest

# 查看版本
python main.py --version
```

自检内容包括：Python 版本检查、依赖库导入、示例文本转换、输出 JSON 格式校验。

---

## 十、用户协议

**请在使用本 Skill 前仔细阅读以下条款，使用即视为同意全部内容：**

1. **责任承担**：使用者自行承担因使用本 Skill 产生的全部责任。本 Skill 提供的输出结果仅供参考，不构成任何形式的专业建议或保证。
2. **禁止反向工程**：使用者不得对本 Skill 的底层算法、模型权重或核心逻辑进行反向工程、反编译或试图提取源代码（除开源部分外）。
3. **数据安全**：使用者应确保输入数据不包含敏感个人信息或受法律保护的机密数据。因输入数据引发的合规问题由使用者自行负责。
4. **无担保声明**：本 Skill 按"原样"提供，不附带任何明示或暗示的担保，包括但不限于适销性、特定用途适用性和非侵权保证。
5. **合规使用**：使用者应遵守所在地法律法规，不得将本 Skill 用于任何非法用途。

<!-- user-agreement-injected -->

---

## 十一、许可证（License）

本 Skill 采用 MIT 许可证发布：

```
MIT License

Copyright (c) 2025 原创作者（自持版权）

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
