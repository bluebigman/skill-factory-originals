---
slug: bestbuy-web-scraper-gpus
name: bestbuy-web-scraper-gpus
displayName: 显卡到货监控 百思买库存提醒
description: 监控百思买显卡库存，到货即时提醒，支持批量轮询与自定义间隔。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: SkillForge Studio
agent_created: true
trigger_words: ["bestbuy-web-scraper-gpus", "显卡到货监控", "3080Ti库存查询", "百思买补货提醒", "GPU库存抓取", "显卡库存轮询", "百思买到货通知"]

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

---

# 百思买显卡库存监控 Skill 文档

## 1. 能力边界（一页纸速查卡）

### 1.1 本 Skill 能做什么

| 能力项 | 说明 |
|--------|------|
| 库存轮询 | 按设定间隔批量请求百思买显卡商品页，解析库存状态 |
| 到货提醒 | 检测到目标显卡从"无货"变为"有货"时，输出醒目提示 |
| 批量监控 | 支持在配置文件中定义多个显卡 SKU，一次运行全部监控 |
| 自定义间隔 | 轮询频率可由用户指定，默认 300 秒，最小建议 60 秒 |
| 快照导出 | 每次轮询后生成 `inventory_snapshot.json`，记录当前所有目标商品状态 |
| 自检模式 | 通过 `--selftest` 验证依赖安装与网络连通性，不发起实际监控 |

### 1.2 本 Skill 不能做什么

| 限制项 | 说明 |
|--------|------|
| 不保证实时性 | 库存数据以百思买页面实际返回为准，存在网络延迟与页面缓存 |
| 不处理购买流程 | 本工具仅监控与提醒，不自动下单、不代购、不绕过任何风控 |
| 不绕过反爬机制 | 若百思买对请求频率或来源 IP 做出限制，本工具不提供绕过方案 |
| 不保证数据绝对准确 | 页面结构变更、地区差异、登录态差异均可能导致解析失败 |
| 不支持非显卡品类 | 虽然代码可扩展，但本 Skill 的解析逻辑针对显卡商品页设计 |

### 1.3 适用对象

- 想蹲守特定显卡（如 RTX 3080 Ti）补货的个人买家
- 需要批量跟踪多款显卡库存状态的技术爱好者
- 希望将库存监控集成到自动化工作流中的开发者

---

## 2. 触发方式

### 2.1 触发词

当用户输入以下任一触发词时，本 Skill 应被激活：

- `bestbuy-web-scraper-gpus`
- `显卡到货监控`
- `3080Ti库存查询`
- `百思买补货提醒`
- `GPU库存抓取`
- `显卡库存轮询`
- `百思买到货通知`

### 2.2 场景映射表

| 用户说（大白话） | 本 Skill 实际执行 |
|------------------|-------------------|
| "帮我盯着百思买上的 3080Ti，有货了告诉我" | 创建配置 → 启动轮询 → 检测到货后输出提醒 |
| "查一下这几款显卡现在有没有货" | 执行单次抓取 → 输出当前库存快照 |
| "每 5 分钟帮我刷一次库存" | 设置轮询间隔为 300 秒 → 持续监控 |
| "监控 3 张显卡，分别给我看状态" | 配置多 SKU → 批量轮询 → 汇总输出 |
| "先测试一下工具能不能用" | 运行 `--selftest` → 输出环境检查结果 |

---

## 3. 标准流程

### 3.1 前置条件

| 条件 | 要求 |
|------|------|
| Python 版本 | 3.8 及以上 |
| 依赖包 | `requests`、`beautifulsoup4`、`lxml` |
| 网络 | 可访问百思买网站（可能需要科学上网，视用户网络环境而定） |
| 目标 SKU | 用户需提供要监控的显卡商品页 URL 或 SKU 编号 |

### 3.2 执行步骤

#### 步骤一：安装依赖

```bash
pip install requests beautifulsoup4 lxml
```

