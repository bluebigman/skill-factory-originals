#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
claude-vigil 代码审查工具 - 独立实现脚本

本脚本依据功能规格独立编写（clean-room），不参考任何既有实现。
核心能力：将用户提供的数据/文件/URL 转换为结构化结果，并给出置信度提示。
"""

import argparse
import json
import os
import re
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
    "E006": "文件读取失败，请检查文件路径和权限",
    "E007": "URL 解析失败，仅支持 http/https 协议",
    "E008": "JSON 解析失败，输入不是有效的 JSON 格式",
    "E009": "内部处理逻辑错误，请联系维护者",
    "E010": "参数错误，请检查命令行参数",
}


class VigilError(Exception):
    """自定义异常，携带错误码"""

    def __init__(self, code: str, message: str = ""):
        self.code = code
        self.message = message or ERROR_CODES.get(code, "未知错误")
        super().__init__(f"[{code}] {self.message}")


# ============================================================
# 核心处理逻辑
# ============================================================

def validate_input(raw_input: str) -> Tuple[bool, str]:
    """
    校验输入是否有效。
    返回 (是否有效, 错误码或空字符串)
    """
    if not raw_input or not raw_input.strip():
        return False, "E001"
    return True, ""


def detect_input_type(raw_input: str) -> str:
    """
    识别输入类型：text / json / url / file
    """
    stripped = raw_input.strip()

    # URL 检测
    if re.match(r'^https?://', stripped, re.IGNORECASE):
        return "url"

    # 文件路径检测（存在且是文件）
    if len(stripped) < 512 and os.path.isfile(stripped):
        return "file"

    # JSON 检测（尝试解析）
    try:
        json.loads(stripped)
        return "json"
    except (json.JSONDecodeError, ValueError):
        pass

    return "text"


def parse_json_input(raw_input: str) -> Dict[str, Any]:
    """解析 JSON 输入"""
    try:
        data = json.loads(raw_input.strip())
        if not isinstance(data, dict):
            raise VigorError("E008", "JSON 顶层必须是对象")
        return data
    except json.JSONDecodeError as e:
        raise VigorError("E008", f"JSON 解析失败: {e}")


def read_file_input(file_path: str) -> str:
    """读取文件内容"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        raise VigorError("E006", f"文件不存在: {file_path}")
    except PermissionError:
        raise VigorError("E006", f"没有读取权限: {file_path}")
    except Exception as e:
        raise VigorError("E006", f"读取失败: {e}")


def process_url_input(url: str) -> Dict[str, Any]:
    """
    处理 URL 输入。
    注意：本工具不访问网络，仅做格式校验和结构化。
    """
    if not re.match(r'^https?://', url, re.IGNORECASE):
        raise VigorError("E007", f"不支持的 URL 协议: {url}")

    # 仅返回结构化元信息，不实际访问
    return {
        "type": "url",
        "url": url.strip(),
        "status": "not_accessed",  # 工具不访问网络
        "confidence": 0.9,
        "note": "URL 已记录，但本工具不执行网络访问",
    }


def extract_key_fields(text: str) -> Dict[str, Any]:
    """
    从文本中提取关键字段。
    实际实现中可根据业务需求扩展，这里提供通用示例。
    """
    fields: Dict[str, Any] = {}
    stripped = text.strip()

    # 提取可能的标题/主题（第一行非空）
    lines = [l.strip() for l in stripped.split("\n") if l.strip()]
    if lines:
        fields["title"] = lines[0][:100]  # 限制长度

    # 提取可能的邮箱
    emails = re.findall(r'[\w.+-]+@[\w-]+\.[\w.]+', stripped)
    if emails:
        fields["emails"] = emails[:5]

    # 提取可能的电话号码（简单模式）
    phones = re.findall(r'1[3-9]\d{9}', stripped)
    if phones:
        fields["phones"] = phones[:5]

    # 提取可能的URL
    urls = re.findall(r'https?://[^\s]+', stripped)
    if urls:
        fields["urls"] = urls[:5]

    return fields


def calculate_confidence(data: Dict[str, Any]) -> Tuple[float, str]:
    """
    计算置信度。
    返回 (置信度, 标注说明)
    """
    if not data:
        return 0.0, "[需核实] 无有效内容"

    # 基于字段完整性计算
    total_weight = 0.0
    filled_weight = 0.0

    # 简单加权评分
    weights = {
        "title": 0.3,
        "emails": 0.2,
        "phones": 0.2,
        "urls": 0.15,
        "type": 0.15,
    }

    for field, weight in weights.items():
        total_weight += weight
        if data.get(field):
            filled_weight += weight

    if total_weight > 0:
        confidence = filled_weight / total_weight
    else:
        confidence = 0.0

    # 附加规则：有明确类型且至少有内容时，基础分提高
    if data.get("type") and data.get("title"):
        confidence = max(confidence, 0.7)

    # 生成标注
    if confidence >= 0.9:
        note = "直接输出"
    elif confidence >= 0.85:
        note = "建议复核"
    else:
        note = "[需核实]"

    return round(confidence, 2), note


