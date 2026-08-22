---
slug: awesome-go
name: awesome-go
displayName: Go选型导航 框架库工具速查
description: 快速定位Go生态优质框架、库与工具，输出结构化清单与选型参考。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: GoEcoNavigator
agent_created: true
trigger_words: ["awesome-go", "go资源", "go框架", "go库", "go工具", "go生态", "golang选型", "go组件"]
---

> 本内容由 AI 生成，仅供学习参考 <!-- ai-generated-notice -->

# Go 生态资源检索与选型参考 Skill

## 一、能力边界：一页纸速查卡

### 1.1 本 Skill 能做什么

| 能力项 | 说明 | 示例 |
|--------|------|------|
| 关键词检索 | 按分类或名称查找 Go 资源 | 输入"ORM 库"返回相关项目清单 |
| 结构化输出 | 以表格或 JSON 呈现资源关键字段 | 名称、描述、分类、星标数、更新时间 |
| 分类导航 | 按预定义分类浏览资源 | `--category 日志库` 列出该分类全部条目 |
| 排序筛选 | 按星标、更新时间等字段排序 | `--sort stars` 按热度降序 |
| 字段定制 | 自定义输出字段集合 | `--fields name,stars,description` |
| 格式切换 | 支持 Markdown 表格与 JSON 输出 | `--format json` 便于程序处理 |

### 1.2 本 Skill 不能做什么

| 限制项 | 说明 |
|--------|------|
| 不提供代码示例 | 仅返回资源元数据，不包含用法代码 |
| 不保证数据实时性 | 知识库为静态快照，星标数等字段存在滞后 |
| 不进行质量评级 | 不输出"推荐指数"或"最佳选择"等主观评价 |
| 不比较同类项目 | 不自动生成 A/B 对比结论，仅并列展示数据 |
| 不解析任意 URL | 仅识别预置知识库中的资源，不抓取外部网页 |

### 1.3 适用对象

- **Go 初学者**：快速了解生态中有哪些主流组件可选。
- **后端工程师**：在项目启动阶段做技术选型调研。
- **技术负责人**：需要结构化清单用于团队评审或采购决策。
- **自动化脚本**：通过 JSON 输出对接内部选型对比流程。

---

## 二、触发方式：场景映射表

| 你可能会这样说 | 本 Skill 如何响应 |
|----------------|-------------------|
| "Go 有哪些 Web 框架？" | 返回 Web 框架分类下的资源清单 |
| "帮我找找日志库" | 映射到"日志库"分类，输出该分类全部条目 |
| "看看最近更新的 CLI 工具" | 按更新时间排序输出 CLI 工具分类 |
| "有没有好用的 Redis 客户端" | 关键词匹配"Redis"与"客户端"，返回相关条目 |
| "awesome-go --sort stars" | 全局按星标数降序输出前 20 条 |
| "awesome-go --category 数据库驱动 --format json" | 输出指定分类的 JSON 格式数据 |

**触发词列表**：`awesome-go`、`go资源`、`go框架`、`go库`、`go工具`、`go生态`、`golang选型`、`go组件`

---

## 三、标准流程：从输入到输出

### 3.1 前置条件

- 本 Skill 为纯本地运行，无需网络连接。
- 默认知识库路径为 Skill 内置目录；如需自定义，设置环境变量 `AWESOME_GO_DATA_DIR` 指向数据目录。
- 输入文件（如批量查询列表）需为 UTF-8 编码的纯文本，每行一个查询词。

### 3.2 执行步骤

1. **解析输入**：提取查询关键词、资源名称、文件路径及附加参数（`--category`、`--sort`、`--format`、`--fields`）。
2. **领域匹配**：将关键词映射到预定义分类表（见 3.4 节）。若关键词命中多个分类，按匹配度排序返回。
3. **数据提取**：从知识库中检索匹配资源，提取字段：`name`、`description`、`category`、`stars`、`updated_at`、`url`。
4. **置信度评估**：对每条资源逐字段检查完整性。缺失字段标注 `[需核实:字段名]`，不猜测填充。
5. **结果生成**：按用户指定格式输出。默认 Markdown 表格，列顺序为：名称、分类、描述、星标、更新时间。
6. **完整性自查**：检查输出是否包含全部请求字段；若 `--fields` 指定了不存在的字段，返回错误码 `E4004`。

### 3.3 输出规范

**Markdown 表格示例**：

| 名称 | 分类 | 描述 | 星标 | 更新时间 |
|------|------|------|------|----------|
| gin | Web框架 | 高性能 HTTP Web 框架 | 78000 | 2024-11-01 |
| zap | 日志库 | 结构化日志库，低分配 | 22000 | 2024-10-15 |

**JSON 输出示例**：

```json
[
  {
    "name": "gin",
    "category": "Web框架",
    "description": "高性能 HTTP Web 框架",
    "stars": 78000,
    "updated_at": "2024-11-01",
    "url": "https://github.com/gin-gonic/gin"
  }
]
```

### 3.4 分类表（预定义）

| 分类ID | 分类名称 | 覆盖范围 |
|--------|----------|----------|
| web | Web框架 | 路由、中间件、全栈框架 |
| log | 日志库 | 结构化日志、日志轮转、日志聚合 |
| db | 数据库驱动 | SQL/NoSQL 客户端、ORM、迁移工具 |
| cli | CLI工具 | 命令行解析、终端交互、进度条 |
| net | 网络库 | HTTP客户端、RPC、消息队列、Socket |
| test | 测试工具 | 断言、Mock、覆盖率、基准测试 |
| crypto | 加密库 | 哈希、签名、加密算法实现 |
| misc | 其他 | 未归类的实用工具 |

---

