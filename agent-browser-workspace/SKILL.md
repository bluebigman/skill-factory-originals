---
slug: agent-browser-workspace
name: agent-browser-workspace
displayName: 浏览器自动化 网页采集 深度调研
description: 本地浏览器自动化工具包，支持网页数据采集与深度调研任务。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: FlowForge Lab
agent_created: true
trigger_words: ["浏览器自动化", "深度调研", "网页数据采集", "CDP", "Playwright", "网页爬取", "信息收集", "自动化测试"]
---

> 本内容由 AI 生成，仅供学习参考 <!-- ai-generated-notice -->

# 浏览器自动化工作台（agent-browser-workspace）

## 一、能力边界：一页纸速查卡

本工具包定位为**本地浏览器自动化执行框架**，面向需要批量获取网页信息、模拟用户操作、完成多步骤调研流程的技术人员。

| 维度 | 能做 | 不能做 |
|------|------|--------|
| 页面操作 | 点击、输入、滚动、悬停、键盘事件、文件上传 | 绕过验证码、破解登录限制、篡改页面逻辑 |
| 数据采集 | 提取 DOM 文本、属性、表格、列表、JSON-LD 结构化数据 | 获取加密流量内容、解密 DRM 保护资源 |
| 流程编排 | 多页面串联、条件分支、循环翻页、等待策略 | 跨域数据共享（受浏览器同源策略约束） |
| 调试辅助 | 监听 console 日志、网络请求、截图、录制视频 | 修改服务器端响应、伪造 TLS 证书 |
| 运行环境 | 本地 Node.js + Playwright，支持无头/有头模式 | 云端分布式执行、集群调度（需自行扩展） |

**适用对象**：数据分析师、调研专员、测试工程师、自动化脚本开发者。

**不适用场景**：需要长期稳定运行的线上爬虫服务（建议使用专业采集框架）、需要绕过访问控制的任何操作。

---

## 二、触发方式与场景映射

当你的任务描述中出现以下关键词时，本 Skill 将被激活：

| 触发词 | 典型场景描述 | 本工具包提供的价值 |
|--------|-------------|-------------------|
| 浏览器自动化 | "帮我自动登录后台导出报表" | 提供 Playwright 脚本模板与交互方法速查 |
| 深度调研 | "调研竞品定价策略并汇总成表" | 多页面遍历 + 结构化数据提取 + 结果导出 |
| 网页数据采集 | "抓取这个列表页的所有商品信息" | 选择器定位 + 分页处理 + JSON 输出 |
| CDP | "通过调试协议控制浏览器" | 底层协议封装与调用示例 |
| Playwright | "写一个自动化测试脚本" | 完整 API 参考与最佳实践 |

---

## 三、标准操作流程

### 3.1 前置条件

| 项目 | 要求 | 验证命令 |
|------|------|----------|
| Node.js | ≥ 18.0.0 | `node -v` |
| Playwright | ≥ 1.40.0 | `npm list playwright` |
| 浏览器内核 | Chromium/Firefox/WebKit 任一 | `npx playwright install chromium` |

首次使用请执行自检命令确认环境就绪：

```bash
npx agent-browser-workspace --selftest
```

预期输出：`✅ 环境检查通过 | Playwright x.x.x | Chromium 已安装`

### 3.2 快速上手模板

以下脚本完成「打开页面 → 等待元素 → 提取数据 → 输出 JSON」的最小闭环：

```javascript
const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  
  // 1. 目标 URL（替换为实际地址）
  await page.goto('https://example.com', { waitUntil: 'networkidle' });
  
  // 2. 等待关键元素出现（替换为实际选择器）
  await page.waitForSelector('.product-item', { timeout: 10000 });
  
  // 3. 提取数据
  const items = await page.$$eval('.product-item', els => 
    els.map(el => ({
      title: el.querySelector('.title')?.textContent?.trim() || '',
      price: el.querySelector('.price')?.textContent?.trim() || ''
    }))
  );
  
  // 4. 输出 JSON
  console.log(JSON.stringify({ count: items.length, items }, null, 2));
  
  await browser.close();
})();
```

### 3.3 进阶调研流程

多步骤调研脚本的标准骨架：

```
步骤 1：初始化浏览器实例（配置视口、UA、代理）
步骤 2：登录流程（fill 表单 → click 提交 → waitForNavigation）
步骤 3：搜索/筛选（输入关键词 → 选择排序方式）
步骤 4：翻页遍历（循环点击「下一页」直到禁用态）
步骤 5：数据清洗（去重、格式规范化、字段映射）
步骤 6：结果持久化（写入 SQLite / 导出 CSV）
```

### 3.4 输出规范

所有脚本统一输出 JSON 格式，结构如下：

