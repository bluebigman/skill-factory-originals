#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
dashbrew — 数据可视化 TUI 仪表板构建器（独立实现）

本脚本依据功能规格独立编写（clean-room），不包含任何既有实现代码。
仅使用 Python 标准库，无第三方依赖。

主要功能：
    1. 将用户提供的数据/文件/URL 转换为结构化结果
    2. 识别并保留输入中的关键信息
    3. 按约定格式生成输出（支持 JSON / 表格 / 文本）
    4. 对不确定项给出置信度提示
    5. 支持批量处理和自定义格式

用法示例：
    python main.py --input "商品A:100;商品B:200;商品C:150" --format table
    python main.py --input data.json --format json
    python main.py --selftest

错误码：
    E001 输入为空
    E002 关键信息缺失
    E003 输入格式错误
    E004 超出能力边界
    E005 置信度过低
    E006 文件读取失败
    E007 输出格式不支持
    E008 批量处理中断
    E009 内部逻辑错误
    E010 参数解析错误
"""

import argparse
import json
import os
import re
import sys
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# 常量定义
# ============================================================

# 置信度阈值
CONFIDENCE_HIGH = 0.90      # 置信度 ≥90%：直接输出
CONFIDENCE_MEDIUM = 0.85    # 85%-90%：标注"建议复核"
# <85%：标注"[需核实]"

# 支持的输出格式
SUPPORTED_FORMATS = ("json", "table", "text", "csv")

# 错误码对应的标准化话术
ERROR_MESSAGES: Dict[str, str] = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：",
    "E003": "输入格式不符合要求，示例：商品A:100;商品B:200",
    "E004": "这超出了本工具的能力范围，建议使用专业数据处理工具。",
    "E005": "结果无法确定，建议：检查输入数据或使用其他工具验证。",
    "E006": "文件读取失败，请检查文件路径和权限。",
    "E007": "不支持的输出格式，可选格式：json / table / text / csv",
    "E008": "批量处理中断，请检查输入数据格式。",
    "E009": "内部逻辑错误，请报告此问题。",
    "E010": "参数解析错误，请检查命令行参数。",
}

# 内置硬编码样例数据（用于 --selftest）
SELFTEST_DATA: List[Dict[str, Any]] = [
    {"name": "商品A", "value": 100, "category": "电子"},
    {"name": "商品B", "value": 200, "category": "家居"},
    {"name": "商品C", "value": 150, "category": "电子"},
    {"name": "商品D", "value": 80, "category": "服饰"},
    {"name": "商品E", "value": 300, "category": "家居"},
]

SELFTEST_RAW_INPUT = "商品A:100;商品B:200;商品C:150;商品D:80;商品E:300"


# ============================================================
# 核心数据结构与处理逻辑
# ============================================================

class DataPoint:
    """表示一条结构化数据记录。"""

    def __init__(self, name: str, value: float, category: str = "未分类"):
        self.name = name
        self.value = value
        self.category = category

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式。"""
        return {
            "name": self.name,
            "value": self.value,
            "category": self.category,
        }

    def __repr__(self) -> str:
        return f"DataPoint(name={self.name!r}, value={self.value!r}, category={self.category!r})"


def parse_key_value_input(raw_text: str) -> Tuple[List[DataPoint], float]:
    """
    解析 "名称:数值;名称:数值;..." 格式的输入。

    参数:
        raw_text: 原始输入文本

    返回:
        (数据点列表, 置信度)

    错误码:
        E001 输入为空
        E003 输入格式错误
    """
    if not raw_text or not raw_text.strip():
        raise DashbrewError("E001")

    items = [item.strip() for item in raw_text.split(";") if item.strip()]
    if not items:
        raise DashbrewError("E001")

    data_points: List[DataPoint] = []
    parsed_count = 0

    for item in items:
        # 支持 "名称:数值" 或 "名称=数值" 格式
        match = re.match(r"^(.+?)[:=](.+)$", item.strip())
        if not match:
            continue

        name = match.group(1).strip()
        value_str = match.group(2).strip()

        try:
            value = float(value_str)
        except ValueError:
            continue

        data_points.append(DataPoint(name=name, value=value))
        parsed_count += 1

    if not data_points:
        raise DashbrewError("E003")

    # 置信度 = 成功解析数 / 总条目数
    confidence = parsed_count / len(items)
    return data_points, confidence


