---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: gsa-prototype
name: gsa-prototype
displayName: 跨域搜索协议转换器
description: 将GSA协议文本转换为结构化JSON，支持跨域数据映射与校验。
version: 1.0.5
rules_version: cpr-20260814-n426
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/gsa-prototype
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 协议工坊
agent_created: true
trigger_words: ["gsa prototype", "GSA搜索协议", "跨域JSON封装", "搜索协议转换", "GSA封装", "协议解析", "数据映射"]
---

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->


> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# GSA 协议转换 Skill 文档

## 一、能力边界速查卡

本 Skill 专注于将 GSA（Generic Search Agreement）协议格式的文本文件转换为结构化的 JSON 数据，并支持跨域字段映射。以下通过清单形式明确其能力范围。

### 1.1 能做什么

| 能力项 | 说明 | 示例 |
|--------|------|------|
| 协议解析 | 读取 GSA 协议格式的纯文本文件 | `gsa://query?term=hello&domain=example.com` |
| 字段提取 | 自动识别协议中的键值对、嵌套结构 | 提取 `term`、`domain`、`page` 等字段 |
| 跨域映射 | 将源字段映射到目标 JSON 结构 | `term` → `search.query` |
| 结构化输出 | 生成符合规范的 JSON 文件 | `{"search": {"query": "hello"}}` |
| 格式校验 | 检查输入文件是否符合 GSA 协议基本语法 | 检测缺失的协议头或非法字符 |

### 1.2 不能做什么

| 限制项 | 说明 |
|--------|------|
| 不支持二进制输入 | 仅处理 UTF-8 编码的纯文本文件 |
| 不执行网络请求 | 仅做本地文件转换，不发起实际搜索 |
| 不处理加密内容 | 加密或混淆的协议内容无法解析 |
| 不保证业务正确性 | 转换结果需人工复核，特别是涉及业务逻辑时 |

### 1.3 适用对象

- 需要将 GSA 协议数据接入 JSON 管道的开发者
- 维护跨域搜索协议兼容层的运维人员
- 数据迁移项目中负责格式转换的工程师

---

## 二、触发方式与场景映射

### 2.1 触发词

当用户输入以下关键词时，本 Skill 自动激活：

- `gsa prototype`
- `GSA搜索协议`
- `跨域JSON封装`
- `搜索协议转换`
- `GSA封装`
- `协议解析`
- `数据映射`

### 2.2 场景映射表

| 用户说（大白话） | 实际需求 | 本 Skill 动作 |
|------------------|----------|---------------|
| "帮我把这个 GSA 文件转成 JSON" | 协议格式转换 | 执行标准转换流程 |
| "这个搜索协议怎么解析？" | 理解协议结构 | 输出解析说明和示例 |
| "字段名对不上，能映射吗？" | 字段映射 | 提供映射配置方法 |
| "转换结果不对" | 调试转换逻辑 | 检查错误码并修正 |

---

## 三、标准执行流程

### 3.1 前置条件

| 条件 | 要求 | 检查方式 |
|------|------|----------|
| 输入文件 | 存在且可读 | `ls -l input.gsa` |
| 文件编码 | UTF-8 无 BOM | `file -i input.gsa` |
| 文件大小 | ≤ 10MB | `du -h input.gsa` |
| 协议头 | 以 `gsa://` 开头 | `head -c 6 input.gsa` |

### 3.2 执行步骤

**步骤 1：读取输入文件**

```bash
cat input.gsa
```

预期输出示例：
```
gsa://query?term=artificial+intelligence&domain=arxiv.org&page=2&size=20
```

**步骤 2：解析协议结构**

协议结构分解规则：

| 组成部分 | 分隔符 | 说明 |
|----------|--------|------|
| 协议头 | `gsa://` | 固定前缀，标识协议类型 |
| 操作名 | `/query` | 操作类型，如 `query`、`fetch`、`update` |
| 参数起始 | `?` | 参数列表开始 |
| 参数分隔 | `&` | 多个参数之间的分隔 |
| 键值分隔 | `=` | 参数名与值的分隔 |
| 值编码 | `+` 或 `%20` | 空格编码方式 |

**步骤 3：执行转换**

转换规则表：

| 源字段 | 目标字段 | 转换逻辑 |
|--------|----------|----------|
| `term` | `search.query` | 直接映射，解码 URL 编码 |
| `domain` | `search.scope` | 直接映射 |
| `page` | `pagination.page` | 字符串转整数 |
| `size` | `pagination.size` | 字符串转整数，限制 1-100 |
| 未识别字段 | `metadata.raw` | 原样保留 |

转换命令：

```bash
gsa-prototype convert input.gsa -o output.json
```

### 3.3 输出规范

转换后的 JSON 必须遵循以下结构：

```json
{
  "protocol": "gsa",
  "operation": "query",
  "search": {
    "query": "artificial intelligence",
    "scope": "arxiv.org"
  },
  "pagination": {
    "page": 2,
    "size": 20
  },
  "metadata": {
    "raw": {},
    "converted_at": "2026-08-14T10:30:00Z",
    "source_file": "input.gsa"
  }
}
```

**输出校验规则：**

