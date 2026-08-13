---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: automatewithpython
name: automatewithpython
displayName: 办公表格 批处理 脚本生成
description: 将重复性文件与表格操作转化为可执行 Python 脚本，提升工作效率。
version: 1.0.5
rules_version: cpr-20260813-n401
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/automatewithpython
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: LingAutomation
agent_created: true
trigger_words: ["automatewithpython", "python自动化", "批量处理", "脚本生成", "办公自动化", "表格批处理", "文件批量操作"]

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

---

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->


# automatewithpython — 办公表格与文件批处理脚本生成器

## 一、能力边界速查卡

### 1.1 本 Skill 能做什么

| 能力项 | 说明 | 典型输入示例 |
|--------|------|--------------|
| 数据去重 | 基于指定列去除 CSV/Excel 中的重复行 | `deduplicate test.csv --key 用户ID` |
| 格式转换 | 在 CSV、Excel、JSON 之间互转 | `convert input.xlsx --to csv` |
| 字段清洗 | 去除空格、统一日期格式、填充空值 | `clean data.csv --fillna 0` |
| 批量重命名 | 按规则批量修改文件名 | `rename ./files --prefix 2026_` |
| 内容合并 | 合并多个表格或文本文件 | `merge *.csv --output all.csv` |
| 数据筛选 | 按条件过滤行或列 | `filter data.csv --where "age>18"` |

### 1.2 本 Skill 不能做什么

- **不能处理非结构化数据**：如从图片中提取文字、理解自然语言语义。
- **不能执行需要人工判断的操作**：如判断某条数据是否涉及商业机密。
- **不能保证脚本在任意环境运行**：依赖 Python 3.8+ 及 pandas/openpyxl 库。
- **不能处理超大文件**：超过 2GB 的表格文件可能内存溢出。
- **不能自动安装依赖**：需用户自行执行 `pip install`。

### 1.3 适用对象

- 日常需要处理 Excel/CSV 的运营、财务、人事人员。
- 需要批量整理文件的设计师、内容创作者。
- 希望减少重复劳动的初级开发者。

---

## 二、触发方式与场景映射

### 2.1 触发词

直接使用以下任一方式触发：

- `automatewithpython`
- `python自动化`
- `批量处理`
- `脚本生成`
- `办公自动化`
- `表格批处理`
- `文件批量操作`

### 2.2 大白话场景映射表

| 你说的话（口语化） | 实际触发动作 |
|-------------------|-------------|
| "帮我把这个 Excel 里重复的客户删掉" | 生成去重脚本 |
| "我有 500 个文件要改名字，太累了" | 生成批量重命名脚本 |
| "这个 CSV 转成 Excel 怎么弄" | 生成格式转换脚本 |
| "把三个月的报表合并成一张表" | 生成合并脚本 |
| "这列日期格式乱七八糟，帮我统一" | 生成字段清洗脚本 |

---

## 三、标准操作流程

### 3.1 前置条件

| 条件 | 要求 | 检查命令 |
|------|------|----------|
| Python 版本 | 3.8 及以上 | `python --version` |
| 依赖库 | pandas, openpyxl | `pip list \| grep pandas` |
| 输入文件 | 存在且格式正确 | `ls -la test.csv` |
| 输出目录 | 有写权限 | `touch ./test_output` |

### 3.2 执行步骤（以去重为例）

**Step 1：准备输入文件**

确保 CSV 文件存在且格式正确：

```bash
$ head -5 test.csv
用户ID,姓名,注册日期
1001,张三,2024-01-01
1002,李四,2024-01-02
1001,张三,2024-01-01
```

**Step 2：生成脚本**

```bash
$ automatewithpython deduplicate test.csv
已生成脚本: script.py
```

**Step 3：运行脚本**

```bash
$ python script.py --input test.csv --output result.csv
处理完成: 4行 → 3行（去重1行）
```

**Step 4：验证输出**

```bash
$ cat result.csv
用户ID,姓名,注册日期
1001,张三,2024-01-01
1002,李四,2024-01-02
```

### 3.3 输出规范

所有生成的脚本遵循以下规范：

- 文件名：`script.py`（可通过 `--name` 参数修改）
- 参数接口：`--input`（输入路径）、`--output`（输出路径）
- 日志输出：处理前后行数变化、耗时
- 错误处理：文件不存在时给出明确提示，退出码非 0

---

## 四、置信度门控

当遇到以下情况时，脚本会输出 `[需核实:字段]` 占位符，**不会**编造数据：

| 场景 | 输出示例 |
|------|----------|
| 输入文件缺少必要列 | `[需核实:缺少列 '用户ID']` |
| 日期格式无法识别 | `[需核实:日期格式 2024/13/45 无法解析]` |
| 编码无法自动检测 | `[需核实:文件编码非UTF-8，请指定--encoding]` |
| 数值列包含非数字 | `[需核实:第3行 '年龄' 列包含 '未知']` |

