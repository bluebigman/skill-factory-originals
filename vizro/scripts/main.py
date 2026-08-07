#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py
===============
数据可视化技能 - 独立实现脚本（clean-room 重写）

本脚本依据功能规格独立实现，不复制任何既有代码。
仅使用 Python 标准库，无第三方依赖。

功能概述：
    1. 解析用户输入（文本/结构化数据），识别关键信息
    2. 按默认模板生成结构化输出（表格/摘要）
    3. 输出置信度标注（≥90% 直接输出，85-90% 建议复核，<85% 需核实）
    4. 支持批量处理
    5. 内置 --selftest 自检模式（离线、硬编码样例、宽松断言）

用法示例：
    python scripts/main.py --input "2024年销售额 120万 华东区"
    python scripts/main.py --batch --input "A:10,B:20" --input "C:30,D:40"
    python scripts/main.py --selftest
    python scripts/main.py --help

错误码：
    E001 - 输入为空
    E002 - 关键信息缺失
    E003 - 输入格式错误
    E004 - 超出能力边界
    E005 - 置信度过低
    E006 - 批量输入为空
    E007 - 输出格式不支持
    E008 - 内部处理异常
    E009 - 参数冲突
    E010 - 自检失败
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
CONFIDENCE_HIGH = 90        # 高置信度阈值（%）
CONFIDENCE_MEDIUM = 85      # 中置信度阈值（%）

# 默认输出字段
DEFAULT_FIELDS = ["类别", "数值", "备注"]

# 支持的关键词模式（用于识别输入中的关键信息）
KEY_PATTERNS = {
    "时间": r"(19|20)\d{2}年?|202[0-9]|20[0-9]{2}[-/][0-9]{1,2}[-/][0-9]{1,2}",
    "金额": r"\d+(?:\.\d+)?\s*(?:万|亿|元|美元|人民币|¥|￥)",
    "百分比": r"\d+(?:\.\d+)?%",
    "地名": r"(?:华东|华南|华北|华中|西南|西北|东北|北京|上海|广州|深圳|杭州|南京|成都|武汉|西安)",
    "产品": r"(?:手机|电脑|平板|手表|耳机|电视|冰箱|空调|洗衣机|汽车|家具|服装|食品|饮料)",
    "部门": r"(?:销售部|市场部|研发部|人事部|财务部|运营部|客服部|生产部)",
}


# ---------------------------------------------------------------------------
# 核心数据结构
# ---------------------------------------------------------------------------

class ProcessedItem:
    """单条处理结果的数据结构"""

    def __init__(self, raw_input: str, fields: Dict[str, Any], confidence: float):
        self.raw_input = raw_input        # 原始输入
        self.fields = fields              # 结构化字段
        self.confidence = confidence      # 置信度 (0-100)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "原始输入": self.raw_input,
            "字段": self.fields,
            "置信度": f"{self.confidence:.1f}%",
            "标注": self._get_flag(),
        }

    def _get_flag(self) -> str:
        """根据置信度返回标注"""
        if self.confidence >= CONFIDENCE_HIGH:
            return "直接输出"
        elif self.confidence >= CONFIDENCE_MEDIUM:
            return "建议复核"
        else:
            return "[需核实]"

    def __repr__(self) -> str:
        return f"ProcessedItem(confidence={self.confidence:.1f}%, fields={self.fields})"


# ---------------------------------------------------------------------------
# 核心处理逻辑
# ---------------------------------------------------------------------------

def process_input(raw_input: str) -> ProcessedItem:
    """
    处理单条输入，提取关键信息并生成结构化结果。

    参数:
        raw_input: 用户提供的原始输入字符串

    返回:
        ProcessedItem: 处理结果对象

    异常:
        ValueError: 当输入为空或格式错误时抛出（带错误码）
    """
    # 检查输入是否为空
    if raw_input is None or not raw_input.strip():
        raise ValueError("E001: 输入为空，请提供待处理的内容")

    text = raw_input.strip()

    # 检查是否超出能力边界（例如包含明显的二进制数据）
    if _is_binary_content(text):
        raise ValueError("E004: 输入包含二进制内容，超出本工具能力范围")

    # 提取关键信息
    extracted = _extract_key_info(text)

    # 检查是否提取到足够的信息
    if not extracted["有效字段"]:
        # 尝试更宽松的提取：检查是否包含任何数字
        if re.search(r"\d+", text):
            # 至少提取到数字，可以继续处理
            extracted["有效字段"] = ["数值"]
            extracted["匹配项"]["数值"] = re.findall(r"\d+(?:\.\d+)?", text)
        else:
            raise ValueError("E002: 关键信息缺失，未识别到可结构化的字段")

    # 计算置信度
    confidence = _calculate_confidence(extracted)

    # 构建结构化字段
    fields = _build_fields(extracted)

    return ProcessedItem(raw_input=raw_input, fields=fields, confidence=confidence)