def parse_json_input(json_text: str) -> Tuple[List[DataPoint], float]:
    """
    解析 JSON 格式输入。

    支持格式:
        [{"name": "A", "value": 100, "category": "电子"}, ...]
        {"items": [{"name": "A", "value": 100}, ...]}

    参数:
        json_text: JSON 文本

    返回:
        (数据点列表, 置信度)

    错误码:
        E001 输入为空
        E003 输入格式错误
    """
    if not json_text or not json_text.strip():
        raise DashbrewError("E001")

    try:
        data = json.loads(json_text)
    except json.JSONDecodeError:
        raise DashbrewError("E003")

    # 支持两种结构：顶层列表 或 {"items": [...]}
    if isinstance(data, list):
        items = data
    elif isinstance(data, dict) and "items" in data:
        items = data["items"]
    else:
        raise DashbrewError("E003")

    if not items:
        raise DashbrewError("E001")

    data_points: List[DataPoint] = []
    parsed_count = 0

    for item in items:
        if not isinstance(item, dict):
            continue

        name = item.get("name") or item.get("label") or item.get("key")
        value = item.get("value") or item.get("val") or item.get("数值")
        category = item.get("category") or item.get("cat") or "未分类"

        if name is None or value is None:
            continue

        try:
            value_num = float(value)
        except (TypeError, ValueError):
            continue

        data_points.append(DataPoint(name=str(name), value=value_num, category=str(category)))
        parsed_count += 1

    if not data_points:
        raise DashbrewError("E003")

    confidence = parsed_count / len(items)
    return data_points, confidence


def parse_file_input(file_path: str) -> Tuple[List[DataPoint], float]:
    """
    从文件读取数据并解析。

    参数:
        file_path: 文件路径

    返回:
        (数据点列表, 置信度)

    错误码:
        E006 文件读取失败
    """
    if not os.path.isfile(file_path):
        raise DashbrewError("E006")

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read().strip()
    except (IOError, OSError):
        raise DashbrewError("E006")

    if not content:
        raise DashbrewError("E001")

    # 尝试 JSON 解析
    if content.startswith("[") or content.startswith("{"):
        try:
            return parse_json_input(content)
        except DashbrewError:
            pass  # 不是合法 JSON，继续尝试其他格式

    # 尝试键值对解析
    return parse_key_value_input(content)


def auto_detect_and_parse(user_input: str) -> Tuple[List[DataPoint], float, str]:
    """
    自动检测输入类型并解析。

    参数:
        user_input: 用户输入（可能是文本、JSON、或文件路径）

    返回:
        (数据点列表, 置信度, 输入类型描述)

    错误码:
        E001 输入为空
        E003 输入格式错误
        E006 文件读取失败
    """
    if not user_input or not user_input.strip():
        raise DashbrewError("E001")

    input_str = user_input.strip()

    # 1. 判断是否为文件路径
    if os.path.isfile(input_str):
        data_points, confidence = parse_file_input(input_str)
        return data_points, confidence, "file"

    # 2. 判断是否为 JSON
    if input_str.startswith("[") or input_str.startswith("{"):
        try:
            data_points, confidence = parse_json_input(input_str)
            return data_points, confidence, "json"
        except DashbrewError:
            pass  # 不是合法 JSON，继续

    # 3. 默认按键值对解析
    data_points, confidence = parse_key_value_input(input_str)
    return data_points, confidence, "key_value"


