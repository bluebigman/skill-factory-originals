---
slug: go-sqlbuilder
name: go-sqlbuilder
displayName: SQL查询构建 Go工具链
description: 面向Go语言SQL查询构建场景的规范流程与输出模板。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 技能工坊·青梧
agent_created: true
trigger_words: ["go-sqlbuilder", "SQL查询", "数据库操作", "Go SQL构建", "查询构造器"]
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# go-sqlbuilder 技能文档

## 一、能力边界速查卡

### 1.1 能做与不能做

| 维度 | 能做 ✅ | 不能做 ❌ |
|------|---------|-----------|
| 输入处理 | 解析用户提供的SQL语句、Go代码片段、表结构描述 | 无法直接连接真实数据库执行查询 |
| 查询构建 | 生成符合go-sqlbuilder库规范的查询构建代码 | 不替代官方文档，不生成完整业务系统 |
| 格式转换 | 将自然语言描述转换为SQL构建代码 | 不处理非SQL相关的编程问题 |
| 批量处理 | 支持多表、多查询场景的批量代码生成 | 不执行批量数据迁移或ETL任务 |
| 输出定制 | 按用户指定格式输出代码、注释、示例 | 不生成与go-sqlbuilder无关的代码 |

### 1.2 适用对象

- **适用**：Go语言开发者、需要快速生成SQL构建代码的工程师、学习go-sqlbuilder库的初学者
- **不适用**：非Go语言项目、无需SQL构建的纯前端场景、生产环境直接部署

---

## 二、触发方式与场景映射

### 2.1 触发词

当用户输入包含以下关键词时，本技能自动激活：

| 触发词 | 典型场景 |
|--------|----------|
| go-sqlbuilder | 直接提及库名 |
| SQL查询 | 需要构建查询语句 |
| 数据库操作 | 涉及增删改查 |
| Go SQL构建 | 需要Go代码实现 |
| 查询构造器 | 需要链式调用构建 |

### 2.2 场景映射表

| 用户说 | 实际需求 | 本技能响应 |
|--------|----------|------------|
| "帮我写个查询用户的SQL" | 生成查询代码 | 输出go-sqlbuilder构建代码 |
| "这个表结构怎么查" | 表结构转查询 | 解析字段并生成SELECT语句 |
| "批量插入怎么做" | 批量操作 | 生成InsertBatch代码 |
| "条件查询怎么写" | 动态条件 | 生成Where条件构建代码 |

---

## 三、标准处理流程

### 3.1 前置条件

1. 确认用户已安装go-sqlbuilder库（版本≥1.0.0）
2. 确认用户提供表结构或字段信息
3. 确认输出格式偏好（代码注释、示例数量）

### 3.2 执行步骤

**步骤1：输入解析**
- 提取SQL语句或表结构信息
- 识别关键字段、表名、条件

**步骤2：代码生成**
- 根据输入生成go-sqlbuilder构建代码
- 遵循以下参数规范：

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| tableName | string | 是 | 无 | 目标表名 |
| fields | []string | 是 | 无 | 查询字段列表 |
| conditions | map[string]interface{} | 否 | 空 | 查询条件 |
| orderBy | string | 否 | 空 | 排序字段 |
| limit | int | 否 | 0 | 限制条数 |

**步骤3：输出规范**
- 生成代码包含完整导入语句
- 附带简要注释说明
- 标注置信度

### 3.3 输出示例

```go
import (
    "github.com/huandu/go-sqlbuilder"
)

func buildQuery() string {
    sb := sqlbuilder.NewSelectBuilder()
    sb.Select("id", "name", "email")
    sb.From("users")
    sb.Where(sb.Equal("status", 1))
    sb.OrderBy("created_at DESC")
    sb.Limit(10)
    
    sql, args := sb.Build()
    return sql
}
```

---

## 四、置信度门控机制

### 4.1 置信度标注规则

| 置信度等级 | 标注方式 | 适用场景 |
|------------|----------|----------|
| 高（≥90%） | 无标注 | 输入信息完整、明确 |
| 中（70-89%） | `[置信度:中]` | 部分信息缺失但可推断 |
| 低（<70%） | `[需核实:字段名]` | 关键信息不明确 |

### 4.2 信息不足处理

当出现以下情况时，使用占位符而非编造：

- 表名未知：`[需核实:表名]`
- 字段列表不完整：`[需核实:字段列表]`
- 条件逻辑模糊：`[需核实:查询条件]`

---

## 五、错误码体系

### 5.1 常见错误与修正

| 错误码 | 错误描述 | 提示话术 | 修正步骤 |
|--------|----------|----------|----------|
| ERR001 | 表名缺失 | "请提供目标表名" | 补充表名后重试 |
| ERR002 | 字段列表为空 | "请指定查询字段" | 提供字段列表或使用* |
| ERR003 | 条件格式错误 | "条件格式应为key-value" | 检查条件格式 |
| ERR004 | 排序字段不存在 | "排序字段不在查询字段中" | 确认排序字段 |
| ERR005 | 版本不兼容 | "go-sqlbuilder版本过低" | 升级至≥1.0.0 |

---

## 六、FAQ 反模式对照

### 6.1 常见坑位

| 坑位 | 反模式 | 正确做法 |
|------|--------|----------|
| 忽略参数绑定 | 直接拼接SQL字符串 | 使用Build()方法自动绑定参数 |
| 过度使用SELECT * | 无条件查询所有字段 | 明确指定所需字段 |
| 忽略错误处理 | 不检查Build()返回值 | 始终检查err并处理 |
| 条件拼接混乱 | 手动拼接Where条件 | 使用Equal/In等构建器方法 |
| 忽略SQL注入 | 直接使用用户输入 | 使用参数化查询 |

---

## 七、渐进式披露路径

### 7.1 新手快速上手

1. 阅读能力边界速查卡
2. 查看标准处理流程
3. 复制输出示例代码
4. 运行并验证结果

### 7.2 进阶使用指南

1. 深入理解置信度门控机制
2. 掌握错误码修正流程
3. 探索批量处理与自定义格式
4. 结合官方文档深入学习

---

## 八、使用注意事项

1. 本技能生成的代码仅供学习参考，生产环境使用前需充分测试
2. 涉及敏感数据操作时，请确保符合相关安全规范
3. 批量处理前建议先进行小规模验证
4. 如遇复杂场景，建议结合官方文档综合判断

---

## 用户协议

<!-- user-agreement-injected -->

**使用前请仔细阅读以下条款：**

1. **责任承担**：使用者自行承担因使用本技能产生的全部责任。本技能提供的代码、建议和输出仅供参考，不构成任何形式的保证或承诺。

2. **禁止反向工程**：未经授权，不得对本技能进行反向工程、反编译、破解或试图提取底层逻辑。

3. **合规使用**：使用者应确保使用场景符合相关法律法规及所在组织的规定。

4. **免责声明**：本技能由AI辅助生成，可能存在不准确或不完整之处。使用者应结合实际情况进行判断。

5. **持续改进**：如发现任何问题或改进建议，欢迎反馈，但本技能不承诺及时更新或修复。

---

## 许可证（License）

<!-- professional-license-embedded -->

**MIT License**

Copyright (c) 2024 技能工坊·青梧

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
