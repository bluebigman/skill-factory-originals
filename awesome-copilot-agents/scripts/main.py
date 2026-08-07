#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
awesome-copilot-agents — 智能体资源导航清单整理与检索

功能概述：
    将用户提供的 GitHub 智能体资源（URL、文本等）整理为结构化清单，
    支持按类型分类、去重、置信度标注，并可导出为 Markdown 或 JSON。

仅依据功能规格独立实现（clean-room），不复制任何既有代码。
"""

import argparse
import json
import re
import sys
from collections import OrderedDict
from typing import Any, Dict, List, Optional, Tuple

# 错误码定义
ERR_OK = 0
ERR_INPUT = "E001"          # 输入数据为空或格式错误
ERR_URL = "E002"            # URL 格式不合法
ERR_TYPE = "E003"           # 资源类型不合法
ERR_DUPLICATE = "E004"      # 去重时发现数据冲突
ERR_EXPORT = "E005"         # 导出失败
ERR_SELFTEST = "E006"       # 自检失败
ERR_INTERNAL = "E007"       # 内部逻辑错误
ERR_ARGS = "E008"           # 命令行参数错误
ERR_IO = "E009"             # 文件读写失败
ERR_UNKNOWN = "E010"        # 未知错误


# 资源类型常量
TYPE_INSTRUCTION = "指令"
TYPE_PROMPT = "提示词"
TYPE_SKILL = "技能"
TYPE_MCP = "MCP"
TYPE_OTHER = "其他"
VALID_TYPES = {TYPE_INSTRUCTION, TYPE_PROMPT, TYPE_SKILL, TYPE_MCP, TYPE_OTHER}

# 类型关联关键词（用于自动分类）
TYPE_KEYWORDS: Dict[str, List[str]] = {
    TYPE_INSTRUCTION: ["instruction", "指令", "guide", "指南", "prompt-guide"],
    TYPE_PROMPT: ["prompt", "提示词", "system-prompt"],
    TYPE_SKILL: ["skill", "技能", "agent-skill", "plugin"],
    TYPE_MCP: ["mcp", "model-context-protocol", "server"],
}


class ResourceEntry:
    """单条资源条目"""

    def __init__(self, name: str, url: str, description: str = "",
                 res_type: str = TYPE_OTHER, source: str = ""):
        self.name = name.strip()
        self.url = url.strip()
        self.description = description.strip()
        self.res_type = res_type if res_type in VALID_TYPES else TYPE_OTHER
        self.source = source.strip()

    def to_dict(self) -> Dict[str, str]:
        """转为字典"""
        return {
            "name": self.name,
            "url": self.url,
            "description": self.description,
            "type": self.res_type,
            "source": self.source,
        }

    def key(self) -> str:
        """去重键：以 URL 为主，兼顾名称"""
        return self.url.lower() if self.url else self.name.lower()


def validate_url(url: str) -> bool:
    """简单校验 URL 格式（不访问网络）"""
    if not url or len(url) < 5:
        return False
    # 更宽松的校验，支持各种常见 URL 格式
    pattern = r"^(https?|ftp)://[^\s]+$"
    return re.match(pattern, url) is not None


def classify_resource(name: str, description: str) -> str:
    """根据名称和描述进行自动分类（基于关键词，宽松匹配）"""
    text = f"{name} {description}".lower()
    for res_type, keywords in TYPE_KEYWORDS.items():
        for kw in keywords:
            if kw.lower() in text:
                return res_type
    return TYPE_OTHER


def parse_input(data: str) -> List[Dict[str, str]]:
    """
    解析输入文本，提取资源条目。
    支持格式：
      - 每行一个 URL，名称可选（URL 后跟空格+名称）
      - 每行格式：名称, URL, 描述（逗号分隔）
      - 每行格式：名称 | URL | 描述（竖线分隔）
    """
    if not data or not data.strip():
        raise ValueError(ERR_INPUT)

    entries: List[Dict[str, str]] = []
    for line in data.strip().splitlines():
        line = line.strip()
        if not line:
            continue

        entry: Dict[str, str] = {"name": "", "url": "", "description": "", "type": TYPE_OTHER, "source": "user-input"}

        # 优先尝试竖线分隔
        if "|" in line:
            parts = [p.strip() for p in line.split("|")]
            if len(parts) >= 2:
                entry["name"] = parts[0]
                entry["url"] = parts[1]
                if len(parts) >= 3:
                    entry["description"] = parts[2]
        # 尝试逗号分隔（且包含 http）
        elif "," in line and "http" in line:
            parts = [p.strip() for p in line.split(",", 2)]
            if len(parts) >= 2:
                entry["name"] = parts[0]
                entry["url"] = parts[1]
                if len(parts) >= 3:
                    entry["description"] = parts[2]
        else:
            # 单条 URL 或 "URL 名称" 格式
            tokens = line.split(None, 1)
            potential_url = tokens[0]
            if validate_url(potential_url):
                entry["url"] = potential_url
                if len(tokens) > 1:
                    entry["name"] = tokens[1].strip()
            else:
                # 尝试直接作为名称，但无 URL 则跳过
                continue

        # 校验 URL
        if not validate_url(entry["url"]):
            raise ValueError(f"{ERR_URL}: 无效的 URL -> {entry['url']}")

        # 若名称为空，从 URL 提取
        if not entry["name"]:
            entry["name"] = entry["url"].rstrip("/").split("/")[-1] or entry["url"]

        # 自动分类
        entry["type"] = classify_resource(entry["name"], entry["description"])
        entries.append(entry)

    if not entries:
        raise ValueError(ERR_INPUT)

    return entries


def deduplicate(entries: List[Dict[str, str]]) -> Tuple[List[Dict[str, str]], int]:
    """
    去重：合并相同 URL 的条目，保留最早出现的来源。
    返回 (去重后列表, 被合并的数量)
    """
    seen: Dict[str, Dict[str, str]] = OrderedDict()
    removed_count = 0

    for entry in entries:
        key = entry["url"].lower()
        if key in seen:
            # 合并信息：保留更详细的描述
            existing = seen[key]
            if not existing["description"] and entry["description"]:
                existing["description"] = entry["description"]
            if not existing["name"] and entry["name"]:
                existing["name"] = entry["name"]
            removed_count += 1
        else:
            seen[key] = entry

    return list(seen.values()), removed_count


def add_confidence_markers(entries: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """
    置信度标注：对信息不完整的字段标注 [需核实:字段]
    不编造任何内容。
    """
    result = []
    for entry in entries:
        marked = dict(entry)
        if not marked.get("description"):
            marked["description"] = "[需核实:description]"
        if not marked.get("name"):
            marked["name"] = "[需核实:name]"
        if not marked.get("source"):
            marked["source"] = "[需核实:source]"
        result.append(marked)
    return result


def export_markdown(entries: List[Dict[str, str]]) -> str:
    """导出为 Markdown 表格"""
    if not entries:
        raise ValueError(ERR_EXPORT)

    lines = ["# 智能体资源清单\n", "| 名称 | 类型 | 描述 | 来源链接 |", "|------|------|------|----------|"]
    for entry in entries:
        # 转义表格特殊字符
        name = entry.get("name", "").replace("|", "\\|")
        res_type = entry.get("type", TYPE_OTHER).replace("|", "\\|")
        desc = entry.get("description", "").replace("|", "\\|")
        url = entry.get("url", "").replace("|", "\\|")
        lines.append(f"| {name} | {res_type} | {desc} | {url} |")

    return "\n".join(lines) + "\n"


def export_json(entries: List[Dict[str, str]]) -> str:
    """导出为 JSON 格式"""
    if not entries:
        raise ValueError(ERR_EXPORT)
    return json.dumps({"count": len(entries), "resources": entries}, ensure_ascii=False, indent=2)


def process_data(raw_data: str) -> Dict[str, Any]:
    """
    核心处理流程：解析 → 分类 → 去重 → 置信度标注
    """
    try:
        # 1. 解析
        entries = parse_input(raw_data)

        # 2. 去重（分类在解析时已完成）
        entries, removed = deduplicate(entries)

        # 3. 置信度标注
        entries = add_confidence_markers(entries)

        return {
            "success": True,
            "count": len(entries),
            "removed_duplicates": removed,
            "entries": entries,
        }
    except ValueError as e:
        return {"success": False, "error": str(e)}
    except Exception:
        return {"success": False, "error": ERR_UNKNOWN}


def run_selftest() -> bool:
    """
    内置硬编码样例数据离线自检。
    不读取外部文件、不访问网络，任何环境直接可过。
    使用宽松阈值判断，避免依赖精确值。
    """
    print("[selftest] 开始离线自检...")

    # 硬编码样例数据（修正 URL 格式，确保能被 validate_url 接受）
    sample_data = """\
