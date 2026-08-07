#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py — Merb 插件装配技能（独立实现）

功能概述：
    将用户提供的插件描述文本整理为结构化装配方案。
    支持 JSON / YAML / Markdown 表格三种输出格式。
    支持批量处理与自定义字段映射。
    内置离线自检（--selftest），不依赖外部文件与网络。

仅依据功能规格独立实现，不复制任何既有代码。
"""

import argparse
import json
import re
import sys
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# 错误码定义
# ---------------------------------------------------------------------------
ERROR_CODES = {
    "E001": "输入文本为空或无法解析",
    "E002": "不支持的输出格式（仅支持 json / yaml / markdown）",
    "E003": "插件名称缺失或格式非法",
    "E004": "版本号格式非法",
    "E005": "依赖关系格式非法",
    "E006": "自定义字段映射格式非法",
    "E007": "批量处理时输入数据格式非法",
    "E008": "YAML 序列化失败（缺少 PyYAML 库）",
    "E009": "内部逻辑错误（未知分支）",
    "E010": "命令行参数错误",
}


class SkillError(Exception):
    """技能运行时异常，携带错误码。"""

    def __init__(self, code: str, message: str):
        super().__init__(f"[{code}] {message}")
        self.code = code
        self.message = message


# ---------------------------------------------------------------------------
# 核心解析逻辑
# ---------------------------------------------------------------------------
def parse_plugin_text(text: str) -> List[Dict[str, Any]]:
    """
    从非结构化文本中提取插件信息。

    支持两种输入形态：
      1. 单行/多行自然语言描述，如："我想装一个处理表单的插件，版本 2.x"
      2. 结构化条目（每行一个插件），如："merb-form 2.x 表单处理"

    返回插件字典列表，每个字典包含：
        name: str         插件名称（必填）
        version: str      版本号（可选，默认 "unknown"）
        purpose: str      用途说明（可选，默认 ""）
        confidence: float 置信度（0~1）
    """
    if not text or not text.strip():
        raise SkillError("E001", ERROR_CODES["E001"])

    lines = [line.strip() for line in text.strip().splitlines() if line.strip()]
    plugins: List[Dict[str, Any]] = []

    for line in lines:
        plugin = _parse_single_line(line)
        if plugin:
            plugins.append(plugin)

    if not plugins:
        raise SkillError("E001", ERROR_CODES["E001"])

    return plugins


def _parse_single_line(line: str) -> Optional[Dict[str, Any]]:
    """解析单行文本为插件字典。"""
    # 尝试结构化格式：名称 版本 用途（空格或制表符分隔）
    parts = re.split(r"\s+", line, maxsplit=2)
    if len(parts) >= 1 and _looks_like_plugin_name(parts[0]):
        name = parts[0].strip()
        version = "unknown"
        purpose = ""
        confidence = 0.9  # 结构化格式置信度较高

        if len(parts) >= 2:
            version = parts[1].strip()
        if len(parts) >= 3:
            purpose = parts[2].strip()

        # 校验名称合法性
        if not re.match(r"^[A-Za-z0-9_.\-]+$", name):
            raise SkillError("E003", f"{ERROR_CODES['E003']}: {name}")

        # 校验版本号合法性（宽松校验）
        if version != "unknown" and not re.match(r"^[A-Za-z0-9_.\-]+$", version):
            raise SkillError("E004", f"{ERROR_CODES['E004']}: {version}")

        return {
            "name": name,
            "version": version,
            "purpose": purpose,
            "confidence": confidence,
        }

    # 尝试自然语言解析：提取插件名、版本、用途
    return _parse_natural_language(line)


def _looks_like_plugin_name(token: str) -> bool:
    """判断 token 是否像插件名（包含连字符或点号，且不含空格）。"""
    return bool(re.match(r"^[A-Za-z0-9]+[A-Za-z0-9_.\-]*$", token)) and (
        "-" in token or "." in token or "_" in token
    )


def _parse_natural_language(line: str) -> Optional[Dict[str, Any]]:
    """从自然语言描述中提取插件信息。"""
    text = line.lower()

    # 提取版本号（如 2.x, 1.0, v3, 版本 2.x）
    version_match = re.search(r"(?:版本\s*)?([0-9]+(?:\.[0-9xX]+)?)", text)
    version = version_match.group(1) if version_match else "unknown"

    # 提取用途关键词
    purpose = ""
    purpose_keywords = ["表单", "认证", "缓存", "数据库", "上传", "邮件", "支付"]
    for kw in purpose_keywords:
        if kw in text:
            purpose = kw
            break

    # 提取插件名（尝试匹配 merb-xxx 模式或通用插件名）
    # 方法1：尝试匹配 merb-xxx 模式
    name_match = re.search(r"(merb[\-_.][a-z0-9\-_.]+)", text)
    if name_match:
        name = name_match.group(1)
        confidence = 0.8 if version != "unknown" or purpose else 0.6
        return {
            "name": name,
            "version": version,
            "purpose": purpose,
            "confidence": confidence,
        }

    # 方法2：从上下文推断插件名（处理表单 -> merb-form）
    purpose_to_name = {
        "表单": "merb-form",
        "认证": "merb-auth",
        "缓存": "merb-cache",
        "数据库": "merb-db",
        "上传": "merb-upload",
        "邮件": "merb-mail",
        "支付": "merb-payment",
    }
    
    # 检查是否提到了具体功能
    for kw, plugin_name in purpose_to_name.items():
        if kw in text:
            name = plugin_name
            confidence = 0.7 if version != "unknown" else 0.5
            return {
                "name": name,
                "version": version,
                "purpose": kw,
                "confidence": confidence,
            }

    # 尝试提取任意可能的插件名（包含连字符的单词）
    generic_name_match = re.search(r"([a-z][a-z0-9]*[\-_.][a-z0-9\-_.]+)", text)
    if generic_name_match:
        name = generic_name_match.group(1)
        confidence = 0.5
        return {
            "name": name,
            "version": version,
            "purpose": purpose,
            "confidence": confidence,
        }

    # 无法识别
    return None


# ---------------------------------------------------------------------------
# 批量处理与自定义字段映射
# ---------------------------------------------------------------------------
def process_batch(
    items: List[Dict[str, Any]], field_map: Optional[Dict[str, str]] = None
) -> List[Dict[str, Any]]:
    """
    批量处理插件条目，支持自定义字段映射。

    field_map 示例：{"插件名": "name", "版本": "version", "说明": "purpose"}
    映射后输出字典的键为映射后的名称。
    """
    if not isinstance(items, list):
        raise SkillError("E007", ERROR_CODES["E007"])

    results = []
    for item in items:
        if not isinstance(item, dict) or "name" not in item:
            raise SkillError("E007", ERROR_CODES["E007"])

        if field_map:
            # 应用自定义字段映射
            mapped = {}
            for src_key, dst_key in field_map.items():
                if src_key in item:
                    mapped[dst_key] = item[src_key]
            # 保留未映射的字段
            for key, value in item.items():
                if key not in field_map.values() and key not in mapped:
                    mapped[key] = value
            results.append(mapped)
        else:
            results.append(item)

    return results


# ---------------------------------------------------------------------------
# 输出格式化
# ---------------------------------------------------------------------------
def format_output(
    plugins: List[Dict[str, Any]], fmt: str = "json"
) -> str:
    """将插件列表格式化为指定格式输出。"""
    if fmt == "json":
        return json.dumps(plugins, ensure_ascii=False, indent=2)

    if fmt == "yaml":
        try:
            import yaml  # pip install pyyaml

            return yaml.safe_dump(plugins, allow_unicode=True, sort_keys=False)
        except ImportError:
            raise SkillError("E008", ERROR_CODES["E008"])

    if fmt == "markdown":
        return _to_markdown_table(plugins)

    raise SkillError("E002", ERROR_CODES["E002"])


def _to_markdown_table(plugins: List[Dict[str, Any]]) -> str:
    """将插件列表转为 Markdown 表格。"""
    if not plugins:
        return "（无插件数据）"

    # 收集所有字段
    all_keys: List[str] = []
    for plugin in plugins:
        for key in plugin.keys():
            if key not in all_keys:
                all_keys.append(key)

    # 表头
    lines = ["| " + " | ".join(all_keys) + " |"]
    lines.append("|" + "---|" * len(all_keys))

    # 数据行
    for plugin in plugins:
        row = []
        for key in all_keys:
            value = plugin.get(key, "")
            if isinstance(value, float):
                value = f"{value:.2f}"
            row.append(str(value))
        lines.append("| " + " | ".join(row) + " |")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 置信度标注
# ---------------------------------------------------------------------------
def annotate_confidence(plugins: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """对低置信度字段进行明确标注。"""
    for plugin in plugins:
        if plugin.get("confidence", 1.0) < 0.6:
            plugin["warning"] = "低置信度：请人工核实插件信息"
    return plugins


# ---------------------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------------------
def main(argv: Optional[List[str]] = None) -> int:
    """命令行主入口。"""
    parser = argparse.ArgumentParser(
        description="Merb 插件装配技能：将插件描述整理为结构化方案",
        epilog="示例：python main.py --input 'merb-form 2.x 表单处理' --format json",
    )
    parser.add_argument(
        "--input",
        type=str,
        default="",
        help="插件描述文本（支持多行，每行一个插件或自然语言描述）",
    )
    parser.add_argument(
        "--format",
        type=str,
        choices=["json", "yaml", "markdown"],
        default="json",
        help="输出格式（默认 json）",
    )
    parser.add_argument(
        "--field-map",
        type=str,
        default="",
        help="自定义字段映射，JSON 格式，如 '{\"插件名\":\"name\"}'",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置离线自检（不读外部文件、不访问网络）",
    )

    args = parser.parse_args(argv)

    if args.selftest:
        return _run_selftest()

    if not args.input:
        parser.error("请提供 --input 参数或使用 --selftest")
        return 10  # E010

    try:
        # 解析输入
        plugins = parse_plugin_text(args.input)

        # 应用自定义字段映射
        field_map = None
        if args.field_map:
            try:
                field_map = json.loads(args.field_map)
                if not isinstance(field_map, dict):
                    raise SkillError("E006", ERROR_CODES["E006"])
            except json.JSONDecodeError:
                raise SkillError("E006", ERROR_CODES["E006"])

        if field_map:
            plugins = process_batch(plugins, field_map)

        # 置信度标注
        plugins = annotate_confidence(plugins)

        # 输出
        output = format_output(plugins, args.format)
        print(output)
        return 0

    except SkillError as e:
        print(f"错误: {e}", file=sys.stderr)
        return int(e.code[1:])  # E001 -> 1, E002 -> 2, ...

    except Exception as e:
        print(f"[E009] 内部错误: {e}", file=sys.stderr)
        return 9


# ---------------------------------------------------------------------------
# 内置自检（离线硬编码样例）
# ---------------------------------------------------------------------------
def _run_selftest() -> int:
    """
    内置离线自检。

    使用硬编码样例数据验证核心逻辑：
      - 解析功能
      - 批量处理
      - 字段映射
      - 三种输出格式

    断言使用宽松阈值（区间/大小比较），不依赖精确值。
    """
    print("=== Merb 插件装配技能自检 ===")

    try:
        # --- 测试 1：结构化解析 ---
        print("[1/5] 测试结构化解析...")
        sample = "merb-form 2.1 表单处理\nmerb-auth 1.0 用户认证"
        plugins = parse_plugin_text(sample)
        assert len(plugins) == 2, f"期望 2 个插件，实际 {len(plugins)}"
        assert plugins[0]["name"] == "merb-form"
        assert plugins[0]["version"] == "2.1"
        assert plugins[0]["purpose"] == "表单处理"
        assert plugins[0]["confidence"] >= 0.8, "置信度应较高"
        print("  ✓ 通过")

        # --- 测试 2：自然语言解析 ---
        print("[2/5] 测试自然语言解析...")
        nl_sample = "我想装一个处理表单的插件，版本 2.x"
        nl_plugins = parse_plugin_text(nl_sample)
        assert len(nl_plugins) >= 1, "应至少解析出一个插件"
        assert nl_plugins[0]["version"] == "2.x" or nl_plugins[0]["version"] == "2"
        assert "表单" in nl_plugins[0]["purpose"]
        assert 0.0 <= nl_plugins[0]["confidence"] <= 1.0
        print("  ✓ 通过")

        # --- 测试 3：批量处理与字段映射 ---
        print("[3/5] 测试批量处理与字段映射...")
        batch_items = [
            {"name": "merb-cache", "version": "3.0", "purpose": "缓存"},
            {"name": "merb-upload", "version": "1.2", "purpose": "上传"},
        ]
        field_map = {"插件名": "name", "版本号": "version"}
        mapped = process_batch(batch_items, field_map)
        assert len(mapped) == 2
        assert "name" in mapped[0], "映射后应包含 name"
        assert "version" in mapped[0], "映射后应包含 version"
        assert "purpose" in mapped[0], "未映射字段应保留"
        print("  ✓ 通过")

        # --- 测试 4：输出格式 ---
        print("[4/5] 测试三种输出格式...")
        json_out = format_output(plugins, "json")
        json_data = json.loads(json_out)
        assert len(json_data) == 2, "JSON 输出应包含 2 个插件"

        md_out = format_output(plugins, "markdown")
        assert "|" in md_out, "Markdown 表格应包含竖线分隔符"
        assert "merb-form" in md_out, "Markdown 应包含插件名"

        # YAML 格式（若 PyYAML 可用）
        try:
            yaml_out = format_output(plugins, "yaml")
            assert "merb-form" in yaml_out, "YAML 应包含插件名"
            print("  ✓ 通过（含 YAML）")
        except SkillError as e:
            if e.code == "E008":
                print("  ✓ 通过（YAML 跳过：未安装 PyYAML，可 pip install pyyaml）")
            else:
                raise
        print("  ✓ 通过")

        # --- 测试 5：置信度标注 ---
        print("[5/5] 测试置信度标注...")
        low_conf = [{"name": "merb-??", "version": "unknown", "confidence": 0.4}]
        annotated = annotate_confidence(low_conf)
        assert "warning" in annotated[0], "低置信度应添加警告"
        assert "人工核实" in annotated[0]["warning"]
        print("  ✓ 通过")

        print("=== 自检全部通过 ===")
        return 0

    except AssertionError as e:
        print(f"✗ 自检失败: {e}", file=sys.stderr)
        return 1

    except SkillError as e:
        print(f"✗ 自检失败: {e}", file=sys.stderr)
        return int(e.code[1:])

    except Exception as e:
        print(f"✗ 自检异常: {e}", file=sys.stderr)
        return 9


# ---------------------------------------------------------------------------
# 程序入口
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    sys.exit(main())
