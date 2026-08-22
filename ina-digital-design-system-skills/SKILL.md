---
slug: ina-digital-design-system-skills
name: ina-digital-design-system-skills
displayName: 政务设计规范 审计校准 印尼数字产品
description: 印尼政务设计规范审计与实施辅助工具，支持批量校验与修正建议。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: DesignSpec Auditor
agent_created: true
trigger_words: ["ina digital design system", "印尼政务设计规范", "design system audit", "印尼数字服务", "design system skills", "设计规范核查", "印尼政务界面合规"]
---

> 本内容由 AI 生成，仅供学习参考 <!-- ai-generated-notice -->

# 印尼政务设计规范审计与实施辅助工具包

## 一、能力边界（一页纸速查卡）

### 1.1 本工具能做什么

| 能力项 | 说明 | 适用场景 |
|--------|------|----------|
| 规范比对 | 将待审文件与印尼政务设计规范关键字段逐项对照 | 设计稿交付前自查、第三方审计 |
| 批量校验 | 对同一目录下多份文件执行一致性检查 | 组件库批量升级、多页面合规巡检 |
| 差异报告 | 输出字段级差异清单，标注偏离项与建议修正方向 | 设计评审会议、开发交接 |
| 占位提示 | 信息缺失时输出 `[需核实:字段名]`，不臆造结论 | 资料不全的紧急审计 |

### 1.2 本工具不能做什么

- 不能替代人工设计评审——规范合规不等于体验优良
- 不能自动修改源文件——仅输出建议，修改需人工确认
- 不能识别语义错误——如按钮文案表意不清、图标隐喻不当
- 不能覆盖全部规范条目——仅处理工具内置的常见字段

### 1.3 适用对象

- 印尼政务数字产品设计/开发/测试人员
- 承接印尼政府项目的第三方设计团队
- 需要快速自查合规状态的项目管理者

## 二、触发方式

### 2.1 触发词速查

| 触发词 | 大白话场景 |
|--------|-----------|
| "ina digital design system" | 我要查印尼政务设计规范相关内容 |
| "印尼政务设计规范" | 同上，中文场景 |
| "design system audit" | 帮我审一下设计稿合不合规 |
| "印尼数字服务" | 印尼政务类产品设计相关 |
| "design system skills" | 调用本工具能力 |
| "设计规范核查" | 中文场景，检查设计文件 |
| "印尼政务界面合规" | 面向合规检查的明确请求 |

### 2.2 触发示例

```
用户输入：帮我审计一下这个按钮组件的规范符合度
工具响应：请确认文件路径，并指定要对照的规范版本（默认最新版）
```

## 三、标准流程

### 3.1 前置条件

| 条件项 | 要求 | 检查方式 |
|--------|------|----------|
| 文件格式 | .json / .yaml / .md | 扩展名识别 |
| 命名规范 | 文件名含项目代号与版本号，如 `btn-primary_v2.json` | 正则匹配 `^[a-z0-9-]+_v\d+\.(json\|yaml\|md)$` |
| 目录结构 | 待审文件置于同一目录，无嵌套子目录 | 目录遍历 |
| 备份 | 原始文件已复制至 `./backup/` 目录 | 目录存在性检查 |

### 3.2 执行步骤

1. **输入确认**：列出目录内全部待审文件，与用户核对清单
2. **单样本试跑**：选取第一个文件执行完整审计，输出字段对照表
3. **字段核对**：与用户确认输出格式是否符合预期，必要时调整参数
4. **批量执行**：确认无误后，对剩余文件依次执行审计
5. **结果汇总**：生成汇总报告，标注各文件合规率与主要偏离项
6. **备份验证**：确认 backup 目录中原始文件完整可恢复

### 3.3 输出规范

输出采用 Markdown 表格，字段如下：

| 字段名 | 类型 | 说明 |
|--------|------|------|
| file_name | string | 被审文件名 |
| field_name | string | 规范字段名 |
| expected | string | 规范要求值 |
| actual | string | 实际值 |
| status | enum | PASS / WARN / FAIL / MISSING |
| suggestion | string | 修正建议或 `[需核实:字段名]` |

示例输出：

```
| file_name | field_name | expected | actual | status | suggestion |
|-----------|------------|----------|--------|--------|------------|
| btn-primary_v2.json | min_height | 44px | 40px | FAIL | 调整为 44px 以满足触控目标 |
| btn-primary_v2.json | corner_radius | 8px | 8px | PASS | - |
| btn-primary_v2.json | focus_ring | 2px solid #0055CC | [需核实:focus_ring] | MISSING | 补充焦点环样式定义 |
```