#### 步骤二：创建配置文件

在项目目录下创建 `monitor_config.json`，格式如下：

```json
{
  "interval_seconds": 300,
  "targets": [
    {
      "name": "RTX 3080 Ti Founders Edition",
      "url": "https://www.bestbuy.com/site/nvidia-geforce-rtx-3080-ti-12gb-gddr6x-graphics-card/6470917.p?skuId=6470917",
      "sku_id": "6470917"
    },
    {
      "name": "RTX 3070 Ti Gaming OC",
      "url": "https://www.bestbuy.com/site/gigabyte-geforce-rtx-3070-ti-gaming-oc-8g-graphics-card/6470918.p?skuId=6470918",
      "sku_id": "6470918"
    }
  ]
}
```

**参数说明：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `interval_seconds` | int | 否 | 轮询间隔（秒），默认 300，最小建议 60 |
| `targets` | array | 是 | 监控目标列表，至少 1 个 |
| `targets[].name` | string | 是 | 商品别名，用于输出展示 |
| `targets[].url` | string | 是 | 商品页完整 URL |
| `targets[].sku_id` | string | 是 | 百思买 SKU 编号，用于 URL 校验 |

#### 步骤三：运行监控

```bash
python monitor.py --config monitor_config.json
```

#### 步骤四：查看输出

- 控制台实时输出每次轮询结果
- 每次轮询后自动生成 `inventory_snapshot.json`，内容示例：

```json
{
  "timestamp": "2025-01-15T10:30:00Z",
  "results": [
    {
      "name": "RTX 3080 Ti Founders Edition",
      "sku_id": "6470917",
      "in_stock": false,
      "price": null,
      "status_text": "Sold Out",
      "checked_at": "2025-01-15T10:30:00Z"
    }
  ]
}
```

### 3.3 输出规范

| 输出类型 | 格式 | 说明 |
|----------|------|------|
| 控制台日志 | `[HH:MM:SS] [SKU名称] 状态：有货/无货` | 每次轮询逐条输出 |
| 到货提醒 | `⚠️ 到货提醒：{商品名} 当前可购买！` | 状态从无货变为有货时输出 |
| 快照文件 | JSON 格式，UTF-8 编码 | 覆盖写入，保留最新一次结果 |

---

## 4. 置信度门控

### 4.1 信息不足时的处理

当出现以下情况时，本 Skill 不会编造数据，而是输出 `[需核实:字段]` 占位符：

| 场景 | 输出示例 |
|------|----------|
| 页面解析失败，无法获取价格 | `"price": "[需核实:price]"` |
| 库存状态文本无法识别 | `"in_stock": "[需核实:in_stock]"` |
| 商品页返回 404 或重定向 | `"status_text": "[需核实:page_status]"` |
| 网络超时，未获取到响应 | `"status_text": "[需核实:network_timeout]"` |

### 4.2 处理原则

1. 宁可输出占位符，不猜测库存状态
2. 每次轮询独立判断，不沿用上一次结果
3. 若连续 3 次解析失败，在控制台输出警告并建议检查页面结构是否变更

---

## 5. 错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| `E001` | 配置文件不存在或格式错误 | `[错误] 无法读取配置文件，请检查路径与 JSON 格式` | 1. 确认文件路径正确；2. 用 `json.tool` 校验格式 |
| `E002` | 网络请求失败（超时/连接拒绝） | `[错误] 网络请求失败：{具体原因}` | 1. 检查网络连通性；2. 增大超时时间；3. 确认目标 URL 可访问 |
| `E003` | 页面解析失败（HTML 结构变更） | `[错误] 无法解析商品页，可能页面结构已更新` | 1. 手动打开 URL 确认页面存在；2. 检查选择器是否需要更新 |
| `E004` | 目标列表为空 | `[错误] 配置文件中未找到任何监控目标` | 1. 在 `targets` 数组中至少添加一个商品 |
| `E005` | 依赖缺失 | `[错误] 缺少依赖包：{包名}` | 1. 执行 `pip install {包名}` 安装缺失依赖 |
| `E006` | 请求频率过高被限制 | `[警告] 请求被拒绝，疑似触发频率限制` | 1. 增大 `interval_seconds`；2. 暂停 10 分钟后再试 |

