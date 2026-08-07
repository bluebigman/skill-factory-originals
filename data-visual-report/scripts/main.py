#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
data-visual-report 技能实现脚本

功能：
- 将表格数据（CSV/JSON）自动转为带图表与结论的可视化分析报告
- 支持趋势分析、占比统计、TopN排行、图表生成、结论提炼
- 提供 --selftest 参数进行离线自检

错误码：
- E001: 参数错误
- E002: 文件不存在
- E003: 文件格式不支持
- E004: 数据为空
- E005: 字段缺失
- E006: 数据类型错误
- E007: 数据行数不足
- E008: 数值计算错误
- E009: 输出目录不可写
- E010: 未知错误

用法示例：
    python main.py --input data.csv --output report.md
    python main.py --input data.json --output report.md --topn 5
    python main.py --selftest
"""

import argparse
import json
import os
import sys
import tempfile
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# 错误码定义
# ============================================================
class SkillError(Exception):
    """技能基础异常类"""
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(f"[{code}] {message}")


# ============================================================
# 数据加载模块
# ============================================================
class DataLoader:
    """数据加载器：支持 CSV 和 JSON 格式"""

    @staticmethod
    def load(file_path: str) -> List[Dict[str, Any]]:
        """从文件加载数据"""
        if not os.path.exists(file_path):
            raise SkillError("E002", f"文件不存在: {file_path}")

        ext = os.path.splitext(file_path)[1].lower()
        if ext == ".csv":
            return DataLoader._load_csv(file_path)
        elif ext == ".json":
            return DataLoader._load_json(file_path)
        else:
            raise SkillError("E003", f"不支持的文件格式: {ext}，仅支持 .csv 和 .json")

    @staticmethod
    def _load_csv(file_path: str) -> List[Dict[str, Any]]:
        """加载 CSV 文件"""
        import csv

        try:
            with open(file_path, "r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                if not reader.fieldnames:
                    raise SkillError("E004", "CSV 文件无表头")
                data = [dict(row) for row in reader]
        except SkillError:
            raise
        except Exception as e:
            raise SkillError("E006", f"CSV 解析失败: {str(e)}")

        if not data:
            raise SkillError("E004", "CSV 文件无数据行")

        return data

    @staticmethod
    def _load_json(file_path: str) -> List[Dict[str, Any]]:
        """加载 JSON 文件"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                raw = json.load(f)
        except Exception as e:
            raise SkillError("E006", f"JSON 解析失败: {str(e)}")

        if isinstance(raw, dict):
            # 兼容 {"data": [...]} 格式
            if "data" in raw and isinstance(raw["data"], list):
                data = raw["data"]
            else:
                raise SkillError("E006", "JSON 对象格式应为 {'data': [...]}")
        elif isinstance(raw, list):
            data = raw
        else:
            raise SkillError("E006", "JSON 应为数组或包含 data 数组的对象")

        if not data:
            raise SkillError("E004", "JSON 数据为空")

        return data


