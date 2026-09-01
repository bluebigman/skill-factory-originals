---
slug: house-purchase-plan
name: house-purchase-plan
displayName: 购房测算 月供评估 预算规划
description: 输入收入与房价，输出月供、税费、现金流压力与购房建议。
version: 2.0.0
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/house-purchase-plan
copyright_holder: 居安测算工坊
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 居安测算工坊
agent_created: true
trigger_words: ["house-purchase-plan", "买房测算", "月供计算", "购房预算", "房贷方案对比", "置业评估", "按揭压力测试"]
---

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->


> 📜 **用户协议（User Agreement）**
> 1. 本 Skill 仅供学习与参考用途。使用本 Skill 产生的任何结果，由使用者自行承担全部责任；本 Skill 不提供任何明示或暗示的保证。
> 2. 涉及法律、财务、税务、投资、医疗等专业决策时，请务必咨询持证专业人士。
> 3. 本代码受版权法保护，未经授权复制、反向工程或商业利用将被追究法律责任。
<!-- user-agreement-injected -->


# 购房测算 Skill（house-purchase-plan）

**一句话定位**：输入家庭月收入与目标房价，输出月供、税费、现金流压力与购房建议，帮助首次购房者与改善型买家在 30 秒内完成置业可行性评估。

## 快速开始 Quick Start

| 场景 | 命令 | 预期结果 |
|------|------|----------|
| 最小可用路径 | `python run.py --price 3000000 --income 25000` | 输出月供、税费、DTI 压力与购房建议 |
| 多方案对比 | `python run.py --price 3000000 --income 25000 --down-payment-ratio 0.3 --down-payment-ratio 0.5` | 输出两种首付方案对比表 |
| 自检 | `python run.py --selftest` | 退出码 0，全部断言通过 |

## 适用场景 When to Use

**什么时候用**：
- 首次购房的工薪家庭，需要快速评估月供承受力
- 考虑换房的改善型买家，比较不同首付比例方案
- 需要对比等额本息与等额本金还款方式的差异
- 房产中介或金融顾问的初步测算辅助

**什么时候不要用**：
- 涉及产权纠纷、合同条款解释等法律问题（请咨询律师）
- 需要投资回报预测、房价涨跌判断（本工具不预测市场）
- 非住宅类房产（商铺、写字楼、厂房）
- 公积金贷款与商业贷款组合的精确计算（本工具仅支持单一利率）

## 能力总览 Capabilities

| 能力 | 命令/参数 | 示例 |
|------|-----------|------|
| 月供估算（等额本息/等额本金） | `--method equal_installment / equal_principal` | `--method equal_principal` |
| 税费概算（契税/中介费/维修基金等） | 自动计算 | 无需额外参数 |
| 现金流压力评估（DTI） | `--income` | `--income 25000` |
| 购房建议生成 | 自动生成 | 无需额外参数 |
| 多方案对比 | 多次传 `--down-payment-ratio` | `--down-payment-ratio 0.3 --down-payment-ratio 0.5` |
| 实时 LPR 获取 | `--fetch-lpr` | `--fetch-lpr` |
| 输出 JSON | `--output-json result.json` | `--output-json result.json` |
| 试运行（不写盘） | `--dry-run` | `--dry-run --output-json result.json` |
| 详细模式 | `--verbose` | `--verbose` |

## 模块决策表 Decision Table

| 用户意图 | 模块/命令 | 读取指引 |
|----------|-----------|----------|
| 快速评估月供 | `calculate_monthly_payment()` | 查看「核心计算函数」章节 |
| 了解税费构成 | `calculate_taxes()` | 查看「税费计算」章节 |
| 判断是否买得起 | `evaluate_cashflow()` | 查看「现金流评估」章节 |
| 获取最新 LPR | `fetch_lpr()` | 查看「LPR 获取」章节 |
| 多方案对比 | `compare_scenarios()` | 查看「方案对比」章节 |

## 示例 Examples

### 示例 1：基础月供计算

```bash
python run.py --price 3000000 --income 25000
```

输出摘要：
```text
=== 购房测算结果 ===
房价: 3,000,000 元
首付 (30%): 900,000 元
贷款金额: 2,100,000 元
贷款年限: 30 年
年利率: 4.15% (LPR 3.85% + 30BP)

月供 (等额本息): 10,204 元
总利息: 1,573,440 元
税费合计: 约 78,000 元
DTI: 40.8% (安全)
建议: 可考虑购买，月供占收入比在安全范围内。
```

### 示例 2：多方案对比

```bash
python run.py --price 3000000 --income 25000 --down-payment-ratio 0.3 --down-payment-ratio 0.5
```

