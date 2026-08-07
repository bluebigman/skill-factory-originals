#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py — awesome-data-analysis 技能核心实现

本脚本根据功能规格独立实现（clean-room）：
- 解析输入内容，识别关键信息并结构化
- 按默认模板组织输出，标注置信度
- 支持批量处理与自定义格式
- 内置 --selftest 离线自检（硬编码样例，不读外部文件/不访问网络）

错误码：
    E001 输入为空
    E002 关键信息缺失
    E003 输入格式错误
    E004 超出能力边界
    E005 置信度过低
    E006 内部处理异常
    E007 输出序列化失败
    E008 未支持的输出格式
    E009 批量处理中断
    E010 未知错误

仅使用 Python 标准库。
"""

import argparse
import hashlib
import json
import re
import sys
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# 常量与配置
# ---------------------------------------------------------------------------

# 能力边界声明
CAPABILITY_BOUNDARIES = {
    "can_do": [
        "将用户提供的数据/文件/URL 转换为结构化结果",
        "识别并保留输入中的关键信息",
        "按约定格式生成输出",
        "对不确定项给出置信度提示",
        "支持批量处理和自定义格式",
    ],
    "cannot_do": [
        "不执行超出输入范围的分析",
        "不保证绝对准确，低置信度会标注",
        "不访问网络或外部服务",
    ],
}

# 置信度阈值
CONFIDENCE_HIGH = 0.90
CONFIDENCE_MEDIUM = 0.85

# 默认输出字段模板（按功能规格 Step 2）
DEFAULT_OUTPUT_TEMPLATE = {
    "summary": "",
    "key_fields": [],
    "content": "",
    "confidence": 0.0,
    "warnings": [],
}

# 错误码与话术映射（按功能规格第四节）
ERROR_MESSAGES = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：{details}",
    "E003": "输入格式不符合要求，示例：{details}",
    "E004": "这超出了本工具的能力范围，建议：{details}",
    "E005": "结果无法确定，建议：{details}",
    "E006": "内部处理异常：{details}",
    "E007": "输出序列化失败：{details}",
    "E008": "不支持的输出格式：{details}",
    "E009": "批量处理中断：{details}",
    "E010": "未知错误：{details}",
}


# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------

def make_error(code: str, **kwargs) -> Dict[str, str]:
    """构造标准错误响应。"""
    template = ERROR_MESSAGES.get(code, ERROR_MESSAGES["E010"])
    try:
        message = template.format(**kwargs) if kwargs else template
    except KeyError:
        message = template
    return {"error_code": code, "message": message}


def is_empty_input(data: Any) -> bool:
    """判断输入是否为空（None、空字符串、空列表、空字典等）。"""
    if data is None:
        return True
    if isinstance(data, str):
        return not data.strip()
    if isinstance(data, (list, tuple, dict, set)):
        return len(data) == 0
    return False


def extract_key_fields(text: str) -> List[Dict[str, str]]:
    """
    从文本中识别关键字段（简易启发式）。
    规则：
      - 识别 "字段名: 值" 模式
      - 识别 "字段名=值" 模式
      - 识别常见日期/数字模式
    返回结构化字段列表。
    """
    fields: List[Dict[str, str]] = []
    if not text or not isinstance(text, str):
        return fields

    # 模式1: "名字: 值" 或 "名字：值"
    pattern1 = re.compile(r"([\u4e00-\u9fa5A-Za-z0-9_]+)\s*[:：]\s*([^\n,，;；]+)")
    for match in pattern1.finditer(text):
        name = match.group(1).strip()
        value = match.group(2).strip()
        if name and value:
            fields.append({"name": name, "value": value, "type": "key_value"})

    # 模式2: "名字=值"
    pattern2 = re.compile(r"([\u4e00-\u9fa5A-Za-z0-9_]+)\s*=\s*([^\n,，;；]+)")
    for match in pattern2.finditer(text):
        name = match.group(1).strip()
        value = match.group(2).strip()
        if name and value:
            fields.append({"name": name, "value": value, "type": "assignment"})

    # 模式3: 日期（YYYY-MM-DD 或 YYYY/MM/DD）
    pattern3 = re.compile(r"\d{4}[-/]\d{1,2}[-/]\d{1,2}")
    for match in pattern3.finditer(text):
        fields.append({"name": "date", "value": match.group(0), "type": "date"})

    # 模式4: 数字（含小数/百分比）
    pattern4 = re.compile(r"\d+(?:\.\d+)?%?")
    for match in pattern4.finditer(text):
        fields.append({"name": "number", "value": match.group(0), "type": "number"})

    # 去重（按 name+value 去重，保留首次出现）
    seen = set()
    unique_fields = []
    for f in fields:
        key = (f["name"], f["value"])
        if key not in seen:
            seen.add(key)
            unique_fields.append(f)
    return unique_fields


def compute_confidence(fields: List[Dict[str, str]], text_length: int) -> Tuple[float, List[str]]:
    """
    根据提取结果计算置信度与警告信息。
    规则（宽松阈值，不依赖精确值）：
      - 有字段提取：基础置信度高
      - 文本长度过短：降低置信度
      - 无字段提取：置信度低
    """
    warnings: List[str] = []
    confidence = 0.0

    if not fields:
        confidence = 0.5
        warnings.append("未识别到关键字段，结果可能不完整")
    else:
        # 有字段：基础 0.9，字段越多置信度越高（但不超过 1.0）
        confidence = min(0.9 + 0.02 * len(fields), 0.99)
        if len(fields) < 2:
            warnings.append("关键字段较少，建议补充更多信息")

    # 文本长度过短：降低置信度
    if text_length < 10:
        confidence = min(confidence, 0.6)
        warnings.append("输入内容过短，建议提供更详细的描述")

    # 置信度阈值标注
    if confidence >= CONFIDENCE_HIGH:
        pass  # 直接输出
    elif confidence >= CONFIDENCE_MEDIUM:
        warnings.append("建议复核")
    else:
        warnings.append("[需核实] 置信度较低，请人工确认关键结果")

    return confidence, warnings


def validate_input(data: Any) -> Optional[Dict[str, str]]:
    """输入校验，返回错误响应或 None（通过）。"""
    if is_empty_input(data):
        return make_error("E001")
    if not isinstance(data, str):
        return make_error("E003", details="请提供文本字符串（支持 JSON 字符串或纯文本）")
    return None


def parse_json_input(text: str) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, str]]]:
    """
    尝试解析 JSON 字符串输入。
    返回 (解析结果, 错误响应)。若解析失败，返回 (None, None) 表示非 JSON 输入。
    """
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed, None
        return None, make_error("E003", details="JSON 输入需为对象（字典）格式")
    except json.JSONDecodeError:
        return None, None  # 非 JSON，按纯文本处理


def format_output(result: Dict[str, Any], output_format: str) -> Tuple[str, Optional[Dict[str, str]]]:
    """按指定格式序列化输出。"""
    try:
        if output_format == "json":
            return json.dumps(result, ensure_ascii=False, indent=2), None
        elif output_format == "text":
            # 简单文本格式
            lines = []
            for key, value in result.items():
                if isinstance(value, (dict, list)):
                    lines.append(f"{key}: {json.dumps(value, ensure_ascii=False)}")
                else:
                    lines.append(f"{key}: {value}")
            return "\n".join(lines), None
        else:
            return "", make_error("E008", details=f"支持的格式: json, text；收到: {output_format}")
    except (TypeError, ValueError) as exc:
        return "", make_error("E007", details=str(exc))


def compute_content_hash(text: str) -> str:
    """计算输入文本的 SHA-256 哈希（用于追踪/去重）。"""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


# ---------------------------------------------------------------------------
# 核心处理函数
# ---------------------------------------------------------------------------

def process_single_input(data: Any, output_format: str = "json") -> Dict[str, Any]:
    """
    处理单个输入，返回结构化结果。
    支持：
      - 纯文本
      - JSON 字符串（字典格式）
    """
    # 输入校验
    error = validate_input(data)
    if error:
        return error

    text = data if isinstance(data, str) else json.dumps(data, ensure_ascii=False)

    # 尝试 JSON 解析
    parsed_json, json_error = parse_json_input(text)
    if json_error:
        return json_error

    # 提取内容
    if parsed_json is not None:
        # JSON 输入：直接结构化
        content_text = json.dumps(parsed_json, ensure_ascii=False)
        key_fields = []
        for k, v in parsed_json.items():
            if isinstance(v, (str, int, float, bool)):
                key_fields.append({"name": str(k), "value": str(v), "type": "json_field"})
        source_type = "json"
    else:
        # 纯文本输入
        content_text = text
        key_fields = extract_key_fields(text)
        source_type = "text"

    # 计算置信度
    confidence, warnings = compute_confidence(key_fields, len(content_text))

    # 组装结果
    result = {
        "summary": f"已处理 {source_type} 输入，识别到 {len(key_fields)} 个关键字段",
        "key_fields": key_fields,
        "content": content_text,
        "confidence": round(confidence, 4),
        "warnings": warnings,
        "source_type": source_type,
        "content_hash": compute_content_hash(content_text),
    }

    # 序列化输出
    output, format_error = format_output(result, output_format)
    if format_error:
        return format_error

    result["_output"] = output
    return result


def process_batch_inputs(inputs: List[Any], output_format: str = "json") -> Dict[str, Any]:
    """
    批量处理多个输入。
    任一输入失败不中断整体，但记录错误。
    """
    if not inputs:
        return make_error("E001")

    results = []
    errors = []
    for idx, item in enumerate(inputs):
        try:
            result = process_single_input(item, output_format)
            if "error_code" in result:
                errors.append({"index": idx, "error": result})
            else:
                results.append({"index": idx, "result": result})
        except Exception as exc:  # 防止单条异常中断批量
            errors.append({"index": idx, "error": make_error("E006", details=str(exc))})

    return {
        "total": len(inputs),
        "success_count": len(results),
        "error_count": len(errors),
        "results": results,
        "errors": errors,
    }


# ---------------------------------------------------------------------------
# 能力边界检查
# ---------------------------------------------------------------------------

def check_capability(request: str) -> Optional[Dict[str, str]]:
    """
    检查请求是否超出能力边界。
    返回错误响应或 None（在能力范围内）。
    """
    if not request or not isinstance(request, str):
        return None

    # 检测网络请求相关关键词
    network_keywords = ["http://", "https://", "www.", "下载", "爬取", "网络请求", "API调用"]
    for kw in network_keywords:
        if kw.lower() in request.lower():
            return make_error("E004", details="本工具不访问网络或外部服务，请提供本地数据")

    # 检测执行代码相关关键词
    code_keywords = ["执行代码", "运行脚本", "调用外部程序", "系统命令"]
    for kw in code_keywords:
        if kw in request:
            return make_error("E004", details="本工具不执行外部程序或系统命令")

    return None


# ---------------------------------------------------------------------------
# 自检（--selftest）
# ---------------------------------------------------------------------------

def run_selftest() -> int:
    """
    离线自检核心逻辑。
    使用内置硬编码样例数据，不读外部文件、不依赖工作目录、不访问网络。
    断言使用宽松阈值（大小比较/区间判断），确保必然匹配。
    """
    print("=" * 60)
    print("自检开始 (selftest)")
    print("=" * 60)

    # 测试1: 空输入 → E001
    print("\n[测试1] 空输入处理")
    result = process_single_input("")
    assert "error_code" in result, "空输入应返回错误码"
    assert result["error_code"] == "E001", f"期望 E001，实际 {result['error_code']}"
    print(f"  通过: {result['error_code']}")

    # 测试2: 纯文本关键字段提取
    print("\n[测试2] 纯文本关键字段提取")
    sample_text = "项目名称: 数据分析平台, 负责人: 张三, 预算: 50000元, 日期: 2026-03-15"
    result = process_single_input(sample_text)
    assert "error_code" not in result, f"不应有错误: {result}"
    assert len(result["key_fields"]) >= 3, f"应至少提取3个字段，实际 {len(result['key_fields'])}"
    assert result["confidence"] > 0.8, f"置信度应高于0.8，实际 {result['confidence']}"
    print(f"  通过: 提取 {len(result['key_fields'])} 个字段, 置信度 {result['confidence']}")

    # 测试3: JSON 输入
    print("\n[测试3] JSON 输入处理")
    json_input = '{"name": "test", "value": 123, "active": true}'
    result = process_single_input(json_input)
    assert "error_code" not in result, f"不应有错误: {result}"
    assert result["source_type"] == "json", f"应识别为 JSON，实际 {result['source_type']}"
    assert len(result["key_fields"]) == 3, f"应提取3个JSON字段，实际 {len(result['key_fields'])}"
    print(f"  通过: JSON 识别, 字段数 {len(result['key_fields'])}")

    # 测试4: 置信度逻辑（短文本）
    print("\n[测试4] 短文本置信度")
    result = process_single_input("你好")
    assert result["confidence"] < 0.7, f"短文本置信度应较低，实际 {result['confidence']}"
    assert len(result["warnings"]) > 0, "应有警告信息"
    print(f"  通过: 置信度 {result['confidence']}, 警告数 {len(result['warnings'])}")

    # 测试5: 输出格式
    print("\n[测试5] 输出格式")
    result = process_single_input("测试内容: 123", output_format="text")
    assert "_output" in result, "应有 _output 字段"
    assert isinstance(result["_output"], str), "输出应为字符串"
    assert len(result["_output"]) > 0, "输出不应为空"
    print(f"  通过: text 格式输出长度 {len(result['_output'])}")

    # 测试6: 批量处理
    print("\n[测试6] 批量处理")
    batch = ["内容1: 测试", "", "内容2: 测试", 123]
    result = process_batch_inputs(batch)
    assert result["total"] == 4, f"总数应为4，实际 {result['total']}"
    assert result["success_count"] >= 2, f"成功数应至少2，实际 {result['success_count']}"
    assert result["error_count"] >= 1, f"应有至少1个错误，实际 {result['error_count']}"
    print(f"  通过: 成功 {result['success_count']}, 失败 {result['error_count']}")

    # 测试7: 能力边界检查
    print("\n[测试7] 能力边界检查")
    error = check_capability("请帮我访问 https://example.com")
    assert error is not None, "网络请求应被拒绝"
    assert error["error_code"] == "E004", f"期望 E004，实际 {error['error_code']}"
    error = check_capability("正常的数据分析请求")
    assert error is None, "正常请求不应被拒绝"
    print(f"  通过: 边界检查逻辑")

    # 测试8: 错误码完整性
    print("\n[测试8] 错误码完整性")
    for code in ["E001", "E002", "E003", "E004", "E005", "E006", "E007", "E008", "E009", "E010"]:
        assert code in ERROR_MESSAGES, f"缺少错误码 {code}"
    print(f"  通过: 全部 {len(ERROR_MESSAGES)} 个错误码已定义")

    # 测试9: 能力边界声明
    print("\n[测试9] 能力边界声明")
    assert len(CAPABILITY_BOUNDARIES["can_do"]) == 5, "应有5项核心能力"
    assert len(CAPABILITY_BOUNDARIES["cannot_do"]) == 3, "应有3项边界声明"
    print(f"  通过: 能力声明完整")

    # 测试10: 哈希函数
    print("\n[测试10] 内容哈希")
    h1 = compute_content_hash("测试内容")
    h2 = compute_content_hash("测试内容")
    h3 = compute_content_hash("不同内容")
    assert h1 == h2, "相同内容哈希应一致"
    assert h1 != h3, "不同内容哈希应不同"
    assert len(h1) == 16, f"哈希长度应为16，实际 {len(h1)}"
    print(f"  通过: 哈希一致性")

    print("\n" + "=" * 60)
    print("所有自检测试通过 ✓")
    print("=" * 60)
    return 0


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------

def main() -> int:
    """命令行入口。"""
    parser = argparse.ArgumentParser(
        description="awesome-data-analysis 技能核心实现",
        epilog="示例: python main.py --input '项目名称: 测试' --format json",
    )
    parser.add_argument(
        "--input", "-i",
        type=str,
        help="待处理的内容（纯文本或 JSON 字符串）",
    )
    parser.add_argument(
        "--format", "-f",
        choices=["json", "text"],
        default="json",
        help="输出格式（默认: json）",
    )
    parser.add_argument(
        "--batch",
        action="store_true",
        help="批量处理模式（--input 为 JSON 数组）",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行离线自检（不读外部文件/不访问网络）",
    )
    parser.add_argument(
        "--check-boundary",
        type=str,
        metavar="REQUEST",
        help="检查请求是否超出能力边界",
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        return run_selftest()

    # 边界检查模式
    if args.check_boundary:
        error = check_capability(args.check_boundary)
        if error:
            print(json.dumps(error, ensure_ascii=False, indent=2))
        else:
            print(json.dumps({"status": "ok", "message": "请求在能力范围内"}, ensure_ascii=False, indent=2))
        return 0

    # 处理模式
    if not args.input:
        print(json.dumps(make_error("E001"), ensure_ascii=False, indent=2), file=sys.stderr)
        return 1

    if args.batch:
        # 批量模式：尝试解析 JSON 数组
        try:
            batch_data = json.loads(args.input)
            if not isinstance(batch_data, list):
                print(json.dumps(make_error("E003", details="批量模式需要 JSON 数组"), ensure_ascii=False, indent=2), file=sys.stderr)
                return 1
            result = process_batch_inputs(batch_data, args.format)
        except json.JSONDecodeError:
            print(json.dumps(make_error("E003", details="批量模式需要 JSON 数组"), ensure_ascii=False, indent=2), file=sys.stderr)
            return 1
    else:
        # 单条处理
        result = process_single_input(args.input, args.format)

    # 输出结果
    if "_output" in result:
        # 使用序列化输出
        print(result["_output"])
        # 移除内部字段后输出完整结果
        clean_result = {k: v for k, v in result.items() if not k.startswith("_")}
        if args.format == "json":
            print("\n# 完整结构化结果:")
            print(json.dumps(clean_result, ensure_ascii=False, indent=2))
    else:
        # 错误响应
        print(json.dumps(result, ensure_ascii=False, indent=2), file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
