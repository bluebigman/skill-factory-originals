---
slug: ebay4r
name: ebay4r
displayName: eBay接口 数据转换 批量处理
description: 封装eBay SOAP API的Ruby工具，简化数据转换与调用流程。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 独立开发者·林默
agent_created: true
trigger_words: ["ebay4r", "eBay接口", "SOAP API", "Ruby封装", "eBay数据转换", "eBay批量处理", "eBay字段提取"]
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# ebay4r — eBay SOAP API 的 Ruby 封装工具使用指南

## 一、能力边界（一页纸速查卡）

### 1.1 能做与不能做

| 维度 | 能做 ✅ | 不能做 ❌ |
|------|---------|-----------|
| **数据格式** | 标准 CSV/JSON 输入，字段名与 eBay API 参数一致 | 非结构化文本（如 PDF 扫描件、手写笔记）直接解析 |
| **调用范围** | 单接口批量请求、字段提取、结构化输出、失败明细追踪 | 多接口串联编排、事务性原子操作 |
| **错误处理** | 记录失败条目及原因，生成错误报告文件 | 自动重试、自动修复数据错误 |
| **数据安全** | 保留原始文件备份，输出文件与源文件分离 | 加密存储、密钥管理（需自行处理） |
| **运行环境** | Ruby 2.7+，需安装 soap4r 或相关 gem | 无 Ruby 环境的服务器直接运行 |

### 1.2 适用对象

- **适合**：需要批量调用 eBay SOAP API 的 Ruby 开发者；已有标准化数据文件（CSV/JSON）需要转换格式的运维人员。
- **不适合**：零编程基础的业务人员；需要实时交互式调用的场景；数据源格式混乱且无规律的项目。

---

## 二、触发方式与场景映射

### 2.1 触发词

- 主触发词：`ebay4r`、`eBay接口`、`SOAP API`、`Ruby封装`、`eBay数据转换`
- 补充场景词：`eBay批量处理`、`eBay字段提取`、`eBay结构化输出`

### 2.2 大白话场景映射表

| 你说的话（意图） | 工具行为 |
|------------------|----------|
| "帮我把这批商品数据转成 eBay 能用的格式" | 读取输入文件，按 eBay API 字段映射规则转换，输出标准请求文件 |
| "我有一堆订单要查状态，怎么批量调？" | 遍历订单 ID 列表，逐个构造 SOAP 请求，汇总响应结果 |
| "上次跑批有 3 条失败了，能告诉我为什么吗？" | 生成错误报告，列出失败条目、错误码和原因描述 |
| "这个字段在源数据里叫 'price'，eBay 要 'StartPrice'，怎么处理？" | 通过配置文件指定字段映射关系，自动完成重命名与类型转换 |

---

## 三、标准操作流程

### 3.1 前置条件

| 条件项 | 要求 |
|--------|------|
| 运行环境 | Ruby 2.7+，已安装 `soap4r` gem（或 `savon`，视版本而定） |
| 输入文件 | 与脚本同目录，命名含批次标识（如 `input_20250101.csv`） |
| 字段规范 | 输入文件表头需与映射配置中的源字段名完全一致 |
| 凭证配置 | 在 `config.yml` 中提供 eBay API 的 `auth_token` 和 `app_id` |
| 备份要求 | 执行前将原始文件复制到 `backup/` 目录 |

### 3.2 执行步骤（分步编号）

1. **准备输入**  
   将待处理文件放入脚本所在目录，确认命名规范为 `input_YYYYMMDD.csv` 或 `input_YYYYMMDD.json`。检查表头字段是否与 `field_mapping.yml` 中的源字段名匹配。

2. **配置检查**  
   运行 `ruby ebay4r.rb --check-config`，验证 `config.yml` 中的凭证、接口地址、超时时间等参数是否完整。输出 `CONFIG OK` 表示通过。

3. **单样本试运行**  
   执行 `ruby ebay4r.rb --sample input_20250101.csv --line 1`，仅处理第一行数据。核对输出文件中的字段名、类型、格式是否符合预期。

   ```bash
   # 示例：试运行输出
   $ ruby ebay4r.rb --sample input_20250101.csv --line 1
   [INFO] 处理第 1 行...
   [SUCCESS] 输出: output_20250101_sample.json
   [字段映射] StartPrice ← price (Float)
   [字段映射] Quantity ← stock (Integer)
   ```

4. **全量执行**  
   确认试运行无误后，执行 `ruby ebay4r.rb --batch input_20250101.csv`。脚本自动完成以下操作：
   - 将原始文件复制到 `backup/` 目录（带时间戳）
   - 逐行读取数据，构造 SOAP 请求
   - 调用 eBay API，接收响应
   - 将成功结果写入 `output_YYYYMMDD.json`
   - 将失败条目写入 `error_YYYYMMDD.log`

