---
slug: cli
name: HTTP命令行测试工具
displayName: 接口调试 命令行 请求构造
description: 命令行HTTP调试工具，支持REST API测试、请求构造、响应格式化与批量执行。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: LingTool
agent_created: true
trigger_words: ["cli", "http", "rest", "api测试", "接口调试", "curl替代", "请求发送", "接口验证"]
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# HTTP命令行测试工具（cli）

## 一、能力边界（一页纸速查卡）

### 1.1 能做什么

| 能力项 | 说明 | 示例 |
|--------|------|------|
| 版本确认 | 输出工具版本号 | `cli --version` → `cli version 1.0.0` |
| 安装自检 | 检查依赖是否完整 | `cli --selftest` → `OK` |
| 单请求发送 | 构造并发送HTTP请求 | `cli http POST /users -d '{"name":"张三"}'` |
| 批量执行 | 从JSON文件读取多条请求并依次执行 | `cli --batch test.json` |
| 响应格式化 | 以JSON/YAML/纯文本格式输出响应 | `cli --format json` |
| 环境变量控制 | 通过环境变量调整超时、重试等参数 | `CLI_TIMEOUT=30 cli http GET /ping` |
| 退出码反馈 | 通过退出码判断执行结果 | `echo $?` → `0` 成功 / `非0` 失败 |

### 1.2 不能做什么（明确边界）

- 不支持交互式会话（如 `curl` 的 `-i` 持续连接模式）
- 不支持文件上传（multipart/form-data）的流式处理
- 不内置OAuth2授权流程，需自行获取token后通过Header传入
- 不提供GUI界面，所有操作均通过命令行完成
- 不负责请求内容的业务正确性校验，仅保证HTTP层面的收发

### 1.3 适用对象

- 后端开发人员：快速验证接口逻辑
- 测试工程师：批量回归测试、断言响应字段
- DevOps工程师：在CI流水线中集成接口健康检查
- 技术文档撰写者：验证API文档中的示例请求

---

## 二、触发方式与场景映射

### 2.1 触发词

当对话中出现以下关键词时，本Skill将被激活：

- `cli`、`http`、`rest`、`api测试`、`接口调试`
- 补充触发词：`curl替代`、`请求发送`、`接口验证`

### 2.2 场景映射表

| 用户说（大白话） | 实际需求 | 推荐命令 |
|------------------|----------|----------|
| "帮我测一下这个接口通不通" | 发送GET请求检查连通性 | `cli http GET https://api.example.com/ping` |
| "这个POST请求怎么发？" | 构造带JSON体的POST请求 | `cli http POST /users -d '{"name":"test"}'` |
| "我要跑一堆接口测试" | 批量执行多条请求 | `cli --batch test.json` |
| "看下返回的JSON结构" | 格式化输出响应体 | `cli http GET /users/1 --format json` |
| "接口超时了怎么办" | 调整超时时间 | `CLI_TIMEOUT=60 cli http GET /slow-api` |

---

## 三、标准流程

### 3.1 前置条件

| 条件 | 检查方法 | 失败处理 |
|------|----------|----------|
| 工具已安装 | `cli --version` | 重新安装或检查PATH |
| 依赖完整 | `cli --selftest` | 按错误码表（第六节）排查 |
| 目标服务可达 | `ping <host>` 或 `curl -I <url>` | 检查网络/防火墙 |
| 认证信息就绪 | 确认token/API Key已获取 | 通过 `-H "Authorization: Bearer <token>"` 传入 |

### 3.2 执行步骤（分步编号）

**单请求发送流程：**

1. **确认工具状态**：执行 `cli --selftest`，输出 `OK` 则继续，否则跳至第六节排查。
2. **构造请求**：按以下参数表组装命令：

   | 参数 | 必填 | 说明 | 示例 |
   |------|------|------|------|
   | `http` | 是 | 子命令，表示HTTP操作 | `cli http` |
   | `METHOD` | 是 | 请求方法（GET/POST/PUT/DELETE等） | `POST` |
   | `URL` | 是 | 完整URL或路径（配合base-url） | `https://api.example.com/users` |
   | `-d, --data` | 否 | 请求体（JSON字符串） | `-d '{"name":"张三"}'` |
   | `-H, --header` | 否 | 自定义Header，可多次使用 | `-H "Content-Type: application/json"` |
   | `--format` | 否 | 输出格式：`json`/`yaml`/`text` | `--format json` |
   | `-o, --output` | 否 | 将响应保存到文件 | `-o response.json` |

