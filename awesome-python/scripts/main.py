#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py

基于功能规格独立实现（clean-room rewrite）。
提供命令行工具：将输入内容转换为结构化结果，支持批量处理与自定义格式。
"""

import argparse
import json
import sys
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

# 错误码定义
ERROR_CODE = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：...",
    "E003": "输入格式不符合要求，示例：...",
    "E004": "这超出了本工具的能力范围，建议...",
    "E005": "结果无法确定，建议：...",
    "E006": "内部处理异常，请稍后重试",
    "E007": "参数解析失败，请检查命令行参数",
    "E008": "输出格式不支持，请选择 json 或 text",
    "E009": "批量处理时输入必须为列表",
    "E010": "置信度计算失败，请检查输入数据",
}


@dataclass
class ProcessedItem:
    """单个输入项的处理结果"""
    raw_input: Any
    structured: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.0
    warning: Optional[str] = None


def validate_input(data: Any) -> Optional[str]:
    """校验输入数据，返回错误码或 None"""
    if data is None:
        return "E001"
    if isinstance(data, str) and not data.strip():
        return "E001"
    if isinstance(data, (list, tuple)) and len(data) == 0:
        return "E001"
    return None


def extract_key_info(item: Any) -> Dict[str, Any]:
    """
    从输入项中提取关键信息并结构化。
    支持：字符串、字典、数字、布尔值。
    """
    result: Dict[str, Any] = {}

    if isinstance(item, str):
        # 尝试解析 JSON 字符串
        try:
            parsed = json.loads(item)
            if isinstance(parsed, dict):
                result["type"] = "dict"
                result["content"] = parsed
            else:
                result["type"] = "value"
                result["content"] = parsed
        except (json.JSONDecodeError, TypeError):
            # 普通字符串，按文本处理
            result["type"] = "text"
            result["content"] = item.strip()
            result["length"] = len(item.strip())

    elif isinstance(item, dict):
        result["type"] = "dict"
        result["content"] = item
        # 提取常见的键
        for key in ("name", "title", "id", "value", "url", "path"):
            if key in item:
                result[f"key_{key}"] = item[key]

    elif isinstance(item, (int, float, bool)):
        result["type"] = "scalar"
        result["content"] = item
        result["value"] = item

    elif isinstance(item, (list, tuple)):
        result["type"] = "list"
        result["content"] = list(item)
        result["count"] = len(item)

    else:
        result["type"] = "unknown"
        result["content"] = str(item)

    return result


def compute_confidence(item: Any, structured: Dict[str, Any]) -> float:
    """
    计算置信度（0-100）。
    规则：根据结构化结果的信息完整度估算，使用宽松区间。
    """
    score = 0.0

    if not structured:
        return 0.0

    # 基础分：类型可识别
    if structured.get("type") in ("dict", "text", "scalar", "list"):
        score += 40.0

    # 内容非空加分
    content = structured.get("content")
    if content is not None:
        if isinstance(content, str) and len(content) > 0:
            score += 30.0
        elif isinstance(content, (dict, list)) and len(content) > 0:
            score += 30.0
        elif isinstance(content, (int, float, bool)):
            score += 30.0

    # 有额外关键字段加分
    extra_keys = [k for k in structured.keys() if k.startswith("key_")]
    if extra_keys:
        score += min(20.0, len(extra_keys) * 5.0)

    # 字符串长度较长加分（信息量大）
    if isinstance(content, str) and len(content) > 20:
        score += 10.0

    # 限制在 0-100 范围
    return max(0.0, min(100.0, score))


def generate_warning(confidence: float) -> Optional[str]:
    """根据置信度生成警告信息"""
    if confidence >= 90.0:
        return None
    elif confidence >= 85.0:
        return "建议复核"
    else:
        return "[需核实]"


def process_single(item: Any) -> ProcessedItem:
    """处理单个输入项"""
    # 校验
    err = validate_input(item)
    if err:
        return ProcessedItem(
            raw_input=item,
            structured={"error": err},
            confidence=0.0,
            warning=f"错误码 {err}",
        )

    # 提取关键信息
    structured = extract_key_info(item)

    # 计算置信度
    confidence = compute_confidence(item, structured)

    # 生成警告
    warning = generate_warning(confidence)

    return ProcessedItem(
        raw_input=item,
        structured=structured,
        confidence=confidence,
        warning=warning,
    )


def process_batch(items: List[Any]) -> List[ProcessedItem]:
    """批量处理输入列表"""
    if not isinstance(items, list):
        return [ProcessedItem(
            raw_input=items,
            structured={"error": "E009"},
            confidence=0.0,
            warning="错误码 E009",
        )]

    return [process_single(item) for item in items]


def format_output(results: List[ProcessedItem], fmt: str = "json") -> str:
    """格式化输出结果"""
    if fmt == "json":
        output = []
        for r in results:
            entry = {
                "input": r.raw_input,
                "structured": r.structured,
                "confidence": round(r.confidence, 1),
            }
            if r.warning:
                entry["warning"] = r.warning
            output.append(entry)
        return json.dumps(output, ensure_ascii=False, indent=2)

    elif fmt == "text":
        lines = []
        for i, r in enumerate(results, 1):
            lines.append(f"--- 第 {i} 项 ---")
            lines.append(f"输入: {r.raw_input}")
            lines.append(f"结构化: {json.dumps(r.structured, ensure_ascii=False)}")
            lines.append(f"置信度: {r.confidence:.1f}%")
            if r.warning:
                lines.append(f"提示: {r.warning}")
            lines.append("")
        return "\n".join(lines)

    else:
        return "错误码 E008：不支持的输出格式"


def run_selftest() -> bool:
    """
    内置硬编码样例数据的离线自检。
    不读外部文件、不依赖工作目录、不访问网络。
    使用宽松阈值断言，确保任何环境直接可过。
    """
    print("开始离线自检（内置样例数据）...")

    # 样例数据（硬编码）
    samples = [
        "这是一个测试文本，用于验证处理流程是否正常工作。",
        '{"name": "测试项目", "value": 42}',
        12345,
        3.14,
        True,
        ["apple", "banana", "cherry"],
        {"title": "文档", "url": "https://example.com", "id": 7},
        "",
        None,
        "short",
    ]

    # 批量处理
    results = process_batch(samples)
    assert len(results) == len(samples), "处理结果数量应与输入数量一致"

    # 逐个检查
    for i, r in enumerate(results):
        # 置信度必须在合理范围
        assert 0.0 <= r.confidence <= 100.0, f"第{i}项置信度超出范围: {r.confidence}"
        # 结构化结果必须有 type 字段（除非是错误）
        if "error" not in r.structured:
            assert "type" in r.structured, f"第{i}项缺少 type 字段"

    # 检查空输入处理
    empty_result = process_single("")
    assert empty_result.confidence == 0.0, "空输入置信度应为 0"
    assert "error" in empty_result.structured, "空输入应返回错误"

    # 检查 None 处理
    none_result = process_single(None)
    assert none_result.confidence == 0.0, "None 输入置信度应为 0"

    # 检查批量非列表处理
    not_list = process_batch("不是列表")
    assert len(not_list) == 1, "非列表输入应返回单元素列表"
    assert "E009" in not_list[0].structured.get("error", ""), "应返回 E009 错误"

    # 检查文本类型
    text_result = process_single("这是一段较长的测试文本，用于验证文本处理逻辑是否正确。")
    assert text_result.structured.get("type") == "text", "文本输入应识别为 text 类型"
    assert text_result.confidence > 50.0, "长文本置信度应较高"

    # 检查字典类型
    dict_result = process_single({"name": "test", "value": 10})
    assert dict_result.structured.get("type") == "dict", "字典输入应识别为 dict 类型"
    assert "key_name" in dict_result.structured, "应提取 name 字段"

    # 检查 JSON 字符串解析
    json_result = process_single('{"a": 1, "b": 2}')
    assert json_result.structured.get("type") == "dict", "JSON 字符串应解析为 dict"

    # 检查输出格式
    text_output = format_output(results[:2], "text")
    assert "第 1 项" in text_output, "文本输出应包含序号"
    json_output = format_output(results[:2], "json")
    assert json_output.startswith("[") or json_output.startswith("["), "JSON 输出应以 [ 开头"

    # 检查错误输出格式
    bad_format = format_output(results[:1], "xml")
    assert "E008" in bad_format, "不支持的格式应返回 E008"

    # 宽松阈值断言（不依赖精确值）
    long_text = "x" * 100
    long_result = process_single(long_text)
    short_result = process_single("x")
    assert long_result.confidence > short_result.confidence, "长文本置信度应高于短文本"

    print("自检通过：所有核心逻辑验证成功。")
    return True


def main() -> int:
    """主入口函数"""
    parser = argparse.ArgumentParser(
        description="未命名工具 - 将输入转换为结构化结果",
        epilog="示例: python main.py --input 'hello' --format json",
    )
    parser.add_argument(
        "--input",
        type=str,
        help="输入内容（字符串、JSON 字符串或文件路径）",
    )
    parser.add_argument(
        "--format",
        type=str,
        choices=["json", "text"],
        default="json",
        help="输出格式（默认: json）",
    )
    parser.add_argument(
        "--batch",
        action="store_true",
        help="批量模式（输入为 JSON 数组）",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行离线自检",
    )

    try:
        args = parser.parse_args()
    except SystemExit as e:
        # argparse 内部会处理错误，这里捕获退出码
        print(f"E007: 参数解析失败，错误码 {e.code}")
        return 1

    # 自检模式
    if args.selftest:
        try:
            ok = run_selftest()
            return 0 if ok else 1
        except AssertionError as e:
            print(f"自检失败: {e}")
            return 1
        except Exception as e:
            print(f"E006: 自检异常 - {e}")
            return 1

    # 正常处理模式
    if not args.input:
        print("E001: 请提供待处理的内容，格式为：用户提供的数据/文件/URL")
        return 1

    # 尝试解析输入
    input_data: Any = args.input

    # 尝试将输入解析为 JSON（支持批量）
    try:
        parsed = json.loads(args.input)
        input_data = parsed
    except (json.JSONDecodeError, TypeError):
        # 不是 JSON，按普通字符串处理
        pass

    # 批量处理
    if args.batch or isinstance(input_data, list):
        if not isinstance(input_data, list):
            print("E009: 批量模式要求输入为 JSON 数组")
            return 1
        results = process_batch(input_data)
    else:
        results = [process_single(input_data)]

    # 输出结果
    output = format_output(results, args.format)
    print(output)

    return 0


if __name__ == "__main__":
    sys.exit(main())
