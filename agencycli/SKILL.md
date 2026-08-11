---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: agencycli
name: agencycli
displayName: 代理团队 角色编排 命令行协作
description: 用Markdown+YAML定义角色与技能，构建自管理AI代理团队的轻量命令行工具。
version: 1.0.2
rules_version: cpr-20260811-n351
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/agencycli
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: Lin Chen
agent_created: true
trigger_words: ["agencycli","AI代理团队","多智能体协作","自管理团队","agent团队编排","角色定义","技能编排","命令行代理"]
---

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->


> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# agencycli — 自管理 AI 代理团队编排工具

## 一、能力边界（一页纸速查卡）

### 能做什么

| 能力项 | 说明 | 示例 |
|--------|------|------|
| 角色定义 | 通过 Markdown+YAML 文件声明代理角色、职责、上下文 | `roles/analyst.md` 中定义数据分析师角色 |
| 技能绑定 | 将处理流程（步骤、参数、输出格式）绑定到角色 | 分析师角色绑定 `summarize` 技能 |
| 团队编排 | 按依赖关系组织多个代理协作完成复杂任务 | 分析师产出数据 → 文案撰写 → 审核员复核 |
| 自管理循环 | 代理根据输出结果自动决策下一步动作 | 审核不通过时自动触发修订流程 |
| 交互式输入 | 无参数启动时进入交互模式，逐步引导输入 | 输入任务描述、选择角色、确认参数 |
| 结构化输出 | 以 YAML/JSON 格式输出结果，便于下游消费 | 输出 `result.yaml` 含状态码与建议 |

### 不能做什么

| 限制项 | 说明 |
|--------|------|
| 不执行外部 API 调用 | 工具本身不发起网络请求，需通过自定义技能扩展 |
| 不提供图形界面 | 纯命令行工具，无 Web UI 或桌面端 |
| 不内置大模型 | 需要用户自行配置 LLM 接口或使用本地模型 |
| 不支持实时流式输出 | 任务完成后一次性输出结果 |
| 不保证任务成功率 | 结果质量取决于角色定义与技能配置的完善程度 |

### 适用对象

- 需要快速搭建多代理协作流程的开发者
- 希望用文本文件管理 AI 工作流的团队
- 对命令行工具熟悉的技术人员
- 需要可审计、可版本控制的代理配置的用户

---

## 二、触发方式

### 触发词

`agencycli`、`AI代理团队`、`多智能体协作`、`自管理团队`、`agent团队编排`、`角色定义`、`技能编排`、`命令行代理`

### 场景映射表

| 用户场景 | 触发方式 | 使用示例 |
|----------|----------|----------|
| 想创建一个数据分析代理团队 | 命令行输入 `agencycli --init data-team` | 生成团队模板目录 |
| 已有角色定义，想执行任务 | 命令行输入 `agencycli --run tasks/analysis.yaml` | 按任务文件执行 |
| 不确定如何配置，需要帮助 | 命令行输入 `agencycli --help` | 查看完整帮助信息 |
| 想验证配置是否正确 | 命令行输入 `agencycli --selftest` | 运行自检程序 |
| 交互式创建任务 | 直接运行 `agencycli` 无参数 | 进入引导式输入流程 |

---

## 三、标准流程

### 前置条件

| 条件 | 要求 | 验证方式 |
|------|------|----------|
| 系统环境 | Python 3.9+ 或 Node.js 16+ | `python --version` 或 `node --version` |
| 配置文件 | 存在 `agency.yaml` 或指定路径 | `ls agency.yaml` |
| 角色定义 | 角色文件位于 `roles/` 目录 | `ls roles/` |
| 技能定义 | 技能文件位于 `skills/` 目录 | `ls skills/` |
| 权限 | 对工作目录有读写权限 | `touch .write_test` |

### 执行步骤

1. **初始化环境**
   ```bash
   agencycli --init my-team
   cd my-team
   ```
   生成标准目录结构：
   ```
   my-team/
   ├── agency.yaml          # 团队主配置
   ├── roles/               # 角色定义目录
   │   ├── analyst.md       # 分析师角色
   │   └── reviewer.md      # 审核员角色
   ├── skills/              # 技能定义目录
   │   ├── summarize.yaml   # 摘要技能
   │   └── validate.yaml    # 校验技能
   └── tasks/               # 任务定义目录
   ```

