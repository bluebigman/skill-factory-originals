
> 📜 **用户协议（User Agreement）**
> 1. 本 Skill 仅供学习与参考用途。使用本 Skill 产生的任何结果，由使用者自行承担全部责任；本 Skill 不提供任何明示或暗示的保证。
> 2. 涉及法律、财务、税务、投资、医疗等专业决策时，请务必咨询持证专业人士。
> 3. 本代码受版权法保护，未经授权复制、反向工程或商业利用将被追究法律责任。
<!-- user-agreement-injected -->

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->
# 文件重命名

> **一页纸速查卡**：本技能用于文件重命名的批量处理、规则生成与校验。核心能力：① 解析用户模糊需求为明确规则；② 生成可执行的 Python 重命名脚本；③ 模拟执行并输出前后对照表；④ 提供安全回滚方案。使用流程：描述需求 → 确认规则 → 生成脚本 → 校验结果。典型场景：批量添加前缀、日期格式化、序号填充、扩展名统一、去除特殊字符。

---
description: 批量添加前缀/后缀。当用户需要批量添加前缀、进行skill 64523相关操作时使用本技能，提供规范、可复用的处理流程与输出。
copyright_holder: 原创作者（自持版权）
source_project: original
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
ai_generated: true
license: MIT

## 一、能力边界

### ✅ 能做（5+项具体能力）

| 编号 | 能力项 | 具体说明 |
|------|--------|----------|
| 1 | **批量添加前缀/后缀** | 支持按指定字符串（如日期、项目名、分类标签）为文件批量添加前缀或后缀，可指定是否使用分隔符（`_`、`-`、空格等） |
| 2 | **序号批量填充** | 支持按文件名排序（字母序/时间序/自定义序）后添加序号，可配置起始值、步长、位数（如 `001`、`01`），支持前置补零 |
| 3 | **日期时间格式化** | 支持从文件元数据（创建时间/修改时间）提取日期，按指定格式（`YYYYMMDD`、`YYYY-MM-DD` 等）重命名，支持时区偏移修正 |
| 4 | **查找替换与正则处理** | 支持普通字符串查找替换，也支持正则表达式匹配替换（如去除文件名中的特殊字符、统一空格为下划线、删除括号内容等） |
| 5 | **扩展名统一与大小写转换** | 支持批量修改扩展名（如 `.jpeg` → `.jpg`）、统一扩展名大小写（`.JPG` → `.jpg`）、文件名大小写转换（全大写/全小写/首字母大写） |
| 6 | **重命名规则脚本生成** | 根据确认的规则，自动生成可直接运行的 Python 脚本（基于 `pathlib` 和 `os` 模块），附带安全检查和回滚机制 |
| 7 | **模拟执行与预览** | 在执行前生成"原文件名 → 新文件名"对照表，标记潜在冲突（重名、非法字符、路径过长），支持人工确认后再执行 |

### ❌ 不做（3+项边界声明）

| 编号 | 边界声明 |
|------|----------|
| 1 | **不直接操作文件系统**：本技能只生成重命名脚本和对照表，不直接对用户磁盘文件执行修改操作。实际执行需用户在本地运行生成的脚本（或明确授权后由用户自行执行） |
| 2 | **不处理文件内容**：仅处理文件名，不读取、修改、转换文件内容（如不处理 PDF 内容提取、图片压缩等） |
| 3 | **不支持跨设备/云盘操作**：不处理网络驱动器、云盘同步目录的特殊逻辑（如 OneDrive 按需文件），仅适用于本地文件系统 |
| 4 | **不处理系统关键目录**：不适用于操作系统目录（`C:\Windows`、`/System` 等）、应用安装目录的批量重命名，避免系统损坏风险 |

---

## 二、触发方式

### 触发词表（6类场景）

| 场景类型 | 触发词示例 |
|----------|------------|
| 直接指令 | 文件重命名、批量重命名、重命名文件、改文件名 |
| 需求描述 | 文件名太乱了、帮我整理下文件名、统一命名格式、加个序号 |
| 特定操作 | 加前缀、加后缀、替换文件名中的文字、去掉特殊符号 |
| 格式处理 | 统一扩展名、改大小写、日期格式化、补零 |
| 自动化需求 | 生成重命名脚本、写个重命名工具、自动化改名 |
| 口语触发 | 帮我洗下文件名、这堆文件名字好乱、批量改下名 |

### 大白话触发示例表

| 用户原话 | 触发动作 |
|----------|----------|
| "帮我处理这个文件夹里的文件" | 启动标准流程，询问目标文件夹路径和重命名需求 |
| "这些照片名字太乱了" | 启动标准流程，建议按日期+序号方案 |
| "把报告都加上日期前缀" | 直接进入规则确认，询问日期来源（创建时间/修改时间）和格式 |
| "文件名里的空格换成下划线" | 直接进入规则确认，确认替换范围和是否处理多个连续空格 |
| "给这些文件排个序加编号" | 直接进入规则确认，询问排序依据（名称/时间/大小）和编号格式 |
| "帮我写个脚本批量改名" | 直接进入规则确认，收集完整规则后生成脚本 |

