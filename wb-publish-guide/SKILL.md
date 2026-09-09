---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: wb-publish-guide
name: wb-publish-guide
displayName: 技能上架 审核诊断 修复指引
description: 诊断 WorkBuddy 开放平台技能上传失败与审核驳回，提供分步修复方案。
version: 1.0.1
rules_version: cpr-20260821-n626
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/wb-publish-guide
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: SkillForge Studio
agent_created: true
trigger_words: ["wb-publish-guide", "技能上传失败", "审核驳回", "发布诊断", "上架修复", "WorkBuddy 发布"]
---

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->


> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# WorkBuddy 开放平台技能发布诊断指南

## 一、能力边界：一页纸速查卡

本 Skill 用于诊断 WorkBuddy 开放平台中技能（Skill）与专家（Agent）在上传、审核阶段遇到的问题，并输出可执行的修复步骤。

| 维度 | 能做 | 不能做 |
|------|------|--------|
| 诊断范围 | 上传失败（格式、网络、校验错误） | 平台服务器内部故障排查 |
| 审核驳回 | 内容规范、描述质量、权限声明类驳回 | 涉及平台未公开的审核算法或人工审核标准 |
| 输出形式 | 结构化修复清单 + 修正后自检项 | 保证修复后必然过审（审核含主观因素） |
| 适用对象 | 技能开发者、ISV 合作伙伴、企业管理员 | 终端业务用户（非开发角色） |

**适用对象速查**：
- 正在向 WorkBuddy 开放平台提交技能/专家包的开发者
- 收到驳回通知但不明原因的维护者
- 批量管理多个技能上架状态的运营人员

**边界警示**：本指南不处理运行时错误（如技能执行报错）、不处理账号权限纠纷、不涉及平台商业化分成规则。

---

## 二、触发方式与场景映射

当用户出现以下表述时，可激活本 Skill：

| 用户可能说 | 实际意图 | 触发词命中 |
|-----------|---------|-----------|
| "上传技能包一直失败，报错看不懂" | 定位上传链路中的技术错误 | 技能上传失败 |
| "审核被驳回了，理由是描述不符" | 理解驳回原因并修改 | 审核驳回 |
| "怎么改才能重新提交？" | 获取修复步骤 | 发布诊断 |
| "专家（Agent）配置总是不通过" | 专家类目发布问题 | 上架修复 |

**大白话场景映射**：
- 场景 A：拖拽 zip 包到控制台 → 红色错误提示 → 需要翻译错误码含义
- 场景 B：提交审核 → 3 天后收到驳回邮件 → 需要解读驳回条款
- 场景 C：修改后再次提交 → 仍被驳回 → 需要系统性排查清单

---

## 三、标准流程：从失败到重新提交

### 前置条件

1. 拥有 WorkBuddy 开放平台开发者账号（已实名认证）
2. 能访问技能管理后台（控制台 URL 以平台官方文档为准）
3. 已准备技能包源文件（zip 格式，含 manifest.json）
4. 保留最近一次提交的报错截图或驳回通知原文

### 执行步骤

**阶段一：上传失败诊断（网络与格式层）**

1. 检查网络连通性：确认能访问平台 API 端点（`ping` 或浏览器访问控制台）。
2. 核对技能包格式：
   - 必须是 zip 压缩格式，根目录直接包含 `manifest.json`（不允许嵌套一层文件夹）。
   - `manifest.json` 必须是合法 UTF-8 编码 JSON，无 BOM 头。
   - 包内文件总大小 ≤ 50MB（平台限制，超出需精简资源）。
3. 验证 manifest 必填字段：

| 字段名 | 类型 | 必填 | 示例值 |
|--------|------|------|--------|
| `slug` | string | 是 | `my-skill` |
| `name` | string | 是 | `my-skill` |
| `description` | string | 是 | 一句话描述 |
| `version` | string | 是 | `1.0.0` |
| `license` | string | 是 | `MIT` |

4. 若报错含 HTTP 状态码，对照下表：

| 状态码 | 含义 | 处理动作 |
|--------|------|---------|
| 400 | 请求体格式错误 | 重新生成 zip，检查 manifest JSON 合法性 |
| 401 | 认证失败 | 检查 API Token 是否过期，重新生成 |
| 413 | 包体过大 | 压缩资源文件，移除无用依赖 |
| 429 | 请求频率超限 | 等待 60 秒后重试，降低调用频次 |

**阶段二：审核驳回诊断（内容与合规层）**

1. 定位驳回通知中的 `rejection_code`（通常位于通知邮件或站内信末尾）。
2. 根据错误码执行对应修复（见下文"错误码体系"章节）。
3. 通用修复后自检清单：
   - [ ] description 是否包含绝对化承诺（如"最""100%""保证"）？若有，删除。
   - [ ] 技能名称是否与 slug 一致？不一致则修改。
   - [ ] 是否声明了所需权限（如网络访问、文件读写）？在 manifest 的 `permissions` 字段补充。
   - [ ] 是否包含测试用例或示例输入？建议在 `examples` 字段添加 1-2 个。

**阶段三：重新提交**