def compute_statistics(data_points: List[DataPoint]) -> Dict[str, Any]:
    """
    计算数据统计信息。

    参数:
        data_points: 数据点列表

    返回:
        统计信息字典
    """
    if not data_points:
        return {}

    values = [dp.value for dp in data_points]
    names = [dp.name for dp in data_points]
    categories = [dp.category for dp in data_points]

    total = sum(values)
    avg = total / len(values) if values else 0
    max_val = max(values) if values else 0
    min_val = min(values) if values else 0

    # 找出最大值和最小值对应的名称
    max_idx = values.index(max_val) if values else -1
    min_idx = values.index(min_val) if values else -1

    # 按类别聚合
    category_totals: Dict[str, float] = {}
    for dp in data_points:
        category_totals[dp.category] = category_totals.get(dp.category, 0) + dp.value

    return {
        "count": len(data_points),
        "total": total,
        "average": avg,
        "max_value": max_val,
        "max_name": names[max_idx] if max_idx >= 0 else "",
        "min_value": min_val,
        "min_name": names[min_idx] if min_idx >= 0 else "",
        "categories": sorted(category_totals.keys()),
        "category_totals": category_totals,
    }


def format_as_table(data_points: List[DataPoint]) -> str:
    """
    将数据点格式化为表格文本。

    参数:
        data_points: 数据点列表

    返回:
        表格字符串
    """
    if not data_points:
        return "（无数据）"

    # 计算列宽
    name_width = max(len("名称"), max(len(dp.name) for dp in data_points))
    value_width = max(len("数值"), max(len(f"{dp.value:.2f}") for dp in data_points))
    cat_width = max(len("类别"), max(len(dp.category) for dp in data_points))

    # 构建表头
    header = f"| {'名称':<{name_width}} | {'数值':>{value_width}} | {'类别':<{cat_width}} |"
    separator = f"|{'-' * (name_width + 2)}|{'-' * (value_width + 2)}|{'-' * (cat_width + 2)}|"

    lines = [header, separator]

    # 构建数据行
    for dp in data_points:
        row = f"| {dp.name:<{name_width}} | {dp.value:>{value_width}.2f} | {dp.category:<{cat_width}} |"
        lines.append(row)

    return "\n".join(lines)


def format_as_csv(data_points: List[DataPoint]) -> str:
    """
    将数据点格式化为 CSV 文本。

    参数:
        data_points: 数据点列表

    返回:
        CSV 字符串
    """
    if not data_points:
        return ""

    lines = ["名称,数值,类别"]
    for dp in data_points:
        # 简单转义：如果包含逗号则用引号包裹
        name = f'"{dp.name}"' if "," in dp.name else dp.name
        category = f'"{dp.category}"' if "," in dp.category else dp.category
        lines.append(f"{name},{dp.value},{category}")

    return "\n".join(lines)


def format_as_text(data_points: List[DataPoint], stats: Dict[str, Any]) -> str:
    """
    将数据点格式化为纯文本报告。

    参数:
        data_points: 数据点列表
        stats: 统计信息

    返回:
        文本报告
    """
    if not data_points:
        return "（无数据）"

    lines = ["=== 数据可视化报告 ===", ""]

    # 数据列表
    lines.append(f"共 {len(data_points)} 条记录：")
    for i, dp in enumerate(data_points, 1):
        lines.append(f"  {i}. {dp.name}: {dp.value:.2f} (类别: {dp.category})")

    # 统计信息
    lines.append("")
    lines.append("--- 统计摘要 ---")
    lines.append(f"  总和: {stats.get('total', 0):.2f}")
    lines.append(f"  平均值: {stats.get('average', 0):.2f}")
    lines.append(f"  最大值: {stats.get('max_name', '')} = {stats.get('max_value', 0):.2f}")
    lines.append(f"  最小值: {stats.get('min_name', '')} = {stats.get('min_value', 0):.2f}")

    # 类别汇总
    cat_totals = stats.get("category_totals", {})
    if cat_totals:
        lines.append("")
        lines.append("--- 类别汇总 ---")
        for cat, val in sorted(cat_totals.items(), key=lambda x: x[1], reverse=True):
            lines.append(f"  {cat}: {val:.2f}")

    return "\n".join(lines)


