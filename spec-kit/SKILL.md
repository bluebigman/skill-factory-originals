---
slug: spec-kit
name: spec-kit
displayName: 需求转规格 结构化处理 批量转换
description: 将需求数据、文件或URL转化为结构化规格结果，支持批量与自定义格式。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 林墨
agent_created: true
trigger_words: ["spec-kit", "规格工具", "需求结构化", "规格驱动", "结构化输出", "需求转规格", "批量结构化"]
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# spec-kit 技能文档

## 一、能力边界（一页纸速查卡）

### 1.1 能做什么

| 能力项 | 说明 | 示例 |
|--------|------|------|
| 输入解析 | 支持本地文件、URL、粘贴文本三种输入方式 | `./需求文档.md`、`https://example.com/req`、直接粘贴文本 |
| 结构化输出 | 将非结构化需求转为固定字段的规格结果 | 需求描述 → `{id, title, priority, acceptance_criteria}` |
| 批量处理 | 对同一目录下多个文件执行相同转换逻辑 | 对 `./requirements/` 下 50 个 `.md` 文件批量处理 |
| 自定义格式 | 允许用户指定输出模板（JSON / YAML / Markdown 表格） | `--format json` 或 `--template custom.tpl` |
| 试运行模式 | 先处理单个样本，核对无误后再全量执行 | `--dry-run sample.md` |

### 1.2 不能做什么（明确边界）

| 限制项 | 说明 |
|--------|------|
| 不进行语义理解 | 无法判断需求是否合理、是否完整，只做结构映射 |
| 不自动修复数据 | 输入缺失字段时，输出 `[需核实:字段名]` 占位，不猜测填充 |
| 不支持跨语言翻译 | 输入中文输出中文，输入英文输出英文，不自动翻译 |
| 不处理二进制文件 | 仅支持文本类文件（`.md`、`.txt`、`.json`、`.yaml`、`.csv`） |
| 不保证字段完整性 | 若源数据本身缺少信息，输出结果必然缺项 |

### 1.3 适用对象

- 需要将零散需求整理为统一格式的**产品经理**
- 需要将需求文档转为开发任务清单的**研发负责人**
- 需要批量整理历史需求数据的**数据分析师**
- 需要将外部 URL 内容转为内部规格的**技术文档工程师**

---

## 二、触发方式

### 2.1 触发词

| 触发词 | 场景 |
|--------|------|
| `spec-kit` | 直接调用工具 |
| `规格工具` | 中文场景下的工具调用 |
| `需求结构化` | 当用户说"帮我把这些需求结构化"时触发 |
| `规格驱动` | 当用户提到"规格驱动开发"时触发 |
| `结构化输出` | 当用户要求"输出成结构化格式"时触发 |
| `需求转规格` | 当用户说"把需求转成规格"时触发 |
| `批量结构化` | 当用户说"批量处理这些文档"时触发 |

### 2.2 场景映射表

| 用户说（大白话） | 触发动作 |
|------------------|----------|
| "帮我把这个需求文档整理一下" | 解析单个文件 → 输出结构化结果 |
| "这 20 个文件都处理一下" | 批量模式 → 逐个处理并汇总 |
| "输出成 JSON 格式" | 指定 `--format json` |
| "先跑一个看看效果" | 试运行模式 → 处理单个样本 |
| "这个链接里的内容也转一下" | 解析 URL → 提取文本 → 结构化 |

---

## 三、标准流程

### 3.1 前置条件

| 条件 | 要求 | 检查方式 |
|------|------|----------|
| 输入文件存在 | 文件路径正确且可读 | `ls -la 文件路径` |
| 文件格式支持 | 扩展名为 `.md/.txt/.json/.yaml/.csv` | `file 文件路径` |
| 命名规范一致 | 同批文件命名有规律（如 `req_001.md`） | `ls 目录` |
| 输出目录可写 | 目标目录有写入权限 | `touch 输出目录/.write_test` |
| 模板文件（可选） | 若使用自定义模板，模板文件须存在 | `test -f 模板路径` |

### 3.2 执行步骤

#### 步骤 1：准备输入

```
操作：将待处理文件放入同一目录
检查：确认命名规范一致（如 req_001.md, req_002.md）
建议：为每个批次单独建目录，避免混淆
```

#### 步骤 2：试运行（必须执行）

```
命令示例：
  spec-kit --dry-run ./requirements/req_001.md

核对项：
  □ 输出字段是否完整
  □ 字段命名是否符合预期
  □ 缺失字段是否显示 [需核实:xxx] 占位
  □ 格式是否符合要求（JSON/YAML/Markdown）
```

#### 步骤 3：批量执行

```
命令示例：
  spec-kit --batch ./requirements/ --format json --output ./output/

注意事项：
  □ 执行前备份原始文件（cp -r requirements requirements_backup）
  □ 执行过程中不要修改源文件
  □ 执行完成后检查输出文件数量是否与输入一致
```

#### 步骤 4：校验结果

```
抽查方法：
  1. 随机抽取 3-5 个输出文件
  2. 对比源文件，核对关键字段（标题、优先级、验收标准）
  3. 确认缺失字段的占位符格式正确
  4. 确认输出文件命名与源文件对应关系清晰
```

### 3.3 输出规范

| 输出格式 | 适用场景 | 示例片段 |
|----------|----------|----------|
| JSON | 程序化处理、API 对接 | `{"id": "req_001", "title": "用户登录", "priority": "P0"}` |
| YAML | 配置文件、人类可读性要求高 | `id: req_001\ntitle: 用户登录\npriority: P0` |
| Markdown 表格 | 文档展示、评审会议 | `\| ID \| 标题 \| 优先级 \|` |

