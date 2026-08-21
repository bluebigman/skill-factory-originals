#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py — evidence 技能核心逻辑实现（Clean-Room 独立实现）

功能概览：
- 数据接入与结构化（C1/C2）
- 可视化图表数据生成（C3）
- 置信度标注（C4）
- 批量处理与模板支持（C5）
- 离线自检（--selftest）

错误码说明：
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

仅使用 Python 标准库实现。
"""

import argparse
import csv
import json
import math
import os
import re
import sys
import tempfile
from collections import OrderedDict
from datetime import timezone, datetime
from typing import Any, Dict, List, Optional, Tuple
dry_run = False  # v3.274 模块级 dry-run 标志

# ---------------------------------------------------------------------------
# 常量定义
# ---------------------------------------------------------------------------

# 数据行数上限（R4）
MAX_DATA_ROWS = 100_000

# 置信度等级
CONFIDENCE_HIGH = "高"
CONFIDENCE_MEDIUM = "中"
CONFIDENCE_LOW = "低"

# 支持的图表类型
SUPPORTED_CHART_TYPES = {"柱状图", "折线图", "饼图", "桑基图"}

# 默认模板配置
DEFAULT_TEMPLATE = {
    "字段顺序": ["日期", "项目", "金额", "状态"],
    "分组方式": "无",
    "图表偏好": "柱状图",
}


# ---------------------------------------------------------------------------
# 数据模型
# ---------------------------------------------------------------------------

class DataRecord:
    """单条数据记录的内部统一模型。"""

    def __init__(self, fields: Dict[str, Any], confidence: Dict[str, str]):
        """
        :param fields: 字段名 -> 字段值
        :param confidence: 字段名 -> 置信度等级
        """
        self.fields = fields
        self.confidence = confidence

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典表示（低置信度字段使用占位符）。"""
        result = {}
        for key, value in self.fields.items():
            if self.confidence.get(key) == CONFIDENCE_LOW:
                result[key] = f"[需核实:{key}]"
            else:
                result[key] = value
        return result


class DataSet:
    """结构化数据集。"""

    def __init__(self, records: List[DataRecord], field_names: List[str]):
        self.records = records
        self.field_names = field_names

    def __len__(self) -> int:
        return len(self.records)

    def to_table(self) -> List[Dict[str, Any]]:
        """转为表格字典列表。"""
        return [r.to_dict() for r in self.records]


# ---------------------------------------------------------------------------
# 数据接入与解析（C1）
# ---------------------------------------------------------------------------

def load_data_from_text(text: str) -> List[Dict[str, str]]:
    """
    从粘贴文本解析数据。
    支持格式：
    - CSV（逗号分隔）
    - TSV（制表符分隔）
    - 简单键值对（每行 "字段: 值"）

    返回字段字典列表。
    """
    if not text or not text.strip():
        raise ValueError("E002: 输入文本为空")

    lines = [line.strip() for line in text.strip().splitlines() if line.strip()]
    if not lines:
        raise ValueError("E002: 输入文本无有效内容")

    # 尝试检测分隔符
    first_line = lines[0]
    if "," in first_line:
        delimiter = ","
    elif "\t" in first_line:
        delimiter = "\t"
    else:
        delimiter = None

    if delimiter:
        # CSV/TSV 格式
        reader = csv.reader(lines, delimiter=delimiter)
        rows = list(reader)
        if len(rows) < 2:
            raise ValueError("E002: CSV 数据至少需要表头和一行数据")

        headers = [h.strip() for h in rows[0]]
        data = []
        for row in rows[1:]:
            if len(row) != len(headers):
                # 列数不匹配，填充空字符串
                row = list(row) + [""] * (len(headers) - len(row))
            data.append(OrderedDict(zip(headers, [c.strip() for c in row])))
        return data
    else:
        # 键值对格式
        data = []
        record = OrderedDict()
        for line in lines:
            if ":" in line:
                key, _, value = line.partition(":")
                record[key.strip()] = value.strip()
            else:
                # 新记录开始
                if record:
                    data.append(record)
                record = OrderedDict()
        if record:
            data.append(record)
        if not data:
            raise ValueError("E002: 无法识别的文本格式")
        return data