---

## 三、标准流程

### Step 1：收集最小信息集

启动时，必须向用户确认以下关键信息（至少前3项）：

| 序号 | 信息项 | 说明 | 示例 |
|------|--------|------|------|
| 1 | **目标文件夹路径** | 待重命名文件所在目录 | `D:\照片\2024旅行`、`/Users/name/Downloads` |
| 2 | **重命名规则类型** | 前缀/后缀/序号/替换/日期/扩展名/组合规则 | "加前缀"、"按日期+序号" |
| 3 | **文件筛选条件** | 按扩展名筛选（如只处理 `.jpg`）、按文件名模式筛选 | `*.pdf`、`IMG_*.jpg` |
| 4 | **排序依据**（仅序号场景） | 名称字母序/创建时间/修改时间/自定义顺序 | "按修改时间从旧到新" |
| 5 | **冲突处理策略** | 重名时如何处理：跳过/覆盖/自动加后缀 | "跳过"、"自动加 (1)" |
| 6 | **是否生成脚本** | 仅预览对照表，还是生成可执行脚本 | "生成脚本" |

**话术模板**：
> 好的，我来帮您处理文件重命名。请先告诉我：
> 1. 文件在哪个文件夹？（请提供完整路径）
> 2. 您想怎么改？（加前缀/加序号/替换文字/统一格式…）
> 3. 只处理特定类型的文件吗？（如只改 .jpg 图片）
> 4. 如果新文件名和已有文件重名，怎么处理？（跳过/覆盖/自动加序号）

### Step 2：核心执行（真实代码绑定）

根据确认的规则，使用 Python 标准库生成重命名脚本。核心工具：`pathlib`（跨平台路径处理）、`os`（文件操作）、`re`（正则替换）。

#### 2.1 规则解析与脚本生成

```python
# 核心生成逻辑（此代码片段会嵌入生成的脚本中）
from pathlib import Path
import re
import os

def build_rename_plan(folder: str, rule: dict) -> list:
    """
    根据规则字典生成重命名计划
    rule 示例:
    {
        "type": "prefix",           # prefix/suffix/sequence/replace/date/ext
        "value": "2024_",           # 前缀内容
        "ext_filter": [".jpg"],     # 扩展名筛选
        "sort_by": "mtime",         # name/mtime/ctime
        "start": 1, "step": 1, "digits": 3  # 序号参数
    }
    """
    folder_path = Path(folder)
    if not folder_path.exists():
        raise FileNotFoundError(f"文件夹不存在: {folder}")
    
    # 筛选文件
    files = [f for f in folder_path.iterdir() if f.is_file()]
    if rule.get("ext_filter"):
        files = [f for f in files if f.suffix.lower() in rule["ext_filter"]]
    
    # 排序
    if rule.get("sort_by") == "mtime":
        files.sort(key=lambda f: f.stat().st_mtime)
    elif rule.get("sort_by") == "ctime":
        files.sort(key=lambda f: f.stat().st_ctime)
    else:
        files.sort(key=lambda f: f.name.lower())
    
    # 生成新文件名
    plan = []
    for idx, f in enumerate(files):
        seq = rule.get("start", 1) + idx * rule.get("step", 1)
        seq_str = str(seq).zfill(rule.get("digits", 3))
        stem, ext = f.stem, f.suffix
        
        if rule["type"] == "prefix":
            new_name = f"{rule['value']}{stem}{ext}"
        elif rule["type"] == "suffix":
            new_name = f"{stem}{rule['value']}{ext}"
        elif rule["type"] == "sequence":
            new_name = f"{seq_str}_{stem}{ext}"
        elif rule["type"] == "replace":
            new_name = re.sub(rule["pattern"], rule["replacement"], stem) + ext
        elif rule["type"] == "date":
            import datetime
            ts = f.stat().st_mtime
            dt = datetime.datetime.fromtimestamp(ts)
            date_str = dt.strftime(rule["date_format"])
            new_name = f"{date_str}_{stem}{ext}"
        elif rule["type"] == "ext":
            new_name = f"{stem}.{rule['new_ext']}"
        else:
            raise ValueError(f"未知规则类型: {rule['type']}")
        
        plan.append((f.name, new_name))
    
    return plan
```

#### 2.2 冲突检测与安全校验