3. **发送请求**：执行命令，观察输出。
4. **检查结果**：
   - 退出码 `0`：请求成功（HTTP 2xx/3xx）
   - 退出码 `1`：请求失败（网络错误、超时等）
   - 退出码 `2`：参数错误（命令构造有误）
5. **处理响应**：根据 `--format` 指定的格式解析输出，或使用 `jq` 提取字段。

**批量执行流程：**

1. **准备测试文件**：按4.3节格式编写JSON文件。
2. **执行批量命令**：`cli --batch test.json`
3. **查看汇总报告**：批量执行后输出每条请求的状态码、耗时、结果摘要。
4. **定位失败项**：根据输出中的错误信息定位具体请求，单独调试。

### 3.3 输出规范

- **成功输出**：响应体按指定格式输出，状态码显示在首行（如 `200 OK`）。
- **失败输出**：错误信息以 `[ERROR]` 前缀标识，附带错误码和排查建议。
- **批量输出**：每条请求一行摘要，格式为 `[序号] 方法 URL → 状态码 耗时`。

---

## 四、置信度门控

### 4.1 信息不足时的处理

当遇到以下情况时，使用 `[需核实:字段]` 占位，不编造数据：

| 场景 | 占位示例 |
|------|----------|
| 用户未提供完整URL | `[需核实:完整URL]` |
| 请求体字段不确定 | `[需核实:请求体JSON结构]` |
| 认证方式不明确 | `[需核实:认证方式(Bearer/Basic/API Key)]` |
| 响应字段含义不明 | `[需核实:响应字段说明]` |

### 4.2 使用原则

- 不猜测用户未提供的参数值
- 不假设接口的鉴权方式
- 不推断响应中未明确说明的字段含义
- 对不确定的信息明确标注，引导用户补充

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| `E001` | 依赖缺失 | `[ERROR] E001: 依赖库未安装` | 运行 `pip install -r requirements.txt` 或重新安装工具 |
| `E002` | 网络不可达 | `[ERROR] E002: 目标主机不可达` | 检查网络连接、DNS解析、防火墙规则 |
| `E003` | 超时 | `[ERROR] E003: 请求超时（默认30s）` | 设置 `CLI_TIMEOUT` 环境变量增加超时时间 |
| `E004` | 参数错误 | `[ERROR] E004: 缺少必要参数` | 检查命令语法，参考 `cli http --help` |
| `E005` | 批量文件格式错误 | `[ERROR] E005: 批量文件JSON解析失败` | 校验JSON格式，参考4.3节模板 |
| `E006` | 认证失败 | `[ERROR] E006: HTTP 401/403` | 检查token有效性，确认Header传递正确 |
| `E007` | 响应解析失败 | `[ERROR] E007: 响应体非合法JSON` | 使用 `--format text` 查看原始响应 |

---

## 六、FAQ 反模式对照

### 6.1 常见坑与正确做法

| 反模式（错误做法） | 问题 | 正确做法 |
|---------------------|------|----------|
| 直接复制浏览器中的请求头 | 包含 `Accept-Encoding: gzip` 等压缩头，导致响应乱码 | 仅保留必要Header（Content-Type、Authorization等） |
| 批量文件中所有请求共用一个超时时间 | 慢接口容易超时失败 | 在批量文件中为每个请求单独设置 `timeout` 字段 |
| 忽略退出码，仅看输出文本 | 输出可能被截断或格式化，误判结果 | 始终检查退出码，结合 `jq` 做断言 |
| 在脚本中硬编码token | token过期后脚本失效 | 通过环境变量或配置文件动态注入token |
| 使用 `--format json` 但响应体不是JSON | 解析报错 | 先用 `--format text` 查看原始响应，确认格式 |

### 6.2 反模式示例

```bash
# 反模式：忽略退出码
cli http GET https://api.example.com/users
echo "请求完成"  # 无论成功失败都输出

# 正确做法
cli http GET https://api.example.com/users
if [ $? -eq 0 ]; then
  echo "请求成功"
else
  echo "请求失败，退出码: $?"
fi
```