def load_data_from_json(json_text: str) -> List[Dict[str, str]]:
    """从 JSON 文本解析数据。支持列表或对象列表。"""
    try:
        parsed = json.loads(json_text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"E002: JSON 解析失败: {exc}") from exc

    if isinstance(parsed, list):
        if not all(isinstance(item, dict) for item in parsed):
            raise ValueError("E002: JSON 列表元素必须是对象")
        return [OrderedDict((str(k), str(v)) for k, v in item.items()) for item in parsed]
    elif isinstance(parsed, dict):
        # 单条记录
        return [OrderedDict((str(k), str(v)) for k, v in parsed.items())]
    else:
        raise ValueError("E002: JSON 必须是对象或对象列表")


def load_data_from_file(file_path: str) -> List[Dict[str, str]]:
    """从本地文件读取数据（CSV/TSV/JSON）。"""
    if not os.path.isfile(file_path):
        raise ValueError(f"E002: 文件不存在: {file_path}")

    ext = os.path.splitext(file_path)[1].lower()
    try:
        with open(file_path, "r", encoding="utf-8-sig") as fh:
            content = fh.read()
    except (IOError, OSError) as exc:
        raise ValueError(f"E002: 文件读取失败: {exc}") from exc

    if ext in (".json",):
        return load_data_from_json(content)
    elif ext in (".csv", ".tsv", ".txt"):
        return load_data_from_text(content)
    else:
        raise ValueError(f"E002: 不支持的文件类型: {ext}")


# ---------------------------------------------------------------------------
# 关键信息识别与结构化（C2）
# ---------------------------------------------------------------------------

# 常见字段名模式
DATE_PATTERNS = [r"日期", r"date", r"时间", r"time"]
AMOUNT_PATTERNS = [r"金额", r"amount", r"价格", r"price", r"费用", r"cost"]
CATEGORY_PATTERNS = [r"项目", r"类别", r"分类", r"category", r"type", r"项目"]
STATUS_PATTERNS = [r"状态", r"status", r"结果", r"result"]

# 日期格式识别
DATE_FORMATS = [
    "%Y-%m-%d",
    "%Y/%m/%d",
    "%Y年%m月%d日",
    "%m-%d-%Y",
    "%m/%d/%Y",
]


def _detect_field_type(header: str) -> str:
    """根据表头名称推断字段类型。"""
    header_lower = header.lower()
    for pattern in DATE_PATTERNS:
        if re.search(pattern, header_lower, re.IGNORECASE):
            return "date"
    for pattern in AMOUNT_PATTERNS:
        if re.search(pattern, header_lower, re.IGNORECASE):
            return "amount"
    for pattern in CATEGORY_PATTERNS:
        if re.search(pattern, header_lower, re.IGNORECASE):
            return "category"
    for pattern in STATUS_PATTERNS:
        if re.search(pattern, header_lower, re.IGNORECASE):
            return "status"
    return "text"


def _parse_date(value: str) -> Optional[datetime]:
    """尝试解析日期字符串。"""
    value = value.strip()
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    # 尝试 ISO 格式
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _parse_amount(value: str) -> Optional[float]:
    """尝试解析金额数字。"""
    value = value.strip().replace(",", "").replace("¥", "").replace("$", "")
    try:
        return float(value)
    except ValueError:
        return None


