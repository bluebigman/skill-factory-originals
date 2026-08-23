---
slug: memsearch
name: memsearch
displayName: 记忆检索 语义搜索 跨会话持久记忆
description: 基于Markdown与Milvus的统一记忆层，为AI代理提供持久化语义检索。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: LingArchitect
agent_created: true
trigger_words: ["memsearch", "记忆检索", "语义搜索", "持久记忆", "跨会话记忆", "记忆查询", "历史回溯"]
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# memsearch — 记忆检索与语义搜索 Skill 文档

## 一、能力边界速查卡（一页纸）

### 1.1 能做什么

| 能力项 | 说明 | 输入示例 | 输出示例 |
|--------|------|----------|----------|
| 文本摄入 | 将用户提供的文本、文件内容或 URL 抓取内容解析为结构化条目 | `memsearch ingest ./notes.md` | 条目 ID、字段列表 |
| 关键信息提取 | 自动识别实体、时间、主题标签等关键字段存入记忆条目 | `memsearch extract "2024年3月与张三签订合同"` | `{entity: 张三, time: 2024-03, tag: 合同}` |
| 语义检索 | 基于自然语言查询，通过 Milvus 向量相似度召回最相关的记忆片段 | `memsearch query "去年签的供应商合同"` | 召回片段列表 + 置信度分数 |
| 置信度标注 | 对每条检索结果或提取字段给出 0~1 的置信度分数 | 自动附加 | `confidence: 0.87` |
| 批量与自定义 | 支持多条目批量写入，允许用户自定义输出字段模板 | `memsearch batch ingest ./data/ --template custom.json` | 批量处理报告 |

### 1.2 不能做什么

| 限制项 | 说明 | 替代方案 |
|--------|------|----------|
| 不执行外部系统写操作 | 不直接修改用户文件系统以外的数据库或应用状态 | 通过 API 网关中转 |
| 不保证检索绝对准确 | 语义检索基于向量相似度，存在误召回可能 | 人工复核高置信度结果 |
| 不处理非文本内容 | 图片、音视频等二进制内容需先经外部工具转文本 | 先调用 OCR/ASR 工具 |
| 不自动删除记忆 | 删除操作需用户显式指定条件或 ID | `memsearch delete --id <id>` |
| 不跨 Skill 共享状态 | 记忆库独立，不与其他 Skill 自动联动 | 通过文件导出/导入交换 |

### 1.3 适用对象

- 需要跨会话保留上下文的 AI 代理开发者
- 需要语义级检索而非关键词匹配的知识库维护者
- 需要结构化记忆管理的个人助理应用

---

## 二、触发方式与场景映射

### 2.1 触发词

直接使用以下任一词汇即可激活本 Skill：

```
memsearch | 记忆检索 | 语义搜索 | 持久记忆 | 跨会话记忆 | 记忆查询 | 历史回溯
```

### 2.2 场景映射表

| 用户说（大白话） | 实际触发动作 | 对应命令 |
|------------------|--------------|----------|
| "帮我记住上个月的项目进度" | 文本摄入 + 关键信息提取 | `memsearch ingest` + `extract` |
| "我之前提过那个客户的要求吗？" | 语义检索 | `memsearch query` |
| "把这几份文档都存进记忆库" | 批量摄入 | `memsearch batch ingest` |
| "删掉上周存的那条记录" | 显式删除 | `memsearch delete --condition "time:2024-W23"` |
| "查一下我去年所有关于合同的记录" | 语义检索 + 时间过滤 | `memsearch query "合同" --filter "time:2023"` |

---

## 三、标准操作流程

### 3.1 前置条件

| 条件 | 要求 | 检查方法 |
|------|------|----------|
| 运行环境 | Python 3.9+，Milvus 2.3+ 已启动 | `python --version` / `milvus-cli status` |
| 依赖安装 | `pip install memsearch-client` | `pip show memsearch-client` |
| 数据目录 | 待处理文件放入同一目录，命名规范一致 | `ls ./data/` |
| 配置初始化 | 首次使用需执行 `memsearch init` 生成配置文件 | `cat ~/.memsearch/config.yaml` |

