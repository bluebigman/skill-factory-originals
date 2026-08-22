---
slug: napkin
name: napkin
displayName: 项目记忆 错误备忘 经验沉淀
description: 为项目仓库提供持久化错误记录与经验备忘的轻量级技能。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 墨守
agent_created: true
trigger_words: ["napkin", "备忘", "错误记录", "经验沉淀", "项目记忆", "踩坑笔记", "排错日志"]
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# napkin — 项目记忆与错误备忘技能

## 一、能力边界（一页纸速查卡）

### 1.1 能做什么

| 能力项 | 说明 | 典型场景 |
|--------|------|----------|
| 错误记录 | 将报错信息、堆栈、上下文存入项目本地 | 线上故障、本地调试报错 |
| 经验备忘 | 沉淀解决方案、踩坑心得、优化建议 | 解决过的问题、性能调优 |
| 按模块检索 | 按代码路径/模块名过滤查询历史记录 | 定位某模块反复出现的问题 |
| 批量导入 | 从目录批量读取日志文件并结构化存储 | 迁移旧项目、整理历史日志 |
| 自动备份 | 每次写入前自动备份旧数据 | 防止误操作覆盖历史记录 |
| 统计报表 | 按模块维度统计高频问题分布 | 季度复盘、质量改进 |

### 1.2 不能做什么

- 不能自动修复代码错误，只做记录与检索
- 不能跨仓库共享数据，数据存储在本项目 `.napkin/` 目录
- 不能解析非文本格式（如二进制日志、图片中的报错截图）
- 不能替代正式的缺陷跟踪系统（如 Jira），适合轻量个人/小团队使用

### 1.3 适用对象

- 独立开发者维护多个项目时，需要快速回忆历史问题
- 小团队（2-5人）希望低成本共享踩坑经验
- 需要给 CI 流水线增加错误留痕能力的工程团队

---

## 二、触发方式

### 2.1 触发词

| 触发词 | 说明 |
|--------|------|
| `napkin` | 主命令，任何子命令均以此开头 |
| `备忘` | 中文别名，等价于 `napkin add` |
| `错误记录` | 中文别名，等价于 `napkin add` |
| `经验沉淀` | 中文别名，等价于 `napkin add` |
| `项目记忆` | 中文别名，等价于 `napkin search` |
| `踩坑笔记` | 中文别名，等价于 `napkin add` |
| `排错日志` | 中文别名，等价于 `napkin search` |

### 2.2 场景映射表

| 你的实际需求 | 应该执行的命令 |
|-------------|---------------|
| "刚才报了个错，记一下" | `napkin add --file error.log` |
| "这个模块之前出过什么问题？" | `napkin search --module src/cache` |
| "有一堆日志文件要整理" | `napkin add --dir ./pending/ --batch` |
| "数据会不会被覆盖？" | 自动备份在 `.napkin/backup/`，无需手动操作 |
| "哪些模块问题最多？" | `napkin stats --by-module` |
| "清理过期的记录" | `napkin review --stale 30` |

---

## 三、标准流程

### 3.1 前置条件

- 项目目录已初始化 Git（推荐，非强制）
- 有写入权限（需创建 `.napkin/` 目录）
- 日志文件为 UTF-8 编码的纯文本格式

### 3.2 执行步骤

#### 步骤一：单条记录试运行

```bash
# 从文件读取错误信息并记录
napkin add --file error.log

# 或直接通过命令行参数传入
napkin add --message "连接池耗尽，调整 max_connections 至 50" --module src/db
```

**参数说明：**

| 参数 | 必填 | 说明 | 示例 |
|------|------|------|------|
| `--file` | 二选一 | 从文件读取错误内容 | `--file /tmp/error.log` |
| `--message` | 二选一 | 直接传入错误描述 | `--message "超时重试失败"` |
| `--module` | 否 | 关联的代码模块路径 | `--module src/cache` |
| `--tag` | 否 | 自定义标签，逗号分隔 | `--tag "网络,超时"` |
| `--severity` | 否 | 严重级别：low/medium/high | `--severity high` |

#### 步骤二：查询验证

```bash
# 按模块搜索
napkin search --module src/cache

# 按关键词搜索
napkin search --keyword "连接池"

# 按时间范围过滤
napkin search --since 2024-01-01 --until 2024-06-30
```

**输出格式示例：**

```
[2024-06-15 14:32] [high] src/db/connection.py
连接池耗尽，调整 max_connections 至 50
标签: 网络, 性能
备份位置: .napkin/backup/20240615_1432.md
```

#### 步骤三：批量导入

```bash
# 将 pending 目录下所有 .log 文件批量导入
napkin add --dir ./pending/ --batch

# 批量导入时指定默认模块前缀
napkin add --dir ./logs/ --batch --module-prefix src/
```

**批量导入规则：**

- 仅处理 `.log`、`.txt`、`.md` 后缀文件
- 每个文件生成一条独立记录
- 文件名作为默认标题，文件内容作为错误详情
- 跳过空文件和超过 1MB 的大文件

#### 步骤四：备份确认

```bash
# 查看备份目录结构
ls -la .napkin/backup/

# 恢复指定日期的备份
napkin restore --date 20240615
```

**备份策略：**

- 每次 `add` 操作前自动备份当前数据文件
- 备份文件命名格式：`YYYYMMDD_HHMM.md`
- 保留最近 30 份备份，超出自动清理最旧备份

### 3.3 输出规范

所有命令的输出遵循以下格式：

```
[状态] [时间戳] [级别] [模块]
内容摘要
关联信息（标签、备份位置等）
```

