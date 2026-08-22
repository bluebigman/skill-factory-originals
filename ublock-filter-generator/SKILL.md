---
slug: ublock-filter-generator
name: ublock-filter-generator
displayName: 广告拦截 规则生成 过滤语法
description: 将自然语言描述转为uBlock Origin过滤规则，支持隐藏、拦截与正则匹配。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: FilterForge
agent_created: true
trigger_words: ["ublock过滤器","广告拦截规则","元素隐藏","网络请求拦截","正则过滤","uBlock Origin"]
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# uBlock Origin 过滤规则生成器

## 一、能力边界：一页纸速查卡

本 Skill 用于将日常语言描述转换为 uBlock Origin 可识别的过滤规则文本。它面向需要自定义浏览器广告拦截行为的普通用户、前端开发者与测试工程师。

| 能力维度 | 支持范围 | 不支持范围 |
|---------|---------|-----------|
| 元素隐藏 | 基于 CSS 选择器的隐藏规则（`##` 语法） | 无法验证选择器在目标页面是否真实存在 |
| 网络拦截 | 基于 URL 模式的请求拦截（`||` 与 `@@` 语法） | 无法模拟浏览器环境测试拦截效果 |
| 正则匹配 | 基于正则表达式的 URL 匹配（`/regex/` 语法） | 无法执行正则表达式，仅做语法结构检查 |
| 规则组合 | 单条规则生成，支持注释说明 | 不生成完整的规则列表文件 |
| 例外规则 | 生成 `@@` 开头的白名单规则 | 不处理高级的 `$` 选项修饰符（如 `$script`、`$image`） |

**适用对象**：需要快速生成过滤规则草稿的 uBlock Origin 用户；需要批量整理过滤需求的测试人员。

**不适用对象**：需要完整规则集管理、规则冲突检测、跨浏览器同步的高级用户。

---

## 二、触发方式：场景映射表

当你的描述中包含以下意图时，本 Skill 将被激活：

| 用户说（大白话） | 实际意图 | 输出规则类型 |
|----------------|---------|-------------|
| "把页面右上角的广告关掉" | 隐藏特定区域的元素 | 元素隐藏规则（`##`） |
| "这个网站的弹窗太烦了" | 隐藏弹窗容器 | 元素隐藏规则（`##`） |
| "别让这个地址加载图片" | 拦截特定 URL 请求 | 网络拦截规则（`||`） |
| "这个脚本拖慢速度，禁掉" | 拦截脚本文件 | 网络拦截规则（`||` + `$script`） |
| "除了登录页，其他都别弹广告" | 生成例外规则 | 白名单规则（`@@`） |
| "所有包含 ad 的链接都拦掉" | 正则匹配 URL | 正则规则（`/.../`） |

**触发词**：`ublock过滤器`、`广告拦截规则`、`元素隐藏`、`网络请求拦截`、`正则过滤`、`uBlock Origin`、`去广告`、`屏蔽元素`、`拦截请求`。

---

## 三、标准流程

### 前置条件

- 用户需提供明确的页面 URL 或元素描述（如"侧边栏的图片广告"）。
- 若涉及网络拦截，需提供完整的资源地址或可识别的 URL 片段。
- 若涉及正则，需说明匹配的 URL 特征。

### 执行步骤

**步骤 1：意图识别**

将用户描述归类为以下四类之一：
- 元素隐藏（视觉层面移除）
- 网络拦截（阻止资源加载）
- 例外放行（解除拦截）
- 正则匹配（模式化拦截）

**步骤 2：提取关键参数**

| 参数 | 说明 | 示例 |
|------|------|------|
| `target_url` | 规则生效的站点域名 | `example.com` |
| `selector` | CSS 选择器（元素隐藏用） | `#ad-banner`、`.sidebar .ads` |
| `resource_url` | 被拦截的资源地址 | `https://cdn.example.com/ads.js` |
| `pattern` | 正则表达式 | `advert|banner` |

**步骤 3：生成规则**

根据类型输出对应语法：

```
// 元素隐藏：目标域名 + ## + 选择器
example.com##.ad-container

// 网络拦截：|| + 资源域名/路径
||cdn.example.com/ads^

// 例外规则：@@ + 匹配模式
@@||example.com/login

// 正则规则：/ + 正则表达式 + /
/advert|banner/
```

**步骤 4：输出规范**

- 每条规则独立一行。
- 规则前附一行注释（`!` 开头），说明用途。
- 若信息不足，使用 `[需核实:字段]` 占位。

