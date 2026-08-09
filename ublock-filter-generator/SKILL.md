---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: ublock-filter-generator
name: ublock-filter-generator
displayName: 网页净化 广告拦截 规则生成
description: 根据自然语言描述自动生成uBlock Origin过滤规则，支持选择器与正则表达式。
version: 1.0.2
rules_version: cpr-20260809-n251
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/ublock-filter-generator
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: FilterForge Studio
agent_created: true
trigger_words: ["广告过滤", "uBlock规则", "拦截规则", "元素屏蔽", "网页去广告", "屏蔽广告", "过滤规则", "去广告"]
---

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->


> 本内容由 AI 生成，仅供学习参考 <!-- ai-generated-notice -->

# uBlock Filter Generator — 网页净化规则生成器

## 一、能力边界速查卡

本 Skill 用于将日常语言描述转化为可直接粘贴到 uBlock Origin 自定义静态规则列表中的过滤语法。它覆盖了静态规则的全部主流形态，但不涉及动态规则（如临时开关、弹窗式白名单操作）。

| 能力维度 | 支持情况 | 说明 |
|---------|---------|------|
| 元素隐藏规则 | ✅ 支持 | 生成 `example.com##.selector` 形式规则 |
| 网络请求拦截 | ✅ 支持 | 生成 `\|\|tracker.example.com^` 形式规则 |
| 属性选择器 | ✅ 支持 | 支持 `[attr^="value"]`、`[attr*="value"]` 等 |
| 正则表达式 | ✅ 支持 | 生成 `/regex/` 形式规则，需谨慎使用 |
| 例外规则 | ✅ 支持 | 生成 `@@` 前缀规则 |
| 站点限定 | ✅ 支持 | 支持多域名逗号分隔 |
| 动态规则生成 | ❌ 不支持 | 不涉及 uBO 面板内的临时开关操作 |
| 复杂脚本注入 | ❌ 不支持 | 不生成 `+js()` 脚本let规则 |
| 规则调试建议 | ⚠️ 有限支持 | 仅提供基础排查建议，不包含浏览器调试指导 |

**适用对象**：需要快速为特定网站编写过滤规则的前端开发者、频繁处理网页广告的普通用户、维护个人过滤列表的爱好者。

---

## 二、触发方式与场景映射

直接使用自然语言描述你的需求，本 Skill 会解析意图并输出对应规则。以下为常见场景与触发语句示例：

| 使用场景 | 触发语句示例 | 预期输出 |
|---------|-------------|---------|
| 隐藏侧边栏广告 | "把 example.com 右侧的广告栏隐藏掉" | `example.com##.sidebar-ad` |
| 拦截追踪器 | "屏蔽 example.com 加载的 tracker 域名" | `\|\|tracker.example.com^` |
| 隐藏推广区块 | "去掉 example.com 里所有带 promo 字样的区块" | `example.com##div[class*="promo"]` |
| 拦截统计脚本 | "不加载 example.com 的统计脚本" | `\|\|stats.example.com/analytics.js` |
| 隐藏视频贴片 | "屏蔽 video.example.com 播放前的广告层" | `video.example.com##.ad-overlay` |
| 白名单放行 | "允许 example.com 的支付弹窗显示" | `@@example.com##.pay-modal` |

---

## 三、标准操作流程

### 前置条件

- 已安装 uBlock Origin 浏览器扩展（Chrome / Firefox / Edge 均支持）。
- 明确目标网站的完整域名（如 `www.example.com` 或 `example.com`）。
- 对目标元素有基本认知（如知道它是图片、文字链、还是整个区块）。

### 执行步骤

**步骤 1：描述需求**

用一句话说明你想屏蔽什么。请包含以下信息（缺一不可）：

- **目标域名**：哪个网站？（必填）
- **元素特征**：长什么样？（如"右侧栏""顶部横幅""带'广告'字样的区块"）
- **元素类型**：是图片、链接、还是整个容器？

**步骤 2：选择规则类型**

根据需求匹配以下规则类型：

| 需求描述 | 规则类型 | 语法前缀 |
|---------|---------|---------|
| 隐藏页面上的某个区块 | 元素隐藏 | `域名##选择器` |
| 阻止某个外部请求 | 网络拦截 | `\|\|域名^` 或 `\|\|域名/路径` |
| 放行某个被误拦的元素 | 例外规则 | `@@域名##选择器` |
| 匹配多个相似元素 | 属性选择器 | `域名##标签[属性*="关键词"]` |
| 匹配复杂模式 | 正则表达式 | `/正则内容/` |

**步骤 3：生成规则**

根据步骤 2 的选择，按以下模板生成规则：

```
元素隐藏：example.com##.class-name
网络拦截：||tracker.example.com^
属性选择：example.com##div[class*="ad"]
正则匹配：/^https?:\/\/.*\.example\.com\/ad/
```

**步骤 4：验证输出**

检查生成的规则是否满足以下条件：

- 域名拼写正确，无多余空格。
- 选择器语法完整（类名以 `.` 开头，ID 以 `#` 开头）。
- 网络拦截规则以 `||` 开头，以 `^` 结尾。
- 正则规则以 `/` 包裹，内部无未转义的特殊字符。

### 输出规范

- 每条规则独占一行，无多余说明文字。
- 多条规则之间用空行分隔。
- 若生成正则规则，同时提供对应的普通选择器版本作为备选。

---

