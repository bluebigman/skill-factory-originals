---
slug: gmail-ai-unsub
name: gmail-ai-unsub
displayName: 邮件退订 批量处理 操作指引
description: 解析邮件退订请求，生成结构化处理方案与操作指引。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 技能工坊·退订组
agent_created: true
trigger_words: ["gmail ai unsub", "邮件退订", "退订助手", "unsubscribe", "批量退订", "取消订阅", "退订邮件"]
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

本 Skill 由 AI 辅助生成，仅供参考，不构成任何形式的操作保证或服务承诺。

---

# 邮件退订 批量处理 操作指引（SKILL.md）

## 一、能力边界：能做与不能做（速查卡）

本 Skill 用于**解析邮件退订请求**，将非结构化的退订需求转化为**结构化处理方案与操作指引**。它不直接连接邮箱服务器，不代发退订指令，也不存储任何邮件内容。

| 能力维度 | 说明 |
|---------|------|
| ✅ 能做 | 解析单封或多封邮件的退订意图，提取发件人、订阅来源、退订方式（如链接、回复指令、邮件头中的 List-Unsubscribe 字段） |
| ✅ 能做 | 生成结构化 JSON 输出，包含处理优先级、建议动作、风险提示 |
| ✅ 能做 | 对批量邮件进行一致性校验，标记缺失字段或歧义内容 |
| ❌ 不能做 | 直接调用 Gmail API 或任何邮件服务商接口执行退订 |
| ❌ 不能做 | 识别验证码、付费订阅、法律强制通知等特殊邮件类型 |
| ❌ 不能做 | 保证退订成功率或时效性 |
| ❌ 不能做 | 处理加密邮件、附件内嵌的退订链接 |

**适用对象**：需要批量整理退订请求的运营人员、个人邮箱使用者、客服团队。不适用于需要自动化执行退订动作的场景。

---

## 二、触发方式：场景映射表

当用户输入以下任一表述时，本 Skill 被激活：

| 触发词/短语 | 典型用户表述 | 对应动作 |
|------------|-------------|---------|
| `gmail ai unsub` | "用 gmail ai unsub 处理这批邮件" | 进入标准处理流程 |
| `邮件退订` | "帮我整理这些退订邮件" | 解析并生成结构化方案 |
| `退订助手` | "退订助手跑一下这个文件夹" | 执行批量解析 |
| `unsubscribe` | "I need to unsubscribe from these emails" | 解析英文退订请求 |
| `批量退订` | "批量退订这 50 封邮件" | 执行批量处理流程 |
| `取消订阅` | "取消订阅这些 newsletter" | 解析并标记优先级 |
| `退订邮件` | "这些退订邮件帮我分类" | 生成分类处理指引 |

---

## 三、标准流程：前置条件 → 执行步骤 → 输出规范

### 3.1 前置条件

| 条件项 | 要求 | 检查方式 |
|-------|------|---------|
| 文件格式 | `.eml` 或 `.txt`（UTF-8 编码） | 文件头检查 |
| 文件命名 | 统一前缀，如 `unsub_001.eml` | 目录列表核对 |
| 文件完整性 | 每封邮件至少包含 `From` 和 `Subject` 字段 | 脚本预检 |
| 目录权限 | 当前目录可读可写 | `ls -l` 确认 |
| 备份要求 | 原始文件不得修改，需另存副本 | 复制到 `./backup/` |

### 3.2 执行步骤（分步编号）

1. **准备输入**：将待处理文件放入同一目录，确认命名规范一致。若命名混乱，先执行重命名脚本（见附录 A）。
2. **试运行**：先用单个样本执行，核对输出字段与格式。命令示例：
   ```bash
   gmail ai unsub --selftest --input ./samples/unsub_001.eml
   ```
   检查输出 JSON 中 `from`、`unsub_method`、`priority` 三个字段是否与源邮件一致。
3. **批量执行**：确认无误后对全量数据执行，并保留原始文件备份。命令示例：
   ```bash
   gmail ai unsub --input ./inbox/ --output ./results/ --backup ./backup/
   ```
   执行过程中若出现错误码，参照第六章处理。
4. **校验结果**：抽查输出条目，核对关键字段与源数据一致。抽查比例不低于 10%，且至少包含 3 条。

### 3.3 输出规范

输出为 JSON 文件，每条记录结构如下：

```json
{
  "file": "unsub_001.eml",
  "from": "newsletter@example.com",
  "subject": "Weekly Digest",
  "unsub_method": "link",
  "unsub_url": "https://example.com/unsub?id=abc123",
  "priority": "high",
  "risk_flags": ["sender_domain_mismatch"],
  "suggested_action": "点击链接并确认退订",
  "confidence": 0.92
}
```

| 字段 | 类型 | 说明 | 边界值 |
|------|------|------|--------|
| `file` | string | 源文件名 | 必填 |
| `from` | string | 发件人邮箱 | 必填，格式校验 |
| `subject` | string | 邮件主题 | 可为空 |
| `unsub_method` | enum | `link` / `reply` / `header` / `unknown` | 默认 `unknown` |
| `unsub_url` | string | 退订链接 | 仅当 `unsub_method=link` 时必填 |
| `priority` | enum | `high` / `medium` / `low` | 默认 `medium` |
| `risk_flags` | array | 风险标记列表 | 可为空数组 |
| `suggested_action` | string | 建议操作 | 必填 |
| `confidence` | float | 置信度 0-1 | 低于 0.6 时需人工复核 |

