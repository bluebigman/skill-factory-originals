---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: bestbuy-web-scraper-gpus
name: bestbuy-web-scraper-gpus
displayName: 显卡库存监控与到货提醒
description: 监控百思买RTX 3080 Ti库存，到货即时通知，支持批量轮询与自定义间隔。
version: 1.0.1
rules_version: cpr-20260809-n251
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/bestbuy-web-scraper-gpus
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 库存哨兵工作室
agent_created: true
trigger_words: ["bestbuy-web-scraper-gpus", "显卡到货监控", "3080Ti库存查询", "百思买补货提醒", "GPU库存抓取"]

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

---

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->


# 百思买显卡库存监控 Skill 文档

## 一、能力边界速查卡

### 1.1 本 Skill 能做什么

| 序号 | 能力项 | 说明 |
|------|--------|------|
| 1 | 商品页库存抓取 | 针对百思买（Best Buy）商品详情页，提取 RTX 3080 Ti 的库存状态（有货/无货/预售） |
| 2 | 结构化输出 | 将抓取结果整理为 JSON 格式，包含商品名、SKU、价格、库存状态、抓取时间戳 |
| 3 | 到货通知 | 当库存状态从“无货”变为“有货”时，生成醒目通知文本（终端输出或写入日志文件） |
| 4 | 批量商品监控 | 支持同时监控多个商品 URL，循环轮询，间隔时间可自定义 |
| 5 | 自定义输出格式 | 支持输出为 JSON 文件、CSV 表格或纯文本摘要，便于对接其他工具 |

### 1.2 本 Skill 不能做什么

| 序号 | 限制项 | 说明 |
|------|--------|------|
| 1 | 不处理验证码 | 若百思买页面出现人机验证（CAPTCHA），本工具无法自动绕过，需人工介入 |
| 2 | 不模拟登录 | 不处理需要登录才能查看的价格或库存信息 |
| 3 | 不保证实时性 | 抓取频率受限于网络延迟与目标站点响应速度，存在秒级延迟 |
| 4 | 不提供购买服务 | 仅负责监控与通知，不包含自动下单、加入购物车等操作 |
| 5 | 不处理非目标商品 | 仅针对规格中指定的 RTX 3080 Ti 相关商品页，其他显卡型号不在处理范围内 |

### 1.3 适用对象

- 需要持续关注 RTX 3080 Ti 补货情况的个人买家
- 小型代购团队或渠道商，需要批量监控多个商品链接
- 对 Scrapy 框架有一定了解，希望快速搭建库存监控脚本的开发者

---

## 二、触发方式与场景映射

### 2.1 触发词

- 主触发词：`bestbuy-web-scraper-gpus`
- 同义场景词：`显卡到货监控`、`3080Ti库存查询`、`百思买补货提醒`

### 2.2 大白话场景映射表

| 用户说（口语化表达） | 实际执行动作 |
|---------------------|-------------|
| “帮我盯着百思买上 3080Ti 有没有货” | 启动 Scrapy 爬虫，抓取指定商品页库存状态 |
| “每 10 分钟查一次，有货就喊我” | 设置轮询间隔为 600 秒，状态变化时触发通知 |
| “把结果存成表格发我” | 输出 CSV 格式文件，包含每次抓取的库存快照 |
| “这几个链接都帮我看看” | 将多个 URL 加入待抓取队列，批量执行 |
| “现在有没有货？” | 执行单次抓取，立即返回当前库存状态 |

---

## 三、标准执行流程

### 3.1 前置条件

| 条件项 | 要求 |
|--------|------|
| Python 环境 | 3.8 及以上版本 |
| Scrapy 框架 | 已安装（`pip install scrapy`） |
| 网络环境 | 可正常访问百思买网站（需海外网络或代理） |
| 目标 URL | 至少一个有效的百思买商品页链接（RTX 3080 Ti 相关） |

### 3.2 执行步骤

**第一步：确认输入**

收集用户提供的商品 URL 列表，检查格式是否合法（必须以 `https://www.bestbuy.com/site/` 开头）。若 URL 无效，返回错误码 `E1001`。

**第二步：配置抓取参数**

| 参数名 | 默认值 | 说明 |
|--------|--------|------|
| `interval` | 300 | 轮询间隔（秒），最小 60，最大 86400 |
| `output_format` | json | 输出格式：json / csv / text |
| `notify_on_change` | true | 仅在状态变化时通知，还是每次抓取都通知 |
| `max_retries` | 3 | 单次抓取失败后的重试次数 |

**第三步：执行抓取**

运行 Scrapy 爬虫，对每个 URL 执行以下操作：

