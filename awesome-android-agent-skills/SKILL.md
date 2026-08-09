---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: awesome-android-agent-skills
name: awesome-android-agent-skills
displayName: Android开发 智能体技能包 现代工程实践
description: 面向AI编程助手的现代Android开发技能集合，覆盖架构、测试与工具链。
version: 1.0.1
rules_version: cpr-20260809-n251
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/awesome-android-agent-skills
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: DevSkillForge
agent_created: true
trigger_words: ["android","android development","android dev","android 开发","android 技能","android 最佳实践","android 架构","android 工具链"]
---

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->


> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# awesome-android-agent-skills

## 一、能力边界：一页纸速查卡

本技能包旨在为 AI 编程助手（如 GitHub Copilot、Claude、Gemini、Cursor）提供一套标准化的现代 Android 开发知识索引与操作指引。它不是一个代码生成器，而是一个“知识导航员”和“实践规范库”。

### 1.1 能做（核心能力）

| 编号 | 能力项 | 说明与示例 |
|------|--------|------------|
| C1 | **技术栈导航** | 根据用户问题（如“我想用 Kotlin 写一个网络请求层”），推荐对应的现代库（Retrofit / Ktor）、架构模式（MVVM / MVI）及官方文档入口。 |
| C2 | **项目结构解析** | 输入一个 Android 项目的目录树或关键文件（如 `build.gradle.kts`），输出对该项目模块划分、依赖管理、构建配置的解读。 |
| C3 | **最佳实践问答** | 针对“如何处理配置变更”“如何做依赖注入”“Compose 状态提升”等高频问题，给出符合 2025 年后 Android 官方推荐的标准答案与代码范式。 |
| C4 | **代码审查辅助** | 提供一段代码（如一个 ViewModel 或 Repository），输出基于官方规范（如 Kotlin 风格、协程使用、生命周期安全）的审查意见清单。 |
| C5 | **工具链指引** | 解释 Gradle 配置、AGP（Android Gradle Plugin）版本选择、R8/ProGuard 规则、Baseline Profile 生成等工具链相关问题。 |

### 1.2 不能做（明确边界）

