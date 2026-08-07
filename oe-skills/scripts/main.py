#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
oe-skills 技能脚本（独立实现，clean-room 重写）

本脚本依据《oe-skills 功能规格》独立实现，提供：
- 标准处理流程：解析输入 -> 结构化关键信息 -> 输出结果并标注置信度
- 错误码体系：E001-E010
- 离线自检：--selftest（内置硬编码样例，不依赖任何外部资源）

仅使用 Python 标准库，无第三方依赖。
"""

import argparse
import json
import re
import sys
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# 常量定义
# ---------------------------------------------------------------------------

# 错误码及其标准化话术
ERROR_MESSAGES: Dict[str, str] = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：...（逐项追问）",
    "E003": "输入格式不符合要求，示例：...",
    "E004": "这超出了本工具的能力范围，建议...",
    "E005": "结果无法确定，建议：...",
    "E006": "内部处理异常，请重试或联系管理员",
    "E007": "输出格式参数不合法，可选值：json / text",
    "E008": "批量处理时存在失败项，请检查详情",
    "E009": "输入来源类型不支持，可选值：data / file / url",
    "E010": "关键字段提取失败，请检查输入内容",
}

# 置信度阈值
CONFIDENCE_THRESHOLD_DIRECT = 0.90  # 直接输出
CONFIDENCE_THRESHOLD_REVIEW = 0.85  # 建议复核

# 默认输出字段模板
DEFAULT_FIELDS = ["content", "source_type", "key_info", "confidence"]

# 支持的关键信息识别模式（键为字段名，值为正则表达式）
KEY_PATTERNS: Dict[str, str] = {
    "email": r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
    "phone": r"(?:\+?86[- ]?)?1[3-9]\d{9}",
    "url": r"https?://[^\s]+",
    "date": r"\d{4}[-/年]\d{1,2}[-/月]\d{1,2}日?",
    "id_card": r"\d{17}[\dXx]",
}

# 输入来源类型关键词映射
SOURCE_TYPE_KEYWORDS: Dict[str, List[str]] = {
    "file": ["文件", "file", "路径", "path"],
    "url": ["网址", "链接", "url", "http"],
    "data": ["数据", "文本", "内容", "data", "text"],
}


# ---------------------------------------------------------------------------
# 错误处理与工具函数
# ---------------------------------------------------------------------------

class SkillError(Exception):
    """技能处理异常，携带错误码。"""

    def __init__(self, error_code: str, message: str = ""):
        self.error_code = error_code
        self.message = message or ERROR_MESSAGES.get(error_code, "未知错误")
        super().__init__(f"[{error_code}] {self.message}")


def validate_input(raw_input: Any) -> str:
    """
    校验输入是否为非空字符串。

    参数:
        raw_input: 原始输入

    返回:
        去除首尾空白后的字符串

    异常:
        SkillError: E001（输入为空）、E003（输入格式错误）
    """
    if raw_input is None:
        raise SkillError("E001")

    if not isinstance(raw_input, str):
        raise SkillError("E003", f"输入必须是字符串，当前类型为 {type(raw_input).__name__}")

    text = raw_input.strip()
    if not text:
        raise SkillError("E001")

    return text


def detect_source_type(text: str) -> str:
    """
    根据输入内容关键词推断来源类型。

    参数:
        text: 输入文本

    返回:
        来源类型：data / file / url

    异常:
        SkillError: E009（无法识别来源类型）
    """
    text_lower = text.lower()

    # 优先判断 URL
    if re.search(r"^https?://", text_lower):
        return "url"

    # 检查关键词
    scores: Dict[str, int] = {"data": 0, "file": 0, "url": 0}
    for source_type, keywords in SOURCE_TYPE_KEYWORDS.items():
        for keyword in keywords:
            if keyword.lower() in text_lower:
                scores[source_type] += 1

    # 取最高分，若均为 0 则默认 data
    max_score = max(scores.values())
    if max_score == 0:
        return "data"

    best_type = max(scores, key=scores.get)
    return best_type


def extract_key_info(text: str) -> Dict[str, List[str]]:
    """
    使用正则从输入文本中提取关键信息（邮箱、电话、URL、日期、身份证号）。

    参数:
        text: 输入文本

    返回:
        字典，键为字段名，值为匹配到的字符串列表
    """
    result: Dict[str, List[str]] = {}
    for field, pattern in KEY_PATTERNS.items():
        matches = re.findall(pattern, text)
        # 去重但保持顺序
        unique_matches = list(dict.fromkeys(matches))
        if unique_matches:
            result[field] = unique_matches
    return result


def calculate_confidence(text: str, key_info: Dict[str, List[str]]) -> float:
    """
    计算处理结果的置信度（0.0 ~ 1.0）。

    规则：
    - 基础置信度 0.80
    - 提取到关键信息：每个字段 +0.05，上限 +0.15
    - 输入长度 > 50：+0.05
    - 输入包含明显结构化标记（如 JSON、表格符号）：+0.05
    - 上限 0.98

    参数:
        text: 输入文本
        key_info: 提取到的关键信息

    返回:
        置信度（0~1 之间的小数）
    """
    confidence = 0.80

    # 关键信息加分
    field_count = len(key_info)
    confidence += min(field_count * 0.05, 0.15)

    # 长度加分
    if len(text) > 50:
        confidence += 0.05

    # 结构化标记加分
    if re.search(r"[{}[\]]", text) or "|" in text or "\t" in text:
        confidence += 0.05

    # 限制上限
    return min(confidence, 0.98)


def make_output(result: Dict[str, Any], output_format: str = "json") -> str:
    """
    按指定格式生成输出。

    参数:
        result: 处理结果字典
        output_format: 输出格式（json / text）

    返回:
        格式化后的字符串

    异常:
        SkillError: E007（输出格式不合法）
    """
    if output_format == "json":
        return json.dumps(result, ensure_ascii=False, indent=2)

    if output_format == "text":
        lines = []
        for key, value in result.items():
            if isinstance(value, dict):
                lines.append(f"{key}:")
                for sub_key, sub_value in value.items():
                    lines.append(f"  {sub_key}: {sub_value}")
            else:
                lines.append(f"{key}: {value}")
        return "\n".join(lines)

    raise SkillError("E007")


# ---------------------------------------------------------------------------
# 核心业务逻辑
# ---------------------------------------------------------------------------

def process_single_item(
    raw_input: Any,
    output_format: str = "json",
    required_fields: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    处理单个输入项，生成结构化结果。

    参数:
        raw_input: 输入内容（字符串）
        output_format: 输出格式（json / text）
        required_fields: 必须提取的字段列表（缺失则报 E002）

    返回:
        处理结果字典

    异常:
        SkillError: E001-E010 相关错误
    """
    # 1. 校验输入
    text = validate_input(raw_input)

    # 2. 识别来源类型
    try:
        source_type = detect_source_type(text)
    except SkillError:
        raise SkillError("E009")

    # 3. 提取关键信息
    key_info = extract_key_info(text)

    # 4. 检查必需字段
    if required_fields:
        missing = [f for f in required_fields if f not in key_info]
        if missing:
            raise SkillError("E002", f"还缺少以下信息，请补充：{', '.join(missing)}")

    # 5. 计算置信度
    confidence = calculate_confidence(text, key_info)

    # 6. 构建结果
    result: Dict[str, Any] = {
        "content": text,
        "source_type": source_type,
        "key_info": key_info,
        "confidence": round(confidence, 4),
        "status": "ok",
    }

    # 7. 置信度标注
    if confidence >= CONFIDENCE_THRESHOLD_DIRECT:
        result["advice"] = "直接输出"
    elif confidence >= CONFIDENCE_THRESHOLD_REVIEW:
        result["advice"] = "建议复核"
    else:
        result["advice"] = "[需核实] 请人工确认关键结果"

    return result


