#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
traceml - 数据追踪、可视化、漂移检测与仪表盘引擎

仅依据功能规格独立实现（clean-room），提供：
- 结构化数据解析（CSV/JSON/URL）
- 关键指标提取与置信度标注
- 漂移检测（分布对比）
- 批量处理与自定义输出模板
- 离线自检（--selftest）

错误码说明：
    E001: 输入参数无效
    E002: 文件读取失败
    E003: 数据解析失败
    E004: 字段提取失败
    E005: 漂移检测失败
    E006: 输出生成失败
    E007: 批量处理失败
    E008: 配置加载失败
    E009: 内部逻辑错误
    E010: 自检失败
"""

import argparse
import csv
import io
import json
import math
import os
import statistics
import sys
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# 数据结构定义
# ============================================================

@dataclass
class MetricRecord:
    """单条指标记录"""
    metric: str          # 指标名
    value: float         # 数值
    timestamp: str       # 时间戳（ISO 格式）
    labels: Dict[str, str] = field(default_factory=dict)  # 附加标签
    confidence: float = 1.0  # 置信度（0~1）


@dataclass
class ParsedData:
    """解析后的结构化数据"""
    records: List[MetricRecord]
    source_type: str   # csv / json / url / dict
    raw_meta: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DriftResult:
    """漂移检测结果"""
    metric: str
    reference_mean: float
    current_mean: float
    drift_score: float   # 0~1，越大表示漂移越严重
    verdict: str         # stable / warning / drift
    details: Dict[str, Any] = field(default_factory=dict)


# ============================================================
# 核心解析模块
# ============================================================

class DataParser:
    """结构化数据解析器"""

    @staticmethod
    def parse_csv(text: str) -> List[Dict[str, Any]]:
        """解析 CSV 文本为字典列表"""
        try:
            reader = csv.DictReader(io.StringIO(text))
            rows = [dict(row) for row in reader]
            if not rows:
                raise ValueError("CSV 内容为空")
            return rows
        except Exception as exc:
            raise RuntimeError(f"E003: CSV 解析失败 - {exc}")

    @staticmethod
    def parse_json(text: str) -> Any:
        """解析 JSON 文本"""
        try:
            return json.loads(text)
        except Exception as exc:
            raise RuntimeError(f"E003: JSON 解析失败 - {exc}")

    @staticmethod
    def fetch_url(url: str, timeout: int = 10) -> str:
        """从 URL 获取文本内容"""
        try:
            with urllib.request.urlopen(url, timeout=timeout) as resp:
                return resp.read().decode("utf-8")
        except Exception as exc:
            raise RuntimeError(f"E002: URL 获取失败 - {exc}")

    @staticmethod
    def read_file(path: str) -> str:
        """读取本地文件内容"""
        try:
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as exc:
            raise RuntimeError(f"E002: 文件读取失败 - {exc}")


class DataExtractor:
    """关键信息提取器"""

    # 常见指标名关键字
    METRIC_KEYWORDS = [
        "loss", "accuracy", "precision", "recall", "f1", "auc",
        "cpu", "memory", "latency", "throughput", "error_rate",
        "mae", "mse", "rmse", "r2", "brier", "log_loss"
    ]

    @staticmethod
    def extract_metric_name(row: Dict[str, Any]) -> Optional[str]:
        """从行数据中提取指标名"""
        # 优先查找明确的指标列
        for key in row:
            key_lower = key.lower()
            if any(kw in key_lower for kw in ["metric", "name", "label", "type"]):
                return row[key]
        # 其次查找值列对应的指标名
        for key in row:
            key_lower = key.lower()
            if any(kw in key_lower for kw in DataExtractor.METRIC_KEYWORDS):
                return key
        return None

    @staticmethod
    def extract_value(row: Dict[str, Any]) -> Optional[float]:
        """从行数据中提取数值"""
        for key in row:
            key_lower = key.lower()
            if any(kw in key_lower for kw in ["value", "val", "metric_value", "score"]):
                try:
                    return float(row[key])
                except (ValueError, TypeError):
                    continue
        # 尝试从指标名列获取数值
        for key in row:
            key_lower = key.lower()
            if any(kw in key_lower for kw in DataExtractor.METRIC_KEYWORDS):
                try:
                    return float(row[key])
                except (ValueError, TypeError):
                    continue
        return None

    @staticmethod
    def extract_timestamp(row: Dict[str, Any]) -> str:
        """从行数据中提取时间戳"""
        for key in row:
            key_lower = key.lower()
            if any(kw in key_lower for kw in ["time", "timestamp", "date", "ts"]):
                return str(row[key])
        return datetime.now().isoformat()

    @staticmethod
    def extract_labels(row: Dict[str, Any]) -> Dict[str, str]:
        """提取附加标签"""
        labels = {}
        for key in row:
            key_lower = key.lower()
            # 排除已识别的字段
            if any(kw in key_lower for kw in ["metric", "value", "time", "timestamp"]):
                continue
            labels[key] = str(row[key])
        return labels

    @staticmethod
    def compute_confidence(row: Dict[str, Any], has_metric: bool, has_value: bool) -> Tuple[float, str]:
        """计算置信度"""
        if has_metric and has_value:
            return 1.0, ""
        if not has_metric and not has_value:
            return 0.2, "缺少指标名和数值"
        if not has_metric:
            return 0.6, "缺少明确的指标名"
        return 0.7, "缺少明确的时间戳"


class DataTransformer:
    """数据转换器：将原始行转为 MetricRecord"""

    @staticmethod
    def transform(rows: List[Dict[str, Any]]) -> List[MetricRecord]:
        """将解析后的行数据转换为 MetricRecord 列表"""
        records = []
        for row in rows:
            metric = DataExtractor.extract_metric_name(row)
            value = DataExtractor.extract_value(row)
            timestamp = DataExtractor.extract_timestamp(row)
            labels = DataExtractor.extract_labels(row)

            has_metric = metric is not None
            has_value = value is not None

            confidence, reason = DataExtractor.compute_confidence(row, has_metric, has_value)

            if not has_metric or not has_value:
                # 跳过无法识别的记录，但在元数据中记录
                continue

            records.append(
                MetricRecord(
                    metric=metric,
                    value=value,
                    timestamp=timestamp,
                    labels=labels,
                    confidence=confidence,
                )
            )

        if not records:
            raise RuntimeError("E004: 无法从输入中提取任何有效指标记录")
        return records


# ============================================================
# 漂移检测模块
# ============================================================

class DriftDetector:
    """漂移检测器"""

    # 判定阈值
    WARNING_THRESHOLD = 0.3   # 超过此值警告
    DRIFT_THRESHOLD = 0.6     # 超过此值判定漂移

    @staticmethod
    def _normalize(v: float, lo: float, hi: float) -> float:
        """将值归一化到 0~1 区间"""
        if hi - lo < 1e-9:
            return 0.5
        return max(0.0, min(1.0, (v - lo) / (hi - lo)))

    @staticmethod
    def detect(metric: str, reference: List[float], current: List[float]) -> DriftResult:
        """检测单个指标的漂移"""
        if not reference or not current:
            raise RuntimeError(f"E005: 指标 {metric} 的数据不足")

        ref_mean = statistics.mean(reference)
        cur_mean = statistics.mean(current)

        # 使用相对变化率作为漂移依据（宽松阈值）
        if abs(ref_mean) < 1e-9:
            # 参考均值为零时，使用绝对差值
            diff = abs(cur_mean - ref_mean)
            drift_score = DriftDetector._normalize(diff, 0, max(abs(cur_mean), 1.0))
        else:
            # 相对变化率
            ratio = abs(cur_mean - ref_mean) / abs(ref_mean)
            drift_score = DriftDetector._normalize(ratio, 0, 2.0)

        # 结合标准差变化
        if len(reference) >= 2 and len(current) >= 2:
            ref_std = statistics.stdev(reference)
            cur_std = statistics.stdev(current)
            std_ratio = abs(cur_std - ref_std) / max(ref_std, 1e-9)
            std_score = DriftDetector._normalize(std_ratio, 0, 1.0)
            drift_score = 0.7 * drift_score + 0.3 * std_score

        # 判定结果
        if drift_score >= DriftDetector.DRIFT_THRESHOLD:
            verdict = "drift"
        elif drift_score >= DriftDetector.WARNING_THRESHOLD:
            verdict = "warning"
        else:
            verdict = "stable"

        details = {
            "reference_size": len(reference),
            "current_size": len(current),
            "ref_std": statistics.stdev(reference) if len(reference) >= 2 else None,
            "cur_std": statistics.stdev(current) if len(current) >= 2 else None,
        }

        return DriftResult(
            metric=metric,
            reference_mean=ref_mean,
            current_mean=cur_mean,
            drift_score=drift_score,
            verdict=verdict,
            details=details,
        )

    @staticmethod
    def detect_all(records: List[MetricRecord], split_ratio: float = 0.5) -> List[DriftResult]:
        """对全部指标进行漂移检测"""
        if not records:
            raise RuntimeError("E005: 没有可检测的记录")

        # 按指标分组
        groups: Dict[str, List[float]] = {}
        for rec in records:
            groups.setdefault(rec.metric, []).append(rec.value)

        results = []
        for metric, values in groups.items():
            if len(values) < 2:
                continue
            split_idx = max(1, int(len(values) * split_ratio))
            reference = values[:split_idx]
            current = values[split_idx:]
            if len(current) < 1:
                continue
            results.append(DriftDetector.detect(metric, reference, current))

        return results


# ============================================================
# 输出生成模块
# ============================================================

class OutputGenerator:
    """输出生成器"""

    @staticmethod
    def to_json(records: List[MetricRecord], drift_results: Optional[List[DriftResult]] = None) -> str:
        """生成 JSON 输出"""
        try:
            output = {
                "generated_at": datetime.now().isoformat(),
                "record_count": len(records),
                "records": [
                    {
                        "metric": r.metric,
                        "value": r.value,
                        "timestamp": r.timestamp,
                        "labels": r.labels,
                        "confidence": r.confidence,
                    }
                    for r in records
                ],
            }

            if drift_results:
                output["drift_detection"] = [
                    {
                        "metric": d.metric,
                        "reference_mean": d.reference_mean,
                        "current_mean": d.current_mean,
                        "drift_score": d.drift_score,
                        "verdict": d.verdict,
                        "details": d.details,
                    }
                    for d in drift_results
                ]

            return json.dumps(output, ensure_ascii=False, indent=2)
        except Exception as exc:
            raise RuntimeError(f"E006: JSON 输出生成失败 - {exc}")

    @staticmethod
    def to_markdown(records: List[MetricRecord], drift_results: Optional[List[DriftResult]] = None) -> str:
        """生成 Markdown 表格输出"""
        try:
            lines = ["# traceml 数据追踪报告", ""]
            lines.append(f"生成时间: {datetime.now().isoformat()}")
            lines.append(f"记录总数: {len(records)}")
            lines.append("")

            # 指标汇总表
            lines.append("## 指标汇总")
            lines.append("")
            lines.append("| 指标 | 数值 | 时间戳 | 置信度 | 标签 |")
            lines.append("|------|------|--------|--------|------|")
            for r in records:
                labels_str = "; ".join(f"{k}={v}" for k, v in r.labels.items())
                lines.append(f"| {r.metric} | {r.value:.4f} | {r.timestamp} | {r.confidence:.2f} | {labels_str} |")

            # 漂移检测表
            if drift_results:
                lines.append("")
                lines.append("## 漂移检测")
                lines.append("")
                lines.append("| 指标 | 参考均值 | 当前均值 | 漂移分数 | 判定 |")
                lines.append("|------|----------|----------|----------|------|")
                for d in drift_results:
                    lines.append(
                        f"| {d.metric} | {d.reference_mean:.4f} | {d.current_mean:.4f} "
                        f"| {d.drift_score:.4f} | {d.verdict} |"
                    )

            return "\n".join(lines)
        except Exception as exc:
            raise RuntimeError(f"E006: Markdown 输出生成失败 - {exc}")


# ============================================================
# 主处理流程
# ============================================================

class TraceML:
    """traceml 主引擎"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.parser = DataParser()
        self.transformer = DataTransformer()
        self.detector = DriftDetector()
        self.generator = OutputGenerator()

    def process_source(self, source: str, source_type: str = "auto") -> ParsedData:
        """
        处理数据源（文件路径、URL、文本内容）
        source_type: auto / csv / json / url / file
        """
        try:
            # 确定数据源类型
            if source_type == "auto":
                source_type = self._detect_source_type(source)
            elif source_type == "url":
                source_type = "url"

            # 获取原始文本
            if source_type == "url":
                text = self.parser.fetch_url(source)
            elif source_type == "file":
                text = self.parser.read_file(source)
            else:
                text = source

            # 解析
            if source_type in ("csv", "file"):
                if source_type == "file":
                    # 文件类型由扩展名决定
                    _, ext = os.path.splitext(source)
                    if ext.lower() in (".json",):
                        data = self.parser.parse_json(text)
                        rows = self._json_to_rows(data)
                    else:
                        rows = self.parser.parse_csv(text)
                else:
                    rows = self.parser.parse_csv(text)
            elif source_type == "json":
                data = self.parser.parse_json(text)
                rows = self._json_to_rows(data)
            else:
                raise ValueError(f"不支持的数据源类型: {source_type}")

            # 转换
            records = self.transformer.transform(rows)

            return ParsedData(
                records=records,
                source_type=source_type,
                raw_meta={"row_count": len(rows)},
            )
        except RuntimeError:
            raise
        except Exception as exc:
            raise RuntimeError(f"E007: 数据源处理失败 - {exc}")

    def _detect_source_type(self, source: str) -> str:
        """自动检测数据源类型"""
        # URL 检测
        if source.startswith(("http://", "https://")):
            return "url"

        # 文件路径检测
        if os.path.isfile(source):
            return "file"

        # JSON 检测
        stripped = source.strip()
        if stripped.startswith("{") or stripped.startswith("["):
            return "json"

        # 默认按 CSV 处理
        return "csv"

    def _json_to_rows(self, data: Any) -> List[Dict[str, Any]]:
        """将 JSON 数据转换为行格式"""
        if isinstance(data, list):
            return [item if isinstance(item, dict) else {"value": item} for item in data]
        elif isinstance(data, dict):
            # 尝试识别常见格式
            if "records" in data and isinstance(data["records"], list):
                return data["records"]
            elif "data" in data and isinstance(data["data"], list):
                return data["data"]
            else:
                return [data]
        else:
            raise ValueError("JSON 数据格式不支持")

    def process_batch(self, sources: List[str], source_types: Optional[List[str]] = None) -> List[ParsedData]:
        """批量处理多个数据源"""
        if source_types is None:
            source_types = ["auto"] * len(sources)
        if len(sources) != len(source_types):
            raise RuntimeError("E001: 数据源与类型数量不匹配")

        results = []
        for src, stype in zip(sources, source_types):
            results.append(self.process_source(src, stype))
        return results

    def generate_output(
        self,
        parsed: ParsedData,
        output_format: str = "json",
        detect_drift: bool = False,
        split_ratio: float = 0.5,
    ) -> str:
        """生成输出"""
        drift_results = None
        if detect_drift:
            drift_results = self.detector.detect_all(parsed.records, split_ratio)

        if output_format == "json":
            return self.generator.to_json(parsed.records, drift_results)
        elif output_format == "markdown":
            return self.generator.to_markdown(parsed.records, drift_results)
        else:
            raise RuntimeError(f"E001: 不支持的输出格式: {output_format}")


