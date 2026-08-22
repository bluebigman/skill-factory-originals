---
slug: audited
name: audited
displayName: 模型审计 属性追踪 操作留痕
description: 为Rails模型自动记录属性变更，提供完整审计日志与操作追溯能力。
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
trigger_words: ["audited", "acts_as_audited", "审计日志", "模型变更记录", "操作追踪", "属性变更", "操作留痕", "变更历史"]
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# audited — Rails 模型审计日志接入指南

## 一、能力边界速查卡

### 1.1 本 Skill 能做什么

| 能力项 | 说明 |
|--------|------|
| 模型属性变更记录 | 在 ActiveRecord 模型中启用后，自动捕获 create / update / destroy 时的属性变化 |
| 审计日志查询 | 支持按模型、按记录、按时间范围、按操作者等维度检索审计记录 |
| 操作者追踪 | 记录执行操作的用户（通过 `current_user` 或手动传入） |
| 关联对象审计 | 可配置记录关联对象的变更（如订单明细随订单一起审计） |
| 自定义审计字段 | 可指定只审计某些字段，或额外记录自定义元数据 |
| 操作备注 | 通过 `comment` 字段为每次操作附加说明文字 |
| 请求链路追踪 | 利用 `request_uuid` 将一次 HTTP 请求内的所有审计记录关联起来 |

### 1.2 本 Skill 不能做什么

| 限制项 | 说明 |
|--------|------|
| 不替代数据库备份 | 审计日志记录的是业务操作轨迹，不是数据恢复手段 |
| 不记录未启用模型的变更 | 只有显式声明 `acts_as_audited` 的模型才会被追踪 |
| 不自动清理历史数据 | 日志会持续累积，需要自行设计归档策略 |
| 不捕获纯 SQL 变更 | 通过 `update_all` / `delete_all` 等批量操作不会触发审计 |
| 不记录读操作 | 只记录写操作（增、删、改），不记录查询行为 |

### 1.3 适用对象

- 使用 Ruby on Rails（4.2+）的项目
- 需要满足合规审计要求的业务系统（如金融、医疗、政务）
- 需要追溯数据变更责任人的协作平台
- 需要排查生产环境数据异常原因的运维场景

---

## 二、触发方式与场景映射

当你的对话中出现以下关键词时，本 Skill 将被激活：

| 触发词 | 典型场景 |
|--------|----------|
| `audited` / `acts_as_audited` | 直接引用 gem 名称 |
| 审计日志 | 需要记录模型变更历史 |
| 模型变更记录 | 想追踪某张表的增删改 |
| 操作追踪 | 需要知道谁在什么时候改了什么 |
| 属性变更 | 关注某个字段的历次修改值 |
| 操作留痕 | 合规要求，需要不可抵赖的操作记录 |

**大白话场景示例：**

- "我想看看用户表里那条记录是谁改的" → 启用审计 + 查询操作者
- "订单状态每次变化都要留个底" → 在 Order 模型启用审计，关注 status 字段
- "出问题了想回滚，但不知道之前的值" → 查询审计日志中的旧值/新值

---

## 三、标准执行流程

### 3.1 前置条件

| 条件 | 要求 |
|------|------|
| Rails 版本 | 4.2 及以上（推荐 5.0+） |
| Ruby 版本 | 2.3 及以上 |
| 数据库 | PostgreSQL / MySQL / SQLite 均可 |
| 认证机制 | 已有 `current_user` 或等效方法（可选，但推荐） |

### 3.2 执行步骤

#### 步骤 1：安装 gem

在 `Gemfile` 中添加：

```ruby
gem 'audited', '~> 5.0'
```

然后执行：

```bash
bundle install
```

#### 步骤 2：生成迁移文件

```bash
rails generate audited:install
rails db:migrate
```

该命令会生成 `audits` 表，核心字段如下：

| 字段 | 类型 | 说明 |
|------|------|------|
| `auditable_id` | integer | 被审计记录的 ID |
| `auditable_type` | string | 被审计模型的类名 |
| `associated_id` | integer | 关联对象的 ID（可空） |
| `associated_type` | string | 关联对象的类名（可空） |
| `user_id` | integer | 操作者 ID（可空） |
| `user_type` | string | 操作者类型（可空） |
| `username` | string | 操作者用户名（冗余存储） |
| `action` | string | 操作类型：`create` / `update` / `destroy` |
| `audited_changes` | text | 变更内容（序列化存储） |
| `version` | integer | 版本号（同一记录每次变更递增） |
| `comment` | string | 操作备注（可空） |
| `request_uuid` | string | 请求 UUID，用于链路追踪 |
| `created_at` | datetime | 审计记录创建时间 |

#### 步骤 3：在模型中启用审计

```ruby
class Order < ApplicationRecord
  acts_as_audited
end
```

如需限定只审计特定字段：

```ruby
class Order < ApplicationRecord
  acts_as_audited only: [:status, :total_amount, :shipping_address]
end
```

如需排除某些字段：