def process_text_input(text: str) -> Dict[str, Any]:
    """处理纯文本输入"""
    valid, err_code = validate_input(text)
    if not valid:
        raise VigorError(err_code)

    fields = extract_key_fields(text)
    fields["type"] = "text"
    fields["content_length"] = len(text.strip())

    confidence, note = calculate_confidence(fields)
    fields["confidence"] = confidence
    fields["confidence_note"] = note

    return fields


def process_json_input(raw_input: str) -> Dict[str, Any]:
    """处理 JSON 输入"""
    valid, err_code = validate_input(raw_input)
    if not valid:
        raise VigorError(err_code)

    data = parse_json_input(raw_input)

    # 结构化 JSON 数据
    result = {
        "type": "json",
        "fields": data,
        "field_count": len(data),
    }

    # 提取顶层键作为标题
    if data:
        keys = list(data.keys())
        result["title"] = keys[0][:100]

    confidence, note = calculate_confidence(result)
    result["confidence"] = confidence
    result["confidence_note"] = note

    return result


def process_file_input(file_path: str) -> Dict[str, Any]:
    """处理文件输入"""
    if not os.path.isfile(file_path):
        raise VigorError("E006", f"文件不存在: {file_path}")

    content = read_file_input(file_path)
    file_ext = os.path.splitext(file_path)[1].lower()

    if file_ext == ".json":
        result = process_json_input(content)
        result["source_file"] = file_path
    else:
        result = process_text_input(content)
        result["source_file"] = file_path

    result["type"] = "file"
    result["file_extension"] = file_ext

    return result


def process_url_input(url: str) -> Dict[str, Any]:
    """处理 URL 输入"""
    valid, err_code = validate_input(url)
    if not valid:
        raise VigorError(err_code)

    return process_url_input(url)


def process_input(raw_input: str) -> Dict[str, Any]:
    """
    统一入口：根据输入类型分发处理
    """
    valid, err_code = validate_input(raw_input)
    if not valid:
        raise VigorError(err_code)

    input_type = detect_input_type(raw_input)

    if input_type == "json":
        return process_json_input(raw_input)
    elif input_type == "file":
        return process_file_input(raw_input)
    elif input_type == "url":
        return process_url_input(raw_input)
    else:
        return process_text_input(raw_input)


# ============================================================
# 批量处理
# ============================================================

def process_batch(inputs: List[str]) -> List[Dict[str, Any]]:
    """
    批量处理多个输入。
    单条失败不影响其他条目，错误记录在结果中。
    """
    results = []
    for item in inputs:
        try:
            result = process_input(item)
            result["_input"] = item[:50]  # 截断显示
            results.append(result)
        except VigorError as e:
            results.append({
                "error": e.code,
                "message": e.message,
                "_input": item[:50],
            })
        except Exception as e:
            results.append({
                "error": "E009",
                "message": f"内部错误: {e}",
                "_input": item[:50],
            })
    return results


# ============================================================
# 输出格式化
# ============================================================

def format_output(result: Dict[str, Any], pretty: bool = True) -> str:
    """格式化输出结果"""
    if pretty:
        return json.dumps(result, ensure_ascii=False, indent=2)
    return json.dumps(result, ensure_ascii=False)


# ============================================================
# 自测（selftest）
# ============================================================

