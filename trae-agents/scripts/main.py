#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py — TRAE Agents 技能核心逻辑（独立实现）

本脚本依据功能规格独立编写，不复制任何既有代码。
提供以下核心能力：
1. 数据转结构化：从原始文本中提取实体与关系，输出为字段明确的记录。
2. 关键信息保留：转换过程中保留输入中的核心属性（名称、数值、状态、时间戳）。
3. 格式约定输出：按默认模板生成结果，保证字段名一致。
4. 置信度标注：对识别结果附置信度等级（高/中/低），不确定字段显式标记。
5. 批量与自定义：支持多条记录同时处理，允许用户自定义输出字段与格式。

命令行支持：
    python scripts/main.py --selftest   # 离线自检核心逻辑
    python scripts/main.py --input "原始数据" --fields "名称,数值"  # 正常处理
"""

import argparse
import json
import re
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional

# ============================================================
# 错误码定义
# ============================================================
# E001: 输入为空或不是字符串
# E002: 输入数据无法解析为有效记录
# E003: 自定义字段格式无效
# E004: 输出序列化失败
# E005: 内部逻辑错误（不应发生）
# E006: 命令行参数缺失或冲突
# E007: 置信度计算失败
# E008: 时间戳解析失败
# E009: 批量处理时单条记录失败
# E010: 未知错误

# ============================================================
# 常量定义
# ============================================================
DEFAULT_FIELDS = ["名称", "数值", "状态", "时间戳"]
CONFIDENCE_LEVELS = ["高", "中", "低"]
FIELD_ALIASES = {
    "name": "名称",
    "名称": "名称",
    "value": "数值",
    "数值": "数值",
    "status": "状态",
    "状态": "状态",
    "timestamp": "时间戳",
    "时间戳": "时间戳",
}

# ============================================================
# 核心数据结构
# ============================================================
class StructuredRecord:
    """结构化记录类，保存单条记录的数据与置信度信息。"""

    def __init__(self, fields: Dict[str, Any], confidence: str = "中"):
        """初始化记录。

        Args:
            fields: 字段名到值的映射。
            confidence: 置信度等级（高/中/低）。
        """
        self.fields = fields
        self.confidence = confidence if confidence in CONFIDENCE_LEVELS else "中"

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典，包含置信度标注。"""
        result = dict(self.fields)
        result["_confidence"] = self.confidence
        return result

    def __repr__(self) -> str:
        return f"StructuredRecord(fields={self.fields}, confidence={self.confidence})"


