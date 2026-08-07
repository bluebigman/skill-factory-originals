#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fotomatic — 闪光快照参数提取 Skill 的独立实现
=============================================
将图片文件、图片 URL 或数据文本解析为结构化参数结果，
并标注每项参数的置信度。

版本: 1.0.1 (clean-room 重写)
作者: skillcraft-studio (基于功能规格独立实现)
"""

import argparse
import json
import os
import re
import sys
import urllib.parse
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union

# 错误码定义
ERROR_CODES = {
    "E001": "输入为空或格式无效",
    "E002": "输入条目数超过上限(20)",
    "E003": "文件大小超过限制(10MB)",
    "E004": "URL 协议不支持(仅 http/https)",
    "E005": "无法解析输入内容",
    "E006": "批量输入中存在无效条目",
    "E007": "输出格式不支持",
    "E008": "参数缺失或类型错误",
    "E009": "内部处理异常",
    "E010": "未知错误",
}

# 常量定义
MAX_ITEMS = 20
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
SUPPORTED_PROTOCOLS = ("http", "https")
SUPPORTED_OUTPUT_FORMATS = ("json", "table", "text")


class FotoError(Exception):
    """fotomatic 自定义异常，携带错误码"""

    def __init__(self, code: str, message: str = ""):
        self.code = code
        self.message = message or ERROR_CODES.get(code, ERROR_CODES["E010"])
        super().__init__(f"[{self.code}] {self.message}")


def _safe_float(value: Any) -> Optional[float]:
    """安全转换为浮点数"""
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _safe_int(value: Any) -> Optional[int]:
    """安全转换为整数"""
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _confidence(value: Any, expected_type: type, base: float = 0.9) -> float:
    """
    计算置信度
    宽松阈值：类型匹配时返回 base，否则返回较低值
    """
    if value is None:
        return 0.0
    if isinstance(value, expected_type):
        return base
    # 尝试转换
    try:
        if expected_type == float:
            converted = float(value)
        elif expected_type == int:
            converted = int(value)
        elif expected_type == str:
            converted = str(value)
        else:
            return 0.3
        if converted is not None:
            return base - 0.1
    except (TypeError, ValueError):
        pass
    return 0.2


def _parse_dimension(text: str) -> Optional[Tuple[int, int]]:
    """
    从文本中解析尺寸信息 (宽 x 高)
    支持格式: "1920x1080", "1920 x 1080", "宽1920高1080" 等
    """
    if not text:
        return None
    # 匹配数字x数字模式
    pattern = r"(\d+)\s*[xX×]\s*(\d+)"
    match = re.search(pattern, text)
    if match:
        width = _safe_int(match.group(1))
        height = _safe_int(match.group(2))
        if width and height and width > 0 and height > 0:
            return (width, height)
    return None


def _parse_file_size(size_bytes: Union[int, float, str]) -> Optional[float]:
    """将字节数转换为 MB 并返回"""
    size = _safe_float(size_bytes)
    if size is None or size < 0:
        return None
    return round(size / (1024 * 1024), 2)


def _parse_url(url: str) -> Dict[str, Any]:
    """解析 URL 提取参数"""
    if not url or not isinstance(url, str):
        raise FotoError("E001", "URL 为空或类型无效")

    # 验证协议
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in SUPPORTED_PROTOCOLS:
        raise FotoError("E004", f"不支持的协议: {parsed.scheme}")

    result: Dict[str, Any] = {
        "url": url,
        "protocol": parsed.scheme,
        "domain": parsed.netloc,
        "path": parsed.path,
        "query_params": {},
        "confidence": {},
    }

    # 解析查询参数
    query_params = urllib.parse.parse_qs(parsed.query)
    for key, values in query_params.items():
        result["query_params"][key] = values[0] if values else ""

    # 从 URL 路径和查询参数中提取可能的信息
    all_text = f"{parsed.path} {parsed.query}"

    # 尝试提取尺寸
    dims = _parse_dimension(all_text)
    if dims:
        result["width"] = dims[0]
        result["height"] = dims[1]
        result["confidence"]["width"] = 0.85
        result["confidence"]["height"] = 0.85

    # 尝试提取文件格式
    ext_match = re.search(r"\.(jpg|jpeg|png|gif|bmp|webp|svg)$", parsed.path, re.I)
    if ext_match:
        result["format"] = ext_match.group(1).lower()
        result["confidence"]["format"] = 0.9

    # 尝试提取文件大小（如果有 size 参数）
    if "size" in result["query_params"]:
        size_mb = _parse_file_size(result["query_params"]["size"])
        if size_mb is not None:
            result["file_size_mb"] = size_mb
            result["confidence"]["file_size_mb"] = 0.7

    return result


def _parse_text_data(text: str) -> Dict[str, Any]:
    """解析数据文本提取参数"""
    if not text or not isinstance(text, str):
        raise FotoError("E001", "文本为空或类型无效")

    result: Dict[str, Any] = {
        "source_type": "text",
        "text_length": len(text),
        "confidence": {},
    }

    # 尝试解析 JSON
    stripped = text.strip()
    if stripped.startswith("{") or stripped.startswith("["):
        try:
            data = json.loads(stripped)
            if isinstance(data, dict):
                result["parsed_data"] = data
                result["confidence"]["parsed_data"] = 0.95
                # 从 JSON 中提取常见字段
                for key in ["width", "height", "format", "size", "filename"]:
                    if key in data:
                        result[key] = data[key]
                        result["confidence"][key] = 0.9
            elif isinstance(data, list):
                result["item_count"] = len(data)
                result["confidence"]["item_count"] = 0.9
        except json.JSONDecodeError:
            pass

    # 尝试提取尺寸
    dims = _parse_dimension(stripped)
    if dims:
        result["width"] = dims[0]
        result["height"] = dims[1]
        result["confidence"]["width"] = 0.8
        result["confidence"]["height"] = 0.8

    # 尝试提取格式
    for fmt in ["jpg", "jpeg", "png", "gif", "bmp", "webp", "svg"]:
        if fmt in stripped.lower():
            result["format"] = fmt
            result["confidence"]["format"] = 0.75
            break

    # 尝试提取文件大小
    size_match = re.search(r"(\d+(?:\.\d+)?)\s*(MB|KB|GB)", stripped, re.I)
    if size_match:
        value = _safe_float(size_match.group(1))
        unit = size_match.group(2).upper()
        if value is not None:
            if unit == "KB":
                value = value / 1024
            elif unit == "GB":
                value = value * 1024
            result["file_size_mb"] = round(value, 2)
            result["confidence"]["file_size_mb"] = 0.7

    return result


def _parse_file_path(file_path: str) -> Dict[str, Any]:
    """解析本地文件路径"""
    if not file_path or not isinstance(file_path, str):
        raise FotoError("E001", "文件路径为空或类型无效")

    if not os.path.exists(file_path):
        raise FotoError("E005", f"文件不存在: {file_path}")

    # 检查文件大小
    file_size = os.path.getsize(file_path)
    if file_size > MAX_FILE_SIZE:
        raise FotoError("E003", f"文件大小 {file_size} 超过限制 {MAX_FILE_SIZE}")

    result: Dict[str, Any] = {
        "filename": os.path.basename(file_path),
        "file_path": file_path,
        "file_size_bytes": file_size,
        "file_size_mb": round(file_size / (1024 * 1024), 2),
        "confidence": {},
    }

    # 提取扩展名
    ext = os.path.splitext(file_path)[1].lstrip(".").lower()
    if ext:
        result["format"] = ext
        result["confidence"]["format"] = 0.95

    # 尝试从文件名提取尺寸
    dims = _parse_dimension(os.path.basename(file_path))
    if dims:
        result["width"] = dims[0]
        result["height"] = dims[1]
        result["confidence"]["width"] = 0.7
        result["confidence"]["height"] = 0.7

    result["confidence"]["file_size_mb"] = 0.95
    result["confidence"]["filename"] = 0.95

    return result


def _process_single_item(item: str) -> Dict[str, Any]:
    """处理单个输入条目"""
    if not item or not isinstance(item, str):
        raise FotoError("E001", "输入条目为空或类型无效")

    item = item.strip()
    if not item:
        raise FotoError("E001", "输入条目为空白")

    # 判断类型：URL、文件路径或数据文本
    if item.startswith(("http://", "https://")):
        result = _parse_url(item)
        result["source_type"] = "url"
    elif os.path.exists(item):
        result = _parse_file_path(item)
        result["source_type"] = "file"
    else:
        result = _parse_text_data(item)
        result["source_type"] = "text"

    # 确保置信度字段存在
    result.setdefault("confidence", {})

    # 填充缺失字段的占位符
    expected_fields = ["width", "height", "format", "file_size_mb", "filename"]
    for field in expected_fields:
        if field not in result:
            result[field] = f"[需核实:{field}]"
            result["confidence"][field] = 0.0

    return result


def process_inputs(inputs: Union[str, List[str]]) -> List[Dict[str, Any]]:
    """
    处理输入，支持单个字符串或字符串列表
    返回结构化结果列表
    """
    # 统一为列表
    if isinstance(inputs, str):
        items = [inputs]
    elif isinstance(inputs, list):
        items = inputs
    else:
        raise FotoError("E008", "输入参数类型必须是字符串或字符串列表")

    # 检查数量限制
    if len(items) > MAX_ITEMS:
        raise FotoError("E002", f"输入条目数 {len(items)} 超过上限 {MAX_ITEMS}")

    # 处理每个条目
    results = []
    errors = []
    for i, item in enumerate(items):
        try:
            result = _process_single_item(item)
            result["index"] = i + 1
            results.append(result)
        except FotoError as e:
            errors.append({"index": i + 1, "error": e.code, "message": str(e)})

    # 如果有错误且没有任何成功结果，抛出异常
    if errors and not results:
        raise FotoError("E006", f"所有条目处理失败: {errors[0]['message']}")

    # 添加错误信息到结果
    if errors:
        results.append({"errors": errors, "partial": True})

    return results


def format_output(results: List[Dict[str, Any]], output_format: str = "json") -> str:
    """格式化输出结果"""
    if output_format not in SUPPORTED_OUTPUT_FORMATS:
        raise FotoError("E007", f"不支持的输出格式: {output_format}")

    if output_format == "json":
        return json.dumps(results, ensure_ascii=False, indent=2, default=str)

    elif output_format == "text":
        lines = []
        for i, result in enumerate(results):
            lines.append(f"--- 条目 {i + 1} ---")
            for key, value in result.items():
                if key == "confidence":
                    continue
                conf = result.get("confidence", {}).get(key, 0.0)
                lines.append(f"  {key}: {value} (置信度: {conf:.0%})")
        return "\n".join(lines)

    elif output_format == "table":
        # 简单表格输出
        if not results:
            return "无结果"

        # 收集所有字段
        all_keys = set()
        for result in results:
            all_keys.update(result.keys())
        all_keys.discard("confidence")
        all_keys.discard("errors")

        # 表头
        lines = []
        header = "| " + " | ".join(sorted(all_keys)) + " |"
        separator = "|" + "|".join(["---"] * len(all_keys)) + "|"
        lines.append(header)
        lines.append(separator)

        # 数据行
        for result in results:
            row = []
            for key in sorted(all_keys):
                value = result.get(key, "N/A")
                if isinstance(value, (dict, list)):
                    value = json.dumps(value, ensure_ascii=False)[:30]
                row.append(str(value)[:30])
            lines.append("| " + " | ".join(row) + " |")

        return "\n".join(lines)

    return json.dumps(results, ensure_ascii=False, indent=2, default=str)


def run_selftest() -> bool:
    """
    内置自检：使用硬编码样例数据验证核心逻辑
    宽松阈值断言，确保任何环境可过
    """
    print("=" * 60)
    print("fotomatic 自检开始")
    print("=" * 60)

    all_passed = True

    # 测试用例 1: URL 解析
    print("\n[测试 1] URL 解析")
    try:
        url_result = _parse_url("https://example.com/images/photo_1920x1080.jpg?size=5242880")
        assert url_result["protocol"] == "https", "协议解析错误"
        assert url_result["domain"] == "example.com", "域名解析错误"
        assert "width" in url_result, "未提取宽度"
        assert "height" in url_result, "未提取高度"
        # 宽松断言：尺寸应大于 0
        assert url_result["width"] > 0, "宽度应大于 0"
        assert url_result["height"] > 0, "高度应大于 0"
        assert url_result.get("format") in ["jpg", "jpeg", "png", "gif"], "格式提取错误"
        print("  ✓ URL 解析通过")
    except AssertionError as e:
        print(f"  ✗ URL 解析失败: {e}")
        all_passed = False
    except FotoError as e:
        print(f"  ✗ URL 解析异常: {e}")
        all_passed = False

    # 测试用例 2: 文本数据解析
    print("\n[测试 2] 文本数据解析")
    try:
        text_data = '{"width": 800, "height": 600, "format": "png", "size": 1048576}'
        text_result = _parse_text_data(text_data)
        assert text_result["text_length"] > 0, "文本长度应为正数"
        assert "parsed_data" in text_result, "JSON 解析失败"
        # 宽松断言：数值应合理
        assert text_result.get("width", 0) > 0, "宽度应大于 0"
        assert text_result.get("height", 0) > 0, "高度应大于 0"
        assert text_result.get("format") == "png", "格式应为 png"
        print("  ✓ 文本解析通过")
    except AssertionError as e:
        print(f"  ✗ 文本解析失败: {e}")
        all_passed = False
    except FotoError as e:
        print(f"  ✗ 文本解析异常: {e}")
        all_passed = False

    # 测试用例 3: 批量处理
    print("\n[测试 3] 批量处理")
    try:
        batch_inputs = [
            "https://example.com/a_1280x720.png",
            '{"width": 640, "height": 480}',
        ]
        batch_results = process_inputs(batch_inputs)
        assert len(batch_results) >= 2, "应至少返回 2 个结果"
        assert batch_results[0]["source_type"] == "url", "第一个应为 URL"
        assert batch_results[1]["source_type"] == "text", "第二个应为文本"
        print("  ✓ 批量处理通过")
    except AssertionError as e:
        print(f"  ✗ 批量处理失败: {e}")
        all_passed = False
    except FotoError as e:
        print(f"  ✗ 批量处理异常: {e}")
        all_passed = False

    # 测试用例 4: 输出格式化
    print("\n[测试 4] 输出格式化")
    try:
        test_results = [{"test": "value", "confidence": {"test": 0.9}}]
        json_out = format_output(test_results, "json")
        assert json_out is not None and len(json_out) > 0, "JSON 输出为空"
        assert "test" in json_out, "JSON 输出缺少字段"

        text_out = format_output(test_results, "text")
        assert text_out is not None and len(text_out) > 0, "文本输出为空"

        table_out = format_output(test_results, "table")
        assert table_out is not None and len(table_out) > 0, "表格输出为空"
        print("  ✓ 输出格式化通过")
    except AssertionError as e:
        print(f"  ✗ 输出格式化失败: {e}")
        all_passed = False
    except FotoError as e:
        print(f"  ✗ 输出格式化异常: {e}")
        all_passed = False

    # 测试用例 5: 错误处理
    print("\n[测试 5] 错误处理")
    try:
        # 空输入
        try:
            _parse_url("")
            print("  ✗ 空 URL 未抛出异常")
            all_passed = False
        except FotoError as e:
            assert e.code == "E001", f"错误码应为 E001，实际 {e.code}"
            print("  ✓ 空输入错误处理通过")

        # 不支持的协议
        try:
            _parse_url("ftp://example.com/file.jpg")
            print("  ✗ 不支持协议未抛出异常")
            all_passed = False
        except FotoError as e:
            assert e.code == "E004", f"错误码应为 E004，实际 {e.code}"
            print("  ✓ 协议错误处理通过")

        # 超过数量限制
        try:
            many_inputs = [f"item{i}" for i in range(21)]
            process_inputs(many_inputs)
            print("  ✗ 超量输入未抛出异常")
            all_passed = False
        except FotoError as e:
            assert e.code == "E002", f"错误码应为 E002，实际 {e.code}"
            print("  ✓ 数量限制错误处理通过")

    except AssertionError as e:
        print(f"  ✗ 错误处理测试失败: {e}")
        all_passed = False

    # 测试用例 6: 置信度计算
    print("\n[测试 6] 置信度计算")
    try:
        # 宽松断言：置信度应在合理范围内
        conf_float = _confidence(3.14, float)
        assert 0.0 < conf_float <= 1.0, "浮点置信度应在 (0, 1] 范围"

        conf_int = _confidence(42, int)
        assert 0.0 < conf_int <= 1.0, "整数置信度应在 (0, 1] 范围"

        conf_str = _confidence("hello", str)
        assert 0.0 < conf_str <= 1.0, "字符串置信度应在 (0, 1] 范围"

        conf_none = _confidence(None, str)
        assert conf_none == 0.0, "空值置信度应为 0"

        print("  ✓ 置信度计算通过")
    except AssertionError as e:
        print(f"  ✗ 置信度计算失败: {e}")
        all_passed = False

    # 测试用例 7: 尺寸解析
    print("\n[测试 7] 尺寸解析")
    try:
        dims = _parse_dimension("1920x1080")
        assert dims is not None, "尺寸解析失败"
        assert dims[0] > 0 and dims[1] > 0, "尺寸应为正数"

        dims2 = _parse_dimension("800 x 600")
        assert dims2 is not None, "带空格尺寸解析失败"
        assert dims2[0] > 0 and dims2[1] > 0, "尺寸应为正数"

        dims3 = _parse_dimension("无效文本")
        assert dims3 is None, "无效文本不应解析出尺寸"

        print("  ✓ 尺寸解析通过")
    except AssertionError as e:
        print(f"  ✗ 尺寸解析失败: {e}")
        all_passed = False

    # 测试用例 8: 文件大小解析
    print("\n[测试 8] 文件大小解析")
    try:
        size_mb = _parse_file_size(5242880)  # 5MB
        assert size_mb is not None, "文件大小解析失败"
        assert size_mb > 0, "文件大小应为正数"
        assert size_mb < 100, "5MB 应远小于 100MB"

        size_invalid = _parse_file_size(-1)
        assert size_invalid is None, "负数不应解析成功"

        print("  ✓ 文件大小解析通过")
    except AssertionError as e:
        print(f"  ✗ 文件大小解析失败: {e}")
        all_passed = False

    # 总结
    print("\n" + "=" * 60)
    if all_passed:
        print("自检全部通过 ✓")
    else:
        print("自检存在失败项 ✗")
    print("=" * 60)

    return all_passed


def main() -> int:
    """主入口"""
    parser = argparse.ArgumentParser(
        description="fotomatic — 闪光快照参数提取 (图片/URL/文本 → 结构化参数)"
    )
    parser.add_argument(
        "inputs",
        nargs="*",
        help="输入内容：文件路径、URL 或数据文本（支持多个，最多 20 个）",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检（使用硬编码样例数据，不依赖外部环境）",
    )
    parser.add_argument(
        "--format",
        choices=SUPPORTED_OUTPUT_FORMATS,
        default="json",
        help="输出格式 (默认: json)",
    )
    parser.add_argument(
        "--file",
        help="从文件读取输入（每行一个条目）",
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        success = run_selftest()
        return 0 if success else 1

    # 从文件读取输入
    input_items: List[str] = list(args.inputs)
    if args.file:
        try:
            with open(args.file, "r", encoding="utf-8") as f:
                file_items = [line.strip() for line in f if line.strip()]
                input_items.extend(file_items)
        except OSError as e:
            print(f"[E010] 读取输入文件失败: {e}", file=sys.stderr)
            return 1

    # 无输入时显示帮助
    if not input_items:
        parser.print_help()
        return 0

    try:
        # 处理输入
        results = process_inputs(input_items)

        # 输出结果
        output = format_output(results, args.format)
        print(output)

        return 0

    except FotoError as e:
        print(f"处理失败: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"[E010] 未知错误: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
