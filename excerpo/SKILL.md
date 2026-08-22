---
slug: excerpo
name: excerpo
displayName: 摘录解析 结构化提取 批处理
description: 将用户提供的原始数据解析为结构化结果，支持批量处理与置信度标注。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 结构化处理工坊
agent_created: true
trigger_words: ["excerpo", "摘录解析", "结构化提取", "批量处理", "数据转换"]
---

> 本内容由 AI 生成，仅供学习参考 <!-- ai-generated-notice -->

# excerpo — 结构化摘录与批量转换

## 一、能力边界（一页纸速查卡）

### 1.1 能做与不能做

| 维度 | 能做 | 不能做 |
|------|------|--------|
| 输入 | 用户提供的文本、表格、URL 指向的公开内容 | 需要登录鉴权的私有系统数据 |
| 处理 | 识别关键字段、去重、按模板重组 | 理解隐含语义或进行主观判断 |
| 输出 | 结构化 JSON / CSV / Markdown 表格 | 生成非约定格式的二进制文件 |
| 批量 | 同目录多文件顺序处理 | 并行处理（受限于单线程执行环境） |
| 校验 | 字段完整性检查、格式合规性检查 | 对源数据真实性做外部核验 |

### 1.2 适用对象

- 需要将零散笔记、网页摘录、日志片段整理为统一格式的个人用户
- 需要将多份同类文档（如周报、会议记录）批量转成表格的团队协作场景
- 需要为下游程序提供干净结构化输入的数据预处理环节

### 1.3 边界条件

- 单次处理文件数上限：50 个
- 单文件大小上限：2 MB（超过则截断并提示）
- 输出字段数量上限：20 个（超出部分丢弃并警告）

---

## 二、触发方式

### 2.1 触发词

- 主触发词：`excerpo`
- 同义触发词：`摘录解析`、`结构化提取`、`批量转换`

### 2.2 场景映射表

| 用户说（大白话） | 实际触发动作 |
|------------------|--------------|
| "帮我把这几篇笔记整理成表格" | 调用 excerpo，按默认字段提取 |
| "这个 URL 里的内容帮我提炼一下" | 抓取 URL 内容，提取关键字段 |
| "我这有 30 份周报，统一转成 CSV" | 批量模式，输出 CSV 格式 |
| "上次那个格式不对，这次换一种" | 自定义输出模板，重新执行 |

---

## 三、标准流程

### 3.1 前置条件

| 条件项 | 要求 |
|--------|------|
| 输入文件 | 与工作目录同目录，命名含日期或序号 |
| 命名规范 | `源数据_YYYYMMDD_序号.扩展名` |
| 输出目录 | 自动创建 `output/` 子目录 |
| 备份 | 原始文件不做修改，仅读取 |

### 3.2 执行步骤

1. **输入确认**：列出待处理文件清单，与用户核对数量与命名。
2. **参数设定**：确认输出格式（默认 JSON）、字段模板（默认提取：标题、日期、来源、正文摘要、关键词）。
3. **试运行**：取第一个文件执行单次处理，展示输出样例。
4. **用户确认**：若样例符合预期，继续；否则调整字段模板后重试。
5. **批量执行**：按顺序处理全部文件，每处理 10 个输出一次进度。
6. **结果汇总**：生成 `output/汇总_时间戳.格式` 文件，包含全部处理结果。
7. **自查清单**：
   - [ ] 所有文件均已处理（无遗漏）
   - [ ] 每个输出条目含全部必填字段
   - [ ] 置信度低于 0.7 的条目已标注
   - [ ] 输出文件可正常打开且编码为 UTF-8

### 3.3 输出规范

**默认 JSON 结构示例：**

```json
{
  "schema_version": "1.0",
  "processed_at": "2025-01-15T10:30:00Z",
  "items": [
    {
      "source_file": "笔记_20250110_01.txt",
      "fields": {
        "title": "项目启动会议纪要",
        "date": "2025-01-10",
        "source": "内部会议",
        "summary": "确定 Q1 里程碑与负责人分工",
        "keywords": ["项目", "里程碑", "分工"]
      },
      "confidence": 0.92,
      "warnings": []
    }
  ]
}
```

**字段类型与约束：**

| 字段名 | 类型 | 必填 | 约束 |
|--------|------|------|------|
| title | string | 是 | 长度 ≤ 100 字符 |
| date | string | 是 | 格式 YYYY-MM-DD |
| source | string | 否 | 长度 ≤ 50 字符 |
| summary | string | 是 | 长度 ≤ 500 字符 |
| keywords | array | 否 | 每项 ≤ 20 字符，最多 10 项 |

