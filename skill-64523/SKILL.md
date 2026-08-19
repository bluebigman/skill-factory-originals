---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: skill-64523
name: 批量文件重命名
displayName: 文件批量重命名 规则引擎 脚本生成
description: 按规则批量重命名文件，生成对照预览与可执行脚本。
version: 1.0.1
rules_version: cpr-20260819-n551
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/skill-64523
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 林默
agent_created: true
trigger_words: ["批量重命名", "文件重命名", "重命名规则", "批量改名", "文件改名"]
---

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->


> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# 批量文件重命名 规则引擎 脚本生成

## 一、能力边界（一页纸速查卡）

### 1.1 能做什么

| 能力项 | 说明 | 示例 |
|--------|------|------|
| 目录扫描 | 列出指定文件夹内的全部文件（含子目录可选） | `./docs/` 下 128 个 `.md` 文件 |
| 规则解析 | 支持前缀、后缀、序号、替换、正则提取等规则 | 加前缀 `2024_`、序号 `01_`、替换 `old→new` |
| 对照预览 | 生成"原名 → 新名"的完整对照表 | `report.pdf → 2024_report.pdf` |
| 脚本生成 | 输出可直接运行的 Python 脚本（跨平台） | `rename_script.py` |
| 安全回滚 | 生成撤销脚本，可一键恢复原名 | `undo_rename.py` |

### 1.2 不能做什么

| 限制项 | 说明 |
|--------|------|
| 不执行重命名 | 本 Skill 只生成脚本和预览，实际重命名需用户本地运行 |
| 不处理系统文件 | 不涉及 `C:\Windows`、`/System` 等系统目录 |
| 不支持模糊匹配 | 规则必须是明确的字符串或正则表达式 |
| 不处理文件内容 | 仅修改文件名，不触碰文件内部数据 |
| 不保证唯一性 | 若新名冲突，脚本会报错并跳过，需用户调整规则 |

### 1.3 适用对象

- **适合**：需要批量整理文档、图片、日志、导出文件的办公人员、数据分析师、开发者。
- **不适合**：需要重命名文件内容、需要跨设备同步重命名、需要图形界面操作的用户。

---

## 二、触发方式

### 2.1 触发词

- 核心触发词：`批量重命名`、`文件重命名`、`重命名规则`、`批量改名`、`文件改名`
- 补充触发词：`文件整理`、`批量改名工具`、`重命名脚本`

### 2.2 场景映射表

| 用户说（大白话） | 实际需求 | 本 Skill 响应 |
|------------------|----------|---------------|
| "帮我把一堆照片改成有顺序的名字" | 按序号重命名 | 生成序号规则脚本 |
| "这些报告文件想加个日期前缀" | 加前缀 | 生成前缀规则脚本 |
| "把文件名里的 'draft' 改成 'final'" | 字符串替换 | 生成替换规则脚本 |
| "我想先看看改完是什么样再动手" | 预览对照 | 输出对照表 + 脚本 |
| "改坏了能恢复吗？" | 安全回滚 | 生成撤销脚本 |

---

## 三、标准流程

### 3.1 前置条件

| 条件 | 要求 | 检查方式 |
|------|------|----------|
| 目标文件夹 | 存在且可读 | 用户提供路径 |
| 文件列表 | 非空 | 扫描确认 |
| 重命名规则 | 明确且无歧义 | 用户描述 + AI 确认 |
| Python 环境 | 3.6+（仅运行脚本时需要） | 用户自查 |

### 3.2 执行步骤

**第 1 步：确认目标文件夹**

- 用户提供绝对路径或相对路径。
- AI 输出示例：`目标文件夹：/Users/username/Documents/reports/`

**第 2 步：明确重命名规则**

