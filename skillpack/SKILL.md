---
slug: skillpack
name: skillpack
displayName: 团队技能分发 打包部署 协作共享
description: 将本地AI技能打包并部署给团队，分钟级完成。
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
trigger_words: ["skillpack", "打包技能", "部署AI技能", "团队技能分发", "技能打包", "技能分发", "团队部署"]
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# SKILL.md — skillpack 技能打包与团队部署

## 一、能力边界（一页纸速查卡）

### 1.1 能做什么

| 能力项 | 说明 | 适用场景 |
|--------|------|----------|
| 技能打包 | 将本地目录中的技能文件（SKILL.md + 辅助脚本）整理为标准化压缩包 | 个人技能迁移、版本归档 |
| 团队部署 | 将打包后的技能分发到团队共享目录或指定服务器 | 团队协作、统一技能版本管理 |
| 批量处理 | 支持多技能文件批量打包，自动生成清单文件 | 技能库整理、批量迁移 |
| 校验检查 | 打包前自动检查文件完整性、frontmatter 必填字段 | 发布前质量门禁 |
| 回滚支持 | 部署前自动备份目标目录原状态 | 误操作恢复、版本回退 |

### 1.2 不能做什么

| 限制项 | 说明 |
|--------|------|
| 不修改技能内容 | 仅打包和分发，不改变 SKILL.md 内部逻辑或 prompt 内容 |
| 不处理依赖安装 | 若技能依赖外部 Python 包或 API Key，需使用者自行配置 |
| 不支持跨平台 GUI | 当前为命令行工具，无图形界面 |
| 不保证兼容性 | 目标环境需满足技能运行的最低要求（如 Python 版本、网络权限） |

### 1.3 适用对象

- **个人开发者**：需要将本地技能快速迁移到其他机器
- **团队技术负责人**：需要统一分发技能版本给多名成员
- **AI 应用运维**：需要批量部署技能到生产环境

---

## 二、触发方式

### 2.1 触发词

当用户输入以下任一关键词时，本 Skill 被激活：

- `skillpack`
- `打包技能`
- `部署AI技能`
- `团队技能分发`
- `技能打包`
- `技能分发`
- `团队部署`

### 2.2 场景映射表

| 用户说（大白话） | 实际意图 | 本 Skill 响应动作 |
|------------------|----------|-------------------|
| "帮我把这个技能发给组里人用" | 团队分发 | 执行打包 → 生成部署包 → 输出部署指引 |
| "我写了个新技能，想存个备份" | 个人归档 | 执行打包 → 生成带时间戳的压缩包 |
| "我们组要统一技能版本，别各改各的" | 版本统一 | 执行批量打包 → 生成清单 → 提供部署命令 |
| "这个技能在别人电脑上跑不起来" | 环境排查 | 执行校验 → 输出依赖清单 → 提示缺失项 |

---

## 三、标准流程

### 3.1 前置条件

| 条件项 | 要求 | 检查方式 |
|--------|------|----------|
| 输入目录 | 待打包技能文件所在目录，路径不含中文和空格 | `ls <目录>` 确认可读 |
| 文件命名 | 技能主文件必须命名为 `SKILL.md`，辅助文件命名无硬性要求 | `find <目录> -name "SKILL.md"` |
| frontmatter 完整性 | 必须包含 `slug`、`name`、`version` 三个字段 | 执行 `skillpack --check` 自动校验 |
| 目标目录 | 部署目标目录需存在且有写权限 | `mkdir -p <目标目录>` 预创建 |

### 3.2 执行步骤

#### 步骤 1：准备输入

```bash
# 将待打包的技能目录放入统一工作目录
mkdir -p ~/skillpack_workspace/input
cp -r /path/to/my_skill ~/skillpack_workspace/input/
```

#### 步骤 2：试运行（单样本验证）

```bash
# 对单个技能执行打包，验证输出格式
skillpack --input ~/skillpack_workspace/input/my_skill --output ~/skillpack_workspace/output --dry-run
```

**试运行输出示例：**