**输出示例**：

```
! 隐藏 example.com 首页顶部的广告横幅
example.com##.top-banner

! 拦截来自 adserver.example.com 的所有请求
||adserver.example.com^

! 放行登录页面的脚本加载
@@||example.com/login/script.js
```

---

## 四、置信度门控

当以下信息缺失时，**不得编造**，必须输出占位符：

| 缺失信息 | 占位符示例 | 后续处理 |
|---------|-----------|---------|
| 目标域名 | `[需核实:目标域名]` | 询问用户具体站点 |
| CSS 选择器 | `[需核实:元素选择器]` | 请用户提供元素特征或截图 |
| 资源完整地址 | `[需核实:资源URL]` | 请用户从开发者工具复制地址 |
| 正则表达式 | `[需核实:匹配模式]` | 请用户描述 URL 特征 |

**示例**：

```
! 隐藏 [需核实:目标域名] 上的 [需核实:元素选择器]
[需核实:目标域名]##[需核实:元素选择器]
```

---

## 五、错误码体系

| 错误码 | 错误场景 | 提示话术 | 修正步骤 |
|--------|---------|---------|---------|
| `E001` | 描述过于模糊，无法判断规则类型 | "请明确是要隐藏元素、拦截请求，还是放行资源？" | 引导用户补充意图关键词 |
| `E002` | 缺少目标域名 | "请提供规则生效的网站地址。" | 询问完整域名，如 `example.com` |
| `E003` | 元素描述无法转换为选择器 | "请描述元素的视觉位置或提供 HTML 片段。" | 建议用户使用浏览器开发者工具查看元素 |
| `E004` | URL 片段不完整 | "请提供完整的资源地址或可识别的路径片段。" | 从网络面板复制请求地址 |
| `E005` | 正则表达式语法错误 | "正则表达式存在语法问题，请检查括号与转义字符。" | 使用在线正则测试工具验证 |

---

## 六、FAQ 反模式对照

| 常见坑 | 反模式（错误做法） | 正确做法 |
|--------|-------------------|---------|
| 选择器过宽 | 使用 `##div` 隐藏所有 div | 使用具体类名或 ID，如 `##.ad-wrapper` |
| 域名遗漏端口 | 写 `example.com` 但页面是 `example.com:8080` | 确认端口号，规则写作 `example.com:8080##...` |
| 正则未转义 | 写 `/ad?/` 匹配 `ad` 后任意字符 | 明确意图：匹配字面量 `ad?` 需写 `/ad\?/` |
| 例外规则过宽 | `@@||example.com^` 放行整个站点 | 精确到路径，如 `@@||example.com/js/app.js` |
| 忽略规则优先级 | 同时生成隐藏与拦截规则，未考虑冲突 | 先写拦截规则，再写例外规则，注释标明优先级 |

---

## 七、渐进式披露：分层次阅读路径

### 速查卡（30 秒上手）

```
元素隐藏： 域名##选择器
网络拦截： ||资源地址^
例外放行： @@||资源地址
正则匹配： /正则表达式/
```

### 新手路径（首次使用）

1. 阅读「能力边界」了解能做什么。
2. 对照「场景映射表」找到自己的需求类型。
3. 按「标准流程」步骤 1-3 提供信息。
4. 将生成的规则粘贴到 uBlock Origin 的"我的规则"面板。

### 进阶路径（熟练用户）

1. 直接使用「错误码体系」排查生成失败的原因。
2. 参考「FAQ 反模式」优化规则精度。
3. 手动调整规则中的 `$` 选项修饰符（如 `$script`、`$image`、`$third-party`）以细化拦截范围。
4. 结合 uBlock Origin 的"元素选择器模式"验证隐藏效果。

---

## 八、用户协议

<!-- user-agreement-injected -->

**使用本 Skill 生成的任何规则，使用者自行承担全部责任。** 规则可能影响目标网站的正常显示或功能，请在应用前充分测试。

**禁止反向工程**：不得利用本 Skill 的输出逆向推导 uBlock Origin 的未公开内部逻辑，或将其用于绕过广告拦截机制的恶意用途。

本 Skill 仅提供规则生成指导，不保证规则在任意环境下的有效性。使用者应遵守目标网站的服务条款与当地法律法规。

---

## 九、许可证（License）

<!-- professional-license-embedded -->

**MIT License**

Copyright (c) 2024 FilterForge

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