5. **校验结果**  
   抽查输出文件中的 5-10 条记录，与源数据比对关键字段（如 `ItemID`、`StartPrice`、`Quantity`）。确认无遗漏、无错位。

### 3.3 输出规范

| 输出文件 | 格式 | 内容说明 |
|----------|------|----------|
| `output_YYYYMMDD.json` | JSON 数组 | 每条记录含 `request_id`、`ebay_response`、`status`（success/failed） |
| `error_YYYYMMDD.log` | 纯文本 | 每行一条错误：`[行号] [错误码] [错误描述]` |
| `backup/` 目录 | 原始文件副本 | 文件名追加时间戳，如 `input_20250101_143022.csv` |

---

## 四、置信度门控

当输入数据缺失关键字段、或 API 响应异常时，**禁止编造或猜测**。按以下规则处理：

| 场景 | 处理方式 |
|------|----------|
| 源数据缺少必填字段（如 `ItemID`） | 输出 `[需核实:ItemID]` 占位符，并将该条标记为 `failed`，错误码 `E1001` |
| API 返回超时或网络错误 | 输出 `[需核实:网络状态]`，记录错误码 `E2001`，不重试 |
| 字段类型不匹配（如字符串传入数值字段） | 输出 `[需核实:字段类型]`，错误码 `E3001`，提示检查源数据 |
| 映射配置中找不到对应字段 | 输出 `[需核实:映射规则]`，错误码 `E4001`，停止处理并提示检查 `field_mapping.yml` |

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| `E1001` | 缺少必填字段 | "第 N 行缺少 ItemID，已跳过" | 检查源数据，补齐字段后重新执行 |
| `E1002` | 字段值为空 | "第 N 行 StartPrice 为空，已跳过" | 确认源数据是否允许空值，或补充默认值 |
| `E2001` | 网络超时 | "第 N 行请求超时（30s），已记录" | 检查网络连接，或调整 `config.yml` 中的 `timeout` 参数 |
| `E2002` | API 认证失败 | "认证失败，请检查 auth_token" | 核对 `config.yml` 中的凭证是否过期 |
| `E3001` | 类型转换错误 | "第 N 行 price 无法转为 Float" | 检查源数据格式，清理异常字符 |
| `E4001` | 映射规则缺失 | "字段 'stock' 未在映射表中定义" | 编辑 `field_mapping.yml`，添加对应映射 |
| `E5001` | 文件格式错误 | "输入文件不是合法的 CSV/JSON" | 检查文件编码和分隔符，确保 UTF-8 编码 |

---

## 六、FAQ 反模式对照

| 常见坑（反模式） | 正确做法 |
|------------------|----------|
| **直接全量跑批，不试运行** → 结果大量失败，浪费时间和 API 配额 | 先 `--sample` 单条验证，再全量执行 |
| **修改源文件后不备份** → 数据丢失无法恢复 | 脚本自动备份，但手动修改前也应自行复制一份 |
| **忽略错误日志** → 失败条目静默丢失 | 每次执行后检查 `error_YYYYMMDD.log`，确认无 `E1001` 类错误 |
| **在映射表中使用中文键名** → 解析失败 | 映射表键名必须与源文件表头完全一致（英文） |
| **凭证硬编码在脚本中** → 泄露风险 | 统一放在 `config.yml`，并设置文件权限为 600 |

---

## 七、渐进式披露

### 7.1 速查卡（30 秒上手）

```bash
# 三步走
ruby ebay4r.rb --check-config          # 1. 检查配置
ruby ebay4r.rb --sample input.csv --line 1   # 2. 试运行
ruby ebay4r.rb --batch input.csv       # 3. 全量执行
```

### 7.2 分层次阅读路径

- **新手路径**：先读「一、能力边界」和「三、标准操作流程」的 3.2 节，按步骤操作即可。遇到错误查「五、错误码体系」。
- **进阶路径**：重点研究 `field_mapping.yml` 的配置语法（支持嵌套字段、类型转换函数），以及如何扩展自定义错误处理回调。可参考 `examples/` 目录下的高级用法示例。

---

## 八、用户协议

**使用本 Skill 即表示您同意以下条款：**

1. 使用者自行承担全部责任。因使用本 Skill 导致的任何数据丢失、API 调用失败、业务损失，作者不承担任何责任。
2. 禁止反向工程。不得对本 Skill 的代码、文档进行反编译、反汇编或试图推导其底层实现（除非适用法律允许）。
3. 本 Skill 仅供学习参考，不构成任何形式的担保或承诺。

<!-- user-agreement-injected -->

---

## 九、许可证（License）

**MIT License**

```
MIT License

Copyright (c) 2025 独立开发者·林默

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