---

## 6. FAQ 反模式

### 6.1 常见坑与对照

| 坑 | 反模式（错误做法） | 正模式（正确做法） |
|----|-------------------|-------------------|
| 轮询间隔过短 | 设置 `interval_seconds: 5`，导致 IP 被临时封禁 | 间隔至少 60 秒，建议 300 秒以上 |
| 忽略页面结构变更 | 页面改版后解析失败，仍反复重试 | 收到 `E003` 后手动检查页面，更新选择器 |
| 依赖未安装完整 | 只装了 `requests`，运行时报 `bs4` 缺失 | 按文档一次性安装三个依赖包 |
| 配置文件编码错误 | 使用 Windows 记事本保存为 UTF-8 BOM，JSON 解析失败 | 使用 UTF-8 无 BOM 编码保存 |
| 混淆 SKU 与 URL | 只填 URL 不填 `sku_id`，导致校验失败 | 两个字段都填写，确保一致 |

### 6.2 反模式自查清单

- [ ] 我是否设置了合理的轮询间隔（≥60 秒）？
- [ ] 我是否在配置中同时填写了 `url` 和 `sku_id`？
- [ ] 我是否在页面结构变更后及时更新了解析逻辑？
- [ ] 我是否遵守了百思买的服务条款，未进行高频请求？

---

## 7. 渐进式披露

### 7.1 速查卡（30 秒上手）

```bash
# 1. 安装依赖
pip install requests beautifulsoup4 lxml

# 2. 创建 monitor_config.json（参考上文格式）

# 3. 运行监控
python monitor.py --config monitor_config.json

# 4. 查看结果
cat inventory_snapshot.json
```

### 7.2 新手路径（首次使用）

1. 阅读第 3.2 节，创建配置文件
2. 先运行 `python monitor.py --selftest` 验证环境
3. 使用单目标配置，间隔设为 600 秒，观察 2-3 次轮询结果
4. 确认输出正常后，再添加更多目标

### 7.3 进阶路径（深度使用）

1. 将 `monitor.py` 集成到 cron 或 systemd 定时任务中
2. 修改输出逻辑，将到货提醒推送到钉钉/企业微信/Telegram（需自行扩展）
3. 增加价格变动监控，记录价格历史曲线
4. 使用代理池分散请求来源，降低被限制风险（注意遵守服务条款）

---

## 8. 用户协议

<!-- user-agreement-injected -->

**使用本 Skill 即表示您同意以下条款：**

1. **责任承担**：使用者自行承担因使用本 Skill 产生的全部责任，包括但不限于因数据不准确、请求被限制、或违反第三方网站条款所导致的任何直接或间接损失。
2. **禁止反向工程**：使用者不得对本 Skill 的代码进行反向工程、反编译、或试图提取其核心逻辑用于商业用途。
3. **合规使用**：使用者应遵守百思买网站的服务条款及相关法律法规，本 Skill 仅供个人学习与技术研究使用。
4. **无担保声明**：本 Skill 按"原样"提供，不附带任何明示或暗示的担保，包括但不限于适销性、特定用途适用性及不侵权保证。

---

## 9. 许可证（License）

<!-- professional-license-embedded -->

**MIT License**

Copyright (c) 2025 SkillForge Studio

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

## 10. 版本记录

| 版本 | 日期 | 变更说明 |
|------|------|----------|
| 1.0.0 | 2025-01-15 | 初始版本，包含基础库存监控、批量轮询、快照导出功能 |

---

*本 Skill 由 AI 辅助生成，仅供参考。使用前请阅读相关文档并自行验证功能。*