1. 在控制台选择"重新提交审核"。
2. 上传修改后的 zip 包。
3. 记录提交时间，平台审核周期通常为 1-3 个工作日（以官方 SLA 为准）。

### 输出规范

诊断完成后，输出以下结构：

```
## 诊断结果
- 问题类型：[上传失败/审核驳回]
- 错误码：[具体码值]
- 根因分析：[一句话说明]

## 修复步骤
1. [具体操作]
2. [具体操作]

## 重新提交前自检
- [ ] 项1
- [ ] 项2
```

---

## 四、置信度门控

当遇到以下情况时，本 Skill 不提供猜测性结论，输出 `[需核实:字段]` 占位：

1. 用户提供的错误信息不完整（如只有截图没有错误码）→ 输出 `[需核实:完整错误信息]`
2. 驳回理由涉及平台未公开的审核细则 → 输出 `[需核实:平台最新审核标准]`
3. 用户询问审核通过概率或时间承诺 → 输出 `[需核实:平台当前排队情况]`，并建议联系官方支持

**禁止行为**：不得编造错误码含义、不得虚构平台规则、不得承诺修复后必然过审。

---

## 五、错误码体系速查

| 错误码（示例） | 含义 | 提示话术 | 修正步骤 |
|---------------|------|---------|---------|
| `UPLOAD_ERR_JSON_PARSE` | manifest.json 解析失败 | "技能描述文件格式有误，请检查 JSON 语法" | 用 JSON 校验工具检查，修复引号/逗号 |
| `UPLOAD_ERR_SLUG_MISMATCH` | slug 与 name 不一致 | "技能标识与名称需保持一致" | 修改 name 使其等于 slug |
| `REVIEW_ERR_DESC_ABSOLUTE` | 描述含绝对化用语 | "描述中请勿使用'最''第一''保证'等词汇" | 改写为客观表述，如"提供多种配置选项" |
| `REVIEW_ERR_PERM_MISSING` | 未声明所需权限 | "技能运行需要网络权限但未声明" | 在 manifest 的 `permissions` 数组添加 `"network"` |
| `REVIEW_ERR_ICON_MISSING` | 缺少图标文件 | "请上传 512x512 像素的 PNG 图标" | 在包内 `assets/icon.png` 添加图标 |
| `REVIEW_ERR_DESC_TOO_SHORT` | 描述过短 | "描述需至少 50 字，说明功能与使用场景" | 扩展描述，包含功能概述与典型用例 |

---

## 六、FAQ 反模式对照

| 常见坑（反模式） | 问题本质 | 正确做法 |
|-----------------|---------|---------|
| 反复提交相同内容等待第三次审核 | 未定位根因，浪费审核周期 | 先对照错误码修复，再提交 |
| 删除报错信息中的敏感词以规避检查 | 治标不治本，可能触发更严审查 | 理解规则意图，如实修改描述 |
| 将 slug 改为随机字符串避免冲突 | 破坏可读性与品牌一致性 | 保持 slug 与技能名强相关 |
| 忽略权限声明直接调用 API | 运行时报错或审核被拒 | 提前声明所有外部访问权限 |
| 复制其他技能的 manifest 仅改名称 | 字段残留导致校验失败 | 从模板新建，逐字段核对 |

---

## 七、渐进式披露：分层次阅读路径

### 速查卡（30 秒上手）

1. 看错误码 → 查第五节表格 → 执行修正步骤
2. 无错误码 → 走第三节阶段一网络/格式检查
3. 修改后 → 跑一遍阶段二自检清单 → 重新提交

### 新手路径（首次接触发布）

1. 先读第三节"标准流程"全文，理解三个阶段。
2. 重点记忆前置条件中的格式要求（zip 根目录含 manifest.json）。
3. 遇到驳回不要慌，按第五节错误码逐条排查。
4. 每次修改只改一个变量，便于定位问题。

### 进阶路径（批量管理或复杂技能）

1. 关注权限声明与描述合规的细节（第五节 REVIEW 类错误）。
2. 建立本地 manifest 模板库，统一字段规范。
3. 使用脚本预检 zip 包结构（检查根目录、JSON 合法性、文件大小）。
4. 跟踪平台更新日志，及时调整适配新规则。

---

## 八、用户协议

使用本 Skill 即表示您同意以下条款：

1. **责任承担**：使用者应自行承担因使用本 Skill 产生的全部责任。本 Skill 提供的诊断建议仅供参考，不构成对审核结果的任何保证。
2. **禁止反向工程**：不得使用本 Skill 对 WorkBuddy 开放平台进行逆向工程、漏洞探测或任何违反平台服务条款的行为。
3. **内容合规**：使用者需确保其上传的技能内容符合平台规范及适用法律法规，本 Skill 不承担内容合规性审查义务。
4. **免责声明**：本 Skill 基于公开信息与通用经验编写，平台规则可能随时变更，请以官方最新文档为准。

<!-- user-agreement-injected -->

---

## 九、许可证（License）

本 Skill 采用 MIT 许可证发布：

```
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

---

*本 Skill 由 AI 辅助生成，仅供参考。使用前请阅读 WorkBuddy 开放平台官方文档。*
