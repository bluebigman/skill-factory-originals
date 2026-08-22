---
slug: gsa-prototype
name: gsa-prototype
displayName: 协议转换 跨域映射 数据校验
description: 将GSA协议文本转为结构化JSON，支持跨域映射与校验。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 协议工坊
agent_created: true
trigger_words: ["gsa prototype", "GSA搜索协议", "跨域JSON封装", "搜索协议转换", "GSA封装", "协议解析", "字段映射", "格式转换"]
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# GSA 协议转换器（gsa-prototype）

## 一、能力边界速查卡

### 1.1 能做什么

| 能力项 | 说明 | 输入示例 | 输出示例 |
|--------|------|----------|----------|
| 文本转JSON | 将 `key=value` 格式的GSA协议文本解析为结构化JSON对象 | `operation=search\nq=hello` | `{"operation":"search","q":"hello"}` |
| 跨域字段映射 | 支持自定义映射表，将源字段名转换为目标系统字段名 | 映射表 `{"operation":"action"}` | `{"action":"search"}` |
| 数据校验 | 对必填字段、字段类型、取值范围进行校验 | 校验规则 `{"q":"required"}` | 缺失时输出 `[需核实:q]` |
| 增量处理 | 记录已处理文件指纹，跳过重复数据 | 文件哈希记录表 | 跳过已处理文件 |

### 1.2 不能做什么

| 限制项 | 说明 |
|--------|------|
| 不支持二进制协议 | 仅处理纯文本 `key=value` 格式 |
| 不执行网络请求 | 仅做本地文本解析与转换 |
| 不保证业务正确性 | 校验仅覆盖格式层面，业务语义需使用者自行确认 |
| 不提供图形界面 | 仅通过命令行接口交互 |

### 1.3 适用对象

- 需要将GSA协议文本批量转换为JSON的开发者
- 需要在不同系统间传递搜索协议数据的集成工程师
- 需要为协议字段建立统一映射规范的技术团队

---

## 二、触发方式与场景映射

| 触发词 | 典型场景 | 预期行为 |
|--------|----------|----------|
| `gsa prototype` | 用户输入完整命令 | 执行转换主流程 |
| `GSA搜索协议` | 用户提到协议名称 | 识别为转换请求 |
| `跨域JSON封装` | 用户需要跨系统字段映射 | 加载映射表并转换 |
| `搜索协议转换` | 用户需要格式转换 | 执行文本到JSON转换 |
| `GSA封装` | 用户需要协议封装 | 生成结构化JSON |
| `协议解析` | 用户需要解析协议文本 | 执行解析流程 |
| `字段映射` | 用户需要字段名映射 | 应用自定义映射表 |
| `格式转换` | 用户需要通用格式转换 | 执行转换主流程 |

---

## 三、标准执行流程

### 3.1 前置条件

| 条件 | 要求 | 检查方式 |
|------|------|----------|
| 输入文件 | 存在且可读 | `test -f input.txt` |
| 文件格式 | 每行一个 `key=value` | `head -5 input.txt` |
| 必填字段 | 包含 `operation` 和 `q` | `grep -E '^(operation|q)=' input.txt` |
| 运行环境 | Python 3.6+ | `python3 --version` |

### 3.2 执行步骤

1. **准备输入文件**：创建或获取GSA协议文本文件，确保每行格式为 `key=value`。

   ```bash
   # 示例输入文件 input.txt
   operation=search
   q=分布式系统
   num=10
   start=0
   ```

2. **运行转换命令**：

   ```bash
   gsa prototype --input input.txt --output result.json
   ```

3. **检查输出结果**：

   ```bash
   cat result.json
   # 期望输出：{"operation":"search","q":"分布式系统","num":"10","start":"0"}
   ```

4. **处理需核实字段**：若输出包含 `[需核实:xxx]`，补充对应字段后重试。

   ```bash
   # 若输出为 {"operation":"search","[需核实:q]":""}
   # 编辑 input.txt 添加 q=搜索内容
   echo "q=分布式系统" >> input.txt
   gsa prototype --input input.txt --output result.json
   ```

5. **应用自定义映射表**（可选）：

   ```bash
   gsa prototype --input input.txt --output result.json --mapping map.json
   ```

   映射表示例 `map.json`：

   ```json
   {
     "operation": "action",
     "q": "query",
     "num": "page_size"
   }
   ```

### 3.3 输出规范

| 输出类型 | 格式 | 说明 |
|----------|------|------|
| 成功 | JSON对象 | 键值对按输入顺序排列 |
| 字段缺失 | `[需核实:字段名]` | 占位符替代缺失值 |
| 解析错误 | 错误码+提示 | 见错误码体系章节 |
| 版本信息 | `gsa-prototype v1.0.0` | 使用 `--version` 参数 |

