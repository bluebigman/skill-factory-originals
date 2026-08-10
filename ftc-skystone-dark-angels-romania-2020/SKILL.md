---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: ftc-skystone-dark-angels-romania-2020
name: ftc-skystone-dark-angels-romania-2020
displayName: FTC机器人 代码审查 结构解析
description: 解析FTC机器人项目结构，识别模块依赖，检查规范并生成审查报告。
version: 2.0.1
rules_version: cpr-20260810-n301
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/ftc-skystone-dark-angels-romania-2020
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: CodeForge Studio
agent_created: true
trigger_words: ["代码审查", "FTC", "SKYSTONE", "机器人代码", "结构解析", "OpMode分析", "依赖梳理"]
---

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->


> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# FTC SKYSTONE 机器人代码审查 Skill

## 一、能力边界（一页纸速查卡）

### 1.1 能做什么

| 能力项 | 说明 | 输出物 |
|--------|------|--------|
| 项目结构解析 | 扫描项目目录，识别 Java/Kotlin 源码文件，按功能模块归类 | 模块清单树 |
| OpMode 识别 | 找出所有继承 `OpMode` / `LinearOpMode` 的类，标注注册状态 | OpMode 清单 |
| 硬件映射梳理 | 识别 `HardwareMap` 的调用点，提取设备名称与类型 | 硬件映射表 |
| 依赖关系分析 | 解析类之间的继承、组合、引用关系，绘制依赖图 | 依赖关系说明 |
| 规范检查 | 检查命名规范、注释覆盖率、魔法数字、空指针风险 | 问题清单 |
| 风险标注 | 识别可能导致运行时崩溃或逻辑错误的代码模式 | 风险报告 |

### 1.2 不能做什么

| 限制项 | 说明 |
|--------|------|
| 不执行代码 | 不运行、编译或调试任何机器人代码 |
| 不连接硬件 | 不连接 FTC 控制台或机器人硬件 |
| 不修改源码 | 只读分析，不提供自动修复补丁 |
| 不保证发现所有问题 | 静态分析存在盲区，动态问题需实测 |
| 不替代人工审查 | 输出作为辅助参考，最终判断由工程师完成 |

### 1.3 适用对象

- FTC 机器人竞赛队伍（尤其是 SKYSTONE 赛季）
- 接手他人项目的开发者
- 需要代码审查的团队负责人
- 教学场景中的代码质量评估

---

## 二、触发方式

### 2.1 触发词

- 代码审查
- FTC
- SKYSTONE
- 机器人代码
- 结构解析
- OpMode分析
- 依赖梳理
- 硬件映射检查

### 2.2 场景映射表

| 用户说（大白话） | 实际触发动作 |
|------------------|--------------|
| "帮我看看这个 FTC 项目的代码结构" | 执行项目结构解析，输出模块清单 |
| "这个机器人代码有没有问题？" | 执行规范检查 + 风险标注 |
| "我想知道有哪些 OpMode 可以用" | 识别 OpMode 清单及注册状态 |
| "硬件配置在哪里？帮我理一下" | 提取硬件映射表 |
| "两个类之间是什么关系？" | 分析依赖关系并说明 |

---

## 三、标准流程

### 3.1 前置条件

| 条件 | 要求 |
|------|------|
| 项目路径 | 提供可访问的本地目录路径 |
| 源码语言 | Java 或 Kotlin（FTC 官方模板为 Java） |
| 目录结构 | 建议包含 `TeamCode/src/main/java` 标准结构 |
| 权限 | 具备读取目录和文件的权限 |

### 3.2 执行步骤

**步骤 1：项目扫描**

```
输入：项目根目录路径
操作：递归扫描所有 .java / .kt 文件
输出：文件清单（路径、大小、行数）
```

**步骤 2：模块分类**

按以下规则将文件归类：

| 模块类型 | 判定规则 |
|----------|----------|
| OpMode | 继承 `OpMode` 或 `LinearOpMode` |
| 硬件类 | 类名含 `Hardware`、`Device`、`Motor`、`Servo` 等 |
| 工具类 | 类名含 `Util`、`Helper`、`Util`、`Math` 等 |
| 配置类 | 含 `Config`、`Constants`、`Parameters` 等 |
| 其他 | 无法归类的辅助类 |

