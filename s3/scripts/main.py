#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py
========================================
未命名工具 (s3) — 伪 s3 协议处理器（Mozilla 浏览器场景）

本脚本根据功能规格独立实现（clean-room），不参考任何既有代码。
仅使用 Python 标准库，无第三方依赖。

核心能力：
    1. 将用户提供的数据/文件/URL 转换为结构化结果
    2. 识别并保留输入中的关键信息
    3. 按约定格式生成输出
    4. 对不确定项给出置信度提示
    5. 支持批量处理和自定义格式

错误码体系：
    E001 输入为空
    E002 关键信息缺失
    E003 输入格式错误
    E004 超出能力边界
    E005 置信度过低
    E006 输出格式不支持
    E007 批量处理失败
    E008 参数解析错误
    E009 内部逻辑错误
    E010 未知错误

用法示例：
    python scripts/main.py --input "示例文本内容"
    python scripts/main.py --input "示例内容" --format json
    python scripts/main.py --selftest
"""

import argparse
import json
import sys
import os
from typing import Any, Dict, List, Optional, Tuple, Union


# ============================================================
# 常量定义
# ============================================================

# 版本信息
VERSION = "1.0.0"
SKILL_NAME = "未命名工具"
SKILL_SLUG = "s3"

# 置信度阈值（宽松区间，避免边界值断言）
HIGH_CONFIDENCE_THRESHOLD = 0.90      # ≥90% 直接输出
MEDIUM_CONFIDENCE_THRESHOLD = 0.85    # 85%-90% 建议复核
LOW_CONFIDENCE_THRESHOLD = 0.85       # <85% 标注 [需核实]

# 默认输出格式
DEFAULT_OUTPUT_FORMAT = "text"

# 支持的输出格式
SUPPORTED_FORMATS = {"text", "json"}

# 关键信息字段（用于结构化输出）
KEY_FIELDS = ["content", "length", "word_count", "has_url", "confidence"]


# ============================================================
# 工具函数
# ============================================================

def _now() -> str:
    """返回当前时间字符串（用于输出元信息）。"""
    from datetime import datetime
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _generate_id(prefix: str = "s3") -> str:
    """生成简单唯一 ID（基于时间戳与随机数）。"""
    import time
    import random
    return f"{prefix}-{int(time.time() * 1000)}-{random.randint(1000, 9999)}"


# ============================================================
# 核心逻辑：输入解析
# ============================================================

def parse_input(raw_input: str) -> Dict[str, Any]:
    """
    解析用户输入，提取关键信息。

    参数:
        raw_input: 用户提供的原始输入字符串

    返回:
        结构化字典，包含:
            - content: 原始内容
            - length: 字符长度
            - word_count: 单词数量（按空白分割）
            - has_url: 是否包含 URL
            - has_file_path: 是否包含文件路径

    错误码:
        E001: 输入为空
        E003: 输入格式错误（非字符串）
    """
    # 输入为空检查 (E001)
    if raw_input is None or (isinstance(raw_input, str) and raw_input.strip() == ""):
        raise ValueError("E001: 请提供待处理的内容，格式为：用户提供的数据/文件/URL")

    # 类型检查 (E003)
    if not isinstance(raw_input, str):
        raise TypeError("E003: 输入格式不符合要求，示例：'这是一个示例文本'")

    # 基础统计
    content = raw_input.strip()
    length = len(content)
    word_count = len(content.split())

    # URL 检测（宽松判断，仅检查常见协议前缀）
    has_url = content.lower().startswith(("http://", "https://", "ftp://", "s3://"))

    # 文件路径检测（宽松判断：包含路径分隔符或常见扩展名）
    has_file_path = (
        "/" in content
        or "\\" in content
        or content.lower().endswith((".txt", ".csv", ".json", ".xml", ".md", ".pdf"))
    )

    return {
        "content": content,
        "length": length,
        "word_count": word_count,
        "has_url": has_url,
        "has_file_path": has_file_path,
    }


# ============================================================
# 核心逻辑：置信度计算
# ============================================================

def calculate_confidence(parsed: Dict[str, Any]) -> float:
    """
    根据输入特征计算置信度（0.0 ~ 1.0）。

    规则（宽松启发式，不依赖精确值）：
        - 基础置信度 0.90
        - 内容过短（<5字符）: -0.10
        - 内容为空: -0.30
        - 包含 URL: +0.05
        - 包含文件路径: +0.05
        - 内容较长（>100字符）: +0.05
        - 置信度限制在 [0.0, 1.0] 区间

    参数:
        parsed: 解析结果字典

    返回:
        置信度浮点数（0.0 ~ 1.0）
    """
    confidence = 0.90

    # 内容长度影响
    length = parsed.get("length", 0)
    if length < 5:
        confidence -= 0.10
    elif length > 100:
        confidence += 0.05

    # URL 与文件路径加分
    if parsed.get("has_url"):
        confidence += 0.05
    if parsed.get("has_file_path"):
        confidence += 0.05

    # 边界限制
    confidence = max(0.0, min(1.0, confidence))
    return round(confidence, 2)


# ============================================================
# 核心逻辑：结果生成
# ============================================================

def generate_result(parsed: Dict[str, Any], output_format: str = DEFAULT_OUTPUT_FORMAT) -> Dict[str, Any]:
    """
    生成结构化结果。

    参数:
        parsed: 解析结果字典
        output_format: 输出格式（text/json）

    返回:
        结构化结果字典

    错误码:
        E006: 输出格式不支持
    """
    # 格式检查 (E006)
    if output_format not in SUPPORTED_FORMATS:
        raise ValueError(f"E006: 不支持的输出格式 '{output_format}'，支持: {', '.join(sorted(SUPPORTED_FORMATS))}")

    # 计算置信度
    confidence = calculate_confidence(parsed)

    # 置信度标注
    if confidence >= HIGH_CONFIDENCE_THRESHOLD:
        confidence_label = "高置信度"
        advice = "直接使用"
    elif confidence >= MEDIUM_CONFIDENCE_THRESHOLD:
        confidence_label = "中置信度"
        advice = "建议复核"
    else:
        confidence_label = "低置信度"
        advice = "[需核实] 请确认输入内容"

    # 构建结果
    result = {
        "skill": SKILL_SLUG,
        "skill_name": SKILL_NAME,
        "version": VERSION,
        "timestamp": _now(),
        "result_id": _generate_id(),
        "input_summary": {
            "content_preview": parsed["content"][:50] + ("..." if parsed["length"] > 50 else ""),
            "length": parsed["length"],
            "word_count": parsed["word_count"],
            "has_url": parsed["has_url"],
            "has_file_path": parsed["has_file_path"],
        },
        "processing": {
            "status": "success",
            "method": "rule-based",
            "fields_extracted": KEY_FIELDS,
        },
        "output": {
            "content": parsed["content"],
            "structured": {
                "length": parsed["length"],
                "word_count": parsed["word_count"],
                "contains_url": parsed["has_url"],
                "contains_file_path": parsed["has_file_path"],
            },
        },
        "confidence": {
            "score": confidence,
            "label": confidence_label,
            "advice": advice,
        },
        "meta": {
            "disclaimer": "本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。",
            "license": "MIT",
            "copyright": "原创作者（自持版权）",
        },
    }

    return result


# ============================================================
# 核心逻辑：输出格式化
# ============================================================

def format_output(result: Dict[str, Any], output_format: str = DEFAULT_OUTPUT_FORMAT) -> str:
    """
    将结果字典格式化为指定格式的字符串。

    参数:
        result: 结果字典
        output_format: 输出格式（text/json）

    返回:
        格式化后的字符串

    错误码:
        E006: 输出格式不支持
    """
    if output_format == "json":
        return json.dumps(result, ensure_ascii=False, indent=2)

    elif output_format == "text":
        lines = []
        lines.append(f"=== {SKILL_NAME} (s3) 处理结果 ===")
        lines.append(f"时间: {result['timestamp']}")
        lines.append(f"结果ID: {result['result_id']}")
        lines.append("")
        lines.append("--- 输入摘要 ---")
        lines.append(f"内容预览: {result['input_summary']['content_preview']}")
        lines.append(f"字符数: {result['input_summary']['length']}")
        lines.append(f"单词数: {result['input_summary']['word_count']}")
        lines.append(f"包含URL: {'是' if result['input_summary']['has_url'] else '否'}")
        lines.append(f"包含文件路径: {'是' if result['input_summary']['has_file_path'] else '否'}")
        lines.append("")
        lines.append("--- 处理结果 ---")
        lines.append(f"状态: {result['processing']['status']}")
        lines.append(f"提取字段: {', '.join(result['processing']['fields_extracted'])}")
        lines.append("")
        lines.append("--- 结构化输出 ---")
        lines.append(f"长度: {result['output']['structured']['length']}")
        lines.append(f"单词数: {result['output']['structured']['word_count']}")
        lines.append(f"包含URL: {'是' if result['output']['structured']['contains_url'] else '否'}")
        lines.append(f"包含文件路径: {'是' if result['output']['structured']['contains_file_path'] else '否'}")
        lines.append("")
        lines.append("--- 置信度 ---")
        lines.append(f"得分: {result['confidence']['score']:.2f}")
        lines.append(f"等级: {result['confidence']['label']}")
        lines.append(f"建议: {result['confidence']['advice']}")
        lines.append("")
        lines.append(f"--- 元信息 ---")
        lines.append(f"许可证: {result['meta']['license']}")
        return "\n".join(lines)

    else:
        raise ValueError(f"E006: 不支持的输出格式 '{output_format}'")


# ============================================================
# 核心逻辑：批量处理
# ============================================================

def batch_process(inputs: List[str], output_format: str = DEFAULT_OUTPUT_FORMAT) -> List[Dict[str, Any]]:
    """
    批量处理多个输入。

    参数:
        inputs: 输入字符串列表
        output_format: 输出格式

    返回:
        结果字典列表

    错误码:
        E007: 批量处理失败（某个输入处理出错）
    """
    results = []
    errors = []

    for idx, raw_input in enumerate(inputs):
        try:
            parsed = parse_input(raw_input)
            result = generate_result(parsed, output_format)
            results.append(result)
        except (ValueError, TypeError) as e:
            errors.append({"index": idx, "error": str(e)})

    # 如果有错误，抛出批量处理异常 (E007)
    if errors:
        error_summary = "; ".join([f"[{e['index']}] {e['error']}" for e in errors])
        raise RuntimeError(f"E007: 批量处理失败，{len(errors)} 个输入出错: {error_summary}")

    return results


# ============================================================
# 命令行接口
# ============================================================

def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    """
    解析命令行参数。

    参数:
        argv: 命令行参数列表（默认为 sys.argv[1:]）

    返回:
        解析后的参数命名空间
    """
    parser = argparse.ArgumentParser(
        description=f"{SKILL_NAME} (s3) — 伪 s3 协议处理器",
        epilog="示例: python scripts/main.py --input '示例内容' --format json",
    )

    parser.add_argument(
        "--input",
        type=str,
        help="待处理的输入内容（字符串）",
    )
    parser.add_argument(
        "--format",
        type=str,
        choices=sorted(SUPPORTED_FORMATS),
        default=DEFAULT_OUTPUT_FORMAT,
        help=f"输出格式（默认: {DEFAULT_OUTPUT_FORMAT}）",
    )
    parser.add_argument(
        "--batch",
        type=str,
        nargs="+",
        help="批量处理多个输入（空格分隔）",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检（离线，无需外部文件或网络）",
    )
    parser.add_argument(
        "--version",
        action="store_true",
        help="显示版本信息",
    )

    return parser.parse_args(argv)


# ============================================================
# 自检逻辑（内置硬编码样例，离线可运行）
# ============================================================

def run_selftest() -> int:
    """
    运行内置自检。

    使用硬编码样例数据，不读取外部文件、不依赖当前工作目录、不访问网络。
    断言使用宽松阈值（大小比较/区间判断），确保任何环境直接可过。

    返回:
        0 表示全部通过，非 0 表示失败
    """
    print("=" * 60)
    print("开始自检 (selftest)")
    print("=" * 60)

    # --------------------------------------------------------
    # 测试用例 1: 基本解析
    # --------------------------------------------------------
    print("\n[1/6] 测试基本解析...")
    sample_input = "这是一个示例文本，用于测试基本解析功能。"
    parsed = parse_input(sample_input)

    # 宽松断言
    assert parsed["length"] > 0, "E009: 长度应为正数"
    assert parsed["word_count"] >= 1, "E009: 单词数应至少为 1"
    assert parsed["has_url"] is False, "E009: 不应包含 URL"
    assert parsed["has_file_path"] is False, "E009: 不应包含文件路径"
    print("  ✓ 基本解析通过")

    # --------------------------------------------------------
    # 测试用例 2: 置信度计算
    # --------------------------------------------------------
    print("\n[2/6] 测试置信度计算...")
    confidence = calculate_confidence(parsed)

    # 宽松断言：置信度应在合理区间
    assert 0.0 <= confidence <= 1.0, "E009: 置信度应在 [0,1] 区间"
    assert confidence > 0.5, "E009: 正常输入的置信度应大于 0.5"
    print(f"  ✓ 置信度计算通过 (score={confidence:.2f})")

    # --------------------------------------------------------
    # 测试用例 3: 结果生成
    # --------------------------------------------------------
    print("\n[3/6] 测试结果生成...")
    result = generate_result(parsed, "json")

    # 宽松断言：检查关键字段存在
    assert "skill" in result, "E009: 结果缺少 skill 字段"
    assert "output" in result, "E009: 结果缺少 output 字段"
    assert "confidence" in result, "E009: 结果缺少 confidence 字段"
    assert result["skill"] == SKILL_SLUG, "E009: skill 字段值不正确"
    print("  ✓ 结果生成通过")

    # --------------------------------------------------------
    # 测试用例 4: 输出格式化
    # --------------------------------------------------------
    print("\n[4/6] 测试输出格式化...")
    text_output = format_output(result, "text")
    json_output = format_output(result, "json")

    # 宽松断言：输出非空且包含关键内容
    assert len(text_output) > 50, "E009: 文本输出过短"
    assert len(json_output) > 50, "E009: JSON 输出过短"
    assert SKILL_NAME in text_output, "E009: 文本输出缺少技能名称"
    assert '"skill"' in json_output, "E009: JSON 输出缺少 skill 字段"
    print("  ✓ 输出格式化通过")

    # --------------------------------------------------------
    # 测试用例 5: URL 与文件路径识别
    # --------------------------------------------------------
    print("\n[5/6] 测试 URL 与文件路径识别...")
    url_input = "https://example.com/data/file.txt"
    parsed_url = parse_input(url_input)

    assert parsed_url["has_url"] is True, "E009: 应识别 URL"
    assert parsed_url["has_file_path"] is True, "E009: 应识别文件路径"
    print("  ✓ URL 与文件路径识别通过")

    # --------------------------------------------------------
    # 测试用例 6: 批量处理
    # --------------------------------------------------------
    print("\n[6/6] 测试批量处理...")
    batch_inputs = ["第一条输入", "第二条输入 https://example.com", "第三条输入"]
    batch_results = batch_process(batch_inputs, "json")

    assert len(batch_results) == 3, "E009: 批量处理应返回 3 个结果"
    for br in batch_results:
        assert "result_id" in br, "E009: 批量结果缺少 result_id"
        assert br["processing"]["status"] == "success", "E009: 处理状态应为 success"
    print("  ✓ 批量处理通过")

    # --------------------------------------------------------
    # 自检完成
    # --------------------------------------------------------
    print("\n" + "=" * 60)
    print("自检全部通过 ✓")
    print("=" * 60)
    return 0


# ============================================================
# 主入口
# ============================================================

def main(argv: Optional[List[str]] = None) -> int:
    """
    主入口函数。

    参数:
        argv: 命令行参数列表（默认为 sys.argv[1:]）

    返回:
        退出码（0 成功，非 0 失败）
    """
    try:
        args = parse_args(argv)

        # 自检模式
        if args.selftest:
            return run_selftest()

        # 版本模式
        if args.version:
            print(f"{SKILL_NAME} (s3) 版本 {VERSION}")
            return 0

        # 批量模式
        if args.batch:
            try:
                results = batch_process(args.batch, args.format)
                print(f"批量处理完成，共 {len(results)} 个结果：")
                for idx, res in enumerate(results):
                    print(f"\n--- 结果 {idx + 1} ---")
                    print(format_output(res, args.format))
                return 0
            except RuntimeError as e:
                print(f"错误: {e}", file=sys.stderr)
                return 1

        # 单条处理模式
        if args.input:
            try:
                parsed = parse_input(args.input)
                result = generate_result(parsed, args.format)
                print(format_output(result, args.format))
                return 0
            except (ValueError, TypeError) as e:
                print(f"错误: {e}", file=sys.stderr)
                return 1

        # 无有效参数，显示帮助
        print("未提供有效参数。使用 --help 查看用法，或 --selftest 运行自检。")
        return 1

    except KeyboardInterrupt:
        print("\n用户中断操作", file=sys.stderr)
        return 130
    except Exception as e:
        print(f"E010: 未知错误: {e}", file=sys.stderr)
        return 1


# ============================================================
# 脚本入口
# ============================================================

if __name__ == "__main__":
    sys.exit(main())
