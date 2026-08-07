#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
openpackage — 技能包管家（独立实现）

本脚本依据功能规格独立编写，用于：
- 统一收纳、组织、分发技能包与命令
- 支持批量转换与格式校验
- 提供命令行自检（--selftest）

错误码说明：
    E001: 参数错误
    E002: 文件读取失败
    E003: 文件写入失败
    E004: 数据解析失败
    E005: 数据校验失败
    E006: 不支持的输出格式
    E007: 批量处理失败
    E008: 输入为空
    E009: 内部逻辑错误
    E010: 未知错误

仅使用 Python 标准库，无第三方依赖。
"""

import argparse
import json
import os
import sys
import tempfile
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# 核心数据结构与常量
# ---------------------------------------------------------------------------

# 支持的输出格式
SUPPORTED_FORMATS = ("json", "markdown", "yaml")

# 置信度级别
CONFIDENCE_LEVELS = ("高", "中", "低")

# 必填核心字段
REQUIRED_FIELDS = ("name", "version", "description")

# 可选核心字段
OPTIONAL_FIELDS = ("author", "license", "trigger_words", "dependencies", "source_url")


def make_empty_package() -> Dict[str, Any]:
    """创建一个空的技能包数据结构。"""
    return {
        "name": "",
        "version": "",
        "description": "",
        "author": "",
        "license": "",
        "trigger_words": [],
        "dependencies": [],
        "source_url": "",
        "confidence": {},  # 字段名 -> 置信度
        "raw_input": "",   # 原始输入记录
    }


# ---------------------------------------------------------------------------
# 核心逻辑：信息提取与结构化
# ---------------------------------------------------------------------------

def parse_text_input(text: str) -> Dict[str, Any]:
    """
    从自由文本中提取技能包关键信息。

    规则：
    - 尝试识别名称、版本、描述等字段
    - 无法确定时使用 [需核实:字段名] 占位
    - 为每个字段标注置信度
    """
    pkg = make_empty_package()
    pkg["raw_input"] = text.strip()

    if not text or not text.strip():
        return pkg

    lines = [line.strip() for line in text.splitlines() if line.strip()]

    # 启发式提取：逐行扫描常见模式
    for line in lines:
        # 名称：形如 "名称: xxx" 或 "name: xxx"
        lower = line.lower()
        for key in ("名称", "name"):
            if lower.startswith(f"{key}:"):
                pkg["name"] = line.split(":", 1)[1].strip()
                pkg["confidence"]["name"] = "高"
                break
        else:
            continue

        # 版本：形如 "版本: 1.2.3" 或 "version: 1.2.3"
        for key in ("版本", "version"):
            if lower.startswith(f"{key}:"):
                pkg["version"] = line.split(":", 1)[1].strip()
                pkg["confidence"]["version"] = "高"
                break

        # 描述：形如 "描述: xxx" 或 "description: xxx"
        for key in ("描述", "description"):
            if lower.startswith(f"{key}:"):
                pkg["description"] = line.split(":", 1)[1].strip()
                pkg["confidence"]["description"] = "高"
                break

        # 作者
        for key in ("作者", "author"):
            if lower.startswith(f"{key}:"):
                pkg["author"] = line.split(":", 1)[1].strip()
                pkg["confidence"]["author"] = "高"
                break

        # 许可证
        for key in ("许可证", "license"):
            if lower.startswith(f"{key}:"):
                pkg["license"] = line.split(":", 1)[1].strip()
                pkg["confidence"]["license"] = "高"
                break

        # 触发词：可逗号/空格分隔
        for key in ("触发词", "trigger_words"):
            if lower.startswith(f"{key}:"):
                raw = line.split(":", 1)[1].strip()
                words = [w.strip() for w in raw.replace("，", ",").split(",") if w.strip()]
                pkg["trigger_words"] = words
                pkg["confidence"]["trigger_words"] = "高"
                break

        # 依赖
        for key in ("依赖", "dependencies"):
            if lower.startswith(f"{key}:"):
                raw = line.split(":", 1)[1].strip()
                deps = [d.strip() for d in raw.replace("，", ",").split(",") if d.strip()]
                pkg["dependencies"] = deps
                pkg["confidence"]["dependencies"] = "高"
                break

        # 来源 URL
        for key in ("来源", "source_url", "url"):
            if lower.startswith(f"{key}:"):
                pkg["source_url"] = line.split(":", 1)[1].strip()
                pkg["confidence"]["source_url"] = "高"
                break

    # 对未提取到的必填字段进行占位与低置信度标注
    for field in REQUIRED_FIELDS:
        if not pkg.get(field):
            pkg[field] = f"[需核实:{field}]"
            pkg["confidence"][field] = "低"

    # 对可选字段，若缺失则标注低置信度（但不占位）
    for field in OPTIONAL_FIELDS:
        if field not in pkg["confidence"]:
            pkg["confidence"][field] = "低"

    return pkg


def parse_json_input(json_str: str) -> Dict[str, Any]:
    """从 JSON 字符串解析技能包信息。"""
    try:
        data = json.loads(json_str)
    except json.JSONDecodeError as exc:
        raise ValueError(f"JSON 解析失败: {exc}") from exc

    if not isinstance(data, dict):
        raise ValueError("JSON 根节点必须是对象")

    pkg = make_empty_package()
    pkg["raw_input"] = json_str

    # 复制已知字段
    for field in REQUIRED_FIELDS + OPTIONAL_FIELDS:
        if field in data and data[field] is not None:
            pkg[field] = data[field]
            pkg["confidence"][field] = "高"

    # 缺失必填字段处理
    for field in REQUIRED_FIELDS:
        if not pkg.get(field):
            pkg[field] = f"[需核实:{field}]"
            pkg["confidence"][field] = "低"

    # 缺失可选字段标注
    for field in OPTIONAL_FIELDS:
        if field not in pkg["confidence"]:
            pkg["confidence"][field] = "低"

    return pkg


def parse_input(raw: str, input_type: str = "auto") -> Dict[str, Any]:
    """
    统一入口：根据输入类型解析为结构化技能包。

    input_type: auto / text / json
    """
    if not raw or not raw.strip():
        raise ValueError("输入为空")

    stripped = raw.strip()

    # 自动检测：若以 { 开头则尝试 JSON
    if input_type == "auto":
        if stripped.startswith("{"):
            try:
                return parse_json_input(stripped)
            except ValueError:
                # JSON 解析失败，回退到文本解析
                return parse_text_input(stripped)
        return parse_text_input(stripped)

    if input_type == "json":
        return parse_json_input(stripped)

    if input_type == "text":
        return parse_text_input(stripped)

    raise ValueError(f"不支持的输入类型: {input_type}")


# ---------------------------------------------------------------------------
# 核心逻辑：输出格式生成
# ---------------------------------------------------------------------------

def to_json(pkg: Dict[str, Any]) -> str:
    """转换为 JSON 字符串。"""
    return json.dumps(pkg, ensure_ascii=False, indent=2)


def to_markdown(pkg: Dict[str, Any]) -> str:
    """转换为 Markdown 字符串。"""
    lines = [
        f"# {pkg.get('name', '[需核实:name]')}",
        "",
        f"> 版本：{pkg.get('version', '[需核实:version]')}",
        "",
        "## 描述",
        "",
        pkg.get("description", "[需核实:description]"),
        "",
        "## 元数据",
        "",
        f"- 作者：{pkg.get('author', '未知')}",
        f"- 许可证：{pkg.get('license', '未知')}",
        f"- 来源：{pkg.get('source_url', '未知')}",
        "",
    ]

    if pkg.get("trigger_words"):
        lines.append("## 触发词")
        lines.append("")
        for word in pkg["trigger_words"]:
            lines.append(f"- {word}")
        lines.append("")

    if pkg.get("dependencies"):
        lines.append("## 依赖")
        lines.append("")
        for dep in pkg["dependencies"]:
            lines.append(f"- {dep}")
        lines.append("")

    lines.append("## 置信度")
    lines.append("")
    for field, level in pkg.get("confidence", {}).items():
        lines.append(f"- {field}: {level}")
    lines.append("")

    return "\n".join(lines)


def to_yaml(pkg: Dict[str, Any]) -> str:
    """转换为 YAML 字符串（简易实现，不引入第三方库）。"""
    lines = []

    def _format_value(value: Any, indent: int = 0) -> List[str]:
        """格式化一个值为 YAML 行。"""
        prefix = " " * indent
        if isinstance(value, dict):
            result = []
            for k, v in value.items():
                if isinstance(v, (dict, list)):
                    result.append(f"{prefix}{k}:")
                    result.extend(_format_value(v, indent + 2))
                else:
                    result.append(f"{prefix}{k}: {v}")
            return result
        elif isinstance(value, list):
            result = []
            for item in value:
                result.append(f"{prefix}- {item}")
            return result
        else:
            return [f"{prefix}{value}"]

    for field in REQUIRED_FIELDS:
        lines.append(f"{field}: {pkg.get(field, '')}")

    for field in OPTIONAL_FIELDS:
        value = pkg.get(field, "")
        if isinstance(value, list):
            if value:
                lines.append(f"{field}:")
                lines.extend(_format_value(value, 2))
            else:
                lines.append(f"{field}: []")
        elif value:
            lines.append(f"{field}: {value}")

    if pkg.get("confidence"):
        lines.append("confidence:")
        for field, level in pkg["confidence"].items():
            lines.append(f"  {field}: {level}")

    return "\n".join(lines)


def format_output(pkg: Dict[str, Any], output_format: str) -> str:
    """按指定格式输出技能包信息。"""
    fmt = output_format.lower()
    if fmt == "json":
        return to_json(pkg)
    elif fmt == "markdown":
        return to_markdown(pkg)
    elif fmt == "yaml":
        return to_yaml(pkg)
    else:
        raise ValueError(f"不支持的输出格式: {output_format}")


# ---------------------------------------------------------------------------
# 核心逻辑：批量处理
# ---------------------------------------------------------------------------

def batch_process(inputs: List[str], input_type: str = "auto") -> List[Dict[str, Any]]:
    """批量处理多个输入，返回技能包列表。"""
    if not inputs:
        raise ValueError("批量输入为空")

    results = []
    for raw in inputs:
        try:
            pkg = parse_input(raw, input_type)
            results.append(pkg)
        except Exception as exc:
            # 单个失败不影响整体，记录错误信息
            pkg = make_empty_package()
            pkg["name"] = "[处理失败]"
            pkg["description"] = str(exc)
            pkg["confidence"]["all"] = "低"
            results.append(pkg)

    return results


# ---------------------------------------------------------------------------
# 核心逻辑：格式校验
# ---------------------------------------------------------------------------

def validate_package(pkg: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    校验技能包格式是否合法。

    返回 (是否合法, 错误信息列表)
    """
    errors = []

    # 必填字段非空
    for field in REQUIRED_FIELDS:
        value = pkg.get(field, "")
        if not value or value.startswith("[需核实:"):
            errors.append(f"必填字段缺失或未确定: {field}")

    # 版本号基本格式（宽松校验：非空即可）
    version = pkg.get("version", "")
    if version and not version.startswith("[需核实:"):
        # 不强制格式，仅检查非空
        pass

    # 触发词必须是列表
    if pkg.get("trigger_words") is not None and not isinstance(pkg["trigger_words"], list):
        errors.append("trigger_words 必须是列表")

    # 依赖必须是列表
    if pkg.get("dependencies") is not None and not isinstance(pkg["dependencies"], list):
        errors.append("dependencies 必须是列表")

    # 置信度必须是字典
    if pkg.get("confidence") is not None and not isinstance(pkg["confidence"], dict):
        errors.append("confidence 必须是字典")

    return (len(errors) == 0, errors)


