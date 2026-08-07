---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: stonks-dashboard
name: stonks-dashboard
displayName: 终端行情 赛博监控 实时看板
description: 在终端中运行的赛博朋克风格实时金融行情监控工具，支持加密货币与股票数据可视化。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/stonks-dashboard
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: TerminalPulse Studio
agent_created: true
trigger_words: ["数据可视化", "行情监控", "终端看板", "加密货币", "股票行情", "实时金融"]
---

> 📜 **用户协议（User Agreement）**
> 1. 本 Skill 仅供学习与参考用途。使用本 Skill 产生的任何结果，由使用者自行承担全部责任；本 Skill 不提供任何明示或暗示的保证。
> 2. 涉及法律、财务、税务、投资、医疗等专业决策时，请务必咨询持证专业人士。
> 3. 本代码受版权法保护，未经授权复制、反向工程或商业利用将被追究法律责任。
<!-- user-agreement-injected -->


> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# stonks-dashboard — 终端行情赛博监控看板

## 一、能力边界（一页纸速查卡）

### ✅ 能做（5 项核心能力）

| 编号 | 能力项 | 说明 |
|------|--------|------|
| 1 | 数据源接入 | 接受用户提供的 CSV/JSON 文件、API URL 或直接粘贴的行情文本，解析为结构化数据 |
| 2 | 关键信息识别 | 自动提取时间戳、交易对/股票代码、价格、成交量、涨跌幅等核心字段 |
| 3 | 格式化输出 | 按终端宽度自适应渲染为赛博朋克风格表格、Sparkline 走势图或 ASCII 色块图 |
| 4 | 置信度标注 | 对缺失字段或推断值标注 `[需核实:字段名]`，不静默填充 |
| 5 | 批量与自定义 | 支持多文件批量处理，支持 `--format` 参数切换输出样式（table / spark / raw） |

### ❌ 不能做（明确边界）

- 不提供任何投资建议或买卖信号
- 不连接真实交易所/券商 API（仅处理用户提供的数据）
- 不保证数据实时性（取决于输入源刷新频率）
- 不支持自然语言模糊查询（如"最近涨得猛的币"）
- 不存储用户数据，所有处理在内存中完成

### 🎯 适用对象

- 终端爱好者、量化交易开发者、需要快速瞥一眼行情的运维工程师
- 适合在 SSH 会话、无图形界面的服务器环境中使用


## 许可证（License）

```text
MIT License

Copyright (c) 2026 SkillForge Lab

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.
```
<!-- professional-license-embedded -->
