---
slug: awesome-claude-code-skills
name: awesome-claude-code-skills
displayName: 技能导航 场景速查 即装即用
description: 按场景分类的技能合集导航，提供推荐等级与安装命令，复制即用。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: SkillNavigator
agent_created: true
trigger_words: ["awesome claude code skills", "技能合集", "技能市场", "skill 推荐", "技能导航", "技能清单", "技能速查"]
---

> 本内容由 AI 生成，仅供学习参考 <!-- ai-generated-notice -->

# 技能导航 · 场景速查 · 即装即用

欢迎使用「技能导航」——一个面向 Claude Code 用户的技能发现与安装助手。本 Skill 将散落的技能资源按业务场景重新组织，帮助你快速定位、评估并安装合适的技能包，减少搜索与试错成本。

---

## 一、能力边界（一页纸速查卡）

### ✅ 能做什么

| 能力项 | 说明 |
|--------|------|
| 场景化检索 | 按「开发 / 文档 / 数据 / 测试 / 运维」等场景分类查找技能 |
| 推荐等级评估 | 为每个技能标注 A / B / C 三级推荐度，辅助决策 |
| 安装命令生成 | 直接输出可复制的安装命令，支持 curl 与 git clone 两种方式 |
| 组合建议 | 针对复杂任务，推荐多个技能搭配使用的顺序与方式 |
| 小样本验证 | 提供 5 分钟快速验证方案，确认技能可用后再批量执行 |

### ❌ 不能做什么

| 限制项 | 说明 |
|--------|------|
| 不托管技能文件 | 本 Skill 仅提供导航与推荐，不存储或分发技能内容 |
| 不保证兼容性 | 技能与你的 Claude Code 版本、系统环境的兼容性需自行验证 |
| 不提供定制开发 | 如需修改技能行为，请直接编辑技能源文件 |
| 不实时更新 | 技能市场状态以你执行检索时的实际结果为准 |

### 👥 适用对象

- **新手用户**：刚接触 Claude Code，想快速找到常用技能
- **效率追求者**：希望减少搜索时间，直接获取高评分技能
- **方案集成者**：需要为团队或项目组合多个技能形成工作流

---

## 二、触发方式（场景映射表）

| 你说的话（大白话） | 触发本 Skill 的方式 | 你会得到什么 |
|-------------------|-------------------|-------------|
| "帮我找个写代码的技能" | 输入 `技能导航 开发` | 开发场景技能清单 + 推荐等级 |
| "有没有处理 Excel 的 skill？" | 输入 `技能导航 数据` | 数据处理技能列表 + 安装命令 |
| "我想看看有哪些好用的技能" | 输入 `技能合集` 或 `技能市场` | 全量分类总览 + 热门推荐 |
| "这个技能靠谱吗？" | 输入 `技能导航 评估 <技能名>` | 推荐等级 + 评估依据 |
| "帮我搭一套测试流程" | 输入 `技能导航 组合 测试` | 多技能组合建议 + 执行顺序 |

---

## 三、标准流程（五步走）

### 前置条件

- 已安装 Claude Code 并完成基础配置
- 具备终端访问权限（用于执行安装命令）
- 网络可访问 GitHub 或技能源仓库

### 执行步骤

1. **找技能** → 打开附录 A「分类总览」，确定你需要的技能类别
2. **选技能** → 查看推荐等级（A 级优先，B 级按需，C 级谨慎），阅读技能描述
3. **装技能** → 复制对应安装命令，在终端执行（见下方命令格式）
4. **验技能** → 使用附录 B 的「5 分钟验证清单」进行小样本测试
5. **用技能** → 在真实任务中批量执行，定期抽查输出质量

### 安装命令格式

```bash
# 方式一：curl 安装（推荐）
curl -sSL https://skills.example.com/install.sh | bash -s <skill-slug>

# 方式二：git clone 安装
git clone https://github.com/your-org/skills/<skill-slug>.git ~/.claude/skills/<skill-slug>
```

> 注意：以上为示例命令，实际安装请以技能源仓库提供的官方命令为准。

### 输出规范

本 Skill 的输出遵循以下结构：

```
技能名称：[技能名]
推荐等级：[A/B/C]
适用场景：[场景描述]
安装命令：[可复制命令]
验证方法：[快速验证步骤]
注意事项：[已知限制或前置要求]
```

---

## 四、置信度门控

当信息不足或无法确认时，本 Skill 会明确标注占位符，**不会编造数据**。

| 场景 | 输出方式 |
|------|---------|
| 技能评分未知 | `[需核实:评分]` |
| 安装命令不确定 | `[需核实:安装命令]` |
| 兼容性未验证 | `[需核实:兼容性]` |
| 技能已下架或失效 | `[需核实:技能状态]` |

**示例**：若某个技能在检索时无法确认其最新版本，输出为：

```
技能名称：code-review-assistant
推荐等级：B（基于历史数据）
安装命令：[需核实:安装命令]（请访问技能源仓库确认）
```

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|---------|---------|
| E001 | 技能不存在 | "未找到匹配技能，请检查名称拼写" | 1. 确认技能名拼写；2. 尝试模糊搜索；3. 检查分类是否正确 |
| E002 | 安装命令执行失败 | "命令执行失败，请检查网络或权限" | 1. 确认网络连接；2. 检查是否有写权限；3. 尝试 git clone 方式 |
| E003 | 技能与当前环境不兼容 | "该技能可能不兼容当前环境" | 1. 查看技能文档中的环境要求；2. 升级 Claude Code；3. 寻找替代技能 |
| E004 | 推荐等级数据缺失 | "该技能暂无评分数据" | 1. 查看技能仓库的 star 数；2. 参考社区讨论；3. 自行小样本测试 |
| E005 | 组合方案冲突 | "所选技能组合存在功能重叠" | 1. 重新选择技能；2. 调整执行顺序；3. 移除冗余技能 |