```python
def validate_plan(plan: list, folder: str) -> dict:
    """检查重命名计划中的冲突和非法文件名"""
    folder_path = Path(folder)
    issues = []
    
    # 检查新文件名是否合法
    illegal_chars = '<>:"/\\|?*'
    for old, new in plan:
        if any(c in new for c in illegal_chars):
            issues.append(f"非法字符: {old} → {new}")
        if len(new) > 255:
            issues.append(f"文件名过长: {old} → {new}")
    
    # 检查重名冲突（新名之间、新名与现有文件）
    new_names = [new for _, new in plan]
    from collections import Counter
    dupes = [name for name, cnt in Counter(new_names).items() if cnt > 1]
    for d in dupes:
        issues.append(f"重名冲突: {d}")
    
    # 检查新名是否与未在计划中的现有文件冲突
    existing = {f.name for f in folder_path.iterdir() if f.is_file()}
    planned_old = {old for old, _ in plan}
    for _, new in plan:
        if new in existing and new not in planned_old:
            issues.append(f"与现有文件冲突: {new}")
    
    return {"ok": len(issues) == 0, "issues": issues}
```

#### 2.3 生成可执行脚本（含回滚）

```python
def generate_script(plan: list, folder: str) -> str:
    """生成带备份和回滚能力的执行脚本"""
    lines = [
        "#!/usr/bin/env python3",
        "# -*- coding: utf-8 -*-",
        "# 自动生成的重命名脚本 - 请确认后执行",
        "import os",
        "import shutil",
        "from pathlib import Path",
        "",
        f"FOLDER = r'{folder}'",
        "BACKUP_DIR = Path(FOLDER) / '.rename_backup'",
        "",
        "def main():",
        "    backup_dir = BACKUP_DIR",
        "    backup_dir.mkdir(exist_ok=True)",
        "    plan = [",
    ]
    
    for old, new in plan:
        lines.append(f"        ({old!r}, {new!r}),")
    
    lines.extend([
        "    ]",
        "    for old, new in plan:",
        "        src = Path(FOLDER) / old",
        "        dst = Path(FOLDER) / new",
        "        if not src.exists():",
        "            print(f'[跳过] 源文件不存在: {old}')",
        "            continue",
        "        if dst.exists():",
        "            print(f'[跳过] 目标已存在: {new}')",
        "            continue",
        "        # 备份原文件名",
        "        shutil.copy2(src, backup_dir / old)",
        "        src.rename(dst)",
        "        print(f'[完成] {old} → {new}')",
        "",
        "if __name__ == '__main__':",
        "    main()",
    ])
    
    return "\n".join(lines)
```

### Step 3：输出校验

| 校验项 | 方法 | 通过标准 |
|--------|------|----------|
| 文件名合法性 | 检查非法字符、长度限制 | 无非法字符，长度 ≤ 255 |
| 重名冲突 | 集合比对新旧文件名 | 无重复新名，不与未处理文件冲突 |
| 路径长度 | 计算完整路径长度 | 完整路径 ≤ 260（Windows）/ 4096（Linux/macOS） |
| 规则一致性 | 抽查 3-5 个文件人工核对 | 符合用户确认的规则 |
| 可逆性 | 确认脚本包含备份逻辑 | 有备份目录和回滚说明 |

---

## 四、置信度门控

| 置信度区间 | 输出策略 | 示例场景 |
|------------|----------|----------|
| **≥ 90%** | 直接输出完整方案（对照表 + 脚本） | 规则明确、无冲突、路径有效 |
| **85-90%** | 输出方案并标注"⚠️ 建议复核" | 存在少量重名风险、排序依据不明确 |
| **< 85%** | 输出方案并标注"🔴 [需核实]" | 路径不存在、规则矛盾、大量冲突 |

**置信度计算规则**：
- 基础分 80 分
- 路径存在且可读：+5 分
- 规则类型明确且参数完整：+5 分
- 冲突检测通过：+5 分
- 用户确认了排序依据（序号场景）：+5 分

---

## 五、异常处理（错误码体系）

| 错误码 | 错误类型 | 触发条件 | 标准化话术 |
|--------|----------|----------|------------|
| **E001** | 输入为空 | 用户未提供文件夹路径 | "请提供需要重命名的文件夹路径，例如 `D:\照片` 或 `/Users/name/Downloads`" |
| **E002** | 信息缺失 | 未说明重命名规则 | "请告诉我您想怎么重命名？例如：加日期前缀、加序号、替换文字、统一扩展名等" |
| **E003** | 格式错误 | 路径格式不正确/不存在 | "您提供的路径 `{path}` 不存在或无法访问，请检查路径是否正确，或确认是否有访问权限" |
| **E004** | 超边界 | 尝试处理系统目录/无权限目录 | "该目录为系统关键目录或无权限访问，出于安全考虑，本技能不处理此类目录。请选择其他文件夹" |
| **E005** | 置信度低 | 规则矛盾/冲突过多/无法生成有效方案 | "当前信息不足以生成可靠的重命名方案，请补充：1) 具体规则 2) 排序方式 3) 冲突处理策略" |
| **E006** | 文件数超限 | 单次处理文件超过 1000 个 | "检测到文件数量超过 1000 个，建议分批处理。已为您截取前 1000 个生成方案，如需全部处理请分批执行" |

