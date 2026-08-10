---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: cheat-sh-pro
name: cheat-sh-pro
displayName: 终端速查 代码示例 即时检索
description: 终端内即时获取编程语言与工具代码示例，支持模糊搜索、领域过滤、随机速查与 Markdown 导出，开发调试零切换。
version: 3.0.1
rules_version: cpr-20260810-n301
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/cheat-sh-pro
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: linq-cli
agent_created: true
trigger_words: ["cheat.sh", "命令行速查", "代码示例查询", "终端查手册", "命令速查", "终端速查", "代码片段检索", "命令行手册"]

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# cheat-sh-pro — 终端代码速查专家

## 一、能力边界（一页纸速查卡）

### 1.1 能做什么

| 能力项 | 说明 | 示例 |
|--------|------|------|
| 代码示例查询 | 按语言/工具名检索代码片段 | `python 文件读取` |
| 模糊搜索 | 支持部分关键词匹配 | `py 列表推导` |
| 领域过滤 | 按语言、框架、工具限定范围 | `python:flask 路由` |
| 随机速查 | 随机获取一条示例 | `--random` |
| Markdown 导出 | 将查询结果保存为 .md 文件 | `--export md` |
| 多语言支持 | 覆盖主流编程语言与 CLI 工具 | `go`, `rust`, `docker` 等 |

### 1.2 不能做什么

| 限制项 | 说明 |
|--------|------|
| 不执行代码 | 仅返回示例文本，不运行任何代码 |
| 不保证示例可运行性 | 示例可能依赖特定版本或环境 |
| 不提供完整项目脚手架 | 仅返回片段，不生成项目结构 |
| 不替代官方文档 | 示例为速查用途，细节请查阅官方文档 |
| 不支持离线查询 | 需要网络连接以获取最新示例 |

### 1.3 适用对象

- 日常使用终端的开发者
- 需要快速回忆 API 用法的工程师
- 学习新语言/框架时希望快速上手的学习者
- 在调试过程中需要即时参考的运维人员

---

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->


## 二、触发方式

### 2.1 触发词

| 触发词 | 场景描述 |
|--------|----------|
| `cheat.sh` | 直接调用工具 |
| `命令行速查` | 需要命令行相关速查 |
| `代码示例查询` | 需要某语言/工具的代码示例 |
| `终端查手册` | 希望在终端内查手册 |
| `命令速查` | 需要命令用法速查 |
| `终端速查` | 终端内速查场景 |
| `代码片段检索` | 检索代码片段 |
| `命令行手册` | 命令行手册查询 |

### 2.2 场景映射表

| 大白话场景 | 实际触发方式 | 预期输出 |
|------------|--------------|----------|
| "我想看看 Python 怎么读文件" | `cheat.sh python 文件读取` | 返回 Python 文件读取示例 |
| "Docker 怎么查看日志？" | `cheat.sh docker logs` | 返回 docker logs 用法 |
| "给我随便来个代码示例" | `cheat.sh --random` | 随机返回一条示例 |
| "把结果存下来" | `cheat.sh python 列表 --export md` | 生成 Markdown 文件 |
| "只查 Flask 的路由写法" | `cheat.sh python:flask 路由` | 返回 Flask 路由示例 |

---

## 三、标准流程

### 3.1 前置条件

| 条件 | 要求 |
|------|------|
| 网络连接 | 必须可用，用于获取远程示例库 |
| 终端环境 | 支持标准输入输出，建议 UTF-8 编码 |
| 工具版本 | 建议使用最新版本（可通过 `--version` 检查） |

### 3.2 执行步骤

1. **输入查询**：在终端输入 `cheat.sh` 后跟查询关键词。
   ```
   cheat.sh python 文件读取
   ```

2. **（可选）指定领域**：使用 `语言:框架` 格式限定范围。
   ```
   cheat.sh python:flask 路由
   ```

3. **（可选）使用过滤参数**：
   | 参数 | 作用 | 示例 |
   |------|------|------|
   | `--lang <语言>` | 指定语言 | `--lang python` |
   | `--tool <工具>` | 指定工具 | `--tool docker` |
   | `--random` | 随机获取 | `--random` |
   | `--export md` | 导出 Markdown | `--export md` |

4. **查看输出**：终端会显示匹配的代码示例，包含简要说明。

5. **（可选）导出结果**：使用 `--export md` 将结果保存为 Markdown 文件，默认保存到当前目录。

### 3.3 输出规范

| 输出项 | 格式 | 说明 |
|--------|------|------|
| 示例标题 | `### 示例：<查询关键词>` | 明确标识示例内容 |
| 语言标识 | `语言：<语言名>` | 标明示例所属语言 |
| 代码块 | 使用 Markdown 代码块包裹 | 便于阅读和复制 |
| 说明文字 | 简短描述示例用途 | 帮助理解示例上下文 |
| 导出文件 | `cheat_<时间戳>.md` | 导出文件命名规则 |

---

## 四、置信度门控

### 4.1 信息不足时的处理

当查询结果不明确或信息不足时，系统会输出以下占位符：

