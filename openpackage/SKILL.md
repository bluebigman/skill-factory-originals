---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: openpackage
name: openpackage
displayName: 技能包收纳分发 批量校验 命令编排
description: 统一收纳、组织、分发技能包与命令，支持批量转换与格式校验。
version: 1.0.3
rules_version: cpr-20260817-n526
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/openpackage
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 林默
agent_created: true
trigger_words: ["openpackage", "技能包管理", "技能组织", "命令编排", "技能分发", "技能包收纳", "批量转换", "格式校验"]
---

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->


> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# openpackage — 技能包收纳分发与批量校验工具

## 一、能力边界（一页纸速查卡）

### 1.1 能做什么

| 能力项 | 具体说明 | 典型场景 |
|--------|----------|----------|
| 技能包收纳 | 将散落的技能文件（SKILL.md、脚本、配置）归入统一目录结构 | 整理个人技能库 |
| 命令编排 | 将多条 CLI 命令按依赖顺序组织为可执行序列 | 批量处理任务 |
| 批量转换 | 将一种格式的技能包批量转换为目标格式 | 迁移到新平台 |
| 格式校验 | 检查技能包是否符合命名规范、frontmatter 完整性 | 发布前自检 |
| 分发打包 | 将技能包打包为可分发的压缩文件或目录树 | 分享给团队 |

### 1.2 不能做什么

| 限制项 | 说明 |
|--------|------|
| 不解析技能内容 | 只处理文件结构与元数据，不评估技能质量 |
| 不执行技能逻辑 | 不运行技能内部的代码或命令 |
| 不自动修复错误 | 只报告问题，修复需人工介入 |
| 不支持跨平台 GUI | 仅提供 CLI 接口 |

### 1.3 适用对象

- 维护大量技能包的开发者
- 需要批量整理技能文件的团队
- 准备发布技能到公开平台的作者

---

## 二、触发方式

### 2.1 触发词映射表

| 触发词 | 大白话场景 |
|--------|------------|
| openpackage | 直接调用工具 |
| 技能包管理 | 想整理技能文件 |
| 技能组织 | 文件太乱想归类 |
| 命令编排 | 多条命令想串起来 |
| 技能分发 | 想把技能分享给别人 |
| 技能包收纳 | 新下载的技能文件没地方放 |
| 批量转换 | 格式不统一想统一 |
| 格式校验 | 发布前检查格式对不对 |

### 2.2 命令行入口

```bash
openpackage [子命令] [参数]
```

| 子命令 | 功能 | 示例 |
|--------|------|------|
| `--selftest` | 自检安装是否正常 | `openpackage --selftest` |
| `--version` | 查看版本号 | `openpackage --version` |
| `pack` | 收纳技能包到目录 | `openpackage pack ./src ./out` |
| `convert` | 批量转换格式 | `openpackage convert --from md --to yaml ./files` |
| `validate` | 校验格式合规性 | `openpackage validate ./skills` |
| `distribute` | 打包分发 | `openpackage distribute ./skills --format zip` |

---

## 三、标准流程

### 3.1 前置条件

| 条件 | 要求 | 检查方法 |
|------|------|----------|
| 输入目录 | 存在且可读 | `ls -la <目录>` |
| 文件命名 | 符合 `技能名_版本号.扩展名` 规范 | `ls *.md` 目测 |
| 输出目录 | 存在或可创建 | `mkdir -p <目录>` |
| 磁盘空间 | 剩余空间 ≥ 输入体积 × 2 | `df -h` |
| 备份 | 原始文件已备份 | `cp -r <输入> <备份路径>` |

### 3.2 执行步骤

#### 步骤 1：准备输入

将待处理文件放入同一目录，确认命名规范一致。

```bash
# 创建输入目录
mkdir -p ./input

# 移动技能文件到输入目录
mv ~/Downloads/*.md ./input/

# 检查命名规范
ls ./input/
# 期望输出：skillname_1.0.0.md, another_2.1.0.md
```

**命名规范检查表：**

| 元素 | 规则 | 示例 |
|------|------|------|
| 技能名 | 小写字母+数字+下划线 | `text_summarizer` |
| 版本号 | 语义化版本 x.y.z | `1.2.3` |
| 分隔符 | 下划线 `_` | `text_summarizer_1.2.3` |
| 扩展名 | `.md` 或 `.yaml` | `.md` |

#### 步骤 2：试运行

先用单个样本执行，核对输出字段与格式。

```bash
# 单文件校验
openpackage validate ./input/sample_1.0.0.md

# 单文件转换
openpackage convert --from md --to yaml ./input/sample_1.0.0.md
```

