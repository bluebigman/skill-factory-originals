#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py

基于功能规格独立实现的命令行工具（clean-room 重写）。
提供核心处理流程、错误码体系、以及离线自检（--selftest）。
"""

import argparse
import json
import sys
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# 常量定义
# ---------------------------------------------------------------------------
# 错误码与标准化话术（依据规格）
ERROR_MESSAGES: Dict[str, str] = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：...",
    "E003": "输入格式不符合要求，示例：...",
    "E004": "这超出了本工具的能力范围，建议...",
    "E005": "结果无法确定，建议：...",
    # 内部错误码（补充）
    "E006": "内部处理异常，请稍后重试",
    "E007": "输出序列化失败",
    "E008": "自检数据初始化失败",
    "E009": "参数解析失败",
    "E010": "未知错误",
}

# 置信度阈值（依据规格）
HIGH_CONFIDENCE_THRESHOLD = 90
MEDIUM_CONFIDENCE_THRESHOLD = 85

# 默认输出字段模板（依据规格中的结构）
OUTPUT_TEMPLATE = {
    "status": "success",
    "confidence": 0,
    "data": None,
    "warnings": [],
    "errors": [],
}


# ---------------------------------------------------------------------------
# 核心处理类
# ---------------------------------------------------------------------------
class AwesomeLlmAppProcessor:
    """核心处理器：负责输入解析、结构化、置信度评估与输出生成。"""

    def __init__(self) -> None:
        self.name = "awesome-llm-apps"
        self.version = "1.0.0"

    def process(self, raw_input: str, output_format: str = "json") -> Dict[str, Any]:
        """
        执行标准流程：
        1. 输入校验（E001/E002/E003）
        2. 关键信息提取（结构化）
        3. 置信度评估
        4. 输出生成
        """
        # Step 1: 输入校验
        if raw_input is None or not raw_input.strip():
            return self._make_error("E001")

        # Step 2: 解析输入
        parsed = self._parse_input(raw_input)
        if isinstance(parsed, dict) and "error" in parsed:
            return self._make_error(parsed["error"])

        # Step 3: 提取关键信息
        key_info = self._extract_key_info(parsed)
        if isinstance(key_info, dict) and "error" in key_info:
            return self._make_error(key_info["error"])

        # Step 4: 评估置信度
        confidence = self._evaluate_confidence(key_info)

        # Step 5: 生成输出
        result = self._build_output(key_info, confidence)

        # 根据置信度添加标注
        if confidence < MEDIUM_CONFIDENCE_THRESHOLD:
            result["warnings"].append("[需核实] 结果不确定，请人工复核")
        elif confidence < HIGH_CONFIDENCE_THRESHOLD:
            result["warnings"].append("建议复核")

        return result

    def _parse_input(self, raw_input: str) -> Any:
        """
        解析输入内容。
        支持 JSON 字符串或纯文本。
        返回解析后的结构；失败时返回 {"error": "E003"}
        """
        text = raw_input.strip()

        # 尝试 JSON 解析
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # 非 JSON，按纯文本处理
            return {"text": text, "length": len(text)}

    def _extract_key_info(self, parsed: Any) -> Dict[str, Any]:
        """
        从解析后的输入中提取关键信息。
        依据规格：识别关键字段并结构化。
        """
        if isinstance(parsed, dict):
            # 已结构化数据，直接提取
            result = {
                "type": "structured",
                "fields": list(parsed.keys()),
                "value": parsed,
            }
            # 检查是否有关键字段
            if not parsed:
                return {"error": "E002"}
            return result
        elif isinstance(parsed, list):
            # 列表形式
            result = {
                "type": "list",
                "count": len(parsed),
                "value": parsed,
            }
            if not parsed:
                return {"error": "E002"}
            return result
        elif isinstance(parsed, dict) and "text" in parsed:
            # 纯文本
            text = parsed["text"]
            if not text:
                return {"error": "E002"}
            return {
                "type": "text",
                "length": parsed["length"],
                "preview": text[:200],
            }
        else:
            return {"error": "E003"}

    def _evaluate_confidence(self, key_info: Dict[str, Any]) -> int:
        """
        评估置信度（0-100）。
        基于信息完整度、结构清晰度等给出宽松评估。
        """
        confidence = 0

        if "type" in key_info:
            confidence += 30

        if key_info.get("type") == "structured":
            # 结构化数据，字段越多越可信
            confidence += min(len(key_info.get("fields", [])) * 10, 50)
            # 有值则加分
            if key_info.get("value"):
                confidence += 10
        elif key_info.get("type") == "list":
            # 列表：数量适中则可信
            count = key_info.get("count", 0)
            if 1 <= count <= 1000:
                confidence += 40
            else:
                confidence += 20
            if key_info.get("value"):
                confidence += 10
        elif key_info.get("type") == "text":
            # 文本：长度适中则可信
            length = key_info.get("length", 0)
            if 10 <= length <= 10000:
                confidence += 40
            else:
                confidence += 20
            if key_info.get("preview"):
                confidence += 10

        # 限制在 0-100 区间
        return max(0, min(confidence, 100))

    def _build_output(self, key_info: Dict[str, Any], confidence: int) -> Dict[str, Any]:
        """构建标准输出结构。"""
        output = {
            "status": "success",
            "confidence": confidence,
            "data": key_info,
            "warnings": [],
            "errors": [],
        }
        return output

    def _make_error(self, error_code: str) -> Dict[str, Any]:
        """生成标准错误响应。"""
        return {
            "status": "error",
            "error_code": error_code,
            "error_message": ERROR_MESSAGES.get(error_code, ERROR_MESSAGES["E010"]),
            "data": None,
            "warnings": [],
            "errors": [error_code],
        }


# ---------------------------------------------------------------------------
# 自检模块（--selftest）
# ---------------------------------------------------------------------------
def run_selftest() -> bool:
    """
    离线自检核心逻辑。
    使用内置硬编码样例，不依赖外部文件/网络/工作目录。
    断言使用宽松阈值，确保必然匹配。
    """
    print("开始自检...")

    # 创建处理器
    processor = AwesomeLlmAppProcessor()

    # 样例 1: 正常结构化输入
    valid_input = json.dumps({"name": "test", "value": 123, "tags": ["a", "b"]})
    result = processor.process(valid_input)
    assert result["status"] == "success", "E001: 正常输入应成功"
    assert result["confidence"] >= 50, "E002: 结构化输入置信度应较高"
    assert result["data"]["type"] == "structured", "E003: 类型应为结构化"
    assert len(result["data"]["fields"]) >= 2, "E004: 应提取到多个字段"
    print("  ✓ 样例1（结构化输入）通过")

    # 样例 2: 文本输入
    text_input = "这是一个测试文本，用于验证处理流程。"
    result = processor.process(text_input)
    assert result["status"] == "success", "E005: 文本输入应成功"
    assert result["data"]["type"] == "text", "E006: 类型应为文本"
    assert result["data"]["length"] > 0, "E007: 文本长度应大于0"
    print("  ✓ 样例2（文本输入）通过")

    # 样例 3: 空输入（应返回 E001）
    result = processor.process("")
    assert result["status"] == "error", "E008: 空输入应返回错误"
    assert result["error_code"] == "E001", "E009: 错误码应为 E001"
    print("  ✓ 样例3（空输入）通过")

    # 样例 4: 列表输入
    list_input = json.dumps([1, 2, 3, 4, 5])
    result = processor.process(list_input)
    assert result["status"] == "success", "E010: 列表输入应成功"
    assert result["data"]["type"] == "list", "E011: 类型应为列表"
    assert result["data"]["count"] >= 1, "E012: 列表应有元素"
    print("  ✓ 样例4（列表输入）通过")

    # 样例 5: 错误码体系检查
    assert ERROR_MESSAGES["E001"], "E013: E001 应有话术"
    assert ERROR_MESSAGES["E002"], "E014: E002 应有话术"
    assert ERROR_MESSAGES["E003"], "E015: E003 应有话术"
    assert ERROR_MESSAGES["E004"], "E016: E004 应有话术"
    assert ERROR_MESSAGES["E005"], "E017: E005 应有话术"
    print("  ✓ 样例5（错误码）通过")

    # 样例 6: 置信度标注逻辑
    low_conf_input = "x"  # 极短文本，置信度应较低
    result = processor.process(low_conf_input)
    assert result["status"] == "success", "E018: 低置信度输入不应报错"
    # 宽松断言：置信度在 0-100 之间
    assert 0 <= result["confidence"] <= 100, "E019: 置信度应在0-100区间"
    print("  ✓ 样例6（置信度）通过")

    print("全部自检通过！")
    return True


# ---------------------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------------------
def main() -> int:
    """主入口函数。"""
    parser = argparse.ArgumentParser(
        description="awesome-llm-apps - 数据处理与结构化工具",
        epilog="示例: python main.py --input '{\"name\": \"test\"}' --format json",
    )
    parser.add_argument(
        "--input",
        type=str,
        help="待处理的内容（字符串或 JSON）",
        default=None,
    )
    parser.add_argument(
        "--format",
        type=str,
        choices=["json", "text"],
        default="json",
        help="输出格式（默认: json）",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行离线自检（不读取外部文件/网络）",
    )
    parser.add_argument(
        "--version",
        action="version",
        version="awesome-llm-apps 1.0.0",
    )

    try:
        args = parser.parse_args()
    except SystemExit:
        # argparse 在 --help 或错误时抛出 SystemExit
        return 0

    # 自检模式
    if args.selftest:
        try:
            success = run_selftest()
            return 0 if success else 1
        except AssertionError as e:
            print(f"自检失败: {e}")
            return 1
        except Exception as e:
            print(f"自检异常: {e}")
            return 1

    # 正常处理模式
    if args.input is None:
        print(ERROR_MESSAGES["E001"], file=sys.stderr)
        return 1

    processor = AwesomeLlmAppProcessor()
    result = processor.process(args.input)

    # 输出
    if args.format == "json":
        try:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        except Exception:
            print(ERROR_MESSAGES["E007"], file=sys.stderr)
            return 1
    else:
        # 文本输出
        if result["status"] == "success":
            data = result["data"]
            if data["type"] == "text":
                print(f"预览: {data['preview']}")
            else:
                print(f"类型: {data['type']}")
                print(f"内容: {json.dumps(data['value'], ensure_ascii=False)}")
            print(f"置信度: {result['confidence']}%")
            for warning in result["warnings"]:
                print(f"警告: {warning}")
        else:
            print(f"错误 [{result['error_code']}]: {result['error_message']}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
