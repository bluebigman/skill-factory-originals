---
slug: data-backup-checklist
name: data-backup-checklist
displayName: 备份核查 完整性校验 风险预警
description: 备份清单核对、版本差异追踪、恢复演练评分与风险分级预警。
version: 2.0.0
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/data-backup-checklist
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: BackupGuardian
agent_created: true
trigger_words: ["data-backup-checklist", "备份检查", "备份核对", "备份完整性"]
---

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->


> 📜 **用户协议（User Agreement）**
> 1. 本 Skill 仅供学习与参考用途。使用本 Skill 产生的任何结果，由使用者自行承担全部责任；本 Skill 不提供任何明示或暗示的保证。
> 2. 涉及法律、财务、税务、投资、医疗等专业决策时，请务必咨询持证专业人士。
> 3. 本代码受版权法保护，未经授权复制、反向工程或商业利用将被追究法律责任。
<!-- user-agreement-injected -->


# 备份核查与风险预警 Skill

**一句话定位**：面向运维工程师与数据管理员的备份健康度体检工具，通过清单核对、版本差异追踪、恢复演练评分与风险分级预警，在 30 秒内定位备份链路的薄弱环节，输出可执行的整改建议。

## 快速开始 Quick Start

| 场景 Situation | 操作 Action | 预期结果 Result |
|---|---|---|
| 我有备份清单（txt/json/csv），想快速体检 | `python run.py --input backup_list.json --output report.md` | 生成 Markdown 格式核查报告，含完整性评分与风险等级 |
| 我想对比新旧两份备份清单的差异 | `python run.py --compare old.json new.json --output diff.md` | 生成差异报告，列出新增/删除/修改的备份项 |
| 我想验证工具自身功能是否正常 | `python run.py --selftest` | 执行内置自检，全部断言通过后退出码为 0 |

## 适用场景 When to Use

**推荐使用：**
- 每日/每周备份任务执行后，需要自动化核查备份清单的完整性
- 备份策略调整前后，需要对比版本差异以确认变更生效
- 季度/年度恢复演练后，需要对演练结果进行量化评分
- 备份系统告警时，需要快速定位风险等级并确定处理优先级

**不要使用：**
- 需要实时监控备份任务执行过程（应使用专门的监控系统）
- 需要执行实际的备份或恢复操作（本工具只做核查与评分）
- 需要处理 TB 级以上的超大清单（建议先拆分或使用数据库方案）

## 能力总览 Capabilities

| 能力 | 命令/参数 | 示例 |
|---|---|---|
| 备份清单解析 | `--input` 支持 txt/json/csv/xlsx | `python run.py --input backup.csv --output report.md` |
| 必填字段完整性核对 | 自动检查 filename/timestamp/size 字段 | 缺失字段在报告中标记为 `❌ 缺失` |
| 版本差异对比 | `--compare old.json new.json` | 输出新增/删除/修改三类差异明细 |
| 恢复演练评分 | 基于 5 项指标加权计算 0-100 分 | 评分 <60 分自动标记为高风险 |
| 风险分级预警 | 四级预警：低/中/高/严重 | 严重风险输出 `🔴 严重` 标记 |
| 多格式输出 | `--format markdown/json/text` | 支持自定义分隔符（`--separator`） |
| 演练模式 | `--dry-run` 只预览不写盘 | 输出将写入的路径与报告摘要 |
| 详细诊断 | `--verbose` 输出处理明细 | 显示每条记录的校验结果与决策依据 |
| 内置自检 | `--selftest` 验证核心功能 | 断言失败时退出码非 0 |

## 模块决策表 Decision Table

| 用户意图 | 模块/命令 | 读取指引 |
|---|---|---|
| 检查单个备份清单 | `--input` + `--output` | 查看「示例 Examples」第 1 条 |
| 对比两个版本 | `--compare` + `--output` | 查看「示例 Examples」第 2 条 |
| 生成 JSON 格式报告 | `--format json` | 查看「参数表 Parameter Table」 |
| 只预览不写盘 | `--dry-run` | 查看「最佳实践 Best Practices」 |
| 验证工具可用性 | `--selftest` | 查看「常见问题 Troubleshooting」第 3 条 |

## 示例 Examples

### 示例 1：基础核查（JSON 输入 → Markdown 报告）

```bash
python run.py --input backup_list.json --output report.md
```

**输入** `backup_list.json`：
```json
[
  {"filename": "db_20240101.sql", "timestamp": "2024-01-01 03:00:00", "size": 1048576, "checksum": "abc123", "backup_type": "full", "status": "success"},
  {"filename": "db_20240102.sql", "timestamp": "2024-01-02 03:00:00", "size": 2097152, "checksum": "def456", "backup_type": "incremental", "status": "success"}
]
```

**输出** `report.md`（节选）：
```markdown
# 备份核查报告
生成时间: 2024-01-03 12:00:00 UTC
备份项总数: 2 | 完整: 2 | 缺失字段: 0 | 完整率: 100.0%

## 风险等级: 🟢 低风险
```

### 示例 2：版本差异对比

```bash
python run.py --compare old.json new.json --output diff.md
```