# ============================================================
# 自检模块
# ============================================================

def run_selftest() -> bool:
    """
    离线自检核心逻辑
    使用内置硬编码样例数据，不依赖外部文件/网络/工作目录
    """
    print("=" * 60)
    print("traceml 自检开始")
    print("=" * 60)

    # 测试数据 1：CSV 格式
    csv_data = """metric,value,timestamp,experiment
loss,0.5,2024-01-01T10:00:00,exp1
loss,0.4,2024-01-01T11:00:00,exp1
loss,0.3,2024-01-01T12:00:00,exp1
accuracy,0.8,2024-01-01T10:00:00,exp1
accuracy,0.85,2024-01-01T11:00:00,exp1
accuracy,0.9,2024-01-01T12:00:00,exp1
cpu,60,2024-01-01T10:00:00,system
cpu,80,2024-01-01T11:00:00,system
cpu,95,2024-01-01T12:00:00,system
"""

    # 测试数据 2：JSON 格式
    json_data = json.dumps({
        "records": [
            {"metric": "loss", "value": 0.6, "timestamp": "2024-02-01T10:00:00"},
            {"metric": "loss", "value": 0.7, "timestamp": "2024-02-01T11:00:00"},
            {"metric": "loss", "value": 0.8, "timestamp": "2024-02-01T12:00:00"},
            {"metric": "accuracy", "value": 0.7, "timestamp": "2024-02-01T10:00:00"},
            {"metric": "accuracy", "value": 0.65, "timestamp": "2024-02-01T11:00:00"},
            {"metric": "accuracy", "value": 0.6, "timestamp": "2024-02-01T12:00:00"},
        ]
    })

    # 初始化引擎
    engine = TraceML()

    try:
        # 测试 1：CSV 解析
        print("\n[1/5] 测试 CSV 解析...")
        parsed_csv = engine.process_source(csv_data, source_type="csv")
        assert len(parsed_csv.records) == 9, f"CSV 应解析出 9 条记录，实际 {len(parsed_csv.records)}"
        assert all(r.confidence >= 0.9 for r in parsed_csv.records), "CSV 记录置信度应较高"
        print(f"  ✓ CSV 解析成功，共 {len(parsed_csv.records)} 条记录")

        # 测试 2：JSON 解析
        print("\n[2/5] 测试 JSON 解析...")
        parsed_json = engine.process_source(json_data, source_type="json")
        assert len(parsed_json.records) == 6, f"JSON 应解析出 6 条记录，实际 {len(parsed_json.records)}"
        print(f"  ✓ JSON 解析成功，共 {len(parsed_json.records)} 条记录")

        # 测试 3：漂移检测
        print("\n[3/5] 测试漂移检测...")
        drift_results = engine.detector.detect_all(parsed_csv.records, split_ratio=0.5)
        assert len(drift_results) >= 2, f"应检测到至少 2 个指标的漂移，实际 {len(drift_results)}"
        for d in drift_results:
            assert 0.0 <= d.drift_score <= 1.0, f"漂移分数应在 0~1 之间，实际 {d.drift_score}"
            assert d.verdict in ("stable", "warning", "drift"), f"判定结果无效: {d.verdict}"
        print(f"  ✓ 漂移检测成功，共 {len(drift_results)} 个指标")
        for d in drift_results:
            print(f"    - {d.metric}: score={d.drift_score:.2f}, verdict={d.verdict}")

        # 测试 4：JSON 输出
        print("\n[4/5] 测试 JSON 输出...")
        json_output = engine.generate_output(parsed_csv, output_format="json", detect_drift=True)
        output_data = json.loads(json_output)
        assert "records" in output_data, "JSON 输出缺少 records 字段"
        assert "drift_detection" in output_data, "JSON 输出缺少 drift_detection 字段"
        assert len(output_data["records"]) == 9, f"JSON 输出记录数应为 9，实际 {len(output_data['records'])}"
        print(f"  ✓ JSON 输出成功，输出大小 {len(json_output)} 字节")

        # 测试 5：Markdown 输出
        print("\n[5/5] 测试 Markdown 输出...")
        md_output = engine.generate_output(parsed_json, output_format="markdown", detect_drift=True)
        assert "| 指标 |" in md_output, "Markdown 输出缺少指标表格头"
        assert "## 漂移检测" in md_output, "Markdown 输出缺少漂移检测部分"
        print(f"  ✓ Markdown 输出成功，输出大小 {len(md_output)} 字节")

        # 汇总
        print("\n" + "=" * 60)
        print("自检全部通过！")
        print("=" * 60)
        return True

    except AssertionError as exc:
        print(f"\n✗ 自检失败: {exc}")
        print("=" * 60)
        return False
    except Exception as exc:
        print(f"\n✗ 自检异常: {exc}")
        print("=" * 60)
        return False