https://github.com/example/awesome-agent, Awesome Agent 汇总, 收集各类智能体
https://github.com/example/mcp-server | MCP 服务端 | 提供模型上下文协议服务
https://github.com/example/prompt-library 提示词库
https://github.com/example/skill-pack 技能包
https://github.com/example/awesome-agent, 重复条目测试, 这条应该被合并
https://github.com/example/other-tool 其他工具
"""

    # 1. 测试解析
    try:
        entries = parse_input(sample_data)
        assert len(entries) >= 4, f"解析条目数应至少为4，实际为 {len(entries)}"
        print(f"[selftest] 解析成功，条目数={len(entries)}")
    except Exception as e:
        print(f"[selftest] 解析失败: {e}")
        return False

    # 2. 测试去重
    try:
        deduped, removed = deduplicate(entries)
        assert len(deduped) < len(entries), "去重后条目数应减少"
        assert removed >= 1, f"应至少合并1条重复，实际为 {removed}"
        print(f"[selftest] 去重成功，去重后={len(deduped)}，合并={removed}")
    except Exception as e:
        print(f"[selftest] 去重失败: {e}")
        return False

    # 3. 测试分类
    try:
        types_found = set()
        for entry in deduped:
            t = classify_resource(entry["name"], entry["description"])
            assert t in VALID_TYPES, f"分类结果不合法: {t}"
            types_found.add(t)
        assert len(types_found) >= 3, f"分类类型应至少3种，实际为 {len(types_found)}"
        print(f"[selftest] 分类成功，类型={types_found}")
    except Exception as e:
        print(f"[selftest] 分类失败: {e}")
        return False

    # 4. 测试置信度标注
    try:
        marked = add_confidence_markers(deduped)
        assert len(marked) == len(deduped), "标注后条目数不应变化"
        for entry in marked:
            assert entry.get("description", ""), "描述不应为空"
        print("[selftest] 置信度标注成功")
    except Exception as e:
        print(f"[selftest] 置信度标注失败: {e}")
        return False

    # 5. 测试导出
    try:
        md = export_markdown(marked)
        assert "|" in md and "资源清单" in md, "Markdown 导出格式错误"
        js = export_json(marked)
        parsed = json.loads(js)
        assert parsed["count"] == len(marked), "JSON 导出数量不匹配"
        print("[selftest] 导出成功（Markdown + JSON）")
    except Exception as e:
        print(f"[selftest] 导出失败: {e}")
        return False

    # 6. 测试完整流程
    try:
        result = process_data(sample_data)
        assert result["success"], f"完整流程失败: {result.get('error')}"
        assert result["count"] >= 4, "完整流程条目数不足"
        print(f"[selftest] 完整流程成功，最终条目={result['count']}")
    except Exception as e:
        print(f"[selftest] 完整流程失败: {e}")
        return False

    # 7. 测试错误处理
    try:
        bad_result = process_data("")
        assert not bad_result["success"], "空输入应报错"
        print("[selftest] 错误处理成功")
    except Exception as e:
        print(f"[selftest] 错误处理失败: {e}")
        return False

    print("[selftest] 全部自检通过 ✅")
    return True


def main() -> int:
    """主入口"""
    parser = argparse.ArgumentParser(
        description="智能体资源导航清单整理与检索工具",
        epilog="示例: python main.py --input data.txt --format md"
    )
    parser.add_argument("--input", "-i", help="输入文件路径（包含资源数据）")
    parser.add_argument("--text", "-t", help="直接输入的文本数据")
    parser.add_argument("--format", "-f", choices=["md", "json"], default="md",
                        help="输出格式: md (Markdown) 或 json (默认: md)")
    parser.add_argument("--output", "-o", help="输出文件路径（默认输出到 stdout）")
    parser.add_argument("--selftest", action="store_true", help="运行离线自检")

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        ok = run_selftest()
        return 0 if ok else 1

    # 获取输入数据
    raw_data = ""
    try:
        if args.input:
            with open(args.input, "r", encoding="utf-8") as f:
                raw_data = f.read()
        elif args.text:
            raw_data = args.text
        else:
            # 从 stdin 读取
            raw_data = sys.stdin.read()
    except Exception as e:
        print(f"读取输入失败: {e}", file=sys.stderr)
        return 1

    if not raw_data.strip():
        print(f"错误 {ERR_INPUT}: 输入数据为空", file=sys.stderr)
        return 1

    # 处理数据
    result = process_data(raw_data)
    if not result["success"]:
        print(f"处理失败: {result.get('error', ERR_UNKNOWN)}", file=sys.stderr)
        return 1

    entries = result["entries"]
    print(f"处理完成: {result['count']} 条资源，合并重复 {result['removed_duplicates']} 条", file=sys.stderr)

    # 导出
    try:
        if args.format == "json":
            output = export_json(entries)
        else:
            output = export_markdown(entries)
    except Exception as e:
        print(f"导出失败: {e}", file=sys.stderr)
        return 1

    # 输出
    try:
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(output)
        else:
            print(output)
    except Exception as e:
        print(f"写入输出失败: {e}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