## 四、置信度门控：不编造，只标注

### 4.1 缺失字段处理规则

| 场景 | 处理方式 |
|------|----------|
| 知识库中该资源缺少 `stars` 字段 | 输出 `[需核实:stars]` |
| 知识库中该资源缺少 `updated_at` 字段 | 输出 `[需核实:updated_at]` |
| 知识库中该资源缺少 `description` 字段 | 输出 `[需核实:description]` |
| 查询词未命中任何分类 | 返回错误码 `E4001`，不输出空表 |

### 4.2 置信度分级

| 级别 | 判定条件 | 输出行为 |
|------|----------|----------|
| 高 | 全部字段完整 | 正常输出，无标注 |
| 中 | 1-2 个字段缺失 | 输出占位符 `[需核实:字段名]` |
| 低 | 3 个及以上字段缺失 | 输出占位符，并在表格末尾追加一行提示："部分条目信息不完整，建议访问 GitHub 核实" |

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| E4001 | 未匹配到任何分类 | "未找到与 'xxx' 相关的 Go 资源分类" | 检查关键词拼写；尝试更宽泛的词汇，如"数据库"而非"pg" |
| E4002 | 输入文件不存在 | "指定的文件路径不存在，请检查路径" | 确认文件路径；使用绝对路径 |
| E4003 | 输入文件格式错误 | "文件格式不支持，仅接受 UTF-8 纯文本" | 转换文件编码；去除 BOM 头 |
| E4004 | 字段名无效 | "字段 'xxx' 不在支持列表中，可用字段：name, description, category, stars, updated_at, url" | 参照提示修正 `--fields` 参数 |
| E4005 | 排序字段无效 | "排序字段仅支持 stars 或 updated_at" | 修正 `--sort` 参数 |
| E4006 | 分类不存在 | "分类 'xxx' 不存在，可用分类：web, log, db, cli, net, test, crypto, misc" | 参照提示修正 `--category` 参数 |

---

## 六、FAQ 反模式对照

### 6.1 常见坑与正确姿势

| 反模式 | 问题描述 | 正确做法 |
|--------|----------|----------|
| 过度依赖星标数 | 认为星标高就是"最好"，忽略项目维护状态 | 结合 `updated_at` 字段判断活跃度；访问 GitHub 查看 issue 响应速度 |
| 忽略置信度标注 | 直接使用 `[需核实:字段]` 的数据做决策 | 对标注条目单独核实后再纳入选型对比 |
| 分类词过于具体 | 输入"postgresql 连接池"但知识库无此细分 | 使用上级分类"数据库驱动"或"连接池" |
| 批量文件含空行 | 空行导致解析中断 | 预处理文件，删除空行；每行仅一个查询词 |
| 混淆输出格式 | 在 `--format json` 下仍期望 Markdown 表格 | 明确指定格式；JSON 输出适合程序解析，人工阅读用默认格式 |

### 6.2 反模式示例

**反模式**：`awesome-go --category 微服务框架 --sort stars`  
**问题**：分类表中无"微服务框架"，返回 E4006。  
**修正**：使用 `web` 分类，或先执行 `awesome-go --category web` 查看全部 Web 框架再自行筛选。

---

## 七、渐进式披露：分层次阅读路径

### 7.1 速查卡（30 秒上手）

```
输入：awesome-go 日志库
输出：日志库分类的 Markdown 表格

输入：awesome-go --sort stars --fields name,stars
输出：全库按星标降序的名称与星标列表

输入：awesome-go --category db --format json
输出：数据库驱动分类的 JSON 数组
```

### 7.2 新手路径（首次使用）

1. 阅读「一、能力边界」了解能做什么、不能做什么。
2. 用 `awesome-go Web框架` 体验基本输出。
3. 尝试 `--category` 限定范围，观察分类表结构。
4. 对感兴趣的条目，复制 `url` 字段到浏览器访问 GitHub。

### 7.3 进阶路径（深度使用）

1. 准备批量查询文件，每行一个分类名，执行 `awesome-go --file query.txt --format json`。
2. 将 JSON 输出导入电子表格，建立自己的选型对比表。
3. 对置信度标注为"中"或"低"的条目，建立人工核实流程（如每周核查一次）。
4. 结合 `--fields` 定制输出，仅保留决策所需字段，减少信息噪音。

---

## 八、参数速查表

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `--category` | string | 无 | 限定分类，取值见 3.4 节 |
| `--sort` | string | 无 | 排序字段，仅支持 `stars` 或 `updated_at` |
| `--format` | string | `markdown` | 输出格式，支持 `markdown` 或 `json` |
| `--fields` | string | 全部字段 | 逗号分隔的字段列表 |
| `--file` | string | 无 | 批量查询文件路径，每行一个查询词 |
| `--selftest` | flag | 无 | 运行内置自检，验证知识库完整性 |
| `--version` | flag | 无 | 输出版本号 |

---

## 九、用户协议

**使用本 Skill 即表示您同意以下条款：**

1. **责任承担**：使用者应自行承担因使用本 Skill 产生的全部责任。本 Skill 提供的信息仅供参考，不构成任何形式的保证或承诺。
2. **禁止反向工程**：使用者不得对本 Skill 的内置知识库结构、算法逻辑进行反向工程、反编译或试图提取源代码。
3. **合规使用**：使用者应遵守所在国家/地区的法律法规，不得将本 Skill 用于任何非法目的或侵犯第三方权益的行为。
4. **内容变更**：本 Skill 可能随时更新或下线，作者保留在不另行通知的情况下修改、暂停或终止本 Skill 的权利。

<!-- user-agreement-injected -->

---

## 十、许可证（License）

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

<!-- professional-license-embedded -->
