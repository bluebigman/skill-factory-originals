---
slug: pscale-workflow-helper-scripts
name: pscale-workflow-helper-scripts
displayName: 流程编排 批量转换 结果校验
description: 将用户输入转换为结构化结果，支持批量处理与置信度标注。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 林默
agent_created: true
trigger_words: ["pscale workflow helper scripts", "任务管理自动化", "流程辅助脚本", "工作流编排", "pscale workflow", "批量转换", "结构化输出", "置信度标注"]
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# pscale-workflow-helper-scripts 技能文档

本 Skill 由 AI 辅助生成，仅供参考。使用前请结合自身场景验证输出质量。

---

## 一、能力边界（一页纸速查卡）

### 1.1 能做什么

| 能力项 | 说明 | 示例 |
|--------|------|------|
| 输入转结构化 | 将自由文本/表格数据转换为统一字段的 JSON 或 CSV 输出 | 将日志行转换为 `{时间, 级别, 消息}` |
| 批量处理 | 对同一目录下多个文件按相同规则执行转换 | 一次处理 200 个 `.txt` 报告 |
| 置信度标注 | 对每条输出附加 `confidence` 字段（0~1 浮点） | `"confidence": 0.92` |
| 字段缺失占位 | 信息不足时输出 `[需核实:字段名]` 占位符 | `"author": "[需核实:author]"` |
| 试运行模式 | 支持单样本先行验证，再全量执行 | `--dry-run` 参数 |

### 1.2 不能做什么

| 限制项 | 说明 |
|--------|------|
| 不执行外部系统写入 | 不直接调用数据库、API 或消息队列 |
| 不处理非文本输入 | 不支持图片、音频、视频的直接解析 |
| 不保证语义理解 | 仅做规则/模板匹配，不做 NLP 深度推理 |
| 不自动修复源数据 | 源文件格式错误时仅报错，不自动改写 |

### 1.3 适用对象

- 需要将散乱文本整理为固定字段的运营人员
- 需要批量预处理数据供下游分析的数据工程师
- 需要快速验证转换规则是否正确的测试人员

---

## 二、触发方式

### 2.1 触发词速查

| 触发词 | 场景说明 |
|--------|----------|
| `pscale workflow helper scripts` | 直接调用本技能主命令 |
| `任务管理自动化` | 需要将任务描述转为结构化清单时 |
| `流程辅助脚本` | 需要批量处理脚本输出时 |
| `工作流编排` | 需要设计多步骤转换流程时 |
| `批量转换` | 明确要求对多个文件执行转换 |
| `结构化输出` | 要求输出为 JSON/CSV 等固定格式 |
| `置信度标注` | 要求对每条结果给出可信度评分 |

### 2.2 场景映射表

| 用户说（大白话） | 实际触发动作 |
|------------------|--------------|
| "帮我把这些日志整理成表格" | 执行输入转结构化 + 批量处理 |
| "这个目录下所有文件都跑一遍" | 执行批量执行模式 |
| "这条记录我不确定对不对" | 触发置信度标注，低置信度输出占位符 |
| "先拿一个文件试试看" | 执行试运行模式 |

---

## 三、标准流程

### 3.1 前置条件

| 条件 | 要求 | 检查方式 |
|------|------|----------|
| 输入文件目录 | 所有待处理文件位于同一目录 | `ls -la ./input/` |
| 命名规范 | 文件名遵循 `prefix_YYYYMMDD.ext` 格式 | 正则匹配 `^[a-z]+_\d{8}\.(txt\|log\|csv)$` |
| 备份 | 原始文件已复制到 `./backup/` | `cp -r ./input/ ./backup/` |
| 规则文件 | 转换规则已定义（JSON 模板） | `cat rules.json` |

### 3.2 执行步骤

1. **准备输入**  
   将待处理文件放入 `./input/` 目录，确认命名规范一致。  
   若命名不一致，先执行重命名脚本：  
   ```bash
   for f in ./input/*.txt; do mv "$f" "$(echo $f | sed 's/^\(.*\)\.txt$/prefix_$(date +%Y%m%d)_\1.txt/')"; done
   ```

2. **试运行**  
   使用单个样本执行转换，核对输出字段与格式：  
   ```bash
   pscale workflow helper scripts --dry-run --input ./input/sample_001.txt --rules rules.json
   ```
   检查输出 JSON 是否包含全部目标字段，且无 `[需核实:]` 占位符异常。

3. **批量执行**  
   确认无误后对全量数据执行：  
   ```bash
   pscale workflow helper scripts --batch --input ./input/ --rules rules.json --output ./output/
   ```
   执行期间保留原始文件备份（`./backup/` 目录）。

4. **校验结果**  
   抽查输出条目（建议抽取 5%~10%），核对关键字段与源数据一致：  
   ```bash
   python -c "import json; data=json.load(open('./output/result.json')); print(data[0])"
   ```
   重点核对：时间戳、ID、状态字段。

### 3.3 输出规范

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `id` | string | 是 | 源文件名去扩展名 |
| `timestamp` | ISO8601 | 是 | 处理时间 |
| `content` | string | 是 | 转换后的结构化内容 |
| `confidence` | float | 是 | 0~1 置信度，低于 0.6 时输出占位符 |
| `source_file` | string | 是 | 原始文件名 |
| `error_code` | string | 否 | 出错时填充错误码 |

