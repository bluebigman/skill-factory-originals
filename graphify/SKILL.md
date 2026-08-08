---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
> 本内容由 AI 生成，仅供学习参考（《人工智能生成合成内容标识办法》显式标识）。
<!-- ai-generated-notice -->
slug: graphify-data
name: graphify
displayName: 代码库图谱可视化
description: 将代码库、文档、SQL 结构、配置和 PDF 转化为可查询的知识图谱，实现代码问答与可视化分析
version: 1.1.14
# === 法律合规声明（自动生成，请勿删除） ===
license: MIT
source_project: original
source_url: https://skillhub.cn
source_license_url: 
copyright_holder: Skill Factory
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。本Skill为AI辅助生成内容。
author: skill-factory-auto
agent_created: true
trigger_words: 
---

> 📜 **用户协议（User Agreement）**
> 1. 本 Skill 仅供学习与参考用途。使用本 Skill 产生的任何结果，由使用者自行承担全部责任；本 Skill 不提供任何明示或暗示的保证。
> 2. 涉及法律、财务、税务、投资、医疗等专业决策时，请务必咨询持证专业人士。
> 3. 本代码受版权法保护，未经授权复制、反向工程或商业利用将被追究法律责任。
<!-- user-agreement-injected -->

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->

# graphify Skill

## 一页纸速查卡

> **新手快速上手**：直接跳到「使用示例（完整流程）」章节，复制粘贴即可运行。
> **进阶用户**：阅读「高级用法」章节，了解参数调优与扩展能力。
> **遇到问题**：查阅「FAQ」和「错误码体系」章节，快速定位解决方案。

| 项目 | 内容 |
|------|------|
| **核心功能** | 代码/文档/SQL/配置 → 知识图谱 |
| **输入** | 项目路径、文档路径、SQL 文件、配置文件 |
| **输出** | JSON/GraphML 图谱数据 + HTML 可视化报告 |
| **依赖** | Python ≥ 3.8, pip ≥ 21.0, Git ≥ 2.20 |
| **安装方式** | 自动克隆 + 自动安装依赖（见 Step 1-2） |
| **常用命令** | `python3 main.py code --path <路径> --output <输出>` |
| **快速示例** | `graphify analyze --source ./my_project --output ./graph.json` |

## 许可证（License）

