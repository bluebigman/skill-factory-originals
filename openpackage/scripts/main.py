#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
openpackage — 技能包收纳、组织、分发、批量转换与格式校验工具

本脚本依据功能规格独立实现（clean-room），仅使用标准库。
支持子命令：organize / convert / validate / list
支持 --selftest 离线自检。
"""

import argparse
import json
import os
import re
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# 错误码定义
ERROR_CODES = {
    "E001": "参数错误：缺少必要参数或参数格式不正确",
    "E002": "路径错误：指定的路径不存在或不可访问",
    "E003": "文件错误：文件读取或写入失败",
    "E004": "格式错误：文件格式不支持或无法解析",
    "E005": "校验错误：frontmatter 必填字段缺失",
    "E006": "校验错误：frontmatter 字段类型或格式不正确",
    "E007": "转换错误：源格式与目标格式相同或转换失败",
    "E008": "组织错误：无法确定目标目录归属",
    "E009": "IO错误：临时文件或目录操作失败",
    "E010": "内部错误：未知异常",
}

# 必填字段定义
REQUIRED_FIELDS = ["name", "version", "description"]
VALID_FORMATS = ["json", "yaml", "md"]


def error_exit(code: str, message: Optional[str] = None) -> None:
    """输出错误信息并退出。"""
    msg = ERROR_CODES.get(code, "未知错误")
    if message:
        print(f"[错误 {code}] {msg}: {message}", file=sys.stderr)
    else:
        print(f"[错误 {code}] {msg}", file=sys.stderr)
    sys.exit(1)


def parse_frontmatter(content: str) -> Tuple[Dict[str, Any], str]:
    """
    解析 Markdown 文件中的 frontmatter（--- 分隔的 YAML 子集）。
    返回 (元数据字典, 正文内容)。
    仅支持简单的 key: value 或 key: [v1, v2] 形式。
    """
    if not content.startswith("---"):
        return {}, content

    lines = content.splitlines()
    if len(lines) < 2:
        return {}, content

    # 找到第二个 ---
    end_idx = -1
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end_idx = i
            break

    if end_idx == -1:
        return {}, content

    fm_lines = lines[1:end_idx]
    body = "\n".join(lines[end_idx + 1:])

    metadata: Dict[str, Any] = {}
    for line in fm_lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = key.strip()
        value = value.strip()

        if not key:
            continue

        # 处理列表值 [a, b, c]
        if value.startswith("[") and value.endswith("]"):
            items = value[1:-1].split(",")
            metadata[key] = [item.strip() for item in items if item.strip()]
        # 处理布尔值
        elif value.lower() in ("true", "false"):
            metadata[key] = value.lower() == "true"
        # 处理数字
        elif value.isdigit():
            metadata[key] = int(value)
        else:
            metadata[key] = value

    return metadata, body


def build_frontmatter(metadata: Dict[str, Any]) -> str:
    """将元数据字典转换为 frontmatter 字符串。"""
    lines = ["---"]
    for key, value in metadata.items():
        if isinstance(value, list):
            items = ", ".join(str(v) for v in value)
            lines.append(f"{key}: [{items}]")
        elif isinstance(value, bool):
            lines.append(f"{key}: {str(value).lower()}")
        elif isinstance(value, (int, float)):
            lines.append(f"{key}: {value}")
        else:
            lines.append(f"{key}: {value}")
    lines.append("---")
    return "\n".join(lines)


def validate_metadata(metadata: Dict[str, Any]) -> List[str]:
    """校验元数据是否满足必填字段要求。"""
    errors = []
    for field in REQUIRED_FIELDS:
        if field not in metadata:
            errors.append(f"缺少必填字段: {field}")
        else:
            value = metadata[field]
            if field == "name" and (not isinstance(value, str) or not value.strip()):
                errors.append(f"字段 name 格式不正确")
            if field == "version" and (not isinstance(value, str) or not re.match(r"^\d+\.\d+\.\d+$", str(value))):
                errors.append(f"字段 version 格式不正确，应为 x.y.z")
            if field == "description" and (not isinstance(value, str) or not value.strip()):
                errors.append(f"字段 description 格式不正确")
    return errors


def read_file(path: Path) -> str:
    """读取文件内容，失败时抛出 E003。"""
    try:
        return path.read_text(encoding="utf-8")
    except Exception as e:
        error_exit("E003", f"读取文件 {path} 失败: {e}")


def write_file(path: Path, content: str) -> None:
    """写入文件内容，失败时抛出 E003。"""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    except Exception as e:
        error_exit("E003", f"写入文件 {path} 失败: {e}")


def convert_content(content: str, source_format: str, target_format: str) -> str:
    """
    将技能包内容从一种格式转换为另一种格式。
    支持 md <-> json / yaml。
    """
    if source_format == target_format:
        error_exit("E007", f"源格式与目标格式相同: {source_format}")

    # 解析源格式
    if source_format == "md":
        metadata, body = parse_frontmatter(content)
    elif source_format == "json":
        try:
            data = json.loads(content)
            metadata = data.get("metadata", {})
            body = data.get("body", "")
        except json.JSONDecodeError as e:
            error_exit("E004", f"JSON 解析失败: {e}")
    elif source_format == "yaml":
        # 简化 YAML 解析：仅处理 frontmatter 格式
        metadata, body = parse_frontmatter(content)
    else:
        error_exit("E004", f"不支持的源格式: {source_format}")

    # 校验元数据
    errors = validate_metadata(metadata)
    if errors:
        error_exit("E005", "; ".join(errors))

    # 转换为目标格式
    if target_format == "md":
        fm = build_frontmatter(metadata)
        return f"{fm}\n\n{body}" if body else fm
    elif target_format == "json":
        return json.dumps({"metadata": metadata, "body": body}, ensure_ascii=False, indent=2)
    elif target_format == "yaml":
        return build_frontmatter(metadata)
    else:
        error_exit("E004", f"不支持的目标格式: {target_format}")


def organize_file(path: Path, target_dir: Path, tag: Optional[str] = None) -> Path:
    """
    将单个技能包文件整理到目标目录结构。
    结构: target_dir/<tag>/<name>/<version>/<filename>
    """
    if not path.is_file():
        error_exit("E002", f"文件不存在: {path}")

    content = read_file(path)
    metadata, _ = parse_frontmatter(content)

    if "name" not in metadata or "version" not in metadata:
        error_exit("E008", f"文件缺少 name 或 version 字段: {path}")

    name = str(metadata["name"])
    version = str(metadata["version"])

    # 确定标签
    effective_tag = tag or str(metadata.get("tag", "general"))

    # 构建目标路径
    dest_dir = target_dir / effective_tag / name / version
    dest_path = dest_dir / path.name

    try:
        dest_dir.mkdir(parents=True, exist_ok=True)
        import shutil
        shutil.copy2(path, dest_path)
    except Exception as e:
        error_exit("E008", f"复制文件失败: {e}")

    return dest_path


def validate_file(path: Path) -> Tuple[bool, List[str]]:
    """校验单个技能包文件。"""
    if not path.is_file():
        return False, [f"路径不是文件: {path}"]

    content = read_file(path)
    ext = path.suffix.lower()

    metadata: Dict[str, Any] = {}
    if ext == ".md":
        metadata, _ = parse_frontmatter(content)
    elif ext == ".json":
        try:
            data = json.loads(content)
            metadata = data.get("metadata", {})
        except json.JSONDecodeError as e:
            return False, [f"JSON 解析失败: {e}"]
    elif ext == ".yaml" or ext == ".yml":
        metadata, _ = parse_frontmatter(content)
    else:
        return False, [f"不支持的文件格式: {ext}"]

    errors = validate_metadata(metadata)
    return len(errors) == 0, errors


def list_packages(directory: Path) -> List[Dict[str, str]]:
    """列出目录下的所有技能包。"""
    if not directory.is_dir():
        error_exit("E002", f"目录不存在: {directory}")

    packages = []
    for path in sorted(directory.rglob("*")):
        if path.is_file() and path.suffix.lower() in [".md", ".json", ".yaml", ".yml"]:
            content = read_file(path)
            metadata, _ = parse_frontmatter(content)
            if "name" in metadata and "version" in metadata:
                packages.append({
                    "name": str(metadata["name"]),
                    "version": str(metadata["version"]),
                    "path": str(path),
                })
    return packages


def run_selftest() -> int:
    """内置硬编码样例数据离线自检核心逻辑。"""
    print("运行自检...")

    # 测试数据：硬编码的 Markdown 技能包内容
    sample_md = """---