```ruby
class Order < ApplicationRecord
  acts_as_audited except: [:updated_at, :encrypted_password]
end
```

#### 步骤 4：配置异步写入（可选，降低主库压力）

在 `config/initializers/audited.rb` 中：

```ruby
Audited.config do |config|
  # 使用 ActiveJob 异步写入审计日志
  config.async = true
  
  # 指定队列名称（默认 :audited）
  config.queue_name = :low_priority
end
```

> 注意：启用异步后，审计记录不会立即写入数据库，查询时可能存在短暂延迟。

#### 步骤 5：配置操作者来源

在 `ApplicationController` 中：

```ruby
class ApplicationController < ActionController::Base
  # 使用当前登录用户作为操作者
  audit_current_user_method :current_user
end
```

如果使用 Devise，默认即可生效。手动指定操作者：

```ruby
Audited.audit_class.as_user(current_user) do
  order.update!(status: 'shipped')
end
```

#### 步骤 6：配置关联追踪（可选）

```ruby
class Order < ApplicationRecord
  acts_as_audited
  
  # 关联的 OrderItem 变更时，也会记录到 Order 的审计日志中
  has_many :order_items, dependent: :destroy
  associated_with :order_items
end
```

#### 步骤 7：配置自定义字段（可选）

```ruby
class Order < ApplicationRecord
  acts_as_audited
  
  # 在审计记录中额外保存当前店铺 ID
  audited_custom_fields :store_id
  
  def store_id
    self.store&.id
  end
end
```

### 3.3 输出规范

完成接入后，应验证以下输出：

1. 对启用审计的模型执行 create / update / destroy 操作
2. 确认 `audits` 表中生成了对应记录
3. 确认 `audited_changes` 字段中包含了变更前后的值
4. 确认 `user_id` / `username` 正确记录了操作者

---

## 四、查询与检索示例

### 4.1 查看某条记录的全部变更历史

```ruby
order = Order.find(123)
order.audits
# => [#<Audited::Audit id: 1, action: "create", ...>,
#     #<Audited::Audit id: 2, action: "update", ...>]
```

### 4.2 查看某条记录的指定字段变更

```ruby
order.audits.where("audited_changes LIKE ?", "%status%")
```

或使用辅助方法：

```ruby
order.audits.map { |a| a.audited_changes["status"] }
# => [["pending", "paid"], ["paid", "shipped"]]
```

### 4.3 按操作者筛选审计记录

```ruby
Audited.audit_class.where(user_id: current_user.id)
```

### 4.4 按时间范围查询

```ruby
Audited.audit_class.where(created_at: 1.week.ago..Time.current)
```

### 4.5 查询某个模型的所有变更

```ruby
Audited.audit_class.where(auditable_type: "Order")
```

### 4.6 查询某个操作者的全部操作（含关联对象）

```ruby
Audited.audit_class.where(user_id: 42).order(created_at: :desc)
```

### 4.7 利用 request_uuid 追踪一次请求内的所有变更

```ruby
# 先找到某条审计记录的 request_uuid
audit = Audited.audit_class.find(123)
Audited.audit_class.where(request_uuid: audit.request_uuid)
```

---

## 五、性能注意事项

### 5.1 索引建议

在 `audits` 表上建议创建以下索引：

```ruby
# 在迁移中添加
add_index :audits, [:auditable_type, :auditable_id]
add_index :audits, [:associated_type, :associated_id]
add_index :audits, [:user_id, :user_type]
add_index :audits, :created_at
add_index :audits, :request_uuid
```

### 5.2 异步配置

| 场景 | 建议 |
|------|------|
| 写入频繁的业务表 | 启用异步写入，避免阻塞主流程 |
| 对审计实时性要求高 | 保持同步写入 |
| 审计表数据量已超 1000 万行 | 考虑分区表或归档 |

### 5.3 批量操作注意

`update_all` / `delete_all` 不会触发审计。如需审计批量操作，应改为逐条更新或使用 `audited` 提供的批量接口：

```ruby
Order.where(status: 'pending').each do |order|
  order.update!(status: 'cancelled')
end
```

---

## 六、归档策略建议

### 6.1 保留周期

| 业务类型 | 建议保留周期 |
|----------|--------------|
| 一般业务系统 | 12 个月 |
| 金融/合规要求 | 36 个月或按监管要求 |
| 内部调试用途 | 6 个月 |

### 6.2 清理频率

建议每月执行一次归档任务：

```ruby
# lib/tasks/audit_archive.rake
namespace :audited do
  desc "归档 6 个月前的审计日志"
  task archive: :environment do
    cutoff = 6.months.ago
    old_audits = Audited.audit_class.where("created_at < ?", cutoff)
    
    # 导出到归档表或文件存储
    old_audits.find_in_batches do |batch|
      # 写入归档存储
      # 然后删除原记录
      Audited.audit_class.where(id: batch.map(&:id)).delete_all
    end
  end
end
```

### 6.3 归档存储方案

