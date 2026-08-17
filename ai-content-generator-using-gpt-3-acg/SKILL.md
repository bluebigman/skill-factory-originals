---
slug: ai-content-generator-using-gpt-3-acg
name: acg-structured-text-processor
displayName: 文本批处理 结构化提取 置信度标注
description: 本地规则驱动的文本批处理与结构化提取引擎，支持多格式输出与置信度标注。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 墨规工作室
agent_created: true
trigger_words: ["文本批处理", "结构化提取", "置信度标注", "批量清洗", "字段抽取", "格式转换"]
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# ACG 结构化文本处理器（acg-structured-text-processor）

## 一、能力边界速查卡

### 1.1 能做什么

| 能力项 | 说明 | 典型输入 | 典型输出 |
|--------|------|----------|----------|
| 批量文本清洗 | 去除噪声字符、统一空白、修正编码 | 爬虫抓取的脏文本 | 干净纯文本 |
| 字段结构化抽取 | 按规则模板提取关键字段 | 合同、简历、日志 | JSON 对象数组 |
| 多格式输出 | 支持 JSON / Markdown / CSV 三种序列化 | 结构化数据 | 指定格式文件 |
| 置信度标注 | 每条抽取结果附带可信度评分 | 模糊文本 | `{"value":"...", "confidence":0.87}` |
| 规则模板复用 | 自定义抽取规则存为模板文件 | 规则 YAML | 可重复执行的模板 |

### 1.2 不能做什么

| 限制项 | 说明 | 替代方案 |
|--------|------|----------|
| 语义理解 | 不基于大模型做语义推断，仅规则匹配 | 接入 LLM API 做后处理 |
| 超大文件 | 单文件超过 50MB 建议先分块 | 使用 `split` 命令或脚本切分 |
| 非结构化推理 | 无法处理无规律的自由文本 | 先人工标注样本，再写规则 |
| 实时流处理 | 不支持 stdin 持续输入 | 落盘后批处理 |

### 1.3 适用对象

- 需要定期清洗日志/导出数据的运维人员
- 需要从批量文档中抽取字段的运营人员
- 需要将非结构化文本转为表格数据的分析人员

---

## 二、触发方式与场景映射

### 2.1 触发词

直接使用以下任一词汇即可激活本 Skill 的规则库：

```
文本批处理、结构化提取、置信度标注、批量清洗、字段抽取、格式转换
```

### 2.2 场景映射表

| 你说的话（大白话） | 实际执行的动作 |
|-------------------|----------------|
| "帮我把这堆日志里的 IP 和状态码抽出来" | 加载日志规则模板 → 抽取 IP/status → 输出 JSON |
| "这个 CSV 里有脏数据，帮我洗一下" | 执行清洗规则 → 去重/去噪 → 输出干净 CSV |
| "把合同里的金额和日期整理成表格" | 加载合同模板 → 抽取金额/日期 → 输出 Markdown 表格 |
| "这些文本里哪些字段是确定的？" | 执行抽取 → 计算置信度 → 标注低置信字段 |

---

## 三、标准执行流程

### 3.1 前置条件

| 条件 | 要求 | 检查方式 |
|------|------|----------|
| 输入文件 | 纯文本或 UTF-8 编码，单文件 ≤ 50MB | `wc -c file.txt` |
| 规则模板 | 已定义抽取字段（或使用内置默认模板） | 见 3.2 节 |
| 运行环境 | Python 3.8+，安装 `pyyaml` | `python3 --version` |

### 3.2 执行步骤

1. **准备输入文件**  
   将待处理文本保存为 `.txt` 或 `.md` 文件。若文件超过 50MB，先执行分块：
   ```bash
   split -l 10000 large_file.txt chunk_
   ```

2. **定义抽取规则（可选）**  
   创建 `rules.yaml`，示例：
   ```yaml
   fields:
     - name: ip_address
       pattern: '\b(?:\d{1,3}\.){3}\d{1,3}\b'
       type: string
     - name: status_code
       pattern: '\b(?:2\d{2}|3\d{2}|4\d{2}|5\d{2})\b'
       type: integer
   ```

3. **执行批处理**  
   运行主程序（伪代码）：
   ```bash
   python acg_processor.py --input raw.txt --rules rules.yaml --output result.json
   ```

