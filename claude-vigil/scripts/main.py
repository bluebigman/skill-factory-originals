#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
claude-vigil 技能实现脚本
=========================
基于功能规格独立实现的 clean-room 版本。

功能概述：
    1. 接收用户输入（文本/数据），解析并结构化关键信息。
    2. 根据置信度规则输出结果，支持批量处理与自定义格式。
    3. 提供 --selftest 离线自检模式，使用内置硬编码样例验证核心逻辑。

错误码：
    E001: 输入为空
    E002: 关键信息缺失
    E003: 输入格式错误
    E004: 超出能力边界
    E005: 置信度过低
    E006: 内部逻辑错误（不应发生）
    E007: 参数解析错误
    E008: 输出格式不支持
    E009: 批量处理中途失败
    E010: 未知异常

用法示例：
    python main.py --input "用户提供的数据" --format json
    python main.py --batch "item1,item2,item3" --format text
    python main.py --selftest
"""

import argparse
import json
import sys
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# 常量定义
# ---------------------------------------------------------------------------

# 置信度阈值
HIGH_CONFIDENCE_THRESHOLD = 90.0      # 高置信度下限
MEDIUM_CONFIDENCE_THRESHOLD = 85.0    # 中置信度下限

# 默认输出格式
DEFAULT_OUTPUT_FORMAT = "text"

# 关键字段列表（用于信息提取与缺失检测）
KEY_FIELDS = ["id", "content", "timestamp"]

# 错误码与话术映射（依据规格）
ERROR_MESSAGES = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：{missing_fields}",
    "E003": "输入格式不符合要求，示例：文本、JSON 字符串或逗号分隔列表",
    "E004": "这超出了本工具的能力范围，建议：简化输入或咨询专业人士",
    "E005": "结果无法确定，建议：人工复核关键字段或补充更多信息",
    "E006": "内部逻辑错误，请联系开发者",
    "E007": "命令行参数解析错误，请检查输入参数",
    "E008": "不支持的输出格式，可选：text / json",
    "E009": "批量处理中途失败，请检查输入项",
    "E010": "发生未知异常，请重试或反馈日志",
}


# ---------------------------------------------------------------------------
# 核心数据结构
# ---------------------------------------------------------------------------

class ProcessedItem:
    """单条处理结果的数据结构。"""

    def __init__(self, item_id: str, content: str, timestamp: str,
                 confidence: float, note: str = ""):
        self.id = item_id
        self.content = content
        self.timestamp = timestamp
        self.confidence = confidence
        self.note = note  # 附加说明，如"建议复核"或"[需核实]"

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式。"""
        return {
            "id": self.id,
            "content": self.content,
            "timestamp": self.timestamp,
            "confidence": round(self.confidence, 1),
            "note": self.note,
        }

    def to_text(self) -> str:
        """转换为文本行格式。"""
        return (f"[{self.id}] {self.content} "
                f"(时间: {self.timestamp}, 置信度: {self.confidence:.1f}%) "
                f"{self.note}".strip())


# ---------------------------------------------------------------------------
# 核心处理逻辑
# ---------------------------------------------------------------------------

def validate_input(raw_input: str) -> Tuple[bool, str]:
    """
    校验输入是否合法。

    返回：(是否合法, 错误码或空字符串)
    """
    if raw_input is None or raw_input.strip() == "":
        return False, "E001"  # 输入为空
    return True, ""


def parse_input(raw_input: str) -> List[Dict[str, str]]:
    """
    解析输入字符串为结构化条目列表。

    支持格式：
        - 纯文本（单条）
        - JSON 字符串（单条或数组）
        - 逗号分隔的多条目（批量）

    返回：解析后的条目列表，每个条目为 dict。
    """
    text = raw_input.strip()

    # 尝试 JSON 解析
    if text.startswith("{") or text.startswith("["):
        try:
            data = json.loads(text)
            if isinstance(data, dict):
                return [data]
            if isinstance(data, list):
                return data
            raise ValueError("JSON 根节点必须是对象或数组")
        except (json.JSONDecodeError, ValueError):
            # JSON 解析失败，继续尝试其他方式
            pass

    # 尝试逗号分隔（批量场景）
    if "," in text and not text.startswith("{"):
        items = [item.strip() for item in text.split(",") if item.strip()]
        return [{"content": item} for item in items]

    # 默认单条文本
    return [{"content": text}]