---

## 六、FAQ 反模式

### 常见坑 1：盲目安装不验证

- **反模式**：看到 A 级推荐就直接安装，跳过验证步骤
- **正确做法**：先跑一遍附录 B 的验证清单，确认技能行为符合预期再投入正式使用

### 常见坑 2：忽略技能依赖

- **反模式**：安装技能后才发现需要额外的 Python 包或系统工具
- **正确做法**：安装前阅读技能文档的「依赖要求」部分，提前准备环境

### 常见坑 3：组合技能时顺序错误

- **反模式**：先执行后处理技能，再执行前置分析技能，导致数据流断裂
- **正确做法**：按照「数据获取 → 处理分析 → 输出呈现」的逻辑顺序排列技能

### 常见坑 4：忽视技能更新

- **反模式**：安装后长期不更新，错过 bug 修复和新功能
- **正确做法**：每月检查一次技能源仓库，关注 release 记录

### 常见坑 5：过度依赖推荐等级

- **反模式**：只选 A 级技能，不考虑实际场景匹配度
- **正确做法**：推荐等级仅作参考，最终以你的实际任务需求为准

---

## 七、渐进式披露（阅读路径）

### 🚀 新手速查（30 秒上手）

1. 看附录 A 找到你的场景分类
2. 选一个 A 级技能
3. 复制安装命令执行
4. 跑一遍验证清单
5. 开始使用

### 📖 进阶阅读（深入掌握）

1. 研究「置信度门控」理解数据可信度边界
2. 用「对比评估」功能在多个技能间做选择
3. 参考「组合建议」优化你的工作流
4. 关注「错误码体系」中的边界情况，提前规避风险

### 🧠 深度研究（生态参与）

1. 分析「输出规范」中的字段结构，理解技能设计模式
2. 研究「置信度分级标准」的判定逻辑，学习评估方法论
3. 参与技能反馈，为生态改进提供建议

---

## 附录 A：分类总览

| 分类 | 典型技能 | 推荐等级 | 一句话说明 |
|------|---------|---------|-----------|
| 开发辅助 | code-review-assistant | A | 自动代码审查，发现潜在问题 |
| 开发辅助 | commit-message-generator | A | 根据 diff 生成规范提交信息 |
| 文档处理 | doc-translator | B | 多语言文档翻译与校对 |
| 文档处理 | api-doc-generator | B | 从代码注释生成 API 文档 |
| 数据处理 | excel-formula-helper | A | Excel 公式生成与解释 |
| 数据处理 | csv-cleaner | B | CSV 数据清洗与格式化 |
| 测试相关 | test-case-generator | A | 根据函数签名生成测试用例 |
| 测试相关 | e2e-runner | C | 端到端测试执行辅助 |
| 运维部署 | docker-compose-helper | B | Docker Compose 配置生成 |
| 运维部署 | log-analyzer | C | 日志文件快速分析 |

> 注：以上为示例数据，实际技能列表以你执行检索时的结果为准。

---

## 附录 B：5 分钟验证清单

| 步骤 | 操作 | 预期结果 | 通过标准 |
|------|------|---------|---------|
| 1 | 安装技能 | 无报错 | 命令执行成功 |
| 2 | 查看技能帮助 | 显示使用说明 | 帮助信息完整 |
| 3 | 用最小样本测试 | 输出符合预期 | 结果合理无异常 |
| 4 | 检查错误处理 | 输入非法参数 | 有明确错误提示 |
| 5 | 确认可重复 | 再次执行相同操作 | 结果一致 |

---

## 附录 C：对比评估模板

当需要在多个技能间做选择时，使用以下模板：

```
对比维度 | 技能 A | 技能 B | 技能 C
---------|--------|--------|--------
推荐等级 | A      | B      | C
安装难度 | 低     | 中     | 高
功能覆盖 | 全面   | 部分   | 单一
社区活跃 | 高     | 中     | 低
已知限制 | 无     | 需 Python3 | 仅支持 Linux
最终选择 | ✅     |        |
```

---

## 用户协议

使用本 Skill 即表示您同意以下条款：

1. **责任承担**：使用者自行承担使用本 Skill 及所推荐技能的全部责任。因使用本 Skill 产生的任何直接或间接损失，本 Skill 作者及贡献者不承担任何责任。
2. **禁止反向工程**：未经明确许可，不得对本 Skill 进行反向工程、反编译、破解或试图提取源代码。
3. **合规使用**：使用者应确保使用行为符合当地法律法规及第三方平台的服务条款。
4. **无担保声明**：本 Skill 按"现状"提供，不附带任何明示或暗示的担保，包括但不限于适销性、特定用途适用性及非侵权保证。

<!-- user-agreement-injected -->

---

## 许可证（License）

本 Skill 采用 MIT 许可证授权：

```
MIT License

Copyright (c) 2024 SkillNavigator

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

*本 Skill 由 AI 辅助生成，仅供参考。使用前请阅读相关文档，并根据自身场景验证适用性。*
