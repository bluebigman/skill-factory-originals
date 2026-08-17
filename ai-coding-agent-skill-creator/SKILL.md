---
slug: ai-coding-agent-skill-creator
name: ai-coding-agent-skill-creator
displayName: 技能封装 数据转技能包 参数校验
description: 将数据文件转化为结构化技能包，支持参数定义与输出验证。
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
trigger_words: ["技能封装", "skill creator", "技能生成", "技能定义", "参数抽象", "技能打包", "技能工厂"]
---

> 本内容由 AI 生成，仅供学习参考 <!-- ai-generated-notice -->

# 技能封装工作台（Skill Creator）

## 一、能力边界速查卡

### 1.1 工具能做什么

| 能力项 | 说明 | 示例 |
|--------|------|------|
| 数据文件解析 | 读取 CSV、JSON、TXT 三种格式的输入文件 | `input.csv`、`config.json`、`notes.txt` |
| 技能包骨架生成 | 在 `./skill_output/<技能名称>/` 下生成标准目录结构 | `SKILL.md`、`assets/`、`examples/` |
| 参数定义 | 为技能声明输入参数，支持类型、默认值、必填标记 | `--threshold 0.8` |
| 校验规则绑定 | 为正则、枚举、范围三类校验规则生成配置模板 | `pattern: ^[A-Z]{3}$` |
| 输出 Schema 映射 | 字段重命名、类型转换、默认值填充 | `price_str → price_float` |
| 自检模式 | 运行内置测试用例验证技能包完整性 | `skill creator --selftest` |

### 1.2 工具不能做什么

- 不能自动理解业务语义——需要你提供字段含义说明
- 不能生成业务逻辑代码——只生成技能定义骨架
- 不能保证输入数据质量——脏数据需要预先清洗
- 不能跨平台运行——仅支持 Python 3.9+ 环境
- 不能处理超过 500MB 的单个文件（内存限制）

### 1.3 适用对象

- 需要将现有数据文件（如配置表、规则集）转化为可复用技能包的开发者
- 需要为 AI Agent 定义标准化输入输出接口的工程师
- 需要为团队建立技能模板库的技术负责人

---

## 二、触发方式与场景映射

### 2.1 触发词

| 触发词 | 适用场景 |
|--------|----------|
| 技能封装 | 将散落的数据文件整理成技能包 |
| skill creator | 命令行直接调用（英文环境） |
| 技能生成 | 从零开始创建新技能 |
| 技能定义 | 为已有技能补充参数和校验规则 |
| 参数抽象 | 将硬编码参数提取为可配置项 |
| 技能打包 | 将多个相关文件合并为一个技能包 |
| 技能工厂 | 批量生成多个同构技能 |

### 2.2 场景示例

| 用户说 | 实际含义 | 工具动作 |
|--------|----------|----------|
| "帮我把这个 CSV 变成技能" | 将数据表转化为技能参数定义 | 解析 CSV 表头 → 生成参数模板 |
| "给这个技能加个正则校验" | 为某字段添加格式约束 | 生成校验规则配置 |
| "跑一下自检" | 验证技能包是否完整 | 执行内置测试用例 |
| "这个技能要能处理 JSON" | 支持 JSON 格式输入 | 生成 JSON 解析器配置 |

---

## 三、标准操作流程

### 3.1 前置条件

| 条件 | 要求 | 检查方式 |
|------|------|----------|
| 运行环境 | Python 3.9+ | `python --version` |
| 输入文件 | CSV/JSON/TXT，编码 UTF-8 | `file -i input.csv` |
| 文件大小 | ≤ 500MB | `ls -lh input.csv` |
| 字段命名 | 不含空格和特殊字符 | 正则 `^[a-zA-Z_][a-zA-Z0-9_]*$` |

### 3.2 执行步骤

**步骤 1：准备输入文件**

```bash
# 确保文件格式正确
head -5 input.csv
cat config.json | python -m json.tool
```

**步骤 2：启动技能封装**

```bash
skill creator --input data.csv
```

**步骤 3：交互式配置**

系统会依次提示：

```
请输入技能名称（小写字母+数字，2-20字符）: 
请输入技能描述（一句话，30字内）: 
是否为字段 price 添加校验规则？(y/n): 
选择校验类型 (1-正则 2-枚举 3-范围): 
```

**步骤 4：确认输出**

```bash
# 查看生成的技能包结构
tree ./skill_output/my_skill/
```

**步骤 5：运行自检**

