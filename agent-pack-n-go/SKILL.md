---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: agent-pack-n-go
name: agent-pack-n-go
displayName: 智能体搬迁 配置打包 设备迁移
description: 将智能体配置、记忆与技能打包迁移至新设备，约25分钟完成。
version: 1.0.2
rules_version: cpr-20260811-n351
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/agent-pack-n-go
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: LingShift Studio
agent_created: true
trigger_words: ["agent-pack-n-go", "克隆智能体", "迁移配置", "打包技能", "设备迁移", "换机搬家", "环境复制"]
---

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->


> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# agent-pack-n-go 技能文档

## 一、能力边界（一页纸速查卡）

本技能用于将当前设备上的 AI 智能体运行环境（含配置文件、长期记忆存储、已安装技能包）完整复制到另一台设备，并完成基础联通性验证。

| 维度 | 说明 |
|------|------|
| **核心能力** | 打包智能体配置目录、记忆数据库、技能清单；生成迁移包；在新设备上执行还原脚本；输出迁移报告 |
| **支持输入格式** | `http`（远程配置仓库地址）、`markdown`（本地或远程的 `.md` 格式配置说明文件） |
| **典型耗时** | 约 25 分钟（含打包 5 分钟、传输 5 分钟、还原 10 分钟、验证 5 分钟） |
| **适用对象** | 个人开发者更换工作机、团队内共享智能体基线配置、需要将本地智能体复制到云端沙箱的场景 |
| **明确不做** | 不迁移操作系统级环境变量（仅迁移智能体自身配置）；不处理模型 API Key 的重新签发；不负责目标设备的依赖预装（如 Python 运行时）；不执行跨大版本（如 v1→v2）的配置结构自动升级 |

**输入参数速查**

| 参数名 | 类型 | 必填 | 默认值 | 说明 |
|--------|------|------|--------|------|
| `--source` | string | 是 | 无 | 源配置路径，支持本地目录、`http(s)://` 远程地址、`markdown` 文件路径 |
| `--target` | string | 是 | 无 | 目标设备写入路径，须为本地绝对路径 |
| `--include-memory` | boolean | 否 | `true` | 是否携带长期记忆数据库 |
| `--include-skills` | boolean | 否 | `true` | 是否携带已安装技能包 |
| `--selftest` | flag | 否 | 无 | 运行自检，验证本技能环境完整性 |
| `--version` | flag | 否 | 无 | 输出版本号 |

---

## 二、触发方式与场景映射

当你在对话中表达以下意图时，本技能会被唤醒：

| 大白话场景 | 触发词示例 | 技能响应动作 |
|------------|------------|--------------|
| "我要换电脑了，把我现在的 AI 助手搬过去" | 克隆智能体、设备迁移、换机搬家 | 启动完整打包流程，询问源路径与目标路径 |
| "帮我把这个仓库里的配置同步到服务器上" | 迁移配置、环境复制 | 解析 `http` 源，生成迁移包并推送至目标 |
| "把技能列表导出一份给我" | 打包技能 | 仅执行技能清单导出，不包含记忆数据 |
| "检查一下我的迁移环境是否就绪" | --selftest | 运行环境自检，输出检查报告 |

---

## 三、标准执行流程

### 前置条件

1. 源设备上存在有效的智能体配置目录（默认 `~/.agent-core/`，可通过 `--source` 覆盖）。
2. 目标设备已安装 `agent-pack-n-go` 命令行工具（版本 ≥ 1.0.0）。
3. 源与目标之间具备网络连通性（若使用 `http` 源）或文件传输通道（U 盘、scp 等）。
4. 已确认目标设备磁盘剩余空间 ≥ 源配置目录大小的 2 倍（含解压临时空间）。

### 执行步骤

**阶段一：读取与解析（约 2 分钟）**

