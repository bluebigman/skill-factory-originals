---
slug: open-saas
name: open-saas
displayName: 开源SaaS 情报解析 结构化转换
description: 将开源SaaS项目信息解析为结构化数据，辅助调研与学习。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: Kaiwu
agent_created: true
trigger_words: ["open saas", "开源SaaS", "SaaS解析", "数据转换", "结构化输出", "项目调研", "情报整理"]
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# 开源SaaS 情报解析 Skill 文档

## 一、能力边界（一页纸速查卡）

### 1.1 本 Skill 能做什么

| 序号 | 能力项 | 说明 |
|------|--------|------|
| 1 | 输入识别 | 接受本地文件路径或可访问的 URL 链接 |
| 2 | 字段抽取 | 从项目 README、官网、文档中抽取名称、技术栈、许可证、部署方式等关键字段 |
| 3 | 结构化输出 | 将非结构化文本转换为统一的 JSON 或 Markdown 表格 |
| 4 | 批量处理 | 支持多文件/多链接的批量解析，输出映射表 |
| 5 | 差异标注 | 对缺失或矛盾的信息打上 `[需核实:字段]` 占位标记 |

### 1.2 本 Skill 不能做什么

| 序号 | 限制项 | 说明 |
|------|--------|------|
| 1 | 不访问私有仓库 | 仅处理公开可访问的内容 |
| 2 | 不执行代码 | 不运行项目代码，仅做静态文本解析 |
| 3 | 不保证实时性 | 解析结果基于输入内容，不主动抓取最新数据 |
| 4 | 不处理非文本格式 | 图片、视频、二进制文件不在处理范围内 |
| 5 | 不进行商业判断 | 不评估项目商业价值或投资潜力 |

### 1.3 适用对象

- 开源项目调研人员
- SaaS 产品学习者
- 技术选型评估者
- 数据整理与分析人员

---

## 二、触发方式

### 2.1 触发词

直接使用以下任一触发词即可激活本 Skill：

- `open saas`
- `开源SaaS`
- `SaaS解析`
- `数据转换`
- `结构化输出`
- `项目调研`
- `情报整理`

### 2.2 场景映射表

| 用户说（大白话） | 实际触发动作 |
|------------------|--------------|
| "帮我把这个 GitHub 项目信息整理一下" | 解析 URL 中的 README 内容 |
| "这几个开源 SaaS 的对比表帮我做一下" | 批量解析多个输入并生成对比表格 |
| "这个本地文件里的项目信息提取出来" | 读取本地文件并结构化输出 |
| "这个项目用的什么技术栈？" | 抽取技术栈相关字段 |
| "帮我看看这个项目的许可证是什么" | 抽取许可证字段并标注合规性 |

---

## 三、标准流程

### 3.1 前置条件

| 条件项 | 要求 |
|--------|------|
| 输入类型 | 本地文件（与 Skill 运行目录一致）或可访问的 URL |
| 网络要求 | URL 输入需确保网络可达 |
| 文件命名 | 批量处理时建议遵循 `项目名_来源.扩展名` 格式 |
| 单条试运行 | 首次使用或输入格式变化时，先执行单条数据试运行 |

### 3.2 执行步骤

**Step 1：输入准备**

确认待处理内容可访问。若为本地文件，需与 Skill 运行目录一致；若为 URL，需确保网络可达。

**Step 2：单条试运行**

```bash
# 示例：单条解析命令
open-saas --input ./projects/example_project_github.md
```

**Step 3：检查输出字段**

查看输出结果，确认以下字段是否完整：

| 字段名 | 必填 | 说明 |
|--------|------|------|
| project_name | 是 | 项目名称 |
| source_url | 是 | 来源链接 |
| tech_stack | 是 | 技术栈列表 |
| license | 是 | 许可证类型 |
| deployment | 否 | 部署方式 |
| stars | 否 | Star 数量（如有） |
| last_updated | 否 | 最近更新时间 |

**Step 4：批量执行**

```bash
# 示例：批量解析命令
open-saas --input ./projects/ --batch
```

**Step 5：抽查校验**

随机抽取 20% 的解析结果，人工核对关键字段的准确性。

### 3.3 输出规范

输出格式为 JSON，示例：

```json
{
  "project_name": "ExampleSaaS",
  "source_url": "https://github.com/example/example-saas",
  "tech_stack": ["React", "Node.js", "PostgreSQL"],
  "license": "MIT",
  "deployment": "Docker Compose",
  "stars": 1234,
  "last_updated": "2024-03-15"
}
```

