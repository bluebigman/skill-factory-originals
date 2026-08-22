---
slug: awesome-claude-skills
name: awesome-claude-skills
displayName: 技能装配台 工作流搭建 资源检索
description: 检索并配置Claude技能资源，快速搭建个性化AI工作流。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 林澈
agent_created: true
trigger_words: ["awesome-claude-skills", "claude技能", "技能清单", "工作流配置", "claude资源", "技能检索", "工作流搭建", "技能市场"]
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# 技能装配台（awesome-claude-skills）

## 一、能力边界：一页纸速查卡

本 Skill 是 Claude 技能资源的**检索与配置向导**，帮助你在数分钟内定位、安装并验证可用的第三方技能模块。

| 维度 | 能做 | 不能做 |
|------|------|--------|
| 检索 | 根据需求关键词匹配技能清单，给出推荐列表 | 不保证推荐结果覆盖全部现存技能 |
| 配置 | 提供安装命令、初始化步骤、自检流程 | 不代替你执行安装（需你在终端操作） |
| 验证 | 引导运行 `--selftest` 检查安装状态 | 不负责修复第三方技能的内部缺陷 |
| 教学 | 按 README 示例演示典型用法 | 不提供超出 README 范围的深度定制教学 |
| 安全 | 提示第三方验证注意事项 | 不对第三方资源的内容、安全性、合规性做任何担保 |

**适用对象**：需要快速为 Claude 环境装配新技能的开发者、AI 工作流搭建者、自动化爱好者。

**不适用对象**：需要官方技术支持的用户、零命令行基础且不愿阅读文档的用户。

---

## 二、触发方式：场景映射表

当你的输入命中以下任一场景，本 Skill 自动激活：

| 触发词/场景 | 大白话解释 | 本 Skill 会做什么 |
|-------------|-----------|-------------------|
| "awesome-claude-skills" | 直接点名 | 进入完整工作流 |
| "claude技能" / "技能清单" | 想看看有什么可用技能 | 输出推荐列表 + 筛选建议 |
| "工作流配置" | 想把多个技能串起来用 | 给出配置顺序和依赖关系说明 |
| "claude资源" | 找现成的工具/插件 | 引导检索 + 安装 + 自检 |
| "技能检索" / "技能市场" | 想找特定功能的技能 | 按需求关键词匹配并推荐 |
| "帮我搭个自动化流程" | 有具体场景但不知从何下手 | 先引导描述需求，再推荐组合方案 |

---

## 三、标准流程：从需求到落地

### 前置条件

- 已安装 Claude 命令行环境（或等效运行环境）
- 具备终端基本操作能力（复制粘贴命令、查看输出）
- 网络可访问技能仓库/资源源

### 执行步骤

**Step 1 — 描述需求（一句话）**

用一句话说清你要解决什么问题。参考句式：

> "我要把每周的周报自动整理成 Markdown 并发送到指定频道。"

**Step 2 — 获取推荐列表**

根据你的需求关键词，本 Skill 输出 3-5 个候选技能，包含：

| 字段 | 说明 | 示例 |
|------|------|------|
| 技能名 | 资源标识 | `weekly-report-gen` |
| 功能摘要 | 一句话说明 | 自动汇总周报并格式化输出 |
| 依赖项 | 需要预装的环境 | Python 3.9+ |
| 安装命令 | 可直接复制的指令 | `claude install weekly-report-gen` |
| 复杂度 | 低/中/高 | 低 |

**Step 3 — 选择并安装**

- 从推荐列表中选 **1-2 个**最匹配的技能
- 复制安装命令到终端执行
- 如安装失败，参考下方「错误码体系」排查

**Step 4 — 运行自检**

```bash
awesome-claude-skills --selftest
```

预期输出（示例）：

```
[OK] 技能包完整性校验通过
[OK] 依赖项检查通过（python3, git）
[OK] 配置目录可写
[OK] 网络连接正常
[WARN] 未检测到 README 文件，请手动确认
```

**Step 5 — 按 README 示例使用**

- 打开技能目录下的 `README.md`
- 复制其中最小可运行示例
- 替换为你的实际参数后执行