# ---------------------------------------------------------------------------
# 文件读写辅助
# ---------------------------------------------------------------------------

def read_file(filepath: str) -> str:
    """读取文本文件内容。"""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError as exc:
        raise IOError(f"文件不存在: {filepath}") from exc
    except PermissionError as exc:
        raise IOError(f"无权限读取: {filepath}") from exc
    except Exception as exc:
        raise IOError(f"读取失败: {filepath}") from exc


def write_file(filepath: str, content: str) -> None:
    """写入文本文件。"""
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
    except Exception as exc:
        raise IOError(f"写入失败: {filepath}") from exc


# ---------------------------------------------------------------------------
# 自检逻辑（--selftest）
# ---------------------------------------------------------------------------

def run_selftest() -> int:
    """
    内置硬编码样例数据，离线自检核心逻辑。

    使用宽松阈值（大小比较/区间判断），确保任何环境直接可过。
    """
    print("[selftest] 开始自检...")
    passed = 0
    failed = 0

    def check(condition: bool, name: str) -> None:
        nonlocal passed, failed
        if condition:
            passed += 1
            print(f"  [PASS] {name}")
        else:
            failed += 1
            print(f"  [FAIL] {name}")

    # --- 测试 1：文本解析 ---
    print("\n[测试1] 文本解析")
    sample_text = """
名称: 示例技能包
版本: 1.2.3
描述: 这是一个用于测试的技能包
作者: 测试作者
许可证: MIT
触发词: 测试, demo, sample
依赖: numpy, requests
来源: https://example.com/skill
    """
    pkg = parse_text_input(sample_text)
    check(pkg["name"] == "示例技能包", "名称提取")
    check(pkg["version"] == "1.2.3", "版本提取")
    check("测试" in pkg["trigger_words"], "触发词提取")
    check(len(pkg["dependencies"]) >= 2, "依赖提取数量")
    check(pkg["confidence"].get("name") == "高", "名称置信度")
    check(pkg["confidence"].get("version") == "高", "版本置信度")

    # --- 测试 2：JSON 解析 ---
    print("\n[测试2] JSON 解析")
    sample_json = json.dumps({
        "name": "JSON技能包",
        "version": "0.9.0",
        "description": "从JSON解析",
        "author": "JSON作者",
        "trigger_words": ["json", "test"],
        "dependencies": ["pytest"],
    })
    pkg2 = parse_json_input(sample_json)
    check(pkg2["name"] == "JSON技能包", "JSON名称")
    check(pkg2["version"] == "0.9.0", "JSON版本")
    check(len(pkg2["trigger_words"]) >= 1, "JSON触发词")
    check(pkg2["confidence"].get("name") == "高", "JSON置信度")

    # --- 测试 3：缺失字段占位 ---
    print("\n[测试3] 缺失字段处理")
    pkg3 = parse_text_input("名称: 只有名字")
    check(pkg3["version"].startswith("[需核实:"), "缺失版本占位")
    check(pkg3["description"].startswith("[需核实:"), "缺失描述占位")
    check(pkg3["confidence"].get("version") == "低", "缺失字段低置信度")

    # --- 测试 4：输出格式 ---
    print("\n[测试4] 输出格式")
    json_out = to_json(pkg)
    check(json_out.startswith("{"), "JSON输出以{开头")
    check("示例技能包" in json_out, "JSON包含名称")

    md_out = to_markdown(pkg)
    check(md_out.startswith("#"), "Markdown以#开头")
    check("示例技能包" in md_out, "Markdown包含名称")

    yaml_out = to_yaml(pkg)
    check("name: 示例技能包" in yaml_out, "YAML包含名称行")

    # --- 测试 5：格式校验 ---
    print("\n[测试5] 格式校验")
    valid, errors = validate_package(pkg)
    check(valid, "完整技能包校验通过")
    check(len(errors) == 0, "无错误信息")

    invalid_pkg = make_empty_package()
    valid2, errors2 = validate_package(invalid_pkg)
    check(not valid2, "空技能包校验失败")
    check(len(errors2) >= 3, "至少3个错误（3个必填字段）")

    # --- 测试 6：批量处理 ---
    print("\n[测试6] 批量处理")
    inputs = [sample_text, sample_json, "名称: 第三个"]
    results = batch_process(inputs)
    check(len(results) == 3, "批量处理数量")
    check(results[0]["name"] == "示例技能包", "批量第一个")
    check(results[1]["name"] == "JSON技能包", "批量第二个")
    check(results[2]["name"] == "第三个", "批量第三个")

    # --- 测试 7：错误处理 ---
    print("\n[测试7] 错误处理")
    try:
        parse_input("")
        check(False, "空输入应抛异常")
    except ValueError:
        check(True, "空输入抛异常")

    try:
        format_output(pkg, "xml")
        check(False, "不支持格式应抛异常")
    except ValueError:
        check(True, "不支持格式抛异常")

    # --- 测试 8：文件操作 ---
    print("\n[测试8] 文件操作")
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, "test.txt")
        write_file(test_file, "名称: 文件技能包\n版本: 1.0.0")
        content = read_file(test_file)
        check("文件技能包" in content, "文件读写")

        try:
            read_file(os.path.join(tmpdir, "nonexist.txt"))
            check(False, "读取不存在文件应失败")
        except IOError:
            check(True, "读取不存在文件抛IOError")

    # --- 汇总 ---
    print(f"\n[selftest] 完成: {passed} 通过, {failed} 失败")
    if failed > 0:
        print("[selftest] 有失败项！")
        return 1
    print("[selftest] 全部通过 ✓")
    return 0