# ============================================================
# 数据分析模块
# ============================================================
class DataAnalyzer:
    """数据分析器：执行趋势、占比、TopN 分析"""

    def __init__(self, data: List[Dict[str, Any]]):
        self.data = data
        if len(data) < 5:
            raise SkillError("E007", f"数据行数不足，至少需要 5 行，当前 {len(data)} 行")
        if len(data[0].keys()) < 2:
            raise SkillError("E005", "字段数不足，至少需要 2 列")

    def get_fields(self) -> List[str]:
        """获取全部字段名"""
        return list(self.data[0].keys())

    def _to_numeric(self, value: Any) -> Optional[float]:
        """尝试转换为数值"""
        if value is None:
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None

    def trend_analysis(self, time_field: str, value_field: str) -> Dict[str, Any]:
        """趋势分析：识别上升/下降/波动"""
        if time_field not in self.data[0] or value_field not in self.data[0]:
            raise SkillError("E005", f"字段不存在: {time_field} 或 {value_field}")

        values = []
        for row in self.data:
            v = self._to_numeric(row.get(value_field))
            if v is None:
                raise SkillError("E006", f"字段 {value_field} 包含非数值数据")
            values.append(v)

        if len(values) < 3:
            raise SkillError("E007", "趋势分析至少需要 3 个数据点")

        # 计算简单线性回归斜率
        n = len(values)
        x_mean = (n - 1) / 2.0
        y_mean = sum(values) / n
        numerator = sum((i - x_mean) * (v - y_mean) for i, v in enumerate(values))
        denominator = sum((i - x_mean) ** 2 for i in range(n))

        if denominator == 0:
            slope = 0.0
        else:
            slope = numerator / denominator

        # 波动性：标准差
        variance = sum((v - y_mean) ** 2 for v in values) / n
        std_dev = variance ** 0.5

        # 判定趋势
        if abs(slope) < 0.01 * (abs(y_mean) + 1e-9):
            trend = "平稳"
        elif slope > 0:
            trend = "上升"
        else:
            trend = "下降"

        return {
            "time_field": time_field,
            "value_field": value_field,
            "trend": trend,
            "slope": slope,
            "mean": y_mean,
            "std_dev": std_dev,
            "min": min(values),
            "max": max(values),
            "values": values,
        }

    def proportion_analysis(self, category_field: str, value_field: str) -> Dict[str, Any]:
        """占比统计：各分类在总体中的份额"""
        if category_field not in self.data[0] or value_field not in self.data[0]:
            raise SkillError("E005", f"字段不存在: {category_field} 或 {value_field}")

        proportions: Dict[str, float] = {}
        for row in self.data:
            cat = str(row.get(category_field, ""))
            v = self._to_numeric(row.get(value_field))
            if v is None:
                raise SkillError("E006", f"字段 {value_field} 包含非数值数据")
            proportions[cat] = proportions.get(cat, 0.0) + v

        total = sum(proportions.values())
        if total == 0:
            raise SkillError("E008", "数值总和为 0，无法计算占比")

        result = {k: v / total for k, v in proportions.items()}
        return {
            "category_field": category_field,
            "value_field": value_field,
            "proportions": result,
            "total": total,
        }

    def topn_analysis(self, dimension_field: str, sort_field: str, n: int = 5) -> Dict[str, Any]:
        """TopN 排行：按指定指标取前 N 名"""
        if dimension_field not in self.data[0] or sort_field not in self.data[0]:
            raise SkillError("E005", f"字段不存在: {dimension_field} 或 {sort_field}")

        # 聚合相同维度
        agg: Dict[str, float] = {}
        for row in self.data:
            dim = str(row.get(dimension_field, ""))
            v = self._to_numeric(row.get(sort_field))
            if v is None:
                raise SkillError("E006", f"字段 {sort_field} 包含非数值数据")
            agg[dim] = agg.get(dim, 0.0) + v

        sorted_items = sorted(agg.items(), key=lambda x: x[1], reverse=True)
        top_items = sorted_items[:n]

        return {
            "dimension_field": dimension_field,
            "sort_field": sort_field,
            "top": top_items,
            "total_count": len(agg),
        }


