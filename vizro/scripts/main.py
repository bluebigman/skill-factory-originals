#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
vizro 数据可视化低代码仪表盘工具 —— 独立实现

本脚本根据功能规格重新实现，不参考任何既有代码。
支持将数据文件（CSV/JSON）或 URL 转换为仪表盘配置，
并提供批量处理与置信度标注能力。
"""

import argparse
import csv
import io
import json
import os
import sys
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

# 错误码定义
ERROR_CODES = {
    "E001": "参数错误：缺少必要参数或参数格式不正确",
    "E002": "文件不存在或无法读取",
    "E003": "文件格式不支持（仅支持 CSV/JSON）",
    "E004": "数据解析失败（CSV/JSON 格式错误）",
    "E005": "URL 访问失败或返回无效数据",
    "E006": "数据为空或缺少必要列",
    "E007": "图表类型不支持",
    "E008": "批量处理中断（某个文件处理失败）",
    "E009": "输出目录不存在或无法写入",
    "E010": "内部逻辑错误（未知异常）",
}


class VizroError(Exception):
    """自定义异常，携带错误码"""

    def __init__(self, code: str, message: str = ""):
        self.code = code
        self.message = message or ERROR_CODES.get(code, "未知错误")
        super().__init__(f"[{code}] {self.message}")


# ---------- 数据结构 ----------

@dataclass
class ColumnInfo:
    """列信息"""
    name: str
    data_type: str  # 'numeric' | 'categorical' | 'datetime' | 'text'
    unique_count: int = 0
    missing_count: int = 0


@dataclass
class ChartSpec:
    """图表配置"""
    chart_type: str  # 'bar' | 'line' | 'scatter' | 'pie'
    x: str
    y: Optional[str] = None
    title: str = ""
    confidence: float = 0.0  # 置信度 0~1


@dataclass
class DashboardConfig:
    """仪表盘配置"""
    title: str = ""
    source: str = ""
    charts: List[ChartSpec] = field(default_factory=list)
    columns: List[ColumnInfo] = field(default_factory=list)
    row_count: int = 0
    generated_at: str = ""


# ---------- 数据加载 ----------

def load_data_from_file(filepath: str) -> List[Dict[str, Any]]:
    """
    从本地文件加载数据（CSV 或 JSON）
    返回字典列表（每行一个字典）
    """
    if not os.path.exists(filepath):
        raise VizroError("E002", f"文件不存在: {filepath}")

    ext = os.path.splitext(filepath)[1].lower()
    try:
        if ext == ".csv":
            with open(filepath, "r", encoding="utf-8-sig") as f:
                return _parse_csv(f.read())
        elif ext == ".json":
            with open(filepath, "r", encoding="utf-8-sig") as f:
                return _parse_json(f.read())
        else:
            raise VizroError("E003", f"不支持的文件格式: {ext}")
    except VizroError:
        raise
    except Exception as e:
        raise VizroError("E004", f"解析失败: {str(e)}")


def load_data_from_url(url: str) -> List[Dict[str, Any]]:
    """从 URL 加载数据（CSV 或 JSON）"""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            content = resp.read().decode("utf-8-sig")
    except Exception as e:
        raise VizroError("E005", f"URL 访问失败: {str(e)}")

    try:
        if url.endswith(".json") or content.lstrip().startswith("["):
            return _parse_json(content)
        else:
            return _parse_csv(content)
    except VizroError:
        raise
    except Exception as e:
        raise VizroError("E005", f"URL 数据解析失败: {str(e)}")


def _parse_csv(content: str) -> List[Dict[str, Any]]:
    """解析 CSV 文本为字典列表"""
    reader = csv.DictReader(io.StringIO(content))
    rows = list(reader)
    if not rows:
        raise VizroError("E006", "CSV 数据为空")
    # 尝试转换数值类型
    converted = []
    for row in rows:
        new_row = {}
        for key, val in row.items():
            if val is None:
                new_row[key] = None
            else:
                new_row[key] = _try_convert(val)
        converted.append(new_row)
    return converted


def _parse_json(content: str) -> List[Dict[str, Any]]:
    """解析 JSON 文本为字典列表"""
    try:
        data = json.loads(content)
    except json.JSONDecodeError as e:
        raise VizroError("E004", f"JSON 解析错误: {str(e)}")

    if isinstance(data, dict):
        # 可能是 {"data": [...]} 或 {"rows": [...]} 格式
        for key in ("data", "rows", "items"):
            if key in data and isinstance(data[key], list):
                data = data[key]
                break
        else:
            # 单行数据
            data = [data]

    if not isinstance(data, list) or not data:
        raise VizroError("E006", "JSON 数据为空或格式不正确")

    # 确保每项是字典
    result = []
    for item in data:
        if isinstance(item, dict):
            result.append(item)
        else:
            raise VizroError("E004", "JSON 数据项必须是对象")
    return result


def _try_convert(value: str) -> Any:
    """尝试将字符串转换为数值或布尔值"""
    if value == "":
        return None
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        pass
    if value.lower() in ("true", "false"):
        return value.lower() == "true"
    return value


# ---------- 数据分析 ----------

def analyze_columns(data: List[Dict[str, Any]]) -> List[ColumnInfo]:
    """分析数据列的类型和统计信息"""
    if not data:
        raise VizroError("E006", "数据为空")

    all_keys = set()
    for row in data:
        all_keys.update(row.keys())

    columns = []
    for key in all_keys:
        values = [row.get(key) for row in data]
        non_null = [v for v in values if v is not None]

        # 判断类型
        data_type = "text"
        if non_null:
            if all(isinstance(v, (int, float)) for v in non_null):
                data_type = "numeric"
            elif all(isinstance(v, bool) for v in non_null):
                data_type = "categorical"
            elif all(isinstance(v, str) for v in non_null):
                # 尝试日期判断
                if len(non_null) > 0 and _looks_like_datetime(non_null[0]):
                    data_type = "datetime"
                else:
                    data_type = "categorical" if len(set(non_null)) <= max(20, len(non_null) * 0.5) else "text"

        columns.append(ColumnInfo(
            name=key,
            data_type=data_type,
            unique_count=len(set(non_null)),
            missing_count=len(values) - len(non_null),
        ))
    return columns


def _looks_like_datetime(value: str) -> bool:
    """简单判断是否为日期格式"""
    import datetime
    try:
        datetime.datetime.fromisoformat(value.replace("Z", "+00:00"))
        return True
    except (ValueError, AttributeError):
        return False


# ---------- 图表生成 ----------

def generate_charts(data: List[Dict[str, Any]], columns: List[ColumnInfo], max_charts: int = 5) -> List[ChartSpec]:
    """
    根据数据自动生成图表配置
    返回图表列表，附带置信度评分
    """
    if not data or not columns:
        raise VizroError("E006", "无法生成图表：数据为空")

    numeric_cols = [c for c in columns if c.data_type == "numeric"]
    categorical_cols = [c for c in columns if c.data_type == "categorical"]
    datetime_cols = [c for c in columns if c.data_type == "datetime"]

    charts: List[ChartSpec] = []

    # 1. 柱状图：分类列 + 数值列（如果有）
    if categorical_cols and numeric_cols:
        cat = categorical_cols[0]
        num = numeric_cols[0]
        charts.append(ChartSpec(
            chart_type="bar",
            x=cat.name,
            y=num.name,
            title=f"{num.name} by {cat.name}",
            confidence=0.85,
        ))

    # 2. 折线图：时间列 + 数值列（如果有）
    if datetime_cols and numeric_cols:
        dt = datetime_cols[0]
        num = numeric_cols[0]
        charts.append(ChartSpec(
            chart_type="line",
            x=dt.name,
            y=num.name,
            title=f"{num.name} over time",
            confidence=0.80,
        ))

    # 3. 散点图：两个数值列（如果有）
    if len(numeric_cols) >= 2:
        charts.append(ChartSpec(
            chart_type="scatter",
            x=numeric_cols[0].name,
            y=numeric_cols[1].name,
            title=f"{numeric_cols[0].name} vs {numeric_cols[1].name}",
            confidence=0.75,
        ))

    # 4. 饼图：分类列（如果有）
    if categorical_cols and len(categorical_cols) >= 1:
        cat = categorical_cols[0]
        charts.append(ChartSpec(
            chart_type="pie",
            x=cat.name,
            title=f"Distribution of {cat.name}",
            confidence=0.70,
        ))

    # 5. 补充：如果只有数值列，生成数值分布图
    if not charts and numeric_cols:
        charts.append(ChartSpec(
            chart_type="bar",
            x=numeric_cols[0].name,
            title=f"Distribution of {numeric_cols[0].name}",
            confidence=0.60,
        ))

    # 限制数量
    return charts[:max_charts]


# ---------- 仪表盘构建 ----------

def build_dashboard(data: List[Dict[str, Any]], source: str = "", title: str = "") -> DashboardConfig:
    """构建完整的仪表盘配置"""
    if not data:
        raise VizroError("E006", "数据为空，无法构建仪表盘")

    columns = analyze_columns(data)
    charts = generate_charts(data, columns)

    if not charts:
        raise VizroError("E007", "无法为数据生成合适的图表")

    import datetime
    config = DashboardConfig(
        title=title or f"数据仪表盘 ({len(data)} 行)",
        source=source,
        charts=charts,
        columns=columns,
        row_count=len(data),
        generated_at=datetime.datetime.now().isoformat(),
    )
    return config


def config_to_dict(config: DashboardConfig) -> Dict[str, Any]:
    """将仪表盘配置转换为字典（便于 JSON 序列化）"""
    return {
        "title": config.title,
        "source": config.source,
        "row_count": config.row_count,
        "generated_at": config.generated_at,
        "columns": [
            {
                "name": c.name,
                "data_type": c.data_type,
                "unique_count": c.unique_count,
                "missing_count": c.missing_count,
            }
            for c in config.columns
        ],
        "charts": [
            {
                "chart_type": c.chart_type,
                "x": c.x,
                "y": c.y,
                "title": c.title,
                "confidence": round(c.confidence, 2),
            }
            for c in config.charts
        ],
    }


def save_config(config: DashboardConfig, output_path: str) -> None:
    """保存仪表盘配置到 JSON 文件"""
    output_dir = os.path.dirname(output_path)
    if output_dir and not os.path.exists(output_dir):
        raise VizroError("E009", f"输出目录不存在: {output_dir}")

    try:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(config_to_dict(config), f, ensure_ascii=False, indent=2)
    except VizroError:
        raise
    except Exception as e:
        raise VizroError("E009", f"写入失败: {str(e)}")


# ---------- 批量处理 ----------

def batch_process(inputs: List[str], output_dir: str = "output") -> List[Tuple[str, bool, str]]:
    """
    批量处理多个数据源
    返回 [(源, 是否成功, 消息/路径)]
    """
    if not os.path.exists(output_dir):
        try:
            os.makedirs(output_dir, exist_ok=True)
        except Exception as e:
            raise VizroError("E009", f"无法创建输出目录: {str(e)}")

    results = []
    for i, source in enumerate(inputs):
        try:
            if source.startswith(("http://", "https://")):
                data = load_data_from_url(source)
            else:
                data = load_data_from_file(source)

            config = build_dashboard(data, source=source)
            output_name = f"dashboard_{i+1}.json"
            output_path = os.path.join(output_dir, output_name)
            save_config(config, output_path)
            results.append((source, True, output_path))
        except VizroError as e:
            results.append((source, False, f"{e.code}: {e.message}"))
        except Exception as e:
            results.append((source, False, f"E010: {str(e)}"))

    # 检查是否全部失败
    success_count = sum(1 for _, ok, _ in results if ok)
    if success_count == 0:
        raise VizroError("E008", "所有文件处理失败")
    return results


# ---------- 自检 ----------

def run_selftest() -> bool:
    """
    内置自检：使用硬编码样例数据验证核心逻辑
    不依赖外部文件/网络/工作目录
    """
    print("=" * 60)
    print("运行内置自检 (selftest)...")
    print("=" * 60)

    # 硬编码样例数据
    sample_data = [
        {"city": "北京", "sales": 120, "month": "2024-01"},
        {"city": "上海", "sales": 150, "month": "2024-01"},
        {"city": "广州", "sales": 90, "month": "2024-01"},
        {"city": "北京", "sales": 135, "month": "2024-02"},
        {"city": "上海", "sales": 165, "month": "2024-02"},
        {"city": "广州", "sales": 100, "month": "2024-02"},
        {"city": "北京", "sales": 145, "month": "2024-03"},
        {"city": "上海", "sales": 180, "month": "2024-03"},
        {"city": "广州", "sales": 110, "month": "2024-03"},
    ]

    # 1. 测试列分析
    print("\n[1/5] 测试列分析...")
    columns = analyze_columns(sample_data)
    assert len(columns) >= 2, "应至少分析出 2 列"
    col_names = {c.name for c in columns}
    assert "city" in col_names and "sales" in col_names, "应包含 city 和 sales 列"
    sales_col = next(c for c in columns if c.name == "sales")
    assert sales_col.data_type == "numeric", "sales 应为数值类型"
    city_col = next(c for c in columns if c.name == "city")
    assert city_col.data_type == "categorical", "city 应为分类类型"
    print(f"  ✓ 列分析通过 ({len(columns)} 列)")

    # 2. 测试图表生成
    print("\n[2/5] 测试图表生成...")
    charts = generate_charts(sample_data, columns, max_charts=5)
    assert len(charts) >= 1, "应至少生成 1 个图表"
    chart_types = {c.chart_type for c in charts}
    assert "bar" in chart_types, "应包含柱状图"
    for chart in charts:
        assert 0.0 <= chart.confidence <= 1.0, "置信度应在 0~1 之间"
        assert chart.confidence > 0.5, "置信度应大于 0.5"
    print(f"  ✓ 图表生成通过 ({len(charts)} 个图表)")

    # 3. 测试仪表盘构建
    print("\n[3/5] 测试仪表盘构建...")
    config = build_dashboard(sample_data, source="selftest")
    assert config.row_count == len(sample_data), "行数应匹配"
    assert len(config.charts) >= 1, "仪表盘应包含图表"
    config_dict = config_to_dict(config)
    assert "charts" in config_dict and "columns" in config_dict, "配置字典应包含关键字段"
    print(f"  ✓ 仪表盘构建通过 (标题: {config.title})")

    # 4. 测试 CSV 解析（内存中）
    print("\n[4/5] 测试 CSV 解析...")
    csv_content = "name,value\nitem1,10\nitem2,20\nitem3,30\n"
    parsed = _parse_csv(csv_content)
    assert len(parsed) == 3, "应解析出 3 行"
    assert parsed[0]["value"] == 10, "数值应自动转换"
    assert parsed[1]["name"] == "item2", "字符串应保留"
    print("  ✓ CSV 解析通过")

    # 5. 测试 JSON 解析（内存中）
    print("\n[5/5] 测试 JSON 解析...")
    json_content = json.dumps([{"a": 1, "b": "x"}, {"a": 2, "b": "y"}])
    parsed_json = _parse_json(json_content)
    assert len(parsed_json) == 2, "应解析出 2 条记录"
    assert parsed_json[0]["a"] == 1, "数值应正确解析"
    print("  ✓ JSON 解析通过")

    print("\n" + "=" * 60)
    print("✓✓ 所有自检通过！")
    print("=" * 60)
    return True


# ---------- 命令行入口 ----------

def main() -> int:
    """主入口"""
    parser = argparse.ArgumentParser(
        description="vizro 数据可视化低代码仪表盘工具",
        epilog="示例: python main.py data.csv -o output.json",
    )
    parser.add_argument("inputs", nargs="*", help="输入文件路径或 URL")
    parser.add_argument("-o", "--output", default="dashboard.json", help="输出 JSON 文件路径")
    parser.add_argument("-d", "--output-dir", default="output", help="批量处理输出目录")
    parser.add_argument("-t", "--title", default="", help="仪表盘标题")
    parser.add_argument("--batch", action="store_true", help="批量处理模式")
    parser.add_argument("--selftest", action="store_true", help="运行内置自检")
    parser.add_argument("--version", action="version", version="vizro 1.0.1")

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        try:
            run_selftest()
            return 0
        except AssertionError as e:
            print(f"\n✗ 自检失败: {str(e)}")
            return 1
        except Exception as e:
            print(f"\n✗ 自检异常: {str(e)}")
            return 1

    # 常规模式
    if not args.inputs:
        parser.print_help()
        return 1

    try:
        if args.batch:
            # 批量处理
            results = batch_process(args.inputs, args.output_dir)
            print(f"\n批量处理完成，共 {len(results)} 个输入：")
            for source, ok, msg in results:
                status = "✓" if ok else "✗"
                print(f"  {status} {source} -> {msg}")
            return 0
        else:
            # 单文件处理
            source = args.inputs[0]
            if source.startswith(("http://", "https://")):
                data = load_data_from_url(source)
            else:
                data = load_data_from_file(source)

            config = build_dashboard(data, source=source, title=args.title)
            save_config(config, args.output)
            print(f"✓ 仪表盘配置已生成: {args.output}")
            print(f"  数据行数: {config.row_count}")
            print(f"  图表数量: {len(config.charts)}")
            return 0

    except VizroError as e:
        print(f"错误: {e.code} - {e.message}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"错误: E010 - 未知异常: {str(e)}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
