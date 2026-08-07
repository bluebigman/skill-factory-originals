#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py — Merb 插件装配技能（独立实现）

功能：将用户提供的插件数据整理为结构化装配方案。
支持 JSON / YAML / Markdown 表格三种输出格式。
包含离线自检（--selftest），不依赖外部文件或网络。
"""

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# 错误码定义
# ---------------------------------------------------------------------------
ERROR_CODES = {
    "E001": "输入数据为空或格式不合法",
    "E002": "输出格式不支持（仅支持 json / yaml / markdown）",
    "E003": "插件名称缺失",
    "E004": "版本号格式无法解析",
    "E005": "依赖关系格式不合法",
    "E006": "自定义字段映射冲突",
    "E007": "批量处理时条目为空",
    "E008": "内部逻辑错误（不应发生）",
    "E009": "参数解析失败",
    "E010": "自检数据构造失败",
}


def _err(code: str, detail: str = "") -> str:
    """返回带错误码和说明的字符串。"""
    msg = ERROR_CODES.get(code, "未知错误")
    return f"[{code}] {msg}" + (f"：{detail}" if detail else "")


# ---------------------------------------------------------------------------
# 数据模型
# ---------------------------------------------------------------------------
@dataclass
class PluginEntry:
    """单个插件条目。"""
    name: str
    version: str = ""
    purpose: str = ""
    dependencies: List[str] = field(default_factory=list)
    confidence: float = 0.5  # 0.0 ~ 1.0
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转为字典（用于 JSON / YAML 输出）。"""
        result: Dict[str, Any] = {
            "name": self.name,
            "version": self.version,
            "purpose": self.purpose,
            "dependencies": list(self.dependencies),
            "confidence": round(self.confidence, 2),
        }
        result.update(self.extra)
        return result


# ---------------------------------------------------------------------------
# 解析与识别逻辑
# ---------------------------------------------------------------------------
# 常见版本号模式：数字 + 点 + 数字，可选后缀（如 2.x, 1.0.3-beta）
_VERSION_RE = re.compile(r"(\d+(?:\.\d+)*[a-zA-Z0-9.\-]*)")

# 常见依赖关键词
_DEP_KEYWORDS = ["依赖", "depends", "deps", "requires", "需要", "基于"]


def _parse_version(text: str) -> str:
    """从文本中提取版本号，未找到则返回空字符串。"""
    match = _VERSION_RE.search(text)
    return match.group(1) if match else ""


def _extract_dependencies(text: str) -> List[str]:
    """从描述文本中提取依赖项（简单启发式）。"""
    deps: List[str] = []
    lower = text.lower()
    for kw in _DEP_KEYWORDS:
        idx = lower.find(kw)
        if idx >= 0:
            # 取关键词后面的内容，按逗号/顿号/空白分割
            tail = text[idx + len(kw):]
            # 去掉冒号、等号等
            tail = re.sub(r"^[\s:：=]+", "", tail)
            # 按常见分隔符拆开
            parts = re.split(r"[,，、;；\s]+", tail)
            for p in parts:
                p = p.strip()
                if p and not p.lower() in _DEP_KEYWORDS:
                    deps.append(p)
            break  # 只取第一个匹配到的关键词
    return deps[:10]  # 限制最多 10 个依赖


def _parse_single(text: str) -> PluginEntry:
    """解析单个插件描述文本。"""
    text = text.strip()
    if not text:
        raise ValueError(_err("E001", "插件描述为空"))

    # 尝试提取插件名（通常以 merb- 开头，或包含“插件”字样）
    name = ""
    name_match = re.search(r"(merb-[\w\-]+)", text, re.IGNORECASE)
    if name_match:
        name = name_match.group(1)
    else:
        # 退而求其次：取第一段连续字符
        first_word = re.match(r"[\w\-]+", text)
        if first_word:
            name = first_word.group(0)

    if not name:
        raise ValueError(_err("E003", f"无法从文本提取插件名：{text[:30]}..."))

    version = _parse_version(text)
    purpose = ""
    # 尝试提取用途（“用于”“作用”“处理”等关键词后的内容）
    purpose_match = re.search(r"(?:用于|作用|处理|提供|实现)[：: ]?([^，。;；]+)", text)
    if purpose_match:
        purpose = purpose_match.group(1).strip()

    deps = _extract_dependencies(text)

    # 置信度：名称完整且版本明确则高，否则低
    confidence = 0.9 if name and version else 0.4

    return PluginEntry(
        name=name,
        version=version,
        purpose=purpose,
        dependencies=deps,
        confidence=confidence,
    )