name: test-skill
version: 1.0.0
description: 测试技能包
tags: [test, demo]
---

# 测试技能包

这是一个用于自检的样例技能包。
"""

    # 测试 parse_frontmatter
    metadata, body = parse_frontmatter(sample_md)
    assert "name" in metadata, "解析 frontmatter 失败：缺少 name"
    assert metadata["name"] == "test-skill", "解析 frontmatter 失败：name 值错误"
    assert metadata["version"] == "1.0.0", "解析 frontmatter 失败：version 值错误"
    assert "tags" in metadata and isinstance(metadata["tags"], list), "解析 frontmatter 失败：tags 应为列表"
    assert len(body) > 0, "解析 frontmatter 失败：正文为空"
    print("  ✓ parse_frontmatter 通过")

    # 测试 validate_metadata
    valid_errors = validate_metadata(metadata)
    assert len(valid_errors) == 0, f"校验失败：{valid_errors}"
    invalid_meta = {"name": "x"}
    invalid_errors = validate_metadata(invalid_meta)
    assert len(invalid_errors) >= 2, "校验失败：缺少字段应产生至少2个错误"
    print("  ✓ validate_metadata 通过")

    # 测试 build_frontmatter + 往返转换
    rebuilt_fm = build_frontmatter(metadata)
    assert "name: test-skill" in rebuilt_fm, "重建 frontmatter 失败"
    assert "version: 1.0.0" in rebuilt_fm, "重建 frontmatter 失败"
    print("  ✓ build_frontmatter 通过")

    # 测试 convert_content: md -> json
    json_content = convert_content(sample_md, "md", "json")
    assert json_content is not None and len(json_content) > 0, "md 转 json 失败"
    json_data = json.loads(json_content)
    assert json_data["metadata"]["name"] == "test-skill", "md 转 json 元数据丢失"
    assert "body" in json_data, "md 转 json 正文丢失"
    print("  ✓ convert md->json 通过")

    # 测试 convert_content: json -> md
    md_back = convert_content(json_content, "json", "md")
    assert md_back is not None and len(md_back) > 0, "json 转 md 失败"
    assert "test-skill" in md_back, "json 转 md 内容丢失"
    print("  ✓ convert json->md 通过")

    # 测试 validate_file（通过临时文件）
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir) / "sample.md"
        tmp_path.write_text(sample_md, encoding="utf-8")
        is_valid, errors = validate_file(tmp_path)
        assert is_valid, f"文件校验失败：{errors}"
        print("  ✓ validate_file 通过")

        # 测试 organize_file
        target_dir = Path(tmpdir) / "organized"
        dest = organize_file(tmp_path, target_dir, tag="demo")
        assert dest.exists(), "组织文件失败：目标文件不存在"
        assert "demo" in str(dest), "组织文件失败：标签目录缺失"
        assert "test-skill" in str(dest), "组织文件失败：名称目录缺失"
        assert "1.0.0" in str(dest), "组织文件失败：版本目录缺失"
        print("  ✓ organize_file 通过")

        # 测试 list_packages
        packages = list_packages(target_dir)
        assert len(packages) >= 1, "列出包失败：应为至少1个包"
        assert packages[0]["name"] == "test-skill", "列出包失败：名称不匹配"
        print("  ✓ list_packages 通过")

    # 测试错误处理
    try:
        convert_content("invalid json", "json", "md")
        assert False, "应抛出 JSON 解析错误"
    except SystemExit:
        print("  ✓ 错误处理 E004 通过")

    print("所有自检通过 ✓")
    return 0


def cmd_organize(args: argparse.Namespace) -> int:
    """organize 子命令：整理技能包到统一目录结构。"""
    source = Path(args.source)
    target = Path(args.target)

    if not source.exists():
        error_exit("E002", f"源路径不存在: {source}")

    # 如果源是文件，直接整理
    if source.is_file():
        dest = organize_file(source, target, tag=args.tag)
        print(f"已整理: {source} -> {dest}")
        return 0

    # 如果源是目录，递归整理所有技能包文件
    if source.is_dir():
        count = 0
        for path in sorted(source.rglob("*")):
            if path.is_file() and path.suffix.lower() in [".md", ".json", ".yaml", ".yml"]:
                try:
                    dest = organize_file(path, target, tag=args.tag)
                    print(f"已整理: {path} -> {dest}")
                    count += 1
                except SystemExit:
                    print(f"跳过文件（缺少元数据）: {path}", file=sys.stderr)
        print(f"完成：共整理 {count} 个文件")
        return 0

    error_exit("E002", f"源路径既不是文件也不是目录: {source}")
    return 0


def cmd_convert(args: argparse.Namespace) -> int:
    """convert 子命令：批量转换格式。"""
    source = Path(args.source)
    target = Path(args.target)
    src_fmt = args.src_format.lower()
    dst_fmt = args.dst_format.lower()

    if src_fmt not in VALID_FORMATS:
        error_exit("E004", f"不支持的源格式: {src_fmt}")
    if dst_fmt not in VALID_FORMATS:
        error_exit("E004", f"不支持的目标格式: {dst_fmt}")

    if not source.exists():
        error_exit("E002", f"源路径不存在: {source}")

    # 处理单个文件
    if source.is_file():
        content = read_file(source)
        result = convert_content(content, src_fmt, dst_fmt)
        write_file(target, result)
        print(f"已转换: {source} -> {target}")
        return 0

    # 处理目录（批量转换）
    if source.is_dir():
        if not target.is_dir():
            target.mkdir(parents=True, exist_ok=True)
        count = 0
        for path in sorted(source.rglob("*")):
            if path.is_file() and path.suffix.lower() in [".md", ".json", ".yaml", ".yml"]:
                content = read_file(path)
                try:
                    result = convert_content(content, src_fmt, dst_fmt)
                    # 构建目标文件名
                    new_name = path.stem + "." + dst_fmt
                    dest_path = target / path.relative_to(source).parent / new_name
                    write_file(dest_path, result)
                    print(f"已转换: {path} -> {dest_path}")
                    count += 1
                except SystemExit:
                    print(f"跳过文件（校验失败）: {path}", file=sys.stderr)
        print(f"完成：共转换 {count} 个文件")
        return 0

    error_exit("E002", f"源路径既不是文件也不是目录: {source}")
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    """validate 子命令：校验技能包格式。"""
    path = Path(args.path)

    if not path.exists():
        error_exit("E002", f"路径不存在: {path}")

    if path.is_file():
        is_valid, errors = validate_file(path)
        if is_valid:
            print(f"校验通过: {path}")
            return 0
        else:
            print(f"校验失败: {path}", file=sys.stderr)
            for err in errors:
                print(f"  - {err}", file=sys.stderr)
            return 1

    if path.is_dir():
        total = 0
        passed = 0
        for p in sorted(path.rglob("*")):
            if p.is_file() and p.suffix.lower() in [".md", ".json", ".yaml", ".yml"]:
                total += 1
                is_valid, errors = validate_file(p)
                if is_valid:
                    passed += 1
                    print(f"校验通过: {p}")
                else:
                    print(f"校验失败: {p}", file=sys.stderr)
                    for err in errors:
                        print(f"  - {err}", file=sys.stderr)
        print(f"校验结果: {passed}/{total} 通过")
        return 0 if passed == total else 1

    error_exit("E002", f"路径既不是文件也不是目录: {path}")
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    """list 子命令：列出目录下的所有技能包。"""
    directory = Path(args.directory)
    packages = list_packages(directory)
    if not packages:
        print("未找到技能包")
        return 0

    print(f"找到 {len(packages)} 个技能包:")
    for pkg in packages:
        print(f"  - {pkg['name']} v{pkg['version']} @ {pkg['path']}")
    return 0


def main() -> int:
    """主入口函数。"""
    parser = argparse.ArgumentParser(
        prog="openpackage",
        description="技能包收纳、组织、分发、批量转换与格式校验工具",
        epilog="示例: openpackage organize ./src ./dist --tag general",
    )
    parser.add_argument("--version", action="version", version="openpackage 1.0.2")
    parser.add_argument("--selftest", action="store_true", help="运行离线自检")

    subparsers = parser.add_subparsers(dest="command", help="子命令")

    # organize 子命令
    org_parser = subparsers.add_parser("organize", help="整理技能包到统一目录结构")
    org_parser.add_argument("source", help="源文件或目录路径")
    org_parser.add_argument("target", help="目标目录路径")
    org_parser.add_argument("--tag", default=None, help="覆盖标签（默认使用 frontmatter 中的 tag 字段）")

    # convert 子命令
    conv_parser = subparsers.add_parser("convert", help="批量转换技能包格式")
    conv_parser.add_argument("source", help="源文件或目录路径")
    conv_parser.add_argument("target", help="目标文件或目录路径")
    conv_parser.add_argument("--src-format", required=True, choices=VALID_FORMATS, help="源格式")
    conv_parser.add_argument("--dst-format", required=True, choices=VALID_FORMATS, help="目标格式")

    # validate 子命令
    val_parser = subparsers.add_parser("validate", help="校验技能包格式")
    val_parser.add_argument("path", help="文件或目录路径")

    # list 子命令
    list_parser = subparsers.add_parser("list", help="列出目录下的技能包")
    list_parser.add_argument("directory", help="目录路径")

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        return run_selftest()

    # 无子命令时显示帮助
    if not args.command:
        parser.print_help()
        return 0

    # 分发到子命令处理函数
    try:
        if args.command == "organize":
            return cmd_organize(args)
        elif args.command == "convert":
            return cmd_convert(args)
        elif args.command == "validate":
            return cmd_validate(args)
        elif args.command == "list":
            return cmd_list(args)
        else:
            parser.print_help()
            return 0
    except SystemExit as e:
        # 保留 SystemExit 错误码
        raise e
    except Exception as e:
        error_exit("E010", str(e))
        return 0


if __name__ == "__main__":
    sys.exit(main())
