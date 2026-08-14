---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: simply-versioned
name: simply-versioned
displayName: 模型版本追踪 数据回溯 轻量方案
description: 为 ActiveRecord 模型提供轻量、非侵入式的版本追踪与回溯方案。
version: 1.0.3
rules_version: cpr-20260814-n426
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/simply-versioned
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 独立技能工坊
agent_created: true
trigger_words: ["simply-versioned", "版本管理", "模型版本", "ActiveRecord版本", "数据追踪", "记录历史", "数据快照", "回滚记录"]
---

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->


> 本内容由 AI 生成，仅供学习参考 <!-- ai-generated-notice -->

# simply-versioned — 轻量级 ActiveRecord 版本追踪与回溯

## 一、能力边界（一页纸速查卡）

### 1.1 能做什么

| 能力项 | 说明 | 示例 |
|--------|------|------|
| 版本快照 | 为模型实例创建不可变的历史快照 | `post.create_version!` |
| 历史回溯 | 将模型恢复到任意历史版本 | `post.revert_to(version_id)` |
| 差异对比 | 比较两个版本之间的字段差异 | `version1.diff(version2)` |
| 版本列表 | 获取模型实例的完整版本历史 | `post.versions` |
| 非侵入集成 | 无需修改现有模型代码，通过模块引入即可 | `include SimplyVersioned::Model` |

### 1.2 不能做什么

| 限制项 | 说明 |
|--------|------|
| 不支持关联对象版本化 | 仅追踪模型自身字段，不追踪 `has_many` / `belongs_to` 关联对象的变化 |
| 不支持二进制大字段 | 对 `BLOB` / `TEXT` 类型字段的存储效率较低，建议使用外部存储 |
| 不提供自动版本创建 | 需要显式调用 `create_version!`，不会在每次保存时自动创建版本 |
| 不处理并发冲突 | 多个进程同时写入版本时，不提供乐观锁或悲观锁机制 |
| 不提供版本清理策略 | 版本记录会持续累积，需自行实现定期清理 |

### 1.3 适用对象

- **适用场景**：需要轻量级审计追踪的 Rails 应用；需要手动控制版本创建时机的业务逻辑；不希望引入重量级 gem（如 `paper_trail`）的简单项目。
- **不适用场景**：需要自动记录每次变更的合规审计系统；需要追踪关联对象变化的复杂数据模型；需要高并发写入的版本管理场景。

---

## 二、触发方式

### 2.1 触发词

当用户输入以下关键词时，本 Skill 将被激活：

- `simply-versioned`
- `版本管理`
- `模型版本`
- `ActiveRecord版本`
- `数据追踪`
- `记录历史`
- `数据快照`
- `回滚记录`

### 2.2 场景映射表

| 用户说（大白话） | 实际需求 | 本 Skill 提供的方案 |
|------------------|----------|---------------------|
| "我想给文章加个历史记录功能" | 为 Post 模型添加版本追踪 | 引入 `SimplyVersioned::Model` 模块，调用 `create_version!` |
| "用户误改了数据，怎么恢复？" | 数据回滚 | 使用 `revert_to(version_id)` 方法 |
| "我想看看这条记录改过几次" | 版本列表 | 调用 `versions` 方法获取历史版本数组 |
| "两个版本之间有什么不同？" | 版本差异 | 使用 `diff(other_version)` 方法 |
| "我不想每次保存都自动存版本" | 手动控制版本创建 | 仅在需要时显式调用 `create_version!` |

---

## 三、标准流程

### 3.1 前置条件

| 条件 | 要求 | 验证方式 |
|------|------|----------|
| Ruby 环境 | Ruby ≥ 2.7 | `ruby -v` |
| Rails 版本 | Rails ≥ 6.0 | `rails -v` |
| 数据库 | 支持 JSON 字段（PostgreSQL / MySQL 5.7+） | `ActiveRecord::Base.connection.adapter_name` |
| 迁移文件 | 已创建 `versions` 表 | `rails db:migrate:status` |

