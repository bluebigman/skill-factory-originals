---
slug: uploadcolumn
name: uploadcolumn
displayName: 字段解析 批量转换 结构化输出
description: 将文件或链接解析为结构化字段，支持批量处理与置信度标注。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 数据工坊
agent_created: true
trigger_words: ["uploadcolumn", "上载列", "字段解析", "数据转换", "结构化输出", "列映射", "批量解析"]
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# uploadcolumn — 字段解析与结构化输出 Skill

## 一、能力边界（一页纸速查卡）

### 能做什么

| 能力项 | 说明 | 示例 |
|--------|------|------|
| 文件解析 | 将 CSV、TXT、JSON 等文本类文件解析为结构化字段 | `sales_001.csv` → `{"region": "华东", "amount": 1234.56}` |
| 链接解析 | 将公开 HTTP/HTTPS 链接指向的内容解析为结构化字段 | `https://example.com/data.csv` → 同上 |
| 批量处理 | 同一目录下多个文件按命名规范批量解析 | `./input/` 下 50 个文件一次跑完 |
| 字段映射 | 通过 `--mapping` 参数自定义源字段到目标字段的映射关系 | 将 `cust_id` 映射为 `customerId` |
| 置信度标注 | 对无法确定的内容输出 `[需核实:字段]` 占位符，不编造数据 | 金额格式异常时标注 `[需核实:amount]` |
| 试运行模式 | 先跑 1 个文件验证效果，再全量执行 | `--dry-run` 参数 |

### 不能做什么

| 限制项 | 说明 |
|--------|------|
| 非文本文件 | 不支持图片、PDF 扫描件、音频、视频等非文本格式 |
| 私有链接 | 需要登录或鉴权的链接无法访问 |
| 复杂嵌套结构 | 超过 3 层嵌套的 JSON 结构需预先扁平化处理 |
| 语义理解 | 不识别字段的业务含义，仅做格式解析与映射 |
| 数据修复 | 不自动修正源数据错误，仅标注置信度 |

### 适用对象

- 需要将散乱数据文件转为统一 JSON 格式的数据工程师
- 需要批量处理导入文件的数据运营人员
- 需要将外部数据接入内部系统的开发人员

---

## 二、触发方式

### 触发词

- 主触发词：`uploadcolumn`、`上载列`、`字段解析`
- 同义场景词：`列映射`、`批量解析`、`结构化输出`

### 场景映射表

| 你说的话 | Skill 执行的动作 |
|----------|-----------------|
| "把这批 CSV 转成 JSON" | 解析 `./input/` 下所有 `.csv` 文件，输出结构化 JSON |
| "这个链接里的表格帮我提取一下" | 访问链接，提取表格内容并结构化 |
| "字段名对不上，帮我映射一下" | 使用 `--mapping` 参数自定义字段映射 |
| "先跑一个试试" | 执行 `--dry-run` 试运行模式 |
| "这些数据有些不确定，帮我标出来" | 对低置信度字段输出 `[需核实:字段]` 占位符 |

---

## 三、标准流程

### 前置条件

| 条件 | 要求 | 检查方式 |
|------|------|----------|
| 文件目录 | 待处理文件放入同一目录，如 `./input/` | `ls ./input/` |
| 文件命名 | 格式：`前缀_序号.扩展名`（如 `sales_001.csv`） | 正则：`^[a-zA-Z]+_\d+\.[a-z]+$` |
| 链接访问 | 公开可访问的 HTTP/HTTPS 地址 | `curl -I <url>` 返回 200 |
| 环境依赖 | Python 3.8+，已安装 `pandas`、`requests` | `python --version` |

### 执行步骤

1. **放置文件**：将待处理文件放入 `./input/` 目录，确认命名规范。

2. **试运行**：执行单文件解析验证效果。
   ```bash
   uploadcolumn --file ./input/sales_001.csv --dry-run
   ```
   查看输出 JSON 结构，确认字段解析正确。

3. **配置映射**（可选）：如需自定义字段映射，创建映射文件。
   ```json
   {
     "cust_id": "customerId",
     "amt": "amount",
     "dt": "date"
   }
   ```
   执行时指定：`--mapping ./mapping.json`

4. **批量执行**：确认无误后全量处理。
   ```bash
   uploadcolumn --dir ./input/ --output ./output/
   ```

5. **结果校验**：
   - 随机抽取 3-5 个输出文件，与源文件对照
   - 核对关键字段（金额、日期、ID）是否一致
   - 统计 `[需核实]` 占位符数量，若超过总量的 10%，检查源数据质量

### 输出规范

- 输出目录：`./output/`
- 文件命名：`<前缀>_<序号>_parsed.json`
- 输出结构：
  ```json
  {
    "source": "sales_001.csv",
    "parsed_at": "2025-01-15T10:30:00Z",
    "fields": {
      "region": {"value": "华东", "confidence": 0.98},
      "amount": {"value": 1234.56, "confidence": 0.95},
      "date": {"value": "[需核实:date]", "confidence": 0.0}
    }
  }
  ```

---

## 四、置信度门控

### 原则

**信息不足时输出 `[需核实:字段]` 占位符，绝不编造数据。**

### 置信度等级

| 等级 | 范围 | 含义 | 处理方式 |
|------|------|------|----------|
| 高 | 0.90-1.00 | 字段值确定，格式正确 | 直接输出 |
| 中 | 0.70-0.89 | 字段值存在但格式可疑 | 输出值 + 置信度标注 |
| 低 | 0.40-0.69 | 字段值缺失或格式异常 | 输出 `[需核实:字段]` + 原始值 |
| 无 | 0.00-0.39 | 无法解析 | 仅输出 `[需核实:字段]` |