def structure_data(raw_data: List[Dict[str, str]]) -> DataSet:
    """
    将原始字典列表结构化，识别字段类型并计算置信度。
    """
    if not raw_data:
        raise ValueError("E002: 无数据可结构化")

    if len(raw_data) > MAX_DATA_ROWS:
        raise ValueError(f"E003: 数据行数 {len(raw_data)} 超过上限 {MAX_DATA_ROWS}")

    # 收集所有字段名
    field_names = list(OrderedDict.fromkeys(k for row in raw_data for k in row.keys()))
    if not field_names:
        raise ValueError("E002: 数据无字段")

    # 推断字段类型
    field_types = {name: _detect_field_type(name) for name in field_names}

    records = []
    for row in raw_data:
        fields = {}
        confidence = {}

        for name in field_names:
            value = row.get(name, "")
            ftype = field_types[name]
            conf = CONFIDENCE_HIGH

            if not value or value == "":
                conf = CONFIDENCE_LOW
                fields[name] = ""
                confidence[name] = conf
                continue

            if ftype == "date":
                parsed = _parse_date(value)
                if parsed:
                    fields[name] = parsed.strftime("%Y-%m-%d")
                    conf = CONFIDENCE_HIGH
                else:
                    fields[name] = value
                    conf = CONFIDENCE_LOW
            elif ftype == "amount":
                parsed = _parse_amount(value)
                if parsed is not None:
                    fields[name] = str(parsed)
                    conf = CONFIDENCE_HIGH
                else:
                    fields[name] = value
                    conf = CONFIDENCE_LOW
            else:
                fields[name] = value
                # 对于文本字段，检查是否包含异常字符
                if len(value) > 0 and not value.isprintable():
                    conf = CONFIDENCE_LOW

            confidence[name] = conf

        records.append(DataRecord(fields, confidence))

    return DataSet(records, field_names)


# ---------------------------------------------------------------------------
# 可视化图表数据生成（C3）
# ---------------------------------------------------------------------------

def generate_chart_data(dataset: DataSet, chart_type: str = "柱状图") -> Dict[str, Any]:
    """
    根据数据集和图表类型生成图表所需数据。
    返回结构包含图表类型、标签、数值等信息。
    """
    if chart_type not in SUPPORTED_CHART_TYPES:
        raise ValueError(f"E005: 不支持的图表类型: {chart_type}")

    if len(dataset) == 0:
        raise ValueError("E002: 数据集为空，无法生成图表")

    # 选择分类字段和数值字段
    category_field = None
    value_field = None

    # 优先使用状态/项目作为分类，金额作为数值
    for name in dataset.field_names:
        if name in ("项目", "类别", "分类", "category", "type"):
            category_field = name
            break
    if not category_field:
        for name in dataset.field_names:
            if name in ("状态", "status"):
                category_field = name
                break
    if not category_field:
        category_field = dataset.field_names[0]

    for name in dataset.field_names:
        if name in ("金额", "价格", "费用", "amount", "price", "cost"):
            value_field = name
            break
    if not value_field:
        # 尝试找数值型字段
        for name in dataset.field_names:
            if name != category_field:
                value_field = name
                break
    if not value_field:
        value_field = dataset.field_names[0]

    # 聚合数据
    aggregated: Dict[str, float] = {}
    for record in dataset.records:
        cat_value = str(record.fields.get(category_field, "未知"))
        raw_val = record.fields.get(value_field, "0")
        try:
            num_val = float(raw_val)
        except (ValueError, TypeError):
            num_val = 0.0
        aggregated[cat_value] = aggregated.get(cat_value, 0.0) + num_val

    labels = list(aggregated.keys())
    values = list(aggregated.values())

    chart_data: Dict[str, Any] = {
        "图表类型": chart_type,
        "分类字段": category_field,
        "数值字段": value_field,
        "标签": labels,
        "数值": values,
        "数据点数量": len(labels),
    }

    if chart_type == "饼图":
        total = sum(values)
        chart_data["占比"] = [v / total if total > 0 else 0 for v in values]
    elif chart_type == "折线图":
        # 按日期排序（如果分类字段是日期类型）
        if _detect_field_type(category_field) == "date":
            try:
                pairs = sorted(zip(labels, values), key=lambda x: _parse_date(x[0]) or datetime.min)
                chart_data["标签"] = [p[0] for p in pairs]
                chart_data["数值"] = [p[1] for p in pairs]
            except Exception as e:
                print(f"[WARN] 降级处理: {e}", file=sys.stderr)  # R2 降级输出  # 排序失败则保持原顺序

    return chart_data


