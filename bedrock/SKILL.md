---
slug: bedrock
name: bedrock
displayName: 数据清洗 结构化解析 置信标注
description: 将杂乱数据转为规整结构化结果，支持批量处理与置信度标注。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 林墨
agent_created: true
trigger_words: ["bedrock", "数据解析", "结构化输出", "信息抽取", "批量处理", "数据清洗", "字段映射"]
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# bedrock — 数据清洗与结构化解析 Skill

## 一、能力边界速查卡

### 1.1 能做什么

| 能力项 | 说明 | 示例 |
|--------|------|------|
| 文本结构化 | 将非结构化文本转为键值对字段 | 从发票照片 OCR 文本中提取金额、日期、发票号 |
| 批量处理 | 一次处理多行/多文件输入 | 1000 条客户留言 → 统一格式的 CSV |
| 置信度标注 | 对每个字段给出匹配可信度 | `confidence: 0.92` 或标记 `[需核实]` |
| 自定义映射规则 | 通过 `mapping_config.json` 调整正则 | 修改日期格式匹配规则 |
| 编码自动识别 | 自动处理 utf-8/gbk/gb18030 编码 | 无需手动转码即可读取 GBK 文件 |
| 预览模式 | 不落盘执行，先看结果再决定 | `--dry-run` 输出预览 |

### 1.2 不能做什么

| 限制项 | 说明 |
|--------|------|
| 不支持直接解析图像/音频/视频 | 必须先经 OCR/ASR 转为文本后再输入 |
| 不保证 100% 字段提取成功 | 低置信度字段会标记 `[需核实]`，不会编造 |
| 不自动生成业务规则 | 正则表达式需由使用者根据业务场景配置 |
| 不处理语义理解 | 仅做模式匹配，不判断上下文含义 |

### 1.3 适用对象

- 需要从日志、表单、票据、留言等文本中提取固定字段的开发者
- 需要批量清洗历史数据的运维/数据工程师
- 需要将非标准输入转为标准 API 入参的集成工程师

---

## 二、触发方式与场景映射

| 触发词 | 大白话场景 | 使用方式 |
|--------|-----------|----------|
| `bedrock 数据解析` | "帮我把这些杂乱的文本整理成表格" | `bedrock parse --input raw.txt` |
| `bedrock 结构化输出` | "把这段文字里的关键信息抽出来" | `bedrock parse --single "文本内容"` |
| `bedrock 批量处理` | "我有 500 条数据要统一格式" | `bedrock parse --batch --input dir/` |
| `bedrock 信息抽取` | "从这些邮件里提取日期和金额" | 配合 `mapping_config.json` 自定义规则 |

---

## 三、标准执行流程

### 3.1 前置条件

| 条件 | 要求 | 检查方式 |
|------|------|----------|
| 输入格式 | 纯文本（.txt/.csv/.log）或可转文本的文件 | `file input.txt` 查看类型 |
| 映射配置 | `mapping_config.json` 存在且格式合法 | `bedrock --selftest` 验证 |
| 环境依赖 | Python 3.8+，已安装 bedrock 包 | `bedrock --version` 确认 |

### 3.2 执行步骤

1. **单样本验证**：先取 3-5 条代表性数据，用 `--single` 模式测试
   ```bash
   bedrock parse --single "客户A 2024-03-15 消费 ¥1,234.56"
   ```

2. **检查映射规则**：确认 `mapping_config.json` 中的正则能覆盖目标字段
   ```json
   {
     "date": {"pattern": "\\d{4}-\\d{2}-\\d{2}", "confidence": 0.9},
     "amount": {"pattern": "¥([0-9,.]+)", "confidence": 0.85}
   }
   ```

3. **预览批量结果**：使用 `--dry-run` 不落盘执行
   ```bash
   bedrock parse --batch --input ./data/ --dry-run
   ```

4. **正式执行**：确认预览无误后移除 `--dry-run`
   ```bash
   bedrock parse --batch --input ./data/ --output ./result/
   ```

5. **检查输出**：查看生成的结构化文件，确认 `[需核实]` 标记数量在可接受范围

### 3.3 输出规范

| 输出项 | 格式 | 说明 |
|--------|------|------|
| 结构化数据 | JSON/CSV | 每个字段含 `value` 和 `confidence` |
| 低置信度字段 | `[需核实:字段名]` | 不猜测，保留占位 |
| 处理日志 | stdout/stderr | `--verbose` 查看详细匹配过程 |

