---
slug: bob
name: bob
displayName: Go数据库方言转换与ORM代码生成
description: 面向Go开发者的SQL方言转换与ORM工厂代码生成工具，支持PostgreSQL、MySQL、SQLite。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 代码工匠
agent_created: true
trigger_words: ["SQL查询", "ORM生成", "查询构建器", "数据库方言", "Go模型生成", "方言转换", "代码生成"]
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# bob — Go 数据库方言转换与 ORM 代码生成 Skill

## 一、能力边界（一页纸速查卡）

### 1.1 能做什么

| 能力项 | 说明 | 支持范围 |
|--------|------|----------|
| SQL 方言转换 | 将一种数据库方言的 SQL 转换为另一种方言 | PostgreSQL ↔ MySQL ↔ SQLite |
| ORM 代码生成 | 根据表结构生成 Go 语言 ORM 模型代码 | 结构体定义、字段标签、CRUD 方法 |
| 查询构建器 | 生成链式查询构建代码 | 支持 Where、OrderBy、Limit、Join 等 |
| 类型映射 | 数据库类型到 Go 类型的自动映射 | 可自定义映射规则 |
| 配置管理 | 通过配置文件定制生成行为 | YAML 格式，支持全局和项目级 |
| 自动化集成 | 与 CI/CD 流水线、go generate 集成 | JSON 输出、命令行调用 |

### 1.2 不能做什么

| 限制项 | 说明 |
|--------|------|
| 不支持非 Go 语言 | 仅面向 Go 开发者 |
| 不支持 NoSQL 数据库 | 仅支持 PostgreSQL、MySQL、SQLite |
| 不处理复杂存储过程 | 仅处理标准 SQL DDL/DML 语句 |
| 不生成完整业务逻辑 | 仅生成数据访问层代码 |
| 不支持实时数据库连接 | 基于表结构 JSON 文件工作，不直连数据库 |

### 1.3 适用对象

- Go 后端开发者
- 需要多数据库兼容的项目团队
- 使用 ORM 框架（如 GORM、SQLBoiler）的开发者
- 需要自动化代码生成的 CI/CD 流水线

---

## 二、触发方式

### 2.1 触发词

当对话中出现以下关键词时，本 Skill 将被激活：

- SQL查询、ORM生成、查询构建器、数据库方言、Go模型生成
- 方言转换、代码生成、表结构转模型、数据库迁移

### 2.2 场景映射表

| 用户说（大白话） | 实际需求 | 触发动作 |
|------------------|----------|----------|
| "帮我把 MySQL 的建表语句转成 PostgreSQL" | SQL 方言转换 | 运行 `bob convert` |
| "根据这个表结构生成 Go 结构体" | ORM 代码生成 | 运行 `bob generate` |
| "我要生成带查询方法的模型代码" | 查询构建器生成 | 运行 `bob generate --with-queries` |
| "检查一下 bob 装好没有" | 安装验证 | 运行 `bob --selftest` |
| "生成一个配置文件" | 初始化配置 | 运行 `bob --init` |

---

## 三、标准流程

### 3.1 前置条件

| 条件 | 要求 | 验证方法 |
|------|------|----------|
| Go 环境 | Go 1.18+ | `go version` |
| bob 安装 | 已安装 bob 可执行文件 | `bob --version` |
| 表结构 JSON | 符合格式要求的表结构描述文件 | 见 3.2 节格式说明 |
| 配置文件（可选） | `~/.bob/config.yaml` 或项目级配置 | `bob --init` 生成 |

### 3.2 表结构 JSON 格式

```json
{
  "database": "mysql",
  "tables": [
    {
      "name": "users",
      "columns": [
        {
          "name": "id",
          "type": "INT",
          "nullable": false,
          "primary_key": true,
          "auto_increment": true
        },
        {
          "name": "email",
          "type": "VARCHAR(255)",
          "nullable": false,
          "unique": true
        },
        {
          "name": "created_at",
          "type": "TIMESTAMP",
          "nullable": false,
          "default": "CURRENT_TIMESTAMP"
        }
      ],
      "indexes": [
        {
          "name": "idx_email",
          "columns": ["email"],
          "unique": true
        }
      ]
    }
  ]
}
```

### 3.3 执行步骤

#### 步骤 1：验证安装

```bash
bob --selftest
```

预期输出：`bob: all checks passed`（或类似成功信息）

#### 步骤 2：初始化配置（首次使用）

```bash
bob --init
```

生成 `~/.bob/config.yaml`，包含默认类型映射和生成选项。

#### 步骤 3：准备表结构文件

创建 `schema.json`，内容遵循 3.2 节格式。

#### 步骤 4：执行方言转换

```bash
# 将 MySQL 方言转换为 PostgreSQL
bob convert --input schema.json --from mysql --to postgresql --output schema_pg.json

# 输出 JSON 格式（用于 CI/CD 集成）
bob convert --input schema.json --from mysql --to postgresql --format json
```

#### 步骤 5：生成 ORM 代码

