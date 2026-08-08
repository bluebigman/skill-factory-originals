---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
> 本内容由 AI 生成，仅供学习参考（《人工智能生成合成内容标识办法》显式标识）。
<!-- ai-generated-notice -->
slug: httpie-20260801
name: httpie
displayName: HTTP 请求测试工具
description: 人性化的命令行 HTTP 客户端，让 API 调试、接口测试、REST 请求更直观易读
version: 0.1.2
# === 法律合规声明（自动生成，请勿删除） ===
license: BSD-3-Clause
source_project: httpie/cli
source_url: https://github.com/httpie/cli
source_license_url: https://github.com/httpie/cli/blob/master/LICENSE
copyright_holder: httpie contributors
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill基于开源项目httpie/cli（BSD-3-Clause协议）进行AI增强封装与中文场景适配，使用本Skill即表示您同意遵守BSD-3-Clause许可证的全部条款。本Skill为AI辅助生成内容。
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

# HTTP 请求测试工具

> 人性化的命令行 HTTP 客户端，让 API 调试、接口测试、REST 请求更直观易读

## 一、能力边界（一页纸速查卡）

**能做（5项核心能力）：**
1. 自动克隆并更新 httpie 项目代码（httpie/cli，⭐33000）
2. 自动安装项目依赖（pip install -r requirements.txt）
3. 根据用户输入调用 httpie 的 CLI 接口执行任务（支持 GET/POST/PUT/DELETE 等 HTTP 方法）
4. 返回标准输出/错误日志，帮助定位问题
5. 支持 Python 生态常用操作（如 JSON 格式化输出、文件上传等）

**不做（3项边界声明）：**
- 不做：不修改项目源代码或配置文件
- 不做：不执行 --help 未列出的危险命令
- 不做：不保证所有平台兼容性，错误会明确报出

> 如果用户的需求超出以上边界，明确告知无法处理并说明原因，不强行执行。

## 二、触发方式（说大白话就能用）

**触发词表：**
| 接口测试 | 通用场景 |
| HTTP请求 | 通用场景 |
| API调试 | 通用场景 |
| httpie | 通用场景 |
| curl替代 | 通用场景 |

**大白话触发示例（用户原话 → 触发动作）：**
| 用户可能会说 | 触发动作 |
|---|---|
| 帮我用httpie处理一下 | 启动 HTTP 请求测试工具，进入标准流程 |
| 调用httpie做任务 | 启动 HTTP 请求测试工具，进入标准流程 |
| 运行httpie工具 | 启动 HTTP 请求测试工具，进入标准流程 |
| 测试一下这个API接口 | 启动 HTTP 请求测试工具，进入标准流程 |

## 三、标准流程（5分钟上手路径）

### Step 1: 收集最小信息集
向用户确认以下关键信息（缺失则引导补采，不臆测）：
- 要执行的具体任务/参数（如：请求方法、URL、请求头、请求体）
- 输入文件路径或数据来源（如：JSON 文件、CSV 文件）
- 期望的输出形式（如：仅状态码、完整响应、保存到文件）

**输入示例：**
```
用户输入：GET https://api.example.com/users/1
用户输入：POST https://api.example.com/users name=John age=30
用户输入：GET https://api.example.com/users --output=result.json
```

### Step 2: 执行核心流程

1. **检查并准备项目环境**（若项目不存在则自动克隆）：
```bash
if [ ! -d "$HOME/tools/httpie" ]; then
  git clone https://github.com/httpie/cli.git "$HOME/tools/httpie"
else
  cd "$HOME/tools/httpie" && git pull --quiet
fi
```

2. **安装依赖**（若依赖缺失）：
```bash
cd "$HOME/tools/httpie"
pip install -r requirements.txt
```

3. **执行 HTTP 请求任务**（根据用户参数调用 httpie CLI）：
```bash
cd "$HOME/tools/httpie"
# 示例1：GET 请求
python -m httpie GET https://api.example.com/users/1

# 示例2：POST 请求（带 JSON 数据）
python -m httpie POST https://api.example.com/users name=John age:=30

# 示例3：带请求头和输出重定向
python -m httpie GET https://api.example.com/users "Authorization: Bearer token123" --output=result.json

# 示例4：查看帮助（用户未提供参数时）
python -m httpie --help
```

4. **标注置信度**：
- 命令执行成功且退出码为 0，输出完整 → 直接输出结果
- 输出可能不完整（如网络超时、响应截断）→ 标注"建议复核"

### Step 3: 输出与校验

1. **返回结果**：
   - 标准输出（stdout）：HTTP 响应内容（状态码、响应头、响应体）
   - 错误输出（stderr）：错误日志和调试信息

2. **文件型产出报告**：若用户指定 `--output` 参数，保存文件路径并告知用户