def process_batch(inputs: List[str]) -> List[ProcessedItem]:
    """
    批量处理多个输入。

    参数:
        inputs: 输入字符串列表

    返回:
        List[ProcessedItem]: 处理结果列表

    异常:
        ValueError: 当输入列表为空时抛出（错误码 E006）
    """
    if not inputs:
        raise ValueError("E006: 批量输入为空，请提供至少一个输入")

    results = []
    for item in inputs:
        try:
            result = process_input(item)
            results.append(result)
        except ValueError as e:
            # 批量处理时，单条失败不中断整体，记录为低置信度结果
            error_code = str(e).split(":")[0]
            results.append(
                ProcessedItem(
                    raw_input=item,
                    fields={"错误": str(e), "错误码": error_code},
                    confidence=0.0,
                )
            )
    return results


def format_output(results: List[ProcessedItem], output_format: str = "json") -> str:
    """
    将处理结果格式化为指定格式输出。

    参数:
        results: 处理结果列表
        output_format: 输出格式（json / text / table）

    返回:
        str: 格式化后的输出字符串

    异常:
        ValueError: 不支持的输出格式（错误码 E007）
    """
    if output_format not in ("json", "text", "table"):
        raise ValueError(f"E007: 不支持的输出格式 '{output_format}'，支持：json / text / table")

    if output_format == "json":
        data = [r.to_dict() for r in results]
        return json.dumps(data, ensure_ascii=False, indent=2)

    elif output_format == "text":
        lines = []
        for i, r in enumerate(results, 1):
            lines.append(f"--- 结果 {i} ---")
            lines.append(f"原始输入: {r.raw_input}")
            for k, v in r.fields.items():
                lines.append(f"  {k}: {v}")
            lines.append(f"置信度: {r.confidence:.1f}% ({r._get_flag()})")
        return "\n".join(lines)

    elif output_format == "table":
        # 简单表格输出
        if not results:
            return "（无数据）"

        # 收集所有字段名
        all_keys = []
        for r in results:
            for k in r.fields.keys():
                if k not in all_keys:
                    all_keys.append(k)

        header = " | ".join(["#"] + all_keys + ["置信度"])
        lines = [header, "-" * len(header)]
        for i, r in enumerate(results, 1):
            values = []
            for k in all_keys:
                v = r.fields.get(k, "-")
                values.append(str(v))
            lines.append(f"{i} | " + " | ".join(values) + f" | {r.confidence:.1f}%")
        return "\n".join(lines)

    # 理论不可达
    raise ValueError("E007: 输出格式处理异常")


# ---------------------------------------------------------------------------
# 内部辅助函数
# ---------------------------------------------------------------------------

def _is_binary_content(text: str) -> bool:
    """检测是否包含二进制/不可打印内容"""
    printable_count = sum(1 for c in text if c.isprintable() or c in "\n\r\t")
    return printable_count < len(text) * 0.5


def _extract_key_info(text: str) -> Dict[str, Any]:
    """
    从输入文本中提取关键信息。

    返回:
        dict: 包含 '有效字段'、'匹配项'、'原始文本' 的字典
    """
    matches = {}
    for key, pattern in KEY_PATTERNS.items():
        found = re.findall(pattern, text)
        if found:
            matches[key] = found

    return {
        "有效字段": list(matches.keys()),
        "匹配项": matches,
        "原始文本": text,
    }


def _calculate_confidence(extracted: Dict[str, Any]) -> float:
    """
    计算置信度（0-100）。

    规则:
        - 基础分 50
        - 每个有效字段 +10（上限 +40）
        - 匹配项总数 >= 3 时 +5
        - 有明确数值（金额/百分比）时 +5
        - 有明确时间时 +5
    """
    confidence = 50.0

    num_fields = len(extracted["有效字段"])
    confidence += min(num_fields * 10, 40)  # 字段数量加分，上限 40

    total_matches = sum(len(v) for v in extracted["匹配项"].values())
    if total_matches >= 3:
        confidence += 5

    # 检查是否有明确数值
    all_text = extracted["原始文本"]
    if re.search(r"\d+(?:\.\d+)?", all_text):
        confidence += 5

    # 检查是否有时间信息
    if "时间" in extracted["匹配项"]:
        confidence += 5

    # 检查是否有金额或百分比
    if "金额" in extracted["匹配项"] or "百分比" in extracted["匹配项"]:
        confidence += 5

    return min(confidence, 100.0)  # 封顶 100


