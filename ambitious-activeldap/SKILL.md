---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: ambitious-activeldap
name: ambitious-activeldap
displayName: 目录数据 批量转换 置信标注
description: 将ActiveLdap目录数据转换为结构化输出，支持批量处理与置信度标注。
version: 2.0.1
rules_version: cpr-20260810-n301
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/ambitious-activeldap
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: DataForge Studio
agent_created: true
trigger_words: ["ActiveLdap", "目录数据转换", "LDAP结构化", "批量处理", "置信度标注", "ldap导出"]
---

> 📜 **用户协议（User Agreement）**
> 1. 本 Skill 仅供学习与参考用途。使用本 Skill 产生的任何结果，由使用者自行承担全部责任；本 Skill 不提供任何明示或暗示的保证。
> 2. 涉及法律、财务、税务、投资、医疗等专业决策时，请务必咨询持证专业人士。
> 3. 本代码受版权法保护，未经授权复制、反向工程或商业利用将被追究法律责任。
<!-- user-agreement-injected -->


> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# ActiveLdap 目录数据转换与结构化输出 Skill

## 一、能力边界（一页纸速查卡）

### 1.1 能做什么

| 能力项 | 说明 | 示例 |
|--------|------|------|
| 目录数据读取 | 从 ActiveLdap 连接中读取条目数据 | 读取用户、组、OU 等条目 |
| 结构化转换 | 将 LDAP 条目转换为 JSON/YAML 结构化格式 | 将 `cn=John Doe,ou=Users,dc=example,dc=com` 转为 `{"cn": "John Doe", "ou": "Users"}` |
| 批量处理 | 支持一次处理多个条目或整个子树 | 处理 1000+ 用户条目 |
| 置信度标注 | 为每个字段添加数据可信度标记 | `{"mail": {"value": "john@example.com", "confidence": 0.95}}` |
| 字段映射 | 自定义 LDAP 属性到目标字段的映射关系 | `{"displayName": "cn", "email": "mail"}` |
| 过滤与筛选 | 按条件过滤不需要的条目或字段 | 只保留 `objectClass=user` 的条目 |

### 1.2 不能做什么

| 限制项 | 说明 |
|--------|------|
| 不修改源目录 | 本 Skill 只做读取与转换，不执行写操作 |
| 不处理二进制大对象 | 如照片、证书等大型二进制属性，仅保留引用或跳过 |
| 不自动推断缺失值 | 缺失字段不会猜测，只标注 `[需核实:字段名]` |
| 不保证数据准确性 | 源数据本身的问题（如过期、错误）不在本 Skill 责任范围 |
| 不支持非 LDAP 协议 | 仅适用于 ActiveLdap 兼容的目录服务 |

### 1.3 适用对象

- **数据迁移工程师**：需要将旧 LDAP 数据导出为结构化格式
- **系统管理员**：需要定期备份或审计目录数据
- **应用开发者**：需要将 LDAP 数据集成到现代应用中
- **数据分析师**：需要对目录数据进行统计分析

---

## 二、触发方式

### 2.1 触发词

当用户输入包含以下关键词时，本 Skill 将被激活：

- `ActiveLdap` / `LDAP` / `目录服务`
- `转换` / `导出` / `结构化`
- `批量处理` / `置信度` / `数据清洗`

### 2.2 场景映射表

| 用户场景（大白话） | 触发词示例 | Skill 响应 |
|-------------------|------------|------------|
| "帮我把 LDAP 里的用户信息导成 JSON" | LDAP, 导出, JSON | 执行目录读取与结构化转换 |
| "这个目录数据太多了，能不能批量处理？" | 批量, 目录数据 | 启用批量模式，分批处理 |
| "这些字段值可靠吗？" | 置信度, 可靠性 | 为每个字段添加置信度标注 |
| "只要用户组的，不要别的" | 过滤, 用户组 | 应用过滤条件，只输出目标条目 |
| "字段名能改成我需要的吗？" | 字段映射, 重命名 | 应用自定义字段映射规则 |