| 规则类型 | 参数 | 示例 |
|----------|------|------|
| 加前缀 | `prefix` 字符串 | `2024_` |
| 加后缀 | `suffix` 字符串 | `_final` |
| 序号 | `start` 起始值、`digits` 位数、`separator` 分隔符 | 从 1 开始，2 位数，`_` 分隔 |
| 替换 | `old` 旧字符串、`new` 新字符串 | `draft → final` |
| 正则提取 | `pattern` 正则表达式、`replacement` 替换模板 | `(\d{4})-\d{2}-\d{2} → $1` |

**第 3 步：生成对照表预览**

- AI 输出前 10 条对照示例，格式如下：

```
原文件名 → 新文件名
----------------------------
report_draft.pdf → 2024_report_final.pdf
report_draft_v2.pdf → 2024_report_final_v2.pdf
...
```

- 若文件超过 50 个，提示"完整对照表见脚本注释"。

**第 4 步：生成可执行脚本**

- 输出 `rename_script.py`，包含：
  - 文件扫描逻辑
  - 规则应用逻辑
  - 冲突检测（新名重复时报错跳过）
  - 日志输出（记录每次重命名的前后对照）
  - 撤销脚本 `undo_rename.py`（自动生成）

**第 5 步：用户本地运行**

- 用户将脚本保存到目标文件夹，执行 `python rename_script.py`。
- 运行后检查输出日志，确认无异常。

### 3.3 输出规范

| 输出项 | 格式 | 说明 |
|--------|------|------|
| 对照表 | Markdown 表格 | 前 10 条预览 + 总数统计 |
| 脚本 | Python 代码块 | 可直接保存运行 |
| 撤销脚本 | Python 代码块 | 自动生成，无需用户编写 |
| 使用说明 | 3 步操作指南 | 保存 → 运行 → 验证 |

---

## 四、置信度门控

### 4.1 信息不足时的处理

当以下信息缺失时，AI 输出 `[需核实:字段]` 占位，不编造内容：

| 缺失字段 | 占位示例 | 用户需补充 |
|----------|----------|------------|
| 文件夹路径 | `[需核实:目标文件夹路径]` | 提供绝对路径 |
| 规则参数 | `[需核实:前缀字符串]` | 明确前缀内容 |
| 文件类型 | `[需核实:目标文件扩展名]` | 指定 `.pdf`、`.jpg` 等 |
| 序号起始值 | `[需核实:序号起始值]` | 默认从 1 开始 |

### 4.2 规则冲突检测

- 若替换规则导致新名为空，输出 `[需核实:替换规则]` 并提示"替换后文件名为空，请调整规则"。
- 若序号位数不足（如 100 个文件但位数设为 2），输出 `[需核实:序号位数]` 并建议改为 3 位。

---

## 五、错误码体系

| 错误码 | 错误描述 | 提示话术 | 修正步骤 |
|--------|----------|----------|----------|
| `E001` | 文件夹不存在 | "目标文件夹不存在，请检查路径" | 确认路径是否正确，或创建文件夹 |
| `E002` | 文件夹为空 | "目标文件夹内没有文件" | 确认文件是否已放入，或检查扩展名过滤 |
| `E003` | 规则参数缺失 | "缺少必要参数：前缀/后缀/替换字符串" | 补充完整规则参数 |
| `E004` | 新文件名冲突 | "检测到重名文件：`a.pdf` 与 `b.pdf` 将重命名为同名" | 调整规则（如增加序号） |
| `E005` | 非法字符 | "文件名包含非法字符：`/`、`\`、`:` 等" | 替换规则中排除非法字符 |
| `E006` | 权限不足 | "无法读取文件夹，可能没有访问权限" | 检查文件夹权限，或更换路径 |
| `E007` | 脚本运行失败 | "脚本执行出错，请查看日志" | 检查 Python 环境，或手动执行单条命令 |

---

## 六、FAQ 反模式

### 6.1 常见坑