def generate_output(
    data_points: List[DataPoint],
    output_format: str,
    confidence: float,
) -> Tuple[str, str]:
    """
    生成最终输出。

    参数:
        data_points: 数据点列表
        output_format: 输出格式 (json/table/text/csv)
        confidence: 置信度 (0-1)

    返回:
        (输出内容, 置信度标注)

    错误码:
        E007 不支持的输出格式
    """
    stats = compute_statistics(data_points)

    # 置信度标注
    if confidence >= CONFIDENCE_HIGH:
        confidence_note = ""
    elif confidence >= CONFIDENCE_MEDIUM:
        confidence_note = "\n\n[建议复核] 部分数据可能存在偏差，请人工确认关键结果。"
    else:
        confidence_note = f"\n\n[需核实] 数据解析置信度较低（{confidence:.0%}），请检查输入数据。"

    # 按格式生成内容
    if output_format == "json":
        output_data = {
            "items": [dp.to_dict() for dp in data_points],
            "statistics": stats,
            "confidence": round(confidence, 2),
        }
        content = json.dumps(output_data, ensure_ascii=False, indent=2)
    elif output_format == "table":
        content = format_as_table(data_points)
    elif output_format == "text":
        content = format_as_text(data_points, stats)
    elif output_format == "csv":
        content = format_as_csv(data_points)
    else:
        raise DashbrewError("E007")

    return content, confidence_note


def process_batch(inputs: List[str], output_format: str) -> List[Dict[str, Any]]:
    """
    批量处理多个输入。

    参数:
        inputs: 输入列表
        output_format: 输出格式

    返回:
        处理结果列表

    错误码:
        E008 批量处理中断
    """
    results = []

    for i, user_input in enumerate(inputs):
        try:
            data_points, confidence, input_type = auto_detect_and_parse(user_input)
            content, note = generate_output(data_points, output_format, confidence)
            results.append({
                "index": i + 1,
                "input_type": input_type,
                "success": True,
                "content": content,
                "confidence_note": note,
                "item_count": len(data_points),
            })
        except DashbrewError as e:
            results.append({
                "index": i + 1,
                "success": False,
                "error_code": e.code,
                "error_message": str(e),
            })

    # 如果有失败项，抛出批量处理中断错误
    failed = [r for r in results if not r.get("success")]
    if failed:
        raise DashbrewError("E008", details={"failed_items": failed})

    return results


# ============================================================
# 自定义异常
# ============================================================

class DashbrewError(Exception):
    """Dashbrew 自定义异常。"""

    def __init__(self, code: str, details: Optional[Dict[str, Any]] = None):
        self.code = code
        self.details = details or {}
        message = ERROR_MESSAGES.get(code, f"未知错误 ({code})")
        if details and "failed_items" in details:
            failed_count = len(details["failed_items"])
            message += f" 共 {failed_count} 项处理失败。"
        super().__init__(message)


# ============================================================
# 自检模块
# ============================================================