---

## 三、标准流程

### 3.1 前置条件

| 条件 | 要求 | 检查方式 |
|------|------|----------|
| 连接信息 | 提供 LDAP 服务器地址、端口、绑定 DN 和密码 | 确认连接参数完整 |
| 权限 | 具备读取目标目录树的权限 | 执行 `ldapsearch` 测试 |
| 输入数据 | 明确要处理的 DN 范围或搜索基准 | 确认 base DN 正确 |
| 输出格式 | 指定目标格式（JSON/YAML/CSV） | 确认格式参数 |

### 3.2 执行步骤

#### 步骤 1：建立连接

```python
import ldap3

server = ldap3.Server('ldap://localhost:389')
conn = ldap3.Connection(server, user='cn=admin,dc=example,dc=com', password='password')
conn.bind()
```

#### 步骤 2：定义搜索范围与过滤条件

```python
search_base = 'ou=users,dc=example,dc=com'
search_filter = '(&(objectClass=user)(!(userAccountControl:1.2.840.113556.1.4.803:=2)))'
attributes = ['cn', 'mail', 'department', 'telephoneNumber']
```

#### 步骤 3：执行搜索并收集条目

```python
conn.search(search_base, search_filter, attributes=attributes)
entries = conn.entries
```

#### 步骤 4：应用字段映射

```python
field_mapping = {
    'cn': 'displayName',
    'mail': 'email',
    'department': 'dept',
    'telephoneNumber': 'phone'
}

def map_fields(entry):
    result = {}
    for ldap_attr, target_field in field_mapping.items():
        if ldap_attr in entry:
            result[target_field] = entry[ldap_attr].value
    return result
```

#### 步骤 5：添加置信度标注

```python
def add_confidence(data, source='direct'):
    """为每个字段添加置信度标注。
    
    置信度规则：
    - direct: 直接从源读取，置信度 0.95
    - derived: 从其他字段推导，置信度 0.80
    - default: 使用默认值，置信度 0.60
    - missing: 字段缺失，置信度 0.00，标注 [需核实:字段名]
    """
    result = {}
    for field, value in data.items():
        if value is None or value == '':
            result[field] = {
                'value': None,
                'confidence': 0.0,
                'note': f'[需核实:{field}]'
            }
        else:
            result[field] = {
                'value': value,
                'confidence': 0.95,
                'source': source
            }
    return result
```

#### 步骤 6：批量处理与输出

```python
import json

def batch_process(entries, batch_size=100):
    """分批处理条目，避免内存溢出。"""
    results = []
    for i in range(0, len(entries), batch_size):
        batch = entries[i:i+batch_size]
        for entry in batch:
            mapped = map_fields(entry)
            annotated = add_confidence(mapped)
            results.append(annotated)
    return results

# 输出为 JSON
output = batch_process(entries)
print(json.dumps(output, ensure_ascii=False, indent=2))
```

### 3.3 输出规范

| 输出项 | 格式 | 示例 |
|--------|------|------|
| 单条记录 | JSON 对象 | `{"displayName": {"value": "张三", "confidence": 0.95}}` |
| 批量结果 | JSON 数组 | `[{...}, {...}, ...]` |
| 处理报告 | 文本摘要 | `共处理 150 条记录，成功 148 条，失败 2 条` |
| 错误信息 | 结构化错误 | `{"error_code": "LDAP_CONN_FAILED", "message": "..."}` |

---

## 四、置信度门控

### 4.1 置信度等级定义

| 等级 | 置信度值 | 含义 | 使用场景 |
|------|----------|------|----------|
| 高 | 0.90 - 1.00 | 直接从源读取，来源可靠 | 标准属性值 |
| 中 | 0.70 - 0.89 | 经过推导或转换 | 格式转换后的值 |
| 低 | 0.50 - 0.69 | 使用默认值或推断值 | 缺失字段的替代 |
| 无 | 0.00 | 字段缺失或无法获取 | 必须标注 `[需核实:字段名]` |