### 3.2 安装与配置步骤

**步骤 1：安装 gem**

在 `Gemfile` 中添加：

```ruby
gem 'simply-versioned', '~> 1.0'
```

执行 `bundle install`。

**步骤 2：生成迁移文件**

```bash
rails generate simply_versioned:install
rails db:migrate
```

**步骤 3：在模型中引入模块**

```ruby
class Post < ApplicationRecord
  include SimplyVersioned::Model
end
```

**步骤 4：创建版本**

```ruby
post = Post.find(1)
post.title = "新标题"
post.save
post.create_version!  # 显式创建版本快照
```

**步骤 5：回溯版本**

```ruby
version = post.versions.last
post.revert_to(version.id)
post.save
```

### 3.3 输出规范

| 方法 | 返回类型 | 说明 |
|------|----------|------|
| `create_version!` | `Version` 对象 | 创建版本快照，返回版本记录 |
| `versions` | `Array<Version>` | 按时间倒序返回所有版本 |
| `revert_to(version_id)` | `Boolean` | 将模型属性恢复至指定版本，返回是否成功 |
| `diff(other_version)` | `Hash` | 返回字段差异，格式为 `{ field_name => [old_value, new_value] }` |

---

## 四、置信度门控

当遇到以下信息不足的情况时，本 Skill 将输出 `[需核实:字段]` 占位符，不会编造数据：

| 场景 | 占位符示例 | 处理方式 |
|------|------------|----------|
| 用户未指定模型名称 | `[需核实:模型名称]` | 提示用户提供模型类名 |
| 用户未指定版本 ID | `[需核实:版本ID]` | 提示用户提供版本 ID 或查询版本列表 |
| 数据库适配器未知 | `[需核实:数据库类型]` | 提示用户确认数据库类型 |
| 版本表结构不明确 | `[需核实:versions表结构]` | 提示用户运行 `rails db:schema:dump` 查看 |

---

## 五、错误码体系

| 错误码 | 错误描述 | 提示话术 | 修正步骤 |
|--------|----------|----------|----------|
| `SV-001` | 模型未引入模块 | "模型未包含 SimplyVersioned::Model 模块" | 在模型类中添加 `include SimplyVersioned::Model` |
| `SV-002` | 版本表不存在 | "versions 表未创建，请先运行迁移" | 执行 `rails generate simply_versioned:install` 和 `rails db:migrate` |
| `SV-003` | 版本 ID 无效 | "找不到指定的版本记录" | 使用 `post.versions` 确认版本 ID 是否存在 |
| `SV-004` | 字段类型不支持 | "该字段类型不支持版本化存储" | 将字段转换为 JSON 兼容类型，或使用 `serialize` 方法 |
| `SV-005` | 并发写入冲突 | "检测到并发写入，请重试" | 使用事务包裹版本创建操作，或添加重试逻辑 |

---

## 六、FAQ 反模式

### 6.1 常见坑与反模式对照

| 常见坑 | 反模式示例 | 正确做法 |
|--------|------------|----------|
| **自动版本陷阱** | 期望每次 `save` 自动创建版本 | 明确调用 `create_version!`，或使用 `after_save` 回调（需自行实现） |
| **关联对象丢失** | 版本化后关联对象变化未被记录 | 在版本快照中手动序列化关联对象的 ID 列表 |
| **版本无限增长** | 从不清理旧版本，导致数据库膨胀 | 定期执行 `post.versions.where('created_at < ?', 30.days.ago).delete_all` |
| **回滚后不保存** | 调用 `revert_to` 后忘记 `save` | 回滚后必须调用 `save` 持久化变更 |
| **忽略 JSON 字段限制** | 在 SQLite 上使用 JSON 字段导致报错 | 确认数据库支持 JSON 类型，或改用 `text` 字段 + `serialize` |

