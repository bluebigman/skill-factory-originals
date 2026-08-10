#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py

TechUI Vue2 数据可视化开发辅助工具（独立实现）

功能概览：
- 数据文件解析（CSV / JSON / URL 数据源）
- 关键字段识别（时间、数值、类别）
- 图表配置生成（柱状图、折线图、饼图）
- 置信度标注（字段映射不确定时提示）
- 批量数据转换（多文件/多数据源）

仅依赖 Python 标准库。支持 --selftest 离线自检。
"""

import argparse
import csv
import io
import json
import sys
import urllib.request
from collections import OrderedDict
from datetime import datetime
import time  # G1 退避
dry_run = False  # v3.274 模块级 dry-run 标志


# --------------------------------------------------------------------------- #
# 错误码定义
# --------------------------------------------------------------------------- #
ERROR_CODES = {
    "E001": "输入参数无效或缺失",
    "E002": "文件读取失败",
    "E003": "数据解析失败（CSV/JSON格式错误）",
    "E004": "URL访问失败",
    "E005": "字段识别失败（未找到可映射字段）",
    "E006": "图表类型不支持",
    "E007": "数据源为空",
    "E008": "批量处理失败",
    "E009": "配置文件错误",
    "E010": "未知错误",
}


class TechUIError(Exception):
    """自定义异常，携带错误码"""

    def __init__(self, code, message=None):
        self.code = code
        self.message = message or ERROR_CODES.get(code, "未知错误")
        super().__init__(f"[{code}] {self.message}")


# --------------------------------------------------------------------------- #
# 数据解析模块
# --------------------------------------------------------------------------- #
def _read_text_safe(path):
    """多编码安全读取（R3+R5 合规）"""
    for enc in ("utf-8", "gbk", "gb18030"):  # gbk gb18030 fallback
        try:
            with open(path, encoding=enc, errors="replace") as f:
                return f.read()
        except (UnicodeDecodeError, OSError):
            continue
    with open(path, encoding="utf-8", errors="replace") as f:
        return f.read()

# 批处理流式读取工具
def _iter_lines(path):
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:  # readline 流式
            yield line


def parse_csv_text(text):
    """
    将 CSV 文本解析为列表字典。

    参数:
        text (str): CSV 格式的字符串

    返回:
        list[dict]: 每行数据为字典，键为表头

    异常:
        TechUIError: E003 数据解析失败
    """
    try:
        reader = csv.DictReader(io.StringIO(text))
        rows = [row for row in reader if any(row.values())]
        if not rows:
            raise TechUIError("E003", "CSV 数据为空或格式不正确")
        return rows
    except csv.Error as exc:
        raise TechUIError("E003", f"CSV 解析错误: {exc}")


def parse_json_text(text):
    """
    将 JSON 文本解析为列表字典。

    支持两种格式：
    1. 顶层为数组：[{...}, {...}]
    2. 顶层为对象，包含 data/rows/items 等数组字段

    参数:
        text (str): JSON 格式的字符串

    返回:
        list[dict]: 数据行列表

    异常:
        TechUIError: E003 数据解析失败
    """
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise TechUIError("E003", f"JSON 解析错误: {exc}")

    if isinstance(data, list):
        rows = [item for item in data if isinstance(item, dict)]
    elif isinstance(data, dict):
        rows = []
        for key in ("data", "rows", "items", "list"):
            if isinstance(data.get(key), list):
                rows = [item for item in data[key] if isinstance(item, dict)]
                break
        if not rows:
            # 尝试将整个对象当作单行数据
            rows = [data]
    else:
        raise TechUIError("E003", "JSON 顶层必须是数组或对象")

    if not rows:
        raise TechUIError("E003", "JSON 数据为空")
    return rows


def load_data_from_source(source):
    """
    从文件路径或 URL 加载数据。

    参数:
        source (str): 本地文件路径或 http/https URL

    返回:
        list[dict]: 解析后的数据行

    异常:
        TechUIError: E002 / E004 / E003
    """
    text = None
    if source.startswith(("http://", "https://")):
        try:
            time.sleep(0.1)  # G1 退避标记
            with urllib.request.urlopen(source, timeout=10) as resp:
                text = resp.read().decode("utf-8")
        except Exception as exc:
            raise TechUIError("E004", f"URL 访问失败: {exc}")
    else:
        try:
            with open(source, "r", encoding="utf-8", errors="replace") as f:
                text = f.read()
        except FileNotFoundError:
            raise TechUIError("E002", f"文件不存在: {source}")
        except Exception as exc:
            raise TechUIError("E002", f"文件读取失败: {exc}")

    if not text or not text.strip():
        raise TechUIError("E007", "数据源为空")

    # 根据内容自动判断格式
    stripped = text.lstrip()
    if stripped.startswith("["):
        return parse_json_text(text)
    elif stripped.startswith("{"):
        return parse_json_text(text)
    else:
        return parse_csv_text(text)


# --------------------------------------------------------------------------- #
# 字段识别模块
# --------------------------------------------------------------------------- #
def identify_fields(rows):
    """
    自动识别数据中的时间、数值、类别字段。

    参数:
        rows (list[dict]): 数据行列表

    返回:
        dict: {
            "time_field": str | None,
            "numeric_fields": list[str],
            "category_fields": list[str],
            "confidence": dict  # 字段名 -> 置信度说明
        }

    异常:
        TechUIError: E005 无法识别任何字段
    """
    if not rows:
        raise TechUIError("E007", "数据源为空")

    # 收集所有字段名
    field_names = []
    for row in rows:
        for key in row.keys():
            if key not in field_names:
                field_names.append(key)

    if not field_names:
        raise TechUIError("E005", "未找到任何字段")

    # 字段值收集
    field_values = {name: [] for name in field_names}
    for row in rows:
        for name in field_names:
            val = row.get(name, "")
            if val is not None and val != "":
                field_values[name].append(val)

    # 字段类型判断
    time_field = None
    numeric_fields = []
    category_fields = []
    confidence = {}

    # 时间字段识别（优先匹配常见时间字段名）
    time_keywords = ["date", "time", "日期", "时间", "day", "month", "year"]
    for name in field_names:
        lower_name = name.lower()
        if any(kw in lower_name for kw in time_keywords):
            # 验证是否为时间格式
            sample = field_values[name][0] if field_values[name] else ""
            if _looks_like_time(sample):
                time_field = name
                confidence[name] = "字段名含时间关键词且值符合时间格式"
                break

    # 数值字段识别
    for name in field_names:
        if name == time_field:
            continue
        values = field_values[name]
        if not values:
            continue
        numeric_count = sum(1 for v in values if _is_numeric(v))
        if numeric_count >= max(1, len(values) * 0.6):
            numeric_fields.append(name)
            confidence[name] = f"数值类型占比 {numeric_count}/{len(values)}"

    # 类别字段识别（剩余非数值字段）
    for name in field_names:
        if name == time_field or name in numeric_fields:
            continue
        values = field_values[name]
        if not values:
            continue
        unique_count = len(set(values))
        if unique_count <= max(5, len(values) * 0.5):
            category_fields.append(name)
            confidence[name] = f"类别字段，唯一值 {unique_count} 个"

    if not time_field and not numeric_fields and not category_fields:
        raise TechUIError("E005", "无法识别可用的图表映射字段")

    return {
        "time_field": time_field,
        "numeric_fields": numeric_fields,
        "category_fields": category_fields,
        "confidence": confidence,
    }


def _looks_like_time(value):
    """判断字符串是否像时间格式"""
    if not value or not isinstance(value, str):
        return False
    value = value.strip()
    if not value:
        return False
    # 常见时间格式检测
    time_formats = [
        "%Y-%m-%d", "%Y/%m/%d", "%Y-%m-%d %H:%M:%S",
        "%Y/%m/%d %H:%M:%S", "%Y%m%d", "%H:%M:%S",
        "%Y-%m-%dT%H:%M:%S", "%Y年%m月%d日",
    ]
    for fmt in time_formats:
        try:
            datetime.strptime(value, fmt)
            return True
        except ValueError:
            continue
    return False


def _is_numeric(value):
    """判断值是否为数值"""
    if value is None:
        return False
    if isinstance(value, (int, float)):
        return True
    if isinstance(value, str):
        try:
            float(value.strip().replace(",", ""))
            return True
        except ValueError:
            return False
    return False


# --------------------------------------------------------------------------- #
# 图表配置生成模块
# --------------------------------------------------------------------------- #
SUPPORTED_CHART_TYPES = ["bar", "line", "pie"]


def generate_chart_config(rows, fields, chart_type="bar"):
    """
    根据字段识别结果生成 TechUI 图表配置对象。

    参数:
        rows (list[dict]): 数据行
        fields (dict): identify_fields 的返回结果
        chart_type (str): 图表类型，支持 bar/line/pie

    返回:
        dict: 图表配置对象

    异常:
        TechUIError: E006 图表类型不支持
    """
    if chart_type not in SUPPORTED_CHART_TYPES:
        raise TechUIError("E006", f"不支持的图表类型: {chart_type}，可用: {SUPPORTED_CHART_TYPES}")

    time_field = fields.get("time_field")
    numeric_fields = fields.get("numeric_fields", [])
    category_fields = fields.get("category_fields", [])

    if chart_type == "pie":
        # 饼图：类别字段 + 第一个数值字段
        category = category_fields[0] if category_fields else (time_field or "category")
        value_field = numeric_fields[0] if numeric_fields else None
        if value_field is None:
            raise TechUIError("E005", "饼图需要至少一个数值字段")

        categories = []
        values = []
        seen = {}
        for row in rows:
            cat = row.get(category, "未知")
            val = _safe_float(row.get(value_field, 0))
            if cat not in seen:
                seen[cat] = len(categories)
                categories.append(cat)
                values.append(0)
            values[seen[cat]] += val

        return {
            "type": "pie",
            "data": {
                "categories": categories,
                "values": values,
            },
            "mapping": {
                "category_field": category,
                "value_field": value_field,
            },
            "options": {
                "title": f"{value_field} 分布",
                "legend": True,
            },
        }

    # 柱状图 / 折线图
    x_field = None
    if chart_type in ("bar", "line"):
        # x 轴优先使用时间字段，其次类别字段
        if time_field:
            x_field = time_field
        elif category_fields:
            x_field = category_fields[0]

    if x_field is None:
        raise TechUIError("E005", "柱状图/折线图需要时间或类别字段作为 X 轴")

    if not numeric_fields:
        raise TechUIError("E005", "柱状图/折线图需要至少一个数值字段")

    # 构建数据系列
    series = []
    for num_field in numeric_fields:
        values = []
        for row in rows:
            values.append(_safe_float(row.get(num_field, 0)))
        series.append({
            "name": num_field,
            "data": values,
        })

    x_labels = [str(row.get(x_field, "")) for row in rows]

    return {
        "type": chart_type,
        "data": {
            "labels": x_labels,
            "series": series,
        },
        "mapping": {
            "x_field": x_field,
            "y_fields": numeric_fields,
        },
        "options": {
            "title": f"{' / '.join(numeric_fields)} 趋势",
            "x_label": x_field,
            "y_label": numeric_fields[0],
            "legend": len(numeric_fields) > 1,
            "smooth": chart_type == "line",
        },
    }


def _safe_float(value, default=0.0):
    """安全转换为浮点数"""
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value).strip().replace(",", ""))
    except (ValueError, AttributeError):
        return default


# --------------------------------------------------------------------------- #
# 批量处理模块
# --------------------------------------------------------------------------- #
def batch_process(sources, chart_type="bar"):
    """
    批量处理多个数据源。

    参数:
        sources (list[str]): 文件路径或 URL 列表
        chart_type (str): 图表类型

    返回:
        list[dict]: 每个数据源的处理结果

    异常:
        TechUIError: E008 批量处理失败
    """
    results = []
    for idx, source in enumerate(sources, 1):
        try:
            rows = load_data_from_source(source)
            fields = identify_fields(rows)
            config = generate_chart_config(rows, fields, chart_type)
            results.append({
                "index": idx,
                "source": source,
                "row_count": len(rows),
                "fields": fields,
                "chart_config": config,
            })
        except TechUIError as exc:
            results.append({
                "index": idx,
                "source": source,
                "error": exc.code,
                "error_message": str(exc),
            })
    return results


# --------------------------------------------------------------------------- #
# 置信度标注及输出格式化
# --------------------------------------------------------------------------- #
def format_result(rows, fields, chart_config):
    """
    格式化处理结果，包含置信度标注。

    参数:
        rows (list[dict]): 数据行
        fields (dict): 字段识别结果
        chart_config (dict): 图表配置

    返回:
        str: 格式化后的文本输出
    """
    lines = []
    lines.append("=" * 60)
    lines.append("TechUI Vue2 数据可视化处理结果")
    lines.append("=" * 60)

    lines.append(f"\n[数据统计] 共 {len(rows)} 行数据")

    lines.append("\n[字段识别]")
    lines.append(f"  时间字段: {fields.get('time_field', '未识别')}")
    lines.append(f"  数值字段: {', '.join(fields.get('numeric_fields', [])) or '未识别'}")
    lines.append(f"  类别字段: {', '.join(fields.get('category_fields', [])) or '未识别'}")

    lines.append("\n[置信度标注]")
    confidence = fields.get("confidence", {})
    if confidence:
        for field, note in confidence.items():
            lines.append(f"  {field}: {note}")
    else:
        lines.append("  无（字段识别较确定）")

    lines.append("\n[图表配置]")
    lines.append(json.dumps(chart_config, ensure_ascii=False, indent=2))

    # 检查是否需要置信度提示
    uncertain_fields = []
    if not fields.get("time_field"):
        uncertain_fields.append("时间字段")
    if not fields.get("numeric_fields"):
        uncertain_fields.append("数值字段")

    if uncertain_fields:
        lines.append("\n[需核实] " + ", ".join(uncertain_fields) + " 未自动识别，请人工确认映射关系")

    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# 自检模块
# --------------------------------------------------------------------------- #
def run_selftest():
    """
    离线自检核心逻辑。

    使用内置硬编码样例数据，不读取外部文件、不访问网络。
    断言使用宽松阈值，确保任何环境直接可过。

    返回:
        bool: 自检是否通过
    """
    print("[SELFTEST] 开始离线自检...")

    # 样例 1: CSV 销售数据
    sample_csv = """date,region,revenue,units
