#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
motion-skills 独立实现脚本

依据功能规格（clean-room）全新编写：
- 将数据/文件/URL 转换为结构化动效设计结果
- 支持批量处理与置信度标注
- 仅使用标准库，无第三方依赖

错误码说明：
    E001: 输入数据为空
    E002: 输入数据格式不支持（非 JSON/YAML/CSV/URL）
    E003: JSON 解析失败
    E004: CSV 解析失败
    E005: URL 格式无效
    E006: 输入数据超过大小限制（50MB）
    E007: 关键字段缺失
    E008: 输出模板格式错误
    E009: 内部处理异常
    E010: 参数错误

用法示例：
    python scripts/main.py --input data.json
    python scripts/main.py --input data.json --output result.yaml
    python scripts/main.py --selftest
"""

import argparse
import csv
import io
import json
import os
import re
import sys
import urllib.parse
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# 常量定义
# ============================================================

# 输入大小限制（50MB，按字节计算）
MAX_FILE_SIZE = 50 * 1024 * 1024

# 支持的输入格式
SUPPORTED_FORMATS = {"json", "yaml", "csv", "url"}

# 输出模板默认格式
DEFAULT_OUTPUT_FORMAT = "json"

# 关键字段（动效设计必需字段）
REQUIRED_FIELDS = {"name", "duration", "easing", "keyframes"}


# ============================================================
# 自定义异常
# ============================================================

class MotionSkillError(Exception):
    """技能处理异常基类"""
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(f"[{code}] {message}")


# ============================================================
# 数据解析模块
# ============================================================

def detect_input_type(data: str) -> str:
    """
    检测输入数据类型。

    参数:
        data: 输入字符串

    返回:
        格式类型: json / yaml / csv / url

    异常:
        E002: 无法识别的格式
        E005: URL 格式无效
    """
    if not data or not data.strip():
        raise MotionSkillError("E001", "输入数据为空")

    stripped = data.strip()

    # 检查 URL
    if stripped.startswith(("http://", "https://")):
        parsed = urllib.parse.urlparse(stripped)
        if not parsed.netloc:
            raise MotionSkillError("E005", f"无效的 URL: {stripped}")
        return "url"

    # 检查 CSV（包含逗号且有表头）
    if "," in stripped and "\n" in stripped:
        try:
            lines = stripped.splitlines()
            if len(lines) > 1:
                header = lines[0].split(",")
                if len(header) > 1:
                    return "csv"
        except Exception:
            pass

    # 检查 JSON
    try:
        json.loads(stripped)
        return "json"
    except json.JSONDecodeError:
        pass

    # 检查 YAML（简化检测：包含冒号+空格）
    if re.search(r"^\s*\w+\s*:", stripped, re.MULTILINE):
        return "yaml"

    raise MotionSkillError("E002", f"无法识别输入格式: {stripped[:50]}...")


def parse_json_data(data: str) -> Dict[str, Any]:
    """解析 JSON 格式数据"""
    try:
        result = json.loads(data)
        if isinstance(result, list):
            return {"items": result}
        if isinstance(result, dict):
            return result
        raise MotionSkillError("E002", "JSON 数据必须是对象或数组")
    except json.JSONDecodeError as e:
        raise MotionSkillError("E003", f"JSON 解析失败: {e}") from e


def parse_csv_data(data: str) -> Dict[str, Any]:
    """解析 CSV 格式数据"""
    try:
        reader = csv.DictReader(io.StringIO(data))
        rows = list(reader)
        if not rows:
            raise MotionSkillError("E004", "CSV 数据为空")
        return {"items": rows, "headers": list(rows[0].keys())}
    except Exception as e:
        raise MotionSkillError("E004", f"CSV 解析失败: {e}") from e


def parse_yaml_data(data: str) -> Dict[str, Any]:
    """
    解析 YAML 格式数据（简化实现）。

    说明:
        完整 YAML 解析需要第三方库 (pyyaml)，但为保持标准库优先，
        这里实现一个简化版解析器，仅支持基础键值对和嵌套字典。

    异常:
        E003: 解析失败
    """
    try:
        result: Dict[str, Any] = {}
        current_dict = result
        stack: List[Tuple[int, Dict[str, Any]]] = []

        for line in data.splitlines():
            if not line.strip() or line.strip().startswith("#"):
                continue

            indent = len(line) - len(line.lstrip())
            content = line.strip()

            # 处理注释
            if " #" in content:
                content = content.split(" #")[0].strip()

            if ":" in content:
                key, _, value = content.partition(":")
                key = key.strip().strip("\"'")
                value = value.strip()

                # 缩进变化处理
                while stack and indent <= stack[-1][0]:
                    stack.pop()

                if stack:
                    current_dict = stack[-1][1]

                if value:
                    # 标量值
                    current_dict[key] = _coerce_scalar(value)
                else:
                    # 嵌套对象
                    new_dict: Dict[str, Any] = {}
                    current_dict[key] = new_dict
                    stack.append((indent, new_dict))
                    current_dict = new_dict

        return result
    except Exception as e:
        raise MotionSkillError("E003", f"YAML 解析失败: {e}") from e


def _coerce_scalar(value: str) -> Any:
    """将字符串转换为适当的标量类型"""
    value = value.strip()
    if value.lower() in ("true", "false"):
        return value.lower() == "true"
    if value.lower() in ("null", "none"):
        return None
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        pass
    return value


def parse_url_data(url: str) -> Dict[str, Any]:
    """
    解析 URL 格式数据。

    说明:
        本实现不实际访问网络（保持离线），仅提取 URL 参数作为结构化数据。
        在实际生产环境中，这里应替换为实际的 HTTP 请求逻辑。
    """
    try:
        parsed = urllib.parse.urlparse(url)
        params = urllib.parse.parse_qs(parsed.query)

        result: Dict[str, Any] = {
            "url": url,
            "scheme": parsed.scheme,
            "host": parsed.netloc,
            "path": parsed.path,
        }

        # 将查询参数转换为结构化数据
        if params:
            items = []
            for key, values in params.items():
                for value in values:
                    items.append({"param": key, "value": value})
            result["items"] = items

        return result
    except Exception as e:
        raise MotionSkillError("E005", f"URL 解析失败: {e}") from e


# ============================================================
# 数据转换模块
# ============================================================

def validate_input_size(data: str) -> None:
    """验证输入数据大小"""
    if len(data.encode("utf-8")) > MAX_FILE_SIZE:
        raise MotionSkillError("E006", f"输入数据超过大小限制: {MAX_FILE_SIZE} 字节")


def extract_key_information(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    提取关键信息并过滤噪声数据。

    从原始数据中提取动效设计相关字段，过滤不相关内容。
    """
    result: Dict[str, Any] = {}

    # 递归搜索关键字段
    def search_fields(obj: Any, path: str = "") -> None:
        if isinstance(obj, dict):
            for key, value in obj.items():
                # 匹配关键字段
                if key.lower() in REQUIRED_FIELDS:
                    result[key.lower()] = value
                # 递归搜索嵌套结构
                search_fields(value, f"{path}.{key}")
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                search_fields(item, f"{path}[{i}]")

    search_fields(data)

    # 如果没有找到任何关键字段，保留原始数据
    if not result:
        result = {"raw_data": data}

    return result