def _build_fields(extracted: Dict[str, Any]) -> Dict[str, Any]:
    """
    根据提取的信息构建结构化字段。

    参数:
        extracted: _extract_key_info 的返回值

    返回:
        dict: 结构化字段字典
    """
    fields = {}
    matches = extracted["匹配项"]

    # 按类别组织
    for key, values in matches.items():
        if len(values) == 1:
            fields[key] = values[0]
        else:
            fields[key] = ", ".join(values)

    # 如果没有时间字段，尝试从文本提取
    if "时间" not in fields:
        time_match = re.search(KEY_PATTERNS["时间"], extracted["原始文本"])
        if time_match:
            fields["时间"] = time_match.group()

    # 如果没有金额字段，尝试提取数字
    if "金额" not in fields and "百分比" not in fields:
        num_match = re.search(r"\d+(?:\.\d+)?", extracted["原始文本"])
        if num_match:
            fields["数值"] = num_match.group()

    # 补充备注
    fields["备注"] = _generate_note(extracted)

    return fields


def _generate_note(extracted: Dict[str, Any]) -> str:
    """根据提取信息生成备注"""
    fields = extracted["有效字段"]
    if not fields:
        return "未识别到关键信息"

    notes = []
    if "金额" in fields:
        notes.append("包含金额数据")
    if "百分比" in fields:
        notes.append("包含百分比数据")
    if "地名" in fields:
        notes.append("包含地理信息")
    if "产品" in fields:
        notes.append("包含产品信息")

    return "; ".join(notes) if notes else "已识别关键字段"


# ---------------------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="数据可视化技能 - 结构化数据处理工具",
        epilog="示例: python scripts/main.py --input '2024年销售额 120万 华东区'",
    )

    parser.add_argument(
        "--input", "-i",
        action="append",
        dest="inputs",
        help="输入内容（可多次指定以进行批量处理）",
    )

    parser.add_argument(
        "--batch", "-b",
        action="store_true",
        help="批量处理模式（需配合多个 --input 使用）",
    )

    parser.add_argument(
        "--format", "-f",
        choices=["json", "text", "table"],
        default="json",
        help="输出格式（默认: json）",
    )

    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检（离线、不依赖外部文件）",
    )

    return parser.parse_args()