1. 读取 `--source` 参数。若为空，进入交互模式，提示用户输入源路径。
2. 根据输入格式分流：
   - 本地目录：直接校验目录存在性及可读权限。
   - `http(s)://`：下载至临时目录，校验下载文件完整性（SHA-256 比对）。
   - `markdown` 文件：解析文件内嵌的 `config_path` 字段，定位实际配置目录。
3. 校验通过后，输出源配置摘要（目录大小、文件数、技能数量、记忆库大小）。

**阶段二：打包（约 5 分钟）**

4. 根据 `--include-memory` 与 `--include-skills` 决定打包内容范围。
5. 生成 `manifest.json`，记录以下字段：
   ```json
   {
     "schema_version": "1.0",
     "created_at": "2026-08-11T10:00:00Z",
     "source_device_id": "device-uuid-xxxx",
     "content": {
       "config": true,
       "memory": true,
       "skills": true
     },
     "file_count": 128,
     "total_size_bytes": 52428800
   }
   ```
6. 使用 `tar.gz` 格式压缩，输出文件命名为 `agent-migration-{timestamp}.tar.gz`。

**阶段三：传输（约 5 分钟）**

7. 若目标设备可达（SSH 或已挂载共享目录），直接推送；否则提示用户手动拷贝迁移包。

**阶段四：还原（约 10 分钟）**

8. 在目标设备上执行 `agent-pack-n-go --restore <迁移包路径> --target <目标路径>`。
9. 还原脚本自动完成：解压 → 校验 manifest → 写入配置 → 导入记忆库 → 注册技能包。
10. 若目标路径已存在旧配置，先备份至 `{target}.bak-{timestamp}`，再执行覆盖。

**阶段五：验证与输出（约 3 分钟）**

11. 运行连通性测试：加载配置、读取一条记忆、调用一个技能，确认三项均返回成功。
12. 输出迁移报告，格式如下：

```
迁移报告
========
源设备: device-uuid-xxxx
目标设备: device-uuid-yyyy
迁移时间: 2026-08-11T10:25:00Z
配置还原: 成功
记忆导入: 成功 (128 条)
技能注册: 成功 (5 个)
验证结果: 全部通过
```

### 输出规范

- 所有输出使用 `stdout` 打印，错误信息使用 `stderr`。
- 报告必须包含上述五个字段，缺失任一字段视为迁移失败。
- 退出码约定：`0` 成功；`1` 参数错误；`2` 源读取失败；`3` 打包失败；`4` 还原失败；`5` 验证失败。

---

## 四、置信度门控

在执行过程中，若遇到以下信息缺失情况，本技能不会自行猜测，而是输出 `[需核实:字段名]` 占位符，并暂停后续流程：

| 场景 | 占位符示例 | 处理方式 |
|------|------------|----------|
| 源路径不存在，且无法通过交互获取有效路径 | `[需核实:source_path]` | 终止流程，提示用户重新输入 |
| `http` 源下载后校验和不匹配 | `[需核实:checksum]` | 终止流程，提示用户检查网络或源文件 |
| `markdown` 文件中未找到 `config_path` 字段 | `[需核实:config_path]` | 终止流程，提示用户补充字段 |
| 目标设备磁盘空间不足 | `[需核实:disk_space]` | 终止流程，提示用户清理空间后重试 |
| 记忆库文件损坏无法解析 | `[需核实:memory_db_integrity]` | 跳过记忆导入，在报告中标记为"需人工介入" |