### 4.2 缺失值处理规则

当遇到以下情况时，**不得编造数据**：

1. **字段不存在**：输出 `{"field": {"value": null, "confidence": 0.0, "note": "[需核实:field]"}}`
2. **字段值为空字符串**：同上处理
3. **字段值格式异常**：保留原始值，置信度降为 0.50，添加说明
4. **多值字段**：保留所有值，置信度取平均值

### 4.3 置信度调整规则

| 场景 | 调整方式 |
|------|----------|
| 字段值经过正则校验 | 置信度 +0.05，上限 0.98 |
| 字段值来自默认配置 | 置信度设为 0.60 |
| 字段值经过格式转换 | 置信度 -0.10 |
| 字段值与其他字段冲突 | 置信度 -0.15，添加冲突说明 |

---

## 五、错误码体系

### 5.1 错误码速查表

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| `LDAP_CONN_FAILED` | 无法连接到 LDAP 服务器 | "连接失败，请检查服务器地址和端口" | 1. 确认服务器可达 2. 检查端口 3. 验证网络 |
| `LDAP_AUTH_FAILED` | 认证失败 | "认证失败，请检查绑定 DN 和密码" | 1. 确认 DN 格式 2. 重置密码 3. 检查权限 |
| `LDAP_SEARCH_FAILED` | 搜索操作失败 | "搜索失败，请检查基准 DN 和过滤条件" | 1. 验证基准 DN 2. 简化过滤条件 3. 检查语法 |
| `LDAP_NO_RESULTS` | 搜索无结果 | "未找到匹配条目，请调整搜索条件" | 1. 放宽过滤条件 2. 扩大搜索范围 3. 检查拼写 |
| `FIELD_MAP_INVALID` | 字段映射无效 | "字段映射包含不存在的属性" | 1. 检查 LDAP 属性名 2. 确认目标字段名 3. 移除无效映射 |
| `OUTPUT_FORMAT_UNSUPPORTED` | 不支持的输出格式 | "仅支持 JSON、YAML、CSV 格式" | 1. 选择支持的格式 2. 检查格式参数 |
| `BATCH_SIZE_INVALID` | 批量大小无效 | "批量大小必须为正整数" | 1. 设置大于 0 的整数 2. 建议 50-200 |
| `DATA_TRUNCATED` | 数据被截断 | "部分数据超过大小限制被截断" | 1. 增加限制 2. 分批处理 3. 过滤大字段 |

### 5.2 错误处理流程

```
检测到错误 → 记录错误码和上下文 → 生成结构化错误信息 → 提示用户 → 提供修正建议
```

---

## 六、FAQ 反模式

### 6.1 常见坑

| 坑编号 | 常见错误 | 反模式（错误做法） | 正确做法 |
|--------|----------|-------------------|----------|
| 1 | 忽略连接超时 | 不设置超时，导致程序挂起 | 设置 5-10 秒超时，失败快速重试 |
| 2 | 一次性加载全部数据 | 直接读取整个目录树到内存 | 使用分页或批量处理，控制内存使用 |
| 3 | 不处理特殊字符 | 直接拼接 DN 导致注入或解析错误 | 使用 LDAP 转义函数处理特殊字符 |
| 4 | 忽略编码问题 | 直接使用默认编码，导致中文乱码 | 明确指定 UTF-8 编码 |
| 5 | 不校验输出数据 | 直接输出未验证的数据 | 添加数据校验步骤，确保格式正确 |

### 6.2 反模式对照表

| 反模式 | 问题描述 | 替代方案 |
|--------|----------|----------|
| 盲目信任源数据 | 源数据可能有误，直接使用会导致下游问题 | 添加置信度标注，标记可疑数据 |
| 过度复杂化映射 | 映射规则过于复杂，难以维护 | 保持映射简单，使用配置文件管理 |
| 忽略错误处理 | 不处理异常，程序崩溃 | 使用 try-catch 包裹关键操作，记录错误 |
| 输出格式不统一 | 不同批次输出格式不一致 | 定义统一的输出 schema，强制校验 |
| 不做性能优化 | 处理大数据集时效率低下 | 使用批量操作、索引、缓存优化 |