def run_selftest() -> int:
    """
    运行内置自检（离线，不依赖外部文件或网络）。

    使用硬编码样例数据验证核心逻辑。

    返回:
        0 表示全部通过，1 表示存在失败项
    """
    print("=" * 60)
    print("dashbrew 自检程序")
    print("=" * 60)

    failures = 0

    # --- 测试1: 键值对解析 ---
    print("\n[测试1] 键值对解析")
    try:
        data_points, confidence = parse_key_value_input(SELFTEST_RAW_INPUT)
        assert len(data_points) == 5, f"期望5条数据，实际{len(data_points)}"
        assert confidence > 0.8, f"置信度应较高，实际{confidence:.2f}"
        # 验证数值范围（宽松断言）
        total = sum(dp.value for dp in data_points)
        assert total > 500, f"总和应大于500，实际{total}"
        assert total < 1000, f"总和应小于1000，实际{total}"
        print(f"  ✓ 通过 (5条数据, 置信度={confidence:.2f}, 总和={total})")
    except (AssertionError, DashbrewError) as e:
        failures += 1
        print(f"  ✗ 失败: {e}")

    # --- 测试2: JSON 解析 ---
    print("\n[测试2] JSON 解析")
    try:
        json_input = json.dumps(SELFTEST_DATA, ensure_ascii=False)
        data_points, confidence = parse_json_input(json_input)
        assert len(data_points) == 5, f"期望5条数据，实际{len(data_points)}"
        assert confidence >= 0.9, f"JSON解析置信度应为1.0，实际{confidence}"
        # 验证类别保留
        categories = {dp.category for dp in data_points}
        assert "电子" in categories, "应包含'电子'类别"
        assert "家居" in categories, "应包含'家居'类别"
        print(f"  ✓ 通过 (5条数据, 置信度={confidence:.2f}, 类别={sorted(categories)})")
    except (AssertionError, DashbrewError) as e:
        failures += 1
        print(f"  ✗ 失败: {e}")

    # --- 测试3: 统计计算 ---
    print("\n[测试3] 统计计算")
    try:
        # 转换为 DataPoint 对象
        data_points = []
        for item in SELFTEST_DATA:
            data_points.append(DataPoint(
                name=item["name"],
                value=item["value"],
                category=item["category"]
            ))
        
        stats = compute_statistics(data_points)
        assert stats["count"] == 5, f"计数应为5，实际{stats['count']}"
        assert stats["total"] > 500, f"总和应大于500，实际{stats['total']}"
        assert stats["total"] < 1000, f"总和应小于1000，实际{stats['total']}"
        assert stats["max_value"] > 200, f"最大值应大于200，实际{stats['max_value']}"
        assert stats["min_value"] < 100, f"最小值应小于100，实际{stats['min_value']}"
        assert len(stats["categories"]) >= 2, f"应至少有2个类别，实际{len(stats['categories'])}"
        print(f"  ✓ 通过 (count={stats['count']}, total={stats['total']:.2f}, "
              f"max={stats['max_name']}={stats['max_value']:.2f})")
    except (AssertionError, DashbrewError) as e:
        failures += 1
        print(f"  ✗ 失败: {e}")

    # --- 测试4: 表格输出 ---
    print("\n[测试4] 表格输出")
    try:
        # 转换为 DataPoint 对象
        data_points = []
        for item in SELFTEST_DATA:
            data_points.append(DataPoint(
                name=item["name"],
                value=item["value"],
                category=item["category"]
            ))
        
        table = format_as_table(data_points)
        assert "名称" in table, "表头应包含'名称'"
        assert "数值" in table, "表头应包含'数值'"
        assert "商品A" in table, "应包含'商品A'"
        assert "商品E" in table, "应包含'商品E'"
        lines = table.split("\n")
        assert len(lines) >= 7, f"表格至少7行，实际{len(lines)}行"
        print(f"  ✓ 通过 ({len(lines)}行)")
    except (AssertionError, DashbrewError) as e:
        failures += 1
        print(f"  ✗ 失败: {e}")

    # --- 测试5: CSV 输出 ---
    print("\n[测试5] CSV 输出")
    try:
        # 转换为 DataPoint 对象
        data_points = []
        for item in SELFTEST_DATA:
            data_points.append(DataPoint(
                name=item["name"],
                value=item["value"],
                category=item["category"]
            ))
        
        csv_text = format_as_csv(data_points)
        lines = csv_text.strip().split("\n")
        assert len(lines) == 6, f"CSV应有6行(含表头)，实际{len(lines)}行"
        assert lines[0] == "名称,数值,类别", f"表头不正确: {lines[0]}"
        assert "商品A" in csv_text, "应包含'商品A'"
        print(f"  ✓ 通过 ({len(lines)}行)")
    except (AssertionError, DashbrewError) as e:
        failures += 1
        print(f"  ✗ 失败: {e}")

    # --- 测试6: 完整输出生成 (JSON) ---
    print("\n[测试6] JSON 输出生成")
    try:
        # 转换为 DataPoint 对象
        data_points = []
        for item in SELFTEST_DATA:
            data_points.append(DataPoint(
                name=item["name"],
                value=item["value"],
                category=item["category"]
            ))
        
        content, note = generate_output(data_points, "json", 1.0)
        parsed = json.loads(content)
        assert len(parsed["items"]) == 5, "items应为5条"
        assert parsed["statistics"]["count"] == 5, "统计计数应为5"
        assert note == "", "高置信度不应有标注"
        print(f"  ✓ 通过 (JSON输出, {len(parsed['items'])}条)")
    except (AssertionError, DashbrewError) as e:
        failures += 1
        print(f"  ✗ 失败: {e}")

    # --- 测试7: 错误处理 ---
    print("\n[测试7] 错误处理")
    try:
        # 空输入
        try:
            parse_key_value_input("")
            failures += 1
            print("  ✗ 失败: 空输入应抛出E001")
        except DashbrewError as e:
            assert e.code == "E001", f"错误码应为E001，实际{e.code}"
            print(f"  ✓ E001 空输入处理正确")

        # 格式错误
        try:
            parse_key_value_input("这是一段没有分隔符的文本")
            failures += 1
            print("  ✗ 失败: 格式错误应抛出E003")
        except DashbrewError as e:
            assert e.code == "E003", f"错误码应为E003，实际{e.code}"
            print(f"  ✓ E003 格式错误处理正确")

    except (AssertionError, DashbrewError) as e:
        failures += 1
        print(f"  ✗ 失败: {e}")

    # --- 汇总 ---
    print("\n" + "=" * 60)
    if failures == 0:
        print("自检结果: 全部通过 ✓")
        return 0
    else:
        print(f"自检结果: {failures} 项失败 ✗")
        return 1


