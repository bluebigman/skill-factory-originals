---
slug: cli-command-tester
name: HTTP命令行测试工具
displayName: 接口调试 请求构造 响应解析
description: 命令行构造HTTP请求、调试REST API并格式化输出响应。
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
trigger_words: ["cli", "curl", "http测试", "接口调试", "rest api", "--selftest", "--version", "请求构造", "响应解析", "api调试"]

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

---

# HTTP命令行测试工具 Skill 文档

## 一、能力边界：一页纸速查卡

### 1.1 能做什么

| 编号 | 能力项 | 说明 |
|------|--------|------|
| C01 | 构造HTTP请求 | 支持GET/POST/PUT/DELETE/PATCH/HEAD/OPTIONS七种方法 |
| C02 | 自定义请求头 | 可添加任意Header键值对，支持重复键 |
| C03 | 请求体构造 | 支持JSON、表单（urlencoded）、纯文本三种格式 |
| C04 | 参数拼接 | 自动处理URL查询字符串的编码与拼接 |
| C05 | 响应格式化 | JSON自动缩进、响应头/体分离展示、状态码高亮 |
| C06 | 超时控制 | 默认10秒，可自定义1-120秒 |
| C07 | 重定向策略 | 默认跟随，可切换为禁止跟随 |
| C08 | 自检模式 | `--selftest` 验证工具链完整性 |
| C09 | 版本查询 | `--version` 输出当前版本号 |

### 1.2 不能做什么

| 编号 | 限制项 | 说明 |
|------|--------|------|
| X01 | 不支持WebSocket | 仅限HTTP/HTTPS协议 |
| X02 | 不支持文件上传 | 不处理multipart/form-data |
| X03 | 不支持Cookie持久化 | 每次调用为无状态请求 |
| X04 | 不支持代理配置 | 需在系统环境变量中预设 |
| X05 | 不支持双向TLS | 仅支持常规CA证书校验 |
| X06 | 不执行JavaScript | 不渲染页面，仅返回原始响应 |

### 1.3 适用对象

- **后端开发者**：快速验证接口逻辑
- **前端开发者**：联调时检查Mock数据
- **测试工程师**：构造边界条件请求
- **运维人员**：探测服务健康状态

---

## 二、触发方式：场景映射表

| 触发词 | 大白话场景 | 实际执行内容 |
|--------|-----------|-------------|
| `cli` | "用命令行测一下这个接口" | 进入命令行交互模式 |
| `curl` | "帮我发个curl请求" | 解析参数并构造请求 |
| `http测试` | "测测这个API通不通" | 发送请求并返回状态码 |
| `接口调试` | "这个接口返回不对，帮我看看" | 构造请求并格式化输出 |
| `rest api` | "验证REST风格接口" | 按REST语义发送请求 |
| `--selftest` | "检查工具是否正常" | 运行内置自检流程 |
| `--version` | "看下工具版本" | 输出版本号 |
| `请求构造` | "帮我拼一个POST请求" | 引导输入请求参数 |
| `响应解析` | "这个返回的JSON啥意思" | 格式化并解析响应体 |
| `api调试` | "调一下登录接口" | 构造带认证头的请求 |

---

## 三、标准流程

### 3.1 前置条件

| 条件项 | 要求 | 检查方式 |
|--------|------|----------|
| 网络连通 | 目标主机可达 | `ping <host>` 或 `curl -I` |
| URL合法性 | 符合RFC 3986 | 正则校验 `^https?://` |
| 端口开放 | 目标端口可访问 | `telnet <host> <port>` |
| 认证信息 | 如需鉴权则准备Token | 环境变量 `AUTH_TOKEN` |

### 3.2 执行步骤

**Step 1：参数解析**

```bash
# 命令行参数格式
cli-command-tester [method] [url] [options]

# 示例
cli-command-tester POST https://api.example.com/users \
  -H "Content-Type: application/json" \
  -d '{"name":"张三","age":30}' \
  -t 15
```

**Step 2：请求构造**

| 参数 | 缩写 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `--method` | `-X` | 否 | GET | HTTP方法 |
| `--header` | `-H` | 否 | 无 | 请求头，可重复 |
| `--data` | `-d` | 否 | 无 | 请求体 |
| `--format` | `-f` | 否 | json | 请求体格式：json/form/text |
| `--timeout` | `-t` | 否 | 10 | 超时秒数 |
| `--no-redirect` | `-n` | 否 | false | 禁止重定向 |
| `--verbose` | `-v` | 否 | false | 显示详细过程 |

**Step 3：发送请求**

```bash
# 内部执行逻辑
1. 校验URL格式
2. 合并默认请求头（User-Agent, Accept）
3. 按format序列化请求体
4. 建立TCP连接（超时控制）
5. 发送请求并等待响应
6. 读取响应头与响应体
```

**Step 4：输出格式化**

```bash
# 标准输出结构
========================================
状态码: 200 OK
耗时: 123ms
========================================
响应头:
  Content-Type: application/json
  Server: nginx/1.24.0
========================================
响应体:
{
  "code": 0,
  "message": "success",
  "data": {
    "id": 1001,
    "name": "张三"
  }
}
========================================
```

### 3.3 输出规范