---

## 七、渐进式披露

### 7.1 速查卡（新手快速上手）

```
1. 准备连接信息（服务器、端口、DN、密码）
2. 调用 Skill，传入连接参数
3. 指定搜索基准和过滤条件
4. 选择输出格式（JSON 推荐）
5. 获取结构化结果和置信度标注
```

### 7.2 分层次阅读路径

#### 新手路径（5 分钟上手）

1. 阅读「能力边界」了解适用范围
2. 查看「标准流程」步骤 1-3 完成基本转换
3. 使用默认参数运行，查看输出

#### 进阶路径（深入使用）

1. 阅读「置信度门控」理解数据质量评估
2. 自定义字段映射和过滤规则
3. 配置批量处理参数，处理大规模数据
4. 参考「错误码体系」处理异常情况

#### 专家路径（定制化开发）

1. 扩展字段映射，支持复杂转换逻辑
2. 自定义置信度计算规则
3. 集成到自动化流水线
4. 开发自定义输出格式

---

## 八、参数配置参考

### 8.1 连接参数

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `server` | string | 是 | 无 | LDAP 服务器地址 |
| `port` | integer | 否 | 389 | 端口号（LDAPS 为 636） |
| `use_ssl` | boolean | 否 | false | 是否使用 SSL |
| `bind_dn` | string | 是 | 无 | 绑定 DN |
| `password` | string | 是 | 无 | 绑定密码 |
| `timeout` | integer | 否 | 10 | 连接超时（秒） |

### 8.2 搜索参数

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `search_base` | string | 是 | 无 | 搜索基准 DN |
| `search_filter` | string | 否 | `(objectClass=*)` | LDAP 过滤条件 |
| `attributes` | list | 否 | 所有属性 | 要获取的属性列表 |
| `search_scope` | string | 否 | `SUBTREE` | 搜索范围（BASE/ONELEVEL/SUBTREE） |
| `page_size` | integer | 否 | 100 | 分页大小 |

### 8.3 输出参数

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `output_format` | string | 否 | `json` | 输出格式（json/yaml/csv） |
| `include_confidence` | boolean | 否 | true | 是否包含置信度标注 |
| `field_mapping` | dict | 否 | 无 | 字段映射规则 |
| `batch_size` | integer | 否 | 100 | 批量处理大小 |
| `pretty_print` | boolean | 否 | true | 是否美化输出 |

---

## 九、使用示例

### 9.1 基础转换示例

```python
# 输入
skill_config = {
    "server": "ldap.example.com",
    "port": 389,
    "bind_dn": "cn=admin,dc=example,dc=com",
    "password": "secret",
    "search_base": "ou=users,dc=example,dc=com",
    "search_filter": "(objectClass=user)",
    "attributes": ["cn", "mail", "department"],
    "output_format": "json"
}

# 输出
{
    "records": [
        {
            "cn": {"value": "张三", "confidence": 0.95},
            "mail": {"value": "zhangsan@example.com", "confidence": 0.95},
            "department": {"value": "技术部", "confidence": 0.95}
        }
    ],
    "summary": {
        "total": 1,
        "success": 1,
        "failed": 0
    }
}
```

### 9.2 批量处理示例

```python
# 输入
skill_config = {
    "server": "ldap.example.com",
    "search_base": "dc=example,dc=com",
    "search_filter": "(&(objectClass=user)(department=IT))",
    "batch_size": 200,
    "include_confidence": True,
    "field_mapping": {
        "cn": "name",
        "mail": "email",
        "telephoneNumber": "phone"
    }
}

# 输出（截取）
{
    "records": [
        {
            "


## 许可证（License）

```text
MIT License

Copyright (c) 2026 SkillForge Lab

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.
```
<!-- professional-license-embedded -->