| 占位符 | 含义 | 使用场景 |
|--------|------|----------|
| `[需核实:语言]` | 语言信息不确定 | 查询未指定语言且结果不明确 |
| `[需核实:版本]` | 版本信息不确定 | 示例依赖特定版本 |
| `[需核实:参数]` | 参数信息不确定 | 示例参数不完整 |
| `[需核实:来源]` | 来源不确定 | 无法确认示例来源 |

### 4.2 处理原则

- **不编造**：当信息不足时，明确输出占位符，不猜测。
- **提示核实**：输出占位符的同时，提示用户查阅官方文档。
- **提供备选**：如果可能，提供相近的替代查询建议。

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| `E001` | 网络连接失败 | "无法连接到示例库，请检查网络连接" | 1. 检查网络；2. 重试查询 |
| `E002` | 查询无结果 | "未找到匹配的示例，请尝试其他关键词" | 1. 更换关键词；2. 使用模糊搜索 |
| `E003` | 语言不支持 | "该语言暂不支持，请查看支持列表" | 1. 使用 `--list-langs` 查看支持语言 |
| `E004` | 导出失败 | "导出文件失败，请检查目录权限" | 1. 检查目录权限；2. 更换导出路径 |
| `E005` | 参数错误 | "参数格式不正确，请查看帮助" | 1. 使用 `--help` 查看参数说明 |
| `E006` | 版本过旧 | "当前版本过旧，建议更新" | 1. 使用 `--version` 查看版本；2. 更新工具 |

---

## 六、FAQ 反模式

### 6.1 常见坑

| 坑 | 反模式 | 正确做法 |
|----|--------|----------|
| 查询太宽泛 | 只输入 `python` 就期望得到具体示例 | 添加具体功能词，如 `python 文件读取` |
| 忽略领域过滤 | 查询 `flask 路由` 但未指定语言 | 使用 `python:flask 路由` 精确匹配 |
| 依赖过时示例 | 使用旧版本示例导致运行失败 | 查看示例中的版本信息，确认兼容性 |
| 忽略导出格式 | 导出后文件无法正常打开 | 使用 `--export md` 确保格式正确 |
| 不检查网络 | 离线状态下查询报错 | 先确认网络连接，再执行查询 |

### 6.2 反模式对照表

| 反模式 | 问题 | 替代方案 |
|--------|------|----------|
| 盲目复制示例 | 示例可能不适用于当前环境 | 理解示例逻辑后自行调整 |
| 过度依赖速查 | 速查无法替代深入学习 | 结合官方文档系统学习 |
| 忽略错误提示 | 错误码被忽略导致问题持续 | 根据错误码提示进行修正 |
| 不更新工具 | 旧版本功能受限 | 定期检查并更新工具 |

---

## 七、渐进式披露

### 7.1 速查卡（新手必读）

```
cheat.sh <关键词>          # 基础查询
cheat.sh python 文件读取    # 指定语言查询
cheat.sh --random          # 随机示例
cheat.sh --help            # 查看帮助
```

### 7.2 分层次阅读路径

#### 新手路径（5 分钟上手）

1. 阅读「能力边界」了解工具范围
2. 使用 `cheat.sh <关键词>` 进行第一次查询
3. 查看「FAQ 反模式」避免常见错误

#### 进阶路径（深入使用）

1. 掌握「领域过滤」语法，精确查询
2. 使用「导出功能」保存常用示例
3. 结合「错误码体系」排查问题
4. 定期更新工具，获取最新示例

#### 专家路径（高效工作流）

1. 将常用查询保存为别名
2. 结合脚本自动化查询流程
3. 使用 `--export md` 建立个人知识库
4. 参与示例库贡献，完善速查内容

---

## 八、参数速查表

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `--lang` | string | 无 | 指定查询语言 |
| `--tool` | string | 无 | 指定查询工具 |
| `--random` | boolean | false | 随机获取示例 |
| `--export` | string | 无 | 导出格式（md） |
| `--list-langs` | boolean | false | 列出支持的语言 |
| `--version` | boolean | false | 显示版本信息 |
| `--selftest` | boolean | false | 运行自检 |
| `--help` | boolean | false | 显示帮助信息 |

---

## 九、用户协议

<!-- user-agreement-injected -->

**使用前请仔细阅读以下条款：**

1. **责任承担**：使用者自行承担使用本 Skill 的全部责任。因使用本 Skill 产生的任何直接或间接损失，作者不承担任何责任。
2. **禁止反向工程**：禁止对本 Skill 进行反向工程、反编译、破解或试图获取源代码。
3. **合法使用**：使用者应遵守所在地法律法规，不得将本 Skill 用于任何非法用途。
4. **内容准确性**：本 Skill 提供的示例仅供参考，使用者应自行核实内容的准确性和适用性。
5. **服务变更**：作者保留随时修改、更新或终止本 Skill 的权利，恕不另行通知。

---

## 十、许可证（License）

<!-- professional-license-embedded -->

**MIT License**

Copyright (c) 2026 linq-cli

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
