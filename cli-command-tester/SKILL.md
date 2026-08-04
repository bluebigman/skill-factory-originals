---
> 本内容由 AI 生成，仅供学习参考（《人工智能生成合成内容标识办法》显式标识）。
<!-- ai-generated-notice -->
slug: cli-command-tester
name: HTTP命令行测试工具
displayName: 接口调试 请求构造 响应校验
description: 用命令行快速构造HTTP请求、调试REST API并格式化输出响应结果。
version: 1.0.16
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/cli-command-tester
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 边缘工坊
agent_created: true
trigger_words: ["cli", "curl", "http测试", "接口调试", "rest api"]
---

> 本内容由 AI 生成，仅供学习参考 <!-- ai-generated-notice -->

---

# HTTP命令行测试工具 · 使用指南

## 1. 能力边界（一页纸速查卡）

### 能做什么

| 场景 | 说明 |
|------|------|
| 构造请求 | 支持 GET/POST/PUT/DELETE/PATCH/HEAD/OPTIONS 七种方法 |
| 参数注入 | URL 路径参数、查询字符串、请求头、JSON/表单请求体 |
| 响应分析 | 状态码、响应头、响应体（自动识别 JSON/XML/纯文本） |
| 批量执行 | 一次性提交多个请求，汇总对比输出 |
| 结果导出 | 输出为表格、JSON 文件或纯文本日志 |

### 不能做什么

| 限制项 | 说明 |
|--------|------|
| 不支持 WebSocket 长连接测试 | 仅限 HTTP/HTTPS 短连接 |
| 不支持文件上传（multipart 大文件） | 超过 10MB 的二进制负载请使用专业工具 |
| 不模拟浏览器行为 | 不执行 JavaScript、不渲染页面 |
| 不做性能压测 | 并发压测请使用专用压测工具 |
| 不存储敏感凭证 | 请求头中的 Authorization 信息仅在当前会话有效 |

### 适用对象

- 后端开发人员：快速验证接口逻辑
- 前端开发人员：确认接口字段与格式
- 测试工程师：做冒烟测试和回归验证
- 运维人员：检查服务健康状态

---

## 2. 触发方式

### 触发词启用

| 触发词 | 使用场景示例 |
|--------|-------------|
| `cli` | “用 cli 测试一下这个接口” |
| `curl` | “帮我写个 curl 命令” |
| `http测试` | “对 https://api.example.com/users 做 http测试” |
| `接口调试` | “接口调试一下登录接口” |
| `rest api` | “用 rest api 方式验证这个端点” |

### 大白话场景映射

| 你说的话 | 工具理解 | 执行动作 |
|----------|----------|----------|
| “试试这个地址通不通” | 发 GET 请求，检查连通性 | 执行 `GET /` 返回状态码 |
| “帮我发个 POST 带 JSON” | 构造 POST + JSON body | 自动设置 `Content-Type: application/json` |
| “我看下返回的格式” | 格式化响应体 | JSON 自动缩进，XML 自动美化 |
| “跑一遍这几个接口” | 批量执行 | 顺序发送所有请求，汇总输出 |
| “带个 token 试” | 附加认证头 | 提示输入 token 值，注入 `Authorization` |

---

## 3. 标准流程

### 前置条件

| 条件 | 要求 | 缺失时表现 |
|------|------|-----------|
| 目标 URL | 必须以 `http://` 或 `https://` 开头 | 报错 `E1001` |
| 网络可达 | 目标主机可解析且可连接 | 报错 `E2002` |
| 请求体格式 | 若声明 JSON，则必须是合法 JSON 字符串 | 报错 `E1003` |
| 认证信息 | 若接口需要认证，需显式提供 | 返回 401/403 时提示 |

### 执行步骤

1. **确认请求目标**  
   接收用户提供的 URL 或从上下文提取接口地址。  
   若 URL 缺失 → 输出 `[需核实:url]` 并停止。

2. **解析请求参数**  
   从输入中提取：
   - 方法（默认 GET）
   - 路径参数（如 `/users/{id}` 中的 `id`）
   - 查询参数（`?key=value`）
   - 请求头（`-H "Name: value"` 格式）
   - 请求体（`-d '{"key":"value"}'` 格式）

3. **校验参数合法性**  
   - URL 格式正则校验：`^https?://`
   - JSON body 使用解析器验证（若声明为 JSON）
   - 方法名必须属于允许集合

4. **执行请求**  
   使用底层 HTTP 客户端发送请求，设置合理超时（默认 10 秒，可配置）。

5. **处理响应**  
   - 提取状态码、响应头、响应体
   - 根据 `Content-Type` 自动格式化：
     - `application/json` → 缩进 2 空格
     - `application/xml` → 缩进 2 空格
     - 其他 → 原样输出（限前 5000 字符）

