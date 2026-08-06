---
slug: exam-question-gen
name: exam-question-gen
displayName: 智能出题 知识点覆盖 题型难度配置
description: 按知识点、题型与难度自动生成配套解析的练习题，支持批量组卷与结构化输出。
version: 2.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: SkillForge Studio
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: SkillForge Studio
agent_created: true
trigger_words: ["出题", "生成题目", "组卷", "测验生成", "练习题", "习题生成", "试卷生成"]
---

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->

> 📜 **用户协议（User Agreement）**
> 1. 本 Skill 仅供学习与参考用途。使用本 Skill 产生的任何结果，由使用者自行承担全部责任；本 Skill 不提供任何明示或暗示的保证。
> 2. 涉及法律、财务、税务、投资、医疗等专业决策时，请务必咨询持证专业人士。
> 3. 本代码受版权法保护，未经授权复制、反向工程或商业利用将被追究法律责任。
<!-- user-agreement-injected -->


# 智能出题 Skill 使用指南

## 一、能力边界（一页纸速查卡）

### 1.1 能做什么（真实实现）

| 能力项 | 说明 | 示例 |
|--------|------|------|
| 按知识点出题 | 从内置题库中筛选指定知识点 | `--point 数据结构` |
| 题型指定 | 单选/多选/填空/判断/解答 | `--type 单选` |
| 难度配置 | 简单(1)/中等(2)/困难(3)，支持比例 | `--difficulty 1:2:1` |
| 数量控制 | 指定题目数量，默认 5 道 | `--count 8` |
| 批量生成 | 多知识点、多题型组合出题 | `--point 数据结构 --type 单选,多选` |
| 结构化输出 | 支持 Markdown 或 JSON 格式 | `--format json` |
| 组卷建议 | 附带分值分配与时间规划 | `--with-suggestions` |
| 自检模式 | 验证核心功能是否正常 | `--selftest` |

### 1.2 不能做什么（真实限制）

| 限制项 | 说明 |
|--------|------|
| 无知识点输入 | 使用默认知识点"Python基础" |
| 不保证教学效果 | 题目仅用于练习，不替代系统教学 |
| 不生成超纲内容 | 难度上限为 3（困难），不涉及竞赛级 |
| 不提供答案详解 | 仅提供正确答案和简要解析，不生成解题思路 |
| 不联网获取数据 | 题库为内置静态数据，不进行网络请求 |

### 1.3 适用对象

- 教师：快速生成课堂练习或课后作业
- 学生：自主练习，巩固知识点
- 培训机构：批量生成测验试卷
- 教育产品开发者：程序化调用生成题目数据

## 二、触发条件

当用户输入包含以下关键词时触发本 Skill：
- 出题、生成题目、组卷、测验生成、练习题、习题生成、试卷生成

## 三、标准流程

### 3.1 输入解析
1. 识别知识点（`--point`，默认"Python基础"）
2. 识别题型（`--type`，默认"单选"）
3. 识别难度（`--difficulty`，默认"1:2:1"）
4. 识别数量（`--count`，默认 5）
5. 识别输出格式（`--format`，默认 markdown）

### 3.2 题目筛选
1. 按知识点过滤题库
2. 按题型过滤
3. 按难度分布比例分配
4. 随机抽样（使用 `random.SystemRandom` 保证安全性）

### 3.3 输出生成
- Markdown 格式：人类可读的题目列表
- JSON 格式：结构化数据，便于程序处理

## 四、置信度门控

| 条件 | 置信度 | 处理方式 |
|------|--------|----------|
| 题库中有足够匹配题目 | 高 | 正常生成 |
| 匹配题目不足 | 中 | 降低难度要求，补充相近题目 |
| 无匹配题目 | 低 | 返回错误码 E1001，提示用户调整参数 |

## 五、错误码

| 错误码 | 含义 | 处理建议 |
|--------|------|----------|
| E1001 | 无匹配题目 | 调整知识点或题型 |
| E1002 | 参数无效 | 检查参数格式 |
| E1003 | 输出格式不支持 | 使用 markdown 或 json |

## 六、FAQ 反模式

### 6.1 常见错误用法
- ❌ 不指定知识点就要求"超纲题" → 系统无法生成
- ❌ 要求"所有题型各 100 道" → 题库容量有限
- ❌ 期望联网获取最新题目 → 题库为静态数据

### 6.2 正确用法
- ✅ 明确指定知识点和题型
- ✅ 合理设置数量（建议 1-20 道）
- ✅ 使用 `--selftest` 验证功能

## 七、命令行用法

## 许可证（License）

```text
MIT License

Copyright (c) {year} {holder}

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