```bash
# 生成基础模型代码
bob generate --input schema.json --output ./models

# 生成带查询构建器的代码
bob generate --input schema.json --output ./models --with-queries

# 指定包名
bob generate --input schema.json --output ./models --package models
```

#### 步骤 6：检查生成结果

```bash
# 查看生成的文件
ls -la ./models/

# 检查类型映射是否正确
cat ./models/users.go
```

### 3.4 输出规范

| 输出类型 | 格式 | 使用场景 |
|----------|------|----------|
| 方言转换结果 | SQL 文件或 JSON | 数据库迁移、多数据库支持 |
| ORM 模型代码 | .go 文件 | Go 项目数据访问层 |
| 查询构建器 | .go 文件（含链式方法） | 复杂查询场景 |
| 转换报告 | JSON（`--format json`） | CI/CD 流水线解析 |

---

## 四、置信度门控

### 4.1 信息不足时的处理

当输入信息不完整时，bob 会输出 `[需核实:字段名]` 占位符，而不是猜测或编造。

| 场景 | 输出示例 | 处理建议 |
|------|----------|----------|
| 缺少主键定义 | `[需核实:primary_key]` | 检查表结构，确认主键字段 |
| 类型映射不明确 | `[需核实:type_mapping]` | 在配置文件中添加自定义映射 |
| 默认值不确定 | `[需核实:default_value]` | 明确指定默认值或留空 |
| 索引信息缺失 | `[需核实:indexes]` | 补充索引定义或确认无索引 |

### 4.2 处理原则

1. 不猜测：遇到不确定的信息，一律输出占位符
2. 不编造：不生成虚构的字段或类型
3. 可追溯：占位符包含字段名，便于定位问题

---

## 五、错误码体系

### 5.1 常见错误与修正

| 错误码 | 错误信息 | 原因 | 提示话术 | 修正步骤 |
|--------|----------|------|----------|----------|
| E001 | `invalid input file` | 输入 JSON 格式错误 | "请检查表结构 JSON 文件格式" | 1. 使用 `jq . schema.json` 验证 JSON 合法性<br>2. 对照 3.2 节格式检查字段 |
| E002 | `unsupported database` | 不支持的数据库类型 | "仅支持 PostgreSQL、MySQL、SQLite" | 1. 检查 `--from`/`--to` 参数<br>2. 确认数据库类型拼写正确 |
| E003 | `type mapping not found` | 数据库类型无对应 Go 类型 | "请在配置文件中添加类型映射" | 1. 打开 `~/.bob/config.yaml`<br>2. 在 `type_mappings` 中添加映射 |
| E004 | `output directory not writable` | 输出目录无写权限 | "请检查输出目录权限" | 1. 确认目录存在<br>2. 使用 `chmod` 调整权限 |
| E005 | `invalid config file` | 配置文件格式错误 | "请检查 YAML 配置格式" | 1. 使用 `bob --init` 重新生成<br>2. 手动检查 YAML 缩进 |
| E006 | `duplicate table name` | 表名重复 | "请检查表结构定义" | 1. 确认表名唯一<br>2. 检查是否有大小写冲突 |

### 5.2 错误处理流程

```
遇到错误
    ↓
查看错误码
    ↓
根据提示话术定位问题
    ↓
执行修正步骤
    ↓
重新运行命令
    ↓
验证输出
```

---

## 六、FAQ 反模式

### 6.1 常见坑与反模式对照

| 常见坑 | 反模式（错误做法） | 正确做法 |
|--------|-------------------|----------|
| 类型映射错误 | 直接修改生成的代码 | 在配置文件中添加自定义类型映射，重新生成 |
| 方言转换后 SQL 不兼容 | 手动逐条修改 SQL | 使用 `bob convert` 自动转换，检查转换报告 |
| 生成代码与项目风格不一致 | 接受默认生成风格 | 编写自定义模板，通过 `--template` 参数指定 |
| 忽略配置文件 | 每次手动指定所有参数 | 使用 `bob --init` 生成配置，统一管理 |
| 不验证生成结果 | 直接使用生成代码 | 运行 `go vet` 和 `go build` 验证 |

### 6.2 反模式示例

**反模式 1：手动修改生成代码**

```go
// ❌ 错误：直接修改生成的文件
type User struct {
    ID   int    `gorm:"column:id"`
    Name string `gorm:"column:name"`
    // 手动添加了字段，但下次生成会被覆盖
    Age  int    `gorm:"column:age"`
}
```

**正确做法：**

```yaml
# ✅ 正确：在配置文件中添加自定义映射
type_mappings:
  TINYINT: int8
  MEDIUMINT: int32
```

**反模式 2：忽略方言差异**

```sql
-- ❌ 错误：直接复制 MySQL 的 SQL 到 PostgreSQL
CREATE TABLE users (
  id INT AUTO_INCREMENT PRIMARY KEY,
  email VARCHAR(255) UNIQUE
);
```

**正确做法：**

