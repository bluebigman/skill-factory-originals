---
slug: eycap
name: eycap
displayName: 部署配方 生成校验 运维脚本
description: 生成、校验与解释 Engine Yard 平台的 Capistrano 部署配方。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 林栖
agent_created: true
trigger_words: ["eycap", "Engine Yard", "Capistrano 配方", "部署脚本生成", "EY 部署配置", "部署任务编写", "配方校验"]
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# eycap — Engine Yard 部署配方工作台

## 一、能力边界（一页纸速查卡）

### 1.1 能做什么

| 编号 | 能力项 | 说明 | 输入要求 |
|------|--------|------|----------|
| C1 | 配方生成 | 根据应用类型、Ruby 版本、数据库配置等参数，生成 Capistrano 部署配方骨架 | 提供应用栈参数（见 3.2 参数表） |
| C2 | 配方校验 | 检查已有配方的语法正确性、任务依赖完整性、路径引用有效性 | 提供 `.cap` 或 `config/deploy.rb` 文件路径 |
| C3 | 配方解释 | 将配方文件中的任务、钩子、变量展开为人类可读的执行流程图 | 提供配方文件路径 |
| C4 | 批量处理 | 对同一目录下多个配方文件执行统一操作（生成/校验/解释） | 目录路径 + 文件命名前缀 |

### 1.2 不能做什么

- 不能代替你执行部署动作（本 Skill 只产出文本，不触发真实服务器操作）。
- 不能识别 Engine Yard 平台未公开的私有 API 或内部参数。
- 不能自动修复语法错误——只给出定位与修改建议。
- 不能处理加密的配方文件或需要密钥才能读取的内容。

### 1.3 适用对象

- 使用 Engine Yard 云平台部署 Ruby 应用的开发/运维人员。
- 需要将既有部署流程迁移到 Capistrano 体系的团队。
- 对部署脚本做代码审查的工程效率角色。

---

## 二、触发方式与场景映射

### 2.1 触发词

直接使用 `eycap` 或以下任一场景词即可激活本 Skill：

| 触发词 | 典型用户原话 | 本 Skill 响应动作 |
|--------|--------------|-------------------|
| eycap | "用 eycap 帮我看看这个部署脚本" | 进入配方校验模式 |
| Engine Yard | "Engine Yard 上跑 Rails 7 的部署配方怎么写" | 进入配方生成模式 |
| Capistrano 配方 | "帮我解释一下这个 cap 文件里的 after 钩子" | 进入配方解释模式 |
| 部署脚本生成 | "生成一个带 sidekiq 的部署脚本" | 进入配方生成模式（含任务扩展） |
| EY 部署配置 | "EY 的 database.yml 配置在配方里怎么处理" | 进入配方解释/生成混合模式 |
| 部署任务编写 | "写一个自定义部署任务，在编译 assets 之前执行迁移" | 进入配方生成模式（自定义任务） |

### 2.2 场景映射表

| 用户场景 | 推荐模式 | 输出物 |
|----------|----------|--------|
| 新项目上线，需要第一版部署配方 | 生成模式 | `deploy.rb` 骨架 + 参数说明 |
| 现有配方报错，需要定位问题 | 校验模式 | 错误清单 + 修正建议 |
| 接手他人项目，需要理解部署流程 | 解释模式 | 分步执行流程图 + 关键变量表 |
| 批量检查多个应用仓库的配方一致性 | 批量校验 | 逐文件校验报告 + 差异对比表 |

---

## 三、标准流程

### 3.1 前置条件

| 条件项 | 要求 | 缺失时的处理 |
|--------|------|--------------|
| 输入文件 | 配方文件为 `.rb` 后缀，或目录中包含 `deploy.rb` / `Capfile` | 提示用户提供文件路径，不猜测 |
| 命名规范 | 批量操作时，文件需以统一前缀命名（如 `app_*.rb`） | 列出目录内实际文件名，请用户确认范围 |
| 环境参数 | 生成模式需提供 Ruby 版本、应用服务器（Puma/Unicorn）、数据库类型 | 缺失时输出 `[需核实:ruby_version]` 占位，不编造默认值 |
| 备份要求 | 批量执行前，确认原始文件已备份 | 未备份则中止操作，提示先备份 |