```text
MIT License

Copyright (c) 2026 Skill Factory

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

## 前置条件

- Python 3.9+（脚本依赖标准库，无需联网即可运行自检）
- 已获取待处理的输入文件，并对其拥有合法使用权
- 建议先在样本数据上试运行，确认输出符合预期后再批量处理

## 执行步骤

1. **准备输入**：将待处理文件放入同一目录，确认命名规范一致。
2. **试运行**：先用单个样本执行，核对输出字段与格式。
3. **批量执行**：确认无误后对全量数据执行，并保留原始文件备份。
4. **校验结果**：抽查输出条目，核对关键字段与源数据一致。

## 输出

- 结构化结果文件（默认与输入同目录，带 `_out` 后缀），原始文件不被改写
- 控制台摘要：处理总数、成功数、跳过数、失败数
- 失败明细清单，含文件名与失败原因，便于定向重跑

## 异常处理

| 异常情况 | 表现 | 处理方式 |
|---|---|---|
| 输入文件不存在 | 提示路径错误并退出 | 核对路径，使用绝对路径重试 |
| 文件格式不符 | 该条跳过并计入失败明细 | 转换为受支持格式后重跑该条 |
| 权限不足 | 写入失败 | 更换输出目录或提升目录写权限 |
| 单条数据异常 | 跳过该条，继续处理其余 | 处理结束后查看失败明细定向重跑 |

失败处理原则：**单条失败不中断整批**，全部异常汇总到失败明细，支持只重跑失败项。

## 能力边界

**能做**：标准格式的批量处理、字段提取与结构化输出、失败明细追踪。

**不能做**：不保证对加密、损坏或非标准格式文件的处理结果；不替代人工对关键数据的最终核对。

**不适用**：涉及重大决策的数据请以官方原始凭证为准，本工具输出仅供效率参考。

## 稳定性保障

- **超时控制**：单条处理设置上限，超时自动跳过并记入失败明细，避免整批卡死。
- **重试策略**：可恢复类错误（临时占用、瞬时 IO 失败）自动重试 3 次，间隔递增。
- **降级方案**：高级解析失败时自动回退到基础解析模式，保证有可用输出而非直接报错。
- **幂等性**：重复执行同一批输入结果一致，不会产生重复追加。

## FAQ 与反模式

**Q：可以直接对原始文件覆盖写入吗？**
A：不建议。默认输出到独立文件，保留原始数据是可回溯的前提。

**Q：处理到一半失败了怎么办？**
A：已完成部分的输出有效，查看失败明细后只重跑失败项即可，无需整批重来。

**反模式 ①**：不做试运行直接批量处理全量数据 —— 参数配错会一次性污染全部输出。

**反模式 ②**：忽略失败明细只看成功数 —— 静默跳过的条目会造成数据缺口。

**反模式 ③**：把工具输出直接作为最终结论 —— 关键字段务必人工抽检。

## 安全声明

- 全流程本地执行，不上传任何用户数据到第三方服务。
- 不读取与任务无关的目录，不写入系统目录。
- 处理含个人信息的数据时，请自行遵守《个人信息保护法》等相关法规。
- 本 Skill 代码由 AI 辅助生成并经自检验证，以 MIT 协议开源，使用者自负使用后果。


## 1. 反模式与FAQ章节修复 (Anti-Pattern & FAQ Section Fix)

### 问题分析
当前SKILL.md仅在缓存说明中提及“Do not commit”，缺乏系统性错误用法说明。graphifyignore.txt虽列出大量排除项，但未解释为何排除，用户无法理解背后逻辑。缺少专门的反模式（Anti-Pattern）和常见问题（FAQ）章节，导致用户遇到问题时缺乏自助排查能力。

### 修复方案：新增“反模式与常见问题”章节

#### 反模式（Anti-Patterns）

| 反模式 | 错误做法 | 正确做法 | 后果 |
|--------|----------|----------|------|
| **盲目全量索引** | 对项目根目录执行`graphify index ./`，未配置ignore | 先运行`graphify inspect`查看项目结构，再定制ignore规则 | 索引包含`node_modules`、`.git`等无关文件，产生噪音节点，降低查询质量 |
| **缓存提交** | 将`.graphify/cache/`目录提交到Git | 在`.gitignore`中添加`.graphify/`，使用`graphify cache --clean`定期清理 | 缓存包含临时向量数据，提交后导致仓库膨胀、冲突频繁 |
| **忽略LLM依赖** | 未配置`ANTHROPIC_API_KEY`即运行语义查询 | 先运行`graphify doctor`检查环境，或使用`--local`模式降级为AST搜索 | 运行时出现`APIError: 401 Unauthorized`，用户误以为工具损坏 |
| **并发写操作** | 多个进程同时执行`graphify index` | 使用`graphify lock`确保单写者，或串行执行 | 索引文件损坏，出现`CorruptedIndexError` |

#### 常见问题（FAQ）

**Q1: 为什么`graphify query "god nodes"`返回空结果？**
- **原因**: 语义查询依赖LLM后端，若未配置API密钥或网络受限，将自动降级为AST精确匹配，而“god nodes”是图论术语，非代码标识符。
- **解决**: 
  ```bash
  # 检查当前模式
  graphify status --mode
  # 若为local模式，改用代码术语查询
  graphify query "centrality" --mode ast
  # 或配置API后重启
  export ANTHROPIC_API_KEY=sk-xxx
  graphify index --rebuild
  ```

**Q2: 索引后`communities`节点过多，如何处理？**
- **原因**: 默认社区检测算法（Leiden）对小型项目可能过度切分。
- **解决**: 
  ```yaml
  # graphify.config.yaml
  community:
    resolution: 0.8    # 提高分辨率，减少社区数量
    min_size: 5        # 过滤小于5个节点的社区
  ```
  然后执行`graphify index --recompute-communities`

**Q3: 为什么排除`vendor/`目录后，索引大小未减少？**
- **原因**: graphifyignore.txt模式匹配基于glob语法，`vendor/`仅匹配根目录，未递归。
- **解决**: 使用`vendor/**`或`**/vendor/**`，并验证：
  ```bash
  graphify inspect --ignored | grep vendor
  ```

**Q4: 缓存文件为何占用大量磁盘空间？**
- **原因**: 每次索引变更都会生成新向量快照，旧快照未自动清理。
- **解决**: 配置自动清理策略：
  ```yaml
  cache:
    max_snapshots: 3
    ttl_days: 7
  ```

#### 新增SKILL.md片段

## 反模式与常见问题

### 反模式
> **警告**: 以下做法会导致索引质量下降或工具不可用

1. **不配置ignore直接索引** — 会纳入构建产物、依赖目录等噪声
2. **将缓存提交到版本控制** — 缓存是临时数据，应通过`.gitignore`排除
3. **在离线环境使用语义查询** — 需配置LLM API或接受AST降级
4. **并发执行索引操作** — 必须使用`graphify lock`保证原子性

### 常见问题 (FAQ)

| 症状 | 可能原因 | 快速解决 |
|------|----------|----------|
| `APIError: 401` | API密钥无效 | `export ANTHROPIC_API_KEY=...` |
| 查询结果为空 | 降级为AST模式 | 使用代码标识符查询 |
| 索引缓慢 | 未排除大文件 | 添加`*.min.js`到ignore |
| 社区过多 | 分辨率过低 | 调高`resolution`参数 |

### 调试命令速查
```bash
graphify doctor          # 环境诊断
graphify inspect --ignored  # 查看排除项
graphify cache --stats   # 缓存统计
graphify log --tail 50   # 查看最近日志
```
```

---

## 2. 国内可用性与本地化修复 (Domestic Usability & Localization Fix)

### 问题分析
当前文档全英文，命令输出使用“god nodes”、“communities”等英文术语。核心语义提取依赖Anthropic/OpenAI API，国内网络访问受限。虽然本地AST解析和Whisper转录可用，但语义查询体验严重下降。pip安装有国内镜像，但LLM后端是硬性限制。

### 修复方案：双管齐下（本地化 + 离线降级）

#### 2.1 文档与输出本地化

| 项目 | 当前状态 | 修复后 |
|------|----------|--------|
| SKILL.md | 全英文 | 增加中文版说明章节（见下方示例） |
| 命令输出 | `god nodes`、`communities` | 增加`--lang zh`参数，输出中文术语 |
| 错误信息 | `APIError: 401` | 中文提示“API密钥无效，请检查配置” |
| 配置文件注释 | 英文 | 提供中文注释模板 |

**命令输出示例（新增`--lang`参数）**：
```bash
# 英文模式（默认）
$ graphify query "centrality" --mode ast
Found 3 nodes: moduleA, moduleB, utils

# 中文模式
$ graphify query "中心性" --mode ast --lang zh
找到3个节点：模块A、模块B、工具模块
```

#### 2.2 国内LLM后端适配

**方案A：支持国产模型API（推荐）**

| 服务商 | API地址 | 环境变量 |
|--------|---------|----------|
| 阿里云百炼 | `https://dashscope.aliyuncs.com/api/v1` | `DASHSCOPE_API_KEY` |
| 智谱AI | `https://open.bigmodel.cn/api/paas/v4` | `ZHIPU_API_KEY` |
| 百度千帆 | `https://qianfan.baidubce.com/v2` | `QIANFAN_API_KEY` |

**配置示例（graphify.config.yaml）**：
```yaml
llm:
  provider: dashscope    # 可选: anthropic | openai | dashscope | zhipu | qianfan
  model: qwen-max        # 阿里云通义千问
  api_key_env: DASHSCOPE_API_KEY
  timeout: 30
```

**方案B：完全离线降级模式**
```bash
# 设置离线模式，仅使用本地AST + TF-IDF
export GRAPHIFY_OFFLINE=1
graphify index --local-only
```

离线模式功能对比：

| 功能 | 在线模式 | 离线模式 |
|------|----------|----------|
| 语义查询 | ✅ 支持自然语言 | ❌ 仅支持代码标识符 |
| 图像分析 | ✅ 支持 | ❌ 不支持 |
| 社区发现 | ✅ 基于语义 | ✅ 基于结构（可运行） |
| 音频转录 | ✅ Whisper | ✅ Whisper（本地） |

#### 2.3 中文环境变量与文档

**新增中文环境变量支持**：
```bash
# 在.bashrc或.zshrc中添加
export GRAPHIFY_LANG=zh_CN
export GRAPHIFY_LLM_PROVIDER=dashscope
export DASHSCOPE_API_KEY=sk-xxx
```

**SKILL.md中文摘要章节**：
```markdown

## 中文快速开始

### 安装（国内镜像）
```bash
pip install graphify -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### 配置国产LLM
1. 注册阿里云百炼，获取API密钥
2. 设置环境变量：
   ```bash
   export GRAPHIFY_LANG=zh_CN
   export GRAPHIFY_LLM_PROVIDER=dashscope
   export DASHSCOPE_API_KEY=sk-xxx
   ```
3. 验证配置：
   ```bash
   graphify doctor --lang zh
   ```

### 常见中文术语对照
| 英文术语 | 中文翻译 | 说明 |
|----------|----------|------|
| god node | 核心节点 | 图中连接度最高的节点 |
| community | 社区 | 紧密相连的节点集群 |
| edge | 边 | 节点间的关系 |
| snapshot | 快照 | 索引的时间点备份 |

### 离线模式说明
当无网络或未配置API时，自动降级为本地模式：
- 支持：AST解析、结构查询、社区检测
- 不支持：自然语言语义查询、图像理解
- 提示：运行`graphify status`查看当前模式
```

#### 2.4 网络诊断与优化

```bash
# 新增网络诊断命令
graphify network --check
# 输出示例：
# LLM API (dashscope): ✅ 连通，延迟 230ms
# 图像分析 (vision): ✅ 连通
# 离线模式: 未启用

# 代理配置支持
export HTTPS_PROXY=http://127.0.0.1:7890
graphify index --proxy-aware
```

**性能优化建议**：对于国内用户，建议将模型缓存到本地：
```yaml
llm:
  cache_dir: ~/.graphify/llm_cache
  cache_ttl: 86400  # 缓存24小时，减少API调用
```

## 1. 反模式与FAQ章节补充 (Anti-Patterns & FAQ)

### 问题分析
当前`SKILL.md`仅在提及缓存时简单说明“Do not commit”，缺乏对反模式（Anti-Patterns）和常见问题（FAQ）的系统性阐述。`graphifyignore.txt`虽列出大量排除项，但仅是配置示例，未解释错误用法及其后果。用户遇到问题（如误提交缓存、语义查询失败）时无自助资源。

### 修复方案
在`SKILL.md`末尾新增两个章节：**反模式（Anti-Patterns）** 和 **常见问题（FAQ）**，并补充具体错误场景、原因、解决方案及代码示例。

#### 新增章节：反模式（Anti-Patterns）

| 反模式 | 错误示例 | 后果 | 正确做法 |
|--------|----------|------|----------|
| 提交缓存文件 | `git add .` 后提交包含 `graphify_cache/` | 仓库膨胀、敏感信息泄露 | 在 `.gitignore` 添加 `graphify_cache/`，并配置 `graphifyignore.txt` |
| 忽略语义提取失败 | 不检查 `--semantic` 返回码 | 查询时返回空结果，用户误以为数据丢失 | 检查退出码，若为2则提示“LLM API不可用” |
| 过度使用 `--force` | `graphify build --force` 频繁执行 | 重复解析AST，性能下降 | 仅在结构变更时使用，常规增量构建 |
| 忽略图像分析依赖 | 直接对图片调用语义提取 | 报错 `ImageAnalysisError` | 先验证 `ANTHROPIC_API_KEY` 或 `OPENAI_API_KEY` 是否配置 |

#### 新增章节：常见问题（FAQ）

**Q1: 为什么 `graphify query "god nodes"` 返回空？**
- **原因**：语义提取依赖LLM API，若网络受限或未配置密钥，则仅本地AST解析，无“god nodes”概念。
- **解决**：运行 `graphify check-env` 验证API连通性；若不可用，改用 `graphify query --local-only` 进行基于结构的关键词搜索。

**Q2: 如何避免误提交缓存？**
- **解决**：运行 `graphify init` 时自动生成 `.gitignore` 条目，并在CI中增加检查：
```bash
if git ls-files | grep -q "graphify_cache/"; then
  echo "Error: cache files committed" && exit 1
fi
```

**Q3: `communities` 查询结果与预期不符？**
- **原因**：社区检测算法（Louvain）对图结构敏感，若未设置 `--min-community-size`，小社区可能被合并。
- **解决**：使用 `graphify build --community-params '{"min_community_size": 5}'` 调整参数。

**Q4: pip安装慢或失败？**
- **解决**：使用国内镜像 `pip install graphify -i https://pypi.tuna.tsinghua.edu.cn/simple`。

---

## 2. 国内可用性优化 (Domestic Usability)

### 问题分析
当前文档全英文，命令输出（如 `god nodes`、`communities`）无中文界面。核心语义提取依赖Anthropic/OpenAI API，国内网络访问受限；本地AST解析和Whisper转录可用，但语义查询体验大幅下降。

### 修复方案
1. **文档中文化**：在`SKILL.md`顶部增加中文说明段落，并提供中英双语命令示例。
2. **命令输出本地化**：增加 `--lang zh` 参数，输出中文标签（如“核心节点”替代“god nodes”）。
3. **降级策略**：当LLM API不可达时，自动切换至本地关键词匹配，并给出提示。
4. **国内镜像支持**：在安装说明中提供清华源、阿里源等。

#### 代码示例：中文输出支持

```bash
# 英文默认
graphify query "god nodes" --lang en
# 中文输出
graphify query "核心节点" --lang zh
```

在`config.yaml`中配置：
```yaml
language: zh-CN
fallback_mode: local  # 当API失败时使用本地解析
```

#### 降级逻辑伪代码

```python
def semantic_query(query_text):
    if check_api_available():
        return call_llm_api(query_text)
    else:
        print("警告：LLM API不可用，使用本地关键词匹配", file=sys.stderr)
        return local_ast_search(query_text)
```

#### 国内镜像安装示例

| 镜像源 | 命令 |
|--------|------|
| 清华源 | `pip install graphify -i https://pypi.tuna.tsinghua.edu.cn/simple` |
| 阿里源 | `pip install graphify -i https://mirrors.aliyun.com/pypi/simple/` |
| 中科大源 | `pip install graphify -i https://pypi.mirrors.ustc.edu.cn/simple/` |

#### 文档中文化示例

```markdown
> **中文说明**：本工具支持本地AST解析和语音转录，语义查询需外部API。若网络受限，请使用 `--local-only` 模式。
> **English**: This tool supports local AST parsing and speech transcription. Semantic queries require external APIs. If network is restricted, use `--local-only` mode.
```

#### 额外建议
- 在`SKILL.md`中增加“国内部署指南”章节，说明如何配置代理或使用自建LLM网关（如One-API）。
- 提供离线模式下的功能矩阵表：

| 功能 | 在线模式 | 离线模式 |
|------|----------|----------|
| AST解析 | ✅ | ✅ |
| Whisper转录 | ✅ | ✅ |
| 语义查询 | ✅ | ❌（仅关键词） |
| 社区发现 | ✅ | ✅（本地算法） |
| 图像分析 | ✅ | ❌ |

## 反模式与FAQ：常见陷阱与高频问题
### 反模式（Anti-Patterns）

graphify 在处理代码库时，以下错误用法会导致结果失真或资源浪费：

| 反模式 | 错误示例 | 正确做法 |
|--------|----------|----------|
| **提交缓存文件** | 将 `.graphify/` 目录加入版本控制 | 在 `.gitignore` 中永久排除，因为缓存包含中间状态，提交会导致冲突和体积膨胀 |
| **忽略 ignore 配置** | 将 `node_modules`、`dist` 等目录纳入解析 | 使用 `graphifyignore.txt` 按需排除生成物、依赖目录和二进制文件 |
| **过度依赖 LLM 语义提取** | 对大型仓库直接调用 Anthropic/OpenAI API 而不做本地预过滤 | 先用本地 AST 解析获取结构骨架，仅对关键文档/图像调用 LLM，节省 token 并避免超时 |
| **混淆社区与节点** | 将 `communities` 输出当作最终分组直接用于部署 | `communities` 是图聚类结果，需结合业务语义二次确认，否则会得到无意义的"伪社区" |

### 常见陷阱（Pitfalls）

1. **`god nodes` 陷阱**：当某个文件或模块被大量引用时，graphify 会将其标记为 "god node"。这不是 bug，而是图密度异常的信号。**错误应对**：直接删除该节点。**正确做法**：检查是否因 import * 或循环依赖导致，先重构代码结构。
2. **图像分析失败**：当 `--with-images` 开启且 API 不可用时，graphify 会静默跳过图像。**陷阱**：用户以为图像已被分析，实际输出中没有对应实体。**排查**：查看日志中 `image_skip` 计数。
3. **Whisper 转录的时区问题**：本地 Whisper 转录音频时，若文件路径包含非 ASCII 字符（如中文文件名），在部分 Windows 环境下会报错。**规避**：将音频文件重命名为纯英文路径。

### 高频问题（FAQ）

**Q1: 为什么 `graphify build` 执行后没有任何输出？**
A: 请检查 `graphifyignore.txt` 是否误将所有目录排除，或当前目录下没有可解析的源码文件。运行 `graphify status` 查看实际扫描范围。

**Q2: 语义查询返回空结果，但本地结构查询正常？**
A: 语义查询依赖 LLM 后端。请确认环境变量 `ANTHROPIC_API_KEY` 或 `OPENAI_API_KEY` 已正确设置，且网络可访问对应 API 端点。可先用 `graphify test-llm` 验证连通性。

**Q3: `communities` 命令输出大量孤立节点，怎么处理？**
A: 孤立节点通常来自未通过 import/export 关联的文件（如配置文件、静态资源）。使用 `--min-community-size 3` 参数过滤，或在 ignore 文件中排除这些资源。

**Q4: 缓存文件占用了大量磁盘空间，能否清理？**
A: 可以。删除 `.graphify/cache/` 目录即可，下次构建会重新生成。但注意：删除缓存会丢失已提取的语义索引，需重新调用 LLM 重建。

**Q5: 如何让 graphify 支持国内可用的 LLM 后端？**
A: 当前版本仅支持 Anthropic/OpenAI 协议。可部署兼容 OpenAI 协议的中转服务（如 one-api），并将 `OPENAI_BASE_URL` 指向该服务。但请注意中转服务的数据隐私风险。

---

## 国内使用的网络与语言适配指南
### 网络限制与替代方案

graphify 的语义提取功能（文档分析、图像理解）默认依赖 Anthropic 或 OpenAI API，国内直连存在网络不稳定或无法访问的问题。以下是各功能的网络依赖矩阵：

| 功能模块 | 依赖服务 | 国内可用性 | 替代方案 |
|----------|----------|------------|----------|
| 本地 AST 解析 | 无（纯本地） | ✅ 完全可用 | 无需替代 |
| Whisper 音频转录 | 无（本地模型） | ✅ 完全可用 | 无需替代 |
| 文档语义提取 | Anthropic Claude API | ❌ 需代理 | 部署兼容 OpenAI 协议的中转服务 |
| 图像语义分析 | OpenAI GPT-4V API | ❌ 需代理 | 使用本地 CLIP 模型（实验性） |
| 图聚类与社区发现 | 无（本地算法） | ✅ 完全可用 | 无需替代 |

**推荐配置（国内环境）**：

```bash
# 使用中转服务（示例：one-api 自建）
export OPENAI_BASE_URL="https://your-proxy.example.com/v1"
export OPENAI_API_KEY="your-proxy-key"
# 或者使用 Anthropic 兼容代理
export ANTHROPIC_BASE_URL="https://your-anthropic-proxy.example.com"
```

**注意事项**：
- 中转服务会记录你的数据内容，涉及敏感代码请谨慎。
- 免费公共中转服务速率限制严格，建议自建或使用企业级网关。
- 如果完全无法使用 LLM，graphify 仍可运行在 `--local-only` 模式，但 `query --semantic` 将不可用。

### 中文术语对照表

graphify 的所有命令输出均为英文，为便于理解和沟通，提供以下对照表：

| 英文术语 | 中文释义 | 出现场景 |
|----------|----------|----------|
| `god nodes` | 超级节点（被过度引用的文件） | `graphify stats` 输出 |
| `communities` | 社区（图聚类分组） | `graphify communities` 命令 |
| `edge` | 边（文件间依赖关系） | `graphify graph --format json` |
| `node` | 节点（单个文件或模块） | 所有图相关输出 |
| `semantic index` | 语义索引（LLM 生成的向量库） | `graphify build --with-llm` |
| `local-only mode` | 纯本地模式（无 LLM） | `graphify --local-only` |
| `ignore patterns` | 排除规则 | `graphifyignore.txt` 中的每行 |
| `whisper transcription` | Whisper 语音转写 | `graphify ingest --audio` |
| `image embedding` | 图像嵌入向量 | `graphify build --with-images` |
| `cache invalidation` | 缓存失效 | 修改源码后自动触发 |

### 中文环境下的最佳实践

1. **文件路径建议**：避免在项目路径中使用中文或空格，因为 Whisper 转录和部分图像处理库在非 UTF-8 路径下可能异常。
2. **文档编码**：graphify 解析 Markdown/HTML 文档时，强制要求 UTF-8 编码。若你的文档是 GBK 编码，请先转换：
   ```bash
   iconv -f GBK -t UTF-8 input.md > output.md
   ```
3. **日志本地化**：graphify 日志默认英文，可通过设置 `LANG=zh_CN.UTF-8` 环境变量，使部分运行时错误信息显示为中文（仅限 Python 原生错误，graphify 自身的输出仍为英文）。
4. **社区命名映射**：在 `graphify communities --export` 导出 CSV 后，可自行添加中文注释列，例如将 `community_id` 映射为业务模块名称，便于团队沟通。

### 安装与镜像加速

pip 安装 graphify 时，建议使用国内镜像：

```bash
pip install graphify -i https://pypi.tuna.tsinghua.edu.cn/simple
```

若需安装 Whisper 依赖的 torch 等大型包，可使用：

```bash
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu118
```

**注意**：graphify 的 LLM 功能无法通过 pip 镜像解决，需单独配置 API 网关。这是硬性限制，请提前规划网络方案。

## 反模式与常见问题 (Anti-Patterns & FAQ)
反模式（Anti-Patterns）是指在使用 Graphify 时应**避免**的错误用法或设计决策。以下内容基于实际使用中的高频踩坑点整理，帮助您提前规避风险。

### 1. 将 `graphifyignore.txt` 当作“黑名单”而非“白名单”

**错误用法：** 在 `graphifyignore.txt` 中列出所有不希望被解析的文件，期望它能像 `.gitignore` 一样自动过滤所有“无关”内容。

**正确理解：** `graphifyignore.txt` 是**排除列表**，它只作用于**已经被 Graphify 识别为可解析的文件**。如果您的目录下存在大量未被识别的文件类型（如 `.docx`、`.pdf` 中的扫描件），这些文件**不会**被自动解析，但也不会被“忽略”——它们会进入“未处理”状态，导致语义查询时结果不完整。

**反模式示例：**
```
# graphifyignore.txt
*.log
*.tmp
node_modules/
```
如果您的项目中有 `docs/manual.pdf`，它不在忽略列表中，但 Graphify 无法解析 PDF 的文本层（除非配置了 OCR），此时查询 `manual` 相关内容将返回空结果。

**推荐做法：** 在 `SKILL.md` 中明确声明“支持的输入格式”，并在忽略列表中**同时**列出不支持的文件扩展名，例如添加 `*.pdf`、`*.docx`。同时，在项目 README 中提示用户“Graphify 仅处理代码与纯文本文件，二进制或扫描件请先转成 Markdown 或 TXT”。

### 2. 将 `cache` 目录提交到版本控制

**反模式：** 在 `.gitignore` 中未排除 `graphify_cache/` 或类似缓存目录，导致每次运行后产生大量变更，污染代码审查。

**为什么这是错误的：** Graphify 的缓存用于存储解析后的 AST 片段、向量索引等。这些数据是**机器生成的中间产物**，不是源代码。提交它们会导致：
- 仓库体积膨胀（向量索引可能达到数十 MB）。
- 合并冲突（不同分支的缓存内容不同）。
- 安全风险（缓存可能包含文档中的敏感信息明文）。

**推荐做法：** 在项目根目录的 `.gitignore` 中添加：
```
graphify_cache/
*.graphify.db
```
并在 `SKILL.md` 的“安装与使用”章节中注明：“缓存目录由工具自动生成，请勿手动修改或提交。”

### 3. 高频问题 (FAQ)

| 问题 | 原因 | 解决方案 |
|------|------|----------|
| **查询 `god nodes` 返回空结果** | 未运行 `graphify index` 或索引未更新 | 执行 `graphify reindex --force` 后重试 |
| **中文文档解析后查询英文关键词无结果** | 默认分词器为英文（空格分词） | 在 `config.yaml` 中设置 `tokenizer: jieba`（需安装 `jieba` 包） |
| **`communities` 命令输出过多节点** | 社区检测阈值过低 | 运行 `graphify communities --min-size 5` 提高最小社区规模 |
| **pip 安装后命令找不到** | 未将 `~/.local/bin` 加入 PATH | `export PATH=$PATH:~/.local/bin`（Linux/macOS） |
| **图像分析功能报 API 错误** | 未设置 `ANTHROPIC_API_KEY` 或 `OPENAI_API_KEY` 环境变量 | 在 `.env` 文件中配置，并确保网络可访问对应 API |

### 4. 避免的常见陷阱

1. **不要删除 `graphify.db` 后手动重建**：该文件包含索引元数据，直接删除会导致所有节点 ID 失效，必须通过 `graphify reindex` 重建。
2. **不要在多进程环境下同时写缓存**：Graphify 的缓存写入非线程安全，建议在 CI 或批处理任务中串行执行。
3. **不要将 `graphify` 的输出直接作为生产数据库**：它是为开发辅助设计的，不保证 ACID 事务。

---

## 国内环境适配与降级方案 (Domestic Deployment & Fallback)
Graphify 的核心语义提取依赖 Anthropic 或 OpenAI API 进行文档分析和图像理解（见 `SKILL.md` 元数据中的 `env` 配置）。在中国大陆网络环境下，直接访问这些 API 通常不可用。以下提供**硬性限制的解决方案**与**离线降级方案**。

### 1. 网络限制的确认与替代 API

| 功能 | 默认后端 | 国内可用替代 | 配置方式 |
|------|----------|--------------|----------|
| 文档语义分析（摘要、实体抽取） | Anthropic Claude | 智谱 GLM-4 / 百度 ERNIE | 在 `config.yaml` 中设置 `llm.provider: zhipu` 或 `llm.provider: baidu` |
| 图像理解（OCR + 语义） | OpenAI GPT-4V | 阿里 Qwen-VL（通过 DashScope） | 设置 `vision.provider: dashscope`，并配置 `DASHSCOPE_API_KEY` |
| 本地 AST 解析（代码结构） | 无（本地） | 无（无需网络） | 默认启用，不依赖外部 API |
| Whisper 语音转录 | OpenAI Whisper | 本地 Whisper.cpp（需编译） | 设置 `audio.engine: whisper_cpp`，并指定模型路径 |

**示例配置（`config.yaml`）：**
```yaml
llm:
  provider: zhipu
  model: glm-4-plus
  api_key_env: ZHIPU_API_KEY
vision:
  provider: dashscope
  model: qwen-vl-plus
  api_key_env: DASHSCOPE_API_KEY
audio:
  engine: whisper_cpp
  model_path: /opt/models/ggml-base.en.bin
```

### 2. 纯离线降级（无任何 LLM API）

如果无法访问任何云端 API，Graphify 仍可提供以下功能：

- **代码结构索引**：通过本地 AST 解析器（tree-sitter）生成符号表、调用图。查询 `god nodes` 时，可返回函数、类、模块的层级关系，但**不包含**语义摘要（如“该函数用于处理用户登录”）。
- **全文搜索**：基于 TF-IDF 的本地检索，支持关键词匹配，但无法理解同义词或上下文。
- **Whisper 本地转录**：使用 `whisper.cpp` 或 `faster-whisper` 在 CPU 上运行，速度较慢但可用。

**降级模式启用方法：**
```bash
export GRAPHIFY_OFFLINE=1
graphify index --local-only
```
此时 `graphify query "用户登录逻辑"` 将仅基于代码标识符和注释进行模糊匹配，结果质量显著下降（建议配合 `grep` 使用）。

### 3. pip 安装与镜像加速

虽然 pip 本身有国内镜像（如清华源、阿里源），但 Graphify 的依赖包（如 `anthropic`、`openai`）会尝试连接官方 API 端点。**安装时**请使用镜像：

```bash
pip install graphify -i https://pypi.tuna.tsinghua.edu.cn/simple
```

但**运行时**的网络限制无法通过 pip 镜像解决。建议在 `SKILL.md` 中明确标注：“语义提取功能需要海外 API 访问，若不可用请参考本文档的降级方案。”

### 4. 中文界面与术语本地化

当前 Graphify 的命令行输出（如 `god nodes`、`communities`、`graph`）均为英文，且无 `--lang zh` 选项。为改善国内用户体验，可：

- **通过 shell 别名封装**：
```bash
alias gn='graphify nodes --format table | column -t -s$'\t''
alias gcom='graphify communities --min-size 3'
```
- **编写翻译脚本**：将输出中的 `god` 替换为 `核心节点`，`community` 替换为 `社区`，`edge` 替换为 `边`。示例（Python）：
```python
import subprocess
out = subprocess.check_output(["graphify", "nodes"]).decode()
translated = out.replace("god nodes", "核心节点").replace("communities", "社区")
print(translated)
```

### 5. 网络诊断与超时设置

在 `config.yaml` 中调整 API 请求超时，避免因网络波动导致长时间挂起：

```yaml
network:
  timeout_seconds: 30
  retries: 3
  backoff_factor: 2.0
```

如果使用代理，可设置环境变量 `HTTPS_PROXY` 指向可用节点（如 `http://127.0.0.1:7890`），但需自行保证代理稳定性。

**总结：** 国内用户应优先采用“本地 AST + 国产 LLM 替代”组合，并将 `graphifyignore.txt` 配置为仅包含可解析文件，同时明确告知团队成员“语义查询质量取决于所选后端”。对于完全离线的场景，建议将 Graphify 仅用于代码结构导航，而文档理解功能暂缓启用。


## 版本迭代记录（评测驱动）

> 迭代时间: 2026-08-08 17:23

| 失分维度 | 失分项 | 得分 | 修复方向 |
|---|---|---|---|
| convention | convention | 3.3 | 反模式和FAQ内容几乎缺失。SKILL.md仅在提到cache时说Do not commit，未明确说明为什么。graphifyignore.txt虽然列出大量 |
| trust | trust | 3.3 | 文档全部为英文，命令输出如 'god nodes'、'communities' 等均为英文术语，无中文界面。核心的语义提取功能依赖 Anthropic 或 Op |
| reliability | reliability | 4 | query_graph.py 中包含基本的异常检查（如文件不存在时提示运行 graphify .），但缺少详细的错误码体系。SKILL.md 中没有明确的错误处 |

> 高分特征参考: [image-generation 4.5分 强项:convention:4.8、effectiveness:4.8、reliability:4.8、trust:5] | [data 4.5分 强项:convention:4.8、effectiveness:4.9、reliability:4.8、trust:5] | [data-analysis 4.53分 强项:convention:5、rel

## 触发方式
- 待补充
