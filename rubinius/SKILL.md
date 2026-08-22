---
slug: rubinius
name: rubinius
displayName: 数据解析 结构化提取 信息标注
description: 将用户提供的数据、文件或URL解析为结构化结果，保留关键信息并标注置信度。
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
trigger_words: ["rubinius","数据解析","结构化提取","格式转换","信息抽取","字段映射","内容清洗"]
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# rubinius — 数据解析与结构化提取 Skill

本 Skill 由 AI 辅助生成，仅供参考。使用前请确认输入数据来源合法，并自行验证输出结果。

---

## 一、能力边界（一页纸速查卡）

### 1.1 能做什么

| 能力项 | 说明 | 示例 |
|--------|------|------|
| 文件解析 | 读取常见文本类文件（CSV、JSON、TXT、Markdown） | 将 CSV 日志转为结构化条目 |
| URL 内容提取 | 抓取公开网页正文，去除导航/广告噪声 | 提取新闻页标题、发布时间、正文 |
| 字段映射 | 将非标准字段名映射为统一 schema | `name` → `full_name` |
| 置信度标注 | 对每个输出字段给出可信度评分（0~1） | `confidence: 0.92` |
| 批量处理 | 对同一目录下多个文件执行相同解析逻辑 | 解析 `./data/*.csv` |

### 1.2 不能做什么

| 限制项 | 说明 |
|--------|------|
| 不处理二进制格式 | PDF、DOCX、图片需先经 OCR 或转换工具转为文本 |
| 不访问付费/登录墙内容 | 仅处理公开可访问的 URL |
| 不执行代码 | 不会运行输入文件中的脚本或宏 |
| 不保证字段完整性 | 源数据缺失时输出 `[需核实:字段名]` 占位，不编造 |

### 1.3 适用对象

- 需要将散乱文本整理为表格化数据的运营人员
- 需要从网页批量提取信息的调研人员
- 需要统一多来源数据格式的数据工程师

---

## 二、触发方式

### 2.1 触发词

直接使用以下任一词汇即可激活本 Skill：

`rubinius`、`数据解析`、`结构化提取`、`格式转换`、`信息抽取`、`字段映射`、`内容清洗`

### 2.2 场景映射表

| 用户说（大白话） | Skill 实际动作 |
|------------------|----------------|
| "帮我把这个 CSV 整理成规范的表格" | 读取 CSV，推断列类型，输出标准化 JSON |
| "这个网页上的信息帮我抓下来" | 请求 URL，提取正文与关键元数据 |
| "这些日志文件格式不统一，帮我统一一下" | 批量解析，字段映射到统一 schema |
| "这个数据缺了好多字段，帮我标一下" | 对缺失字段输出 `[需核实:字段名]` 占位 |

---

## 三、标准流程

### 3.1 前置条件

| 条件 | 要求 |
|------|------|
| 输入文件 | 与 Skill 运行目录一致，命名不含空格或特殊字符 |
| 输入格式 | 文本类（CSV/JSON/TXT/MD）或公开 URL |
| 目录权限 | 当前用户对输入/输出目录有读写权限 |
| 网络（仅 URL 场景） | 可访问目标网站，且目标未屏蔽爬虫 |

### 3.2 执行步骤

1. **准备输入**  
   将待处理文件放入同一目录（如 `./input/`），确认命名规范一致（如 `data_01.csv`、`data_02.csv`）。若为 URL，整理为纯文本列表，每行一个链接。

2. **试运行**  
   选取单个样本执行解析命令，核对输出字段与格式是否符合预期。  
   示例命令（伪代码）：
   ```bash
   rubinius parse --input ./input/sample.csv --schema ./schema.json
   ```

3. **批量执行**  
   确认试运行无误后，对全量数据执行。执行前自动备份原始文件至 `./backup/` 目录。

4. **校验结果**  
   抽查输出条目（建议 ≥ 10%），核对关键字段与源数据一致性。重点检查：  
   - 字段名是否映射正确  
   - 日期/数字格式是否统一  
   - 置信度低于 0.6 的字段是否已标注占位符

### 3.3 输出规范

输出为 JSON 格式，结构如下：

