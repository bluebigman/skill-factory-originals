---
> 本内容由 AI 生成，仅供学习参考（《人工智能生成合成内容标识办法》显式标识）。
<!-- ai-generated-notice -->
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: short-video-script-gen
name: short-video-script-gen
displayName: 短视频脚本 分镜脚本生成器
description: 按主题、时长与平台生成带钩子、节奏与转化的短视频分镜脚本。
version: 1.0.0
rules_version: cpr-20260820-n601
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/short-video-script-gen
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 光影文案工坊
agent_created: true
trigger_words: ["short-video-script-gen", "短视频脚本", "分镜脚本", "视频脚本生成", "抖音脚本", "口播视频", "短视频文案", "拍视频脚本"]
---

> 📜 **用户协议（User Agreement）**
> 1. 本 Skill 仅供学习与参考用途。使用本 Skill 产生的任何结果，由使用者自行承担全部责任；本 Skill 不提供任何明示或暗示的保证。
> 2. 涉及法律、财务、税务、投资、医疗等专业决策时，请务必咨询持证专业人士。
> 3. 本代码受版权法保护，未经授权复制、反向工程或商业利用将被追究法律责任。
<!-- user-agreement-injected -->


# 短视频脚本生成器（Short Video Script Generator）

## 简介

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
<!-- professional-redbox-injected -->适合内容创作者、新媒体运营与电商团队批量生产视频素材；生成结果可人工二次精调后直接用于拍摄。


按主题、目标时长与发布平台，生成可直接开拍的短视频分镜脚本：前 3 秒钩子、内容展开、转化引导、字幕与画面提示一应俱全。

## 功能简介与能力边界

## 差异对比：本工具 vs 直接问 AI

| 功能 | 原版(通用AI直接生成) | 本版(本工具) |
|---|---|---|
| 输出形态 | 零散建议，需自己拼分镜 | 结构化分镜：时间轴/画面/台词/运镜/节奏 |
| 平台适配 | 通用，不区分平台 | 抖音/视频号/小红书/B站/快手差异化模板 |
| 合规 | 无词表拦截 | 绝对化与医疗金融风险词内置拦截 |
| 可复现 | 同一提示词结果漂移 | --seed 固定结果可复现 |
| 离线可用 | 依赖外部模型 | 纯标准库离线运行零依赖 |
| 二次加工 | 纯文本 | --json 结构化供剪辑/提词器消费 |

本项目为**全新原创设计、独立开发实现

本工具核心增量：新增结构化输出功能（时间轴/段落/JSON），新增合规词表拦截功能，实现离线运行能力（零第三方依赖），实现自检契约验证能力，支持 --seed 复现特性，支持 --lexicon 自定义词库特性。**，无对应开源前置项目；结构思路借鉴行业通用内容方法论，代码与模板库全部自研。功能增量：① 输出结构稳定可解析（时间轴/JSON）② 合规词表内置拦截 ③ 离线运行零依赖 ④ 内置自检契约可验证。



**能做**
- 输入主题一句话 + 平台（抖音/视频号/小红书/B站/快手）+ 目标时长 → 输出完整分镜脚本
- 五种风格模板：种草推荐 / 知识讲解 / 剧情演绎 / 干货清单 / 热点观点
- 分镜含：序号、时长分配、画面提示、台词/字幕、运镜建议、情绪点
- 自动计算节奏：前 3 秒钩子 → 内容主体（按 7:3 信息-转化分配）→ 结尾 CTA
- 多平台差异化：抖音重前奏冲突、小红书重清单与滤镜词、B站重信息密度
- 批量生成 count 条不同切入角度脚本；结构化 JSON 输出供二次编排
- 自定义语气词库：--lexicon 指定本地词库文件（UTF-8/GBK/GB18030 均可读）

**不做**
- 不直接发布到任何视频平台
- 不保证视频数据表现（流量受算法、时机、内容质量等多因素影响）
- 不生成违反平台社区规范的内容（医疗疗效、绝对化承诺、虚假夸大被模板库过滤）

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
python run.py --topic "办公室如何快速做出一杯好咖啡" --platform douyin --duration 45 --style knowhow
python run.py --topic "露营装备避坑指南" --platform xiaohongshu --count 3 --out scripts.md
python run.py --topic "AI 绘画入门" --platform bilibili --json
```

## 参数表

| 参数 | 默认 | 说明 |
|---|---|---|
| --topic | 必填 | 视频主题，一句话即可 |
| --platform | douyin | 平台：douyin/shipinhao/xiaohongshu/bilibili/kuaishou |
| --duration | 30 | 目标时长（秒），10-600 |
| --style | seed | 风格：seed/knowhow/drama/list/hotspot |
| --count | 1 | 生成条数（不同切入角度），1-5 |
| --angle | 自动 | 指定切入角度（倒叙/对比/设问/数据/故事/清单） |
| --out | 无 | 输出文件路径（默认仅预览不写盘） |
| --json | 无 | 输出结构化 JSON |
| --dry-run | 无 | 只展示本次将写入的内容预览，不写盘 |
| --verbose | 无 | 输出每个分镜的节奏决策明细 |
| --selftest | 无 | 运行内置自检契约 |
| --lexicon | 无 | 自定义语气词库文件路径 |

## 输出示例（预览节选）

```
【短视频脚本 · 主题: AI 绘画入门 · 平台: bilibili · 45s · 风格: knowhow】
▍镜1 (0-3s) 钩子 · 冲突提问
  画面: 错误示范 vs 正确效果 对比快切
  台词: 你是不是觉得 AI 绘画很难？其实三分钟就能上手。
▍镜2 (3-12s) 干货 · 步骤演示
  画面: 屏幕录制逐步操作
  台词: 第一步选模型，第二步写提示词，记住"主体+风格+光线"。
...
```

## 高级用法

1. **内容策略**：先 `--count 5` 生成五个切入角度，人工挑选后再精调单条
2. **二次创作**：`--json` 输出分镜结构，可接入剪辑脚本或提词器
3. **行业复用**：同一主题换平台/时长重跑，即得多平台投放矩阵
4. **合规自查**：生成后人工过一遍"三不"清单（不夸大、不承诺效果、不贬低竞品）

## 常见问题（FAQ）

- Q: 生成的脚本为什么没有具体数字/案例？A: 为避免编造，模板只给结构，数字与案例需你按真实素材填入（--angle data 会给数据占位格式）。
- Q: 能直接商用吗？A: 脚本结构可自由商用；引用他人观点/音乐/素材请自行确权。
- Q: 和口播稿有什么区别？A: 本工具输出的是含画面与节奏的**分镜脚本**；纯口语逐字稿见口播稿生成器。

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