2. **定义角色**（`roles/analyst.md`）
   ```markdown
   ---
   name: analyst
   display_name: 数据分析师
   description: 负责数据清洗与初步分析
   skills:
     - summarize
     - validate
   max_retries: 3
   ---
   
   # 角色职责
   接收原始数据，执行清洗，输出结构化摘要。
   ```

3. **定义技能**（`skills/summarize.yaml`）
   ```yaml
   name: summarize
   description: 生成数据摘要
   input:
     data_path: string  # 数据文件路径
     max_length: int    # 摘要最大长度，默认 500
   process:
     - step: read_data
       action: load_csv
       params:
         path: "{data_path}"
     - step: generate_summary
       action: llm_call
       params:
         prompt: "总结以下数据的关键特征: {data}"
         max_tokens: "{max_length}"
   output:
     format: yaml
     fields:
       - summary
       - key_metrics
   ```

4. **创建任务**（`tasks/analysis.yaml`）
   ```yaml
   team: my-team
   goal: 分析销售数据并生成报告
   roles:
     - analyst:
         input:
           data_path: ./data/sales.csv
           max_length: 800
     - reviewer:
         input:
           report_path: ./output/report.md
   ```

5. **执行任务**
   ```bash
   agencycli --run tasks/analysis.yaml
   ```

6. **查看输出**
   ```bash
   cat output/result.yaml
   ```

### 输出规范

| 字段 | 类型 | 说明 |
|------|------|------|
| `status` | string | `success` / `partial` / `failed` |
| `result` | object | 各角色输出汇总 |
| `suggestions` | array | 下一步行动建议 |
| `errors` | array | 错误信息列表（如有） |
| `duration_ms` | int | 执行耗时（毫秒） |

示例输出：
```yaml
status: success
result:
  analyst:
    summary: "Q3 销售额增长 12%，主要来自华东区"
    key_metrics:
      growth_rate: 0.12
      top_region: 华东
  reviewer:
    verdict: approved
    comments: "数据完整，结论合理"
suggestions:
  - "可将报告导出为 PDF 格式"
  - "建议增加同比对比分析"
errors: []
duration_ms: 3421
```

---

## 四、置信度门控

当输入信息不足或存在歧义时，工具不会猜测或编造数据，而是输出占位符 `[需核实:字段名]`。

| 场景 | 输出示例 |
|------|----------|
| 缺少数据文件路径 | `[需核实:data_path]` |
| 角色未定义所需技能 | `[需核实:skill_definition]` |
| 输出字段未指定格式 | `[需核实:output_format]` |
| 模型返回内容不完整 | `[需核实:model_response]` |

**处理原则：**
1. 所有占位符必须保留在输出中，不得替换为推测值
2. 占位符出现时，`status` 字段设为 `partial`
3. 在 `suggestions` 中提示用户补充缺失信息

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| `E001` | 配置文件不存在 | "未找到 agency.yaml，请先运行 --init 或指定配置文件路径" | 运行 `agencycli --init` 或使用 `--config` 参数 |
| `E002` | 角色定义缺失 | "角色 {role_name} 未在 roles/ 目录中找到定义文件" | 创建对应 .md 文件，或检查文件名拼写 |
| `E003` | 技能定义缺失 | "技能 {skill_name} 未定义，请检查 skills/ 目录" | 添加对应 .yaml 技能文件 |
| `E004` | 参数类型错误 | "参数 {param_name} 期望类型 {expected}，实际为 {actual}" | 修改任务文件中的参数类型 |
| `E005` | 依赖循环 | "检测到角色依赖循环: A → B → A" | 重新设计团队结构，打破循环依赖 |
| `E006` | 执行超时 | "任务执行超过 {timeout}s 限制" | 增加超时配置，或优化技能流程 |
| `E007` | 输出格式错误 | "输出不符合 schema 定义，缺少字段 {field}" | 检查技能输出配置，补充缺失字段 |
| `E008` | 权限不足 | "无法写入输出目录，请检查文件权限" | 修改目录权限或更换输出路径 |

---

## 六、FAQ 反模式

### 常见坑 1：角色文件格式错误

**错误做法：**
```markdown
---
name: analyst
description: 数据分析师
skills: summarize, validate  # 错误：技能列表格式不对
---
```

**正确做法：**
```markdown
---
name: analyst
description: 数据分析师
skills:
  - summarize
  - validate
---
```

### 常见坑 2：技能参数引用错误

