---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: autoresearch
name: autoresearch
displayName: 单卡微调 自动调研 数据准备
description: 面向单GPU nanochat训练场景，自动完成数据采集、清洗与结构化整理。
version: 1.0.1
rules_version: cpr-20260809-n251
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/autoresearch
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: LingResearch
agent_created: true
trigger_words: ["autoresearch", "自动调研", "数据整理", "nanochat训练", "单卡微调"]
---

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->


> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# 单卡微调 自动调研 数据准备 Skill 文档

## 一、能力边界（一页纸速查卡）

### 1.1 能做（核心能力清单）

| 序号 | 能力项 | 说明 | 输入示例 | 输出示例 |
|------|--------|------|----------|----------|
| 1 | 数据/文件/URL 结构化转换 | 将用户提供的原始材料解析为统一格式 | 一段文本、CSV文件、网页链接 | 结构化 JSON 或 Markdown 表格 |
| 2 | 关键信息识别与保留 | 自动提取输入中的核心实体、数值、结论 | 论文摘要、训练日志 | 关键字段列表 |
| 3 | 约定格式输出 | 按用户指定的 schema 生成结果 | 用户指定字段结构 | 符合 schema 的输出文件 |
| 4 | 置信度标注 | 对不确定的字段标注置信度等级 | 模糊数据、缺失值 | `[需核实:字段名]` 占位 |
| 5 | 批量处理与自定义格式 | 支持多文件/多URL批量处理，可定制输出模板 | 10个CSV文件、5个URL | 批量处理报告 |

### 1.2 不能做（明确边界）

- **不能** 执行实际的模型训练或推理任务
- **不能** 访问需要登录认证的私有数据源
- **不能** 保证数据的绝对准确性和完整性
- **不能** 替代人工对关键决策的审核
- **不能** 处理超过 100MB 的单个文件

### 1.3 适用对象

- 正在准备 nanochat 单卡微调数据集的工程师
- 需要快速整理训练语料的算法研究员
- 需要批量清洗数据的 AI 应用开发者

---

## 二、触发方式

### 2.1 触发词

| 触发词 | 场景描述 |
|--------|----------|
| `autoresearch` | 直接调用本 Skill 的指令词 |
| `自动调研` | 中文场景下的等价触发词 |
| `数据整理` | 当用户需要整理训练数据时触发 |
| `nanochat训练` | 明确提到 nanochat 微调场景时触发 |
| `单卡微调` | 单 GPU 训练数据准备场景 |

### 2.2 场景映射表

| 用户实际需求（大白话） | 触发动作 |
|------------------------|----------|
| "帮我整理这些训练数据" | 启动数据清洗与结构化流程 |
| "把这个网页内容转成训练格式" | 启动 URL 抓取与转换流程 |
| "我有100个文件要处理" | 启动批量处理模式 |
| "这个CSV格式不对，帮我改一下" | 启动格式转换流程 |

---

## 三、标准流程

### 3.1 前置条件

| 条件项 | 要求 | 检查方式 |
|--------|------|----------|
| 输入数据 | 文件大小 ≤ 100MB，或 URL 可公开访问 | 自动检测 |
| 输出格式 | 用户已明确指定或使用默认 JSON 格式 | 对话确认 |
| 运行环境 | Python 3.8+，已安装 requests, pandas | 环境检测 |

### 3.2 执行步骤

**步骤 1：输入收集与确认**

```
输入类型：文件 / URL / 文本
处理动作：
  1.1 接收用户输入
  1.2 检测输入类型
  1.3 确认输出格式（默认 JSON）
  1.4 确认批量模式（单条/多条）
```

**步骤 2：内容解析**

```
解析规则：
  2.1 文本 → 按段落/句子切分
  2.2 CSV → 按行/列解析，识别表头
  2.3 URL → 抓取正文，去除导航/广告
  2.4 多文件 → 逐个解析，保持独立
```

**步骤 3：关键信息提取**

```
提取策略：
  3.1 实体识别：人名、机构、模型名、数据集名
  3.2 数值提取：参数量、训练轮数、学习率
  3.3 结论提取：摘要、关键句、指标值
  3.4 关系识别：数据来源、处理流程、结果对比
```

**步骤 4：结果生成与校验**

```
输出规范：
  4.1 按约定 schema 组织字段
  4.2 缺失字段标注 [需核实:字段名]
  4.3 完整性检查：必填字段是否齐全
  4.4 格式校验：JSON 语法、字段类型
```

### 3.3 输出规范

**默认输出格式（JSON）**：

```json
{
  "meta": {
    "source_type": "file|url|text",
    "source_count": 1,
    "processed_at": "2026-08-09T12:00:00Z"
  },
  "data": [
    {
      "id": 1,
      "content": "原始内容摘要",
      "key_entities": ["entity1", "entity2"],
      "metrics": {"param_count": "7B", "learning_rate": "2e-5"},
      "confidence": 0.95,
      "notes": "补充说明"
    }
  ]
}
```

---

## 四、置信度门控机制

### 4.1 置信度等级定义

| 等级 | 数值范围 | 含义 | 处理方式 |
|------|----------|------|----------|
| 高 | 0.85-1.0 | 信息完整且来源可靠 | 直接输出 |
| 中 | 0.60-0.84 | 信息基本完整，部分存疑 | 标注提示 |
| 低 | 0.00-0.59 | 信息缺失或矛盾 | 使用 `[需核实:字段]` 占位 |