| 编号 | 限制项 | 说明 |
|------|--------|------|
| L1 | **不执行代码** | 本技能不连接终端或模拟器，无法运行、编译或调试任何代码。 |
| L2 | **不提供实时数据** | 不查询 Maven Central 或 Google Maven 的最新版本号，版本信息需用户自行确认或提供。 |
| L3 | **不替代官方文档** | 对于 API 的精确签名或行为，以 [developer.android.com](https://developer.android.com) 为准，本技能提供的是思路与索引。 |
| L4 | **不处理非 Android 问题** | 不解答通用 JVM、前端或后端开发问题，除非与 Android 开发强相关。 |

### 1.3 适用对象

- **AI 助手**：作为系统提示词或工具描述的一部分，增强对 Android 领域的理解。
- **开发者**：作为学习路径图或快速查阅手册，了解当前 Android 开发的主流实践。
- **技术管理者**：用于评估团队技术栈是否符合现代 Android 工程标准。

---

## 二、触发方式：场景映射表

当用户输入包含以下关键词或意图时，本技能应被激活。

| 触发词/场景 | 用户可能说的话（大白话） | 技能响应动作 |
|-------------|--------------------------|--------------|
| `android` / `android dev` | “帮我看看这个 Android 项目结构合不合理。” | 执行 C2（项目结构解析） |
| `android 架构` | “ViewModel 和 Flow 应该怎么配合用？” | 执行 C3（最佳实践问答） |
| `android 工具链` | “AGP 8.5 和 Gradle 8.9 搭配有没有坑？” | 执行 C5（工具链指引） |
| `android 测试` | “写单元测试时怎么 mock 掉 `Context`？” | 执行 C3（最佳实践问答） |
| `android 代码审查` | “这段协程代码有没有内存泄漏风险？” | 执行 C4（代码审查辅助） |
| `android 技能` / `android 最佳实践` | “给我列一下 2025 年 Android 开发的黄金标准。” | 执行 C1（技术栈导航） |

---

## 三、标准流程：从输入到输出

### 3.1 前置条件

- **输入**：用户需提供足够上下文。例如，询问架构问题时，最好附带相关代码片段或项目结构描述。
- **环境**：无需特定环境，纯文本交互即可。

### 3.2 执行步骤（分步编号）

1. **意图识别**：解析用户输入，匹配 `trigger_words` 或语义相近的表达，确定核心需求属于 C1-C5 中的哪一类。
2. **信息收集**：检查输入是否包含必要信息（如代码、版本号、具体报错）。若信息不足，进入“置信度门控”流程。
3. **知识检索**：从内置的知识库（即本技能文档的后续章节及关联的参考文档索引）中检索相关内容。
4. **方案生成**：根据检索结果，组织回答。回答结构遵循“结论先行、分点阐述、代码示例、参考链接”的格式。
5. **输出规范**：按 3.3 节要求格式化输出。

### 3.3 输出规范

- **格式**：Markdown 格式，代码块需标注语言（如 `kotlin`、`groovy`）。
- **结构**：
  - **直接回答**：用 1-2 句话直接回应核心问题。
  - **详细解释**：分点列出步骤、原因或对比。
  - **代码示例**：提供可运行的 Kotlin/Groovy 代码片段。
  - **参考链接**：附上官方文档或权威博客链接。
- **长度**：根据问题复杂度调整，简单问题 200-500 字，复杂问题 800-1500 字。

---

## 四、置信度门控：不编造，不猜测

当遇到以下情况时，必须使用占位符 `[需核实:字段]`，并明确告知用户信息缺口。

| 场景 | 处理方式 | 示例话术 |
|------|----------|----------|
| **版本号不确定** | 不提供具体版本号，引导用户查询官方发布页。 | “关于 AGP 的最新稳定版本，我无法实时确认，请查阅 [AGP 发布说明](https://developer.android.com/build/releases/gradle-plugin) 获取 `[需核实:AGP版本号]`。” |
| **API 行为不确定** | 不猜测 API 的具体行为，建议用户查阅官方 API 文档。 | “`remember` 在 Compose 中的具体重组行为，请参考 [官方文档](https://developer.android.com/jetpack/compose/state) 确认 `[需核实:特定API行为]`。” |
| **用户代码上下文缺失** | 不臆测用户代码逻辑，要求补充关键代码。 | “要分析内存泄漏，我需要看到你的 ViewModel 或 Fragment 中协程的创建方式，请补充 `[需核实:协程作用域代码]`。” |
| **第三方库用法** | 不编造第三方库的 API，提供官方文档链接。 | “关于 Ktor 的特定配置，请参考 [Ktor 官方文档](https://ktor.io/) 中的 `[需核实:具体配置项]`。” |

---

## 五、错误码体系：常见问题与修正

| 错误码 | 错误描述 | 提示话术 | 修正步骤 |
|--------|----------|----------|----------|
| `E-INPUT-001` | 输入为空或过于模糊 | “我无法理解你的需求。请提供更具体的问题，例如包含代码片段、报错信息或你尝试过的方案。” | 1. 引导用户提供代码或报错。2. 询问用户使用的技术栈（如 Compose 还是 View 系统）。 |
| `E-INPUT-002` | 输入内容与 Android 无关 | “这似乎不是 Android 开发相关的问题。本技能专注于 Android 领域，建议咨询其他资源。” | 1. 礼貌说明边界。2. 如果问题与 JVM 相关但非 Android，可建议用户去 Kotlin 官方社区。 |
| `E-KNOWLEDGE-001` | 知识库未覆盖该问题 | “这是一个非常具体或新兴的问题，我的知识库尚未覆盖。建议查阅官方文档或 Stack Overflow。” | 1. 提供官方文档搜索关键词。2. 建议用户将问题拆解为更小的子问题。 |
| `E-CONTEXT-001` | 用户未提供必要的代码上下文 | “要分析这个问题，我需要看到相关的代码片段（如 `build.gradle.kts` 或 ViewModel 类）。” | 1. 明确列出需要哪些文件。2. 等待用户补充后重新分析。 |
| `E-VERSION-001` | 涉及版本兼容性问题但未提供版本号 | “版本兼容性分析需要具体的版本号。请提供你的 AGP、Gradle 和 Kotlin 版本。” | 1. 告知用户如何查看版本号（`./gradlew --version`）。2. 等待用户提供后继续。 |

---

## 六、FAQ 反模式：常见坑与对照

| 常见坑（反模式） | 错误示例 | 正确做法（本技能推荐） |
|------------------|----------|------------------------|
| **过度依赖旧资料** | “AsyncTask 是官方推荐的异步方式。” | 明确告知 AsyncTask 已废弃，推荐 Kotlin Coroutines 或 Flow。 |
| **忽略生命周期安全** | “在 ViewModel 里直接用 `viewModelScope.launch` 就行，不用管取消。” | 强调 `viewModelScope` 会自动取消，但需注意在自定义 `CoroutineScope` 时必须手动处理取消逻辑。 |
| **盲目追求“最新”** | “直接用最新的 AGP 版本，肯定没问题。” | 提醒用户关注 AGP 与 Gradle 的兼容性矩阵，并建议阅读 Release Notes。 |
| **混淆 Compose 与 View 系统** | “在 Compose 里用 `findViewById` 就行。” | 明确指出 Compose 中不存在 `findViewById`，应使用 `remember` 和状态管理。 |
| **忽视构建优化** | “项目编译慢？加 `-Xmx4g` 到 Gradle JVM 参数就行。” | 建议先分析构建耗时（`--profile`），再针对性地启用配置缓存、增量编译等。 |

---

## 七、渐进式披露：分层次阅读路径

### 7.1 速查卡（30 秒上手）

- **核心定位**：Android 开发知识导航与规范库。
- **触发方式**：直接提问 Android 相关问题。
- **输出风格**：结论先行，附代码示例与官方链接。
- **最大价值**：帮你快速找到官方推荐方案，避免踩坑。

### 7.2 新手路径（首次使用）

1. 阅读本文件的「能力边界」章节，了解我能做什么、不能做什么。
2. 尝试提出一个简单的 Android 问题，例如：“Kotlin 协程怎么在 Android 里用？”
3. 观察我的回答结构，重点关注“参考链接”部分，养成查阅官方文档的习惯。
4. 遇到不确定的信息，我会明确标注 `[需核实:字段]`，请以此为准。

### 7.3 进阶路径（深度使用）

1. 利用「代码审查辅助」能力，将你的项目代码片段发给我，获取基于官方规范的审查意见。
2. 利用「工具链指引」能力，深入理解 Gradle 配置、R8 规则等高级主题。
3. 结合「标准流程」章节，将本技能的输出作为你技术决策的起点，而非终点。
4. 若发现我的知识有误或过时，请以官方文档为准，并反馈给我以便改进。

---

## 八、核心知识库索引（节选）

> 以下为本技能内置的部分核心知识索引，用于支撑上述能力。

### 8.1 现代 Android 技术栈推荐（2025+）

| 领域 | 推荐方案 | 官方入口 |
|------|----------|----------|
| UI 开发 | Jetpack Compose | [developer.android.com/jetpack/compose](https://developer.android.com/jetpack/compose) |
| 异步编程 | Kotlin Coroutines + Flow | [kotlinlang.org/docs/coroutines-guide.html](https://kotlinlang.org/docs/coroutines-guide.html) |
| 依赖注入 | Hilt | [developer.android.com/training/dependency-injection/hilt-android](https://developer.android.com/training/dependency-injection/hilt-android) |
| 网络请求 | Retrofit / Ktor Client | [square.github.io/retrofit](https://square.github.io/retrofit/) / [ktor.io](https://ktor.io/) |
| 本地存储 | Room | [developer.android.com/training/data-storage/room](https://developer.android.com/training/data-storage/room) |
| 导航 | Navigation Compose | [developer.android.com/develop/ui/compose/navigation](https://developer.android.com/develop/ui/compose/navigation) |
| 架构模式 | MVVM + MVI | [developer.android.com/topic/architecture](https://developer.android.com/topic/architecture) |
| 模块化 | 多 Module + Convention Plugins | [developer.android.com/build](https://developer.android.com/build) |

### 8.2 构建工具链关键版本兼容性（提示）

- **AGP 与 Gradle**：每个 AGP 版本都有对应的最低 Gradle 版本要求。升级 AGP 前，务必查阅 [官方兼容性表](https://developer.android.com/build/releases/gradle-plugin#updating-gradle)。
- **Kotlin 与 Compose**：Compose Compiler 与 Kotlin 版本强绑定，需使用匹配的 Compose Compiler 版本。建议使用 Kotlin 2.0+ 的 Compose Compiler Gradle Plugin。
- **JDK 版本**：AGP 8.x 要求 JDK 17 及以上。

### 8.3 代码审查要点清单（节选）

- **协程安全**：是否所有协程都在正确的 `CoroutineScope` 中启动？是否处理了取消？
- **生命周期安全**：是否在 `onDestroy` 中清理了非 ViewModel 持有的资源？
- **状态管理**：Compose 中是否使用了 `remember`/`mutableStateOf` 正确管理状态？是否避免了状态提升过度？
- **依赖注入**：是否通过 Hilt 管理依赖？是否避免了在 ViewModel 中直接 `new` 一个 Repository？
- **性能**：是否存在不必要的重组？`LazyColumn` 是否使用了正确的 `key`？

---

## 九、用户协议

<!-- user-agreement-injected -->

**使用本 Skill 即表示您同意以下条款：**

1. **责任承担**：使用者自行承担因使用本 Skill 及其输出内容（包括但不限于代码示例、技术建议、架构方案）而产生的全部责任。本 Skill 提供的所有信息仅供学习、研究和参考之用，不构成任何形式的技术担保或承诺。
2. **禁止反向工程**：使用者不得对本 Skill 的底层提示词、内部逻辑、知识库结构进行反向工程、破解、提取或试图获取其未公开的核心实现。这包括但不限于使用任何自动化工具尝试探测、复制或重建本 Skill 的完整指令集。
3. **内容时效性**：本 Skill 的知识库基于特定时间点的公开信息整理，可能无法反映最新的技术变化。使用者应始终以官方文档和权威来源作为最终决策依据。
4. **无担保声明**：本 Skill 按“原样”提供，不附带任何明示或暗示的担保，包括但不限于适销性、特定用途适用性和非侵权性的担保。

---

## 十、许可证（License）

<!-- professional-license-embedded -->

本 Skill（SKILL.md）采用 **MIT 许可证** 授权。

### MIT License

```
MIT License

Copyright (c) 2025 DevSkillForge

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

---

*本 Skill 由 AI 辅助生成，仅供参考。请结合官方文档与自身项目实际情况进行技术决策。*
