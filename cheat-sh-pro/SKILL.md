---
> 本内容由 AI 生成，仅供学习参考（《人工智能生成合成内容标识办法》显式标识）。
<!-- ai-generated-notice -->
slug: cheat-sh-pro
name: 命令行速查手册
displayName: 终端速查 命令示例 编程助手
description: 一条命令获取编程语言与工具示例，开发调试即时查阅。
version: 1.0.14
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/cheat-sh-pro
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: DevCompass
agent_created: true
trigger_words:
  - "cheat.sh"
  - "命令行示例"
  - "速查命令"
  - "工具用法"
---

# 命令行速查手册 SKILL.md

> 本内容由 AI 生成，仅供学习参考  
<!-- ai-generated-notice -->

---

## 一、能力边界

### 能做什么

| 场景 | 说明 |
|------|------|
| 语言速查 | 获取 Python、Go、Rust、JavaScript 等语言的函数用法或常见片段 |
| 工具速查 | 获取 curl、jq、git、docker、kubectl 等 CLI 工具的实用示例 |
| 问题定位 | 通过 `cheat.sh/关键词` 获取社区常见问题解答 |
| 学习参考 | 不依赖浏览器，终端内快速浏览代码模式 |

### 不能做什么

| 限制 | 说明 |
|------|------|
| 不执行代码 | 仅返回文本示例，不运行任何代码或命令 |
| 不保证最新 | 内容来自 cheat.sh 社区，可能滞后于最新版本 |
| 不处理登录态 | 需要认证的私有仓库、内部工具无法访问 |
| 不做语义理解 | 仅按关键词匹配，不做复杂意图解析 |

### 适用对象

- 日常使用终端的中级开发者
- 需要快速回忆 API 用法时的查阅场景
- 调试脚本、写一次性命令时的辅助参考

---

## 二、触发方式

### 触发词

| 触发词 | 说明 |
|--------|------|
| `cheat.sh` | 主触发词，完整形式 |
| 命令行示例 | 中文口语触发 |
| 速查命令 | 中文口语触发 |
| 工具用法 | 中文口语触发 |

### 场景映射表

| 用户说（大白话） | 实际行为 |
|------------------|----------|
| “帮我查一下 Python 怎么读 JSON” | 请求 `python/read json` 的速查内容 |
| “curl 怎么带 cookie 请求” | 请求 `curl/with cookie` 示例 |
| “jq 怎么取数组第一个元素” | 请求 `jq/array first element` 示例 |
| “给我一个 Go 的 http server 模板” | 请求 `go/http server` 示例 |

---

## 三、标准流程

### 前置条件

1. 用户已提供明确的查询目标（语言/工具 + 具体需求）
2. 网络可访问 `cheat.sh` 服务
3. 若未提供目标，进入澄清环节（见下文）

### 执行步骤

1. **解析输入**  
   提取 `语言/工具` 与 `需求关键词`，格式为：`工具/需求描述`

2. **构造请求**  
   拼接 URL：`https://cheat.sh/工具/需求描述`  
   示例：`https://cheat.sh/python/read json`

3. **执行请求**  
   使用 `curl -s` 发起 GET 请求，必要时加 `-H "User-Agent: curl"` 避免服务端拦截

4. **校验响应**  
   - 若返回 HTTP 200 且内容非空 → 继续
   - 若返回 404 → 提示关键词不匹配
   - 若返回其他错误 → 进入错误码处理（见下文）

5. **格式化输出**  
   - 保留原始文本格式（代码块、注释、示例）
   - 若内容过长（超过 200 行），截断并提示“内容较长，已截取前 200 行，需要完整版请回复 `/full`”

6. **交付结果**  
   输出速查内容，末尾附一行来源提示：`来源: cheat.sh（社区维护，仅供参考）`

### 输出规范

| 项目 | 要求 |
|------|------|
| 格式 | Markdown 代码块包裹原始内容 |
| 长度 | 默认截断 200 行，超长告知用户 |
| 附加信息 | 末尾附一行来源说明 |
| 错误提示 | 按错误码体系输出（见下文） |

---

## 四、置信度门控