**错误做法：**
```yaml
process:
  - step: read
    action: load_csv
    params:
      path: "{data_path}"  # 正确
      encoding: "{encoding}"  # 错误：encoding 未在 input 中声明
```

**正确做法：**
```yaml
input:
  data_path: string
  encoding: string  # 必须先声明
process:
  - step: read
    action: load_csv
    params:
      path: "{data_path}"
      encoding: "{encoding}"
```

### 常见坑 3：忽略依赖顺序

**错误做法：**
```yaml
roles:
  - reviewer:  # 审核员先执行，但报告还没生成
      input:
        report_path: ./output/report.md
  - analyst:
      input:
        data_path: ./data/sales.csv
```

**正确做法：**
```yaml
roles:
  - analyst:  # 分析师先执行
      input:
        data_path: ./data/sales.csv
  - reviewer:  # 审核员依赖分析师输出
      input:
        report_path: ./output/report.md
```

### 常见坑 4：输出目录不存在

**错误做法：** 直接指定 `output/result.yaml` 但未创建 `output/` 目录。

**正确做法：** 在任务文件中声明输出目录，或确保目录已存在：
```yaml
output:
  dir: ./output
  create_if_missing: true  # 自动创建
```

### 常见坑 5：模型响应超长

**错误做法：** 不设置 `max_tokens`，导致模型输出被截断。

**正确做法：** 在技能中显式设置长度限制：
```yaml
process:
  - step: generate
    action: llm_call
    params:
      max_tokens: 1000  # 显式限制
      truncate: true    # 超长时截断而非报错
```

---

## 七、渐进式披露

### 速查卡（30 秒上手）

```bash
# 1. 初始化团队
agencycli --init my-team

# 2. 编辑角色和技能文件
cd my-team
# 修改 roles/*.md 和 skills/*.yaml

# 3. 创建任务
cat > tasks/my-task.yaml << EOF
team: my-team
goal: 完成数据分析
roles:
  - analyst:
      input:
        data_path: ./data.csv
EOF

# 4. 执行
agencycli --run tasks/my-task.yaml

# 5. 查看结果
cat output/result.yaml
```

### 新手阅读路径

1. 先阅读「能力边界」了解工具能做什么
2. 按「速查卡」完成一次最小流程
3. 遇到问题时查阅「错误码体系」
4. 熟悉后阅读「标准流程」深入理解配置细节

### 进阶阅读路径

1. 完整阅读「标准流程」理解所有配置项
2. 研究「FAQ 反模式」避免常见错误
3. 自定义复杂技能，参考「技能定义」示例
4. 设计多级代理团队，利用依赖关系实现复杂工作流
5. 结合外部工具扩展技能，实现 API 调用、数据持久化等高级功能

---

## 八、用户协议

使用本 Skill 即表示您同意以下条款：

1. **责任承担**：使用者自行承担使用本 Skill 的全部责任。因使用本工具产生的任何直接或间接损失，包括但不限于数据丢失、业务中断、决策失误等，工具作者不承担任何责任。

2. **禁止反向工程**：未经授权，不得对本 Skill 的代码、配置模板、算法逻辑进行反向工程、反编译、破解或试图提取源代码。

3. **合规使用**：使用者应确保使用场景符合当地法律法规，不得利用本工具从事任何违法活动。

4. **无担保声明**：本 Skill 按"现状"提供，不附带任何明示或暗示的担保，包括但不限于适销性、特定用途适用性和非侵权保证。

5. **修改与分发**：允许在遵守 MIT 许可证的前提下修改和分发本 Skill，但须保留原始版权声明。

<!-- user-agreement-injected -->

---

## 九、许可证（License）

MIT License

版权所有 (c) 2024 Lin Chen

特此免费授予任何获得本软件及相关文档文件（以下简称"软件"）副本的人士处理软件的权限，包括不受限制地使用、复制、修改、合并、发布、分发、再许可和/或销售软件副本的权利，并允许向软件所提供给的人士授予上述权利，但须满足以下条件：

上述版权声明和本许可声明应包含在软件的所有副本或重要部分中。

本软件按"现状"提供，不附带任何明示或暗示的担保，包括但不限于适销性、特定用途适用性和非侵权保证。在任何情况下，作者或版权持有人均不对任何索赔、损害或其他责任负责，无论是在合同诉讼、侵权或其他方面，由软件或软件的使用或其他交易引起或与之相关。

<!-- professional-license-embedded -->

---

*本 Skill 由 AI 辅助生成，仅供参考。使用前请阅读相关文档。*
