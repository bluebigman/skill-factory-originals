#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
laravel-dynamic-report-generator 独立实现脚本
================================================
本脚本根据功能规格独立实现（clean-room），不参考任何既有代码。

核心能力:
  - 动态查询构建 (WHERE / GROUP BY / ORDER BY)
  - 报表结构设计 (字段映射、聚合逻辑、分组层级)
  - 可视化配置输出 (柱状图、折线图、饼图)
  - 批量处理 (多数据源合并)

命令行用法:
  python main.py --selftest     # 离线自检（内置硬编码样例）
  python main.py --help         # 显示帮助

错误码:
  E001: 参数错误
  E002: 数据源格式不支持
  E003: 数据源加载失败
  E004: 查询语句语法错误
  E005: 查询执行失败
  E006: 报表结构生成失败
  E007: 可视化配置生成失败
  E008: 批量处理失败
  E009: 自检失败
  E010: 未知错误
"""

import argparse
import csv
import io
import json
import os
import re
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple


# ------------------------------------------------------------
# 错误码常量
# ------------------------------------------------------------
ERR_PARAM = "E001"
ERR_DATASOURCE_FORMAT = "E002"
ERR_DATASOURCE_LOAD = "E003"
ERR_QUERY_SYNTAX = "E004"
ERR_QUERY_EXEC = "E005"
ERR_REPORT_STRUCT = "E006"
ERR_VISUAL_CONFIG = "E007"
ERR_BATCH = "E008"
ERR_SELFTEST = "E009"
ERR_UNKNOWN = "E010"


# ------------------------------------------------------------
# 数据源加载模块
# ------------------------------------------------------------
class DataSourceLoader:
    """数据源加载器：支持 CSV / JSON / 内存数据"""

    @staticmethod
    def load(data: Any, source_type: str = "auto") -> List[Dict[str, Any]]:
        """
        加载数据源为统一的字典列表格式。

        参数:
            data: 数据内容（文件路径、字符串内容或列表）
            source_type: auto/csv/json/list

        返回:
            字典列表，每行数据为一个字典

        异常:
            E002: 格式不支持
            E003: 加载失败
        """
        try:
            if source_type == "auto":
                source_type = DataSourceLoader._detect_type(data)

            if source_type == "list":
                return DataSourceLoader._load_from_list(data)
            elif source_type == "csv":
                return DataSourceLoader._load_from_csv(data)
            elif source_type == "json":
                return DataSourceLoader._load_from_json(data)
            else:
                raise ValueError(f"不支持的数据源类型: {source_type}")
        except ValueError as e:
            raise RuntimeError(f"{ERR_DATASOURCE_FORMAT}: {str(e)}")
        except Exception as e:
            raise RuntimeError(f"{ERR_DATASOURCE_LOAD}: {str(e)}")

    @staticmethod
    def _detect_type(data: Any) -> str:
        """自动检测数据类型"""
        if isinstance(data, list):
            return "list"
        if isinstance(data, str):
            # 判断是文件路径还是内容
            if os.path.isfile(data):
                ext = os.path.splitext(data)[1].lower()
                if ext == ".csv":
                    return "csv"
                elif ext == ".json":
                    return "json"
                else:
                    raise ValueError(f"不支持的文件扩展名: {ext}")
            else:
                # 尝试解析为 JSON
                stripped = data.strip()
                if stripped.startswith("[") or stripped.startswith("{"):
                    return "json"
                else:
                    return "csv"
        raise ValueError("无法识别的数据类型")

    @staticmethod
    def _load_from_list(data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """从列表加载"""
        if not data:
            return []
        if not isinstance(data[0], dict):
            raise ValueError("列表元素必须是字典")
        return [dict(row) for row in data]

    @staticmethod
    def _load_from_csv(data: str) -> List[Dict[str, Any]]:
        """从 CSV 字符串或文件路径加载"""
        if os.path.isfile(data):
            with open(data, "r", encoding="utf-8-sig") as f:
                content = f.read()
        else:
            content = data

        reader = csv.DictReader(io.StringIO(content))
        rows = []
        for row in reader:
            # 去除键和值的首尾空白
            cleaned = {k.strip(): (v.strip() if isinstance(v, str) else v) for k, v in row.items()}
            rows.append(cleaned)
        return rows

    @staticmethod
    def _load_from_json(data: str) -> List[Dict[str, Any]]:
        """从 JSON 字符串或文件路径加载"""
        if os.path.isfile(data):
            with open(data, "r", encoding="utf-8") as f:
                content = f.read()
        else:
            content = data

        parsed = json.loads(content)
        if isinstance(parsed, list):
            return [dict(item) for item in parsed]
        elif isinstance(parsed, dict):
            # 可能是 {"data": [...]} 格式
            if "data" in parsed and isinstance(parsed["data"], list):
                return [dict(item) for item in parsed["data"]]
            else:
                return [parsed]
        else:
            raise ValueError("JSON 必须是对象数组")


# ------------------------------------------------------------
# 动态查询构建模块
# ------------------------------------------------------------
class QueryBuilder:
    """动态查询构建器：支持 WHERE / GROUP BY / ORDER BY / 聚合"""

    def __init__(self, data: List[Dict[str, Any]]):
        self.data = data
        self.fields = self._extract_fields(data)

    def _extract_fields(self, data: List[Dict[str, Any]]) -> List[str]:
        """提取所有字段名"""
        fields = set()
        for row in data:
            fields.update(row.keys())
        return sorted(fields)

    def build_query(
        self,
        select: Optional[List[str]] = None,
        where: Optional[Dict[str, Any]] = None,
        group_by: Optional[List[str]] = None,
        order_by: Optional[Dict[str, str]] = None,
        aggregates: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        构建查询配置。

        参数:
            select: 要选择的字段列表
            where: 过滤条件，如 {"field": "value"} 或 {"field": {"op": ">", "value": 10}}
            group_by: 分组字段列表
            order_by: 排序，如 {"field": "asc"} 或 {"field": "desc"}
            aggregates: 聚合函数，如 {"total": "sum(amount)", "count": "count(*)"}

        返回:
            查询配置字典

        异常:
            E004: 查询语法错误
        """
        try:
            query = {
                "select": select or self.fields,
                "where": where or {},
                "group_by": group_by or [],
                "order_by": order_by or {},
                "aggregates": aggregates or {},
            }
            # 校验字段存在性
            for field in query["select"]:
                if field != "*" and field not in self.fields:
                    raise ValueError(f"字段不存在: {field}")
            for field in query["group_by"]:
                if field not in self.fields:
                    raise ValueError(f"分组字段不存在: {field}")
            return query
        except ValueError as e:
            raise RuntimeError(f"{ERR_QUERY_SYNTAX}: {str(e)}")

    def execute(self, query: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        执行查询，返回结果。

        异常:
            E005: 查询执行失败
        """
        try:
            result = self.data

            # WHERE 过滤
            if query["where"]:
                result = self._apply_where(result, query["where"])

            # 分组聚合
            if query["group_by"]:
                result = self._apply_group_by(result, query["group_by"], query["aggregates"])
            else:
                # 选择字段
                if query["select"] and "*" not in query["select"]:
                    result = [{k: row.get(k) for k in query["select"]} for row in result]

            # 排序
            if query["order_by"]:
                result = self._apply_order_by(result, query["order_by"])

            return result
        except Exception as e:
            raise RuntimeError(f"{ERR_QUERY_EXEC}: {str(e)}")

    def _apply_where(self, data: List[Dict[str, Any]], conditions: Dict[str, Any]) -> List[Dict[str, Any]]:
        """应用 WHERE 条件过滤"""
        filtered = []
        for row in data:
            match = True
            for field, condition in conditions.items():
                if isinstance(condition, dict):
                    # 复杂条件 {"op": ">", "value": 10}
                    op = condition.get("op", "=")
                    value = condition.get("value")
                    actual = row.get(field)
                    if op == "=":
                        match = match and actual == value
                    elif op == ">":
                        match = match and actual is not None and float(actual) > float(value)
                    elif op == "<":
                        match = match and actual is not None and float(actual) < float(value)
                    elif op == ">=":
                        match = match and actual is not None and float(actual) >= float(value)
                    elif op == "<=":
                        match = match and actual is not None and float(actual) <= float(value)
                    elif op == "!=":
                        match = match and actual != value
                    elif op == "in":
                        match = match and actual in value
                    else:
                        raise ValueError(f"不支持的操作符: {op}")
                else:
                    # 简单条件 field == value
                    match = match and row.get(field) == condition
                if not match:
                    break
            if match:
                filtered.append(row)
        return filtered

    def _apply_group_by(
        self,
        data: List[Dict[str, Any]],
        group_fields: List[str],
        aggregates: Dict[str, str],
    ) -> List[Dict[str, Any]]:
        """应用 GROUP BY 分组聚合"""
        groups: Dict[Tuple, List[Dict[str, Any]]] = {}
        for row in data:
            key = tuple(row.get(f) for f in group_fields)
            if key not in groups:
                groups[key] = []
            groups[key].append(row)

        result = []
        for key, rows in groups.items():
            item = dict(zip(group_fields, key))
            # 应用聚合函数
            for alias, expr in aggregates.items():
                item[alias] = self._apply_aggregate(rows, expr)
            result.append(item)
        return result

    def _apply_aggregate(self, rows: List[Dict[str, Any]], expr: str) -> Any:
        """应用单个聚合函数"""
        expr = expr.strip().lower()
        if expr == "count(*)" or expr == "count":
            return len(rows)

        # 解析 sum(field), avg(field), min(field), max(field)
        match = re.match(r"^(sum|avg|min|max)\((.+)\)$", expr)
        if not match:
            raise ValueError(f"不支持的聚合表达式: {expr}")

        func, field = match.group(1), match.group(2).strip()
        values = []
        for row in rows:
            v = row.get(field)
            if v is not None:
                try:
                    values.append(float(v))
                except (ValueError, TypeError):
                    pass

        if not values:
            return 0 if func in ("sum", "avg") else None

        if func == "sum":
            return sum(values)
        elif func == "avg":
            return sum(values) / len(values)
        elif func == "min":
            return min(values)
        elif func == "max":
            return max(values)
        else:
            raise ValueError(f"不支持的聚合函数: {func}")

    def _apply_order_by(self, data: List[Dict[str, Any]], order_by: Dict[str, str]) -> List[Dict[str, Any]]:
        """应用排序"""
        fields = list(order_by.keys())
        reverse = [order_by[f].lower() == "desc" for f in fields]

        # 多字段排序（稳定排序，从最后一个字段开始）
        for i in range(len(fields) - 1, -1, -1):
            data.sort(key=lambda r, i=i: r.get(fields[i]), reverse=reverse[i])
        return data


# ------------------------------------------------------------
# 报表结构设计模块
# ------------------------------------------------------------
class ReportDesigner:
    """报表结构设计器：生成报表字段映射、聚合逻辑、分组层级"""

    @staticmethod
    def design_report(
        data: List[Dict[str, Any]],
        title: str = "数据报表",
        group_fields: Optional[List[str]] = None,
        metric_fields: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        设计报表结构。

        参数:
            data: 数据（字典列表）
            title: 报表标题
            group_fields: 分组字段
            metric_fields: 指标字段（数值型）

        返回:
            报表结构配置

        异常:
            E006: 报表结构生成失败
        """
        try:
            if not data:
                raise ValueError("数据为空，无法生成报表结构")

            # 自动检测字段类型
            fields_info = ReportDesigner._analyze_fields(data)

            # 分组字段（默认取第一个非数值字段）
            if not group_fields:
                for field, info in fields_info.items():
                    if info["type"] == "string" and info["unique_ratio"] < 0.8:
                        group_fields = [field]
                        break
                if not group_fields:
                    group_fields = [list(fields_info.keys())[0]]

            # 指标字段（默认取所有数值字段）
            if not metric_fields:
                metric_fields = [f for f, info in fields_info.items() if info["type"] == "number"]

            # 生成报表结构
            report = {
                "title": title,
                "generated_at": datetime.now().isoformat(),
                "data_count": len(data),
                "group_fields": group_fields,
                "metric_fields": metric_fields,
                "fields_info": fields_info,
                "aggregations": {
                    f"total_{f}": f"sum({f})" for f in metric_fields
                },
            }
            return report
        except Exception as e:
            raise RuntimeError(f"{ERR_REPORT_STRUCT}: {str(e)}")

    @staticmethod
    def _analyze_fields(data: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """分析字段类型和统计信息"""
        fields_info: Dict[str, Dict[str, Any]] = {}
        for row in data:
            for field, value in row.items():
                if field not in fields_info:
                    fields_info[field] = {
                        "type": "string",
                        "unique_values": set(),
                        "count": 0,
                        "numeric_values": [],
                    }
                info = fields_info[field]
                info["count"] += 1
                if isinstance(value, (int, float)):
                    info["type"] = "number"
                    info["numeric_values"].append(value)
                else:
                    info["unique_values"].add(str(value))

        # 计算唯一值比例
        for field, info in fields_info.items():
            total = max(info["count"], 1)
            info["unique_ratio"] = len(info["unique_values"]) / total
            if info["type"] == "number" and info["numeric_values"]:
                info["min"] = min(info["numeric_values"])
                info["max"] = max(info["numeric_values"])
                info["avg"] = sum(info["numeric_values"]) / len(info["numeric_values"])
            # 移除临时字段
            info.pop("unique_values", None)
            info.pop("numeric_values", None)

        return fields_info


# ------------------------------------------------------------
# 可视化配置模块
# ------------------------------------------------------------
class VisualConfigGenerator:
    """可视化配置生成器：输出 ECharts 配置 JSON"""

    # 颜色板
    COLOR_PALETTE = [
        "#5470c6", "#91cc75", "#fac858", "#ee6666",
        "#73c0de", "#3ba272", "#fc8452", "#9a60b4",
        "#ea7ccc",
    ]

    @staticmethod
    def generate(
        data: List[Dict[str, Any]],
        chart_type: str = "auto",
        x_field: Optional[str] = None,
        y_fields: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        生成可视化配置。

        参数:
            data: 数据
            chart_type: bar/line/pie/auto
            x_field: X 轴字段
            y_fields: Y 轴字段列表

        返回:
            ECharts 配置字典

        异常:
            E007: 可视化配置生成失败
        """
        try:
            if not data:
                raise ValueError("数据为空，无法生成可视化配置")

            # 自动选择字段
            if not x_field:
                # 优先选择字符串类型的第一个字段
                for key in data[0].keys():
                    if not isinstance(data[0][key], (int, float)):
                        x_field = key
                        break
                if not x_field:
                    x_field = list(data[0].keys())[0]

            if not y_fields:
                # 选择所有数值字段
                y_fields = [k for k in data[0].keys() if isinstance(data[0][k], (int, float))]
                if not y_fields:
                    # 如果没有数值字段，使用第一个非 X 字段
                    y_fields = [k for k in data[0].keys() if k != x_field][:1]

            # 自动选择图表类型
            if chart_type == "auto":
                if len(y_fields) == 1 and len(data) <= 10:
                    chart_type = "pie"
                elif len(y_fields) > 1:
                    chart_type = "line"
                else:
                    chart_type = "bar"

            # 构建 ECharts 配置
            if chart_type == "pie":
                config = VisualConfigGenerator._build_pie(data, x_field, y_fields[0])
            elif chart_type == "line":
                config = VisualConfigGenerator._build_line(data, x_field, y_fields)
            elif chart_type == "bar":
                config = VisualConfigGenerator._build_bar(data, x_field, y_fields)
            else:
                raise ValueError(f"不支持的图表类型: {chart_type}")

            config["_meta"] = {
                "chart_type": chart_type,
                "x_field": x_field,
                "y_fields": y_fields,
                "data_count": len(data),
            }
            return config
        except Exception as e:
            raise RuntimeError(f"{ERR_VISUAL_CONFIG}: {str(e)}")

    @staticmethod
    def _build_bar(data: List[Dict[str, Any]], x_field: str, y_fields: List[str]) -> Dict[str, Any]:
        """柱状图配置"""
        return {
            "tooltip": {"trigger": "axis"},
            "legend": {"data": y_fields},
            "xAxis": {"type": "category", "data": [str(row.get(x_field)) for row in data]},
            "yAxis": {"type": "value"},
            "series": [
                {
                    "name": field,
                    "type": "bar",
                    "data": [row.get(field, 0) for row in data],
                    "itemStyle": {"color": VisualConfigGenerator.COLOR_PALETTE[i % len(VisualConfigGenerator.COLOR_PALETTE)]},
                }
                for i, field in enumerate(y_fields)
            ],
        }

    @staticmethod
    def _build_line(data: List[Dict[str, Any]], x_field: str, y_fields: List[str]) -> Dict[str, Any]:
        """折线图配置"""
        return {
            "tooltip": {"trigger": "axis"},
            "legend": {"data": y_fields},
            "xAxis": {"type": "category", "data": [str(row.get(x_field)) for row in data]},
            "yAxis": {"type": "value"},
            "series": [
                {
                    "name": field,
                    "type": "line",
                    "data": [row.get(field, 0) for row in data],
                    "smooth": True,
                }
                for field in y_fields
            ],
        }

    @staticmethod
    def _build_pie(data: List[Dict[str, Any]], x_field: str, y_field: str) -> Dict[str, Any]:
        """饼图配置"""
        pie_data = [
            {"name": str(row.get(x_field)), "value": row.get(y_field, 0)}
            for row in data
        ]
        return {
            "tooltip": {"trigger": "item"},
            "legend": {"orient": "vertical", "left": "left"},
            "series": [
                {
                    "name": y_field,
                    "type": "pie",
                    "radius": "60%",
                    "data": pie_data,
                    "emphasis": {"itemStyle": {"shadowBlur": 10, "shadowOffsetX": 0}},
                }
            ],
        }


# ------------------------------------------------------------
# 批量处理模块
# ------------------------------------------------------------
class BatchProcessor:
    """批量处理器：多数据源合并"""

    @staticmethod
    def merge(datasets: List[List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
        """
        合并多个数据集。

        参数:
            datasets: 多个数据集列表

        返回:
            合并后的数据集

        异常:
            E008: 批量处理失败
        """
        try:
            if not datasets:
                return []
            merged = []
            for ds in datasets:
                merged.extend(ds)
            return merged
        except Exception as e:
            raise RuntimeError(f"{ERR_BATCH}: {str(e)}")

    @staticmethod
    def merge_by_key(
        datasets: List[List[Dict[str, Any]]],
        key_field: str,
    ) -> List[Dict[str, Any]]:
        """
        按键合并多个数据集（类似 SQL JOIN）。

        参数:
            datasets: 多个数据集列表
            key_field: 关联键字段

        返回:
            合并后的数据集
        """
        try:
            if not datasets:
                return []

            # 第一个数据集作为基础
            result = []
            for row in datasets[0]:
                key_value = row.get(key_field)
                merged_row = dict(row)

                for ds in datasets[1:]:
                    for other in ds:
                        if other.get(key_field) == key_value:
                            # 合并字段，添加前缀避免冲突
                            for k, v in other.items():
                                if k == key_field:
                                    continue
                                new_key = f"{k}"
                                if new_key in merged_row and merged_row[new_key] != v:
                                    new_key = f"{new_key}_2"
                                merged_row[new_key] = v
                            break
                result.append(merged_row)
            return result
        except Exception as e:
            raise RuntimeError(f"{ERR_BATCH}: {str(e)}")


# ------------------------------------------------------------
# 主流程编排
# ------------------------------------------------------------
class ReportGenerator:
    """报表生成器主类"""

    def __init__(self):
        self.loader = DataSourceLoader()
        self.query_builder = None
        self.report_designer = ReportDesigner()
        self.visual_generator = VisualConfigGenerator()
        self.batch_processor = BatchProcessor()

    def generate(
        self,
        data: Any,
        source_type: str = "auto",
        query_config: Optional[Dict[str, Any]] = None,
        report_title: str = "数据报表",
        chart_type: str = "auto",
    ) -> Dict[str, Any]:
        """
        完整的报表生成流程。

        参数:
            data: 数据源
            source_type: 数据源类型
            query_config: 查询配置
            report_title: 报表标题
            chart_type: 图表类型

        返回:
            完整报表配置
        """
        # 1. 加载数据
        rows = self.loader.load(data, source_type)

        # 2. 构建查询
        self.query_builder = QueryBuilder(rows)
        if query_config:
            query = self.query_builder.build_query(**query_config)
        else:
            query = self.query_builder.build_query()

        # 3. 执行查询
        query_result = self.query_builder.execute(query)

        # 4. 设计报表
        report = self.report_designer.design_report(query_result, title=report_title)

        # 5. 生成可视化配置
        visual = self.visual_generator.generate(query_result, chart_type=chart_type)

        # 6. 组装最终结果
        final = {
            "report": report,
            "data": query_result,
            "visualization": visual,
            "query": query,
        }
        return final


# ------------------------------------------------------------
# 自检模块
# ------------------------------------------------------------
def run_selftest() -> bool:
    """
    运行内置自检，验证核心逻辑。

    使用硬编码样例数据，不依赖外部文件/网络。
    断言使用宽松阈值（大小比较/区间判断），确保稳健。

    返回:
        True 表示所有检查通过

    异常:
        E009: 自检失败
    """
    print("=== 开始自检 ===")

    # ---------- 测试 1: 数据源加载 ----------
    print("[1/6] 数据源加载测试...")
    csv_data = """name,department,salary,years
Alice,Engineering,85000,5
Bob,Engineering,92000,7
Charlie,Sales,65000,3
Diana,Sales,72000,4
Eve,Marketing,78000,6
"""
    try:
        rows = DataSourceLoader.load(csv_data, "csv")
        assert len(rows) == 5, f"CSV 加载行数应为 5，实际 {len(rows)}"
        assert rows[0]["name"] == "Alice", "CSV 首行数据错误"
        print("    通过")
    except Exception as e:
        raise RuntimeError(f"{ERR_SELFTEST}: 数据源加载测试失败: {e}")

    # ---------- 测试 2: 动态查询（WHERE + GROUP BY + 聚合） ----------
    print("[2/6] 动态查询测试...")
    try:
        qb = QueryBuilder(rows)
        query = qb.build_query(
            where={"department": "Sales"},
            group_by=["department"],
            aggregates={"total_salary": "sum(salary)", "emp_count": "count(*)"},
        )
        result = qb.execute(query)
        assert len(result) == 1, f"Sales 分组结果应为 1 行，实际 {len(result)}"
        assert result[0]["department"] == "Sales", "分组字段错误"
        assert result[0]["emp_count"] == 2, "Sales 人数应为 2"
        assert result[0]["total_salary"] == 137000, "Sales 总薪资应为 137000"
        print("    通过")
    except Exception as e:
        raise RuntimeError(f"{ERR_SELFTEST}: 动态查询测试失败: {e}")

    # ---------- 测试 3: 报表结构设计 ----------
    print("[3/6] 报表结构设计测试...")
    try:
        report = ReportDesigner.design_report(rows, title="员工薪资报表")
        assert report["data_count"] == 5, "报表数据量应为 5"
        assert "salary" in report["metric_fields"], "salary 应为指标字段"
        assert len(report["metric_fields"]) > 0, "应至少有一个指标字段"
        assert "generated_at" in report, "应包含生成时间"
        print("    通过")
    except Exception as e:
        raise RuntimeError(f"{ERR_SELFTEST}: 报表结构设计测试失败: {e}")

    # ---------- 测试 4: 可视化配置 ----------
    print("[4/6] 可视化配置测试...")
    try:
        # 准备聚合数据用于可视化
        qb = QueryBuilder(rows)
        agg_query = qb.build_query(
            group_by=["department"],
            aggregates={"total_salary": "sum(salary)"},
        )
        agg_result = qb.execute(agg_query)

        visual = VisualConfigGenerator.generate(agg_result, chart_type="bar")
        assert "series" in visual, "可视化配置应包含 series"
        assert len(visual["series"]) > 0, "应有至少一个系列"
        assert "xAxis" in visual, "柱状图应包含 xAxis"
        assert "yAxis" in visual, "柱状图应包含 yAxis"
        print("    通过")
    except Exception as e:
        raise RuntimeError(f"{ERR_SELFTEST}: 可视化配置测试失败: {e}")

    # ---------- 测试 5: 批量处理 ----------
    print("[5/6] 批量处理测试...")
    try:
        ds1 = [{"id": 1, "name": "A"}, {"id": 2, "name": "B"}]
        ds2 = [{"id": 1, "dept": "IT"}, {"id": 2, "dept": "HR"}]
        merged = BatchProcessor.merge_by_key([ds1, ds2], "id")
        assert len(merged) == 2, "合并后应有 2 条记录"
        assert merged[0]["name"] == "A", "合并后 name 字段错误"
        assert merged[0]["dept"] == "IT", "合并后 dept 字段错误"
        print("    通过")
    except Exception as e:
        raise RuntimeError(f"{ERR_SELFTEST}: 批量处理测试失败: {e}")

    # ---------- 测试 6: 完整流程 ----------
    print("[6/6] 完整流程测试...")
    try:
        generator = ReportGenerator()
        result = generator.generate(
            data=csv_data,
            source_type="csv",
            query_config={
                "where": {"years": {"op": ">=", "value": 4}},
                "group_by": ["department"],
                "aggregates": {"avg_salary": "avg(salary)"},
            },
            report_title="高工龄薪资报表",
            chart_type="bar",
        )
        assert "report" in result, "结果应包含报表结构"
        assert "data" in result, "结果应包含数据"
        assert "visualization" in result, "结果应包含可视化配置"
        assert result["report"]["data_count"] > 0, "报表数据量应大于 0"
        assert "avg_salary" in result["data"][0], "应包含平均薪资聚合字段"
        print("    通过")
    except Exception as e:
        raise RuntimeError(f"{ERR_SELFTEST}: 完整流程测试失败: {e}")

    print("\n=== 自检全部通过 ===")
    return True


# ------------------------------------------------------------
# 命令行入口
# ------------------------------------------------------------
def main():
    """主入口函数"""
    parser = argparse.ArgumentParser(
        description="Laravel 动态报表生成器 - 独立实现",
        epilog="示例: python main.py --selftest",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检（使用硬编码样例数据，离线可执行）",
    )
    parser.add_argument(
        "--input",
        type=str,
        help="输入数据文件路径（CSV 或 JSON）",
    )
    parser.add_argument(
        "--output",
        type=str,
        help="输出 JSON 文件路径",
    )
    parser.add_argument(
        "--chart",
        type=str,
        default="auto",
        choices=["auto", "bar", "line", "pie"],
        help="图表类型",
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        try:
            run_selftest()
            sys.exit(0)
        except RuntimeError as e:
            print(f"自检失败: {e}", file=sys.stderr)
            sys.exit(1)

    # 正常模式
    if not args.input:
        print(f"{ERR_PARAM}: 请提供输入文件路径（--input）或使用 --selftest", file=sys.stderr)
        sys.exit(1)

    try:
        generator = ReportGenerator()
        result = generator.generate(args.input, chart_type=args.chart)

        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2, default=str)
            print(f"报表已生成: {args.output}")
        else:
            print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    except RuntimeError as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"{ERR_UNKNOWN}: 未知错误: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