def extract_fields(item: Dict[str, Any]) -> ProcessedItem:
    """
    从条目中提取关键字段，计算置信度。

    置信度计算规则（宽松启发式）：
        - 基础分 60
        - 每个关键字段存在 +10
        - 内容长度超过 10 字符 +10
        - 内容长度超过 50 字符 +10
        - 时间戳格式像日期 +10

    返回：ProcessedItem 对象。
    """
    # 提取字段（缺失则用空字符串兜底）
    item_id = str(item.get("id", ""))
    content = str(item.get("content", ""))
    timestamp = str(item.get("timestamp", ""))

    # 计算置信度
    confidence = 60.0

    if item_id:
        confidence += 10
    if content:
        confidence += 10
    if timestamp:
        confidence += 10
    if len(content) > 10:
        confidence += 10
    if len(content) > 50:
        confidence += 10
    # 简单时间戳格式判断（包含数字和分隔符即可）
    if timestamp and any(c.isdigit() for c in timestamp):
        confidence += 10

    # 置信度封顶 100
    confidence = min(confidence, 100.0)

    # 根据置信度设置备注（依据规格）
    note = ""
    if confidence < MEDIUM_CONFIDENCE_THRESHOLD:
        note = "[需核实]"
    elif confidence < HIGH_CONFIDENCE_THRESHOLD:
        note = "建议复核"

    return ProcessedItem(
        item_id=item_id,
        content=content,
        timestamp=timestamp,
        confidence=confidence,
        note=note,
    )


def check_missing_fields(item: Dict[str, Any]) -> List[str]:
    """检查关键字段缺失情况，返回缺失字段列表。"""
    missing = []
    for field in KEY_FIELDS:
        if field not in item or str(item.get(field, "")).strip() == "":
            missing.append(field)
    return missing


def process_single(item: Dict[str, Any]) -> Tuple[ProcessedItem, Optional[str]]:
    """
    处理单个条目。

    返回：(处理结果, 错误码或None)
    """
    # 检查关键字段缺失
    missing = check_missing_fields(item)
    if len(missing) > 0 and "content" in missing:
        # 内容缺失属于关键错误
        return None, "E002"

    # 提取并结构化
    result = extract_fields(item)

    # 置信度过低检查
    if result.confidence < MEDIUM_CONFIDENCE_THRESHOLD:
        return result, "E005"  # 返回结果但附带低置信度错误码

    return result, None


def process_batch(raw_input: str) -> Tuple[List[ProcessedItem], List[str]]:
    """
    批量处理入口。

    返回：(处理结果列表, 错误码列表)
    """
    # 输入校验
    valid, err_code = validate_input(raw_input)
    if not valid:
        return [], [err_code]

    # 解析输入
    try:
        items = parse_input(raw_input)
    except Exception:
        return [], ["E003"]

    if not items:
        return [], ["E001"]

    results = []
    errors = []

    for item in items:
        try:
            result, err = process_single(item)
            if result is not None:
                results.append(result)
            if err is not None:
                errors.append(err)
        except Exception:
            errors.append("E010")

    return results, errors


def format_output(results: List[ProcessedItem], fmt: str) -> str:
    """
    按指定格式输出结果。

    支持格式：text / json
    """
    if fmt == "json":
        return json.dumps(
            [r.to_dict() for r in results],
            ensure_ascii=False,
            indent=2
        )
    elif fmt == "text":
        lines = [r.to_text() for r in results]
        return "\n".join(lines)
    else:
        raise ValueError(f"不支持的格式: {fmt}")


# ---------------------------------------------------------------------------
# 自检逻辑 (--selftest)
# ---------------------------------------------------------------------------