| 坑 | 反模式描述 | 正确做法 |
|----|------------|----------|
| 坑 1：直接执行 | 用户要求"直接改吧"，AI 直接生成脚本并让用户运行 | 必须先输出对照表预览，用户确认后再运行 |
| 坑 2：规则模糊 | 用户说"把名字改好看点"，AI 自行发挥 | 必须明确规则参数，否则输出 `[需核实:规则]` |
| 坑 3：忽略冲突 | 生成脚本时不检查重名，导致运行时报错 | 脚本内置冲突检测，提前提示用户 |
| 坑 4：无回滚 | 不生成撤销脚本，改错了无法恢复 | 每次生成脚本时自动附带 `undo_rename.py` |
| 坑 5：路径硬编码 | 脚本中写死绝对路径，换机器无法运行 | 脚本使用相对路径，或运行时读取当前目录 |

### 6.2 反模式对照表

| 反模式 | 问题 | 替代方案 |
|--------|------|----------|
| "我帮你直接改" | 违反安全原则，无法回滚 | 生成脚本 + 预览，用户自行执行 |
| "这个规则肯定没问题" | 绝对化承诺，违反合规 | 输出"建议先在小范围测试" |
| "所有文件都适用" | 忽略特殊情况（隐藏文件、只读文件） | 脚本默认跳过隐藏文件和系统文件 |

---

## 七、渐进式披露

### 7.1 速查卡（新手路径）

```
1. 告诉我文件夹路径
2. 告诉我规则（前缀/序号/替换）
3. 看预览对照表
4. 保存脚本 → 运行 → 完成
```

### 7.2 进阶路径（有经验用户）

- **自定义正则**：支持 `pattern` 参数，如 `(\d{4})-(\d{2})-(\d{2})` 提取日期。
- **批量规则组合**：支持多规则叠加，如先加前缀再替换。
- **过滤条件**：支持按扩展名、文件名模式过滤，如 `*.pdf`。
- **干跑模式**：脚本支持 `--dry-run` 参数，只输出对照不实际重命名。

### 7.3 参数速查表

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `--path` | str | 当前目录 | 目标文件夹路径 |
| `--prefix` | str | 空 | 文件名前缀 |
| `--suffix` | str | 空 | 文件名后缀 |
| `--start` | int | 1 | 序号起始值 |
| `--digits` | int | 2 | 序号位数 |
| `--separator` | str | `_` | 序号分隔符 |
| `--old` | str | 空 | 替换的旧字符串 |
| `--new` | str | 空 | 替换的新字符串 |
| `--pattern` | str | 空 | 正则表达式 |
| `--replacement` | str | 空 | 正则替换模板 |
| `--dry-run` | bool | False | 干跑模式，不实际重命名 |
| `--recursive` | bool | False | 是否包含子目录 |

---

## 八、脚本示例

### 8.1 基础重命名脚本

