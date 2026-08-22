---
slug: huashu-design
name: huashu-design
displayName: 画术设计 高保真原型 幻灯片 交互动画
description: 在 Claude Code 中直接生成 HTML 原生高保真原型、幻灯片与交互动画。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 界面工坊
agent_created: true
trigger_words: ["huashu-design", "画术设计", "HTML 原型", "高保真原型", "幻灯片", "交互原型", "页面设计", "动效演示"]
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

> 本 Skill 由 AI 辅助生成，仅供参考

# 画术设计（huashu-design）技能文档

## 一、能力边界（一页纸速查卡）

### 1.1 能做什么

| 能力项 | 说明 | 输出形式 |
|--------|------|----------|
| 高保真原型 | 根据需求生成完整 HTML 页面，包含布局、样式、交互 | 完整 HTML 代码 |
| 幻灯片演示 | 生成基于 HTML/CSS 的幻灯片，支持翻页切换 | 完整 HTML 代码 |
| 交互动画 | 生成按钮悬停、页面切换、元素动效等交互效果 | 完整 HTML 代码 |
| 组件化设计 | 生成按钮、卡片、导航栏、表单等常见 UI 组件 | 完整 HTML 代码 |
| 响应式布局 | 适配桌面端与移动端的不同屏幕尺寸 | 完整 HTML 代码 |

### 1.2 不能做什么

| 限制项 | 说明 |
|--------|------|
| 不生成后端代码 | 不包含服务器端逻辑、数据库操作、API 接口 |
| 不生成框架代码 | 不输出 React/Vue/Angular 等框架代码，仅限原生 HTML/CSS/JS |
| 不生成图片资源 | 不生成图片文件，仅使用占位符或 CSS 绘制 |
| 不保证浏览器兼容性 | 建议使用最新版 Chrome/Edge/Firefox 查看 |
| 不处理复杂业务逻辑 | 不实现登录验证、支付流程、数据持久化等 |

### 1.3 适用对象

- 产品经理：快速验证交互方案
- UI 设计师：将设计稿转化为可交互原型
- 前端学习者：学习 HTML/CSS/JS 原生实现
- 项目演示者：制作轻量级演示文稿

---

## 二、触发方式

### 2.1 触发词

直接使用以下任一方式触发本技能：

- `huashu-design`
- `画术设计`
- `HTML 原型`
- `高保真原型`
- `幻灯片`
- `交互原型`
- `页面设计`
- `动效演示`

### 2.2 场景映射表

| 你的需求（大白话） | 触发指令示例 | 预期输出 |
|-------------------|-------------|----------|
| "帮我做一个登录页面" | `画术设计：登录页面，包含用户名密码输入框和登录按钮` | 完整 HTML 登录页 |
| "做个产品介绍幻灯片" | `huashu-design：产品介绍幻灯片，5页，每页一个核心卖点` | 可翻页的 HTML 幻灯片 |
| "按钮点击要有动画效果" | `画术设计：按钮点击时产生波纹扩散动画` | 带交互动画的 HTML 页面 |
| "做一个移动端风格的设置页" | `HTML 原型：移动端设置页面，包含开关和列表项` | 移动端适配的 HTML 页面 |

---

## 三、标准流程

### 3.1 前置条件

- 已安装 Claude Code 环境
- 明确描述需求（一句话即可，越具体越好）
- 如需特定风格，请附参考描述（如"简约风""暗色主题"）

### 3.2 执行步骤

**第一步：描述需求**

用一句话说明你要什么，包含以下要素（可选）：

| 要素 | 示例 |
|------|------|
| 页面类型 | 登录页、首页、设置页、幻灯片 |
| 风格偏好 | 简约、科技感、复古、渐变 |
| 功能要求 | 表单验证、轮播图、折叠面板 |
| 尺寸适配 | 桌面端、移动端、两者兼顾 |

**第二步：等待生成**

系统自动输出完整 HTML 代码，包含：

- `<!DOCTYPE html>` 声明
- `<head>` 中的样式定义（内联 CSS 或 `<style>` 标签）
- `<body>` 中的页面结构
- `<script>` 中的交互逻辑（如有需要）

**第三步：保存运行**