```bash
skill creator --selftest --skill ./skill_output/my_skill/
```

### 3.3 输出规范

生成的技能包目录结构：

```
skill_output/
└── my_skill/
    ├── SKILL.md          # 技能主文档
    ├── parameters.yaml   # 参数定义
    ├── validation.yaml   # 校验规则
    ├── schema.yaml       # 输出映射
    ├── assets/           # 静态资源
    └── examples/
        └── sample.json   # 示例数据
```

---

## 四、置信度门控机制

### 4.1 信息不足时的处理

当输入数据存在以下情况时，系统会输出 `[需核实:字段名]` 占位符，而非猜测值：

| 场景 | 处理方式 | 示例 |
|------|----------|------|
| 字段类型不明确 | 标记为 `[需核实:type]` | `price: [需核实:type]` |
| 枚举值不完整 | 标记为 `[需核实:enum]` | `status: [需核实:enum]` |
| 默认值缺失 | 标记为 `[需核实:default]` | `timeout: [需核实:default]` |
| 关联关系不明 | 标记为 `[需核实:relation]` | `user_id: [需核实:relation]` |

### 4.2 使用规则

- 占位符必须保留在输出中，不得自行填充
- 用户需在后续编辑中补充真实值
- 自检模式会检测未解决的占位符并给出警告

---

## 五、错误码体系

| 错误码 | 错误描述 | 提示话术 | 修正步骤 |
|--------|----------|----------|----------|
| E001 | 文件不存在 | "找不到输入文件，请检查路径" | 确认文件路径，使用绝对路径 |
| E002 | 格式不支持 | "仅支持 CSV/JSON/TXT 格式" | 转换文件格式后重试 |
| E003 | 编码错误 | "文件编码不是 UTF-8" | 使用 `iconv -f GBK -t UTF-8` 转换 |
| E004 | 字段名非法 | "字段名含非法字符" | 重命名字段，使用下划线命名 |
| E005 | 校验规则冲突 | "正则与枚举规则不能同时使用" | 选择一种校验方式 |
| E006 | 输出目录已存在 | "目标目录已存在，是否覆盖？" | 选择覆盖或指定新目录 |
| E007 | 内存不足 | "文件过大，超出内存限制" | 分割文件后分批处理 |
| E008 | 参数缺失 | "缺少必填参数 --input" | 补充参数后重试 |

---

## 六、常见陷阱与反模式

### 6.1 陷阱一：忽略字段类型

**错误做法**：所有字段都定义为字符串类型

```yaml
# 错误示例
parameters:
  price: { type: string }
  count: { type: string }
```

**正确做法**：根据数据特征定义类型

```yaml
# 正确示例
parameters:
  price: { type: float, min: 0.0 }
  count: { type: integer, min: 0 }
```

### 6.2 陷阱二：过度校验

**错误做法**：为每个字段都添加正则校验

```yaml
# 错误示例
validation:
  name: { pattern: "^[a-zA-Z\\s]+$" }
  description: { pattern: "^.{1,500}$" }
```

**正确做法**：只对关键字段添加校验

```yaml
# 正确示例
validation:
  email: { pattern: "^[\\w.-]+@[\\w.-]+\\.\\w+$" }
  status: { enum: ["active", "inactive"] }
```

### 6.3 陷阱三：忽略默认值

**错误做法**：所有参数都设为必填

```yaml
# 错误示例
parameters:
  timeout: { required: true }
  retries: { required: true }
```

**正确做法**：为可选参数设置默认值

```yaml
# 正确示例
parameters:
  timeout: { required: false, default: 30 }
  retries: { required: false, default: 3 }
```

### 6.4 陷阱四：输出映射不完整

**错误做法**：只映射部分字段

```yaml
# 错误示例
schema:
  mappings:
    - source: name
      target: full_name
```

**正确做法**：完整映射所有字段

```yaml
# 正确示例
schema:
  mappings:
    - source: name
      target: full_name
    - source: age
      target: age_years
      type: integer
    - source: email
      target: contact_email
      default: "unknown@example.com"
```

### 6.5 陷阱五：忽略自检

**错误做法**：生成后不运行自检直接使用

**正确做法**：每次修改后都运行 `skill creator --selftest`

---

## 七、渐进式阅读路径

### 7.1 新手快速上手（5 分钟）

1. 阅读「能力边界速查卡」了解工具范围
2. 查看「场景示例」找到你的使用场景
3. 按「标准操作流程」完成一次完整操作
4. 遇到问题查「错误码体系」

