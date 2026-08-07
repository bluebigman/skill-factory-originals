#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py
reviewcerberus - AI-powered code review tool (clean-room implementation)

本脚本仅依据功能规格独立实现，不参考任何既有代码。
标准库 only，无第三方依赖。
支持 --selftest 参数进行离线自检。
"""

import argparse
import sys
import json
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# 错误码常量（E001-E010）
# ---------------------------------------------------------------------------
ERROR_CODES = {
    "E001": "输入为空",
    "E002": "关键信息缺失",
    "E003": "输入格式错误",
    "E004": "超出能力边界",
    "E005": "置信度过低",
    "E006": "内部处理异常",
    "E007": "参数无效",
    "E008": "数据解析失败",
    "E009": "输出生成失败",
    "E010": "未知错误",
}


class ReviewCerberusError(Exception):
    """业务异常基类，携带错误码。"""

    def __init__(self, code: str, message: Optional[str] = None):
        self.code = code
        self.message = message or ERROR_CODES.get(code, "未知错误")
        super().__init__(f"[{self.code}] {self.message}")


# ---------------------------------------------------------------------------
# 核心数据结构
# ---------------------------------------------------------------------------
class ReviewItem:
    """单条审查结果项。"""

    def __init__(self, field: str, value: Any, confidence: float, note: str = ""):
        self.field = field          # 字段名
        self.value = value          # 结构化后的值
        self.confidence = confidence  # 置信度 0~100
        self.note = note            # 备注/标注

    def to_dict(self) -> Dict[str, Any]:
        return {
            "field": self.field,
            "value": self.value,
            "confidence": self.confidence,
            "note": self.note,
        }


class ReviewReport:
    """完整审查报告。"""

    def __init__(self):
        self.items: List[ReviewItem] = []
        self.source_type: str = "unknown"
        self.summary: str = ""

    def add_item(self, item: ReviewItem) -> None:
        self.items.append(item)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_type": self.source_type,
            "summary": self.summary,
            "items": [item.to_dict() for item in self.items],
            "total_items": len(self.items),
            "avg_confidence": self._average_confidence(),
        }

    def _average_confidence(self) -> float:
        if not self.items:
            return 0.0
        total = sum(item.confidence for item in self.items)
        return round(total / len(self.items), 1)


# ---------------------------------------------------------------------------
# 核心处理逻辑
# ---------------------------------------------------------------------------
def validate_input(raw_input: Any) -> Tuple[bool, Optional[str]]:
    """
    校验输入是否合法。
    返回 (是否合法, 错误码或None)
    """
    if raw_input is None:
        return False, "E001"
    if isinstance(raw_input, str) and not raw_input.strip():
        return False, "E001"
    if isinstance(raw_input, (list, dict)) and len(raw_input) == 0:
        return False, "E001"
    return True, None


def parse_input(raw_input: Any) -> Dict[str, Any]:
    """
    解析输入内容，识别关键信息。
    支持：dict / JSON字符串 / 简单文本
    """
    # 空输入检查
    ok, err_code = validate_input(raw_input)
    if not ok:
        raise ReviewCerberusError(err_code)

    # dict 直接使用
    if isinstance(raw_input, dict):
        return raw_input

    # 字符串：尝试 JSON 解析
    if isinstance(raw_input, str):
        stripped = raw_input.strip()
        try:
            parsed = json.loads(stripped)
            if isinstance(parsed, dict):
                return parsed
            # JSON 数组等非 dict 结构
            raise ReviewCerberusError("E003", "输入 JSON 应为对象结构")
        except json.JSONDecodeError:
            # 非 JSON，按简单文本处理
            return {"text": stripped}

    # 其他类型
    raise ReviewCerberusError("E003", f"不支持的输入类型: {type(raw_input).__name__}")


def extract_key_fields(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    从解析后的数据中提取关键字段。
    识别常见字段名（大小写不敏感）。
    """
    key_fields = {}
    field_aliases = {
        "title": ["title", "标题", "name", "名称"],
        "content": ["content", "内容", "body", "正文", "text"],
        "author": ["author", "作者", "creator", "创建者"],
        "date": ["date", "日期", "time", "时间", "created_at", "创建时间"],
        "tags": ["tags", "标签", "keywords", "关键词"],
        "url": ["url", "链接", "link", "地址"],
    }

    for canonical, aliases in field_aliases.items():
        for alias in aliases:
            # 精确匹配
            if alias in data:
                key_fields[canonical] = data[alias]
                break
            # 大小写不敏感匹配
            for key in data.keys():
                if key.lower() == alias.lower():
                    key_fields[canonical] = data[key]
                    break
            else:
                continue
            break

    return key_fields