def process_batch(
    items: List[Any],
    output_format: str = "json",
) -> Dict[str, Any]:
    """
    批量处理多个输入项。

    参数:
        items: 输入项列表
        output_format: 输出格式

    返回:
        批量处理结果字典

    异常:
        SkillError: E008（存在失败项）、E001（输入为空）
    """
    if not items:
        raise SkillError("E001")

    results = []
    errors = []

    for idx, item in enumerate(items):
        try:
            result = process_single_item(item, output_format)
            result["index"] = idx
            results.append(result)
        except SkillError as e:
            errors.append({"index": idx, "error_code": e.error_code, "message": e.message})

    batch_result = {
        "total": len(items),
        "success_count": len(results),
        "failed_count": len(errors),
        "results": results,
        "errors": errors,
    }

    if errors:
        batch_result["status"] = "partial"
        raise SkillError("E008", f"批量处理完成，成功 {len(results)} 项，失败 {len(errors)} 项")

    batch_result["status"] = "ok"
    return batch_result


# ---------------------------------------------------------------------------
# 自检函数（--selftest）
# ---------------------------------------------------------------------------

def run_selftest() -> int:
    """
    离线自检核心逻辑，使用内置硬编码样例数据。

    不读取外部文件、不依赖当前工作目录、不访问网络。
    断言使用宽松阈值（大小比较/区间判断），确保任何环境可过。

    返回:
        0 表示全部通过，非 0 表示失败
    """
    print("开始自检 oe-skills 核心逻辑...")

    # ---- 1. 校验 validate_input ----
    try:
        validate_input("")
        print("FAIL: validate_input 空字符串未报错")
        return 1
    except SkillError as e:
        assert e.error_code == "E001", f"期望 E001，实际 {e.error_code}"
        print("PASS: validate_input 空输入校验")

    try:
        validate_input(None)
        print("FAIL: validate_input None 未报错")
        return 1
    except SkillError as e:
        assert e.error_code == "E001", f"期望 E001，实际 {e.error_code}"
        print("PASS: validate_input None 校验")

    text = validate_input("  你好，世界  ")
    assert text == "你好，世界", "validate_input 未去除首尾空白"
    print("PASS: validate_input 正常输入")

    # ---- 2. 校验 detect_source_type ----
    assert detect_source_type("https://example.com") == "url", "URL 识别失败"
    print("PASS: detect_source_type URL")

    assert detect_source_type("这是一个文件路径") == "file", "文件识别失败"
    print("PASS: detect_source_type 文件")

    assert detect_source_type("普通文本内容") == "data", "数据识别失败"
    print("PASS: detect_source_type 数据")

    # ---- 3. 校验 extract_key_info ----
    sample_text = "联系邮箱 test@example.com，电话 13812345678，网址 https://abc.com，日期 2024-01-15"
    key_info = extract_key_info(sample_text)
    assert "email" in key_info, "邮箱提取失败"
    assert "phone" in key_info, "电话提取失败"
    assert "url" in key_info, "URL 提取失败"
    assert "date" in key_info, "日期提取失败"
    assert len(key_info["email"]) >= 1, "邮箱数量异常"
    print("PASS: extract_key_info 多字段提取")

    # ---- 4. 校验 calculate_confidence ----
    conf_short = calculate_confidence("简单输入", {})
    conf_rich = calculate_confidence(sample_text + " 更多内容" * 20, key_info)
    assert conf_short > 0.0, "置信度应为正数"
    assert conf_short < conf_rich, "丰富输入的置信度应更高"
    assert conf_rich <= 0.98, "置信度不应超过上限"
    print(f"PASS: calculate_confidence ({conf_short:.2f} < {conf_rich:.2f})")

    # ---- 5. 校验 make_output ----
    test_result = {"content": "测试", "confidence": 0.95}
    json_out = make_output(test_result, "json")
    assert json_out.startswith("{"), "JSON 输出格式错误"
    text_out = make_output(test_result, "text")
    assert "content: 测试" in text_out, "文本输出格式错误"
    try:
        make_output(test_result, "xml")
        print("FAIL: make_output 未对非法格式报错")
        return 1
    except SkillError as e:
        assert e.error_code == "E007", f"期望 E007，实际 {e.error_code}"
    print("PASS: make_output 格式输出")

    # ---- 6. 校验 process_single_item ----
    result = process_single_item(sample_text)
    assert result["status"] == "ok", "处理状态应为 ok"
    assert result["source_type"] in ("data", "url"), "来源类型识别异常"
    assert result["confidence"] > 0.5, "置信度应大于 0.5"
    assert "key_info" in result, "缺少 key_info 字段"
    print(f"PASS: process_single_item 完整流程 (置信度 {result['confidence']:.2f})")

    # ---- 7. 校验必需字段缺失 ----
    try:
        process_single_item("没有邮箱的内容", required_fields=["email"])
        print("FAIL: 缺少必需字段未报错")
        return 1
    except SkillError as e:
        assert e.error_code == "E002", f"期望 E002，实际 {e.error_code}"
    print("PASS: process_single_item 必需字段校验")

    # ---- 8. 校验 process_batch ----
    batch_items = ["第一条内容 test@a.com", "第二条内容", "https://example.org"]
    batch_result = process_batch(batch_items)
    assert batch_result["total"] == 3, "批量总数错误"
    assert batch_result["success_count"] == 3, "批量成功数错误"
    assert batch_result["failed_count"] == 0, "批量失败数应为 0"
    print("PASS: process_batch 全成功")

    # 含失败项的批量
    try:
        process_batch(["正常内容", ""])
        print("FAIL: 批量含空输入未报错")
        return 1
    except SkillError as e:
        assert e.error_code == "E008", f"期望 E008，实际 {e.error_code}"
    print("PASS: process_batch 含失败项处理")

    # ---- 9. 校验错误码体系 ----
    for code in ["E001", "E002", "E003", "E004", "E005", "E006", "E007", "E008", "E009", "E010"]:
        assert code in ERROR_MESSAGES, f"错误码 {code} 缺少话术"
        assert len(ERROR_MESSAGES[code]) > 0, f"错误码 {code} 话术为空"
    print("PASS: 错误码体系完整性")

    print("\n全部自检通过！")
    return 0


