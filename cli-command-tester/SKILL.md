---
slug: cli-command-tester
name: HTTP命令行测试工具
displayName: 接口调试 命令行速测
description: 用命令行快速构造HTTP请求、调试REST API并格式化输出响应结果。
version: 2.0.0
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

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->

> 📜 **用户协议（User Agreement）**
> 1. 本 Skill 仅供学习与参考用途。使用本 Skill 产生的任何结果，由使用者自行承担全部责任；本 Skill 不提供任何明示或暗示的保证。
> 2. 涉及法律、财务、税务、投资、医疗等专业决策时，请务必咨询持证专业人士。
> 3. 本代码受版权法保护，未经授权复制、反向工程或商业利用将被追究法律责任。
<!-- user-agreement-injected -->


# HTTP命令行测试工具 Skill 文档

## 一、能力边界：一页纸速查卡

### 1.1 能做什么（真实实现）

| 能力项 | 说明 | 示例 |
|--------|------|------|
| 构造HTTP请求 | 支持GET/POST/PUT/DELETE/PATCH/HEAD/OPTIONS | `cli POST https://api.example.com/users` |
| 自定义请求头 | 添加认证、内容类型等头部 | `cli GET https://api.example.com -H "Authorization: Bearer token"` |
| 请求体构造 | JSON、表单、原始文本 | `cli POST https://api.example.com -d '{"name":"test"}'` |
| 参数拼接 | 查询字符串自动编码 | `cli GET https://api.example.com -p "page=1&size=20"` |
| 响应格式化 | JSON高亮、缩进、截断 | 自动格式化JSON响应 |
| 超时控制 | 设置请求超时时间 | `cli GET https://api.example.com -t 10` |
| 跟随重定向 | 自动或手动控制 | `cli GET https://api.example.com -L` |
| 输出保存 | 响应体写入文件（原子化） | `cli GET https://api.example.com -o response.json` |
| 指数退避重试 | 网络错误自动重试（最多3次） | 默认启用，`--no-retry` 禁用 |
| 不验证TLS证书 | 跳过HTTPS证书验证 | `cli GET https://self-signed.badssl.com -k` |
| 自检测试 | 验证核心功能 | `cli --selftest` |

### 1.2 不能做什么（真实限制）

| 限制项 | 说明 |
|--------|------|
| 不支持WebSocket | 仅限HTTP/HTTPS协议 |
| 不支持文件上传 | 仅支持文本请求体 |
| 不支持Cookie持久化 | 每次调用独立会话 |
| 不支持代理配置 | 需在系统层面配置 |
| 不支持双向TLS | 仅支持常规HTTPS证书验证 |
| 不支持流式响应 | 响应体一次性加载到内存 |

### 1.3 适用对象

- 后端开发人员：快速验证接口逻辑
- 前端开发人员：联调时检查接口返回
- 测试工程师：构造边界条件请求
- DevOps人员：健康检查、接口监控

## 二、触发条件

### 2.1 显式触发

用户输入包含以下任一关键词时激活：
- `cli`（命令前缀）
- `http测试`、`接口调试`、`rest api`、`接口请求`、`api调试`
- `curl`（当用户意图是构造HTTP请求时）

### 2.2 隐式触发

用户描述以下场景时激活：
- "帮我测试一下这个接口"
- "用命令行发个POST请求"
- "检查这个API是否正常"

## 三、标准流程

### 3.1 输入解析

1. 识别用户意图（构造请求/调试接口/测试API）
2. 提取关键参数：URL、方法、请求头、请求体、查询参数
3. 确认参数完整性，缺失时提示用户补充

### 3.2 命令构造

根据参数生成标准命令：

## 许可证（License）

```text
MIT License

Copyright (c) {year} {holder}

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

## 失败处理

- 命令执行失败或返回非零退出码时，程序会输出明确错误信息并给出排查建议。
- 依赖缺失时提示安装命令；网络异常时建议重试并检查连接。
- 异常情况不中断主流程，错误信息包含具体原因（error context），便于定位修复。
## 前置条件

- 本技能开箱即用，无需额外安装依赖。
- 需要 Python 3.9+ 运行环境。
- 涉及网络请求时需保持网络连通。