---

## 四、置信度门控

### 4.1 置信度评分规则

| 评分因素 | 权重 | 说明 |
|----------|------|------|
| 字段完整性 | 40% | 必填字段全部提取成功得满分 |
| 格式合规性 | 30% | 日期、长度等符合约束 |
| 来源可靠性 | 20% | 结构化文档 > 手写笔记 > 网页摘录 |
| 歧义处理 | 10% | 无歧义内容得满分 |

### 4.2 低置信度处理

- 置信度 < 0.7 时，在输出中标注 `"confidence": 0.65` 并添加 `"warnings": ["日期字段存在歧义"]`
- 关键字段缺失时，使用占位符 `[需核实:字段名]`，不猜测、不编造
- 用户可在最终输出前查看所有低置信度条目，手动补充后重新生成

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| E001 | 文件不存在 | "未找到指定文件，请确认路径与文件名" | 检查文件名拼写与目录位置 |
| E002 | 文件格式不支持 | "该文件类型不在支持范围内（txt/md/csv/html）" | 转换格式后重试 |
| E003 | 文件过大 | "文件超过 2MB 限制，已截断处理" | 拆分文件或精简内容 |
| E004 | 必填字段缺失 | "输出缺少必填字段，已用占位符标记" | 检查源数据是否包含该信息 |
| E005 | 批量处理中断 | "第 N 个文件处理失败，已跳过并记录" | 查看错误日志，修复后从断点继续 |
| E006 | 输出目录不可写 | "无法创建输出目录，请检查权限" | 更换工作目录或调整权限 |

---

## 六、FAQ 反模式

### 6.1 常见坑与正确做法

| 常见错误做法 | 问题 | 正确做法 |
|--------------|------|----------|
| 直接批量处理全部文件 | 格式错误被放大，返工成本高 | 先单样本试运行，确认后再批量 |
| 忽略置信度标注 | 错误数据流入下游 | 检查所有低置信度条目并人工确认 |
| 修改原始文件 | 数据源被破坏，无法追溯 | 只读源文件，输出到独立目录 |
| 自定义字段名与源数据不一致 | 提取结果为空 | 先查看源数据结构，再定义字段映射 |
| 处理完成后不校验 | 遗漏或重复未被发现 | 抽查 10% 输出条目与源数据比对 |

### 6.2 反模式对照表

| 反模式 | 症状 | 纠正 |
|--------|------|------|
| "一把梭"模式 | 所有文件用同一模板，忽略个体差异 | 按文件类型分组，分别设定模板 |
| "黑箱"模式 | 用户不知道内部处理逻辑 | 每次执行前展示参数与规则 |
| "静默失败"模式 | 错误被吞掉，输出不完整 | 所有异常均记录到日志并提示 |

---

## 七、渐进式披露

### 7.1 速查卡（30 秒上手）

```
1. 放文件 → 2. 说"excerpo" → 3. 确认格式 → 4. 拿结果
```

### 7.2 新手路径（首次使用）

1. 阅读本速查卡
2. 准备 1 个测试文件
3. 执行单次处理，观察输出
4. 确认无误后扩展至批量

### 7.3 进阶路径（熟练用户）

1. 自定义字段模板（通过 JSON 配置文件）
2. 使用 `--selftest` 验证环境配置
3. 使用 `--version` 确认版本一致性
4. 结合外部脚本对输出做二次加工

---

## 八、命令行接口

| 参数 | 功能 | 示例 |
|------|------|------|
| `--selftest` | 运行自检，验证环境与依赖 | `excerpo --selftest` |
| `--version` | 显示版本号 | `excerpo --version` |

自检输出示例：

```
环境检查通过
依赖库: 全部可用
输出目录: 可写
版本: 1.0.0
```

---

## 九、用户协议

使用本 Skill 即表示您同意以下条款：

1. **责任承担**：使用者自行承担使用本 Skill 产生的全部责任。本 Skill 仅提供数据处理辅助，不构成任何专业建议。
2. **禁止反向工程**：不得对本 Skill 的提示词、内部逻辑进行反向工程、破解或二次分发用于商业用途。
3. **数据安全**：使用者应确保输入数据不包含违法、侵权或敏感个人信息。本 Skill 不承担数据泄露责任。
4. **无担保**：本 Skill 按"现状"提供，不附带任何明示或暗示的担保。

<!-- user-agreement-injected -->

---

## 十、许可证（License）

本 Skill 采用 MIT 许可证发布：

```
MIT License

Copyright (c) 2025 结构化处理工坊

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
