#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gsa-feeds 数据接入与结构化转换工具

功能：
- 将任意数据源（字典/列表/CSV文本）转为结构化结果
- 支持批量处理与置信度标注
- 内置离线自检（--selftest），不依赖外部文件/网络

错误码：
E001 参数错误
E002 输入格式不支持
E003 数据源为空
E004 字段映射失败
E005 类型转换失败
E006 批量处理中断
E007 置信度计算异常
E008 输出格式不支持
E009 自检失败
E010 未知错误

依赖：仅标准库（json, csv, argparse, sys, math）
"""

import argparse
import csv
import io
import json
import math
import sys
from typing import Any, Dict, List, Optional, Union


# ============================================================
# 核心数据结构
# ============================================================

class FeedRecord:
    """单条结构化记录"""
    def __init__(self, data: Dict[str, Any], confidence: float = 1.0):
        self.data = data
        self.confidence = confidence

    def to_dict(self) -> Dict[str, Any]:
        return {
            "data": self.data,
            "confidence": round(self.confidence, 4)
        }


class FeedResult:
    """批量处理结果容器"""
    def __init__(self):
        self.records: List[FeedRecord] = []
        self.meta: Dict[str, Any] = {}

    def add(self, record: FeedRecord) -> None:
        self.records.append(record)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "meta": self.meta,
            "count": len(self.records),
            "records": [r.to_dict() for r in self.records]
        }


# ============================================================
# 数据源解析
# ============================================================

def parse_json_source(raw: str) -> List[Dict[str, Any]]:
    """解析 JSON 文本为记录列表"""
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"JSON解析失败: {exc}") from exc

    if isinstance(data, dict):
        # 单条记录包装为列表
        return [data]
    if isinstance(data, list):
        # 过滤非字典元素
        result = []
        for item in data:
            if isinstance(item, dict):
                result.append(item)
            else:
                # 非字典元素包装为 {"value": item}
                result.append({"value": item})
        return result
    raise TypeError("JSON根节点必须是对象或数组")


def parse_csv_source(raw: str, has_header: bool = True) -> List[Dict[str, Any]]:
    """解析 CSV 文本为记录列表"""
    reader = csv.reader(io.StringIO(raw))
    rows = [row for row in reader if any(cell.strip() for cell in row)]
    if not rows:
        return []

    if has_header:
        header = rows[0]
        body = rows[1:]
    else:
        header = [f"col_{i}" for i in range(len(rows[0]))]
        body = rows

    records = []
    for row in body:
        # 补齐长度
        padded = row + [""] * (len(header) - len(row))
        record = {header[i]: padded[i].strip() for i in range(len(header))}
        records.append(record)
    return records


def parse_source(raw: str, source_type: str = "json") -> List[Dict[str, Any]]:
    """根据类型解析数据源"""
    stype = source_type.lower().strip()
    if stype == "json":
        return parse_json_source(raw)
    if stype in ("csv", "tsv"):
        delimiter = "\t" if stype == "tsv" else ","
        # 临时替换分隔符处理
        if delimiter != ",":
            raw = raw.replace(delimiter, ",")
        return parse_csv_source(raw)
    if stype in ("list", "python"):
        # 尝试按 JSON 处理
        return parse_json_source(raw)
    raise ValueError(f"不支持的数据源类型: {source_type}")


# ============================================================
# 字段处理与类型转换
# ============================================================

def convert_type(value: Any, target_type: str) -> Any:
    """将字段值转换为目标类型"""
    ttype = target_type.lower().strip()
    if ttype in ("str", "string", "text"):
        return str(value)
    if ttype in ("int", "integer"):
        try:
            return int(float(str(value)))
        except (ValueError, TypeError) as exc:
            raise ValueError(f"无法转换为整数: {value}") from exc
    if ttype in ("float", "double", "number"):
        try:
            return float(str(value))
        except (ValueError, TypeError) as exc:
            raise ValueError(f"无法转换为浮点数: {value}") from exc
    if ttype in ("bool", "boolean"):
        if isinstance(value, bool):
            return value
        sval = str(value).strip().lower()
        if sval in ("true", "1", "yes", "y", "on"):
            return True
        if sval in ("false", "0", "no", "n", "off"):
            return False
        raise ValueError(f"无法转换为布尔值: {value}")
    if ttype in ("json", "dict", "object"):
        if isinstance(value, dict):
            return value
        try:
            return json.loads(str(value))
        except json.JSONDecodeError as exc:
            raise ValueError(f"无法解析JSON: {value}") from exc
    # 默认返回原值
    return value


def apply_field_mapping(
    record: Dict[str, Any],
    mapping: Dict[str, str],
    conversions: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """应用字段映射与类型转换"""
    result: Dict[str, Any] = {}
    conv = conversions or {}

    for target_field, source_field in mapping.items():
        if source_field not in record:
            raise KeyError(f"源字段缺失: {source_field}")
        value = record[source_field]
        if target_field in conv:
            value = convert_type(value, conv[target_field])
        result[target_field] = value
    return result


# ============================================================
# 置信度计算
# ============================================================

def compute_confidence(record: Dict[str, Any], base: float = 1.0) -> float:
    """基于字段完整度计算置信度"""
    if not record:
        return 0.0
    # 统计非空字段比例
    filled = sum(1 for v in record.values() if v is not None and str(v).strip() != "")
    ratio = filled / len(record)
    # 基础置信度乘以完整度，并限制在 [0, 1]
    conf = base * ratio
    return max(0.0, min(1.0, conf))


# ============================================================
# 主处理流程
# ============================================================

def process_records(
    raw_records: List[Dict[str, Any]],
    mapping: Optional[Dict[str, str]] = None,
    conversions: Optional[Dict[str, str]] = None,
    confidence_base: float = 1.0,
    batch_size: int = 100
) -> FeedResult:
    """批量处理记录"""
    result = FeedResult()
    result.meta = {
        "total_input": len(raw_records),
        "processed": 0,
        "failed": 0,
        "batch_size": batch_size
    }

    if not raw_records:
        raise ValueError("数据源为空")

    # 默认映射：原样保留所有字段
    if mapping is None:
        if raw_records:
            all_keys = set()
            for rec in raw_records:
                all_keys.update(rec.keys())
            mapping = {k: k for k in all_keys}

    for i, rec in enumerate(raw_records):
        try:
            # 应用字段映射
            if mapping:
                mapped = apply_field_mapping(rec, mapping, conversions)
            else:
                mapped = dict(rec)

            # 计算置信度
            conf = compute_confidence(mapped, base=confidence_base)

            # 创建记录
            feed_rec = FeedRecord(mapped, conf)
            result.add(feed_rec)
            result.meta["processed"] += 1

        except (KeyError, ValueError, TypeError) as exc:
            result.meta["failed"] += 1
            # 失败记录保留原数据，置信度为0
            result.add(FeedRecord({"error": str(exc), "original": rec}, 0.0))

        # 批量检查点（此处仅记录，不中断）
        if (i + 1) % batch_size == 0:
            pass  # 可扩展为持久化检查点

    return result


# ============================================================
# 输出格式化
# ============================================================

def format_output(result: FeedResult, output_format: str = "json") -> str:
    """将结果格式化为指定格式"""
    fmt = output_format.lower().strip()
    if fmt == "json":
        return json.dumps(result.to_dict(), ensure_ascii=False, indent=2)
    if fmt == "compact":
        return json.dumps(result.to_dict(), ensure_ascii=False, separators=(",", ":"))
    if fmt in ("csv", "tsv"):
        # 展平记录为CSV
        all_keys = set()
        for rec in result.records:
            all_keys.update(rec.data.keys())
        keys = sorted(all_keys)
        delimiter = "\t" if fmt == "tsv" else ","
        buf = io.StringIO()
        writer = csv.writer(buf, delimiter=delimiter)
        writer.writerow(keys + ["confidence"])
        for rec in result.records:
            row = [rec.data.get(k, "") for k in keys]
            row.append(rec.confidence)
            writer.writerow(row)
        return buf.getvalue()
    raise ValueError(f"不支持的输出格式: {output_format}")


# ============================================================
# 自检模块
# ============================================================

def run_selftest() -> bool:
    """内置硬编码样例进行离线自检"""
    print("=== gsa-feeds 自检开始 ===")

    # --- 测试1: JSON解析 ---
    json_sample = """
    [
        {"name": "Alice", "age": "30", "active": "true"},
        {"name": "Bob", "age": "25", "active": "false"}
    ]
    """
    try:
        records = parse_source(json_sample, "json")
        assert len(records) == 2, f"JSON解析记录数错误: {len(records)}"
        assert records[0]["name"] == "Alice"
        assert records[1]["age"] == "25"
        print("[PASS] JSON解析")
    except Exception as exc:
        print(f"[FAIL] JSON解析: {exc}")
        return False

    # --- 测试2: CSV解析 ---
    csv_sample = "name,age,city\n张三,28,北京\n李四,35,上海\n"
    try:
        records = parse_source(csv_sample, "csv")
        assert len(records) == 2, f"CSV解析记录数错误: {len(records)}"
        assert records[0]["name"] == "张三"
        assert records[1]["city"] == "上海"
        print("[PASS] CSV解析")
    except Exception as exc:
        print(f"[FAIL] CSV解析: {exc}")
        return False

    # --- 测试3: 字段映射与类型转换 ---
    mapping = {"user_name": "name", "user_age": "age"}
    conversions = {"user_age": "int"}
    try:
        mapped = apply_field_mapping(records[0], mapping, conversions)
        assert mapped["user_name"] == "张三"
        assert isinstance(mapped["user_age"], int)
        assert mapped["user_age"] == 28
        print("[PASS] 字段映射与类型转换")
    except Exception as exc:
        print(f"[FAIL] 字段映射: {exc}")
        return False

    # --- 测试4: 置信度计算 ---
    test_data = {"a": "x", "b": "", "c": "z"}
    try:
        conf = compute_confidence(test_data)
        # 2/3 填充 => 置信度约 0.667，使用宽松区间
        assert conf > 0.5, f"置信度过低: {conf}"
        assert conf <= 1.0, f"置信度超过1: {conf}"
        print(f"[PASS] 置信度计算 (conf={conf:.3f})")
    except Exception as exc:
        print(f"[FAIL] 置信度: {exc}")
        return False

    # --- 测试5: 批量处理 ---
    try:
        raw = [
            {"id": "1", "value": "a"},
            {"id": "2", "value": ""},
            {"id": "3", "value": "c"}
        ]
        result = process_records(raw, confidence_base=0.9)
        assert result.meta["total_input"] == 3
        assert result.meta["processed"] == 3, f"处理数错误: {result.meta['processed']}"
        assert len(result.records) == 3
        # 空值记录置信度应较低
        assert result.records[1].confidence < result.records[0].confidence
        print("[PASS] 批量处理")
    except Exception as exc:
        print(f"[FAIL] 批量处理: {exc}")
        return False

    # --- 测试6: 输出格式化 ---
    try:
        json_out = format_output(result, "json")
        parsed = json.loads(json_out)
        assert parsed["count"] == 3
        assert len(parsed["records"]) == 3
        compact_out = format_output(result, "compact")
        assert len(compact_out) < len(json_out)
        print("[PASS] 输出格式化")
    except Exception as exc:
        print(f"[FAIL] 输出格式化: {exc}")
        return False

    # --- 测试7: 空数据处理 ---
    try:
        empty_result = process_records([{"x": ""}])
        assert empty_result.records[0].confidence == 0.0
        print("[PASS] 空数据处理")
    except Exception as exc:
        print(f"[FAIL] 空数据处理: {exc}")
        return False

    print("=== 全部自检通过 ===")
    return True


# ============================================================
# 命令行入口
# ============================================================

def main(argv: Optional[List[str]] = None) -> int:
    """主入口函数"""
    parser = argparse.ArgumentParser(
        description="gsa-feeds 数据接入与结构化转换工具",
        epilog="错误码: E001-E010"
    )
    parser.add_argument("--input", "-i", help="输入数据（JSON/CSV文本）")
    parser.add_argument("--file", "-f", help="从文件读取输入")
    parser.add_argument("--type", "-t", default="json", choices=["json", "csv", "tsv"],
                        help="数据源类型 (默认: json)")
    parser.add_argument("--mapping", "-m", help="字段映射 JSON，如 {\"新字段\":\"旧字段\"}")
    parser.add_argument("--conversions", "-c", help="类型转换 JSON，如 {\"字段\":\"int\"}")
    parser.add_argument("--base-confidence", type=float, default=1.0,
                        help="基础置信度 (默认: 1.0)")
    parser.add_argument("--batch-size", type=int, default=100,
                        help="批处理大小 (默认: 100)")
    parser.add_argument("--output-format", "-o", default="json",
                        choices=["json", "compact", "csv", "tsv"],
                        help="输出格式 (默认: json)")
    parser.add_argument("--selftest", action="store_true",
                        help="运行离线自检")

    args = parser.parse_args(argv)

    # 自检模式
    if args.selftest:
        try:
            ok = run_selftest()
            return 0 if ok else 9  # 9 对应 E009
        except Exception as exc:
            print(f"自检异常: {exc}", file=sys.stderr)
            return 9

    # 正常处理模式
    try:
        # 获取输入数据
        if args.file:
            try:
                with open(args.file, "r", encoding="utf-8") as fh:
                    raw_input = fh.read()
            except OSError as exc:
                print(f"E001: 无法读取文件 {args.file}: {exc}", file=sys.stderr)
                return 1
        elif args.input:
            raw_input = args.input
        else:
            # 尝试从标准输入读取
            raw_input = sys.stdin.read() if not sys.stdin.isatty() else ""
            if not raw_input.strip():
                print("E001: 未提供输入数据，请使用 --input 或 --file 指定", file=sys.stderr)
                return 1

        # 解析数据源
        try:
            records = parse_source(raw_input, args.type)
        except (ValueError, TypeError) as exc:
            print(f"E002: 数据源解析失败: {exc}", file=sys.stderr)
            return 2

        # 解析映射配置
        mapping = None
        if args.mapping:
            try:
                mapping = json.loads(args.mapping)
                if not isinstance(mapping, dict):
                    raise ValueError("映射必须是JSON对象")
            except (json.JSONDecodeError, ValueError) as exc:
                print(f"E004: 映射配置错误: {exc}", file=sys.stderr)
                return 4

        # 解析转换配置
        conversions = None
        if args.conversions:
            try:
                conversions = json.loads(args.conversions)
                if not isinstance(conversions, dict):
                    raise ValueError("转换配置必须是JSON对象")
            except (json.JSONDecodeError, ValueError) as exc:
                print(f"E005: 转换配置错误: {exc}", file=sys.stderr)
                return 5

        # 批量处理
        try:
            result = process_records(
                records,
                mapping=mapping,
                conversions=conversions,
                confidence_base=args.base_confidence,
                batch_size=args.batch_size
            )
        except ValueError as exc:
            print(f"E006: 批量处理失败: {exc}", file=sys.stderr)
            return 6

        # 输出结果
        try:
            output = format_output(result, args.output_format)
            print(output)
        except ValueError as exc:
            print(f"E008: 输出格式化失败: {exc}", file=sys.stderr)
            return 8

        return 0

    except Exception as exc:
        print(f"E010: 未知错误: {exc}", file=sys.stderr)
        return 10


if __name__ == "__main__":
    sys.exit(main())