**试运行检查点：**

- [ ] 输出文件是否生成
- [ ] 字段映射是否正确
- [ ] 格式是否符合预期
- [ ] 错误信息是否清晰

#### 步骤 3：批量执行

确认无误后对全量数据执行，并保留原始文件备份。

```bash
# 备份原始文件
cp -r ./input ./backup_$(date +%Y%m%d)

# 批量校验
openpackage validate ./input/

# 批量转换
openpackage convert --from md --to yaml ./input/ --output ./output/
```

**批量执行参数表：**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `--from` | string | 无 | 源格式 |
| `--to` | string | 无 | 目标格式 |
| `--output` | path | `./output` | 输出目录 |
| `--recursive` | bool | false | 递归处理子目录 |
| `--dry-run` | bool | false | 只显示将执行的操作 |
| `--force` | bool | false | 覆盖已存在文件 |

#### 步骤 4：校验结果

抽查输出条目，核对关键字段与源数据一致。

```bash
# 抽查前 5 个文件
ls ./output/ | head -5

# 对比源文件与输出文件
diff ./input/sample_1.0.0.md ./output/sample_1.0.0.yaml
```

**校验清单：**

| 字段 | 源文件 | 输出文件 | 一致性 |
|------|--------|----------|--------|
| slug | openpackage | openpackage | ✅ |
| name | openpackage | openpackage | ✅ |
| version | 1.0.0 | 1.0.0 | ✅ |
| description | 原描述 | 原描述 | ✅ |

### 3.3 输出规范

**校验报告格式：**

```yaml
validation_report:
  timestamp: 2026-08-17T10:30:00Z
  total_files: 25
  passed: 23
  failed: 2
  warnings: 5
  failures:
    - file: "bad_name.md"
      reason: "命名不符合规范，缺少版本号"
    - file: "missing_frontmatter_1.0.0.md"
      reason: "frontmatter 缺少 description 字段"
```

**转换输出目录结构：**

```
output/
├── skill1_1.0.0.yaml
├── skill2_2.1.0.yaml
└── conversion_report.json
```

---

## 四、置信度门控

### 4.1 信息不足时的处理

当输入信息不完整时，使用 `[需核实:字段]` 占位，不编造数据。

| 场景 | 处理方式 | 示例 |
|------|----------|------|
| 缺少版本号 | 输出 `[需核实:version]` | `name_[需核实:version].md` |
| 缺少描述 | 输出 `[需核实:description]` | 校验报告标注缺失 |
| 格式不确定 | 询问用户确认 | `无法确定源格式，请指定 --from 参数` |
| 依赖关系不明 | 标记为待确认 | `依赖关系未声明，请确认` |

### 4.2 门控规则

1. 遇到无法确认的信息，必须输出占位符，不得猜测
2. 校验报告必须明确标注「需人工确认」的项目
3. 批量操作前必须执行 `--dry-run` 预览

---

## 五、错误码体系

### 5.1 常见错误码

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| `E001` | 输入目录不存在 | `输入目录不存在: <路径>` | 检查路径是否正确，创建目录 |
| `E002` | 文件命名不规范 | `文件命名不符合规范: <文件名>` | 重命名为 `技能名_版本号.扩展名` |
| `E003` | frontmatter 缺失 | `文件缺少 frontmatter: <文件名>` | 添加 YAML frontmatter 头 |
| `E004` | 必填字段缺失 | `缺少必填字段: <字段名>` | 补充对应字段 |
| `E005` | 输出目录不可写 | `无法写入输出目录: <路径>` | 检查权限，更换目录 |
| `E006` | 格式不支持 | `不支持的格式: <格式>` | 使用 `--list-formats` 查看支持格式 |
| `E007` | 转换失败 | `转换失败: <文件名>` | 查看详细日志，检查源文件格式 |
| `E008` | 磁盘空间不足 | `磁盘空间不足，需要 <大小> 可用空间` | 清理磁盘，或更换输出路径 |

### 5.2 错误处理流程

```bash
# 查看详细错误日志
openpackage validate ./input/ --verbose

# 只处理失败文件
openpackage validate ./input/ --only-failed

# 跳过错误继续执行
openpackage convert ./input/ --skip-errors
```

---

## 六、FAQ 反模式

### 6.1 常见坑与反模式对照

