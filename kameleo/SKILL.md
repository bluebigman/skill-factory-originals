---
slug: kameleo
name: kameleo
displayName: 反检测指纹 多账号管理 网页采集
description: 反检测浏览器指纹伪装，支持多账号管理与网页采集自动化。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: FlowForge Studio
agent_created: true
trigger_words: ["kameleo", "反检测浏览器", "指纹伪装", "浏览器自动化", "多账号管理", "指纹隔离", "账号矩阵", "采集防封"]

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

---

# Kameleo 反检测浏览器操作指南

## 一、能力边界（一页纸速查卡）

### 1.1 能做什么

| 能力项 | 说明 | 典型场景 |
|--------|------|----------|
| 指纹伪装 | 修改浏览器指纹参数（Canvas、WebGL、时区、字体、UA 等） | 绕过网站基于指纹的识别 |
| 多账号隔离 | 每个配置文件拥有独立指纹、存储、Cookie | 同时管理多个电商/社交账号 |
| 自动化采集 | 通过 CDP 协议驱动浏览器执行脚本 | 商品价格监控、公开数据抓取 |
| 批量操作 | 对多个配置文件执行相同指令 | 批量登录、批量发布、批量巡检 |

### 1.2 不能做什么

| 限制项 | 说明 |
|--------|------|
| 不保证绕过验证码 | 人机验证（reCAPTCHA/hCaptcha）依赖行为分析，指纹伪装无法单独解决 |
| 不提供代理服务 | 需自行准备住宅/数据中心代理，Kameleo 仅负责接入 |
| 不承担账号安全责任 | 账号封禁受平台风控策略影响，指纹伪装仅是其中一环 |
| 不支持原生移动端 | 仅支持桌面端浏览器内核（Chromium/Firefox/Safari 技术预览） |

### 1.3 适用对象

- 需要同时运营多个同平台账号的运营人员
- 需要采集公开网页数据的开发人员
- 需要模拟不同地区/设备访问效果的测试人员

---

## 二、触发方式与场景映射

### 2.1 触发词

| 触发词 | 场景描述 |
|--------|----------|
| kameleo | 直接调用本 Skill 时使用 |
| 反检测浏览器 | 需要伪装指纹或创建隔离环境时 |
| 指纹伪装 | 需要修改浏览器指纹参数时 |
| 浏览器自动化 | 需要驱动浏览器执行脚本时 |
| 多账号管理 | 需要同时管理多个账号时 |
| 指纹隔离 | 需要确保账号间无关联时 |
| 账号矩阵 | 需要批量创建/管理账号体系时 |
| 采集防封 | 需要降低采集时被识别风险时 |

### 2.2 场景映射表

| 用户说 | 实际需求 | 本 Skill 提供的方案 |
|--------|----------|---------------------|
| "我要同时登 10 个亚马逊账号" | 多账号隔离 | 创建 10 个独立配置文件，每个配置独立指纹 |
| "爬淘宝商品数据总是被封" | 采集防封 | 轮换指纹 + 代理 IP，降低关联风险 |
| "想模拟美国用户访问" | 地区伪装 | 修改时区、语言、地理位置参数 |
| "批量注册 50 个账号" | 批量操作 | 编写自动化脚本，循环创建配置文件并执行注册流程 |

---

## 三、标准操作流程

### 3.1 前置条件

| 条件 | 要求 | 检查方式 |
|------|------|----------|
| Kameleo 客户端 | 已安装并登录（v2.9+） | 打开客户端，确认左下角显示已连接 |
| 许可证 | 有效订阅（至少 Starter 版） | 客户端「帮助 → 关于」查看 |
| 代理资源 | 可选但建议准备 | 每个配置文件建议绑定独立代理 |
| 目标网站 | 已确认采集/操作合规 | 阅读目标网站 robots.txt 及服务条款 |

### 3.2 执行步骤

#### 步骤 1：创建配置文件

```
操作路径：Kameleo 客户端 → 新建配置文件 → 选择基础指纹
```