## 四、置信度门控机制

当输入信息不足以生成精确规则时，本 Skill 不会猜测或编造，而是输出带有 `[需核实:字段]` 占位符的模板，由你补充确认。

| 缺失信息 | 输出示例 |
|---------|---------|
| 域名不明确 | `[需核实:域名]##.ad-banner` |
| 元素特征模糊 | `example.com##[需核实:选择器]` |
| 请求路径不完整 | `\|\|[需核实:完整域名]^` |
| 正则模式不确定 | `/[需核实:正则表达式]/` |

**处理原则**：

- 当描述中出现"大概""好像""可能"等模糊词汇时，自动触发置信度门控。
- 当描述包含多个候选域名时，分别生成规则并标注 `[需核实:选择其一]`。
- 当描述涉及动态加载内容（如"滚动后出现的广告"），输出规则时附加提示：`[提示:动态内容可能需要额外规则]`。

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|-------|------|---------|---------|
| E001 | 域名缺失 | "请提供需要过滤的网站域名。" | 补充域名后重新描述 |
| E002 | 选择器无效 | "无法从描述中提取有效选择器。" | 提供更具体的元素特征（类名、ID、标签） |
| E003 | 规则类型冲突 | "描述同时匹配多种规则类型，请明确优先级。" | 指定优先使用的规则类型 |
| E004 | 正则语法错误 | "正则表达式存在未转义字符。" | 检查特殊字符，使用 `\` 转义 |
| E005 | 超出能力范围 | "该需求涉及动态规则或脚本注入，超出本 Skill 范围。" | 参考 uBlock 官方文档手动编写 |
| E006 | 信息矛盾 | "描述中的域名与元素特征不匹配。" | 核对域名是否正确，元素是否属于该域名 |

---

## 六、FAQ 反模式对照

| 常见错误 | 反模式示例 | 正确做法 |
|---------|-----------|---------|
| 使用绝对化表达 | "这个规则一定能屏蔽所有广告" | 使用"可屏蔽""通常有效"等表述 |
| 忽略动态内容 | 只写一条静态规则就认为万事大吉 | 考虑动态加载场景，准备多条备选规则 |
| 过度使用正则 | 所有规则都用正则表达式实现 | 优先使用普通选择器，正则仅用于复杂匹配 |
| 忽略例外规则 | 只生成拦截规则，不考虑误伤 | 同时考虑生成 `@@` 例外规则 |
| 不验证规则 | 生成后直接粘贴，不做测试 | 先在 uBO 的"元素选择器模式"中验证再保存 |

---

## 七、渐进式披露阅读路径

### 新手路径（快速上手）

1. 阅读「能力边界速查卡」了解基本能力。
2. 使用「触发方式」中的示例语句发起请求。
3. 查看「标准操作流程」中的步骤 1-2 了解输入格式。
4. 直接使用生成的规则，无需深入理解语法。

### 进阶路径（深度使用）

1. 完整阅读「标准操作流程」全部步骤。
2. 掌握「置信度门控机制」理解输出质量。
3. 熟悉「错误码体系」快速排查问题。
4. 参考「FAQ 反模式对照」避免常见错误。
5. 结合 uBlock 官方文档深入理解规则语法。

---

## 八、规则生成参考表

以下为常用规则模式速查，可直接参考或组合使用：

| 目标 | 规则模式 | 示例 |
|-----|---------|------|
| 隐藏整个区块 | `域名##.类名` | `example.com##.ad-container` |
| 隐藏指定 ID | `域名##元素#ID` | `example.com##div#sidebar` |
| 隐藏带特定属性的元素 | `域名##元素[属性*="值"]` | `example.com##div[class*="banner"]` |
| 拦截整个域名 | `\|\|域名^` | `\|\|ads.example.com^` |
| 拦截特定路径 | `\|\|域名/路径` | `\|\|example.com/scripts/track.js` |
| 拦截带参数的请求 | `\|\|域名^$query=参数` | `\|\|example.com^$query=ad_id` |
| 放行特定元素 | `@@域名##选择器` | `@@example.com##.pay-modal` |
| 放行特定请求 | `@@\|\|域名^` | `@@\|\|cdn.example.com^` |

---

## 九、用户协议

使用本 Skill 即表示您同意以下条款：

1. **责任承担**：使用者应确保使用本 Skill 的行为符合当地法律法规及平台政策。不得将生成内容用于任何非法或未经授权的用途。因使用本 Skill 产生的任何直接或间接后果，由使用者自行承担全部责任。
2. **合法使用**：本 Skill 仅用于合法的广告过滤和网页内容管理，不得用于干扰网站正常运营、窃取数据或任何侵犯第三方权益的行为。
3. **禁止反向工程**：使用者不得对本 Skill 的底层逻辑、算法或实现方式进行反向工程、反编译或试图提取源代码。
4. **内容变更**：本 Skill 可能随时更新或调整，使用者应定期查看最新版本。
5. **免责声明**：本 Skill 按"原样"提供，不附带任何明示或暗示的保证，包括但不限于适销性、特定用途适用性和非侵权性。

<!-- user-agreement-injected -->

---

## 十、许可证（License）

本 Skill 采用 MIT 许可证发布：

```
MIT License

Copyright (c) 2026 FilterForge Studio

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

---

*本 Skill 由 AI 辅助生成，仅供参考。使用前请阅读 uBlock Origin 官方文档以获取完整语法支持。*
