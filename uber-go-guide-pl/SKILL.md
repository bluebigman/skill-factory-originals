---
slug: uber-go-guide-pl
name: uber-go-guide-pl
displayName: Go编码规范 工程实践 代码审查
description: 解析Uber Go风格指南，输出结构化规范摘要与代码审查要点。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: code-craftsman
agent_created: true
trigger_words: ["uber-go-guide-pl", "Uber Go风格指南", "Go编码规范", "Go代码审查", "Go最佳实践"]

> 本内容由 AI 生成，仅供学习参考 <!-- ai-generated-notice -->

---

# Uber Go 风格指南解析与工程实践 Skill

## 一、能力边界速查卡

### 1.1 能做与不能做

| 维度 | 能做 | 不能做 |
|------|------|--------|
| 输入处理 | 接受用户提供的 Go 源码片段、代码审查清单、规范问题描述 | 不接受二进制文件、非文本格式输入 |
| 规范解析 | 将 Uber Go 风格指南条款拆解为可执行要点，输出结构化摘要 | 不替代官方文档，不生成完整规范原文 |
| 代码审查 | 基于规范条款对代码片段进行逐条比对，输出问题清单与修改建议 | 不执行静态分析，不保证发现所有潜在缺陷 |
| 输出格式 | 支持 Markdown 表格、列表、JSON 三种格式 | 不支持 PDF、Word 等富文本格式 |
| 批量处理 | 支持多文件批量解析，输出汇总报告 | 不支持跨语言混排分析 |

### 1.2 适用对象

- **Go 初学者**：需要快速掌握 Uber Go 风格指南核心条款
- **团队技术负责人**：制定代码审查规范时需要参考依据
- **代码审查者**：审查 Go 代码时需要对照规范条款
- **培训讲师**：准备 Go 编码规范培训材料

---

## 二、触发方式与场景映射

| 触发词/场景 | 用户意图 | 本 Skill 响应 |
|-------------|----------|---------------|
| "帮我看看这段代码符合 Uber Go 规范吗" | 代码审查 | 逐条比对规范，输出问题清单 |
| "Uber Go 风格指南里关于错误处理怎么说" | 条款查询 | 提取错误处理相关条款，结构化输出 |
| "写 Go 代码时 interface 应该怎么用" | 最佳实践咨询 | 给出 interface 使用规范要点与示例 |
| "这份代码审查报告帮我按 Uber 规范整理" | 报告整理 | 将审查意见映射到规范条款 |
| "uber-go-guide-pl" | 直接触发 | 进入标准处理流程 |

---

## 三、标准处理流程

### 3.1 前置条件

| 条件项 | 要求 | 检查方式 |
|--------|------|----------|
| 输入格式 | 纯文本或 Markdown 格式的 Go 代码/问题描述 | 文件扩展名或内容预览 |
| 编码 | UTF-8 | 文件头检查 |
| 文件命名 | 建议使用 `*.go`、`*.md`、`*.txt` 后缀 | 文件名检查 |
| 内容完整性 | 代码片段需包含完整函数或类型定义 | 人工确认 |

### 3.2 执行步骤

**步骤 1：输入解析**

- 读取用户提供的代码片段或问题描述
- 识别代码语言版本（Go 1.15+ 与旧版规范有差异）
- 提取关键要素：函数签名、类型定义、错误处理模式、并发结构

**步骤 2：规范匹配**

- 将输入内容与 Uber Go 风格指南条款进行映射
- 匹配维度包括：命名规范、错误处理、并发安全、性能优化、代码组织
- 每条匹配结果标注：规范条款编号、符合/不符合、严重程度

**步骤 3：结果生成**

- 按约定格式输出分析结果
- 每条问题包含：位置定位、违反条款、修改建议、优先级
- 置信度标注规则见 3.4 节

**步骤 4：自查与确认**

- 检查输出字段完整性：问题描述、条款引用、建议方案
- 检查格式正确性：Markdown 表格对齐、JSON 语法
- 置信度低于 0.7 的条目主动向用户二次确认

### 3.3 输出规范

**Markdown 格式示例：**

```markdown
## 代码审查结果

### 问题清单

| 序号 | 位置 | 问题描述 | 违反条款 | 优先级 | 置信度 |
|------|------|----------|----------|--------|--------|
| 1 | 第 15 行 | 错误处理缺失 | 错误处理章节 | 高 | 0.95 |
| 2 | 第 28 行 | 命名不符合驼峰式 | 命名规范章节 | 中 | 0.88 |

### 修改建议

1. 第 15 行：添加 `if err != nil` 检查
2. 第 28 行：将 `user_id` 改为 `userID`
```

**JSON 格式示例：**

```json
{
  "review_results": [
    {
      "line": 15,
      "issue": "missing error handling",
      "rule_ref": "error-handling",
      "priority": "high",
      "confidence": 0.95
    }
  ]
}
```

### 3.4 置信度门控

