#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI应用构建器底座 - 独立实现脚本

根据功能规格 clean-room 重写，仅依赖标准库。
提供：输入解析、关键信息提取、结构化输出、置信度标注、批量处理。
"""

import argparse
import json
import os
import re
import sys
import tempfile
from collections import OrderedDict
from difflib import unified_diff

# ============================================================
# 错误码定义（与规格一致）
# ============================================================
ERROR_CODES = {
    "E001": "输入为空，请提供待处理的内容",
    "E002": "关键信息缺失，请补充必要字段",
    "E003": "输入格式错误，请检查格式",
    "E004": "超出能力边界，无法处理",
    "E005": "置信度过低，结果需人工复核",
    "E006": "文件读取失败，请检查文件路径",
    "E007": "文件写入失败，请检查权限",
    "E008": "参数校验失败，请检查命令行参数",
    "E009": "内部逻辑错误，请联系开发者",
    "E010": "未知异常，请查看错误详情",
}


# ============================================================
# 输入校验模块
# ============================================================
def validate_input(raw_text):
    """
    校验输入文本的有效性。

    参数:
        raw_text: 原始输入字符串

    返回:
        (是否有效, 错误码或None)
    """
    if raw_text is None:
        return False, "E001"
    if not isinstance(raw_text, str):
        return False, "E003"
    if not raw_text.strip():
        return False, "E001"
    return True, None


def validate_output_format(fmt):
    """
    校验输出格式参数。

    参数:
        fmt: 输出格式字符串

    返回:
        (是否有效, 错误码或None)
    """
    valid_formats = {"text", "json", "table"}
    if fmt not in valid_formats:
        return False, "E003"
    return True, None


def validate_confidence_threshold(threshold):
    """
    校验置信度阈值参数。

    参数:
        threshold: 置信度阈值（0-100）

    返回:
        (是否有效, 错误码或None)
    """
    if threshold is None:
        return True, None
    try:
        val = float(threshold)
    except (TypeError, ValueError):
        return False, "E003"
    if val < 0 or val > 100:
        return False, "E003"
    return True, None


# ============================================================
# 核心逻辑模块
# ============================================================
def extract_key_info(text):
    """
    从输入文本中提取关键信息。

    策略：
    - 识别中英文标点作为句子边界
    - 提取包含关键字的句子作为关键信息
    - 统计文本统计特征用于置信度计算

    参数:
        text: 输入文本

    返回:
        dict: 包含关键信息、统计特征、置信度
    """
    # 防御性处理
    if not text or not text.strip():
        return {
            "key_points": [],
            "stats": {"total_chars": 0, "sentence_count": 0},
            "confidence": 0.0,
        }

    # 按中英文标点切分句子
    sentences = re.split(r'[。！？!?；;]', text)
    sentences = [s.strip() for s in sentences if s.strip()]

    # 关键信息关键词
    keywords = [
        "需求", "功能", "目标", "用户", "系统", "数据",
        "require", "feature", "goal", "user", "system", "data",
        "构建", "部署", "模板", "生成", "验证",
        "build", "deploy", "template", "generate", "verify",
    ]

    key_points = []
    for sent in sentences:
        # 检查是否包含关键词
        has_keyword = any(kw.lower() in sent.lower() for kw in keywords)
        # 检查句子长度（太短或太长都降低重要性）
        length_score = min(len(sent) / 50, 1.0) if len(sent) > 5 else 0.3
        if has_keyword and length_score > 0.3:
            key_points.append({
                "text": sent,
                "importance": round(length_score, 2),
            })

    # 计算统计特征
    total_chars = len(text)
    sentence_count = len(sentences)
    # 粗略估计信息密度（非空字符占比）
    non_space_chars = len(re.sub(r'\s', '', text))
    density = non_space_chars / max(total_chars, 1)

    # 置信度计算（基于信息完整度）
    confidence = min(95.0, 60.0 + sentence_count * 5 + density * 20)
    if not key_points:
        confidence = min(confidence, 70.0)

    return {
        "key_points": key_points[:10],  # 最多保留10条
        "stats": {
            "total_chars": total_chars,
            "sentence_count": sentence_count,
            "info_density": round(density, 3),
        },
        "confidence": round(confidence, 1),
    }


def format_output(result, fmt="text"):
    """
    将处理结果格式化为指定格式。

    参数:
        result: 处理结果字典
        fmt: 输出格式（text/json/table）

    返回:
        str: 格式化后的字符串
    """
    if fmt == "json":
        return json.dumps(result, ensure_ascii=False, indent=2)

    if fmt == "table":
        lines = ["| 序号 | 关键信息 | 重要度 |", "|------|----------|--------|"]
        for i, point in enumerate(result.get("key_points", []), 1):
            lines.append(
                f"| {i} | {point['text'][:30]}... | {point['importance']} |"
            )
        lines.append("")
        lines.append(f"置信度: {result.get('confidence', 0)}%")
        return "\n".join(lines)

    # 默认 text 格式
    lines = ["=== AI应用构建器底座 - 处理结果 ===", ""]
    lines.append(f"输入统计: {result['stats']['total_chars']} 字符, "
                 f"{result['stats']['sentence_count']} 句")
    lines.append(f"信息密度: {result['stats']['info_density']}")
    lines.append("")
    lines.append("关键信息:")
    for i, point in enumerate(result.get("key_points", []), 1):
        lines.append(f"  {i}. {point['text']}")
    lines.append("")
    lines.append(f"置信度: {result['confidence']}%")
    if result["confidence"] < 85:
        lines.append("[需核实] 置信度较低，请人工复核关键结果")
    return "\n".join(lines)


def process_batch(inputs, fmt="text"):
    """
    批量处理多个输入。

    参数:
        inputs: 输入列表
        fmt: 输出格式

    返回:
        list: 处理结果列表
    """
    results = []
    for item in inputs:
        try:
            valid, err_code = validate_input(item)
            if not valid:
                results.append({
                    "input": item,
                    "error": err_code,
                    "error_msg": ERROR_CODES[err_code],
                    "result": None,
                })
                continue
            result = extract_key_info(item)
            result["formatted"] = format_output(result, fmt)
            results.append({
                "input": item,
                "error": None,
                "result": result,
            })
        except Exception as exc:
            # 单条失败不影响整体
            results.append({
                "input": item,
                "error": "E010",
                "error_msg": f"处理失败: {str(exc)}",
                "result": None,
            })
    return results


# ============================================================
# 文件处理模块（多编码支持）
# ============================================================
def read_text_file(filepath):
    """
    读取文本文件，支持多编码。

    尝试顺序: utf-8 -> gbk -> gb18030 -> latin-1(replace)

    参数:
        filepath: 文件路径

    返回:
        str: 文件内容

    异常:
        E006: 文件读取失败
    """
    if not os.path.isfile(filepath):
        raise IOError(f"文件不存在: {filepath}")

    encodings = ["utf-8", "gbk", "gb18030", "latin-1"]
    last_error = None

    for enc in encodings:
        try:
            with open(filepath, "r", encoding=enc) as f:
                return f.read()
        except UnicodeDecodeError as exc:
            last_error = exc
            continue
        except OSError as exc:
            raise IOError(f"读取文件失败: {exc}") from exc

    # 最后尝试 replace 模式
    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
            print(f"警告: 使用 replace 模式读取，部分字符可能已替换", file=sys.stderr)
            return content
    except OSError as exc:
        raise IOError(f"读取文件失败: {exc}") from exc


def write_text_file(filepath, content, dry_run=False):
    """
    写入文本文件。

    参数:
        filepath: 文件路径
        content: 内容字符串
        dry_run: 是否仅预览不写入

    返回:
        str: 操作结果描述
    """
    if dry_run:
        # 预览模式：输出 diff
        if os.path.exists(filepath):
            try:
                old_content = read_text_file(filepath)
                diff = list(unified_diff(
                    old_content.splitlines(True),
                    content.splitlines(True),
                    fromfile=f"a/{filepath}",
                    tofile=f"b/{filepath}",
                ))
                if diff:
                    return "预览变更:\n" + "".join(diff)
                return "无变更"
            except IOError:
                return f"预览: 新文件将创建 {filepath}"
        return f"预览: 新文件将创建 {filepath}"

    # 实际写入
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        return f"已写入: {filepath}"
    except OSError as exc:
        raise IOError(f"写入文件失败: {exc}") from exc


# ============================================================
# CLI 入口
# ============================================================
def run_selftest():
    """
    内置自检逻辑，使用硬编码样例数据。

    覆盖场景:
    - 正常中文输入
    - 中文标点
    - 空输入
    - 超长输入
    - 英文输入

    返回:
        bool: 自检是否通过
    """
    print("=== 自检开始 ===")
    test_cases = [
        # (描述, 输入, 期望有结果)
        ("正常中文输入", "我们需要构建一个AI应用，支持模板生成功能。用户可以通过命令行操作。", True),
        ("中文标点", "需求：构建部署流程；功能：模板生成。", True),
        ("空输入", "", False),
        ("超长输入", "功能需求。" * 1000, True),
        ("英文输入", "We need to build an AI app with template generation.", True),
    ]

    all_passed = True
    for desc, text, expect_result in test_cases:
        try:
            valid, err_code = validate_input(text)
            if not expect_result:
                # 期望无效输入
                if not valid:
                    print(f"  [PASS] {desc}: 正确拒绝 (错误码 {err_code})")
                else:
                    print(f"  [FAIL] {desc}: 期望拒绝但通过了")
                    all_passed = False
                continue

            # 期望有效输入
            if not valid:
                print(f"  [FAIL] {desc}: 期望通过但被拒绝 ({err_code})")
                all_passed = False
                continue

            result = extract_key_info(text)
            # 宽松断言：置信度在合理范围
            if not (0 <= result["confidence"] <= 100):
                print(f"  [FAIL] {desc}: 置信度超出范围")
                all_passed = False
                continue

            # 统计特征合理
            if result["stats"]["total_chars"] <= 0:
                print(f"  [FAIL] {desc}: 字符统计异常")
                all_passed = False
                continue

            # 格式化输出不报错
            formatted = format_output(result, "text")
            if not formatted or len(formatted) < 10:
                print(f"  [FAIL] {desc}: 格式化输出异常")
                all_passed = False
                continue

            # JSON 格式验证
            json_out = format_output(result, "json")
            json.loads(json_out)  # 应能解析

            print(f"  [PASS] {desc}: 处理正常 (置信度 {result['confidence']}%)")

        except Exception as exc:
            print(f"  [FAIL] {desc}: 异常 {str(exc)}")
            all_passed = False

    # 批量处理测试
    print("  批量处理测试...")
    batch_inputs = ["第一个输入", "第二个输入", ""]
    batch_results = process_batch(batch_inputs)
    if len(batch_results) == 3:
        # 第三条应为错误
        if batch_results[2]["error"] == "E001":
            print("  [PASS] 批量处理: 正确识别空输入")
        else:
            print(f"  [FAIL] 批量处理: 空输入未正确识别, got {batch_results[2]['error']}")
            all_passed = False
    else:
        print(f"  [FAIL] 批量处理: 结果数量异常")
        all_passed = False

    print(f"=== 自检{'通过' if all_passed else '失败'} ===")
    return all_passed


def main():
    """CLI 入口函数。"""
    parser = argparse.ArgumentParser(
        description="AI应用构建器底座 - 处理文本输入并生成结构化结果"
    )
    parser.add_argument("input", nargs="?", help="输入文本或文件路径 (@前缀)")
    parser.add_argument("--file", "-f", help="从文件读取输入")
    parser.add_argument("--format", "-F", default="text",
                        choices=["text", "json", "table"],
                        help="输出格式")
    parser.add_argument("--batch", "-b", action="store_true",
                        help="批量模式（每行一个输入）")
    parser.add_argument("--dry-run", action="store_true",
                        help="预览模式（不实际写入）")
    parser.add_argument("--force", action="store_true",
                        help="强制写入（配合 --output 使用）")
    parser.add_argument("--output", "-o", help="输出文件路径")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="显示详细处理过程")
    parser.add_argument("--selftest", action="store_true",
                        help="运行内置自检")
    parser.add_argument("--threshold", type=float, default=None,
                        help="置信度阈值（0-100）")

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        sys.exit(0 if run_selftest() else 1)

    # 参数校验
    valid, err_code = validate_output_format(args.format)
    if not valid:
        print(f"错误 [{err_code}]: {ERROR_CODES[err_code]}", file=sys.stderr)
        sys.exit(1)

    valid, err_code = validate_confidence_threshold(args.threshold)
    if not valid:
        print(f"错误 [{err_code}]: {ERROR_CODES[err_code]}", file=sys.stderr)
        sys.exit(1)

    # 收集输入
    input_text = None
    try:
        if args.file:
            input_text = read_text_file(args.file)
        elif args.input:
            if args.input.startswith("@"):
                # @前缀表示文件路径
                filepath = args.input[1:]
                input_text = read_text_file(filepath)
            else:
                input_text = args.input
        else:
            # 从 stdin 读取
            if not sys.stdin.isatty():
                input_text = sys.stdin.read()
    except IOError as exc:
        print(f"错误 [E006]: {str(exc)}", file=sys.stderr)
        sys.exit(1)

    # 批量处理
    if args.batch and input_text:
        lines = [line.strip() for line in input_text.splitlines() if line.strip()]
        results = process_batch(lines, args.format)
        output_lines = []
        for i, res in enumerate(results, 1):
            if res["error"]:
                output_lines.append(f"#{i}: 错误 [{res['error']}] {res['error_msg']}")
            else:
                output_lines.append(f"#{i}:")
                output_lines.append(res["result"]["formatted"])
        output_text = "\n".join(output_lines)
    else:
        # 单条处理
        valid, err_code = validate_input(input_text)
        if not valid:
            print(f"错误 [{err_code}]: {ERROR_CODES[err_code]}", file=sys.stderr)
            sys.exit(1)

        result = extract_key_info(input_text)
        output_text = format_output(result, args.format)

        # verbose 模式输出处理明细
        if args.verbose:
            print("=== 处理明细 ===", file=sys.stderr)
            print(f"输入长度: {result['stats']['total_chars']}", file=sys.stderr)
            print(f"句子数: {result['stats']['sentence_count']}", file=sys.stderr)
            print(f"信息密度: {result['stats']['info_density']}", file=sys.stderr)
            print(f"提取关键点: {len(result['key_points'])} 条", file=sys.stderr)
            print(f"置信度: {result['confidence']}%", file=sys.stderr)
            print("", file=sys.stderr)

    # 输出
    if args.output:
        try:
            dry = args.dry_run and not args.force
            msg = write_text_file(args.output, output_text, dry_run=dry)
            print(msg)
        except IOError as exc:
            print(f"错误 [E007]: {str(exc)}", file=sys.stderr)
            sys.exit(1)
    else:
        print(output_text)


if __name__ == "__main__":
    main()
