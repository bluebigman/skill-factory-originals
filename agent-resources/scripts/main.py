#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
agent-resources 技能实现脚本（全新独立实现）

功能：将任意数据源转为结构化结果，支持批量处理与置信度标注。
本脚本为 clean-room 实现，仅依据功能规格独立编写。

用法示例：
    python scripts/main.py --selftest          # 离线自检
    python scripts/main.py --help              # 查看帮助
"""

import argparse
import json
import sys
from typing import Any, Dict, List, Optional, Union

# 错误码定义
ERROR_CODES = {
    "E001": "参数无效或缺失",
    "E002": "输入数据格式不支持",
    "E003": "数据清洗失败",
    "E004": "转换失败",
    "E005": "批量处理中断",
    "E006": "输出序列化失败",
    "E007": "自检断言失败",
    "E008": "内部逻辑错误",
    "E009": "资源未找到",
    "E010": "未知错误",
}


class ResourceTransformError(Exception):
    """资源转换异常基类，携带错误码。"""

    def __init__(self, code: str, message: str = ""):
        self.code = code
        self.message = message or ERROR_CODES.get(code, ERROR_CODES["E010"])
        super().__init__(f"[{self.code}] {self.message}")


# ---------------------------------------------------------------------------
# 核心数据结构
# ---------------------------------------------------------------------------

class StructuredRecord:
    """结构化记录：包含数据内容、来源标识与置信度。"""

    def __init__(self, data: Dict[str, Any], source: str = "", confidence: float = 1.0):
        self.data = data
        self.source = source
        self.confidence = confidence

    def to_dict(self) -> Dict[str, Any]:
        """转换为可序列化字典。"""
        return {
            "data": self.data,
            "source": self.source,
            "confidence": self.confidence,
        }

    @classmethod
    def from_dict(cls, obj: Dict[str, Any]) -> "StructuredRecord":
        """从字典构建记录。"""
        return cls(
            data=obj.get("data", {}),
            source=obj.get("source", ""),
            confidence=obj.get("confidence", 1.0),
        )


# ---------------------------------------------------------------------------
# 数据清洗与归一化
# ---------------------------------------------------------------------------

def clean_value(value: Any, key: str = "") -> Any:
    """
    清洗单个值：去除空白、归一化类型。

    规则：
    - 字符串：去除首尾空白，空串转为 None
    - 数字：保持原样
    - 布尔：保持原样
    - None：保持
    """
    try:
        if value is None:
            return None
        if isinstance(value, str):
            cleaned = value.strip()
            return cleaned if cleaned else None
        if isinstance(value, (int, float, bool)):
            return value
        if isinstance(value, (list, dict)):
            return value
        return value
    except Exception as exc:
        raise ResourceTransformError("E003", f"清洗字段 {key} 失败: {exc}") from exc


def clean_record(record: Dict[str, Any]) -> Dict[str, Any]:
    """清洗整条记录。"""
    if not isinstance(record, dict):
        raise ResourceTransformError("E003", "记录必须为字典类型")
    return {k: clean_value(v, k) for k, v in record.items()}


# ---------------------------------------------------------------------------
# 格式归一化（将不同输入格式转为统一结构化记录）
# ---------------------------------------------------------------------------

def normalize_json(raw: Union[Dict, List]) -> List[Dict[str, Any]]:
    """归一化 JSON 输入为记录列表。"""
    if isinstance(raw, dict):
        return [raw]
    if isinstance(raw, list):
        return [item for item in raw if isinstance(item, dict)]
    raise ResourceTransformError("E002", "JSON 顶层必须是对象或数组")


def parse_csv_text(text: str) -> List[Dict[str, Any]]:
    """解析 CSV 文本（简单实现，支持逗号分隔与引号）。"""
    import csv
    from io import StringIO

    try:
        reader = csv.DictReader(StringIO(text))
        return [dict(row) for row in reader]
    except Exception as exc:
        raise ResourceTransformError("E002", f"CSV 解析失败: {exc}") from exc


def normalize_input(data: Union[str, Dict, List]) -> List[Dict[str, Any]]:
    """
    将输入数据归一化为记录字典列表。

    支持：
    - 字典/列表（直接使用）
    - JSON 字符串（自动解析）
    - CSV 文本（自动检测）
    """
    if isinstance(data, (dict, list)):
        return normalize_json(data)

    if isinstance(data, str):
        stripped = data.strip()
        if not stripped:
            raise ResourceTransformError("E002", "输入文本为空")

        # 尝试 JSON 解析
        try:
            parsed = json.loads(stripped)
            return normalize_json(parsed)
        except json.JSONDecodeError:
            pass

        # 尝试 CSV 解析（包含逗号或换行）
        if "," in stripped or "\n" in stripped:
            return parse_csv_text(stripped)

        # 单行文本作为单字段记录
        return [{"text": stripped}]

    raise ResourceTransformError("E002", f"不支持的数据类型: {type(data).__name__}")


# ---------------------------------------------------------------------------
# 置信度标注
# ---------------------------------------------------------------------------

def estimate_confidence(record: Dict[str, Any]) -> float:
    """
    基于字段完整度估算置信度（0.5 ~ 1.0）。

    规则：
    - 空记录：0.5
    - 字段越多、非空字段越多，置信度越高
    """
    if not record:
        return 0.5

    total_fields = len(record)
    non_empty = sum(1 for v in record.values() if v is not None and str(v).strip() != "")

    if total_fields == 0:
        return 0.5

    ratio = non_empty / total_fields
    # 宽松映射：比率越高置信度越高，但保留下限 0.5
    return round(0.5 + 0.5 * ratio, 2)


# ---------------------------------------------------------------------------
# 核心转换流程
# ---------------------------------------------------------------------------

def transform_to_records(
    data: Union[str, Dict, List],
    source: str = "unknown",
    auto_confidence: bool = True,
    confidence: Optional[float] = None,
) -> List[StructuredRecord]:
    """
    将任意数据源转换为结构化记录列表。

    参数：
        data: 输入数据（字典、列表、JSON 字符串、CSV 文本）
        source: 来源标识
        auto_confidence: 是否自动估算置信度
        confidence: 手动指定置信度（覆盖自动估算）

    返回：
        StructuredRecord 列表
    """
    try:
        raw_records = normalize_input(data)
        records = []

        for raw in raw_records:
            # 清洗
            cleaned = clean_record(raw)

            # 置信度
            if not auto_confidence and confidence is not None:
                conf = confidence
            else:
                conf = estimate_confidence(cleaned)

            records.append(StructuredRecord(data=cleaned, source=source, confidence=conf))

        return records
    except ResourceTransformError:
        raise
    except Exception as exc:
        raise ResourceTransformError("E004", f"转换失败: {exc}") from exc


def batch_transform(
    items: List[Union[str, Dict, List]],
    source: str = "batch",
    auto_confidence: bool = True,
) -> List[StructuredRecord]:
    """批量转换多个数据项。"""
    try:
        all_records: List[StructuredRecord] = []
        for idx, item in enumerate(items):
            try:
                records = transform_to_records(
                    item, source=f"{source}#{idx}", auto_confidence=auto_confidence
                )
                all_records.extend(records)
            except ResourceTransformError as exc:
                # 单条失败不中断整个批次
                all_records.append(
                    StructuredRecord(
                        data={"error": exc.code, "message": exc.message},
                        source=f"{source}#{idx}",
                        confidence=0.0,
                    )
                )
        return all_records
    except Exception as exc:
        raise ResourceTransformError("E005", f"批量处理异常: {exc}") from exc


# ---------------------------------------------------------------------------
# 输出序列化
# ---------------------------------------------------------------------------

def serialize_output(records: List[StructuredRecord], format: str = "json") -> str:
    """
    将记录序列化为指定格式。

    支持格式：json（默认）、compact
    """
    try:
        payload = [r.to_dict() for r in records]

        if format == "json":
            return json.dumps(payload, ensure_ascii=False, indent=2)
        if format == "compact":
            return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        raise ResourceTransformError("E001", f"不支持的输出格式: {format}")
    except ResourceTransformError:
        raise
    except Exception as exc:
        raise ResourceTransformError("E006", f"序列化失败: {exc}") from exc


# ---------------------------------------------------------------------------
# 自检模块（离线，硬编码样例数据）
# ---------------------------------------------------------------------------

def _run_selftest() -> int:
    """
    执行内置自检，验证核心逻辑。

    使用宽松阈值（大小比较/区间判断），不依赖精确边界值。
    """
    failures = 0

    def check(condition: bool, name: str) -> None:
        nonlocal failures
        if not condition:
            print(f"  ✗ 失败: {name}")
            failures += 1
        else:
            print(f"  ✓ 通过: {name}")

    print("开始自检 agent-resources ...")

    # --- 用例 1: JSON 对象输入 ---
    print("[用例 1] 字典输入")
    try:
        records = transform_to_records(
            {"name": "Alice", "age": 30, "city": "北京"}, source="test1"
        )
        check(len(records) == 1, "单条记录生成")
        check(records[0].data.get("name") == "Alice", "字段值正确")
        check(0.5 <= records[0].confidence <= 1.0, "置信度在合理区间")
    except Exception as exc:
        check(False, f"异常: {exc}")

    # --- 用例 2: JSON 数组输入 ---
    print("[用例 2] 列表输入")
    try:
        records = transform_to_records(
            [{"a": 1}, {"a": 2, "b": "x"}], source="test2"
        )
        check(len(records) == 2, "两条记录生成")
        check(records[0].confidence >= 0.5, "首条置信度下限")
        check(records[1].confidence >= records[0].confidence, "字段多则置信度不低")
    except Exception as exc:
        check(False, f"异常: {exc}")

    # --- 用例 3: JSON 字符串 ---
    print("[用例 3] JSON 字符串")
    try:
        records = transform_to_records('{"x": 1, "y": "test"}', source="test3")
        check(len(records) == 1, "JSON 字符串解析成功")
        check(records[0].data.get("y") == "test", "字符串字段正确")
    except Exception as exc:
        check(False, f"异常: {exc}")

    # --- 用例 4: CSV 文本 ---
    print("[用例 4] CSV 文本")
    try:
        csv_text = "name,age\nBob,25\nCarol,31"
        records = transform_to_records(csv_text, source="test4")
        check(len(records) == 2, "CSV 两行解析")
        check(records[0].data.get("name") == "Bob", "CSV 首行字段")
        check(records[1].data.get("age") == "31", "CSV 次行字段（字符串）")
    except Exception as exc:
        check(False, f"异常: {exc}")

    # --- 用例 5: 批量处理 ---
    print("[用例 5] 批量处理")
    try:
        items = [{"id": 1}, {"id": 2, "note": "ok"}, "not-json"]
        records = batch_transform(items, source="batch-test")
        # 前两项正常，第三项转成错误记录
        check(len(records) >= 2, "批量至少产生两条记录")
        check(records[0].confidence >= 0.5, "批量首条置信度正常")
        check(records[-1].confidence == 0.0, "错误记录置信度为 0")
    except Exception as exc:
        check(False, f"异常: {exc}")

    # --- 用例 6: 清洗功能 ---
    print("[用例 6] 数据清洗")
    try:
        cleaned = clean_record({"a": "  hello  ", "b": None, "c": 42})
        check(cleaned["a"] == "hello", "字符串去空白")
        check(cleaned["b"] is None, "空值保持 None")
        check(cleaned["c"] == 42, "数字不变")
    except Exception as exc:
        check(False, f"异常: {exc}")

    # --- 用例 7: 序列化 ---
    print("[用例 7] 输出序列化")
    try:
        records = [StructuredRecord({"k": "v"}, source="s", confidence=0.9)]
        json_out = serialize_output(records, "json")
        check("confidence" in json_out, "JSON 输出包含置信度")
        compact_out = serialize_output(records, "compact")
        check(len(compact_out) < len(json_out), "紧凑格式更短")
    except Exception as exc:
        check(False, f"异常: {exc}")

    # --- 用例 8: 置信度估算 ---
    print("[用例 8] 置信度估算")
    try:
        empty_conf = estimate_confidence({})
        full_conf = estimate_confidence({"a": 1, "b": 2, "c": 3})
        check(empty_conf < full_conf, "空记录置信度低于完整记录")
        check(0.5 <= empty_conf <= 1.0, "空记录置信度区间")
        check(0.5 <= full_conf <= 1.0, "完整记录置信度区间")
    except Exception as exc:
        check(False, f"异常: {exc}")

    # --- 汇总 ---
    print(f"\n自检完成: {'全部通过' if failures == 0 else f'{failures} 项失败'}")
    if failures > 0:
        raise ResourceTransformError("E007", f"自检失败 {failures} 项")
    return 0


# ---------------------------------------------------------------------------
# CLI 入口
# ---------------------------------------------------------------------------

def main() -> int:
    """命令行入口。"""
    parser = argparse.ArgumentParser(
        description="agent-resources: 数据整理 / 资源转换 / 结构化输出"
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置离线自检（无需外部输入）",
    )
    parser.add_argument(
        "--input",
        type=str,
        default=None,
        help="输入文件路径（JSON/CSV），若不提供则从 stdin 读取",
    )
    parser.add_argument(
        "--source",
        type=str,
        default="cli",
        help="数据来源标识（默认: cli）",
    )
    parser.add_argument(
        "--confidence",
        type=float,
        default=None,
        help="手动指定置信度（0.0~1.0），不指定则自动估算",
    )
    parser.add_argument(
        "--output-format",
        type=str,
        choices=["json", "compact"],
        default="json",
        help="输出格式（默认: json）",
    )
    parser.add_argument(
        "--batch",
        action="store_true",
        help="批量模式：输入文件每行作为独立数据项",
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        try:
            _run_selftest()
            return 0
        except ResourceTransformError as exc:
            print(f"自检失败: {exc}", file=sys.stderr)
            return 1

    # 正常处理模式
    try:
        # 读取输入
        if args.input:
            with open(args.input, "r", encoding="utf-8") as f:
                raw_text = f.read()
        else:
            raw_text = sys.stdin.read()

        if not raw_text.strip():
            raise ResourceTransformError("E001", "输入为空")

        # 批量或单条处理
        if args.batch:
            # 每行作为一个独立数据项
            lines = [line for line in raw_text.splitlines() if line.strip()]
            records = batch_transform(lines, source=args.source)
        else:
            # 尝试解析为 JSON/CSV
            try:
                data: Union[str, Dict, List] = json.loads(raw_text)
            except json.JSONDecodeError:
                data = raw_text  # 按文本处理
            records = transform_to_records(
                data,
                source=args.source,
                auto_confidence=args.confidence is None,
                confidence=args.confidence,
            )

        # 输出
        output = serialize_output(records, args.output_format)
        print(output)
        return 0

    except ResourceTransformError as exc:
        print(f"错误 {exc.code}: {exc.message}", file=sys.stderr)
        return 1
    except FileNotFoundError:
        print(f"错误 E009: 文件不存在: {args.input}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"错误 E010: 未知错误: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
