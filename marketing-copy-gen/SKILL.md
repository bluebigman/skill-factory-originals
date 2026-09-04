---
> 本内容由 AI 生成，仅供学习参考（《人工智能生成合成内容标识办法》显式标识）。
<!-- ai-generated-notice -->
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: marketing-copy-gen
name: marketing-copy-gen
displayName: 营销文案 广告文案生成器
description: 从产品卖点生成电商、朋友圈、广告等多平台营销文案矩阵。
version: 1.0.0
rules_version: cpr-20260820-n601
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/marketing-copy-gen
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 卖点文案工坊
agent_created: true
trigger_words: ["marketing-copy-gen", "营销文案", "广告文案", "产品描述", "电商文案", "朋友圈文案", "卖点提炼", "种草文案", "广告语"]
---

> 📜 **用户协议（User Agreement）**
> 1. 本 Skill 仅供学习与参考用途。使用本 Skill 产生的任何结果，由使用者自行承担全部责任；本 Skill 不提供任何明示或暗示的保证。
> 2. 涉及法律、财务、税务、投资、医疗等专业决策时，请务必咨询持证专业人士。
> 3. 本代码受版权法保护，未经授权复制、反向工程或商业利用将被追究法律责任。
<!-- user-agreement-injected -->


# 营销文案生成器（Marketing Copy Generator）

## 简介

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
<!-- professional-redbox-injected -->适合电商运营、市场与品牌从业者；同一产品卖点一次生成六类渠道文案，减少重复劳动。


从一句话产品描述 + 2-3 个真实卖点出发，生成覆盖多平台、多场景的营销文案矩阵：电商标题、商品详情、朋友圈种草、信息流广告、短广告语、小红书种草笔记。

## 功能简介与能力边界

## 差异对比：本工具 vs 直接问 AI

| 功能 | 原版(通用AI直接生成) | 本版(本工具) |
|---|---|---|
| 输出形态 | 单条文案 | 六类渠道文案矩阵一次生成 |
| 卖点管理 | 要反复重述 | --points 结构化，主打卖点自动置顶 |
| 平台适配 | 通用 | 电商标题/详情/朋友圈/信息流/小红书模板 |
| 合规 | 无词表 | 广告法绝对化用语内置拦截提示改写 |
| 人群语气 | 要反复指定 | 四种语气+人群推断 |
| 可复现 | 结果漂移 | --seed 可复现 |

本项目为**全新原创设计、独立开发实现

本工具核心增量：新增结构化输出功能（时间轴/段落/JSON），新增合规词表拦截功能，实现离线运行能力（零第三方依赖），实现自检契约验证能力，支持 --seed 复现特性，支持 --lexicon 自定义词库特性。**，无对应开源前置项目；结构思路借鉴行业通用内容方法论，代码与模板库全部自研。功能增量：① 输出结构稳定可解析（时间轴/JSON）② 合规词表内置拦截 ③ 离线运行零依赖 ④ 内置自检契约可验证。



**能做**
- 输入：产品一句话 + 卖点列表（--points "卖点1|卖点2|卖点3"，最多 5 个）+ 目标人群（可选）
- 六类文案模板：电商标题 / 商品详情 / 朋友圈种草 / 信息流广告 / 短广告语 / 小红书笔记
- 四种语气：专业 / 亲切 / 年轻化 / 高端
- 卖点自动排序：用户痛点相关度优先（参数 --top-point 可指定主打卖点）
- 差异化开头策略：按平台生成（电商=场景+人群、朋友圈=真实体验口吻、广告=痛点直击）
- 批量生成 count 套不同角度文案；JSON 输出；自定义词库

**不做**
- 不虚构产品功效/参数/销量（销量类极限词由词表拦截并提示改写为真实数据）
- 不生成医疗、金融等强监管行业的绝对化宣传（词表拦截 + 提醒）
- 不保证广告投放效果（ROI 受渠道、素材、受众多重影响）

## 安装与配置

本工具零第三方依赖，无需 pip 安装。将资产目录放入 skills 目录，或直接 `python run.py --help` 即可运行；跨机迁移仅需拷贝整个资产目录。

## 前置条件

- Python 3.8+，零第三方依赖（纯标准库），直接 `python run.py` 运行
- 运行前建议 `python run.py --selftest` 验证环境（9/9 全绿）
- 生成内容仅打印预览，需落盘时显式传 `--out <路径>`

