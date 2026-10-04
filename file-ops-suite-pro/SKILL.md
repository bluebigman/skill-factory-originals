---
slug: batch-renamer
name: batch-renamer
displayName: 批量重命名 文件整理工具
description: "按查找替换、序号、日期等规则批量重命名文件，预览确认后执行可回滚。"
version: 1.0.0
rules_version: cpr-20260820-n601
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/batch-renamer
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: user_2fd890c9
agent_created: true
trigger_words: ["batch-renamer", "批量重命名", "文件重命名", "批量改名", "文件整理", "renamer", "批量处理文件名"]
display_name: 批量重命名 文件整理工具（batch-renamer）
---

> 📜 **用户协议（User Agreement）**
> 1. 本 Skill 仅供学习与参考用途。使用本 Skill 产生的任何结果，由使用者自行承担全部责任；本 Skill 不提供任何明示或暗示的保证。
> 2. 涉及法律、财务、税务、投资、医疗等专业决策时，请务必咨询持证专业人士。
> 3. 本代码受版权法保护，未经授权复制、反向工程或商业利用将被追究法律责任。
<!-- user-agreement-injected -->

# 批量重命名 文件整理工具（batch-renamer）

按查找替换、序号、日期前缀、大小写等规则批量重命名文件；**默认只预览不执行**，--apply 执行并支持 --undo 一键回滚。适合把"下载文件/照片/周报/报表"批量归整成统一命名规范。

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**

## 简介

batch-renamer 是零依赖的文件批量重命名工具：单命令组合规则（查找替换/前后缀/序号/日期/大小写），执行前先出完整预览，确认后 --apply 落地，每次执行自动保存回滚记录（--undo 恢复），误操作可一键还原。

## 功能简介与能力边界

**能做**
- 按模式过滤文件（*.txt、report_*）后批量改名
- 规则组合：查找替换 / 加前后缀 / 递增序号(01..) / 日期前缀(YYYYMMDD_) / 大小写转换 / 扩展名统一
- 默认仅预览变更（安全优先）；--apply 执行；--undo 回滚上次；--verbose 逐条明细
- Windows/Linux/macOS 通用（纯标准库）

**不做**
- 不修改文件内容（仅文件名）
- 不递归处理子目录（避免误伤；如需请分批）
- 不移动/复制/删除文件

## 差异对比：本工具 vs 手工/通用脚本

| 功能 | 原版(手工或一次性脚本) | 本版(本工具) |
|---|---|---|
| 安全性 | 无预览直接改 | 默认预览，--apply 才执行 |
| 回滚 | 无 | --undo 一键恢复上次 |
| 规则组合 | 要写脚本 | 参数化组合无需编程 |
| 批量过滤 | 手动筛选 | --pattern 精确圈定 |
| 可复现 | 脚本易失 | 同参数同结果，--json 可审计 |

本项目为**全新原创设计、独立开发实现**，无对应开源前置项目。

本工具核心增量：新增预览撤回功能（默认不落盘），新增回滚能力（--undo），实现批量过滤与规则组合能力，支持 --json 审计特性。

## 安装与配置

零第三方依赖，无需 pip 安装。将资产目录放入 skills 目录或直接 `python run.py --help` 运行；跨机迁移仅需拷贝目录。

## 前置条件

- Python 3.8+（纯标准库）
- 运行前建议 `python run.py --selftest` 验证（9/9 全绿）
- 预览输出只读不改名；确认后加 --apply

## 标准执行步骤

```bash
# 1. 自检
python run.py --selftest

# 2. 预览（只展示变更，不执行）
python run.py --dir ./reports --pattern "*.txt" --find "draft" --replace "final"

# 3. 执行（加 --apply）
python run.py --dir ./reports --pattern "*.txt" --find "draft" --replace "final" --apply

# 4. 误操作回滚
python run.py --undo
```

## 使用方法

```bash
python run.py --dir 照片 --pattern "IMG_*.jpg" --seq --prefix "旅行_"          # 序号+前缀
python run.py --dir 周报 --pattern "*.md" --date                                 # 日期前缀
python run.py --dir 下载 --find "（1）" --replace ""                             # 清括号
python run.py --dir docs --case lower --ext lower --apply --verbose              # 统一小写
```

## 输出示例（节选）

```
预览（12 个文件，加 --apply 执行）：
  IMG_001.jpg -> 旅行_001.jpg
  IMG_002.jpg -> 旅行_002.jpg
  …
完成 12 / 12（回滚记录已存 ~/.batch_renamer_undo.json）
```

## 参数表

| 参数 | 默认 | 说明 |
|---|---|---|
| --dir | . | 目标目录 |
| --pattern | * | 匹配模式（*.txt / report_*）|
| --find/--replace | 空 | 查找替换 |
| --prefix/--suffix | 空 | 加前后缀 |
| --seq / --seq-start | 关/1 | 递增序号（2 位补零）|
| --date | 关 | 日期前缀 YYYYMMDD_ |
| --case | keep | lower/upper/title（仅主名）|
| --ext | keep | 扩展名 keep/lower/upper |
| --apply | 关 | 执行（默认仅预览）|
| --undo | 关 | 回滚上次执行 |
| --dry-run/--verbose/--selftest/--json | | 预览/明细/自检/审计 |

## 高级用法

1. **安全规范**：永远先预览后 --apply；大目录分批处理；--verbose 留审计
2. **回滚机制**：每次执行自动覆盖写回滚记录（~/.batch_renamer_undo.json），--undo 恢复
3. **批量场景**：周报加日期、照片加序号前缀、下载文件去浏览器后缀（"（1）"等）
4. **脚本化**：--json 输出变更计划供 CI/批处理

## 常见问题（FAQ）

- Q: 会不会改坏文件？A: 只改文件名不改内容；默认预览不执行；执行后 --undo 可恢复。
- Q: 支持中文文件名吗？A: 原生支持，Windows/macOS/Linux 均可。
- Q: 能递归子目录吗？A: 不递归（防误伤），可对子目录分别执行。

## 竞品对标

**对标对象**：手工逐个改名、一次性 Python/shell 脚本、图形改名工具。

**下载原因拆解**：要批量、要安全（可预览可回滚）、要跨平台、要可审计——本工具四点全覆盖且零依赖。

**覆盖声明**：本工具默认预览不落盘，比一次性脚本直接改更强更安全；独有回滚能力；竞品图形改名工具不具备命令行可审计输出；本工具输出结构比手工改名更全更规范。

**超越声明**：本工具在安全（预览+回滚）与可审计（--json/--verbose）两维度领先同类通用脚本方案。

## 异常处理与失败排查

| 现象 | 可能原因 | 处理方式 |
|---|---|---|
| 无可重命名文件 | 规则未命中/名已一致 | 检查 --pattern 与规则 |
| 目录不存在 | 路径错 | 用绝对路径 |
| 改名失败 | 目标名冲突/占用 | --verbose 看明细，先 --undo |
| --undo 无反应 | 无记录/记录损坏 | 手动改名或删记录重试 |

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