---

## 四、置信度门控机制

### 4.1 置信度阈值

| 阈值区间 | 行为 | 建议场景 |
|----------|------|----------|
| ≥ 0.9 | 直接输出字段值 | 高精度要求（财务数据） |
| 0.7 - 0.9 | 输出值并标注 `confidence` | 常规业务数据 |
| < 0.7 | 输出 `[需核实:字段名]` | 不确定时宁缺毋滥 |

### 4.2 调整方法

```bash
# 修改 mapping_config.json 中的 confidence_threshold
bedrock parse --config ./mapping_config.json --threshold 0.8
```

### 4.3 不编造原则

当信息不足时，工具**不会**：
- 猜测缺失字段的值
- 用默认值填充
- 忽略低置信度字段

而是输出 `[需核实:字段名]` 占位，由使用者决定后续处理。

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| `E001` | 输入文件不存在 | `Error: input file not found` | 检查路径，确认文件存在 |
| `E002` | 编码无法识别 | `Error: cannot detect encoding` | 手动转码：`iconv -f gbk -t utf-8 input.txt > output.txt` |
| `E003` | 映射配置格式错误 | `Error: invalid mapping_config.json` | 用 `json.tool` 校验：`python -m json.tool mapping_config.json` |
| `E004` | 正则匹配失败 | `Warning: no match for field 'date'` | 调整正则，或降低该字段的 `confidence_threshold` |
| `E005` | 批量处理中断 | `Error: batch processing interrupted at line N` | 对第 N 行单独执行 `parse --single` 定位问题 |

---

## 六、FAQ 反模式对照

### 6.1 常见坑与正确做法

| 反模式 ❌ | 正确做法 ✅ |
|-----------|-------------|
| 拿到数据直接批量跑，不先单测 | 先用 `--single` 测试 3-5 条代表性样本 |
| 正则写得过于宽泛，匹配到错误内容 | 使用精确正则，如 `^\\d{4}-\\d{2}-\\d{2}$` 而非 `\\d+` |
| 阈值设得太低，大量 `[需核实]` 标记 | 根据业务容忍度调整，先试 0.8 再逐步降低 |
| 忽略 `--dry-run` 直接正式执行 | 批量前务必预览，确认无误再落盘 |
| 输入含特殊符号（如 emoji）导致匹配失败 | 预处理时清洗干扰字符，或增加宽松正则兜底 |

### 6.2 调试建议

- 使用 `--verbose` 查看每个字段的匹配过程
- 对失败行单独执行 `parse --single` 定位问题
- 检查输入文本编码是否正确（工具自动支持 utf-8/gbk/gb18030）

---

## 七、渐进式披露路径

### 7.1 新手快速上手（5 分钟）

1. 准备一个纯文本文件，内容包含日期、金额、编号
2. 运行 `bedrock parse --single "测试文本"` 看效果
3. 用 `--dry-run` 预览批量结果
4. 正式执行并检查输出

### 7.2 进阶用户（自定义规则）

1. 编辑 `mapping_config.json` 添加自定义字段
2. 使用 `--verbose` 调试正则匹配
3. 调整 `confidence_threshold` 控制输出质量
4. 结合 `--selftest` 验证配置正确性

### 7.3 专家级（集成与自动化）

1. 将 bedrock 嵌入 CI/CD 流水线
2. 编写脚本自动处理编码转换
3. 根据业务反馈持续优化正则规则
4. 建立字段置信度监控，定期评估提取质量

---

## 八、用户协议

<!-- user-agreement-injected -->

**使用 bedrock Skill 即表示您同意以下条款：**

1. **责任承担**：使用者自行承担使用本 Skill 产生的全部责任。包括但不限于因数据解析错误、字段提取不准确、批量处理失误等造成的直接或间接损失。
2. **禁止反向工程**：不得对本 Skill 进行反向工程、反编译、破解或试图提取源代码（除非适用法律允许）。
3. **数据安全**：使用者需自行确保输入数据的合法性和安全性，不得输入违反法律法规或侵犯他人权益的内容。
4. **无担保声明**：本 Skill 按"现状"提供，不附带任何明示或暗示的担保，包括但不限于适销性、特定用途适用性和非侵权性。
5. **修改与分发**：使用者可以修改和分发本 Skill，但需保留原始版权声明和本协议条款。

---

## 九、许可证（License）

<!-- professional-license-embedded -->

### MIT License

Copyright (c) 2024 林墨

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