### 3.2 执行步骤（生成模式）

**Step 1 — 收集参数**

| 参数名 | 必填 | 可选值/格式 | 示例 |
|--------|------|-------------|------|
| `app_name` | 是 | 小写字母+数字+下划线 | `my_app` |
| `ruby_version` | 是 | 形如 `3.2.2` | `3.2.2` |
| `app_server` | 是 | `puma` / `unicorn` | `puma` |
| `db_type` | 是 | `postgresql` / `mysql` / `sqlite` | `postgresql` |
| `worker` | 否 | `sidekiq` / `delayed_job` / 无 | `sidekiq` |
| `extra_tasks` | 否 | 逗号分隔的任务名列表 | `migrate,assets` |

**Step 2 — 生成骨架**

输出 `deploy.rb` 文件，包含以下固定区块：

```ruby
# 基础配置
set :application, 'my_app'
set :repo_url, 'git@example.com:my_app.git'

# 环境配置
set :stage, :production
set :branch, 'main'

# 服务器配置
set :deploy_to, '/var/www/my_app'

# 框架集成
namespace :deploy do
  # 任务定义区
end
```

**Step 3 — 输出参数说明表**

生成文件后，附一张参数对照表，说明每个 `set` 语句的含义与可调整项。

**Step 4 — 自检**

对生成的配方执行一次内部校验（调用校验逻辑），确认无语法错误后交付。

### 3.3 执行步骤（校验模式）

**Step 1 — 读取文件**

读取目标配方文件全文，记录行号。

**Step 2 — 语法检查**

使用 Ruby 语法解析器检查语法错误。输出格式：

```
[错误] 第 12 行：未闭合的 do 块
[警告] 第 34 行：变量 `:branch` 未在任意位置定义
```

**Step 3 — 依赖检查**

检查 `after` / `before` 钩子引用的任务是否存在。

**Step 4 — 路径检查**

检查配方中引用的本地路径（如 `shared_path`、`release_path`）是否符合 Capistrano 目录规范。

**Step 5 — 输出报告**

| 严重级别 | 数量 | 说明 |
|----------|------|------|
| 错误 | 2 | 必须修复 |
| 警告 | 3 | 建议修复 |
| 提示 | 1 | 可选优化 |

### 3.4 执行步骤（解释模式）

**Step 1 — 解析配方**

将配方拆解为：变量定义、任务定义、钩子绑定、命名空间。

**Step 2 — 生成执行流程图**

以文本形式输出执行顺序：

```
deploy:starting
  → deploy:check
  → deploy:updating
    → git:clone
    → bundle:install
    → deploy:assets:precompile
  → deploy:publishing
  → deploy:finishing
```

**Step 3 — 关键变量表**

| 变量名 | 当前值 | 作用域 | 影响范围 |
|--------|--------|--------|----------|
| `:deploy_to` | `/var/www/my_app` | 全局 | 所有路径的根目录 |
| `:branch` | `main` | 全局 | 拉取代码的分支 |

### 3.5 输出规范

- 所有输出使用 Markdown 格式，代码块标注语言。
- 错误信息必须包含行号与具体原因。
- 生成的文件内容直接输出在代码块中，不额外提供下载链接。

---

## 四、置信度门控

### 4.1 占位符规则

当输入信息不足以生成准确内容时，使用 `[需核实:字段名]` 格式占位，并附说明。

| 场景 | 占位示例 | 后续处理 |
|------|----------|----------|
| 未提供 Ruby 版本 | `[需核实:ruby_version]` | 提示用户补充，或建议查询 Engine Yard 支持矩阵 |
| 未指定应用服务器 | `[需核实:app_server]` | 提示用户选择 Puma 或 Unicorn |
| 配方中引用了未知任务 | `[需核实:task_name]` | 列出配方中所有任务名，请用户确认 |