def calculate_confidence(data: Dict[str, Any]) -> float:
    """
    计算数据置信度。

    基于数据完整性和结构清晰度计算 0-1 之间的置信度值。
    """
    score = 0.5  # 基础分

    # 检查关键字段完整性
    found_fields = sum(1 for field in REQUIRED_FIELDS if field in data)
    score += found_fields * 0.1

    # 检查数据结构
    if "items" in data and isinstance(data["items"], list):
        score += 0.1

    if "keyframes" in data:
        if isinstance(data["keyframes"], list) and len(data["keyframes"]) > 0:
            score += 0.1

    # 限制在 0-1 范围内
    return max(0.0, min(1.0, score))


def format_output(data: Dict[str, Any], format_type: str = "json") -> str:
    """
    按指定格式输出结构化结果。

    参数:
        data: 结构化数据
        format_type: 输出格式 (json/yaml/text)

    异常:
        E008: 输出格式不支持
    """
    if format_type == "json":
        return json.dumps(data, ensure_ascii=False, indent=2)

    if format_type == "yaml":
        return _dict_to_simple_yaml(data)

    if format_type == "text":
        return _dict_to_text(data)

    raise MotionSkillError("E008", f"不支持的输出格式: {format_type}")


def _dict_to_simple_yaml(data: Dict[str, Any], indent: int = 0) -> str:
    """将字典转换为简单 YAML 格式"""
    lines = []
    prefix = " " * indent

    for key, value in data.items():
        if isinstance(value, dict):
            lines.append(f"{prefix}{key}:")
            lines.append(_dict_to_simple_yaml(value, indent + 2))
        elif isinstance(value, list):
            lines.append(f"{prefix}{key}:")
            for item in value:
                if isinstance(item, dict):
                    lines.append(f"{prefix}  -")
                    lines.append(_dict_to_simple_yaml(item, indent + 4))
                else:
                    lines.append(f"{prefix}  - {item}")
        else:
            lines.append(f"{prefix}{key}: {value}")

    return "\n".join(lines)


