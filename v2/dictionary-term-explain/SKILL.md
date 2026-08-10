---
slug: dictionary-term-explain
name: 术语释义助手
displayName: 场景拆解 概念边界 落地解释
description: 按场景拆解术语含义，给出边界清晰、可落地的概念解释。
version: 3.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 术语工坊
agent_created: true
trigger_words: ["术语解释", "名词释义", "概念说明", "这个词什么意思", "通俗解释", "术语拆解", "概念辨析", "定义解读"]
---

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->


> 📜 **用户协议（User Agreement）**
> 1. 本 Skill 仅供学习与参考用途。使用本 Skill 产生的任何结果，由使用者自行承担全部责任；本 Skill 不提供任何明示或暗示的保证。
> 2. 涉及法律、财务、税务、投资、医疗等专业决策时，请务必咨询持证专业人士。
> 3. 本代码受版权法保护，未经授权复制、反向工程或商业利用将被追究法律责任。
<!-- user-agreement-injected -->


# 术语释义助手（Term Explainer）

**一句话定位**：面向产品经理、技术写作者、新员工和跨部门协作人员，按「技术 / 业务 / 日常 / 学术」四类场景拆解术语含义，明确概念边界与常见误用，让抽象名词变得可落地、可沟通。

---

## 快速开始 Quick Start

| 场景 | 命令 | 预期结果 |
|------|------|---------|
| 解释单个术语 | `python run.py "微服务"` | 输出结构化解释（核心定义 / 场景拆解 / 概念边界 / 常见误用） |
| 指定场景解释 | `python run.py "区块链" --scene 技术` | 只输出「技术」场景的解释，聚焦专业视角 |
| 批量解释多个术语 | `python run.py --batch terms.json` | 依次输出每个术语的完整解释，以分隔线隔开 |

> 💡 **最常用**：`python run.py "微服务"` 即可获得全场景解释，无需额外参数。

---

## 适用场景 When to Use

### ✅ 推荐使用

- **产品经理**向开发 / 设计 / 运营解释业务术语时
- **技术写作者**编写文档时需要澄清概念边界时
- **新员工 / 转岗人员**快速理解团队内部黑话时
- **跨部门协作**消除术语理解偏差时
- **学生 / 自学者**理解专业教材中的抽象概念时

### ❌ 不推荐使用

- 需要法律 / 医疗 / 财务等专业领域正式意见的场景
- 需要逐字逐句翻译的场景
- 需要权威定义（如 ISO 标准原文）的场景
- 需要操作步骤或实施指导的场景（本工具只做概念解释）

---

## 能力总览 Capabilities

| 能力 | 命令 / 参数 | 示例 |
|------|------------|------|
| 单个术语解释 | `python run.py <术语>` | `python run.py "微服务"` |
| 指定场景解释 | `--scene <技术/业务/日常/学术/all>` | `python run.py "区块链" --scene 技术` |
| 批量处理 JSON 文件 | `--batch <file.json>` | `python run.py --batch terms.json` |
| 批量处理纯文本文件 | `--batch <file.txt>` | `python run.py --batch terms.txt` |
| 预览模式（不执行查询） | `--dry-run` | `python run.py --batch terms.json --dry-run` |
| 调试输出（详细日志） | `--verbose` | `python run.py "微服务" --verbose` |
| 内置自测 | `--selftest` | `python run.py --selftest` |
| 版本信息 | `--version` | `python run.py --version` |
| 外部 API 兜底 | 自动触发（知识库未命中时） | 查询维基百科获取解释 |
| LRU 缓存 | 自动启用（1024 条） | 重复查询秒回 |

---

## 模块决策表 Decision Table

| 用户意图 | 推荐模块 / 命令 | 读取指引 |
|---------|----------------|---------|
| 快速了解一个术语 | `python run.py <术语>` | 查看「快速开始」 |
| 需要特定场景的专业解释 | `python run.py <术语> --scene <场景>` | 查看「能力总览」 |
| 批量解释多个术语 | `python run.py --batch <文件>` | 查看「批量处理」章节 |
| 预览将处理的术语（不执行查询） | `python run.py --batch <文件> --dry-run` | 查看「预览模式」 |
| 验证功能是否正常 | `python run.py --selftest` | 查看「自测」章节 |
| 知识库未命中时 | 自动尝试维基百科 | 查看「外部 API 兜底」 |
| 排查错误 | 查看错误码 | 查看「错误码」章节 |

---

## 示例 Examples

### 示例 1：单个术语解释（全场景）

```bash
$ python run.py "微服务"
```

