---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: ux-skill
name: ux-skill
displayName: 界面体验 交互诊断 设计审查
description: 面向AI编程工具的体验设计审查引擎，将输入转化为结构化诊断结果。
version: 1.0.3
rules_version: cpr-20260814-n426
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/ux-skill
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: Lin Chen
agent_created: true
trigger_words: ["ux-skill", "体验审查", "界面诊断", "UX评审", "交互检查", "体验评估", "设计走查"]
---

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->


> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# ux-skill — 界面体验 交互诊断 设计审查

## 一、能力边界：一页纸速查卡

本 Skill 面向 AI 编程工具，用于对界面设计、交互流程、用户体验相关材料进行结构化审查，输出可追踪、可复核的诊断结果。

### 1.1 能做清单

| 序号 | 能力项 | 说明 |
|------|--------|------|
| 1 | 标准格式批量处理 | 对符合命名规范的输入文件进行批量审查 |
| 2 | 字段提取与结构化输出 | 从非结构化文本中提取关键体验要素，输出为固定字段 |
| 3 | 失败明细追踪 | 对无法解析的条目生成错误码并记录原因 |
| 4 | 单样本试运行 | 支持先跑单条数据验证输出格式 |
| 5 | 置信度标注 | 对信息不完整的字段标注 `[需核实:字段名]` 占位符 |

### 1.2 不能做清单

| 序号 | 限制项 | 说明 |
|------|--------|------|
| 1 | 不执行真实用户测试 | 无法替代真人可用性测试，仅做静态规则审查 |
| 2 | 不生成设计稿 | 不产出视觉稿、原型图或高保真设计文件 |
| 3 | 不提供量化评分 | 不输出 0-100 分等绝对化评分，只输出结构化诊断 |
| 4 | 不处理非标准输入 | 文件命名不规范或格式不符时直接报错，不做猜测性解析 |
| 5 | 不修改源文件 | 只输出诊断结果，不直接改动任何输入文件 |

### 1.3 适用对象

- 需要快速走查界面体验的 AI 编程工具
- 需要批量审查交互说明文档的自动化流程
- 需要将体验问题结构化归档的团队

---

## 二、触发方式：场景映射表

当输入中包含以下任一触发词时，本 Skill 自动激活：

| 触发词 | 场景示例 | 预期行为 |
|--------|----------|----------|
| `ux-skill` | 直接调用 | 执行完整审查流程 |
| `体验审查` | "帮我做一次体验审查" | 启动审查引擎 |
| `界面诊断` | "这个界面帮我诊断一下" | 启动审查引擎 |
| `UX评审` | "准备 UX 评审材料" | 启动审查引擎 |
| `交互检查` | "检查一下交互逻辑" | 启动审查引擎 |
| `体验评估` | "评估这个流程的体验" | 启动审查引擎 |
| `设计走查` | "做一次设计走查" | 启动审查引擎 |

---

## 三、标准流程

### 3.1 前置条件

| 条件项 | 要求 |
|--------|------|
| 输入文件 | 与 Skill 位于同一目录，命名格式为 `input_*.txt` 或 `input_*.md` |
| 命名规范 | 文件名必须包含 `input_` 前缀，否则报错 `ERR_001` |
| 目录权限 | 当前目录需有读写权限，用于生成输出文件 |
| 备份要求 | 批量执行前必须保留原始文件副本 |

### 3.2 执行步骤

**第一步：准备输入**

将待审查文件放入当前目录，确认命名符合规范。示例：

```
input_login_flow.txt
input_checkout_flow.md
input_onboarding_flow.txt
```

**第二步：试运行**

使用单个样本执行，核对输出字段与格式是否符合预期：

```bash
ux-skill 体验审查 --file input_login_flow.txt
```

检查输出中的以下字段是否完整：

- `flow_id` — 流程标识
- `step_count` — 步骤数量
- `pain_points` — 痛点列表
- `severity` — 严重程度（低/中/高）
- `confidence` — 置信度

**第三步：批量执行**

确认无误后，对全量数据执行：

```bash
ux-skill 体验审查 --batch
```

执行期间自动完成：

- 遍历所有 `input_*` 文件
- 逐条生成诊断记录
- 生成 `diagnosis_report.json` 汇总文件
- 生成 `error_log.csv` 失败明细

**第四步：校验结果**

抽查输出条目，核对关键字段与源数据一致性：

```bash
ux-skill 体验审查 --verify --file diagnosis_report.json
```

校验规则：

| 校验项 | 规则 |
|--------|------|
| 字段完整性 | 每条记录必须包含 `flow_id` 和 `severity` |
| 数据一致性 | 提取的步骤数必须与源文件描述一致 |
| 错误码有效性 | 所有错误码必须在错误码表中存在 |

### 3.3 输出规范

输出文件为 JSON 格式，结构如下：

```json
{
  "schema_version": "1.0",
  "generated_at": "2026-08-14T10:30:00Z",
  "total_flows": 3,
  "success_count": 2,
  "error_count": 1,
  "results": [
    {
      "flow_id": "login_flow",
      "step_count": 5,
      "pain_points": [
        {
          "step": 2,
          "issue": "密码输入框缺少可见性切换",
          "severity": "中",
          "suggestion": "增加显示/隐藏密码按钮"
        }
      ],
      "confidence": 0.85
    }
  ],
  "errors": [
    {
      "flow_id": "checkout_flow",
      "error_code": "ERR_002",
      "message": "步骤描述缺失"
    }
  ]
}
```

