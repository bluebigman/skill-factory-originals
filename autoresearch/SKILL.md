---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: autoresearch
name: autoresearch
displayName: 数据采集清洗 单卡训练 语料整理
description: 面向单GPU nanochat训练，自动完成数据采集、清洗与结构化整理。
version: 2.0.1
rules_version: cpr-20260819-n551
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/autoresearch
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: DataPilot Studio
agent_created: true
trigger_words: ["autoresearch", "自动调研", "数据整理", "nanochat训练", "单卡微调", "语料清洗", "数据集构建"]
---

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->


> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# autoresearch — 单卡训练数据自动采集与清洗 Skill

## 一、能力边界（一页纸速查卡）

### 1.1 能做什么

| 能力项 | 说明 | 输出形态 |
|--------|------|----------|
| 数据采集 | 从指定源（本地目录、URL列表、简单API）抓取文本数据 | 原始文本文件集 |
| 数据清洗 | 去除重复、噪声、HTML标签、特殊字符、过短片段 | 清洗后文本文件 |
| 结构化整理 | 按对话格式（instruction/input/output）或纯文本段落重组 | JSONL / JSON / TXT |
| 质量预筛 | 基于长度、重复度、困惑度估算给出置信度评分 | 置信度字段（0.0~1.0） |
| 预览模式 | 不写盘，仅打印处理效果样本 | 终端输出 |

### 1.2 不能做什么

| 限制项 | 说明 |
|--------|------|
| 不支持多GPU分布式训练 | 仅面向单卡 nanochat 微调场景 |
| 不做语义级去重 | 仅做文本相似度（n-gram）去重，不识别语义相同但表述不同的内容 |
| 不生成新数据 | 不进行数据增强、改写、翻译等生成操作 |
| 不处理非文本数据 | 图片、音频、视频等多媒体内容不在处理范围内 |
| 不保证数据质量 | 置信度评分仅作参考，最终质量需人工确认 |

### 1.3 适用对象

- 使用 nanochat 框架进行单卡微调的研究者/开发者
- 需要快速整理本地散落文本为训练语料的个人或小团队
- 对数据清洗有基本认知，愿意人工抽检的进阶用户

---

## 二、触发方式与场景映射

### 2.1 触发词

| 触发词 | 场景说明 |
|--------|----------|
| `autoresearch` | 直接调用主命令 |
| `自动调研` | 中文场景下的数据采集请求 |
| `数据整理` | 需要清洗/结构化已有数据 |
| `nanochat训练` | 明确针对 nanochat 微调的数据准备 |
| `单卡微调` | 单GPU训练前的数据预处理 |
| `语料清洗` | 去除噪声、重复内容的操作 |
| `数据集构建` | 从零开始搭建训练数据集 |

### 2.2 场景映射表

| 用户说 | 实际需求 | Skill 响应 |
|--------|----------|------------|
| "我有一堆txt文件想训练用" | 清洗+结构化 | 执行 `--mode clean --format jsonl` |
| "帮我抓几个网页做语料" | 数据采集 | 执行 `--mode fetch --urls-file urls.txt` |
| "这个数据集太乱了" | 清洗+去重 | 执行 `--mode clean --dedupe true` |
| "想看看处理效果" | 预览 | 执行 `--dry-run --verbose` |
| "要跑nanochat了" | 完整流程 | 执行 `--mode all --format jsonl` |

---

## 三、标准流程

### 3.1 前置条件

| 条件 | 要求 | 检查方式 |
|------|------|----------|
| Python | ≥ 3.9 | `python --version` |
| 依赖包 | `click`, `jieba`, `regex`, `tqdm` | `pip list` 或 `pip install -r requirements.txt` |
| 磁盘空间 | 至少为原始数据量的 3 倍 | `df -h` |
| 输入数据 | 文本文件（.txt/.md/.json）或 URL 列表 | 确认路径存在 |

### 3.2 执行步骤

#### 步骤 1：初始化环境

```bash
# 安装依赖（首次使用）
pip install click jieba regex tqdm

# 验证安装
python -c "import click, jieba, regex, tqdm; print('OK')"
```

#### 步骤 2：配置参数

| 参数 | 默认值 | 说明 | 示例 |
|------|--------|------|------|
| `--input` | `./data/raw` | 输入目录或文件 | `--input ./my_data` |
| `--output` | `./data/processed` | 输出目录 | `--output ./train_data` |
| `--format` | `jsonl` | 输出格式：jsonl/json/txt | `--format json` |
| `--min-confidence` | `0.6` | 置信度阈值，低于此值标记为待审 | `--min-confidence 0.8` |
| `--dedupe` | `true` | 是否启用 n-gram 去重 | `--dedupe false` |
| `--dry-run` | `false` | 预览模式，不写盘 | `--dry-run --verbose` |
| `--verbose` | `false` | 输出详细日志 | `--verbose` |
| `--mode` | `all` | 执行模式：all/fetch/clean | `--mode clean` |
| `--urls-file` | 无 | URL 列表文件（每行一个） | `--urls-file urls.txt` |