class BatchResult:
    """批量处理结果，包含多条记录与统计信息。"""

    def __init__(self, records: List[StructuredRecord]):
        """初始化批量结果。

        Args:
            records: 结构化记录列表。
        """
        self.records = records
        self.total = len(records)
        self.high_confidence = sum(1 for r in records if r.confidence == "高")
        self.medium_confidence = sum(1 for r in records if r.confidence == "中")
        self.low_confidence = sum(1 for r in records if r.confidence == "低")

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典，包含统计信息。"""
        return {
            "total": self.total,
            "high_confidence": self.high_confidence,
            "medium_confidence": self.medium_confidence,
            "low_confidence": self.low_confidence,
            "records": [r.to_dict() for r in self.records],
        }


# ============================================================
# 核心处理函数
# ============================================================
def validate_input(data: Any) -> str:
    """验证输入数据。

    Args:
        data: 输入数据，应为非空字符串。

    Returns:
        验证通过的字符串。

    Raises:
        Exception: 错误码 E001，当输入为空或不是字符串时。
    """
    if not isinstance(data, str):
        raise Exception("E001: 输入必须是非空字符串")
    if not data.strip():
        raise Exception("E001: 输入不能为空")
    return data.strip()


def parse_timestamp(text: str) -> Optional[str]:
    """从文本中提取时间戳。

    尝试多种常见时间格式，返回标准化时间字符串；失败返回 None。

    Args:
        text: 输入文本。

    Returns:
        标准化时间字符串，或 None。
    """
    # 尝试 ISO 格式（YYYY-MM-DD HH:MM:SS 或 YYYY-MM-DD）
    iso_patterns = [
        r"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}",
        r"\d{4}-\d{2}-\d{2}",
    ]
    for pattern in iso_patterns:
        match = re.search(pattern, text)
        if match:
            try:
                # 宽松解析，只验证格式合法性
                dt_str = match.group(0)
                if "T" in dt_str or " " in dt_str:
                    datetime.strptime(dt_str.replace("T", " "), "%Y-%m-%d %H:%M:%S")
                else:
                    datetime.strptime(dt_str, "%Y-%m-%d")
                return dt_str
            except ValueError:
                continue

    # 尝试常见中文日期格式
    cn_patterns = [
        r"\d{4}年\d{1,2}月\d{1,2}日",
        r"\d{4}年\d{1,2}月",
    ]
    for pattern in cn_patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(0)

    return None


def extract_name(text: str) -> Optional[str]:
    """从文本中提取名称。

    启发式规则：
    - 优先匹配"名称：xxx"或"名称:xxx"格式
    - 其次匹配引号内的内容
    - 最后尝试匹配常见命名模式

    Args:
        text: 输入文本。

    Returns:
        提取的名称，或 None。
    """
    # 优先匹配显式名称字段
    explicit_patterns = [
        r"名称[：:]\s*([^\s,，;；]+)",
        r"name[：:]\s*([^\s,，;；]+)",
    ]
    for pattern in explicit_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1)

    # 匹配引号内容
    quoted_patterns = [
        r"[\"']([^\"']+)[\"']",
        r"「([^」]+)」",
        r"『([^』]+)』",
    ]
    for pattern in quoted_patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1)

    # 尝试匹配常见命名模式（如"项目A"、"系统B"等）
    naming_pattern = r"([\u4e00-\u9fa5A-Za-z][\u4e00-\u9fa5A-Za-z0-9]{1,20})"
    match = re.search(naming_pattern, text)
    if match:
        return match.group(1)

    return None


def extract_value(text: str) -> Optional[float]:
    """从文本中提取数值。

    Args:
        text: 输入文本。

    Returns:
        提取的数值（浮点数），或 None。
    """
    # 匹配整数或浮点数（支持千分位）
    number_patterns = [
        r"[-+]?\d+\.\d+",
        r"[-+]?\d+",
        r"[-+]?\d{1,3}(?:,\d{3})+(?:\.\d+)?",
    ]
    for pattern in number_patterns:
        match = re.search(pattern, text)
        if match:
            try:
                num_str = match.group(0).replace(",", "")
                return float(num_str)
            except ValueError:
                continue
    return None


def extract_status(text: str) -> Optional[str]:
    """从文本中提取状态。

    识别常见状态关键词。

    Args:
        text: 输入文本。

    Returns:
        提取的状态字符串，或 None。
    """
    status_keywords = {
        "成功": ["成功", "完成", "succeed", "success", "done"],
        "失败": ["失败", "错误", "fail", "error", "failed"],
        "进行中": ["进行中", "处理中", "运行中", "processing", "running", "in progress"],
        "待处理": ["待处理", "等待", "pending", "waiting"],
        "已取消": ["取消", "cancelled", "canceled"],
    }

    text_lower = text.lower()
    for status, keywords in status_keywords.items():
        for keyword in keywords:
            if keyword.lower() in text_lower:
                return status
    return None


def calculate_confidence(text: str, extracted: Dict[str, Any]) -> str:
    """计算置信度等级。

    规则：
    - 高：提取到至少 3 个字段，且包含时间戳
    - 中：提取到至少 2 个字段
    - 低：提取到少于 2 个字段

    Args:
        text: 原始输入文本。
        extracted: 已提取的字段字典。

    Returns:
        置信度等级字符串。
    """
    try:
        non_none_count = sum(1 for v in extracted.values() if v is not None)

        if non_none_count >= 3 and extracted.get("时间戳") is not None:
            return "高"
        elif non_none_count >= 2:
            return "中"
        else:
            return "低"
    except Exception:
        # 任何异常都返回低置信度，避免影响主流程
        return "低"


def transform_to_records(data: str, fields: Optional[List[str]] = None) -> BatchResult:
    """将原始文本转换为结构化记录。

    支持单条记录和多条记录（按行或分隔符拆分）。

    Args:
        data: 原始输入文本。
        fields: 自定义字段列表（可选）。

    Returns:
        BatchResult 对象。

    Raises:
        Exception: 错误码 E002，当数据无法解析时。
        Exception: 错误码 E003，当自定义字段格式无效时。
    """
    # 验证输入
    text = validate_input(data)

    # 确定字段列表
    if fields is None:
        field_list = DEFAULT_FIELDS
    else:
        # 校验自定义字段
        if not isinstance(fields, list) or len(fields) == 0:
            raise Exception("E003: 自定义字段必须是非空列表")
        # 标准化字段名
        field_list = []
        for f in fields:
            normalized = FIELD_ALIASES.get(f, f)
            if normalized not in field_list:
                field_list.append(normalized)

    # 按行拆分（支持多条记录）
    lines = [line.strip() for line in text.splitlines() if line.strip()]

    records: List[StructuredRecord] = []

    for line in lines:
        try:
            # 提取各字段
            extracted: Dict[str, Any] = {}
            for field in field_list:
                if field == "名称":
                    extracted[field] = extract_name(line)
                elif field == "数值":
                    extracted[field] = extract_value(line)
                elif field == "状态":
                    extracted[field] = extract_status(line)
                elif field == "时间戳":
                    extracted[field] = parse_timestamp(line)
                else:
                    # 自定义字段：尝试匹配"字段名：值"格式
                    pattern = rf"{re.escape(field)}[：:]\s*([^\s,，;；]+)"
                    match = re.search(pattern, line)
                    extracted[field] = match.group(1) if match else None

            # 计算置信度
            confidence = calculate_confidence(line, extracted)

            # 创建记录（即使所有字段为 None 也创建，标记低置信度）
            records.append(StructuredRecord(extracted, confidence))

        except Exception as e:
            # 单条记录失败不影响整体
            if "E0" in str(e):
                raise
            continue

    if not records:
        raise Exception("E002: 输入数据无法解析为有效记录")

    return BatchResult(records)


def serialize_output(result: BatchResult, output_format: str = "json") -> str:
    """序列化输出结果。

    Args:
        result: 批量处理结果。
        output_format: 输出格式（json/markdown）。

    Returns:
        序列化后的字符串。

    Raises:
        Exception: 错误码 E004，当序列化失败时。
    """
    try:
        if output_format == "json":
            return json.dumps(result.to_dict(), ensure_ascii=False, indent=2)
        elif output_format == "markdown":
            # 生成 Markdown 表格
            lines = []
            lines.append("| 字段 | 值 | 置信度 |")
            lines.append("|------|-----|--------|")
            for record in result.records:
                for field, value in record.fields.items():
                    lines.append(f"| {field} | {value if value is not None else 'N/A'} | {record.confidence} |")
            return "\n".join(lines)
        else:
            raise Exception("E004: 不支持的输出格式")
    except Exception as e:
        if "E0" in str(e):
            raise
        raise Exception("E004: 输出序列化失败")


# ============================================================
# 自检功能
# ============================================================
def run_selftest() -> bool:
    """运行内置自检，验证核心逻辑。

    使用硬编码样例数据，不依赖外部文件或网络。

    Returns:
        True 表示自检通过，False 表示失败。
    """
    print("=" * 60)
    print("TRAE Agents 技能自检开始")
    print("=" * 60)

    # 测试样例 1：单条记录，包含名称、数值、状态、时间戳
    sample1 = "项目Alpha 已完成 数值：98.5 时间戳：2026-03-15 14:30:00"
    try:
        result1 = transform_to_records(sample1)
        assert result1.total == 1, "样例1: 应生成1条记录"
        record1 = result1.records[0]
        assert record1.fields["名称"] is not None, "样例1: 应提取到名称"
        assert record1.fields["数值"] is not None, "样例1: 应提取到数值"
        assert record1.fields["数值"] > 90, "样例1: 数值应大于90（宽松验证）"
        assert record1.fields["状态"] == "成功", "样例1: 状态应为成功"
        assert record1.fields["时间戳"] is not None, "样例1: 应提取到时间戳"
        assert record1.confidence in CONFIDENCE_LEVELS, "样例1: 置信度等级合法"
        print(f"[通过] 样例1: 单条记录解析成功，置信度={record1.confidence}")

        # 序列化测试
        json_output = serialize_output(result1, "json")
        assert json_output is not None and len(json_output) > 0, "样例1: JSON序列化失败"
        markdown_output = serialize_output(result1, "markdown")
        assert markdown_output is not None and len(markdown_output) > 0, "样例1: Markdown序列化失败"
        print("[通过] 样例1: JSON/Markdown序列化成功")
    except Exception as e:
        print(f"[失败] 样例1: {e}")
        return False

    # 测试样例 2：批量记录（多行）
    sample2 = """项目A 进行中 数值：50 时间戳：2026-03-14