---

## 四、置信度门控

当输入信息不足以支撑某个字段的判断时，**不得编造内容**，必须输出 `[需核实:字段名]` 占位符。

### 4.1 触发条件

| 场景 | 处理方式 |
|------|----------|
| 步骤描述不完整 | `[需核实:step_description]` |
| 缺少用户角色信息 | `[需核实:user_role]` |
| 无法判断严重程度 | `[需核实:severity]` |
| 缺少错误处理说明 | `[需核实:error_handling]` |

### 4.2 占位符使用规则

- 占位符必须保留在输出字段中，不得删除或替换
- 占位符不计入 `confidence` 评分
- 占位符数量超过字段总数 30% 时，该条记录标记为 `low_confidence`

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| `ERR_001` | 文件命名不符合规范 | "文件名必须以 input_ 开头" | 重命名文件后重试 |
| `ERR_002` | 内容缺少必要字段 | "缺少步骤描述，无法解析" | 补充步骤描述后重试 |
| `ERR_003` | 文件格式不支持 | "仅支持 .txt 和 .md 格式" | 转换格式后重试 |
| `ERR_004` | 批量执行时目录为空 | "未找到任何 input_* 文件" | 确认文件已放入目录 |
| `ERR_005` | 输出目录无写入权限 | "无法创建输出文件" | 检查目录权限后重试 |

---

## 六、FAQ 反模式

### 6.1 常见坑

**坑 1：跳过试运行直接批量**

反模式：直接执行 `--batch` 导致输出格式错误，浪费处理时间。

正确做法：先跑单样本验证格式，再批量执行。

**坑 2：忽略错误日志**

反模式：只看成功结果，忽略 `error_log.csv` 中的失败记录。

正确做法：每次批量执行后必须检查错误日志，确认失败原因。

**坑 3：修改源文件**

反模式：直接编辑 `input_*` 文件来"修正"问题。

正确做法：保留原始文件，通过输出结果定位问题后，在源系统中修改。

**坑 4：依赖绝对化判断**

反模式：期望输出"这个界面一定有问题"的确定性结论。

正确做法：理解输出为结构化诊断，而非最终裁决。

**坑 5：忽略置信度标记**

反模式：将 `[需核实:字段]` 当作有效数据使用。

正确做法：对带占位符的记录进行人工复核。

### 6.2 反模式对照表

| 反模式 | 正确模式 |
|--------|----------|
| 直接批量执行 | 先试运行再批量 |
| 忽略错误日志 | 每次执行后检查错误码 |
| 修改源文件 | 保留原始文件，在源系统修改 |
| 追求绝对结论 | 接受结构化诊断结果 |
| 忽略占位符 | 对低置信度记录人工复核 |

---

## 七、渐进式披露

### 7.1 速查卡（新手路径）

1. 把文件命名为 `input_*.txt` 放入目录
2. 跑单条：`ux-skill 体验审查 --file input_xxx.txt`
3. 检查输出格式
4. 跑批量：`ux-skill 体验审查 --batch`
5. 查看 `diagnosis_report.json` 和 `error_log.csv`

### 7.2 进阶路径（有经验用户）

1. 自定义校验规则：修改 `config.json` 中的 `validation_rules`
2. 调整严重程度阈值：设置 `severity_threshold` 参数
3. 集成到 CI/CD：在流水线中调用 `ux-skill 体验审查 --batch --ci-mode`
4. 扩展字段映射：在 `field_mappings.json` 中增加自定义字段

### 7.3 参数速查

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `--file` | string | 无 | 指定单文件审查 |
| `--batch` | boolean | false | 批量执行模式 |
| `--verify` | boolean | false | 校验输出结果 |
| `--ci-mode` | boolean | false | CI 模式，输出简化日志 |
| `--severity-threshold` | string | "中" | 最低报告严重程度 |
| `--output-dir` | string | "./output" | 输出目录路径 |

---

## 八、使用示例

### 8.1 单文件审查

```bash
ux-skill 体验审查 --file input_login_flow.txt
```

### 8.2 批量审查

```bash
ux-skill 体验审查 --batch --output-dir ./reports
```

### 8.3 校验结果

```bash
ux-skill 体验审查 --verify --file reports/diagnosis_report.json
```

### 8.4 自检

```bash
ux-skill --selftest
```

### 8.5 版本查询

```bash
ux-skill --version
```

---

## 九、用户协议

<!-- user-agreement-injected -->

使用本 Skill 即表示您同意以下条款：

1. **责任承担**：使用者自行承担使用本 Skill 产生的全部责任。本 Skill 提供的诊断结果仅供参考，不构成任何形式的设计决策依据。
2. **禁止反向工程**：不得对本 Skill 的底层逻辑进行反向工程、反编译、破解或试图提取源代码。
3. **无担保声明**：本 Skill 按"原样"提供，不附带任何明示或暗示的担保。
4. **合规使用**：使用者须确保使用场景符合当地法律法规及平台政策。

---

## 十、许可证（License）

<!-- professional-license-embedded -->

MIT License

Copyright (c) 2026 Lin Chen

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