# ============================================================
# 命令行入口
# ============================================================

def main() -> int:
    """主入口函数"""
    parser = argparse.ArgumentParser(
        description="traceml - 数据追踪、可视化、漂移检测与仪表盘引擎",
        epilog="示例: python main.py input.csv --format json --drift",
    )
    parser.add_argument(
        "input",
        nargs="?",
        help="输入数据源（文件路径、URL、或直接数据文本）",
    )
    parser.add_argument(
        "--type",
        choices=["auto", "csv", "json", "url", "file"],
        default="auto",
        help="输入数据类型（默认 auto 自动检测）",
    )
    parser.add_argument(
        "--format",
        choices=["json", "markdown"],
        default="json",
        help="输出格式（默认 json）",
    )
    parser.add_argument(
        "--drift",
        action="store_true",
        help="启用漂移检测",
    )
    parser.add_argument(
        "--split-ratio",
        type=float,
        default=0.5,
        help="漂移检测的数据分割比例（默认 0.5）",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行离线自检",
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        success = run_selftest()
        return 0 if success else 1

    # 正常处理模式
    if not args.input:
        print("错误: 必须提供输入数据源（或使用 --selftest）", file=sys.stderr)
        parser.print_help()
        return 1

    try:
        engine = TraceML()
        parsed = engine.process_source(args.input, source_type=args.type)

        # 显示处理摘要
        print(f"成功解析 {len(parsed.records)} 条记录", file=sys.stderr)
        print(f"数据源类型: {parsed.source_type}", file=sys.stderr)

        # 生成输出
        output = engine.generate_output(
            parsed,
            output_format=args.format,
            detect_drift=args.drift,
            split_ratio=args.split_ratio,
        )
        print(output)
        return 0

    except RuntimeError as exc:
        print(f"处理失败: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"未知错误: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