**原则**：宁可输出占位符，不猜测、不伪造、不静默跳过。

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| E001 | 输入文件不存在 | `错误: 文件 xxx.csv 不存在` | 检查路径；使用绝对路径 |
| E002 | 缺少必要参数 | `错误: 缺少 --input 参数` | 运行 `python script.py --help` 查看帮助 |
| E003 | 依赖库未安装 | `错误: pandas 未安装，请执行 pip install pandas` | 安装依赖后重试 |
| E004 | 文件编码错误 | `错误: 无法解码文件，请指定 --encoding utf-8` | 添加编码参数 |
| E005 | 内存不足 | `错误: 文件过大，内存不足` | 使用 `--chunksize 10000` 分块处理 |
| E006 | 输出目录无权限 | `错误: 无法写入输出目录` | 检查目录权限或更换路径 |

---

## 六、FAQ 与反模式

### 6.1 常见坑

| 坑 | 反模式（错误做法） | 正确做法 |
|----|-------------------|----------|
| 忽略编码 | 直接读取 GBK 编码文件不指定编码 | 使用 `--encoding gbk` 或先检测编码 |
| 覆盖原文件 | 输出路径设为输入路径 | 使用独立输出文件，确认无误后再覆盖 |
| 忽略空值 | 去重时未处理 NaN 导致误删 | 先执行 `clean --fillna` 再去重 |
| 盲目信任默认参数 | 不指定 `--key` 导致全列去重 | 明确指定去重键列 |
| 忽略数据类型 | 日期列被当作字符串处理 | 使用 `--parse-dates` 参数 |

### 6.2 反模式对照表

| 反模式 | 问题 | 替代方案 |
|--------|------|----------|
| 手动修改生成脚本 | 升级后无法同步 | 重新生成脚本，保留参数配置 |
| 在脚本中硬编码路径 | 换环境即失效 | 使用 `--input`/`--output` 参数 |
| 一次处理所有数据 | 内存溢出 | 分块处理或先筛选 |
| 不验证输出 | 错误数据流入下游 | 运行后检查行数、抽样验证 |

---

## 七、渐进式学习路径

### 7.1 速查卡（新手必读）

```
1. 准备 CSV 文件
2. 运行: automatewithpython deduplicate test.csv
3. 执行: python script.py --input test.csv --output result.csv
4. 查看: result.csv
```

### 7.2 进阶路径（有经验用户）

**Level 1：理解脚本**

阅读生成的 `script.py`，理解 pandas 的 `drop_duplicates()`、`to_csv()` 等核心调用。

**Level 2：参数定制**

```bash
# 指定去重列
python script.py --input test.csv --output result.csv --key 用户ID

# 保留最后出现的重复项
python script.py --input test.csv --output result.csv --keep last
```

**Level 3：组合操作**

```bash
# 先清洗再转换
automatewithpython clean test.csv --fillna 0 --output cleaned.csv
automatewithpython convert cleaned.csv --to xlsx --output final.xlsx
```

**Level 4：流水线集成**

```bash
# 定时任务（每天凌晨2点执行）
0 2 * * * cd /path/to/project && python script.py --input data.csv --output result.csv
```

**Level 5：函数库封装**

将生成的脚本重构为可导入的函数：

```python
# mylib.py
import pandas as pd

def deduplicate(input_path, output_path, key=None):
    df = pd.read_csv(input_path)
    df = df.drop_duplicates(subset=key)
    df.to_csv(output_path, index=False)
    return len(df)
```

---

## 八、参数速查表

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `--input` | 字符串 | 必填 | 输入文件路径 |
| `--output` | 字符串 | `result.csv` | 输出文件路径 |
| `--key` | 字符串 | 无 | 去重/筛选的列名 |
| `--encoding` | 字符串 | `utf-8` | 文件编码 |
| `--chunksize` | 整数 | 无 | 分块处理的行数 |
| `--keep` | 字符串 | `first` | 保留重复项中的哪一条（first/last/false） |
| `--fillna` | 任意 | 无 | 空值填充值 |
| `--parse-dates` | 布尔 | `False` | 是否解析日期列 |
| `--prefix` | 字符串 | 无 | 重命名前缀 |
| `--to` | 字符串 | 无 | 转换目标格式（csv/xlsx/json） |

---

## 九、用户协议

<!-- user-agreement-injected -->

**使用本 Skill 即表示您同意以下条款：**

1. **责任承担**：使用者应自行承担因使用本 Skill 产生的全部责任。包括但不限于因脚本运行导致的数据丢失、系统故障、业务中断等后果。

2. **数据安全**：使用者应确保输入数据的合法性和安全性。本 Skill 不存储用户数据，所有处理均在本地完成。请勿输入包含敏感个人信息或商业机密的数据。

3. **禁止反向工程**：使用者不得对本 Skill 生成的脚本进行反向工程、反编译或试图提取源代码（除明确授权的修改外）。

4. **合规使用**：使用者应遵守所在国家/地区的法律法规，不得使用本 Skill 从事任何违法活动，包括但不限于数据窃取、侵犯他人隐私、制作恶意软件等。

5. **修改与分发**：允许使用者基于本 Skill 进行修改和再分发，但需保留原始版权声明和本协议。

---

## 十、许可证（License）

<!-- professional-license-embedded -->

**MIT License**

Copyright (c) 2026 LingAutomation

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

## 附：版本信息

- 当前版本：1.0.0
- 更新日期：2026-08-13
- 兼容性：Python 3.8+，pandas ≥ 1.3，openpyxl ≥ 3.0
- 反馈渠道：通过 GitHub Issues 提交问题或建议

---

*本 Skill 由 AI 辅助生成，仅供参考。使用前请阅读相关文档。*
