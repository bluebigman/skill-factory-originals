---
slug: cli-command-tester
name: HTTP命令行测试工具
displayName: 接口调试 命令行速测
description: 用命令行快速构造HTTP请求、调试REST API并格式化输出响应结果。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 命令行工坊
agent_created: true
trigger_words: ["cli", "curl", "http测试", "接口调试", "rest api", "接口请求", "api调试"]
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# HTTP命令行测试工具 Skill 文档

## 一、能力边界：一页纸速查卡

### 1.1 能做什么

| 能力项 | 说明 | 示例 |
|--------|------|------|
| 构造HTTP请求 | 支持GET/POST/PUT/DELETE/PATCH/HEAD/OPTIONS | `cli POST https://api.example.com/users` |
| 自定义请求头 | 添加认证、内容类型等头部 | `cli GET https://api.example.com -H "Authorization: Bearer token"` |
| 请求体构造 | JSON、表单、原始文本 | `cli POST https://api.example.com -d '{"name":"test"}'` |
| 参数拼接 | 查询字符串自动编码 | `cli GET https://api.example.com -p "page=1&size=20"` |
| 响应格式化 | JSON高亮、缩进、截断 | 自动格式化JSON响应 |
| 超时控制 | 设置请求超时时间 | `cli GET https://api.example.com -t 10` |
| 跟随重定向 | 自动或手动控制 | `cli GET https://api.example.com -L` |
| 输出保存 | 响应体写入文件 | `cli GET https://api.example.com -o response.json` |

### 1.2 不能做什么

| 限制项 | 说明 |
|--------|------|
| 不支持WebSocket | 仅限HTTP/HTTPS协议 |
| 不支持文件上传 | 仅支持文本请求体 |
| 不支持Cookie持久化 | 每次调用独立会话 |
| 不支持代理配置 | 需在系统层面配置 |
| 不支持双向TLS | 仅支持常规HTTPS证书验证 |

### 1.3 适用对象

- 后端开发人员：快速验证接口逻辑
- 前端开发人员：联调时检查接口返回
- 测试工程师：构造边界条件请求
- DevOps人员：健康检查、接口监控

---

## 二、触发方式

### 2.1 触发词

直接使用 `cli` 或 `curl` 作为命令前缀，后跟HTTP方法和URL。

### 2.2 场景映射表

| 用户说（大白话） | 实际执行命令 |
|-----------------|-------------|
| "帮我测一下这个接口通不通" | `cli GET https://api.example.com/health` |
| "用POST提交一段JSON数据" | `cli POST https://api.example.com/users -d '{"name":"张三"}'` |
| "带token请求一下用户信息" | `cli GET https://api.example.com/me -H "Authorization: Bearer eyJhbGci..."` |
| "看看这个接口返回的响应头" | `cli GET https://api.example.com -i` |
| "设置5秒超时测一下" | `cli GET https://api.example.com -t 5` |

---

## 三、标准流程

### 3.1 前置条件

| 条件 | 要求 | 检查方式 |
|------|------|----------|
| 网络连通 | 目标服务器可达 | `ping 目标域名` 或 `curl -I 目标URL` |
| URL格式 | 合法HTTP/HTTPS地址 | 必须以 `http://` 或 `https://` 开头 |
| 参数格式 | JSON或键值对 | JSON需双引号包裹键名 |
| 权限 | 目标接口允许访问 | 确认认证信息已准备 |

### 3.2 执行步骤

1. **解析命令**：识别HTTP方法、URL、参数
2. **校验参数**：检查URL合法性、参数格式
3. **构造请求**：组装请求头、请求体
4. **发送请求**：执行HTTP请求，记录耗时
5. **处理响应**：格式化输出状态码、响应头、响应体
6. **展示结果**：按优先级展示关键信息

### 3.3 输出规范

```
状态码: 200 OK
耗时: 235ms
响应头:
  content-type: application/json
  server: nginx/1.24.0
响应体:
{
  "code": 0,
  "message": "success",
  "data": {
    "id": 123,
    "name": "张三"
  }
}
```

---

## 四、置信度门控

当遇到以下情况时，输出 `[需核实:字段]` 占位符，不进行编造：

| 场景 | 处理方式 |
|------|----------|
| 响应体解析失败 | 输出原始内容，标注 `[需核实:响应格式]` |
| 状态码非2xx | 标注 `[需核实:错误原因]`，展示响应体 |
| 超时无响应 | 标注 `[需核实:服务器状态]` |
| 参数含义不明 | 标注 `[需核实:参数定义]`，不猜测 |

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| E001 | URL格式错误 | "URL必须以http://或https://开头" | 检查URL拼写，补全协议头 |
| E002 | 参数格式错误 | "JSON参数格式不正确，请检查引号" | 使用JSON验证工具检查格式 |
| E003 | 连接超时 | "请求超时，请检查网络或增大超时时间" | 使用 `-t` 参数增大超时 |
| E004 | DNS解析失败 | "域名无法解析，请检查域名拼写" | 使用 `nslookup` 检查DNS |
| E005 | 连接被拒绝 | "目标端口未开放或服务未启动" | 检查服务状态和防火墙 |
| E006 | SSL证书错误 | "证书验证失败，请检查证书" | 确认证书有效性或使用 `-k` 跳过验证 |
| E007 | 响应解析失败 | "响应内容无法解析为JSON" | 使用 `-r` 参数查看原始响应 |

