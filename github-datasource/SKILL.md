---
slug: github-datasource
name: github-datasource
displayName: 代码仓数据接入 结构化解析 批量处理
description: 将Git代码仓数据、文件与URL转化为结构化结果，支持批量处理与置信度标注。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: DataFlow Architect
agent_created: true
trigger_words: ["github datasource", "Git代码管理", "数据可视化", "仓库数据接入", "代码仓解析", "仓库数据提取", "Git数据转换"]
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# SKILL.md — github-datasource

## 一、能力边界（一页纸速查卡）

### 1.1 能做什么

| 能力项 | 说明 | 输入示例 | 输出示例 |
|--------|------|----------|----------|
| 单文件解析 | 将单个代码文件转为结构化字段 | `src/utils/date.ts` | `{path, language, loc, functions[]}` |
| 目录批量处理 | 递归扫描目录下全部代码文件 | `./repo/src/` | `[{path, ...}, ...]` |
| URL 抓取解析 | 从公开仓库 URL 拉取文件并解析 | `https://github.com/user/repo/blob/main/readme.md` | `{url, content, meta}` |
| 置信度标注 | 对每个输出字段标注可信程度 | 任意输入 | `{field: value, confidence: 0.95}` |
| 格式转换 | 将解析结果输出为 JSON / CSV / Markdown 表格 | 解析后的结构化数据 | 指定格式的文本 |

### 1.2 不能做什么（明确拒绝）

| 禁止事项 | 原因 |
|----------|------|
| 不执行代码、不运行测试 | 本 Skill 仅做静态解析，不涉及运行时行为 |
| 不访问私有仓库 | 无认证机制，仅支持公开数据 |
| 不修改源文件 | 只读操作，输出结果不写回原仓库 |
| 不推断业务逻辑 | 只提取结构信息，不做语义理解 |
| 不处理二进制文件 | 仅支持文本类代码文件 |

### 1.3 适用对象

- 需要快速了解仓库结构的开发者
- 需要将代码数据导入可视化工具的分析师
- 需要批量整理代码清单的文档维护者
- 需要从公开 URL 提取代码片段的学习者

---

## 二、触发方式

### 2.1 触发词速查

| 触发词 | 场景描述 |
|--------|----------|
| `github datasource` | 直接调用本 Skill 的主命令 |
| `Git代码管理` | 需要整理或解析 Git 仓库时 |
| `数据可视化` | 需要将代码数据转为图表输入时 |
| `仓库数据接入` | 需要将仓库数据导入其他系统时 |
| `代码仓解析` | 需要提取代码结构信息时 |
| `仓库数据提取` | 需要从仓库中抽取特定文件或信息时 |
| `Git数据转换` | 需要将 Git 数据转为其他格式时 |

### 2.2 场景映射表

| 用户说（大白话） | 实际触发动作 |
|------------------|--------------|
| "帮我看下这个仓库里有哪些 Python 文件" | 扫描目录，过滤 `.py` 文件，输出清单 |
| "把这个 GitHub 链接里的代码整理成表格" | 抓取 URL，解析内容，输出 Markdown 表格 |
| "我有一堆代码文件，想统计每个文件的行数" | 批量解析，统计 LOC，输出统计报告 |
| "这个文件里有哪些函数？" | 单文件解析，提取函数列表 |

---

## 三、标准流程

### 3.1 前置条件

| 条件 | 要求 | 检查方式 |
|------|------|----------|
| 输入文件 | 文本类代码文件（`.py`, `.js`, `.ts`, `.java`, `.go`, `.rs`, `.md`, `.json`, `.yaml` 等） | 检查文件扩展名 |
| 目录结构 | 待处理文件位于同一目录或可访问的路径下 | `ls` 或 `dir` 确认 |
| 网络访问 | 若处理 URL，需可访问公网 | `curl -I <url>` 测试 |
| 命名规范 | 文件名建议使用 `kebab-case` 或 `snake_case`，避免空格与特殊字符 | 目视检查 |

### 3.2 执行步骤

#### 步骤 1：准备输入

```bash
# 将待处理文件放入同一目录
mkdir -p ./input_data
cp /path/to/files/* ./input_data/

# 确认文件列表
ls -la ./input_data/
```

#### 步骤 2：单样本试运行

```bash
# 使用单个文件验证解析逻辑
github datasource --file ./input_data/sample.py --format json
```

**核对要点：**

- 输出字段是否完整（path, language, loc, functions 等）
- 字段类型是否正确（数字是否为 int，列表是否为 array）
- 置信度标注是否合理（高置信度 ≥ 0.9，中置信度 0.7-0.9，低置信度 < 0.7）

#### 步骤 3：批量执行

```bash
# 全量处理
github datasource --dir ./input_data/ --output ./output_data/ --format csv

# 或处理 URL 列表
github datasource --url-list ./urls.txt --output ./output_data/ --format json
```