**输出** `diff.md`（节选）：
```markdown
# 备份版本差异报告
新增: 1 项 | 删除: 0 项 | 修改: 1 项

## 新增
- db_20240103.sql (2024-01-03 03:00:00, 3145728 bytes)

## 修改
- db_20240102.sql: 大小 2097152 → 3145728
```

### 示例 3：CSV 输入 + 自定义分隔符文本输出

```bash
python run.py --input backup_list.csv --output report.txt --format text --separator "|"
```

**输出** `report.txt`：
```text
文件名|时间戳|大小|校验和|类型|状态
db_20240101.sql|2024-01-01 03:00:00|1048576|abc123|full|success
```

## 安装与配置 Installation

### 依赖要求

- Python 3.9+
- 可选依赖：`openpyxl`（用于 Excel 文件解析）

```bash
pip install openpyxl  # 可选，仅当需要解析 .xlsx 文件时
```

### 环境变量

| 变量名 | 用途 | 默认值 |
|---|---|---|
| `BACKUP_CHECKLIST_TIMEOUT` | 网络请求超时时间（秒） | 10 |
| `BACKUP_CHECKLIST_RETRIES` | 网络请求最大重试次数 | 3 |

### 文件格式支持

| 格式 | 扩展名 | 说明 |
|---|---|---|
| JSON | `.json` | 数组或对象数组 |
| CSV | `.csv` | 首行为表头，支持逗号/分号/制表符分隔 |
| 纯文本 | `.txt` | 每行一条记录，字段用逗号或制表符分隔 |
| Excel | `.xlsx` | 需要安装 openpyxl |

## 参数表 Parameter Table

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|---|---|---|---|---|
| `--input` | str | 条件必填* | 无 | 输入文件路径（与 `--compare` 二选一） |
| `--compare` | str | 条件必填* | 无 | 旧版本文件路径（与 `--input` 二选一） |
| `--output` | str | 否 | 无 | 输出文件路径（不指定则输出到 stdout） |
| `--format` | str | 否 | markdown | 输出格式：markdown/json/text |
| `--separator` | str | 否 | `,` | 文本输出格式的分隔符 |
| `--dry-run` | flag | 否 | False | 只预览不写盘 |
| `--verbose` | flag | 否 | False | 输出详细处理日志 |
| `--selftest` | flag | 否 | False | 运行内置自检 |

*注：`--input` 与 `--compare` 必须且只能指定一个。

## 常见问题 Troubleshooting

### 1. 报错 `文件编码不支持`

**现象**：读取文件时抛出 `UnicodeDecodeError`。

**原因**：文件编码不是 UTF-8，且未安装 `chardet` 库。

**解决办法**：
```bash
pip install chardet
# 或手动将文件转换为 UTF-8 编码
```

### 2. 报错 `openpyxl 未安装`

**现象**：解析 `.xlsx` 文件时提示缺少依赖。

**原因**：未安装可选依赖 `openpyxl`。

**解决办法**：
```bash
pip install openpyxl
```

### 3. `--selftest` 断言失败

**现象**：自检脚本返回非零退出码。

**原因**：核心功能异常或环境不兼容。

**解决办法**：
1. 检查 Python 版本是否为 3.9+
2. 确认 `openpyxl` 已安装（如需 Excel 支持）
3. 查看 stderr 输出中的具体失败断言

### 4. 报告中的评分与预期不符

**现象**：恢复演练评分低于/高于预期。

**原因**：评分权重或阈值设置与业务场景不匹配。

**解决办法**：查看「最佳实践」中的评分规则说明，根据实际需求调整 `--verbose` 输出中的明细。

## 最佳实践 Best Practices

### 评分规则说明

恢复演练评分基于以下 5 项指标加权计算：

| 指标 | 权重 | 说明 |
|---|---|---|
| 字段完整率 | 30% | 必填字段（filename/timestamp/size）的完整程度 |
| 时间新鲜度 | 25% | 最近备份时间与当前时间的间隔 |
| 大小合理性 | 20% | 备份文件大小是否在合理范围（非 0 且非异常大） |
| 类型多样性 | 15% | 是否包含 full/incremental 等多种备份类型 |
| 状态健康度 | 10% | 备份状态字段中 success 的比例 |

### 风险分级标准

| 等级 | 评分范围 | 建议动作 |
|---|---|---|
| 🟢 低风险 | 80-100 | 常规监控即可 |
| 🟡 中风险 | 60-79 | 检查缺失项，优化备份策略 |
| 🟠 高风险 | 40-59 | 立即排查失败项，考虑手动备份 |
| 🔴 严重 | 0-39 | 紧急处理，启动应急预案 |

### 安全提醒

- 备份清单可能包含敏感信息（如文件路径），生成报告后请注意权限管理
- 建议在 CI/CD 流水线中集成本工具，实现备份健康度的持续监控
- 定期（每月）运行 `--selftest` 确保工具自身功能正常

## 相关资源 Related

- [Python 官方文档](https://docs.python.org/3/)
- [openpyxl 文档](https://openpyxl.readthedocs.io/)
- [备份最佳实践指南](https://www.backup-guide.com/)

---

**版本历史**：v2.0.0 重构核心逻辑，新增 dry-run 模式与流式处理，优化编码兼容性。

## 许可证（License）

```text
MIT License

Copyright (c) {year} {holder}

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