6. **返回结果**  
   输出格式：

   ```
   状态码: 200 OK
   耗时: 123ms
   响应头:
     content-type: application/json
     server: nginx
   响应体:
   {
     "id": 1,
     "name": "示例"
   }
   ```

### 输出规范

| 输出类型 | 格式要求 |
|----------|----------|
| 成功（2xx） | 绿色标记 `✔` + 状态码 + 格式化响应体 |
| 重定向（3xx） | 黄色标记 `↪` + 状态码 + 跳转地址 |
| 客户端错误（4xx） | 红色标记 `✘` + 状态码 + 错误响应体 |
| 服务端错误（5xx） | 红色标记 `✘` + 状态码 + 建议重试提示 |

---

## 4. 置信度门控

### 信息不足时使用占位符

以下情况禁止编造数据，必须输出 `[需核实:字段名]`：

| 场景 | 占位符示例 |
|------|-----------|
| 用户未提供 URL | `[需核实:url]` |
| 请求头缺少必要字段 | `[需核实:header Authorization]` |
| 请求体内容不完整 | `[需核实:body 字段]` |
| 响应解析失败，原因未知 | `[需核实:响应格式]` |

### 门控规则

- 当输入信息不足以构造一个完整的 HTTP 请求时，**立即停止**，不猜测、不补全。
- 当响应体无法按声明格式解析时，输出原始内容并标注 `[需核实:格式声明与实际不符]`。

---

## 5. 错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| `E1001` | URL 格式错误 | “URL 必须以 http:// 或 https:// 开头” | 检查 URL 前缀，补全协议头 |
| `E1002` | 方法不支持 | “方法 X 不在支持列表中” | 用 `GET/POST/PUT/DELETE/PATCH/HEAD/OPTIONS` 重试 |
| `E1003` | JSON 解析失败 | “请求体不是合法 JSON，请检查引号和逗号” | 用 JSON 校验器检查格式 |
| `E1004` | 请求头格式错误 | “请求头应为 '名称: 值' 格式” | 修正分隔符为冒号加空格 |
| `E2001` | DNS 解析失败 | “无法解析域名，请检查拼写” | 确认域名正确，尝试 ping |
| `E2002` | 连接超时 | “连接目标超时（10秒）”，请检查网络或延长超时 | 检查防火墙/代理设置 |
| `E2003` | SSL 证书错误 | “证书验证失败”，如确需跳过请声明 `-k` | 检查证书有效期 |
| `E3001` | 响应体过大 | “响应超过 5000 字符限制，已截断” | 使用输出重定向到文件 |

---

## 6. FAQ 反模式对照

| # | 常见坑 | 反模式（错误做法） | 正确做法 |
|---|--------|-------------------|----------|
| 1 | 忘记加 URL 协议头 | 直接写 `api.example.com/users` | 始终写 `https://api.example.com/users` |
| 2 | JSON 引号用错 | 用单引号包 JSON 且内部也用了单引号 | 外层用单引号，内部用双引号 |
| 3 | 忽略状态码含义 | 只看响应体，不看状态码 | 先看状态码，再读响应体内容 |
| 4 | 混淆查询参数与路径参数 | 把 `/users/{id}` 写成 `/users?id=1` | 路径参数用 `/users/1`，查询参数用 `?id=1` |
| 5 | 忽视响应头信息 | 只看响应体，忽略 `Set-Cookie`、`Rate-Limit` | 检查响应头中的关键字段 |

---

## 7. 渐进式披露

### 速查卡（30 秒上手）

```
用法: cli <method> <url> [选项]

选项:
  -d, --data <json>      请求体 (JSON 字符串)
  -H, --header <kv>      请求头 ("Name: value")
  -q, --query <kv>       查询参数 ("key=value")
  -t, --timeout <sec>    超时时间 (默认 10s)
  -k, --insecure         跳过 SSL 验证
  -o, --output <file>    输出到文件
  -b, --batch <file>     批量执行文件 (每行一个请求)

示例:
  cli GET https://api.example.com/users
  cli POST https://api.example.com/users -d '{"name":"张三"}' -H "Authorization: Bearer token123"
```

### 新手路径（首次使用）

1. 先跑一个最简单的 GET 请求确认连通性
2. 再尝试带查询参数的 GET
3. 然后尝试 POST + JSON body
4. 最后学习批量执行和文件输出

### 进阶路径（熟练用户）

1. 掌握响应头分析（缓存策略、限流信息）
2. 使用批量文件做接口回归测试
3. 结合 `-o` 输出到文件，配合 diff 工具做版本对比
4. 自定义超时和 SSL 行为处理复杂网络环境

---

## 附：批量测试文件格式

每行一个完整请求，`#` 开头为注释：

```
# 用户模块测试
GET https://api.example.com/users
POST https://api.example.com/users -d '{"name":"测试"}'
GET https://api.example.com/users/1
DELETE https://api.example.com/users/1
```

执行结果按顺序编号输出，最后汇总各请求状态码统计。

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