# ============================================================
# 图表生成模块（ASCII 简易图表）
# ============================================================
class ChartGenerator:
    """图表生成器：生成 ASCII 简易图表用于文本报告"""

    @staticmethod
    def line_chart(values: List[float], labels: Optional[List[str]] = None, width: int = 40) -> str:
        """生成简易折线图"""
        if not values:
            return "(无数据)"

        min_v, max_v = min(values), max(values)
        if max_v - min_v < 1e-9:
            # 所有值相同
            range_v = 1.0
            min_v = min_v - 0.5
            max_v = max_v + 0.5
        else:
            range_v = max_v - min_v

        # 归一化到 [0, height-1]
        height = 10
        points = []
        for i, v in enumerate(values):
            norm = int((v - min_v) / range_v * (height - 1))
            points.append((i, norm))

        # 绘制
        lines = []
        for h in range(height - 1, -1, -1):
            line = ""
            for x in range(len(values)):
                # 计算 x 位置（缩放）
                x_scaled = int(x * (width - 1) / max(1, len(values) - 1))
                while len(line) < x_scaled:
                    line += " "
                if any(p[1] == h for p in points if p[0] == x):
                    line += "*"
                else:
                    line += " "
            lines.append(line.rstrip())

        # 添加 Y 轴标签
        y_labels = [f"{max_v:.1f}", f"{min_v:.1f}"]
        labeled_lines = []
        for i, line in enumerate(lines):
            if i == 0:
                labeled_lines.append(f"{y_labels[0]:>8} | {line}")
            elif i == len(lines) - 1:
                labeled_lines.append(f"{y_labels[1]:>8} | {line}")
            else:
                labeled_lines.append(f"{'':>8} | {line}")

        # X 轴
        x_axis = f"{'':>8} +" + "-" * width
        labeled_lines.append(x_axis)

        return "\n".join(labeled_lines)

    @staticmethod
    def bar_chart(items: List[Tuple[str, float]], width: int = 40) -> str:
        """生成简易柱状图"""
        if not items:
            return "(无数据)"

        max_v = max(v for _, v in items)
        if max_v <= 0:
            max_v = 1.0

        lines = []
        for label, value in items:
            bar_len = int(value / max_v * width)
            bar = "█" * bar_len
            lines.append(f"{label:<20} | {bar} {value:.2f}")

        return "\n".join(lines)

    @staticmethod
    def pie_chart(proportions: Dict[str, float]) -> str:
        """生成简易饼图（用百分比列表表示）"""
        if not proportions:
            return "(无数据)"

        lines = []
        total = sum(proportions.values())
        for label, prop in sorted(proportions.items(), key=lambda x: x[1], reverse=True):
            pct = prop / total * 100
            bar_len = int(pct / 100 * 30)
            bar = "█" * bar_len
            lines.append(f"{label:<20} | {bar} {pct:.1f}%")

        return "\n".join(lines)


# ============================================================
# 报告生成模块
# ============================================================
class ReportGenerator:
    """报告生成器：组装分析结果生成 Markdown 报告"""

    def __init__(self, data: List[Dict[str, Any]]):
        self.data = data
        self.analyzer = DataAnalyzer(data)
        self.chart_gen = ChartGenerator()

    def generate(self, topn: int = 5) -> str:
        """生成完整报告"""
        fields = self.analyzer.get_fields()
        report_lines = [
            "# 数据洞察分析报告",
            "",
            f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"**数据规模**: {len(self.data)} 行 × {len(fields)} 列",
            "",
            "---",
            "",
            "## 1. 数据概览",
            "",
            f"字段列表: {', '.join(fields)}",
            "",
            "前 5 行数据预览:",
            "",
            "| " + " | ".join(fields) + " |",
            "|" + "|".join(["---"] * len(fields)) + "|",
        ]

        # 数据预览
        for row in self.data[:5]:
            values = [str(row.get(f, ""))[:30] for f in fields]
            report_lines.append("| " + " | ".join(values) + " |")

        report_lines.extend(["", "---", "", "## 2. 自动分析", ""])

        # 自动选择分析维度
        numeric_fields = []
        category_fields = []
        for f in fields:
            sample_vals = [self.data[i].get(f) for i in range(min(3, len(self.data)))]
            if all(self.analyzer._to_numeric(v) is not None for v in sample_vals):
                numeric_fields.append(f)
            else:
                category_fields.append(f)

        if not numeric_fields:
            raise SkillError("E006", "未找到数值型字段，无法进行分析")

        # 趋势分析（使用第一个数值字段）
        trend_field = numeric_fields[0]
        time_field = fields[0] if fields[0] != trend_field else fields[1] if len(fields) > 1 else fields[0]

        try:
            trend_result = self.analyzer.trend_analysis(time_field, trend_field)
            report_lines.extend([
                "### 2.1 趋势分析",
                "",
                f"- 分析维度: `{time_field}` → `{trend_field}`",
                f"- 趋势判断: **{trend_result['trend']}**",
                f"- 均值: {trend_result['mean']:.2f}",
                f"- 标准差: {trend_result['std_dev']:.2f}",
                f"- 波动范围: [{trend_result['min']:.2f}, {trend_result['max']:.2f}]",
                "",
                "