---

## 四、置信度门控：不编造，只标注

当以下信息无法从源邮件中提取时，**不得猜测或编造**，必须输出占位符 `[需核实:字段名]`：

| 场景 | 输出示例 |
|------|---------|
| 邮件中无退订链接，也无退订指令 | `"unsub_method": "[需核实:unsub_method]"` |
| 发件人域名与链接域名不一致 | `"risk_flags": ["sender_domain_mismatch"], "unsub_url": "[需核实:unsub_url]"` |
| 邮件语言无法识别 | `"suggested_action": "[需核实:suggested_action]"` |
| 置信度低于 0.6 | `"confidence": 0.45, "needs_review": true` |

**规则**：任何 `[需核实:]` 字段出现时，该条记录必须附带 `"needs_review": true`，且不得自动执行后续动作。

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|---------|---------|
| `E001` | 文件不存在或不可读 | "文件无法访问，请检查路径与权限" | 确认路径正确，检查文件权限 |
| `E002` | 文件格式不支持 | "仅支持 .eml 或 .txt 格式" | 转换格式后重试 |
| `E003` | 邮件缺少 From 字段 | "邮件缺少发件人信息，无法解析" | 人工补充或跳过 |
| `E004` | 退订链接格式异常 | "退订链接不是有效 URL" | 人工核对链接 |
| `E005` | 批量执行中断 | "批量处理在第 N 条中断，已保留已处理结果" | 检查中断原因，从第 N+1 条续跑 |
| `E006` | 输出目录不可写 | "无法写入输出目录，请检查磁盘空间与权限" | 更换目录或清理空间 |

---

## 六、FAQ 反模式：常见坑与对照

| 常见坑（反模式） | 问题描述 | 正确做法 |
|-----------------|---------|---------|
| ❌ 直接批量执行 | 未试运行就处理全量数据，导致格式错误扩散 | 先单样本试运行，核对输出后再批量 |
| ❌ 覆盖原始文件 | 处理过程中修改了源邮件，无法回溯 | 始终保留 `./backup/` 副本 |
| ❌ 忽略置信度标记 | 对 `[需核实:]` 字段强行赋值 | 保留占位符，标记 `needs_review` |
| ❌ 混淆退订与举报 | 将"举报垃圾邮件"误判为退订请求 | 检查邮件正文是否包含"unsubscribe"或"退订"字样 |
| ❌ 忽略风险标记 | 未检查发件人域名与链接域名是否一致 | 启用 `risk_flags` 字段并人工复核 |

---

## 七、渐进式披露：分层次阅读路径

### 7.1 速查卡（30 秒上手）

1. 文件放同一目录，命名统一。
2. 先跑 `--selftest` 单样本。
3. 确认输出格式后跑批量。
4. 抽查 10% 结果，核对关键字段。
5. 有 `[需核实:]` 的条目一律人工处理。

### 7.2 新手路径（首次使用）

- 阅读第三章「标准流程」的 3.1 和 3.2。
- 执行一次 `--selftest`，观察输出 JSON 结构。
- 对照第五章错误码表，理解常见报错。
- 遇到不确定字段时，参考第四章置信度门控规则。

### 7.3 进阶路径（批量与异常处理）

- 阅读第三章 3.3 输出规范，自定义字段映射。
- 结合第六章反模式，优化批量执行策略。
- 对 `risk_flags` 建立人工复核清单，降低误判率。
- 可扩展 `--version` 参数检查当前 Skill 版本，确保使用最新规则。

---

## 附录 A：文件重命名脚本（Python 示例）

```python
import os, re

def rename_files(directory):
    for i, fname in enumerate(os.listdir(directory)):
        if fname.endswith(('.eml', '.txt')):
            new_name = f"unsub_{i:03d}{os.path.splitext(fname)[1]}"
            os.rename(os.path.join(directory, fname),
                      os.path.join(directory, new_name))
    print("重命名完成")
```

---

## 用户协议

<!-- user-agreement-injected -->

使用本 Skill 即表示您同意以下条款：

1. **责任承担**：使用者自行承担全部责任。本 Skill 仅提供信息解析与操作建议，不构成任何形式的退订服务承诺。因使用本 Skill 产生的任何直接或间接损失，Skill 作者与发布者不承担任何责任。
2. **禁止反向工程**：不得对本 Skill 的底层逻辑、提示词结构、输出规则进行反向工程、反编译、提取或二次分发，除非获得作者明确书面许可。
3. **合规使用**：使用者应确保其使用场景符合当地法律法规及邮件服务商的服务条款。本 Skill 不用于规避退订机制、发送垃圾邮件或任何非法目的。
4. **无保证声明**：本 Skill 按"现状"提供，不附带任何明示或暗示的保证，包括但不限于适销性、特定用途适用性和非侵权性。

---

## 许可证（License）

<!-- professional-license-embedded -->

MIT License

Copyright (c) 2024 技能工坊·退订组

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