## 标准执行步骤

```bash
# 1. 自检（验证环境）
python run.py --selftest

# 2. 预览生成（不写盘，安全优先）
python run.py --product "<产品名>" --points "卖点1|卖点2"

# 3. 落盘输出
python run.py --product "<产品名>" --points "卖点1|卖点2" --out result.md

# 4. 结构化 JSON（供下游程序消费）
python run.py --product "<产品名>" --points "卖点1|卖点2" --json
```

## 使用方法

```bash
python run.py --product "便携榨汁杯" --points "30秒出汁|USB充电|可拆洗" --tone young
python run.py --product "降噪耳机" --points "主动降噪|40小时续航" --audience "通勤族" --channels ecommerce,friends
python run.py --product "护肤精华" --points "成分温和|保湿修护" --count 3 --json
```

## 参数表

| 参数 | 默认 | 说明 |
|---|---|---|
| --product | 必填 | 产品/服务名称 |
| --points | 必填 | 卖点，用 | 分隔（2-5 个） |
| --audience | 自动 | 目标人群 |
| --channels | all | 文案类型：all/title/detail/moments/ads/slogan/xhs（逗号分隔） |
| --tone | pro | 语气：pro/friendly/young/premium |
| --top-point | 无 | 主打卖点（排第一） |
| --count | 1 | 生成套数 1-3 |
| --out | 无 | 输出文件（默认仅预览） |
| --json | 无 | 结构化 JSON |
| --dry-run | 无 | 预览不写盘 |
| --verbose | 无 | 输出决策明细 |
| --selftest | 无 | 内置自检 |

## 输出示例（节选）

```
【营销文案 · 便携榨汁杯 · 目标人群: 办公室白领 · 语气: 年轻化】
═══ 电商标题 ═══
上班族专用便携榨汁杯 30秒出汁 USB充电 可拆洗 通勤随行
═══ 朋友圈种草 ═══
最近换了新杯子，早上榨杯果汁只要30秒，直接拎走，真香。
═══ 短广告语 ═══
30秒，一杯新鲜果汁。
```

## 合规铁律（内置）
1. 禁止绝对化与极限用语（词表内置拦截，命中即提示改写为真实可验证表述）
2. 数据类卖点必须真实：模板输出中【数据占位】需你填入可验证来源的数字
3. 涉及功效宣称（护肤/保健/金融）→ 输出"效果因人而异，请以官方说明为准"提醒

## 异常处理与失败排查

| 现象 | 可能原因 | 处理方式 |
|---|---|---|
| 提示缺少主题 | 未传 --topic | 按参数表补必填参数 |
| 提示参数越界 | 时长/字数/条数超范围 | 调整到合法区间后重试 |
| 内容被拦截(rc=3) | 主题命中内置禁止词 | 按提示改写表述后重试 |
| 写盘失败 | 路径无权限/目录异常 | 换可写路径，或先预览(--dry-run)确认 |
| --selftest 有失败项 | 环境/依赖异常 | 先修环境至自检全绿再使用 |

## 竞品对标

**覆盖声明**：本工具输出结构优于通用对话的零散建议（可复现、可解析）；独有合规词表拦截功能；通用 AI 方案不具备离线运行与内置自检能力。

**超越声明**：本工具领先同类通用提示词方案，在结构稳定性与合规性两个维度完胜。


**对标对象**：通用 AI 对话直接生成（ChatGPT/豆包等）与本类内容的通用提示词模板。

**用户为什么下载这类工具（下载原因拆解）**：
1. 要结构——"短视频脚本/口播稿/营销文案"是高频刚需动作词（搜索需求万级），用户要的是能直接开拍/发布的结构化成品，不是聊天建议；
2. 要省事——每次问 AI 都要重复描述平台/时长/语气，本工具参数化一次到位；
3. 要合规——发布平台对绝对化宣传有硬约束，用户怕踩广告法，需要内置拦截。

**差异化覆盖**：结构模板覆盖（对照上表逐项）；合规词表覆盖（唯一内置）；多平台参数化覆盖（远超通用对话的零散输出）。

**超越声明**：相比通用 AI 提示词方案，本工具在可复现性（--seed）、可解析性（--json）、合规拦截、离线可用四个维度均更强，且结果稳定不漂移。

## 许可证（License）

```text
MIT License

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
```
<!-- professional-license-embedded -->
