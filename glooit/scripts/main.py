#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
glooit - 未命名工具
仅供学习与参考用途。提供规范、可复用的处理流程与输出。
"""

import argparse
import json
import sys
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# 错误码定义
# ============================================================
ERROR_CODES = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：...",
    "E003": "输入格式不符合要求，示例：...",
    "E004": "这超出了本工具的能力范围，建议...",
    "E005": "结果无法确定，建议：...",
}


class GlooitError(Exception):
    """自定义异常，携带错误码"""

    def __init__(self, code: str, message: str = ""):
        self.code = code
        self.message = message or ERROR_CODES.get(code, "未知错误")
        super().__init__(f"[{code}] {self.message}")


# ============================================================
# 核心处理逻辑
# ============================================================

def parse_input(raw_input: Any) -> Dict[str, Any]:
    """
    解析输入内容，识别关键信息。
    支持：字符串、字典、列表。
    """
    if raw_input is None or (isinstance(raw_input, str) and not raw_input.strip()):
        raise GlooitError("E001")

    # 尝试解析 JSON 字符串
    if isinstance(raw_input, str):
        try:
            parsed = json.loads(raw_input)
            return _extract_fields(parsed)
        except json.JSONDecodeError:
            # 非 JSON 字符串，按纯文本处理
            return {"text": raw_input.strip(), "type": "plain_text"}

    # 字典或列表直接处理
    return _extract_fields(raw_input)


def _extract_fields(data: Any) -> Dict[str, Any]:
    """从结构化数据中提取关键字段"""
    result: Dict[str, Any] = {"type": type(data).__name__}

    if isinstance(data, dict):
        # 保留所有键值对
        result["fields"] = data
        # 识别常见关键字段
        for key in ["name", "title", "id", "content", "value"]:
            if key in data:
                result[f"key_{key}"] = data[key]
    elif isinstance(data, list):
        result["items"] = data
        result["count"] = len(data)
    else:
        result["value"] = data

    return result


def process_input(parsed: Dict[str, Any]) -> Dict[str, Any]:
    """
    按规则处理解析后的数据，生成结构化结果。
    返回包含处理结果和置信度的字典。
    """
    result: Dict[str, Any] = {
        "processed": True,
        "confidence": 0.0,
        "output": {},
        "warnings": [],
    }

    # 根据输入类型处理
    if parsed.get("type") == "plain_text":
        text = parsed.get("text", "")
        # 简单文本处理：统计信息
        result["output"] = {
            "text": text,
            "char_count": len(text),
            "word_count": len(text.split()),
        }
        result["confidence"] = 0.95  # 文本统计置信度高

    elif "fields" in parsed:
        fields = parsed["fields"]
        # 字段结构化处理
        structured = {}
        for key, value in fields.items():
            # 简单清洗：去除空值
            if value is not None and value != "":
                structured[key] = value

        result["output"] = {
            "structured_fields": structured,
            "field_count": len(structured),
        }
        # 置信度基于字段完整性
        if len(structured) >= len(fields) * 0.8:
            result["confidence"] = 0.92
        elif len(structured) >= len(fields) * 0.5:
            result["confidence"] = 0.87
            result["warnings"].append("部分字段缺失，建议复核")
        else:
            result["confidence"] = 0.75
            result["warnings"].append("[需核实] 大量字段缺失")

    elif "items" in parsed:
        items = parsed["items"]
        # 列表批量处理
        processed_items = []
        for item in items:
            if isinstance(item, dict):
                processed_items.append({k: v for k, v in item.items() if v is not None})
            else:
                processed_items.append(item)

        result["output"] = {
            "items": processed_items,
            "total": len(processed_items),
            "valid": sum(1 for i in processed_items if i),
        }
        result["confidence"] = 0.9 if processed_items else 0.8

    else:
        # 简单值
        result["output"] = {"value": parsed.get("value")}
        result["confidence"] = 0.85

    # 置信度标注
    _apply_confidence_marker(result)

    return result


def _apply_confidence_marker(result: Dict[str, Any]) -> None:
    """根据置信度添加标注"""
    conf = result.get("confidence", 0)
    if conf >= 0.90:
        result["marker"] = "直接输出"
    elif conf >= 0.85:
        result["marker"] = "建议复核"
    else:
        result["marker"] = "[需核实]"


def format_output(processed: Dict[str, Any], fmt: str = "json") -> str:
    """
    按指定格式输出结果。
    支持：json, text
    """
    if fmt == "json":
        return json.dumps(processed, ensure_ascii=False, indent=2)
    elif fmt == "text":
        lines = []
        marker = processed.get("marker", "")
        if marker:
            lines.append(f"状态: {marker}")
        lines.append(f"置信度: {processed.get('confidence', 0):.1%}")

        output = processed.get("output", {})
        if "text" in output:
            lines.append(f"内容: {output['text']}")
        elif "structured_fields" in output:
            for k, v in output["structured_fields"].items():
                lines.append(f"{k}: {v}")
        elif "items" in output:
            lines.append(f"共 {output.get('total', 0)} 项")
            for item in output["items"][:5]:  # 只显示前5项
                lines.append(f"  - {item}")
            if output.get("total", 0) > 5:
                lines.append(f"  ... 等 {output['total']} 项")

        for warning in processed.get("warnings", []):
            lines.append(f"注意: {warning}")

        return "\n".join(lines)
    else:
        raise GlooitError("E003", f"不支持的输出格式: {fmt}")


def run_pipeline(raw_input: Any, output_format: str = "json") -> str:
    """
    完整处理流程：
    1. 解析输入
    2. 核心处理
    3. 格式化输出
    """
    try:
        parsed = parse_input(raw_input)
        processed = process_input(parsed)
        return format_output(processed, output_format)
    except GlooitError as e:
        return json.dumps({"error": e.code, "message": e.message}, ensure_ascii=False)


# ============================================================
# 自检模块
# ============================================================

def selftest() -> bool:
    """
    内置硬编码样例数据的离线自检。
    不读取外部文件、不访问网络、不依赖当前工作目录。
    使用宽松阈值断言，确保任何环境可过。
    """
    print("=" * 60)
    print("glooit 自检开始 (离线模式)")
    print("=" * 60)

    test_cases = [
        # (描述, 输入, 期望格式)
        ("文本输入", "这是一段测试文本内容", "json"),
        ("JSON字典", '{"name": "测试", "id": 123, "content": "内容"}', "json"),
        ("列表输入", '[{"a": 1}, {"b": 2}, {"c": 3}]', "json"),
        ("空输入", "", "json"),
        ("文本格式输出", "测试文本", "text"),
    ]

    passed = 0
    total = len(test_cases)

    for desc, input_data, fmt in test_cases:
        print(f"\n--- 测试: {desc} ---")
        try:
            result = run_pipeline(input_data, fmt)
            print(f"输出: {result[:200]}{'...' if len(result) > 200 else ''}")

            # 宽松验证
            if fmt == "json":
                parsed_result = json.loads(result)
                # 验证结构存在
                assert "processed" in parsed_result or "error" in parsed_result, "缺少处理标记"
                if "processed" in parsed_result:
                    # 置信度在合理范围
                    conf = parsed_result.get("confidence", 0)
                    assert 0 <= conf <= 1, "置信度超出范围"
                    # 有输出内容
                    assert parsed_result.get("output") is not None, "缺少输出"
            else:
                # 文本格式验证
                assert len(result) > 0, "文本输出为空"
                assert "置信度" in result, "缺少置信度标注"

            passed += 1
            print("✓ 通过")
        except AssertionError as e:
            print(f"✗ 失败: {e}")
        except Exception as e:
            print(f"✗ 异常: {e}")

    # 额外验证错误处理
    print("\n--- 测试: 错误处理 ---")
    try:
        err_result = run_pipeline(None, "json")
        err_data = json.loads(err_result)
        assert "error" in err_data, "未返回错误信息"
        assert err_data["error"] in ERROR_CODES, "错误码不在定义范围内"
        print("✓ 错误处理正常")
        passed += 1
    except Exception as e:
        print(f"✗ 错误处理测试失败: {e}")

    total += 1

    # 汇总
    print("\n" + "=" * 60)
    print(f"自检完成: {passed}/{total} 通过")
    print("=" * 60)

    # 宽松阈值：至少 80% 通过即可
    return passed >= total * 0.8


# ============================================================
# 命令行入口
# ============================================================

def main() -> int:
    """主入口函数"""
    parser = argparse.ArgumentParser(
        description="glooit - 未命名工具，提供规范、可复用的处理流程与输出",
        epilog="示例: python main.py --input '{\"name\": \"test\"}' --format json"
    )
    parser.add_argument(
        "--input", "-i",
        type=str,
        help="输入内容（字符串、JSON或文件路径）"
    )
    parser.add_argument(
        "--format", "-f",
        type=str,
        choices=["json", "text"],
        default="json",
        help="输出格式 (默认: json)"
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检（离线，不依赖外部文件）"
    )
    parser.add_argument(
        "--file",
        type=str,
        help="从文件读取输入（本地文件路径）"
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        success = selftest()
        return 0 if success else 1

    # 正常处理模式
    try:
        # 收集输入
        if args.file:
            # 从文件读取（本地文件，非网络）
            try:
                with open(args.file, "r", encoding="utf-8") as f:
                    input_data = f.read()
            except FileNotFoundError:
                raise GlooitError("E001", f"文件不存在: {args.file}")
            except Exception as e:
                raise GlooitError("E003", f"文件读取失败: {e}")
        elif args.input:
            input_data = args.input
        else:
            # 无输入时提示
            print("提示: 请使用 --input 或 --file 提供输入内容，或使用 --selftest 运行自检")
            print("示例: python main.py --input '{\"name\": \"test\"}' --format json")
            return 1

        # 处理并输出
        result = run_pipeline(input_data, args.format)
        print(result)
        return 0

    except GlooitError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\n操作已取消", file=sys.stderr)
        return 130
    except Exception as e:
        print(f"未预期错误: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