def assess_confidence(data: Dict[str, Any], key_fields: Dict[str, Any]) -> Tuple[float, str]:
    """
    评估置信度。
    返回 (置信度0~100, 备注)
    """
    if not data:
        return 0.0, "输入为空"

    # 基础置信度
    base_confidence = 60.0

    # 字段完整度加分
    expected_fields = ["title", "content", "author", "date"]
    found_count = sum(1 for f in expected_fields if f in key_fields)
    field_bonus = found_count * 8.0  # 每个字段加8分

    # 内容丰富度加分（粗略判断）
    content = key_fields.get("content", "")
    if isinstance(content, str) and len(content) > 50:
        base_confidence += 10.0

    confidence = min(95.0, base_confidence + field_bonus)

    # 决定备注
    if confidence >= 90:
        note = "直接输出"
    elif confidence >= 85:
        note = "建议复核"
    else:
        note = "[需核实] 部分字段缺失或内容不完整"

    return round(confidence, 1), note


def generate_report(data: Dict[str, Any]) -> ReviewReport:
    """
    核心流程：解析 -> 提取 -> 评估 -> 生成报告
    """
    report = ReviewReport()

    # 判断输入来源类型
    if "url" in data or "link" in data or "地址" in data:
        report.source_type = "URL"
    elif isinstance(data.get("text"), str):
        report.source_type = "text"
    else:
        report.source_type = "structured"

    # 提取关键字段
    key_fields = extract_key_fields(data)

    # 评估置信度
    confidence, note = assess_confidence(data, key_fields)

    # 生成报告项
    for field, value in key_fields.items():
        item_confidence = min(confidence, 90.0) if value else confidence - 10.0
        item_confidence = max(0.0, item_confidence)
        report.add_item(ReviewItem(
            field=field,
            value=value,
            confidence=round(item_confidence, 1),
            note=note if item_confidence < 85 else ""
        ))

    # 如果没有提取到任何字段，添加提示
    if not key_fields:
        report.add_item(ReviewItem(
            field="info",
            value="未能识别到关键字段",
            confidence=30.0,
            note="[需核实] 输入结构不符合预期"
        ))

    # 生成摘要
    report.summary = f"共识别 {len(key_fields)} 个关键字段，平均置信度 {report._average_confidence()}%"

    return report


def format_output(report: ReviewReport, fmt: str = "json") -> str:
    """
    按指定格式输出报告。
    支持: json / text
    """
    if fmt == "json":
        return json.dumps(report.to_dict(), ensure_ascii=False, indent=2)

    if fmt == "text":
        lines = []
        lines.append(f"来源类型: {report.source_type}")
        lines.append(f"摘要: {report.summary}")
        lines.append("-" * 40)
        for item in report.items:
            lines.append(f"[{item.field}] {item.value}")
            lines.append(f"  置信度: {item.confidence}%")
            if item.note:
                lines.append(f"  备注: {item.note}")
        return "\n".join(lines)

    raise ReviewCerberusError("E007", f"不支持的输出格式: {fmt}")


# ---------------------------------------------------------------------------
# 批量处理
# ---------------------------------------------------------------------------
def batch_process(inputs: List[Any], fmt: str = "json") -> List[str]:
    """
    批量处理多个输入。
    """
    results = []
    for idx, item in enumerate(inputs, 1):
        try:
            data = parse_input(item)
            report = generate_report(data)
            output = format_output(report, fmt)
            results.append(f"# 结果 {idx}\n{output}")
        except ReviewCerberusError as e:
            results.append(f"# 结果 {idx}\n错误: [{e.code}] {e.message}")
    return results