输出摘要：
```text
=== 方案对比 ===
方案1 (首付30%): 月供 10,204 元, DTI 40.8%
方案2 (首付50%): 月供 7,289 元, DTI 29.2%
建议: 方案2 更稳健，月供压力更小。
```

### 示例 3：等额本金计算

```bash
python run.py --price 2000000 --income 20000 --method equal_principal
```

输出摘要：
```text
=== 购房测算结果 ===
月供 (等额本金): 首月 13,472 元, 逐月递减
总利息: 1,284,750 元
DTI: 67.4% (警告)
建议: 首月月供压力较大，建议考虑等额本息或提高首付比例。
```

## 安装与配置 Installation

### 依赖

- Python 3.9+
- 无第三方依赖（仅使用标准库）

### 环境变量

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `HOUSE_PLAN_LPR` | 手动指定 LPR 值（%），优先级高于 API | 无 |
| `HOUSE_PLAN_LPR_CACHE` | 自定义 LPR 缓存文件路径 | 系统临时目录 |

### LPR 获取说明

- 默认使用中国外汇交易中心官网 API（`https://www.chinamoney.com.cn/r/cms/www/chinamoney/data/rate/benchmark.json`）
- 带超时（5 秒）与指数退避重试（最多 3 次）
- 24 小时本地缓存，避免频繁请求
- 网络不可用时自动降级为默认值 3.85%，并输出警告

## 常见问题 Troubleshooting

| 错误现象 | 原因 | 解决办法 |
|----------|------|----------|
| `E2001: LPR API请求失败` | 网络不可用或 API 变更 | 检查网络连接；设置 `HOUSE_PLAN_LPR` 环境变量手动指定 |
| `E1001: 房价必须为正数` | 输入了负数或零 | 检查 `--price` 参数，确保为正数 |
| `E1006: 基点必须在-100到200之间` | 基点超出合理范围 | 检查 `--bp` 参数，确保在 -100 到 200 之间 |
| 输出乱码 | 终端编码不兼容 | 设置 `PYTHONIOENCODING=utf-8` 环境变量 |
| 写入文件失败 | 路径无权限或磁盘满 | 检查输出路径权限；使用 `--dry-run` 先试运行 |

## 最佳实践 Best Practices

### 使用技巧

1. **先试运行再写盘**：使用 `--dry-run` 预览输出，确认无误后再正式执行
2. **多方案对比**：通过多次传 `--down-payment-ratio` 比较不同首付方案
3. **实时 LPR**：每月 LPR 公布后使用 `--fetch-lpr` 获取最新利率
4. **详细模式**：使用 `--verbose` 查看每个计算步骤的明细

### 安全边界

- 本工具输出为估算值，实际贷款额度与利率以银行审批为准
- 税费计算基于常规标准，各地政策可能不同，请人工核对
- 不构成投资建议，购房决策请综合考虑个人情况

### 性能说明

- 所有计算均为 O(1) 时间复杂度，不随输入规模增长
- 支持批量方案对比，单次最多 10 个方案

## 相关资源 Related

- [中国外汇交易中心 LPR 数据](https://www.chinamoney.com.cn/)
- [中国人民银行贷款市场报价利率（LPR）公告](http://www.pbc.gov.cn/zhengcehuobisi/125207/125213/125440/3876551/index.html)
- [等额本息与等额本金还款方式详解](https://baike.baidu.com/item/%E7%AD%89%E9%A2%9D%E6%9C%AC%E6%81%AF)

---

## 附录：错误码参考

| 错误码 | 含义 | 处理建议 |
|--------|------|----------|
| E1001 | 房价必须为正数 | 检查 `--price` 参数 |
| E1002 | 收入必须为正数 | 检查 `--income` 参数 |
| E1003 | 首付比例必须在 0-1 之间 | 检查 `--down-payment-ratio` 参数 |
| E1004 | 贷款年限必须在 1-30 年 | 检查 `--years` 参数 |
| E1005 | LPR 不能为负数 | 检查 `--lpr` 参数或环境变量 |
| E1006 | 基点必须在 -100 到 200 之间 | 检查 `--bp` 参数 |
| E1007 | 还款方式非法 | 检查 `--method` 参数 |
| E2001 | LPR API 请求失败 | 检查网络连接或手动指定 LPR |
| E2002 | 输出文件写入失败 | 检查路径权限或磁盘空间 |
| E3001 | 内部计算错误 | 提交 issue 反馈 |

## 许可证（License）

```text
MIT License

Copyright (c) {year} {holder}

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