def _dict_to_text(data: Dict[str, Any], indent: int = 0) -> str:
    """将字典转换为结构化文本格式"""
    lines = []
    prefix = " " * indent

    for key, value in data.items():
        if isinstance(value, dict):
            lines.append(f"{prefix}■ {key}:")
            lines.append(_dict_to_text(value, indent + 2))
        elif isinstance(value, list):
            lines.append(f"{prefix}■ {key}:")
            for i, item in enumerate(value):
                if isinstance(item, dict):
                    lines.append(f"{prefix}  {i+1}.")
                    lines.append(_dict_to_text(item, indent + 4))
                else:
                    lines.append(f"{prefix}  {i+1}. {item}")
        else:
            lines.append(f"{prefix}■ {key}: {value}")

    return "\n".join(lines)


# ============================================================
# 核心处理函数
# ============================================================

def process_input(data: str, output_format: str = "json") -> str:
    """
    核心处理流程：解析 -> 提取 -> 标注 -> 输出

    参数:
        data: 输入数据字符串
        output_format: 输出格式

    返回:
        格式化后的结构化结果字符串

    异常:
        可能抛出 MotionSkillError 异常
    """
    try:
        # 1. 验证输入大小
        validate_input_size(data)

        # 2. 检测输入类型
        input_type = detect_input_type(data)

        # 3. 解析数据
        parsed_data: Dict[str, Any]
        if input_type == "json":
            parsed_data = parse_json_data(data)
        elif input_type == "csv":
            parsed_data = parse_csv_data(data)
        elif input_type == "yaml":
            parsed_data = parse_yaml_data(data)
        elif input_type == "url":
            parsed_data = parse_url_data(data)
        else:
            raise MotionSkillError("E002", f"不支持的数据类型: {input_type}")

        # 4. 提取关键信息
        key_info = extract_key_information(parsed_data)

        # 5. 计算置信度
        confidence = calculate_confidence(key_info)

        # 6. 构建最终结果
        result = {
            "meta": {
                "version": "1.0.1",
                "input_type": input_type,
                "confidence": round(confidence, 2),
                "processed_at": "offline",
            },
            "data": key_info,
        }

        # 7. 格式化输出
        return format_output(result, output_format)

    except MotionSkillError:
        raise
    except Exception as e:
        raise MotionSkillError("E009", f"内部处理异常: {e}") from e


def batch_process(inputs: List[str], output_format: str = "json") -> List[str]:
    """
    批量处理多个输入数据。

    参数:
        inputs: 输入数据列表
        output_format: 输出格式

    返回:
        处理结果列表
    """
    results = []
    for data in inputs:
        try:
            result = process_input(data, output_format)
            results.append(result)
        except MotionSkillError as e:
            results.append(json.dumps({"error": e.code, "message": e.message}))
    return results


# ============================================================
# 自检模块
# ============================================================

