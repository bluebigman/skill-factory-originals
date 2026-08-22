---
slug: jsawesome
name: jsawesome
displayName: 数据转换 结构化处理 批量执行
description: 将用户输入的数据、文件或URL转换为结构化结果，支持批量处理与自定义格式。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: SkillForge Studio
agent_created: true
trigger_words: ["jsawesome", "数据转换", "结构化处理", "批量执行", "格式转换"]
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# jsawesome 技能文档

## 一、能力边界（一页纸速查卡）

### 1.1 能做（核心能力）

| 编号 | 能力项 | 说明 |
|------|--------|------|
| C1 | 数据/文件/URL 结构化转换 | 将用户提供的原始输入（文本、文件、链接）解析为结构化结果 |
| C2 | 关键信息识别与保留 | 自动提取输入中的核心字段，保留原始语义 |
| C3 | 约定格式输出 | 按用户指定或系统默认的格式生成结果（JSON/YAML/CSV等） |
| C4 | 置信度标注 | 对每个输出字段标注可信程度，不确定时明确提示 |
| C5 | 批量处理与自定义格式 | 支持多文件/多条目批量执行，支持用户自定义输出模板 |

### 1.2 不能做（明确边界）

| 编号 | 限制项 | 说明 |
|------|--------|------|
| L1 | 不执行代码 | 本技能仅做数据转换与格式化，不运行或执行任何代码逻辑 |
| L2 | 不访问外部网络 | 对 URL 的处理仅限解析链接本身，不抓取网页内容 |
| L3 | 不修改原始文件 | 所有操作基于副本，原始数据保持只读 |
| L4 | 不处理加密内容 | 加密文件或受密码保护的数据需先由用户解密 |
| L5 | 不保证绝对准确 | 所有输出均带置信度标注，高置信度≠100%正确 |

### 1.3 适用对象

- 需要将散乱数据整理为统一格式的开发者
- 需要批量处理数据文件的运维人员
- 需要从 URL 中提取结构化信息的研究人员
- 需要自定义输出格式的数据分析师

---

## 二、触发方式

### 2.1 触发词

- 主触发词：`jsawesome`
- 同义场景词：`数据转换`、`结构化处理`、`批量执行`、`格式转换`

### 2.2 场景映射表

| 用户说（大白话） | 实际需求 | 触发动作 |
|------------------|----------|----------|
| "帮我把这几个文件整理一下" | 多文件批量结构化 | 执行批量处理流程 |
| "这个链接里的信息提取出来" | URL 内容解析 | 解析链接并提取字段 |
| "输出成 JSON 格式" | 自定义输出格式 | 按 JSON 模板生成 |
| "这个数据靠谱吗" | 置信度评估 | 输出置信度标注 |
| "先跑一个试试" | 单样本试运行 | 执行试运行流程 |

---

## 三、标准流程

### 3.1 前置条件

| 条件项 | 要求 | 检查方式 |
|--------|------|----------|
| 输入文件 | 文件命名规范一致，扩展名正确 | 目视检查 + 文件头校验 |
| 输入格式 | 文本/JSON/CSV/URL 均可 | 自动识别 |
| 输出格式 | 用户指定或默认 JSON | 确认配置 |
| 环境 | 当前目录可写 | 权限检查 |

### 3.2 执行步骤

**Step 1：准备输入**

1. 将待处理文件放入当前工作目录
2. 确认所有文件命名符合统一规范（如 `data_01.txt`、`data_02.txt`）
3. 记录文件清单及数量

**Step 2：试运行**

1. 选取单个样本文件执行转换
2. 核对输出字段是否完整
3. 检查格式是否符合预期
4. 确认置信度标注是否合理

**Step 3：批量执行**

1. 确认试运行无误后，对全量文件执行
2. 保留原始文件备份（自动创建 `backup_YYYYMMDD/` 目录）
3. 输出结果写入 `output/` 目录

**Step 4：校验结果**

1. 随机抽查 10% 输出条目
2. 核对关键字段与源数据一致性
3. 检查置信度标注是否准确
4. 生成校验报告

### 3.3 输出规范

**默认输出格式（JSON）：**

```json
{
  "schema_version": "1.0",
  "processed_at": "2025-01-15T10:30:00Z",
  "items": [
    {
      "id": "001",
      "source": "data_01.txt",
      "fields": {
        "field_name": "value"
      },
      "confidence": {
        "field_name": 0.95
      }
    }
  ]
}
```

**字段说明：**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| schema_version | string | 是 | 输出格式版本号 |
| processed_at | string | 是 | 处理时间（ISO 8601） |
| items | array | 是 | 处理结果列表 |
| items[].id | string | 是 | 条目唯一标识 |
| items[].source | string | 是 | 源文件/URL 名称 |
| items[].fields | object | 是 | 提取的字段键值对 |
| items[].confidence | object | 是 | 各字段置信度（0-1） |

---

## 四、置信度门控

### 4.1 置信度等级

| 等级 | 范围 | 含义 | 处理方式 |
|------|------|------|----------|
| 高 | 0.90-1.00 | 字段提取明确，无歧义 | 正常输出 |
| 中 | 0.70-0.89 | 字段存在但可能有变体 | 输出并附注说明 |
| 低 | 0.50-0.69 | 字段推断得出，存在不确定性 | 输出并标注 [需核实] |
| 不可用 | <0.50 | 无法确定字段值 | 输出 `[需核实:字段名]` 占位 |

### 4.2 处理规则

1. **信息不足时**：使用 `[需核实:字段名]` 占位，不编造数据
2. **冲突信息**：保留所有候选值，标注各候选置信度
3. **缺失字段**：明确标注 `[缺失]`，不自动填充默认值
4. **格式异常**：标记 `[格式异常]`，附原始内容供参考