---

## 四、置信度门控

### 4.1 占位符规则

当输入信息不足以生成某个字段时，**不得编造**，必须输出：

```
[需核实:字段名]
```

示例：

```
输入：用户登录功能，要求支持手机号登录。
输出：
  title: 用户登录
  login_method: 手机号
  priority: [需核实:priority]
  acceptance_criteria: [需核实:acceptance_criteria]
```

### 4.2 置信度分级

| 置信度 | 判定条件 | 输出行为 |
|--------|----------|----------|
| 高（≥90%） | 字段信息在源数据中明确出现 | 直接输出 |
| 中（60-89%） | 字段信息可推断但非显式 | 输出推断值，并标注 `[推断]` |
| 低（<60%） | 字段信息缺失或模糊 | 输出 `[需核实:字段名]` |

### 4.3 禁止行为

- ❌ 猜测缺失字段值
- ❌ 用"默认值"填充缺失字段
- ❌ 忽略缺失字段不输出
- ❌ 将推断值标记为确定值

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| `E001` | 文件不存在 | "未找到指定文件，请检查路径" | 确认路径正确，或使用绝对路径 |
| `E002` | 文件格式不支持 | "仅支持 .md/.txt/.json/.yaml/.csv 格式" | 转换文件格式后重试 |
| `E003` | 目录为空 | "指定目录下没有可处理的文件" | 确认文件已放入目录 |
| `E004` | 输出目录不可写 | "无法写入输出目录，请检查权限" | 修改目录权限或更换目录 |
| `E005` | 模板文件缺失 | "指定的模板文件不存在" | 确认模板路径，或使用内置模板 |
| `E006` | 批量处理中断 | "批量处理在第 N 个文件处中断" | 查看错误日志，修复后从第 N+1 个继续 |
| `E007` | URL 无法访问 | "无法访问指定 URL，请检查网络或链接有效性" | 确认 URL 可访问后重试 |
| `E008` | 输入内容为空 | "输入内容为空，无法处理" | 确认输入文件/URL/文本非空 |

---

## 六、FAQ 反模式

### 6.1 常见坑与反模式对照

| 坑 | 反模式（错误做法） | 正确做法 |
|----|-------------------|----------|
| 跳过试运行 | 直接批量处理全部文件，结果格式全错 | 先跑单个样本，确认无误再批量 |
| 不备份原文件 | 批量处理后发现源文件被覆盖 | 执行前 `cp -r` 备份原始目录 |
| 忽略占位符 | 看到 `[需核实:xxx]` 不处理，直接交付 | 逐个核实占位符字段，补充真实数据 |
| 混用命名规范 | 同一目录下文件命名无规律，批量处理遗漏 | 按批次整理文件，统一命名前缀 |
| 依赖 AI 推断 | 让 AI 猜测缺失字段值 | 使用 `[需核实:xxx]` 占位，人工补充 |

### 6.2 反模式示例

**反模式 1：直接批量处理**

```
❌ 错误：spec-kit --batch ./requirements/ --format json
✅ 正确：spec-kit --dry-run ./requirements/req_001.md
        # 核对输出格式无误后
        spec-kit --batch ./requirements/ --format json
```

**反模式 2：不处理占位符**

```
❌ 错误：输出结果中保留 [需核实:priority] 直接交付
✅ 正确：人工核实 priority 字段，补充为 P0/P1/P2 后交付
```

---

## 七、渐进式披露

### 7.1 速查卡（30 秒上手）

```
1. 放文件 → 2. 试运行 → 3. 批量跑 → 4. 查结果
   ls        dry-run     batch      抽查 3-5 个
```

### 7.2 分层次阅读路径

#### 新手路径（首次使用）

1. 阅读「一、能力边界」了解工具能做什么
2. 阅读「三、标准流程」按步骤执行
3. 遇到问题查「五、错误码体系」

#### 进阶路径（熟练使用）

1. 阅读「四、置信度门控」理解占位符机制
2. 阅读「六、FAQ 反模式」避免常见错误
3. 自定义模板，适配团队内部格式规范

#### 专家路径（深度定制）

1. 研究输出规范，设计自定义模板
2. 结合 CI/CD 流程，将批量处理集成到自动化管道
3. 对输出结果做二次校验，建立质量门禁

---

## 八、参数速查表

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `--input` | string | 是 | 无 | 输入文件路径或 URL |
| `--batch` | string | 否 | 无 | 批量处理目录路径 |
| `--output` | string | 否 | `./output/` | 输出目录 |
| `--format` | string | 否 | `json` | 输出格式：`json`/`yaml`/`md` |
| `--template` | string | 否 | 内置模板 | 自定义模板文件路径 |
| `--dry-run` | string | 否 | 无 | 试运行模式，处理单个文件 |
| `--selftest` | flag | 否 | 无 | 运行自检 |
| `--version` | flag | 否 | 无 | 显示版本号 |

---

## 九、用户协议

使用本 Skill 即表示您同意以下条款：

1. **责任承担**：使用者自行承担使用本 Skill 产生的全部责任。因使用本 Skill 导致的任何直接或间接损失，Skill 作者不承担任何责任。
2. **禁止反向工程**：不得对本 Skill 进行反向工程、反编译、破解或试图提取源代码。
3. **合法用途**：本 Skill 仅可用于合法目的，不得用于任何违反法律法规的场景。
4. **无担保**：本 Skill 按"现状"提供，不附带任何明示或暗示的担保。

<!-- user-agreement-injected -->

---

## 十、许可证（License）

本 Skill 采用 MIT 许可证发布。

### MIT License

```
MIT License

Copyright (c) 2024 林墨

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