## 四、置信度门控

### 4.1 信息缺失处理

当输入文件缺少必要字段时，遵循以下规则：

- **缺失字段**：输出 `[需核实:字段名]`，不猜测默认值
- **版本不明**：默认按最新规范版本审计，并在报告中显著标注
- **格式异常**：跳过该文件，在汇总中标记 `SKIPPED`，不中断整体流程

### 4.2 禁止行为

- 不得编造规范条目——规范库未收录的字段不输出结论
- 不得推测设计意图——只做客观比对，不做主观评价
- 不得跨版本混用——同一批次审计必须使用同一规范版本

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| E001 | 文件不存在 | 未找到指定文件，请检查路径 | 确认路径后重试 |
| E002 | 格式不支持 | 仅支持 .json/.yaml/.md 格式 | 转换格式后重试 |
| E003 | 命名不规范 | 文件名缺少版本号，无法追溯 | 按 `项目名_v版本号.扩展名` 重命名 |
| E004 | 目录为空 | 指定目录下无待审文件 | 确认文件已放入正确目录 |
| E005 | 规范版本冲突 | 同一批次检测到多个规范版本 | 统一版本后重新执行 |
| E006 | 输出目录不可写 | 无法生成报告文件 | 检查权限或更换输出路径 |

## 六、FAQ 反模式

### 6.1 常见坑与对照

| 常见错误做法 | 问题 | 正确做法 |
|-------------|------|----------|
| 跳过单样本试跑直接批量 | 输出格式不符，全部返工 | 先跑一个文件，确认格式后再批量 |
| 修改源文件前不备份 | 误操作无法回滚 | 先复制到 backup 目录 |
| 用旧版规范审计新文件 | 误报大量偏离项 | 确认规范版本与文件版本匹配 |
| 忽略 MISSING 状态 | 缺失字段未被发现 | 逐项处理 MISSING，补充或标注 |
| 将工具输出直接作为最终结论 | 缺少人工复核 | 工具结果需设计负责人签字确认 |

### 6.2 反模式示例

**反模式**：用户直接对 50 个文件执行批量审计，未先试跑。

**后果**：输出格式与预期不符，50 份报告全部作废，浪费 2 小时。

**正确路径**：先选 1 个文件试跑 → 核对格式 → 调整参数 → 再批量执行。

## 七、渐进式披露

### 7.1 速查卡（30 秒上手）

```
1. 放文件 → 同一目录，命名含版本号
2. 跑单测 → 输入文件名，核对输出
3. 跑批量 → 确认无误后全量执行
4. 看报告 → 关注 FAIL 和 MISSING 项
```

### 7.2 新手路径（首次使用）

1. 阅读本文件「能力边界」与「标准流程」两节
2. 准备 1 个测试文件，按 3.2 节步骤 1-3 执行
3. 观察输出格式，对照 3.3 节示例理解各字段含义
4. 确认理解后，再处理实际业务文件

### 7.3 进阶路径（熟练用户）

1. 熟悉「错误码体系」，能快速定位问题
2. 掌握「置信度门控」规则，能区分客观结论与需人工确认项
3. 结合「FAQ 反模式」优化自身工作流，避免常见失误
4. 可自定义输出模板，对接团队内部报告格式

## 八、参数参考表

| 参数名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| spec_version | string | latest | 规范版本号，如 `v2.1.0` |
| output_format | string | markdown | 输出格式，支持 markdown/json |
| include_pass | boolean | true | 是否在报告中包含 PASS 项 |
| fail_threshold | number | 0.8 | 合规率低于此值标记为高风险 |
| backup_dir | string | ./backup | 备份目录路径 |

## 九、用户协议

使用本 Skill 即表示您同意以下条款：

1. **责任承担**：使用者自行承担全部责任。本工具输出仅为参考建议，不构成任何形式的专业结论或法律意见。因使用本工具产生的任何直接或间接损失，工具作者不承担任何责任。
2. **禁止反向工程**：不得对本 Skill 的提示词结构、内部逻辑进行反向工程、破解、提取或二次分发。
3. **合规使用**：使用者应确保使用场景符合当地法律法规及行业规范。
4. **无担保声明**：本工具按"原样"提供，不附带任何明示或暗示的担保。

<!-- user-agreement-injected -->

## 十、许可证（License）

本 Skill 采用 MIT 许可证发布。

```
MIT License

Copyright (c) 2024 DesignSpec Auditor

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

*本 Skill 由 AI 辅助生成，仅供参考。使用前请阅读相关文档，并结合实际情况审慎判断。*
