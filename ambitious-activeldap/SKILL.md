---
slug: ambitious-activeldap
name: ambitious-activeldap
displayName: 目录数据转换 结构化输出 批量标注
description: 将ActiveLdap目录数据转为结构化JSON，支持批量处理与置信度标注。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: DataForge Studio
agent_created: true
trigger_words: ["ActiveLdap", "目录数据转换", "LDAP结构化", "批量处理", "置信度标注", "LDAP导出", "目录清洗"]
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# ActiveLdap 目录数据转换 Skill

## 一、能力边界（一页纸速查卡）

### 1.1 能做什么

| 能力项 | 说明 | 输出示例 |
|--------|------|----------|
| 目录数据读取 | 连接 ActiveLdap 服务，按 base DN 拉取条目 | 原始条目列表 |
| 字段映射 | 将 LDAP 属性名映射为业务字段名 | `cn` → `commonName` |
| 数据清洗 | 去除空值、统一日期格式、拆分多值属性 | `mail` 多值拆分为数组 |
| 置信度标注 | 对每个字段标注可信度（0.0 ~ 1.0） | `"confidence": 0.95` |
| 批量处理 | 支持分页拉取，自动处理超过单页限制的数据 | 多页合并输出 |
| 结构化输出 | 生成 JSON 文件，按时间戳命名 | `20250617_1430_people.json` |

### 1.2 不能做什么

- 不能修改 LDAP 服务器上的数据（只读操作）
- 不能自动识别 LDAP 服务器的认证方式（需手动配置）
- 不能处理非 LDAP 协议的数据源（如 SQL 数据库）
- 不能保证字段映射的语义正确性（需人工校验映射配置）
- 不能自动处理 LDAP 服务器不可用时的重试策略

### 1.3 适用对象

- 需要将 LDAP 用户数据导出为 JSON 供下游系统使用的开发人员
- 需要定期同步目录数据到数据仓库的运维工程师
- 需要审计目录数据完整性的安全审计人员

---

## 二、触发方式

### 2.1 触发词

| 触发词 | 场景说明 |
|--------|----------|
| ActiveLdap | 直接指定工具名称 |
| 目录数据转换 | 描述任务目标 |
| LDAP结构化 | 强调输出格式要求 |
| 批量处理 | 数据量超过单页限制 |
| 置信度标注 | 需要评估数据可信度 |
| LDAP导出 | 同义场景词 |
| 目录清洗 | 同义场景词 |

### 2.2 大白话场景映射

| 用户说 | 实际需求 | 本 Skill 动作 |
|--------|----------|---------------|
| "帮我把 LDAP 里的用户导出来" | 导出用户列表 | 执行查询 → 映射字段 → 输出 JSON |
| "这个目录数据有点乱，整理一下" | 清洗并结构化 | 字段清洗 → 置信度标注 → 输出 |
| "我要把 LDAP 数据同步到数仓" | 定期批量导出 | 分页拉取 → 合并输出 → 生成文件 |
| "看看这些数据靠不靠谱" | 评估数据质量 | 置信度计算 → 标注 → 输出报告 |

---

## 三、标准流程

### 3.1 前置条件

| 条件 | 要求 | 验证方式 |
|------|------|----------|
| 环境变量 | `LDAP_HOST`、`LDAP_BIND_DN`、`LDAP_PASSWORD` 已设置 | `echo $LDAP_HOST` |
| Python 环境 | Python 3.8+，已安装依赖 | `python --version` |
| 配置文件 | `mapping_config.json` 存在且格式正确 | `python -c "import json; json.load(open('mapping_config.json'))"` |
| 网络连通 | 目标 LDAP 服务器可达 | `nc -zv $LDAP_HOST 389` |

### 3.2 执行步骤

**步骤 1：初始化配置**

```bash
export LDAP_HOST="ldap.example.com"
export LDAP_BIND_DN="cn=admin,dc=example,dc=com"
export LDAP_PASSWORD="your_password"
```

**步骤 2：运行最小转换**

```bash
python main.py --base-dn "ou=people,dc=example,dc=com"
```

参数说明：

| 参数 | 必填 | 默认值 | 说明 |
|------|------|--------|------|
| `--base-dn` | 是 | 无 | 查询的基准 DN |
| `--page-size` | 否 | 500 | 每页拉取条数 |
| `--output-dir` | 否 | `./output` | 输出目录 |
| `--mapping` | 否 | `mapping_config.json` | 字段映射配置 |
| `--selftest` | 否 | 无 | 运行自检 |
| `--version` | 否 | 无 | 显示版本号 |

**步骤 3：检查输出**

```bash
ls ./output/
cat ./output/20250617_1430_people.json | python -m json.tool
```

### 3.3 输出规范

输出文件命名格式：`<timestamp>_<base_dn_suffix>.json`

- `timestamp`：格式 `YYYYMMDD_HHMM`
- `base_dn_suffix`：取 base DN 的最后一个 RDN 值，如 `ou=people` → `people`

输出 JSON 结构：

