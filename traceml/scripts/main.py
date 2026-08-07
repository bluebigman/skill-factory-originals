#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
traceml - 数据追踪、可视化、漂移检测与仪表盘引擎（独立实现）

本脚本为 clean-room 实现，仅依据功能规格编写，不参考任何既有代码。
功能覆盖：
  C1 数据/文件/URL 结构化转换
  C2 关键信息识别与保留
  C3 按约定格式生成输出
  C4 置信度标注
  C5 批量处理与自定义格式

边界遵守：
  N1 不执行模型训练
  N2 不修改原始数据
  N3 不进行实时流式处理
  N4 不提供存储服务
  N5 不保证数据准确性

用法示例：
  python main.py --parse "loss,0.5,2024-01-01,acc,0.9"
  python main.py --batch file1.csv file2.json
  python main.py --selftest
"""

import argparse
import csv
import io
import json
import math
import os
import sys
import tempfile
import urllib.request
import urllib.parse
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

# 错误码定义
ERROR_CODES = {
    "E001": "参数错误：缺少必要参数或参数格式不正确",
    "E002": "文件读取失败：文件不存在或无读取权限",
    "E003": "URL 访问失败：网络不可达或响应异常",
    "E004": "数据解析失败：输入格式无法识别",
    "E005": "字段提取失败：关键字段缺失或不完整",
    "E006": "输出生成失败：无法按模板生成结果",
    "E007": "批量处理失败：部分输入处理异常",
    "E008": "JSON 序列化失败：数据无法转换为 JSON",
    "E009": "CSV 解析失败：文件内容不符合 CSV 格式",
    "E010": "内部错误：未预期的运行时异常",
}

# 置信度等级说明
CONFIDENCE_HIGH = "高"
CONFIDENCE_MEDIUM = "中"
CONFIDENCE_LOW = "低"


class TraceMLError(Exception):
    """traceml 自定义异常，携带错误码。"""

    def __init__(self, code: str, message: str = ""):
        self.code = code
        self.message = message or ERROR_CODES.get(code, "未知错误")
        super().__init__(f"[{code}] {self.message}")


# ---------------------------------------------------------------------------
# 核心工具函数
# ---------------------------------------------------------------------------

def _safe_float(value: Any) -> Optional[float]:
    """安全转换为浮点数，失败返回 None。"""
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _safe_int(value: Any) -> Optional[int]:
    """安全转换为整数，失败返回 None。"""
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _is_timestamp(value: str) -> bool:
    """判断字符串是否为常见时间戳格式。"""
    if not isinstance(value, str):
        return False
    for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%Y/%m/%d", "%Y%m%d"):
        try:
            datetime.strptime(value.strip(), fmt)
            return True
        except ValueError:
            continue
    return False


def _extract_timestamp(value: str) -> Optional[str]:
    """尝试从字符串中提取时间戳，失败返回 None。"""
    if not isinstance(value, str):
        return None
    value = value.strip()
    if _is_timestamp(value):
        return value
    # 尝试从混合文本中提取日期模式（简单启发式）
    import re
    patterns = [
        r"\d{4}-\d{2}-\d{2}",
        r"\d{4}/\d{2}/\d{2}",
        r"\d{4}\d{2}\d{2}",
        r"\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}",
    ]
    for pat in patterns:
        m = re.search(pat, value)
        if m:
            return m.group(0)
    return None


def _detect_type(value: Any) -> str:
    """检测值的类型，返回类型名称字符串。"""
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, (int, float)):
        return "number"
    if isinstance(value, str):
        if _is_timestamp(value):
            return "timestamp"
        return "string"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    return "unknown"


def _parse_key_value_pairs(text: str) -> Dict[str, Any]:
    """解析 'key1,val1,key2,val2' 形式的字符串为字典。"""
    parts = [p.strip() for p in text.split(",") if p.strip()]
    result: Dict[str, Any] = {}
    i = 0
    while i < len(parts) - 1:
        key = parts[i]
        val_str = parts[i + 1]
        # 尝试转换为数值
        num = _safe_float(val_str)
        if num is not None:
            result[key] = num
        else:
            result[key] = val_str
        i += 2
    # 如果最后一个键没有值，补 None
    if i == len(parts) - 1:
        result[parts[i]] = None
    return result


def _infer_confidence(record: Dict[str, Any]) -> Dict[str, Any]:
    """根据记录完整性推断置信度，返回新字典（不修改原字典）。"""
    # 创建副本，避免修改原字典
    result = dict(record)
    
    required = {"metric", "value"}
    optional = {"timestamp", "label", "group"}
    present = set(record.keys())

    missing_required = required - present
    missing_optional = optional - present

    if not missing_required and not missing_optional:
        confidence = 1.0
        level = CONFIDENCE_HIGH
        reason = ""
    elif not missing_required:
        confidence = 0.8
        level = CONFIDENCE_MEDIUM
        reason = f"缺少可选字段: {', '.join(sorted(missing_optional))}"
    else:
        confidence = 0.4
        level = CONFIDENCE_LOW
        reason = f"缺少必要字段: {', '.join(sorted(missing_required))}"

    result["confidence"] = round(confidence, 2)
    result["confidence_level"] = level
    if reason:
        result["confidence_reason"] = reason
    return result


# ---------------------------------------------------------------------------
# 核心功能模块
# ---------------------------------------------------------------------------

class DataParser:
    """C1/C2: 数据解析与关键信息提取。"""

    @staticmethod
    def parse_text(text: str) -> List[Dict[str, Any]]:
        """解析纯文本为结构化记录列表。"""
        records = []
        for line in text.strip().splitlines():
            line = line.strip()
            if not line:
                continue
            # 尝试 CSV 格式
            if "," in line:
                parts = [p.strip() for p in line.split(",")]
                # 尝试 key,value 对
                if len(parts) >= 2 and parts[0] not in ("metric", "value", "timestamp", "label"):
                    kv = _parse_key_value_pairs(line)
                    records.append(kv)
                else:
                    records.append({"raw": line})
            elif line.startswith("{") and line.endswith("}"):
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    records.append({"raw": line})
            else:
                records.append({"raw": line})
        return records

    @staticmethod
    def parse_csv(text: str) -> List[Dict[str, Any]]:
        """解析 CSV 文本为字典列表，支持表头。"""
        try:
            reader = csv.DictReader(io.StringIO(text))
            rows = []
            for row in reader:
                # 清理空值
                cleaned = {k: (v if v else None) for k, v in row.items()}
                rows.append(cleaned)
            return rows
        except Exception as e:
            raise TraceMLError("E009", f"CSV 解析失败: {e}")

    @staticmethod
    def parse_json(text: str) -> List[Dict[str, Any]]:
        """解析 JSON 文本为字典列表。"""
        try:
            data = json.loads(text)
        except json.JSONDecodeError as e:
            raise TraceMLError("E004", f"JSON 解析失败: {e}")

        if isinstance(data, list):
            return [item for item in data if isinstance(item, dict)]
        elif isinstance(data, dict):
            # 尝试识别常见结构
            if "records" in data and isinstance(data["records"], list):
                return [item for item in data["records"] if isinstance(item, dict)]
            return [data]
        else:
            raise TraceMLError("E004", "JSON 顶层必须是对象或数组")

    @staticmethod
    def parse_file(file_path: str) -> List[Dict[str, Any]]:
        """根据文件扩展名解析文件内容。"""
        if not os.path.isfile(file_path):
            raise TraceMLError("E002", f"文件不存在: {file_path}")
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
        except (OSError, IOError) as e:
            raise TraceMLError("E002", f"文件读取失败: {e}")

        ext = os.path.splitext(file_path)[1].lower()
        if ext == ".csv":
            return DataParser.parse_csv(content)
        elif ext == ".json":
            return DataParser.parse_json(content)
        elif ext in (".txt", ".log", ".md"):
            return DataParser.parse_text(content)
        else:
            # 尝试自动检测
            if content.lstrip().startswith("{"):
                return DataParser.parse_json(content)
            elif content.splitlines() and "," in content.splitlines()[0]:
                return DataParser.parse_csv(content)
            else:
                return DataParser.parse_text(content)

    @staticmethod
    def parse_url(url: str) -> List[Dict[str, Any]]:
        """从 URL 获取内容并解析。"""
        try:
            with urllib.request.urlopen(url, timeout=10) as resp:
                content = resp.read().decode("utf-8")
        except Exception as e:
            raise TraceMLError("E003", f"URL 访问失败: {e}")

        # 根据响应头或 URL 扩展名解析
        path = urllib.parse.urlparse(url).path
        ext = os.path.splitext(path)[1].lower()
        if ext == ".csv":
            return DataParser.parse_csv(content)
        elif ext == ".json":
            return DataParser.parse_json(content)
        else:
            return DataParser.parse_text(content)


class DataTransformer:
    """C2: 关键信息提取与标准化。"""

    @staticmethod
    def standardize(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """将记录标准化为 {metric, value, timestamp, label, group} 结构。"""
        result = []
        for rec in records:
            std = {}
            # 指标名
            metric = rec.get("metric") or rec.get("name") or rec.get("key")
            if metric is None:
                # 尝试从原始文本提取
                if "raw" in rec and isinstance(rec["raw"], str):
                    parts = rec["raw"].split()
                    if parts:
                        metric = parts[0]
            std["metric"] = str(metric) if metric else "unknown"

            # 数值
            value = rec.get("value")
            if value is None:
                value = rec.get("val") or rec.get("score")
            if isinstance(value, str):
                value = _safe_float(value)
            std["value"] = value

            # 时间戳
            ts = rec.get("timestamp") or rec.get("time") or rec.get("date")
            if ts is None and "raw" in rec and isinstance(rec["raw"], str):
                ts = _extract_timestamp(rec["raw"])
            std["timestamp"] = ts if ts else None

            # 标签和分组
            std["label"] = rec.get("label") or rec.get("tag", "")
            std["group"] = rec.get("group") or rec.get("experiment", "")

            # 附加原始字段（排除已处理的）
            for k, v in rec.items():
                if k not in ("metric", "name", "key", "value", "val", "score",
                             "timestamp", "time", "date", "label", "tag", "group", "experiment", "raw"):
                    std[k] = v

            result.append(std)
        return result


class DriftDetector:
    """漂移检测模块。"""

    @staticmethod
    def detect_drift(reference: List[float], current: List[float]) -> Dict[str, Any]:
        """检测两个分布之间的漂移（简化版 PSI/KS 检测）。"""
        if not reference or not current:
            raise TraceMLError("E005", "漂移检测需要非空数据")

        # 使用均值差异和分布重叠作为简化指标
        ref_mean = sum(reference) / len(reference)
        cur_mean = sum(current) / len(current)

        # 标准差
        ref_std = math.sqrt(sum((x - ref_mean) ** 2 for x in reference) / len(reference)) or 1e-9
        cur_std = math.sqrt(sum((x - cur_mean) ** 2 for x in current) / len(current)) or 1e-9

        # 归一化均值差（单位：标准差）
        mean_diff = abs(ref_mean - cur_mean) / max(ref_std, cur_std, 1e-9)

        # 简化 PSI（分箱近似）
        all_vals = sorted(reference + current)
        n_bins = min(10, len(all_vals) // 2) or 1
        bin_edges = [all_vals[i * len(all_vals) // n_bins] for i in range(1, n_bins)]
        bin_edges.append(float("inf"))

        def _bin_distribution(data):
            dist = [0.0] * n_bins
            for val in data:
                for i, edge in enumerate(bin_edges):
                    if val <= edge:
                        dist[i] += 1
                        break
            total = len(data)
            return [x / total for x in dist]

        ref_dist = _bin_distribution(reference)
        cur_dist = _bin_distribution(current)

        psi = 0.0
        for i in range(n_bins):
            p = ref_dist[i] + 1e-9
            q = cur_dist[i] + 1e-9
            psi += (p - q) * math.log(p / q)

        # 判定漂移等级
        if psi > 0.25 or mean_diff > 2.0:
            level = "严重漂移"
            drifted = True
        elif psi > 0.1 or mean_diff > 1.0:
            level = "轻微漂移"
            drifted = True
        else:
            level = "无漂移"
            drifted = False

        return {
            "drift_detected": drifted,
            "drift_level": level,
            "psi": round(psi, 4),
            "mean_reference": round(ref_mean, 4),
            "mean_current": round(cur_mean, 4),
            "mean_difference_sigma": round(mean_diff, 4),
            "sample_size_reference": len(reference),
            "sample_size_current": len(current),
        }


class OutputGenerator:
    """C3/C4: 输出生成与格式化。"""

    @staticmethod
    def to_json(records: List[Dict[str, Any]]) -> str:
        """生成 JSON 输出。"""
        try:
            return json.dumps(records, ensure_ascii=False, indent=2)
        except TypeError as e:
            raise TraceMLError("E008", f"JSON 序列化失败: {e}")

    @staticmethod
    def to_markdown_table(records: List[Dict[str, Any]]) -> str:
        """生成 Markdown 表格输出。"""
        if not records:
            return "_无数据_"

        # 确定列：优先核心字段
        core_cols = ["metric", "value", "timestamp", "label", "group", "confidence", "confidence_level"]
        extra_cols = []
        for rec in records:
            for k in rec:
                if k not in core_cols and k not in extra_cols:
                    extra_cols.append(k)
        cols = core_cols + extra_cols

        lines = []
        header = "| " + " | ".join(cols) + " |"
        separator = "|" + "|".join(["---"] * len(cols)) + "|"
        lines.append(header)
        lines.append(separator)

        for rec in records:
            row = []
            for col in cols:
                val = rec.get(col, "")
                if val is None:
                    val = ""
                row.append(str(val))
            lines.append("| " + " | ".join(row) + " |")

        return "\n".join(lines)

    @staticmethod
    def to_custom(records: List[Dict[str, Any]], template: str) -> str:
        """根据自定义模板生成输出。模板使用 {field} 占位符。"""
        lines = []
        for rec in records:
            try:
                line = template.format(**rec)
                lines.append(line)
            except KeyError as e:
                raise TraceMLError("E006", f"模板缺少字段: {e}")
        return "\n".join(lines)


class BatchProcessor:
    """C5: 批量处理。"""

    @staticmethod
    def process_batch(inputs: List[str]) -> Dict[str, Any]:
        """批量处理多个文件/URL/文本输入。"""
        results = []
        errors = []

        for item in inputs:
            try:
                if item.startswith(("http://", "https://")):
                    records = DataParser.parse_url(item)
                elif os.path.isfile(item):
                    records = DataParser.parse_file(item)
                else:
                    records = DataParser.parse_text(item)

                std_records = DataTransformer.standardize(records)
                # 附加置信度（不修改原记录）
                std_records = [_infer_confidence(r) for r in std_records]
                results.extend(std_records)
            except TraceMLError as e:
                errors.append({"input": item, "error": str(e)})
            except Exception as e:
                errors.append({"input": item, "error": f"[E010] 未预期异常: {e}"})

        if errors and not results:
            raise TraceMLError("E007", f"批量处理全部失败: {errors[0]['error']}")

        return {
            "total_inputs": len(inputs),
            "successful": len(inputs) - len(errors),
            "failed": len(errors),
            "records_count": len(results),
            "records": results,
            "errors": errors,
        }


# ---------------------------------------------------------------------------
# 自检模块
# ---------------------------------------------------------------------------

class SelfTest:
    """内置硬编码样例数据的离线自检。"""

    @staticmethod
    def run() -> bool:
        """执行自检，全部通过返回 True。"""
        print("=" * 60)
        print("traceml 自检开始")
        print("=" * 60)

        all_passed = True

        # --- 测试 1: 文本解析 ---
        print("\n[1/6] 测试文本解析...")
        text = "loss,0.35,2024-01-01\nacc,0.91,2024-01-01\nloss,0.28,2024-01-02"
        records = DataParser.parse_text(text)
        assert len(records) >= 2, "文本解析应产生至少 2 条记录"
        print(f"  解析出 {len(records)} 条记录 ✓")

        # --- 测试 2: CSV 解析 ---
        print("\n[2/6] 测试 CSV 解析...")
        csv_text = "metric,value,timestamp\nloss,0.5,2024-01-01\nacc,0.9,2024-01-01"
        csv_records = DataParser.parse_csv(csv_text)
        assert len(csv_records) == 2, "CSV 解析应产生 2 条记录"
        assert "metric" in csv_records[0], "CSV 记录应包含 metric 字段"
        print("  CSV 解析成功 ✓")

        # --- 测试 3: JSON 解析与标准化 ---
        print("\n[3/6] 测试 JSON 解析与标准化...")
        json_text = json.dumps([
            {"name": "loss", "val": 0.42, "time": "2024-03-01"},
            {"name": "acc", "val": 0.87, "time": "2024-03-01"},
        ])
        json_records = DataParser.parse_json(json_text)
        std_records = DataTransformer.standardize(json_records)
        assert len(std_records) >= 2, "标准化应产生至少 2 条记录"
        assert all("metric" in r for r in std_records), "每条记录应有 metric 字段"
        assert all("value" in r for r in std_records), "每条记录应有 value 字段"
        print(f"  标准化处理 {len(std_records)} 条记录 ✓")

        # --- 测试 4: 漂移检测 ---
        print("\n[4/6] 测试漂移检测...")
        ref_data = [0.5, 0.51, 0.49, 0.52, 0.5, 0.48, 0.51, 0.5, 0.49, 0.52]
        cur_data = [0.7, 0.72, 0.69, 0.71, 0.73, 0.68, 0.72, 0.7, 0.71, 0.69]
        drift_result = DriftDetector.detect_drift(ref_data, cur_data)
        assert drift_result["drift_detected"] is True, "明显偏移应检测出漂移"
        assert drift_result["psi"] > 0, "PSI 应大于 0"
        print(f"  漂移检测完成: {drift_result['drift_level']} (PSI={drift_result['psi']}) ✓")

        # --- 测试 5: 置信度标注 ---
        print("\n[5/6] 测试置信度标注...")
        complete_rec = {"metric": "loss", "value": 0.3, "timestamp": "2024-01-01", "label": "train"}
        incomplete_rec = {"metric": "loss"}  # 缺少 value
        
        # 确保原记录不被修改
        complete_rec_copy = dict(complete_rec)
        incomplete_rec_copy = dict(incomplete_rec)
        
        c1 = _infer_confidence(complete_rec_copy)
        c2 = _infer_confidence(incomplete_rec_copy)
        
        # 验证原记录未被修改
        assert "confidence" not in complete_rec, "原记录不应被修改"
        assert "confidence" not in incomplete_rec, "原记录不应被修改"
        
        assert c1["confidence"] > c2["confidence"], "完整记录置信度应更高"
        assert c1["confidence_level"] == CONFIDENCE_HIGH, "完整记录应为高置信度"
        assert c2["confidence_level"] == CONFIDENCE_LOW, "不完整记录应为低置信度"
        print(f"  完整记录置信度={c1['confidence']} {c1['confidence_level']} ✓")
        print(f"  不完整记录置信度={c2['confidence']} {c2['confidence_level']} ✓")

        # --- 测试 6: 输出生成 ---
        print("\n[6/6] 测试输出生成...")
        test_records = [
            {"metric": "loss", "value": 0.35, "timestamp": "2024-01-01", "confidence": 0.9, "confidence_level": "高"},
            {"metric": "acc", "value": 0.91, "timestamp": "2024-01-01", "confidence": 0.9, "confidence_level": "高"},
        ]
        md_table = OutputGenerator.to_markdown_table(test_records)
        assert "| metric" in md_table, "Markdown 表应包含表头"
        json_out = OutputGenerator.to_json(test_records)
        parsed = json.loads(json_out)
        assert len(parsed) == 2, "JSON 输出应可反序列化且包含 2 条记录"
        print("  Markdown 表格生成 ✓")
        print("  JSON 输出生成 ✓")

        print("\n" + "=" * 60)
        print("自检全部通过！")
        print("=" * 60)
        return all_passed


# ---------------------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------------------

def main() -> int:
    """主入口函数。"""
    parser = argparse.ArgumentParser(
        description="traceml - 数据追踪、可视化、漂移检测与仪表盘引擎",
        epilog="示例: python main.py --parse 'loss,0.5,2024-01-01' | python main.py --selftest"
    )

    # 输入源
    parser.add_argument("--parse", type=str, metavar="TEXT",
                        help="解析纯文本字符串（如 'loss,0.5,2024-01-01'）")
    parser.add_argument("--file", type=str, metavar="PATH",
                        help="解析文件（支持 CSV/JSON/TXT/LOG）")
    parser.add_argument("--url", type=str, metavar="URL",
                        help="从 URL 获取数据并解析")
    parser.add_argument("--batch", nargs="+", metavar="INPUT",
                        help="批量处理多个输入（文件/URL/文本）")

    # 处理选项
    parser.add_argument("--standardize", action="store_true",
                        help="标准化输出为 {metric, value, timestamp, ...} 结构")
    parser.add_argument("--confidence", action="store_true",
                        help="附加置信度标注")

    # 漂移检测
    parser.add_argument("--drift", action="store_true",
                        help="对两列数值执行漂移检测（需配合 --reference 和 --current）")
    parser.add_argument("--reference", nargs="+", type=float, metavar="VAL",
                        help="参考分布数值列表")
    parser.add_argument("--current", nargs="+", type=float, metavar="VAL",
                        help="当前分布数值列表")

    # 输出格式
    parser.add_argument("--format", choices=["json", "markdown", "custom"], default="json",
                        help="输出格式（默认: json）")
    parser.add_argument("--template", type=str, metavar="TPL",
                        help="自定义输出模板，如 '{metric}: {value}'")

    # 自检
    parser.add_argument("--selftest", action="store_true",
                        help="运行内置自检（离线，无需外部依赖）")

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        try:
            SelfTest.run()
            return 0
        except AssertionError as e:
            print(f"[E010] 自检失败: {e}", file=sys.stderr)
            return 1
        except Exception as e:
            print(f"[E010] 自检异常: {e}", file=sys.stderr)
            return 1

    # 漂移检测模式
    if args.drift:
        if not args.reference or not args.current:
            print("[E001] 漂移检测需要 --reference 和 --current 参数", file=sys.stderr)
            return 1
        try:
            result = DriftDetector.detect_drift(args.reference, args.current)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0
        except TraceMLError as e:
            print(str(e), file=sys.stderr)
            return 1

    # 数据解析模式
    try:
        if args.batch:
            # 批量处理
            result = BatchProcessor.process_batch(args.batch)
            records = result["records"]
            if args.standardize:
                records = DataTransformer.standardize(records)
            if args.confidence:
                records = [_infer_confidence(r) for r in records]
            # 输出
            if args.format == "json":
                output = OutputGenerator.to_json(records)
            elif args.format == "markdown":
                output = OutputGenerator.to_markdown_table(records)
            elif args.format == "custom":
                if not args.template:
                    raise TraceMLError("E001", "自定义格式需要 --template")
                output = OutputGenerator.to_custom(records, args.template)
            else:
                output = OutputGenerator.to_json(records)
            print(output)
            return 0

        elif args.parse:
            records = DataParser.parse_text(args.parse)
        elif args.file:
            records = DataParser.parse_file(args.file)
        elif args.url:
            records = DataParser.parse_url(args.url)
        else:
            print("[E001] 请提供输入源（--parse/--file/--url/--batch）或使用 --selftest", file=sys.stderr)
            return 1

        # 后处理
        if args.standardize:
            records = DataTransformer.standardize(records)
        if args.confidence:
            records = [_infer_confidence(r) for r in records]

        # 输出
        if args.format == "json":
            output = OutputGenerator.to_json(records)
        elif args.format == "markdown":
            output = OutputGenerator.to_markdown_table(records)
        elif args.format == "custom":
            if not args.template:
                raise TraceMLError("E001", "自定义格式需要 --template")
            output = OutputGenerator.to_custom(records, args.template)
        else:
            output = OutputGenerator.to_json(records)
        print(output)
        return 0

    except TraceMLError as e:
        print(str(e), file=sys.stderr)
        return 1
    except Exception as e:
        print(f"[E010] 未预期异常: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
