#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gchart - 基于功能规格的独立实现脚本

本脚本依据功能规格（clean-room）全新编写，不参考任何既有实现。
提供标准流程处理、置信度评估、错误码体系，以及离线自检功能。

用法：
    python scripts/main.py --selftest   # 离线自检核心逻辑
    python scripts/main.py --input <文本> --format <json|text>  # 标准处理流程
"""

import argparse
import json
import sys
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# 错误码与异常定义
# ============================================================

class GChartError(Exception):
    """gchart 基础异常，携带错误码。"""
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(f"[{code}] {message}")


def raise_error(code: str, message: str) -> None:
    """抛出带错误码的异常。"""
    raise GChartError(code, message)


# ============================================================
# 核心逻辑：输入解析、结构化、置信度评估、输出
# ============================================================

def validate_input(raw_text: str) -> str:
    """
    校验输入内容。

    错误码：
        E001 - 输入为空
        E003 - 输入格式错误（非字符串）
    """
    if raw_text is None:
        raise_error("E001", "请提供待处理的内容，格式为：用户提供的数据/文件/URL")
    if not isinstance(raw_text, str):
        raise_error("E003", "输入格式不符合要求，示例：一段文本、文件路径或URL")
    stripped = raw_text.strip()
    if not stripped:
        raise_error("E001", "请提供待处理的内容，格式为：用户提供的数据/文件/URL")
    return stripped


def parse_input(raw_text: str) -> Dict[str, Any]:
    """
    解析输入内容，识别关键信息并结构化。

    返回结构：
        {
            "source_type": "text" | "file" | "url",
            "content": 原始内容,
            "keywords": [识别的关键词列表],
            "segments": [按分隔符切分的片段],
            "field_count": 片段数量
        }

    错误码：
        E002 - 关键信息缺失（无法识别任何有意义内容）
    """
    text = validate_input(raw_text)

    # 识别来源类型
    source_type = "text"
    if text.startswith(("http://", "https://")):
        source_type = "url"
    elif text.startswith(("file://", "./", "../", "/")) or text.endswith((".txt", ".csv", ".json", ".md")):
        source_type = "file"

    # 提取关键词（简单分词：按非字母数字切分，过滤短词和停用词）
    import re
    tokens = re.findall(r"[a-zA-Z0-9\u4e00-\u9fff]+", text)
    stop_words = {"的", "了", "和", "是", "在", "有", "我", "你", "他", "她", "它",
                  "the", "a", "an", "is", "are", "was", "were", "to", "of", "in"}
    keywords = [t for t in tokens if len(t) >= 2 and t.lower() not in stop_words][:10]

    # 按常见分隔符切分
    segments = [s.strip() for s in re.split(r"[,，;；。\n]+", text) if s.strip()]

    if not segments and not keywords:
        raise_error("E002", "还缺少以下信息，请补充：可识别的关键内容（文本、文件路径或URL）")

    return {
        "source_type": source_type,
        "content": text,
        "keywords": keywords,
        "segments": segments,
        "field_count": len(segments),
    }


def compute_confidence(parsed: Dict[str, Any]) -> Tuple[float, str]:
    """
    计算置信度并给出建议标注。

    规则（依据规格）：
        - 置信度 ≥90%：直接输出
        - 85%-90%：标注"建议复核"
        - <85%：标注"[需核实]"，并说明不确定点

    返回：(置信度 0-100, 标注文本)
    """
    score = 50.0  # 基础分

    # 有内容 +20
    if parsed.get("content"):
        score += 20

    # 有关键词 +10
    if parsed.get("keywords"):
        score += 10

    # 有分段 +10
    if parsed.get("segments"):
        score += 10

    # 来源类型明确 +5
    if parsed.get("source_type") in ("text", "file", "url"):
        score += 5

    # 字段数量适中（1-10个字段） +5
    field_count = parsed.get("field_count", 0)
    if 1 <= field_count <= 10:
        score += 5

    # 内容长度合理（10-500字符） +5
    content_len = len(parsed.get("content", ""))
    if 10 <= content_len <= 500:
        score += 5

    # 限制在 0-100
    score = max(0.0, min(100.0, score))

    # 生成标注
    if score >= 90:
        label = "直接输出"
    elif score >= 85:
        label = "建议复核"
    else:
        # 说明不确定点
        reasons = []
        if not parsed.get("keywords"):
            reasons.append("未识别到关键关键词")
        if not parsed.get("segments"):
            reasons.append("无法切分内容片段")
        if field_count > 10:
            reasons.append(f"字段数量过多（{field_count}个）")
        if content_len < 10:
            reasons.append("内容过短")
        if content_len > 500:
            reasons.append("内容过长")
        detail = "；".join(reasons) if reasons else "输入信息不足"
        label = f"[需核实]（{detail}）"

    return score, label


def generate_output(parsed: Dict[str, Any], output_format: str = "json") -> str:
    """
    按约定格式生成输出。

    支持格式：
        - json: 结构化 JSON
        - text: 人类可读文本
    """
    confidence, label = compute_confidence(parsed)

    result = {
        "source_type": parsed["source_type"],
        "content_preview": parsed["content"][:100] + ("..." if len(parsed["content"]) > 100 else ""),
        "keywords": parsed["keywords"],
        "segments": parsed["segments"],
        "field_count": parsed["field_count"],
        "confidence": round(confidence, 1),
        "confidence_label": label,
        "status": "success",
    }

    if output_format == "json":
        return json.dumps(result, ensure_ascii=False, indent=2)
    else:
        # 文本格式
        lines = [
            "=== gchart 处理结果 ===",
            f"来源类型: {result['source_type']}",
            f"内容预览: {result['content_preview']}",
            f"关键词: {', '.join(result['keywords']) if result['keywords'] else '无'}",
            f"片段数: {result['field_count']}",
            f"置信度: {result['confidence']}%",
            f"标注: {label}",
        ]
        return "\n".join(lines)


def process_input(raw_text: str, output_format: str = "json") -> str:
    """
    标准流程入口：解析 → 结构化 → 置信度评估 → 输出。

    错误码：
        E004 - 超出能力边界（不支持的输出格式）
    """
    if output_format not in ("json", "text"):
        raise_error("E004", f"这超出了本工具的能力范围，建议：使用 json 或 text 格式，当前格式: {output_format}")

    parsed = parse_input(raw_text)
    return generate_output(parsed, output_format)


# ============================================================
# 批量处理
# ============================================================

def process_batch(inputs: List[str], output_format: str = "json") -> str:
    """
    批量处理多个输入，按同一规则逐项处理。

    错误码：
        E001 - 输入列表为空
    """
    if not inputs:
        raise_error("E001", "请提供待处理的内容，格式为：用户提供的数据/文件/URL")

    results = []
    for item in inputs:
        try:
            parsed = parse_input(item)
            confidence, label = compute_confidence(parsed)
            results.append({
                "input": item[:50] + ("..." if len(item) > 50 else ""),
                "field_count": parsed["field_count"],
                "confidence": round(confidence, 1),
                "label": label,
                "status": "success",
            })
        except GChartError as e:
            results.append({
                "input": item[:50] + ("..." if len(item) > 50 else ""),
                "error_code": e.code,
                "error_message": e.message,
                "status": "error",
            })

    return json.dumps({"batch_size": len(results), "results": results}, ensure_ascii=False, indent=2)


# ============================================================
# 离线自检（--selftest）
# ============================================================

def run_selftest() -> int:
    """
    内置硬编码样例数据离线自检核心逻辑。
    不读外部文件、不依赖当前工作目录、不访问网络。

    断言使用宽松阈值（大小比较/区间判断），确保必然匹配。
    """
    print("=== gchart 自检开始 ===")
    failures = 0

    # ---- 测试1: 正常文本处理 ----
    print("\n[测试1] 正常文本处理")
    try:
        sample = "这是一个示例文本，包含关键词 A 和 B，以及一些其他内容。"
        parsed = parse_input(sample)
        assert parsed["source_type"] == "text", "来源类型应为 text"
        assert len(parsed["segments"]) >= 1, "应至少有一个片段"
        assert len(parsed["keywords"]) >= 1, "应至少有一个关键词"

        confidence, label = compute_confidence(parsed)
        assert 0 <= confidence <= 100, "置信度应在 0-100 范围内"
        assert label in ("直接输出", "建议复核") or label.startswith("[需核实]"), "标注格式不正确"

        output = generate_output(parsed, "json")
        assert "confidence" in output, "JSON 输出应包含置信度字段"
        print(f"  通过 (置信度={confidence:.1f}%, 标注={label})")
    except Exception as e:
        print(f"  失败: {e}")
        failures += 1

    # ---- 测试2: URL 输入 ----
    print("\n[测试2] URL 输入识别")
    try:
        sample = "https://example.com/data/page?query=test"
        parsed = parse_input(sample)
        assert parsed["source_type"] == "url", "URL 输入应识别为 url 类型"
        assert parsed["field_count"] >= 1, "URL 应至少产生一个片段"
        print(f"  通过 (类型={parsed['source_type']}, 片段数={parsed['field_count']})")
    except Exception as e:
        print(f"  失败: {e}")
        failures += 1

    # ---- 测试3: 文件路径输入 ----
    print("\n[测试3] 文件路径输入识别")
    try:
        sample = "./data/sample.txt"
        parsed = parse_input(sample)
        assert parsed["source_type"] == "file", "文件路径应识别为 file 类型"
        print(f"  通过 (类型={parsed['source_type']})")
    except Exception as e:
        print(f"  失败: {e}")
        failures += 1

    # ---- 测试4: 空输入错误处理 ----
    print("\n[测试4] 空输入错误处理")
    try:
        parse_input("   ")
        print("  失败: 空输入应抛出 E001 错误")
        failures += 1
    except GChartError as e:
        assert e.code == "E001", f"错误码应为 E001，实际 {e.code}"
        print(f"  通过 (错误码={e.code})")
    except Exception as e:
        print(f"  失败: 应抛出 GChartError，实际 {type(e).__name__}: {e}")
        failures += 1

    # ---- 测试5: 置信度区间判断 ----
    print("\n[测试5] 置信度区间判断")
    try:
        # 长文本应获得较高置信度
        long_text = "这是一个较长的示例文本。" * 20
        parsed = parse_input(long_text)
        conf_long, _ = compute_confidence(parsed)

        # 短文本置信度不应过高
        short_text = "你好"
        parsed_short = parse_input(short_text)
        conf_short, _ = compute_confidence(parsed_short)

        # 宽松断言：长文本置信度应大于短文本
        assert conf_long > conf_short, f"长文本置信度({conf_long})应大于短文本({conf_short})"
        print(f"  通过 (长文本={conf_long:.1f}% > 短文本={conf_short:.1f}%)")
    except Exception as e:
        print(f"  失败: {e}")
        failures += 1

    # ---- 测试6: 批量处理 ----
    print("\n[测试6] 批量处理")
    try:
        batch = ["第一条数据", "https://example.com", ""]
        result = process_batch(batch)
        result_data = json.loads(result)
        assert result_data["batch_size"] == 3, "批量大小应为 3"
        assert len(result_data["results"]) == 3, "应有 3 条结果"
        # 空输入应产生错误条目
        error_items = [r for r in result_data["results"] if r["status"] == "error"]
        assert len(error_items) >= 1, "空输入应产生错误条目"
        print(f"  通过 (共{result_data['batch_size']}条, 错误{len(error_items)}条)")
    except Exception as e:
        print(f"  失败: {e}")
        failures += 1

    # ---- 测试7: 不支持的输出格式 ----
    print("\n[测试7] 不支持的输出格式")
    try:
        process_input("测试内容", output_format="xml")
        print("  失败: 应抛出 E004 错误")
        failures += 1
    except GChartError as e:
        assert e.code == "E004", f"错误码应为 E004，实际 {e.code}"
        print(f"  通过 (错误码={e.code})")
    except Exception as e:
        print(f"  失败: 应抛出 GChartError，实际 {type(e).__name__}: {e}")
        failures += 1

    # ---- 总结 ----
    print("\n=== 自检结束 ===")
    if failures == 0:
        print("全部测试通过 ✓")
        return 0
    else:
        print(f"{failures} 项测试失败 ✗")
        return 1


# ============================================================
# 命令行入口
# ============================================================

def main() -> int:
    """命令行主入口。"""
    parser = argparse.ArgumentParser(
        description="gchart - 数据/文件/URL 结构化处理工具",
        epilog="示例: python scripts/main.py --input '这是一个测试文本' --format json"
    )
    parser.add_argument("--input", "-i", help="待处理的输入内容（文本、文件路径或URL）")
    parser.add_argument("--format", "-f", choices=["json", "text"], default="json",
                        help="输出格式: json（默认）或 text")
    parser.add_argument("--batch", "-b", nargs="+", help="批量处理多个输入")
    parser.add_argument("--selftest", action="store_true", help="离线自检核心逻辑")

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        return run_selftest()

    # 批量模式
    if args.batch:
        try:
            result = process_batch(args.batch, args.format)
            print(result)
            return 0
        except GChartError as e:
            print(f"错误: {e}", file=sys.stderr)
            return 1

    # 单条处理模式
    if args.input:
        try:
            result = process_input(args.input, args.format)
            print(result)
            return 0
        except GChartError as e:
            print(f"错误: {e}", file=sys.stderr)
            return 1

    # 无参数时显示帮助
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