```json
{
  "meta": {
    "generated_at": "2025-06-17T14:30:00Z",
    "base_dn": "ou=people,dc=example,dc=com",
    "total_entries": 2,
    "page_size": 500
  },
  "entries": [
    {
      "dn": "uid=jdoe,ou=people,dc=example,dc=com",
      "fields": {
        "commonName": {
          "value": "John Doe",
          "confidence": 0.98
        },
        "email": {
          "value": "jdoe@example.com",
          "confidence": 0.95
        }
      }
    }
  ]
}
```

---

## 四、置信度门控

### 4.1 置信度计算规则

| 场景 | 置信度 | 说明 |
|------|--------|------|
| 字段值完整且格式正确 | 0.95 ~ 1.0 | 正常值 |
| 字段值存在但格式异常 | 0.70 ~ 0.85 | 如日期格式不标准 |
| 字段值为空 | 0.0 | 不输出该字段 |
| 字段值来自多值属性 | 0.85 | 取第一个值，标注多值 |
| 字段映射不确定 | 0.50 | 需人工确认 |

### 4.2 信息不足时的处理

当某个字段无法确定时，输出 `[需核实:字段名]` 占位符，**绝不编造数据**。

示例：

```json
{
  "fields": {
    "employeeId": {
      "value": "[需核实:employeeId]",
      "confidence": 0.0
    }
  }
}
```

---

## 五、错误码体系

| 错误码 | 错误描述 | 提示话术 | 修正步骤 |
|--------|----------|----------|----------|
| `E001` | LDAP 连接失败 | "无法连接到 LDAP 服务器，请检查 LDAP_HOST 和网络连通性" | 1. 检查网络；2. 验证主机名；3. 确认端口开放 |
| `E002` | 认证失败 | "LDAP 认证失败，请检查 LDAP_BIND_DN 和 LDAP_PASSWORD" | 1. 核对凭据；2. 确认账号权限 |
| `E003` | base DN 不存在 | "指定的 base DN 不存在，请检查 --base-dn 参数" | 1. 使用 ldapsearch 验证 DN |
| `E004` | 映射配置错误 | "mapping_config.json 格式错误或字段缺失" | 1. 校验 JSON 格式；2. 检查必填字段 |
| `E005` | 输出目录不可写 | "无法写入输出目录，请检查权限" | 1. 检查目录权限；2. 更换 --output-dir |
| `E006` | 分页超限 | "单页数据量超过服务器限制" | 1. 减小 --page-size；2. 启用分页游标 |

---

## 六、FAQ 反模式

### 6.1 常见坑

| 坑 | 反模式 | 正确做法 |
|----|--------|----------|
| 忽略分页 | 一次性拉取全部数据导致内存溢出 | 始终使用分页参数，默认 500 条/页 |
| 硬编码凭据 | 在代码中写死 LDAP 密码 | 使用环境变量或密钥管理服务 |
| 跳过清洗 | 直接输出原始 LDAP 属性名 | 先做字段映射和清洗 |
| 忽略置信度 | 所有字段一视同仁 | 对每个字段标注置信度 |
| 不校验输出 | 直接使用生成的文件 | 先检查 JSON 结构和字段完整性 |

### 6.2 反模式对照表

| 反模式 | 问题 | 替代方案 |
|--------|------|----------|
| 使用 `ldapsearch` 手动导出 | 无法自动化、无结构化输出 | 使用本 Skill 的批量处理 |
| 写一次性脚本处理 | 无法复用、无错误处理 | 使用本 Skill 的标准流程 |
| 手动修改输出文件 | 破坏数据一致性 | 修改映射配置后重新生成 |

---

## 七、渐进式披露

### 7.1 速查卡（新手路径）

1. 设置环境变量（3 个）
2. 运行 `python main.py --base-dn "ou=people,dc=example,dc=com"`
3. 查看 `./output/*.json`

### 7.2 进阶路径

1. **自定义字段映射**：编辑 `mapping_config.json`，示例：

```json
{
  "field_mappings": {
    "cn": "commonName",
    "mail": "email",
    "telephoneNumber": "phone"
  },
  "cleaning_rules": {
    "email": "lowercase",
    "phone": "strip_spaces"
  }
}
```

2. **调整置信度规则**：重写 `confidence_evaluator.py` 中的 `evaluate_field()` 函数

3. **集成到 CI/CD**：将转换命令封装为 Docker 镜像，通过 API 触发

4. **开发自定义输出格式**：继承 `OutputFormatter` 基类，实现 `format()` 方法

---

## 八、用户协议

<!-- user-agreement-injected -->

**使用本 Skill 即表示您同意以下条款：**

1. **责任承担**：使用者自行承担使用本 Skill 的全部责任。因使用本 Skill 导致的任何直接或间接损失，作者不承担任何责任。

2. **合法使用**：使用者应确保使用本 Skill 的行为符合相关法律法规及所在组织的政策要求。

3. **禁止反向工程**：未经授权，不得对本 Skill 进行反向工程、反编译、破解或试图获取源代码。

4. **数据安全**：使用者应自行负责处理数据的合规性，包括但不限于个人隐私数据的保护。

5. **免责声明**：本 Skill 按"现状"提供，不附带任何明示或暗示的保证。

---

## 九、许可证（License）

<!-- professional-license-embedded -->

### MIT License

Copyright (c) 2025 原创作者（自持版权）

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

*本 Skill 由 AI 辅助生成，仅供参考。使用前请阅读相关文档。*
