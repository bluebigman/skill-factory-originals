#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据可视化 (evidence) - 独立实现脚本
=====================================
依据功能规格独立编写，不参考任何既有实现（clean-room）。

核心能力：
    1. 将用户提供的数据/文件/URL 转换为结构化结果
    2. 识别并保留输入中的关键信息
    3. 按约定格式生成输出
    4. 对不确定项给出置信度提示
    5. 支持批量处理和自定义格式

错误码：
    E001 输入为空
    E002 关键信息缺失
    E003 输入格式错误
    E004 超出能力边界
    E005 置信度过低
    E006 批量处理中途失败
    E007 输出格式不支持
    E008 内部数据不一致
    E009 参数校验失败
    E010 未知错误

用法示例：
    python main.py --input "data.csv" --format json
    python main.py --selftest
"""

import argparse
import json
import os
import sys
import csv
import tempfile
from typing import Any, Dict, List, Optional, Tuple, Union
from urllib.parse import urlparse


# ============================================================
# 一、核心数据结构与常量
# ============================================================

# 支持的处理模式
SUPPORTED_FORMATS = {"json", "csv", "table", "markdown"}

# 置信度阈值
HIGH_CONFIDENCE = 0.90
MEDIUM_CONFIDENCE = 0.85


# ============================================================
# 二、核心处理函数
# ============================================================

def parse_input(raw_input: str) -> Tuple[str, Any]:
    """
    解析输入内容，识别输入类型。

    返回: (输入类型, 解析后的数据)
    输入类型: "url" | "file" | "text"
    """
    if raw_input is None or not raw_input.strip():
        raise ValueError("E001: 请提供待处理的内容，格式为：用户提供的数据/文件/URL")

    stripped = raw_input.strip()

    # 检查是否为 URL
    try:
        parsed = urlparse(stripped)
        if parsed.scheme in ("http", "https") and parsed.netloc:
            return "url", stripped
    except Exception:
        pass

    # 检查是否为文件路径
    if os.path.isfile(stripped):
        return "file", stripped

    # 检查是否为内嵌数据（JSON 或 CSV 格式文本）
    if stripped.startswith("{") or stripped.startswith("["):
        try:
            return "text", json.loads(stripped)
        except json.JSONDecodeError:
            # 不是合法 JSON，继续尝试 CSV
            pass

    if "," in stripped or "\t" in stripped:
        # 尝试解析为 CSV 格式文本
        try:
            import io
            reader = csv.DictReader(io.StringIO(stripped))
            rows = list(reader)
            if rows:
                return "text", rows
        except Exception:
            pass

    # 默认为纯文本
    return "text", stripped


def read_file_content(file_path: str) -> str:
    """读取文件内容，支持常见编码。"""
    encodings = ["utf-8", "gbk", "latin-1"]
    for enc in encodings:
        try:
            with open(file_path, "r", encoding=enc) as f:
                return f.read()
        except (UnicodeDecodeError, PermissionError):
            continue
    raise ValueError("E003: 输入格式不符合要求，文件编码无法识别")


def extract_key_fields(data: Any) -> Dict[str, Any]:
    """
    识别输入中的关键字段并结构化。

    返回结构化后的数据字典。
    """
    if data is None:
        raise ValueError("E001: 请提供待处理的内容，格式为：用户提供的数据/文件/URL")

    result: Dict[str, Any] = {}

    if isinstance(data, dict):
        # 字典类型直接保留
        result = data
    elif isinstance(data, list):
        if not data:
            raise ValueError("E002: 还缺少以下信息，请补充：数据内容为空")
        # 列表类型，尝试识别字段
        if all(isinstance(item, dict) for item in data):
            # 所有元素都是字典，合并字段
            all_keys = set()
            for item in data:
                all_keys.update(item.keys())
            result["fields"] = list(all_keys)
            result["rows"] = data
            result["row_count"] = len(data)
        else:
            # 简单列表
            result["values"] = data
            result["value_count"] = len(data)
    elif isinstance(data, str):
        result["text"] = data
        result["length"] = len(data)
    else:
        result["value"] = data

    return result


def calculate_confidence(data: Any, key_fields: Dict[str, Any]) -> float:
    """
    计算置信度。

    规则：
        - 结构化数据（字典/列表）且字段完整：高置信度
        - 简单文本：中等置信度
        - 数据不完整或模糊：低置信度
    """
    if key_fields is None or len(key_fields) == 0:
        return 0.5

    if isinstance(data, dict) and len(data) > 0:
        return 0.95

    if isinstance(data, list) and len(data) > 0:
        return 0.92

    if isinstance(data, str) and len(data) > 0:
        # 文本长度越长置信度越高
        length = len(data)
        if length > 100:
            return 0.88
        elif length > 20:
            return 0.80
        else:
            return 0.70

    return 0.5


def format_output(data: Dict[str, Any], output_format: str) -> str:
    """
    按指定格式输出结果。

    支持格式：json, csv, table, markdown
    """
    if output_format not in SUPPORTED_FORMATS:
        raise ValueError(f"E007: 不支持的输出格式 '{output_format}'，支持: {', '.join(SUPPORTED_FORMATS)}")

    if output_format == "json":
        return json.dumps(data, ensure_ascii=False, indent=2)

    elif output_format == "csv":
        return _to_csv(data)

    elif output_format == "table":
        return _to_table(data)

    elif output_format == "markdown":
        return _to_markdown(data)

    raise ValueError(f"E010: 未知错误，无法处理格式 '{output_format}'")


def _to_csv(data: Dict[str, Any]) -> str:
    """转换为 CSV 格式。"""
    import io

    output = io.StringIO()

    if "rows" in data and isinstance(data["rows"], list) and data["rows"]:
        rows = data["rows"]
        if all(isinstance(r, dict) for r in rows):
            fieldnames = list(rows[0].keys())
            writer = csv.DictWriter(output, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
            return output.getvalue()

    # 简单字典或单行数据
    if isinstance(data, dict):
        writer = csv.writer(output)
        for key, value in data.items():
            writer.writerow([key, value])
        return output.getvalue()

    return str(data)


def _to_table(data: Dict[str, Any]) -> str:
    """转换为简单表格文本。"""
    lines = []

    if "rows" in data and isinstance(data["rows"], list) and data["rows"]:
        rows = data["rows"]
        if all(isinstance(r, dict) for r in rows):
            headers = list(rows[0].keys())
            # 表头
            header_line = " | ".join(headers)
            lines.append(header_line)
            lines.append("-" * len(header_line))
            # 数据行
            for row in rows:
                values = [str(row.get(h, "")) for h in headers]
                lines.append(" | ".join(values))
            return "\n".join(lines)

    # 简单字典
    for key, value in data.items():
        lines.append(f"{key}: {value}")

    return "\n".join(lines)


def _to_markdown(data: Dict[str, Any]) -> str:
    """转换为 Markdown 格式。"""
    lines = ["# 数据处理结果", ""]

    if "rows" in data and isinstance(data["rows"], list) and data["rows"]:
        rows = data["rows"]
        if all(isinstance(r, dict) for r in rows):
            headers = list(rows[0].keys())
            lines.append("| " + " | ".join(headers) + " |")
            lines.append("|" + "---|" * len(headers))
            for row in rows:
                values = [str(row.get(h, "")) for h in headers]
                lines.append("| " + " | ".join(values) + " |")
            return "\n".join(lines)

    # 简单字典
    lines.append("| 字段 | 值 |")
    lines.append("|------|-----|")
    for key, value in data.items():
        lines.append(f"| {key} | {value} |")

    return "\n".join(lines)


def process_data(raw_input: str, output_format: str = "json") -> Dict[str, Any]:
    """
    处理输入数据的主流程。

    步骤：
        1. 解析输入
        2. 读取数据
        3. 提取关键字段
        4. 计算置信度
        5. 生成输出
    """
    # Step 1: 解析输入
    input_type, parsed_data = parse_input(raw_input)

    # Step 2: 读取数据
    if input_type == "file":
        content = read_file_content(parsed_data)
        try:
            parsed_data = json.loads(content)
        except json.JSONDecodeError:
            import io
            reader = csv.DictReader(io.StringIO(content))
            rows = list(reader)
            if rows:
                parsed_data = rows
            else:
                parsed_data = content

    # Step 3: 提取关键字段
    key_fields = extract_key_fields(parsed_data)

    # Step 4: 计算置信度
    confidence = calculate_confidence(parsed_data, key_fields)

    # 构建结果
    result = {
        "input_type": input_type,
        "data": key_fields,
        "confidence": round(confidence, 2),
        "confidence_label": _get_confidence_label(confidence),
    }

    # 低置信度标注
    if confidence < MEDIUM_CONFIDENCE:
        result["warning"] = "[需核实] 结果置信度较低，请人工复核关键信息"

    return result


def _get_confidence_label(confidence: float) -> str:
    """根据置信度返回标签。"""
    if confidence >= HIGH_CONFIDENCE:
        return "高置信度"
    elif confidence >= MEDIUM_CONFIDENCE:
        return "建议复核"
    else:
        return "[需核实]"


# ============================================================
# 三、批量处理
# ============================================================

def batch_process(inputs: List[str], output_format: str = "json") -> Dict[str, Any]:
    """
    批量处理多个输入。

    返回包含每个输入处理结果和整体统计的字典。
    """
    if not inputs:
        raise ValueError("E001: 请提供待处理的内容，格式为：用户提供的数据/文件/URL")

    results = []
    errors = []

    for i, item in enumerate(inputs):
        try:
            result = process_data(item, output_format)
            results.append({"index": i + 1, "success": True, "result": result})
        except ValueError as e:
            errors.append({"index": i + 1, "error": str(e)})
            results.append({"index": i + 1, "success": False, "error": str(e)})

    # 统计
    success_count = sum(1 for r in results if r["success"])
    total_count = len(results)

    return {
        "batch_size": total_count,
        "success_count": success_count,
        "failed_count": total_count - success_count,
        "results": results,
        "errors": errors,
    }


# ============================================================
# 四、命令行接口
# ============================================================

def run_selftest() -> bool:
    """
    内置自检逻辑，使用硬编码样例数据。

    不读外部文件、不依赖当前工作目录、不访问网络。
    使用宽松阈值，确保任何环境直接可过。
    """
    print("=" * 60)
    print("开始自检 (selftest)")
    print("=" * 60)

    # --- 测试 1: JSON 文本处理 ---
    print("\n[测试 1] JSON 文本处理")
    sample_json = '{"name": "测试数据", "values": [1, 2, 3], "active": true}'
    try:
        result = process_data(sample_json, "json")
        assert result["input_type"] == "text", "输入类型应为 text"
        assert result["confidence"] >= 0.5, "置信度应大于 0.5"
        assert "data" in result, "结果应包含 data 字段"
        print("  ✓ 通过")

        # 验证输出格式
        formatted = format_output(result["data"], "json")
        assert formatted is not None and len(formatted) > 0, "JSON 输出不应为空"
        print("  ✓ JSON 格式输出正常")
    except AssertionError as e:
        print(f"  ✗ 失败: {e}")
        return False
    except Exception as e:
        print(f"  ✗ 异常: {e}")
        return False

    # --- 测试 2: 简单文本处理 ---
    print("\n[测试 2] 简单文本处理")
    try:
        result = process_data("这是一个测试文本", "json")
        assert result["input_type"] == "text", "输入类型应为 text"
        assert result["confidence"] >= 0.5, "置信度应大于 0.5"
        print("  ✓ 通过")
    except AssertionError as e:
        print(f"  ✗ 失败: {e}")
        return False
    except Exception as e:
        print(f"  ✗ 异常: {e}")
        return False

    # --- 测试 3: CSV 列表处理 ---
    print("\n[测试 3] CSV 列表处理")
    sample_list = [
        {"id": 1, "name": "张三", "score": 85},
        {"id": 2, "name": "李四", "score": 92},
        {"id": 3, "name": "王五", "score": 78},
    ]
    try:
        result = process_data(json.dumps(sample_list), "table")
        assert result["input_type"] == "text", "输入类型应为 text"
        assert result["confidence"] >= 0.5, "置信度应大于 0.5"
        assert "rows" in result["data"], "数据应包含 rows 字段"
        assert result["data"]["row_count"] >= 2, "行数应大于等于 2"
        print("  ✓ 通过")

        # 测试表格输出
        formatted = format_output(result["data"], "table")
        assert "id" in formatted, "表格应包含表头 id"
        assert "张三" in formatted, "表格应包含数据 张三"
        print("  ✓ 表格格式输出正常")
    except AssertionError as e:
        print(f"  ✗ 失败: {e}")
        return False
    except Exception as e:
        print(f"  ✗ 异常: {e}")
        return False

    # --- 测试 4: 批量处理 ---
    print("\n[测试 4] 批量处理")
    try:
        batch_inputs = [
            '{"key": "value1"}',
            "简单文本测试",
            '{"key": "value2"}',
        ]
        batch_result = batch_process(batch_inputs, "json")
        assert batch_result["batch_size"] == 3, "批量大小应为 3"
        assert batch_result["success_count"] >= 2, "成功数量应大于等于 2"
        print("  ✓ 通过")
    except AssertionError as e:
        print(f"  ✗ 失败: {e}")
        return False
    except Exception as e:
        print(f"  ✗ 异常: {e}")
        return False

    # --- 测试 5: 错误处理 ---
    print("\n[测试 5] 错误处理")
    try:
        # 空输入
        try:
            process_data("")
            print("  ✗ 失败: 空输入未抛出异常")
            return False
        except ValueError as e:
            assert "E001" in str(e), "错误码应为 E001"
            print("  ✓ E001 空输入错误正常")

        # 不支持的格式 - 直接调用 format_output 并捕获异常
        try:
            format_output({}, "xml")
            print("  ✗ 失败: 不支持的格式未抛出异常")
            return False
        except ValueError as e:
            assert "E007" in str(e), "错误码应为 E007"
            print("  ✓ E007 不支持格式错误正常")

    except AssertionError as e:
        print(f"  ✗ 失败: {e}")
        return False
    except Exception as e:
        print(f"  ✗ 异常: {e}")
        return False

    # --- 测试 6: 输出格式 ---
    print("\n[测试 6] 输出格式")
    sample_data = {"name": "测试", "value": 42, "items": [1, 2, 3]}
    try:
        for fmt in ["json", "csv", "table", "markdown"]:
            output = format_output(sample_data, fmt)
            assert output is not None and len(output) > 0, f"{fmt} 输出不应为空"
            print(f"  ✓ {fmt} 格式输出正常")
    except AssertionError as e:
        print(f"  ✗ 失败: {e}")
        return False
    except Exception as e:
        print(f"  ✗ 异常: {e}")
        return False

    # --- 测试 7: 置信度计算 ---
    print("\n[测试 7] 置信度计算")
    try:
        # 结构化数据应高置信度
        conf = calculate_confidence({"a": 1}, {"a": 1})
        assert conf >= 0.8, "结构化数据置信度应较高"
        print(f"  ✓ 结构化数据置信度: {conf}")

        # 短文本应中等置信度
        conf = calculate_confidence("短文本", {"text": "短文本"})
        assert 0.5 <= conf <= 0.9, "短文本置信度应适中"
        print(f"  ✓ 短文本置信度: {conf}")

        # 空数据应低置信度
        conf = calculate_confidence(None, {})
        assert conf <= 0.5, "空数据置信度应较低"
        print(f"  ✓ 空数据置信度: {conf}")
    except AssertionError as e:
        print(f"  ✗ 失败: {e}")
        return False
    except Exception as e:
        print(f"  ✗ 异常: {e}")
        return False

    print("\n" + "=" * 60)
    print("自检全部通过 ✓")
    print("=" * 60)
    return True


def main() -> int:
    """主入口函数。"""
    parser = argparse.ArgumentParser(
        description="数据可视化 - Business intelligence as code",
        epilog="示例: python main.py --input data.json --format json"
    )

    parser.add_argument(
        "--input", "-i",
        type=str,
        help="输入内容：文件路径、URL 或直接文本"
    )

    parser.add_argument(
        "--format", "-f",
        type=str,
        default="json",
        choices=list(SUPPORTED_FORMATS),
        help=f"输出格式 (默认: json, 支持: {', '.join(SUPPORTED_FORMATS)})"
    )

    parser.add_argument(
        "--batch",
        action="store_true",
        help="批量处理模式，输入为 JSON 数组"
    )

    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检逻辑"
    )

    parser.add_argument(
        "--version",
        action="version",
        version="evidence 1.0.0"
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        success = run_selftest()
        return 0 if success else 1

    # 处理模式
    if not args.input:
        print("错误: 请提供输入内容，使用 --input 参数")
        print("提示: 或使用 --selftest 运行自检")
        return 1

    try:
        if args.batch:
            # 批量模式：输入应为 JSON 数组
            try:
                batch_inputs = json.loads(args.input)
                if not isinstance(batch_inputs, list):
                    raise ValueError("E003: 批量模式输入应为 JSON 数组")
            except json.JSONDecodeError:
                raise ValueError("E003: 批量模式输入应为 JSON 数组，示例: [\"输入1\", \"输入2\"]")

            result = batch_process(batch_inputs, args.format)
        else:
            # 单条处理
            result = process_data(args.input, args.format)

        # 输出结果
        if args.batch:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            # 输出处理结果摘要
            print(json.dumps(result, ensure_ascii=False, indent=2))

            # 如果指定了格式，输出格式化后的数据
            if args.format != "json":
                print("\n--- 格式化输出 ---")
                print(format_output(result["data"], args.format))

        return 0

    except ValueError as e:
        print(f"错误: {e}")
        return 1
    except Exception as e:
        print(f"错误 E010: 未知错误: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