**参数说明：**

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `--file` | string | 否 | 无 | 单文件路径 |
| `--dir` | string | 否 | 无 | 目录路径（递归扫描） |
| `--url-list` | string | 否 | 无 | 包含 URL 的文本文件路径 |
| `--output` | string | 是 | `./output/` | 输出目录 |
| `--format` | string | 否 | `json` | 输出格式：`json` / `csv` / `md` |
| `--confidence` | bool | 否 | `true` | 是否输出置信度标注 |
| `--recursive` | bool | 否 | `true` | 是否递归扫描子目录 |
| `--include` | string | 否 | 无 | 文件扩展名过滤，逗号分隔，如 `".py,.js"` |
| `--exclude` | string | 否 | 无 | 排除的目录名，逗号分隔，如 `"node_modules,.git"` |

#### 步骤 4：校验结果

```bash
# 抽查输出条目
head -20 ./output_data/result.json

# 与源数据对比
diff <(jq '.[0].path' ./output_data/result.json) <(echo "./input_data/sample.py")
```

**校验清单：**

- [ ] 文件路径与源目录一致
- [ ] 行数统计与 `wc -l` 结果一致
- [ ] 函数/类名提取完整
- [ ] 语言识别正确
- [ ] 置信度标注存在且合理

### 3.3 输出规范

#### JSON 输出示例

```json
{
  "schema_version": "1.0",
  "generated_at": "2025-01-15T10:30:00Z",
  "total_files": 2,
  "items": [
    {
      "path": "src/utils/date.ts",
      "language": "typescript",
      "loc": 42,
      "functions": [
        {"name": "formatDate", "line_start": 3, "line_end": 15, "confidence": 0.98},
        {"name": "parseDate", "line_start": 17, "line_end": 30, "confidence": 0.95}
      ],
      "imports": ["dayjs"],
      "confidence": 0.96
    }
  ]
}
```

#### CSV 输出示例

```csv
path,language,loc,functions,confidence
src/utils/date.ts,typescript,42,"formatDate;parseDate",0.96
src/index.js,javascript,120,"main;helper",0.94
```

#### Markdown 表格输出示例

```markdown
| 文件路径 | 语言 | 行数 | 函数列表 | 置信度 |
|----------|------|------|----------|--------|
| src/utils/date.ts | TypeScript | 42 | formatDate; parseDate | 0.96 |
| src/index.js | JavaScript | 120 | main; helper | 0.94 |
```

---

## 四、置信度门控

### 4.1 置信度等级定义

| 等级 | 分值范围 | 含义 | 适用场景 |
|------|----------|------|----------|
| 高 | 0.90 - 1.00 | 字段提取准确，无歧义 | 文件路径、语言识别、行数统计 |
| 中 | 0.70 - 0.89 | 字段存在但可能有边界情况 | 函数边界识别、导入列表 |
| 低 | 0.50 - 0.69 | 字段为推测值，需人工确认 | 语义推断、注释解析 |
| 不可用 | < 0.50 | 无法确定，输出占位符 | 信息缺失、格式异常 |

### 4.2 占位符规则

当信息不足时，**不编造数据**，输出以下占位符：

| 场景 | 占位符 | 示例 |
|------|--------|------|
| 函数名无法确定 | `[需核实:函数名]` | `{"name": "[需核实:函数名]", "line_start": 3}` |
| 语言无法识别 | `[需核实:语言]` | `{"language": "[需核实:语言]"}` |
| 行数统计失败 | `[需核实:行数]` | `{"loc": "[需核实:行数]"}` |
| 导入列表不完整 | `[需核实:导入]` | `{"imports": ["[需核实:导入]"]}` |

### 4.3 置信度计算规则

```
confidence = base_score × weight_structural × weight_syntax

base_score = 0.95（默认）
weight_structural = 1.0（结构清晰） / 0.8（结构模糊） / 0.5（结构混乱）
weight_syntax = 1.0（语法正确） / 0.85（有语法警告） / 0.6（语法错误较多）
```

---

## 五、错误码体系

### 5.1 错误码速查表

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| `E001` | 文件不存在 | "指定的文件路径不存在，请检查路径是否正确" | 1. 使用 `ls` 确认路径；2. 检查相对/绝对路径；3. 重新输入 |
| `E002` | 目录为空 | "指定目录下没有可解析的文本文件" | 1. 确认文件扩展名；2. 检查 `--include` 过滤条件；3. 添加文件后重试 |
| `E003` | URL 无法访问 | "无法访问该 URL，请确认链接为公开仓库且网络通畅" | 1. 浏览器打开链接验证；2. 检查网络代理；3. 确认仓库为 public |
| `E004` | 文件格式不支持 | "该文件类型不在支持列表中，支持类型：.py, .js, .ts, .java, .go, .rs, .md, .json, .yaml" | 1. 转换文件格式；2. 或使用 `--include` 指定其他类型 |
| `E005` | 输出目录不可写 | "无法写入输出目录，请检查权限" | 1. `chmod +w ./output/`；2. 更换输出路径 |
| `E006` | 解析超时 | "文件解析超时，可能文件过大或结构异常" | 1. 拆分大文件；2. 使用 `--timeout` 参数延长超时时间 |
| `E007` | 编码错误 | "文件编码不是 UTF-8，无法正确解析" | 1. 使用 `iconv` 转换编码；2. 重新执行 |