- 导出为 CSV / JSON 文件存入对象存储（如 S3）
- 迁移到独立的归档数据库
- 使用数据仓库（如 BigQuery）做长期留存

---

## 七、置信度门控

当遇到以下情况时，本 Skill 会输出 `[需核实:字段]` 占位符，而非编造信息：

| 场景 | 输出示例 |
|------|----------|
| 不确定某个 Rails 版本是否兼容 | `[需核实:audited gem 与 Rails 7.1 的兼容性]` |
| 不确定某个数据库的序列化格式 | `[需核实:PostgreSQL 中 audited_changes 的存储格式]` |
| 不确定某个回调是否触发审计 | `[需核实:touch 方法是否触发审计记录]` |
| 不确定自定义配置的准确写法 | `[需核实:audited_custom_fields 的准确 API]` |

遇到此类情况时，请查阅 [audited 官方文档](https://github.com/collectiveidea/audited) 确认。

---

## 八、错误码体系

| 错误码 | 现象 | 可能原因 | 修正步骤 |
|--------|------|----------|----------|
| `AUD-001` | 模型启用后无审计记录 | 迁移未执行 / gem 未加载 | 执行 `rails db:migrate`；确认 `bundle install` 完成 |
| `AUD-002` | `audits` 表不存在 | 未生成迁移文件 | 执行 `rails generate audited:install` 后迁移 |
| `AUD-003` | 操作者信息为空 | 未配置 `current_user` 来源 | 在 ApplicationController 中配置 `audit_current_user_method` |
| `AUD-004` | 关联对象变更未记录 | 未配置 `associated_with` | 在模型中添加关联追踪配置 |
| `AUD-005` | 异步模式下查询不到刚写入的审计 | 异步任务尚未执行 | 检查队列状态；或临时切换为同步模式 |
| `AUD-006` | `audited_changes` 为 `nil` | 使用了 `update_all` 等批量操作 | 改为逐条更新 |
| `AUD-007` | 自定义字段未出现在审计记录中 | 方法名拼写错误或返回 `nil` | 检查 `audited_custom_fields` 中声明的方法是否正确定义 |

---

## 九、FAQ 与反模式对照

### 9.1 常见坑

| 坑 | 反模式示例 | 正确做法 |
|----|------------|----------|
| 审计所有字段导致日志膨胀 | `acts_as_audited` 不加任何参数 | 使用 `only:` 限定关键字段 |
| 在回调中手动修改审计记录 | `after_save { audits.create!(...) }` | 依赖 gem 自动处理，不要手动干预 |
| 忽略异步模式的延迟 | 异步写入后立即查询并依赖结果 | 确认业务是否接受短暂延迟，否则用同步 |
| 不建索引直接上生产 | 裸表无索引，查询越来越慢 | 按 5.1 节建议创建索引 |
| 从不清理历史数据 | 审计表无限增长 | 按 6.2 节设计归档任务 |

### 9.2 反模式对照表

| 反模式 | 问题 | 替代方案 |
|--------|------|----------|
| 用审计日志做数据恢复 | 审计只记录变更，不保存完整快照 | 使用数据库备份或事件溯源 |
| 审计日志中包含敏感字段（如密码） | 安全风险 | 用 `except:` 排除敏感字段 |
| 在循环中逐条启用/禁用审计 | 性能开销大 | 使用 `as_user` 块包裹批量操作 |
| 依赖审计日志排查所有问题 | 日志可能不完整（批量操作不记录） | 结合应用日志和数据库日志 |

---

## 十、渐进式披露路径

### 10.1 新手路径（首次使用）

1. 阅读「能力边界速查卡」确认适用性
2. 按「标准执行流程」步骤 1-3 完成基础接入
3. 使用「查询与检索示例」验证功能
4. 遇到问题对照「错误码体系」排查

### 10.2 进阶路径（已有基础，需优化）

1. 配置异步写入降低主库压力（步骤 4）
2. 设计数据归档策略（步骤 6）
3. 自定义审计字段与关联追踪
4. 结合 `audited` 的 `comment` 字段实现操作备注
5. 利用 `request_uuid` 实现请求级操作链路追踪

---

## 用户协议

**使用本 Skill 即表示您同意以下条款：**

1. **责任承担**：使用者自行承担使用本 Skill 的全部责任。因使用本 Skill 产生的任何直接或间接损失，作者不承担任何责任。
2. **禁止反向工程**：不得对本 Skill 进行反向工程、反编译、破解或试图获取源代码（除非适用法律允许）。
3. **合规使用**：使用者应确保使用方式符合当地法律法规及所在平台的服务条款。
4. **无担保声明**：本 Skill 按"现状"提供，不附带任何明示或暗示的担保，包括但不限于适销性、特定用途适用性和非侵权性。
5. **修改与分发**：允许修改和分发，但需保留原始版权声明，且不得使用作者名义进行推广。

<!-- user-agreement-injected -->

---

## 许可证（License）

### MIT License

Copyright (c) 2024 林默

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
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR
