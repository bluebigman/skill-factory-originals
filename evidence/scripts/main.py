#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
run.py — evidence 技能核心实现

功能：
- 数据清洗与标准化
- 字段映射
- 证据链生成（哈希指纹）
- 图表数据生成
- 校验报告
- 批量处理
- 预览模式（--dry-run）
- 自检（--selftest）

错误码：
E001: 参数解析失败
E002: 输入数据格式非法
E003: 数据行数超过上限
E004: 字段映射失败
E005: 图表类型不支持
E006: 模板配置非法
E007: 置信度计算失败
E008: 批量处理失败
E009: 自检数据不合法
E010: 内部逻辑异常

仅使用 Python 标准库。
"""

import argparse
import csv
import hashlib
import json
import math
import os
import re
import sys
import tempfile
import time
import traceback
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# 常量定义
# ---------------------------------------------------------------------------

MAX_DATA_ROWS = int(os.environ.get("EVIDENCE_MAX_ROWS", "100000"))
BATCH_SIZE = int(os.environ.get("EVIDENCE_BATCH_SIZE", "1000"))
MAX_WORKERS = int(os.environ.get("EVIDENCE_MAX_WORKERS", "4"))
MAX_RETRIES = int(os.environ.get("EVIDENCE_MAX_RETRIES", "3"))
RETRY_BASE_DELAY = float(os.environ.get("EVIDENCE_RETRY_BASE_DELAY", "1.0"))
RETRY_MAX_DELAY = float(os.environ.get("EVIDENCE_RETRY_MAX_DELAY", "10.0"))

CONFIDENCE_HIGH = "高"
CONFIDENCE_MEDIUM = "中"
CONFIDENCE_LOW = "低"

SUPPORTED_CHART_TYPES = {"bar", "line", "pie", "sankey"}

DEFAULT_TEMPLATE = {
    "字段顺序": ["日期", "项目", "金额", "状态"],
    "分组方式": "无",
    "图表偏好": "bar",
}

# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------


def _now_utc() -> datetime:
    """获取当前 UTC 时间。"""
    return datetime.now(timezone.utc)


def _atomic_write(file_path: str, content: str) -> None:
    """
    原子写入文件，跨平台安全。
    使用临时文件 + os.replace 确保原子性。
    """
    dir_path = os.path.dirname(os.path.abspath(file_path))
    os.makedirs(dir_path, exist_ok=True)
    fd, temp_path = tempfile.mkstemp(dir=dir_path, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
        os.replace(temp_path, file_path)
    except Exception:
        if os.path.exists(temp_path):
            os.unlink(temp_path)
        raise


def _read_file_with_encoding(file_path: str) -> str:
    """
    读取文件内容，自动尝试多种编码。
    优先 utf-8，然后 gbk，最后 gb18030。
    """
    encodings = ["utf-8", "gbk", "gb18030"]
    for encoding in encodings:
        try:
            with open(file_path, "r", encoding=encoding) as f:
                return f.read()
        except UnicodeDecodeError:
            continue
        except FileNotFoundError:
            raise
    # 最后尝试 with errors="replace"
    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


def _parse_csv_content(content: str) -> List[Dict[str, Any]]:
    """解析 CSV 内容为字典列表。"""
    reader = csv.DictReader(content.splitlines())
    return [row for row in reader]


def _parse_json_content(content: str) -> List[Dict[str, Any]]:
    """解析 JSON 内容为字典列表。"""
    data = json.loads(content)
    if isinstance(data, list):
        return data
    elif isinstance(data, dict):
        # 尝试找到列表字段
        for key, value in data.items():
            if isinstance(value, list):
                return value
        return [data]
    else:
        raise ValueError("JSON 内容必须是对象或数组")


def _detect_format(file_path: str) -> str:
    """根据文件扩展名检测格式。"""
    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".csv":
        return "csv"
    elif ext == ".json":
        return "json"
    else:
        return "csv"  # 默认按 CSV 处理


def _calculate_hash(data: Dict[str, Any]) -> str:
    """计算数据行的 SHA-256 哈希。"""
    content = json.dumps(data, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _calculate_confidence(row: Dict[str, Any]) -> str:
    """
    计算数据行置信度。
    高：无缺失值，格式统一
    中：有少量缺失值
    低：有大量缺失值或格式异常
    """
    if not row:
        return CONFIDENCE_LOW

    total_fields = len(row)
    if total_fields == 0:
        return CONFIDENCE_LOW

    missing_fields = sum(1 for v in row.values() if v is None or str(v).strip() == "")
    missing_ratio = missing_fields / total_fields

    if missing_ratio == 0:
        return CONFIDENCE_HIGH
    elif missing_ratio < 0.3:
        return CONFIDENCE_MEDIUM
    else:
        return CONFIDENCE_LOW


def _format_timestamp(dt: datetime) -> str:
    """格式化时间戳为 YYYYMMDDHHMMSS。"""
    return dt.strftime("%Y%m%d%H%M%S")


def _generate_output_filename(original: str, timestamp: str, ext: str) -> str:
    """生成输出文件名。"""
    base = os.path.splitext(os.path.basename(original))[0]
    return f"{base}_{timestamp}.{ext}"


# ---------------------------------------------------------------------------
# 核心处理类
# ---------------------------------------------------------------------------


class EvidenceProcessor:
    """证据链处理器。"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.mapping = self.config.get("mapping", {})
        self.template = self.config.get("template", DEFAULT_TEMPLATE)
        self.evidence_chain = []
        self.stats = {
            "total_rows": 0,
            "processed_rows": 0,
            "missing_values": 0,
            "duplicates_removed": 0,
            "mapping_applied": 0,
            "errors": [],
        }

    def process_file(self, file_path: str, dry_run: bool = False) -> Dict[str, Any]:
        """
        处理单个文件。
        返回处理结果摘要。
        """
        try:
            # 检测格式并读取
            fmt = _detect_format(file_path)
            content = _read_file_with_encoding(file_path)

            if fmt == "csv":
                data = _parse_csv_content(content)
            elif fmt == "json":
                data = _parse_json_content(content)
            else:
                raise ValueError(f"不支持的文件格式: {fmt}")

            # 检查行数
            if len(data) > MAX_DATA_ROWS:
                raise ValueError(
                    f"数据行数 {len(data)} 超过上限 {MAX_DATA_ROWS}，"
                    f"请设置 EVIDENCE_MAX_ROWS 环境变量"
                )

            # 处理数据
            processed_data = self._process_data(data)

            # 生成输出
            timestamp = _format_timestamp(_now_utc())
            output_dir = os.path.dirname(os.path.abspath(file_path))
            output_base = _generate_output_filename(file_path, timestamp, "csv")

            if not dry_run:
                # 写入清洗后数据
                output_path = os.path.join(output_dir, output_base)
                self._write_csv(processed_data, output_path)

                # 生成证据链
                if self.evidence_chain:
                    evidence_path = os.path.join(
                        output_dir,
                        _generate_output_filename(file_path, timestamp, "json"),
                    )
                    self._write_evidence_chain(evidence_path)

                # 生成校验报告
                report_path = os.path.join(
                    output_dir,
                    _generate_output_filename(file_path, timestamp, "md"),
                )
                self._write_validation_report(report_path)

            return {
                "file": file_path,
                "output_base": output_base,
                "rows": len(processed_data),
                "stats": self.stats,
                "dry_run": dry_run,
            }

        except Exception as e:
            self.stats["errors"].append(str(e))
            raise


    def _process_data(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """处理数据：清洗、映射、计算置信度。"""
        processed = []
        seen_hashes = set()

        for row in data:
            # 跳过 None 行
            if row is None:
                continue

            # 应用字段映射
            mapped_row = self._apply_mapping(row)

            # 清洗数据
            cleaned_row = self._clean_row(mapped_row)

            # 计算哈希
            row_hash = _calculate_hash(cleaned_row)

            # 去重
            if row_hash in seen_hashes:
                self.stats["duplicates_removed"] += 1
                continue
            seen_hashes.add(row_hash)

            # 计算置信度
            confidence = _calculate_confidence(cleaned_row)
            cleaned_row["_confidence"] = confidence

            # 添加到证据链
            self.evidence_chain.append(
                {
                    "hash": row_hash,
                    "timestamp": _now_utc().isoformat(),
                    "confidence": confidence,
                    "row": cleaned_row,
                }
            )

            processed.append(cleaned_row)
            self.stats["processed_rows"] += 1

        self.stats["total_rows"] = len(data)
        return processed


    def _apply_mapping(self, row: Dict[str, Any]) -> Dict[str, Any]:
        """应用字段映射。"""
        if not self.mapping:
            return row

        mapped = {}
        for src, dst in self.mapping.items():
            if src in row:
                mapped[dst] = row[src]
                self.stats["mapping_applied"] += 1
            else:
                mapped[dst] = None

        # 保留未映射的字段
        for key, value in row.items():
            if key not in self.mapping:
                mapped[key] = value

        return mapped


    def _clean_row(self, row: Dict[str, Any]) -> Dict[str, Any]:
        """清洗单行数据。"""
        cleaned = {}
        for key, value in row.items():
            if value is None:
                cleaned[key] = ""
                self.stats["missing_values"] += 1
            elif isinstance(value, str):
                # 去除首尾空白
                cleaned[key] = value.strip()
                # 处理空字符串
                if cleaned[key] == "":
                    self.stats["missing_values"] += 1
            else:
                cleaned[key] = value
        return cleaned


    def _write_csv(self, data: List[Dict[str, Any]], file_path: str) -> None:
        """写入 CSV 文件。"""
        if not data:
            _atomic_write(file_path, "")
            return

        # 获取所有字段
        fieldnames = list(data[0].keys())
        for row in data:
            for key in row.keys():
                if key not in fieldnames:
                    fieldnames.append(key)

        # 写入 CSV
        with open(file_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(data)


    def _write_evidence_chain(self, file_path: str) -> None:
        """写入证据链文件。"""
        evidence_data = {
            "generated_at": _now_utc().isoformat(),
            "total_records": len(self.evidence_chain),
            "chain": self.evidence_chain,
        }
        _atomic_write(file_path, json.dumps(evidence_data, ensure_ascii=False, indent=2))


    def _write_validation_report(self, file_path: str) -> None:
        """写入校验报告。"""
        total = self.stats["total_rows"]
        processed = self.stats["processed_rows"]
        missing = self.stats["missing_values"]
        duplicates = self.stats["duplicates_removed"]

        # 计算完整率
        if total > 0:
            completeness = (processed / total) * 100
        else:
            completeness = 0.0

        report = f"""# 数据校验报告

生成时间: {_now_utc().isoformat()}

## 数据统计

| 指标 | 值 |
|------|-----|
| 总行数 | {total} |
| 处理行数 | {processed} |
| 缺失值 | {missing} |
| 重复行 | {duplicates} |
| 完整率 | {completeness:.1f}% |

## 置信度分布

"""
        # 统计置信度
        confidence_counts = {"高": 0, "中": 0, "低": 0}
        for item in self.evidence_chain:
            conf = item["confidence"]
            if conf in confidence_counts:
                confidence_counts[conf] += 1

        for level, count in confidence_counts.items():
            report += f"- {level}: {count}\n"

        # 错误信息
        if self.stats["errors"]:
            report += "\n## 错误信息\n\n"
            for error in self.stats["errors"]:
                report += f"- {error}\n"

        _atomic_write(file_path, report)


# ---------------------------------------------------------------------------
# 图表生成
# ---------------------------------------------------------------------------


def generate_chart_data(
    data: List[Dict[str, Any]],
    chart_type: str,
    x_field: Optional[str] = None,
    y_field: Optional[str] = None,
) -> Dict[str, Any]:
    """
    生成图表数据（不生成图片，只生成数据）。
    返回可用于前端渲染的图表数据。
    """
    if chart_type not in SUPPORTED_CHART_TYPES:
        raise ValueError(f"不支持的图表类型: {chart_type}")

    if not data:
        return {"type": chart_type, "data": []}

    # 自动选择字段
    if not x_field or not y_field:
        numeric_fields = []
        for key in data[0].keys():
            if key.startswith("_"):
                continue
            try:
                float(data[0][key])
                numeric_fields.append(key)
            except (ValueError, TypeError):
                pass

        if len(numeric_fields) >= 2:
            y_field = y_field or numeric_fields[0]
            x_field = x_field or numeric_fields[1]
        elif len(numeric_fields) == 1:
            y_field = y_field or numeric_fields[0]
            x_field = x_field or "index"
        else:
            # 没有数值字段，使用第一个字段
            x_field = x_field or list(data[0].keys())[0]
            y_field = y_field or "count"

    # 生成图表数据
    chart_data = []
    for i, row in enumerate(data):
        x_value = row.get(x_field, i) if x_field != "index" else i
        y_value = row.get(y_field, 0)

        try:
            y_value = float(y_value)
        except (ValueError, TypeError):
            y_value = 0

        chart_data.append({"x": x_value, "y": y_value})

    return {"type": chart_type, "data": chart_data, "x_field": x_field, "y_field": y_field}


# ---------------------------------------------------------------------------
# 批量处理
# ---------------------------------------------------------------------------


def batch_process(
    input_paths: List[str],
    output_dir: str,
    chart_types: List[str],
    config: Optional[Dict[str, Any]] = None,
    dry_run: bool = False,
    batch_size: int = BATCH_SIZE,
    verbose: bool = False,
) -> List[Dict[str, Any]]:
    """
    批量处理多个文件。
    使用线程池并行处理。
    """
    results = []
    processor = EvidenceProcessor(config)

    def process_one(file_path: str) -> Dict[str, Any]:
        try:
            result = processor.process_file(file_path, dry_run=dry_run)
            if verbose:
                print(f"[OK] {file_path}: {result['rows']} 行")
            return result
        except Exception as e:
            if verbose:
                print(f"[ERROR] {file_path}: {e}", file=sys.stderr)
            return {"file": file_path, "error": str(e)}

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = [executor.submit(process_one, path) for path in input_paths]
        for future in as_completed(futures):
            results.append(future.result())

    return results


# ---------------------------------------------------------------------------
# 自检程序
# ---------------------------------------------------------------------------


def run_selftest() -> int:
    """
    运行自检程序。
    验证核心功能是否正常。
    返回 0 表示成功，非 0 表示失败。
    """
    print("=== evidence 自检程序 ===")
    failures = 0

    # 测试 1：数据清洗
    print("\n[测试 1] 数据清洗...")
    try:
        test_data = [
            {"日期": "2024-01-01", "项目": "A", "金额": "100", "状态": "完成"},
            {"日期": "2024-01-02", "项目": "B", "金额": "200", "状态": "进行中"},
            {"日期": "2024-01-03", "项目": "C", "金额": "", "状态": "完成"},
            {"日期": "2024-01-01", "项目": "A", "金额": "100", "状态": "完成"},  # 重复
        ]
        processor = EvidenceProcessor()
        processed = processor._process_data(test_data)
        assert len(processed) == 3, f"预期 3 行，实际 {len(processed)} 行"
        assert processor.stats["duplicates_removed"] == 1, "应去除 1 个重复"
        assert processor.stats["missing_values"] >= 1, "应检测到缺失值"
        print("[PASS] 数据清洗正常")
    except Exception as e:
        print(f"[FAIL] 数据清洗异常: {e}")
        failures += 1

    # 测试 2：字段映射
    print("\n[测试 2] 字段映射...")
    try:
        config = {"mapping": {"日期": "date", "项目": "project", "金额": "amount"}}
        processor = EvidenceProcessor(config)
        mapped = processor._apply_mapping({"日期": "2024-01-01", "项目": "A", "金额": "100"})
        assert "date" in mapped, "映射后应包含 date 字段"
        assert "project" in mapped, "映射后应包含 project 字段"
        assert "amount" in mapped, "映射后应包含 amount 字段"
        assert mapped["date"] == "2024-01-01", "date 值不正确"
        print("[PASS] 字段映射正常")
    except Exception as e:
        print(f"[FAIL] 字段映射异常: {e}")
        failures += 1

    # 测试 3：证据链生成
    print("\n[测试 3] 证据链生成...")
    try:
        test_data = [
            {"日期": "2024-01-01", "项目": "A", "金额": "100"},
            {"日期": "2024-01-02", "项目": "B", "金额": "200"},
        ]
        processor = EvidenceProcessor()
        processed = processor._process_data(test_data)
        assert len(processor.evidence_chain) == 2, "证据链应有 2 条记录"
        assert all("hash" in item for item in processor.evidence_chain), "每条记录应有哈希"
        assert all("timestamp" in item for item in processor.evidence_chain), "每条记录应有时间戳"
        print("[PASS] 证据链生成正常")
    except Exception as e:
        print(f"[FAIL] 证据链生成异常: {e}")
        failures += 1

    # 测试 4：图表数据生成
    print("\n[测试 4] 图表数据生成...")
    try:
        test_data = [
            {"日期": "2024-01-01", "项目": "A", "金额": "100"},
            {"日期": "2024-01-02", "项目": "B", "金额": "200"},
            {"日期": "2024-01-03", "项目": "C", "金额": "300"},
        ]
        chart_data = generate_chart_data(test_data, "bar")
        assert chart_data["type"] == "bar", "图表类型应为 bar"
        assert len(chart_data["data"]) == 3, "图表数据应有 3 条"
        assert all("x" in item and "y" in item for item in chart_data["data"]), "每条数据应有 x 和 y"
        print("[PASS] 图表数据生成正常")
    except Exception as e:
        print(f"[FAIL] 图表数据生成异常: {e}")
        failures += 1

    # 测试 5：置信度计算
    print("\n[测试 5] 置信度计算...")
    try:
        assert _calculate_confidence({"a": "1", "b": "2"}) == CONFIDENCE_HIGH, "完整数据应为高置信度"
        # 修复：{"a": "1", "b": ""} 缺失 1/2 = 0.5，应返回低置信度
        assert _calculate_confidence({"a": "1", "b": ""}) == CONFIDENCE_LOW, "缺失 50% 应为低置信度"
        assert _calculate_confidence({"a": "", "b": ""}) == CONFIDENCE_LOW, "大量缺失应为低置信度"
        print("[PASS] 置信度计算正常")
    except Exception as e:
        print(f"[FAIL] 置信度计算异常: {e}")
        failures += 1

    # 测试 6：文件读写
    print("\n[测试 6] 文件读写...")
    try:
        # 创建临时文件
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8") as f:
            f.write("日期,项目,金额\n2024-01-01,A,100\n2024-01-02,B,200\n")
            temp_path = f.name

        # 读取并处理
        content = _read_file_with_encoding(temp_path)
        data = _parse_csv_content(content)
        assert len(data) == 2, "应读取 2 行数据"

        # 清理
        os.unlink(temp_path)
        print("[PASS] 文件读写正常")
    except Exception as e:
        print(f"[FAIL] 文件读写异常: {e}")
        failures += 1

    # 测试 7：原子写入
    print("\n[测试 7] 原子写入...")
    try:
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
            temp_path = f.name
        os.unlink(temp_path)

        _atomic_write(temp_path, "测试内容")
        with open(temp_path, "r", encoding="utf-8") as f:
            content = f.read()
        assert content == "测试内容", "写入内容不正确"
        os.unlink(temp_path)
        print("[PASS] 原子写入正常")
    except Exception as e:
        print(f"[FAIL] 原子写入异常: {e}")
        failures += 1

    # 测试 8：批量处理
    print("\n[测试 8] 批量处理...")
    try:
        # 创建临时目录
        temp_dir = tempfile.mkdtemp()
        file1 = os.path.join(temp_dir, "test1.csv")
        file2 = os.path.join(temp_dir, "test2.csv")

        with open(file1, "w", encoding="utf-8") as f:
            f.write("日期,项目,金额\n2024-01-01,A,100\n")
        with open(file2, "w", encoding="utf-8") as f:
            f.write("日期,项目,金额\n2024-01-02,B,200\n")

        results = batch_process([file1, file2], temp_dir, ["bar"], dry_run=True)
        assert len(results) == 2, "应处理 2 个文件"
        assert all("file" in r for r in results), "每个结果应有文件路径"

        # 清理
        os.unlink(file1)
        os.unlink(file2)
        os.rmdir(temp_dir)
        print("[PASS] 批量处理正常")
    except Exception as e:
        print(f"[FAIL] 批量处理异常: {e}")
        failures += 1

    # 测试 9：空输入处理
    print("\n[测试 9] 空输入处理...")
    try:
        processor = EvidenceProcessor()
        processed = processor._process_data([])
        assert len(processed) == 0, "空输入应返回空列表"
        assert processor.stats["total_rows"] == 0, "统计应为 0"
        print("[PASS] 空输入处理正常")
    except Exception as e:
        print(f"[FAIL] 空输入处理异常: {e}")
        failures += 1

    # 测试 10：异常输入处理
    print("\n[测试 10] 异常输入处理...")
    try:
        processor = EvidenceProcessor()
        processed = processor._process_data([None, {"a": "1"}])
        assert len(processed) == 1, "应处理 1 行（None 行被跳过）"
        assert processor.stats["total_rows"] == 2, "总行数应为 2"
        print("[PASS] 异常输入处理正常")
    except Exception as e:
        print(f"[FAIL] 异常输入处理异常: {e}")
        failures += 1

    # 汇总
    print(f"\n=== 自检完成: {10 - failures}/10 通过 ===")
    return 0 if failures == 0 else 1


# ---------------------------------------------------------------------------
# 主程序
# ---------------------------------------------------------------------------


def main() -> int:
    """主入口。"""
    parser = argparse.ArgumentParser(
        description="数据核验与证据链构建工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python run.py --input data.csv --output out/ --chart-type bar
  python run.py --input data.csv --dry-run
  python run.py --input data/ --batch-size 500
  python run.py --selftest
        """,
    )

    parser.add_argument(
        "--input",
        type=str,
        help="输入文件或目录路径",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="./output",
        help="输出目录 (默认: ./output)",
    )
    parser.add_argument(
        "--chart-type",
        type=str,
        default="bar",
        help="图表类型，逗号分隔 (bar,line,pie,sankey) (默认: bar)",
    )
    parser.add_argument(
        "--config",
        type=str,
        help="配置文件路径 (YAML/JSON)",
    )
    parser.add_argument(
        "--mapping",
        type=str,
        help="字段映射 JSON 字符串，如 '{\"旧字段\":\"新字段\"}'",
    )
    parser.add_argument(
        "--evidence",
        action="store_true",
        help="生成证据链",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=BATCH_SIZE,
        help=f"批处理大小 (默认: {BATCH_SIZE})",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="预览模式，不写文件",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="显示详细日志",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行自检程序",
    )
    parser.add_argument(
        "--version",
        action="version",
        version="evidence 2.0.0",
    )

    args = parser.parse_args()

    # 运行自检（必须在所有必填校验之前）
    if args.selftest:
        return run_selftest()

    # 检查必要参数
    if not args.input:
        parser.error("必须指定 --input 参数")

    # 解析配置
    config = {}
    if args.config:
        try:
            content = _read_file_with_encoding(args.config)
            if args.config.endswith(".json"):
                config = json.loads(content)
            else:
                # 简单 YAML 解析（仅支持 mapping 字段）
                mapping = {}
                for line in content.splitlines():
                    line = line.strip()
                    if line.startswith("mapping:") or line.startswith("  "):
                        continue
                    if ":" in line and not line.startswith("#"):
                        key, value = line.split(":", 1)
                        mapping[key.strip()] = value.strip()
                if mapping:
                    config["mapping"] = mapping
        except Exception as e:
            print(f"E006: 配置文件解析失败: {e}", file=sys.stderr)
            return 6

    # 解析命令行映射
    if args.mapping:
        try:
            mapping = json.loads(args.mapping)
            config["mapping"] = mapping
        except json.JSONDecodeError as e:
            print(f"E001: 映射参数解析失败: {e}", file=sys.stderr)
            return 1

    # 解析图表类型
    chart_types = [t.strip() for t in args.chart_type.split(",")]
    for chart_type in chart_types:
        if chart_type not in SUPPORTED_CHART_TYPES:
            print(f"E005: 不支持的图表类型: {chart_type}", file=sys.stderr)
            print(f"支持的类型: {', '.join(sorted(SUPPORTED_CHART_TYPES))}", file=sys.stderr)
            return 5

    # 收集输入文件
    input_paths = []
    if os.path.isfile(args.input):
        input_paths.append(args.input)
    elif os.path.isdir(args.input):
        for root, dirs, files in os.walk(args.input):
            for file in files:
                if file.endswith((".csv", ".json")):
                    input_paths.append(os.path.join(root, file))
    else:
        print(f"E002: 输入路径不存在: {args.input}", file=sys.stderr)
        return 2

    if not input_paths:
        print("E002: 未找到输入文件", file=sys.stderr)
        return 2

    # 创建输出目录
    if not args.dry_run:
        os.makedirs(args.output, exist_ok=True)

    # 批量处理
    try:
        results = batch_process(
            input_paths,
            args.output,
            chart_types,
            config=config,
            dry_run=args.dry_run,
            batch_size=args.batch_size,
            verbose=args.verbose,
        )

        # 输出结果摘要
        success_count = 0
        error_count = 0
        for result in results:
            if "error" in result:
                error_count += 1
                if args.verbose:
                    print(f"  [ERROR] {result['file']}: {result['error']}", file=sys.stderr)
            else:
                success_count += 1
                if args.verbose:
                    print(f"  [OK] {result['file']}: {result['rows']} 行")

        print(f"\n处理完成: {success_count} 成功, {error_count} 失败")

        if args.dry_run:
            print("\n[DRY-RUN] 未写入任何文件")

        return 0 if error_count == 0 else 8

    except Exception as e:
        print(f"E010: 内部逻辑异常: {e}", file=sys.stderr)
        if args.verbose:
            traceback.print_exc()
        return 10


if __name__ == "__main__":
    sys.exit(main())