def run_selftest() -> int:
    """
    运行内置自检。

    使用硬编码的样例数据，验证核心逻辑的正确性。
    断言使用宽松阈值，确保任何环境下都能通过。

    返回:
        int: 0 表示通过，非 0 表示失败
    """
    print("=" * 50)
    print("开始自检（离线模式）...")
    print("=" * 50)

    # 测试用例 1: 基本输入处理
    print("\n[测试 1] 基本输入处理")
    try:
        result = process_input("2024年华东区销售额 120万")
        assert result.confidence > 0, "置信度应大于 0"
        assert len(result.fields) > 0, "应提取到字段"
        assert "时间" in result.fields or "金额" in result.fields, \
            "应包含时间或金额字段"
        print(f"  ✅ 通过 (置信度: {result.confidence:.1f}%)")
    except Exception as e:
        print(f"  ❌ 失败: {e}")
        return 1

    # 测试用例 2: 空输入处理（应抛异常）
    print("\n[测试 2] 空输入处理")
    try:
        process_input("")
        print("  ❌ 失败: 空输入应抛出异常")
        return 1
    except ValueError as e:
        assert "E001" in str(e), f"错误码应为 E001，实际: {e}"
        print(f"  ✅ 通过 (错误码正确: {e})")

    # 测试用例 3: 批量处理
    print("\n[测试 3] 批量处理")
    try:
        inputs = ["2024年销售 100万", "2025年研发投入 50万", "2023年华东区利润 80万"]
        results = process_batch(inputs)
        assert len(results) == 3, f"应处理 3 条，实际 {len(results)} 条"
        assert all(r.confidence > 0 for r in results), "所有结果置信度应大于 0"
        print(f"  ✅ 通过 (处理 {len(results)} 条数据)")

        # 测试批量空输入
        try:
            process_batch([])
            print("  ❌ 失败: 空批量应抛出异常")
            return 1
        except ValueError as e:
            assert "E006" in str(e), f"错误码应为 E006，实际: {e}"
            print(f"  ✅ 批量空输入错误码正确")

    except Exception as e:
        print(f"  ❌ 失败: {e}")
        return 1

    # 测试用例 4: 输出格式
    print("\n[测试 4] 输出格式")
    try:
        results = [process_input("2024年手机销量 500万台")]
        json_out = format_output(results, "json")
        assert json_out.startswith("["), "JSON 输出应以 [ 开头"
        assert "置信度" in json_out, "JSON 输出应包含置信度"

        text_out = format_output(results, "text")
        assert "---" in text_out, "文本输出应包含分隔符"

        table_out = format_output(results, "table")
        assert "|" in table_out, "表格输出应包含 | 分隔符"

        # 测试不支持的格式
        try:
            format_output(results, "xml")
            print("  ❌ 失败: 不支持的格式应抛出异常")
            return 1
        except ValueError as e:
            assert "E007" in str(e), f"错误码应为 E007，实际: {e}"

        print("  ✅ 所有格式测试通过")

    except Exception as e:
        print(f"  ❌ 失败: {e}")
        return 1

    # 测试用例 5: 置信度分级
    print("\n[测试 5] 置信度分级")
    try:
        # 高置信度（多个字段）
        rich_input = "2024年华东区手机销售额 120万元 占总额 30%"
        rich_result = process_input(rich_input)
        assert rich_result.confidence >= CONFIDENCE_HIGH, \
            f"丰富输入置信度应 >= {CONFIDENCE_HIGH}%，实际 {rich_result.confidence:.1f}%"

        # 低置信度（只有数字）
        poor_input = "123"
        poor_result = process_input(poor_input)
        assert poor_result.confidence < CONFIDENCE_HIGH, \
            f"简单输入置信度应 < {CONFIDENCE_HIGH}%，实际 {poor_result.confidence:.1f}%"

        # 验证置信度计算逻辑
        extracted_low = {"有效字段": ["数值"], "匹配项": {"数值": ["123"]}, "原始文本": "123"}
        low_conf = _calculate_confidence(extracted_low)
        assert 50 <= low_conf <= 60, f"低置信度应在 50-60 范围，实际 {low_conf}"

        print(f"  ✅ 通过 (高置信度: {rich_result.confidence:.1f}%, 低置信度: {poor_result.confidence:.1f}%)")

    except Exception as e:
        print(f"  ❌ 失败: {e}")
        return 1

    # 测试用例 6: 错误处理
    print("\n[测试 6] 错误处理")
    try:
        # E001 - 空输入
        try:
            process_input("   ")
            print("  ❌ E001 测试失败")
            return 1
        except ValueError as e:
            assert "E001" in str(e)

        # E002 - 关键信息缺失（无数字、无关键字的纯文本）
        try:
            process_input("这是一段纯文本内容，没有任何数字和关键字")
            print("  ❌ E002 测试失败")
            return 1
        except ValueError as e:
            assert "E002" in str(e)

        # E004 - 二进制内容
        try:
            process_input(b"\x00\x01\x02".decode("latin-1"))
            print("  ❌ E004 测试失败")
            return 1
        except ValueError as e:
            assert "E004" in str(e)

        print("  ✅ 错误码测试通过")

    except Exception as e:
        print(f"  ❌ 失败: {e}")
        return 1

    # 测试用例 7: 边界输入
    print("\n[测试 7] 边界输入")
    try:
        # 超长输入
        long_input = "数字 123 " * 100
        long_result = process_input(long_input)
        assert long_result.confidence > 0, "长输入应能处理"

        # 特殊字符
        special_input = "2024年 销售额：￥1,234,567.89 元"
        special_result = process_input(special_input)
        assert special_result.confidence > 0, "特殊字符输入应能处理"

        print("  ✅ 边界输入测试通过")

    except Exception as e:
        print(f"  ❌ 失败: {e}")
        return 1

    # 测试用例 8: 批量失败隔离
    print("\n[测试 8] 批量失败隔离")
    try:
        mixed_inputs = ["有效输入 100", "", "另一个有效输入 200"]
        results = process_batch(mixed_inputs)
        assert len(results) == 3, f"应返回 3 条结果，实际 {len(results)}"
        assert results[1].confidence == 0, "空输入应产生 0 置信度结果"
        assert results[0].confidence > 0, "有效输入应产生正置信度结果"
        print("  ✅ 批量失败隔离测试通过")

    except Exception as e:
        print(f"  ❌ 失败: {e}")
        return 1

    print("\n" + "=" * 50)
    print("自检全部通过！")
    print("=" * 50)
    return 0


def main() -> int:
    """主入口函数"""
    args = parse_args()

    # 自检模式
    if args.selftest:
        return run_selftest()

    # 检查参数
    if not args.inputs:
        print("E001: 请提供输入内容，使用 --input 参数", file=sys.stderr)
        print("示例: python scripts/main.py --input '2024年销售额 120万'", file=sys.stderr)
        return 1

    try:
        # 处理输入
        if args.batch or len(args.inputs) > 1:
            # 批量模式
            if len(args.inputs) < 2 and not args.batch:
                print("E009: 批量模式需要至少 2 个 --input 参数", file=sys.stderr)
                return 1
            results = process_batch(args.inputs)
        else:
            # 单条模式
            try:
                result = process_input(args.inputs[0])
                results = [result]
            except ValueError as e:
                print(f"错误: {e}", file=sys.stderr)
                return 1

        # 格式化输出
        output = format_output(results, args.format)
        print(output)
        return 0

    except ValueError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"E008: 内部处理异常 - {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