| 常见坑 | 反模式（错误做法） | 正模式（正确做法） |
|--------|-------------------|-------------------|
| 覆盖原始文件 | 直接在原目录执行转换 | 先备份，再转换到新目录 |
| 忽略命名规范 | 文件名随意，如 `新建文档.md` | 统一为 `技能名_版本号.md` |
| 跳过试运行 | 直接批量处理全部文件 | 先单文件试运行，确认无误再批量 |
| 不检查输出 | 转换完不查看结果 | 抽查输出文件，对比关键字段 |
| 依赖默认值 | 不指定参数，依赖默认配置 | 显式指定 `--from`、`--to`、`--output` |
| 忽略警告 | 只看错误，不看警告 | 警告也需检查，可能是潜在问题 |

### 6.2 反模式示例

**反模式 1：直接批量处理**

```bash
# ❌ 错误：没有试运行直接批量
openpackage convert ./all_files/

# ✅ 正确：先试运行单个文件
openpackage convert ./all_files/sample_1.0.0.md
openpackage convert ./all_files/ --dry-run
openpackage convert ./all_files/
```

**反模式 2：不保留备份**

```bash
# ❌ 错误：直接覆盖原文件
openpackage convert ./input/ --output ./input/

# ✅ 正确：备份后转换到新目录
cp -r ./input ./backup
openpackage convert ./input/ --output ./output/
```

**反模式 3：忽略命名规范**

```bash
# ❌ 错误：文件名不规范
mv ~/Downloads/我的技能.md ./input/

# ✅ 正确：规范命名
mv ~/Downloads/我的技能.md ./input/my_skill_1.0.0.md
```

---

## 七、渐进式披露

### 7.1 速查卡（新手必读）

```
openpackage 使用三步走：
1. 准备：文件放同一目录，命名规范
2. 试运行：先处理一个文件
3. 批量：确认无误后处理全部
```

### 7.2 分层次阅读路径

#### 新手路径（5 分钟上手）

1. 阅读「能力边界」了解工具能做什么
2. 阅读「标准流程」的步骤 1-2
3. 使用 `--selftest` 验证安装
4. 用单个文件试运行

#### 进阶路径（深入使用）

1. 阅读「错误码体系」了解常见问题
2. 阅读「FAQ 反模式」避免踩坑
3. 掌握 `--dry-run`、`--recursive` 等高级参数
4. 自定义输出格式和校验规则

#### 专家路径（定制化）

1. 编写自定义校验规则文件
2. 使用 `--config` 指定配置文件
3. 集成到 CI/CD 流程
4. 开发插件扩展功能

### 7.3 参数速查表

| 参数 | 用途 | 新手建议 |
|------|------|----------|
| `--selftest` | 自检安装 | 首次使用必跑 |
| `--version` | 查看版本 | 确认版本兼容 |
| `--dry-run` | 预览操作 | 批量前必用 |
| `--verbose` | 详细日志 | 排查问题时使用 |
| `--recursive` | 递归处理 | 处理嵌套目录时使用 |
| `--skip-errors` | 跳过错误 | 批量处理时使用 |
| `--force` | 强制覆盖 | 谨慎使用 |
| `--config` | 指定配置 | 进阶用户使用 |

---

## 八、配置文件示例

### 8.1 自定义校验规则

```yaml
# validate_rules.yaml
rules:
  required_fields:
    - slug
    - name
    - version
    - description
  naming_pattern: "^[a-z0-9_]+_[0-9]+\\.[0-9]+\\.[0-9]+\\.(md|yaml)$"
  max_file_size: 1024  # KB
  allowed_formats:
    - md
    - yaml
```

### 8.2 批量转换配置

```yaml
# convert_config.yaml
input_dir: "./input"
output_dir: "./output"
from_format: "md"
to_format: "yaml"
recursive: true
backup: true
backup_dir: "./backup"
dry_run: false
skip_errors: true
```

---

## 九、用户协议

<!-- user-agreement-injected -->

**使用 openpackage Skill 即表示您同意以下条款：**

1. **责任承担**：使用者自行承担使用本 Skill 的全部责任。因使用本 Skill 导致的任何直接或间接损失，包括但不限于数据丢失、文件损坏、业务中断等，Skill 作者及贡献者不承担任何责任。

2. **禁止反向工程**：不得对本 Skill 进行反向工程、反编译、反汇编或试图提取源代码（适用法律允许的除外）。

3. **合法使用**：使用者应确保使用本 Skill 的行为符合当地法律法规，不得用于任何非法目的。

4. **无担保声明**：本 Skill 按「现状」提供，不附带任何明示或暗示的担保，包括但不限于适销性、特定用途适用性和非侵权保证。

5. **修改与分发**：允许修改和分发本 Skill，但须保留原始版权声明和本协议。

---

## 十、许可证（License）

<!-- professional-license-embedded -->

### MIT License

Copyright (c) 2026 林默

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
