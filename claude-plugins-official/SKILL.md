---
slug: claude-plugins-official
name: claude-plugins-official
displayName: 官方插件目录 检索筛选 工具集
description: 检索并筛选 Anthropic 官方维护的高质量 Claude Code 插件目录。
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
trigger_words: ["claude plugins official", "官方插件目录", "插件检索", "官方插件列表", "插件筛选", "官方扩展查询", "插件目录浏览"]

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# Claude 官方插件目录检索与筛选 Skill

## 一、能力边界速查卡

### 能做
- 检索 Anthropic 官方维护的 Claude Code 插件目录
- 按关键词、分类、用途筛选插件列表
- 输出结构化插件清单（名称、用途摘要、匹配理由）
- 提供插件筛选建议与使用场景映射

### 不能做
- 无法安装、卸载或配置插件
- 无法访问非官方插件源或第三方仓库
- 无法评估插件的实际运行性能或安全性
- 无法获取插件版本更新日志的实时推送

### 适用对象
- 需要快速定位官方插件的 Claude Code 使用者
- 需要在多个插件间做选型对比的开发者
- 希望了解官方插件生态的新手用户

---

## 二、触发方式与场景映射

| 触发词/短语 | 典型使用场景 |
|------------|------------|
| `claude plugins official` | 直接调用官方插件目录检索功能 |
| `官方插件目录` | 中文场景下浏览官方插件清单 |
| `插件检索` | 按特定关键词查找插件 |
| `官方插件列表` | 获取完整官方插件清单 |
| `插件筛选` | 按条件过滤插件结果 |
| `官方扩展查询` | 查询特定扩展的详细信息 |
| `插件目录浏览` | 浏览分类或按用途浏览插件 |

---

## 三、标准操作流程

### 前置条件
1. 确认当前环境已安装 Claude Code 且网络连接正常
2. 明确检索目标（如：需要文件处理类插件、需要代码分析类插件）
3. 准备关键词列表（可选，用于精确筛选）

### 执行步骤

**步骤 1：确认检索意图**
- 明确是浏览全部插件还是按条件筛选
- 确定筛选维度（名称、功能分类、适用场景）

**步骤 2：发起检索请求**
- 使用触发词发起检索，或直接描述需求
- 示例："检索官方插件目录中与代码审查相关的插件"

**步骤 3：接收并整理结果**
- 获取插件清单后，按以下字段整理输出：
  - 插件名称
  - 用途摘要（一句话说明核心功能）
  - 匹配理由（为什么该插件符合检索条件）

**步骤 4：结果校验**
- 核对插件名称拼写与官方文档一致
- 确认用途摘要无歧义
- 如信息不完整，标记 `[需核实:字段]` 占位

### 输出规范

输出格式为 Markdown 表格或结构化列表，示例如下：

| 插件名称 | 用途摘要 | 匹配理由 |
|---------|---------|---------|
| plugin-example | 示例用途说明 | 匹配关键词"示例" |

---

## 四、置信度门控规则

当遇到以下情况时，使用 `[需核实:字段]` 占位，不编造信息：

| 场景 | 处理方式 |
|------|---------|
| 插件名称不确定 | 输出 `[需核实:插件名称]` |
| 用途描述模糊 | 输出 `[需核实:用途摘要]` |
| 匹配理由不明确 | 输出 `[需核实:匹配理由]` |
| 目录数据不完整 | 提示"目录数据可能不完整，建议访问官方文档确认" |

---

## 五、错误码体系

| 错误码 | 错误描述 | 提示话术 | 修正步骤 |
|--------|---------|---------|---------|
| ERR_001 | 检索无结果 | "未找到匹配的官方插件，请尝试放宽筛选条件" | 1. 检查关键词拼写<br>2. 减少筛选条件<br>3. 尝试浏览完整目录 |
| ERR_002 | 网络连接失败 | "无法连接官方插件目录，请检查网络后重试" | 1. 确认网络连接<br>2. 稍后重试<br>3. 检查防火墙设置 |
| ERR_003 | 输入参数无效 | "输入的筛选条件格式不正确，请检查后重试" | 1. 确认关键词格式<br>2. 移除特殊字符<br>3. 重新输入 |
| ERR_004 | 结果超限 | "检索结果过多，建议增加筛选条件缩小范围" | 1. 增加关键词<br>2. 按分类筛选<br>3. 分页查看 |

---

## 六、FAQ 与反模式对照

| 常见坑 | 反模式示例 | 正确做法 |
|--------|-----------|---------|
| 过度筛选 | 同时使用 5+ 个筛选条件导致无结果 | 先宽后窄，逐步增加条件 |
| 忽略官方文档 | 仅依赖检索结果，不查阅官方说明 | 检索后访问官方文档确认细节 |
| 混淆插件来源 | 将第三方插件误认为官方插件 | 核对插件来源标识，仅信任官方目录 |
| 依赖单一关键词 | 只用一个词检索，遗漏相关插件 | 使用同义词、近义词多轮检索 |
| 不校验输出 | 直接使用未核实的插件信息 | 对关键字段进行二次确认 |

---

## 七、渐进式披露路径

### 速查卡（30 秒上手）
1. 说"官方插件目录"或"claude plugins official"
2. 描述你的需求（如"找文件处理插件"）
3. 获取结构化清单，核对输出字段

### 新手路径（5 分钟掌握）
1. 阅读本 Skill 的能力边界速查卡
2. 使用触发词发起一次完整检索
3. 对照输出规范检查结果格式
4. 遇到问题参考错误码体系

### 进阶路径（深度使用）
1. 掌握多维度组合筛选技巧
2. 建立个人常用插件清单
3. 结合官方文档深入理解插件能力
4. 定期关注官方目录更新

---

## 八、参数参考表

| 参数 | 类型 | 说明 | 示例 |
|------|------|------|------|
| 关键词 | string | 用于匹配插件名称或描述 | "代码审查" |
| 分类 | string | 插件功能分类 | "开发工具" |
| 排序方式 | enum | 结果排序规则 | "相关度/名称/更新时间" |
| 结果数量 | int | 单次返回最大条数 | 10/20/50 |

---

## 九、用户协议

<!-- user-agreement-injected -->

使用本 Skill 即表示您同意以下条款：

1. **责任承担**：使用者自行承担使用本 Skill 的全部责任。因使用本 Skill 产生的任何直接或间接损失，Skill 作者及贡献者不承担任何责任。
2. **禁止反向工程**：不得对本 Skill 进行反向工程、反编译、反汇编或试图提取源代码。
3. **合规使用**：使用者应遵守相关法律法规及 Anthropic 的服务条款。
4. **内容变更**：本 Skill 可能随时更新或修改，恕不另行通知。

---

## 十、许可证（License）

<!-- professional-license-embedded -->

MIT License

Copyright (c) 2024 SkillForge Studio

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

*本 Skill 由 AI 辅助生成，仅供参考。使用前请阅读相关文档。*