---

## 四、置信度门控机制

### 4.1 占位符规则

| 场景 | 输出 | 说明 |
|------|------|------|
| 必填字段缺失 | `[需核实:字段名]` | 不猜测、不编造 |
| 字段值格式异常 | `[需核实:字段名=原始值]` | 保留原始值供人工确认 |
| 映射表字段不存在 | `[需核实:映射字段]` | 提示映射配置问题 |

### 4.2 处理策略

1. 遇到缺失字段时，**立即停止**后续转换，输出占位符。
2. 占位符字段不参与后续映射和校验。
3. 用户补充字段后，重新执行转换。

---

## 五、错误码体系

| 错误码 | 错误描述 | 提示话术 | 修正步骤 |
|--------|----------|----------|----------|
| E001 | 输入文件不存在 | `错误: 文件 input.txt 不存在` | 检查文件路径，确认文件已创建 |
| E002 | 文件格式错误 | `错误: 第3行格式不正确，应为 key=value` | 编辑文件，修正格式 |
| E003 | 缺少必填字段 | `错误: 缺少 operation 或 q 字段` | 添加对应字段后重试 |
| E004 | 映射表格式错误 | `错误: 映射表 map.json 不是有效JSON` | 检查映射表语法 |
| E005 | 输出目录不可写 | `错误: 无法写入 result.json` | 检查目录权限 |
| E006 | 编码不支持 | `错误: 文件编码不是UTF-8` | 转换文件编码为UTF-8 |

---

## 六、FAQ 与反模式对照

| 常见坑 | 反模式示例 | 正确做法 |
|--------|------------|----------|
| 忽略必填字段 | 直接输出缺少 `q` 的JSON | 输出 `[需核实:q]` 占位符 |
| 猜测缺失值 | 自动填充 `q=default` | 保留占位符，等待用户确认 |
| 覆盖原始文件 | 转换后直接修改输入文件 | 输出到独立文件，保留原始数据 |
| 忽略映射错误 | 映射字段不存在时静默跳过 | 输出 `[需核实:映射字段]` 提示 |
| 批量处理无记录 | 重复处理相同文件 | 记录文件哈希，跳过已处理项 |

---

## 七、渐进式披露路径

### 7.1 新手速查卡

```text
1. 准备 input.txt（每行 key=value）
2. 运行：gsa prototype --input input.txt --output result.json
3. 查看 result.json
4. 有 [需核实:xxx] 就补字段重跑
```

### 7.2 进阶路径

1. **阅读源码**：查看 `convert_one.py` 理解核心转换逻辑。
2. **扩展格式**：添加XML、CSV输入支持。
3. **增量处理**：实现文件指纹记录，跳过重复数据。
4. **自定义插件**：开发转换插件机制，支持业务定制。

### 7.3 高级路径

1. **设计映射表**：为目标系统定制字段命名规范。
2. **编写校验规则**：增加业务级字段检查（如枚举值、正则匹配）。
3. **CI/CD集成**：将转换流程接入自动化流水线。
4. **批量并发**：开发多文件并发处理脚本。

---

## 八、参数参考表

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `--input` | string | 是 | 无 | 输入文件路径 |
| `--output` | string | 是 | 无 | 输出文件路径 |
| `--mapping` | string | 否 | 无 | 映射表JSON文件路径 |
| `--validate` | string | 否 | 无 | 校验规则JSON文件路径 |
| `--incremental` | boolean | 否 | false | 启用增量处理模式 |
| `--selftest` | boolean | 否 | false | 运行自检流程 |
| `--version` | boolean | 否 | false | 显示版本信息 |

---

## 九、用户协议

<!-- user-agreement-injected -->

**使用本 Skill 即表示您同意以下条款：**

1. **责任承担**：使用者自行承担因使用本 Skill 产生的全部责任。包括但不限于数据转换错误、数据丢失、业务中断等风险。
2. **禁止反向工程**：不得对本 Skill 的源代码进行反向工程、反编译、破解或试图提取底层算法。
3. **合规使用**：使用者应确保使用场景符合当地法律法规，不得用于任何非法用途。
4. **无担保声明**：本 Skill 按"现状"提供，不附带任何明示或暗示的担保。
5. **免责范围**：在任何情况下，Skill 作者均不对因使用本 Skill 而产生的任何直接、间接、偶然、特殊或后果性损害承担责任。

---

## 十、许可证（License）

<!-- professional-license-embedded -->

**MIT License**

Copyright (c) 2024 协议工坊

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