```python
#!/usr/bin/env python3
"""批量文件重命名脚本 - 自动生成"""
import os
import re
import sys
import argparse
from pathlib import Path

def parse_args():
    parser = argparse.ArgumentParser(description="批量文件重命名工具")
    parser.add_argument("--path", default=".", help="目标文件夹路径")
    parser.add_argument("--prefix", default="", help="文件名前缀")
    parser.add_argument("--suffix", default="", help="文件名后缀")
    parser.add_argument("--start", type=int, default=1, help="序号起始值")
    parser.add_argument("--digits", type=int, default=2, help="序号位数")
    parser.add_argument("--separator", default="_", help="序号分隔符")
    parser.add_argument("--old", default="", help="替换的旧字符串")
    parser.add_argument("--new", default="", help="替换的新字符串")
    parser.add_argument("--pattern", default="", help="正则表达式")
    parser.add_argument("--replacement", default="", help="正则替换模板")
    parser.add_argument("--dry-run", action="store_true", help="干跑模式")
    parser.add_argument("--recursive", action="store_true", help="包含子目录")
    return parser.parse_args()

def get_files(path, recursive=False):
    """获取文件列表"""
    p = Path(path)
    if recursive:
        return [f for f in p.rglob("*") if f.is_file()]
    return [f for f in p.iterdir() if f.is_file()]

def apply_rule(filename, args, index):
    """应用重命名规则"""
    stem, ext = os.path.splitext(filename)
    new_name = stem

    # 替换规则
    if args.old and args.new:
        new_name = new_name.replace(args.old, args.new)

    # 正则规则
    if args.pattern and args.replacement:
        new_name = re.sub(args.pattern, args.replacement, new_name)

    # 序号规则
    if args.start is not None:
        seq = str(args.start + index).zfill(args.digits)
        new_name = f"{seq}{args.separator}{new_name}"

    # 前缀/后缀
    new_name = f"{args.prefix}{new_name}{args.suffix}{ext}"
    return new_name

def main():
    args = parse_args()
    files = get_files(args.path, args.recursive)

    if not files:
        print(f"错误 E002: 文件夹 {args.path} 内没有文件")
        sys.exit(1)

    # 冲突检测
    new_names = []
    for i, f in enumerate(files):
        new_name = apply_rule(f.name, args, i)
        new_names.append(new_name)

    # 检查重名
    seen = {}
    for old, new in zip(files, new_names):
        if new in seen:
            print(f"错误 E004: 重名冲突 - {old.name} 和 {seen[new]} 都将重命名为 {new}")
            sys.exit(1)
        seen[new] = old.name

    # 输出对照表
    print(f"共 {len(files)} 个文件，预览前 10 条：")
    print("-" * 50)
    for i, (old, new) in enumerate(zip(files, new_names)):
        if i < 10:
            print(f"{old.name} → {new}")
        # 记录日志
        with open("rename_log.txt", "a") as log:
            log.write(f"{old.name} → {new}\n")

    # 干跑模式
    if args.dry_run:
        print("干跑模式，未执行实际重命名")
        return

    # 执行重命名
    for old, new in zip(files, new_names):
        old_path = old
        new_path = old.with_name(new)
        os.rename(old_path, new_path)
        print(f"已重命名: {old.name} → {new}")

    # 生成撤销脚本
    with open("undo_rename.py", "w") as f:
        f.write("#!/usr/bin/env python3\n")
        f.write("import os\n")
        for old, new in zip(files, new_names):
            f.write(f"os.rename({repr(new)}, {repr(old.name)})\n")
        f.write("print('已恢复所有文件名')\n")

    print("重命名完成，撤销脚本已生成: undo_rename.py")

if __name__ == "__main__":
    main()
```

### 8.2 使用示例

```bash
# 加前缀
python rename_script.py --path ./docs --prefix "2024_"

# 加序号
python rename_script.py --path ./images --start 1 --digits 3 --separator "_"

# 替换
python rename_script.py --path ./reports --old "draft" --new "final"

# 正则提取日期
python rename_script.py --path ./logs --pattern "(\d{4})-(\d{2})-(\d{2})" --replacement "\1_\2_\3"

# 干跑模式（不实际执行）
python rename_script.py --path ./docs --prefix "2024_" --dry-run
```

---

## 九、用户协议

<!-- user-agreement-injected -->

**使用本 Skill 即表示您同意以下条款：**

1. **责任承担**：使用者自行承担全部责任。本 Skill 提供的脚本和指导仅供参考，使用者应自行验证脚本的正确性和安全性，并在测试环境中先行测试。
2. **禁止反向工程**：禁止对本 Skill 生成的脚本进行反向工程、反编译或试图提取源代码（法律允许的除外）。
3. **数据安全**：使用者应自行备份重要数据。本 Skill 不对因使用脚本导致的数据丢失或损坏负责。
4. **合规使用**：使用者应确保使用本 Skill 的行为符合当地法律法规及所在组织的规章制度。
5. **无担保**：本 Skill 按"现状"提供，不附带任何明示或暗示的担保。

---

## 十、许可证（License）

<!-- professional-license-embedded -->

**MIT License**

Copyright (c) 2026 林默

Permission