### 4.2 占位符使用规则

- 格式：`[需核实:字段名]`
- 场景：数据缺失、来源不可靠、信息矛盾
- 示例：`[需核实:learning_rate]` 表示学习率字段无法确认

### 4.3 禁止行为

- **禁止** 编造不存在的数值或结论
- **禁止** 用默认值填充未知字段
- **禁止** 忽略置信度标注直接输出

---

## 五、错误码体系

| 错误码 | 错误描述 | 提示话术 | 修正步骤 |
|--------|----------|----------|----------|
| E001 | 输入文件不存在 | "未找到指定文件，请检查路径是否正确" | 1. 确认文件路径 2. 重新输入 |
| E002 | URL 无法访问 | "目标 URL 返回 404 或超时" | 1. 检查 URL 拼写 2. 确认网络连接 |
| E003 | 文件格式不支持 | "仅支持 txt/csv/json/md 格式" | 1. 转换文件格式 2. 重新上传 |
| E004 | 文件超过大小限制 | "文件超过 100MB 限制" | 1. 拆分文件 2. 压缩后上传 |
| E005 | 输出格式冲突 | "指定的输出格式与默认 schema 冲突" | 1. 确认输出格式 2. 调整 schema |
| E006 | 批量处理中断 | "第 N 个文件处理失败，已跳过" | 1. 查看错误日志 2. 单独处理失败文件 |

---

## 六、FAQ 反模式对照

### 6.1 常见坑与反模式

| 常见坑 | 反模式示例 | 正确做法 |
|--------|------------|----------|
| 忽略置信度 | 直接输出所有字段，不标注不确定项 | 对不确定字段使用 `[需核实:字段]` |
| 过度清洗 | 删除所有特殊字符，导致语义丢失 | 保留必要的标点和格式标记 |
| 格式硬编码 | 只支持 JSON 输出，拒绝其他格式 | 提供模板机制，支持自定义 schema |
| 批量处理无日志 | 批量失败后无法定位问题 | 记录每个文件的处理状态和错误信息 |
| 忽略输入校验 | 直接处理异常格式导致崩溃 | 前置校验输入类型和大小 |

### 6.2 反模式对照表

| 反模式 | 问题描述 | 推荐替代方案 |
|--------|----------|--------------|
| 静默失败 | 处理失败但不提示用户 | 明确返回错误码和修正建议 |
| 过度承诺 | 声称"保证100%准确" | 明确说明置信度范围和限制 |
| 无版本控制 | 输出格式变更无记录 | 在 meta 中记录 schema 版本 |

---

## 七、渐进式披露

### 7.1 速查卡（30秒上手）

```
1. 输入：文件/URL/文本
2. 确认输出格式（默认 JSON）
3. 运行：autoresearch --input <路径> --format json
4. 检查输出中的 [需核实] 字段
5. 完成
```

### 7.2 新手路径（首次使用）

1. 阅读「能力边界」了解适用范围
2. 使用默认 JSON 格式处理一个小文件
3. 检查输出中的置信度标注
4. 参考「错误码体系」处理常见问题

### 7.3 进阶路径（深度使用）

1. 自定义输出 schema 满足特定需求
2. 使用批量模式处理多文件
3. 结合「置信度门控」设计数据审核流程
4. 参考「FAQ 反模式」优化处理策略

---

## 八、命令行接口

### 8.1 参数说明

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `--input` | string | 是 | 无 | 输入文件路径或 URL |
| `--format` | string | 否 | json | 输出格式（json/csv/md） |
| `--batch` | boolean | 否 | false | 批量处理模式 |
| `--output` | string | 否 | stdout | 输出文件路径 |
| `--selftest` | boolean | 否 | false | 运行自检 |
| `--version` | boolean | 否 | false | 显示版本号 |

### 8.2 使用示例

```bash
# 单文件处理
python autoresearch.py --input data.txt --format json

# URL 抓取
python autoresearch.py --input https://example.com/doc --format md

# 批量处理
python autoresearch.py --input ./data_dir/ --batch --output result.json

# 自检
python autoresearch.py --selftest
```

---

## 九、用户协议

<!-- user-agreement-injected -->

**使用本 Skill 即表示您同意以下条款：**

1. **责任承担**：使用者自行承担使用本 Skill 产生的全部责任。本 Skill 提供的数据处理结果仅供参考，不构成任何形式的保证或承诺。

2. **禁止反向工程**：禁止对本 Skill 进行反向工程、反编译、破解或试图提取源代码。

3. **合规使用**：使用者应确保使用本 Skill 的行为符合当地法律法规及道德规范。

4. **免责声明**：本 Skill 按"现状"提供，不附带任何明示或暗示的保证，包括但不限于适销性、特定用途适用性和非侵权保证。

5. **数据安全**：使用者应自行负责输入数据的合法性和安全性，本 Skill 不承担数据泄露或损失的责任。

---

## 十、许可证（License）

<!-- professional-license-embedded -->

**MIT License**

Copyright (c) 2026 LingResearch

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

*本文档由 AI 辅助生成，仅供参考。使用前请阅读相关文档。*