### 6.2 反模式对照表

| 反模式 | 问题 | 替代方案 |
|--------|------|----------|
| 在 `before_save` 中自动创建版本 | 每次保存都产生版本，数据冗余 | 仅在关键操作后手动调用 `create_version!` |
| 使用 `update_all` 批量修改后创建版本 | 绕过 ActiveRecord 回调，版本记录不完整 | 使用 `each` 循环逐条更新并创建版本 |
| 将版本表与业务表放在同一数据库 | 业务数据增长影响版本查询性能 | 考虑将版本表迁移至独立数据库或使用分区表 |

---

## 七、渐进式披露

### 7.1 速查卡（30 秒上手）

```ruby
# 1. 引入模块
class Post < ApplicationRecord
  include SimplyVersioned::Model
end

# 2. 创建版本
post.create_version!

# 3. 查看版本
post.versions

# 4. 回滚版本
post.revert_to(version_id)
post.save
```

### 7.2 新手路径（5 分钟）

1. 阅读「能力边界」了解适用范围。
2. 按照「标准流程」完成安装与配置。
3. 使用速查卡中的四个核心方法完成基本操作。
4. 遇到问题时查阅「错误码体系」定位问题。

### 7.3 进阶路径（15 分钟）

1. 深入阅读「FAQ 反模式」避免常见陷阱。
2. 自定义版本存储策略（如：仅存储变更字段）。
3. 实现版本清理的定时任务。
4. 扩展 `diff` 方法以支持嵌套字段对比。

---

## 八、自定义扩展指南

### 8.1 自定义版本存储

默认情况下，版本快照存储为 JSON 格式。如需自定义存储格式：

```ruby
class Version < ActiveRecord::Base
  belongs_to :versionable, polymorphic: true

  def snapshot
    JSON.parse(data)
  end

  def snapshot=(hash)
    self.data = hash.to_json
  end
end
```

### 8.2 版本清理策略

```ruby
# 保留最近 30 天的版本，其余删除
def self.cleanup_old_versions(days = 30)
  where('created_at < ?', days.days.ago).delete_all
end
```

### 8.3 差异对比增强

```ruby
def diff(other_version)
  current = snapshot
  previous = other_version.snapshot
  (current.keys | previous.keys).each_with_object({}) do |key, diff|
    diff[key] = [previous[key], current[key]] if previous[key] != current[key]
  end
end
```

---

## 九、性能考量

| 场景 | 性能建议 |
|------|----------|
| 频繁创建版本 | 使用批量插入（`insert_all`）减少数据库往返 |
| 版本表数据量大 | 为 `versionable_type` 和 `versionable_id` 添加复合索引 |
| 查询历史版本 | 使用 `limit` 和 `offset` 进行分页查询 |
| 版本数据序列化 | 使用 `Oj` 等高性能 JSON 解析器替代默认的 `JSON` |

---

## 十、用户协议

使用本 Skill 即表示您同意以下条款：

1. **责任承担**：使用者自行承担因使用本 Skill 产生的全部责任。本 Skill 提供的代码示例和配置方法仅供参考，不构成任何形式的保证。
2. **禁止反向工程**：不得对本 Skill 生成的文档、代码示例进行反向工程、反编译或试图提取底层算法。
3. **合规使用**：使用者应确保其使用场景符合当地法律法规及所在组织的安全规范。
4. **无担保声明**：本 Skill 按"原样"提供，不附带任何明示或暗示的担保，包括但不限于适销性、特定用途适用性和非侵权保证。

<!-- user-agreement-injected -->

---

## 十一、许可证（License）

本 Skill 采用 MIT 许可证发布。

```
MIT License

Copyright (c) 2026 独立技能工坊

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

*本 Skill 由 AI 辅助生成，仅供参考。使用前请阅读相关文档并验证代码在目标环境中的兼容性。*