#### 步骤 3：运行主脚本

```bash
# 完整流程（采集+清洗+结构化）
python autoresearch.py --mode all --input ./raw --output ./processed --format jsonl

# 仅清洗本地已有数据
python autoresearch.py --mode clean --input ./raw --output ./cleaned --dedupe true

# 预览模式（推荐先跑一次）
python autoresearch.py --mode clean --input ./raw --dry-run --verbose
```

#### 步骤 4：验证输出

```bash
# 检查输出文件
ls -la ./processed/
# 预期看到：data.jsonl, stats.json, rejected.json

# 查看统计信息
cat ./processed/stats.json
# 预期包含：total_records, passed_records, rejected_records, avg_confidence
```

#### 步骤 5：异常处理

| 错误现象 | 可能原因 | 处理方式 |
|----------|----------|----------|
| 输出为空 | 输入路径错误或数据格式不支持 | 检查 `--input` 路径，确认文件为 .txt/.md/.json |
| 置信度普遍偏低 | 数据噪声大或长度过短 | 调整 `--min-confidence` 至 0.4~0.5，或先人工粗筛 |
| 去重过度 | n-gram 阈值过高 | 在代码中调整 `--ngram-size`（默认 5） |
| 内存溢出 | 单文件过大 | 拆分文件，或使用 `--chunk-size`（默认 10000 条/批） |

### 3.3 输出规范

| 输出文件 | 格式 | 内容说明 |
|----------|------|----------|
| `data.jsonl` | JSONL | 每行一条记录，含 `text`、`confidence`、`source` 字段 |
| `stats.json` | JSON | 处理统计：总数、通过数、拒绝数、平均置信度 |
| `rejected.json` | JSON | 未通过置信度阈值的数据，含拒绝原因 |

**记录示例（JSONL）：**

```json
{"text": "用户提问：什么是注意力机制？\n回答：注意力机制是一种让模型关注输入序列中重要部分的技术...", "confidence": 0.87, "source": "tech_blog_001.txt"}
{"text": "深度学习中的梯度消失问题可以通过残差连接缓解...", "confidence": 0.72, "source": "notes_003.md"}
```

---

## 四、置信度门控

### 4.1 置信度计算规则

| 因素 | 权重 | 说明 |
|------|------|------|
| 文本长度 | 30% | 少于 50 字符扣分，多于 500 字符加分 |
| 重复度 | 30% | 与已处理文本 n-gram 相似度 > 0.8 扣分 |
| 特殊字符占比 | 20% | 非中英文/数字字符占比 > 20% 扣分 |
| 结构完整性 | 20% | 含明显截断（无结尾标点）扣分 |

### 4.2 门控规则

- **置信度 ≥ 阈值**：自动通过，进入输出文件
- **置信度 < 阈值**：写入 `rejected.json`，不进入训练集
- **信息不足时**：输出 `[需核实:字段名]` 占位符，不编造内容

**示例：**

```json
{"text": "[需核实:source] 这段文本来源不明，且内容不完整...", "confidence": 0.31, "status": "rejected"}
```

### 4.3 人工抽检建议

- 每处理 1000 条记录，抽检 50 条（5%）
- 重点检查：置信度在 0.5~0.7 之间的边缘数据
- 抽检时关注：语义连贯性、事实准确性、格式一致性

---

## 五、错误码体系

| 错误码 | 错误描述 | 提示话术 | 修正步骤 |
|--------|----------|----------|----------|
| `E001` | 输入路径不存在 | "输入路径无效，请检查 --input 参数" | 确认路径存在，或创建目录 |
| `E002` | 输出目录无写入权限 | "输出目录无写入权限，请检查权限设置" | `chmod +w ./output` 或更换目录 |
| `E003` | 依赖包缺失 | "缺少依赖包：jieba，请先安装" | `pip install jieba` |
| `E004` | URL 无法访问 | "URL 请求失败：{url}，已跳过" | 检查网络，或从 urls.txt 中移除该 URL |
| `E005` | 数据格式不支持 | "文件 {file} 格式不支持，仅支持 .txt/.md/.json" | 转换格式后重试 |
| `E006` | 内存不足 | "处理批次过大，内存不足" | 减小 `--chunk-size` 至 5000 或更低 |
| `E007` | 输出格式无效 | "输出格式无效，可选：jsonl/json/txt" | 检查 `--format` 参数拼写 |

---

## 六、FAQ 反模式对照

### 6.1 常见坑与反模式

| 坑 | 反模式（错误做法） | 正模式（正确做法） |
|----|-------------------|-------------------|
| **跳过预览直接跑** | 直接执行完整流程，发现输出格式不对，浪费算力 | 先跑 `--dry-run --verbose` 确认效果 |
| **置信度阈值设太高** | 设 0.9，导致 80% 数据被拒，训练数据不足 | 从 0.6 起步，根据 rejected.json 调整 |
| **不保留原始数据** | 直接覆盖原文件，清洗效果不理想时无法回退 | 处理前 `cp -r ./raw ./raw_backup` |
| **完全信任置信度** | 置信度 0.9 的数据直接入训练集，不抽检 | 即使高置信度，也抽检 5% 记录 |
| **忽略 rejected.json** | 只看通过的记录，不分析被拒原因 | 定期查看 rejected.json，了解数据短板 |