# ============================================================
# 主入口
# ============================================================

def main() -> int:
    """
    主函数。

    返回:
        退出码 (0 成功, 非0 失败)
    """
    parser = argparse.ArgumentParser(
        description="dashbrew - 数据可视化 TUI 仪表板构建器",
        epilog="示例: python main.py --input '商品A:100;商品B:200' --format table",
    )
    parser.add_argument(
        "--input", "-i",
        help="输入内容：文本、JSON、或文件路径",
    )
    parser.add_argument(
        "--format", "-f",
        choices=["json", "table", "text", "csv"],
        default="table",
        help="输出格式 (默认: table)",
    )
    parser.add_argument(
        "--batch",
        action="store_true",
        help="批量模式：输入用分号分隔多个数据源",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检（离线）",
    )

    try:
        args = parser.parse_args()
    except SystemExit:
        return 1
    except Exception:
        print(f"E010: {ERROR_MESSAGES['E010']}")
        return 1

    # 自检模式
    if args.selftest:
        return run_selftest()

    # 检查必要参数
    if not args.input:
        print(f"E001: {ERROR_MESSAGES['E001']}")
        return 1

    try:
        if args.batch:
            # 批量模式：输入用分号分隔
            inputs = [s.strip() for s in args.input.split(";") if s.strip()]
            if not inputs:
                raise DashbrewError("E001")
            results = process_batch(inputs, args.format)
            print(f"批量处理完成，共 {len(results)} 项：")
            for r in results:
                if r["success"]:
                    print(f"\n--- 第 {r['index']} 项 ({r['input_type']}, {r['item_count']}条) ---")
                    print(r["content"])
                    if r["confidence_note"]:
                        print(r["confidence_note"])
                else:
                    print(f"\n--- 第 {r['index']} 项 失败 ({r['error_code']}) ---")
                    print(r["error_message"])
        else:
            # 单次处理
            data_points, confidence, input_type = auto_detect_and_parse(args.input)
            content, note = generate_output(data_points, args.format, confidence)
            print(content)
            if note:
                print(note)

        return 0

    except DashbrewError as e:
        print(f"{e.code}: {e}")
        return 1
    except Exception as e:
        # 未预期的异常
        print(f"E009: {ERROR_MESSAGES['E009']} ({e})")
        return 1


if __name__ == "__main__":
    sys.exit(main())
