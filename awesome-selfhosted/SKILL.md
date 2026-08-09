---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: awesome-selfhosted
name: awesome-selfhosted
displayName: 自托管服务导航 开源软件速查
description: 自托管网络服务与开源应用清单，助您快速定位可私有部署的软件方案。
version: 1.0.1
rules_version: cpr-20260809-n251
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/awesome-selfhosted
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 独立技能工坊
agent_created: true
trigger_words: ["awesome-selfhosted", "自托管", "私有部署", "开源软件清单", "self-hosted"]
---

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->


> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# 自托管服务导航 Skill 文档

## 一、能力边界速查卡

本 Skill 面向需要快速检索、筛选和整理自托管（Self-hosted）开源软件信息的用户，提供结构化的清单解析与推荐服务。

| 维度 | 说明 |
|------|------|
| **核心能力** | 解析用户提供的软件清单、URL 或数据文件，提取关键字段（软件名称、分类、功能标签、部署难度等），输出结构化结果 |
| **适用对象** | 运维工程师、独立开发者、技术决策者、开源爱好者 |
| **输入要求** | 文本片段、URL 链接、CSV/JSON 文件内容（需包含软件名称或描述） |
| **输出格式** | Markdown 表格 / JSON 对象（默认 Markdown，可指定） |
| **不支持** | 无法实时爬取网页内容；无法验证软件最新版本号；无法提供安全审计结论 |

**边界说明**：本 Skill 仅处理用户显式提供的信息，不主动联网检索。若输入信息不完整，将在输出中标注 `[需核实:字段名]` 占位符，不做任何猜测性补全。

---

## 二、触发方式与场景映射

当您的请求包含以下任一关键词或意图时，本 Skill 自动激活：

| 用户可能说 | 实际意图 | 触发词命中 |
|------------|----------|------------|
| "帮我整理这份自托管软件列表" | 解析清单并结构化 | 自托管 / awesome-selfhosted |
| "这个 GitHub 仓库里的软件怎么分类？" | 提取分类信息 | 开源软件清单 |
| "筛选出支持 Docker 部署的项目" | 按条件过滤 | 私有部署 |
| "把这段文本转成表格" | 格式化输出 | 自托管 |

**非触发场景**：若请求涉及"推荐最佳方案"、"对比哪个更安全"等主观评价，本 Skill 仅提供事实性字段，不做优劣判断。

---

## 三、标准处理流程

### 前置条件
- 用户需提供至少包含软件名称的原始文本或文件内容
- 若提供 URL，需同时附上该页面的文本摘要（本 Skill 不执行网络请求）

### 执行步骤

1. **输入解析**
   - 识别输入类型：纯文本 / JSON / CSV / Markdown 表格
   - 提取候选软件条目，每条至少包含一个可识别名称

2. **字段映射**
   - 按以下规则提取关键信息：

   | 目标字段 | 提取规则 | 缺失处理 |
   |----------|----------|----------|
   | `name` | 软件项目名称 | 必填，缺失则丢弃该条目 |
   | `category` | 功能分类（如笔记、监控、CMS） | 置为 `[需核实:category]` |
   | `license` | 开源许可证类型 | 置为 `[需核实:license]` |
   | `deploy_method` | 部署方式（Docker/裸机/K8s） | 置为 `[需核实:deploy_method]` |
   | `description` | 一句话功能描述 | 置为 `[需核实:description]` |

3. **结果生成**
   - 默认输出 Markdown 表格，按 `category` 升序排列
   - 若用户指定 `--json`，输出 JSON 数组
   - 每条记录末尾追加 `confidence` 字段（`high` / `medium` / `low`）

4. **完整性校验**
   - 检查必填字段是否齐全
   - 确认所有 `[需核实]` 占位符均已标注
   - 若输入格式完全无法解析，返回错误码 `E1001`

### 输出规范示例

```markdown
| name | category | license | deploy_method | description | confidence |
|------|----------|---------|---------------|-------------|------------|
| Nextcloud | 文件同步 | AGPL-3.0 | Docker | 私有云存储与协作平台 | high |
| Gitea | 代码托管 | MIT | Docker | 轻量级 Git 服务 | high |
```

