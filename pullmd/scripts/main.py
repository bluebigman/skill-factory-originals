#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pullmd - 通用数据/文件/URL 转结构化 Markdown 工具（独立实现）

本脚本根据功能规格独立编写，不参考任何既有代码。
仅依赖 Python 标准库，无第三方依赖。

用法:
    python main.py --selftest          # 离线自检（不读外部文件/不联网）
    python main.py --input <内容>       # 处理单个输入
    python main.py --batch             # 批量模式（从 stdin 逐行读取）
"""

import argparse
import json
import sys
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# 错误码定义（E001-E010）
# ============================================================
ERROR_CODES = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：...（逐项追问）",
    "E003": "输入格式不符合要求，示例：...",
    "E004": "这超出了本工具的能力范围，建议...",
    "E005": "结果无法确定，建议：...",
    "E006": "内部处理异常，请重试或检查输入",
    "E007": "批量处理中断，部分输入未完成",
    "E008": "输出格式不支持，可选：markdown / json / text",
    "E009": "输入来源类型不支持，可选：text / url / file",
    "E010": "置信度计算失败，已按最低置信度处理",
}


class PullMDError(Exception):
    """统一异常类，携带错误码"""

    def __init__(self, code: str, message: str = ""):
        self.code = code
        self.message = message or ERROR_CODES.get(code, "未知错误")
        super().__init__(f"[{code}] {self.message}")


# ============================================================
# 核心处理逻辑
# ============================================================

def parse_input(raw: str) -> Dict[str, Any]:
    """
    解析输入内容，识别关键信息。

    支持三种输入类型（自动检测）：
    - text: 普通文本
    - url: 以 http(s):// 开头
    - file: 以 file:// 开头或包含文件路径特征

    返回结构化字典，包含：
    - source_type: 输入类型
    - content: 原始内容
    - key_fields: 提取的关键字段
    - confidence: 置信度 (0-100)
    """
    if not raw or not raw.strip():
        raise PullMDError("E001")

    raw = raw.strip()

    # 检测输入类型
    source_type = "text"
    if raw.startswith(("http://", "https://")):
        source_type = "url"
    elif raw.startswith("file://") or raw.endswith((".md", ".txt", ".json", ".csv")):
        source_type = "file"

    # 提取关键字段（基于通用规则）
    key_fields = _extract_key_fields(raw, source_type)

    # 计算置信度
    confidence = _calculate_confidence(raw, key_fields, source_type)

    return {
        "source_type": source_type,
        "content": raw,
        "key_fields": key_fields,
        "confidence": confidence,
        "warnings": _generate_warnings(confidence, key_fields),
    }


def _extract_key_fields(content: str, source_type: str) -> Dict[str, Any]:
    """从输入中提取关键字段（通用规则，不依赖具体格式）"""
    fields: Dict[str, Any] = {}

    # 提取标题（第一行非空内容，截取前50字符）
    lines = [l.strip() for l in content.splitlines() if l.strip()]
    if lines:
        title = lines[0][:50]
        if len(lines[0]) > 50:
            title += "..."
        fields["title"] = title

    # 提取关键词（简单统计词频）
    words = _tokenize(content)
    if words:
        fields["keywords"] = _top_words(words, 5)

    # 统计信息
    fields["stats"] = {
        "char_count": len(content),
        "line_count": len(lines),
        "word_count": len(words),
    }

    # 类型特定字段
    if source_type == "url":
        fields["url"] = content
        fields["domain"] = _extract_domain(content)
    elif source_type == "file":
        fields["file_path"] = content

    return fields


def _tokenize(text: str) -> List[str]:
    """简单分词：按非字母数字字符分割，过滤停用词和短词"""
    import re

    words = re.findall(r"[a-zA-Z0-9\u4e00-\u9fff]+", text.lower())
    stopwords = {"the", "a", "an", "and", "or", "but", "of", "to", "in",
                 "for", "on", "with", "as", "by", "at", "from", "is", "are",
                 "was", "were", "be", "been", "being", "this", "that",
                 "这些", "那些", "一个", "的", "了", "和", "与", "是"}
    return [w for w in words if w not in stopwords and len(w) > 1]


def _top_words(words: List[str], n: int) -> List[str]:
    """返回出现频率最高的 n 个词"""
    freq: Dict[str, int] = {}
    for w in words:
        freq[w] = freq.get(w, 0) + 1
    sorted_words = sorted(freq.items(), key=lambda x: -x[1])
    return [w for w, _ in sorted_words[:n]]


def _extract_domain(url: str) -> str:
    """从 URL 中提取域名（简化实现）"""
    url = url.replace("http://", "").replace("https://", "")
    return url.split("/")[0].split("?")[0]


def _calculate_confidence(content: str, fields: Dict[str, Any], source_type: str) -> float:
    """
    计算置信度 (0-100)。

    规则：
    - 基础分 60
    - 有标题 +10
    - 有关键词 +10
    - 内容长度 > 50 字符 +10
    - 内容长度 > 200 字符 +10
    - 类型明确 +10（url/file 额外加分）
    """
    confidence = 60.0

    if fields.get("title"):
        confidence += 10
    if fields.get("keywords"):
        confidence += 10

    char_count = fields.get("stats", {}).get("char_count", 0)
    if char_count > 50:
        confidence += 10
    if char_count > 200:
        confidence += 10

    if source_type in ("url", "file"):
        confidence += 10

    # 置信度上限 98，下限 10
    return max(10.0, min(98.0, confidence))


def _generate_warnings(confidence: float, fields: Dict[str, Any]) -> List[str]:
    """根据置信度生成警告信息"""
    warnings = []
    if confidence < 85:
        warnings.append("[需核实] 置信度较低，部分内容可能不准确")
    elif confidence < 90:
        warnings.append("建议复核：置信度在 85%-90% 之间")
    return warnings


def format_output(data: Dict[str, Any], fmt: str = "markdown") -> str:
    """按指定格式输出结果"""
    if fmt == "markdown":
        return _format_markdown(data)
    elif fmt == "json":
        return json.dumps(data, ensure_ascii=False, indent=2)
    elif fmt == "text":
        return _format_text(data)
    else:
        raise PullMDError("E008")


def _format_markdown(data: Dict[str, Any]) -> str:
    """格式化为 Markdown"""
    lines = []
    fields = data["key_fields"]

    # 标题
    title = fields.get("title", "未命名内容")
    lines.append(f"# {title}")
    lines.append("")

    # 元信息
    lines.append(f"> 来源类型：{data['source_type']}")
    lines.append(f"> 置信度：{data['confidence']:.1f}%")
    if data["warnings"]:
        for w in data["warnings"]:
            lines.append(f"> ⚠️ {w}")
    lines.append("")

    # 关键字段
    if fields.get("keywords"):
        lines.append("## 关键词")
        lines.append("")
        lines.append("、".join(f"`{k}`" for k in fields["keywords"]))
        lines.append("")

    # 统计信息
    stats = fields.get("stats", {})
    lines.append("## 统计")
    lines.append("")
    lines.append(f"- 字符数：{stats.get('char_count', 0)}")
    lines.append(f"- 行数：{stats.get('line_count', 0)}")
    lines.append(f"- 词数：{stats.get('word_count', 0)}")
    lines.append("")

    # 类型特定信息
    if data["source_type"] == "url":
        lines.append("## URL 信息")
        lines.append("")
        lines.append(f"- 域名：{fields.get('domain', '未知')}")
        lines.append("")
    elif data["source_type"] == "file":
        lines.append("## 文件信息")
        lines.append("")
        lines.append(f"- 路径：{fields.get('file_path', '未知')}")
        lines.append("")

    # 原始内容摘要
    lines.append("## 内容摘要")
    lines.append("")
    content = data["content"]
    summary = content[:200] + ("..." if len(content) > 200 else "")
    lines.append(summary)
    lines.append("")

    return "\n".join(lines)


def _format_text(data: Dict[str, Any]) -> str:
    """格式化为纯文本"""
    lines = []
    fields = data["key_fields"]

    lines.append(f"标题: {fields.get('title', '未命名')}")
    lines.append(f"类型: {data['source_type']}")
    lines.append(f"置信度: {data['confidence']:.1f}%")

    if fields.get("keywords"):
        lines.append(f"关键词: {', '.join(fields['keywords'])}")

    stats = fields.get("stats", {})
    lines.append(f"统计: {stats.get('char_count', 0)} 字符, "
                 f"{stats.get('line_count', 0)} 行, "
                 f"{stats.get('word_count', 0)} 词")

    if data["warnings"]:
        lines.append("警告:")
        for w in data["warnings"]:
            lines.append(f"  - {w}")

    return "\n".join(lines)


# ============================================================
# 批量处理
# ============================================================

def process_batch(inputs: List[str], fmt: str = "markdown") -> List[Tuple[bool, Any]]:
    """批量处理多个输入，返回 (成功标志, 结果或错误) 列表"""
    results = []
    for inp in inputs:
        try:
            data = parse_input(inp)
            output = format_output(data, fmt)
            results.append((True, output))
        except PullMDError as e:
            results.append((False, str(e)))
        except Exception:
            results.append((False, f"[E006] {ERROR_CODES['E006']}"))
    return results


# ============================================================
# 自检模块（离线、硬编码样例）
# ============================================================

def run_selftest() -> int:
    """
    自检核心逻辑。使用硬编码样例数据，不读外部文件、不联网。

    返回 0 表示全部通过，1 表示有失败。
    """
    print("=" * 60)
    print("pullmd 自检开始（离线模式）")
    print("=" * 60)

    failures = 0

    # --- 测试用例 1: 普通文本 ---
    print("\n[测试 1] 普通文本处理")
    try:
        result = parse_input("这是一个测试文档，用于验证核心功能是否正常。包含一些中文内容。")
        assert result["source_type"] == "text", "类型应为 text"
        assert result["confidence"] > 50, "置信度应大于 50"
        assert result["key_fields"]["stats"]["char_count"] > 10, "字符数应大于 10"
        output = format_output(result, "markdown")
        assert "#" in output, "Markdown 应包含标题标记"
        print("  ✓ 通过")
    except AssertionError as e:
        failures += 1
        print(f"  ✗ 失败: {e}")
    except PullMDError as e:
        failures += 1
        print(f"  ✗ 异常: {e}")

    # --- 测试用例 2: URL 输入 ---
    print("\n[测试 2] URL 处理")
    try:
        result = parse_input("https://example.com/docs/page1")
        assert result["source_type"] == "url", "类型应为 url"
        assert "example.com" in result["key_fields"].get("domain", ""), "应提取域名"
        assert result["confidence"] > 50, "置信度应大于 50"
        print("  ✓ 通过")
    except AssertionError as e:
        failures += 1
        print(f"  ✗ 失败: {e}")
    except PullMDError as e:
        failures += 1
        print(f"  ✗ 异常: {e}")

    # --- 测试用例 3: 空输入应报错 ---
    print("\n[测试 3] 空输入错误处理")
    try:
        parse_input("")
        failures += 1
        print("  ✗ 失败: 空输入未报错")
    except PullMDError as e:
        assert e.code == "E001", f"错误码应为 E001，实际 {e.code}"
        print("  ✓ 通过")

    # --- 测试用例 4: 批量处理 ---
    print("\n[测试 4] 批量处理")
    try:
        inputs = ["第一条测试内容", "https://example.org", ""]
        results = process_batch(inputs)
        assert len(results) == 3, "应有 3 个结果"
        assert results[0][0] is True, "第一条应成功"
        assert results[1][0] is True, "第二条应成功"
        assert results[2][0] is False, "第三条应失败（空输入）"
        print("  ✓ 通过")
    except AssertionError as e:
        failures += 1
        print(f"  ✗ 失败: {e}")

    # --- 测试用例 5: 置信度边界 ---
    print("\n[测试 5] 置信度范围")
    try:
        # 长文本应有较高置信度
        long_text = "这是一段较长的文本。" * 20
        result = parse_input(long_text)
        assert result["confidence"] > 70, "长文本置信度应较高"
        # 所有置信度应在 0-100 之间
        assert 0 <= result["confidence"] <= 100, "置信度应在 0-100"
        print("  ✓ 通过")
    except AssertionError as e:
        failures += 1
        print(f"  ✗ 失败: {e}")

    # --- 测试用例 6: 输出格式 ---
    print("\n[测试 6] 多种输出格式")
    try:
        result = parse_input("测试多种输出格式")
        md = format_output(result, "markdown")
        js = format_output(result, "json")
        tx = format_output(result, "text")
        assert "{" in js, "JSON 应包含大括号"
        assert md != tx, "Markdown 和文本输出应不同"
        print("  ✓ 通过")
    except AssertionError as e:
        failures += 1
        print(f"  ✗ 失败: {e}")
    except PullMDError as e:
        failures += 1
        print(f"  ✗ 异常: {e}")

    # --- 测试用例 7: 错误码覆盖 ---
    print("\n[测试 7] 错误码检查")
    try:
        assert "E001" in ERROR_CODES
        assert "E002" in ERROR_CODES
        assert "E003" in ERROR_CODES
        assert "E004" in ERROR_CODES
        assert "E005" in ERROR_CODES
        assert "E006" in ERROR_CODES
        assert "E007" in ERROR_CODES
        assert "E008" in ERROR_CODES
        assert "E009" in ERROR_CODES
        assert "E010" in ERROR_CODES
        print("  ✓ 通过")
    except AssertionError as e:
        failures += 1
        print(f"  ✗ 失败: 错误码缺失")

    # --- 测试用例 8: 文件类型输入 ---
    print("\n[测试 8] 文件路径输入")
    try:
        result = parse_input("file:///tmp/test.md")
        assert result["source_type"] == "file", "类型应为 file"
        assert result["confidence"] > 50, "置信度应大于 50"
        print("  ✓ 通过")
    except AssertionError as e:
        failures += 1
        print(f"  ✗ 失败: {e}")

    # --- 测试用例 9: 中文内容支持 ---
    print("\n[测试 9] 中文内容处理")
    try:
        result = parse_input("人工智能 深度学习 自然语言处理 机器学习 神经网络")
        keywords = result["key_fields"].get("keywords", [])
        assert len(keywords) > 0, "应提取到关键词"
        assert any("人工智能" in k or "学习" in k for k in keywords), "应包含中文关键词"
        print("  ✓ 通过")
    except AssertionError as e:
        failures += 1
        print(f"  ✗ 失败: {e}")

    # --- 测试用例 10: 非法输出格式 ---
    print("\n[测试 10] 非法输出格式")
    try:
        result = parse_input("测试内容")
        format_output(result, "xml")
        failures += 1
        print("  ✗ 失败: 非法格式未报错")
    except PullMDError as e:
        assert e.code == "E008", f"错误码应为 E008，实际 {e.code}"
        print("  ✓ 通过")

    # --- 汇总 ---
    print("\n" + "=" * 60)
    if failures == 0:
        print("自检全部通过 ✓")
        return 0
    else:
        print(f"自检完成，{failures} 项失败 ✗")
        return 1


# ============================================================
# 主入口
# ============================================================

def main() -> int:
    """命令行主入口"""
    parser = argparse.ArgumentParser(
        description="pullmd - 通用数据/文件/URL 转结构化工具",
        epilog="示例: python main.py --input 'https://example.com'"
    )
    parser.add_argument("--input", "-i", type=str,
                        help="待处理的内容（文本/URL/文件路径）")
    parser.add_argument("--batch", "-b", action="store_true",
                        help="批量模式：从 stdin 逐行读取输入")
    parser.add_argument("--format", "-f", type=str, default="markdown",
                        choices=["markdown", "json", "text"],
                        help="输出格式（默认: markdown）")
    parser.add_argument("--selftest", action="store_true",
                        help="运行离线自检（不读文件、不联网）")

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        return run_selftest()

    # 批量模式
    if args.batch:
        print("请输入内容（每行一条，Ctrl+D 结束）：", file=sys.stderr)
        inputs = [line.strip() for line in sys.stdin if line.strip()]
        if not inputs:
            print(f"[E001] {ERROR_CODES['E001']}", file=sys.stderr)
            return 1
        results = process_batch(inputs, args.format)
        for i, (ok, res) in enumerate(results, 1):
            print(f"--- 结果 {i} ---")
            if ok:
                print(res)
            else:
                print(res, file=sys.stderr)
        return 0

    # 单条处理
    if not args.input:
        print(f"[E001] {ERROR_CODES['E001']}", file=sys.stderr)
        return 1

    try:
        data = parse_input(args.input)
        output = format_output(data, args.format)
        print(output)
        return 0
    except PullMDError as e:
        print(e, file=sys.stderr)
        return 1
    except Exception as e:
        print(f"[E006] {ERROR_CODES['E006']}: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
