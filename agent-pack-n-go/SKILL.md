---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: agent-pack-n-go
name: agent-pack-n-go
displayName: 智能体迁移 配置打包 设备换机
description: 将智能体配置、记忆与技能打包迁移至新设备，约25分钟完成。
version: 1.0.3
rules_version: cpr-20260812-n376
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/agent-pack-n-go
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: AgentForge Studio
agent_created: true
trigger_words: ["克隆智能体", "迁移配置", "打包技能", "设备迁移", "换机搬家", "环境复制"]
---

> 📜 **用户协议（User Agreement）**
> 1. 本 Skill 仅供学习与参考用途。使用本 Skill 产生的任何结果，由使用者自行承担全部责任；本 Skill 不提供任何明示或暗示的保证。
> 2. 涉及法律、财务、税务、投资、医疗等专业决策时，请务必咨询持证专业人士。
> 3. 本代码受版权法保护，未经授权复制、反向工程或商业利用将被追究法律责任。
<!-- user-agreement-injected -->


> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# agent-pack-n-go — 智能体迁移打包工具

## 一、能力边界（一页纸速查卡）

### 1.1 能做什么

| 能力项 | 说明 | 约束条件 |
|--------|------|----------|
| 配置打包 | 将 `~/.agent-core/` 下的配置目录压缩为 tar.gz 迁移包 | 源目录必须存在且可读 |
| 记忆库迁移 | 将记忆向量库/索引文件一并打包 | 需显式指定 `--include-memory` |
| 技能包迁移 | 将已注册的技能插件目录打包 | 需显式指定 `--include-skills` |
| 远程推送 | 通过 SSH 或共享目录直接推送到目标设备 | 需网络连通或共享挂载 |
| 目标还原 | 在目标设备解包、校验、写入配置 | 目标设备需安装 ≥1.0.0 版本工具 |
| 旧配置备份 | 覆盖前自动备份至 `{target}.bak-{timestamp}` | 目标路径已存在旧配置时触发 |
| 连通性自检 | 还原后自动验证配置加载、记忆读取、技能调用 | 三项全部通过才算迁移成功 |

### 1.2 不能做什么

- **不能**跨版本迁移（源设备 agent-core 版本与目标设备不兼容时，工具会拒绝执行）。
- **不能**迁移系统级环境变量、PATH 设置或操作系统依赖。
- **不能**迁移未授权第三方技能（需技能本身允许再分发）。
- **不能**在无网络且无文件传输通道时自动完成迁移（需人工介入拷贝）。
- **不能**保证迁移后所有技能 100% 功能一致（依赖外部 API 密钥的技能需重新配置）。

### 1.3 适用对象

- 需要更换开发机/工作站的 AI Agent 使用者
- 需要在多台设备间同步智能体环境的开发者
- 需要为团队批量部署统一智能体配置的运维人员

---

## 二、触发方式

### 2.1 触发词

当用户表达以下意图时，本技能被激活：

| 触发词 | 场景示例 |
|--------|----------|
| 克隆智能体 | "帮我把这台机器的智能体克隆到新电脑上" |
| 迁移配置 | "我要迁移 agent 配置到服务器" |
| 打包技能 | "把已安装的技能打包带走" |
| 设备迁移 | "换新机器了，怎么把环境搬过去" |
| 换机搬家 | "新笔记本到了，老环境怎么弄过来" |
| 环境复制 | "想复制一份一模一样的 agent 环境" |

### 2.2 命令行入口

```bash
agent-pack-n-go [命令] [选项]
```

| 命令/选项 | 说明 | 示例 |
|-----------|------|------|
| `--source <路径>` | 指定源配置目录 | `--source ~/.agent-core` |
| `--target <路径>` | 指定目标路径（打包时输出路径，还原时安装路径） | `--target /tmp/migration.tar.gz` |
| `--restore <包路径>` | 还原模式，从迁移包恢复 | `--restore /tmp/migration.tar.gz` |
| `--include-memory` | 打包时包含记忆库 | `--include-memory` |
| `--include-skills` | 打包时包含技能包 | `--include-skills` |
| `--selftest` | 运行自检 | `--selftest` |
| `--version` | 显示版本号 | `--version` |

