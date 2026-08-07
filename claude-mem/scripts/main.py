#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
claude-mem — 跨会话上下文持久化与压缩
=====================================
版本: 1.0.1
功能: 捕获、压缩、检索会话中的关键信息，支持 JSON / Markdown 输出。
"""

import argparse
import json
import re
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

# 错误码定义
ERROR_CODES = {
    "E001": "参数错误：缺少必要输入",
    "E002": "文件读取失败：文件不存在或不可读",
    "E003": "URL 获取失败：网络不可达或响应异常",
    "E004": "输入格式错误：无法解析为结构化文本",
    "E005": "输出格式错误：不支持的输出格式",
    "E006": "配置错误：自定义字段定义无效",
    "E007": "内部错误：处理流程异常",
    "E008": "批量处理错误：部分文件处理失败",
    "E009": "记忆检索错误：未找到匹配条目",
    "E010": "权限错误：写入目标无权限",
}

# 内置硬编码样例数据（用于 --selftest，不依赖外部文件）
SELFTEST_SAMPLE = [
    {
        "id": "sample-001",
        "text": "用户决定采用 Python 3.12 作为项目主语言，限制条件是不使用任何第三方框架。",
        "meta": {"source": "selftest", "timestamp": "2026-01-01T00:00:00Z"},
    },
    {
        "id": "sample-002",
        "text": "项目名称为 Atlas，核心模块为 memory-core 与 retrieval-api。",
        "meta": {"source": "selftest", "timestamp": "2026-01-02T00:00:00Z"},
    },
    {
        "id": "sample-003",
        "text": "用户偏好简洁文档风格，拒绝过度设计。",
        "meta": {"source": "selftest", "timestamp": "2026-01-03T00:00:00Z"},
    },
]

# 关键信息识别关键词（用于提取高价值信息）
KEYWORD_PATTERNS = {
    "decision": re.compile(r"(决定|采用|选择|确定|拒绝|同意|否决)", re.IGNORECASE),
    "constraint": re.compile(r"(限制|约束|条件|必须|不能|不允许|仅限)", re.IGNORECASE),
    "entity": re.compile(r"(项目|模块|系统|工具|语言|框架|库|服务)", re.IGNORECASE),
    "preference": re.compile(r"(偏好|喜欢|倾向|希望|期望|风格)", re.IGNORECASE),
    "task": re.compile(r"(待办|任务|计划|下一步|后续|需要完成)", re.IGNORECASE),
}


def _now_utc() -> str:
    """返回当前 UTC 时间字符串（ISO 格式）。"""
    return datetime.now(timezone.utc).isoformat()


def _generate_id() -> str:
    """生成唯一记忆条目 ID。"""
    return f"mem-{uuid.uuid4().hex[:12]}"


def parse_input(text: str, source: str = "text") -> dict:
    """
    输入结构化: 将原始文本解析为结构化字段。
    返回: {"id", "text", "source", "timestamp", "entities", "keywords"}
    """
    if not text or not text.strip():
        raise ValueError(ERROR_CODES["E001"])

    # 提取关键词
    keywords = set()
    for category, pattern in KEYWORD_PATTERNS.items():
        if pattern.search(text):
            keywords.add(category)

    # 简单实体提取（示例：提取引号中的内容或特定前缀）
    entities = []
    quoted = re.findall(r"[“\"']([^”\"']+)[”\"']", text)
    entities.extend(quoted)
    for m in re.finditer(r"(?:项目|模块|系统|工具|语言|框架|库|服务)[：:\s]*([A-Za-z0-9\-_]+)", text):
        entities.append(m.group(1))

    return {
        "id": _generate_id(),
        "text": text.strip(),
        "source": source,
        "timestamp": _now_utc(),
        "entities": list(set(entities)),
        "keywords": sorted(keywords),
    }


def identify_key_info(structured: dict) -> dict:
    """
    关键信息识别: 标记高价值信息并添加置信度。
    返回: {"confidence", "flagged_fields", "summary"}
    """
    text = structured.get("text", "")
    keywords = structured.get("keywords", [])

    # 置信度计算：基于关键词数量和实体丰富度（宽松规则）
    base_score = 0.3
    keyword_bonus = min(0.3, len(keywords) * 0.1)
    entity_bonus = min(0.2, len(structured.get("entities", [])) * 0.05)
    confidence = min(0.95, base_score + keyword_bonus + entity_bonus)

    # 标记不确定字段（示例：若缺少实体则标记）
    flagged = []
    if not structured.get("entities"):
        flagged.append("[需核实:entities]")

    # 生成摘要（前 80 字符 + 省略号）
    summary = text[:80] + ("..." if len(text) > 80 else "")

    return {
        "confidence": round(confidence, 2),
        "flagged_fields": flagged,
        "summary": summary,
    }


def format_output(entry: dict, fmt: str = "json") -> str:
    """
    格式约定输出: 按预设模板生成压缩后的记忆条目。
    支持 json / markdown 两种格式。
    """
    if fmt == "json":
        return json.dumps(entry, ensure_ascii=False, indent=2)
    elif fmt == "markdown":
        lines = [
            f"## 记忆条目: {entry['id']}",
            f"- **时间**: {entry['timestamp']}",
            f"- **来源**: {entry['source']}",
            f"- **置信度**: {entry.get('confidence', 'N/A')}",
            f"- **关键词**: {', '.join(entry.get('keywords', [])) or '无'}",
            f"- **实体**: {', '.join(entry.get('entities', [])) or '无'}",
            "",
            f"### 摘要",
            entry.get("summary", entry.get("text", "")),
            "",
            f"### 原文",
            entry.get("text", ""),
            "",
        ]
        if entry.get("flagged_fields"):
            lines.append("### 待核实")
            lines.extend(f"- {f}" for f in entry["flagged_fields"])
            lines.append("")
        return "\n".join(lines)
    else:
        raise ValueError(ERROR_CODES["E005"])


def process_text(text: str, fmt: str = "json", source: str = "text") -> dict:
    """
    核心处理流程: 输入 -> 结构化 -> 识别 -> 输出。
    """
    try:
        structured = parse_input(text, source=source)
        info = identify_key_info(structured)
        entry = {**structured, **info}
        entry["formatted"] = format_output(entry, fmt)
        return entry
    except ValueError as e:
        raise
    except Exception:
        raise RuntimeError(ERROR_CODES["E007"])


def process_file(filepath: str, fmt: str = "json") -> dict:
    """处理单个文件: 读取文本并压缩。"""
    path = Path(filepath)
    if not path.is_file():
        raise FileNotFoundError(ERROR_CODES["E002"])
    try:
        content = path.read_text(encoding="utf-8")
    except PermissionError:
        raise PermissionError(ERROR_CODES["E010"])
    except Exception:
        raise IOError(ERROR_CODES["E002"])
    return process_text(content, fmt=fmt, source=str(path))


def process_url(url: str, fmt: str = "json") -> dict:
    """处理 URL: 获取内容并压缩（仅标准库，简化实现）。"""
    # 标准库实现：使用 urllib（不引入第三方）
    from urllib.request import urlopen

    try:
        with urlopen(url, timeout=10) as resp:
            content = resp.read().decode("utf-8", errors="replace")
    except Exception:
        raise ConnectionError(ERROR_CODES["E003"])
    return process_text(content, fmt=fmt, source=url)


def batch_process(inputs: list, fmt: str = "json") -> list:
    """批量处理多个输入（文件路径或 URL）。"""
    results = []
    errors = []
    for item in inputs:
        try:
            if item.startswith(("http://", "https://")):
                results.append(process_url(item, fmt))
            else:
                results.append(process_file(item, fmt))
        except Exception as e:
            errors.append({"input": item, "error": str(e)})

    if errors:
        # 部分失败时返回结果 + 错误信息（不抛出，由调用方决定）
        results.append({"batch_errors": errors})
    return results


def search_memories(memories: list, query: str) -> list:
    """
    记忆检索: 基于关键词匹配返回相关条目。
    """
    if not memories:
        return []
    query_lower = query.lower()
    matched = []
    for mem in memories:
        text = mem.get("text", "").lower()
        if query_lower in text:
            matched.append(mem)
    return matched


# ---------- 自检（--selftest）----------
def run_selftest() -> int:
    """离线自检核心逻辑，使用内置硬编码数据，不依赖外部环境。"""
    print("[selftest] 开始自检...")
    passed = 0
    total = 0

    # 测试1: parse_input 基本结构化
    total += 1
    try:
        s = parse_input(SELFTEST_SAMPLE[0]["text"])
        assert s["text"], "文本不应为空"
        assert isinstance(s["entities"], list), "实体应为列表"
        assert isinstance(s["keywords"], list), "关键词应为列表"
        passed += 1
        print("[ok] parse_input")
    except Exception as e:
        print(f"[fail] parse_input: {e}")

    # 测试2: identify_key_info 置信度在合理区间
    total += 1
    try:
        s = parse_input(SELFTEST_SAMPLE[1]["text"])
        info = identify_key_info(s)
        # 宽松断言: 置信度在 0 到 1 之间
        assert 0.0 <= info["confidence"] <= 1.0, "置信度应在 [0,1]"
        assert isinstance(info["summary"], str), "摘要应为字符串"
        passed += 1
        print("[ok] identify_key_info")
    except Exception as e:
        print(f"[fail] identify_key_info: {e}")

    # 测试3: format_output 两种格式
    total += 2
    try:
        s = parse_input(SELFTEST_SAMPLE[2]["text"])
        info = identify_key_info(s)
        entry = {**s, **info}
        j = format_output(entry, "json")
        m = format_output(entry, "markdown")
        assert j.startswith("{"), "JSON 应以 { 开头"
        assert m.startswith("##"), "Markdown 应以 ## 开头"
        passed += 2
        print("[ok] format_output (json/markdown)")
    except Exception as e:
        print(f"[fail] format_output: {e}")

    # 测试4: 批量处理（使用内置数据模拟文件，不读真实文件）
    total += 1
    try:
        # 模拟批量: 直接用文本列表
        results = [process_text(t["text"]) for t in SELFTEST_SAMPLE]
        assert len(results) == 3, "应处理 3 条"
        for r in results:
            assert "formatted" in r, "应包含格式化输出"
        passed += 1
        print("[ok] batch_process (模拟)")
    except Exception as e:
        print(f"[fail] batch_process: {e}")

    # 测试5: 检索功能
    total += 2
    try:
        memories = [process_text(t["text"]) for t in SELFTEST_SAMPLE]
        # 检索 "Python" 应至少返回 1 条
        r1 = search_memories(memories, "Python")
        assert len(r1) >= 1, "应至少找到 1 条"
        # 检索 "不存在词" 应返回 0 条
        r2 = search_memories(memories, "绝无此词xyz")
        assert len(r2) == 0, "应返回 0 条"
        passed += 2
        print("[ok] search_memories")
    except Exception as e:
        print(f"[fail] search_memories: {e}")

    # 测试6: 错误处理
    total += 1
    try:
        # 空输入应报错
        try:
            parse_input("")
            raise AssertionError("空输入应报错")
        except ValueError:
            pass
        # 不支持的格式
        try:
            format_output({}, "xml")
            raise AssertionError("不支持格式应报错")
        except ValueError:
            pass
        passed += 1
        print("[ok] error handling")
    except Exception as e:
        print(f"[fail] error handling: {e}")

    # 汇总
    print(f"\n[selftest] 结果: {passed}/{total} 通过")
    return 0 if passed == total else 1


def main():
    parser = argparse.ArgumentParser(
        description="claude-mem — 跨会话上下文持久化与压缩",
        epilog="示例: python main.py --input '文本内容' --format json",
    )
    parser.add_argument(
        "--input", "-i",
        help="输入文本内容（直接传递）",
    )
    parser.add_argument(
        "--file", "-f",
        action="append",
        help="输入文件路径（可多次指定）",
    )
    parser.add_argument(
        "--url",
        action="append",
        help="输入 URL（可多次指定）",
    )
    parser.add_argument(
        "--format",
        choices=["json", "markdown"],
        default="json",
        help="输出格式 (默认: json)",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行离线自检（不依赖外部文件/网络）",
    )
    parser.add_argument(
        "--search",
        help="在输出结果中检索关键词（需配合 --input 或 --file）",
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        sys.exit(run_selftest())

    # 收集输入
    inputs = []
    if args.input:
        inputs.append(("text", args.input))
    if args.file:
        for f in args.file:
            inputs.append(("file", f))
    if args.url:
        for u in args.url:
            inputs.append(("url", u))

    if not inputs:
        print(f"错误: {ERROR_CODES['E001']}", file=sys.stderr)
        parser.print_help()
        sys.exit(1)

    # 处理
    results = []
    try:
        for kind, value in inputs:
            if kind == "text":
                results.append(process_text(value, fmt=args.format))
            elif kind == "file":
                results.append(process_file(value, fmt=args.format))
            elif kind == "url":
                results.append(process_url(value, fmt=args.format))
    except Exception as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)

    # 检索模式
    if args.search:
        results = search_memories(results, args.search)
        if not results:
            print(f"错误: {ERROR_CODES['E009']}", file=sys.stderr)
            sys.exit(1)

    # 输出
    for r in results:
        if "formatted" in r:
            print(r["formatted"])
        else:
            print(json.dumps(r, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
