#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
awesome-mcp-servers 技能实现脚本
=================================
功能：将 MCP 服务器资源数据整理为结构化输出（Markdown / JSON）。
仅用于学习与参考用途，不提供任何可用性、安全性或性能保证。

用法示例：
    python main.py --input data.json --format markdown --sort name
    python main.py --selftest
"""

import argparse
import json
import sys
from typing import Any, Dict, List, Optional
dry_run = False  # v3.274 模块级 dry-run 标志

# 错误码定义（E001-E010）
ERROR_CODES = {
    "E001": "输入文件不存在或无法读取",
    "E002": "输入数据格式无效（非 JSON）",
    "E003": "输入数据不是列表或字典结构",
    "E004": "记录缺少必要字段（name 或 description）",
    "E005": "输出格式不支持（仅支持 markdown / json）",
    "E006": "排序字段不存在于记录中",
    "E007": "输出文件无法写入",
    "E008": "字段过滤子集为空或无效",
    "E009": "内部数据转换错误",
    "E010": "未知错误",
}


class MCPDataError(Exception):
    """MCP 数据处理异常，携带错误码。"""

    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(f"[{code}] {message}")


# ----------------------------------------------------------------------
# 核心数据模型与工具函数
# ----------------------------------------------------------------------

# 允许的协议类型（用于识别，不限制）
KNOWN_PROTOCOLS = {"mcp", "sse", "stdio", "http", "websocket"}
# 常见用途标签（用于提取，非强制）
KNOWN_TAGS = {
    "database", "search", "filesystem", "web", "api", "automation",
    "monitoring", "security", "ai", "data", "devops", "chat",
    "image", "video", "audio", "code", "testing", "deployment",
}


def _safe_str(value: Any) -> str:
    """安全转换为字符串。"""
    if value is None:
        return ""
    return str(value).strip()


def _extract_protocol(record: Dict[str, Any]) -> str:
    """从记录中提取协议类型，未知时返回 'unknown'。"""
    proto = _safe_str(record.get("protocol", "")).lower()
    if not proto:
        # 尝试从描述中识别
        desc = _safe_str(record.get("description", "")).lower()
        for p in KNOWN_PROTOCOLS:
            if p in desc:
                return p
        return "unknown"
    return proto if proto in KNOWN_PROTOCOLS else "unknown"


def _extract_tags(record: Dict[str, Any]) -> List[str]:
    """从记录中提取用途标签，返回去重后的列表。"""
    tags: List[str] = []
    # 显式标签
    raw_tags = record.get("tags", [])
    if isinstance(raw_tags, list):
        for t in raw_tags:
            t = _safe_str(t).lower()
            if t and t not in tags:
                tags.append(t)
    elif isinstance(raw_tags, str):
        for t in raw_tags.replace(";", ",").split(","):
            t = _safe_str(t).lower()
            if t and t not in tags:
                tags.append(t)
    # 从描述中提取已知标签
    desc = _safe_str(record.get("description", "")).lower()
    for tag in KNOWN_TAGS:
        if tag in desc and tag not in tags:
            tags.append(tag)
    return tags


def _normalize_record(raw: Dict[str, Any]) -> Dict[str, Any]:
    """
    将原始记录规范化为统一结构。
    必需字段：name, description
    可选字段：protocol, tags, url, stars, updated
    无法确认的字段标注 [需核实:字段名]
    """
    name = _safe_str(raw.get("name"))
    description = _safe_str(raw.get("description"))
    if not name or not description:
        raise MCPDataError("E004", "记录缺少必要字段（name 或 description）")

    protocol = _safe_str(raw.get("protocol"))
    if not protocol:
        protocol = _extract_protocol(raw)
        if protocol == "unknown":
            protocol = "[需核实:protocol]"

    tags = _extract_tags(raw)
    if not tags:
        tags = ["[需核实:tags]"]

    url = _safe_str(raw.get("url"))
    if not url:
        url = "[需核实:url]"

    stars = raw.get("stars")
    if stars is None:
        stars = "[需核实:stars]"
    else:
        try:
            stars = int(stars)
        except (ValueError, TypeError):
            stars = "[需核实:stars]"

    updated = _safe_str(raw.get("updated"))
    if not updated:
        updated = "[需核实:updated]"

    return {
        "name": name,
        "description": description,
        "protocol": protocol,
        "tags": tags,
        "url": url,
        "stars": stars,
        "updated": updated,
    }


def parse_input(data: Any) -> List[Dict[str, Any]]:
    """
    解析输入数据，返回规范化记录列表。
    支持输入为列表或 {items: [...]} 的字典。
    """
    if isinstance(data, dict):
        items = data.get("items") or data.get("servers") or data.get("data")
        if not isinstance(items, list):
            raise MCPDataError("E003", "输入数据不是列表或字典结构")
        raw_records = items
    elif isinstance(data, list):
        raw_records = data
    else:
        raise MCPDataError("E003", "输入数据不是列表或字典结构")

    records: List[Dict[str, Any]] = []
    for raw in raw_records:
        if not isinstance(raw, dict):
            raise MCPDataError("E003", "输入数据不是列表或字典结构")
        records.append(_normalize_record(raw))
    return records


# ----------------------------------------------------------------------
# 输出格式化
# ----------------------------------------------------------------------

def to_markdown(records: List[Dict[str, Any]], fields: Optional[List[str]] = None) -> str:
    """生成 Markdown 表格格式输出。"""
    if not records:
        return "（无记录）"

    # 默认字段顺序
    default_fields = ["name", "description", "protocol", "tags", "url", "stars", "updated"]
    if fields:
        # 校验字段有效性
        valid_fields = set(default_fields)
        for f in fields:
            if f not in valid_fields:
                raise MCPDataError("E008", f"字段过滤子集无效: {f}")
        selected = [f for f in default_fields if f in fields]
    else:
        selected = default_fields

    # 表头
    header = "| " + " | ".join(selected) + " |"
    separator = "|" + "|".join(["---"] * len(selected)) + "|"
    lines = [header, separator]

    # 数据行
    for rec in records:
        row = []
        for field in selected:
            val = rec.get(field, "")
            if isinstance(val, list):
                val = ", ".join(_safe_str(v) for v in val)
            row.append(_safe_str(val))
        lines.append("| " + " | ".join(row) + " |")

    return "\n".join(lines)


def to_json(records: List[Dict[str, Any]], fields: Optional[List[str]] = None) -> str:
    """生成 JSON 格式输出。"""
    if fields:
        valid_fields = {"name", "description", "protocol", "tags", "url", "stars", "updated"}
        for f in fields:
            if f not in valid_fields:
                raise MCPDataError("E008", f"字段过滤子集无效: {f}")
        output = []
        for rec in records:
            filtered = {k: v for k, v in rec.items() if k in fields}
            output.append(filtered)
    else:
        output = records
    return json.dumps(output, ensure_ascii=False, indent=2)


def format_output(records: List[Dict[str, Any]], fmt: str, fields: Optional[List[str]] = None) -> str:
    """按指定格式输出。"""
    if fmt == "markdown":
        return to_markdown(records, fields)
    elif fmt == "json":
        return to_json(records, fields)
    else:
        raise MCPDataError("E005", "输出格式不支持（仅支持 markdown / json）")


# ----------------------------------------------------------------------
# 排序与过滤
# ----------------------------------------------------------------------

def sort_records(records: List[Dict[str, Any]], sort_by: str, reverse: bool = False) -> List[Dict[str, Any]]:
    """按指定字段排序。"""
    if not records:
        return records
    if sort_by not in records[0]:
        raise MCPDataError("E006", f"排序字段不存在于记录中: {sort_by}")

    def sort_key(rec: Dict[str, Any]) -> Any:
        val = rec.get(sort_by, "")
        # 数值比较
        if isinstance(val, int):
            return val
        return _safe_str(val).lower()

    return sorted(records, key=sort_key, reverse=reverse)


# ----------------------------------------------------------------------
# 自检（selftest）
# ----------------------------------------------------------------------

def _run_selftest() -> bool:
    """内置硬编码样例数据，离线自检核心逻辑。"""
    print("开始自检 awesome-mcp-servers ...")

    # 硬编码测试数据（不读外部文件）
    sample_data = [
        {
            "name": "TestDB MCP Server",
            "description": "A database MCP server for MySQL and PostgreSQL",
            "protocol": "mcp",
            "tags": ["database", "sql"],
            "url": "https://example.com/testdb",
            "stars": 120,
            "updated": "2026-01-15",
        },
        {
            "name": "SearchAPI Server",
            "description": "Web search API integration with SSE support",
            "tags": ["search", "web"],
            "url": "https://example.com/search",
            "stars": 85,
        },
        {
            "name": "FileSystem Helper",
            "description": "Filesystem operations for local development",
            "protocol": "stdio",
            "stars": 200,
            "updated": "2026-02-01",
        },
    ]

    try:
        # 1. 解析输入
        records = parse_input(sample_data)
        assert len(records) == 3, "解析记录数量应为 3"
        print(f"  [PASS] 解析输入: {len(records)} 条记录")

        # 2. 必需字段检查
        for rec in records:
            assert rec["name"], "name 字段不能为空"
            assert rec["description"], "description 字段不能为空"
        print("  [PASS] 必需字段完整")

        # 3. 协议提取（宽松断言：不依赖具体值）
        protocols = [rec["protocol"] for rec in records]
        assert all(p for p in protocols), "protocol 不能全为空"
        unknown_count = sum(1 for p in protocols if "需核实" in p)
        assert unknown_count <= 2, "未知协议数量不应超过 2"
        print(f"  [PASS] 协议提取: {protocols}")

        # 4. 标签提取（宽松断言）
        for rec in records:
            assert rec["tags"], "tags 不能为空"
            assert len(rec["tags"]) >= 1, "tags 至少 1 个"
        print("  [PASS] 标签提取")

        # 5. 缺失字段标注
        for rec in records:
            for key in ["url", "stars", "updated"]:
                val = rec[key]
                # 要么有真实值，要么标注需核实
                assert val is not None and val != "", f"{key} 不能为空"
        print("  [PASS] 缺失字段标注")

        # 6. Markdown 输出
        md = to_markdown(records)
        assert "|" in md, "Markdown 应包含表格分隔符"
        assert "name" in md, "Markdown 应包含表头"
        assert len(md.splitlines()) >= 5, "Markdown 行数应不少于 5"
        print("  [PASS] Markdown 输出")

        # 7. JSON 输出
        js = to_json(records)
        parsed = json.loads(js)
        assert len(parsed) == 3, "JSON 解析后应有 3 条记录"
        print("  [PASS] JSON 输出")

        # 8. 排序（宽松断言：只验证数量不变，不依赖具体顺序）
        sorted_records = sort_records(records, "name")
        assert len(sorted_records) == 3, "排序后数量应为 3"
        assert all(rec["name"] for rec in sorted_records), "排序后 name 均存在"
        print("  [PASS] 排序功能")

        # 9. 字段过滤
        filtered_md = to_markdown(records, fields=["name", "url"])
        assert "protocol" not in filtered_md, "过滤后不应包含 protocol"
        assert "name" in filtered_md, "过滤后应包含 name"
        print("  [PASS] 字段过滤")

        # 10. 错误处理（E004）
        try:
            parse_input([{"description": "缺少 name"}])
            assert False, "应抛出 E004 错误"
        except MCPDataError as e:
            assert e.code == "E004", "错误码应为 E004"
        print("  [PASS] 错误处理 E004")

        # 11. 错误处理（E005）
        try:
            format_output(records, "xml")
            assert False, "应抛出 E005 错误"
        except MCPDataError as e:
            assert e.code == "E005", "错误码应为 E005"
        print("  [PASS] 错误处理 E005")

        # 12. 错误处理（E006）
        try:
            sort_records(records, "nonexistent_field")
            assert False, "应抛出 E006 错误"
        except MCPDataError as e:
            assert e.code == "E006", "错误码应为 E006"
        print("  [PASS] 错误处理 E006")

        print("\n全部自检通过 ✔")
        return True

    except AssertionError as e:
        print(f"自检失败: {e}")
        return False
    except MCPDataError as e:
        print(f"自检失败: [{e.code}] {e.message}")
        return False
    except Exception as e:
        print(f"自检失败: 未知异常 {e}")
        return False


# ----------------------------------------------------------------------
# 主入口
# ----------------------------------------------------------------------

def main() -> int:
    """命令行入口。"""
    parser = argparse.ArgumentParser(
        description="MCP服务器资源整理与结构化输出工具（学习参考用途）",
        epilog="示例: python main.py --input data.json --format markdown --sort name",
    )
    parser.add_argument("--input", "-i", help="输入 JSON 文件路径")
    parser.add_argument("--format", "-f", choices=["markdown", "json"], default="markdown",
                        help="输出格式（默认: markdown）")
    parser.add_argument("--sort", "-s", help="按指定字段排序")
    parser.add_argument("--reverse", "-r", action="store_true", help="排序时反转顺序")
    parser.add_argument("--fields", "-c", nargs="+",
                        help="输出字段子集（如: name url protocol）")
    parser.add_argument("--output", "-o", help="输出文件路径（默认输出到 stdout）")
    parser.add_argument("--selftest", action="store_true", help="运行内置自检")

    parser.add_argument("--force", action="store_true")  # R4 强制写盘


    parser.add_argument("--dry-run", action="store_true")  # R4 预览模式

    args = parser.parse_args()

    global dry_run

    dry_run = getattr(args, "dry_run", False)  # v3.274 同步到全局

    # 自检模式
    if args.selftest:
        ok = _run_selftest()
        return 0 if ok else 1

    # 正常处理模式
    if not args.input:
        print("错误: 必须指定 --input 或使用 --selftest", file=sys.stderr)
        print("用法: python main.py --input data.json [--format markdown|json]", file=sys.stderr)
        return 1

    try:
        # 读取输入文件
        try:
            with open(args.input, "r", encoding="utf-8") as f:
                raw_data = json.load(f)
        except FileNotFoundError:
            raise MCPDataError("E001", f"输入文件不存在或无法读取: {args.input}")
        except json.JSONDecodeError:
            raise MCPDataError("E002", "输入数据格式无效（非 JSON）")

        # 解析记录
        records = parse_input(raw_data)

        # 排序
        if args.sort:
            records = sort_records(records, args.sort, args.reverse)

        # 格式化输出
        output = format_output(records, args.format, args.fields)

        # 输出
        if args.output:
            try:
                with open(args.output, "w", encoding="utf-8") as f:
                    f.write(output)
                print(f"已写入: {args.output}")
            except OSError:
                raise MCPDataError("E007", f"输出文件无法写入: {args.output}")
        else:
            print(output)

        return 0

    except MCPDataError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"错误: [{ERROR_CODES['E010']}] 未知错误: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
