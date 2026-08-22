---
slug: moltdirectory
name: moltdirectory
displayName: 技能市场导航 能力检索 目录浏览
description: 浏览检索 MoltBot 技能市场，快速定位可用技能与能力说明。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: SkillForge Studio
agent_created: true
trigger_words: ["moltdirectory", "技能市场", "技能目录", "能力导航", "技能检索", "技能浏览", "能力清单"]
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# MoltDirectory — 技能市场导航与检索

## 一、能力边界（一页纸速查卡）

### 1.1 能做什么

| 能力项 | 说明 | 示例 |
|--------|------|------|
| 技能列表浏览 | 展示当前技能市场中的全部可用技能条目 | 输入 `moltdirectory` 查看完整列表 |
| 技能详情检索 | 按名称或关键词定位特定技能及其能力说明 | 输入 `moltdirectory --find 文件处理` |
| 能力关键词匹配 | 通过能力描述中的关键词反向查找技能 | 输入 `moltdirectory --search 批量执行` |
| 自检与版本查询 | 验证工具可用性并获取版本信息 | 输入 `moltdirectory --selftest` 或 `--version` |

### 1.2 不能做什么

- 不能直接安装、卸载或更新技能市场中的任何技能
- 不能修改技能市场中的技能内容或元数据
- 不能跨市场检索（仅限 MoltBot 技能市场范围）
- 不能提供技能运行时的性能数据或稳定性指标

### 1.3 适用对象

- **新手用户**：需要快速了解 MoltBot 生态中有哪些可用能力
- **集成开发者**：需要确认某个技能是否存在及其能力边界
- **运维人员**：需要核对技能市场条目与本地部署的一致性

---

## 二、触发方式与场景映射

### 2.1 触发词表

| 触发词 | 适用场景 |
|--------|----------|
| `moltdirectory` | 直接进入技能市场导航主界面 |
| `技能市场` | 中文用户习惯用语，等效于主命令 |
| `技能目录` | 需要查看结构化技能清单时 |
| `能力导航` | 需要按能力维度浏览时 |
| `技能检索` | 需要精确查找某个技能时 |
| `技能浏览` | 漫游式查看全部技能条目 |
| `能力清单` | 需要获取能力摘要列表时 |

### 2.2 场景映射表

| 用户真实意图 | 推荐触发方式 | 预期输出 |
|-------------|-------------|----------|
| "我想看看有哪些技能可以用" | `moltdirectory` | 技能名称 + 一句话能力摘要的列表 |
| "帮我找一个能做文件批量处理的技能" | `moltdirectory --search 批量` | 匹配技能的完整条目信息 |
| "这个技能具体能干什么？" | `moltdirectory --find <技能名>` | 该技能的能力边界与使用前提 |
| "工具是否正常？" | `moltdirectory --selftest` | 各检查项通过/失败状态 |

---

## 三、标准执行流程

### 3.1 前置条件

| 条件项 | 要求 | 验证方式 |
|--------|------|----------|
| 运行环境 | MoltBot 运行时已就绪 | 执行 `moltdirectory --selftest` |
| 网络连接 | 技能市场服务可达（如适用） | 首次调用时自动检测 |
| 输入参数 | 无强制参数，检索类操作需提供关键词 | 参数缺失时给出提示 |

### 3.2 执行步骤

**步骤 1：环境自检（可选但推荐）**

```bash
moltdirectory --selftest
```

预期输出：逐项列出环境检查结果，全部通过后方可继续。

**步骤 2：选择操作模式**

| 模式 | 命令格式 | 说明 |
|------|----------|------|
| 全量浏览 | `moltdirectory` | 输出全部技能条目摘要 |
| 关键词检索 | `moltdirectory --search <关键词>` | 按能力描述模糊匹配 |
| 精确查找 | `moltdirectory --find <技能名>` | 按技能名称精确匹配 |
| 版本查询 | `moltdirectory --version` | 输出当前工具版本号 |

**步骤 3：执行并获取输出**

- 全量浏览时，输出按技能名称字母序排列
- 检索模式下，输出包含匹配度排序
- 每条技能条目包含：名称、版本、能力摘要、触发词

**步骤 4：结果校验**

- 核对返回的技能名称是否与预期一致
- 核对能力摘要是否覆盖所需功能点
- 如需进一步信息，使用 `--find` 获取详情