1. 复制生成的代码
2. 粘贴到文本编辑器，保存为 `.html` 文件（如 `prototype.html`）
3. 使用浏览器打开该文件即可查看效果

### 3.3 输出规范

- 所有代码为原生 HTML/CSS/JavaScript，不依赖外部库
- 样式使用内联 `<style>` 或 `<style>` 标签，不引用外部 CSS 文件
- 图片使用占位符（如 `https://via.placeholder.com/300x200`）或 CSS 渐变替代
- 代码包含必要的注释，说明关键结构

---

## 四、置信度门控

当需求描述不完整或存在歧义时，系统会输出 `[需核实:字段]` 占位符，而非编造内容。

### 常见需核实字段

| 字段 | 示例 | 缺失时的占位输出 |
|------|------|-----------------|
| 页面数量 | 幻灯片页数 | `[需核实:幻灯片页数]` |
| 颜色主题 | 主色调 | `[需核实:主色调]` |
| 功能细节 | 表单字段 | `[需核实:表单字段列表]` |
| 目标设备 | 桌面/移动 | `[需核实:目标设备]` |

### 处理方式

- 遇到占位符时，请补充相关信息后重新触发
- 或接受默认值（如无特别说明，默认适配桌面端）

---

## 五、错误码体系

| 错误码 | 错误描述 | 提示话术 | 修正步骤 |
|--------|----------|----------|----------|
| E001 | 需求过于模糊 | "请提供更具体的页面类型或功能描述" | 补充页面类型、风格、功能等细节 |
| E002 | 需求超出能力范围 | "本技能仅支持原生 HTML/CSS/JS，不支持框架代码" | 调整需求为原生实现，或拆分需求 |
| E003 | 代码生成不完整 | "输出代码缺少闭合标签，请检查" | 重新触发，或手动补全缺失标签 |
| E004 | 交互逻辑冲突 | "多个动画效果存在冲突，已简化处理" | 明确优先级，或分次生成 |

---

## 六、FAQ 反模式

### 常见坑与反模式对照

| 常见坑 | 反模式（错误做法） | 正确做法 |
|--------|-------------------|----------|
| 需求描述过于笼统 | "帮我做个网页" | 明确页面类型、用途、风格 |
| 期望生成图片素材 | "生成一张 logo 图片" | 使用 CSS 绘制或占位符替代 |
| 要求使用 React 组件 | "用 React 写个组件" | 本技能仅支持原生 HTML/CSS/JS |
| 期望自动部署上线 | "帮我部署到服务器" | 本技能仅生成代码，部署需自行完成 |
| 一次生成过多页面 | "做一个 50 页的完整网站" | 分批次生成，每次聚焦一个页面或模块 |

---

## 七、渐进式披露

### 7.1 速查卡（30 秒上手）

```
1. 输入：画术设计：<你的需求>
2. 等待：自动输出 HTML 代码
3. 保存：复制到 .html 文件
4. 打开：浏览器查看效果
```

### 7.2 新手路径（5 分钟入门）

1. 从简单需求开始，如"做一个带标题和按钮的页面"
2. 逐步增加复杂度：添加表单、导航栏、卡片布局
3. 尝试生成 3-5 页的幻灯片
4. 参考输出代码，学习 HTML 结构

### 7.3 进阶路径（深入使用）

1. 组合多个功能：登录页 + 表单验证 + 动画效果
2. 使用响应式布局适配移动端
3. 自定义 CSS 变量控制主题色
4. 实现复杂交互：轮播图、折叠面板、模态框

---

## 八、用户协议

<!-- user-agreement-injected -->

**使用本技能生成的代码前，请仔细阅读以下条款：**

1. 本技能生成的代码仅供学习、测试和内部评估使用。使用者自行承担全部责任，包括但不限于代码的正确性、安全性、合规性以及因使用产生的任何后果。

2. 禁止对本技能生成的代码进行反向工程、反编译或试图提取底层逻辑用于商业竞争。

3. 使用者应确保其使用场景符合当地法律法规，不得将生成内容用于侵权、欺诈或其他非法用途。

4. 本技能不提供任何形式的明示或暗示担保，包括但不限于适销性、特定用途适用性。

---

## 九、许可证（License）

<!-- professional-license-embedded -->

### MIT License

Copyright (c) 2024 界面工坊

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