---

## 四、置信度门控

### 4.1 置信度判定规则

| 条件 | 置信度 | 输出行为 |
|------|--------|----------|
| 所有字段均匹配规则模板 | 0.9~1.0 | 正常输出 |
| 部分字段匹配，部分缺失 | 0.6~0.89 | 缺失字段输出 `[需核实:字段名]` |
| 关键字段缺失或格式错误 | <0.6 | 整条输出 `[需核实:整条记录]`，并附错误码 |

### 4.2 占位符使用规范

- 占位符格式：`[需核实:字段名]`
- 占位符不得被后续处理自动替换，必须人工确认
- 批量输出中占位符占比超过 20% 时，建议暂停并检查规则文件

### 4.3 禁止行为

- 禁止在信息不足时编造字段值
- 禁止将低置信度结果标记为高置信度
- 禁止忽略 `[需核实:]` 占位符直接进入下游流程

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| `E001` | 输入文件不存在 | "未找到指定输入文件，请检查路径" | 确认文件路径，重新执行 |
| `E002` | 命名规范不符 | "文件名不符合 prefix_YYYYMMDD.ext 格式" | 重命名文件后重试 |
| `E003` | 规则文件解析失败 | "规则文件 JSON 格式错误" | 使用 `jq . rules.json` 校验语法 |
| `E004` | 字段映射缺失 | "规则中未定义字段 xxx 的映射" | 在规则文件中补充映射 |
| `E005` | 批量执行中断 | "第 N 个文件处理失败，已跳过" | 查看 `./output/error.log`，修复后重跑 |
| `E006` | 输出目录不可写 | "无法写入输出目录，请检查权限" | 修改目录权限或更换路径 |

---

## 六、FAQ 反模式

### 6.1 常见坑

| 坑 | 反模式示例 | 正确做法 |
|----|------------|----------|
| 跳过试运行 | 直接批量执行，结果全错 | 必须先用单样本验证 |
| 覆盖原始文件 | 批量执行后原文件被覆盖 | 始终保留 `./backup/` 备份 |
| 忽略置信度 | 低置信度结果直接入库 | 人工复核所有 `[需核实:]` 条目 |
| 规则不匹配 | 规则文件与输入格式不匹配 | 先检查规则模板再执行 |
| 无错误日志 | 失败后无任何记录 | 确保输出目录生成 `error.log` |

### 6.2 反模式对照表

| 反模式 | 问题 | 替代方案 |
|--------|------|----------|
| "先跑完再说" | 批量执行后才发现规则错误 | 先试运行 1 个样本 |
| "这个字段猜一下就行" | 编造数据导致下游错误 | 输出 `[需核实:字段]` |
| "全量跑完再检查" | 错误累积难以定位 | 每 50 条抽查一次 |
| "规则改一下就行" | 规则变更未同步测试 | 每次改规则后重新试运行 |

---

## 七、渐进式披露

### 7.1 速查卡（30 秒上手）

```
1. 放文件到 ./input/
2. 确认命名规范
3. 试运行：--dry-run --input sample
4. 检查输出字段
5. 批量执行：--batch --input ./input/
6. 抽查 5% 结果
```

### 7.2 新手路径（首次使用）

1. 阅读「能力边界」了解适用范围
2. 按「标准流程」步骤 1~2 完成试运行
3. 确认输出格式无误后进入批量执行
4. 遇到问题查「错误码体系」

### 7.3 进阶路径（熟练用户）

1. 自定义规则文件，支持复杂字段映射
2. 编写后处理脚本，自动处理 `[需核实:]` 占位符
3. 集成到 CI/CD 流水线，实现定时批量转换
4. 使用置信度阈值自动分流高低质量数据

---

## 八、参数速查表

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `--input` | string | 是 | 无 | 输入文件或目录路径 |
| `--output` | string | 否 | `./output/` | 输出目录 |
| `--rules` | string | 是 | 无 | 规则文件路径（JSON） |
| `--dry-run` | bool | 否 | `false` | 试运行模式 |
| `--batch` | bool | 否 | `false` | 批量执行模式 |
| `--confidence-threshold` | float | 否 | `0.6` | 置信度阈值 |
| `--selftest` | bool | 否 | `false` | 自检模式 |
| `--version` | bool | 否 | `false` | 显示版本号 |

---

## 九、用户协议

<!-- user-agreement-injected -->

**使用本 Skill 即表示您同意以下条款：**

1. **责任承担**：使用者自行承担因使用本 Skill 产生的全部责任。包括但不限于数据丢失、处理错误、输出不准确等风险。
2. **禁止反向工程**：不得对本 Skill 的底层逻辑进行反向工程、反编译或试图提取源代码（除非适用法律允许）。
3. **无担保**：本 Skill 按"现状"提供，不附带任何明示或暗示的担保。
4. **合规使用**：使用者须确保使用场景符合当地法律法规及所在组织的规定。

---

## 十、许可证（License）

<!-- professional-license-embedded -->

**MIT License**

Copyright (c) 2025 林默

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

*文档版本：1.0.0 | 最后更新：2025-01-01 | 适用场景：批量文本转结构化处理*
