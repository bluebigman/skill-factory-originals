---
name: email-draft-pro
description: 按场景生成专业商务邮件，自动匹配语气与格式，支持中英双语与批量起草。
version: 3.0.0
license: MIT
ai_generated: true
disclaimer: true
source_project: skill-factory-originals
copyright_holder: bluebigman

---

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->

> 📜 **用户协议（User Agreement）**
> 1. 本 Skill 仅供学习与参考用途。使用本 Skill 产生的任何结果，由使用者自行承担全部责任；本 Skill 不提供任何明示或暗示的保证。
> 2. 涉及法律、财务、税务、投资、医疗等专业决策时，请务必咨询持证专业人士。
> 3. 本代码受版权法保护，未经授权复制、反向工程或商业利用将被追究法律责任。
<!-- user-agreement-injected -->


# email-draft-pro

## 能力边界

| 能力 | 支持 | 不支持 |
|------|------|--------|
| 场景 | dunning, follow_up, quote, apology, thanks, formal | 其他场景 |
| 语言 | zh-CN, en-US | 其他语言 |
| 语气 | formal, semi, casual | 其他语气 |
| 输出格式 | markdown, text, html | 其他格式 |
| 批量处理 | CSV/JSON，单批 ≤ 100 条 | 超过 100 条 |
| 字段校验 | 必填字段缺失时标注 `[需核实:字段]` | 静默编造数据 |
| 风险提示 | 检测高风险措辞并警告 | 自动修改内容 |
| 网络请求 | 无（纯本地处理） | 不涉及 |

## 触发条件

- 用户请求起草商务邮件
- 用户提供场景、语言、语气等参数
- 用户要求批量生成邮件

## 标准流程

1. 解析用户输入（场景、语言、语气、字段值）
2. 校验参数合法性（场景、语言、语气）
3. 加载对应模板
4. 渲染邮件内容（缺失字段标注）
5. 检查风险措辞
6. 输出结果（单封或批量）

## 置信度门控

- 必填字段缺失时，输出 `[需核实:字段]` 并返回警告
- 检测到风险措辞时，输出警告但不修改内容
- 批量处理时，单条失败不影响其他记录

## 错误码

| 错误码 | 说明 |
|--------|------|
| E001 | 模板加载失败 |
| E002 | 模板非合法 JSON |
| E003 | 指定的场景不存在 |
| E004 | 该场景下无对应语言模板 |
| E005 | 指定的语气不存在 |
| E006 | 必填字段缺失 |
| E007 | 单次输入超过长度上限 |
| E008 | 批量记录数超过上限 |
| E009 | 批量输入文件解析失败 |
| E010 | 输出写入失败 |

## FAQ / 反模式

- **反模式**：使用 `random` 伪造数据 → 禁止，必须基于用户输入
- **反模式**：静默忽略缺失字段 → 必须标注 `[需核实:字段]`
- **FAQ**：如何添加新场景？→ 修改 `TEMPLATES` 字典
- **FAQ**：如何自定义模板？→ 编辑 `TEMPLATES` 中的模板字符串

## 使用示例

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

## 失败处理

- 命令执行失败或返回非零退出码时，程序会输出明确错误信息并给出排查建议。
- 依赖缺失时提示安装命令；网络异常时建议重试并检查连接。
- 异常情况不中断主流程，错误信息包含具体原因（error context），便于定位修复。
## 前置条件

- 本技能开箱即用，无需额外安装依赖。
- 需要 Python 3.9+ 运行环境。
- 涉及网络请求时需保持网络连通。