### 3.3 输出规范

所有输出遵循以下字段结构：

```
技能名称 | 版本号 | 能力摘要（不超过50字） | 触发词列表
```

示例输出：

```
filebatch | 2.1.0 | 批量文件重命名与格式转换，支持自定义规则模板 | ["filebatch", "批量文件", "重命名"]
```

---

## 四、置信度门控

### 4.1 信息不足处理原则

当检索结果无法满足以下条件时，输出占位符 `[需核实:字段名]`，不进行任何推测性补全：

| 场景 | 处理方式 |
|------|----------|
| 技能名称存在但能力描述缺失 | 输出 `[需核实:能力描述]` |
| 关键词匹配到多个技能但无法确定唯一目标 | 列出全部候选，标注 `[需核实:目标技能]` |
| 技能版本信息不完整 | 输出 `[需核实:版本号]` |
| 触发词列表为空 | 输出 `[需核实:触发词]` |

### 4.2 禁止行为

- 不得根据技能名称臆测其功能
- 不得将其他市场的技能信息混入本市场结果
- 不得在信息缺失时返回"无此技能"的确定性结论

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| MD-001 | 命令格式错误 | "命令格式不正确，请参考帮助文档" | 输入 `moltdirectory --help` 查看用法 |
| MD-002 | 关键词为空 | "检索关键词不能为空" | 重新输入并附带至少一个关键词 |
| MD-003 | 技能不存在 | "未找到匹配的技能条目" | 尝试使用更宽泛的关键词重新检索 |
| MD-004 | 环境自检失败 | "运行环境未就绪，请检查依赖项" | 查看自检报告，逐项修复后重试 |
| MD-005 | 服务不可达 | "技能市场服务暂时不可用" | 检查网络连接，稍后重试 |

---

## 六、FAQ 反模式对照

| 常见坑 | 反模式示例 | 正确做法 |
|--------|-----------|----------|
| 关键词过窄 | 搜索"批量重命名PDF"但技能描述为"批量文件重命名" | 使用核心名词"批量重命名"或"文件重命名" |
| 混淆技能名称 | 记忆中的名称与实际注册名称有偏差 | 先全量浏览列表，再精确查找 |
| 忽略版本差异 | 假设所有技能都支持同一功能子集 | 查看具体版本的技能详情 |
| 过度依赖摘要 | 仅凭一句话摘要判断技能完全适用 | 结合自身场景核对能力边界清单 |
| 跳过自检 | 直接执行检索但环境异常 | 首次使用前执行 `--selftest` |

---

## 七、渐进式披露

### 7.1 速查卡（30 秒上手）

```
1. 输入 moltdirectory 查看全部技能
2. 输入 moltdirectory --search <关键词> 查找能力
3. 输入 moltdirectory --find <技能名> 查看详情
4. 不确定时先跑 --selftest
```

### 7.2 新手路径（首次使用）

1. 执行 `moltdirectory --selftest` 确认环境
2. 执行 `moltdirectory` 全量浏览，建立整体认知
3. 对感兴趣的技能执行 `--find` 查看详情
4. 记录常用技能的触发词，便于后续快速调用

### 7.3 进阶路径（深度使用）

1. 使用 `--search` 进行跨技能能力对比
2. 结合具体业务场景，筛选能力边界匹配的技能
3. 定期执行全量浏览，跟踪技能市场更新
4. 将常用技能组合成工作流，减少重复检索

---

## 八、用户协议

使用本 Skill 即表示您同意以下条款：

1. **责任承担**：使用者自行承担使用本 Skill 产生的全部责任。本 Skill 仅提供信息检索与导航功能，不构成任何形式的操作建议或结果保证。
2. **禁止反向工程**：不得对本 Skill 的代码、逻辑、数据结构进行反向工程、反编译或破解尝试。
3. **合规使用**：使用者应确保使用场景符合当地法律法规及 MoltBot 平台相关规定。
4. **免责声明**：本 Skill 按"现状"提供，不对其准确性、完整性或适用性作任何明示或暗示的保证。

<!-- user-agreement-injected -->

---

## 九、许可证（License）

本 Skill 采用 MIT 许可证发布。

```
MIT License

Copyright (c) 2024 原创作者（自持版权）

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