### 输出规范

- 推荐列表必须包含：技能名、功能摘要、依赖项、安装命令、复杂度
- 自检结果必须逐项列出 `[OK]` / `[WARN]` / `[FAIL]` 状态
- 所有命令示例必须使用代码块包裹，便于复制

---

## 四、置信度门控：不编造，只标注

当出现以下情况时，本 Skill 会输出占位符 `[需核实:字段]` 而非猜测：

| 场景 | 处理方式 |
|------|----------|
| 技能版本号未知 | `[需核实:版本号]` |
| 依赖项兼容性不确定 | `[需核实:兼容性]` |
| 安装命令可能因平台而异 | `[需核实:平台差异]` |
| 第三方技能的安全性未验证 | `[需核实:安全审计状态]` |

**原则**：宁可留白，不可虚构。所有占位符均需在后续验证后替换。

---

## 五、错误码体系：常见故障排查

| 错误码 | 现象 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| E001 | 安装命令找不到技能 | "技能名不存在或已下架" | 1. 检查拼写；2. 运行 `awesome-claude-skills --list` 查看可用列表 |
| E002 | 依赖项缺失 | "缺少运行所需组件" | 1. 查看 README 的依赖清单；2. 按提示安装缺失项 |
| E003 | 权限不足 | "无法写入配置目录" | 1. 检查目录权限；2. 使用 `sudo` 或调整用户权限 |
| E004 | 网络超时 | "连接资源源超时" | 1. 检查网络；2. 重试；3. 更换镜像源 |
| E005 | 自检失败 | "自检未通过，存在 FAIL 项" | 1. 查看 FAIL 项详情；2. 按提示修复；3. 重新运行 `--selftest` |
| E006 | 版本冲突 | "与现有技能版本不兼容" | 1. 查看冲突详情；2. 升级或降级相关技能 |

---

## 六、FAQ 反模式：常见坑与正确姿势

| 常见坑（反模式） | 问题描述 | 正确做法 |
|------------------|----------|----------|
| 一次性装太多 | 一次安装 5+ 个技能，依赖冲突频发 | 每次只装 1-2 个，验证通过后再继续 |
| 跳过自检 | 装完直接使用，报错后无从排查 | 安装后必须运行 `--selftest` |
| 忽略 README | 不看文档直接猜用法 | 先读 README 的最小示例，再扩展 |
| 盲目信任第三方 | 不验证来源就运行未知代码 | 安装前检查仓库星标、更新时间、代码审查记录 |
| 不记录配置 | 装完忘记装了什么、改了什么 | 维护一份本地技能清单（名称、版本、用途） |

---

## 七、渐进式披露：按需阅读路径

### 速查卡（30 秒版）

```
需求描述 → 获取推荐 → 选 1-2 个 → 安装 → --selftest → 读 README → 使用
```

### 新手路径（首次使用）

1. 阅读「能力边界」明确本 Skill 能做什么
2. 按「标准流程」Step 1-5 完整走一遍
3. 遇到问题查「错误码体系」
4. 记住「FAQ 反模式」中的前三条

### 进阶路径（熟练用户）

1. 直接使用触发词快速进入检索
2. 关注「置信度门控」中的占位符，自行验证
3. 参考「FAQ 反模式」中的后两条，建立自己的技能管理规范
4. 组合多个技能时，注意依赖顺序和版本兼容性

---

## 八、用户协议

<!-- user-agreement-injected -->

**使用本 Skill 即表示您同意以下条款：**

1. **责任承担**：使用者应自行承担因使用本 Skill 及其推荐的第三方资源所产生的全部责任。本 Skill 不对任何直接或间接损失负责。
2. **第三方验证**：使用者应自行验证所安装技能的安全性、合规性和适用性。本 Skill 不对第三方资源的内容和安全性负责。
3. **禁止反向工程**：禁止对本 Skill 进行反向工程、反编译、反汇编或试图提取源代码。
4. **禁止不当用途**：禁止将本 Skill 用于任何违法、侵权或不当用途。

---

## 九、许可证（License）

<!-- professional-license-embedded -->

**MIT License**

Copyright (c) 2025 林澈

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