1. 发送 HTTP GET 请求，携带合理的 User-Agent 头
2. 解析页面中的库存状态元素（通常位于 `div.fulfillment-add-to-cart-button` 或类似容器内）
3. 提取商品名称、SKU、价格、库存状态
4. 将结果暂存于内存中

**第四步：状态比对与通知**

- 若 `notify_on_change` 为 `true`，将本次结果与上一次结果比对：
  - 状态从“无货”变为“有货” → 输出醒目通知（`[到货提醒]` 前缀）
  - 状态无变化 → 静默记录
- 若 `notify_on_change` 为 `false`，每次抓取均输出结果

**第五步：输出与保存**

按 `output_format` 参数生成结果文件：

- `json`：输出 `inventory_snapshot.json`，包含每次抓取的完整记录
- `csv`：输出 `inventory_log.csv`，每行一条记录，字段为 `timestamp, sku, name, price, stock_status`
- `text`：终端直接打印摘要，不落盘

### 3.3 输出规范

**JSON 输出示例：**

```json
{
  "snapshot_id": "20260809_153000_001",
  "captured_at": "2026-08-09T15:30:00Z",
  "items": [
    {
      "sku": "6450982",
      "name": "NVIDIA GeForce RTX 3080 Ti 12GB GDDR6X",
      "price": 1199.99,
      "stock_status": "in_stock",
      "url": "https://www.bestbuy.com/site/6450982.p"
    }
  ]
}
```

**CSV 输出示例：**

```csv
timestamp,sku,name,price,stock_status
2026-08-09T15:30:00Z,6450982,NVIDIA GeForce RTX 3080 Ti 12GB GDDR6X,1199.99,in_stock
```

**文本输出示例：**

```
[2026-08-09 15:30:00] RTX 3080 Ti (SKU: 6450982) — 有货，价格 $1199.99
```

---

## 四、置信度门控机制

### 4.1 信息不足时的处理规则

当出现以下情况时，本 Skill 不会编造数据，而是输出占位符 `[需核实:字段名]`：

| 场景 | 输出内容 |
|------|----------|
| 页面结构变化，无法定位库存元素 | `"stock_status": "[需核实:stock_status]"` |
| 价格被隐藏（需登录） | `"price": "[需核实:price]"` |
| 商品名称解析失败 | `"name": "[需核实:name]"` |
| 页面加载超时 | 整条记录标记为 `"fetch_status": "timeout"` |

### 4.2 置信度标注

每条抓取记录附带 `confidence` 字段，取值规则：

| 置信度 | 判定条件 |
|--------|----------|
| `high` | 所有字段均成功解析，无占位符 |
| `medium` | 存在 1 个字段为占位符，或页面加载耗时超过 10 秒 |
| `low` | 存在 2 个及以上字段为占位符，或重试 3 次仍失败 |

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| `E1001` | URL 格式无效 | “您提供的链接不是有效的百思买商品页，请检查后重试。” | 确认 URL 以 `https://www.bestbuy.com/site/` 开头，且包含数字 SKU |
| `E1002` | 网络连接失败 | “无法连接到百思买服务器，请检查网络或代理设置。” | 测试网络连通性，更换代理节点后重试 |
| `E1003` | 页面解析失败 | “页面结构可能已更新，无法提取库存信息。” | 检查页面是否出现验证码，或等待 30 分钟后重试 |
| `E1004` | 参数越界 | “轮询间隔必须在 60 到 86400 秒之间。” | 调整 `interval` 参数至合法范围 |
| `E1005` | 输出格式不支持 | “仅支持 json、csv、text 三种输出格式。” | 修改 `output_format` 参数 |

---

## 六、FAQ 与反模式对照

### 6.1 常见坑

**坑 1：频繁请求导致 IP 被封**

- 反模式：将 `interval` 设为 60 秒以下，持续高频抓取
- 正确做法：保持默认 300 秒间隔，或使用代理池轮换 IP

**坑 2：忽略页面结构变化**

- 反模式：爬虫写死 CSS 选择器，页面改版后直接报错
- 正确做法：在解析层增加容错逻辑，选择器失效时自动降级为模糊匹配

**坑 3：不处理时区问题**

- 反模式：直接使用本地时间戳，导致跨时区比对混乱
- 正确做法：统一使用 UTC 时间（ISO 8601 格式）记录时间戳

**坑 4：通知信息过于频繁**

- 反模式：每次抓取都发送通知，造成信息轰炸
- 正确做法：默认开启 `notify_on_change`，仅在状态变化时提醒

**坑 5：忽略重试机制**

