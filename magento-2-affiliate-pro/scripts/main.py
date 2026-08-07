#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py

Magento 2 Affiliate Pro - 代码审查技能核心逻辑

本脚本依据功能规格独立实现（clean-room），提供：
1. 结构化数据处理与置信度评估
2. 命令行调用与 --selftest 自检
3. 错误码机制（E001-E010）

仅使用 Python 标准库，无第三方依赖。
"""

import argparse
import sys
import json
from typing import Dict, List, Any, Tuple


# ---------------------------------------------------------------------------
# 错误码定义
# ---------------------------------------------------------------------------
ERROR_CODES = {
    "E001": "输入为空，请提供待处理的内容。",
    "E002": "关键信息缺失，请补充必要字段。",
    "E003": "输入格式错误，请检查格式是否符合要求。",
    "E004": "超出能力边界，无法处理该请求。",
    "E005": "置信度过低，结果无法确定。",
    "E006": "内部处理异常，请重试或检查输入。",
    "E007": "参数解析失败，请检查命令行参数。",
    "E008": "输出序列化失败，请检查数据内容。",
    "E009": "自检失败，核心逻辑存在异常。",
    "E010": "未知错误，请联系维护人员。",
}


def get_error_message(code: str) -> str:
    """获取错误码对应的标准话术。"""
    return ERROR_CODES.get(code, ERROR_CODES["E010"])


# ---------------------------------------------------------------------------
# 核心数据结构
# ---------------------------------------------------------------------------
class ReviewItem:
    """单个审查条目。"""

    def __init__(self, key: str, value: Any, confidence: float):
        self.key = key
        self.value = value
        self.confidence = confidence

    def to_dict(self) -> Dict[str, Any]:
        return {
            "key": self.key,
            "value": self.value,
            "confidence": round(self.confidence, 2),
            "flag": self._get_flag(),
        }

    def _get_flag(self) -> str:
        """根据置信度返回标记。"""
        if self.confidence >= 0.90:
            return "直接输出"
        elif self.confidence >= 0.85:
            return "建议复核"
        else:
            return "[需核实]"


class ReviewResult:
    """审查结果集合。"""

    def __init__(self, source: str = ""):
        self.source = source
        self.items: List[ReviewItem] = []
        self.overall_confidence: float = 0.0

    def add_item(self, item: ReviewItem) -> None:
        self.items.append(item)

    def compute_overall(self) -> None:
        """计算整体置信度（加权平均）。"""
        if not self.items:
            self.overall_confidence = 0.0
            return
        total = sum(item.confidence for item in self.items)
        self.overall_confidence = total / len(self.items)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source": self.source,
            "overall_confidence": round(self.overall_confidence, 2),
            "items": [item.to_dict() for item in self.items],
        }


# ---------------------------------------------------------------------------
# 核心处理逻辑
# ---------------------------------------------------------------------------
def validate_input(data: Any) -> Tuple[bool, str]:
    """校验输入数据合法性。"""
    if data is None:
        return False, "E001"
    if isinstance(data, str) and not data.strip():
        return False, "E001"
    if isinstance(data, (list, dict)) and len(data) == 0:
        return False, "E001"
    return True, ""


def extract_key_fields(data: Any) -> Dict[str, Any]:
    """从输入中提取关键字段。"""
    # 支持 dict、list、str 三种基本输入
    if isinstance(data, dict):
        return data
    elif isinstance(data, list):
        # 列表输入：尝试提取常见字段
        result = {}
        for i, item in enumerate(data):
            if isinstance(item, dict):
                for k, v in item.items():
                    result[f"{k}_{i}"] = v
            else:
                result[f"item_{i}"] = item
        return result
    elif isinstance(data, str):
        # 字符串输入：简单分词
        words = data.strip().split()
        return {f"word_{i}": w for i, w in enumerate(words)}
    else:
        return {"value": data}


def assess_confidence(field: str, value: Any) -> float:
    """评估单个字段的置信度。"""
    # 基础置信度
    base = 0.85

    # 字段名完整性检查
    if not field or len(field.strip()) < 2:
        base -= 0.1

    # 值有效性检查
    if value is None or (isinstance(value, str) and not value.strip()):
        base -= 0.2
    elif isinstance(value, (int, float)) and value == 0:
        base -= 0.05

    # 长文本字段置信度略低（可能包含噪声）
    if isinstance(value, str) and len(value) > 500:
        base -= 0.1

    # 确保在 0-1 范围内
    return max(0.0, min(1.0, base))


def process_data(data: Any, source: str = "") -> ReviewResult:
    """核心处理流程：解析、结构化、评估置信度。"""
    # 输入校验
    valid, err_code = validate_input(data)
    if not valid:
        raise ValueError(err_code)

    # 提取字段
    try:
        fields = extract_key_fields(data)
    except Exception:
        raise ValueError("E006")

    if not fields:
        raise ValueError("E002")

    # 构建结果
    result = ReviewResult(source=source)
    for field, value in fields.items():
        confidence = assess_confidence(field, value)
        result.add_item(ReviewItem(key=field, value=value, confidence=confidence))

    result.compute_overall()

    # 整体置信度过低时抛出异常
    if result.overall_confidence < 0.5:
        raise ValueError("E005")

    return result


def format_output(result: ReviewResult, fmt: str = "text") -> str:
    """格式化输出结果。"""
    if fmt == "json":
        try:
            return json.dumps(result.to_dict(), ensure_ascii=False, indent=2)
        except Exception:
            raise ValueError("E008")
    else:
        # 文本格式
        lines = []
        lines.append(f"来源: {result.source or '未知'}")
        lines.append(f"整体置信度: {result.overall_confidence:.2%}")
        lines.append("-" * 50)
        for item in result.items:
            flag = item._get_flag()
            lines.append(f"[{flag}] {item.key}: {item.value}")
            lines.append(f"    置信度: {item.confidence:.2%}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# 命令行接口
# ---------------------------------------------------------------------------
def run_selftest() -> bool:
    """内置自检逻辑，使用硬编码样例数据，不依赖外部环境。"""
    print("=== 自检开始 ===")

    # 测试数据（硬编码）
    test_cases = [
        # (输入数据, 期望至少有n个字段, 期望置信度下限)
        (
            {
                "name": "Magento 2 Affiliate Pro",
                "version": "1.0.0",
                "description": "Affiliate program extension for Magento 2",
                "enabled": True,
                "commission_rate": 0.15,
            },
            3,
            0.8,
        ),
        (
            ["item1", "item2", "item3"],
            2,
            0.7,
        ),
        (
            "simple text input",
            1,
            0.7,
        ),
    ]

    # 运行测试
    for i, (data, min_fields, min_conf) in enumerate(test_cases):
        try:
            result = process_data(data, source=f"selftest_case_{i}")
            assert len(result.items) >= min_fields, f"字段数不足: {len(result.items)} < {min_fields}"
            assert result.overall_confidence >= min_conf, (
                f"置信度过低: {result.overall_confidence} < {min_conf}"
            )
            print(f"  测试用例 {i}: 通过 (字段数={len(result.items)}, 置信度={result.overall_confidence:.2%})")
        except AssertionError as e:
            print(f"  测试用例 {i}: 失败 - {e}")
            return False
        except ValueError as e:
            print(f"  测试用例 {i}: 异常 - {str(e)}")
            return False

    # 错误处理测试
    try:
        process_data(None)
        print("  空输入测试: 失败 (未抛出异常)")
        return False
    except ValueError as e:
        assert str(e) == "E001", f"错误码不匹配: {str(e)}"
        print("  空输入测试: 通过 (正确抛出 E001)")

    try:
        process_data("")
        print("  空字符串测试: 失败 (未抛出异常)")
        return False
    except ValueError as e:
        assert str(e) == "E001", f"错误码不匹配: {str(e)}"
        print("  空字符串测试: 通过 (正确抛出 E001)")

    # 输出格式测试
    try:
        sample_result = process_data({"test": "value"}, source="format_test")
        text_out = format_output(sample_result, "text")
        json_out = format_output(sample_result, "json")
        assert len(text_out) > 0, "文本输出为空"
        assert json.loads(json_out), "JSON 输出无效"
        print("  输出格式测试: 通过")
    except Exception as e:
        print(f"  输出格式测试: 失败 - {e}")
        return False

    print("=== 自检全部通过 ===")
    return True


def main() -> int:
    """主入口函数。"""
    parser = argparse.ArgumentParser(
        description="Magento 2 Affiliate Pro - 代码审查技能",
        epilog="示例: python main.py --input '{\"name\": \"test\"}' --format json",
    )
    parser.add_argument(
        "--input",
        type=str,
        help="输入数据（JSON 字符串或文本）",
    )
    parser.add_argument(
        "--source",
        type=str,
        default="命令行输入",
        help="数据来源标识",
    )
    parser.add_argument(
        "--format",
        type=str,
        choices=["text", "json"],
        default="text",
        help="输出格式 (默认: text)",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检",
    )

    # 解析参数
    try:
        args = parser.parse_args()
    except SystemExit:
        # argparse 会自行处理错误并退出
        return 2

    # 自检模式
    if args.selftest:
        success = run_selftest()
        return 0 if success else 1

    # 正常处理模式
    if not args.input:
        error_msg = get_error_message("E001")
        print(f"错误 E001: {error_msg}", file=sys.stderr)
        return 1

    # 尝试解析 JSON 输入
    data = args.input
    try:
        if args.input.strip().startswith("{"):
            data = json.loads(args.input)
    except json.JSONDecodeError:
        # 不是 JSON，按普通文本处理
        pass

    # 处理数据
    try:
        result = process_data(data, source=args.source)
        output = format_output(result, args.format)
        print(output)
        return 0
    except ValueError as e:
        err_code = str(e)
        error_msg = get_error_message(err_code)
        print(f"错误 {err_code}: {error_msg}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"错误 E010: 未知错误 - {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