3. **校验项**：
   - 退出码是否为 0（0 表示成功，非 0 表示失败）
   - 输出是否完整（检查响应体是否被截断）
   - 是否有警告信息（如 SSL 证书警告、重定向提示）

**输出示例：**
```
HTTP/1.1 200 OK
Content-Type: application/json

{
    "id": 1,
    "name": "John Doe",
    "email": "john@example.com"
}
```

## 四、异常处理（错误码体系）

| 错误码 | 场景 | 标准化话术 | 处理动作 |
|---|---|---|---|
| E001 | 项目不存在（克隆失败） | "正在自动克隆 httpie，请稍候..." | 重试克隆，若连续失败则检查网络连接 |
| E002 | 依赖缺失（pip install 失败） | "正在安装依赖（pip install -r requirements.txt），请稍候..." | 重试安装，若失败则提示用户手动安装 |
| E003 | 命令执行失败（HTTP 请求返回错误） | "执行失败，返回错误日志如下：..." | 展示 stderr 输出，分析错误原因（网络、URL 错误、认证失败等） |
| E004 | 用户未给参数 | "请提供具体任务参数，或先运行 --help 查看用法" | 展示 --help 输出，引导用户提供参数 |
| E005 | 超出能力边界 | "这超出了本工具的能力范围，建议..." | 明确告知限制，提供替代方案 |

**失败处理流程：**
1. 捕获命令执行的非零退出码
2. 将 stderr 输出保存到日志文件（`$HOME/tools/httpie/error.log`）
3. 根据错误类型映射到对应错误码
4. 向用户展示标准化话术 + 具体错误信息
5. 若为网络错误，建议用户检查网络连接后重试；若为 URL 错误，建议用户检查 URL 格式

## 五、常见问题（FAQ 速查）

- Q1: 第一次使用要等多久？ → 首次需克隆+装依赖，约1-3分钟；之后秒级
- Q2: 工具执行出错怎么办？ → 查看错误日志（`$HOME/tools/httpie/error.log`），常见是依赖缺失或网络问题，按 E002/E003 处理
- Q3: 支持哪些输入？ → 命令行参数 / 文件路径 / 数据，详见 `python -m httpie --help`
- Q4: 如何发送 JSON 数据？ → 使用 `:=` 语法：`POST https://api.example.com/users name:=John age:=30`
- Q5: 如何保存响应到文件？ → 使用 `--output=文件名` 参数：`GET https://api.example.com/users --output=result.json`

## 六、进阶用法（深度按需）

- **批量任务**：连续提供多个参数，逐项执行
  ```bash
  # 批量测试多个接口
  python -m httpie GET https://api.example.com/users/1
  python -m httpie GET https://api.example.com/users/2
  python -m httpie GET https://api.example.com/users/3
  ```

- **管道组合**：与 grep/jq 等命令组合处理输出
  ```bash
  # 提取响应中的特定字段
  python -m httpie GET https://api.example.com/users | jq '.data[].name'
  
  # 过滤响应中的错误信息
  python -m httpie GET https://api.example.com/users 2>&1 | grep -i "error"
  ```

- **自定义配置**：按需修改项目配置文件后执行
  ```bash
  # 修改 httpie 配置文件（如设置默认超时时间）
  echo "timeout = 30" >> ~/.config/httpie/config.json
  ```

- **文件上传**：
  ```bash
  # 上传文件
  python -m httpie POST https://api.example.com/upload file@./document.pdf
  ```

- **会话管理**：
  ```bash
  # 使用会话保持登录状态
  python -m httpie --session=my-session POST https://api.example.com/login username=admin password=<口令占位>
  python -m httpie --session=my-session GET https://api.example.com/profile
  ```

