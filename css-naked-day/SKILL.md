---
slug: css-naked-day
name: css-naked-day
displayName: 样式剥离 裸奔日 全站去样式
description: 在CSS裸奔日自动禁用全站样式，让网页回归纯HTML本色。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: StyleShed
agent_created: true
trigger_words: ["css naked day", "样式裸奔日", "禁用样式", "裸样式模式", "样式剥离", "去样式化", "无样式浏览"]
---

> 本内容由 AI 生成，仅供学习参考 <!-- ai-generated-notice -->

# CSS Naked Day 样式剥离 Skill

## 一、能力边界（一页纸速查卡）

### 能做什么
| 能力项 | 说明 | 示例 |
|--------|------|------|
| 全站样式禁用 | 在指定日期（4月9日）自动移除所有 CSS 文件引用 | 移除 `<link rel="stylesheet">` 标签 |
| 内联样式清理 | 删除页面中的 `<style>` 块与元素内联 `style` 属性 | 清除 `style="color:red"` |
| 样式恢复 | 日期过后自动恢复原有样式引用 | 重新注入原 CSS 链接 |
| 白名单保护 | 可指定某些样式（如打印样式）不被剥离 | 保留 `media="print"` 的样式表 |

### 不能做什么
- 不能修改 HTML 结构本身（如删除 `<div>` 或调整 DOM 层级）
- 不能处理通过 JavaScript 动态注入的样式（需额外配置）
- 不能优化剥离后的页面布局——裸样式页面可能错乱，属正常现象
- 不能保证所有第三方组件（如富文本编辑器）在无样式下可用

### 适用对象
- 个人博客、内容型网站、文档站点
- 想参与 CSS Naked Day 活动的开发者
- 需要临时检查 HTML 语义结构的团队

### 不适用对象
- 强依赖 CSS 的 Web 应用（如后台管理系统、复杂交互页面）
- 有严格品牌视觉规范的企业官网
- 电商、银行等对视觉呈现有合规要求的站点

---

## 二、触发方式

### 触发词
直接使用以下任一短语即可激活本 Skill：

| 触发词 | 场景说明 |
|--------|----------|
| `css naked day` | 英文原词，最通用 |
| `样式裸奔日` | 中文直译 |
| `禁用样式` | 描述动作 |
| `裸样式模式` | 描述状态 |
| `样式剥离` | 描述过程 |
| `去样式化` | 同义补充 |
| `无样式浏览` | 描述目的 |

### 场景映射表

| 你说的话 | Skill 会做什么 |
|----------|----------------|
| "帮我准备 css naked day" | 扫描项目，列出所有样式文件，生成剥离清单 |
| "今天裸奔日，把样式都禁了" | 执行样式剥离，移除 CSS 引用 |
| "看看没样式长啥样" | 生成无样式预览页面 |
| "样式恢复了没" | 检查日期，若已过则恢复样式 |

---

## 三、标准流程

### 前置条件
1. 项目目录结构清晰，CSS 文件路径可被识别
2. 已确认参与 CSS Naked Day 的日期（每年 4 月 9 日）
3. 已备份原始文件（或使用 Git 等版本控制）

### 执行步骤

#### 步骤 1：扫描样式清单

```bash
# 在项目根目录执行
find . -name "*.css" -o -name "*.html" | sort
```

输出示例：
```
./index.html
./about.html
./css/main.css
./css/print.css
```

#### 步骤 2：生成剥离计划

| 文件类型 | 处理方式 | 说明 |
|----------|----------|------|
| `<link rel="stylesheet">` | 移除标签 | 保留 `media="print"` 的标签 |
| `<style>` 块 | 移除内容 | 保留 `<style>` 空标签或整体删除 |
| 内联 `style=""` | 删除属性 | 保留元素本身 |
| `@import` 语句 | 注释掉 | 在 CSS 文件内处理 |

#### 步骤 3：执行剥离

```html
<!-- 剥离前 -->
<link rel="stylesheet" href="/css/main.css">
<link rel="stylesheet" href="/css/print.css" media="print">
<div style="color: red;">Hello</div>

<!-- 剥离后 -->
<link rel="stylesheet" href="/css/print.css" media="print">
<div>Hello</div>
```

#### 步骤 4：验证结果

- 打开页面，确认无任何样式生效
- 检查 HTML 语义结构是否完整（标题、段落、列表等）
- 确认打印样式仍可用

#### 步骤 5：恢复样式