### 7.2 进阶用户（15 分钟）

1. 学习「自定义校验」配置方法
2. 理解「输出 Schema 映射」的字段转换规则
3. 掌握「置信度门控」的使用场景
4. 阅读「常见陷阱与反模式」避免踩坑

### 7.3 高级用户（30 分钟）

1. 设计可复用的参数模板库
2. 实现插件式处理引擎
3. 构建技能版本管理机制
4. 编写性能优化策略（大数据量分片处理）

---

## 八、高级配置参考

### 8.1 自定义校验规则

```yaml
validation:
  # 正则校验
  product_code:
    pattern: "^[A-Z]{3}-\\d{4}$"
    message: "产品代码格式应为 XXX-1234"
  
  # 枚举校验
  status:
    enum: ["draft", "published", "archived"]
    message: "状态必须是 draft/published/archived 之一"
  
  # 范围校验
  price:
    range: [0.01, 9999.99]
    message: "价格必须在 0.01 到 9999.99 之间"
```

### 8.2 复杂处理逻辑

```yaml
processing:
  # 多表关联
  joins:
    - source: users.csv
      key: user_id
      target: orders.csv
      foreign_key: customer_id
  
  # 条件分支
  conditionals:
    - field: status
      if: "active"
      then: { action: "notify", channel: "email" }
      else: { action: "log", level: "warning" }
```

### 8.3 输出 Schema 映射

```yaml
schema:
  mappings:
    - source: user_name
      target: username
      type: string
    
    - source: signup_date
      target: created_at
      type: datetime
      format: "%Y-%m-%d"
    
    - source: is_admin
      target: role
      type: enum
      mapping:
        "true": "admin"
        "false": "user"
```

### 8.4 CI/CD 集成示例

```yaml
# .github/workflows/skill-build.yml
name: Build Skill
on: [push]
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run skill creator
        run: |
          skill creator --input data.csv --non-interactive
      - name: Run selftest
        run: |
          skill creator --selftest --skill ./skill_output/my_skill/
```

### 8.5 单元测试覆盖

```python
# test_skill_creator.py
import unittest
from skill_creator import SkillCreator

class TestSkillCreator(unittest.TestCase):
    def test_csv_parsing(self):
        creator = SkillCreator()
        result = creator.parse_file("test.csv")
        self.assertEqual(result.format, "csv")
    
    def test_validation_rules(self):
        creator = SkillCreator()
        rules = creator.generate_validation("email")
        self.assertIn("pattern", rules)
    
    def test_schema_mapping(self):
        creator = SkillCreator()
        schema = creator.map_schema({"name": "full_name"})
        self.assertEqual(schema["target"], "full_name")

if __name__ == "__main__":
    unittest.main()
```

---

## 九、性能优化策略

### 9.1 大数据量分片处理

```python
# 分片处理示例
CHUNK_SIZE = 10000

def process_large_file(file_path):
    with open(file_path, 'r') as f:
        chunk = []
        for line in f:
            chunk.append(line)
            if len(chunk) >= CHUNK_SIZE:
                process_chunk(chunk)
                chunk = []
        if chunk:
            process_chunk(chunk)
```

### 9.2 内存优化建议

| 数据量 | 建议方案 |
|--------|----------|
| < 10MB | 直接加载到内存 |
| 10MB - 100MB | 使用生成器逐行读取 |
| 100MB - 500MB | 分片处理 + 临时文件 |
| > 500MB | 不支持，需拆分文件 |

---

## 十、用户协议

**使用本 Skill 即视为同意以下条款：**

1. **责任承担**：使用者自行承担全部责任。本 Skill 提供的输出仅供参考，不构成任何形式的保证或承诺。
2. **禁止反向工程**：禁止对本 Skill 进行反向工程、反编译、破解或试图提取源代码。
3. **数据合规**：使用者应确保输入数据的合法性与合规性，不得使用本 Skill 处理违法违规内容。
4. **数据隐私**：本 Skill 不收集、存储或传输任何用户数据，所有处理均在本地完成。
5. **免责声明**：因使用本 Skill 产生的任何直接或间接损失，作者不承担任何责任。
6. **协议确认**：使用本 Skill 即视为同意本协议全部条款。

<!-- user-agreement-injected -->

---

## 十一、许可证（License）

本 Skill 采用 MIT 许可证发布：

```
MIT License

Copyright (c) 2024 SkillForge Studio

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

*文档版本：1.0.0 | 最后更新：2024年*
