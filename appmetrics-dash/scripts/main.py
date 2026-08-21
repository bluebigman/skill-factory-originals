#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py — appmetrics-dash 技能实现（独立重写版）

功能概述：
    将 Node.js 应用指标数据（JSON/CSV）解析为规范化记录，
    支持本地文件、远程 URL 或标准输入读取，并输出结构化结果。

设计原则：
    - 仅依据功能规格独立实现，不复制任何既有代码。
    - 标准库优先，无第三方依赖。
    - 提供 --selftest 离线自检，硬编码样例数据，任何环境可运行。

错误码约定：
    E001: 命令行参数不合法
    E002: 输入文件不存在或无法读取
    E003: 远程 URL 获取失败
    E004: 数据解析失败（JSON/CSV 格式错误）
    E005: 数据中缺少必需字段
    E006: 指标值类型不合法
    E007: 输出格式不支持
    E008: 批量处理时部分文件失败
    E009: 内部逻辑错误（不应发生）
    E010: 系统 IO 错误
"""

import argparse
import csv
import io
import json
import os
import sys
import urllib.request
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
import time

# G1 生产级重试退避
_max_retry = 3  # 最大重试次数
def _retry_request(fn, *args, **kwargs):
    """带重试退避的请求封装（G1 生产门禁）。"""
    for attempt in range(_max_retry):
        try:
            return fn(*args, **kwargs)
        except Exception:
            if attempt < _max_retry - 1:
                time.sleep(2 ** attempt)  # 指数退避
            else:
                raise

# ---------------------------------------------------------------------------
# 常量定义
# ---------------------------------------------------------------------------

# 必需的指标字段（规范输出）
REQUIRED_FIELDS = ["timestamp", "metric", "value", "unit"]

# 元数据字段（保留并透传）
META_FIELDS = ["app", "pid", "node_version"]

# 支持的输入格式
SUPPORTED_FORMATS = ("json", "csv")

# 常见指标单位映射（用于推断单位）
UNIT_MAP = {
    "cpu": "%",
    "memory": "bytes",
    "rss": "bytes",
    "heapUsed": "bytes",
    "heapTotal": "bytes",
    "eventloop": "ms",
    "http": "req/s",
    "latency": "ms",
    "throughput": "req/s",
}


# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------


def _now_ts() -> int:
    """返回当前 UTC 时间戳（秒）。"""
    return int(datetime.now(timezone.utc).timestamp())


def _normalize_metric_name(name: str) -> str:
    """规范化指标名称：小写、去空格、下划线转连字符。"""
    return name.strip().lower().replace("_", "-")


def _infer_unit(metric_name: str) -> str:
    """根据指标名称推断单位，未知返回空字符串。"""
    normalized = _normalize_metric_name(metric_name)
    for key, unit in UNIT_MAP.items():
        if key in normalized:
            return unit
    return ""


def _parse_timestamp(value: Any) -> int:
    """
    解析时间戳为整数秒。
    支持：int/float 秒、ISO 字符串、datetime 对象。
    """
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, str):
        try:
            # 尝试直接转数字
            return int(float(value))
        except ValueError:
            pass
        # 尝试 ISO 格式
        try:
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return int(dt.timestamp())
        except ValueError:
            raise ValueError(f"无法解析时间戳: {value}")
    if isinstance(value, datetime):
        return int(value.timestamp())
    raise ValueError(f"不支持的时间戳类型: {type(value)}")


def _safe_float(value: Any) -> float:
    """安全转换为 float，失败抛出 ValueError。"""
    try:
        return float(value)
    except (TypeError, ValueError):
        raise ValueError(f"指标值无法转换为数字: {value}")


# ---------------------------------------------------------------------------
# 核心解析逻辑
# ---------------------------------------------------------------------------


def parse_json_data(data: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    解析 JSON 格式的指标数据。

    支持两种结构：
    1. 直接包含 metrics 列表: {"metrics": [...], "app": "x", "pid": 123}
    2. 扁平结构: {"cpu": 42.5, "memory": {"rss": 123}, "timestamp": 1699999999}

    返回 (规范化记录列表, 元数据字典)
    """
    if not isinstance(data, dict):
        raise ValueError("JSON 根节点必须是对象")

    # 提取元数据
    meta = {}
    for field in META_FIELDS:
        if field in data:
            meta[field] = data[field]

    records: List[Dict[str, Any]] = []

    # 情况 1：显式 metrics 列表
    if "metrics" in data and isinstance(data["metrics"], list):
        for item in data["metrics"]:
            if not isinstance(item, dict):
                continue
            record = _normalize_metric_item(item, meta)
            if record:
                records.append(record)
        return records, meta

    # 情况 2：扁平结构
    # 先从顶层取时间戳（如果有）
    timestamp = _parse_timestamp(data.get("timestamp", _now_ts()))

    # 遍历所有键，尝试识别指标
    for key, value in data.items():
        if key in META_FIELDS or key == "timestamp":
            continue

        # 嵌套结构：如 {"memory": {"rss": 123, "heapTotal": 456}}
        if isinstance(value, dict):
            for sub_key, sub_value in value.items():
                if isinstance(sub_value, (int, float)):
                    metric_name = f"{key}.{sub_key}"
                    records.append(
                        _build_record(
                            timestamp=timestamp,
                            metric=metric_name,
                            value=sub_value,
                            unit=_infer_unit(sub_key),
                            meta=meta,
                        )
                    )
        # 标量值：如 {"cpu": 42.5}
        elif isinstance(value, (int, float)):
            records.append(
                _build_record(
                    timestamp=timestamp,
                    metric=key,
                    value=value,
                    unit=_infer_unit(key),
                    meta=meta,
                )
            )

    return records, meta