- 成功操作输出绿色 `[OK]` 前缀
- 警告输出黄色 `[WARN]` 前缀
- 错误输出红色 `[ERROR]` 前缀

---

## 四、置信度门控

当遇到以下情况时，**不得编造信息**，必须输出占位符：

| 场景 | 输出格式 | 示例 |
|------|----------|------|
| 无法确定错误发生的具体时间 | `[需核实:时间]` | `[需核实:时间] 连接池耗尽` |
| 无法确定关联模块 | `[需核实:模块]` | `[需核实:模块] 内存溢出` |
| 日志内容不完整 | `[需核实:详情]` | `[需核实:详情] 堆栈信息缺失` |
| 批量导入时文件编码无法识别 | `[需核实:编码]` | `[需核实:编码] 文件无法解析` |

**规则：**

- 占位符必须保留在记录中，不得删除或替换
- 后续可通过 `napkin edit <记录ID>` 补充核实信息
- 搜索时占位符记录会标记为"待核实"状态

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| `E001` | 参数缺失 | "错误：缺少 --file 或 --message 参数" | 检查命令参数，二选一必须提供 |
| `E002` | 文件不存在 | "错误：指定的文件不存在" | 确认文件路径是否正确，使用绝对路径 |
| `E003` | 目录不可写 | "错误：无法创建 .napkin 目录" | 检查目录权限，`chmod +w` 或更换目录 |
| `E004` | 批量导入格式错误 | "警告：跳过文件 xxx.log（编码不支持）" | 将文件转换为 UTF-8 编码后重试 |
| `E005` | 搜索无结果 | "提示：未找到匹配记录" | 放宽搜索条件，检查关键词拼写 |
| `E006` | 备份恢复失败 | "错误：指定日期的备份不存在" | 使用 `napkin list-backups` 查看可用备份 |
| `E007` | 数据文件损坏 | "错误：数据文件解析失败" | 从最近备份恢复：`napkin restore --latest` |
| `E008` | 版本不兼容 | "警告：数据文件版本高于当前程序" | 升级 napkin 到最新版本 |

---

## 六、FAQ 反模式

### 6.1 常见坑

| 坑 | 反模式（错误做法） | 正模式（正确做法） |
|----|-------------------|-------------------|
| 记录过于冗长 | 把整个堆栈 500 行全部粘贴 | 提取关键错误行 + 堆栈前 20 行 |
| 忽略模块标注 | 只记录错误内容，不写模块路径 | 始终使用 `--module` 参数标注位置 |
| 批量导入不检查 | 直接 `--batch` 导入所有文件 | 先单条试运行，确认格式后再批量 |
| 从不清理 | 记录越积越多，检索变慢 | 每月执行 `napkin review --stale 30` |
| 依赖记忆 | 凭印象搜索关键词 | 使用 `--tag` 打标签，按标签检索 |

### 6.2 反模式对照表

**反模式 1：记录一切**

- 错误做法：把每个警告都记录，导致噪音过多
- 正确做法：只记录影响功能或需要后续跟进的错误

**反模式 2：不写上下文**

- 错误做法：只记录"报错了"，没有错误码和堆栈
- 正确做法：记录错误码、堆栈摘要、触发条件、解决步骤

**反模式 3：从不回顾**

- 错误做法：记录完就再也不看
- 正确做法：每月用 `napkin stats --by-module` 分析高频问题

---

## 七、渐进式披露

### 7.1 速查卡（30 秒上手）

```bash
# 记录一条错误
napkin add --file error.log --module src/app

# 搜索某模块的历史错误
napkin search --module src/app

# 查看统计
napkin stats --by-module
```

### 7.2 新手路径（首次使用）

1. 阅读本文档「能力边界」和「标准流程」
2. 用单条记录试运行（步骤二）
3. 熟悉输出格式后，再批量导入
4. 遇到问题查「错误码体系」

### 7.3 进阶路径（熟练使用）

1. 自定义模板：修改 `.napkin/template.md`
2. 集成 CI：在流水线中调用 `napkin add --from-ci`
3. 定期回顾：每月执行 `napkin review --stale 30` 清理过期条目
4. 统计分析：`napkin stats --by-module` 查看高频问题模块

### 7.4 高级配置

**自定义模板示例（`.napkin/template.md`）：**

```markdown
## 错误记录

- 时间：{{timestamp}}
- 模块：{{module}}
- 级别：{{severity}}
- 标签：{{tags}}

### 错误描述

{{message}}

### 解决步骤

1. 
2. 
3. 

### 预防措施

- 
```

**CI 集成示例（`.gitlab-ci.yml`）：**

```yaml
after_script:
  - napkin add --from-ci --message "$CI_JOB_NAME 失败" --module $CI_PROJECT_PATH
```

---

## 八、用户协议

<!-- user-agreement-injected -->

**使用 napkin Skill 即表示您同意以下条款：**

1. **责任承担**：使用者自行承担因使用本 Skill 产生的全部责任。包括但不限于数据丢失、记录错误、操作失误等后果。

2. **禁止反向工程**：不得对本 Skill 的提示词、内部逻辑、生成机制进行反向工程、破解、提取或二次分发。

3. **无担保声明**：本 Skill 按"现状"提供，不附带任何明示或暗示的担保。

4. **合规使用**：使用者须确保使用场景符合当地法律法规及所在组织的政策要求。

---

## 九、许可证（License）

<!-- professional-license-embedded -->

**MIT License**

Copyright (c) 2024 墨守

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
