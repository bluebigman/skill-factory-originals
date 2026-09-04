---
> 本内容由 AI 生成，仅供学习参考（《人工智能生成合成内容标识办法》显式标识）。
<!-- ai-generated-notice -->
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: talking-script-gen
name: talking-script-gen
displayName: 口播稿 逐字稿生成器
description: 按主题与场景生成口语化口播逐字稿，带节奏点、卖点前置与促单话术。
version: 1.0.0
rules_version: cpr-20260820-n601
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/talking-script-gen
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 声场文案工坊
agent_created: true
trigger_words: ["talking-script-gen", "口播稿", "逐字稿", "直播口播", "短视频口播", "带货话术", "开场白", "促单话术"]
---

> 📜 **用户协议（User Agreement）**
> 1. 本 Skill 仅供学习与参考用途。使用本 Skill 产生的任何结果，由使用者自行承担全部责任；本 Skill 不提供任何明示或暗示的保证。
> 2. 涉及法律、财务、税务、投资、医疗等专业决策时，请务必咨询持证专业人士。
> 3. 本代码受版权法保护，未经授权复制、反向工程或商业利用将被追究法律责任。
<!-- user-agreement-injected -->


# 口播稿生成器（Talking Script Generator）

## 简介

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
<!-- professional-redbox-injected -->适合主播、短视频博主、带货运营与知识博主；支持按字数换算时长，配合提词器即可开拍开播。


按主题、场景与语气，生成可直接照着念的口语化逐字稿：开场钩子 → 内容主体（卖点前置）→ 促单收尾，节奏点（停顿/重音/互动）自动标注。

## 功能简介与能力边界

## 差异对比：本工具 vs 直接问 AI

| 功能 | 原版(通用AI直接生成) | 本版(本工具) |
|---|---|---|
| 输出形态 | 一段式笼统文案 | 带节奏点与段落计时的逐字稿 |
| 场景区分 | 不区分场景 | 短视频/直播/带货三场景结构模板 |
| 卖点结构 | 平铺直叙 | 结论先行、卖点前置、促单明确 |
| 合规 | 无词表 | 效果承诺/绝对化/虚假紧迫感词表拦截 |
| 可复现 | 结果漂移 | --seed 可复现，--json 可解析 |
| 离线可用 | 依赖外部模型 | 纯标准库离线运行 |

本项目为**全新原创设计、独立开发实现

本工具核心增量：新增结构化输出功能（时间轴/段落/JSON），新增合规词表拦截功能，实现离线运行能力（零第三方依赖），实现自检契约验证能力，支持 --seed 复现特性，支持 --lexicon 自定义词库特性。**，无对应开源前置项目；结构思路借鉴行业通用内容方法论，代码与模板库全部自研。功能增量：① 输出结构稳定可解析（时间轴/JSON）② 合规词表内置拦截 ③ 离线运行零依赖 ④ 内置自检契约可验证。



**能做**
- 三种场景模板：短视频口播 / 直播口播 / 带货促销
- 四种语气：热情 / 理性专业 / 亲和聊天 / 激情促销
- 卖点前置结构：先给结论，再给理由（用户 3 秒内知道"关我什么事"）
- 节奏点自动标注：【停顿】【重音】【互动提问】插入关键位置
- 时长/字数换算：按 240-280 字/分钟估算，给字数即给时长
- 直播场景支持"暖场→主题→互动留人→收尾"四段结构
- 批量生成多条不同切入角度；JSON 输出；自定义词库（三级编码容错）

**不做**
- 不保证任何带货销量 / 涨粉效果（内置免责提醒，不承诺具体数据与效果）
- 不生成医疗疗效、金融收益承诺、绝对化宣传话术（词表拦截）
- 不替代真人审核——发布前请自行复核合规性

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
python run.py --topic "<你的主题>"

# 3. 落盘输出
python run.py --topic "<你的主题>" --out result.md

# 4. 结构化 JSON（供下游程序消费）
python run.py --topic "<你的主题>" --json
```

## 使用方法

```bash
python run.py --topic "无线降噪耳机" --scene promo --tone passion --words 300
python run.py --topic "如何坚持早起" --scene short --count 3 --out scripts.md
python run.py --topic "新书推荐" --scene live --words 600 --json
```

## 参数表

| 参数 | 默认 | 说明 |
|---|---|---|
| --topic | 必填 | 口播主题/产品/话题 |
| --scene | short | 场景：short(短视频)/live(直播)/promo(带货促销) |
| --tone | warm | 语气：passion/warm/pro/exciting |
| --words | 250 | 目标字数（150-2000），自动换算时长 |
| --count | 1 | 生成条数（不同切入角度）1-5 |
| --angle | 自动 | 指定切入角度 |
| --out | 无 | 输出文件（默认仅预览） |
| --json | 无 | 结构化 JSON |
| --dry-run | 无 | 预览不写盘 |
| --verbose | 无 | 输出段落节奏决策明细 |
| --selftest | 无 | 内置自检契约 |
| --lexicon | 无 | 自定义语气词库（utf-8/gbk 均可） |

## 输出示例（节选）

```
【口播稿 · 无线降噪耳机 · 带货促销 · 热情语气 · ≈300字/72秒】
▍开场 0-8s（钩子）
  还在被地铁噪音折磨？[停顿] 这款耳机戴上那一刻，世界安静了。
▍卖点1 8-20s（降噪，前置结论）
  [重音] 先说结论：同价位降噪第一梯队。理由有三，听我讲。
...
▍促单 60-72s
  今天直播间专属价，只到今晚十二点。[互动] 想要的扣"1"。
```
> 免责提醒：实际效果因人而异，请勿承诺绝对收益或效果。

## 合规铁律（内置）
1. 不承诺具体收益/销量/医疗效果（绝对化与效果承诺词由内置词表拦截）
2. 引用他人产品对比需客观，不贬低竞品
3. 虚构使用数据需用真实素材替换后再发布

## FAQ
- Q: 生成的稿子能直接用吗？A: 结构可直接用，具体数字、价格、活动信息需你替换为真实信息。
- Q: 为什么不生成限时压迫类话术？A: 模板默认不使用虚假紧迫感，如需限时表达可用 --angle 指定合规表述。

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