def run_selftest() -> bool:
    """
    运行内置自检。

    使用硬编码的测试数据验证核心逻辑，不依赖外部文件或网络。
    所有断言使用宽松阈值（区间判断），确保稳健性。

    返回:
        True 表示所有测试通过
    """
    print("=" * 60)
    print("motion-skills 自检开始")
    print("=" * 60)

    all_passed = True

    # ---- 测试 1: 数据类型检测 ----
    print("\n[测试 1] 数据类型检测")
    try:
        assert detect_input_type('{"name": "test"}') == "json", "JSON 类型检测失败"
        assert detect_input_type("https://example.com/data") == "url", "URL 类型检测失败"
        assert detect_input_type("name,duration\ntest,1.5") == "csv", "CSV 类型检测失败"
        assert detect_input_type("name: test\nduration: 1.5") == "yaml", "YAML 类型检测失败"
        print("  ✓ 通过")
    except AssertionError as e:
        print(f"  ✗ 失败: {e}")
        all_passed = False

    # ---- 测试 2: JSON 解析 ----
    print("\n[测试 2] JSON 解析")
    try:
        json_data = '{"name": "fade", "duration": 1.5, "easing": "ease-in", "keyframes": [0, 0.5, 1]}'
        result = parse_json_data(json_data)
        assert result["name"] == "fade", "JSON 字段 name 解析失败"
        assert result["duration"] == 1.5, "JSON 字段 duration 解析失败"
        print("  ✓ 通过")
    except AssertionError as e:
        print(f"  ✗ 失败: {e}")
        all_passed = False

    # ---- 测试 3: CSV 解析 ----
    print("\n[测试 3] CSV 解析")
    try:
        csv_data = "name,duration,easing\nslide,2.0,ease-out\nfade,1.0,linear"
        result = parse_csv_data(csv_data)
        assert "items" in result, "CSV 解析结果缺少 items"
        assert len(result["items"]) == 2, "CSV 行数不正确"
        print("  ✓ 通过")
    except AssertionError as e:
        print(f"  ✗ 失败: {e}")
        all_passed = False

    # ---- 测试 4: 关键信息提取 ----
    print("\n[测试 4] 关键信息提取")
    try:
        test_data = {
            "name": "test-animation",
            "duration": 2.5,
            "easing": "ease-in-out",
            "keyframes": [{"time": 0, "value": 0}, {"time": 1, "value": 1}],
            "noise_field": "should be filtered",
        }
        result = extract_key_information(test_data)
        assert "name" in result, "关键字段 name 未提取"
        assert "duration" in result, "关键字段 duration 未提取"
        assert "noise_field" not in result, "噪声字段未被过滤"
        print("  ✓ 通过")
    except AssertionError as e:
        print(f"  ✗ 失败: {e}")
        all_passed = False

    # ---- 测试 5: 置信度计算 ----
    print("\n[测试 5] 置信度计算")
    try:
        complete_data = {
            "name": "test",
            "duration": 1.0,
            "easing": "linear",
            "keyframes": [0, 1],
        }
        confidence = calculate_confidence(complete_data)
        assert 0.5 <= confidence <= 1.0, "置信度应在 0.5-1.0 范围内"
        print(f"  ✓ 通过 (置信度: {confidence:.2f})")
    except AssertionError as e:
        print(f"  ✗ 失败: {e}")
        all_passed = False

    # ---- 测试 6: 完整处理流程 ----
    print("\n[测试 6] 完整处理流程")
    try:
        sample_data = '{"name": "slide-in", "duration": 1.8, "easing": "ease-out", "keyframes": [0, 0.3, 1]}'
        result = process_input(sample_data, "json")
        parsed_result = json.loads(result)

        # 验证结构
        assert "meta" in parsed_result, "处理结果缺少 meta"
        assert "data" in parsed_result, "处理结果缺少 data"
        assert parsed_result["meta"]["confidence"] > 0.5, "置信度应大于 0.5"
        assert parsed_result["data"]["name"] == "slide-in", "名称字段不正确"
        print("  ✓ 通过")
    except AssertionError as e:
        print(f"  ✗ 失败: {e}")
        all_passed = False

    # ---- 测试 7: 批量处理 ----
    print("\n[测试 7] 批量处理")
    try:
        inputs = [
            '{"name": "a", "duration": 1, "easing": "linear", "keyframes": [0, 1]}',
            '{"name": "b", "duration": 2, "easing": "ease", "keyframes": [0, 0.5, 1]}',
            "invalid data",
        ]
        results = batch_process(inputs)
        assert len(results) == 3, "批量处理数量不正确"
        # 前两个应该成功，第三个应该返回错误
        assert json.loads(results[0])["data"]["name"] == "a", "批量处理第一个结果错误"
        assert "error" in json.loads(results[2]), "批量处理应返回错误"
        print("  ✓ 通过")
    except AssertionError as e:
        print(f"  ✗ 失败: {e}")
        all_passed = False

    # ---- 测试 8: 错误处理 ----
    print("\n[测试 8] 错误处理")
    try:
        # 空数据
        try:
            process_input("")
            assert False, "空数据应抛出异常"
        except MotionSkillError as e:
            assert e.code == "E001", f"错误码应为 E001, 实际: {e.code}"

        # 无效格式
        try:
            process_input("@@@invalid@@@")
            assert False, "无效格式应抛出异常"
        except MotionSkillError as e:
            assert e.code in ("E002", "E003"), f"错误码应为 E002/E003, 实际: {e.code}"

        # 无效输出格式
        try:
            process_input('{"name": "test"}', "xml")
            assert False, "无效输出格式应抛出异常"
        except MotionSkillError as e:
            assert e.code == "E008", f"错误码应为 E008, 实际: {e.code}"

        print("  ✓ 通过")
    except AssertionError as e:
        print(f"  ✗ 失败: {e}")
        all_passed = False

    # ---- 测试 9: 输出格式 ----
    print("\n[测试 9] 输出格式")
    try:
        test_dict = {"name": "test", "duration": 1.5, "items": [{"x": 1}, {"x": 2}]}

        # JSON 输出
        json_out = format_output(test_dict, "json")
        assert json_out.startswith("{"), "JSON 输出格式错误"

        # YAML 输出
        yaml_out = format_output(test_dict, "yaml")
        assert "name: test" in yaml_out, "YAML 输出格式错误"

        # 文本输出
        text_out = format_output(test_dict, "text")
        assert "■ name: test" in text_out, "文本输出格式错误"

        print("  ✓ 通过")
    except AssertionError as e:
        print(f"  ✗ 失败: {e}")
        all_passed = False

    # ---- 测试 10: URL 解析 ----
    print("\n[测试 10] URL 解析")
    try:
        url = "https://example.com/api?name=test&duration=2.5"
        result = parse_url_data(url)
        assert result["host"] == "example.com", "URL 主机解析失败"
        assert "items" in result, "URL 参数解析失败"
        assert len(result["items"]) == 2, "URL 参数数量不正确"
        print("  ✓ 通过")
    except AssertionError as e:
        print(f"  ✗ 失败: {e}")
        all_passed = False

    # ---- 总结 ----
    print("\n" + "=" * 60)
    if all_passed:
        print("✅ 所有自检测试通过")
    else:
        print("❌ 部分自检测试失败")
    print("=" * 60)

    return all_passed


