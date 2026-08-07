#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
claude-code-blueprint - 独立实现脚本
仅供学习与参考用途，不构成任何专业建议。
"""

import argparse
import json
import sys
import re
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# 错误码定义
# ---------------------------------------------------------------------------
ERROR_CODES = {
    "E001": "输入为空",
    "E002": "关键信息缺失",
    "E003": "输入格式错误",
    "E004": "超出能力边界",
    "E005": "置信度过低",
    "E006": "内部处理错误",
    "E007": "参数错误",
    "E008": "输出生成失败",
    "E009": "批量处理中断",
    "E010": "未知异常",
}


def make_error(code: str, detail: str = "") -> Dict[str, str]:
    """构造标准错误返回结构。"""
    msg = ERROR_CODES.get(code, "未知错误")
    result = {"error_code": code, "message": msg}
    if detail:
        result["detail"] = detail
    return result


# ---------------------------------------------------------------------------
# 核心处理逻辑
# ---------------------------------------------------------------------------
def parse_input(raw_input: Any) -> Tuple[bool, Any, Optional[Dict[str, str]]]:
    """
    解析输入内容，识别关键信息。
    返回 (是否成功, 解析结果, 错误信息)
    """
    if raw_input is None or (isinstance(raw_input, str) and not raw_input.strip()):
        return False, None, make_error("E001")

    # 尝试解析 JSON
    if isinstance(raw_input, str):
        try:
            data = json.loads(raw_input)
            return True, data, None
        except json.JSONDecodeError:
            # 非 JSON 文本，按文本处理
            return True, {"text": raw_input.strip()}, None

    if isinstance(raw_input, (dict, list)):
        return True, raw_input, None

    return False, None, make_error("E003", "不支持的输入类型")


def extract_key_fields(data: Any) -> Tuple[bool, Dict[str, Any], Optional[Dict[str, str]]]:
    """
    从解析后的数据中提取关键字段并结构化。
    返回 (是否成功, 结构化结果, 错误信息)
    """
    if data is None:
        return False, {}, make_error("E001")

    result: Dict[str, Any] = {}

    # 处理字典类型
    if isinstance(data, dict):
        # 处理纯文本包装的情况
        if "text" in data and isinstance(data["text"], str):
            text = data["text"]
            result["text"] = text
            result["length"] = len(text)
            # 简单识别关键信息
            urls = re.findall(r'https?://[^\s]+', text)
            if urls:
                result["urls"] = urls
            emails = re.findall(r'[\w.+-]+@[\w-]+\.[\w.-]+', text)
            if emails:
                result["emails"] = emails
        else:
            # 处理普通字典
            for key in ["id", "name", "title", "content", "type", "data"]:
                if key in data and data[key] is not None:
                    result[key] = data[key]
            # 保留所有其他字段
            for key, value in data.items():
                if key not in result:
                    result[key] = value

    # 处理列表类型
    elif isinstance(data, list):
        result["items"] = data
        result["count"] = len(data)
        # 尝试识别列表中的共性字段
        if data and isinstance(data[0], dict):
            common_keys = set(data[0].keys())
            for item in data[1:]:
                if isinstance(item, dict):
                    common_keys &= set(item.keys())
            if common_keys:
                result["common_fields"] = sorted(common_keys)

    # 检查关键信息是否完整
    if not result:
        return False, {}, make_error("E002", "未能提取到有效信息")

    return True, result, None


def calculate_confidence(data: Dict[str, Any]) -> float:
    """
    计算结果置信度。
    返回 0-100 的置信度分数。
    """
    if not data:
        return 0.0

    score = 0.0
    total_checks = 0

    # 检查是否有结构化字段
    if any(k in data for k in ["id", "name", "title", "content"]):
        score += 40
    total_checks += 1

    # 检查是否有明确的数据类型
    if "type" in data or "text" in data or "items" in data:
        score += 20
    total_checks += 1

    # 检查内容完整性
    if "content" in data or "items" in data or "text" in data:
        score += 20
    total_checks += 1

    # 检查附加信息
    if "count" in data or "urls" in data or "emails" in data:
        score += 20
    total_checks += 1

    return min(100.0, score)


def format_output(data: Dict[str, Any], confidence: float) -> Dict[str, Any]:
    """
    按约定格式生成输出，标注置信度。
    """
    result = {
        "data": data,
        "confidence": round(confidence, 1),
        "confidence_label": "直接输出",
    }

    if confidence < 85:
        result["confidence_label"] = "[需核实]"
        result["warning"] = "结果不确定，请人工复核"
    elif confidence < 90:
        result["confidence_label"] = "建议复核"

    return result


def process_single_input(raw_input: Any) -> Dict[str, Any]:
    """
    处理单个输入，返回标准结果。
    """
    # Step 1: 解析输入
    ok, parsed, err = parse_input(raw_input)
    if not ok:
        return err

    # Step 2: 提取关键字段
    ok, extracted, err = extract_key_fields(parsed)
    if not ok:
        return err

    # Step 3: 计算置信度并生成输出
    confidence = calculate_confidence(extracted)
    return format_output(extracted, confidence)


def process_batch(inputs: List[Any]) -> Dict[str, Any]:
    """
    批量处理多个输入。
    """
    if not inputs:
        return make_error("E001")

    results = []
    failed_count = 0

    for idx, item in enumerate(inputs):
        try:
            result = process_single_input(item)
            if "error_code" in result:
                failed_count += 1
                result["index"] = idx
            results.append(result)
        except Exception as e:
            failed_count += 1
            results.append({
                "index": idx,
                "error_code": "E010",
                "message": f"处理第 {idx + 1} 项时发生异常: {str(e)}"
            })

    return {
        "data": results,
        "total": len(inputs),
        "success": len(inputs) - failed_count,
        "failed": failed_count,
        "confidence": round(90.0 if failed_count == 0 else 60.0, 1),
    }


# ---------------------------------------------------------------------------
# 自检功能
# ---------------------------------------------------------------------------
def run_selftest() -> bool:
    """
    内置硬编码样例数据离线自检核心逻辑。
    不读外部文件、不依赖当前工作目录、不访问网络。
    """
    print("=" * 60)
    print("开始自检...")
    print("=" * 60)

    # 测试用例 1: 空输入
    print("\n[测试 1] 空输入处理")
    result = process_single_input(None)
    assert result.get("error_code") == "E001", f"期望 E001，实际 {result.get('error_code')}"
    print("  ✓ 空输入正确返回 E001")

    # 测试用例 2: JSON 输入
    print("\n[测试 2] JSON 输入处理")
    json_input = json.dumps({
        "id": "test-001",
        "name": "示例数据",
        "content": "这是一段测试内容",
        "type": "sample"
    })
    result = process_single_input(json_input)
    assert "error_code" not in result, f"不应有错误，实际 {result}"
    assert "data" in result, "缺少 data 字段"
    assert result["data"].get("id") == "test-001", "id 字段提取失败"
    assert result["confidence"] > 50, f"置信度应大于 50，实际 {result['confidence']}"
    print("  ✓ JSON 输入正确解析")
    print(f"  ✓ 置信度: {result['confidence']}%")

    # 测试用例 3: 文本输入
    print("\n[测试 3] 文本输入处理")
    text_input = "请访问 https://example.com 或联系 test@example.com"
    result = process_single_input(text_input)
    assert "error_code" not in result, f"不应有错误，实际 {result}"
    assert "urls" in result["data"], "URL 识别失败"
    assert "emails" in result["data"], "邮箱识别失败"
    assert len(result["data"]["urls"]) > 0, "URL 列表为空"
    assert len(result["data"]["emails"]) > 0, "邮箱列表为空"
    print("  ✓ 文本输入正确解析")
    print("  ✓ URL 和邮箱识别成功")

    # 测试用例 4: 列表输入
    print("\n[测试 4] 列表输入处理")
    list_input = [
        {"id": 1, "name": "项目A"},
        {"id": 2, "name": "项目B"},
        {"id": 3, "name": "项目C"}
    ]
    result = process_single_input(list_input)
    assert "error_code" not in result, f"不应有错误，实际 {result}"
    assert result["data"].get("count") == 3, f"数量应为 3，实际 {result['data'].get('count')}"
    assert "common_fields" in result["data"], "共性字段识别失败"
    assert set(result["data"]["common_fields"]) == {"id", "name"}, "共性字段不正确"
    print("  ✓ 列表输入正确解析")
    print("  ✓ 共性字段识别成功")

    # 测试用例 5: 批量处理
    print("\n[测试 5] 批量处理")
    batch_input = [
        {"name": "项目1", "content": "内容1"},
        "纯文本输入",
        None,  # 应失败
        ["列表项1", "列表项2"]
    ]
    result = process_batch(batch_input)
    assert result["total"] == 4, f"总数应为 4，实际 {result['total']}"
    assert result["success"] == 3, f"成功数应为 3，实际 {result['success']}"
    assert result["failed"] == 1, f"失败数应为 1，实际 {result['failed']}"
    print("  ✓ 批量处理正确")
    print(f"  ✓ 成功 {result['success']} 项，失败 {result['failed']} 项")

    # 测试用例 6: 错误码完整性
    print("\n[测试 6] 错误码完整性")
    for code in ["E001", "E002", "E003", "E004", "E005"]:
        assert code in ERROR_CODES, f"缺少错误码 {code}"
    print("  ✓ 核心错误码完整")

    print("\n" + "=" * 60)
    print("所有自检测试通过！")
    print("=" * 60)
    return True


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------
def main() -> int:
    """主函数入口。"""
    parser = argparse.ArgumentParser(
        description="claude-code-blueprint - 仅供学习与参考用途",
        epilog="示例: python main.py --input '{\"name\": \"测试\"}'"
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检（不读外部文件、不访问网络）"
    )
    parser.add_argument(
        "--input",
        type=str,
        help="输入内容（JSON 字符串或纯文本）"
    )
    parser.add_argument(
        "--batch",
        type=str,
        help="批量输入（JSON 数组字符串）"
    )
    parser.add_argument(
        "--format",
        choices=["json", "text"],
        default="json",
        help="输出格式（默认 json）"
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        try:
            run_selftest()
            return 0
        except AssertionError as e:
            print(f"自检失败: {e}", file=sys.stderr)
            return 1
        except Exception as e:
            print(f"自检发生异常: {e}", file=sys.stderr)
            return 1

    # 处理输入
    try:
        if args.batch:
            # 批量处理
            try:
                batch_data = json.loads(args.batch)
                if not isinstance(batch_data, list):
                    print(json.dumps(make_error("E003", "批量输入必须是 JSON 数组")), file=sys.stderr)
                    return 1
                result = process_batch(batch_data)
            except json.JSONDecodeError:
                print(json.dumps(make_error("E003", "批量输入不是有效的 JSON")), file=sys.stderr)
                return 1
        elif args.input:
            # 单条处理
            result = process_single_input(args.input)
        else:
            # 无输入
            print(json.dumps(make_error("E001")), file=sys.stderr)
            return 1

        # 输出结果
        if args.format == "json":
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            # 文本格式输出
            if "error_code" in result:
                print(f"[{result['error_code']}] {result['message']}")
            else:
                print(f"处理结果 (置信度: {result['confidence']}%)")
                print("-" * 40)
                if "data" in result:
                    for key, value in result["data"].items():
                        if not isinstance(value, (list, dict)):
                            print(f"  {key}: {value}")
                if result.get("confidence_label") == "[需核实]":
                    print("-" * 40)
                    print("⚠  [需核实] 请人工复核结果")

        return 0

    except KeyboardInterrupt:
        print(json.dumps(make_error("E009", "用户中断")), file=sys.stderr)
        return 1
    except Exception as e:
        print(json.dumps(make_error("E010", str(e))), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