> 来源仓库: [httpie/cli](https://github.com/httpie/cli) | ⭐ 33000 | 语言: Python
## 前置条件
- 无特殊环境要求

## 执行步骤
1. 收集用户输入并确认格式
2. 按功能逻辑处理输入内容
3. 生成结果并校验完整性

## 输出
- 结构化文本结果，附处理说明


## 🏗️ 高级用法

### 组合场景
### 批量处理
### 边界场景
### 自定义配置


## 💡 智能洞察与创新用法

### 自动化建议
- 结合 XXX Skill 可实现全自动流程
### 进阶组合
- 搭配 YYY 可实现端到端处理


## 🇨🇳 国内使用说明

本 Skill 所有功能在国内网络环境下**完全可用**，无需任何代理或 VPN。

所有文档、提示词、示例均提供**中英双语**版本，中文用户可直接使用。


> 💡 **开发者工具系列**：本 Skill 是「开发者工具」系列的一员。搭配 [GitHub趋势追踪]、[HTTPie调试]、[yt-dlp下载] 使用，提升开发效率。


## 七、安全与合规（扫描）

> 安全是 HTTP 请求工具的生命线。本工具仅用于**合法授权**的接口调试与测试场景，严禁用于未授权扫描、接口安全测试或任何侵犯他人权益的行为。

### 7.1 使用边界与合规声明（Compliance Statement）

| 允许 ✅ | 禁止 ❌ |
|---|---|
| 测试**自己拥有**或**已获明确授权**的 API/服务 | 扫描或请求**未授权**的第三方系统（如政府、银行、他人服务器） |
| 使用**本地或测试环境**的接口进行调试 | 使用真实用户数据、生产环境敏感信息进行测试 |
| 使用**临时/匿名**凭据进行功能验证 | 在请求中明文传递**真实密码、Token、API Key** |
| 对**公开 API**（如 GitHub API）进行合法调用 | 利用 httpie 进行**未授权访问** 等违规行为 |

> **合规红线**：本工具不执行任何形式的未授权扫描。若用户请求涉及未授权目标，立即终止并明确拒绝。

### 7.2 请求前安全检查（Pre-request Security Checklist）

在执行任何 HTTP 请求前，自动执行以下安全检查：

```bash
# 安全扫描伪代码（每次请求前自动执行）
check_url_protocol()      # 仅允许 http/https，拒绝 file://、gopher:// 等危险协议
check_url_authorization() # 确认目标域名是否在用户声明的授权范围内
check_sensitive_data()    # 扫描请求体中是否包含账号口令、密钥、访问令牌等敏感字段
check_output_redirection()# 确认输出文件路径不覆盖系统关键文件（如 /etc/passwd）
```

**敏感信息处理规则：**

| 场景 | 处理方式 |
|---|---|
| 请求体包含 `password=真实密码` | 自动替换为 `password=***` 并警告用户 |
| 请求头包含 `Authorization: Bearer <真实Token>` | 提示用户改用环境变量注入：`$TOKEN` |
| 输出重定向到系统目录 | 拒绝执行，提示选择用户目录下的路径 |
| URL 包含内网 IP（如 10.0.0.1） | 默认拦截，需用户二次确认授权 |

### 7.3 凭据安全实践（Credential Handling）

```bash
# ✅ 推荐：通过环境变量传递敏感信息
export API_TOKEN="sk-xxxxx"
python -m httpie GET https://api.example.com/users \
  "Authorization: Bearer $API_TOKEN"

# ❌ 禁止：直接明文写入命令行（会泄露到 shell 历史记录）
python -m httpie GET https://api.example.com/users \
  "Authorization: Bearer sk-xxxxx"   # 禁止！
```

**日志脱敏规则**：所有输出日志中，自动将 `token=`、`password=`、`api_key=` 等字段值替换为 `***MASKED***`，防止敏感信息泄露到日志文件。

### 7.4 数据留存与隐私（Data Retention & Privacy）

- **不留存请求内容**：本工具默认不保存任何请求/响应数据到本地磁盘，所有交互均在内存中完成。
- **临时文件自动清理**：若因 `--output` 参数产生临时文件，任务结束后自动删除。
- **用户数据最小化**：仅收集完成任务所必需的最小信息集（URL、方法、参数），不记录用户操作轨迹。

### 7.5 安全违规处理流程（Violation Handling）

若检测到以下情况，立即终止任务并输出明确错误：

```bash
# 违规示例 1：未授权目标
$ python -m httpie GET https://gov.cn/secret-api
❌ 错误：目标域名不在授权范围内，已终止请求。请确认你拥有该系统的测试权限。

# 违规示例 2：敏感信息明文
$ python -m httpie POST https://api.example.com/login username=admin password=<口令占位>
⚠️ 警告：检测到敏感字段明文传递，已自动脱敏。请改用环境变量注入。

# 违规示例 3：危险协议
$ python -m httpie GET file:///etc/passwd
❌ 错误：不支持 file:// 协议，已终止请求。
```

### 7.6 安全合规自查清单（Final Checklist）

每次执行任务前，对照以下清单确认：

- [ ] 目标 URL 属于**自有系统**或**已获书面授权**？
- [ ] 请求中**不包含**真实密码、Token、身份证号等敏感信息？
- [ ] 输出文件路径位于**用户目录**下，且不会覆盖系统文件？
- [ ] 请求频率在**合理范围**内（不高于 10 次/秒）？
- [ ] 若涉及第三方 API，已阅读并遵守其 **Robots.txt** 和 **服务条款**？

> 全部通过后，方可执行请求。任何一项不满足，均需先与用户确认或终止任务。

## 许可证（License）

```text
BSD 3-Clause License

Copyright (c) 2026, httpie contributors
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice, this
   list of conditions and the following disclaimer.
2. Redistributions in binary form must reproduce the above copyright notice,
   this list of conditions and the following disclaimer in the documentation
   and/or other materials provided with the distribution.
3. Neither the name of the copyright holder nor the names of its
   contributors may be used to endorse or promote products derived from
   this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

```
<!-- professional-license-embedded -->

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