---

## 六、FAQ 反模式

### 6.1 常见坑

| 坑 | 反模式示例 | 正确做法 |
|----|-----------|----------|
| 忽略状态码 | 只看响应体，不看状态码 | 先检查状态码，再解析响应体 |
| 参数未编码 | URL中直接拼中文 | 使用 `-p` 参数自动编码 |
| 请求头遗漏 | 忘记添加Content-Type | 明确指定 `-H "Content-Type: application/json"` |
| 超时设置过长 | 默认超时导致长时间等待 | 根据场景设置合理超时（3-10秒） |
| 忽略响应头 | 只看响应体 | 使用 `-i` 查看完整响应头 |

### 6.2 反模式对照表

| 反模式 | 问题 | 替代方案 |
|--------|------|----------|
| 在脚本中硬编码token | 安全隐患 | 使用环境变量注入 |
| 循环请求不做间隔 | 可能触发限流 | 添加随机延迟 |
| 忽略错误处理 | 脚本中断 | 检查退出码并处理 |
| 不记录请求日志 | 难以排查 | 使用 `-v` 输出详细日志 |

---

## 七、渐进式披露

### 7.1 速查卡（新手必读）

```bash
# 基础GET请求
cli GET https://api.example.com

# POST提交JSON
cli POST https://api.example.com/users -d '{"name":"test"}'

# 带认证请求
cli GET https://api.example.com/me -H "Authorization: Bearer TOKEN"

# 查看响应头
cli GET https://api.example.com -i

# 设置超时
cli GET https://api.example.com -t 10
```

### 7.2 进阶路径

**新手路径**（第1-2天）：
1. 掌握基础GET/POST请求
2. 学会查看状态码和响应体
3. 理解请求头的作用

**进阶路径**（第3-7天）：
1. 掌握参数编码和复杂JSON构造
2. 学会调试认证流程
3. 理解重定向和缓存机制

**专家路径**（第2周+）：
1. 编写自动化测试脚本
2. 集成CI/CD流程
3. 性能测试和压力测试

---

## 八、参数详解

| 参数 | 全称 | 说明 | 默认值 | 示例 |
|------|------|------|--------|------|
| `-H` | header | 添加请求头 | 无 | `-H "Content-Type: application/json"` |
| `-d` | data | 请求体数据 | 无 | `-d '{"key":"value"}'` |
| `-p` | params | 查询参数 | 无 | `-p "page=1&size=20"` |
| `-t` | timeout | 超时时间(秒) | 30 | `-t 5` |
| `-i` | include | 包含响应头 | false | `-i` |
| `-L` | location | 跟随重定向 | false | `-L` |
| `-o` | output | 输出到文件 | 无 | `-o response.json` |
| `-k` | insecure | 跳过SSL验证 | false | `-k` |
| `-v` | verbose | 详细日志 | false | `-v` |
| `-r` | raw | 原始输出 | false | `-r` |

---

## 九、用户协议

<!-- user-agreement-injected -->

**使用本 Skill 即表示您同意以下条款：**

1. **责任承担**：使用者自行承担因使用本 Skill 产生的全部责任。包括但不限于因请求错误、数据泄露、接口滥用等造成的任何直接或间接损失。

2. **禁止反向工程**：不得对本 Skill 进行反向工程、反编译、破解或试图提取源代码。

3. **合法使用**：使用者承诺仅将本 Skill 用于合法目的，不得用于攻击、入侵、非法抓取数据等违法行为。

4. **无担保声明**：本 Skill 按"现状"提供，不附带任何明示或暗示的担保。

5. **变更权利**：作者保留随时修改、更新或终止本 Skill 的权利，恕不另行通知。

---

## 十、许可证（License）

<!-- professional-license-embedded -->

**MIT License**

版权所有 (c) 2024 命令行工坊

特此免费授予任何获得本软件及相关文档文件（以下简称"软件"）副本的人，不受限制地处理本软件，包括但不限于使用、复制、修改、合并、发布、分发、再许可和/或出售软件副本的权利，并允许向其提供本软件的人这样做，但须满足以下条件：

上述版权声明和本许可声明应包含在本软件的所有副本或主要部分中。

本软件按"现状"提供，不附带任何明示或暗示的担保，包括但不限于适销性、特定用途适用性和非侵权性的担保。在任何情况下，作者或版权持有人均不对因本软件或使用本软件或其他交易而产生、与之相关或与之相关的任何索赔、损害或其他责任承担责任，无论是在合同诉讼、侵权诉讼或其他诉讼中。

---

*本 Skill 文档由 AI 辅助生成，仅供参考。使用前请阅读相关文档并自行验证命令的正确性。*