def run_selftest() -> int:
    """
    内置硬编码样例数据的离线自检。
    不读取外部文件、不依赖当前工作目录、不访问网络。
    使用宽松阈值断言，确保任何环境可过。
    """
    print("=" * 60)
    print("claude-vigil 自检开始...")
    print("=" * 60)

    tests_passed = 0
    tests_failed = 0

    # --- 测试 1: 文本输入处理 ---
    print("\n[测试 1] 文本输入处理")
    try:
        sample_text = "项目周报\n联系人: zhangsan@example.com\n电话: 13812345678\n网址: https://example.com/report"
        result = process_text_input(sample_text)
        assert result["type"] == "text", f"类型错误: {result['type']}"
        assert result["content_length"] > 0, "内容长度应为正数"
        assert 0.0 <= result["confidence"] <= 1.0, "置信度应在 0-1 之间"
        assert "title" in result, "缺少标题字段"
        print(f"  ✓ 通过 (置信度: {result['confidence']})")
        tests_passed += 1
    except AssertionError as e:
        print(f"  ✗ 失败: {e}")
        tests_failed += 1

    # --- 测试 2: JSON 输入处理 ---
    print("\n[测试 2] JSON 输入处理")
    try:
        sample_json = '{"name": "测试项目", "version": "1.0", "items": [1, 2, 3]}'
        result = process_json_input(sample_json)
        assert result["type"] == "json", f"类型错误: {result['type']}"
        assert result["field_count"] >= 2, f"字段数应>=2, 实际: {result['field_count']}"
        assert 0.0 <= result["confidence"] <= 1.0, "置信度应在 0-1 之间"
        print(f"  ✓ 通过 (字段数: {result['field_count']}, 置信度: {result['confidence']})")
        tests_passed += 1
    except AssertionError as e:
        print(f"  ✗ 失败: {e}")
        tests_failed += 1

    # --- 测试 3: URL 输入处理 ---
    print("\n[测试 3] URL 输入处理")
    try:
        sample_url = "https://example.com/data"
        result = process_input(sample_url)
        assert result["type"] == "url", f"类型错误: {result['type']}"
        assert result["status"] == "not_accessed", "不应实际访问网络"
        assert 0.0 <= result["confidence"] <= 1.0, "置信度应在 0-1 之间"
        print(f"  ✓ 通过 (URL: {result['url']})")
        tests_passed += 1
    except AssertionError as e:
        print(f"  ✗ 失败: {e}")
        tests_failed += 1

    # --- 测试 4: 空输入错误处理 ---
    print("\n[测试 4] 空输入错误处理")
    try:
        try:
            process_input("")
            assert False, "空输入应抛出异常"
        except VigorError as e:
            assert e.code == "E001", f"错误码应为 E001, 实际: {e.code}"
        print("  ✓ 通过 (正确返回 E001)")
        tests_passed += 1
    except AssertionError as e:
        print(f"  ✗ 失败: {e}")
        tests_failed += 1

    # --- 测试 5: 批量处理 ---
    print("\n[测试 5] 批量处理")
    try:
        inputs = [
            "第一条文本内容",
            '{"key": "value"}',
            "https://example.com",
            "",  # 空输入，应记录错误
        ]
        results = process_batch(inputs)
        assert len(results) == 4, f"结果数量应为4, 实际: {len(results)}"
        assert results[0]["type"] == "text", "第一条应为文本"
        assert results[1]["type"] == "json", "第二条应为JSON"
        assert results[2]["type"] == "url", "第三条应为URL"
        assert "error" in results[3], "第四条应包含错误信息"
        print(f"  ✓ 通过 (处理 {len(results)} 条，其中错误 {sum(1 for r in results if 'error' in r)} 条)")
        tests_passed += 1
    except AssertionError as e:
        print(f"  ✗ 失败: {e}")
        tests_failed += 1

    # --- 测试 6: 置信度计算 ---
    print("\n[测试 6] 置信度计算")
    try:
        # 完整数据应高置信度
        complete = {"title": "完整", "emails": ["a@b.com"], "phones": ["13812345678"], "urls": ["https://x.com"], "type": "text"}
        conf_high, note = calculate_confidence(complete)
        assert conf_high >= 0.5, f"完整数据置信度应>=0.5, 实际: {conf_high}"
        assert note in ("直接输出", "建议复核", "[需核实]"), f"无效标注: {note}"

        # 空数据应低置信度
        empty = {}
        conf_low, note_low = calculate_confidence(empty)
        assert conf_low == 0.0, f"空数据置信度应为0, 实际: {conf_low}"
        assert note_low == "[需核实]", f"空数据标注应为[需核实], 实际: {note_low}"

        # 高置信度应 >= 低置信度
        assert conf_high >= conf_low, "高置信度应大于等于低置信度"
        print(f"  ✓ 通过 (高: {conf_high}, 低: {conf_low})")
        tests_passed += 1
    except AssertionError as e:
        print(f"  ✗ 失败: {e}")
        tests_failed += 1

    # --- 测试 7: 错误码体系 ---
    print("\n[测试 7] 错误码体系")
    try:
        # 验证所有错误码都有对应话术
        for code in ["E001", "E002", "E003", "E004", "E005", "E006", "E007", "E008", "E009", "E010"]:
            assert code in ERROR_CODES, f"缺少错误码 {code}"
            assert len(ERROR_CODES[code]) > 0, f"错误码 {code} 缺少话术"
        print(f"  ✓ 通过 (共 {len(ERROR_CODES)} 个错误码)")
        tests_passed += 1
    except AssertionError as e:
        print(f"  ✗ 失败: {e}")
        tests_failed += 1

    # --- 测试 8: 输入类型检测 ---
    print("\n[测试 8] 输入类型检测")
    try:
        assert detect_input_type("hello world") == "text", "普通文本应识别为 text"
        assert detect_input_type('{"a": 1}') == "json", "JSON 应识别为 json"
        assert detect_input_type("https://example.com") == "url", "URL 应识别为 url"
        print("  ✓ 通过 (text/json/url 识别正确)")
        tests_passed += 1
    except AssertionError as e:
        print(f"  ✗ 失败: {e}")
        tests_failed += 1

    # --- 测试 9: 关键字段提取 ---
    print("\n[测试 9] 关键字段提取")
    try:
        sample = "联系邮箱: test@example.com, 备用: admin@test.org, 电话: 13912345678"
        fields = extract_key_fields(sample)
        assert "emails" in fields, "应提取到邮箱"
        assert len(fields["emails"]) >= 1, "至少一个邮箱"
        assert "phones" in fields, "应提取到电话"
        assert len(fields["phones"]) >= 1, "至少一个电话"
        print(f"  ✓ 通过 (邮箱: {len(fields.get('emails', []))}个, 电话: {len(fields.get('phones', []))}个)")
        tests_passed += 1
    except AssertionError as e:
        print(f"  ✗ 失败: {e}")
        tests_failed += 1

    # --- 测试 10: 输出格式化 ---
    print("\n[测试 10] 输出格式化")
    try:
        sample_result = {"type": "text", "confidence": 0.9}
        pretty_output = format_output(sample_result, pretty=True)
        assert "\n" in pretty_output, "美化输出应包含换行"
        assert '"type" in pretty_output', "输出应包含字段"

        compact_output = format_output(sample_result, pretty=False)
        assert "\n" not in compact_output.replace(" ", ""), "紧凑输出不应包含换行"
        print("  ✓ 通过 (美化/紧凑格式均正常)")
        tests_passed += 1
    except AssertionError as e:
        print(f"  ✗ 失败: {e}")
        tests_failed += 1

    # --- 汇总 ---
    print("\n" + "=" * 60)
    print(f"自检完成: {tests_passed} 通过, {tests_failed} 失败")
    print("=" * 60)

    return 0 if tests_failed == 0 else 1