```json
{
  "status": "success" | "partial" | "failed",
  "timestamp": "2024-01-15T10:30:00Z",
  "total": 42,
  "data": [ ... ],
  "warnings": ["第 3 页元素未加载，已跳过"]
}
```

---

## 四、置信度门控

当遇到以下情况时，**不得编造数据**，必须输出占位符 `[需核实:字段名]`：

| 场景 | 处理方式 |
|------|----------|
| 元素未找到 | 记录 `[需核实:该元素选择器]`，继续后续流程 |
| 数据格式异常 | 标记 `[需核实:字段格式]`，保留原始值 |
| 页面跳转超时 | 重试 2 次，仍失败则标记 `[需核实:页面状态]` |
| 登录态失效 | 中断流程，输出 `[需核实:会话有效性]` |

示例输出：

```json
{
  "items": [
    { "title": "商品A", "price": "[需核实:价格字段]" }
  ]
}
```

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| `E1001` | 浏览器启动失败 | "无法启动浏览器实例，请检查安装" | 运行 `npx playwright install` 重新安装内核 |
| `E1002` | 页面导航超时 | "页面加载超过 30 秒，已终止" | 检查网络；改用 `waitUntil: 'domcontentloaded'` |
| `E2001` | 选择器未匹配 | "未找到目标元素，请确认选择器" | 使用 DevTools 复制精确选择器；增加等待时间 |
| `E2002` | 数据提取为空 | "提取到 0 条记录，可能结构已变更" | 打印页面 HTML 片段辅助定位 |
| `E3001` | 脚本执行异常 | "JavaScript 执行出错" | 查看 `page.on('pageerror')` 监听日志 |
| `E4001` | 输出写入失败 | "无法写入目标文件" | 检查路径权限；确认磁盘空间 |

---

## 六、常见陷阱与反模式对照

| 反模式 | 问题描述 | 推荐做法 |
|--------|----------|----------|
| 固定等待 `sleep(5000)` | 网络波动时不稳定，过慢或过早 | 使用 `waitForSelector` / `waitForResponse` 条件等待 |
| 忽略弹窗处理 | 页面出现弹窗导致后续操作失败 | 注册 `page.on('dialog', d => d.accept())` 统一处理 |
| 单页硬编码 | 翻页逻辑写死，页面结构变化即失效 | 抽象分页函数，检测「下一页」按钮的 disabled 属性 |
| 不关闭浏览器 | 进程残留导致内存泄漏 | 使用 `try/finally` 或 `browser.close()` 兜底 |
| 无日志输出 | 出错后难以定位问题 | 关键步骤添加 `console.log` 或写入日志文件 |

---

## 七、渐进式学习路径

### 新手路径（15 分钟上手）

1. 阅读「一、能力边界」确认工具定位
2. 执行 `--selftest` 验证环境
3. 复制「3.2 快速上手模板」，替换 URL 和选择器
4. 运行脚本，观察 JSON 输出

### 进阶路径（1-2 小时精通）

1. 学习 Playwright 核心交互方法：`click`、`fill`、`selectOption`、`keyboard`
2. 掌握等待策略：`waitForSelector`、`waitForFunction`、`waitForTimeout`
3. 编写多步骤调研脚本（登录 → 搜索 → 翻页 → 采集）
4. 使用 `page.on('console')` 监听页面日志辅助调试
5. 将采集结果写入数据库或导出为 CSV

### 专家路径（按需深入）

- 自定义浏览器上下文（代理、UA、Cookie 注入）
- 并行采集（多浏览器实例 / 多页面并发）
- 断点续采（记录已采集索引，失败后恢复）
- 与 CI/CD 集成（定时触发、结果通知）

---

## 八、用户协议

**使用本 Skill 即表示您同意以下条款：**

1. **责任承担**：使用者应自行承担因使用本技能产生的一切后果与责任。本技能仅提供技术实现手段，不对使用目的、使用方式及使用结果负责。
2. **合法用途**：本技能仅限用于合法目的。禁止将本技能用于侵犯他人隐私、窃取商业机密、破坏计算机系统、绕过访问控制等非法活动。
3. **禁止反向工程**：使用者不得对本技能进行反向工程、反编译、破解或试图提取源代码（除非适用法律允许）。
4. **无担保声明**：本技能按"原样"提供，不附带任何明示或暗示的担保，包括但不限于适销性、特定用途适用性及不侵权保证。
5. **免责条款**：因使用本技能导致的任何直接、间接、偶然、特殊或后果性损害，作者及贡献者不承担任何责任。

<!-- user-agreement-injected -->

---

## 九、许可证（License）

本技能采用 MIT 许可证授权：

```
MIT License

Copyright (c) 2024 FlowForge Lab

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

*本 Skill 由 AI 辅助生成，仅供参考。使用前请阅读相关文档并自行验证适用性。*