### 3.2 执行步骤（分步编号）

#### 步骤 1：准备输入

```
# 将待处理文件放入同一目录，确认命名规范一致
mkdir -p ./memory_input
cp ~/documents/*.md ./memory_input/
# 检查文件命名：建议格式 YYYY-MM-DD_主题.md
```

#### 步骤 2：试运行

```
# 先用单个样本执行，核对输出字段与格式
memsearch ingest ./memory_input/2024-06-01_项目启动.md --dry-run
# 预期输出：解析后的字段列表、置信度预估、向量维度
```

#### 步骤 3：批量执行

```
# 确认无误后对全量数据执行，并保留原始文件备份
cp -r ./memory_input ./memory_input_backup
memsearch batch ingest ./memory_input/ --output ./memory_output/
```

#### 步骤 4：校验结果

```
# 抽查输出条目，核对关键字段与源数据一致
memsearch query "项目启动" --limit 5
# 检查每条结果的 source_file 字段是否指向正确文件
# 核对 entity/time/tag 字段是否与原文一致
```

### 3.3 输出规范

所有命令输出统一为 JSON 格式，包含以下字段：

```json
{
  "status": "success",
  "operation": "ingest",
  "items": [
    {
      "id": "mem_001",
      "content": "原文片段",
      "fields": {
        "entity": ["张三"],
        "time": "2024-06-01",
        "tag": ["项目", "启动"]
      },
      "confidence": 0.92,
      "source_file": "./memory_input/2024-06-01_项目启动.md"
    }
  ]
}
```

---

## 四、置信度门控机制

### 4.1 置信度分级

| 置信度范围 | 级别 | 处理方式 |
|------------|------|----------|
| 0.85 ~ 1.0 | 高置信 | 直接使用，标注绿色 |
| 0.60 ~ 0.84 | 中置信 | 使用但提示人工复核 |
| 0.40 ~ 0.59 | 低置信 | 提示"结果可能不准确" |
| 0.00 ~ 0.39 | 极低置信 | 不输出结果，建议重新表述查询 |

### 4.2 信息不足时的占位符

当提取字段信息不足时，使用 `[需核实:字段名]` 占位，不编造内容：

```
输入: "去年签了个合同"
输出: {
  "entity": "[需核实:签约方]",
  "time": "2023",
  "tag": ["合同"],
  "confidence": 0.72
}
```

### 4.3 门控规则

- 任何字段置信度低于 0.5 时，该字段自动转为 `[需核实:字段名]`
- 整条记录置信度低于 0.4 时，不写入记忆库，仅返回提示
- 查询结果中，低置信度结果排在最后并标注警告符号

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| MEM-001 | 输入文件不存在 | "未找到指定文件，请检查路径" | 确认文件路径，使用绝对路径 |
| MEM-002 | 向量维度不匹配 | "向量维度与集合定义不一致" | 检查 Milvus 集合维度配置，重建集合 |
| MEM-003 | 批量处理中断 | "批量处理在第 N 条中断" | 查看日志定位失败条目，单独重试 |
| MEM-004 | 置信度过低 | "所有候选结果置信度均低于阈值" | 调整查询表述，增加上下文关键词 |
| MEM-005 | 删除条件不明确 | "请提供明确的删除条件或 ID" | 使用 `--id` 或 `--condition` 参数 |
| MEM-006 | Milvus 连接失败 | "无法连接到 Milvus 服务" | 检查服务状态，确认端口和认证信息 |

---

## 六、FAQ 与反模式对照

### 6.1 常见坑

| 坑 | 反模式（错误做法） | 正模式（正确做法） |
|----|-------------------|-------------------|
| 数据格式混乱 | 直接摄入未格式化的原始文本 | 先统一为 Markdown 格式，添加元数据头 |
| 查询表述模糊 | 查询"那个东西" | 查询"2024年签订的供应商框架协议" |
| 忽略置信度 | 直接采用所有检索结果 | 根据置信度分级决定是否人工复核 |
| 批量处理无备份 | 直接对原始文件批量处理 | 先复制备份，再执行批量操作 |
| 删除操作随意 | 使用模糊条件删除 | 先查询确认 ID，再精确删除 |

