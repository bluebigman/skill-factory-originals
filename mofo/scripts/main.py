#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
mofo - 未命名工具（微格式解析器）

基于功能规格独立实现（clean-room）。
仅使用 Python 标准库，无第三方依赖。

功能概述：
    将输入内容解析为结构化结果，支持置信度标注、错误码体系。
    提供 --selftest 离线自检模式（硬编码样例，不依赖外部环境）。

错误码：
    E001 输入为空
    E002 关键信息缺失
    E003 输入格式错误
    E004 超出能力边界
    E005 置信度过低
    E006 内部处理异常
    E007 输出序列化失败
    E008 参数解析失败
    E009 自检断言失败
    E010 未知错误
"""

import argparse
import json
import re
import sys
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# 常量定义
# ---------------------------------------------------------------------------

# 置信度阈值
CONFIDENCE_HIGH = 90      # >=90% 直接输出
CONFIDENCE_MEDIUM = 85    # 85%-90% 标注"建议复核"
# <85% 标注"[需核实]"

# 默认输出字段模板
DEFAULT_FIELDS = ["title", "content", "author", "date", "tags"]

# 错误码与话术映射
ERROR_MESSAGES = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：...",
    "E003": "输入格式不符合要求，示例：...",
    "E004": "这超出了本工具的能力范围，建议...",
    "E005": "结果无法确定，建议：...",
    "E006": "内部处理异常，请重试",
    "E007": "输出序列化失败",
    "E008": "参数解析失败",
    "E009": "自检断言失败",
    "E010": "未知错误",
}


# ---------------------------------------------------------------------------
# 核心解析器
# ---------------------------------------------------------------------------

class MofoParser:
    """微格式解析器：将文本输入解析为结构化字典。"""

    # 字段名与正则模式（宽松匹配，不依赖精确格式）
    _FIELD_PATTERNS = {
        "title": re.compile(r"(?:标题|title|TITLE)\s*[:：]\s*(.+)", re.MULTILINE),
        "content": re.compile(r"(?:内容|正文|content|CONTENT)\s*[:：]\s*(.+)", re.MULTILINE | re.DOTALL),
        "author": re.compile(r"(?:作者|author|AUTHOR)\s*[:：]\s*(.+)", re.MULTILINE),
        "date": re.compile(r"(?:日期|时间|date|DATE)\s*[:：]\s*(\d{4}[-/年]\d{1,2}[-/月]\d{1,2}日?)", re.MULTILINE),
        "tags": re.compile(r"(?:标签|关键词|tags|TAGS)\s*[:：]\s*(.+)", re.MULTILINE),
    }

    def __init__(self, input_text: str) -> None:
        """初始化解析器。

        Args:
            input_text: 原始输入文本（可为空字符串）。
        """
        self.input_text = input_text
        self._result: Dict[str, Any] = {}
        self._missing_fields: List[str] = []

    # -- 公开接口 ----------------------------------------------------------

    def parse(self) -> Dict[str, Any]:
        """执行解析，返回结构化结果。

        Returns:
            包含字段值、置信度、缺失信息的字典。
        """
        # 校验输入非空
        if not self.input_text or not self.input_text.strip():
            return self._build_error_result("E001")

        # 提取字段
        extracted = self._extract_fields()

        # 计算置信度
        confidence, missing = self._calculate_confidence(extracted)

        # 组装结果
        result = {
            "data": extracted,
            "confidence": confidence,
            "missing_fields": missing,
            "status": self._determine_status(confidence),
        }

        # 若置信度过低，补充说明
        if confidence < CONFIDENCE_MEDIUM:
            result["note"] = "结果无法确定，建议补充更多信息或人工复核。"

        self._result = result
        return result

    # -- 内部方法 ----------------------------------------------------------

    def _extract_fields(self) -> Dict[str, str]:
        """从输入文本中提取关键字段。

        Returns:
            字段名到值的映射（仅包含成功匹配的字段）。
        """
        extracted: Dict[str, str] = {}
        for field, pattern in self._FIELD_PATTERNS.items():
            match = pattern.search(self.input_text)
            if match:
                value = match.group(1).strip()
                # 内容字段可能跨行，去除多余空白
                if field == "content":
                    value = re.sub(r"\s+", " ", value)
                extracted[field] = value
        return extracted

    def _calculate_confidence(
        self, extracted: Dict[str, str]
    ) -> Tuple[int, List[str]]:
        """基于字段提取情况计算置信度。

        Args:
            extracted: 已提取的字段字典。

        Returns:
            (置信度百分比, 缺失字段列表)。
        """
        total_fields = len(DEFAULT_FIELDS)
        found_fields = [f for f in DEFAULT_FIELDS if f in extracted]
        missing = [f for f in DEFAULT_FIELDS if f not in extracted]

        if total_fields == 0:
            return 0, missing

        # 基础置信度：按字段覆盖率计算
        base_confidence = int(len(found_fields) / total_fields * 100)

        # 内容字段权重更高（若有内容，置信度提升）
        if "content" in extracted:
            base_confidence = min(100, base_confidence + 10)

        # 至少需要 title 或 content 才能有较高置信度
        if not extracted:
            base_confidence = 0
        elif "title" not in extracted and "content" not in extracted:
            base_confidence = min(base_confidence, 30)

        return base_confidence, missing

    def _determine_status(self, confidence: int) -> str:
        """根据置信度确定输出状态。"""
        if confidence >= CONFIDENCE_HIGH:
            return "直接输出"
        elif confidence >= CONFIDENCE_MEDIUM:
            return "建议复核"
        else:
            return "[需核实]"

    def _build_error_result(self, error_code: str) -> Dict[str, Any]:
        """构造错误结果。"""
        return {
            "error": error_code,
            "message": ERROR_MESSAGES.get(error_code, ERROR_MESSAGES["E010"]),
            "data": {},
            "confidence": 0,
            "missing_fields": DEFAULT_FIELDS,
            "status": "错误",
        }


# ---------------------------------------------------------------------------
# 输出格式化
# ---------------------------------------------------------------------------

def format_output(result: Dict[str, Any], output_format: str = "json") -> str:
    """将解析结果格式化为指定格式。

    Args:
        result: 解析结果字典。
        output_format: 输出格式（json / text）。

    Returns:
        格式化后的字符串。

    Raises:
        ValueError: 不支持的输出格式。
    """
    if output_format == "json":
        try:
            return json.dumps(result, ensure_ascii=False, indent=2)
        except (TypeError, ValueError) as exc:
            return json.dumps(
                {"error": "E007", "message": ERROR_MESSAGES["E007"], "detail": str(exc)},
                ensure_ascii=False,
            )
    elif output_format == "text":
        return _format_as_text(result)
    else:
        raise ValueError(f"不支持的输出格式: {output_format}（错误码 E003）")


def _format_as_text(result: Dict[str, Any]) -> str:
    """将结果格式化为纯文本。"""
    lines: List[str] = []

    # 错误信息
    if "error" in result:
        lines.append(f"[错误] {result['error']}: {result['message']}")
        return "\n".join(lines)

    # 状态与置信度
    status = result.get("status", "未知")
    confidence = result.get("confidence", 0)
    lines.append(f"状态: {status} | 置信度: {confidence}%")

    # 数据字段
    data = result.get("data", {})
    if data:
        lines.append("--- 解析结果 ---")
        for key, value in data.items():
            lines.append(f"{key}: {value}")
    else:
        lines.append("（未提取到有效字段）")

    # 缺失字段
    missing = result.get("missing_fields", [])
    if missing:
        lines.append(f"--- 缺失字段: {', '.join(missing)} ---")

    # 补充说明
    if "note" in result:
        lines.append(f"提示: {result['note']}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 批量处理
# ---------------------------------------------------------------------------

def process_batch(inputs: List[str], output_format: str = "json") -> List[Dict[str, Any]]:
    """批量解析多个输入。

    Args:
        inputs: 输入文本列表。
        output_format: 输出格式（仅用于最终格式化）。

    Returns:
        解析结果列表。
    """
    results = []
    for text in inputs:
        parser = MofoParser(text)
        result = parser.parse()
        results.append(result)
    return results


# ---------------------------------------------------------------------------
# 自检（selftest）
# ---------------------------------------------------------------------------

def selftest() -> int:
    """离线自检核心逻辑。

    使用硬编码样例数据，不读文件、不访问网络、不依赖当前目录。

    Returns:
        0 表示全部通过，非 0 表示失败。
    """
    print("开始自检...")

    # 测试样例 1：正常输入
    sample_1 = (
        "标题：测试文档\n"
        "作者：张三\n"
        "日期：2026-01-15\n"
        "内容：这是一段用于测试的正文内容。\n"
        "标签：测试, 文档"
    )
    parser_1 = MofoParser(sample_1)
    result_1 = parser_1.parse()

    # 宽松断言：不应报错，置信度应较高
    assert "error" not in result_1, f"测试1失败：不应有错误，实际 {result_1.get('error')}"
    assert result_1["confidence"] >= 50, f"测试1失败：置信度应 >=50，实际 {result_1['confidence']}"
    assert "title" in result_1["data"], "测试1失败：应提取到 title"
    assert "content" in result_1["data"], "测试1失败：应提取到 content"
    print("测试1（正常输入）通过")

    # 测试样例 2：空输入
    parser_2 = MofoParser("")
    result_2 = parser_2.parse()
    assert "error" in result_2, "测试2失败：空输入应返回错误"
    assert result_2["error"] == "E001", f"测试2失败：错误码应为 E001，实际 {result_2.get('error')}"
    print("测试2（空输入）通过")

    # 测试样例 3：部分字段输入（无标题）
    sample_3 = (
        "作者：李四\n"
        "内容：只有内容和作者，没有标题。"
    )
    parser_3 = MofoParser(sample_3)
    result_3 = parser_3.parse()
    assert "error" not in result_3, f"测试3失败：不应有错误，实际 {result_3.get('error')}"
    assert "title" not in result_3["data"], "测试3失败：不应提取到 title"
    assert result_3["confidence"] < 100, "测试3失败：置信度不应为 100"
    print("测试3（部分字段）通过")

    # 测试样例 4：格式错误输入（无有效字段）
    sample_4 = "随便写的一些内容，没有任何结构化字段。"
    parser_4 = MofoParser(sample_4)
    result_4 = parser_4.parse()
    # 不应报错，但置信度应很低
    assert "error" not in result_4, f"测试4失败：不应有错误，实际 {result_4.get('error')}"
    assert result_4["confidence"] <= 30, f"测试4失败：置信度应 <=30，实际 {result_4['confidence']}"
    print("测试4（无有效字段）通过")

    # 测试样例 5：批量处理
    batch_inputs = [sample_1, sample_3, ""]
    batch_results = process_batch(batch_inputs)
    assert len(batch_results) == 3, f"测试5失败：应有3个结果，实际 {len(batch_results)}"
    assert "error" in batch_results[2], "测试5失败：第3个结果应为错误"
    print("测试5（批量处理）通过")

    # 测试样例 6：输出格式化
    formatted_json = format_output(result_1, "json")
    assert formatted_json.startswith("{"), "测试6失败：JSON 输出应以 { 开头"
    formatted_text = format_output(result_1, "text")
    assert "状态" in formatted_text, "测试6失败：文本输出应包含状态信息"
    try:
        format_output(result_1, "xml")
        assert False, "测试6失败：不支持的格式应抛出异常"
    except ValueError:
        pass  # 预期行为
    print("测试6（输出格式化）通过")

    print("所有自检通过！")
    return 0


# ---------------------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------------------

def main() -> int:
    """命令行主入口。"""
    parser = argparse.ArgumentParser(
        description="mofo - 微格式解析器",
        epilog="示例: python main.py --input '标题：测试' --format json",
    )
    parser.add_argument(
        "--input", "-i", type=str, default="",
        help="输入文本（直接提供内容）",
    )
    parser.add_argument(
        "--file", "-f", type=str,
        help="输入文件路径（从文件读取内容）",
    )
    parser.add_argument(
        "--format", "-o", type=str, choices=["json", "text"], default="json",
        help="输出格式（默认: json）",
    )
    parser.add_argument(
        "--selftest", action="store_true",
        help="运行离线自检",
    )
    parser.add_argument(
        "--batch", action="store_true",
        help="批量模式（配合 --file 使用，每行视为一条输入）",
    )

    # 解析参数
    try:
        args = parser.parse_args()
    except SystemExit as exc:
        # argparse 在出错时会抛出 SystemExit
        if exc.code != 0:
            print(f"参数解析失败（E008）: {ERROR_MESSAGES['E008']}")
            return exc.code
        raise

    # 自检模式
    if args.selftest:
        try:
            return selftest()
        except AssertionError as exc:
            print(f"自检失败（E009）: {exc}")
            return 1
        except Exception as exc:  # noqa: BLE001
            print(f"自检异常（E010）: {exc}")
            return 1

    # 读取输入
    input_text = args.input
    if args.file:
        try:
            with open(args.file, "r", encoding="utf-8") as fh:
                input_text = fh.read()
        except OSError as exc:
            print(f"读取文件失败（E003）: {exc}")
            return 1

    # 批量模式
    if args.batch:
        if not args.file:
            print("批量模式需要 --file 参数（E002）")
            return 1
        lines = [line.strip() for line in input_text.splitlines() if line.strip()]
        if not lines:
            print(f"输入为空（E001）: {ERROR_MESSAGES['E001']}")
            return 1
        results = process_batch(lines, args.format)
        for idx, result in enumerate(results, 1):
            print(f"--- 条目 {idx} ---")
            print(format_output(result, args.format))
        return 0

    # 单条模式
    if not input_text:
        print(f"输入为空（E001）: {ERROR_MESSAGES['E001']}")
        return 1

    parser = MofoParser(input_text)
    result = parser.parse()
    print(format_output(result, args.format))
    return 0


if __name__ == "__main__":
    sys.exit(main())