# ---------------------------------------------------------------------------
# 置信度标注（C4）
# ---------------------------------------------------------------------------

def annotate_confidence(dataset: DataSet) -> List[Dict[str, Any]]:
    """
    为数据集添加置信度标注，返回带标注的记录列表。
    """
    result = []
    for record in dataset.records:
        annotated = record.to_dict()
        annotated["_置信度"] = dict(record.confidence)
        result.append(annotated)
    return result


def compute_overall_confidence(dataset: DataSet) -> Dict[str, float]:
    """
    计算整体置信度指标。
    返回：字段名 -> 高置信度比例 (0~1)
    """
    if not dataset.records:
        raise ValueError("E007: 无记录可计算置信度")

    result = {}
    for name in dataset.field_names:
        high_count = sum(1 for r in dataset.records if r.confidence.get(name) == CONFIDENCE_HIGH)
        result[name] = high_count / len(dataset.records)
    return result


# ---------------------------------------------------------------------------
# 批量处理与模板（C5）
# ---------------------------------------------------------------------------

def apply_template(dataset: DataSet, template: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    根据模板配置输出数据。
    模板支持：
    - 字段顺序
    - 分组方式（无/按某字段分组）
    - 图表偏好
    """
    field_order = template.get("字段顺序", dataset.field_names)
    group_by = template.get("分组方式", "无")
    chart_pref = template.get("图表偏好", "柱状图")

    if chart_pref not in SUPPORTED_CHART_TYPES:
        raise ValueError(f"E006: 模板中不支持的图表偏好: {chart_pref}")

    # 校验字段顺序
    valid_fields = set(dataset.field_names)
    for f in field_order:
        if f not in valid_fields:
            raise ValueError(f"E006: 模板字段不存在: {f}")

    # 生成输出
    output = []
    if group_by == "无":
        for record in dataset.records:
            row = OrderedDict()
            for f in field_order:
                row[f] = record.fields.get(f, "")
            output.append(row)
    else:
        # 按指定字段分组
        if group_by not in valid_fields:
            raise ValueError(f"E006: 分组字段不存在: {group_by}")

        groups: Dict[str, List[DataRecord]] = {}
        for record in dataset.records:
            key = str(record.fields.get(group_by, "未分组"))
            groups.setdefault(key, []).append(record)

        for group_key, records in groups.items():
            group_output = {
                "分组字段": group_by,
                "分组值": group_key,
                "记录数": len(records),
                "数据": []
            }
            for record in records:
                row = OrderedDict()
                for f in field_order:
                    row[f] = record.fields.get(f, "")
                group_output["数据"].append(row)
            output.append(group_output)

    return output


def batch_process(datasets: List[DataSet], template: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    批量处理多个数据集。
    """
    if not datasets:
        raise ValueError("E008: 无数据集可处理")

    results = []
    for idx, ds in enumerate(datasets):
        try:
            processed = apply_template(ds, template)
            chart = generate_chart_data(ds, template.get("图表偏好", "柱状图"))
            confidence = compute_overall_confidence(ds)
            results.append({
                "数据集编号": idx + 1,
                "记录数": len(ds),
                "处理结果": processed,
                "图表数据": chart,
                "置信度指标": confidence,
            })
        except ValueError as exc:
            raise ValueError(f"E008: 数据集 {idx + 1} 处理失败: {exc}") from exc
    return results


# ---------------------------------------------------------------------------
# 主入口与命令行处理
# ---------------------------------------------------------------------------

def _run_selftest() -> int:
    """
    离线自检核心逻辑。
    使用内置硬编码样例数据，不依赖外部文件或网络。
    """
    # 硬编码样例数据（CSV 文本）
    sample_csv = """日期,项目,金额,状态
2024-01-05,产品A,1200.50,已完成
2024-01-12,产品B,800.00,进行中
2024-01-19,产品A,950.00,已完成
2024-01-26,产品C,1500.00,待审核
"""

    # 硬编码样例数据（JSON）
    sample_json = json.dumps([
        {"日期": "2024-02-01", "项目": "服务X", "金额": 2000, "状态": "已完成"},
        {"日期": "2024-02-15", "项目": "服务Y", "金额": 1200.5, "状态": "进行中"},
    ])

    # 硬编码模板
    sample_template = {
        "字段顺序": ["日期", "项目", "金额", "状态"],
        "分组方式": "无",
        "图表偏好": "柱状图",
    }

    try:
        # 测试1: 文本解析
        raw_csv = load_data_from_text(sample_csv)
        assert len(raw_csv) == 4, "CSV 解析行数错误"
        assert all(len(row) == 4 for row in raw_csv), "CSV 列数错误"

        # 测试2: JSON 解析
        raw_json = load_data_from_json(sample_json)
        assert len(raw_json) == 2, "JSON 解析行数错误"

        # 测试3: 结构化处理
        ds = structure_data(raw_csv)
        assert len(ds) == 4, "结构化后记录数错误"
        assert len(ds.field_names) == 4, "字段数错误"

        # 测试4: 字段类型识别
        assert "date" == _detect_field_type("日期"), "日期字段识别失败"
        assert "amount" == _detect_field_type("金额"), "金额字段识别失败"
        assert "category" == _detect_field_type("项目"), "分类字段识别失败"
        assert "status" == _detect_field_type("状态"), "状态字段识别失败"

        # 测试5: 日期解析
        parsed_date = _parse_date("2024-01-05")
        assert parsed_date is not None, "日期解析失败"
        assert parsed_date.year == 2024, "日期年份错误"

        # 测试6: 金额解析
        parsed_amount = _parse_amount("1,200.50")
        assert parsed_amount is not None, "金额解析失败"
        assert parsed_amount > 1000, "金额解析值错误"

        # 测试7: 图表数据生成
        chart_data = generate_chart_data(ds, "柱状图")
        assert chart_data["数据点数量"] > 0, "图表数据点为空"
        assert len(chart_data["标签"]) == len(chart_data["数值"]), "图表标签与数值数量不匹配"
        total_value = sum(chart_data["数值"])
        assert total_value > 0, "图表数值总和非正"

        # 测试8: 饼图占比
        pie_data = generate_chart_data(ds, "饼图")
        assert "占比" in pie_data, "饼图缺少占比数据"
        pie_total = sum(pie_data["占比"])
        assert abs(pie_total - 1.0) < 0.01, "饼图占比总和不为1"

        # 测试9: 置信度标注
        annotated = annotate_confidence(ds)
        assert len(annotated) == 4, "置信度标注记录数错误"
        assert all("_置信度" in row for row in annotated), "置信度标注缺失"

        # 测试10: 整体置信度
        conf_metrics = compute_overall_confidence(ds)
        assert len(conf_metrics) == 4, "置信度指标字段数错误"
        for field, ratio in conf_metrics.items():
            assert 0 <= ratio <= 1, "置信度比例超出范围"

        # 测试11: 模板应用
        processed = apply_template(ds, sample_template)
        assert len(processed) == 4, "模板应用记录数错误"
        assert all(list(row.keys()) == ["日期", "项目", "金额", "状态"] for row in processed), "模板字段顺序错误"

        # 测试12: 批量处理
        ds2 = structure_data(raw_json)
        batch_result = batch_process([ds, ds2], sample_template)
        assert len(batch_result) == 2, "批量处理结果数错误"
        assert batch_result[0]["记录数"] == 4, "批量处理记录数错误"
        assert batch_result[1]["记录数"] == 2, "批量处理记录数错误"

        # 测试13: 分组模板
        group_template = dict(sample_template)
        group_template["分组方式"] = "项目"
        grouped = apply_template(ds, group_template)
        assert len(grouped) >= 2, "分组结果数错误"
        assert all("分组值" in g for g in grouped), "分组结果缺少分组值"

        # 测试14: 错误处理
        try:
            load_data_from_text("")
            assert False, "空文本应抛出异常"
        except ValueError:
            pass

        try:
            generate_chart_data(ds, "不支持的图表")
            assert False, "不支持的图表类型应抛出异常"
        except ValueError:
            pass

        # 测试15: 数据行数上限
        too_many_rows = [{"a": str(i)} for i in range(MAX_DATA_ROWS + 1)]
        try:
            structure_data(too_many_rows)
            assert False, "超出行数上限应抛出异常"
        except ValueError:
            pass

        # 测试16: 桑基图支持
        sankey_data = generate_chart_data(ds, "桑基图")
        assert sankey_data["图表类型"] == "桑基图", "桑基图类型错误"
        assert sankey_data["数据点数量"] > 0, "桑基图数据点为空"

        # 测试17: 折线图排序
        line_data = generate_chart_data(ds, "折线图")
        assert line_data["图表类型"] == "折线图", "折线图类型错误"
        assert len(line_data["标签"]) == len(line_data["数值"]), "折线图标签与数值数量不匹配"

        # 测试18: 异常提示生成
        anomaly_notes = _generate_anomaly_notes(ds)
        assert isinstance(anomaly_notes, list), "异常提示应为列表"

        # 测试19: 空数据集异常
        empty_ds = DataSet([], [])
        try:
            generate_chart_data(empty_ds, "柱状图")
            assert False, "空数据集应抛出异常"
        except ValueError:
            pass

        # 测试20: 模板字段校验
        bad_template = dict(sample_template)
        bad_template["字段顺序"] = ["不存在的字段"]
        try:
            apply_template(ds, bad_template)
            assert False, "模板字段不存在应抛出异常"
        except ValueError:
            pass

        print("[SELFTEST] 全部 20 项核心逻辑检查通过")
        return 0

    except AssertionError as exc:
        print(f"[SELFTEST] 断言失败: {exc}", file=sys.stderr)
        return 1
    except ValueError as exc:
        print(f"[SELFTEST] 值错误: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"[SELFTEST] 未预期异常: {exc}", file=sys.stderr)
        return 1


def _build_parser() -> argparse.ArgumentParser:
    """构建命令行参数解析器。"""
    parser = argparse.ArgumentParser(
        prog="evidence",
        description="数据报表 证据链 可视化呈现 — 数据处理核心工具",
        epilog="示例: python main.py --input data.csv --chart 柱状图 --template template.json"
    )
    parser.add_argument(
        "--input", "-i",
        help="输入数据文件路径（CSV/TSV/JSON）"
    )
    parser.add_argument(
        "--text",
        help="直接传入文本数据（CSV/TSV/键值对格式）"
    )
    parser.add_argument(
        "--chart", "-c",
        choices=sorted(SUPPORTED_CHART_TYPES),
        default="柱状图",
        help="图表类型"
    )
    parser.add_argument(
        "--template", "-t",
        help="模板 JSON 文件路径"
    )
    parser.add_argument(
        "--group-by",
        help="分组字段名（覆盖模板设置）"
    )
    parser.add_argument(
        "--output", "-o",
        help="输出结果到文件（JSON 格式）"
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行离线自检"
    )
    return parser


def _load_template(template_path: Optional[str]) -> Dict[str, Any]:
    """加载模板配置。"""
    if not template_path:
        return dict(DEFAULT_TEMPLATE)

    try:
        with open(template_path, "r", encoding="utf-8") as fh:
            template = json.load(fh)
    except (IOError, OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"E006: 模板加载失败: {exc}") from exc

    if not isinstance(template, dict):
        raise ValueError("E006: 模板必须是 JSON 对象")

    # 合并默认值
    merged = dict(DEFAULT_TEMPLATE)
    merged.update(template)
    return merged


def _output_json(data: Any, output_path: Optional[str]) -> None:
    """输出 JSON 结果。"""
    json_str = json.dumps(data, ensure_ascii=False, indent=2, default=str)

    if output_path:
        try:
            with open(output_path, "w", encoding="utf-8") as fh:
                fh.write(json_str)
            print(f"结果已保存至: {output_path}")
        except (IOError, OSError) as exc:
            raise ValueError(f"E010: 输出文件写入失败: {exc}") from exc
    else:
        print(json_str)


def main(argv: Optional[List[str]] = None) -> int:
    """主函数入口。"""
    parser = _build_parser()

    try:
        parser.add_argument("--force", action="store_true")  # R4 强制写盘

        parser.add_argument("--dry-run", action="store_true")  # R4 预览模式
        args = parser.parse_args(argv)
        global dry_run
        dry_run = getattr(args, "dry_run", False)  # v3.274 同步到全局
    except SystemExit as exc:
        # 参数错误
        return int(exc.code) if exc.code else 1
    except Exception as exc:
        print(f"E001: 参数解析失败: {exc}", file=sys.stderr)
        return 1

    # 自检模式
    if args.selftest:
        return _run_selftest()

    # 检查输入来源
    if not args.input and not args.text:
        print("E002: 必须提供 --input 或 --text 参数", file=sys.stderr)
        return 1

    try:
        # 1. 数据接入
        if args.input:
            raw_data = load_data_from_file(args.input)
        else:
            raw_data = load_data_from_text(args.text)

        # 2. 数据结构化
        dataset = structure_data(raw_data)

        # 3. 加载模板
        template = _load_template(args.template)

        # 4. 覆盖分组设置
        if args.group_by:
            template["分组方式"] = args.group_by

        # 5. 覆盖图表偏好
        template["图表偏好"] = args.chart

        # 6. 处理数据
        processed = apply_template(dataset, template)
        chart_data = generate_chart_data(dataset, args.chart)
        confidence = compute_overall_confidence(dataset)
        annotated = annotate_confidence(dataset)

        # 7. 组装结果
        result = {
            "元信息": {
                "工具": "evidence",
                "版本": "1.0.1",
                "处理时间": datetime.now(timezone.utc).isoformat(),
                "记录数": len(dataset),
                "字段数": len(dataset.field_names),
            },
            "处理结果": processed,
            "图表数据": chart_data,
            "置信度标注": annotated,
            "置信度指标": confidence,
            "异常提示": _generate_anomaly_notes(dataset),
        }

        # 8. 输出
        _output_json(result, args.output)
        return 0

    except ValueError as exc:
        print(f"错误: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"E010: 内部异常: {exc}", file=sys.stderr)
        return 1


def _generate_anomaly_notes(dataset: DataSet) -> List[str]:
    """
    生成数据异常提示（R3 要求）。
    检测：缺失值、格式不一致、异常数值等。
    """
    notes = []
    if not dataset.records:
        notes.append("数据集为空")
        return notes

    # 检查缺失值
    for name in dataset.field_names:
        missing_count = sum(1 for r in dataset.records if not r.fields.get(name, ""))
        if missing_count > 0:
            notes.append(f"字段 '{name}' 存在 {missing_count} 条缺失记录")

    # 检查数值异常（金额字段）
    for name in dataset.field_names:
        if _detect_field_type(name) == "amount":
            values = []
            for r in dataset.records:
                try:
                    values.append(float(r.fields.get(name, "0")))
                except (ValueError, TypeError):
                    continue
            if values:
                avg = sum(values) / len(values)
                for idx, v in enumerate(values):
                    if avg > 0 and abs(v - avg) / avg > 10:
                        notes.append(f"第 {idx + 1} 条记录字段 '{name}' 数值异常（偏离均值过大）")
                        break

    return notes


if __name__ == "__main__":
    sys.exit(main())