### 6.2 反模式对照表

| 反模式 | 问题 | 替代方案 |
|--------|------|----------|
| 把 memsearch 当数据库用 | 语义检索≠精确查询，可能漏召回 | 需要精确查询时使用传统数据库 |
| 期望跨 Skill 自动同步 | 记忆库独立设计 | 通过文件导出/导入手动同步 |
| 依赖检索结果做关键决策 | 向量相似度存在误召回 | 高价值场景必须人工复核 |
| 忽略字段置信度 | 低置信度字段可能错误 | 使用 `[需核实:字段]` 占位符 |

---

## 七、渐进式披露路径

### 7.1 速查卡（30 秒上手）

```
# 初始化
memsearch init

# 单条摄入
memsearch ingest "文本内容"

# 查询
memsearch query "自然语言查询"

# 查看帮助
memsearch --help
```

### 7.2 新手路径（首次使用）

1. 执行 `memsearch init` 完成初始化
2. 使用 `memsearch ingest` 摄入 3-5 条测试文本
3. 使用 `memsearch query` 验证检索效果
4. 查看输出 JSON 中的 confidence 字段理解置信度
5. 阅读本文档第三节了解完整流程

### 7.3 进阶路径（熟练用户）

1. 自定义字段模板：创建 `custom_template.json` 定义输出字段
2. 批量处理优化：使用 `--batch-size` 和 `--parallel` 参数
3. 过滤查询：使用 `--filter` 参数按时间/标签过滤
4. 数据导出：使用 `memsearch export` 导出记忆库为 Markdown
5. 性能调优：调整 Milvus 索引参数（HNSW_M、efConstruction）

---

## 八、参数参考表

### 8.1 全局参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `--config` | string | `~/.memsearch/config.yaml` | 配置文件路径 |
| `--verbose` | bool | false | 输出详细日志 |
| `--output-format` | string | json | 输出格式（json/yaml） |
| `--timeout` | int | 30 | 请求超时时间（秒） |

### 8.2 摄入参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `--dry-run` | bool | false | 试运行，不写入记忆库 |
| `--template` | string | 默认模板 | 自定义字段模板路径 |
| `--extract-fields` | bool | true | 是否自动提取关键字段 |
| `--chunk-size` | int | 500 | 文本分块大小（字符） |

### 8.3 查询参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `--limit` | int | 10 | 返回结果数量上限 |
| `--filter` | string | 无 | 过滤条件（如 `time:2023`） |
| `--min-confidence` | float | 0.4 | 最低置信度阈值 |
| `--include-fields` | bool | true | 是否返回结构化字段 |

---

## 九、用户协议

<!-- user-agreement-injected -->

**使用本 Skill 即表示您同意以下条款：**

1. **责任承担**：使用者自行承担全部责任。本 Skill 提供的检索结果仅供参考，不构成任何形式的专业建议或决策依据。因使用本 Skill 产生的任何直接或间接损失，Skill 作者及贡献者不承担任何责任。

2. **禁止反向工程**：禁止对本 Skill 的代码、算法、模型权重进行反向工程、反编译、破解或任何形式的未授权访问。禁止移除或篡改本 Skill 中的任何版权声明、水印或标识。

3. **数据安全**：使用者应自行确保输入数据的合法性与安全性。本 Skill 不承担数据泄露、丢失或损坏的责任。

4. **合规使用**：使用者应遵守所在地法律法规，不得将本 Skill 用于任何非法目的，包括但不限于侵犯他人隐私、知识产权或商业机密。

5. **服务变更**：本 Skill 可能随时更新或终止服务，恕不另行通知。

---

## 十、许可证（License）

<!-- professional-license-embedded -->

**MIT License**

Copyright (c) 2024 原创作者（自持版权）

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