4. **检查置信度标注**  
   输出中每个字段附带 `confidence` 值（0~1）。低于 0.6 的字段会标记为 `[需核实:字段名]`。

5. **导出目标格式**  
   通过 `--format` 参数切换输出格式：
   ```bash
   python acg_processor.py --input raw.txt --rules rules.yaml --format csv --output result.csv
   ```

### 3.3 输出规范

| 格式 | 结构示例 | 适用场景 |
|------|----------|----------|
| JSON | `[{"ip":"192.168.1.1","confidence":0.98}]` | 程序间数据交换 |
| Markdown | `\| ip \| 置信度 \|` 表格 | 人工阅读 |
| CSV | `ip,confidence` 首行表头 | Excel 打开 |

---

## 四、置信度门控机制

### 4.1 置信度计算规则

| 条件 | 置信度 | 说明 |
|------|--------|------|
| 规则完全匹配且无歧义 | 0.95~1.0 | 直接采信 |
| 规则匹配但存在多个候选 | 0.7~0.9 | 取最长匹配 |
| 规则部分匹配（如缺失前缀） | 0.4~0.6 | 标记需核实 |
| 无规则命中 | 0.0~0.3 | 输出 `[需核实:字段名]` |

### 4.2 占位符规范

当信息不足时，**严禁编造数据**。统一使用以下占位符：

```
[需核实:字段名]
```

示例：`[需核实:合同金额]` 表示该字段未能可靠提取，需人工确认。

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| `E001` | 输入文件不存在 | "未找到指定文件，请检查路径" | 确认文件路径，重新执行 |
| `E002` | 文件超过 50MB | "文件过大，建议先分块处理" | 使用 `split` 分块后重试 |
| `E003` | 规则模板格式错误 | "规则 YAML 解析失败，请检查缩进" | 用 `yaml.safe_load` 验证 |
| `E004` | 无任何字段命中 | "未提取到任何字段，请检查规则" | 调整正则表达式或换模板 |
| `E005` | 输出目录无写入权限 | "无法写入输出文件，请检查权限" | `chmod +w` 或更换目录 |

---

## 六、FAQ 反模式对照

| 常见坑 | 反模式（错误做法） | 正确做法 |
|--------|-------------------|----------|
| 规则过宽 | 用 `.*` 匹配所有内容 | 使用锚点 `^...$` 限定边界 |
| 忽略编码 | 直接处理 GBK 文件 | 先转 UTF-8 再处理 |
| 置信度误用 | 把 0.5 的字段当确定值 | 低于 0.6 一律走人工复核 |
| 模板不备份 | 修改规则后无法回滚 | 用 git 管理规则文件 |
| 输出覆盖 | 多次运行覆盖原结果 | 输出文件名加时间戳 |

---

## 七、渐进式阅读路径

### 7.1 新手路径（5 分钟上手）

1. 阅读「一、能力边界速查卡」了解适用范围
2. 直接使用内置默认模板处理小文件（< 1MB）
3. 查看 JSON 输出中的 `confidence` 字段，理解置信度含义

### 7.2 进阶路径（深度使用）

1. 学习「三、标准执行流程」中的规则定义语法
2. 自定义 `rules.yaml` 适配业务字段
3. 结合错误码表排查复杂场景
4. 将处理流程封装为 shell 脚本或 CI 任务

---

## 八、用户协议

<!-- user-agreement-injected -->

**使用本 Skill 即表示您同意以下条款：**

1. 使用者自行承担全部责任。因使用本 Skill 产生的任何直接或间接损失，作者不承担任何责任。
2. 禁止反向工程。不得对本 Skill 的规则模板、核心逻辑进行逆向、破解或二次分发。
3. 本 Skill 输出的结果仅供参考，不构成任何形式的专业建议或保证。
4. 若您不同意以上条款，请立即停止使用并删除相关文件。

---

## 九、许可证（License）

<!-- professional-license-embedded -->

**MIT License**

```
MIT License

Copyright (c) 2024 墨规工作室

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

---

*本 Skill 由 AI 辅助生成，仅供参考。使用前请结合自身场景验证规则准确性。*