### 5.2 错误处理流程

```
遇到错误
    ↓
读取错误码
    ↓
根据提示话术定位问题
    ↓
执行修正步骤
    ↓
重新运行命令
    ↓
若仍失败 → 输出 [需核实:错误原因] 并跳过该文件，继续处理其余文件
```

---

## 六、FAQ 反模式

### 6.1 常见坑与反模式对照

| # | 常见坑（反模式） | 正确做法（正模式） |
|---|------------------|-------------------|
| 1 | **直接批量处理所有文件，不做试运行** → 输出格式错误，返工 | 先用单个样本验证输出格式，确认无误后再批量执行 |
| 2 | **忽略置信度标注，直接使用所有数据** → 低置信度数据污染分析结果 | 根据置信度阈值过滤数据，低于 0.7 的字段需人工确认 |
| 3 | **修改源文件后不备份** → 数据丢失无法恢复 | 处理前备份原始文件，保留 `*.bak` 或使用 Git 提交 |
| 4 | **使用绝对路径硬编码** → 换环境后脚本失效 | 使用相对路径或环境变量，确保可移植性 |
| 5 | **不检查输出结果，直接用于下游任务** → 错误数据流入生产环境 | 每次执行后抽查 10%-20% 输出条目，与源数据比对 |

### 6.2 反模式示例

**反模式 1：跳过试运行**

```bash
# ❌ 错误做法
github datasource --dir ./all_files/ --output ./result/ --format csv

# ✅ 正确做法
# 先试运行单个文件
github datasource --file ./all_files/sample.py --format json
# 确认无误后批量执行
github datasource --dir ./all_files/ --output ./result/ --format csv
```

**反模式 2：忽略置信度**

```python
# ❌ 错误做法
data = load_result("result.json")
for item in data["items"]:
    process(item["functions"])  # 直接使用所有数据

# ✅ 正确做法
data = load_result("result.json")
for item in data["items"]:
    if item["confidence"] >= 0.8:
        process(item["functions"])
    else:
        manual_review(item)
```

---

## 七、渐进式披露

### 7.1 速查卡（30 秒上手）

```
1. 准备文件 → 放入同一目录
2. 试运行 → github datasource --file sample.py --format json
3. 批量执行 → github datasource --dir ./input/ --output ./out/ --format csv
4. 校验结果 → 抽查 10% 条目，比对源数据
```

### 7.2 新手路径（5 分钟掌握）

1. 阅读「能力边界」了解适用范围
2. 按「标准流程」步骤 1-2 完成单文件解析
3. 查看输出 JSON 结构，理解字段含义
4. 尝试修改 `--format` 参数，体验不同输出格式
5. 阅读「置信度门控」了解数据可信度

### 7.3 进阶路径（深入使用）

1. 掌握「错误码体系」，能独立排查常见问题
2. 理解置信度计算规则，自定义置信度阈值
3. 使用 `--include` / `--exclude` 精细控制处理范围
4. 结合外部工具（jq, pandas）对输出结果做二次处理
5. 阅读「FAQ 反模式」，避免常见陷阱

### 7.4 参数速查表

| 参数 | 新手建议 | 进阶建议 |
|------|----------|----------|
| `--format` | 使用 `json` 便于调试 | 按需切换 `csv` / `md` |
| `--confidence` | 保持默认 `true` | 可关闭以提升性能 |
| `--recursive` | 保持默认 `true` | 按需关闭以控制范围 |
| `--include` | 不设置，处理全部 | 设置以过滤特定类型 |
| `--exclude` | 不设置 | 排除 `node_modules`, `.git` 等 |

---

## 八、用户协议

<!-- user-agreement-injected -->

**使用本 Skill 即表示您同意以下条款：**

1. **责任承担**：使用者自行承担因使用本 Skill 产生的全部责任。本 Skill 仅提供数据处理指导，不构成任何形式的保证或承诺。

2. **数据安全**：使用者应自行确保输入数据的合法性与安全性。本 Skill 不收集、存储或传输任何用户数据。

3. **禁止反向工程**：使用者不得对本 Skill 进行反向工程、反编译、破解或试图提取底层算法。

4. **合规使用**：使用者应遵守所在地区法律法规，不得将本 Skill 用于任何非法用途。

5. **免责声明**：本 Skill 按"现状"提供，不附带任何明示或暗示的保证，包括但不限于适销性、特定用途适用性和非侵权保证。

---

## 九、许可证（License）

<!-- professional-license-embedded -->

### MIT License

```
MIT License

Copyright (c) 2025 DataFlow Architect

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to