### 4.2 禁止行为

- 不猜测缺失参数的具体值。
- 不假设 Engine Yard 平台的默认配置。
- 不输出未经确认的路径或版本号。

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| E1001 | 文件不存在 | "未找到指定文件，请确认路径是否正确" | 检查路径；使用绝对路径或相对路径重新输入 |
| E1002 | 语法错误 | "配方存在语法错误，已定位到第 N 行" | 根据行号修复；可请求本 Skill 输出该行上下文 |
| E1003 | 钩子引用缺失 | "after 钩子引用了未定义的任务 `xxx`" | 在配方中补充该任务定义，或移除该钩子 |
| E1004 | 参数缺失 | "生成模式缺少必填参数 `app_name`" | 参考 3.2 参数表补齐 |
| E1005 | 批量命名不匹配 | "目录下未找到符合前缀 `app_` 的文件" | 列出实际文件名，请用户确认或调整前缀 |
| E1006 | 备份未确认 | "批量操作前需确认原始文件已备份" | 执行备份命令后重新发起操作 |

---

## 六、FAQ 反模式

### 6.1 常见坑

| 坑编号 | 典型错误操作 | 后果 | 正确做法 |
|--------|--------------|------|----------|
| P1 | 直接复制网上配方不校验 | 环境不匹配导致部署失败 | 先运行校验模式，再按报告修正 |
| P2 | 在配方中硬编码服务器 IP | 环境迁移后配方失效 | 使用变量或从环境变量读取 |
| P3 | 忽略 `before` / `after` 钩子顺序 | 任务执行顺序错乱 | 使用解释模式查看完整流程图 |
| P4 | 批量操作前不备份 | 误操作后无法回滚 | 强制先备份，再执行批量 |
| P5 | 使用绝对路径而非 Capistrano 变量 | 多环境部署时路径冲突 | 统一使用 `shared_path`、`release_path` |

### 6.2 反模式对照表

| 反模式 | 反例 | 正例 |
|--------|------|------|
| 无参数生成 | "给我一个部署配方" | "生成一个 Rails 7 + Puma + PostgreSQL 的部署配方" |
| 无校验修改 | "帮我把第 5 行改成 xxx" | "先校验这个文件，再告诉我第 5 行怎么改" |
| 无解释执行 | "这个配方是干嘛的" | "解释一下这个配方里 deploy:restart 任务的执行逻辑" |

---

## 七、渐进式披露

### 7.1 速查卡（30 秒上手）

```
eycap 三件事：
1. 生成 → 给参数，出骨架
2. 校验 → 给文件，出报告
3. 解释 → 给文件，出流程图
```

### 7.2 新手路径

1. 先读「能力边界」确认本 Skill 能帮你做什么。
2. 用「生成模式」产出一个基础配方。
3. 用「校验模式」检查生成结果。
4. 用「解释模式」理解每个任务的作用。

### 7.3 进阶路径

1. 自定义任务编写：在生成模式下通过 `extra_tasks` 参数添加自定义任务。
2. 批量配方一致性检查：使用批量校验模式，对比多个应用的配方差异。
3. 钩子链优化：通过解释模式分析钩子执行顺序，优化部署流程。

---

## 八、用户协议

使用本 Skill 生成的任何内容（包括但不限于配方文件、校验报告、解释文档），使用者自行承担全部责任。本 Skill 仅提供文本生成与解释服务，不参与任何实际部署操作，不对部署结果承担任何直接或间接责任。

使用者不得对本 Skill 生成的文本内容进行反向工程、反编译或试图提取底层算法逻辑。

<!-- user-agreement-injected -->

---

## 九、许可证（License）

本 Skill 采用 MIT 许可证发布：

```
MIT License

Copyright (c) 2024 林栖

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
