---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: agent-browser-workspace
name: agent-browser-workspace
displayName: 浏览器自动化 深度调研 数据采集
description: 本地浏览器工具包，支持深度调研与浏览器自动化操作。
version: 1.0.2
rules_version: cpr-20260811-n351
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/agent-browser-workspace
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: FlowForge Studio
agent_created: true
trigger_words: ["浏览器自动化", "深度调研", "网页数据采集", "CDP", "Playwright", "网页抓取", "自动化测试"]
---

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->


> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# agent-browser-workspace 技能文档

## 一、能力边界（一页纸速查卡）

### 1.1 能做什么

| 能力项 | 说明 | 典型场景 |
|--------|------|----------|
| 浏览器自动化 | 通过 Playwright 驱动 Chromium/Firefox/WebKit 执行点击、填表、导航、截图等操作 | 表单批量提交、UI 回归检查 |
| 深度调研 | 多页面跳转、滚动加载、内容聚合，支持自定义抓取逻辑 | 竞品价格跟踪、行业新闻汇总 |
| 网页数据采集 | 提取结构化数据（表格、列表、JSON-LD），输出为 CSV/JSON | 商品信息采集、公开数据整理 |
| CDP 协议支持 | 通过 Chrome DevTools Protocol 进行底层控制（网络拦截、性能追踪） | 性能分析、请求拦截调试 |

### 1.2 不能做什么（明确边界）

- 不能绕过登录验证、验证码识别或任何反爬机制。
- 不能对目标网站发起高频请求（建议请求间隔 ≥ 2 秒）。
- 不能处理需要图形验证码或短信验证的流程。
- 不能保证目标网站 DOM 结构不变，脚本需具备基础容错。
- 不提供分布式抓取或代理池管理能力。

### 1.3 适用对象

- 需要快速实现浏览器自动化的开发者。
- 需要定期采集公开网页数据的分析师。
- 需要验证自身网站交互流程的测试人员。

---

## 二、触发方式

### 2.1 触发词

`浏览器自动化`、`深度调研`、`网页数据采集`、`CDP`、`Playwright`、`网页抓取`、`自动化测试`

### 2.2 场景映射表

| 用户说（大白话） | 触发动作 | 实际执行 |
|------------------|----------|----------|
| "帮我自动打开网页并截图" | 浏览器自动化 | 启动浏览器 → 导航 → 截图 → 保存 |
| "把那个网站上的新闻标题都抓下来" | 网页数据采集 | 遍历列表页 → 提取标题 → 输出 CSV |
| "调研一下竞品的定价策略" | 深度调研 | 多页面访问 → 收集价格 → 汇总对比表 |
| "用 CDP 拦截一下这个页面的网络请求" | CDP 协议 | 开启网络监听 → 记录请求 → 输出日志 |

---

## 三、标准流程

### 3.1 前置条件

| 条件 | 要求 | 验证方式 |
|------|------|----------|
| Python 环境 | ≥ 3.9 | `python --version` |
| Playwright 安装 | `pip install playwright && playwright install chromium` | `python -c "from playwright.sync_api import sync_playwright"` |
| 目标网站可达 | 网络连通，无防火墙拦截 | `curl -I https://example.com` |
| 存储目录 | 当前目录可写，用于存放输出文件 | `touch .write_test && rm .write_test` |

### 3.2 执行步骤

1. **参数解析**：读取输入参数（目标 URL、操作类型、输出格式），若缺失则交互式询问。
2. **环境自检**：检查 Playwright 是否可用，浏览器是否已安装，失败则提示安装命令。
3. **任务分发**：根据操作类型（`automate` / `research` / `scrape` / `cdp`）调用对应执行模块。
4. **执行核心逻辑**：
   - 启动浏览器实例（headless 默认开启，可配置关闭）。
   - 执行导航、等待、交互、提取等操作。
   - 捕获异常并记录日志。
5. **结果输出**：将结果写入指定文件（默认 `output/` 目录），并在终端打印摘要。
6. **收尾清理**：关闭浏览器进程，释放资源。

### 3.3 输出规范

| 输出类型 | 格式 | 示例 |
|----------|------|------|
| 数据采集 | CSV / JSON | `output/scrape_result_20260811.csv` |
| 截图 | PNG | `output/screenshot_20260811.png` |
| 调研报告 | Markdown | `output/research_report.md` |
| 操作日志 | 文本 | `output/execution.log` |

---

## 四、置信度门控

当遇到以下情况时，**不得编造数据**，必须输出 `[需核实:字段]` 占位符：