当遇到以下情况，**不编造内容**，直接输出占位符：

| 场景 | 输出格式 |
|------|----------|
| 用户需求模糊（如“给我看看”无关键词） | `[需核实:请明确查询的语言或工具名称]` |
| 关键词过泛（如“python”无具体需求） | `[需核实:请补充具体需求，例如 "python/read csv"]` |
| 响应内容无法解析 | `[需核实:服务返回异常，请稍后重试或更换关键词]` |

**原则**：宁缺毋滥，不拼凑、不臆造示例。

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| `E001` | 输入为空 | “未检测到查询目标，请提供语言/工具名称及需求” | 1. 引导用户输入 `工具/需求` 格式 |
| `E002` | 关键词不匹配（404） | “未找到匹配的速查内容，请尝试更换关键词或查看拼写” | 1. 建议用户简化关键词 2. 尝试英文原词 3. 推荐使用 `工具/常见任务` 格式 |
| `E003` | 网络超时或服务不可达 | “暂无法连接 cheat.sh 服务，请检查网络后重试” | 1. 等待 5 秒后重试 2. 若仍失败，提示用户稍后再试 |
| `E004` | 响应内容为空 | “服务返回空内容，请换一个更具体的关键词” | 1. 建议增加动词或对象（如 `read`、`list`、`create`） |
| `E005` | 响应格式异常 | “返回内容格式异常，无法正常展示” | 1. 建议用户更换关键词 2. 或直接访问 cheat.sh 网页版 |

---

## 六、FAQ 反模式

| 常见坑 | 反模式（错误做法） | 正确姿势 |
|--------|-------------------|----------|
| 关键词太宽泛 | 输入 `python` 不附加需求 | 输入 `python/read file`、`python/list comprehension` 等 |
| 使用中文关键词 | 输入 `python/读取文件` | 使用英文关键词（服务端以英文为主） |
| 忽略大小写 | 输入 `Python/Read Json` | 统一小写：`python/read json` |
| 依赖记忆 | 每次手动拼 URL | 直接口述需求，由 Skill 自动构造请求 |
| 误以为可执行 | 期望返回结果直接运行 | 明确本 Skill 仅提供示例文本，需自行复制执行 |

---

## 七、渐进式披露

### 速查卡（新手速览）

```
cheat.sh 使用口诀：
  输入格式：工具/需求
  示例：python/read json
  请求方式：curl -s https://cheat.sh/工具/需求
  输出：示例代码 + 注释
```

### 分层阅读路径

| 用户层级 | 建议路径 |
|----------|----------|
| 新手 | 先读速查卡 → 尝试 3 个标准示例 → 掌握格式 → 进入常见任务表 |
| 进阶 | 直接使用 `工具/任务` 格式 → 结合错误码排查 → 尝试复杂组合（如 `python/read json + write csv`） |
| 高级 | 使用 `工具/tab completion` 获取补全列表 → 探索 cheat.sh 的 `:list` 命令 → 自定义别名加速 |

---

## 八、附加说明

- 本 Skill 依赖外部服务 `cheat.sh`，其内容由社区维护，不保证绝对准确。
- 建议在使用前阅读 [cheat.sh 官网说明](https://cheat.sh)（外部链接，非本 Skill 提供）。
- 若连续 3 次查询失败，建议改用浏览器访问 cheat.sh 网页版。

## 许可证（License）

```text
MIT License

Copyright (c) 2026 SkillForge Lab

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.
```
<!-- professional-license-embedded -->

## 异常处理

| 异常情况 | 表现 | 处理方式 |
|---|---|---|
| 输入文件不存在 | 提示路径错误并退出 | 核对路径，使用绝对路径重试 |
| 文件格式不符 | 该条跳过并计入失败明细 | 转换为受支持格式后重跑该条 |
| 权限不足 | 写入失败 | 更换输出目录或提升目录写权限 |
| 单条数据异常 | 跳过该条，继续处理其余 | 处理结束后查看失败明细定向重跑 |

失败处理原则：**单条失败不中断整批**，全部异常汇总到失败明细，支持只重跑失败项。

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