---

## 七、渐进式披露

### 7.1 速查卡（30秒上手）

```bash
# 1. 检查工具
cli --selftest

# 2. 发送GET请求
cli http GET https://api.example.com/ping

# 3. 发送POST请求（带JSON体）
cli http POST https://api.example.com/users -d '{"name":"张三"}' -H "Content-Type: application/json"

# 4. 格式化输出
cli http GET https://api.example.com/users/1 --format json

# 5. 批量执行
cli --batch test.json
```

### 7.2 分层次阅读路径

**新手路径（5分钟上手）：**
1. 阅读第一节「能力边界」了解工具能做什么
2. 执行 `cli --selftest` 确认环境
3. 按速查卡发送第一个请求
4. 遇到问题查阅第五节「错误码体系」

**进阶路径（深入使用）：**
1. 学习4.3节批量文件格式，编写自动化测试
2. 掌握环境变量配置（`CLI_TIMEOUT`、`CLI_RETRY`）
3. 集成CI流水线，结合 `jq` 做响应断言
4. 自定义输出解析，将结果管道给其他工具

---

## 八、批量执行文件格式（4.3节参考）

```json
{
  "requests": [
    {
      "name": "创建用户",
      "method": "POST",
      "url": "https://api.example.com/users",
      "headers": {
        "Content-Type": "application/json",
        "Authorization": "Bearer ${TOKEN}"
      },
      "body": {
        "name": "张三",
        "email": "zhangsan@example.com"
      },
      "timeout": 30,
      "retry": 2
    },
    {
      "name": "查询用户",
      "method": "GET",
      "url": "https://api.example.com/users/1",
      "timeout": 10
    }
  ]
}
```

**字段说明：**

| 字段 | 必填 | 说明 |
|------|------|------|
| `name` | 否 | 请求名称，用于输出标识 |
| `method` | 是 | HTTP方法 |
| `url` | 是 | 完整请求URL |
| `headers` | 否 | 请求头对象 |
| `body` | 否 | 请求体（对象或字符串） |
| `timeout` | 否 | 单请求超时时间（秒），默认30 |
| `retry` | 否 | 失败重试次数，默认0 |

---

## 九、环境变量参考

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `CLI_TIMEOUT` | `30` | 全局默认超时时间（秒） |
| `CLI_RETRY` | `0` | 全局默认重试次数 |
| `CLI_BASE_URL` | 空 | 基础URL，请求中可使用相对路径 |
| `CLI_TOKEN` | 空 | 默认认证token，自动附加到Authorization头 |

---

## 十、用户协议

<!-- user-agreement-injected -->

**使用本Skill即表示您同意以下条款：**

1. **责任承担**：使用者自行承担因使用本Skill进行接口测试、调试或任何其他操作所产生的全部责任。本Skill提供的是工具使用指导，不构成对任何操作结果的保证。
2. **禁止反向工程**：严禁对本Skill文档内容进行反向工程、反编译、破解或试图提取底层逻辑用于商业用途。
3. **合规使用**：使用者应确保所有测试行为符合当地法律法规及目标服务的服务条款，不得用于未经授权的系统访问或攻击行为。
4. **无担保声明**：本Skill按"现状"提供，不附带任何明示或暗示的担保，包括但不限于适销性、特定用途适用性和非侵权性。

---

## 十一、许可证（License）

<!-- professional-license-embedded -->

**MIT License**

版权所有 (c) 2024 LingTool

特此免费授予任何获得本软件及相关文档文件（"软件"）副本的人士以下权限：不受限制地处理本软件，包括但不限于使用、复制、修改、合并、发布、分发、再许可和/或销售软件副本的权利，并允许向本软件提供对象的人士这样做，但须满足以下条件：

上述版权声明和本许可声明应包含在本软件的所有副本或重要部分中。

本软件按"现状"提供，不附带任何明示或暗示的担保，包括但不限于适销性、特定用途适用性和非侵权性保证。在任何情况下，作者或版权持有人均不对因使用本软件而产生的任何索赔、损害或其他责任负责，无论是在合同诉讼、侵权或其他诉讼中。

---

*本Skill文档由AI辅助生成，仅供学习参考。使用前请阅读相关文档，确保理解工具行为。*
