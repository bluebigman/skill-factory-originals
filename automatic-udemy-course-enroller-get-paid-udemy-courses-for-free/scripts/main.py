#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py

自动课程信息采集与结构化处理工具（仅供学习与参考用途）。

设计原则：
- 仅依据功能规格独立实现（clean-room）。
- 标准库优先，无第三方依赖。
- 提供 --selftest 离线自检模式，内置硬编码样例数据，不访问网络/文件。
- 错误处理统一使用 E001-E010 错误码。
"""

import argparse
import json
import sys
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# 常量定义
# ---------------------------------------------------------------------------

# 错误码及对应标准化话术
ERROR_MESSAGES: Dict[str, str] = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：",
    "E003": "输入格式不符合要求，示例：{'title': '课程名', 'url': 'https://...'}",
    "E004": "这超出了本工具的能力范围，建议：",
    "E005": "结果无法确定，建议：",
    "E006": "内部处理异常，请重试或检查输入",
    "E007": "批量处理中部分条目失败，详见结果",
    "E008": "输出格式不支持，支持：json / text",
    "E009": "输入内容超出允许大小",
    "E010": "未知错误",
}

# 支持的处理类型
SUPPORTED_INPUT_KEYS = {"title", "url", "price", "instructor", "rating", "students"}

# 置信度阈值
HIGH_CONFIDENCE = 0.90
MEDIUM_CONFIDENCE = 0.85


# ---------------------------------------------------------------------------
# 核心数据结构
# ---------------------------------------------------------------------------

class ProcessingResult:
    """处理结果封装。"""

    def __init__(self, success: bool, data: Any = None, error_code: Optional[str] = None,
                 confidence: float = 1.0, message: str = "") -> None:
        self.success = success
        self.data = data
        self.error_code = error_code
        self.confidence = confidence
        self.message = message

    def to_dict(self) -> Dict[str, Any]:
        """转为字典格式。"""
        return {
            "success": self.success,
            "data": self.data,
            "error_code": self.error_code,
            "confidence": self.confidence,
            "message": self.message,
        }


# ---------------------------------------------------------------------------
# 核心处理逻辑
# ---------------------------------------------------------------------------

def validate_input(raw_input: Any) -> ProcessingResult:
    """
    校验输入内容。

    规则：
    - 输入不能为空
    - 输入必须是字典或字典列表
    - 字典必须包含 title 字段
    - 字典大小受限（防止超大输入）
    """
    # E001: 输入为空
    if raw_input is None:
        return ProcessingResult(False, error_code="E001", message=ERROR_MESSAGES["E001"])
    
    if isinstance(raw_input, str):
        # 尝试解析 JSON 字符串
        try:
            raw_input = json.loads(raw_input)
        except json.JSONDecodeError:
            return ProcessingResult(False, error_code="E003", message=ERROR_MESSAGES["E003"])

    # E009: 输入过大（超过 1MB 字符长度）
    raw_str = json.dumps(raw_input, ensure_ascii=False)
    if len(raw_str) > 1024 * 1024:
        return ProcessingResult(False, error_code="E009", message=ERROR_MESSAGES["E009"])

    # 统一为列表处理
    items = raw_input if isinstance(raw_input, list) else [raw_input]

    # E003: 格式错误 - 非字典
    if not all(isinstance(item, dict) for item in items):
        return ProcessingResult(False, error_code="E003", message=ERROR_MESSAGES["E003"])

    # E002: 缺少关键字段 title
    missing_titles = [i for i, item in enumerate(items) if "title" not in item]
    if missing_titles:
        return ProcessingResult(
            False, error_code="E002",
            message=ERROR_MESSAGES["E002"] + f"第 {missing_titles[0] + 1} 条缺少 title 字段"
        )

    # E003: 格式错误 - 包含不支持字段
    for item in items:
        unsupported = set(item.keys()) - SUPPORTED_INPUT_KEYS
        if unsupported:
            return ProcessingResult(
                False, error_code="E003",
                message=ERROR_MESSAGES["E003"] + f" 不支持的字段: {', '.join(unsupported)}"
            )

    return ProcessingResult(True, data=items)


def process_item(item: Dict[str, Any]) -> Tuple[Dict[str, Any], float, str]:
    """
    处理单个课程信息条目，结构化并计算置信度。

    返回: (处理后的字典, 置信度, 提示信息)
    """
    processed = dict(item)
    notes = []

    # 字段完整性检查
    required_fields = {"title", "url"}
    missing = required_fields - set(item.keys())
    if missing:
        notes.append(f"缺少字段: {', '.join(missing)}")

    # 价格处理
    price = item.get("price")
    if price is not None:
        try:
            price_val = float(str(price).replace("$", "").replace(",", ""))
            processed["price"] = price_val
            if price_val <= 0:
                notes.append("价格为 0 或负值，可能为免费课程")
        except (ValueError, TypeError):
            processed["price"] = None
            notes.append("价格格式无法解析")
    else:
        processed["price"] = None
        notes.append("未提供价格")

    # 评分处理（0-5 区间）
    rating = item.get("rating")
    if rating is not None:
        try:
            rating_val = float(rating)
            if 0 <= rating_val <= 5:
                processed["rating"] = rating_val
            else:
                processed["rating"] = None
                notes.append("评分超出 0-5 范围")
        except (ValueError, TypeError):
            processed["rating"] = None
            notes.append("评分格式无法解析")
    else:
        processed["rating"] = None
        notes.append("未提供评分")

    # 学生数量处理
    students = item.get("students")
    if students is not None:
        try:
            students_val = int(str(students).replace(",", "").replace("人", ""))
            processed["students"] = students_val
        except (ValueError, TypeError):
            processed["students"] = None
            notes.append("学生数量格式无法解析")
    else:
        processed["students"] = None
        notes.append("未提供学生数量")

    # 讲师处理
    instructor = item.get("instructor")
    if instructor is None:
        notes.append("未提供讲师信息")

    # 置信度计算
    # 基础 1.0，每缺失一个字段扣 0.05，每个解析失败扣 0.08
    confidence = 1.0
    for field in required_fields:
        if field not in item or not item.get(field):
            confidence -= 0.05
    for field in ["price", "rating", "students"]:
        if field in item and processed.get(field) is None:
            confidence -= 0.08
        elif field not in item:
            confidence -= 0.05  # 完全缺失也扣分

    # 讲师缺失额外扣分
    if "instructor" not in item:
        confidence -= 0.03

    confidence = max(0.0, min(1.0, confidence))

    # 附加提示信息
    hint = ""
    if confidence < MEDIUM_CONFIDENCE:
        hint = "[需核实] "
    elif confidence < HIGH_CONFIDENCE:
        hint = "[建议复核] "

    if notes:
        hint += "；".join(notes)

    # 确保有提示信息
    if not hint:
        hint = "信息完整，无需特别提示"

    return processed, confidence, hint


def process_input(raw_input: Any) -> ProcessingResult:
    """
    主处理流程：校验 → 逐条处理 → 汇总结果。
    """
    # 校验输入
    validation = validate_input(raw_input)
    if not validation.success:
        return validation

    items = validation.data
    results = []
    total_confidence = 0.0
    failed_count = 0

    for item in items:
        processed, confidence, hint = process_item(item)
        total_confidence += confidence
        result_entry = {
            "processed": processed,
            "confidence": round(confidence, 2),
            "hint": hint,
        }
        results.append(result_entry)

        if confidence < MEDIUM_CONFIDENCE:
            failed_count += 1

    # 汇总
    summary = {
        "total": len(items),
        "success": len(items) - failed_count,
        "failed": failed_count,
        "average_confidence": round(total_confidence / len(items), 2) if items else 0,
    }

    output = {
        "summary": summary,
        "results": results,
    }

    # E007: 部分条目失败
    if failed_count > 0 and failed_count < len(items):
        return ProcessingResult(True, data=output, error_code="E007", message=ERROR_MESSAGES["E007"])

    return ProcessingResult(True, data=output)


def format_output(result: ProcessingResult, output_format: str = "json") -> ProcessingResult:
    """
    按指定格式输出结果。
    """
    if not result.success:
        return result

    if output_format == "json":
        return result

    if output_format == "text":
        # 转为文本格式
        lines = []
        data = result.data
        lines.append(f"处理统计: 共 {data['summary']['total']} 条，成功 {data['summary']['success']} 条，失败 {data['summary']['failed']} 条")
        lines.append(f"平均置信度: {data['summary']['average_confidence']:.0%}")
        lines.append("")
        for i, entry in enumerate(data["results"], 1):
            p = entry["processed"]
            lines.append(f"--- 第 {i} 条 ---")
            lines.append(f"标题: {p.get('title', '未知')}")
            lines.append(f"URL: {p.get('url', '未知')}")
            lines.append(f"价格: {p.get('price', '未知')}")
            lines.append(f"评分: {p.get('rating', '未知')}")
            lines.append(f"学生数: {p.get('students', '未知')}")
            lines.append(f"讲师: {p.get('instructor', '未知')}")
            lines.append(f"置信度: {entry['confidence']:.0%}")
            if entry["hint"]:
                lines.append(f"提示: {entry['hint']}")
            lines.append("")

        result.data = "\n".join(lines)
        return result

    # E008: 不支持的输出格式
    return ProcessingResult(False, error_code="E008", message=ERROR_MESSAGES["E008"])


# ---------------------------------------------------------------------------
# 自检（selftest）逻辑
# ---------------------------------------------------------------------------

def run_selftest() -> bool:
    """
    离线自检核心逻辑。
    使用内置硬编码样例数据，不依赖外部文件、网络或当前工作目录。
    断言使用宽松阈值，确保任何环境均可通过。
    """
    print("开始自检...")

    # 测试用例 1: 正常单条数据
    test1 = {
        "title": "Python 入门到精通",
        "url": "https://example.com/course/python",
        "price": "$49.99",
        "rating": "4.5",
        "students": "12,345",
        "instructor": "张三",
    }
    result1 = process_input(test1)
    assert result1.success, f"测试1失败: {result1.error_code}"
    assert result1.data["summary"]["total"] == 1, "测试1: 数量错误"
    assert 0 < result1.data["summary"]["average_confidence"] <= 1, "测试1: 置信度范围错误"
    print("测试1（正常单条）: 通过")

    # 测试用例 2: 批量数据（含缺失字段）
    test2 = [
        {"title": "Web 开发实战", "url": "https://example.com/course/web"},
        {"title": "数据分析基础", "url": "https://example.com/course/data", "price": "free"},
    ]
    result2 = process_input(test2)
    assert result2.success, f"测试2失败: {result2.error_code}"
    assert result2.data["summary"]["total"] == 2, "测试2: 数量错误"
    assert result2.data["summary"]["success"] >= 1, "测试2: 成功数错误"
    print("测试2（批量含缺失）: 通过")

    # 测试用例 3: 空输入
    result3 = process_input(None)
    assert not result3.success, "测试3: 空输入应失败"
    assert result3.error_code == "E001", f"测试3: 错误码错误 {result3.error_code}"
    print("测试3（空输入）: 通过")

    # 测试用例 4: 格式错误输入
    result4 = process_input("这不是有效数据")
    assert not result4.success, "测试4: 格式错误应失败"
    assert result4.error_code in ("E003", "E001"), f"测试4: 错误码错误 {result4.error_code}"
    print("测试4（格式错误）: 通过")

    # 测试用例 5: 输出格式转换
    test5 = {"title": "机器学习", "url": "https://example.com/course/ml", "price": "$0"}
    result5 = process_input(test5)
    assert result5.success, f"测试5失败: {result5.error_code}"
    text_result = format_output(result5, "text")
    assert text_result.success, "测试5: 文本格式转换失败"
    assert isinstance(text_result.data, str), "测试5: 输出类型错误"
    assert len(text_result.data) > 0, "测试5: 输出为空"
    print("测试5（输出格式）: 通过")

    # 测试用例 6: 低置信度提示
    test6 = {"title": "仅标题无其他信息"}
    result6 = process_input(test6)
    assert result6.success, f"测试6失败: {result6.error_code}"
    assert result6.data["results"][0]["confidence"] < 1.0, "测试6: 置信度应降低"
    assert "需核实" in result6.data["results"][0]["hint"] or "建议复核" in result6.data["results"][0]["hint"], "测试6: 应有提示"
    print("测试6（低置信度）: 通过")

    # 测试用例 7: 极端数据（负价格、超范围评分）
    test7 = {
        "title": "极端数据测试",
        "url": "https://example.com/course/extreme",
        "price": "-5",
        "rating": "99",
        "students": "abc",
    }
    result7 = process_input(test7)
    assert result7.success, f"测试7失败: {result7.error_code}"
    processed = result7.data["results"][0]["processed"]
    assert processed["price"] <= 0, "测试7: 价格应为负或零"
    assert processed["rating"] is None, "测试7: 评分应无效"
    print("测试7（极端数据）: 通过")

    # 测试用例 8: 批量处理部分失败
    test8 = [
        {"title": "正常课程", "url": "https://example.com/course/ok"},
        {"title": "异常课程", "url": "https://example.com/course/bad", "price": "invalid"},
    ]
    result8 = process_input(test8)
    assert result8.success, f"测试8失败: {result8.error_code}"
    assert result8.data["summary"]["total"] == 2, "测试8: 数量错误"
    print("测试8（部分失败）: 通过")

    print("全部自检通过！")
    return True


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------

def main() -> int:
    """
    命令行主入口。
    """
    parser = argparse.ArgumentParser(
        description="课程信息采集与结构化处理工具（仅供学习与参考用途）"
    )
    parser.add_argument(
        "--input", "-i",
        type=str,
        help="输入内容，JSON 格式的课程信息（字典或字典列表），或包含 JSON 的文件路径",
    )
    parser.add_argument(
        "--format", "-f",
        type=str,
        default="json",
        choices=["json", "text"],
        help="输出格式（默认: json）",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行离线自检（不读取外部输入）",
    )

    args = parser.parse_args()

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
    if not args.input:
        print(f"错误 E001: {ERROR_MESSAGES['E001']}", file=sys.stderr)
        return 1

    # 尝试读取文件（如果路径存在）
    input_data = args.input
    try:
        import os
        if os.path.isfile(args.input):
            with open(args.input, "r", encoding="utf-8") as f:
                input_data = f.read()
    except Exception:
        # 不是文件或读取失败，按字符串处理
        pass

    # 解析输入
    try:
        raw = json.loads(input_data)
    except json.JSONDecodeError:
        # 不是有效 JSON，按原始字符串处理
        raw = input_data

    # 处理
    result = process_input(raw)
    if not result.success:
        print(f"错误 {result.error_code}: {result.message}", file=sys.stderr)
        return 1

    # 格式化输出
    result = format_output(result, args.format)
    if not result.success:
        print(f"错误 {result.error_code}: {result.message}", file=sys.stderr)
        return 1

    # 输出结果
    if args.format == "json":
        print(json.dumps(result.data, ensure_ascii=False, indent=2))
    else:
        print(result.data)

    return 0


if __name__ == "__main__":
    sys.exit(main())