```json
{
  "source": "data_01.csv",
  "parsed_at": "2025-01-15T10:30:00Z",
  "records": [
    {
      "id": 1,
      "fields": {
        "full_name": {"value": "张三", "confidence": 0.98},
        "email": {"value": "zhangsan@example.com", "confidence": 0.95},
        "phone": {"value": "[需核实:phone]", "confidence": 0.0}
      }
    }
  ]
}
```

---

## 四、置信度门控

### 4.1 置信度评分规则

| 分值 | 含义 | 触发条件 |
|------|------|----------|
| 0.9~1.0 | 高可信 | 字段值完整且格式校验通过 |
| 0.7~0.89 | 中可信 | 字段值存在但格式有轻微异常（如多余空格） |
| 0.5~0.69 | 低可信 | 字段值存在但内容疑似截断或乱码 |
| 0.0 | 缺失 | 字段不存在或无法提取 |

### 4.2 占位符规则

- 当字段无法提取时，输出 `[需核实:字段名]`，置信度置 0.0。
- 禁止用猜测值填充缺失字段。
- 若某条记录超过 30% 字段为占位符，整条记录标记 `"valid": false`。

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| E001 | 文件不存在 | "未找到指定文件，请检查路径" | 确认文件路径，重新输入 |
| E002 | 文件格式不支持 | "仅支持 CSV/JSON/TXT/MD 格式" | 转换文件格式后重试 |
| E003 | URL 无法访问 | "目标地址返回 404 或超时" | 检查 URL 拼写，或更换网络环境 |
| E004 | 字段映射冲突 | "同一字段映射到多个目标字段" | 检查 schema 配置，删除重复映射 |
| E005 | 批量执行中断 | "第 3 个文件解析失败，已跳过" | 查看错误日志，单独处理失败文件 |

---

## 六、FAQ 反模式

### 6.1 常见坑

| 坑 | 反模式描述 | 正确做法 |
|----|------------|----------|
| 忽略试运行 | 直接跑全量，导致 schema 错误扩散 | 务必先跑单样本，确认无误再批量 |
| 覆盖原始文件 | 输出直接写回源文件，无备份 | 输出到独立目录，保留 `./backup/` |
| 编造缺失值 | 对缺失字段填"未知"或"无" | 使用 `[需核实:字段名]` 占位 |
| 忽略置信度 | 所有字段一视同仁，不区分可信度 | 下游使用前先过滤低置信度记录 |
| 批量无校验 | 全量跑完不抽查，错误未被发现 | 至少抽查 10% 输出与源数据比对 |

### 6.2 反模式对照表

| 反模式 | 后果 | 替代方案 |
|--------|------|----------|
| 用正则硬匹配所有字段 | 格式稍有变化即失效 | 先做字段类型推断，再匹配 |
| 对 URL 内容不做去噪 | 提取结果含大量导航/广告文本 | 先提取正文区块，再解析字段 |
| 一次解析所有文件类型 | 逻辑复杂且易出错 | 按文件类型分批次处理 |

---

## 七、渐进式披露

### 7.1 速查卡（30 秒上手）

1. 文件放 `./input/`，命名规范。
2. 跑 `rubinius parse --input ./input/sample.csv` 试运行。
3. 确认输出字段无误后，跑全量。
4. 抽查输出，检查置信度标注。

### 7.2 新手路径（首次使用）

- 阅读「能力边界」→ 确认输入格式符合要求。
- 按「标准流程」步骤 1~2 完成一次试运行。
- 遇到问题查「错误码体系」对照修正。

### 7.3 进阶路径（深度使用）

- 自定义 schema 文件，实现复杂字段映射。
- 编写后处理脚本，过滤低置信度记录。
- 对接 CI/CD 流程，实现定时批量解析。

---

## 用户协议

使用本 Skill 即表示您同意以下条款：

1. **责任承担**：使用者自行承担全部责任。因使用本 Skill 产生的任何直接或间接损失，作者不承担任何责任。
2. **合法使用**：使用者须确保输入数据来源合法，不得用于侵犯他人隐私、知识产权或违反法律法规的场景。
3. **禁止反向工程**：使用者不得对本 Skill 的底层逻辑进行反向工程、反编译或试图提取源代码（除非适用法律允许）。
4. **无担保**：本 Skill 按"现状"提供，不附带任何明示或暗示的担保。

<!-- user-agreement-injected -->

---

## 许可证（License）

本 Skill 采用 MIT 许可证发布。

```
MIT License

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
```

<!-- professional-license-embedded -->