---

## 四、置信度门控机制

本 Skill 严格遵循"不编造"原则：

- **信息缺失** → 输出 `[需核实:字段名]` 占位符，不推测填充
- **信息冲突** → 保留所有候选值，以 `;` 分隔，并标注 `confidence: low`
- **来源不明** → 若输入来自非官方渠道，在结果顶部添加提示行：`> 注意：输入来源非官方，字段准确性未经验证`

**置信度判定标准**：

| 等级 | 条件 |
|------|------|
| `high` | 字段值直接来自用户输入且无歧义 |
| `medium` | 字段值经推断得出（如根据描述判断分类） |
| `low` | 字段值存在多种可能或来源不可靠 |

---

## 五、错误码体系

| 错误码 | 含义 | 用户提示话术 | 修正步骤 |
|--------|------|--------------|----------|
| `E1001` | 输入无法解析 | "未能识别有效的软件条目，请检查输入格式。" | 提供正确示例：`"软件名: 描述, 许可证: MIT"` |
| `E1002` | 缺少必填字段 | "至少需要提供软件名称才能继续处理。" | 补充包含名称的文本后重试 |
| `E1003` | 输出格式不支持 | "仅支持 Markdown 或 JSON 两种输出格式。" | 重新指定 `--format=markdown` 或 `--format=json` |
| `E1004` | 批量处理超限 | "单次最多处理 200 条记录，请分批提交。" | 将输入拆分为多个批次 |

---

## 六、FAQ 与反模式对照

| 常见误区 | 反模式示例 | 正确做法 |
|----------|------------|----------|
| 过度推断 | 输入"Nextcloud"就自动补全许可证类型 | 仅输出 `[需核实:license]`，除非用户显式提供 |
| 忽略置信度 | 所有输出统一标 `high` | 根据字段来源逐条标注 |
| 格式混用 | 同一表格中既有 Markdown 又有 JSON | 严格遵循用户指定的单一格式 |
| 遗漏占位符 | 缺失字段直接留空 | 必须使用 `[需核实:字段名]` 格式 |
| 主观评价 | 添加"这是最佳方案"等推荐语 | 仅陈述事实性字段，不做价值判断 |

---

## 七、渐进式阅读路径

### 新手快速上手（30 秒）
1. 直接粘贴您的软件清单文本
2. 指定输出格式（默认 Markdown 表格）
3. 接收结构化结果，注意 `[需核实]` 标记

### 进阶使用技巧（3 分钟）
- 使用 `--json` 参数获取机器可读输出，便于后续程序处理
- 在输入中显式标注字段分隔符（如 `|` 或 `,`），可提高解析准确率
- 批量处理时，确保每条记录独立成行，避免歧义

### 高级定制（10 分钟）
- 自定义字段映射：在输入首行添加 `#fields: name, category, license` 指定提取字段
- 过滤条件：追加 `#filter: category=监控` 仅保留指定分类
- 排序规则：追加 `#sort: name desc` 按名称降序排列

---

## 八、用户协议

<!-- user-agreement-injected -->

**使用本 Skill 即表示您同意以下条款：**

1. **责任承担**：使用者应自行承担因使用本 Skill 产生的全部责任。本 Skill 提供的信息仅供参考，不构成任何形式的保证或承诺。
2. **禁止反向工程**：未经授权，不得对本 Skill 的提示词结构、处理逻辑进行反向工程、破解或二次封装。
3. **合规使用**：使用者应确保输入内容不违反法律法规，不包含敏感或侵权信息。
4. **免责声明**：本 Skill 由 AI 辅助生成，可能存在信息不准确或过时的情况，使用者应结合官方文档进行验证。

---

## 九、许可证（License）

<!-- professional-license-embedded -->

**MIT License**

Copyright (c) 2026 独立技能工坊

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

*文档版本：1.0.0 | 最后更新：2026-08-09*