| 输出项 | 格式要求 | 示例 |
|--------|----------|------|
| 状态码 | 数字+文本 | `200 OK` |
| 耗时 | 毫秒整数 | `123ms` |
| 响应头 | 键值对缩进 | `Content-Type: application/json` |
| 响应体 | JSON缩进2空格 | 见上例 |
| 错误信息 | `[错误]` 前缀 | `[错误] 连接超时` |

---

## 四、置信度门控

### 4.1 信息不足处理

当以下信息缺失时，输出 `[需核实:字段]` 占位符，不进行猜测：

| 缺失字段 | 占位符示例 | 后续处理 |
|----------|------------|----------|
| URL | `[需核实:目标URL]` | 提示用户补充 |
| 认证方式 | `[需核实:认证类型]` | 询问Bearer/Basic/无 |
| 请求体格式 | `[需核实:Content-Type]` | 根据数据推断 |
| 响应结构 | `[需核实:响应Schema]` | 不解析未知字段 |

### 4.2 禁止行为

- 不编造响应数据
- 不猜测接口语义
- 不假设默认端口（除非标准80/443）
- 不自动重试失败请求

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| E001 | URL格式错误 | `[错误] 无法解析URL，请检查协议头` | 1. 确认以http://或https://开头<br>2. 检查域名合法性<br>3. 确认端口号范围1-65535 |
| E002 | 连接超时 | `[错误] 连接目标超时（10s）` | 1. 检查网络连通性<br>2. 确认目标端口开放<br>3. 使用-t参数增加超时 |
| E003 | DNS解析失败 | `[错误] 域名无法解析` | 1. 检查域名拼写<br>2. 尝试IP直连<br>3. 检查DNS配置 |
| E004 | 请求体格式错误 | `[错误] JSON解析失败：位置12` | 1. 使用JSON校验工具<br>2. 检查引号与逗号<br>3. 确认编码为UTF-8 |
| E005 | 响应解析失败 | `[错误] 响应体不是合法JSON` | 1. 检查Content-Type<br>2. 查看原始响应（-v参数）<br>3. 确认服务端返回格式 |
| E006 | SSL证书错误 | `[错误] 证书验证失败` | 1. 确认证书有效期<br>2. 检查证书链完整性<br>3. 确认域名匹配 |
| E007 | 参数缺失 | `[错误] 缺少必要参数：--data` | 1. 查看帮助文档<br>2. 确认必填参数<br>3. 使用交互模式 |

---

## 六、FAQ 反模式

### 6.1 常见坑

| 坑编号 | 错误做法 | 正确姿势 |
|--------|----------|----------|
| F01 | 忽略状态码直接解析响应体 | 先检查状态码，2xx才解析body |
| F02 | 使用`-d`传JSON但忘记设置Content-Type | 必须同时设置`-H "Content-Type: application/json"` |
| F03 | 不处理重定向导致拿到302页面 | 默认跟随重定向，或使用`-n`禁止 |
| F04 | 超时设置过短导致误判 | 根据网络状况设置合理超时（建议≥5s） |
| F05 | 混淆表单与JSON格式 | 表单用`key=value&key2=value2`，JSON用`{"key":"value"}` |

### 6.2 反模式对照

| 反模式 | 问题描述 | 替代方案 |
|--------|----------|----------|
| 盲目复制curl命令 | 忽略环境差异导致失败 | 逐项检查URL、Header、Body |
| 依赖默认参数 | 某些服务需要特定Header | 显式声明所有必要Header |
| 忽略响应头 | 分页、限流信息在Header中 | 使用`-v`查看完整响应 |
| 不校验SSL | 生产环境存在中间人风险 | 保留证书校验，除非测试环境 |

---

## 七、渐进式披露

### 7.1 速查卡（30秒上手）

```bash
# 最常用三个命令
cli-command-tester GET https://api.example.com/health
cli-command-tester POST https://api.example.com/users -H "Content-Type: application/json" -d '{"name":"test"}'
cli-command-tester --selftest
```

### 7.2 新手路径（5分钟掌握）

1. 运行 `--selftest` 确认环境正常
2. 用GET请求测试一个公开API（如 `https://httpbin.org/get`）
3. 尝试添加自定义Header
4. 用POST发送JSON数据
5. 查看格式化输出，理解状态码含义

### 7.3 进阶路径（深入使用）

1. 掌握所有参数组合（参考3.2节参数表）
2. 理解重定向、超时、认证机制
3. 编写脚本批量测试接口
4. 结合CI/CD流水线自动化测试
5. 使用`-v`参数调试复杂请求

---

## 八、用户协议

<!-- user-agreement-injected -->

**使用本Skill即表示您同意以下条款：**

1. **责任承担**：使用者自行承担使用本工具产生的全部责任。包括但不限于因请求发送、数据处理、结果解读等行为引发的直接或间接损失。

2. **禁止反向工程**：不得对本Skill的底层实现进行逆向工程、反编译、反汇编或任何形式的代码还原。

3. **合规使用**：使用者需确保使用场景符合当地法律法规，不得用于非法接口探测、未授权访问等违规行为。

4. **免责声明**：本Skill按"现状"提供，不附带任何明示或暗示的保证。作者不对工具适用性、准确性或可靠性作出承诺。

---

## 九、许可证（License）

<!-- professional-license-embedded -->

**MIT License**

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

---

*文档版本：1.0.0 | 最后更新：2024年*