| 置信度区间 | 标注方式 | 处理策略 |
|------------|----------|----------|
| 0.9 - 1.0 | 直接输出 | 正常展示 |
| 0.7 - 0.9 | 标注"较确定" | 正常展示，附说明 |
| 0.5 - 0.7 | 标注"需核实" | 输出 `[需核实:字段名]` 占位 |
| < 0.5 | 不输出 | 向用户说明信息不足 |

**信息不足时的处理：**

- 当代码片段缺少函数签名时，输出 `[需核实:函数签名]`
- 当无法确定 Go 版本时，输出 `[需核实:Go版本]`
- 当规范条款存在歧义时，输出 `[需核实:条款解释]`

---

## 四、错误码体系

| 错误码 | 错误描述 | 提示话术 | 修正步骤 |
|--------|----------|----------|----------|
| E001 | 输入为空 | "未检测到有效输入，请提供代码片段或问题描述" | 1. 检查输入内容 2. 重新提交 |
| E002 | 输入格式不支持 | "仅支持文本或 Markdown 格式，请转换后重试" | 1. 转换格式 2. 重新提交 |
| E003 | 规范条款匹配失败 | "未能将输入映射到 Uber Go 规范条款，请补充上下文" | 1. 补充代码上下文 2. 重新提交 |
| E004 | 输出格式冲突 | "检测到多个输出格式请求，请指定单一格式" | 1. 确认输出格式 2. 重新提交 |
| E005 | 批量处理中断 | "批量处理在第 N 个文件处中断，请检查该文件格式" | 1. 检查第 N 个文件 2. 修复后重试 |

---

## 五、FAQ 与反模式对照

### 5.1 常见坑

| 坑位描述 | 反模式示例 | 正确做法 |
|----------|------------|----------|
| 过度依赖规范 | 认为 Uber Go 规范适用于所有 Go 项目 | 根据项目实际情况调整，规范是参考不是教条 |
| 忽略版本差异 | 用旧版规范审查新版 Go 代码 | 确认 Go 版本，使用对应规范版本 |
| 机械套用 | 所有错误都必须立即返回，不考虑上下文 | 理解错误处理的设计意图，灵活应用 |
| 忽视性能影响 | 为符合规范而牺牲明显性能 | 在规范与性能之间寻找平衡点 |
| 跳过置信度检查 | 对不确定的结论直接输出 | 使用 `[需核实:字段]` 标注不确定项 |

### 5.2 反模式对照表

| 反模式 | 问题 | 替代方案 |
|--------|------|----------|
| "规范说必须这样做" | 绝对化，缺乏灵活性 | "规范建议这样做，但需结合上下文判断" |
| "这段代码完全不符合规范" | 一刀切，忽略合理部分 | "这段代码有 N 处不符合规范，具体如下..." |
| "按规范改就对了" | 忽略业务场景 | "建议按规范调整，同时考虑业务影响" |

---

## 六、渐进式披露路径

### 6.1 速查卡（30 秒上手）

1. 准备 Go 代码片段或规范问题
2. 输入触发词或直接描述需求
3. 接收结构化分析结果
4. 按置信度标注处理不确定项

### 6.2 新手路径（首次使用）

1. 阅读本速查卡了解能力边界
2. 使用单个代码片段试运行
3. 核对输出格式与字段含义
4. 逐步增加输入复杂度

### 6.3 进阶路径（熟练用户）

1. 掌握置信度门控机制，理解不确定项处理
2. 使用批量处理功能，提高审查效率
3. 结合错误码体系，快速定位处理问题
4. 自定义输出格式，适配团队工作流

---

## 七、批量处理指南

### 7.1 准备阶段

- 将待处理文件放入同一目录
- 确认文件命名规范一致（建议 `*.go` 或 `*.md`）
- 创建输出目录，用于存放结果文件

### 7.2 试运行

- 选取 1-2 个代表性文件执行
- 核对输出字段与格式是否符合预期
- 确认置信度标注是否合理

### 7.3 批量执行

- 对全量文件执行处理
- 保留原始文件备份
- 生成汇总报告

### 7.4 结果校验

- 抽查 10% 输出条目
- 核对关键字段与源数据一致性
- 确认置信度标注准确性

---

## 八、用户协议

使用本 Skill 即表示您同意以下条款：

1. **责任承担**：使用者自行承担全部责任。本 Skill 提供的所有输出仅供参考，不构成任何形式的专业建议或保证。
2. **禁止反向工程**：严禁对本 Skill 进行反向工程、反编译、破解或任何形式的未授权访问。
3. **合规使用**：使用者应确保使用方式符合当地法律法规及所在组织的政策要求。
4. **免责声明**：本 Skill 由 AI 辅助生成，可能存在不准确或不完整之处，使用者应结合实际情况判断。

<!-- user-agreement-injected -->

---

## 九、许可证（License）

本 Skill 采用 MIT 许可证发布：

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

---

*本 Skill 由 AI 辅助生成，仅供参考。使用前请阅读相关文档。*