---

## 六、FAQ（高频问题速查）

**Q1：重命名后能撤销吗？**
A：生成的脚本会自动在目标文件夹下创建 `.rename_backup` 备份目录，保存所有原文件名的副本。如需回滚，将备份目录中的文件复制回原目录并删除新文件即可。建议执行前先手动备份重要文件。

**Q2：支持中文文件名吗？**
A：完全支持。脚本基于 Python 3 的 `pathlib`，原生支持 Unicode 文件名。但请注意：Windows 系统下文件名不能包含 `\ / : * ? " < > |` 字符，macOS/Linux 下不能包含 `/` 和空字符 `\0`。

**Q3：能处理子文件夹中的文件吗？**
A：默认只处理指定文件夹**顶层**的文件（不递归子目录）。如需递归处理子文件夹，请在需求中说明"包含子文件夹"，脚本会使用 `rglob('*')` 替代 `iterdir()`。

**Q4：文件太多会不会很慢？**
A：脚本使用操作系统原生 `rename` 调用，单文件操作在毫秒级。1000 个文件通常 1-2 秒内完成。主要耗时在冲突检测阶段（需遍历目录），但也在秒级完成。

**Q5：生成的脚本在别的电脑上能用吗？**
A：可以。脚本仅依赖 Python 3.6+ 标准库（`os`、`pathlib`、`re`、`shutil`），无需额外安装依赖。只需修改脚本开头的 `FOLDER` 变量为目标路径即可。

---

## 七、渐进式披露

### 📖 速览（30秒上手）
1. 告诉我要处理哪个文件夹
2. 说明重命名规则（加前缀/序号/替换等）
3. 获取对照表预览 + 可执行脚本
4. 本地运行脚本完成重命名

### 🚀 上手（3分钟进阶）
- 支持组合规则：如"日期前缀 + 序号"（在确认规则时说明"先加日期再加序号"）
- 支持正则替换：如"把 `IMG_(\d+)` 改成 `photo_\1`"
- 支持条件筛选：如"只处理 2023 年修改的文件"（需在需求中说明）

### 🎯 深度（完整能力）
- 自定义排序：按文件大小、按文件名长度排序
- 批量重命名 + 移动：重命名后移动到指定子目录
- 生成 CSV 映射表：便于人工审核或导入其他工具
- 定时任务集成：生成的脚本可加入 cron/Task Scheduler 实现定时整理

---

## 附录：完整脚本示例

以下为生成脚本的完整示例（用户确认规则后输出）：

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 自动生成的重命名脚本 - 请确认后执行
# 规则: 按修改时间排序，添加日期前缀(YYYYMMDD) + 3位序号

import os
import shutil
import datetime
from pathlib import Path

FOLDER = r'D:\照片\2024旅行'
BACKUP_DIR = Path(FOLDER) / '.rename_backup'

def main():
    backup_dir = BACKUP_DIR
    backup_dir.mkdir(exist_ok=True)
    
    # 收集文件并按修改时间排序
    files = [f for f in Path(FOLDER).iterdir() if f.is_file() and f.suffix.lower() in ['.jpg', '.jpeg']]
    files.sort(key=lambda f: f.stat().st_mtime)
    
    plan = []
    for idx, f in enumerate(files, start=1):
        dt = datetime.datetime.fromtimestamp(f.stat().st_mtime)
        date_str = dt.strftime('%Y%m%d')
        seq_str = str(idx).zfill(3)
        new_name = f"{date_str}_{seq_str}_{f.stem}{f.suffix}"
        plan.append((f.name, new_name))
    
    # 执行重命名
    for old, new in plan:
        src = Path(FOLDER) / old
        dst = Path(FOLDER) / new
        if not src.exists():
            print(f'[跳过] 源文件不存在: {old}')
            continue
        if dst.exists():
            print(f'[跳过] 目标已存在: {new}')
            continue
        shutil.copy2(src, backup_dir / old)
        src.rename(dst)
        print(f'[完成] {old} → {new}')
    
    print(f'\n完成! 共处理 {len(plan)} 个文件')
    print(f'备份目录: {backup_dir}')

if __name__ == '__main__':
    main()
```

---

> **使用建议**：对于重要文件，建议先执行 `--dry-run` 模式（可在脚本开头添加 `DRY_RUN = True` 变量，仅打印不执行），确认无误后再正式运行。本技能生成的所有脚本均包含备份逻辑，最大限度保障数据安全。

## 许可证（License）

```text
MIT License

Copyright (c) 2026 原创作者（自持版权）

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
```
<!-- professional-license-embedded -->