### 触发场景

| 场景 | 处理 |
|------|------|
| 日期格式不统一（`2024/1/5` vs `2024-01-05`） | 输出 `[需核实:date]` |
| 金额含货币符号（`$1,234.56` vs `1234.56`） | 输出 `[需核实:amount]` |
| ID 字段为空或超长 | 输出 `[需核实:id]` |
| 字段值包含不可见字符 | 输出 `[需核实:field]` |

### 门控阈值调整

通过参数 `--confidence-threshold` 调整门控阈值，默认 0.7。低于阈值的字段自动转为 `[需核实]` 占位符。

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| `E001` | 文件不存在 | "未找到指定文件，请检查路径" | 确认文件路径，使用绝对路径 |
| `E002` | 文件命名不规范 | "文件名不符合 `前缀_序号.扩展名` 规范" | 重命名文件，如 `sales_001.csv` |
| `E003` | 链接无法访问 | "链接返回非 200 状态码，请确认链接公开可访问" | 检查链接有效性，或下载后本地处理 |
| `E004` | 字段映射冲突 | "映射文件中存在重复目标字段" | 检查 mapping 文件，确保目标字段唯一 |
| `E005` | 输出目录不可写 | "无法写入输出目录，请检查权限" | 修改目录权限或更换输出路径 |
| `E006` | 文件格式不支持 | "仅支持 CSV、TXT、JSON 格式" | 转换文件格式后重试 |
| `E007` | 批量处理中断 | "第 N 个文件解析失败，已跳过" | 查看错误日志，修复后重新执行 |
| `E008` | 置信度超限 | "低置信度字段超过总量 10%，建议检查源数据" | 检查源数据质量，或调整阈值 |

---

## 六、FAQ 反模式

### 常见坑与反模式对照

| 反模式 | 问题 | 正确做法 |
|--------|------|----------|
| 直接全量跑，不试运行 | 字段映射错误导致全部输出无效 | 先 `--dry-run` 跑 1 个文件验证 |
| 忽略 `[需核实]` 占位符 | 下游系统收到脏数据 | 统计占位符比例，超过 10% 先修源数据 |
| 文件名随意命名 | 批量处理时无法识别文件顺序 | 严格遵循 `前缀_序号.扩展名` 规范 |
| 映射文件字段名写错 | 映射无效，输出原字段名 | 核对 mapping 文件字段名与源文件完全一致 |
| 链接未验证直接使用 | 链接失效导致任务失败 | 先用 `curl -I` 验证链接可访问 |
| 忽略置信度阈值调整 | 业务场景对精度要求高但用默认阈值 | 根据业务需求调整 `--confidence-threshold` |

---

## 七、渐进式披露

### 速查卡（30 秒上手）

```
1. 放文件到 ./input/（命名：前缀_序号.csv）
2. 试运行：uploadcolumn --file ./input/sales_001.csv --dry-run
3. 批量：uploadcolumn --dir ./input/ --output ./output/
4. 校验：抽 3-5 个输出文件对照源文件
```

### 分层次阅读路径

**新手路径**（首次使用）：
1. 阅读「能力边界」了解适用范围
2. 按「标准流程」执行一次单文件解析
3. 查看输出 JSON 结构，理解字段与置信度

**进阶路径**（熟练使用）：
1. 熟悉「错误码体系」，遇到问题快速定位
2. 阅读「FAQ 反模式」，避免常见错误
3. 使用 `--mapping` 参数自定义字段映射
4. 结合置信度门控，建立数据质量检查流程

**专家路径**（深度定制）：
1. 修改解析规则（如自定义分隔符、日期格式）
2. 编写后处理脚本，对接内部系统
3. 将置信度阈值调整为业务需求匹配的值

---

## 八、参数速查表

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `--file` | string | 无 | 指定单个文件解析 |
| `--dir` | string | `./input/` | 指定批量处理目录 |
| `--output` | string | `./output/` | 输出目录 |
| `--mapping` | string | 无 | 字段映射 JSON 文件路径 |
| `--dry-run` | flag | false | 试运行模式，仅处理第一个文件 |
| `--confidence-threshold` | float | 0.7 | 置信度门控阈值 |
| `--delimiter` | string | `,` | 自定义分隔符 |
| `--date-format` | string | 自动检测 | 自定义日期格式 |
| `--selftest` | flag | false | 运行自检 |
| `--version` | flag | false | 显示版本号 |

---

## 九、用户协议

<!-- user-agreement-injected -->

**使用本 Skill 即表示您同意以下条款：**

1. **责任承担**：使用者应自行承担使用本 Skill 产生的全部责任。因使用本 Skill 导致的任何直接或间接损失，Skill 作者不承担任何责任。

2. **数据安全**：使用者应确保处理的数据不违反法律法规，不侵犯第三方权益。涉及个人隐私或商业机密的数据，使用者应自行做好脱敏处理。

3. **禁止反向工程**：使用者不得对本 Skill 进行反向工程、反编译、破解或试图提取源代码逻辑。

4. **合规使用**：使用者应遵守所在国家/地区的法律法规，不得将本 Skill 用于任何非法用途。

5. **免责声明**：本 Skill 由 AI 辅助生成，仅供学习参考。技能输出结果可能存在误差，使用者应结合实际情况进行判断。

---

## 十、许可证（License）

<!-- professional-license-embedded -->

### MIT License

Copyright (c) 2025 数据工坊

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

*本 Skill 由 AI 辅助生成，仅供学习参考。使用前请阅读相关文档。*