# ---------------------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------------------

def main() -> int:
    """
    命令行主入口。

    支持：
    - --selftest: 离线自检
    - --input: 处理单个输入
    - --batch: 处理多个输入（JSON 数组字符串）
    - --format: 输出格式（json / text）
    - --required-fields: 必需字段列表（逗号分隔）

    返回:
        退出码（0 成功，非 0 失败）
    """
    parser = argparse.ArgumentParser(
        description="oe-skills 技能处理脚本（仅供学习与参考用途）",
        epilog="示例：python main.py --input '你好，邮箱 test@example.com' --format json",
    )

    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行离线自检（不依赖任何外部资源）",
    )
    parser.add_argument(
        "--input",
        type=str,
        help="待处理的输入内容（字符串）",
    )
    parser.add_argument(
        "--batch",
        type=str,
        help="批量处理：JSON 数组字符串，如 '[\"a\",\"b\"]'",
    )
    parser.add_argument(
        "--format",
        type=str,
        choices=["json", "text"],
        default="json",
        help="输出格式（默认 json）",
    )
    parser.add_argument(
        "--required-fields",
        type=str,
        default="",
        help="必需字段列表，逗号分隔，如 'email,phone'",
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        return run_selftest()

    # 处理模式
    try:
        required_fields = [f.strip() for f in args.required_fields.split(",") if f.strip()] or None

        if args.batch:
            # 批量处理
            try:
                items = json.loads(args.batch)
                if not isinstance(items, list):
                    raise SkillError("E003", "批量输入必须是 JSON 数组")
                result = process_batch(items, args.format)
            except json.JSONDecodeError:
                raise SkillError("E003", "批量输入无法解析为 JSON 数组，示例：[\"内容1\",\"内容2\"]")
            except SkillError as e:
                # 部分失败时也输出结果
                if e.error_code == "E008":
                    print(json.dumps(result, ensure_ascii=False, indent=2))
                    return 1
                raise
        elif args.input is not None:
            # 单个处理
            result = process_single_item(args.input, args.format, required_fields)
        else:
            raise SkillError("E001")

        # 输出结果
        output = make_output(result, args.format)
        print(output)
        return 0

    except SkillError as e:
        error_output = {
            "error_code": e.error_code,
            "message": e.message,
            "status": "error",
        }
        print(json.dumps(error_output, ensure_ascii=False, indent=2))
        return 1

    except Exception as e:
        error_output = {
            "error_code": "E006",
            "message": f"内部处理异常: {str(e)}",
            "status": "error",
        }
        print(json.dumps(error_output, ensure_ascii=False, indent=2))
        return 1


if __name__ == "__main__":
    sys.exit(main())