```
[DRY-RUN] 校验通过: my_skill
[DRY-RUN] 检测到文件: SKILL.md, helper.py, config.json
[DRY-RUN] frontmatter 字段完整: slug, name, version
[DRY-RUN] 预计打包大小: 24.5 KB
[DRY-RUN] 无阻塞问题，可执行正式打包
```

#### 步骤 3：批量执行

```bash
# 确认试运行无误后，对全量数据执行打包
skillpack --input ~/skillpack_workspace/input --output ~/skillpack_workspace/output --batch
```

**批量执行输出示例：**

```
[1/3] 打包 my_skill → my_skill_v1.2.0.skillpack  ✓
[2/3] 打包 data_processor → data_processor_v0.9.1.skillpack  ✓
[3/3] 打包 report_gen → report_gen_v2.0.0.skillpack  ✓
清单已生成: manifest.json
```

#### 步骤 4：部署与校验

```bash
# 部署到团队共享目录（自动备份原状态）
skillpack --deploy ~/skillpack_workspace/output --target /team/shared/skills --backup

# 抽查校验部署结果
skillpack --verify --target /team/shared/skills --sample 2
```

**校验输出示例：**

```
抽查 2 个已部署技能:
  my_skill: 文件完整, frontmatter 通过, 依赖声明完整  ✓
  report_gen: 文件完整, frontmatter 通过, 依赖声明完整  ✓
校验通过，可正常使用。
```

### 3.3 输出规范

| 输出物 | 格式 | 说明 |
|--------|------|------|
| 技能包 | `.skillpack` 后缀的 tar.gz 压缩包 | 包含技能全部文件 + 校验和文件 |
| 清单文件 | `manifest.json` | 记录每个技能包的名称、版本、大小、SHA256 校验值 |
| 部署日志 | `deploy_log.txt` | 记录部署时间、目标路径、备份路径、操作人 |
| 备份目录 | `backup_<时间戳>/` | 部署前自动创建，保存目标目录原状态 |

---

## 四、置信度门控

### 4.1 信息不足时的处理

当执行过程中遇到以下情况，**不猜测、不编造**，输出 `[需核实:字段]` 占位：

| 场景 | 占位输出 | 后续动作 |
|------|----------|----------|
| frontmatter 缺少 `version` 字段 | `[需核实:version]` | 提示用户补充版本号后重试 |
| 技能依赖的外部库未声明 | `[需核实:dependencies]` | 提示用户在 SKILL.md 中补充依赖声明 |
| 目标目录权限不确定 | `[需核实:target_permission]` | 提示用户手动检查目录写权限 |
| 技能文件编码非 UTF-8 | `[需核实:file_encoding]` | 提示用户转换编码后重试 |

### 4.2 禁止行为

- 禁止自动补全缺失的 frontmatter 字段（如自动生成 version 号）
- 禁止跳过校验直接打包
- 禁止在未确认目标目录状态时执行覆盖部署

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| `E001` | 输入目录不存在 | "未找到输入目录，请检查路径是否正确" | 确认路径，使用 `ls` 验证目录存在 |
| `E002` | SKILL.md 文件缺失 | "该目录下未找到 SKILL.md 主文件" | 确认技能文件命名正确，或手动指定文件名 |
| `E003` | frontmatter 字段不完整 | "frontmatter 缺少必要字段: [字段名]" | 编辑 SKILL.md 补充缺失字段 |
| `E004` | 目标目录无写权限 | "目标目录不可写，请检查权限设置" | 使用 `chmod` 调整权限，或更换目标目录 |
| `E005` | 打包文件已存在 | "同名技能包已存在，是否覆盖？" | 确认后使用 `--force` 覆盖，或更换输出文件名 |
| `E006` | 校验和不匹配 | "文件校验失败，可能传输损坏" | 重新打包，或从源文件重新复制 |
| `E007` | 批量处理中断 | "批量处理在第 N 个文件处中断" | 查看日志定位失败文件，单独处理后继续 |

---

## 六、FAQ 反模式

### 6.1 常见坑与反模式对照