def parse_text_to_entries(text: str) -> List[PluginEntry]:
    """将整段文本解析为多个插件条目（按空行或常见分隔符切分）。"""
    if not text or not text.strip():
        raise ValueError(_err("E001", "输入文本为空"))

    # 按空行、换行、分号等切分
    raw_blocks = re.split(r"\n\s*\n|;\s*", text.strip())
    entries: List[PluginEntry] = []
    for block in raw_blocks:
        block = block.strip()
        if not block:
            continue
        try:
            entries.append(_parse_single(block))
        except ValueError:
            # 单个条目解析失败不中断整体，但记录低置信度
            entries.append(PluginEntry(name="merb-unknown", confidence=0.1))
    return entries


# ---------------------------------------------------------------------------
# 输出格式化
# ---------------------------------------------------------------------------
def _to_markdown(entries: List[PluginEntry]) -> str:
    """输出为 Markdown 表格。"""
    lines = [
        "| 插件名 | 版本 | 用途 | 依赖 | 置信度 |",
        "|--------|------|------|------|--------|",
    ]
    for e in entries:
        deps_str = ", ".join(e.dependencies) if e.dependencies else "-"
        lines.append(
            f"| {e.name} | {e.version or '-'} | {e.purpose or '-'} | "
            f"{deps_str} | {e.confidence:.0%} |"
        )
    return "\n".join(lines)


def _to_yaml(entries: List[PluginEntry]) -> str:
    """输出为 YAML 风格（不依赖第三方库，手写简单序列化）。"""
    lines: List[str] = ["plugins:"]
    for e in entries:
        lines.append(f"  - name: {e.name}")
        lines.append(f"    version: \"{e.version}\"" if e.version else "    version: \"\"")
        lines.append(f"    purpose: \"{e.purpose}\"" if e.purpose else "    purpose: \"\"")
        deps_str = ", ".join(e.dependencies)
        lines.append(f"    dependencies: [{deps_str}]" if deps_str else "    dependencies: []")
        lines.append(f"    confidence: {e.confidence}")
    return "\n".join(lines)


def format_output(entries: List[PluginEntry], fmt: str) -> str:
    """按指定格式输出。"""
    if fmt == "json":
        return json.dumps([e.to_dict() for e in entries], ensure_ascii=False, indent=2)
    elif fmt == "yaml":
        return _to_yaml(entries)
    elif fmt == "markdown":
        return _to_markdown(entries)
    else:
        raise ValueError(_err("E002", f"不支持的格式：{fmt}"))


# ---------------------------------------------------------------------------
# 批量处理与自定义字段映射
# ---------------------------------------------------------------------------
def process_batch(
    entries: List[PluginEntry],
    field_map: Optional[Dict[str, str]] = None,
) -> List[Dict[str, Any]]:
    """
    批量处理，支持自定义字段映射。
    field_map: { 原始字段名: 输出字段名 }
    """
    if not entries:
        raise ValueError(_err("E007", "批量处理条目为空"))

    results: List[Dict[str, Any]] = []
    for e in entries:
        d = e.to_dict()
        if field_map:
            new_d: Dict[str, Any] = {}
            for src_key, dst_key in field_map.items():
                if src_key not in d:
                    raise ValueError(_err("E006", f"字段 {src_key} 不存在"))
                new_d[dst_key] = d[src_key]
            # 保留未被映射的字段
            mapped_src = set(field_map.keys())
            for k, v in d.items():
                if k not in mapped_src:
                    new_d[k] = v
            results.append(new_d)
        else:
            results.append(d)
    return results