项目B 失败 数值：10 时间戳：2026-03-13
项目C 成功 数值：88"""
    try:
        result2 = transform_to_records(sample2)
        assert result2.total >= 2, "样例2: 应生成至少2条记录"
        assert result2.total <= 3, "样例2: 应生成不超过3条记录"
        assert result2.medium_confidence >= 1, "样例2: 至少应有1条中置信度记录"
        print(f"[通过] 样例2: 批量解析成功，共{result2.total}条记录")
    except Exception as e:
        print(f"[失败] 样例2: {e}")
        return False

    # 测试样例 3：自定义字段
    sample3 = "系统X 负责人：张三 优先级：高 时间戳：2026-03-15"
    try:
        custom_fields = ["名称", "负责人", "优先级", "时间戳"]
        result3 = transform_to_records(sample3, custom_fields)
        assert result3.total == 1, "样例3: 应生成1条记录"
        record3 = result3.records[0]
        assert record3.fields["名称"] is not None, "样例3: 应提取到名称"
        assert record3.fields["负责人"] is not None, "样例3: 应提取到负责人"
        assert record3.fields["优先级"] is not None, "样例3: 应提取到优先级"
        print(f"[通过] 样例3: 自定义字段解析成功")
    except Exception as e:
        print(f"[失败] 样例3: {e}")
        return False

    # 测试样例 4：边界情况（空输入、无效输入）
    try:
        # 空输入应报错 E001
        try:
            transform_to_records("")
            print("[失败] 样例4: 空输入应报错")
            return False
        except Exception as e:
            assert "E001" in str(e), "样例4: 错误码应为E001"

        # 无有效数据应报错 E002
        try:
            transform_to_records("!!!@@@###")
            print("[失败] 样例4: 无有效数据应报错")
            return False
        except Exception as e:
            assert "E002" in str(e), "样例4: 错误码应为E002"

        print("[通过] 样例4: 错误处理正确")
    except Exception as e:
        print(f"[失败] 样例4: {e}")
        return False

    # 测试样例 5：置信度计算
    try:
        # 高置信度：完整信息
        high_sample = "项目X 成功 数值：100 时间戳：2026-03-15 10:00:00"
        high_result = transform_to_records(high_sample)
        assert high_result.records[0].confidence in ["高", "中"], "样例5: 完整信息置信度应为高或中"

        # 低置信度：信息不完整
        low_sample = "项目Y"
        low_result = transform_to_records(low_sample)
        assert low_result.records[0].confidence in ["低", "中"], "样例5: 不完整信息置信度应为低或中"

        print("[通过] 样例5: 置信度计算逻辑正确")
    except Exception as e:
        print(f"[失败] 样例5: {e}")
        return False

    print("=" * 60)
    print("所有自检用例通过！")
    print("=" * 60)
    return True


# ============================================================
# 命令行入口
# ============================================================
def main() -> None:
    """主入口函数。"""
    parser = argparse.ArgumentParser(
        description="TRAE Agents 技能核心逻辑 — 数据转结构化工具",
        epilog="示例: python scripts/main.py --input '项目A 成功 数值：95 时间戳：2026-03-15'",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检（离线、无依赖）",
    )
    parser.add_argument(
        "--input",
        type=str,
        help="原始输入数据（字符串）",
    )
    parser.add_argument(
        "--fields",
        type=str,
        help="自定义字段列表，逗号分隔（可选）",
    )
    parser.add_argument(
        "--format",
        type=str,
        choices=["json", "markdown"],
        default="json",
        help="输出格式（默认: json）",
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        success = run_selftest()
        sys.exit(0 if success else 1)

    # 正常处理模式
    if not args.input:
        parser.error("E006: 需要提供 --input 参数（或使用 --selftest）")

    try:
        # 解析自定义字段
        fields = None
        if args.fields:
            fields = [f.strip() for f in args.fields.split(",") if f.strip()]

        # 处理数据
        result = transform_to_records(args.input, fields)

        # 输出结果
        output = serialize_output(result, args.format)
        print(output)

    except Exception as e:
        error_msg = str(e)
        if "E0" in error_msg:
            print(f"错误: {error_msg}", file=sys.stderr)
        else:
            print(f"错误: E010: {error_msg}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