**步骤 3：OpMode 识别**

- 提取所有 OpMode 类名
- 检查 `@TeleOp` / `@Autonomous` 注解
- 标注是否注册（有注解 = 已注册）

**步骤 4：硬件映射提取**

- 搜索 `hardwareMap.get(` 调用
- 提取设备名称（字符串参数）和类型（泛型参数）
- 汇总为硬件映射表

**步骤 5：依赖分析**

- 解析每个类的 `import` 语句和字段声明
- 识别继承关系（`extends`）
- 识别接口实现（`implements`）
- 识别组合关系（字段类型引用）

**步骤 6：规范检查**

| 检查项 | 规则 | 违规示例 |
|--------|------|----------|
| 类名命名 | 大驼峰 | `myClass` |
| 方法命名 | 小驼峰 | `My_Method` |
| 常量命名 | 全大写+下划线 | `maxSpeed` |
| 魔法数字 | 禁止裸数字 | `if (x > 5)` |
| 注释覆盖率 | 关键方法必须有注释 | 无注释的复杂逻辑 |
| 空指针风险 | 字段使用前必须判空 | `motor.setPower()` 前未检查 null |

**步骤 7：风险标注**

- 识别 `try-catch` 缺失的异常风险
- 识别无限循环风险（`while(true)` 无退出条件）
- 识别资源未释放（如 `close()` 未调用）
- 识别线程安全问题（共享变量无同步）

**步骤 8：生成报告**

按以下模板输出 Markdown 报告：

```markdown
# FTC 代码审查报告

## 项目概览
- 项目名称：[项目名]
- 审查时间：[时间戳]
- 文件总数：[N] 个
- 代码总行数：[N] 行

## 模块清单
[模块树形结构]

## OpMode 清单
| 类名 | 类型 | 注册状态 |
|------|------|----------|
| ...  | ...  | ...      |

## 硬件映射表
| 设备名 | 类型 | 使用位置 |
|--------|------|----------|
| ...    | ...  | ...      |

## 依赖关系
[依赖说明]

## 规范检查结果
[问题清单]

## 风险标注
[风险列表]

## 改进建议
[按优先级排序的建议]
```

### 3.3 输出规范

- 报告必须包含时间戳（格式：`YYYY-MM-DD HH:mm:ss`）
- 所有问题必须标注严重级别：🔴 严重 / 🟡 警告 / 🔵 建议
- 每个问题必须给出文件路径和行号
- 建议按优先级排序（高 → 低）

---

## 四、置信度门控

### 4.1 信息不足时的处理

当遇到以下情况，输出 `[需核实:字段]` 占位符，不编造信息：

| 场景 | 占位符示例 |
|------|------------|
| 无法确定设备类型 | `[需核实:设备类型]` |
| 无法确定注册状态 | `[需核实:注册状态]` |
| 无法解析依赖关系 | `[需核实:依赖关系]` |
| 无法确定风险等级 | `[需核实:风险等级]` |

### 4.2 禁止行为

- 不猜测未在代码中出现的硬件设备
- 不推断未明确声明的类关系
- 不假设未注册的 OpMode 可运行
- 不编造不存在的文件或行号

---

## 五、错误码体系

| 错误码 | 错误描述 | 提示话术 | 修正步骤 |
|--------|----------|----------|----------|
| E001 | 项目路径不存在 | "指定的路径不存在，请检查路径是否正确" | 1. 确认路径拼写 2. 检查目录权限 3. 重新输入 |
| E002 | 目录中无源码文件 | "未找到任何 .java 或 .kt 文件" | 1. 确认项目结构 2. 检查是否在正确子目录 3. 确认源码文件后缀 |
| E003 | 无法读取文件 | "文件读取失败，可能被占用或无权限" | 1. 关闭占用程序 2. 检查文件权限 3. 复制到可读目录 |
| E004 | 解析语法错误 | "源码存在语法错误，无法完整解析" | 1. 定位语法错误位置 2. 修复后重新扫描 3. 或跳过该文件 |
| E005 | 依赖分析失败 | "存在无法解析的类引用，依赖图不完整" | 1. 检查缺失的 import 2. 确认外部库路径 3. 手动补充依赖信息 |
| E006 | 输出目录不可写 | "无法写入报告文件，请检查输出目录权限" | 1. 更换输出目录 2. 修改目录权限 3. 使用默认输出位置 |