---

## 三、标准流程

### 3.1 前置条件检查

在开始迁移前，逐项确认以下条件：

| 序号 | 检查项 | 检查方法 | 不通过时的处理 |
|------|--------|----------|----------------|
| 1 | 源配置目录存在 | `ls ~/.agent-core/` | 确认路径是否正确，或使用 `--source` 指定实际路径 |
| 2 | 目标设备已安装工具 | `agent-pack-n-go --version` | 在目标设备安装 ≥1.0.0 版本 |
| 3 | 网络/传输通道可用 | `ping <目标IP>` 或确认 U 盘已挂载 | 准备离线传输方案（U 盘、移动硬盘） |
| 4 | 目标磁盘空间充足 | `df -h` 确认剩余空间 ≥ 源目录 2 倍 | 清理磁盘或扩容后再执行 |
| 5 | 源配置目录可读 | `cat ~/.agent-core/config.yaml` | 检查文件权限 |

### 3.2 执行步骤（源设备打包）

**步骤 1：读取源路径**

```bash
# 显式指定源路径
agent-pack-n-go --source ~/.agent-core --target /tmp/migration.tar.gz

# 或进入交互模式（不带 --source 参数时）
agent-pack-n-go
# 程序会提示：请输入源配置路径（默认 ~/.agent-core）：
```

**步骤 2：确认打包范围**

根据需求选择是否包含记忆库和技能包：

```bash
# 仅打包配置（最小包）
agent-pack-n-go --source ~/.agent-core --target /tmp/migration.tar.gz

# 打包配置 + 记忆库
agent-pack-n-go --source ~/.agent-core --target /tmp/migration.tar.gz --include-memory

# 打包配置 + 记忆库 + 技能包（完整迁移）
agent-pack-n-go --source ~/.agent-core --target /tmp/migration.tar.gz --include-memory --include-skills
```

**步骤 3：查看源配置摘要**

打包前工具会输出以下摘要信息：

```
源配置摘要：
  目录大小：  128.5 MB
  文件数量：  1,247
  技能数量：  8
  记忆库大小： 86.2 MB
```

**步骤 4：生成 manifest.json**

工具自动生成 `manifest.json`，包含以下字段：

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `tool_version` | string | 打包工具版本号 |
| `source_path` | string | 源配置目录路径 |
| `created_at` | string | 打包时间（ISO 8601 格式） |
| `file_count` | integer | 文件总数 |
| `total_size` | integer | 总大小（字节） |
| `has_memory` | boolean | 是否包含记忆库 |
| `has_skills` | boolean | 是否包含技能包 |
| `checksum` | string | 打包内容的 SHA-256 校验和 |

**步骤 5：生成迁移包**

输出文件命名为 `agent-migration-{timestamp}.tar.gz`，其中 `{timestamp}` 为打包时刻的 Unix 时间戳。

### 3.3 执行步骤（传输）

**方式 A：自动推送（SSH 或共享目录）**

```bash
# 工具检测到目标设备可达时，自动推送
agent-pack-n-go --source ~/.agent-core --target /tmp/migration.tar.gz --push-to user@192.168.1.100:/tmp/
```

**方式 B：手动拷贝**

```bash
# 工具提示手动拷贝
scp /tmp/migration.tar.gz user@new-device:/tmp/
```

### 3.4 执行步骤（目标设备还原）

**步骤 1：执行还原命令**

```bash
agent-pack-n-go --restore /tmp/migration.tar.gz --target ~/.agent-core
```

**步骤 2：还原脚本自动完成以下操作**

| 序号 | 操作 | 说明 |
|------|------|------|
| 1 | 解压 | 解包 tar.gz 至临时目录 |
| 2 | 校验 manifest | 核对文件数、大小、校验和 |
| 3 | 备份旧配置 | 若目标路径已存在，备份至 `{target}.bak-{timestamp}` |
| 4 | 写入配置 | 将新配置写入目标路径 |
| 5 | 导入记忆库 | 若包含记忆库，导入至目标位置 |
| 6 | 注册技能包 | 若包含技能包，注册至目标环境 |