| 场景 | 占位符示例 | 后续建议 |
|------|------------|----------|
| 页面元素未找到 | `[需核实:商品价格]` | 检查选择器或等待策略 |
| 网络请求超时 | `[需核实:响应时间]` | 重试或延长超时时间 |
| 数据格式异常 | `[需核实:日期字段]` | 确认源站格式并调整解析逻辑 |
| 目标页面结构变化 | `[需核实:页面结构]` | 更新抓取规则 |

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| `E001` | 浏览器启动失败 | 浏览器未安装或路径错误 | 执行 `playwright install chromium` |
| `E002` | 页面导航超时 | 目标网站响应超时 | 检查网络，或增加 `timeout` 参数 |
| `E003` | 元素定位失败 | 未找到指定元素 | 检查选择器，或使用 `wait_for_selector` |
| `E004` | 数据提取为空 | 提取结果为空列表 | 确认页面是否加载完成，或调整解析逻辑 |
| `E005` | 输出目录不可写 | 无法创建输出文件 | 检查目录权限，或指定其他输出路径 |
| `E006` | CDP 连接失败 | 无法建立调试连接 | 确认浏览器以 `--remote-debugging-port` 启动 |

---

## 六、FAQ 反模式

### 6.1 常见坑

| 坑 | 反模式（错误做法） | 正模式（推荐做法） |
|----|--------------------|--------------------|
| 等待策略 | 固定 `time.sleep(5)` | 使用 `page.wait_for_selector()` 或 `page.wait_for_load_state()` |
| 选择器编写 | 使用绝对 XPath（易碎） | 优先使用 `data-testid` 或相对 CSS 选择器 |
| 异常处理 | 裸 `try-except` 吞掉异常 | 捕获后记录日志并输出错误码 |
| 资源清理 | 忘记关闭浏览器 | 使用 `with sync_playwright() as p:` 上下文管理器 |
| 数据去重 | 重复抓取相同内容 | 维护已抓取 URL 集合，实现去重 |

### 6.2 反模式对照

- **反模式**：抓取失败后静默跳过 → **正模式**：记录失败原因并输出 `[需核实]` 占位。
- **反模式**：对所有网站使用同一套超时设置 → **正模式**：根据目标网站响应速度动态调整。
- **反模式**：将抓取数据直接覆盖原文件 → **正模式**：按时间戳生成新文件，保留历史记录。

---

## 七、渐进式披露

### 7.1 速查卡（30 秒上手）

```bash
# 安装依赖
pip install playwright
playwright install chromium

# 运行示例（抓取标题）
python main.py --url https://example.com --action scrape --output result.json
```

### 7.2 新手路径（首次使用）

1. 阅读本速查卡，确认环境就绪。
2. 使用 `--selftest` 验证安装是否成功。
3. 从简单的 `scrape` 操作开始，熟悉输出格式。
4. 逐步尝试 `automate` 和 `research` 操作。

### 7.3 进阶路径（深度使用）

1. 学习 CDP 协议，掌握网络拦截与性能分析。
2. 自定义抓取规则，处理复杂页面结构。
3. 结合调度工具（如 cron）实现定时采集。
4. 为不同网站编写专用解析模块，提升鲁棒性。

---

## 八、参数参考表

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `--url` | str | 必填 | 目标网页地址 |
| `--action` | str | `scrape` | 操作类型：`automate` / `research` / `scrape` / `cdp` |
| `--output` | str | `output/` | 输出目录 |
| `--headless` | bool | `True` | 是否无头模式运行 |
| `--timeout` | int | `30000` | 页面加载超时（毫秒） |
| `--selftest` | flag | - | 运行自检并退出 |
| `--version` | flag | - | 显示版本号并退出 |

---

## 九、用户协议

<!-- user-agreement-injected -->

**使用前请仔细阅读以下条款，使用本 Skill 即视为同意本协议。**

1. **责任承担**：使用者应自行承担因使用本 Skill 进行浏览器自动化、网页数据采集等操作所产生的一切后果与责任。本 Skill 仅提供技术实现方案，不对使用目的、使用方式及使用结果负责。
2. **合规使用**：使用者须确保其使用行为符合相关法律法规、网站服务条款及道德规范。禁止将本 Skill 用于任何非法用途，包括但不限于未经授权的数据抓取、绕过访问控制、干扰网站正常运行等行为。
3. **禁止反向工程**：使用者不得对本 Skill 进行反向工程、反编译、破解或试图提取源代码（除非适用法律允许）。
4. **无担保声明**：本 Skill 按"原样"提供，不附带任何明示或暗示的担保，包括但不限于适销性、特定用途适用性及不侵权保证。
5. **免责条款**：因使用本 Skill 导致的任何直接、间接、偶然、特殊或后果性损害，作者及贡献者不承担任何责任。

---

## 十、许可证（License）

<!-- professional-license-embedded -->

**MIT License**

Copyright (c) 2026 原创作者（自持版权）

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

*本 Skill 由 AI 辅助生成，仅供参考。使用前请阅读相关文档，并根据实际场景进行验证与调整。*