| 常见坑 | 反模式（错误做法） | 正确做法 |
|--------|-------------------|----------|
| 打包后技能无法运行 | 跳过试运行直接批量打包 | 先对单个样本执行 `--dry-run`，确认输出格式正确 |
| 团队成员拿到的是旧版本 | 直接覆盖部署，不保留备份 | 使用 `--backup` 参数，部署前自动备份原状态 |
| 技能依赖缺失导致报错 | 打包时不检查依赖声明 | 打包前执行 `--check`，确认依赖项已声明 |
| 多人同时部署冲突 | 多人手动复制文件到同一目录 | 使用统一部署命令，配合 `manifest.json` 版本比对 |
| 技能文件被误修改 | 直接编辑已部署的文件 | 修改源文件后重新打包部署，保持部署目录只读 |

### 6.2 反模式示例

**反模式：** 用户说"直接帮我打包，不用检查了"

**正确响应：** "打包前校验是标准流程的一部分，可以跳过但会增加部署后出错的风险。建议至少执行一次 `--dry-run` 确认文件完整性。是否继续跳过校验？"

---

## 七、渐进式披露

### 7.1 速查卡（30 秒上手）

```
1. 放入文件 → 2. 试运行 → 3. 批量打包 → 4. 部署 → 5. 校验
命令速查:
  skillpack --check <目录>          # 校验
  skillpack --dry-run <目录>        # 试运行
  skillpack --batch <目录>          # 批量打包
  skillpack --deploy <包目录> --target <目标>  # 部署
  skillpack --verify --target <目标> # 校验部署结果
```

### 7.2 新手路径（首次使用）

1. 阅读本 Skill 的「能力边界」章节，确认工具符合需求
2. 准备一个测试技能目录，执行 `--check` 和 `--dry-run`
3. 确认输出符合预期后，再处理正式数据
4. 部署前务必确认目标目录状态，使用 `--backup` 参数

### 7.3 进阶路径（熟练用户）

1. 使用 `manifest.json` 做版本比对，实现增量部署
2. 编写脚本调用 `skillpack` CLI，集成到 CI/CD 流水线
3. 自定义校验规则，通过配置文件扩展 frontmatter 必填字段
4. 利用部署日志做审计追踪，记录每次变更的操作人和时间

---

## 八、参数速查表

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `--input` | 路径 | 是 | 无 | 输入目录（技能文件所在目录） |
| `--output` | 路径 | 是 | 无 | 输出目录（打包产物存放位置） |
| `--target` | 路径 | 否 | 无 | 部署目标目录（与 `--deploy` 配合使用） |
| `--batch` | 标志 | 否 | false | 批量处理模式 |
| `--dry-run` | 标志 | 否 | false | 试运行模式，不实际写入文件 |
| `--check` | 标志 | 否 | false | 仅执行校验，不打包 |
| `--verify` | 标志 | 否 | false | 校验已部署的技能 |
| `--backup` | 标志 | 否 | false | 部署前自动备份目标目录 |
| `--force` | 标志 | 否 | false | 覆盖已存在的同名文件 |
| `--sample` | 整数 | 否 | 1 | 抽查数量（与 `--verify` 配合） |
| `--selftest` | 标志 | 否 | false | 运行自检程序 |
| `--version` | 标志 | 否 | false | 显示版本信息 |

---

## 九、用户协议

<!-- user-agreement-injected -->

**使用本 Skill 即表示您同意以下条款：**

1. **责任承担**：使用者自行承担因使用本 Skill 产生的全部责任。包括但不限于因打包、部署、分发技能文件导致的任何直接或间接损失。
2. **禁止反向工程**：不得对本 Skill 的代码、逻辑、结构进行反向工程、反编译、破解或试图提取源代码。
3. **合规使用**：使用者应确保所打包和分发的技能内容不违反任何法律法规、不侵犯第三方知识产权。
4. **无担保声明**：本 Skill 按"现状"提供，不附带任何明示或暗示的担保，包括但不限于适销性、特定用途适用性和非侵权保证。
5. **修改与分发**：允许在保留本协议的前提下修改和再分发本 Skill，但需注明原始出处。

---

## 十、许可证（License）

<!-- professional-license-embedded -->

### MIT License

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

---

*本 Skill 由 AI 辅助生成，仅供参考。使用前请阅读相关文档并自行验证适用性。*
