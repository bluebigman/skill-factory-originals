---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: cheat.sh
name: cheat-sh
displayName: 命令行速查 代码示例 即时检索
description: 一条命令获取任意编程语言与工具的代码示例，无需安装，开发必备速查手册。
version: 2.0.2
rules_version: cpr-20260811-n351
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/cheat.sh
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: SkillForge Studio
agent_created: true
trigger_words: ["cheat.sh", "命令行速查", "代码示例", "速查手册", "开发查询", "编程速查"]
---

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->


> 本内容由 AI 辅助生成，仅供参考
<!-- ai-generated-notice -->

# cheat.sh 命令行速查手册

## 一、能力边界：一页纸速查卡

### 1.1 这个 Skill 能做什么

| 能力项 | 说明 | 示例 |
|--------|------|------|
| 中文查询转译 | 将自然语言描述自动转换为 cheat.sh 查询路径 | 「Python 读文件」→ `python/read+file` |
| 多结果对比 | 查看同一主题的不同实现写法 | `--index 2` 查看第二种方案 |
| 管道友好输出 | 去除颜色码，便于 grep/less 等工具处理 | 始终附加 `--plain` 参数 |
| 离线缓存复用 | 缓存常用查询结果，断网可复查 | 先执行 `--cache` 预热 |
| 关键词收窄 | 结果过多时通过追加关键词缩小范围 | `python/read+json+file` |

### 1.2 这个 Skill 不能做什么

| 限制项 | 说明 |
|--------|------|
| 不执行代码 | 仅返回代码片段，不负责运行验证 |
| 不保证版本兼容 | 示例可能基于特定版本，需自行适配 |
| 不替代官方文档 | 复杂场景仍需查阅权威文档 |
| 不提供 GUI 界面 | 纯命令行交互，无图形化操作 |

### 1.3 适用对象

- 日常使用命令行的开发者
- 需要快速获取代码片段的技术人员
- 希望减少文档翻阅时间的效率追求者

---

## 二、触发方式：场景映射表

| 触发词/场景 | 实际执行动作 |
|-------------|--------------|
| 「查一下 Python 怎么读文件」 | 执行 `cheat.sh python/read+file --plain` |
| 「看看 Go 的 HTTP 客户端写法」 | 执行 `cheat.sh go/http+client --plain` |
| 「有没有别的实现方式」 | 执行 `cheat.sh python/read+file --index 2 --plain` |
| 「断网了还能查吗」 | 执行 `cheat.sh --cache` 后复用缓存 |
| 「结果太多了，只要 JSON 相关的」 | 执行 `cheat.sh python/read+json+file --plain` |

---

## 三、标准流程

### 3.1 前置条件

- 已安装 cheat.sh 客户端（安装命令：`curl -s https://cht.sh/:bash | bash`）
- 网络连通（首次查询需要联网，缓存后可离线使用）

### 3.2 执行步骤

1. **确定查询主题**：明确你要查的语言/工具和具体功能点
2. **构建查询路径**：格式为 `语言/功能+关键词`
   - 语言部分：`python`、`go`、`javascript` 等
   - 功能部分：`read+file`、`http+client` 等
   - 多个关键词用 `+` 连接
3. **附加参数**：
   - `--plain`：去除颜色码（推荐始终使用）
   - `--index N`：查看第 N 个结果
   - `--cache`：缓存当前查询
4. **执行命令**：`cheat.sh <查询路径> [参数]`
5. **处理输出**：根据需求复制代码或进一步收窄查询

### 3.3 输出规范

- 默认输出为纯文本代码片段
- 使用 `--plain` 时无 ANSI 颜色码
- 多结果时使用 `--index` 指定查看第几个

---

## 四、置信度门控

当查询结果不明确或信息不足时，遵循以下原则：

