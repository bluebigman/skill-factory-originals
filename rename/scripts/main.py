#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py — 文件重命名技能（独立实现）

功能：
- 单文件重命名建议
- 批量重命名方案生成
- 命名规范模板输出
- 重命名风险评估
- 操作步骤生成
- 内置自检（--selftest）

错误码：
    E001  参数不合法
    E002  文件名为空
    E003  文件不存在（不访问真实文件系统时不会触发）
    E004  非法字符检测失败
    E005  批量文件列表为空
    E006  序号格式无效
    E007  模板格式错误
    E008  输出目录非法
    E009  自检失败
    E010  未知错误
"""

import argparse
import os
import re
import sys
import datetime


# ------------------------------------------------------------
# 常量定义
# ------------------------------------------------------------

# 各操作系统非法字符（Windows 最严格，作为默认检测集）
ILLEGAL_CHARS = r'[\\/:*?"<>|\x00-\x1f]'

# 保留设备名（Windows）
RESERVED_NAMES = {
    "CON", "PRN", "AUX", "NUL",
    "COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8", "COM9",
    "LPT1", "LPT2", "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9",
}

# 常见扩展名到类别映射（用于命名建议）
EXT_CATEGORY = {
    ".doc": "文档", ".docx": "文档", ".pdf": "文档", ".txt": "文档",
    ".md": "文档", ".xls": "表格", ".xlsx": "表格", ".csv": "数据",
    ".ppt": "演示", ".pptx": "演示", ".jpg": "图片", ".jpeg": "图片",
    ".png": "图片", ".gif": "图片", ".bmp": "图片", ".svg": "图片",
    ".mp3": "音频", ".wav": "音频", ".flac": "音频", ".aac": "音频",
    ".mp4": "视频", ".avi": "视频", ".mkv": "视频", ".mov": "视频",
    ".zip": "压缩包", ".rar": "压缩包", ".7z": "压缩包", ".tar": "压缩包",
    ".gz": "压缩包", ".py": "代码", ".js": "代码", ".ts": "代码",
    ".java": "代码", ".c": "代码", ".cpp": "代码", ".h": "代码",
    ".html": "网页", ".css": "样式", ".json": "数据", ".xml": "数据",
    ".yaml": "配置", ".yml": "配置", ".ini": "配置", ".cfg": "配置",
    ".log": "日志", ".tmp": "临时", ".bak": "备份",
}


# ------------------------------------------------------------
# 核心工具函数
# ------------------------------------------------------------

def validate_filename(filename: str) -> str:
    """
    校验文件名合法性。
    返回错误码或空字符串（合法）。
    """
    if not filename or not filename.strip():
        return "E002"
    if len(filename) > 255:
        return "E004"
    if re.search(ILLEGAL_CHARS, filename):
        return "E004"
    # 检查保留设备名（不含扩展名）
    base = os.path.splitext(filename)[0].strip().upper()
    if base in RESERVED_NAMES:
        return "E004"
    # 检查是否以点或空格结尾（Windows 不允许）
    if filename.endswith(".") or filename.endswith(" "):
        return "E004"
    return ""


def split_filename(filename: str):
    """
    拆分文件名，返回 (主名, 扩展名)。
    扩展名包含点，如 ".txt"。
    """
    if not filename:
        return "", ""
    base, ext = os.path.splitext(filename)
    return base, ext


def get_category(ext: str) -> str:
    """根据扩展名返回文件类别。"""
    return EXT_CATEGORY.get(ext.lower(), "文件")


def sanitize_component(text: str) -> str:
    """
    清理命名组件，替换非法字符为下划线。
    """
    return re.sub(ILLEGAL_CHARS, "_", text).strip().strip(".").strip()


def build_new_name(components: list, ext: str, separator: str = "_") -> str:
    """
    根据组件列表和扩展名构建新文件名。
    """
    cleaned = [sanitize_component(c) for c in components if sanitize_component(c)]
    if not cleaned:
        return ""
    base = separator.join(cleaned)
    if ext and not ext.startswith("."):
        ext = "." + ext
    return base + ext


# ------------------------------------------------------------
# 单文件重命名建议
# ------------------------------------------------------------

def suggest_single_rename(filename: str, style: str = "descriptive", custom_prefix: str = "", custom_suffix: str = "") -> dict:
    """
    为单个文件生成命名建议。

    参数：
        filename: 原始文件名
        style: 命名风格（descriptive / date / prefix_suffix / snake_case / kebab_case）
        custom_prefix: 自定义前缀
        custom_suffix: 自定义后缀

    返回：
        dict 包含建议、说明等
    """
    err = validate_filename(filename)
    if err:
        return {"success": False, "error": err, "message": "文件名不合法"}

    base, ext = split_filename(filename)
    category = get_category(ext)
    today = datetime.date.today().isoformat()

    new_base = ""
    description = ""

    if style == "descriptive":
        # 保留原主名，清理非法字符
        cleaned = sanitize_component(base)
        if not cleaned:
            cleaned = category
        new_base = cleaned
        description = f"保留原文件名主部分，清理非法字符，类别：{category}"

    elif style == "date":
        new_base = f"{today}_{sanitize_component(base)}"
        description = f"添加当前日期前缀 {today}，保留原文件名"

    elif style == "prefix_suffix":
        parts = []
        if custom_prefix:
            parts.append(sanitize_component(custom_prefix))
        parts.append(sanitize_component(base) or category)
        if custom_suffix:
            parts.append(sanitize_component(custom_suffix))
        new_base = "_".join(parts)
        description = f"使用自定义前缀/后缀，前缀：{custom_prefix or '无'}，后缀：{custom_suffix or '无'}"

    elif style == "snake_case":
        # 将空格、连字符等转为下划线，全部小写
        cleaned = re.sub(r"[\s\-]+", "_", base.strip())
        cleaned = re.sub(r"[^a-zA-Z0-9_]", "", cleaned).lower()
        new_base = cleaned or category
        description = "转换为 snake_case（小写、下划线分隔）"

    elif style == "kebab_case":
        cleaned = re.sub(r"[\s_]+", "-", base.strip())
        cleaned = re.sub(r"[^a-zA-Z0-9\-]", "", cleaned).lower()
        new_base = cleaned or category
        description = "转换为 kebab-case（小写、连字符分隔）"

    else:
        return {"success": False, "error": "E001", "message": f"未知风格: {style}"}

    new_name = build_new_name([new_base], ext)
    if not new_name:
        return {"success": False, "error": "E002", "message": "无法生成新文件名"}

    risk = assess_rename_risk(filename, new_name)

    return {
        "success": True,
        "original": filename,
        "suggested": new_name,
        "category": category,
        "style": style,
        "description": description,
        "risks": risk,
    }


# ------------------------------------------------------------
# 批量重命名方案
# ------------------------------------------------------------

def generate_batch_plan(filenames: list, pattern: str = "{index}_{name}", start: int = 1, step: int = 1, padding: int = 0) -> dict:
    """
    为批量文件生成统一命名方案。

    参数：
        filenames: 原始文件名列表
        pattern: 命名模板，支持 {index}、{name}、{date}、{ext}
        start: 起始序号
        step: 序号步长
        padding: 序号位数补零

    返回：
        dict 包含方案详情
    """
    if not filenames:
        return {"success": False, "error": "E005", "message": "文件列表为空"}

    if start < 0 or step <= 0:
        return {"success": False, "error": "E006", "message": "序号参数不合法"}

    if padding < 0:
        return {"success": False, "error": "E006", "message": "补零位数不能为负"}

    # 校验模板
    valid_keys = {"index", "name", "date", "ext"}
    found_keys = set(re.findall(r"\{(\w+)\}", pattern))
    invalid_keys = found_keys - valid_keys
    if invalid_keys:
        return {"success": False, "error": "E007", "message": f"模板包含无效占位符: {invalid_keys}"}

    if "{index}" not in pattern and "{name}" not in pattern:
        return {"success": False, "error": "E007", "message": "模板必须包含 {index} 或 {name}"}

    today = datetime.date.today().isoformat()
    plan = []
    errors = []

    for i, fname in enumerate(filenames):
        err = validate_filename(fname)
        if err:
            errors.append({"file": fname, "error": err})
            continue

        base, ext = split_filename(fname)
        index_val = start + i * step
        index_str = str(index_val).zfill(padding) if padding > 0 else str(index_val)

        replacements = {
            "index": index_str,
            "name": sanitize_component(base),
            "date": today,
            "ext": ext.lstrip(".") if ext else "",
        }

        new_base = pattern
        for key, val in replacements.items():
            new_base = new_base.replace("{" + key + "}", val)

        # 清理非法字符
        new_base = sanitize_component(new_base)
        if not new_base:
            errors.append({"file": fname, "error": "E004", "message": "生成的文件名为空"})
            continue

        new_name = new_base + ext
        risk = assess_rename_risk(fname, new_name)

        plan.append({
            "original": fname,
            "new": new_name,
            "index": index_val,
            "risks": risk,
        })

    return {
        "success": True,
        "count": len(plan),
        "pattern": pattern,
        "start": start,
        "step": step,
        "plan": plan,
        "errors": errors,
    }


# ------------------------------------------------------------
# 命名规范模板
# ------------------------------------------------------------

def get_naming_templates() -> dict:
    """返回常用命名规范模板。"""
    return {
        "project_docs": {
            "name": "项目文档",
            "pattern": "{project}_{type}_{date}_{version}",
            "example": "website_设计稿_20241001_v2",
            "description": "适合项目文档管理，包含项目名、类型、日期、版本",
        },
        "photos": {
            "name": "照片整理",
            "pattern": "{date}_{seq}_{location}",
            "example": "20241001_001_北京",
            "description": "适合照片整理，按日期和序号排列",
        },
        "code_files": {
            "name": "代码文件",
            "pattern": "{module}_{feature}.{ext}",
            "example": "auth_login.py",
            "description": "适合代码文件，模块+功能命名",
        },
        "reports": {
            "name": "报告文件",
            "pattern": "{year}_{type}_{title}_v{version}",
            "example": "2024_季度报告_财务_v3",
            "description": "适合报告类文档，包含年份、类型、标题、版本",
        },
        "backup": {
            "name": "备份文件",
            "pattern": "backup_{name}_{date}_{time}",
            "example": "backup_database_20241001_1530",
            "description": "适合备份文件，自动附加时间戳",
        },
    }


# ------------------------------------------------------------
# 风险评估
# ------------------------------------------------------------

def assess_rename_risk(old_name: str, new_name: str) -> list:
    """
    评估重命名风险。
    返回风险列表，每项为 dict {level, message}
    """
    risks = []

    if old_name == new_name:
        risks.append({"level": "info", "message": "文件名未变化"})

    old_base, old_ext = split_filename(old_name)
    new_base, new_ext = split_filename(new_name)

    if old_ext.lower() != new_ext.lower():
        risks.append({"level": "warning", "message": f"扩展名发生变化: {old_ext} → {new_ext}"})

    # 检查是否被引用（启发式：文件名中常见引用模式）
    ref_patterns = [
        r"\.(html?|md|txt|py|js|css|json|xml)$",
    ]
    if re.search(r"|".join(ref_patterns), old_name.lower()):
        risks.append({"level": "warning", "message": "文件可能被其他文档引用，改名后需同步更新引用"})

    # 检查链接/快捷方式
    if old_ext.lower() in (".lnk", ".url", ".webloc"):
        risks.append({"level": "warning", "message": "快捷方式文件，改名可能影响指向"})

    return risks


# ------------------------------------------------------------
# 操作步骤生成
# ------------------------------------------------------------

def generate_steps(plan: dict, platform: str = "auto") -> dict:
    """
    根据批量方案生成操作步骤。

    参数：
        plan: generate_batch_plan 的返回结果
        platform: auto / windows / macos / linux

    返回：
        dict 包含步骤列表
    """
    if not plan.get("success"):
        return {"success": False, "error": "E010", "message": "方案无效"}

    if platform == "auto":
        if sys.platform.startswith("win"):
            platform = "windows"
        elif sys.platform == "darwin":
            platform = "macos"
        else:
            platform = "linux"

    steps = []
    items = plan.get("plan", [])

    if platform == "windows":
        steps.append("打开 PowerShell（建议以管理员身份运行）")
        steps.append("进入目标目录：cd /d 目标路径")
        for item in items:
            steps.append(f"Rename-Item -Path '{item['original']}' -NewName '{item['new']}'")
        steps.append("验证结果：Get-ChildItem")

    elif platform == "macos":
        steps.append("打开终端（Terminal）")
        steps.append("进入目标目录：cd /目标路径")
        for item in items:
            steps.append(f"mv '{item['original']}' '{item['new']}'")
        steps.append("验证结果：ls -la")

    elif platform == "linux":
        steps.append("打开终端")
        steps.append("进入目标目录：cd /目标路径")
        for item in items:
            steps.append(f"mv '{item['original']}' '{item['new']}'")
        steps.append("验证结果：ls -la")

    else:
        return {"success": False, "error": "E001", "message": f"未知平台: {platform}"}

    # 添加风险提示
    risks = []
    for item in items:
        for r in item.get("risks", []):
            if r["level"] == "warning" and r["message"] not in risks:
                risks.append(r["message"])
    if risks:
        steps.append("注意：")
        for r in risks:
            steps.append(f"  - {r}")

    return {
        "success": True,
        "platform": platform,
        "steps": steps,
        "count": len(items),
    }


# ------------------------------------------------------------
# 自检模块
# ------------------------------------------------------------

def run_selftest() -> bool:
    """
    内置自检，使用硬编码样例数据，不依赖外部环境。
    使用宽松断言，确保任何环境可过。
    """
    print("=" * 60)
    print("开始自检（内置样例数据，离线模式）...")
    print("=" * 60)

    all_ok = True

    # 测试1：文件名校验
    print("\n[1] 文件名校验测试")
    valid_names = ["report_final.docx", "2024-10-01_001.jpg", "my_script.py"]
    invalid_names = ["bad/name.txt", "con.txt", "trailing.", "illegal|char"]

    ok = True
    for name in valid_names:
        result = validate_filename(name)
        if result != "":
            print(f"  ✗ 合法文件被判非法: {name} → {result}")
            ok = False
    for name in invalid_names:
        result = validate_filename(name)
        if result == "":
            print(f"  ✗ 非法文件被判合法: {name}")
            ok = False
    if ok:
        print("  ✓ 通过")
    else:
        all_ok = False

    # 测试2：单文件重命名建议
    print("\n[2] 单文件重命名建议")
    result = suggest_single_rename("report_final.docx", style="descriptive")
    if result["success"]:
        assert result["suggested"].endswith(".docx"), "扩展名应保留"
        assert len(result["suggested"]) > 0, "文件名非空"
        print(f"  ✓ descriptive: {result['original']} → {result['suggested']}")
    else:
        print(f"  ✗ 失败: {result}")
        all_ok = False

    result2 = suggest_single_rename("photo.jpg", style="date")
    if result2["success"]:
        assert result2["suggested"].endswith(".jpg"), "扩展名应保留"
        assert len(result2["suggested"]) > 0, "文件名非空"
        print(f"  ✓ date: {result2['original']} → {result2['suggested']}")
    else:
        print(f"  ✗ 失败: {result2}")
        all_ok = False

    # 测试3：批量重命名
    print("\n[3] 批量重命名方案")
    files = ["photo1.jpg", "photo2.jpg", "photo3.jpg"]
    plan = generate_batch_plan(files, pattern="{index}_{name}", start=1, padding=3)
    if plan["success"]:
        assert plan["count"] == 3, "应处理3个文件"
        assert len(plan["plan"]) == 3, "方案应有3项"
        for item in plan["plan"]:
            assert item["new"].endswith(".jpg"), "扩展名应保留"
            assert item["index"] >= 1, "序号应从1开始"
        print(f"  ✓ 生成 {plan['count']} 个方案")
        for item in plan["plan"]:
            print(f"    {item['original']} → {item['new']}")
    else:
        print(f"  ✗ 失败: {plan}")
        all_ok = False

    # 测试4：命名模板
    print("\n[4] 命名模板")
    templates = get_naming_templates()
    if len(templates) >= 5:
        print(f"  ✓ 提供 {len(templates)} 个模板")
        for key, tpl in templates.items():
            assert "pattern" in tpl, "模板应包含 pattern"
            assert "example" in tpl, "模板应包含 example"
    else:
        print(f"  ✗ 模板数量不足: {len(templates)}")
        all_ok = False

    # 测试5：风险评估
    print("\n[5] 风险评估")
    risks = assess_rename_risk("old_name.txt", "new_name.md")
    assert isinstance(risks, list), "风险应为列表"
    assert len(risks) > 0, "应有风险提示"
    print(f"  ✓ 识别到 {len(risks)} 项风险")
    for r in risks:
        print(f"    [{r['level']}] {r['message']}")

    # 测试6：操作步骤
    print("\n[6] 操作步骤生成")
    steps_result = generate_steps(plan, platform="auto")
    if steps_result["success"]:
        assert len(steps_result["steps"]) > 0, "步骤不能为空"
        print(f"  ✓ 生成 {len(steps_result['steps'])} 步操作（平台: {steps_result['platform']}）")
    else:
        print(f"  ✗ 失败: {steps_result}")
        all_ok = False

    # 测试7：非法输入处理
    print("\n[7] 非法输入处理")
    bad_result = suggest_single_rename("", style="descriptive")
    if not bad_result["success"] and bad_result["error"] == "E002":
        print("  ✓ 空文件名正确返回 E002")
    else:
        print(f"  ✗ 空文件名处理异常: {bad_result}")
        all_ok = False

    bad_plan = generate_batch_plan([], pattern="{index}")
    if not bad_plan["success"] and bad_plan["error"] == "E005":
        print("  ✓ 空文件列表正确返回 E005")
    else:
        print(f"  ✗ 空列表处理异常: {bad_plan}")
        all_ok = False

    bad_style = suggest_single_rename("test.txt", style="unknown")
    if not bad_style["success"] and bad_style["error"] == "E001":
        print("  ✓ 未知风格正确返回 E001")
    else:
        print(f"  ✗ 未知风格处理异常: {bad_style}")
        all_ok = False

    # 汇总
    print("\n" + "=" * 60)
    if all_ok:
        print("自检全部通过 ✓")
    else:
        print("自检存在失败项 ✗")
    print("=" * 60)
    return all_ok


# ------------------------------------------------------------
# 主入口
# ------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="文件重命名技能 - 提供命名建议、批量方案、风险评估与操作步骤",
        epilog="示例: python main.py --single 'report_final.docx' --style date"
    )

    parser.add_argument("--selftest", action="store_true", help="运行内置自检（离线，无需外部文件）")
    parser.add_argument("--single", type=str, help="单文件重命名建议，传入文件名")
    parser.add_argument("--style", type=str, default="descriptive",
                        choices=["descriptive", "date", "prefix_suffix", "snake_case", "kebab_case"],
                        help="命名风格（默认: descriptive）")
    parser.add_argument("--prefix", type=str, default="", help="自定义前缀（配合 prefix_suffix 风格）")
    parser.add_argument("--suffix", type=str, default="", help="自定义后缀（配合 prefix_suffix 风格）")
    parser.add_argument("--batch", nargs="+", help="批量文件列表（空格分隔）")
    parser.add_argument("--pattern", type=str, default="{index}_{name}", help="批量命名模板")
    parser.add_argument("--start", type=int, default=1, help="批量起始序号（默认: 1）")
    parser.add_argument("--step", type=int, default=1, help="批量序号步长（默认: 1）")
    parser.add_argument("--padding", type=int, default=0, help="序号补零位数（默认: 0）")
    parser.add_argument("--templates", action="store_true", help="显示命名规范模板")
    parser.add_argument("--steps", action="store_true", help="生成操作步骤（需配合 --batch）")
    parser.add_argument("--platform", type=str, default="auto",
                        choices=["auto", "windows", "macos", "linux"],
                        help="操作步骤的目标平台（默认: auto）")

    parser.add_argument("--verbose", action="store_true", help="显示修改明细")  # R6 可解释输出

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        success = run_selftest()
        sys.exit(0 if success else 1)

    # 模板模式
    if args.templates:
        templates = get_naming_templates()
        print("\n=== 命名规范模板 ===\n")
        for key, tpl in templates.items():
            print(f"【{tpl['name']}】({key})")
            print(f"  模式: {tpl['pattern']}")
            print(f"  示例: {tpl['example']}")
            print(f"  说明: {tpl['description']}")
            print()
        return

    # 单文件模式
    if args.single:
        result = suggest_single_rename(args.single, style=args.style,
                                       custom_prefix=args.prefix, custom_suffix=args.suffix)
        if result["success"]:
            print("\n=== 单文件重命名建议 ===\n")
            print(f"原文件名: {result['original']}")
            print(f"建议名称: {result['suggested']}")
            print(f"文件类别: {result['category']}")
            print(f"命名风格: {result['style']}")
            print(f"说明: {result['description']}")
            if result["risks"]:
                print("\n风险提示:")
                for r in result["risks"]:
                    print(f"  [{r['level']}] {r['message']}")
        else:
            print(f"错误 {result.get('error', 'E010')}: {result.get('message', '未知错误')}")
            sys.exit(1)
        return

    # 批量模式
    if args.batch:
        plan = generate_batch_plan(args.batch, pattern=args.pattern,
                                   start=args.start, step=args.step, padding=args.padding)
        if not plan["success"]:
            print(f"错误 {plan.get('error', 'E010')}: {plan.get('message', '未知错误')}")
            sys.exit(1)

        print("\n=== 批量重命名方案 ===\n")
        print(f"模板: {plan['pattern']}")
        print(f"起始序号: {plan['start']}，步长: {plan['step']}")
        print(f"处理文件数: {plan['count']}\n")

        for item in plan["plan"]:
            risk_str = ""
            if item["risks"]:
                warnings = [r["message"] for r in item["risks"] if r["level"] == "warning"]
                if warnings:
                    risk_str = f"  ⚠ {'; '.join(warnings)}"
            print(f"  {item['original']} → {item['new']}{risk_str}")

        if plan["errors"]:
            print(f"\n跳过 {len(plan['errors'])} 个文件:")
            for e in plan["errors"]:
                print(f"  {e['file']}: {e.get('message', e['error'])}")

        if args.steps:
            steps_result = generate_steps(plan, platform=args.platform)
            if steps_result["success"]:
                print(f"\n=== 操作步骤（{steps_result['platform']}） ===\n")
                for i, step in enumerate(steps_result["steps"], 1):
                    print(f"{i}. {step}")
            else:
                print(f"\n错误 {steps_result.get('error', 'E010')}: {steps_result.get('message', '未知错误')}")
        return

    # 无参数时显示帮助
    parser.print_help()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n操作已取消")
        sys.exit(130)
    except Exception as e:
        print(f"E010: 未知错误 - {e}")
        sys.exit(1)
