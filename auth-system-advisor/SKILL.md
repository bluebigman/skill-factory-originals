---
slug: auth-system-advisor
name: auth-system-advisor
displayName: 认证集成 配置向导 故障排查
description: 提供 authentik 认证系统集成方案、配置指南与故障排查支持。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: TechFlow Studio
agent_created: true
trigger_words: ["认证系统集成", "authentik", "身份验证", "SSO", "单点登录", "OIDC配置", "身份认证对接"]
---

> 本内容由 AI 生成，仅供学习参考 <!-- ai-generated-notice -->

# authentik 认证系统集成顾问

## 一、能力边界（速查卡）

### 1.1 本 Skill 能做什么

| 能力项 | 说明 |
|--------|------|
| 方案设计 | 提供 authentik 作为身份提供者（IdP）的 OIDC 集成方案 |
| 配置指导 | 分步指导 Provider、Application 的创建与关联 |
| 参数解释 | 说明 Client ID、Client Secret、Redirect URI 等核心参数含义 |
| 故障排查 | 针对登录跳转失败、回调错误等常见问题给出排查路径 |
| 流程梳理 | 从创建到验证的完整集成链路梳理 |

### 1.2 本 Skill 不能做什么

| 限制项 | 说明 |
|--------|------|
| 不替代官方文档 | 版本升级后的界面差异请以 authentik 官方文档为准 |
| 不处理非 OIDC 协议 | SAML、LDAP、Proxy 等协议不在本 Skill 覆盖范围 |
| 不提供代码级定制 | 目标应用的源码修改需由开发团队自行完成 |
| 不保证兼容性 | 不同版本 authentik 的 API 与界面可能存在差异 |
| 不承担运维责任 | 生产环境的变更操作需由具备权限的运维人员执行 |

### 1.3 适用对象

- 需要将 authentik 与内部应用（Wiki、GitLab、Grafana 等）对接的运维/开发人员
- 正在评估 SSO 方案、需要快速了解 authentik 集成路径的技术决策者
- 已部署 authentik 但登录流程异常、需要排查思路的排障人员

---

## 二、触发方式

### 2.1 触发词

当对话中出现以下关键词时，本 Skill 自动激活：

- 认证系统集成
- authentik
- 身份验证
- SSO / 单点登录
- OIDC 配置
- 身份认证对接

### 2.2 场景映射表

| 用户实际诉求（大白话） | 本 Skill 的响应策略 |
|----------------------|-------------------|
| "我想让公司系统用同一个账号登录" | 提供 OIDC Provider 创建与参数配置指南 |
| "authentik 怎么跟我们的 Wiki 对接？" | 给出从 Provider 到 Application 的完整配置路径 |
| "登录时跳转不过去 / 回调报错" | 按错误码体系给出排查步骤与修正建议 |
| "SSO 配置里那些参数填什么？" | 提供参数对照表与填写示例 |
| "配置完了怎么确认没问题？" | 给出端到端验证流程与检查清单 |

---

## 三、标准流程

### 3.1 前置条件

在开始配置前，请确认以下条件已满足：

| 序号 | 前置条件 | 验证方式 |
|------|---------|---------|
| 1 | authentik 已部署且管理员账号可登录 | 访问 authentik 管理界面确认可正常登录 |
| 2 | 目标应用支持 OIDC 协议 | 查阅目标应用文档确认其认证方式 |
| 3 | 已确定回调地址（Redirect URI） | 目标应用认证设置页面可获取 |
| 4 | 网络可达性 | 目标应用服务器能访问 authentik 域名 |

### 3.2 执行步骤

#### 阶段一：创建 OIDC Provider

1. 登录 authentik 管理界面，进入 **Directory → Providers** 页面。
2. 点击右上角 **Create** 按钮，在协议列表中选择 **OIDC Provider**。
3. 填写以下核心参数：

| 参数名 | 必填 | 说明 | 示例值 |
|--------|------|------|--------|
| Name | 是 | Provider 显示名称 | `wiki-oidc` |
| Client Type | 是 | 客户端类型 | `Confidential` |
| Redirect URIs | 是 | 允许的回调地址（可多个） | `https://wiki.example.com/callback` |
| Signing Key | 是 | 签名密钥 | 选择已有的 RSA Key 或新建 |
| Scopes | 否 | 授权范围 | 默认包含 openid、profile、email |

4. 点击 **Save** 后，系统生成 `Client ID` 与 `Client Secret`。**Client Secret 仅显示一次**，请立即复制并妥善保存。

#### 阶段二：配置目标应用

1. 登录目标应用的认证设置页面，找到 OIDC / SSO 配置区域。
2. 填入 authentik 提供的信息：

| 目标应用字段 | 对应 authentik 值 |
|-------------|-------------------|
| Client ID | 阶段一生成的 Client ID |
| Client Secret | 阶段一生成的 Client Secret |
| Authorization Endpoint | `https://<authentik域名>/application/o/authorize/` |
| Token Endpoint | `https://<authentik域名>/application/o/token/` |
| UserInfo Endpoint | `https://<authentik域名>/application/o/userinfo/` |
| JWKS Endpoint | `https://<authentik域名>/application/o/jwks/` |

> 注：`<authentik域名>` 替换为你的实际部署域名。若使用自签名证书，需确保目标应用信任该证书链。

#### 阶段三：关联 Application

1. 导航至 **Directory → Applications**，点击 **Create**。
2. 填写应用名称（如 `wiki-app`）与 Slug（如 `wiki-app`）。
3. 在 **Provider** 下拉框中选择阶段一创建的 Provider。
4. 保存配置。此时 authentik 侧配置完成。

#### 阶段四：验证登录