**原则：宁缺毋滥。** 任何关键路径上的不确定信息，一律以占位符形式暴露给用户，绝不编造默认值。

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| `E001` | 参数缺失或格式错误 | "参数不完整，请检查 --source 与 --target 是否已提供" | 重新执行命令，补齐参数 |
| `E002` | 源路径不可读 | "无法读取源路径，请确认目录存在且具备读权限" | 检查路径拼写、权限设置 |
| `E003` | 打包过程异常（磁盘满、文件占用） | "打包失败，请检查磁盘空间及文件占用情况" | 清理空间，关闭占用进程后重试 |
| `E004` | 目标路径不可写 | "目标路径不可写，请更换路径或调整权限" | 修改目录权限或选择新路径 |
| `E005` | 还原后验证失败 | "验证未通过，请查看报告中的失败项" | 根据报告定位失败项，手动修复后重新验证 |
| `E006` | 迁移包损坏 | "迁移包校验失败，文件可能已损坏" | 重新打包或重新传输 |

---

## 六、FAQ 反模式对照

| 常见坑 | 反模式（错误做法） | 正确模式 |
|--------|-------------------|----------|
| 迁移后技能无法调用 | 直接拷贝技能目录，忽略依赖声明 | 在还原阶段执行 `agent-pack-n-go --restore` 时自动读取技能包的 `requirements.txt` 并提示安装 |
| 记忆数据丢失 | 仅打包配置文件，未包含记忆库 | 确认 `--include-memory` 为 `true`（默认值），并在报告中核对记忆条数 |
| 目标设备已有旧配置 | 直接覆盖，导致旧数据永久丢失 | 先自动备份至 `.bak-{timestamp}`，再执行覆盖 |
| 远程源下载中断 | 忽略校验和，直接使用不完整文件 | 强制校验 SHA-256，不匹配即终止 |
| 跨设备路径不一致 | 硬编码绝对路径 | 使用相对路径模板，还原时根据 `--target` 动态拼接 |

---

## 七、渐进式披露

### 速查卡（30 秒上手）

```
迁移三步走：
1. 源设备打包：agent-pack-n-go --source ~/.agent-core --target /tmp/migration.tar.gz
2. 传输文件：scp /tmp/migration.tar.gz user@new-device:/tmp/
3. 目标还原：agent-pack-n-go --restore /tmp/migration.tar.gz --target ~/.agent-core
```

### 分层次阅读路径

**新手路径（首次使用）**

- 阅读「一、能力边界」了解适用范围。
- 直接使用速查卡中的三条命令完成迁移。
- 遇到问题对照「五、错误码体系」定位原因。

**进阶路径（深度定制）**

- 阅读「三、标准执行流程」理解各阶段细节。
- 使用 `--include-memory=false` 进行仅配置迁移测试。
- 修改 `manifest.json` 中的 `schema_version` 以适配自定义场景。
- 阅读「四、置信度门控」了解占位符机制，便于二次开发。

---

## 八、自检命令

运行 `agent-pack-n-go --selftest` 可验证本技能运行环境是否完整：

```
自检项 1: 配置目录模板存在 ......... 通过
自检项 2: 打包模块可导入 ........... 通过
自检项 3: 还原脚本可执行 ........... 通过
自检项 4: 网络模块（http源）可用 ... 通过
自检项 5: markdown解析器可用 ....... 通过
```

任一自检项失败，输出对应错误码并建议重新安装。

---

## 用户协议

<!-- user-agreement-injected -->

使用本技能（agent-pack-n-go）即表示您理解并同意以下条款：

1. **责任承担**：使用者自行承担因使用本技能进行智能体迁移所产生的一切后果，包括但不限于数据丢失、配置错误、服务中断等。技能作者及贡献者不对任何直接或间接损失承担责任。
2. **禁止反向工程**：未经授权，不得对本技能的核心逻辑进行反向工程、反编译、破解或试图提取源代码（开源部分除外）。
3. **合规使用**：使用者须确保迁移行为符合源设备与目标设备所在平台的服务条款，不得利用本技能进行未授权的数据复制。
4. **无担保声明**：本技能按"现状"提供，不附带任何明示或暗示的担保，包括但不限于适销性、特定用途适用性及非侵权保证。

---

## 许可证（License）

<!-- professional-license-embedded -->

MIT License

Copyright (c) 2026 LingShift Studio

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