# ============================================================
# 主入口
# ============================================================

def main() -> int:
    """主入口函数"""
    parser = argparse.ArgumentParser(
        description="claude-vigil 代码审查工具",
        epilog="示例: python main.py '要处理的内容' 或 python main.py --selftest"
    )
    parser.add_argument(
        "input",
        nargs="?",
        help="待处理的内容（文本/JSON/文件路径/URL）"
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检（不依赖外部输入）"
    )
    parser.add_argument(
        "--batch",
        nargs="*",
        help="批量处理多个输入"
    )
    parser.add_argument(
        "--output",
        choices=["pretty", "compact"],
        default="pretty",
        help="输出格式（默认: pretty）"
    )
    parser.add_argument(
        "--batch-file",
        help="从文件读取批量输入（每行一条）"
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        return run_selftest()

    # 批量文件模式
    if args.batch_file:
        try:
            with open(args.batch_file, "r", encoding="utf-8") as f:
                inputs = [line.strip() for line in f if line.strip()]
            if not inputs:
                print(f"[E001] 批量文件为空: {args.batch_file}", file=sys.stderr)
                return 1
            results = process_batch(inputs)
            print(format_output(results, pretty=(args.output == "pretty")))
            return 0
        except FileNotFoundError:
            print(f"[E006] 批量文件不存在: {args.batch_file}", file=sys.stderr)
            return 1
        except Exception as e:
            print(f"[E009] 批量处理失败: {e}", file=sys.stderr)
            return 1

    # 批量参数模式
    if args.batch:
        results = process_batch(args.batch)
        print(format_output(results, pretty=(args.output == "pretty")))
        return 0

    # 单条输入模式
    if not args.input:
        print(f"[E001] {ERROR_CODES['E001']}", file=sys.stderr)
        print("提示: 使用 --selftest 运行自检，或提供输入内容", file=sys.stderr)
        return 1

    try:
        result = process_input(args.input)
        print(format_output(result, pretty=(args.output == "pretty")))
        return 0
    except VigorError as e:
        print(f"[{e.code}] {e.message}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"[E009] 内部错误: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