参数配置建议：

| 参数 | 推荐值 | 说明 |
|------|--------|------|
| 浏览器内核 | Chromium | 兼容性最好，自动化支持完善 |
| 操作系统 | 随机 | 避免全部使用同一 OS 指纹 |
| 语言 | 目标地区语言 | 与代理 IP 地区保持一致 |
| 时区 | 自动匹配 IP | 勾选「根据 IP 自动设置」 |
| WebGL 渲染器 | 随机 | 避免统一特征 |
| Canvas 指纹 | 噪声注入 | 默认开启即可 |

#### 步骤 2：绑定代理（可选但推荐）

```
操作路径：配置文件 → 网络设置 → 添加代理
```

代理格式支持：`http://user:pass@host:port` 或 `socks5://user:pass@host:port`

#### 步骤 3：启动浏览器并验证指纹

```bash
# 通过命令行启动指定配置文件
kameleo-cli start --profile-id "your-profile-id"

# 验证指纹是否生效（在浏览器中访问）
# 访问 https://browserleaks.com/canvas 检查 Canvas 指纹
# 访问 https://whoer.net 检查 IP 与语言一致性
```

#### 步骤 4：执行自动化操作

```python
# 使用 CDP 协议连接（Python 示例）
import asyncio
from kameleo.local_api_client import KameleoLocalApiClient

async def main():
    client = KameleoLocalApiClient()
    # 获取已启动的浏览器端口
    profile = client.get_base_profile("your-profile-id")
    cdp_port = profile.launcher.cdp_port
    
    # 通过 CDP 连接并执行脚本
    import websockets
    import json
    async with websockets.connect(f"ws://localhost:{cdp_port}") as ws:
        await ws.send(json.dumps({
            "id": 1,
            "method": "Runtime.evaluate",
            "params": {"expression": "document.title"}
        }))
        result = await ws.recv()
        print(result)

asyncio.run(main())
```

#### 步骤 5：批量执行

```bash
# 批量启动所有配置文件
kameleo-cli start --all

# 批量停止
kameleo-cli stop --all
```

### 3.3 输出规范

| 输出类型 | 格式要求 | 示例 |
|----------|----------|------|
| 配置文件列表 | JSON 数组 | `[{"id": "abc123", "name": "账号1", "status": "running"}]` |
| 自动化结果 | 结构化数据 | `{"url": "...", "title": "...", "status_code": 200}` |
| 错误日志 | 时间戳 + 错误码 + 描述 | `[2025-01-15 10:30:00] ERR-1001: 代理连接超时` |

---

## 四、置信度门控

当遇到以下情况时，**不得编造数据**，应输出 `[需核实:字段名]` 占位符：

| 场景 | 处理方式 |
|------|----------|
| 目标网站返回数据不完整 | 输出 `[需核实:商品价格]` 而非猜测数值 |
| 指纹验证结果不确定 | 输出 `[需核实:WebGL指纹是否生效]` |
| 代理 IP 归属地未知 | 输出 `[需核实:IP地理位置]` |
| 账号登录状态未知 | 输出 `[需核实:登录是否成功]` |

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| ERR-1001 | 代理连接超时 | "代理服务器无响应，请检查代理配置" | 1. 测试代理连通性 2. 更换代理端口 3. 确认代理认证信息 |
| ERR-1002 | 指纹加载失败 | "无法加载指定指纹，配置文件可能已损坏" | 1. 重新创建配置文件 2. 检查磁盘空间 3. 重启 Kameleo 客户端 |
| ERR-1003 | CDP 连接断开 | "浏览器进程异常退出，连接已断开" | 1. 检查浏览器崩溃日志 2. 降低并发数量 3. 更新显卡驱动 |
| ERR-1004 | 许可证过期 | "当前许可证已过期，请续费" | 1. 访问官网续费 2. 确认账号余额 3. 联系客服 |
| ERR-1005 | 目标网站拦截 | "目标网站返回 403/429，可能触发了风控" | 1. 更换代理 IP 2. 降低请求频率 3. 更换指纹配置 |