```bash
# ✅ 正确：使用 bob 转换方言
bob convert --input schema.json --from mysql --to postgresql
```

---

## 七、渐进式披露

### 7.1 速查卡（新手必读）

```bash
# 1. 验证安装
bob --selftest

# 2. 初始化配置
bob --init

# 3. 生成 ORM 代码
bob generate --input schema.json --output ./models

# 4. 方言转换
bob convert --input schema.json --from mysql --to postgresql

# 5. 查看帮助
bob --help
```

### 7.2 分层次阅读路径

#### 新手路径（首次使用）

1. 阅读「能力边界」了解工具范围
2. 运行 `bob --selftest` 验证安装
3. 运行 `bob --init` 生成配置
4. 准备表结构 JSON 文件
5. 运行 `bob generate` 生成代码
6. 检查生成结果

#### 进阶路径（日常使用）

1. 自定义 `~/.bob/config.yaml` 中的类型映射
2. 使用 `bob convert --format json` 输出 JSON，接入 CI/CD 流水线
3. 配置变更检测，使用 `jq` 解析变更并触发自动构建
4. 结合 `go generate` 实现代码生成自动化
5. 编写自定义模板，扩展生成代码的风格

#### 专家路径（深度定制）

1. 编写自定义 Go 模板，控制生成代码的每个细节
2. 开发插件扩展 bob 的功能
3. 将 bob 集成到完整的代码生成流水线
4. 为团队制定统一的代码生成规范

---

## 八、配置参考

### 8.1 默认配置文件结构

```yaml
# ~/.bob/config.yaml
version: "1.0"

type_mappings:
  # 数据库类型到 Go 类型的映射
  INT: int
  BIGINT: int64
  VARCHAR: string
  TEXT: string
  BOOLEAN: bool
  TIMESTAMP: time.Time
  DATE: time.Time
  FLOAT: float64
  DOUBLE: float64
  DECIMAL: float64
  JSON: interface{}

generation:
  package_name: models
  with_queries: false
  with_timestamps: true
  json_tags: true
  gorm_tags: true

conversion:
  preserve_comments: true
  output_format: sql
```

### 8.2 自定义类型映射示例

```yaml
type_mappings:
  # 自定义映射
  MEDIUMINT: int32
  TINYINT: int8
  ENUM: string
  UUID: string
  JSONB: interface{}
```

---

## 九、CI/CD 集成示例

### 9.1 GitHub Actions 示例

```yaml
name: Generate ORM Code

on:
  push:
    paths:
      - 'schema/**'

jobs:
  generate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Setup Go
        uses: actions/setup-go@v4
        with:
          go-version: '1.21'
      - name: Install bob
        run: go install github.com/example/bob@latest
      - name: Generate ORM code
        run: |
          bob generate --input schema/schema.json --output ./models
          bob convert --input schema/schema.json --from mysql --to postgresql --format json > conversion_report.json
      - name: Check for changes
        run: |
          if git diff --quiet; then
            echo "No changes"
          else
            echo "Changes detected"
            git add .
            git commit -m "chore: regenerate ORM code"
            git push
          fi
```

### 9.2 go generate 集成

```go
//go:generate bob generate --input schema.json --output ./models --package models
//go:generate bob convert --input schema.json --from mysql --to postgresql --output schema_pg.sql

package models
```

---

## 十、用户协议

<!-- user-agreement-injected -->

**使用条款**

1. **责任承担**：使用者自行承担使用本 Skill 及 bob 工具的全部责任。因使用本 Skill 产生的任何直接或间接损失，作者不承担任何责任。

2. **禁止反向工程**：禁止对本 Skill 文档及关联工具进行反向工程、反编译、破解或任何形式的未授权修改。

3. **合规使用**：使用者应确保使用本 Skill 的行为符合当地法律法规及所在组织的政策要求。

4. **无担保声明**：本 Skill 按"原样"提供，不附带任何明示或暗示的担保，包括但不限于适销性、特定用途适用性和非侵权保证。

5. **更新与变更**：作者保留随时修改、更新或终止本 Skill 的权利，恕不另行通知。

---

## 十一、许可证（License）

<!-- professional-license-embedded -->

**MIT License**

版权所有 (c) 2024 代码工匠

特此免费授予任何获得本软件及相关文档文件（以下简称"软件"）副本的人士，不受限制地处理本软件，包括但不限于使用、复制、修改、合并、发布、分发、再许可和/或销售软件副本的权利，并允许向其提供软件的人士在遵守以下条件的前提下这样做：

上述版权声明和本许可声明应包含在软件的所有副本或实质性部分中。

本软件按"原样"提供，不附带任何明示或暗示的担保，包括但不限于适销性、特定用途适用性和非侵权保证。在任何情况下，作者或版权持有人均不对因使用本软件而产生的任何索赔、损害或其他责任负责，无论是在合同诉讼、侵权或其他诉讼中。

---

*本 Skill 由 AI 辅助生成，仅供参考。使用前请阅读相关文档。*