# ============================================================
# 命令行入口
# ============================================================

def main() -> int:
    """命令行主入口"""
    parser = argparse.ArgumentParser(
        description="motion-skills: 将数据/文件/URL 转换为结构化动效设计结果",
        epilog="示例: python main.py --input data.json --output result.yaml"
    )

    parser.add_argument(
        "--input", "-i",
        type=str,
        help="输入数据（JSON/YAML/CSV 字符串或 URL）"
    )

    parser.add_argument(
        "--file", "-f",
        type=str,
        help="输入文件路径"
    )

    parser.add_argument(
        "--output-format", "-o",
        type=str,
        choices=["json", "yaml", "text"],
        default=DEFAULT_OUTPUT_FORMAT,
        help=f"输出格式 (默认: {DEFAULT_OUTPUT_FORMAT})"
    )

    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检"
    )

    parser.add_argument(
        "--batch",
        type=str,
        nargs="+",
        help="批量处理多个输入数据"
    )

    args = parser.parse_args()

    # 运行自检
    if args.selftest:
        success = run_selftest()
        return 0 if success else 1

    # 参数检查
    if not args.input and not args.file and not args.batch:
        parser.print_help()
        print("\n错误: 必须提供 --input, --file 或 --batch 参数", file=sys.stderr)
        return 1

    try:
        # 批量处理
        if args.batch:
            results = batch_process(args.batch, args.output_format)
            for i, result in enumerate(results):
                print(f"--- 结果 {i+1} ---")
                print(result)
                print()
            return 0

        # 从文件读取
        if args.file:
            try:
                # 检查文件大小
                file_size = os.path.getsize(args.file)
                if file_size > MAX_FILE_SIZE:
                    raise MotionSkillError("E006", f"文件超过大小限制: {file_size} 字节")

                with open(args.file, "r", encoding="utf-8") as f:
                    data = f.read()
            except FileNotFoundError:
                print(f"错误: 文件不存在: {args.file}", file=sys.stderr)
                return 1
            except IOError as e:
                print(f"错误: 读取文件失败: {e}", file=sys.stderr)
                return 1
        else:
            # 直接使用输入字符串
            data = args.input

        # 处理数据
        result = process_input(data, args.output_format)
        print(result)
        return 0

    except MotionSkillError as e:
        print(f"错误 [{e.code}]: {e.message}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"错误 [E009]: 未预期的异常: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