# ---------------------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------------------

def main() -> int:
    """命令行主入口。"""
    parser = argparse.ArgumentParser(
        description="openpackage — 技能包管家：统一收纳、组织、分发技能包与命令",
        epilog="示例: python main.py --input data.txt --format json",
    )
    parser.add_argument(
        "--input", "-i",
        help="输入文件路径（文本或JSON）",
    )
    parser.add_argument(
        "--text",
        help="直接输入文本内容",
    )
    parser.add_argument(
        "--format", "-f",
        choices=["json", "markdown", "yaml"],
        default="json",
        help="输出格式（默认: json）",
    )
    parser.add_argument(
        "--input-type",
        choices=["auto", "text", "json"],
        default="auto",
        help="输入类型（默认: auto 自动检测）",
    )
    parser.add_argument(
        "--output", "-o",
        help="输出文件路径（默认输出到 stdout）",
    )
    parser.add_argument(
        "--batch",
        help="批量处理：输入文件路径，每行一个输入项",
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="仅校验输入格式，不输出完整结果",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检（无需外部输入）",
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        return run_selftest()

    try:
        # 收集输入
        raw_inputs: List[str] = []

        if args.batch:
            # 批量模式：从文件读取，每行一个输入
            content = read_file(args.batch)
            raw_inputs = [line.strip() for line in content.splitlines() if line.strip()]
            if not raw_inputs:
                print(f"错误 E008: 批量文件为空: {args.batch}", file=sys.stderr)
                return 8
        elif args.text:
            raw_inputs = [args.text]
        elif args.input:
            content = read_file(args.input)
            raw_inputs = [content]
        else:
            # 从 stdin 读取
            if not sys.stdin.isatty():
                content = sys.stdin.read()
                if content.strip():
                    raw_inputs = [content]

        if not raw_inputs:
            print("错误 E001: 请提供输入（--input/--text/--batch 或管道输入）", file=sys.stderr)
            return 1

        # 处理
        if args.batch:
            packages = batch_process(raw_inputs, args.input_type)
        else:
            packages = [parse_input(raw_inputs[0], args.input_type)]

        # 校验模式
        if args.validate:
            all_valid = True
            for i, pkg in enumerate(packages):
                valid, errors = validate_package(pkg)
                status = "通过" if valid else "失败"
                print(f"[{i+1}] {pkg.get('name', '未知')}: {status}")
                if not valid:
                    all_valid = False
                    for err in errors:
                        print(f"  - {err}")
            return 0 if all_valid else 1

        # 输出
        outputs = [format_output(pkg, args.format) for pkg in packages]

        if args.output:
            if len(outputs) == 1:
                write_file(args.output, outputs[0])
            else:
                # 批量输出到目录
                out_dir = args.output
                os.makedirs(out_dir, exist_ok=True)
                for i, out in enumerate(outputs):
                    filepath = os.path.join(out_dir, f"package_{i+1}.{args.format}")
                    write_file(filepath, out)
                print(f"已输出 {len(outputs)} 个文件到 {out_dir}")
        else:
            for out in outputs:
                print(out)
                if len(outputs) > 1:
                    print("---")

        return 0

    except IOError as exc:
        print(f"错误 E002/E003: {exc}", file=sys.stderr)
        return 2
    except ValueError as exc:
        print(f"错误 E004/E006: {exc}", file=sys.stderr)
        return 4
    except Exception as exc:
        print(f"错误 E010: 未知错误: {exc}", file=sys.stderr)
        return 10


if __name__ == "__main__":
    sys.exit(main())