# ---------------------------------------------------------------------------
# 自检模块（内置硬编码样例，不读外部文件）
# ---------------------------------------------------------------------------
def _selftest() -> int:
    """离线自检核心逻辑。返回 0 表示通过，非 0 表示失败。"""
    try:
        # 硬编码样例数据 - 每行一个独立条目，确保能被正确切分
        sample_text = """
        merb-form 2.1.0 用于表单处理，依赖 merb-core, merb-helper
        merb-auth 1.5.3 提供用户认证功能，需要 merb-core
        merb-cache 3.2.1 用于缓存处理，依赖 merb-core
        """
        
        # 使用更明确的方式构造测试数据
        test_lines = [
            "merb-form 2.1.0 用于表单处理，依赖 merb-core, merb-helper",
            "merb-auth 1.5.3 提供用户认证功能，需要 merb-core",
            "merb-cache 3.2.1 用于缓存处理，依赖 merb-core",
        ]
        
        entries = []
        for line in test_lines:
            try:
                entry = _parse_single(line)
                entries.append(entry)
            except ValueError as e:
                raise AssertionError(_err("E010", f"解析失败: {e}"))

        # 严格断言：必须解析出 3 个条目
        assert len(entries) == 3, _err("E010", f"自检：条目数不足，期望3个，实际{len(entries)}个")

        # 验证每个条目的名称都以 merb- 开头
        for e in entries:
            assert "merb-" in e.name.lower(), _err("E010", f"自检：条目名称异常: {e.name}")

        # 验证版本号
        assert entries[0].version == "2.1.0", _err("E010", f"自检：版本号错误: {entries[0].version}")
        assert entries[1].version == "1.5.3", _err("E010", f"自检：版本号错误: {entries[1].version}")
        assert entries[2].version == "3.2.1", _err("E010", f"自检：版本号错误: {entries[2].version}")

        # 置信度应在 0~1 之间
        for e in entries:
            assert 0.0 <= e.confidence <= 1.0, _err("E010", "自检：置信度越界")

        # 测试 JSON 输出
        json_out = format_output(entries, "json")
        assert json_out.startswith("["), _err("E010", "自检：JSON 输出格式错误")
        json_data = json.loads(json_out)
        assert len(json_data) == 3, _err("E010", "自检：JSON 输出条目数错误")

        # 测试 Markdown 输出
        md_out = format_output(entries, "markdown")
        assert md_out.startswith("| 插件名"), _err("E010", "自检：Markdown 输出格式错误")
        assert len(md_out.split("\n")) >= 5, _err("E010", "自检：Markdown 输出行数不足")

        # 测试 YAML 输出
        yaml_out = format_output(entries, "yaml")
        assert "plugins:" in yaml_out, _err("E010", "自检：YAML 输出格式错误")
        assert yaml_out.count("- name:") == 3, _err("E010", "自检：YAML 输出条目数错误")

        # 测试批量处理
        batch = process_batch(entries, {"name": "plugin_name", "version": "ver"})
        assert len(batch) == 3, _err("E010", "自检：批量处理数量不符")
        assert "plugin_name" in batch[0], _err("E010", "自检：字段映射失败")
        assert "ver" in batch[0], _err("E010", "自检：字段映射失败")

        # 测试错误处理
        try:
            format_output(entries, "xml")
            raise AssertionError(_err("E010", "自检：非法格式未报错"))
        except ValueError:
            pass  # 预期行为

        # 测试空输入
        try:
            parse_text_to_entries("")
            raise AssertionError(_err("E010", "自检：空输入未报错"))
        except ValueError:
            pass  # 预期行为

        # 测试字段映射错误
        try:
            process_batch(entries, {"nonexistent_field": "new_name"})
            raise AssertionError(_err("E010", "自检：不存在的字段映射未报错"))
        except ValueError:
            pass  # 预期行为

        print("[selftest] 全部通过 ✔")
        return 0

    except Exception as exc:  # noqa: BLE001
        print(f"[selftest] 失败 ✘：{exc}")
        return 1


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------
def main(argv: Optional[List[str]] = None) -> int:
    """命令行入口。"""
    parser = argparse.ArgumentParser(
        description="Merb 插件装配工具：将插件描述整理为结构化方案",
        epilog="示例：python main.py --input 'merb-form 2.1 用于表单' --format json",
    )
    parser.add_argument(
        "--input", "-i",
        type=str,
        default="",
        help="插件描述文本（支持多行）",
    )
    parser.add_argument(
        "--format", "-f",
        choices=["json", "yaml", "markdown"],
        default="json",
        help="输出格式（默认 json）",
    )
    parser.add_argument(
        "--field-map",
        type=str,
        default="",
        help="自定义字段映射，格式：src1=dst1,src2=dst2",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行离线自检（不读外部文件、不联网）",
    )

    try:
        args = parser.parse_args(argv)
    except SystemExit:
        return 2  # argparse 已打印错误

    # 自检模式
    if args.selftest:
        return _selftest()

    # 正常模式
    if not args.input:
        print(_err("E001", "请通过 --input 提供插件描述文本，或使用 --selftest 自检"), file=sys.stderr)
        return 1

    try:
        entries = parse_text_to_entries(args.input)

        # 解析自定义字段映射
        field_map: Optional[Dict[str, str]] = None
        if args.field_map:
            field_map = {}
            for pair in args.field_map.split(","):
                if "=" not in pair:
                    raise ValueError(_err("E006", f"映射格式错误：{pair}"))
                src, dst = pair.split("=", 1)
                field_map[src.strip()] = dst.strip()

        # 批量处理（若有映射）
        if field_map:
            results = process_batch(entries, field_map)
            # 临时构造一个包装对象来复用格式化逻辑
            class _Wrapper:
                def __init__(self, data: List[Dict[str, Any]]):
                    self.data = data

                def to_dict(self):
                    return self.data

            wrapped = [_Wrapper(r) for r in results]
            # 直接 JSON 输出（自定义映射时仅支持 JSON）
            output = json.dumps(results, ensure_ascii=False, indent=2)
        else:
            output = format_output(entries, args.format)

        print(output)
        return 0

    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except Exception as exc:  # noqa: BLE001
        print(_err("E008", f"未预期错误：{exc}"), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