日期过后（4月10日 00:00），恢复所有被移除的样式引用。

### 输出规范

| 输出项 | 格式 | 示例 |
|--------|------|------|
| 剥离报告 | Markdown 表格 | 列出每个文件的操作类型 |
| 恢复脚本 | Shell 脚本 | 自动恢复所有样式引用 |
| 验证清单 | 勾选列表 | 确认无样式、语义完整、打印可用 |

---

## 四、置信度门控

当遇到以下情况时，输出 `[需核实:字段]` 占位符，不编造信息：

| 场景 | 占位符示例 |
|------|------------|
| 不确定日期是否匹配 | `[需核实:当前日期是否为4月9日]` |
| 无法识别 CSS 文件路径 | `[需核实:样式文件路径]` |
| 动态样式注入逻辑不明 | `[需核实:JS样式注入方式]` |
| 第三方组件样式来源未知 | `[需核实:组件样式来源]` |

---

## 五、错误码体系

| 错误码 | 错误描述 | 提示话术 | 修正步骤 |
|--------|----------|----------|----------|
| `E001` | 找不到 CSS 文件 | "未检测到样式文件，请确认项目结构" | 检查 `link` 标签路径是否正确 |
| `E002` | 日期不匹配 | "今天不是 CSS Naked Day，确认是否继续？" | 确认日期或手动指定执行 |
| `E003` | 文件权限不足 | "无法修改文件，请检查读写权限" | 使用 `chmod` 调整权限 |
| `E004` | 恢复失败 | "样式恢复失败，请手动检查" | 从备份恢复或重新执行恢复脚本 |
| `E005` | 白名单冲突 | "打印样式被误删，请检查白名单配置" | 重新配置 `media="print"` 保护 |

---

## 六、FAQ 反模式

### 常见坑 1：忘记恢复
**反模式**：剥离后不设置自动恢复机制，导致网站长期无样式。
**正确做法**：使用 cron 定时任务或 CI 流程，在 4 月 10 日自动恢复。

### 常见坑 2：误删打印样式
**反模式**：一刀切删除所有样式，导致打印功能失效。
**正确做法**：白名单保护 `media="print"` 的样式表。

### 常见坑 3：忽略 JS 动态样式
**反模式**：只处理静态 CSS，忽略 JS 注入的样式。
**正确做法**：检查 JS 文件中的 `style` 操作，手动添加处理逻辑。

### 常见坑 4：未备份原始文件
**反模式**：直接修改文件，无备份，恢复困难。
**正确做法**：操作前先 `cp -r` 备份或使用 Git 提交。

### 常见坑 5：剥离后不验证
**反模式**：剥离后直接上线，不检查页面是否正常。
**正确做法**：至少抽查 3 个页面，确认 HTML 语义完整。

---

## 七、渐进式披露

### 速查卡（30 秒上手）

```
1. 备份 → cp -r project project-backup
2. 扫描 → find . -name "*.css"
3. 剥离 → 移除 link/style 标签
4. 验证 → 打开页面确认无样式
5. 恢复 → 4月10日自动恢复
```

### 新手路径（首次使用）

1. 阅读「能力边界」了解适用范围
2. 按「标准流程」步骤 1-2 执行扫描
3. 在测试环境试运行，观察效果
4. 确认无误后应用到生产环境

### 进阶路径（深度定制）

1. 配置白名单规则，保护关键样式
2. 编写自定义恢复脚本，支持多环境
3. 集成 CI/CD 流程，实现自动化
4. 添加监控告警，剥离期间异常通知

---

## 八、用户协议

使用本 Skill 即表示您同意以下条款：

1. **责任承担**：使用者自行承担全部责任。因使用本 Skill 导致的任何直接或间接损失（包括但不限于数据丢失、服务中断、业务受损），Skill 作者及 AI 生成方不承担任何责任。
2. **禁止反向工程**：不得对本 Skill 的底层逻辑进行反向工程、反编译、破解或试图提取源代码（除非适用法律允许）。
3. **合规使用**：使用者应确保其使用场景符合当地法律法规及平台政策。
4. **无担保声明**：本 Skill 按"现状"提供，不附带任何明示或暗示的担保。

<!-- user-agreement-injected -->

---

## 九、许可证（License）

本 Skill 采用 MIT 许可证发布。

### MIT License

```
MIT License

Copyright (c) 2024 StyleShed

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

*本 Skill 由 AI 辅助生成，仅供参考。使用前请结合自身项目情况评估适用性。*