1. 从目标应用发起一次登录尝试（点击"使用 SSO 登录"按钮）。
2. 确认浏览器被重定向至 authentik 登录页面（URL 包含 authentik 域名）。
3. 输入 authentik 中的用户凭据完成登录。
4. 确认登录成功后跳转回目标应用，且用户信息（用户名、邮箱等）正确显示。

### 3.3 输出规范

完成配置后，建议输出以下交付物：

- **配置摘要表**：包含 Provider 名称、Client ID（脱敏）、回调地址、关联应用列表
- **验证记录**：登录测试的时间、结果、异常截图
- **回滚方案**：如需回退，删除 Application 关联、停用 Provider 的步骤说明

---

## 四、置信度门控

当出现以下情况时，本 Skill 将输出 `[需核实:字段]` 占位符，而非编造信息：

| 场景 | 处理方式 |
|------|---------|
| 用户未提供 authentik 版本号 | 提示"不同版本界面可能有差异，请确认版本号" |
| 目标应用类型未知 | 输出 `[需核实:目标应用支持的OIDC配置项]` |
| 回调地址不确定 | 输出 `[需核实:目标应用的回调URL]` |
| 证书配置情况不明 | 输出 `[需核实:authentik证书类型及信任链]` |
| 用户权限未知 | 提示"需确认当前账号是否有 Provider 创建权限" |

---

## 五、错误码体系

| 错误码 | 现象描述 | 提示话术 | 修正步骤 |
|--------|---------|---------|---------|
| E-001 | 登录时跳转至 authentik 后显示 `Invalid redirect_uri` | "回调地址与 Provider 配置不匹配" | 1. 核对目标应用配置中的回调地址<br>2. 与 authentik Provider 中的 Redirect URIs 比对<br>3. 确保协议（http/https）与域名完全一致 |
| E-002 | 登录成功后跳回应用但提示 `Invalid client` | "Client ID 或 Secret 填写错误" | 1. 重新复制 authentik 中的 Client ID<br>2. 确认 Secret 未包含多余空格<br>3. 若 Secret 丢失，需在 Provider 中重新生成 |
| E-003 | 点击登录后页面无响应或超时 | "网络连通性或端点地址错误" | 1. 从目标应用服务器 curl 测试 authentik 端点<br>2. 确认 Endpoint URL 拼写正确<br>3. 检查防火墙/安全组规则 |
| E-004 | 登录成功但用户信息为空 | "Scope 配置缺失" | 1. 在 Provider 中确认已勾选 email、profile 等 Scope<br>2. 检查目标应用请求的 Scope 列表 |
| E-005 | 提示 `Invalid token` 或 `Token expired` | "密钥轮换或时间同步问题" | 1. 检查 authentik 与目标应用服务器时间是否同步<br>2. 确认 Signing Key 是否被更换<br>3. 重新触发登录流程获取新 Token |

---

## 六、FAQ 反模式

### 6.1 常见坑位

| 坑位 | 反模式（错误做法） | 正模式（推荐做法） |
|------|-------------------|-------------------|
| Secret 丢失 | 在 Provider 中反复重置 Secret 导致旧配置失效 | 创建时立即保存；丢失后统一更新所有关联应用 |
| 回调地址不一致 | 配置时省略端口号或路径 | 严格按目标应用要求填写完整 URL，含端口与路径 |
| 多环境混用 | 生产与测试共用同一 Provider | 为不同环境分别创建 Provider 与 Application |
| 忽略 Scope | 仅使用默认 Scope 导致用户信息不全 | 按需勾选 email、profile、groups 等 Scope |
| 证书信任缺失 | 自签名证书未导入目标应用信任库 | 提前将 CA 证书导入目标应用运行环境的信任存储 |

### 6.2 反模式对照

| 反模式 | 问题描述 | 替代方案 |
|--------|---------|---------|
| 直接修改 Provider 的 Client ID | 会导致所有已配置应用失效 | 新建 Provider 并逐步迁移应用 |
| 在目标应用硬编码 Token | Token 会过期，且存在安全风险 | 使用标准 OIDC 流程获取 Token |
| 跳过验证直接上线 | 配置错误未被发现，影响生产用户 | 先在测试环境完成全流程验证 |

---

## 七、渐进式披露

### 7.1 速查卡（30 秒上手）

```
创建 Provider → 获取 Client ID/Secret → 配置目标应用 → 关联 Application → 验证登录
```

### 7.2 新手路径（首次集成）

1. 阅读「三、标准流程」的完整步骤
2. 按阶段一至阶段四顺序执行
3. 遇到问题对照「五、错误码体系」排查
4. 完成验证后记录配置摘要

### 7.3 进阶路径（优化与排障）

1. 熟悉「六、FAQ 反模式」避免常见错误
2. 深入理解 Scope 与 Claim 映射关系
3. 学习 authentik 的 Policy 与 Binding 机制实现细粒度访问控制
4. 关注 authentik 版本更新日志，及时调整配置

---

## 八、用户协议

<!-- user-agreement-injected -->

**使用本 Skill 即表示您同意以下条款：**

1. **责任承担**：使用者自行承担因使用本 Skill 产生的全部责任。包括但不限于因配置错误导致的系统故障、数据丢失或安全事件。
2. **禁止反向工程**：不得对本 Skill 进行反向工程、反编译、破解或试图提取底层逻辑。
3. **无担保声明**：本 Skill 按"现状"提供，不附带任何明示或暗示的担保，包括但不限于适销性、特定用途适用性。
4. **合规使用**：使用者应确保其使用行为符合当地法律法规及 authentik 相关许可条款。

---

## 九、许可证（License）

<!-- professional-license-embedded -->

本 Skill 采用 MIT 许可证发布：

```
MIT License

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
```

---

*本 Skill 由 AI 辅助生成，仅供参考。使用前请阅读 authentik 官方文档及上述协议条款。*