**步骤 3：连通性测试**

还原完成后自动执行三项验证：

```bash
# 1. 加载配置
agent-pack-n-go --selftest --check-config

# 2. 读取一条记忆
agent-pack-n-go --selftest --check-memory

# 3. 调用一个技能
agent-pack-n-go --selftest --check-skill
```

**步骤 4：查看迁移报告**

```
迁移报告
========
源设备：    192.168.1.10
目标设备：  192.168.1.100
迁移包：    agent-migration-1723456789.tar.gz
文件数：    1,247
总大小：    128.5 MB
配置加载：  ✅ 通过
记忆读取：  ✅ 通过
技能调用：  ✅ 通过
耗时：      23 分钟
状态：      迁移成功
```

### 3.5 输出规范

- 迁移包命名：`agent-migration-{timestamp}.tar.gz`
- 备份目录命名：`{target}.bak-{timestamp}`
- 迁移报告格式：见步骤 4 示例
- 所有时间戳使用 Unix 时间戳（秒级）

---

## 四、置信度门控

### 4.1 信息不足时的处理

当工具在执行过程中遇到信息缺失或不确定的情况时，使用以下占位符标记，**不编造数据**：

| 场景 | 占位符 | 示例 |
|------|--------|------|
| 源目录大小未知 | `[需核实:源目录大小]` | 摘要输出：`目录大小：[需核实:源目录大小]` |
| 技能数量不确定 | `[需核实:技能数量]` | 摘要输出：`技能数量：[需核实:技能数量]` |
| 目标设备路径不确定 | `[需核实:目标路径]` | 推送失败提示：`目标路径 [需核实:目标路径] 不可达` |
| 记忆库版本不匹配 | `[需核实:记忆库版本]` | 还原警告：`记忆库版本 [需核实:记忆库版本] 与当前工具不兼容` |

### 4.2 门控规则

- 当源目录存在但无法读取大小时，输出 `[需核实:源目录大小]`，不猜测。
- 当目标设备无法连接时，输出 `[需核实:目标设备连通性]`，不假设可达。
- 当技能包包含未知依赖时，输出 `[需核实:技能依赖]`，不自动安装。

---

## 五、错误码体系

### 5.1 常见错误与处理

| 错误码 | 错误描述 | 提示话术 | 修正步骤 |
|--------|----------|----------|----------|
| `E001` | 源配置目录不存在 | `错误：源目录 [路径] 不存在或不可读` | 1. 检查路径拼写；2. 使用 `--source` 指定正确路径；3. 确认目录权限 |
| `E002` | 目标设备工具版本过低 | `错误：目标设备 agent-pack-n-go 版本低于 1.0.0` | 1. 在目标设备升级工具；2. 重新执行还原 |
| `E003` | 磁盘空间不足 | `错误：目标磁盘剩余空间不足（需 ≥ 源目录 2 倍）` | 1. 清理磁盘；2. 扩容；3. 重新执行 |
| `E004` | 网络连接失败 | `错误：无法连接目标设备 [IP]` | 1. 检查网络；2. 确认 SSH 服务；3. 改用 U 盘传输 |
| `E005` | manifest 校验失败 | `错误：迁移包校验失败，文件可能已损坏` | 1. 重新打包；2. 重新传输；3. 检查传输完整性 |
| `E006` | 目标路径写入失败 | `错误：无法写入目标路径 [路径]` | 1. 检查目录权限；2. 确认目标路径可写；3. 手动创建父目录 |
| `E007` | 记忆库导入失败 | `错误：记忆库导入失败，版本可能不兼容` | 1. 检查记忆库格式；2. 确认目标工具版本；3. 尝试仅迁移配置 |
| `E008` | 技能注册失败 | `错误：技能 [名称] 注册失败，依赖缺失` | 1. 检查技能依赖；2. 手动安装依赖；3. 重新注册 |
| `E009` | 连通性测试失败 | `错误：迁移后验证未通过（配置/记忆/技能）` | 1. 查看详细日志；2. 定位失败项；3. 手动修复后重试 |
| `E010` | 备份失败 | `错误：旧配置备份失败，已中止覆盖操作` | 1. 检查目标路径权限；2. 手动备份旧配置；3. 重新执行 |