### 6.2 反模式示例

**反模式：**

```bash
# 直接跑完整流程，不预览
python autoresearch.py --mode all --input ./raw --output ./processed
# 结果：输出格式不是想要的 jsonl，且大量数据被误删
```

**正模式：**

```bash
# 先预览
python autoresearch.py --mode clean --input ./raw --dry-run --verbose
# 确认效果后，正式运行
python autoresearch.py --mode clean --input ./raw --output ./processed --format jsonl --min-confidence 0.6
```

---

## 七、渐进式披露

### 7.1 速查卡（30秒上手）

```bash
# 三步上手
pip install click jieba regex tqdm
python autoresearch.py --mode clean --input ./raw --dry-run --verbose
python autoresearch.py --mode clean --input ./raw --output ./processed --format jsonl
```

### 7.2 新手路径（首次使用）

1. 阅读「能力边界」了解工具限制
2. 准备一个小规模测试集（10~20 个文件）
3. 执行 `--dry-run --verbose` 预览效果
4. 确认无误后正式运行
5. 查看 `stats.json` 和 `rejected.json` 了解处理情况
6. 人工抽检 5% 输出数据

### 7.3 进阶路径（熟练用户）

1. 自定义 `--min-confidence` 和 `--ngram-size` 参数
2. 使用 `--mode fetch` 采集网络数据，配合 `--urls-file`
3. 分析 `rejected.json` 中的拒绝原因，优化输入数据质量
4. 将 `stats.json` 作为数据质量报告，持续跟踪改进
5. 结合 nanochat 训练结果，反向调整数据清洗策略

---

## 八、附录

### 8.1 完整参数表

| 参数 | 类型 | 默认值 | 必填 | 说明 |
|------|------|--------|------|------|
| `--input` | string | `./data/raw` | 否 | 输入目录或文件路径 |
| `--output` | string | `./data/processed` | 否 | 输出目录 |
| `--format` | string | `jsonl` | 否 | 输出格式：jsonl/json/txt |
| `--min-confidence` | float | `0.6` | 否 | 置信度阈值（0.0~1.0） |
| `--dedupe` | bool | `true` | 否 | 是否启用去重 |
| `--dry-run` | bool | `false` | 否 | 预览模式，不写盘 |
| `--verbose` | bool | `false` | 否 | 详细日志输出 |
| `--mode` | string | `all` | 否 | 执行模式：all/fetch/clean |
| `--urls-file` | string | 无 | 否 | URL 列表文件路径 |
| `--chunk-size` | int | `10000` | 否 | 每批处理记录数 |
| `--ngram-size` | int | `5` | 否 | 去重时 n-gram 大小 |

### 8.2 目录结构建议

```
project/
├── raw/                  # 原始数据（只读）
├── raw_backup/           # 原始数据备份
├── processed/            # 处理输出
│   ├── data.jsonl
│   ├── stats.json
│   └── rejected.json
├── urls.txt              # URL 列表（可选）
└── autoresearch.py       # 主脚本
```

---

## 用户协议

**使用本 Skill 即表示您同意以下条款：**

1. **责任承担**：使用者自行承担因使用本 Skill 产生的全部责任。本 Skill 提供的数据处理建议和输出结果仅供参考，不构成任何形式的保证或承诺。
2. **禁止反向工程**：不得对本 Skill 的代码、逻辑、算法进行反向工程、反编译或试图提取源代码（除非适用法律允许）。
3. **数据合规**：使用者需确保输入数据的合法性和合规性，不得使用本 Skill 处理违法违规内容。
4. **无担保声明**：本 Skill 按"原样"提供，不附带任何明示或暗示的担保，包括但不限于适销性、特定用途适用性和非侵权性保证。

<!-- user-agreement-injected -->

---

## 许可证（License）

**MIT License**

版权所有 (c) 2025 原创作者（自持版权）

特此免费授予任何获得本软件及相关文档文件（以下简称"软件"）副本的人士使用本软件的权利，包括但不限于使用、复制、修改、合并、发布、分发、再许可和/或销售软件副本的权利，并允许向提供软件的人士授权上述行为，但须满足以下条件：

上述版权声明和本许可声明应包含在软件的所有副本或实质性部分中。

本软件按"原样"提供，不附带任何明示或暗示的担保，包括但不限于适销性、特定用途适用性和非侵权性保证。在任何情况下，作者或版权持有人均不对任何索赔、损害或其他责任负责，无论是在合同诉讼、侵权或其他方面，由软件或软件的使用或其他交易引起、产生或与之相关。

<!-- professional-license-embedded -->