| 场景 | 处理方式 |
|------|----------|
| 查询无结果 | 输出 `[需核实:查询路径是否正确]`，建议检查拼写 |
| 结果过于宽泛 | 输出 `[需核实:建议添加更多关键词]`，引导用户细化 |
| 版本兼容性未知 | 输出 `[需核实:版本适配性]`，提醒用户自行验证 |
| 代码片段不完整 | 输出 `[需核实:代码完整性]`，建议查阅官方文档 |

**绝不编造**：当查询失败时，不猜测、不虚构结果，如实反馈错误信息。

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| `E001` | 网络连接失败 | 「无法连接到 cheat.sh 服务器，请检查网络」 | 1. 检查网络连接 2. 使用 `--cache` 查看缓存 |
| `E002` | 查询路径格式错误 | 「查询路径格式不正确，应为 语言/功能+关键词」 | 1. 检查路径格式 2. 参考示例重新输入 |
| `E003` | 无匹配结果 | 「未找到相关代码示例」 | 1. 简化关键词 2. 检查语言名称拼写 |
| `E004` | 索引越界 | 「指定的索引超出结果范围」 | 1. 先不加 `--index` 查看总数 2. 调整索引值 |
| `E005` | 缓存未命中 | 「缓存中无此查询记录」 | 1. 联网执行一次 2. 使用 `--cache` 保存 |

---

## 六、FAQ 反模式对照

| 常见坑 | 反模式（错误做法） | 正确做法 |
|--------|-------------------|----------|
| 颜色码干扰 | 直接使用原始输出进行管道处理 | 始终添加 `--plain` 参数 |
| 结果过多 | 不加限制地浏览全部结果 | 使用 `--index` 或追加关键词收窄 |
| 断网无法查询 | 依赖实时网络连接 | 提前使用 `--cache` 缓存常用查询 |
| 中文查询失败 | 直接输入中文路径 | 先转译为英文关键词再查询 |
| 版本不匹配 | 直接复制代码不验证 | 检查代码注释中的版本信息 |

---

## 七、渐进式披露

### 7.1 速查卡（30 秒上手）

```bash
# 基本查询
cheat.sh python/read+file --plain

# 查看第二种写法
cheat.sh python/read+file --index 2 --plain

# 缓存常用查询
cheat.sh python/read+file --cache

# 离线使用
cheat.sh --cache
```

### 7.2 新手路径（5 分钟掌握）

1. 从简单查询开始：`cheat.sh python/list --plain`
2. 学习关键词组合：`cheat.sh python/list+sort --plain`
3. 尝试多结果对比：`cheat.sh python/list --index 2 --plain`
4. 建立个人缓存库：对常用查询执行 `--cache`

### 7.3 进阶路径（深度使用）

1. **批量查询脚本**：编写 shell 脚本循环查询多个主题
2. **缓存管理**：定期更新缓存，保持离线数据新鲜
3. **自定义别名**：为高频查询设置 shell 别名
4. **集成工作流**：将 cheat.sh 集成到 CI/CD 或开发工具链中

---

## 八、参数速查表

| 参数 | 作用 | 示例 |
|------|------|------|
| `--plain` | 去除颜色码 | `cheat.sh python/read --plain` |
| `--index N` | 查看第 N 个结果 | `cheat.sh python/read --index 3` |
| `--cache` | 缓存查询结果 | `cheat.sh python/read --cache` |
| `--selftest` | 自检安装状态 | `cheat.sh --selftest` |
| `--version` | 查看版本信息 | `cheat.sh --version` |

---

## 九、用户协议

使用本 Skill 即表示您同意以下条款：

1. **责任承担**：使用者自行承担因使用本 Skill 产生的全部责任。包括但不限于因代码示例不适用、信息不准确或操作失误导致的任何损失。
2. **禁止反向工程**：不得对本 Skill 进行反向工程、反编译、破解或试图提取源代码（除非适用法律允许）。
3. **合规使用**：使用者应遵守所在地区法律法规，不得将本 Skill 用于任何非法用途。
4. **免责声明**：本 Skill 按"现状"提供，不附带任何明示或暗示的保证。

<!-- user-agreement-injected -->

---

## 十、许可证（License）

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

<!-- professional-license-embedded -->