---

## 六、FAQ 反模式

### 6.1 常见坑

| 坑 | 反模式描述 | 正确做法 |
|----|------------|----------|
| 坑 1 | 只扫描 `TeamCode` 目录，忽略 `FtcRobotController` 中的共享代码 | 全项目扫描，包括库文件 |
| 坑 2 | 把所有 `OpMode` 都当作已注册 | 必须检查 `@TeleOp` / `@Autonomous` 注解 |
| 坑 3 | 忽略 `HardwareMap` 中的设备名大小写 | 设备名区分大小写，需精确匹配 |
| 坑 4 | 把 `LinearOpMode` 和 `OpMode` 混为一谈 | 两者生命周期不同，需分开分析 |
| 坑 5 | 只关注编译错误，忽略逻辑风险 | 静态分析应同时关注运行时风险 |

### 6.2 反模式对照表

| 反模式 | 问题 | 替代方案 |
|--------|------|----------|
| 一次性扫描所有文件 | 输出冗长，重点不突出 | 分模块扫描，按优先级输出 |
| 只输出问题不输出建议 | 用户不知道如何修复 | 每个问题附带修复建议 |
| 忽略代码注释 | 无法理解设计意图 | 结合注释分析代码逻辑 |
| 不区分严重级别 | 用户无法判断优先级 | 按 🔴🟡🔵 分级标注 |
| 不保留历史报告 | 无法对比项目演进 | 每次生成带时间戳的报告 |

---

## 七、渐进式披露

### 7.1 速查卡（新手必读）

```
1. 提供项目路径 → 2. 执行扫描 → 3. 获取报告
报告包含：模块清单、OpMode 清单、硬件映射、风险标注
```

### 7.2 分层次阅读路径

**新手路径（5 分钟）**

1. 阅读「项目概览」了解整体规模
2. 查看「OpMode 清单」确认可用的操作模式
3. 查看「风险标注」了解最严重的问题

**进阶路径（15 分钟）**

1. 阅读「模块清单」理解项目架构
2. 查看「硬件映射表」确认设备配置
3. 阅读「依赖关系」理解类之间的耦合
4. 逐条查看「规范检查结果」并修复问题

**专家路径（30 分钟）**

1. 完整阅读报告所有章节
2. 结合源码逐条验证问题
3. 制定修复计划并按优先级执行
4. 修复后重新生成报告对比改进

---

## 八、使用建议

### 8.1 最佳实践

- 在项目开发早期就进行代码审查，避免问题积累
- 每次重大修改后重新生成报告，跟踪代码质量变化
- 将报告纳入团队代码评审流程
- 结合人工审查，工具输出作为辅助参考

### 8.2 注意事项

- 本工具不替代编译器和调试器
- 静态分析无法发现所有运行时问题
- 硬件相关问题需在真实设备上验证
- 报告中的建议需结合项目实际情况判断

---

## 九、用户协议

<!-- user-agreement-injected -->

**使用本 Skill 即表示您同意以下条款：**

1. **责任承担**：使用者自行承担因使用本 Skill 产生的全部责任。本 Skill 提供的分析结果仅供参考，不构成任何形式的保证或承诺。

2. **禁止反向工程**：不得对本 Skill 的提示词、内部逻辑、生成机制进行反向工程、破解、篡改或二次分发。

3. **合规使用**：使用者应确保使用场景符合当地法律法规及 FTC 竞赛规则。

4. **免责声明**：本 Skill 不保证分析结果的完整性、准确性或适用性。因使用本 Skill 导致的任何直接或间接损失，作者不承担任何责任。

---

## 十、许可证（License）

<!-- professional-license-embedded -->

**MIT License**

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

---

*本 Skill 由 AI 辅助生成，仅供参考。使用前请阅读相关文档。*
