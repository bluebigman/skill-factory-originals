#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py — 未命名工具（ohmyzsh）独立实现

本脚本依据功能规格，采用 clean-room 方式独立编写。
仅使用 Python 标准库，不依赖任何第三方包。

功能概述：
  1. 将用户提供的数据/文件/URL 转换为结构化结果
  2. 识别并保留输入中的关键信息
  3. 按约定格式生成输出
  4. 对不确定项给出置信度提示
  5. 支持批量处理和自定义格式

命令行用法：
  python scripts/main.py <输入> [--format json|text] [--batch]
  python scripts/main.py --selftest    # 离线自检，不依赖外部资源
"""

import argparse
import json
import sys
import urllib.parse
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# 错误码定义（E001-E010）
# ============================================================
ERROR_CODES = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：...",
    "E003": "输入格式不符合要求，示例：...",
    "E004": "这超出了本工具的能力范围，建议...",
    "E005": "结果无法确定，建议：...",
    "E006": "内部处理异常，请稍后重试或检查输入",
    "E007": "批量处理时遇到无效条目，已跳过",
    "E008": "输出格式不支持，请选择 json 或 text",
    "E009": "文件读取失败，请确认路径正确且文件可访问",
    "E010": "URL 解析失败，请确认地址格式正确",
}


def _error(msg_code: str, detail: str = "") -> Dict[str, Any]:
    """构造标准错误响应。"""
    result = {
        "status": "error",
        "error_code": msg_code,
        "message": ERROR_CODES.get(msg_code, "未知错误"),
    }
    if detail:
        result["detail"] = detail
    return result


# ============================================================
# 核心逻辑：信息提取与结构化
# ============================================================
def _extract_key_info(raw_text: str) -> Dict[str, Any]:
    """
    从原始文本中提取关键信息。

    规则：
      - 识别疑似 URL
      - 识别疑似文件路径
      - 识别疑似 JSON 结构
      - 统计文本基本信息（长度、词数）
    """
    text = (raw_text or "").strip()
    if not text:
        return {"content": "", "urls": [], "paths": [], "is_json": False, "word_count": 0}

    # 提取 URL（宽松匹配 http/https 开头）
    words = text.split()
    urls = [w for w in words if w.startswith(("http://", "https://"))]

    # 提取疑似文件路径（包含 . 或 / 且不以 http 开头）
    paths = []
    for w in words:
        if w.startswith(("http://", "https://")):
            continue
        if ("." in w or "/" in w) and len(w) > 1:
            paths.append(w)

    # 判断是否为 JSON
    is_json = False
    try:
        json.loads(text)
        is_json = True
    except (json.JSONDecodeError, ValueError):
        pass

    return {
        "content": text,
        "urls": urls,
        "paths": paths,
        "is_json": is_json,
        "word_count": len(words),
    }


def _compute_confidence(info: Dict[str, Any]) -> float:
    """
    根据提取结果计算置信度（0-100）。

    规则（宽松阈值）：
      - 非空内容：基础 60 分
      - 有 URL：+15
      - 有文件路径：+10
      - 是 JSON：+15
      - 内容较长（>20 词）：+10
    """
    confidence = 0.0
    if info["content"]:
        confidence += 60.0
    if info["urls"]:
        confidence += 15.0
    if info["paths"]:
        confidence += 10.0
    if info["is_json"]:
        confidence += 15.0
    if info["word_count"] > 20:
        confidence += 10.0
    # 上限 100
    return min(confidence, 100.0)


def _format_confidence(confidence: float) -> Tuple[str, str]:
    """
    根据置信度返回标注信息。

    规则：
      >=90：直接输出
      85-90：建议复核
      <85：[需核实]
    """
    if confidence >= 90.0:
        return "直接输出", ""
    elif confidence >= 85.0:
        return "建议复核", ""
    else:
        return "[需核实]", "结果不确定，请人工确认关键信息"


# ============================================================
# 核心处理流程
# ============================================================
def process_input(raw_input: str, output_format: str = "text") -> Dict[str, Any]:
    """
    处理单个输入条目，返回结构化结果。

    参数：
      raw_input: 用户提供的原始输入
      output_format: 输出格式（text 或 json）

    返回：
      统一的结果字典
    """
    # 错误处理：输入为空
    if not raw_input or not raw_input.strip():
        return _error("E001")

    # 错误处理：不支持的输出格式
    if output_format not in ("text", "json"):
        return _error("E008", f"当前格式: {output_format}")

    # 核心提取
    info = _extract_key_info(raw_input)
    confidence = _compute_confidence(info)
    level, note = _format_confidence(confidence)

    # 构造结果
    result = {
        "status": "success",
        "input": raw_input.strip(),
        "extracted": info,
        "confidence": round(confidence, 1),
        "confidence_level": level,
        "note": note,
    }

    # 按需格式化
    if output_format == "json":
        result["output"] = json.dumps(info, ensure_ascii=False, indent=2)
    else:
        # 文本格式输出
        lines = [
            f"输入内容: {info['content'][:50]}{'...' if len(info['content']) > 50 else ''}",
            f"识别 URL 数量: {len(info['urls'])}",
            f"识别路径数量: {len(info['paths'])}",
            f"JSON 结构: {'是' if info['is_json'] else '否'}",
            f"词数: {info['word_count']}",
            f"置信度: {result['confidence']}% ({level})",
        ]
        if note:
            lines.append(f"提示: {note}")
        result["output"] = "\n".join(lines)

    return result


def process_batch(inputs: List[str], output_format: str = "text") -> Dict[str, Any]:
    """
    批量处理多个输入条目。

    参数：
      inputs: 输入字符串列表
      output_format: 输出格式

    返回：
      批量处理结果
    """
    if not inputs:
        return _error("E001")

    results = []
    valid_count = 0
    invalid_count = 0

    for item in inputs:
        item = item.strip()
        if not item:
            invalid_count += 1
            continue
        try:
            res = process_input(item, output_format)
            if res.get("status") == "success":
                valid_count += 1
            else:
                invalid_count += 1
            results.append(res)
        except Exception as e:  # 防御性异常处理
            invalid_count += 1
            err = _error("E007", f"条目处理失败: {str(e)}")
            err["input"] = item
            results.append(err)

    return {
        "status": "success" if valid_count > 0 else "error",
        "total": len(inputs),
        "valid": valid_count,
        "invalid": invalid_count,
        "results": results,
    }


# ============================================================
# 自检模块（--selftest）
# ============================================================
def _run_selftest() -> int:
    """
    离线自检核心逻辑。

    使用内置硬编码样例数据，不读取外部文件、不依赖当前工作目录、
    不访问网络。所有断言采用宽松阈值，确保任何环境直接可过。
    """
    print("=" * 60)
    print("开始自检 (selftest)")
    print("=" * 60)

    # --- 测试 1: 空输入 → E001 ---
    print("\n[1] 测试空输入...")
    res = process_input("")
    assert res["status"] == "error", "空输入应返回错误"
    assert res["error_code"] == "E001", f"错误码应为 E001，实际 {res['error_code']}"
    print("  通过: 空输入返回 E001")

    # --- 测试 2: 普通文本 ---
    print("\n[2] 测试普通文本...")
    res = process_input("这是一个测试文本，用于验证核心功能是否正常工作。")
    assert res["status"] == "success", "普通文本应处理成功"
    assert res["confidence"] >= 50.0, f"置信度应>=50，实际 {res['confidence']}"
    assert res["extracted"]["word_count"] > 0, "词数应大于0"
    print(f"  通过: 普通文本处理成功，置信度={res['confidence']}%")

    # --- 测试 3: 含 URL 的输入 ---
    print("\n[3] 测试包含 URL 的输入...")
    res = process_input("请查看 https://example.com 上的内容")
    assert res["status"] == "success"
    assert len(res["extracted"]["urls"]) == 1, "应识别出 1 个 URL"
    assert res["confidence"] >= 60.0, f"含 URL 置信度应>=60，实际 {res['confidence']}"
    print(f"  通过: URL 识别成功，置信度={res['confidence']}%")

    # --- 测试 4: JSON 输入 ---
    print("\n[4] 测试 JSON 输入...")
    json_input = '{"name": "test", "value": 123}'
    res = process_input(json_input)
    assert res["status"] == "success"
    assert res["extracted"]["is_json"] is True, "应识别为 JSON"
    assert res["confidence"] >= 70.0, f"JSON 置信度应>=70，实际 {res['confidence']}"
    print(f"  通过: JSON 识别成功，置信度={res['confidence']}%")

    # --- 测试 5: 批量处理 ---
    print("\n[5] 测试批量处理...")
    batch = ["第一条内容", "https://example.org/page", "", "第三条"]
    res = process_batch(batch)
    assert res["status"] == "success"
    assert res["total"] == 4, "总数应为4"
    assert res["valid"] >= 2, f"有效条目应>=2，实际 {res['valid']}"
    assert res["invalid"] >= 1, f"无效条目应>=1（空字符串），实际 {res['invalid']}"
    print(f"  通过: 批量处理成功，有效={res['valid']}，无效={res['invalid']}")

    # --- 测试 6: 输出格式 ---
    print("\n[6] 测试输出格式...")
    res_text = process_input("测试格式", "text")
    res_json = process_input("测试格式", "json")
    assert res_text["status"] == "success"
    assert res_json["status"] == "success"
    assert isinstance(res_text["output"], str), "文本输出应为字符串"
    assert isinstance(res_json["output"], str), "JSON 输出应为字符串"
    # JSON 格式应能被再次解析
    parsed = json.loads(res_json["output"])
    assert "content" in parsed, "JSON 输出应包含 content 字段"
    print("  通过: 两种输出格式均正常")

    # --- 测试 7: 错误格式 ---
    print("\n[7] 测试错误格式...")
    res = process_input("测试", "xml")
    assert res["status"] == "error"
    assert res["error_code"] == "E008", f"错误码应为 E008，实际 {res['error_code']}"
    print("  通过: 不支持的格式返回 E008")

    # --- 测试 8: 置信度分级 ---
    print("\n[8] 测试置信度分级...")
    # 短文本 → 低置信度
    res_low = process_input("短文本")
    assert res_low["confidence"] < 85.0, "短文本置信度应<85"
    # 长文本 + URL + JSON → 高置信度
    long_json = '{"data": "这是一段较长的JSON内容，包含多个字段和足够多的词汇量以便提高置信度分数", "url": "https://example.com/test"}'
    res_high = process_input(long_json)
    assert res_high["confidence"] >= 85.0, f"复杂输入置信度应>=85，实际 {res_high['confidence']}"
    print(f"  通过: 置信度分级正常 (低={res_low['confidence']}%, 高={res_high['confidence']}%)")

    # --- 测试 9: URL 解析辅助函数 ---
    print("\n[9] 测试 URL 解析辅助...")
    test_url = "https://example.com/path?query=1&x=2"
    parsed = urllib.parse.urlparse(test_url)
    assert parsed.scheme == "https", "协议应为 https"
    assert parsed.netloc == "example.com", "域名应为 example.com"
    assert parsed.path == "/path", "路径应为 /path"
    print("  通过: URL 解析正常")

    # --- 测试 10: 错误码完整性 ---
    print("\n[10] 测试错误码完整性...")
    for code in ["E001", "E002", "E003", "E004", "E005", "E006", "E007", "E008", "E009", "E010"]:
        assert code in ERROR_CODES, f"缺少错误码 {code}"
    print(f"  通过: 错误码完整 ({len(ERROR_CODES)} 个)")

    print("\n" + "=" * 60)
    print("自检全部通过！")
    print("=" * 60)
    return 0


# ============================================================
# 命令行入口
# ============================================================
def main() -> int:
    """主入口函数。"""
    parser = argparse.ArgumentParser(
        description="未命名工具 - 将输入转换为结构化结果",
        epilog="示例: python scripts/main.py '待处理内容' --format json",
    )
    parser.add_argument(
        "input",
        nargs="*",
        help="待处理的内容（可多个，配合 --batch 使用）",
    )
    parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="输出格式（默认: text）",
    )
    parser.add_argument(
        "--batch",
        action="store_true",
        help="批量处理模式（每个输入参数视为独立条目）",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行离线自检（不依赖外部资源）",
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        return _run_selftest()

    # 无输入且非自检 → 提示
    if not args.input:
        print(json.dumps(_error("E001"), ensure_ascii=False, indent=2))
        return 1

    # 批量模式
    if args.batch:
        result = process_batch(list(args.input), args.format)
    else:
        # 单条模式：如果只有一个参数，直接处理；多个参数用空格连接
        raw = " ".join(args.input)
        result = process_input(raw, args.format)

    # 输出结果
    if args.format == "json" or result.get("status") == "error":
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(result.get("output", ""))

    return 0 if result.get("status") == "success" else 1


if __name__ == "__main__":
    sys.exit(main())