---

## 四、置信度门控

### 4.1 信息不足时的处理

当输入内容无法明确某个字段时，使用 `[需核实:字段名]` 占位，不进行猜测或编造。

**示例：**

```json
{
  "project_name": "ExampleSaaS",
  "license": "[需核实:license]",
  "deployment": "[需核实:deployment]"
}
```

### 4.2 置信度分级

| 级别 | 说明 | 处理方式 |
|------|------|----------|
| 高 | 输入中明确出现 | 直接输出 |
| 中 | 可从上下文推断 | 输出并标注 `(推断)` |
| 低 | 无法确定 | 输出 `[需核实:字段]` |

---

## 五、错误码体系

| 错误码 | 错误描述 | 提示话术 | 修正步骤 |
|--------|----------|----------|----------|
| E001 | 输入文件不存在 | "未找到指定文件，请检查路径" | 1. 确认文件路径正确 2. 确认文件与运行目录一致 |
| E002 | URL 无法访问 | "无法访问该 URL，请检查网络或链接" | 1. 检查网络连接 2. 确认链接有效 |
| E003 | 输入格式不支持 | "不支持的输入格式，请使用 .md/.txt/.json" | 1. 转换文件格式 2. 重新输入 |
| E004 | 批量处理中断 | "批量处理中断，请检查第 N 个文件" | 1. 定位失败文件 2. 单独处理该文件 |
| E005 | 输出字段缺失 | "输出缺少必填字段" | 1. 检查输入内容 2. 补充信息后重试 |

---

## 六、FAQ 反模式

### 6.1 常见坑

| 坑位 | 反模式 | 正确做法 |
|------|--------|----------|
| 1 | 跳过单条试运行直接批量处理 | 首次使用必须单条试运行 |
| 2 | 输入 URL 不检查可达性 | 先确认 URL 可访问 |
| 3 | 对缺失字段自行猜测 | 使用 `[需核实:字段]` 占位 |
| 4 | 忽略输出字段校验 | 每次解析后检查必填字段 |
| 5 | 批量处理不抽查 | 至少抽查 20% 的结果 |

### 6.2 反模式对照

**反模式 1：** "这个项目应该是 MIT 许可证，直接填上吧"

**正确做法：** 输入中未明确提到许可证，应输出 `[需核实:license]`。

**反模式 2：** "批量处理失败了，重新跑一遍就行"

**正确做法：** 定位失败文件，单独处理该文件，确认问题后再继续批量。

---

## 七、渐进式披露

### 7.1 速查卡（新手必读）

1. 准备输入（文件或 URL）
2. 单条试运行
3. 检查输出字段
4. 批量执行
5. 抽查校验

### 7.2 分层次阅读路径

**新手路径：**

1. 阅读「能力边界」了解适用范围
2. 阅读「标准流程」按步骤操作
3. 遇到问题查阅「错误码体系」

**进阶路径：**

1. 阅读「置信度门控」理解字段处理逻辑
2. 阅读「FAQ 反模式」避免常见错误
3. 自定义输出模板（需额外配置）

---

## 八、参数参考表

| 参数名 | 类型 | 必填 | 默认值 | 说明 |
|--------|------|------|--------|------|
| `--input` | string | 是 | 无 | 输入文件路径或 URL |
| `--batch` | boolean | 否 | false | 批量处理模式 |
| `--output` | string | 否 | stdout | 输出文件路径 |
| `--format` | string | 否 | json | 输出格式（json/markdown） |
| `--selftest` | boolean | 否 | false | 自检模式 |
| `--version` | boolean | 否 | false | 显示版本信息 |

---

## 九、用户协议

<!-- user-agreement-injected -->

**使用本 Skill 即表示您同意以下条款：**

1. **责任承担**：使用者自行承担使用本 Skill 的全部责任。因使用本 Skill 产生的任何直接或间接损失，作者不承担任何责任。

2. **禁止反向工程**：不得对本 Skill 的提示词结构、处理逻辑进行反向工程、破解、篡改或二次分发用于商业用途。

3. **内容合规**：使用者不得利用本 Skill 处理违反法律法规或侵犯第三方权益的内容。

4. **无担保声明**：本 Skill 按"现状"提供，不对输出的准确性、完整性作任何明示或暗示的担保。

---

## 十、许可证（License）

<!-- professional-license-embedded -->

**MIT License**

Copyright (c) 2024 Kaiwu

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