**输出**：

```text
【微服务】核心定义
将单一应用拆分为一组小型独立服务，每个服务围绕业务能力构建，可独立部署和扩展。

【技术场景】
服务间通过 HTTP/RPC 轻量通信，每个服务拥有独立数据库，支持独立部署与水平扩展。

【业务场景】
团队可按业务域拆分，独立迭代发布，提升交付效率，降低单点故障影响。

【日常场景】
就像一家餐厅分成多个档口，每个档口独立出菜，互不干扰。

【概念边界】
微服务 ≠ 微架构；微服务是架构风格，微架构是单体应用内部模块化设计。

【常见误用】
误以为微服务一定比单体好——团队规模小、业务简单时，单体反而更高效。
```

### 示例 2：指定场景解释

```bash
$ python run.py "区块链" --scene 技术
```

**输出**：

```text
【区块链 · 技术场景】
一种由密码学保障的分布式数据存储结构。
技术实现上包含区块头（版本、时间戳、Merkle根）与区块体（交易列表）；
共识机制包括PoW、PoS、PBFT等；
典型应用包括以太坊智能合约平台、Hyperledger Fabric联盟链。
```

### 示例 3：批量处理 JSON 文件

```bash
$ cat terms.json
{"terms": ["微服务", "区块链", "容器化"]}

$ python run.py --batch terms.json
```

**输出**：

```text
========== 1/3 ==========
【微服务】核心定义
...

========== 2/3 ==========
【区块链】核心定义
...

========== 3/3 ==========
【容器化】核心定义
...
```

---

## 安装与配置 Installation

### 环境要求

- Python 3.8+
- 无第三方依赖（仅使用标准库）

### 安装步骤

```bash
# 1. 下载 run.py 到本地目录
# 2. 赋予执行权限（可选）
chmod +x run.py

# 3. 验证安装
python run.py --version
```

### 环境变量

| 变量名 | 用途 | 默认值 |
|--------|------|--------|
| `TERM_EXPLAINER_TIMEOUT` | 外部 API 超时时间（秒） | `5` |
| `TERM_EXPLAINER_RETRIES` | 外部 API 最大重试次数 | `3` |

---

## 常见问题 Troubleshooting

### 问题 1：知识库未命中，且外部 API 查询失败

**现象**：输出 `E1004: 知识库未命中且外部API失败`

**原因**：本地知识库没有该术语，且网络不可用或维基百科 API 返回错误。

**解决办法**：
- 检查网络连接
- 确认术语拼写是否正确
- 稍后重试（外部 API 可能临时不可用）

### 问题 2：批量文件格式错误

**现象**：输出 `E1003: 批量文件不存在或格式错误`

**原因**：JSON 文件格式不正确，或纯文本文件编码无法识别。

**解决办法**：
- JSON 文件需包含 `{"terms": ["术语1", "术语2"]}` 结构
- 纯文本文件每行一个术语，使用 UTF-8 或 GBK 编码

### 问题 3：输入术语过长

**现象**：输出 `E1002: 输入超长（>100字符）`

**原因**：术语长度超过 100 字符限制。

**解决办法**：缩短术语长度，或拆分查询。

---

## 最佳实践 Best Practices

### 技巧

1. **优先使用全场景解释**：不带 `--scene` 参数时，输出最全面，适合快速了解。
2. **批量处理提高效率**：需要解释多个术语时，使用 `--batch` 参数一次处理。
3. **预览模式安全操作**：不确定批量文件内容时，先使用 `--dry-run` 预览。

### 边界与安全提醒

- 本工具仅提供概念解释，不构成专业建议。
- 涉及法律、医疗、财务等专业决策时，请咨询持证专业人士。
- 外部 API 查询需要网络连接，且结果仅供参考。

---

## 相关资源 Related

- [维基百科 API 文档](https://www.mediawiki.org/wiki/API:Main_page)
- [Python 官方文档](https://docs.python.org/3/)

---

## 错误码 Error Codes

| 错误码 | 含义 | 处理建议 |
|--------|------|---------|
| E1001 | 输入为空 | 提供非空术语 |
| E1002 | 输入超长（>100字符） | 缩短术语长度 |
| E1003 | 批量文件不存在或格式错误 | 检查文件路径和格式 |
| E1004 | 知识库未命中且外部API失败 | 检查网络或稍后重试 |
| E1005 | 批量文件编码无法识别 | 使用 UTF-8 或 GBK 编码 |

---

## 许可证（License）

```text
MIT License

Copyright (c) 2024 术语工坊

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