| 检查项 | 规则 | 失败处理 |
|--------|------|----------|
| 必填字段 | `protocol`、`operation` 必须存在 | 返回错误码 `E1001` |
| 类型正确 | `page`、`size` 必须是整数 | 返回错误码 `E1002` |
| 值域范围 | `size` 必须在 1-100 之间 | 返回错误码 `E1003` |
| 编码合法 | 所有字符串必须是合法 UTF-8 | 返回错误码 `E1004` |

---

## 四、置信度门控

当输入信息不足以确定转换结果时，本 Skill 遵循以下原则：

1. **不编造数据**：缺失的必填字段输出 `[需核实:字段名]` 占位符
2. **不猜测意图**：操作名不明确时，输出 `[需核实:operation]` 并停止转换
3. **不假设默认值**：`page` 缺失时不默认填 1，而是输出 `[需核实:page]`

**示例：**

输入：
```
gsa://query?term=hello
```

输出：
```json
{
  "protocol": "gsa",
  "operation": "query",
  "search": {
    "query": "hello",
    "scope": "[需核实:domain]"
  },
  "pagination": {
    "page": "[需核实:page]",
    "size": "[需核实:size]"
  },
  "metadata": {
    "raw": {},
    "converted_at": "2026-08-14T10:30:00Z",
    "source_file": "input.gsa"
  }
}
```

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| `E1001` | 缺少协议头 | "输入文件不是有效的 GSA 协议格式" | 检查文件首行是否以 `gsa://` 开头 |
| `E1002` | 缺少操作名 | "无法识别操作类型" | 确认协议中包含 `/query`、`/fetch` 等操作名 |
| `E1003` | 参数格式错误 | "参数解析失败，请检查键值对格式" | 确认参数使用 `&` 分隔，`=` 连接 |
| `E1004` | 值类型错误 | "字段类型不符合预期" | 检查 `page`、`size` 是否为数字 |
| `E1005` | 值域越界 | "参数值超出允许范围" | 调整 `size` 至 1-100 之间 |
| `E1006` | 编码错误 | "文件包含非法 UTF-8 字符" | 重新保存文件为 UTF-8 编码 |
| `E1007` | 文件过大 | "文件大小超过 10MB 限制" | 分割文件或增加限制配置 |

---

## 六、FAQ 与反模式

### 6.1 常见问题

**Q1：转换后中文乱码怎么办？**

检查输入文件编码是否为 UTF-8。使用 `iconv -f GBK -t UTF-8 input.gsa > output.gsa` 转换编码。

**Q2：如何自定义字段映射？**

创建映射配置文件 `mapping.json`：

```json
{
  "term": "search.keyword",
  "domain": "search.site"
}
```

然后执行：
```bash
gsa-prototype convert input.gsa -m mapping.json -o output.json
```

**Q3：批量处理多个文件？**

```bash
for f in *.gsa; do
  gsa-prototype convert "$f" -o "${f%.gsa}.json"
done
```

### 6.2 反模式对照

| 反模式 | 问题 | 正确做法 |
|--------|------|----------|
| 忽略错误码 | 转换失败后继续处理 | 先解决错误码对应问题 |
| 硬编码字段名 | 修改协议后代码失效 | 使用映射配置文件 |
| 跳过校验 | 输出不符合规范 | 执行 `gsa-prototype validate output.json` |
| 手动修改输出 | 破坏结构一致性 | 修改输入文件后重新转换 |

---

## 七、渐进式披露

### 7.1 新手路径

1. 阅读「一、能力边界速查卡」了解工具定位
2. 准备一个 GSA 协议格式的文本文件
3. 按「三、标准执行流程」步骤 1-3 完成一次单文件转换
4. 查看输出结果，对照「3.3 输出规范」确认格式

### 7.2 进阶路径

1. 阅读「五、错误码体系」了解异常处理
2. 按「六、FAQ 与反模式」规避常见问题
3. 参考扩展指南，自定义字段映射和转换逻辑
4. 集成到 CI/CD 流程，实现自动化

### 7.3 专家路径

1. 阅读 `convert_one.py` 源码，理解转换核心逻辑
2. 扩展支持更多输入格式（XML、CSV）
3. 实现增量处理（记录已处理文件，跳过重复数据）
4. 添加自定义转换插件机制

---

## 八、扩展指南

### 8.1 添加新操作类型

在 `operations.json` 中注册：

```json
{
  "delete": {
    "required_fields": ["id"],
    "output_template": "delete_confirmation"
  }
}
```

### 8.2 自定义校验规则

创建 `validators.py`：

```python
def validate_size(value):
    if not 1 <= value <= 100:
        raise ValueError("size must be between 1 and 100")
```

---

## 用户协议

<!-- user-agreement-injected -->

**使用本 Skill 即表示您同意以下条款：**

1. **责任承担**：使用者自行承担因使用本 Skill 产生的全部责任。包括但不限于数据转换错误、数据丢失、业务中断等风险。
2. **禁止反向工程**：不得对本 Skill 的源代码进行反向工程、反编译、破解或试图提取底层算法。
3. **合规使用**：使用者应确保使用场景符合当地法律法规，不得用于任何非法用途。
4. **无担保声明**：本 Skill 按"现状"提供，不附带任何明示或暗示的担保。
5. **免责范围**：在任何情况下，Skill 作者均不对因使用本 Skill 而产生的任何直接、间接、偶然、特殊或后果性损害承担责任。

---

## 许可证（License）

<!-- professional-license-embedded -->

MIT License

Copyright (c) 2026 原创作者（自持版权）

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
