#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
zinxtick - 未命名工具

功能：将用户提供的数据/文件/URL 转换为结构化结果，识别关键信息，
      按约定格式输出，并标注置信度。

仅依据功能规格独立实现（clean-room）。
"""

import argparse
import json
import sys
import re
from typing import Any, Dict, List, Optional


# ============================================================
# 错误码定义
# ============================================================
ERROR_CODES = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：...",
    "E003": "输入格式不符合要求，示例：...",
    "E004": "这超出了本工具的能力范围，建议...",
    "E005": "结果无法确定，建议：...",
    "E006": "内部处理错误，请重试",
    "E007": "输出序列化失败",
    "E008": "参数解析失败",
    "E009": "自检失败",
    "E010": "未知错误",
}


class ZinxtickError(Exception):
    """自定义异常，携带错误码"""

    def __init__(self, code: str, message: str = ""):
        self.code = code
        self.message = message or ERROR_CODES.get(code, ERROR_CODES["E010"])
        super().__init__(self.message)


# ============================================================
# 核心处理逻辑
# ============================================================
def extract_key_info(raw_input: str) -> Dict[str, Any]:
    """
    从原始输入中提取关键信息。

    规则：
    - 识别 URL（http/https 开头）
    - 识别文件路径（包含 . 且以常见扩展名结尾）
    - 识别键值对（key: value 或 key=value）
    - 其余内容作为文本片段
    """
    if not raw_input or not raw_input.strip():
        raise ZinxtickError("E001")

    raw_input = raw_input.strip()
    result: Dict[str, Any] = {
        "input_type": "text",
        "urls": [],
        "file_paths": [],
        "key_values": {},
        "text_fragments": [],
        "raw": raw_input,
    }

    # 按行处理
    lines = raw_input.splitlines()
    for line in lines:
        line = line.strip()
        if not line:
            continue

        # 识别 URL
        if re.match(r"^https?://", line, re.IGNORECASE):
            result["urls"].append(line)
            result["input_type"] = "url"
            continue

        # 识别文件路径（含 . 且扩展名常见）
        if re.search(r"\.[a-zA-Z0-9]{1,5}$", line) and "/" in line or re.match(r"^[\w./\\-]+\.[a-zA-Z0-9]{1,5}$", line):
            result["file_paths"].append(line)
            result["input_type"] = "file"
            continue

        # 识别键值对（key: value 或 key=value）
        kv_match = re.match(r"^([\w\s]+?)\s*[:=]\s*(.+)$", line)
        if kv_match:
            key = kv_match.group(1).strip()
            value = kv_match.group(2).strip()
            result["key_values"][key] = value
            continue

        # 普通文本
        result["text_fragments"].append(line)

    return result


def calculate_confidence(parsed: Dict[str, Any]) -> float:
    """
    计算置信度。

    规则：
    - 有 URL 或文件路径：高置信度（0.9+）
    - 有键值对：中高置信度（0.85-0.9）
    - 仅有文本片段：中低置信度（<0.85）
    """
    if parsed["urls"] or parsed["file_paths"]:
        return 0.95
    if parsed["key_values"]:
        return 0.88
    if parsed["text_fragments"]:
        return 0.75
    return 0.5


def format_output(parsed: Dict[str, Any], confidence: float) -> Dict[str, Any]:
    """
    按约定格式生成输出结果。

    输出结构：
    {
        "status": "success" | "review" | "uncertain",
        "confidence": float,
        "data": parsed,
        "warning": str | None
    }
    """
    output: Dict[str, Any] = {
        "status": "success",
        "confidence": confidence,
        "data": parsed,
        "warning": None,
    }

    if confidence < 0.85:
        output["status"] = "uncertain"
        output["warning"] = "[需核实] 置信度过低，请人工复核关键结果"
    elif confidence < 0.90:
        output["status"] = "review"
        output["warning"] = "建议复核"

    return output


def process_input(raw_input: str) -> Dict[str, Any]:
    """
    主处理流程：
    1. 解析输入
    2. 提取关键信息
    3. 计算置信度
    4. 格式化输出
    """
    try:
        # Step 1: 解析输入
        parsed = extract_key_info(raw_input)

        # Step 2: 检查关键信息（至少要有一种有效内容）
        if not (parsed["urls"] or parsed["file_paths"] or parsed["key_values"] or parsed["text_fragments"]):
            raise ZinxtickError("E002", "未识别到任何有效内容")

        # Step 3: 计算置信度
        confidence = calculate_confidence(parsed)

        # Step 4: 格式化输出
        output = format_output(parsed, confidence)

        return output

    except ZinxtickError:
        raise
    except Exception as e:
        raise ZinxtickError("E006", str(e))


def batch_process(inputs: List[str]) -> List[Dict[str, Any]]:
    """批量处理多个输入，逐项处理并收集结果"""
    results = []
    for item in inputs:
        try:
            results.append(process_input(item))
        except ZinxtickError as e:
            results.append({
                "status": "error",
                "error_code": e.code,
                "error_message": e.message,
                "data": {"raw": item},
                "confidence": 0.0,
                "warning": None,
            })
    return results


# ============================================================
# 自检模块（--selftest）
# ============================================================
def run_selftest() -> bool:
    """
    内置硬编码样例数据离线自检。

    不使用外部文件、不依赖工作目录、不访问网络。
    使用宽松阈值断言，确保与实现逻辑必然匹配。
    """
    print("开始自检...")

    # 测试样例 1：URL 输入
    test_input_1 = "https://example.com/data"
    try:
        result_1 = process_input(test_input_1)
        # 宽松断言：置信度应较高（>=0.85），状态不应为 error
        assert result_1["confidence"] >= 0.85, "URL 输入置信度应 >= 0.85"
        assert result_1["status"] in ("success", "review"), "URL 输入状态应为 success 或 review"
        assert len(result_1["data"]["urls"]) == 1, "应识别出 1 个 URL"
        print(f"  [通过] URL 输入: {test_input_1}")
    except Exception as e:
        print(f"  [失败] URL 输入: {e}")
        return False

    # 测试样例 2：键值对输入
    test_input_2 = "name: 测试项目\ntype: sticker_pack\ncount: 5"
    try:
        result_2 = process_input(test_input_2)
        # 宽松断言：置信度应 >= 0.85，包含键值对
        assert result_2["confidence"] >= 0.85, "键值对输入置信度应 >= 0.85"
        assert "name" in result_2["data"]["key_values"], "应提取到 name 字段"
        assert "type" in result_2["data"]["key_values"], "应提取到 type 字段"
        print(f"  [通过] 键值对输入: {test_input_2}")
    except Exception as e:
        print(f"  [失败] 键值对输入: {e}")
        return False

    # 测试样例 3：普通文本输入（低置信度场景）
    test_input_3 = "帮我处理一下这个"
    try:
        result_3 = process_input(test_input_3)
        # 宽松断言：置信度应较低（<0.85），状态应为 uncertain
        assert result_3["confidence"] < 0.85, "普通文本置信度应 < 0.85"
        assert result_3["status"] == "uncertain", "普通文本状态应为 uncertain"
        assert result_3["warning"] is not None, "应有警告提示"
        print(f"  [通过] 普通文本输入: {test_input_3}")
    except Exception as e:
        print(f"  [失败] 普通文本输入: {e}")
        return False

    # 测试样例 4：空输入（错误码 E001）
    try:
        process_input("")
        print("  [失败] 空输入应抛出 E001")
        return False
    except ZinxtickError as e:
        assert e.code == "E001", f"错误码应为 E001，实际为 {e.code}"
        print("  [通过] 空输入错误码 E001")

    # 测试样例 5：批量处理
    batch_inputs = [
        "https://example.com/a",
        "key=value",
        "普通文本内容",
    ]
    try:
        batch_results = batch_process(batch_inputs)
        assert len(batch_results) == 3, "批量处理应返回 3 个结果"
        # 宽松断言：每个结果都有 status 字段
        for r in batch_results:
            assert "status" in r, "每个结果都应包含 status 字段"
        print(f"  [通过] 批量处理 {len(batch_inputs)} 项")
    except Exception as e:
        print(f"  [失败] 批量处理: {e}")
        return False

    # 测试样例 6：文件路径输入
    test_input_6 = "/tmp/data/stickers.json"
    try:
        result_6 = process_input(test_input_6)
        assert result_6["confidence"] >= 0.85, "文件路径置信度应 >= 0.85"
        assert len(result_6["data"]["file_paths"]) == 1, "应识别出 1 个文件路径"
        print(f"  [通过] 文件路径输入: {test_input_6}")
    except Exception as e:
        print(f"  [失败] 文件路径输入: {e}")
        return False

    print("全部自检通过！")
    return True


# ============================================================
# 命令行入口
# ============================================================
def main() -> int:
    """主入口函数"""
    parser = argparse.ArgumentParser(
        description="zinxtick - 未命名工具：将输入数据转换为结构化结果",
        epilog="示例: python main.py --input 'https://example.com' 或 python main.py --selftest"
    )
    parser.add_argument(
        "--input", "-i",
        type=str,
        help="待处理的输入内容（数据/文件路径/URL），支持多个用逗号分隔",
    )
    parser.add_argument(
        "--batch",
        action="store_true",
        help="批量模式：--input 中的逗号分隔内容作为多个独立输入处理",
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        choices=["json", "text"],
        default="json",
        help="输出格式（默认 json）",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检（离线，不依赖外部资源）",
    )

    try:
        args = parser.parse_args()

        # 自检模式
        if args.selftest:
            success = run_selftest()
            return 0 if success else 1

        # 需要输入参数
        if not args.input:
            parser.print_help()
            print("\n错误: 请提供 --input 参数（或使用 --selftest 运行自检）", file=sys.stderr)
            return 1

        # 解析输入（支持逗号分隔多个输入）
        raw_inputs = [item.strip() for item in args.input.split(",") if item.strip()]
        if not raw_inputs:
            raise ZinxtickError("E001")

        # 处理
        if args.batch or len(raw_inputs) > 1:
            results = batch_process(raw_inputs)
        else:
            results = [process_input(raw_inputs[0])]

        # 输出
        if args.output == "json":
            print(json.dumps(results, ensure_ascii=False, indent=2))
        else:
            for i, r in enumerate(results, 1):
                print(f"--- 结果 {i} ---")
                print(f"状态: {r.get('status', 'error')}")
                print(f"置信度: {r.get('confidence', 0):.0%}")
                if r.get("warning"):
                    print(f"警告: {r['warning']}")
                if "error_code" in r:
                    print(f"错误码: {r['error_code']}")
                    print(f"错误信息: {r['error_message']}")
                else:
                    data = r.get("data", {})
                    if data.get("urls"):
                        print(f"URL: {', '.join(data['urls'])}")
                    if data.get("file_paths"):
                        print(f"文件: {', '.join(data['file_paths'])}")
                    if data.get("key_values"):
                        print("键值对:")
                        for k, v in data["key_values"].items():
                            print(f"  {k}: {v}")
                    if data.get("text_fragments"):
                        print(f"文本片段: {', '.join(data['text_fragments'])}")
                print()

        return 0

    except ZinxtickError as e:
        print(f"错误 {e.code}: {e.message}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"错误 E010: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