- 反模式：单次请求失败后直接终止整个任务
- 正确做法：设置 `max_retries=3`，采用指数退避策略（1s、2s、4s）重试

### 6.2 反模式对照表

| 反模式 | 推荐替代方案 |
|--------|-------------|
| 硬编码商品 URL 列表 | 从外部配置文件读取，便于动态增删 |
| 同步阻塞式抓取 | 使用 Scrapy 异步并发，提升吞吐量 |
| 将库存状态硬编码为布尔值 | 使用枚举（in_stock / out_of_stock / pre_order / unknown） |
| 忽略 HTTP 状态码检查 | 先检查 `response.status`，非 200 时直接标记为失败 |

---

## 七、渐进式披露阅读路径

### 7.1 新手速查卡（30 秒上手）

1. 准备一个百思买 RTX 3080 Ti 商品链接
2. 运行命令：`python monitor.py --url <商品链接> --interval 300`
3. 等待输出结果，看到 `[到货提醒]` 即表示有货
4. 结果默认保存为 `inventory_snapshot.json`

### 7.2 进阶用户指南（完整能力）

- 阅读「三、标准执行流程」了解全部参数配置
- 阅读「五、错误码体系」排查运行问题
- 阅读「六、FAQ 与反模式对照」优化抓取策略
- 可自行修改 `spider.py` 中的解析逻辑，适配其他显卡型号

---

## 八、用户协议

<!-- user-agreement-injected -->

**使用本 Skill 即表示您同意以下条款：**

1. 本 Skill 仅供学习与个人用途，使用者自行承担全部责任。
2. 使用者应遵守百思买网站的服务条款与 robots.txt 规范，不得利用本工具进行恶意抓取或高频请求。
3. 禁止对本 Skill 进行反向工程、反编译或试图提取底层源代码用于商业用途。
4. 本 Skill 不提供任何形式的明示或暗示担保，包括但不限于适销性、特定用途适用性。
5. 因使用本 Skill 产生的任何直接或间接损失，作者不承担任何责任。

---

## 九、许可证（License）

<!-- professional-license-embedded -->

**MIT License**

Copyright (c) 2026 库存哨兵工作室

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

## 十、附：最小可运行示例（main.py）

```python
#!/usr/bin/env python3
"""Best Buy RTX 3080 Ti 库存监控 - 最小示例"""

import argparse
import json
import time
from datetime import datetime, timezone

import requests
from scrapy import Selector

# 百思买商品页库存状态选择器（基于 2026 年 8 月页面结构）
STOCK_SELECTOR = "div.fulfillment-add-to-cart-button button[data-button-state]"
PRICE_SELECTOR = "div.priceView-hero-price span[aria-hidden='true']"
NAME_SELECTOR = "h1.sku-title"

def fetch_inventory(url: str) -> dict:
    """抓取单个商品页的库存信息"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    resp = requests.get(url, headers=headers, timeout=15)
    resp.raise_for_status()

    sel = Selector(text=resp.text)
    stock_btn = sel.css(STOCK_SELECTOR).get()
    price = sel.css(PRICE_SELECTOR).re_first(r"\$[\d,]+\.\d{2}")
    name = sel.css(NAME_SELECTOR).get()

    # 判定库存状态
    if stock_btn and "SOLD_OUT" in stock_btn:
        status = "out_of_stock"
    elif stock_btn and "ADD_TO_CART" in stock_btn:
        status = "in_stock"
    else:
        status = "[需核实:stock_status]"

    return {
        "name": name.strip() if name else "[需核实:name]",
        "price": price if price else "[需核实:price]",
        "stock_status": status,
        "captured_at": datetime.now(timezone.utc).isoformat(),
    }

def main():
    parser = argparse.ArgumentParser(description="Best Buy GPU 库存监控")
    parser.add_argument("--url", required=True, help="百思买商品页 URL")
    parser.add_argument("--interval", type=int, default=300, help="轮询间隔（秒）")
    parser.add_argument("--once", action="store_true", help="仅执行一次抓取")
    args = parser.parse_args()

    if args.interval < 60:
        print("错误：轮询间隔不能小于 60 秒")
        return

    while True:
        try:
            data = fetch_inventory(args.url)
            print(json.dumps(data, ensure_ascii=False, indent=2))
            if data["stock_status"] == "in_stock":
                print("[到货提醒] 目标商品已上架！")
        except Exception as exc:
            print(f"抓取失败: {exc}")

        if args.once:
            break
        time.sleep(args.interval)

if __name__ == "__main__":
    main()
```

---

*本文档由 AI 辅助生成，旨在提供清晰、可执行的使用指导。实际部署前请结合目标网站最新页面结构进行适配调整。*