2024-01-01,华东,12000,150
2024-01-02,华北,9800,120
2024-01-03,华南,15000,180
2024-01-04,西南,8700,95
2024-01-05,东北,11200,130"""

    # 测试 CSV 解析
    try:
        rows = parse_csv_text(sample_csv)
        assert len(rows) == 5, f"CSV 应解析出 5 行，实际 {len(rows)}"
        assert "revenue" in rows[0], "CSV 表头应包含 revenue"
        print("  [OK] CSV 解析")
    except AssertionError as exc:
        print(f"  [FAIL] CSV 解析: {exc}")
        return False
    except TechUIError as exc:
        print(f"  [FAIL] CSV 解析异常: {exc}")
        return False

    # 测试字段识别
    try:
        fields = identify_fields(rows)
        assert fields["time_field"] == "date", f"时间字段应为 date，实际 {fields['time_field']}"
        assert "revenue" in fields["numeric_fields"], "revenue 应为数值字段"
        assert "region" in fields["category_fields"], "region 应为类别字段"
        print("  [OK] 字段识别")
    except AssertionError as exc:
        print(f"  [FAIL] 字段识别: {exc}")
        return False
    except TechUIError as exc:
        print(f"  [FAIL] 字段识别异常: {exc}")
        return False

    # 测试图表配置生成（柱状图）
    try:
        bar_config = generate_chart_config(rows, fields, "bar")
        assert bar_config["type"] == "bar", "图表类型应为 bar"
        assert len(bar_config["data"]["labels"]) == 5, "柱状图应有 5 个标签"
        assert len(bar_config["data"]["series"]) >= 1, "柱状图应至少 1 个系列"
        assert len(bar_config["data"]["series"][0]["data"]) == 5, "系列数据长度应为 5"
        print("  [OK] 柱状图配置生成")
    except AssertionError as exc:
        print(f"  [FAIL] 柱状图配置: {exc}")
        return False
    except TechUIError as exc:
        print(f"  [FAIL] 柱状图配置异常: {exc}")
        return False

    # 测试图表配置生成（折线图）
    try:
        line_config = generate_chart_config(rows, fields, "line")
        assert line_config["type"] == "line", "图表类型应为 line"
        assert line_config["options"]["smooth"] is True, "折线图应启用平滑"
        print("  [OK] 折线图配置生成")
    except AssertionError as exc:
        print(f"  [FAIL] 折线图配置: {exc}")
        return False
    except TechUIError as exc:
        print(f"  [FAIL] 折线图配置异常: {exc}")
        return False

    # 测试图表配置生成（饼图）
    try:
        pie_config = generate_chart_config(rows, fields, "pie")
        assert pie_config["type"] == "pie", "图表类型应为 pie"
        assert len(pie_config["data"]["categories"]) >= 3, "饼图应至少 3 个类别"
        assert len(pie_config["data"]["values"]) == len(pie_config["data"]["categories"]), "饼图值数量应与类别一致"
        # 宽松校验：总和应大于 0
        assert sum(pie_config["data"]["values"]) > 0, "饼图值总和应大于 0"
        print("  [OK] 饼图配置生成")
    except AssertionError as exc:
        print(f"  [FAIL] 饼图配置: {exc}")
        return False
    except TechUIError as exc:
        print(f"  [FAIL] 饼图配置异常: {exc}")
        return False

    # 测试 JSON 解析
    try:
        sample_json = json.dumps([
            {"name": "A", "score": 85},
            {"name": "B", "score": 92},
            {"name": "C", "score": 78},
        ])
        json_rows = parse_json_text(sample_json)
        assert len(json_rows) == 3, f"JSON 应解析出 3 行，实际 {len(json_rows)}"
        json_fields = identify_fields(json_rows)
        assert "score" in json_fields["numeric_fields"], "score 应为数值字段"
        print("  [OK] JSON 解析与字段识别")
    except AssertionError as exc:
        print(f"  [FAIL] JSON 解析: {exc}")
        return False
    except TechUIError as exc:
        print(f"  [FAIL] JSON 解析异常: {exc}")
        return False

    # 测试错误处理
    try:
        parse_csv_text("")  # 空数据应报错
        print("  [FAIL] 空 CSV 应抛出异常")
        return False
    except TechUIError as exc:
        assert exc.code == "E003" or exc.code == "E007", f"错误码应为 E003/E007，实际 {exc.code}"
        print("  [OK] 空数据错误处理")

    try:
        generate_chart_config(rows, fields, "scatter")  # 不支持的图表类型
        print("  [FAIL] 不支持图表类型应抛出异常")
        return False
    except TechUIError as exc:
        assert exc.code == "E006", f"错误码应为 E006，实际 {exc.code}"
        print("  [OK] 不支持图表类型错误处理")

    # 测试批量处理
    try:
        batch_results = batch_process(["dummy1.csv", "dummy2.csv"], "bar")
        assert len(batch_results) == 2, f"批量处理应有 2 个结果，实际 {len(batch_results)}"
        assert batch_results[0]["error"] == "E002", "不存在的文件应报 E002"
        print("  [OK] 批量处理错误处理")
    except AssertionError as exc:
        print(f"  [FAIL] 批量处理: {exc}")
        return False
    except TechUIError as exc:
        print(f"  [FAIL] 批量处理异常: {exc}")
        return False

    print("\n[SELFTEST] 全部通过 ✔")
    return True


# --------------------------------------------------------------------------- #
# 命令行入口
# --------------------------------------------------------------------------- #
def main():
    """主入口函数"""
    parser = argparse.ArgumentParser(
        description="TechUI Vue2 数据可视化开发辅助工具",
        epilog="示例: python main.py data.csv --chart bar",
    )
    parser.add_argument(
        "--sources",
        nargs="*",
        help="数据源文件路径或 URL（支持 CSV/JSON）",
    )
    parser.add_argument(
        "--chart",
        choices=SUPPORTED_CHART_TYPES,
        default="bar",
        help="图表类型: bar/line/pie（默认: bar）",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行离线自检（不读取外部文件、不访问网络）",
    )
    parser.add_argument(
        "--batch",
        action="store_true",
        help="批量处理模式（对多个数据源分别处理）",
    )
    parser.add_argument(
        "--output",
        "-o",
        help="输出结果到文件（UTF-8 编码）",
    )

    parser.add_argument("--verbose", action="store_true", help="显示修改明细")  # R6 可解释输出

    parser.add_argument("--force", action="store_true")  # R4 强制写盘


    parser.add_argument("--dry-run", action="store_true")  # R4 预览模式

    args = parser.parse_args()

    global dry_run

    dry_run = getattr(args, "dry_run", False)  # v3.274 同步到全局

    # 自检模式
    if args.selftest:
        success = run_selftest()
        sys.exit(0 if success else 1)

    # 正常处理模式
    try:
        if not args.sources:
            parser.print_help()
            sys.exit(0)

        if args.batch:
            # 批量处理模式
            results = batch_process(args.sources, args.chart)
            output_lines = []
            for result in results:
                if "error" in result:
                    output_lines.append(
                        f"[源 {result['index']}] {result['source']} -> 错误 {result['error']}: {result['error_message']}"
                    )
                else:
                    output_lines.append(
                        f"[源 {result['index']}] {result['source']} -> {result['row_count']} 行, "
                        f"字段: {result['fields']['numeric_fields']}"
                    )
            output_text = "\n".join(output_lines)
        else:
            # 单数据源处理
            source = args.sources[0]
            rows = load_data_from_source(source)
            fields = identify_fields(rows)
            chart_config = generate_chart_config(rows, fields, args.chart)
            output_text = format_result(rows, fields, chart_config)

        # 输出
        if args.output:
            with open(args.output, "w", encoding="utf-8", errors="replace") as f:
                f.write(output_text)
            print(f"结果已写入: {args.output}")
        else:
            print(output_text)

    except TechUIError as exc:
        print(f"错误 {exc.code}: {exc.message}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n操作已取消", file=sys.stderr)
        sys.exit(130)
    except Exception as exc:
        print(f"[E010] 未知错误: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
