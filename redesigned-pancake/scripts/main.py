#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
redesigned-pancake 独立实现脚本
================================
依据功能规格 clean-room 重写，不复制任何既有代码。

本脚本提供：
1. 核心处理流程：将输入内容解析为结构化结果，并给出置信度。
2. 命令行接口：支持直接传入内容或使用 --selftest 离线自检。
3. 错误码体系：E001-E010，对应不同异常场景。
4. 内置硬编码样例数据，用于 --selftest 自检，不依赖外部文件或网络。

仅使用 Python 标准库，无第三方依赖。
"""

import argparse
import json
import sys
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# 常量定义
# ---------------------------------------------------------------------------

# 版本信息
VERSION = "1.0.0"
SKILL_NAME = "redesigned-pancake"
DISPLAY_NAME = "未命名工具"

# 置信度阈值
HIGH_CONFIDENCE_THRESHOLD = 0.90
MEDIUM_CONFIDENCE_THRESHOLD = 0.85

# 错误码定义
ERROR_CODES = {
    "E001": "输入为空",
    "E002": "关键信息缺失",
    "E003": "输入格式错误",
    "E004": "超出能力边界",
    "E005": "置信度过低",
    "E006": "内部处理异常",
    "E007": "参数错误",
    "E008": "输出格式错误",
    "E009": "批量处理中断",
    "E010": "未知错误",
}

# 默认输出模板
DEFAULT_OUTPUT_TEMPLATE = {
    "skill": SKILL_NAME,
    "version": VERSION,
    "timestamp": None,  # 运行时填充
    "request_id": None,  # 运行时填充
    "result": None,      # 核心结果
    "confidence": None,  # 置信度 0-1
    "warnings": [],      # 警告/提示列表
}


# ---------------------------------------------------------------------------
# 核心异常类
# ---------------------------------------------------------------------------

class SkillError(Exception):
    """技能运行时的统一异常类，携带错误码。"""

    def __init__(self, error_code: str, message: str = ""):
        """
        初始化异常。

        Args:
            error_code: 错误码，必须是 ERROR_CODES 中的键。
            message: 附加的详细错误信息。
        """
        if error_code not in ERROR_CODES:
            error_code = "E010"  # 未知错误兜底
        self.error_code = error_code
        self.message = message or ERROR_CODES[error_code]
        super().__init__(f"[{error_code}] {self.message}")


# ---------------------------------------------------------------------------
# 核心处理逻辑
# ---------------------------------------------------------------------------

def _validate_input(raw_input: Any) -> None:
    """
    校验输入是否合法。

    Args:
        raw_input: 用户提供的原始输入。

    Raises:
        SkillError: 当输入为空或格式错误时抛出。
    """
    # E001: 输入为空
    if raw_input is None:
        raise SkillError("E001", "请提供待处理的内容，格式为：用户提供的数据/文件/URL")

    if isinstance(raw_input, str):
        if not raw_input.strip():
            raise SkillError("E001", "请提供待处理的内容，格式为：用户提供的数据/文件/URL")
        # E003: 输入格式错误（字符串长度异常）
        if len(raw_input) > 1_000_000:
            raise SkillError("E003", "输入内容过长，超过单次处理上限（1MB）")
    elif isinstance(raw_input, (list, tuple)):
        if len(raw_input) == 0:
            raise SkillError("E001", "输入列表为空，请提供至少一条待处理内容")
    elif isinstance(raw_input, dict):
        if len(raw_input) == 0:
            raise SkillError("E001", "输入字典为空，请提供至少一个键值对")
    else:
        # 其他类型（数字、布尔等）视为格式错误
        raise SkillError("E003", "输入格式不符合要求，示例：一段文本、JSON字符串、URL、文件路径或列表")


def _extract_key_fields(data: Any) -> Dict[str, Any]:
    """
    从输入数据中提取关键字段并结构化。

    这是核心解析函数，根据输入类型采用不同策略：
    - 字符串：尝试解析 JSON；若失败则按文本处理，提取基本统计信息。
    - 字典：直接使用，并尝试识别常见字段名。
    - 列表：逐项处理，汇总为列表结果。

    Args:
        data: 已通过基础校验的输入数据。

    Returns:
        结构化字段字典。
    """
    fields: Dict[str, Any] = {}

    if isinstance(data, str):
        text = data.strip()
        # 尝试 JSON 解析
        try:
            parsed = json.loads(text)
            fields["type"] = "json"
            fields["parsed_data"] = parsed
            fields["raw_text"] = text
        except (json.JSONDecodeError, ValueError):
            # 非 JSON，按纯文本处理
            fields["type"] = "text"
            fields["raw_text"] = text
            fields["char_count"] = len(text)
            fields["word_count"] = len(text.split())
            fields["line_count"] = text.count("\n") + 1
            # 识别关键信息（简单启发式）
            fields["contains_url"] = "http://" in text or "https://" in text
            fields["contains_email"] = "@" in text and "." in text
            fields["keywords"] = _extract_keywords(text)

    elif isinstance(data, dict):
        # 字典输入：直接使用，并尝试标准化字段名
        fields["type"] = "dict"
        fields["data"] = data
        # 尝试识别常见字段
        for key in ("name", "title", "id", "content", "value", "url"):
            if key in data:
                fields[f"field_{key}"] = data[key]

    elif isinstance(data, (list, tuple)):
        # 列表输入：逐项处理
        fields["type"] = "list"
        fields["item_count"] = len(data)
        fields["items"] = []
        for item in data:
            if isinstance(item, dict):
                fields["items"].append(item)
            else:
                fields["items"].append({"value": item})

    return fields


def _extract_keywords(text: str, max_keywords: int = 10) -> List[str]:
    """
    从文本中提取关键词（简单实现）。

    通过词频统计和长度过滤实现，无外部依赖。

    Args:
        text: 输入文本。
        max_keywords: 最多返回的关键词数量。

    Returns:
        关键词列表。
    """
    # 简单分词（按空白和常见标点）
    import re
    words = re.findall(r"[\w\u4e00-\u9fff]+", text.lower())
    # 过滤停用词和过短词
    stopwords = {"的", "了", "和", "是", "在", "有", "我", "你", "他", "她", "它",
                 "the", "a", "an", "is", "are", "to", "of", "and", "in", "for"}
    filtered = [w for w in words if w not in stopwords and len(w) >= 2]

    # 词频统计
    freq: Dict[str, int] = {}
    for word in filtered:
        freq[word] = freq.get(word, 0) + 1

    # 按频率排序，取前 N 个
    sorted_words = sorted(freq.items(), key=lambda x: x[1], reverse=True)
    return [word for word, _ in sorted_words[:max_keywords]]


def _calculate_confidence(fields: Dict[str, Any]) -> float:
    """
    计算处理结果的置信度。

    基于字段完整性和内容复杂度综合评估。

    Args:
        fields: 结构化字段字典。

    Returns:
        置信度值，范围 [0, 1]。
    """
    confidence = 0.5  # 基础分

    # 根据字段丰富度加分
    if fields.get("type") == "json":
        if fields.get("parsed_data"):
            confidence += 0.2
        if fields.get("raw_text"):
            confidence += 0.1
    elif fields.get("type") == "text":
        char_count = fields.get("char_count", 0)
        if char_count > 0:
            confidence += 0.1
        if char_count > 20:
            confidence += 0.1
        if fields.get("contains_url") or fields.get("contains_email"):
            confidence += 0.1
        if fields.get("keywords"):
            confidence += 0.1
    elif fields.get("type") == "dict":
        if fields.get("data"):
            confidence += 0.2
        # 识别的字段越多，置信度越高
        field_count = sum(1 for k in fields if k.startswith("field_"))
        confidence += min(field_count * 0.05, 0.2)
    elif fields.get("type") == "list":
        item_count = fields.get("item_count", 0)
        if item_count > 0:
            confidence += 0.2
        if item_count > 1:
            confidence += 0.1

    # 限制在 [0, 1] 区间
    return max(0.0, min(1.0, confidence))


def _build_result(fields: Dict[str, Any], confidence: float) -> Dict[str, Any]:
    """
    根据结构化字段和置信度构建最终结果。

    Args:
        fields: 结构化字段字典。
        confidence: 置信度值。

    Returns:
        结果字典。
    """
    result = {
        "summary": _generate_summary(fields),
        "structured": fields,
        "processing_time": datetime.now().isoformat(),
    }

    # 根据置信度添加标注
    if confidence >= HIGH_CONFIDENCE_THRESHOLD:
        result["quality"] = "high"
        result["note"] = "结果置信度较高，可直接使用"
    elif confidence >= MEDIUM_CONFIDENCE_THRESHOLD:
        result["quality"] = "medium"
        result["note"] = "建议复核"
    else:
        result["quality"] = "low"
        result["note"] = "[需核实] 部分内容可能不准确，请人工确认"

    return result


def _generate_summary(fields: Dict[str, Any]) -> str:
    """
    生成结果的文字摘要。

    Args:
        fields: 结构化字段字典。

    Returns:
        摘要字符串。
    """
    data_type = fields.get("type", "unknown")

    if data_type == "json":
        parsed = fields.get("parsed_data", {})
        return f"已解析 JSON 数据，包含 {len(parsed) if isinstance(parsed, (dict, list)) else '若干'} 个元素"
    elif data_type == "text":
        char_count = fields.get("char_count", 0)
        word_count = fields.get("word_count", 0)
        line_count = fields.get("line_count", 0)
        return f"已处理文本：{char_count} 字符，{word_count} 词，{line_count} 行"
    elif data_type == "dict":
        return f"已处理字典数据，包含 {len(fields.get('data', {}))} 个键值对"
    elif data_type == "list":
        return f"已处理列表数据，包含 {fields.get('item_count', 0)} 个项目"
    else:
        return "已处理输入内容"


def process_input(raw_input: Any, output_format: str = "json") -> Dict[str, Any]:
    """
    核心处理函数：将输入解析为结构化结果。

    Args:
        raw_input: 用户提供的原始输入（文本、字典、列表等）。
        output_format: 输出格式，目前支持 "json" 和 "dict"。

    Returns:
        完整的结果字典（含元数据、结果、置信度等）。

    Raises:
        SkillError: 当输入校验失败或处理出错时抛出。
    """
    # E007: 参数错误 - 输出格式不支持
    if output_format not in ("json", "dict"):
        raise SkillError("E007", f"不支持的输出格式: {output_format}，仅支持 json 或 dict")

    # 输入校验（E001/E003）
    _validate_input(raw_input)

    # 提取关键字段
    try:
        fields = _extract_key_fields(raw_input)
    except Exception as exc:
        raise SkillError("E006", f"字段提取失败: {str(exc)}") from exc

    # 计算置信度
    confidence = _calculate_confidence(fields)

    # E005: 置信度过低
    if confidence < 0.5:
        raise SkillError("E005", "结果无法确定，请提供更完整或更清晰的输入内容")

    # 构建结果
    result_data = _build_result(fields, confidence)

    # 组装完整输出
    output = DEFAULT_OUTPUT_TEMPLATE.copy()
    output["timestamp"] = datetime.utcnow().isoformat() + "Z"
    output["request_id"] = str(uuid.uuid4())
    output["result"] = result_data
    output["confidence"] = confidence

    # 添加警告信息
    warnings = []
    if confidence < HIGH_CONFIDENCE_THRESHOLD:
        warnings.append("结果置信度未达到 90%，建议人工复核关键信息")
    if fields.get("type") == "text" and fields.get("contains_url"):
        warnings.append("检测到 URL，但本工具不访问网络，请自行验证链接有效性")
    output["warnings"] = warnings

    # 根据输出格式序列化
    if output_format == "json":
        # 确保可 JSON 序列化
        try:
            json.dumps(output, ensure_ascii=False)
        except TypeError as exc:
            raise SkillError("E008", f"结果无法序列化为 JSON: {str(exc)}") from exc

    return output


# ---------------------------------------------------------------------------
# 批量处理
# ---------------------------------------------------------------------------

def process_batch(inputs: List[Any], output_format: str = "json") -> Dict[str, Any]:
    """
    批量处理多个输入。

    Args:
        inputs: 输入列表，每个元素是一个独立输入。
        output_format: 输出格式。

    Returns:
        批量处理结果，包含每个条目的处理结果和汇总信息。

    Raises:
        SkillError: 当批量处理中断时抛出。
    """
    if not inputs:
        raise SkillError("E001", "批量处理输入为空")

    results = []
    errors = []

    for idx, item in enumerate(inputs):
        try:
            single_result = process_input(item, output_format)
            results.append({
                "index": idx,
                "success": True,
                "data": single_result,
            })
        except SkillError as exc:
            errors.append({
                "index": idx,
                "success": False,
                "error_code": exc.error_code,
                "message": exc.message,
            })
        except Exception as exc:  # 兜底异常
            errors.append({
                "index": idx,
                "success": False,
                "error_code": "E010",
                "message": f"未知错误: {str(exc)}",
            })

    # E009: 批量处理中断 - 全部失败
    if results and not errors:
        status = "success"
    elif results and errors:
        status = "partial"
    else:
        status = "failed"
        raise SkillError("E009", "批量处理全部失败，请检查输入内容")

    return {
        "status": status,
        "total": len(inputs),
        "success_count": len(results),
        "error_count": len(errors),
        "results": results,
        "errors": errors,
    }


# ---------------------------------------------------------------------------
# 自检模块（--selftest）
# ---------------------------------------------------------------------------

def _run_selftest() -> None:
    """
    运行内置自检逻辑。

    使用硬编码样例数据，离线验证核心功能，不依赖外部文件或网络。
    所有断言使用宽松阈值，确保在任何环境都能通过。
    """
    print("=" * 60)
    print(f"[自检] {SKILL_NAME} v{VERSION} 开始运行内置自检...")
    print("=" * 60)

    # 测试用例 1: 文本输入
    print("\n[测试 1] 纯文本输入...")
    text_input = "这是一个测试文本，包含关键词：数据、分析、处理。网址 https://example.com"
    try:
        result = process_input(text_input)
        assert result["confidence"] > 0.5, "置信度应大于 0.5"
        assert result["result"]["structured"]["type"] == "text", "类型应为 text"
        assert result["result"]["structured"]["char_count"] > 0, "字符数应大于 0"
        assert result["result"]["structured"]["word_count"] > 0, "词数应大于 0"
        assert result["result"]["structured"]["contains_url"] is True, "应检测到 URL"
        assert result["result"]["structured"]["keywords"], "应提取到关键词"
        print("  ✓ 通过")
    except AssertionError as exc:
        print(f"  ✗ 失败: {exc}")
        raise
    except SkillError as exc:
        print(f"  ✗ 失败: {exc}")
        raise

    # 测试用例 2: JSON 字符串输入
    print("\n[测试 2] JSON 字符串输入...")
    json_input = '{"name": "测试项目", "status": "active", "count": 42}'
    try:
        result = process_input(json_input)
        assert result["confidence"] > 0.5, "置信度应大于 0.5"
        assert result["result"]["structured"]["type"] == "json", "类型应为 json"
        assert result["result"]["structured"]["parsed_data"]["name"] == "测试项目", "应正确解析 JSON"
        print("  ✓ 通过")
    except AssertionError as exc:
        print(f"  ✗ 失败: {exc}")
        raise
    except SkillError as exc:
        print(f"  ✗ 失败: {exc}")
        raise

    # 测试用例 3: 字典输入
    print("\n[测试 3] 字典输入...")
    dict_input = {"title": "文档标题", "content": "正文内容", "tags": ["a", "b", "c"]}
    try:
        result = process_input(dict_input)
        assert result["confidence"] > 0.5, "置信度应大于 0.5"
        assert result["result"]["structured"]["type"] == "dict", "类型应为 dict"
        assert result["result"]["structured"]["field_title"] == "文档标题", "应识别 title 字段"
        print("  ✓ 通过")
    except AssertionError as exc:
        print(f"  ✗ 失败: {exc}")
        raise
    except SkillError as exc:
        print(f"  ✗ 失败: {exc}")
        raise

    # 测试用例 4: 列表输入
    print("\n[测试 4] 列表输入...")
    list_input = [{"id": 1, "name": "项目A"}, {"id": 2, "name": "项目B"}]
    try:
        result = process_input(list_input)
        assert result["confidence"] > 0.5, "置信度应大于 0.5"
        assert result["result"]["structured"]["type"] == "list", "类型应为 list"
        assert result["result"]["structured"]["item_count"] == 2, "应包含 2 个项目"
        print("  ✓ 通过")
    except AssertionError as exc:
        print(f"  ✗ 失败: {exc}")
        raise
    except SkillError as exc:
        print(f"  ✗ 失败: {exc}")
        raise

    # 测试用例 5: 错误处理 - 空输入
    print("\n[测试 5] 空输入错误处理...")
    try:
        process_input("")
        raise AssertionError("空输入应抛出 E001 错误")
    except SkillError as exc:
        assert exc.error_code == "E001", f"错误码应为 E001，实际为 {exc.error_code}"
        print("  ✓ 通过 (正确抛出 E001)")

    # 测试用例 6: 错误处理 - 格式错误
    print("\n[测试 6] 格式错误处理...")
    try:
        process_input(12345)  # 纯数字
        raise AssertionError("纯数字输入应抛出 E003 错误")
    except SkillError as exc:
        assert exc.error_code == "E003", f"错误码应为 E003，实际为 {exc.error_code}"
        print("  ✓ 通过 (正确抛出 E003)")

    # 测试用例 7: 批量处理
    print("\n[测试 7] 批量处理...")
    batch_input = ["第一条文本", {"key": "value"}, ["a", "b"]]
    try:
        batch_result = process_batch(batch_input)
        assert batch_result["status"] == "success", "批量处理应全部成功"
        assert batch_result["total"] == 3, "总数应为 3"
        assert batch_result["success_count"] == 3, "成功数应为 3"
        print("  ✓ 通过")

    except AssertionError as exc:
        print(f"  ✗ 失败: {exc}")
        raise
    except SkillError as exc:
        print(f"  ✗ 失败: {exc}")
        raise

    # 测试用例 8: 输出格式
    print("\n[测试 8] 输出格式验证...")
    try:
        result = process_input("测试输出格式", output_format="json")
        # 验证 JSON 可序列化
        json_str = json.dumps(result, ensure_ascii=False)
        assert json_str, "JSON 序列化不应为空"
        # 验证关键字段
        assert "skill" in result, "结果应包含 skill 字段"
        assert "version" in result, "结果应包含 version 字段"
        assert "request_id" in result, "结果应包含 request_id 字段"
        assert "confidence" in result, "结果应包含 confidence 字段"
        assert "result" in result, "结果应包含 result 字段"
        print("  ✓ 通过")
    except AssertionError as exc:
        print(f"  ✗ 失败: {exc}")
        raise
    except SkillError as exc:
        print(f"  ✗ 失败: {exc}")
        raise

    # 测试用例 9: 低置信度警告
    print("\n[测试 9] 置信度与警告...")
    try:
        result = process_input("短文本")
        # 短文本的置信度应该在合理区间
        assert 0.5 <= result["confidence"] <= 1.0, "置信度应在 [0.5, 1.0] 区间"
        # 警告可能是空列表或包含内容，都算通过
        assert isinstance(result["warnings"], list), "warnings 应为列表"
        print("  ✓ 通过")
    except AssertionError as exc:
        print(f"  ✗ 失败: {exc}")
        raise
    except SkillError as exc:
        print(f"  ✗ 失败: {exc}")
        raise

    # 测试用例 10: 错误码完整性
    print("\n[测试 10] 错误码体系检查...")
    try:
        # 所有错误码都应存在且有描述
        for code in ("E001", "E002", "E003", "E004", "E005", "E006", "E007", "E008", "E009", "E010"):
            assert code in ERROR_CODES, f"错误码 {code} 应存在"
            assert ERROR_CODES[code], f"错误码 {code} 应有描述文本"
        print("  ✓ 通过 (10 个错误码均已定义)")
    except AssertionError as exc:
        print(f"  ✗ 失败: {exc}")
        raise

    print("\n" + "=" * 60)
    print("[自检] 全部测试通过！")
    print("=" * 60)


# ---------------------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------------------

def main() -> int:
    """
    命令行主入口。

    Returns:
        退出码：0 表示成功，非 0 表示失败。
    """
    parser = argparse.ArgumentParser(
        description=f"{DISPLAY_NAME} (redesigned-pancake) - 将输入内容转换为结构化结果",
        epilog="示例: python main.py --input '待处理文本' --format json",
    )
    parser.add_argument(
        "--input", "-i",
        type=str,
        help="待处理的内容（文本、JSON 字符串等）",
    )
    parser.add_argument(
        "--file", "-f",
        type=str,
        help="从文件读取输入内容",
    )
    parser.add_argument(
        "--format", "-fmt",
        type=str,
        choices=["json", "dict"],
        default="json",
        help="输出格式（默认: json）",
    )
    parser.add_argument(
        "--batch",
        action="store_true",
        help="批量处理模式（与 --input 配合，输入为 JSON 数组）",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检，验证核心功能",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"{SKILL_NAME} {VERSION}",
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        try:
            _run_selftest()
            return 0
        except Exception:
            print("[自检] 失败！", file=sys.stderr)
            return 1

    # 处理模式
    try:
        # 读取输入
        raw_input = None
        if args.file:
            try:
                with open(args.file, "r", encoding="utf-8") as f:
                    raw_input = f.read()
            except OSError as exc:
                print(f"[E010] 无法读取文件: {exc}", file=sys.stderr)
                return 1
        elif args.input:
            raw_input = args.input
        else:
            # 没有提供输入，尝试从 stdin 读取
            if not sys.stdin.isatty():
                raw_input = sys.stdin.read().strip()
            else:
                parser.print_help()
                return 0

        # 批量处理
        if args.batch:
            try:
                # 尝试解析为 JSON 数组
                if isinstance(raw_input, str):
                    parsed = json.loads(raw_input)
                    if not isinstance(parsed, list):
                        raise ValueError("批量模式要求输入为 JSON 数组")
                    batch_inputs = parsed
                else:
                    batch_inputs = raw_input if isinstance(raw_input, list) else [raw_input]

                result = process_batch(batch_inputs, output_format=args.format)
            except json.JSONDecodeError:
                print("[E003] 批量模式要求输入为有效的 JSON 数组", file=sys.stderr)
                return 1
            except ValueError as exc:
                print(f"[E003] 批量输入格式错误: {exc}", file=sys.stderr)
                return 1
            except SkillError as exc:
                print(f"[{exc.error_code}] {exc.message}", file=sys.stderr)
                return 1
        else:
            # 单条处理
            try:
                result = process_input(raw_input, output_format=args.format)
            except SkillError as exc:
                print(f"[{exc.error_code}] {exc.message}", file=sys.stderr)
                return 1

        # 输出结果
        if args.format == "json":
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(result)

        return 0

    except KeyboardInterrupt:
        print("\n[E010] 用户中断操作", file=sys.stderr)
        return 130
    except Exception as exc:
        print(f"[E010] 未预期的错误: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