### 4.3 示例

**输入：**
```
张三，电话：138-1234-5678，邮箱：zhangsan@example.com
```

**输出：**
```json
{
  "fields": {
    "name": "张三",
    "phone": "138-1234-5678",
    "email": "zhangsan@example.com"
  },
  "confidence": {
    "name": 0.98,
    "phone": 0.95,
    "email": 0.92
  }
}
```

---

## 五、错误码体系

| 错误码 | 错误描述 | 用户提示话术 | 修正步骤 |
|--------|----------|--------------|----------|
| E001 | 文件不存在 | "未找到指定文件，请确认路径是否正确" | 1. 检查文件路径 2. 确认文件名 3. 重新执行 |
| E002 | 文件格式不支持 | "当前文件格式不在支持范围内" | 1. 转换为支持的格式 2. 或使用 --format 指定 |
| E003 | 字段解析失败 | "部分字段无法解析，已标记为需核实" | 1. 查看输出中的 [需核实] 标记 2. 手动补充 |
| E004 | 批量处理中断 | "批量处理在第 N 个文件处中断" | 1. 检查第 N 个文件 2. 修复后从断点继续 |
| E005 | 输出目录不可写 | "无法写入输出目录，请检查权限" | 1. 检查目录权限 2. 更换输出路径 |
| E006 | URL 格式无效 | "提供的 URL 格式不正确" | 1. 检查 URL 语法 2. 确认协议头（http/https） |
| E007 | 置信度低于阈值 | "存在低置信度字段，请人工复核" | 1. 查看低置信度字段 2. 确认或修正数据 |
| E008 | 输入为空 | "未检测到有效输入内容" | 1. 检查输入文件 2. 确认内容非空 |

---

## 六、FAQ 反模式

### 6.1 常见坑

| 坑编号 | 常见错误 | 反模式（错误做法） | 正确做法 |
|--------|----------|--------------------|----------|
| F1 | 跳过试运行 | 直接对全量数据执行，导致格式错误扩散 | 先单样本试运行，确认无误再批量 |
| F2 | 忽略置信度 | 将低置信度字段当作确定值使用 | 对低置信度字段进行人工复核 |
| F3 | 覆盖原始文件 | 直接修改源文件，无法回滚 | 始终保留原始文件备份 |
| F4 | 编造缺失数据 | 对缺失字段自动填充猜测值 | 使用 [需核实] 占位，由用户确认 |
| F5 | 忽略格式校验 | 输出后不检查格式，导致下游解析失败 | 每次输出后执行 schema 校验 |

### 6.2 反模式对照表

| 场景 | 反模式 | 推荐模式 |
|------|--------|----------|
| 用户说"直接全部处理" | 跳过试运行直接批量 | 坚持先试运行，说明风险 |
| 用户说"缺的字段随便填" | 自动填充默认值 | 使用占位符，标注需核实 |
| 用户说"不用备份" | 不保留原始文件 | 自动创建备份目录 |
| 用户说"置信度不用标" | 移除置信度标注 | 保留标注，说明其重要性 |

---

## 七、渐进式披露

### 7.1 速查卡（30秒上手）

```
1. 放入文件 → 2. 试运行 → 3. 批量执行 → 4. 校验结果
```

### 7.2 新手路径（首次使用）

1. 阅读「能力边界」了解能做什么
2. 按「标准流程」执行一次完整流程
3. 遇到问题查「错误码体系」
4. 输出结果关注「置信度标注」

### 7.3 进阶路径（熟练使用）

1. 自定义输出格式模板
2. 批量处理参数调优
3. 置信度阈值自定义
4. 错误恢复与断点续跑
5. 与其他工具链集成

---

## 八、命令行接口

### 8.1 参数说明

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--selftest` | 运行自检，验证环境配置 | 无 |
| `--version` | 显示版本信息 | 无 |
| `--input` | 指定输入文件/目录 | 当前目录 |
| `--output` | 指定输出目录 | `./output` |
| `--format` | 输出格式（json/yaml/csv） | `json` |
| `--confidence-threshold` | 置信度阈值（0-1） | `0.5` |

### 8.2 使用示例

```bash
# 运行自检
jsawesome --selftest

# 显示版本
jsawesome --version

# 单文件处理
jsawesome --input data.txt --output result.json

# 批量处理
jsawesome --input ./data/ --output ./result/ --format json

# 自定义置信度阈值
jsawesome --input data.txt --confidence-threshold 0.7
```

---

## 九、用户协议

<!-- user-agreement-injected -->

**使用本技能即表示您同意以下条款：**

1. **责任承担**：使用者自行承担使用本技能产生的一切后果与责任。本技能提供的输出结果仅供参考，不构成任何形式的保证或承诺。

2. **禁止反向工程**：不得对本技能进行反向工程、反编译、破解或试图提取底层算法。

3. **合规使用**：使用者应确保使用场景符合当地法律法规，不得将本技能用于任何非法用途。

4. **数据安全**：使用者应对输入数据的合法性、合规性负责，不得输入涉及国家秘密、商业秘密或个人隐私的敏感数据。

5. **免责声明**：本技能按"现状"提供，不提供任何明示或暗示的保证，包括但不限于适销性、特定用途适用性和非侵权性。

---

## 十、许可证（License）

<!-- professional-license-embedded -->

**MIT License**

```
MIT License

Copyright (c) 2025 SkillForge Studio

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

*本 Skill 由 AI 辅助生成，仅供参考。使用前请阅读相关文档。*