### 5.2 错误处理原则

- 所有错误均输出到 stderr，退出码非零。
- 错误信息包含错误码、具体描述和修正建议。
- 遇到 `E010` 时，工具会中止操作，不会覆盖旧配置。

---

## 六、FAQ 反模式

### 6.1 常见坑与反模式对照

| 常见坑 | 反模式（错误做法） | 正确做法 |
|--------|-------------------|----------|
| 打包时忘记包含记忆库 | 直接执行 `agent-pack-n-go --source ~/.agent-core --target /tmp/migration.tar.gz`，不带 `--include-memory` | 确认需要迁移记忆库时，显式添加 `--include-memory` 参数 |
| 目标设备磁盘空间不足 | 忽略磁盘检查直接还原，导致解压失败 | 还原前执行 `df -h` 确认空间 ≥ 源目录 2 倍 |
| 技能依赖未迁移 | 只打包技能目录，不检查依赖 | 打包前检查技能依赖清单，确认目标设备已安装所需依赖 |
| 旧配置未备份 | 直接覆盖目标路径，导致旧配置丢失 | 工具会自动备份至 `{target}.bak-{timestamp}`，但建议手动再备份一次 |
| 迁移后不验证 | 还原完成后直接使用，不运行连通性测试 | 执行 `--selftest` 验证配置、记忆、技能三项均通过 |
| 跨版本迁移 | 源设备版本 2.x，目标设备版本 1.x，直接迁移 | 先升级目标设备工具至与源设备兼容的版本 |
| 忽略 manifest 校验 | 手动解压迁移包，跳过校验 | 始终使用 `--restore` 命令还原，让工具自动校验 |

### 6.2 反模式自查清单

- [ ] 是否确认了源目录路径正确？
- [ ] 是否确认了目标设备工具版本 ≥ 1.0.0？
- [ ] 是否确认了磁盘空间充足？
- [ ] 是否确认了记忆库和技能包的迁移范围？
- [ ] 是否在还原后运行了连通性测试？

---

## 七、渐进式披露

### 7.1 速查卡（30 秒上手）

```bash
# 打包（完整迁移）
agent-pack-n-go --source ~/.agent-core --target /tmp/migration.tar.gz --include-memory --include-skills

# 传输
scp /tmp/migration.tar.gz user@new-device:/tmp/

# 还原
agent-pack-n-go --restore /tmp/migration.tar.gz --target ~/.agent-core
```

### 7.2 新手路径（首次使用）

1. 阅读「能力边界」了解工具能做什么。
2. 按「标准流程」的步骤 3.2 执行打包。
3. 按步骤 3.3 选择传输方式。
4. 按步骤 3.4 执行还原。
5. 查看步骤 3.4 的迁移报告确认成功。

### 7.3 进阶路径（深度使用）

1. 阅读「错误码体系」了解常见问题处理。
2. 阅读「FAQ 反模式」避免常见坑。
3. 使用 `--selftest` 定期验证环境完整性。
4. 结合 `--include-memory` 和 `--include-skills` 定制迁移范围。
5. 探索交互模式（不带 `--source` 参数）获取引导式体验。

---

## 八、使用示例

### 8.1 完整迁移示例

```bash
# 源设备（192.168.1.10）
agent-pack-n-go --source ~/.agent-core --target /tmp/migration.tar.gz --include-memory --include-skills

# 输出摘要
源配置摘要：
  目录大小：  128.5 MB
  文件数量：  1,247
  技能数量：  8
  记忆库大小： 86.2 MB

# 传输到目标设备
scp /tmp/migration.tar.gz user@192.168.1.100:/tmp/

# 目标设备（192.168.1.100）
agent-pack-n-go --restore /tmp/migration.tar.gz --target ~/.agent-core

# 迁移报告
迁移报告
========
源设备：    192.168.1.10
目标设备：  192.168.1.100
迁移包：    agent-migration-1723456789.tar.gz
文件数：    1,247
总大小：    128.5 MB
配置加载：


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