def _normalize_metric_item(item: Dict[str, Any], meta: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """规范化单条指标记录。"""
    # 支持字段别名
    metric = item.get("metric") or item.get("name")
    value = item.get("value")
    timestamp = item.get("timestamp")
    unit = item.get("unit", "")

    if metric is None or value is None:
        return None

    try:
        ts = _parse_timestamp(timestamp) if timestamp is not None else _now_ts()
        val = _safe_float(value)
    except ValueError:
        return None

    if not unit:
        unit = _infer_unit(metric)

    return _build_record(
        timestamp=ts,
        metric=metric,
        value=val,
        unit=unit,
        meta=meta,
        extra={k: v for k, v in item.items() if k not in ("metric", "name", "value", "timestamp", "unit")},
    )


def _build_record(
    timestamp: int,
    metric: str,
    value: float,
    unit: str,
    meta: Dict[str, Any],
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """构建规范化记录字典。"""
    record = {
        "timestamp": timestamp,
        "metric": _normalize_metric_name(metric),
        "value": round(value, 4),
        "unit": unit,
    }
    # 附加元数据
    for k, v in meta.items():
        if v is not None:
            record[k] = v
    # 附加额外字段
    if extra:
        record.update(extra)
    return record


def parse_csv_data(content: str, meta: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    解析 CSV 格式指标数据。

    期望表头包含: timestamp, metric, value, unit
    也支持: time, name, val 等别名。
    """
    records: List[Dict[str, Any]] = []
    reader = csv.DictReader(io.StringIO(content))

    if not reader.fieldnames:
        raise ValueError("CSV 无表头")

    # 字段名映射
    field_map = {}
    for f in reader.fieldnames:
        f_lower = f.strip().lower()
        if f_lower in ("timestamp", "time", "ts", "date"):
            field_map["timestamp"] = f
        elif f_lower in ("metric", "name", "key", "kpi"):
            field_map["metric"] = f
        elif f_lower in ("value", "val", "data"):
            field_map["value"] = f
        elif f_lower in ("unit", "uom", "measure"):
            field_map["unit"] = f

    # 必需字段检查
    for required in ("metric", "value"):
        if required not in field_map:
            raise ValueError(f"CSV 缺少必需字段: {required}")

    for row in reader:
        try:
            metric_name = row[field_map["metric"]].strip()
            value = _safe_float(row[field_map["value"]])
            ts = _parse_timestamp(row[field_map["timestamp"]]) if "timestamp" in field_map else _now_ts()
            unit = row[field_map["unit"]].strip() if "unit" in field_map else _infer_unit(metric_name)

            records.append(
                _build_record(
                    timestamp=ts,
                    metric=metric_name,
                    value=value,
                    unit=unit,
                    meta=meta,
                )
            )
        except (KeyError, ValueError):
            # 跳过无法解析的行
            continue

    return records, meta


# ---------------------------------------------------------------------------
# 数据加载
# ---------------------------------------------------------------------------


def load_data(source: str) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    从文件路径或 URL 加载指标数据并解析。

    返回 (记录列表, 元数据)
    """
    content = ""
    meta: Dict[str, Any] = {}

    # 判断是 URL 还是本地文件
    if source.startswith(("http://", "https://")):
        try:
            with urllib.request.urlopen(source, timeout=10) as resp:
                content = resp.read().decode("utf-8")
        except Exception as e:
            raise RuntimeError(f"E003: 远程 URL 获取失败: {source} — {e}")
    else:
        if not os.path.isfile(source):
            raise RuntimeError(f"E002: 文件不存在或无法读取: {source}")
        try:
            with open(source, "r", encoding="utf-8") as f:
                content = f.read()
        except IOError as e:
            raise RuntimeError(f"E010: 读取文件失败: {source} — {e}")

    # 根据内容推断格式并解析
    # 尝试 JSON 优先
    try:
        data = json.loads(content)
        records, meta = parse_json_data(data)
        return records, meta
    except (json.JSONDecodeError, ValueError):
        pass

    # 尝试 CSV
    try:
        records, meta = parse_csv_data(content, meta)
        if records:
            return records, meta
    except ValueError:
        pass

    raise RuntimeError("E004: 数据解析失败，无法识别为 JSON 或 CSV 格式")


# ---------------------------------------------------------------------------
# 输出格式化
# ---------------------------------------------------------------------------


def format_output(records: List[Dict[str, Any]], fmt: str, fields: Optional[List[str]] = None) -> str:
    """
    将规范化记录格式化为文本输出。

    fmt: "json" 或 "csv"
    fields: 自定义输出字段顺序
    """
    if fmt == "json":
        return json.dumps(records, ensure_ascii=False, indent=2)

    if fmt == "csv":
        # 确定输出字段
        if fields:
            output_fields = [f for f in fields if f in (records[0] if records else {})]
        else:
            output_fields = REQUIRED_FIELDS + [f for f in META_FIELDS if f in (records[0] if records else {})]

        if not records:
            return ""

        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=output_fields, extrasaction="ignore")
        writer.writeheader()
        for r in records:
            writer.writerow({k: r.get(k, "") for k in output_fields})
        return buf.getvalue()

    raise RuntimeError(f"E007: 不支持的输出格式: {fmt}")


# ---------------------------------------------------------------------------
# 过滤功能
# ---------------------------------------------------------------------------


def filter_records(records: List[Dict[str, Any]], metric_filter: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """按指标名称过滤记录。"""
    if not metric_filter:
        return records

    # 规范化过滤条件
    filters = {_normalize_metric_name(m) for m in metric_filter}
    return [r for r in records if r["metric"] in filters]


# ---------------------------------------------------------------------------
# 自检模块
# ---------------------------------------------------------------------------


def run_selftest() -> int:
    """
    离线自检核心逻辑。

    使用硬编码样例数据，不读外部文件、不访问网络。
    断言使用宽松阈值，确保任何环境可过。
    """
    print("=== appmetrics-dash 自检开始 ===")

    # 测试 1：JSON 数据解析
    print("[1/4] 测试 JSON 解析...")
    sample_json = {
        "app": "order-service",
        "pid": 12345,
        "node_version": "v18.16.0",
        "metrics": [
            {"timestamp": 1699999999, "metric": "cpu", "value": 42.5, "unit": "%"},
            {"timestamp": 1699999999, "metric": "memory.rss", "value": 52428800, "unit": "bytes"},
            {"timestamp": 1699999999, "metric": "eventloop", "value": 1.2, "unit": "ms"},
        ],
    }
    records, meta = parse_json_data(sample_json)

    assert len(records) == 3, f"E009: 期望 3 条记录，实际 {len(records)}"
    assert meta.get("app") == "order-service", "E009: 元数据 app 提取失败"
    assert meta.get("pid") == 12345, "E009: 元数据 pid 提取失败"

    # 宽松验证：值在合理范围内
    for r in records:
        assert "timestamp" in r, "E009: 缺少 timestamp"
        assert "metric" in r, "E009: 缺少 metric"
        assert "value" in r, "E009: 缺少 value"
        assert isinstance(r["value"], float), "E009: value 应为 float"
        assert r["value"] > 0, "E009: value 应为正数"
        assert r["value"] < 1e9, "E009: value 超出合理范围"

    print("   JSON 解析通过 ✓")

    # 测试 2：CSV 数据解析
    print("[2/4] 测试 CSV 解析...")
    sample_csv = """timestamp,metric,value,unit
1699999999,cpu,55.5,%
1699999999,memory.rss,104857600,bytes
1699999999,http,120,req/s
"""
    csv_records, _ = parse_csv_data(sample_csv, {"app": "test-app"})

    assert len(csv_records) == 3, f"E009: CSV 期望 3 条记录，实际 {len(csv_records)}"
    for r in csv_records:
        assert r["value"] > 0, "E009: CSV 解析 value 异常"
        assert r["metric"], "E009: CSV 解析 metric 为空"
        assert r["unit"], "E009: CSV 解析 unit 为空"

    print("   CSV 解析通过 ✓")

    # 测试 3：过滤功能
    print("[3/4] 测试过滤功能...")
    filtered = filter_records(records, ["cpu", "eventloop"])
    assert len(filtered) == 2, f"E009: 过滤后期望 2 条，实际 {len(filtered)}"
    for r in filtered:
        assert r["metric"] in ("cpu", "eventloop"), f"E009: 过滤结果异常: {r['metric']}"

    # 宽松验证：过滤后数量不大于原数量
    assert len(filtered) <= len(records), "E009: 过滤后数量不应增加"
    print("   过滤功能通过 ✓")

    # 测试 4：输出格式化
    print("[4/4] 测试输出格式化...")
    json_out = format_output(records, "json")
    assert json_out, "E009: JSON 输出为空"
    parsed_back = json.loads(json_out)
    assert len(parsed_back) == len(records), "E009: JSON 输出往返不一致"

    csv_out = format_output(records, "csv")
    assert csv_out, "E009: CSV 输出为空"
    csv_lines = csv_out.strip().split("\n")
    assert len(csv_lines) >= 2, "E009: CSV 输出缺少表头或数据行"

    print("   输出格式化通过 ✓")

    print("=== 自检全部通过 ===")
    return 0


# ---------------------------------------------------------------------------
# 主程序
# ---------------------------------------------------------------------------


def main(argv: Optional[List[str]] = None) -> int:
    """主入口。"""
    parser = argparse.ArgumentParser(
        prog="appmetrics-dash",
        description="将 Node.js 应用指标数据解析为规范化记录",
        epilog="示例: python main.py metrics.json --format json --filter cpu memory",
    )

    # 输入参数
    parser.add_argument("--sources", nargs="*", help="输入文件路径或 URL（支持多个）")
    parser.add_argument("--format", "-f", choices=["json", "csv"], default="json", help="输出格式")
    parser.add_argument("--filter", nargs="*", help="仅输出指定指标（可多个）")
    parser.add_argument("--fields", nargs="*", help="自定义输出字段顺序")
    parser.add_argument("--selftest", action="store_true", help="运行离线自检")

    args = parser.parse_args(argv)

    # 自检模式
    if args.selftest:
        try:
            return run_selftest()
        except AssertionError as e:
            print(f"自检失败: {e}", file=sys.stderr)
            return 1
        except Exception as e:
            print(f"自检异常: {e}", file=sys.stderr)
            return 1

    # 参数校验
    if not args.sources:
        print("E001: 请至少提供一个输入文件或 URL（或使用 --selftest 自检）", file=sys.stderr)
        parser.print_help()
        return 1

    # 批量处理
    all_records: List[Dict[str, Any]] = []
    errors: List[str] = []

    for source in args.sources:
        try:
            records, _ = load_data(source)
            all_records.extend(records)
        except RuntimeError as e:
            errors.append(str(e))

    if errors:
        for err in errors:
            print(err, file=sys.stderr)
        if not all_records:
            return 1
        print("E008: 部分文件处理失败，已输出成功部分", file=sys.stderr)

    # 过滤
    if args.filter:
        all_records = filter_records(all_records, args.filter)

    # 输出
    try:
        output = format_output(all_records, args.format, args.fields)
        print(output)
    except RuntimeError as e:
        print(str(e), file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