---

## 六、常见坑与反模式

### 坑 1：所有账号使用相同指纹

**错误做法**：创建 10 个配置文件，全部使用默认指纹。

**后果**：网站通过指纹聚类识别出账号关联，全部封禁。

**正确做法**：每个配置文件手动调整 2-3 个指纹参数（如 Canvas 噪声种子、字体列表、屏幕分辨率）。

### 坑 2：代理 IP 与指纹地区不一致

**错误做法**：使用美国代理，但指纹设置为中文语言 + 中国时区。

**后果**：触发风控的「IP 与语言不匹配」规则。

**正确做法**：勾选「根据 IP 自动设置时区和语言」，或手动保持三者一致。

### 坑 3：采集频率过高

**错误做法**：对同一网站每秒发送 10 个请求。

**后果**：IP 被限流，甚至触发法律风险。

**正确做法**：设置随机延迟 3-8 秒，模拟人类操作节奏。

### 坑 4：忽略浏览器自动化检测

**错误做法**：直接使用默认 CDP 连接，未隐藏自动化特征。

**后果**：网站通过 `navigator.webdriver` 属性识别出自动化。

**正确做法**：在启动参数中添加 `--disable-blink-features=AutomationControlled`，并在页面加载前注入反检测脚本。

### 坑 5：不保留原始数据备份

**错误做法**：批量执行前未备份配置文件。

**后果**：误操作导致配置损坏，无法恢复。

**正确做法**：执行批量操作前，导出配置文件备份（`.kameleo` 文件）。

---

## 七、渐进式阅读路径

### 7.1 新手速查卡（5 分钟上手）

1. 安装 Kameleo 客户端并登录
2. 新建配置文件 → 选择随机指纹 → 启动
3. 访问 `https://whoer.net` 验证指纹生效
4. 在浏览器中手动操作目标网站
5. 完成后停止浏览器，配置文件自动保存

### 7.2 进阶路径（自动化开发）

1. 阅读官方 API 文档（`https://docs.kameleo.io`）
2. 使用 Local API Client 连接本地服务
3. 编写 Python/Node.js 脚本控制浏览器
4. 集成代理池实现 IP 轮换
5. 构建批量任务调度系统

### 7.3 专家路径（风控对抗）

1. 研究目标网站的风控策略（通过 JS 逆向分析）
2. 定制指纹参数（修改 WebGL 参数、AudioContext 噪声）
3. 实现行为模拟（鼠标轨迹、键盘输入延迟）
4. 建立指纹轮换策略（定时更换指纹）
5. 监控账号健康度（登录成功率、操作成功率）

---

## 八、用户协议

<!-- user-agreement-injected -->

**使用本 Skill 即表示您同意以下条款：**

1. **责任承担**：使用者自行承担因使用本 Skill 产生的全部责任，包括但不限于账号封禁、法律纠纷、数据损失等。本 Skill 提供的是技术操作指导，不构成任何合规性保证。

2. **禁止反向工程**：不得对本 Skill 文档进行反向工程、反编译、破解或试图提取底层逻辑。不得将本 Skill 用于任何违反法律法规或平台服务条款的活动。

3. **合规使用**：使用者应确保其使用场景符合目标网站的服务条款、robots.txt 协议及当地法律法规。本 Skill 不鼓励、不纵容任何形式的网络攻击、数据窃取或侵权行为。

4. **免责声明**：本 Skill 按「现状」提供，不附带任何明示或暗示的担保。作者不对因使用本 Skill 造成的任何直接或间接损失承担责任。

---

## 九、许可证（License）

<!-- professional-license-embedded -->

**MIT License**

Copyright (c) 2025 原创作者（自持版权）

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

---

*本 Skill 由 AI 辅助生成，仅供参考。使用前请阅读 Kameleo 官方文档（https://docs.kameleo.io）以获取最新信息。*