def run_selftest() -> int:
    """
    离线自检核心逻辑。使用内置硬编码样例，不依赖外部环境。

    返回：0 表示成功，1 表示失败。
    """
    print("=== claude-vigil 自检开始 ===")

    # 硬编码测试样例
    test_cases = [
        # (输入, 期望置信度下限, 期望是否至少有一条结果)
        (
            "这是第一条测试内容，包含足够长度的文本来测试置信度计算逻辑。",
            80.0,
            True,
        ),
        (
            '{"id": "A001", "content": "结构化测试数据", "timestamp": "2026-01-15"}',
            85.0,
            True,
        ),
        (
            "短文本",
            60.0,
            True,
        ),
        (
            "",  # 空输入应报错
            0.0,
            False,
        ),
    ]

    all_passed = True

    for idx, (input_str, min_conf, expect_result) in enumerate(test_cases):
        print(f"\n--- 用例 {idx + 1} ---")
        print(f"输入: {input_str[:50]}{'...' if len(input_str) > 50 else ''}")

        # 执行处理
        results, errors = process_batch(input_str)

        # 验证结果存在性
        if expect_result:
            if not results:
                print(f"  [FAIL] 期望有处理结果，但结果为空。错误码: {errors}")
                all_passed = False
                continue
            # 验证置信度（宽松阈值）
            avg_conf = sum(r.confidence for r in results) / len(results)
            print(f"  平均置信度: {avg_conf:.1f}% (阈值: ≥{min_conf}%)")
            if avg_conf < min_conf:
                print(f"  [FAIL] 平均置信度低于预期阈值")
                all_passed = False
                continue
            print("  [PASS] 结果存在且置信度达标")
        else:
            if results:
                print(f"  [FAIL] 期望无结果，但实际有 {len(results)} 条")
                all_passed = False
                continue
            if not errors:
                print("  [FAIL] 期望有错误码，但没有")
                all_passed = False
                continue
            print(f"  [PASS] 正确返回错误码: {errors[0]}")

    # 额外测试：格式输出
    print("\n--- 格式输出测试 ---")
    sample_items = [
        ProcessedItem("T1", "测试内容A", "2026-01-01", 92.0, ""),
        ProcessedItem("T2", "测试内容B", "2026-01-02", 88.0, "建议复核"),
    ]

    try:
        text_out = format_output(sample_items, "text")
        json_out = format_output(sample_items, "json")
        assert len(text_out) > 0, "文本输出为空"
        assert len(json_out) > 0, "JSON输出为空"
        # 宽松验证：JSON 应包含关键字段
        json_data = json.loads(json_out)
        assert len(json_data) == 2, "JSON条目数量不符"
        assert "confidence" in json_data[0], "缺少置信度字段"
        print("  [PASS] 文本与JSON格式输出均正常")
    except Exception as e:
        print(f"  [FAIL] 格式输出异常: {e}")
        all_passed = False

    # 测试错误处理
    print("\n--- 错误处理测试 ---")
    try:
        # 触发 E001（空输入）
        _, errs = process_batch("")
        assert "E001" in errs, "空输入应返回 E001"
        print("  [PASS] E001 空输入处理正确")

        # 触发 E002（关键信息缺失）
        _, errs = process_batch('{"id": "X1"}')
        assert "E002" in errs, "缺少content应返回 E002"
        print("  [PASS] E002 关键信息缺失处理正确")

        # 触发 E008（不支持的格式）
        try:
            format_output(sample_items, "xml")
            print("  [FAIL] 不支持的格式未抛异常")
            all_passed = False
        except ValueError:
            print("  [PASS] E008 不支持的格式处理正确")

    except Exception as e:
        print(f"  [FAIL] 错误处理测试异常: {e}")
        all_passed = False

    print("\n=== 自检结束 ===")
    if all_passed:
        print("结果: 全部通过 ✅")
        return 0
    else:
        print("结果: 存在失败项 ❌")
        return 1


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------

def main() -> int:
    """命令行主入口。"""
    parser = argparse.ArgumentParser(
        description="claude-vigil 代码审查技能 - 数据标准化处理工具",
        epilog="示例: python main.py --input '文本内容' --format json"
    )
    parser.add_argument(
        "--input", "-i",
        type=str,
        default="",
        help="输入内容：文本、JSON 或逗号分隔列表"
    )
    parser.add_argument(
        "--format", "-f",
        type=str,
        default=DEFAULT_OUTPUT_FORMAT,
        choices=["text", "json"],
        help="输出格式：text 或 json (默认: text)"
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行离线自检并退出"
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        return run_selftest()

    # 正常处理模式
    if not args.input:
        print(f"错误 E001: {ERROR_MESSAGES['E001']}", file=sys.stderr)
        return 1

    try:
        results, errors = process_batch(args.input)

        if not results:
            # 处理失败，输出第一个错误
            err = errors[0] if errors else "E010"
            msg = ERROR_MESSAGES.get(err, ERROR_MESSAGES["E010"])
            print(f"错误 {err}: {msg}", file=sys.stderr)
            return 1

        # 输出结果
        output = format_output(results, args.format)
        print(output)

        # 如果有警告，输出到 stderr
        for err in set(errors):
            if err == "E005":
                print(f"警告 E005: {ERROR_MESSAGES['E005']}", file=sys.stderr)

        return 0

    except Exception as e:
        print(f"错误 E010: {ERROR_MESSAGES['E010']} - {str(e)}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