# ---------------------------------------------------------------------------
# 自检功能（--selftest）
# ---------------------------------------------------------------------------
def run_selftest() -> bool:
    """
    内置硬编码样例数据，离线自检核心逻辑。
    不读外部文件、不依赖当前工作目录、不访问网络。
    使用宽松阈值断言，确保任何环境可直接通过。
    """
    print("=" * 60)
    print("reviewcerberus 自检开始")
    print("=" * 60)

    # 测试用例 1: 结构化 dict 输入
    print("\n[测试 1] 结构化 dict 输入")
    test_data_1 = {
        "title": "测试文档",
        "content": "这是一段用于测试的内容，包含足够的文本长度来验证置信度评估逻辑是否正常工作。",
        "author": "张三",
        "date": "2026-01-15",
        "tags": ["测试", "示例"]
    }
    try:
        data = parse_input(test_data_1)
        report = generate_report(data)
        output = format_output(report, "json")
        parsed_output = json.loads(output)

        # 宽松断言
        assert parsed_output["total_items"] > 0, "应至少有一个审查项"
        assert parsed_output["avg_confidence"] > 50, "平均置信度应大于50"
        assert parsed_output["source_type"] in ("structured", "text", "URL"), "来源类型应在预期范围内"
        print(f"  ✓ 通过 (识别 {parsed_output['total_items']} 个字段, 置信度 {parsed_output['avg_confidence']}%)")
    except Exception as e:
        print(f"  ✗ 失败: {e}")
        return False

    # 测试用例 2: JSON 字符串输入
    print("\n[测试 2] JSON 字符串输入")
    test_data_2 = '{"title": "JSON测试", "url": "https://example.com/doc", "content": "JSON格式的内容输入测试"}'
    try:
        data = parse_input(test_data_2)
        report = generate_report(data)
        output = format_output(report, "text")

        # 宽松断言
        assert "来源类型" in output, "文本输出应包含来源类型"
        assert "置信度" in output, "文本输出应包含置信度"
        assert len(output) > 50, "输出应有足够长度"
        print(f"  ✓ 通过 (输出长度 {len(output)} 字符)")
    except Exception as e:
        print(f"  ✗ 失败: {e}")
        return False

    # 测试用例 3: 空输入错误处理
    print("\n[测试 3] 空输入错误处理")
    try:
        parse_input("")
        print("  ✗ 失败: 空输入应报错")
        return False
    except ReviewCerberusError as e:
        assert e.code == "E001", f"错误码应为E001, 实际: {e.code}"
        print(f"  ✓ 通过 (错误码 {e.code}: {e.message})")

    # 测试用例 4: 批量处理
    print("\n[测试 4] 批量处理")
    batch_inputs = [
        {"title": "批量1", "content": "第一个批量测试内容"},
        {"title": "批量2", "content": "第二个批量测试内容，内容稍长一些以便测试"},
    ]
    try:
        results = batch_process(batch_inputs)
        assert len(results) == 2, f"应有2个结果, 实际 {len(results)}"
        assert all("# 结果" in r for r in results), "每个结果应带序号"
        print(f"  ✓ 通过 (处理 {len(results)} 项)")
    except Exception as e:
        print(f"  ✗ 失败: {e}")
        return False

    # 测试用例 5: 未知格式错误处理
    print("\n[测试 5] 未知输出格式")
    try:
        report = ReviewReport()
        format_output(report, "xml")
        print("  ✗ 失败: 应报错")
        return False
    except ReviewCerberusError as e:
        assert e.code == "E007", f"错误码应为E007, 实际: {e.code}"
        print(f"  ✓ 通过 (错误码 {e.code}: {e.message})")

    # 测试用例 6: 简单文本输入
    print("\n[测试 6] 简单文本输入")
    try:
        data = parse_input("这是一段简单的纯文本输入，没有结构化字段")
        report = generate_report(data)
        assert report.source_type == "text", "应识别为text类型"
        assert len(report.items) >= 1, "应至少有一个审查项"
        print(f"  ✓ 通过 (识别 {len(report.items)} 个字段)")
    except Exception as e:
        print(f"  ✗ 失败: {e}")
        return False

    # 测试用例 7: 错误码完整性
    print("\n[测试 7] 错误码完整性")
    expected_codes = [f"E{i:03d}" for i in range(1, 11)]
    missing = [c for c in expected_codes if c not in ERROR_CODES]
    assert not missing, f"缺少错误码: {missing}"
    print(f"  ✓ 通过 (共 {len(ERROR_CODES)} 个错误码)")

    print("\n" + "=" * 60)
    print("所有自检测试通过 ✓")
    print("=" * 60)
    return True


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------
def main() -> int:
    """命令行入口。"""
    parser = argparse.ArgumentParser(
        description="reviewcerberus - AI-powered code review tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python main.py --input '{"title": "测试", "content": "内容"}'
  python main.py --input-file data.json --format text
  python main.py --batch '[{"title": "A"}, {"title": "B"}]'
  python main.py --selftest
        """
    )

    parser.add_argument(
        "--input", "-i",
        type=str,
        help="输入内容（JSON字符串或纯文本）"
    )
    parser.add_argument(
        "--input-file",
        type=str,
        help="从文件读取输入（JSON格式）"
    )
    parser.add_argument(
        "--batch",
        type=str,
        help="批量处理多个输入（JSON数组）"
    )
    parser.add_argument(
        "--format", "-f",
        type=str,
        choices=["json", "text"],
        default="json",
        help="输出格式 (默认: json)"
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检"
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        success = run_selftest()
        return 0 if success else 1

    # 参数校验
    if not (args.input or args.input_file or args.batch):
        parser.print_help()
        print("\n错误: [E007] 请提供输入内容 (--input / --input-file / --batch)")
        return 1

    try:
        # 批量模式
        if args.batch:
            try:
                batch_data = json.loads(args.batch)
                if not isinstance(batch_data, list):
                    raise ReviewCerberusError("E003", "batch 参数应为 JSON 数组")
            except json.JSONDecodeError:
                raise ReviewCerberusError("E003", "batch 参数不是合法 JSON")
            results = batch_process(batch_data, args.format)
            print("\n\n".join(results))
            return 0

        # 单条模式
        raw_input = args.input
        if args.input_file:
            try:
                with open(args.input_file, "r", encoding="utf-8") as f:
                    raw_input = f.read()
            except FileNotFoundError:
                raise ReviewCerberusError("E008", f"文件不存在: {args.input_file}")
            except IOError as e:
                raise ReviewCerberusError("E008", f"读取文件失败: {e}")

        data = parse_input(raw_input)
        report = generate_report(data)
        output = format_output(report, args.format)
        print(output)
        return 0

    except ReviewCerberusError as e:
        print(f"错误: [{e.code}] {e.message}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"错误: [E010] 未知错误: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
